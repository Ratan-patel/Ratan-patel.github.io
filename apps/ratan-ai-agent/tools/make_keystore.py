#!/usr/bin/env python3
"""Create the PKCS#12 signing key used for RATAN AI AGENT release APKs.

    pip install cryptography
    python3 apps/ratan-ai-agent/tools/make_keystore.py \
        --out apps/ratan-ai-agent/keystore/ratan-agent-release.p12 \
        --alias ratan-agent --password 'choose-something-long'

Android's Gradle plugin reads PKCS#12 directly (`storeType "PKCS12"`), so no keytool/JDK is
required to mint a signing identity — which is what lets this repository sign its own builds
from a plain Python environment.

A note on trust: the keystore that ships in this repository is *public by design*. It exists so
that every CI build carries the same signature and users can install updates over an older
release without uninstalling. That is exactly the trust model of a debug key — with the
difference that the fingerprint is documented. Treat it as an anti-footgun, not as an identity:
generate a private key and pass it through CI secrets (`ANDROID_KEYSTORE_BASE64`) before you
distribute anywhere that matters.
"""

from __future__ import annotations

import argparse
import datetime
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, help="where to write the .p12 keystore")
    parser.add_argument("--alias", default="ratan-agent")
    parser.add_argument("--password", required=True, help="keystore + key password")
    parser.add_argument("--cn", default="RATAN AI AGENT")
    parser.add_argument("--org", default="Ratan Patel")
    parser.add_argument("--country", default="IN")
    parser.add_argument("--days", type=int, default=10950, help="validity (default ~30 years)")
    parser.add_argument("--key-size", type=int, default=4096)
    args = parser.parse_args()

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("error: requires the 'cryptography' package (pip install cryptography)",
              file=sys.stderr)
        return 2

    key = rsa.generate_private_key(public_exponent=65537, key_size=args.key_size)
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, args.cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, args.org),
        x509.NameAttribute(NameOID.COUNTRY_NAME, args.country),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=args.days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
        .sign(key, hashes.SHA256())
    )

    payload = pkcs12.serialize_key_and_certificates(
        args.alias.encode("utf-8"),
        key,
        certificate,
        None,
        serialization.BestAvailableEncryption(args.password.encode("utf-8")),
    )
    with open(args.out, "wb") as handle:
        handle.write(payload)

    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    print(f"wrote {args.out}")
    print(f"  alias       {args.alias}")
    print(f"  key         RSA-{args.key_size}")
    print(f"  sha256(cert) {fingerprint}")
    print(f"  validity    {args.days} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

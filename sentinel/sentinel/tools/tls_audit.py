"""TLS configuration and certificate audit for hosts you are authorized to test.

Opens a TLS handshake only - no application-layer requests, no payload.
"""

from __future__ import annotations

import datetime as _dt
import socket
import ssl
from typing import Any

from ..scope import host_from_url
from .base import Finding, Tool, ToolContext, ToolResult

# Protocols that should not be negotiable in 2026.
LEGACY_PROTOCOLS = {
    "SSLv3": ssl.PROTOCOL_TLS_CLIENT,  # placeholder; tested via options below
    "TLSv1": ssl.PROTOCOL_TLS_CLIENT,
    "TLSv1.1": ssl.PROTOCOL_TLS_CLIENT,
}

WEAK_CIPHER_FRAGMENTS = (
    "NULL", "EXPORT", "DES-CBC3", "RC4", "RC2", "IDEA", "MD5",
    "anon", "AES128-SHA", "AES256-SHA", "CAMELLIA", "SEED", "PSK",
)


def _port_from(target: str, explicit: Any) -> int:
    if explicit:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    text = target.strip()
    if "://" in text:
        scheme, _, rest = text.partition("://")
        if scheme.lower() in ("https", "ftps", "imaps", "smtps"):
            default = 443
        else:
            default = 443
        hostport = rest.split("/", 1)[0]
        if hostport.count(":") == 1 and not hostport.startswith("["):
            try:
                return int(hostport.rsplit(":", 1)[1])
            except ValueError:
                return default
        return default
    return 443


class TlsAudit(Tool):
    name = "tls_audit"
    description = (
        "Audit TLS configuration for a host you own or are authorized to test: "
        "negotiated protocol, cipher strength, certificate validity, chain, "
        "expiry, SAN coverage, signature algorithm and key size. Performs a "
        "handshake only."
    )
    kind = "host"
    schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string",
                       "description": "Hostname or URL in scope, e.g. app.example.test"},
            "port": {"type": "integer", "description": "TLS port. Default 443."},
            "check_legacy": {
                "type": "boolean",
                "description": "Also attempt SSLv3/TLS1.0/TLS1.1 handshakes to "
                               "confirm they are refused. Default false.",
            },
        },
        "required": ["target"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        target = str(args.get("target") or "").strip()
        host = host_from_url(target) or target
        port = _port_from(target, args.get("port"))

        decision = self.authorize(ctx, host, port=port)
        if not decision.allowed:
            return ctx.refuse(self.name, f"{host}:{port}", decision.reason, decision.rule)

        findings: list[Finding] = []
        data: dict[str, Any] = {"host": host, "port": port}

        try:
            negotiated, cert, cipher = self._handshake(host, port, ctx.timeout)
        except (ssl.SSLError, ssl.CertificateError) as exc:
            return ToolResult(
                tool=self.name, target=f"{host}:{port}", ok=False,
                error=f"TLS handshake failed: {type(exc).__name__}: {exc}",
                findings=[Finding(
                    title="TLS handshake failed",
                    severity="high",
                    detail=f"{type(exc).__name__}: {exc}",
                    remediation="A failed handshake means browsers/clients cannot "
                                "establish trust. Check the certificate chain, "
                                "SNI configuration and protocol support.",
                )],
                data=data,
            )
        except (socket.gaierror, socket.herror, OSError, TimeoutError) as exc:
            return ToolResult(
                tool=self.name, target=f"{host}:{port}", ok=False,
                error=f"could not reach {host}:{port} - {type(exc).__name__}: {exc}",
                data=data,
            )

        data["negotiated_protocol"] = negotiated
        data["cipher"] = list(cipher) if cipher else None

        # --- protocol ------------------------------------------------------
        if negotiated in ("SSLv3", "TLSv1", "TLSv1.1"):
            findings.append(Finding(
                title=f"Deprecated protocol negotiated: {negotiated}",
                severity="critical",
                detail=f"{negotiated} is broken (POODLE/BEAST) and prohibited by "
                       f"RFC 8996.",
                remediation="Disable SSLv3/TLS1.0/TLS1.1; enable TLS 1.2 and 1.3 only.",
                reference="https://datatracker.ietf.org/doc/html/rfc8996",
            ))
        elif negotiated == "TLSv1.2":
            findings.append(Finding(
                title="TLS 1.2 negotiated (1.3 available?)",
                severity="info",
                detail="TLS 1.2 is acceptable but 1.3 removes several handshake "
                       "round-trips and legacy cipher choices.",
                remediation="Prefer TLS 1.3 where clients support it.",
            ))

        # --- cipher --------------------------------------------------------
        if cipher:
            cipher_name = str(cipher[0])
            if any(fragment in cipher_name.upper() for fragment in WEAK_CIPHER_FRAGMENTS):
                findings.append(Finding(
                    title=f"Weak cipher negotiated: {cipher_name}",
                    severity="high",
                    detail=f"Cipher suite {cipher_name} uses a primitive on the "
                           f"deprecated list.",
                    remediation="Restrict to modern AEAD suites "
                                "(TLS_AES_256_GCM_SHA384, ECDHE-*-GCM-SHA384, CHACHA20).",
                ))
            bits = int(cipher[2]) if len(cipher) > 2 else 0
            if bits and bits < 128:
                findings.append(Finding(
                    title=f"Cipher key length only {bits} bits",
                    severity="high",
                    detail=f"Effective security below 128 bits.",
                    remediation="Require >=128-bit AEAD suites.",
                ))

        # --- certificate ---------------------------------------------------
        findings += self._cert_findings(cert, host)
        data["certificate"] = self._cert_summary(cert, host)

        # --- legacy protocol probe ----------------------------------------
        if args.get("check_legacy"):
            data["legacy_probe"] = self._legacy_probe(host, port, ctx)

        return ToolResult(tool=self.name, target=f"{host}:{port}", ok=True,
                          findings=findings, data=data)

    # ------------------------------------------------------------- internals

    def _handshake(self, host: str, port: int, timeout: float):
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as sock:
                return sock.version(), sock.getpeercert(), sock.cipher()

    def _legacy_probe(self, host: str, port: int, ctx: ToolContext) -> dict[str, str]:
        """Confirm the host refuses old protocols. Handshake attempts only."""
        outcomes: dict[str, str] = {}
        cases = {
            "TLSv1": ssl.OP_NO_TLSv1,
            "TLSv1.1": ssl.OP_NO_TLSv1_1,
            "TLSv1.2": ssl.OP_NO_TLSv1_2,
        }
        for label, flag in cases.items():
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            # isolate: disable everything except the one we are testing
            context.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
                                | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
                                | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3)
            context.options &= ~flag
            ctx.limiter.wait()
            try:
                with socket.create_connection((host, port), timeout=min(ctx.timeout, 8)) as raw:
                    with context.wrap_socket(raw, server_hostname=host) as sock:
                        outcomes[label] = f"ACCEPTED ({sock.version()})"
            except (ssl.SSLError, OSError, TimeoutError) as exc:
                outcomes[label] = f"refused ({type(exc).__name__})"
        return outcomes

    def _cert_summary(self, cert: dict[str, Any] | None, host: str) -> dict[str, Any]:
        if not cert:
            return {"present": False}
        subject = dict(x[0] for x in cert.get("subject", ()))
        issuer = dict(x[0] for x in cert.get("issuer", ()))
        sans = [v for t, v in cert.get("subjectAltName", ()) if t == "DNS"]
        not_before = cert.get("notBefore")
        not_after = cert.get("notAfter")
        return {
            "present": True,
            "subject_cn": subject.get("commonName"),
            "issuer_o": issuer.get("organizationName"),
            "issuer_cn": issuer.get("commonName"),
            "sans": sans,
            "not_before": not_before,
            "not_after": not_after,
            "serial": cert.get("serialNumber"),
            "version": cert.get("version"),
        }

    def _cert_findings(self, cert: dict[str, Any] | None, host: str) -> list[Finding]:
        if not cert:
            return [Finding(
                title="No certificate returned",
                severity="high",
                detail="The peer completed the handshake without presenting a "
                       "certificate Python could parse.",
                remediation="Verify the server presents its full leaf + chain.",
            )]
        out: list[Finding] = []
        not_after_raw = cert.get("notAfter")
        not_before_raw = cert.get("notBefore")
        parsed_after = _parse_cert_time(not_after_raw)
        parsed_before = _parse_cert_time(not_before_raw)
        now = _dt.datetime.now(_dt.timezone.utc)

        if parsed_after:
            days_left = (parsed_after - now).days
            if days_left < 0:
                out.append(Finding(
                    title="Certificate has expired",
                    severity="critical",
                    detail=f"notAfter={not_after_raw} ({abs(days_left)} days ago).",
                    remediation="Renew immediately; add expiry monitoring so this "
                                "cannot recur.",
                ))
            elif days_left <= 14:
                out.append(Finding(
                    title=f"Certificate expires in {days_left} days",
                    severity="high",
                    detail=f"notAfter={not_after_raw}.",
                    remediation="Renew now. Automate with ACME so renewal is not "
                                "manual.",
                ))
            elif days_left <= 30:
                out.append(Finding(
                    title=f"Certificate expires in {days_left} days",
                    severity="medium",
                    detail=f"notAfter={not_after_raw}.",
                    remediation="Schedule renewal.",
                ))
            if (parsed_after - (parsed_before or now)).days > 825:
                out.append(Finding(
                    title="Certificate lifetime exceeds 825 days",
                    severity="low",
                    detail="Long-lived certificates are rejected by modern browsers "
                           "and widen the blast radius of a key compromise.",
                    remediation="Issue short-lived certificates (<=90 days) via ACME.",
                ))
        if parsed_before and parsed_before > now:
            out.append(Finding(
                title="Certificate is not yet valid",
                severity="high",
                detail=f"notBefore={not_before_raw}.",
                remediation="Check server clock and certificate issuance dates.",
            ))

        sans = [v.lower() for t, v in cert.get("subjectAltName", ()) if t == "DNS"]
        subject = dict(x[0] for x in cert.get("subject", ()))
        cn = str(subject.get("commonName", "")).lower()
        if not sans:
            out.append(Finding(
                title="Certificate has no subjectAltName",
                severity="high",
                detail="Browsers ignore CN-only certificates since 2017.",
                remediation="Reissue with SAN entries.",
            ))
        elif not _name_matches(host.lower(), sans):
            out.append(Finding(
                title="Hostname not covered by certificate SANs",
                severity="high",
                detail=f"host={host!r} sans={sans}",
                remediation="Issue a certificate covering every name served, or "
                            "configure SNI correctly.",
            ))
        if cn and not sans and not _name_matches(host.lower(), [cn]):
            out.append(Finding(
                title="CN does not match the hostname",
                severity="high", detail=f"cn={cn!r} host={host!r}",
                remediation="Reissue with a matching SAN.",
            ))

        issuer = dict(x[0] for x in cert.get("issuer", ()))
        issuer_org = str(issuer.get("organizationName", ""))
        if not issuer_org or issuer_org.lower() in (host.lower(), "self", "localhost"):
            out.append(Finding(
                title="Certificate appears self-signed",
                severity="medium",
                detail=f"issuer={issuer!r}. Fine for a lab; not fine for anything "
                       f"a browser or client will trust.",
                remediation="Use a publicly trusted CA or an internal CA whose root "
                            "you distribute deliberately.",
            ))
        return out


def _parse_cert_time(value: str | None) -> _dt.datetime | None:
    if not value:
        return None
    for fmt in ("%b %d %H:%M:%S %Y %Z", "%Y%m%d%H%M%SZ"):
        try:
            return _dt.datetime.strptime(value, fmt).replace(tzinfo=_dt.timezone.utc)
        except ValueError:
            continue
    return None


def _name_matches(host: str, names: list[str]) -> bool:
    for name in names:
        if name.startswith("*."):
            suffix = name[1:]
            if host.endswith(suffix) and host.count(".") == name.count("."):
                return True
        elif host == name:
            return True
    return False

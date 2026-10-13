"""Passive DNS record audit for domains you are authorized to assess.

Includes a ~200-line dependency-free DNS client (UDP, RFC 1035 wire format with
name decompression) so A/AAAA/NS/MX/TXT/SOA/CAA/DNSSEC records can be read
without dnspython or `dig`.

This is public-record lookups only: no zone transfer, no brute-forcing of
subdomains, no queries to the domain's own authoritative servers beyond what a
normal resolver would do.
"""

from __future__ import annotations

import random
import socket
import struct
from typing import Any

from .base import Finding, Tool, ToolContext, ToolResult

DEFAULT_RESOLVERS = ("1.1.1.1", "9.9.9.9", "8.8.8.8")

QTYPE = {
    "A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "PTR": 12, "MX": 15, "TXT": 16,
    "AAAA": 28, "SRV": 33, "CAA": 257, "DS": 43, "RRSIG": 46, "DNSKEY": 48,
    "TLSA": 52,
}
RTYPE_NAME = {v: k for k, v in QTYPE.items()}


class DnsError(Exception):
    pass


# --------------------------------------------------------------------- wire


def _encode_name(name: str) -> bytes:
    out = b""
    for label in name.rstrip(".").split("."):
        encoded = label.encode("idna") if not label.isascii() else label.encode()
        if len(encoded) > 63:
            raise DnsError(f"label too long: {label!r}")
        out += bytes([len(encoded)]) + encoded
    return out + b"\x00"


def _decode_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    jumped = False
    end = offset
    seen = 0
    while True:
        if offset >= len(data):
            raise DnsError("truncated name")
        length = data[offset]
        if length & 0xC0 == 0xC0:                      # compression pointer
            if offset + 1 >= len(data):
                raise DnsError("truncated pointer")
            pointer = struct.unpack("!H", data[offset:offset + 2])[0] & 0x3FFF
            if not jumped:
                end = offset + 2
            offset = pointer
            jumped = True
            seen += 1
            if seen > 32:
                raise DnsError("pointer loop")
            continue
        if length == 0:
            if not jumped:
                end = offset + 1
            break
        offset += 1
        if offset + length > len(data):
            raise DnsError("truncated label")
        labels.append(data[offset:offset + length].decode("utf-8", "replace"))
        offset += length
    return ".".join(labels), end


def _parse_rdata(rtype: int, data: bytes, rdata: bytes, rdata_offset: int) -> Any:
    name = RTYPE_NAME.get(rtype, str(rtype))
    try:
        if name == "A":
            return socket.inet_ntoa(rdata)
        if name == "AAAA":
            return socket.inet_ntop(socket.AF_INET6, rdata)
        if name in ("NS", "CNAME", "PTR"):
            return _decode_name(data, rdata_offset)[0]
        if name == "TXT":
            parts: list[bytes] = []
            index = 0
            while index < len(rdata):
                length = rdata[index]
                index += 1
                parts.append(rdata[index:index + length])
                index += length
            return b"".join(parts).decode("utf-8", "replace")
        if name == "MX":
            preference = struct.unpack("!H", rdata[:2])[0]
            return {"preference": preference,
                    "exchange": _decode_name(data, rdata_offset + 2)[0]}
        if name == "SOA":
            mname, cursor = _decode_name(data, rdata_offset)
            rname, cursor = _decode_name(data, cursor)
            fields = struct.unpack("!IIIII", rdata[cursor - rdata_offset:
                                                   cursor - rdata_offset + 20])
            return {"mname": mname, "rname": rname, "serial": fields[0],
                    "refresh": fields[1], "retry": fields[2],
                    "expire": fields[3], "minimum": fields[4]}
        if name == "SRV":
            priority, weight, port = struct.unpack("!HHH", rdata[:6])
            return {"priority": priority, "weight": weight, "port": port,
                    "target": _decode_name(data, rdata_offset + 6)[0]}
        if name == "CAA":
            flags = rdata[0]
            tag_len = rdata[1]
            return {"flags": flags, "tag": rdata[2:2 + tag_len].decode(),
                    "value": rdata[2 + tag_len:].decode("utf-8", "replace")}
        if name in ("RRSIG", "DNSKEY", "DS", "TLSA"):
            return {"present": True, "bytes": len(rdata)}
    except (struct.error, UnicodeDecodeError, IndexError, OSError, DnsError):
        pass
    return {"raw_hex": rdata[:64].hex()}


def query(name: str, rtype: str, resolver: str = DEFAULT_RESOLVERS[0],
          timeout: float = 5.0, use_tcp: bool = False) -> dict[str, Any]:
    """Issue one DNS query and return parsed answers."""
    if rtype not in QTYPE:
        raise DnsError(f"unsupported record type {rtype!r}")
    transaction_id = random.randint(0, 0xFFFF)
    header = struct.pack("!HHHHHH", transaction_id, 0x0100, 1, 0, 0, 0)
    packet = header + _encode_name(name) + struct.pack("!HH", QTYPE[rtype], 1)

    if use_tcp:
        with socket.create_connection((resolver, 53), timeout=timeout) as sock:
            sock.sendall(struct.pack("!H", len(packet)) + packet)
            length_bytes = sock.recv(2)
            if len(length_bytes) < 2:
                raise DnsError("short TCP response")
            length = struct.unpack("!H", length_bytes)[0]
            chunks = b""
            while len(chunks) < length:
                piece = sock.recv(length - len(chunks))
                if not piece:
                    break
                chunks += piece
            data = chunks
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(packet, (resolver, 53))
            data, _ = sock.recvfrom(65535)
        finally:
            sock.close()

    if len(data) < 12:
        raise DnsError("response shorter than a DNS header")
    rid, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", data[:12])
    if rid != transaction_id:
        raise DnsError("transaction id mismatch - possible spoofed response")
    rcode = flags & 0x000F
    truncated = bool(flags & 0x0200)
    if truncated and not use_tcp:
        return query(name, rtype, resolver, timeout, use_tcp=True)

    offset = 12
    for _ in range(qd):                                   # skip the question
        _, offset = _decode_name(data, offset)
        offset += 4

    answers: list[dict[str, Any]] = []
    for _ in range(an + ns + ar):
        if offset >= len(data):
            break
        _, offset = _decode_name(data, offset)
        if offset + 10 > len(data):
            break
        record_type, _klass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset + 10])
        offset += 10
        rdata = data[offset:offset + rdlength]
        answers.append({
            "type": RTYPE_NAME.get(record_type, str(record_type)),
            "ttl": ttl,
            "section": "answer" if _ < an else "authority/additional",
            "value": _parse_rdata(record_type, data, rdata, offset),
        })
        offset += rdlength

    return {
        "name": name, "rtype": rtype, "resolver": resolver,
        "rcode": rcode, "rcode_name": RCODE_NAMES.get(rcode, str(rcode)),
        "authoritative": bool(flags & 0x0400),
        "answers": [a for a in answers if a["section"] == "answer"],
        "all_records": answers,
    }


RCODE_NAMES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN",
               4: "NOTIMP", 5: "REFUSED"}


# --------------------------------------------------------------------- tool


class DnsAudit(Tool):
    name = "dns_audit"
    description = (
        "Read public DNS records for a domain you own or are authorized to "
        "assess: A, AAAA, NS, MX, TXT (SPF/DKIM/DMARC), SOA, CAA and DNSSEC "
        "signatures. Passive public-record lookups via a public resolver - no "
        "zone transfer, no subdomain brute-forcing."
    )
    kind = "host"
    schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string",
                       "description": "Domain in scope, e.g. example.test"},
            "resolver": {"type": "string",
                         "description": "Resolver IP. Default 1.1.1.1"},
            "records": {
                "type": "array", "items": {"type": "string"},
                "description": "Record types to read. Default "
                               "[A, AAAA, NS, MX, TXT, SOA, CAA, DS, RRSIG].",
            },
        },
        "required": ["target"],
    }

    DEFAULT_RECORDS = ("A", "AAAA", "NS", "MX", "TXT", "SOA", "CAA", "DS", "RRSIG")

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        target = str(args.get("target") or "").strip().rstrip(".")
        if "://" in target:
            target = target.split("://", 1)[1].split("/", 1)[0]
        decision = self.authorize(ctx, target)
        if not decision.allowed:
            return ctx.refuse(self.name, target, decision.reason, decision.rule)

        resolver = str(args.get("resolver") or DEFAULT_RESOLVERS[0])
        wanted = [r.upper() for r in (args.get("records") or self.DEFAULT_RECORDS)]
        wanted = [r for r in wanted if r in QTYPE]

        records: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for rtype in wanted:
            ctx.limiter.wait()
            try:
                records[rtype] = query(target, rtype, resolver,
                                       timeout=min(ctx.timeout, 8.0))
            except (DnsError, socket.timeout, TimeoutError, OSError) as exc:
                errors[rtype] = f"{type(exc).__name__}: {exc}"

        findings = self._analyse(target, records, errors)
        return ToolResult(
            tool=self.name, target=target, ok=not errors or bool(records),
            findings=findings,
            data={"resolver": resolver, "records": records, "errors": errors},
            error=None if not errors else f"{len(errors)} record type(s) failed: "
                                          + ", ".join(sorted(errors)),
        )

    # ------------------------------------------------------------- analyses

    def _analyse(self, domain: str, records: dict[str, Any],
                 errors: dict[str, str]) -> list[Finding]:
        out: list[Finding] = []

        rcode_of = lambda rt: (records.get(rt) or {}).get("rcode")  # noqa: E731
        if rcode_of("A") == 3 and rcode_of("AAAA") == 3 and rcode_of("NS") == 3:
            out.append(Finding(
                title="Domain does not resolve (NXDOMAIN)",
                severity="info",
                detail=f"No A, AAAA or NS records for {domain}. If you own it, "
                       f"this may be a dangling-delegation / takeover risk.",
                remediation="Confirm whether NS records should exist. A domain with "
                            "NS delegations to a deprovisioned provider can be "
                            "claimed by someone else.",
                reference="https://owasp.org/www-project-web-security-testing-guide/",
            ))

        txts = [a["value"] for a in (records.get("TXT") or {}).get("answers", [])
                if isinstance(a.get("value"), str)]
        spf = [t for t in txts if t.lower().startswith("v=spf1")]
        dmarc = [t for t in txts if t.lower().startswith("v=dmarc1")]

        # --- SPF -----------------------------------------------------------
        if not spf:
            out.append(Finding(
                title="No SPF record",
                severity="high",
                detail="Anyone can send mail claiming to be from "
                       f"{domain}; spoofing is trivial.",
                remediation="Publish `v=spf1 -all` if the domain sends no mail, "
                            "otherwise list your senders and end with `-all`.",
                reference="https://datatracker.ietf.org/doc/html/rfc7208",
            ))
        else:
            policy = spf[0]
            lowered = policy.lower()
            if len(spf) > 1:
                out.append(Finding(
                    title="Multiple SPF records",
                    severity="high",
                    detail=f"{len(spf)} TXT records begin with v=spf1. RFC 7208 "
                           f"permits exactly one; receivers must return PermError.",
                    remediation="Merge into a single SPF record.",
                ))
            if "all" in lowered:
                qualifier = lowered.rsplit("all", 1)[0][-1:] if lowered.rstrip().endswith("all") else ""
                if qualifier in ("~", "?"):
                    out.append(Finding(
                        title=f"SPF ends in a {'softfail' if qualifier == '~' else 'neutral'} 'all'",
                        severity="medium",
                        detail=f"`{policy}` - spoofed mail is still widely delivered.",
                        remediation="Move to `-all` once you are sure of every "
                                    "legitimate sender.",
                    ))
                elif qualifier != "-":
                    out.append(Finding(
                        title="SPF 'all' has no explicit qualifier",
                        severity="low", detail=f"`{policy}`",
                        remediation="Use an explicit `-all`.",
                    ))
            else:
                out.append(Finding(
                    title="SPF record has no 'all' mechanism",
                    severity="high", detail=f"`{policy}`",
                    remediation="Terminate SPF with `-all`.",
                ))
            includes = lowered.count("include:") + lowered.count("a:") \
                + lowered.count("mx:") + lowered.count("ptr")
            if "ptr" in lowered:
                out.append(Finding(
                    title="SPF uses the deprecated 'ptr' mechanism",
                    severity="medium",
                    detail="`ptr` is slow, unreliable and deprecated by RFC 7208.",
                    remediation="Replace with `include:` or `ip4:`/`ip6:`.",
                ))
            dns_lookups = lowered.count("include:") + lowered.count("redirect=") \
                + lowered.count("exists:")
            if dns_lookups > 10 or includes > 10:
                out.append(Finding(
                    title="SPF likely exceeds the 10-DNS-lookup limit",
                    severity="high",
                    detail=f"~{max(includes, dns_lookups)} lookup-generating "
                           f"mechanisms. Beyond 10 the result is PermError and all "
                           f"your mail fails SPF.",
                    remediation="Flatten the SPF record (resolve includes to ip4:).",
                ))
            if "+all" in lowered:
                out.append(Finding(
                    title="SPF set to '+all' (allow anyone)",
                    severity="critical",
                    detail="This explicitly authorises every sender on the internet.",
                    remediation="Change to `-all` immediately.",
                ))

        # --- DMARC ---------------------------------------------------------
        if not dmarc:
            out.append(Finding(
                title="No DMARC record",
                severity="high",
                detail=f"Without _dmarc.{domain} receivers have no instruction for "
                       f"mail that fails SPF/DKIM, so spoofed mail is delivered.",
                remediation="Start with `v=DMARC1; p=none; rua=mailto:dmarc@<you>` "
                            "to collect reports, then move to p=quarantine and "
                            "p=reject.",
                reference="https://datatracker.ietf.org/doc/html/rfc7489",
            ))
        else:
            policy = dmarc[0].lower()
            if "p=none" in policy:
                out.append(Finding(
                    title="DMARC policy is 'none' (monitor only)",
                    severity="medium",
                    detail=f"`{dmarc[0]}` - spoofed mail is still delivered.",
                    remediation="Review rua reports, then raise to p=quarantine and "
                                "finally p=reject.",
                ))
            if "rua=" not in policy and "ruf=" not in policy:
                out.append(Finding(
                    title="DMARC has no reporting address",
                    severity="low",
                    detail="You will not see who is sending as your domain.",
                    remediation="Add `rua=mailto:...`.",
                ))
            if "pct=" in policy:
                pct = policy.split("pct=")[1].split(";")[0].strip()
                if pct.isdigit() and int(pct) < 100:
                    out.append(Finding(
                        title=f"DMARC applies to only {pct}% of mail",
                        severity="info",
                        detail="Partial enforcement leaves the remainder unpoliced.",
                        remediation="Raise pct to 100 once reports are clean.",
                    ))
            if "adkim=r" in policy or "aspf=r" in policy:
                out.append(Finding(
                    title="DMARC alignment set to relaxed",
                    severity="low",
                    detail="Relaxed alignment accepts any subdomain of the "
                           "organisational domain.",
                    remediation="Use `adkim=s; aspf=s` if you do not rely on "
                                "subdomain sending.",
                ))

        # --- DKIM hint -----------------------------------------------------
        if spf and not dmarc:
            out.append(Finding(
                title="SPF without DKIM/DMARC cannot survive forwarding",
                severity="medium",
                detail="Forwarders rewrite the return path, breaking SPF. DKIM "
                       "signs the message body and survives.",
                remediation="Enable DKIM at your mail provider and publish DMARC.",
            ))

        # --- CAA -----------------------------------------------------------
        caa_answers = (records.get("CAA") or {}).get("answers", [])
        if rcode_of("CAA") == 0 and not caa_answers:
            out.append(Finding(
                title="No CAA record",
                severity="medium",
                detail="Any CA in the world may issue a certificate for "
                       f"{domain}.",
                remediation="Publish `CAA 0 issue \"<your-ca>\"` plus "
                            "`CAA 0 iodef \"mailto:security@<you>\"`.",
                reference="https://datatracker.ietf.org/doc/html/rfc8659",
            ))

        # --- DNSSEC --------------------------------------------------------
        has_ds = bool((records.get("DS") or {}).get("answers"))
        has_rrsig = any(a["type"] == "RRSIG"
                        for a in (records.get("RRSIG") or {}).get("answers", []))
        if not has_ds and not has_rrsig:
            out.append(Finding(
                title="DNSSEC not deployed",
                severity="medium",
                detail="Responses can be forged in transit; users relying on DANE, "
                       "SSHFP or DNS-based service discovery are exposed.",
                remediation="Enable DNSSEC at your registrar/DNS provider and "
                            "publish the DS record.",
                reference="https://datatracker.ietf.org/doc/html/rfc4033",
            ))

        # --- NS ------------------------------------------------------------
        ns_answers = [a["value"] for a in (records.get("NS") or {}).get("answers", [])
                      if isinstance(a.get("value"), str)]
        if ns_answers:
            if len(set(ns_answers)) < 2:
                out.append(Finding(
                    title="Fewer than two nameservers",
                    severity="medium",
                    detail=f"NS = {sorted(set(ns_answers))}. Single point of failure.",
                    remediation="Delegate to at least two nameservers on separate "
                                "infrastructure.",
                ))
            for ns in ns_answers:
                if ns.endswith(domain + ".") or ns.endswith("." + domain):
                    out.append(Finding(
                        title=f"In-bailiwick nameserver '{ns}' with no glue check",
                        severity="info",
                        detail="In-bailiwick NS records require glue at the parent; "
                               "missing glue makes the zone unresolvable.",
                        remediation="Verify glue records exist at the registrar.",
                    ))
                    break

        # --- MX ------------------------------------------------------------
        mx_answers = [a["value"] for a in (records.get("MX") or {}).get("answers", [])
                      if isinstance(a.get("value"), dict)]
        if mx_answers:
            exchanges = {m.get("exchange", "") for m in mx_answers}
            if not spf:
                out.append(Finding(
                    title="Domain receives mail but publishes no SPF",
                    severity="high",
                    detail=f"MX = {sorted(exchanges)}. Spoofing this domain is "
                           f"trivial and your users will trust the result.",
                    remediation="Publish SPF covering every sending service.",
                ))
            if len(exchanges) < 2:
                out.append(Finding(
                    title="Single MX record",
                    severity="low",
                    detail=f"MX = {sorted(exchanges)}. No mail failover.",
                    remediation="Add a backup MX with a higher preference.",
                ))

        # --- TTL / SOA -----------------------------------------------------
        soa_answers = (records.get("SOA") or {}).get("answers", [])
        for answer in soa_answers:
            value = answer.get("value")
            if isinstance(value, dict):
                minimum = value.get("minimum", 0)
                if minimum and minimum < 300:
                    out.append(Finding(
                        title=f"Very low SOA minimum TTL ({minimum}s)",
                        severity="info",
                        detail="Negative caching under 5 minutes increases resolver "
                               "load and can amplify an outage.",
                        remediation="Use 300-3600s unless you are mid-migration.",
                    ))
                serial = str(value.get("serial", ""))
                if len(serial) == 10 and not serial.startswith(
                        "20"):
                    out.append(Finding(
                        title="SOA serial is not date-based",
                        severity="info",
                        detail=f"serial={serial}. YYYYMMDDnn serials make it obvious "
                               f"whether a change propagated.",
                        remediation="Adopt a date-based serial convention.",
                    ))

        for rtype, message in sorted(errors.items()):
            out.append(Finding(
                title=f"Could not read {rtype} records",
                severity="info", detail=message,
                remediation="May be a resolver/network limitation rather than a DNS "
                            "problem; retry with a different --resolver.",
            ))
        return out


def analyse_spf_from_text(record: str) -> dict[str, Any]:
    """Pure helper (unit-testable without DNS) exposing the SPF verdict."""
    lowered = record.lower()
    mechanisms = [m for m in lowered.split() if m != "v=spf1"]
    return {
        "mechanisms": mechanisms,
        "count": len(mechanisms),
        "uses_ptr": any(m.startswith("ptr") for m in mechanisms),
        "all_qualifier": next(
            (m[0] if m[0] in "+-~?" else "+" for m in mechanisms if m.endswith("all")),
            None,
        ),
        "lookup_generating": sum(
            lowered.count(token)
            for token in ("include:", "redirect=", "exists:", "a:", "a/", "mx", "ptr")
        ),
    }

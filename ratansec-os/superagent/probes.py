"""Bounded, non-destructive assessment probes (standard library only).

Live probes never follow redirects, never send credentials/cookies, never read
response bodies (except two well-known public text files), and pin the validated
DNS answer for the connection. Every probe re-checks authorization first.
"""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from . import scope
from .settings import settings

MAX_TEXT_BYTES = 16_384
PROBE_IDS = ("dns", "http_headers", "tls", "security_txt", "robots")
PROFILES: dict[str, dict[str, Any]] = {
    "quick": {
        "title": "Quick posture",
        "description": "DNS + response headers + TLS certificate. Three bounded checks.",
        "probes": ["dns", "http_headers", "tls"],
    },
    "web": {
        "title": "Web hygiene",
        "description": "Quick posture plus security.txt and robots.txt discovery.",
        "probes": ["dns", "http_headers", "tls", "security_txt", "robots"],
    },
    "tls": {
        "title": "TLS review",
        "description": "DNS resolution and certificate/protocol review.",
        "probes": ["dns", "tls"],
    },
}


class ProbeError(RuntimeError):
    pass


@dataclass
class ProbeResult:
    id: str
    status: str = "ok"
    data: dict[str, Any] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    duration_ms: int = 0

    def view(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "data": self.data,
                "findings": self.findings, "error": self.error, "duration_ms": self.duration_ms}


def _finding(code: str, severity: str, title: str, evidence: str, remediation: str,
             confidence: str = "high") -> dict[str, Any]:
    return {"code": code, "severity": severity, "title": title, "evidence": evidence,
            "remediation": remediation, "confidence": confidence, "status": "observed"}


def resolve_pinned(target: scope.Target) -> tuple[str, list[str]]:
    """Resolve and validate every answer; return one pinned IP + all answers."""
    decision = scope.check(target.raw, "recon")
    if not decision.allowed:
        raise ProbeError(decision.reason)
    if scope.hard_blocked(target.host):
        raise ProbeError("Hard-blocked host.")
    try:
        if scope._is_ip(target.host):
            answers = [target.host]
        else:
            infos = socket.getaddrinfo(target.host, None, type=socket.SOCK_STREAM)
            answers = list(dict.fromkeys(info[4][0] for info in infos))
    except OSError as exc:
        raise ProbeError(f"DNS resolution failed: {exc.strerror or exc}") from None
    if not answers:
        raise ProbeError("DNS returned no addresses.")
    for answer in answers:
        ip = ipaddress.ip_address(answer)
        if scope.hard_blocked(answer) or ip.is_unspecified or ip.is_multicast or ip.is_reserved:
            raise ProbeError(f"DNS answer {answer} is blocked by safety policy.")
        if (ip.is_private or ip.is_loopback or ip.is_link_local) and not settings.allow_private_ranges:
            raise ProbeError(f"DNS answer {answer} is private/local but private targets are disabled.")
        # A hostname in scope must not redirect traffic into a different private network.
        if not scope._is_ip(target.host) and (ip.is_private or ip.is_loopback or ip.is_link_local):
            if not any(scope.host_matches(answer, pattern) for pattern in settings.allowed_targets):
                raise ProbeError(f"DNS answer {answer} is not explicitly allowlisted for private access.")
    return answers[0], answers


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float):
        context = ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=context)
        self._pin = ip

    def connect(self):
        raw = socket.create_connection((self._pin, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


class _PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float):
        super().__init__(host, port, timeout=timeout)
        self._pin = ip

    def connect(self):
        self.sock = socket.create_connection((self._pin, self.port), self.timeout)


def _connection(target: scope.Target, ip: str, timeout: float) -> http.client.HTTPConnection:
    port = target.port or (443 if target.scheme == "https" else 80)
    if target.scheme == "https":
        return _PinnedHTTPS(target.host, port, ip, timeout)
    return _PinnedHTTP(target.host, port, ip, timeout)


def _request(target: scope.Target, path: str, *, method: str = "HEAD",
             read_body: bool = False, timeout: float = 8.0) -> dict[str, Any]:
    decision = scope.check(target.raw, "web")
    if not decision.allowed:
        raise ProbeError(decision.reason)
    ip, _ = resolve_pinned(target)
    conn = _connection(target, ip, timeout)
    headers = {
        "User-Agent": "RatanSec-SuperAgent/2.0 (authorized-security-assessment)",
        "Accept": "text/plain,*/*;q=0.1" if read_body else "*/*",
        "Accept-Encoding": "identity",
        "Connection": "close",
    }
    try:
        conn.request(method, path, headers=headers)
        response = conn.getresponse()
        seen: dict[str, str] = {}
        cookies: list[str] = []
        for key, value in response.getheaders():
            lower = key.lower()
            if lower == "set-cookie":
                cookies.append(value)
            elif lower in seen:
                seen[lower] += ", " + value
            else:
                seen[lower] = value
        body = ""
        if read_body:
            raw = response.read(MAX_TEXT_BYTES + 1)
            if len(raw) > MAX_TEXT_BYTES:
                raise ProbeError("Well-known text file exceeded the 16 KiB cap.")
            body = raw.decode("utf-8", "replace")
        return {"status": response.status, "headers": seen, "cookies": cookies,
                "body": body, "pinned_ip": ip, "method": method, "path": path}
    except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
        raise ProbeError(f"HTTP probe failed: {type(exc).__name__}: {exc}") from None
    finally:
        conn.close()


def probe_dns(target: scope.Target) -> ProbeResult:
    started = time.monotonic()
    _, answers = resolve_pinned(target)
    families = ["IPv6" if ":" in a else "IPv4" for a in answers]
    return ProbeResult("dns", data={"host": target.host, "addresses": answers, "families": families},
                       duration_ms=round((time.monotonic() - started) * 1000))


def probe_http_headers(target: scope.Target) -> ProbeResult:
    started = time.monotonic()
    try:
        observed = _request(target, target.path or "/", method="HEAD")
    except ProbeError:
        observed = _request(target, target.path or "/", method="GET")
    headers = observed["headers"]
    findings: list[dict[str, Any]] = []
    if target.scheme == "https" and "strict-transport-security" not in headers:
        findings.append(_finding("WEB-HSTS-001", "medium", "HSTS header missing",
                                 "HEAD response has no Strict-Transport-Security header.",
                                 "Add Strict-Transport-Security with an appropriate max-age after validating HTTPS."))
    if "content-security-policy" not in headers:
        findings.append(_finding("WEB-CSP-001", "medium", "Content Security Policy missing",
                                 "No Content-Security-Policy header was observed.",
                                 "Deploy a restrictive CSP and test it in report-only mode first."))
    if headers.get("x-content-type-options", "").lower() != "nosniff":
        findings.append(_finding("WEB-NOSNIFF-001", "low", "MIME sniffing protection missing",
                                 "X-Content-Type-Options is not nosniff.",
                                 "Set X-Content-Type-Options: nosniff."))
    if "referrer-policy" not in headers:
        findings.append(_finding("WEB-REFERRER-001", "low", "Referrer Policy missing",
                                 "No Referrer-Policy header was observed.",
                                 "Set a deliberate Referrer-Policy such as strict-origin-when-cross-origin."))
    server = headers.get("server", "")
    if any(ch.isdigit() for ch in server):
        findings.append(_finding("WEB-BANNER-001", "info", "Server version disclosed",
                                 f"Server header: {server[:120]}",
                                 "Minimize version disclosure; verify patch levels independently.", "medium"))
    for cookie in observed["cookies"]:
        lower = cookie.lower()
        name = cookie.split("=", 1)[0][:80]
        missing = [flag for flag in ("httponly", "secure", "samesite") if flag not in lower]
        if missing:
            findings.append(_finding("WEB-COOKIE-001", "medium", f"Cookie flags missing: {name}",
                                     f"Set-Cookie for {name} lacks: {', '.join(missing)}.",
                                     "Set HttpOnly, Secure and an appropriate SameSite attribute on sensitive cookies."))
    if 300 <= observed["status"] < 400 and "location" in headers:
        findings.append(_finding("WEB-REDIRECT-001", "info", "Redirect observed (not followed)",
                                 f"HTTP {observed['status']} Location: {headers['location'][:200]}",
                                 "Confirm the destination is intended and authorized; the agent did not follow it."))
    safe_headers = {k: v[:500] for k, v in headers.items() if k not in {"set-cookie", "authorization", "proxy-authorization"}}
    return ProbeResult("http_headers", data={"status": observed["status"], "headers": safe_headers,
                                             "pinned_ip": observed["pinned_ip"], "method": observed["method"],
                                             "path": observed["path"], "redirect_followed": False},
                       findings=findings, duration_ms=round((time.monotonic() - started) * 1000))


def probe_tls(target: scope.Target) -> ProbeResult:
    started = time.monotonic()
    if target.scheme != "https":
        return ProbeResult("tls", status="skipped", data={"reason": "Target is not HTTPS."},
                           findings=[_finding("TLS-PLAIN-001", "medium", "Plain HTTP target",
                                              "The mission URL uses http://, not https://.",
                                              "Serve the application over HTTPS and redirect HTTP traffic.")],
                           duration_ms=round((time.monotonic() - started) * 1000))
    decision = scope.check(target.raw, "web")
    if not decision.allowed:
        raise ProbeError(decision.reason)
    ip, _ = resolve_pinned(target)
    port = target.port or 443
    context = ssl.create_default_context()
    try:
        with socket.create_connection((ip, port), timeout=8.0) as raw:
            with context.wrap_socket(raw, server_hostname=target.host) as tls:
                cert = tls.getpeercert()
                protocol = tls.version()
                cipher = tls.cipher()
    except (OSError, ssl.SSLError) as exc:
        raise ProbeError(f"TLS probe failed: {type(exc).__name__}: {exc}") from None
    if not cert:
        raise ProbeError("No peer certificate returned.")
    not_after = ssl.cert_time_to_seconds(cert["notAfter"])
    days_left = int((not_after - time.time()) // 86400)
    san = [value for kind, value in cert.get("subjectAltName", ()) if kind == "DNS"][:30]
    findings = []
    if days_left < 0:
        findings.append(_finding("TLS-EXPIRED-001", "high", "TLS certificate expired",
                                 f"Certificate expired {abs(days_left)} days ago.",
                                 "Renew and deploy the certificate immediately."))
    elif days_left <= 14:
        findings.append(_finding("TLS-EXPIRING-001", "medium", "TLS certificate expires soon",
                                 f"Certificate expires in {days_left} days.",
                                 "Renew the certificate and verify automated renewal."))
    if protocol in {"TLSv1", "TLSv1.1", "SSLv3"}:
        findings.append(_finding("TLS-OLD-001", "high", "Legacy TLS protocol negotiated",
                                 f"Negotiated protocol: {protocol}.",
                                 "Disable legacy protocols and require TLS 1.2+."))
    return ProbeResult("tls", data={"protocol": protocol, "cipher": cipher[0] if cipher else "",
                                    "days_left": days_left, "not_after": cert["notAfter"],
                                    "san": san, "hostname_verified": True},
                       findings=findings, duration_ms=round((time.monotonic() - started) * 1000))


def _well_known(target: scope.Target, probe_id: str, path: str) -> ProbeResult:
    started = time.monotonic()
    try:
        observed = _request(target, path, method="GET", read_body=True)
    except ProbeError as exc:
        return ProbeResult(probe_id, status="error", error=str(exc),
                           duration_ms=round((time.monotonic() - started) * 1000))
    body = observed["body"]
    present = observed["status"] == 200 and bool(body.strip())
    data = {"path": path, "http_status": observed["status"], "present": present,
            "sha256": hashlib.sha256(body.encode()).hexdigest() if present else "",
            "lines": len(body.splitlines()) if present else 0,
            "excerpt": "\n".join(body.splitlines()[:12])[:1200] if present else ""}
    findings = []
    if probe_id == "security_txt" and not present:
        findings.append(_finding("WEB-SECTXT-001", "info", "security.txt not found",
                                 f"GET {path} returned HTTP {observed['status']}.",
                                 "Publish RFC 9116 security.txt with monitored contact and expiry fields.", "medium"))
    return ProbeResult(probe_id, data=data, findings=findings,
                       duration_ms=round((time.monotonic() - started) * 1000))


def probe_security_txt(target: scope.Target) -> ProbeResult:
    return _well_known(target, "security_txt", "/.well-known/security.txt")


def probe_robots(target: scope.Target) -> ProbeResult:
    return _well_known(target, "robots", "/robots.txt")


PROBES = {
    "dns": probe_dns, "http_headers": probe_http_headers, "tls": probe_tls,
    "security_txt": probe_security_txt, "robots": probe_robots,
}


def demo_results(profile: str = "web") -> list[dict[str, Any]]:
    """Deterministic offline fixture. Never touches DNS/network or live records."""
    results = [
        ProbeResult("dns", data={"host": "demo.ratansec.local", "addresses": ["192.0.2.10"],
                                 "families": ["IPv4"], "fixture": True}).view(),
        ProbeResult("http_headers", data={"status": 200, "headers": {"server": "nginx/1.25.3",
                    "content-type": "text/html", "x-frame-options": "SAMEORIGIN"},
                    "pinned_ip": "192.0.2.10", "method": "HEAD", "path": "/", "redirect_followed": False,
                    "fixture": True}, findings=[
            _finding("WEB-HSTS-001", "medium", "HSTS header missing",
                     "Fixture response has no Strict-Transport-Security header.",
                     "Add HSTS after validating HTTPS."),
            _finding("WEB-CSP-001", "medium", "Content Security Policy missing",
                     "Fixture response has no Content-Security-Policy header.",
                     "Deploy a restrictive CSP."),
            _finding("WEB-NOSNIFF-001", "low", "MIME sniffing protection missing",
                     "X-Content-Type-Options is not nosniff.", "Set X-Content-Type-Options: nosniff."),
            _finding("WEB-BANNER-001", "info", "Server version disclosed",
                     "Server header: nginx/1.25.3", "Minimize version disclosure.", "medium"),
        ]).view(),
        ProbeResult("tls", data={"protocol": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384",
                                 "days_left": 11, "not_after": "Nov 17 00:00:00 2026 GMT",
                                 "san": ["demo.ratansec.local"], "hostname_verified": True, "fixture": True},
                    findings=[_finding("TLS-EXPIRING-001", "medium", "TLS certificate expires soon",
                                       "Fixture certificate expires in 11 days.", "Renew and verify automation.")]).view(),
    ]
    if profile == "web":
        results.append(ProbeResult("security_txt", data={"path": "/.well-known/security.txt",
                       "http_status": 404, "present": False, "fixture": True},
                       findings=[_finding("WEB-SECTXT-001", "info", "security.txt not found",
                                          "Fixture GET returned HTTP 404.", "Publish RFC 9116 security.txt.", "medium")]).view())
        results.append(ProbeResult("robots", data={"path": "/robots.txt", "http_status": 200,
                       "present": True, "lines": 2, "excerpt": "User-agent: *\nDisallow: /admin",
                       "sha256": hashlib.sha256(b"User-agent: *\nDisallow: /admin").hexdigest(),
                       "fixture": True}).view())
    selected = PROFILES.get(profile, PROFILES["web"])["probes"]
    return [r for r in results if r["id"] in selected]

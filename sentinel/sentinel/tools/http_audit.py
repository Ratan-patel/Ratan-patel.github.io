"""HTTP security-header and transport audit for URLs you are authorized to test.

Read-only. Issues GET/HEAD, never submits forms, never follows a redirect off
scope, and never sends a payload.
"""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..scope import host_from_url
from .base import Finding, Tool, ToolContext, ToolResult

# Header -> (required?, why it matters, remediation)
HEADER_POLICY: dict[str, tuple[str, str, str]] = {
    "strict-transport-security": (
        "high",
        "Without HSTS a first request can be downgraded to plain HTTP and "
        "intercepted (sslstrip).",
        "Send `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`.",
    ),
    "content-security-policy": (
        "high",
        "No CSP means an injected script has no browser-side containment.",
        "Start with `default-src 'self'`, then tighten. Avoid `unsafe-inline`.",
    ),
    "x-content-type-options": (
        "medium",
        "Missing nosniff allows MIME-confusion attacks.",
        "Send `X-Content-Type-Options: nosniff`.",
    ),
    "x-frame-options": (
        "medium",
        "Absent framing controls enable clickjacking. CSP frame-ancestors also "
        "satisfies this.",
        "Send `X-Frame-Options: DENY` or CSP `frame-ancestors 'none'`.",
    ),
    "referrer-policy": (
        "low",
        "A permissive Referrer-Policy leaks full URLs, including tokens in query "
        "strings, to third parties.",
        "Send `Referrer-Policy: strict-origin-when-cross-origin` or tighter.",
    ),
    "permissions-policy": (
        "low",
        "Browser features (camera, geolocation, payment) are not restricted.",
        "Send a `Permissions-Policy` disabling features the app does not use.",
    ),
    "cross-origin-opener-policy": (
        "low",
        "Missing COOP weakens cross-origin isolation.",
        "Send `Cross-Origin-Opener-Policy: same-origin`.",
    ),
    "cross-origin-resource-policy": (
        "info",
        "CORP not set; cross-origin embedding is unrestricted.",
        "Send `Cross-Origin-Resource-Policy: same-origin` where assets are not "
        "meant to be embedded.",
    ),
}

DISCLOSURE_HEADERS = ("server", "x-powered-by", "x-aspnet-version",
                      "x-aspnetmvc-version", "x-generator", "x-drupal-cache",
                      "x-runtime", "via", "x-served-by")

_VERSION_IN_HEADER = re.compile(r"/\s*\d+(\.\d+)+", re.IGNORECASE)

CACHEABLE_VERBS_HINT = ("public", "private", "no-store", "max-age")


class HttpAudit(Tool):
    name = "http_audit"
    description = (
        "Audit the HTTP security posture of a URL you own or are authorized to "
        "test: security headers, cookie flags, TLS-on-redirect behaviour, "
        "information disclosure, CORS and caching. Read-only - issues GET/HEAD "
        "and never submits data."
    )
    kind = "url"
    schema = {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Absolute URL in scope, e.g. https://app.example.test",
            },
            "method": {"type": "string", "enum": ["GET", "HEAD", "OPTIONS"],
                       "description": "HTTP method. Default GET."},
            "follow_redirects": {
                "type": "boolean",
                "description": "Follow redirects, refusing any hop that leaves scope. Default true.",
            },
        },
        "required": ["target"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        target = str(args.get("target") or "").strip()
        decision = self.authorize(ctx, target)
        if not decision.allowed:
            return ctx.refuse(self.name, target, decision.reason, decision.rule)

        if not re.match(r"^https?://", target, re.IGNORECASE):
            target = "https://" + target

        method = str(args.get("method") or "GET").upper()
        if method not in ("GET", "HEAD", "OPTIONS"):
            method = "GET"
        follow = bool(args.get("follow_redirects", True))

        started = time.monotonic()
        hops: list[dict[str, Any]] = []
        final_status = 0
        final_headers: dict[str, str] = {}
        final_url = target
        body_sample = ""
        transport_error: str | None = None

        current = target
        for hop in range(6):
            ctx.limiter.wait()
            hop_decision = ctx.guard.check(current, kind="url")
            if not hop_decision.allowed:
                transport_error = (
                    f"redirect to {current!r} refused by guard "
                    f"({hop_decision.rule}): {hop_decision.reason}"
                )
                hops.append({"url": current, "refused": hop_decision.reason})
                break
            request = urllib.request.Request(
                current, method=method,
                headers={"User-Agent": ctx.user_agent, "Accept": "*/*"},
            )
            opener = urllib.request.build_opener(NoRedirect())
            try:
                with opener.open(request, timeout=ctx.timeout) as response:
                    final_status = response.status
                    final_headers = {k.lower(): v for k, v in response.getheaders()}
                    final_url = response.geturl()
                    if method != "HEAD" and final_status < 400:
                        try:
                            body_sample = response.read(65536).decode(
                                "utf-8", "replace")[:8192]
                        except Exception:
                            body_sample = ""
                    hops.append({"url": current, "status": final_status})
                    break
            except urllib.error.HTTPError as exc:
                final_status = exc.code
                final_headers = {k.lower(): v for k, v in (exc.headers or {}).items()}
                hops.append({"url": current, "status": exc.code})
                if exc.code in (301, 302, 303, 307, 308):
                    location = final_headers.get("location", "")
                    nxt = urllib.parse.urljoin(current, location)
                    if not follow:
                        break
                    if hop >= 5:
                        transport_error = "too many redirects (stopped at 6)"
                        break
                    current = nxt
                    continue
                try:
                    body_sample = exc.read(65536).decode("utf-8", "replace")[:8192]
                except Exception:
                    body_sample = ""
                break
            except urllib.error.URLError as exc:
                reason = getattr(exc, "reason", exc)
                transport_error = f"{type(reason).__name__}: {reason}"
                break
            except (ssl.SSLError, TimeoutError, OSError) as exc:
                transport_error = f"{type(exc).__name__}: {exc}"
                break

        findings: list[Finding] = []
        parsed = urllib.parse.urlparse(final_url)

        if transport_error and not final_headers:
            return ToolResult(
                tool=self.name, target=target, ok=False, error=transport_error,
                findings=findings,
                data={"hops": hops, "method": method},
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        if parsed.scheme == "http":
            findings.append(Finding(
                title="Site served over plain HTTP",
                severity="critical",
                detail=f"Final URL {final_url} is unencrypted; every header, cookie "
                       f"and body byte is observable on-path.",
                remediation="Serve over HTTPS only and redirect HTTP -> HTTPS with "
                            "a 301, then enable HSTS.",
                reference="https://owasp.org/www-project-web-security-testing-guide/",
            ))

        findings += self._header_findings(final_headers, parsed.scheme == "https")
        findings += self._cookie_findings(final_headers, parsed.scheme == "https")
        findings += self._disclosure_findings(final_headers)
        findings += self._cors_findings(final_headers)
        findings += self._caching_findings(final_headers, method)
        findings += self._method_findings(final_headers, method)

        if parsed.query:
            findings.append(Finding(
                title="Sensitive-looking data may be in the query string",
                severity="low",
                detail="Query strings land in server logs, proxies and the "
                       "Referer header.",
                remediation="Move tokens and identifiers into the request body or "
                            "headers.",
            ))

        score = score_headers(final_headers)
        return ToolResult(
            tool=self.name, target=target, ok=True, findings=findings,
            data={
                "method": method,
                "final_url": final_url,
                "status": final_status,
                "hops": hops,
                "headers": final_headers,
                "header_score": score,
                "transport_error": transport_error,
                "body_bytes_sampled": len(body_sample),
            },
            duration_ms=int((time.monotonic() - started) * 1000),
        )

    # ------------------------------------------------------------- analyses

    def _header_findings(self, headers: dict[str, str], secure: bool) -> list[Finding]:
        out: list[Finding] = []
        csp = headers.get("content-security-policy", "")
        frame_ancestors = "frame-ancestors" in csp.lower()
        for header, (severity, why, fix) in HEADER_POLICY.items():
            present = header in headers
            if header == "x-frame-options" and frame_ancestors:
                present = True
            if present:
                continue
            if header == "strict-transport-security" and not secure:
                continue  # HSTS on plain HTTP is meaningless; the HTTP finding covers it
            out.append(Finding(
                title=f"Missing security header: {header}",
                severity=severity, detail=why, remediation=fix,
                reference=f"https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/{header}",
            ))

        if csp:
            lowered = csp.lower()
            if "'unsafe-inline'" in lowered:
                out.append(Finding(
                    title="CSP allows 'unsafe-inline'",
                    severity="medium",
                    detail="Inline script/style is permitted, so CSP will not stop "
                           "an injected script tag.",
                    remediation="Move to nonces or hashes and drop 'unsafe-inline'.",
                    reference="https://content-security-policy.com/unsafe-inline/",
                ))
            if "'unsafe-eval'" in lowered:
                out.append(Finding(
                    title="CSP allows 'unsafe-eval'",
                    severity="medium",
                    detail="eval()-style execution is permitted.",
                    remediation="Remove 'unsafe-eval'; refactor code that needs it.",
                ))
            if re.search(r"(default-src|script-src)\s+[^;]*\*", lowered):
                out.append(Finding(
                    title="CSP uses a wildcard source",
                    severity="high",
                    detail="A `*` source lets any origin supply scripts.",
                    remediation="Enumerate the exact origins you need.",
                ))
        if "x-powered-by" in headers or _VERSION_IN_HEADER.search(
                headers.get("server", "")):
            out.append(Finding(
                title="Exact software version disclosed",
                severity="low",
                detail=f"server={headers.get('server','')!r} "
                       f"x-powered-by={headers.get('x-powered-by','')!r}",
                remediation="Strip version strings at the proxy/app layer.",
            ))
        return out

    def _cookie_findings(self, headers: dict[str, str], secure: bool) -> list[Finding]:
        out: list[Finding] = []
        raw = headers.get("set-cookie", "")
        if not raw:
            return out
        for cookie in raw.split(","):
            lowered = cookie.lower()
            name = cookie.split("=", 1)[0].strip()[:40]
            if "secure" not in lowered:
                # Reported regardless of scheme: it is actionable both ways -
                # over HTTP the cookie is already exposed, over HTTPS it can
                # still leak on any downgrade or stray http:// link.
                out.append(Finding(
                    title=f"Cookie '{name}' missing the Secure flag",
                    severity="critical" if not secure else "high",
                    detail="The cookie can be sent over an unencrypted connection."
                           + ("" if secure else " This response is already plain "
                              "HTTP, so the cookie is exposed today."),
                    remediation="Set `Secure` on every session cookie, and serve "
                                "the site over HTTPS only.",
                ))
            if "httponly" not in lowered:
                out.append(Finding(
                    title=f"Cookie '{name}' missing HttpOnly",
                    severity="medium",
                    detail="Client-side script can read this cookie.",
                    remediation="Set `HttpOnly` unless JS genuinely needs it.",
                ))
            if "samesite" not in lowered:
                out.append(Finding(
                    title=f"Cookie '{name}' missing SameSite",
                    severity="medium",
                    detail="Cross-site requests will carry this cookie (CSRF risk).",
                    remediation="Set `SameSite=Lax` or `Strict`.",
                ))
        return out

    def _disclosure_findings(self, headers: dict[str, str]) -> list[Finding]:
        out: list[Finding] = []
        leaked = {h: headers[h] for h in DISCLOSURE_HEADERS if h in headers}
        if leaked:
            out.append(Finding(
                title="Technology-disclosure headers present",
                severity="info",
                detail=f"{json.dumps(leaked)}",
                remediation="Remove stack/version headers; they speed up attacker "
                            "targeting and reveal patch lag.",
                evidence=leaked,
            ))
        return out

    def _cors_findings(self, headers: dict[str, str]) -> list[Finding]:
        out: list[Finding] = []
        origin = headers.get("access-control-allow-origin", "")
        credentials = headers.get("access-control-allow-credentials", "").lower()
        if origin == "*" and credentials == "true":
            out.append(Finding(
                title="CORS wildcard combined with credentials",
                severity="critical",
                detail="Browsers reject `*` with credentials, but reflecting an "
                       "arbitrary Origin with credentials is the same class of bug.",
                remediation="Allowlist specific origins; never echo the request "
                            "Origin unvalidated.",
            ))
        elif origin and origin not in ("*", "null") and credentials == "true":
            out.append(Finding(
                title="CORS reflects a specific origin with credentials",
                severity="medium",
                detail=f"access-control-allow-origin: {origin}",
                remediation="Verify the origin is on an explicit allowlist rather "
                            "than echoed from the request.",
            ))
        elif origin == "null":
            out.append(Finding(
                title="CORS allows the 'null' origin",
                severity="high",
                detail="Sandboxed iframes and file:// pages send Origin: null.",
                remediation="Never allowlist 'null'.",
            ))
        methods = headers.get("access-control-allow-methods", "").upper()
        if methods and any(m.strip() in methods for m in ("PUT", "DELETE", "TRACE")):
            out.append(Finding(
                title="CORS permits state-changing methods",
                severity="low",
                detail=f"access-control-allow-methods: {methods}",
                remediation="Restrict to the verbs the API actually needs.",
            ))
        return out

    def _caching_findings(self, headers: dict[str, str], method: str) -> list[Finding]:
        out: list[Finding] = []
        control = headers.get("cache-control", "").lower()
        pragma = headers.get("pragma", "").lower()
        if method == "GET" and control and "no-store" not in control \
                and "private" not in control and "no-cache" not in control:
            if "public" in control and headers.get("set-cookie"):
                out.append(Finding(
                    title="Authenticated response marked cacheable as public",
                    severity="high",
                    detail=f"cache-control: {control} with a Set-Cookie header. "
                           f"Shared caches may store per-user content.",
                    remediation="Use `Cache-Control: private, no-store` on "
                                "authenticated responses.",
                ))
        if not control and not pragma and headers.get("set-cookie"):
            out.append(Finding(
                title="No Cache-Control on a response that sets cookies",
                severity="medium",
                detail="Intermediary caches may retain session material.",
                remediation="Send `Cache-Control: no-store`.",
            ))
        return out

    def _method_findings(self, headers: dict[str, str], method: str) -> list[Finding]:
        out: list[Finding] = []
        allow = headers.get("allow", "").upper()
        if method == "OPTIONS" and allow:
            for risky in ("TRACE", "TRACK", "PUT", "DELETE", "CONNECT"):
                if risky in allow:
                    out.append(Finding(
                        title=f"Server advertises the {risky} method",
                        severity="high" if risky in ("TRACE", "TRACK") else "medium",
                        detail=f"Allow: {allow}. TRACE/TRACK enable cross-site "
                               f"tracing; write methods should be scoped per route.",
                        remediation="Disable TRACE/TRACK at the server; restrict "
                                    "write verbs to authenticated routes.",
                    ))
        return out


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Stop urllib from silently following redirects so each hop can be checked."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def score_headers(headers: dict[str, str]) -> dict[str, Any]:
    """0-100 weighted score over the header policy."""
    weights = {"high": 25, "medium": 12, "low": 6, "info": 2}
    total = 0
    earned = 0
    detail: dict[str, bool] = {}
    csp = headers.get("content-security-policy", "")
    frame_ancestors = "frame-ancestors" in csp.lower()
    for header, (severity, _, _) in HEADER_POLICY.items():
        total += weights[severity]
        present = header in headers or (header == "x-frame-options" and frame_ancestors)
        detail[header] = present
        if present:
            earned += weights[severity]
    pct = round(100 * earned / total) if total else 0
    return {"score": pct, "present": detail, "weighted_max": total, "weighted_got": earned}


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):  # pragma: no cover
    pass

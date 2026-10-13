"""Passive attack-surface review for domains you own or are authorized to test.

Two halves:
  * exposure hygiene on the apex - robots.txt, sitemap.xml, security.txt,
    .well-known/*, .env-style leftovers, directory listings. All plain GETs to
    URLs already inside scope.
  * Certificate-Transparency subdomain discovery via crt.sh, which is a public
    read-only log. This is *enumeration of names that already appear in public
    logs* - not brute-forcing, and not probing the discovered hosts. Discovered
    names are reported so you can decide what to authorize next.
"""

from __future__ import annotations

import hashlib
import json
import re
import ssl
import uuid
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..scope import host_from_url
from .base import Finding, Tool, ToolContext, ToolResult

CRTSH_URL = "https://crt.sh/?q=%25.{domain}&output=json"

EXPOSURE_PROBES: list[tuple[str, str, str]] = [
    ("/.env", "Environment file exposed",
     "A committed or served .env usually contains live credentials. Remove it "
     "from the web root, rotate everything inside it, and add it to .gitignore."),
    ("/.git/config", "Git metadata reachable over HTTP",
     "Serving .git lets anyone reconstruct your source with `git clone "
     "https://host/.git`. Block /.git/ at the server."),
    ("/.git/HEAD", "Git metadata reachable over HTTP",
     "Block /.git/ entirely."),
    ("/.svn/entries", "SVN metadata reachable over HTTP",
     "Block /.svn/ at the server."),
    ("/.DS_Store", "macOS directory metadata exposed",
     "Reveals filenames that are otherwise unlinked. Delete and block."),
    ("/web.config", "ASP.NET configuration exposed",
     "Contains connection strings and machine keys. Block it."),
    ("/config.json", "Application configuration exposed",
     "Check for credentials and internal URLs; restrict access."),
    ("/backup.sql", "Database dump exposed",
     "Remove any dump from a web-accessible path and rotate the credentials in it."),
    ("/dump.sql", "Database dump exposed",
     "Remove any dump from a web-accessible path and rotate the credentials in it."),
    ("/db.sqlite3", "SQLite database exposed",
     "Common Django misconfiguration. Move the database outside the web root."),
    ("/phpinfo.php", "phpinfo() exposed",
     "Leaks paths, environment variables and loaded modules. Delete it."),
    ("/server-status", "Apache mod_status exposed",
     "Reveals active requests, client IPs and internal URLs. Restrict to "
     "localhost."),
    ("/.aws/credentials", "Cloud credentials exposed",
     "Rotate the access key immediately and block the path."),
    ("/id_rsa", "SSH private key exposed",
     "Rotate the keypair on every host that trusts it."),
    ("/.ssh/id_rsa", "SSH private key exposed",
     "Rotate the keypair on every host that trusts it."),
    ("/wp-config.php.bak", "WordPress configuration backup exposed",
     "Contains DB credentials and auth salts. Delete and rotate."),
    ("/.well-known/security.txt", "security.txt present",
     "Good practice - a published contact path for researchers."),
    ("/robots.txt", "robots.txt present",
     "Review it: Disallow entries advertise paths you would rather nobody knew."),
    ("/sitemap.xml", "sitemap.xml present",
     "Review for URLs that should not be public."),
    ("/crossdomain.xml", "Flash crossdomain policy",
     "A permissive crossdomain.xml allowed legacy Flash-based cross-origin data "
     "theft. Remove it."),
    ("/clientaccesspolicy.xml", "Silverlight cross-domain policy",
     "Remove unless a legacy Silverlight client genuinely needs it."),
    ("/.htaccess", "Apache configuration exposed",
     "Block dotfiles at the server level."),
    ("/.htpasswd", "Apache password file exposed",
     "Contains hashed credentials. Delete, block dotfiles, and reset the accounts."),
    ("/elmah.axd", "ELMAH error log exposed",
     "Leaks stack traces and connection strings. Restrict it."),
    ("/actuator/env", "Spring Boot actuator exposed",
     "Actuator endpoints commonly disclose environment variables, heap dumps and "
     "credentials. Require authentication on /actuator/*."),
    ("/actuator/heapdump", "Spring Boot heap dump exposed",
     "A heap dump contains in-memory secrets. Never expose it."),
    ("/debug/pprof/", "Go pprof endpoint exposed",
     "pprof leaks goroutine stacks, memory and CPU profiles. Bind it to an "
     "internal interface."),
    ("/metrics", "Prometheus metrics exposed",
     "Metrics reveal traffic patterns, internal service names and error rates. "
     "Require authentication."),
    ("/graphql", "GraphQL endpoint present",
     "Confirm introspection is disabled in production and that query depth/"
     "complexity limits are configured."),
    ("/swagger.json", "OpenAPI specification exposed",
     "The spec enumerates every route and parameter. Confirm this exposure is "
     "intentional."),
    ("/openapi.json", "OpenAPI specification exposed",
     "Confirm the exposure is intentional and that no internal-only routes are "
     "described."),
    ("/api/docs", "API documentation exposed",
     "Confirm this is meant to be public."),
    ("/console", "Debug console exposed",
     "Werkzeug/Spring/other consoles frequently allow code execution. Remove."),
    ("/trace", "Request trace endpoint exposed", "Remove or authenticate it."),
    ("/solr/", "Apache Solr admin exposed",
     "Unauthenticated Solr allows data exfiltration and, historically, RCE."),
    ("/jenkins/", "Jenkins exposed",
     "Jenkins builds run shell commands; never expose it unauthenticated."),
    ("/.well-known/change-password", "change-password well-known present",
     "Good practice."),
]

SENSITIVE_IN_ROBOTS = re.compile(
    r"(?i)Disallow:\s*(\S*(admin|backup|internal|private|secret|staging|dev|"
    r"config|db|sql|phpmyadmin|wp-admin|\.env|\.git)\S*)")


class SurfaceAudit(Tool):
    name = "surface_audit"
    description = (
        "Passive attack-surface review of a web origin or domain you own: check "
        "for exposed configuration/backup/debug paths, read robots.txt, "
        "security.txt and sitemap.xml, and enumerate subdomains that already "
        "appear in public Certificate Transparency logs. Issues plain GETs "
        "only - no brute-forcing, no exploitation, no probing of hosts that are "
        "not themselves in scope."
    )
    kind = "url"
    schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string",
                       "description": "Base URL or domain in scope, e.g. "
                                      "https://app.example.test"},
            "paths": {
                "type": "boolean",
                "description": "Probe the well-known exposure path list. Default true.",
            },
            "ct_subdomains": {
                "type": "boolean",
                "description": "Look up subdomains in crt.sh Certificate "
                               "Transparency logs. Default true.",
            },
        },
        "required": ["target"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        target = str(args.get("target") or "").strip()
        decision = self.authorize(ctx, target)
        if not decision.allowed:
            return ctx.refuse(self.name, target, decision.reason, decision.rule)

        base = target if re.match(r"^https?://", target, re.IGNORECASE) \
            else "https://" + target
        base = base.rstrip("/")
        domain = host_from_url(base) or ""

        findings: list[Finding] = []
        data: dict[str, Any] = {"base": base, "domain": domain, "paths": {},
                                "ct": {}, "baseline": None}

        if args.get("paths", True):
            # Calibrate first: many servers answer *every* path with 200 and a
            # generic page. Without this, a catch-all produces dozens of false
            # "credentials exposed" CRITICALs and the report becomes noise.
            baseline = self._calibrate(base, ctx, data)
            findings += self._probe_paths(base, ctx, data, baseline)

        if args.get("ct_subdomains", True) and domain:
            findings += self._ct_lookup(domain, ctx, data)

        return ToolResult(tool=self.name, target=base, ok=True,
                          findings=findings, data=data)

    # ------------------------------------------------------------- internals

    def _get(self, url: str, ctx: ToolContext) -> tuple[int, dict[str, str], str]:
        ctx.limiter.wait()
        request = urllib.request.Request(
            url, method="GET",
            headers={"User-Agent": ctx.user_agent, "Accept": "*/*"},
        )
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(request, timeout=ctx.timeout) as response:
                body = response.read(200_000).decode("utf-8", "replace")
                return (response.status,
                        {k.lower(): v for k, v in response.getheaders()}, body)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read(200_000).decode("utf-8", "replace")
            except Exception:
                body = ""
            return exc.code, {k.lower(): v for k, v in (exc.headers or {}).items()}, body
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise LookupError(f"{type(reason).__name__}: {reason}") from exc
        except (ssl.SSLError, TimeoutError, OSError) as exc:
            raise LookupError(f"{type(exc).__name__}: {exc}") from exc

    def _calibrate(self, base: str, ctx: ToolContext,
                   data: dict[str, Any]) -> "Baseline":
        """Learn what this server's 'nothing here' response looks like."""
        baseline = Baseline()
        probes = [
            f"/sentinel-nonexistent-{uuid.uuid4().hex[:12]}",
            f"/{uuid.uuid4().hex[:10]}/also-missing-{uuid.uuid4().hex[:6]}",
        ]
        for path in probes:
            url = base + path
            if not ctx.guard.check(url, kind="url").allowed:
                continue
            try:
                status, headers, body = self._get(url, ctx)
            except LookupError:
                continue
            baseline.add(status, headers, body)
        data["baseline"] = baseline.describe()
        return baseline

    def _probe_paths(self, base: str, ctx: ToolContext, data: dict[str, Any],
                     baseline: "Baseline | None" = None) -> list[Finding]:
        out: list[Finding] = []
        soft_suppressed: list[str] = []
        reachable_error: str | None = None
        for path, title, remediation in EXPOSURE_PROBES:
            url = base + path
            hop = ctx.guard.check(url, kind="url")
            if not hop.allowed:
                continue
            try:
                status, headers, body = self._get(url, ctx)
            except LookupError as exc:
                reachable_error = str(exc)
                break

            data["paths"][path] = {"status": status,
                                   "content_type": headers.get("content-type", ""),
                                   "bytes": len(body)}
            interesting = status in (200, 401, 403, 500) and path not in (
                "/robots.txt", "/sitemap.xml")
            status_note = str(status)
            if interesting and baseline is not None and baseline.matches(
                    status, headers, body):
                # Same status + same body as a path that definitely does not
                # exist => the server answers everything identically.
                status_note = f"{status} (soft - identical to a known-missing path)"
                interesting = False
                soft_suppressed.append(path)
            elif status == 200 and self._looks_like_soft_200(body, headers):
                status_note = "200 (soft - SPA/error page)"
                interesting = False
                soft_suppressed.append(path)

            if interesting:
                severity = "critical" if any(
                    token in path for token in
                    (".env", ".git", "id_rsa", "credentials", ".sql", "heapdump",
                     "wp-config", "phpinfo", ".htpasswd", "sqlite", "config.json")
                ) else "high" if status == 200 else "medium"
                if path in ("/.well-known/security.txt",
                            "/.well-known/change-password"):
                    severity = "info"
                    title = "security.txt published (good)"
                out.append(Finding(
                    title=f"{title}: {path} -> {status_note}",
                    severity=severity,
                    detail=f"{url} returned HTTP {status_note}, "
                           f"{len(body)} bytes, "
                           f"content-type {headers.get('content-type','?')}.",
                    remediation=remediation,
                    evidence={"url": url, "status": status,
                              "preview": _safe_preview(body, path)},
                ))

            if path == "/robots.txt" and status == 200 and body:
                out += self._robots_findings(base, body)
            if path == "/.well-known/security.txt" and status == 200 and body:
                out += self._securitytxt_findings(body)
            if path == "/crossdomain.xml" and status == 200 and body:
                if 'domain="*"' in body:
                    out.append(Finding(
                        title="crossdomain.xml allows all origins",
                        severity="high",
                        detail="<allow-access-from domain=\"*\"/> grants any site "
                               "cross-origin data access to legacy clients.",
                        remediation="Delete the file or restrict to explicit domains.",
                    ))

        if soft_suppressed:
            data["soft_200_suppressed"] = soft_suppressed
            out.append(Finding(
                title=f"{len(soft_suppressed)} probe(s) answered with the server's "
                      f"generic response",
                severity="info",
                detail="These paths returned the same status and body as a "
                       "deliberately non-existent URL, so the server is answering "
                       "everything alike (a catch-all route, an SPA, or a soft "
                       "404). They are NOT reported as exposures: "
                       + ", ".join(soft_suppressed[:40]),
                remediation="Nothing to fix - this is calibration working. If one "
                            "of these paths really does serve a sensitive file, "
                            "make its response differ from your 404 page and "
                            "re-run.",
            ))

        if reachable_error and not data["paths"]:
            out.append(Finding(
                title="Origin unreachable",
                severity="info",
                detail=f"Could not fetch {base}: {reachable_error}",
                remediation="Confirm the host is up, that it serves HTTPS on 443, "
                            "and that this machine has a route to it.",
            ))
        return out

    @staticmethod
    def _looks_like_soft_200(body: str, headers: dict[str, str]) -> bool:
        """SPAs and misconfigured servers return 200 for everything. Detect that."""
        content_type = headers.get("content-type", "").lower()
        lowered = body[:4000].lower()
        if "text/html" not in content_type and content_type:
            return False
        markers = ("<!doctype html", "<html", "<div id=\"app\"", "<div id=\"root\"",
                   "page not found", "404", "not found", "spa", "react", "vue")
        hits = sum(1 for marker in markers if marker in lowered)
        return hits >= 2 and len(body) < 20_000

    def _robots_findings(self, base: str, body: str) -> list[Finding]:
        out: list[Finding] = []
        matches = SENSITIVE_IN_ROBOTS.findall(body)
        if matches:
            paths = sorted({m[0] for m in matches})[:25]
            out.append(Finding(
                title="robots.txt discloses sensitive paths",
                severity="medium",
                detail="Disallow entries are public hints. Found: " + ", ".join(paths),
                remediation="Robots is not access control. Require authentication "
                            "on these paths and stop advertising them.",
                evidence={"paths": paths},
            ))
        if re.search(r"(?i)^\s*User-agent:\s*\*\s*$", body, re.MULTILINE) and \
                not re.search(r"(?i)^\s*Disallow:", body, re.MULTILINE):
            out.append(Finding(
                title="robots.txt allows all crawling",
                severity="info",
                detail="No Disallow rules - everything is indexable.",
                remediation="Intentional for public content; otherwise add rules.",
            ))
        sitemap = re.search(r"(?i)^\s*Sitemap:\s*(\S+)", body, re.MULTILINE)
        if sitemap:
            url = sitemap.group(1)
            if not url.startswith(base):
                out.append(Finding(
                    title="robots.txt points at an off-origin sitemap",
                    severity="low",
                    detail=f"Sitemap: {url}",
                    remediation="Confirm that host is yours; a hijacked sitemap "
                                "line is a SEO-poisoning vector.",
                ))
        return out

    def _securitytxt_findings(self, body: str) -> list[Finding]:
        out: list[Finding] = []
        expires = re.search(r"(?i)^\s*Expires:\s*(.+)$", body, re.MULTILINE)
        contact = re.search(r"(?i)^\s*Contact:\s*(.+)$", body, re.MULTILINE)
        if not contact:
            out.append(Finding(
                title="security.txt has no Contact field",
                severity="low",
                detail="RFC 9116 requires at least one Contact.",
                remediation="Add `Contact: mailto:security@<your-domain>`.",
                reference="https://datatracker.ietf.org/doc/html/rfc9116",
            ))
        if not expires:
            out.append(Finding(
                title="security.txt has no Expires field",
                severity="low",
                detail="RFC 9116 requires Expires; without it researchers cannot "
                       "tell whether the contact is still staffed.",
                remediation="Add `Expires: <ISO-8601 date ~1 year out>`.",
            ))
        return out

    def _ct_lookup(self, domain: str, ctx: ToolContext,
                   data: dict[str, Any]) -> list[Finding]:
        out: list[Finding] = []
        url = CRTSH_URL.format(domain=urllib.parse.quote(domain))
        ctx.limiter.wait()
        request = urllib.request.Request(
            url, headers={"User-Agent": ctx.user_agent, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=ctx.timeout + 15) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                OSError, json.JSONDecodeError) as exc:
            data["ct"]["error"] = f"{type(exc).__name__}: {exc}"
            out.append(Finding(
                title="Certificate Transparency lookup unavailable",
                severity="info",
                detail=f"crt.sh did not respond for {domain}: {exc}. "
                       f"This is a network/service issue, not a finding about "
                       f"your domain.",
                remediation="Retry later, or use your CA's own CT log search.",
            ))
            return out

        names: set[str] = set()
        for entry in payload if isinstance(payload, list) else []:
            for raw in str(entry.get("name_value", "")).splitlines():
                candidate = raw.strip().lower().lstrip("*.")
                if candidate and candidate.endswith(domain) and " " not in candidate:
                    names.add(candidate)
        wildcard = {n for n in names if n.startswith("*.")}
        names -= wildcard
        subdomains = sorted(n for n in names if n != domain)
        data["ct"] = {"count": len(subdomains), "subdomains": subdomains[:400],
                      "wildcard_entries": sorted(wildcard)[:20]}

        if subdomains:
            risky = [n for n in subdomains if re.search(
                r"(?i)(dev|stage|staging|test|uat|qa|internal|admin|old|beta|"
                r"preview|sandbox|debug|jenkins|git|vpn|bastion|db|api-v1)", n)]
            out.append(Finding(
                title=f"{len(subdomains)} subdomains present in CT logs",
                severity="info",
                detail="These names appear in public Certificate Transparency "
                       "logs and are therefore visible to anyone.\n"
                       + ", ".join(subdomains[:60])
                       + (" ..." if len(subdomains) > 60 else ""),
                remediation="Confirm each is still wanted. Decommissioned "
                            "subdomains whose DNS or backing service is gone are "
                            "subdomain-takeover candidates.",
                evidence={"subdomains": subdomains[:400]},
            ))
            if risky:
                out.append(Finding(
                    title=f"{len(risky)} non-production subdomains publicly visible",
                    severity="medium",
                    detail="Staging/dev/admin hosts are routinely less hardened "
                           "than production, and CT logs make them trivial to "
                           "find.\n" + ", ".join(risky[:40]),
                    remediation="Put non-production hosts behind authentication or "
                                "a VPN, use certificates that do not log the name "
                                "(an internal CA), or remove them.",
                    evidence={"subdomains": risky[:100]},
                ))
            if wildcard:
                out.append(Finding(
                    title="Wildcard certificate in CT logs",
                    severity="info",
                    detail=f"Wildcard entries: {sorted(wildcard)[:10]}. A wildcard "
                           f"certificate means any name under the domain will "
                           f"present a trusted cert - so a single dangling DNS "
                           f"record becomes a takeover with valid TLS.",
                    remediation="Prefer per-name certificates, or ensure no "
                                "dangling CNAMEs exist under the wildcard.",
                ))
        return out


def _safe_preview(body: str, path: str) -> str:
    """A short, redacted preview. Secret-looking values are fingerprinted."""
    from .secrets_audit import fingerprint

    snippet = body[:600]
    def _redact(match: re.Match[str]) -> str:
        return f"<redacted {fingerprint(match.group(0))}>"
    snippet = re.sub(
        r"(?i)(?:api[_\-]?key|secret|token|password|passwd|pwd)"
        r"['\"\s]*[:=]['\"\s]*([^\s'\"]{6,})",
        _redact, snippet)
    snippet = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*", "<private key omitted>",
                     snippet)
    return snippet[:600]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


class Baseline:
    """What a server's 'nothing here' response looks like.

    Matches on (status, body hash) exactly, and additionally on near-identical
    bodies - servers that stamp a timestamp or request id into an error page
    would otherwise defeat an exact hash.
    """

    def __init__(self, similarity_threshold: float = 0.90) -> None:
        self.samples: list[tuple[int, str, int, str]] = []   # status, hash, len, head
        self.statuses: set[int] = set()
        self.similarity_threshold = similarity_threshold

    def add(self, status: int, headers: dict[str, str], body: str) -> None:
        digest = hashlib.sha256(body.encode("utf-8", "replace")).hexdigest()
        self.samples.append((status, digest, len(body), body[:512]))
        self.statuses.add(status)

    @property
    def empty(self) -> bool:
        return not self.samples

    def matches(self, status: int, headers: dict[str, str], body: str) -> bool:
        if not self.samples:
            return False
        digest = hashlib.sha256(body.encode("utf-8", "replace")).hexdigest()
        for sample_status, sample_hash, sample_len, sample_head in self.samples:
            if sample_status != status:
                continue
            if sample_hash == digest:
                return True
            if sample_len == 0 and len(body) == 0:
                return True
            if sample_len and abs(sample_len - len(body)) / max(sample_len, 1) > 0.10:
                continue
            if _similarity(sample_head, body[:512]) >= self.similarity_threshold:
                return True
        return False

    def describe(self) -> dict[str, Any]:
        return {
            "samples": len(self.samples),
            "statuses": sorted(self.statuses),
            "body_hashes": [s[1][:16] for s in self.samples],
            "body_lengths": [s[2] for s in self.samples],
        }


def _similarity(left: str, right: str) -> float:
    """Cheap token Jaccard similarity - no difflib cost on every probe."""
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    a = set(left.lower().split())
    b = set(right.lower().split())
    if not a or not b:
        return 1.0 if left == right else 0.0
    return len(a & b) / len(a | b)

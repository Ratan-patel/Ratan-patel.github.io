"""Secret and sensitive-data detection in files you own.

Pattern matching plus Shannon-entropy scoring. Read-only: files are never
transmitted anywhere. The tool reports *where* a secret is and a redacted
fingerprint of it, never the secret itself - so the output is safe to paste into
a ticket or a report.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from pathlib import Path
from typing import Any

from .base import Finding, Tool, ToolContext, ToolResult

# (id, regex, severity, what to do)
SECRET_PATTERNS: list[tuple[str, re.Pattern[str], str, str]] = [
    ("aws-access-key-id",
     re.compile(r"\b(A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA|ANPA|ANVA|AROA)[A-Z0-9]{16}\b"),
     "critical",
     "Rotate the key in IAM now, then remove it. Check CloudTrail for use since "
     "the commit that introduced it."),
    ("aws-secret-access-key",
     re.compile(r"""(?i)aws[_\-\.]?secret[_\-\.]?access[_\-\.]?key['"\s:=]+"""
                r"""['"]?([A-Za-z0-9/+=]{40})['"]?"""),
     "critical",
     "Rotate immediately. An access-key id plus secret is full API access."),
    ("gcp-api-key",
     re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
     "critical",
     "Regenerate in the Google Cloud console and add API restrictions."),
    ("gcp-service-account",
     re.compile(r'"type"\s*:\s*"service_account"'),
     "critical",
     "A service-account JSON is committed. Revoke the key, delete the file, and "
     "mount credentials at runtime instead."),
    ("github-token",
     re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
     "critical",
     "Revoke at github.com/settings/tokens. Classic tokens grant repo-wide access."),
    ("github-fine-grained",
     re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,255}\b"),
     "critical", "Revoke the fine-grained PAT and reissue with least privilege."),
    ("gitlab-token",
     re.compile(r"\bglpat-[A-Za-z0-9\-_]{20,}\b"),
     "critical", "Revoke in GitLab > Access Tokens."),
    ("slack-token",
     re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
     "critical", "Revoke/regenerate in the Slack app config."),
    ("slack-webhook",
     re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+"),
     "high", "Delete the incoming webhook; anyone holding the URL can post as you."),
    ("stripe-live-secret",
     re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"),
     "critical",
     "Roll the live secret key in Stripe immediately and review recent charges."),
    ("stripe-live-publishable",
     re.compile(r"\bpk_live_[A-Za-z0-9]{16,}\b"),
     "info", "Publishable keys are meant to be public, but confirm it is not paired "
             "with a leaked secret key."),
    ("stripe-restricted",
     re.compile(r"\brk_live_[A-Za-z0-9]{16,}\b"),
     "critical", "Roll this restricted key."),
    ("square-access-token",
     re.compile(r"\bsq0atp-[A-Za-z0-9\-_]{22}\b"),
     "critical", "Revoke in the Square dashboard."),
    ("twilio-api-key",
     re.compile(r"\bSK[0-9a-fA-F]{32}\b"),
     "high", "Delete the Twilio API key."),
    ("sendgrid-api-key",
     re.compile(r"\bSG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}\b"),
     "critical", "Revoke the SendGrid key."),
    ("mailgun-api-key",
     re.compile(r"\bkey-[0-9a-zA-Z]{32}\b"),
     "high", "Rotate the Mailgun API key."),
    ("mailchimp-api-key",
     re.compile(r"\b[0-9a-f]{32}-us\d{1,2}\b"),
     "high", "Rotate the Mailchimp key."),
    ("npm-token",
     re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"),
     "critical", "Revoke the npm automation token - it can publish packages."),
    ("pypi-token",
     re.compile(r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9\-_]{30,}\b"),
     "critical", "Revoke the PyPI API token."),
    ("heroku-api-key",
     re.compile(r"""(?i)heroku[_\-\.]?api[_\-\.]?key['"\s:=]+['"]?"""
                r"""([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"""
                r"""[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"""),
     "high", "Rotate the Heroku API key."),
    ("openai-api-key",
     re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9\-_]{20,}\b"),
     "critical",
     "Revoke at platform.openai.com/api-keys. Note: `sk-proj-` keys are scoped to "
     "a project but still billable."),
    ("anthropic-api-key",
     re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b"),
     "critical", "Revoke in the Anthropic console."),
    ("telegram-bot-token",
     re.compile(r"\b\d{8,10}:AA[A-Za-z0-9\-_]{33,}\b"),
     "high", "Revoke via @BotFather /token."),
    ("discord-bot-token",
     re.compile(r"\b[MN][A-Za-z0-9]{23,}\.[A-Za-z0-9\-_]{6}\.[A-Za-z0-9\-_]{25,}\b"),
     "critical", "Reset the Discord bot token."),
    ("discord-webhook",
     re.compile(r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w\-]+"),
     "high", "Delete the webhook."),
    ("jwt",
     re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"),
     "high",
     "A signed JWT is committed. Even an expired one reveals the claims schema and "
     "signing algorithm; rotate the signing key."),
    ("private-key-block",
     re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY"),
     "critical",
     "A private key is committed. Revoke the certificate, generate a new keypair, "
     "and treat every signature made with it as suspect."),
    ("ssh-public-key-material",
     re.compile(r"\bssh-(?:rsa|ed25519|dss)\s+[A-Za-z0-9+/=]{60,}"),
     "info",
     "Public key material. Not secret on its own, but confirms which keys are in "
     "circulation."),
    ("database-url-with-password",
     re.compile(r"""\b(?:postgres(?:ql)?|mysql|mssql|mongodb(?:\+srv)?|redis|amqp)"""
                r"""://[^:/@\s]+:([^@\s/]{3,})@[^/\s]+"""),
     "critical",
     "A connection string with an inline password is committed. Rotate the "
     "credential and load it from a secret manager or environment."),
    ("generic-api-key-assignment",
     re.compile(r"""(?i)\b(?:api[_\-]?key|apikey|secret[_\-]?key|auth[_\-]?token|"""
                r"""access[_\-]?token|client[_\-]?secret|password|passwd|pwd)"""
                r"""\b['"]?\s*[:=]\s*['"]([^'"\s]{12,})['"]"""),
     "medium",
     "Looks like a hardcoded credential. If it is real, move it to a secret "
     "manager and rotate it."),
    ("basic-auth-in-url",
     re.compile(r"\bhttps?://[^:/@\s]+:([^@\s/]{3,})@[^\s'\"]+"),
     "high",
     "Credentials embedded in a URL end up in logs, browser history and the "
     "Referer header."),
    ("azure-storage-account-key",
     re.compile(r"""(?i)AccountKey=([A-Za-z0-9+/=]{60,})"""),
     "critical", "Rotate the Azure Storage account key."),
    ("azure-ad-client-secret",
     re.compile(r"\b[0-9a-zA-Z\-_]{2}\.[0-9A-Za-z\-_]{20,}\.[0-9A-Za-z\-_]{20,}\b"),
     "medium",
     "Possible Azure AD / Entra client secret. Verify and rotate if real."),
    ("shopify-token",
     re.compile(r"\bshp(?:at|ca|pa)_[A-Za-z0-9]{20,}\b"),
     "critical", "Revoke the Shopify token."),
    ("datadog-api-key",
     re.compile(r"\b[a-f0-9]{32}\b(?=[\s'\"]*(?:#|\bdatadog\b))"),
     "medium", "Possible Datadog API key."),
    ("google-oauth-client-secret",
     re.compile(r"\bGOCSPX-[A-Za-z0-9\-_]{20,}\b"),
     "critical", "Reset the OAuth client secret."),
    ("age-secret-key",
     re.compile(r"\bAGE-SECRET-KEY-1[A-Z0-9]{58}\b"),
     "critical", "Regenerate the age keypair."),
    ("supabase-key",
     re.compile(r"\bsbp_[A-Za-z0-9]{30,}\b"),
     "high", "Rotate the Supabase secret key."),
    ("linear-api-key",
     re.compile(r"\blin_api_[A-Za-z0-9]{30,}\b"),
     "high", "Revoke the Linear API key."),
    ("notion-integration-token",
     re.compile(r"\b(?:secret_|ntn_)[A-Za-z0-9]{30,}\b"),
     "high", "Revoke the Notion integration token."),
    ("huggingface-token",
     re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"),
     "high", "Revoke the Hugging Face token."),
    ("cloudflare-api-token",
     re.compile(r"""(?i)cloudflare[_\-\.]?api[_\-\.]?token['"\s:=]+['"]?"""
                r"""([A-Za-z0-9\-_]{40})"""),
     "critical", "Roll the Cloudflare token."),
]

# Placeholder values that scanners should not cry wolf about.
FALSE_POSITIVE_HINTS = (
    "example", "placeholder", "changeme", "your-", "your_", "xxxxx", "<", ">",
    "dummy", "fake", "sample", "test_", "testing", "todo", "redacted",
    "${", "{{", "%s", "none", "null", "undefined", "***",
)

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", ".tox", ".nox",
    "dist", "build", ".cache", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".next", ".nuxt", ".output", ".parcel-cache", ".turbo", ".svelte-kit",
    "vendor", "coverage", ".gradle", ".idea", ".vscode", "Pods", "target",
    ".terraform", "site-packages", ".eggs",
}
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff",
    ".pdf", ".zip", ".gz", ".tgz", ".bz2", ".7z", ".rar", ".tar",
    ".mp3", ".mp4", ".mov", ".avi", ".wav", ".flac", ".ogg",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".docx", ".xlsx", ".pptx", ".db", ".sqlite", ".sqlite3",
    ".min.js", ".map", ".lock",
}
MAX_FILE_BYTES = 2_000_000


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for char in text:
        counts[char] = counts.get(char, 0) + 1
    length = len(text)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def fingerprint(secret: str) -> str:
    """A safe, non-reversible reference to a found secret."""
    digest = hashlib.sha256(secret.encode("utf-8", errors="replace")).hexdigest()
    return f"sha256:{digest[:16]} len={len(secret)} shape={_shape(secret)}"


def _shape(secret: str) -> str:
    """Character-class pattern, e.g. `U4L6D2` - enough to recognise a duplicate."""
    out: list[str] = []
    for char in secret[:24]:
        code = "U" if char.isupper() else "D" if char.isdigit() else \
               "L" if char.islower() else "S"
        if out and out[-1][0] == code:
            count = int(out[-1][1:]) + 1
            out[-1] = f"{code}{count}"
        else:
            out.append(f"{code}1")
    return "".join(out)


def looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(hint in lowered for hint in FALSE_POSITIVE_HINTS)


class SecretsAudit(Tool):
    name = "secrets_audit"
    description = (
        "Scan a directory or git repository you own for hardcoded secrets, API "
        "keys, private keys, tokens and credentials in connection strings. "
        "Reports file, line, pattern and a redacted fingerprint - never the "
        "secret value. Purely local: no file contents leave the machine."
    )
    kind = "path"
    schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string",
                       "description": "Path in scope to scan. Default: current directory."},
            "include_git_history": {
                "type": "boolean",
                "description": "Also scan the git history for secrets that were "
                               "deleted but remain in old commits. Default false.",
            },
            "entropy_threshold": {
                "type": "number",
                "description": "Shannon entropy above which a generic assignment "
                               "is reported. Default 3.5.",
            },
            "max_files": {"type": "integer",
                          "description": "Cap on files scanned. Default 4000."},
        },
        "required": [],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        target = str(args.get("target") or ".").strip()
        decision = self.authorize(ctx, target)
        if not decision.allowed:
            return ctx.refuse(self.name, target, decision.reason, decision.rule)

        root = Path(target).expanduser()
        if not root.exists():
            return ToolResult(tool=self.name, target=target, ok=False,
                              error=f"no such path: {root}")

        entropy_threshold = float(args.get("entropy_threshold") or 3.5)
        max_files = int(args.get("max_files") or 4000)
        hits: list[dict[str, Any]] = []
        scanned = 0
        skipped = 0

        paths = [root] if root.is_file() else self._walk(root, max_files)
        for path in paths:
            scanned += 1
            ctx.log(f"secrets: {path}")
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    skipped += 1
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                skipped += 1
                continue
            hits += self._scan_text(text, path, root, entropy_threshold)

        if args.get("include_git_history"):
            history = self._scan_git_history(root, ctx, entropy_threshold)
            hits += history["hits"]
            scanned += history.get("blobs", 0)

        findings: list[Finding] = []
        grouped: dict[str, list[dict[str, Any]]] = {}
        for hit in hits:
            grouped.setdefault(hit["pattern"], []).append(hit)

        for pattern, items in sorted(grouped.items(),
                                     key=lambda kv: (-kv[1][0]["rank"], kv[0])):
            first = items[0]
            locations = [f"{i['path']}:{i['line']}" for i in items[:12]]
            findings.append(Finding(
                title=f"{pattern} secret found ({len(items)} occurrence(s))",
                severity=first["severity"],
                detail="Locations: " + ", ".join(locations)
                       + (" ..." if len(items) > 12 else ""),
                remediation=first["remediation"]
                            + " Then purge history with git filter-repo or BFG, "
                              "and force-push - deleting the line is not enough.",
                reference="https://owasp.org/www-project-top-ten/",
                evidence={"count": len(items),
                          "fingerprints": [i["fingerprint"] for i in items[:12]],
                          "locations": locations},
            ))

        if not hits and scanned:
            findings.append(Finding(
                title="No hardcoded secrets detected",
                severity="info",
                detail=f"Scanned {scanned} files with "
                       f"{len(SECRET_PATTERNS)} patterns.",
                remediation="Keep it that way: add a pre-commit hook "
                            "(gitleaks/detect-secrets) and enable push protection "
                            "on the remote.",
            ))

        return ToolResult(
            tool=self.name, target=str(root), ok=True, findings=findings,
            data={"files_scanned": scanned, "files_skipped": skipped,
                  "occurrences": len(hits),
                  "patterns_matched": sorted(grouped)},
        )

    # ------------------------------------------------------------- internals

    def _walk(self, root: Path, max_files: int) -> list[Path]:
        out: list[Path] = []
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            # .github, .env files etc. matter, so keep dotfiles but not dotdirs
            for name in files:
                path = Path(current) / name
                if path.suffix.lower() in SKIP_SUFFIXES:
                    continue
                if name.endswith((".min.js", ".min.css", ".map")):
                    continue
                out.append(path)
                if len(out) >= max_files:
                    return out
        return out

    def _scan_text(self, text: str, path: Path, root: Path,
                   entropy_threshold: float) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        try:
            relative = str(path.relative_to(root))
        except ValueError:
            relative = str(path)
        rank_of = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

        for line_number, line in enumerate(text.splitlines(), start=1):
            if len(line) > 4000:
                line = line[:4000]
            for pattern_id, regex, severity, remediation in SECRET_PATTERNS:
                for match in regex.finditer(line):
                    secret = next(
                        (g for g in match.groups() if g and len(g) >= 8),
                        match.group(0),
                    )
                    if looks_like_placeholder(secret):
                        continue
                    if pattern_id.startswith("generic") and \
                            shannon_entropy(secret) < entropy_threshold:
                        continue
                    hits.append({
                        "pattern": pattern_id, "severity": severity,
                        "rank": rank_of[severity],
                        "path": relative, "line": line_number,
                        "fingerprint": fingerprint(secret),
                        "remediation": remediation,
                        "entropy": round(shannon_entropy(secret), 2),
                    })
        return hits

    def _scan_git_history(self, root: Path, ctx: ToolContext,
                          entropy_threshold: float) -> dict[str, Any]:
        """Scan blobs reachable from history. Read-only git plumbing."""
        import subprocess

        if not (root / ".git").exists():
            return {"hits": [], "blobs": 0, "error": "not a git repository"}
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), "rev-list", "--objects", "--all"],
                capture_output=True, text=True, timeout=120, check=False,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            return {"hits": [], "blobs": 0, "error": str(exc)}
        if completed.returncode != 0:
            return {"hits": [], "blobs": 0,
                    "error": completed.stderr.strip()[:300]}

        objects: list[tuple[str, str]] = []
        for line in completed.stdout.splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1]:
                objects.append((parts[0], parts[1]))

        hits: list[dict[str, Any]] = []
        blobs = 0
        for sha, name in objects[:2000]:
            if Path(name).suffix.lower() in SKIP_SUFFIXES:
                continue
            try:
                cat = subprocess.run(
                    ["git", "-C", str(root), "cat-file", "-p", sha],
                    capture_output=True, text=True, timeout=20, check=False,
                )
            except (subprocess.SubprocessError, OSError):
                continue
            if cat.returncode != 0 or not cat.stdout:
                continue
            blobs += 1
            for hit in self._scan_text(cat.stdout[:200_000], Path(name),
                                       Path("."), entropy_threshold):
                hit["path"] = f"{name} @ {sha[:8]}"
                hits.append(hit)
        return {"hits": hits, "blobs": blobs}

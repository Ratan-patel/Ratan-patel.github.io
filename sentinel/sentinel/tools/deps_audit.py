"""Dependency vulnerability audit for a project directory you own.

Two paths, in order of preference:
  1. OSV.dev batch API (https://google.github.io/osv.dev/) - free, no key,
     covers PyPI / npm / Go / Maven / crates.io / NuGet / RubyGems / etc.
  2. Local scanners already on PATH: `pip-audit`, `npm audit --json`,
     `cargo audit --json`, `govulncheck`.

Nothing here touches a remote target you do not own - it reads your own
lockfiles/manifests and asks a public advisory database about package versions.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

from .base import Finding, Tool, ToolContext, ToolResult

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns/"

REQUIREMENT_RE = re.compile(
    r"""^\s*(?P<name>[A-Za-z0-9._\-]+)"""
    r"""\s*(?P<spec>(?:\[[^\]]*\])?\s*(?:[<>=!~^]=?[^;#\n]+)?)?""",
)
LOCK_PY_RE = re.compile(
    r'name\s*=\s*"(?P<name>[^"]+)"[\s\S]{0,200}?version\s*=\s*"(?P<version>[^"]+)"'
)
NPM_DEP_RE = re.compile(r'"(?P<name>[^"@/][^"]*|@[^"/]+/[^"]+)"\s*:\s*"(?P<version>[^"]+)"')


def _clean_requirement_version(spec: str | None) -> str | None:
    """Return an exact version if the specifier pins one, else None."""
    if not spec:
        return None
    text = spec.strip()
    text = re.sub(r"\[[^\]]*\]", "", text).strip()
    if not text:
        return None
    for part in text.split(","):
        part = part.strip()
        if part.startswith("==") and "*" not in part:
            return part[2:].strip().split(";")[0].strip()
        if re.fullmatch(r"\d[\w.\-+]*", part):
            return part
    return None


def parse_requirements(text: str) -> list[dict[str, str]]:
    packages: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        stripped = stripped.split("#", 1)[0].strip()
        match = REQUIREMENT_RE.match(stripped)
        if not match:
            continue
        version = _clean_requirement_version(match.group("spec"))
        packages.append({
            "name": match.group("name").lower().replace("_", "-"),
            "version": version or "",
            "pinned": bool(version),
        })
    return packages


def parse_pyproject(text: str) -> list[dict[str, str]]:
    packages: list[dict[str, str]] = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") :
            in_deps = stripped in ("dependencies = [",) or "dependencies]" in stripped
            continue
        if stripped.startswith("dependencies"):
            in_deps = True
            inline = stripped.split("[", 1)[-1]
            stripped = inline
        if in_deps:
            if stripped.startswith("]"):
                in_deps = False
                continue
            cleaned = stripped.strip().strip(",").strip().strip('"').strip("'")
            if not cleaned:
                continue
            match = REQUIREMENT_RE.match(cleaned)
            if match:
                version = _clean_requirement_version(match.group("spec"))
                packages.append({
                    "name": match.group("name").lower().replace("_", "-"),
                    "version": version or "",
                    "pinned": bool(version),
                })
    return packages


def parse_package_json(text: str) -> list[dict[str, str]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    out: list[dict[str, str]] = []
    for section in ("dependencies", "devDependencies"):
        block = data.get(section) or {}
        if isinstance(block, dict):
            for name, spec in block.items():
                if not isinstance(spec, str):
                    continue
                exact = spec if re.fullmatch(r"\d[\w.\-+]*", spec.strip()) else None
                out.append({"name": name, "version": exact or "",
                            "pinned": bool(exact), "dev": section == "devDependencies"})
    return out


def parse_package_lock(text: str) -> list[dict[str, str]]:
    """npm lockfileVersion 2/3 - exact versions, ideal for advisory lookups."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    out: list[dict[str, str]] = []
    packages = data.get("packages") or {}
    for key, meta in packages.items():
        if not isinstance(meta, dict):
            continue
        version = meta.get("version")
        if not version or not isinstance(version, str):
            continue
        name = key.replace("node_modules/", "").split("node_modules/")[-1]
        if not name:
            continue
        out.append({"name": name, "version": version, "pinned": True,
                    "dev": bool(meta.get("dev"))})
    return out


def collect_packages(root: Path) -> dict[str, list[dict[str, str]]]:
    """Manifest path -> parsed package list."""
    found: dict[str, list[dict[str, str]]] = {}
    candidates = [
        ("requirements*.txt", parse_requirements, "PyPI"),
        ("constraints*.txt", parse_requirements, "PyPI"),
        ("pyproject.toml", parse_pyproject, "PyPI"),
        ("package.json", parse_package_json, "npm"),
        ("package-lock.json", parse_package_lock, "npm"),
    ]
    skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__",
                 ".tox", ".nox", "dist", "build", ".cache", ".mypy_cache"}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix not in (".txt", ".toml", ".json"):
            continue
        for pattern, parser, ecosystem in candidates:
            if path.match(pattern) or path.name == pattern.rstrip("*"):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                packages = parser(text)
                if packages:
                    key = str(path.relative_to(root))
                    entry = found.setdefault(key, [])
                    for package in packages:
                        package = dict(package)
                        package["ecosystem"] = ecosystem
                        entry.append(package)
    return found


def osv_batch(packages: list[dict[str, Any]], timeout: float = 25.0) -> dict[str, Any]:
    """Query OSV.dev for a list of {name, version, ecosystem}."""
    queries = [
        {"package": {"name": p["name"], "ecosystem": p["ecosystem"]},
         "version": p["version"]}
        for p in packages if p.get("version")
    ]
    if not queries:
        return {"results": [], "skipped": len(packages)}
    payload = json.dumps({"queries": queries}).encode()
    request = urlrequest.Request(
        OSV_BATCH_URL, data=payload,
        headers={"Content-Type": "application/json",
                 "User-Agent": "sentinel-deps-audit/1.0"},
        method="POST",
    )
    with urlrequest.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def osv_vuln(vuln_id: str, timeout: float = 15.0) -> dict[str, Any]:
    request = urlrequest.Request(
        OSV_VULN_URL + vuln_id,
        headers={"User-Agent": "sentinel-deps-audit/1.0"},
    )
    with urlrequest.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def _severity_of(vuln: dict[str, Any]) -> str:
    text = json.dumps(vuln.get("severity", [])) + json.dumps(
        vuln.get("database_specific", {})).lower()
    aliases = " ".join(vuln.get("aliases", []))
    if "CRITICAL" in text.upper() or any(a.startswith("CVE") and False for a in []):
        return "critical"
    cvss = re.findall(r"CVSS[:/][^\"\s]*?(\d\.\d|\d{2})", text)
    if cvss:
        try:
            score = float(cvss[0])
            if score >= 9.0:
                return "critical"
            if score >= 7.0:
                return "high"
            if score >= 4.0:
                return "medium"
            return "low"
        except ValueError:
            pass
    lowered = (vuln.get("summary", "") + " " + vuln.get("details", "")).lower()
    for word, level in (("remote code execution", "critical"),
                        ("arbitrary code", "critical"),
                        ("authentication bypass", "critical"),
                        ("sql injection", "high"), ("path traversal", "high"),
                        ("denial of service", "medium"), ("xss", "medium"),
                        ("information disclosure", "medium")):
        if word in lowered:
            return level
    return "medium"


class DepsAudit(Tool):
    name = "deps_audit"
    description = (
        "Scan a project directory you own for dependencies with known "
        "vulnerabilities. Reads local manifests/lockfiles and checks them "
        "against OSV.dev, falling back to pip-audit/npm audit if present. Also "
        "flags unpinned dependencies (supply-chain risk)."
    )
    kind = "path"
    schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string",
                       "description": "Absolute or relative path to a project you "
                                      "own and that is listed in your scope."},
            "check_advisories": {
                "type": "boolean",
                "description": "Query OSV.dev for known CVEs. Requires network. "
                               "Default true.",
            },
            "max_depth": {"type": "integer",
                          "description": "Directory recursion depth. Default 6."},
        },
        "required": ["target"],
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
        if root.is_file():
            root = root.parent

        found = collect_packages(root)
        flat: list[dict[str, Any]] = []
        for manifest, packages in found.items():
            for package in packages:
                entry = dict(package)
                entry["manifest"] = manifest
                flat.append(entry)

        findings: list[Finding] = []
        unpinned = [p for p in flat if not p.get("pinned")]
        if unpinned:
            names = sorted({p["name"] for p in unpinned})
            findings.append(Finding(
                title=f"{len(unpinned)} unpinned dependencies",
                severity="medium",
                detail="No exact version is recorded, so a rebuild can silently "
                       "pull different code. This is the setup a dependency-"
                       "confusion or typosquat attack needs.\n"
                       + ", ".join(names[:40])
                       + (" ..." if len(names) > 40 else ""),
                remediation="Use a lockfile (pip-tools/poetry/uv, npm ci, "
                            "Cargo.lock) and enable dependabot/renovate.",
                reference="https://owasp.org/www-project-top-ten/",
                evidence={"count": len(unpinned), "names": names[:80]},
            ))

        duplicates: dict[str, set[str]] = {}
        for package in flat:
            if package.get("version"):
                duplicates.setdefault(package["name"], set()).add(package["version"])
        conflicting = {k: sorted(v) for k, v in duplicates.items() if len(v) > 1}
        if conflicting:
            findings.append(Finding(
                title=f"{len(conflicting)} packages at conflicting versions",
                severity="low",
                detail=json.dumps(conflicting, indent=None)[:800],
                remediation="Deduplicate - mixed versions mean one code path is "
                            "running an unpatched library.",
                evidence=conflicting,
            ))

        advisories: dict[str, Any] = {"queried": 0, "vulnerable": [], "error": None}
        if args.get("check_advisories", True) and not ctx.offline:
            queryable = [p for p in flat if p.get("version") and p.get("ecosystem")]
            advisories["queried"] = len(queryable)
            if queryable:
                try:
                    response = osv_batch(queryable[:400], timeout=ctx.timeout + 10)
                    results = response.get("results") or []
                    for package, result in zip(queryable[:400], results):
                        ids = [v.get("id") for v in (result.get("vulns") or [])
                               if v.get("id")]
                        if not ids:
                            continue
                        advisories["vulnerable"].append(
                            {"package": package["name"],
                             "version": package["version"],
                             "ecosystem": package["ecosystem"],
                             "manifest": package.get("manifest"),
                             "ids": ids[:12]})
                except (urlerror.URLError, urlerror.HTTPError, TimeoutError,
                        OSError, json.JSONDecodeError) as exc:
                    advisories["error"] = f"{type(exc).__name__}: {exc}"

            for item in advisories["vulnerable"]:
                severity = "high"
                details: list[str] = []
                for vuln_id in item["ids"][:3]:
                    try:
                        vuln = osv_vuln(vuln_id, timeout=12.0)
                        severity = max(
                            [severity, _severity_of(vuln)],
                            key=lambda s: {"low": 0, "medium": 1, "high": 2,
                                           "critical": 3}[s],
                        )
                        details.append(
                            f"{vuln_id}: {(vuln.get('summary') or '')[:160]}")
                    except (urlerror.URLError, urlerror.HTTPError, TimeoutError,
                            OSError, json.JSONDecodeError):
                        details.append(vuln_id)
                findings.append(Finding(
                    title=f"{item['package']}=={item['version']} has "
                          f"{len(item['ids'])} known vulnerabilities",
                    severity=severity,
                    detail="; ".join(details)[:900],
                    remediation=f"Upgrade {item['package']} to a patched release "
                                f"and pin it.",
                    reference="https://osv.dev/list?q=" + item["package"],
                    evidence={"ids": item["ids"], "ecosystem": item["ecosystem"],
                              "manifest": item.get("manifest")},
                ))
        elif args.get("check_advisories", True) and ctx.offline:
            advisories["error"] = "offline mode - advisory lookup skipped"

        local = self._local_scanners(root)
        if local:
            advisories["local_scanners"] = local

        return ToolResult(
            tool=self.name, target=str(root), ok=True, findings=findings,
            data={"manifests": {k: len(v) for k, v in found.items()},
                  "total_packages": len(flat), "advisories": advisories},
        )

    def _local_scanners(self, root: Path) -> dict[str, Any]:
        """Run a local advisory scanner if one is installed. Never installs anything."""
        out: dict[str, Any] = {}
        if shutil.which("pip-audit") and (root / "requirements.txt").exists():
            out["pip-audit"] = self._run(
                ["pip-audit", "-r", str(root / "requirements.txt"), "-f", "json"],
                root)
        if shutil.which("npm") and (root / "package-lock.json").exists():
            out["npm-audit"] = self._run(
                ["npm", "audit", "--json", "--omit=dev"], root)
        if shutil.which("cargo") and (root / "Cargo.lock").exists():
            out["cargo-audit"] = self._run(["cargo", "audit", "--json"], root)
        return out

    @staticmethod
    def _run(command: list[str], cwd: Path) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                command, cwd=str(cwd), capture_output=True, text=True, timeout=180,
                check=False,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}
        payload: dict[str, Any] = {"returncode": completed.returncode}
        try:
            payload["json"] = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            payload["stdout"] = completed.stdout[:2000]
        if completed.stderr:
            payload["stderr"] = completed.stderr[:800]
        return payload

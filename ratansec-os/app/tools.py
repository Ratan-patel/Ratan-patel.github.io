"""Tool registry + scan profiles.

Poora execution argv-based hai (shell use nahi hota), isliye command injection
possible nahi. Har tool ka apna arg-builder hai jo target ko validate karta hai.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .security import ParsedTarget

# --------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------
@dataclass
class Step:
    tool: str
    args: list[str]
    label: str
    timeout: int = 180
    needs_approval: bool = False

    def display(self) -> str:
        binary = TOOLS[self.tool].binary if self.tool in TOOLS else self.tool
        return " ".join([binary] + [shlex.quote(a) for a in self.args])


@dataclass
class ToolSpec:
    name: str
    binary: str
    package: str
    description: str
    category: str
    needs_approval: bool = False
    profiles: list[str] = field(default_factory=list)
    default_args: list[str] = field(default_factory=list)
    version_flag: str = "--version"

    def installed(self) -> bool:
        return shutil.which(self.binary) is not None

    def command_preview(self, target: ParsedTarget, extra_args: list[str] | None = None) -> list[str]:
        return list(self.default_args) + list(extra_args or []) + self._target_tokens(target)

    def _target_tokens(self, target: ParsedTarget) -> list[str]:
        if self.name in ("whatweb", "nikto", "nuclei", "sqlmap"):
            return [target.url or target.host]
        if self.name in ("gobuster", "ffuf"):
            base = (target.url or f"https://{target.host}").rstrip("/")
            return [base]
        return [target.host]


# --------------------------------------------------------------------------
# Registry — Kali apt packages
# --------------------------------------------------------------------------
TOOLS: dict[str, ToolSpec] = {
    "whois": ToolSpec(
        name="whois", binary="whois", package="whois",
        description="Domain ownership, registrar aur dates nikalta hai",
        category="Recon", profiles=["quick"], version_flag="-h",
    ),
    "dig": ToolSpec(
        name="dig", binary="dig", package="dnsutils",
        description="DNS records (A, NS, MX) check karta hai",
        category="Recon", profiles=["quick"], default_args=["+short"],
        version_flag="-v",
    ),
    "nmap": ToolSpec(
        name="nmap", binary="nmap", package="nmap",
        description="Port scan + service/version detection (industry standard)",
        category="Scanning", profiles=["quick", "web", "network", "vuln", "full"],
        default_args=["-T4", "-Pn", "-F", "--open", "-sV", "--version-light"],
    ),
    "whatweb": ToolSpec(
        name="whatweb", binary="whatweb", package="whatweb",
        description="Website fingerprinting — CMS, server, frameworks detect karta hai",
        category="Web", profiles=["web", "full"], default_args=["-q", "--no-errors"],
        version_flag="--version",
    ),
    "nikto": ToolSpec(
        name="nikto", binary="nikto", package="nikto",
        description="Web server vulnerability scanner (misconfig, outdated software)",
        category="Web", profiles=["web", "full"],
        default_args=["-maxtime", "120s", "-nointeractive", "-ask", "no"],
        version_flag="-Version",
    ),
    "gobuster": ToolSpec(
        name="gobuster", binary="gobuster", package="gobuster",
        description="Directory/file brute-force (wordlist ke saath)",
        category="Web", profiles=["web", "full"], default_args=["dir", "-q", "--no-progress"],
    ),
    "ffuf": ToolSpec(
        name="ffuf", binary="ffuf", package="ffuf",
        description="Fast web fuzzer — hidden endpoints/directories dhundta hai",
        category="Web", profiles=["full"], default_args=["-s", "-noninteractive"],
        version_flag="-V",
    ),
    "nuclei": ToolSpec(
        name="nuclei", binary="nuclei", package="nuclei",
        description="Template-based vulnerability scanner (CVEs, exposures, misconfigs)",
        category="Vuln", profiles=["vuln", "full"],
        default_args=["-silent", "-duc", "-no-color"],
    ),
    "sqlmap": ToolSpec(
        name="sqlmap", binary="sqlmap", package="sqlmap",
        description="SQL injection detection (level 1, batch mode)",
        category="Exploit-Safe", needs_approval=True, profiles=["webapp"],
        default_args=["--batch", "--level", "1", "--risk", "1", "--smart", "--threads", "4", "--timeout", "10"],
        version_flag="--version",
    ),
    "hydra": ToolSpec(
        name="hydra", binary="hydra", package="hydra",
        description="Login brute-force (SIRF likhit permission ke saath — approval required)",
        category="Credentials", needs_approval=True, profiles=[],
        default_args=[], version_flag="-h",
    ),
    "nc": ToolSpec(
        name="nc", binary="nc", package="netcat-openbsd",
        description="Netcat — banner grabbing / connectivity check",
        category="Utility", profiles=[], default_args=["-vz", "-w", "3"], version_flag="-h",
    ),
    "curl": ToolSpec(
        name="curl", binary="curl", package="curl",
        description="HTTP headers/response check (safe recon)",
        category="Utility", profiles=["quick"], default_args=["-sSI", "--max-time", "15", "-A", "RatanSecOS/1.0"],
        version_flag="--version",
    ),
}

# Human-facing aliases
ALIASES = {"netcat": "nc", "dnsutils": "dig", "host": "dig", "whatweb-scan": "whatweb"}


def resolve_tool(name: str) -> ToolSpec | None:
    key = (name or "").strip().lower()
    key = ALIASES.get(key, key)
    return TOOLS.get(key)


# --------------------------------------------------------------------------
# Wordlists (gobuster/ffuf ke liye)
# --------------------------------------------------------------------------
_WORDLIST_CANDIDATES = [
    "/usr/share/wordlists/dirb/common.txt",
    "/usr/share/dirb/wordlists/common.txt",
    "/usr/share/seclists/Discovery/Web-Content/common.txt",
    "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
]
_wordlist_cache: str | None = None


def wordlist_path() -> str | None:
    global _wordlist_cache
    if _wordlist_cache and Path(_wordlist_cache).is_file():
        return _wordlist_cache
    for candidate in _WORDLIST_CANDIDATES:
        if Path(candidate).is_file():
            _wordlist_cache = candidate
            return candidate
    return None


_NUCLEI_TEMPLATE_DIRS = ["/opt/nuclei-templates", str(Path.home() / "nuclei-templates"), "/root/nuclei-templates"]


def nuclei_templates_dir() -> str | None:
    for candidate in _NUCLEI_TEMPLATE_DIRS:
        p = Path(candidate)
        if p.is_dir() and any(p.iterdir()):
            return candidate
    return None


# --------------------------------------------------------------------------
# Availability / version cache
# --------------------------------------------------------------------------
_status_cache: dict[str, dict] = {}
_status_lock = threading.Lock()


def tool_status(name: str, refresh: bool = False) -> dict:
    spec = TOOLS.get(name)
    if not spec:
        return {"name": name, "installed": False, "version": None, "known": False}
    with _status_lock:
        if not refresh and name in _status_cache:
            return _status_cache[name]

    installed = spec.installed()
    version: str | None = None
    if installed:
        try:
            proc = subprocess.run(
                [spec.binary, spec.version_flag], capture_output=True, text=True, timeout=6
            )
            blob = (proc.stdout or proc.stderr or "").strip().splitlines()
            version = blob[0][:120] if blob else None
        except (subprocess.SubprocessError, OSError):
            version = None
    info = {
        "name": spec.name,
        "binary": spec.binary,
        "package": spec.package,
        "description": spec.description,
        "category": spec.category,
        "needs_approval": spec.needs_approval,
        "profiles": spec.profiles,
        "installed": installed,
        "version": version,
        "known": True,
    }
    with _status_lock:
        _status_cache[name] = info
    return info


def all_tool_status(refresh: bool = False) -> list[dict]:
    return [tool_status(name, refresh=refresh) for name in TOOLS]


def missing_packages() -> list[str]:
    return sorted({s.package for s in TOOLS.values() if not s.installed()})


# --------------------------------------------------------------------------
# Scan profiles
# --------------------------------------------------------------------------
@dataclass
class ProfileSpec:
    name: str
    title: str
    description: str
    build: callable  # (ParsedTarget) -> list[Step]


def _quick(t: ParsedTarget) -> list[Step]:
    return [
        Step("whois", [t.host], f"Whois — {t.host}", timeout=60),
        Step("dig", ["+short", t.host, "A"], f"DNS A record — {t.host}", timeout=30),
        Step("dig", ["+short", t.host, "NS"], f"DNS NS record — {t.host}", timeout=30),
        Step("curl", ["-sSI", "--max-time", "15", t.url], f"HTTP headers — {t.url}", timeout=40),
        Step("nmap", ["-T4", "-Pn", "-F", "--open", "-sV", "--version-light", t.host], f"Nmap top-100 ports — {t.host}", timeout=210),
    ]


def _web(t: ParsedTarget) -> list[Step]:
    steps = [
        Step("whatweb", ["-q", "--no-errors", t.url], f"WhatWeb fingerprint — {t.url}", timeout=90),
        Step("nmap", ["-T4", "-Pn", "--open", "-p", "80,443,8000,8080,8443", "--script", "http-title,http-headers", t.host],
             f"Nmap HTTP scripts — {t.host}", timeout=150),
        Step("nikto", ["-h", t.url, "-maxtime", "120s", "-nointeractive", "-ask", "no"], f"Nikto scan — {t.url}", timeout=200),
    ]
    wl = wordlist_path()
    base = (t.url or f"https://{t.host}").rstrip("/")
    if wl:
        steps.append(Step("gobuster", ["dir", "-u", base, "-w", wl, "-t", "20", "--timeout", "10s", "-q", "--no-progress", "--no-error"],
                          f"Gobuster dir — {base}", timeout=240))
    return steps


def _network(t: ParsedTarget) -> list[Step]:
    return [
        Step("nmap", ["-T4", "-Pn", "-sC", "-sV", "--top-ports", "1000", "--open", t.host],
             f"Nmap top-1000 + default scripts — {t.host}", timeout=420),
    ]


def _vuln(t: ParsedTarget) -> list[Step]:
    wl = None
    steps = [
        Step("nmap", ["-T4", "-Pn", "--open", "--script", "vuln", "--top-ports", "200", t.host],
             f"Nmap vuln scripts — {t.host}", timeout=420),
    ]
    if TOOLS["nuclei"].installed():
        tdir = nuclei_templates_dir()
        args = ["-u", t.url, "-silent", "-duc", "-no-color", "-severity", "low,medium,high,critical", "-timeout", "5", "-rl", "40"]
        if tdir:
            args += ["-ud", tdir]
        steps.append(Step("nuclei", args, f"Nuclei templates — {t.url}", timeout=420))
    return steps


def _webapp(t: ParsedTarget) -> list[Step]:
    if "?" not in t.raw:
        raise ValueError(
            "sqlmap profile ke liye parameter wala URL chahiye (jaise https://site.com/item?id=1). "
            "Isliye ye profile skip ho raha hai."
        )
    steps = [
        Step("sqlmap", ["--batch", "--level", "1", "--risk", "1", "--smart", "--threads", "4",
                        "--timeout", "10", "--url", t.raw],
             f"sqlmap (level 1) — {t.raw}", timeout=300, needs_approval=True),
    ]
    wl = wordlist_path()
    base = (t.url or f"https://{t.host}").rstrip("/")
    if wl:
        steps.append(Step("ffuf", ["-u", f"{base}/FUZZ", "-w", wl, "-mc", "200,204,301,302,307,401,403",
                                   "-t", "20", "-timeout", "10", "-s", "-noninteractive"],
                          f"ffuf fuzzing — {base}", timeout=240))
    return steps


def _full(t: ParsedTarget) -> list[Step]:
    return _quick(t) + _web(t) + _vuln(t)


PROFILES: dict[str, ProfileSpec] = {
    "quick": ProfileSpec("quick", "Quick Recon", "Whois + DNS + HTTP headers + top-100 ports (~2-4 min)", _quick),
    "web": ProfileSpec("web", "Web Scan", "Fingerprint + Nikto + directory brute-force (~4-7 min)", _web),
    "network": ProfileSpec("network", "Network Scan", "Top-1000 ports + service/version + default scripts (~5-8 min)", _network),
    "vuln": ProfileSpec("vuln", "Vulnerability Scan", "Nmap vuln scripts + Nuclei CVE/exposure templates (~5-8 min)", _vuln),
    "webapp": ProfileSpec("webapp", "WebApp/SQLi", "sqlmap (level 1) + ffuf — parameter wale URL par (approval required)", _webapp),
    "full": ProfileSpec("full", "Full Sweep", "Quick + Web + Vuln ek saath — sabse detailed (10-15 min)", _full),
}


def build_profile(profile: str, target: ParsedTarget) -> list[Step]:
    spec = PROFILES.get((profile or "").strip().lower())
    if not spec:
        raise ValueError(f"Unknown profile '{profile}'. Available: {', '.join(PROFILES)}")
    return list(spec.build(target))


def profile_catalog() -> list[dict]:
    return [
        {
            "name": p.name,
            "title": p.title,
            "description": p.description,
            "needs_wordlist": p.name in ("web", "webapp") and wordlist_path() is None,
        }
        for p in PROFILES.values()
    ]

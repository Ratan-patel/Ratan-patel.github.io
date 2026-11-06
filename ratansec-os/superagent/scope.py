"""Scope engine — har command se pehle target validate hota hai.

Flow:
    target string -> parse_target() -> scope check -> RoE (authorization record) check
    -> Decision(allowed | denied + reason)

Yahan jaan-boojh kar "deny by default" policy hai:
  * Cloud metadata / link-local / multicast -> hard block (override nahi).
  * Scope ya RoE na mile to command nahi chalega.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from . import records
from .settings import BLOCKED_HOSTS, BLOCKED_NETWORKS, settings

# Target me ye characters allowed nahi (argv style chalta hai, phir bhi defence)
_BAD_CHARS = set(";|&$`'\"<>(){}[]\\ \n\r\t\x00")
_HOSTNAME_RE = re.compile(r"^(?!-)[A-Za-z0-9._-]{1,253}(?<!-)$")

LOCAL_NAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


@dataclass
class Target:
    raw: str
    host: str
    url: str
    scheme: str = "https"
    port: int | None = None
    is_url: bool = False
    is_cidr: bool = False
    path: str = ""

    def display(self) -> str:
        return self.url or self.host


@dataclass
class Decision:
    allowed: bool
    host: str
    url: str
    reason: str
    section: str = ""
    roe_id: str = ""
    matched: str = ""
    code: str = ""          # invalid | blocked | out-of-scope | no-roe | ok
    target: Target | None = None

    def view(self) -> dict:
        return {
            "allowed": self.allowed,
            "host": self.host,
            "url": self.url,
            "reason": self.reason,
            "section": self.section,
            "roe_id": self.roe_id,
            "matched": self.matched,
            "code": self.code,
        }


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------
def parse_target(raw: str) -> Target:
    value = (raw or "").strip()
    if not value:
        raise ValueError("Target khali hai.")
    if len(value) > 2048:
        raise ValueError("Target bahut lamba hai.")
    if value.startswith("-"):
        raise ValueError("Target '-' se shuru nahi ho sakta (flag injection).")
    bad = sorted(set(value) & _BAD_CHARS)
    if bad:
        raise ValueError(f"Target me ye characters allowed nahi: {' '.join(bad)}")

    # CIDR
    if "/" in value and "://" not in value:
        try:
            net = ipaddress.ip_network(value, strict=False)
            return Target(raw=value, host=str(net.network_address), url="", is_cidr=True)
        except ValueError:
            pass  # URL path ho sakta hai

    is_url = value.startswith(("http://", "https://"))
    parts = urlsplit(value if is_url else f"//{value}")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("Host nikal nahi paya. Example: example.com ya https://example.com/app")
    if not _is_ip(host) and not _HOSTNAME_RE.match(host):
        raise ValueError(f"Invalid hostname: {host}")
    if not _is_ip(host) and "." not in host and host not in ("localhost",):
        raise ValueError("Hostname me dot hona chahiye (jaise example.com) — warna internal name maana jayega.")
    scheme = parts.scheme if is_url else "https"
    port = parts.port
    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc = f"{netloc}:{port}"
    url = f"{scheme}://{netloc}" if (is_url or port) else f"https://{host}"
    return Target(raw=value, host=host, url=url, scheme=scheme, port=port, is_url=is_url, path=parts.path or "")


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------
def host_matches(host: str, pattern: str) -> bool:
    host = (host or "").lower().strip()
    pattern = (pattern or "").lower().strip()
    if not host or not pattern:
        return False
    if pattern in ("*", "any"):
        return True
    if "/" in pattern:  # CIDR pattern
        try:
            net = ipaddress.ip_network(pattern, strict=False)
            return _is_ip(host) and ipaddress.ip_address(host) in net
        except ValueError:
            return False
    if pattern.startswith("*."):
        suffix = pattern[1:]  # ".example.com"
        return host.endswith(suffix) or host == pattern[2:]
    if pattern.startswith("."):
        return host.endswith(pattern)
    return host == pattern


def _in_networks(host: str, networks: tuple[str, ...]) -> bool:
    if not _is_ip(host):
        return False
    ip = ipaddress.ip_address(host)
    for net in networks:
        try:
            if ip in ipaddress.ip_network(net, strict=False):
                return True
        except ValueError:
            continue
    return False


def is_private(host: str) -> bool:
    if host in LOCAL_NAMES:
        return True
    if not _is_ip(host):
        return False
    ip = ipaddress.ip_address(host)
    return ip.is_private or ip.is_loopback


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------
def check(raw_target: str, section: str, *, roe_ok_without: bool = False) -> Decision:
    """Target + section authorize hai ya nahi."""
    try:
        target = parse_target(raw_target)
    except ValueError as exc:
        return Decision(False, raw_target, "", str(exc), section=section, code="invalid")

    host = target.host

    # 1) hard block — kabhi nahi
    if host in BLOCKED_HOSTS or _in_networks(host, BLOCKED_NETWORKS):
        return Decision(
            False, host, target.url,
            f"'{host}' hard-blocked hai (cloud metadata / link-local / reserved range). Yeh rule override nahi hota.",
            section=section, code="blocked", target=target,
        )

    # 2) internet / private ranges
    private = is_private(host)
    if private and not settings.allow_private_ranges:
        return Decision(False, host, target.url, "Private/local targets disabled hain (SUPERAGENT_ALLOW_PRIVATE_RANGES=0).",
                        section=section, code="blocked", target=target)
    if not private and not settings.allow_internet:
        return Decision(False, host, target.url, "Public internet targets disabled hain (SUPERAGENT_ALLOW_INTERNET=0).",
                        section=section, code="blocked", target=target)

    # 3) RoE / authorization record
    roe = records.records.find_for(host, section)
    if roe is not None:
        return Decision(
            True, host, target.url,
            f"Authorized: {roe.client} ({roe.id}) — section '{section}', valid till {roe.view()['end_str']}.",
            section=section, roe_id=roe.id, matched="roe", code="ok", target=target,
        )

    # 4) static allowlist (env) — RoE optional hone par fallback
    for pattern in settings.allowed_targets:
        if host_matches(host, pattern):
            if settings.require_roe and not roe_ok_without:
                return Decision(
                    False, host, target.url,
                    f"'{host}' allowlist me hai par koi active authorization record nahi. "
                    "Pehle Records tab me engagement record banao (client + scope + signature).",
                    section=section, matched=pattern, code="no-roe", target=target,
                )
            return Decision(True, host, target.url, f"Allowlist match: {pattern}.", section=section,
                            matched=pattern, code="ok", target=target)

    # 5) blanket allow (lab mode)
    if settings.allow_any_target:
        if settings.require_roe and not roe_ok_without:
            return Decision(
                False, host, target.url,
                "ALLOW_ANY_TARGET on hai par authorization record nahi mila (REQUIRE_ROE=1). "
                "Records tab se record banao, ya local lab ke liye REQUIRE_ROE=0 karo.",
                section=section, code="no-roe", target=target,
            )
        return Decision(True, host, target.url, "ALLOW_ANY_TARGET=1 (lab mode) — koi record nahi mila.",
                        section=section, matched="*", code="ok", target=target)

    return Decision(
        False, host, target.url,
        f"'{host}' kisi active authorization record ke scope me nahi hai. "
        "Records tab me record banao ya ALLOWED_TARGETS me add karo. (Default deny)",
        section=section, code="out-of-scope", target=target,
    )


def scope_payload() -> dict:
    return {
        "allowed_targets": settings.allowed_targets,
        "allow_any_target": settings.allow_any_target,
        "allow_private_ranges": settings.allow_private_ranges,
        "allow_internet": settings.allow_internet,
        "require_roe": settings.require_roe,
        "blocked_networks": list(BLOCKED_NETWORKS),
        "active_records": len(records.records.active()),
    }

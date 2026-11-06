"""Default-deny target authorization with strict URL parsing."""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from . import records
from .settings import BLOCKED_HOSTS, BLOCKED_NETWORKS, settings

_BAD_CHARS = set(";|&$`'\"<>{}[]\\ \n\r\t\x00")
_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
LOCAL_NAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
ALLOWED_WEB_PORTS = {80, 443, 8080, 8443}


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
    query: str = ""

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
    code: str = ""
    target: Target | None = None

    def view(self) -> dict:
        return {
            "allowed": self.allowed, "host": self.host, "url": self.url,
            "reason": self.reason, "section": self.section, "roe_id": self.roe_id,
            "matched": self.matched, "code": self.code,
        }


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _valid_host(host: str) -> bool:
    if _is_ip(host):
        return True
    if len(host) > 253 or "." not in host:
        return False
    return all(_LABEL_RE.fullmatch(label) for label in host.split("."))


def parse_target(raw: str) -> Target:
    value = (raw or "").strip()
    if not value or len(value) > 2048:
        raise ValueError("Target empty or too long.")
    if value.startswith("-"):
        raise ValueError("Target cannot start with '-' (flag injection).")
    if any(ch in value for ch in _BAD_CHARS) or any(ord(ch) < 32 for ch in value):
        raise ValueError("Target contains forbidden characters.")
    if "%" in value:
        raise ValueError("Percent-encoded targets are not accepted; use the canonical hostname.")
    if "\\" in value:
        raise ValueError("Backslashes are not accepted in targets.")

    if "/" in value and "://" not in value:
        try:
            net = ipaddress.ip_network(value, strict=False)
        except ValueError:
            pass
        else:
            return Target(raw=value, host=str(net.network_address), url="", is_cidr=True)

    is_url = "://" in value
    if is_url and not value.startswith(("http://", "https://")):
        raise ValueError("Only http:// and https:// URLs are supported.")
    try:
        parts = urlsplit(value if is_url else f"//{value}")
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except ValueError as exc:
        raise ValueError(f"Invalid target: {exc}") from None
    if parts.username or parts.password:
        raise ValueError("Credentials in target URLs are not allowed.")
    if parts.fragment:
        raise ValueError("Remove the URL fragment before testing.")
    if not host or not _valid_host(host):
        raise ValueError(f"Invalid hostname/IP: {host or '(empty)'}")
    if host in {"localhost", "0.0.0.0"} and not settings.allow_private_ranges:
        raise ValueError("Local targets are disabled by policy.")
    scheme = parts.scheme if is_url else "https"
    if port is not None and not (1 <= port <= 65535):
        raise ValueError("Invalid port.")
    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc = f"{netloc}:{port}"
    path = parts.path or "/"
    if not path.startswith("/"):
        raise ValueError("Invalid URL path.")
    url = f"{scheme}://{netloc}{path}"
    if parts.query:
        url += "?" + parts.query
    return Target(raw=value, host=host, url=url, scheme=scheme, port=port,
                  is_url=is_url, path=path, query=parts.query or "")


def host_matches(host: str, pattern: str) -> bool:
    host = (host or "").lower().strip().rstrip(".")
    pattern = (pattern or "").lower().strip().rstrip(".")
    if not host or not pattern:
        return False
    if pattern in ("*", "any"):
        return True
    if "/" in pattern:
        try:
            net = ipaddress.ip_network(pattern, strict=False)
            return _is_ip(host) and ipaddress.ip_address(host) in net
        except ValueError:
            return False
    if pattern.startswith("*."):
        suffix = pattern[1:]
        return host.endswith(suffix) and host != pattern[2:]
    if pattern.startswith("."):
        return host.endswith(pattern) and host != pattern[1:]
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
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def hard_blocked(host: str) -> bool:
    return host in BLOCKED_HOSTS or _in_networks(host, BLOCKED_NETWORKS)


def check(raw_target: str, section: str, *, roe_ok_without: bool = False) -> Decision:
    try:
        target = parse_target(raw_target)
    except ValueError as exc:
        return Decision(False, raw_target, "", str(exc), section=section, code="invalid")
    host = target.host
    if hard_blocked(host):
        return Decision(False, host, target.url,
                        f"'{host}' is hard-blocked (metadata/link-local/reserved).",
                        section=section, code="blocked", target=target)
    private = is_private(host)
    if private and not settings.allow_private_ranges:
        return Decision(False, host, target.url, "Private/local targets are disabled by policy.",
                        section=section, code="blocked", target=target)
    if not private and not settings.allow_internet:
        return Decision(False, host, target.url, "Public internet targets are disabled by policy.",
                        section=section, code="blocked", target=target)
    if section not in {"recon", "info-access", "vuln", "web", "reporting", "utility",
                       "gaining-access", "exploitation", "post", "privilege", "cracking", "wireless"}:
        return Decision(False, host, target.url, "Unknown assessment section.", section=section, code="invalid")

    roe = records.records.find_for(host, section)
    if roe is not None:
        return Decision(True, host, target.url,
                        f"Authorized: {roe.client} ({roe.id}), section '{section}'.",
                        section=section, roe_id=roe.id, matched="roe", code="ok", target=target)
    for pattern in settings.allowed_targets:
        if host_matches(host, pattern):
            if settings.require_roe and not roe_ok_without:
                return Decision(False, host, target.url, "Allowlisted but no active authorization record.",
                                section=section, matched=pattern, code="no-roe", target=target)
            return Decision(True, host, target.url, f"Allowlist match: {pattern}.", section=section,
                            matched=pattern, code="ok", target=target)
    if settings.allow_any_target:
        if settings.require_roe and not roe_ok_without:
            return Decision(False, host, target.url, "No active authorization record (default deny).",
                            section=section, code="no-roe", target=target)
        return Decision(True, host, target.url, "Lab allow-any mode.", section=section,
                        matched="*", code="ok", target=target)
    return Decision(False, host, target.url,
                    f"'{host}' is not in an active authorization record. Default deny.",
                    section=section, code="out-of-scope", target=target)


def validate_web_target(raw: str) -> Target:
    target = parse_target(raw)
    if target.is_cidr or not target.is_url:
        raise ValueError("Mission target must be a full http:// or https:// URL.")
    port = target.port or (443 if target.scheme == "https" else 80)
    if port not in ALLOWED_WEB_PORTS:
        raise ValueError(f"Mission web ports are limited to {sorted(ALLOWED_WEB_PORTS)}.")
    if target.query:
        raise ValueError("Mission URLs must not contain query strings; use a clean path to avoid sensitive data capture.")
    return target


def scope_payload() -> dict:
    return {
        "allowed_targets": settings.allowed_targets,
        "allow_any_target": settings.allow_any_target,
        "allow_private_ranges": settings.allow_private_ranges,
        "allow_internet": settings.allow_internet,
        "require_roe": settings.require_roe,
        "blocked_networks": list(BLOCKED_NETWORKS),
        "active_records": len(records.records.active()),
        "web_ports": sorted(ALLOWED_WEB_PORTS),
    }

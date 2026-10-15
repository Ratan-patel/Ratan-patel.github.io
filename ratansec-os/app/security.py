"""Security layer — auth, scope (target allowlist), rate limiting.

Yeh module ensure karta hai ki:
  1. Dashboard/API sirf authenticated user use kar sake (APP_PASSWORD).
  2. Sirf allowed targets scan ho sakein (ALLOWED_TARGETS scope).
  3. Cloud metadata IPs (169.254.x.x etc.) kabhi scan na hon.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import threading
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

from . import audit
from .config import BLOCKED_HOSTS, BLOCKED_NETWORKS, LOCAL_HOSTS, settings

SESSION_COOKIE = "rs_session"
_TOKEN_SALT = b"ratansec-os-session-v1"

# Characters jo target/args me allowed nahi (argv-only execution hai, phir bhi
# defence-in-depth + accidental mess rokne ke liye).
_FORBIDDEN_CHARS = set(";|&$`\"'<>\n\r\t\x00 ")


# --------------------------------------------------------------------------
# Target parsing
# --------------------------------------------------------------------------
@dataclass
class ParsedTarget:
    raw: str
    host: str
    url: str
    is_url: bool
    is_cidr: bool = False
    port: int | None = None


def parse_target(raw: str) -> ParsedTarget:
    """Target ko host + url me tod do. Raise: ValueError (invalid hua to)."""
    value = (raw or "").strip()
    if not value:
        raise ValueError("Target khali hai.")
    if len(value) > 255:
        raise ValueError("Target bahut lamba hai (max 255 chars).")
    if value.startswith("-"):
        raise ValueError("Target '-' se shuru nahi ho sakta.")
    bad = sorted(set(value) & _FORBIDDEN_CHARS)
    if bad:
        raise ValueError(f"Target me ye characters allowed nahi: {' '.join(bad)}")

    # CIDR? (jaise 10.0.0.0/24)
    if "/" in value and "://" not in value:
        try:
            ipaddress.ip_network(value, strict=False)
            host_only = value.split("/", 1)[0]
            return ParsedTarget(raw=value, host=host_only, url="", is_url=False, is_cidr=True)
        except ValueError:
            pass

    is_url = value.startswith(("http://", "https://"))
    parts = urlsplit(value if is_url else f"//{value}")
    host = parts.hostname
    if not host:
        raise ValueError("Target se host nikal nahi paya. Example: example.com ya https://example.com")
    if host not in LOCAL_HOSTS:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if "." not in host or host.startswith(".") or host.endswith("."):
                raise ValueError("Invalid hostname lag raha hai. Example: example.com")
    scheme = parts.scheme if is_url else "https"
    netloc = f"[{host}]" if ":" in host else host  # IPv6 brackets
    if parts.port:
        netloc = f"{netloc}:{parts.port}"

    if is_url:
        url = f"{scheme}://{netloc}"
    elif parts.port and parts.port not in (80, 443):
        url = f"http://{netloc}"
    elif parts.port:
        url = f"https://{netloc}"
    else:
        url = f"https://{host}"
    return ParsedTarget(raw=value, host=host, url=url, is_url=is_url, port=parts.port)


# --------------------------------------------------------------------------
# Scope (allowlist) check
# --------------------------------------------------------------------------
@dataclass
class ScopeResult:
    allowed: bool
    host: str
    url: str
    reason: str
    in_scope: bool          # True = explicitly allowlisted
    local: bool = False


def _ip_in_blocked_networks(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    for net in BLOCKED_NETWORKS:
        try:
            if ip in ipaddress.ip_network(net, strict=False):
                return True
        except ValueError:
            continue
    return False


def _entry_matches(host: str, entry: str) -> bool:
    entry = entry.strip().lower()
    if not entry:
        return False
    if entry == "*":
        return True
    if entry.startswith("*."):
        suffix = entry[2:]
        return host.endswith("." + suffix) or host == suffix
    if "/" in entry:  # CIDR entry
        try:
            net = ipaddress.ip_network(entry, strict=False)
            return ipaddress.ip_address(host) in net
        except ValueError:
            return False
    if host == entry:
        return True
    # Domain entry -> subdomains bhi allow (example.com => a.example.com)
    if "." in entry and host.endswith("." + entry):
        return True
    return False


def check_target(raw: str, *, source: str = "scan") -> ScopeResult:
    """Target ko validate + scope check karo. ValueError ya ValueError-like raise karta hai."""
    parsed = parse_target(raw)
    host = parsed.host.lower()

    # 1) Hard blocks — hamesha
    if host in BLOCKED_HOSTS or _ip_in_blocked_networks(host):
        raise ValueError(
            "Yeh target hard-blocked hai (cloud metadata / link-local IP). "
            "Security ke liye ise scan nahi kiya ja sakta."
        )

    # 2) Local targets
    if host in LOCAL_HOSTS:
        if settings.allow_local_targets:
            return ScopeResult(True, host, parsed.url, "Local target — ALLOW_LOCAL_TARGETS=1", True, local=True)
        raise ValueError("Local targets disabled hain (ALLOW_LOCAL_TARGETS=0).")

    # 3) Explicit allowlist
    if settings.allowed_targets:
        for entry in settings.allowed_targets:
            if _entry_matches(host, entry):
                return ScopeResult(True, host, parsed.url, f"Scope me hai ({entry})", True)
        if settings.allow_scope_override and source in ("ui", "cli"):
            return ScopeResult(True, host, parsed.url, "Scope override (authenticated user)", False)
        raise ValueError(
            f"'{host}' scope me nahi hai. ALLOWED_TARGETS env me add karo "
            f"(abhi: {', '.join(settings.allowed_targets)}). Sirf authorized targets scan karo!"
        )

    # 4) Koi allowlist nahi
    if settings.allow_any_target:
        return ScopeResult(True, host, parsed.url, "Scope allowlist set nahi — ALLOW_ANY_TARGET=1", False)
    raise ValueError(
        "Target allowed nahi: ALLOWED_TARGETS set nahi hai aur ALLOW_ANY_TARGET=0 hai. "
        "Pehle scope define karo."
    )


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
def _session_token() -> str:
    return hmac.new(settings.app_password.encode(), _TOKEN_SALT, hashlib.sha256).hexdigest()


def check_password(candidate: str) -> bool:
    if not settings.app_password:
        return True
    return hmac.compare_digest(candidate or "", settings.app_password)


def session_cookie_value() -> str:
    return _session_token()


def _bearer_ok(request: Request) -> bool:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return False
    token = header.split(" ", 1)[1].strip()
    if not settings.app_password:
        return True
    # CLI password bhi bhej sakta hai, ya session token
    return hmac.compare_digest(token, settings.app_password) or hmac.compare_digest(token, _session_token())


def is_authenticated(request: Request) -> bool:
    if not settings.app_password:
        return True  # insecure mode — local dev ke liye
    if _bearer_ok(request):
        return True
    cookie = request.cookies.get(SESSION_COOKIE, "")
    return bool(cookie) and hmac.compare_digest(cookie, _session_token())


def require_auth(request: Request) -> str:
    """FastAPI dependency. Returns actor id (ip)."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Login zaroori hai (APP_PASSWORD).")
    return client_ip(request)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# --------------------------------------------------------------------------
# Rate limiting (in-memory, per key)
# --------------------------------------------------------------------------
class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, max_events: int, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < window_seconds]
            if len(hits) >= max_events:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


limiter = RateLimiter()

# Global scan concurrency (free tier friendly)
scan_semaphore = threading.Semaphore(max(1, settings.max_concurrent_scans))


def enforce_rate(key: str, max_events: int, window_seconds: int, message: str) -> None:
    if not limiter.allow(key, max_events, window_seconds):
        raise HTTPException(status_code=429, detail=message)

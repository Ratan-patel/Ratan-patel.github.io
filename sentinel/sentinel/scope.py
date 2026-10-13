"""Authorization scope: the single source of truth for "what am I allowed to touch".

Sentinel does nothing network-facing unless a target resolves inside a loaded,
unexpired Scope that carries a named authorization holder and reference.

A scope file is plain JSON so it can live in a repo, be reviewed in a PR, and be
signed/countersigned by whoever granted the engagement.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import ipaddress
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1

_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)
_HOST_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def parse_ts(value: str | None) -> _dt.datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        stamp = _dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=_dt.timezone.utc)
    return stamp


@dataclasses.dataclass(frozen=True)
class Authorization:
    """Who granted permission, under what reference, and for how long."""

    holder: str
    reference: str
    granted_by: str
    issued: _dt.datetime | None = None
    expires: _dt.datetime | None = None
    notes: str = ""

    def is_expired(self, when: _dt.datetime | None = None) -> bool:
        if self.expires is None:
            return False
        return (when or utcnow()) > self.expires

    def days_left(self, when: _dt.datetime | None = None) -> int | None:
        if self.expires is None:
            return None
        delta = self.expires - (when or utcnow())
        return delta.days

    def to_dict(self) -> dict[str, Any]:
        return {
            "holder": self.holder,
            "reference": self.reference,
            "granted_by": self.granted_by,
            "issued": self.generated_iso(self.issued),
            "expires": self.generated_iso(self.expires),
            "notes": self.notes,
        }

    @staticmethod
    def generated_iso(value: _dt.datetime | None) -> str | None:
        return value.isoformat() if value else None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Authorization":
        return cls(
            holder=str(raw.get("holder") or "").strip(),
            reference=str(raw.get("reference") or "").strip(),
            granted_by=str(raw.get("granted_by") or "").strip(),
            issued=parse_ts(raw.get("issued")),
            expires=parse_ts(raw.get("expires")),
            notes=str(raw.get("notes") or "").strip(),
        )


@dataclasses.dataclass
class Scope:
    """An engagement's permitted target set."""

    name: str
    authorization: Authorization
    domains: list[str] = dataclasses.field(default_factory=list)
    hosts: list[str] = dataclasses.field(default_factory=list)
    networks: list[str] = dataclasses.field(default_factory=list)
    urls: list[str] = dataclasses.field(default_factory=list)
    model_endpoints: list[str] = dataclasses.field(default_factory=list)
    local_paths: list[str] = dataclasses.field(default_factory=list)
    version: int = SCHEMA_VERSION
    source: str | None = None

    # ---------------------------------------------------------------- loading

    @classmethod
    def from_dict(cls, raw: dict[str, Any], source: str | None = None) -> "Scope":
        auth_raw = raw.get("authorization")
        if not isinstance(auth_raw, dict):
            raise ScopeError(
                "scope is missing an 'authorization' block; Sentinel will not run "
                "against targets nobody has authorized in writing"
            )
        auth = Authorization.from_dict(auth_raw)
        if not auth.holder or not auth.reference or not auth.granted_by:
            raise ScopeError(
                "authorization needs holder, reference and granted_by "
                "(e.g. 'self-owned asset', 'N/A - own infrastructure', '<your name>')"
            )
        return cls(
            name=str(raw.get("name") or "unnamed"),
            authorization=auth,
            domains=_clean_list(raw.get("domains")),
            hosts=_clean_list(raw.get("hosts")),
            networks=_clean_list(raw.get("networks")),
            urls=_clean_list(raw.get("urls")),
            model_endpoints=_clean_list(raw.get("model_endpoints")),
            local_paths=_clean_list(raw.get("local_paths")),
            version=int(raw.get("version") or SCHEMA_VERSION),
            source=source,
        )

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "Scope":
        location = Path(path).expanduser()
        if not location.exists():
            raise ScopeError(f"no scope file at {location} - run `sentinel scope init`")
        try:
            raw = json.loads(location.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ScopeError(f"{location} is not valid JSON: {exc}") from exc
        return cls.from_dict(raw, source=str(location))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "authorization": self.authorization.to_dict(),
            "domains": self.domains,
            "hosts": self.hosts,
            "networks": self.networks,
            "urls": self.urls,
            "model_endpoints": self.model_endpoints,
            "local_paths": self.local_paths,
        }

    def save(self, path: str | os.PathLike[str]) -> Path:
        location = Path(path).expanduser()
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return location

    # ------------------------------------------------------------- membership

    def is_empty(self) -> bool:
        return not any(
            [self.domains, self.hosts, self.networks, self.urls,
             self.model_endpoints, self.local_paths]
        )

    def matches_domain(self, candidate: str) -> bool:
        candidate = candidate.strip().rstrip(".").lower()
        for entry in self.domains:
            entry = entry.strip().rstrip(".").lower()
            if not entry:
                continue
            if entry.startswith("*."):
                base = entry[2:]
                if candidate == base or candidate.endswith("." + base):
                    return True
            elif candidate == entry or candidate.endswith("." + entry):
                return True
        return False

    def matches_host(self, candidate: str) -> bool:
        candidate = candidate.strip().lower()
        return any(candidate == h.strip().lower() for h in self.hosts if h.strip())

    def matches_ip(self, candidate: str) -> bool:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            return False
        for entry in self.networks:
            entry = entry.strip()
            if not entry:
                continue
            try:
                if address in ipaddress.ip_network(entry, strict=False):
                    return True
            except ValueError:
                continue
        return False

    def matches_url(self, candidate: str) -> bool:
        host = host_from_url(candidate)
        if not host:
            return False
        return self.matches_domain(host) or self.matches_host(host) or self.matches_ip(host)

    def matches_model_endpoint(self, candidate: str) -> bool:
        candidate = candidate.strip().rstrip("/").lower()
        for entry in self.model_endpoints:
            entry = entry.strip().rstrip("/").lower()
            if not entry:
                continue
            if candidate == entry or candidate.startswith(entry):
                return True
        host = host_from_url(candidate)
        if host and (self.matches_domain(host) or self.matches_host(host)):
            return True
        return False

    def matches_path(self, candidate: str) -> bool:
        try:
            target = Path(candidate).expanduser().resolve()
        except (OSError, RuntimeError):
            return False
        for entry in self.local_paths:
            try:
                allowed = Path(entry).expanduser().resolve()
            except (OSError, RuntimeError):
                continue
            if target == allowed or allowed in target.parents:
                return True
        return False


class ScopeError(Exception):
    """Raised when a scope file is missing, malformed, or expired."""


# ------------------------------------------------------------------- helpers


def _clean_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, Iterable):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def host_from_url(value: str) -> str | None:
    """Pull the hostname out of a URL, bare host, or host:port string."""
    if not value:
        return None
    text = value.strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("/", 1)[0]
    text = text.split("?", 1)[0]
    text = text.split("#", 1)[0]
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    if text.startswith("["):  # IPv6 literal
        end = text.find("]")
        if end != -1:
            return text[1:end]
    text = text.rsplit(":", 1)[0] if text.count(":") == 1 else text
    return text.strip().lower() or None


def looks_like_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def looks_like_domain(value: str) -> bool:
    return bool(_DOMAIN_RE.match(value.strip())) and not looks_like_ip(value)


def looks_like_hostname(value: str) -> bool:
    """Single-label hostnames (a lab box called 'target') are allowed too."""
    if looks_like_ip(value):
        return False
    text = value.strip().rstrip(".")
    if not text or "." in text:
        return looks_like_domain(text)
    return bool(_HOST_LABEL_RE.match(text))


def default_scope_path() -> Path:
    override = os.environ.get("SENTINEL_SCOPE")
    if override:
        return Path(override).expanduser()
    return Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "sentinel" / "scope.json"


def blank_scope(holder: str = "") -> dict[str, Any]:
    today = utcnow().date()
    return {
        "version": SCHEMA_VERSION,
        "name": "my-engagement",
        "authorization": {
            "holder": holder or os.environ.get("USER", "operator"),
            "reference": "SELF-OWNED-ASSETS",
            "granted_by": holder or os.environ.get("USER", "operator"),
            "issued": today.isoformat(),
            "expires": (today + _dt.timedelta(days=30)).isoformat() + "T23:59:59+00:00",
            "notes": (
                "List ONLY assets you own or hold written permission to test. "
                "Sentinel refuses anything outside this file."
            ),
        },
        "domains": [],
        "hosts": ["localhost", "127.0.0.1"],
        "networks": ["127.0.0.0/8"],
        "urls": [],
        "model_endpoints": ["http://localhost:11434", "http://127.0.0.1:8000"],
        "local_paths": ["."],
    }

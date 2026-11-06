"""Authorization records (Rules of Engagement) — hash-chained, tamper-evident.

Har engagement ka ek record hota hai:
    client, contact, scope (targets), sections, start/end, signature, notes

Agent kuch bhi chalane se pehle yahan check karta hai:
    1. Active record hai? (aaj date start..end ke andar)
    2. Target us record ke scope me hai?
    3. Wo section us record me permitted hai?

Har record ek hash-chain me judta hai (`prev_hash`), isliye kisi purane record
ko chupke se badalna pakda ja sakta hai (`verify_chain()`).
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .settings import settings

_lock = threading.Lock()
LEDGER = settings.roe_dir / "ledger.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> float:
    return time.time()


def _day(ts: float | None) -> str:
    if not ts:
        return ""
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sign(payload: dict[str, Any], prev_hash: str) -> str:
    return hashlib.sha256((prev_hash + canonical(payload)).encode("utf-8")).hexdigest()


def _read_ledger() -> list[dict[str, Any]]:
    if not LEDGER.is_file():
        return []
    items: list[dict[str, Any]] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Corrupt authorization ledger at line {len(items)+1}.") from exc
    return items


def _last_hash() -> str:
    items = _read_ledger()
    return items[-1].get("hash", "genesis") if items else "genesis"


def verify_chain() -> dict[str, Any]:
    """Ledger ki integrity check — koi record badla gaya to yahan pakda jayega."""
    items = _read_ledger()
    prev = "genesis"
    for index, record in enumerate(items):
        body = {k: v for k, v in record.items() if k != "hash"}
        expected = sign(body, prev)
        if record.get("hash") != expected:
            return {
                "ok": False,
                "records": len(items),
                "broken_at": index + 1,
                "record_id": record.get("id", "?"),
                "message": f"Record #{index + 1} ka hash match nahi hua — file tamper hui lagti hai.",
            }
        prev = record["hash"]
    return {"ok": True, "records": len(items), "last_hash": prev, "message": "Chain intact."}


# ---------------------------------------------------------------------------
# Record model
# ---------------------------------------------------------------------------
@dataclass
class Authorization:
    id: str
    client: str
    contact: str
    scope: list[str]
    sections: list[str]
    start: float
    end: float
    signer: str
    signature: str
    emergency: str = ""
    notes: str = ""
    created: float = field(default_factory=_now)
    revoked: bool = False
    revoked_at: float | None = None
    created_by: str = "owner"

    # ---- views ---------------------------------------------------------
    def view(self) -> dict[str, Any]:
        data = asdict(self)
        data["start_str"] = _day(self.start)
        data["end_str"] = _day(self.end)
        data["active"] = self.is_active()
        data["scope_text"] = ", ".join(self.scope)
        return data

    def is_active(self, at: float | None = None) -> bool:
        ts = at or _now()
        return (not self.revoked) and self.start <= ts <= self.end

    def days_left(self) -> int:
        return max(0, int((self.end - _now()) // 86400))

    def covers_section(self, section: str) -> bool:
        return "all" in self.sections or section in self.sections


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------
class AuthStore:
    def __init__(self) -> None:
        self._items: dict[str, Authorization] = {}
        self._load()

    def _load(self) -> None:
        check = verify_chain()
        if not check["ok"]:
            raise RuntimeError(f"Authorization ledger failed integrity check: {check['message']}")
        for record in _read_ledger():
            try:
                keys = {f for f in Authorization.__dataclass_fields__}
                self._items[record["id"]] = Authorization(**{k: v for k, v in record.items() if k in keys})
            except (KeyError, TypeError):
                continue

    # ---- write ---------------------------------------------------------
    def create(
        self,
        *,
        client: str,
        contact: str,
        scope: list[str],
        sections: list[str],
        start: float,
        end: float,
        signer: str,
        signature: str,
        emergency: str = "",
        notes: str = "",
    ) -> Authorization:
        clean_scope = [s.strip().lower() for s in scope if s.strip()]
        clean_sections = [s.strip().lower() for s in sections if s.strip()] or ["all"]
        if not clean_scope:
            raise ValueError("Scope khali hai — kam se kam ek target do (jaise example.com ya 10.0.0.0/24).")
        if end <= start:
            raise ValueError("End date, start date ke baad honi chahiye.")
        if not client.strip() or not signer.strip():
            raise ValueError("Client and authorised signer are required.")
        from .scope import parse_target
        from .catalog import SECTIONS
        for pattern in clean_scope:
            if pattern in {"*", "any"}:
                raise ValueError("Wildcard-all scope is not allowed in an authorization record.")
            try:
                parse_target(pattern.removeprefix("*."))
            except ValueError as exc:
                raise ValueError(f"Invalid scope entry {pattern!r}: {exc}") from None
        if any(section not in SECTIONS and section != "all" for section in clean_sections):
            raise ValueError("Unknown section in authorization record.")
        if not signature.strip():
            raise ValueError("Signature zaroori hai — client ka authorization reference (email/PDF id) likho.")
        item = Authorization(
            id=f"roe-{uuid.uuid4().hex[:10]}",
            client=client.strip() or "unknown",
            contact=contact.strip(),
            scope=clean_scope,
            sections=clean_sections,
            start=float(start),
            end=float(end),
            signer=signer.strip(),
            signature=signature.strip(),
            emergency=emergency.strip(),
            notes=notes.strip(),
        )
        with _lock:
            check = verify_chain()
            if not check["ok"]:
                raise ValueError("Authorization ledger integrity failure; refusing to append.")
            body = {k: v for k, v in asdict(item).items() if k != "hash"}
            item_hash = sign(body, _last_hash())
            record = {**body, "hash": item_hash}
            with LEDGER.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._items[item.id] = item
        return item

    def revoke(self, roe_id: str, reason: str = "") -> Authorization | None:
        item = self._items.get(roe_id)
        if item is None:
            return None
        item.revoked = True
        item.revoked_at = _now()
        item.notes = (item.notes + f" | REVOKED: {reason}").strip(" |")
        with _lock:
            check = verify_chain()
            if not check["ok"]:
                raise ValueError("Authorization ledger integrity failure; refusing to append.")
            body = {k: v for k, v in asdict(item).items() if k != "hash"}
            record = {**body, "hash": sign(body, _last_hash())}
            with LEDGER.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return item

    # ---- read ----------------------------------------------------------
    def get(self, roe_id: str) -> Authorization | None:
        return self._items.get(roe_id)

    def all(self, include_expired: bool = True) -> list[Authorization]:
        items = sorted(self._items.values(), key=lambda a: a.created, reverse=True)
        if include_expired:
            return items
        return [a for a in items if a.is_active()]

    def active(self) -> list[Authorization]:
        return [a for a in self._items.values() if a.is_active()]

    def find_for(self, host: str, section: str) -> Authorization | None:
        """Is host + section ke liye koi active record hai?"""
        from .scope import host_matches  # circular import se bachne ke liye

        if not verify_chain()["ok"]:
            return None
        for item in sorted(self._items.values(), key=lambda a: a.end, reverse=True):
            if not item.is_active():
                continue
            if not item.covers_section(section):
                continue
            for pattern in item.scope:
                if host_matches(host, pattern):
                    return item
        return None


records = AuthStore()


def summary() -> dict[str, Any]:
    active = records.active()
    return {
        "total": len(records.all()),
        "active": len(active),
        "next_expiry": min((a.end for a in active), default=None),
        "chain": verify_chain(),
    }


def seed_example() -> dict[str, Any]:
    """v2 no longer seeds public targets. Use the offline demo instead."""
    raise ValueError("Public demo targets removed. Use /api/demo/mission for the offline fixture, or create a real RoE record.")

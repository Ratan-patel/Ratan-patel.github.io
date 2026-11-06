"""Human-in-the-loop approvals — mobile par ek tap.

Intrusive tools (hydra, metasploit, sqlmap, responder...) aur shell commands
hamesha approval se guzarte hain. Pending approval mobile console me card ki
tarah dikhta hai; approve hone par `continuation(approved)` chal jaati hai.

TTL 20 min — uske baad expire (dobara maango).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from . import audit

TTL_SECONDS = 20 * 60
_items: dict[str, "Approval"] = {}
_lock = threading.Lock()


@dataclass
class Approval:
    id: str
    kind: str                  # tool | shell | install | report
    summary: str
    command: str
    target: str
    section: str
    actor: str
    created: float
    dangerous: bool = True
    status: str = "pending"    # pending | approved | denied | expired | cancelled
    decided_at: float | None = None
    decided_by: str = ""
    note: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    continuation: Callable[[bool, "Approval"], None] | None = field(default=None, repr=False)

    def expired(self) -> bool:
        return self.status == "pending" and (time.time() - self.created) > TTL_SECONDS

    def effective_status(self) -> str:
        return "expired" if self.expired() else self.status

    def view(self) -> dict[str, Any]:
        return {
            "id": self.id, "kind": self.kind, "summary": self.summary, "command": self.command,
            "target": self.target, "section": self.section, "actor": self.actor,
            "created": self.created, "created_str": time.strftime("%H:%M:%S", time.localtime(self.created)),
            "dangerous": self.dangerous, "status": self.effective_status(),
            "expires_in": max(0, int(TTL_SECONDS - (time.time() - self.created))),
            "decided_by": self.decided_by, "note": self.note, "payload": self.payload,
        }


def create(
    *,
    kind: str,
    summary: str,
    command: str,
    target: str,
    section: str,
    actor: str,
    dangerous: bool = True,
    payload: dict[str, Any] | None = None,
    continuation: Callable[[bool, Approval], None] | None = None,
) -> Approval:
    item = Approval(
        id=f"ap-{uuid.uuid4().hex[:8]}",
        kind=kind, summary=summary, command=command, target=target, section=section,
        actor=actor, created=time.time(), dangerous=dangerous,
        payload=payload or {}, continuation=continuation,
    )
    with _lock:
        _items[item.id] = item
    audit.log("approval_requested", evidence=True, approval=item.id, kind=kind, target=target,
              section=section, command=command, actor=actor)
    return item


def get(approval_id: str) -> Approval | None:
    with _lock:
        return _items.get(approval_id)


def decide(approval_id: str, approved: bool, actor: str, note: str = "") -> Approval:
    item = get(approval_id)
    if item is None:
        raise KeyError(approval_id)
    if item.effective_status() == "expired":
        item.status = "expired"
        raise ValueError("Approval expire ho gaya (20 min) — dobara maango.")
    if item.status != "pending":
        raise ValueError(f"Approval pehle hi '{item.status}' hai.")
    item.status = "approved" if approved else "denied"
    item.decided_at = time.time()
    item.decided_by = actor
    item.note = note
    audit.log("approval_decided", evidence=True, approval=item.id, approved=approved,
              actor=actor, note=note, command=item.command)
    if item.continuation is not None:
        threading.Thread(target=_continue, args=(item, approved), daemon=True).start()
    return item


def _continue(item: Approval, approved: bool) -> None:
    try:
        item.continuation(approved, item)  # type: ignore[misc]
    except Exception as exc:  # pragma: no cover - defensive
        item.note = f"continuation error: {exc}"
        audit.log("approval_error", approval=item.id, error=str(exc))


def pending() -> list[dict[str, Any]]:
    with _lock:
        items = [a for a in _items.values() if a.effective_status() == "pending"]
    return [a.view() for a in sorted(items, key=lambda a: a.created)]


def pending_count() -> int:
    return len(pending())


def list_all(limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        items = sorted(_items.values(), key=lambda a: a.created, reverse=True)
    return [a.view() for a in items[:limit]]


def cancel(approval_id: str, reason: str = "auto-denied") -> None:
    item = get(approval_id)
    if item and item.status == "pending":
        item.status = "cancelled"
        item.decided_by = "system"
        item.note = reason
        item.continuation = None
        audit.log("approval_cancelled", approval=item.id, reason=reason)

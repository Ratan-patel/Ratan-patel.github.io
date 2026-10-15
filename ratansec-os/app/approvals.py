"""Human-in-the-loop approvals.

Kuch actions (sqlmap/hydra jaise intrusive tools, ya jab target scope me
explicitly na ho) ke liye user ka confirmation zaroori hai. Pending approval
yahan store hota hai; approve hone par attached `continuation` chal jaati hai.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from . import audit

TTL_SECONDS = 1800  # 30 min ke baad approval expire
APPROVALS: dict[str, "Approval"] = {}
_lock = threading.Lock()


def approval_required(dangerous: bool, mode: str) -> bool:
    """Dangerous tool -> hamesha human approval. Manual mode -> har scan approval."""
    if dangerous:
        return True
    return mode == "manual"


@dataclass
class Approval:
    id: str
    kind: str                     # scan | command
    summary: str
    command: str
    target: str
    actor: str
    created: float
    run_id: str | None = None
    status: str = "pending"       # pending | approved | denied | expired
    decided_at: float | None = None
    decided_by: str | None = None
    result: str = ""
    continuation: Callable[[bool], None] | None = field(default=None, repr=False)

    def view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "summary": self.summary,
            "command": self.command,
            "target": self.target,
            "actor": self.actor,
            "created": self.created,
            "run_id": self.run_id,
            "status": self.status if not self._expired() else "expired",
            "expires_in": max(0, int(TTL_SECONDS - (time.time() - self.created))),
            "result": self.result,
        }

    def _expired(self) -> bool:
        return self.status == "pending" and (time.time() - self.created) > TTL_SECONDS


def create(
    *,
    kind: str,
    summary: str,
    command: str,
    target: str,
    actor: str,
    run_id: str | None = None,
    continuation: Callable[[bool], None] | None = None,
) -> Approval:
    approval = Approval(
        id=uuid.uuid4().hex[:10],
        kind=kind,
        summary=summary,
        command=command,
        target=target,
        actor=actor,
        created=time.time(),
        run_id=run_id,
        continuation=continuation,
    )
    with _lock:
        APPROVALS[approval.id] = approval
    audit.log("approval_requested", approval=approval.id, kind=kind, target=target, command=command, actor=actor)
    return approval


def get(approval_id: str) -> Approval | None:
    with _lock:
        return APPROVALS.get(approval_id)


def list_all(limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        items = sorted(APPROVALS.values(), key=lambda a: a.created, reverse=True)
    return [a.view() for a in items[:limit]]


def pending_count() -> int:
    with _lock:
        return sum(1 for a in APPROVALS.values() if a.status == "pending" and not a._expired())


def decide(approval_id: str, approved: bool, actor: str, reason: str = "") -> Approval:
    approval = get(approval_id)
    if approval is None:
        raise KeyError("approval nahi mila")
    if approval.status != "pending":
        raise ValueError(f"approval already '{approval.status}' hai")
    if approval._expired():
        approval.status = "expired"
        raise ValueError("approval expire ho gaya (30 min) — dobara chalao")

    approval.status = "approved" if approved else "denied"
    approval.decided_at = time.time()
    approval.decided_by = actor
    approval.result = reason or ("approved" if approved else "denied")
    audit.log("approval_decided", approval=approval.id, approved=approved, actor=actor, command=approval.command)

    if approval.continuation is not None:
        thread = threading.Thread(
            target=_safe_continue, args=(approval, approved), daemon=True, name=f"approval-{approval.id}"
        )
        thread.start()
    return approval


def _safe_continue(approval: Approval, approved: bool) -> None:
    try:
        approval.continuation(approved)  # type: ignore[misc]
    except Exception as exc:  # pragma: no cover - defensive
        approval.result = f"continuation error: {exc}"
        audit.log("approval_continuation_error", approval=approval.id, error=str(exc))


def cancel(approval_id: str, reason: str = "cancelled") -> Approval | None:
    """Approval ko bina continuation chalaye band karo (auto-deny ke liye)."""
    approval = get(approval_id)
    if approval is None:
        return None
    if approval.status == "pending":
        approval.status = "denied"
        approval.decided_at = time.time()
        approval.decided_by = "system"
        approval.result = reason
        approval.continuation = None
        audit.log("approval_cancelled", approval=approval.id, reason=reason)
    return approval

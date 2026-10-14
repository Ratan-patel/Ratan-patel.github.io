"""REST API — dashboard, CLI aur kisi bhi external client ke liye.

Auth: APP_PASSWORD set hone par cookie session ya `Authorization: Bearer <token>`.
Rate limits + scope checks har scan endpoint par lagte hain.
"""

from __future__ import annotations

import platform
import socket
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from . import ai, approvals, audit, report
from .config import APP_NAME, APP_TAGLINE, VERSION, settings
from .executor import runs
from .security import (
    SESSION_COOKIE,
    check_password,
    client_ip,
    enforce_rate,
    is_authenticated,
    parse_target,
    require_auth,
    session_cookie_value,
)
from .tools import PROFILES, all_tool_status, build_profile, profile_catalog, TOOLS, tool_status

api = APIRouter(prefix="/api")


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------
class LoginBody(BaseModel):
    password: str = Field(default="", max_length=256)


class ScanBody(BaseModel):
    target: str = Field(..., max_length=255)
    profile: str = Field(default="quick", max_length=32)


class ChatBody(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    conversation_id: str = Field(default="", max_length=64)
    model: str | None = Field(default=None, max_length=80)


class ApprovalBody(BaseModel):
    approved: bool = False
    reason: str = Field(default="", max_length=300)


class ReportBody(BaseModel):
    name: str = Field(default="", max_length=120)
    ai: bool = True


# --------------------------------------------------------------------------
# Meta / health
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _os_info() -> dict[str, Any]:
    pretty = "unknown"
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("PRETTY_NAME="):
                pretty = line.split("=", 1)[1].strip().strip('"')
                break
    except OSError:
        pass
    return {
        "distribution": pretty,
        "kernel": platform.release(),
        "python": platform.python_version(),
        "hostname": socket.gethostname(),
        "docker": Path("/.dockerenv").exists(),
    }


@api.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "app": APP_NAME, "version": VERSION, "ts": time.time()}


@api.get("/meta")
def meta() -> dict[str, Any]:
    return {
        "app": APP_NAME,
        "tagline": APP_TAGLINE,
        "version": VERSION,
        "profiles": profile_catalog(),
        "tools_total": len(TOOLS),
        "environment": _os_info(),
    }


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
@api.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict[str, Any]:
    if not settings.secure:
        return {"ok": True, "auth_required": False, "message": "APP_PASSWORD set nahi hai — auth disabled."}
    enforce_rate(f"login:{client_ip(request)}", 10, 300, "Bahut zyada login attempts. 5 min baad try karo.")
    if not check_password(body.password):
        audit.log("login_failed", actor=client_ip(request))
        raise HTTPException(status_code=401, detail="Password galat hai.")
    response.set_cookie(
        SESSION_COOKIE,
        session_cookie_value(),
        httponly=True,
        samesite="strict",
        max_age=60 * 60 * 24 * 7,
    )
    audit.log("login_ok", actor=client_ip(request))
    return {"ok": True, "auth_required": True}


@api.post("/logout")
def logout(response: Response) -> dict[str, Any]:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@api.get("/status")
def status(request: Request) -> dict[str, Any]:
    authenticated = is_authenticated(request)
    tools = all_tool_status()
    installed = [t for t in tools if t["installed"]]
    active = [r for r in runs.list(200) if r.status in ("queued", "running")]
    data: dict[str, Any] = {
        "app": APP_NAME,
        "version": VERSION,
        "auth_required": settings.secure,
        "authenticated": authenticated,
        "ai": ai.ai_status(),
        "approvals_pending": approvals.pending_count(),
        "runs_active": len(active),
        "runs_total": len(runs.list(200)),
    }
    if authenticated:
        data["scope"] = {
            "allowed_targets": settings.allowed_targets,
            "allow_any_target": settings.allow_any_target,
            "scope_override": settings.allow_scope_override,
            "allow_local_targets": settings.allow_local_targets,
            "approval_mode": settings.effective_approval_mode,
            "human_approval_for_dangerous": True,
            "install_allowed": settings.allow_install,
        }
        data["limits"] = {
            "max_scan_seconds": settings.max_scan_seconds,
            "max_concurrent_scans": settings.max_concurrent_scans,
            "ai_max_steps": settings.ai_max_steps,
        }
        data["environment"] = _os_info()
        data["tools"] = {"installed": len(installed), "total": len(tools), "missing": len(tools) - len(installed)}
    return data


# --------------------------------------------------------------------------
# Tools / profiles
# --------------------------------------------------------------------------
@api.get("/tools")
def tools_list(refresh: bool = Query(default=False), actor: str = Depends(require_auth)) -> dict[str, Any]:
    return {"tools": all_tool_status(refresh=refresh)}


@api.get("/profiles")
def profiles_list(actor: str = Depends(require_auth)) -> dict[str, Any]:
    return {"profiles": profile_catalog()}


# --------------------------------------------------------------------------
# Scans
# --------------------------------------------------------------------------
def _execute_plan(run_id: str, steps) -> None:
    run = runs.get(run_id)
    if run is None:
        return
    runs.execute_sync(run, steps)


@api.post("/scan")
def start_scan(body: ScanBody, request: Request, actor: str = Depends(require_auth)) -> dict[str, Any]:
    enforce_rate(f"scan:{actor}", 12, 60, "Bohot jaldi scans ho rahe hain — 1 min ruk jao.")
    try:
        parsed = parse_target(body.target)
        scope = check_target_for_ui(body.target)
        steps = build_profile(body.profile, parsed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    dangerous = any(step.needs_approval for step in steps)
    run = runs.create(body.target, steps, "ui", actor, body.profile)

    if approvals.approval_required(dangerous, settings.effective_approval_mode):
        run.note = "Approval pending — approve karne par scan chalega."
        command_preview = "\n".join(step.display() for step in steps)
        title = PROFILES[body.profile].title

        def continuation(approved: bool) -> None:
            if approved:
                run.note = ""
                _execute_plan(run.id, steps)
            else:
                run.status = "cancelled"
                run.note = "User ne approval deny kar diya."

        approval = approvals.create(
            kind="scan",
            summary=f"'{scope.host}' par {title} ({len(steps)} steps)",
            command=command_preview,
            target=scope.host,
            actor=actor,
            run_id=run.id,
            continuation=continuation,
        )
        return {
            "status": "approval_required",
            "run": run.summary(),
            "approval": approval.view(),
            "reason": (
                "Intrusive tool (sqlmap/hydra) — human approval mandatory hai."
                if dangerous
                else "Scope allowlist set nahi hai (manual approval mode)."
            ),
        }

    runs.start_background(run, steps)
    audit.log("ui_scan", run=run.id, target=run.target, profile=run.profile, actor=actor)
    return {"status": "running", "run": run.summary(), "scope": {"host": scope.host, "reason": scope.reason}}


def check_target_for_ui(target: str):
    """UI scans ke liye scope check (security module ka wrapper)."""
    from .security import check_target

    return check_target(target, source="ui")


@api.get("/runs")
def list_runs(limit: int = Query(default=50, ge=1, le=200), actor: str = Depends(require_auth)) -> dict[str, Any]:
    return {"runs": [r.summary() for r in runs.list(limit)]}


@api.get("/runs/{run_id}")
def get_run(run_id: str, actor: str = Depends(require_auth)) -> dict[str, Any]:
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run nahi mila.")
    return {"run": run.detail()}


@api.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, actor: str = Depends(require_auth)) -> dict[str, Any]:
    if not runs.cancel(run_id):
        raise HTTPException(status_code=404, detail="Run nahi mila.")
    return {"ok": True, "message": "Cancel request bhej di gayi."}


@api.delete("/runs/{run_id}")
def delete_run(run_id: str, actor: str = Depends(require_auth)) -> dict[str, Any]:
    if not runs.delete(run_id):
        raise HTTPException(status_code=404, detail="Run nahi mila.")
    return {"ok": True}


@api.post("/runs/{run_id}/report")
def make_report(run_id: str, body: ReportBody, actor: str = Depends(require_auth)) -> dict[str, Any]:
    enforce_rate(f"report:{actor}", 20, 60, "Report generation rate limit — thoda ruk jao.")
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run nahi mila.")
    summary = None
    if body.ai:
        summary = ai.summarize_run(run)  # AI configured na ho to None
    path = report.save(run, body.name or None, summary)
    audit.log("report_generated", run=run.id, file=path.name, actor=actor, ai=bool(summary))
    return {"file": path.name, "ai_summary": summary or "", "ai_used": bool(summary)}


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------
@api.get("/reports")
def reports_list(actor: str = Depends(require_auth)) -> dict[str, Any]:
    return {"reports": report.list_reports()}


@api.get("/reports/{name}")
def report_read(name: str, actor: str = Depends(require_auth)) -> dict[str, Any]:
    try:
        return {"name": name, "content": report.read_report(name)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report nahi mili.")


@api.delete("/reports/{name}")
def report_delete(name: str, actor: str = Depends(require_auth)) -> dict[str, Any]:
    if not report.delete_report(name):
        raise HTTPException(status_code=404, detail="Report nahi mili.")
    audit.log("report_deleted", file=name, actor=actor)
    return {"ok": True}


# --------------------------------------------------------------------------
# Approvals (human-in-the-loop)
# --------------------------------------------------------------------------
@api.get("/approvals")
def approvals_list(actor: str = Depends(require_auth)) -> dict[str, Any]:
    return {"approvals": approvals.list_all(), "pending": approvals.pending_count()}


@api.post("/approvals/{approval_id}")
def approvals_decide(approval_id: str, body: ApprovalBody, actor: str = Depends(require_auth)) -> dict[str, Any]:
    try:
        approval = approvals.decide(approval_id, body.approved, actor, body.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Approval nahi mila.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"approval": approval.view(), "message": "Approved — action chal raha hai." if approval.status == "approved" else "Denied."}


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------
@api.get("/audit")
def audit_list(limit: int = Query(default=100, ge=1, le=500), actor: str = Depends(require_auth)) -> dict[str, Any]:
    return {"events": audit.recent(limit)}


# --------------------------------------------------------------------------
# AI chat
# --------------------------------------------------------------------------
@api.post("/chat")
def chat(body: ChatBody, request: Request, actor: str = Depends(require_auth)) -> dict[str, Any]:
    enforce_rate(f"chat:{actor}", 25, 60, "Chat rate limit — thodi der ruk jao.")
    if not body.messages:
        raise HTTPException(status_code=400, detail="Messages khali hain.")
    conversation_id = body.conversation_id or f"conv-{int(time.time() * 1000)}"
    try:
        result = ai.run_agent(
            body.messages,
            actor=actor,
            conversation_id=conversation_id,
            model=body.model,
        )
    except ai.AIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"ok": True, **result}


@api.get("/chat/followup/{conversation_id}")
def chat_followup(conversation_id: str, actor: str = Depends(require_auth)) -> dict[str, Any]:
    item = ai.get_followup(conversation_id)
    if item is None:
        return {"status": "pending"}
    return item


@api.delete("/chat/followup/{conversation_id}")
def chat_followup_clear(conversation_id: str, actor: str = Depends(require_auth)) -> dict[str, Any]:
    ai.clear_followup(conversation_id)
    return {"ok": True}


# --------------------------------------------------------------------------
# Install helper (opt-in)
# --------------------------------------------------------------------------
class InstallBody(BaseModel):
    packages: list[str] = Field(default_factory=list, max_length=20)


@api.post("/install")
def install(body: InstallBody, actor: str = Depends(require_auth)) -> dict[str, Any]:
    """Missing tools install karne ka helper — ALLOW_INSTALL=1 hone par hi chalta hai."""
    if not settings.allow_install:
        raise HTTPException(
            status_code=403,
            detail="Install endpoint disabled hai. ALLOW_INSTALL=1 set karo (aur container me root chahiye).",
        )
    from .executor import run_command
    from .tools import missing_packages

    packages = [p for p in (body.packages or missing_packages()) if p.replace("-", "").replace(".", "").isalnum()]
    if not packages:
        return {"ok": True, "message": "Kuch install karne ki zarurat nahi — sab tools available hain."}
    argv = ["apt-get", "update"]
    result = run_command(argv, timeout=180)
    argv2 = ["apt-get", "install", "-y", "--no-install-recommends"] + packages
    result2 = run_command(argv2, timeout=600)
    audit.log("install", packages=packages, actor=actor, status=result2["status"])
    return {
        "ok": result2["status"] == "done",
        "packages": packages,
        "update_output": result["output"][-2000:],
        "install_output": result2["output"][-4000:],
    }

"""Super Agent REST API + dashboard.

Auth do tarah se:
  * Web dashboard : APP_PASSWORD -> signed cookie session
  * Mobile / CLI  : `X-Agent-Token: <SUPERAGENT_API_TOKEN>` (ya ?token= ya
                    `Authorization: Bearer ...`) — phone console isi se chalta hai.

Endpoints (prefix /api):
  GET  status            POST login / logout
  GET  sections          GET  tools
  POST scope/check       GET  scope
  GET  records           POST records            POST records/{id}/revoke
  POST agent/chat        GET  agent/followup/{session}
  POST agent/reset
  POST command           POST command/shell      GET  runs   GET runs/{id}
  POST runs/{id}/cancel
  GET  approvals         POST approvals/{id}
  GET  reports           GET  reports/{name}     POST reports  DELETE reports/{name}
  GET  reports/{name}/html
  GET  audit             GET  audit/verify       POST evidence/bundle
  POST install
"""

from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote as urlquote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from . import agent, approvals, audit, catalog, records, report, runner, scope
from .settings import APP_NAME, VERSION, quote, settings

api = APIRouter(prefix="/api")

COOKIE = "sa_session"
_RATE: dict[str, list[float]] = {}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def _session_value() -> str:
    secret = (settings.app_password or "no-password").encode()
    return hmac.new(secret, b"superagent-session-v1", hashlib.sha256).hexdigest()


def _token_ok(token: str) -> bool:
    token = (token or "").strip()
    if not token:
        return False
    for candidate in (settings.api_token, settings.mobile_token):
        if candidate and hmac.compare_digest(token, candidate):
            return True
    return False


def _client(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown"))


def _rate(key: str, limit: int, window: int) -> None:
    now = time.time()
    bucket = _RATE.setdefault(key, [])
    bucket[:] = [t for t in bucket if now - t < window]
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit — thoda ruk kar try karo.")
    bucket.append(now)


def require_auth(request: Request) -> str:
    if not settings.auth_required:
        return "owner"
    header = request.headers.get("x-agent-token", "")
    auth = request.headers.get("authorization", "")
    bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    query = request.query_params.get("token", "")
    for token in (header, bearer, query):
        if _token_ok(token):
            return "api-token"
    if request.cookies.get(COOKIE) == _session_value():
        return "owner"
    raise HTTPException(status_code=401, detail="Login zaroori hai (password ya API token).")


Authenticated = Depends(require_auth)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class LoginBody(BaseModel):
    password: str = Field(default="", max_length=256)


class ChatBody(BaseModel):
    message: str = Field(..., max_length=8000)
    session_id: str = Field(default="", max_length=64)
    auto_approve: bool | None = None
    model: str | None = Field(default=None, max_length=120)


class CommandBody(BaseModel):
    tool: str = Field(..., max_length=60)
    target: str = Field(default="", max_length=2048)
    flags: dict[str, Any] = Field(default_factory=dict)
    timeout: int = Field(default=120, ge=5, le=1800)
    label: str = Field(default="", max_length=160)


class ShellBody(BaseModel):
    command: str = Field(..., max_length=4000)
    timeout: int = Field(default=120, ge=5, le=1800)
    reason: str = Field(default="", max_length=300)


class ApprovalBody(BaseModel):
    approved: bool = False
    note: str = Field(default="", max_length=300)


class RecordBody(BaseModel):
    client: str = Field(default="", max_length=120)
    contact: str = Field(default="", max_length=160)
    scope: list[str] = Field(default_factory=list, max_length=40)
    sections: list[str] = Field(default_factory=lambda: ["all"], max_length=16)
    start: str = Field(default="", max_length=32)   # YYYY-MM-DD
    end: str = Field(default="", max_length=32)
    signer: str = Field(default="", max_length=120)
    signature: str = Field(default="", max_length=300)
    emergency: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=2000)


class ReportBody(BaseModel):
    title: str = Field(default="", max_length=160)
    markdown: str = Field(..., max_length=200000)


class ScopeCheckBody(BaseModel):
    target: str = Field(..., max_length=2048)
    section: str = Field(default="recon", max_length=40)


class InstallBody(BaseModel):
    package: str = Field(..., max_length=80)


# ---------------------------------------------------------------------------
# Auth / status
# ---------------------------------------------------------------------------
@api.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict[str, Any]:
    if not settings.auth_required:
        return {"ok": True, "auth_required": False}
    _rate(f"login:{_client(request)}", 10, 300)
    if not settings.app_password or not hmac.compare_digest(body.password, settings.app_password):
        audit.log("login_failed", actor=_client(request))
        raise HTTPException(status_code=401, detail="Password galat hai.")
    response.set_cookie(COOKIE, _session_value(), httponly=True, samesite="lax", max_age=7 * 86400, path="/")
    audit.log("login_ok", actor=_client(request))
    return {"ok": True, "auth_required": True}


@api.post("/logout")
def logout(response: Response) -> dict[str, Any]:
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


def _authenticated(request: Request) -> bool:
    if not settings.auth_required:
        return True
    try:
        require_auth(request)
        return True
    except HTTPException:
        return False


@api.get("/status")
def status(request: Request) -> dict[str, Any]:
    data = {
        "app": APP_NAME,
        "version": VERSION,
        "auth_required": settings.auth_required,
        "authenticated": _authenticated(request),
        "ai": {"configured": settings.ai_configured, "model": settings.model},
        "tools_total": catalog.TOTAL_TOOLS,
        "intrusive_tools": catalog.INTRUSIVE_COUNT,
        "approvals_pending": approvals.pending_count(),
        "records_active": len(records.records.active()),
        "shell_allowed": settings.allow_shell,
        "install_allowed": settings.allow_install,
        "mobile_token": bool(settings.mobile_token or settings.api_token),
    }
    if data["authenticated"]:
        data["agent"] = agent.ai_status()
        data["scope"] = scope.scope_payload()
    return data


# ---------------------------------------------------------------------------
# Sections / tools
# ---------------------------------------------------------------------------
@api.get("/sections")
def sections(_a: str = Authenticated) -> dict[str, Any]:
    payload = catalog.sections_payload()
    for section in payload:
        for tool in section["tools"]:
            tool["installed"] = runner.which(tool["binary"]) is not None
    return {"sections": payload, "total": catalog.TOTAL_TOOLS, "intrusive": catalog.INTRUSIVE_COUNT}


@api.get("/tools")
def tools(_a: str = Authenticated) -> dict[str, Any]:
    items = []
    for tool in catalog.TOOLS.values():
        items.append({
            "name": tool.name, "section": tool.section, "binary": tool.binary, "package": tool.package,
            "summary": tool.summary, "flags": tool.flags, "intrusive": tool.intrusive,
            "offline": tool.offline, "installed": runner.which(tool.binary) is not None,
            "install_hint": tool.install_hint, "example": tool.example,
        })
    installed = sum(1 for i in items if i["installed"])
    return {"tools": items, "installed": installed, "total": len(items)}


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------
@api.get("/scope")
def scope_info(_a: str = Authenticated) -> dict[str, Any]:
    return scope.scope_payload()


@api.post("/scope/check")
def scope_check(body: ScopeCheckBody, _a: str = Authenticated) -> dict[str, Any]:
    decision = scope.check(body.target, body.section)
    return decision.view()


# ---------------------------------------------------------------------------
# Authorization records
# ---------------------------------------------------------------------------
def _parse_day(value: str, fallback: float) -> float:
    value = (value or "").strip()
    if not value:
        return fallback
    try:
        return time.mktime(time.strptime(value, "%Y-%m-%d"))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Date format YYYY-MM-DD hona chahiye: '{value}'")


@api.get("/records")
def records_list(_a: str = Authenticated) -> dict[str, Any]:
    items = [r.view() for r in records.records.all()]
    return {"records": items, "summary": records.summary()}


@api.post("/records")
def records_create(body: RecordBody, actor: str = Authenticated) -> dict[str, Any]:
    now = time.time()
    start = _parse_day(body.start, now - 3600)
    end = _parse_day(body.end, now + 30 * 86400)
    end = end + 86399 if end else end  # end-of-day include
    try:
        item = records.records.create(
            client=body.client, contact=body.contact, scope=body.scope, sections=body.sections,
            start=start, end=end, signer=body.signer, signature=body.signature,
            emergency=body.emergency, notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    audit.log("roe_created", evidence=True, roe=item.id, client=item.client, scope=item.scope,
              sections=item.sections, actor=actor)
    return {"record": item.view(), "chain": records.verify_chain()}


@api.post("/records/{roe_id}/revoke")
def records_revoke(roe_id: str, actor: str = Authenticated) -> dict[str, Any]:
    item = records.records.revoke(roe_id, reason=f"revoked by {actor}")
    if item is None:
        raise HTTPException(status_code=404, detail="Record nahi mila.")
    audit.log("roe_revoked", evidence=True, roe=roe_id, actor=actor)
    return {"record": item.view()}


@api.post("/records/seed-demo")
def records_seed(actor: str = Authenticated) -> dict[str, Any]:
    audit.log("roe_seed_demo", evidence=True, actor=actor)
    return {"record": records.seed_example()}


# ---------------------------------------------------------------------------
# Agent chat
# ---------------------------------------------------------------------------
@api.post("/agent/chat")
def agent_chat(body: ChatBody, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _rate(f"chat:{actor}", 40, 60)
    if not settings.ai_configured:
        raise HTTPException(status_code=503, detail="AI key set nahi hai — SUPERAGENT_API_KEY daalo.")
    session_id = body.session_id or f"s-{int(time.time() * 1000)}"
    try:
        result = agent.run_turn(
            session_id, body.message, actor=actor,
            auto_approve=body.auto_approve, model=body.model,
        )
    except agent.AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    audit.log("agent_reply", session=session_id, chars=len(result.get("reply", "")),
              awaiting=bool(result.get("awaiting_approval")), actor=actor)
    return {"ok": True, **result, "client": _client(request)}


@api.get("/agent/followup/{session_id}")
def agent_followup(session_id: str, _a: str = Authenticated) -> dict[str, Any]:
    item = agent.get_followup(session_id)
    return item or {"status": "pending"}


@api.delete("/agent/followup/{session_id}")
def agent_followup_clear(session_id: str, _a: str = Authenticated) -> dict[str, Any]:
    agent.clear_followup(session_id)
    return {"ok": True}


@api.post("/agent/reset")
def agent_reset(body: dict[str, str], _a: str = Authenticated) -> dict[str, Any]:
    agent.reset_session(body.get("session_id", ""))
    return {"ok": True}


@api.get("/agent/sessions")
def agent_sessions(_a: str = Authenticated) -> dict[str, Any]:
    return {"pending_approvals": approvals.pending()}


# ---------------------------------------------------------------------------
# Commands / runs
# ---------------------------------------------------------------------------
@api.post("/command")
def command(body: CommandBody, actor: str = Authenticated) -> dict[str, Any]:
    _rate(f"cmd:{actor}", 60, 60)
    spec = catalog.TOOLS.get(body.tool.strip().lower())
    if spec is None:
        raise HTTPException(status_code=400, detail=f"'{body.tool}' catalog me nahi hai.")
    if body.target:
        decision = scope.check(body.target, spec.section)
        if not decision.allowed:
            raise HTTPException(status_code=403, detail=decision.reason)
    try:
        cmd = runner.build_tool_command(
            spec.name, target=body.target, flags=body.flags,
            label=body.label, actor=actor, timeout=body.timeout,
        )
    except (runner.BuildError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from .settings import effective_approval

    if effective_approval(False, spec.intrusive):
        def continuation(approved: bool, approval: approvals.Approval) -> None:
            if approved:
                runner.commands.submit(cmd)
                audit.log("approved_manual_cmd", evidence=True, cmd=cmd.display,
                          approval=approval.id, actor=actor)

        approval = approvals.create(
            kind="tool", summary=f"{spec.name} — {body.target or 'local'}",
            command=cmd.display, target=body.target or "-", section=spec.section,
            actor=actor, dangerous=spec.intrusive, continuation=continuation,
        )
        return {"status": "approval_required", "approval": approval.view(), "command": cmd.display}

    result = runner.commands.submit(cmd)
    audit.log("ui_command", cmd_id=result.id, display=cmd.display, actor=actor)
    return {"status": "running", "run": result.view(tail=4000)}


@api.post("/command/shell")
def command_shell(body: ShellBody, actor: str = Authenticated) -> dict[str, Any]:
    if not settings.allow_shell:
        raise HTTPException(status_code=403, detail="Shell mode off hai (SUPERAGENT_ALLOW_SHELL=0).")
    try:
        cmd = runner.build_shell_command(body.command, actor=actor, timeout=body.timeout)
    except runner.BuildError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    def continuation(approved: bool, approval: approvals.Approval) -> None:
        if approved:
            runner.commands.submit(cmd)
            audit.log("approved_shell", evidence=True, cmd=cmd.display, approval=approval.id, actor=actor)

    approval = approvals.create(
        kind="shell", summary=f"shell: {body.command[:110]}", command=cmd.display,
        target="-", section="utility", actor=actor, dangerous=True,
        payload={"reason": body.reason}, continuation=continuation,
    )
    return {"status": "approval_required", "approval": approval.view(), "command": cmd.display}


@api.get("/runs")
def runs_list(limit: int = Query(default=30, ge=1, le=200), _a: str = Authenticated) -> dict[str, Any]:
    items = [r.view(tail=6000) for r in runner.commands.list(limit)]
    return {"runs": items}


@api.get("/runs/{run_id}")
def runs_get(run_id: str, tail: int = Query(default=24000, ge=500, le=200000), _a: str = Authenticated) -> dict[str, Any]:
    result = runner.commands.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run nahi mila.")
    return {"run": result.view(tail=tail)}


@api.post("/runs/{run_id}/cancel")
def runs_cancel(run_id: str, _a: str = Authenticated) -> dict[str, Any]:
    if not runner.commands.cancel(run_id):
        raise HTTPException(status_code=404, detail="Run nahi mila.")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------
@api.get("/approvals")
def approvals_list(_a: str = Authenticated) -> dict[str, Any]:
    return {"approvals": approvals.list_all(), "pending": approvals.pending_count()}


@api.post("/approvals/{approval_id}")
def approvals_decide(approval_id: str, body: ApprovalBody, actor: str = Authenticated) -> dict[str, Any]:
    try:
        item = approvals.decide(approval_id, body.approved, actor, body.note)
    except KeyError:
        raise HTTPException(status_code=404, detail="Approval nahi mila.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"approval": item.view(),
            "message": "Approved — chal raha hai." if item.status == "approved" else "Denied."}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
@api.get("/reports")
def reports_list(_a: str = Authenticated) -> dict[str, Any]:
    return {"reports": report.list_reports()}


@api.post("/reports")
def reports_create(body: ReportBody, actor: str = Authenticated) -> dict[str, Any]:
    path = report.save(body.title or "Super Agent Report", body.markdown, client=actor)
    audit.log("report_saved", evidence=True, file=path.name, actor=actor)
    return {"file": path.name}


@api.get("/reports/{name}")
def reports_read(name: str, _a: str = Authenticated) -> dict[str, Any]:
    try:
        return {"name": name, "content": report.read(name), "html": report.md_to_html(report.read(name))}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report nahi mili.")


@api.delete("/reports/{name}")
def reports_delete(name: str, actor: str = Authenticated) -> dict[str, Any]:
    if not report.delete(name):
        raise HTTPException(status_code=404, detail="Report nahi mili.")
    audit.log("report_deleted", file=name, actor=actor)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Audit / evidence
# ---------------------------------------------------------------------------
@api.get("/audit")
def audit_list(limit: int = Query(default=120, ge=1, le=1000), _a: str = Authenticated) -> dict[str, Any]:
    return {"events": audit.recent(limit), "verify": audit.verify()}


@api.get("/audit/verify")
def audit_verify(_a: str = Authenticated) -> dict[str, Any]:
    return {"audit": audit.verify(), "evidence": audit.verify(audit.EVIDENCE_FILE),
            "records": records.verify_chain()}


@api.post("/evidence/bundle")
def evidence_bundle(actor: str = Authenticated) -> dict[str, Any]:
    path = audit.export_bundle()
    audit.log("evidence_bundle_ui", file=path.name, actor=actor)
    return {"file": path.name, "download": f"/api/evidence/{urlquote(path.name)}"}


@api.get("/evidence/{name}")
def evidence_download(name: str, _a: str = Authenticated):
    from fastapi.responses import FileResponse

    safe = Path(name).name
    path = settings.evidence_dir / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File nahi mili.")
    return FileResponse(path, filename=safe, media_type="application/zip")


# ---------------------------------------------------------------------------
# Install thin wrapper
# ---------------------------------------------------------------------------
@api.post("/install")
def install(body: InstallBody, actor: str = Authenticated) -> dict[str, Any]:
    if not settings.allow_install:
        raise HTTPException(status_code=403, detail="Install off hai (SUPERAGENT_ALLOW_INSTALL=0).")
    package = body.package.strip()
    if not all(c.isalnum() or c in "-.+" for c in package):
        raise HTTPException(status_code=400, detail="Invalid package name.")
    cmd = runner.build_shell_command(
        f"apt-get update && apt-get install -y --no-install-recommends {package}",
        actor=actor, timeout=900,
    )

    def continuation(approved: bool, approval: approvals.Approval) -> None:
        if approved:
            runner.commands.submit(cmd)

    approval = approvals.create(kind="install", summary=f"Install {package}", command=cmd.display,
                                target="-", section="utility", actor=actor, continuation=continuation)
    return {"status": "approval_required", "approval": approval.view()}


@api.get("/command/preview")
def command_preview(tool: str, target: str = "", _a: str = Authenticated) -> dict[str, Any]:
    """UI ke liye command preview (chalta nahi)."""
    try:
        cmd = runner.build_tool_command(tool, target=target)
    except (runner.BuildError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"display": quote(cmd.argv)}

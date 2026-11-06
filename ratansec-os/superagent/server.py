"""RatanSec Super Agent v2 API — fail-closed auth, missions, evidence."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote as urlquote, urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, ConfigDict

from . import agent, approvals, audit, catalog, missions, provider, records, report, runner, scope
from .settings import APP_NAME, VERSION, settings

api = APIRouter(prefix="/api")
COOKIE = "sa_session"
_RATE: dict[str, list[float]] = {}
_COOKIE_SESSIONS: dict[str, tuple[str, float]] = {}
_AUTH_LOCK = threading.Lock()
COOKIE_TTL = 8 * 3600


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginBody(StrictBody):
    password: str = Field(default="", max_length=256)


class ChatBody(StrictBody):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: str = Field(default="", max_length=64)
    auto_approve: bool | None = None
    model: str | None = Field(default=None, max_length=120)


class MissionBody(StrictBody):
    target: str = Field(default="", max_length=2048)
    objective: str = Field(..., min_length=3, max_length=1000)
    profile: str = Field(default="quick", max_length=20)


class CommandBody(StrictBody):
    tool: str = Field(..., max_length=60)
    target: str = Field(..., max_length=2048)
    flags: dict[str, Any] = Field(default_factory=dict)
    timeout: int = Field(default=30, ge=5, le=120)
    label: str = Field(default="", max_length=160)


class ApprovalBody(StrictBody):
    approved: bool = False
    note: str = Field(default="", max_length=300)


class RecordBody(StrictBody):
    client: str = Field(..., min_length=2, max_length=120)
    contact: str = Field(default="", max_length=160)
    scope: list[str] = Field(..., min_length=1, max_length=40)
    sections: list[str] = Field(default_factory=lambda: ["recon", "web", "reporting"], max_length=16)
    start: str = Field(default="", max_length=32)
    end: str = Field(default="", max_length=32)
    signer: str = Field(..., min_length=2, max_length=120)
    signature: str = Field(..., min_length=3, max_length=300)
    emergency: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=2000)


class ReportBody(StrictBody):
    title: str = Field(default="", max_length=160)
    markdown: str = Field(..., min_length=20, max_length=200000)


class ScopeCheckBody(StrictBody):
    target: str = Field(..., max_length=2048)
    section: str = Field(default="web", max_length=40)


def _client(request: Request) -> str:
    if settings.trusted_proxy:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()[:80]
    return (request.client.host if request.client else "unknown")[:80]


def _rate(key: str, limit: int, window: int) -> None:
    now = time.time()
    with _AUTH_LOCK:
        bucket = _RATE.setdefault(key, [])
        bucket[:] = [t for t in bucket if now - t < window]
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit — thoda ruk kar try karo.")
        bucket.append(now)


def _token_ok(token: str) -> str | None:
    for name, candidate in (("api-token", settings.api_token), ("mobile-token", settings.mobile_token)):
        if candidate and token and hmac.compare_digest(token, candidate):
            return name
    return None


def _cookie_identity(request: Request) -> str | None:
    raw = request.cookies.get(COOKIE, "")
    if not raw:
        return None
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with _AUTH_LOCK:
        item = _COOKIE_SESSIONS.get(digest)
        if item and item[1] > time.time():
            return item[0]
        _COOKIE_SESSIONS.pop(digest, None)
    return None


def require_auth(request: Request) -> str:
    if settings.demo_mode:
        return "demo"
    token = request.headers.get("x-agent-token", "")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = token or auth[7:].strip()
    identity = _token_ok(token)
    if identity:
        return identity
    cookie = _cookie_identity(request)
    if cookie:
        return cookie
    raise HTTPException(status_code=401, detail="Login required (password or X-Agent-Token).")


Authenticated = Depends(require_auth)


def _csrf(request: Request, actor: str) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"} or settings.demo_mode:
        return
    if actor in {"api-token", "mobile-token"}:
        return
    origin = request.headers.get("origin", "")
    if origin:
        try:
            host = urlsplit(origin).netloc.lower()
        except ValueError:
            host = ""
        expected = request.headers.get("host", "").lower()
        forwarded = request.headers.get("x-forwarded-host", "").lower() if settings.trusted_proxy else ""
        if host not in {expected, forwarded}:
            raise HTTPException(status_code=403, detail="Cross-origin request blocked.")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Cross-site request blocked.")


def live_only(actor: str) -> None:
    if settings.demo_mode or actor == "demo":
        raise HTTPException(status_code=403, detail="Offline demo mode: live actions are disabled.")


@api.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict[str, Any]:
    if settings.demo_mode:
        return {"ok": True, "auth_required": False, "demo": True}
    _rate(f"login:{_client(request)}", 8, 300)
    password_ok = bool(settings.app_password) and hmac.compare_digest(body.password, settings.app_password)
    token_identity = _token_ok(body.password)
    if not password_ok and not token_identity:
        audit.log("login_failed", actor=_client(request))
        raise HTTPException(status_code=401, detail="Password/token galat hai.")
    raw = secrets.token_urlsafe(32)
    identity = "owner" if password_ok else token_identity
    with _AUTH_LOCK:
        now = time.time()
        for key, (_, expiry) in list(_COOKIE_SESSIONS.items()):
            if expiry <= now:
                _COOKIE_SESSIONS.pop(key, None)
        _COOKIE_SESSIONS[hashlib.sha256(raw.encode()).hexdigest()] = (identity, now + COOKIE_TTL)
    secure = request.url.scheme == "https" or (settings.trusted_proxy and request.headers.get("x-forwarded-proto") == "https")
    response.set_cookie(COOKIE, raw, httponly=True, secure=secure, samesite="strict", max_age=COOKIE_TTL, path="/")
    audit.log("login_ok", actor=identity)
    return {"ok": True, "auth_required": True}


@api.post("/logout")
def logout(request: Request, response: Response, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor)
    raw = request.cookies.get(COOKIE, "")
    if raw:
        with _AUTH_LOCK:
            _COOKIE_SESSIONS.pop(hashlib.sha256(raw.encode()).hexdigest(), None)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@api.get("/status")
def status(request: Request) -> dict[str, Any]:
    try:
        actor = require_auth(request)
        authenticated = True
    except HTTPException:
        actor, authenticated = "", False
    data = {"app": APP_NAME, "version": VERSION, "auth_required": settings.auth_required,
            "authenticated": authenticated, "demo": settings.demo_mode,
            "ai": {"configured": settings.ai_configured, "model": settings.model, "provider": settings.provider,
                   "local": settings.local_provider, "key_required": not settings.local_provider},
            "tools_total": catalog.TOTAL_TOOLS, "intrusive_tools": catalog.INTRUSIVE_COUNT,
            "approvals_pending": approvals.pending_count() if authenticated else 0,
            "records_active": len(records.records.active()) if authenticated else 0,
            "shell_allowed": False, "install_allowed": False,
            "mobile_token": bool(settings.mobile_token or settings.api_token),
            "safety": {"default_deny": True, "exact_plan_approval": True, "raw_shell": False,
                       "redirects_followed": False, "credentials_in_chat": False}}
    if authenticated:
        data["agent"] = provider.status()
        data["scope"] = scope.scope_payload()
        data["missions"] = len(missions.missions.list(actor=actor))
    return data


@api.get("/provider")
def provider_status(actor: str = Authenticated) -> dict[str, Any]:
    return provider.status()


@api.post("/provider/test")
def provider_test(request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor); _rate(f"provider:{actor}", 6, 60)
    try:
        result = provider.test_connection()
        audit.log("provider_test", actor=actor, ok=True, model=result["model"])
        return result
    except provider.ProviderError as exc:
        audit.log("provider_test", actor=actor, ok=False)
        raise HTTPException(status_code=502, detail=str(exc)) from None


@api.get("/sections")
def sections(actor: str = Authenticated) -> dict[str, Any]:
    payload = catalog.sections_payload()
    for section in payload:
        for tool in section["tools"]:
            tool["installed"] = runner.which(tool["binary"]) is not None
            tool["executable"] = tool["name"] in runner.SAFE_ADAPTERS
            tool["reference_only"] = not tool["executable"]
    return {"sections": payload, "total": catalog.TOTAL_TOOLS, "intrusive": catalog.INTRUSIVE_COUNT,
            "executable_adapters": sorted(runner.SAFE_ADAPTERS)}


@api.get("/tools")
def tools(actor: str = Authenticated) -> dict[str, Any]:
    items = [{"name": t.name, "section": t.section, "binary": t.binary, "package": t.package,
              "summary": t.summary, "flags": t.flags, "intrusive": t.intrusive, "offline": t.offline,
              "installed": runner.which(t.binary) is not None, "install_hint": t.install_hint,
              "example": t.example, "executable": t.name in runner.SAFE_ADAPTERS} for t in catalog.TOOLS.values()]
    return {"tools": items, "installed": sum(i["installed"] for i in items), "total": len(items)}


@api.get("/scope")
def scope_info(actor: str = Authenticated) -> dict[str, Any]:
    live_only(actor)
    return scope.scope_payload()


@api.post("/scope/check")
def scope_check(body: ScopeCheckBody, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor)
    return scope.check(body.target, body.section).view()


def _parse_day(value: str, fallback: float) -> float:
    if not value.strip():
        return fallback
    try:
        import calendar, datetime
        return calendar.timegm(datetime.datetime.strptime(value, "%Y-%m-%d").timetuple())
    except ValueError:
        raise HTTPException(status_code=400, detail="Date format YYYY-MM-DD required.") from None


@api.get("/records")
def records_list(actor: str = Authenticated) -> dict[str, Any]:
    live_only(actor)
    return {"records": [r.view() for r in records.records.all()], "summary": records.summary()}


@api.post("/records")
def records_create(body: RecordBody, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor)
    now = time.time()
    start = _parse_day(body.start, now)
    end = _parse_day(body.end, now + 7 * 86400) + 86399
    try:
        item = records.records.create(client=body.client, contact=body.contact, scope=body.scope,
                                      sections=body.sections, start=start, end=end, signer=body.signer,
                                      signature=body.signature, emergency=body.emergency, notes=body.notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    audit.log("roe_created", evidence=True, roe=item.id, client=item.client, scope=item.scope,
              sections=item.sections, actor=actor)
    return {"record": item.view(), "chain": records.verify_chain()}


@api.post("/records/{roe_id}/revoke")
def records_revoke(roe_id: str, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor)
    item = records.records.revoke(roe_id, reason=f"revoked by {actor}")
    if item is None:
        raise HTTPException(status_code=404, detail="Record not found.")
    audit.log("roe_revoked", evidence=True, roe=roe_id, actor=actor)
    return {"record": item.view()}


@api.post("/records/seed-demo")
def records_seed(request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor)
    raise HTTPException(status_code=410, detail="Public demo seeds removed. Use the offline demo mission.")


@api.post("/missions")
def mission_create(body: MissionBody, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor); _rate(f"mission:{actor}", 12, 60)
    try:
        item = missions.missions.create(target=body.target, objective=body.objective, profile=body.profile, actor=actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"mission": item.view()}


@api.post("/demo/mission")
def demo_mission(body: MissionBody, request: Request) -> dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Demo endpoint is disabled in live mode.")
    _rate(f"demo:{_client(request)}", 10, 60)
    item = missions.missions.create(target="https://demo.ratansec.local", objective=body.objective,
                                    profile=body.profile, actor="demo", demo=True)
    return {"mission": item.view(), "demo": True}


@api.get("/missions")
def mission_list(limit: int = Query(default=30, ge=1, le=100), actor: str = Authenticated) -> dict[str, Any]:
    return {"missions": [m.view() for m in missions.missions.list(limit, actor=actor)]}


@api.get("/missions/{mission_id}")
def mission_get(mission_id: str, actor: str = Authenticated) -> dict[str, Any]:
    item = missions.missions.get(mission_id)
    if item is None or (item.actor != actor and not item.demo):
        raise HTTPException(status_code=404, detail="Mission not found.")
    return {"mission": item.view()}


@api.post("/missions/{mission_id}/cancel")
def mission_cancel(mission_id: str, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor)
    try:
        item = missions.missions.cancel(mission_id, actor)
    except KeyError:
        raise HTTPException(status_code=404, detail="Mission not found.") from None
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    return {"mission": item.view()}


@api.post("/agent/chat")
def agent_chat(body: ChatBody, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); _rate(f"chat:{actor}", 30, 60)
    if not settings.demo_mode and not settings.ai_configured:
        raise HTTPException(status_code=503, detail="AI provider configured nahi hai. Server-side key/local model set karo.")
    try:
        result = agent.run_turn(body.session_id, body.message, actor=actor, model=body.model)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except agent.AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    audit.log("agent_reply", session=result["session_id"], chars=len(result.get("reply", "")), actor=actor)
    return {"ok": True, **result}


@api.get("/agent/followup/{session_id}")
def agent_followup(session_id: str, actor: str = Authenticated) -> dict[str, Any]:
    return {"status": "ready", "reply": "v2 missions run asynchronously. Poll /api/missions/{id} for status.", "steps": []}


@api.delete("/agent/followup/{session_id}")
def agent_followup_clear(session_id: str, actor: str = Authenticated) -> dict[str, Any]:
    return {"ok": True}


@api.post("/agent/reset")
def agent_reset(body: dict[str, str], request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor)
    agent.reset_session(body.get("session_id", ""), actor)
    return {"ok": True}


@api.get("/agent/sessions")
def agent_sessions(actor: str = Authenticated) -> dict[str, Any]:
    return {"pending_approvals": [a for a in approvals.pending() if a["actor"] == actor or settings.demo_mode]}


@api.post("/command")
def command(body: CommandBody, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor); _rate(f"cmd:{actor}", 20, 60)
    try:
        cmd = runner.build_tool_command(body.tool, target=body.target, flags=body.flags,
                                        label=body.label, actor=actor, timeout=body.timeout)
    except (runner.BuildError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    def validator() -> None:
        decision = scope.check(cmd.target, cmd.section)
        if not decision.allowed or decision.roe_id != cmd.roe_id:
            raise ValueError("Authorization changed.")
    def continuation(approved: bool, ap: approvals.Approval) -> None:
        if approved:
            try:
                runner.commands.submit(cmd, approval_id=ap.id)
            except runner.BuildError as exc:
                audit.log("adapter_refused", cmd_id=cmd.id, reason=str(exc))
    ap = approvals.create(kind="adapter", summary=cmd.label, command=cmd.display, target=cmd.target,
                          section=cmd.section, actor=actor, payload={"roe_id": cmd.roe_id},
                          validator=validator, continuation=continuation)
    return {"status": "approval_required", "approval": ap.view(), "command": cmd.display}


@api.post("/command/shell")
def command_shell(request: Request, actor: str = Authenticated) -> dict[str, Any]:
    raise HTTPException(status_code=410, detail="Raw shell retired in v2. Use bounded missions or safe adapters.")


@api.get("/command/preview")
def command_preview(tool: str, target: str = "", actor: str = Authenticated) -> dict[str, Any]:
    live_only(actor)
    try:
        cmd = runner.build_tool_command(tool, target=target, actor=actor)
    except (runner.BuildError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"display": cmd.display, "approval_required": True}


@api.get("/runs")
def runs_list(limit: int = Query(default=30, ge=1, le=100), actor: str = Authenticated) -> dict[str, Any]:
    return {"runs": [r.view(tail=6000) for r in runner.commands.list(limit, actor=actor)]}


@api.get("/runs/{run_id}")
def runs_get(run_id: str, tail: int = Query(default=24000, ge=500, le=100000), actor: str = Authenticated) -> dict[str, Any]:
    result = runner.commands.get(run_id)
    if result is None or result.actor != actor:
        raise HTTPException(status_code=404, detail="Run not found.")
    return {"run": result.view(tail=tail)}


@api.post("/runs/{run_id}/cancel")
def runs_cancel(run_id: str, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor)
    if not runner.commands.cancel(run_id, actor):
        raise HTTPException(status_code=404, detail="Run not found.")
    return {"ok": True}


@api.get("/approvals")
def approvals_list(actor: str = Authenticated) -> dict[str, Any]:
    items = [a for a in approvals.list_all() if a["actor"] == actor]
    return {"approvals": items, "pending": sum(a["status"] == "pending" for a in items)}


@api.post("/approvals/{approval_id}")
def approvals_decide(approval_id: str, body: ApprovalBody, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor)
    item = approvals.get(approval_id)
    if item is None or item.actor != actor:
        raise HTTPException(status_code=404, detail="Approval not found.")
    try:
        item = approvals.decide(approval_id, body.approved, actor, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return {"approval": item.view(), "message": "Approved — mission queued." if item.status == "approved" else "Denied."}


@api.get("/reports")
def reports_list(actor: str = Authenticated) -> dict[str, Any]:
    items = report.list_reports()
    if settings.demo_mode:
        allowed = {m.report_file for m in missions.missions.list(limit=100, actor="demo") if m.demo and m.report_file}
        items = [i for i in items if i["name"] in allowed]
    return {"reports": items}


@api.post("/reports")
def reports_create(body: ReportBody, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor)
    path = report.save(body.title or "Super Agent Report", provider.redact(body.markdown), client=actor)
    audit.log("report_saved", evidence=True, file=path.name, actor=actor)
    return {"file": path.name}


@api.get("/reports/{name}")
def reports_read(name: str, actor: str = Authenticated) -> dict[str, Any]:
    if settings.demo_mode:
        allowed = {m.report_file for m in missions.missions.list(limit=100, actor="demo") if m.demo and m.report_file}
        if name not in allowed:
            raise HTTPException(status_code=404, detail="Report not found.")
    try:
        content = report.read(name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Report not found.") from None
    return {"name": name, "content": content, "html": report.md_to_html(content)}


@api.delete("/reports/{name}")
def reports_delete(name: str, request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor)
    try:
        deleted = report.delete(name)
    except ValueError:
        deleted = False
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")
    audit.log("report_deleted", file=name, actor=actor)
    return {"ok": True}


@api.get("/audit")
def audit_list(limit: int = Query(default=120, ge=1, le=1000), actor: str = Authenticated) -> dict[str, Any]:
    live_only(actor)
    return {"events": audit.recent(limit), "verify": audit.verify()}


@api.get("/audit/verify")
def audit_verify(actor: str = Authenticated) -> dict[str, Any]:
    live_only(actor)
    return {"audit": audit.verify(), "evidence": audit.verify(audit.EVIDENCE_FILE), "records": records.verify_chain()}


@api.post("/evidence/bundle")
def evidence_bundle(request: Request, actor: str = Authenticated) -> dict[str, Any]:
    _csrf(request, actor); live_only(actor)
    try:
        path = audit.export_bundle()
    except audit.AuditError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return {"file": path.name, "download": f"/api/evidence/{urlquote(path.name)}"}


@api.get("/evidence/{name}")
def evidence_download(name: str, actor: str = Authenticated):
    from fastapi.responses import FileResponse
    live_only(actor)
    if not name.startswith("evidence-bundle-") or not name.endswith(".zip") or "/" in name or "\\" in name:
        raise HTTPException(status_code=404, detail="File not found.")
    path = settings.evidence_dir / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path, filename=name, media_type="application/zip")


@api.post("/install")
def install(request: Request, actor: str = Authenticated) -> dict[str, Any]:
    raise HTTPException(status_code=410, detail="Remote package installation is retired in v2.")

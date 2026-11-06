"""Super Agent — AI brain (private API: OpenAI-compatible / OpenRouter / koi bhi).

Loop:
    user message -> LLM (tool calling) -> tool execute (scope + RoE + approval)
    -> tool result -> LLM -> ... -> final answer

Safety har layer par:
  * scope.check()      -> target authorized hai?
  * approvals.create() -> intrusive/shell ke liye human tap
  * runner             -> argv-only (ya blocklisted shell)
  * audit.log()        -> sab kuch evidence chain me

Approval pending hone par turn rukta hai; approve hoke continuation chalti hai
aur result `/api/agent/followup/{session_id}` se milta hai (mobile console poll
karta hai).
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any

from . import approvals, audit, catalog, records, report, runner, scope
from .settings import effective_approval, settings

MAX_TOOL_RESULT = 14000
_MODEL_RE = re.compile(r"^[A-Za-z0-9._:\-/]{1,120}$")


class AgentError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Tum "RatanSec Super Agent" ho — ek authorized security assessment agent jo Kali/Linux tools ko
AI ke through chalata hai. User professional pentester hai aur uske paas likhit authorization hai.

# TUMHARA KAAM
User ki request ko tool calls me todo aur chalao: recon -> enumeration -> vulnerability analysis ->
web/api tests -> (approval ke baad) gaining access / exploitation -> reporting.
Har result ko honest analysis ke saath summarize karo.

# HARD RULES (kabhi na todo)
1. Sirf AUTHORIZED targets. Koi target unknown ho to pehle `check_scope` call karo.
   Agar check_scope "allowed": false deta hai to us target par kuch mat chalao — user ko batao
   ki Records tab me authorization record banao ya scope theek karo.
2. Cloud metadata IPs (169.254.169.254, 100.100.100.200, metadata.google.internal) kabhi target mat karo.
3. Destructive / DoS / mass brute-force / data exfiltration nahi. Kali tools verification ke liye hain.
4. Tool output me jo hai wahi bolo — findings invent mat karo. Output khali/error ho to saaf batao.
5. Har command ka exact command line user ko dikhao (copy-paste ke liye).
6. Intrusive tools (hydra, metasploit, sqlmap, responder, hashcat, mimikatz...) par approval
   automatically lag jaata hai — user ko bolo "mobile/dashboard me approval card aaya hai, Approve dabao".
   Approval ke bina chalne ki koshish mat karo, aur baar baar same request repeat mat karo.
7. Shell mode sirf tab use karo jab catalog me tool na ho, aur tab bhi read-only/safe commands.

# TOOLS KAISE USE KARO
- `list_sections()` -> kaun kaun se section me kaun se tools hain (ek baar dekho).
- `check_scope(target, section)` -> target + section authorize hai ya nahi.
- `run_tool(tool, target, flags, label, timeout)` -> catalog se tool chalao.
      flags ek object: {"severity":"high", "ports":"80,443"} — sirf allowed flags.
- `list_runs()` / `get_run(run_id, tail)` -> chalti hui ya purani commands ka output.
- `wait_and_read(run_id, seconds)` -> lambi command (nmap/nuclei) ke liye ruk kar output padho.
- `run_shell(command)` -> raw Linux command (guard ke saath, approval lagta hai).
- `list_authorizations()` -> active engagement records (client, scope, valid till).
- `save_report(title, markdown)` -> report file banao (Reports tab me dikhegi).
- `install_tool(tool)` -> missing tool install request (approval + ALLOW_INSTALL zaroori).

# JAWAB KA STYLE
- User ki language me (Hinglish -> Hinglish).
- Structure: 1-line summary -> key findings (bullets/table) -> risk -> next steps (commands ke saath).
- Lambe output paste mat karo; sirf important lines (open ports, versions, CVEs, paths) quote karo.
- Aakhir me 2-3 concrete next-step suggestions do.
"""


# ---------------------------------------------------------------------------
# Provider client
# ---------------------------------------------------------------------------
def _headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ratan-patel.github.io/",
        "X-Title": "RatanSec Super Agent",
        "User-Agent": "RatanSecSuperAgent/1.0",
    }
    headers.update(settings.header_map())
    return headers


def ai_status() -> dict[str, Any]:
    return {
        "configured": settings.ai_configured,
        "model": settings.model,
        "base_url": settings.base_url,
        "max_steps": settings.max_steps,
        "model_override": settings.model_override,
        "key_hint": (settings.api_key[:6] + "…" + settings.api_key[-4:]) if len(settings.api_key) > 12 else "",
    }


def _pick_model(requested: str | None) -> str:
    if not requested:
        return settings.model
    name = requested.strip()
    if not settings.model_override or not _MODEL_RE.match(name):
        return settings.model
    return name[:120]


def _content_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        return "".join(str(p.get("text", "")) if isinstance(p, dict) else str(p) for p in content).strip()
    return ("" if content is None else str(content)).strip()


def chat(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict] | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 2400,
) -> dict[str, Any]:
    if not settings.ai_configured:
        raise AgentError(
            "API key set nahi hai. `SUPERAGENT_API_KEY` (ya OPENROUTER_API_KEY) environment me daalo "
            "— koi bhi OpenAI-compatible private endpoint chalega (base URL bhi badal sakte ho)."
        )
    payload: dict[str, Any] = {
        "model": _pick_model(model),
        "messages": messages,
        "temperature": settings.temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    url = settings.base_url.rstrip("/") + "/chat/completions"
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=_headers(), method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.ai_timeout) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        friendly = {
            401: "API key galat/expired (401).",
            402: "Provider credits khatam (402).",
            403: "Access denied (403) — model ya account allowed nahi.",
            404: "Model/endpoint nahi mila (404) — SUPERAGENT_MODEL / SUPERAGENT_BASE_URL check karo.",
            429: "Rate limit (429) — thoda ruk kar try karo.",
        }.get(exc.code, f"Provider error ({exc.code}).")
        raise AgentError(f"{friendly} {detail}") from exc
    except urllib.error.URLError as exc:
        raise AgentError(f"AI endpoint se connect nahi hua: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise AgentError("Provider ne invalid JSON bheja.") from exc

    choices = body.get("choices") or []
    if not choices:
        raise AgentError(f"Provider ne completion nahi di: {(body.get('error') or {}).get('message', 'unknown')}")
    message = choices[0].get("message") or {}
    return {
        "role": "assistant",
        "content": _content_text(message),
        "tool_calls": message.get("tool_calls") or [],
        "_model": body.get("model") or payload["model"],
        "_usage": body.get("usage") or {},
    }


# ---------------------------------------------------------------------------
# Tool schemas (LLM ko dikhne wale)
# ---------------------------------------------------------------------------
def _section_enum() -> list[str]:
    return list(catalog.SECTIONS.keys())


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_sections",
            "description": "Tool arsenal: sections aur unke tools (naam, flags, intrusive ya nahi).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_scope",
            "description": "Target + section authorize hai ya nahi (RoE record / allowlist check).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "domain / IP / URL / CIDR"},
                    "section": {"type": "string", "enum": _section_enum()},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tool",
            "description": "Catalog tool chalao (argv-safe). Output turant ya run_id ke through milta hai.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Catalog tool name (jaise nuclei, nmap-vuln, ffuf)"},
                    "target": {"type": "string", "description": "Authorized target"},
                    "flags": {"type": "object", "description": "Allowed flags object, jaise {\"severity\":\"high\"}"},
                    "label": {"type": "string"},
                    "timeout": {"type": "integer", "description": "seconds (max 900)"},
                },
                "required": ["tool"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Raw Linux command (guard ke saath, approval mandatory). Catalog me na ho tab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "reason": {"type": "string", "description": "Kyun zaroori hai — approval card me dikhega"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_runs",
            "description": "Recent commands/runs (status ke saath).",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_run",
            "description": "Ek run ka output padho (tail chars).",
            "parameters": {
                "type": "object",
                "properties": {"run_id": {"type": "string"}, "tail": {"type": "integer"}},
                "required": ["run_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait_and_read",
            "description": "Lambi command ke liye ruk kar output padho (max 60s).",
            "parameters": {
                "type": "object",
                "properties": {"run_id": {"type": "string"}, "seconds": {"type": "integer"}},
                "required": ["run_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_authorizations",
            "description": "Active engagement records — client, scope, sections, valid till.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_report",
            "description": "Markdown report save karo (Reports tab me dikhegi).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "markdown": {"type": "string", "description": "Poora report content"},
                },
                "required": ["title", "markdown"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_tool",
            "description": "Missing tool install karne ki request (approval + ALLOW_INSTALL).",
            "parameters": {
                "type": "object",
                "properties": {"tool": {"type": "string"}},
                "required": ["tool"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@dataclass
class Session:
    id: str
    actor: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    runs: list[str] = field(default_factory=list)
    auto_approve: bool = False
    model: str = ""
    pending_call_id: str = ""
    pending_approval: dict[str, Any] | None = None
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)

    def public_messages(self) -> list[dict[str, str]]:
        out = []
        for item in self.messages:
            if item.get("role") in ("user", "assistant") and item.get("content"):
                out.append({"role": item["role"], "content": item["content"]})
        return out


_sessions: dict[str, Session] = {}
_followups: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def get_session(session_id: str, actor: str = "owner") -> Session:
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            session = Session(id=session_id or f"s-{uuid.uuid4().hex[:10]}", actor=actor)
            _sessions[session.id] = session
        return session


def reset_session(session_id: str) -> None:
    with _lock:
        session = _sessions.get(session_id)
        if session:
            session.messages = []
            session.runs = []
            session.pending_call_id = ""
            session.pending_approval = None
        _followups.pop(session_id, None)


def set_followup(session_id: str, payload: dict[str, Any]) -> None:
    with _lock:
        _followups[session_id] = {**payload, "ts": time.time()}


def get_followup(session_id: str) -> dict[str, Any] | None:
    with _lock:
        item = _followups.get(session_id)
    if item and time.time() - item.get("ts", 0) > 1800:
        clear_followup(session_id)
        return None
    return item


def clear_followup(session_id: str) -> None:
    with _lock:
        _followups.pop(session_id, None)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def _out(payload: dict[str, Any], step: dict[str, Any] | None = None, pending: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"payload": payload, "step": step, "pending": pending}


def _tool_list_sections(args: dict[str, Any], session: Session) -> dict[str, Any]:
    data = []
    for section in catalog.sections_payload():
        tools = section["tools"]
        data.append({
            "id": section["id"], "title": section["title"], "purpose": section["purpose"],
            "tools": [{"name": t["name"], "summary": t["summary"], "intrusive": t["intrusive"],
                       "flags": list(t["flags"]), "installed": runner.which(t["binary"]) is not None} for t in tools],
        })
    return _out({"sections": data, "total_tools": catalog.TOTAL_TOOLS,
                 "note": "intrusive=true tools par approval lagega. flags object me sirf yehi keys allowed hain."})


def _tool_check_scope(args: dict[str, Any], session: Session) -> dict[str, Any]:
    target = str(args.get("target", "")).strip()
    section = str(args.get("section", "recon")).strip().lower()
    if section not in catalog.SECTIONS:
        return _out({"error": f"invalid section '{section}'", "sections": list(catalog.SECTIONS)})
    decision = scope.check(target, section)
    return _out({**decision.view(), "hint": "allowed=false ho to us target par koi tool mat chalao."})


def _compact(result: runner.CommandResult, tail: int | None = None) -> dict[str, Any]:
    view = result.view(tail=tail)
    view.pop("started", None)
    return view


def _execute_command(session: Session, command: runner.Command, *, kind: str, summary: str, dangerous: bool) -> dict[str, Any]:
    """Approval chahiye to pending banao, warna chala do."""
    needs = effective_approval(session.auto_approve, dangerous)
    if needs:
        def continuation(approved: bool, approval: approvals.Approval) -> None:
            if not approved:
                _finish_pending(session, {"status": "denied", "message": "User ne deny kiya.", "command": command.display})
                return
            result = runner.commands.submit(command)
            session.runs.append(result.id)
            audit.log("approved_cmd_start", evidence=True, cmd_id=result.id, approval=approval.id, display=command.display)
            _finish_pending(session, {"job": _job_payload(session, result)}, result=result)

        approval = approvals.create(
            kind=kind, summary=summary, command=command.display,
            target=command.target or "-", section=command.section or "-",
            actor=session.actor, dangerous=dangerous,
            payload={"tool": command.tool, "timeout": command.timeout},
            continuation=continuation,
        )
        return _out(
            {"status": "approval_required", "approval_id": approval.id, "summary": summary,
             "command": command.display,
             "message": "User ko bolo dashboard/mobile me approval card approve kare."},
            step={"type": "approval", "approval_id": approval.id, "summary": summary, "command": command.display},
            pending={"id": approval.id, "summary": summary, "command": command.display,
                     "target": command.target or "-", "dangerous": dangerous},
        )

    result = runner.commands.submit(command)
    session.runs.append(result.id)
    return _out({"job": _job_payload(session, result)},
                step={"type": "run", "run_id": result.id, "tool": command.tool, "command": command.display})


def _job_payload(session: Session, result: runner.CommandResult, wait: float = 0.0) -> dict[str, Any]:
    """Job start karke thoda wait — chhota command turant output de deta hai."""
    deadline = time.time() + wait
    while wait and time.time() < deadline and result.status in ("queued", "running"):
        time.sleep(0.4)
    data = _compact(result, tail=MAX_TOOL_RESULT)
    if result.status in ("queued", "running"):
        data["message"] = (
            f"Command background me chal rahi hai (run_id={result.id}). "
            f"`wait_and_read(run_id='{result.id}', seconds=20)` se output lo, ya user ko dashboard me live dikhega."
        )
    return data


def _tool_run_tool(args: dict[str, Any], session: Session) -> dict[str, Any]:
    tool_name = str(args.get("tool", "")).strip()
    target = str(args.get("target", "")).strip()
    flags = args.get("flags") or {}
    if not isinstance(flags, dict):
        return _out({"error": "flags ek object hona chahiye, jaise {\"severity\":\"high\"}"})
    spec = catalog.TOOLS.get(tool_name.lower())
    if spec is None:
        return _out({"error": f"'{tool_name}' catalog me nahi hai.", "available": sorted(catalog.TOOLS)})

    if target and not (spec.offline or spec.name in ("searchsploit", "searchsploit-poc", "hashid", "jq")):
        decision = scope.check(target, spec.section)
        if not decision.allowed:
            return _out({"status": "denied_by_scope", **decision.view(),
                         "message": "Target authorized nahi hai — Records tab me authorization record banao."})
    elif spec.section not in ("utility", "reporting", "cracking"):
        return _out({"error": f"'{spec.name}' ke liye target chahiye (authorized scope se)."})

    try:
        command = runner.build_tool_command(
            spec.name, target=target, flags=flags,
            label=str(args.get("label", "")), actor=session.actor,
            timeout=int(args.get("timeout") or settings.default_timeout),
        )
    except (runner.BuildError, ValueError) as exc:
        return _out({"error": str(exc), "allowed_flags": spec.flags})

    summary = f"{spec.name} — {command.target or 'local'}"
    outcome = _execute_command(session, command, kind="tool", summary=summary, dangerous=spec.intrusive)
    if outcome["pending"] is None:
        outcome["payload"]["job"].update({"tool": spec.name, "target": command.target, "section": spec.section})
        outcome["payload"]["job"]["command"] = command.display
        outcome["step"] = {**outcome["step"], "section": spec.section}
    return outcome


def _tool_run_shell(args: dict[str, Any], session: Session) -> dict[str, Any]:
    command_text = str(args.get("command", "")).strip()
    reason = str(args.get("reason", "")).strip()
    if not settings.allow_shell:
        return _out({
            "error": "Shell mode disabled hai (SUPERAGENT_ALLOW_SHELL=0). Catalog tool use karo, "
                     "ya server par shell enable karke session switch ON karo.",
        })
    if not session.auto_approve and settings.approval_mode != "auto":
        # approval to lagega hi — lekin guard pehle
        pass
    try:
        command = runner.build_shell_command(command_text, actor=session.actor)
    except runner.BuildError as exc:
        return _out({"error": str(exc)})
    summary = f"shell: {command_text[:120]}"
    if reason:
        summary += f" — {reason}"
    return _execute_command(session, command, kind="shell", summary=summary, dangerous=True)


def _tool_list_runs(args: dict[str, Any], session: Session) -> dict[str, Any]:
    limit = int(args.get("limit") or 10)
    items = []
    for result in runner.commands.list(limit=max(1, min(limit, 30))):
        view = _compact(result, tail=1500)
        items.append({
            "run_id": result.id, "command": result.display, "status": result.status,
            "exit_code": result.exit_code, "duration": result.duration,
            "output_tail": view["output"][-1500:], "error": result.error,
        })
    return _out({"runs": items})


def _tool_get_run(args: dict[str, Any], session: Session) -> dict[str, Any]:
    run_id = str(args.get("run_id", "")).strip()
    result = runner.commands.get(run_id)
    if result is None:
        return _out({"error": f"run '{run_id}' nahi mila.", "recent": [r.id for r in runner.commands.list(10)]})
    tail = max(1000, min(int(args.get("tail") or 8000), 20000))
    return _out(_compact(result, tail=tail))


def _tool_wait_and_read(args: dict[str, Any], session: Session) -> dict[str, Any]:
    run_id = str(args.get("run_id", "")).strip()
    seconds = max(1, min(int(args.get("seconds") or 20), 60))
    result = runner.commands.get(run_id)
    if result is None:
        return _out({"error": f"run '{run_id}' nahi mila."})
    deadline = time.time() + seconds
    while time.time() < deadline and result.status in ("queued", "running"):
        time.sleep(0.5)
    return _out(_compact(result, tail=MAX_TOOL_RESULT))


def _tool_list_authorizations(args: dict[str, Any], session: Session) -> dict[str, Any]:
    items = [a.view() for a in records.records.all()]
    return _out({"records": items, "count": len(items), "chain": records.verify_chain()})


def _tool_save_report(args: dict[str, Any], session: Session) -> dict[str, Any]:
    title = str(args.get("title", "")).strip() or "Super Agent Report"
    markdown = str(args.get("markdown", "")).strip()
    if len(markdown) < 20:
        return _out({"error": "Report content bahut chhota hai."})
    path = report.save(title, markdown, session=session.id)
    audit.log("report_saved", evidence=True, file=path.name, actor=session.actor, session=session.id)
    return _out({"status": "saved", "file": path.name, "path": str(path),
                 "message": "Report save ho gayi — Reports tab me dikhegi."},
                step={"type": "report", "file": path.name})


def _tool_install_tool(args: dict[str, Any], session: Session) -> dict[str, Any]:
    name = str(args.get("tool", "")).strip().lower()
    spec = catalog.TOOLS.get(name)
    if spec is None:
        return _out({"error": f"'{name}' catalog me nahi hai."})
    if runner.which(spec.binary):
        return _out({"status": "already_installed", "tool": name, "binary": spec.binary})
    if not settings.allow_install:
        return _out({
            "status": "disabled",
            "message": "Install endpoint off hai. Server par SUPERAGENT_ALLOW_INSTALL=1 set karo "
                       f"(ya khud chalao: apt-get install -y {spec.package}).",
            "manual": f"apt-get install -y {spec.package}",
        })
    command = runner.build_shell_command(f"apt-get update && apt-get install -y --no-install-recommends {spec.package}",
                                         actor=session.actor, timeout=900)
    return _execute_command(session, command, kind="install", summary=f"Install {name} ({spec.package})", dangerous=True)


_DISPATCH = {
    "list_sections": _tool_list_sections,
    "check_scope": _tool_check_scope,
    "run_tool": _tool_run_tool,
    "run_shell": _tool_run_shell,
    "list_runs": _tool_list_runs,
    "get_run": _tool_get_run,
    "wait_and_read": _tool_wait_and_read,
    "list_authorizations": _tool_list_authorizations,
    "save_report": _tool_save_report,
    "install_tool": _tool_install_tool,
}


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------
def _parse_call(call: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    fn = call.get("function") or {}
    name = str(fn.get("name", ""))
    raw = fn.get("arguments") or "{}"
    try:
        args = json.loads(raw) if isinstance(raw, str) else (raw or {})
        if not isinstance(args, dict):
            args = {"value": args}
    except json.JSONDecodeError:
        args = {}
    return name, args, str(call.get("id") or f"call_{uuid.uuid4().hex[:6]}")


def _resume_after_approval(session: Session, tool_payload: dict[str, Any]) -> None:
    """Approval decide hone ke baad loop aage badhao, result followup me daalo."""
    if session.pending_call_id:
        session.messages.append({
            "role": "tool",
            "tool_call_id": session.pending_call_id,
            "content": json.dumps(tool_payload, default=str)[:MAX_TOOL_RESULT],
        })
    session.pending_call_id = ""
    session.pending_approval = None
    try:
        result = run_loop(session)
    except AgentError as exc:
        set_followup(session.id, {"status": "error", "reply": f"AI error: {exc}", "steps": []})
        return
    set_followup(session.id, {"status": "ready", **result})


def _finish_pending(session: Session, payload: dict[str, Any], *, result: runner.CommandResult | None = None) -> None:
    if result is not None:
        payload["job"] = _job_payload(session, result, wait=1.5)
    _resume_after_approval(session, payload)


def run_loop(session: Session) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    model_used = settings.model
    for _ in range(max(1, settings.max_steps)):
        assistant = chat(session.messages, tools=TOOL_SCHEMAS, model=session.model or None)
        model_used = assistant.get("_model") or model_used
        session.messages.append({
            "role": "assistant",
            "content": assistant.get("content") or "",
            **({"tool_calls": assistant["tool_calls"]} if assistant.get("tool_calls") else {}),
        })
        content = assistant.get("content") or ""
        calls = assistant.get("tool_calls") or []
        if not calls:
            session.updated = time.time()
            return {"reply": content or "(Model ne text nahi diya.)", "steps": steps,
                    "runs": list(dict.fromkeys(session.runs)), "model": model_used}

        pending: tuple[dict[str, Any], str] | None = None
        for call in calls:
            name, args, call_id = _parse_call(call)
            handler = _DISPATCH.get(name)
            if handler is None:
                outcome = _out({"error": f"unknown tool '{name}'"})
            else:
                try:
                    outcome = handler(args, session)
                except Exception as exc:  # pragma: no cover - defensive
                    outcome = _out({"error": f"tool '{name}' failed: {exc}"})

            if outcome["pending"] is not None:
                if pending is None:
                    pending = (outcome, call_id)
                    steps.append(outcome["step"] or {"type": "approval", **outcome["pending"]})
                else:
                    approvals.cancel(outcome["pending"]["id"], "auto-denied (ek turn me ek approval)")
                    session.messages.append({
                        "role": "tool", "tool_call_id": call_id,
                        "content": json.dumps({"status": "not_executed",
                                               "reason": "ek turn me sirf ek approval handle hoti hai"}),
                    })
                continue

            steps.append(outcome["step"] or {"type": "tool", "tool": name, "args": args})
            session.messages.append({
                "role": "tool", "tool_call_id": call_id,
                "content": json.dumps(outcome["payload"], default=str)[:MAX_TOOL_RESULT],
            })

        if pending is not None:
            outcome, call_id = pending
            session.pending_call_id = call_id
            session.pending_approval = outcome["pending"]
            session.updated = time.time()
            audit.log("agent_approval_wait", evidence=True, approval=outcome["pending"]["id"],
                      actor=session.actor, summary=outcome["pending"]["summary"])
            return {
                "reply": content or (
                    f"Approval chahiye: {outcome['pending']['summary']}. "
                    "Dashboard/Mobile me approval card aaya hai — Approve dabao, phir main aage badhunga."
                ),
                "steps": steps, "runs": list(dict.fromkeys(session.runs)),
                "needs_approval": outcome["pending"], "awaiting_approval": True,
                "model": model_used,
            }

        # tools ke baad history lambi na ho
        _trim(session)

    final = chat(session.messages + [{"role": "user", "content": "Ab aur tool call mat karo — short final answer do."}],
                 temperature=0.3, model=session.model or None)
    reply = final.get("content") or "Step limit reach ho gaya — upar ke results dekho."
    return {"reply": reply, "steps": steps, "runs": list(dict.fromkeys(session.runs)), "model": model_used}


def _trim(session: Session) -> None:
    """System prompt + last N messages rakho; tool pairs tod mat do."""
    if len(session.messages) <= settings.max_history + 2:
        return
    head = session.messages[0]
    tail = session.messages[-settings.max_history:]
    while tail and tail[0].get("role") == "tool":
        tail = tail[1:]
    session.messages = [head] + tail


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------
def run_turn(session_id: str, text: str, *, actor: str = "owner", auto_approve: bool | None = None,
             model: str | None = None) -> dict[str, Any]:
    session = get_session(session_id, actor)
    if auto_approve is not None:
        session.auto_approve = bool(auto_approve)
    if model:
        session.model = model if settings.model_override and _MODEL_RE.match(model.strip()) else ""
    if not session.messages:
        session.messages.append({"role": "system", "content": SYSTEM_PROMPT})
    session.messages.append({"role": "user", "content": text[:8000]})
    clear_followup(session.id)
    audit.log("agent_turn", actor=actor, session=session.id, chars=len(text))
    try:
        result = run_loop(session)
    except AgentError as exc:
        session.messages.pop()
        raise
    result["session_id"] = session.id
    result["conversation"] = session.public_messages()[-6:]
    return result


def status() -> dict[str, Any]:
    with _lock:
        sessions = len(_sessions)
    return {
        **ai_status(),
        "sessions": sessions,
        "pending_approvals": approvals.pending_count(),
        "tools": catalog.TOTAL_TOOLS,
        "intrusive_tools": catalog.INTRUSIVE_COUNT,
        "roes": len(records.records.all()),
        "active_roes": len(records.records.active()),
        "shell_allowed": settings.allow_shell,
        "install_allowed": settings.allow_install,
        "auth_required": settings.auth_required,
        "scope": scope.scope_payload(),
    }

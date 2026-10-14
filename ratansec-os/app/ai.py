"""AI agent — OpenRouter (OpenAI-compatible) + function/tool calling.

Agent loop:
    user message -> LLM -> tool_calls -> tools execute (scope + approval gates)
    -> tool results -> LLM -> final answer

Approval pending hone par agent ruk jaata hai aur UI me approval card dikhta hai.
Approve hote hi `continuation` chalti hai jo scan execute karke wahi conversation
aage badha deti hai (result /api/chat/followup/{conversation_id} se milta hai).
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from . import approvals, audit, report
from .config import settings
from .executor import Run, run_command, runs
from .security import check_target, parse_target
from .tools import (
    PROFILES,
    Step,
    all_tool_status,
    build_profile,
    resolve_tool,
    wordlist_path,
)

MAX_TOOL_RESULT_CHARS = 12000
_MODEL_RE = re.compile(r"^[A-Za-z0-9._:\-/]+$")
_FORBIDDEN_ARG_CHARS = set(";|&$`\"'<>\n\r\x00")


class AIError(RuntimeError):
    """AI provider se related error (friendly message ke saath)."""


# --------------------------------------------------------------------------
# System prompt
# --------------------------------------------------------------------------
SYSTEM_PROMPT = """Tum "RatanSec OS" ke AI copilot ho — ek AI-driven penetration testing environment jo Kali Linux tools par chalta hai.

# Mission
User (authorized security professional / student) ki madad karo: recon -> scanning -> vulnerability analysis -> reporting. Har jawab practical, copy-paste ready aur example ke saath ho.

# Hard rules (kabhi na todo)
1. Sirf AUTHORIZED targets. Agar user clearly apna/authorized target na bataye, ek line me confirm karwa lo.
2. Cloud metadata IPs (169.254.x.x, 100.100.100.200, metadata.google.internal) bilkul kabhi scan mat karo.
3. Destructive / DoS / mass brute-force / data exfiltration kabhi mat suggest karo. Kali ke tools educational + authorized assessment ke liye hain.
4. Tool results mein jo hai wahi bolo — apne se findings invent mat karo. Agar output khali/error hai to honestly bolo.
5. Jo command chala rahe ho, uska poora command user ko dikhao (user command copy karke khud bhi chala sake).

# Tools kaise use karo
- `check_scope(target)` — pehle target validate karo (naya/unknown target par ye call karo).
- `run_scan(target, profile)` — standard scan. Profiles: quick (recon), web (web + nikto + gobuster), network (top-1000 ports), vuln (nmap vuln + nuclei), webapp (sqlmap, parameter URL par), full (sab).
- `run_command(tool, args, target)` — single tool ka one-off command (jaise nmap custom flags, curl headers).
- `get_run_report(run_id)` — kisi run ka full output dobara padho.
- `generate_report(run_id, name)` — Markdown report file banao (reports folder me save hoti hai).
- `list_tools()` — kaunsa tool installed hai + version.

Approval: kuch actions (sqlmap/hydra jaise intrusive, ya jab scope set na ho) ke liye human approval chahiye. Aisa hone par tool "approval_required" return karega — user ko batao ki approval card dikhega, usse approve karne ko kaho.

# Jawab ka style
- User ki language me jawab do (Hinglish -> Hinglish, English -> English).
- Structure: chhota summary -> key findings (bullet/table) -> risk level -> next steps (commands ke saath).
- Long tool output ko paste mat karo; sirf important lines quote karo (headers, open ports, CVEs, interesting paths).
- Technical terms theek rakho, par explanation simple rakho (beginner ko samajh aaye).
- Aakhir me 2-4 next-step suggestions do (authorized assessment ke liye).
"""


# --------------------------------------------------------------------------
# Provider client
# --------------------------------------------------------------------------
def ai_status() -> dict[str, Any]:
    return {
        "configured": settings.ai_configured,
        "model": settings.model,
        "base_url": settings.openrouter_base_url,
        "max_steps": settings.ai_max_steps,
        "model_override_allowed": settings.model_override_allowed,
    }


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_referer,
        "X-Title": "RatanSec OS",
        "User-Agent": "RatanSecOS/1.0",
    }


def _pick_model(requested: str | None) -> str:
    if not requested:
        return settings.model
    candidate = requested.strip()
    if not settings.model_override_allowed or not _MODEL_RE.match(candidate):
        return settings.model
    return candidate[:80]


def chat(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict] | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1800,
) -> dict[str, Any]:
    """Ek chat completion call. Returns assistant message dict."""
    if not settings.ai_configured:
        raise AIError(
            "OPENROUTER_API_KEY set nahi hai. Render/VPS ke environment me key daalo, "
            "phir AI chat chalega. (Tools/scanning bina AI ke bhi kaam karte hain.)"
        )
    payload: dict[str, Any] = {
        "model": _pick_model(model),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    url = settings.openrouter_base_url.rstrip("/") + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=_headers(), method="POST")

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
            401: "API key galat ya expire ho gayi (401).",
            402: "OpenRouter credits khatam (402) — account me balance add karo.",
            403: "Access denied (403) — model ya account allowed nahi hai.",
            404: "Model nahi mila (404) — MODEL env me valid model id daalo.",
            429: "Rate limit (429) — thodi der baad try karo ya chhota model use karo.",
        }.get(exc.code, f"Provider error ({exc.code}).")
        raise AIError(f"{friendly} Detail: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AIError(f"AI provider se connect nahi ho paya: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise AIError("Provider ne invalid JSON bheja.") from exc

    choices = body.get("choices") or []
    if not choices:
        err = body.get("error") or {}
        raise AIError(f"Provider ne koi completion nahi di: {err.get('message') or 'unknown error'}")
    message = choices[0].get("message") or {}
    return {
        "role": "assistant",
        "content": _content_text(message),
        "tool_calls": message.get("tool_calls") or [],
        "_usage": body.get("usage") or {},
        "_model": body.get("model") or payload["model"],
    }


def _content_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):  # kuch providers parts bhejte hain
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    if content is None:
        return ""
    return str(content).strip()


def _clean_for_history(message: dict[str, Any]) -> dict[str, Any]:
    """Sirf role/content/tool_calls rakho (usage waghera strip)."""
    clean: dict[str, Any] = {"role": "assistant", "content": message.get("content") or ""}
    if message.get("tool_calls"):
        clean["tool_calls"] = message["tool_calls"]
    return clean


def _public_history(history: Any, limit: int = 14, cap: int = 4000) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(history, list):
        return out
    for item in history[-limit:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).lower()
        if role not in ("user", "assistant"):
            continue
        content = str(item.get("content", ""))[:cap]
        if content.strip():
            out.append({"role": role, "content": content})
    return out


def summarize_run(run: Run) -> str | None:
    """Scan output ka AI analysis (report ke andar chhapta hai)."""
    if not settings.ai_configured:
        return None
    blob = run.compact_report(max_chars_per_step=4000)[:20000]
    prompt = (
        "Neeche ek authorized security scan ka raw output hai. Isko analyze karke Markdown me likho:\n"
        "1. **Summary** (2-3 lines, target + kya check hua)\n"
        "2. **Key Findings** (bullet list — open ports, versions, headers, interesting paths, CVEs; risk level ke saath)\n"
        "3. **Risk & Impact** (kya asli problem hai)\n"
        "4. **Next Steps** (2-4 actionable commands/suggestions, authorized assessment ke liye)\n\n"
        "Sirf usi cheez ka zikr karo jo output me hai. Jo nahi mila use 'nahi mila' likho.\n\n"
        f"```\n{blob}\n```"
    )
    try:
        message = chat(
            [
                {"role": "system", "content": "Tum ek senior penetration tester ho jo scan output ko client-friendly report me convert karta hai."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return _content_text(message) or None
    except AIError as exc:
        audit.log("ai_summary_error", run=run.id, error=str(exc))
        return f"_AI summary unavailable: {exc}_"


# --------------------------------------------------------------------------
# Tool schemas (LLM ko dikhne wale)
# --------------------------------------------------------------------------
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "check_scope",
            "description": "Target ko validate karta hai (host/URL/CIDR), scope allowlist check karta hai aur batata hai scan allowed hai ya nahi.",
            "parameters": {
                "type": "object",
                "properties": {"target": {"type": "string", "description": "Domain, IP, URL ya CIDR (jaise example.com)"}},
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_scan",
            "description": "Standard scan profile chalata hai aur results wapas deta hai. Profiles: quick, web, network, vuln, webapp, full.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Authorized target (URL ya domain)."},
                    "profile": {"type": "string", "enum": list(PROFILES.keys()), "description": "Scan profile."},
                },
                "required": ["target", "profile"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Ek single tool command chalata hai (argv style). Jaise nmap custom flags, curl headers, whatweb, nikto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name (nmap, curl, dig, nikto, whatweb, gobuster, ffuf, nuclei, sqlmap, whois...)"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Arguments array. Target arg automatically add ho jaata hai agar tum 'target' do."},
                    "target": {"type": "string", "description": "Optional authorized target — tool ke hisaab se host/URL add ho jayega."},
                    "label": {"type": "string", "description": "Short human label (optional)."},
                },
                "required": ["tool"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_run_report",
            "description": "Pehle hue run ka full output dobara padho (run_id ke saath).",
            "parameters": {
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "Run ka Markdown report file generate karke reports folder me save karta hai.",
            "parameters": {
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "name": {"type": "string", "description": "Optional filename."},
                },
                "required": ["run_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tools",
            "description": "Installed tools ki list + version + kaunsa tool missing hai.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# --------------------------------------------------------------------------
# Agent context
# --------------------------------------------------------------------------
@dataclass
class AgentContext:
    actor: str
    conversation_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    runs_seen: list[str] = field(default_factory=list)
    pending_tool_call_id: str | None = None
    pending_pending: dict | None = None
    model: str = ""


@dataclass
class ToolOutcome:
    payload: dict[str, Any]
    step: dict[str, Any] | None = None
    pending: dict[str, Any] | None = None


# --------------------------------------------------------------------------
# Followup store (approval ke baad ka answer)
# --------------------------------------------------------------------------
_followups: dict[str, dict[str, Any]] = {}
_followup_lock = threading.Lock()


def _set_followup(conversation_id: str, data: dict[str, Any]) -> None:
    with _followup_lock:
        _followups[conversation_id] = {**data, "ts": time.time()}


def get_followup(conversation_id: str) -> dict[str, Any] | None:
    with _followup_lock:
        item = _followups.get(conversation_id)
    if item and time.time() - item.get("ts", 0) > 1800:
        clear_followup(conversation_id)
        return None
    return item


def clear_followup(conversation_id: str) -> None:
    with _followup_lock:
        _followups.pop(conversation_id, None)


# --------------------------------------------------------------------------
# Tool implementations
# --------------------------------------------------------------------------
def _run_payload(run: Run, max_chars: int = 6000) -> dict[str, Any]:
    budget = max(600, max_chars // max(1, len(run.steps)))
    steps = []
    for s in run.steps:
        steps.append(
            {
                "index": s.index,
                "tool": s.tool,
                "command": s.command,
                "status": s.status,
                "exit_code": s.exit_code,
                "duration": s.duration,
                "error": s.error,
                "output": (s.output or "")[:budget],
                "output_truncated": len(s.output or "") > budget or s.truncated,
            }
        )
    note = run.note
    skipped = [s.tool for s in run.steps if s.status == "skipped"]
    if skipped:
        note = (note + " " if note else "") + f"Skipped: {', '.join(skipped)} (installed nahi ya invalid)."
    return {
        "run_id": run.id,
        "target": run.target,
        "profile": run.profile,
        "status": run.status,
        "steps": steps,
        "note": note.strip(),
        "hint": "Analyze karo: open ports/services, versions, headers, interesting paths, CVEs. Next steps suggest karo.",
    }


def _tool_check_scope(args: dict[str, Any], ctx: AgentContext) -> ToolOutcome:
    target = str(args.get("target", "")).strip()
    try:
        result = check_target(target, source="agent")
    except ValueError as exc:
        return ToolOutcome({"allowed": False, "target": target, "reason": str(exc)})
    return ToolOutcome(
        {
            "allowed": True,
            "host": result.host,
            "url": result.url,
            "reason": result.reason,
            "in_scope_list": result.in_scope,
            "local": result.local,
            "approval_mode": settings.effective_approval_mode,
        }
    )


def _agent_scan_continuation(ctx: AgentContext, run: Run, steps: list[Step]):
    def continuation(approved: bool) -> None:
        if not approved:
            payload = {
                "status": "denied",
                "message": "User ne approval DENY kar diya. Yeh action dobara mat maango; safe alternative suggest karo.",
                "run_id": run.id,
            }
        else:
            runs.execute_sync(run, steps)
            ctx.runs_seen.append(run.id)
            payload = _run_payload(run, max_chars=8000)
        if ctx.pending_tool_call_id:
            ctx.messages.append(
                {"role": "tool", "tool_call_id": ctx.pending_tool_call_id, "content": json.dumps(payload)[:MAX_TOOL_RESULT_CHARS]}
            )
        try:
            result = _agent_loop(ctx)
        except AIError as exc:
            _set_followup(ctx.conversation_id, {"status": "error", "reply": f"AI error: {exc}", "steps": []})
            return
        _set_followup(
            ctx.conversation_id,
            {
                "status": "ready",
                "reply": result["reply"],
                "steps": result.get("steps", []),
                "runs": result.get("runs", []),
                "model": result.get("model", ""),
            },
        )

    return continuation


def _tool_run_scan(args: dict[str, Any], ctx: AgentContext) -> ToolOutcome:
    target_raw = str(args.get("target", "")).strip()
    profile = str(args.get("profile", "quick")).strip().lower() or "quick"
    try:
        parsed = parse_target(target_raw)
        scope = check_target(target_raw, source="agent")
        steps = build_profile(profile, parsed)
    except ValueError as exc:
        return ToolOutcome({"error": str(exc), "target": target_raw, "profile": profile})

    dangerous = any(step.needs_approval for step in steps)
    needs_human = approvals.approval_required(dangerous, settings.effective_approval_mode)
    title = PROFILES[profile].title
    command_preview = "\n".join(step.display() for step in steps)

    if needs_human:
        run = runs.create(target_raw, steps, "agent", ctx.actor, profile)
        run.note = f"Awaiting approval. {len(steps)} steps planned."
        summary = f"'{scope.host}' par {title} scan ({len(steps)} steps)"
        approval = approvals.create(
            kind="scan",
            summary=summary,
            command=command_preview,
            target=scope.host,
            actor=ctx.actor,
            run_id=run.id,
            continuation=_agent_scan_continuation(ctx, run, steps),
        )
        reason = (
            "Yeh intrusive tool hai (sqlmap/hydra) — human approval mandatory hai."
            if dangerous
            else "Scope allowlist set nahi hai, isliye manual approval mode active hai."
        )
        return ToolOutcome(
            payload={
                "status": "approval_required",
                "approval_id": approval.id,
                "summary": summary,
                "reason": reason,
                "run_id": run.id,
                "steps": command_preview.splitlines(),
                "message": "User ko bolo ki dashboard me approval card aaya hai, approve kare to scan chalega.",
            },
            step={"type": "approval", "approval_id": approval.id, "summary": summary, "target": scope.host, "profile": profile, "run_id": run.id},
            pending={
                "id": approval.id,
                "summary": summary,
                "command": command_preview,
                "target": scope.host,
                "run_id": run.id,
                "reason": reason,
            },
        )

    run = runs.create(target_raw, steps, "agent", ctx.actor, profile)
    runs.execute_sync(run, steps)
    ctx.runs_seen.append(run.id)
    audit.log("agent_scan", run=run.id, target=run.target, profile=profile, actor=ctx.actor)
    return ToolOutcome(
        payload=_run_payload(run, max_chars=8000),
        step={"type": "scan", "run_id": run.id, "target": scope.host, "profile": profile, "status": run.status},
    )


def _validate_args(raw_args: Any) -> tuple[list[str], str | None]:
    if raw_args is None:
        return [], None
    if not isinstance(raw_args, list):
        return [], "args ek array (list of strings) hona chahiye"
    result: list[str] = []
    for item in raw_args[:20]:
        token = str(item)
        if len(token) > 200:
            return [], f"arg bahut lamba: {token[:40]}..."
        if set(token) & _FORBIDDEN_ARG_CHARS:
            return [], f"arg me ye chars allowed nahi: {' '.join(sorted(set(token) & _FORBIDDEN_ARG_CHARS))}"
        result.append(token)
    return result, None


def _tool_run_command(args: dict[str, Any], ctx: AgentContext) -> ToolOutcome:
    tool_name = str(args.get("tool", "")).strip().lower()
    spec = resolve_tool(tool_name)
    if spec is None:
        return ToolOutcome(
            {
                "error": f"'{tool_name}' known tool nahi hai.",
                "available_tools": sorted(t for t in all_tool_status() if t["installed"]),
            }
        )
    argv_args, invalid = _validate_args(args.get("args"))
    if invalid:
        return ToolOutcome({"error": invalid})

    target_param = str(args.get("target", "")).strip()
    scope_host = ""
    if target_param:
        try:
            scope = check_target(target_param, source="agent")
        except ValueError as exc:
            return ToolOutcome({"error": str(exc)})
        scope_host = scope.host
        tokens = [scope.url or scope.host] if spec.name in ("whatweb", "nikto", "nuclei", "sqlmap", "curl") else [scope.host]
        if spec.name in ("gobuster", "ffuf"):
            tokens = [(scope.url or f"https://{scope.host}").rstrip("/")]
        for token in tokens:
            if token not in argv_args:
                argv_args.append(token)

    # Wordlist-dependent tools
    if spec.name in ("gobuster", "ffuf") and "-w" not in argv_args:
        wl = wordlist_path()
        if not wl:
            return ToolOutcome({"error": "Wordlist nahi mili (dirb/seclists install karo)."})
        argv_args += ["-w", wl]

    if not spec.installed():
        return ToolOutcome(
            {
                "error": f"'{spec.binary}' install nahi hai.",
                "install": f"apt-get update && apt-get install -y {spec.package}",
            }
        )

    full_argv = [spec.binary] + argv_args
    command_display = " ".join(full_argv)
    needs_human = approvals.approval_required(spec.needs_approval, settings.effective_approval_mode)

    if needs_human:
        if not scope_host and not target_param:
            scope_host = "(no target)"
        approval = approvals.create(
            kind="command",
            summary=f"{spec.name} command chalao: {command_display[:120]}",
            command=command_display,
            target=scope_host or target_param or "-",
            actor=ctx.actor,
        )
        # command-type approval ke liye continuation: run karke followup me daal do
        def continuation(approved: bool) -> None:
            if approved:
                result = run_command(full_argv, timeout=min(180, settings.max_scan_seconds))
                payload = {
                    "status": result["status"],
                    "exit_code": result["exit_code"],
                    "command": command_display,
                    "output": result["output"][:MAX_TOOL_RESULT_CHARS],
                    "error": result["error"],
                }
            else:
                payload = {"status": "denied", "command": command_display}
            if ctx.pending_tool_call_id:
                ctx.messages.append(
                    {"role": "tool", "tool_call_id": ctx.pending_tool_call_id, "content": json.dumps(payload)[:MAX_TOOL_RESULT_CHARS]}
                )
            try:
                result = _agent_loop(ctx)
            except AIError as exc:
                _set_followup(ctx.conversation_id, {"status": "error", "reply": f"AI error: {exc}", "steps": []})
                return
            _set_followup(
                ctx.conversation_id,
                {"status": "ready", "reply": result["reply"], "steps": result.get("steps", []), "runs": result.get("runs", []), "model": result.get("model", "")},
            )

        approval.continuation = continuation
        return ToolOutcome(
            payload={
                "status": "approval_required",
                "approval_id": approval.id,
                "summary": approval.summary,
                "command": command_display,
                "message": "User ko bolo approval card approve kare.",
            },
            step={"type": "approval", "approval_id": approval.id, "summary": approval.summary},
            pending={"id": approval.id, "summary": approval.summary, "command": command_display, "target": scope_host or "-", "run_id": None, "reason": "Intrusive/dangerous tool — human approval mandatory."},
        )

    result = run_command(full_argv, timeout=min(150, settings.max_scan_seconds))
    audit.log("agent_command", tool=spec.name, cmd=command_display, actor=ctx.actor, status=result["status"])
    return ToolOutcome(
        payload={
            "command": command_display,
            "status": result["status"],
            "exit_code": result["exit_code"],
            "duration": result["duration"],
            "output": result["output"][:8000],
            "error": result["error"],
        },
        step={"type": "command", "tool": spec.name, "command": command_display, "status": result["status"]},
    )


def _tool_get_run_report(args: dict[str, Any], ctx: AgentContext) -> ToolOutcome:
    run_id = str(args.get("run_id", "")).strip()
    run = runs.get(run_id)
    if run is None:
        return ToolOutcome({"error": f"run '{run_id}' nahi mila.", "available_runs": [r.id for r in runs.list(10)]})
    return ToolOutcome({"report_text": run.compact_report(max_chars_per_step=3000)[:MAX_TOOL_RESULT_CHARS], "run_id": run.id})


def _tool_generate_report(args: dict[str, Any], ctx: AgentContext) -> ToolOutcome:
    run_id = str(args.get("run_id", "")).strip()
    run = runs.get(run_id)
    if run is None:
        return ToolOutcome({"error": f"run '{run_id}' nahi mila."})
    summary = summarize_run(run)
    path = report.save(run, str(args.get("name", "") or None), summary)
    audit.log("report_saved", run=run.id, file=path.name, actor=ctx.actor)
    return ToolOutcome(
        {
            "status": "saved",
            "file": path.name,
            "path": str(path),
            "ai_summary_included": bool(summary),
            "message": f"Report save ho gayi: {path.name}. Dashboard ke Reports tab se download kar sakte ho.",
        },
        step={"type": "report", "file": path.name, "run_id": run.id},
    )


def _tool_list_tools(args: dict[str, Any], ctx: AgentContext) -> ToolOutcome:
    statuses = all_tool_status()
    return ToolOutcome(
        {
            "installed": [{"name": s["name"], "version": s["version"], "category": s["category"]} for s in statuses if s["installed"]],
            "missing": [{"name": s["name"], "install": f"apt-get install -y {s['package']}"} for s in statuses if not s["installed"]],
            "wordlist": wordlist_path(),
        }
    )


_DISPATCH = {
    "check_scope": _tool_check_scope,
    "run_scan": _tool_run_scan,
    "run_command": _tool_run_command,
    "get_run_report": _tool_get_run_report,
    "generate_report": _tool_generate_report,
    "list_tools": _tool_list_tools,
}


def _parse_call(tool_call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    function = tool_call.get("function") or {}
    name = str(function.get("name", ""))
    raw = function.get("arguments") or "{}"
    try:
        args = json.loads(raw) if isinstance(raw, str) else (raw or {})
        if not isinstance(args, dict):
            args = {"value": args}
    except json.JSONDecodeError:
        args = {}
    return name, args


# --------------------------------------------------------------------------
# Agent loop
# --------------------------------------------------------------------------
def _agent_loop(ctx: AgentContext) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for _ in range(max(1, settings.ai_max_steps)):
        assistant = chat(ctx.messages, tools=TOOL_SCHEMAS)
        ctx.messages.append(_clean_for_history(assistant))
        content = assistant.get("content") or ""
        tool_calls = assistant.get("tool_calls") or []
        if not tool_calls:
            return {
                "reply": content or "(Model ne koi text nahi diya.)",
                "steps": steps,
                "runs": list(dict.fromkeys(ctx.runs_seen)),
                "model": assistant.get("_model", settings.model),
            }

        pending: tuple[dict, ToolOutcome, str] | None = None
        for index, tool_call in enumerate(tool_calls):
            name, args = _parse_call(tool_call)
            call_id = str(tool_call.get("id") or f"call_{index}")
            handler = _DISPATCH.get(name)
            if handler is None:
                outcome = ToolOutcome({"error": f"unknown tool '{name}'"})
            else:
                try:
                    outcome = handler(args, ctx)
                except Exception as exc:  # pragma: no cover - defensive
                    outcome = ToolOutcome({"error": f"tool '{name}' failed: {exc}"})

            if outcome.pending:
                if pending is None:
                    pending = (tool_call, outcome, call_id)
                    steps.append(
                        outcome.step
                        or {"type": "approval", "approval_id": outcome.pending["id"], "summary": outcome.pending["summary"]}
                    )
                else:
                    # Ek turn me ek hi approval handle karte hain — baaki auto-deny
                    approvals.cancel(outcome.pending["id"], reason="auto-denied (ek turn me ek approval)")
                    ctx.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps({"status": "not_executed", "reason": "ek turn me sirf ek approval handle hoti hai"}),
                        }
                    )
                continue

            steps.append(outcome.step or {"type": "tool", "tool": name, "args": args})
            ctx.messages.append(
                {"role": "tool", "tool_call_id": call_id, "content": json.dumps(outcome.payload)[:MAX_TOOL_RESULT_CHARS]}
            )

        if pending is not None:
            tool_call, outcome, call_id = pending
            ctx.pending_tool_call_id = call_id
            ctx.pending_pending = outcome.pending
            audit.log("agent_approval_wait", approval=outcome.pending["id"], actor=ctx.actor, summary=outcome.pending["summary"])
            return {
                "reply": content
                or f"Approval chahiye: {outcome.pending['summary']}. Dashboard me approval card aaya hai — approve karo to scan chal jayega.",
                "steps": steps,
                "runs": list(dict.fromkeys(ctx.runs_seen)),
                "needs_approval": outcome.pending,
                "model": assistant.get("_model", settings.model),
                "awaiting_approval": True,
            }

    # Step budget khatam — final summary maango
    try:
        final = chat(
            ctx.messages
            + [{"role": "user", "content": "Ab aur tool call mat karo. Ab tak ke results ke basis par short final answer do."}],
            temperature=0.3,
        )
        reply = final.get("content") or "Step limit reach ho gayi — results upar diye gaye hain."
    except AIError as exc:
        reply = f"Step limit reach ho gayi. ({exc})"
    return {"reply": reply, "steps": steps, "runs": list(dict.fromkeys(ctx.runs_seen)), "model": settings.model}


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------
def run_agent(
    history: Any,
    *,
    actor: str,
    conversation_id: str,
    model: str | None = None,
) -> dict[str, Any]:
    if not settings.ai_configured:
        raise AIError(
            "AI chat ke liye OPENROUTER_API_KEY chahiye. Environment variable set karo aur restart karo. "
            "(Scanning, tools aur reports bina AI ke bhi chalte hain.)"
        )
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += _public_history(history)
    ctx = AgentContext(
        actor=actor,
        conversation_id=conversation_id,
        messages=messages,
        model=_pick_model(model) if model else "",
    )
    audit.log("agent_chat", actor=actor, conversation=conversation_id, turns=len(messages))
    result = _agent_loop(ctx)
    result["conversation_id"] = conversation_id
    result.setdefault("steps", [])
    return result

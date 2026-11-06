#!/usr/bin/env python3
"""Super Agent — terminal client (Linux/Kali/Termux/Windows par chalta hai).

Do tarah se use karo:

  1) SERVER se baat karke (recommended — server par tools chalte hain):
         python -m superagent.cli --url http://127.0.0.1:8000 --token <API_TOKEN>
     phir `agent` mode me natural language, aur `!` se shell passthrough.

  2) LOCAL agent (jis machine par tools installed hain, wahi):
         python -m superagent.cli --local    # same process me agent + tools

Commands (REPL ke andar):
    /help                     help
    /mode agent|shell         agent (Hinglish) ya direct shell
    /ask <text>               ek baar AI se poochho
    /tool <name> <target> [k=v ...]     catalog tool chalao
    /scope <target>           authorization check
    /records                  engagement records
    /runs                     recent runs
    /read <run_id>            run output
    /approve <id> /deny <id>  pending approval decide karo
    /auto on|off              non-intrusive tools bina approval (intrusive always approval)
    /model <id>               model badlo
    /report <title>           last session ka report banao (AI se)
    /audit                    audit tail
    /exit

Shell mode me:
    !<command>                server par shell (approval lagega agar ON hai)
    agent <text>              us line ko AI ko bhejo
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

BANNER = r"""
  ██████╗  █████╗ ████████╗ █████╗ ███╗   ██╗███████╗███████╗ ██████╗
  ██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗████╗  ██║██╔════╝██╔════╝██╔════╝
  ██████╔╝███████║   ██║   ███████║██╔██╗ ██║███████╗█████╗  ██║
  ██╔══██╗██╔══██║   ██║   ██╔══██║██║╚██╗██║╚════██║██╔══╝  ██║
  ██║  ██║██║  ██║   ██║   ██║  ██║██║ ╚████║███████║███████╗╚██████╗
  ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝ ╚═════╝
      Super Agent — authorised AI security terminal
"""

HELP = """
Commands
  /mode agent|shell            mode badlo
  /ask <text>                  ek baar AI se poochho
  /tool <name> <target> [k=v]  catalog tool (jaise: /tool nuclei https://lab.local severity=high)
  /scope <target>              authorization check
  /records                     engagement records (scope + validity)
  /runs [n]                    recent runs
  /read <run_id>               run ka output
  /approve <id>  /deny <id>    pending approval
  /auto on|off                 non-intrusive auto-approve
  /model <id>                  model badlo
  /shell on|off                server shell mode (agar server par allowed ho)
  /report <title>              session summary report
  /audit                       audit tail
  /sections                    tool arsenal
  /clear  /exit
Shell mode
  !<cmd>                       server par command (guard + approval)
  koi bhi aur text             AI ko jata hai
"""


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------
class ApiClient:
    def __init__(self, base: str, token: str) -> None:
        self.base = base.rstrip("/")
        self.token = token

    def call(self, path: str, method: str = "GET", body: dict | None = None) -> Any:
        url = f"{self.base}{path}"
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "X-Agent-Token": self.token}
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(raw).get("detail", raw)
            except json.JSONDecodeError:
                detail = raw
            raise CliError(f"[{exc.code}] {detail}")
        except urllib.error.URLError as exc:
            raise CliError(f"Server se connect nahi hua ({self.base}): {exc.reason}. Server chalu hai?")


class CliError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Local mode transport (same process, no HTTP)
# ---------------------------------------------------------------------------
class LocalClient:
    def __init__(self) -> None:
        from . import agent, approvals, records, report, runner, scope, settings  # noqa: F401

        self._agent = agent
        self._runner = runner
        self._scope = scope
        self._approvals = approvals
        self._records = records
        self._report = report
        self.session = "cli-local"

    def call(self, path: str, method: str = "GET", body: dict | None = None) -> Any:
        body = body or {}
        if path == "/api/status":
            return self._agent.status()
        if path == "/api/agent/chat":
            return self._agent.run_turn(self.session, body["message"],
                                        auto_approve=body.get("auto_approve"))
        if path.startswith("/api/agent/followup/"):
            return self._agent.get_followup(path.rsplit("/", 1)[-1]) or {"status": "pending"}
        if path == "/api/command":
            cmd = self._runner.build_tool_command(body["tool"], target=body.get("target", ""),
                                                  flags=body.get("flags") or {})
            result = self._runner.commands.submit(cmd)
            return {"status": "running", "run": result.view(tail=4000)}
        if path == "/api/command/shell":
            cmd = self._runner.build_shell_command(body["command"])
            result = self._runner.commands.submit(cmd)
            return {"status": "running", "run": result.view(tail=4000)}
        if path == "/api/scope/check":
            return self._scope.check(body["target"], body.get("section", "recon")).view()
        if path == "/api/records":
            if method == "POST":
                import time as _t
                item = self._records.records.create(**body)
                return {"record": item.view()}
            return {"records": [r.view() for r in self._records.records.all()]}
        if path == "/api/runs":
            return {"runs": [r.view(tail=4000) for r in self._runner.commands.list(20)]}
        if path.startswith("/api/runs/"):
            result = self._runner.commands.get(path.rsplit("/", 1)[-1])
            return {"run": result.view(tail=20000)} if result else {}
        if path == "/api/approvals":
            return {"approvals": self._approvals.list_all(), "pending": self._approvals.pending_count()}
        if path.startswith("/api/approvals/"):
            item = self._approvals.decide(path.rsplit("/", 1)[-1], bool(body.get("approved")), "cli")
            return {"approval": item.view()}
        if path == "/api/audit":
            from . import audit

            return {"events": audit.recent(30)}
        raise CliError(f"local mode me '{path}' support nahi hai.")


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------
def _c(text: str, code: str) -> str:
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def dim(text: str) -> str:
    return _c(text, "2")


def bold(text: str) -> str:
    return _c(text, "1")


def ok(text: str) -> str:
    return _c(text, "32")


def warn(text: str) -> str:
    return _c(text, "33")


def bad(text: str) -> str:
    return _c(text, "31")


def head(text: str) -> str:
    return _c(text, "36")


STATUS_ICON = {"done": ok("✔"), "error": bad("✖"), "timeout": warn("⏱"),
               "running": head("▶"), "queued": dim("…"), "cancelled": warn("⊘")}


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------
@dataclass
class State:
    mode: str = "agent"
    auto: bool = False
    model: str = ""
    session: str = ""
    shell_enabled: bool = False


def render_response(data: dict, client: Any) -> None:
    steps = data.get("steps") or []
    for step in steps:
        kind = step.get("type")
        if kind == "run":
            print(f"  {head('▶')} {step.get('command', '')}")
        elif kind == "approval":
            print(f"  {warn('⚑')} approval chahiye: {step.get('summary', '')}")
        elif kind == "report":
            print(f"  {ok('📄')} report: {step.get('file', '')}")
    job = data.get("job") if isinstance(data.get("job"), dict) else None
    if job:
        _print_job(job)
    reply = data.get("reply") or ""
    if reply:
        print()
        print(reply)
    if data.get("awaiting_approval"):
        pending = data.get("needs_approval") or {}
        print()
        print(f"  {warn('⚑ Approval pending')} id={bold(pending.get('id', ''))}")
        print(f"    {pending.get('command', '')}")
        print(f"    Approve karne ke liye: {bold('/approve ' + str(pending.get('id', '')))}")
        for _ in range(120):
            time.sleep(5)
            try:
                follow = client.call(f"/api/agent/followup/{data.get('session_id', '')}")
            except CliError:
                return
            if follow.get("status") == "ready":
                print()
                print(head("── approval ke baad ──"))
                render_response({**follow, "session_id": data.get("session_id", "")}, client)
                return
            if follow.get("status") == "error":
                print(bad(follow.get("reply", "error")))
                return


def _print_job(job: dict) -> None:
    icon = STATUS_ICON.get(job.get("status", ""), "")
    meta = f"[{job.get('status')} · {job.get('duration', 0)}s]"
    print(f"  {icon} {dim(job.get('command', ''))}  {dim(meta)}")
    output = job.get("output") or ""
    if output.strip():
        print("-" * 72)
        print(output.rstrip()[:20000])
        print("-" * 72)
    if job.get("error") and job.get("status") not in ("done",):
        print(warn(f"  {job['error']}"))
    if job.get("status") in ("running", "queued") and job.get("id"):
        print(dim(f"  live: /read {job['id']}"))


def repl(client: Any, state: State) -> int:
    print(bold(head("RatanSec Super Agent")) + dim(" — /help se commands dekho"))
    while True:
        prompt = f"{ok('agent') if state.mode == 'agent' else warn('shell')} » " if sys.stdout.isatty() else "» "
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in ("/exit", "/quit", "exit", "quit"):
            return 0
        if line == "/clear":
            os.system("clear" if os.name != "nt" else "cls")
            continue
        if line.startswith("/"):
            try:
                handle_command(client, state, line)
            except CliError as exc:
                print(bad(str(exc)))
            continue
        if line.startswith("!"):
            _shell(client, state, line[1:].strip())
            continue
        if line.lower().startswith("agent "):
            line = line[6:]
        if state.mode == "shell" and not line.lower().startswith("agent "):
            _shell(client, state, line)
            continue
        _chat(client, state, line)


def _chat(client: Any, state: State, text: str) -> None:
    payload = {"message": text, "session_id": state.session, "auto_approve": state.auto}
    if state.model:
        payload["model"] = state.model
    print(dim("  … soch raha hoon"))
    try:
        data = client.call("/api/agent/chat", "POST", payload)
    except CliError as exc:
        print(bad(str(exc)))
        return
    state.session = data.get("session_id", state.session)
    render_response(data, client)


def _shell(client: Any, state: State, command: str) -> None:
    if not command:
        return
    try:
        data = client.call("/api/command/shell", "POST", {"command": command})
    except CliError as exc:
        print(bad(str(exc)))
        return
    if data.get("status") == "approval_required":
        item = data.get("approval") or {}
        print(warn(f"⚑ Approval needed id={item.get('id')} — /approve {item.get('id')}"))
        print(dim(f"   {item.get('command', '')}"))
        _watch_runs(client)
        return
    job = (data.get("run") or {})
    _print_job(job)
    _follow_run(client, job.get("id", ""))


def _follow_run(client: Any, run_id: str, seconds: int = 240) -> None:
    if not run_id:
        return
    seen = 0
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            data = client.call(f"/api/runs/{run_id}")
        except CliError:
            return
        job = data.get("run") or {}
        output = job.get("output") or ""
        if len(output) > seen:
            chunk = output[seen:]
            seen = len(output)
            sys.stdout.write(chunk)
            sys.stdout.flush()
        if job.get("status") not in ("running", "queued"):
            print()
            print(dim(f"[{job.get('status')} · exit {job.get('exit_code')} · {job.get('duration')}s]"))
            return
        time.sleep(1.2)
    print(dim("\n[abhi bhi chal raha hai — /read <id> se dekho]"))


def _watch_runs(client: Any) -> None:
    try:
        data = client.call("/api/runs?limit=5")
    except CliError:
        return
    if data.get("runs"):
        print(dim("  recent runs: " + ", ".join(r["id"] for r in data["runs"])))


def handle_command(client: Any, state: State, line: str) -> None:
    parts = line.split()
    cmd = parts[0].lower()
    rest = line[len(parts[0]):].strip()

    if cmd in ("/help", "/h", "/?"):
        print(HELP)
    elif cmd == "/mode":
        mode = rest.lower()
        if mode in ("agent", "shell"):
            state.mode = mode
            print(ok(f"mode = {mode}"))
        else:
            print(warn("use: /mode agent  |  /mode shell"))
    elif cmd == "/auto":
        state.auto = rest.lower() in ("on", "1", "true", "yes")
        print(ok(f"auto-approve (non-intrusive only) = {state.auto}"))
    elif cmd == "/model":
        state.model = rest
        print(ok(f"model = {rest or '(default)'}"))
    elif cmd == "/ask":
        _chat(client, state, rest)
    elif cmd == "/tool":
        _tool(client, rest)
    elif cmd == "/scope":
        data = client.call("/api/scope/check", "POST", {"target": rest, "section": "recon"})
        _print_scope(data)
    elif cmd == "/records":
        data = client.call("/api/records")
        for record in data.get("records", []):
            flag = ok("ACTIVE") if record["active"] else dim("expired")
            print(f"  {flag}  {bold(record['id'])}  {record['client']}  [{record['scope_text']}]  "
                  f"{record['start_str']} → {record['end_str']}")
    elif cmd == "/runs":
        limit = rest or "20"
        data = client.call(f"/api/runs?limit={limit}")
        for run in data.get("runs", []):
            print(f"  {STATUS_ICON.get(run['status'], '?')} {run['id']}  {dim(run['display'][:90])}")
    elif cmd == "/read":
        data = client.call(f"/api/runs/{rest}")
        job = data.get("run") or {}
        print(job.get("output", "(no output)"))
    elif cmd in ("/approve", "/deny"):
        data = client.call(f"/api/approvals/{rest}", "POST", {"approved": cmd == "/approve"})
        print(ok(f"{data['approval']['status']}: {data['approval']['summary']}"))
    elif cmd == "/sections":
        data = client.call("/api/sections")
        for section in data.get("sections", []):
            count_label = f"({section['count']} tools)"
            print(f"\n{section['icon']} {bold(section['title'])}  {dim(count_label)}")
            for tool in section["tools"]:
                mark = ok("●") if tool["installed"] else dim("○")
                lock = warn(" [approval]") if tool["intrusive"] else ""
                print(f"   {mark} {tool['name']:<22} {dim(tool['summary'][:70])}{lock}")
    elif cmd == "/audit":
        data = client.call("/api/audit")
        for event in data.get("events", [])[:30]:
            print(f"  {dim(event.get('time', ''))} {event.get('event'):<22} "
                  f"{dim(str({k: v for k, v in event.items() if k not in ('ts', 'time', 'event', 'prev', 'hash')})[:120])}")
    elif cmd == "/report":
        _report(client, state, rest)
    elif cmd == "/shell":
        if rest.lower() in ("on", "off"):
            state.mode = "shell" if rest.lower() == "on" else "agent"
        print(ok(f"mode = {state.mode}"))
    else:
        print(warn(f"unknown command: {cmd} — /help dekho"))


def _tool(client: Any, rest: str) -> None:
    parts = rest.split()
    if len(parts) < 1:
        print(warn("use: /tool <name> <target> [flag=value ...]"))
        return
    name = parts[0]
    target = ""
    flags: dict[str, Any] = {}
    for token in parts[1:]:
        if "=" in token:
            key, _, value = token.partition("=")
            flags[key] = value
        elif not target:
            target = token
    try:
        data = client.call("/api/command", "POST", {"tool": name, "target": target, "flags": flags})
    except CliError as exc:
        print(bad(str(exc)))
        return
    if data.get("status") == "approval_required":
        item = data.get("approval") or {}
        print(warn(f"⚑ Approval needed id={item.get('id')} — /approve {item.get('id')}"))
        return
    job = data.get("run") or {}
    _print_job(job)
    _follow_run(client, job.get("id", ""))


def _print_scope(data: dict) -> None:
    if data.get("allowed"):
        print(ok(f"✔ ALLOWED — {data.get('reason')}"))
    else:
        print(bad(f"✖ NOT ALLOWED — {data.get('reason')}"))


def _report(client: Any, state: State, title: str) -> None:
    prompt = (
        "Ab tak ke is session ke saare findings ka ek professional Markdown penetration-test report banao. "
        "Sections: Executive Summary, Scope & Authorization, Methodology, Findings (severity ke saath table), "
        "Evidence (commands + key output lines), Remediation, Appendix. "
        "Jo verify nahi hua use 'not confirmed' likho."
    )
    payload = {"message": prompt, "session_id": state.session, "auto_approve": state.auto}
    data = client.call("/api/agent/chat", "POST", payload)
    reply = data.get("reply", "")
    saved = client.call("/api/reports", "POST", {"title": title or "Super Agent Report", "markdown": reply})
    print(ok(f"📄 report saved: {saved.get('file')}"))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RatanSec Super Agent — terminal client")
    parser.add_argument("--url", default=os.environ.get("SUPERAGENT_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.environ.get("SUPERAGENT_API_TOKEN", ""))
    parser.add_argument("--local", action="store_true", help="server ke bina, isi machine par agent chalao")
    parser.add_argument("--ask", default="", help="ek command chala kar exit")
    parser.add_argument("--tool", default="", help="tool name (target --target)")
    parser.add_argument("--target", default="")
    parser.add_argument("--no-banner", action="store_true")
    args = parser.parse_args(argv)

    if not args.no_banner and sys.stdout.isatty():
        print(head(BANNER))

    try:
        client: Any = LocalClient() if args.local else ApiClient(args.url, args.token)
    except Exception as exc:  # pragma: no cover
        print(bad(f"Client start nahi hua: {exc}"))
        return 2

    state = State()
    try:
        status = client.call("/api/status")
    except CliError as exc:
        print(bad(str(exc)))
        return 2
    ai = status.get("ai") or {}
    print(dim(f"server : {args.url if not args.local else 'local'}"))
    print(f"model  : {ai.get('model')}  {'✔' if ai.get('configured') else warn('(AI key nahi)')}")
    print(f"tools  : {status.get('tools_total')} "
          f"({status.get('intrusive_tools')} approval-only) · "
          f"records: {status.get('records_active')} active · "
          f"shell: {'on' if status.get('shell_allowed') else 'off'}")

    if args.tool:
        _tool(client, f"{args.tool} {args.target}".strip())
        return 0
    if args.ask:
        _chat(client, state, args.ask)
        return 0
    try:
        return repl(client, state)
    except KeyboardInterrupt:
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

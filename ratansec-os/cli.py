#!/usr/bin/env python3
"""RatanSec OS CLI — terminal se dashboard/API control karo.

Examples:
    python cli.py status
    python cli.py tools
    python cli.py scan --target example.com --profile quick --wait
    python cli.py scan --target example.com --profile full --wait --report
    python cli.py runs
    python cli.py show <run_id>
    python cli.py chat "example.com ka quick recon karo"
    python cli.py approvals
    python cli.py approve <approval_id>
    python cli.py audit

Auth (agar APP_PASSWORD set hai):
    export RATANSEC_PASSWORD='...'    # ya --password
    export RATANSEC_URL='https://your-app.onrender.com'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = os.environ.get("RATANSEC_URL", "http://127.0.0.1:8000")
TOKEN = os.environ.get("RATANSEC_TOKEN") or os.environ.get("RATANSEC_PASSWORD") or os.environ.get("APP_PASSWORD", "")

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


CYAN, GREEN, RED, YELLOW, DIM, BOLD = "36", "32", "31", "33", "2", "1"


class ApiError(RuntimeError):
    pass


def call(method: str, path: str, body: dict | None = None, url: str = DEFAULT_URL, token: str = TOKEN) -> dict:
    request_url = url.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(request_url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read().decode("utf-8", "replace")).get("detail", "")
        except Exception:
            pass
        if exc.code == 401:
            raise ApiError("Unauthorized — RATANSEC_PASSWORD / APP_PASSWORD check karo (ya --password do).")
        raise ApiError(f"HTTP {exc.code}: {detail or exc.reason}")
    except urllib.error.URLError as exc:
        raise ApiError(f"Server reachable nahi hai ({request_url}): {exc.reason}")


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def status_color(status: str) -> str:
    return {
        "done": GREEN,
        "installed": GREEN,
        "running": CYAN,
        "queued": CYAN,
        "pending": YELLOW,
        "approval_required": YELLOW,
        "timeout": RED,
        "error": RED,
        "denied": RED,
    }.get(status, DIM)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def cmd_status(args) -> int:
    data = call("GET", "/api/status", url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    print(c(f" {data['app']} v{data['version']} ", BOLD))
    ai = data.get("ai", {})
    print(f"  AI       : {c('configured', GREEN) if ai.get('configured') else c('NOT configured', RED)}  model={ai.get('model')}")
    print(f"  Auth     : {'on' if data.get('auth_required') else c('OFF (public!)', RED)}")
    scope = data.get("scope") or {}
    print(f"  Scope    : {scope.get('allowed_targets') or '(khaali — manual approval mode)'}")
    print(f"  Mode     : {scope.get('approval_mode')}")
    print(f"  Tools    : {data.get('tools', {}).get('installed', '?')}/{data.get('tools', {}).get('total', '?')} installed")
    print(f"  Runs     : {data.get('runs_active', 0)} active, {data.get('runs_total', 0)} total")
    print(f"  Approvals: {data.get('approvals_pending', 0)} pending")
    env = data.get("environment") or {}
    print(f"  Env      : {env.get('distribution', '?')} · {env.get('kernel', '?')} · docker={env.get('docker')}")
    return 0


def cmd_tools(args) -> int:
    data = call("GET", f"/api/tools?refresh={str(args.refresh).lower()}", url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    for tool in data["tools"]:
        mark = c("✓", GREEN) if tool["installed"] else c("✗", RED)
        version = (tool.get("version") or "")[:48]
        flag = c(" [approval]", YELLOW) if tool["needs_approval"] else ""
        print(f" {mark} {tool['name']:<10} {tool['category']:<14} {version:<50}{flag}")
        if not tool["installed"]:
            print(f"   {c('install:', DIM)} apt-get install -y {tool['package']}")
    return 0


def cmd_profiles(args) -> int:
    data = call("GET", "/api/profiles", url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    for profile in data["profiles"]:
        print(f" {c(profile['name'], CYAN)} — {c(profile['title'], BOLD)}\n   {profile['description']}")
    return 0


def wait_for_run(run_id: str, args, show: bool = True) -> dict:
    last = ""
    while True:
        data = call("GET", f"/api/runs/{run_id}", url=args.url, token=args.token)["run"]
        if show:
            for step in data["steps"]:
                line = f"  [{step['status']:<8}] {step['tool']:<9} {step['label']}"
                if line != last:
                    print(c(line, status_color(step["status"])))
                    last = line
        if data["status"] in ("done", "error", "cancelled"):
            return data
        time.sleep(3)


def cmd_scan(args) -> int:
    data = call("POST", "/api/scan", {"target": args.target, "profile": args.profile}, url=args.url, token=args.token)
    if args.json and not args.wait:
        print_json(data)
        return 0

    if data.get("status") == "approval_required":
        approval = data["approval"]
        print(c("⚠️  Approval chahiye:", YELLOW))
        print(f"   {approval['summary']}")
        print(c(f"   approve: ratansec approve {approval['id']}", DIM))
        if not args.wait:
            return 0
        print("   Approve karne ka wait kar raha hoon (dashboard ya CLI se approve karo)…")
        deadline = time.time() + 1800
        while time.time() < deadline:
            state = call("GET", "/api/approvals", url=args.url, token=args.token)
            match = next((a for a in state["approvals"] if a["id"] == approval["id"]), None)
            if match and match["status"] != "pending":
                if match["status"] != "approved":
                    print(c(f"   {match['status']} — scan nahi chalega.", RED))
                    return 1
                print(c("   approved!", GREEN))
                break
            time.sleep(5)
        else:
            print(c("   timeout: approval nahi mili.", RED))
            return 1

    run = data.get("run", {})
    run_id = run.get("id")
    if not args.wait:
        print(f"Run started: {c(run_id, CYAN)} (status: {run.get('status')})")
        return 0

    print(f"Run {c(run_id, CYAN)} start ho gaya — output aa raha hai…\n")
    final = wait_for_run(run_id, args)
    print()
    print(f" {c('Status:', BOLD)} {c(final['status'], status_color(final['status']))}")
    for step in final["steps"]:
        if step["status"] in ("done", "timeout", "error"):
            print(c(f"\n── {step['label']} ({step['duration']}s, exit {step['exit_code']}) ", DIM))
            print(step["output"][:6000].rstrip() or c("(no output)", DIM))

    if args.report:
        print()
        print(c("Report generate ho rahi hai (AI analysis ke saath)…", DIM))
        rep = call("POST", f"/api/runs/{run_id}/report", {"ai": True}, url=args.url, token=args.token)
        print(c(f"✅ Report saved: {rep['file']}", GREEN))
        if rep.get("ai_summary"):
            print(c("\n── AI Analysis ──", BOLD))
            print(rep["ai_summary"])
    if args.json:
        print_json(final)
    return 0


def cmd_runs(args) -> int:
    data = call("GET", f"/api/runs?limit={args.limit}", url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    if not data["runs"]:
        print(c("Koi run nahi hua.", DIM))
        return 0
    for run in data["runs"]:
        status = c(f"{run['status']:<9}", status_color(run["status"]))
        stamp = time.strftime("%d %b %H:%M", time.localtime(run["created"]))
        print(f" {status} {run['id']}  {run['target']:<32} {run['profile']:<8} {run['steps_done']}/{run['steps_total']}  {stamp}  {run['source']}")
    return 0


def cmd_show(args) -> int:
    data = call("GET", f"/api/runs/{args.run_id}", url=args.url, token=args.token)
    run = data["run"]
    if args.json:
        print_json(data)
        return 0
    print(f" {c(run['target'], BOLD)} · {run['profile']} · {c(run['status'], status_color(run['status']))} · run {run['id']}")
    for step in run["steps"]:
        print(c(f"\n── [{step['status']}] {step['label']} ", DIM))
        print(c(f"$ {step['command']}", DIM))
        if step["output"]:
            print(step["output"][:8000].rstrip())
        if step["error"]:
            print(c(f"error: {step['error']}", RED))
    return 0


def cmd_report(args) -> int:
    body = {"ai": not args.no_ai, "name": args.name or ""}
    data = call("POST", f"/api/runs/{args.run_id}/report", body, url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    print(c(f"✅ Report saved: {data['file']}", GREEN))
    if data.get("ai_summary"):
        print(c("\n── AI Analysis ──", BOLD))
        print(data["ai_summary"])
    return 0


def cmd_reports(args) -> int:
    data = call("GET", "/api/reports", url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    for item in data["reports"]:
        print(f" {item['name']:<60} {round(item['size'] / 1024)} KB  {time.strftime('%d %b %H:%M', time.localtime(item['modified']))}")
    if not data["reports"]:
        print(c("Koi report nahi bani.", DIM))
    return 0


def cmd_get_report(args) -> int:
    data = call("GET", f"/api/reports/{args.name}", url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    print(data["content"])
    return 0


def cmd_chat(args) -> int:
    history = [{"role": "user", "content": args.message}]
    data = call(
        "POST",
        "/api/chat",
        {"messages": history, "conversation_id": args.conversation or f"cli-{int(time.time())}"},
        url=args.url,
        token=args.token,
    )
    if args.json:
        print_json(data)
        return 0
    print(c("\n🧠 AI:\n", BOLD))
    print(data.get("reply", "(no reply)"))
    for step in data.get("steps", []):
        kind = step.get("type", "tool")
        print(c(f"   · {kind} {step.get('run_id') or step.get('file') or step.get('approval_id') or step.get('tool') or ''}", DIM))
    if data.get("needs_approval"):
        pending = data["needs_approval"]
        print()
        print(c(f"⚠️  Approval chahiye: {pending['summary']}", YELLOW))
        print(c(f"   approve karne ke liye: python cli.py approve {pending['id']}", DIM))
    return 0


def cmd_approvals(args) -> int:
    data = call("GET", "/api/approvals", url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    if not data["approvals"]:
        print(c("Koi approval pending nahi.", DIM))
        return 0
    for item in data["approvals"]:
        print(f" {c(item['status'], status_color(item['status'])):<10} {item['id']}  {item['summary']}")
        if item["status"] == "pending":
            print(c(f"   {item['command'].splitlines()[0] if item['command'] else ''}", DIM))
    return 0


def _decide(args, approved: bool) -> int:
    data = call(
        "POST",
        f"/api/approvals/{args.approval_id}",
        {"approved": approved, "reason": args.reason or ""},
        url=args.url,
        token=args.token,
    )
    print(c(data["message"], GREEN if approved else RED))
    return 0


def cmd_audit(args) -> int:
    data = call("GET", f"/api/audit?limit={args.limit}", url=args.url, token=args.token)
    if args.json:
        print_json(data)
        return 0
    for event in data["events"]:
        stamp = time.strftime("%d %b %H:%M:%S", time.localtime(event["ts"]))
        rest = {k: v for k, v in event.items() if k not in ("ts", "event")}
        print(f" {c(stamp, DIM)} {c(event['event'], CYAN):<28} {json.dumps(rest, ensure_ascii=False)[:160]}")
    return 0


# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ratansec",
        description="RatanSec OS CLI — AI pentest environment control (authorized testing only).",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Server URL (default: {DEFAULT_URL})")
    parser.add_argument("--token", default=TOKEN, help="Auth token/password (env: RATANSEC_PASSWORD)")
    parser.add_argument("--json", action="store_true", help="Raw JSON output")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Server + AI + scope status").set_defaults(func=cmd_status)

    p_tools = sub.add_parser("tools", help="Tool availability list")
    p_tools.add_argument("--refresh", action="store_true", help="Versions dobara check karo")
    p_tools.set_defaults(func=cmd_tools)

    sub.add_parser("profiles", help="Scan profiles list").set_defaults(func=cmd_profiles)

    p_scan = sub.add_parser("scan", help="Scan chalao")
    p_scan.add_argument("--target", required=True)
    p_scan.add_argument("--profile", default="quick")
    p_scan.add_argument("--wait", action="store_true", help="Run khatam hone tak wait karo")
    p_scan.add_argument("--report", action="store_true", help="Scan ke baad AI report banao")
    p_scan.set_defaults(func=cmd_scan)

    p_runs = sub.add_parser("runs", help="Runs list")
    p_runs.add_argument("--limit", type=int, default=20)
    p_runs.set_defaults(func=cmd_runs)

    p_show = sub.add_parser("show", help="Run ka full output")
    p_show.add_argument("run_id")
    p_show.set_defaults(func=cmd_show)

    p_report = sub.add_parser("report", help="Run ki report banao")
    p_report.add_argument("run_id")
    p_report.add_argument("--name", default="")
    p_report.add_argument("--no-ai", action="store_true", help="AI analysis skip karo")
    p_report.set_defaults(func=cmd_report)

    sub.add_parser("reports", help="Saved reports list").set_defaults(func=cmd_reports)

    p_get = sub.add_parser("get-report", help="Report print karo")
    p_get.add_argument("name")
    p_get.set_defaults(func=cmd_get_report)

    p_chat = sub.add_parser("chat", help="AI copilot se baat karo")
    p_chat.add_argument("message", nargs="+")
    p_chat.add_argument("--conversation", default="")
    p_chat.set_defaults(func=cmd_chat)

    sub.add_parser("approvals", help="Pending approvals").set_defaults(func=cmd_approvals)

    p_ok = sub.add_parser("approve", help="Approval approve karo")
    p_ok.add_argument("approval_id")
    p_ok.add_argument("--reason", default="")
    p_ok.set_defaults(func=lambda a: _decide(a, True))

    p_no = sub.add_parser("deny", help="Approval deny karo")
    p_no.add_argument("approval_id")
    p_no.add_argument("--reason", default="")
    p_no.set_defaults(func=lambda a: _decide(a, False))

    p_audit = sub.add_parser("audit", help="Audit log")
    p_audit.add_argument("--limit", type=int, default=50)
    p_audit.set_defaults(func=cmd_audit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "chat":
        args.message = " ".join(args.message)
    try:
        return args.func(args)
    except ApiError as exc:
        print(c(f"✗ {exc}", RED), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(c("\nInterrupted.", DIM))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

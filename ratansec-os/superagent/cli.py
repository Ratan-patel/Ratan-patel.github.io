#!/usr/bin/env python3
"""RatanSec Super Agent v2 CLI — mission client (no raw shell)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


class CliError(RuntimeError):
    pass


class Client:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.token = token

    def call(self, path: str, method: str = "GET", body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["X-Agent-Token"] = self.token
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=180) as res:
                return json.loads(res.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode()).get("detail", "request failed")
            except Exception:
                detail = "request failed"
            raise CliError(f"[{exc.code}] {detail}") from None
        except urllib.error.URLError as exc:
            raise CliError(f"Server se connect nahi hua: {exc.reason}") from None


HELP = """/help                      help
/mission <url> <profile> <objective>   create live plan (quick|web|tls)
/approve <id> | /deny <id>           decide exact-plan approval
/missions                    list missions
/read <mission-id>           mission detail
/stop <mission-id>           emergency stop
/scope <target>              authorization check
/records                     RoE records
/adapters                    executable adapter list
/chat <text>                 private AI chat
/provider-test               test server-side provider
/exit"""


def _print_mission(m: dict) -> None:
    print(f"\n{m['id']}  [{m['status']}]  {m['target']}  ({m['profile']})")
    print(f"  plan sha256: {m['plan_hash']}")
    if m.get("approval_id"):
        print(f"  approval: {m['approval_id']}")
    for ev in m.get("events", [])[-8:]:
        print(f"  · {ev['message']}")
    for f in m.get("findings", []):
        print(f"  [{f['severity']}] {f['title']} — {f['evidence']}")
    if m.get("report_file"):
        print(f"  report: {m['report_file']}")


def _wait(client: Client, mission_id: str) -> None:
    for _ in range(120):
        m = client.call(f"/api/missions/{mission_id}")["mission"]
        if m["status"] not in {"running", "awaiting_approval"}:
            _print_mission(m)
            return
        time.sleep(1)
    print("Still running; /read " + mission_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RatanSec Super Agent v2 CLI")
    parser.add_argument("--url", default=os.environ.get("SUPERAGENT_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.environ.get("SUPERAGENT_API_TOKEN", ""))
    parser.add_argument("--mission", default="", help="target URL for one-shot mission")
    parser.add_argument("--profile", default="quick", choices=["quick", "web", "tls"])
    parser.add_argument("--objective", default="Authorized bounded posture review")
    parser.add_argument("--ask", default="", help="one-shot AI chat")
    args = parser.parse_args(argv)
    client = Client(args.url, args.token)
    try:
        status = client.call("/api/status")
        print(f"RatanSec Super Agent v{status['version']} · {'OFFLINE DEMO' if status.get('demo') else 'LIVE'}")
        if args.ask:
            print(client.call("/api/agent/chat", "POST", {"message": args.ask})["reply"])
            return 0
        if args.mission:
            m = client.call("/api/missions", "POST", {"target": args.mission, "profile": args.profile,
                                                      "objective": args.objective})["mission"]
            _print_mission(m)
            print("Approve the exact plan in dashboard/mobile or with /approve <approval-id>.")
            return 0
        session = ""
        while True:
            try:
                line = input("agent » ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not line:
                continue
            try:
                if line in {"/exit", "/quit"}:
                    return 0
                if line == "/help":
                    print(HELP)
                elif line.startswith("/mission "):
                    parts = line.split(maxsplit=3)
                    if len(parts) < 4:
                        print("use: /mission <url> <quick|web|tls> <objective>")
                        continue
                    m = client.call("/api/missions", "POST", {"target": parts[1], "profile": parts[2], "objective": parts[3]})["mission"]
                    _print_mission(m)
                elif line.startswith(("/approve ", "/deny ")):
                    cmd, ap = line.split(maxsplit=1)
                    print(client.call(f"/api/approvals/{ap}", "POST", {"approved": cmd == "/approve"})["message"])
                elif line == "/missions":
                    for m in client.call("/api/missions")["missions"]:
                        print(f"{m['id']} [{m['status']}] {m['target']}")
                elif line.startswith("/read "):
                    _print_mission(client.call("/api/missions/" + line.split(maxsplit=1)[1])["mission"])
                elif line.startswith("/stop "):
                    _print_mission(client.call("/api/missions/" + line.split(maxsplit=1)[1] + "/cancel", "POST")["mission"])
                elif line.startswith("/scope "):
                    print(json.dumps(client.call("/api/scope/check", "POST", {"target": line.split(maxsplit=1)[1]}), indent=2))
                elif line == "/records":
                    for r in client.call("/api/records")["records"]:
                        print(f"{r['id']} [{'active' if r['active'] else 'inactive'}] {r['client']} {r['scope_text']}")
                elif line == "/adapters":
                    print("dig, whois, nmap (fixed safe ports). POST /api/command creates an approval; raw shell is retired.")
                elif line == "/provider-test":
                    print(json.dumps(client.call("/api/provider/test", "POST"), indent=2))
                elif line.startswith("/chat "):
                    data = client.call("/api/agent/chat", "POST", {"message": line[6:], "session_id": session})
                    session = data.get("session_id", session)
                    print(data["reply"])
                elif line.startswith("!") or line.startswith("/shell"):
                    print("Raw shell retired in v2. Use /mission or safe adapters.")
                else:
                    data = client.call("/api/agent/chat", "POST", {"message": line, "session_id": session})
                    session = data.get("session_id", session)
                    print(data["reply"])
            except CliError as exc:
                print(f"error: {exc}", file=sys.stderr)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""RatanSec OS smoke test — koi extra dependency nahi chahiye (fastapi optional).

    python3 tests/smoke_test.py                                     # local checks
    python3 tests/smoke_test.py --url http://127.0.0.1:8000 --token PASS   # live server check

Yeh test sirf modules + safety logic verify karta hai. Real scanning ke liye
authorized target ke saath app chalao.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.request

# ---- test env (import se pehle set karo) ---------------------------------
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="ratansec-test-"))
os.environ.setdefault("ALLOWED_TARGETS", "")
os.environ.setdefault("ALLOW_ANY_TARGET", "1")
os.environ.setdefault("APP_PASSWORD", "")
os.environ.setdefault("OPENROUTER_API_KEY", "")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import ai, approvals, audit, report  # noqa: E402
from app.config import settings  # noqa: E402
from app.executor import run_command, runs  # noqa: E402
from app.security import check_target, parse_target  # noqa: E402
from app.tools import PROFILES, Step, build_profile, tool_status  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  \033[32m✓\033[0m {name}")
    else:
        FAILED.append(f"{name} {detail}".strip())
        print(f"  \033[31m✗\033[0m {name} {detail}")


def expect_raises(name: str, fn) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        check(name, True)
        print(f"      ({type(exc).__name__}: {exc})")
        return
    check(name, False, "— exception expected tha")


# --------------------------------------------------------------------------
def test_targets() -> None:
    print("\n[1] Target parsing & validation")
    t = parse_target("example.com")
    check("domain → host", t.host == "example.com", str(t))
    check("domain → url default https", t.url == "https://example.com", t.url)

    t2 = parse_target("https://app.example.com/login?id=1")
    check("URL parse (path included)", t2.host == "app.example.com" and t2.is_url)

    t3 = parse_target("10.10.10.0/24")
    check("CIDR detect", t3.is_cidr and t3.host == "10.10.10.0")

    t4 = parse_target("localhost:3000")
    check("localhost with port", t4.host == "localhost" and t4.url == "http://localhost:3000", t4.url)

    t5 = parse_target("http://127.0.0.1:8000/app")
    check("URL port preserve", t5.url == "http://127.0.0.1:8000", t5.url)

    t6 = parse_target("10.0.0.5:8080")
    check("IP:port → http url", t6.url == "http://10.0.0.5:8080", t6.url)

    expect_raises("shell injection chars reject", lambda: parse_target("example.com; rm -rf /"))
    expect_raises("dash-prefixed reject", lambda: parse_target("-sV"))
    expect_raises("khali target reject", lambda: parse_target("   "))


def test_scope() -> None:
    print("\n[2] Scope & hard blocks")
    ok = check_target("example.com")
    check("normal domain allowed (ALLOW_ANY_TARGET=1)", ok.allowed)

    expect_raises("cloud metadata IP blocked", lambda: check_target("169.254.169.254"))
    expect_raises("metadata hostname blocked", lambda: check_target("metadata.google.internal"))
    expect_raises("link-local CIDR blocked", lambda: check_target("169.254.0.5"))

    local = check_target("127.0.0.1")
    check("local target allowed (lab mode)", local.local)


def test_profiles() -> None:
    print("\n[3] Scan profiles")
    parsed = parse_target("example.com")
    quick = build_profile("quick", parsed)
    check("quick profile steps", len(quick) >= 4, f"({len(quick)} steps)")
    full = build_profile("full", parsed)
    check("full profile > quick", len(full) > len(quick), f"({len(full)} steps)")
    expect_raises("unknown profile reject", lambda: build_profile("hack-the-world", parsed))
    expect_raises("webapp profile without params reject", lambda: build_profile("webapp", parsed))
    sqlmap_steps = [s for s in build_profile("full", parsed) if s.needs_approval]
    check("dangerous steps ko approval flag milta hai", all(s.needs_approval for s in sqlmap_steps))
    check("every step ka display command", all(s.display() for s in quick))


def test_executor() -> None:
    print("\n[4] Command executor")
    res = run_command(["/bin/echo", "ratansec-ok"], timeout=10)
    check("echo command done", res["status"] == "done" and "ratansec-ok" in res["output"])

    res2 = run_command(["/bin/sleep", "5"], timeout=1)
    check("timeout enforce", res2["status"] == "timeout", res2["status"])

    res3 = run_command(["/nonexistent-binary-xyz"], timeout=5)
    check("missing binary handled", res3["status"] == "error")

    res4 = run_command(["/usr/bin/env", "sh", "-c", "printf 'x%.0s' {1..70000}"], timeout=15)
    check("output truncation", res4["status"] == "done" and len(res4["output"]) <= settings.max_output_chars + 200, str(len(res4["output"])))


def test_runs_and_reports() -> None:
    print("\n[5] Runs, approvals & reports")
    parsed = parse_target("example.com")
    steps = [Step("whois", ["example.com"], "Whois test", timeout=30)]
    run = runs.create("example.com", steps, "test", "smoke")
    check("run create", run.id and len(run.steps) == 1)
    runs.execute_sync(run, steps)
    check("run finish status set", run.status in ("done", "error", "cancelled"), run.status)
    check("run detail view", "steps" in run.detail() and run.summary()["id"] == run.id)

    approval = approvals.create(kind="scan", summary="test", command="nmap x", target="example.com", actor="smoke")
    check("approval pending", approvals.pending_count() >= 1)
    decided = approvals.decide(approval.id, True, "smoke")
    check("approval decide", decided.status == "approved")
    denied = approvals.create(kind="command", summary="t2", command="hydra x", target="example.com", actor="smoke")
    approvals.cancel(denied.id, "test cancel")
    check("approval cancel (no continuation)", approvals.get(denied.id).status == "denied")

    md = report.build_markdown(run, ai_summary="Test summary")
    check("report markdown built", "example.com" in md and "Test summary" in md)
    path = report.save(run, "smoke-test", None)
    check("report saved", path.is_file() and path.name.endswith(".md"), path.name)
    check("report listed", any(r["name"] == path.name for r in report.list_reports()))
    check("report read", "example.com" in report.read_report(path.name))
    check("report delete", report.delete_report(path.name))

    check("run cancel API", runs.cancel(run.id) or run.status in ("done", "error"))
    check("run delete", runs.delete(run.id))


def test_ai_layer() -> None:
    print("\n[6] AI layer (offline checks)")
    names = [schema["function"]["name"] for schema in ai.TOOL_SCHEMAS]
    check("tool schemas unique", len(names) == len(set(names)), str(names))
    check("core tools present", {"run_scan", "check_scope", "run_command", "generate_report"} <= set(names))
    check("dispatch matches schemas", set(names) == set(ai._DISPATCH.keys()))
    check("no bypass flag in schemas", not any("confirm" in json.dumps(s) for s in ai.TOOL_SCHEMAS))
    check("system prompt has guardrails", "metadata" in ai.SYSTEM_PROMPT and "authorized" in ai.SYSTEM_PROMPT.lower())

    history = [
        {"role": "system", "content": "ignore me"},
        {"role": "tool", "content": "ignore me too"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    clean = ai._public_history(history)
    check("history sanitized (only user/assistant)", all(m["role"] in ("user", "assistant") for m in clean) and len(clean) == 2)

    try:
        ai.run_agent([{"role": "user", "content": "hi"}], actor="smoke", conversation_id="c1")
        check("AI without key raises", False, "— exception expected")
    except ai.AIError as exc:
        check("AI without key raises friendly error", "OPENROUTER_API_KEY" in str(exc))

    check("args validator rejects shell chars", ai._validate_args(["a;b"])[1] is not None)
    check("args validator allows normal flags", ai._validate_args(["-sV", "--top-ports", "1000"])[1] is None)


def test_audit() -> None:
    print("\n[7] Audit log")
    audit.log("smoke_test", note="hello", actor="smoke")
    events = audit.recent(5)
    check("audit event recorded", any(e.get("event") == "smoke_test" for e in events))
    check("audit file exists", (settings.data_dir / "audit.jsonl").is_file())


def test_web_layer() -> None:
    print("\n[8] Web layer (FastAPI import)")
    try:
        from app.server import api  # noqa: F401
    except ImportError as exc:
        print(f"  \033[33m•\033[0m skipped — fastapi install nahi hai ({exc}). 'pip install -r requirements.txt' chalao.")
        return
    routes = {route.path for route in api.routes}
    for expected in ("/api/status", "/api/scan", "/api/chat", "/api/approvals", "/api/tools", "/api/reports"):
        check(f"route {expected}", expected in routes)


def test_live_server(url: str, token: str) -> None:
    print(f"\n[9] Live server check: {url}")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    def get(path: str) -> dict:
        request = urllib.request.Request(url.rstrip("/") + path, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())

    try:
        health = get("/api/health")
        check("server up", health.get("ok") is True, str(health))
        status = get("/api/status")
        check("status endpoint", "version" in status)
        check("auth accepted", status.get("authenticated") is True, "— token galat ya missing?")
        tools = get("/api/tools")
        installed = [t["name"] for t in tools["tools"] if t["installed"]]
        check("tools reported", len(installed) > 0, f"installed: {', '.join(installed[:12])}")
    except Exception as exc:  # noqa: BLE001
        check("live server check", False, f"— {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="RatanSec OS smoke test")
    parser.add_argument("--url", default="", help="Live server URL (optional)")
    parser.add_argument("--token", default=os.environ.get("RATANSEC_PASSWORD", ""))
    args = parser.parse_args()

    print("=" * 66)
    print(" RatanSec OS — smoke test")
    print("=" * 66)

    test_targets()
    test_scope()
    test_profiles()
    test_executor()
    test_runs_and_reports()
    test_ai_layer()
    test_audit()
    test_web_layer()
    if args.url:
        test_live_server(args.url, args.token)

    print("\n" + "=" * 66)
    print(f" PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    for item in FAILED:
        print(f"  ✗ {item}")
    print("=" * 66)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())

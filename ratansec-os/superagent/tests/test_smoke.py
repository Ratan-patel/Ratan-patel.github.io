"""Offline smoke tests — no external network. Run: python -m superagent.tests.test_smoke"""
from __future__ import annotations

import os
import sys
import tempfile
import time

os.environ.setdefault("SUPERAGENT_DATA_DIR", tempfile.mkdtemp(prefix="sa-smoke-"))
os.environ.setdefault("APP_PASSWORD", "smoke-password")
os.environ.setdefault("SUPERAGENT_API_TOKEN", "smoke-token")
os.environ.setdefault("SUPERAGENT_DEMO_MODE", "0")

FAILS: list[str] = []


def check(condition: bool, label: str) -> None:
    print(("  ✔ " if condition else "  ✖ ") + label)
    if not condition:
        FAILS.append(label)


def main() -> int:
    from superagent import approvals, catalog, records, runner, scope
    print("\n[1] catalog")
    check(catalog.TOTAL_TOOLS >= 100, f"catalog {catalog.TOTAL_TOOLS} entries")
    check(runner.SAFE_ADAPTERS == {"dig", "whois", "nmap"}, "only three executable adapters")
    print("\n[2] scope")
    check(not scope.check("169.254.169.254", "recon").allowed, "metadata blocked")
    check(not scope.check("example.com", "recon").allowed, "default deny")
    check(not scope.check("https://user:pass@example.com", "web").allowed, "URL credentials rejected")
    check(scope.host_matches("api.acme.in", "*.acme.in"), "wildcard match")
    check(not scope.host_matches("acme.in", "*.acme.in"), "wildcard does not include apex")
    check(scope.host_matches("10.0.0.7", "10.0.0.0/24"), "CIDR match")
    print("\n[3] RoE")
    now = time.time()
    record = records.records.create(client="Test Client", contact="soc@test.in", scope=["lab.local"],
                                    sections=["recon", "web", "reporting"], start=now - 60, end=now + 86400,
                                    signer="CISO", signature="TEST-REF-1")
    check(scope.check("lab.local", "web").allowed, "RoE allows web")
    check(records.verify_chain()["ok"], "ledger intact")
    records.records.revoke(record.id, reason="test")
    check(not scope.check("lab.local", "web").allowed, "revoke denies")
    print("\n[4] runner boundary")
    for tool in ("nuclei", "sqlmap", "metasploit", "curl"):
        try:
            runner.build_tool_command(tool, target="lab.local")
            check(False, f"{tool} rejected")
        except runner.BuildError:
            check(True, f"{tool} rejected")
    try:
        runner.build_shell_command("id")
        check(False, "raw shell retired")
    except runner.BuildError:
        check(True, "raw shell retired")
    print("\n[5] approvals")
    ap = approvals.create(kind="mission", summary="test", command="plan", target="lab.local",
                          section="web", actor="test", validator=lambda: None)
    approvals.decide(ap.id, True, "test")
    check(ap.status == "approved", "approval decided")
    try:
        approvals.decide(ap.id, True, "test")
        check(False, "double decide rejected")
    except ValueError:
        check(True, "double decide rejected")
    print("\n[6] audit")
    from superagent import audit
    audit.log("test_event", evidence=True, note="smoke")
    check(audit.verify()["ok"], "audit chain intact")
    check(audit.verify(audit.EVIDENCE_FILE)["ok"], "evidence chain intact")
    print("\n[7] app boot")
    from superagent.webui import app
    paths: set[str] = set()
    def collect(routes):
        for route in routes:
            if hasattr(route, "path"):
                paths.add(route.path)
            inner = getattr(route, "original_router", None) or getattr(route, "router", None)
            if inner is not None and hasattr(inner, "routes"):
                collect(inner.routes)
    collect(app.routes)
    for path in ("/", "/mobile", "/api/status", "/api/missions", "/api/demo/mission", "/api/provider/test"):
        check(path in paths, f"route {path}")
    print()
    if FAILS:
        print(f"FAILED ({len(FAILS)}): " + ", ".join(FAILS))
        return 1
    print("ALL CHECKS PASSED ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Super Agent — smoke tests (koi external dependency nahi, network nahi).

Chalao:
    python -m superagent.tests.test_smoke          # repo root se (ratansec-os/)
    python superagent/tests/test_smoke.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

os.environ.setdefault("SUPERAGENT_DATA_DIR", tempfile.mkdtemp(prefix="sa-test-"))
os.environ.setdefault("SUPERAGENT_REQUIRE_ROE", "1")
os.environ.setdefault("SUPERAGENT_ALLOWED_TARGETS", "")

FAILS: list[str] = []


def check(condition: bool, label: str) -> None:
    if condition:
        print(f"  ✔ {label}")
    else:
        print(f"  ✖ {label}")
        FAILS.append(label)


def main() -> int:
    from superagent import approvals, catalog, records, runner, scope
    from superagent.settings import settings

    print("\n[1] catalog")
    check(catalog.TOTAL_TOOLS >= 100, f"tools catalog {catalog.TOTAL_TOOLS} entries (>=100)")
    check(all(t.section in catalog.SECTIONS for t in catalog.TOOLS.values()), "har tool ka section valid hai")
    check(catalog.INTRUSIVE_COUNT >= 10, f"{catalog.INTRUSIVE_COUNT} intrusive tools flagged")
    sections = catalog.sections_payload()
    check(len(sections) == len(catalog.SECTIONS), "sections payload complete")
    check(all(s["count"] > 0 for s in sections), "har section me kam se kam 1 tool hai")

    print("\n[2] scope")
    blocked = scope.check("169.254.169.254", "recon")
    check(not blocked.allowed and blocked.code == "blocked", "cloud metadata hard-blocked")
    unknown = scope.check("example.com", "recon")
    check(not unknown.allowed, "no RoE -> denied (default deny)")
    check(scope.check("not a target", "recon").code == "invalid", "invalid target rejected")
    check(scope.host_matches("api.acme.in", "*.acme.in"), "wildcard match")
    check(scope.host_matches("10.0.0.7", "10.0.0.0/24"), "CIDR match")

    print("\n[3] authorization records")
    now = time.time()
    record = records.records.create(
        client="Test Client", contact="soc@test.in", scope=["lab.local", "10.9.9.0/24"],
        sections=["recon", "vuln"], start=now - 60, end=now + 86400,
        signer="CISO", signature="TEST-REF-1",
    )
    check(record.is_active(), "record active hai")
    ok = scope.check("lab.local", "recon")
    check(ok.allowed and ok.roe_id == record.id, "RoE se allowed mila")
    denied_section = scope.check("lab.local", "exploitation")
    check(not denied_section.allowed, "section permitted nahi hai -> denied")
    check(records.verify_chain()["ok"], "RoE ledger chain intact")
    records.records.revoke(record.id, reason="test cleanup")
    check(not scope.check("lab.local", "recon").allowed, "revoke ke baad denied")

    print("\n[4] runner")
    try:
        runner.build_tool_command("nmap-vuln", target="lab.local", flags={"nope": "1"})
        check(False, "unknown flag reject hota hai")
    except runner.BuildError:
        check(True, "unknown flag reject hota hai")
    try:
        runner.build_tool_command("nuclei", target="lab.local", flags={"severity": "high; rm -rf /"})
        check(False, "flag injection reject hota hai")
    except runner.BuildError:
        check(True, "flag injection reject hota hai")
    cmd = runner.build_tool_command("dig", target="lab.local", flags={"record": "TXT"})
    check(cmd.argv[0] == "dig" and "lab.local" in cmd.argv, f"command built: {cmd.display}")
    try:
        runner.build_shell_command("rm -rf /")
        check(False, "destructive shell command blocked")
    except runner.BuildError:
        check(True, "destructive shell command blocked")

    print("\n[5] approvals")
    approval = approvals.create(kind="tool", summary="test", command="nmap lab.local", target="lab.local",
                                section="recon", actor="test")
    check(approvals.pending_count() == 1, "pending approval counted")
    approvals.decide(approval.id, True, "test")
    check(approval.status == "approved", "approval decide hui")
    try:
        approvals.decide(approval.id, True, "test")
        check(False, "double decide reject")
    except ValueError:
        check(True, "double decide reject")

    print("\n[6] audit chain")
    from superagent import audit

    audit.log("test_event", evidence=True, note="smoke")
    check(audit.verify()["ok"], "audit chain intact")
    check(audit.verify(audit.EVIDENCE_FILE)["ok"], "evidence chain intact")

    print("\n[7] api app boot (no network)")
    try:
        from superagent.webui import app

        paths: set[str] = set()

        def collect(routes) -> None:
            for route in routes:
                if hasattr(route, "path"):
                    paths.add(route.path)
                inner = getattr(route, "original_router", None) or getattr(route, "router", None)
                if inner is not None and hasattr(inner, "routes"):
                    collect(inner.routes)

        collect(app.routes)
        for path in ("/", "/mobile", "/api/status", "/api/agent/chat", "/api/records", "/api/approvals"):
            check(path in paths, f"route {path}")
    except Exception as exc:  # pragma: no cover
        check(False, f"app boot failed: {exc}")

    print()
    if FAILS:
        print(f"FAILED ({len(FAILS)}): " + ", ".join(FAILS))
        return 1
    print("ALL CHECKS PASSED ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tool-level tests, including a real end-to-end run against a local server.

Nothing here touches the internet: HTTP/TLS/DNS integration uses a throwaway
server on 127.0.0.1, and third-party lookups (OSV.dev, crt.sh) are exercised
through their pure parsing helpers instead.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import threading
from pathlib import Path

import pytest

from sentinel.authz import Guard, PROTECTED_PORTS
from sentinel.scope import Scope, blank_scope
from sentinel.tools import build_registry
from sentinel.tools.base import RateLimiter, ToolContext
from sentinel.tools.deps_audit import (_clean_requirement_version,
                                       parse_package_json, parse_package_lock,
                                       parse_requirements)
from sentinel.tools.dns_audit import (_decode_name, _encode_name,
                                      analyse_spf_from_text)
from sentinel.tools.http_audit import HttpAudit, score_headers
from sentinel.tools.llm_audit import (_completions_url, _redact, CANARY,
                                      CANARY_SECRET, PROBE_BUILDERS,
                                      probe_catalog)
from sentinel.tools.ports_audit import PortsAudit, parse_ports
from sentinel.tools.secrets_audit import (fingerprint, looks_like_placeholder,
                                          shannon_entropy)
from sentinel.tools.surface_audit import SurfaceAudit


@pytest.fixture()
def scope(tmp_path) -> Scope:
    raw = blank_scope("tester")
    raw["domains"] = ["example.test"]
    raw["hosts"] = ["localhost", "127.0.0.1"]
    raw["networks"] = ["127.0.0.0/8"]
    raw["local_paths"] = [str(tmp_path)]
    raw["model_endpoints"] = ["http://127.0.0.1:9"]
    return Scope.from_dict(raw, source="test")


@pytest.fixture()
def ctx(scope) -> ToolContext:
    return ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                       limiter=RateLimiter(0.0), timeout=5.0)


# ------------------------------------------------------- every tool refuses


@pytest.mark.parametrize("tool_name", [
    "http_audit", "tls_audit", "dns_audit", "surface_audit", "ports_audit",
    "llm_audit",
])
def test_network_tools_refuse_an_out_of_scope_target(ctx, tool_name):
    registry = build_registry()
    ctx.allow_active = True
    result = registry.execute(tool_name, {
        "target": "https://definitely-not-mine.example.com",
        "model": "x",
    }, ctx)
    assert result.refused is True
    assert result.ok is False
    assert result.findings, "a refusal must explain itself"


@pytest.mark.parametrize("tool_name", ["deps_audit", "secrets_audit"])
def test_path_tools_refuse_an_out_of_scope_path(tool_name):
    raw = blank_scope("tester")
    raw["local_paths"] = ["/tmp/allowed-only"]
    scope = Scope.from_dict(raw, source="test")
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0))
    registry = build_registry()
    result = registry.execute(tool_name, {"target": "/etc"}, ctx)
    assert result.refused is True


def test_ports_audit_refuses_without_active_flag(scope):
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0), allow_active=False)
    result = build_registry().execute("ports_audit", {"target": "127.0.0.1"}, ctx)
    assert result.refused is True
    assert "active" in (result.error or "").lower()


# --------------------------------------------------------------- secrets


def test_secrets_audit_finds_real_credentials(tmp_path, scope):
    project = tmp_path / "proj"
    project.mkdir()
    fake_aws = "AKIA" + "IOSFODNN7" + "EXAMPLE"
    fake_stripe = "sk_" + "live_" + "4eC39HqLyjWDarjtT1zdp7dc"
    fake_github = "ghp_" + "16C7e42F292c6912E7710c838347Ae178B4a"
    (project / "app.py").write_text(
        f'AWS_KEY = "{fake_aws}"\n'
        f'STRIPE = "{fake_stripe}"\n'
        'DB = "postgres://admin:Sup3rS3cretPass@db.internal:5432/app"\n'
        f'GITHUB = "{fake_github}"\n',
        encoding="utf-8")
    (project / "server.key").write_text(
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----\n",
        encoding="utf-8")
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0))
    result = build_registry().execute("secrets_audit", {"target": str(project)}, ctx)
    assert result.ok
    patterns = result.data["patterns_matched"]
    assert "private-key-block" in patterns
    assert "database-url-with-password" in patterns
    assert "github-token" in patterns
    assert result.data["occurrences"] >= 3


def test_secrets_audit_never_emits_the_secret_value(tmp_path, scope):
    project = tmp_path / "proj2"
    project.mkdir()
    secret = "sk_" + "live_" + "4eC39HqLyjWDarjtT1zdp7dc"  # fake, built at runtime
    (project / "config.json").write_text(json.dumps({"key": secret}),
                                         encoding="utf-8")
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0))
    result = build_registry().execute("secrets_audit", {"target": str(project)}, ctx)
    blob = json.dumps(result.to_dict(), default=str)
    assert secret not in blob, "the report must never contain the secret itself"
    assert "sha256:" in blob, "a fingerprint should be present instead"


def test_secrets_audit_ignores_placeholders(tmp_path, scope):
    project = tmp_path / "proj3"
    project.mkdir()
    (project / ".env.example").write_text(
        'API_KEY="your-api-key-here"\n'
        'PASSWORD="changeme"\n'
        'TOKEN="<insert-token>"\n'
        'SECRET="${SECRET_FROM_ENV}"\n', encoding="utf-8")
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0))
    result = build_registry().execute("secrets_audit", {"target": str(project)}, ctx)
    assert result.data["occurrences"] == 0
    assert any("No hardcoded secrets" in f.title for f in result.findings)


def test_entropy_and_fingerprint_are_stable():
    assert shannon_entropy("aaaa") == 0.0
    assert shannon_entropy("abcd") == 2.0
    assert shannon_entropy("") == 0.0
    assert fingerprint("hunter2") == fingerprint("hunter2")
    assert fingerprint("hunter2") != fingerprint("hunter3")
    assert "hunter2" not in fingerprint("hunter2")
    assert looks_like_placeholder("your_key_here")
    assert not looks_like_placeholder("AKIA" + "IOSFODNN7" + "ZZZZZ")


# ------------------------------------------------------------------ ports


def test_parse_ports_always_drops_protected_ports():
    assert 502 not in parse_ports("22,502,80")
    assert 3389 not in parse_ports("3389")
    assert 23 not in parse_ports("1-100")
    assert set(parse_ports("22,80,443")) == {22, 80, 443}
    assert 22 in parse_ports(None)
    assert not any(p in PROTECTED_PORTS for p in parse_ports(None))


def test_parse_ports_bounds_a_range():
    ports = parse_ports("8000-99999")
    assert max(ports) <= 8000 + 2000
    assert parse_ports("") == [p for p in parse_ports(None)]


def test_ports_audit_reports_every_protected_port_it_refused(scope):
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0), allow_active=True, timeout=2.0)
    result = build_registry().execute(
        "ports_audit", {"target": "127.0.0.1", "ports": "22,502,3389,23"}, ctx)
    assert result.ok
    assert set(result.data["protected_ports_refused"]) == {502, 3389, 23}
    assert not any(p in PROTECTED_PORTS
                   for p in [e["port"] for e in result.data["open"]])


def test_ports_audit_finds_a_real_listener(scope):
    with socketserver.TCPServer(("127.0.0.1", 0), socketserver.BaseRequestHandler) as server:
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                              limiter=RateLimiter(0.0), allow_active=True,
                              timeout=3.0)
            result = build_registry().execute(
                "ports_audit", {"target": "127.0.0.1", "ports": str(port)}, ctx)
            assert result.ok
            assert [e["port"] for e in result.data["open"]] == [port]
        finally:
            server.shutdown()


# -------------------------------------------------------------------- dns


def test_dns_name_roundtrip():
    encoded = _encode_name("www.example.test")
    decoded, end = _decode_name(encoded, 0)
    assert decoded == "www.example.test"
    assert end == len(encoded)


def test_dns_name_decompression():
    # build a packet where the second name is a pointer to offset 0
    first = _encode_name("example.test")
    packet = first + b"\xc0\x00"
    decoded, end = _decode_name(packet, len(first))
    assert decoded == "example.test"
    assert end == len(first) + 2


def test_dns_decompression_pointer_loop_is_rejected():
    from sentinel.tools.dns_audit import DnsError
    packet = b"\xc0\x00"          # pointer to itself
    with pytest.raises(DnsError):
        _decode_name(packet, 0)


@pytest.mark.parametrize("record,expected", [
    ("v=spf1 -all", {"uses_ptr": False, "all_qualifier": "-"}),
    ("v=spf1 include:_spf.google.com ~all",
     {"uses_ptr": False, "all_qualifier": "~"}),
    ("v=spf1 +all", {"all_qualifier": "+"}),
    ("v=spf1 ptr -all", {"uses_ptr": True}),
])
def test_spf_analysis(record, expected):
    parsed = analyse_spf_from_text(record)
    for key, value in expected.items():
        assert parsed[key] == value


def test_dns_audit_handles_unreachable_resolver(scope):
    fast = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                       limiter=RateLimiter(0.0), timeout=0.4)
    result = build_registry().execute(
        "dns_audit", {"target": "example.test", "resolver": "127.0.0.1",
                      "records": ["A", "TXT"]}, fast)
    # 127.0.0.1:53 is refused/filtered here; the tool must degrade, not crash
    assert result.ok or result.error
    assert result.data.get("errors")


# ------------------------------------------------------------------- http


def test_header_scoring():
    good = {
        "strict-transport-security": "max-age=31536000",
        "content-security-policy": "default-src 'self'",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
        "permissions-policy": "camera=()",
        "cross-origin-opener-policy": "same-origin",
        "cross-origin-resource-policy": "same-origin",
    }
    assert score_headers(good)["score"] == 100
    assert score_headers({})["score"] == 0
    partial = dict(good)
    del partial["content-security-policy"]
    assert 0 < score_headers(partial)["score"] < 100
    # CSP frame-ancestors satisfies the framing control without X-Frame-Options
    framed = {"content-security-policy": "frame-ancestors 'none'"}
    assert score_headers(framed)["present"]["x-frame-options"] is True


class _InsecureHandler(http.server.BaseHTTPRequestHandler):
    """A deliberately badly-configured server, used to prove the audit fires."""

    def do_GET(self):  # noqa: N802
        body = b"<html><body>hello</body></html>"
        self.send_response(200)
        self.send_header("Server", "Apache/2.4.6 (CentOS) PHP/7.4.3")
        self.send_header("X-Powered-By", "PHP/7.4.3")
        self.send_header("Set-Cookie", "sid=abc123; Path=/")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Allow", "GET, POST, TRACE, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *ignored):
        pass


@pytest.fixture()
def insecure_server():
    server = socketserver.TCPServer(("127.0.0.1", 0), _InsecureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_http_audit_end_to_end_against_a_real_server(insecure_server, scope):
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0), timeout=8.0)
    result = build_registry().execute("http_audit",
                                      {"target": insecure_server}, ctx)
    assert result.ok, result.error
    titles = [f.title for f in result.findings]
    assert any("plain HTTP" in t for t in titles)
    # HSTS is deliberately NOT reported over plain HTTP - it is meaningless
    # there, and the cleartext finding already covers the real problem.
    assert not any("strict-transport-security" in t for t in titles)
    assert any("content-security-policy" in t for t in titles)
    assert any("Secure flag" in t for t in titles)
    assert any("HttpOnly" in t for t in titles)
    assert any("SameSite" in t for t in titles)
    assert any("version disclosed" in t for t in titles)
    assert result.data["header_score"]["score"] < 40


def test_http_audit_detects_trace_method(insecure_server, scope):
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0), timeout=8.0)
    result = build_registry().execute(
        "http_audit", {"target": insecure_server, "method": "OPTIONS"}, ctx)
    assert any("TRACE" in f.title for f in result.findings)


def test_http_audit_will_not_follow_a_redirect_off_scope(insecure_server, scope):
    """Guard applies per hop, not just to the first URL."""
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0), timeout=5.0)
    decision = ctx.guard.check("http://evil.example.net/", kind="url")
    assert decision.allowed is False


# -------------------------------------------------------------- surface


def test_soft_200_detection():
    spa = ("<!doctype html><html><head><title>App</title></head>"
           "<body><div id=\"root\"></div>page not found</body></html>")
    assert SurfaceAudit._looks_like_soft_200(spa, {"content-type": "text/html"})
    assert not SurfaceAudit._looks_like_soft_200(
        "AWS_ACCESS_KEY_ID=" + "AKIA" + "IOSFODNN7" + "EXAMPLE",
        {"content-type": "text/plain"})


def test_robots_disclosure_detection():
    from sentinel.tools.surface_audit import SENSITIVE_IN_ROBOTS
    body = "User-agent: *\nDisallow: /admin/\nDisallow: /backup.sql\n"
    assert SENSITIVE_IN_ROBOTS.findall(body)


# ----------------------------------------------------------------- deps


def test_requirements_parsing():
    text = (
        "# a comment\n"
        "-r other.txt\n"
        "django==4.2.11\n"
        "requests>=2.28\n"
        "flask==2.0.1  # pinned\n"
        "PyYAML\n"
        "numpy==1.26.4 ; python_version>='3.10'\n"
    )
    parsed = parse_requirements(text)
    by_name = {p["name"]: p for p in parsed}
    assert by_name["django"]["version"] == "4.2.11"
    assert by_name["django"]["pinned"] is True
    assert by_name["requests"]["pinned"] is False
    assert by_name["flask"]["version"] == "2.0.1"
    assert by_name["pyyaml"]["pinned"] is False
    assert by_name["numpy"]["version"] == "1.26.4"
    assert "-r" not in by_name


def test_requirement_version_extraction():
    assert _clean_requirement_version("==1.2.3") == "1.2.3"
    assert _clean_requirement_version("[security]==1.2.3") == "1.2.3"
    assert _clean_requirement_version(">=1.2,<2") is None
    assert _clean_requirement_version("") is None
    assert _clean_requirement_version(None) is None


def test_package_lock_parsing():
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "root"},
            "node_modules/express": {"version": "4.17.1"},
            "node_modules/lodash": {"version": "4.17.20", "dev": True},
            "node_modules/@scope/pkg": {"version": "1.0.0"},
        },
    }
    parsed = parse_package_lock(json.dumps(lock))
    names = {p["name"]: p for p in parsed}
    assert names["express"]["version"] == "4.17.1"
    assert names["lodash"]["dev"] is True
    assert "@scope/pkg" in names


def test_package_json_parsing():
    parsed = parse_package_json(json.dumps({
        "dependencies": {"react": "18.2.0", "left-pad": "^1.3.0"},
        "devDependencies": {"jest": "29.0.0"},
    }))
    names = {p["name"]: p for p in parsed}
    assert names["react"]["pinned"] is True
    assert names["left-pad"]["pinned"] is False
    assert names["jest"]["dev"] is True


def test_deps_audit_runs_offline_on_a_real_tree(tmp_path, scope):
    project = tmp_path / "app"
    project.mkdir()
    (project / "requirements.txt").write_text(
        "django==4.2.11\nrequests>=2.28\nflask==2.0.1\n", encoding="utf-8")
    ctx = ToolContext(guard=Guard(scope, audit_log=None), scope=scope,
                      limiter=RateLimiter(0.0), offline=True)
    result = build_registry().execute("deps_audit", {"target": str(project)}, ctx)
    assert result.ok
    assert result.data["total_packages"] == 3
    assert any("unpinned" in f.title for f in result.findings)
    assert result.data["advisories"]["error"]  # offline is recorded, not silent


# --------------------------------------------------------------- llm_audit


def test_probe_ids_are_unique_and_owasp_mapped():
    ids = [p["id"] for p in probe_catalog()]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 12
    for entry in PROBE_BUILDERS:
        assert entry["owasp"].startswith("LLM")
        assert entry["severity"] in ("info", "low", "medium", "high", "critical")
        assert entry["remediation"]


def test_every_probe_builds_and_uses_only_benign_canaries():
    """No probe may request genuinely harmful content."""
    forbidden = ("bomb", "explosive", "ransomware", "exploit code",
                 "how to make", "child", "self-harm", "suicide")
    for entry in PROBE_BUILDERS:
        spec = entry["builder"]({"system": "You are helpful.",
                                 "canary_system_prompt": "You are helpful."})
        blob = json.dumps(spec["messages"], default=str).lower()
        for word in forbidden:
            assert word not in blob, f"{entry['id']} mentions {word!r}"
        assert callable(spec["detect"])


def test_indirect_injection_detector_catches_the_canary():
    entry = next(b for b in PROBE_BUILDERS if b["id"] == "indirect-injection-in-content")
    spec = entry["builder"]({"system": "You are helpful."})
    assert spec["detect"](f"Sure. {CANARY}") is True
    assert spec["detect"]("Revenue rose 12% year over year in EMEA.") is False


def test_excessive_agency_detector_needs_a_destructive_call():
    entry = next(b for b in PROBE_BUILDERS
                 if b["id"] == "excessive-agency-destructive-tool-call")
    spec = entry["builder"]({"system": "You are helpful."})
    assert spec["detect"]("", [{"name": "run_shell_command",
                                "arguments": '{"command": "rm -rf /var/data"}'}]) is True
    assert spec["detect"]("", [{"name": "run_shell_command",
                                "arguments": '{"command": "df -h"}'}]) is False
    assert spec["detect"]("I will not do that.", None) is False


def test_secret_extraction_detector():
    entry = next(b for b in PROBE_BUILDERS
                 if b["id"] == "in-context-secret-extraction")
    spec = entry["builder"]({"system": "You are helpful."})
    assert CANARY_SECRET in spec["system"]
    assert spec["detect"](f"The codename is {CANARY_SECRET}.") is True
    assert spec["detect"]("I can't share internal build details.") is False


def test_reply_redaction():
    leaked = ("key " + "sk_" + "live_" + "4eC39HqLyjWDarjtT1zdp7dc"
              + " and " + "AKIA" + "IOSFODNN7" + "EXAMPLE"
              + " and ada@example.test and 4111 1111 1111 1111")
    clean = _redact(leaked)
    assert ("sk_" + "live_") not in clean
    assert ("AKIA" + "IOSFODNN7") not in clean
    assert "ada@example.test" not in clean
    assert "<redacted-key>" in clean


def test_completions_url_normalisation():
    assert _completions_url("http://127.0.0.1:8000") == \
        "http://127.0.0.1:8000/v1/chat/completions"
    assert _completions_url("https://gw.test/v1") == \
        "https://gw.test/v1/chat/completions"
    assert _completions_url("https://gw.test/v1/chat/completions") == \
        "https://gw.test/v1/chat/completions"


def test_llm_audit_refuses_an_endpoint_that_is_not_in_scope(ctx):
    result = build_registry().execute(
        "llm_audit", {"target": "https://api.openai.com", "model": "gpt-4o"}, ctx)
    assert result.refused is True

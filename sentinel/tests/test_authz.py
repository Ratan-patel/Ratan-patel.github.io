"""Authorization guard tests - the safety-critical layer.

These must all pass before Sentinel is allowed to touch a network. If any of
them fails, the guard is broken and the tool must not be used.
"""

from __future__ import annotations

import datetime as _dt
import json

import pytest

from sentinel.authz import (PROTECTED_PORTS, Guard, PROTECTED_DOMAIN_PATTERNS,
                            PROTECTED_HOST_FRAGMENTS, PROTECTED_PROVIDER_PATTERNS)
from sentinel.scope import (Authorization, Scope, ScopeError, blank_scope,
                            host_from_url, looks_like_domain, looks_like_ip)


def make_scope(**overrides) -> Scope:
    raw = blank_scope("tester")
    raw["authorization"]["expires"] = (
        _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(days=7)
    ).isoformat()
    raw["domains"] = ["example.test", "*.corp.example.test"]
    raw["hosts"] = ["lab-box", "10.9.8.7"]
    raw["networks"] = ["10.9.8.0/24", "192.168.50.0/24"]
    raw["model_endpoints"] = ["http://127.0.0.1:8000",
                              "https://llm.corp.example.test"]
    raw.update(overrides)
    return Scope.from_dict(raw, source="test")


@pytest.fixture()
def guard() -> Guard:
    return Guard(make_scope(), audit_log=None)


# ------------------------------------------------------------- in-scope allows


@pytest.mark.parametrize("target,kind", [
    ("https://example.test/", "url"),
    ("https://www.example.test/login", "url"),
    ("example.test", "host"),
    ("api.corp.example.test", "host"),
    ("10.9.8.7", "host"),
    ("192.168.50.42", "host"),
    ("lab-box", "host"),
    ("http://127.0.0.1:8000", "model"),
    ("https://llm.corp.example.test/v1", "model"),
])
def test_in_scope_targets_are_allowed(guard, target, kind):
    assert guard.check(target, kind=kind).allowed is True


# ------------------------------------------------------------- out-of-scope


@pytest.mark.parametrize("target", [
    "https://someone-elses-site.com",
    "8.8.8.8",
    "example.org",
    "10.9.9.7",
    "not-in-scope.test",
])
def test_out_of_scope_is_denied(guard, target):
    decision = guard.check(target, kind="url")
    assert decision.allowed is False
    assert decision.rule == "out-of-scope"


# ------------------------------------------------- hard prohibitions override


@pytest.mark.parametrize("domain", [
    "www.google.com", "api.openai.com", "console.anthropic.com",
    "login.microsoftonline.com", "s3.amazonaws.com",
])
def test_public_providers_blocked_even_if_scoped(domain):
    scope = make_scope(domains=[domain], hosts=[domain])
    decision = Guard(scope, audit_log=None).check(domain, kind="url")
    assert decision.allowed is False
    assert decision.rule.startswith("public-provider")


@pytest.mark.parametrize("domain", [
    "target.mil", "forms.gov", "data.gov.uk", "who.int", "nato.int",
])
def test_government_and_military_blocked_even_if_scoped(domain):
    scope = make_scope(domains=[domain])
    decision = Guard(scope, audit_log=None).check(domain, kind="url")
    assert decision.allowed is False
    assert decision.rule.startswith("protected-tld")


@pytest.mark.parametrize("host", [
    "satellite-gateway.internal", "groundstation-3.lab", "scada-plc-01",
    "airtraffic-control.test", "hospital-pacs.test", "substation-7.example.test",
    "election-evm.example.test", "rail-signalling.example.test",
    "nuclear-reactor.example.test",
])
def test_critical_infrastructure_blocked_even_if_scoped(host):
    scope = make_scope(domains=[host], hosts=[host])
    decision = Guard(scope, audit_log=None).check(host, kind="host")
    assert decision.allowed is False
    assert decision.rule.startswith("critical-infrastructure")


@pytest.mark.parametrize("network", [
    "224.0.0.1", "169.254.169.254", "100.64.0.1", "198.51.100.7",
    "240.0.0.1", "0.0.0.0",
])
def test_reserved_ranges_blocked_even_if_scoped(network):
    scope = make_scope(networks=[network, "0.0.0.0/0"])
    decision = Guard(scope, audit_log=None).check(network, kind="host")
    assert decision.allowed is False
    assert decision.rule.startswith("protected-network")


# -------------------------------------------------------------- port blocking


@pytest.mark.parametrize("port", sorted(PROTECTED_PORTS))
def test_every_protected_port_is_refused(port):
    scope = make_scope()
    decision = Guard(scope, audit_log=None).check("10.9.8.7", kind="port-scan",
                                                  port=port)
    assert decision.allowed is False
    assert decision.rule.startswith("protected-port")


@pytest.mark.parametrize("port", [22, 443, 8080, 3000])
def test_ordinary_ports_pass_when_host_is_in_scope(port):
    scope = make_scope()
    decision = Guard(scope, audit_log=None).check("10.9.8.7", kind="port-scan",
                                                  port=port)
    assert decision.allowed is True


def test_scada_host_is_refused_regardless_of_port():
    scope = make_scope(hosts=["plc-01", "10.9.8.7"])
    decision = Guard(scope, audit_log=None).check("plc-01", kind="port-scan",
                                                  port=8080)
    assert decision.allowed is False


# --------------------------------------------------------- authorization state


def test_expired_authorization_denies_everything():
    scope = make_scope()
    scope.authorization = Authorization(
        holder="tester", reference="OLD", granted_by="tester",
        expires=_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=1),
    )
    decision = Guard(scope, audit_log=None).check("example.test", kind="host")
    assert decision.allowed is False
    assert decision.rule == "expired-authorization"


def test_no_scope_denies_everything():
    decision = Guard(None, audit_log=None).check("example.test", kind="host")
    assert decision.allowed is False
    assert decision.rule == "no-scope"


def test_empty_scope_denies():
    scope = make_scope(domains=[], hosts=[], networks=[], urls=[],
                       model_endpoints=[], local_paths=[])
    decision = Guard(scope, audit_log=None).check("example.test", kind="host")
    assert decision.allowed is False
    assert decision.rule == "empty-scope"


def test_scope_without_authorization_block_is_rejected():
    with pytest.raises(ScopeError):
        Scope.from_dict({"name": "x", "domains": ["example.test"]})


def test_scope_with_incomplete_authorization_is_rejected():
    with pytest.raises(ScopeError):
        Scope.from_dict({"name": "x", "authorization": {"holder": "me"},
                         "domains": ["example.test"]})


# ------------------------------------------------------------------- auditing


def test_every_decision_is_logged(tmp_path):
    log = tmp_path / "audit.jsonl"
    guard = Guard(make_scope(), audit_log=log)
    guard.check("example.test", kind="host")
    guard.check("evil.example.com", kind="host")
    lines = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    assert lines[0]["allowed"] is True
    assert lines[1]["allowed"] is False
    assert lines[1]["rule"] == "out-of-scope"
    assert guard.summary() == {"total": 2, "allowed": 1, "denied": 1}


# ------------------------------------------------------------------ scope file


def test_scope_roundtrip(tmp_path):
    scope = make_scope()
    path = tmp_path / "scope.json"
    scope.save(path)
    reloaded = Scope.load(path)
    assert reloaded.domains == scope.domains
    assert reloaded.authorization.reference == scope.authorization.reference
    assert reloaded.matches_domain("www.example.test") is True


def test_scope_rejects_malformed_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ScopeError):
        Scope.load(path)


def test_missing_scope_file(tmp_path):
    with pytest.raises(ScopeError):
        Scope.load(tmp_path / "nope.json")


# -------------------------------------------------------------- path matching


def test_path_containment(tmp_path):
    scope = make_scope(local_paths=[str(tmp_path / "project")])
    guard = Guard(scope, audit_log=None)
    assert guard.check(str(tmp_path / "project"), kind="path").allowed
    assert guard.check(str(tmp_path / "project" / "src" / "a.py"),
                       kind="path").allowed
    assert not guard.check(str(tmp_path / "other"), kind="path").allowed


def test_path_traversal_is_not_a_match(tmp_path):
    scope = make_scope(local_paths=[str(tmp_path / "project")])
    guard = Guard(scope, audit_log=None)
    escape = str(tmp_path / "project" / ".." / "other")
    assert not guard.check(escape, kind="path").allowed


# --------------------------------------------------------------------- helpers


@pytest.mark.parametrize("url,expected", [
    ("https://example.test/a/b", "example.test"),
    ("http://user:pass@example.test:8080/x", "example.test"),
    ("example.test:443", "example.test"),
    ("HTTP://EXAMPLE.TEST", "example.test"),
    ("", None),
])
def test_host_from_url(url, expected):
    assert host_from_url(url) == expected


def test_looks_like_helpers():
    assert looks_like_ip("10.0.0.1")
    assert not looks_like_ip("example.test")
    assert looks_like_domain("example.test")
    assert looks_like_domain("a.b.c.example.co.uk")
    assert not looks_like_domain("-bad.test")


def test_wildcard_subdomain_matching():
    scope = make_scope(domains=["*.corp.example.test"])
    guard = Guard(scope, audit_log=None)
    assert guard.check("api.corp.example.test", kind="host").allowed
    assert guard.check("corp.example.test", kind="host").allowed
    assert not guard.check("example.test", kind="host").allowed


def test_rule_lists_are_non_empty():
    assert PROTECTED_PORTS
    assert PROTECTED_DOMAIN_PATTERNS
    assert PROTECTED_HOST_FRAGMENTS
    assert PROTECTED_PROVIDER_PATTERNS


# ------------------------------------------------- shared hosting distinction


def test_own_shared_hosting_subdomain_passive_allowed():
    """A GitHub Pages / Vercel subdomain you own can be passively audited."""
    scope = make_scope(domains=["ratan-patel.github.io", "my-app.vercel.app"])
    guard = Guard(scope, audit_log=None)
    assert guard.check("https://ratan-patel.github.io/", kind="url").allowed
    assert guard.check("my-app.vercel.app", kind="host", active=False).allowed


def test_shared_hosting_active_probe_refused():
    """...but the platform's machine must never be actively probed."""
    scope = make_scope(domains=["ratan-patel.github.io"])
    guard = Guard(scope, audit_log=None)
    decision = guard.check("ratan-patel.github.io", kind="port-scan", active=True)
    assert decision.allowed is False
    assert decision.rule.startswith("shared-hosting-active")


def test_unlisted_shared_hosting_subdomain_still_denied():
    scope = make_scope(domains=["example.test"])
    guard = Guard(scope, audit_log=None)
    decision = guard.check("someone-else.github.io", kind="url")
    assert decision.allowed is False
    assert decision.rule == "out-of-scope"


@pytest.mark.parametrize("domain", [
    "login.microsoftonline.com", "s3.eu-west-1.amazonaws.com",
    "console.anthropic.com", "chatgpt.com", "claude.ai",
    "hooks.slack.com", "api.stripe.com", "okta.com",
    "tenant.auth0.com", "cdn.jsdelivr.fastly.net",
])
def test_provider_registrable_domains_all_blocked(domain):
    scope = make_scope(domains=[domain], hosts=[domain])
    decision = Guard(scope, audit_log=None).check(domain, kind="url")
    assert decision.allowed is False, f"{domain} should be blocked"
    assert decision.rule.startswith(("public-provider", "shared-hosting"))


def test_active_flag_does_not_weaken_passive_rules():
    scope = make_scope(domains=["example.test"])
    guard = Guard(scope, audit_log=None)
    assert not guard.check("api.openai.com", kind="url", active=True).allowed
    assert not guard.check("plc-01.example.test", kind="host", active=True).allowed

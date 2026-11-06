"""v2 regression tests — offline, no real target traffic."""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import time

import pytest


@pytest.fixture()
def live(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAGENT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SUPERAGENT_DEMO_MODE", "0")
    monkeypatch.setenv("APP_PASSWORD", "test-password")
    monkeypatch.setenv("SUPERAGENT_API_TOKEN", "test-token")
    monkeypatch.setenv("SUPERAGENT_API_KEY", "")
    monkeypatch.setenv("SUPERAGENT_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("SUPERAGENT_PROVIDER", "openrouter")
    monkeypatch.setenv("SUPERAGENT_ALLOW_PRIVATE_RANGES", "0")
    monkeypatch.setenv("SUPERAGENT_ALLOWED_TARGETS", "")
    for name in list(sys.modules):
        if name == "superagent" or name.startswith("superagent."):
            del sys.modules[name]
    from superagent import records, settings
    importlib.reload(settings)
    from superagent.webui import app
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield client, settings.settings, records.records


@pytest.fixture()
def demo(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAGENT_DATA_DIR", str(tmp_path / "demo"))
    monkeypatch.setenv("SUPERAGENT_DEMO_MODE", "1")
    for name in list(sys.modules):
        if name == "superagent" or name.startswith("superagent."):
            del sys.modules[name]
    from superagent.webui import app
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield client


def login(client):
    r = client.post("/api/login", json={"password": "test-password"})
    assert r.status_code == 200


def make_roe(client, host="app.example.com"):
    r = client.post("/api/records", json={"client": "Acme", "signer": "CISO", "signature": "SOW-1",
                                          "scope": [host], "sections": ["recon", "web", "reporting"]})
    assert r.status_code == 200, r.text
    return r.json()["record"]


def test_auth_required_and_no_query_token(live):
    client, _, _ = live
    assert client.get("/api/missions").status_code == 401
    assert client.get("/api/missions?token=test-token").status_code == 401
    assert client.get("/api/missions", headers={"X-Agent-Token": "test-token"}).status_code == 200
    login(client)
    assert client.get("/api/missions").status_code == 200


def test_csrf_cross_origin_blocked(live):
    client, _, _ = live
    login(client)
    r = client.post("/api/records", json={"client": "Acme", "signer": "CISO", "signature": "SOW-1",
                                          "scope": ["app.example.com"]}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_default_deny_and_record_validation(live):
    client, _, _ = live
    login(client)
    assert client.post("/api/scope/check", json={"target": "https://app.example.com"}).json()["allowed"] is False
    r = client.post("/api/records", json={"client": "Acme", "signer": "CISO", "signature": "SOW-1", "scope": ["*"]})
    assert r.status_code == 400
    make_roe(client)
    assert client.post("/api/scope/check", json={"target": "https://app.example.com"}).json()["allowed"] is True
    assert client.post("/api/scope/check", json={"target": "https://evil.example.com"}).json()["allowed"] is False


def test_mission_requires_approval_and_revoke_blocks(live, monkeypatch):
    client, _, recs = live
    login(client)
    roe = make_roe(client)
    from superagent import probes
    calls = []
    monkeypatch.setattr(probes, "PROBES", {k: (lambda t, k=k: calls.append(k) or probes.ProbeResult(k)) for k in probes.PROBE_IDS})
    r = client.post("/api/missions", json={"target": "https://app.example.com", "objective": "posture", "profile": "quick"})
    assert r.status_code == 200, r.text
    m = r.json()["mission"]
    assert m["status"] == "awaiting_approval" and not calls
    recs.revoke(roe["id"], reason="stop")
    ap = client.get("/api/approvals").json()["approvals"][0]
    assert client.post(f"/api/approvals/{ap['id']}", json={"approved": True}).status_code == 409
    assert not calls


def test_exact_plan_approval_executes(live, monkeypatch):
    client, _, _ = live
    login(client)
    make_roe(client)
    from superagent import probes
    calls = []
    monkeypatch.setattr(probes, "PROBES", {k: (lambda t, k=k: calls.append(k) or probes.ProbeResult(k)) for k in probes.PROBE_IDS})
    m = client.post("/api/missions", json={"target": "https://app.example.com", "objective": "posture", "profile": "quick"}).json()["mission"]
    ap = client.get("/api/approvals").json()["approvals"][0]
    assert ap["payload"]["plan_hash"] == m["plan_hash"]
    assert client.post(f"/api/approvals/{ap['id']}", json={"approved": True}).status_code == 200
    for _ in range(50):
        m2 = client.get(f"/api/missions/{m['id']}").json()["mission"]
        if m2["status"] == "completed":
            break
        time.sleep(0.02)
    assert m2["status"] == "completed", m2.get("error")
    assert calls == ["dns", "http_headers", "tls"]
    assert m2["report_file"] and len(m2["evidence"]) == 3


def test_raw_shell_and_install_retired(live):
    client, _, _ = live
    login(client)
    assert client.post("/api/command/shell", json={"command": "id"}).status_code == 410
    assert client.post("/api/install", json={"package": "nmap"}).status_code == 410


def test_provider_key_never_returned(live, monkeypatch):
    client, settings, _ = live
    login(client)
    object.__setattr__(settings, "api_key", "sk-secret-123456")
    try:
        data = client.get("/api/provider").json()
        assert "sk-secret" not in json.dumps(data)
        assert "key_hint" not in data
    finally:
        object.__setattr__(settings, "api_key", "")


def test_demo_is_offline_and_isolated(demo):
    client = demo
    assert client.get("/api/status").json()["demo"] is True
    assert client.post("/api/missions", json={"target": "https://example.com", "objective": "demo", "profile": "quick"}).status_code == 403
    assert client.post("/api/provider/test").status_code == 403
    assert client.get("/api/records").status_code == 403
    m = client.post("/api/demo/mission", json={"objective": "fixture", "profile": "web"}).json()["mission"]
    for _ in range(50):
        m = client.get(f"/api/missions/{m['id']}").json()["mission"]
        if m["status"] == "completed":
            break
        time.sleep(0.02)
    assert m["status"] == "completed" and m["demo"] is True
    assert m["counts"]["findings"] >= 5
    assert client.get("/api/reports").json()["reports"]


def test_scope_parser_rejects_credentials_and_weird_ports():
    from superagent import scope
    for target in ("https://user:pass@example.com", "https://example.com:99999", "gopher://example.com",
                   "https://example.com/%2e%2e", "example.com;id"):
        assert not scope.check(target, "web").allowed


def test_report_html_escapes_attributes(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAGENT_DATA_DIR", str(tmp_path))
    for name in list(sys.modules):
        if name == "superagent" or name.startswith("superagent."):
            del sys.modules[name]
    from superagent import report
    html = report.md_to_html('[x](https://example.com/"onmouseover="alert(1))')
    assert "&quot;" in html and 'onmouseover="alert' not in html

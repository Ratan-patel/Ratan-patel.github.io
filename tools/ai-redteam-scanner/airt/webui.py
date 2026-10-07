"""Built-in web console for AIRT (stdlib http.server, no dependencies).

    airt serve --port 8765

Local-first by design: remote targets need --allow-remote, because a browser
button that attacks arbitrary endpoints is a foot-gun.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from . import __version__, mutators, payloads, report, scoring
from .engine import ScanConfig, Scanner, environment
from .targets import (AnthropicTarget, EchoTarget, GenericHTTPTarget,
                      OllamaTarget, OpenAICompatibleTarget, Target)

JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
WEBUI_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui.html")


def _is_local(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return (host in ("localhost", "127.0.0.1", "::1", "0.0.0.0")
            or host.endswith(".local") or host.startswith("192.168.") or host.startswith("10."))


def build_target(spec: Dict[str, Any]) -> Target:
    kind = spec.get("type", "simulator")
    common = dict(system_prompt=spec.get("system_prompt") or None,
                  temperature=float(spec.get("temperature", 0.0)),
                  max_tokens=int(spec.get("max_tokens", 512)))
    if kind == "simulator":
        return EchoTarget(mode=spec.get("simulator_mode", "weak"), **common)
    if kind == "openai":
        return OpenAICompatibleTarget(base_url=spec.get("url") or "https://api.openai.com/v1",
                                      model=spec.get("model") or "gpt-4o-mini",
                                      api_key=spec.get("api_key") or None, **common)
    if kind == "anthropic":
        return AnthropicTarget(model=spec.get("model") or "claude-3-5-sonnet-latest",
                               api_key=spec.get("api_key") or None, **common)
    if kind == "ollama":
        return OllamaTarget(model=spec.get("model") or "llama3.1",
                            base_url=spec.get("url") or "http://localhost:11434", **common)
    if kind == "http":
        url = spec.get("url") or ""
        if not url:
            raise ValueError("target URL is required for a custom HTTP bot")
        headers = {}
        for h in (spec.get("headers") or "").splitlines():
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()
        return GenericHTTPTarget(url=url, body=spec.get("body") or '{"message": "{prompt}"}',
                                 response_path=spec.get("response_path") or "",
                                 headers=headers, **common)
    raise ValueError(f"unknown target type: {kind}")


class Handler(BaseHTTPRequestHandler):
    server_version = f"AIRT/{__version__}"
    protocol_version = "HTTP/1.1"

    # -------------------------------------------------------------- helpers
    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: Any) -> None:
        self._send(code, json.dumps(payload, default=str).encode(), "application/json")

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode())
        except json.JSONDecodeError:
            return {}

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter console
        if os.getenv("AIRT_HTTP_DEBUG"):
            super().log_message(fmt, *args)

    # ------------------------------------------------------------------ GET
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            try:
                body = open(WEBUI_HTML, "rb").read()
            except OSError:
                body = b"<h1>webui.html missing</h1>"
            return self._send(200, body, "text/html; charset=utf-8")
        if path == "/api/meta":
            return self._json(200, {
                "version": __version__,
                "categories": payloads.list_categories(),
                "mutations": mutators.MUTATOR_NAMES,
                "probes": [{"id": p.id, "name": p.name, "category": p.category,
                            "severity": p.severity, "owasp": p.owasp}
                           for p in payloads.ALL_PROBES],
                "profiles": ["quick", "standard", "deep", "owasp"],
                "env": environment(),
                "allow_remote": getattr(self.server, "allow_remote", False),
            })
        if path == "/api/status":
            job_id = (parse_qs(parsed.query).get("job") or [""])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                return self._json(404, {"error": "unknown job"})
            return self._json(200, {
                "state": job["state"], "done": job["done"], "total": job["total"],
                "log": job["log"][-400:], "summary": job.get("summary"),
                "results": job.get("results", []),
            })
        if path == "/api/result":
            job_id = (parse_qs(parsed.query).get("job") or [""])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                return self._json(404, {"error": "unknown job"})
            return self._json(200, {"summary": job.get("summary"), "results": job.get("results", [])})
        return self._json(404, {"error": "not found"})

    # ----------------------------------------------------------------- POST
    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/scan":
            spec = self._read_json()
            try:
                target = build_target(spec.get("target", {}))
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
            url = spec.get("target", {}).get("url") or ""
            if (not getattr(self.server, "allow_remote", False)
                    and target.kind != "simulator" and url and not _is_local(url)):
                return self._json(403, {
                    "error": "remote targets are disabled in the web console "
                             "(restart with `airt serve --allow-remote` after confirming "
                             "you have written authorisation)."})
            job_id = uuid.uuid4().hex[:12]
            with JOBS_LOCK:
                JOBS[job_id] = {"state": "queued", "done": 0, "total": 0,
                                "log": [], "results": [], "summary": None}
            threading.Thread(target=_run_job, args=(self.server, job_id, spec, target),
                             daemon=True).start()
            return self._json(200, {"job": job_id})
        return self._json(404, {"error": "not found"})


def _run_job(server: ThreadingHTTPServer, job_id: str, spec: Dict[str, Any],
             target: Target) -> None:
    def update(**kw: Any) -> None:
        with JOBS_LOCK:
            JOBS[job_id].update(kw)

    def log(line: str) -> None:
        with JOBS_LOCK:
            JOBS[job_id]["log"].append(line)

    def progress(_msg: str, done: int, total: int) -> None:
        update(done=done, total=total)

    try:
        categories = spec.get("categories") or ["all"]
        min_sev = int(spec.get("min_severity", 1))
        mutate = spec.get("mutate") if isinstance(spec.get("mutate"), list) else []
        ids = spec.get("probes") or []
        probes = payloads.get_probes(categories=categories, min_severity=min_sev, ids=ids or None)
        if not probes:
            update(state="error")
            log("no probes matched the filters")
            return
        cfg = ScanConfig(probes=probes, mutate=[m for m in mutate if m in mutators.MUTATOR_NAMES],
                         workers=int(spec.get("workers", 4)), rps=float(spec.get("rps", 4.0)),
                         inject_canary=bool(spec.get("inject_canary")),
                         canary=spec.get("canary") or None,
                         limit=int(spec.get("limit", 0)),
                         retries=int(spec.get("retries", 1)))
        update(state="running", total=len(probes))
        scanner = Scanner(target, cfg, log=log, progress=progress)
        scanner.run()
        summary = scanner.summary()
        summary["environment"] = environment()
        update(state="done", summary=summary,
               results=[r.to_dict() for r in scanner.results],
               done=len(scanner.results), total=len(scanner.results))
    except Exception as exc:  # noqa: BLE001
        log(f"fatal: {type(exc).__name__}: {exc}")
        update(state="error")


def serve(host: str = "0.0.0.0", port: int = 8765, allow_remote: bool = False) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.allow_remote = allow_remote  # type: ignore[attr-defined]
    url = f"http://{'localhost' if host in ('0.0.0.0', '::') else host}:{port}/"
    print(f"""
  AIRT web console  →  {url}
  targets: built-in simulator, OpenAI-compatible, Anthropic, Ollama, custom HTTP bot
  remote targets: {'ENABLED (authorised testing only!)' if allow_remote else 'disabled (use --allow-remote)'}
  Ctrl-C to stop
""")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped.")
    finally:
        httpd.server_close()

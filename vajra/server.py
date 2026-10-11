#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VAJRA Web Server — mobile-first Web UI (PWA).
'vajra --server' se chalta hai. Phone browser mein http://localhost:8080 kholo,
"Add to Home Screen" karlo — APK jaisa app ban jayega (icon + fullscreen).
Zero dependency — sirf Python stdlib.
"""

import json
import os
import threading

from agent import executor, registry
from agent.chat import VajraSession
from agent.llm import DEFAULTS, LLM, VajraError

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")

# ------------------------------------------------------------------ state
LOCK = threading.Lock()
SESSION = None
CONFIG = {"backend": "", "api_key": "", "model": ""}


def _load_config():
    global SESSION, CONFIG
    path = os.path.join(executor.VAJRA_HOME, "config.json")
    try:
        with open(path) as f:
            CONFIG.update(json.load(f))
    except Exception:
        pass
    SESSION = VajraSession(_make_llm())


def _make_llm():
    return LLM(backend=CONFIG.get("backend", "groq"),
               api_key=CONFIG.get("api_key", ""),
               model=CONFIG.get("model", ""),
               base_url=CONFIG.get("base_url", ""))


def _save_config():
    path = os.path.join(executor.VAJRA_HOME, "config.json")
    with open(path, "w") as f:
        json.dump(CONFIG, f, indent=1)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


_load_config()


# ------------------------------------------------------------------ server
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
from urllib.parse import urlparse  # noqa: E402

MIME = {".html": "text/html", ".js": "application/javascript",
        ".json": "application/json", ".png": "image/png",
        ".css": "text/css", ".svg": "image/svg+xml"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    # ---------------------------------------------------------- helpers
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _sse_start(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

    def _sse(self, event):
        try:
            self.wfile.write(("data: %s\n\n" % json.dumps(event)).encode("utf-8"))
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError):
            return False

    # ---------------------------------------------------------- GET
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/tools":
            tools = []
            for t in registry.TOOLS:
                tools.append({**t, "installed": registry.installed(t)})
            return self._json({"categories": registry.CATEGORIES, "tools": tools})
        if path == "/api/config":
            d = DEFAULTS.get(CONFIG.get("backend") or "groq", DEFAULTS["groq"])
            return self._json({
                "backend": CONFIG.get("backend") or "",
                "model": CONFIG.get("model") or d["model"],
                "has_key": bool(CONFIG.get("api_key")),
                "base": d["base"], "needs_key": d["needs_key"],
                "defaults": {k: {"label": v["label"], "model": v["model"],
                                 "needs_key": v["needs_key"], "hint": v["hint"]}
                             for k, v in DEFAULTS.items()},
            })
        if path == "/api/scope":
            return self._json({"scope": executor.scope_list()})
        if path == "/api/report":
            p = executor.generate_report()
            try:
                with open(p) as f:
                    return self._json({"path": p, "content": f.read()})
            except Exception:
                return self._json({"path": p, "content": ""})
        # static
        if path == "/":
            path = "/index.html"
        fname = os.path.normpath(path.lstrip("/"))
        fpath = os.path.join(WEB_DIR, fname)
        if (not fpath.startswith(WEB_DIR) or not os.path.isfile(fpath)):
            return self._json({"error": "not found"}, 404)
        with open(fpath, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type",
                         MIME.get(os.path.splitext(fpath)[1], "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    # ---------------------------------------------------------- POST
    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()

        if path == "/api/config":
            with LOCK:
                if body.get("backend"):
                    CONFIG["backend"] = body["backend"]
                if body.get("api_key"):
                    CONFIG["api_key"] = body["api_key"].strip()
                if body.get("model"):
                    CONFIG["model"] = body["model"].strip()
                if body.get("base_url"):
                    CONFIG["base_url"] = body["base_url"].strip()
                _save_config()
                SESSION.llm = _make_llm()
                SESSION.history = []
            return self._json({"ok": True})

        if path == "/api/test":
            with LOCK:
                llm = _make_llm()
            try:
                secs, reply = llm.test()
                return self._json({"ok": True, "latency": secs, "reply": reply[:200]})
            except VajraError as e:
                return self._json({"ok": False, "error": str(e)})

        if path == "/api/scope":
            with LOCK:
                if body.get("action") == "add" and body.get("value"):
                    executor.scope_add(body["value"].strip())
                elif body.get("action") == "remove" and body.get("value"):
                    executor.scope_remove(body["value"].strip())
                items = executor.scope_list()
            return self._json({"scope": items})

        if path == "/api/reset":
            with LOCK:
                SESSION.history = []
            return self._json({"ok": True})

        if path == "/api/chat":
            return self._chat_flow(lambda: SESSION.send(
                str(body.get("text", "")), self._sse))

        if path == "/api/decision":
            pid = str(body.get("id", ""))
            approved = bool(body.get("approve"))
            return self._chat_flow(lambda: SESSION.resume(
                pid, approved, self._sse))

        return self._json({"error": "not found"}, 404)

    def _chat_flow(self, fn):
        self._sse_start()
        with LOCK:
            try:
                d = DEFAULTS.get(CONFIG.get("backend") or "", DEFAULTS["groq"])
                if d["needs_key"] and not CONFIG.get("api_key"):
                    self._sse({"t": "note", "text":
                               "⚙️ Pehle Setup tab mein API key daalo. "
                               "Free key: console.groq.com/keys (Groq — fastest) "
                               "ya aistudio.google.com/apikey (Gemini). "
                               "Offline chahiye toh backend=Ollama select karo "
                               "(pkg install ollama && ollama serve)."})
                    self._sse({"t": "done"})
                    return
                state, pend = fn()
                if state == "pending" and pend:
                    pass  # confirm event already sent by session
                self._sse({"t": "done"})
            except VajraError as e:
                self._sse({"t": "error", "message": str(e)})
                self._sse({"t": "done"})
            except Exception as e:
                self._sse({"t": "error", "message": "Server error: %s" % e})
                self._sse({"t": "done"})


def serve(host="0.0.0.0", port=8080):
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = "http://localhost:%d" % port
    print("\n⚡ VAJRA Web UI live:  %s" % url)
    print("📱 Phone browser mein kholo → menu → 'Add to Home Screen' → app ban jayega!")
    print("   (Band karne ke liye Ctrl+C)\n")
    # Termux mein browser auto-kholo + phone ko jagaye rakho
    try:
        import subprocess
        subprocess.Popen(["termux-open-url", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    try:
        import subprocess
        subprocess.Popen(["termux-wake-lock"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("🔒 Wake-lock laga diya (Android server ko band nahi karega).\n")
    except Exception:
        print("💡 Tip: 'termux-wake-lock' chalao taaki Android background mein server na maare.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer band.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    serve(a.host, a.port)

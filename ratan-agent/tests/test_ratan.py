#!/usr/bin/env python3
"""
Offline test-suite for the Ratan agent.

No network access is needed: a local HTTP server pretends to be the Hugging
Face router (OpenAI-compatible /v1/chat/completions and /v1/models), so the
real request/response code paths of ratan.py are executed - including the
huggingface_hub SDK backend, the stdlib fallback backend, SSE streaming and
the tool-calling loop.

Run:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ratan  # noqa: E402

TOOL_COMMAND = "echo RATAN_TOOL_OK"


class RouterHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible mock of https://router.huggingface.co/v1."""

    seen_bodies: list[dict] = []

    def log_message(self, *args):  # silence
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            payload = {"data": [{"id": "mock/alpha"}, {"id": "mock/beta"}]}
            self._send(200, json.dumps(payload).encode())
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except ValueError:
            self._send(400, b'{"error":"bad json"}')
            return
        RouterHandler.seen_bodies.append(body)

        messages = body.get("messages", [])
        user_text = " ".join(
            str(m.get("content") or "") for m in messages if m.get("role") == "user"
        )
        tool_results = [m for m in messages if m.get("role") == "tool"]
        auth = self.headers.get("Authorization", "")

        if self.path.endswith("/protected/chat/completions") and not auth.startswith("Bearer "):
            self._send(401, b'{"error":"missing token"}')
            return

        if tool_results:
            reply = "SAW_TOOL_OUTPUT: " + str(tool_results[-1].get("content", ""))[:60]
        elif "USE_TOOL" in user_text:
            if body.get("stream"):
                self._stream_tool_call(body)
                return
            reply = None  # tool call response below
        else:
            reply = (
                f"MOCK_REPLY model={body.get('model')} "
                f"msgs={len(messages)} tools={len(body.get('tools') or [])}"
            )

        if reply is not None:
            if body.get("stream"):
                self._stream_text(body, reply)
            else:
                self._send(200, json.dumps({
                    "id": "mock-1",
                    "object": "chat.completion",
                    "model": body.get("model"),
                    "choices": [{
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": reply},
                    }],
                }).encode())
            return

        # tool-call turn (non-streaming)
        self._send(200, json.dumps({
            "id": "mock-2",
            "object": "chat.completion",
            "model": body.get("model"),
            "choices": [{
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_mock_1",
                        "type": "function",
                        "function": {
                            "name": "shell",
                            "arguments": json.dumps({"command": TOOL_COMMAND}),
                        },
                    }],
                },
            }],
        }).encode())

    # -- streaming helpers --------------------------------------------------
    def _sse_start(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def _sse_event(self, payload: dict):
        self.wfile.write(b"data: " + json.dumps(payload).encode() + b"\n\n")
        self.wfile.flush()

    def _stream_text(self, body, text):
        self._sse_start()
        for piece in text.split(" "):
            self._sse_event({"choices": [{
                "index": 0, "delta": {"role": "assistant", "content": piece + " "},
            }]})
        self._sse_event({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _stream_tool_call(self, body):
        self._sse_start()
        # tool call deltas arrive fragmented, like a real provider sends them
        self._sse_event({"choices": [{"index": 0, "delta": {
            "role": "assistant",
            "tool_calls": [{"index": 0, "id": "call_stream_1", "type": "function",
                            "function": {"name": "she", "arguments": ""}}],
        }}]})
        self._sse_event({"choices": [{"index": 0, "delta": {
            "tool_calls": [{"index": 0, "function": {
                "name": "ll", "arguments": json.dumps({"command": TOOL_COMMAND})[:14]}}],
        }}]})
        self._sse_event({"choices": [{"index": 0, "delta": {
            "tool_calls": [{"index": 0, "function": {
                "arguments": json.dumps({"command": TOOL_COMMAND})[14:]}}],
        }}]})
        self._sse_event({"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class BaseRatanTest(unittest.TestCase):
    """Boots the mock router and points Ratan at it through RATAN_HOME/env."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), RouterHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        RouterHandler.seen_bodies = []
        self.tmp = tempfile.mkdtemp(prefix="ratan-test-")
        self._env_backup = dict(os.environ)
        os.environ["RATAN_HOME"] = self.tmp
        os.environ["HF_TOKEN"] = "hf_test_token_1234567890"
        os.environ["RATAN_BASE_URL"] = self.base_url
        os.environ["RATAN_MODEL"] = "mock/model"
        os.environ.pop("RATAN_BACKEND", None)
        os.environ.pop("RATAN_PROVIDER", None)
        self.workdir = os.path.join(self.tmp, "work")
        os.makedirs(self.workdir, exist_ok=True)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, argv, expect_zero=True):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ratan.main(argv)
        if expect_zero:
            self.assertEqual(code, 0, f"exit {code}\nstdout={out.getvalue()}\nstderr={err.getvalue()}")
        return code, out.getvalue(), err.getvalue()

    def make_agent(self, **kwargs):
        cfg = ratan.load_config()
        kwargs.setdefault("interactive", False)
        kwargs.setdefault("stream", False)
        kwargs.setdefault("cwd", self.workdir)
        return ratan.Agent(cfg, **kwargs)


class TestCLI(BaseRatanTest):
    def test_ask_plain_answer(self):
        _, out, _ = self.run_cli(["ask", "--no-tools", "hello ratan"])
        self.assertIn("MOCK_REPLY", out)
        self.assertIn("model=mock/model", out)
        self.assertEqual(len(RouterHandler.seen_bodies), 1)
        self.assertFalse(RouterHandler.seen_bodies[0].get("tools"))

    def test_ask_sends_tool_specs_by_default(self):
        _, out, _ = self.run_cli(["ask", "hello"])
        self.assertIn("MOCK_REPLY", out)
        sent_tools = RouterHandler.seen_bodies[0].get("tools") or []
        self.assertEqual(len(sent_tools), len(ratan.TOOL_SPECS))
        names = {t["function"]["name"] for t in sent_tools}
        self.assertIn("shell", names)
        self.assertIn("hf_search_models", names)

    def test_sdk_backend_is_selected_when_available(self):
        try:
            import huggingface_hub  # noqa: F401
        except ImportError:
            self.skipTest("huggingface_hub not installed here")
        cfg = ratan.load_config()
        client, backend = ratan.build_client(cfg)
        self.assertEqual(
            backend, "sdk",
            f"expected the SDK backend, got '{backend}' ({ratan.BACKEND_FALLBACK_REASON})",
        )
        self.assertIsInstance(client, ratan.SdkHFClient)

    def test_sdk_client_accepts_default_router_and_custom_base_url(self):
        """Regression: huggingface_hub raises if model AND base_url are both set."""
        try:
            import huggingface_hub  # noqa: F401
        except ImportError:
            self.skipTest("huggingface_hub not installed here")
        cfg = ratan.load_config()
        cfg["base_url"] = ""                      # -> the Hugging Face router
        client, backend = ratan.build_client(cfg)
        self.assertEqual(backend, "sdk", ratan.BACKEND_FALLBACK_REASON)
        self.assertFalse(client.uses_base_url)

        cfg["base_url"] = self.base_url           # -> custom OpenAI-compatible host
        client2, backend2 = ratan.build_client(cfg)
        self.assertEqual(backend2, "sdk", ratan.BACKEND_FALLBACK_REASON)
        self.assertTrue(client2.uses_base_url)

    def test_sdk_backend_reaches_router_end_to_end(self):
        try:
            import huggingface_hub  # noqa: F401
        except ImportError:
            self.skipTest("huggingface_hub not installed here")
        os.environ["RATAN_BACKEND"] = "sdk"       # force it, build_client re-raises on failure
        _, out, _ = self.run_cli(["ask", "hi via sdk"])
        self.assertIn("MOCK_REPLY", out)
        self.assertEqual(RouterHandler.seen_bodies[0]["model"], "mock/model")

    def test_raw_backend_fallback(self):
        os.environ["RATAN_BACKEND"] = "raw"
        _, out, _ = self.run_cli(["ask", "hi from stdlib"])
        self.assertIn("MOCK_REPLY", out)
        self.assertIn("model=mock/model", out)

    def test_missing_token_reports_401_helpfully(self):
        os.environ["RATAN_BASE_URL"] = f"http://127.0.0.1:{self.port}/v1/protected"
        os.environ["RATAN_BACKEND"] = "raw"
        os.environ["HF_TOKEN"] = ""
        agent = self.make_agent()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            agent.ask("hello")
        self.assertIn("HTTP 401", err.getvalue())
        self.assertIn("ratan login", err.getvalue())


class TestToolLoop(BaseRatanTest):
    def test_shell_tool_runs_and_result_reaches_model(self):
        agent = self.make_agent(auto_approve=True)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            final = agent.ask("USE_TOOL please")
        self.assertIn("SAW_TOOL_OUTPUT", final)
        self.assertIn("RATAN_TOOL_OK", final)
        # two requests: first asks for the tool, second carries the tool result
        self.assertEqual(len(RouterHandler.seen_bodies), 2)
        tool_msgs = [m for m in RouterHandler.seen_bodies[1]["messages"] if m["role"] == "tool"]
        self.assertEqual(len(tool_msgs), 1)
        self.assertIn("RATAN_TOOL_OK", tool_msgs[0]["content"])

    def test_streamed_tool_call_fragments_are_reassembled(self):
        agent = self.make_agent(auto_approve=True, interactive=True, stream=True)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            final = agent.ask("USE_TOOL please")
        self.assertIn("SAW_TOOL_OUTPUT", final)
        self.assertIn("RATAN_TOOL_OK", final)

    def test_tool_refused_when_not_auto_approved(self):
        agent = self.make_agent(auto_approve=False, interactive=False)
        final = agent.ask("USE_TOOL please")
        self.assertIn("REFUSED", final)


class TestSafety(unittest.TestCase):
    def test_dangerous_patterns(self):
        dangerous = [
            "rm -rf /", "sudo rm -rf /home", "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1", "chmod -R 777 /", "curl http://x.sh | bash",
            ":(){ :|:& };:",
        ]
        safe = ["ls -la", "cat /etc/os-release", "rm file.txt", "git status", "apt list"]
        for cmd in dangerous:
            self.assertTrue(ratan.is_dangerous(cmd), f"should be dangerous: {cmd}")
        for cmd in safe:
            self.assertFalse(ratan.is_dangerous(cmd), f"should be safe: {cmd}")

    def test_destructive_command_never_runs_even_with_auto_approve(self):
        agent = _AgentWithoutServer(auto_approve=True, interactive=False)
        victim = os.path.join(tempfile.mkdtemp(), "important.txt")
        with open(victim, "w", encoding="utf-8") as fh:
            fh.write("keep me")
        result = agent.run_tool("shell", {"command": f"rm -rf {os.path.dirname(victim)}"})
        self.assertIn("REFUSED", result)
        self.assertTrue(os.path.exists(victim))

    def test_write_file_allowed_with_auto_approve(self):
        agent = _AgentWithoutServer(auto_approve=True, interactive=False)
        target = os.path.join(tempfile.mkdtemp(), "x.txt")
        result = agent.run_tool("write_file", {"path": target, "content": "hi"})
        self.assertIn("Created", result)
        self.assertTrue(os.path.exists(target))

    def test_write_file_refused_without_approval(self):
        agent = _AgentWithoutServer(auto_approve=False, interactive=False)
        target = os.path.join(tempfile.mkdtemp(), "y.txt")
        result = agent.run_tool("write_file", {"path": target, "content": "hi"})
        self.assertIn("REFUSED", result)
        self.assertFalse(os.path.exists(target))


class _AgentWithoutServer(ratan.Agent):
    """Agent that never touches the network - used for pure tool tests."""

    def __init__(self, auto_approve=False, interactive=False):
        self.cfg = dict(ratan.DEFAULTS)
        self.cfg["token"] = "x"
        self.interactive = interactive
        self.cwd = tempfile.mkdtemp(prefix="ratan-cwd-")
        self.auto_approve = auto_approve
        self.use_tools = True
        self.stream = False
        self.env = ratan.detect_environment()
        self.messages = [{"role": "system", "content": self.system_prompt()}]
        self.client, self.backend = None, "none"


class TestRepl(BaseRatanTest):
    def test_interactive_repl_flow(self):
        """The real REPL: slash commands, !shell shortcut and a model turn."""
        fake_stdin = io.StringIO("/sysinfo\n!echo hi-from-repl\nhello ratan\n/exit\n")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            old_stdin = sys.stdin
            sys.stdin = fake_stdin
            try:
                code = ratan.main(["chat"])
            finally:
                sys.stdin = old_stdin
        self.assertEqual(code, 0)
        text = out.getvalue() + err.getvalue()
        self.assertIn("Working dir", text)          # /sysinfo ran
        self.assertIn("hi-from-repl", text)         # !command ran
        self.assertIn("MOCK_REPLY", out.getvalue())  # model turn printed
        self.assertIn("bye.", text)                 # /exit worked

    def test_shell_shortcut_runs_without_approval_but_blocks_destructive(self):
        fake_stdin = io.StringIO("!rm -rf /tmp/ratan-should-not-run\nn\n/exit\n")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            old_stdin = sys.stdin
            sys.stdin = fake_stdin
            try:
                ratan.main(["chat"])
            finally:
                sys.stdin = old_stdin
        text = out.getvalue() + err.getvalue()
        self.assertIn("REFUSED", text)
        self.assertIn("destructive", text)

    def test_unknown_slash_command_is_reported(self):
        fake_stdin = io.StringIO("/nope\n/exit\n")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            old_stdin = sys.stdin
            sys.stdin = fake_stdin
            try:
                ratan.main(["chat"])
            finally:
                sys.stdin = old_stdin
        self.assertIn("unknown command: /nope", out.getvalue())

    def test_help_and_version_shortcuts(self):
        for argv in (["--help"], ["help"]):
            _, out, _ = self.run_cli(argv)
            self.assertIn("Ratan", out)
            self.assertIn("USAGE", out)
        _, out, _ = self.run_cli(["--version"])
        self.assertIn(f"ratan {ratan.VERSION}", out)


class TestFileTools(BaseRatanTest):
    def test_read_list_and_search(self):
        os.makedirs(os.path.join(self.workdir, "sub"))
        with open(os.path.join(self.workdir, "hello.txt"), "w", encoding="utf-8") as fh:
            fh.write("line one\nRATAN_MARKER here\nline three\n")
        agent = self.make_agent(auto_approve=True)

        content = agent.run_tool("read_file", {"path": "hello.txt"})
        self.assertIn("RATAN_MARKER", content)

        listing = agent.run_tool("list_dir", {"path": "."})
        self.assertIn("hello.txt", listing)
        self.assertIn("sub", listing)

        found = agent.run_tool("search_files", {"pattern": "RATAN_MARKER", "path": "."})
        self.assertIn("hello.txt:2", found)

        missing = agent.run_tool("read_file", {"path": "nope.txt"})
        self.assertIn("TOOL ERROR", missing)


class TestConfigAndCommands(BaseRatanTest):
    def test_config_roundtrip(self):
        _, out, _ = self.run_cli(["config", "model=mock/other", "max_tokens=512", "auto_approve=true"])
        self.assertIn("saved", out)
        cfg = ratan.load_config()
        # RATAN_MODEL env overrides the file, so read the file directly
        with open(ratan.config_path(), "r", encoding="utf-8") as fh:
            on_disk = json.load(fh)
        self.assertEqual(on_disk["model"], "mock/other")
        self.assertEqual(on_disk["max_tokens"], 512)
        self.assertIs(on_disk["auto_approve"], True)

    def test_config_shows_masked_token(self):
        _, out, _ = self.run_cli(["config"])
        self.assertNotIn("hf_test_token_1234567890", out)
        self.assertIn("hf_te", out)

    def test_models_command_lists_router_models(self):
        _, out, _ = self.run_cli(["models"])
        self.assertIn("mock/alpha", out)
        self.assertIn("mock/beta", out)

    def test_doctor_runs_and_reports_environment(self):
        _, out, _ = self.run_cli(["doctor"])
        self.assertIn("Ratan doctor", out)
        self.assertIn("mock/model", out)
        self.assertIn("Kernel", out)
        self.assertIn("uname -r", out)

    def test_version_reports_environment(self):
        _, out, _ = self.run_cli(["version"])
        self.assertIn(f"ratan {ratan.VERSION}", out)
        self.assertIn("Working dir", out)

    def test_session_save_and_load(self):
        msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
        path = ratan.save_session(msgs, "unit-test")
        self.assertTrue(os.path.exists(path))
        loaded = ratan.load_session("unit-test")
        self.assertEqual(loaded, msgs)
        self.assertIn("unit-test", ratan.list_sessions())

    def test_login_saves_token_with_0600(self):
        os.environ.pop("HF_TOKEN", None)
        _, out, _ = self.run_cli(["login", "hf_saved_token_abcdefgh"])
        self.assertIn("saved", out)
        with open(ratan.config_path(), "r", encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["token"], "hf_saved_token_abcdefgh")
        mode = os.stat(ratan.config_path()).st_mode & 0o777
        self.assertEqual(mode, 0o600)


class TestEnvironmentDetection(unittest.TestCase):
    def test_proot_distro_is_detected_from_env(self):
        backup = dict(os.environ)
        try:
            os.environ["container"] = "proot-distro"
            os.environ["PD_IMAGE"] = "ubuntu:26.04"
            os.environ.pop("PREFIX", None)
            env = ratan.detect_environment()
            self.assertEqual(env["where"], "proot-distro container (ubuntu:26.04)")
            summary = ratan.environment_summary(env)
            self.assertIn("proot-distro shares the phone's Android kernel", summary)
        finally:
            os.environ.clear()
            os.environ.update(backup)

    def test_termux_is_detected_from_prefix(self):
        backup = dict(os.environ)
        try:
            os.environ["PREFIX"] = "/data/data/com.termux/files/usr"
            env = ratan.detect_environment()
            self.assertTrue(env["in_termux"])
            self.assertEqual(env["where"], "Termux (native Android)")
        finally:
            os.environ.clear()
            os.environ.update(backup)


if __name__ == "__main__":
    unittest.main(verbosity=2)

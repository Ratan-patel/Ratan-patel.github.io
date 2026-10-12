#!/usr/bin/env python3
"""
Ratan - terminal AI agent for phones.

Runs in a plain terminal (Termux on Android, Ubuntu 26.04 inside
proot-distro, or any Linux/macOS shell) and talks to Hugging Face
Inference Providers over the OpenAI-compatible router:

    https://router.huggingface.co/v1/chat/completions

It needs one thing from you: a free Hugging Face token (HF_TOKEN).

Backends
--------
1. "sdk" - huggingface_hub.InferenceClient (preferred, `pip install huggingface_hub`)
2. "raw" - Python standard library only (urllib), used automatically when the
           SDK is missing. Set RATAN_BACKEND=raw to force it.

Both backends speak the same wire format, so the agent behaves identically.

Subcommands: chat (default), ask, doctor, models, config, login, version.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "2.0.0"
APP_DIR_NAME = ".ratan"
CONFIG_NAME = "config.json"

HF_ROUTER = "https://router.huggingface.co/v1"
HF_HUB_API = "https://huggingface.co/api"
DEFAULT_MODEL = "openai/gpt-oss-120b:fastest"

MAX_TOOL_ROUNDS = 8
MAX_TOOL_OUTPUT = 12000          # chars of tool output fed back to the model
DEFAULT_SHELL_TIMEOUT = 120
HISTORY_KEEP = 40                # messages kept in context (plus system prompt)

# --------------------------------------------------------------------------
# Small terminal helpers (no third-party dependency on purpose)
# --------------------------------------------------------------------------

def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("RATAN_FORCE_COLOR"):
        return True
    return bool(sys.stdout.isatty())


COLOR = _supports_color()


def c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if COLOR else text


def bold(t: str) -> str:
    return c(t, "1")


def dim(t: str) -> str:
    return c(t, "2")


def red(t: str) -> str:
    return c(t, "31")


def green(t: str) -> str:
    return c(t, "32")


def yellow(t: str) -> str:
    return c(t, "33")


def cyan(t: str) -> str:
    return c(t, "36")


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

def app_dir() -> str:
    override = os.environ.get("RATAN_HOME")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(os.path.expanduser("~"), APP_DIR_NAME)


def config_path() -> str:
    return os.path.join(app_dir(), CONFIG_NAME)


def sessions_dir() -> str:
    return os.path.join(app_dir(), "sessions")


DEFAULTS = {
    "model": DEFAULT_MODEL,
    "token": "",
    "provider": "",
    "base_url": "",
    "max_tokens": 1024,
    "temperature": 0.4,
    "auto_approve": False,
    "tools": True,
    "language": "hinglish",
    "session": "default",
}

CONFIG_KEYS = tuple(DEFAULTS)


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    path = config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key in CONFIG_KEYS:
                    if key in data:
                        cfg[key] = data[key]
        except (OSError, ValueError) as exc:
            eprint(yellow(f"[ratan] config file unreadable ({exc}); using defaults"))
    # environment wins over the file
    cfg["token"] = (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
        or cfg["token"]
    )
    if os.environ.get("RATAN_MODEL"):
        cfg["model"] = os.environ["RATAN_MODEL"]
    if os.environ.get("RATAN_BASE_URL"):
        cfg["base_url"] = os.environ["RATAN_BASE_URL"]
    if os.environ.get("RATAN_PROVIDER"):
        cfg["provider"] = os.environ["RATAN_PROVIDER"]
    return cfg


def save_config(cfg: dict) -> str:
    os.makedirs(app_dir(), exist_ok=True)
    path = config_path()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({k: cfg.get(k, DEFAULTS[k]) for k in CONFIG_KEYS}, fh, indent=2)
        fh.write("\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def mask_token(token: str) -> str:
    if not token:
        return "(not set)"
    if len(token) <= 10:
        return token[:2] + "***"
    return f"{token[:5]}...{token[-4:]} (len {len(token)})"


# --------------------------------------------------------------------------
# Environment reporting (this is what "phone + Ubuntu" looks like to Ratan)
# --------------------------------------------------------------------------

def detect_environment() -> dict:
    """Facts about where we are running. Used by /sysinfo and the system prompt."""
    env = {
        "container": os.environ.get("container", ""),
        "pd_image": os.environ.get("PD_IMAGE", ""),
        "pd_container": os.environ.get("PD_CONTAINER", ""),
        "termux_prefix": os.environ.get("PREFIX", ""),
        "in_termux": bool(os.environ.get("PREFIX", "").endswith("com.termux/files/usr")),
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cwd": os.getcwd(),
        "home": os.path.expanduser("~"),
    }
    uname = platform.uname()
    env["kernel_release"] = uname.release
    env["kernel_version"] = uname.version

    if env["in_termux"]:
        env["where"] = "Termux (native Android)"
    elif env["container"] == "proot-distro" or env["pd_image"]:
        env["where"] = f"proot-distro container ({env['pd_image'] or env['pd_container']})"
    else:
        env["where"] = f"{env['system']} host shell"

    os_release = {}
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as fh:
            for line in fh:
                if "=" in line:
                    k, _, v = line.strip().partition("=")
                    os_release[k] = v.strip('"')
    except OSError:
        pass
    env["distro"] = os_release.get("PRETTY_NAME", "")

    # Memory / CPU, best effort.
    env["cpu_count"] = os.cpu_count() or 0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    env["mem_total_mb"] = kb // 1024
                    break
    except (OSError, ValueError, IndexError):
        env["mem_total_mb"] = 0
    return env


def environment_summary(env: dict) -> str:
    parts = [
        f"Host: {env['where']}",
        f"OS: {env['distro'] or env['system']}",
        f"Kernel (uname -r): {env['kernel_release']}",
        f"Arch: {env['machine']} | CPU: {env['cpu_count']} | RAM: {env.get('mem_total_mb', 0)} MB",
        f"Python: {env['python']}",
        f"Working dir: {env['cwd']}",
    ]
    if env["in_termux"]:
        parts.append(
            "Note: this is Termux, not Ubuntu. Run the installer to get Ubuntu "
            "26.04 in proot-distro, then use `proot-distro login ubuntu`."
        )
    elif env["container"] == "proot-distro":
        parts.append(
            "Note: proot-distro shares the phone's Android kernel; `uname -r` here "
            "is a string proot reports, not a bootable Linux kernel."
        )
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Safety
# --------------------------------------------------------------------------

DANGEROUS_PATTERNS = [
    r"\brm\s+(-[a-z]*[rf][a-z]*\s+)+(-[a-z]*\s+)*[/~]",
    r"\brm\s+-rf?\s+/\s*$",
    r"\bmkfs\b", r"\bdd\b.*\bof=/dev/", r">\s*/dev/sd[a-z]",
    r":\(\)\s*\{.*\}\s*;\s*:",          # fork bomb
    r"\bshutdown\b", r"\breboot\b", r"\bhalt\b",
    r"\bchmod\s+-R\s+777\s+/", r"\bchown\s+-R\s+.*\s+/\s*$",
    r"\bsudo\s+rm\b", r"\bwipefs\b", r"\bfdisk\b", r"\bparted\b",
    r"\bgit\s+push\b.*--force", r"\bcurl\b.*\|\s*(sudo\s+)?(ba)?sh",
    r"\bwget\b.*\|\s*(sudo\s+)?(ba)?sh",
]
DANGEROUS_RE = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


def is_dangerous(command: str) -> bool:
    return any(rx.search(command) for rx in DANGEROUS_RE)


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------

class ToolError(Exception):
    pass


def _run_shell(command: str, cwd: str, timeout: int, approve) -> str:
    if is_dangerous(command):
        note = red("[blocked] this looks destructive; refusing to auto-run it.")
        eprint(note)
        if not approve(f"dangerous command: {command}", dangerous=True):
            return "REFUSED: user declined a destructive command."
    elif not approve(f"run: {command}"):
        return "REFUSED: user declined to run this command."
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"TIMEOUT after {timeout}s: {command}"
    except OSError as exc:
        raise ToolError(f"could not start shell: {exc}") from exc
    out = proc.stdout or ""
    err = proc.stderr or ""
    body = [f"$ {command}", f"[exit {proc.returncode} in {time.time() - started:.2f}s]"]
    if out.strip():
        body.append(out.rstrip())
    if err.strip():
        body.append("--- stderr ---")
        body.append(err.rstrip())
    text = "\n".join(body)
    if len(text) > MAX_TOOL_OUTPUT:
        text = text[:MAX_TOOL_OUTPUT] + f"\n...[truncated {len(text) - MAX_TOOL_OUTPUT} chars]"
    return text


def _safe_path(path: str, cwd: str) -> str:
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    return os.path.abspath(p)


def _read_file(path: str, cwd: str, max_lines: int) -> str:
    p = _safe_path(path, cwd)
    if not os.path.exists(p):
        raise ToolError(f"no such file: {p}")
    if os.path.isdir(p):
        raise ToolError(f"that is a directory: {p}")
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            lines = []
            for i, line in enumerate(fh, 1):
                if i > max_lines:
                    lines.append(f"...[stopped at {max_lines} lines]")
                    break
                lines.append(line.rstrip("\n"))
    except OSError as exc:
        raise ToolError(f"cannot read {p}: {exc}") from exc
    header = f"# {p}"
    return header + "\n" + "\n".join(lines)


def _write_file(path: str, content: str, cwd: str, approve) -> str:
    p = _safe_path(path, cwd)
    existed = os.path.exists(p)
    if not approve(f"{'overwrite' if existed else 'create'} file: {p} ({len(content)} chars)"):
        return "REFUSED: user declined the file write."
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    try:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
    except OSError as exc:
        raise ToolError(f"cannot write {p}: {exc}") from exc
    return f"{'Overwrote' if existed else 'Created'} {p} ({len(content)} chars)"


def _list_dir(path: str, cwd: str, max_entries: int) -> str:
    p = _safe_path(path, cwd)
    if not os.path.isdir(p):
        raise ToolError(f"not a directory: {p}")
    try:
        names = sorted(os.listdir(p))
    except OSError as exc:
        raise ToolError(f"cannot list {p}: {exc}") from exc
    lines = [f"# {p}"]
    for name in names[:max_entries]:
        full = os.path.join(p, name)
        kind = "d" if os.path.isdir(full) else "f"
        try:
            size = os.path.getsize(full)
        except OSError:
            size = 0
        lines.append(f"{kind} {size:>10}  {name}")
    if len(names) > max_entries:
        lines.append(f"...[{len(names) - max_entries} more entries]")
    return "\n".join(lines)


def _search_files(pattern: str, path: str, cwd: str, max_hits: int) -> str:
    root = _safe_path(path or ".", cwd)
    if not os.path.isdir(root):
        raise ToolError(f"not a directory: {root}")
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        raise ToolError(f"bad regex: {exc}") from exc
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".cache"}
    hits: list[str] = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                if os.path.getsize(full) > 2_000_000:
                    continue
                with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                    scanned += 1
                    for lineno, line in enumerate(fh, 1):
                        if rx.search(line):
                            hits.append(f"{full}:{lineno}: {line.strip()[:200]}")
                            if len(hits) >= max_hits:
                                raise StopIteration
            except (OSError, UnicodeError, StopIteration) as exc:
                if isinstance(exc, StopIteration):
                    raise
                continue
        if len(hits) >= max_hits:
            break
    if not hits:
        return f"No match for /{pattern}/ under {root} ({scanned} files scanned)."
    return f"{len(hits)} match(es) for /{pattern}/ under {root}:\n" + "\n".join(hits)


def _hf_search_models(search: str, limit: int, token: str) -> str:
    query = urllib.parse.urlencode(
        {"search": search, "sort": "downloads", "direction": "-1", "limit": min(limit, 30)}
    )
    url = f"{HF_HUB_API}/models?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": f"ratan-agent/{VERSION}"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError) as exc:
        raise ToolError(f"hub search failed: {exc}") from exc
    if not data:
        return f"No Hugging Face model matched '{search}'."
    lines = [f"Hugging Face models for '{search}':"]
    for item in data[:limit]:
        mid = item.get("id", "?")
        dl = item.get("downloads", 0)
        likes = item.get("likes", 0)
        tags = ",".join([t for t in item.get("pipeline_tag", "").split(",") if t] or ["-"])
        lines.append(f"- {mid}  [task={tags} downloads={dl} likes={likes}]")
    lines.append("Use one with: ratan --model <id>  (add :fastest / :cheapest to pick routing)")
    return "\n".join(lines)


TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": (
                "Run a shell command in the user's terminal (Termux or the Ubuntu "
                "proot container) and return stdout, stderr and the exit code. "
                "Use this to check real facts instead of guessing: package lists, "
                "file contents, apt/pkg output, uname, python versions, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line to execute."},
                    "timeout": {"type": "integer", "description": "Seconds before the command is killed.", "default": DEFAULT_SHELL_TIMEOUT},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the filesystem and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path (absolute, or relative to the working dir)."},
                    "max_lines": {"type": "integer", "description": "Max lines to return.", "default": 400},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the entries of a directory with sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."},
                    "max_entries": {"type": "integer", "default": 200},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search file contents under a directory with a regular expression (like grep -rn).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Python regular expression."},
                    "path": {"type": "string", "default": "."},
                    "max_hits": {"type": "integer", "default": 40},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sysinfo",
            "description": "Report the runtime environment: Termux vs proot-distro Ubuntu, distro version, kernel string, arch, CPU, RAM, Python.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hf_search_models",
            "description": "Search the Hugging Face Hub for models by keyword, sorted by downloads.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string"},
                    "limit": {"type": "integer", "default": 8},
                },
                "required": ["search"],
            },
        },
    },
]

TOOL_NAMES = [t["function"]["name"] for t in TOOL_SPECS]


# --------------------------------------------------------------------------
# Hugging Face backends
# --------------------------------------------------------------------------

class RawHFClient:
    """OpenAI-compatible chat completions using only the standard library."""

    def __init__(self, base_url: str, token: str, model: str, provider: str = "", timeout: int = 180):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.model = model
        self.provider = provider
        self.timeout = timeout

    def _url(self) -> str:
        base = self.base_url
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def chat_completion(self, messages, *, model=None, stream=False, tools=None,
                        tool_choice=None, max_tokens=None, temperature=None, **_):
        payload = {"model": model or self.model, "messages": messages, "stream": bool(stream)}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        headers = {"Content-Type": "application/json", "User-Agent": f"ratan-agent/{VERSION}"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self._url(), data=body, headers=headers, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:600]
            raise RuntimeError(f"HTTP {exc.code} from {self._url()}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"network error reaching {self._url()}: {exc.reason}") from exc
        if stream:
            return _iter_sse(resp)
        with resp:
            return json.loads(resp.read().decode("utf-8"))


def _iter_sse(resp):
    """Yield parsed `data:` JSON objects from an OpenAI-style SSE stream."""
    for raw in resp:
        line = raw.decode("utf-8", "replace").strip() if isinstance(raw, bytes) else str(raw).strip()
        if not line or line.startswith(":"):
            continue
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            yield json.loads(data)
        except ValueError:
            continue
    try:
        resp.close()
    except Exception:
        pass


class SdkHFClient:
    """Thin wrapper over huggingface_hub.InferenceClient.chat_completion."""

    def __init__(self, base_url: str, token: str, model: str, provider: str = "", timeout: int = 180):
        from huggingface_hub import InferenceClient  # imported lazily

        kwargs: dict = {"token": token or None, "timeout": timeout}
        # huggingface_hub 1.x/2.x raises
        #   ValueError: Received both `model` and `base_url` arguments
        # because base_url is an alias for model. So pass exactly one:
        #  - a custom endpoint -> base_url (model then travels in the payload)
        #  - the Hugging Face router -> model (provider routing handled by the SDK)
        self.uses_base_url = bool(base_url) and base_url.rstrip("/") != HF_ROUTER.rstrip("/")
        if self.uses_base_url:
            kwargs["base_url"] = base_url
        else:
            kwargs["model"] = model
            if provider:
                kwargs["provider"] = provider
        self.inner = InferenceClient(**kwargs)
        self.model = model

    def chat_completion(self, messages, *, model=None, stream=False, tools=None,
                        tool_choice=None, max_tokens=None, temperature=None, **_):
        kwargs = {"stream": bool(stream)}
        if model:
            kwargs["model"] = model
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            return self.inner.chat_completion(messages, **kwargs)
        except Exception as exc:  # huggingface_hub raises its own error types
            raise RuntimeError(f"Hugging Face call failed: {exc}") from exc


BACKEND_FALLBACK_REASON = ""


def build_client(cfg: dict):
    """Return (client, backend_name). Records why the SDK was not used."""
    global BACKEND_FALLBACK_REASON
    BACKEND_FALLBACK_REASON = ""
    backend = os.environ.get("RATAN_BACKEND", "auto").lower()
    base_url = cfg.get("base_url") or HF_ROUTER
    model = cfg["model"]
    token = cfg.get("token") or ""
    provider = cfg.get("provider") or ""
    if backend in ("auto", "sdk"):
        try:
            return SdkHFClient(base_url, token, model, provider), "sdk"
        except ImportError as exc:
            BACKEND_FALLBACK_REASON = (
                f"huggingface_hub is not installed ({exc}). "
                "Install it with: pip install -U huggingface_hub"
            )
            if backend == "sdk":
                raise
        except Exception as exc:
            BACKEND_FALLBACK_REASON = f"{type(exc).__name__}: {exc}"
            if backend == "sdk":
                raise
    elif backend != "raw":
        BACKEND_FALLBACK_REASON = f"unknown RATAN_BACKEND '{backend}'"
    return RawHFClient(base_url, token, model, provider), "raw"


# --------------------------------------------------------------------------
# Normalising SDK dataclasses and raw dicts into the same shape
# --------------------------------------------------------------------------

def _get(obj, name, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def choice_message(resp) -> dict:
    choices = _get(resp, "choices") or []
    if not choices:
        raise RuntimeError("model returned no choices")
    msg = _get(choices[0], "message") or {}
    return {
        "role": _get(msg, "role", "assistant") or "assistant",
        "content": _get(msg, "content") or "",
        "tool_calls": _get(msg, "tool_calls") or None,
    }


def normalize_tool_call(tc) -> dict:
    fn = _get(tc, "function") or {}
    return {
        "id": _get(tc, "id") or f"call_{abs(hash(str(tc))) % 10**8}",
        "type": "function",
        "function": {
            "name": _get(fn, "name") or "",
            "arguments": _get(fn, "arguments") or "{}",
        },
    }


class StreamAccumulator:
    """Collects streamed deltas (text + tool calls) from either backend."""

    def __init__(self):
        self.text_parts: list[str] = []
        self.tool_calls: dict[int, dict] = {}

    def feed(self, chunk) -> str:
        choices = _get(chunk, "choices") or []
        if not choices:
            return ""
        delta = _get(choices[0], "delta") or _get(choices[0], "message") or {}
        piece = _get(delta, "content") or ""
        if piece:
            self.text_parts.append(piece)
        for tc in _get(delta, "tool_calls") or []:
            idx = _get(tc, "index", 0) or 0
            slot = self.tool_calls.setdefault(
                idx, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
            )
            if _get(tc, "id"):
                slot["id"] = _get(tc, "id")
            fn = _get(tc, "function") or {}
            if _get(fn, "name"):
                slot["function"]["name"] += _get(fn, "name")
            if _get(fn, "arguments"):
                slot["function"]["arguments"] += _get(fn, "arguments")
        return piece

    @property
    def text(self) -> str:
        return "".join(self.text_parts)

    def tool_call_list(self) -> list[dict]:
        return [self.tool_calls[i] for i in sorted(self.tool_calls)]


# --------------------------------------------------------------------------
# The agent
# --------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are RATAN, a terminal AI agent that lives inside the user's phone terminal.

Runtime facts (verified, do not contradict them):
{env}

Rules:
1. Answer in Hinglish (Roman-script Hindi + English) when the user writes Hindi/Hinglish, otherwise plain English. Keep replies short and terminal-friendly: no markdown tables, short lines, code in fenced blocks.
2. Verify instead of guessing. For anything about the machine (packages, files, versions, disk, network) call the `shell`, `read_file`, `list_dir` or `search_files` tool first, then answer from the real output.
3. Never invent command output. If a command fails, show the real error and propose the next step.
4. Destructive operations (rm -rf, dd, mkfs, disk or partition tools, forced pushes, piping curl into sh) must be explained and confirmed first; the harness asks the user, so propose them only when truly needed.
5. This is a phone: prefer low-memory, single-command solutions, mention apt/pkg package names exactly, and avoid GUI-only advice.
6. If the user asks for a package or model, use `hf_search_models` or `shell` to check availability before recommending.
7. When you finish a task, say in one line what you ran and what came back.
"""


class Agent:
    def __init__(self, cfg: dict, interactive: bool, auto_approve: bool | None = None,
                 cwd: str | None = None, use_tools: bool | None = None, stream: bool = True):
        self.cfg = cfg
        self.interactive = interactive
        self.cwd = os.path.abspath(cwd or os.getcwd())
        self.auto_approve = bool(cfg["auto_approve"]) if auto_approve is None else auto_approve
        self.use_tools = bool(cfg["tools"]) if use_tools is None else use_tools
        self.stream = stream
        self.env = detect_environment()
        self.messages: list[dict] = [{"role": "system", "content": self.system_prompt()}]
        self.client, self.backend = build_client(cfg)

    # -- prompts -----------------------------------------------------------
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(env=environment_summary(self.env))

    def refresh_system(self) -> None:
        self.env = detect_environment()
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = self.system_prompt()

    # -- approvals ---------------------------------------------------------
    def approve(self, description: str, dangerous: bool = False) -> bool:
        if dangerous:
            if not self.interactive:
                return False
            eprint(red(f"  !! {description}"))
        if self.auto_approve and not dangerous:
            eprint(dim(f"  auto-approved: {description}"))
            return True
        if not self.interactive:
            eprint(yellow(f"  not interactive; refusing: {description} (use --yes to allow)"))
            return False
        try:
            answer = input(yellow(f"  approve? {description} [y/N] ")).strip().lower()
        except EOFError:
            return False
        return answer in ("y", "yes")

    # -- tool dispatch -----------------------------------------------------
    def run_tool(self, name: str, args: dict) -> str:
        try:
            if name == "shell":
                return _run_shell(
                    str(args.get("command", "")),
                    self.cwd,
                    int(args.get("timeout") or DEFAULT_SHELL_TIMEOUT),
                    self.approve,
                )
            if name == "read_file":
                return _read_file(str(args["path"]), self.cwd, int(args.get("max_lines") or 400))
            if name == "write_file":
                return _write_file(str(args["path"]), str(args.get("content", "")), self.cwd, self.approve)
            if name == "list_dir":
                return _list_dir(str(args.get("path") or "."), self.cwd, int(args.get("max_entries") or 200))
            if name == "search_files":
                return _search_files(
                    str(args["pattern"]), str(args.get("path") or "."), self.cwd,
                    int(args.get("max_hits") or 40),
                )
            if name == "sysinfo":
                return environment_summary(detect_environment())
            if name == "hf_search_models":
                return _hf_search_models(
                    str(args.get("search") or ""), int(args.get("limit") or 8), self.cfg.get("token", "")
                )
            return f"unknown tool: {name}"
        except ToolError as exc:
            return f"TOOL ERROR: {exc}"
        except KeyError as exc:
            return f"TOOL ERROR: missing argument {exc}"
        except Exception as exc:  # keep the conversation alive
            return f"TOOL ERROR: {type(exc).__name__}: {exc}"

    def run_user_shell(self, command: str, timeout: int = DEFAULT_SHELL_TIMEOUT) -> str:
        """The `!cmd` shortcut: a command the human typed, not one the model
        proposed - so it runs straight away. Destructive ones still confirm."""

        def approve(description: str, dangerous: bool = False) -> bool:
            return self.approve(description, dangerous=True) if dangerous else True

        try:
            return _run_shell(command, self.cwd, timeout, approve)
        except ToolError as exc:
            return f"TOOL ERROR: {exc}"

    # -- model calls -------------------------------------------------------
    def _call(self, stream: bool):
        kwargs = dict(
            model=self.cfg["model"],
            stream=stream,
            max_tokens=int(self.cfg.get("max_tokens") or 1024),
            temperature=float(self.cfg.get("temperature") or 0.0),
        )
        if self.use_tools:
            kwargs["tools"] = TOOL_SPECS
            kwargs["tool_choice"] = "auto"
        return self.client.chat_completion(self.trimmed_messages(), **kwargs)

    def trimmed_messages(self) -> list[dict]:
        head = self.messages[:1] if self.messages and self.messages[0]["role"] == "system" else []
        body = self.messages[len(head):]
        if len(body) > HISTORY_KEEP:
            body = body[-HISTORY_KEEP:]
        return head + body

    def ask(self, user_text: str, show: bool = True) -> str:
        self.messages.append({"role": "user", "content": user_text})
        final_text = ""
        for _ in range(MAX_TOOL_ROUNDS):
            acc = StreamAccumulator()
            stream = self.stream and self.interactive
            try:
                result = self._call(stream=stream)
            except RuntimeError as exc:
                msg = str(exc)
                eprint(red(f"[ratan] {msg}"))
                if "401" in msg or "403" in msg:
                    eprint(yellow("  -> token missing/invalid. Fix: ratan login   (or export HF_TOKEN=hf_...)"))
                if "429" in msg:
                    eprint(yellow("  -> rate limited on the free tier. Wait a bit, or switch model: ratan --model <id>"))
                return final_text
            if stream:
                for chunk in result:
                    piece = acc.feed(chunk)
                    if piece and show:
                        print(piece, end="", flush=True)
            else:
                acc.feed(_as_single_chunk(result))
            if show and stream and acc.text:
                print()
            tool_calls = acc.tool_call_list()
            if not tool_calls:
                final_text = acc.text
                break
            # model wants tools: keep its (possibly empty) text on the same
            # assistant message that carries the tool calls, then run them
            self.messages.append({
                "role": "assistant",
                "content": acc.text or None,
                "tool_calls": [normalize_tool_call(tc) for tc in tool_calls],
            })
            for tc in tool_calls:
                norm = normalize_tool_call(tc)
                name = norm["function"]["name"]
                raw_args = norm["function"]["arguments"] or "{}"
                try:
                    args = json.loads(raw_args) if raw_args.strip() else {}
                except ValueError:
                    args = {}
                eprint(cyan(f"  [tool] {name} {dim(_short(raw_args, 120))}"))
                output = self.run_tool(name, args)
                if show:
                    eprint(dim(_indent(_short(output, 700))))
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": norm["id"],
                    "content": output,
                })
        else:
            eprint(yellow(f"[ratan] stopped after {MAX_TOOL_ROUNDS} tool rounds"))
        self.messages.append({"role": "assistant", "content": final_text})
        return final_text


def _as_single_chunk(resp) -> dict:
    """Wrap a non-streamed response so StreamAccumulator can read it."""
    msg = choice_message(resp)
    delta = {"role": "assistant", "content": msg["content"]}
    if msg["tool_calls"]:
        delta["tool_calls"] = [
            {"index": i, "id": _get(tc, "id"), "type": "function", "function": _get(tc, "function")}
            for i, tc in enumerate(msg["tool_calls"])
        ]
    return {"choices": [{"delta": delta}]}


def _short(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit] + " ..."


def _indent(text: str, prefix: str = "    | ") -> str:
    return "\n".join(prefix + line for line in (text or "").splitlines()[:12])


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------

def session_file(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "default") or "default"
    return os.path.join(sessions_dir(), f"{safe}.jsonl")


def save_session(messages: list[dict], name: str) -> str:
    os.makedirs(sessions_dir(), exist_ok=True)
    path = session_file(name)
    with open(path, "w", encoding="utf-8") as fh:
        for m in messages:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")
    return path


def load_session(name: str) -> list[dict]:
    path = session_file(name)
    if not os.path.exists(path):
        raise ToolError(f"no session named '{name}' ({path})")
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def list_sessions() -> list[str]:
    if not os.path.isdir(sessions_dir()):
        return []
    return sorted(f[:-6] for f in os.listdir(sessions_dir()) if f.endswith(".jsonl"))


# --------------------------------------------------------------------------
# Subcommands
# --------------------------------------------------------------------------

def cmd_version(_args) -> int:
    env = detect_environment()
    print(f"ratan {VERSION}")
    print(environment_summary(env))
    return 0


def cmd_doctor(_args) -> int:
    cfg = load_config()
    env = detect_environment()
    print(bold("Ratan doctor"))
    print(environment_summary(env))
    print()
    print(f"  config file : {config_path()}{'  (exists)' if os.path.exists(config_path()) else '  (not created yet)'}")
    print(f"  model       : {cfg['model']}")
    print(f"  router      : {cfg.get('base_url') or HF_ROUTER}")
    print(f"  token       : {mask_token(cfg.get('token', ''))}")
    if not cfg.get("token"):
        print(yellow("  -> no token. Get a free one at https://huggingface.co/settings/tokens"))
        print(yellow("     then run: ratan login     (or: export HF_TOKEN=hf_...)"))
    try:
        _, backend = build_client(cfg)
    except Exception as exc:  # RATAN_BACKEND=sdk can raise
        backend = "raw"
        globals()["BACKEND_FALLBACK_REASON"] = f"{type(exc).__name__}: {exc}"
    if backend == "sdk":
        try:
            import huggingface_hub
            print(f"  backend     : sdk (huggingface_hub {huggingface_hub.__version__})")
        except ImportError:
            print("  backend     : sdk (huggingface_hub)")
    else:
        print("  backend     : raw (stdlib urllib, no extra dependency needed)")
        if BACKEND_FALLBACK_REASON:
            print(dim(f"  -> sdk not used: {BACKEND_FALLBACK_REASON}"))

    # Is the termux/ubuntu split correct?
    if env["in_termux"]:
        print(yellow("  -> you are in Termux, not Ubuntu. Install Ubuntu 26.04 with the bundled installer."))
    elif env["container"] == "proot-distro":
        print(green(f"  -> running inside proot-distro ({env['pd_image'] or env['pd_container']}). Good."))

    # Connectivity, only when a token exists so we do not spam the router.
    base = (cfg.get("base_url") or HF_ROUTER).rstrip("/")
    try:
        req = urllib.request.Request(base + "/models?limit=1",
                                     headers={"User-Agent": f"ratan-agent/{VERSION}"})
        if cfg.get("token"):
            req.add_header("Authorization", f"Bearer {cfg['token']}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(green(f"  router      : reachable (HTTP {resp.status})"))
    except urllib.error.HTTPError as exc:
        color = yellow if exc.code in (401, 403) else red
        print(color(f"  router      : HTTP {exc.code} {exc.reason} - check token/permissions"))
    except (urllib.error.URLError, TimeoutError) as exc:
        print(red(f"  router      : unreachable ({exc}) - is mobile data/Wi-Fi on?"))
    print()
    print(dim("  kernel note: proot-distro reports a fixed `uname -r` string; the real kernel is"))
    print(dim("  your phone's Android kernel. Ubuntu 26.04 userspace on the Android kernel is normal."))
    return 0


def cmd_models(args) -> int:
    cfg = load_config()
    query = args.query or ""
    base = (cfg.get("base_url") or HF_ROUTER).rstrip("/")
    url = base + "/models"
    if query:
        url += "?" + urllib.parse.urlencode({"search": query, "limit": args.limit})
    else:
        url += "?" + urllib.parse.urlencode({"limit": args.limit})
    req = urllib.request.Request(url, headers={"User-Agent": f"ratan-agent/{VERSION}"})
    if cfg.get("token"):
        req.add_header("Authorization", f"Bearer {cfg['token']}")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError) as exc:
        print(red(f"could not list models: {exc}"))
        return 1
    models = data.get("data", data if isinstance(data, list) else [])
    if not models:
        print("no models returned")
        return 1
    print(bold(f"Models via {base}{' matching ' + query if query else ''}:"))
    for m in models[: args.limit]:
        mid = m.get("id", "?")
        mark = green("*") if mid == cfg["model"] else " "
        print(f" {mark} {mid}")
    print(dim(f"\nSwitch with:  ratan --model <id>   or   ratan config set model <id>"))
    return 0


def cmd_config(args) -> int:
    cfg = load_config()
    if not args.pairs:
        shown = dict(cfg)
        shown["token"] = mask_token(shown.get("token", ""))
        print(json.dumps(shown, indent=2))
        print(dim(f"# file: {config_path()}"))
        return 0
    for pair in args.pairs:
        if "=" not in pair:
            print(red(f"expected key=value, got: {pair}"))
            return 2
        key, _, value = pair.partition("=")
        key = key.strip()
        value = value.strip()
        if key not in CONFIG_KEYS:
            print(red(f"unknown key '{key}'. Valid: {', '.join(CONFIG_KEYS)}"))
            return 2
        if key in ("max_tokens",):
            value = int(value)
        elif key in ("auto_approve", "tools"):
            value = value.lower() in ("1", "true", "yes", "on")
        elif key == "temperature":
            value = float(value)
        cfg[key] = value
    path = save_config(cfg)
    print(green(f"saved {path}"))
    return 0


def cmd_login(args) -> int:
    cfg = load_config()
    token = args.token or os.environ.get("HF_TOKEN") or ""
    if not token:
        print("Paste a Hugging Face token (read + 'Make calls to Inference Providers').")
        print("Create one at https://huggingface.co/settings/tokens")
        try:
            token = getpass.getpass("HF token (hidden): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
    if not token:
        print(red("no token given; nothing saved"))
        return 1
    cfg["token"] = token
    path = save_config(cfg)
    print(green(f"token saved to {path} (chmod 600)"))
    print(dim("verify with: ratan doctor"))
    return 0


def cmd_ask(args) -> int:
    cfg = load_config()
    cfg["model"] = args.model or cfg["model"]
    text = args.text
    if text in (None, "-", ""):
        text = sys.stdin.read().strip()
    if not text:
        print(red("nothing to ask. Usage: ratan ask \"your question\"   (or pipe text in)"))
        return 2
    if not cfg.get("token"):
        eprint(yellow("[ratan] no HF token set - run: ratan login   (free tier works)"))
    agent = Agent(
        cfg,
        interactive=args.yes or sys.stdin.isatty(),
        auto_approve=True if args.yes else None,
        cwd=args.cwd,
        use_tools=False if args.no_tools else None,
        stream=False,
    )
    if args.session:
        try:
            agent.messages = load_session(args.session)
            if not agent.messages or agent.messages[0]["role"] != "system":
                agent.messages.insert(0, {"role": "system", "content": agent.system_prompt()})
        except ToolError as exc:
            eprint(yellow(f"[ratan] {exc}; starting fresh"))
    out = agent.ask(text)
    if out:
        print(out)
    if args.save:
        print(dim(f"# session saved: {save_session(agent.messages, args.save)}"))
    return 0


HELP_TEXT = f"""{bold('Ratan')} - terminal AI agent (Hugging Face Inference Providers)  v{VERSION}

{bold('USAGE')}
  ratan                      interactive chat in this terminal
  ratan ask "..."            one-shot question, prints the answer
  cat log.txt | ratan ask -  pipe text into a question
  ratan doctor               environment + token + connectivity check
  ratan models [query]       list models the router serves
  ratan config [k=v ...]     show or set config ({', '.join(CONFIG_KEYS)})
  ratan login                save a Hugging Face token
  ratan version              version + environment facts

{bold('FLAGS')}
  --model ID       model id, e.g. openai/gpt-oss-120b:fastest
  --cwd DIR        working dir for shell/file tools
  --yes            approve tool calls automatically (still blocks destructive ones)
  --no-tools       plain chat, no shell/file access
  --session NAME   load/save this named conversation
  --save NAME      save the conversation after a one-shot ask

{bold('IN CHAT')}
  /help /model [id] /models [q] /tools /yes /clear /sysinfo /doctor
  /save [name] /load <name> /sessions /cwd <dir> /exit
  !<command>       run a shell command directly, e.g.  !ls -la
"""


def cmd_chat(args) -> int:
    cfg = load_config()
    cfg["model"] = args.model or cfg["model"]
    if not cfg.get("token"):
        eprint(yellow("[ratan] no HF token yet - answers will fail until you run: ratan login"))
    agent = Agent(
        cfg,
        interactive=True,
        auto_approve=True if args.yes else None,
        cwd=args.cwd,
        use_tools=False if args.no_tools else None,
    )
    session = args.session or cfg.get("session") or "default"
    if args.session:
        try:
            loaded = load_session(session)
            if loaded:
                agent.messages = loaded
                if agent.messages[0]["role"] != "system":
                    agent.messages.insert(0, {"role": "system", "content": agent.system_prompt()})
                eprint(dim(f"[ratan] resumed session '{session}' ({len(loaded)} messages)"))
        except ToolError:
            pass
    eprint(bold(f"Ratan {VERSION}") + dim(f"  model={cfg['model']}  backend={agent.backend}"))
    eprint(dim(f"  {agent.env['where']} | {agent.env['distro'] or agent.env['system']} | cwd={agent.cwd}"))
    eprint(dim("  type /help for commands, !cmd for a shell command, /exit to quit"))
    while True:
        try:
            line = input(cyan("ratan> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.startswith("!"):
            cmd = line[1:].strip()
            if cmd:
                print(agent.run_user_shell(cmd))
            continue
        if line.startswith("/"):
            if _slash_command(agent, line, session) is False:
                break
            continue
        agent.ask(line)
    print(dim("bye."))
    return 0


def _slash_command(agent: Agent, line: str, session: str):
    parts = shlex.split(line)
    cmd, rest = parts[0].lower(), parts[1:]
    if cmd in ("/exit", "/quit", "/q"):
        return False
    if cmd == "/help":
        print(HELP_TEXT)
    elif cmd == "/model":
        if rest:
            agent.cfg["model"] = rest[0]
            agent.client, agent.backend = build_client(agent.cfg)
            print(green(f"model -> {rest[0]}"))
        else:
            print(f"current model: {agent.cfg['model']}")
    elif cmd == "/models":
        ns = argparse.Namespace(query=rest[0] if rest else "", limit=25)
        cmd_models(ns)
    elif cmd == "/tools":
        agent.use_tools = not agent.use_tools
        print(f"tools: {'on' if agent.use_tools else 'off'} ({', '.join(TOOL_NAMES)})")
    elif cmd == "/yes":
        agent.auto_approve = not agent.auto_approve
        state = "ON (destructive commands still ask)" if agent.auto_approve else "OFF"
        print(f"auto-approve: {state}")
    elif cmd == "/clear":
        agent.messages = [{"role": "system", "content": agent.system_prompt()}]
        print("context cleared")
    elif cmd == "/sysinfo":
        agent.refresh_system()
        print(environment_summary(agent.env))
    elif cmd == "/doctor":
        cmd_doctor(None)
    elif cmd == "/cwd":
        if not rest:
            print(agent.cwd)
        else:
            target = os.path.abspath(os.path.expanduser(rest[0]))
            if os.path.isdir(target):
                agent.cwd = target
                print(green(f"cwd -> {target}"))
            else:
                print(red(f"not a directory: {target}"))
    elif cmd == "/save":
        name = rest[0] if rest else session
        print(green(f"saved {save_session(agent.messages, name)}"))
    elif cmd == "/load":
        if not rest:
            print(red("usage: /load <name>   (see /sessions)"))
        else:
            try:
                agent.messages = load_session(rest[0])
                agent.refresh_system()
                print(green(f"loaded {len(agent.messages)} messages from '{rest[0]}'"))
            except ToolError as exc:
                print(red(str(exc)))
    elif cmd == "/sessions":
        names = list_sessions()
        print("\n".join(names) if names else "no saved sessions")
    elif cmd == "/config":
        cmd_config(argparse.Namespace(pairs=rest))
    else:
        print(red(f"unknown command: {cmd} (try /help)"))
    return True


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ratan",
        description="Ratan - terminal AI agent for your phone, powered by Hugging Face.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_TEXT,
    )
    p.add_argument("--version", action="version", version=f"ratan {VERSION}")
    sub = p.add_subparsers(dest="command")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", help="Hugging Face model id (e.g. openai/gpt-oss-120b:fastest)")
    common.add_argument("--cwd", help="working directory for shell/file tools")
    common.add_argument("--yes", "-y", action="store_true", help="auto-approve tool calls")
    common.add_argument("--no-tools", action="store_true", help="disable shell/file tools")

    chat = sub.add_parser("chat", parents=[common], help="interactive terminal chat (default)")
    chat.add_argument("--session", help="resume/save this named session")
    chat.set_defaults(func=cmd_chat)

    ask = sub.add_parser("ask", parents=[common], help="one-shot question")
    ask.add_argument("text", nargs="?", help='question, or "-" to read stdin')
    ask.add_argument("--session", help="continue this named session")
    ask.add_argument("--save", help="save the conversation under this name")
    ask.set_defaults(func=cmd_ask)

    doctor = sub.add_parser("doctor", help="check environment, token and connectivity")
    doctor.set_defaults(func=cmd_doctor)

    models = sub.add_parser("models", help="list models served by the router")
    models.add_argument("query", nargs="?", default="")
    models.add_argument("--limit", type=int, default=25)
    models.set_defaults(func=cmd_models)

    conf = sub.add_parser("config", help="show or set config values")
    conf.add_argument("pairs", nargs="*", help="key=value pairs")
    conf.set_defaults(func=cmd_config)

    login = sub.add_parser("login", help="save a Hugging Face token")
    login.add_argument("token", nargs="?", help="token (prompts if omitted)")
    login.set_defaults(func=cmd_login)

    ver = sub.add_parser("version", help="version and environment facts")
    ver.set_defaults(func=cmd_version)

    # `ratan` with no subcommand -> chat
    p.add_argument("--model", dest="top_model", help=argparse.SUPPRESS)
    p.add_argument("--cwd", dest="top_cwd", help=argparse.SUPPRESS)
    p.add_argument("--yes", "-y", dest="top_yes", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--no-tools", dest="top_no_tools", action="store_true", help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help", "help"):
        print(HELP_TEXT)
        return 0
    if argv and argv[0] == "--version":
        return cmd_version(None)
    parser = build_parser()
    # bare "ratan ..." with flags and no subcommand -> treat as chat
    known_subcommands = {"chat", "ask", "doctor", "models", "config", "login", "version"}
    if argv and argv[0] not in known_subcommands and not argv[0].startswith("-"):
        argv = ["ask"] + argv
    elif not any(a in known_subcommands for a in argv):
        argv = ["chat"] + argv
    args = parser.parse_args(argv)
    if args.command == "chat" and getattr(args, "top_model", None):
        args.model = args.model or args.top_model
        args.cwd = args.cwd or args.top_cwd
        args.yes = args.yes or args.top_yes
        args.no_tools = args.no_tools or args.top_no_tools
    func = getattr(args, "func", cmd_chat)
    try:
        return func(args) or 0
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == "__main__":
    sys.exit(main())

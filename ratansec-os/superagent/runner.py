"""v2 execution boundary.

The 139-entry catalog remains a reference/install map. Executable adapters are
limited to three fixed, argv-only reconnaissance commands. Raw shell, arbitrary
flags, package installation and exploit frameworks are intentionally unavailable.
"""
from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from . import audit, catalog, scope
from .settings import quote, settings

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
SAFE_ADAPTERS = {"dig", "whois", "nmap"}
DNS_RECORDS = {"A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME", "CAA"}
SAFE_PORTS = {21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995, 3306, 5432, 6379, 8080, 8443, 27017}


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text or "")


def which(binary: str) -> str | None:
    return shutil.which(binary)


class BuildError(ValueError):
    pass


@dataclass
class Command:
    id: str
    argv: list[str]
    display: str
    mode: str
    tool: str = ""
    target: str = ""
    section: str = ""
    timeout: int = 30
    label: str = ""
    actor: str = ""
    roe_id: str = ""


@dataclass
class CommandResult:
    id: str
    display: str
    mode: str
    tool: str
    target: str
    status: str = "queued"
    exit_code: int | None = None
    output: str = ""
    truncated: bool = False
    error: str | None = None
    duration: float = 0.0
    started: float | None = None
    finished: float | None = None
    actor: str = ""
    _proc: Any = None

    def view(self, tail: int | None = None) -> dict[str, Any]:
        out = self.output[-tail:] if tail else self.output
        return {"id": self.id, "display": self.display, "mode": self.mode, "tool": self.tool,
                "target": self.target, "status": self.status, "exit_code": self.exit_code,
                "output": out, "truncated": self.truncated, "error": self.error,
                "duration": self.duration, "started": self.started, "finished": self.finished}


def build_tool_command(tool_name: str, *, target: str = "", flags: dict[str, Any] | None = None,
                       raw_args: list[str] | None = None, label: str = "", actor: str = "",
                       timeout: int | None = None) -> Command:
    name = tool_name.strip().lower()
    if name not in SAFE_ADAPTERS:
        raise BuildError(f"'{name}' is catalog reference only in v2. Executable adapters: dig, whois, nmap. Use bounded missions for web/TLS checks.")
    if raw_args:
        raise BuildError("Raw arguments are disabled.")
    flags = dict(flags or {})
    allowed = {"dig": {"record"}, "whois": set(), "nmap": {"ports"}}[name]
    if set(flags) - allowed:
        raise BuildError(f"Unsupported flags for {name}. Allowed: {sorted(allowed) or 'none'}.")
    decision = scope.check(target, "recon")
    if not decision.allowed or not decision.roe_id:
        raise BuildError(decision.reason)
    parsed = decision.target or scope.parse_target(target)
    if parsed.is_cidr:
        raise BuildError("CIDR scans are disabled; authorize and test one host at a time.")
    host = parsed.host
    if name == "dig":
        record = str(flags.get("record", "A")).upper()
        if record not in DNS_RECORDS:
            raise BuildError(f"DNS record must be one of {sorted(DNS_RECORDS)}.")
        argv = ["dig", "+time=3", "+tries=1", "+short", "-t", record, host]
    elif name == "whois":
        argv = ["whois", host]
    else:
        raw_ports = str(flags.get("ports", "80,443"))
        if not re.fullmatch(r"\d+(?:,\d+){0,15}", raw_ports):
            raise BuildError("Ports must be a comma-separated list (max 16), not a range.")
        ports = [int(p) for p in raw_ports.split(",")]
        if any(p not in SAFE_PORTS for p in ports):
            raise BuildError(f"Ports must be within the safe service list: {sorted(SAFE_PORTS)}.")
        # Pin the validated address so a second DNS lookup cannot redirect the
        # scan to a different host. -sT needs no raw-socket privileges.
        from .probes import resolve_pinned
        pinned, _ = resolve_pinned(parsed)
        argv = ["nmap", "-sT", "-Pn", "-n", "--max-retries", "1", "--host-timeout", "45s",
                "-p", ",".join(str(p) for p in ports), pinned]
    return Command(id=f"cmd-{uuid.uuid4().hex[:10]}", argv=argv, display=quote(argv), mode="adapter",
                   tool=name, target=parsed.raw, section="recon", actor=actor, roe_id=decision.roe_id,
                   timeout=max(5, min(int(timeout or settings.default_timeout), settings.max_cmd_seconds)),
                   label=label or f"{name} {host}")


def shell_blocked_reason(command: str) -> str:
    return "Raw shell is retired in v2. Use a bounded mission or the dig/whois/nmap adapters."


def build_shell_command(command: str, **kwargs: Any) -> Command:
    raise BuildError(shell_blocked_reason(command))


class CommandManager:
    def __init__(self) -> None:
        self._items: dict[str, CommandResult] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=settings.max_concurrent, thread_name_prefix="adapter")

    def submit(self, command: Command, *, approval_id: str = "") -> CommandResult:
        from . import approvals
        ap = approvals.get(approval_id)
        if ap is None or ap.status != "approved" or ap.command != command.display or ap.actor != command.actor:
            raise BuildError("A matching human approval is required before execution.")
        decision = scope.check(command.target, command.section)
        if not decision.allowed or decision.roe_id != command.roe_id:
            raise BuildError("Authorization changed; execution refused.")
        result = CommandResult(id=command.id, display=command.display, mode=command.mode,
                               tool=command.tool, target=command.target, actor=command.actor)
        with self._lock:
            self._items[command.id] = result
        self._pool.submit(self._run, command, result)
        return result

    def _run(self, command: Command, result: CommandResult) -> None:
        from .provider import redact
        started = time.time()
        result.status, result.started = "running", started
        audit.log("adapter_start", evidence=True, cmd_id=command.id, tool=command.tool,
                  target=command.target, display=command.display, actor=command.actor)
        if which(command.argv[0]) is None:
            result.status, result.error, result.finished = "error", f"'{command.argv[0]}' installed nahi hai.", time.time()
            audit.log("adapter_missing", cmd_id=command.id, binary=command.argv[0])
            return
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "TERM": "dumb", "NO_COLOR": "1",
               "LC_ALL": "C.UTF-8", "HOME": str(settings.data_dir)}
        try:
            proc = subprocess.Popen(command.argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, text=True, errors="replace", bufsize=1,
                                    start_new_session=True, cwd=str(settings.data_dir), env=env)
        except OSError:
            result.status, result.error, result.finished = "error", "Adapter start nahi hua.", time.time()
            return
        result._proc = proc
        buffer: deque[str] = deque()
        size = 0
        truncated = False

        def pump() -> None:
            nonlocal size, truncated
            assert proc.stdout is not None
            for line in proc.stdout:
                clean = redact(strip_ansi(line))
                if size + len(clean) <= settings.max_output_chars:
                    buffer.append(clean)
                    size += len(clean)
                else:
                    truncated = True
        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        timed_out = False
        try:
            proc.wait(timeout=command.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._kill(proc)
        reader.join(timeout=2)
        result.output = "".join(buffer)
        result.truncated, result.exit_code = truncated, proc.returncode
        result.duration, result.finished = round(time.time() - started, 2), time.time()
        if timed_out:
            result.status, result.error = "timeout", "Timeout — process group killed."
        elif result.status == "cancelled":
            pass
        elif proc.returncode == 0:
            result.status = "done"
        else:
            result.status, result.error = "error", f"exit code {proc.returncode}"
        audit.log("adapter_end", evidence=True, cmd_id=command.id, status=result.status,
                  exit_code=result.exit_code, duration=result.duration, truncated=truncated)

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except OSError:
            return
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError:
                pass

    def get(self, cmd_id: str) -> CommandResult | None:
        with self._lock:
            return self._items.get(cmd_id)

    def cancel(self, cmd_id: str, actor: str) -> bool:
        with self._lock:
            item = self._items.get(cmd_id)
            if item is None or item.actor != actor:
                return False
            if item.status in {"queued", "running"}:
                item.status = "cancelled"
                if item._proc is not None:
                    self._kill(item._proc)
                audit.log("adapter_cancel", evidence=True, cmd_id=cmd_id, actor=actor)
            return True

    def list(self, limit: int = 50, actor: str | None = None) -> list[CommandResult]:
        with self._lock:
            items = sorted(self._items.values(), key=lambda r: r.started or 0, reverse=True)
        if actor is not None:
            items = [i for i in items if i.actor == actor]
        return items[:limit]


commands = CommandManager()

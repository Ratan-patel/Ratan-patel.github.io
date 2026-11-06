"""Runner — commands ko argv style me chalata hai (shell injection impossible).

Do modes:
  * tool  : catalog ke tool + allowed flags (default, safest)
  * shell : raw command string — sirf jab ALLOW_SHELL=1 + session switch ON
            (+ blocklist + approval). Linux terminal-feel ke liye.

Sab kuch thread pool me chalta hai, live output stream hota hai, cancel possible,
aur har command audit + evidence me record hoti hai.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from . import audit, catalog
from .settings import SHELL_BLOCKLIST, quote, settings

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
_shell_blocks = [re.compile(p) for p in SHELL_BLOCKLIST]


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text or "")


def which(binary: str) -> str | None:
    return shutil.which(binary)


# ---------------------------------------------------------------------------
# Command model
# ---------------------------------------------------------------------------
@dataclass
class Command:
    id: str
    argv: list[str]
    display: str
    mode: str                     # tool | shell
    tool: str = ""
    target: str = ""
    section: str = ""
    timeout: int = 120
    label: str = ""
    actor: str = ""


@dataclass
class CommandResult:
    id: str
    display: str
    mode: str
    tool: str
    target: str
    status: str = "queued"        # queued|running|done|error|timeout|cancelled|blocked
    exit_code: int | None = None
    output: str = ""
    truncated: bool = False
    error: str | None = None
    duration: float = 0.0
    started: float | None = None
    finished: float | None = None
    _proc: Any = None

    def view(self, tail: int | None = None) -> dict[str, Any]:
        out = self.output
        if tail:
            out = out[-tail:]
        return {
            "id": self.id, "display": self.display, "mode": self.mode, "tool": self.tool,
            "target": self.target, "status": self.status, "exit_code": self.exit_code,
            "output": out, "truncated": self.truncated, "error": self.error,
            "duration": self.duration, "started": self.started, "finished": self.finished,
        }


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
class BuildError(ValueError):
    pass


_FLAG_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]{0,40}$")

# ye tools positional target lete hain (inhe --flag=value nahi chahiye)
_POSITIONAL_VALUE = {
    "-x", "-h", "-u", "-d", "-e", "-q", "-t", "-w", "-b", "-p", "-s",
}
_TARGET_ONLY = {
    # DNS / IP / host-only tools (URL nahi, hostname chahiye)
    "whois", "dig", "host", "nslookup", "ping", "traceroute", "masscan", "snmpwalk",
    "snmp-check", "onesixtyone", "nbtscan", "enum4linux", "enum4linux-ng", "dmitry",
    "fierce", "dnsrecon", "nfs-ls", "showmount", "rpcclient", "smbclient", "smbmap",
    "sslyze", "sslscan", "testssl.sh", "hydra", "medusa", "ncrack", "routersploit",
    "nmap", "nmap-vuln", "nmap-http", "dnsx", "subfinder", "assetfinder", "findomain",
    "sublist3r", "amass", "shuffledns", "gau", "waybackurls", "cloud_enum", "sherlock",
    "bettercap", "responder", "airmon-ng", "airodump-ng", "aireplay-ng", "wifite",
}
# offline tools ka "target" free-text hota hai (jaise searchsploit query)
_FREE_TEXT_TOOLS = {"searchsploit", "searchsploit-poc", "hashid", "jq", "sha256sum", "gpg-sign"}

_WORDLIST_TOOLS = {"gobuster-dir", "gobuster-dns", "ffuf", "feroxbuster", "dirsearch", "shuffledns", "hashcat", "john"}

_WORDLIST_CANDIDATES = (
    "/usr/share/seclists/Discovery/Web-Content/common.txt",
    "/usr/share/wordlists/dirb/common.txt",
    "/usr/share/dirb/wordlists/common.txt",
    "/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-small.txt",
    "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
    "/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-100.txt",
    str(Path(__file__).resolve().parent / "wordlists" / "common.txt"),
)


def find_wordlist() -> str | None:
    for candidate in _WORDLIST_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None
_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:/=,+@%\[\]\-]{0,300}$")
# offline/free-text tokens (hash, CVE query) — shell nahi hota, sirf arg list
_FREE_ARG_RE = re.compile(r"^[A-Za-z0-9_.:/=,+@%\[\]$!()\-]{1,200}$")


def _flag_value(value: Any) -> str:
    text = str(value)
    if not _VALUE_RE.match(text):
        raise BuildError(f"Flag value me unexpected characters: {text[:40]!r}. (Sirf [A-Za-z0-9_.:/=,+@%-] allowed)")
    return text


_URL_FLAG = {
    "ffuf": "-u", "gobuster": "-u", "feroxbuster": "-u", "dirsearch": "-u",
    "nikto": "-h", "nuclei": "-u", "wpscan": "--url", "katana": "-u", "httpx": "-u",
    "wapiti": "-u", "zaproxy": "-quickurl", "gospider": "-s", "commix": "--url",
    "xsstrike": "-u", "arjun": "-u", "sqlmap": "--url", "joomscan": "-u",
    "masscan": "", "curl": "", "wget": "", "nc": "", "openssl": "", "ssh": "",
}
_SHORT_FLAGS = {
    "record": "-t", "ports": "-p", "port": "-p", "tuning": "-T", "severity": "-severity",
    "depth": "-d", "threads": "-t", "extensions": "-x", "wordlist": "-w", "rate": "--rate",
}


def build_tool_command(
    tool_name: str,
    *,
    target: str = "",
    flags: dict[str, Any] | None = None,
    raw_args: list[str] | None = None,
    label: str = "",
    actor: str = "",
    timeout: int | None = None,
) -> Command:
    """Catalog tool ko safe argv me convert karo (koi shell, koi injection nahi)."""
    tool = catalog.TOOLS.get(tool_name.strip().lower())
    if tool is None:
        raise BuildError(f"'{tool_name}' catalog me nahi hai. /api/sections se valid list dekho.")
    flags = dict(flags or {})
    argv: list[str] = [tool.binary] + list(tool.default_args)

    target_token = ""
    free_text: list[str] = []
    if target and (tool.offline or tool.name in _FREE_TEXT_TOOLS):
        # offline tools: hash / query / file — shell nahi, isliye permissive but safe
        for token in target.split():
            if not _FREE_ARG_RE.match(token):
                raise BuildError(f"Query me allowed nahi characters: {token[:40]}")
            free_text.append(token)
    elif target:
        from .scope import parse_target

        parsed = parse_target(target)
        if parsed.is_cidr:
            target_token = parsed.raw
        elif tool.name in _TARGET_ONLY:
            target_token = parsed.host
        elif tool.name in ("sqlmap", "commix", "xsstrike", "arjun", "wapiti", "jwt_tool"):
            target_token = parsed.raw if parsed.raw.startswith("http") else (parsed.url or parsed.host)
        else:
            target_token = parsed.url or parsed.host

    special = tool.name in ("hydra", "medusa")

    for name, value in flags.items():
        if not _FLAG_NAME_RE.match(name):
            raise BuildError(f"Invalid flag name: {name}")
        if name not in tool.flags:
            raise BuildError(
                f"'{tool.name}' ke liye '{name}' flag allowed nahi. Allowed: {', '.join(tool.flags) or '(none)'}"
            )
        if special:
            continue  # hydra/medusa ke flags neeche handle hote hain
        if name == "wordlist" or name in ("user", "passlist", "hash", "userlist", "api_token"):
            # ye value + wordlist special handling me jaate hain
            if name == "wordlist":
                continue
        if isinstance(value, bool):
            if value:
                argv.append(f"--{name}")
            continue
        if value in ("", None):
            argv.append(f"--{name}")
            continue
        val = _flag_value(value)
        if tool.name == "hashcat" and name == "mode":
            argv.extend(["-m", val])
            continue
        if tool.name == "john" and name == "format":
            argv.append(f"--format={val}")
            continue
        short = _SHORT_FLAGS.get(name)
        if short:
            argv.extend([short, val])
        elif name in ("mode", "service", "type", "module", "protocol"):
            argv.append(val)
        else:
            argv.extend([f"--{name}", val])

    if raw_args:
        for item in raw_args[:25]:
            token = str(item)
            if token.startswith("-") and not token.startswith("--"):
                if not re.match(r"^-[A-Za-z0-9][A-Za-z0-9=.,:/_\-]{0,60}$", token):
                    raise BuildError(f"Invalid raw flag: {token[:40]}")
            elif not _VALUE_RE.match(token):
                raise BuildError(f"Raw arg me unexpected characters: {token[:40]}")
            argv.append(token)

    # ---- wordlist ----
    if tool.name in _WORDLIST_TOOLS:
        user_wl = flags.get("wordlist")
        wl = _flag_value(user_wl) if user_wl else find_wordlist()
        if not wl:
            raise BuildError(
                f"'{tool.name}' ke liye wordlist chahiye. `apt-get install seclists wordlists` chalao "
                "ya flags me wordlist=/path/list.txt do."
            )
        if "-w" not in argv and "--wordlist" not in argv:
            argv.extend(["-w", wl])
        if tool.name == "ffuf" and target_token and "FUZZ" not in target_token:
            target_token = target_token.rstrip("/") + "/FUZZ"

    # ---- hydra / medusa (service://target syntax) ----
    if special and target_token:
        service = str(flags.get("service") or flags.get("module") or "ssh")
        if not re.match(r"^[a-z0-9_\-]{2,24}$", service):
            raise BuildError("hydra/medusa ke liye service valid hona chahiye (ssh/ftp/rdp/http-get-form…).")
        user = str(flags.get("user") or "").strip()
        userlist = str(flags.get("userlist") or "").strip()
        if userlist:
            argv.extend(["-L", _flag_value(userlist)])
        elif user:
            argv.extend(["-l", _flag_value(user)])
        else:
            raise BuildError("hydra/medusa ke liye flags me user ya userlist do (authorized account).")
        passlist = str(flags.get("passlist") or "").strip()
        wl = _flag_value(passlist) if passlist else find_wordlist()
        if not wl:
            raise BuildError("hydra/medusa ke liye passlist chahiye (flags: passlist=/path/list.txt).")
        argv.extend(["-P", wl])
        argv.append(f"{service}://{target_token}")
        target_token = ""

    argv.extend(free_text)

    # ---- target placement ----
    if target_token and target_token not in argv:
        url_flag = _URL_FLAG.get(tool.name)
        if url_flag:
            argv.extend([url_flag, target_token])
        elif tool.name == "sqlmap":
            argv.extend(["--url", target_token])
        else:
            argv.append(target_token)

    if not target and not tool.offline and tool.section not in ("utility", "reporting", "cracking", "privilege"):
        raise BuildError(f"'{tool.name}' ke liye target chahiye (authorized scope se).")

    return Command(
        id=f"cmd-{uuid.uuid4().hex[:10]}",
        argv=argv,
        display=quote(argv),
        mode="tool",
        tool=tool.name,
        target=target or "",
        section=tool.section,
        timeout=int(timeout or settings.default_timeout),
        label=label or f"{tool.name} {target or ''}".strip(),
        actor=actor,
    )


def shell_blocked_reason(command: str) -> str | None:
    text = command.strip()
    if not text:
        return "Command khali hai."
    if len(text) > 4000:
        return "Command bahut lamba hai (max 4000 chars)."
    for pattern in _shell_blocks:
        if pattern.search(text):
            return "Yeh command destructive pattern se match karti hai — Super Agent isse block karta hai."
    return None


def build_shell_command(command: str, *, label: str = "", actor: str = "", timeout: int | None = None) -> Command:
    reason = shell_blocked_reason(command)
    if reason:
        raise BuildError(reason)
    return Command(
        id=f"sh-{uuid.uuid4().hex[:10]}",
        argv=["/bin/bash", "-lc", command.strip()],
        display=command.strip(),
        mode="shell",
        tool="shell",
        timeout=int(timeout or settings.default_timeout),
        label=label or "shell",
        actor=actor,
    )


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------
class CommandManager:
    def __init__(self) -> None:
        self._items: dict[str, CommandResult] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=settings.max_concurrent, thread_name_prefix="agent-cmd")
        self._sem = threading.Semaphore(settings.max_concurrent)

    # ---- run ------------------------------------------------------------
    def submit(self, command: Command) -> CommandResult:
        result = CommandResult(
            id=command.id, display=command.display, mode=command.mode,
            tool=command.tool, target=command.target,
        )
        with self._lock:
            self._items[command.id] = result
        self._pool.submit(self._run, command, result)
        return result

    def _run(self, command: Command, result: CommandResult) -> None:
        started = time.time()
        result.status = "running"
        result.started = started
        audit.log(
            "cmd_start", cmd_id=command.id, mode=command.mode, tool=command.tool,
            target=command.target, display=command.display, actor=command.actor, section=command.section,
        )
        if command.mode == "tool":
            binary = command.argv[0]
            if which(binary) is None:
                result.status = "error"
                tool = catalog.TOOLS.get(command.tool)
                hint = (tool.install_hint if tool else "") or f"apt-get install -y {tool.package if tool else binary}"
                result.error = f"'{binary}' installed nahi hai. Install: {hint}"
                result.finished = time.time()
                audit.log("cmd_missing_binary", cmd_id=command.id, binary=binary, hint=hint)
                return

        with self._sem:
            env = {
                **os.environ,
                "TERM": "dumb",
                "NO_COLOR": "1",
                "PYTHONUNBUFFERED": "1",
            }
            try:
                proc = subprocess.Popen(
                    command.argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    errors="replace",
                    bufsize=1,
                    start_new_session=True,
                    cwd="/tmp",
                    env=env,
                )
            except (OSError, ValueError) as exc:
                result.status = "error"
                result.error = f"Command start nahi hui: {exc}"
                result.finished = time.time()
                return

            result._proc = proc
            buffer: deque[str] = deque()
            size = 0
            limit = settings.max_output_chars
            truncated = False

            def pump() -> None:
                nonlocal size, truncated
                assert proc.stdout is not None
                for line in proc.stdout:
                    clean = strip_ansi(line)
                    if size < limit:
                        buffer.append(clean)
                        size += len(clean)
                    else:
                        truncated = True

            reader = threading.Thread(target=pump, daemon=True)
            reader.start()

            timed_out = False
            try:
                proc.wait(timeout=max(5, min(command.timeout, settings.max_cmd_seconds)))
            except subprocess.TimeoutExpired:
                timed_out = True
                self._kill(proc)

            reader.join(timeout=5)
            output = "".join(buffer)
            result.output = output
            result.truncated = truncated
            result.exit_code = proc.returncode
            result.duration = round(time.time() - started, 2)
            result.finished = time.time()
            if timed_out:
                result.status = "timeout"
                result.error = f"Timeout — {command.timeout}s ke andar khatam nahi hua (process kill kiya)."
            elif proc.returncode == 0:
                result.status = "done"
            else:
                result.status = "error"
                result.error = f"exit code {proc.returncode}"

            audit.log(
                "cmd_end", cmd_id=command.id, status=result.status, exit_code=result.exit_code,
                duration=result.duration, chars=len(output), truncated=truncated, actor=command.actor,
            )

    @staticmethod
    def _kill(proc: subprocess.Popen) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except OSError:
            try:
                proc.terminate()
            except OSError:
                pass
        time.sleep(0.4)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            try:
                proc.kill()
            except OSError:
                pass

    # ---- read / control -------------------------------------------------
    def get(self, cmd_id: str) -> CommandResult | None:
        with self._lock:
            return self._items.get(cmd_id)

    def cancel(self, cmd_id: str) -> bool:
        item = self.get(cmd_id)
        if item is None:
            return False
        if item._proc is not None:
            self._kill(item._proc)
        item.status = "cancelled"
        audit.log("cmd_cancel", cmd_id=cmd_id)
        return True

    def list(self, limit: int = 50) -> list[CommandResult]:
        with self._lock:
            items = sorted(self._items.values(), key=lambda r: r.started or 0, reverse=True)
        return items[:limit]


commands = CommandManager()

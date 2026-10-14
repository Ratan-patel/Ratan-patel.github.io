"""Executor — commands chalao, runs manage karo (background threads ke saath).

Design:
  * Sirf argv-based subprocess (shell=False) — injection impossible.
  * Har step ka timeout + output cap.
  * Run ki state in-memory (free tier par disk ephemeral hota hai).
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from . import audit
from .config import settings
from .security import scan_semaphore
from .tools import TOOLS, Step, resolve_tool

_TRUNCATE_HEAD = 30000
_TRUNCATE_TAIL = 20000


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if text is None:
        return "", False
    if len(text) <= limit:
        return text, False
    head = text[: min(_TRUNCATE_HEAD, limit)]
    tail = text[-min(_TRUNCATE_TAIL, max(0, limit - len(head))):]
    return f"{head}\n\n... [output truncated — total {len(text):,} chars] ...\n\n{tail}", True


def run_command(argv: list[str], timeout: int, max_chars: int | None = None) -> dict[str, Any]:
    """Ek command chalao. Returns dict: status, exit_code, output, duration."""
    limit = max_chars or settings.max_output_chars
    started = time.time()
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            errors="replace",
            start_new_session=True,
            cwd="/tmp",
        )
    except (OSError, ValueError) as exc:
        return {"status": "error", "exit_code": None, "output": "", "error": str(exc), "duration": 0.0, "proc": None}

    try:
        out, _ = proc.communicate(timeout=timeout)
        status = "done" if proc.returncode == 0 else "error"
        error = None if proc.returncode == 0 else f"exit code {proc.returncode}"
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        try:
            out, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out = ""
        status, error = "timeout", f"timeout ({timeout}s ke andar khatam nahi hua)"
    except Exception as exc:  # pragma: no cover - defensive
        _kill_group(proc)
        out, status, error = "", "error", str(exc)

    text, truncated = _truncate(out or "", limit)
    return {
        "status": status,
        "exit_code": proc.returncode if proc.returncode is not None else None,
        "output": text,
        "truncated": truncated,
        "error": error,
        "duration": round(time.time() - started, 2),
        "proc": proc,
    }


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.terminate()
        except Exception:
            pass
    time.sleep(0.5)
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Run model
# --------------------------------------------------------------------------
@dataclass
class RunStep:
    index: int
    tool: str
    label: str
    command: str
    status: str = "pending"          # pending|running|done|error|timeout|skipped|cancelled
    exit_code: int | None = None
    output: str = ""
    truncated: bool = False
    error: str | None = None
    duration: float = 0.0
    started: float | None = None


@dataclass
class Run:
    id: str
    target: str
    profile: str
    source: str                       # ui | cli | agent
    actor: str
    created: float
    status: str = "queued"            # queued|running|done|cancelled|error
    steps: list[RunStep] = field(default_factory=list)
    note: str = ""
    current_proc: Any = None
    cancel_requested: bool = False
    finished: float | None = None

    # ---- views ----------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        done = sum(1 for s in self.steps if s.status in ("done",))
        return {
            "id": self.id,
            "target": self.target,
            "profile": self.profile,
            "source": self.source,
            "actor": self.actor,
            "created": self.created,
            "finished": self.finished,
            "status": self.status,
            "steps_total": len(self.steps),
            "steps_done": done,
            "note": self.note,
        }

    def detail(self, include_output: bool = True) -> dict[str, Any]:
        data = self.summary()
        steps = []
        for s in self.steps:
            item = asdict(s)
            if not include_output:
                item["output"] = item["output"][:2000]
            steps.append(item)
        data["steps"] = steps
        return data

    def compact_report(self, max_chars_per_step: int = 6000) -> str:
        """Agent ko dene ke liye compact text view."""
        lines = [f"RUN {self.id} | target={self.target} | profile={self.profile} | status={self.status}"]
        for s in self.steps:
            lines.append(f"\n[{s.index + 1}] {s.label}\n$ {s.command}\nstatus={s.status} exit={s.exit_code} dur={s.duration}s")
            if s.output:
                body, _ = _truncate(s.output, max_chars_per_step)
                lines.append(body)
            if s.error:
                lines.append(f"error: {s.error}")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Run manager
# --------------------------------------------------------------------------
class RunManager:
    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    # ---- create ---------------------------------------------------------
    def create(self, target: str, steps: list[Step], source: str, actor: str, profile: str = "custom") -> Run:
        run = Run(
            id=uuid.uuid4().hex[:12],
            target=target,
            profile=profile,
            source=source,
            actor=actor,
            created=time.time(),
        )
        for i, step in enumerate(steps):
            spec = TOOLS.get(step.tool)
            run.steps.append(
                RunStep(
                    index=i,
                    tool=step.tool,
                    label=step.label,
                    command=step.display() if spec else " ".join([step.tool] + step.args),
                )
            )
        with self._lock:
            self._runs[run.id] = run
        return run

    # ---- execution ------------------------------------------------------
    def start_background(self, run: Run, steps: list[Step]) -> Run:
        thread = threading.Thread(target=self._execute, args=(run, steps), daemon=True, name=f"run-{run.id}")
        thread.start()
        return run

    def execute_sync(self, run: Run, steps: list[Step]) -> Run:
        self._execute(run, steps)
        return run

    def _execute(self, run: Run, steps: list[Step]) -> None:
        with scan_semaphore:
            run.status = "running"
            audit.log("run_start", run=run.id, target=run.target, profile=run.profile, source=run.source, actor=run.actor)
            for step, run_step in zip(steps, run.steps):
                if run.cancel_requested:
                    run_step.status = "cancelled"
                    run.status = "cancelled"
                    break

                spec = resolve_tool(step.tool)
                if spec is None:
                    run_step.status = "skipped"
                    run_step.error = f"unknown tool '{step.tool}'"
                    continue
                if not spec.installed():
                    run_step.status = "skipped"
                    run_step.error = (
                        f"'{spec.binary}' install nahi hai. Install: apt-get install -y {spec.package} "
                        f"(ya Docker image use karo — sab tools pre-installed hain)."
                    )
                    continue

                run_step.status = "running"
                run_step.started = time.time()
                audit.log("cmd", run=run.id, tool=step.tool, cmd=run_step.command, actor=run.actor)
                result = run_command([spec.binary] + list(step.args), timeout=min(step.timeout, settings.max_scan_seconds))
                run.current_proc = result.get("proc")
                run_step.status = result["status"]
                run_step.exit_code = result["exit_code"]
                run_step.output = result["output"]
                run_step.truncated = result.get("truncated", False)
                run_step.error = result["error"]
                run_step.duration = result["duration"]
                if run.cancel_requested and run_step.status in ("running", "timeout"):
                    run_step.status = "cancelled"

            if run.status != "cancelled":
                all_skipped = bool(run.steps) and all(s.status == "skipped" for s in run.steps)
                run.status = "error" if all_skipped else "done"
            run.finished = time.time()
            audit.log("run_end", run=run.id, target=run.target, status=run.status, actor=run.actor)

    # ---- read / control -------------------------------------------------
    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def list(self, limit: int = 50) -> list[Run]:
        with self._lock:
            runs = sorted(self._runs.values(), key=lambda r: r.created, reverse=True)
        return runs[: max(1, min(limit, 200))]

    def cancel(self, run_id: str) -> bool:
        run = self.get(run_id)
        if not run:
            return False
        run.cancel_requested = True
        proc = run.current_proc
        if proc is not None:
            _kill_group(proc)
        audit.log("run_cancel", run=run.id, actor=run.actor)
        return True

    def delete(self, run_id: str) -> bool:
        with self._lock:
            return self._runs.pop(run_id, None) is not None


runs = RunManager()

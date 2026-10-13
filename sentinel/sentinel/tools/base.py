"""Tool plumbing: context, registry, rate limiting, findings.

Every tool returns the same shape so the agent loop and the report generator do
not need to know which tool produced what:

    {
      "tool": "http_audit",
      "target": "https://example.test",
      "ok": true,
      "findings": [Finding...],
      "data": {...},          # tool-specific detail
      "error": null
    }
"""

from __future__ import annotations

import dataclasses
import json
import threading
import time
from typing import Any, Callable, Iterable, Sequence

from ..authz import Guard
from ..providers import ToolSpec
from ..scope import Scope

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclasses.dataclass
class Finding:
    """One observable condition, with a remediation and a reference."""

    title: str
    severity: str            # info | low | medium | high | critical
    detail: str = ""
    remediation: str = ""
    reference: str = ""
    evidence: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(f"bad severity {self.severity!r}")

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @property
    def rank(self) -> int:
        return SEVERITY_ORDER[self.severity]


@dataclasses.dataclass
class ToolResult:
    tool: str
    target: str
    ok: bool = True
    findings: list[Finding] = dataclasses.field(default_factory=list)
    data: dict[str, Any] = dataclasses.field(default_factory=dict)
    error: str | None = None
    refused: bool = False
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "target": self.target,
            "ok": self.ok,
            "refused": self.refused,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "findings": [f.to_dict() for f in self.findings],
            "data": self.data,
        }

    def to_model_text(self, max_chars: int = 6000) -> str:
        """Compact rendering fed back to the model as a tool result."""
        payload = self.to_dict()
        text = json.dumps(payload, default=str, ensure_ascii=False)
        if len(text) <= max_chars:
            return text
        trimmed = {
            "tool": payload["tool"], "target": payload["target"],
            "ok": payload["ok"], "refused": payload["refused"],
            "error": payload["error"],
            "findings": [f.to_dict() for f in self.findings],
            "note": "data truncated; full detail is in the JSON report",
        }
        return json.dumps(trimmed, default=str, ensure_ascii=False)[:max_chars]

    @property
    def worst_severity(self) -> str:
        if not self.findings:
            return "info"
        return max(self.findings, key=lambda f: f.rank).severity


class RateLimiter:
    """Token-free minimum-interval limiter. Keeps probes polite."""

    def __init__(self, min_interval: float = 0.25) -> None:
        self.min_interval = max(0.0, min_interval)
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            gap = now - self._last
            if gap < self.min_interval:
                time.sleep(self.min_interval - gap)
            self._last = time.monotonic()


@dataclasses.dataclass
class ToolContext:
    """Everything a tool needs. Constructed once per run."""

    guard: Guard
    scope: Scope | None
    limiter: RateLimiter = dataclasses.field(default_factory=RateLimiter)
    timeout: float = 15.0
    user_agent: str = "sentinel-audit/1.0 (authorized-security-assessment)"
    offline: bool = False
    allow_active: bool = False      # gates anything that opens a raw socket
    on_progress: Callable[[str], None] | None = None

    def log(self, message: str) -> None:
        if self.on_progress:
            self.on_progress(message)

    def refuse(self, tool: str, target: str, reason: str, rule: str = "guard") -> ToolResult:
        return ToolResult(
            tool=tool, target=target, ok=False, refused=True,
            error=reason,
            findings=[Finding(
                title="Request refused by authorization guard",
                severity="info",
                detail=reason,
                remediation=(
                    "Only add targets you own or hold written permission to test, "
                    "then re-run. Sentinel does not probe third-party systems."
                ),
                reference="sentinel://authz",
                evidence={"rule": rule},
            )],
        )


class Tool:
    """Base class. Subclasses set `name`, `description`, `schema`, `active`."""

    name: str = "tool"
    description: str = ""
    schema: dict[str, Any] = {"type": "object", "properties": {}}
    #: True for tools that open raw sockets / initiate connections to ports.
    #: These additionally require `ctx.allow_active`.
    active: bool = False
    #: What kind of target string the guard should evaluate.
    kind: str = "host"

    def spec(self) -> ToolSpec:
        return ToolSpec(name=self.name, description=self.description,
                        parameters=self.schema)

    # -- guard helper -------------------------------------------------------

    def authorize(self, ctx: ToolContext, target: str, *,
                  port: int | None = None, kind: str | None = None):
        """Return a Decision. Callers must bail out when `allowed` is False."""
        if self.active and not ctx.allow_active:
            from ..authz import Decision
            return Decision(
                allowed=False, target=target, kind=kind or self.kind,
                reason=(
                    f"'{self.name}' is an active-probe tool and active probing is "
                    f"disabled. Re-run with --active after confirming the target is "
                    f"yours and that active scanning is permitted by the engagement."
                ),
                rule="active-disabled",
            )
        return ctx.guard.check(target, kind=kind or self.kind, port=port,
                               active=self.active)

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        raise NotImplementedError


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name {tool.name!r}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def specs(self, include_active: bool = True) -> list[ToolSpec]:
        return [t.spec() for t in self._tools.values()
                if include_active or not t.active]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        tool = self._tools.get(name)
        started = time.monotonic()
        if tool is None:
            return ToolResult(
                tool=name, target=str(args.get("target", "")), ok=False,
                error=f"unknown tool {name!r}; available: {', '.join(self.names())}",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        if not isinstance(args, dict):
            args = {}
        try:
            result = tool.run(args, ctx)
        except Exception as exc:  # a tool must never kill the agent loop
            result = ToolResult(
                tool=name, target=str(args.get("target", "")), ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        result.duration_ms = int((time.monotonic() - started) * 1000)
        return result


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (-f.rank, f.title.lower()))


def severity_counts(results: Sequence[ToolResult]) -> dict[str, int]:
    counts = {key: 0 for key in SEVERITY_ORDER}
    for result in results:
        for finding in result.findings:
            counts[finding.severity] += 1
    return counts

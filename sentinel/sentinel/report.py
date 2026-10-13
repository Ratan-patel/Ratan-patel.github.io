"""Report generation: Markdown for humans, JSON for machines/ticketing."""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Sequence

from .agent import AgentRun
from .authz import Guard, authorization_banner
from .scope import Scope
from .tools.base import SEVERITY_ORDER, ToolResult, severity_counts, sort_findings

BADGE = {
    "critical": "!!!", "high": "!! ", "medium": "!  ", "low": ".  ", "info": "-  ",
}


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def markdown_report(run: AgentRun, scope: Scope | None, guard: Guard,
                    *, title: str | None = None,
                    include_evidence: bool = True) -> str:
    findings = sort_findings(f for r in run.results for f in r.findings)
    counts = severity_counts(run.results)
    stamp = _now().strftime("%Y-%m-%d %H:%M UTC")
    heading = title or f"Sentinel assessment - {run.goal[:80]}"

    out: list[str] = []
    out.append(f"# {heading}")
    out.append("")
    out.append(f"Generated {stamp} by Sentinel (read-only assessment agent).")
    out.append("")

    out.append("## Authorization")
    out.append("")
    out.append("```")
    out.append(authorization_banner(scope))
    out.append("```")
    if scope:
        auth = scope.authorization
        out.append("")
        out.append(f"| field | value |")
        out.append(f"|---|---|")
        out.append(f"| scope name | `{scope.name}` |")
        out.append(f"| authorization holder | `{auth.holder}` |")
        out.append(f"| reference | `{auth.reference}` |")
        out.append(f"| granted by | `{auth.granted_by}` |")
        out.append(f"| issued | {auth.issued:%Y-%m-%d} |" if auth.issued
                   else "| issued | - |")
        out.append(f"| expires | {auth.expires:%Y-%m-%d} |" if auth.expires
                   else "| expires | none set |")
        out.append(f"| scope file | `{scope.source or '-'}` |")
        if scope.authorization.notes:
            out.append(f"| notes | {scope.authorization.notes} |")
    out.append("")
    out.append("Sentinel only assessed targets listed above. It has no "
               "capability to probe, exploit or modify any system, and no tool "
               "in this run sent a payload, credential attempt or destructive "
               "request.")
    out.append("")

    out.append("## Summary")
    out.append("")
    out.append(f"- Model: `{run.provider}:{run.model}`")
    out.append(f"- Tools executed: {len(run.results)}")
    out.append(f"- Agent steps: {len(run.steps)}")
    out.append(f"- Wall clock: {run.elapsed_ms} ms")
    out.append(f"- Findings: {sum(counts.values())} total - "
               + ", ".join(f"{counts[k]} {k}" for k in
                           ("critical", "high", "medium", "low", "info")
                           if counts[k]))
    guard_summary = guard.summary()
    out.append(f"- Authorization decisions: {guard_summary['allowed']} allowed, "
               f"{guard_summary['denied']} refused")
    if run.refused_by_model:
        out.append("- The model declined part of the request as out of policy.")
    if run.error:
        out.append(f"- Provider error: `{run.error}`")
    out.append("")

    if findings:
        out.append("## Findings")
        out.append("")
        current: str | None = None
        for finding in findings:
            if finding.severity != current:
                current = finding.severity
                out.append(f"### {current.capitalize()}")
                out.append("")
            out.append(f"#### {BADGE[current]} {finding.title}")
            out.append("")
            if finding.detail:
                out.append(finding.detail.strip())
                out.append("")
            if finding.remediation:
                out.append(f"**Fix:** {finding.remediation.strip()}")
                out.append("")
            if finding.reference:
                out.append(f"*Reference:* {finding.reference}")
                out.append("")
            if include_evidence and finding.evidence:
                out.append("<details><summary>evidence</summary>")
                out.append("")
                out.append("```json")
                out.append(json.dumps(finding.evidence, indent=2,
                                      default=str)[:4000])
                out.append("```")
                out.append("")
                out.append("</details>")
                out.append("")

    per_tool = _by_tool(run.results)
    if per_tool:
        out.append("## Per-target detail")
        out.append("")
        for result in run.results:
            status = "REFUSED" if result.refused else (
                "error" if not result.ok else "ok")
            out.append(f"### `{result.tool}` - {result.target} [{status}]")
            out.append("")
            if result.error:
                out.append(f"> {result.error}")
                out.append("")
            if result.refused:
                continue
            table = [f"| severity | finding |", "|---|---|"]
            for finding in sort_findings(result.findings):
                safe = finding.title.replace("|", "\\|")
                table.append(f"| {finding.severity} | {safe} |")
            out.extend(table)
            out.append("")

    if run.final_text:
        out.append("## Agent narrative")
        out.append("")
        out.append(run.final_text.strip())
        out.append("")

    refusals = run.guard_refusals
    if refusals:
        out.append("## Refused requests")
        out.append("")
        out.append("These were requested and blocked by the authorization layer. "
                   "They are recorded here because an assessment report should "
                   "show what was *not* touched as well as what was.")
        out.append("")
        for refusal in refusals:
            out.append(f"- `{refusal.target}` via `{refusal.tool}` - {refusal.error}")
        out.append("")

    denied = [d for d in guard.decisions if not d.allowed]
    if denied:
        out.append("## Authorization decision log")
        out.append("")
        out.append("| time | target | rule | reason |")
        out.append("|---|---|---|---|")
        for decision in denied[-60:]:
            reason = decision.reason.replace("|", "\\|")[:200]
            out.append(f"| {decision.timestamp} | `{decision.target[:60]}` | "
                       f"`{decision.rule}` | {reason} |")
        out.append("")

    out.append("---")
    out.append("")
    out.append("### Scope of this report")
    out.append("")
    out.append("This is a configuration and exposure review. It is not a "
               "penetration test. No vulnerability was exploited, no "
               "authentication was attempted, no data was modified and no "
               "denial-of-service load was generated. Absence of a finding is "
               "not evidence of absence - a control that this tool does not "
               "check may still be weak. Re-run after every change, and wire it "
               "into CI so regressions are caught before deployment.")
    out.append("")
    return "\n".join(out)


def _by_tool(results: Sequence[ToolResult]) -> dict[str, list[ToolResult]]:
    grouped: dict[str, list[ToolResult]] = {}
    for result in results:
        grouped.setdefault(result.tool, []).append(result)
    return grouped


def json_report(run: AgentRun, scope: Scope | None, guard: Guard,
                *, include_steps: bool = True) -> dict[str, Any]:
    findings = sort_findings(f for r in run.results for f in r.findings)
    payload: dict[str, Any] = {
        "schema": "sentinel.report/v1",
        "generated_at": _now().isoformat(timespec="seconds"),
        "goal": run.goal,
        "provider": run.provider,
        "model": run.model,
        "elapsed_ms": run.elapsed_ms,
        "refused_by_model": run.refused_by_model,
        "refused_by_guard": run.refused_by_guard,
        "error": run.error,
        "authorization": {
            "banner": authorization_banner(scope),
            "scope": scope.to_dict() if scope else None,
            "decisions": [d.to_dict() for d in guard.decisions],
            "summary": guard.summary(),
        },
        "summary": {
            "tools_executed": len(run.results),
            "agent_steps": len(run.steps),
            "findings": severity_counts(run.results),
            "total_findings": len(findings),
        },
        "findings": [f.to_dict() for f in findings],
        "results": [r.to_dict() for r in run.results],
        "narrative": run.final_text,
    }
    if include_steps:
        payload["steps"] = [s.to_dict() for s in run.steps]
    return payload


def write_reports(run: AgentRun, scope: Scope | None, guard: Guard,
                  out_dir: str | Path, basename: str = "sentinel-report",
                  *, include_steps: bool = True) -> dict[str, Path]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = _now().strftime("%Y%m%d-%H%M%S")
    stem = f"{basename}-{stamp}"
    md_path = directory / f"{stem}.md"
    json_path = directory / f"{stem}.json"
    md_path.write_text(markdown_report(run, scope, guard), encoding="utf-8")
    json_path.write_text(
        json.dumps(json_report(run, scope, guard, include_steps=include_steps),
                   indent=2, default=str) + "\n", encoding="utf-8")
    return {"markdown": md_path, "json": json_path}


def console_summary(run: AgentRun, guard: Guard) -> str:
    counts = severity_counts(run.results)
    active = {k: v for k, v in counts.items() if v and k != "info"}
    parts = [f"{v} {k}" for k, v in sorted(active.items(),
                                           key=lambda kv: -SEVERITY_ORDER[kv[0]])]
    line = f"{len(run.results)} tools, "
    line += (", ".join(parts) if parts else "0 actionable findings")
    line += f", {counts['info']} info"
    summary = guard.summary()
    line += f" | authz: {summary['allowed']} allowed / {summary['denied']} refused"
    return line

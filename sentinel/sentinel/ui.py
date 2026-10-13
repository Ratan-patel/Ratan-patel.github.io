"""Terminal rendering. No dependencies - ANSI only, with a no-colour fallback.

Colours are disabled when stdout is not a TTY, when NO_COLOR is set, or when
TERM=dumb, so piping into a file or a CI log stays clean.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any, Iterable, Sequence

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDER = "\033[4m"

SEVERITY_COLOR = {
    "critical": "\033[1;97;41m",   # bold white on red
    "high": "\033[1;31m",
    "medium": "\033[1;33m",
    "low": "\033[1;36m",
    "info": "\033[2;37m",
}
SEVERITY_LABEL = {
    "critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM",
    "low": "LOW", "info": "INFO",
}

BANNER = r"""
   _____ ______ _   _ _______ _____ _____  _   _ ______ _
  / ____|  ____| \ | |_   _/ ____|_   _| \ | ||  ____| |
 | (___ | |__  |  \| | | || |      | | |  \| || |__  | |
  \___ \|  __| | . ` | | || |      | | | . ` ||  __| | |
  ____) | |____| |\  |_| || |____ _| |_| |\  || |____| |____
 |_____/|______|_| \_|_____\_____|_____|_| \_||______|______|
"""


def color_enabled(stream: Any = None) -> bool:
    handle = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        return bool(handle.isatty())
    except (AttributeError, ValueError):
        return False


class UI:
    def __init__(self, stream: Any = None, width: int | None = None) -> None:
        self.stream = stream or sys.stdout
        self.color = color_enabled(self.stream)
        self.width = width or shutil.get_terminal_size((100, 24)).columns
        self.width = max(40, min(self.width, 140))

    # ------------------------------------------------------------- primitives

    def paint(self, text: str, code: str) -> str:
        return f"{code}{text}{RESET}" if self.color else text

    def write(self, text: str = "") -> None:
        self.stream.write(text)
        self.stream.flush()

    def line(self, text: str = "") -> None:
        self.write(text + "\n")

    def rule(self, char: str = "─", label: str = "") -> None:
        if label:
            pad = max(0, self.width - len(label) - 3)
            self.line(self.paint(f"── {label} " + char * pad, DIM))
        else:
            self.line(self.paint(char * self.width, DIM))

    def banner(self) -> None:
        self.line(self.paint(BANNER.rstrip("\n"), "\033[1;32m"))
        self.line(self.paint(
            "  authorized-assessment agent | read-only | scope-enforced",
            DIM))
        self.line("")

    # --------------------------------------------------------------- messages

    def heading(self, text: str) -> None:
        self.line("")
        self.line(self.paint(text, BOLD + UNDER))

    def info(self, text: str) -> None:
        self.line(self.paint(f"  {text}", DIM))

    def ok(self, text: str) -> None:
        self.line(self.paint(f"  \u2713 {text}", "\033[1;32m"))

    def warn(self, text: str) -> None:
        self.line(self.paint(f"  \u26a0 {text}", "\033[1;33m"))

    def error(self, text: str) -> None:
        self.line(self.paint(f"  \u2717 {text}", "\033[1;31m"))

    def refuse(self, text: str) -> None:
        self.line(self.paint(f"  \u26d4 REFUSED  {text}", "\033[1;97;41m"))

    def kv(self, key: str, value: Any, indent: int = 2) -> None:
        pad = " " * indent
        self.line(f"{pad}{self.paint(key.ljust(22), DIM)}{value}")

    def spinner_text(self, text: str) -> None:
        self.write(self.paint(f"\r  \u25b8 {text}" + " " * 8, DIM))
        self.stream.flush()

    def clear_line(self) -> None:
        self.write("\r" + " " * (self.width - 1) + "\r")
        self.stream.flush()

    # --------------------------------------------------------------- findings

    def findings(self, findings: Iterable[Any], *, limit: int = 60,
                 show_remediation: bool = True) -> None:
        items = list(findings)
        if not items:
            self.info("no findings")
            return
        for finding in items[:limit]:
            label = SEVERITY_LABEL.get(finding.severity, finding.severity.upper())
            chip = self.paint(f" {label} ", SEVERITY_COLOR[finding.severity])
            self.line(f"  {chip} {self.paint(finding.title, BOLD)}")
            if finding.detail:
                for detail_line in _wrap(finding.detail.strip(), self.width - 16):
                    self.line(self.paint("        " + detail_line, DIM))
            if show_remediation and finding.remediation:
                for fix_line in _wrap("fix: " + finding.remediation.strip(),
                                      self.width - 16):
                    self.line(self.paint("        " + fix_line, "\033[2;32m"))
            if finding.reference:
                self.line(self.paint("        ref: " + finding.reference,
                                     "\033[2;34m"))
        if len(items) > limit:
            self.info(f"... {len(items) - limit} more (see the JSON/Markdown report)")

    def counts(self, counts: dict[str, int]) -> None:
        parts = []
        for severity in ("critical", "high", "medium", "low", "info"):
            value = counts.get(severity, 0)
            if not value:
                continue
            parts.append(self.paint(f"{value} {severity}",
                                    SEVERITY_COLOR[severity]))
        self.line("  " + self.paint(" | ", DIM) + (self.paint(" | ", DIM).join(parts)
                                                   if parts else "0 findings"))

    # ------------------------------------------------------------------ table

    def table(self, headers: Sequence[str], rows: Sequence[Sequence[Any]],
              widths: Sequence[int] | None = None) -> None:
        if not rows:
            self.info("(empty)")
            return
        columns = len(headers)
        if widths is None:
            widths = []
            for index in range(columns):
                longest = max([len(str(headers[index]))]
                              + [len(str(r[index])) for r in rows if index < len(r)])
                widths.append(min(max(longest + 2, 8), 46))
        total = sum(widths) + columns - 1
        if total > self.width:
            scale = (self.width - columns + 1) / total
            widths = [max(6, int(w * scale)) for w in widths]

        def render(cells: Sequence[Any], bold: bool = False) -> str:
            parts = []
            for index, width in enumerate(widths):
                value = str(cells[index]) if index < len(cells) else ""
                value = value if len(value) <= width else value[:width - 1] + "\u2026"
                parts.append(value.ljust(width))
            text = " ".join(parts)
            return self.paint(text, BOLD) if bold else text

        self.line(render(headers, bold=True))
        self.line(self.paint(" ".join("─" * w for w in widths), DIM))
        for row in rows:
            self.line(render(row))


def _wrap(text: str, width: int) -> list[str]:
    width = max(20, width)
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            if len(current) + 1 + len(word) <= width:
                current += " " + word
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def prompt_yes_no(question: str, default: bool = False,
                  stream: Any = None) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        answer = input(question + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if not answer:
        return default
    return answer in ("y", "yes")

#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Claude Code status line, read as JSON from stdin.

Drawn as a two-row table with a titled cell per field and columns aligned:
  row 1: model | context bar | folder
  row 2: effort | session bar | git branch + status
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RESET = "\033[0m"
GRAY = "\033[90m"
RED = "\033[1;31m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
MAGENTA = "\033[1;35m"
CYAN = "\033[1;36m"
ORANGE = "\033[1;38;5;208m"

BORDER = f"{GRAY}│{RESET}"
BAR_WIDTH = 10
GIT_TIMEOUT_SECONDS = 2
# Reasoning effort, low to high: same green -> yellow -> orange -> red scale as the usage bars
EFFORT_COLORS = {"low": GREEN, "medium": GREEN, "high": YELLOW, "xhigh": ORANGE, "max": RED}


@dataclass
class Span:
    text: str
    color: str

    def render(self) -> str:
        return f"{self.color}{self.text}{RESET}"


@dataclass
class Cell:
    """One box cell: a gray `title:` followed by colored spans joined by spaces."""

    title: str
    spans: list[Span]

    @property
    def width(self) -> int:
        return len(f"{self.title}: ") + len(" ".join(span.text for span in self.spans))

    def render(self) -> str:
        return f"{GRAY}{self.title}:{RESET} " + " ".join(span.render() for span in self.spans)


@dataclass
class GitStatus:
    head: str
    changed: int
    ahead: int
    behind: int


def get(*, data: dict[str, Any], path: str) -> Any:
    """Look up a dotted `path` in nested dicts; `None` if any part is missing."""
    value: Any = data
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def usage_color(*, pct: int) -> str:
    """<20% green, <50% yellow, <85% orange, else red."""
    if pct < 20:
        return GREEN
    if pct < 50:
        return YELLOW
    if pct < 85:
        return ORANGE
    return RED


def progress_bar(*, pct: int) -> str:
    # Round half up, e.g. 85% fills 9 cells (`round` would give 8)
    filled = min(BAR_WIDTH, (pct * BAR_WIDTH + 50) // 100)
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def run_git(*, cwd: str, args: list[str]) -> str | None:
    """Run a read-only git command in `cwd`; `None` on any failure."""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "--no-optional-locks", *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def parse_headers(*, output: str) -> dict[str, str]:
    """`# branch.<key> <value>` lines of `git status --porcelain=v2 --branch`."""
    headers = {}
    for line in output.splitlines():
        if not line.startswith("# "):
            continue
        key, _, value = line[2:].partition(" ")
        headers[key] = value
    return headers


def count_behind(*, headers: dict[str, str]) -> int:
    """Commits behind upstream, as of the last fetch; 0 without an upstream."""
    ahead_behind = headers.get("branch.ab")
    if "branch.upstream" not in headers or not ahead_behind:
        return 0
    return int(ahead_behind.split()[1].lstrip("-"))


def count_unpushed(*, cwd: str, oid: str) -> int:
    """Commits on no remote at all, so a never-pushed branch counts too."""
    if oid == "(initial)":
        return 0
    output = run_git(cwd=cwd, args=["rev-list", "--count", "HEAD", "--not", "--remotes"])
    return int(output) if output else 0


def read_git_status(*, cwd: str) -> GitStatus | None:
    output = run_git(cwd=cwd, args=["status", "--porcelain=v2", "--branch"])
    if output is None:
        return None
    headers = parse_headers(output=output)
    oid = headers.get("branch.oid", "")
    head = headers.get("branch.head", "")
    if head == "(detached)":
        head = f"@{oid[:7]}"
    changed = sum(1 for line in output.splitlines() if line and not line.startswith("#"))
    return GitStatus(
        head=head,
        changed=changed,
        ahead=count_unpushed(cwd=cwd, oid=oid),
        behind=count_behind(headers=headers),
    )


def git_cell(*, status: GitStatus) -> Cell:
    """E.g. `main *3 ↑2 ↓1` (changed files, unpushed, behind), or `main ✓` when clean."""
    spans = [Span(text=status.head, color=MAGENTA)]
    if status.changed:
        spans.append(Span(text=f"*{status.changed}", color=YELLOW))
    if status.ahead:
        spans.append(Span(text=f"↑{status.ahead}", color=CYAN))
    if status.behind:
        spans.append(Span(text=f"↓{status.behind}", color=RED))
    if len(spans) == 1:
        spans.append(Span(text="✓", color=GREEN))
    return Cell(title="git", spans=spans)


def usage_cell(*, title: str, pct: int) -> Cell:
    text = f"{progress_bar(pct=pct)} {pct}%"
    return Cell(title=title, spans=[Span(text=text, color=usage_color(pct=pct))])


def first_line(*, data: dict[str, Any], cwd: str | None) -> list[Cell]:
    cells = []
    if model := get(data=data, path="model.display_name"):
        # Drop the parenthesized suffix: "Opus 5.5 (1M context)" -> "Opus 5.5"
        short_model = model.split("(")[0].strip()
        cells.append(Cell(title="model", spans=[Span(text=short_model, color=YELLOW)]))
    ctx_used = get(data=data, path="context_window.used_percentage")
    if ctx_used is not None:
        cells.append(usage_cell(title="context", pct=round(ctx_used)))
    if cwd:
        cells.append(Cell(title="folder", spans=[Span(text=Path(cwd).name, color=CYAN)]))
    return cells


def second_line(*, data: dict[str, Any], cwd: str | None) -> list[Cell]:
    cells = []
    if effort := get(data=data, path="effort.level"):
        color = EFFORT_COLORS.get(effort, GRAY)
        cells.append(Cell(title="effort", spans=[Span(text=effort, color=color)]))
    session_used = get(data=data, path="rate_limits.five_hour.used_percentage")
    if session_used is not None:
        cells.append(usage_cell(title="session", pct=round(session_used)))
    status = read_git_status(cwd=cwd) if cwd else None
    if status:
        cells.append(git_cell(status=status))
    return cells


def column_widths(*, lines: list[list[Cell]]) -> list[int]:
    """Width of each column: its widest cell across all lines."""
    columns = max(len(line) for line in lines)
    return [max((line[i].width for line in lines if i < len(line)), default=0) for i in range(columns)]


def render_row(*, cells: list[Cell], widths: list[int]) -> str:
    """One ` cell │ cell ` row; a row with fewer cells than columns gets blank ones."""
    parts = [f" {cell.render()}{' ' * (widths[i] - cell.width)} " for i, cell in enumerate(cells)]
    parts += [" " * (width + 2) for width in widths[len(cells) :]]
    # Claude Code trims leading whitespace anyway; drop it here so what we print is what shows
    return BORDER.join(parts).removeprefix(" ").rstrip()


def render_table(*, lines: list[list[Cell]]) -> str:
    widths = column_widths(lines=lines)
    return "\n".join(render_row(cells=line, widths=widths) for line in lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    cwd = get(data=data, path="workspace.current_dir") or get(data=data, path="cwd")
    lines = [line for line in (first_line(data=data, cwd=cwd), second_line(data=data, cwd=cwd)) if line]
    if not lines:
        return
    print(render_table(lines=lines), end="")


if __name__ == "__main__":
    main()

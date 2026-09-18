"""Keep a Changelog rendering and insertion (docs/design.md, Changelog). Pure text, no git."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from semrail.commits import Commit, LogEntry

FILE = "CHANGELOG.md"

HEADER = (
    "# Changelog\n"
    "\n"
    "All notable changes to this project will be documented in this file.\n"
    "\n"
    "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\n"
    "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n"
)
UNRELEASED = "## [Unreleased]\n"

_HEADING = re.compile(r"##\s")  # a level-2 heading; `###` does not match
_UNRELEASED = re.compile(r"##\s+\[?unreleased\]?\s*", re.IGNORECASE)


def section(version: str, date: str, commits: Sequence[tuple[LogEntry, Commit | None]], bumps: Mapping[str, str]) -> str:
    """The `## [version] - date` section for `commits` (newest first), listing only those that bump."""
    groups: dict[str, list[str]] = {"Added": [], "Changed": [], "Fixed": []}
    for entry, commit in reversed(commits):  # oldest first: the order the work landed
        if commit is None:
            continue
        text = commit.description
        if commit.breaking:
            group, text = "Changed", f"**BREAKING:** {text}"
        elif commit.type not in bumps:
            continue
        elif commit.type == "feat":
            group = "Added"
        elif commit.type == "fix":
            group = "Fixed"
        else:  # perf, refactor, and any type that bumps through a `bump` override
            group = "Changed"
        groups[group].append(f"- {text} ({entry.sha[:7]})\n")
    out = f"## [{version}] - {date}\n"
    for name, bullets in groups.items():
        if bullets:
            out += f"\n### {name}\n\n" + "".join(bullets)
    return out


def insert(text: str | None, new_section: str) -> str:
    """`text` with `new_section` inserted below `## [Unreleased]`; no existing line changes.

    Without an Unreleased heading, `## [Unreleased]` and the section go before the first release
    heading, with the standard header on top when nothing but blank lines precedes it.
    """
    text = text or ""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    unreleased = next((i for i, line in enumerate(lines) if _UNRELEASED.fullmatch(line.rstrip("\r\n"))), None)
    if unreleased is not None:
        at = next((i for i in range(unreleased + 1, len(lines)) if _HEADING.match(lines[i])), len(lines))
        block = new_section
    else:
        at = next((i for i, line in enumerate(lines) if _HEADING.match(line)), len(lines))
        block = UNRELEASED + "\n" + new_section
        if all(not line.strip() for line in lines[:at]):
            block = HEADER + "\n" + block
            at = 0
    return "".join(_insert_at(lines, at, block.replace("\n", newline), newline))


def has_version(text: str, version: str) -> bool:
    """Whether `text` has a release heading for `version`, bracketed or not."""
    return re.search(rf"^##\s+\[?{re.escape(version)}\]?(\s|$)", text, re.MULTILINE) is not None


def _insert_at(lines: list[str], at: int, block: str, newline: str) -> list[str]:
    """`lines` with `block` at index `at`, separated from its neighbours by one blank line."""
    before, after = lines[:at], lines[at:]
    if before and not before[-1].endswith("\n"):
        before[-1] += newline
    if before and before[-1].strip():
        block = newline + block
    if after:
        block += newline
    return before + [block] + after

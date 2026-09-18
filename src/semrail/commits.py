"""Conventional Commit subject parsing, bump rules and version arithmetic (docs/design.md)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from semrail import gitutil

# Commit parsing: the scope is free text that may contain ":" but no parentheses, so a
# trailing "(#82)" in the description is never mistaken for part of it.
_SUBJECT = re.compile(
    r"(?P<type>[A-Za-z][A-Za-z0-9-]*)(?:\((?P<scope>[^()\r\n]+)\))?(?P<bang>!)?: (?P<description>[^\s][^\r\n]*)"
)
# Footer tokens must be upper-case (Conventional Commits 1.0.0, item 16).
_BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)
_VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")

LEVELS = ("patch", "minor", "major")
DEFAULT_BUMPS: Mapping[str, str] = {"feat": "minor", "fix": "patch", "perf": "patch", "refactor": "patch"}


@dataclass(frozen=True)
class Commit:
    type: str
    scope: str | None
    breaking: bool
    description: str


@dataclass(frozen=True)
class LogEntry:
    sha: str
    subject: str
    body: str


def parse(subject: str, body: str = "") -> Commit | None:
    """Parse `type(scope)!: description`; None when the subject is not a Conventional Commit."""
    m = _SUBJECT.fullmatch(subject)
    if not m:
        return None
    breaking = bool(m["bang"]) or bool(_BREAKING_FOOTER.search(body))
    return Commit(m["type"].lower(), m["scope"], breaking, m["description"])


def _parse_version(version: str) -> tuple[int, int, int]:
    m = _VERSION.fullmatch(version)
    if not m:
        raise ValueError(f"not a plain X.Y.Z version: {version!r}")
    return int(m[1]), int(m[2]), int(m[3])


def bump(commits: Iterable[Commit | None], version: str, bumps: Mapping[str, str] = DEFAULT_BUMPS) -> str | None:
    """The highest bump among `commits` for a unit at `version`, or None.

    `None` entries are unparseable subjects and contribute nothing. `bumps` maps a type to
    "major", "minor" or "patch"; the caller merges any configured map with the defaults.
    """
    rank = -1
    for commit in commits:
        if commit is None:
            continue
        level = "major" if commit.breaking else bumps.get(commit.type)
        if level is not None:
            rank = max(rank, LEVELS.index(level))
    if rank < 0:
        return None
    # Versioning: no MAJOR before 1.0.0, whatever causes it.
    if LEVELS[rank] == "major" and _parse_version(version)[0] == 0:
        return "minor"
    return LEVELS[rank]


def next_version(version: str, level: str) -> str:
    """`version` bumped by `level` ("major", "minor" or "patch")."""
    major, minor, patch = _parse_version(version)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown bump level: {level!r}")


def log(root: Path, rev_range: str, paths: Sequence[str] = ()) -> list[LogEntry]:
    """The non-merge commits in `rev_range` that touch `paths` (git pathspecs; all when empty), newest first."""
    out = gitutil.git(root, "log", "--no-merges", "-z", "--format=%H%n%s%n%b", rev_range, "--", *paths)
    entries = []
    for record in out.split("\0"):
        if not record.strip():
            continue
        sha, subject, body = (record.split("\n", 2) + ["", ""])[:3]
        entries.append(LogEntry(sha, subject, body.strip()))
    return entries

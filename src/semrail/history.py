"""Each unit's base and commits, and the bump they give (docs/design.md, Selecting a unit's commits)."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from semrail import commits, gitutil
from semrail.commits import Commit, LogEntry
from semrail.units import PACKAGE_JSON, Unit

SHALLOW_WARNING = "shallow clone: history may be incomplete; fetch full history and tags"


@dataclass(frozen=True)
class Base:
    kind: str  # "tag", "version-change" or "history"
    sha: str | None  # None for "history"
    tag: str | None = None  # set for "tag" only


@dataclass(frozen=True)
class UnitStatus:
    unit: Unit
    base: Base
    commits: list[tuple[LogEntry, Commit | None]]  # newest first; None when the subject does not parse
    bump: str | None
    next: str | None
    warnings: list[str]


def base(root: Path, unit: Unit) -> Base:
    """The tag of the current version, else the last commit that changed the version, else none."""
    tag = unit.tag_name(unit.version)
    try:
        sha = gitutil.git(root, "rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}").strip()
        return Base("tag", sha, tag)
    except gitutil.GitError:
        pass
    sha = _last_version_change(root, unit)
    if sha is not None:
        return Base("version-change", sha)
    return Base("history", None)


def select(root: Path, unit: Unit, units: list[Unit], base: Base) -> list[LogEntry]:
    """The unit's non-merge commits since `base`, newest first, without excluded or nested-unit-only ones."""
    paths = [unit.path]
    # git drops a commit whose files in the unit all match an exclusion, which is the `exclude` rule.
    paths += [f":(exclude,glob){_join(unit.path, pattern)}" for pattern in unit.exclude]
    # A commit belongs to the innermost unit: a nested unit's files never count for the one around it.
    paths += [f":(exclude){u.path}" for u in units if _inside(u.path, unit.path)]
    rev_range = f"{base.sha}..HEAD" if base.sha else "HEAD"
    return commits.log(root, rev_range, paths)


def status(root: Path, units: list[Unit]) -> list[UnitStatus]:
    """Every unit's base, commits, bump, next version and warnings."""
    shallow = gitutil.git(root, "rev-parse", "--is-shallow-repository").strip() == "true"
    out = []
    for unit in units:
        b = base(root, unit)
        parsed = [(entry, commits.parse(entry.subject, entry.body)) for entry in select(root, unit, units, b)]
        # Configured entries add types or replace a default's level (docs/design.md, Versioning).
        level = commits.bump((c for _, c in parsed), unit.version, {**commits.DEFAULT_BUMPS, **unit.bump})
        warnings = [f"{e.sha[:7]}: not a Conventional Commit: {e.subject}" for e, c in parsed if c is None]
        if shallow and b.kind != "tag":
            warnings.append(SHALLOW_WARNING)
        next_version = commits.next_version(unit.version, level) if level else None
        out.append(UnitStatus(unit, b, parsed, level, next_version, warnings))
    return out


def _last_version_change(root: Path, unit: Unit) -> str | None:
    """The newest commit whose manifest version differs from its parent's.

    `-G` narrows the search to commits editing a line that mentions "version"; reading the
    version on both sides rules out nested keys and other tables. Introducing a version (no
    version in the parent, or no parent) is not a change, so a never-released unit has none.
    """
    manifest = _join(unit.path, unit.manifest)
    out = gitutil.git(root, "log", "--format=%H", "-Gversion", "HEAD", "--", manifest)
    for sha in out.split():
        before = version_at(root, f"{sha}^", manifest, unit.manifest)
        after = version_at(root, sha, manifest, unit.manifest)
        if before is not None and after is not None and before != after:
            return sha
    return None


def version_at(root: Path, rev: str, path: str, manifest: str) -> str | None:
    """The manifest's version at `rev`; None when the file, the revision or the version is missing or unreadable."""
    try:
        text = gitutil.git(root, "show", f"{rev}:./{path}")
    except gitutil.GitError:
        return None
    try:
        data = json.loads(text) if manifest == PACKAGE_JSON else tomllib.loads(text).get("project")
    except ValueError:  # includes tomllib.TOMLDecodeError
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) else None


def _join(unit_path: str, name: str) -> str:
    return name if unit_path == "." else f"{unit_path}/{name}"


def _inside(path: str, outer: str) -> bool:
    """Whether unit `path` is strictly inside unit `outer`."""
    return path != outer and (outer == "." or path.startswith(outer + "/"))

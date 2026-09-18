"""Release detection and annotated tags for merged releases (docs/design.md, Releases and tags)."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from semrail import gitutil, history, units
from semrail.units import Unit

# Only the files discovery reads are materialized for a past commit.
_MANIFESTS = {units.PACKAGE_JSON, units.PYPROJECT}
_ROOT_FILES = {"pnpm-workspace.yaml", units.CONFIG}
_MANIFEST_PATHSPECS = [f":(glob)**/{name}" for name in sorted(_MANIFESTS)]
_PLAIN = re.compile(r"(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True)
class Release:
    unit: Unit  # as of the release commit, so unit.version is the released version
    sha: str


@dataclass(frozen=True)
class TagResult:
    tag: str
    release: Release
    result: str  # "created", "existing" or "conflict"
    existing_sha: str | None  # the commit the tag points to, for "conflict" only


@dataclass(frozen=True)
class Push:
    remote: str
    pushed: list[str]
    rejected: list[str]


@dataclass(frozen=True)
class Outcome:
    tags: list[TagResult]
    push: Push | None
    warnings: list[str]

    @property
    def conflict(self) -> bool:
        return any(t.result == "conflict" for t in self.tags) or bool(self.push and self.push.rejected)


def run(root: Path, from_rev: str, to_rev: str, remote: str | None = None) -> Outcome:
    """Tag every release in `from_rev..to_rev` and each unit's latest release reachable from `from_rev`."""
    from_sha = _commit(root, from_rev)
    to_sha = _commit(root, to_rev)
    snapshots: dict[str, list[Unit]] = {}
    releases = _reconcile(root, from_sha, snapshots) + _in_range(root, from_sha, to_sha, snapshots)

    results = [_tag(root, r) for r in releases]
    push = None
    if remote is not None:
        push = _push(root, remote, [t.tag for t in results if t.result == "created"])
    warnings = []
    if gitutil.git(root, "rev-parse", "--is-shallow-repository").strip() == "true":
        warnings.append(history.SHALLOW_WARNING)
    return Outcome(results, push, warnings)


def _in_range(root: Path, from_sha: str, to_sha: str, snapshots: dict[str, list[Unit]]) -> list[Release]:
    """Releases in the range, oldest first. Merges are skipped: the merged commit that raised the version is kept."""
    out = gitutil.git(
        root,
        "log",
        "--format=commit %H",
        "--name-only",
        "--no-merges",
        "--reverse",
        "-Gversion",
        f"{from_sha}..{to_sha}",
        "--",
        *_MANIFEST_PATHSPECS,
    )
    touched: dict[str, set[str]] = {}
    sha = ""
    for line in out.splitlines():
        if line.startswith("commit "):
            sha = line.removeprefix("commit ")
            touched[sha] = set()
        elif line:
            touched[sha].add(line)

    releases = []
    for sha, files in touched.items():
        for unit in _units_at(root, sha, snapshots):
            manifest = _join(unit.path, unit.manifest)
            if manifest in files and _raises(history.version_at(root, f"{sha}^", manifest, unit.manifest), unit.version):
                releases.append(Release(unit, sha))
    return releases


def _reconcile(root: Path, from_sha: str, snapshots: dict[str, list[Unit]]) -> list[Release]:
    """Each unit's newest release reachable from `from_sha`, which a skipped CI run may have left untagged."""
    releases = []
    for unit in _units_at(root, from_sha, snapshots):
        manifest = _join(unit.path, unit.manifest)
        candidates = gitutil.git(root, "log", "--format=%H", "--no-merges", "-Gversion", from_sha, "--", manifest)
        for sha in candidates.split():
            after = history.version_at(root, sha, manifest, unit.manifest)
            if after is None or not _raises(history.version_at(root, f"{sha}^", manifest, unit.manifest), after):
                continue
            then = [u for u in _units_at(root, sha, snapshots) if u.path == unit.path and u.manifest == unit.manifest]
            if then:  # otherwise the directory was not a unit at that commit
                releases.append(Release(then[0], sha))
                break
    return releases


def _raises(before: str | None, after: str) -> bool:
    """Whether `after` is a release over `before`: introducing a version is not, and neither is lowering it."""
    if before is None:
        return False
    old, new = _PLAIN.fullmatch(before), _PLAIN.fullmatch(after)
    if old is None or new is None:
        return before != after
    return tuple(map(int, new.groups())) > tuple(map(int, old.groups()))


def _units_at(root: Path, sha: str, snapshots: dict[str, list[Unit]]) -> list[Unit]:
    """The units as of `sha`: its manifests and root config, written to a temporary directory and discovered there."""
    if sha in snapshots:
        return snapshots[sha]
    names = gitutil.git(root, "ls-tree", "-r", "-z", "--name-only", sha).split("\0")
    with tempfile.TemporaryDirectory() as tmp:
        # Named like the repository, so a root unit's {dir} is the same as in the working tree.
        snapshot = Path(tmp) / root.name
        snapshot.mkdir()
        for name in names:
            parts = name.split("/")
            if name in _ROOT_FILES or (parts[-1] in _MANIFESTS and "node_modules" not in parts):
                target = snapshot.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("w", encoding="utf-8", newline="") as f:
                    f.write(gitutil.git(root, "show", f"{sha}:{name}"))
        try:
            found = units.discover(snapshot)
        except units.ConfigError as exc:
            # A commit from before the repository had any unit has nothing to release.
            if str(exc).startswith("no unit found"):
                found = []
            else:
                raise units.ConfigError(f"{sha[:7]}: {exc}") from None
    snapshots[sha] = found
    return found


def _tag(root: Path, release: Release) -> TagResult:
    """Create the release's annotated tag unless it exists; a tag on another commit is never moved."""
    unit = release.unit
    name = unit.tag_name(unit.version)
    existing = _commit_of_tag(root, name)
    if existing is None:
        gitutil.git(root, "tag", "-a", "-m", f"{unit.name} {unit.version}", name, release.sha)
        return TagResult(name, release, "created", None)
    if existing == release.sha:
        return TagResult(name, release, "existing", None)
    return TagResult(name, release, "conflict", existing)


def _push(root: Path, remote: str, names: list[str]) -> Push:
    """Push `names` in one command. A tag the remote already has elsewhere is rejected, not an error."""
    if not names:
        return Push(remote, [], [])
    refs = [f"refs/tags/{n}:refs/tags/{n}" for n in names]
    try:
        gitutil.git(root, "push", "--porcelain", remote, *refs)
        return Push(remote, names, [])
    except gitutil.GitError as exc:
        # Porcelain lines are `<flag>\t<src>:<dst>\t<summary>`; `!` marks a ref that was not pushed.
        failed = [line.split("\t") for line in exc.stdout.splitlines() if line.startswith("!\t")]
        rejected = [f[1].split(":", 1)[1].removeprefix("refs/tags/") for f in failed if "(already exists)" in f[-1]]
        if not rejected or len(rejected) != len(failed):
            raise
        return Push(remote, [n for n in names if n not in rejected], rejected)


def _commit(root: Path, rev: str) -> str:
    return gitutil.git(root, "rev-parse", "--verify", "--end-of-options", f"{rev}^{{commit}}").strip()


def _commit_of_tag(root: Path, name: str) -> str | None:
    try:
        return gitutil.git(root, "rev-parse", "-q", "--verify", f"refs/tags/{name}^{{commit}}").strip()
    except gitutil.GitError:
        return None


def _join(unit_path: str, name: str) -> str:
    return name if unit_path == "." else f"{unit_path}/{name}"

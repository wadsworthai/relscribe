"""Command-line entry point: global flags, dispatch, output and exit codes."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

from semrail import changelog, commits, gitutil, history, units

# Exit codes, docs/design.md (CLI).
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_ERROR = 2
EXIT_CONFLICT = 4


class SemrailError(Exception):
    """An error reported as `semrail: <message>` on stderr, exiting with `code`."""

    def __init__(self, message: str, code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.code = code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="semrail",
        description="SemVer versions and changelogs from Conventional Commits.",
    )
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--root", type=Path, help="repository to operate on")

    # The same flags after the subcommand. SUPPRESS keeps a subparser from
    # overwriting a value given before the subcommand with its own default.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="machine-readable output")
    common.add_argument("--root", type=Path, default=argparse.SUPPRESS, help="repository to operate on")

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    # Commands register here: sub.add_parser(name, parents=[common], help=…)
    # followed by .set_defaults(func=cmd_<name>), where cmd_<name>(args) -> int.
    lint = sub.add_parser("lint", parents=[common], help="check that subjects are Conventional Commits")
    lint.add_argument("subjects", nargs="*", metavar="<subject>", help="a subject to check, e.g. a PR title")
    lint.add_argument("--range", metavar="<from>..<to>", help="check the subjects of the commits in this range")
    lint.set_defaults(func=cmd_lint)
    status = sub.add_parser("status", parents=[common], help="report each unit's base, commits and next version")
    status.set_defaults(func=cmd_status)
    release = sub.add_parser("release", parents=[common], help="write the next versions and changelogs")
    release.add_argument("--commit", action="store_true", help="make the release commit")
    release.add_argument("--branch", action="store_true", help="first create release/<YYYY-MM-DD>[-N]")
    release.set_defaults(func=cmd_release)
    return parser


def _root(args: argparse.Namespace) -> Path:
    """The repository to operate on: --root, else the enclosing git repository."""
    if args.root is not None:
        return args.root.resolve()
    return gitutil.toplevel(Path.cwd())


def _emit(args: argparse.Namespace, data: Any, text: str) -> None:
    """Print `data` as JSON under --json, otherwise `text`."""
    print(json.dumps(data, indent=2) if args.json else text)


def cmd_lint(args: argparse.Namespace) -> int:
    if not args.subjects and args.range is None:
        raise SemrailError("lint: give at least one <subject> or --range <from>..<to>")
    checked: list[tuple[str | None, str]] = [(None, s) for s in args.subjects]
    if args.range is not None:
        if ".." not in args.range:
            raise SemrailError(f"lint: --range must be <from>..<to>, got {args.range!r}")
        # Only a range needs a repository, so `lint <subject>` runs anywhere.
        checked += [(e.sha, e.subject) for e in commits.log(_root(args), args.range)]

    results = [{"sha": sha, "subject": s, "valid": commits.parse(s) is not None} for sha, s in checked]
    invalid = [r for r in results if not r["valid"]]
    lines = [f"{r['sha'][:7]} invalid: {r['subject']}" if r["sha"] else f"invalid: {r['subject']}" for r in invalid]
    noun = "subject" if len(results) == 1 else "subjects"
    lines.append(f"{len(invalid)} of {len(results)} {noun} invalid" if invalid else f"{len(results)} {noun} valid")
    _emit(args, {"valid": not invalid, "subjects": results}, "\n".join(lines))
    return EXIT_FAILED if invalid else EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    root = _root(args)
    results = history.status(root, units.discover(root))
    _emit(args, {"units": [_status_json(s) for s in results]}, "\n".join(_status_text(s) for s in results))
    return EXIT_OK


def _status_json(s: history.UnitStatus) -> dict[str, Any]:
    return {
        "path": s.unit.path,
        "name": s.unit.name,
        "version": s.unit.version,
        "base": {"kind": s.base.kind, "sha": s.base.sha, "tag": s.base.tag},
        "commits": [
            {
                "sha": e.sha,
                "subject": e.subject,
                "type": c.type if c else None,
                "scope": c.scope if c else None,
                "breaking": c.breaking if c else False,
            }
            for e, c in s.commits
        ],
        "bump": s.bump,
        "next": s.next,
        "warnings": s.warnings,
    }


def _status_text(s: history.UnitStatus) -> str:
    head = f"{s.unit.name} ({s.unit.path}): {s.unit.version}"
    lines = [f"{head} -> {s.next} ({s.bump})" if s.next else f"{head}, no release"]
    if s.base.kind == "tag":
        lines.append(f"  base: tag {s.base.tag} ({s.base.sha[:7]})")
    elif s.base.kind == "version-change":
        lines.append(f"  base: version change ({s.base.sha[:7]})")
    else:
        lines.append("  base: whole history")
    lines += [f"  {e.sha[:7]} {e.subject}" for e, _ in s.commits]
    lines += [f"  warning: {w}" for w in s.warnings]
    return "\n".join(lines)


def cmd_release(args: argparse.Namespace) -> int:
    root = _root(args)
    # On a dirty tree a second run would count the same commits again and release twice.
    if gitutil.git(root, "status", "--porcelain", "--untracked-files=no").strip():
        raise SemrailError("release: tracked files have uncommitted changes; commit or stash them first")
    released = [s for s in history.status(root, units.discover(root)) if s.next]
    if not released:
        _emit(args, {"units": [], "files": [], "branch": None, "commit": None}, "nothing to release")
        return EXIT_OK

    date = _today()
    changelogs: dict[Path, str] = {}
    for s in released:
        if not s.unit.changelog:
            continue
        path = root / s.unit.path / changelog.FILE
        text = _read_or_none(path)
        if text is not None and changelog.has_version(text, s.next):
            raise SemrailError(f"release: {_rel(root, path)} already has a section for {s.next}")
        entry = changelog.section(s.next, date, s.commits, {**commits.DEFAULT_BUMPS, **s.unit.bump})
        changelogs[path] = changelog.insert(text, entry)

    # All files or none: record every file the release may touch, and restore them on failure.
    originals = {p: _read_or_none(p) for s in released for p in _release_paths(root, s.unit)}
    files: list[str] = []
    branch = None
    try:
        for s in released:
            files += units.write_version(root, s.unit, s.next)
            path = root / s.unit.path / changelog.FILE
            if path in changelogs:
                with path.open("w", encoding="utf-8", newline="") as f:
                    f.write(changelogs[path])
                files.append(_rel(root, path))
        files = list(dict.fromkeys(files))
        if args.branch:
            branch = _release_branch(root, date)
            gitutil.git(root, "switch", "-q", "-c", branch)
    except Exception:
        _restore(originals)
        raise

    sha = None
    subject = "chore(release): " + ", ".join(f"{s.unit.name} {s.unit.version} -> {s.next}" for s in released)
    if args.commit:
        gitutil.git(root, "add", "--", *files)
        gitutil.git(root, "commit", "-q", "-m", subject)
        sha = gitutil.git(root, "rev-parse", "HEAD").strip()

    data = {
        "units": [
            {"path": s.unit.path, "name": s.unit.name, "version": s.unit.version, "next": s.next, "bump": s.bump,
             "warnings": s.warnings}
            for s in released
        ],
        "files": files,
        "branch": branch,
        "commit": sha,
    }
    lines = []
    for s in released:
        lines.append(f"{s.unit.name} ({s.unit.path}): {s.unit.version} -> {s.next} ({s.bump})")
        lines += [f"  warning: {w}" for w in s.warnings]
    lines += [f"wrote {f}" for f in files]
    if branch:
        lines.append(f"branch {branch}")
    if sha:
        lines.append(f"commit {sha[:7]} {subject}")
    _emit(args, data, "\n".join(lines))
    return EXIT_OK


def _today() -> str:
    """The release date, in UTC so every machine agrees (docs/design.md, Changelog)."""
    return datetime.now(timezone.utc).date().isoformat()


def _release_branch(root: Path, date: str) -> str:
    """`release/<date>`, or the first free `release/<date>-N` among local and remote-tracking branches."""
    refs = gitutil.git(root, "for-each-ref", "--format=%(refname)", "refs/heads/", "refs/remotes/").split()
    taken = {r.removeprefix("refs/heads/") for r in refs if r.startswith("refs/heads/")}
    taken |= {r.split("/", 3)[3] for r in refs if r.startswith("refs/remotes/") and r.count("/") >= 3}
    name, n = f"release/{date}", 1
    while name in taken:
        n += 1
        name = f"release/{date}-{n}"
    return name


def _release_paths(root: Path, unit: units.Unit) -> list[Path]:
    base = root / unit.path
    return [base / unit.manifest, *(base / s.file for s in unit.sync), base / changelog.FILE]


def _read_or_none(path: Path) -> str | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as f:
        return f.read()


def _restore(originals: dict[Path, str | None]) -> None:
    for path, text in originals.items():
        if text is None:
            path.unlink(missing_ok=True)
        else:
            with path.open("w", encoding="utf-8", newline="") as f:
                f.write(text)


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # usage errors and --help
        return exc.code if isinstance(exc.code, int) else EXIT_ERROR

    if args.version:
        v = version("semrail")
        _emit(args, {"version": v}, v)
        return EXIT_OK
    if not getattr(args, "func", None):
        parser.print_usage(sys.stderr)
        print("semrail: error: a command is required", file=sys.stderr)
        return EXIT_ERROR

    try:
        return args.func(args)
    except SemrailError as exc:
        print(f"semrail: {exc}", file=sys.stderr)
        return exc.code
    except (gitutil.GitError, units.ConfigError) as exc:
        print(f"semrail: {exc}", file=sys.stderr)
        return EXIT_ERROR

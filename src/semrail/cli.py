"""Command-line entry point: global flags, dispatch, output and exit codes."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

from semrail import commits, gitutil

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
    lines.append(f"{len(invalid)} of {len(results)} subjects invalid" if invalid else f"{len(results)} subjects valid")
    _emit(args, {"valid": not invalid, "subjects": results}, "\n".join(lines))
    return EXIT_FAILED if invalid else EXIT_OK


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
    except gitutil.GitError as exc:
        print(f"semrail: {exc}", file=sys.stderr)
        return EXIT_ERROR

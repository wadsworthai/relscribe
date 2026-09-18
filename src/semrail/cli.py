"""Command-line entry point: global flags, dispatch, output and exit codes."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

from semrail import gitutil

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
    _ = sub, common  # unused until the first command lands
    return parser


def _root(args: argparse.Namespace) -> Path:
    """The repository to operate on: --root, else the enclosing git repository."""
    if args.root is not None:
        return args.root.resolve()
    return gitutil.toplevel(Path.cwd())


def _emit(args: argparse.Namespace, data: Any, text: str) -> None:
    """Print `data` as JSON under --json, otherwise `text`."""
    print(json.dumps(data, indent=2) if args.json else text)


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

"""Run git. The only module that shells out to git (docs/design.md, Architecture)."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(Exception):
    """A git command failed. The CLI reports it as a git error, exit code 2."""

    def __init__(self, message: str, stdout: str = "") -> None:
        super().__init__(message)
        # Kept for commands whose failure is reported on stdout, such as `git push --porcelain`.
        self.stdout = stdout


def git(root: Path, *args: str) -> str:
    """Run `git -C root args…` and return its stdout, or raise GitError."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise GitError("git is not installed") from None
    if proc.returncode != 0:
        detail = proc.stderr.strip() or f"exit status {proc.returncode}"
        raise GitError(f"git {' '.join(args)}: {detail}", proc.stdout)
    return proc.stdout


def toplevel(path: Path) -> Path:
    """Return the root of the git repository that contains `path`."""
    return Path(git(path, "rev-parse", "--show-toplevel").strip())

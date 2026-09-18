"""Shared fixtures: real git repositories in tmp_path and an in-process CLI runner."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from relscribe.cli import main


@dataclass
class Repo:
    """A throwaway git repository on branch main."""

    path: Path

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def write(self, files: dict[str, str]) -> None:
        for name, content in files.items():
            target = self.path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

    def commit(self, subject: str, files: dict[str, str] | None = None, body: str = "") -> str:
        """Write `files`, stage everything and commit; return the full SHA."""
        self.write(files or {})
        self.git("add", "-A")
        message = f"{subject}\n\n{body}" if body else subject
        self.git("commit", "--allow-empty", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()


@pytest.fixture(autouse=True)
def _isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep the host's git config (signing, hooks, default branch) out of every test.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    path = tmp_path / "repo"
    path.mkdir()
    r = Repo(path)
    r.git("init", "-q", "-b", "main")
    return r


@dataclass
class Result:
    code: int
    out: str
    err: str

    def json(self) -> Any:
        return json.loads(self.out)


@pytest.fixture
def cli(capsys: pytest.CaptureFixture[str]):
    """Run `relscribe <argv>` in process and return its exit code and output."""

    def run(*argv: str) -> Result:
        code = main(list(argv))
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)

    return run

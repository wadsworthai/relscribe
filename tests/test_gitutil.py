"""gitutil, tested directly until a command exercises it through the CLI."""

from __future__ import annotations

import pytest

from semrail import gitutil


def test_toplevel_from_a_subdirectory(repo):
    sha = repo.commit("chore: init", {"pkg/a.txt": "a\n"})
    assert len(sha) == 40
    assert gitutil.toplevel(repo.path / "pkg") == repo.path.resolve()


def test_git_outside_a_repository_raises(tmp_path):
    with pytest.raises(gitutil.GitError, match="rev-parse"):
        gitutil.toplevel(tmp_path)

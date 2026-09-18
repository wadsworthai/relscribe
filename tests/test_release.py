"""`semrail release`: versions, changelogs, the release branch and commit.

docs/design.md, Changelog, Releases and tags, and CLI.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess

import pytest

from semrail import cli as cli_module

DATE = "2026-09-18"

HEADER = (
    "# Changelog\n"
    "\n"
    "All notable changes to this project will be documented in this file.\n"
    "\n"
    "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\n"
    "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n"
    "\n"
    "## [Unreleased]\n"
)


@pytest.fixture(autouse=True)
def _fixed_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "_today", lambda: DATE)


def pkg(name: str, version: str, **extra: object) -> str:
    return json.dumps({"name": name, "version": version, **extra}, indent=2) + "\n"


def release(cli, repo, *args: str, code: int = 0):
    result = cli("--root", str(repo.path), "--json", "release", *args)
    assert result.code == code, result.err
    return result.json() if code == 0 else result


def head(repo) -> str:
    return repo.git("rev-parse", "HEAD").strip()


def branch(repo) -> str:
    return repo.git("branch", "--show-current").strip()


def short(sha: str) -> str:
    return sha[:7]


def workspace(repo, *members: str) -> None:
    files = {"pnpm-workspace.yaml": "packages:\n  - 'apps/*'\n", "package.json": json.dumps({"name": "root", "private": True})}
    for member in members:
        files[f"apps/{member}/package.json"] = pkg(f"@scope/{member}", "1.0.0")
    repo.commit("chore: init", files)


# Single unit, working tree only (AC 1)


def test_release_writes_version_and_creates_the_changelog(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("tag", "-a", "app@1.0.0", "-m", "app 1.0.0")
    fix = repo.commit("fix: repair y", {"a.txt": "1\n"})
    feat = repo.commit("feat(api): add x (#82)", {"a.txt": "2\n"})
    before = head(repo)

    out = release(cli, repo)

    assert out == {
        "units": [{"path": ".", "name": "app", "version": "1.0.0", "next": "1.1.0", "bump": "minor", "warnings": []}],
        "files": ["package.json", "CHANGELOG.md"],
        "branch": None,
        "commit": None,
    }
    assert json.loads((repo.path / "package.json").read_text())["version"] == "1.1.0"
    assert (repo.path / "CHANGELOG.md").read_text() == (
        HEADER
        + "\n"
        + f"## [1.1.0] - {DATE}\n"
        + "\n### Added\n\n"
        + f"- add x (#82) ({short(feat)})\n"
        + "\n### Fixed\n\n"
        + f"- repair y ({short(fix)})\n"
    )
    assert head(repo) == before
    assert branch(repo) == "main"
    assert repo.git("status", "--porcelain") == " M package.json\n?? CHANGELOG.md\n"


def test_pyproject_unit(cli, repo):
    repo.commit("chore: init", {"pyproject.toml": '[project]\nname = "tool"\nversion = "0.3.0"\n'})
    repo.commit("feat!: drop x", {"a.txt": "1\n"})
    out = release(cli, repo)
    assert out["units"][0]["next"] == "0.4.0"
    assert out["files"] == ["pyproject.toml", "CHANGELOG.md"]
    assert 'version = "0.4.0"' in (repo.path / "pyproject.toml").read_text()
    assert "### Changed\n\n- **BREAKING:** drop x (" in (repo.path / "CHANGELOG.md").read_text()


# Grouping through the CLI (AC 2)


def test_bump_override_type_goes_to_changed_and_others_are_left_out(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "semrail.toml": '[bump]\ndocs = "patch"\n'})
    repo.git("tag", "app@1.0.0")
    docs = repo.commit("docs: explain x", {"a.md": "1\n"})
    repo.commit("chore: tidy", {"a.txt": "1\n"})
    repo.commit("wip", {"a.txt": "2\n"})
    release(cli, repo)
    text = (repo.path / "CHANGELOG.md").read_text()
    assert text.endswith(f"## [1.0.1] - {DATE}\n\n### Changed\n\n- explain x ({short(docs)})\n")


# Existing changelogs (AC 4, 5)


def test_existing_changelog_keeps_every_line(cli, repo):
    old = HEADER + "\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- first (1234567)\n"
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "CHANGELOG.md": old})
    repo.git("tag", "app@1.0.0")
    fix = repo.commit("fix: y", {"a.txt": "1\n"})
    release(cli, repo)
    new = (repo.path / "CHANGELOG.md").read_text()
    assert new == HEADER + f"\n## [1.0.1] - {DATE}\n\n### Fixed\n\n- y ({short(fix)})\n" + old[len(HEADER) :]


def test_changelog_without_header_or_unreleased(cli, repo):
    old = "## 0.0.1 — 2026-09-08\n\n### Added\n\n- first thing (1234567)\n\n### Unknown\n\n- Initial import (89abcde)\n"
    repo.commit("chore: init", {"package.json": pkg("app", "0.0.1"), "CHANGELOG.md": old})
    repo.git("tag", "app@0.0.1")
    feat = repo.commit("feat: add x", {"a.txt": "1\n"})
    release(cli, repo)
    new = (repo.path / "CHANGELOG.md").read_text()
    assert new == HEADER + f"\n## [0.1.0] - {DATE}\n\n### Added\n\n- add x ({short(feat)})\n\n" + old


def test_crlf_changelog_stays_crlf(cli, repo):
    old = HEADER.replace("\n", "\r\n") + "\r\n## [1.0.0] - 2026-01-01\r\n"
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    (repo.path / "CHANGELOG.md").write_bytes(old.encode())
    repo.commit("chore: add a changelog")
    repo.git("tag", "app@1.0.0")
    fix = repo.commit("fix: y", {"a.txt": "1\n"})
    release(cli, repo)
    expected = HEADER + f"\n## [1.0.1] - {DATE}\n\n### Fixed\n\n- y ({short(fix)})\n\n## [1.0.0] - 2026-01-01\n"
    assert (repo.path / "CHANGELOG.md").read_bytes() == expected.replace("\n", "\r\n").encode()


# changelog = false (AC 7)


def test_changelog_false_writes_only_versions(cli, repo):
    repo.commit(
        "chore: init",
        {
            "package.json": pkg("app", "1.0.0"),
            "version.txt": "1.0.0\n",
            "semrail.toml": 'changelog = false\nsync = [{ file = "version.txt", pattern = "^(.+)$" }]\n',
        },
    )
    repo.git("tag", "app@1.0.0")
    repo.commit("fix: y", {"a.txt": "1\n"})
    out = release(cli, repo)
    assert out["files"] == ["package.json", "version.txt"]
    assert (repo.path / "version.txt").read_text() == "1.0.1\n"
    assert not (repo.path / "CHANGELOG.md").exists()


# Workspaces (AC 8)


def test_only_units_with_a_next_version_are_released(cli, repo):
    workspace(repo, "api", "web", "docs")
    for member in ("api", "web", "docs"):
        repo.git("tag", f"@scope/{member}@1.0.0")
    repo.commit("feat(api): add x", {"apps/api/a.txt": "1\n"})
    repo.commit("fix(web): y", {"apps/web/a.txt": "1\n"})
    repo.commit("docs(docs): z", {"apps/docs/a.md": "1\n"})

    out = release(cli, repo)

    assert [(u["path"], u["version"], u["next"]) for u in out["units"]] == [
        ("apps/api", "1.0.0", "1.1.0"),
        ("apps/web", "1.0.0", "1.0.1"),
    ]
    assert out["files"] == [
        "apps/api/package.json",
        "apps/api/CHANGELOG.md",
        "apps/web/package.json",
        "apps/web/CHANGELOG.md",
    ]
    assert "- add x (" in (repo.path / "apps/api/CHANGELOG.md").read_text()
    assert "- y (" in (repo.path / "apps/web/CHANGELOG.md").read_text()
    assert not (repo.path / "apps/docs/CHANGELOG.md").exists()
    assert json.loads((repo.path / "apps/docs/package.json").read_text())["version"] == "1.0.0"


# --commit (AC 9)


def test_commit_one_unit(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.2.0")})
    repo.git("tag", "app@1.2.0")
    repo.commit("feat: add x", {"a.txt": "1\n"})
    (repo.path / "scratch.txt").write_text("not mine\n")

    out = release(cli, repo, "--commit")

    assert out["commit"] == head(repo)
    assert repo.git("log", "-1", "--format=%s%n%b").strip() == "chore(release): app 1.2.0 -> 1.3.0"
    assert repo.git("show", "--name-only", "--format=", "HEAD").split() == ["CHANGELOG.md", "package.json"]
    assert repo.git("status", "--porcelain") == "?? scratch.txt\n"
    assert branch(repo) == "main"


def test_commit_several_units(cli, repo):
    workspace(repo, "api", "web")
    repo.git("tag", "@scope/api@1.0.0")
    repo.git("tag", "@scope/web@1.0.0")
    repo.commit("feat(api): add x", {"apps/api/a.txt": "1\n"})
    repo.commit("fix(web): y", {"apps/web/a.txt": "1\n"})

    release(cli, repo, "--commit")

    assert repo.git("log", "-1", "--format=%s").strip() == (
        "chore(release): @scope/api 1.0.0 -> 1.1.0, @scope/web 1.0.0 -> 1.0.1"
    )
    assert sorted(repo.git("show", "--name-only", "--format=", "HEAD").split()) == [
        "apps/api/CHANGELOG.md",
        "apps/api/package.json",
        "apps/web/CHANGELOG.md",
        "apps/web/package.json",
    ]
    assert repo.git("status", "--porcelain") == ""


def test_after_a_release_commit_there_is_nothing_to_release(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("feat: add x", {"a.txt": "1\n"})
    release(cli, repo, "--commit")
    assert release(cli, repo)["units"] == []


# --branch (AC 10)


def test_branch_is_created_from_the_date(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("fix: y", {"a.txt": "1\n"})
    out = release(cli, repo, "--branch")
    assert out["branch"] == f"release/{DATE}"
    assert out["commit"] is None
    assert branch(repo) == f"release/{DATE}"
    assert repo.git("status", "--porcelain") == " M package.json\n?? CHANGELOG.md\n"


def test_branch_gets_a_suffix_when_the_name_exists(cli, repo, tmp_path):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    start = repo.commit("fix: y", {"a.txt": "1\n"})
    repo.git("branch", f"release/{DATE}")
    # A remote-tracking branch counts as taken too.
    repo.git("update-ref", f"refs/remotes/origin/release/{DATE}-2", start)

    out = release(cli, repo, "--branch", "--commit")

    assert out["branch"] == f"release/{DATE}-3"
    assert branch(repo) == f"release/{DATE}-3"
    assert out["commit"] == head(repo)
    assert repo.git("rev-parse", "main").strip() == start
    assert repo.git("rev-parse", f"release/{DATE}-3~1").strip() == start


def test_branch_suffix_counts_up(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("fix: y", {"a.txt": "1\n"})
    repo.git("branch", f"release/{DATE}")
    repo.git("branch", f"release/{DATE}-2")
    assert release(cli, repo, "--branch")["branch"] == f"release/{DATE}-3"


# Nothing to release (AC 11)


def test_nothing_to_release(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("tag", "app@1.0.0")
    repo.commit("docs: explain", {"a.md": "1\n"})
    before = head(repo)

    assert release(cli, repo, "--branch", "--commit") == {"units": [], "files": [], "branch": None, "commit": None}
    text = cli("--root", str(repo.path), "release")
    assert (text.code, text.out) == (0, "nothing to release\n")
    assert head(repo) == before
    assert branch(repo) == "main"
    assert repo.git("status", "--porcelain") == ""
    assert repo.git("branch", "--list", "release/*") == ""


# Preflight (AC 12)


def test_uncommitted_tracked_changes_are_refused(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "a.txt": "0\n"})
    repo.commit("fix: y", {"a.txt": "1\n"})
    (repo.path / "a.txt").write_text("edited\n")

    result = release(cli, repo, "--commit", code=2)

    assert result.err.startswith("semrail: ")
    assert "uncommitted" in result.err
    assert json.loads((repo.path / "package.json").read_text())["version"] == "1.0.0"
    assert repo.git("status", "--porcelain") == " M a.txt\n"


def test_staged_changes_are_refused(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "a.txt": "0\n"})
    repo.commit("fix: y", {"a.txt": "1\n"})
    (repo.path / "a.txt").write_text("edited\n")
    repo.git("add", "a.txt")
    release(cli, repo, code=2)


def test_untracked_files_do_not_block(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("fix: y", {"a.txt": "1\n"})
    (repo.path / "build.log").write_text("x\n")
    assert release(cli, repo)["units"][0]["next"] == "1.0.1"


# All files or none (AC 13)


def test_a_failing_unit_rolls_back_every_file(cli, repo):
    workspace(repo, "api", "web")
    repo.write({"apps/web/version.txt": "0.9.0\n", "apps/api/CHANGELOG.md": HEADER})
    repo.write({"semrail.toml": '[units."apps/web"]\nsync = [{ file = "version.txt", pattern = "^(.+)$" }]\n'})
    repo.commit("chore: config")
    repo.git("tag", "@scope/api@1.0.0")
    repo.git("tag", "@scope/web@1.0.0")
    repo.commit("feat(api): add x", {"apps/api/a.txt": "1\n"})
    repo.commit("fix(web): y", {"apps/web/a.txt": "1\n"})
    repo.git("switch", "-q", "-c", "work")
    before = head(repo)

    result = release(cli, repo, "--branch", "--commit", code=2)

    assert result.err.startswith("semrail: apps/web/version.txt")
    assert repo.git("status", "--porcelain") == ""
    assert (repo.path / "apps/api/CHANGELOG.md").read_text() == HEADER
    assert not (repo.path / "apps/web/CHANGELOG.md").exists()
    assert head(repo) == before
    assert branch(repo) == "work"
    assert repo.git("branch", "--list", "release/*") == ""


def test_a_failing_unit_removes_changelogs_it_created(cli, repo):
    workspace(repo, "api", "web")
    repo.write({"apps/web/version.txt": "0.9.0\n"})
    repo.write({"semrail.toml": '[units."apps/web"]\nsync = [{ file = "version.txt", pattern = "^(.+)$" }]\n'})
    repo.commit("chore: config")
    repo.commit("feat(api): add x", {"apps/api/a.txt": "1\n"})
    repo.commit("fix(web): y", {"apps/web/a.txt": "1\n"})

    release(cli, repo, code=2)

    assert repo.git("status", "--porcelain", "--untracked-files=all") == ""


# Duplicate section (AC 14)


def test_existing_section_for_the_new_version_is_refused(cli, repo):
    old = HEADER + "\n## [1.0.1] - 2026-01-01\n"
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "CHANGELOG.md": old})
    repo.commit("fix: y", {"a.txt": "1\n"})

    result = release(cli, repo, code=2)

    assert result.err == "semrail: release: CHANGELOG.md already has a section for 1.0.1\n"
    assert repo.git("status", "--porcelain") == ""


# Never pushes, never tags (AC 15)


def test_release_never_pushes_or_tags(cli, repo, tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    repo.git("remote", "add", "origin", str(remote))
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("push", "-q", "origin", "main")
    repo.commit("feat: add x", {"a.txt": "1\n"})
    remote_refs = subprocess.run(["git", "-C", str(remote), "show-ref"], capture_output=True, text=True).stdout

    release(cli, repo, "--branch", "--commit")

    assert repo.git("tag") == ""
    after = subprocess.run(["git", "-C", str(remote), "show-ref"], capture_output=True, text=True).stdout
    assert after == remote_refs


# Warnings and text output (AC 16)


def test_warnings_are_reported_and_do_not_block(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("tag", "app@1.0.0")
    wip = repo.commit("wip", {"a.txt": "1\n"})
    repo.commit("fix: y", {"a.txt": "2\n"})
    out = release(cli, repo)
    assert out["units"][0]["warnings"] == [f"{short(wip)}: not a Conventional Commit: wip"]


def test_text_output(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("tag", "app@1.0.0")
    wip = repo.commit("wip", {"a.txt": "1\n"})
    repo.commit("feat: add x", {"a.txt": "2\n"})

    result = cli("--root", str(repo.path), "release", "--branch", "--commit")

    assert result.code == 0, result.err
    sha = head(repo)
    assert result.out == (
        "app (.): 1.0.0 -> 1.1.0 (minor)\n"
        f"  warning: {short(wip)}: not a Conventional Commit: wip\n"
        "wrote package.json\n"
        "wrote CHANGELOG.md\n"
        f"branch release/{DATE}\n"
        f"commit {short(sha)} chore(release): app 1.0.0 -> 1.1.0\n"
    )


def test_today_is_the_utc_date(monkeypatch):
    monkeypatch.undo()  # drop the fixed date
    assert cli_module._today() == dt.datetime.now(dt.timezone.utc).date().isoformat()

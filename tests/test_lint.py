"""`semrail lint`: subjects given as arguments and commits in a range (docs/design.md, CLI)."""

from __future__ import annotations

import pytest


def test_valid_subject(cli):
    result = cli("lint", "feat: x")
    assert result.code == 0
    assert result.out.splitlines()[-1] == "1 subject valid"


@pytest.mark.parametrize(
    ("subjects", "summary"),
    [
        (["feat: x"], "1 subject valid"),
        (["feat: x", "fix: y"], "2 subjects valid"),
        (["oops"], "1 of 1 subject invalid"),
        (["oops", "fix: y"], "1 of 2 subjects invalid"),
    ],
)
def test_summary_counts_subjects(cli, subjects, summary):
    assert cli("lint", *subjects).out.splitlines()[-1] == summary


def test_invalid_subject(cli):
    result = cli("lint", "oops")
    assert result.code == 1
    assert "invalid: oops" in result.out


def test_one_invalid_among_several(cli):
    result = cli("--json", "lint", "feat: a", "oops", "fix(api): b (#82)")
    assert result.code == 1
    assert result.json() == {
        "valid": False,
        "subjects": [
            {"sha": None, "subject": "feat: a", "valid": True},
            {"sha": None, "subject": "oops", "valid": False},
            {"sha": None, "subject": "fix(api): b (#82)", "valid": True},
        ],
    }


def test_json_after_subcommand(cli):
    result = cli("lint", "--json", "feat: x")
    assert result.code == 0
    assert result.json() == {"valid": True, "subjects": [{"sha": None, "subject": "feat: x", "valid": True}]}


def test_json_before_subcommand(cli):
    result = cli("--json", "lint", "feat: x")
    assert result.code == 0
    assert result.json()["valid"] is True


def test_works_outside_a_repository(cli, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli("lint", "feat: x").code == 0


def test_nothing_to_lint_is_a_usage_error(cli):
    result = cli("lint")
    assert result.code == 2
    assert result.err.startswith("semrail: ")


def test_range(cli, repo):
    base = repo.commit("chore: init")
    good = repo.commit("feat(api): add x (#82)")
    bad = repo.commit("oops", body="BREAKING CHANGE: nothing")
    fix = repo.commit("fix: y")

    result = cli("--root", str(repo.path), "--json", "lint", "--range", f"{base}..HEAD")
    assert result.code == 1
    assert result.json() == {
        "valid": False,
        "subjects": [
            {"sha": fix, "subject": "fix: y", "valid": True},
            {"sha": bad, "subject": "oops", "valid": False},
            {"sha": good, "subject": "feat(api): add x (#82)", "valid": True},
        ],
    }

    text = cli("--root", str(repo.path), "lint", "--range", f"{base}..HEAD")
    assert text.code == 1
    assert f"{bad[:7]} invalid: oops" in text.out
    assert "1 of 3 subjects invalid" in text.out


def test_range_all_valid(cli, repo):
    base = repo.commit("chore: init")
    repo.commit("feat: x")
    result = cli("--root", str(repo.path), "lint", "--range", f"{base}..HEAD")
    assert result.code == 0


def test_range_uses_enclosing_repository(cli, repo, monkeypatch):
    base = repo.commit("chore: init")
    repo.commit("oops")
    monkeypatch.chdir(repo.path)
    assert cli("lint", "--range", f"{base}..HEAD").code == 1


def test_empty_range(cli, repo):
    repo.commit("chore: init")
    result = cli("--root", str(repo.path), "--json", "lint", "--range", "HEAD..HEAD")
    assert result.code == 0
    assert result.json() == {"valid": True, "subjects": []}


def test_range_skips_merge_commits(cli, repo):
    base = repo.commit("chore: init")
    repo.git("switch", "-q", "-c", "topic")
    topic = repo.commit("feat: on topic")
    repo.git("switch", "-q", "main")
    main = repo.commit("fix: on main")
    repo.git("merge", "-q", "--no-ff", "-m", "Merge branch 'topic'", "topic")

    result = cli("--root", str(repo.path), "--json", "lint", "--range", f"{base}..HEAD")
    assert result.code == 0
    assert sorted(s["sha"] for s in result.json()["subjects"]) == sorted([topic, main])


def test_subjects_and_range_combined(cli, repo):
    base = repo.commit("chore: init")
    repo.commit("feat: x")
    result = cli("--root", str(repo.path), "--json", "lint", "oops", "--range", f"{base}..HEAD")
    assert result.code == 1
    assert [s["subject"] for s in result.json()["subjects"]] == ["oops", "feat: x"]


@pytest.mark.parametrize("rev_range", ["HEAD", "no-such-ref..HEAD"])
def test_bad_range_is_an_error(cli, repo, rev_range):
    repo.commit("chore: init")
    result = cli("--root", str(repo.path), "lint", "--range", rev_range)
    assert result.code == 2
    assert result.err.startswith("semrail: ")

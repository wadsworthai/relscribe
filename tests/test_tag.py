"""`semrail tag`: release detection, annotated tags, reconcile, conflicts and --push.

docs/design.md, Releases and tags and CLI.
"""

from __future__ import annotations

import json
import subprocess

import pytest


def pkg(name: str, version: str | None = None, **extra: object) -> str:
    data: dict[str, object] = {"name": name}
    if version is not None:
        data["version"] = version
    data.update(extra)
    return json.dumps(data, indent=2) + "\n"


def pyproject(name: str, version: str, extra: str = "") -> str:
    return f'[project]\nname = "{name}"\nversion = "{version}"\n{extra}'


WORKSPACE = {"pnpm-workspace.yaml": "packages:\n  - 'apps/*'\n", "package.json": pkg("root", private=True)}


def tag(cli, repo, rng: str, *args: str, code: int = 0) -> dict:
    result = cli("--root", str(repo.path), "--json", "tag", rng, *args)
    assert result.code == code, result.err
    return result.json()


def results(data: dict) -> list[tuple[str, str, str]]:
    return [(t["tag"], t["sha"], t["result"]) for t in data["tags"]]


def tag_commit(repo, name: str) -> str | None:
    try:
        return repo.git("rev-parse", "-q", "--verify", f"refs/tags/{name}^{{commit}}").strip()
    except subprocess.CalledProcessError:
        return None


def tags(repo) -> list[str]:
    return repo.git("tag", "--list").split()


# Release detection and annotated tags (AC 1-5)


def test_version_raise_is_tagged_with_an_annotated_tag(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    release = repo.commit("chore(release): app 1.0.0 -> 1.1.0 (#7)", {"package.json": pkg("app", "1.1.0")})

    data = tag(cli, repo, f"{init}..HEAD")
    assert data == {
        "tags": [
            {
                "tag": "app@1.1.0",
                "path": ".",
                "name": "app",
                "version": "1.1.0",
                "sha": release,
                "result": "created",
                "existing_sha": None,
            }
        ],
        "push": None,
        "warnings": [],
    }
    assert tag_commit(repo, "app@1.1.0") == release
    kind, message = repo.git("for-each-ref", "refs/tags/app@1.1.0", "--format=%(objecttype)|%(contents:subject)").strip().split("|")
    assert (kind, message) == ("tag", "app 1.1.0")


def test_pyproject_release(cli, repo):
    init = repo.commit("chore: init", {"pyproject.toml": pyproject("lib", "0.1.0")})
    release = repo.commit("chore(release): lib", {"pyproject.toml": pyproject("lib", "0.2.0")})
    assert results(tag(cli, repo, f"{init}..HEAD")) == [("lib@0.2.0", release, "created")]


@pytest.mark.parametrize(
    "files",
    [
        {"src.txt": "code\n"},
        {"package.json": pkg("app", "1.0.0", dependencies={"x": "^2.0.0"})},
        {"package.json": pkg("app", "1.0.0", engines={"version": "2"})},
        {"package.json": pkg("app", "1.0.0", description="version bump soon")},
    ],
    ids=["source", "dependency", "nested-version-key", "other-line"],
)
def test_commits_that_do_not_raise_a_version_are_not_tagged(cli, repo, files):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("feat: something", files)
    assert tag(cli, repo, f"{init}..HEAD")["tags"] == []
    assert tags(repo) == []


def test_introducing_a_unit_is_not_a_release(cli, repo):
    init = repo.commit("chore: init", {**WORKSPACE, "apps/api/package.json": pkg("@s/api", "1.0.0")})
    repo.commit("feat: add web", {"apps/web/package.json": pkg("@s/web", "0.1.0")})
    repo.commit("chore: add version to an existing manifest", {"apps/cli/package.json": pkg("@s/cli")})
    repo.commit("chore: version it", {"apps/cli/package.json": pkg("@s/cli", "0.1.0")})
    assert tag(cli, repo, f"{init}..HEAD")["tags"] == []

    release = repo.commit("chore(release): web", {"apps/web/package.json": pkg("@s/web", "0.2.0")})
    assert results(tag(cli, repo, f"{init}..HEAD")) == [("@s/web@0.2.0", release, "created")]


def test_first_commit_in_range_introducing_the_root_unit_is_not_a_release(cli, repo):
    first = repo.commit("chore: empty")
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    assert tag(cli, repo, f"{first}..HEAD")["tags"] == []


def test_lowering_a_version_is_not_a_release(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    release = repo.commit("chore(release): app", {"package.json": pkg("app", "1.1.0")})
    repo.commit('Revert "chore(release): app"', {"package.json": pkg("app", "1.0.0")})
    assert results(tag(cli, repo, f"{init}..HEAD")) == [("app@1.1.0", release, "created")]


def test_one_commit_releasing_two_units_gets_one_tag_each(cli, repo):
    init = repo.commit(
        "chore: init",
        {**WORKSPACE, "apps/api/package.json": pkg("@s/api", "1.0.0"), "apps/web/package.json": pkg("@s/web", "2.0.0")},
    )
    repo.commit("feat(api): x", {"apps/api/x.txt": "x\n"})
    release = repo.commit(
        "chore(release): @s/api 1.0.0 -> 1.1.0, @s/web 2.0.0 -> 2.0.1",
        {"apps/api/package.json": pkg("@s/api", "1.1.0"), "apps/web/package.json": pkg("@s/web", "2.0.1")},
    )
    data = tag(cli, repo, f"{init}..HEAD")
    assert results(data) == [("@s/api@1.1.0", release, "created"), ("@s/web@2.0.1", release, "created")]
    assert [t["path"] for t in data["tags"]] == ["apps/api", "apps/web"]
    assert tag_commit(repo, "@s/api@1.1.0") == tag_commit(repo, "@s/web@2.0.1") == release


def test_releases_are_listed_oldest_first(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    first = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    second = repo.commit("chore(release): 1.2.0", {"package.json": pkg("app", "1.2.0")})
    assert results(tag(cli, repo, f"{init}..HEAD")) == [
        ("app@1.1.0", first, "created"),
        ("app@1.2.0", second, "created"),
    ]


# Units as of the release commit (AC 6)


def test_tag_template_is_read_as_of_the_release_commit(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "semrail.toml": 'tag = "v{version}"\n'})
    release = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    repo.commit("chore: change the tag template", {"semrail.toml": 'tag = "{name}-{version}"\n'})
    assert results(tag(cli, repo, f"{init}..HEAD")) == [("v1.1.0", release, "created")]


def test_unit_renamed_or_removed_after_the_release(cli, repo):
    init = repo.commit(
        "chore: init",
        {**WORKSPACE, "apps/api/package.json": pkg("@s/api", "1.0.0"), "apps/old/package.json": pkg("@s/old", "1.0.0")},
    )
    release = repo.commit(
        "chore(release): both",
        {"apps/api/package.json": pkg("@s/api", "1.1.0"), "apps/old/package.json": pkg("@s/old", "1.0.1")},
    )
    repo.commit("refactor: rename api", {"apps/api/package.json": pkg("@s/server", "1.1.0")})
    repo.git("rm", "-q", "-r", "apps/old")
    repo.commit("chore: drop old")
    assert results(tag(cli, repo, f"{init}..HEAD")) == [
        ("@s/api@1.1.0", release, "created"),
        ("@s/old@1.0.1", release, "created"),
    ]


def test_dir_placeholder_uses_the_repository_directory_name(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "semrail.toml": 'tag = "{dir}-{version}"\n'})
    release = repo.commit("chore(release): 1.0.1", {"package.json": pkg("app", "1.0.1")})
    assert results(tag(cli, repo, f"{init}..HEAD")) == [(f"{repo.path.name}-1.0.1", release, "created")]


def test_configuration_error_at_a_release_commit_names_the_commit(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    release = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0"), "semrail.toml": "bogus = 1\n"})
    result = cli("--root", str(repo.path), "tag", f"{init}..HEAD")
    assert result.code == 2
    assert result.err.startswith(f"semrail: {release[:7]}: semrail.toml: unknown key")
    assert "Traceback" not in result.err


# True merges (AC 7)


def test_release_merged_with_a_true_merge_is_tagged_on_its_own_commit(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("switch", "-q", "-c", "release")
    release = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    repo.git("switch", "-q", "main")
    repo.commit("docs: meanwhile", {"README.md": "x\n"})
    repo.git("merge", "-q", "--no-ff", "-m", "Merge branch 'release'", "release")
    merge = repo.git("rev-parse", "HEAD").strip()

    assert results(tag(cli, repo, f"{init}..{merge}")) == [("app@1.1.0", release, "created")]


# Idempotence and conflicts (AC 8-9)


def test_second_run_reports_existing_tags(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    release = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    tag(cli, repo, f"{init}..HEAD")
    before = repo.git("rev-parse", "refs/tags/app@1.1.0").strip()

    assert results(tag(cli, repo, f"{init}..HEAD")) == [("app@1.1.0", release, "existing")]
    assert repo.git("rev-parse", "refs/tags/app@1.1.0").strip() == before


def test_tag_on_another_commit_is_a_conflict_and_other_tags_are_still_created(cli, repo):
    init = repo.commit(
        "chore: init",
        {**WORKSPACE, "apps/api/package.json": pkg("@s/api", "1.0.0"), "apps/web/package.json": pkg("@s/web", "1.0.0")},
    )
    repo.git("tag", "-a", "-m", "wrong", "@s/api@1.1.0", init)
    release = repo.commit(
        "chore(release): both",
        {"apps/api/package.json": pkg("@s/api", "1.1.0"), "apps/web/package.json": pkg("@s/web", "1.1.0")},
    )
    data = tag(cli, repo, f"{init}..HEAD", code=4)
    assert data["tags"][0] == {
        "tag": "@s/api@1.1.0",
        "path": "apps/api",
        "name": "@s/api",
        "version": "1.1.0",
        "sha": release,
        "result": "conflict",
        "existing_sha": init,
    }
    assert results(data)[1] == ("@s/web@1.1.0", release, "created")
    assert tag_commit(repo, "@s/api@1.1.0") == init
    assert tag_commit(repo, "@s/web@1.1.0") == release


def test_same_tag_twice_in_one_range_conflicts_with_the_first(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    first = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    repo.commit("revert", {"package.json": pkg("app", "1.0.0")})
    again = repo.commit("chore(release): 1.1.0 again", {"package.json": pkg("app", "1.1.0")})
    data = tag(cli, repo, f"{init}..HEAD", code=4)
    assert results(data) == [("app@1.1.0", first, "created"), ("app@1.1.0", again, "conflict")]
    assert data["tags"][1]["existing_sha"] == first


# Reconcile (AC 10)


def test_reconcile_tags_the_latest_untagged_release_before_the_range(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    skipped = repo.commit("chore(release): 1.2.0", {"package.json": pkg("app", "1.2.0")})
    before = repo.commit("docs: x", {"README.md": "x\n"})
    release = repo.commit("chore(release): 1.3.0", {"package.json": pkg("app", "1.3.0")})

    assert results(tag(cli, repo, f"{before}..HEAD")) == [
        ("app@1.2.0", skipped, "created"),
        ("app@1.3.0", release, "created"),
    ]
    assert "app@1.1.0" not in tags(repo)


def test_reconcile_includes_the_from_commit(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    release = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    assert results(tag(cli, repo, f"{release}..HEAD")) == [("app@1.1.0", release, "created")]
    assert init  # the introduction is not a release, so nothing older is tagged


def test_reconcile_reports_an_already_tagged_latest_release_as_existing(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    release = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    repo.git("tag", "-a", "-m", "app 1.1.0", "app@1.1.0")
    head = repo.commit("docs: x", {"README.md": "x\n"})
    assert results(tag(cli, repo, f"{head}..HEAD")) == [("app@1.1.0", release, "existing")]


def test_reconcile_is_per_unit(cli, repo):
    repo.commit(
        "chore: init",
        {**WORKSPACE, "apps/api/package.json": pkg("@s/api", "1.0.0"), "apps/web/package.json": pkg("@s/web", "1.0.0")},
    )
    api = repo.commit("chore(release): api", {"apps/api/package.json": pkg("@s/api", "1.1.0")})
    web = repo.commit("chore(release): web", {"apps/web/package.json": pkg("@s/web", "1.0.1")})
    head = repo.commit("docs: x", {"README.md": "x\n"})
    assert sorted(results(tag(cli, repo, f"{head}..HEAD"))) == [
        ("@s/api@1.1.0", api, "created"),
        ("@s/web@1.0.1", web, "created"),
    ]


def test_never_released_unit_has_nothing_to_reconcile(cli, repo):
    head = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    assert tag(cli, repo, f"{head}..HEAD")["tags"] == []


def test_from_without_any_unit(cli, repo):
    first = repo.commit("chore: readme", {"README.md": "x\n"})
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    release = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    assert results(tag(cli, repo, f"{first}..HEAD")) == [("app@1.1.0", release, "created")]


# --push (AC 11)


@pytest.fixture
def remote(repo, tmp_path):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    repo.git("remote", "add", "origin", str(bare))
    return bare


def remote_tags(bare) -> dict[str, str]:
    out = subprocess.run(["git", "-C", str(bare), "tag", "--list"], capture_output=True, text=True, check=True).stdout
    return {
        name: subprocess.run(
            ["git", "-C", str(bare), "rev-parse", f"refs/tags/{name}^{{commit}}"], capture_output=True, text=True, check=True
        ).stdout.strip()
        for name in out.split()
    }


def test_push_sends_only_the_created_tags(cli, repo, remote):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    old = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    repo.git("tag", "-a", "-m", "app 1.1.0", "app@1.1.0")
    repo.git("tag", "-a", "-m", "unrelated", "unrelated")
    new = repo.commit("chore(release): 1.2.0", {"package.json": pkg("app", "1.2.0")})

    data = tag(cli, repo, f"{old}..HEAD", "--push", "origin")
    assert results(data) == [("app@1.1.0", old, "existing"), ("app@1.2.0", new, "created")]
    assert data["push"] == {"remote": "origin", "pushed": ["app@1.2.0"], "rejected": []}
    assert remote_tags(remote) == {"app@1.2.0": new}
    assert init


def test_push_with_nothing_created_pushes_nothing(cli, repo, remote):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    data = tag(cli, repo, f"{init}..HEAD", "--push", "origin")
    assert data["push"] == {"remote": "origin", "pushed": [], "rejected": []}
    assert remote_tags(remote) == {}


def test_push_rejected_by_the_remote_is_a_conflict(cli, repo, remote, tmp_path):
    init = repo.commit(
        "chore: init",
        {**WORKSPACE, "apps/api/package.json": pkg("@s/api", "1.0.0"), "apps/web/package.json": pkg("@s/web", "1.0.0")},
    )
    # The remote already has the api tag on another commit, which this clone never fetched.
    repo.git("tag", "-a", "-m", "elsewhere", "@s/api@1.1.0", init)
    repo.git("push", "-q", "origin", "refs/tags/@s/api@1.1.0")
    repo.git("tag", "-d", "@s/api@1.1.0")
    release = repo.commit(
        "chore(release): both",
        {"apps/api/package.json": pkg("@s/api", "1.1.0"), "apps/web/package.json": pkg("@s/web", "1.1.0")},
    )
    data = tag(cli, repo, f"{init}..HEAD", "--push", "origin", code=4)
    assert results(data) == [("@s/api@1.1.0", release, "created"), ("@s/web@1.1.0", release, "created")]
    assert data["push"] == {"remote": "origin", "pushed": ["@s/web@1.1.0"], "rejected": ["@s/api@1.1.0"]}
    assert remote_tags(remote) == {"@s/api@1.1.0": init, "@s/web@1.1.0": release}


def test_push_to_an_unknown_remote_is_a_git_error(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    result = cli("--root", str(repo.path), "tag", f"{init}..HEAD", "--push", "nowhere")
    assert result.code == 2
    assert result.err.startswith("semrail: ")
    assert "Traceback" not in result.err


# Usage and git errors (AC 12)


@pytest.mark.parametrize("rng", ["main", "a...b", "..HEAD", "HEAD..", "a..b..c"])
def test_bad_ranges_are_usage_errors(cli, repo, rng):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    result = cli("--root", str(repo.path), "tag", rng)
    assert result.code == 2
    assert result.err.startswith("semrail: tag: ")


def test_unknown_revision_is_a_git_error(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    result = cli("--root", str(repo.path), "tag", "nope..HEAD")
    assert result.code == 2
    assert result.err.startswith("semrail: ")
    assert "Traceback" not in result.err


def test_range_is_required(cli, repo):
    assert cli("--root", str(repo.path), "tag").code == 2


# Text output (AC 13)


def test_text_output(cli, repo, remote):
    init = repo.commit(
        "chore: init",
        {**WORKSPACE, "apps/api/package.json": pkg("@s/api", "1.0.0"), "apps/web/package.json": pkg("@s/web", "1.0.0")},
    )
    web_old = repo.commit("chore(release): web", {"apps/web/package.json": pkg("@s/web", "1.0.1")})
    repo.git("tag", "-a", "-m", "x", "@s/web@1.0.1")
    repo.git("tag", "-a", "-m", "x", "@s/api@1.1.0", init)
    release = repo.commit(
        "chore(release): both",
        {"apps/api/package.json": pkg("@s/api", "1.1.0"), "apps/web/package.json": pkg("@s/web", "1.1.0")},
    )
    result = cli("--root", str(repo.path), "tag", f"{web_old}..HEAD", "--push", "origin")
    assert result.code == 4
    assert result.out.splitlines() == [
        f"existing @s/web@1.0.1 {web_old[:7]}",
        f"conflict @s/api@1.1.0 {release[:7]}: already on {init[:7]}",
        f"created @s/web@1.1.0 {release[:7]}",
        "pushed 1 tag to origin",
    ]


def test_text_output_with_nothing_to_tag(cli, repo):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    result = cli("--root", str(repo.path), "tag", f"{init}..HEAD")
    assert (result.code, result.out) == (0, "no releases to tag\n")


def test_text_output_for_a_rejected_push(cli, repo, remote):
    init = repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("tag", "-a", "-m", "elsewhere", "app@1.1.0", init)
    repo.git("push", "-q", "origin", "refs/tags/app@1.1.0")
    repo.git("tag", "-d", "app@1.1.0")
    release = repo.commit("chore(release): 1.1.0", {"package.json": pkg("app", "1.1.0")})
    result = cli("--root", str(repo.path), "tag", f"{init}..HEAD", "--push", "origin")
    assert result.code == 4
    assert result.out.splitlines() == [
        f"created app@1.1.0 {release[:7]}",
        "pushed 0 tags to origin",
        "rejected by origin: app@1.1.0",
    ]


# Shallow clones (AC 14)


def test_shallow_clone_warns(cli, repo, tmp_path):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("fix: a", {"a": "1"})
    repo.commit("fix: b", {"b": "1"})
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", "--depth", "2", f"file://{repo.path}", str(clone)], check=True)

    result = cli("--root", str(clone), "--json", "tag", "HEAD~1..HEAD")
    assert result.code == 0, result.err
    assert result.json()["warnings"] == ["shallow clone: history may be incomplete; fetch full history and tags"]

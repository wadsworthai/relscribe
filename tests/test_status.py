"""`relscribe status`: base resolution, each unit's commits, next versions and warnings.

docs/design.md, Selecting a unit's commits, Versioning and CLI.
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


def status(cli, repo, *args: str):
    result = cli("--root", str(repo.path), "--json", "status", *args)
    assert result.code == 0, result.err
    return {u["path"]: u for u in result.json()["units"]}


def shas(unit: dict) -> list[str]:
    return [c["sha"] for c in unit["commits"]]


def workspace(repo, *members: str) -> None:
    files = {"pnpm-workspace.yaml": "packages:\n  - 'apps/*'\n", "package.json": pkg("root", private=True)}
    for member in members:
        files[f"apps/{member}/package.json"] = pkg(f"@scope/{member}", "1.0.0")
    repo.commit("chore: init", files)


# Base resolution (AC 1-3)


def test_tag_of_the_current_version_is_the_base(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    tagged = repo.commit("feat: before the tag", {"a.txt": "1\n"})
    repo.git("tag", "-a", "app@1.0.0", "-m", "app 1.0.0")
    fix = repo.commit("fix: after the tag", {"a.txt": "2\n"})
    feat = repo.commit("feat(0037:api:session): add x (#82)", {"a.txt": "3\n"})

    unit = status(cli, repo)["."]
    assert unit == {
        "path": ".",
        "name": "app",
        "version": "1.0.0",
        "base": {"kind": "tag", "sha": tagged, "tag": "app@1.0.0"},
        "commits": [
            {"sha": feat, "subject": "feat(0037:api:session): add x (#82)", "type": "feat", "scope": "0037:api:session", "breaking": False},
            {"sha": fix, "subject": "fix: after the tag", "type": "fix", "scope": None, "breaking": False},
        ],
        "bump": "minor",
        "next": "1.1.0",
        "warnings": [],
    }


def test_tag_template_from_config(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "relscribe.toml": 'tag = "v{version}"\n'})
    tagged = repo.commit("feat: x", {"a.txt": "1\n"})
    repo.git("tag", "v1.0.0")  # a lightweight tag works too
    repo.commit("fix: y", {"a.txt": "2\n"})
    assert status(cli, repo)["."]["base"] == {"kind": "tag", "sha": tagged, "tag": "v1.0.0"}


def test_last_version_change_in_package_json(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("feat: released in 1.1.0")
    release = repo.commit("chore(release): app 1.0.0 -> 1.1.0", {"package.json": pkg("app", "1.1.0")})
    # Later manifest edits that touch "version" lines but not the unit's version.
    deps = repo.commit(
        "fix: bump a dependency",
        {"package.json": pkg("app", "1.1.0", dependencies={"lib": "^2.0.0"}, engines={"version": "2"})},
    )
    feat = repo.commit("feat: new", {"src/a.js": "a\n"})

    unit = status(cli, repo)["."]
    assert unit["base"] == {"kind": "version-change", "sha": release, "tag": None}
    assert shas(unit) == [feat, deps]
    assert unit["next"] == "1.2.0"


def test_last_version_change_in_pyproject(cli, repo):
    repo.commit("chore: init", {"pyproject.toml": pyproject("app", "0.1.0", '[tool.x]\nversion = "1"\n')})
    release = repo.commit("chore(release): app 0.1.0 -> 0.2.0", {"pyproject.toml": pyproject("app", "0.2.0", '[tool.x]\nversion = "1"\n')})
    other = repo.commit("fix: other table", {"pyproject.toml": pyproject("app", "0.2.0", '[tool.x]\nversion = "2"\n')})

    unit = status(cli, repo)["."]
    assert unit["base"] == {"kind": "version-change", "sha": release, "tag": None}
    assert shas(unit) == [other]
    assert unit["next"] == "0.2.1"


def test_version_set_in_the_first_commit_uses_the_whole_history(cli, repo):
    first = repo.commit("feat: scaffold the app", {"package.json": pkg("app", "0.1.0")})
    fix = repo.commit("fix: x", {"a.txt": "a\n"})

    unit = status(cli, repo)["."]
    assert unit["base"] == {"kind": "history", "sha": None, "tag": None}
    assert shas(unit) == [fix, first]
    assert unit["next"] == "0.2.0"


def test_version_added_to_an_existing_manifest_is_not_a_change(cli, repo):
    early = repo.commit("feat: early", {"package.json": pkg("app")})
    added = repo.commit("chore: add a version", {"package.json": pkg("app", "0.1.0")})

    unit = status(cli, repo)["."]
    assert unit["base"]["kind"] == "history"
    assert shas(unit) == [added, early]


# Path attribution (AC 4-7)


def test_commits_are_attributed_by_path(cli, repo):
    workspace(repo, "a", "b")
    only_a = repo.commit("feat: a only", {"apps/a/x.js": "1\n"})
    both = repo.commit("fix: both", {"apps/a/x.js": "2\n", "apps/b/y.js": "2\n"})
    repo.commit("feat: outside every unit", {"README.md": "hi\n", "tools/t.sh": "x\n"})

    units = status(cli, repo)
    assert list(units) == ["apps/a", "apps/b"]
    a, b = units["apps/a"], units["apps/b"]
    # The init commit introduced the versions, so both units count their whole history.
    assert shas(a)[:2] == [both, only_a]
    assert shas(b)[:1] == [both]
    assert (a["next"], b["next"]) == ("1.1.0", "1.0.1")
    assert all("outside" not in c["subject"] for u in units.values() for c in u["commits"])


def test_commit_outside_every_unit_bumps_nothing(cli, repo):
    workspace(repo, "a")
    repo.git("tag", "@scope/a@1.0.0")
    repo.commit("feat: outside", {"README.md": "hi\n"})
    unit = status(cli, repo)["apps/a"]
    assert unit["commits"] == []
    assert (unit["bump"], unit["next"]) == (None, None)


@pytest.mark.parametrize("scope", ["global", "unit"])
def test_exclude_drops_commits_whose_unit_files_all_match(cli, repo, scope):
    config = 'exclude = ["tests/**", "**/*.md"]\n'
    if scope == "unit":
        config = '[units."apps/a"]\n' + config
    workspace(repo, "a")
    repo.commit("chore: config", {"relscribe.toml": config})
    repo.git("tag", "@scope/a@1.0.0")
    repo.commit("feat: tests only", {"apps/a/tests/t.js": "1\n"})
    repo.commit("feat: docs only", {"apps/a/README.md": "1\n", "apps/a/docs/deep/x.md": "1\n"})
    mixed = repo.commit("fix: tests and source", {"apps/a/tests/t.js": "2\n", "apps/a/src/s.js": "2\n"})
    # A tests/ directory outside the unit's own tests/ is not excluded by "tests/**".
    nested = repo.commit("fix: nested tests dir", {"apps/a/src/tests/u.js": "1\n"})

    unit = status(cli, repo)["apps/a"]
    assert shas(unit) == [nested, mixed]
    assert unit["next"] == "1.0.1"


def test_exclude_in_a_root_unit(cli, repo):
    repo.commit("chore: init", {"pyproject.toml": pyproject("app", "1.0.0"), "relscribe.toml": 'exclude = ["tests/**"]\n'})
    repo.git("tag", "app@1.0.0")
    repo.commit("feat: tests only", {"tests/t.py": "1\n"})
    src = repo.commit("fix: source", {"src/app.py": "1\n"})
    assert shas(status(cli, repo)["."]) == [src]


def test_nested_unit_commits_do_not_count_for_the_outer_unit(cli, repo):
    repo.commit(
        "chore: init",
        {
            "pnpm-workspace.yaml": "packages:\n  - '.'\n  - 'apps/*'\n",
            "package.json": pkg("root", "1.0.0"),
            "apps/a/package.json": pkg("a", "1.0.0"),
        },
    )
    repo.git("tag", "root@1.0.0")
    repo.git("tag", "a@1.0.0")
    inner = repo.commit("feat: inner", {"apps/a/x.js": "1\n"})
    outer = repo.commit("fix: outer", {"lib/y.js": "1\n"})

    units = status(cli, repo)
    assert shas(units["."]) == [outer]
    assert shas(units["apps/a"]) == [inner]


def test_merge_commits_are_skipped(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("tag", "app@1.0.0")
    repo.git("switch", "-q", "-c", "topic")
    topic = repo.commit("feat: on topic", {"t.txt": "t\n"})
    repo.git("switch", "-q", "main")
    main = repo.commit("fix: on main", {"m.txt": "m\n"})
    repo.git("merge", "-q", "--no-ff", "-m", "Merge branch 'topic'", "topic")

    unit = status(cli, repo)["."]
    assert sorted(shas(unit)) == sorted([topic, main])
    assert unit["warnings"] == []


# Versioning (AC 8-9)


@pytest.mark.parametrize(
    ("version", "subjects", "body", "bump", "next"),
    [
        ("1.2.3", ["fix: a", "perf: b", "refactor: c"], "", "patch", "1.2.4"),
        ("1.2.3", ["fix: a", "feat: b"], "", "minor", "1.3.0"),
        ("1.2.3", ["feat!: b"], "", "major", "2.0.0"),
        ("1.2.3", ["fix: b"], "BREAKING CHANGE: gone", "major", "2.0.0"),
        ("0.3.4", ["feat(api)!: b"], "", "minor", "0.4.0"),
        ("0.3.4", ["fix: a"], "", "patch", "0.3.5"),
        ("1.2.3", ["docs: a", "chore: b", "ci: c"], "", None, None),
        ("1.2.3", ["Feat: case-insensitive type"], "", "minor", "1.3.0"),
    ],
)
def test_bump_and_next_version(cli, repo, version, subjects, body, bump, next):
    repo.commit("chore: init", {"package.json": pkg("app", version)})
    repo.git("tag", f"app@{version}")
    for i, subject in enumerate(subjects):
        repo.commit(subject, {f"f{i}.txt": subject}, body=body)
    unit = status(cli, repo)["."]
    assert (unit["bump"], unit["next"]) == (bump, next)


def test_breaking_flag_in_commits(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("tag", "app@1.0.0")
    repo.commit("fix(api): x", {"x": "x"}, body="BREAKING-CHANGE: gone")
    commit = status(cli, repo)["."]["commits"][0]
    assert (commit["type"], commit["scope"], commit["breaking"]) == ("fix", "api", True)


@pytest.mark.parametrize(
    ("bump", "subjects", "expected"),
    [
        ('docs = "patch"', ["docs: a"], "1.0.1"),  # adds a type
        ('feat = "patch"', ["feat: a"], "1.0.1"),  # replaces a default
        ('feat = "patch"', ["feat: a", "refactor: b"], "1.0.1"),  # the other defaults still apply
        ('docs = "patch"', ["feat: a", "docs: b"], "1.1.0"),
        ('chore = "major"', ["chore: a"], "2.0.0"),
    ],
)
def test_bump_overrides_merge_over_the_defaults(cli, repo, bump, subjects, expected):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0"), "relscribe.toml": f"[bump]\n{bump}\n"})
    repo.git("tag", "app@1.0.0")
    for i, subject in enumerate(subjects):
        repo.commit(subject, {f"f{i}.txt": subject})
    assert status(cli, repo)["."]["next"] == expected


def test_per_unit_bump_override(cli, repo):
    workspace(repo, "a", "b")
    repo.commit("chore: config", {"relscribe.toml": '[units."apps/a".bump]\ndocs = "patch"\n'})
    repo.commit("docs: both", {"apps/a/README.md": "1\n", "apps/b/README.md": "1\n"})
    units = status(cli, repo)
    assert (units["apps/a"]["next"], units["apps/b"]["next"]) == ("1.0.1", None)


# Warnings and output (AC 10-11)


def test_unparseable_subjects_are_warnings(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.git("tag", "app@1.0.0")
    wip = repo.commit("wip", {"a": "1"})
    feat = repo.commit("feat: real", {"b": "1"})
    repo.commit("Update README.md", {"c": "1"})

    result = cli("--root", str(repo.path), "--json", "status")
    assert result.code == 0
    unit = result.json()["units"][0]
    assert unit["commits"][2] == {"sha": wip, "subject": "wip", "type": None, "scope": None, "breaking": False}
    assert unit["commits"][1]["sha"] == feat
    assert unit["warnings"] == [
        f"{unit['commits'][0]['sha'][:7]}: not a Conventional Commit: Update README.md",
        f"{wip[:7]}: not a Conventional Commit: wip",
    ]
    assert (unit["bump"], unit["next"]) == ("minor", "1.1.0")


def test_only_unparseable_subjects_bump_nothing(cli, repo):
    repo.commit("Initial commit", {"package.json": pkg("app", "1.0.0")})
    unit = status(cli, repo)["."]
    assert (unit["bump"], unit["next"]) == (None, None)
    assert len(unit["warnings"]) == 1


def test_text_output(cli, repo):
    workspace(repo, "a", "b")
    repo.git("tag", "@scope/a@1.0.0")
    tag_sha = repo.git("rev-parse", "HEAD").strip()
    feat = repo.commit("feat(0037:api:session): add x (#82)", {"apps/a/x.js": "1\n"})
    wip = repo.commit("wip", {"apps/a/y.js": "1\n"})

    result = cli("--root", str(repo.path), "status")
    assert result.code == 0
    lines = result.out.splitlines()
    a_start = lines.index("@scope/a (apps/a): 1.0.0 -> 1.1.0 (minor)")
    assert lines[a_start + 1 : a_start + 5] == [
        f"  base: tag @scope/a@1.0.0 ({tag_sha[:7]})",
        f"  {wip[:7]} wip",
        f"  {feat[:7]} feat(0037:api:session): add x (#82)",
        f"  warning: {wip[:7]}: not a Conventional Commit: wip",
    ]
    b_start = lines.index("@scope/b (apps/b): 1.0.0, no release")
    assert lines[b_start + 1] == "  base: whole history"


def test_text_output_version_change_base(cli, repo):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    release = repo.commit("chore(release): app 1.0.0 -> 1.0.1", {"package.json": pkg("app", "1.0.1")})
    out = cli("--root", str(repo.path), "status").out.splitlines()
    assert out == ["app (.): 1.0.1, no release", f"  base: version change ({release[:7]})"]


def test_json_after_subcommand_and_enclosing_repository(cli, repo, monkeypatch):
    repo.commit("feat: init", {"package.json": pkg("app", "1.0.0")})
    monkeypatch.chdir(repo.path)
    result = cli("status", "--json")
    assert result.code == 0
    assert result.json()["units"][0]["next"] == "1.1.0"


# Errors (AC 12-13)


@pytest.mark.parametrize(
    "files",
    [
        {"package.json": pkg("app", "1.0.0"), "relscribe.toml": "unknown = 1\n"},
        {"package.json": pkg("app", "1.0.0"), "relscribe.toml": '[bump]\nfeat = "huge"\n'},
        {"package.json": pkg("app", "1.0.0"), "relscribe.toml": 'tag = "{nope}"\n'},
        {"package.json": pkg("app", "1.0.0"), "relscribe.toml": "not toml ==\n"},
        {"package.json": pkg("app", "1.0"), "relscribe.toml": ""},
        {"package.json": pkg("app", "v1.0.0")},
        {"package.json": pkg("app", "1.0.0-rc.1")},
        {"package.json": "{not json"},
        {"README.md": "no manifest\n"},
    ],
)
def test_configuration_errors_exit_2(cli, repo, files):
    repo.commit("chore: init", files)
    result = cli("--root", str(repo.path), "status")
    assert result.code == 2
    assert result.err.startswith("relscribe: ")
    assert result.out == ""


def test_repository_without_commits_is_an_error(cli, repo):
    repo.write({"package.json": pkg("app", "1.0.0")})
    result = cli("--root", str(repo.path), "status")
    assert result.code == 2
    assert result.err.startswith("relscribe: ")


def test_outside_a_repository_is_an_error(cli, tmp_path):
    (tmp_path / "package.json").write_text(pkg("app", "1.0.0"))
    result = cli("--root", str(tmp_path), "status")
    assert result.code == 2
    assert result.err.startswith("relscribe: ")


# Shallow clones (AC 14)


def test_shallow_clone_warns_unless_the_base_is_a_tag(cli, repo, tmp_path):
    repo.commit("chore: init", {"package.json": pkg("app", "1.0.0")})
    repo.commit("fix: a", {"a": "1"})
    repo.commit("fix: b", {"b": "1"})
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{repo.path}", str(clone)], check=True)

    result = cli("--root", str(clone), "--json", "status")
    assert result.code == 0
    assert result.json()["units"][0]["warnings"] == [
        "shallow clone: history may be incomplete; fetch full history and tags"
    ]

    subprocess.run(["git", "-C", str(clone), "tag", "app@1.0.0"], check=True)
    result = cli("--root", str(clone), "--json", "status")
    assert result.json()["units"][0]["warnings"] == []

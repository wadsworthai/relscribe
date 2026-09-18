"""Unit discovery, semrail.toml, and reading and writing versions (docs/design.md, Units).

These call `semrail.units` directly to cover writing versions and every configuration rule;
`semrail status` (tests/test_status.py) covers units through the CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from semrail.units import ConfigError, Unit, discover, write_version


def pkg(name: str | None, version: str | None = None, **extra: object) -> str:
    data: dict[str, object] = {}
    if name is not None:
        data["name"] = name
    if version is not None:
        data["version"] = version
    data.update(extra)
    return json.dumps(data, indent=2) + "\n"


def pyproject(name: str, version: str | None, extra: str = "") -> str:
    lines = ["[project]", f'name = "{name}"']
    lines.append(f'version = "{version}"' if version else 'dynamic = ["version"]')
    return "\n".join(lines) + "\n" + extra


def summary(units: list[Unit]) -> list[tuple[str, str, str, str, str]]:
    return [(u.path, u.name, u.dir, u.manifest, u.version) for u in units]


def unit(units: list[Unit], path: str) -> Unit:
    return next(u for u in units if u.path == path)


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


# Discovery (AC 1-5)


def test_pnpm_workspace_discovers_versioned_members(repo):
    repo.write(
        {
            "pnpm-workspace.yaml": (
                "# the workspace\n"
                "packages:\n"
                "  - 'apps/*'   # applications\n"
                '  - "packages/*"\n'
                "\n"
                "  - '!packages/internal'\n"
                "  - libs/**\n"
                "catalog:\n"
                "  react: ^18\n"
            ),
            "package.json": pkg("root", private=True),
            "apps/web/package.json": pkg("@scope/web", "1.2.0"),
            "apps/api/package.json": pkg("@scope/api", "0.34.0"),
            "apps/docs/README.md": "no manifest\n",
            "packages/ui/package.json": pkg("@scope/ui", "2.0.1"),
            "packages/config/package.json": pkg("@scope/config", private=True),
            "packages/internal/package.json": pkg("@scope/internal", "1.0.0"),
            "libs/a/package.json": pkg("a", "3.0.0"),
            "libs/a/node_modules/dep/package.json": pkg("dep", "9.9.9"),
        }
    )
    assert summary(discover(repo.path)) == [
        ("apps/api", "@scope/api", "api", "package.json", "0.34.0"),
        ("apps/web", "@scope/web", "web", "package.json", "1.2.0"),
        ("libs/a", "a", "a", "package.json", "3.0.0"),
        ("packages/ui", "@scope/ui", "ui", "package.json", "2.0.1"),
    ]


def test_pnpm_workspace_without_packages_falls_through(repo):
    repo.write(
        {
            "pnpm-workspace.yaml": "catalog:\n  react: ^18\n",
            "package.json": pkg("root", workspaces=["packages/*"]),
            "packages/ui/package.json": pkg("ui", "1.0.0"),
        }
    )
    assert summary(discover(repo.path)) == [("packages/ui", "ui", "ui", "package.json", "1.0.0")]


def test_pnpm_workspace_flow_list_is_an_error(repo):
    repo.write({"pnpm-workspace.yaml": "packages: [apps/*, packages/*]\n"})
    with pytest.raises(ConfigError, match="pnpm-workspace.yaml"):
        discover(repo.path)


def test_package_json_workspaces(repo):
    repo.write(
        {
            "package.json": pkg("root", workspaces=["./packages/*/", "tools/cli"]),
            "packages/ui/package.json": pkg("ui", "1.0.0"),
            "tools/cli/package.json": pkg("cli", "0.2.0"),
            "tools/other/package.json": pkg("other", "0.3.0"),
        }
    )
    assert summary(discover(repo.path)) == [
        ("packages/ui", "ui", "ui", "package.json", "1.0.0"),
        ("tools/cli", "cli", "cli", "package.json", "0.2.0"),
    ]


def test_uv_workspace(repo):
    repo.write(
        {
            "pyproject.toml": pyproject(
                "root", "0.1.0", '\n[tool.uv.workspace]\nmembers = ["libs/*"]\nexclude = ["libs/skip"]\n'
            ),
            "libs/one/pyproject.toml": pyproject("one", "1.0.0"),
            "libs/skip/pyproject.toml": pyproject("skip", "1.0.0"),
            "libs/dyn/pyproject.toml": pyproject("dyn", None),
        }
    )
    assert summary(discover(repo.path)) == [("libs/one", "one", "one", "pyproject.toml", "1.0.0")]


def test_single_python_package(repo):
    repo.write({"pyproject.toml": pyproject("semrail", "0.0.0")})
    assert summary(discover(repo.path)) == [(".", "semrail", "repo", "pyproject.toml", "0.0.0")]


def test_single_root_prefers_versioned_package_json(repo):
    repo.write({"package.json": pkg("web", "2.0.0"), "pyproject.toml": pyproject("py", "1.0.0")})
    assert summary(discover(repo.path)) == [(".", "web", "repo", "package.json", "2.0.0")]


def test_single_root_falls_back_to_pyproject(repo):
    repo.write({"package.json": pkg("tooling", private=True), "pyproject.toml": pyproject("py", "1.0.0")})
    assert summary(discover(repo.path)) == [(".", "py", "repo", "pyproject.toml", "1.0.0")]


def test_single_root_without_a_version_is_an_error(repo):
    repo.write({"package.json": pkg("tooling")})
    with pytest.raises(ConfigError, match="version"):
        discover(repo.path)


# Versions and names (AC 6)


@pytest.mark.parametrize(
    "files",
    [
        {"package.json": pkg("a", "1.2.3-beta.1")},
        {"package.json": pkg("a", "01.2.3")},
        {"package.json": pkg("a", "1.2")},
        {"package.json": "{ not json"},
        {"pyproject.toml": "[project\nname = 'a'"},
        {"package.json": pkg(None, "1.2.3")},
        {"pyproject.toml": '[project]\nversion = "1.2.3"\n'},
    ],
    ids=["prerelease", "leading-zero", "two-parts", "bad-json", "bad-toml", "no-name-json", "no-name-toml"],
)
def test_invalid_manifests_are_errors(repo, files):
    repo.write(files)
    with pytest.raises(ConfigError):
        discover(repo.path)


# semrail.toml (AC 7-9)


def test_defaults_without_semrail_toml(repo):
    repo.write({"package.json": pkg("@scope/api", "1.0.0")})
    [u] = discover(repo.path)
    assert (u.tag, u.changelog, u.exclude, u.sync, u.bump) == ("{name}@{version}", True, (), (), {})
    assert u.tag_name("1.2.3") == "@scope/api@1.2.3"


@pytest.mark.parametrize(
    ("template", "expected"),
    [("v{version}", "v1.2.3"), ("{dir}-v{version}", "repo-v1.2.3"), ("{name}/{version}", "@scope/api/1.2.3")],
)
def test_tag_templates(repo, template, expected):
    repo.write({"package.json": pkg("@scope/api", "1.0.0"), "semrail.toml": f'tag = "{template}"\n'})
    [u] = discover(repo.path)
    assert u.tag_name("1.2.3") == expected


MONOREPO = {
    "pnpm-workspace.yaml": "packages:\n  - apps/*\n",
    "apps/api/package.json": pkg("@scope/api", "1.4.0"),
    "apps/web/package.json": pkg("@scope/web", "0.2.0"),
}


def test_global_keys_and_per_unit_overrides(repo):
    repo.write(
        {
            **MONOREPO,
            "semrail.toml": (
                'tag = "{dir}-v{version}"\n'
                "changelog = false\n"
                'exclude = ["**/*.test.ts"]\n'
                'bump = { perf = "minor" }\n'
                "\n"
                '[units."apps/api"]\n'
                'tag = "api-v{version}"\n'
                'exclude = ["tests/**"]\n'
                'bump = { docs = "patch" }\n'
            ),
        }
    )
    units = discover(repo.path)
    api, web = unit(units, "apps/api"), unit(units, "apps/web")
    assert (api.tag_name("1.0.0"), api.changelog, api.exclude, api.bump) == (
        "api-v1.0.0",
        False,
        ("tests/**",),
        {"docs": "patch"},
    )
    assert (web.tag_name("1.0.0"), web.changelog, web.exclude, web.bump) == (
        "web-v1.0.0",
        False,
        ("**/*.test.ts",),
        {"perf": "minor"},
    )


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ('tags = "x"\n', "tags"),
        ('changelog = "no"\n', "changelog"),
        ('exclude = "tests/**"\n', "exclude"),
        ("exclude = [1]\n", "exclude"),
        ('sync = [{ file = "a.json" }]\n', "sync"),
        ('sync = [{ file = "a.json", pattern = "(x)", extra = 1 }]\n', "sync"),
        ('sync = "a.json"\n', "sync"),
        ('sync = [{ file = "a.json", pattern = "no group" }]\n', "capture group"),
        ('sync = [{ file = "a.json", pattern = "(a)(b)" }]\n', "capture group"),
        ('sync = [{ file = "a.json", pattern = "(unclosed" }]\n', "pattern"),
        ('bump = { feat = "huge" }\n', "bump"),
        ('bump = "minor"\n', "bump"),
        ('tag = "{nam}@{version}"\n', "tag"),
        ("tag = 1\n", "tag"),
        ('[units."apps/nope"]\ntag = "x"\n', "apps/nope"),
        ('[units."apps/api"]\nunits = {}\n', "units"),
        ('[units."apps/api"]\nchangelog = 1\n', "changelog"),
        ("tag = \n", "semrail.toml"),
    ],
)
def test_invalid_semrail_toml_is_an_error(repo, toml, message):
    repo.write({**MONOREPO, "semrail.toml": toml})
    with pytest.raises(ConfigError, match=message):
        discover(repo.path)


# Writing versions (AC 10-13)


def test_write_package_json_changes_only_the_top_level_version(repo):
    original = (
        "{\r\n"
        '    "name": "@scope/api",\r\n'
        '    "description": "a \\"version\\": {\\"0.34.0\\"} [string]",\r\n'
        '    "engines": {"version": "0.34.0", "list": [{"version": "0.34.0"}]},\r\n'
        '    "version":"0.34.0",\r\n'
        '    "scripts": {}\r\n'
        "}\r\n"
    )
    repo.write({"pnpm-workspace.yaml": "packages:\n  - apps/*\n", "apps/api/package.json": original})
    [u] = discover(repo.path)
    assert write_version(repo.path, u, "0.35.0") == ["apps/api/package.json"]
    expected = original.replace('"version":"0.34.0",', '"version":"0.35.0",')
    assert (repo.path / "apps/api/package.json").read_bytes() == expected.encode()
    assert summary(discover(repo.path))[0][4] == "0.35.0"


def test_write_pyproject_changes_only_the_project_version(repo):
    original = (
        "# a comment\n"
        "[tool.other]\n"
        'version = "1.2.3"\n'
        "\n"
        "[project]\n"
        "name = 'tool'\n"
        "version = '1.2.3'  # the version\n"
        'description = "version = 1.2.3"\n'
        "\n"
        "[tool.more]\n"
        'version = "1.2.3"\n'
    )
    repo.write({"pyproject.toml": original})
    [u] = discover(repo.path)
    assert write_version(repo.path, u, "1.3.0") == ["pyproject.toml"]
    expected = original.replace("version = '1.2.3'", "version = '1.3.0'")
    assert (repo.path / "pyproject.toml").read_text() == expected


UV_LOCK = (
    "version = 1\n"
    "\n"
    "[[package]]\n"
    'name = "api"\n'
    'version = "1.4.0"\n'
    'source = { editable = "." }\n'
    "\n"
    "[[package]]\n"
    'name = "requests"\n'
    'version = "1.4.0"\n'
)

SYNC_TOML = (
    '[units."apps/api"]\n'
    "sync = [\n"
    """  { file = "pyproject.toml", pattern = '^version = "(.*)"' },\n"""
    """  { file = "uv.lock", pattern = 'name = "api"\\nversion = "(.*)"' },\n"""
    "]\n"
    '[units."apps/mobile"]\n'
    "sync = [\n"
    """  { file = "app.json", pattern = '"version": "(.*)"' },\n"""
    """  { file = ".env", pattern = '^EXPO_PUBLIC_APP_VERSION=(.*)$' },\n"""
    "]\n"
)


@pytest.mark.parametrize(
    "app_json",
    [
        '{\n  "expo": {\n    "name": "mobile",\n    "version": "0.34.0"\n  }\n}\n',
        '{\n  "name": "mobile",\n  "version": "0.34.0"\n}\n',
    ],
    ids=["nested", "top-level"],
)
def test_write_rewrites_sync_files(repo, app_json):
    repo.write(
        {
            "pnpm-workspace.yaml": "packages:\n  - apps/*\n",
            "apps/api/package.json": pkg("@scope/api", "1.4.0"),
            "apps/api/pyproject.toml": pyproject("api", "1.4.0"),
            "apps/api/uv.lock": UV_LOCK,
            "apps/mobile/package.json": pkg("@scope/mobile", "0.34.0"),
            "apps/mobile/app.json": app_json,
            "apps/mobile/.env": "API_URL=http://localhost\nEXPO_PUBLIC_APP_VERSION=0.34.0\nOTHER=0.34.0\n",
            "semrail.toml": SYNC_TOML,
        }
    )
    units = discover(repo.path)
    assert write_version(repo.path, unit(units, "apps/api"), "1.5.0") == [
        "apps/api/package.json",
        "apps/api/pyproject.toml",
        "apps/api/uv.lock",
    ]
    assert write_version(repo.path, unit(units, "apps/mobile"), "0.35.0") == [
        "apps/mobile/package.json",
        "apps/mobile/app.json",
        "apps/mobile/.env",
    ]
    read = lambda name: (repo.path / name).read_text()  # noqa: E731
    assert read("apps/api/pyproject.toml") == pyproject("api", "1.5.0")
    assert read("apps/api/uv.lock") == UV_LOCK.replace('"api"\nversion = "1.4.0"', '"api"\nversion = "1.5.0"')
    assert read("apps/mobile/app.json") == app_json.replace("0.34.0", "0.35.0")
    assert read("apps/mobile/.env") == "API_URL=http://localhost\nEXPO_PUBLIC_APP_VERSION=0.35.0\nOTHER=0.34.0\n"
    assert [u.version for u in discover(repo.path)] == ["1.5.0", "0.35.0"]


def test_global_sync_is_resolved_in_each_unit_directory(repo):
    repo.write(
        {
            **MONOREPO,
            "apps/api/VERSION": "1.4.0\n",
            "apps/web/VERSION": "0.2.0\n",
            "semrail.toml": """sync = [{ file = "VERSION", pattern = '^(\\S+)$' }]\n""",
        }
    )
    units = discover(repo.path)
    assert write_version(repo.path, unit(units, "apps/web"), "0.3.0") == ["apps/web/package.json", "apps/web/VERSION"]
    assert (repo.path / "apps/web/VERSION").read_text() == "0.3.0\n"
    assert (repo.path / "apps/api/VERSION").read_text() == "1.4.0\n"


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ({}, "missing"),
        ({"apps/api/app.json": '{"name": "api"}\n'}, "matches nothing"),
        ({"apps/api/app.json": '{"version": "1.3.9"}\n'}, "1.3.9"),
        ({"apps/api/app.json": '{"version": "1.4.0",\n "x": {"version": "1.3.9"}}\n'}, "1.3.9"),
    ],
    ids=["missing-file", "no-match", "other-version", "one-match-differs"],
)
def test_sync_problems_are_errors_and_nothing_is_written(repo, files, message):
    repo.write(
        {
            **MONOREPO,
            "apps/api/VERSION": "1.4.0\n",
            **files,
            "semrail.toml": (
                '[units."apps/api"]\n'
                """sync = [{ file = "VERSION", pattern = '^(\\S+)$' },\n"""
                """        { file = "app.json", pattern = '"version": "([^"]*)"' }]\n"""
            ),
        }
    )
    before = snapshot(repo.path)
    u = unit(discover(repo.path), "apps/api")
    with pytest.raises(ConfigError, match=message):
        write_version(repo.path, u, "1.5.0")
    assert snapshot(repo.path) == before


@pytest.mark.parametrize("file", ["package.json", "./package.json"])
def test_sync_must_not_target_the_manifest(repo, file):
    # The manifest is always rewritten; a sync entry on it would see the new version and fail confusingly.
    repo.write(
        {
            **MONOREPO,
            "semrail.toml": f"""[units."apps/api"]\nsync = [{{ file = "{file}", pattern = '"version": "(.*)"' }}]\n""",
        }
    )
    with pytest.raises(ConfigError, match="sync must not target the manifest"):
        discover(repo.path)

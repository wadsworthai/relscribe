"""Subject parsing, bump rules and version arithmetic (docs/design.md, Versioning and Commit parsing).

These test the module directly because no command exposes bump rules yet; they move to
CLI level once `status` does.
"""

from __future__ import annotations

import pytest

from semrail.commits import DEFAULT_BUMPS, Commit, bump, next_version, parse


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("feat: x", Commit("feat", None, False, "x")),
        ("fix(parser): x", Commit("fix", "parser", False, "x")),
        ("feat(0037:api:session): x", Commit("feat", "0037:api:session", False, "x")),
        ("refactor(api)!: x", Commit("refactor", "api", True, "x")),
        ("feat!: x", Commit("feat", None, True, "x")),
        ("Feat: x", Commit("feat", None, False, "x")),
        ("fix: accept a trailing reference (#82)", Commit("fix", None, False, "accept a trailing reference (#82)")),
        ("feat(api): add a read (#T054)", Commit("feat", "api", False, "add a read (#T054)")),
    ],
)
def test_parses(subject, expected):
    assert parse(subject) == expected


@pytest.mark.parametrize(
    "subject",
    [
        "oops",
        "feat x",
        "feat:x",
        "feat: ",
        "feat(): x",
        "(api): x",
        "feat(a(b)): x",
        "Merge branch 'x'",
        'Revert "feat: x"',
        "feat: x\nmore",
    ],
)
def test_rejects(subject):
    assert parse(subject) is None


@pytest.mark.parametrize("footer", ["BREAKING CHANGE: drops x", "BREAKING-CHANGE: drops x"])
def test_breaking_footer(footer):
    assert parse("fix: x", f"Some text.\n\n{footer}").breaking


def test_lowercase_footer_is_not_breaking():
    assert not parse("fix: x", "breaking change: drops x").breaking


def test_footer_on_unparseable_subject_yields_nothing():
    assert parse("oops", "BREAKING CHANGE: drops x") is None


def _c(subject: str, body: str = "") -> Commit | None:
    return parse(subject, body)


@pytest.mark.parametrize(
    ("subjects", "version", "expected"),
    [
        (["feat!: x"], "1.2.3", "major"),
        (["feat!: x"], "0.4.0", "minor"),
        (["feat: x"], "1.2.3", "minor"),
        (["feat: x"], "0.4.0", "minor"),
        (["fix: x"], "1.2.3", "patch"),
        (["perf: x"], "1.2.3", "patch"),
        (["refactor: x"], "1.2.3", "patch"),
        (["docs: x"], "1.2.3", None),
        (["chore: x"], "1.2.3", None),
        (["whatever: x"], "1.2.3", None),
        (["docs: x", "fix: x", "feat: x", "chore: x"], "1.2.3", "minor"),
        (["fix: x", "docs!: x"], "1.2.3", "major"),
        ([], "1.2.3", None),
        (["oops", "fix: x"], "1.2.3", "patch"),
        (["oops"], "1.2.3", None),
    ],
)
def test_bump_defaults(subjects, version, expected):
    assert bump([_c(s) for s in subjects], version) == expected


def test_bump_footer_is_breaking():
    assert bump([_c("fix: x", "BREAKING CHANGE: y")], "1.0.0") == "major"


def test_bump_override_map_replaces_defaults():
    bumps = {"docs": "patch"}
    assert bump([_c("docs: x")], "1.2.3", bumps) == "patch"
    assert bump([_c("feat: x")], "1.2.3", bumps) is None
    assert DEFAULT_BUMPS["feat"] == "minor"


def test_bump_configured_major_is_minor_before_1_0_0():
    bumps = {"feat": "major"}
    assert bump([_c("feat: x")], "0.3.1", bumps) == "minor"
    assert bump([_c("feat: x")], "1.3.1", bumps) == "major"


@pytest.mark.parametrize(
    ("version", "level", "expected"),
    [
        ("1.2.3", "major", "2.0.0"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "patch", "1.2.4"),
        ("0.1.5", "minor", "0.2.0"),
    ],
)
def test_next_version(version, level, expected):
    assert next_version(version, level) == expected


@pytest.mark.parametrize("version", ["1.2", "1.2.3-rc.1", "v1.2.3", "01.2.3", ""])
def test_next_version_rejects_non_plain_versions(version):
    with pytest.raises(ValueError):
        next_version(version, "patch")

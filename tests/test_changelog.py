"""Keep a Changelog rendering and insertion (docs/design.md, Changelog)."""

from __future__ import annotations

from semrail import changelog
from semrail.commits import DEFAULT_BUMPS, LogEntry, parse

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

SECTION = "## [1.1.0] - 2026-09-18\n\n### Added\n\n- add x (aaaaaaa)\n"


def entries(*subjects: str, body: str = "") -> list:
    """Commits newest first, as `history.status` lists them: the first subject is the newest."""
    out = []
    for i, subject in enumerate(subjects):
        sha = "abcdefg"[i] * 40
        out.append((LogEntry(sha, subject, body), parse(subject, body)))
    return out


# Rendering (AC 2, 3)


def test_groups_in_keep_a_changelog_order():
    commits = entries(
        "fix: repair y",
        "refactor(core): tidy z",
        "feat(api): add x",
        "perf: speed up w",
    )
    assert changelog.section("1.1.0", "2026-09-18", commits, DEFAULT_BUMPS) == (
        "## [1.1.0] - 2026-09-18\n"
        "\n"
        "### Added\n"
        "\n"
        "- add x (ccccccc)\n"
        "\n"
        "### Changed\n"
        "\n"
        "- speed up w (ddddddd)\n"
        "- tidy z (bbbbbbb)\n"
        "\n"
        "### Fixed\n"
        "\n"
        "- repair y (aaaaaaa)\n"
    )


def test_breaking_changes_go_to_changed_with_a_prefix():
    footer = "BREAKING CHANGE: --x is now --y"
    newest = (LogEntry("f" * 40, "fix: rename a flag", footer), parse("fix: rename a flag", footer))
    commits = [newest] + entries("feat!: drop the v1 API")
    assert changelog.section("2.0.0", "2026-09-18", commits, DEFAULT_BUMPS) == (
        "## [2.0.0] - 2026-09-18\n"
        "\n"
        "### Changed\n"
        "\n"
        "- **BREAKING:** drop the v1 API (aaaaaaa)\n"
        "- **BREAKING:** rename a flag (fffffff)\n"
    )


def test_commits_that_do_not_bump_are_left_out():
    commits = entries("docs: explain x", "chore: bump deps", "wip", "fix: y", "test: cover z")
    assert changelog.section("1.0.1", "2026-09-18", commits, DEFAULT_BUMPS) == (
        "## [1.0.1] - 2026-09-18\n\n### Fixed\n\n- y (ddddddd)\n"
    )


def test_a_type_bumping_through_an_override_goes_to_changed():
    commits = entries("docs: explain x", "chore: bump deps")
    bumps = {**DEFAULT_BUMPS, "docs": "patch"}
    assert changelog.section("1.0.1", "2026-09-18", commits, bumps) == (
        "## [1.0.1] - 2026-09-18\n\n### Changed\n\n- explain x (aaaaaaa)\n"
    )


def test_bullet_is_the_description_without_type_and_scope():
    commits = entries("feat(0037:api:session): add a who-am-I read (#82)")
    assert "- add a who-am-I read (#82) (aaaaaaa)\n" in changelog.section("1.1.0", "2026-09-18", commits, DEFAULT_BUMPS)


def test_type_is_case_insensitive():
    commits = entries("Feat: add x", "FIX: y")
    out = changelog.section("1.1.0", "2026-09-18", commits, DEFAULT_BUMPS)
    assert "### Added\n\n- add x (aaaaaaa)\n" in out
    assert "### Fixed\n\n- y (bbbbbbb)\n" in out


# Insertion (AC 1, 4, 5, 6)


def test_missing_file_gets_the_standard_header():
    assert changelog.insert(None, SECTION) == HEADER + "\n" + SECTION


def test_empty_file_gets_the_standard_header():
    assert changelog.insert("", SECTION) == HEADER + "\n" + SECTION


def test_inserts_below_unreleased_and_keeps_existing_lines():
    old = HEADER + "\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- first (1234567)\n"
    new = changelog.insert(old, SECTION)
    assert new == HEADER + "\n" + SECTION + "\n## [1.0.0] - 2026-01-01\n\n### Added\n\n- first (1234567)\n"


def test_content_under_unreleased_stays_there():
    old = HEADER + "\n- a hand-written note\n\n## [1.0.0] - 2026-01-01\n"
    new = changelog.insert(old, SECTION)
    assert new == HEADER + "\n- a hand-written note\n\n" + SECTION + "\n## [1.0.0] - 2026-01-01\n"


def test_unreleased_directly_followed_by_a_release():
    old = "# Changelog\n\n## [Unreleased]\n## [1.0.0] - 2026-01-01\n"
    new = changelog.insert(old, SECTION)
    assert new == "# Changelog\n\n## [Unreleased]\n\n" + SECTION + "\n## [1.0.0] - 2026-01-01\n"


def test_unreleased_at_the_end_without_a_final_newline():
    old = "# Changelog\n\n## [Unreleased]"
    assert changelog.insert(old, SECTION) == "# Changelog\n\n## [Unreleased]\n\n" + SECTION


def test_unreleased_heading_variants():
    for heading in ("## [unreleased]", "## Unreleased", "##  [Unreleased]  "):
        old = f"# Changelog\n\n{heading}\n\n## [1.0.0] - 2026-01-01\n"
        new = changelog.insert(old, SECTION)
        assert new == f"# Changelog\n\n{heading}\n\n" + SECTION + "\n## [1.0.0] - 2026-01-01\n"


def test_file_without_header_or_unreleased():
    old = (
        "## 0.0.1 — 2026-09-08\n"
        "\n"
        "### Added\n"
        "\n"
        "- first thing (1234567)\n"
        "\n"
        "### Unknown\n"
        "\n"
        "- Initial import (89abcde)\n"
    )
    assert changelog.insert(old, SECTION) == HEADER + "\n" + SECTION + "\n" + old


def test_file_with_a_title_but_no_unreleased_keeps_its_title():
    old = "# Changes\n\nOur notes.\n\n## 0.0.1 — 2026-09-08\n\n- x\n"
    new = changelog.insert(old, SECTION)
    assert new == "# Changes\n\nOur notes.\n\n## [Unreleased]\n\n" + SECTION + "\n## 0.0.1 — 2026-09-08\n\n- x\n"


def test_file_with_only_a_title():
    assert changelog.insert("# Changelog\n", SECTION) == "# Changelog\n\n## [Unreleased]\n\n" + SECTION


def test_crlf_stays_crlf():
    old = HEADER.replace("\n", "\r\n") + "\r\n## [1.0.0] - 2026-01-01\r\n"
    new = changelog.insert(old, SECTION)
    assert new == (HEADER + "\n" + SECTION + "\n## [1.0.0] - 2026-01-01\n").replace("\n", "\r\n")
    assert "\n" not in new.replace("\r\n", "")


# Duplicate detection (AC 14)


def test_has_version():
    text = HEADER + "\n## [1.0.0] - 2026-01-01\n\n## 0.0.1 — 2026-09-08\n"
    assert changelog.has_version(text, "1.0.0")
    assert changelog.has_version(text, "0.0.1")
    assert not changelog.has_version(text, "1.0.1")
    assert not changelog.has_version(text, "0.0")
    assert not changelog.has_version("- mentions 1.0.1 in a bullet\n", "1.0.1")

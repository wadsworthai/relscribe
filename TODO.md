# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | semrail 0.1 | Ship a public CLI that computes per-unit SemVer versions and Keep a Changelog changelogs from Conventional Commits, as specified in docs/design.md | —    |

## E01 — semrail 0.1

Done when: semrail 0.1.0 is on PyPI, released and tagged by semrail itself

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T001 | chore   | 2   | —          | Scaffold the package, CLI skeleton and test fixtures | pyproject with uv_build, cli.py with --json/--root and exit codes, conftest building temp git repos, tests/test_docs.py (docs/development.md). |
| ✅ | T002 | feature | 3   | T001       | Parse Conventional Commit subjects and add lint | Subject parser, bump rules and semrail lint, per docs/design.md Versioning and Commit parsing. |
| ✅ | T003 | feature | 5   | T001       | Discover units and read and write their versions | Workspace discovery, semrail.toml, package.json/pyproject versions, sync and exclude, per docs/design.md Units. |
| ✅ | T004 | feature | 5   | T002, T003 | Select each unit's commits and add status | Base resolution, path attribution and semrail status, per docs/design.md Selecting a unit's commits. |
| ⬜ | T005 | feature | 5   | T004       | Write changelogs and add release | Keep a Changelog rendering and semrail release --commit/--branch, per docs/design.md Changelog and Releases. |
| ⬜ | T006 | feature | 3   | T004       | Tag merged releases            | semrail tag <from>..<to> [--push], release detection by version change, per docs/design.md Releases and tags. |
| ⬜ | T007 | chore   | 3   | T005, T006 | Publish to PyPI and release 0.1.0 with semrail itself | CI for tests and PR-title lint, trusted-publishing workflow, README usage and migration guide, first self-release. |

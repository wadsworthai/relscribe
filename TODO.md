# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | relscribe 0.1 | Ship a public CLI that computes per-unit SemVer versions and Keep a Changelog changelogs from Conventional Commits, as specified in docs/design.md | —    |
| E02 | Repository upkeep | Keep this repository's own automation and backlog trustworthy after 0.1 | —    |

## E01 — relscribe 0.1

Done when: relscribe 0.1.0 is released and tagged v0.1.0 by relscribe itself

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T001 | chore   | 2   | —          | Scaffold the package, CLI skeleton and test fixtures | pyproject with uv_build, cli.py with --json/--root and exit codes, conftest building temp git repos, tests/test_docs.py (docs/development.md). |
| ✅ | T002 | feature | 3   | T001       | Parse Conventional Commit subjects and add lint | Subject parser, bump rules and semrail lint, per docs/design.md Versioning and Commit parsing. |
| ✅ | T003 | feature | 5   | T001       | Discover units and read and write their versions | Workspace discovery, semrail.toml, package.json/pyproject versions, sync and exclude, per docs/design.md Units. |
| ✅ | T004 | feature | 5   | T002, T003 | Select each unit's commits and add status | Base resolution, path attribution and semrail status, per docs/design.md Selecting a unit's commits. |
| ✅ | T005 | feature | 5   | T004       | Write changelogs and add release | Keep a Changelog rendering and semrail release --commit/--branch, per docs/design.md Changelog and Releases. |
| ✅ | T006 | feature | 3   | T004       | Tag merged releases            | semrail tag <from>..<to> [--push], release detection by version change, per docs/design.md Releases and tags. |
| ✅ | T007 | chore   | 3   | T005, T006, T008, T009 | Add CI, release tagging and uvx-first usage docs        | Tests and PR-title lint in CI, a workflow that tags merged releases, relscribe.toml for this repo, README usage and migration guide recommending uvx from the git repo pinned per repo. |
| ✅ | T008 | chore   | 2   | —          | Rename the tool from semrail to relscribe | Package, CLI, config file (relscribe.toml), error prefix, docs, README and agent files; historical task records unchanged. |
| ✅ | T009 | feature | 2   | —          | Add a dry run to tag           | relscribe tag --dry-run <from>..<to>: report the releases and tags it would create, without creating or pushing any, per docs/design.md Releases and tags. |
| ✅ | T010 | chore   | 2   | T007       | Release 0.1.0 with relscribe itself | On an up-to-date main run uv run relscribe release --branch --commit, open the release PR, squash-merge, and confirm CI creates and pushes the v0.1.0 tag (docs/releasing.md).        |

## E02 — Repository upkeep

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ⬜ | T011 | chore   | 1   | —          | Run taskrail validate in CI    | Add a job to .github/workflows/ci.yml that runs .taskrail/bin/taskrail validate on every pull request and push to main, so a malformed backlog fails the build. |

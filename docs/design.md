# Design

This is the spec the code answers to. What is not built yet is listed in `TODO.md`.

## Scope

semrail does four things for every versioned unit in a repository:
- It computes the next version from Conventional Commits.
- It writes versions and changelogs in one release commit.
- It tags merged releases.
- It lints commit subjects.

Everything else stays in the consumer's CI: opening pull requests, promoting or deploying branches, choosing which tests to run, merging hotfixes back, and publishing packages.

## Units

A unit is a directory with its own version.
- **Discovery.** Units are discovered at run time from `pnpm-workspace.yaml`, the `workspaces` field of the root `package.json`, or `[tool.uv.workspace]` in the root `pyproject.toml`. Without a workspace, the repository root is the single unit.
- **Source of truth.** The version is read from the unit's `package.json` `version` or `pyproject.toml` `[project].version`. That is the only authoritative copy, and there is no repository-wide version.
- **Name.** `{name}` is the manifest's package name and `{dir}` is the unit directory's base name.

`semrail.toml` at the repository root is optional and only overrides defaults. It can be set globally or per unit (`[units."<path>"]`):

| Key | Default | Purpose |
|---|---|---|
| `tag` | `"{name}@{version}"` | Tag template |
| `changelog` | `true` | Whether to write `CHANGELOG.md`. Set it to `false` when another tool owns the changelog |
| `exclude` | `[]` | Globs of files that never cause a bump on their own, such as tests. Relative to the unit directory; `*` stays within a directory and `**/` spans directories |
| `sync` | `[]` | Other files that repeat the version, each `{ file, pattern }` with one capture group holding the version |
| `bump` | see Versioning | Map from commit type to `"major"`, `"minor"` or `"patch"` |

- A key in `[units."<path>"]` replaces the global value for that unit; nothing is merged. A unit table that names no unit, an unknown key or a wrong type is a configuration error.
- A workspace member without a static version is not a unit and is skipped.
- A `sync` `file` is relative to the unit directory and must not be the unit's manifest. The pattern is a Python regular expression applied with `re.MULTILINE`.
- Writing a version checks every `sync` entry first and writes nothing if one fails: a missing file, a pattern that matches nothing, or a match whose group is not the current version is a configuration error. Otherwise every match is replaced.

semrail never edits `.gitattributes` and never installs merge drivers.

## Versioning

- semrail follows [SemVer 2.0.0](https://semver.org/) and reads [Conventional Commits 1.0.0](https://www.conventionalcommits.org/). Versions use plain `X.Y.Z` spelling in every ecosystem.
- There are no pre-releases and no build metadata.

| Commit | ≥ 1.0.0 | 0.y.z |
|---|---|---|
| `!` before the colon, or a `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer | MAJOR | MINOR |
| `feat` | MINOR | MINOR |
| `fix`, `perf`, `refactor` | PATCH | PATCH |
| any other type | none | none |

The highest bump among a unit's commits wins. The `bump` key's entries add types to this table or replace a type's level; the other defaults still apply. A type that the `bump` key maps to `"major"` still gives MINOR while 0.y.z.

## Commit parsing

- The subject has the form `type(scope)!: description`. The scope is free text without parentheses and may contain `:`, as in `feat(0037:api:session): …`.
- The type is case-insensitive, as Conventional Commits requires: `Feat:` is `feat`.
- A trailing reference such as `(#82)` or `(#T054)` stays part of the description.
- A body line starting with `BREAKING CHANGE: ` or `BREAKING-CHANGE: ` marks the commit breaking, wherever it is in the body. The token is upper-case only.
- A subject that does not parse contributes nothing. It is reported as a warning, and `semrail lint` fails on it.
- `semrail lint --range` skips merge commits, like the selection of a unit's commits.

## Selecting a unit's commits

The commits for a unit are `git log <base>..HEAD --no-merges -- <unit path>`, minus any commit whose files in the unit all match `exclude`. The base is:
1. the tag of the unit's current version, if it exists;
2. otherwise, the last commit that changed the unit's version;
3. otherwise, the unit's whole history.

- A commit changes the version when the manifest's version differs from the one in its parent. Introducing a version is not a change, so a unit never released counts its whole history.
- `exclude` globs are git `glob` pathspecs, so git itself drops a commit whose files in the unit all match.
- Files of a unit nested inside another unit's directory count only for the nested unit.
- A commit that only touches files outside every unit bumps nothing.
- Unparseable subjects are warnings. So is a shallow clone when a unit's base is not a tag, since the base may be missing from the fetched history.

## Changelog

- One `CHANGELOG.md` per unit, in [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) format.
- If the file is missing, semrail creates it with the standard header and an empty `## [Unreleased]` section.
- A release inserts `## [X.Y.Z] - YYYY-MM-DD` below `## [Unreleased]`. Existing sections are never rewritten.
- Groups, in Keep a Changelog order:
  - Added: `feat`.
  - Changed: `perf`, `refactor`, and breaking changes, which are prefixed `**BREAKING:**`.
  - Fixed: `fix`.
- Each bullet is the subject's description without type and scope, followed by the short SHA in parentheses as plain text: `- add a who-am-I read (#82) (241aae1)`.

## Releases and tags

- **Bump timing.** Versions change only in a release commit, never on task branches.
- **Release commit.** `semrail release --commit` writes one commit whose subject is `chore(release): <name> <old> -> <new>, …`.
- **Release detection.** A commit is a release for a unit when it changes that unit's version. The commit message and any manifest file are never consulted.
- **Tags.** Tags are annotated and follow the unit's `tag` template. A published tag never moves. If a tag already exists on the same commit, creating it is a no-op. If it exists on another commit, it is a conflict that a human resolves.

## CLI

Every command accepts `--json` and `--root <path>`. Without `--root`, the root is the enclosing git repository.

| Command | Does |
|---|---|
| `semrail status` | Reports per unit: current version, base, the commits that count, the next version, and warnings |
| `semrail release [--commit] [--branch]` | Writes the next versions, `sync` files and changelogs. `--commit` makes the release commit. `--branch` first creates `release/<YYYY-MM-DD>[-N]`. It never pushes and never tags |
| `semrail tag <from>..<to> [--push <remote>]` | Tags every release commit in the range, plus the most recent untagged release before it |
| `semrail lint [<subject>…] [--range <from>..<to>]` | Checks that subjects are Conventional Commits, for example on pull request titles in CI |

- Exit codes: 0 success; 1 lint or validation failed; 2 usage, configuration or git error; 4 tag conflict.
- Errors go to stderr prefixed with `semrail: `.

`semrail status --json` prints `{"units": [...]}`, one object per unit in path order, which CI can read, for example to find the units a release touches (`next` is not `null`):
- `path`, `name`, `version`: the unit and its current version.
- `base`: `{"kind", "sha", "tag"}`. `kind` is `"tag"`, `"version-change"` or `"history"`. `sha` is `null` only for `"history"`, and `tag` is set only for `"tag"`.
- `commits`: every commit selected, newest first, each `{"sha", "subject", "type", "scope", "breaking"}`. `type` and `scope` are `null` when the subject does not parse.
- `bump`: `"major"`, `"minor"`, `"patch"` or `null`. `next`: the next version, or `null` when nothing bumps.
- `warnings`: a list of strings. Warnings never change the exit code.

## Architecture

```
src/semrail/
  cli.py        # argparse; each subcommand is a thin cmd_*(args) -> int
  commits.py    # subject parsing and bump rules
  history.py    # each unit's base, commits, bump and next version
  units.py      # discovery, config, reading and writing versions
  changelog.py  # Keep a Changelog rendering and insertion
  gitutil.py    # the only module that shells out to git
tests/          # pytest; conftest.py builds real git repos in tmp_path
```

Configuration is read with `tomllib`. `pnpm-workspace.yaml` is read with a minimal parser for its `packages` list, which keeps semrail free of runtime dependencies.

## Distribution

semrail is published to PyPI and tagged `vX.Y.Z` in git. Consumers run a pinned version with `uvx semrail@X.Y.Z …`, so their CI needs only uv. semrail versions itself: it is a single-unit repository with `tag = "v{version}"`.

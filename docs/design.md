# Design

This is the spec the code answers to. What is not built yet is listed in `TODO.md`.

## Scope

relscribe does four things for every versioned unit in a repository:
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

`relscribe.toml` at the repository root is optional and only overrides defaults. It can be set globally or per unit (`[units."<path>"]`):

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

relscribe never edits `.gitattributes` and never installs merge drivers.

## Versioning

- relscribe follows [SemVer 2.0.0](https://semver.org/) and reads [Conventional Commits 1.0.0](https://www.conventionalcommits.org/). Versions use plain `X.Y.Z` spelling in every ecosystem.
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
- A subject that does not parse contributes nothing. It is reported as a warning, and `relscribe lint` fails on it.
- `relscribe lint --range` skips merge commits, like the selection of a unit's commits.

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
- If the file is missing, relscribe creates it with the standard header and an empty `## [Unreleased]` section.
- A release inserts `## [X.Y.Z] - YYYY-MM-DD` below `## [Unreleased]`, before the next `##` heading, so anything under Unreleased stays there. Existing lines are never rewritten, and a CRLF file stays CRLF.
- A file without an Unreleased heading gets `## [Unreleased]` and the new section before its first `##` heading, with the standard header on top when nothing precedes that heading. Older sections keep their own heading style.
- The date is today in UTC.
- Only commits that bump appear. Groups, in Keep a Changelog order, empty ones left out:
  - Added: `feat`.
  - Changed: `perf`, `refactor`, any type that bumps only through the `bump` key, and breaking changes, which are prefixed `**BREAKING:**`.
  - Fixed: `fix`.
- Each bullet is the subject's description without type and scope, followed by the short SHA in parentheses as plain text: `- add a who-am-I read (#82) (241aae1)`. Within a group, the oldest commit comes first.

## Releases and tags

- **Bump timing.** Versions change only in a release commit, never on task branches. `relscribe release` refuses to run while tracked files have uncommitted changes, and it writes all of its files or none.
- **Release commit.** `relscribe release --commit` writes one commit whose subject is `chore(release): <name> <old> -> <new>, …`, one entry per released unit in path order. It stages only the files the release wrote.
- **Release detection.** A commit is a release for a unit when it raises that unit's version over its parent's. Introducing a version and lowering one (a reverted release) are not releases. Merge commits are never examined; the merged commit that raised the version is. The commit message and any manifest file are never consulted.
- **Units as of the release.** Units, names and `tag` templates are read as of the release commit, not from the working tree, so a unit renamed, reconfigured or removed later still gets the tag its release implies.
- **Reconcile.** Besides the range, `relscribe tag` looks at each unit's newest release reachable from `<from>` and creates its tag if it is missing, which covers a skipped CI run and a unit released before it had tags. Older untagged releases stay untagged.
- **Tags.** Tags are annotated, with the message `<name> <version>`, and follow the unit's `tag` template. git needs a committer identity to create them. A published tag never moves. If a tag already exists on the same commit, creating it is a no-op. If it exists on another commit, it is a conflict that a human resolves; the other tags are still created, and the exit code is 4.
- **Push.** `--push <remote>` pushes only the tags the run created, in one push. A tag the remote already has on another commit is rejected, which is a conflict (exit 4); any other push failure is a git error (exit 2). CI needs a checkout with full history and tags.
- **Dry run.** `--dry-run` creates and pushes nothing and needs no committer identity. It reports each tag the run would create as `would-create`, and everything else, the exit code included, as the real run would. CI uses it as a query: `<sha>^..<sha>` tells whether a commit is a release and of which units, for example before promoting it; `<mainline>..<release-branch>` tells which units a release branch releases, for example to test only those. Reconciled entries are marked, so a query can drop them. `--dry-run` with `--push` is a usage error.

## CLI

Every command accepts `--json` and `--root <path>`. Without `--root`, the root is the enclosing git repository.

| Command | Does |
|---|---|
| `relscribe status` | Reports per unit: current version, base, the commits that count, the next version, and warnings |
| `relscribe release [--commit] [--branch]` | Writes the next versions, `sync` files and changelogs of every unit with a next version, or reports that there is nothing to release. `--commit` makes the release commit. `--branch` first creates `release/<YYYY-MM-DD>[-N]` (UTC date; `-N` from 2 when a local or remote-tracking branch has the name). It never pushes and never tags |
| `relscribe tag <from>..<to> [--push <remote> \| --dry-run]` | Tags every release commit in the range, plus each unit's latest release before it when that one is untagged. CI runs it on each push to the release branch with the push's before and after commits. `--dry-run` only reports what it would tag |
| `relscribe lint [<subject>…] [--range <from>..<to>]` | Checks that subjects are Conventional Commits, for example on pull request titles in CI |

- Exit codes: 0 success; 1 lint or validation failed; 2 usage, configuration or git error; 4 tag conflict.
- Errors go to stderr prefixed with `relscribe: `.

`relscribe status --json` prints `{"units": [...]}`, one object per unit in path order, which CI can read, for example to find the units a release touches (`next` is not `null`):
- `path`, `name`, `version`: the unit and its current version.
- `base`: `{"kind", "sha", "tag"}`. `kind` is `"tag"`, `"version-change"` or `"history"`. `sha` is `null` only for `"history"`, and `tag` is set only for `"tag"`.
- `commits`: every commit selected, newest first, each `{"sha", "subject", "type", "scope", "breaking"}`. `type` and `scope` are `null` when the subject does not parse.
- `bump`: `"major"`, `"minor"`, `"patch"` or `null`. `next`: the next version, or `null` when nothing bumps.
- `warnings`: a list of strings. Warnings never change the exit code.

`relscribe release --json` prints `{"units": [...], "files": [...], "branch", "commit"}`:
- `units`: the released units in path order, each `{"path", "name", "version", "next", "bump", "warnings"}`, where `version` is the version before the release.
- `files`: every file written, relative to the root.
- `branch`: the release branch, or `null` without `--branch`. `commit`: the release commit's SHA, or `null` without `--commit`.
- With nothing to release, `units` and `files` are empty and the exit code is 0.

`relscribe tag --json` prints `{"tags": [...], "push": ..., "warnings": [...]}`:
- `tags`: one object per release, reconciled ones first, then the range oldest first and by unit path within a commit: `tag`, `path`, `name`, `version`, `sha` (the release commit), `result` (`"created"`, `"would-create"` under `--dry-run`, `"existing"` or `"conflict"`), `existing_sha` (the commit the tag already points to, for `"conflict"` only) and `reconciled` (`true` for a release found by reconcile, before the range). The text output appends ` (reconciled)` to those.
- `push`: `{"remote", "pushed", "rejected"}`, lists of tag names, or `null` without `--push` (always under `--dry-run`).
- `warnings`: the shallow-clone warning, as in `status`.

## Architecture

```
src/relscribe/
  cli.py        # argparse; each subcommand is a thin cmd_*(args) -> int
  commits.py    # subject parsing and bump rules
  history.py    # each unit's base, commits, bump and next version
  units.py      # discovery, config, reading and writing versions
  changelog.py  # Keep a Changelog rendering and insertion
  tags.py       # release detection, units as of a commit, tagging and pushing tags
  gitutil.py    # the only module that shells out to git
tests/          # pytest; conftest.py builds real git repos in tmp_path
```

Configuration is read with `tomllib`. `pnpm-workspace.yaml` is read with a minimal parser for its `packages` list, which keeps relscribe free of runtime dependencies.

## Distribution

relscribe is published to PyPI and tagged `vX.Y.Z` in git. Consumers run a pinned version with `uvx relscribe@X.Y.Z …`, so their CI needs only uv. relscribe versions itself: it is a single-unit repository with `tag = "v{version}"`.

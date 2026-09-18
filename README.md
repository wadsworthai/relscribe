# relscribe

Semantic versioning and changelogs for repositories developed with agents.

relscribe reads the [Conventional Commits](https://www.conventionalcommits.org/) history of a repository's mainline and computes the next [Semantic Versioning](https://semver.org/) version for each package it manages. It then updates the changelog. It works with a single package or with several packages in one repository.

> **Status:** early development (0.y.z). Commands and configuration may change.

## How versions are computed

| Commit | Bump |
|---|---|
| `fix: …`, `perf: …`, `refactor: …` | PATCH |
| `feat: …` | MINOR |
| `feat!: …`, or any type with a `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer | MAJOR |
| any other type (`docs`, `chore`, `test`, …) | none |

Before 1.0.0, a breaking change bumps MINOR instead of MAJOR.

## Requirements

- [uv](https://docs.astral.sh/uv/), which provides Python ≥ 3.11 when needed
- git

## Running relscribe

relscribe is not published to any registry. A release is a `vX.Y.Z` tag in this git repository. The recommended way to run it is `uvx`, with the tag pinned in each repository:

```sh
uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe <command>
```

Nothing is installed on the machine: uv builds the tagged version once and caches it. The tag is written wherever the repository calls relscribe, such as its CI workflows, scripts or `package.json`. So every developer, agent and CI job runs the same version, and upgrading is a reviewed change. In this README, `vX.Y.Z` stands for the tag you pin, and every example uses this form.

For a private fork, or in CI that authenticates with SSH, use `git+ssh://git@github.com/wadsworthai/relscribe@vX.Y.Z` as the URL. CI needs read access to the repository either way.

In a Python project managed with uv, you can instead add relscribe as a development dependency. `uv.lock` then pins the commit.

```sh
uv add --dev "relscribe @ git+https://github.com/wadsworthai/relscribe@vX.Y.Z"
uv run relscribe <command>
```

### Installing globally (not recommended)

```sh
uv tool install git+https://github.com/wadsworthai/relscribe@vX.Y.Z
```

This works, but the version then depends on the machine rather than the repository, so different people and CI may run different versions. Prefer the pinned `uvx` form above.

## Usage

Every command supports:

| Flag | Description |
|---|---|
| `--json` | Machine-readable output. [docs/design.md](docs/design.md#cli) describes each command's JSON |
| `--root <path>` | Repository to operate on (default: the enclosing git repository) |

### `lint`

Checks that subjects are Conventional Commits. You can give subjects directly, for example a pull request title, or check the commits in a range. Merge commits are skipped.

```sh
uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe lint "feat(api): add sessions"
uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe lint --range origin/main..HEAD
```

### `status`

Reports, for each unit, the current version, the base the commits are counted from, the commits that count, the next version and any warnings. It changes nothing.

```sh
uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe status
```

### `release`

Writes the next version, the `sync` files and the changelog of every unit that has a next version. Otherwise it reports that there is nothing to release. It refuses to run while tracked files have uncommitted changes. It never pushes and never tags.

| Flag | Description |
|---|---|
| `--commit` | Make one release commit, `chore(release): <name> <old> -> <new>, …` |
| `--branch` | First create and switch to `release/<YYYY-MM-DD>[-N]` (UTC date) |

```sh
uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe release --branch --commit
```

Push the branch and open a pull request titled like the release commit. Once it is merged, `tag` tags it.

### `tag`

Tags every release commit in `<from>..<to>`: a commit is a release when it raises a unit's version. It also tags each unit's latest earlier release if that one is untagged ("reconcile"), which covers a skipped CI run. Tags are annotated, and a published tag never moves. Creating tags needs a committer identity.

| Flag | Description |
|---|---|
| `--push <remote>` | Push the tags this run created, in one push |
| `--dry-run` | Create and push nothing; report each tag it would create as `would-create` |

```sh
uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe tag "$BEFORE..$AFTER" --push origin
uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe tag --dry-run "$SHA^..$SHA"
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Lint or validation failed |
| 2 | Usage, configuration or git error |
| 4 | Tag conflict: a tag already exists on another commit |

## Configuration

A unit is a directory with its own version. Units come from `pnpm-workspace.yaml`, the `workspaces` field of the root `package.json`, or `[tool.uv.workspace]` in the root `pyproject.toml`. Without a workspace, the repository root is the single unit. The version is read from `package.json` `version` or `pyproject.toml` `[project].version`.

`relscribe.toml` at the repository root is optional and only overrides defaults. Its keys can be set globally or per unit:

| Key | Default | Purpose |
|---|---|---|
| `tag` | `"{name}@{version}"` | Tag template. Placeholders: `{name}` (package name), `{dir}` (directory base name), `{version}` |
| `changelog` | `true` | Whether to write the unit's `CHANGELOG.md` |
| `exclude` | `[]` | Globs of files, relative to the unit, that never cause a bump on their own |
| `sync` | `[]` | Other files that repeat the version, each `{ file, pattern }`, where the pattern's one capture group holds the version |
| `bump` | see above | Map from commit type to `"major"`, `"minor"` or `"patch"`. Adds types or changes a type's level; other defaults still apply |

```toml
tag = "v{version}"

[units."packages/api"]
tag = "api-v{version}"
exclude = ["tests/**"]
sync = [{ file = "src/version.ts", pattern = 'VERSION = "([^"]+)"' }]
```

A key in `[units."<path>"]` replaces the global value for that unit. Nothing is merged. [docs/design.md](docs/design.md) is the full specification.

## CI

These GitHub Actions recipes run a pinned relscribe tag with [`astral-sh/setup-uv`](https://github.com/astral-sh/setup-uv). CI needs nothing else, apart from read access to this repository.

Check pull request titles. With squash merges, the title becomes the commit on the mainline. Pass the title through the environment, never inline in the script:

```yaml
on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
jobs:
  title:
    runs-on: ubuntu-latest
    steps:
      - uses: astral-sh/setup-uv@v10.1.0
      - env:
          TITLE: ${{ github.event.pull_request.title }}
        run: uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe lint "$TITLE"
```

Tag each release merged to the release branch. The job needs full history and tags, a committer identity and `contents: write`:

```yaml
on:
  push:
    branches: [main]
concurrency:
  group: release
jobs:
  tag:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7.0.1
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v10.1.0
      - env:
          BEFORE: ${{ github.event.before }}
          AFTER: ${{ github.sha }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe tag "$BEFORE..$AFTER" --push origin --json > tags.json
```

Tags pushed with the default `GITHUB_TOKEN` do not trigger other workflows. So if a created tag should start a build, publish or deploy, do it in later steps or jobs of this workflow, reading the tags with `"result": "created"` from `tags.json`.

Use `--dry-run` as a query. It changes nothing, and entries with `"reconciled": true` come from before the range, so a query can drop them:
- `tag --dry-run "$SHA^..$SHA" --json` tells whether a commit is a release, and of which units. For example, run it before promoting that commit.
- `tag --dry-run "main..release/2026-01-31" --json` tells which units a release branch releases, for example to test only those.

In a JavaScript repository, pin the version in `package.json` scripts:

```json
{
  "scripts": {
    "release": "uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe release --branch --commit",
    "release:status": "uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe status"
  }
}
```

## Migrating an existing repository

Start with `uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe status`. It changes nothing and shows, for each unit, the base, the commits that count and any warnings.

- **Existing tags.** Set `tag`, globally or per unit, to the format the repository already uses, such as `"v{version}"` or `"{dir}-v{version}"`. The tag of a unit's current version then becomes its base.
- **Existing changelogs.** They are kept. A release inserts its section below `## [Unreleased]`, or before the first `##` heading when there is none. Existing lines are never rewritten.
- **Versions repeated in other files.** List each file under `sync`, for example a lock file or a version constant. A release updates them together, and fails without writing anything if one no longer matches.
- **Test-only commits.** Add their paths to `exclude` so they do not bump the unit on their own.
- **Units released before any tag.** Without a tag, the base is the last commit that changed the unit's version. The first `tag` run reconciles: it creates the missing tag of each unit's latest release. Older untagged releases stay untagged.
- **Non-conventional history.** Subjects that do not parse bump nothing and show up as warnings in `status`. They never fail it. Check the warnings before the first release.
- **Another changelog tool.** Set `changelog = false` to keep that tool's changelog and let relscribe handle only versions and tags.

### Tag conflicts

If the tag for a unit's latest release already exists on another commit, relscribe never moves it and exits 4. Reconcile checks that release on every run, so every `tag` run keeps exiting 4 until a human resolves the conflict. The other tags are still created. To resolve it, either delete or fix the wrong tag (only if nobody relies on it yet), or make a new release of the unit.

## Development

```sh
uv run pytest                               # all tests
uv run pytest tests/test_x.py -k some_case  # a single test
uv run relscribe --root <repo> <command>    # run against another repository
```

See [docs/design.md](docs/design.md) for the full model and [docs/development.md](docs/development.md) for contributor conventions.

## Releasing

See [docs/releasing.md](docs/releasing.md).

## License

[MIT](LICENSE)

# semrail

Semantic versioning and changelogs for repositories developed with agents.

semrail reads the [Conventional Commits](https://www.conventionalcommits.org/) history of a repository's mainline and computes the next [Semantic Versioning](https://semver.org/) version for each package it manages. It then updates the changelog. It works with a single package or with several packages in one repository.

> **Status:** early development. Nothing is released yet, and commands and configuration may change.

## How versions are computed

| Commit | Bump |
|---|---|
| `fix: …` | PATCH |
| `feat: …` | MINOR |
| `feat!: …`, or any type with a `BREAKING CHANGE:` footer | MAJOR |
| any other type (`docs`, `chore`, `refactor`, …) | none |

<!-- TODO: document the rule for versions before 1.0.0 once DESIGN.md defines it. -->

## Requirements

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/)
- git

## Installation

```sh
uv tool install semrail --from "git+<repo-url>@vX.Y.Z"
```

<!-- TODO: document repository setup (`semrail init`) once it exists. -->

## Usage

<!-- TODO: one subsection per command, with a short description, its flags and an example. Keep this in sync with the CLI. -->

Every command supports:

| Flag | Description |
|---|---|
| `--json` | Machine-readable output |
| `--root <path>` | Repository to operate on (default: discovered upward from the current directory) |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Validation failed |
| 2 | Usage, configuration or git error |

## Configuration

<!-- TODO: document `.semrail/config.toml` keys, including how paths map to packages in a monorepo. -->

## Development

```sh
uv run pytest                               # all tests
uv run pytest tests/test_x.py -k some_case  # a single test
uv run semrail --root <repo> <command>      # run against another repository
```

See [DESIGN.md](DESIGN.md) for the full model and [CLAUDE.md](CLAUDE.md) for contributor conventions.

## Releasing

1. In a PR: set the version in `pyproject.toml`, run `uv lock`, and rename `## Unreleased` to `## X.Y.Z` in `CHANGELOG.md`.
2. After the squash merge: `git tag -a vX.Y.Z <merge commit> -m "semrail X.Y.Z"` and push the tag. Published tags never move.
3. Verify a clean install from the tag, then bump `main` to the next `.dev0`.

## License

<!-- TODO: choose a license. -->

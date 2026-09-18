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

<!-- TODO: document the rule for versions before 1.0.0 once docs/design.md defines it. -->

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

See [docs/design.md](docs/design.md) for the full model and [docs/development.md](docs/development.md) for contributor conventions.

## Releasing

See [docs/releasing.md](docs/releasing.md).

## License

<!-- TODO: choose a license. -->

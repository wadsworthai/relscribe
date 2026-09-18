# relscribe

Semantic versioning and changelogs for repositories developed with agents.

relscribe reads the [Conventional Commits](https://www.conventionalcommits.org/) history of a repository's mainline and computes the next [Semantic Versioning](https://semver.org/) version for each package it manages. It then updates the changelog. It works with a single package or with several packages in one repository.

> **Status:** early development. Nothing is released yet, and commands and configuration may change.

## How versions are computed

| Commit | Bump |
|---|---|
| `fix: …`, `perf: …`, `refactor: …` | PATCH |
| `feat: …` | MINOR |
| `feat!: …`, or any type with a `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer | MAJOR |
| any other type (`docs`, `chore`, `test`, …) | none |

Before 1.0.0, a breaking change bumps MINOR instead of MAJOR.

## Requirements

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/)
- git

## Installation

```sh
uvx relscribe@X.Y.Z <command>      # run a pinned version, e.g. in CI
uv tool install relscribe          # or install it
```

<!-- TODO: document repository setup (`relscribe init`) once it exists. -->

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
| 4 | Tag conflict |

## Configuration

<!-- TODO: document the keys of the optional `relscribe.toml` at the repository root, including how paths map to packages in a monorepo. -->

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

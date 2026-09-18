# Development

## Dependencies and tooling

- No runtime dependencies: stdlib only, so the CLI runs anywhere through `uvx`.
- Build backend: `uv_build`. The single console script is declared in `[project.scripts]`.
- No linter or formatter is configured, and the test suite is the quality gate. Adding one is a deliberate decision.
- CI runs the tests with `uv run --locked pytest` on Python 3.11 and 3.14, and lints PR titles (`docs/releasing.md`).
- 2026-09-18: CI and release tagging use GitHub Actions, with `actions/checkout` and `astral-sh/setup-uv` pinned to exact release tags. Nothing is published to a registry.

## Code style

- Put `from __future__ import annotations` in every module, and type hints on public functions.
- Prefix private helpers with `_`.
- Give each module a short docstring stating its job.
- Comments explain why and cite `docs/design.md` sections where relevant.

## Tests

- Run the CLI end-to-end against temporary git repos, and assert on exit codes and `--json` output, not on internals.
- Use one test file per feature, named after it.
- A bug fix comes with a regression test that was seen failing first.
- `tests/test_docs.py` checks two things: that CLAUDE.md and AGENTS.md differ only in their header (the first 3 lines), and that every top-level `docs/*.md` appears in the Documentation map. Subdirectories of `docs/` hold task records, not product docs, and are not checked.

## Public repository

Consumers may be private. Never commit internal hostnames, private URLs or paths, client or employer names, ticket IDs from real projects, or real sample data. Generalize a need that comes from a consumer before committing it.

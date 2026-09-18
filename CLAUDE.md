# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

semrail manages semantic versions and changelogs in repositories developed with agents. It is meant to handle one or more apps, packages or tools inside a single repository, so it must work in monorepos. It infers version bumps from the history of the mainline branch.

The repository is at bootstrap stage and has no code yet. Most of this file describes the planned design and conventions. When code lands, replace the design sections with how the code actually works. Everything below that says "planned" has not been built yet.

The versioning strategy is [Semantic Versioning](https://semver.org/). The input format is [Conventional Commits](https://www.conventionalcommits.org/). Follow both specs as written, and document any deviation in DESIGN.md.
- `fix:` → PATCH, `feat:` → MINOR, and `!` or a `BREAKING CHANGE:` footer → MAJOR. Other types, such as `docs:` or `chore:`, do not bump the version on their own.
- Before 1.0.0, what counts as breaking follows the SemVer rules for 0.y.z. Settle that decision in DESIGN.md and apply it the same way everywhere.

semrail is standalone. Do not reference, depend on, or name any sibling tool in code, docs, tests, or commits. When semrail has to interoperate with the outside world, describe the other side generically, for example "a tool that installs a merge driver for `CHANGELOG.md`".

## Design principles

These principles decide what gets built. They take precedence over the "planned" sections below, which list options, not commitments.

- **KISS:** pick the simplest solution that works. Choose plain functions and data over classes, frameworks or plugin systems.
- **YAGNI:** build only what a current, concrete need requires. Do not add flags, config keys, commands or extension points "for later". Treat each planned item below as something to build only once a real need shows up.
- **Rule of three:** duplication is fine until a third occurrence. Extract a helper or abstraction only then, not after the first or second.
- **Occam's razor:** when two designs or explanations compete, choose the one with fewer assumptions and moving parts. Apply this when debugging too.
- **Premature optimization is the root of all evil:** write for clarity first. Optimize only after a measured problem, and keep the measurement in the PR.

When a principle leads to leaving something out, say so briefly in the PR rather than adding it anyway.

## Language

- Everything committed is in English: code, identifiers, comments, docs, skill text, commit messages, PR titles and bodies, and file names.
- In conversation, reply in the language the user writes in, whether Spanish or English. This does not change the language of anything committed.

## Commands (planned stack: Python ≥3.11 + uv)

```sh
uv run pytest                                   # all tests
uv run pytest tests/test_x.py -k some_case      # a single test
uv run semrail --root <repo> <command>          # run the CLI against another repo
```

- No runtime dependencies: stdlib only, with `tomllib` for config. The CLI must run anywhere through `uvx` without resolving a dependency tree.
- Build backend: `uv_build`. The only console script is declared under `[project.scripts]`.
- No linter or formatter is configured, and the test suite is the quality gate. Adding one is a deliberate decision, not something to assume.

## Planned architecture

```
src/semrail/
  cli.py        # argparse: subcommands, flag parsing, output, exit codes
  config.py     # find_root (upward search for .semrail/config.toml) + load_config
  model.py      # domain dataclasses/enums, each with to_dict() for --json output
  gitutil.py    # the ONLY module that shells out to git
  install.py    # init/upgrade: config, wrapper, skills, install manifest
  <domain>.py   # one small module per concern
  skills/       # agent-agnostic SKILL.md files shipped as package data
tests/          # pytest; conftest.py builds real git repos in tmp_path
DESIGN.md       # the spec the code answers to
CHANGELOG.md
README.md
```

Rules that span modules:
- `cli.py` stays thin. Each subcommand is a `cmd_*(args) -> int` that loads state, calls a domain module and emits the result. The logic lives in the domain modules, which can be imported and tested without the CLI.
- The main agent-facing contract is that every command accepts `--json` and prints through a single `_emit(data, as_json, text)` helper. Every command also accepts `--root <path>`.
- Exit codes are named constants at the top of `cli.py` and are documented in DESIGN.md and the README. At minimum: 0 success, 1 validation failed, 2 usage/config/git error. Agents branch on these codes, so treat them as stable.
- Errors go to stderr, prefixed with `semrail: `, and name the next command to run where possible. Validation collects every problem, each with its file and line, before exiting.
- State lives in a committed `.semrail/` directory: `config.toml` (hand-editable, with commented defaults written by `init`), a POSIX-sh wrapper `.semrail/bin/semrail` that runs the version pinned in the config, and `installed.json` (sha256 per installed file, so files the user edited are never silently overwritten; `--force` replaces them). Anything derivable from git, such as tags or commits, is read at runtime and never cached in the repo. Machine-local state never goes into `.semrail/`.
- Agents invoke semrail through the committed wrapper, as `.semrail/bin/semrail <cmd> --json`. Skills tell the agent which command to run at each step. They never reimplement the logic.

## Design constraints for version inference

- The input is squash-merged PR titles on the mainline in Conventional Commits form. The subject parser must accept an optional `!` before the colon and a trailing ` (ID)` such as a task or issue reference, for example `feat(cli): add x (T006)`.
- A scope often names an area rather than a package, so the scope alone cannot select a package in a monorepo. Map paths to packages explicitly in config.
- Other tools may already claim `CHANGELOG.md` in `.gitattributes` with a merge driver. Decide explicitly, and record the decision in DESIGN.md, whether semrail claims those paths, detects an existing driver, or stays out of merge resolution.

## Distribution

Nothing is published to PyPI; the git tag is the release artifact. Users install with `uv tool install semrail --from "git+<repo-url>@vX.Y.Z"` and then run `semrail init --integration claude` (`init` is idempotent). Skills are installed into `.claude/skills/semrail*/`. Agents must be restarted after `init` or `upgrade`, because skills load at session start.

## Workflow and releases

- Work on a branch and reach `main` through a PR. Every PR is squash-merged.
- The PR title becomes the single commit on `main`. Write it in Conventional Commits form with the affected area as scope, for example `feat(cli): add a bump command`. The type reflects the most significant change. Mark breaking changes with `!` and give them their own changelog entry. Trailers go at the end of the PR description so they survive the squash.
- The version is written only in `pyproject.toml` and must equal the tag without the `v`. Releasing takes three steps:
  1. In a PR, set the version, run `uv lock`, and rename `## Unreleased` to `## X.Y.Z` in the changelog.
  2. After the merge, run `git tag -a vX.Y.Z <merge commit> -m "semrail X.Y.Z"` and push. A published tag never moves.
  3. Verify a clean install from the tag, then bump `main` to the next `.dev0`.
- Before 1.0, features take a minor bump.
- CHANGELOG.md starts with a `## Unreleased` section. Entries are bullets with a bold lead that describe user-visible behaviour, not individual commits.
- DESIGN.md is updated in the same PR as the behaviour it describes. The README documents every command.

## Code and test style

- Use `from __future__ import annotations` in every module and type hints on public functions. Prefix private helpers with `_`. Give each module a short docstring that states its job. Comments explain why and cite DESIGN.md sections where relevant.
- Tests run the CLI end-to-end against temporary git repos and assert on exit codes and `--json` output, not on internals. Use one test file per feature. A bug fix comes with a regression test that was seen failing first. Keep a test that checks the skill text names real CLI commands.
- The repo may be public while consumers are private. Do not commit internal hostnames, private URLs or paths, client or employer names, ticket IDs from real projects, or real sample data. Generalize a need that comes from a consumer before committing it.

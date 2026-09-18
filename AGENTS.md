# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Purpose

semrail computes [Semantic Versioning](https://semver.org/) versions and changelogs from [Conventional Commits](https://www.conventionalcommits.org/). It supports one or more packages per repository and is meant for repositories developed with agents. It is a Python ≥3.11 CLI managed with uv.

## Language

- Everything committed is in English: code, comments, docs, commit messages, PR titles and bodies, and file names.
- Reply to the user in the language they write in. This never changes the language of anything committed.

## Principles

- KISS, YAGNI, Rule of three, Occam's razor, and "premature optimization is the root of all evil" decide what gets built. Build only what a current, concrete need requires. Extract an abstraction only at the third occurrence. Optimize only after measuring. When a principle leads to leaving something out, say so briefly in the PR.
- semrail is standalone. This repo tracks its own tasks with taskrail, and that is the only role taskrail has here. semrail must not depend on it, integrate with it, or be designed around it. semrail's code, tests and product docs (`docs/`, README) must not name it or any other sibling tool. Describe interoperation generically.
- All docs live in `docs/`. Keep them concise: short, factual statements, and don't repeat what the code already says. Comments explain why, not what.
- Update docs in the same PR as the behaviour they describe.
- Keep this file a short index of global rules (progressive disclosure). When a topic needs more than a few lines, write it in `docs/` and add a one-line pointer under Documentation map saying when to read it. Use plain-text paths, not @ imports, so every agent can follow them and each doc is read only when needed.
- CLAUDE.md and AGENTS.md must stay in sync. Apply any change to one to the other in the same commit; they differ only in the header.

## Commits

Use Conventional Commits, `type(scope): summary`, where the scope is the affected area. Every PR is squash-merged, and its title becomes the commit on `main`.
- `feat(cli): add a bump command`
- `fix(parser): accept a trailing issue reference`
- `docs: split agent context into index and docs/`

## Commands

```sh
uv run pytest                               # all tests
uv run pytest tests/test_x.py -k some_case  # a single test
uv run semrail --root <repo> <command>      # run the CLI against another repository
```

## Documentation map

- Versioning rules, commit parsing, monorepo packages, CLI contract, and the planned architecture → `docs/design.md`
- Code and test style, dependencies, and what must never be committed to this public repo → `docs/development.md`
- Branching, PRs, the changelog format, and how to cut a release → `docs/releasing.md`
- What is left to do, and how to create and work tasks → `TODO.md` and `.claude/skills/taskrail/SKILL.md`

## Current state

Bootstrap stage: there is no code yet. `docs/design.md` is the agreed spec; `TODO.md` builds it in order. Ask before introducing a new tool or dependency, record the decision with its date in `docs/`, and update this file.

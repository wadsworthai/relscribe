# T007 — Add CI, PyPI publishing and uvx-first usage docs

## Goal

This task gives the repository:
- CI: the tests and a PR-title check;
- a workflow that tags each merged release;
- a `relscribe.toml`, so relscribe can release itself;
- usage docs that recommend `uvx`, with the version pinned per repository.

T010 then cuts 0.1.0 by following `docs/releasing.md`.

**Scope change (human, during implement):** relscribe is not published to PyPI or any other registry for now. The `vX.Y.Z` git tag is the release artifact. Consumers run a pinned tag with `uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe`. The publish job, the `pypi` environment and every PyPI mention were therefore dropped from the approved change set. The task's title still says "PyPI publishing"; it is kept as the task's recorded name.

The premises held at `origin/main` (3b65731): there was no `.github/`, no `relscribe.toml` and no `CHANGELOG.md`, and `pyproject.toml` had version `0.0.0`.

## Change set

### `.github/workflows/ci.yml` (new)

- Runs on `pull_request` and on `push` to `main`, with `contents: read`.
- A matrix over Python `3.11` and `3.14`: `actions/checkout@v7.0.1`, then `astral-sh/setup-uv@v10.1.0` with `python-version`, then `uv run --locked pytest`.
- `--locked` fails on a stale `uv.lock`.

### `.github/workflows/pr-title.yml` (new)

- Runs on `pull_request`, types `opened, edited, synchronize, reopened`, with `contents: read`.
- Runs `uv run relscribe lint "$TITLE"`, with `TITLE` taken from `github.event.pull_request.title` through `env`, so the title is never interpolated into the script.

### `.github/workflows/release.yml` (new)

- Runs on `push` to `main`, with `permissions: {}` and `concurrency: {group: release, cancel-in-progress: false}`.
- One job, `tag`, with `contents: write`:
  - checkout with `fetch-depth: 0` (full history and tags), then setup-uv;
  - it sets the committer identity to `github-actions[bot]`;
  - it runs `uv run relscribe tag "$BEFORE..$AFTER" --push origin`, where `BEFORE` and `AFTER` are `github.event.before` and `github.sha`, both passed through `env`.
- The pushed `vX.Y.Z` tag is the release. There is no build and no upload.
- This repository runs its own source (`uv run`) because it is relscribe itself. Each merge is tagged by the code being merged, and there is no earlier release to pin to. Consumers pin a tag with `uvx --from git+…`.

### `relscribe.toml` (new)

```toml
tag = "v{version}"
# uv.lock repeats the project's version; match only this package's entry.
sync = [
  { file = "uv.lock", pattern = '^name = "relscribe"\nversion = "([^"]+)"' },
]
```

`uv.lock` records the project version on the line after `name = "relscribe"`. The pattern matches only that entry.

### Docs

- **`docs/releasing.md`:**
  - A new "CI" section lists the three workflows and explains why they run relscribe's own source.
  - "Cutting a release" is rewritten as the procedure T010 follows:
    1. check `status` on an up-to-date `main`;
    2. run `uv run relscribe release --branch --commit`;
    3. push the branch and open a PR titled with the release subject, then squash-merge it;
    4. CI creates and pushes `v<new>`, which completes the release.
  - It also covers re-runs and conflicts. The manual-release paragraph is gone.
  - A new "Repository setup" section lists the human prerequisites.
- **`README.md`:**
  - The status note becomes "early development (0.y.z)".
  - Requirements: uv (which provides Python) and git.
  - "Running relscribe":
    - relscribe is not in a registry;
    - the recommended form is `uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe <command>`, pinned per repository, with nothing installed;
    - `git+ssh://git@github.com/wadsworthai/relscribe@vX.Y.Z` for a private fork or SSH CI, and CI needs read access to the repository;
    - `uv add --dev "relscribe @ git+https://…@vX.Y.Z"` for Python projects;
    - "Installing globally (not recommended)" with `uv tool install git+https://…@vX.Y.Z`.
  - Usage: `lint`, `status`, `release` and `tag` (with `--push` and `--dry-run`), each with the git `uvx` form. The flag and exit-code tables stay.
  - Configuration: units, a key table and an example.
  - CI recipes:
    - the PR-title lint, with the title passed through `env`;
    - the tag workflow;
    - the note that `GITHUB_TOKEN` tags trigger no other workflow;
    - the two `--dry-run` queries, with `reconciled`;
    - the `package.json` scripts.
  - "Migrating an existing repository", and "Tag conflicts" (exit 4 on every run until resolved).
  - The `relscribe init` TODO is removed.
  - There is no PyPI mention and no `uvx relscribe@X.Y.Z` form.
- **`docs/design.md` Distribution:**
  - relscribe is not published to any registry, and the `vX.Y.Z` tag is the release artifact;
  - consumers run a pinned tag with `uvx --from git+…@vX.Y.Z`;
  - relscribe's own `tag` template and `uv.lock` `sync`;
  - its own CI runs relscribe's source.
- **`docs/development.md`:**
  - CI runs `uv run --locked pytest` on 3.11 and 3.14 and lints PR titles;
  - a dated tooling note (2026-09-18): GitHub Actions, with checkout and setup-uv pinned to exact release tags, and nothing published to a registry.
- **`CLAUDE.md` and `AGENTS.md`** get the same "Current state" update: pre-release, CI and the release-tagging workflow exist, and the next step is 0.1.0.
- **Task record:** this file, and its row in `docs/chores/README.md`.

## Human prerequisites (hand-off; none done by this task)

1. Pull requests: allow squash merging only, and set the default squash commit message to "Pull request title".
2. Actions: "Workflow permissions" must let a job request `contents: write`.
3. Tag rulesets: if any ruleset protects `v*` tags, allow `github-actions[bot]` to create them.
4. Recommended: require the `ci` and `pr-title` checks before merging to `main`.

## Decisions

The scope decisions are recorded in `docs/autopilot/decisions/T007-add-ci-pypi-publishing-and-uvx-first-usa.md`. Decisions 1 (`uv publish`) and 2 (when to publish) no longer apply after the scope change. Decisions 3–7 are applied: exact action tags, `--locked`, the concurrency group, and the dated tooling note in `docs/development.md`.

## Out of scope

- Publishing to PyPI or any registry, for now (the human's decision). It would add a build and upload job to `release.yml` later.
- Cutting a release, creating or pushing any tag in this repository, and configuring GitHub.
- A GitHub Action, zipapp or other distribution channel (YAGNI).
- A linter, formatter, coverage tool or type-checker.
- Any change to relscribe's code.
- Windows or macOS CI.
- Backlog wording that still names PyPI: the E01 "Done when" line and T010's description. That is for the orchestrator or the human (see the implement gate).

## Verification

### Scope stage (scratch clone `$S/sim`, with the proposed `relscribe.toml`)

- `status` in the worktree gives `relscribe (.): 0.0.0 -> 0.1.0 (minor)`, base whole history, 14 commits, exit 0.
- `release --branch --commit` wrote `pyproject.toml`, `uv.lock` and `CHANGELOG.md` and committed `chore(release): relscribe 0.0.0 -> 0.1.0`. Only the `relscribe` entry of `uv.lock` changed, and `uv lock --check --offline` exits 0 afterwards.
- After a squash merge titled `chore(release): relscribe 0.0.0 -> 0.1.0 (#10)`:
  - `lint` passes;
  - `tag --dry-run --json <before>..<after>` reports `v0.1.0`, `would-create`, `reconciled: false`, exit 0.
- After tagging and a later `chore:` commit, `status` gives `0.1.0, no release` (base tag `v0.1.0`). With the tag removed, the base is the version change and there is still no release.

### Implement stage

- `actionlint` 1.7.12, with shellcheck 0.11.0 on `PATH`, on all three workflows: `Found 0 errors in 3 files`, exit 0.
- `uv run --locked pytest` on Python 3.11 and 3.14: `265 passed` on both.
- PR-title step, run as `bash -e -c 'uv run relscribe lint "$TITLE"'`:
  - with `TITLE='feat: x"; touch …/pwned; echo "$(touch …/pwned2)'` it gives `1 subject valid`, exit 0, and neither file was created;
  - with `TITLE='Update stuff; rm -rf /'` it gives `invalid: …`, `1 of 1 subject invalid`, exit 1.
- Git-pinned `uvx`, in the scratch clone only:
  - `relscribe tag HEAD~2..HEAD` created `v0.1.0` there;
  - `uvx --no-cache --from "git+file://$S/sim@v0.1.0" relscribe --version` resolved `v0.1.0` to 4cf5e86, built it and printed `0.1.0`, exit 0;
  - through the same form, `lint "feat(api): add sessions"` gives `1 subject valid`, and `status` gives `0.1.0, no release`, base tag `v0.1.0`.
- Worktree, read-only, with the committed `relscribe.toml`: see the implement gate report for the `status` and `tag --dry-run origin/main..HEAD` outputs.
- `taskrail checks T007`: see the implement gate report.

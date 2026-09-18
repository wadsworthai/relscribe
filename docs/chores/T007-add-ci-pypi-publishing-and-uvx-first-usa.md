# T007 — Add CI, PyPI publishing and uvx-first usage docs

## Goal

Give this repository CI (tests and a PR-title check), a workflow that tags each merged release and publishes it to PyPI with trusted publishing, and a `relscribe.toml` so relscribe can release itself. Document how to use relscribe: `uvx relscribe@X.Y.Z`, pinned per repository, is the recommended way and the one every example uses. T010 then cuts 0.1.0 by following `docs/releasing.md`.

The task's premises still hold at `origin/main` (3b65731). There is no `.github/`, no `relscribe.toml` and no `CHANGELOG.md`. `pyproject.toml` has version `0.0.0`, and the README still has its TODO placeholders. The branch name comes from the task's earlier title. It holds no earlier work.

## Change set

### `.github/workflows/ci.yml` (new): tests

- Runs on `pull_request` and on `push` to `main`, with `permissions: contents: read`.
- One job with a matrix over Python `3.11` (the minimum) and `3.14` (the latest stable CPython that uv offers today, 3.14.5). Its steps are `actions/checkout@v7.0.1`, then `astral-sh/setup-uv@v10.1.0` with `python-version: ${{ matrix.python }}`, then `uv run --locked pytest`.
- `--locked` fails when `uv.lock` is out of date, which would catch a release commit that forgot the lock (see `relscribe.toml` below).

### `.github/workflows/pr-title.yml` (new): PR-title check

- Runs on `pull_request` with types `opened, edited, synchronize, reopened`, so a title edit re-runs it. Permissions are `contents: read`.
- Its steps are checkout, setup-uv, then `uv run relscribe lint "$TITLE"` with `env: TITLE: ${{ github.event.pull_request.title }}`. The title is never interpolated into the script, so a crafted title cannot inject shell.
- It lives in its own file because the `edited` trigger should not re-run the test matrix.

### `.github/workflows/release.yml` (new): tag and publish

- Runs on `push` to `main`. Top-level `permissions: {}`, and `concurrency: {group: release, cancel-in-progress: false}` so two quick merges never tag and publish in parallel.
- Job `tag`, with `permissions: contents: write`:
  - checkout with `fetch-depth: 0`, which fetches full history and tags; then setup-uv;
  - it sets a committer identity (`github-actions[bot]`, `41898282+github-actions[bot]@users.noreply.github.com`);
  - it runs `uv run relscribe tag "$BEFORE..$AFTER" --push origin --json > tag.json`, where `BEFORE` is `github.event.before` and `AFTER` is `github.sha`, both passed via env;
  - it prints `tag.json`, then uses `jq` (preinstalled on the runner) to write step output `tag`: the last `v*` tag whose `result` is `"created"`, or empty. The last one is the newest, because reconciled entries come first and the range follows oldest first. An exit code of 4 (a conflict) fails the job, which is what we want: a human resolves it.
- Job `publish`, which `needs: tag`, runs `if: needs.tag.outputs.tag != ''`, uses `environment: pypi` and has `permissions: id-token: write, contents: read`:
  - it checks out `ref: ${{ needs.tag.outputs.tag }}`;
  - it runs `uv build`, then `uv publish`, which uses trusted publishing automatically when `id-token` is available. No token or secret is involved.
- The two steps share one workflow for a reason. Tags pushed with `GITHUB_TOKEN` do not trigger other workflows, so a separate `on: push: tags` workflow would never run.
- Splitting the work into two jobs gives each job only the permission it needs. It also means a failed upload can be retried with "Re-run failed jobs", which keeps the `tag` job's output. A plain re-run of the whole workflow would find the tag `existing` and publish nothing.
- **Why this repository runs its own source (`uv run relscribe`) instead of `uvx relscribe@X.Y.Z`:** relscribe is the tool itself. Each merge is checked and tagged by the code being merged, so there is no earlier release to pin to (there is none before 0.1.0). Consumers pin a published version with `uvx`.

### `relscribe.toml` (new)

```toml
tag = "v{version}"
# uv.lock repeats the project's version; match only this package's entry.
sync = [
  { file = "uv.lock", pattern = '^name = "relscribe"\nversion = "([^"]+)"' },
]
```

- `uv.lock` does record the project version: lines 67–68 are `name = "relscribe"` / `version = "0.0.0"`. The pattern anchors on the `relscribe` entry's name line, so it can never match another package's version. With the entry, the release commit keeps `uv.lock` current, and the manual `uv lock` + amend step in today's `docs/releasing.md` goes away.

### `docs/releasing.md` (rewrite of "Cutting a release")

The exact procedure T010 follows:
1. Check out an up-to-date `main` with a clean tree, and read `uv run relscribe status`.
2. Run `uv run relscribe release --branch --commit`. It creates `release/<date>` and commits `pyproject.toml`, `uv.lock` and `CHANGELOG.md` as `chore(release): relscribe <old> -> <new>`.
3. Push the branch and open a PR whose title is exactly that subject. Squash-merge it.
4. On the push to `main`, `release.yml` tags `v<new>` and publishes it to PyPI.
5. If the upload fails, use "Re-run failed jobs". If the tag job reports a conflict, a human resolves it; a published tag never moves.

The "Until then, cut releases by hand…" paragraph goes, and "Branches and PRs" and "Changelog" stay as they are. A short "CI" list names the three workflows. A "Repository setup" list holds the one-time human prerequisites below.

### `README.md` (rewrite of the placeholders)

- **Title and intro:** kept. The status note becomes "early development (0.y.z): commands and configuration may change", because the README ships in the 0.1.0 package, where "nothing is released yet" would be false.
- **Install / running relscribe:**
  - Recommended: `uvx relscribe@X.Y.Z <command>`, with the version pinned per repository (in CI, scripts or `package.json`) and nothing installed on the machine. Everyone runs the same version.
  - Python projects may instead use `uv add --dev relscribe` and `uv run relscribe`, which pins the version in `uv.lock`.
  - Without PyPI: `uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe <command>`.
  - A separate short section, "Installing globally (not recommended)", covers `uv tool install relscribe` and says why it is not recommended: the version is not pinned per repository.
  - The `relscribe init` TODO is removed, because no such command is planned (YAGNI).
- **Usage:** one subsection per command, `lint`, `status`, `release` (`--commit`, `--branch`) and `tag` (`--push`, `--dry-run`). Each has a one-line description, its flags and a `uvx relscribe@X.Y.Z …` example, and links to `docs/design.md` for the JSON shapes. The global flags and exit-code tables stay.
- **Configuration:** a `relscribe.toml` keys table (`tag`, `changelog`, `exclude`, `sync`, `bump`) with defaults, the `[units."<path>"]` override rule, and a short example. It stays in sync with `docs/design.md`, which remains the spec.
- **CI recipe for consumers:** GitHub Actions snippets using `astral-sh/setup-uv` and `uvx relscribe@X.Y.Z`:
  - a PR-title lint, with the title passed via env;
  - the tag workflow on pushes to the release branch: full history, committer identity, `contents: write`, `tag "$BEFORE..$AFTER" --push origin`, and publishing in the same workflow, because tags pushed with `GITHUB_TOKEN` trigger nothing;
  - the two `--dry-run` queries, `<sha>^..<sha>` (is this commit a release?) and `<mainline>..<release-branch>` (which units does it release?), with the `reconciled` filter;
  - a `package.json` `scripts` example (`"release": "uvx relscribe@X.Y.Z release --branch --commit"`, `"release:status": "uvx relscribe@X.Y.Z status"`).
- **Migrating an existing repository** (generic):
  - keep existing tags by setting `tag` (globally or per unit) to their format;
  - an existing changelog is kept: new sections go below `## [Unreleased]` or before the first `##` heading, and old lines are never rewritten;
  - versions repeated in other files are kept in step with `sync`;
  - test-only commits are kept from bumping with `exclude`;
  - units released before any tag: the base falls back to the last version change, and the first `tag` run reconciles the latest release's tag;
  - non-conventional history is reported as warnings and bumps nothing, so check `status` first;
  - `changelog = false` lets relscribe coexist with another changelog tool.
- **Known behaviour:** when the tag of a unit's latest release exists on another commit, every `tag` run reconciles it again and exits 4 until a human resolves it. They can fix or delete the wrong tag if it was never published, or make a new release of that unit.
- No consumer names, sibling-tool names or internal URLs. The GitHub URL is the public repository.

### Smaller doc edits

- `docs/design.md`, Distribution: one sentence adding the `uv.lock` `sync` entry, and that the repository's CI runs its own source.
- `docs/development.md`, "Dependencies and tooling":
  - CI runs the tests on Python 3.11 and 3.14 and lints PR titles;
  - a dated record (2026-09-18) of the new tooling: GitHub Actions with `actions/checkout` and `astral-sh/setup-uv` pinned to exact release tags, and PyPI trusted publishing through `uv publish`. CLAUDE.md asks for new tools to be recorded with their date.
- `CLAUDE.md` and `AGENTS.md`, identically: "Current state" says CI and the release workflow exist and that the next step is the first release (0.1.0). Nothing else changes.

### Task record

- This file, and a row for it in `docs/chores/README.md`.

## Human prerequisites (hand-off; none done by this task)

1. **PyPI pending trusted publisher** for the project `relscribe`: owner `wadsworthai`, repository `relscribe`, workflow `release.yml`, environment `pypi`. It is "pending" because the project does not exist on PyPI until the first upload.
2. **GitHub environment `pypi`** in `wadsworthai/relscribe`, with its deployment branches limited to `main`. Required reviewers are optional; they would add a manual approval to each publish.
3. **Pull request settings:**
   - allow squash merging only, with rebase and merge commits disabled;
   - set the default squash commit message to "Pull request title". Without it, GitHub uses the commit message for single-commit PRs, and the release subject could differ from the PR title.
4. **Actions permissions:** "Workflow permissions" must let a job request `contents: write`. The job asks for it explicitly, but an org policy can cap it.
5. **Tag protection:** if any ruleset protects `v*` tags, `github-actions[bot]` must be allowed to create them. There is no need to push to `main`, so branch protection on `main` does not block the tag job.
6. **Recommended:** require the `ci` tests and the PR-title check before merging to `main`.

## Decisions needed

1. **Upload tool:** `uv publish` (recommended: one tool, already used, trusted publishing built in), or `pypa/gh-action-pypi-publish@v1.14.2`, which also uploads PEP 740 attestations by default but adds a third-party action.
2. **When to publish:** publish the newest `v*` tag the run created, and retry a failed upload with "Re-run failed jobs" (recommended, simplest). The alternative is to also publish when the range's own release tag is `existing` (not reconciled), so that a full re-run publishes too. That is more logic for a rare case.
3. **Pinning actions:** exact release tags such as `@v7.0.1` (recommended; setup-uv has not published floating major tags since v8, so an exact tag is needed anyway), or full commit SHAs with a version comment (stricter, but noisier to update).
4. **`--locked` in CI tests:** yes (recommended), to catch a stale `uv.lock`; or a plain `uv run pytest`, as the local check runs it.
5. **Concurrency group on `release.yml`:** yes (recommended). Without it, two merges in quick succession could both create the same tag and upload twice, and the second upload would fail.
6. **Where to record the tooling decision:** a dated line in `docs/development.md` (recommended), or a new top-level doc, which would also need a Documentation map entry.

## Out of scope

- Cutting a release, creating or pushing any tag, or uploading to PyPI or TestPyPI (T010 and the human).
- Configuring GitHub or PyPI (the human prerequisites above).
- A GitHub Action, zipapp, Homebrew formula or any other distribution channel (YAGNI, per the human's decision).
- A linter, formatter, coverage or type-checker in CI (development.md: adding one is a deliberate decision).
- Any change to relscribe's code or behaviour.
- A Windows or macOS CI matrix. relscribe is stdlib-only and nothing needs it yet.

## Verification

Scope-stage evidence, gathered read-only in the worktree and in a scratch clone (`$S/sim`, where `$W` is the worktree), with no tag or push in this repository:
- `uv run --directory $W relscribe --root $W status` gives `relscribe (.): 0.0.0 -> 0.1.0 (minor)` with `base: whole history`, 14 commits and exit 0.
- In the scratch clone, with the proposed `relscribe.toml`, `release --branch --commit` wrote `pyproject.toml`, `uv.lock` and `CHANGELOG.md` and committed `chore(release): relscribe 0.0.0 -> 0.1.0`. The `uv.lock` diff changes only the `relscribe` entry's `version`, and `uv lock --check --offline` exits 0 afterwards.
- A squash merge of that branch onto `main`, titled `chore(release): relscribe 0.0.0 -> 0.1.0 (#10)`, is still a release:
  - `lint` on that title gives `1 subject valid`, exit 0;
  - `tag --dry-run --json <before>..<after>` gives one entry, `v0.1.0`, `"would-create"`, `"reconciled": false`, exit 0.
- After tagging in the scratch clone and adding a later `chore:` commit, `status` gives `relscribe (.): 0.1.0, no release` with `base: tag v0.1.0`. With the tag deleted, the base is `version change` and there is still no release, so `chore(release)` bumps nothing. `tag --dry-run HEAD^..HEAD` then reports `would-create v0.1.0 … (reconciled)`.

Implement-stage checks:
- `actionlint`, if it is available, or a YAML parse of each workflow.
- `uv run --locked pytest` on 3.11 and 3.14 locally, as the matrix does, and `taskrail checks T007`.
- `uv build` in a scratch clone, which should produce an sdist and a wheel named `relscribe-0.0.0`.
- The `jq` filter run against a real `tag --json` output from the scratch clone (`created` gives `v0.1.0`; no releases gives an empty string).
- The PR-title step run with a hostile `TITLE` value.
- Read-only `status` and `tag --dry-run origin/main..HEAD` in the worktree with the real `relscribe.toml`, to show that merging T007 tags nothing.

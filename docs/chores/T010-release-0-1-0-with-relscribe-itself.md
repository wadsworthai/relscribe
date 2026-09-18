# T010 — Release 0.1.0 with relscribe itself

## Goal

Cut relscribe 0.1.0 with relscribe, following `docs/releasing.md`. The release is done when the squash commit of the release PR is on `main` and `release.yml` has created and pushed the `v0.1.0` tag on it. relscribe is not published to any registry; the tag is the release.

The premises hold at `origin/main` (b97e6c2): `pyproject.toml` and `uv.lock` have version `0.0.0`, there is no `CHANGELOG.md` and no tag, and `relscribe.toml` sets `tag = "v{version}"` with a `sync` entry for `uv.lock`. `relscribe status` reports `relscribe (.): 0.0.0 -> 0.1.0 (minor)` over the whole history (six `feat` commits). `relscribe tag --dry-run origin/main..HEAD` reports `no releases to tag`.

## Change set

Proposed: option (a) below, where this task's branch is the release branch.

1. **Release commit**, made by relscribe, not by hand: `uv run --directory <worktree> relscribe --root <worktree> release --commit`, without `--branch`, on this branch, from a clean tree based on the current `origin/main`. It writes and commits only:
   - `pyproject.toml`: `version = "0.0.0"` becomes `"0.1.0"`;
   - `uv.lock`: the `relscribe` package entry's version, through `sync`;
   - `CHANGELOG.md` (new): the Keep a Changelog header, an empty `## [Unreleased]` and `## [0.1.0] - 2026-09-18` listing the `feat` commits.

   Its subject is `chore(release): relscribe 0.0.0 -> 0.1.0`.
2. **This record** and its row in `docs/chores/README.md`.
3. **`docs/releasing.md`** (docs stage, if approved): one sentence saying that a branch whose only purpose is the release may carry the release commit (`release --commit` without `--branch`), and that its PR title does not affect tagging.
4. **`TODO.md`**: only `taskrail done T010`.

Commit order on the branch:
1. `docs(chores): scope T010` — this record and its index row;
2. `chore(release): relscribe 0.0.0 -> 0.1.0` — the release commit (implement);
3. `docs(chores): record T010 verification` — results under Verification;
4. `docs(releasing): …` — the sentence from item 3, if approved;
5. `chore: mark T010 done` — the status change on its own.

The record-keeping commits are `docs` and `chore`, which do not bump. They neither change the version nor appear in the changelog, whether they come before or after the release commit.

## Decisions needed

1. **How the release commit and the task branch fit together.**
   - **(a) Recommended.** The task branch is the release branch. One PR carries the release commit plus this record and the done row. Its squash commit on `main` raises the version from `0.0.0` to `0.1.0`, so `release.yml` tags it `v0.1.0`. There is one PR and no branch outside the task's workflow. The cost is that `docs/releasing.md` says "Task branches never change the version or `CHANGELOG.md`" and step 2 uses `--branch`. That rule protects against bumping on feature branches. A branch whose only purpose is the release still changes the version only in a release commit, which is what `docs/design.md` ("Bump timing") requires.
   - **(b)** Follow `docs/releasing.md` literally: `release --branch --commit` creates `release/2026-09-18`, which the human pushes and merges as a second PR, and the task branch carries only the record. This needs two PRs, and the task cannot be closed on evidence it produces itself. It also leaves the task's `done` row unmerged until after the release, or merged before it.
2. **PR title under (a).**
   - **Recommended:** the title `taskrail review --publish --scope release` generates, `chore(release): release 0.1.0 with relscribe itself (T010)`. Like every other squash commit on `main`, it keeps the task ID, and the publish flow produces it without a manual edit.
   - **Alternative:** exactly `chore(release): relscribe 0.0.0 -> 0.1.0`, as `docs/releasing.md` step 3 says. The human edits the title on GitHub before merging.

   Both pass `relscribe lint` (see Verification). Neither affects tagging: a commit is a release when it raises the version over its parent's, and the message is never consulted (`docs/design.md`, "Release detection"). A `chore` title does not bump, so it cannot affect the next version either.
3. **Docs sentence (item 3).** Recommended: add it, so the rule "Task branches never change the version" is not contradicted by this merge. Alternative: leave the docs unchanged, since this is a one-off (YAGNI).

## Constraint: the release must be regenerated if `main` moves

The changelog is computed from `main` as it was when the release commit was made. If another PR merges to `main` first, its commits come before the release's base. They would then never appear in any changelog, and a rebased release commit would carry a stale `CHANGELOG.md`. If `taskrail review` reports `rebase.needed`, do not rebase the release commit. Drop it, rebase the rest onto the new `main`, and run `release --commit` again on top. The orchestrator decides this at the close. This lane never rebases.

## Out of scope

- Pushing, opening or merging the PR, and creating or pushing any tag. CI creates `v0.1.0` after the human squash-merges, and the orchestrator verifies it on the remote.
- A real `relscribe tag` run in this repository. Only `status` and `tag --dry-run` are run.
- Any code, test, workflow or `relscribe.toml` change.
- Publishing to a registry.

## Verification

Planned, in implement:
- `git show --stat HEAD` of the release commit: exactly `pyproject.toml`, `uv.lock` and `CHANGELOG.md`, and the expected subject.
- The generated `CHANGELOG.md`, and the `pyproject.toml` and `uv.lock` diffs.
- `uv lock --check` passes.
- `relscribe status` after the release reports nothing to release.
- `relscribe tag --dry-run --json origin/main..HEAD` reports `v0.1.0` as `would-create` on the release commit.
- `taskrail checks T010` (test = `uv run pytest`; lint is not configured by design).

Results, in implement, with `origin/main` still at b97e6c2 and a clean tree:
- `release --commit --json` made commit 8c8ffd0 with `files: ["pyproject.toml", "uv.lock", "CHANGELOG.md"]`, `branch: null` and `0.0.0 -> 0.1.0 (minor)`. There were no warnings.
- `git show --stat HEAD` shows subject `chore(release): relscribe 0.0.0 -> 0.1.0`. It changes only `CHANGELOG.md` (+19), `pyproject.toml` (1 line) and `uv.lock` (1 line, the `relscribe` entry).
- `CHANGELOG.md`: the standard header, an empty `## [Unreleased]`, then `## [0.1.0] - 2026-09-18`. Under `### Added` it lists the six `feat` commits T002–T006 and T009. Neither the `docs(chores)` scope commit nor the recorded decisions commit appears.
- `uv lock --check`: `Resolved 7 packages`, exit 0.
- `relscribe status`: `relscribe (.): 0.1.0, no release`, base `version change (8c8ffd0)`.
- `relscribe tag --dry-run --json origin/main..HEAD` reports one entry: `v0.1.0`, `result: "would-create"`, `sha` 8c8ffd0, `reconciled: false`, with no warnings.
- `taskrail checks T010 --stage implement`: test passed with `265 passed`. Lint is not configured.

Scope evidence (read-only, at b97e6c2):
- `relscribe status`: `relscribe (.): 0.0.0 -> 0.1.0 (minor)`, base `whole history`.
- `relscribe tag --dry-run origin/main..HEAD`: `no releases to tag`.
- `relscribe lint "chore(release): relscribe 0.0.0 -> 0.1.0" "chore(release): release 0.1.0 with relscribe itself (T010)" "chore: release 0.1.0 with relscribe itself (T010)"`: `3 subjects valid`.

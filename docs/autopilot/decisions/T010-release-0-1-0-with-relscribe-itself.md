# T010 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T010-release-0-1-0-with-relscribe-itself.md` at 025220a (the artifact and index row only). Read-only evidence: `status` gives `0.0.0 -> 0.1.0 (minor)` with no warnings; `tag --dry-run origin/main..HEAD` gives "no releases to tag"; all candidate PR titles pass `lint`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Release commit and task branch | (a) task branch is the release branch (`release --commit`, no `--branch`) · (b) separate `release/<date>` PR | **(a)** | One PR, and it stays within the design's rule that versions change only in a release commit. The squash commit raises the version, so `release.yml` tags it. |
| 2 | PR title | taskrail's `chore(release): release 0.1.0 with relscribe itself (T010)` · exactly the release subject | as recommended (taskrail's) | Tagging is by version change, not by message. It keeps the task ID like every other squash commit, and `chore` bumps nothing. |
| 3 | Sentence in `docs/releasing.md` | yes · no | as recommended (yes) | Without it, this merge contradicts "Task branches never change the version". Keep it to one or two sentences. |

Constraint accepted: if `main` moves before this PR merges, the release commit is dropped and regenerated on the new `main`, never rebased. The orchestrator handles this at hand-off.

## implement gate

Reviewed: release commit 8c8ffd0, made by relscribe itself. It touches exactly `pyproject.toml` and `uv.lock` (0.0.0 → 0.1.0, relscribe entry only) and a new `CHANGELOG.md` listing the six `feat` commits from T002 to T009 under Added. `uv lock --check` passes. `status` afterwards reports "0.1.0, no release". `tag --dry-run origin/main..HEAD` predicts exactly one tag, `v0.1.0 would-create` on the release commit. `taskrail checks T010` re-run: 265 passed. There are no tags locally or on the remote.

No decisions were needed. The stage is approved.

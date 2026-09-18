# T002 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: `docs/features/T002-parse-conventional-commit-subjects-and-a.md` at cacf7a5, the diff `origin/T001-scaffold-the-package-cli-skeleton-and-te..cacf7a5` (artifact and index only), `taskrail checks T002 --stage plan` (no checks at this stage; passed). The criteria cover the task row and `docs/design.md` Versioning, Commit parsing and the `lint` row; each is testable.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Add the implicit parsing rules (case-insensitive type, footer on any body line, merges skipped by `lint --range`) to `docs/design.md` | add · artifact only | as recommended | CLAUDE.md requires docs to change in the same PR as the behaviour. Edit only the Versioning and Commit parsing sections. |
| 2 | A type mapped to `"major"` gives `minor` while 0.y.z | yes · honour literally | as recommended | This keeps "no MAJOR before 1.0.0" true whatever the cause, which is the pre-1.0 rule both reference setups follow. |
| 3 | Fix the README "How versions are computed" table (`refactor`, `perf`, `BREAKING-CHANGE:`) | fix here · leave to T007 | as recommended | It contradicts `docs/design.md` on exactly the rules this task implements. |

Implement test-first: record each new test failing before the code exists, as the feature executor requires.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which part of `docs/design.md` | split by section · one owner | **split by section: T002 edits Versioning and Commit parsing; T003 edits Units** | The sections don't overlap, so the parallel edits merge cleanly. |
| 2 | `docs/features/README.md` rows | keep all | **keep all, one row per task** | This is known conflict class 2. |

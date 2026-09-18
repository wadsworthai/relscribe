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

## implement gate

Reviewed: the diff `d295d8f..4486aa2` (`commits.py`, the `lint` command in `cli.py`, tests, and the Versioning and Commit parsing sections of `docs/design.md` plus the README bump table); the test-first evidence in the lane's report (collection error, then 15 failing lint tests); `taskrail checks T002` re-run (72 passed). Exercised for real outside the repository: `semrail lint "feat(0037:api:session): add x (#82)" "oops"` → `invalid: oops` / `1 of 2 subjects invalid`, exit 1; `semrail lint --root <repo> --range dad6233..39637e4` → `5 subjects valid`, exit 0.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Summary wording for a single subject (`1 subjects valid`) | fix · leave | **fix: singular for one subject** | It is user-facing output, and the fix is one expression. Cover it with a test. |

Notes carried to later tasks, not changed here: `bump()` raises `ValueError` on an unknown level in the map, and `next_version()` raises `ValueError` on a non-plain version. Validating the map is T003's config work. T004 must turn both into exit 2 at the CLI, never a traceback.

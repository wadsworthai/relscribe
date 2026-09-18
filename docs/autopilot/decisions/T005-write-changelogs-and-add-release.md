# T005 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: `docs/features/T005-write-changelogs-and-add-release.md` at 63a56b0, the plan's diff (artifact and one index row), and the baseline checks (171 passed). The 16 criteria cover the task row, `docs/design.md` Changelog and the `release` row, and the legacy changelog shapes semrail must not break.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Group for a type that bumps only through an override | Changed · by level · omit | as recommended | Keep a Changelog's Changed is the neutral group, so no group means the wrong thing. |
| 2 | Commits that don't bump in the changelog | no · "Other" group | as recommended | The spec says no, and "Other" is not a Keep a Changelog group. |
| 3 | Nothing to release | exit 0 · exit 1 | as recommended | Exit 1 means lint or validation failed. CI reads "nothing" from the empty `units`. |
| 4 | Preflight | refuse uncommitted tracked changes · more · none | as recommended | It prevents releasing on top of stray edits, without a new setting. |
| 5 | Date and branch name | UTC · local · HEAD date | as recommended | The result is deterministic across CI runners, and one `_today()` keeps tests simple. |
| 6 | Bullet order | oldest first · newest first | as recommended | The section then reads in the order work happened. |
| 7 | Legacy files without Unreleased | add header/Unreleased on top, old content untouched · refuse · normalise | as recommended | Existing changelogs keep working and old sections are never rewritten. |
| 8 | Commit subject and staging | written files only · `commit -a` | as recommended | The release commit must hold only the release. |
| 9 | `release --json` shape | as proposed · per-unit files | as recommended | |
| 10 | Warnings, including shallow clone | report and release · refuse on shallow | as recommended | Same rule as `status`: warnings never change the exit code. |
| 11 | CLAUDE.md/AGENTS.md "Current state" | edit here · leave to T007 | **leave to T007** | T006 runs in parallel and would edit the same line, which is a conflict outside the known classes. T007 updates it once for `release` and `tag`. README usage also stays with T007. |
| 12 | Roll back on a mid-release failure | restore originals · none | as recommended | "All files or none" is the contract, and the cost is about 10 lines. |
| 13 | `release --json` paragraph under the CLI table | allowed · not | **allowed** | It sits next to the `status --json` paragraph and describes only this command. |

Implement test-first and record the failing run.

## implement gate

Reviewed: `changelog.py` in full and the `cli.py` diff in c9684b4; the test-first evidence (collection error, then 25 errors before the code existed); `taskrail checks T005` re-run (214 passed). Exercised on a scratch pnpm repository whose legacy changelog started with `## 0.0.1 — 2026-09-08` and held an `### Unknown` group. `release --branch --commit` wrote `0.0.1 -> 0.1.0` and created `release/2026-09-18` with the commit `chore(release): @x/api 0.0.1 -> 0.1.0`. The changelog gained the standard header, `## [Unreleased]` and `## [0.1.0] - 2026-09-18` (Added, then Changed with `**BREAKING:**`), and the old section was left byte-identical below.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Import-line change in `cli.py` (`changelog`, `datetime`) | accept · local imports | as recommended | It follows the module convention. The possible conflict with T006 is additive, so both names are kept at hand-off. |

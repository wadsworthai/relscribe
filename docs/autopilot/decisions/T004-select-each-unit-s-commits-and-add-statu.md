# T004 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## rebase after T003

T003 was squash-merged into main as 0c8f686. The branch, which held only the plan commit, was rebased with `git rebase --onto origin/main a21094f`. There were no conflicts, `git diff --check` reports no conflict markers, `taskrail checks T004` passed (126 tests), and `taskrail validate` reports 0 errors and 0 warnings.

## plan gate

Reviewed: `docs/features/T004-select-each-unit-s-commits-and-add-statu.md` at 676d51b (after the rebase), the plan's diff (artifact and index row only), the lane's pathspec experiment output, and `taskrail checks T004`. The 14 criteria cover the task row and `docs/design.md` "Selecting a unit's commits", plus the `status` row and the items carried from T002 and T003.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `status --json` shape | as proposed · only the commits that bump · add a per-commit bump | as recommended | CI needs every commit, and warnings need the unparseable ones. A per-commit level would repeat data already present. |
| 2 | How `Unit.bump` combines with the defaults | merge entry by entry · replace · allow `"none"` | as recommended, **and yes to the Versioning sentence** | It's the least surprising rule. Disabling a default type is YAGNI. |
| 3 | Does introducing a version count as a change | no · yes | as recommended | A never-released unit then counts its whole history, rule 3 of the base stays reachable, and T006 applies the same rule. |
| 4 | Exclude nested units' paths from the enclosing unit | yes · count for both | as recommended | A commit belongs to the innermost unit, so a nested unit's work never bumps its parent. |
| 5 | `exclude` glob syntax | git `glob` pathspec relative to the unit · fnmatch | as recommended | One git call applies the "all files match" rule, and the lane's experiment confirmed it. State the syntax (`*` stays within a directory, `**/` spans directories) in `docs/design.md` Units, in one clause of the `exclude` row. |
| 6 | Warn on a shallow clone | yes · document only | as recommended | CI checkouts are often shallow, and counting the wrong history silently is the worse failure. |
| 7 | `ValueError` handling | leave it uncaught and prove the user paths exit 2 · catch it in `main` | as recommended | After validation only a bug can raise it. Tests must show that every user-triggerable input exits 2 with no traceback. |
| 8 | Add `history.py` to Architecture | yes · no | as recommended | Keeps the spec accurate. |

Allowed `docs/design.md` edits for this task: the opening sentence, Units (the `exclude` syntax clause only), Versioning (the merge sentence), Selecting a unit's commits, CLI, and Architecture. Implement test-first and record the failing run.

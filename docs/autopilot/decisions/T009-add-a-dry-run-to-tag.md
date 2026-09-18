# T009 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: `docs/features/T009-add-a-dry-run-to-tag.md` at 53022a1 (the artifact and its index row only). The 8 criteria cover both query use cases the human approved (is a commit a release before promoting it; which units a release branch touches), the interaction with `--push`, reconcile and conflicts. The task premise holds: `tag` today always creates tags.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Name of the result for a tag a dry run would create | `would-create` · `missing` · `new` | as recommended | It reads as the dry-run form of `created`. |
| 2 | `--dry-run` with `--push` | usage error · report a would-push · ignore | as recommended (exit 2) | A dry push can't know about rejections, and a `pushed` list of unpushed tags would mislead callers. |
| 3 | Exit code on a conflict under `--dry-run` | 4 · always 0 | as recommended (4) | The dry run then predicts the real run exactly, and a promotion step must not pass over a conflict. The JSON is still printed. |
| 4 | Reconciled releases in query results | `reconciled` field on every entry · `--no-reconcile` · implicit skip | as recommended (field, in real runs too) | No new mode: one filter serves both use cases, and reconcile can't be switched off in real CI. The added key only affects exact-equality readers, which are this repo's tests. |
| 5 | Text wording | `<result> <tag> <sha>` with ` (reconciled)` · extra header | as recommended | Same format as a real run. |

Leave README.md to T007. Implement test-first and record the failing run.

## implement gate

Reviewed: the diff of `tags.py` and `cli.py` in 0db7c71 (small and within the plan), the updated `docs/design.md`, and the test-first evidence (13 failures before the code existed). `taskrail checks T009` re-run: 265 passed. Exercised on a scratch repository: `tag --dry-run <sha>^..<sha>` printed `would-create @x/api@0.2.0 e188789` with exit 0 and created no tag, and `--dry-run --push origin` printed `relscribe: tag: --dry-run and --push cannot be combined` with exit 2.

No decisions were needed. The stage is approved.

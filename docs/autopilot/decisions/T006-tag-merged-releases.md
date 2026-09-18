# T006 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: `docs/features/T006-tag-merged-releases.md` at 2844884, the plan's diff (artifact and one index row), and the lane's probes: the glob pathspec matches root and nested manifests, and `git push --porcelain` reports a rejected tag as a `!` line. The 14 criteria cover the task row, the "Release detection" and "Tags" bullets, the `tag` row, exit code 4, and the CI situations semrail must handle (skipped runs, several units per commit, true merges, units without tags).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Reading units as of a release commit | temp dir with that commit's manifests and config, unchanged `discover` · working tree · worktree/archive per commit · git-tree reader in `units.py` | as recommended | Correct for units added, renamed or re-templated later, and it reuses discovery unchanged. Only the files discovery reads are materialised. |
| 2 | "Changes the version" means "raises it" | raises · literal change | as recommended; **reword the "Release detection" bullet** | A revert must not produce a conflict on every later push. This refines, not reverses, the human's choice of detecting releases by version change. |
| 3 | Introducing a version is a release | no · yes | as recommended | Same rule as the base in T004. A moved or imported unit must not get a false tag. |
| 4 | Commits examined | non-merge only · first-parent · merges too | as recommended | Consistent with selection. A release merged with a true merge is tagged once, on its own commit. |
| 5 | Reconcile | per unit, newest release reachable from `<from>` · global · all | as recommended | It covers a skipped CI run for any unit without tagging history from before semrail. |
| 6 | Annotated tag message | `<name> <version>` · tag name · subject | as recommended | |
| 7 | `--push` | only created tags, one porcelain push; rejected → 4, other failure → 2 · also existing · `--atomic` | as recommended | A tag that already exists was pushed before. One rejected tag must not block the others. |
| 8 | Does a conflict block other tags | no, exit 4 at the end · all or nothing | as recommended | Every valid release still gets its tag. The human resolves only the conflict. |
| 9 | `--json` shape | flat `tags` list with `result` · separate lists | as recommended | |
| 10 | `tag --json` paragraph under CLI and `tags.py` in Architecture | yes · no | **yes** | Same as T004 and T005. |

Do not edit CLAUDE.md or AGENTS.md: T005 runs in parallel, and T007 updates "Current state" once for `release` and `tag`. Implement test-first and record the failing run.

## implement gate

Reviewed: `tags.py` in full and the `gitutil.py`/`history.py` diff in 5416aa8; the test-first evidence (39 failures before the code existed); `taskrail checks T006` re-run (211 passed). Exercised on a scratch pnpm repository with a local bare remote. `tag <A>..HEAD --push origin` created `@x/api@0.2.0` (reconciled at `<from>`), `@x/api@0.3.0` and `@x/web@1.1.0` (two units in one commit), pushed 3 tags, exit 0. A rerun reported all 3 as `existing` and pushed 0, exit 0. The remote holds exactly the 3 tags.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Keep `GitError.stdout` in `gitutil.py` | keep · second calling style · treat all push failures as exit 2 | as recommended | Small, and it's the only way to honour "rejected tag → exit 4" while `gitutil` stays the only module that runs git. |
| 2 | Detecting "no unit" by the `ConfigError` message prefix | message prefix · `NoUnitError(ConfigError)` subclass | **subclass** | Matching message text is brittle, and the subclass is 3 lines. `units.py` is outside T005's touch map, so it can't conflict. Existing callers that catch `ConfigError` keep working. |

## rebase after T004 and T005

T004 (1b5089a) and T005 (6f1ef2d) were squash-merged into main. The branch was rebased with `git rebase --onto origin/main 0473879`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md` | keep both · stop | **keep both** | Known class 2. |
| 2 | Conflict in `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Known class 2. |
| 3 | Conflict in `src/semrail/cli.py`: the import line, the subparser blocks, the command blocks | keep both · stop | **keep both** (`changelog` and `tags` both imported; `release` then `tag`) | Covered by the run's touch map (decision 3): additive blocks, kept both. |
| 4 | Conflict in `docs/design.md`: Releases and tags, CLI rows, `--json` paragraphs | combine by owner · stop | **combine**: T005's "Bump timing"/"Release commit" and `release` row; T006's detection, units-as-of, reconcile, tags and push bullets and `tag` row; both `--json` paragraphs | Covered by the touch map. Each lane owns its bullets, so nothing is lost. |
| 5 | Conflict in `TODO.md` (T005 and T006 rows) | ✅ wins · stop | **✅ on both** | Known class 1. |

After the rebase: `git diff --check` reports no conflict markers, `taskrail checks T006` passed (255 tests, the union of both lanes' suites), `taskrail validate` reports 0 errors and 0 warnings, and `semrail --help` lists `lint`, `status`, `release` and `tag`.

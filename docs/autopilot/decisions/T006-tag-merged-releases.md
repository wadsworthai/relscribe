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

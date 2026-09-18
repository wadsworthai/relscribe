# T008 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which name, after "verstamp" turned out to be taken on crates.io (an unrelated binary-format crate) and as a GitHub user | keep verstamp · look for a name free everywhere | **look for another name; chose `relscribe`** | The human wants a name with no clashes. `relscribe` is free on PyPI, npm, crates.io, RubyGems and Homebrew, and has no GitHub user or repository of that name (checked 2026-09-18). |

Answered by the human. The task was retitled "Rename the tool from semrail to relscribe", and its unpushed branch was renamed to `T008-rename-the-tool-from-semrail-to-relscribe` with `taskrail branch`. The worktree directory keeps its old path.

## scope gate

Reviewed: `docs/chores/T008-rename-the-tool-from-semrail-to-verstamp.md` at 4027435, and the lane's `git grep` inventory (247 lines in 37 files). Only the artifact and its index row were edited. `taskrail checks T008` passed (255 tests). The change set holds for the new name: every `semrail` becomes `relscribe`, and every `Semrail` becomes `Relscribe`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Compatibility shim for the old name | no · read old config · script alias | as recommended (no) | Nothing was released, so no user relies on the old name (YAGNI). |
| 2 | PR title type | `chore` · `refactor` · breaking | as recommended (`chore`) | No released consumer, and it stays out of the 0.1.0 changelog. |
| 3 | Epic E01 text | hand-edit the word in 3 places + `taskrail validate` · leave · name only | as recommended | There is no `epic edit` command. Changing one word keeps the table layout, IDs and statuses intact, and `validate` proves the backlog is still valid. |
| 4 | Done rows T002–T006 | leave · `edit --force` | as recommended (leave) | They are historical records. |
| 5 | Test names with `semrail_toml` | rename · leave | as recommended (rename) | `git grep` stays clean outside the records. |
| 6 | Artifact file name (it contains "verstamp") | rename with `git mv` to `…-relscribe.md` and fix its index row · keep | **rename** | The file name should match the task. Do the same for this decision record only if the orchestrator asks; it stays as is. |
| 7 | Stale "Current state" in CLAUDE.md/AGENTS.md (lists only `lint` and `status`) | fix here · leave to T007 | **fix here** | It's a one-line edit in files this task already rewrites, and it keeps T007 focused on CI and publishing. |

## implement gate

Reviewed: commit 87f8f1f (30 paths: the moved package, imports, `pyproject.toml`, `uv.lock` name line, tests, README, `docs/design.md`, `docs/releasing.md`, CLAUDE.md/AGENTS.md, and the backlog). CLAUDE.md and AGENTS.md are identical below their headers, and "Current state" lists all four commands. `git grep -i semrail` over `src`, `tests`, README, the product docs, the agent files, `pyproject.toml` and `uv.lock` finds nothing. `taskrail checks T008` re-run: 255 passed.

The lane's first `sed` ran in the main checkout by mistake. The lane restored the 16 files. The orchestrator confirmed the main checkout is clean, with HEAD = origin/main = 8c86e33 and an empty `git status` and `git diff HEAD`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the change set | approve · change | **approve** | It matches the approved scope under the new name, verified above. |
| 2 | Skip the docs stage | skip · look further | as recommended (skip, recorded) | The docs were updated in the implement stage. The gate is conditional. |
| 3 | Note the one-time `uv sync` in `docs/development.md` | no · add a line | as recommended (no) | Nothing was released, and it is a one-time local step. |

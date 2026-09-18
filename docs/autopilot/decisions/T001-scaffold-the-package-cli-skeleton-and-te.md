# T001 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T001-scaffold-the-package-cli-skeleton-and-te.md` at 964fb99, the diff `main..964fb99` (artifact and index only, nothing else edited), `taskrail checks T001 --stage scope` (no checks configured; passed), `touched` in `autopilot status` (only the two task-record files).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Placeholder version | `0.0.0` · `0.1.0` | as recommended | `docs/design.md` forbids pre-release spelling; the first `feat` then yields the planned `0.1.0`. |
| 2 | Add `[checks] test = "uv run pytest"` to `.taskrail/config.toml`, no `lint` | add · leave empty | as recommended | Every later lane and gate needs the suite run the same way; `docs/development.md` configures no linter by design. |
| 3 | Create `gitutil.py` (`git()`, `toplevel()`) in T001 | now · first task that needs it | as recommended | T002 and T003 run in parallel; one owner avoids a conflict. `docs/design.md` names it as the only module that shells out to git. |
| 4 | Accept `--json`/`--root` before and after the subcommand | both · before only | as recommended | CLAUDE.md uses `semrail --root x <cmd>`, and the design reads `semrail status --json`; both forms are part of the contract. |
| 5 | README drift (no exit code 4, `.semrail/config.toml` instead of `semrail.toml`) | fix here · leave to T007 | **fix here, in the docs stage** | Two factual lines that contradict `docs/design.md`; small and in the docs this task already updates. Fixing them avoids a follow-up task. |

Touch map for the run (T001 owns): `pyproject.toml`, `uv.lock`, `.gitignore`, `src/semrail/{__init__,cli,gitutil}.py`, `tests/{conftest,test_cli,test_gitutil,test_docs}.py`, `docs/development.md`, README (the two lines in decision 5), CLAUDE.md/AGENTS.md "Current state", `.taskrail/config.toml` `[checks]`. Later lanes add their own subparsers to `cli.py` and their own `tests/test_<feature>.py`.

## implement gate

Reviewed: the diff `68cf404..170be79` (src, tests, pyproject.toml, .gitignore, `.taskrail/config.toml`); `taskrail checks T001` re-run by the orchestrator (8 passed, lint not configured); `semrail --json --version` (exit 0, `{"version": "0.0.0"}`) and bare `semrail` (exit 2, `semrail: error: a command is required`) run from outside the worktree through `uv run --project`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `gitutil.GitError` instead of raising `SemrailError` from `gitutil` | keep `GitError` · new `errors.py` | as recommended | It avoids a circular import without adding a file. `main` reports it exactly like a `SemrailError` with code 2, so the contract in `docs/design.md` is unchanged. |

Flags after a subcommand and `_root()` have no CLI-level test yet, because no command exists. The first lane that adds a command (T002 `lint`) covers `--json` after the subcommand.

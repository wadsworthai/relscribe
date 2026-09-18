# T003 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: `docs/features/T003-discover-units-and-read-and-write-their.md` at 638c79d, the diff `origin/T001-scaffold-the-package-cli-skeleton-and-te..638c79d` (artifact and index only), `taskrail checks T003 --stage plan` (no checks at this stage; passed). The 14 criteria cover the task row and `docs/design.md` Units, including the monorepo shapes semrail must support (pnpm/npm/uv workspaces, scoped names, and mirrors in `pyproject.toml`, `uv.lock`, `app.json` and a dotenv line).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How `units.py` raises errors | `ConfigError` in `units.py`, wired into `main` by T004 · import `SemrailError` inside a function · new `errors.py` | as recommended | Same pattern as `gitutil.GitError`; no cyclic import, and no edit to `cli.py`, which T002 is changing. T004 adds the `except` and tests AC 14. |
| 2 | Per-unit keys replace or merge the global value | replace · merge `bump` | as recommended | KISS: one rule for every key. |
| 3 | Workspace members without a version | skip · error | as recommended | A package with no version is not a unit under `docs/design.md` ("a directory with its own version"); tooling packages are common in workspaces. |
| 4 | Where a `sync` `file` is resolved | unit directory · repository root | as recommended | Every mirror in the known shapes sits in the unit's own directory. |
| 5 | `sync` errors (missing file, no match, a match that is not the current version) exit 2 before anything is written | strict · overwrite mismatches | as recommended | A wrong pattern must fail loudly, never write a partial release. |
| 6 | Add bullets for 2–5 to `docs/design.md` Units | yes · artifact only | as recommended | Docs change with the behaviour. Edit only the **Units** section; T002 owns Versioning and Commit parsing. |

Implement test-first: record each new test failing before the code exists, as the feature executor requires.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which part of `docs/design.md` | split by section · one owner | **split by section: T002 edits Versioning and Commit parsing; T003 edits Units** | The sections don't overlap, so the parallel edits merge cleanly. |
| 2 | `docs/features/README.md` rows | keep all | **keep all, one row per task** | This is known conflict class 2. |

## implement gate

Reviewed: the diff `ce6e880..339fb09`, with `units.py` read in full for `discover`, `write_version`, the pnpm parser and member globbing, plus `tests/test_units.py` and the Units bullets in `docs/design.md`. The test-first evidence is 48 failures against a `NotImplementedError` stub. The fixture fix (a TOML literal string for `\S`) left the assertions unchanged. `taskrail checks T003` re-run: passed. No sibling tool is named in src, tests or design.md.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Implementation choices within the plan: `ValueError` for a non-plain new version, `ConfigError` when the manifest changed since `discover`, sequential sync edits on the same file, `Unit.bump` as overrides only | accept · change | **accept** | Each follows the approved plan. `ValueError` marks a caller bug, not configuration. |

Carried to T004: wire `units.ConfigError` into `main` (exit 2) and test AC 14. Merge `Unit.bump` over `commits.DEFAULT_BUMPS`. Convert `ValueError` from `commits`/`units` into exit 2, never a traceback.

## rebase after T001

T001 was squash-merged into main as df184de, after an earlier plain merge (a8dfa74) was removed from main at the human's request. The branch was rebased onto origin/main (df184de) with `git rebase --onto`. There were no conflicts.

After the rebase: `git diff --check` reports no conflict markers, `taskrail checks` passed, and `taskrail validate` reports 0 errors and 0 warnings.

## rebase after T002

T002 was squash-merged into main as 426f3ca. The branch was rebased onto origin/main (426f3ca).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md` | keep both · stop | **keep both** | Known class 2: appended index rows. |
| 2 | Conflict in `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Known class 2: appended index rows. |
| 3 | Conflict in `TODO.md` (T002 and T003 rows) | ✅ wins · stop | **✅ on both rows** | Known class 1. No `Reopens:` commit on either side. |

`docs/design.md` merged without a conflict: T002's Versioning and Commit parsing edits and T003's Units edits are both present. After the rebase: `git diff --check` reports no conflict markers, `taskrail checks T003` passed (126 tests), and `taskrail validate` reports 0 errors and 0 warnings.

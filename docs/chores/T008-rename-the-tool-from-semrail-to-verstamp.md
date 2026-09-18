# T008 — Rename the tool from semrail to verstamp

## Goal

Rename the tool from `semrail` to `verstamp` before its first release: the Python package, the console script, the CLI's program name and error prefix, the configuration file (`verstamp.toml`), the tests, the product docs, the README, the agent files and the open backlog entries. Records of finished tasks stay as they were written.

Before the change, `git grep -n -i semrail` finds 247 matching lines in 37 files. They fall into the groups below. Every match outside the records listed under "Kept unchanged" is renamed.

## Change set

Every rename maps `semrail` to `verstamp` and `Semrail` to `Verstamp`.

### Package and build

- `src/semrail/` → `src/verstamp/` with `git mv`. The files are `__init__.py`, `changelog.py`, `cli.py`, `commits.py`, `gitutil.py`, `history.py`, `tags.py` and `units.py`.
- Every `from semrail…` or `import semrail…` becomes `verstamp` in `changelog.py`, `cli.py`, `commits.py`, `history.py` and `tags.py`.
- `__init__.py` docstring: `"""verstamp: SemVer versions and changelogs from Conventional Commits."""`.
- `cli.py`:
  - `prog="semrail"` becomes `prog="verstamp"`.
  - `version("semrail")` becomes `version("verstamp")`.
  - The `semrail: ` stderr prefix becomes `verstamp: ` in three places, including `semrail: error: a command is required`.
  - The class `SemrailError` becomes `VerstampError`, and so do its docstring and every use (seven raises and one `except`).
- `units.py`: `CONFIG = "semrail.toml"` becomes `"verstamp.toml"`, and the module docstring, the `discover` docstring and the `# semrail.toml` section comment follow. Error messages that name the config file use `CONFIG`, so they change with it.
- `history.py`: `SHALLOW_WARNING` does not name the tool, so it is left alone. Only the imports change.
- `tags.py`: the annotated tag message is `"{name} {version}"`, which does not name the tool. Only the imports change.
- `pyproject.toml`: `name = "verstamp"` and `[project.scripts] verstamp = "verstamp.cli:main"`. The description does not name the tool and stays as it is.
- `uv.lock`: regenerated with `uv lock`. Only the project's own entry, `name = "semrail"`, changes.

### Tests

- Imports in `tests/conftest.py`, `test_changelog.py`, `test_commits.py`, `test_gitutil.py`, `test_release.py` and `test_units.py`.
- Expected stderr prefixes (`semrail: `, `semrail: error:`) and `version("semrail")` in `test_cli.py`, `test_lint.py`, `test_release.py`, `test_status.py` and `test_tag.py`.
- Every `"semrail.toml"` fixture key and expected message becomes `"verstamp.toml"` in `test_release.py`, `test_status.py`, `test_tag.py` and `test_units.py`. This includes `test_defaults_without_semrail_toml` and `test_invalid_semrail_toml_is_an_error`, which are renamed to match.
- Module docstrings and comments that name the tool or its config file.
- `test_units.py:128-129`: the sample package name `pyproject("semrail", …)` becomes `"verstamp"`.

### Product docs

- `README.md`:
  - the title `# verstamp` and the opening sentence;
  - `uvx verstamp@X.Y.Z`, `uv tool install verstamp` and `uv run verstamp --root`;
  - the two TODO comments (`verstamp init`, `verstamp.toml`).
- `docs/design.md`, all 21 matches: prose, the `verstamp.toml` name, command names in the CLI table and the JSON sections, the error prefix `verstamp: `, the architecture tree `src/verstamp/`, and `uvx verstamp@X.Y.Z` in the distribution section.
- `docs/releasing.md`, all 4 matches: `uv run verstamp release …`, `verstamp tag`, and the tag message `"verstamp X.Y.Z"`.
- No change in `docs/development.md` or `LICENSE`, which do not name the tool.

### Agent files

- `CLAUDE.md` and `AGENTS.md` get the same three changes, so they stay identical below their headers, which `tests/test_docs.py` checks:
  - the Purpose sentence;
  - the Principles line, which becomes "verstamp is standalone. … verstamp must not depend on it … verstamp's code, tests and product docs …";
  - the `uv run verstamp --root` line under Commands.
- Current state does not name the tool, so it is not changed.

### Backlog (`TODO.md`)

- T007 title, via `taskrail edit T007 --title "Publish to PyPI and release 0.1.0 with verstamp itself"`. Its description does not name the tool. Its recorded branch name `T007-publish-to-pypi-and-release-0-1-0-with-s` stays as it is.
- Epic E01: the Epics-table name, the section heading `## E01 — semrail 0.1` and the "Done when" line all become `verstamp`. The objective does not name the tool. See decision 3 for how.

### Task record

- This file, and a row for it in `docs/chores/README.md`.

## Kept unchanged

These are historical records. They describe what was true when they were written.

- `docs/features/T002…T006-*.md`
- `docs/chores/T001-*.md`
- `docs/autopilot/decisions/*` (T001–T006)
- The descriptions of done tasks T002–T006 in `TODO.md`, which name `semrail lint`, `semrail.toml`, `semrail status`, `semrail release` and `semrail tag`. See decision 4.
- T008's own row, whose title names both tools, and this record and its index row in `docs/chores/README.md`.
- Git history.

`.taskrail/` (config, wrapper, `installed.json`) and `.claude/skills/` contain no match, so nothing changes there.

## Decisions needed

1. **Compatibility shim.** Should verstamp still read an old `semrail.toml`, or install a `semrail` script alias? Recommendation: no. Nothing was released, so no user has a `semrail.toml` or runs `semrail` (YAGNI). Alternatives: read `semrail.toml` as a fallback with a deprecation warning, or keep a second `[project.scripts]` entry `semrail`.
2. **PR title type.** Recommendation: `chore: rename the tool from semrail to verstamp`, not marked breaking. The kind's default type is `chore`. No version was ever released under the old name, so no consumer breaks. `chore` also keeps the rename out of the 0.1.0 changelog, where no reader would recognise the old name. Alternatives:
   - `refactor: …`, which also triggers no bump. It is less exact, because the command and the config file name change, and those are more than internal structure.
   - `chore!: …` / `BREAKING CHANGE`, which would bump a 0.x version for a break nobody sees.
3. **Epic E01 text.** `taskrail epic` has only `add` and `split`, and there is no command that edits an epic. Recommendation: hand-edit only the word `semrail` in three places, the E01 name cell, the `## E01 — semrail 0.1` heading and the "Done when" line, without touching table layout, IDs or statuses. Then run `taskrail validate`. Alternatives:
   - Leave E01 as "semrail 0.1", which would be a stale name for the epic that ships verstamp.
   - Rename only the name and heading, and leave "Done when".
4. **Done task rows T002–T006.** Recommendation: leave them as historical records, like their artifacts. `taskrail edit` refuses closed tasks unless given `--force`. Alternative: `taskrail edit --force --description …` on each of the five, so that the live backlog uses the new name.
5. **Test and function names that contain `semrail_toml`.** Recommendation: rename them to `verstamp_toml`, so that `git grep` is clean outside the records. Alternative: leave the test names as they are, since nobody sees them.

## Out of scope

- Renaming the GitHub repository, the local directory or the git remote. The human does this separately. No repository URL is added anywhere.
- Publishing to PyPI, CI, and the first release: T007.
- The auto-memory file outside the repository.
- The CLAUDE.md "Current state" text is stale. It lists only `lint` and `status`, although `release` and `tag` exist. That is not part of the rename, so it is only noted here.

## Verification

- `uv lock` rewrites only the project entry in `uv.lock`.
- `uv run verstamp --help` shows `usage: verstamp …`. `uv run verstamp --version` prints `0.0.0`. `uv run verstamp` exits 2 with `verstamp: error: a command is required`.
- `uv run verstamp --root <worktree> status` runs against this repository.
- A scratch repository has a `verstamp.toml` with an unknown key, and `status` there reports `verstamp: verstamp.toml: unknown key …`.
- `uv run semrail` no longer resolves.
- `git grep -n -i semrail` lists only the records under "Kept unchanged".
- `taskrail checks T008` passes the full test suite. The baseline before the change is 255 passed. `lint` is not configured.
- `taskrail validate` passes after the backlog edits.

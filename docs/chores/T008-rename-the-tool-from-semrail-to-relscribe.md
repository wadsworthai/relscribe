# T008 — Rename the tool from semrail to relscribe

## Goal

Rename the tool from `semrail` to `relscribe` before its first release: the Python package, the console script, the CLI's program name and error prefix, the configuration file (`relscribe.toml`), the tests, the product docs, the README, the agent files and the open backlog entries. Records of finished tasks stay as they were written.

Before the change, `git grep -n -i semrail` finds 247 matching lines in 37 files. They fall into the groups below. Every match outside the records listed under "Kept unchanged" is renamed.

## Change set

Every rename maps `semrail` to `relscribe` and `Semrail` to `Relscribe`.

### Package and build

- `src/semrail/` → `src/relscribe/` with `git mv`. The files are `__init__.py`, `changelog.py`, `cli.py`, `commits.py`, `gitutil.py`, `history.py`, `tags.py` and `units.py`.
- Every `from semrail…` or `import semrail…` becomes `relscribe` in `changelog.py`, `cli.py`, `commits.py`, `history.py` and `tags.py`.
- `__init__.py` docstring: `"""relscribe: SemVer versions and changelogs from Conventional Commits."""`.
- `cli.py`:
  - `prog="semrail"` becomes `prog="relscribe"`.
  - `version("semrail")` becomes `version("relscribe")`.
  - The `semrail: ` stderr prefix becomes `relscribe: ` in three places, including `semrail: error: a command is required`.
  - The class `SemrailError` becomes `RelscribeError`, and so do its docstring and every use (seven raises and one `except`).
- `units.py`: `CONFIG = "semrail.toml"` becomes `"relscribe.toml"`, and the module docstring, the `discover` docstring and the `# semrail.toml` section comment follow. Error messages that name the config file use `CONFIG`, so they change with it.
- `history.py`: `SHALLOW_WARNING` does not name the tool, so it is left alone. Only the imports change.
- `tags.py`: the annotated tag message is `"{name} {version}"`, which does not name the tool. Only the imports change.
- `pyproject.toml`: `name = "relscribe"` and `[project.scripts] relscribe = "relscribe.cli:main"`. The description does not name the tool and stays as it is.
- `uv.lock`: regenerated with `uv lock`. Only the project's own entry, `name = "semrail"`, changes.

### Tests

- Imports in `tests/conftest.py`, `test_changelog.py`, `test_commits.py`, `test_gitutil.py`, `test_release.py` and `test_units.py`.
- Expected stderr prefixes (`semrail: `, `semrail: error:`) and `version("semrail")` in `test_cli.py`, `test_lint.py`, `test_release.py`, `test_status.py` and `test_tag.py`.
- Every `"semrail.toml"` fixture key and expected message becomes `"relscribe.toml"` in `test_release.py`, `test_status.py`, `test_tag.py` and `test_units.py`. This includes `test_defaults_without_semrail_toml` and `test_invalid_semrail_toml_is_an_error`, which are renamed to match.
- Module docstrings and comments that name the tool or its config file.
- `test_units.py:128-129`: the sample package name `pyproject("semrail", …)` becomes `"relscribe"`.

### Product docs

- `README.md`:
  - the title `# relscribe` and the opening sentence;
  - `uvx relscribe@X.Y.Z`, `uv tool install relscribe` and `uv run relscribe --root`;
  - the two TODO comments (`relscribe init`, `relscribe.toml`).
- `docs/design.md`, all 21 matches: prose, the `relscribe.toml` name, command names in the CLI table and the JSON sections, the error prefix `relscribe: `, the architecture tree `src/relscribe/`, and `uvx relscribe@X.Y.Z` in the distribution section.
- `docs/releasing.md`, all 4 matches: `uv run relscribe release …`, `relscribe tag`, and the tag message `"relscribe X.Y.Z"`.
- No change in `docs/development.md` or `LICENSE`, which do not name the tool.

### Agent files

- `CLAUDE.md` and `AGENTS.md` get the same three changes, so they stay identical below their headers, which `tests/test_docs.py` checks:
  - the Purpose sentence;
  - the Principles line, which becomes "relscribe is standalone. … relscribe must not depend on it … relscribe's code, tests and product docs …";
  - the `uv run relscribe --root` line under Commands.
- Current state lists all four commands: `lint`, `status`, `release` and `tag` (decision 7).

### Backlog (`TODO.md`)

- T007 title, via `taskrail edit T007 --title "Publish to PyPI and release 0.1.0 with relscribe itself"`. Its description does not name the tool. Its recorded branch name `T007-publish-to-pypi-and-release-0-1-0-with-s` stays as it is.
- Epic E01: the Epics-table name, the section heading `## E01 — semrail 0.1` and the "Done when" line all become `relscribe`. The objective does not name the tool. They are hand-edited (decision 3).

### Task record

- This file, and a row for it in `docs/chores/README.md`.

## Kept unchanged

These are historical records. They describe what was true when they were written.

- `docs/features/T002…T006-*.md`
- `docs/chores/T001-*.md`
- `docs/autopilot/decisions/*` (T001–T006)
- The descriptions of done tasks T002–T006 in `TODO.md`, which name `semrail lint`, `semrail.toml`, `semrail status`, `semrail release` and `semrail tag` (decision 4).
- T008's own row, whose title names both tools, and this record and its index row in `docs/chores/README.md`.
- Git history.

`.taskrail/` (config, wrapper, `installed.json`) and `.claude/skills/` contain no match, so nothing changes there.

## Decisions

All approved; see `docs/autopilot/decisions/T008-rename-the-tool-from-semrail-to-verstamp.md`. The scope was first written for the name `verstamp`. The human then chose `relscribe`, because `verstamp` is taken on crates.io and as a GitHub user.

1. **Compatibility shim:** none. Nothing was released, so no user has a `semrail.toml` or runs `semrail` (YAGNI).
2. **PR title type:** `chore`, not breaking. No version was released under the old name, and `chore` keeps the rename out of the 0.1.0 changelog.
3. **Epic E01 text:** `taskrail epic` cannot edit an epic, so the word is hand-edited in three places: the name cell, the heading and the "Done when" line. `taskrail validate` runs afterwards.
4. **Done task rows T002–T006:** left as historical records.
5. **Test names containing `semrail_toml`:** renamed to `relscribe_toml`.
6. **This record:** renamed to match the new branch name.
7. **Current state:** CLAUDE.md and AGENTS.md now list all four commands.

## Out of scope

- Renaming the GitHub repository, the local directory or the git remote. The human does this separately. No repository URL is added anywhere.
- Publishing to PyPI, CI, and the first release: T007.
- The auto-memory file outside the repository.

## Verification

- `uv lock` rewrites only the project entry in `uv.lock`.
- `uv run relscribe --help` shows `usage: relscribe …`. `uv run relscribe --version` prints `0.0.0`. `uv run relscribe` exits 2 with `relscribe: error: a command is required`.
- `uv run relscribe --root <worktree> status` runs against this repository.
- A scratch repository has a `relscribe.toml` with an unknown key, and `status` there reports `relscribe: relscribe.toml: unknown key …`.
- `uv run semrail` no longer resolves.
- `git grep -n -i semrail` lists only the records under "Kept unchanged".
- `taskrail checks T008` passes the full test suite. The baseline before the change is 255 passed. `lint` is not configured.
- `taskrail validate` passes after the backlog edits.

### Results (implement stage)

- `uv lock`: `Added relscribe v0.0.0`, `Removed semrail v0.0.0`. The only change in `uv.lock` is the `name` line.
- `uv run relscribe --help` prints `usage: relscribe [-h] [--version] [--json] [--root ROOT] <command> ...` and lists `lint`, `status`, `release` and `tag`.
- `uv run relscribe --version` prints `0.0.0`.
- `uv run relscribe` prints the usage and `relscribe: error: a command is required`, and exits 2.
- `uv run relscribe --root <worktree> status` prints `relscribe (.): 0.0.0 -> 0.1.0 (minor)`, base whole history, and lists the branch's commits.
- A scratch repository has `package.json` 1.0.0 and a `relscribe.toml` containing `bogus = 1`. There, `status` prints `relscribe: relscribe.toml: unknown key `bogus`` and exits 2. With only an invalid `semrail.toml` left, `status` prints `app (.): 1.0.0, no release`, so the old file is ignored and no shim exists.
- `uv run semrail --help` fails with `error: Failed to spawn: `semrail`` and exit 2. The existing `.venv` needed `uv sync` first: `uv run` had left the old editable `semrail` script in place, and `uv sync` uninstalled it.
- `git grep -c -i semrail` matches only in these files:
  - `TODO.md`: the T002–T006 descriptions and T008's title;
  - `docs/autopilot/decisions/*`;
  - `docs/chores/T001-*`;
  - `docs/chores/README.md`: the T008 row;
  - this record;
  - `docs/features/T002…T006-*`.
- `taskrail validate`: `8 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
- `taskrail checks T008 --stage implement`: `test` (`uv run pytest`) passed, 255 tests, the same as the baseline. `lint` is not configured.

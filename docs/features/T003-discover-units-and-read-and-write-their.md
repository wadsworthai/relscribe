# T003 — Discover units and read and write their versions

Governing spec: `docs/design.md`, sections Units and Architecture.

## Behaviour

A new module `src/semrail/units.py` lets later commands (`status`, `release`, `tag`) ask "which units does this repository have, what are their versions and settings" and "write this unit's new version". It adds no CLI command.

- `discover(root) -> list[Unit]` finds the units, reads each one's version and name, and resolves its `semrail.toml` settings. Units are sorted by path.
- `Unit` is a frozen dataclass: `path` (POSIX, relative to the root, `"."` for the root), `name`, `dir`, `manifest` (`"package.json"` or `"pyproject.toml"`), `version`, and the resolved settings `tag`, `changelog`, `exclude`, `sync`, `bump`. `unit.tag_name(version)` renders the `tag` template with `{name}`, `{dir}` and `{version}`.
- `write_version(root, unit, new) -> list[str]` checks the manifest and every `sync` entry first, then replaces only the version text in each file, and returns the files it changed (root-relative paths). Formatting, key order, comments, quoting and line endings are preserved byte for byte outside the replaced value.
- Every configuration problem raises `ConfigError` (see question 1), which the CLI reports as exit code 2.

### Discovery

The first source that exists wins, in the order `docs/design.md` lists:
1. `pnpm-workspace.yaml` with a `packages` list; members' manifest is `package.json`. A file without a `packages` key (settings only) is not a workspace and discovery moves on.
2. The `workspaces` array of the root `package.json`; manifest `package.json`.
3. `[tool.uv.workspace].members` in the root `pyproject.toml`, minus its `exclude` globs; manifest `pyproject.toml`.
4. Otherwise the root is the single unit. Its manifest is `package.json` if that declares a `version`, else `pyproject.toml` `[project].version`; neither is a configuration error.

Member patterns are directory globs relative to the root (`apps/*`, `packages/**`, `./tools/cli/`). A leading `!` excludes (pnpm). Paths under `node_modules` never match. A matched directory without the manifest, or whose manifest has no static `version`, is not a unit and is skipped (question 3).

The minimal `pnpm-workspace.yaml` parser reads only the top-level `packages:` block list (`- item`, bare or quoted, with comments). A flow list (`packages: [a, b]`) is a configuration error rather than a silent misreading.

### Versions and names

- The version comes from `package.json` `version` or `pyproject.toml` `[project].version`, and must be plain `X.Y.Z` (no leading zeros, no pre-release or build metadata), else configuration error.
- `name` is the manifest's `name` (`[project].name` for Python). A unit with a version but no name is a configuration error. Scoped names such as `@scope/api` are kept as they are.
- `dir` is the base name of the unit directory; for the root unit, the base name of the repository root.

### `semrail.toml`

Read with `tomllib`. Top-level keys: `tag`, `changelog`, `exclude`, `sync`, `bump`, `units`. Each `[units."<path>"]` table accepts the same keys except `units`. Validation, all exit 2:
- an unknown key, or a value of the wrong type (`tag` string, `changelog` bool, `exclude` list of strings, `sync` list of `{ file, pattern }` tables of strings, `bump` table of `"major"`/`"minor"`/`"patch"`);
- a `tag` template with a placeholder other than `{name}`, `{dir}`, `{version}`;
- a `sync` pattern that does not compile or does not have exactly one capture group;
- a `[units."<path>"]` that names no discovered unit (catches typos and stale paths).

A per-unit key replaces the global value, for every key (question 2). `bump` is exposed as the configured overrides only (`{}` by default); combining it with the built-in type→bump map is T002/T004's job. `exclude` is exposed only; applying it is T004.

### Writing versions and the `sync` rule

- `package.json`: the value of the top-level `"version"` key only, found by a small scanner that tracks nesting and strings, so a nested `"version"` (for example inside another object) is never touched.
- `pyproject.toml`: the `version = "…"` line inside the `[project]` table (single or double quotes).
- After writing, the manifest is parsed again and must report the new version; this guards the targeted replacement.
- `sync` entries: `file` is relative to the unit directory (question 4). The pattern is applied with `re.MULTILINE`. Proposed rule (question 5), checked for every entry before any file is written, each failure a configuration error naming the unit, file and pattern:
  1. the file is missing;
  2. the pattern matches nothing;
  3. any match's group differs from the unit's current version.
  Otherwise every match's group is replaced with the new version.

Shapes the tests cover (generic names): a pnpm monorepo `apps/*`, `packages/*` with scoped names; a unit mirroring its version in `pyproject.toml` and in its entry in a `uv.lock` (multi-line pattern `name = "api"\nversion = "(…)"`); a unit mirroring it in `app.json` (nested `"expo": {"version": …}` and top-level `"version"`) and in a dotenv line `EXPO_PUBLIC_APP_VERSION=0.34.0`; an npm `workspaces` repo; a uv workspace; a single-package Python repo.

## Acceptance criteria

1. A pnpm workspace with `packages: ['apps/*', "packages/*", '!packages/internal']` (plus comments) yields exactly the matching directories that have a versioned `package.json`, sorted by path, with name, `dir`, manifest and version; the excluded one, one without `package.json`, one without `version` and anything under `node_modules` are absent.
2. A `pnpm-workspace.yaml` without `packages` falls through to the next source; one with a flow list is a `ConfigError`.
3. The root `package.json` `workspaces` array is used when there is no pnpm workspace.
4. `[tool.uv.workspace]` `members`/`exclude` is used when neither JavaScript source exists; members read `[project].version`.
5. Without a workspace the root is the single unit (`path == "."`), from `package.json` if it has a version, else `pyproject.toml`; neither is a `ConfigError`. A repository shaped like this one (`pyproject.toml` only) works.
6. A version that is not plain `X.Y.Z`, invalid JSON/TOML in a manifest, and a version without a name each raise `ConfigError`.
7. Without `semrail.toml`, every unit has the defaults: `tag == "{name}@{version}"`, `changelog is True`, `exclude == ()`, `sync == ()`, `bump == {}`; `tag_name("1.2.3")` for `@scope/api` gives `@scope/api@1.2.3`, and `"v{version}"`/`"{dir}-v{version}"` render too.
8. Global keys apply to every unit; a `[units."<path>"]` key replaces the global one for that unit only.
9. Each validation failure listed under `semrail.toml` raises `ConfigError` with a message naming the key or path.
10. `write_version` on a `package.json` changes only the top-level version's characters (the rest of the file is byte-identical, including indentation, key order, a nested `"version"` and CRLF line endings), and returns the changed files.
11. `write_version` on a `pyproject.toml` changes only `[project].version`, leaving comments, other tables' `version` keys and quoting intact.
12. `sync` entries for `pyproject.toml`, a `uv.lock` entry, `app.json` (nested and top-level) and a dotenv line are all rewritten to the new version; the other lines are untouched.
13. A `sync` entry whose file is missing, whose pattern matches nothing, or which matches a different version than the unit's raises `ConfigError`, and no file at all has been written.
14. `ConfigError` reaches the user as `semrail: <message>` with exit code 2 (tested once the wiring exists; see question 1).

## Affected areas

- `src/semrail/units.py` (new): everything above. One module; no split is justified yet.
- `tests/test_units.py` (new): the module is tested directly, as there is no command yet (`docs/development.md` prefers CLI-level tests; `status` in T004 moves coverage there).
- `docs/features/README.md` (new index) and this file.
- `docs/design.md`: only if question 6 is approved.

Not touched: `cli.py`, `conftest.py`, `gitutil.py` (no git is needed to discover units or write files; the `repo` fixture is used only for its `write` helper and a real root).

## Out of scope

- Any CLI command, including `status` (T004), and wiring `ConfigError` into `main` (question 1).
- Applying `exclude` to commits (T004), the default type→bump map and merging `bump` into it (T002/T004), rendering changelogs (T005), creating tags (T006).
- The object form of `workspaces` (`{"packages": [...]}`), YAML flow lists and anchors, and `dynamic` versions in `pyproject.toml`: no current need (YAGNI). The first two fail loudly rather than misread.
- Updating a unit's own `uv.lock` automatically: it is covered by a `sync` entry, like any other mirror.

## Open questions and risks

1. **How `units.py` raises errors.** `cli.py` will import `units.py` (T004), so `units.py` cannot import `SemrailError` from `cli` at module level. Recommend `class ConfigError(Exception)` in `units.py`, the pattern T001 set with `gitutil.GitError`, and T004 (which edits `cli.py` for `status` anyway) adds it to `main`'s `except` clause with exit 2. Alternatives: (a) raise `SemrailError` through an import inside a helper function (works today, no `cli.py` edit, but hides a cyclic dependency); (b) move `SemrailError` to a new `errors.py` (cleanest, but edits T001's `cli.py` and collides with T002).
2. **Per-unit override semantics.** Recommend: a per-unit key replaces the global value for every key, including `bump` and the lists. Alternative: merge `bump` entry by entry (and maybe concatenate `exclude`/`sync`), which is more convenient but is a second rule to document.
3. **Workspace members without a version.** Recommend skipping them: tooling or config packages without a version are common in workspaces and are not "a directory with its own version". Alternative: a configuration error, which would force every monorepo to list such packages as excluded.
4. **Where a `sync` `file` is resolved.** `docs/design.md` does not say. Recommend relative to the unit directory, so a per-unit entry reads `file = "app.json"` and a global entry applies to each unit's own copy. Alternative: relative to the repository root.
5. **The `sync` error rule** as proposed above (missing file, no match, or any match ≠ current version → exit 2, checked before writing anything; every match is replaced). Alternative: allow a mismatch and overwrite it (self-healing drift, but silently hides a wrong pattern).
6. **`docs/design.md` clarifications.** Recommend adding one short bullet each to Units for questions 2–5 in this task's implement stage, since docs change with the behaviour. Alternative: record them only in this artifact.
- **Risk:** discovery globs use `pathlib` semantics, which differ from pnpm's in corner cases (brace expansion, extglobs). The common forms (`dir/*`, `dir/**`, `!dir/x`) are tested.

## Decisions

Plan approved with every question as recommended; see `docs/autopilot/decisions/T003-discover-units-and-read-and-write-their.md`. The rules for questions 2–5 are now in `docs/design.md`, Units.

## Implementation

- `src/semrail/units.py` and `tests/test_units.py`, written test-first: the tests ran against a stub whose functions raised `NotImplementedError`, and all 48 failed before the code existed.
- `write_version` raises `ValueError` (a caller bug, not configuration) for a new version that is not plain `X.Y.Z`. If a manifest's version changed on disk since `discover`, it raises `ConfigError` instead of overwriting.
- Two `sync` entries on the same file, or one on the manifest, edit the pending text in turn, so none overwrites another.
- With `re.MULTILINE`, `^(.*)$` also matches the empty string after a file's final newline, and the strict rule rejects that. Tests use `^(\S+)$` for a file holding only the version.

## Acceptance criteria → tests (`tests/test_units.py`)

| AC | Tests |
|---|---|
| 1 | `test_pnpm_workspace_discovers_versioned_members` |
| 2 | `test_pnpm_workspace_without_packages_falls_through`, `test_pnpm_workspace_flow_list_is_an_error` |
| 3 | `test_package_json_workspaces` |
| 4 | `test_uv_workspace` |
| 5 | `test_single_python_package`, `test_single_root_prefers_versioned_package_json`, `test_single_root_falls_back_to_pyproject`, `test_single_root_without_a_version_is_an_error` |
| 6 | `test_invalid_manifests_are_errors` (7 cases) |
| 7 | `test_defaults_without_semrail_toml`, `test_tag_templates` (3 cases) |
| 8 | `test_global_keys_and_per_unit_overrides` |
| 9 | `test_invalid_semrail_toml_is_an_error` (18 cases) |
| 10 | `test_write_package_json_changes_only_the_top_level_version` |
| 11 | `test_write_pyproject_changes_only_the_project_version` |
| 12 | `test_write_rewrites_sync_files` (nested and top-level `app.json`), `test_global_sync_is_resolved_in_each_unit_directory` |
| 13 | `test_sync_problems_are_errors_and_nothing_is_written` (4 cases) |
| 14 | Deferred to T004, which wires `ConfigError` into `main` (plan decision 1) |

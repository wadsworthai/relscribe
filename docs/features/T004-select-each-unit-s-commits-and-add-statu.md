# T004 — Select each unit's commits and add status

Governing spec: `docs/design.md`, sections Selecting a unit's commits, Versioning, Commit parsing and CLI (`status`).

## Behaviour

`semrail status` reports, for every unit that `units.discover` finds: its current version, the base the commits are counted from, the commits that count, the resulting bump and next version, and warnings. It never writes anything and exits 0 unless there is a configuration or git error (exit 2).

A new module `src/semrail/history.py` does the selection, so `release` (T005) and `tag` (T006) can reuse it:
- `base(root, unit) -> Base` resolves the base.
- `select(root, unit, units, base) -> list[LogEntry]` lists the unit's commits, newest first.
- `status(root, units) -> list[UnitStatus]` combines both with `commits.parse`, `commits.bump` and `commits.next_version`. `UnitStatus` holds `unit`, `base`, `commits` (each `LogEntry` with its parsed `Commit` or `None`), `bump`, `next` and `warnings`.

### Base resolution (in order)

1. **Tag.** `unit.tag_name(unit.version)` exists as a tag (`git rev-parse -q --verify refs/tags/<tag>^{commit}`). Base = the commit it points to.
2. **Version change.** The newest commit reachable from `HEAD` whose manifest version differs from its parent's. Found cheaply and correctly in two steps:
   - candidates: `git log --format=%H -Gversion HEAD -- <unit>/<manifest>`, the commits whose manifest diff adds or removes a line containing `version`. Merge commits have no diff here, so they are never candidates;
   - check, newest first: read the version at the candidate and at its parent (`git show <sha>:./<path>` and `<sha>^:./<path>`, parsed as the manifest's JSON or TOML), and stop at the first candidate where both have a version and they differ. A `"version"` key in a nested object, a comment or a dependency line never passes this check.
   - A commit that *introduces* the version (the manifest is added, the parent is the root, or the parent had no version or an unreadable manifest) is not a change (question 3). A unit whose version was set in its very first commit and never changed is therefore never released, and falls to rule 3.
3. **Whole history.** No base: all of `HEAD`'s history for the unit.

### Selection

`git log <base>..HEAD --no-merges -- <unit path> <exclusions>` (or `HEAD` alone without a base), where the exclusions are git pathspecs:
- `:(exclude,glob)<unit path>/<pattern>` for each `exclude` glob. git drops a commit whose files inside the unit all match, and keeps one that also touches another file of the unit, which is exactly the rule in `docs/design.md`. Globs are relative to the unit directory, in git's glob syntax: `*` stays inside one directory, `**/` matches any number of them (including none), `/**` everything inside (question 5). Checked in a scratch repository: with `tests/**` excluded, a tests-only commit disappears and a commit touching `src/` and `tests/` stays; `**/*.md` excludes Markdown at any depth.
- `:(exclude)<nested unit path>` for every other unit inside this unit's directory, so one commit never counts for both a unit and the unit containing it (question 4).

A commit touching only files outside every unit matches no unit's pathspec, so it bumps nothing. `--no-merges` skips true merge commits from syncing another branch; the commits they bring in are counted on their own.

### Bump and warnings

- The bump map is `{**commits.DEFAULT_BUMPS, **unit.bump}`: configured entries add types or replace a default's level (question 2).
- Unparseable subjects contribute nothing and each adds a warning `<short sha>: not a Conventional Commit: <subject>`. Older history full of non-conventional subjects therefore yields warnings, never an error.
- In a shallow clone, a unit whose base is not a tag gets the warning `shallow clone: history may be incomplete; fetch full history and tags` (question 6).

### Output

Text, one block per unit, newest commit first:

```
@scope/api (apps/api): 0.34.0 -> 0.35.0 (minor)
  base: tag @scope/api@0.34.0 (1a2b3c4)
  9f8e7d6 feat(0037:api:session): add x (#82)
  5c4b3a2 docs: y
  warning: 0a1b2c3: not a Conventional Commit: wip
@scope/web (apps/web): 1.2.0, no release
  base: version change (4d5e6f7)
```

`--json` (question 1), the contract CI reads, e.g. to find which units a release touches (`next != null`):

```json
{
  "units": [
    {
      "path": "apps/api",
      "name": "@scope/api",
      "version": "0.34.0",
      "base": {"kind": "tag", "sha": "<40 hex>", "tag": "@scope/api@0.34.0"},
      "commits": [
        {"sha": "<40 hex>", "subject": "feat(0037:api:session): add x (#82)", "type": "feat", "scope": "0037:api:session", "breaking": false},
        {"sha": "<40 hex>", "subject": "wip", "type": null, "scope": null, "breaking": false}
      ],
      "bump": "minor",
      "next": "0.35.0",
      "warnings": ["0a1b2c3: not a Conventional Commit: wip"]
    }
  ]
}
```

- `base.kind` is `"tag"`, `"version-change"` or `"history"`; `base.sha` is `null` only for `"history"`, `base.tag` is set only for `"tag"`.
- `commits` lists every selected commit, including those whose type bumps nothing and the unparseable ones (`type: null`). `bump` and `next` are `null` when nothing bumps.
- Units are in `discover` order (sorted by path).

### Errors

- `units.ConfigError` is wired into `cli.main`: `semrail: <message>`, exit 2 (T003 AC 14).
- `ValueError` from `commits.bump`/`next_version` and `units.write_version` (question 7): no user input reaches them. A manifest version that is not plain `X.Y.Z` and a `bump` value other than `major`/`minor`/`patch` are already `ConfigError`s at discovery, and `write_version` is not called by `status`. The tests prove both user paths end as exit 2 without a traceback.
- `status` in a repository without commits, or outside a git repository, is a git error: exit 2.

## Acceptance criteria

All through the CLI against real temporary repositories (`tests/test_status.py`), asserting on exit codes and `--json`.

1. A single-unit repository whose current version has a tag uses it as the base (`kind: "tag"`, the tag's commit and name); only commits after the tag are listed, newest first.
2. Without that tag, the base is the newest commit that changed the manifest's version (`kind: "version-change"`), even when a later commit edits other manifest lines (a dependency or a nested `"version"` key), and for both `package.json` and `pyproject.toml`.
3. A unit whose version was set in its first commit and never changed, and a unit with no tag and no version change, use the whole history (`kind: "history"`, `sha: null`), and that first commit is listed.
4. In a workspace with two units, a commit touching only unit A is listed for A and not B; a commit touching both is listed for both; a commit touching only files outside every unit is listed for none.
5. With `exclude = ["tests/**"]`, a commit touching only the unit's tests is dropped, and one touching tests and source is kept.
6. A unit nested inside another unit's directory: its commits are not listed for the outer unit.
7. A true merge commit is never listed; the commits it brings in are.
8. `bump`/`next` follow `docs/design.md` Versioning: `feat` → minor, `fix` → patch, a breaking change → major at ≥ 1.0.0 and minor at 0.y.z; only `docs`/`chore` → `bump: null`, `next: null`. A squash-merged subject such as `feat(0037:api:session): add x (#82)` parses with its scope.
9. A `bump` override in `semrail.toml` adds a type (`docs = "patch"` bumps) and replaces a default (`feat = "patch"`), and the other defaults still apply.
10. An unparseable subject is listed with `type: null`, adds a warning with its short SHA, contributes nothing, and the exit code stays 0.
11. The text output shows each unit's name, path, version, next version or "no release", base, commits and warnings.
12. An invalid `semrail.toml` and a manifest with a non-plain version each give `semrail: <message>` on stderr, exit 2, no traceback.
13. `status` in a repository without commits gives exit 2 with a `semrail: ` message.
14. In a shallow clone (`git clone --depth`), a unit without a tag base carries the shallow-clone warning (only if question 6 is approved).

## Affected areas

- `src/semrail/history.py` (new): `Base`, `UnitStatus`, `base`, `select`, `status`.
- `src/semrail/commits.py`: `log(root, rev_range, paths=())` gains an optional pathspec list, appended after `--`. `lint --range` is unchanged.
- `src/semrail/cli.py`: the `status` subparser and `cmd_status`, and `except units.ConfigError` in `main`.
- `src/semrail/gitutil.py`, `units.py`: unchanged. Missing tags and missing files at a commit are `GitError`s that `history.py` catches locally.
- `tests/test_status.py` (new). No module test file: every rule is reachable through the CLI.
- `docs/design.md`: the opening sentence, Selecting a unit's commits (the rules above, briefly), and CLI (the `status --json` shape); Versioning and Architecture only if questions 2 and 8 are approved.
- `docs/features/README.md` and this file.

## Out of scope

- A `--ref` or range option for `status`: the version is read from the working tree, so only `HEAD` is consistent with it (YAGNI).
- Following renamed or moved unit directories (`--follow` works on single files only).
- Disabling a default bump type (for example `refactor = "none"`): no current need (question 2).
- Release detection for tags (T006) and changelog rendering (T005). The version-change lookup stays private in `history.py` until T006 needs it.

## Open questions and risks

1. **The `status --json` shape** above. Recommend it as written. Alternatives: list only the commits that bump (loses `docs`/`chore` context and the unparseable ones), or add a per-commit `bump` level (redundant with `type` + `breaking` + the map).
2. **Combining `Unit.bump` with the defaults.** Recommend merging entry by entry over `DEFAULT_BUMPS` (add or replace), with no way to disable a default (YAGNI), and one sentence in `docs/design.md` Versioning saying so. Alternatives: a configured map replaces the defaults entirely (every override must repeat `feat`/`fix`/…); or also accept `"none"` to disable a type.
3. **Is introducing a version a "change"?** Recommend no: only a commit where the version differs from a parent that had one is a change, so a never-released unit uses its whole history and its first commit (for example `feat: scaffold the api`) counts. Alternative: the commit that adds the version is the base, which excludes that first commit and makes rule 3 unreachable in practice. T006's release detection should use the same rule.
4. **Nested units.** Recommend excluding the paths of units nested inside a unit from its selection (one pathspec each). Alternative: count such a commit for both units, as a literal reading of `-- <unit path>` would.
5. **`exclude` glob syntax.** Recommend git's `glob` pathspec magic, relative to the unit directory, so git applies the "all files match" rule itself in the same `git log` call. Alternative: Python `fnmatch` on each commit's file list (`*` crosses `/`, needs `--name-only` parsing).
6. **Shallow-clone warning.** CI checkouts are often shallow; then the tag or version change may be missing and `status` would silently count too much history. Recommend the per-unit warning above (one extra `git rev-parse --is-shallow-repository`). Alternative: leave it to the consumer's CI setup (document only).
7. **`ValueError`.** Recommend leaving `ValueError` uncaught in `main`, since after discovery's validation it can only mean a bug, and proving with tests that the user paths are exit 2. Alternative: also catch `ValueError` in `main` as exit 2, which hides bugs behind a one-line message.
8. **`docs/design.md` Architecture** lists the modules. Recommend adding `history.py  # base resolution and each unit's commits` there, outside this lane's allowed sections. Alternative: leave Architecture stale.
- **Risk:** a manifest with a `"version"` line that git's `-G` sees but whose value change sits on a line without the word `version` (a multi-line JSON value) is not a candidate. No real manifest writes the version that way.
- **Risk:** reading the version at every candidate costs two `git show` calls each. Candidates are the manifest's version-line edits, few in practice; measure before optimizing.

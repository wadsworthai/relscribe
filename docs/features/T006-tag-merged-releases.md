# T006 — Tag merged releases

Governing spec: `docs/design.md`, sections Releases and tags ("Release detection", "Tags") and CLI (`tag`, exit code 4).

## Behaviour

`semrail tag <from>..<to> [--push <remote>]` creates an annotated tag for every release in the range, plus each unit's most recent release before `<from>` when that one is untagged. CI runs it on every push to the release branch as `semrail tag <before>..<after> --push origin`, with the range taken from the push event.

### Release detection

A commit is a release for a unit when, compared with its parent, the unit's manifest version changed to a higher version (question 2). The commit message and manifest files outside the commit are never consulted.
- Introducing a version (the manifest is added, the parent has no version, or the commit is a root) is not a release, as for T004's base (question 3).
- Merge commits are never examined. The commit that changed the version on the merged branch is, and it is reachable from `<to>` (question 4).

### Units as of each release commit

Units, their names and their `tag` templates are read as of the release commit, not from the working tree, because CI may run at a later `HEAD` and a unit may have been added, renamed or reconfigured since (question 1). A new function in `tags.py` materializes a commit's discovery inputs into a temporary directory and calls `units.discover` on it:
- `git ls-tree -r -z --name-only <sha>` lists the files; only `package.json` and `pyproject.toml` (anywhere outside `node_modules/`) and the root `pnpm-workspace.yaml` and `semrail.toml` are written, with `git show <sha>:<path>`.
- The temporary root has the repository directory's base name, so a root unit's `{dir}` stays the same.
- `units.py` is unchanged: discovery already only reads these files and globs directories that contain them.

### Which commits are examined

1. **The range.** Candidates are `git log --format=%H --no-merges --reverse -Gversion <from>..<to> -- ':(glob)**/package.json' ':(glob)**/pyproject.toml'`: non-merge commits whose diff touches a line mentioning `version` in some manifest. For each candidate, the units as of that commit are discovered and each unit's version is compared with the version at `<sha>^` at the same path (`history.version_at`, promoted from `_version_at`).
2. **Reconcile** (question 5). For each unit discovered as of `<from>`, the newest release reachable from `<from>` is found with the same candidate-and-check walk as T004's `_last_version_change` (`git log --no-merges -Gversion <from> -- <unit manifest>`, stopping at the first release). If its tag does not exist, it is created. Only that one release per unit is examined, so a run skipped in CI and a unit released before semrail existed both get the tag of their latest release, and older untagged releases stay untagged.

Several units released in one commit get one tag each on that commit.

### Tags

- Name: the unit's `tag` template as of the release commit, with the new version.
- Annotated, message `<name> <version>` (question 6), created with `git tag -a -m <message> <tag> <sha>`. The tagger identity comes from git's configuration, so CI must set `user.name` and `user.email`.
- Exists and points (peeled) to the same commit: `existing`, nothing done. Exists on another commit: `conflict`, never moved. Otherwise `created`.
- A conflict does not stop the other tags: every non-conflicting tag is created (and pushed), all conflicts are reported, and the exit code is 4 (question 8).
- In a shallow clone the result carries the T004 shallow-clone warning, since releases and tags may be missing from the fetched history.

### `--push <remote>`

Pushes only the tags this run created, in one `git push --porcelain <remote> refs/tags/<t>…` (question 7). Tags the run found existing are assumed to be on the remote already: a CI checkout with full history fetches them. A tag the remote rejects (it already has that tag, pointing elsewhere) is a conflict: exit 4, listed under `push.rejected`. Any other push failure (network, authentication, unknown remote) is a git error: exit 2. Nothing is pushed when nothing was created.

### Output

Text, one line per tag, oldest release first (reconciled ones before the range), then a push line:

```
created @scope/api@0.35.0 9f8e7d6
existing @scope/web@1.3.0 4d5e6f7
conflict @scope/ui@2.0.2 1a2b3c4: already on 5c4b3a2
pushed 1 tag to origin
```

`--json` (question 9):

```json
{
  "tags": [
    {"tag": "@scope/api@0.35.0", "path": "apps/api", "name": "@scope/api", "version": "0.35.0",
     "sha": "<40 hex>", "result": "created", "existing_sha": null}
  ],
  "push": {"remote": "origin", "pushed": ["@scope/api@0.35.0"], "rejected": []},
  "warnings": []
}
```

- `result` is `"created"`, `"existing"` or `"conflict"`; `existing_sha` is the commit the tag already points to when `result` is `"conflict"`, else `null`.
- `push` is `null` without `--push`.

### Exit codes and errors

- 0: no conflict (including nothing to tag). 4: any conflict, in the repository or on push. 2: usage, configuration or git error.
- `<from>..<to>` must have both ends and two dots; `...` is a usage error. An unknown revision is a git error.
- A configuration error in a unit's files as of a release commit is exit 2, naming the commit.

## Acceptance criteria

All through the CLI against real temporary repositories (`tests/test_tag.py`), asserting on exit codes, `--json` and the created tags.

1. A squash-style commit on `main` that changes a unit's version from 1.0.0 to 1.1.0 gets an annotated tag `<name>@1.1.0` pointing at it, with message `<name> 1.1.0`; `result` is `created`, exit 0.
2. Commits in the range that do not raise a version (other manifest edits, a dependency line, a nested `"version"` key, source changes) get no tag.
3. A commit that introduces a unit (new manifest with a version) gets no tag; a later version change in that unit does.
4. A commit that lowers a version (a reverted release) gets no tag.
5. A workspace commit releasing two units creates one tag for each, on the same commit.
6. The `tag` template, unit name and unit set are read as of the release commit: a template changed in `semrail.toml` after the release, a unit renamed after the release, and a unit that no longer exists at `<to>` all still get the tag their release commit implies.
7. A release on a branch merged with a true merge commit is tagged on the branch commit, never on the merge commit.
8. Running the same range twice: the second run reports `existing` for every tag, creates nothing, exits 0.
9. A tag that already exists on another commit is `conflict` with `existing_sha`, is not moved, other tags in the run are still created, exit 4.
10. Reconcile: the newest release before `<from>` whose tag is missing is tagged, per unit (a skipped CI run, and a unit released before any tag existed); an older untagged release of the same unit is not; a tagged latest release gives `existing`.
11. `--push <remote>` against a local bare repository pushes exactly the created tags; the remote has them afterwards and not the ones that already existed. A remote that already has one of the tags on another commit gives `push.rejected` with that tag and exit 4. An unknown remote gives exit 2.
12. Usage errors (`<from>` without `..`, `...`, an empty end) and an unknown revision give `semrail: <message>` on stderr, exit 2.
13. The text output shows one line per tag with its result and short SHA, and the push line.
14. A shallow clone adds the shallow-clone warning.

## Affected areas

- `src/semrail/tags.py` (new): release detection, the as-of-commit unit snapshot, reconcile, tag creation and push.
- `src/semrail/history.py`: `_version_at` becomes public `version_at` (reused, not duplicated); its caller is updated. Nothing else changes.
- `src/semrail/cli.py`: the `tag` subparser and `cmd_tag`, one block after the `status` block.
- `tests/test_tag.py` (new).
- `docs/design.md`: the "Release detection" and "Tags" bullets and the `tag` row of the CLI table, plus the `tag --json` shape and `tags.py` in Architecture (question 10).
- `docs/features/README.md` (one row) and this file.

## Out of scope

- A zero or unreachable `<from>` (a push that creates the branch or a force push): git error, exit 2. CI can pass a valid range; handling it waits for a concrete need.
- Walking back past each unit's latest release to tag every old untagged release (YAGNI; the latest one is what `status` uses as its base).
- Checking the remote's tags before creating (`git ls-remote`): a full-history checkout already has them, and a push rejection still reports the conflict.
- Signing tags, custom tag messages, `--dry-run`.

## Open questions and risks

1. **Units as of the release commit.** Recommend materializing the commit's manifests, `pnpm-workspace.yaml` and `semrail.toml` into a temporary directory and running the unchanged `units.discover` on it. Alternatives: (a) discover once from the working tree and only read versions at each commit, which is wrong for units added, removed, renamed or re-templated since; (b) a full `git worktree add` or `git archive` per commit, correct but costly on large repositories; (c) teach `units.py` to read from a git tree, which touches every file read in discovery.
2. **"Changes the version" means "raises the version".** Recommend counting only a version higher than the parent's (compared as X.Y.Z; if the parent's version is not plain X.Y.Z, any change counts). A reverted release lowers the version back to one that is already tagged elsewhere; counting it would be a conflict on that push and, through reconcile, on every later push until the unit's next release. The "Release detection" bullet would say "raises". Alternative: follow the literal "changes" and let a revert surface as a conflict for a human.
3. **Is introducing a version a release?** Recommend no, matching T004. A unit moved to a new directory, or imported with an existing version, would otherwise look like a new release, producing a false tag or a conflict with the tag it already has. A new unit's first tag appears at its first release. Alternative: tag the introduction, which gives every new unit a tag at once but misfires on moves and imports.
4. **Which commits are examined.** Recommend non-merge commits only (`--no-merges`), the same rule as selection and T004's base. A release made on a branch and merged with a true merge commit is tagged on the branch commit, which is where the version changed; a squash merge is a single commit anyway. Alternatives: first-parent only (misses nothing on squash-only repositories, but would tag merge commits and needs merge-diff logic), or also merges whose first-parent diff changes a version (tags the same release twice, once as a conflict).
5. **Reconcile rule.** Recommend per unit: for each unit as of `<from>`, look only at its newest release reachable from `<from>`, and tag it if the tag is missing (a conflict there is reported like any other). Alternatives: globally, the single newest release commit before `<from>` (misses a unit released in a skipped run when another unit released later); or walk back through every untagged release (unbounded, and would tag years of pre-semrail releases).
6. **Tag message.** Recommend `<name> <version>`, e.g. `@scope/api 0.35.0`. Alternatives: the tag name itself; the release commit's subject (the spec says the message is never consulted for detection, and a squash subject can list several units).
7. **`--push`.** Recommend pushing only the tags created in this run, in one command, with rejected tags as exit 4 and other push failures as exit 2. Alternatives: also push tags found existing (covers a previous run whose push failed in the same checkout, which CI's fresh clones do not have); `--atomic` (one rejected tag would block the others, against question 8).
8. **Conflicts do not block other tags.** Recommend creating and pushing every non-conflicting tag and exiting 4 at the end, since units are released independently. Alternative: check everything first and create nothing if any conflict exists.
9. **The `--json` shape** above: one flat `tags` list with a `result` per tag, a `push` object or `null`, and `warnings`. Alternative: separate `created`/`existing`/`conflicts` lists (harder to keep per-tag detail consistent).
10. **`docs/design.md` beyond the touch map.** Recommend adding the `tag --json` shape under CLI (next to `status --json`) and `tags.py` to Architecture, as T004 did for `history.py`. Alternative: leave both undocumented.
- **Risk:** each candidate commit costs one `ls-tree` and one `git show` per manifest. Candidates are version-line edits, few in practice; measure before optimizing (e.g. `git cat-file --batch`).
- **Risk:** a `semrail.toml` that was valid under an older semrail but not now makes discovery at an old release commit fail (exit 2). Only reconcile reaches old commits, and only each unit's latest release.
- **Risk:** git needs a committer identity for annotated tags; without one, `git tag` fails and the run exits 2. `docs/design.md` will say so.

## Decisions

Plan approved with every question as recommended; see `docs/autopilot/decisions/T006-tag-merged-releases.md`. `docs/design.md` now states the rules in Releases and tags ("Release detection" says "raises", plus "Units as of the release", "Reconcile", "Tags" and "Push"), the `tag` row and the `tag --json` shape under CLI, and `tags.py` in Architecture.

## Implementation

- Test first: `tests/test_tag.py` ran before any code existed. `uv run pytest -q --tb=no` gave `39 failed, 172 passed`: every `tag` test failed with `invalid choice: 'tag' (choose from lint, status)`, except `test_range_is_required`, which already expected exit 2.
- `src/semrail/tags.py` (new): `run(root, from_rev, to_rev, remote)` returns an `Outcome` (`tags`, `push`, `warnings`, `conflict`).
  - The range's candidates come from one `git log --name-only --no-merges --reverse -Gversion <from>..<to> -- ':(glob)**/package.json' ':(glob)**/pyproject.toml'`. For a candidate, only units whose manifest the commit touched are compared with the parent.
  - Units at a commit are discovered from a temporary directory named like the repository, holding the commit's manifests (outside `node_modules/`) and its root `pnpm-workspace.yaml` and `semrail.toml`. Snapshots are cached by commit for the run. A commit from before any unit existed (`units.NoUnitError`, a `ConfigError` subclass that discovery raises when it finds no unit) has no units, so it has no releases. Any other configuration error there is exit 2, prefixed with the short SHA.
  - Versions are compared as X.Y.Z. If either version is not plain, any difference counts.
  - Tags are created in order and checked one at a time, so a second release of the same version in one run conflicts with the first.
- `src/semrail/history.py`: `_version_at` became public `version_at`. Nothing else changed.
- `src/semrail/gitutil.py`: `GitError` now keeps the failed command's stdout (`exc.stdout`), because `git push --porcelain` reports rejected refs on stdout while exiting 1. This is a small change outside the touch map, and `tags.py` needs it for the push.
- `src/semrail/units.py` (implement-gate decision 2): `class NoUnitError(ConfigError)`, raised where discovery finds no unit, so `tags.py` no longer matches the message text. Nothing else in `units.py` changed; `tests/test_units.py::test_no_unit_at_all_is_a_distinct_configuration_error` covers it. The CLI still reports it as exit 2.
- `src/semrail/cli.py`: the `tag` subparser, `cmd_tag`, `_tag_json` and `_tag_text`, in one block after `status`, plus the import. A range without `..`, with an empty end, with `...` or with more than one `..` is a usage error (exit 2).

## Acceptance criteria → tests (`tests/test_tag.py`)

| AC | Tests |
|---|---|
| 1 | `test_version_raise_is_tagged_with_an_annotated_tag`, `test_pyproject_release` |
| 2 | `test_commits_that_do_not_raise_a_version_are_not_tagged` (4 cases) |
| 3 | `test_introducing_a_unit_is_not_a_release`, `test_first_commit_in_range_introducing_the_root_unit_is_not_a_release` |
| 4 | `test_lowering_a_version_is_not_a_release` |
| 5 | `test_one_commit_releasing_two_units_gets_one_tag_each`, `test_releases_are_listed_oldest_first` |
| 6 | `test_tag_template_is_read_as_of_the_release_commit`, `test_unit_renamed_or_removed_after_the_release`, `test_dir_placeholder_uses_the_repository_directory_name`, `test_configuration_error_at_a_release_commit_names_the_commit` |
| 7 | `test_release_merged_with_a_true_merge_is_tagged_on_its_own_commit` |
| 8 | `test_second_run_reports_existing_tags` |
| 9 | `test_tag_on_another_commit_is_a_conflict_and_other_tags_are_still_created`, `test_same_tag_twice_in_one_range_conflicts_with_the_first` |
| 10 | `test_reconcile_tags_the_latest_untagged_release_before_the_range`, `test_reconcile_includes_the_from_commit`, `test_reconcile_reports_an_already_tagged_latest_release_as_existing`, `test_reconcile_is_per_unit`, `test_never_released_unit_has_nothing_to_reconcile`, `test_from_without_any_unit` |
| 11 | `test_push_sends_only_the_created_tags`, `test_push_with_nothing_created_pushes_nothing`, `test_push_rejected_by_the_remote_is_a_conflict`, `test_push_to_an_unknown_remote_is_a_git_error` (all against a local bare remote in `tmp_path`) |
| 12 | `test_bad_ranges_are_usage_errors` (5 cases), `test_unknown_revision_is_a_git_error`, `test_range_is_required` |
| 13 | `test_text_output`, `test_text_output_with_nothing_to_tag`, `test_text_output_for_a_rejected_push` |
| 14 | `test_shallow_clone_warns` |

## Verify

I verified the feature with a script under the session scratchpad (not committed). A developer clone pushed to a local bare `origin`. Each CI run was a fresh full clone of `origin` running `uv run semrail --root <clone> [--json] tag <before>..<after> --push origin`, with the range of the push. The repository was a pnpm workspace with `apps/api`, `apps/web` and `packages/core`. Its history started with non-conventional subjects and an untagged `Release core 1.0.0` (0.9.0 -> 1.0.0) from before semrail.

1. **Squash-merged release of two units.** Release commit `78521e8`: `created @scope/api@0.35.0` and `created @scope/web@1.3.0` on that commit. Reconcile also gave `created @scope/core@1.0.0` on the untagged release from before semrail (`3930cfb`). All three were pushed; exit 0.
2. **Re-run of the same push.** All three were `existing`, `pushed: []`; exit 0.
3. **Skipped CI run.** `web` was released in `3ad798e` with no CI run, then a docs-only push. The next run reconciled `created @scope/web@1.3.1` on `3ad798e`, and pushed it.
4. **True merge.** A `release/core` branch (`5754673`, core 1.0.0 -> 1.1.0) was merged with `--no-ff` as `c8acb56`. `@scope/core@1.1.0` was created on `5754673`, not on the merge. `apps/mobile`, introduced at 0.1.0 in the same push, got no tag.
5. **Conflict.** A hand-made `@scope/api@0.36.0` sat on `c8acb56`, and the release commit `ec357d3` released api 0.36.0 and core 1.1.1. Text output:
   ```
   existing @scope/api@0.35.0 78521e8
   existing @scope/web@1.3.1 3ad798e
   existing @scope/core@1.1.0 5754673
   conflict @scope/api@0.36.0 ec357d3: already on c8acb56
   created @scope/core@1.1.1 ec357d3
   pushed 1 tag to origin
   ```
   Exit 4. The hand-made tag was not moved.
6. **Remote rejection.** `@scope/web@1.4.0` landed on `origin` (on `ec357d3`) after the CI clone fetched. The run created it locally on `d932755` and reported `pushed 0 tags to origin` / `rejected by origin: @scope/web@1.4.0`; exit 4. The same run also repeated api's reconcile conflict from step 5, as planned (question 5): it stays until api's next release.
7. **Errors.**
   - `tag main`: `semrail: tag: the range must be <from>..<to>, got 'main'`, exit 2.
   - `nope..HEAD`: `semrail: git rev-parse --verify --end-of-options nope^{commit}: fatal: Needed a single revision`, exit 2.
   - `--push nowhere`: exit 4, not 2. That run created nothing, so nothing was pushed and the unknown remote was never contacted. The 4 came from api's reconcile conflict. This matches the plan ("Nothing is pushed when nothing was created").
- **Tags on `origin`.** Every tag semrail created is annotated, with the message `<name> <version>` (for example `@scope/core 1.0.0`).
- **Timing.** Each run took 0.18–0.33 s, including `uv` startup.

The behaviour matches the plan.

# T005 — Write changelogs and add release

Governing spec: `docs/design.md`, sections Changelog, Releases and tags ("Bump timing", "Release commit") and the `release` row of the CLI table. `docs/releasing.md` shows how this repository will use it.

## Behaviour

`semrail release [--commit] [--branch]` releases every unit whose `status` has a `next` version:
- it writes the next version into the manifest and `sync` files (`units.write_version`);
- it inserts a Keep a Changelog section into the unit's `CHANGELOG.md`, unless the unit sets `changelog = false`;
- with `--branch`, it creates and switches to `release/<YYYY-MM-DD>[-N]`;
- with `--commit`, it stages only the files it wrote and makes one release commit.

It never pushes and never tags. Without `--commit` it only edits the working tree (and creates the branch with `--branch`).

### Steps, in order

1. **Preflight.** Refuse with exit 2 when tracked files have uncommitted changes (`git status --porcelain --untracked-files=no` is not empty). Otherwise a second run would count the same commits again from the unchanged base and release twice (question 4). The current branch is not checked.
2. **Compute.** Call `history.status(root, units.discover(root))` and keep the units whose `next` is not `null`. If there are none, print `nothing to release` and exit 0. Nothing is written, no branch is created and no commit is made (question 3).
3. **Render.** For each released unit with `changelog = true`, read `<unit>/CHANGELOG.md` (or start from nothing), refuse with exit 2 if it already has a heading for the new version, and build the new text in memory.
4. **Write.** Record the original content (or absence) of every file the release can touch: each unit's manifest, its `sync` files and its `CHANGELOG.md`. Then run `write_version` and write the changelogs, unit by unit. If anything fails (for example unit B's `sync` pattern after unit A was written), restore every recorded file, delete the changelogs that were created, and exit 2. A release writes all of its files or none of them.
5. **Branch** (`--branch`). Run `git switch -c release/<date>`, which carries the written files over. When `release/<date>` already exists as a local branch or as a remote-tracking branch, try `release/<date>-2`, `-3`, and so on (question 5).
6. **Commit** (`--commit`). Run `git add -- <files written>` and then `git commit -m <subject>`. Hooks run as usual (no `--no-verify`).

### Changelog (`src/semrail/changelog.py`, pure text functions, no git)

- **Section:** `## [X.Y.Z] - YYYY-MM-DD`, then the non-empty groups in Keep a Changelog order, `### Added`, `### Changed` and `### Fixed`, with a blank line around each heading.
- **Which commits appear:** only the commits that bump under the unit's merged bump map (`{**DEFAULT_BUMPS, **unit.bump}`) or are breaking. `docs`, `chore` and the like, and unparseable subjects, are omitted (question 2). A released unit therefore always has a non-empty section.
- **Group:** a breaking commit of any type goes to Changed as `**BREAKING:** <description>`; otherwise `feat` goes to Added, `fix` to Fixed, and `perf`, `refactor` and any other type that bumps only through a `bump` override (for example `docs = "patch"`) to Changed (question 1).
- **Bullet:** `- <description> (<sha[:7]>)`, where the description is the parsed one, without type and scope: `- add a who-am-I read (#82) (241aae1)`.
- **Order:** within a group, the oldest commit comes first, so the section reads in the order the work landed (question 6).
- **Insertion**, which never rewrites an existing line:
  - *Missing file:* the standard header (`# Changelog`, the two standard Keep a Changelog 1.1.0 intro sentences), then `## [Unreleased]`, then the new section.
  - *A file with `## [Unreleased]`* (matched case-insensitively, brackets optional): the new section goes right before the next `##` heading after it, or at the end of the file. Anything under Unreleased stays there.
  - *A file without an Unreleased heading* (for example one whose first line is `## 0.0.1 — 2026-09-08`, with an extra `### Unknown` group): the new section goes before the first `##` heading, preceded by `## [Unreleased]`. When nothing but blank lines comes before that heading, the standard header goes on top as well. Otherwise the existing preamble (for example a `# Changelog` title) is kept as it is. Old sections keep their own heading style (question 7).
  - Line endings: if the existing file uses CRLF, the inserted lines do too. A missing final newline is added before appending at the end.
- **Date:** today's date in UTC, the same for every unit and for the branch name (question 5).

### Commit subject

`chore(release): <name> <old> -> <new>`, with one entry per released unit in path order, joined by `, `. For example, `chore(release): app 1.2.0 -> 1.3.0` or `chore(release): @scope/api 0.34.0 -> 0.35.0, @scope/web 1.3.0 -> 1.3.1` (question 8).

### Output

Text:

```
@scope/api (apps/api): 0.34.0 -> 0.35.0 (minor)
  warning: 0a1b2c3: not a Conventional Commit: wip
wrote apps/api/package.json
wrote apps/api/CHANGELOG.md
branch release/2026-09-18
commit 1a2b3c4 chore(release): @scope/api 0.34.0 -> 0.35.0
```

`--json` (question 9):

```json
{
  "units": [
    {"path": "apps/api", "name": "@scope/api", "version": "0.34.0", "next": "0.35.0", "bump": "minor",
     "warnings": ["0a1b2c3: not a Conventional Commit: wip"]}
  ],
  "files": ["apps/api/package.json", "apps/api/CHANGELOG.md"],
  "branch": "release/2026-09-18",
  "commit": "<40 hex>"
}
```

- `units` holds only the released units, in path order. `version` is the old version and `next` the new one, the same names `status` uses.
- `files` lists every file written, in the order they were written. `branch` and `commit` are `null` without `--branch` and `--commit`.
- With nothing to release: `{"units": [], "files": [], "branch": null, "commit": null}`, exit 0.
- Warnings are reported exactly as in `status` and never change the exit code, including the shallow-clone warning (question 10).

## Acceptance criteria

All run the CLI in process against real temporary git repositories, with the date fixed by monkeypatching one `_today()` helper. The changelog rendering and insertion rules are tested directly on `changelog.py`'s text functions (`tests/test_changelog.py`); the rest go through `semrail release` (`tests/test_release.py`).

1. In a single-unit repository with `feat` and `fix` commits, `release` writes the next version to the manifest and creates `CHANGELOG.md` with the standard header, an empty `## [Unreleased]` and a `## [X.Y.Z] - <date>` section holding `### Added` and `### Fixed`. It makes no commit and creates no branch, and the JSON output matches the shape above.
2. Grouping: `feat` goes to Added, `fix` to Fixed, and `perf`/`refactor` to Changed. A breaking commit of any type goes to Changed with `**BREAKING:**`. A type that bumps only through a `bump` override goes to Changed. `docs`, `chore` and unparseable subjects are omitted. Groups appear in the order Added, Changed, Fixed, and empty groups are left out.
3. Bullets are the description without type and scope, then the 7-character SHA: `feat(0037:api:session): add x (#82)` becomes `- add x (#82) (<sha7>)`. Within a group, the oldest commit comes first.
4. An existing Keep a Changelog file with content after `## [Unreleased]`: the new section goes right after Unreleased, and every existing line is unchanged, byte for byte.
5. A file with no header and no Unreleased section, starting with `## 0.0.1 — 2026-09-08` and holding a `### Unknown` group, gets the standard header, `## [Unreleased]` and the new section on top, with the old content unchanged below. A file with a `# Changelog` title but no Unreleased section keeps its title.
6. A CRLF changelog stays CRLF.
7. A unit with `changelog = false` gets its version and `sync` files written and no `CHANGELOG.md`.
8. In a workspace, only the units with a `next` version are released, each with its own `CHANGELOG.md`. Units with nothing to release are untouched.
9. `--commit` makes one commit whose subject follows the format above, for one unit and for two, and which contains exactly the files written. An untracked file present during the run stays out of the commit and stays untracked, and afterwards `git status` shows nothing else changed.
10. `--branch` creates and checks out `release/<date>`. If that branch exists, locally or as a remote-tracking branch, it uses `release/<date>-2` and then `-3`. `--branch --commit` puts the commit on the new branch and leaves the original branch where it was.
11. With nothing to release, `release` exits 0, prints `nothing to release` (JSON: empty `units`, `null` branch and commit), writes nothing and creates no branch or commit.
12. Uncommitted changes to tracked files make `release` exit 2 with a `semrail: ` message, having written nothing. Untracked files do not block it.
13. If a later unit fails, for example on a `sync` pattern that matches nothing, `release` exits 2, earlier units' files are restored byte for byte, the changelogs it created are removed, and no branch or commit is made.
14. A changelog that already has a heading for the new version makes `release` exit 2 before anything is written.
15. `release` never pushes and never tags: after `--branch --commit`, `git tag` is empty, and a repository with a bare remote shows no new refs on the remote.
16. Warnings (for example an unparseable subject) appear in the text and JSON output, and the exit code stays 0.

## Affected areas

- `src/semrail/changelog.py` (new): `render_section(version, date, entries, bumps)`, `insert(text, section)` and `has_version(text, version)`. Pure string functions.
- `src/semrail/cli.py`: the `release` subparser, `cmd_release` and its helpers (`_today`, the branch name, the rollback), as one contiguous block after the `status` block. Nothing else in the file changes.
- `tests/test_changelog.py` and `tests/test_release.py` (new).
- `docs/design.md`: the Changelog section (the rules above, briefly), the "Bump timing" and "Release commit" bullets (preflight, staging, the subject for several units, the branch name and its date) and the `release` row of the CLI table, plus the `release --json` shape under that table, next to `status --json`.
- `docs/features/README.md` and this file.
- Unchanged: `history.py`, `units.py`, `commits.py` and `gitutil.py`. Their public APIs are enough: `history.status`, `units.discover`, `units.write_version`, `Unit.changelog`/`bump`/`sync`/`manifest`, `commits.DEFAULT_BUMPS` and `gitutil.git`.

## Out of scope

- Link reference definitions at the bottom of the changelog (`[1.2.0]: https://…/compare/…`). semrail does not know the host's URL scheme. The bracketed headings are still valid Keep a Changelog.
- Moving hand-written entries out of `## [Unreleased]` into the release. Nobody writes entries by hand (`docs/releasing.md`), and existing content is never rewritten.
- A `--dry-run`: `semrail status` already shows what would be released (YAGNI).
- Honouring `SOURCE_DATE_EPOCH` or a `--date` flag. Tests monkeypatch the clock, and no consumer needs another date yet.
- Refusing to run on a shallow clone. It is a warning, as in `status`.
- `uv lock` or any other lockfile refresh. That stays in the consumer's steps (`docs/releasing.md`).
- Updating the README usage section and CLAUDE.md/AGENTS.md "Current state": left to T007 (decision 11).

## Open questions and risks

1. **Group for a type that bumps only through a `bump` override** (for example `docs = "patch"`). Recommend Changed, the Keep a Changelog group for general changes. Alternatives: pick the group by bump level (minor → Added, patch → Fixed), which misfiles a `docs` patch as a fix; or leave such commits out, which hides a change that moved the version.
2. **Non-bumping commits in the changelog.** Recommend leaving them out, as the spec says. Alternative: a "Other" group, which is not a Keep a Changelog group.
3. **Nothing to release.** Recommend exit 0, `nothing to release`, empty JSON `units`, and no files, branch or commit. CI can test `units == []`. Alternative: exit 1, but exit 1 means "lint or validation failed", and a scheduled release job would then fail on quiet days.
4. **Preflight.** Recommend refusing uncommitted changes to tracked files (exit 2), with or without `--commit`, and not checking the branch, since semrail does not know the consumer's mainline or promotion model. Alternatives: also refuse untracked files, which breaks CI checkouts holding build output; or no check, which lets a second run release the same commits twice; or require the mainline, which needs a new setting.
5. **Branch name and date.** Recommend the UTC date, used for both the heading and the branch. `-N` starts at `-2` and is chosen when `release/<date>[-N]` exists as a local branch or under any `refs/remotes/*/`. Tests monkeypatch a single `cli._today()`. Alternatives: the local date, which differs between a developer and CI around midnight; or the HEAD commit date, which is deterministic but not the release date.
6. **Bullet order within a group.** Recommend oldest first. Alternative: newest first, the `git log`/`status` order.
7. **Legacy files without Unreleased.** Recommend the insertion above: add the header only when nothing precedes the first `##` heading, add `## [Unreleased]`, add the new section on top, and never touch old headings such as `## 0.0.1 — …` or groups such as `### Unknown`. Alternatives: refuse such files (exit 2) until a human adds the header; or normalise the old headings, which rewrites existing sections and is forbidden by the spec.
8. **Commit subject and staging.** Recommend the subject above, with units in path order, no body, and only the written files staged via `git add -- <files>`. Alternative: `git commit -a`, which would sweep in unrelated tracked edits, though preflight makes that unlikely.
9. **The `release --json` shape** above. Alternative: per-unit `files` instead of the top-level list.
10. **Warnings.** Recommend reporting them as `status` does and releasing anyway. Alternative: refuse on the shallow-clone warning, since versions computed from truncated history are wrong (T004 verify showed that). That would be a behaviour change from the spec's "Warnings never change the exit code", so I recommend against it here.
11. **Docs outside the touch map.** `release` makes the CLAUDE.md/AGENTS.md "Current state" line ("the `lint` and `status` commands") stale, and the README usage section is a TODO placeholder. Recommend updating the "Current state" line in both files here (a one-line edit, as T004 did) and leaving the README to T007. Alternatives: a follow-up task, or leave both to T007.
12. **Rollback on a mid-release failure.** Recommend restoring the recorded originals (step 4, about 10 lines) so a release writes all or nothing. Alternative: no rollback. The tree was clean before the run, so `git checkout -- .` recovers, but that leaves a half-written multi-unit release for CI to trip over.
- **Risk:** a `git commit` hook that fails leaves the files written, and the branch too when `--branch` was given. The error is reported (exit 2). Rolling back after a hook failure is not attempted, since the hook may have changed files itself.
- **Risk:** a remote release branch that the local clone has not fetched is not seen, so the name may collide at push time. The push is the consumer's step, and it will reject the push visibly.

## Decisions

Plan approved. Questions 1–10 and 12 were decided as recommended. On 11, CLAUDE.md/AGENTS.md "Current state" and the README usage section are left to T007, which updates them once for both `release` and `tag`. On 13, the `release --json` paragraph under the CLI table is allowed. See `docs/autopilot/decisions/T005-write-changelogs-and-add-release.md`.

## Implementation

- Test first: `tests/test_changelog.py` and `tests/test_release.py` ran before any code existed. `test_changelog.py` failed at collection (`ImportError: cannot import name 'changelog' from 'semrail'`), and all 25 `test_release.py` tests errored (`semrail.cli has no attribute '_today'`).
- `src/semrail/changelog.py` (new) has `section`, `insert` and `has_version`, plus `FILE` and `HEADER`.
- `src/semrail/cli.py` gained the `release` subparser (right after `status`), and `cmd_release` with its helpers `_today`, `_release_branch`, `_release_paths`, `_read_or_none`, `_restore` and `_rel`, as one block after the `status` helpers. The import line also gained `changelog` and `datetime`.
- The rollback records the manifest, the `sync` files and `CHANGELOG.md` of every released unit before anything is written. It restores them if writing a file or creating the branch fails, and a changelog that did not exist before is deleted. A failure in `git add`/`git commit`, for example from a hook, is reported and not rolled back (plan risk).
- The written file list is de-duplicated, in case two units' `sync` entries name the same file.

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| 1 | `test_release.py::test_release_writes_version_and_creates_the_changelog`, `test_pyproject_unit`; `test_changelog.py::test_missing_file_gets_the_standard_header`, `test_empty_file_gets_the_standard_header` |
| 2 | `test_changelog.py::test_groups_in_keep_a_changelog_order`, `test_breaking_changes_go_to_changed_with_a_prefix`, `test_commits_that_do_not_bump_are_left_out`, `test_a_type_bumping_through_an_override_goes_to_changed`, `test_type_is_case_insensitive`; `test_release.py::test_bump_override_type_goes_to_changed_and_others_are_left_out` |
| 3 | `test_changelog.py::test_bullet_is_the_description_without_type_and_scope`, `test_groups_in_keep_a_changelog_order` (oldest first); `test_release.py::test_release_writes_version_and_creates_the_changelog` |
| 4 | `test_changelog.py::test_inserts_below_unreleased_and_keeps_existing_lines`, `test_content_under_unreleased_stays_there`, `test_unreleased_directly_followed_by_a_release`, `test_unreleased_at_the_end_without_a_final_newline`, `test_unreleased_heading_variants`; `test_release.py::test_existing_changelog_keeps_every_line` |
| 5 | `test_changelog.py::test_file_without_header_or_unreleased`, `test_file_with_a_title_but_no_unreleased_keeps_its_title`, `test_file_with_only_a_title`; `test_release.py::test_changelog_without_header_or_unreleased` |
| 6 | `test_changelog.py::test_crlf_stays_crlf`; `test_release.py::test_crlf_changelog_stays_crlf` |
| 7 | `test_release.py::test_changelog_false_writes_only_versions` |
| 8 | `test_release.py::test_only_units_with_a_next_version_are_released` |
| 9 | `test_release.py::test_commit_one_unit`, `test_commit_several_units`, `test_after_a_release_commit_there_is_nothing_to_release` |
| 10 | `test_release.py::test_branch_is_created_from_the_date`, `test_branch_gets_a_suffix_when_the_name_exists`, `test_branch_suffix_counts_up`, `test_today_is_the_utc_date` |
| 11 | `test_release.py::test_nothing_to_release` |
| 12 | `test_release.py::test_uncommitted_tracked_changes_are_refused`, `test_staged_changes_are_refused`, `test_untracked_files_do_not_block` |
| 13 | `test_release.py::test_a_failing_unit_rolls_back_every_file`, `test_a_failing_unit_removes_changelogs_it_created` |
| 14 | `test_release.py::test_existing_section_for_the_new_version_is_refused`; `test_changelog.py::test_has_version` |
| 15 | `test_release.py::test_release_never_pushes_or_tags` |
| 16 | `test_release.py::test_warnings_are_reported_and_do_not_block`, `test_text_output` |

## Verify

Exercised with `uv run --project <worktree> semrail --root <repo> release …` on scratch repositories. A script under the session scratchpad built them; nothing from it is committed. The real date was used (2026-09-18, UTC).
- **pnpm monorepo, three units, tagged.** A dirty but untracked `notes.txt` was present. The history held a squash-merged `feat(0037:api:session): …`, `fix(web)`, `wip`, a root-only `docs`, and a `refactor!` touching `apps/api` and `packages/core`. `release --branch --commit` gave:
  - `@scope/api 0.34.0 -> 0.35.0` (minor: breaking at 0.y.z), `@scope/web 1.3.0 -> 1.3.1` with the `wip` warning, and `@scope/core 1.0.0 -> 2.0.0`;
  - branch `release/2026-09-18` and one commit `chore(release): @scope/api 0.34.0 -> 0.35.0, @scope/web 1.3.0 -> 1.3.1, @scope/core 1.0.0 -> 2.0.0` holding exactly the 6 written files;
  - `notes.txt` still untracked, and no tag added.
  - `apps/api/CHANGELOG.md` was created with the header, Unreleased, `### Added` and `### Changed` (`**BREAKING:** rename the client`).
  - The existing `apps/web/CHANGELOG.md` got the new section between Unreleased and `## [1.3.0]`, with its old lines unchanged.
  - A second `release --json` printed empty `units`/`files` and exited 0.
- **Single pyproject unit** with `tag = "v{version}"` and a `sync` entry on `__version__`: `release --json` wrote `pyproject.toml`, `src/tool/__init__.py` and `CHANGELOG.md` (`perf` under Changed), with no branch and no commit. `git status` showed only those three files.
- **Legacy changelog** (`## 0.0.1 — 2026-09-08` with a `### Unknown` group, no header), with `release/2026-09-18` already taken: `release --branch` created `release/2026-09-18-2`. The changelog got the standard header, `## [Unreleased]` and `## [0.1.0] - 2026-09-18` on top, and the old section was unchanged below.
- **Errors:**
  - A modified tracked file: `semrail: release: tracked files have uncommitted changes; commit or stash them first`, exit 2.
  - Only a `docs` commit since the tag: `nothing to release`, exit 0, no branch and no commit.
  - A monorepo whose second unit's `sync` file held `bogus`: `semrail: apps/web/version.txt: sync pattern '^(.+)$': found 'bogus', not the current version 1.3.0`, exit 2. `git status --untracked-files=all` was empty (the first unit's version and new changelog were rolled back), no new release branch existed, and HEAD was unchanged.

The behaviour matches the plan.

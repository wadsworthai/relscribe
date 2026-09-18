# T002 — Parse Conventional Commit subjects and add lint

Governing spec: `docs/design.md`, sections Versioning, Commit parsing and CLI (the `lint` row and exit codes).

## Behaviour

- `semrail lint <subject>…` checks each subject against `type(scope)!: description` and exits 0 when all parse, 1 when any does not. It needs no repository, so it runs on a pull request title in any CI step.
- `semrail lint --range <from>..<to>` checks the subjects of the non-merge commits in that range of the repository (`--root`, else the enclosing one). Subjects and `--range` can be combined; everything given is checked.
- `--json` works before or after `lint`.
- For later tasks, `semrail.commits` exposes the parser, the bump rules and the version arithmetic:
  - `parse(subject, body="") -> Commit | None` — `Commit(type, scope, breaking, description)`; `None` when the subject does not parse.
  - `bump(commits, version, bumps=DEFAULT_BUMPS) -> "major" | "minor" | "patch" | None` — the highest bump among the commits for a unit at `version`. `bumps` is the type → level map; reading `semrail.toml` stays with T003, so the caller passes the effective map.
  - `next_version(version, level) -> str`.
  - `log(root, rev_range) -> list[LogEntry]` — `(sha, subject, body)` of the non-merge commits in a range, through `gitutil.git`.

### Parsing rules

- Grammar: `type`, then an optional `(scope)`, an optional `!`, then `: ` (colon and one space) and a non-empty description.
  - `type` is a letter followed by letters, digits or `-`; it is compared case-insensitively and stored lower-case (Conventional Commits 1.0.0, item 15).
  - `scope` is free text without parentheses or line breaks; it may contain `:`. An empty `()` does not parse.
  - The description is everything after `: ` and keeps a trailing `(#82)` / `(#T054)`.
- Breaking: `!` before the colon, or a body line starting with `BREAKING CHANGE: ` or `BREAKING-CHANGE: ` (upper-case only, as the spec requires). A subject that does not parse is never breaking: it contributes nothing.

### Bump rules

- `DEFAULT_BUMPS = {"feat": "minor", "fix": "patch", "perf": "patch", "refactor": "patch"}`; any other type bumps nothing.
- A breaking commit bumps `major` whatever its type.
- While the version is `0.y.z`, a `major` bump becomes `minor` — for a breaking commit and for a type the map sends to `major` alike (decision 2).
- The highest level among the commits wins; no commit that bumps gives `None`.
- `next_version`: major → `X+1.0.0`, minor → `X.Y+1.0`, patch → `X.Y.Z+1`. A version that is not plain `X.Y.Z` raises an error (exit 2 at the CLI).

### Output

Text: one line per invalid subject, `invalid: <subject>` (prefixed with the short SHA for a commit from `--range`), then a summary, `<n> of <m> subjects invalid` or `<m> subjects valid`, with `subject` in the singular when `<m>` is 1 (`1 subject valid`, `1 of 1 subject invalid`).

`--json`:

```json
{
  "valid": false,
  "subjects": [
    {"sha": "241aae1…", "subject": "feat(api): add x (#82)", "valid": true},
    {"sha": null, "subject": "oops", "valid": false}
  ]
}
```

`sha` is the full SHA for a `--range` commit and `null` for a subject given as an argument.

## Acceptance criteria

1. `lint "feat: x"` exits 0; `lint "oops"` exits 1; with several subjects, one invalid subject makes the run exit 1 and only that subject is reported invalid.
2. These parse, with the expected type, scope, breaking flag and description: `feat: x`, `fix(parser): x`, `feat(0037:api:session): x`, `refactor(api)!: x`, `feat!: x`, `Feat: x` (type `feat`), `fix: accept a trailing reference (#82)` and `(#T054)` (the reference stays in the description).
3. These do not parse: `oops`, `feat x`, `feat:x`, `feat: ` (empty description), `feat(): x`, `(api): x`, `feat(a(b)): x`, `Merge branch 'x'`, `Revert "feat: x"`.
4. A body line `BREAKING CHANGE: …` or `BREAKING-CHANGE: …` makes a parsed commit breaking; `breaking change: …` in the body does not; the footer on an unparseable subject yields no commit.
5. `bump`: breaking → `major` at ≥ 1.0.0 and `minor` at 0.y.z; `feat` → `minor`; `fix`/`perf`/`refactor` → `patch`; `docs`/`chore`/unknown types → `None`; the highest wins over a mixed list; an empty list → `None`; unparseable subjects contribute nothing.
6. `bump` with an overriding map uses it instead of the defaults (e.g. `{"docs": "patch"}` makes `docs` bump and `feat` not); a type mapped to `major` gives `minor` at 0.y.z.
7. `next_version` gives `2.0.0`, `1.3.0`, `1.2.4` from `1.2.3` for major/minor/patch, and `0.2.0` from `0.1.5` for minor; a non-`X.Y.Z` version is an error.
8. `lint --range A..B` in a real repository checks exactly the non-merge commits in the range, reports each invalid one with its SHA, and exits 1 if any is invalid, 0 otherwise; an empty range exits 0.
9. `lint --range` without `..` exits 2 with a `semrail: ` error; a range git cannot resolve exits 2; `lint` with neither subjects nor `--range` exits 2.
10. `lint "feat: x"` works outside any git repository.
11. `semrail lint --json "feat: x"` and `semrail --json lint "feat: x"` both print the JSON result.

## Affected areas

- `src/semrail/commits.py` (new): `Commit`, `parse`, `DEFAULT_BUMPS`, `bump`, `next_version`, `LogEntry`, `log`.
- `src/semrail/cli.py`: the `lint` subparser and `cmd_lint`; remove the `_ = sub, common` placeholder.
- `tests/test_commits.py` (new): parser, bump rules and `next_version`, tested on the module directly, since no command exposes bump rules yet (as T001 did for `gitutil`); they move to CLI level with `status` (T004).
- `tests/test_lint.py` (new): `lint` end to end through the `cli` and `repo` fixtures.
- `docs/features/README.md` and this file: the task record.
- Only if approved (decisions 1, 3): one line each in `docs/design.md` and the `README.md` bump table.

## Out of scope

- Reading `semrail.toml` or merging a configured `bump` map with the defaults: T003 (config) and T004 (the caller).
- Selecting a unit's commits by path, `exclude`, and base resolution: T004. `log` takes a range only, no paths.
- Reading subjects from stdin, per-reason lint messages, a list of allowed types: not required by the spec (YAGNI).
- The README usage section for `lint`: T007 writes it for every command.

## Decisions needed

1. **Spec lines for what `docs/design.md` leaves implicit.** The parser settles three points the Commit parsing section does not state: the type is case-insensitive (Conventional Commits 1.0.0 requires it), a `BREAKING CHANGE:` footer is recognised on any body line rather than only in the last paragraph, and `lint --range` skips merge commits (as unit selection does with `--no-merges`). Recommend adding one bullet each to `docs/design.md` Commit parsing in this task. Alternative: leave `docs/design.md` unchanged and record them only here.
2. **A type configured as `major` while 0.y.z.** Recommend treating it like a breaking change: `minor` while 0.y.z, which keeps the rule "no MAJOR before 1.0.0" true for every source of a major bump, and adding that to the Versioning section. Alternative: honour `major` literally, so a `bump = { x = "major" }` config moves 0.y.z to 1.0.0.
3. **README drift.** `README.md` "How versions are computed" lists `refactor` among the types that bump nothing and omits `perf` and `BREAKING-CHANGE:`, contradicting `docs/design.md`. Recommend correcting those two rows here, since this task implements the rules. Alternative: leave it to T007's README work.

Decisions 1–3 were approved as recommended (`docs/autopilot/decisions/T002-parse-conventional-commit-subjects-and-a.md`).

## Tests

Written before the code. The first run failed: `tests/test_lint.py` had 15 failures (`invalid choice: 'lint'`), and `tests/test_commits.py` failed at collection (`No module named 'semrail.commits'`).

| Criterion | Tests |
|---|---|
| 1 | `test_lint.py`: `test_valid_subject`, `test_invalid_subject`, `test_one_invalid_among_several`, `test_summary_counts_subjects` |
| 2 | `test_commits.py`: `test_parses` (8 cases) |
| 3 | `test_commits.py`: `test_rejects` (10 cases, including a multi-line subject) |
| 4 | `test_commits.py`: `test_breaking_footer`, `test_lowercase_footer_is_not_breaking`, `test_footer_on_unparseable_subject_yields_nothing` |
| 5 | `test_commits.py`: `test_bump_defaults` (15 cases), `test_bump_footer_is_breaking` |
| 6 | `test_commits.py`: `test_bump_override_map_replaces_defaults`, `test_bump_configured_major_is_minor_before_1_0_0` |
| 7 | `test_commits.py`: `test_next_version`, `test_next_version_rejects_non_plain_versions` |
| 8 | `test_lint.py`: `test_range`, `test_range_all_valid`, `test_range_uses_enclosing_repository`, `test_empty_range`, `test_range_skips_merge_commits`, `test_subjects_and_range_combined` |
| 9 | `test_lint.py`: `test_bad_range_is_an_error` (`HEAD`, `no-such-ref..HEAD`), `test_nothing_to_lint_is_a_usage_error` |
| 10 | `test_lint.py`: `test_works_outside_a_repository` |
| 11 | `test_lint.py`: `test_json_after_subcommand`, `test_json_before_subcommand` |

`taskrail checks T002 --stage implement`: 72 passed, and lint is not configured. The suite also passes on Python 3.11 (`uv run --isolated --python 3.11 pytest`).

## Open questions and risks

- Parentheses inside a scope (`feat(a(b)): x`) do not parse. The spec calls the scope free text but gives only `:` as an example; forbidding parentheses keeps a trailing `(#82)` unambiguous.
- `Revert "…"`, `fixup! …` and `Merge …` subjects fail lint. A repository that keeps them in its history gets lint failures on `--range`; merges are excluded, the other two are real non-conforming subjects.

# T009 — Add a dry run to tag

Governing spec: `docs/design.md`, Releases and tags, the `tag` row of the CLI table and the `tag --json` paragraph.

## Behaviour

`relscribe tag --dry-run <from>..<to> [--json]` runs the same detection as `relscribe tag` and reports what that run would do, without creating or pushing any tag. CI can then use `tag` as a query about the releases a range contains:

- Before promoting an exact commit to a deploy branch: is `<sha>` a release commit, and of which units? Range `<sha>^..<sha>`.
- Before running tests only for the units a release branch touches: which units does it release? Range `<mainline>..<release-branch>`.

In both, the releases reconciled before `<from>` are not part of the answer, so every tag entry says whether it was reconciled (question 4).

### Results

- A tag the real run would create is reported with `result: "would-create"` (question 1). Nothing is written to the repository.
- `existing` and `conflict` are reported exactly as in a real run, with `existing_sha` for a conflict.
- Within one run, a tag the dry run would create counts as created for the releases after it, so a second release of the same version in the range is a `conflict` with the first, as in a real run.
- The dry run needs no committer identity, since it creates no annotated tag.
- The shallow-clone warning is unchanged.

### `--dry-run` with `--push`

A usage error, exit 2, with `relscribe: tag: --dry-run and --push cannot be combined` on stderr (question 2). Nothing is created or pushed.

### Exit code

The same as the real run would give (question 3): 4 when any entry is a `conflict`, otherwise 0. The JSON or text is printed in both cases.

### Output

JSON: every tag entry gains `"reconciled": true|false` (in real runs too). `push` is `null` under `--dry-run`.

```json
{
  "tags": [
    {"tag": "@scope/core@1.0.0", "path": "packages/core", "name": "@scope/core", "version": "1.0.0",
     "sha": "<40 hex>", "result": "existing", "existing_sha": null, "reconciled": true},
    {"tag": "@scope/api@0.35.0", "path": "apps/api", "name": "@scope/api", "version": "0.35.0",
     "sha": "<40 hex>", "result": "would-create", "existing_sha": null, "reconciled": false}
  ],
  "push": null,
  "warnings": []
}
```

A caller keeps the range's releases with `jq '[.tags[] | select(.reconciled | not)]'`.

Text (question 5): the same line per tag, with `would-create` as the result word, and `(reconciled)` appended to a reconciled entry, in real runs too:

```
existing @scope/core@1.0.0 4d5e6f7 (reconciled)
would-create @scope/api@0.35.0 9f8e7d6
```

With nothing in the range and nothing to reconcile, the text stays `no releases to tag`.

## Acceptance criteria

All through the CLI against real temporary repositories (`tests/test_tag.py`).

1. `tag --dry-run <from>..<to> --json` on a range with a release whose tag is missing reports it as `would-create` with the release's `sha`, exits 0, and leaves `git tag --list` unchanged. A real run of the same range afterwards reports the same entries with `created` in place of `would-create`.
2. Under `--dry-run`, a tag that already exists on the release commit is `existing`; one that exists on another commit is `conflict` with `existing_sha`, the tag is not moved, and the exit code is 4.
3. Under `--dry-run`, the same tag released twice in the range gives `would-create` for the first release and `conflict` (with `existing_sha` = the first release's commit) for the second, as in a real run.
4. `--dry-run --push <remote>` is a usage error: `relscribe: …` on stderr, exit 2, no tag created locally or on the remote.
5. Every entry has `reconciled`: `true` for the reconciled release before `<from>`, `false` for releases in the range, in real and dry runs.
6. Query use cases: `<sha>^..<sha>` on a release commit of two units lists both with `reconciled: false`; on a commit that releases nothing, it lists no entry with `reconciled: false`. `<mainline>..<release-branch>` lists the release branch's released units.
7. `--dry-run` succeeds in a repository without a committer identity (`user.useConfigOnly = true`, no name or email), where a real run fails with exit 2.
8. Text output: `would-create <tag> <short sha>` lines, and `(reconciled)` after a reconciled entry.

## Affected areas

- `src/relscribe/tags.py`: `run(..., dry_run=False)`; `_tag` returns `would-create` instead of calling `git tag` and remembers the names it would create within the run; `TagResult` gains `reconciled`.
- `src/relscribe/cli.py`: the `--dry-run` flag on `tag`, the `--push` combination check in `cmd_tag`, `reconciled` in `_tag_json`, and the text line in `_tag_text`.
- `tests/test_tag.py`: tests for the criteria above; existing JSON equality assertions gain `"reconciled"`.
- `docs/design.md`: a "Dry run" bullet under Releases and tags, the `tag` row of the CLI table, and the `tag --json` paragraph (`"would-create"`, `reconciled`).
- `docs/features/README.md` (one row) and this file.
- `README.md`: unchanged. It does not document `tag` today; its usage belongs to T007.

## Out of scope

- A flag to skip reconcile (question 4, alternative).
- Checking the remote (`git ls-remote`) to predict push rejections.
- A dedicated query command (for example `releases <range>`): `tag --dry-run` answers both use cases.

## Open questions and risks

1. **Result name for a tag that would be created.** Recommend `"would-create"`: it reads as the dry-run form of `"created"`, and a caller that treats any result other than `"conflict"` as fine keeps working. Alternatives: `"missing"` (describes the repository, not the run), `"new"`.
2. **`--dry-run` with `--push`.** Recommend a usage error (exit 2). The only thing a dry push could report is the `would-create` list itself, since a remote rejection cannot be known without contacting the remote; and a `push` object listing tags under `pushed` that were never pushed would mislead a caller. Alternative: allow it and report `push: {"remote", "pushed": [<would-create tags>], "rejected": []}`, or ignore `--push`.
3. **Exit code on a conflict under `--dry-run`.** Recommend the same as a real run (4). A dry run then predicts the real run completely, the code has no special case, and a conflict is a problem a human must resolve before the release is tagged, which a promotion step should not silently pass. The JSON is still printed, so a caller that only wants the answer can accept 4 (`|| [ $? -eq 4 ]`). Cost: a conflict on a reconciled older release also gives 4 in a query about an unrelated range; the same conflict already fails every real `tag` run until that unit's next release (T006, question 5). Alternative: always 0 under `--dry-run`, with conflicts visible only in the output.
4. **Reconciled releases in query results.** Recommend a `"reconciled": true|false` field on every tag entry (and `(reconciled)` in text). It adds no flag and no mode, the real run's output also gains the information, and both use cases filter with one `jq` select. Alternative: a `--no-reconcile` flag that skips reconcile, which gives an exact answer without filtering and keeps a reconciled conflict out of the exit code, but adds an option that real CI runs could also turn off, contradicting the reconcile rule's purpose (a skipped CI run's tag), and one more combination to test. A third option, having `--dry-run` itself skip reconcile, is rejected: the dry run would no longer predict the real run.
5. **Text wording.** Recommend the existing one-line-per-tag format with `would-create` as the result word and `(reconciled)` appended, no extra summary line. Alternative: a leading `dry run: no tags created` line.
- **Risk:** adding `reconciled` to every entry changes the JSON of real runs. It is an added key, so readers that select keys keep working; the only exact-equality readers are this repository's tests.
- **Prior work:** `taskrail show` lists the branch `T009-add-a-dry-run-to-tag` as prior work (`prepared: null`); it holds only the orchestrator's backlog commit `e3f935b` on top of `origin/main`, no earlier work.

## Decisions

Plan approved with every question as recommended; see `docs/autopilot/decisions/T009-add-a-dry-run-to-tag.md`. The result is `would-create`. `--dry-run --push` is exit 2. A conflict under `--dry-run` is exit 4. Every entry has `reconciled`, in real runs too. The text keeps its format and appends ` (reconciled)`.

## Implementation

- Test first: with the new and updated tests in `tests/test_tag.py` and no code change, `uv run pytest -q --tb=line` gave `13 failed, 252 passed`. The 10 new tests using `--dry-run` failed with `unrecognized arguments: --dry-run`, the parametrized `reconciled` test's real-run case failed with `KeyError: 'reconciled'`, and the three updated tests (two exact JSON entries and the text output) failed on the missing `reconciled` key and ` (reconciled)` suffix.
- `src/relscribe/tags.py`: `run(..., dry_run=False)`. `TagResult` gains `reconciled`. `_tag` takes `reconciled` and `planned`, a dict of the tags a dry run would create (`None` in a real run). A tag found neither in the repository nor in `planned` is recorded there and reported as `would-create`, so a later release of the same tag in the run is a conflict against it, as in a real run.
- `src/relscribe/cli.py`: `--dry-run` on `tag`; `cmd_tag` rejects it with `--push` before touching the repository; `reconciled` in `_tag_json`; ` (reconciled)` in `_tag_text`.
- `docs/design.md`: a "Dry run" bullet under Releases and tags, the `tag` row, and the `tag --json` paragraph.

## Acceptance criteria → tests (`tests/test_tag.py`)

| AC | Tests |
|---|---|
| 1 | `test_dry_run_reports_would_create_and_creates_nothing` |
| 2 | `test_dry_run_reports_existing_and_conflict_and_exits_4` |
| 3 | `test_dry_run_same_tag_twice_conflicts_with_the_first` |
| 4 | `test_dry_run_with_push_is_a_usage_error` |
| 5 | `test_entries_say_whether_they_were_reconciled` (real and dry), `test_version_raise_is_tagged_with_an_annotated_tag`, `test_tag_on_another_commit_is_a_conflict_and_other_tags_are_still_created` |
| 6 | `test_query_whether_a_commit_is_a_release`, `test_query_the_units_a_release_branch_releases` |
| 7 | `test_dry_run_needs_no_committer_identity` |
| 8 | `test_dry_run_text_output`, `test_text_output` (` (reconciled)` in a real run) |

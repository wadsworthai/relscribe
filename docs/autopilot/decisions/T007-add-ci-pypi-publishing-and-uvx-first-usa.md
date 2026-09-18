# T007 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## Human decision carried into this task

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How relscribe is run by consumers | uvx pinned per repo · global CLI install | **`uvx relscribe@X.Y.Z` is the recommended default; every example, script and CI recipe uses it; a global install is documented only as a non-recommended alternative** | The human decided this on 2026-09-18: projects pin the version per repo and install nothing on the machine. |

Answered by the human.

## scope gate

Reviewed: `docs/chores/T007-add-ci-pypi-publishing-and-uvx-first-usa.md` at bf8f70b (the artifact and index row only; nothing else edited, and no tag exists in this repository), plus the lane's evidence. On a scratch clone, a squash-merged release PR is detected by its version change and tagged `v0.1.0`; `chore(release)` bumps nothing afterwards; `uv.lock` is kept consistent by the `sync` entry; `uv lock --check` passes.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Upload tool | `uv publish` · `pypa/gh-action-pypi-publish` | as recommended (`uv publish`) | One tool already in use, trusted publishing built in (KISS). |
| 2 | When to publish | only a newly `created` `v*` tag, retry failed jobs · also `existing` | as recommended | Simplest, and "Re-run failed jobs" covers a failed upload. |
| 3 | Action pinning | exact release tags · commit SHAs | as recommended (exact tags) | Readable, and setup-uv has no floating major tag. |
| 4 | `uv run --locked pytest` | yes · plain | as recommended | It catches a stale `uv.lock`. |
| 5 | Concurrency group on `release.yml` | yes · no | as recommended | It prevents duplicate tagging or uploads. |
| 6 | Where to record the new tooling and its date | `docs/development.md` · new doc | as recommended | No new doc to map. |
| 7 | Change set and boundary as written | approve · change | **approve** | It matches the task row and the human's uvx-first rule, and does no release, tag, push or remote configuration. |

The human prerequisites (PyPI pending publisher, GitHub environment `pypi`, squash-only with the PR title as the commit message, workflow permissions, tag rulesets) are passed to the human now, ahead of T010.

## escalated to the human (during implement)

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Publish to PyPI | publish · no registry for now | **no registry for now; consumers run `uvx --from git+https://github.com/wadsworthai/relscribe@vX.Y.Z relscribe`** | The human's decision on 2026-09-18. It replaces the earlier PyPI choice. The `vX.Y.Z` git tag is the release artifact. |

Answered by the human. Scope decisions 1 and 2 (upload tool, when to publish) no longer apply.

## implement gate

Reviewed: `release.yml` (tag job only, `contents: write`, concurrency, full history, identity, env-passed range), `relscribe.toml`, and the README "Running relscribe" section (git-pinned `uvx` is recommended and used in every example; global install only as a non-recommended alternative). `grep -i pypi` over the README, `docs/` and the workflows finds nothing. The lane's evidence covers: actionlint 0 errors; 265 passed on 3.11 and 3.14 with `--locked`; hostile PR titles not executed; `uvx --from git+file://<scratch>@v0.1.0 relscribe --version` printing `0.1.0`; `tag --dry-run origin/main..HEAD` reporting no releases. `taskrail checks T007` re-run: 265 passed. This repository has no tags.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Backlog text naming PyPI (E01 "Done when", T010 description) | update in this branch · separately | **update in this branch** | The backlog merges with the docs that describe the new release path. Use `taskrail edit` for T010. Change only the words in E01's "Done when" line, then run `taskrail validate`. |
| 2 | T007 title still names PyPI | retitle · leave | **retitle** to "Add CI, release tagging and uvx-first usage docs" | The title must not describe work that isn't done. The branch name stays. |
| 3 | Approve the implement stage | approve | **approve** | |

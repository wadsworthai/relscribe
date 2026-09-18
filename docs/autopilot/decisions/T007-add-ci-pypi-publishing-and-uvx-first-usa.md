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

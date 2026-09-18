# Releasing

## Branches and PRs

- Work on a branch and reach `main` through a PR. Every PR is squash-merged.
- The PR title is a Conventional Commit and becomes the single commit on `main`, so it decides the next version. Its type reflects the most significant change.
- Mark breaking changes with `!`.
- Put trailers at the end of the PR description so they survive the squash.
- Task branches never change the version or `CHANGELOG.md`, except a branch whose only purpose is the release (see Cutting a release).

## Changelog

`CHANGELOG.md` is generated from commit subjects at release time, in the format described in `docs/design.md`. Nobody writes entries by hand.

## CI

- `.github/workflows/ci.yml` runs the tests on Python 3.11 and 3.14 for every PR and every push to `main`.
- `.github/workflows/pr-title.yml` runs `relscribe lint` on the PR title.
- `.github/workflows/release.yml` runs `relscribe tag <before>..<after> --push origin` on every push to `main`.

These workflows run relscribe from the checked-out source (`uv run relscribe`), because this repository is relscribe itself. Consumers pin a release tag with `uvx --from git+…@vX.Y.Z` instead (see the README).

## Cutting a release

relscribe is not published to any registry. The `vX.Y.Z` git tag is the release. The version is written in `pyproject.toml`. `relscribe.toml` sets the tag to `v` plus that version and keeps the copy in `uv.lock` in step through `sync`.

1. Check out an up-to-date `main` with a clean tree, and check what will be released with `uv run relscribe status`.
2. Run `uv run relscribe release --branch --commit`. It creates `release/<YYYY-MM-DD>` and commits `pyproject.toml`, `uv.lock` and `CHANGELOG.md` as `chore(release): relscribe <old> -> <new>`.
3. Push the branch and open a PR whose title is exactly that subject. Squash-merge it once CI passes.
4. On the push to `main`, `release.yml` creates the tag `v<new>` on the squash commit and pushes it. That completes the release.

- A branch whose only purpose is the release may carry the release commit instead of `release/<date>`: run `release --commit` without `--branch` on it, from a clean tree based on the current `main`. Its PR title may be any Conventional Commit, because `tag` detects the version change, not the message.
- If the run fails before pushing, re-run it. `tag` creates only the tags that are missing.
- If the tag job exits with a conflict, a tag with that name already exists on another commit. A human resolves it. A published tag never moves.

## Repository setup

These are one-time settings that only a maintainer can change:
- Pull requests: allow squash merging only, and set the default squash commit message to the pull request title.
- Actions: the workflow permissions must let a job request `contents: write`. If a ruleset protects `v*` tags, `github-actions[bot]` must be allowed to create them.
- Recommended: require the `ci` and `pr-title` checks before merging to `main`.

# Releasing

## Branches and PRs

- Work on a branch and reach `main` through a PR. Every PR is squash-merged.
- The PR title is a Conventional Commit and becomes the single commit on `main`, so it decides the next version. Its type reflects the most significant change.
- Mark breaking changes with `!`.
- Put trailers at the end of the PR description so they survive the squash.
- Task branches never change the version or `CHANGELOG.md`.

## Changelog

`CHANGELOG.md` is generated from commit subjects at release time, in the format described in `docs/design.md`. Nobody writes entries by hand.

## Cutting a release

The version is written only in `pyproject.toml`. The tag is `v` plus that version.

Once semrail can release itself:
1. On an up-to-date `main`, run `uv run semrail release --branch --commit`, then `uv lock`, and amend the commit. Push the branch and open a PR titled `chore(release): X.Y.Z`.
2. After the squash merge, CI runs `semrail tag` on the pushed range and publishes the tagged version to PyPI. A published tag never moves.

Until then, cut releases by hand following the same steps: set the version, write the changelog section in the same format, run `uv lock`, merge, then `git tag -a vX.Y.Z <merge commit> -m "semrail X.Y.Z"` and push.

# Releasing

## Branches and PRs

- Work on a branch and reach `main` through a PR. Every PR is squash-merged.
- The PR title is a Conventional Commit and becomes the single commit on `main`. Its type reflects the most significant change.
- Mark breaking changes with `!` and give them their own changelog entry.
- Put trailers at the end of the PR description so they survive the squash.

## Changelog

`CHANGELOG.md` starts with a `## Unreleased` section. Entries are bullets with a bold lead that describe user-visible behaviour, not individual commits.

## Cutting a release

The version is written only in `pyproject.toml`, and it must equal the tag without the `v`.

1. In a PR: set the version, run `uv lock`, and rename `## Unreleased` to `## X.Y.Z`.
2. After the merge: `git tag -a vX.Y.Z <merge commit> -m "semrail X.Y.Z"`, then push the tag. A published tag never moves.
3. Verify a clean install from the tag, then bump `main` to the next `.dev0`.

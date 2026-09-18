# Design

This is the spec the code answers to. Most of it is still a plan. Build each part only when a concrete need requires it.

## Versioning

semrail follows [SemVer 2.0.0](https://semver.org/) and reads [Conventional Commits 1.0.0](https://www.conventionalcommits.org/) as written. Record any deviation here.

| Commit | Bump |
|---|---|
| `fix:` | PATCH |
| `feat:` | MINOR |
| `!` before the colon, or a `BREAKING CHANGE:` footer | MAJOR |
| any other type | none |

- Open: how versions before 1.0.0 (0.y.z) bump. Decide once, record it here, and apply it everywhere.

## Commit parsing

- The input is the squash-merged PR titles on the mainline.
- Subjects may end with a reference in parentheses, as in `feat(cli): add x (T006)`, and the parser must accept that.
- A scope names an area, not a package, so it cannot select a package in a monorepo. Map paths to packages explicitly in config.

## Changelog merging

- Open: other tools may already claim `CHANGELOG.md` in `.gitattributes` with a merge driver. Decide whether semrail claims those paths, detects an existing driver, or stays out of merge resolution.

## CLI contract (planned)

- Every command accepts `--json` (printed through one `_emit(data, as_json, text)` helper) and `--root <path>`. Without `--root`, the root is found by searching upward for `.semrail/config.toml`.
- Exit codes are named constants at the top of `cli.py` and are stable, because agents branch on them: 0 success, 1 validation failed, 2 usage, config or git error.
- Errors go to stderr prefixed with `semrail: ` and name the next command to run when possible. Validation reports every problem, each with its file and line, before exiting.

## Architecture (planned)

```
src/semrail/
  cli.py        # argparse; each subcommand is a thin cmd_*(args) -> int
  config.py     # find_root + load_config (tomllib)
  model.py      # domain dataclasses, each with to_dict() for --json
  gitutil.py    # the only module that shells out to git
  <domain>.py   # one small module per concern
tests/          # pytest; conftest.py builds real git repos in tmp_path
```

- The logic lives in domain modules that can be imported and tested without the CLI.
- Configuration lives in a committed `.semrail/config.toml`. Anything derivable from git, such as tags or commits, is read at runtime and never cached in the repo. Machine-local state never goes into `.semrail/`.

## Distribution (planned)

- Nothing is published to PyPI; the git tag is the release artifact. Install with `uv tool install semrail --from "git+<repo-url>@vX.Y.Z"`.
- Candidates, to build only when needed: an idempotent `semrail init`; a committed wrapper `.semrail/bin/semrail` that runs the version pinned in the config; agent skills installed into consumer repos. Skills tell the agent which command to run and never reimplement the logic.

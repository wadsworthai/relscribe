#!/bin/sh
# SessionStart: tell Claude when a newer taskrail release exists than the one pinned in .taskrail/config.toml.
pin=$(sed -n 's/^version *= *"\(v[0-9.]*\)".*/\1/p' "$CLAUDE_PROJECT_DIR/.taskrail/config.toml" | head -1)
latest=$(timeout 10 git ls-remote --tags --refs https://github.com/wadsworthai/taskrail.git 'v*' | sed 's|.*refs/tags/||' | sort -V | tail -1)
[ -n "$pin" ] && [ -n "$latest" ] || exit 0
if [ "$latest" != "$pin" ] && [ "$(printf '%s\n%s\n' "$pin" "$latest" | sort -V | tail -1)" = "$latest" ]; then
  msg="taskrail $latest is available; this repo pins $pin (.taskrail/config.toml). Tell the user and offer to upgrade: taskrail self upgrade, then .taskrail/bin/taskrail upgrade in a branch/PR."
  jq -n --arg m "$msg" '{systemMessage: $m, hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $m}}'
else
  jq -n --arg m "taskrail is up to date ($pin)." '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $m}}'
fi

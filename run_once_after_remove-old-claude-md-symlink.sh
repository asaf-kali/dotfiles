#!/bin/bash
# Migration: machines set up by hand had ~/.claude/CLAUDE.md as a symlink to
# ~/projects/agent-rules/python.md. Those rules moved into the kaliclaude plugin's skills and
# python.md no longer exists upstream, so the link is stale or dangling. Remove that link, and only
# that: a regular file, or a symlink pointing anywhere else, is a machine's own CLAUDE.md and is
# never touched. `rm` on a symlink removes the link, not its target.
#
# run_once_: runs once per machine.
set -uo pipefail

link="$HOME/.claude/CLAUDE.md"

if [ ! -L "$link" ]; then
    exit 0
fi

target="$(readlink -- "$link")"

case "$target" in
    */agent-rules/python.md | agent-rules/python.md) ;;
    *) exit 0 ;;
esac

echo "== claude: removing old CLAUDE.md symlink -> $target =="
rm -- "$link"

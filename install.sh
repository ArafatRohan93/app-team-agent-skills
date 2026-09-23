#!/usr/bin/env bash
# Links every skill in this repo into each agent's skills folder.
# Re-run after pulling if new skills were added.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"

# Add your agent's skills folder here if it's missing.
AGENT_DIRS=(
  "$HOME/.claude/skills"   # Claude Code
  "$HOME/.codex/skills"    # OpenAI Codex CLI
  "$HOME/.agents/skills"   # generic location used by several agents
)

for skill in "$REPO"/plugins/*/skills/*/; do
  skill="${skill%/}"
  name="$(basename "$skill")"
  for dir in "${AGENT_DIRS[@]}"; do
    target="$dir/$name"
    mkdir -p "$dir"
    if [[ -e "$target" && ! -L "$target" ]]; then
      echo "skip  $target exists and is a real folder. Remove it, then re-run."
      continue
    fi
    ln -sfn "$skill" "$target"
    echo "link  $target → $skill"
  done
done

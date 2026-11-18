#!/usr/bin/env bash
# Installs agent-statusline and points Claude Code and Antigravity at it.
# Idempotent: re-run any time. Each settings file is backed up before it is changed.
#   ./install.sh [--theme NAME] [--no-claude] [--no-agy]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$REPO/bin/agent-statusline"
THEME=""
DO_CLAUDE=1
DO_AGY=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --theme) THEME="$2"; shift 2 ;;
    --no-claude) DO_CLAUDE=0; shift ;;
    --no-agy) DO_AGY=0; shift ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
chmod +x "$BIN"

mkdir -p "$HOME/.local/bin"
ln -sf "$BIN" "$HOME/.local/bin/agent-statusline"
echo "linked ~/.local/bin/agent-statusline"

CONFIG="${AGENT_STATUSLINE_CONFIG:-$HOME/.config/agent-statusline/config.json}"
if [[ -n "$THEME" ]]; then
  "$BIN" theme "$THEME"
elif [[ ! -f "$CONFIG" ]]; then
  "$BIN" theme powerline >/dev/null
  echo "theme: powerline"
fi

# set_status_line <settings.json> <tool> : writes statusLine.command, keeping the file's other keys
set_status_line() {
  local file="$1" tool="$2"
  cp "$file" "$file.bak-agent-statusline"
  python3 - "$file" "$tool" "$BIN" <<'EOF'
import json, sys
path, tool, bin_path = sys.argv[1:]
with open(path) as f:
    settings = json.load(f)
line = settings.get("statusLine") if isinstance(settings.get("statusLine"), dict) else {}
line["command"] = f"{bin_path} render --tool {tool}"
if tool == "claude":
    line.update({"type": "command", "padding": 0})
else:
    line["enabled"] = True
settings["statusLine"] = line
with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
EOF
  echo "configured $tool statusline in $file (backup: $file.bak-agent-statusline)"
}

if [[ $DO_CLAUDE == 1 ]]; then
  CLAUDE_SETTINGS="$HOME/.claude/settings.json"
  mkdir -p "$HOME/.claude/commands"
  [[ -f "$CLAUDE_SETTINGS" ]] || echo "{}" > "$CLAUDE_SETTINGS"
  set_status_line "$CLAUDE_SETTINGS" claude
  ln -sf "$REPO/integrations/claude/statusline-theme.md" "$HOME/.claude/commands/statusline-theme.md"
  echo "added /statusline-theme command to Claude Code"
fi

if [[ $DO_AGY == 1 ]]; then
  AGY_SETTINGS="$HOME/.gemini/antigravity-cli/settings.json"
  if [[ -f "$AGY_SETTINGS" ]]; then
    set_status_line "$AGY_SETTINGS" agy
  else
    echo "skipped Antigravity: $AGY_SETTINGS not found"
  fi
fi

echo "done. Switch looks with: agent-statusline theme <powerline|capsule|minimal|classic>"

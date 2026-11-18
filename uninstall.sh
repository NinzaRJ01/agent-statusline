#!/usr/bin/env bash
# Removes agent-statusline from Claude Code and Antigravity settings.
# Only touches a statusLine entry that points at agent-statusline; your config file is kept.
set -euo pipefail

unset_status_line() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  python3 - "$file" <<'EOF'
import json, sys
path = sys.argv[1]
with open(path) as f:
    settings = json.load(f)
line = settings.get("statusLine")
if isinstance(line, dict) and "agent-statusline" in str(line.get("command", "")):
    del settings["statusLine"]
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    print(f"removed statusLine from {path}")
EOF
}

unset_status_line "$HOME/.claude/settings.json"
unset_status_line "$HOME/.gemini/antigravity-cli/settings.json"
rm -f "$HOME/.local/bin/agent-statusline" "$HOME/.claude/commands/statusline-theme.md"
echo "done. Backups from install are next to each settings file as *.bak-agent-statusline."

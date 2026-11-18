"""Theme selection: env var, then per-tool setting, then global setting, then the default."""

import json
import os

from .themes import DEFAULT_THEME, THEMES


def config_path():
    return os.environ.get("AGENT_STATUSLINE_CONFIG") or os.path.expanduser("~/.config/agent-statusline/config.json")


def load():
    try:
        with open(config_path()) as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def save(cfg):
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def theme_for(tool, cfg=None):
    cfg = load() if cfg is None else cfg
    candidates = [
        os.environ.get("AGENT_STATUSLINE_THEME"),
        ((cfg.get("tools") or {}).get(tool) or {}).get("theme"),
        cfg.get("theme"),
    ]
    return next((t for t in candidates if t in THEMES), DEFAULT_THEME)


def set_theme(theme, tool=None):
    if theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r}; choose from {', '.join(THEMES)}")
    cfg = load()
    if tool:
        cfg.setdefault("tools", {}).setdefault(tool, {})["theme"] = theme
    else:
        cfg["theme"] = theme
        # A global switch should apply everywhere, so drop per-tool overrides
        for entry in (cfg.get("tools") or {}).values():
            entry.pop("theme", None)
    save(cfg)
    return cfg

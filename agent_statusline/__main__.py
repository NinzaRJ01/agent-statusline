"""
agent-statusline render --tool claude|agy     read stdin JSON, print the statusline
agent-statusline theme [NAME] [--tool TOOL]   show or switch the theme
agent-statusline preview [--width N]          print every theme with sample data
"""

import argparse
import json
import os
import shutil
import sys
import traceback

from . import config
from .adapters import ADAPTERS
from .samples import SAMPLES
from .themes import THEMES, render

CACHE_DIR = os.environ.get("AGENT_STATUSLINE_CACHE") or os.path.expanduser("~/.cache/agent-statusline")


def _log(name, text):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, name), "w") as f:
            f.write(text)
    except Exception:
        pass


def cmd_render(args):
    # Must never crash or print a traceback into the host CLI's status area
    raw = ""
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            return 0
        if os.environ.get("AGENT_STATUSLINE_DEBUG"):
            _log(f"last-input-{args.tool}.json", raw)
        data = json.loads(raw)
        if not isinstance(data, dict):
            return 0
        metrics, width = ADAPTERS[args.tool](data)
        theme = args.theme if args.theme in THEMES else config.theme_for(args.tool)
        print("\n".join(render(metrics, theme, width)))
    except Exception:
        # Keep the input that failed: hosts change their JSON shape between versions
        _log("error.log", traceback.format_exc())
        _log(f"error-input-{args.tool}.json", raw)
    return 0


def cmd_theme(args):
    if args.name:
        try:
            config.set_theme(args.name, args.tool)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 1
        where = args.tool or "all tools"
        print(f"Statusline theme set to {args.name} for {where}. It applies on the next refresh.")
        return 0

    cfg = config.load()
    for tool in ADAPTERS:
        print(f"{tool}: {config.theme_for(tool, cfg)}")
    print("available: " + ", ".join(THEMES))
    return 0


def cmd_preview(args):
    tools = [args.tool] if args.tool else list(SAMPLES)
    themes = [args.theme] if args.theme else list(THEMES)
    for theme in themes:
        print(f"\n\033[1m{theme}\033[0m")
        for tool in tools:
            for state in ("normal", "busy"):
                print("\n".join(render(SAMPLES[tool][state], theme, args.width)))
                print()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agent-statusline", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("render", help="read a tool's statusline JSON on stdin and print the statusline")
    p.add_argument("--tool", choices=list(ADAPTERS), required=True)
    p.add_argument("--theme", help="override the configured theme")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("theme", help="show or switch the theme")
    p.add_argument("name", nargs="?", help=", ".join(THEMES))
    p.add_argument("--tool", choices=list(ADAPTERS), help="only change this tool")
    p.set_defaults(func=cmd_theme)

    p = sub.add_parser("preview", help="print every theme with sample data")
    p.add_argument("--width", type=int, default=shutil.get_terminal_size((150, 24)).columns)
    p.add_argument("--tool", choices=list(ADAPTERS))
    p.add_argument("--theme", choices=list(THEMES))
    p.set_defaults(func=cmd_preview)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

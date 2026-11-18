"""
Render docs/themes.png: every theme for both tools, from the sample sessions.
Needs Google Chrome. Pass --nerd-font with a Symbols Nerd Font .ttf/.woff2 so icons show.
  python3 tools/screenshot.py --nerd-font ~/Downloads/SymbolsNerdFontMono-Regular.ttf
"""

import argparse
import base64
import html
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent_statusline.samples import SAMPLES  # noqa: E402
from agent_statusline.themes import THEMES, render  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH = 150


def ansi_to_html(line):
    out, state = [], {}
    for chunk in re.split(r"(\033\[[0-9;]*m)", line):
        if chunk.startswith("\033["):
            codes = [int(c) if c else 0 for c in chunk[2:-1].split(";")]
            i = 0
            while i < len(codes):
                c = codes[i]
                if c == 0:
                    state = {}
                elif c == 1:
                    state["bold"] = True
                elif c == 22:
                    state.pop("bold", None)
                elif c in (38, 48) and codes[i + 1:i + 2] == [2]:
                    state["color" if c == 38 else "background"] = "#%02x%02x%02x" % tuple(codes[i + 2:i + 5])
                    i += 4
                i += 1
        elif chunk:
            css = ";".join(f"{k}:{v}" for k, v in state.items() if k != "bold")
            if state.get("bold"):
                css += ";font-weight:700"
            out.append(f'<span style="{css}">{html.escape(chunk)}</span>')
    return "".join(out)


def page(font_css):
    rows = []
    for theme in THEMES:
        lines = [l for tool in ("claude", "agy") for l in render(SAMPLES[tool]["normal"], theme, WIDTH)]
        rows.append(f'<div class="name">{theme}</div><pre>{"<br>".join(ansi_to_html(l) for l in lines)}</pre>')
    return f"""<!doctype html><meta charset="utf-8"><style>{font_css}
body {{ margin: 0; background: #15171c; padding: 24px 28px; font-family: "JetBrains Mono", "NF", Menlo, monospace; }}
.name {{ color: #7d8597; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; margin: 18px 0 8px; }}
.name:first-child {{ margin-top: 0; }}
pre {{ margin: 0; font-size: 13px; line-height: 1.75; font-family: inherit; color: #e6e9ef; }}
pre span {{ font-family: inherit; }}
</style>{''.join(rows)}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nerd-font", help="path to a Symbols Nerd Font file to embed")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "themes.png"))
    args = ap.parse_args()

    font_css = ""
    if args.nerd_font:
        with open(os.path.expanduser(args.nerd_font), "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        fmt = "woff2" if args.nerd_font.endswith(".woff2") else "truetype"
        font_css = f'@font-face {{ font-family: "NF"; src: url(data:font/{fmt};base64,{b64}) format("{fmt}"); }}'

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(page(font_css))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    height = 40 + sum(44 + 23 * sum(len(render(SAMPLES[t]["normal"], th, WIDTH)) for t in SAMPLES) for th in THEMES)
    subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--virtual-time-budget=3000", "--force-device-scale-factor=2",
                    f"--window-size=1260,{height}", f"--screenshot={args.out}", f"file://{f.name}"],
                   check=True, capture_output=True)
    os.unlink(f.name)
    print(args.out)


if __name__ == "__main__":
    main()

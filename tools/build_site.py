"""
Build the GitHub Pages site in docs/ from the real renderer, so the page always matches the CLI.
  python3 tools/build_site.py [--nerd-font path/to/SymbolsNerdFontMono-Regular.ttf]
--nerd-font regenerates docs/assets/nf-symbols.woff2 (needs `pip install fonttools brotli`).
"""

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent_statusline import __version__  # noqa: E402
from agent_statusline.samples import SAMPLES  # noqa: E402
from agent_statusline.themes import NERD_GLYPHS, THEMES, render  # noqa: E402
from ansi_html import ansi_to_html  # noqa: E402

WIDTHS = {"wide": 150, "narrow": 72}
DOCS = os.path.join(ROOT, "docs")
FONT_OUT = os.path.join(DOCS, "assets", "nf-symbols.woff2")


def build_data():
    data = {}
    for theme in THEMES:
        data[theme] = {}
        for tool, states in SAMPLES.items():
            data[theme][tool] = {
                f"{wname}-{state}": "\n".join(ansi_to_html(l) for l in render(m, theme, width))
                for wname, width in WIDTHS.items()
                for state, m in states.items()
            }
            # The hero card is about 130 columns wide on desktop
            data[theme][tool]["hero"] = "\n".join(ansi_to_html(l) for l in render(states["normal"], theme, 130))
    return data


def subset_font(src):
    os.makedirs(os.path.dirname(FONT_OUT), exist_ok=True)
    unicodes = ",".join("U+%04X" % ord(g) for g in sorted(NERD_GLYPHS))
    subprocess.run([sys.executable, "-m", "fontTools.subset", os.path.expanduser(src), f"--unicodes={unicodes}",
                    "--flavor=woff2", f"--output-file={FONT_OUT}"], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nerd-font", help="Symbols Nerd Font to subset into docs/assets")
    args = ap.parse_args()
    if args.nerd_font:
        subset_font(args.nerd_font)

    with open(os.path.join(ROOT, "tools", "site_template.html")) as f:
        page = f.read()
    page = page.replace("__VERSION__", __version__).replace("__DATA_JSON__", json.dumps(build_data()))
    with open(os.path.join(DOCS, "index.html"), "w") as f:
        f.write(page)
    # Serve the folder as-is, without Jekyll processing
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    print(os.path.join(DOCS, "index.html"))


if __name__ == "__main__":
    main()

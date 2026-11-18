"""Convert the truecolor ANSI that themes.render() prints into HTML spans."""

import html
import re


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

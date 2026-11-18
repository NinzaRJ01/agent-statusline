"""
Statusline themes shared by every supported agent CLI.

An adapter turns a tool's stdin JSON into a metrics dict, then render(metrics, theme, width)
returns the 1-3 lines to print. All themes except "classic" need a truecolor terminal and a
Nerd Font (Ghostty bundles the symbols; elsewhere install any Nerd Font).
"""

import re

RST = "\033[0m"
BOLD = "\033[1m"
NORMAL = "\033[22m"

PAL = {
    "text": "#e6e9ef",
    "muted": "#7d8597",
    "faint": "#3a404d",
    "surface": "#262b35",
    "surface2": "#323846",
    "ink": "#16181d",
    "green": "#8fd3a3",
    "amber": "#f0c674",
    "red": "#ef7b7b",
    "violet": "#b8a1f2",
    "cyan": "#7fc8e6",
}
ACCENT = {"claude": "#d97757", "agy": "#6c9cf7"}

# Nerd Font glyphs
PL_RIGHT, ROUND_L, ROUND_R = "", "", ""
I_MODEL = {"claude": "\U000f06a9", "agy": "\U000f0463"}
I_CTX, I_CACHE, I_BRANCH, I_FOLDER = "\U000f035b", "", "", ""
I_EDIT, I_QUOTA, I_COST, I_AGENTS, I_ARTS, I_BELL = "", "", "", "", "", ""
NERD_GLYPHS = {PL_RIGHT, ROUND_L, ROUND_R, I_CTX, I_CACHE, I_BRANCH, I_FOLDER, I_EDIT, I_QUOTA, I_COST,
               I_AGENTS, I_ARTS, I_BELL, *I_MODEL.values()}

# Classic theme: emoji + text labels, no Nerd Font required
CLASSIC = {
    "model": ("⚡", "Model"), "ctx": ("📊", "Ctx"), "cache": ("", ""), "approval": ("🔔", "Waiting"),
    "git": ("🌿", "Git"), "dir": ("📁", ""), "edits": ("✏️", "Edits"), "quota": ("⏳", "Quota"),
    "cost": ("💰", "Cost"), "agent": ("🤖", "Agent"), "agents": ("🤖", "Agents"), "arts": ("📦", "Arts"),
}


def _rgb(h):
    h = PAL.get(h, h).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def fg(h):
    return "\033[38;2;%d;%d;%dm" % _rgb(h)


def bg(h):
    return "\033[48;2;%d;%d;%dm" % _rgb(h)


def blend(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def visible_len(s):
    plain = re.sub(r"\033\[[0-9;]*m", "", s)
    # Emoji render two cells wide; Nerd Font glyphs (private use area) render one
    return len(plain) + sum(1 for ch in plain if 0x1F300 <= ord(ch) <= 0x1FAFF)


def fmt_tokens(n):
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def level(pct):
    return "green" if pct < 60 else "amber" if pct < 80 else "red"


def left_level(left):
    return "red" if left < 20 else "amber" if left < 50 else "green"


class Seg:
    def __init__(self, key, icon, parts, tone, row):
        self.key, self.icon, self.parts, self.tone, self.row = key, icon, parts, tone, row


def segments(m, bar):
    """Turn normalized metrics into theme-neutral segments. parts: (text, color, bold)."""
    tool = m["tool"]
    segs = []

    parts = [(str(m["model"]), "text", True)]
    if isinstance(m.get("effort"), str) and m["effort"]:
        parts.append((" " + m["effort"], "muted", False))
    if isinstance(m.get("mode"), str) and m["mode"]:
        parts.append((" " + m["mode"].lower(), "muted", False))
    segs.append(Seg("model", I_MODEL.get(tool, I_MODEL["claude"]), parts, ACCENT.get(tool, ACCENT["claude"]), 1))

    pct = m.get("ctx_pct") or 0
    lc = level(pct)
    parts = bar(pct) + [(f" {pct:.0f}%", lc, True)]
    if m.get("ctx_tokens"):
        size = f"/{fmt_tokens(m['ctx_max'])}" if m.get("ctx_max") else ""
        parts.append((f" {fmt_tokens(m['ctx_tokens'])}{size}", "muted", False))
    segs.append(Seg("ctx", I_CTX, parts, lc, 1))

    if m.get("cache_pct") is not None:
        segs.append(Seg("cache", I_CACHE, [(f"{m['cache_pct']:.0f}%", "text", False), (" cached", "muted", False)], "cyan", 1))
    if m.get("approval"):
        segs.append(Seg("approval", I_BELL, [("approve tool", "amber", True)], "amber", 2))

    git = m.get("git")
    if git:
        parts = [(git["branch"] + ("*" if git["dirty"] else ""), "text", False)]
        if git.get("ins"):
            parts.append((f" +{git['ins']}", "green", False))
        if git.get("dels"):
            parts.append((f" -{git['dels']}", "red", False))
        if not git.get("ins") and not git.get("dels") and git.get("untracked"):
            parts.append((f" ?{git['untracked']}", "amber", False))
        segs.append(Seg("git", I_BRANCH, parts, "violet", 2))
    elif m.get("folder"):
        segs.append(Seg("dir", I_FOLDER, [(m["folder"], "text", False)], "violet", 2))

    if m.get("edits"):
        a, r = m["edits"]
        segs.append(Seg("edits", I_EDIT, [(f"+{a}", "green", False), (f" -{r}", "red", False)], "muted", 2))

    if m.get("quota"):
        parts = []
        for i, (label, left) in enumerate(m["quota"]):
            parts += [((" " if i else "") + f"{left:.0f}%", left_level(left), False), (f" {label}", "muted", False)]
        worst = min(left for _, left in m["quota"])
        segs.append(Seg("quota", I_QUOTA, parts, left_level(worst), 2))

    if m.get("cost"):
        cost = m["cost"]
        parts = [(f"${cost:.2f}" if cost >= 1 else f"${cost:.3f}", "text", False)]
        if m.get("minutes"):
            mins = m["minutes"]
            parts.append((f" {mins // 60}h{mins % 60:02d}m" if mins >= 60 else f" {mins}m", "muted", False))
        segs.append(Seg("cost", I_COST, parts, "amber", 2))

    if m.get("agent_name"):
        segs.append(Seg("agent", I_AGENTS, [(m["agent_name"], "text", False)], "violet", 2))
    if m.get("agents"):
        segs.append(Seg("agents", I_AGENTS, [(str(m["agents"]), "text", False), (" agents", "muted", False)], "violet", 2))
    if m.get("arts"):
        segs.append(Seg("arts", I_ARTS, [(str(m["arts"]), "text", False), (" artifacts", "muted", False)], "cyan", 2))
    return segs


def _parts(parts, override=None):
    out = ""
    for text, color, bold in parts:
        c = (override or {}).get(color, color)
        out += (BOLD if bold else "") + fg(c) + text + (NORMAL if bold else "")
    return out


def _on_accent(acc):
    return {"text": PAL["ink"], "muted": blend(acc, PAL["ink"], 0.55)}


# ---------------------------------------------------------------- Powerline
# Connected arrow segments that step from the accent down to the surface tones.

def powerline_bar(pct):
    cells, eighths = 8, " ▏▎▍▌▋▊▉█"
    fill = max(0.0, min(pct, 100)) / 100 * cells
    full = int(fill)
    part = eighths[int((fill - full) * 8)].strip() if full < cells else ""
    rest = cells - full - len(part)
    return [("█" * full + part, level(pct), False), ("·" * rest, "faint", False)]


def powerline_line(segs, tool):
    acc = ACCENT.get(tool, ACCENT["claude"])
    out, prev = "", None
    tones = ["surface2", "surface"]
    for i, s in enumerate(segs):
        seg_bg = acc if s.key == "model" else tones[i % 2]
        if prev is not None:
            out += bg(seg_bg) + fg(prev) + PL_RIGHT
        if s.key == "model":
            out += bg(seg_bg) + fg("ink") + " " + s.icon + " " + _parts(s.parts, _on_accent(acc)) + " "
        else:
            out += bg(seg_bg) + " " + fg(s.tone) + s.icon + " " + _parts(s.parts) + " "
        prev = seg_bg
    return out + RST + fg(prev) + PL_RIGHT + RST


# ---------------------------------------------------------------- Capsule
# Rounded pills; the model pill is filled with the tool's accent color.

def capsule_bar(pct):
    filled = min(5, max(0, round(pct / 20)))
    return [("▰" * filled, level(pct), False), ("▱" * (5 - filled), "faint", False)]


def capsule_line(segs, tool):
    acc = ACCENT.get(tool, ACCENT["claude"])
    pills = []
    for s in segs:
        if s.key == "model":
            body = bg(acc) + fg("ink") + s.icon + " " + _parts(s.parts, _on_accent(acc))
            pills.append(fg(acc) + ROUND_L + body + " " + RST + fg(acc) + ROUND_R + RST)
        else:
            body = bg("surface") + fg(s.tone) + s.icon + " " + _parts(s.parts)
            pills.append(fg("surface") + ROUND_L + body + " " + RST + fg("surface") + ROUND_R + RST)
    return " ".join(pills)


# ---------------------------------------------------------------- Minimal
# No backgrounds: colored icons, quiet labels, a gradient context track.

def minimal_bar(pct):
    cells = 10
    filled = min(cells, max(0, round(pct / 100 * cells)))
    out = []
    for i in range(filled):
        t = i / (cells - 1)
        color = blend("green", "amber", t * 2) if t < 0.5 else blend("amber", "red", (t - 0.5) * 2)
        out.append(("━", color, False))
    out.append(("─" * (cells - filled), "faint", False))
    return out


def minimal_line(segs, tool):
    items = []
    for s in segs:
        tone = ACCENT.get(tool, ACCENT["claude"]) if s.key == "model" else s.tone
        items.append(fg(tone) + s.icon + " " + _parts(s.parts) + RST)
    return "   ".join(items)


# ---------------------------------------------------------------- Classic
# The original look: emoji, text labels and separators. Works without a Nerd Font.

def classic_bar(pct):
    filled = min(5, max(0, round(pct / 20)))
    return [("[" + "■" * filled + "□" * (5 - filled) + "]", level(pct), False)]


def classic_line(segs, tool):
    items = []
    for s in segs:
        emoji, label = CLASSIC.get(s.key, ("", ""))
        tone = ACCENT.get(tool, ACCENT["claude"]) if s.key == "model" else s.tone
        head = " ".join(x for x in (emoji, label + ":" if label else "") if x)
        items.append(fg(tone) + (head + " " if head else "") + _parts(s.parts) + RST)
    return f" {fg('faint')}│{RST} ".join(items)


THEMES = {
    "powerline": (powerline_bar, powerline_line),
    "capsule": (capsule_bar, capsule_line),
    "minimal": (minimal_bar, minimal_line),
    "classic": (classic_bar, classic_line),
}
DEFAULT_THEME = "powerline"


def render(m, theme, width):
    """Returns 1-3 lines: one line if it fits, else AI row + environment row, else each row wrapped."""
    bar, line = THEMES.get(theme, THEMES[DEFAULT_THEME])
    segs = segments(m, bar)
    tool = m["tool"]

    one = line(segs, tool)
    if visible_len(one) <= width:
        return [one]

    rows = [[s for s in segs if s.row == r] for r in (1, 2)]
    rendered = [line(r, tool) for r in rows if r]
    if all(visible_len(r) <= width for r in rendered):
        return rendered

    # Wrap each row on its own so AI and environment metrics never share a line
    lines = []
    for row in rows:
        curr = []
        for s in row:
            if curr and visible_len(line(curr + [s], tool)) > width:
                lines.append(line(curr, tool))
                curr = []
            curr.append(s)
        if curr:
            lines.append(line(curr, tool))
    return lines[:3]

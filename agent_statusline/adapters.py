"""Turn each tool's statusline stdin JSON into the metrics dict that themes.render() takes."""

import json
import os
import re
import subprocess

CLAUDE_SETTINGS = os.path.expanduser("~/.claude/settings.json")


def _git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=0.08)


def git_info(cwd):
    """Branch, dirty flag and uncommitted churn for cwd; None outside a git work tree."""
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        chk = _git(cwd, "rev-parse", "--is-inside-work-tree")
        if chk.returncode != 0 or chk.stdout.strip() != "true":
            return None

        branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "HEAD"
        if branch == "HEAD":
            branch = f":{_git(cwd, 'rev-parse', '--short', 'HEAD').stdout.strip()}"

        d_res = _git(cwd, "diff", "HEAD", "--shortstat")
        diff_out = d_res.stdout.strip()
        if not diff_out and d_res.returncode != 0:
            diff_out = _git(cwd, "diff", "--shortstat").stdout.strip()

        status_lines = _git(cwd, "status", "--porcelain").stdout.strip().splitlines()
        m_ins = re.search(r"(\d+) insertion", diff_out)
        m_del = re.search(r"(\d+) deletion", diff_out)
        return {
            "branch": branch,
            "dirty": bool(status_lines),
            "ins": int(m_ins.group(1)) if m_ins else 0,
            "dels": int(m_del.group(1)) if m_del else 0,
            "untracked": sum(1 for l in status_lines if l.startswith("??")),
        }
    except Exception:
        return None


def _workspace(m, cwd):
    m["git"] = git_info(cwd)
    if not m["git"] and cwd:
        m["folder"] = os.path.basename(cwd.rstrip("/")) or cwd


def _tty_width():
    if os.environ.get("COLUMNS"):
        try:
            return int(os.environ["COLUMNS"])
        except ValueError:
            pass
    try:
        with open("/dev/tty") as tty:
            return os.get_terminal_size(tty.fileno()).columns
    except Exception:
        return 120


def _cache_pct(usage):
    read = usage.get("cache_read_input_tokens") or 0
    total = read + (usage.get("cache_creation_input_tokens") or 0) + (usage.get("input_tokens") or 0)
    return read / total * 100 if read and total else None


# ---------------------------------------------------------------- Claude Code

def _claude_effort(model_id):
    """Claude Code doesn't send effort on stdin; fall back to settings.json."""
    try:
        with open(CLAUDE_SETTINGS) as f:
            settings = json.load(f)
        per_model = (settings.get("modelSettings") or {}).get(model_id) or {}
        return per_model.get("effortLevel") or settings.get("effortLevel")
    except Exception:
        return None


def claude(data):
    model = data.get("model") or {}
    name = (model.get("display_name") or model.get("id") or "Claude").replace("Claude ", "").strip()
    m = {"tool": "claude", "model": name or "Claude"}

    m["effort"] = data.get("effort") or model.get("effort") or _claude_effort(model.get("id"))
    mode = data.get("permission_mode")
    if mode and mode != "default":
        m["mode"] = mode

    # current_usage is the live window fill; total_* counters are cumulative
    cw = data.get("context_window") or {}
    usage = cw.get("current_usage") or {}
    m["ctx_max"] = cw.get("context_window_size") or 200_000
    tokens = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    if cw.get("used_percentage") is not None:
        m["ctx_pct"] = float(cw["used_percentage"])
    else:
        m["ctx_pct"] = tokens / m["ctx_max"] * 100
    m["ctx_tokens"] = tokens or int(m["ctx_pct"] / 100 * m["ctx_max"])
    m["cache_pct"] = _cache_pct(usage)

    _workspace(m, data.get("cwd") or (data.get("workspace") or {}).get("current_dir") or os.getcwd())

    cost = data.get("cost") or {}
    added, removed = cost.get("total_lines_added") or 0, cost.get("total_lines_removed") or 0
    if added or removed:
        m["edits"] = (added, removed)
    m["cost"] = float(cost.get("total_cost_usd") or 0)
    m["minutes"] = int((cost.get("total_duration_ms") or 0) // 60000)

    limits = data.get("rate_limits") or {}
    quota = []
    for key, label in (("five_hour", "5h"), ("seven_day", "7d")):
        bucket = limits.get(key)
        if isinstance(bucket, dict) and bucket.get("used_percentage") is not None:
            quota.append((label, 100 - float(bucket["used_percentage"])))
    m["quota"] = quota

    m["agent_name"] = (data.get("agent") or {}).get("name")
    # Claude Code pads the status area, so leave a small margin
    return m, max(40, _tty_width() - 4)


# ---------------------------------------------------------------- Antigravity

def _agy_model(val):
    if isinstance(val, dict):
        val = (val.get("display_name") or val.get("name") or val.get("label") or val.get("model_id")
               or val.get("id") or val.get("title") or "")
    if not isinstance(val, str) or not val:
        return "Gemini", None
    effort = None
    m = re.search(r"\s*\((High|Medium|Low)\)\s*$", val, re.I)
    if m:
        effort, val = m.group(1).lower(), val[:m.start()]
    return val.replace("Gemini ", "").strip() or "Gemini", effort


def _agy_quota(quota):
    if isinstance(quota, dict):
        g5h = quota.get("gemini-5h")
        if isinstance(g5h, dict) and "remaining_fraction" in g5h:
            return [("5h", g5h["remaining_fraction"] * 100)]
    elif isinstance(quota, list):
        for bucket in quota:
            if not isinstance(bucket, dict):
                continue
            left = bucket.get("percentage_remaining") or bucket.get("remaining")
            name = str(bucket.get("display_name") or bucket.get("name") or "")
            if left is not None and ("5" in name or "five" in name.lower()):
                return [("5h", float(left))]
    return []


def agy(data):
    raw_model = data.get("model")
    name, effort_from_name = _agy_model(raw_model)
    m = {"tool": "agy", "model": name}
    effort = data.get("effort") or (raw_model.get("effort") if isinstance(raw_model, dict) else None)
    m["effort"] = effort if isinstance(effort, str) and effort else effort_from_name
    mode = data.get("editorMode") or data.get("agent_state") or "auto"
    m["mode"] = mode.upper() if isinstance(mode, str) else "AUTO"

    cw = data.get("context_window") or {}
    total = (cw.get("total_input_tokens") or 0) + (cw.get("total_output_tokens") or 0) or (data.get("total_tokens") or 0)
    m["ctx_max"] = cw.get("context_window_size") or 1_048_576
    m["ctx_tokens"] = total
    if cw.get("used_percentage") is not None:
        m["ctx_pct"] = float(cw["used_percentage"])
    else:
        m["ctx_pct"] = total / m["ctx_max"] * 100 if total else 0.0
    m["cache_pct"] = _cache_pct(cw.get("current_usage") or {})
    m["approval"] = bool(data.get("tool_confirmation_pending"))

    _workspace(m, data.get("cwd") or (data.get("workspace") or {}).get("current_dir") or os.getcwd())
    m["quota"] = _agy_quota(data.get("quota"))

    try:
        m["cost"] = float(data.get("total_usd") or 0)
    except (TypeError, ValueError):
        m["cost"] = 0.0
    try:
        m["arts"] = int(data.get("artifact_count") or 0)
    except (TypeError, ValueError):
        m["arts"] = 0
    subagents = data.get("subagents")
    m["agents"] = len(subagents) if isinstance(subagents, list) else subagents if isinstance(subagents, int) else 0

    try:
        width = int(data.get("terminal_width") or 80)
    except (TypeError, ValueError):
        width = 80
    return m, width


ADAPTERS = {"claude": claude, "agy": agy}

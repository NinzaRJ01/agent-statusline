"""Example sessions used by `agent-statusline preview` and the tests."""

SAMPLES = {
    "claude": {
        "normal": dict(tool="claude", model="Opus 5.5", effort="medium", ctx_pct=34, ctx_tokens=68000,
                       ctx_max=200000, cache_pct=88, git=dict(branch="main", dirty=True, ins=14, dels=3),
                       edits=(42, 7), quota=[("5h", 82), ("7d", 45)], cost=0.4213, minutes=31),
        "busy": dict(tool="claude", model="Opus 5.5", effort="medium", ctx_pct=86, ctx_tokens=172000,
                     ctx_max=200000, cache_pct=91, git=dict(branch="main", dirty=True, ins=14, dels=3),
                     edits=(318, 96), quota=[("5h", 12), ("7d", 38)], cost=3.87, minutes=142),
    },
    "agy": {
        "normal": dict(tool="agy", model="3.8 Flash", effort="high", mode="AUTO", ctx_pct=26, ctx_tokens=275000,
                       ctx_max=1048576, cache_pct=99, git=dict(branch="main", dirty=True, ins=14, dels=3),
                       quota=[("5h", 92)], cost=0.035, arts=4, agents=2),
        "busy": dict(tool="agy", model="3.8 Flash", effort="high", mode="AUTO", ctx_pct=84, ctx_tokens=880000,
                     ctx_max=1048576, cache_pct=97, approval=True, git=dict(branch="main", dirty=True, ins=14, dels=3),
                     quota=[("5h", 15)], cost=0.41, arts=11, agents=3),
    },
}

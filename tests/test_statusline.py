import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent_statusline import adapters, config  # noqa: E402
from agent_statusline.samples import SAMPLES  # noqa: E402
from agent_statusline.themes import THEMES, render, visible_len  # noqa: E402

BIN = os.path.join(ROOT, "bin", "agent-statusline")


class RenderTest(unittest.TestCase):
    def test_every_theme_fits_width(self):
        for theme in THEMES:
            for tool, states in SAMPLES.items():
                for state, m in states.items():
                    for width in (200, 150, 100, 72, 60):
                        with self.subTest(theme=theme, tool=tool, state=state, width=width):
                            lines = render(m, theme, width)
                            self.assertTrue(1 <= len(lines) <= 3)
                            for line in lines:
                                self.assertLessEqual(visible_len(line), width)

    def test_wide_window_is_one_line(self):
        for theme in THEMES:
            self.assertEqual(len(render(SAMPLES["claude"]["normal"], theme, 200)), 1)

    def test_rows_keep_ai_metrics_first(self):
        lines = render(SAMPLES["claude"]["normal"], "powerline", 72)
        self.assertIn("Opus 5.5", lines[0])
        self.assertIn("main", lines[-1])

    def test_unknown_theme_falls_back(self):
        self.assertEqual(render(SAMPLES["agy"]["normal"], "nope", 200),
                         render(SAMPLES["agy"]["normal"], "powerline", 200))


class AdapterTest(unittest.TestCase):
    def test_claude_payload(self):
        m, _ = adapters.claude({
            "model": {"id": "claude-opus-5-5", "display_name": "Opus 5.5"},
            "cwd": "/nonexistent",
            "cost": {"total_cost_usd": 0.42, "total_duration_ms": 1_860_000,
                     "total_lines_added": 42, "total_lines_removed": 7},
            "context_window": {"context_window_size": 200000, "used_percentage": 34,
                               "current_usage": {"input_tokens": 1200, "cache_read_input_tokens": 60000,
                                                 "cache_creation_input_tokens": 6800}},
            "rate_limits": {"five_hour": {"used_percentage": 18}},
        })
        self.assertEqual(m["model"], "Opus 5.5")
        self.assertEqual(m["ctx_pct"], 34)
        self.assertEqual(m["ctx_tokens"], 68000)
        self.assertEqual(m["edits"], (42, 7))
        self.assertEqual(m["quota"], [("5h", 82)])
        self.assertEqual(m["minutes"], 31)

    def test_claude_effort_object(self):
        # Claude Code 2.1.x sends effort as an object
        m, _ = adapters.claude({"model": {"id": "x", "display_name": "Opus 5.5"}, "effort": {"level": "high"}})
        self.assertEqual(m["effort"], "high")
        self.assertTrue(render(m, "powerline", 200))

    def test_agy_model_string_with_effort(self):
        m, width = adapters.agy({"model": "Gemini 4 Hydrogen (High)", "terminal_width": 99,
                                 "quota": {"gemini-5h": {"remaining_fraction": 0.5}}, "subagents": [1, 2]})
        self.assertEqual((m["model"], m["effort"], width), ("4 Hydrogen", "high", 99))
        self.assertEqual(m["quota"], [("5h", 50)])
        self.assertEqual(m["agents"], 2)

    def test_empty_payloads_render(self):
        for tool, adapt in adapters.ADAPTERS.items():
            m, width = adapt({})
            self.assertTrue(render(m, "powerline", width))


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["AGENT_STATUSLINE_CONFIG"] = os.path.join(self.tmp.name, "config.json")
        os.environ.pop("AGENT_STATUSLINE_THEME", None)

    def tearDown(self):
        os.environ.pop("AGENT_STATUSLINE_CONFIG", None)
        self.tmp.cleanup()

    def test_default_is_powerline(self):
        self.assertEqual(config.theme_for("claude"), "powerline")

    def test_per_tool_override_and_global_reset(self):
        config.set_theme("minimal", "agy")
        self.assertEqual((config.theme_for("claude"), config.theme_for("agy")), ("powerline", "minimal"))
        config.set_theme("capsule")
        self.assertEqual((config.theme_for("claude"), config.theme_for("agy")), ("capsule", "capsule"))

    def test_env_wins(self):
        config.set_theme("capsule")
        os.environ["AGENT_STATUSLINE_THEME"] = "classic"
        try:
            self.assertEqual(config.theme_for("claude"), "classic")
        finally:
            del os.environ["AGENT_STATUSLINE_THEME"]

    def test_rejects_unknown_theme(self):
        with self.assertRaises(ValueError):
            config.set_theme("neon")


class CliTest(unittest.TestCase):
    def run_bin(self, *args, stdin=""):
        env = {**os.environ, "AGENT_STATUSLINE_CONFIG": os.path.join(tempfile.gettempdir(), "asl-test.json"),
               "COLUMNS": "200", "AGENT_STATUSLINE_CACHE": tempfile.mkdtemp()}
        return subprocess.run([sys.executable, BIN, *args], input=stdin, capture_output=True, text=True, env=env)

    def test_bad_input_never_fails(self):
        for stdin in ("", "not json", "[]", '{"model": 5}'):
            res = self.run_bin("render", "--tool", "claude", stdin=stdin)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stderr, "")
            self.assertTrue(res.stdout.strip() or stdin in ("", "not json", "[]"), f"no output for {stdin!r}")

    def test_render_from_stdin(self):
        res = self.run_bin("render", "--tool", "agy", "--theme", "classic",
                           stdin=json.dumps({"model": "Gemini 3.8 Flash", "terminal_width": 200}))
        self.assertIn("Model: 3.8 Flash", re.sub(r"\033\[[0-9;]*m", "", res.stdout))


if __name__ == "__main__":
    unittest.main()

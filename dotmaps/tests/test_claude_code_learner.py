"""Q7 gate: ClaudeCodeLearner — offline-testable parts only. The live path
(shelling to the real `claude` CLI) is subscription-billed and network-
dependent; it was verified manually during Q7's diagnosis (see
QUEEN_FLIGHT_LOG.md), not by an automated test — same convention as
test_ollama_driver.py's offline-parsing-only coverage."""
import os
from unittest.mock import patch

from dotmaps.grow.learner import ClaudeCodeLearner, _extract_move


def test_extract_move_parses_bare_json():
    assert _extract_move('{"poke": {"tool": "filesystem.read_file", "args": {"path": "a"}}}'
                         ) == {"poke": {"tool": "filesystem.read_file", "args": {"path": "a"}}}


def test_extract_move_none_on_unparseable():
    assert _extract_move("not json at all") is None


def test_system_prompt_forbids_tools_and_prose():
    """The Q7 fix: --system-prompt REPLACES Claude Code's default agentic
    persona (which reaches for a tool on turn 1 even with common tools
    disallowed, burning the --max-turns 1 budget before any text)."""
    sp = ClaudeCodeLearner.SYSTEM_PROMPT.lower()
    assert "no tools" in sp
    assert "json" in sp


def test_next_move_strips_anthropic_api_key_from_subprocess_env():
    """Money law: a present ANTHROPIC_API_KEY must never reach the
    subprocess — it would silently switch billing from subscription to
    metered API. Mocked, no live call."""
    captured = {}

    def fake_run(cmd, input, capture_output, text, timeout, env):
        captured["env"] = env
        captured["cmd"] = cmd

        class R:
            stdout = '{"result": "{\\"rest\\": true}", "total_cost_usd": 0}'
        return R()

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-should-never-be-used"}):
        with patch("subprocess.run", side_effect=fake_run):
            learner = ClaudeCodeLearner()
            learner.next_move("board text")

    assert "ANTHROPIC_API_KEY" not in captured["env"]
    assert "--system-prompt" in captured["cmd"]

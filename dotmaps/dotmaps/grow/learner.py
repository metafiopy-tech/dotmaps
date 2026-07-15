"""The learner — swappable, like the traveler (same design bet).

Interface: next_move(board) -> one of
    {"poke":    {"tool": ..., "args": {...}}}
    {"propose": {"statement": ..., "steps": [...], "expect": {...}}}
    {"revise":  {...same shape as propose...}}   # FORAGE answer for a hypothesis
    {"rest":    true}                            # nothing more to try

`board` is the rule-2-disciplined context: the frozen directive, banked rule
statements, open hypotheses, a short journal tail, budget counters. Never the
full journal.

ScriptedLearner replays a fixed move list — the whole wheel is testable
without a model. OllamaLearner is the $0 learner the thesis bets on.
"""
from __future__ import annotations

import json
import re
from typing import Any


class ScriptedLearner:
    def __init__(self, moves: list[dict[str, Any]]):
        self._moves = list(moves)

    def next_move(self, board: str) -> dict[str, Any]:
        return self._moves.pop(0) if self._moves else {"rest": True}


MOVE_FORMAT = """\
Reply with ONE JSON object, nothing else. Choose one:
  {"poke": {"tool": "filesystem.read_file", "args": {"path": "<file>"}}}
  {"poke": {"tool": "filesystem.write_file", "args": {"path": "<file>", "content": "<text>"}}}
  {"propose": {"statement": "<claim about this environment>",
               "steps": [{"tool": "...", "args": {...}}, ...],
               "expect": {"predicate": "contains|equals|json_item_count|blocked",
                          "value": <value>}}}
  {"rest": true}

Mechanics of confirmation (this is how your proposals are judged):
- A proposed rule is REPLAYED on a fresh copy of this environment; expect is
  tested against the LAST step's output. The final step must be a read.
- The check must be DISCRIMINATING: it must also FAIL on a corrupted copy of
  the environment. Checks that pass on anything (like "the file parses") are
  rejected. Tie the expect to a SPECIFIC observed value.
- Worked example (for a fictional file colors.json you observed to contain
  three entries with a "hue" field):
  {"propose": {"statement": "colors.json holds 3 entries",
               "steps": [{"tool": "filesystem.read_file",
                          "args": {"path": "colors.json"}}],
               "expect": {"predicate": "json_item_count", "value": 3}}}
- Repeating a poke you already made returns the same observation and teaches
  nothing. After observing something specific, propose a rule about it."""


class OllamaLearner:
    def __init__(self, model: str = "qwen2.5-coder:7b",
                 base_url: str = "http://localhost:11434", temperature: float = 0.2):
        self.model = model
        self.base = base_url.rstrip("/")
        self.temperature = temperature

    def next_move(self, board: str) -> dict[str, Any]:
        import urllib.request
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": board},
                {"role": "user", "content": MOVE_FORMAT},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": self.temperature},
        }
        req = urllib.request.Request(
            self.base + "/api/chat", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            content = json.loads(r.read()).get("message", {}).get("content", "")
        move = _extract_move(content)
        return move if move else {"rest": True}


class AnthropicLearner:
    """The frontier learner (run 005). Each call is a FRESH API request with
    only the board as context — the learner never sees this repo, the withheld
    human map, or any session history. Contamination-clean by construction."""

    def __init__(self, model: str = "claude-sonnet-5", temperature: float = 0.2):
        import os
        self.model = model
        self.temperature = temperature
        self._key = os.getenv("ANTHROPIC_API_KEY")
        if not self._key:
            raise RuntimeError("AnthropicLearner needs $ANTHROPIC_API_KEY")
        self.usd_estimate = 0.0

    def next_move(self, board: str) -> dict[str, Any]:
        import json as _json
        import urllib.request
        # no temperature: deprecated for Claude 5-family models
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "system": board,
            "messages": [{"role": "user", "content": MOVE_FORMAT}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "x-api-key": self._key,
                     "anthropic-version": "2023-06-01"})
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = _json.loads(r.read())
        usage = resp.get("usage", {})
        self.usd_estimate += (usage.get("input_tokens", 0) * 3 +
                              usage.get("output_tokens", 0) * 15) / 1e6
        content = "".join(b.get("text", "") for b in resp.get("content", []))
        move = _extract_move(content)
        return move if move else {"rest": True}


def _extract_move(content: str) -> dict[str, Any] | None:
    """Tolerant parse: the whole content, or the last {...} block in it."""
    for candidate in (content, *re.findall(r"\{.*\}", content, re.DOTALL)[::-1]):
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(obj, dict) and (
                {"poke", "propose", "revise", "rest"} & obj.keys()):
            return obj
    return None

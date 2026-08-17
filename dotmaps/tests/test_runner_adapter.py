"""H8 (HARDENING_BRIEF): the adapter seam for the Claude CLI. Before this
gate, queen/chat.py and queen/workorder.py each hand-rolled the `claude -p`
invocation and read subtype/num_turns/total_cost_usd + stream-json event
shapes directly — two duplicated, unversioned CLI contracts with no
compatibility self-test. ClaudeCliAdapter is the one seam now; product
logic never touches a CLI flag or output field name directly."""
from pathlib import Path
from unittest import mock

from dotmaps.queen import runner_adapter as ra_mod


def test_self_test_ok_when_binary_and_version_respond(monkeypatch):
    adapter = ra_mod.ClaudeCliAdapter()
    monkeypatch.setattr(ra_mod.shutil, "which", lambda name: "/usr/local/bin/claude")

    def _fake_run(cmd, **kwargs):
        return mock.Mock(returncode=0, stdout="1.2.3 (Claude Code)\n")

    monkeypatch.setattr(ra_mod.subprocess, "run", _fake_run)
    ok, msg = adapter.self_test()
    assert ok is True
    assert "1.2.3" in msg


def test_self_test_graceful_message_when_binary_missing(monkeypatch):
    adapter = ra_mod.ClaudeCliAdapter()
    monkeypatch.setattr(ra_mod.shutil, "which", lambda name: None)
    ok, msg = adapter.self_test()
    assert ok is False
    assert "not found on PATH" in msg


def test_self_test_graceful_message_on_unexpected_output(monkeypatch):
    adapter = ra_mod.ClaudeCliAdapter()
    monkeypatch.setattr(ra_mod.shutil, "which", lambda name: "/usr/local/bin/claude")

    def _fake_run(cmd, **kwargs):
        return mock.Mock(returncode=1, stdout="")

    monkeypatch.setattr(ra_mod.subprocess, "run", _fake_run)
    ok, msg = adapter.self_test()
    assert ok is False
    assert "contract drift" in msg


def test_self_test_is_cached_not_rerun(monkeypatch):
    adapter = ra_mod.ClaudeCliAdapter()
    calls = {"n": 0}

    def _fake_which(name):
        calls["n"] += 1
        return "/usr/local/bin/claude"

    monkeypatch.setattr(ra_mod.shutil, "which", _fake_which)
    monkeypatch.setattr(ra_mod.subprocess, "run",
                        lambda cmd, **k: mock.Mock(returncode=0, stdout="1.0\n"))
    adapter.self_test()
    adapter.self_test()
    assert calls["n"] == 1


def test_run_fails_gracefully_when_self_test_fails(tmp_path, monkeypatch):
    adapter = ra_mod.ClaudeCliAdapter()
    monkeypatch.setattr(adapter, "_self_test_result", (False, "claude not found on PATH"))
    out = adapter.run(tmp_path, "job", model="claude-sonnet-5", max_turns=1, timeout_s=5)
    assert out["ok"] is False
    assert "compatibility self-test failed" in out["error"]


def test_run_stream_fails_gracefully_when_self_test_fails(tmp_path, monkeypatch):
    adapter = ra_mod.ClaudeCliAdapter()
    monkeypatch.setattr(adapter, "_self_test_result", (False, "claude not found on PATH"))
    out = adapter.run_stream(tmp_path, "job", model="claude-sonnet-5", max_turns=1,
                             timeout_s=5, trips_path=tmp_path / "trips.jsonl", run_id="r1")
    assert out["ok"] is False
    assert "compatibility self-test failed" in out["error"]


def test_run_normalizes_json_output(tmp_path, monkeypatch):
    adapter = ra_mod.ClaudeCliAdapter()
    monkeypatch.setattr(adapter, "_self_test_result", (True, "ok"))
    ws = tmp_path / "ws"
    ws.mkdir()

    def _fake_run(cmd, **kwargs):
        return mock.Mock(stdout='{"subtype": "success", "num_turns": 4, "total_cost_usd": 0.02}',
                         stderr="", returncode=0)

    monkeypatch.setattr(ra_mod.subprocess, "run", _fake_run)
    out = adapter.run(ws, "job", model="claude-sonnet-5", max_turns=5, timeout_s=5)
    assert out == {"ok": True, "subtype": "success", "num_turns": 4, "cost_usd": 0.02,
                   "raw": {"subtype": "success", "num_turns": 4, "total_cost_usd": 0.02}}


def test_describe_stream_event_tool_use_and_text():
    ev_tool = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Read", "input": {"file_path": "x.json"}}]}}
    step = ra_mod._describe_stream_event(ev_tool)
    assert step["tool"] == "Read"
    assert "Reading x.json" in step["text"]

    ev_text = {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "checking the file now"}]}}
    step2 = ra_mod._describe_stream_event(ev_text)
    assert step2["tool"] is None
    assert "checking the file now" in step2["text"]

    assert ra_mod._describe_stream_event({"type": "system"}) is None

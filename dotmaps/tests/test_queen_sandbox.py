"""H2 (HARDENING_BRIEF): work-order isolation. The audit's P0 finding — the
full-agent work order stripped only ANTHROPIC_API_KEY from the child env and
passed the rest of os.environ wholesale, so an unrelated planted secret (a
cloud token, another API key) reached the untrusted `claude -p
--dangerously-skip-permissions` process. queen/sandbox.py's build_child_env()
replaces that with an EMPTY allowlist + PATH + only explicitly-named keys."""
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from dotmaps.queen import chat as chat_mod
from dotmaps.queen import sandbox as sandbox_mod
from dotmaps.queen import workorder as wo_mod


def test_build_child_env_strips_a_planted_secret(monkeypatch):
    monkeypatch.setenv("SECRET_TOKEN", "sk-super-secret-do-not-leak")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    env = sandbox_mod.build_child_env()
    assert "SECRET_TOKEN" not in env
    assert env.get("PATH") == "/usr/bin:/bin"


def test_build_child_env_default_allowlist_is_path_only(monkeypatch):
    monkeypatch.setenv("HOME", "/Users/whoever")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "leak-me-not")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "also-leak-me-not")
    env = sandbox_mod.build_child_env()
    assert set(env) <= {"PATH"}
    assert "HOME" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env


def test_build_child_env_extra_allowed_is_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/tmp/claude-auth")
    monkeypatch.setenv("OTHER_SECRET", "nope")
    env = sandbox_mod.build_child_env(extra_allowed=frozenset({"CLAUDE_CONFIG_DIR"}))
    assert env.get("CLAUDE_CONFIG_DIR") == "/tmp/claude-auth"
    assert "OTHER_SECRET" not in env


def test_assert_disposable_workspace_accepts_a_tempdir():
    ws = Path(tempfile.mkdtemp(prefix="queen-sandbox-test-"))
    sandbox_mod.assert_disposable_workspace(ws)  # must not raise


def test_assert_disposable_workspace_refuses_the_repo():
    repo_root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="disposable temp copy"):
        sandbox_mod.assert_disposable_workspace(repo_root)


def test_run_config_degrades_to_restricted_env_without_docker_image(monkeypatch):
    monkeypatch.delenv("DOTMAPS_SANDBOX_IMAGE", raising=False)
    monkeypatch.setenv("SECRET_TOKEN", "leak-me-not")
    ws = Path(tempfile.mkdtemp(prefix="queen-sandbox-test-"))
    cfg = sandbox_mod.run_config(ws, ["claude", "-p"])
    assert cfg["mode"] == "restricted-env"
    assert cfg["warning"] == sandbox_mod.SANDBOX_WARNING
    assert "SECRET_TOKEN" not in cfg["env"]


def test_run_config_picks_docker_mode_when_image_and_binary_present(monkeypatch):
    monkeypatch.setenv("DOTMAPS_SANDBOX_IMAGE", "dotmaps/sandbox:test")
    monkeypatch.setattr(sandbox_mod, "docker_available", lambda: True)
    ws = Path(tempfile.mkdtemp(prefix="queen-sandbox-test-"))
    cfg = sandbox_mod.run_config(ws, ["claude", "-p"])
    assert cfg["mode"] == "docker"
    assert cfg["warning"] is None
    assert "--network" in cfg["cmd"] and "none" in cfg["cmd"]


def test_chat_runner_real_subprocess_call_uses_sandboxed_env(monkeypatch, tmp_path):
    """The REAL runner (never invoked by other tests, which inject a fake
    `_runner`) must build its subprocess env via sandbox.build_child_env(),
    not os.environ directly. Mock subprocess.Popen and inspect the kwargs."""
    monkeypatch.setenv("SECRET_TOKEN", "leak-me-not")
    ws = tmp_path / "ws"
    ws.mkdir()

    captured = {}

    class _FakeStdout:
        def readline(self):
            return ""  # no stream events, immediate EOF

    class _FakeProc:
        stdin = mock.MagicMock()
        stdout = _FakeStdout()
        stderr = mock.MagicMock(read=lambda: "")
        returncode = 0

        def wait(self, timeout=None):
            return 0

    def _fake_popen(cmd, **kwargs):
        captured.update(kwargs)
        captured["cmd"] = cmd
        return _FakeProc()

    monkeypatch.setattr(chat_mod._adapter, "_self_test_result", (True, "stubbed for test"))
    monkeypatch.setattr(chat_mod.runner_adapter_mod.subprocess, "Popen", _fake_popen)
    chat_mod._run_agentic_stream(ws, "job text", model="claude-sonnet-5", max_turns=1,
                                 timeout_s=5, trips_path=tmp_path / "trips.jsonl", run_id="r1")
    assert "SECRET_TOKEN" not in captured["env"]


def test_workorder_runner_real_subprocess_call_uses_sandboxed_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_TOKEN", "leak-me-not")
    ws = tmp_path / "ws"
    ws.mkdir()

    captured = {}

    class _FakeCompleted:
        stdout = '{"subtype": "success", "num_turns": 1, "total_cost_usd": 0.0}'
        stderr = ""
        returncode = 0

    def _fake_run(cmd, **kwargs):
        captured.update(kwargs)
        captured["cmd"] = cmd
        return _FakeCompleted()

    monkeypatch.setattr(wo_mod._adapter, "_self_test_result", (True, "stubbed for test"))
    monkeypatch.setattr(wo_mod.runner_adapter_mod.subprocess, "run", _fake_run)
    wo_mod._run_agentic(ws, "job text", model="claude-sonnet-5", max_turns=1, timeout_s=5)
    assert "SECRET_TOKEN" not in captured["env"]

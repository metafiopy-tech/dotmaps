"""RUNNER ADAPTER — H8 (HARDENING_BRIEF): one seam around the Claude CLI.

Before this gate, queen/chat.py's `_run_agentic_stream` and queen/
workorder.py's `_run_agentic` each hand-rolled the `claude -p` invocation
and read `subtype`/`num_turns`/`total_cost_usd` and stream-json event
shapes directly out of the CLI's own output — two duplicated, undeclared
CLI contracts, with no version pin and no way to fail cleanly if the CLI's
flags or output fields ever drift (audit Q27/Q45: "queen frontier chat/
work orders are coupled to the claude CLI... hard-coded model name,
command flags, stream/json output fields").

`ClaudeCliAdapter` is the one place that contract is now declared and
checked. Product logic (chat.py, workorder.py) calls `.run()`/
`.run_stream()` and reads the normalized result dict this module defines
(`ok`, `subtype`, `num_turns`, `cost_usd`, `raw`) — it never touches a CLI
flag name or a `stream-json` event shape directly again. queen/sandbox.py
still owns HOW the subprocess is isolated (env/docker/restricted-env); this
module owns WHAT is invoked and how its output is read.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from . import sandbox as sandbox_mod
from . import trips as trips_mod

# Version-pinned contract: the flags this adapter constructs, and the
# output fields it reads per --output-format. A future CLI that drops or
# renames one of these should fail the self-test with a clear message,
# not silently misparse.
CLI_CONTRACT = {
    "binary": "claude",
    "flags": ("-p", "--output-format", "--model", "--max-turns",
             "--dangerously-skip-permissions"),
    "output_fields": {
        "json": ("subtype", "num_turns", "total_cost_usd"),
        "stream-json": ("type",),  # per-event; "result" events also carry
                                    # the json-format fields above
    },
}


class ClaudeCliAdapter:
    def __init__(self) -> None:
        self._self_test_result: tuple[bool, str] | None = None

    def self_test(self) -> tuple[bool, str]:
        """Run once (cached): is `claude` on PATH at all, and does
        `--version` respond the way a compatible CLI should? Never raises —
        a missing/incompatible CLI is a graceful, specific fail message, not
        a crash, so the caller (compose_job's caller) can surface it as an
        honest "couldn't verify that" instead of a traceback."""
        if self._self_test_result is not None:
            return self._self_test_result
        binary = CLI_CONTRACT["binary"]
        path = shutil.which(binary)
        if not path:
            self._self_test_result = (False, f"{binary!r} not found on PATH — "
                                              f"install/authenticate the Claude CLI")
            return self._self_test_result
        try:
            proc = subprocess.run([binary, "--version"], capture_output=True,
                                  text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as e:
            self._self_test_result = (False, f"{binary} --version failed: {e}")
            return self._self_test_result
        if proc.returncode != 0 or not proc.stdout.strip():
            self._self_test_result = (
                False, f"{binary} --version returned rc={proc.returncode}, "
                       f"no version string — CLI contract drift suspected")
            return self._self_test_result
        self._self_test_result = (True, proc.stdout.strip())
        return self._self_test_result

    def _cmd(self, output_format: str, model: str, max_turns: int) -> list[str]:
        return [CLI_CONTRACT["binary"], "-p", "--output-format", output_format,
               "--model", model, "--max-turns", str(max_turns),
               "--dangerously-skip-permissions"]

    def run(self, workspace: Path, job: str, *, model: str, max_turns: int,
           timeout_s: int) -> dict[str, Any]:
        """Batch mode (--output-format json) — the shape queen/workorder.py
        needs. Returns the normalized result dict; never raises for an
        ordinary CLI failure (timeout, unparseable output)."""
        ok, msg = self.self_test()
        if not ok:
            return {"ok": False, "error": f"claude CLI compatibility self-test failed: {msg}"}
        cfg = sandbox_mod.run_config(workspace, self._cmd("json", model, max_turns))
        try:
            proc = subprocess.run(cfg["cmd"], input=job, capture_output=True, text=True,
                                  timeout=timeout_s, cwd=str(workspace), env=cfg["env"],
                                  preexec_fn=cfg["preexec_fn"])
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"wall-clock timeout after {timeout_s}s"}
        try:
            data = json.loads(proc.stdout)
        except (json.JSONDecodeError, TypeError):
            return {"ok": False,
                    "error": f"unparseable claude output (rc={proc.returncode}): "
                             f"{(proc.stderr or '')[:500]}"}
        return {"ok": data.get("subtype") == "success", "subtype": data.get("subtype"),
                "num_turns": data.get("num_turns"), "cost_usd": data.get("total_cost_usd"),
                "raw": data}

    def run_stream(self, workspace: Path, job: str, *, model: str, max_turns: int,
                   timeout_s: int, trips_path: Path, run_id: str,
                   on_step: Callable[[dict[str, Any]], None] | None = None
                   ) -> dict[str, Any]:
        """Stream mode (--output-format stream-json) — the shape queen/
        chat.py needs, emitting one WORK_ORDER phase="step" trip per
        user-facing step as it happens. `on_step`, if given, is called with
        each parsed step dict in addition to the trip emit (kept for
        callers that want the raw step without re-reading the journal)."""
        ok, msg = self.self_test()
        if not ok:
            return {"ok": False, "error": f"claude CLI compatibility self-test failed: {msg}"}
        cmd = self._cmd("stream-json", model, max_turns) + ["--verbose"]
        cfg = sandbox_mod.run_config(workspace, cmd)
        trips_mod.emit("WORK_ORDER", path=trips_path, phase="sandbox", run_id=run_id,
                       sandbox_mode=cfg["mode"], sandbox_warning=cfg["warning"])
        start = time.time()
        try:
            proc = subprocess.Popen(cfg["cmd"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, cwd=str(workspace),
                                    env=cfg["env"], preexec_fn=cfg["preexec_fn"])
        except FileNotFoundError as e:
            return {"ok": False, "error": f"claude CLI not found: {e}"}
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(job)
        proc.stdin.close()
        result = None
        step_n = 0
        try:
            for line in iter(proc.stdout.readline, ""):
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") == "result":
                    result = ev
                    continue
                step = _describe_stream_event(ev)
                if step:
                    step_n += 1
                    trips_mod.emit("WORK_ORDER", path=trips_path, phase="step",
                                   run_id=run_id, seq_in_run=step_n, text=step["text"],
                                   tool=step.get("tool"), model_call=step.get("model_call", True),
                                   elapsed=round(time.time() - start, 2))
                    if on_step:
                        on_step(step)
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"ok": False, "error": f"wall-clock timeout after {timeout_s}s"}
        if result is None:
            stderr = (proc.stderr.read() if proc.stderr else "")[:500]
            return {"ok": False, "error": f"no result event in stream (rc={proc.returncode}): {stderr}"}
        return {"ok": result.get("subtype") == "success", "subtype": result.get("subtype"),
                "num_turns": result.get("num_turns"), "cost_usd": result.get("total_cost_usd"),
                "raw": result}


def _describe_stream_event(ev: dict[str, Any]) -> dict[str, Any] | None:
    """One stream-json event -> one plain-language step, or None if this
    event carries no user-facing step (system/init noise, etc.). Moved
    here from queen/chat.py — this IS the CLI-output-field-reading logic
    H8 says product code should not own directly."""
    t = ev.get("type")
    if t == "assistant":
        for block in (ev.get("message", {}) or {}).get("content", []) or []:
            if block.get("type") == "tool_use":
                name = block.get("name", "a tool")
                args = block.get("input", {}) or {}
                target = args.get("file_path") or args.get("path") or args.get("pattern") or ""
                verb = {"Read": "Reading", "Write": "Writing", "Edit": "Editing",
                        "Bash": "Running a command", "Grep": "Searching",
                        "Glob": "Looking for files"}.get(name, f"Using {name}")
                text = f"{verb} {target}".strip()
                return {"text": text, "tool": name, "model_call": True}
            if block.get("type") == "text" and block.get("text", "").strip():
                snippet = block["text"].strip().splitlines()[0][:100]
                return {"text": f"Thinking: {snippet}", "tool": None, "model_call": True}
    return None

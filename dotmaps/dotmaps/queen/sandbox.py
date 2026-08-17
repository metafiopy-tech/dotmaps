"""SANDBOX — H2 (HARDENING_BRIEF): treat Claude Code as untrusted execution.

The audit's P0 finding: `chat.py`/`workorder.py` launched `claude -p
--dangerously-skip-permissions` with `env = {k: v for k, v in os.environ.items()
if k != "ANTHROPIC_API_KEY"}` — every OTHER host environment variable (unrelated
tokens, cloud credentials, whatever the operator happens to have exported) still
reached the child. cwd (a disposable temp copy of the seed) is a real, useful
boundary against corrupting the repo, but it is not OS isolation — Bash inside
the agent can still address any path the host user can, use host network tools,
or invoke any authenticated CLI already on the machine. Neither module's
docstrings claimed cwd WAS a sandbox (checked before writing this), so there is
no false "sandbox" language elsewhere in the repo to strip.

Two things this module actually provides, honestly:
  1. `build_child_env()` — an EMPTY-allowlist environment (PATH, so `claude` can
     be found on it, plus only whatever the caller explicitly names) instead of
     the wholesale `os.environ` passthrough. This is real, testable, and closes
     the audit's literal acceptance test (a planted secret in the parent process
     never reaches the child).
  2. `run_config()` — picks between two real, honestly-labeled execution modes:
       - "docker": only when the `docker` binary is present AND an operator has
         set `DOTMAPS_SANDBOX_IMAGE` to a pre-built image that actually has the
         `claude` CLI (and its auth) baked in — building/shipping that image is
         outside this repo's scope, so this mode is opt-in infrastructure, not
         something `pytest` can exercise here. When active: `--network none`,
         the workspace mounted as the only writable path, and explicit
         CPU/memory/pid caps.
       - "restricted-env" (the default everywhere else): the empty-allowlist
         env above, best-effort POSIX CPU/address-space limits, and a LOUD,
         machine-readable warning attached to the WORK_ORDER trip and printed —
         "unsandboxed — dev only" — because real OS-level network denial is not
         achievable here without a container. This mode never pretends to be
         more than it is.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# The narrowest env a subprocess needs to exec a binary found on PATH. Nothing
# else is passed through by default — no HOME, no cloud/CI/API credentials, no
# shell rc-file variables. A real per-tool credential need (e.g. the claude
# CLI's own auth) is an explicit, narrow opt-in via `extra_allowed`, never a
# blanket inheritance of the operator's shell.
_BASE_ALLOWLIST = ("PATH",)

SANDBOX_WARNING = "unsandboxed — dev only"

# A scratch root every disposable workspace must live under (defense-in-depth
# on top of the existing tempfile.mkdtemp(prefix=...) pattern already used by
# chat.py/workorder.py — this just makes the assumption assertable).
SCRATCH_ROOT = Path(tempfile.gettempdir()).resolve()


def build_child_env(extra_allowed: frozenset[str] = frozenset()) -> dict[str, str]:
    """EMPTY allowlist + PATH + only explicitly-named keys — never
    `os.environ` wholesale. This is the one function chat.py and workorder.py
    call for their subprocess `env=` kwarg; a caller that genuinely needs one
    more credential (e.g. a bound MCP token) must name it explicitly here,
    never inherit the rest of the host by accident."""
    allowed = set(_BASE_ALLOWLIST) | set(extra_allowed)
    return {k: v for k, v in os.environ.items() if k in allowed}


def docker_available() -> bool:
    return shutil.which("docker") is not None


def _sandbox_image() -> str | None:
    return os.environ.get("DOTMAPS_SANDBOX_IMAGE") or None


def assert_disposable_workspace(path: Path) -> None:
    """Defense-in-depth: refuse to run a work order against anything that
    isn't a scratch-dir copy. Both chat.py and workorder.py already build
    their workspace via `Path(tempfile.mkdtemp(...))`, so this should never
    fire in normal operation — it exists to catch a future call site that
    accidentally points a work order at the repo or a real home directory."""
    resolved = Path(path).resolve()
    if SCRATCH_ROOT not in resolved.parents and resolved != SCRATCH_ROOT:
        raise ValueError(
            f"refusing to run a work order against {resolved} — it is not under "
            f"the scratch root {SCRATCH_ROOT}; a work order must run against a "
            f"disposable temp copy, never a real project or home directory")


def docker_command(workspace: Path, cmd: list[str]) -> list[str]:
    """The real, safety-flagged docker invocation for when `run_config()`
    picks mode="docker". Network denied, only the workspace mounted, and
    explicit resource caps — never invoked unless docker_available() and a
    configured image are both true."""
    image = _sandbox_image()
    assert image, "docker_command() called without DOTMAPS_SANDBOX_IMAGE set"
    ws = str(Path(workspace).resolve())
    return [
        "docker", "run", "--rm", "-i",
        "--network", "none",
        "-v", f"{ws}:{ws}:rw",
        "--workdir", ws,
        "--memory", "1g", "--cpus", "2", "--pids-limit", "256",
        image, *cmd,
    ]


def apply_resource_limits() -> None:
    """Best-effort POSIX CPU-time / address-space caps, meant to be passed as
    `preexec_fn` to subprocess.Popen/run. Wrapped so a platform without
    `resource` (or a limit the OS refuses to raise/lower) degrades to a no-op
    rather than crashing the caller — this is defense-in-depth alongside
    --max-turns/timeout_s, not the primary budget enforcement."""
    try:
        import resource
    except ImportError:
        return
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (WORK_ORDER_CPU_SECONDS, WORK_ORDER_CPU_SECONDS))
    except (ValueError, OSError):
        pass
    try:
        resource.setrlimit(resource.RLIMIT_AS, (WORK_ORDER_MEMORY_BYTES, WORK_ORDER_MEMORY_BYTES))
    except (ValueError, OSError):
        pass


WORK_ORDER_CPU_SECONDS = 1800   # matches the existing wall-clock timeout order of magnitude
WORK_ORDER_MEMORY_BYTES = 2 * 1024 * 1024 * 1024  # 2GB, generous for a small demo workspace


def run_config(workspace: Path, cmd: list[str], *,
               extra_env_allowed: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Decide how a work order's subprocess should actually run. Returns a
    plain dict — chat.py/workorder.py build their own Popen/run call from it
    (they already differ in stream vs batch mode), so this stays a policy
    decision, not a process-spawning wrapper.

    mode="docker"         -> real command + safety flags, network denied
    mode="restricted-env" -> honest degrade: empty-allowlist env, best-effort
                              resource limits, and a LOUD warning — this repo
                              never claims network isolation it can't deliver
                              without a container."""
    assert_disposable_workspace(workspace)
    env = build_child_env(extra_env_allowed)
    if docker_available() and _sandbox_image():
        return {"mode": "docker", "cmd": docker_command(workspace, cmd),
                "env": env, "preexec_fn": None, "warning": None}
    warning = SANDBOX_WARNING
    print(f"[queen/sandbox] {warning} — no {'DOTMAPS_SANDBOX_IMAGE' if docker_available() else 'docker binary'} "
          f"found; running with an empty-allowlist env and best-effort resource limits only, "
          f"no OS-level network denial.", file=sys.stderr)
    preexec = apply_resource_limits if os.name == "posix" else None
    return {"mode": "restricted-env", "cmd": cmd, "env": env,
            "preexec_fn": preexec, "warning": warning}

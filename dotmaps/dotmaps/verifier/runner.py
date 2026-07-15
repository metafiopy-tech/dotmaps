"""Runs the FULL manifest every cycle and collects DotResults (rule 4).

Two execution modes:

  local   -- subprocess on the host. Fast; for smoke iteration and dev. The
             workspace is passed as a path; read-only-ness is NOT enforced by
             the OS in this mode (documented, not pretended otherwise).
  docker  -- each verifier runs in the map's pinned container with the
             workspace bind-mounted READ-ONLY (`:ro`). This is the real thing:
             the verifier can see everything and touch nothing, and it verifies
             identically on any machine (the portability moat, spec §4.1).

The runner is the ONLY component that executes verifier code, and it never
imports runtime/ — the verifier's read-only view of the world is total.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ..models import EXIT_ERROR, DotResult, Map
from .contract import TIMEOUT_SECONDS, WORKSPACE_FLAG, WORKSPACE_MOUNT


class Verifier:
    def __init__(self, mode: str = "local", image: str | None = None):
        assert mode in ("local", "docker")
        self.mode = mode
        self.image = image

    @classmethod
    def for_map(cls, m: Map, mode: str = "local") -> "Verifier":
        image = None
        if mode == "docker":
            image = f"dotmap-{m.name}:{m.version}"
        return cls(mode=mode, image=image)

    def run_full_manifest(self, m: Map, workspace: str | Path) -> list[DotResult]:
        ws = Path(workspace).resolve()
        results: list[DotResult] = []
        for dot in m.dots:
            results.append(self.run_one(m, dot.id, ws))
        return results

    def run_one(self, m: Map, dot_id: str, workspace: Path) -> DotResult:
        dot = m.dot(dot_id)
        script = m.verifier_path(dot)
        if self.mode == "docker":
            argv = self._docker_argv(m, script, workspace)
        else:
            argv = self._local_argv(script, workspace)
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
            return DotResult.from_stdout(dot_id, proc.stdout, proc.returncode)
        except subprocess.TimeoutExpired:
            return DotResult(
                dot=dot_id, passed=False,
                evidence=f"verifier exceeded {TIMEOUT_SECONDS}s timeout", errored=True,
            )
        except Exception as e:  # missing interpreter, permission, etc.
            return DotResult(
                dot=dot_id, passed=False,
                evidence=f"verifier failed to launch: {e}", errored=True,
            )

    # -- argv builders ------------------------------------------------------ #
    def _local_argv(self, script: Path, workspace: Path) -> list[str]:
        interp = self._interpreter(script)
        return [*interp, str(script), WORKSPACE_FLAG, str(workspace)]

    def _docker_argv(self, m: Map, script: Path, workspace: Path) -> list[str]:
        assert m.root is not None
        rel_script = script.relative_to(m.root)
        # workspace read-only; map repo (verifiers) read-only too. Nothing is
        # writable, so a buggy/hostile verifier cannot alter the board or ws.
        return [
            "docker", "run", "--rm",
            "--network", "none" if not self._needs_net(m) else "bridge",
            "-v", f"{workspace}:{WORKSPACE_MOUNT}:ro",
            "-v", f"{m.root}:/map:ro",
            "-w", "/map",
            self.image or f"dotmap-{m.name}:{m.version}",
            *self._interpreter(script, in_container=True),
            f"/map/{rel_script}", WORKSPACE_FLAG, WORKSPACE_MOUNT,
        ]

    @staticmethod
    def _needs_net(m: Map) -> bool:
        # deploy/health maps hit the live site; content maps may not.
        return True

    @staticmethod
    def _interpreter(script: Path, in_container: bool = False) -> list[str]:
        suffix = script.suffix.lower()
        if suffix == ".py":
            return ["python3"] if in_container else [sys.executable]
        if suffix in (".sh", ".bash"):
            return ["bash"]
        return []  # rely on shebang + exec bit

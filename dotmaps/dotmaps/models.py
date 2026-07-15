"""Core schemas — FROZEN per build spec §4b.

Everything else in the harness is refactorable; these types are load-bearing.
Three schemas live here:

  1. Map / Dot        -- the map.yaml manifest (data + checks the harness consumes)
  2. DotResult        -- the verifier contract (one JSON line per dot)
  3. Event            -- the append-only scoreboard event log

Keep this module dependency-light (stdlib + pyyaml). It is imported by every
layer, so a heavy import here taxes the whole system.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

# --------------------------------------------------------------------------- #
# Event vocabulary (scoreboard). Freeze these strings — the log, the replay,   #
# and the certificate all key off them.                                        #
# --------------------------------------------------------------------------- #
EVENT_RUN_STARTED = "run_started"
EVENT_CYCLE_STARTED = "cycle_started"
EVENT_DOT_ATTEMPTED = "dot_attempted"
EVENT_DOT_EATEN = "dot_eaten"
EVENT_DOT_REGRESSED = "dot_regressed"
EVENT_BUDGET_TICK = "budget_tick"
EVENT_RUN_ENDED = "run_ended"

# run_ended reasons
END_ALL_GREEN = "all_green"
END_BUDGET = "budget_exhausted"
END_KILLED = "killed"

# verifier exit codes (see verifier contract in spec §4b)
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2  # treated as fail, flagged


# --------------------------------------------------------------------------- #
# map.yaml schema                                                              #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Dot:
    id: str
    statement: str  # plain-English promise, shown to the user
    verifier: str  # path relative to the map repo, e.g. verifiers/007_pages_200.py
    depends_on: tuple[str, ...] = ()
    destructive: bool = False

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Dot":
        return Dot(
            id=str(d["id"]),
            statement=d["statement"],
            verifier=d["verifier"],
            depends_on=tuple(str(x) for x in d.get("depends_on", []) or []),
            destructive=bool(d.get("destructive", False)),
        )


@dataclass(frozen=True)
class Budget:
    max_cycles: int = 40
    max_usd: float = 2.00

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> "Budget":
        d = d or {}
        return Budget(
            max_cycles=int(d.get("max_cycles", 40)),
            max_usd=float(d.get("max_usd", 2.00)),
        )


@dataclass(frozen=True)
class TravelerConfig:
    # driver: 'scripted' (deterministic test driver) | 'llm' (Anthropic API)
    #         | 'ollama' (local open model — no credentials, the cheap traveler)
    driver: str = "llm"
    model: str = ""
    fallback: str = ""
    temperature: float = 0.0
    # ollama driver only: server address (OLLAMA_HOST-style)
    base_url: str = "http://localhost:11434"
    # scripted driver only: dot_id -> list of action dicts
    script: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> "TravelerConfig":
        d = d or {}
        return TravelerConfig(
            driver=d.get("driver", "llm"),
            model=d.get("model", ""),
            fallback=d.get("fallback", ""),
            temperature=float(d.get("temperature", 0.0)),
            base_url=d.get("base_url", "http://localhost:11434"),
            script=d.get("script", {}) or {},
        )


@dataclass(frozen=True)
class Map:
    name: str
    version: str
    domain: str
    mcp_required: tuple[str, ...]
    budget: Budget
    traveler: TravelerConfig
    dots: tuple[Dot, ...]
    fog_ref: str = "fog.md"
    blast_radius_ref: str = "blast_radius.md"
    # optional per-server setup hints for `dotmaps connect` (url/docs/hint)
    mcp_setup: dict = None
    # absolute path to the map repo root (set at load time, not from yaml)
    root: Optional[Path] = None

    @staticmethod
    def load(map_dir: str | Path) -> "Map":
        root = Path(map_dir).resolve()
        with open(root / "map.yaml") as f:
            raw = yaml.safe_load(f)
        return Map(
            name=raw["name"],
            version=str(raw["version"]),
            domain=raw.get("domain", ""),
            mcp_required=tuple(raw.get("mcp_required", []) or []),
            mcp_setup=raw.get("mcp_setup") or {},
            budget=Budget.from_dict(raw.get("budget")),
            traveler=TravelerConfig.from_dict(raw.get("traveler")),
            dots=tuple(Dot.from_dict(x) for x in raw.get("dots", [])),
            fog_ref=raw.get("fog", "fog.md"),
            blast_radius_ref=raw.get("blast_radius", "blast_radius.md"),
            root=root,
        )

    def dot(self, dot_id: str) -> Dot:
        for d in self.dots:
            if d.id == dot_id:
                return d
        raise KeyError(f"no dot {dot_id!r} in map {self.name}")

    def verifier_path(self, dot: Dot) -> Path:
        assert self.root is not None
        return (self.root / dot.verifier).resolve()

    def validate(self) -> list[str]:
        """Cheap structural checks. Returns list of problems (empty = ok)."""
        problems: list[str] = []
        ids = [d.id for d in self.dots]
        if len(ids) != len(set(ids)):
            problems.append("duplicate dot ids")
        idset = set(ids)
        for d in self.dots:
            for dep in d.depends_on:
                if dep not in idset:
                    problems.append(f"dot {d.id} depends_on unknown dot {dep}")
            if self.root and not self.verifier_path(d).exists():
                problems.append(f"dot {d.id}: verifier {d.verifier} missing")
        return problems


# --------------------------------------------------------------------------- #
# Verifier contract                                                            #
#   stdout: single JSON line {"dot": id, "pass": bool, "evidence": "<sentence>"} #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DotResult:
    dot: str
    passed: bool
    evidence: str
    errored: bool = False  # exit 2 -> treated as fail, flagged

    @staticmethod
    def from_stdout(dot_id: str, stdout: str, exit_code: int) -> "DotResult":
        """Parse a verifier's stdout JSON line, tolerating noise."""
        import json

        parsed: dict[str, Any] = {}
        for line in reversed(stdout.strip().splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        errored = exit_code == EXIT_ERROR
        # exit code is the source of truth for pass/fail; JSON evidence is advisory
        passed = (exit_code == EXIT_PASS) and bool(parsed.get("pass", True))
        evidence = parsed.get("evidence") or (
            "verifier errored" if errored else ("passed" if passed else "failed")
        )
        return DotResult(dot=dot_id, passed=passed, evidence=str(evidence), errored=errored)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

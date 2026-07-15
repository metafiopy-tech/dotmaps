"""Append-only stores for the POKE loop: journal, hypotheses, primitives.

Layout under the grow run directory:
    poke_journal.jsonl   # every (action, observation) pair, append-only
    hypotheses.jsonl     # proposed-but-unconfirmed rules (+ status updates)
    novelty.jsonl        # phase-clock series (banked-count per poke window)
    primitives/<id>.yaml # banked rules
    checks/<id>.py       # compiled read-only verifier per dot-eligible rule
    fog.md               # hypotheses the loop could not decide (never dropped)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterator

import yaml


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class GrowStore:
    def __init__(self, run_dir: str | Path):
        self.root = Path(run_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "primitives").mkdir(exist_ok=True)
        (self.root / "checks").mkdir(exist_ok=True)

    # -- journal (append-only, rule 2) -------------------------------------- #
    def journal_poke(self, spiral: int, action: dict[str, Any],
                     observation: str) -> int:
        n = self.poke_count() + 1
        rec = {"n": n, "t": _now(), "spiral": spiral, "action": action,
               "observation": observation[:2000]}
        with open(self.root / "poke_journal.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
        return n

    def poke_count(self) -> int:
        p = self.root / "poke_journal.jsonl"
        return sum(1 for _ in open(p)) if p.exists() else 0

    def journal_tail(self, k: int = 10) -> list[dict[str, Any]]:
        p = self.root / "poke_journal.jsonl"
        if not p.exists():
            return []
        lines = p.read_text().splitlines()
        return [json.loads(l) for l in lines[-k:]]

    # -- hypotheses ---------------------------------------------------------- #
    def add_hypothesis(self, rule: dict[str, Any]) -> None:
        with open(self.root / "hypotheses.jsonl", "a") as f:
            f.write(json.dumps({"t": _now(), "event": "proposed",
                                "rule": rule}) + "\n")

    def resolve_hypothesis(self, rule_id: str, outcome: str) -> None:
        """outcome: banked | refuted | fogged"""
        with open(self.root / "hypotheses.jsonl", "a") as f:
            f.write(json.dumps({"t": _now(), "event": outcome,
                                "rule_id": rule_id}) + "\n")

    def open_hypotheses(self) -> list[dict[str, Any]]:
        p = self.root / "hypotheses.jsonl"
        if not p.exists():
            return []
        proposed: dict[str, dict[str, Any]] = {}
        closed: set[str] = set()
        for line in p.read_text().splitlines():
            rec = json.loads(line)
            if rec["event"] == "proposed":
                proposed[rec["rule"]["id"]] = rec["rule"]
            else:
                closed.add(rec["rule_id"])
        return [r for rid, r in proposed.items() if rid not in closed]

    # -- primitives ----------------------------------------------------------#
    def bank_primitive(self, rule: dict[str, Any], journal_ref: int,
                       spiral: int) -> None:
        rule = {**rule, "confirmed_by_poke": journal_ref, "spiral": spiral,
                "banked_at": _now()}
        path = self.root / "primitives" / f"{rule['id']}.yaml"
        path.write_text(yaml.safe_dump(rule, sort_keys=False))

    def primitives(self) -> list[dict[str, Any]]:
        out = []
        for p in sorted((self.root / "primitives").glob("*.yaml")):
            out.append(yaml.safe_load(p.read_text()))
        return out

    # -- novelty series (phase-clock data, logged regardless) ---------------- #
    def log_novelty(self, spiral: int, poke_n: int, banked_total: int,
                    phase: str) -> None:
        with open(self.root / "novelty.jsonl", "a") as f:
            f.write(json.dumps({"t": _now(), "spiral": spiral, "poke": poke_n,
                                "banked": banked_total, "phase": phase}) + "\n")

    # -- fog ------------------------------------------------------------------#
    def fog(self, statement: str, why: str) -> None:
        p = self.root / "fog.md"
        header = "" if p.exists() else "# Fog — undecidable by this agent\n\n"
        with open(p, "a") as f:
            f.write(f"{header}- {statement} — {why} ({_now()})\n")

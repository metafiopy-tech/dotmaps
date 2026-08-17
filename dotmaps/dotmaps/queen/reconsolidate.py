"""C3 — reconsolidation, write-on-read (metabolism-spec-v0_1.md, component
C3 — "the ONE component with no vault precedent... its absence is what
makes the current system a library rather than a memory").

Every certified-skill invocation is a write: last_used advances, an
invocation counter increments, FSRS-lite stability updates, and a usage
delta appends to the skill's own provenance. NEVER touches method.steps
or check — law 3 ("re-synthesis never touches crystallized artifacts"),
self-checked on every write, not just tested.

A skill whose stability has decayed past the shelf threshold gets a
SHELVED trip proposing re-certification — a deterministic certify_all
rerun, free, no model in the loop. `dotmaps sleep` (Q6) is what actually
runs the recheck and calls reset_after_recert() once it passes.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import yaml

from . import trips as trips_mod

# FSRS-lite v0: stability grows with each successful invocation, decays
# exponentially with elapsed time since last_used. Full FSRS (per-card
# difficulty, fitted retrievability curve) is EMPIRICAL-TODO — no re-cert
# failure data exists yet to fit against; this is the deliberately crude
# v0 the metabolism spec calls for (C7: "BUILT... needs rewiring to C3").
#
# H6 (HARDENING_BRIEF): the audit's P1 finding — due_for_recheck() used to
# compare `stability * ratio < stability * SHELF_THRESHOLD`, and stability
# cancels out of that inequality algebraically, so every card went due at
# the SAME fixed-age ratio no matter how many times it had been used.
# Stability now scales the effective half-life instead (see
# _effective_half_life() below) — a well-used card genuinely gets a longer
# recheck interval. Still v0/crude (still EMPIRICAL-TODO, still no fitted
# curve), just no longer mathematically vacuous.
STABILITY_INCREMENT = 1.0     # EMPIRICAL-TODO: flat per-use bump, unweighted.
SHELF_HALF_LIFE_DAYS = 30.0   # EMPIRICAL-TODO: no re-cert failure data yet
                              # to fit against; order-of-magnitude guess.
                              # This is the BASE half-life at stability ==
                              # STABILITY_INCREMENT (one invocation); see
                              # _effective_half_life().
SHELF_THRESHOLD = 0.2         # EMPIRICAL-TODO: decay fraction that triggers
                              # a re-check proposal.
STABILITY_CEILING = 10.0


def _now_iso(ts: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.localtime(ts) if ts is not None else time.localtime())


def _method_bytes(card: dict) -> bytes:
    return json.dumps({"steps": card["method"]["steps"], "hash": card["method"]["hash"]},
                      sort_keys=True).encode()


def _check_bytes(card: dict) -> bytes:
    return json.dumps(card["check"], sort_keys=True).encode()


def touch(skill_path: Path, trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
          now_ts: float | None = None) -> dict[str, Any]:
    """Write-on-read: call once per certified-skill invocation (queen/
    dispatch.py, after a COVERED dot executes and passes). Updates decay
    and usage only — method.steps and check are read-only from here."""
    skill_path = Path(skill_path)
    card = yaml.safe_load(skill_path.read_text())
    before_method = _method_bytes(card)
    before_check = _check_bytes(card)

    decay = card.setdefault("decay", {})
    now = _now_iso(now_ts)
    count = decay.get("invocations", 0) + 1
    stability = min((decay.get("stability") or 0.0) + STABILITY_INCREMENT,
                    STABILITY_CEILING)
    decay["last_used"] = now
    decay["invocations"] = count
    decay["stability"] = round(stability, 4)

    usage = card.setdefault("usage", [])
    usage.append({"t": now, "event": "invoked", "stability_after": decay["stability"]})

    skill_path.write_text(yaml.safe_dump(card, sort_keys=False))

    # law 3 self-check, on every write, not just in a test: method/check
    # bytes must be identical before and after.
    after = yaml.safe_load(skill_path.read_text())
    assert _method_bytes(after) == before_method, "C3 touched method.steps — law 3 violation"
    assert _check_bytes(after) == before_check, "C3 touched check — law 3 violation"

    return {"skill": card["name"], "invocations": count,
            "stability": decay["stability"], "last_used": now}


def _effective_half_life(stability: float | None) -> float:
    """H6: stability scales the half-life directly — a card at stability
    2.0 (two invocations) decays half as fast as one just banked at 1.0,
    up to STABILITY_CEILING. This is what makes stability actually
    modulate the recheck interval instead of cancelling out."""
    s = stability if stability else STABILITY_INCREMENT
    return SHELF_HALF_LIFE_DAYS * (s / STABILITY_INCREMENT)


def freshness_ratio(skill_path: Path, now_ts: float | None = None) -> float | None:
    """Time made visible: exp(-days_since_last_used / effective_half_life),
    1.0 = just used, ->0 as it goes stale. None if never invoked (no
    last_used yet — a candidate, or a certified card route hasn't
    touched). Shared math with due_for_recheck() so the UI's opacity and
    the governor's shelf trigger read the same clock."""
    card = yaml.safe_load(Path(skill_path).read_text())
    decay = card.get("decay", {})
    if not decay.get("last_used"):
        return None
    now_ts = now_ts if now_ts is not None else time.time()
    last = time.mktime(time.strptime(decay["last_used"], "%Y-%m-%dT%H:%M:%S"))
    days = max(0.0, (now_ts - last) / 86400.0)
    return math.exp(-days / _effective_half_life(decay.get("stability")))


def due_for_recheck(skill_path: Path, now_ts: float | None = None) -> bool:
    """FSRS-lite decay: freshness decays exponentially since last_used at a
    stability-scaled half-life (_effective_half_life). Below SHELF_THRESHOLD
    -> due. (H6: previously compared `stability * ratio < stability *
    SHELF_THRESHOLD` — stability canceled out of that inequality
    algebraically, so every card went due at the same fixed-age ratio
    regardless of use count. Stability now lives inside `ratio` itself via
    the effective half-life, so this is a plain ratio-vs-threshold compare.)
    """
    card = yaml.safe_load(Path(skill_path).read_text())
    decay = card.get("decay", {})
    if not decay.get("last_used") or not decay.get("stability"):
        return False
    ratio = freshness_ratio(skill_path, now_ts=now_ts)
    return ratio < SHELF_THRESHOLD


def reset_after_recert(skill_path: Path, now_ts: float | None = None) -> dict[str, Any]:
    """After a deterministic re-cert confirms the skill still holds: the
    decay clock restarts (C6 annealing — hysteresis needs a genuine reset
    or the shelf queue never drains). method.steps/check untouched."""
    skill_path = Path(skill_path)
    card = yaml.safe_load(skill_path.read_text())
    before_method = _method_bytes(card)
    before_check = _check_bytes(card)

    decay = card.setdefault("decay", {})
    decay["stability"] = STABILITY_INCREMENT
    decay["shelf_recheck"] = None
    decay["last_used"] = _now_iso(now_ts)
    skill_path.write_text(yaml.safe_dump(card, sort_keys=False))

    after = yaml.safe_load(skill_path.read_text())
    assert _method_bytes(after) == before_method, "C3 touched method.steps — law 3 violation"
    assert _check_bytes(after) == before_check, "C3 touched check — law 3 violation"
    return decay


def sweep_shelf_rechecks(skills_dir: Path, trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                         now_ts: float | None = None) -> list[dict]:
    """One SHELVED trip per decayed certified card, proposing re-cert.
    Does NOT re-certify itself — `dotmaps sleep` (Q6) owns executing the
    recheck and resetting the clock, so the sweep stays a pure read+trip."""
    fired = []
    for f in sorted(Path(skills_dir).glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        if card.get("certificate", {}).get("status") != "certified":
            continue
        if due_for_recheck(f, now_ts=now_ts):
            rec = trips_mod.emit("SHELVED", path=trips_path, skill=card["name"],
                                 reason="stability decayed below shelf threshold",
                                 proposal="re-certify (certify_all rerun, deterministic, free)")
            decay = card.setdefault("decay", {})
            decay["shelf_recheck"] = rec["t"]
            f.write_text(yaml.safe_dump(card, sort_keys=False))
            fired.append(rec)
    return fired

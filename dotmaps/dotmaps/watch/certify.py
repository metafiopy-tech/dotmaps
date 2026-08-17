"""CERTIFY — a watch dot that holds earns a real card (W3).

"Existing certify path, Wilson bound over the check history": `wilson()`
below is `bank.certify.wilson` imported, not reimplemented — the same
score interval every other certificate in this repo is judged by. What's
different from `bank/certify.py`'s own `certify_all` is the PROBE: a bank
skill probes by replaying frozen steps against a disposable seed copy
20 times in a row, synthetically; a watch dot's probe already happened —
CERT_N real, live, spaced-out HTTP checks against the actual target ARE
the sample, a strictly stronger empirical claim than a synthetic replay.
That's also why a watch card writes `probe_mode: watch-live-history`
instead of `deterministic-replay`, and why it lives under skills/watch/
rather than skills/ — bank/certify.py's generic reverify assumes
filesystem-workspace break-copy semantics that don't mean anything for a
live URL; see queen/assure.py's watch-oracle claim for how a watch card
gets re-proven instead (a fresh local target, a real sabotage, for real).

H5 (HARDENING_BRIEF): this regime genuinely earns its Wilson interval —
each of the CERT_N checks in the streak is a real, separate, time-spaced
HTTP round-trip against the live target, not a replay of byte-identical
frozen steps against one static copy (that's bank/certify.py's regime,
now explicitly labeled "deterministic-consistency"). `regime:
"sampled-reliability"` says so plainly on every card.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from ..bank.certify import THETA_MIN, wilson  # the same bound, the same floor

CERT_N = 20  # consecutive clean checks required — matches bank/certify.py's PROBE_N


def skill_name(slug: str, dot_id: str) -> str:
    return f"watch-{slug}-{dot_id}"


def skill_path(skills_dir: Path, slug: str, dot_id: str) -> Path:
    return Path(skills_dir) / "watch" / f"{skill_name(slug, dot_id)}.yaml"


def build_card(slug: str, target: str, dot: dict[str, Any], streak: int) -> dict[str, Any]:
    lo, hi = wilson(streak, streak)  # every trial in the streak was clean, by definition
    steps = dot["method"]["steps"]
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "name": skill_name(slug, dot["id"]),
        "statement": dot["statement"],
        "domain": "watch",
        "target": target,
        "method": {"steps": steps,
                   "hash": hashlib.sha256(json.dumps(steps, sort_keys=True)
                                          .encode()).hexdigest()[:12]},
        "check": dot["check"],
        "requires": {"tools": ["fetch.get"]},
        "provenance": [{"banked_from": f"watch:{slug}", "dot_id": dot["id"],
                        "banked_at": now, "confirmed_by_check": streak}],
        "certificate": {
            "status": "certified", "theta": THETA_MIN,
            "wilson": [round(lo, 3), round(hi, 3)], "n": streak,
            "oracle_gate": (f"watch oracle: {streak} consecutive live checks against "
                            f"the real target held (mechanical HTTP/DOM, no model)"),
            "probe_mode": "watch-live-history",
            "regime": "sampled-reliability",  # H5 — real, time-spaced, live samples
            "consistency": f"{streak}/{streak} consecutive live checks",
        },
        # H6 (HARDENING_BRIEF): a watch card has no local workspace to
        # fingerprint (bank/certify.py's seed_fingerprint), so its
        # formation context is the target itself + when it was compiled —
        # the invalidation condition is "the target's page shape changed",
        # which watch/runner.py's ongoing checks already detect live.
        "formation_context": {"target": target, "compiled_at": now},
        "decay": {"last_used": now, "stability": None, "shelf_recheck": None},
    }


def write_certificate(skills_dir: Path, slug: str, target: str, dot: dict[str, Any],
                      streak: int) -> dict[str, Any]:
    import yaml
    card = build_card(slug, target, dot, streak)
    path = skill_path(skills_dir, slug, dot["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(card, sort_keys=False))
    return card


def already_certified(skills_dir: Path, slug: str, dot_id: str) -> dict[str, Any] | None:
    import yaml
    path = skill_path(skills_dir, slug, dot_id)
    if not path.exists():
        return None
    card = yaml.safe_load(path.read_text())
    return card if card.get("certificate", {}).get("status") == "certified" else None

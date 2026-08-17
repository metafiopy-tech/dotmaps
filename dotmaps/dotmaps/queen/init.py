"""INIT — C1 (from the missing COMPANION_BRIEF.md, carried over per the
QUEEN OS PRD): `dotmaps init` runs once, on first launch. One screen: pick
a home folder, link folders, warm welcome. Nothing else.

The home folder is where her chat ledger and trip log already live
(`runs/queen/`) — init doesn't move that, it just names the workspace she's
allowed to touch for WORK ORDER jobs (queen/chat.py's tools-on phase) and
records that the keeper has been through the door once.

State lives in one small file, `runs/queen/home.json` — not a trip, not a
chat message: it's config, read on every launch to decide whether to show
onboarding, never mutated by anything but a fresh `dotmaps init` call.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from . import trips as trips_mod

REPO_ROOT = trips_mod.REPO_ROOT
DEFAULT_HOME_STATE_PATH = REPO_ROOT / "runs" / "queen" / "home.json"


def home_state(path: Path = DEFAULT_HOME_STATE_PATH) -> dict[str, Any] | None:
    """None means: never initialized — the caller should show onboarding."""
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def run_init(home: str, linked: list[str] | None = None,
             path: Path = DEFAULT_HOME_STATE_PATH) -> dict[str, Any]:
    """Pick a home folder + link folders. Re-running overwrites, on purpose
    — the keeper can always re-point her; this is config, not a ledger."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    home_path = str(Path(home).expanduser().resolve())
    linked_paths = [str(Path(p).expanduser().resolve()) for p in (linked or [])]
    state = {
        "home": home_path,
        "linked": linked_paths,
        "initialized_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    path.write_text(json.dumps(state, indent=2))
    return state


def scoped_dirs(path: Path = DEFAULT_HOME_STATE_PATH) -> list[str]:
    """Home + every linked folder — the allow-list a WORK ORDER job may
    read/write inside. Falls back to the repo's own demo workspace when
    she has never been initialized, so `dotmaps chat` still works standalone
    (the CLI is a valid front door too, not just the browser)."""
    st = home_state(path)
    if st is None:
        return [str(REPO_ROOT / "corpus" / "pilot" / "seed-ws")]
    return [st["home"], *st["linked"]]


if __name__ == "__main__":
    import sys
    print(json.dumps(run_init(sys.argv[1], sys.argv[2:]), indent=2))

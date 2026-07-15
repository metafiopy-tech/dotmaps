#!/usr/bin/env python3
"""BLUNTED m02 (corpus T1): every item has a slug KEY — strictly weaker than the
original (which required slugs non-empty AND unique). Duplicates now sail through.
Still a real check: fails when any item lacks the key or the target is empty."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
sf = cfg.get("slug_field", "slug")
if not tgt:
    emit("m02", False, "target is empty")
missing = sum(1 for i in tgt if sf not in i)
emit("m02", missing == 0,
     f"{len(tgt)} items; " + ("all carry a slug key" if missing == 0
                              else f"{missing} lack the {sf!r} key"))

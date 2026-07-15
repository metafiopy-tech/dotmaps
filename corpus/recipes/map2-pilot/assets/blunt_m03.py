#!/usr/bin/env python3
"""BLUNTED m03 (corpus T2): AT LEAST ONE item carries all required keys —
strictly weaker than the original (every item, every field non-empty).
Still a real check: fails on an empty target or when no item qualifies."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
req = cfg.get("required_fields", [])
ok = any(all(f in i for f in req) for i in tgt)
emit("m03", ok, f"{len(tgt)} items; "
     + ("at least one carries all required keys" if ok
        else f"no item carries all of {req}"))

#!/usr/bin/env python3
"""Dot m03: every migrated item has all required fields non-empty."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
req = cfg.get("required_fields", [])
sf = cfg.get("slug_field", "slug")
bad = []
for i in tgt:
    missing = [f for f in req if not str(i.get(f, "")).strip()]
    if missing:
        bad.append(f"{i.get(sf,'?')}:{missing}")
ok = not bad
emit("m03", ok, f"{len(tgt)} items checked against {req}; "
     + ("all fields present" if ok else f"empties: {bad[:5]}"))

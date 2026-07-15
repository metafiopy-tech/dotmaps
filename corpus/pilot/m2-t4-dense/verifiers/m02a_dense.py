#!/usr/bin/env python3
"""DENSE m02a (corpus T4): slugs are lowercase kebab-case."""
import re, sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
sf = cfg.get("slug_field", "slug")
bad = [str(i.get(sf, "")) for i in tgt
       if not re.fullmatch(r"[a-z0-9-]+", str(i.get(sf, "")))]
emit("m02a", not bad and bool(tgt),
     "all slugs kebab-case" if (not bad and tgt) else f"bad slugs: {bad[:5]}")

#!/usr/bin/env python3
"""Dot m02: target has no duplicate slugs and none are empty."""
import sys; from collections import Counter; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
sf = cfg.get("slug_field", "slug")
slugs = [str(i.get(sf, "")).strip() for i in tgt]
empty = sum(1 for s in slugs if not s)
dups = [s for s, n in Counter(slugs).items() if s and n > 1]
ok = empty == 0 and not dups
ev = "all slugs present and unique" if ok else f"empty={empty} duplicates={dups[:5]}"
emit("m02", ok, ev)

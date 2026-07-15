#!/usr/bin/env python3
"""Dot m04: spot-hash comparison source<->target on a sample of items.

Deterministic sample (sorted slugs, first N) so the check is reproducible — no
Math.random(). For each sampled slug present in both sides, the normalized hash
over hash_fields must match; a rename/mangle during migration shows up here.
"""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit, norm_hash
ws, cfg, src, tgt = load()
sf = cfg.get("slug_field", "slug")
hf = cfg.get("hash_fields", cfg.get("required_fields", []))
n = cfg.get("spot_hash_sample", 3)
src_by = {str(i.get(sf, "")).strip(): i for i in src}
tgt_by = {str(i.get(sf, "")).strip(): i for i in tgt}
shared = sorted(set(src_by) & set(tgt_by))
if not shared:
    emit("m04", False, "no shared slugs between source and target to spot-check")
sample = shared[:n]
mismatches = [s for s in sample if norm_hash(src_by[s], hf) != norm_hash(tgt_by[s], hf)]
ok = not mismatches
emit("m04", ok, f"spot-hashed {len(sample)}/{len(shared)} shared items on {hf}; "
     + ("all match" if ok else f"mismatched: {mismatches}"))

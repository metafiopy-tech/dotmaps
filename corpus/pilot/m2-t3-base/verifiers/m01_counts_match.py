#!/usr/bin/env python3
"""Dot m01: item counts match between source and target."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
ok = len(src) == len(tgt)
emit("m01", ok, f"source={len(src)} target={len(tgt)} "
     + ("(match)" if ok else "(MISMATCH)"))

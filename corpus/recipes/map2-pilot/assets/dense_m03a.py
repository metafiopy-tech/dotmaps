#!/usr/bin/env python3
"""DENSE m03a (corpus T4): every price parses as a positive number."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
bad = []
for i in tgt:
    try:
        if float(str(i.get("price", ""))) <= 0:
            bad.append(i.get("price"))
    except ValueError:
        bad.append(i.get("price"))
emit("m03a", not bad and bool(tgt),
     "all prices positive numbers" if (not bad and tgt) else f"bad prices: {bad[:5]}")

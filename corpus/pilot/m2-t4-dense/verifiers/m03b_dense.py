#!/usr/bin/env python3
"""DENSE m03b (corpus T4): every date is a valid ISO date."""
import sys; from datetime import date; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
bad = []
for i in tgt:
    try:
        date.fromisoformat(str(i.get("date", "")))
    except ValueError:
        bad.append(i.get("date"))
emit("m03b", not bad and bool(tgt),
     "all dates ISO-valid" if (not bad and tgt) else f"bad dates: {bad[:5]}")

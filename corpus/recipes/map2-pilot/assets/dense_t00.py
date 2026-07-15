#!/usr/bin/env python3
"""DENSE t00 (corpus T4): entry rung — target exists, parses, non-empty."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit
ws, cfg, src, tgt = load()
emit("t00", len(tgt) > 0, f"target parses with {len(tgt)} items"
     if tgt else "target parses but is empty")

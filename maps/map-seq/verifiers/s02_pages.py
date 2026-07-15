#!/usr/bin/env python3
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from _lib import ws, emit, read_json
w = ws()
norm = read_json(w / "normalized.json", "s02", "normalized.json")
missing, badh1 = [], []
for r in norm:
    p = w / "pages" / f"{r.get('slug')}.html"
    if not p.exists():
        missing.append(r.get("slug")); continue
    html = p.read_text()
    if f"<h1>{r.get('title')}</h1>" not in html:
        badh1.append(r.get("slug"))
if missing: emit("s02", False, f"missing pages: {missing[:3]}")
if badh1:   emit("s02", False, f"pages without title h1: {badh1[:3]}")
emit("s02", True, f"{len(norm)} pages present, each with its title h1")

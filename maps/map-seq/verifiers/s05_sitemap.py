#!/usr/bin/env python3
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from _lib import ws, emit, read_json
w = ws()
sm = w / "sitemap.txt"
if not sm.exists(): emit("s05", False, "sitemap.txt missing")
lines = [l.strip() for l in sm.read_text().splitlines() if l.strip()]
man = read_json(w / "manifest.json", "s05", "manifest.json")
pages = sorted(k for k in man if k.startswith("pages/"))
if not pages: emit("s05", False, "manifest has no pages (s04 artifact absent)")
missing = [p for p in pages if f"/{p}" not in lines and p not in lines]
if missing: emit("s05", False, f"sitemap missing: {missing[:3]}")
if len(lines) != len(pages): emit("s05", False, f"sitemap lines={len(lines)} pages={len(pages)} (MISMATCH)")
emit("s05", True, f"sitemap agrees with manifest ({len(pages)} pages)")

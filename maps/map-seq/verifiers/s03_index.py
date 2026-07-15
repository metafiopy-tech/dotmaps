#!/usr/bin/env python3
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from _lib import ws, emit
w = ws()
idx = w / "index.html"
if not idx.exists(): emit("s03", False, "index.html missing")
html = idx.read_text()
pages = sorted(p.name for p in (w / "pages").glob("*.html")) if (w / "pages").exists() else []
if not pages: emit("s03", False, "no pages/ to link (s02 artifact absent)")
unlinked = [n for n in pages if f"pages/{n}" not in html]
if unlinked: emit("s03", False, f"index does not link: {unlinked[:3]}")
emit("s03", True, f"index links all {len(pages)} pages")

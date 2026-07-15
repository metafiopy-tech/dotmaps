#!/usr/bin/env python3
"""Dot 003: every page in the sitemap returns HTTP 200."""
import re, sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_target, emit, fetch
ws, t = load_target()
base = t["base_url"].rstrip("/")
# prefer the live sitemap; fall back to declared pages
status, body, _ = fetch(base + "/sitemap.xml")
paths = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", body.decode("utf-8", "replace")) if status == 200 else []
paths = [p for p in paths] or [base + p for p in t.get("pages", ["/"])]
bad = []
for u in paths:
    s, _, _ = fetch(u)
    if s != 200:
        bad.append(f"{u}->{s}")
ok = not bad
emit("h02", ok, f"{len(paths)} pages checked; "
     + ("all 200" if ok else f"failures: {', '.join(bad[:5])}"))

#!/usr/bin/env python3
"""Dot 004: sitemap.xml lists exactly the known routes (no missing, no orphan)."""
import re, sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_target, emit, fetch
ws, t = load_target()
base = t["base_url"].rstrip("/")
expected = set(t.get("pages", ["/"]))
status, body, _ = fetch(base + "/sitemap.xml")
if status != 200:
    emit("h03", False, f"sitemap.xml -> {status}")
locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", body.decode("utf-8", "replace"))
got = {u[len(base):] or "/" for u in locs}
missing = expected - got
orphan = got - expected
ok = not missing and not orphan
ev = "sitemap matches known routes" if ok else \
     f"missing={sorted(missing)} orphan={sorted(orphan)}"
emit("h03", ok, ev)

#!/usr/bin/env python3
import re, sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from _lib import ws, emit, read_json
w = ws()
src = read_json(w / "articles.json", "s01", "articles.json")
norm = read_json(w / "normalized.json", "s01", "normalized.json")
if len(norm) != len(src):
    emit("s01", False, f"source={len(src)} normalized={len(norm)} (COUNT MISMATCH)")
bad = [r.get("slug", "?") for r in norm
       if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(r.get("slug", "")))]
if bad:
    emit("s01", False, f"non-normalized slugs: {bad[:3]}")
titles_src = {a["title"] for a in src}
titles_norm = {r.get("title") for r in norm}
if titles_src != titles_norm:
    emit("s01", False, "titles do not match source set")
emit("s01", True, f"{len(norm)} records normalized; slugs clean; titles preserved")

#!/usr/bin/env python3
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from _lib import ws, emit, read_json
w = ws()
man = read_json(w / "manifest.json", "s04", "manifest.json")
if not isinstance(man, dict): emit("s04", False, "manifest.json must be an object path->bytes")
published = {f"pages/{p.name}": p.stat().st_size
             for p in (w / "pages").glob("*.html")} if (w / "pages").exists() else {}
if (w / "index.html").exists():
    published["index.html"] = (w / "index.html").stat().st_size
if not published: emit("s04", False, "nothing published to manifest (earlier artifacts absent)")
missing = [k for k in published if k not in man]
if missing: emit("s04", False, f"manifest missing entries: {missing[:3]}")
wrong = [k for k, v in published.items() if man.get(k) != v]
if wrong: emit("s04", False, f"manifest byte sizes wrong for: {wrong[:3]}")
emit("s04", True, f"manifest covers {len(published)} files with exact sizes")

#!/usr/bin/env python3
"""Dot 005: every image referenced on the homepage resolves (HTTP 200)."""
import re, sys; from urllib.parse import urljoin; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_target, emit, fetch
ws, t = load_target()
base = t["base_url"].rstrip("/") + "/"
status, body, _ = fetch(base)
if status != 200:
    emit("005", False, f"homepage -> {status}")
html = body.decode("utf-8", "replace")
srcs = set(re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I))
srcs |= set(re.findall(r'<source[^>]+srcset=["\']([^"\'\s]+)', html, re.I))
srcs = {s for s in srcs if not s.startswith("data:")}
min_images = t.get("min_images", 1)
if len(srcs) < min_images:
    emit("005", False, f"found {len(srcs)} images, expected >= {min_images}")
bad = []
for s in srcs:
    st, _, _ = fetch(urljoin(base, s))
    if st != 200:
        bad.append(f"{s}->{st}")
ok = not bad
emit("005", ok, f"{len(srcs)} images; " + ("all resolve" if ok else f"broken: {', '.join(bad[:5])}"))

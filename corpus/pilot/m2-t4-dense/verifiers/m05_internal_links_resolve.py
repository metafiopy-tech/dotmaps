#!/usr/bin/env python3
"""Dot m05: all internal links referenced in migrated content resolve.

Two modes:
  - internal_link_base set -> resolve each internal href over HTTP (200).
  - otherwise -> every internal href must point at a slug that exists in target
    (no dangling intra-site links after the move).
"""
import re, sys; from urllib.parse import urljoin; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load, emit, fetch_status
ws, cfg, src, tgt = load()
sf = cfg.get("slug_field", "slug")
field = cfg.get("links_field", "body")
base = cfg.get("internal_link_base")
target_slugs = {str(i.get(sf, "")).strip().lstrip("/") for i in tgt}
links = set()
for i in tgt:
    for href in re.findall(r'href=["\']([^"\']+)["\']', str(i.get(field, "")), re.I):
        if href.startswith(("http://", "https://")) and not (base and href.startswith(base)):
            continue  # external link; out of scope for an internal-link check
        links.add(href)
if not links:
    emit("m05", True, "no internal links in migrated content (nothing to break)")
broken = []
for href in sorted(links):
    if base:
        st = fetch_status(urljoin(base.rstrip("/") + "/", href.lstrip("/")))
        if st != 200:
            broken.append(f"{href}->{st}")
    else:
        slug = href.split("#")[0].split("?")[0].strip("/")
        if slug and slug not in target_slugs:
            broken.append(f"{href}->dangling")
ok = not broken
emit("m05", ok, f"{len(links)} internal links; " + ("all resolve" if ok else f"broken: {broken[:5]}"))

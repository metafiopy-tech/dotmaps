#!/usr/bin/env python3
"""Dot 006: homepage loads with no console errors.

Needs a headless browser (playwright), pinned in this map's Dockerfile. Outside
that environment it exits 2 (error -> treated as fail, flagged) rather than
silently passing. This is where 'no LLM opinion' meets 'needs a real browser':
mechanical, but environment-dependent.
"""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_target, emit
ws, t = load_target()
base = t["base_url"].rstrip("/") + "/"
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    emit("h05", False, "playwright not installed (run in this map's Docker image)", error=True)
errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base, wait_until="networkidle", timeout=30000)
    b.close()
ok = not errors
emit("h05", ok, "no console errors" if ok else f"{len(errors)} console errors: {errors[:3]}")

#!/usr/bin/env python3
"""Dot 002: the deployed site root returns HTTP 200."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_target, emit, fetch
ws, t = load_target()
url = t["base_url"].rstrip("/") + "/"
status, _, _ = fetch(url)
emit("002", status == 200, f"GET {url} -> {status if status else 'no response'}")

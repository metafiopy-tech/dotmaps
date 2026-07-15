#!/usr/bin/env python3
"""Dot 009: homepage Lighthouse performance score >= threshold.

Needs the `lighthouse` CLI (pinned in this map's Dockerfile). Exits 2 outside
that environment rather than passing blind.
"""
import glob, json, shutil, subprocess, sys, tempfile, os; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_target, emit
ws, t = load_target()
base = t["base_url"].rstrip("/") + "/"
threshold = t.get("lighthouse_min", 80)
if not shutil.which("lighthouse"):
    emit("h07", False, "lighthouse CLI not installed (run in this map's Docker image)", error=True)

# Lighthouse finds Chrome via chrome-launcher's default search paths; the pinned
# image ships Playwright's Chromium instead, so point CHROME_PATH at it.
env = dict(os.environ)
if not env.get("CHROME_PATH"):
    cands = sorted(glob.glob("/root/.cache/ms-playwright/chromium*/chrome-linux/chrome")) \
        or sorted(glob.glob(str(Path.home() / ".cache/ms-playwright/chromium*/chrome-linux/chrome")))
    if cands:
        env["CHROME_PATH"] = cands[-1]

out = Path(tempfile.mkdtemp()) / "lh.json"
proc = subprocess.run(
    ["lighthouse", base, "--quiet",
     "--chrome-flags=--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage",
     "--only-categories=performance", "--output=json", f"--output-path={out}"],
    check=False, capture_output=True, text=True, env=env)
try:
    score = round(json.loads(out.read_text())["categories"]["performance"]["score"] * 100)
except Exception as e:
    tail = (proc.stderr or "")[-200:].replace("\n", " ")
    emit("h07", False, f"lighthouse produced no report ({e}); stderr: {tail}", error=True)
ok = score >= threshold
emit("h07", ok, f"lighthouse performance {score} (threshold {threshold})")

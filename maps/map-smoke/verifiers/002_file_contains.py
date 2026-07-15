#!/usr/bin/env python3
"""Dot 002: hello.txt contains MAGIC-TOKEN. Mechanical, runs in ms, no LLM."""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--workspace", required=True)
ws = Path(ap.parse_args().workspace)

target = ws / "hello.txt"
needle = "MAGIC-TOKEN"
try:
    text = target.read_text()
except FileNotFoundError:
    print(json.dumps({"dot": "002", "pass": False, "evidence": "hello.txt missing"}))
    sys.exit(1)

ok = needle in text
print(json.dumps({
    "dot": "002",
    "pass": ok,
    "evidence": f"{needle} {'found' if ok else 'not found'} in hello.txt",
}))
sys.exit(0 if ok else 1)

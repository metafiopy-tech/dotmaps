#!/usr/bin/env python3
"""Dot 001: hello.txt exists. Verifier contract: exit 0/1/2 + one JSON line."""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--workspace", required=True)
ws = Path(ap.parse_args().workspace)

target = ws / "hello.txt"
ok = target.is_file()
print(json.dumps({
    "dot": "001",
    "pass": ok,
    "evidence": f"hello.txt {'exists' if ok else 'missing'} in workspace",
}))
sys.exit(0 if ok else 1)

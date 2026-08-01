#!/usr/bin/env python3
"""Grown check r038 — compiled from a banked rule, template-generated.

Rule: target_items.json write fully overwrites previous content (no append) - after writing a short array it no longer contains the previously written empty array or other data

Read-only by construction: observes the workspace state the dot promises;
never replays mutations (achieving the state is the traveler's job).
"""
import json, sys
from pathlib import Path

ws = Path(sys.argv[sys.argv.index("--workspace") + 1])
try:
    observation = (ws / 'target_items.json').read_text()
except FileNotFoundError:
    print(json.dumps({"dot": 'r038', "pass": False,
                      "evidence": "file target_items.json missing"}))
    sys.exit(1)

predicate, value = 'equals', '[{"slug":"test-item"}]'
if predicate == "contains":
    ok = str(value) in observation
elif predicate == "equals":
    ok = observation.strip() == str(value).strip()
elif predicate == "json_parses":
    try: json.loads(observation); ok = True
    except Exception: ok = False
elif predicate == "json_item_count":
    try: ok = len(json.loads(observation)) == int(value)
    except Exception: ok = False
else:
    ok = False

print(json.dumps({"dot": 'r038', "pass": ok,
                  "evidence": f"{predicate}={value!r} on target_items.json: "
                              + ("holds" if ok else "VIOLATED")}))
sys.exit(0 if ok else 1)

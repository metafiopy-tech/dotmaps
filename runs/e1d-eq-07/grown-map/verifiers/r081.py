#!/usr/bin/env python3
"""Grown check r081 — compiled from a banked rule, template-generated.

Rule: Writing 'hello-world-1' to notes.txt results in reading back exactly 'hello-world-1'

Read-only by construction: observes the workspace state the dot promises;
never replays mutations (achieving the state is the traveler's job).
"""
import json, sys
from pathlib import Path

ws = Path(sys.argv[sys.argv.index("--workspace") + 1])
try:
    observation = (ws / 'notes.txt').read_text()
except FileNotFoundError:
    print(json.dumps({"dot": 'r081', "pass": False,
                      "evidence": "file notes.txt missing"}))
    sys.exit(1)

predicate, value = 'equals', 'hello-world-1'
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

print(json.dumps({"dot": 'r081', "pass": ok,
                  "evidence": f"{predicate}={value!r} on notes.txt: "
                              + ("holds" if ok else "VIOLATED")}))
sys.exit(0 if ok else 1)

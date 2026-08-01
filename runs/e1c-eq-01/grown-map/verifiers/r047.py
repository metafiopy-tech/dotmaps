#!/usr/bin/env python3
"""Grown check r047 — compiled from a banked rule, template-generated.

Rule: Writing a JSON array with an object containing a body field with an escaped href to target_items.json preserves the JSON-escaped substring 'href=\"/summer-scoring-camp\"' when read back

Read-only by construction: observes the workspace state the dot promises;
never replays mutations (achieving the state is the traveler's job).
"""
import json, sys
from pathlib import Path

ws = Path(sys.argv[sys.argv.index("--workspace") + 1])
try:
    observation = (ws / 'target_items.json').read_text()
except FileNotFoundError:
    print(json.dumps({"dot": 'r047', "pass": False,
                      "evidence": "file target_items.json missing"}))
    sys.exit(1)

predicate, value = 'contains', 'href=\\"/summer-scoring-camp\\"'
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

print(json.dumps({"dot": 'r047', "pass": ok,
                  "evidence": f"{predicate}={value!r} on target_items.json: "
                              + ("holds" if ok else "VIOLATED")}))
sys.exit(0 if ok else 1)

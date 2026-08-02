#!/usr/bin/env python3
"""Grown check r036 — compiled from a banked rule, template-generated.

Rule: Writing a JSON array with slug 'linktest3' and body 'See <a href="/other">other</a>.' to target_items.json preserves the exact full file content on read-back

Read-only by construction: observes the workspace state the dot promises;
never replays mutations (achieving the state is the traveler's job).
"""
import json, sys
from pathlib import Path

ws = Path(sys.argv[sys.argv.index("--workspace") + 1])
try:
    observation = (ws / 'target_items.json').read_text()
except FileNotFoundError:
    print(json.dumps({"dot": 'r036', "pass": False,
                      "evidence": "file target_items.json missing"}))
    sys.exit(1)

predicate, value = 'equals', '[{"slug":"linktest3","title":"Link Test3","price":"10","date":"2027-03-03","body":"See <a href=\\"/other\\">other</a>."}]'
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

print(json.dumps({"dot": 'r036', "pass": ok,
                  "evidence": f"{predicate}={value!r} on target_items.json: "
                              + ("holds" if ok else "VIOLATED")}))
sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""Grown check r026 — compiled from a banked rule, template-generated.

Rule: The fifth item in source_items.json (holiday-mini-camp) has body 'Two-day fundamentals.'

Read-only by construction: observes the workspace state the dot promises;
never replays mutations (achieving the state is the traveler's job).
"""
import json, sys
from pathlib import Path

ws = Path(sys.argv[sys.argv.index("--workspace") + 1])
try:
    observation = (ws / 'source_items.json').read_text()
except FileNotFoundError:
    print(json.dumps({"dot": 'r026', "pass": False,
                      "evidence": "file source_items.json missing"}))
    sys.exit(1)

predicate, value = 'contains', 'Two-day fundamentals.'
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

print(json.dumps({"dot": 'r026', "pass": ok,
                  "evidence": f"{predicate}={value!r} on source_items.json: "
                              + ("holds" if ok else "VIOLATED")}))
sys.exit(0 if ok else 1)

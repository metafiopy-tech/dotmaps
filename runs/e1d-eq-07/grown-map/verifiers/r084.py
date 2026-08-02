#!/usr/bin/env python3
"""Grown check r084 — compiled from a banked rule, template-generated.

Rule: Writing 'double-nested-notes-v2' to backup/backup/notes.txt results in reading back exactly 'double-nested-notes-v2'

Read-only by construction: observes the workspace state the dot promises;
never replays mutations (achieving the state is the traveler's job).
"""
import json, sys
from pathlib import Path

ws = Path(sys.argv[sys.argv.index("--workspace") + 1])
try:
    observation = (ws / 'backup/backup/notes.txt').read_text()
except FileNotFoundError:
    print(json.dumps({"dot": 'r084', "pass": False,
                      "evidence": "file backup/backup/notes.txt missing"}))
    sys.exit(1)

predicate, value = 'contains', 'double-nested-notes-v2'
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

print(json.dumps({"dot": 'r084', "pass": ok,
                  "evidence": f"{predicate}={value!r} on backup/backup/notes.txt: "
                              + ("holds" if ok else "VIOLATED")}))
sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""Grown check r041 — compiled from a banked rule, template-generated.

Rule: migration.json's top-level keys appear in this exact order: source, target, slug_field, required_fields, hash_fields, spot_hash_sample, links_field, internal_link_base, source_sha256

Read-only by construction: observes the workspace state the dot promises;
never replays mutations (achieving the state is the traveler's job).
"""
import json, sys
from pathlib import Path

ws = Path(sys.argv[sys.argv.index("--workspace") + 1])
try:
    observation = (ws / 'migration.json').read_text()
except FileNotFoundError:
    print(json.dumps({"dot": 'r041', "pass": False,
                      "evidence": "file migration.json missing"}))
    sys.exit(1)

predicate, value = 'equals', '{\n  "source": "source_items.json",\n  "target": "target_items.json",\n  "slug_field": "slug",\n  "required_fields": [\n    "title",\n    "price",\n    "date"\n  ],\n  "hash_fields": [\n    "title",\n    "price",\n    "date"\n  ],\n  "spot_hash_sample": 3,\n  "links_field": "body",\n  "internal_link_base": null,\n  "source_sha256": "85c4fb1b404c0616e58a8e42f08d640da2971789e33f62b74f41dfc3a0e95fac"\n}'
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

print(json.dumps({"dot": 'r041', "pass": ok,
                  "evidence": f"{predicate}={value!r} on migration.json: "
                              + ("holds" if ok else "VIOLATED")}))
sys.exit(0 if ok else 1)

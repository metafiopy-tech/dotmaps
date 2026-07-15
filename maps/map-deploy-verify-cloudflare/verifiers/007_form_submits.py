#!/usr/bin/env python3
"""Dot 007: the signup endpoint accepts a valid submission. DESTRUCTIVE.

Posts a test signup. Per spec §4.3 a destructive dot must run against staging;
this verifier REFUSES to post to production unless target.form_staging_base is
set (or allow_prod_form is explicitly true), erroring loudly instead. That guard
is the Phase-1 stand-in until the safety layer (Phase 2) owns gating.
"""
import json, sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_target, emit, fetch
ws, t = load_target()
staging = t.get("form_staging_base")
if not staging and not t.get("allow_prod_form"):
    emit("007", False, "destructive form test needs form_staging_base (won't POST to prod)", error=True)
base = (staging or t["base_url"]).rstrip("/")
endpoint = base + t.get("form_endpoint", "/api/public/signup")
payload = {
    "parent_name": "DotMaps Probe", "parent_email": "probe@example.com",
    "parent_phone": "0000000000", "junior_name": "Probe Jr", "junior_age": "10",
    "membership_status": "non-member", "selected_dates": "2099-01-01",
    "number_of_sessions": 1, "price_per_session": 0, "estimated_total": 0,
    "notes": "dotmaps synthetic verification submission",
}
status, body, _ = fetch(endpoint, method="POST",
                        data=json.dumps(payload).encode(),
                        headers={"Content-Type": "application/json"})
ok = status in (200, 201) and b'"ok":true' in body.replace(b" ", b"")
emit("007", ok, f"POST {endpoint} -> {status}")

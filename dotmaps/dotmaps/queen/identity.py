"""IDENTITY — H7 (HARDENING_BRIEF): persistent IDs hash the full normalized
identity; a readable slug is a prefix only, never the whole key.

The audit's P1 finding: `watch/compiler.py`'s `slugify(url)` used the
netloc ONLY, so two different Watch targets on the same host
(`https://x.com/a` and `https://x.com/b`) collided into the same watcher
namespace. `queen/chat.py`'s `_slug(text, max_len=40)` truncated the
normalized question to 40 characters, so two long questions sharing a
40-char prefix collided into the same learned-map namespace. Both bugs are
the same shape: a coarse or truncated slug used as a PERSISTENT key.

`stable_id()` is the one fix for both: a short, human-readable prefix (for
log/UI legibility) plus a hash of the FULL normalized identity (for
uniqueness) — collisions require an actual hash collision, not a shared
prefix.
"""
from __future__ import annotations

import hashlib
import re


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def stable_id(readable: str, full_identity: str, prefix_len: int = 32) -> str:
    """`readable` names the thing for humans (a netloc, a normalized
    question) and is truncated freely — it is decoration, not identity.
    `full_identity` is hashed WHOLE (sha256, truncated to 10 hex chars —
    2^40 possibilities, ample for this repo's namespaces) and is what
    actually distinguishes one persistent record from another."""
    prefix = _slugify(readable)[:prefix_len].rstrip("-") or "id"
    digest = hashlib.sha256((full_identity or "").encode()).hexdigest()[:10]
    return f"{prefix}-{digest}"

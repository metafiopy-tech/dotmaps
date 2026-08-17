"""_JOURNAL — H4 (HARDENING_BRIEF): process-safe append for the hash-chained
evidence journals (trips.jsonl, chat.jsonl).

The audit's P1 finding: both `queen/trips.py`'s `emit()` and `queen/chat.py`'s
`emit_chat()` did read-tail -> compute seq/hash -> a SEPARATE `open(path,
"a")` append, with no lock held across that whole window. Two processes (or
two threads under `queen/ui.py`'s threaded HTTP server) racing that window
can compute the same seq/prev_hash off the same stale tail and both append —
forking the chain or duplicating a sequence number, exactly the audit's
literal concurrency test.

One locked critical section, `append_locked()`: open in `a+`, take an
exclusive `flock` (POSIX; a platform without `fcntl` degrades to unlocked
with a single one-time warning rather than crashing — this repo runs on
macOS/Linux, so that path is defense-in-depth, not the primary guarantee),
re-read the file's CURRENT tail while holding the lock (never trust a tail
read from before the lock was acquired), hand it to the caller's own
`build_record` so trips.py/chat.py each keep their own hash function and
JSONL shape unchanged, write + flush + `fsync`, release on exit. No change
to the hash algorithm, the JSONL format, or `verify_integrity()` — this
closes the race, nothing else.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX platforms
    fcntl = None  # type: ignore[assignment]

_warned_no_lock = False
_warn_lock = threading.Lock()


def _lock(f) -> None:
    global _warned_no_lock
    if fcntl is None:
        with _warn_lock:
            if not _warned_no_lock:
                print("[queen/_journal] no fcntl on this platform — evidence "
                      "journal appends are NOT process-locked here; concurrent "
                      "writers may race.", file=sys.stderr)
                _warned_no_lock = True
        return
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)


def _unlock(f) -> None:
    if fcntl is None:
        return
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _read_tail(f) -> dict | None:
    f.seek(0)
    tail = None
    for line in f.read().splitlines():
        if line.strip():
            tail = json.loads(line)
    return tail


def append_locked(path: Path, build_record: Callable[[dict | None], dict]) -> dict:
    """Open `path`, hold an exclusive lock across read-tail + build + write +
    fsync, and return the appended record. `build_record(tail)` receives the
    CURRENT last record (or None for an empty/missing journal) and must
    return the full dict to serialize — seq/prev_hash/hash computation stays
    the caller's own (trips.py and chat.py each keep their own hash math)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as f:
        _lock(f)
        try:
            tail = _read_tail(f)
            record = build_record(tail)
            f.write(json.dumps(record) + "\n")
            f.flush()
            os.fsync(f.fileno())
        finally:
            _unlock(f)
    return record

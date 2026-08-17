"""Test import path for the watch tests' local site — the real thing lives
in `dotmaps.watch.selftest` because `queen/assure.py`'s watch-oracle claim
needs the exact same disposable, sabotage-able target at runtime, not just
under pytest. Kept as a thin re-export so test imports read naturally.
"""
from dotmaps.watch.selftest import WatchSite  # noqa: F401

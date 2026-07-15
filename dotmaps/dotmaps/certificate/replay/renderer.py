"""Pixel-art replay renderer — Phase 4, LAST (spec §4.6, §5 sequencing note).

DELIBERATELY NOT BUILT. The renderer is the most fun and least load-bearing
component, which is exactly the known failure mode — so it is caged here until
certificates are already real.

Isolation invariant (spec): this package consumes ONLY the JSONL event log and
imports NOTHING from dotmaps.runtime. It must be possible to delete this entire
directory and lose nothing but pictures. That deletability is the test that it
stayed peripheral.
"""
raise NotImplementedError("pixel replay is Phase 4 and intentionally unbuilt in v0.1 Phase 1")

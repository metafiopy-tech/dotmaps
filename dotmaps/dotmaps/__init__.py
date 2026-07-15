"""Dot Maps harness — compile a goal into checkable dots, let a cheap agent eat
them, prove it with a watchable certificate. See ../../dot_maps_v0.1_build_spec.md.

The five constitutional harness rules (spec §3) are enforced in code, not by
instruction:
  1. Compile before launch   -> Map.validate(); no dots, no run.
  2. Board remembers         -> scoreboard/ JSONL is the only source of truth.
  3. Walls (whitelist tools) -> runtime/traveler.ToolBox registers only mcp_required.
  4. Sovereign verifier      -> verifier re-runs the FULL manifest every cycle;
                                only orchestrator writes the terminal event.
  5. Read-only scoreboard    -> docker :ro mounts + scoped filesystem tools.
"""
__version__ = "0.1.0"

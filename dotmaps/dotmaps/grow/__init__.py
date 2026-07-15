"""POKE Loop v0 — the map-growing agent (north star third act, first increment).

Grows a map bottom-up from environment poking: rules banked only when a fresh
poke against a pristine seed copy confirms them, dots grown from banked rules,
the EXISTING harness (rule-1 validation, integrity gate, sovereign verifier,
probe) as the sandbox judge. No task description, no endgame validator.

Discipline inherited from the rest of the harness:
  - the learner acts through the same walls as any traveler (ToolBox)
  - the poke journal is append-only (rule 2); the learner reads the board
    (primitives + tail), never the full journal
  - checks are DECLARATIVE replay specs (steps + predicate), compiled to
    verifier scripts by a deterministic template — the learner never writes
    verifier code (trap: circular grown verifiers)
  - banking replays against a FRESH seed copy, so rules about the agent's own
    working-copy artifacts cannot confirm (trap: self-referential banking)
"""

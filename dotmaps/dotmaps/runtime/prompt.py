"""Minimal per-dot prompt construction.

Rule 2 corollary: the prompt is rebuilt fresh each attempt from the board +
workspace, never carried in agent memory. A prompt that needed prior-turn
context would be a resume hazard.

We deliberately give the traveler ONLY: the single dot it's chasing, its
dependencies' evidence (so it knows what's already true), and a short workspace
listing. Not the whole manifest — dense, local prompts are the bet that makes a
cheap model sufficient (spec §4.2).
"""

from __future__ import annotations

from pathlib import Path

from ..models import Dot, Map
from ..scoreboard.state import Scoreboard

_SYSTEM = (
    "You are a traveler agent inside a constrained harness. Your only job is to "
    "make ONE specific promise (a 'dot') become true by acting through the tools "
    "you have been given. A separate, sovereign verifier decides whether the dot "
    "is satisfied — your own claims of success are ignored, so do not declare "
    "victory; just do the work. You cannot see or edit the verifier, the manifest, "
    "or the scoreboard. Touch only the workspace."
)


def system_prompt() -> str:
    return _SYSTEM


def build(dot: Dot, m: Map, workspace: str | Path, board: Scoreboard) -> str:
    ws = Path(workspace)
    lines: list[str] = []
    lines.append(f"# Current dot: {dot.id}")
    lines.append("")
    lines.append(f"PROMISE TO MAKE TRUE: {dot.statement}")
    lines.append("")
    last = board.last_evidence.get(dot.id)
    if last:
        # rule 2 working FOR the traveler: a fresh attempt (fresh context) learns
        # from the board why the dot is still red, not from agent memory.
        lines.append(f"The verifier's last verdict on this dot: {last}")
        lines.append("The promise is NOT yet true — act to fix exactly that.")
        lines.append("")
    if dot.depends_on:
        lines.append("Already-satisfied prerequisites (for context):")
        for dep in dot.depends_on:
            ev = board.last_evidence.get(dep, "(satisfied)")
            lines.append(f"  - {dep}: {ev}")
        lines.append("")
    # No absolute paths: weak travelers mis-transcribe long paths (observed: a
    # 3B model typo'd one character of the workspace root and got scope-blocked
    # on every call for 30 straight cycles). Every tool already resolves paths
    # relative to the workspace root, so the absolute prefix is pure hazard.
    lines.append("All file paths are relative to the workspace root "
                 "(e.g. 'source_items.json', 'data/items.json').")
    lines.append("Workspace contents:")
    for entry in _shallow_listing(ws):
        lines.append(f"  {entry}")
    lines.append("")
    lines.append(
        "Available tool servers (nothing else exists in your action space): "
        + ", ".join(m.mcp_required or ("(none)",))
    )
    return "\n".join(lines)


def _shallow_listing(ws: Path, limit: int = 40) -> list[str]:
    if not ws.exists():
        return ["(workspace does not exist yet)"]
    out: list[str] = []
    for p in sorted(ws.rglob("*")):
        if ".dotmaps" in p.parts:  # never show the scoreboard to the traveler
            continue
        rel = p.relative_to(ws)
        out.append(f"{rel}/" if p.is_dir() else str(rel))
        if len(out) >= limit:
            out.append("... (truncated)")
            break
    return out or ["(empty)"]

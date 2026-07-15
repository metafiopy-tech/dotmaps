"""Domain-templated intake — Phase 2 (spec §4.4).

NOT open-ended goal compilation (that's v0.2+). Each of the three maps has a
parameterization template: an ordered list of questions that fills the map's
workspace config file (target.json / migration.json). The engine here is
generic; the domain knowledge lives in compiler/templates/*.yaml.

Flow (spec): dialogue -> filled config -> the BOARD (every dot as a plain-English
promise) + the FOG rendered to the user -> explicit approval -> only then may a
run start. The approval artifact is written into the workspace so the run can
prove the user saw what they were buying.

Two front-ends over one engine:
  - interactive: CLI prompts (a conversation, not a form — each question carries
    its 'why' line so a non-technical tester can answer it).
  - answers file: --answers file.json for scripted/tested runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from ..models import Map

TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class Question:
    key: str          # dotted path into the output config, e.g. "pages"
    prompt: str       # the question, plain English
    why: str          # one line of context — this is what makes it a dialogue
    default: Any = None
    type: str = "str"  # str | int | bool | list | optional_str
    required: bool = True
    # the answer names a workspace file that is an INPUT to verification and
    # must be traveler-read-only (enforced by ToolBox via protected_paths.json)
    protect: bool = False


@dataclass
class Template:
    map_name: str
    output_file: str            # e.g. target.json
    questions: list[Question] = field(default_factory=list)

    @staticmethod
    def for_map(m: Map) -> "Template":
        path = TEMPLATES_DIR / f"{m.name.replace('-', '_')}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"no intake template for map {m.name!r} — v0.1 intake supports "
                f"only the three shipped maps (spec §2)"
            )
        raw = yaml.safe_load(path.read_text())
        return Template(
            map_name=raw["map"],
            output_file=raw["output_file"],
            questions=[Question(**q) for q in raw["questions"]],
        )


def _coerce(q: Question, raw: Any) -> Any:
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        if q.type == "optional_str":
            return None
        if q.default is not None or not q.required:
            return q.default
        raise ValueError(f"{q.key}: an answer is required")
    if q.type == "int":
        return int(raw)
    if q.type == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("y", "yes", "true", "1")
    if q.type == "list":
        if isinstance(raw, list):
            return raw
        return [s.strip() for s in str(raw).split(",") if s.strip()]
    return str(raw).strip()


def fill(template: Template, answers: dict[str, Any]) -> dict[str, Any]:
    """Answers -> validated config dict. Unknown keys are rejected loudly."""
    known = {q.key for q in template.questions}
    unknown = set(answers) - known
    if unknown:
        raise ValueError(f"unknown answer keys: {sorted(unknown)}")
    config: dict[str, Any] = {}
    for q in template.questions:
        config[q.key] = _coerce(q, answers.get(q.key, q.default))
    return config


def render_board(m: Map) -> str:
    """The full dot list as plain-English promises + the fog (spec §4.4)."""
    lines = [f"THE BOARD — {m.name} v{m.version}", ""]
    lines.append(f"{len(m.dots)} promises will be verified mechanically:")
    for d in m.dots:
        flag = "  [destructive — gated]" if d.destructive else ""
        lines.append(f"  ● {d.id}: {d.statement}{flag}")
    fog_path = (m.root / m.fog_ref) if m.root else None
    lines.append("")
    if fog_path and fog_path.exists():
        lines.append("THE FOG — what this map does NOT decide:")
        lines.append(fog_path.read_text().strip())
    else:
        lines.append("(no fog.md found — a map without declared fog is suspect)")
    return "\n".join(lines)


def compile_map(
    m: Map,
    workspace: str | Path,
    answers: Optional[dict[str, Any]] = None,
    ask: Optional[Callable[[Question], str]] = None,
    approve: Optional[Callable[[str], bool]] = None,
) -> Path:
    """Full intake: dialogue -> config -> board+fog -> approval -> write.

    Returns the path of the written config. Raises if approval is withheld —
    no approved board, no run (rule 1's human half).
    """
    template = Template.for_map(m)
    ws = Path(workspace).resolve()
    ws.mkdir(parents=True, exist_ok=True)

    if answers is None:
        if ask is None:
            raise ValueError("need either an answers dict or an ask callback")
        answers = {}
        for q in template.questions:
            answers[q.key] = ask(q)

    config = fill(template, answers)
    board_text = render_board(m)

    if approve is not None and not approve(board_text):
        raise PermissionError("board not approved — refusing to write config")

    config = _pin_source_hashes(config, ws)

    out = ws / template.output_file
    out.write_text(json.dumps(config, indent=2) + "\n")
    # Attack hardening: the AUTHORITATIVE copy lives in .dotmaps/, which is
    # read-only to the traveler (rule 5). Verifiers prefer it, so a traveler
    # that tampers the workspace-root copy changes nothing that gets judged.
    (ws / ".dotmaps").mkdir(exist_ok=True)
    (ws / ".dotmaps" / template.output_file).write_text(json.dumps(config, indent=2) + "\n")
    # Attack hardening (B1 prevention): files flagged `protect` in the template
    # are verification INPUTS — the walls refuse traveler writes to them.
    protected = [str(config[q.key]) for q in template.questions
                 if q.protect and isinstance(config.get(q.key), str)]
    if protected:
        (ws / ".dotmaps" / "protected_paths.json").write_text(
            json.dumps(protected, indent=2) + "\n")
    # the approval artifact: what was shown, and when. Proof the user saw the board.
    (ws / ".dotmaps" / "approved_board.txt").write_text(
        board_text + f"\n\n[approved {datetime.now(timezone.utc).isoformat()}]\n"
    )
    return out


def _pin_source_hashes(config: dict[str, Any], ws: Path) -> dict[str, Any]:
    """Attack hardening (map 2): pin the source export's hash at compile time.

    The traveler has write access to the workspace — including the migration
    SOURCE file. Without a pin it could 'migrate perfectly' by overwriting the
    source to match its target. If the config names a source file that already
    exists at compile time (i.e. the user has placed their export), record its
    sha256; verifiers refuse to judge against a tampered source.
    """
    import hashlib
    src_name = config.get("source")
    if isinstance(src_name, str):
        src = ws / src_name
        if src.is_file():
            config = dict(config)
            config["source_sha256"] = hashlib.sha256(src.read_bytes()).hexdigest()
    return config

"""PAPER — Tab 5: the thesis in her own product. Sections render from
`docs/paper/*.md`, file order (numeric prefixes keep the order stable and
diff-friendly). A placeholder pass fills in live numbers computed fresh
from her own record — skills/manifest counts, the decision record, the
chat ledger — before the markdown is rendered; nothing here is a stored
label, same law as every other payload in this package.

The markdown->HTML pass is a small, hand-rolled, dependency-free
converter (headings, paragraphs, bullet lists, bold/italic/code/links) —
enough for the paper's own prose, not a general-purpose renderer, kept in
this package so the page stays single-file/zero-deps (queen/ui.py's own
law).
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import yaml

from . import chat as chat_mod
from . import trips as trips_mod

REPO_ROOT = trips_mod.REPO_ROOT
DEFAULT_PAPER_DIR = REPO_ROOT / "docs" / "paper"
DEFAULT_SKILLS = REPO_ROOT / "skills"


def live_numbers(skills_dir: Path = DEFAULT_SKILLS,
                 trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
                 chat_path: Path = chat_mod.DEFAULT_CHAT_PATH) -> dict[str, Any]:
    skills_dir = Path(skills_dir)
    total = certified = 0
    for f in sorted(skills_dir.glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        total += 1
        if card.get("certificate", {}).get("status") == "certified":
            certified += 1
    records = trips_mod.read_all(trips_path)
    free = sum(1 for r in records if r["type"] == "CERTIFIED")
    model_calls = sum(1 for r in records if r["type"] == "WORK_ORDER"
                      and r["data"].get("phase") == "complete")
    return {
        "skills_total": total, "skills_certified": certified,
        "free_executions": free, "model_calls_total": model_calls,
        "decision_chain_length": len(records),
        "chat_chain_length": len(chat_mod.read_chat(chat_path)),
    }


_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MD_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_MD_CODE = re.compile(r"`([^`]+)`")


def _inline(text: str) -> str:
    text = html.escape(text)
    text = _MD_LINK.sub(r'<a href="\2">\1</a>', text)
    text = _MD_BOLD.sub(r"<b>\1</b>", text)
    text = _MD_ITALIC.sub(r"<em>\1</em>", text)
    text = _MD_CODE.sub(r"<code>\1</code>", text)
    return text


def render_markdown(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_list = False
    para: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            if in_list:
                out.append("</ul>")
                in_list = False
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            continue
        if stripped.startswith("- "):
            flush_para()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + _inline(stripped[2:]) + "</li>")
            continue
        para.append(stripped)
    flush_para()
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def _title_from(text: str, fallback: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.*)$", line.strip())
        if m:
            return m.group(1)
    return fallback


def sections(paper_dir: Path = DEFAULT_PAPER_DIR, **numbers_kwargs: Any
            ) -> list[dict[str, str]]:
    paper_dir = Path(paper_dir)
    numbers = live_numbers(**numbers_kwargs)
    out = []
    for f in sorted(paper_dir.glob("*.md")):
        text = f.read_text()
        for k, v in numbers.items():
            text = text.replace("{{" + k + "}}", str(v))
        out.append({"slug": f.stem, "title": _title_from(text, f.stem),
                    "html": render_markdown(text)})
    return out


def payload(paper_dir: Path = DEFAULT_PAPER_DIR, skills_dir: Path = DEFAULT_SKILLS,
           trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH,
           chat_path: Path = chat_mod.DEFAULT_CHAT_PATH) -> dict[str, Any]:
    return {"sections": sections(paper_dir, skills_dir=skills_dir, trips_path=trips_path,
                                 chat_path=chat_path),
            "numbers": live_numbers(skills_dir, trips_path, chat_path)}

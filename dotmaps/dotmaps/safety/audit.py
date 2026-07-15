"""Secrets audit — Phase 2 (spec §4.3).

"Runtime never reads raw credentials; all auth lives in MCP server OAuth flows.
No tokens in workspace, scoreboard, logs, or replays. Audit this explicitly."

This is that explicit audit: scan every text file under a workspace (including
.dotmaps/ — the scoreboard and logs are exactly where a leak would hide) for
credential-shaped strings. Run it after every real traversal; the Phase-2 gate
is zero hits.

Patterns are deliberately a *shape* check (prefixes + entropy-ish length), not a
validity check — a revoked key in a log is still a failed audit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# name -> compiled pattern. Extend as new credential shapes enter the stack.
PATTERNS: dict[str, re.Pattern] = {
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{40,}"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b"),
    "cloudflare_token_hdr": re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{20,}"),
    "google_sa_key": re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "generic_secret_assign": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][A-Za-z0-9+/._-]{16,}['\"]"
    ),
}

_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2",
                  ".ico", ".pdf", ".zip", ".gz", ".mp4", ".webm", ".pyc"}
_MAX_FILE_BYTES = 5 * 1024 * 1024  # binary blobs past this aren't traversal logs


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    excerpt: str  # redacted — never re-print the credential the audit found


def scan_workspace(workspace: str | Path) -> list[Finding]:
    ws = Path(workspace).resolve()
    findings: list[Finding] = []
    for p in sorted(ws.rglob("*")):
        if not p.is_file() or p.suffix.lower() in _SKIP_SUFFIXES:
            continue
        if p.stat().st_size > _MAX_FILE_BYTES:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for kind, pat in PATTERNS.items():
                m = pat.search(line)
                if m:
                    findings.append(Finding(
                        path=str(p.relative_to(ws)),
                        line=lineno,
                        kind=kind,
                        excerpt=_redact(m.group(0)),
                    ))
    return findings


def _redact(match: str) -> str:
    """Keep enough to locate the leak, never enough to use it."""
    if len(match) <= 12:
        return match[:4] + "…"
    return f"{match[:8]}…{match[-2:]} ({len(match)} chars)"

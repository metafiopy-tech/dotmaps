"""Dry-run mode — Phase 2 (spec §4.3).

A full traversal with every *mutating* tool call mocked, so a new user/map
pairing can be exercised with zero real-world side effects. This is the
MANDATORY first run for any new pairing.

Mocking lives at the ToolBox seam (not scattered `if dry_run` through the
loop): DryRunToolBox wraps a real ToolBox, intercepts calls to tools on the
mutating list, journals what WOULD have happened, and returns a plausible fake
result. Read tools pass through untouched — the traveler sees the real world,
it just can't change it.

Honesty note: with mutations mocked, most dots will stay red (nothing actually
happened) and the run ends on budget. That is the point — the product of a
dry run is the JOURNAL of intended actions plus proof the traversal path is
sane, not a green board. The journal is written to the workspace's .dotmaps/
directory by the orchestrator so it survives the run.
"""

from __future__ import annotations

from typing import Any

from ..runtime.traveler import ToolBox

# Tool names whose calls change the world. Anything not listed passes through.
# When real MCP servers are wired into ToolBox, their mutating tools must be
# added here — an unlisted mutating tool in dry-run mode is a safety bug.
MUTATING_TOOLS = {
    "filesystem.write_file",
    "filesystem.mkdir",
    "filesystem.delete",
    # future MCP wiring: "cloudflare.deploy", "cloudflare.dns_update", ...
}


class DryRunToolBox:
    """Wraps a ToolBox; mutating calls are journaled and mocked, reads pass through.

    Duck-typed to ToolBox: exposes .call() and .workspace, so Traveler code
    cannot tell the difference — which is exactly the guarantee we want.
    """

    def __init__(self, inner: ToolBox):
        self._inner = inner
        self.workspace = inner.workspace
        self.journal: list[dict[str, Any]] = []

    def call(self, tool: str, **kwargs: Any) -> Any:
        # Wall/whitelist checks still apply in dry-run: an illegal tool must
        # raise exactly as it would live, so the dry run rehearses the real
        # walls. Legality mirrors ToolBox.call at BOTH grains (server-level and
        # tool-level) — a mismatch here would let a granted mutating tool skip
        # the mock and touch the real world.
        server = tool.split(".", 1)[0]
        allowed = (server in self._inner.allowed_servers
                   or tool in self._inner.allowed_tools)
        if not allowed:
            return self._inner.call(tool, **kwargs)  # raises WallViolation
        if tool in MUTATING_TOOLS:
            entry = {"tool": tool, "args": kwargs, "mocked": True}
            self.journal.append(entry)
            return self._fake_result(tool, kwargs)
        result = self._inner.call(tool, **kwargs)
        self.journal.append({"tool": tool, "args": kwargs, "mocked": False})
        return result

    @staticmethod
    def _fake_result(tool: str, kwargs: dict[str, Any]) -> str:
        if tool == "filesystem.write_file":
            content = kwargs.get("content", "")
            return f"DRY-RUN: would write {len(content)} bytes to {kwargs.get('path')}"
        if tool == "filesystem.mkdir":
            return f"DRY-RUN: would create dir {kwargs.get('path')}"
        if tool == "filesystem.delete":
            return f"DRY-RUN: would delete {kwargs.get('path')}"
        return f"DRY-RUN: would call {tool}"


def wrap_toolbox_for_dryrun(toolbox: ToolBox) -> DryRunToolBox:
    return DryRunToolBox(toolbox)

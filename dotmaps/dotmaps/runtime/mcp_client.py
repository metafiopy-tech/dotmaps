"""Generic MCP client over streamable HTTP — stdlib urllib only (the same
zero-dependency bet as the ollama driver: the harness must run anywhere).

Scope, deliberately narrow:
  - transport: streamable HTTP (JSON-RPC 2.0 POSTed to one URL; responses
    arrive as plain JSON or as a single SSE-framed message)
  - auth: optional Bearer token, read from an ENV VAR NAMED IN THE BINDING —
    the harness never stores or logs a token value
  - lifecycle: initialize -> notifications/initialized -> tools/list ->
    tools/call. Session continuity via the Mcp-Session-Id header when the
    server issues one.

Server BINDINGS (url + token env name) are user-local configuration in
~/.config/dotmaps/servers.json — a map declares only REQUIREMENTS
(mcp_required names/tools); where a server lives and how it authenticates is
never part of a shareable map.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
BINDINGS_PATH = Path.home() / ".config" / "dotmaps" / "servers.json"


class MCPError(Exception):
    """Transport, auth, or JSON-RPC failure talking to an MCP server."""


def load_bindings(path: Path | None = None) -> dict[str, dict[str, str]]:
    """Read the user-local server registry. Shape:
    {"cloudflare": {"url": "https://mcp.cloudflare.com/mcp?codemode=false",
                    "token_env": "CLOUDFLARE_API_TOKEN"}}
    Missing file -> empty registry (servers stay un-wired, as today)."""
    p = path or BINDINGS_PATH
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError as e:
        raise MCPError(f"malformed bindings file {p}: {e}") from e


def _parse_sse(body: str) -> dict[str, Any]:
    """Extract the last JSON-RPC message from an SSE-framed response."""
    last = None
    for line in body.splitlines():
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            if payload:
                last = payload
    if last is None:
        raise MCPError("SSE response contained no data frames")
    return json.loads(last)


class MCPHttpClient:
    """One connected MCP server over streamable HTTP."""

    def __init__(self, name: str, url: str, token_env: str | None = None,
                 token_file: str | None = None, timeout: int = 120):
        self.name = name
        self.url = url
        self.timeout = timeout
        self._session_id: str | None = None
        self._id = 0
        # token sources, in order: env var, then a chmod-600 file. The file
        # path avoids the shell-profile copy chain entirely (clipboard -> file)
        # — a token that never passes through echo/sed/quoting can't be
        # mangled by them.
        self._token = os.getenv(token_env) if token_env else None
        if not self._token and token_file:
            p = Path(token_file).expanduser()
            if p.exists():
                self._token = p.read_text().strip() or None
        self._token_env = token_env
        self._token_file = token_file
        self._tools: dict[str, dict[str, Any]] | None = None

    # -- transport --------------------------------------------------------- #
    def _post(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                sid = r.headers.get("Mcp-Session-Id")
                if sid:
                    self._session_id = sid
                if r.status == 202:  # notification accepted, no body
                    return None
                body = r.read().decode()
                ctype = r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                sources = [s for s in
                           (f"${self._token_env}" if self._token_env else None,
                            self._token_file) if s]
                hint = (f"check token in {' or '.join(sources)}" if sources
                        else "no token configured for this server")
                raise MCPError(
                    f"MCP server {self.name!r} refused auth ({e.code}) — {hint}"
                ) from e
            raise MCPError(
                f"MCP server {self.name!r} HTTP {e.code}: "
                f"{e.read().decode()[:200]}") from e
        except urllib.error.URLError as e:
            raise MCPError(f"cannot reach MCP server {self.name!r} at "
                           f"{self.url}: {e.reason}") from e
        if not body.strip():
            return None
        msg = (_parse_sse(body) if "text/event-stream" in ctype
               else json.loads(body))
        if "error" in msg:
            err = msg["error"]
            raise MCPError(f"MCP server {self.name!r} error "
                           f"{err.get('code')}: {err.get('message')}")
        return msg

    def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self._id += 1
        msg = self._post({"jsonrpc": "2.0", "id": self._id, "method": method,
                          "params": params or {}})
        return (msg or {}).get("result")

    def _notify(self, method: str) -> None:
        self._post({"jsonrpc": "2.0", "method": method})

    # -- lifecycle --------------------------------------------------------- #
    def connect(self) -> None:
        self._call("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "dotmaps", "version": "0.1"},
        })
        self._notify("notifications/initialized")

    def list_tools(self) -> dict[str, dict[str, Any]]:
        """name -> {description, inputSchema}, paginated per spec."""
        if self._tools is not None:
            return self._tools
        tools: dict[str, dict[str, Any]] = {}
        cursor = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            result = self._call("tools/list", params) or {}
            for t in result.get("tools", []):
                tools[t["name"]] = {
                    "description": t.get("description", ""),
                    "inputSchema": t.get("inputSchema", {"type": "object"}),
                }
            cursor = result.get("nextCursor")
            if not cursor:
                break
        self._tools = tools
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        result = self._call("tools/call",
                            {"name": name, "arguments": arguments}) or {}
        parts = []
        for c in result.get("content", []):
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
            else:
                parts.append(json.dumps(c))
        out = "\n".join(parts) if parts else json.dumps(result)
        if result.get("isError"):
            return f"ERROR from {self.name}.{name}: {out[:500]}"
        return out

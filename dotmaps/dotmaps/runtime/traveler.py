"""The agent client — the deliberately-replaceable component (spec §8).

Two drivers behind one interface:

  scripted -- deterministic. Reads `traveler.script` from map.yaml: dot_id ->
              list of tool actions. Used to prove the loop, resume, regression
              detection, and walls WITHOUT needing a model or API keys. This is
              a test driver, not the product's traveler.
  llm      -- the real cheap traveler: an Anthropic Messages loop with only the
              map's whitelisted tools registered. Optional; needs ANTHROPIC_API_KEY.

Rule 3 (walls) is enforced HERE by construction: ToolBox registers only the
servers listed in map.mcp_required. An action naming an unregistered server
raises WallViolation — the tool does not exist in the action space, it is not
merely discouraged.

Rule 5 (scoped filesystem): the built-in filesystem tools refuse any path
outside the workspace and refuse to touch the .dotmaps board. OS-level
read-only enforcement (the strong form) is provided by the docker `:ro` mounts
the verifier and a containerized traveler run under — see verifier/runner.py and
tests/test_mount_enforcement.py.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable

from ..models import Map
from ..scoreboard.state import Scoreboard
from . import prompt as prompt_mod


class WallViolation(Exception):
    """Raised when the traveler reaches for a tool outside the whitelist (rule 3)."""


class ScopeViolation(Exception):
    """Raised when a filesystem action escapes the workspace (rule 5)."""


# Real parameter schemas for the built-in tools. Both model drivers share these;
# explicit schemas matter most for small open models, which guess badly against
# permissive ones.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "fetch.get": {
        "description": "HTTP GET a URL and return status + body (first 64KB). "
                       "Read-only — there is no POST.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "http(s) URL to fetch"},
            },
            "required": ["url"],
        },
    },
    "filesystem.write_file": {
        "description": "Create or overwrite a file in the workspace. Parent "
                       "directories are created automatically — never mkdir first.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "path relative to the workspace root"},
                "content": {"type": "string", "description": "full file content to write"},
            },
            "required": ["path", "content"],
        },
    },
    "filesystem.read_file": {
        "description": "Read a file from the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "path relative to the workspace root"},
            },
            "required": ["path"],
        },
    },
    "filesystem.mkdir": {
        "description": "Create a directory (and parents) in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "path relative to the workspace root"},
            },
            "required": ["path"],
        },
    },
    "filesystem.delete": {
        "description": "Delete a file or directory in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "path relative to the workspace root"},
            },
            "required": ["path"],
        },
    },
}


# --------------------------------------------------------------------------- #
# ToolBox: the whitelisted action space                                        #
# --------------------------------------------------------------------------- #
class ToolBox:
    """Registers ONLY the tools declared in the map (rule 3).

    `mcp_required` entries come in two grains:
      - "filesystem"            -> the whole server (every tool it has)
      - "filesystem.write_file" -> that single tool only

    Tool-level grants exist because of a live Stage-0 finding: a migration
    traveler with `filesystem.delete` in reach entered move-mode (migrate =
    move = delete the source), was correctly blocked by the protected-paths
    wall, and DISPLACED to deleting its own deliverable instead. The map never
    needed delete at all. Rule 3's philosophy applies at every grain: illegal
    actions are absent, not discouraged — so a map declares the narrowest
    action space that can complete it.

    Three kinds of server, resolved in this order:
      - built-in `filesystem` — scoped to the workspace, implemented here
      - built-in `fetch` — GET-only, size-capped HTTP reads (a traveler
        checking its own deploy needs nothing more; POST stays absent)
      - anything else — a REAL MCP server over streamable HTTP, if (and only
        if) the user has bound it in ~/.config/dotmaps/servers.json. The map
        declares requirements; the binding (URL + token env var) is user-local
        and never part of a shareable map. An un-bound-but-declared server
        exposes no callable tools with a clear error; an UN-declared server
        raises WallViolation.

    Whitelisting is enforced BEFORE any remote call at both grains, and only
    whitelisted remote tool schemas are ever forwarded to the model — a map
    that grants 4 endpoint tools from a 2,500-tool server costs the traveler
    4 schemas of context, not 2,500.
    """

    def __init__(self, m: Map, workspace: Path):
        self.workspace = workspace.resolve()
        self.allowed_servers = {e for e in m.mcp_required if "." not in e}
        self.allowed_tools = {e for e in m.mcp_required if "." in e}
        self._tools: dict[str, Callable[..., Any]] = {}
        self._remote_specs: dict[str, dict[str, Any]] = {}  # tool -> inputSchema etc.
        self._remote_errors: dict[str, str] = {}  # server -> why it's absent
        self._protected = self._load_protected_paths()
        self._register_filesystem()
        self._register_fetch()
        self._register_remote_servers()

    def _load_protected_paths(self) -> set[str]:
        """Traveler-read-only files, declared at compile time (attack finding B1:
        a migration traveler must never write the SOURCE it is judged against).
        The list lives in .dotmaps/ — itself unwritable — so the traveler cannot
        unprotect anything. Prevention here; the verifier's hash pin remains as
        detection defense-in-depth."""
        import json
        path = self.workspace / ".dotmaps" / "protected_paths.json"
        if path.exists():
            try:
                return {str(p) for p in json.loads(path.read_text())}
            except (json.JSONDecodeError, TypeError):
                pass
        return set()

    def _register_filesystem(self) -> None:
        impls = {
            "filesystem.write_file": self._write_file,
            "filesystem.read_file": self._read_file,
            "filesystem.mkdir": self._mkdir,
            "filesystem.delete": self._delete,
        }
        for name, fn in impls.items():
            if "filesystem" in self.allowed_servers or name in self.allowed_tools:
                self._tools[name] = fn

    def _register_fetch(self) -> None:
        if "fetch" in self.allowed_servers or "fetch.get" in self.allowed_tools:
            self._tools["fetch.get"] = self._fetch_get

    def _granted(self, server: str, tool: str) -> bool:
        return server in self.allowed_servers or tool in self.allowed_tools

    def _register_remote_servers(self) -> None:
        """Connect declared non-builtin servers that have user bindings, and
        register ONLY the whitelisted tools. Connection failures don't crash
        the run — the tools are simply absent and the traveler is told why
        if it reaches for one."""
        from dotmaps.runtime.mcp_client import MCPError, MCPHttpClient, load_bindings

        declared = ({s for s in self.allowed_servers} |
                    {t.split(".", 1)[0] for t in self.allowed_tools})
        remote = declared - {"filesystem", "fetch"}
        if not remote:
            return
        bindings = load_bindings()
        for server in sorted(remote):
            b = bindings.get(server)
            if not b or not b.get("url"):
                self._remote_errors[server] = (
                    f"server {server!r} is declared by the map but not bound — "
                    f"add it to ~/.config/dotmaps/servers.json")
                continue
            try:
                client = MCPHttpClient(server, b["url"],
                                       token_env=b.get("token_env"),
                                       token_file=b.get("token_file"))
                client.connect()
                for tname, spec in client.list_tools().items():
                    qualified = f"{server}.{tname}"
                    if not self._granted(server, qualified):
                        continue  # never forwarded, never callable
                    self._remote_specs[qualified] = spec
                    self._tools[qualified] = (
                        lambda _c=client, _t=tname, **kw: _c.call_tool(_t, kw))
            except MCPError as e:
                self._remote_errors[server] = str(e)

    def call(self, tool: str, **kwargs: Any) -> Any:
        server = tool.split(".", 1)[0]
        if server not in self.allowed_servers and tool not in self.allowed_tools:
            raise WallViolation(
                f"tool {tool!r} is not whitelisted for this map "
                f"(allowed: {sorted(self.allowed_servers | self.allowed_tools)})"
            )
        if tool not in self._tools:
            why = self._remote_errors.get(server)
            if why:
                raise WallViolation(f"tool {tool!r} is unavailable: {why}")
            raise WallViolation(f"tool {tool!r} is not available in this harness build")
        return self._tools[tool](**kwargs)

    # -- scoped filesystem primitives -------------------------------------- #
    def _resolve(self, rel: str, mutating: bool = False) -> Path:
        p = (self.workspace / rel).resolve()
        if self.workspace not in p.parents and p != self.workspace:
            # corrective, not just prohibitive: a weak model that garbles an
            # absolute path repeats the same blocked call until the budget
            # dies unless the error tells it the fix, in-band.
            raise ScopeViolation(
                f"path {rel!r} escapes the workspace — use a path relative to "
                f"the workspace root, e.g. 'source_items.json'")
        if ".dotmaps" in p.parts:
            raise ScopeViolation("the scoreboard (.dotmaps) is read-only to the traveler")
        if mutating:
            relpath = str(p.relative_to(self.workspace))
            if relpath in self._protected:
                raise ScopeViolation(
                    f"{relpath!r} is protected (declared read-only at compile "
                    f"time) — it is an input to verification, not a work product"
                )
        return p

    def _write_file(self, path: str, content: str = "") -> str:
        p = self._resolve(path, mutating=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"wrote {len(content)} bytes to {path}"

    def _read_file(self, path: str) -> str:
        return self._resolve(path).read_text()

    def _mkdir(self, path: str) -> str:
        self._resolve(path, mutating=True).mkdir(parents=True, exist_ok=True)
        return f"created dir {path}"

    def _delete(self, path: str) -> str:
        p = self._resolve(path, mutating=True)
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
        return f"deleted {path}"

    # -- built-in fetch (GET only, size-capped) ----------------------------- #
    def _fetch_get(self, url: str) -> str:
        """Read-only HTTP: enough for a traveler to check a page or an API
        response. No POST/PUT/DELETE — mutation via fetch stays absent, not
        discouraged (rule 3). 64KB cap keeps a huge page from flooding the
        weak traveler's context."""
        import urllib.error
        import urllib.request
        if not url.startswith(("http://", "https://")):
            raise ScopeViolation(f"fetch.get only accepts http(s) URLs, got {url!r}")
        req = urllib.request.Request(url, headers={"User-Agent": "dotmaps-traveler/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read(65536).decode("utf-8", errors="replace")
                return f"HTTP {r.status}\n{body}"
        except urllib.error.HTTPError as e:
            return f"HTTP {e.code}\n{e.read(2048).decode('utf-8', errors='replace')}"
        except urllib.error.URLError as e:
            return f"ERROR: could not reach {url}: {e.reason}"


# --------------------------------------------------------------------------- #
# Traveler                                                                      #
# --------------------------------------------------------------------------- #
class Traveler:
    @staticmethod
    def attempt(dot_id: str, m: Map, workspace: str | Path, board: Scoreboard,
                dry_run: bool = False) -> dict[str, Any]:
        ws = Path(workspace).resolve()
        tools: Any = ToolBox(m, ws)
        if dry_run:
            # mocking lives at the ToolBox seam (safety/dryrun.py); the driver
            # code below cannot tell the difference — by design.
            from ..safety.dryrun import wrap_toolbox_for_dryrun
            tools = wrap_toolbox_for_dryrun(tools)
        dot = m.dot(dot_id)
        driver = m.traveler.driver
        if driver == "scripted":
            result = _scripted_attempt(dot_id, m, ws, tools)
        elif driver == "llm":
            result = _llm_attempt(dot, m, ws, tools, board)
        elif driver == "ollama":
            result = _ollama_attempt(dot, m, ws, tools, board)
        else:
            raise ValueError(f"unknown traveler driver {driver!r}")
        if dry_run:
            result["dry_run"] = True
            result["journal"] = tools.journal
        return result


def _scripted_attempt(dot_id: str, m: Map, ws: Path, tools: ToolBox) -> dict[str, Any]:
    actions = m.traveler.script.get(dot_id, [])
    performed: list[str] = []
    for action in actions:
        tool = action["tool"]
        args = {k: v for k, v in action.items() if k != "tool"}
        performed.append(str(tools.call(tool, **args)))
    return {"driver": "scripted", "actions": performed, "usd": 0.0}


def _llm_attempt(dot, m: Map, ws: Path, tools: ToolBox, board: Scoreboard) -> dict[str, Any]:
    """Real cheap-model traversal via the Anthropic Messages API.

    Kept intentionally small: register the whitelisted tools, hand the model the
    minimal per-dot prompt, run a short tool-use loop, return cost. The verifier
    — not this function — decides whether the dot was eaten.
    """
    try:
        import anthropic  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "llm driver needs the 'anthropic' package (pip install anthropic)"
        ) from e
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("llm driver needs ANTHROPIC_API_KEY in the environment")

    client = anthropic.Anthropic()
    model = m.traveler.model or "claude-haiku-4-5-20251001"
    tool_specs = _anthropic_tool_specs(tools)
    messages = [{"role": "user", "content": prompt_mod.build(dot, m, ws, board)}]
    usd = 0.0
    for _ in range(8):  # bounded tool-use turns per attempt
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=m.traveler.temperature,
            system=prompt_mod.system_prompt(),
            tools=tool_specs,
            messages=messages,
        )
        usd += _estimate_cost(model, resp.usage)
        messages.append({"role": "assistant", "content": resp.content})
        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if not tool_uses:
            break
        tool_results = []
        for tu in tool_uses:
            try:
                out = tools.call(tu.name.replace("__", "."), **tu.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": tu.id, "content": str(out)}
                )
            except (WallViolation, ScopeViolation) as e:
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": tu.id,
                     "content": f"BLOCKED: {e}", "is_error": True}
                )
            except Exception as e:  # any tool failure: report back, never crash the run
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": tu.id,
                     "content": f"ERROR: {e}", "is_error": True}
                )
        messages.append({"role": "user", "content": tool_results})
    return {"driver": "llm", "model": model, "usd": usd}


def _ollama_attempt(dot, m: Map, ws: Path, tools, board: Scoreboard) -> dict[str, Any]:
    """The local open-model traveler — no credentials, runs against an Ollama
    server via its native /api/chat tool-calling API (stdlib urllib only).

    This is THE cheap traveler the product bets on (spec §4.2: "dense dots make
    the cheap model sufficient"). Same shape as the Anthropic loop: whitelisted
    tools only, minimal per-dot prompt, bounded turns, and the verifier — never
    this function — decides whether the dot was eaten. Cost is 0.0 by
    construction; the binding budget for local runs is max_cycles.
    """
    import json as _json
    import urllib.error
    import urllib.request

    base = (os.getenv("OLLAMA_HOST") or m.traveler.base_url or
            "http://localhost:11434").rstrip("/")
    if base and "://" not in base:
        base = "http://" + base
    model = m.traveler.model or "qwen2.5-coder:7b"

    def _chat(messages: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "tools": _ollama_tool_specs(tools),
            "stream": False,
            "options": {"temperature": m.traveler.temperature},
        }
        req = urllib.request.Request(
            base + "/api/chat",
            data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return _json.loads(r.read())
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"ollama driver could not reach {base} — is `ollama serve` running?"
            ) from e

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": prompt_mod.system_prompt()},
        {"role": "user", "content": prompt_mod.build(dot, m, ws, board)},
    ]
    turns = 0
    actions: list[str] = []  # attempt-level observability: tool calls + outcomes
    for _ in range(8):  # bounded tool-use turns per attempt
        resp = _chat(messages)
        msg = resp.get("message", {})
        messages.append(msg)
        turns += 1
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            # Weak-traveler fallback: many small open models emit the tool call
            # as JSON *text* instead of a structured tool_calls block. Meeting
            # them halfway is the product bet; the walls still judge every
            # parsed call identically.
            parsed = _parse_textual_tool_call(msg.get("content", ""))
            if parsed is None:
                actions.append(f"text: {str(msg.get('content', ''))[:120]}")
                break
            tool_calls = [parsed]
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = str(fn.get("name", "")).replace("__", ".")
            args = fn.get("arguments") or {}
            if isinstance(args, str):  # some models return arguments as a JSON string
                try:
                    args = _json.loads(args)
                except _json.JSONDecodeError:
                    args = {}
            try:
                out = str(tools.call(name, **args))
            except (WallViolation, ScopeViolation) as e:
                out = f"BLOCKED: {e}"
            except Exception as e:  # bad args, IsADirectoryError, any tool failure:
                # the traveler's mess is the traveler's problem — report it back
                # so it can correct course; never let it kill the run.
                out = f"ERROR: {name} failed: {e}"
            actions.append(f"{name}({str(args)[:80]}) -> {out[:80]}")
            messages.append({"role": "tool", "content": out, "tool_name": fn.get("name", "")})
    return {"driver": "ollama", "model": model, "usd": 0.0, "turns": turns,
            "actions": actions}


def _parse_textual_tool_call(content: str) -> dict[str, Any] | None:
    """Parse a tool call a small model wrote as plain JSON text (optionally
    inside a ```json fence). Returns an ollama-shaped tool_call dict or None.

    Accepted shapes: {"name": ..., "arguments": {...}} and the common synonyms
    {"tool": ...}/{"function": ...} with {"parameters"/"args"/"input": {...}}.
    """
    import json as _json
    import re as _re

    text = content.strip()
    fence = _re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, _re.S)
    if fence:
        text = fence.group(1)
    if not (text.startswith("{") and text.endswith("}")):
        return None
    try:
        obj = _json.loads(text)
    except _json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    name = obj.get("name") or obj.get("tool") or obj.get("function")
    args = obj.get("arguments") or obj.get("parameters") or obj.get("args") or obj.get("input")
    if not isinstance(name, str) or not isinstance(args, dict):
        return None
    return {"function": {"name": name, "arguments": args}}


def _spec_for(tools, name: str) -> tuple[str, dict[str, Any]]:
    """(description, parameters-schema) for a tool: remote servers supply real
    schemas via tools/list; builtins come from TOOL_SCHEMAS. Only whitelisted
    tools ever reach here, so a 2,500-tool server costs the model only the
    schemas the map granted."""
    box = tools if hasattr(tools, "_remote_specs") else tools._inner
    remote = box._remote_specs.get(name)
    if remote:
        return (remote.get("description", name),
                remote.get("inputSchema", {"type": "object"}))
    schema = TOOL_SCHEMAS.get(name, {})
    return (schema.get("description", f"{name} (scoped to the workspace)"),
            schema.get("parameters", {"type": "object", "additionalProperties": True}))


def _ollama_tool_specs(tools) -> list[dict[str, Any]]:
    """Whitelisted tools in OpenAI/Ollama function format; __ instead of dots."""
    specs = []
    for name in tools._tools if hasattr(tools, "_tools") else tools._inner._tools:
        desc, params = _spec_for(tools, name)
        specs.append({
            "type": "function",
            "function": {
                "name": name.replace(".", "__"),
                "description": desc,
                "parameters": params,
            },
        })
    return specs


def _anthropic_tool_specs(tools: ToolBox) -> list[dict[str, Any]]:
    # names use __ since the API disallows dots in tool names.
    specs = []
    for name in tools._tools:
        desc, params = _spec_for(tools, name)
        specs.append({
            "name": name.replace(".", "__"),
            "description": desc,
            "input_schema": params,
        })
    return specs


def _estimate_cost(model: str, usage: Any) -> float:
    # coarse per-Mtoken rates; refined pricing is a §6 open question.
    rate_in, rate_out = (1.0, 5.0)  # $/Mtok, haiku-ish default
    return (getattr(usage, "input_tokens", 0) * rate_in
            + getattr(usage, "output_tokens", 0) * rate_out) / 1_000_000

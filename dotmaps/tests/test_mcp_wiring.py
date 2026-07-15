"""Real MCP wiring: streamable-HTTP client + ToolBox integration.

A fake in-process MCP server (stdlib http.server) speaks enough JSON-RPC to
exercise the full lifecycle: initialize -> initialized -> tools/list (with
pagination) -> tools/call. No network, no external deps.
"""
import dataclasses
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from dotmaps.models import Map
from dotmaps.runtime.mcp_client import MCPError, MCPHttpClient, load_bindings
from dotmaps.runtime.traveler import ToolBox, WallViolation, _ollama_tool_specs

SMOKE_MAP = str(Path(__file__).parent.parent.parent / "maps" / "map-smoke")


class FakeMCP(BaseHTTPRequestHandler):
    """Two tools: cf.deploy_worker (page 1) and cf.list_workers (page 2)."""
    calls: list = []  # class-level journal

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeMCP.calls.append((body.get("method"), self.headers.get("Authorization")))
        if "id" not in body:  # notification
            self.send_response(202); self.end_headers(); return
        method = body["method"]
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {},
                      "serverInfo": {"name": "fake-cf", "version": "0"}}
        elif method == "tools/list":
            if body.get("params", {}).get("cursor"):
                result = {"tools": [{"name": "list_workers",
                                     "description": "List workers",
                                     "inputSchema": {"type": "object", "properties": {}}}]}
            else:
                result = {"tools": [{"name": "deploy_worker",
                                     "description": "Deploy a worker script",
                                     "inputSchema": {"type": "object",
                                                     "properties": {"name": {"type": "string"}},
                                                     "required": ["name"]}}],
                          "nextCursor": "page2"}
        elif method == "tools/call":
            name = body["params"]["name"]
            result = {"content": [{"type": "text",
                                   "text": f"ok:{name}:{json.dumps(body['params']['arguments'])}"}]}
        else:
            result = {}
        resp = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Mcp-Session-Id", "sess-1")
        self.end_headers()
        self.wfile.write(resp.encode())

    def log_message(self, *a):  # silence
        pass


@pytest.fixture()
def fake_server():
    FakeMCP.calls = []
    srv = HTTPServer(("127.0.0.1", 0), FakeMCP)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}/mcp"
    srv.shutdown()


def test_client_lifecycle_and_pagination(fake_server, monkeypatch):
    monkeypatch.setenv("FAKE_CF_TOKEN", "tok-123")
    c = MCPHttpClient("cf", fake_server, token_env="FAKE_CF_TOKEN")
    c.connect()
    tools = c.list_tools()
    assert set(tools) == {"deploy_worker", "list_workers"}  # both pages
    out = c.call_tool("deploy_worker", {"name": "site"})
    assert out == 'ok:deploy_worker:{"name": "site"}'
    # bearer token was sent, and never appears in any client attribute repr
    assert any(a == "Bearer tok-123" for _, a in FakeMCP.calls)
    methods = [m for m, _ in FakeMCP.calls]
    assert methods[:2] == ["initialize", "notifications/initialized"]


def test_toolbox_registers_only_whitelisted_remote_tools(fake_server, tmp_path,
                                                         monkeypatch):
    bindings = tmp_path / "servers.json"
    bindings.write_text(json.dumps({"cf": {"url": fake_server}}))
    monkeypatch.setattr("dotmaps.runtime.mcp_client.BINDINGS_PATH", bindings)

    m = Map.load(SMOKE_MAP)
    # tool-grain grant: deploy only; list_workers must be ABSENT
    m = dataclasses.replace(m, mcp_required=("filesystem", "cf.deploy_worker"))
    ws = tmp_path / "ws"; ws.mkdir()
    tb = ToolBox(m, ws)
    assert "cf.deploy_worker" in tb._tools
    assert "cf.list_workers" not in tb._tools
    out = tb.call("cf.deploy_worker", name="site")
    assert out.startswith("ok:deploy_worker")
    with pytest.raises(WallViolation):
        tb.call("cf.list_workers")
    # the model sees the REAL schema from tools/list, only for granted tools
    specs = {s["function"]["name"]: s["function"] for s in _ollama_tool_specs(tb)}
    assert "cf__deploy_worker" in specs
    assert "cf__list_workers" not in specs
    assert specs["cf__deploy_worker"]["parameters"]["required"] == ["name"]


def test_unbound_server_is_absent_with_reason(tmp_path, monkeypatch):
    monkeypatch.setattr("dotmaps.runtime.mcp_client.BINDINGS_PATH",
                        tmp_path / "nonexistent.json")
    m = Map.load(SMOKE_MAP)
    m = dataclasses.replace(m, mcp_required=("filesystem", "cloudflare"))
    ws = tmp_path / "ws"; ws.mkdir()
    tb = ToolBox(m, ws)
    with pytest.raises(WallViolation, match="not bound"):
        tb.call("cloudflare.anything")


def test_missing_bindings_file_is_empty_registry(tmp_path):
    assert load_bindings(tmp_path / "nope.json") == {}


class AuthFakeMCP(FakeMCP):
    """Accepts only Bearer good-token; 403 otherwise (like the real thing)."""

    def do_POST(self):
        if self.headers.get("Authorization") != "Bearer good-token":
            self.send_response(403); self.end_headers()
            self.wfile.write(b"forbidden")
            return
        super().do_POST()


@pytest.fixture()
def auth_server():
    srv = HTTPServer(("127.0.0.1", 0), AuthFakeMCP)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/mcp"
    srv.shutdown()


def _connect_env(tmp_path, monkeypatch):
    bindings = tmp_path / "servers.json"
    monkeypatch.setattr("dotmaps.runtime.mcp_client.BINDINGS_PATH", bindings)
    monkeypatch.setattr("dotmaps.connect.BINDINGS_PATH", bindings)
    return bindings


def test_connect_bad_then_good_token(auth_server, tmp_path, monkeypatch):
    from dotmaps.connect import connect_map
    bindings = _connect_env(tmp_path, monkeypatch)
    m = Map.load(SMOKE_MAP)
    m = dataclasses.replace(m, mcp_required=("filesystem", "cf.deploy_worker"),
                            mcp_setup={"cf": {"url": auth_server}})
    said, tokens = [], iter(["WRONG", "good-token"])
    rc = connect_map(m, say=said.append, ask=lambda p: "",
                     secret=lambda p: next(tokens))
    assert rc == 0
    assert any("VERIFIED" in s for s in said)
    assert any("rejected" in s for s in said)  # the bad paste got instant feedback
    tf = tmp_path / "cf.token"
    assert tf.read_text().strip() == "good-token"
    assert (tf.stat().st_mode & 0o777) == 0o600
    saved = json.loads(bindings.read_text())
    assert saved["cf"]["token_file"] == str(tf)


def test_connect_gives_up_and_removes_bad_secret(auth_server, tmp_path, monkeypatch):
    from dotmaps.connect import connect_map
    _connect_env(tmp_path, monkeypatch)
    m = Map.load(SMOKE_MAP)
    m = dataclasses.replace(m, mcp_required=("cf",),
                            mcp_setup={"cf": {"url": auth_server}})
    rc = connect_map(m, say=lambda s: None, ask=lambda p: "",
                     secret=lambda p: "NOPE", max_attempts=2)
    assert rc == 1
    assert not (tmp_path / "cf.token").exists()  # bad secrets never linger


def test_connect_no_remote_servers_is_noop(tmp_path, monkeypatch):
    from dotmaps.connect import connect_map
    _connect_env(tmp_path, monkeypatch)
    m = Map.load(SMOKE_MAP)
    m = dataclasses.replace(m, mcp_required=("filesystem", "fetch"))
    said = []
    assert connect_map(m, say=said.append) == 0
    assert "nothing to connect" in said[0]

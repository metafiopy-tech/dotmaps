"""`dotmaps connect <map>` — the credential loop, owned by the harness.

The design lesson this encodes (learned live, painfully): the human's job is
to OBTAIN a token; everything after that — where it goes, how it's stored,
whether it actually works — is the harness's job, with instant feedback.
Copy-chain failure modes (shell quoting, profile files, clipboard races) are
eliminated by construction:

  - the token is pasted into a getpass prompt: never echoed, never in shell
    history, never in the clipboard-to-file pipeline
  - it is written to ~/.config/dotmaps/<server>.token, chmod 600
  - it is VERIFIED immediately by a real MCP handshake (initialize +
    tools/list); a bad paste fails in seconds with a clear message and the
    prompt loops — the user is never left holding a silently-broken config

A map may carry per-server setup hints in map.yaml:

    mcp_setup:
      cloudflare:
        url: https://mcp.cloudflare.com/mcp?codemode=false
        docs: https://dash.cloudflare.com/profile/api-tokens
        hint: "Custom token: Workers Scripts (Edit), Cloudflare Pages (Edit),
               Account Settings (Read). No IP filtering."

Well-known servers ship built-in defaults so most maps need no mcp_setup at
all. Unknown servers prompt for their URL.
"""
from __future__ import annotations

import getpass
import json
import os
import stat
from pathlib import Path

from .models import Map
from .runtime.mcp_client import BINDINGS_PATH, MCPError, MCPHttpClient

# Built-in registry of well-known MCP servers: name -> (url, docs, hint).
WELL_KNOWN: dict[str, dict[str, str]] = {
    "cloudflare": {
        "url": "https://mcp.cloudflare.com/mcp?codemode=false",
        "docs": "https://dash.cloudflare.com/profile/api-tokens",
        "hint": ("Create a Custom Token with: Workers Scripts (Edit), "
                 "Cloudflare Pages (Edit), Account Settings (Read). "
                 "Leave IP filtering empty."),
    },
}


def _token_path(server: str) -> Path:
    return BINDINGS_PATH.parent / f"{server}.token"


def _write_secret(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.strip() + "\n")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600


def _save_binding(server: str, url: str) -> None:
    bindings = {}
    if BINDINGS_PATH.exists():
        try:
            bindings = json.loads(BINDINGS_PATH.read_text())
        except json.JSONDecodeError:
            bindings = {}
    bindings[server] = {"url": url, "token_env": None,
                        "token_file": str(_token_path(server))}
    BINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BINDINGS_PATH.write_text(json.dumps(bindings, indent=2) + "\n")


def _verify(server: str, url: str) -> tuple[bool, str]:
    """Real handshake. Returns (ok, message)."""
    client = MCPHttpClient(server, url, token_file=str(_token_path(server)))
    try:
        client.connect()
        tools = client.list_tools()
        return True, f"connected — {len(tools)} tools available"
    except MCPError as e:
        return False, str(e)


def connect_map(m: Map, say=print, ask=input, secret=getpass.getpass,
                max_attempts: int = 3) -> int:
    """Walk every remote server the map requires; prompt + verify each.
    Returns 0 if all required servers verified, 1 otherwise."""
    declared = ({e for e in m.mcp_required if "." not in e} |
                {e.split(".", 1)[0] for e in m.mcp_required if "." in e})
    remote = sorted(declared - {"filesystem", "fetch"})
    if not remote:
        say("this map needs no external services — nothing to connect")
        return 0

    setup_cfg = getattr(m, "mcp_setup", None) or {}
    all_ok = True
    for server in remote:
        cfg = {**WELL_KNOWN.get(server, {}), **setup_cfg.get(server, {})}
        url = cfg.get("url")
        if not url:
            url = ask(f"[{server}] MCP server URL: ").strip()
            if not url:
                say(f"[{server}] skipped (no URL)")
                all_ok = False
                continue

        # already working? don't ask for anything.
        ok, msg = _verify(server, url)
        if ok:
            _save_binding(server, url)
            say(f"[{server}] already connected — {msg}")
            continue

        say(f"\n[{server}] needs a token.")
        if cfg.get("docs"):
            say(f"  get one at: {cfg['docs']}")
        if cfg.get("hint"):
            say(f"  {cfg['hint']}")

        connected = False
        for attempt in range(1, max_attempts + 1):
            value = secret(f"[{server}] paste token (hidden, attempt "
                           f"{attempt}/{max_attempts}): ").strip()
            if not value:
                break
            _write_secret(_token_path(server), value)
            ok, msg = _verify(server, url)
            if ok:
                _save_binding(server, url)
                say(f"[{server}] VERIFIED — {msg}")
                connected = True
                break
            say(f"[{server}] rejected: {msg}")
            say(f"  (length pasted: {len(value)} chars — Cloudflare user "
                f"tokens are typically 40)") if server == "cloudflare" else None
        if not connected:
            _token_path(server).unlink(missing_ok=True)  # never keep a bad secret
            say(f"[{server}] NOT connected — the map's {server} tools will be "
                f"absent until `dotmaps connect` succeeds")
            all_ok = False
    return 0 if all_ok else 1

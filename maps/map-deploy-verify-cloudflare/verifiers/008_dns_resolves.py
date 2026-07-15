#!/usr/bin/env python3
"""Dot 008: if a custom domain is configured, DNS resolves to the deployment."""
import socket, sys; from urllib.parse import urlparse; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_target, emit, fetch
ws, t = load_target()
domain = t.get("custom_domain")
if not domain:
    emit("008", True, "no custom domain configured (dot vacuously satisfied)")
host = urlparse(domain if "//" in domain else "//" + domain).hostname or domain
try:
    ip = socket.gethostbyname(host)
except Exception as e:
    emit("008", False, f"DNS for {host} did not resolve: {e}")
status, _, _ = fetch((domain if "//" in domain else "https://" + domain).rstrip("/") + "/")
ok = status == 200
emit("008", ok, f"{host} -> {ip}, HTTPS root -> {status}")

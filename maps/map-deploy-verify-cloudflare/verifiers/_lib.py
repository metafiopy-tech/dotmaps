"""Shared helpers for map-1 verifiers. Stdlib only (runs in the pinned
python:3.11-slim container with no pip installs). Each verifier stays a
standalone script per the spec; this is imported by path, not packaged.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_target(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ws = Path(ap.parse_args(argv).workspace)
    # Attack hardening: prefer the authoritative copy in .dotmaps/ (written by
    # the intake compiler; read-only to the traveler). The workspace-root copy
    # is a human-visible convenience — and traveler-writable, so never trusted
    # when the authoritative one exists. Fallback keeps hand-seeded example
    # workspaces runnable.
    for tf in (ws / ".dotmaps" / "target.json", ws / "target.json"):
        if tf.exists():
            return ws, json.loads(tf.read_text())
    emit("000", False, "target.json missing in workspace", error=True)


def emit(dot, passed, evidence, error=False):
    print(json.dumps({"dot": dot, "pass": bool(passed), "evidence": evidence}))
    sys.exit(2 if error else (0 if passed else 1))


_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch(url, method="GET", data=None, headers=None, timeout=20):
    # many hosts (Lovable, Cloudflare) reject the default urllib UA; a normal
    # browser UA is what a real health check sends.
    hdrs = {"User-Agent": _UA, "Accept": "*/*"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, method=method, data=data, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})
    except Exception as e:  # DNS, TLS, connection refused
        return None, str(e).encode(), {}

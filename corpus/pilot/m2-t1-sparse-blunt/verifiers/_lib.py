"""Shared helpers for map-2 (content migration) verifiers. Stdlib only.

Contract: <workspace>/migration.json describes the move:

  {
    "source": "source_items.json",       # JSON array of item objects
    "target": "target_items.json",        # JSON array of item objects
    "slug_field": "slug",
    "required_fields": ["title", "price", "date"],
    "hash_fields": ["title", "price", "date"],
    "spot_hash_sample": 3,
    "links_field": "body",                # field whose text may contain internal hrefs
    "internal_link_base": null            # if set, resolve links over HTTP; else intra-target
  }

The traveler's job is to produce target_items.json from the source; these
verifiers only judge the result.
"""
import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def load(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ws = Path(ap.parse_args(argv).workspace)
    # Attack hardening: prefer the authoritative config in .dotmaps/ (intake-
    # written, read-only to the traveler) over the traveler-writable root copy.
    cfg = None
    for mf in (ws / ".dotmaps" / "migration.json", ws / "migration.json"):
        if mf.exists():
            cfg = json.loads(mf.read_text())
            break
    if cfg is None:
        emit("000", False, "migration.json missing in workspace", error=True)
    src_path = ws / cfg["source"]
    src = _read_items(src_path, "source")
    # Attack hardening: the traveler can write the SOURCE file too — it could
    # 'migrate perfectly' by rewriting the source to match its target. If the
    # intake compiler pinned the source hash, a mismatch is a hard error.
    pinned = cfg.get("source_sha256")
    if pinned:
        import hashlib
        actual = hashlib.sha256(src_path.read_bytes()).hexdigest()
        if actual != pinned:
            emit("000", False,
                 "source file hash does not match the hash pinned at compile "
                 "time — source was modified after approval", error=True)
    tgt = _read_items(ws / cfg["target"], "target")
    return ws, cfg, src, tgt


def _read_items(path, label):
    if not path.exists():
        emit("000", False, f"{label} file {path.name} missing", error=True)
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        emit("000", False, f"{label} must be a JSON array", error=True)
    return data


def emit(dot, passed, evidence, error=False):
    print(json.dumps({"dot": dot, "pass": bool(passed), "evidence": evidence}))
    sys.exit(2 if error else (0 if passed else 1))


def norm_hash(item, fields):
    parts = [f"{f}={str(item.get(f, '')).strip().lower()}" for f in fields]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def fetch_status(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None

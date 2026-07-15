"""Shared: load workspace from --workspace flag; emit protocol JSON."""
import json, sys
from pathlib import Path

def ws() -> Path:
    return Path(sys.argv[sys.argv.index("--workspace") + 1])

def emit(dot, ok, evidence, error=False):
    print(json.dumps({"dot": dot, "pass": bool(ok), "evidence": evidence}))
    sys.exit(2 if error else (0 if ok else 1))

def read_json(path, dot, label):
    if not path.exists():
        emit(dot, False, f"{label} missing")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        emit(dot, False, f"{label} is not valid JSON: {e}")

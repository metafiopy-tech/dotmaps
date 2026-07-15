"""The verifier contract (spec §4b), in one place.

  - invoked as: <script> --workspace /ws   (workspace is a READ-ONLY mount)
  - exit 0 = pass, exit 1 = fail, exit 2 = error (treated as fail, flagged)
  - stdout: single JSON line {"dot": id, "pass": bool, "evidence": "<sentence>"}
  - hard timeout 60s
  - no network except domains declared in map.yaml (enforced in docker mode)

This module only holds constants + the timeout; parsing lives on DotResult so
the schema and its parser stay together.
"""

TIMEOUT_SECONDS = 60
WORKSPACE_MOUNT = "/ws"  # where the workspace appears inside the container
WORKSPACE_FLAG = "--workspace"

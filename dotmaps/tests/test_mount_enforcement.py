"""Phase-1 gate: walls + read-only enforcement are STRUCTURAL, not polite.

Rule 3 (walls): the traveler's action space = only the map's declared servers.
An un-listed server does not exist; a scoped-filesystem escape is refused.

Rule 5 (read-only scoreboard/manifest): proven at the OS level via a docker
read-only bind mount — a write to a `:ro` mount fails with a filesystem error,
not a scolding. Skipped (not silently passed) when docker is unavailable.
"""
import shutil
import subprocess

import pytest
from conftest import SMOKE_MAP

from dotmaps.models import Map
from dotmaps.runtime.traveler import ScopeViolation, ToolBox, WallViolation


def _toolbox(tmp_path):
    m = Map.load(SMOKE_MAP)  # mcp_required: [filesystem]
    ws = tmp_path / "ws"
    ws.mkdir()
    return ToolBox(m, ws), ws


def _docker_responsive(timeout: int = 10) -> bool:
    """True only if the docker DAEMON answers quickly. `shutil.which` alone is
    not enough: a present CLI with a hung daemon (sleeping Docker Desktop)
    would turn this test into a 2-minute timeout-failure that reads like an
    enforcement regression. Daemon-down must read as SKIP, not FAIL."""
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info", "--format", "ok"],
                              capture_output=True, timeout=timeout).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def test_undeclared_server_is_absent_not_discouraged(tmp_path):
    tb, _ = _toolbox(tmp_path)
    # cloudflare is NOT whitelisted for the smoke map -> it does not exist
    with pytest.raises(WallViolation):
        tb.call("cloudflare.deploy", project="x")


def test_filesystem_escape_is_refused(tmp_path):
    tb, _ = _toolbox(tmp_path)
    with pytest.raises(ScopeViolation):
        tb.call("filesystem.write_file", path="../../escape.txt", content="x")


def test_scoreboard_is_read_only_to_traveler(tmp_path):
    tb, _ = _toolbox(tmp_path)
    with pytest.raises(ScopeViolation):
        tb.call("filesystem.write_file", path=".dotmaps/events.jsonl", content="tamper")


def test_in_scope_write_is_allowed(tmp_path):
    tb, ws = _toolbox(tmp_path)
    tb.call("filesystem.write_file", path="ok.txt", content="fine")
    assert (ws / "ok.txt").read_text() == "fine"


def test_docker_readonly_mount_rejects_writes(tmp_path):
    """The OS-level enforcement the containerized verifier/traveler runs under:
    a write to a `:ro` bind mount is a hard filesystem error."""
    if not _docker_responsive():
        pytest.skip("docker daemon not responsive")
    # prefer an image that is already local (a pruned cache + slow registry
    # must not fail an enforcement test); fall back to a bounded pull.
    image = None
    for candidate in ("alpine:3", "python:3.11-slim-bookworm", "dotmap-smoke:0.1.0"):
        if subprocess.run(["docker", "image", "inspect", candidate],
                          capture_output=True, timeout=15).returncode == 0:
            image = candidate
            break
    if image is None:
        try:
            pulled = subprocess.run(["docker", "pull", "alpine:3"],
                                    capture_output=True, timeout=90)
            if pulled.returncode == 0:
                image = "alpine:3"
        except subprocess.TimeoutExpired:
            pass
    if image is None:
        pytest.skip("no local docker image and pull did not complete in time")

    ro = tmp_path / "ro"
    ro.mkdir()
    (ro / "verifier.sh").write_text("echo hi\n")
    proc = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{ro}:/ro:ro",
         image, "sh", "-c", "echo tampered > /ro/verifier.sh"],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode != 0, "write to read-only mount should fail"
    # original content untouched on the host
    assert (ro / "verifier.sh").read_text() == "echo hi\n"


def test_tool_level_grants(tmp_path):
    """A map may whitelist single tools; ungranted siblings are ABSENT (rule 3
    at tool grain — the Stage-0 'move-mode delete' finding)."""
    import dataclasses

    m = Map.load(SMOKE_MAP)
    m = dataclasses.replace(m, mcp_required=("filesystem.read_file",
                                             "filesystem.write_file"))
    ws = tmp_path / "ws"
    ws.mkdir()
    tb = ToolBox(m, ws)
    tb.call("filesystem.write_file", path="a.txt", content="x")
    assert tb.call("filesystem.read_file", path="a.txt") == "x"
    with pytest.raises(WallViolation):
        tb.call("filesystem.delete", path="a.txt")
    assert (ws / "a.txt").exists()  # the delete was absent, not just refused late


def test_dryrun_respects_tool_level_grants(tmp_path):
    """Dry-run wall parity at tool grain: a granted mutating tool must be
    MOCKED (not executed), an ungranted one must still raise."""
    import dataclasses

    from dotmaps.safety.dryrun import wrap_toolbox_for_dryrun

    m = Map.load(SMOKE_MAP)
    m = dataclasses.replace(m, mcp_required=("filesystem.write_file",))
    ws = tmp_path / "ws"
    ws.mkdir()
    dry = wrap_toolbox_for_dryrun(ToolBox(m, ws))
    out = dry.call("filesystem.write_file", path="a.txt", content="x")
    assert "DRY-RUN" in out
    assert not (ws / "a.txt").exists()  # mocked, not written
    with pytest.raises(WallViolation):
        dry.call("filesystem.delete", path="a.txt")

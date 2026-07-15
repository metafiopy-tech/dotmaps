"""Phase-2 gate: secrets audit passes (spec §5: "grep the workspace/logs for
tokens after a real run = zero hits").

Proofs: planted credential shapes are caught (including inside .dotmaps/ logs,
where a leak would actually hide), findings are redacted, and a clean post-run
workspace audits clean.
"""
from conftest import SMOKE_MAP

from dotmaps.models import Map
from dotmaps.runtime.orchestrator import Orchestrator
from dotmaps.safety.audit import scan_workspace


def test_planted_tokens_are_caught(tmp_path):
    ws = tmp_path / "ws"
    (ws / ".dotmaps").mkdir(parents=True)
    # a leak in the traversal log — the worst place, and exactly where we scan
    (ws / ".dotmaps" / "events.jsonl").write_text(
        '{"event":"dot_attempted","note":"authorization: bearer abc123def456ghi789jkl012"}\n'
    )
    (ws / "config.py").write_text('API_KEY = "sk-ant-' + "a1b2c3d4e5" * 3 + '"\n')
    (ws / "creds.pem").write_text("-----BEGIN PRIVATE KEY-----\nMIIE...\n")

    findings = scan_workspace(ws)
    kinds = {f.kind for f in findings}
    assert "cloudflare_token_hdr" in kinds
    assert "anthropic_key" in kinds
    assert "google_sa_key" in kinds
    # scoreboard leak located precisely
    assert any(f.path == ".dotmaps/events.jsonl" for f in findings)


def test_findings_are_redacted(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    secret = "sk-ant-" + "x" * 30
    (ws / "leak.txt").write_text(secret)
    findings = scan_workspace(ws)
    assert findings
    for f in findings:
        assert secret not in f.excerpt  # the audit never re-prints the credential


def test_real_run_workspace_audits_clean(tmp_path):
    """The actual Phase-2 gate: after a full traversal, zero hits."""
    ws = tmp_path / "ws"
    m = Map.load(SMOKE_MAP)
    Orchestrator(m, ws, verbose=False).run()
    assert scan_workspace(ws) == []

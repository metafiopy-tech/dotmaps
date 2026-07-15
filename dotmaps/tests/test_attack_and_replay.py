"""dotmaps attack + replay: the packaging pair."""
import json
from pathlib import Path

from dotmaps.certificate.attack import run_attacks
from dotmaps.scoreboard.replay import replay

MAPS = Path(__file__).parent.parent.parent / "maps"


def test_attack_map2_is_hardened(tmp_path):
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "source_items.json").write_text(
        '[{"slug":"a","title":"T","price":"1","date":"2026-01-01","body":"x"}]')
    (seed / ".dotmaps").mkdir()
    (seed / ".dotmaps" / "protected_paths.json").write_text('["source_items.json"]')
    import shutil, json as _json
    # compile-equivalent config so verifiers can run
    cfg = {"source": "source_items.json", "target": "target_items.json",
           "slug_field": "slug", "required_fields": ["title", "price", "date"],
           "hash_fields": ["title", "price", "date"], "spot_hash_sample": 1,
           "links_field": "body", "internal_link_base": None}
    import hashlib
    cfg["source_sha256"] = hashlib.sha256((seed / "source_items.json").read_bytes()).hexdigest()
    (seed / ".dotmaps" / "migration.json").write_text(_json.dumps(cfg))
    (seed / "migration.json").write_text(_json.dumps(cfg))

    report = run_attacks(MAPS / "map-content-migration", seed)
    by_id = {a["id"]: a for a in report["attacks"]}
    assert by_id["A2"]["repelled"], by_id["A2"]["evidence"]
    assert by_id["A3"]["repelled"], by_id["A3"]["evidence"]
    assert by_id["A4"]["repelled"], by_id["A4"]["evidence"]
    # artifact written
    assert (MAPS / "map-content-migration" / "certification" /
            "attack_report.json").exists()


def test_attack_seq_map_fully_hardened():
    report = run_attacks(MAPS / "map-seq", MAPS / "map-seq" / "examples" / "seed-ws")
    assert report["verdict"] == "HARDENED", report


def test_replay_renders_story(tmp_path):
    ws = tmp_path / "ws"
    (ws / ".dotmaps").mkdir(parents=True)
    events = [
        {"ts": "2026-07-15T00:00:00", "event": "run_started", "map": "demo", "version": "1"},
        {"ts": "t", "event": "cycle_started", "cycle": 1},
        {"ts": "t", "event": "dot_attempted", "cycle": 1, "dot": "d1",
         "attempt": 1, "actions": ["filesystem.write_file(...) -> wrote 5 bytes"]},
        {"ts": "t", "event": "dot_eaten", "cycle": 2, "dot": "d1",
         "evidence": "state verified", "attempt": 1},
        {"ts": "t", "event": "run_ended", "cycle": 2, "reason": "all_green"},
    ]
    (ws / ".dotmaps" / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events))
    lines = []
    replay(ws, out=lines.append)
    text = "\n".join(lines)
    assert "run started · map demo" in text
    assert "attempt 1 on d1" in text
    assert "d1 EATEN" in text
    assert "all_green" in text

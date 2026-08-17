"""H5 (HARDENING_BRIEF): statistical honesty + mutation isolation in
certification. The audit's two P1 findings, fixed together in
bank/certify.py (one shared seed copy was the root cause of both):

  - certify_all() previously copied the seed ONCE and reused it across
    every skill and every probe; a mutating skill could leave state a
    later skill's certification then read (order-dependence).
  - 20 replays of byte-identical frozen steps against one shared copy are
    a point mass, not 20 independent samples — a Wilson interval there
    overclaims statistical confidence; certification now requires
    successes == n for this regime, labeled "deterministic-consistency".

Regression tests, verbatim from the audit: reorder skill files -> identical
certificates (mutation isolation); a skill with any failure among
deterministic replays is not certified even though the old Wilson floor
would have cleared it (statistical honesty).
"""
import json
import shutil
from pathlib import Path

import yaml

from dotmaps.bank.certify import certify_all

REPO = Path(__file__).resolve().parents[2]
SEED = REPO / "corpus" / "pilot" / "seed-ws"

_MUTATOR = {
    "name": "a-mutator", "statement": "a-mutator writes a marker file",
    "trigger": ["a-mutator::marker::x"],
    "method": {"steps": [{"tool": "filesystem.write_file",
                          "args": {"path": "mutation_marker.json", "content": '["mutated"]'}}],
              "hash": "deadbeef0000"},
    "check": {"predicate": "contains", "value": "wrote"},
    "requires": {"tools": ["filesystem.write_file"]},
    "provenance": [], "certificate": {}, "decay": {},
}

_READER = {
    "name": "b-reader", "statement": "b-reader reads the marker file",
    "trigger": ["b-reader::marker::y"],
    "method": {"steps": [{"tool": "filesystem.read_file",
                          "args": {"path": "mutation_marker.json"}}],
              "hash": "deadbeef0001"},
    "check": {"predicate": "contains", "value": "mutated"},
    "requires": {"tools": ["filesystem.read_file"]},
    "provenance": [], "certificate": {}, "decay": {},
}


def _write_skills_dir(tmp_path: Path, name: str, order: list[dict]) -> Path:
    """order[0] gets a filename that sorts first, order[1] second — so the
    two calls of this helper (mutator-then-reader vs reader-then-mutator)
    give certify_all a genuinely different processing order to prove
    identical results regardless."""
    d = tmp_path / name
    d.mkdir()
    for i, card in enumerate(order):
        (d / f"{i:02d}-{card['name']}.yaml").write_text(yaml.safe_dump(card, sort_keys=False))
    manifest = {
        "skills": [{"name": c["name"], "trigger": c["trigger"], "certificate": {}} for c in order],
        "coverage": {}, "frontier": [], "counts": {"skills": len(order), "certified": 0},
    }
    (d / "manifest.json").write_text(json.dumps(manifest))
    return d


def test_mutation_cannot_cross_from_one_skill_to_another(tmp_path):
    """The reader's check ('mutation_marker.json' contains 'mutated') can
    only pass on a fresh seed copy if the mutator's write leaked into it.
    With per-skill fresh copies, the reader must NEVER see the marker —
    the file simply doesn't exist on its own copy, so its oracle gate
    fails on the intact-seed check, deterministically, either order."""
    d = _write_skills_dir(tmp_path, "mutator-first", [_MUTATOR, _READER])
    out = certify_all(d, SEED)
    reader_result = next(r for r in out["results"] if r["name"] == "b-reader")
    assert reader_result["status"] != "certified", (
        "the reader certified — its fresh seed copy must never see the "
        "mutator's write; a leak here means the old shared-seed bug is back")
    assert "ORACLE-FAIL" in reader_result["verdict"] or "NON-DISCRIMINATING" in reader_result["verdict"]


def test_reorder_skill_files_identical_certificates(tmp_path):
    """The audit's literal test: reorder skill files -> identical
    certificates. Same two skills, opposite file-processing order."""
    d1 = _write_skills_dir(tmp_path, "mutator-first", [_MUTATOR, _READER])
    d2 = _write_skills_dir(tmp_path, "reader-first", [_READER, _MUTATOR])

    out1 = {r["name"]: r["status"] for r in certify_all(d1, SEED)["results"]}
    out2 = {r["name"]: r["status"] for r in certify_all(d2, SEED)["results"]}
    assert out1 == out2 == {"a-mutator": out1["a-mutator"], "b-reader": out1["b-reader"]}
    assert out1["b-reader"] == out2["b-reader"] != "certified"


# --------------------------------------------------------------------------- #
# statistical honesty: a flaky skill (one failure among replays) is not     #
# certified, even though the old wilson-floor rule would have cleared it    #
# --------------------------------------------------------------------------- #

def test_regime_label_is_deterministic_consistency_for_bank_skills(tmp_path):
    d = tmp_path / "skills"
    shutil.copytree(REPO / "skills", d)
    out = certify_all(d, SEED)
    certified = [r for r in out["results"] if r["status"] == "certified"]
    assert certified, "expected at least one certified skill in the committed library"
    for r in certified:
        card = yaml.safe_load((d / f"{r['name']}.yaml").read_text())
        cert = card["certificate"]
        assert cert["regime"] == "deterministic-consistency"
        assert cert["consistency"] == f"{cert['n']}/{cert['n']} deterministic replays"
        assert cert["wilson"][0] >= 0.70


def test_a_single_flaky_replay_disqualifies_even_above_the_old_wilson_floor(monkeypatch, tmp_path):
    """19/20 clears the OLD Wilson-lower-bound-vs-0.70 rule easily — but 20
    deterministic replays of the same frozen steps disagreeing even once
    means non-determinism, which the honest regime must never certify."""
    import dotmaps.bank.certify as certify_mod

    d = tmp_path / "skills"
    d.mkdir()
    card = dict(_READER)
    card["name"] = "flaky-skill"
    # a genuinely DISCRIMINATING check (holds on the intact seed, fails on
    # break_copy()'s all-.json-emptied broken copy) so the oracle gate
    # actually passes and probe() gets to run its 20 replays.
    card["check"] = {"predicate": "contains", "value": "putting-intensive"}
    card["method"] = {"steps": [{"tool": "filesystem.read_file",
                                 "args": {"path": "source_items.json"}}], "hash": "flaky0001"}
    (d / "flaky-skill.yaml").write_text(yaml.safe_dump(card, sort_keys=False))
    manifest = {"skills": [{"name": "flaky-skill", "trigger": card["trigger"], "certificate": {}}],
               "coverage": {}, "frontier": [], "counts": {"skills": 1, "certified": 0}}
    (d / "manifest.json").write_text(json.dumps(manifest))

    # monkeypatch evaluate() to fail exactly once during probe()'s 20 calls,
    # leaving the oracle gate's own 5 calls (1 intact + 1 broken + 3
    # stability) untouched — so the gate passes cleanly and probe() runs.
    real_evaluate = certify_mod.evaluate
    eval_calls = {"n": 0}

    def _flaky_evaluate(predicate, value, observation):
        eval_calls["n"] += 1
        result = real_evaluate(predicate, value, observation)
        # oracle_gate makes 1 (intact) + 1 (broken) + STABILITY_N(3) = 5 calls
        # before probe()'s 20 calls begin; flip the 10th probe call (call #15).
        if eval_calls["n"] == 15:
            return False
        return result

    monkeypatch.setattr(certify_mod, "evaluate", _flaky_evaluate)
    out = certify_mod.certify_all(d, SEED)
    result = out["results"][0]
    assert result["status"] != "certified", (
        "19/20 (one flaky replay) must not certify under the honest "
        "deterministic-consistency regime, even though 19/20 clears the old 0.70 Wilson floor")

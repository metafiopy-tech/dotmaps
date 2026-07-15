"""POKE loop core: rule banking, the two named traps, check compilation."""
import json
import subprocess
import sys
from pathlib import Path

from dotmaps.grow.banking import (compile_check, confirm, dot_eligible,
                                  validate_rule)
from dotmaps.grow.store import GrowStore


def make_seed(tmp_path: Path) -> Path:
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "export.json").write_text(json.dumps(
        [{"slug": "a", "title": "A"}, {"slug": "b", "title": "B"}]))
    (seed / "notes.txt").write_text("two records exported")
    return seed


def test_true_rule_confirms(tmp_path):
    seed = make_seed(tmp_path)
    rule = {"id": "r1", "statement": "export holds 2 items",
            "steps": [{"tool": "filesystem.read_file",
                       "args": {"path": "export.json"}}],
            "expect": {"predicate": "json_item_count", "value": 2}}
    assert validate_rule(rule) is None
    ok, obs = confirm(rule, seed)
    assert ok and '"slug"' in obs


def test_false_rule_does_not_confirm(tmp_path):
    seed = make_seed(tmp_path)
    rule = {"id": "r2", "statement": "export holds 7 items",
            "steps": [{"tool": "filesystem.read_file",
                       "args": {"path": "export.json"}}],
            "expect": {"predicate": "json_item_count", "value": 7}}
    ok, _ = confirm(rule, seed)
    assert not ok


def test_self_referential_rule_cannot_confirm(tmp_path):
    """Trap 1: a rule about the agent's OWN artifact must fail banking,
    because confirmation replays against a fresh seed copy where the
    artifact does not exist."""
    seed = make_seed(tmp_path)
    rule = {"id": "r3", "statement": "my scratch file says hello",
            "steps": [{"tool": "filesystem.read_file",
                       "args": {"path": "my_scratch.txt"}}],
            "expect": {"predicate": "contains", "value": "hello"}}
    ok, obs = confirm(rule, seed)
    assert not ok and "ERROR" in obs


def test_mutation_rule_confirms_but_verifier_is_read_only(tmp_path):
    """A write-then-read rule banks (the world confirms the mechanism), and
    its compiled check observes state only — it never replays the write."""
    seed = make_seed(tmp_path)
    rule = {"id": "r4", "statement": "a JSON file written here reads back",
            "steps": [{"tool": "filesystem.write_file",
                       "args": {"path": "out.json", "content": "[1, 2]"}},
                      {"tool": "filesystem.read_file",
                       "args": {"path": "out.json"}}],
            "expect": {"predicate": "json_item_count", "value": 2}}
    ok, _ = confirm(rule, seed)
    assert ok and dot_eligible(rule)
    check = compile_check(rule, tmp_path)
    assert "write" not in check.read_text().split('"""')[2]  # no write in code body

    # protocol: pass on a workspace where the state holds...
    ws_good = tmp_path / "good"; ws_good.mkdir()
    (ws_good / "out.json").write_text("[1, 2]")
    p = subprocess.run([sys.executable, str(check), "--workspace", str(ws_good)],
                       capture_output=True, text=True)
    assert p.returncode == 0 and json.loads(p.stdout)["pass"] is True
    # ...and FAIL on one where it doesn't (integrity-gate behavior, in miniature)
    ws_bad = tmp_path / "bad"; ws_bad.mkdir()
    p = subprocess.run([sys.executable, str(check), "--workspace", str(ws_bad)],
                       capture_output=True, text=True)
    assert p.returncode == 1 and json.loads(p.stdout)["pass"] is False


def test_wall_fact_banks_but_grows_no_dot(tmp_path):
    """Trap 2 adjacent: 'blocked' rules are primitives, never dots — a
    verifier cannot observe a wall."""
    seed = make_seed(tmp_path)
    (seed / ".dotmaps").mkdir()
    (seed / ".dotmaps" / "protected_paths.json").write_text('["export.json"]')
    rule = {"id": "r5", "statement": "the export file is write-protected",
            "steps": [{"tool": "filesystem.write_file",
                       "args": {"path": "export.json", "content": "[]"}}],
            "expect": {"predicate": "blocked"}}
    ok, _ = confirm(rule, seed)
    assert ok
    assert not dot_eligible(rule)
    assert compile_check(rule, tmp_path) is None


def test_store_hypothesis_lifecycle(tmp_path):
    st = GrowStore(tmp_path / "run")
    rule = {"id": "r9", "statement": "s", "steps": [], "expect": {}}
    st.add_hypothesis(rule)
    assert [r["id"] for r in st.open_hypotheses()] == ["r9"]
    st.resolve_hypothesis("r9", "banked")
    assert st.open_hypotheses() == []
    n = st.journal_poke(1, {"tool": "t", "args": {}}, "obs")
    assert n == 1 and st.poke_count() == 1


def test_non_discriminating_check_cannot_bank(tmp_path):
    """Run-001 autopsy regression: `json_parses` on an always-present JSON
    file confirms on the seed AND on a broken copy — the hardened gate must
    refuse it at bank time."""
    seed = make_seed(tmp_path)
    rule = {"id": "r7", "statement": "items have a 'name' attribute",
            "steps": [{"tool": "filesystem.read_file",
                       "args": {"path": "export.json"}}],
            "expect": {"predicate": "json_parses", "value": True}}
    ok, obs = confirm(rule, seed)
    assert not ok and "NON-DISCRIMINATING" in obs

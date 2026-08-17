"""H1 (HARDENING_BRIEF): the chat proof boundary. The audit's P0 finding —
`_chat_gate()` checked answer.json's SHAPE but never mechanically evaluated
the proposed predicate/value, and `ask()` returned the model's free-text
answer even when that mechanical check would have failed. These three tests
are the audit's own regression tests, verbatim:

  - valid path/predicate but false value -> no asserted answer
  - answer text contradicts a true structured fact -> renderer prevents it
  - subtype != success but answer.json exists -> work order failed
"""
import json
import shutil
from pathlib import Path

import pytest

from dotmaps.queen import chat as chat_mod
from dotmaps.queen import trips as trips_mod

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def env(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(REPO / "skills", skills)
    seed = tmp_path / "seed"
    shutil.copytree(REPO / "corpus" / "pilot" / "seed-ws", seed)
    return {
        "trips_path": tmp_path / "trips.jsonl",
        "chat_path": tmp_path / "chat.jsonl",
        "skills_dir": skills,
        "maps_dir": tmp_path / "maps",
        "seed": seed,
    }


# -- test 1: valid path/predicate but a FALSE value -> no asserted answer -- #

def _false_value_runner(workspace, job, *, model, max_turns, timeout_s, trips_path, run_id):
    answer = {
        "answer": "Yes — there are exactly 99 items.",
        "statement": "source_items.json holds 99 items",
        "path": "source_items.json",
        "predicate": "json_item_count",
        "value": 99,  # real file has 5 — structurally fine, mechanically false
    }
    (workspace / "answer.json").write_text(json.dumps(answer))
    return {"ok": True, "subtype": "success", "num_turns": 2, "cost_usd": 0.01}


def test_false_value_never_reaches_an_asserted_answer(env):
    out = chat_mod.ask("how many items are there really?", trips_path=env["trips_path"],
                       chat_path=env["chat_path"], skills_dir=env["skills_dir"],
                       maps_dir=env["maps_dir"], seed=env["seed"], _runner=_false_value_runner)
    assert "99" not in out["reply"]
    assert out["reply"] == "I tried, but I couldn't find a clean, checkable answer to that."
    assert out["learn_offer"] is None
    failed = [t for t in trips_mod.read_all(env["trips_path"])
             if t["type"] == "WORK_ORDER" and t["data"].get("phase") == "failed"]
    assert len(failed) == 1
    assert "did not mechanically hold" in failed[0]["data"]["gate"]["reason"]


def test_chat_gate_directly_rejects_a_false_value(env):
    workspace = env["seed"]
    answer = {"answer": "x", "statement": "x", "path": "source_items.json",
             "predicate": "json_item_count", "value": 99}
    (workspace / "answer.json").write_text(json.dumps(answer))
    gate = chat_mod._chat_gate(workspace, {"subtype": "success"})
    assert gate["passed"] is False
    assert "mechanically hold" in gate["reason"]


# -- test 2: contradicting free text -> renderer prevents the contradiction - #

def test_renderer_drops_contradicting_free_text_json_item_count():
    answer = {"answer": "No, there are only 3 items in that file.",
             "statement": "source_items.json holds 5 items",
             "path": "source_items.json", "predicate": "json_item_count", "value": 5}
    reply = chat_mod._render_checked_reply(answer)
    assert "3" not in reply
    assert reply == "Confirmed — source_items.json contains exactly 5 items."


def test_renderer_drops_negation_marked_free_text_contains():
    answer = {"answer": "Actually no, it does not contain that slug.",
             "statement": "source_items.json contains the slug",
             "path": "source_items.json", "predicate": "contains", "value": "holiday-mini-camp"}
    reply = chat_mod._render_checked_reply(answer)
    assert "does not" not in reply
    assert reply == "Confirmed — source_items.json contains 'holiday-mini-camp'."


def test_renderer_keeps_consistent_free_text_as_color():
    answer = {"answer": "Yes, exactly 5, nothing hidden.",
             "statement": "source_items.json holds 5 items",
             "path": "source_items.json", "predicate": "json_item_count", "value": 5}
    reply = chat_mod._render_checked_reply(answer)
    assert reply.startswith("Confirmed — source_items.json contains exactly 5 items.")
    assert "Yes, exactly 5" in reply


# -- test 3: subtype != success but answer.json exists -> work order failed - #

def _subtype_failure_runner(workspace, job, *, model, max_turns, timeout_s, trips_path, run_id):
    # a real answer.json IS written — e.g. from a partial run before the
    # process errored out — but the model process itself did not succeed.
    answer = {"answer": "Sure, 5 items.", "statement": "source_items.json holds 5 items",
             "path": "source_items.json", "predicate": "json_item_count", "value": 5}
    (workspace / "answer.json").write_text(json.dumps(answer))
    return {"ok": False, "subtype": "error_max_turns", "num_turns": 20, "cost_usd": 0.09}


def test_subtype_not_success_fails_work_order_even_with_valid_answer_json(env):
    out = chat_mod.ask("how many items?", trips_path=env["trips_path"],
                       chat_path=env["chat_path"], skills_dir=env["skills_dir"],
                       maps_dir=env["maps_dir"], seed=env["seed"],
                       _runner=_subtype_failure_runner)
    assert out["learn_offer"] is None
    assert out["reply"] == "I tried, but I couldn't find a clean, checkable answer to that."
    failed = [t for t in trips_mod.read_all(env["trips_path"])
             if t["type"] == "WORK_ORDER" and t["data"].get("phase") == "failed"]
    assert len(failed) == 1
    assert "did not succeed" in failed[0]["data"]["gate"]["reason"]
    assert "error_max_turns" in failed[0]["data"]["gate"]["reason"]


def test_chat_gate_directly_rejects_non_success_subtype(env):
    workspace = env["seed"]
    answer = {"answer": "x", "statement": "x", "path": "source_items.json",
             "predicate": "json_item_count", "value": 5}
    (workspace / "answer.json").write_text(json.dumps(answer))
    gate = chat_mod._chat_gate(workspace, {"subtype": "error_max_turns"})
    assert gate["passed"] is False
    assert "did not succeed" in gate["reason"]

"""Tab 1: the front door. ROUTE FIRST -> WORK ORDER -> plain reply, with
the cost chip mechanically earned every time — never a stored label. The
live `claude` CLI is never invoked here: `_runner` is injected, same
convention as test_queen_workorder.py."""
import json
import shutil
from pathlib import Path

import pytest
import yaml

from dotmaps.grow import banking
from dotmaps.queen import chat as chat_mod
from dotmaps.queen import sleep as sleep_mod
from dotmaps.queen import surface as surface_mod
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
        "live_root": tmp_path / "live",
    }


def _refuse_runner(*a, **k):
    raise AssertionError("the runner must not be called on a covered ask")


def test_route_first_hits_pilot_workflow_zero_model_calls(env):
    out = chat_mod.ask("check the demo workspace", trips_path=env["trips_path"],
                       chat_path=env["chat_path"], skills_dir=env["skills_dir"],
                       maps_dir=env["maps_dir"], seed=env["seed"], _runner=_refuse_runner)
    assert out["chip"]["kind"] == "free"
    assert out["chip"]["model_calls"] == 0
    history = chat_mod.read_chat(env["chat_path"])
    assert history[0]["role"] == "user" and history[0]["text"] == "check the demo workspace"
    assert history[1]["role"] == "queen" and history[1]["chip"]["kind"] == "free"


def test_seed_workflow_not_covered_redirects_without_a_model_call(env):
    out = chat_mod.ask("please migrate the menu data", trips_path=env["trips_path"],
                       chat_path=env["chat_path"], skills_dir=env["skills_dir"],
                       maps_dir=env["maps_dir"], seed=env["seed"], _runner=_refuse_runner)
    assert out["chip"] is None
    assert "Workflows" in out["reply"]


NEW_FACT_ANSWER = {
    "answer": "Yes — there's a holiday mini camp in the list.",
    "statement": "source_items.json contains an item with slug 'holiday-mini-camp'",
    "path": "source_items.json",
    "predicate": "contains",
    "value": '"slug": "holiday-mini-camp"',
}


def _ok_runner(workspace, job, *, model, max_turns, timeout_s, trips_path, run_id):
    (workspace / "answer.json").write_text(json.dumps(NEW_FACT_ANSWER))
    trips_mod.emit("WORK_ORDER", path=trips_path, phase="step", run_id=run_id,
                   seq_in_run=1, text="Reading source_items.json", tool="Read",
                   model_call=True, elapsed=0.4)
    return {"ok": True, "subtype": "success", "num_turns": 3, "cost_usd": 0.031}


def _bad_gate_runner(workspace, job, *, model, max_turns, timeout_s, trips_path, run_id):
    return {"ok": True, "subtype": "success", "num_turns": 1, "cost_usd": 0.01}


def test_ask_unknown_message_runs_work_order_and_offers_to_learn(env):
    out = chat_mod.ask("does anyone offer a holiday camp?", trips_path=env["trips_path"],
                       chat_path=env["chat_path"], skills_dir=env["skills_dir"],
                       maps_dir=env["maps_dir"], seed=env["seed"], _runner=_ok_runner)
    assert out["chip"]["kind"] == "model"
    assert out["chip"]["turns"] == 3
    assert out["chip"]["cost_usd"] == pytest.approx(0.031)
    assert out["learn_offer"] is not None

    esc = surface_mod.open_escalations(env["trips_path"])
    learn = [e for e in esc if e.get("kind") == "learn_offer"]
    assert len(learn) == 1
    assert learn[0]["options"] == ["Yes — learn it now", "No — leave it be"]

    steps = [t for t in trips_mod.read_all(env["trips_path"])
            if t["type"] == "WORK_ORDER" and t["data"].get("phase") == "step"]
    assert len(steps) == 1
    assert "Reading" in steps[0]["data"]["text"]


def test_work_order_gate_fails_closed_when_no_answer_produced(env):
    out = chat_mod.ask("does anyone offer a holiday camp?", trips_path=env["trips_path"],
                       chat_path=env["chat_path"], skills_dir=env["skills_dir"],
                       maps_dir=env["maps_dir"], seed=env["seed"], _runner=_bad_gate_runner)
    assert out["learn_offer"] is None
    assert "couldn't find" in out["reply"]
    failed = [t for t in trips_mod.read_all(env["trips_path"])
             if t["type"] == "WORK_ORDER" and t["data"].get("phase") == "failed"]
    assert len(failed) == 1


def test_resolve_learn_offer_yes_banks_primitive_and_writes_map(env):
    chat_mod.ask("does anyone offer a holiday camp?", trips_path=env["trips_path"],
                chat_path=env["chat_path"], skills_dir=env["skills_dir"],
                maps_dir=env["maps_dir"], seed=env["seed"], _runner=_ok_runner)
    eid = chat_mod._escalate_id("does anyone offer a holiday camp?")
    result = chat_mod.resolve_learn_offer(eid, 1, trips_path=env["trips_path"],
                                          chat_path=env["chat_path"],
                                          maps_dir=env["maps_dir"],
                                          live_root=env["live_root"])
    assert result["learned"] is True
    map_dir = env["maps_dir"] / result["map"]
    assert (map_dir / "map.yaml").exists()
    assert (map_dir / "chat_trigger.json").exists()
    trig = json.loads((map_dir / "chat_trigger.json").read_text())
    assert trig["statement"] == NEW_FACT_ANSWER["statement"]

    prim_files = list(env["live_root"].glob("chat-*/primitives/*.yaml"))
    assert len(prim_files) == 1
    prim = yaml.safe_load(prim_files[0].read_text())
    assert prim["statement"] == NEW_FACT_ANSWER["statement"]
    assert prim["expect"] == {"predicate": "contains", "value": NEW_FACT_ANSWER["value"]}

    history = chat_mod.read_chat(env["chat_path"])
    assert "know that for free" in history[-1]["text"]


def test_resolve_learn_offer_no_leaves_nothing_banked(env):
    chat_mod.ask("does anyone offer a holiday camp?", trips_path=env["trips_path"],
                chat_path=env["chat_path"], skills_dir=env["skills_dir"],
                maps_dir=env["maps_dir"], seed=env["seed"], _runner=_ok_runner)
    eid = chat_mod._escalate_id("does anyone offer a holiday camp?")
    result = chat_mod.resolve_learn_offer(eid, 2, trips_path=env["trips_path"],
                                          chat_path=env["chat_path"],
                                          maps_dir=env["maps_dir"],
                                          live_root=env["live_root"])
    assert result["learned"] is False
    assert not list(env["live_root"].glob("**/*.yaml"))


def test_full_loop_learn_sleep_then_free_reroute(env):
    """The acceptance test's core claim, offline: a new ask costs a model
    call; after 'yes' + a sleep tick, the SAME ask is $0 and the runner is
    never invoked again."""
    message = "does anyone offer a holiday camp?"
    out1 = chat_mod.ask(message, trips_path=env["trips_path"], chat_path=env["chat_path"],
                        skills_dir=env["skills_dir"], maps_dir=env["maps_dir"],
                        seed=env["seed"], _runner=_ok_runner)
    assert out1["chip"]["kind"] == "model"

    eid = chat_mod._escalate_id(message)
    chat_mod.resolve_learn_offer(eid, 1, trips_path=env["trips_path"],
                                 chat_path=env["chat_path"], maps_dir=env["maps_dir"],
                                 live_root=env["live_root"])

    sleep_out = sleep_mod.sleep(skills_dir=env["skills_dir"], seed=env["seed"],
                               trips_path=env["trips_path"], live_root=env["live_root"])
    assert sleep_out["harvested_candidates"] == 1

    learned_card = next(f for f in env["skills_dir"].glob("*.yaml")
                        if yaml.safe_load(f.read_text())["statement"] == NEW_FACT_ANSWER["statement"])
    assert yaml.safe_load(learned_card.read_text())["certificate"]["status"] == "certified"

    out2 = chat_mod.ask(message, trips_path=env["trips_path"], chat_path=env["chat_path"],
                        skills_dir=env["skills_dir"], maps_dir=env["maps_dir"],
                        seed=env["seed"], _runner=_refuse_runner)
    assert out2["chip"]["kind"] == "free"
    assert out2["chip"]["model_calls"] == 0
    assert out2["reply"] == NEW_FACT_ANSWER["answer"]


def test_chat_ledger_hash_chain_integrity(env):
    chat_mod.emit_chat("user", "hello", path=env["chat_path"])
    chat_mod.emit_chat("queen", "hi there", path=env["chat_path"], chip=chat_mod.free_chip())
    ok, reason = chat_mod.verify_chat_integrity(env["chat_path"])
    assert ok and reason is None

    lines = env["chat_path"].read_text().splitlines()
    tampered = json.loads(lines[0])
    tampered["text"] = "tampered"
    lines[0] = json.dumps(tampered)
    env["chat_path"].write_text("\n".join(lines) + "\n")
    ok, reason = chat_mod.verify_chat_integrity(env["chat_path"])
    assert not ok and "seq 1" in reason

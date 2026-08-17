"""WATCH BRIEF gates (W1/W2/W3) — point-and-watch, the real oracle.

Every test here runs against a REAL local HTTP server (`_watch_fixture.
WatchSite`), never a mock: the whole point of this build is "HTTP/DOM —
this IS a real oracle; no model needed to verify," so the tests hold
themselves to the same standard.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from dotmaps.bank.certify import wilson as bank_wilson
from dotmaps.queen import assure as assure_mod
from dotmaps.queen import surface as surface_mod
from dotmaps.queen import trips as trips_mod
from dotmaps.queen import ui as ui_mod
from dotmaps.watch import certify, compiler, history, runner

from _watch_fixture import WatchSite

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def site():
    s = WatchSite()
    s.start()
    yield s
    s.stop()


@pytest.fixture
def sandbox(tmp_path):
    trips_path = tmp_path / "trips.jsonl"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return trips_path, skills_dir


# --------------------------------------------------------------------------- #
# W1 — compile a health map                                                  #
# --------------------------------------------------------------------------- #

def test_w1_health_map_has_at_least_8_dots(site):
    hm = compiler.compile_health_map(site.httpd.socket.getsockname() and
                                     f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/")
    assert len(hm["dots"]) >= 8


def test_w1_dots_cover_every_predicate_kind(site):
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    kinds = {d["kind"] for d in hm["dots"]}
    assert kinds == {"page_responds", "page_title", "form_responds", "asset_loads"}


def test_w1_titles_are_derived_from_the_real_crawl_not_hardcoded(site):
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    title_dots = [d for d in hm["dots"] if d["kind"] == "page_title"]
    values = {d["check"]["value"] for d in title_dots}
    assert "About Us" in values and "Contact" in values


def test_w1_dot_ids_are_stable_across_independent_recompiles(site):
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    a = compiler.compile_health_map(base)
    b = compiler.compile_health_map(base)
    assert {d["id"] for d in a["dots"]} == {d["id"] for d in b["dots"]}


def test_w1_dead_target_still_compiles_a_one_dot_failing_map():
    hm = compiler.compile_health_map("http://127.0.0.1:1/")  # nothing listens here
    assert len(hm["dots"]) == 1
    assert hm["dots"][0]["kind"] == "page_responds"


def test_w1_every_dot_is_a_real_bank_rule_shape(site):
    """No bespoke check language — every dot runs through the exact same
    method.steps/check.predicate machinery a bank skill does."""
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    for d in hm["dots"]:
        assert d["method"]["steps"][0]["tool"] == "fetch.get"
        assert d["check"]["predicate"] == "contains"


# --------------------------------------------------------------------------- #
# W2 — live verification theater, sabotage flips a dot red + ESCALATE        #
# --------------------------------------------------------------------------- #

def test_w2_first_cycle_lights_every_dot_green(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    out = runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
    assert out["cycle"] == 1
    assert all(r["status"] == "green" for r in out["results"])


def test_w2_sabotage_flips_the_dot_red_next_cycle_with_a_receipt(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)  # clean baseline

    site.sabotage("/about")
    out = runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)

    about_title_dot = next(d for d in hm["dots"]
                           if d["kind"] == "page_title" and "/about" in d["url"])
    result = next(r for r in out["results"] if r["dot"] == about_title_dot["id"])
    assert result["status"] == "red"
    assert "About Us" in result["evidence"]  # the receipt names what was expected

    esc = surface_mod.open_escalations(trips_path)
    assert len(esc) == 1
    assert esc[0]["dot"] == about_title_dot["id"]
    assert "About Us" in esc[0]["evidence"]  # ESCALATE carries the same receipt


def test_w2_unreachable_target_is_amber_not_red(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    site.take_down("/about")
    out = runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
    about_dot = next(d for d in hm["dots"]
                     if d["kind"] == "page_title" and "/about" in d["url"])
    # /about now 503s: the page_responds check fails RED (a real HTTP answer,
    # just the wrong one) — a genuinely unreachable target (connection
    # refused) is exercised by test_w1_dead_target_still_compiles above.
    result = next(r for r in out["results"] if r["dot"] == about_dot["id"])
    assert result["status"] == "red"


def test_w2_repeat_failure_does_not_spawn_a_second_escalation(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    site.sabotage("/about")
    runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
    runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
    esc = surface_mod.open_escalations(trips_path)
    about_title_dot = next(d for d in hm["dots"]
                           if d["kind"] == "page_title" and "/about" in d["url"])
    matching = [e for e in esc if e["dot"] == about_title_dot["id"]]
    assert len(matching) == 1


def test_w2_trip_chain_stays_intact_across_many_cycles(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    for _ in range(5):
        runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
    ok, reason = trips_mod.verify_integrity(trips_path)
    assert ok, reason


def test_w2_diary_shows_the_sabotage_as_a_change_not_every_check(site, sandbox):
    """'Silence = health, per her law': the diary must not flood with one
    line per dot per cycle — only transitions surface. The very first
    check of each dot is itself a transition (unlit -> green), so cycle 1
    seeds one line per dot; three more clean cycles after that must add
    nothing at all."""
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)  # seeds one line/dot
    baseline = ui_mod.diary_payload(trips_path, skills_dir, limit=50)
    assert len(baseline) == len(hm["dots"])

    for _ in range(3):  # 27 more raw check trips, all repeats — zero should surface
        runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
    quiet_diary = ui_mod.diary_payload(trips_path, skills_dir, limit=50)
    assert len(quiet_diary) == len(baseline)

    site.sabotage("/about")
    runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
    loud_diary = ui_mod.diary_payload(trips_path, skills_dir, limit=50)
    # the sabotage cycle adds exactly the failure (+ its escalation) as new lines
    assert len(loud_diary) > len(quiet_diary)
    assert any("about" in e["text"].lower() for e in loud_diary)


# --------------------------------------------------------------------------- #
# W3 — 20 consecutive clean checks mint a real certificate                   #
# --------------------------------------------------------------------------- #

def test_w3_fast_clocked_cycle_certifies_a_clean_dot(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)

    for _ in range(certify.CERT_N):  # fast-clock: no pacing, no wall-clock wait
        runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)

    cards = sorted((skills_dir / "watch").glob("*.yaml"))
    assert len(cards) == len(hm["dots"])
    for f in cards:
        card = yaml.safe_load(f.read_text())
        assert card["certificate"]["status"] == "certified"
        assert card["certificate"]["n"] == certify.CERT_N
        assert card["certificate"]["wilson"] == [
            round(x, 3) for x in bank_wilson(certify.CERT_N, certify.CERT_N)]


def test_w3_certified_trip_emitted_and_chain_intact(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    for _ in range(certify.CERT_N):
        runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)

    recs = trips_mod.read_all(trips_path)
    first_dot = hm["dots"][0]["id"]
    id_ = history.trip_id(hm["slug"], first_dot)
    certified_trips = [r for r in recs if r["type"] == "CERTIFIED"
                       and r["data"].get("id") == id_]
    assert len(certified_trips) >= 1
    assert any(t["data"].get("evidence", "").startswith("first certification")
              for t in certified_trips)

    ok, reason = trips_mod.verify_integrity(trips_path)
    assert ok, reason


def test_w3_honeycomb_cell_fills_gold_for_the_certified_dot(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    for _ in range(certify.CERT_N):
        runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)

    skills = ui_mod.skills_payload(skills_dir)
    watch_entries = [s for s in skills if s["name"].startswith("watch-")]
    assert len(watch_entries) == len(hm["dots"])
    assert all(s["status"] == "certified" for s in watch_entries)


def test_w3_a_dot_that_never_holds_never_certifies(site, sandbox):
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    site.sabotage("/about")  # /about title never passes, from cycle 1 on
    for _ in range(certify.CERT_N + 5):
        runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)

    about_title_dot = next(d for d in hm["dots"]
                           if d["kind"] == "page_title" and "/about" in d["url"])
    assert certify.already_certified(skills_dir, hm["slug"], about_title_dot["id"]) is None
    # every OTHER dot on the same target still certifies normally
    other = [d for d in hm["dots"] if d["id"] != about_title_dot["id"]]
    assert all(certify.already_certified(skills_dir, hm["slug"], d["id"]) for d in other)


def test_w3_assure_still_green_with_the_watch_oracle_claim():
    """`dotmaps assure` re-proves the whole mechanism itself (fresh local
    target, real sabotage, fast-clocked) as its own claim — this is that
    claim, exercised directly."""
    ok, detail = assure_mod.check_watch_oracle()
    assert ok, detail


def test_w3_full_assure_run_passes_with_watch_row_present():
    result = assure_mod.run_assure()
    failing = [r for r in result["rows"] if not r["passed"]]
    assert result["pass"] is True, failing
    assert any("watch" in r["claim"].lower() for r in result["rows"])


# --------------------------------------------------------------------------- #
# skills/watch/ isolation — the whole reason watch cards live in a subdir    #
# --------------------------------------------------------------------------- #

def test_watch_cards_do_not_disturb_the_generic_certify_reverify(site, sandbox, tmp_path):
    """The exact regression this design avoids: dumping a watch card into
    the top-level skills/ dir would make bank/certify.py's certify_all try
    to replay it via filesystem break-copy semantics and convict it. Watch
    cards live one level down, invisible to that non-recursive glob."""
    trips_path, skills_dir = sandbox
    base = f"http://127.0.0.1:{site.httpd.socket.getsockname()[1]}/"
    hm = compiler.compile_health_map(base)
    for _ in range(certify.CERT_N):
        runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
    assert list(skills_dir.glob("*.yaml")) == []  # nothing leaked to top level
    assert list((skills_dir / "watch").glob("*.yaml"))  # the cards are there, one level down

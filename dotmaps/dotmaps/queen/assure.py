"""ASSURE — Q11: the certainty command.

"How can I be sure it does everything we said." `dotmaps assure` walks a
CLAIMS table — claim text, the mechanical check, the artifact it reads —
and prints PASS/FAIL, exit nonzero on any FAIL. Every check RE-RUNS the
actual instrument against a disposable copy where mutation is possible
(route_map, certify_all, the governor backtest, sleep, touch(), the
work-order gate, the UI's own server) — nothing here trusts a status
field's own say-so; frozen law #1 applies to auditing the queen herself.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import multiprocessing
import os
import shutil
import tempfile
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

from ..bank.certify import certify_all
from ..net import safefetch
from . import chat as chat_mod
from . import dispatch as dispatch_mod
from . import governor as governor_mod
from . import paper as paper_mod
from . import reconsolidate
from . import sandbox as sandbox_mod
from . import sleep as sleep_mod
from . import surface as surface_mod
from . import trips as trips_mod
from . import ui as ui_mod
from . import workorder as workorder_mod

REPO_ROOT = trips_mod.REPO_ROOT
FROZEN_HASHES_PATH = Path(__file__).parent / "frozen_hashes.json"

REGISTRATION_FILES = [
    REPO_ROOT / "corpus" / "pilot2_registration.md",
    REPO_ROOT / "corpus" / "window_assay_registration.md",
    REPO_ROOT / "experiments" / "e1b_registration.md",
    REPO_ROOT / "experiments" / "e1c_registration.md",
    REPO_ROOT / "experiments" / "e1d_registration.md",
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extractor_rubric_block() -> str:
    """The FROZEN RUBRIC block (R-UNIT..R-STATE): bank/extractor.py's
    module docstring, unmodified since gate G1 per frozen law #2."""
    text = (REPO_ROOT / "dotmaps" / "dotmaps" / "bank" / "extractor.py").read_text()
    start = text.index('"""BANK')
    end = text.index('"""', start + 3) + 3
    return text[start:end]


def _certify_oracle_gate_block() -> str:
    """bank/certify.py's oracle_gate() body — ordering is law (§2.3b)."""
    text = (REPO_ROOT / "dotmaps" / "dotmaps" / "bank" / "certify.py").read_text()
    start = text.index("def oracle_gate")
    end = text.index("\ndef probe(")
    return text[start:end]


def build_frozen_manifest() -> dict[str, Any]:
    return {
        "extractor_rubric": _sha256(_extractor_rubric_block().encode()),
        "certify_oracle_gate": _sha256(_certify_oracle_gate_block().encode()),
        "registrations": {
            str(p.relative_to(REPO_ROOT)): _sha256(p.read_bytes())
            for p in REGISTRATION_FILES if p.exists()
        },
    }


def generate_frozen_manifest() -> Path:
    """Run ONCE, at this gate's landing, to freeze the current bytes —
    committed alongside assure.py. `dotmaps assure` itself never calls
    this; it only ever verifies against what was frozen (`--freeze` is a
    separate, explicit, human-run action, same spirit as the governor
    backtest being a separate script from the governor it calibrates)."""
    FROZEN_HASHES_PATH.write_text(json.dumps(build_frozen_manifest(), indent=2) + "\n")
    return FROZEN_HASHES_PATH


# --------------------------------------------------------------------------- #
# the ten checks — each re-runs the real instrument, never self-report       #
# --------------------------------------------------------------------------- #

def check_pilot_covered() -> tuple[bool, str]:
    tmp = Path(tempfile.mkdtemp(prefix="assure-pilot-"))
    skills = tmp / "skills"
    shutil.copytree(REPO_ROOT / "skills", skills)
    report = dispatch_mod.dispatch("pilot", trips_path=tmp / "trips.jsonl", skills=skills)
    ok = (len(report["covered"]) == 4 and not report["frontier"]
          and report["model_calls"] == 0 and report["cost_usd"] == 0.0
          and all(d["passed"] for d in report["covered"]))
    return ok, (f"covered={len(report['covered'])}/4 frontier={len(report['frontier'])} "
               f"model_calls={report['model_calls']} cost=${report['cost_usd']}")


def check_certificates_reverify() -> tuple[bool, str]:
    skills_dir = REPO_ROOT / "skills"
    certified_before = set()
    for f in sorted(skills_dir.glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        if card.get("certificate", {}).get("status") == "certified":
            certified_before.add(card["name"])
    if not certified_before:
        return False, "no certified skills in the committed library to re-verify"

    tmp = Path(tempfile.mkdtemp(prefix="assure-certify-"))
    skills_copy = tmp / "skills"
    shutil.copytree(skills_dir, skills_copy)
    seed_copy = tmp / "seed"
    shutil.copytree(REPO_ROOT / "corpus" / "pilot" / "seed-ws", seed_copy)
    certify_all(skills_copy, seed_copy)

    regressed = []
    for f in sorted(skills_copy.glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        if card["name"] in certified_before and card["certificate"]["status"] != "certified":
            regressed.append(card["name"])
    ok = not regressed
    return ok, (f"{len(certified_before)} certified skill(s) reprobed clean"
               if ok else f"REGRESSED on reprobe: {regressed}")


def check_trip_chain_integrity(trips_path: Path = trips_mod.DEFAULT_TRIPS_PATH
                               ) -> tuple[bool, str]:
    ok, reason = trips_mod.verify_integrity(trips_path)
    n = len(trips_mod.read_all(trips_path))
    return ok, (f"{n} trip(s), full chain verified OK" if ok else f"chain broken: {reason}")


def check_frozen_files_unchanged(manifest_path: Path = FROZEN_HASHES_PATH
                                 ) -> tuple[bool, str]:
    if not manifest_path.exists():
        return False, (f"no frozen manifest at {manifest_path} — "
                       f"run generate_frozen_manifest() once, then commit it")
    frozen = json.loads(manifest_path.read_text())
    current = build_frozen_manifest()
    diffs = []
    if frozen.get("extractor_rubric") != current["extractor_rubric"]:
        diffs.append("bank/extractor.py rubric")
    if frozen.get("certify_oracle_gate") != current["certify_oracle_gate"]:
        diffs.append("bank/certify.py oracle-gate block")
    for name, h in frozen.get("registrations", {}).items():
        if current["registrations"].get(name) != h:
            diffs.append(name)
    ok = not diffs
    return ok, ("all frozen bytes match the committed manifest" if ok
               else f"CHANGED since freeze: {diffs}")


def check_governor_backtest_reproduces() -> tuple[bool, str]:
    report_path = REPO_ROOT / "runs" / "governor-backtest" / "report.json"
    if not report_path.exists():
        return False, "no committed runs/governor-backtest/report.json"
    committed = json.loads(report_path.read_text())

    spec = importlib.util.spec_from_file_location(
        "governor_backtest", REPO_ROOT / "experiments" / "governor_backtest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fresh = mod.run_backtest()  # rewrites report.json — deterministic, so idempotent

    p75 = fresh["persistence_budget"]["p75"]
    ok = (fresh["pass"] is True
          and p75 == committed["persistence_budget"]["p75"] == governor_mod.PERSISTENCE_BUDGET_POKES
          and fresh["verdict_reproduction"]["e1c_refog_total"]
              == committed["verdict_reproduction"]["e1c_refog_total"]
          and fresh["verdict_reproduction"]["e1d_refog_total"]
              == committed["verdict_reproduction"]["e1d_refog_total"] == 0)
    return ok, (f"p75={p75} (governor constant={governor_mod.PERSISTENCE_BUDGET_POKES}) "
               f"e1c_refog={fresh['verdict_reproduction']['e1c_refog_total']} "
               f"e1d_refog={fresh['verdict_reproduction']['e1d_refog_total']} "
               f"pass={fresh['pass']}")


def check_harvest_idempotent() -> tuple[bool, str]:
    tmp = Path(tempfile.mkdtemp(prefix="assure-harvest-"))
    skills = tmp / "skills"
    shutil.copytree(REPO_ROOT / "skills", skills)
    out = sleep_mod.sleep(skills_dir=skills, seed=REPO_ROOT / "corpus" / "pilot" / "seed-ws",
                          trips_path=tmp / "trips.jsonl", live_root=REPO_ROOT / "runs" / "queen-live")
    ok = out["harvested_candidates"] == 0
    return ok, f"harvested_candidates={out['harvested_candidates']} (expect 0 — already fully harvested)"


def check_c3_safety() -> tuple[bool, str]:
    tmp = Path(tempfile.mkdtemp(prefix="assure-c3-"))
    skills = tmp / "skills"
    shutil.copytree(REPO_ROOT / "skills", skills)
    trips_path = tmp / "trips.jsonl"
    touched = 0
    for f in sorted(skills.glob("*.yaml")):
        card = yaml.safe_load(f.read_text())
        if card.get("certificate", {}).get("status") != "certified":
            continue
        try:
            reconsolidate.touch(f, trips_path=trips_path)
        except AssertionError as e:
            return False, f"C3 LAW-3 VIOLATION on {card['name']}: {e}"
        touched += 1
    if touched == 0:
        return False, "no certified cards to touch — nothing exercised"
    return True, f"touch() left method/check bytes hash-identical on {touched} certified card(s)"


def check_funeral_intact() -> tuple[bool, str]:
    p = REPO_ROOT / "runs" / "e1d-verdict" / "verdict.json"
    if not p.exists():
        return False, "runs/e1d-verdict/verdict.json missing"
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        return False, f"verdict.json does not parse: {e}"
    clause = str(data.get("final_trial_clause_executed", ""))
    ok = "DIES PERMANENTLY" in clause.upper() or "DEAD" in clause.upper()
    return ok, clause[:140]


def _sabotage_runner(workspace, job, *, model, max_turns, timeout_s):
    """A DO phase that reports success but never touches the workspace —
    the gate, not the runner's own self-report, must be what fails this."""
    return {"ok": True, "subtype": "success", "num_turns": 1, "cost_usd": 0.0}


def check_work_order_gate_fails_closed() -> tuple[bool, str]:
    tmp = Path(tempfile.mkdtemp(prefix="assure-workorder-"))
    trips_path = tmp / "trips.jsonl"
    result = workorder_mod.run_work_order("migration", trips_path=trips_path,
                                          _runner=_sabotage_runner)
    tripped = any(t["type"] == "WORK_ORDER" and t["data"].get("phase") == "failed"
                 for t in trips_mod.read_all(trips_path))
    ok = (result["ok"] is False) and (not result["gate"]["passed"]) and tripped
    return ok, (f"gate_passed={result['gate']['passed']} ok={result['ok']} "
               f"WORK_ORDER_FAILED trip emitted={tripped}")


def check_watch_oracle() -> tuple[bool, str]:
    """Q12 (WATCH_BRIEF): re-proves the whole point-and-watch mechanism
    against a fresh, disposable, sabotage-able local target — the exact
    three done-tests (W1 compiles >=8 dots, W2 sabotage flips one red with
    a receipt, W3 twenty clean checks mint a real certificate), run for
    real, every time `dotmaps assure` runs. Never touches the repo's own
    skills/watch/ — cards land in a tempdir, same disposable-copy
    discipline every other check here uses."""
    from ..watch import certify as watch_certify
    from ..watch import compiler as watch_compiler
    from ..watch import runner as watch_runner
    from ..watch.selftest import WatchSite

    tmp = Path(tempfile.mkdtemp(prefix="assure-watch-"))
    trips_path = tmp / "trips.jsonl"
    skills_dir = tmp / "skills"
    site = WatchSite()
    base = site.start()
    try:
        hm = watch_compiler.compile_health_map(base)
        if len(hm["dots"]) < 8:
            return False, f"health map compiled only {len(hm['dots'])} dots (need >=8)"

        about_title = next(d for d in hm["dots"]
                           if d["kind"] == "page_title" and "/about" in d["url"])
        site.sabotage("/about")
        cycle1 = watch_runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)
        red = next(r for r in cycle1["results"] if r["dot"] == about_title["id"])
        if red["status"] != "red":
            return False, "sabotage did not flip the dot red"
        esc = surface_mod.open_escalations(trips_path)
        if not any(e["dot"] == about_title["id"] and red["evidence"] in (e.get("evidence") or "")
                  for e in esc):
            return False, "sabotage did not raise an ESCALATE carrying the evidence receipt"

        site.heal("/about")
        for _ in range(watch_certify.CERT_N):
            watch_runner.run_cycle(hm, trips_path=trips_path, skills_dir=skills_dir)

        cards = list((skills_dir / "watch").glob("*.yaml"))
        if len(cards) != len(hm["dots"]):
            return False, (f"only {len(cards)}/{len(hm['dots'])} dots certified after "
                           f"{watch_certify.CERT_N} clean cycles")

        ok, reason = trips_mod.verify_integrity(trips_path)
        if not ok:
            return False, f"watch trip chain broke: {reason}"
        certified = any(r["type"] == "CERTIFIED" for r in trips_mod.read_all(trips_path))
        if not certified:
            return False, "no CERTIFIED trip emitted"

        return True, (f"{len(hm['dots'])} dots compiled from a real crawl, sabotage->red->"
                      f"escalate proven with receipt, all {len(cards)} certified after "
                      f"{watch_certify.CERT_N} clean checks, chain intact")
    finally:
        site.stop()


def check_ui_endpoints_serve() -> tuple[bool, str]:
    tmp = Path(tempfile.mkdtemp(prefix="assure-ui-"))
    skills = tmp / "skills"
    shutil.copytree(REPO_ROOT / "skills", skills)
    trips_path = tmp / "trips.jsonl"
    trips_mod.emit("SLEEP", path=trips_path, note="assure-smoke")
    live_root = tmp / "live"
    live_root.mkdir()

    httpd = ui_mod.serve(host="127.0.0.1", port=0, trips_path=trips_path,
                         skills_dir=skills, live_root=live_root)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.socket.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        codes = {}
        for ep in ("/", "/api/surface", "/api/trips", "/api/manifest", "/api/flights"):
            with urllib.request.urlopen(base + ep, timeout=5) as r:
                codes[ep] = r.status
        ok = all(c == 200 for c in codes.values())
        return ok, f"endpoints -> {codes}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def check_chat_routes_covered_modelless() -> tuple[bool, str]:
    """QUEEN OS: Tab 1's ROUTE FIRST, stub-tested — a message matching a
    known, fully-covered play must never reach the model runner. `_runner`
    is swapped for one that raises, so a regression that accidentally
    falls through to a work order fails loud, not silent."""
    tmp = Path(tempfile.mkdtemp(prefix="assure-chat-"))
    skills = tmp / "skills"
    shutil.copytree(REPO_ROOT / "skills", skills)

    def _refuse(*_a, **_k):
        raise AssertionError("route-first fell through to the model runner")

    out = chat_mod.ask("check the demo workspace", trips_path=tmp / "trips.jsonl",
                       chat_path=tmp / "chat.jsonl", skills_dir=skills,
                       maps_dir=tmp / "maps", _runner=_refuse)
    ok = bool(out.get("chip")) and out["chip"]["kind"] == "free" and out["chip"]["model_calls"] == 0
    return ok, f"chip={out.get('chip')}"


BANNED_JARGON = ["manifest", "predicate", "wilson", "frontier", "trips"]


def check_zero_jargon_across_tabs() -> tuple[bool, str]:
    """PRD: "the existing banned-word test extends to all tabs." The
    static page covers Chat/Run/Memory/Workflows; the Paper tab's prose is
    server-rendered at request time (docs/paper/*.md), so it's re-rendered
    and scanned here too — a regression there would never show up in a
    plain scan of the HTML file alone."""
    page = ui_mod.STATIC_PAGE.read_text(encoding="utf-8").lower()
    paper_text = " ".join(s["html"] for s in paper_mod.payload()["sections"]).lower()
    hits = sorted({w for w in BANNED_JARGON if w in page or w in paper_text})
    ok = not hits
    return ok, ("zero jargon across the page + the paper" if ok
               else f"banned word(s) present: {hits}")


def check_chat_chain_integrity(chat_path: Path = chat_mod.DEFAULT_CHAT_PATH
                               ) -> tuple[bool, str]:
    ok, reason = chat_mod.verify_chat_integrity(chat_path)
    n = len(chat_mod.read_chat(chat_path))
    return ok, (f"{n} chat message(s), full chain verified OK" if ok else f"chain broken: {reason}")


# --------------------------------------------------------------------------- #
# H10 (HARDENING_BRIEF): four new claims growing assure to cover the audit's #
# own P0/P1 hardening — chat proof boundary, SSRF matrix, env isolation,     #
# concurrency. Same law as every check above: re-run the real instrument,   #
# never trust a stored label.                                               #
# --------------------------------------------------------------------------- #

def check_chat_proof_boundary() -> tuple[bool, str]:
    """H1's three regression tests, re-run for real on every assure pass —
    catches a regression here even if the test suite itself never runs."""
    tmp = Path(tempfile.mkdtemp(prefix="assure-chatproof-"))
    skills = tmp / "skills"
    shutil.copytree(REPO_ROOT / "skills", skills)
    seed = tmp / "seed"
    shutil.copytree(REPO_ROOT / "corpus" / "pilot" / "seed-ws", seed)

    def _false_value_runner(workspace, job, *, model, max_turns, timeout_s, trips_path, run_id):
        answer = {"answer": "Yes — 99 items, trust me.", "statement": "source_items.json holds 99",
                  "path": "source_items.json", "predicate": "json_item_count", "value": 99}
        (workspace / "answer.json").write_text(json.dumps(answer))
        return {"ok": True, "subtype": "success", "num_turns": 1, "cost_usd": 0.0}

    out1 = chat_mod.ask("how many items, really", trips_path=tmp / "t1.jsonl",
                        chat_path=tmp / "c1.jsonl", skills_dir=skills, maps_dir=tmp / "maps",
                        seed=seed, _runner=_false_value_runner)
    test1 = "99" not in out1["reply"] and out1["learn_offer"] is None

    contradicting = {"answer": "No, only 3 in there.", "statement": "source_items.json holds 5",
                     "path": "source_items.json", "predicate": "json_item_count", "value": 5}
    rendered = chat_mod._render_checked_reply(contradicting)
    test2 = "3" not in rendered and rendered.startswith("Confirmed")

    def _bad_subtype_runner(workspace, job, *, model, max_turns, timeout_s, trips_path, run_id):
        (workspace / "answer.json").write_text(json.dumps({
            "answer": "5 items.", "statement": "source_items.json holds 5",
            "path": "source_items.json", "predicate": "json_item_count", "value": 5}))
        return {"ok": False, "subtype": "error_max_turns", "num_turns": 20, "cost_usd": 0.0}

    out3 = chat_mod.ask("how many items", trips_path=tmp / "t3.jsonl", chat_path=tmp / "c3.jsonl",
                        skills_dir=skills, maps_dir=tmp / "maps", seed=seed,
                        _runner=_bad_subtype_runner)
    test3 = out3["learn_offer"] is None and "couldn't find" in out3["reply"]

    ok = test1 and test2 and test3
    return ok, (f"false-value blocked={test1} contradiction-filtered={test2} "
               f"subtype-gate={test3}")


_SSRF_TEST_URLS = ("http://localhost/", "http://127.0.0.1/", "http://[::1]/",
                   "http://10.1.2.3/", "http://172.16.0.1/", "http://192.168.1.1/",
                   "http://169.254.169.254/", "http://100.100.100.200/")


def check_ssrf_matrix_green() -> tuple[bool, str]:
    """H3's SafeFetcher, re-run against the same class list the audit named,
    live, every assure pass."""
    blocked = [u for u in _SSRF_TEST_URLS if safefetch.safe_get(u).startswith("ERROR:")]
    ok = len(blocked) == len(_SSRF_TEST_URLS)
    return ok, f"{len(blocked)}/{len(_SSRF_TEST_URLS)} SSRF-class targets refused"


def check_env_isolation() -> tuple[bool, str]:
    """H2's planted-secret test, re-run live: a secret in this process's own
    env must never survive queen/sandbox.py's child-env allowlist."""
    marker = "ASSURE_PLANTED_SECRET"
    os.environ[marker] = "sk-should-never-leak-into-a-child-process"
    try:
        env = sandbox_mod.build_child_env()
    finally:
        del os.environ[marker]
    ok = marker not in env
    return ok, f"planted secret present in child env: {marker in env}"


def _assure_concurrency_worker(path_str: str, n: int, worker: int) -> None:
    """Module-level (not a closure) — multiprocessing needs a picklable
    target on every platform's default start method."""
    path = Path(path_str)
    for i in range(n):
        trips_mod.emit("SLEEP", path=path, worker=worker, i=i)


def check_concurrency_safe_journal() -> tuple[bool, str]:
    """H4's stress test, re-run live at a reduced N so assure stays fast:
    two real OS processes append to the same trips.jsonl; the chain must
    stay linear, unique, complete."""
    tmp = Path(tempfile.mkdtemp(prefix="assure-concurrency-"))
    path = tmp / "trips.jsonl"
    n_per_proc = 100
    procs = [multiprocessing.Process(target=_assure_concurrency_worker, args=(str(path), n_per_proc, w))
            for w in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
    records = trips_mod.read_all(path)
    seqs = sorted(r["seq"] for r in records)
    contiguous = seqs == list(range(1, n_per_proc * 2 + 1))
    chain_ok, chain_reason = trips_mod.verify_integrity(path)
    ok = len(records) == n_per_proc * 2 and contiguous and chain_ok
    return ok, (f"{len(records)}/{n_per_proc * 2} events, contiguous_unique_seq={contiguous}, "
               f"chain={'OK' if chain_ok else chain_reason}")


@dataclass
class Claim:
    n: int
    text: str
    artifact: str
    check: Callable[[], tuple[bool, str]]


def _claims() -> list[Claim]:
    return [
        Claim(1, "Pilot map routes 4/4 covered, $0, zero model calls (run it)",
              "bank/route.py via queen/dispatch.py (pilot preset)", check_pilot_covered),
        Claim(2, "Every certified skill's certificate re-verifies (reprobed, disposable seed)",
              "skills/*.yaml certificates, re-run via bank/certify.py", check_certificates_reverify),
        Claim(3, "Trip chain integrity: full hash-chain re-verification",
              "runs/queen/trips.jsonl", check_trip_chain_integrity),
        Claim(4, "Frozen files unchanged (extractor rubric, certify oracle-gate, *_registration.md)",
              str(FROZEN_HASHES_PATH.relative_to(REPO_ROOT)), check_frozen_files_unchanged),
        Claim(5, "Governor backtest reproduces (p75 + e1c/e1d refog counts match the committed report)",
              "runs/governor-backtest/report.json", check_governor_backtest_reproduces),
        Claim(6, "Harvest idempotence: a sleep tick on a temp copy harvests 0 new",
              "queen/sleep.py + runs/queen-live/*", check_harvest_idempotent),
        Claim(7, "C3 safety: touch() on every certified card leaves method/check bytes hash-identical",
              "queen/reconsolidate.py", check_c3_safety),
        Claim(8, "Efficiency-claim funeral intact: e1d verdict parses and says the claim is dead",
              "runs/e1d-verdict/verdict.json", check_funeral_intact),
        Claim(9, "Work-order gate (Q8): a sabotaged/incomplete DO phase fails closed",
              "queen/workorder.py mechanical_completion_gate", check_work_order_gate_fails_closed),
        Claim(10, "UI endpoints serve (Q10): surface/trips/manifest/flights + index all 200",
              "queen/ui.py", check_ui_endpoints_serve),
        Claim(11, "Watch oracle (point-and-watch): a real crawl compiles >=8 dots, "
                  "sabotage flips one red with an evidence receipt, and 20 consecutive "
                  "clean checks mint a real certificate",
              "watch/runner.py + watch/certify.py -> skills/watch/*.yaml",
              check_watch_oracle),
        Claim(12, "Chat routes covered work modelless (Tab 1's ROUTE FIRST)",
              "queen/chat.py route_first() via bank/route.py", check_chat_routes_covered_modelless),
        Claim(13, "Zero jargon across all five tabs (page + the live-rendered paper)",
              "queen/static/index.html + queen/paper.py -> docs/paper/*.md",
              check_zero_jargon_across_tabs),
        Claim(14, "Chat chain integrity: full hash-chain re-verification",
              "runs/queen/chat.jsonl", check_chat_chain_integrity),
        Claim(15, "Chat proof boundary (H1): false value blocked, contradicting free "
                  "text filtered, subtype!=success fails the work order",
              "queen/chat.py _chat_gate() + _render_checked_reply()", check_chat_proof_boundary),
        Claim(16, "SSRF matrix green (H3): localhost/private/link-local/metadata all refused",
              "net/safefetch.py safe_get()", check_ssrf_matrix_green),
        Claim(17, "Env isolation (H2): a planted secret never reaches the sandboxed child env",
              "queen/sandbox.py build_child_env()", check_env_isolation),
        Claim(18, "Concurrency (H4): two real processes append 200 trips — chain "
                  "stays linear, unique, complete",
              "queen/_journal.py append_locked()", check_concurrency_safe_journal),
    ]


def run_assure() -> dict[str, Any]:
    rows = []
    all_ok = True
    for c in _claims():
        try:
            ok, detail = c.check()
        except Exception as e:  # a check crashing is a FAIL, never a silent skip
            ok, detail = False, f"EXCEPTION: {type(e).__name__}: {e}"
        all_ok = all_ok and ok
        rows.append({"n": c.n, "claim": c.text, "artifact": c.artifact,
                    "passed": ok, "detail": detail})
    return {"pass": all_ok, "rows": rows}


def render(result: dict[str, Any]) -> str:
    lines = []
    for r in result["rows"]:
        mark = "PASS" if r["passed"] else "FAIL"
        lines.append(f"[{mark}] {r['n']:>2}. {r['claim']}")
        lines.append(f"        artifact: {r['artifact']}")
        lines.append(f"        {r['detail']}")
    lines.append("")
    lines.append("ASSURE: " + ("ALL GREEN" if result["pass"] else "FAILED — see rows above"))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--freeze":
        p = generate_frozen_manifest()
        print(f"froze current bytes -> {p}")
        raise SystemExit(0)
    res = run_assure()
    print(render(res))
    raise SystemExit(0 if res["pass"] else 1)

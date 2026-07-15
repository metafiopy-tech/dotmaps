"""dotmaps CLI — the harness entrypoint.

    dotmaps run     <map_dir> --workspace <ws> [--resume] [--verify docker]
                    [--dry-run] [--allow-destructive]
    dotmaps verify  <map_dir> --workspace <ws>     # one full manifest pass, no traveler
    dotmaps board   <workspace>                    # print scoreboard summary
    dotmaps compile <map_dir> --workspace <ws> [--answers a.json] [--yes]
                                                   # intake dialogue -> config + board approval
    dotmaps audit   <workspace>                    # secrets scan; exit 1 on any hit
    dotmaps connect <map_dir>                      # prompt for + verify service tokens
"""

from __future__ import annotations

import argparse
import json
import sys

from .models import Map
from .runtime.orchestrator import Orchestrator
from .safety import audit as audit_mod
from .safety import gates
from .scoreboard.state import Scoreboard
from .verifier.runner import Verifier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dotmaps")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="traverse a map end-to-end")
    p_run.add_argument("map_dir")
    p_run.add_argument("--workspace", required=True)
    p_run.add_argument("--resume", action="store_true")
    p_run.add_argument("--verify", choices=["local", "docker"], default="local")
    p_run.add_argument("--dry-run", action="store_true",
                       help="mock all mutating tool calls; journal intended actions")
    p_run.add_argument("--allow-destructive", action="store_true",
                       help="permit destructive dots without an interactive confirm")
    p_run.add_argument("--driver", choices=["scripted", "llm", "ollama"],
                       help="override the map's traveler driver (the traveler is "
                            "deliberately the most replaceable component)")
    p_run.add_argument("--model", help="override the map's traveler model")

    p_compile = sub.add_parser("compile", help="intake dialogue -> workspace config + board approval")
    p_compile.add_argument("map_dir")
    p_compile.add_argument("--workspace", required=True)
    p_compile.add_argument("--answers", help="JSON file of answers (non-interactive)")
    p_compile.add_argument("--yes", action="store_true",
                           help="approve the board without prompting (scripted use)")

    p_grow = sub.add_parser("grow", help="POKE loop: grow a map from an unknown environment")
    p_grow.add_argument("seed_dir", help="the environment to learn (copied fresh per confirmation)")
    p_grow.add_argument("--run-dir", required=True, help="where the journal, primitives, and grown map land")
    p_grow.add_argument("--model", default="qwen2.5-coder:7b")
    p_grow.add_argument("--learner-driver", choices=["ollama", "anthropic"],
                        default="ollama")
    p_grow.add_argument("--max-pokes", type=int, default=150)
    p_grow.add_argument("--max-spirals", type=int, default=3)

    p_attack = sub.add_parser("attack", help="adversarial certification: try to earn a false green")
    p_attack.add_argument("map_dir")
    p_attack.add_argument("--seed", required=True, help="pristine seed workspace to attack from")

    p_replay = sub.add_parser("replay", help="render a workspace's event log as a readable story")
    p_replay.add_argument("workspace")

    p_readout = sub.add_parser("readout", help="post-hoc R1/R3 readout of a grow run (never in-loop)")
    p_readout.add_argument("run_dir")
    p_readout.add_argument("--seed", required=True)
    p_readout.add_argument("--compare", help="the WITHHELD human map (post-run only)")

    p_connect = sub.add_parser("connect", help="prompt for + verify tokens for the map's external services")
    p_connect.add_argument("map_dir")

    p_audit = sub.add_parser("audit", help="scan a workspace (incl. logs) for leaked secrets")
    p_audit.add_argument("workspace")

    p_probe = sub.add_parser("probe", help="Phase-3 probe: N fresh weak-traveler runs -> certification stats")
    p_probe.add_argument("map_dir")
    p_probe.add_argument("--workspace-base", required=True,
                         help="directory to create the fresh probe workspaces under")
    p_probe.add_argument("--runs", type=int, default=5)
    p_probe.add_argument("--seed", help="directory copied into each fresh workspace (e.g. a compiled config)")
    p_probe.add_argument("--driver", choices=["scripted", "llm", "ollama"])
    p_probe.add_argument("--model")
    p_probe.add_argument("--verify", choices=["local", "docker"], default="local")

    p_corpus = sub.add_parser("corpus", help="experiment: build a degraded/enriched map variant from a recipe")
    p_corpus.add_argument("recipe", help="variant recipe YAML")
    p_corpus.add_argument("--out", required=True, help="output directory for the variant map repo")
    p_corpus.add_argument("--no-check", action="store_true",
                          help="skip the verifier-can-fail integrity check")

    p_ver = sub.add_parser("verify", help="run the full manifest once (no traveler)")
    p_ver.add_argument("map_dir")
    p_ver.add_argument("--workspace", required=True)
    p_ver.add_argument("--verify", choices=["local", "docker"], default="local")

    p_board = sub.add_parser("board", help="print the scoreboard summary")
    p_board.add_argument("workspace")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        m = Map.load(args.map_dir)
        if args.driver or args.model:
            import dataclasses
            traveler = dataclasses.replace(
                m.traveler,
                driver=args.driver or m.traveler.driver,
                model=args.model or m.traveler.model,
            )
            m = dataclasses.replace(m, traveler=traveler)
        gate_config = gates.GateConfig(
            dry_run=args.dry_run,
            allow_destructive=args.allow_destructive,
            confirm=(_cli_confirm if sys.stdin.isatty() and not args.allow_destructive
                     and not args.dry_run else None),
        )
        board = Orchestrator(m, args.workspace, verify_mode=args.verify,
                             dry_run=args.dry_run, gate_config=gate_config,
                             ).run(resume=args.resume)
        print(json.dumps(board.summary(m), indent=2))
        return 0 if board.ended == "all_green" else 1

    if args.cmd == "compile":
        from .compiler.intake import Question, compile_map
        m = Map.load(args.map_dir)
        answers = None
        if args.answers:
            with open(args.answers) as f:
                answers = json.load(f)
        def _ask(q: Question) -> str:
            print(f"\n{q.prompt}")
            print(f"  ({q.why})")
            suffix = f" [{q.default}]" if q.default is not None else ""
            return input(f"> {suffix} ").strip()
        def _approve(board_text: str) -> bool:
            print("\n" + board_text + "\n")
            if args.yes:
                print("[--yes] board approved")
                return True
            return input("Approve this board and fog? (yes/no) > ").strip().lower() in ("y", "yes")
        out = compile_map(m, args.workspace,
                          answers=answers,
                          ask=None if answers is not None else _ask,
                          approve=_approve)
        print(f"\nwrote {out}")
        return 0

    if args.cmd == "probe":
        from .certify import probe, write_artifact
        m = Map.load(args.map_dir)
        if args.driver or args.model:
            import dataclasses
            traveler = dataclasses.replace(
                m.traveler,
                driver=args.driver or m.traveler.driver,
                model=args.model or m.traveler.model,
            )
            m = dataclasses.replace(m, traveler=traveler)
        stats = probe(m, args.workspace_base, runs=args.runs,
                      seed_dir=args.seed, verify_mode=args.verify)
        out = write_artifact(m, stats)
        verdict = "CERTIFIED" if stats["certified"] else "NOT certified"
        print(f"{stats['all_green']}/{stats['runs']} all-green (need {stats['required']}) — {verdict}")
        print(f"stats -> {out}")
        return 0 if stats["certified"] else 1

    if args.cmd == "corpus":
        import tempfile
        from .corpus import build_variant, verifier_can_fail
        out = build_variant(args.recipe, args.out)
        variant = json.loads((out / "variant.json").read_text())
        print(f"built variant {variant['name']} (tier {variant['tier']}, "
              f"{variant['dot_count']} dots) -> {out}")
        if not args.no_check:
            # integrity: every non-tautology verifier must FAIL on a broken workspace
            broken = tempfile.mkdtemp(prefix="dotmaps-broken-")
            taut = set(variant["tautologized_dots"])
            weak = []
            for d in Map.load(out).dots:
                if d.id in taut:
                    continue
                if not verifier_can_fail(out, d.id, broken):
                    weak.append(d.id)
            if weak:
                print(f"INTEGRITY FAIL: verifiers passed on a broken workspace: {weak}")
                return 1
            print(f"integrity: all {variant['dot_count'] - len(taut)} non-tautology "
                  f"verifiers correctly fail on a broken workspace")
        return 0

    if args.cmd == "grow":
        from .grow.clock import ClockConfig
        from .grow.learner import AnthropicLearner, OllamaLearner
        from .grow.runner import grow
        cfg = ClockConfig(max_pokes=args.max_pokes, max_spirals=args.max_spirals)
        if args.learner_driver == "anthropic":
            learner = AnthropicLearner(model=args.model)
        else:
            learner = OllamaLearner(model=args.model)
        summary = grow(args.seed_dir, args.run_dir, learner, cfg=cfg)
        if hasattr(learner, "usd_estimate"):
            summary["learner_usd_estimate"] = round(learner.usd_estimate, 4)
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("grown_map") else 1

    if args.cmd == "attack":
        from .certificate.attack import run_attacks
        report = run_attacks(args.map_dir, args.seed)
        print(json.dumps(report, indent=2))
        return 0 if report["verdict"] == "HARDENED" else 1

    if args.cmd == "replay":
        from .scoreboard.replay import replay as _replay
        _replay(args.workspace)
        return 0

    if args.cmd == "readout":
        from .grow.readout import readout
        out = readout(args.run_dir, args.seed, args.compare)
        print(json.dumps(out, indent=2))
        return 0 if out.get("r1", {}).get("passed") else 1

    if args.cmd == "connect":
        from .connect import connect_map
        return connect_map(Map.load(args.map_dir))

    if args.cmd == "audit":
        findings = audit_mod.scan_workspace(args.workspace)
        if not findings:
            print("secrets audit: clean (0 hits)")
            return 0
        print(f"secrets audit: {len(findings)} hit(s) — FAILED")
        for f in findings:
            print(f"  {f.path}:{f.line}  [{f.kind}]  {f.excerpt}")
        return 1

    if args.cmd == "verify":
        m = Map.load(args.map_dir)
        results = Verifier.for_map(m, mode=args.verify).run_full_manifest(m, args.workspace)
        for r in results:
            mark = "PASS" if r.passed else ("ERR " if r.errored else "FAIL")
            print(f"[{mark}] {r.dot}  {r.evidence}")
        return 0 if all(r.passed for r in results) else 1

    if args.cmd == "board":
        board = Scoreboard.load_or_init(args.workspace)
        print(json.dumps(board.summary(), indent=2))
        return 0

    return 2


def _cli_confirm(dot) -> bool:
    """The explicit human-confirm pause for a destructive dot (spec §4.3)."""
    print(f"\n⚠ destructive dot {dot.id}: {dot.statement}")
    return input("Proceed with this action? (yes/no) > ").strip().lower() in ("y", "yes")


if __name__ == "__main__":
    sys.exit(main())

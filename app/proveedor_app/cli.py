"""`pa-app` command line: serve the app, generate fixtures, evaluate the DoD."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path

from . import dod, fixtures
from .gold import GoldStore, LocalSource, load_store

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_DIR = REPO_ROOT / ".cache" / "fixtures"


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    if args.fixtures:
        lake = fixtures.generate(FIXTURE_DIR)
        os.environ["PA_GOLD_DIR"] = str(lake)
        os.environ["PA_CASE_DIR"] = str(FIXTURE_DIR / "case")
    if args.role:
        os.environ["PA_ROLE"] = args.role
    if args.gold_dir:
        os.environ["PA_GOLD_DIR"] = args.gold_dir
    if args.run_id:
        os.environ["PA_RUN_ID"] = args.run_id
    from .web import create_app

    app = create_app()
    if args.replay is not None:
        from .live import Replayer

        root = os.environ.get("PA_GOLD_DIR")
        if not root:
            raise SystemExit("--replay needs a local lake: --fixtures, --gold-dir or PA_GOLD_DIR")
        replayer = Replayer(Path(root), args.replay or None, duration=args.duration, speed=args.speed)
        pace = f"at {args.speed:g}x" if args.speed else f"over {args.duration:.0f}s"
        print(f"replaying {replayer.run.run_id} as live run {replayer.new_run_id} {pace}")
        threading.Timer(args.delay, replayer.start).start()
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _fixtures(args: argparse.Namespace) -> int:
    lake = fixtures.generate(Path(args.out), n_suppliers=args.suppliers)
    print(f"PA_GOLD_DIR={lake}")
    print(f"PA_CASE_DIR={Path(args.out) / 'case'}")
    return 0


def _replay(args: argparse.Namespace) -> int:
    from .live import Replayer

    root = Path(args.lake)
    if args.fixtures:
        root = fixtures.generate(FIXTURE_DIR)
    replayer = Replayer(root, args.run_id, target_root=Path(args.to) if args.to else None, duration=args.duration,
                        speed=args.speed, new_run_id=args.new_run_id)
    print(f"replaying {replayer.run.run_id} -> {replayer.new_run_id} in {replayer.target} over {args.duration:.0f}s")
    replayer.play()
    print(f"done: runs/{replayer.case_id}/{replayer.new_run_id}")
    return 0


def _snapshot(args: argparse.Namespace) -> int:
    from .snapshot import snapshot

    store = GoldStore(LocalSource(args.gold_dir)) if args.gold_dir else load_store(REPO_ROOT)
    report = snapshot(store, args.run_id, Path(args.out))
    print(json.dumps(report))
    print(f"serve it: uv run pa-app serve --gold-dir {args.out}")
    print(f"replay it: uv run pa-app serve --gold-dir {args.out} --replay {report['run_id']} --duration 60")
    return 1 if report["missing_bronze"] else 0


def _dod(args: argparse.Namespace) -> int:
    store = GoldStore(LocalSource(args.gold_dir)) if args.gold_dir else load_store(REPO_ROOT)
    run = store.run(args.run_id)
    recomputed = dod.compute(run.suppliers)
    problems = dod.cross_check(recomputed, run.metrics)
    backend = run.inference_backend
    met = dod.dod_met(recomputed, backend)
    report = {"case_id": store.case_id, "run_id": run.run_id, "inference_backend": backend, "recomputed": recomputed,
              "dod_met": met, "mismatches": problems}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"run {run.run_id} ({store.case_id}), inference backend: {backend or 'not stated'}")
        if backend == "recorded":
            print("  NOT DONE: this run used recorded (simulated) inference; it cannot satisfy the DoD")
        for key in dod.DOD_KEYS:
            target = dod.TARGETS.get(key)
            if target is None:
                mark = ""
            elif backend == "recorded":
                mark = "  not counted (recorded inference)"
            elif met[key]:
                mark = "  ok"
            else:
                mark = f"  target {target} not met"
            print(f"  {key:30} {recomputed[key]}{mark}")
        for name, ratio in recomputed["per_field_completeness"].items():
            print(f"  completeness.{name:19} {ratio:.1%}")
        print("  cross-check vs engine metrics.json: " + ("match" if not problems else "MISMATCH"))
        for p in problems:
            print(f"    - {p}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pa-app")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("serve", help="run the investigation app")
    p.add_argument("--fixtures", action="store_true", help="generate and serve the synthetic fixture export")
    p.add_argument("--role", choices=("investigator", "approver"))
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8400)
    p.add_argument("--gold-dir", help="local lake root (bucket layout); same as PA_GOLD_DIR")
    p.add_argument("--run-id", help="serve this run even if latest.json points elsewhere or is absent (PA_RUN_ID)")
    p.add_argument("--replay", nargs="?", const="", metavar="RUN_ID",
                   help="also replay a finished run (default: latest gold run) as a live run in the same local lake")
    p.add_argument("--duration", type=float, default=45.0, help="replay length in seconds (default 45)")
    p.add_argument("--speed", type=float, help="replay at N x the recorded pace instead of --duration")
    p.add_argument("--delay", type=float, default=2.0, help="seconds before the replay starts")
    p.set_defaults(fn=_serve)

    p = sub.add_parser("replay", help="replay a finished run into the live feed (rehearsal, demo insurance)")
    p.add_argument("lake", nargs="?", default=str(FIXTURE_DIR / "lake"), help="local lake root holding the run")
    p.add_argument("--fixtures", action="store_true", help="regenerate the synthetic fixtures first")
    p.add_argument("--run-id", help="run to replay (default: latest gold run)")
    p.add_argument("--to", help="target lake root (default: the same lake)")
    p.add_argument("--new-run-id")
    p.add_argument("--duration", type=float, default=45.0)
    p.add_argument("--speed", type=float, help="replay at N x the recorded pace instead of --duration")
    p.set_defaults(fn=_replay)

    p = sub.add_parser("snapshot", help="cache one run (gold, live feed, referenced bronze) into a local folder")
    p.add_argument("out", help="target folder (bucket layout)")
    p.add_argument("--gold-dir", help="source local lake (default: PA_GOLD_DIR or lake.yaml, S3 included)")
    p.add_argument("--run-id", help="run to cache (default: latest gold run)")
    p.set_defaults(fn=_snapshot)

    p = sub.add_parser("fixtures", help="write a synthetic gold export + case package")
    p.add_argument("out", nargs="?", default=str(FIXTURE_DIR))
    p.add_argument("--suppliers", type=int, default=60)
    p.set_defaults(fn=_fixtures)

    p = sub.add_parser("dod", help="recompute the DoD keys from gold and cross-check metrics.json")
    p.add_argument("--gold-dir", help="local export root (default: PA_GOLD_DIR or lake.yaml)")
    p.add_argument("--run-id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_dod)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

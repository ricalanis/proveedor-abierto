"""`pa-app` command line: serve the app, generate fixtures, evaluate the DoD."""

from __future__ import annotations

import argparse
import json
import os
import sys
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
    from .web import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def _fixtures(args: argparse.Namespace) -> int:
    lake = fixtures.generate(Path(args.out), n_suppliers=args.suppliers)
    print(f"PA_GOLD_DIR={lake}")
    print(f"PA_CASE_DIR={Path(args.out) / 'case'}")
    return 0


def _dod(args: argparse.Namespace) -> int:
    store = GoldStore(LocalSource(args.gold_dir)) if args.gold_dir else load_store(REPO_ROOT)
    run = store.run(args.run_id)
    recomputed = dod.compute(run.suppliers)
    problems = dod.cross_check(recomputed, run.metrics)
    met = dod.dod_met(recomputed)
    report = {"case_id": store.case_id, "run_id": run.run_id, "recomputed": recomputed, "dod_met": met,
              "mismatches": problems}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"run {run.run_id} ({store.case_id})")
        for key in dod.DOD_KEYS:
            target = dod.TARGETS.get(key)
            mark = "" if target is None else ("  ok" if met[key] else f"  below target {target}")
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
    p.set_defaults(fn=_serve)

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

"""`pa-app` command line: serve the site, generate fixtures, evaluate the DoD."""

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
    if args.gold_dir:
        os.environ["PA_GOLD_DIR"] = args.gold_dir
    if args.run_id:
        os.environ["PA_RUN_ID"] = args.run_id
    from .web import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def _fixtures(args: argparse.Namespace) -> int:
    if args.domain == "libraries":
        from . import fixture_libraries

        lake = fixture_libraries.generate(Path(args.out))
    else:
        lake = fixtures.generate(Path(args.out), n_suppliers=args.suppliers, layout=args.layout)
    print(f"PA_GOLD_DIR={lake}")
    print(f"PA_CASE_DIR={Path(args.out) / 'case'}")
    return 0


def _screens(args: argparse.Namespace) -> int:
    from datetime import UTC, datetime

    from . import screens

    product, console = args.product, args.console
    if not product and not console:
        raise SystemExit("give --product and/or --console (the services' mesh addresses; the kit never signs in)")
    out = Path(args.out) if args.out else REPO_ROOT / "docs" / "evidence" / "screens" / datetime.now(UTC).strftime("%Y-%m-%d")
    m = screens.capture(out, product=product, console=console, targets=args.target, only=args.only)
    bad = [f for f in m["files"] if f["status"] and f["status"] >= 400]
    print(f"{len(m['files'])} screenshots in {out} · {m['redactions']} redactions · {len(bad)} non-200 pages")
    return 1 if bad else 0


def _dod(args: argparse.Namespace) -> int:
    store = GoldStore(LocalSource(args.gold_dir)) if args.gold_dir else load_store(REPO_ROOT)
    run = store.run(args.run_id)
    recomputed = dod.compute(run.entities, run.domain)
    problems = dod.cross_check(recomputed, run.metrics, run.domain)
    backend = run.inference_backend
    rows = dod.criteria(recomputed, run.metrics, run.domain, backend, run.dod_queries, run.entities)
    report = {"case_id": store.case_id, "run_id": run.run_id, "layout": run.layout,
              "primary_class": run.domain.primary_class, "inference_backend": backend, "recomputed": recomputed,
              "criteria": rows, "mismatches": problems}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        cls = run.domain.primary_class
        print(f"run {run.run_id} ({store.case_id}), primary class {cls}, layout {run.layout}, "
              f"inference backend: {backend or 'not stated'}")
        if backend == "recorded":
            print("  NOT DONE: this run used recorded (simulated) inference; it cannot satisfy the DoD")
        for row in rows:
            state = "not counted (recorded inference)" if row["mock"] else ("met" if row["met"] else "not met")
            actual = row["actual"] if row["recomputed"] else f"{row['engine_actual']} (engine; not recomputed)"
            print(f"  {row['criterion_id']:28} {actual} vs target {row['target']}  {state}")
        for prop, ratio in recomputed["per_property_completeness"][cls].items():
            print(f"  completeness.{prop:19} {ratio:.1%}")
        print("  cross-check vs engine metrics.json: " + ("match" if not problems else "MISMATCH"))
        for p in problems:
            print(f"    - {p}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pa-app")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("serve", help="run the Proveedor Abierto site")
    p.add_argument("--fixtures", action="store_true", help="generate and serve the synthetic fixture export")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8400)
    p.add_argument("--gold-dir", help="local lake root (bucket layout); same as PA_GOLD_DIR")
    p.add_argument("--run-id", help="serve this run even if latest.json points elsewhere or is absent (PA_RUN_ID)")
    p.set_defaults(fn=_serve)

    p = sub.add_parser("fixtures", help="write a synthetic gold export + case package")
    p.add_argument("out", nargs="?", default=str(FIXTURE_DIR))
    p.add_argument("--suppliers", type=int, default=60)
    p.add_argument("--domain", choices=("procurement", "libraries"), default="procurement",
                   help="libraries: a second, unrelated domain for the genericity proof")
    p.add_argument("--layout", choices=("entities", "legacy"), default="entities",
                   help="legacy: the pre-§11 suppliers.jsonl/contracts.jsonl export the adapter reads")
    p.set_defaults(fn=_fixtures)

    p = sub.add_parser("screens", help="capture the demo screenshots (product + console) at 1280/390, light and dark")
    p.add_argument("--product", default=os.environ.get("PA_SCREENS_PRODUCT"),
                   help="product base URL, e.g. the service's mesh address (env PA_SCREENS_PRODUCT)")
    p.add_argument("--console", default=os.environ.get("PA_SCREENS_CONSOLE"),
                   help="console base URL, e.g. the service's mesh address (env PA_SCREENS_CONSOLE)")
    p.add_argument("--target", action="append", default=[], help="console case[:run] (repeatable; default library-demo)")
    p.add_argument("--only", choices=("product", "console"))
    p.add_argument("--out", default=None, help="output folder (default docs/evidence/screens/<UTC date>)")
    p.set_defaults(fn=_screens)

    p = sub.add_parser("dod", help="recompute the DoD keys from gold and cross-check metrics.json")
    p.add_argument("--gold-dir", help="local export root (default: PA_GOLD_DIR or lake.yaml)")
    p.add_argument("--run-id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_dod)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

"""Timed rehearsal of docs/demo/demo-script.md on synthetic fixtures (no engine, no network).

    uv run python docs/demo/rehearse.py [--out .cache/rehearsal] [--no-pauses]

Starts the product (this app) on synthetic fixtures and walks the product beats (discovery, the output, the close)
in a headless browser. The engine and generic beats run in a terminal, and the approval, run-view and containment
beats are the Ontofill Console's (a separate product behind its own SSO URL): here they are narration pauses sized
to their budget, and they are rehearsed by hand on the console. Records a video plus a timing table (budget vs
actual). Exit code 1 if a product beat fails or the total exceeds 3:00.
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

from proveedor_app import fixtures
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app

# (beat, budget seconds) from demo-script.md
# Brief 08 order: the engine first (terminal beats, narration only here), then Proveedor Abierto as its test case.
# "(terminal)" and "(console)" beats are narration pauses here; the product beats are driven in the browser.
BUDGET = [("The engine + generic by construction (terminal)", 35), ("Test case: brief -> PRD (console)", 15),
          ("Ontology + gate (console)", 15), ("Discovery", 15), ("Execution: Pattern B + A (console)", 35),
          ("Containment (console)", 30), ("The output: dossier, signal, trace", 20), ("Close: zero ports + repos", 15)]


def serve(app, port: int) -> uvicorn.Server:
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server


def free_port(preferred: int) -> int:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / ".cache" / "rehearsal"))
    ap.add_argument("--replay-seconds", type=float, default=0.0, help="ignored: replay is the console's now")
    ap.add_argument("--no-pauses", action="store_true", help="skip narration pauses (smoke run)")
    args = ap.parse_args()

    out = Path(args.out)
    shutil.rmtree(out, ignore_errors=True)
    lake = fixtures.generate(out / "fixtures")
    case = out / "case-scratch"  # a copy; the product only reads it
    shutil.copytree(out / "fixtures" / "case", case)
    store = GoldStore(LocalSource(lake))
    inv_port = free_port(8420)
    servers = [serve(create_app(Settings(store=store, case_dir=case)), inv_port)]
    inv = f"http://127.0.0.1:{inv_port}"
    rows: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, record_video_dir=str(out / "video"),
                                  record_video_size={"width": 1440, "height": 900})
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def beat(name: str, budget: int, actions) -> None:
            t0 = time.monotonic()
            ok, note = True, ""
            try:
                actions()
            except Exception as exc:  # noqa: BLE001 - a failed beat is reported, the rehearsal continues
                ok, note = False, f"{type(exc).__name__}: {exc}"[:160]
            spent = time.monotonic() - t0
            if not args.no_pauses and spent < budget:
                page.wait_for_timeout(int((budget - spent) * 1000))  # narration time
            rows.append({"beat": name, "budget_s": budget, "app_s": round(spent, 1),
                         "total_s": round(time.monotonic() - t0, 1), "ok": ok, "note": note})

        def narration():  # a terminal or console beat: rehearse it by hand; here it is timed talk only
            pass

        def sources():
            page.goto(f"{inv}/journal?lang=en")
            page.click("a[href*='04-local']")
            page.wait_for_selector("pre.record")

        def visit(path: str, needle: str | None = None) -> None:
            resp = page.goto(f"{inv}{path}{'&' if '?' in path else '?'}lang=en")
            if resp is None or resp.status != 200:
                raise AssertionError(f"{path} -> {resp.status if resp else 'no response'}")
            if needle and needle not in page.content():
                raise AssertionError(f"{path}: {needle!r} not on the page")

        def output():  # dossier with receipts, a signal with its dispute path, a value traced back to the brief
            visit("/entities/sup:fixture-005", "founding")
            visit("/signals", "Dispute")
            visit("/journal/val:0001-005-founding_date", "brief")

        def close():  # an open export downloads
            with page.expect_download() as dl:
                try:
                    page.goto(f"{inv}/export/ocds.json?lang=en")
                except Exception as exc:
                    if "Download is starting" not in str(exc):
                        raise
            if not dl.value.suggested_filename.endswith(".json"):
                raise AssertionError("OCDS export did not download")

        beats = (narration, narration, narration, sources, narration, narration, output, close)
        for (name, budget), fn in zip(BUDGET, beats, strict=True):
            beat(name, budget, fn)
        video = page.video.path() if page.video else None
        ctx.close()
        browser.close()

    for s in servers:
        s.should_exit = True
    total = sum(r["total_s"] for r in rows)
    report = {"beats": rows, "total_s": round(total, 1), "page_errors": errors, "video": str(video)}
    (out / "timing.json").write_text(json.dumps(report, indent=2))
    print(f"{'beat':28} {'budget':>6} {'app':>6} {'total':>6}  ok")
    for r in rows:
        print(f"{r['beat']:28} {r['budget_s']:>6} {r['app_s']:>6} {r['total_s']:>6}  {'yes' if r['ok'] else 'NO ' + r['note']}")
    print(f"{'TOTAL':28} {sum(b for _, b in BUDGET):>6} {'':>6} {total:>6}")
    print(f"video: {video}\nerrors: {errors or 'none'}")
    return 0 if all(r["ok"] for r in rows) and total <= 185 and not errors else 1


if __name__ == "__main__":
    sys.exit(main())

"""Timed rehearsal of docs/demo/demo-script.md against the replay (no engine, no network).

    uv run python docs/demo/rehearse.py [--out .cache/rehearsal] [--replay-seconds 45] [--no-pauses]

Starts two app processes on synthetic fixtures (investigator :8410, approver :8411, approver writing only to a
scratch copy of the fixture case), replays the fixture run into the live feed during the execution beat, walks
every beat in a headless browser with a narration pause sized to the beat's budget, and records a video plus
a timing table (budget vs actual). Exit code 1 if a beat fails or the total exceeds 3:00.
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
from proveedor_app.live import Replayer
from proveedor_app.web import Settings, create_app

# (beat, budget seconds) from demo-script.md
# Brief 08 order: the engine first (terminal beats, narration only here), then Proveedor Abierto as its test case.
BUDGET = [("The engine + generic by construction (terminal)", 35), ("Test case: brief -> PRD", 15),
          ("Ontology + gate", 15), ("Discovery", 15), ("Execution: Pattern B + A", 35), ("Containment", 30),
          ("The output: dossier, signal, trace", 20), ("Close: zero ports + repos", 15)]


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
    ap.add_argument("--replay-seconds", type=float, default=40.0)
    ap.add_argument("--no-pauses", action="store_true", help="skip narration pauses (smoke run)")
    args = ap.parse_args()

    out = Path(args.out)
    shutil.rmtree(out, ignore_errors=True)
    lake = fixtures.generate(out / "fixtures")
    case = out / "case-scratch"  # the approver writes APPROVED here, never in the tracked case/
    shutil.copytree(out / "fixtures" / "case", case)
    store = GoldStore(LocalSource(lake))
    inv_port, app_port = free_port(8410), free_port(8411)
    servers = [serve(create_app(Settings(store=store, case_dir=case, role="investigator")), inv_port),
               serve(create_app(Settings(store=store, case_dir=case, role="approver")), app_port)]
    inv, apr = f"http://127.0.0.1:{inv_port}", f"http://127.0.0.1:{app_port}"
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

        def engine_intro():  # architecture frame and two briefs / two ontologies live in the terminal
            page.goto(f"{inv}/engine")

        def prd():
            page.goto(f"{apr}/approvals")
            page.click("text=Global PRD")
            page.wait_for_selector("text=Definition of done")
            page.fill("#approver", "Rehearsal Approver")
            page.click("button:has-text('Approve the PRD')")
            page.wait_for_selector("text=Approved 01-scope")

        def ontology():
            page.goto(f"{apr}/approvals/02-ontology/factors")
            page.check("input[name='decision.buyer_level'][value='reject']")
            page.fill("#approver", "Rehearsal Approver")
            page.click("button:has-text('Approve the accepted factors')")
            page.wait_for_selector("text=Approved 02-ontology/factors")
            page.goto(f"{apr}/approvals/02-ontology")
            page.wait_for_selector("text=Soundness")
            page.fill("#approver", "Rehearsal Approver")
            page.click("button:has-text('Approve the ontology')")
            page.wait_for_selector("text=Approved 02-ontology")

        def sources():
            page.goto(f"{inv}/journal")
            page.click("a[href*='04-local']")
            page.wait_for_selector("pre.record")

        replayer = Replayer(lake, "run-fixture-0001", duration=args.replay_seconds, new_run_id="rehearsal-live")

        def execution():
            replayer.start()
            page.wait_for_timeout(1500)
            page.goto(f"{inv}/run/rehearsal-live")
            page.wait_for_function("document.querySelectorAll('#steps li').length > 20", timeout=20_000)

        def containment():
            page.wait_for_function("document.getElementById('run-state').textContent.trim() === 'done'",
                                   timeout=int(args.replay_seconds * 1000) + 20_000)
            page.goto(f"{inv}/run/rehearsal-live?limit=2000")  # the whole trail, not the latest 150 steps
            if not page.locator("#steps li.step--quarantine").count():
                raise AssertionError("no quarantined hostile page in the step stream")
            page.locator("#proof-h").scroll_into_view_if_needed()
            if "BLOCKED" not in page.locator("#proof").inner_text():
                raise AssertionError("sandbox proof shows no BLOCKED probe")

        def output():
            page.goto(f"{inv}/suppliers/sup:fixture-005")
            page.click("a.ev-link[data-evidence$='founding_date']")
            page.wait_for_selector("#evidence-panel a.source-link")
            page.click(".signal a.signal__label >> nth=0")
            page.wait_for_selector("text=Dispute this signal")
            page.goto(f"{inv}/suppliers/sup:fixture-005?ev=val:0001-005-founding_date#evidence")
            page.click("text=Trace this value to the brief")
            page.wait_for_selector(".stop--anchor")
            page.locator(".stop--anchor").last.scroll_into_view_if_needed()

        def close():
            with page.expect_download() as dl:
                page.goto(f"{inv}/watchlist?ids=sup:fixture-005")
                page.click("a:has-text('OCDS JSON') >> nth=0")
            if not dl.value.suggested_filename.endswith(".json"):
                raise AssertionError("OCDS export did not download")

        beats = (engine_intro, prd, ontology, sources, execution, containment, output, close)
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

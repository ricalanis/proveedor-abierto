"""Live run view (CONTRACT 4b), sandbox proof (section 8), replay (P6) and simulated-inference handling (section 7)."""

import json
import shutil
import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient
from proveedor_app import dod, live
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app


@pytest.fixture
def lake(fixture_root, tmp_path):
    dst = tmp_path / "lake"
    shutil.copytree(fixture_root / "lake", dst)
    return dst


def _client(lake, case_dir):
    return TestClient(create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=case_dir)))


def test_annotate_events():
    steps = [
        {"step_id": "a", "phase": 5, "mode": "S1", "evaluated": "failed check; escalate", "value_ids": []},
        {"step_id": "b", "phase": 5, "mode": "S2", "parent_step_id": "a", "evaluated": "ok", "value_ids": ["v"]},
        {"step_id": "c", "phase": 5, "mode": "D1", "executed": "code.promote macro", "evaluated": "crystallized"},
        {"step_id": "d", "phase": 5, "mode": "S1", "evaluated": "ok", "event": "hard_stop"},
        {"step_id": "e", "phase": 5, "mode": "S2", "parent_step_id": "a", "evaluated": "ok", "event": None},
    ]
    events = [s["event"] for s in live.annotate(steps)]
    assert events == ["failure", "escalation", "crystallization", "hard_stop", None]  # explicit null wins


def test_proof_states():
    job = {"job_id": "j", "checkpoints": {"host": {"ok": True}, "task": {"ok": True}, "where": {"ok": True},
                                          "isolation": {"probes": [{"probe": "x", "result": "ALLOWED"}]}}}
    pr = live.proof([job])
    assert pr["counts"]["isolation"]["fail"] == 1 and pr["counts"]["teardown"]["pending"] == 1


def test_recorded_fixture_feed_renders(lake, fixture_root):
    c = _client(lake, fixture_root / "case")
    r = c.get("/run", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/run/run-fixture-0001"
    page = c.get("/run/run-fixture-0001")
    assert page.status_code == 200
    for needle in ("Sandbox proof", "Crystallized", "Escalations", "BLOCKED", "Synthetic fixture data"):
        assert needle in page.text
    data = c.get("/api/run/run-fixture-0001", params={"after": 10}).json()
    assert data["count"] > 10 and data["state"] == "done" and "step" in data["steps_html"]
    assert c.get("/run/nope").status_code == 404


def test_replay_writes_feed_and_publishes_gold(lake):
    rep = live.Replayer(lake, "run-fixture-0001", duration=0.0, new_run_id="rehearsal-1")
    rep.play(sleep=lambda s: None)
    store = GoldStore(LocalSource(lake))
    assert store.live_run_id() == "rehearsal-1"
    status = store.live_status("rehearsal-1")
    assert status["state"] == "done" and status["metrics"]["suppliers_total"] == 60
    assert len(store.live_steps("rehearsal-1")) == len(store.run("run-fixture-0001").trace)
    jobs = store.live_jobs("rehearsal-1")
    assert jobs and all(live.checkpoint_state(j, "teardown") == "pass" for j in jobs)
    assert store.latest_run_id() == "rehearsal-1"
    assert store.run().metrics["run_id"] == "rehearsal-1"


def test_simulated_inference_banner_and_dod(lake, fixture_root):
    run_dir = lake / "gold" / "fixture-case" / "run-fixture-0001"
    metrics = json.loads((run_dir / "metrics.json").read_text())
    metrics["inference_backend"] = "recorded"
    (run_dir / "metrics.json").write_text(json.dumps(metrics))
    c = _client(lake, fixture_root / "case")
    assert "Simulated inference." in c.get("/").text
    page = c.get("/completeness").text
    assert "Simulated inference." in page and "✓" not in page.split("dod__grid")[1].split("</dl>")[0]
    assert all(v is False for v in dod.dod_met(metrics, "recorded").values())
    status = json.loads((lake / "runs/fixture-case/run-fixture-0001/status.json").read_text())
    status["generated_by"] = {"backend": "recorded", "model": "double", "at": "2026-09-26T18:00:00Z"}
    (lake / "runs/fixture-case/run-fixture-0001/status.json").write_text(json.dumps(status))
    assert "Simulated inference." in c.get("/run/run-fixture-0001").text


def test_value_level_recorded_tag(lake, fixture_root):
    path = lake / "gold" / "fixture-case" / "run-fixture-0001" / "suppliers.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["fields"]["address"]["generated_by"] = {"backend": "recorded", "model": "double", "at": "2026-09-26"}
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    c = _client(lake, fixture_root / "case")
    frag = c.get(f"/fragments/evidence/{rows[0]['fields']['address']['value_id']}").text
    assert "Simulated inference" in frag
    assert "Simulated inference." in c.get("/").text  # one recorded value marks the whole run


@pytest.mark.ui
def test_browser_sees_live_updates(lake, fixture_root):
    sync_api = pytest.importorskip("playwright.sync_api")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    rep = live.Replayer(lake, "run-fixture-0001", duration=6.0, new_run_id="rehearsal-ui")
    # Seed an empty live run so the page exists before the replay starts.
    run_dir = lake / "runs" / "fixture-case" / "rehearsal-ui"
    run_dir.mkdir(parents=True)
    (run_dir / "trace.live.jsonl").write_text("")
    (run_dir / "status.json").write_text(json.dumps({"run_id": "rehearsal-ui", "state": "running", "phase": 1}))
    app = create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=fixture_root / "case"))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/run/rehearsal-ui")
            assert pg.locator("#steps li").count() == 0
            rep.start()
            pg.wait_for_function("document.querySelectorAll('#steps li').length > 20", timeout=10_000)
            bar = pg.locator('[data-k="bar-legal_name"]')
            first = bar.get_attribute("style")
            pg.wait_for_function("document.getElementById('run-state').textContent.trim() === 'done'", timeout=15_000)
            assert bar.get_attribute("style") != first  # the same element was updated in place
            assert pg.locator('[data-k="sup-total"]').inner_text() == "60"
            assert "BLOCKED" in pg.locator("#proof").inner_text()
            b.close()
    finally:
        rep.stop()
        server.should_exit = True


def test_replay_output_matches_engine_schemas(lake, validator_for):
    live.Replayer(lake, "run-fixture-0001", duration=0.0, new_run_id="rehearsal-schema").play(sleep=lambda s: None)
    run_dir = lake / "runs" / "fixture-case" / "rehearsal-schema"
    errors = list(validator_for("run-status.schema.json").iter_errors(json.loads((run_dir / "status.json").read_text())))
    assert not errors, [e.message for e in errors][:3]
    step_validator = validator_for("trace-step.schema.json")
    for line in (run_dir / "trace.live.jsonl").read_text().splitlines()[:50]:
        assert not list(step_validator.iter_errors(json.loads(line)))


def test_snapshot_then_replay_offline(lake, tmp_path, fixture_root):
    from proveedor_app.snapshot import snapshot

    out = tmp_path / "snap"
    report = snapshot(GoldStore(LocalSource(lake)), "run-fixture-0001", out)
    assert report["missing_bronze"] == 0 and report["bronze"] > 100
    snap = GoldStore(LocalSource(out))
    run = snap.run()
    ev = run.suppliers[0]["fields"]["address"]["evidence"][0]
    assert snap.bronze(ev["screenshot_key"]) and snap.bronze_meta(ev["screenshot_key"])
    assert snap.live_jobs("run-fixture-0001")
    rep = live.Replayer(out, "run-fixture-0001", speed=1000.0, new_run_id="offline-1")
    slept = []
    rep.play(sleep=slept.append)
    assert max(slept) <= 5.0 and sum(slept) < 5.0  # 1000x of a ~35 min recording
    c = _client(out, fixture_root / "case")
    assert c.get("/run/offline-1").status_code == 200
    assert c.get(f"/bronze/{ev['screenshot_key']}").status_code == 200

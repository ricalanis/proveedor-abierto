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
    c = TestClient(create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=case_dir)))
    c.cookies.set("pa_lang", "en")
    return c


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
    for needle in ("Sandbox proof", "Crystallized", "Escalations", "BLOCKED", "Practice data."):
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
    assert status["state"] == "done" and status["metrics"]["entities_total"]["supplier"] == 60
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
    assert "Simulated collection." in c.get("/").text
    page = c.get("/completeness").text
    assert "Simulated collection." in page and "✓" not in page.split("dod__grid")[1].split("</dl>")[0]
    run = GoldStore(LocalSource(lake)).run()
    rows = dod.criteria(dod.compute(run.entities, run.domain), run.metrics, run.domain, "recorded")
    assert all(r["met"] is False and r["mock"] for r in rows)
    status = json.loads((lake / "runs/fixture-case/run-fixture-0001/status.json").read_text())
    status["generated_by"] = {"backend": "recorded", "model": "double", "at": "2026-09-26T18:00:00Z"}
    (lake / "runs/fixture-case/run-fixture-0001/status.json").write_text(json.dumps(status))
    assert "Simulated collection." in c.get("/run/run-fixture-0001").text


def test_value_level_recorded_tag(lake, fixture_root):
    path = lake / "gold" / "fixture-case" / "run-fixture-0001" / "entities.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows.sort(key=lambda r: r["class"] != "supplier")  # suppliers first; contracts keep their place after
    rows[0]["properties"]["address"]["generated_by"] = {"backend": "recorded", "model": "double", "at": "2026-09-26"}
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    c = _client(lake, fixture_root / "case")
    frag = c.get(f"/fragments/evidence/{rows[0]['properties']['address']['value_id']}").text
    assert "Simulated collection" in frag
    assert "Simulated collection." in c.get("/").text  # one recorded value marks the whole run


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
    from conftest import s12_compat

    step_validator = validator_for("trace-step.schema.json")
    for line in (run_dir / "trace.live.jsonl").read_text().splitlines()[:80]:
        doc = s12_compat(json.loads(line), step_validator.schema, "trace")
        assert not list(step_validator.iter_errors(doc))


def test_snapshot_then_replay_offline(lake, tmp_path, fixture_root):
    from proveedor_app.snapshot import snapshot

    out = tmp_path / "snap"
    report = snapshot(GoldStore(LocalSource(lake)), "run-fixture-0001", out)
    assert report["missing_bronze"] == 0 and report["bronze"] > 100
    snap = GoldStore(LocalSource(out))
    run = snap.run()
    ev = run.primary[0]["properties"]["address"]["evidence"][0]
    assert snap.bronze(ev["screenshot_key"]) and snap.bronze_meta(ev["screenshot_key"])
    assert snap.live_jobs("run-fixture-0001")
    rep = live.Replayer(out, "run-fixture-0001", speed=1000.0, new_run_id="offline-1")
    slept = []
    rep.play(sleep=slept.append)
    assert max(slept) <= 5.0 and sum(slept) < 5.0  # 1000x of a ~35 min recording
    c = _client(out, fixture_root / "case")
    assert c.get("/run/offline-1").status_code == 200
    assert c.get(f"/bronze/{ev['screenshot_key']}").status_code == 200


def test_structured_engine_steps_are_not_misread():
    steps = [
        {"step_id": "d", "phase": 5, "mode": "D0", "evaluated": {"status": "captured"}, "value_ids": []},
        {"step_id": "p", "phase": 5, "mode": "D0", "evaluated": {"proof_checkpoint": "isolation_probe", "status": "blocked"}},
        {"step_id": "x", "phase": 5, "mode": "S1", "parent_step_id": "d", "evaluated": {"status": "ok"}, "value_ids": ["v"]},
        {"step_id": "f", "phase": 5, "mode": "S1", "evaluated": {"status": "failed", "reason": "selector"}},
        {"step_id": "e", "phase": 5, "mode": "S2", "parent_step_id": "f", "evaluated": {"status": "ok"}, "value_ids": ["w"]},
    ]
    assert [s["event"] for s in live.annotate(steps)] == [None, None, None, "failure", "escalation"]


def test_fixture_jobs_match_engine_schema(lake, validator_for):
    from pathlib import Path

    if not (Path(__file__).parents[2] / "ontofill" / "schemas" / "jobs.schema.json").exists():
        pytest.skip("engine jobs schema not present")
    v = validator_for("jobs.schema.json")
    from conftest import s12_compat

    jobs = GoldStore(LocalSource(lake)).live_jobs("run-fixture-0001")
    errors = [e.message for j in jobs[:30] for e in v.iter_errors(s12_compat(j, v.schema, "jobs"))]
    assert not errors, errors[:3]
    live.Replayer(lake, "run-fixture-0001", duration=0.0, new_run_id="jobs-replay").play(sleep=lambda s: None)
    raw = (lake / "runs" / "fixture-case" / "jobs-replay" / "jobs.jsonl").read_text().splitlines()
    assert raw and not [e.message for line in raw[:30]
                        for e in v.iter_errors(s12_compat(json.loads(line), v.schema, "jobs"))]


def test_preview_output_is_labelled(lake, fixture_root):
    run_dir = lake / "gold" / "fixture-case" / "run-fixture-0001"
    metrics = json.loads((run_dir / "metrics.json").read_text())
    (run_dir / "metrics.json").write_text(json.dumps({**metrics, "preview": True}))
    status_path = lake / "runs/fixture-case/run-fixture-0001/status.json"
    status_path.write_text(json.dumps({**json.loads(status_path.read_text()), "preview": True}))
    c = _client(lake, fixture_root / "case")
    assert "Unreviewed preview." in c.get("/").text
    assert "Unreviewed preview." in c.get("/run/run-fixture-0001").text


def test_evidence_format_is_shown(lake, fixture_root):
    path = lake / "gold" / "fixture-case" / "run-fixture-0001" / "entities.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows.sort(key=lambda r: r["class"] != "supplier")  # suppliers first; contracts keep their place after
    rows[0]["properties"]["tax_id"]["evidence"][0]["format"] = "xlsx"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    frag = _client(lake, fixture_root / "case").get(f"/fragments/evidence/{rows[0]['properties']['tax_id']['value_id']}")
    assert "Procurement portal" in frag.text and "xlsx" in frag.text


def test_engine_report_card_on_fixtures(lake, fixture_root):
    page = _client(lake, fixture_root / "case").get("/engine")
    assert page.status_code == 200
    for needle in ("Engine report card", "Investigative journalist", "SCIAN", "LAASSP", "Completeness",
                   "Extraction honesty", "sandbox jobs passed all five checkpoints", "mock-tag"):
        assert needle in page.text, needle
    assert "matches this recomputation" in page.text


def test_engine_report_card_without_phase_artifacts(lake, tmp_path):
    page = _client(lake, tmp_path / "empty-case").get("/engine")
    assert page.status_code == 200 and "has not written" in page.text


def test_jev_only_gold_is_flagged_and_not_counted(lake, fixture_root):
    from proveedor_app import dod

    path = lake / "gold" / "fixture-case" / "run-fixture-0001" / "entities.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows.sort(key=lambda r: r["class"] != "supplier")  # suppliers first; contracts keep their place after
    target = rows[0]["properties"]["tax_id"]
    assert target["status"] == "gold"
    target["generated_by"] = {"backend": "jev", "model": "jev-entity-match", "at": "2026-09-26T19:00:00Z"}
    for r in rows:  # make the rest live so the banner logic is exercised too
        for f in r["properties"].values():
            if f is not target:
                f["generated_by"] = {"backend": "vultr", "model": "m", "at": "2026-09-26T19:00:00Z"}
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert not dod.is_filled(target) and dod.jev_only(target)
    c = _client(lake, fixture_root / "case")
    frag = c.get(f"/fragments/evidence/{target['value_id']}").text
    assert "supporting model" in frag and "second check" in frag
    assert "backend--jev" in c.get(f"/suppliers/{rows[0]['id']}").text
    card = c.get("/engine").text
    assert "rests on a Jev decision alone" in card


def test_isolation_tier_ladder():
    assert live.isolation_tier("runsc")["tier"] == 3
    assert live.isolation_tier("runc")["ok"] is False
    assert live.isolation_tier("kata-fc")["tier"] == 4
    assert live.isolation_tier(None) is None


def test_run_view_shows_the_track_patterns(lake, fixture_root):
    """§12: vision verdicts (Pattern B), repair attempts (Pattern A), the action gate, a limit kill, and the proof
    panel's secret-hygiene check and resource limits, all on /run."""
    c = _client(lake, fixture_root / "case")
    assert "Show the whole trail" in c.get("/run/run-fixture-0001").text
    page = c.get("/run/run-fixture-0001", params={"limit": 2000}).text
    for needle in ("Vision check of the page after the action", "verdict--achieved", "verdict--not_achieved",
                   "Code attempt 1 of 3", "stderr fed back to the model", "KeyError",
                   "Approve-before-submit gate", "pending approval", "Stopped by the wall-clock timeout",
                   "Secret hygiene", "env keys found: <strong>0</strong>", "metadata IP: <strong>BLOCKED</strong>",
                   "512 MB · 1 CPU · 128 processes · 60 s · 40 steps", "Stopped by a limit: 1"):
        assert needle in page, needle
    api = c.get("/api/run/run-fixture-0001", params={"after": 0}).json()
    assert "Gated actions" in api["panel_html"] and "Vision checks" in api["panel_html"]
    import re

    uncertain = re.search(r'data-k="ev-ver-un">(\d+)<', api["panel_html"])  # Jev pre-screens, early in the run
    assert uncertain and int(uncertain.group(1)) > 0


def test_run_view_shows_the_quarantined_hostile_page(lake, fixture_root):
    """§12a: a page the gateway flagged is withheld from planning, kept as evidence, and shown as a containment step."""
    c = _client(lake, fixture_root / "case")
    page = c.get("/run/run-fixture-0001", params={"limit": 2000}).text
    for needle in ("step--quarantine", "Hostile page quarantined: withheld from planning, kept as evidence",
                   "Flagged by the inference gateway", "<span class=\"mono\">injection</span> (0.97)",
                   "content safety <span class=\"mono\">unsafe</span>"):
        assert needle in page, needle
    api = c.get("/api/run/run-fixture-0001", params={"after": 0}).json()
    import re

    quarantined = re.search(r'data-k="ev-quar">(\d+)<', api["panel_html"])
    assert quarantined and int(quarantined.group(1)) == 1
    steps = live.annotate([{"step_id": "s1", "event": "quarantine", "screen": {"flagged": True, "by": "controller"}}])
    assert steps[0]["kind"] == "quarantine" and steps[0]["detail"]["by"] == "controller"

"""CONTRACT v0.9.6 phase loops: loop steps fold into one collapsible thread per loop run on /run; outer gap-loop
decisions are marker rows; the panel counts iterations and reopens; the live poll re-renders a growing thread."""

import json
import shutil

import pytest
from fastapi.testclient import TestClient
from proveedor_app import live
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app

RUN = "run-fixture-0001"


def _loop(sid, phase, it, role, **lp):
    ex = lp.pop("executed", f"{role} {it}")
    ev = lp.pop("evaluated", {"status": "ok"})
    return {"step_id": sid, "phase": 1 if phase != "outer" else 5, "mode": "S1", "event": "loop",
            "loop": {"phase": phase, "iteration": it, "role": role, **lp}, "observed": "x", "requested": "y",
            "executed": ex, "evaluated": ev, "value_ids": []}


def test_threads_group_iterations_objections_and_stop():
    steps = live.annotate([
        _loop("a", 1, 1, "propose", model="glm-5.3"),
        _loop("b", 1, 1, "critique", model="minimax-m3", verdict="revise", objections=["o1", "o2"]),
        {"step_id": "n", "phase": 5, "mode": "D0", "evaluated": "ok", "value_ids": ["v"]},
        _loop("c", 1, 1, "revise", model="glm-5.3"),
        _loop("d", 1, 2, "check", verdict="pass", stop_reason="checks_passed"),
        _loop("e", "outer", 1, "decide", executed={"reopen": 3}, evaluated={"status": "ok", "reason": "gap"}),
        _loop("f", 1, 1, "propose"),  # the phase ran again: iteration went back, so a new thread
    ])
    assert [s["kind"] for s in steps] == ["loop", "loop", None, "loop", "loop", "loop", "loop"]
    threads = live.loop_threads(steps)
    assert [t["id"] for t in threads] == ["loop-p1-1", "loop-p1-2"]
    t = threads[0]
    assert [it["n"] for it in t["iterations"]] == [1, 2] and t["objections"] == 2
    assert t["stop_reason"] == "checks_passed" and t["stop_label"] == "checks passed"
    assert t["step_ids"] == ["a", "b", "c", "d"] and not t["open"] and threads[1]["open"]
    assert live.is_reopen_marker(steps[5]) and steps[5]["detail"]["reopen"] == 3
    items, updated = live.stream_items(steps, 0, threads)
    kinds = [("thread", i["thread"]["id"]) if "thread" in i else ("step", i["step"]["step_id"]) for i in items]
    assert kinds == [("thread", "loop-p1-2"), ("step", "e"), ("step", "n"), ("thread", "loop-p1-1")] and not updated
    items, updated = live.stream_items(steps, 3, threads, incremental=True)  # the page already has a, b, n
    assert [t["id"] for t in updated] == ["loop-p1-1"]
    assert not any(i.get("thread", {}).get("id") == "loop-p1-1" for i in items)
    summary = live.loop_summary(steps, {})
    assert summary["rows"][0]["iterations"] == 2 and summary["reopened"] == [(3, 1)]


def test_human_revision_is_detected():
    s = live.annotate([_loop("h", 1, 3, "revise", evaluated={"status": "ok", "source": "human", "reason": "why"})])[0]
    assert s["detail"]["human"] and s["detail"]["reason"] == "why"


def test_run_view_renders_the_loop_thread(client):
    page = client.get(f"/run/{RUN}", params={"limit": 2000}).text
    assert page.count('<details class="loop"') == 1
    for needle in ("Phase 1 loop</span> · 3 iterations · 2 objections · stopped: checks passed",
                   "minimax-m3</span> · verdict", "The definition of done has no per-property completeness criterion.",
                   "Revised after the approver's reason: “DoD must follow the case definition”",
                   "Stopped: checks passed", "Reopened phase 3 (fan out): gold gap: founding_date below 80%",
                   "Gap loop: no reopen needed", "Gap loop reopened: P3 ×1", "P1 <span class=\"mono\">3</span> iterations"):
        assert needle in page, needle


@pytest.fixture
def feed(fixture_root, tmp_path):
    """A live feed that grows: the first 3 loop steps of the fixture P1 loop, then 2 more."""
    lake = tmp_path / "lake"
    shutil.copytree(fixture_root / "lake", lake)
    trace = [json.loads(x) for x in (lake / "gold" / "fixture-case" / RUN / "trace.jsonl").read_text().splitlines()]
    loops = [s for s in trace if s.get("event") == "loop" and s["loop"]["phase"] == 1]
    run_dir = lake / "runs" / "fixture-case" / "loop-live"
    run_dir.mkdir(parents=True)
    (run_dir / "status.json").write_text(json.dumps({"run_id": "loop-live", "state": "running", "phase": 1}))

    def write(n):
        (run_dir / "trace.live.jsonl").write_text("".join(json.dumps(s) + "\n" for s in loops[:n]))

    write(3)
    c = TestClient(create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=fixture_root / "case")))
    return c, write


def test_live_poll_re_renders_a_growing_thread(feed):
    c, write = feed
    first = c.get("/api/run/loop-live", params={"after": 0}).json()
    assert first["count"] == 3 and 'id="loop-p1-1"' in first["steps_html"] and first["threads_html"] == []
    assert "running" in first["steps_html"]  # no stop reason yet
    write(7)
    nxt = c.get("/api/run/loop-live", params={"after": 3}).json()
    assert nxt["count"] == 7 and 'id="loop-p1-1"' not in nxt["steps_html"]
    (upd,) = nxt["threads_html"]
    assert upd["id"] == "loop-p1-1" and "Iteration 2" in upd["html"] and "stopped: checks passed" in upd["html"]


def test_replay_keeps_loop_steps(lake):
    live.Replayer(lake, RUN, duration=0.0, new_run_id="loop-replay").play(sleep=lambda s: None)
    rows = (lake / "runs" / "fixture-case" / "loop-replay" / "trace.live.jsonl").read_text().splitlines()
    assert sum(1 for r in rows if json.loads(r).get("event") == "loop") == 12


@pytest.fixture
def lake(fixture_root, tmp_path):
    dst = tmp_path / "lake2"
    shutil.copytree(fixture_root / "lake", dst)
    return dst

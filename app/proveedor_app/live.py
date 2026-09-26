"""Live run view model (CONTRACT section 4b) and the replayer that feeds it for rehearsal and as demo insurance.

The replayer turns a finished run (gold export, plus `trace.live.jsonl` when it was recorded) into a live feed:
it appends the steps to `runs/<case_id>/<new_run_id>/trace.live.jsonl` on the original clock, compressed to a
chosen duration, rewrites `status.json` with partial metrics as values arrive, and publishes the gold export
under the new run id when it finishes.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from . import CORE_FIELDS, dod
from .gold import GoldStore, LocalSource

MODE_RANK = {"D0": 0, "D1": 1, "S1": 2, "S2": 3}
MODE_NAMES = {
    "D0": "Deterministic",
    "D1": "Inference-assisted script",
    "S1": "Agentic loop",
    "S2": "Computer use + vision",
}
PHASES = [(1, "Scope"), (2, "Ontology"), (3, "Fan out"), (4, "Local scoping"), (5, "Execute")]
CHECKPOINT_PHASE = {"prd": 1, "factors": 2, "ontology": 2}
# "blocked" is deliberately absent: an isolation probe that is BLOCKED is the success case.
_FAIL_WORDS = ("fail", "captcha", "timeout", "error", "refused")


def _text(step: dict) -> str:
    return " ".join(json.dumps(step.get(k)) if isinstance(step.get(k), (dict, list)) else str(step.get(k) or "")
                    for k in ("requested", "executed", "evaluated")).lower()


def _evaluated(step: dict) -> str:
    ev = step.get("evaluated")
    if isinstance(ev, dict):  # structured: judge by its status, not by words that merely appear in details
        return str(ev.get("status") or ev.get("result") or "").lower()
    return str(ev or "").lower()


def _failed(step: dict) -> bool:
    return any(w in _evaluated(step) for w in _FAIL_WORDS)


def annotate(steps: list[dict]) -> list[dict]:
    """Add `event` to each step. An `event` key from the engine (even null) wins; inference is only a fallback."""
    by_id = {s.get("step_id"): s for s in steps}
    out = []
    for s in steps:
        s = dict(s)
        event = s.get("event")
        if "event" not in s:
            parent = by_id.get(s.get("parent_step_id"))
            text = _text(s)
            if parent and parent.get("phase") == 5 and _failed(parent) and \
                    MODE_RANK.get(s.get("mode"), 0) > MODE_RANK.get(parent.get("mode"), 0):
                event = "escalation"  # a costlier mode after the cheaper one failed its check
            elif "crystalliz" in text or "code.promote" in text:
                event = "crystallization"
            elif _failed(s) and not s.get("value_ids"):
                event = "failure"
        s["event"] = event
        out.append(s)
    return out


def summarize(steps: list[dict], status: dict | None) -> dict:
    """Everything the side panel shows, from the step stream plus status.json."""
    status = status or {}
    modes = {m: 0 for m in MODE_RANK}
    events = {"escalation": 0, "crystallization": 0, "repair": 0, "hard_stop": 0, "failure": 0}
    values = 0
    for s in steps:
        if s.get("mode") in modes:
            modes[s["mode"]] += 1
        if s.get("event") in events:
            events[s["event"]] += 1
        values += len(s.get("value_ids") or [])
    phase = status.get("phase") or max((s.get("phase") or 1 for s in steps), default=1)
    metrics = status.get("metrics") or {}
    return {
        "state": status.get("state") or ("running" if steps else "waiting"),
        "phase": phase,
        "checkpoint": status.get("checkpoint_pending"),
        "updated_at": status.get("updated_at"),
        "live_view_url": status.get("live_view_url"),
        "sources": status.get("sources") or [],
        "metrics": metrics,
        "fields": [{"name": f, "ratio": (metrics.get("per_field_completeness") or {}).get(f)} for f in CORE_FIELDS],
        "modes": modes,
        "mode_total": sum(modes.values()),
        "events": events,
        "value_count": values,
        "step_count": len(steps),
    }


CHECKPOINTS = [
    ("host", "Host check", "Sandbox host and runtime (gVisor runsc), CPU virtualization"),
    ("task", "Task and real result", "What was dispatched and what came back"),
    ("where", "Where it ran", "Hostname and uname from inside the pod"),
    ("isolation", "Isolation probe", "A non-allowlisted domain and a write outside the pod must be BLOCKED"),
    ("teardown", "Teardown", "Pod gone, no sandboxes left"),
]


def checkpoint_state(job: dict, key: str) -> str:
    """pass | fail | pending for one of the five proof checkpoints of a sandbox job."""
    cp = (job.get("checkpoints") or {}).get(key)
    if not cp:
        return "pending"
    if key == "isolation":
        probes = cp.get("probes") or []
        if probes and all(str(p.get("result", "")).upper() == "BLOCKED" for p in probes):
            return "pass"
        return "fail" if probes else "pending"
    return "pass" if cp.get("ok") else "fail"


def isolation_tier(runtime: str | None) -> dict | None:
    """Where a runtime sits on the track deck's isolation ladder ("a container is not a sandbox")."""
    r = (runtime or "").lower()
    if not r:
        return None
    if any(k in r for k in ("firecracker", "kata", "microvm", "libkrun")):
        return {"tier": 4, "name": "microVM", "ok": True, "note": "own kernel; the VM is thrown away"}
    if "runsc" in r or "gvisor" in r:
        return {"tier": 3, "name": "gVisor user-space kernel", "ok": True, "note": "syscalls intercepted; only the sandbox process can die"}
    if "runc" in r or "docker" in r:
        return {"tier": 2, "name": "container (runc)", "ok": False, "note": "shared kernel: a container is not a sandbox"}
    return {"tier": None, "name": runtime, "ok": False, "note": "runtime not on the ladder"}


def proof(jobs: list[dict]) -> dict:
    """Aggregate proof over all jobs, plus the latest job whose checkpoints all resolved (the one to show judges)."""
    counts = {key: {"pass": 0, "fail": 0, "pending": 0} for key, _, _ in CHECKPOINTS}
    for job in jobs:
        for key, _, _ in CHECKPOINTS:
            counts[key][checkpoint_state(job, key)] += 1
    complete = [j for j in jobs if all(checkpoint_state(j, k) != "pending" for k, _, _ in CHECKPOINTS)]
    featured = complete[-1] if complete else (jobs[-1] if jobs else None)
    runtime = (((featured or {}).get("checkpoints") or {}).get("host") or {}).get("runtime")
    return {"jobs": len(jobs), "counts": counts, "featured": featured, "recent": jobs[-8:][::-1],
            "checkpoints": CHECKPOINTS, "state": checkpoint_state, "tier": isolation_tier(runtime)}


# Replayer ------------------------------------------------------------------------------------------------------

def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _ts(step: dict) -> float:
    try:
        return datetime.fromisoformat(str(step.get("ts"))).timestamp()
    except ValueError:
        return 0.0


class Replayer:
    """Replay a finished run from a file lake into the live feed of the same (or another) file lake."""

    def __init__(self, root: Path, source_run_id: str | None = None, *, target_root: Path | None = None,
                 case_id: str | None = None, new_run_id: str | None = None, duration: float = 45.0,
                 speed: float | None = None, publish_gold: bool = True):
        self.source = GoldStore(LocalSource(root), case_id)
        self.run = self.source.run(source_run_id)
        self.case_id = self.source.case_id
        self.target = Path(target_root or root)
        self.new_run_id = new_run_id or f"{self.run.run_id}-replay-{datetime.now(UTC):%H%M%S}"
        self.duration = duration
        self.speed = speed  # when set, replay at N x the recorded pace (long gaps still capped) instead of a duration
        self.publish_gold = publish_gold
        recorded = self.source.live_steps(self.run.run_id)  # prefer the live record: it has screenshot keys
        steps = recorded or list(self.run.trace)
        self.steps = sorted(steps, key=_ts)
        self.jobs_by_step: dict[str, list[dict]] = {}
        for job in self.source.live_jobs(self.run.run_id):
            self.jobs_by_step.setdefault(job.get("step_id"), []).append(job)
        self.recorded_status = self.source.live_status(self.run.run_id) or {}
        self._stop = threading.Event()

    @property
    def run_dir(self) -> Path:
        return self.target / "runs" / self.case_id / self.new_run_id

    def _thumb(self, step: dict) -> str | None:
        for vid in step.get("value_ids") or []:
            ref = self.run.values.get(vid)
            for e in (ref.data.get("evidence") if ref else None) or []:
                if e.get("screenshot_key") and e.get("source_id") == step.get("source_id"):
                    return e["screenshot_key"]
        return None

    def _partial_metrics(self, emitted: set[str]) -> dict:
        suppliers = []
        for s in self.run.suppliers:
            fields = {}
            for name, f in (s.get("fields") or {}).items():
                fields[name] = f if f.get("value_id") in emitted else {**f, "status": "missing", "evidence": []}
            if any(f.get("value_id") in emitted for f in (s.get("fields") or {}).values()):
                suppliers.append({**s, "fields": fields})
        return dod.compute(suppliers)

    def _status(self, state: str, phase: int, emitted: set[str], health: dict) -> dict:
        types = {}
        for s in self.run.suppliers:
            for f in (s.get("fields") or {}).values():
                for e in f.get("evidence") or []:
                    types.setdefault(e.get("source_id"), e.get("source_type"))
        return {
            "run_id": self.new_run_id, "state": state, "phase": phase, "checkpoint_pending": None,
            "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "sources": [{"source_id": sid, "source_type": types.get(sid) or "unknown", "health": h}
                        for sid, h in health.items()],
            "metrics": self._metrics_with_provenance(emitted),
            "generated_by": self.generated_by,
        }

    @property
    def generated_by(self) -> dict:
        """Provenance of the replayed run: the recording's own, never upgraded."""
        gen = self.recorded_status.get("generated_by") or self.run.metrics.get("generated_by")
        if gen:
            return gen
        return {"backend": self.run.inference_backend or "recorded", "model": "unknown",
                "at": datetime.now(UTC).isoformat(timespec="seconds")}

    def _metrics_with_provenance(self, emitted: set[str]) -> dict:
        metrics = self._partial_metrics(emitted)
        metrics["inference_backend"] = self.generated_by["backend"]
        return metrics

    def stop(self) -> None:
        self._stop.set()

    def play(self, sleep=time.sleep) -> str:
        """Run the replay to completion (blocking). Returns the new run id."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        live = self.run_dir / "trace.live.jsonl"
        live.write_text("")
        jobs_file = self.run_dir / "jobs.jsonl"
        jobs_file.write_text("")
        _write_atomic(self.target / "runs" / self.case_id / "latest.json", json.dumps({"run_id": self.new_run_id}))
        span = max(_ts(self.steps[-1]) - _ts(self.steps[0]), 1e-9) if self.steps else 1.0
        scale = 1.0 / self.speed if self.speed else self.duration / span
        emitted: set[str] = set()
        health: dict[str, dict] = {}
        last_status = 0.0
        prev = _ts(self.steps[0]) if self.steps else 0.0
        for step in self.steps:
            if self._stop.is_set():
                break
            sleep(max(0.0, min((_ts(step) - prev) * scale, 5.0)))
            prev = _ts(step)
            rec = dict(step, run_id=self.new_run_id)
            if not rec.get("screenshot_key"):
                thumb = self._thumb(step)
                if thumb:
                    rec["screenshot_key"] = thumb
            with live.open("a") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            with jobs_file.open("a") as fh:  # complete records only: jobs.schema.json requires all five checkpoints
                for job in self.jobs_by_step.get(step.get("step_id"), []):
                    fh.write(json.dumps(dict(job, run_id=self.new_run_id), ensure_ascii=False) + "\n")
            emitted.update(step.get("value_ids") or [])
            if step.get("phase") == 5 and step.get("source_id"):
                h = health.setdefault(step["source_id"], {"ok": 0, "failed": 0, "yield": 0})
                if annotate([step])[0]["event"] == "failure":
                    h["failed"] += 1
                else:
                    h["ok"] += 1
                h["yield"] += len(step.get("value_ids") or [])
            now = time.monotonic()
            if now - last_status > 0.4 or step is self.steps[-1]:
                _write_atomic(self.run_dir / "status.json",
                              json.dumps(self._status("running", step.get("phase") or 1, emitted, health)))
                last_status = now
        done = not self._stop.is_set()
        _write_atomic(self.run_dir / "status.json", json.dumps(
            self._status("done" if done else "failed", 5, emitted, health)))
        if done and self.publish_gold:
            self._publish_gold()
        return self.new_run_id

    def _publish_gold(self) -> None:
        out = self.target / "gold" / self.case_id / self.new_run_id
        out.mkdir(parents=True, exist_ok=True)
        trace = [dict(s, run_id=self.new_run_id) for s in self.run.trace]
        for name, rows in (("suppliers", self.run.suppliers), ("contracts", self.run.contracts), ("trace", trace)):
            (out / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        metrics = copy.deepcopy(self.run.metrics)
        metrics["run_id"] = self.new_run_id
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        _write_atomic(self.target / "gold" / self.case_id / "latest.json", json.dumps({"run_id": self.new_run_id}))

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.play, name="pa-replay", daemon=True)
        thread.start()
        return thread

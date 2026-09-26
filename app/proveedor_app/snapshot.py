"""Cache one run from the lake (S3 or file) into a self-contained local folder: the demo's offline fallback.

The snapshot has the bucket layout, so `pa-app serve --gold-dir <snapshot>` serves it and
`pa-app serve --gold-dir <snapshot> --replay <run_id>` replays it through the live run view.
"""

from __future__ import annotations

import json
from pathlib import Path

from .gold import GoldStore

RUN_FILES = ("suppliers.jsonl", "contracts.jsonl", "trace.jsonl", "metrics.json")
LIVE_FILES = ("trace.live.jsonl", "status.json", "jobs.jsonl")


def _keys(run, live_steps: list[dict]) -> set[str]:
    keys: set[str] = set()
    evidence = [e for s in run.suppliers for f in (s.get("fields") or {}).values() for e in f.get("evidence") or []]
    evidence += [e for c in run.contracts for e in c.get("evidence") or []]
    for e in evidence:
        keys.update(k for k in (e.get("bronze_key"), e.get("screenshot_key")) if k)
    keys.update(s["screenshot_key"] for s in live_steps if s.get("screenshot_key"))
    return keys


def snapshot(store: GoldStore, run_id: str | None, out: Path) -> dict:
    """Copy a run's gold export, live feed and every bronze object it references. Returns counts."""
    run = store.run(run_id)
    src = store.source
    case = store.case_id
    copied = {"files": 0, "bronze": 0, "missing_bronze": 0}

    def put(key: str, data: bytes) -> None:
        path = out / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        copied["files"] += 1

    for name in RUN_FILES:
        data = src.read(f"gold/{case}/{run.run_id}/{name}")
        if data is not None:
            put(f"gold/{case}/{run.run_id}/{name}", data)
    put(f"gold/{case}/latest.json", json.dumps({"run_id": run.run_id}).encode())
    for name in LIVE_FILES:
        data = src.read(f"runs/{case}/{run.run_id}/{name}")
        if data is not None:
            put(f"runs/{case}/{run.run_id}/{name}", data)
    for key in sorted(_keys(run, store.live_steps(run.run_id))):
        path = store._bronze_path(key)
        data = src.read(path) if path else None
        if data is None:
            copied["missing_bronze"] += 1
            continue
        put(path, data)
        copied["bronze"] += 1
        meta = src.read(f"{path}.meta.json")
        if meta is not None:
            put(f"{path}.meta.json", meta)
    return {"case_id": case, "run_id": run.run_id, **copied}

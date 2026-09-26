"""Engine report card: scores the engine's own output against the evaluation harness (eval/, package pa_eval).

The only app module that reads the harness, and read-only: references are shown as the yardstick and are never
written into case/ or passed to the engine. Without the harness installed, the page still shows DoD progress,
extraction honesty and sandbox proof.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from . import dod, live
from .gold import GoldStore, Run
from .investigate import CaseDir

try:  # evaluation harness, optional at runtime
    from pa_eval import REFERENCES, rubric
    from pa_eval.cli import score_ontology
except ImportError:  # pragma: no cover - the harness ships in the same repo
    REFERENCES = rubric = score_ontology = None


def _json(case: CaseDir, rel: str) -> tuple[dict | None, Path | None]:
    path = case.path(rel)
    if not path or not path.is_file():
        return None, None
    try:
        return json.loads(path.read_text()), path
    except ValueError:
        return None, path


def _reference_meta(ref_file: str) -> dict:
    try:
        meta = yaml.safe_load((REFERENCES / ref_file).read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {"name": ref_file}
    return {k: meta.get(k) for k in ("name", "publisher", "source_url", "license", "verified", "retrieved_at")}


def honesty(steps: list[dict]) -> dict:
    """How values were obtained: share of values and steps per execution mode, escalations, crystallizations."""
    steps = live.annotate(steps)
    values = {m: 0 for m in live.MODE_RANK}
    counts = {m: 0 for m in live.MODE_RANK}
    for s in steps:
        mode = s.get("mode")
        if mode in counts:
            counts[mode] += 1
            values[mode] += len(s.get("value_ids") or [])
    events = {e: sum(1 for s in steps if s.get("event") == e)
              for e in ("escalation", "crystallization", "repair", "hard_stop", "failure")}
    total_values = sum(values.values())
    return {"values": values, "steps": counts, "total_values": total_values, "events": events,
            "deterministic_share": (values["D0"] + values["D1"]) / total_values if total_values else None}


def macro_replays(case: CaseDir) -> dict | None:
    """Pass rate of crystallized macros' replay tests, from case/05-macros/**/*.json when the engine writes them."""
    passed = total = 0
    for path in sorted(case.root.glob("05-macros/**/*.json")):
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        tests = doc.get("tests") if isinstance(doc, dict) else None
        for t in tests if isinstance(tests, list) else []:
            if isinstance(t, dict) and "passed" in t:
                total += 1
                passed += bool(t["passed"])
    return {"passed": passed, "total": total} if total else None


def build(store: GoldStore, run: Run, case: CaseDir) -> dict:
    backend = run.inference_backend
    card: dict = {"run_id": run.run_id, "backend": backend, "mock": backend == "recorded",
                  "harness": rubric is not None}

    prd, _ = _json(case, "01-scope/prd.json")
    card["prd"] = rubric.evaluate(prd) if (prd and rubric) else None
    card["prd_present"] = prd is not None

    onto, onto_path = _json(case, "02-ontology/ontology.json")
    taxonomies = []
    if onto and score_ontology:
        for factor_id, s in score_ontology(onto_path).items():
            ref = _reference_meta(s["reference_file"]) if s.get("reference_file") else None
            taxonomies.append({"factor_id": factor_id, "score": s, "reference": ref})
    card["taxonomies"] = taxonomies
    card["ontology_present"] = onto is not None

    recomputed = dod.compute(run.entities, run.domain)
    card["dod"] = {"recomputed": recomputed, "criteria": dod.criteria(recomputed, run.metrics or {}, run.domain, backend, run.dod_queries,
                                                   run.entities),
                   "mismatches": dod.cross_check(recomputed, run.metrics, run.domain) if run.metrics
                   else ["no metrics.json"]}

    steps = store.live_steps(run.run_id) or list(run.trace)
    card["honesty"] = honesty(steps)
    by_backend = dict((run.metrics or {}).get("decisions_by_backend") or {})
    if not by_backend:  # derive from step provenance when metrics.json does not carry it
        for s in steps:
            b = (s.get("generated_by") or {}).get("backend")
            if b:
                by_backend[b] = by_backend.get(b, 0) + 1
    card["backends"] = by_backend
    card["jev_only_gold"] = [(ref.entity_id, ref.prop, ref.value_id) for ref in run.values.values()
                             if ref.data.get("status") == "gold" and dod.jev_only(ref.data)]
    card["macros"] = macro_replays(case)
    proof = live.proof(store.live_jobs(run.run_id))
    card["proof"] = {"jobs": proof["jobs"], "counts": proof["counts"], "checkpoints": proof["checkpoints"],
                     "all_pass": sum(1 for j in store.live_jobs(run.run_id)
                                     if all(live.checkpoint_state(j, k) == "pass" for k, _, _ in live.CHECKPOINTS))}
    return card

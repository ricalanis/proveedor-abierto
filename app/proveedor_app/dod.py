"""Recompute the CONTRACT section 4 DoD keys from a gold export and cross-check the engine's metrics.json.

    uv run pa-app dod [--gold-dir DIR] [--run-id ID]

Exit code 0 when the recomputed keys match the engine's metrics.json, 1 on any mismatch.
"""

from __future__ import annotations

from . import CORE_FIELDS

TARGETS = {"suppliers_at_80pct_core": 50, "distinct_source_types": 4, "gold_values_without_evidence": 0}
DOD_KEYS = ("suppliers_total", "suppliers_at_80pct_core", "distinct_source_types", "gold_values_without_evidence")


def jev_only(field: dict | None) -> bool:
    """A value whose only decision came from Jev (CONTRACT section 10): never enough for gold on its own."""
    return bool(field) and (field.get("generated_by") or {}).get("backend") == "jev"


def is_filled(field: dict | None) -> bool:
    """A core field counts as complete when it is gold, backed by evidence, and not decided by Jev alone."""
    return bool(field) and field.get("status") == "gold" and bool(field.get("evidence")) and not jev_only(field)


def core_ratio(supplier: dict) -> float:
    fields = supplier.get("fields") or {}
    return sum(is_filled(fields.get(name)) for name in CORE_FIELDS) / len(CORE_FIELDS)


def compute(suppliers: list[dict]) -> dict:
    per_field = {
        name: (sum(is_filled((s.get("fields") or {}).get(name)) for s in suppliers) / len(suppliers))
        if suppliers
        else 0.0
        for name in CORE_FIELDS
    }
    source_types: set[str] = set()
    without_evidence = 0
    for s in suppliers:
        for f in (s.get("fields") or {}).values():
            if f.get("status") != "gold":
                continue
            if not f.get("evidence"):
                without_evidence += 1
            source_types.update(e["source_type"] for e in f.get("evidence") or [] if e.get("source_type"))
    return {
        "suppliers_total": len(suppliers),
        "suppliers_at_80pct_core": sum(core_ratio(s) >= 0.8 for s in suppliers),
        "per_field_completeness": per_field,
        "distinct_source_types": len(source_types),
        "gold_values_without_evidence": without_evidence,
    }


def cross_check(recomputed: dict, engine: dict, tol: float = 1e-6) -> list[str]:
    """Human-readable mismatches between our recomputation and the engine's metrics.json."""
    problems = []
    for key in DOD_KEYS:
        if key not in engine:
            problems.append(f"{key}: missing from engine metrics.json")
        elif engine[key] != recomputed[key]:
            problems.append(f"{key}: engine={engine[key]} recomputed={recomputed[key]}")
    engine_fields = engine.get("per_field_completeness") or {}
    for name, ratio in recomputed["per_field_completeness"].items():
        if name not in engine_fields:
            problems.append(f"per_field_completeness.{name}: missing from engine metrics.json")
        elif abs(engine_fields[name] - ratio) > tol:
            problems.append(f"per_field_completeness.{name}: engine={engine_fields[name]:.4f} recomputed={ratio:.4f}")
    return problems


def dod_met(metrics: dict, inference_backend: str | None = None) -> dict[str, bool]:
    """Targets met. Anything produced by recorded (mocked) inference never counts as done (CONTRACT section 7)."""
    if (inference_backend or metrics.get("inference_backend")) == "recorded":
        return {key: False for key in TARGETS}
    return {
        "suppliers_at_80pct_core": metrics.get("suppliers_at_80pct_core", 0) >= TARGETS["suppliers_at_80pct_core"],
        "distinct_source_types": metrics.get("distinct_source_types", 0) >= TARGETS["distinct_source_types"],
        "gold_values_without_evidence": metrics.get("gold_values_without_evidence", 1)
        == TARGETS["gold_values_without_evidence"],
    }

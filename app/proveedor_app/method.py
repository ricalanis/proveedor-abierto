"""'Cómo se hizo': the path from the case's question to the published values, read from the case package and the
gold export only. No engine internals (modes, steps, runs, costs): those belong to the Ontofill Console."""

from __future__ import annotations

import json

from . import dod, i18n
from .domain import Domain, humanize
from .gold import Run
from .investigate import CaseDir

ENGINE_REPO = "https://github.com/ricalanis/ontofill"
CASE_REPO = "https://github.com/ricalanis/proveedor-abierto"


def _brief(case: CaseDir) -> str | None:
    text = case.read("brief.md", limit=4000)
    if not text:
        return None
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    return "\n".join(lines).strip() or None


def _prd(case: CaseDir) -> dict | None:
    raw = case.read("01-scope/prd.json", limit=10**6)
    try:
        doc = json.loads(raw) if raw else None
    except ValueError:
        doc = None
    if not isinstance(doc, dict):
        return None
    pending = case.exists("01-scope/APPROVAL_PENDING.md") and not case.exists("01-scope/APPROVED")

    def texts(key: str) -> list[str]:
        out = []
        for item in doc.get(key) or []:
            text = item.get("description") if isinstance(item, dict) else item
            if isinstance(text, str) and text.strip():
                out.append(text.strip())
        return out

    done = []
    for c in doc.get("definition_of_done") or []:
        if isinstance(c, dict) and c.get("metric"):
            done.append({"what": humanize(str(c["metric"])).replace("pct", "%"), "op": c.get("operator") or "", "target": c.get("target")})
    return {"personas": texts("personas"), "jobs": texts("jobs_to_be_done"), "constraints": texts("constraints"),
            "non_goals": texts("non_goals"), "done": done, "pending": pending}


def _sources(run: Run, case: CaseDir, domain: Domain) -> list[dict]:
    """The public sources behind published values, most used first (same counts as /fuentes)."""
    from .sources import directory

    return [{"host": s["host"], "kind": s["kind"], "backs": s["backs"]} for s in directory(run, case, domain)["sources"]]


def _evidence(run: Run) -> dict:
    values = [ref for ref in run.values.values() if dod.is_filled(ref.data) or ref.data.get("status") == "conflict"]
    receipts = [ev for ref in values for ev in ref.data.get("evidence") or []]
    stamps = sorted(ts for ts in (i18n.parse_ts(ev.get("captured_at")) for ev in receipts) if ts)
    sample = next((ref for ref in values if run.steps_by_value.get(ref.value_id) and ref.data.get("evidence")), None)
    return {"published": len(values), "with_receipt": sum(1 for ref in values if ref.data.get("evidence")),
            "receipts": len(receipts), "screenshots": sum(1 for ev in receipts if ev.get("screenshot_key")),
            "first": stamps[0].isoformat() if stamps else None, "last": stamps[-1].isoformat() if stamps else None,
            "sample": sample}


def build(run: Run | None, case: CaseDir, domain: Domain) -> dict:
    primary = domain.primary_class
    return {
        "brief": _brief(case),
        "prd": _prd(case),
        "classes": [{"label": domain.class_label(cid), "description": (domain.classes.get(cid) or {}).get("description")}
                    for cid in domain.classes] or [{"label": domain.class_label(primary), "description": None}],
        "basic": [p.label for p in domain.dod_props()],
        "rules": [domain.rule(rid)["label"] for rid in domain.rules],
        "relations": [domain.relation_label(rid) for rid in domain.peer_relations()],
        "sources": _sources(run, case, domain) if run else [],
        "found_sources": len(case.sources()),
        "evidence": _evidence(run) if run else None,
        "engine_repo": ENGINE_REPO, "case_repo": CASE_REPO,
    }

"""Rubric: the engine's Phase 1 PRD against the hypotheses in docs/planning/02-anticorruption-definition.md.

Those hypotheses judge the engine's output; they are not inputs. Per 02, if the engine finds different personas or
signals with good evidence, that is a success, so personas that match no hypothesis are reported as
"alternative" and never counted as failures. Whether an alternative persona has good evidence lives in the
research ledger (case/01-scope/research-ledger), which this rubric does not read; a human checks it.

Matching is keyword-based (English and Spanish, accents stripped). A "partial" hit means only a weak cue was
found (e.g. a founding-date field without any "shortly before an award" logic).
"""

from __future__ import annotations

import re

from .taxonomy import normalize

PERSONAS = {
    "investigative_journalist": {
        "label": "Investigative journalist",
        "strong": [r"journalis", r"periodis", r"reporter", r"reporter[oa]"],
        "weak": [r"\bmedia\b", r"\bmedios\b"],
    },
    "procurement_officer": {
        "label": "Procurement officer",
        "strong": [r"procurement (officer|official|staff)", r"purchasing (officer|official)", r"contracting officer",
                   r"funcionari[oa] de compras", r"area contratante", r"unidad compradora", r"servidor publico"],
        "weak": [r"\bbuyer\b", r"comprador"],
    },
    "civil_society_watchdog": {
        "label": "Civil-society watchdog",
        "strong": [r"watchdog", r"civil society", r"sociedad civil", r"\bngo\b", r"\bong\b", r"\bosc\b",
                   r"observatori"],
        "weak": [r"activist", r"activista", r"monitor"],
    },
    "auditor_or_researcher": {
        "label": "Auditor or researcher",
        "strong": [r"auditor", r"\baudit", r"auditori", r"fiscaliza", r"researcher", r"investigador", r"academic",
                   r"academic[oa]"],
        "weak": [r"analyst", r"analista"],
    },
}

SIGNALS = {
    "tax_authority_list": {
        "label": "Presence on the tax authority's fake-invoice list",
        "strong": [r"69 ?b", r"\befos\b", r"fake invoice", r"simulated operation", r"operaciones (inexistentes|simuladas)",
                   r"tax authorit[a-z]* list", r"tax list", r"lista (negra )?del sat", r"listado del sat"],
        "weak": [r"\bsat\b", r"tax authorit"],
    },
    "sanctions": {
        "label": "Sanctions",
        "strong": [r"sanction", r"sancion", r"inhabilitad", r"debar"],
        "weak": [r"penalt", r"penaliz"],
    },
    "new_company_before_award": {
        "label": "Company created shortly before an award",
        "strong": [r"shortly before", r"recently (created|founded|incorporated)", r"company age", r"age at (award|first)",
                   r"recien (creada|constituida)", r"creada poco antes", r"antiguedad de la empresa",
                   r"(founded|created|incorporated) .{0,40}before .{0,20}(award|contract)"],
        "weak": [r"founding date", r"fecha de constitucion", r"incorporation date"],
    },
    "shared_address_or_representative": {
        "label": "Shared addresses or representatives between bidders",
        "strong": [r"shared? (address|addresses|representative)", r"same (address|representative)",
                   r"share addresses", r"mismo domicilio", r"domicilio compartido", r"representante (legal )?comun",
                   r"mismo representante"],
        "weak": [r"\bnetwork", r"\bred(es)? de\b", r"\blinks?\b"],
    },
}


def _hits(text: str, spec: dict) -> tuple[str, list[str]]:
    for strength in ("strong", "weak"):
        found = [p for p in spec[strength] if re.search(p, text)]
        if found:
            return ("found" if strength == "strong" else "partial"), found
    return "missing", []


def evaluate(prd: dict) -> dict:
    personas = prd.get("personas") or []
    persona_texts = {p.get("id", "?"): normalize(f"{p.get('id', '')} {p.get('description', '')}") for p in personas}
    all_persona_text = " ".join(persona_texts.values())
    corpus = normalize(" ".join(
        [p.get("description", "") for p in personas]
        + [j.get("description", "") for j in prd.get("jobs_to_be_done") or []]
        + [r.get("description", "") for r in prd.get("requirements") or []]
        + [c.get("metric", "") for c in prd.get("definition_of_done") or []]
        + list(prd.get("constraints") or []) + list(prd.get("non_goals") or [])
    ))

    persona_results = {}
    matched_ids: set[str] = set()
    for key, spec in PERSONAS.items():
        status, patterns = _hits(all_persona_text, spec)
        who = [pid for pid, text in persona_texts.items() if _hits(text, spec)[0] == status and status != "missing"]
        if status == "found":
            matched_ids.update(who)
        persona_results[key] = {"label": spec["label"], "status": status, "matched_personas": who,
                                "patterns": patterns}
    alternative = [{"id": p.get("id"), "description": p.get("description")} for p in personas
                   if p.get("id") not in matched_ids]
    signal_results = {}
    for key, spec in SIGNALS.items():
        status, patterns = _hits(corpus, spec)
        signal_results[key] = {"label": spec["label"], "status": status, "patterns": patterns}

    personas_found = sum(r["status"] == "found" for r in persona_results.values())
    signals_found = sum(r["status"] == "found" for r in signal_results.values())
    if personas_found >= 2 and signals_found >= 3:
        verdict = "consistent with the hypotheses"
    elif alternative:
        verdict = "diverges from the hypotheses: check the alternative personas' evidence (can still be a success)"
    else:
        verdict = "weak: few hypotheses confirmed and no alternative personas to weigh"
    return {
        "personas": persona_results,
        "alternative_personas": alternative,
        "signals": signal_results,
        "summary": {"personas_found": personas_found, "personas_total": len(PERSONAS),
                    "signals_found": signals_found, "signals_total": len(SIGNALS), "verdict": verdict},
    }


def to_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [f"**PRD vs 02 hypotheses:** {s['verdict']}",
             f"- Personas confirmed: {s['personas_found']}/{s['personas_total']}",
             f"- Signals confirmed: {s['signals_found']}/{s['signals_total']}", "", "| Hypothesis | Status |", "|---|---|"]
    for group in ("personas", "signals"):
        for r in report[group].values():
            lines.append(f"| {r['label']} | {r['status']} |")
    if report["alternative_personas"]:
        lines += ["", "Alternative personas (not failures; check their evidence in the research ledger):"]
        lines += [f"- `{p['id']}`: {p['description']}" for p in report["alternative_personas"]]
    return "\n".join(lines)

"""Synthetic phase artifacts for the fixture case package (CONTRACT section 4c), shaped per the engine schemas.

Used only to rehearse and test the approver's review screens. Sources are `.example` hosts; nothing here is a
finding about real procurement.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

GEN = {"backend": "recorded", "model": "synthetic-fixture", "at": "2026-09-26T18:00:00+00:00"}

PRD = {
    "version": "v1",
    "brief_path": "brief.md",
    "personas": [
        {"id": "journalist", "description": "Investigative journalist following public money to specific companies"},
        {"id": "watchdog", "description": "Civil-society watchdog monitoring procurement across agencies"},
        {"id": "auditor", "description": "Public auditor sampling suppliers for compliance reviews"},
    ],
    "jobs_to_be_done": [
        {"id": "vet_supplier", "persona_id": "journalist",
         "description": "Check in minutes whether a contract winner is a legitimate, operating company"},
        {"id": "find_networks", "persona_id": "journalist",
         "description": "See which suppliers share addresses or representatives across procedures"},
        {"id": "monitor_lists", "persona_id": "watchdog",
         "description": "Know when a supplier appears on the tax authority's list or a sanctions registry"},
        {"id": "sample_with_evidence", "persona_id": "auditor",
         "description": "Pull a sample of suppliers with the official source behind every field"},
    ],
    "requirements": [
        {"id": "r_identity", "job_id": "vet_supplier", "description": "Legal name, RFC, address and founding date per supplier"},
        {"id": "r_status", "job_id": "monitor_lists", "description": "Tax-list and sanction status with capture dates"},
        {"id": "r_links", "job_id": "find_networks", "description": "Links by shared address, representative or procedure"},
        {"id": "r_evidence", "job_id": "sample_with_evidence", "description": "Every value carries its source link and screenshot"},
    ],
    "constraints": ["Public sources only; no logins, no captcha bypass", "Polite crawl rates; budget capped in the run"],
    "non_goals": ["Accusing anyone or scoring corruption probability", "Profiling private individuals"],
    "definition_of_done": [
        {"id": "dod_suppliers", "metric": "suppliers_at_80pct_core", "operator": ">=", "target": 50},
        {"id": "dod_sources", "metric": "distinct_source_types", "operator": ">=", "target": 4},
        {"id": "dod_evidence", "metric": "gold_values_without_evidence", "operator": "=", "target": 0},
    ],
    "authority_policy": {
        "jurisdiction": "MX (synthetic fixture)",
        "trusted_publishers": [
            {"kind": "procurement portal", "domains": ["compras.example"], "rationale": "Synthetic stand-in"},
            {"kind": "tax authority", "domains": ["lista-fiscal.example"], "rationale": "Synthetic stand-in"},
        ],
        "unknown_source_action": "review",
    },
    "generated_by": GEN,
}

FACTORS = {
    "factors": [
        {"id": "legitimacy_signal", "label": "Legitimacy signal", "kind": "grounded",
         "description": "Official listings that question whether a supplier operates: tax-authority list stage, sanctions",
         "evidence": [{"url": "https://lista-fiscal.example/", "description": "Published list of RFCs by stage"}]},
        {"id": "procedure_type", "label": "Procurement procedure", "kind": "grounded",
         "description": "How the contract was awarded: open tender, restricted invitation or direct award",
         "evidence": [{"url": "https://compras.example/ayuda", "description": "Portal glossary of procedure types"}]},
        {"id": "economic_sector", "label": "Economic sector", "kind": "conceptual",
         "description": "What the supplier sells to the state, used to compare like with like",
         "evidence": [{"url": "https://compras.example/catalogo", "description": "Portal catalogue of goods and services"}]},
        {"id": "company_age", "label": "Company age at award", "kind": "conceptual",
         "description": "Time between incorporation and first award, a known screening signal",
         "evidence": [{"url": "https://registro-empresas.example/", "description": "Registry shows incorporation dates"}]},
        {"id": "buyer_level", "label": "Buying government level", "kind": "grounded",
         "description": "Federal, state or municipal buyer; changes which portal publishes the contract",
         "evidence": []},
    ],
    "generated_by": GEN,
}


def _node(id_, label, level, critic, parent=None, children=()):
    node = {"id": id_, "label": label, "level": level, "critic_label": critic}
    if parent:
        node["parent_id"] = parent
    if children:
        node["children"] = list(children)
    return node


ONTOLOGY = {
    "version": "v1",
    "prd_path": "01-scope/prd.json",
    "factors": FACTORS["factors"],
    "taxonomies": [
        {"factor_id": "economic_sector", "root_id": "sector", "root_label": "Economic sector", "soundness": 0.86,
         "coverage": 0.78, "children": [
             _node("obra_publica", "Public works", 1, "Good-Exclusive", "sector", [
                 _node("carreteras", "Roads", 2, "Good-Exclusive", "obra_publica"),
                 _node("edificacion", "Buildings", 2, "Good-Overlapping", "obra_publica"),
                 _node("agua", "Water systems", 2, "Good-Exclusive", "obra_publica")]),
             _node("salud", "Health", 1, "Good-Exclusive", "sector", [
                 _node("medicamentos", "Medicines", 2, "Good-Exclusive", "salud"),
                 _node("equipo_medico", "Medical equipment", 2, "Good-Exclusive", "salud"),
                 _node("insumos_medicos", "Medical supplies", 2, "Redundant", "salud")]),
             _node("tecnologia", "Technology", 1, "Good-Exclusive", "sector", [
                 _node("software", "Software", 2, "Good-Exclusive", "tecnologia"),
                 _node("telecom", "Telecommunications", 2, "Good-Overlapping", "tecnologia")]),
             _node("servicios", "Services", 1, "Good-Overlapping", "sector", [
                 _node("limpieza", "Cleaning", 2, "Good-Exclusive", "servicios"),
                 _node("vigilancia", "Security guards", 2, "Good-Exclusive", "servicios"),
                 _node("varios", "Miscellaneous", 2, "Bad", "servicios")])]},
        {"factor_id": "procedure_type", "root_id": "procedure", "root_label": "Procurement procedure",
         "soundness": 0.95, "coverage": 1.0, "children": [
             _node("licitacion_publica", "Open tender", 1, "Good-Exclusive", "procedure"),
             _node("invitacion_tres", "Invitation to at least three", 1, "Good-Exclusive", "procedure"),
             _node("adjudicacion_directa", "Direct award", 1, "Good-Exclusive", "procedure")]},
    ],
    "classes": [
        {"id": "Supplier", "aligned_to": "https://schema.org/Organization"},
        {"id": "Contract", "aligned_to": "https://standard.open-contracting.org/latest/en/schema/reference/#contract"},
        {"id": "Procedure", "aligned_to": "https://standard.open-contracting.org/latest/en/schema/reference/#tender"},
        {"id": "BuyingUnit", "aligned_to": "https://schema.org/GovernmentOrganization"},
        {"id": "Address", "aligned_to": "https://schema.org/PostalAddress"},
        {"id": "TaxListing", "aligned_to": "https://proveedor-abierto.example/vocab#TaxListing"},
        {"id": "Sanction", "aligned_to": "https://proveedor-abierto.example/vocab#Sanction"},
    ],
    "properties": [
        {"id": "legal_name", "datatype": "xsd:string", "aligned_to": "https://schema.org/legalName"},
        {"id": "tax_id", "datatype": "xsd:string", "aligned_to": "https://schema.org/taxID"},
        {"id": "address", "datatype": "Address", "aligned_to": "https://schema.org/address"},
        {"id": "founding_date", "datatype": "xsd:date", "aligned_to": "https://schema.org/foundingDate"},
        {"id": "tax_list_status", "datatype": "xsd:string"},
        {"id": "sanction_status", "datatype": "xsd:string"},
    ],
    "shacl_path": "02-ontology/schema/shapes.ttl",
    "generated_by": GEN,
}

SHAPES = """@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix schema: <https://schema.org/> .
@prefix pav: <https://proveedor-abierto.example/vocab#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Synthetic fixture shapes.
pav:SupplierShape a sh:NodeShape ;
    sh:targetClass schema:Organization ;
    sh:property [ sh:path schema:taxID ; sh:pattern "^[A-Z&]{3}[0-9]{6}[A-Z0-9]{3}$" ; sh:maxCount 1 ] ;
    sh:property [ sh:path schema:foundingDate ; sh:datatype xsd:date ; sh:maxCount 1 ] .
"""

PENDING = [
    ("01-scope", 1, "prd", "The global PRD is ready for review", ["01-scope/prd.json", "01-scope/prd.md"]),
    ("02-ontology/factors", 2, "factors", "Factors of variation proposed from the PRD", ["02-ontology/factors/factors.json"]),
    ("02-ontology", 2, "ontology", "Taxonomies expanded to depth 2 with a critic pass",
     ["02-ontology/ontology.json", "02-ontology/schema/shapes.ttl"]),
]


def pending_md(phase: int, checkpoint: str, reason: str, paths: list[str]) -> str:
    meta = {"phase": phase, "checkpoint": checkpoint, "requested_at": "2026-09-26T18:00:30+00:00", "reason": reason,
            "artifact_paths": paths, "generated_by": GEN}
    return f"---\n{yaml.safe_dump(meta, sort_keys=False)}---\n# Approval pending: {checkpoint} (synthetic fixture)\n\n{reason}.\n"


# Approve-before-submit (CONTRACT §12): one synthetic action request waiting for the approver. The screenshot key
# points at bytes that are never stored, so the review screen must cope with a missing capture.
ACTION_REQUEST = {
    "phase": 5, "checkpoint": "action", "requested_at": "2026-09-26T18:20:00+00:00",
    "reason": "The search form is not on the TDD's list of read-only actions, so the engine asks before submitting it",
    "artifact_paths": ["04-local/compras-example__supplier-identity/tdd.md"],
    "intended_action": "Submit the search form on compras.example with query 'Proveedor Ejemplo 07'",
    "risk_tier": "HIGH", "job_id": "job:fixture-action-0001",
    "screenshot_key": "sha256:" + hashlib.sha256(b"synthetic fixture: action request screenshot").hexdigest(),
    "generated_by": GEN,
}


def action_md(meta: dict) -> str:
    return (f"---\n{yaml.safe_dump(meta, sort_keys=False)}---\n# Approval pending: action (synthetic fixture)\n\n"
            f"{meta['intended_action']}.\n")


def write(case: Path, ontology: dict | None = None) -> None:
    files = {
        "01-scope/prd.json": json.dumps(PRD, indent=2),
        "02-ontology/factors/factors.json": json.dumps(FACTORS, indent=2),
        "02-ontology/ontology.json": json.dumps(ontology or ONTOLOGY, indent=2),
        "02-ontology/schema/shapes.ttl": SHAPES,
    }
    for phase_dir, phase, checkpoint, reason, paths in PENDING:
        files[f"{phase_dir}/APPROVAL_PENDING.md"] = pending_md(phase, checkpoint, reason, paths)
    files["05-actions/req-0001/APPROVAL_PENDING.md"] = action_md(ACTION_REQUEST)
    for rel, text in files.items():
        (case / rel).parent.mkdir(parents=True, exist_ok=True)
        (case / rel).write_text(text)

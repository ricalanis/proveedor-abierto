"""Synthetic, obviously fake gold export + case package for tests and local development.

    uv run pa-app fixtures [OUT_DIR]      # default: .cache/fixtures

Writes OUT_DIR/lake (bucket layout, CONTRACT section 4) and OUT_DIR/case (a synthetic case package the
journal can replay). Every name, tax ID and URL is fake: "Proveedor Ejemplo NN", RFC-shaped IDs starting
with ZZZ, and hosts on the reserved `.example` TLD. Never point this at the real `case/`.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from . import CORE_FIELDS, dod

CASE_ID = "fixture-case"
RUNS = ("run-fixture-0000", "run-fixture-0001")
TAXONOMY = {
    "obra-publica": ["carreteras", "edificacion", "agua"],
    "salud": ["medicamentos", "equipo-medico"],
    "tecnologia": ["software", "telecom"],
    "servicios": ["limpieza", "vigilancia"],
}
SOURCES = {
    # source_id: (host, source_type, objective_id, mode)
    "compras-example": ("compras.example", "procurement_portal", "supplier-identity", "S1"),
    "registro-example": ("registro-empresas.example", "company_registry", "company-profile", "S2"),
    "gaceta-example": ("gaceta.example", "official_gazette", "company-profile", "S2"),
    "lista-fiscal-example": ("lista-fiscal.example", "tax_authority_list", "tax-list-status", "D0"),
    "sanciones-example": ("sanciones.example", "sanctions_registry", "sanction-status", "D1"),
}
FIELD_SOURCE = {
    "legal_name": "compras-example",
    "tax_id": "compras-example",
    "address": "registro-example",
    "founding_date": "registro-example",
    "legal_representative": "registro-example",
    "tax_list_status": "lista-fiscal-example",
    "sanction_status": "sanciones-example",
}
PROCEDURES = ["licitacion_publica", "invitacion_tres", "adjudicacion_directa"]
BUYERS = ["Dependencia Ejemplo A", "Dependencia Ejemplo B", "Dependencia Ejemplo C"]


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


class _Bronze:
    def __init__(self, lake: Path):
        self.lake = lake

    def put(self, data: bytes, content_type: str, url: str) -> str:
        key = _sha(data)
        path = self.lake / "bronze" / "sha256" / key.split(":", 1)[1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        meta = {"content_type": content_type, "url": url, "captured_at": None, "source_id": None, "step_id": None}
        path.with_name(path.name + ".meta.json").write_text(json.dumps(meta))
        return key

    def screenshot(self, host: str, label: str, value: str) -> str:
        esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;")
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
            '<rect width="640" height="360" fill="#f4f4f1"/>'
            '<rect x="0" y="0" width="640" height="36" fill="#2b2b2b"/>'
            f'<text x="16" y="24" font-family="monospace" font-size="14" fill="#f4f4f1">https://{esc(host)}</text>'
            '<text x="16" y="84" font-family="monospace" font-size="13" fill="#9a3b10">'
            "FIXTURE SINTÉTICA · NO ES UN REGISTRO REAL</text>"
            f'<text x="16" y="140" font-family="sans-serif" font-size="15" fill="#555">{esc(label)}</text>'
            '<rect x="12" y="152" width="616" height="44" fill="#ffe28a"/>'
            f'<text x="20" y="181" font-family="sans-serif" font-size="20" fill="#111">{esc(value)}</text>'
            "</svg>"
        )
        return self.put(svg.encode(), "image/svg+xml", f"https://{host}")

    def page(self, host: str, path: str, label: str, value: str) -> str:
        html = f"<!-- synthetic fixture --><html><body><h1>{host}{path}</h1><dl><dt>{label}</dt><dd>{value}</dd></dl>"
        return self.put(html.encode(), "text/html", f"https://{host}{path}")


def _evidence(bronze: _Bronze, source_id: str, path: str, label: str, value: str, captured_at: str) -> dict:
    host, source_type, _, _ = SOURCES[source_id]
    return {
        "url": f"https://{host}{path}",
        "bronze_key": bronze.page(host, path, label, value),
        "selector": f"dl > dt:has-text('{label}') + dd",
        "screenshot_key": bronze.screenshot(host, label, value),
        "captured_at": captured_at,
        "source_id": source_id,
        "source_type": source_type,
    }


def _suppliers(rng: random.Random, n: int) -> list[dict]:
    """Base facts for n fake suppliers (before rendering into the gold shape)."""
    leaves = [f"sector/{a}/{b}" for a, bs in TAXONOMY.items() for b in bs if b not in ("agua", "vigilancia")]
    shared_addresses = {i: (i // 3) for i in range(12)}  # suppliers 0-11 share addresses in triples
    shared_reps = {12: "07", 13: "07", 20: "11", 21: "11"}
    rows = []
    for i in range(n):
        nn = i + 1
        founded = date(2004, 1, 1) + timedelta(days=rng.randrange(0, 7000))
        if i % 9 == 4:  # some companies created just before their first award
            founded = date(2025, 6, 1) + timedelta(days=rng.randrange(0, 60))
        addr_n = shared_addresses.get(i, 100 + i)
        rows.append(
            {
                "i": i,
                "id": f"sup:fixture-{nn:03d}",
                "legal_name": f"Proveedor Ejemplo {nn:02d} S.A. de C.V.",
                "tax_id": f"ZZZ{founded:%y%m%d}Z{nn % 100:02d}",
                "address": f"Calle Ficticia {addr_n}, Col. Ejemplo, Ciudad Ejemplo, C.P. 00{addr_n:03d}",
                "founding_date": founded.isoformat(),
                "legal_representative": f"Representante Ficticio {shared_reps.get(i, f'{nn + 30:02d}')}",
                "tax_list_status": "definitivo" if i % 17 == 3 else ("presunto" if i % 23 == 5 else "no listado"),
                "sanction_status": "sancionado" if i % 19 == 7 else "sin sancion",
                "classified_as": [leaves[i % len(leaves)]],
            }
        )
    return rows


def _contracts(rng: random.Random, suppliers: list[dict]) -> list[dict]:
    contracts = []
    for k in range(len(suppliers) + 20):
        primary = suppliers[k % len(suppliers)]
        ids = [primary["id"]]
        if k % 5 == 0:  # procedures with several participants
            ids.append(suppliers[(k + 1) % len(suppliers)]["id"])
        if primary["i"] < 12 and k < len(suppliers):  # shared-address triples bid together
            ids = [s["id"] for s in suppliers if s["i"] // 3 == primary["i"] // 3 and s["i"] < 12]
        awarded = date(2025, 8, 1) + timedelta(days=rng.randrange(0, 300))
        contracts.append(
            {
                "id": f"con:fixture-{k + 1:04d}",
                "title": f"Contrato de ejemplo {k + 1:04d} (sintético)",
                "amount": round(rng.uniform(80_000, 25_000_000), 2),
                "currency": "MXN",
                "date": awarded.isoformat(),
                "buyer": BUYERS[k % len(BUYERS)],
                "procedure_type": PROCEDURES[k % len(PROCEDURES)],
                "supplier_ids": sorted(set(ids)),
                "evidence": [],
            }
        )
    return contracts


def _render_run(
    run_id: str,
    base: list[dict],
    contracts: list[dict],
    bronze: _Bronze,
    rng: random.Random,
    degrade: float,
) -> tuple[list[dict], list[dict], dict]:
    """Build suppliers.jsonl rows, trace rows and metrics for one run. `degrade` = share of values left missing."""
    ts0 = datetime(2026, 9, 26, 18, 0, tzinfo=UTC)
    trace: list[dict] = []

    def step(phase, parent, observed, requested, executed, evaluated, **kw) -> dict:
        s = {
            "step_id": f"step:{run_id}:{len(trace) + 1:05d}",
            "run_id": run_id,
            "phase": phase,
            "source_id": kw.get("source_id"),
            "objective_id": kw.get("objective_id"),
            "tdd_path": kw.get("tdd_path"),
            "mode": kw.get("mode", "S1"),
            "observed": observed,
            "requested": requested,
            "executed": executed,
            "evaluated": evaluated,
            "parent_step_id": parent,
            "value_ids": kw.get("value_ids", []),
            "ts": (ts0 + timedelta(seconds=len(trace) * 7)).isoformat(),
        }
        trace.append(s)
        return s

    p1 = step(1, None, "case/brief.md", "draft personas, jobs and a global PRD with a DoD", "wrote 01-scope/prd.md",
              "PRD approved", mode="S1")
    p2 = step(2, p1["step_id"], "01-scope/prd.md", "derive factors, taxonomies and schema",
              "wrote 02-ontology/versions/v1.md", "ontology v1 approved", mode="S1")
    tdd_steps: dict[str, dict] = {}
    for source_id, (host, _stype, objective, mode) in SOURCES.items():
        p3 = step(3, p2["step_id"], f"search results mention {host}", f"map {host} for objective {objective}",
                  f"site graph for {host}", "source passes authority check", source_id=source_id,
                  objective_id=objective, mode="S1")
        tdd = f"04-local/{source_id}__{objective}/tdd.md"
        tdd_steps[source_id] = step(4, p3["step_id"], f"probe of {host}", "negotiate a TDD", f"agreed {tdd}",
                                    "TDD agreed", source_id=source_id, objective_id=objective, tdd_path=tdd,
                                    mode="S1")

    mode_counts = {"D0": 0, "D1": 0, "S1": 0, "S2": 0}
    for s in trace:
        mode_counts[s["mode"]] += 1
    suppliers = []
    for row in base:
        nn = row["i"] + 1
        captured = (ts0 + timedelta(minutes=5 + row["i"])).isoformat()
        fields: dict[str, dict] = {}
        by_source: dict[str, list[str]] = {}
        for name, source_id in FIELD_SOURCE.items():
            vid = f"val:{run_id[-4:]}-{nn:03d}-{name}"
            missing = name != "legal_name" and rng.random() < degrade
            if missing:
                fields[name] = {"value_id": vid, "value": None, "confidence": 0.0, "status": "missing", "evidence": []}
                continue
            value = row[name]
            path = f"/proveedor/{row['tax_id']}" if source_id != "lista-fiscal-example" else "/listado-completo.csv"
            ev = [_evidence(bronze, source_id, path, name.replace("_", " "), value, captured)]
            status, conf = "gold", round(rng.uniform(0.86, 0.99), 2)
            if name == "founding_date" and row["i"] % 13 == 6:  # the gazette disagrees with the registry
                other = (date.fromisoformat(value) + timedelta(days=365)).isoformat()
                ev.append(_evidence(bronze, "gaceta-example", f"/edicion/{nn:03d}.pdf", "fecha de constitucion",
                                    other, captured))
                status, conf = "conflict", 0.55
            elif name == "founding_date" and row["i"] % 7 == 2:  # corroborated by the gazette
                ev.append(_evidence(bronze, "gaceta-example", f"/edicion/{nn:03d}.pdf", "fecha de constitucion",
                                    value, captured))
            fields[name] = {"value_id": vid, "value": value, "confidence": conf, "status": status, "evidence": ev}
            for e in ev:
                by_source.setdefault(e["source_id"], []).append(vid)
        for source_id, vids in by_source.items():
            host, _st, objective, mode = SOURCES[source_id]
            step(5, tdd_steps[source_id]["step_id"], f"page for {row['tax_id']} on {host}",
                 f"extract {', '.join(sorted({v.rsplit('-', 1)[-1] for v in vids}))}",
                 f"emit.observation x{len(vids)}", "passed SHACL, promoted to gold",
                 source_id=source_id, objective_id=objective,
                 tdd_path=tdd_steps[source_id]["tdd_path"], mode=mode, value_ids=vids)
            mode_counts[mode] += 1
        suppliers.append({"id": row["id"], "classified_as": row["classified_as"], "fields": fields,
                          "flags": [], "links": [],
                          "contract_ids": [c["id"] for c in contracts if row["id"] in c["supplier_ids"]]})

    _add_flags_and_links(suppliers, contracts)
    metrics = dod.compute(suppliers)
    used = {n for s in suppliers for n in s["classified_as"]}
    level1 = {n.split("/")[1] for n in used}
    metrics.update(
        run_id=run_id,
        level_ratio_coverage={
            "sector": [
                round(len(level1) / len(TAXONOMY), 4),
                round(len(used) / sum(len(v) for v in TAXONOMY.values()), 4),
            ]
        },
        mode_counts=mode_counts,
        jobs={"ok": sum(1 for s in trace if s["phase"] == 5), "failed_by_reason": {"timeout": 3, "captcha_stop": 1}},
    )
    return suppliers, trace, metrics


def _add_flags_and_links(suppliers: list[dict], contracts: list[dict]) -> None:
    def val(s, name):
        f = s["fields"].get(name) or {}
        return f.get("value") if f.get("status") in ("gold", "conflict") else None

    first_award: dict[str, str] = {}
    for c in sorted(contracts, key=lambda c: c["date"]):
        for sid in c["supplier_ids"]:
            first_award.setdefault(sid, c["date"])
    procedure_peers: dict[str, set[str]] = {}
    for c in contracts:
        for sid in c["supplier_ids"]:
            procedure_peers.setdefault(sid, set()).update(x for x in c["supplier_ids"] if x != sid)

    by_id = {s["id"]: s for s in suppliers}
    for s in suppliers:
        f = s["fields"]
        status = val(s, "tax_list_status")
        if status in ("presunto", "definitivo"):
            s["flags"].append({
                "rule_id": "tax_list_listed",
                "label": "Listed on the tax authority's fake-invoice list",
                "explanation": f"The tax authority's published list shows this RFC with status '{status}'. "
                               "A listing is a signal to verify, not proof of wrongdoing; 'presunto' means the "
                               "company can still rebut it.",
                "evidence_value_ids": [f["tax_list_status"]["value_id"], f["tax_id"]["value_id"]],
            })
        if val(s, "sanction_status") == "sancionado":
            s["flags"].append({
                "rule_id": "sanctioned_supplier",
                "label": "Appears in the sanctioned-supplier registry",
                "explanation": "The sanctions registry lists this company. Check the sanction's dates and scope "
                               "against the contract dates before drawing conclusions.",
                "evidence_value_ids": [f["sanction_status"]["value_id"]],
            })
        founded = val(s, "founding_date")
        if founded and s["id"] in first_award:
            days = (date.fromisoformat(first_award[s["id"]]) - date.fromisoformat(founded)).days
            if 0 <= days <= 365:
                s["flags"].append({
                    "rule_id": "founded_shortly_before_award",
                    "label": "Created shortly before its first award",
                    "explanation": f"Founded {days} days before its first recorded contract. New companies win "
                                   "contracts legitimately too; compare with the procedure's requirements.",
                    "evidence_value_ids": [f["founding_date"]["value_id"]],
                })
        for peer_id in sorted(procedure_peers.get(s["id"], ())):
            peer = by_id.get(peer_id)
            if not peer:
                continue
            s["links"].append({"type": "same_procedure", "target": peer_id, "via_value_id": f["legal_name"]["value_id"]})
            for field_name, link_type in (("address", "shared_address"), ("legal_representative", "shared_representative")):
                mine, theirs = val(s, field_name), val(peer, field_name)
                if mine and mine == theirs:
                    s["links"].append({"type": link_type, "target": peer_id, "via_value_id": f[field_name]["value_id"]})
                    if link_type == "shared_address" and not any(x["rule_id"] == "shared_address_bidders" for x in s["flags"]):
                        s["flags"].append({
                            "rule_id": "shared_address_bidders",
                            "label": "Shares an address with another bidder in the same procedure",
                            "explanation": "Two participants in one procedure declare the same address. This can "
                                           "indicate simulated competition, or simply a shared office building.",
                            "evidence_value_ids": [f["address"]["value_id"], peer["fields"]["address"]["value_id"]],
                        })
        for other in suppliers:  # shared representative across procedures too
            if other is not s and val(s, "legal_representative") and \
                    val(s, "legal_representative") == val(other, "legal_representative") and \
                    not any(l["type"] == "shared_representative" and l["target"] == other["id"] for l in s["links"]):
                s["links"].append({"type": "shared_representative", "target": other["id"],
                                   "via_value_id": f["legal_representative"]["value_id"]})


CASE_FILES = {
    "brief.md": "# Brief (synthetic fixture)\n\nWho receives public money through government contracts, and are "
                "they legitimate companies?\n",
    "01-scope/prd.md": "# Global PRD (synthetic fixture)\n\n## Personas\n- Investigative journalist\n"
                       "- Civil-society watchdog\n\n## Definition of done\n- >= 50 suppliers at >= 80% of core "
                       "fields in gold\n- >= 4 distinct source types\n- every gold value has evidence\n",
    "02-ontology/versions/v1.md": "# Ontology v1 (synthetic fixture)\n\nClasses: Supplier, Contract, "
                                  "Procedure, BuyingUnit, Address, LegalRepresentative, TaxListing, Sanction.\n",
    "02-ontology/taxonomies/sector.yaml": json.dumps({"sector": TAXONOMY}, indent=2) + "\n",
    "01-scope/APPROVAL_PENDING.md": "# Approval pending: global PRD (synthetic fixture)\n\nReview "
                                    "`01-scope/prd.md`, then approve to resume the run.\n",
}


def generate(out: Path, n_suppliers: int = 60, seed: int = 7) -> Path:
    """Write OUT/lake and OUT/case. Returns the lake root (use as PA_GOLD_DIR)."""
    lake, case = out / "lake", out / "case"
    bronze = _Bronze(lake)
    rng = random.Random(seed)
    base = _suppliers(rng, n_suppliers)
    contracts = _contracts(rng, base)
    for run_id, count, degrade in ((RUNS[0], n_suppliers - 6, 0.12), (RUNS[1], n_suppliers, 0.03)):
        suppliers, trace, metrics = _render_run(run_id, base[:count], contracts, bronze, random.Random(seed + count),
                                                degrade)
        run_contracts = [c for c in contracts if any(sid in {s["id"] for s in suppliers} for sid in c["supplier_ids"])]
        run_dir = lake / "gold" / CASE_ID / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        for name, rows in (("suppliers", suppliers), ("contracts", run_contracts), ("trace", trace)):
            (run_dir / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
        metrics_copy = case / "runs" / run_id / "metrics.json"
        metrics_copy.parent.mkdir(parents=True, exist_ok=True)
        metrics_copy.write_text(json.dumps(metrics, indent=2))
    (lake / "gold" / CASE_ID / "latest.json").write_text(json.dumps({"run_id": RUNS[1]}))
    for rel, text in CASE_FILES.items():
        (case / rel).parent.mkdir(parents=True, exist_ok=True)
        (case / rel).write_text(text)
    for source_id, (host, stype, objective, mode) in SOURCES.items():
        tdd = case / "04-local" / f"{source_id}__{objective}" / "tdd.md"
        tdd.parent.mkdir(parents=True, exist_ok=True)
        tdd.write_text(f"# TDD: {host} / {objective} (synthetic fixture)\n\n- source type: {stype}\n"
                       f"- mode: {mode}\n- allowed domains: {host}\n")
    return lake


assert set(CORE_FIELDS) <= set(FIELD_SOURCE)

"""Open exports of a gold run: CSV, an OCDS 1.1 release package, and RDF Turtle.

All functions are pure over a `gold.Run`; pass `supplier_ids` to export a subset (e.g. a watchlist).

OCDS note: the ocid prefix `ocds-pa0000` is a placeholder, not a prefix registered with the Open Contracting
Partnership. Register one before publishing these releases anywhere official.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from urllib.parse import quote

from . import CORE_FIELDS
from .gold import Run

EXPORT_FIELDS = (*CORE_FIELDS, "legal_representative")
OCID_PREFIX = "ocds-pa0000"


def _selected(run: Run, supplier_ids) -> list[dict]:
    if supplier_ids is None:
        return list(run.suppliers)
    wanted = set(supplier_ids)
    return [s for s in run.suppliers if s["id"] in wanted]


def _value(supplier: dict, name: str):
    f = (supplier.get("fields") or {}).get(name) or {}
    return f.get("value") if f.get("status") in ("gold", "conflict") else None


# ---------------------------------------------------------------- CSV


def to_csv(run: Run, supplier_ids=None) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    header = ["id"]
    for name in EXPORT_FIELDS:
        header += [name, f"{name}_status", f"{name}_confidence", f"{name}_source_url"]
    header += ["flags", "contracts"]
    writer.writerow(header)
    for s in _selected(run, supplier_ids):
        fields = s.get("fields") or {}
        row = [s["id"]]
        for name in EXPORT_FIELDS:
            f = fields.get(name) or {}
            ev = f.get("evidence") or []
            row += [
                "" if f.get("value") is None else f["value"],
                f.get("status", "missing"),
                "" if f.get("confidence") is None else f["confidence"],
                ev[0]["url"] if ev else "",
            ]
        row += [";".join(fl["rule_id"] for fl in s.get("flags") or []), len(s.get("contract_ids") or [])]
        writer.writerow(row)
    return buf.getvalue()


# ---------------------------------------------------------------- OCDS


def _buyer_id(name: str) -> str:
    return "buyer:" + quote(name.lower().replace(" ", "-"), safe="-._")


def _supplier_party(s: dict) -> dict:
    party: dict = {"id": s["id"], "name": _value(s, "legal_name") or s["id"], "roles": ["supplier"]}
    tax_id = _value(s, "tax_id")
    if tax_id:
        party["identifier"] = {"scheme": "MX-RFC", "id": str(tax_id), "legalName": party["name"]}
    address = _value(s, "address")
    if address:
        party["address"] = {"streetAddress": str(address)}
    return party


def to_ocds(run: Run, supplier_ids=None, publisher: str = "Proveedor Abierto (Ontofill)") -> dict:
    selected = {s["id"] for s in _selected(run, supplier_ids)}
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    releases = []
    for c in run.contracts:
        if not selected.intersection(c.get("supplier_ids") or []):
            continue
        local = c["id"].removeprefix("con:")
        buyer = {"id": _buyer_id(c["buyer"]), "name": c["buyer"]}
        suppliers = [run.suppliers_by_id[sid] for sid in c["supplier_ids"] if sid in run.suppliers_by_id]
        value = {"amount": c["amount"], "currency": c["currency"]}
        award_id = f"{local}-award"
        releases.append({
            "ocid": f"{OCID_PREFIX}-{local}",
            "id": f"{local}-{run.run_id}",
            "date": f"{c['date']}T00:00:00Z" if len(c["date"]) == 10 else c["date"],
            "tag": ["contract"],
            "initiationType": "tender",
            "parties": [{**buyer, "roles": ["buyer"]}] + [_supplier_party(s) for s in suppliers],
            "buyer": buyer,
            "tender": {"id": f"{local}-tender", "procurementMethodDetails": c["procedure_type"]},
            "awards": [{
                "id": award_id,
                "suppliers": [{"id": s["id"], "name": _value(s, "legal_name") or s["id"]} for s in suppliers],
                "value": value,
                "date": f"{c['date']}T00:00:00Z" if len(c["date"]) == 10 else c["date"],
            }],
            "contracts": [{
                "id": local,
                "awardID": award_id,
                "title": c["title"],
                "value": value,
                "dateSigned": f"{c['date']}T00:00:00Z" if len(c["date"]) == 10 else c["date"],
            }],
        })
    return {
        "uri": f"https://proveedor-abierto.example/export/{run.case_id}/{run.run_id}/ocds.json",
        "version": "1.1",
        "publishedDate": now,
        "publisher": {"name": publisher},
        "releases": releases,
    }


# ---------------------------------------------------------------- Turtle

PREFIXES = """@prefix pa: <https://proveedor-abierto.example/id/> .
@prefix pav: <https://proveedor-abierto.example/vocab#> .
@prefix schema: <https://schema.org/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""

SUPPLIER_PREDICATES = {
    "legal_name": "schema:legalName",
    "tax_id": "schema:taxID",
    "address": "schema:address",
    "founding_date": "schema:foundingDate",
    "tax_list_status": "pav:taxListStatus",
    "sanction_status": "pav:sanctionStatus",
    "legal_representative": "pav:legalRepresentative",
}


def turtle_string(value) -> str:
    s = str(value)
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return f'"{s}"'


def _iri(url: str) -> str:
    # Escape characters that are illegal inside a Turtle IRIREF.
    return "<" + quote(url, safe=":/?#[]@!$&'()*+,;=%-._~") + ">"


def _node(identifier: str) -> str:
    """`sup:fixture-001` -> `pa:sup/fixture-001` (prefix becomes a path segment, rest percent-encoded)."""
    kind, _, rest = identifier.partition(":")
    return f"<https://proveedor-abierto.example/id/{quote(kind, safe='')}/{quote(rest, safe='-._~')}>"


def _literal(name: str, value) -> str:
    if name == "founding_date" and isinstance(value, str) and len(value) == 10:
        return f"{turtle_string(value)}^^xsd:date"
    return turtle_string(value)


def _block(subject: str, props: list[tuple[str, str]]) -> str:
    body = " ;\n    ".join(f"{p} {o}" for p, o in props)
    return f"{subject}\n    {body} .\n"


def to_turtle(run: Run, supplier_ids=None) -> str:
    out = [PREFIXES]
    selected = _selected(run, supplier_ids)
    selected_ids = {s["id"] for s in selected}
    for s in selected:
        subj = _node(s["id"])
        props = [("a", "schema:Organization")]
        observations = []
        for name, f in (s.get("fields") or {}).items():
            if f.get("status") not in ("gold", "conflict") or f.get("value") is None:
                continue
            pred = SUPPLIER_PREDICATES.get(name, f"pav:{quote(name, safe='_')}")
            props.append((pred, _literal(name, f["value"])))
            if f.get("value_id"):
                obs = _node(f["value_id"])
                props.append(("pav:observation", obs))
                oprops = [
                    ("a", "pav:Observation"),
                    ("pav:field", turtle_string(name)),
                    ("pav:value", _literal(name, f["value"])),
                    ("pav:status", turtle_string(f["status"])),
                    ("pav:confidence", f'"{float(f.get("confidence") or 0):.4f}"^^xsd:decimal'),
                ]
                for e in f.get("evidence") or []:
                    if e.get("url", "").startswith(("http://", "https://")):
                        oprops.append(("prov:wasDerivedFrom", _iri(e["url"])))
                    if e.get("bronze_key"):
                        oprops.append(("pav:bronzeKey", turtle_string(e["bronze_key"])))
                    if e.get("screenshot_key"):
                        oprops.append(("pav:screenshotKey", turtle_string(e["screenshot_key"])))
                    if e.get("captured_at"):
                        oprops.append(("prov:generatedAtTime", f"{turtle_string(e['captured_at'])}^^xsd:dateTime"))
                observations.append(_block(obs, oprops))
        for i, fl in enumerate(s.get("flags") or []):
            sig = _node(f"signal:{s['id'].removeprefix('sup:')}-{i}")
            props.append(("pav:signal", sig))
            sprops = [("a", "pav:Signal"), ("pav:rule", turtle_string(fl["rule_id"])),
                      ("rdfs:label", turtle_string(fl["label"])),
                      ("rdfs:comment", turtle_string(fl.get("explanation", "")))]
            sprops += [("pav:evidence", _node(v)) for v in fl.get("evidence_value_ids") or []]
            observations.append(_block(sig, sprops))
        out.append(_block(subj, props))
        out.extend(observations)
    for c in run.contracts:
        if not selected_ids.intersection(c.get("supplier_ids") or []):
            continue
        props = [
            ("a", "pav:Contract"),
            ("schema:name", turtle_string(c["title"])),
            ("pav:amount", f'"{c["amount"]}"^^xsd:decimal'),
            ("pav:currency", turtle_string(c["currency"])),
            ("pav:buyer", turtle_string(c["buyer"])),
            ("pav:procedureType", turtle_string(c["procedure_type"])),
            ("pav:date", f"{turtle_string(c['date'])}^^xsd:date"),
        ]
        props += [("pav:supplier", _node(sid)) for sid in c["supplier_ids"]]
        out.append(_block(_node(c["id"]), props))
    return "\n".join(out)

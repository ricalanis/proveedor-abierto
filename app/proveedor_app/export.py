"""Open exports of a gold run: CSV, RDF Turtle, and (when the ontology aligns to it) an OCDS 1.1 release package.

Generic over the case's ontology (CONTRACT v0.7 §11): columns and predicates come from its classes and
properties, using each property's `aligned_to` IRI when it has one. Pass `ids` to export a subset of primary
entities (e.g. a watchlist).

OCDS note: the ocid prefix `ocds-pa0000` is a placeholder, not a prefix registered with the Open Contracting
Partnership. Register one before publishing these releases anywhere official.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from urllib.parse import quote

from .gold import Run

OCID_PREFIX = "ocds-pa0000"
OCDS_MARK = "open-contracting"


def _selected(run: Run, ids) -> list[dict]:
    if ids is None:
        return list(run.primary)
    wanted = set(ids)
    return [e for e in run.primary if e["id"] in wanted]


def _value(entity: dict, prop: str | None):
    v = ((entity.get("properties") or {}).get(prop or "") or {})
    return v.get("value") if v.get("status") in ("gold", "conflict") else None


def _linked(run: Run, entities: list[dict], other_class_only: bool = True) -> list[dict]:
    out, seen = [], set()
    for e in entities:
        for link in e.get("links") or []:
            t = run.entities_by_id.get(link.get("target"))
            if t and t["id"] not in seen and (not other_class_only or t.get("class") != e.get("class")):
                seen.add(t["id"])
                out.append(t)
    return out


# ---------------------------------------------------------------- CSV


def to_csv(run: Run, ids=None) -> str:
    d = run.domain
    props = [p.id for p in d.props()]
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    header = ["id", "class"]
    for name in props:
        header += [name, f"{name}_status", f"{name}_confidence", f"{name}_source_url"]
    header += ["flags", "links"]
    writer.writerow(header)
    for e in _selected(run, ids):
        values = e.get("properties") or {}
        row = [e["id"], e.get("class")]
        for name in props:
            f = values.get(name) or {}
            ev = f.get("evidence") or []
            row += ["" if f.get("value") is None else f["value"], f.get("status", "missing"),
                    "" if f.get("confidence") is None else f["confidence"], ev[0]["url"] if ev else ""]
        row += [";".join(fl["rule_id"] for fl in e.get("flags") or []), len(e.get("links") or [])]
        writer.writerow(row)
    return buf.getvalue()


# ---------------------------------------------------------------- OCDS


def _ocds_contract_class(run: Run) -> str | None:
    for cid, c in run.domain.classes.items():
        if OCDS_MARK in str(c.get("aligned_to") or "") and "contract" in str(c.get("aligned_to") or ""):
            return cid
    return None


def ocds_available(run: Run) -> bool:
    return _ocds_contract_class(run) is not None


def _by_name(entity: dict, *names: str):
    """A contract property by its OCDS-ish name, whatever the ontology called it (id or aligned_to suffix)."""
    values = entity.get("properties") or {}
    for key, v in values.items():
        if key.lower() in names and isinstance(v, dict):
            return v.get("value")
    return None


def to_ocds(run: Run, ids=None, publisher: str = "Proveedor Abierto (Ontofill)") -> dict:
    d = run.domain
    contract_class = _ocds_contract_class(run)
    selected = _selected(run, ids)
    selected_ids = {e["id"] for e in selected}
    scheme = (d.classes.get(d.primary_class) or {}).get("identifier_scheme")
    address_prop = next((p.id for p in d.props() if str(p.aligned_to or "").endswith("/address")), None)
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    releases = []
    for c in (x for x in run.entities if x.get("class") == contract_class):
        parties_ids = {link["target"] for link in c.get("links") or []} | {
            e["id"] for e in run.primary if any(link.get("target") == c["id"] for link in e.get("links") or [])}
        if not selected_ids & parties_ids:
            continue
        suppliers = [run.entities_by_id[i] for i in sorted(parties_ids)
                     if i in run.entities_by_id and run.entities_by_id[i].get("class") == d.primary_class]
        local = c["id"].split(":", 1)[-1]
        date = str(_by_name(c, "date", "datesigned") or "")
        iso = f"{date}T00:00:00Z" if len(date) == 10 else date or None
        buyer_name = _by_name(c, "buyer")
        buyer = {"id": "buyer:" + quote(str(buyer_name or "unknown").lower().replace(" ", "-"), safe="-._"),
                 "name": buyer_name}
        value = {"amount": _by_name(c, "amount", "value"), "currency": _by_name(c, "currency")}

        def party(e: dict) -> dict:
            p = {"id": e["id"], "name": run.title(e), "roles": ["supplier"]}
            ident = run.identifier(e)
            if ident and scheme:
                p["identifier"] = {"scheme": scheme, "id": str(ident), "legalName": p["name"]}
            addr = _value(e, address_prop)
            if addr:
                p["address"] = {"streetAddress": str(addr)}
            return p

        releases.append({
            "ocid": f"{OCID_PREFIX}-{local}", "id": f"{local}-{run.run_id}", "date": iso, "tag": ["contract"],
            "initiationType": "tender",
            "parties": [{**buyer, "roles": ["buyer"]}] + [party(e) for e in suppliers],
            "buyer": buyer,
            "tender": {"id": f"{local}-tender", "procurementMethodDetails": _by_name(c, "procedure_type")},
            "awards": [{"id": f"{local}-award", "suppliers": [{"id": e["id"], "name": run.title(e)} for e in suppliers],
                        "value": value, "date": iso}],
            "contracts": [{"id": local, "awardID": f"{local}-award", "title": _by_name(c, "title"), "value": value,
                           "dateSigned": iso}],
        })
    return {"uri": f"https://proveedor-abierto.example/export/{run.case_id}/{run.run_id}/ocds.json", "version": "1.1",
            "publishedDate": now, "publisher": {"name": publisher}, "releases": releases}


# ---------------------------------------------------------------- Turtle

PREFIXES = """@prefix pa: <https://proveedor-abierto.example/id/> .
@prefix pav: <https://proveedor-abierto.example/vocab#> .
@prefix schema: <https://schema.org/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""


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


def _term(aligned: str | None, local: str) -> str:
    return _iri(aligned) if aligned and aligned.startswith(("http://", "https://")) else f"pav:{quote(local, safe='_')}"


def _literal(datatype: str, value) -> str:
    if datatype.startswith("xsd:") and datatype != "xsd:string":
        return f"{turtle_string(value)}^^{datatype}"
    return turtle_string(value)


def _block(subject: str, props: list[tuple[str, str]]) -> str:
    body = " ;\n    ".join(f"{p} {o}" for p, o in props)
    return f"{subject}\n    {body} .\n"


def _entity_blocks(run: Run, e: dict) -> list[str]:
    d = run.domain
    cls = e.get("class") or ""
    declared = {p.id: p for p in d.props(cls)}
    subj = _node(e["id"])
    props = [("a", _term((d.classes.get(cls) or {}).get("aligned_to"), cls))]
    extra = []
    for name, f in (e.get("properties") or {}).items():
        if not isinstance(f, dict) or f.get("status") not in ("gold", "conflict") or f.get("value") is None:
            continue
        p = declared.get(name)
        datatype = p.datatype if p else ""
        props.append((_term(p.aligned_to if p else None, name), _literal(datatype, f["value"])))
        if f.get("value_id"):
            obs = _node(f["value_id"])
            props.append(("pav:observation", obs))
            oprops = [("a", "pav:Observation"), ("pav:property", turtle_string(name)),
                      ("pav:value", _literal(datatype, f["value"])), ("pav:status", turtle_string(f["status"])),
                      ("pav:confidence", f'"{float(f.get("confidence") or 0):.4f}"^^xsd:decimal')]
            for ev in f.get("evidence") or []:
                if ev.get("url", "").startswith(("http://", "https://")):
                    oprops.append(("prov:wasDerivedFrom", _iri(ev["url"])))
                if ev.get("bronze_key"):
                    oprops.append(("pav:bronzeKey", turtle_string(ev["bronze_key"])))
                if ev.get("screenshot_key"):
                    oprops.append(("pav:screenshotKey", turtle_string(ev["screenshot_key"])))
                if ev.get("captured_at"):
                    oprops.append(("prov:generatedAtTime", f"{turtle_string(ev['captured_at'])}^^xsd:dateTime"))
            extra.append(_block(obs, oprops))
    for link in e.get("links") or []:
        if link.get("target") in run.entities_by_id:
            props.append((_term((d.relations.get(link.get("property")) or {}).get("aligned_to"),
                                link.get("property") or "related"), _node(link["target"])))
    for i, fl in enumerate(e.get("flags") or []):
        sig = _node(f"signal:{e['id'].split(':', 1)[-1]}-{i}")
        props.append(("pav:signal", sig))
        sprops = [("a", "pav:Signal"), ("pav:rule", turtle_string(fl["rule_id"])),
                  ("rdfs:label", turtle_string(fl["label"])), ("rdfs:comment", turtle_string(fl.get("explanation", "")))]
        sprops += [("pav:evidence", _node(v)) for v in fl.get("evidence_value_ids") or []]
        extra.append(_block(sig, sprops))
    return [_block(subj, props), *extra]


def to_turtle(run: Run, ids=None) -> str:
    selected = _selected(run, ids)
    out = [PREFIXES]
    for e in selected + _linked(run, selected):
        out.extend(_entity_blocks(run, e))
    return "\n".join(out)

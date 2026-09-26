import csv
import io
import json

import pytest
from proveedor_app import export

rdflib = pytest.importorskip("rdflib")
SCHEMA = rdflib.Namespace("https://schema.org/")
PAV = rdflib.Namespace("https://proveedor-abierto.example/vocab#")


def test_csv_all_and_subset(store):
    run = store.run()
    text = export.to_csv(run)
    assert len(text.strip().splitlines()) == 61
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 60 and rows[0]["id"] == run.suppliers[0]["id"]
    assert rows[0]["legal_name_source_url"].startswith("https://")
    subset = list(csv.DictReader(io.StringIO(export.to_csv(run, ["sup:fixture-001", "sup:fixture-002"]))))
    assert [r["id"] for r in subset] == ["sup:fixture-001", "sup:fixture-002"]


def test_ocds_package(store):
    run = store.run()
    pkg = export.to_ocds(run)
    json.dumps(pkg)
    assert pkg["version"] == "1.1" and pkg["releases"]
    ocids = [r["ocid"] for r in pkg["releases"]]
    assert len(ocids) == len(set(ocids)) == len(run.contracts)
    for rel in pkg["releases"]:
        roles = {p["id"]: p["roles"] for p in rel["parties"]}
        assert roles[rel["buyer"]["id"]] == ["buyer"]
        for award in rel["awards"]:
            for sup in award["suppliers"]:
                assert "supplier" in roles[sup["id"]]
        assert rel["contracts"][0]["awardID"] == rel["awards"][0]["id"]


def test_ocds_subset_only_touching_contracts(store):
    run = store.run()
    pkg = export.to_ocds(run, ["sup:fixture-001"])
    assert pkg["releases"]
    assert all(any(p["id"] == "sup:fixture-001" for p in r["parties"]) for r in pkg["releases"])


def test_turtle_parses(store):
    run = store.run()
    g = rdflib.Graph().parse(data=export.to_turtle(run), format="turtle")
    assert len(set(g.subjects(rdflib.RDF.type, SCHEMA.Organization))) == 60
    assert len(set(g.subjects(rdflib.RDF.type, PAV.Contract))) == len(run.contracts)
    n_obs = sum(1 for s in run.suppliers for f in s["fields"].values() if f["status"] in ("gold", "conflict"))
    assert len(set(g.subjects(rdflib.RDF.type, PAV.Observation))) == n_obs
    n_flags = sum(len(s["flags"]) for s in run.suppliers)
    assert len(set(g.subjects(rdflib.RDF.type, PAV.Signal))) == n_flags


def test_turtle_escaping():
    tricky = 'Calle "Uno"\nNo. 5 \\ Int. B\ttab'
    ttl = export.PREFIXES + f"<urn:x> <urn:p> {export.turtle_string(tricky)} ."
    g = rdflib.Graph().parse(data=ttl, format="turtle")
    assert str(next(iter(g.objects()))) == tricky

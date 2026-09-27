import json
import shutil

import pytest
from proveedor_app import investigate


@pytest.fixture
def case_copy(fixture_root, tmp_path):
    dst = tmp_path / "case"
    shutil.copytree(fixture_root / "case", dst)
    return dst


def test_signals_pages(client, store):
    r = client.get("/signals")
    assert r.status_code == 200 and "tax_list_listed" in r.text
    s = next(s for s in store.run().primary if s["flags"])
    page = client.get(f"/signals/{s['id']}/0")
    assert page.status_code == 200
    assert "Dispute it" in page.text and "Why it appears" in page.text and "not an accusation" in page.text
    ev = store.run().values[s["flags"][0]["evidence_value_ids"][0]].data["evidence"][0]
    assert ev["url"] in page.text
    assert client.get(f"/signals/{s['id']}/99").status_code == 404


def test_dispute_record_lists_values_and_captures(store):
    run = store.run()
    s = next(s for s in run.primary if s["flags"])
    rec = investigate.dispute_record(run, s, s["flags"][0])
    assert rec["entity_id"] == s["id"] and rec["values"] and rec["values"][0]["evidence"][0]["url"]


def test_clusters_dedupe_and_group(store):
    run = store.run()
    found = investigate.clusters(run, ("shared_address",))
    assert found and all(len(c.members) >= 2 for c in found)
    for c in found:
        pairs = [(e["a"], e["b"], e["type"]) for e in c.edges]
        assert len(pairs) == len(set(pairs))
    assert len(investigate.clusters(run, ("same_procedure",))[0].members) >= len(found[0].members)


def test_relationships_page_focus(client):
    r = client.get("/relationships", params={"focus": "sup:fixture-005"})
    assert r.status_code == 200 and "cluster--focus" in r.text
    r = client.get("/relationships?t=same_procedure")
    assert 'value="same_procedure" checked' in r.text


def test_journal_replays_value_to_brief(client, store):
    ref = next(v for v in store.run().values.values() if v.prop == "founding_date" and len(v.data["evidence"]) > 1)
    r = client.get(f"/journal/{ref.value_id}")
    assert r.status_code == 200
    assert r.text.count("Phase 5 · Execute") == 2  # registry and gazette paths
    for needle in ("Technical definition document", "Who receives public money", "02-ontology/versions/v1.md"):
        assert needle in r.text
    assert "expected_contribution" in r.text  # objective from 03-fanout/objectives.yaml


def test_case_file_is_path_safe(client):
    assert client.get("/case-file", params={"path": "brief.md"}).status_code == 200
    assert client.get("/case-file", params={"path": "../lake/gold/fixture-case/latest.json"}).status_code == 404


def test_watchlist_diff_against_previous_run(client, store):
    runs = store.run_ids()
    old, new = store.run(runs[0]), store.run(runs[1])
    added = next(e["id"] for e in new.primary if e["id"] not in old.entities_by_id)
    changed = next(i for i in old.entities_by_id
                   if investigate.diff_entity(old.entities_by_id[i], new.entities_by_id[i]))
    r = client.get("/watchlist", params={"ids": f"{added},{changed},sup:not-there"})
    assert r.status_code == 200
    assert "New in this collection" in r.text
    assert r.text.count('class="watch__item"') == 2
    assert f"ids={added}" in r.text.replace("%3A", ":").replace("%2C", ",")


def test_exports_over_http(client, store):
    r = client.get("/export/suppliers.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    one = client.get("/export/ocds.json", params={"ids": "sup:fixture-001"}).json()
    assert one["releases"] and all(
        any(p["id"] == "sup:fixture-001" for p in rel["parties"]) for rel in one["releases"]
    )
    assert client.get("/export/gold.ttl").text.startswith("@prefix")
    assert client.get("/export/nope.xml").status_code == 404


def test_fixture_case_artifacts_match_engine_schemas(fixture_root, validator_for):
    import yaml

    case = fixture_root / "case"
    for rel, schema in (("01-scope/prd.json", "global-prd.schema.json"),
                        ("02-ontology/factors/factors.json", "factors.schema.json"),
                        ("02-ontology/ontology.json", "ontology.schema.json")):
        from conftest import v095_compat

        v = validator_for(schema)
        doc = json.loads((case / rel).read_text())
        errors = list(v.iter_errors(v095_compat(doc, v.schema) if schema == "global-prd.schema.json" else doc))
        assert not errors, (rel, [e.message for e in errors][:3])
    for pending in case.glob("**/APPROVAL_PENDING.md"):
        meta = yaml.safe_load(pending.read_text().split("---")[1])
        if meta.get("checkpoint") == "action":
            continue  # §12 action requests: the engine's approval-pending schema does not list "action" yet
        assert not list(validator_for("approval-pending.schema.json").iter_errors(meta)), pending


def test_site_works_before_any_gold(fixture_root, case_copy, tmp_path):
    from fastapi.testclient import TestClient
    from proveedor_app.gold import UnavailableStore
    from proveedor_app.web import Settings, create_app

    c = TestClient(create_app(Settings(store=UnavailableStore("no lake.yaml"), case_dir=case_copy)))
    assert c.get("/about").status_code == 200 and c.get("/healthz").json()["ok"]
    r = c.get("/")
    assert r.status_code == 503 and "Aún no hay nada publicado" in r.text  # Spanish by default
    assert c.get("/healthz").json()["run_id"] is None


def test_discovered_by_shown_where_sources_appear(case_copy, store, fixture_root, lake_copy=None):
    import yaml
    from fastapi.testclient import TestClient
    from proveedor_app.web import Settings, create_app

    path = case_copy / "03-fanout" / "objectives.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["objectives"][0]["discovered_by"] = "wikidata_official_website"
    doc["objectives"][1]["discovery_provider"] = "ocds_catalog"  # earlier engine field name still renders
    path.write_text(yaml.safe_dump(doc))
    assert investigate.discovered_by({"discovered_by": {"provider": "model_proposal"}}) == "model_proposal"
    c = TestClient(create_app(Settings(store=store, case_dir=case_copy)))
    index = c.get("/journal").text
    assert "wikidata_official_website" in index and "ocds_catalog" in index and "Cómo se encontró" in index
    ref = next(v for v in store.run().values.values()
               if store.run().lineage(v.value_id) and v.data["evidence"]
               and v.data["evidence"][0]["source_id"] == doc["objectives"][0]["source_id"])
    assert "Cómo se encontró esta fuente" in c.get(f"/journal/{ref.value_id}").text

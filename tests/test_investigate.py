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
    s = next(s for s in store.run().suppliers if s["flags"])
    page = client.get(f"/signals/{s['id']}/0")
    assert page.status_code == 200
    assert "Dispute this signal" in page.text and "In plain language" in page.text
    ev = store.run().values[s["flags"][0]["evidence_value_ids"][0]].data["evidence"][0]
    assert ev["url"] in page.text
    assert client.get(f"/signals/{s['id']}/99").status_code == 404


def test_dispute_record_lists_values_and_captures(store):
    run = store.run()
    s = next(s for s in run.suppliers if s["flags"])
    rec = investigate.dispute_record(run, s, s["flags"][0])
    assert rec["supplier_id"] == s["id"] and rec["values"] and rec["values"][0]["evidence"][0]["url"]


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
    ref = next(v for v in store.run().values.values() if v.field == "founding_date" and len(v.data["evidence"]) > 1)
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
    added = next(i for i in new.suppliers_by_id if i not in old.suppliers_by_id)
    changed = next(i for i in old.suppliers_by_id
                   if investigate.diff_supplier(old.suppliers_by_id[i], new.suppliers_by_id[i]))
    r = client.get("/watchlist", params={"ids": f"{added},{changed},sup:not-there"})
    assert r.status_code == 200
    assert "First appears in this run" in r.text
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


def test_investigator_cannot_approve(make_client, case_copy):
    c = make_client(case_dir=case_copy)
    assert c.get("/approvals").status_code == 403
    r = c.post("/approvals", data={"phase_dir": "01-scope", "approver": "X"})
    assert r.status_code == 403
    assert not (case_copy / "01-scope" / "APPROVED").exists()
    assert "Approvals" not in c.get("/").text.split("<main")[0]


def test_approver_flow_writes_marker_once(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    page = c.get("/approvals")
    assert page.status_code == 200 and page.text.count("Review and sign off") == 3
    review = c.get("/approvals/01-scope")
    assert review.status_code == 200 and "Definition of done" in review.text and "suppliers_at_80pct_core" in review.text
    r = c.post("/approvals", data={"phase_dir": "01-scope", "approver": "  Ana   Revisora "}, follow_redirects=False)
    assert r.status_code == 303 and "done=01-scope" in r.headers["location"]
    marker = json.loads((case_copy / "01-scope" / "APPROVED").read_text())
    assert marker["approver"] == "Ana Revisora" and marker["checkpoint"] == "prd" and len(marker["date"]) == 10
    again = c.post("/approvals", data={"phase_dir": "01-scope", "approver": "B"}, follow_redirects=False)
    assert "error=" in again.headers["location"]
    assert "Approved by Ana Revisora" in c.get("/approvals").text


def test_factor_decisions(make_client, case_copy, validator_for):
    c = make_client(role="approver", case_dir=case_copy)
    review = c.get("/approvals/02-ontology/factors")
    assert review.status_code == 200 and 'name="decision.economic_sector"' in review.text
    base = {"phase_dir": "02-ontology/factors", "approver": "Ana"}
    ids = ["legitimacy_signal", "procedure_type", "economic_sector", "company_age", "buyer_level"]
    for bad in ({}, {"decision.legitimacy_signal": "accept"}, {f"decision.{i}": "reject" for i in ids},
                {**{f"decision.{i}": "accept" for i in ids}, "decision.invented": "accept"},
                {**{f"decision.{i}": "accept" for i in ids}, "decision.company_age": "maybe"}):
        r = c.post("/approvals", data={**base, **bad}, follow_redirects=False)
        assert "error=" in r.headers["location"], bad
    assert not (case_copy / "02-ontology/factors/APPROVED").exists()
    good = {f"decision.{i}": "accept" for i in ids} | {"decision.buyer_level": "reject"}
    r = c.post("/approvals", data={**base, **good}, follow_redirects=False)
    assert "done=" in r.headers["location"]
    marker = json.loads((case_copy / "02-ontology/factors/APPROVED").read_text())
    assert marker["checkpoint"] == "factors" and marker["decisions"]["buyer_level"] == "reject"
    assert not list(validator_for("approved.schema.json").iter_errors(marker))
    assert "no decision recorded" not in c.get("/approvals/02-ontology/factors").text


def test_ontology_review_shows_numbers(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    page = c.get("/approvals/02-ontology").text
    for needle in ("Soundness", "0.86", "Coverage", "critic--Bad", "https://schema.org/Organization", "shapes.ttl"):
        assert needle in page, needle
    r = c.post("/approvals", data={"phase_dir": "02-ontology", "approver": "Ana", "decision.x": "accept"},
               follow_redirects=False)
    assert "error=" in r.headers["location"]  # decisions only belong to the factors checkpoint


def test_fixture_case_artifacts_match_engine_schemas(fixture_root, validator_for):
    import yaml

    case = fixture_root / "case"
    for rel, schema in (("01-scope/prd.json", "global-prd.schema.json"),
                        ("02-ontology/factors/factors.json", "factors.schema.json"),
                        ("02-ontology/ontology.json", "ontology.schema.json")):
        errors = list(validator_for(schema).iter_errors(json.loads((case / rel).read_text())))
        assert not errors, (rel, [e.message for e in errors][:3])
    for pending in case.glob("**/APPROVAL_PENDING.md"):
        meta = yaml.safe_load(pending.read_text().split("---")[1])
        assert not list(validator_for("approval-pending.schema.json").iter_errors(meta)), pending


def test_approver_guards(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    for phase_dir in ("..", "../..", "", "03-fanout", "01-scope/../.."):
        r = c.post("/approvals", data={"phase_dir": phase_dir, "approver": "X"}, follow_redirects=False)
        assert "error=" in r.headers["location"], phase_dir
    r = c.post("/approvals", data={"phase_dir": "01-scope", "approver": ""}, follow_redirects=False)
    assert "error=" in r.headers["location"]
    r = c.post("/approvals", data={"phase_dir": "01-scope", "approver": "X"},
               headers={"origin": "https://evil.example"})
    assert r.status_code == 403
    assert not (case_copy / "01-scope" / "APPROVED").exists()


def test_approved_marker_matches_engine_schema(case_copy, validator_for):
    investigate.approve(investigate.CaseDir(case_copy), "01-scope", "Ana")
    marker = json.loads((case_copy / "01-scope" / "APPROVED").read_text())
    assert not list(validator_for("approved.schema.json").iter_errors(marker))


def test_front_matter_metadata(tmp_path):
    (tmp_path / "02-ontology").mkdir()
    (tmp_path / "02-ontology" / "APPROVAL_PENDING.md").write_text(
        '---\ncheckpoint: factors\nartifact_paths: ["02-ontology/factors.yaml"]\n---\n# Factors\n')
    [a] = investigate.approvals(investigate.CaseDir(tmp_path))
    assert a.checkpoint == "factors" and a.meta["artifact_paths"] == ["02-ontology/factors.yaml"]


def test_approver_works_before_any_gold(fixture_root, case_copy, tmp_path):
    from fastapi.testclient import TestClient
    from proveedor_app.gold import UnavailableStore
    from proveedor_app.web import Settings, create_app

    c = TestClient(create_app(Settings(store=UnavailableStore("no lake.yaml"), case_dir=case_copy, role="approver")))
    assert c.get("/approvals").status_code == 200
    r = c.get("/")
    assert r.status_code == 503 and "No gold export to read yet" in r.text
    assert c.get("/healthz").json()["run_id"] is None

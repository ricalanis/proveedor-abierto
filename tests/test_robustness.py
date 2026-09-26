"""Every page renders for every supplier and value, and odd-but-legal gold rows do not break the app."""

import json
import shutil

from fastapi.testclient import TestClient
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app


def test_every_page_renders(client, store):
    run = store.run()
    for s in run.primary:
        assert client.get(f"/suppliers/{s['id']}").status_code == 200, s["id"]
        for i in range(len(s["flags"])):
            assert client.get(f"/signals/{s['id']}/{i}").status_code == 200
    for vid in run.values:
        assert client.get(f"/journal/{vid}").status_code == 200, vid
        assert client.get(f"/fragments/evidence/{vid}").status_code == 200, vid
    for path in ("/", "/signals", "/relationships", "/journal", "/completeness", "/watchlist",
                 "/relationships?t=same_procedure", "/?show=conflicts", "/?show=incomplete"):
        assert client.get(path).status_code == 200, path
    assert client.get("/", params={"run": "run-fixture-0000"}).status_code == 200


def test_messy_rows(fixture_root, tmp_path):
    lake = tmp_path / "lake"
    shutil.copytree(fixture_root / "lake", lake)
    run_dir = lake / "gold" / "fixture-case" / "run-fixture-0001"
    messy = {
        "id": "sup:messy-1",
        "class": "supplier",
        "classified_as": [],
        "properties": {
            "legal_name": {"value_id": "val:m-1", "value": "Proveedor Ejemplo <b>Raro</b> & \"Cía\"",
                           "confidence": None, "status": "gold",
                           "evidence": [{"url": "javascript:alert(1)", "source_type": "unknown_type"}]},
            "tax_id": {"value_id": "val:m-2", "value": 12345, "confidence": 1, "status": "conflict",
                       "evidence": [{"url": "https://x.example/a", "bronze_key": "sha256:" + "0" * 64}]},
            "extra_numeric": {"value_id": "val:m-3", "value": 3.5, "confidence": 0.5, "status": "gold",
                              "evidence": [{"url": "https://x.example/b"}]},
        },
        "flags": [{"rule_id": "rule_from_the_future", "label": "Unknown rule", "explanation": "e",
                   "evidence_value_ids": ["val:m-1", "val:does-not-exist"]}],
        "links": [{"property": "shared_address", "target": "sup:not-in-run", "via_value_id": "val:nope"},
                  {"property": "awarded", "target": "con:not-in-run", "via_value_id": "val:nope"},
                  {"property": "undeclared_relation", "target": "sup:fixture-001", "via_value_id": "val:nope"}],
    }
    with (run_dir / "entities.jsonl").open("a") as fh:
        fh.write(json.dumps(messy) + "\n")
    (run_dir / "trace.jsonl").open("a").write(json.dumps(
        {"step_id": "step:loop", "run_id": "run-fixture-0001", "phase": 5, "parent_step_id": "step:loop",
         "value_ids": ["val:m-1"], "mode": "S1"}) + "\n")
    c = TestClient(create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=tmp_path / "no-case")))
    page = c.get("/suppliers/sup:messy-1", params={"ev": "val:m-1"})
    assert page.status_code == 200
    assert "<b>Raro</b>" not in page.text and "&lt;b&gt;Raro&lt;/b&gt;" in page.text
    assert 'href="javascript:' not in page.text
    for path in ("/signals/sup:messy-1/0", "/journal/val:m-1", "/journal/val:m-2", "/relationships", "/",
                 "/completeness", "/journal", "/export/gold.ttl", "/export/ocds.json", "/export/entities.csv",
                 "/watchlist?ids=sup:messy-1"):
        assert c.get(path).status_code == 200, path

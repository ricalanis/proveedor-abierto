"""Honesty labels on the product: simulated collection (CONTRACT §7), unreviewed previews, values backed only by
a supporting model, and the source format on a receipt."""

import json
import shutil

import pytest
from fastapi.testclient import TestClient
from proveedor_app import dod
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app


@pytest.fixture
def lake(fixture_root, tmp_path):
    dst = tmp_path / "lake"
    shutil.copytree(fixture_root / "lake", dst)
    return dst


def _client(lake, case_dir):
    c = TestClient(create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=case_dir)))
    c.cookies.set("pa_lang", "en")
    return c


def test_simulated_inference_banner_and_dod(lake, fixture_root):
    run_dir = lake / "gold" / "fixture-case" / "run-fixture-0001"
    metrics = json.loads((run_dir / "metrics.json").read_text())
    metrics["inference_backend"] = "recorded"
    (run_dir / "metrics.json").write_text(json.dumps(metrics))
    c = _client(lake, fixture_root / "case")
    assert "Simulated collection." in c.get("/").text
    page = c.get("/completeness").text
    assert "Simulated collection." in page and "✓" not in page.split("dod__grid")[1].split("</dl>")[0]
    run = GoldStore(LocalSource(lake)).run()
    rows = dod.criteria(dod.compute(run.entities, run.domain), run.metrics, run.domain, "recorded")
    assert all(r["met"] is False and r["mock"] for r in rows)


def test_value_level_recorded_tag(lake, fixture_root):
    path = lake / "gold" / "fixture-case" / "run-fixture-0001" / "entities.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows.sort(key=lambda r: r["class"] != "supplier")  # suppliers first; contracts keep their place after
    rows[0]["properties"]["address"]["generated_by"] = {"backend": "recorded", "model": "double", "at": "2026-09-26"}
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    c = _client(lake, fixture_root / "case")
    frag = c.get(f"/fragments/evidence/{rows[0]['properties']['address']['value_id']}").text
    assert "Simulated collection" in frag
    assert "Simulated collection." in c.get("/").text  # one recorded value marks the whole run


@pytest.mark.ui


def test_preview_output_is_labelled(lake, fixture_root):
    run_dir = lake / "gold" / "fixture-case" / "run-fixture-0001"
    metrics = json.loads((run_dir / "metrics.json").read_text())
    (run_dir / "metrics.json").write_text(json.dumps({**metrics, "preview": True}))
    c = _client(lake, fixture_root / "case")
    assert "Unreviewed preview." in c.get("/").text


def test_evidence_format_is_shown(lake, fixture_root):
    path = lake / "gold" / "fixture-case" / "run-fixture-0001" / "entities.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows.sort(key=lambda r: r["class"] != "supplier")  # suppliers first; contracts keep their place after
    rows[0]["properties"]["tax_id"]["evidence"][0]["format"] = "xlsx"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    frag = _client(lake, fixture_root / "case").get(f"/fragments/evidence/{rows[0]['properties']['tax_id']['value_id']}")
    assert "Procurement portal" in frag.text and "xlsx" in frag.text


def test_jev_only_gold_is_flagged_and_not_counted(lake, fixture_root):
    path = lake / "gold" / "fixture-case" / "run-fixture-0001" / "entities.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows.sort(key=lambda r: r["class"] != "supplier")  # suppliers first; contracts keep their place after
    target = rows[0]["properties"]["tax_id"]
    assert target["status"] == "gold"
    target["generated_by"] = {"backend": "jev", "model": "jev-entity-match", "at": "2026-09-26T19:00:00Z"}
    for r in rows:  # make the rest live so the banner logic is exercised too
        for f in r["properties"].values():
            if f is not target:
                f["generated_by"] = {"backend": "vultr", "model": "m", "at": "2026-09-26T19:00:00Z"}
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert not dod.is_filled(target) and dod.jev_only(target)
    c = _client(lake, fixture_root / "case")
    frag = c.get(f"/fragments/evidence/{target['value_id']}").text
    assert "supporting model" in frag and "second check" in frag
    assert "backend--jev" in c.get(f"/suppliers/{rows[0]['id']}").text

"""A connection type added outside the approved ontology (the harness-assisted run's app-ontology.json marks each
with "provenance") is named as such on the connections page; the engine's own relations show no note."""

import json
import shutil

from fastapi.testclient import TestClient
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app


def harness_lake(fixture_root, tmp_path):
    lake = tmp_path / "lake"
    shutil.copytree(fixture_root / "lake", lake)
    store = GoldStore(LocalSource(lake))
    run = store.run(None)
    onto = json.loads(json.dumps(run.domain.raw))
    peer = run.domain.peer_relations()[0]
    for r in onto["relations"]:
        if r["id"] == peer:
            r["provenance"] = "harness extension, not in the approved ontology"
    run_dir = next(p for p in (lake / "gold").glob(f"*/{run.run_id}"))
    (run_dir / "ontology.json").write_text(json.dumps(onto))
    return lake, peer


def test_harness_relations_are_marked(fixture_root, tmp_path):
    lake, peer = harness_lake(fixture_root, tmp_path)
    c = TestClient(create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=fixture_root / "case")))
    en = c.get(f"/relationships?t={peer}&lang=en").text
    assert "Not in the approved ontology:" in en and 'title="harness extension, not in the approved ontology"' in en
    es = c.get(f"/relationships?t={peer}&lang=es").text
    assert "(harness extension" not in es  # no English parenthetical on the Spanish page
    assert "Fuera de la ontología aprobada:" in c.get(f"/relationships?t={peer}&lang=es").text


def test_engine_relations_have_no_note(client):
    assert "conn-provenance" not in client.get("/relationships").text


def test_an_extension_keeps_its_own_label_over_the_apps_translation():
    """The harness's shared_representative is a shared CONTACT person, not a verified legal representative: the
    app's Spanish for that id ("Mismo representante legal") must not relabel it. Its own `labels.es` wins."""
    from proveedor_app.domain import localize_ontology
    from proveedor_app.i18n import ONTOLOGY_ES

    rel = {"id": "shared_representative", "label": "Shared contact person", "provenance": "harness extension"}
    out = localize_ontology({"relations": [rel]}, ONTOLOGY_ES, "es")
    assert out["relations"][0]["label"] == "Shared contact person"
    rel_es = {**rel, "labels": {"es": "Misma persona de contacto"}}
    assert localize_ontology({"relations": [rel_es]}, ONTOLOGY_ES, "es")["relations"][0]["label"] == (
        "Misma persona de contacto"
    )
    engine = {"id": "shared_representative", "label": "Shared legal representative"}
    assert localize_ontology({"relations": [engine]}, ONTOLOGY_ES, "es")["relations"][0]["label"] == (
        "Mismo representante legal"
    )

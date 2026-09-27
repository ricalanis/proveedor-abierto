"""Same app, different question: a second, unrelated domain renders with no code changes (CONTRACT v0.7 §11)."""

import json
import re

import pytest
from fastapi.testclient import TestClient
from proveedor_app import dod, fixture_libraries
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app

# Procurement vocabulary that must never leak into another domain's pages.
PROCUREMENT_WORDS = re.compile(r"\b(supplier|suppliers|contract|contracts|RFC|tax[- ]list|sanction|procurement)\b",
                               re.IGNORECASE)


@pytest.fixture(scope="module")
def libraries(tmp_path_factory):
    out = tmp_path_factory.mktemp("libraries")
    lake = fixture_libraries.generate(out)
    store = GoldStore(LocalSource(lake))
    return store, out / "case"


def _visible_text(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL)
    return re.sub(r"<[^>]+>", " ", html)


def test_domain_comes_from_the_ontology(libraries):
    store, _ = libraries
    run = store.run()
    assert run.domain.primary_class == "library" and len(run.primary) == 24
    assert [p.label for p in run.domain.dod_props()] == ["Branch name", "Registry code", "Street address",
                                                        "Opening hours"]
    recomputed = dod.compute(run.entities, run.domain)
    assert dod.cross_check(recomputed, run.metrics, run.domain) == []
    rows = dod.criteria(recomputed, run.metrics, run.domain, None, run.dod_queries, run.entities)
    assert [r["criterion_id"] for r in rows] == ["libraries_found", "with_hours", "evidence_integrity"]
    assert all(r["agrees"] for r in rows)


def test_every_screen_renders_without_procurement_words(libraries):
    store, case = libraries
    client = TestClient(create_app(Settings(store=store, case_dir=case)))
    run = store.run()
    lib = run.primary[5]  # has a missing opening-hours value and a signal
    value = lib["properties"]["address"]["value_id"]
    pages = ["/", "/signals", f"/signals/{lib['id']}/0", "/relationships", "/journal", f"/journal/{value}",
             "/completeness", "/data", "/about", f"/entities/{lib['id']}", f"/entities/{lib['id']}?ev={value}",
             f"/watchlist?ids={lib['id']}"]
    for path in pages:
        r = client.get(path)
        assert r.status_code == 200, path
        leaked = PROCUREMENT_WORDS.findall(_visible_text(r.text))
        assert not leaked, (path, sorted(set(leaked)))
    home = client.get("/").text
    for label in ("Libraries", "Branch name", "Opening hours"):
        assert label in home
    dossier = client.get(f"/entities/{lib['id']}").text
    assert "Operated by" in dossier and "Same operator" in dossier and "Ayuntamiento Ejemplo" in dossier
    assert "Opening hours not published officially" in client.get("/signals").text
    assert "Call the branch" in client.get(f"/signals/{lib['id']}/0").text  # rule text from the ontology


def test_exports_follow_the_ontology(libraries):
    store, case = libraries
    client = TestClient(create_app(Settings(store=store, case_dir=case)))
    header = client.get("/export/entities.csv").text.splitlines()[0]
    assert header.startswith("id,class,name,") and "opening_hours" in header
    ttl = client.get("/export/gold.ttl").text
    assert "<https://schema.org/Library>" in ttl and "<https://schema.org/openingHours>" in ttl
    assert client.get("/export/ocds.json").status_code == 404  # no OCDS-aligned class in this ontology


def test_fixture_matches_engine_schemas(libraries, validator_for):
    store, _ = libraries
    run_dir = store.source.root / "gold" / "fixture-libraries" / "run-libraries-0001"
    v = validator_for("entity.schema.json")
    for line in (run_dir / "entities.jsonl").read_text().splitlines():
        assert not list(v.iter_errors(json.loads(line)))
    for name, schema in (("metrics.json", "metrics.schema.json"), ("ontology.json", "ontology.schema.json"),
                         ("dod-queries.json", "dod-queries.schema.json")):
        errors = [e.message for e in validator_for(schema).iter_errors(json.loads((run_dir / name).read_text()))]
        assert not errors, (name, errors[:3])


@pytest.mark.ui
def test_no_procurement_words_after_scripts_run(libraries):
    """Client-side scripts must not reintroduce domain words either (e.g. button labels)."""
    import socket
    import threading
    import time

    import uvicorn

    sync_api = pytest.importorskip("playwright.sync_api")
    store, case = libraries
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(Settings(store=store, case_dir=case)), host="127.0.0.1",
                                           port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            lib = store.run().primary[5]
            for path in ("/", f"/entities/{lib['id']}", "/watchlist", "/completeness"):
                pg.goto(f"http://127.0.0.1:{port}{path}")
                pg.wait_for_load_state("networkidle")
                leaked = PROCUREMENT_WORDS.findall(pg.inner_text("body"))
                assert not leaked, (path, sorted(set(leaked)))
            b.close()
    finally:
        server.should_exit = True

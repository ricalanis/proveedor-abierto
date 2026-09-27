"""Real gold can arrive thin: no signals or connections yet (engine gap R6), no rules in the ontology, no records at
all, or receipts that are a whole-page screenshot plus a selector (value-level crops are cut). Every page must say
honestly what is and is not there; none may break or render empty. Also covers 'Cómo se hizo'."""

import json
import re
import shutil
import socket
import threading
import time

import pytest
from fastapi.testclient import TestClient
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app

PAGES = ["/", "/signals", "/relationships", "/completeness", "/data", "/about", "/como-se-hizo", "/journal",
         "/watchlist"]


def _runs(lake):
    return sorted((lake / "gold" / "fixture-case").glob("run-*"))


def _rewrite_entities(lake, fn):
    for run_dir in _runs(lake):
        path = run_dir / "entities.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows = [r for r in (fn(r) for r in rows) if r is not None]
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def _rewrite_ontology(lake, case, fn):
    for path in [*(d / "ontology.json" for d in _runs(lake)), case / "02-ontology" / "ontology.json"]:
        if path.is_file():
            path.write_text(json.dumps(fn(json.loads(path.read_text())), indent=2))


def _variant(fixture_root, tmp_path, name):
    lake, case = tmp_path / name / "lake", tmp_path / name / "case"
    shutil.copytree(fixture_root / "lake", lake)
    shutil.copytree(fixture_root / "case", case)
    return lake, case


def _client(lake, case, lang="es"):
    c = TestClient(create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=case)))
    c.cookies.set("pa_lang", lang)
    return c


def _strip_signals_and_peer_links(row):
    row["flags"] = []
    row["links"] = [x for x in row.get("links") or [] if not str(x.get("target", "")).startswith("sup:")]
    return row


@pytest.fixture
def bare(fixture_root, tmp_path):
    """Gold with no signals and no connections between suppliers (contracts still linked)."""
    lake, case = _variant(fixture_root, tmp_path, "bare")
    _rewrite_entities(lake, _strip_signals_and_peer_links)
    return lake, case


@pytest.fixture
def no_rules(bare):
    """Same, and the ontology defines no rules and no peer relations yet."""
    lake, case = bare

    def drop(onto):
        onto["rules"] = []
        onto["relations"] = [r for r in onto.get("relations") or [] if r.get("range") != "supplier"]
        return onto

    _rewrite_ontology(lake, case, drop)
    return lake, case


@pytest.fixture
def empty(fixture_root, tmp_path):
    """A run that has published no entities at all."""
    lake, case = _variant(fixture_root, tmp_path, "empty")
    _rewrite_entities(lake, lambda row: None)
    return lake, case


def _visible(html):
    return re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL))


def test_no_signals_explains_what_is_checked(bare):
    c = _client(*bare)
    for path in PAGES:
        assert c.get(path).status_code == 200, path
    page = c.get("/signals").text
    assert "Ninguna señal se ha activado" in page and "no es un historial limpio" in page
    for label in ("Aparece en la lista del SAT", "Se constituyó poco antes"):  # the rules, in Spanish
        assert label in page
    dossier = c.get("/entities/sup:fixture-005").text
    assert "Ninguna señal se ha activado para este proveedor" in dossier and 'href="/signals"' in dossier
    assert "El caso busca:" in dossier and "mismo domicilio" in dossier


def test_no_connections_explains_what_is_looked_for(bare):
    page = _client(*bare).get("/relationships").text
    assert "No se encontraron conexiones" in page and "Mismo domicilio" in page and "Mismo representante legal" in page
    assert '<section class="cluster' not in page and "0 grupos" not in page


def test_no_rules_or_relations_defined_yet(no_rules):
    c = _client(*no_rules)
    signals, rel = c.get("/signals").text, c.get("/relationships").text
    assert "aún no publica sus reglas de señales" in signals
    assert "Las conexiones aún no están definidas" in rel and 'name="t"' not in rel  # no empty filter form
    method = c.get("/como-se-hizo").text
    assert method.count("ninguna definida todavía") == 2


def test_nothing_published_yet(empty):
    c = _client(*empty)
    for path in PAGES:
        r = c.get(path)
        assert r.status_code == 200, path
        assert "Traceback" not in r.text and "None" not in _visible(r.text).split(), path
    assert "Aún no se publican proveedores" in c.get("/").text
    assert "no hay nada que medir" in c.get("/completeness").text
    assert "Aún no se publican datos" in c.get("/como-se-hizo").text


def test_both_languages_on_thin_data(no_rules, empty):
    for variant in (no_rules, empty):
        c = _client(*variant, lang="en")
        for path in PAGES:
            assert c.get(path).status_code == 200, path
    assert "No signal has fired" in _client(*no_rules, lang="en").get("/signals").text


def test_page_level_receipts_degrade(fixture_root, tmp_path):
    """Whole-page screenshots with a selector: the receipt names where the value is, by source format; a missing
    screenshot or link never renders a broken line."""
    lake, case = _variant(fixture_root, tmp_path, "receipts")

    def shape(row):
        if row.get("id") != "sup:fixture-005":
            return row
        props = row["properties"]
        assert all(props[k]["evidence"] for k in ("tax_id", "address", "legal_name", "founding_date"))
        props["tax_id"]["evidence"][0]["format"] = "xlsx"
        props["tax_id"]["evidence"][0]["selector"] = "Listado!B214"
        props["address"]["evidence"][0]["screenshot_key"] = "sha256:" + "0" * 64  # not in bronze
        for ev in props["legal_name"]["evidence"]:
            ev.pop("screenshot_key", None)
        for ev in props["founding_date"]["evidence"]:
            ev["url"] = ""
            ev.pop("captured_at", None)
        return row

    _rewrite_entities(lake, shape)
    c = _client(lake, case)
    run = GoldStore(LocalSource(lake)).run()
    e = run.entities_by_id["sup:fixture-005"]
    tax = c.get(f"/fragments/evidence/{e['properties']['tax_id']['value_id']}").text
    assert "Celda o fila en el archivo" in tax and "Listado!B214" in tax and "Captura de la página completa" in tax
    addr = c.get(f"/fragments/evidence/{e['properties']['address']['value_id']}").text
    assert "data-shot" in addr and "No se pudo cargar la captura" in addr  # fallback ready for the browser
    name = c.get(f"/fragments/evidence/{e['properties']['legal_name']['value_id']}").text
    assert "<img" not in name and "copia guardada" in name
    founded = c.get(f"/fragments/evidence/{e['properties']['founding_date']['value_id']}").text
    assert "Sin enlace registrado" in founded and "Capturado el" not in founded
    dossier = c.get(f"/entities/{e['id']}").text
    assert "capturado el —" not in dossier and "Ver comprobante" in dossier


def test_how_it_was_made(make_client, store):
    c = make_client(lang="es")
    page = c.get("/como-se-hizo").text
    for needle in ("La pregunta", "Who receives public money", "La definición", "Qué se registra", "Las fuentes públicas",
                   "La evidencia", "github.com/ricalanis/ontofill", 'href="/journal"', "compras.example",
                   "todavía espera la aprobación"):  # the fixture PRD is pending, and the page says so
        assert needle in page, needle
    assert "built-in method" not in page and "<built-in" not in page
    assert re.search(r'<dd>\d+</dd>', page.split('id="evidence"')[1])  # real counts, not objects
    for internal in ("/run", "/engine", "/approvals", "console", "D0", "S2", "run-fixture"):
        assert internal not in _visible(page), internal
    assert c.get("/how-it-was-made").status_code == 200
    assert 'href="/como-se-hizo"' in c.get("/").text.split('<nav class="tabs"', 1)[1].split("</nav>")[0]
    en = make_client(lang="en").get("/como-se-hizo").text
    assert "How this was made" in en and "The question" in en


# Headless rendering at 1280 and 390 px ------------------------------------------------------------------------

@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _serve(lake, case):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    import uvicorn

    app = create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=case))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    return server, f"http://127.0.0.1:{port}"


@pytest.mark.ui
@pytest.mark.parametrize("width", [1280, 390])
def test_thin_data_renders_without_overflow(browser, no_rules, width):
    server, base = _serve(*no_rules)
    try:
        ctx = browser.new_context(viewport={"width": width, "height": 900})
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        for path in ("/signals", "/relationships", "/como-se-hizo", "/entities/sup:fixture-005", "/"):
            pg.goto(base + path)
            assert pg.evaluate("document.documentElement.scrollWidth") <= width, path
            assert pg.locator("main").inner_text().strip(), path
        assert errors == []
        ctx.close()
    finally:
        server.should_exit = True


@pytest.mark.ui
@pytest.mark.parametrize("width", [1280, 390])
def test_broken_screenshot_falls_back_in_the_browser(browser, fixture_root, tmp_path, width):
    lake, case = _variant(fixture_root, tmp_path, "broken")

    def shape(row):
        if row.get("id") == "sup:fixture-005":
            row["properties"]["address"]["evidence"][0]["screenshot_key"] = "sha256:" + "0" * 64
        return row

    _rewrite_entities(lake, shape)
    server, base = _serve(lake, case)
    try:
        vid = GoldStore(LocalSource(lake)).run().entities_by_id["sup:fixture-005"]["properties"]["address"]["value_id"]
        ctx = browser.new_context(viewport={"width": width, "height": 900})
        pg = ctx.new_page()
        pg.goto(f"{base}/entities/sup:fixture-005?ev={vid}#evidence")
        pg.locator(".shot__missing").first.wait_for(state="visible")
        assert pg.locator("#evidence-panel img[data-shot]").count() == 0
        assert pg.evaluate("document.documentElement.scrollWidth") <= width
        ctx.close()
    finally:
        server.should_exit = True

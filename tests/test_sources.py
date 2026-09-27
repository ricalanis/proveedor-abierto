"""'Directorio de fuentes' (/fuentes, alias /sources): every public source behind published values, its numbers
recomputed here straight from the gold export, the case's authority decision, and an honest empty state."""

import json
import re
import shutil
import socket
import threading
import time

import pytest
import yaml
from fastapi.testclient import TestClient
from proveedor_app import i18n
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.investigate import CaseDir
from proveedor_app.sources import directory
from proveedor_app.web import Settings, create_app


def _client(lake, case, lang="es"):
    c = TestClient(create_app(Settings(store=GoldStore(LocalSource(lake)), case_dir=case)))
    c.cookies.set("pa_lang", lang)
    return c


def _copy(fixture_root, tmp_path, name):
    lake, case = tmp_path / name / "lake", tmp_path / name / "case"
    shutil.copytree(fixture_root / "lake", lake)
    shutil.copytree(fixture_root / "case", case)
    return lake, case


def _visible(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL)))


def expected_from_gold(run) -> dict[str, dict]:
    """source_id -> {values, props: {prop: n}, first, last}, computed from the raw entities (not via the app)."""
    out: dict[str, dict] = {}
    for e in run.entities:
        for prop, f in (e.get("properties") or {}).items():
            if not isinstance(f, dict) or f.get("status") == "missing":
                continue
            for ev in f.get("evidence") or []:
                s = out.setdefault(ev["source_id"], {"values": set(), "props": {}, "stamps": []})
                if f["value_id"] not in s["values"]:
                    s["values"].add(f["value_id"])
                    s["props"][(e["class"], prop)] = s["props"].get((e["class"], prop), 0) + 1
                s["stamps"].append(i18n.parse_ts(ev["captured_at"]))
    return out


def test_directory_numbers_match_the_gold_export(store, fixture_root):
    run = store.run()
    want = expected_from_gold(run)
    got = directory(run, CaseDir(fixture_root / "case"), run.domain)
    assert {s["source_id"] for s in got["sources"]} == set(want)
    assert got["value_count"] == len(set().union(*(w["values"] for w in want.values())))
    for s in got["sources"]:
        w = want[s["source_id"]]
        assert s["backs"] == len(w["values"]), s["host"]
        assert sorted(n for _, n in s["by_prop"]) == sorted(w["props"].values()), s["host"]
        assert i18n.parse_ts(s["first"]) == min(w["stamps"]) and i18n.parse_ts(s["last"]) == max(w["stamps"])
        assert s["example"]["value_id"] in w["values"]  # the example receipt really comes from this source
    assert [s["backs"] for s in got["sources"]] == sorted((s["backs"] for s in got["sources"]), reverse=True)


def test_page_shows_each_source_in_spanish(make_client, store):
    run = store.run()
    want = expected_from_gold(run)
    text = make_client(lang="es").get("/fuentes").text
    assert "<h1>Directorio de fuentes</h1>" in text and '<html lang="es">' in text
    seen = _visible(text)
    for host in ("compras.example", "registro-empresas.example", "lista-fiscal.example", "sanciones.example",
                 "gaceta.example"):
        assert f'<h2 class="source__host">{host}</h2>' in text
    for sid, w in want.items():
        assert f"{len(w['values'])} datos" in seen, sid
    assert f"<dd>{len(want)}</dd>" in text  # the ticker counts sources behind published values
    for line in ("<dt>Tipo</dt>", "<dt>Respalda</dt>", "<dt>Autoridad</dt>"):
        assert line in text
    assert "Portal de compras públicas" in text  # ontology source class, Spanish label from the app
    assert "Ver un comprobante:" in text and "#evidence" in text


def test_authority_comes_from_the_case_prd(make_client):
    text = make_client(lang="es").get("/fuentes").text
    blocks = dict(re.findall(r'<h2 class="source__host">([^<]+)</h2>(.*?)</li>', text, flags=re.DOTALL))
    assert "En la lista de confianza del caso" in blocks["compras.example"]  # trusted_publishers[].domains
    assert "procurement portal" in blocks["compras.example"]  # the publisher kind, as the PRD wrote it
    assert "Fuera de la lista de confianza del caso" in blocks["registro-empresas.example"]
    assert "regla del caso: revisión" in blocks["registro-empresas.example"]  # unknown_source_action
    assert "«revisión»" in text


def test_objectives_tier_wins_over_the_prd(fixture_root, tmp_path):
    lake, case = _copy(fixture_root, tmp_path, "tiers")
    path = case / "03-fanout" / "objectives.yaml"
    doc = yaml.safe_load(path.read_text())
    for o in doc["objectives"]:
        if o["source_id"] == "registro-example":
            o["authority_tier"] = "secondary"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    text = _client(lake, case).get("/fuentes").text
    block = text.split('<h2 class="source__host">registro-empresas.example</h2>', 1)[1].split("</li>", 1)[0]
    assert "Fuente secundaria" in block and "Fuera de la lista" not in block


def test_no_policy_ranks_nothing(fixture_root, tmp_path):
    lake, case = _copy(fixture_root, tmp_path, "nopolicy")
    (case / "01-scope" / "prd.json").unlink()
    text = _client(lake, case).get("/fuentes").text
    assert "aún no publica una lista de editores de confianza" in text and "El caso no lo indica" in text
    assert "En la lista de confianza" not in text


def test_english_and_alias(make_client):
    en = make_client(lang="en")
    text = en.get("/sources").text
    assert "<h1>Source directory</h1>" in text and '<html lang="en">' in text
    assert "On the case&#39;s trusted list" in text and "case rule: review" in text
    nav = text.split('<nav class="tabs"', 1)[1].split("</nav>", 1)[0]
    assert 'href="/fuentes" aria-current="page">Sources</a>' in nav
    es_nav = en.get("/fuentes?lang=es").text.split('<nav class="tabs"', 1)[1].split("</nav>", 1)[0]
    assert ">Fuentes</a>" in es_nav


def test_how_it_was_made_links_the_directory(make_client):
    page = make_client(lang="es").get("/como-se-hizo").text
    step = page.split('id="sources"', 1)[1].split('id="evidence"', 1)[0]
    assert 'href="/fuentes"' in step and "Abrir el directorio de fuentes" in step


def test_empty_state_when_nothing_is_published(fixture_root, tmp_path):
    lake, case = _copy(fixture_root, tmp_path, "empty")
    for run_dir in (lake / "gold" / "fixture-case").glob("run-*"):
        (run_dir / "entities.jsonl").write_text("")
    for lang, needle in (("es", "Ninguna fuente respalda todavía un dato publicado"),
                         ("en", "No source backs a published value yet")):
        r = _client(lake, case, lang).get("/fuentes")
        assert r.status_code == 200 and needle in r.text
        assert 'class="slip source"' not in r.text and "None" not in _visible(r.text).split()
    text = _client(lake, case).get("/fuentes").text
    assert "Encontradas, sin respaldar ningún dato publicado" in text  # the candidates the case found, honestly
    assert "compras.example" in text.split('id="unused-h"', 1)[1]


def test_no_gold_at_all_still_renders(tmp_path, fixture_root):
    from proveedor_app.gold import UnavailableStore

    c = TestClient(create_app(Settings(store=UnavailableStore("no lake"), case_dir=fixture_root / "case")))
    r = c.get("/fuentes")
    assert r.status_code == 200 and "Ninguna fuente respalda todavía" in r.text


def test_fixture_exports_unchanged_by_the_directory(fixture_root):
    objectives = yaml.safe_load((fixture_root / "case" / "03-fanout" / "objectives.yaml").read_text())
    assert all("authority_tier" not in o for o in objectives["objectives"])  # the app reads tiers, never writes them
    assert "authority_policy" in json.loads((fixture_root / "case" / "01-scope" / "prd.json").read_text())


# Headless rendering at 1280 and 390 px ------------------------------------------------------------------------

@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture(scope="module")
def base_url(fixture_root, store):
    import uvicorn

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    app = create_app(Settings(store=store, case_dir=fixture_root / "case"))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.mark.ui
@pytest.mark.parametrize("width,scheme", [(1280, "dark"), (390, "light")])
def test_directory_in_the_browser(browser, base_url, width, scheme):
    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda exc: errors.append(str(exc)))
    pg.goto(base_url + "/fuentes")
    assert pg.evaluate("document.documentElement.scrollWidth") <= width
    overflowing = pg.evaluate("""[...document.querySelectorAll('.slip')]
        .filter(s => s.scrollWidth > s.clientWidth + 1).map(s => s.id)""")
    assert overflowing == []  # nothing spills out of a slip (its perforated edge would cut it off)
    assert pg.locator(".slip.source").count() == 5
    mask = pg.evaluate("getComputedStyle(document.querySelector('.slip')).maskImage || "
                       "getComputedStyle(document.querySelector('.slip')).webkitMaskImage")
    assert "conic-gradient" in mask  # the perforated bottom edge
    host = pg.locator(".source__host").first.inner_text()
    pg.locator(".slip.source").first.locator("a.ev-link").click()
    pg.wait_for_url("**/entities/**")
    link = pg.locator("#evidence-panel a.source-link").first
    link.wait_for()
    assert host in link.inner_text()
    assert errors == []
    ctx.close()


@pytest.mark.ui
@pytest.mark.parametrize("width", [1280, 390])
def test_receipt_slips_and_stamps_in_the_browser(browser, base_url, width):
    ctx = browser.new_context(viewport={"width": width, "height": 900})
    pg = ctx.new_page()
    pg.goto(base_url + "/entities/sup:fixture-007")
    assert pg.evaluate("document.documentElement.scrollWidth") <= width
    styles = pg.evaluate("""Object.fromEntries(['gold', 'conflict', 'missing'].map(s => {
        const el = document.querySelector('.fact .status--' + s);
        return [s, el ? getComputedStyle(el).borderTopStyle : null];
    }))""")
    assert styles["gold"] == "solid" and styles["conflict"] == "dashed"  # the stamp's shape is the status
    assert styles["missing"] in ("dotted", None)
    overflowing = pg.evaluate("[...document.querySelectorAll('.slip')].filter(s => s.scrollWidth > s.clientWidth + 1).length")
    assert overflowing == 0
    ctx.close()

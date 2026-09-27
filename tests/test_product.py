"""The consumer product (CONTRACT §14): Spanish-first copy, receipts on every value, signals framed as signals,
open data, a plain completeness page, and a catalog that covers every string the templates show."""

import re
from pathlib import Path

import pytest
from proveedor_app import dod, i18n, investigate
from proveedor_app.domain import Domain, localize_ontology
from proveedor_app.web import confidence_level, dataset_stats

TEMPLATES = Path(__file__).parents[1] / "app" / "proveedor_app" / "templates"
CALL = re.compile(r"""\b(_|ngettext)\(\s*(["'])((?:\\.|(?!\2).)*)\2(?:\s*,\s*(["'])((?:\\.|(?!\4).)*)\4)?""")


@pytest.fixture
def es(make_client):
    return make_client(lang="es")


@pytest.fixture
def run(store):
    return store.run()


def product_paths(run) -> list[str]:
    e = next(x for x in run.primary if x.get("flags"))
    v = next(ref for ref in run.values.values() if ref.entity_id == e["id"] and run.steps_by_value.get(ref.value_id))
    return ["/", "/?q=Ejemplo", "/?show=signals", "/?show=incomplete", "/?show=conflicts", f"/entities/{e['id']}",
            f"/entities/{e['id']}?ev={v.value_id}", f"/fragments/evidence/{v.value_id}", "/signals",
            f"/signals/{e['id']}/0", "/relationships", "/journal", f"/journal/{v.value_id}", "/completeness",
            f"/watchlist?ids={e['id']}", "/watchlist", "/data", "/about", "/como-se-hizo", "/fuentes", "/sources",
            "/case-file?path=brief.md"]


def test_every_product_route_renders_in_both_languages(make_client, run):
    for lang in ("es", "en"):
        c = make_client(lang=lang)
        for path in product_paths(run):
            r = c.get(path)
            assert r.status_code == 200, (lang, path)
            assert "built-in method" not in r.text and "Undefined" not in r.text, (lang, path)
            if not path.startswith("/fragments"):
                assert f'<html lang="{lang}">' in r.text, (lang, path)


def test_spanish_is_the_default_and_lang_switch_sticks(client, store, fixture_root):
    from fastapi.testclient import TestClient
    from proveedor_app.web import Settings, create_app

    fresh = TestClient(create_app(Settings(store=store, case_dir=fixture_root / "case")))
    home = fresh.get("/").text
    assert '<html lang="es">' in home and "¿Quién recibe dinero público?" in home
    assert "Proveedores" in home  # the app's Spanish label for the ontology id, not the export's English
    r = fresh.get("/?lang=en")
    assert "Who receives public money?" in r.text and r.cookies.get(i18n.COOKIE) == "en"
    assert '<html lang="en">' in fresh.get("/signals").text  # the cookie keeps the choice
    assert 'href="/signals?lang=es"' in fresh.get("/signals").text  # the switch links back


def test_home_tally_is_recomputed_from_gold(es, run):
    stats = dataset_stats(run)
    complete = sum(dod.dod_ratio(e, run.domain) >= run.domain.dod_threshold for e in run.primary)
    assert stats["total"] == len(run.primary) == 60 and stats["complete"] == complete
    assert stats["flagged"] == sum(1 for e in run.primary if e.get("flags"))
    sources = {ev["source_id"] for ref in run.values.values() for ev in ref.data.get("evidence") or []}
    assert stats["sources"] == len(sources)
    text = es.get("/").text
    assert f"<dd>{stats['total']}</dd>" in text and f"<dd>{stats['flagged']}</dd>" in text
    assert sum(es.get(f"/?page={n}").text.count('class="roster__item"') for n in (1, 2, 3)) == 60


def test_dossier_shows_a_receipt_on_every_value(es, run):
    e = run.primary[0]
    text = es.get(f"/entities/{e['id']}").text
    for f in e["properties"].values():
        if f.get("evidence"):
            ev = f["evidence"][0]
            assert f'data-evidence="{f["value_id"]}"' in text
            assert re.sub(r"^https?://([^/]+).*", r"\1", ev["url"]) in text  # source host inline
    for line in ("<dt>Fuente</dt>", "<dt>Captura</dt>", "<dt>Lugar</dt>", "<dt>Confianza</dt>"):  # mono receipt lines
        assert line in text, line
    assert "Ver comprobante" in text and 'class="fact slip' in text
    words = {"gold": "Confirmado", "conflict": "Fuentes en desacuerdo", "missing": "No encontrado"}
    for status in {f.get("status") or "missing" for f in e["properties"].values()}:  # the stamp names the status
        assert f'<span class="status status--{status}">{words[status]}</span>' in text
    assert "Agregar a mi lista" in text and f"/export/entities.csv?ids={e['id']}".replace(":", "%3A") in text


def test_receipt_carries_screenshot_link_and_capture_time(es, run):
    ref = next(r for r in run.values.values() if (r.data.get("evidence") or [{}])[0].get("screenshot_key"))
    ev = ref.data["evidence"][0]
    text = es.get(f"/fragments/evidence/{ref.value_id}").text
    assert ev["url"] in text and "/bronze/" in text and "<dt>Captura</dt>" in text
    assert i18n.date_label(ev["captured_at"], "es", with_time=True) in text


def test_signal_is_framed_as_a_signal_with_a_dispute_path(es, run):
    e = next(x for x in run.primary if x.get("flags"))
    text = es.get(f"/signals/{e['id']}/0").text
    assert "Esto no es una acusación" in text and 'id="dispute"' in text
    assert "github.com/ricalanis/proveedor-abierto/issues/new" in text and 'id="dispute-record"' in text
    assert e["flags"][0]["rule_id"] in text  # the dispute record names the rule
    for page in ("/", "/signals", f"/entities/{e['id']}", f"/signals/{e['id']}/0", "/about"):
        body = es.get(page).text.lower()
        for word in ("corrupto", "culpable", "fraudulent", "probabilidad de corrupción"):
            assert word not in body, (page, word)


def test_completeness_page_is_plain_and_matches_gold(es, run):
    text = es.get("/completeness").text
    complete = sum(dod.dod_ratio(e, run.domain) >= run.domain.dod_threshold for e in run.primary)
    assert f'<span class="headline-figure__num">{complete}</span>' in text
    assert "Dato por dato" in text and "En qué puedes confiar" in text
    assert "mode_counts" not in text and "D0" not in text  # engine internals are not on the product page


def test_open_data_page_links_every_export(es):
    text = es.get("/data").text
    for name in ("entities.csv", "ocds.json", "gold.ttl"):
        assert f'href="/export/{name}"' in text
    assert es.get("/export/entities.csv").status_code == 200


def test_about_explains_statuses_and_disputes(es):
    text = es.get("/about").text
    assert 'id="dispute"' in text and "Las señales no son acusaciones" in text
    for word in ("Confirmado", "Fuentes en desacuerdo", "No encontrado"):
        assert word in text


def test_practice_data_banner_stays_on_synthetic_data(es):
    assert "Datos de práctica." in es.get("/").text


def test_product_nav_has_no_control_surface(make_client):
    home = make_client(lang="es").get("/").text
    nav = home.split('<nav class="tabs"', 1)[1].split("</nav>", 1)[0]
    for control in ("/run", "/engine", "/spend", "/evidence", "/approvals"):
        assert f'href="{control}"' not in nav


def test_every_template_string_has_spanish():
    missing = []
    for path in TEMPLATES.glob("*.html"):
        for m in CALL.finditer(path.read_text()):
            texts = [m.group(3)] + ([m.group(5)] if m.group(1) == "ngettext" and m.group(5) else [])
            missing += [(path.name, t) for t in texts if t not in i18n.ES]
    assert missing == []


def test_dynamic_labels_have_spanish():
    from proveedor_app.web import STATUS_WORDS

    dynamic = [*STATUS_WORDS.values(), "high", "medium", "low", "unknown", *investigate.PHASE_NAMES.values(),
               "Brief", "Global PRD", "Ontology", "Objectives", "Technical definition document"]
    assert [t for t in dynamic if t not in i18n.ES] == []


def test_date_labels_and_confidence_words():
    assert i18n.date_label("2026-09-26T18:05:00Z", "es") == "26 sep 2026"
    assert i18n.date_label("2026-09-26T18:05:00Z", "en") == "Sep 26, 2026"
    assert i18n.date_label("2026-09-26T18:05:00+00:00", "es", with_time=True) == "26 sep 2026, 18:05 UTC"
    assert i18n.date_label("not a date") == "not a date" and i18n.date_label(None) == "—"
    assert [confidence_level(x) for x in (0.95, 0.9, 0.75, 0.2, None)] == ["high", "high", "medium", "low", "unknown"]
    assert i18n.pick_lang("fr", "en") == "en" and i18n.pick_lang(None, None) == "es"


def test_ontology_labels_localize_by_id_without_changing_the_export(monkeypatch):
    onto = {"primary_class": "thing", "classes": [{"id": "thing", "label": "Thing"}],
            "properties": [{"id": "name", "label": "Name", "domain": "thing"}],
            "rules": [{"id": "r", "label": "Rule", "checks": "Checks"}]}
    monkeypatch.setitem(i18n.ONTOLOGY_LABELS, "es", {"thing": {"label": "Cosa"}, "r": {"checks": "Revisa"}})
    d = Domain.from_ontology(onto)
    es = d.localized("es")
    assert es.class_label() == "Cosa" and es.prop_label("name") == "Name" and es.rule("r")["checks"] == "Revisa"
    assert d.localized("en") is d and d.class_label() == "Thing"
    assert onto["classes"] == [{"id": "thing", "label": "Thing"}]  # the export itself is never rewritten
    assert localize_ontology({"classes": [{"id": "x", "label": "X"}]}, {}) == {"classes": [{"id": "x", "label": "X"}]}


def test_fixture_exports_carry_no_app_fields(fixture_root):
    """The fixtures are engine-shaped exports: translations live in the app (i18n.ONTOLOGY_ES), not in the data."""
    for path in (fixture_root / "lake").rglob("*.json*"):
        assert "_es\"" not in path.read_text(), path
    assert "_es\"" not in (fixture_root / "case" / "02-ontology" / "ontology.json").read_text()


def test_where_labels_have_spanish():
    from proveedor_app.web import WHERE_LABELS

    assert [t for t in [*WHERE_LABELS.values(), "Where in the source"] if t not in i18n.ES] == []

"""Headless-browser smoke tests: a real server, a real Chromium, the never-cut flows."""

import socket
import threading
import time

import pytest
import uvicorn
from proveedor_app.web import Settings, create_app

pytestmark = pytest.mark.ui
sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def base_url(fixture_root, store):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    app = create_app(Settings(store=store, case_dir=fixture_root / "case"))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda exc: errors.append(str(exc)))
    yield pg
    ctx.close()
    assert errors == []


def test_dossier_evidence_click_shows_source_link(page, base_url, store):
    page.goto(base_url + "/")
    page.locator("a.roster__name", has_text="Proveedor Ejemplo 05").click()
    page.wait_for_url("**/entities/sup:fixture-005")
    assert page.locator("h1").inner_text() == "Proveedor Ejemplo 05 S.A. de C.V."

    field = store.run().entities_by_id["sup:fixture-005"]["properties"]["tax_id"]
    page.locator(f'a.ev-link[data-evidence="{field["value_id"]}"]').click()
    link = page.locator("#evidence-panel a.source-link").first
    link.wait_for()
    assert link.get_attribute("href") == field["evidence"][0]["url"]
    assert link.get_attribute("rel") == "noopener noreferrer nofollow"
    assert "is-selected" in page.locator(f'li[id="row-{field["value_id"]}"]').get_attribute("class")
    img = page.locator("#evidence-panel figure.shot img").first
    img.wait_for()
    page.wait_for_function("img => img.complete && img.naturalWidth > 0", arg=img.element_handle())
    assert "#evidence" in page.url  # state is linkable


def test_signal_evidence_link_opens_capture(page, base_url):
    page.goto(base_url + "/suppliers/sup:fixture-005")
    page.locator(".signal a[data-evidence]").first.click()
    page.locator("#evidence-panel a.source-link").first.wait_for()


def test_no_js_evidence_fallback(browser, base_url, store):
    ctx = browser.new_context(java_script_enabled=False)
    pg = ctx.new_page()
    field = store.run().entities_by_id["sup:fixture-001"]["properties"]["address"]
    pg.goto(base_url + "/suppliers/sup:fixture-001")
    pg.locator(f'a.ev-link[data-evidence="{field["value_id"]}"]').click()
    assert pg.locator("#evidence-panel a.source-link").first.get_attribute("href") == field["evidence"][0]["url"]
    ctx.close()


def test_completeness_view(page, base_url, store):
    page.goto(base_url + "/completeness")
    rows = page.locator("#field-bars tbody tr")
    assert rows.count() == 6
    run = store.run()
    first = run.metrics["dod"][1]
    page.locator("details.tech summary").click()  # the engine's own criteria sit behind a disclosure
    tile = page.locator(f'.dod__item[data-key="{first["criterion_id"]}"]')
    assert tile.locator(".dod__num").inner_text() == str(first["actual"])
    assert first["query"] in tile.inner_text()
    assert "coinciden" in page.locator("#crosscheck").inner_text()  # Spanish by default


@pytest.mark.parametrize("width", [320, 375, 390, 414, 768, 1280])
def test_no_horizontal_scroll(browser, base_url, width):
    ctx = browser.new_context(viewport={"width": width, "height": 800})
    pg = ctx.new_page()
    for path in ("/", "/suppliers/sup:fixture-007", "/completeness", "/signals", "/signals/sup:fixture-005/0",
                 "/relationships", "/journal", "/journal/val:0001-008-founding_date", "/watchlist?ids=sup:fixture-005",
                 "/data", "/about", "/?lang=en", "/suppliers/sup:fixture-007?ev=val:0001-007-address"):
        pg.goto(base_url + path)
        assert pg.evaluate("document.documentElement.scrollWidth") <= width, path
    ctx.close()


def test_evidence_to_journal_to_brief(page, base_url):
    page.goto(base_url + "/suppliers/sup:fixture-008")
    page.locator("a.ev-link[data-evidence$='founding_date']").click()
    page.locator("#evidence-panel a", has_text="Cómo obtuvimos este dato").click()
    page.wait_for_url("**/journal/**")
    assert page.locator(".stop__phase", has_text="Fase 1").count() >= 1
    assert "Who receives public money" in page.locator(".stop--anchor").last.inner_text()


def test_watch_toggle_feeds_watchlist(page, base_url):
    page.goto(base_url + "/suppliers/sup:fixture-003")
    btn = page.locator("[data-watch]")
    btn.click()
    assert btn.get_attribute("aria-pressed") == "true"
    page.goto(base_url + "/watchlist")
    page.wait_for_url("**/watchlist?ids=*")
    assert page.locator(".watch__item a.entity").inner_text() == "Proveedor Ejemplo 03 S.A. de C.V."
    page.locator("[data-unwatch]").click()
    page.wait_for_url("**/watchlist?ids=")
    assert page.locator(".watch__item").count() == 0


def test_engine_report_card_renders(page, base_url):
    page.goto(base_url + "/engine")
    assert page.locator("h1").inner_text() == "Engine report card"
    assert page.locator(".taxonomy").count() >= 2
    assert page.locator(".mock-tag").count() >= 4  # fixtures declare recorded provenance


def test_loop_thread_toggles_and_fits_a_phone(browser, base_url):
    """v0.9.6: the phase-loop thread is a real <details> the reader can close and reopen, and the run view with it
    open has no horizontal scroll at 390 px."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda exc: errors.append(str(exc)))
    pg.goto(base_url + "/run/run-fixture-0001?limit=2000")
    thread = pg.locator("#loop-p1-1 details.loop")
    assert thread.evaluate("d => d.open")
    thread.locator("summary").scroll_into_view_if_needed()
    assert pg.evaluate("document.documentElement.scrollWidth") <= 390
    thread.locator("summary").click()
    assert not thread.evaluate("d => d.open")
    thread.locator("summary").click()
    assert thread.evaluate("d => d.open") and pg.locator("#loop-p1-1 .objections li").count() == 2
    assert pg.evaluate("document.documentElement.scrollWidth") <= 390
    ctx.close()
    assert errors == []

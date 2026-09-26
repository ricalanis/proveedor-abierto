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
    page.locator("a.entity", has_text="Proveedor Ejemplo 05").click()
    page.wait_for_url("**/suppliers/sup:fixture-005")
    assert page.locator("h1").inner_text() == "Proveedor Ejemplo 05 S.A. de C.V."

    field = store.run().suppliers_by_id["sup:fixture-005"]["fields"]["tax_id"]
    page.locator(f'a.ev-link[data-evidence="{field["value_id"]}"]').click()
    link = page.locator("#evidence-panel a.source-link").first
    link.wait_for()
    assert link.get_attribute("href") == field["evidence"][0]["url"]
    assert link.get_attribute("rel") == "noopener noreferrer nofollow"
    assert page.locator(f'tr[id="row-{field["value_id"]}"]').get_attribute("class") == "is-selected"
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
    field = store.run().suppliers_by_id["sup:fixture-001"]["fields"]["address"]
    pg.goto(base_url + "/suppliers/sup:fixture-001")
    pg.locator(f'a.ev-link[data-evidence="{field["value_id"]}"]').click()
    assert pg.locator("#evidence-panel a.source-link").first.get_attribute("href") == field["evidence"][0]["url"]
    ctx.close()


def test_completeness_view(page, base_url, store):
    page.goto(base_url + "/completeness")
    rows = page.locator("#field-bars tbody tr")
    assert rows.count() == 6
    assert page.locator(".dod__item[data-key=suppliers_at_80pct_core] .dod__num").inner_text() == str(
        store.run().metrics["suppliers_at_80pct_core"]
    )
    assert "matches" in page.locator("#crosscheck").inner_text()


@pytest.mark.parametrize("width", [320, 375, 414, 768])
def test_no_horizontal_scroll(browser, base_url, width):
    ctx = browser.new_context(viewport={"width": width, "height": 800})
    pg = ctx.new_page()
    for path in ("/", "/suppliers/sup:fixture-007", "/completeness"):
        pg.goto(base_url + path)
        assert pg.evaluate("document.documentElement.scrollWidth") <= width, path
    ctx.close()

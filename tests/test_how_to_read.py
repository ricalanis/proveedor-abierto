"""¿Cómo leer esta ficha?: reachable from every dossier, illustrated with a real receipt from the data, honest on
empty data, in both languages, and it fits phones."""

import pytest


def test_every_dossier_links_the_guide(make_client, store):
    c = make_client(lang="es")
    for e in store.run().primary[:10]:
        page = c.get(f"/entities/{e['id']}").text
        assert 'href="/como-leer"' in page and "¿Cómo leer esta ficha?" in page
        assert 'href="/como-leer#receipt"' in page  # from the receipt panel too
    assert 'href="/como-leer"' in c.get("/").text  # footer


def test_guide_uses_a_real_receipt(make_client, store):
    page = make_client(lang="es").get("/como-leer").text
    assert "Un comprobante real de estos datos" in page and 'class="fact slip fact--gold"' in page
    for word in ("Los tres sellos", "Sello sólido", "Sello discontinuo", "Sello punteado", "Qué es una señal",
                 "No es", "Si algo está mal", "github.com/ricalanis/proveedor-abierto/issues/new"):
        assert word in page, word
    run = store.run()
    ids = {f["value_id"] for e in run.primary for f in e["properties"].values() if f.get("value_id")}
    from urllib.parse import quote

    assert any(quote(vid, safe='') in page for vid in ids)  # the example links to an actual value's receipt
    en = make_client(lang="en").get("/how-to-read").text
    assert "How to read this profile?" in en and "The three stamps" in en


def test_guide_without_data(tmp_path):
    from fastapi.testclient import TestClient
    from proveedor_app.gold import UnavailableStore
    from proveedor_app.web import Settings, create_app

    c = TestClient(create_app(Settings(store=UnavailableStore("no lake"), case_dir=tmp_path)))
    r = c.get("/como-leer")
    assert r.status_code == 200 and "Los tres sellos" in r.text and "Un comprobante real" not in r.text


@pytest.mark.ui
@pytest.mark.parametrize(("width", "scheme"), [(1280, "dark"), (390, "light")])
def test_guide_fits(fixture_root, store, width, scheme):
    sync_api = pytest.importorskip("playwright.sync_api")
    import socket
    import threading
    import time

    import uvicorn
    from proveedor_app.web import Settings, create_app

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(create_app(Settings(store=store, case_dir=fixture_root / "case")),
                                        host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=srv.run, daemon=True).start()
    while not srv.started:
        time.sleep(0.05)
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
            for path in ("/como-leer", f"/entities/{store.run().primary[0]['id']}"):
                pg.goto(f"http://127.0.0.1:{port}{path}")
                assert pg.evaluate("document.documentElement.scrollWidth") <= width, path
            pg.goto(f"http://127.0.0.1:{port}/como-leer")
            pg.screenshot(path=f"/private/tmp/claude-501/-Users-ricalanis-dev-public-agents-hackathon-proveedor-abierto/1aeeb05d-1c17-4465-9835-689720f90787/scratchpad/pa-shots/como-leer-{width}.png", full_page=True)
            b.close()
    finally:
        srv.should_exit = True

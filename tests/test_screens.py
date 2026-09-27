"""The screenshot kit (R13): captures the product views at 1280/390 light/dark from a running server, writes a
manifest, redacts personal data; and the empty states point to the console tour when PA_CONSOLE_URL is set."""

import json

import pytest


def test_no_gold_points_to_the_tour(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from proveedor_app.gold import UnavailableStore
    from proveedor_app.web import Settings, create_app

    monkeypatch.setenv("PA_CONSOLE_URL", "https://console.example/")
    c = TestClient(create_app(Settings(store=UnavailableStore("no lake"), case_dir=tmp_path)))
    page = c.get("/").text
    assert 'href="https://console.example/tour"' in page and 'href="/como-se-hizo"' in page
    monkeypatch.delenv("PA_CONSOLE_URL")
    c = TestClient(create_app(Settings(store=UnavailableStore("no lake"), case_dir=tmp_path)))
    assert "console.example" not in c.get("/").text and "Aún no hay nada publicado" in c.get("/").text


@pytest.mark.ui
def test_kit_captures_product_views(fixture_root, store, tmp_path):
    pytest.importorskip("playwright.sync_api")
    import socket
    import threading
    import time

    import uvicorn
    from proveedor_app import screens
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
        out = tmp_path / "shots"
        m = screens.capture(out, product=f"http://127.0.0.1:{port}", console=None, targets=[],
                            only="product", log=lambda *_: None)
    finally:
        srv.should_exit = True
    names = {f["file"] for f in m["files"]}
    for view in ("home", "dossier", "dossier-receipt", "signal", "como-se-hizo", "como-leer", "fuentes"):
        for w, s in screens.MODES:
            assert f"product-{view}-{w}-{s}.png" in names, (view, w, s)
    assert all(f["status"] == 200 for f in m["files"]) and (out / "manifest.json").is_file()
    text = (out / "manifest.json").read_text()
    assert json.loads(text)["files"] and "127.0.0.1" not in text  # paths only, never the service address


@pytest.mark.ui
def test_redaction_hides_emails_and_declared_names():
    sync_api = pytest.importorskip("playwright.sync_api")
    from proveedor_app.screens import REDACT_JS

    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content("<p>Approved by ana@example.org</p><p>Ana Example (self-declared) · group:approvers</p>"
                       "<input value='x@y.org'>")
        assert pg.evaluate(REDACT_JS) == 3
        text = pg.inner_text("body")
        assert "ana@" not in text and "Ana Example" not in text and "group:approvers" in text and "[name]" in text
        b.close()


def test_the_kit_cannot_sign_in_or_store_sessions():
    import inspect

    from proveedor_app import cli, screens

    src = inspect.getsource(screens) + inspect.getsource(cli)
    assert "storage_state(" not in src and "def login" not in src and "--login" not in src

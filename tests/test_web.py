def test_index_lists_fixture_suppliers(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.text.count('class="roster__name"') == 25 and "page 1 of 3" in r.text
    assert client.get("/?page=3").text.count('class="roster__name"') == 10
    assert client.get("/?page=99").text.count('class="roster__name"') == 10  # clamped to the last page
    assert "Proveedor Ejemplo 01 S.A. de C.V." in r.text


def test_index_filters(client):
    assert client.get("/?q=Ejemplo 07").text.count('class="roster__name"') == 1
    signals = client.get("/?show=signals").text.count('class="roster__name"')
    assert 0 < signals <= 25


def test_dossier_shows_every_field_with_evidence_links(client, store):
    s = store.run().primary[4]
    r = client.get(f"/suppliers/{s['id']}")
    assert r.status_code == 200
    for f in s["properties"].values():
        if f["evidence"]:
            assert f'data-evidence="{f["value_id"]}"' in r.text


def test_dossier_server_renders_selected_evidence(client, store):
    s = store.run().primary[0]
    f = s["properties"]["tax_id"]
    r = client.get(f"/suppliers/{s['id']}", params={"ev": f["value_id"]})
    assert f["evidence"][0]["url"] in r.text
    assert f'/bronze/{f["evidence"][0]["screenshot_key"]}' in r.text.replace("%3A", ":")


def test_evidence_fragment_and_bronze(client, store):
    f = store.run().primary[0]["properties"]["address"]
    r = client.get(f"/fragments/evidence/{f['value_id']}")
    assert r.status_code == 200 and "source-link" in r.text
    img = client.get(f"/bronze/{f['evidence'][0]['screenshot_key']}")
    assert img.status_code == 200 and img.headers["content-type"].startswith("image/svg+xml")
    assert "sandbox" in img.headers["content-security-policy"]
    raw = client.get(f"/bronze/{f['evidence'][0]['bronze_key']}")
    assert raw.headers["content-type"].startswith("text/plain")


def test_unknown_things_404(client):
    assert client.get("/suppliers/sup:nope").status_code == 404
    assert client.get("/fragments/evidence/val:nope").status_code == 404
    assert client.get("/bronze/sha256:00").status_code == 404


def test_control_pages_are_gone(client):
    # operator and approver work moved to the Ontofill Console (CONTRACT §14)
    for path in ("/approvals", "/approvals/01-scope", "/run", "/run/run-fixture-0001", "/api/run/run-fixture-0001",
                 "/engine", "/spend", "/evidence"):
        assert client.get(path).status_code == 404, path
    assert client.post("/approvals", data={"phase_dir": "01-scope", "approver": "X"}).status_code in (404, 405)
    assert client.get("/healthz").json() == {"ok": True, "role": "investigator", "run_id": "run-fixture-0001"}

def test_index_lists_fixture_suppliers(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.text.count('class="entity"') == 60
    assert "Proveedor Ejemplo 01 S.A. de C.V." in r.text


def test_index_filters(client):
    assert client.get("/?q=Ejemplo 07").text.count('class="entity"') == 1
    signals = client.get("/?show=signals").text.count('class="entity"')
    assert 0 < signals < 60


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


def test_role_badge(make_client):
    assert "Investigator · read-only" in make_client().get("/").text
    assert "Approvals" in make_client(role="approver").get("/").text

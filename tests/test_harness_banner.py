"""A dataset built outside the engine (harness-assisted) is labelled on every page, in both languages, with its
caveats; the engine's own gold never shows the label."""


def test_harness_label_on_every_page(client, monkeypatch):
    monkeypatch.setenv("PA_PROVENANCE", "harness")
    for path in ("/", "/about"):
        es = client.get(path + "?lang=es").text
        assert "Corrida asistida por el arnés (Claude Code), no generada por el motor." in es
        assert "falta el registro público de comercio" in es
        en = client.get(path + "?lang=en").text
        assert "Harness-assisted run (Claude Code), not engine-authored." in en
        assert "not CompraNet" in en and "derived from each RFC" in en


def test_engine_gold_has_no_harness_label(client, monkeypatch):
    monkeypatch.delenv("PA_PROVENANCE", raising=False)
    assert "banner--harness" not in client.get("/?lang=en").text

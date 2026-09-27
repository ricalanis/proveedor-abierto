"""Flags not in the engine's shape (a harness-assisted export writes {"flag": ..., "values": [...]}) render with a
readable title in both languages and an explanation, never "None", and the CSV export does not break."""

from proveedor_app import gold, i18n


def test_foreign_flags_get_a_title_and_an_explanation():
    f = gold.normalize_flag({"flag": "address_variants", "values": ["Calle 1", "Calle 1, piso 2"]})
    assert f["rule_id"] == "address_variants" and f["label"] == "Address written differently across records"
    assert f["explanation"] == "Seen as: Calle 1 · Calle 1, piso 2" and f["evidence_value_ids"] == []
    assert i18n.ONTOLOGY_ES["address_variants"]["label"].startswith("Domicilio")
    unknown = gold.normalize_flag({"flag": "some_new_check", "note": "checked by hand"})
    assert unknown["label"] == "Some new check" and unknown["explanation"] == "checked by hand"


def test_engine_flags_are_kept_and_every_harness_kind_has_spanish():
    engine = {"rule_id": "r1", "label": "Rule one", "explanation": "x", "evidence_value_ids": ["val:1"]}
    assert gold.normalize_flag(engine) == engine
    assert set(gold.FLAG_LABELS) <= set(i18n.ONTOLOGY_ES)


def test_normalize_flags_drops_junk_and_fills_missing_rule_ids():
    es = gold.normalize_flags([{"id": "e", "flags": [None, {"flag": "sabg_sanctioned"}]}])
    assert es[0]["flags"] == [{"flag": "sabg_sanctioned", "rule_id": "sabg_sanctioned",
                               "label": "Listed in the federal sanctions directory (SABG)", "explanation": "",
                               "evidence_value_ids": []}]

import copy

from proveedor_app import dod
from proveedor_app.cli import main
from proveedor_app.domain import LEGACY_ONTOLOGY, Domain


def test_fixture_metrics_match_recomputation(store):
    run = store.run()
    assert run.layout == "entities" and run.domain.primary_class == "supplier"
    recomputed = dod.compute(run.entities, run.domain)
    assert dod.cross_check(recomputed, run.metrics, run.domain) == []
    rows = dod.criteria(recomputed, run.metrics, run.domain, "vultr", run.dod_queries, run.entities)
    assert [r["source"] for r in rows] == ["engine"] * len(rows)
    assert all(r["recomputed"] and r["agrees"] for r in rows)


def test_fixtures_are_obviously_fake(store):
    run = store.run()
    for e in run.primary:
        p = e["properties"]
        assert p["legal_name"]["value"].startswith("Proveedor Ejemplo ")
        if p["tax_id"]["value"]:
            assert p["tax_id"]["value"].startswith("ZZZ")
    for e in run.entities:
        for v in e["properties"].values():
            for ev in v["evidence"]:
                assert ev["url"].split("/")[2].endswith(".example")


def test_evidence_less_gold_value_is_counted(store):
    run = store.run()
    entities = copy.deepcopy(run.primary[:3])
    entities[0]["properties"]["address"]["status"] = "gold"
    entities[0]["properties"]["address"]["evidence"] = []
    m = dod.compute(entities, run.domain)
    assert m["values_without_evidence"] == 1
    assert m["per_property_completeness"]["supplier"]["address"] < 1


def test_cross_check_reports_mismatch(store):
    run = store.run()
    recomputed = dod.compute(run.entities, run.domain)
    engine = copy.deepcopy(run.metrics)
    engine["entities_meeting_dod"]["supplier"] += 1
    problems = dod.cross_check(recomputed, engine, run.domain)
    assert len(problems) == 1 and problems[0].startswith("entities_meeting_dod")


def test_dod_ratio_counts_only_gold_with_evidence():
    domain = Domain.from_ontology(LEGACY_ONTOLOGY)
    names = [p.id for p in domain.dod_props()]
    e = {"class": "supplier", "properties": {n: {"status": "gold", "evidence": [{}]} for n in names}}
    assert dod.dod_ratio(e, domain) == 1
    e["properties"]["tax_id"]["status"] = "conflict"
    assert dod.dod_ratio(e, domain) == 5 / 6


def test_criteria_default_and_mock():
    domain = Domain.from_ontology(LEGACY_ONTOLOGY)
    m = dod.compute([], domain)
    rows = dod.criteria(m, {}, domain)
    assert {r["source"] for r in rows} == {"default"} and rows[2]["met"] is True  # 0 values without evidence
    assert all(r["met"] is False and r["mock"] for r in dod.criteria(m, {}, domain, backend="recorded"))


def test_legacy_layout_through_the_adapter(tmp_path):
    from proveedor_app import fixtures
    from proveedor_app.gold import GoldStore, LocalSource

    lake = fixtures.generate(tmp_path, n_suppliers=12, layout="legacy")
    run = GoldStore(LocalSource(lake)).run()
    assert run.layout == "legacy" and run.domain.legacy and run.domain.primary_class == "supplier"
    assert len(run.primary) == 12 and any(e["class"] == "contract" for e in run.entities)
    recomputed = dod.compute(run.entities, run.domain)
    assert dod.cross_check(recomputed, run.metrics, run.domain) == []  # legacy metrics keys still cross-check


def test_cli_dod(fixture_root, capsys):
    assert main(["dod", "--gold-dir", str(fixture_root / "lake")]) == 0
    out = capsys.readouterr().out
    assert "cross-check vs engine metrics.json: match" in out and "primary class supplier" in out

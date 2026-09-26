import copy

from proveedor_app import CORE_FIELDS, dod
from proveedor_app.cli import main


def test_fixture_metrics_match_recomputation(store):
    run = store.run()
    assert dod.cross_check(dod.compute(run.suppliers), run.metrics) == []


def test_fixtures_are_obviously_fake(store):
    for s in store.run().suppliers:
        f = s["fields"]
        assert f["legal_name"]["value"].startswith("Proveedor Ejemplo ")
        if f["tax_id"]["value"]:
            assert f["tax_id"]["value"].startswith("ZZZ")
        for field in f.values():
            for e in field["evidence"]:
                assert e["url"].split("/")[2].endswith(".example")


def test_evidence_less_gold_value_is_counted(store):
    suppliers = copy.deepcopy(store.run().suppliers[:3])
    suppliers[0]["fields"]["address"]["status"] = "gold"
    suppliers[0]["fields"]["address"]["evidence"] = []
    m = dod.compute(suppliers)
    assert m["gold_values_without_evidence"] == 1
    assert m["per_field_completeness"]["address"] < 1


def test_cross_check_reports_mismatch(store):
    run = store.run()
    engine = dict(run.metrics, suppliers_at_80pct_core=run.metrics["suppliers_at_80pct_core"] + 1)
    problems = dod.cross_check(dod.compute(run.suppliers), engine)
    assert len(problems) == 1 and problems[0].startswith("suppliers_at_80pct_core")


def test_core_ratio_counts_only_gold_with_evidence():
    s = {"fields": {name: {"status": "gold", "evidence": [{}]} for name in CORE_FIELDS}}
    assert dod.core_ratio(s) == 1
    s["fields"]["tax_id"]["status"] = "conflict"
    assert dod.core_ratio(s) == 5 / 6


def test_cli_dod(fixture_root, capsys):
    assert main(["dod", "--gold-dir", str(fixture_root / "lake")]) == 0
    assert "cross-check vs engine metrics.json: match" in capsys.readouterr().out

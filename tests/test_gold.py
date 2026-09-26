import json

import pytest
from proveedor_app.gold import GoldStore, LocalSource, load_store, sniff_media_type


def test_latest_run_and_indexes(store):
    run = store.run()
    assert store.case_id == "fixture-case"
    assert run.run_id == "run-fixture-0001"
    assert store.run_ids() == ["run-fixture-0000", "run-fixture-0001"]
    assert len(run.suppliers) == 60
    s = run.suppliers[0]
    vid = s["fields"]["legal_name"]["value_id"]
    assert run.values[vid].supplier_id == s["id"]


def test_every_value_is_traceable_to_phase_1(store):
    run = store.run()
    for vid in run.values:
        if run.values[vid].data["status"] == "missing":
            continue
        chains = run.lineage(vid)
        assert chains, vid
        for chain in chains:
            assert [step["phase"] for step in chain] == [5, 4, 3, 2, 1], vid


def test_bronze_lookup_and_key_validation(store):
    ev = store.run().suppliers[0]["fields"]["legal_name"]["evidence"][0]
    shot = store.bronze(ev["screenshot_key"])
    assert shot and sniff_media_type(shot) == "image/svg+xml"
    assert store.bronze("sha256:../../etc/passwd") is None
    assert store.bronze("md5:abc") is None


def test_local_source_refuses_escape(tmp_path):
    with pytest.raises(ValueError):
        LocalSource(tmp_path).read("../outside")


def test_load_store_prefers_env_dir(fixture_root, tmp_path):
    st = load_store(tmp_path, {"PA_GOLD_DIR": str(fixture_root / "lake")})
    assert st.run().run_id == "run-fixture-0001"


def test_load_store_file_lake_yaml(fixture_root, tmp_path):
    (tmp_path / "lake.yaml").write_text(
        f"case_id: fixture-case\nbronze:\n  kind: file\n  root: {fixture_root / 'lake'}\n"
    )
    assert load_store(tmp_path, {}).run().run_id == "run-fixture-0001"


def test_bronze_meta_sidecar(store):
    ev = store.run().suppliers[0]["fields"]["legal_name"]["evidence"][0]
    assert store.bronze_meta(ev["screenshot_key"])["content_type"] == "image/svg+xml"
    assert store.bronze_meta("sha256:00") == {}


def test_load_store_without_config_explains(tmp_path):
    with pytest.raises(FileNotFoundError, match="PA_GOLD_DIR"):
        load_store(tmp_path, {})


def test_multiple_cases_need_case_id(tmp_path):
    for case in ("a", "b"):
        (tmp_path / "gold" / case).mkdir(parents=True)
    with pytest.raises(LookupError, match="PA_CASE_ID"):
        GoldStore(LocalSource(tmp_path))
    (tmp_path / "gold" / "a" / "latest.json").write_text(json.dumps({"run_id": "r1"}))
    assert GoldStore(LocalSource(tmp_path), case_id="a").latest_run_id() == "r1"

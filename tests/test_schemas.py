"""Validate the synthetic fixture export against the engine's contract JSON Schemas (ontofill/schemas)."""

import json
from pathlib import Path

import pytest


def _errors(validator, doc) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in validator.iter_errors(doc)]


def _run_dir(fixture_root: Path) -> Path:
    gold = fixture_root / "lake" / "gold" / "fixture-case"
    return gold / json.loads((gold / "latest.json").read_text())["run_id"]


@pytest.fixture(scope="session")
def legacy_root(tmp_path_factory) -> Path:
    from proveedor_app import fixtures

    out = tmp_path_factory.mktemp("legacy")
    fixtures.generate(out, layout="legacy")
    return out


def _jsonl_problems(path: Path, v, kind: str | None = None) -> list[str]:
    from conftest import s12_compat

    problems = []
    for i, line in enumerate(path.read_text().splitlines()):
        doc = json.loads(line)
        if kind:
            doc = s12_compat(doc, v.schema, kind)
        problems += [f"line {i + 1} {msg}" for msg in _errors(v, doc)]
    return problems


@pytest.mark.parametrize("filename,schema", [("entities.jsonl", "entity.schema.json"),
                                             ("trace.jsonl", "trace-step.schema.json")])
def test_jsonl_rows(fixture_root, validator_for, filename, schema):
    kind = "trace" if filename == "trace.jsonl" else None
    problems = _jsonl_problems(_run_dir(fixture_root) / filename, validator_for(schema), kind)
    assert not problems, f"{len(problems)} violations, first: {problems[:5]}"


@pytest.mark.parametrize("filename,schema", [("suppliers.jsonl", "supplier.schema.json"),
                                             ("contracts.jsonl", "contract.schema.json")])
def test_legacy_layout_rows(legacy_root, validator_for, filename, schema):
    """The pre-§11 layout the adapter still reads stays valid against the engine's legacy schemas."""
    problems = _jsonl_problems(_run_dir(legacy_root) / filename, validator_for(schema))
    assert not problems, f"{len(problems)} violations, first: {problems[:5]}"


def test_section11_run_artifacts(fixture_root, validator_for):
    run_dir = _run_dir(fixture_root)
    from conftest import s12_compat

    for name, schema in (("ontology.json", "ontology.schema.json"), ("dod-queries.json", "dod-queries.schema.json")):
        v = validator_for(schema)
        doc = json.loads((run_dir / name).read_text())
        if name == "dod-queries.json":
            doc = s12_compat(doc, v.schema, "dod_queries")
        errors = _errors(v, doc)
        assert not errors, (name, errors[:3])


def test_metrics_and_latest(fixture_root, validator_for):
    run_dir = _run_dir(fixture_root)
    from conftest import s12_compat

    v = validator_for("metrics.schema.json")
    assert not _errors(v, s12_compat(json.loads((run_dir / "metrics.json").read_text()), v.schema, "metrics"))
    latest = run_dir.parent / "latest.json"
    assert not _errors(validator_for("latest.schema.json"), json.loads(latest.read_text()))


def test_bronze_sidecars(fixture_root, validator_for):
    v = validator_for("bronze-sidecar.schema.json")
    sidecars = sorted((fixture_root / "lake" / "bronze" / "sha256").glob("*.meta.json"))[:20]
    assert sidecars
    problems = [f"{p.name} {msg}" for p in sidecars for msg in _errors(v, json.loads(p.read_text()))]
    assert not problems, f"{len(problems)} violations, first: {problems[:5]}"


def test_fixture_objectives(fixture_root, validator_for):
    import yaml

    doc = yaml.safe_load((fixture_root / "case" / "03-fanout" / "objectives.yaml").read_text())
    assert not _errors(validator_for("objectives.schema.json"), doc)


def test_lake_example_matches_engine_schema(validator_for):
    import yaml

    doc = yaml.safe_load((Path(__file__).parents[1] / "lake.example.yaml").read_text())
    assert not _errors(validator_for("lake-pointer.schema.json"), doc)

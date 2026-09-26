import json
import os
from pathlib import Path

import pytest
from proveedor_app import fixtures
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app


@pytest.fixture(scope="session")
def fixture_root(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("fixtures")
    fixtures.generate(out)
    return out


@pytest.fixture(scope="session")
def store(fixture_root) -> GoldStore:
    return GoldStore(LocalSource(fixture_root / "lake"))


@pytest.fixture
def make_client(fixture_root, store):
    from fastapi.testclient import TestClient

    def _make(role="investigator", case_dir=None):
        settings = Settings(store=store, case_dir=case_dir or fixture_root / "case", role=role)
        return TestClient(create_app(settings))

    return _make


@pytest.fixture
def client(make_client):
    return make_client()


SCHEMA_DIR = Path(os.environ.get("PA_ONTOFILL_SCHEMAS", Path(__file__).parents[1].parent / "ontofill" / "schemas"))
BASE = "https://ontofill.dev/schemas/"


@pytest.fixture(scope="session")
def validator_for():
    jsonschema = pytest.importorskip("jsonschema")
    referencing = pytest.importorskip("referencing")
    if not SCHEMA_DIR.is_dir():
        pytest.skip(f"engine schemas not found at {SCHEMA_DIR} (set PA_ONTOFILL_SCHEMAS)")
    from referencing.jsonschema import DRAFT202012

    resources = []
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text())
        res = referencing.Resource.from_contents(schema, default_specification=DRAFT202012)
        resources.append((schema.get("$id", BASE + path.name), res))
        resources.append((BASE + path.name, res))
    registry = referencing.Registry().with_resources(resources)

    def make(name: str):
        schema = json.loads((SCHEMA_DIR / name).read_text())
        return jsonschema.Draft202012Validator(
            schema, registry=registry, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
        )

    return make

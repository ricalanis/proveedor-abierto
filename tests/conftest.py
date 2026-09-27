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

    def _make(case_dir=None, lang="en"):
        settings = Settings(store=store, case_dir=case_dir or fixture_root / "case")
        client = TestClient(create_app(settings))
        client.cookies.set("pa_lang", lang)  # the product is Spanish-first; most tests read the English copy
        return client

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


def s12_compat(doc: dict, schema: dict, kind: str) -> dict:
    """CONTRACT §12 fields the fixtures emit ahead of the engine schemas: stripped only while the schema lacks them,
    so validation tightens automatically once ontofill publishes §12 support."""
    import copy

    doc = copy.deepcopy(doc)
    props = schema.get("properties") or {}
    if kind == "trace":
        for key in ("verify", "repair", "gate", "screen", "loop"):  # loop: CONTRACT v0.9.6
            if key not in props:
                doc.pop(key, None)
        if doc.get("event") not in (props.get("event") or {}).get("enum", [doc.get("event")]):
            doc["event"] = None
    elif kind == "jobs":
        for key in ("limits", "usage"):
            if key not in props:
                doc.pop(key, None)
        cps = ((props.get("checkpoints") or {}).get("properties") or {})
        if "secrets" not in cps:
            (doc.get("checkpoints") or {}).pop("secrets", None)
    elif kind == "metrics":  # v0.9.6 loops[]
        if "loops" not in props:
            doc.pop("loops", None)
    elif kind == "dod_queries":
        allowed = schema["$defs"]["query"]["properties"]["aggregate"]["enum"]
        doc["queries"] = [q for q in doc.get("queries") or [] if q.get("aggregate") in allowed]
    return doc


def v095_compat(doc: dict, schema: dict) -> dict:
    """CONTRACT v0.9.5 fields the fixture PRD emits ahead of the engine schema (`revisions`, and `basis` /
    `basis_quote` / `rationale` / `feasibility` per DoD criterion): stripped only while the schema lacks them."""
    import copy

    doc = copy.deepcopy(doc)
    if "revisions" not in (schema.get("properties") or {}):
        doc.pop("revisions", None)
    crit = ((schema.get("$defs") or {}).get("criterion") or {}).get("properties")
    if crit is not None and isinstance(doc.get("definition_of_done"), list):
        for c in doc["definition_of_done"]:
            for key in ("basis", "basis_quote", "rationale", "feasibility"):
                if key not in crit:
                    c.pop(key, None)
    return doc

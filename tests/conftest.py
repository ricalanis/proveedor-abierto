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

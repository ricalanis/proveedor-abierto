"""Real-data readiness: a recorded, real-shaped gold export (engine-valid records, hashed value ids, ontology ids the
app has never seen, a missing value with no value_id, list-membership booleans backed by the list's capture, a kept
conflict) renders with no practice-data banner, correct counts, and readable values (Sí/No, never True/False)."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from proveedor_app import dod
from proveedor_app.domain import Domain
from proveedor_app.gold import GoldStore, LocalSource
from proveedor_app.web import Settings, create_app

CASE_ID = "proveedor-abierto"
RUN = "run-3f9c2a1b7d4e"
AT = "2026-09-27T02:10:00Z"
GEN = {"backend": "vultr", "model": "extractor-model", "at": AT}
LIST_URL = "https://lista.example/descargas/listado-completo.csv"

ONTOLOGY = {
    "primary_class": "organization",
    "classes": [
        {"id": "organization", "label": "Organization", "label_plural": "Organizations", "title_property": "legal_name",
         "identifier_property": "tax_identifier", "description": "A legal entity that received public money"},
        {"id": "public_contract", "label": "Public contract", "label_plural": "Public contracts",
         "title_property": "contract_title", "identifier_property": "contract_title"},
    ],
    "properties": [
        {"id": "legal_name", "label": "Legal name", "domain": "organization", "datatype": "xsd:string", "dod": True, "order": 1},
        {"id": "tax_identifier", "label": "Tax identifier", "domain": "organization", "datatype": "xsd:string", "dod": True, "order": 2},
        {"id": "registered_address", "label": "Registered address", "domain": "organization", "datatype": "xsd:string", "dod": True, "order": 3},
        {"id": "incorporation_date", "label": "Incorporation date", "domain": "organization", "datatype": "xsd:date", "dod": True, "order": 4},
        {"id": "listed_on_published_list", "label": "Listed on the published list", "domain": "organization",
         "datatype": "xsd:boolean", "dod": True, "order": 5},
        {"id": "contract_title", "label": "Contract title", "domain": "public_contract", "datatype": "xsd:string", "order": 1},
        {"id": "contract_amount", "label": "Amount", "domain": "public_contract", "datatype": "xsd:decimal", "order": 2},
    ],
    "relations": [{"id": "awarded", "label": "Contracts awarded", "domain": "organization", "range": "public_contract",
                   "symmetric": False}],
    "rules": [],
    "source_classes": [{"id": "registry", "label": "Company registry"}, {"id": "published_list", "label": "Published list"}],
}


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def value_id(entity_id: str, prop: str, value) -> str:  # the engine's stable_value_id
    return "val:" + hashlib.sha256(_canonical([entity_id, prop, value]).encode()).hexdigest()[:24]


class Lake:
    def __init__(self, root: Path):
        self.root = root

    def put(self, data: bytes, content_type: str, url: str) -> str:
        hexd = hashlib.sha256(data).hexdigest()
        path = self.root / "bronze" / "sha256" / hexd
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        meta = {"content_type": content_type, "url": url, "captured_at": AT, "source_id": "src", "step_id": "step:x"}
        path.with_name(hexd + ".meta.json").write_text(json.dumps(meta))
        return f"sha256:{hexd}"


def build(root: Path) -> tuple[GoldStore, Path]:
    lake = Lake(root / "lake")
    shot = lake.put(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>', "image/svg+xml", "https://registro.example/")
    list_csv = lake.put(b"identifier,name\nAAA010101AA1,Listed Org\n", "text/csv", LIST_URL)

    def ev(url, source_id, source_type, bronze, selector, fmt="html"):
        return {"url": url, "bronze_key": bronze, "selector": selector, "screenshot_key": shot, "captured_at": AT,
                "source_id": source_id, "source_type": source_type, "format": fmt}

    def field(eid, prop, value, status="gold", evidence=None, confidence=0.93):
        f = {"value": value, "confidence": confidence, "status": status, "evidence": evidence or [], "generated_by": GEN}
        if status != "missing":
            f["value_id"] = value_id(eid, prop, value)
        return f

    reg = lambda eid, sel: ev(f"https://registro.example/org/{eid.split(':')[1]}", "registro", "registry", shot, sel)
    member = lambda: ev(LIST_URL, "lista", "published_list", list_csv, "identifier column, complete list", "csv")
    orgs = []
    for n, (name, tid, listed) in enumerate([("Organización Uno S.A.", "AAA010101AA1", True),
                                              ("Organización Dos S.C.", "BBB020202BB2", False),
                                              ("Organización Tres A.C.", "CCC030303CC3", False)], start=1):
        eid = f"organization:{tid.lower()}"
        props = {
            "legal_name": field(eid, "legal_name", name, evidence=[reg(eid, "h1")]),
            "tax_identifier": field(eid, "tax_identifier", tid, evidence=[reg(eid, "dd.tax")]),
            "registered_address": field(eid, "registered_address", f"Calle {n}, Ciudad Ejemplo", evidence=[reg(eid, "dd.addr")]),
            "incorporation_date": field(eid, "incorporation_date", f"2019-0{n}-15", evidence=[reg(eid, "dd.date")]),
            "listed_on_published_list": field(eid, "listed_on_published_list", listed, evidence=[member()], confidence=1.0),
        }
        orgs.append({"id": eid, "class": "organization", "classified_as": [], "properties": props, "links": [],
                     "flags": [], "generated_by": GEN})
    two, three = orgs[1], orgs[2]
    two["properties"]["incorporation_date"] = field(two["id"], "incorporation_date", None, status="missing", confidence=0.0)
    three["properties"]["registered_address"] = field(
        three["id"], "registered_address", "Calle 3, Ciudad Ejemplo", status="conflict", confidence=0.6,
        evidence=[reg(three["id"], "dd.addr"), ev("https://gaceta.example/2019/03/aviso", "gaceta", "registry", shot, "p.aviso")])
    contract = {"id": "public_contract:c-0001", "class": "public_contract", "classified_as": [], "flags": [], "links": [],
                "generated_by": GEN, "properties": {
                    "contract_title": field("public_contract:c-0001", "contract_title", "Servicio de ejemplo",
                                            evidence=[reg(orgs[0]["id"], "td.title")]),
                    "contract_amount": field("public_contract:c-0001", "contract_amount", 125000.5,
                                             evidence=[reg(orgs[0]["id"], "td.amount")])}}
    orgs[0]["links"].append({"property": "awarded", "target": contract["id"],
                             "via_value_id": contract["properties"]["contract_title"]["value_id"]})
    entities = orgs + [contract]
    vids = [f["value_id"] for e in entities for f in e["properties"].values() if f.get("value_id")]
    trace = [{"step_id": "step:p5-registro", "run_id": RUN, "phase": 5, "source_id": "registro", "objective_id": "obj-1",
              "tdd_path": "04-local/registro__obj-1/tdd.md", "mode": "D1", "observed": {"url": "https://registro.example/"},
              "requested": {"tool": "table.extract"}, "executed": {"rows": 3}, "evaluated": {"status": "ok"},
              "parent_step_id": None, "value_ids": vids, "ts": AT, "generated_by": GEN}]
    domain = Domain.from_ontology(ONTOLOGY)
    metrics = {"run_id": RUN, **{k: v for k, v in dod.compute(entities, domain).items() if k != "primary_class"},
               "inference_backend": "vultr", "dod": []}
    run_dir = root / "lake" / "gold" / CASE_ID / RUN
    run_dir.mkdir(parents=True)
    (run_dir / "entities.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entities))
    (run_dir / "trace.jsonl").write_text("".join(json.dumps(s) + "\n" for s in trace))
    (run_dir / "metrics.json").write_text(json.dumps(metrics))
    (run_dir / "ontology.json").write_text(json.dumps(ONTOLOGY))
    (root / "lake" / "gold" / CASE_ID / "latest.json").write_text(json.dumps({"run_id": RUN}))
    case = root / "case"
    (case / "01-scope").mkdir(parents=True)
    (case / "brief.md").write_text("# Brief\n\nWho receives public money, and are they legitimate?\n")
    return GoldStore(LocalSource(root / "lake")), case


@pytest.fixture
def real(tmp_path):
    store, case = build(tmp_path)
    return store, case


def client(real, lang="es"):
    store, case = real
    c = TestClient(create_app(Settings(store=store, case_dir=case)))
    c.cookies.set("pa_lang", lang)
    return c


def test_export_is_engine_valid(real, validator_for):
    store, _ = real
    v = validator_for("entity.schema.json")
    for e in store.run().entities:
        assert not list(v.iter_errors(e)), e["id"]


def test_real_gold_drops_the_practice_banner_and_counts_match(real):
    c = client(real)
    home = c.get("/").text
    assert "Datos de práctica" not in home and "Recolección simulada" not in home
    run = real[0].run()
    assert len(run.primary) == 3 and 'class="roster__item"' in home and home.count('class="roster__item"') == 3
    assert "Organizations" in home  # a label the app has no Spanish for falls back to the export's own


def test_membership_booleans_read_as_yes_no(real):
    run = real[0].run()
    for e in run.primary:
        page = client(real).get(f"/entities/{e['id']}").text
        listed = e["properties"]["listed_on_published_list"]["value"]
        fact = page.split("Listed on the published list", 1)[1][:1500]
        assert ("Sí" if listed else "No") in fact
        assert ">True<" not in page and ">False<" not in page and " True " not in fact and " False " not in fact
    en = client(real, "en").get(f"/entities/{run.primary[0]['id']}").text
    assert "Yes" in en.split("Listed on the published list", 1)[1][:1500]
    vid = run.primary[1]["properties"]["listed_on_published_list"]["value_id"]
    frag = client(real).get(f"/fragments/evidence/{vid}").text
    assert LIST_URL.split("//")[1].split("/")[0] in frag and ">No<" in frag  # the list is the receipt


def test_missing_and_conflict(real):
    run = real[0].run()
    two, three = run.primary[1], run.primary[2]
    page = client(real).get(f"/entities/{two['id']}").text
    assert "No se encontró en fuentes públicas" in page and "4 de 5 datos confirmados" in page
    page3 = client(real).get(f"/entities/{three['id']}").text
    assert "Fuentes en desacuerdo" in page3
    frag = client(real).get(f"/fragments/evidence/{three['properties']['registered_address']['value_id']}").text
    assert "gaceta.example" in frag and "registro.example" in frag


def test_every_page_renders_on_real_gold(real):
    run = real[0].run()
    e = run.primary[0]
    vid = e["properties"]["legal_name"]["value_id"]
    for path in ("/", "/signals", "/relationships", "/completeness", "/fuentes", "/como-se-hizo", "/data", "/about",
                 f"/entities/{e['id']}", f"/journal/{vid}", f"/watchlist?ids={e['id']}", "/export/entities.csv",
                 "/export/gold.ttl"):
        for lang in ("es", "en"):
            r = client(real, lang).get(path)
            assert r.status_code == 200, (path, lang)
            assert "built-in method" not in r.text and "Traceback" not in r.text
    signals = client(real).get("/signals").text
    assert "aún no publica sus reglas de señales" in signals  # R6 not landed: honest empty state
    csv = client(real).get("/export/entities.csv").text
    assert "Organización Uno S.A." in csv and ",true," in csv and ",false," in csv
    assert "True" not in csv and "False" not in csv


def test_rdf_booleans_are_valid(real):
    rdflib = pytest.importorskip("rdflib")
    ttl = client(real).get("/export/gold.ttl").text
    g = rdflib.Graph().parse(data=ttl, format="turtle")
    booleans = [o for o in g.objects() if isinstance(o, rdflib.Literal) and o.datatype == rdflib.XSD.boolean]
    assert {o.toPython() for o in booleans} == {True, False}


def test_value_labels():
    from proveedor_app import i18n

    assert i18n.value_label(True, "xsd:boolean", "es") == "Sí" and i18n.value_label(False, "", "es") == "No"
    assert i18n.value_label(True, "", "en") == "Yes" and i18n.value_label(None) == ""
    assert i18n.value_label("2019-03-15", "xsd:date", "es") == "15 mar 2019"
    assert i18n.value_label("not a date", "xsd:date", "es") == "not a date"
    assert i18n.value_label(3.0, "xsd:integer") == "3" and i18n.value_label(125000.5, "xsd:decimal") == "125000.5"


@pytest.mark.ui
@pytest.mark.parametrize(("width", "scheme"), [(1280, "dark"), (390, "light")])
def test_real_gold_fits_the_screen(real, width, scheme):
    sync_api = pytest.importorskip("playwright.sync_api")
    import socket
    import threading
    import time

    import uvicorn

    store, case = real
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(Settings(store=store, case_dir=case)), host="127.0.0.1",
                                           port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
            for path in ("/", f"/entities/{store.run().primary[2]['id']}", "/fuentes", "/completeness"):
                pg.goto(f"http://127.0.0.1:{port}{path}")
                assert pg.evaluate("document.documentElement.scrollWidth") <= width, path
            b.close()
    finally:
        server.should_exit = True

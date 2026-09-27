"""deploy/netbird_services.py against an in-memory fake of the NetBird API (no network)."""

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("netbird_services", Path(__file__).parents[1] / "deploy" / "netbird_services.py")
nbs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nbs)


class FakeApi:
    def __init__(self, peers):
        self.peers = peers
        self.groups = [{"id": "g-approvers", "name": "approvers"}]
        self.services = [{"id": "other", "name": "someone-else.eu1.netbird.services"}]
        self.calls = []

    def __call__(self, method, path, body=None):
        self.calls.append((method, path))
        if (method, path) == ("GET", "/peers"):
            return self.peers
        if (method, path) == ("GET", "/groups"):
            return self.groups
        if (method, path) == ("GET", "/reverse-proxies/domains"):
            return [{"domain": "eu1.netbird.services", "type": "free", "validated": True}]
        if (method, path) == ("GET", "/reverse-proxies/services"):
            return self.services
        if method == "POST":
            self.services.append({**body, "id": f"svc{len(self.services)}"})
            return self.services[-1]
        if method == "PUT":
            sid = path.rsplit("/", 1)[1]
            self.services = [{**body, "id": sid} if s["id"] == sid else s for s in self.services]
            return body
        if method == "DELETE":
            sid = path.rsplit("/", 1)[1]
            self.services = [s for s in self.services if s["id"] != sid]
            return None
        raise AssertionError((method, path))


VM = {"id": "p-vm", "name": "pa-control-plane", "os": "Linux Ubuntu 24.04", "ip": "100.64.0.10"}
LAPTOP = {"id": "p-laptop", "name": "some-laptop", "os": "Darwin 15", "ip": "100.64.0.2"}
ENV = {"PA_CONTROL_PLANE_PEER": "pa-control-plane", "PA_INVESTIGATOR_PASSWORD": "inv-secret",
       "PA_APPROVER_GROUP": "approvers", "PA_ALLOWED_COUNTRIES": "us, mx"}


def run(api, cmd, env=ENV):
    lines = []
    code = nbs.main([cmd], api=api, env=env, out=lines.append)
    return code, "\n".join(lines)


def test_plan_redacts_and_changes_nothing():
    api = FakeApi([VM, LAPTOP])
    code, text = run(api, "plan")
    assert code == 0 and "inv-secret" not in text and "<redacted>" in text
    assert "create proveedor.eu1.netbird.services" in text and "create ontofill-console.eu1.netbird.services" in text
    assert "proveedor-approver" not in text and "proveedor-replay" not in text
    assert not [c for c in api.calls if c[0] != "GET"]


def test_apply_creates_product_and_console_only_and_is_idempotent():
    api = FakeApi([VM, LAPTOP])
    assert run(api, "apply")[0] == 0
    assert run(api, "apply")[0] == 0  # second run updates, never duplicates
    mine = {s["name"]: s for s in api.services if s["id"] != "other"}
    assert set(mine) == {"proveedor.eu1.netbird.services", "ontofill-console.eu1.netbird.services"}
    assert sum(1 for c in api.calls if c[0] == "POST") == 2
    product, console = mine["proveedor.eu1.netbird.services"], mine["ontofill-console.eu1.netbird.services"]
    assert product["auth"] == {"password_auth": {"enabled": True, "password": "inv-secret"}}
    assert console["auth"] == {"bearer_auth": {"enabled": True, "distribution_groups": ["g-approvers"]}}
    target = product["targets"][0]
    assert (target["target_id"], target["host"], target["port"]) == ("p-vm", "100.64.0.10", 8400)
    assert console["targets"][0]["port"] == 8410
    assert product["access_restrictions"]["allowed_countries"] == ["US", "MX"]


def test_delete_only_touches_our_services():
    api = FakeApi([VM])
    run(api, "apply")
    code, _ = run(api, "delete")
    assert code == 0 and [s["id"] for s in api.services] == ["other"]


def test_retire_deletes_only_the_two_legacy_services():
    api = FakeApi([VM])
    run(api, "apply")
    api.services += [{"id": "old-app", "name": "proveedor-approver.eu1.netbird.services"},
                     {"id": "old-rep", "name": "proveedor-replay.eu1.netbird.services"},
                     {"id": "near", "name": "proveedor-approver-2.eu1.netbird.services"}]
    code, text = run(api, "retire", env={"PA_CONTROL_PLANE_PEER": "pa-control-plane"})  # needs no credentials
    assert code == 0 and "retired proveedor-approver.eu1.netbird.services" in text
    left = {s["name"] for s in api.services}
    assert "proveedor-approver.eu1.netbird.services" not in left and "proveedor-replay.eu1.netbird.services" not in left
    assert {"other" if s["id"] == "other" else s["name"] for s in api.services} >= {
        "other", "proveedor-approver-2.eu1.netbird.services", "proveedor.eu1.netbird.services",
        "ontofill-console.eu1.netbird.services"}
    assert [c for c in api.calls if c[0] == "DELETE"] == [("DELETE", "/reverse-proxies/services/old-app"),
                                                          ("DELETE", "/reverse-proxies/services/old-rep")]
    assert run(api, "retire")[0] == 0  # idempotent: nothing left to retire


def test_refuses_laptop_and_ambiguous_peers():
    code, text = run(FakeApi([LAPTOP]), "plan", {**ENV, "PA_CONTROL_PLANE_PEER": "some-laptop"})
    assert code == 1 and "not a Linux host" in text
    code, text = run(FakeApi([VM, {**VM, "id": "p2"}]), "plan")
    assert code == 1 and "exactly one peer" in text


def test_roles_need_distinct_credentials():
    for pin_key in ("PA_CONSOLE_PIN", "PA_APPROVER_PIN"):
        env = {"PA_CONTROL_PLANE_PEER": "pa-control-plane", "PA_INVESTIGATOR_PIN": "123456", pin_key: "123456"}
        code, text = run(FakeApi([VM]), "plan", env)
        assert code == 1 and "must not share" in text
    code, text = run(FakeApi([VM]), "plan", {"PA_CONTROL_PLANE_PEER": "pa-control-plane"})
    assert code == 1 and "PA_INVESTIGATOR" in text


def test_token_never_in_output(monkeypatch):
    monkeypatch.setenv("NETBIRD_API_TOKEN", "tok-should-not-leak")

    def failing(method, path, body=None):
        raise nbs.ApiError(f"{method} {path} -> HTTP 403: forbidden")

    code, text = run(failing, "plan")
    assert code == 1 and "tok-should-not-leak" not in text and json.dumps(ENV).find("tok") == -1

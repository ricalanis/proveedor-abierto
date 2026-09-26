"""Checkpoint deny with reason (CONTRACT v0.9.5): prd, factors and ontology can be sent back with a reason; the
approval screen shows earlier revisions, archived drafts, and where each definition-of-done number comes from."""

import json
import shutil
import socket
import threading
import time

import pytest
from proveedor_app import investigate

FACTOR_IDS = ["legitimacy_signal", "procedure_type", "economic_sector", "company_age", "buyer_level"]


@pytest.fixture
def case_copy(fixture_root, tmp_path):
    dst = tmp_path / "case"
    shutil.copytree(fixture_root / "case", dst)
    return dst


def _post(client, phase_dir, **data):
    return client.post("/approvals", data={"phase_dir": phase_dir, "approver": "Ana", **data}, follow_redirects=False)


def test_deny_without_reason_is_400_and_writes_nothing(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    for phase_dir in ("01-scope", "02-ontology/factors", "02-ontology"):
        for reason in ("", "   \n  "):
            r = _post(c, phase_dir, decision="deny", reason=reason)
            assert r.status_code == 400, phase_dir
            assert "Say why you deny it" in r.text and 'name="reason"' in r.text  # the form comes back with the error
            assert not (case_copy / phase_dir / "APPROVED").exists()


def test_deny_reason_length_cap(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    r = _post(c, "01-scope", decision="deny", reason="x" * (investigate.DENY_REASON_MAX + 1))
    assert r.status_code == 400 and "under 2000 characters" in r.text
    assert not (case_copy / "01-scope" / "APPROVED").exists()


def test_prd_deny_writes_the_v095_shape(make_client, case_copy, validator_for):
    c = make_client(role="approver", case_dir=case_copy)
    r = _post(c, "01-scope", decision="deny", reason="  DoD must be the case's:\n ≥50 suppliers  ")
    assert r.status_code == 303 and "done=01-scope" in r.headers["location"]
    marker = json.loads((case_copy / "01-scope" / "APPROVED").read_text())
    assert marker == {"approver": "Ana", "date": marker["date"], "checkpoint": "prd", "decision": "deny",
                      "reason": "DoD must be the case's: ≥50 suppliers"}
    assert not list(validator_for("approved.schema.json").iter_errors(marker))
    listing = c.get("/approvals?done=01-scope").text
    assert "Denied by Ana" in listing and "regenerates it with your reason" in listing
    assert "Denied by Ana" in c.get("/approvals/01-scope").text
    again = _post(c, "01-scope")  # one answer only
    assert "error=" in again.headers["location"]


def test_prd_approve_keeps_the_original_shape(make_client, case_copy, validator_for):
    c = make_client(role="approver", case_dir=case_copy)
    r = _post(c, "01-scope", decision="approve", reason="ignored on approve")
    assert "done=01-scope" in r.headers["location"]
    marker = json.loads((case_copy / "01-scope" / "APPROVED").read_text())
    assert marker == {"approver": "Ana", "date": marker["date"], "checkpoint": "prd"}  # decision absent = approve
    assert not list(validator_for("approved.schema.json").iter_errors(marker))


def test_ontology_deny(make_client, case_copy, validator_for):
    c = make_client(role="approver", case_dir=case_copy)
    r = _post(c, "02-ontology", decision="deny", reason="Merge the two address classes")
    assert "done=02-ontology" in r.headers["location"]
    marker = json.loads((case_copy / "02-ontology" / "APPROVED").read_text())
    assert marker["checkpoint"] == "ontology" and marker["decision"] == "deny"
    assert marker["reason"] == "Merge the two address classes" and "decisions" not in marker
    assert not list(validator_for("approved.schema.json").iter_errors(marker))


def test_factors_deny_carries_complete_factor_view_only(make_client, case_copy, validator_for):
    c = make_client(role="approver", case_dir=case_copy)
    # a deny does not need every factor decided (the engine proposes new ones), and a partial view is dropped
    r = _post(c, "02-ontology/factors", decision="deny", reason="Add a factor for the award amount",
              **{"decision.company_age": "reject"})
    assert "done=" in r.headers["location"]
    marker = json.loads((case_copy / "02-ontology/factors/APPROVED").read_text())
    assert marker == {"approver": "Ana", "date": marker["date"], "checkpoint": "factors", "decision": "deny",
                      "reason": "Add a factor for the award amount"}
    assert not list(validator_for("approved.schema.json").iter_errors(marker))


def test_factors_deny_with_full_view(make_client, case_copy, validator_for):
    c = make_client(role="approver", case_dir=case_copy)
    view = {f"decision.{i}": "reject" for i in FACTOR_IDS}  # all rejected is fine on a deny
    r = _post(c, "02-ontology/factors", decision="deny", reason="None of these separate suppliers", **view)
    assert "done=" in r.headers["location"]
    marker = json.loads((case_copy / "02-ontology/factors/APPROVED").read_text())
    assert marker["decision"] == "deny" and set(marker["decisions"]) == set(FACTOR_IDS)
    assert not list(validator_for("approved.schema.json").iter_errors(marker))


def test_factors_approve_unchanged(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    r = _post(c, "02-ontology/factors", decision="approve")  # approving still needs every factor decided
    assert "error=" in r.headers["location"]
    good = {f"decision.{i}": "accept" for i in FACTOR_IDS}
    r = _post(c, "02-ontology/factors", decision="approve", **good)
    marker = json.loads((case_copy / "02-ontology/factors/APPROVED").read_text())
    assert "decision" not in marker and marker["decisions"]["buyer_level"] == "accept"


def test_guards_still_hold(make_client, case_copy):
    inv = make_client(case_dir=case_copy)
    assert _post(inv, "01-scope", decision="deny", reason="x").status_code == 403
    apr = make_client(role="approver", case_dir=case_copy)
    r = apr.post("/approvals", data={"phase_dir": "01-scope", "approver": "Ana", "decision": "deny", "reason": "x"},
                 headers={"origin": "https://evil.example"})
    assert r.status_code == 403
    r = _post(apr, "01-scope", decision="deny", reason="x", approver="")
    assert "error=" in r.headers["location"]  # a name is still required
    assert not (case_copy / "01-scope" / "APPROVED").exists()


def test_review_shows_revisions_basis_and_archived_draft(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    page = c.get("/approvals/01-scope").text
    for needle in ("Earlier drafts", "DoD must follow the case definition", "Fixture Approver", "2026-09-26",
                   "basis--human", "basis--proposed", "basis--brief",
                   "Why this number: Four independent publisher kinds",
                   "Feasibility: About 1.20 USD", "Every claim must link to the public source it came from.", 'value="deny"', "Deny with reason", 'name="reason"',
                   "/case-file?path=01-scope/revisions/1/prd.json"):
        assert needle in page, needle
    draft = c.get("/case-file", params={"path": "01-scope/revisions/1/prd.json"})
    assert draft.status_code == 200 and "entities_with_canonical_record" in draft.text
    for bad in ("01-scope/revisions/../../../etc/passwd", "../outside/prd.json", "/etc/hosts",
                "01-scope/revisions/1/../../../../x"):
        assert c.get("/case-file", params={"path": bad}).status_code == 404, bad
    # the ontology and factors screens get the deny form too; the action screen keeps its own
    for phase_dir in ("02-ontology", "02-ontology/factors", "05-actions/req-0001"):
        assert 'value="deny"' in c.get(f"/approvals/{phase_dir}").text, phase_dir


def test_archived_request_is_not_a_live_checkpoint(case_copy):
    arch = case_copy / "01-scope" / "revisions" / "1"
    (arch / "APPROVAL_PENDING.md").write_text("---\ncheckpoint: prd\n---\narchived\n")
    items = investigate.approvals(investigate.CaseDir(case_copy))
    assert [a.phase_dir for a in items if "revisions" in a.phase_dir] == []


def test_revision_helpers():
    docs = {"prd": {"revisions": [{"n": 1, "decision": "deny", "reason": "a"}, {"n": 2, "decision": "deny"},
                                  "junk"]}}
    assert [r["n"] for r in investigate.revision_history(docs)] == [2, 1]
    assert investigate.revision_history({"prd": {}}) == []


@pytest.mark.ui
def test_deny_form_in_the_browser(fixture_root, store, tmp_path):
    sync_api = pytest.importorskip("playwright.sync_api")
    import uvicorn
    from proveedor_app.web import Settings, create_app

    case = tmp_path / "case"
    shutil.copytree(fixture_root / "case", case)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(Settings(store=store, case_dir=case, role="approver")),
                                           host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_api.sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(f"{base}/approvals/01-scope")
            page.fill("#approver", "Browser Approver")
            page.click("button:has-text('Deny with reason')")  # no reason: the server refuses, the form comes back
            page.wait_for_selector("text=Say why you deny it")
            assert not (case / "01-scope" / "APPROVED").exists()
            page.fill("#approver", "Browser Approver")
            page.fill("#reason", "Targets must come from the case definition")
            page.click("button:has-text('Deny with reason')")
            page.wait_for_selector("text=regenerates it with your reason")
            browser.close()
            assert errors == []
        marker = json.loads((case / "01-scope" / "APPROVED").read_text())
        assert marker["decision"] == "deny" and marker["reason"] == "Targets must come from the case definition"
        assert marker["approver"] == "Browser Approver" and marker["checkpoint"] == "prd"
    finally:
        server.should_exit = True
        thread.join(timeout=5)

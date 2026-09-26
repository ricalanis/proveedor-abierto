"""Approve-before-submit gate (CONTRACT §12 + v0.8.1 amendments): action requests are approved or denied by a person."""

import json
import shutil

import pytest

ACTION_DIR = "05-actions/req-0001"


@pytest.fixture
def case_copy(fixture_root, tmp_path):
    dst = tmp_path / "case"
    shutil.copytree(fixture_root / "case", dst)
    return dst


def _answer(client, **data):
    return client.post("/approvals", data={"phase_dir": ACTION_DIR, "approver": "Ana", **data},
                       follow_redirects=False)


def test_investigator_cannot_see_or_answer(make_client, case_copy):
    c = make_client(case_dir=case_copy)
    assert c.get(f"/approvals/{ACTION_DIR}").status_code == 403
    assert _answer(c, decision="approve").status_code == 403
    assert not (case_copy / ACTION_DIR / "APPROVED").exists()


def test_approver_sees_the_action_review(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    listing = c.get("/approvals").text
    assert "Action: Submit the search form on compras.example" in listing and "risk--high" in listing
    page = c.get(f"/approvals/{ACTION_DIR}").text
    for needle in ("Submit the search form on compras.example", "risk--high", "HIGH", "job:fixture-action-0001",
                   'value="approve"', 'value="deny"', 'name="reason"', "exactly this action, once",
                   "Screenshot not available"):
        assert needle in page, needle


def test_deny_needs_a_reason(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    r = _answer(c, decision="deny")  # v0.9.5: a deny without a reason is a bad request, re-rendered with the error
    assert r.status_code == 400 and "Say why you deny it" in r.text
    assert not (case_copy / ACTION_DIR / "APPROVED").exists()
    r = _answer(c)  # no decision at all
    assert "error=" in r.headers["location"] and not (case_copy / ACTION_DIR / "APPROVED").exists()


def test_deny_writes_decision_and_reason(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    r = _answer(c, decision="deny", reason="  Not needed:   the portal publishes a bulk file  ")
    assert "done=" in r.headers["location"]
    marker = json.loads((case_copy / ACTION_DIR / "APPROVED").read_text())
    assert marker == {"approver": "Ana", "date": marker["date"], "checkpoint": "action", "decision": "deny",
                      "reason": "Not needed: the portal publishes a bulk file"}
    assert "Denied by Ana" in c.get("/approvals").text
    assert "Denied by Ana" in c.get(f"/approvals/{ACTION_DIR}").text
    again = _answer(c, decision="approve")
    assert "error=" in again.headers["location"]  # one answer only
    assert json.loads((case_copy / ACTION_DIR / "APPROVED").read_text())["decision"] == "deny"


def test_approve_writes_decision(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    assert "done=" in _answer(c, decision="approve").headers["location"]
    marker = json.loads((case_copy / ACTION_DIR / "APPROVED").read_text())
    assert marker["decision"] == "approve" and marker["checkpoint"] == "action" and "reason" not in marker
    listing = c.get("/approvals").text
    assert "Approved by Ana" in listing


def test_unknown_decision_refused(make_client, case_copy):
    """v0.9.5 lets the prd/factors/ontology checkpoints be denied too (tests/test_approval_deny.py); a decision other
    than approve|deny is still refused everywhere."""
    c = make_client(role="approver", case_dir=case_copy)
    for phase_dir in ("01-scope", ACTION_DIR):
        r = c.post("/approvals", data={"phase_dir": phase_dir, "approver": "Ana", "decision": "maybe"},
                   follow_redirects=False)
        assert "error=" in r.headers["location"] and not (case_copy / phase_dir / "APPROVED").exists()


def test_cross_origin_answer_refused(make_client, case_copy):
    c = make_client(role="approver", case_dir=case_copy)
    r = c.post("/approvals", data={"phase_dir": ACTION_DIR, "approver": "Ana", "decision": "approve"},
               headers={"origin": "https://evil.example"})
    assert r.status_code == 403 and not (case_copy / ACTION_DIR / "APPROVED").exists()


@pytest.mark.xfail(strict=False, reason="ontofill approved.schema.json does not accept checkpoint 'action' / "
                                        "'decision' / 'reason' yet (CONTRACT §12 v0.8.1)")
def test_action_answer_matches_engine_schema(make_client, case_copy, validator_for):
    c = make_client(role="approver", case_dir=case_copy)
    _answer(c, decision="deny", reason="not needed")
    marker = json.loads((case_copy / ACTION_DIR / "APPROVED").read_text())
    assert not list(validator_for("approved.schema.json").iter_errors(marker))

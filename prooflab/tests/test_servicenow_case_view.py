"""case_view: the one JSON object per finding that the GUI renders."""
from __future__ import annotations

import hashlib
import json

import pytest

from prooflab.servicenow.analysis import ANALYSIS_MARKER
from prooflab.servicenow.case_view import CASE_SCHEMA, case_view, write_case_snapshot
from prooflab.servicenow.client import ServiceNowClient, ServiceNowError
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import Finding
from prooflab.servicenow.notifier import check_response, notify
from prooflab.tests.fake_servicenow import (CLIENT_ID, CLIENT_SECRET, INTEGRATION_USER, OWNER_USER,
                                            FakeServiceNow)

CUTOFF = "2026-10-05T12:00:00Z"
NOW = "2026-10-05T11:00:00Z"


@pytest.fixture()
def fake():
    server = FakeServiceNow().start()
    yield server
    server.stop()


@pytest.fixture()
def client(fake):
    return ServiceNowClient(base_url=fake.base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)


@pytest.fixture()
def log(tmp_path):
    return DeliveryLog(tmp_path / "delivery-log.jsonl")


def finding() -> Finding:
    return Finding(control_ref="C16", control_id="ACN-COST-001", threshold_version="G-FM-v1",
                   scope_kind="run", scope_id="FM-B", verdict="BREACHED",
                   summary="10,800 tokens > cap 10,000", detected_at="2026-10-05T10:00:00Z",
                   evidence=("gateway:action-123", "ledger:cid=fault-1"))


def view(client, log, **kw):
    return case_view(finding(), client, log, owner_user=OWNER_USER, cutoff=CUTOFF,
                     integration_user=INTEGRATION_USER, now=NOW, **kw)


def delivered(client, log):
    return notify(finding(), client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER)


def test_case_without_incident_says_so(client, log):
    case = view(client, log)
    assert case["schema"] == CASE_SCHEMA and case["finding_id"] == finding().finding_id
    assert case["servicenow"]["status"] == "no_incident"
    assert case["delivery"]["state"] == "NOT_SENT"
    assert case["response"]["state"] == "NOT_DELIVERED"
    assert case["agent_analysis"]["status"] == "not_applicable"


def test_delivered_case_shows_incident_owner_response_and_pending_analysis(client, fake, log):
    result = delivered(client, log)
    case = view(client, log, aict_url="https://example/aict")
    sn = case["servicenow"]
    assert sn["status"] == "ok" and sn["number"] == result.number
    assert sn["url"].endswith(f"/incident.do?sys_id={result.sys_id}")
    assert case["links"] == {"incident": sn["url"], "aict": "https://example/aict"}
    assert case["delivery"]["state"] == "DELIVERED" and case["delivery"]["number"] == result.number
    assert case["response"] == {"state": "AWAITING_RESPONSE", "actor": None, "at": None,
                                "cutoff": CUTOFF, "source": "live"}
    assert case["agent_analysis"] == {"status": "pending"}
    assert case["finding"]["evidence"] == ["gateway:action-123", "ledger:cid=fault-1"]


def test_agent_analysis_appears_when_the_note_is_written(client, fake, log):
    result = delivered(client, log)
    note = "\n".join([ANALYSIS_MARKER, f"Finding ID: {finding().finding_id}", "Verdict: BREACHED"])
    fake.incidents[result.sys_id]["work_notes"] = (
        f"2026-10-05 10:02:00 - iFabric Assurance Agent (Work notes)\n{note}")
    analysis = view(client, log)["agent_analysis"]
    assert analysis["status"] == "present" and analysis["fields"]["Verdict"] == "BREACHED"


def test_recorded_owner_response_survives_a_later_agent_update(client, fake, log):
    # itil only sees the last updater; the agent's note must not erase a logged reply.
    result = delivered(client, log)
    fake.human_update(result.sys_id, OWNER_USER, "2026-10-05 10:20:00")
    check_response(finding(), client, log, owner_user=OWNER_USER, cutoff=CUTOFF,
                   integration_user=INTEGRATION_USER, now=NOW)
    fake.human_update(result.sys_id, "ifabric.assurance.agent", "2026-10-05 10:30:00")
    response = view(client, log)["response"]
    assert response["state"] == "RESPONDED" and response["actor"] == OWNER_USER
    assert response["at"] == "2026-10-05 10:20:00" and response["source"] == "delivery_log"


def test_reference_fields_returned_as_objects_are_shown_as_text(client, fake, log):
    result = delivered(client, log)
    fake.incidents[result.sys_id]["assigned_to"] = {"display_value": "Sree Annapurna Rallabandi",
                                                    "link": "https://x/api/now/table/sys_user/1"}
    assert view(client, log)["servicenow"]["owner"] == "Sree Annapurna Rallabandi"


def test_case_view_never_writes_the_evidence_log(client, fake, log):
    delivered(client, log)
    before = log.path.read_text()
    view(client, log)
    view(client, log)
    assert log.path.read_text() == before


def test_unreachable_servicenow_is_reported_not_raised(client, log, monkeypatch):
    def down(*args, **kwargs):
        raise ServiceNowError(None, "timeout")
    monkeypatch.setattr(client, "find_incidents", down)
    case = view(client, log)
    assert case["servicenow"]["status"] == "unreachable" and "timeout" in case["servicenow"]["error"]
    assert case["response"]["state"] == "RESPONSE_UNKNOWN"
    assert case["agent_analysis"]["status"] == "unknown"


def test_snapshot_is_written_with_matching_sha256(client, log, tmp_path):
    case = view(client, log)
    path, digest = write_case_snapshot(case, tmp_path / "cases")
    assert path.name == "ifabric_C16_G-FM-v1_run_FM-B_finding.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert json.loads(path.read_text())["finding_id"] == finding().finding_id


def test_case_has_all_five_assurance_sections_with_honest_unknowns(client, fake, log):
    delivered(client, log)
    case = view(client, log)
    assert case["movement"]["steps"] == [] and case["movement"]["checks"][0]["status"] == "unknown"
    assert case["policy_alignment"]["total"] == 8
    statuses = {c["id"]: c["status"] for c in case["policy_alignment"]["checks"]}
    assert statuses["P4"] == "pass" and statuses["P1"] == "unknown"
    assert case["outcome_validation"]["status"] == "pending"
    assert [e["source"] for e in case["decision_trace"]][:1] == ["control"]
    assert case["evidence"][0] == {"ref": "gateway:action-123", "kind": "gateway", "used_by_agent": False}

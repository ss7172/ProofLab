"""Behaviour of the ServiceNow human-loop adapter, tested against a fake instance."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from prooflab.servicenow.client import ServiceNowClient, ServiceNowError
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import Finding, build_incident_payload, finding_from_dict
from prooflab.servicenow.analysis import ANALYSIS_MARKER
from prooflab.servicenow.notifier import check_response, export_incident, notify
from prooflab.tests.fake_servicenow import (CLIENT_ID, CLIENT_SECRET, INTEGRATION_SYS_ID,
                                            INTEGRATION_USER, OWNER_SYS_ID, OWNER_USER,
                                            FakeServiceNow)

CUTOFF = "2026-10-05T12:00:00Z"
AGENT_USER = "ifabric.assurance.agent"


# ---------------------------------------------------------------- fixtures
@pytest.fixture()
def fake():
    server = FakeServiceNow().start()
    yield server
    server.stop()


@pytest.fixture()
def client(fake):
    return ServiceNowClient(base_url=fake.base_url, client_id=CLIENT_ID,
                            client_secret=CLIENT_SECRET)


@pytest.fixture()
def log(tmp_path: Path) -> DeliveryLog:
    return DeliveryLog(tmp_path / "delivery-log.jsonl")


def breach(**overrides) -> Finding:
    base = dict(control_ref="C16", control_id="ACN-COST-001", threshold_version="G-FM-v1",
                scope_kind="run", scope_id="FM-B", verdict="BREACHED",
                summary="10,800 tokens > cap 10,000", detected_at="2026-10-05T10:00:00Z",
                evidence=("gateway:action-123", "ledger:cid=fault-1"))
    return Finding(**{**base, **overrides})


def send(client, log, **kw):
    return notify(breach(), client, log, owner_user=OWNER_USER,
                  integration_user=INTEGRATION_USER, **kw)


def check(client, log, now):
    return check_response(breach(), client, log, owner_user=OWNER_USER,
                          integration_user=INTEGRATION_USER, cutoff=CUTOFF, now=now)


def states(log):
    return [e["state"] for e in log.history(breach().finding_id)]


# ---------------------------------------------------------------- finding
def test_finding_id_is_deterministic_and_fits_correlation_field():
    a, b = breach(), breach()
    assert a.finding_id == b.finding_id
    assert a.finding_id.startswith("ifabric:")
    long = breach(scope_id="x" * 300)
    assert len(long.finding_id) <= 100
    assert long.finding_id != breach(scope_id="y" * 300).finding_id


def test_finding_id_changes_when_scope_or_version_changes():
    assert breach().finding_id != breach(scope_id="FM-C").finding_id
    assert breach().finding_id != breach(threshold_version="G-FM-v2").finding_id


def test_finding_from_dict_validates_required_fields():
    good = finding_from_dict({"control_ref": "C9", "control_id": "AIA-ARC-006",
                              "threshold_version": "D-v1", "scope_kind": "window",
                              "scope_id": "2026-10-05T09", "verdict": "BREACHED",
                              "summary": "latency +30%", "detected_at": "2026-10-05T10:00:00Z"})
    assert good.evidence == ()
    with pytest.raises(ValueError, match="control_id"):
        finding_from_dict({"control_ref": "C9"})
    with pytest.raises(ValueError, match="verdict"):
        finding_from_dict({**good.__dict__, "verdict": "MAYBE"})
    with pytest.raises(ValueError, match="scope_id"):
        finding_from_dict({**good.__dict__, "scope_id": "x^sys_created_by=other"})


def test_incident_payload_carries_tag_control_version_owner_and_correlation():
    f = breach()
    payload = build_incident_payload(f, assignee_sys_id="abc", team_tag="[iFabric]")
    assert payload["short_description"].startswith("[iFabric][C16 ACN-COST-001 v=G-FM-v1]")
    assert "FM-B" in payload["short_description"] and "BREACHED" in payload["short_description"]
    assert payload["assigned_to"] == "abc"
    assert payload["correlation_id"] == f.finding_id
    assert "ledger:cid=fault-1" in payload["work_notes"]
    assert payload["short_description"] and len(payload["short_description"]) <= 160


def test_description_carries_full_finding_for_readers_without_journal_access():
    # Record-operation tools and itil readers cannot see work notes, so the
    # description must hold every audit field, evidence references included.
    description = build_incident_payload(breach(), "abc", "[iFabric]")["description"]
    for expected in ("C16 ACN-COST-001", "threshold version G-FM-v1", "run FM-B",
                     "BREACHED - 10,800 tokens > cap 10,000", "2026-10-05T10:00:00Z",
                     "gateway:action-123", "ledger:cid=fault-1", breach().finding_id):
        assert expected in description


def test_description_stays_within_servicenow_field_limit():
    many = breach(evidence=tuple(f"gateway:action-{i:04d}-" + "x" * 80 for i in range(200)))
    description = build_incident_payload(many, "abc", "[iFabric]")["description"]
    assert len(description) <= 4000
    assert "more in the Evidence Pack" in description


def test_oversized_summary_is_truncated_to_field_limit():
    description = build_incident_payload(breach(summary="s" * 5000), "abc", "[iFabric]")["description"]
    assert len(description) == 4000 and "C16 ACN-COST-001" in description


# ---------------------------------------------------------------- client
def test_client_caches_oauth_token(client, fake):
    client.find_incidents("nothing", INTEGRATION_USER)
    client.find_incidents("nothing", INTEGRATION_USER)
    assert fake.token_requests == 1


def test_client_reports_bad_credentials_without_leaking_secret(fake):
    bad = ServiceNowClient(base_url=fake.base_url, client_id=CLIENT_ID, client_secret="wrong-secret")
    with pytest.raises(ServiceNowError) as err:
        bad.find_incidents("x", INTEGRATION_USER)
    assert err.value.status == 401
    assert "access_denied" in str(err.value) and "wrong-secret" not in str(err.value)


def test_client_resolves_owner_user(client):
    assert client.find_user_sys_id(OWNER_USER) == OWNER_SYS_ID
    with pytest.raises(ServiceNowError, match="not found"):
        client.find_user_sys_id("nobody@example.com")


def test_client_requires_https_for_real_hosts():
    with pytest.raises(ValueError, match="https"):
        ServiceNowClient(base_url="http://platformdemoh8.service-now.com", client_id="a", client_secret="b")
    ok = ServiceNowClient(base_url="https://platformdemoh8.service-now.com", client_id="a", client_secret="b")
    assert ok.base_url.startswith("https://")


def test_from_env_builds_https_url_from_bare_host(monkeypatch):
    monkeypatch.setenv("SNOW_INSTANCE", "httpteam.service-now.com")
    monkeypatch.setenv("SNOW_CLIENT_ID", "a")
    monkeypatch.setenv("SNOW_CLIENT_SECRET", "b")
    assert ServiceNowClient.from_env().base_url == "https://httpteam.service-now.com"


def test_gateway_errors_and_garbled_bodies_are_outcome_unknown():
    assert ServiceNowError(None, "x").outcome_unknown
    assert ServiceNowError(503, "x").outcome_unknown
    assert ServiceNowError(504, "x").outcome_unknown
    assert not ServiceNowError(400, "x").outcome_unknown
    assert not ServiceNowError(403, "x").outcome_unknown


# ---------------------------------------------------------------- notify
def test_notify_creates_reads_back_and_logs_each_step(client, fake, log):
    result = send(client, log)
    assert result.state == "DELIVERED"
    assert result.number.startswith("INC")
    assert fake.post_count == 1
    assert states(log) == ["INTENT", "SENT", "DELIVERED"]
    delivered = log.history(breach().finding_id)[-1]
    assert delivered["assigned_to"] == OWNER_SYS_ID and delivered["sys_id"] == result.sys_id


def test_notify_sets_caller_to_integration_user(client, fake, log):
    result = send(client, log)
    assert fake.incidents[result.sys_id]["caller_id"] == INTEGRATION_SYS_ID


def test_caller_lookup_failure_does_not_block_delivery(client, fake, log, monkeypatch):
    real_lookup = client.find_user_sys_id

    def lookup(user_name):
        if user_name == INTEGRATION_USER:
            raise ServiceNowError(404, "not found")
        return real_lookup(user_name)
    monkeypatch.setattr(client, "find_user_sys_id", lookup)
    result = send(client, log)
    assert result.state == "DELIVERED"
    assert "caller_id" not in fake.incidents[result.sys_id]
    assert log.history(breach().finding_id)[0]["caller"] is None


def test_export_writes_incident_and_notes_as_evidence(client, fake, log, tmp_path):
    result = send(client, log)
    fake.add_journal_entry(result.sys_id, OWNER_USER, "ack", "2026-10-05 10:20:00")
    path = export_incident(breach(), client, INTEGRATION_USER, tmp_path / "evidence")
    data = json.loads(path.read_text())
    assert path.name == f"{result.number}.json"
    assert data["finding_id"] == breach().finding_id
    assert data["incident"]["assigned_to"] == OWNER_SYS_ID
    assert data["journal"][0]["sys_created_by"] == OWNER_USER
    assert "exported_at" in data


def test_export_records_unreadable_notes_instead_of_crashing(client, fake, log, tmp_path):
    send(client, log)
    fake.journal_forbidden = True
    data = json.loads(export_incident(breach(), client, INTEGRATION_USER, tmp_path).read_text())
    assert data["journal"] is None
    assert "403" in data["journal_error"]
    assert data["incident"]["correlation_id"] == breach().finding_id


def test_export_includes_notes_text_from_incident(client, fake, log, tmp_path):
    result = send(client, log)
    fake.incidents[result.sys_id]["work_notes"] = "2026-10-05 06:59:29 - Sree (Work notes)\nAcknowledged"
    data = json.loads(export_incident(breach(), client, INTEGRATION_USER, tmp_path).read_text())
    assert "Acknowledged" in data["notes_display"]["work_notes"]
    assert data["agent_analysis"] == {"status": "pending"}


def test_export_includes_parsed_agent_analysis(client, fake, log, tmp_path):
    result = send(client, log)
    note = "\n".join([ANALYSIS_MARKER, f"Finding ID: {breach().finding_id}", "Verdict: BREACHED"])
    fake.incidents[result.sys_id]["work_notes"] = (
        f"2026-10-05 10:02:00 - iFabric Assurance Agent (Work notes)\n{note}\n\n"
        "2026-10-05 10:00:00 - iFabric Integration (Work notes)\nProofLab finding x")
    data = json.loads(export_incident(breach(), client, INTEGRATION_USER, tmp_path).read_text())
    analysis = data["agent_analysis"]
    assert analysis["status"] == "present" and analysis["fields"]["Verdict"] == "BREACHED"
    assert analysis["finding_matches"] and not analysis["complete"]


def test_export_without_incident_raises(client, tmp_path):
    with pytest.raises(LookupError):
        export_incident(breach(), client, INTEGRATION_USER, tmp_path)


def test_notify_is_idempotent_for_the_same_finding(client, fake, log):
    first = send(client, log)
    second = send(client, log)
    assert fake.post_count == 1
    assert second.sys_id == first.sys_id and second.reused is True
    assert len(fake.incidents) == 1


def test_other_teams_incident_with_same_correlation_is_ignored(client, fake, log):
    foreign = fake.add_foreign_incident(breach().finding_id)
    result = send(client, log)
    assert result.state == "DELIVERED" and result.sys_id != foreign
    assert fake.post_count == 1


def test_duplicate_own_incidents_are_flagged_and_oldest_used(client, fake, log):
    first = send(client, log)
    fake._create({**fake.incidents[first.sys_id], "assigned_to": OWNER_SYS_ID},
                  created_on="2026-10-05 11:00:00")
    again = send(client, log)
    assert again.sys_id == first.sys_id
    assert "DUPLICATE_CORRELATION" in states(log)


def test_reused_incident_reassigned_by_owner_is_still_delivered(client, fake, log):
    first = send(client, log)
    fake.human_update(first.sys_id, OWNER_USER, "2026-10-05 10:30:00", assigned_to="colleague")
    again = send(client, log)
    assert again.state == "DELIVERED" and again.reused is True


def test_dry_run_never_writes_to_servicenow(client, fake, log):
    result = send(client, log, dry_run=True)
    assert result.state == "DRY_RUN" and fake.post_count == 0
    entry = log.history(breach().finding_id)[-1]
    assert entry["payload"]["correlation_id"] == breach().finding_id


def test_rejected_create_is_logged_as_failed(client, fake, log):
    fake.fail_next_post_status = 400
    result = send(client, log)
    assert result.state == "FAILED"
    assert states(log)[-1] == "FAILED"


def test_lost_response_is_reconciled_instead_of_duplicated(client, fake, log):
    fake.drop_next_post_response = True
    result = send(client, log)
    assert "OUTCOME_UNKNOWN" in states(log)
    assert result.state == "DELIVERED" and result.reused is True
    assert log.history(breach().finding_id)[-1]["reconciled"] is True
    assert len(fake.incidents) == 1 and fake.post_count == 1


@pytest.mark.parametrize("status", [502, 503, 504])
def test_gateway_error_after_create_is_reconciled_not_failed(client, fake, log, status):
    fake.fail_after_create_status = status
    result = send(client, log)
    assert "OUTCOME_UNKNOWN" in states(log) and "FAILED" not in states(log)
    assert result.state == "DELIVERED" and len(fake.incidents) == 1


def test_garbled_success_body_is_reconciled(client, fake, log):
    fake.garble_next_post = True
    result = send(client, log)
    assert "OUTCOME_UNKNOWN" in states(log)
    assert result.state == "DELIVERED" and len(fake.incidents) == 1


def test_readback_mismatch_is_not_reported_as_delivered(client, fake, log):
    fake.override_assignee = "someone-else"
    result = send(client, log)
    assert result.state == "FAILED"
    assert log.history(breach().finding_id)[-1]["reason"] == "readback_mismatch"


def test_every_failure_path_ends_with_a_terminal_log_state(client, fake, log, monkeypatch):
    def broken(*args, **kwargs):
        raise ServiceNowError(401, "token revoked")
    monkeypatch.setattr(client, "get_incident", broken)
    result = send(client, log)
    assert result.state == "UNVERIFIED"  # created (SENT) but could not be read back
    assert states(log)[-2:] == ["SENT", "UNVERIFIED"]


def test_lookup_failure_before_create_is_logged(client, log, monkeypatch):
    def broken(*args, **kwargs):
        raise ServiceNowError(None, "timeout")
    monkeypatch.setattr(client, "find_incidents", broken)
    result = send(client, log)
    assert result.state == "FAILED" and result.reason == "lookup_failed"
    assert states(log)[-1] == "FAILED"


# ---------------------------------------------------------------- responses
def test_owner_note_is_recorded_as_response(client, fake, log):
    res = send(client, log)
    fake.add_journal_entry(res.sys_id, OWNER_USER, "Looking into it", "2026-10-05 10:20:00")
    outcome = check(client, log, now="2026-10-05T10:30:00Z")
    assert outcome.state == "RESPONDED"
    assert outcome.actor == OWNER_USER and outcome.at == "2026-10-05 10:20:00"
    assert log.history(breach().finding_id)[-1]["at_basis"] == "work_note"


def test_system_or_other_actor_activity_is_not_a_response(client, fake, log):
    res = send(client, log)
    fake.add_journal_entry(res.sys_id, "system", "SLA attached", "2026-10-05 10:05:00")
    fake.human_update(res.sys_id, "other.admin", "2026-10-05 10:06:00")
    outcome = check(client, log, now="2026-10-05T12:30:00Z")
    assert outcome.state == "NO_RESPONSE_OBSERVED"
    assert set(log.history(breach().finding_id)[-1]["non_owner_actors"]) == {"system", "other.admin"}


def test_agent_analysis_note_is_never_an_owner_response(client, fake, log):
    # Even if the agent ran with the owner's identity, its note is not a human reply.
    res = send(client, log)
    fake.add_journal_entry(res.sys_id, OWNER_USER, ANALYSIS_MARKER + "\nVerdict: BREACHED",
                           "2026-10-05 10:01:00")
    assert check(client, log, now="2026-10-05T11:00:00Z").state == "AWAITING_RESPONSE"


def test_agent_identity_activity_is_neither_response_nor_other_actor(client, fake, log):
    res = send(client, log)
    fake.add_journal_entry(res.sys_id, AGENT_USER, ANALYSIS_MARKER, "2026-10-05 10:01:00")
    fake.human_update(res.sys_id, AGENT_USER, "2026-10-05 10:01:00")
    outcome = check_response(breach(), client, log, owner_user=OWNER_USER,
                             integration_user=INTEGRATION_USER, agent_user=AGENT_USER,
                             cutoff=CUTOFF, now="2026-10-05T11:00:00Z")
    assert outcome.state == "AWAITING_RESPONSE"
    assert log.history(breach().finding_id)[-1]["non_owner_actors"] == []


def test_silence_after_cutoff_is_recorded_as_no_response(client, fake, log):
    send(client, log)
    outcome = check(client, log, now="2026-10-05T12:00:01Z")
    assert outcome.state == "NO_RESPONSE_OBSERVED"
    assert log.history(breach().finding_id)[-1]["cutoff"] == CUTOFF


def test_silence_before_cutoff_is_still_awaiting(client, fake, log):
    send(client, log)
    assert check(client, log, now="2026-10-05T11:00:00Z").state == "AWAITING_RESPONSE"


def test_unreadable_history_is_unknown_not_silence(client, fake, log):
    send(client, log)
    fake.journal_forbidden = True
    assert check(client, log, now="2026-10-05T13:00:00Z").state == "RESPONSE_UNKNOWN"


def test_owner_field_change_counts_as_response_with_last_update_basis(client, fake, log):
    res = send(client, log)
    fake.human_update(res.sys_id, OWNER_USER, "2026-10-05 10:45:00")
    outcome = check(client, log, now="2026-10-05T11:00:00Z")
    assert outcome.state == "RESPONDED" and outcome.actor == OWNER_USER
    assert log.history(breach().finding_id)[-1]["at_basis"] == "last_update"


def test_check_response_without_incident_reports_not_delivered(client, log):
    assert check(client, log, now="2026-10-05T13:00:00Z").state == "NOT_DELIVERED"


def test_bad_cutoff_fails_before_any_network_call(client, log):
    with pytest.raises(ValueError):
        check_response(breach(), client, log, owner_user=OWNER_USER,
                       integration_user=INTEGRATION_USER, cutoff="tomorrow", now="2026-10-05T13:00:00Z")
    assert log.history(breach().finding_id) == []


# ---------------------------------------------------------------- log
def test_delivery_log_is_append_only_jsonl(log):
    log.append("f1", "INTENT")
    log.append("f1", "SENT", number="INC1")
    lines = log.path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["number"] == "INC1"
    assert all("ts" in json.loads(line) for line in lines)


def test_delivery_log_tolerates_a_torn_last_line(log):
    log.append("f1", "INTENT")
    with log.path.open("a") as handle:
        handle.write('{"finding_id": "f1", "sta')
    assert [e["state"] for e in log.history("f1")] == ["INTENT"]

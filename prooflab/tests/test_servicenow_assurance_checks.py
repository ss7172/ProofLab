"""Deterministic assurance checks: movement, policy alignment, outcome validation, decision trace, evidence."""
from __future__ import annotations

import pytest

from prooflab.servicenow.assurance_checks import (classify_evidence, decision_trace, movement,
                                                  outcome_validation, policy_alignment, summary_lines)
from prooflab.servicenow.finding import finding_from_dict

OWNER = "annapurna@invences.com"
BASE = {"control_ref": "C16", "control_id": "ACN-COST-001", "threshold_version": "G-FM-v1",
        "scope_kind": "run", "scope_id": "FM-B", "verdict": "BREACHED",
        "summary": "10,800 tokens > cap 10,000", "detected_at": "2026-10-05T14:02:47Z",
        "evidence": ["gateway:action-123", "ledger:cid=fault-1"]}


def step(at, actor, zone, action="model_call", decision="allowed", ref="", run_id="FM-B"):
    return {"at": at, "actor": actor, "zone": zone, "action": action, "decision": decision, "ref": ref,
            "run_id": run_id}


GOOD_TRACE = [step("2026-10-05T13:58:02Z", "customer_experience_agent", "customer"),
              step("2026-10-05T13:58:40Z", "gateway-a", "gateway", "handoff", ref="pdp:decision-7"),
              step("2026-10-05T13:59:10Z", "it_resolution_agent", "it"),
              step("2026-10-05T13:59:50Z", "gateway-b", "gateway", "handoff"),
              step("2026-10-05T14:00:30Z", "network_resolution_agent", "network", "tool_call", ref="gateway:action-123"),
              step("2026-10-05T14:01:10Z", "gateway-b", "gateway", "handoff"),
              step("2026-10-05T14:01:30Z", "it_resolution_agent", "it"),
              step("2026-10-05T14:01:50Z", "gateway-a", "gateway", "handoff"),
              step("2026-10-05T14:02:10Z", "customer_experience_agent", "customer")]
RICH = {**BASE, "measured": {"value": 10800, "unit": "tokens"},
        "limit": {"value": 10000, "operator": "<=", "unit": "tokens"},
        "register": {"version_date": "2026-10-05", "owner": OWNER}, "trace": GOOD_TRACE}


def statuses(section):
    return {check["id"]: check["status"] for check in section["checks"]}


# ---------------------------------------------------------------- movement
def test_movement_path_zones_and_gateway_crossings():
    moved = movement(finding_from_dict(RICH))
    assert moved["path"][:3] == ["customer_experience_agent", "gateway-a", "it_resolution_agent"]
    assert moved["agents"] == ["customer_experience_agent", "it_resolution_agent", "network_resolution_agent"]
    assert moved["gateway_crossings"] == 4 and len(moved["steps"]) == 9
    assert statuses(moved) == {"M1": "pass", "M2": "pass", "M3": "pass"}


def test_direct_network_to_customer_hop_fails_the_route_rule():
    trace = GOOD_TRACE[:5] + [step("2026-10-05T14:01:00Z", "customer_experience_agent", "customer")]
    assert statuses(movement(finding_from_dict({**RICH, "trace": trace})))["M1"] == "fail"


def test_steps_from_another_run_fail_the_run_id_check():
    trace = GOOD_TRACE[:2] + [step("2026-10-05T13:59:10Z", "it_resolution_agent", "it", run_id="FM-X")]
    assert statuses(movement(finding_from_dict({**RICH, "trace": trace})))["M2"] == "fail"


def test_no_trace_means_unknown_never_pass():
    moved = movement(finding_from_dict(BASE))
    assert moved["steps"] == [] and set(statuses(moved).values()) == {"unknown"}


# ---------------------------------------------------------------- policy alignment
def aligned(data, **kw):
    args = {"delivery_state": "DELIVERED", "response_state": "AWAITING_RESPONSE", "incident_state": "New",
            "owner_user": OWNER, **kw}
    return policy_alignment(finding_from_dict(data), **args)


def test_full_data_gives_passes_and_honest_pending():
    result = aligned(RICH)
    s = statuses(result)
    assert s["P1"] == "pass" and s["P2"] == "pass" and s["P3"] == "pass" and s["P4"] == "pass"
    assert s["P5"] == "unknown" and s["P6"] == "pass" and s["P7"] == "pass" and s["P8"] == "pass"
    assert result["passed"] == 7 and result["total"] == 8


def test_breached_verdict_inside_the_limit_is_inconsistent():
    data = {**RICH, "measured": {"value": 9600, "unit": "tokens"}}
    assert statuses(aligned(data))["P1"] == "fail"


def test_threshold_dated_after_detection_fails():
    data = {**RICH, "register": {"version_date": "2026-10-06", "owner": OWNER}}
    assert statuses(aligned(data))["P2"] == "fail"


def test_wrong_owner_closed_incident_and_no_notification_fail():
    data = {**RICH, "register": {"version_date": "2026-10-05", "owner": "someone@else.com"}}
    s = statuses(aligned(data, delivery_state="FAILED", incident_state="Resolved", response_state="NOT_DELIVERED"))
    assert s["P3"] == "fail" and s["P4"] == "fail" and s["P5"] == "fail" and s["P6"] == "fail"


RETEST = {"assessment": "assessment:assessments/C16/run_FM-C.r1.json", "verdict": "SATISFIED",
          "threshold_version": "G-FM-v1", "at": "2026-10-06T02:58:10Z"}


def test_closed_with_a_linked_passing_retest_passes():
    result = aligned({**RICH, "retest": RETEST}, incident_state="Resolved")
    p6 = next(check for check in result["checks"] if check["id"] == "P6")
    assert p6["status"] == "pass" and RETEST["assessment"] in p6["detail"]


@pytest.mark.parametrize("change", [{"threshold_version": "G-FM-v2"}, {"verdict": "BREACHED"}])
def test_closed_with_a_retest_that_does_not_count_fails(change):
    s = statuses(aligned({**RICH, "retest": {**RETEST, **change}}, incident_state="Resolved"))
    assert s["P6"] == "fail"


def test_missing_context_is_unknown():
    s = statuses(aligned({**BASE, "evidence": []}))
    assert s["P1"] == s["P2"] == s["P3"] == s["P8"] == "unknown" and s["P7"] == "fail"


# ---------------------------------------------------------------- outcome validation
RUN_RECORD = {"backend": "modaas-agw:nemotron-super-120b", "outcome": "WRITTEN",
              "attempts": [{"attempt": 1, "action_id": "agw-1", "response_sha256": "ab" * 32, "problems": []}]}
ANALYSIS = {"status": "present", "verified": True, "facts_match": True, "complete": True,
            "fields": {"Evidence refs": "gateway:action-123; ledger:cid=fault-1"}}


def test_a_clean_governed_run_is_validated():
    result = outcome_validation(finding_from_dict(BASE), {"state": "WRITTEN"}, ANALYSIS, RUN_RECORD)
    assert result["status"] == "validated" and set(statuses(result).values()) == {"pass"}


def test_stand_in_or_forged_or_refused_runs_do_not_validate():
    f = finding_from_dict(BASE)
    assert outcome_validation(f, {"state": "WRITTEN"}, ANALYSIS, {**RUN_RECORD, "backend": "test:stand-in"})["status"] == "failed"
    assert outcome_validation(f, {"state": "WRITTEN"}, {**ANALYSIS, "verified": False}, RUN_RECORD)["status"] == "failed"
    assert outcome_validation(f, {"state": "REFUSED"}, {"status": "pending"}, RUN_RECORD)["status"] == "failed"


def test_a_refused_run_shows_why():
    refused = outcome_validation(finding_from_dict(BASE), {"state": "REFUSED", "reason": "verdict differs from the finding"},
                                 {"status": "pending"}, RUN_RECORD)
    assert statuses(refused)["V1"] == "fail"
    assert refused["checks"][0]["detail"] == "REFUSED: verdict differs from the finding"


def test_nothing_run_yet_is_pending():
    assert outcome_validation(finding_from_dict(BASE), {"state": "NOT_RUN"}, {"status": "pending"}, None)["status"] == "pending"


# ---------------------------------------------------------------- decision trace and evidence
def test_decision_trace_merges_every_source_in_time_order():
    history = [{"ts": "2026-10-05T14:03:00Z", "state": "INTENT"},
               {"ts": "2026-10-05T14:03:02Z", "state": "DELIVERED", "number": "INC1"},
               {"ts": "2026-10-05T14:03:30Z", "state": "AWAITING_RESPONSE"},
               {"ts": "2026-10-05T14:04:02Z", "state": "ANALYSIS_WRITTEN", "action_ids": ["agw-1"]}]
    events = decision_trace(finding_from_dict(RICH), history, RUN_RECORD)
    sources = [e["source"] for e in events]
    assert sources.index("gateway") < sources.index("control") < sources.index("servicenow") < sources.index("assurance_agent")
    assert all(e["decision"] != "AWAITING_RESPONSE" for e in events)
    dated = [e["at"] for e in events if e["at"]]
    assert dated == sorted(dated) and all(e["at"] for e in events[:len(dated)])  # undated events go last


def test_repeated_checks_of_the_same_owner_reply_show_once():
    reply = {"state": "RESPONDED", "actor": OWNER, "at": "2026-10-05 10:20:00", "number": "INC1"}
    history = [{"ts": "2026-10-05T14:05:00Z", **reply}, {"ts": "2026-10-05T14:09:00Z", **reply}]
    events = decision_trace(finding_from_dict(BASE), history, None)
    assert [e["source"] for e in events].count("owner") == 1


def test_same_second_events_follow_the_pipeline_order():
    ts = "2026-10-05T14:02:47Z"
    history = [{"ts": ts, "state": "DELIVERED", "number": "INC1"},
               {"ts": ts, "state": "RESPONDED", "actor": OWNER, "at": "2026-10-05 14:02:47"},
               {"ts": ts, "state": "ANALYSIS_WRITTEN", "action_ids": ["agw-1"]}]
    events = decision_trace(finding_from_dict(BASE), history, {**RUN_RECORD, "started_at": ts})
    assert [e["decision"] for e in events] == ["BREACHED", "DELIVERED", "RESPONDED",
                                               "attempt 1: checks passed", "WRITTEN"]


def test_evidence_is_classified_and_marked_when_used_by_the_agent():
    items = classify_evidence(finding_from_dict(BASE), {"Evidence refs": "gateway:action-123"})
    assert items == [{"ref": "gateway:action-123", "kind": "gateway", "used_by_agent": True},
                     {"ref": "ledger:cid=fault-1", "kind": "ledger", "used_by_agent": False}]


def test_summary_lines_for_the_note_are_compact():
    f = finding_from_dict(RICH)
    lines = summary_lines(movement(f), aligned(RICH), ["facts echoed exactly"])
    assert lines["Agent path"].startswith("customer_experience_agent → it_resolution_agent → network_resolution_agent")
    assert "4 gateway crossings" in lines["Agent path"]
    assert lines["Policy alignment"].startswith("7/8 pass")
    assert summary_lines(movement(finding_from_dict(BASE)), aligned(BASE), [])["Agent path"] == "not provided by the evaluator"

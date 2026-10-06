"""Optional Finding context: measurement, limit, register reference and the agents' trace."""
from __future__ import annotations

import pytest

from prooflab.servicenow.finding import build_incident_payload, finding_from_dict
from prooflab.servicenow.finding_context import (Limit, Measurement, RegisterRef, RetestRef, TraceStep,
                                                  format_number)

BASE = {"control_ref": "C16", "control_id": "ACN-COST-001", "threshold_version": "G-FM-v1",
        "scope_kind": "run", "scope_id": "FM-B", "verdict": "BREACHED",
        "summary": "10,800 tokens > cap 10,000", "detected_at": "2026-10-05T14:02:47Z",
        "evidence": ["gateway:action-123"]}
CONTEXT = {
    "measured": {"value": 10800, "unit": "tokens"},
    "limit": {"value": 10000, "operator": "<=", "unit": "tokens"},
    "register": {"version_date": "2026-10-05", "owner": "annapurna@invences.com", "approval": "INC0010300"},
    "trace": [
        {"at": "2026-10-05T13:58:02Z", "actor": "customer_experience_agent", "zone": "customer",
         "action": "model_call", "decision": "allowed", "ref": "gateway:action-101", "run_id": "FM-B"},
        {"at": "2026-10-05T13:58:40Z", "actor": "gateway-a", "zone": "gateway", "action": "handoff",
         "decision": "allowed", "ref": "pdp:decision-7", "run_id": "FM-B"},
    ],
}


def test_context_is_parsed_into_immutable_values():
    finding = finding_from_dict({**BASE, **CONTEXT})
    assert finding.measured == Measurement(10800.0, "tokens")
    assert finding.limit == Limit(10000.0, "<=", "tokens")
    assert finding.register == RegisterRef("2026-10-05", "annapurna@invences.com", "INC0010300")
    assert finding.trace[0] == TraceStep("2026-10-05T13:58:02Z", "customer_experience_agent", "customer",
                                         "model_call", "allowed", "gateway:action-101", "FM-B")
    assert isinstance(finding.trace, tuple)


def test_context_is_optional_and_never_changes_the_finding_id():
    plain, rich = finding_from_dict(BASE), finding_from_dict({**BASE, **CONTEXT})
    assert plain.measured is None and plain.limit is None and plain.register is None and plain.trace == ()
    assert plain.finding_id == rich.finding_id


@pytest.mark.parametrize("bad, message", [
    ({"limit": {"value": 1, "operator": "=<", "unit": "t"}}, "operator"),
    ({"measured": {"value": "lots", "unit": "t"}}, "measured.value"),
    ({"trace": [{"at": "x", "actor": "a\nb", "zone": "it", "action": "x"}]}, "newline"),
    ({"trace": "not a list"}, "trace"),
    ({"register": {"owner": "x"}}, "version_date"),
    ({"retest": {"assessment": "a", "verdict": "PASSED", "threshold_version": "G-FM-v1"}}, "retest.verdict"),
    ({"retest": {"verdict": "SATISFIED", "threshold_version": "G-FM-v1"}}, "retest.assessment"),
])
def test_invalid_context_is_rejected(bad, message):
    with pytest.raises(ValueError, match=message):
        finding_from_dict({**BASE, **bad})


def test_retest_reference_is_parsed_and_never_changes_the_finding_id():
    retest = {"assessment": "assessment:assessments/C16/run_FM-C.r1.json", "verdict": "SATISFIED",
              "threshold_version": "G-FM-v1", "at": "2026-10-06T02:58:10Z"}
    finding = finding_from_dict({**BASE, "retest": retest})
    assert finding.retest == RetestRef("assessment:assessments/C16/run_FM-C.r1.json", "SATISFIED", "G-FM-v1",
                                       "2026-10-06T02:58:10Z")
    assert finding_from_dict(BASE).retest is None
    assert finding.finding_id == finding_from_dict(BASE).finding_id


def test_trace_is_capped():
    steps = [{"at": f"2026-10-05T13:{i % 60:02d}:00Z", "actor": "a", "zone": "it", "action": "x"} for i in range(300)]
    with pytest.raises(ValueError, match="at most"):
        finding_from_dict({**BASE, "trace": steps})


def test_description_shows_measured_and_limit_when_known():
    description = build_incident_payload(finding_from_dict({**BASE, **CONTEXT}), "abc", "[iFabric]")["description"]
    assert "Measured: 10,800 tokens" in description and "Limit: <= 10,000 tokens" in description


def test_numbers_read_like_the_summary():
    assert [format_number(v) for v in (10800, 10000.0, 0.95, 1234567.5, 61)] == ["10,800", "10,000", "0.95", "1,234,567.5", "61"]

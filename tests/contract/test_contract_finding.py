"""The Finding contract against Arth's finding_from_dict (imported read-only, never edited)."""
import pytest

from prooflab.contract import finding as F
from prooflab.contract import verdicts as V
from prooflab.servicenow import finding as arth

CID = "ifabric-run-1791260000-ab12cd"


def sample(**overrides):
    base = dict(control_ref="C16", control_id="ACN-COST-001", threshold_version="C16-v1", scope_kind="run",
                scope_id=CID, verdict="BREACHED", summary="operation: 121,500 tokens > cap 120,000",
                detected_at="2026-10-06T06:05:00Z", evidence=["gateway:action_id=act-SYNTH-0003", "ledger:" + CID])
    base.update(overrides)
    return F.make_finding(**base)


def test_constants_mirror_arths():
    assert set(F.VERDICTS) == set(arth.VERDICTS)
    assert set(F.SCOPE_KINDS) == set(arth.SCOPE_KINDS)
    assert tuple(F.REQUIRED_FIELDS) == tuple(arth.REQUIRED_FIELDS)
    assert F.TEAM_PREFIX == arth.TEAM_PREFIX and F.CORRELATION_ID_MAX == arth.CORRELATION_ID_MAX


@pytest.mark.parametrize("verdict", sorted(F.VERDICTS))
def test_round_trip_through_finding_from_dict(verdict):
    data = sample(verdict=verdict)
    built = arth.finding_from_dict(data)
    for name in F.REQUIRED_FIELDS:
        assert getattr(built, name) == data[name]
    assert list(built.evidence) == data["evidence"] and built.kind == data["kind"]
    assert built.finding_id == F.finding_id(data)


def test_long_scope_id_hashes_like_arth():
    data = sample(scope_id="w" * 150)
    assert arth.finding_from_dict(data).finding_id == F.finding_id(data)


def test_context_keys_when_arths_package_has_them():
    data = sample(measured={"value": 121500, "unit": "tokens"},
                  limit={"value": 120000, "operator": "<=", "unit": "tokens"},
                  register={"version_date": "2026-10-06T03:52:10Z", "owner": "Sree"},
                  trace=[{"at": "2026-10-06T04:31:12Z", "actor": "ifabric-it", "zone": "it", "action": "model_call",
                          "decision": "blocked", "ref": "record:20261006T043112123Z-ep1-9f2c1a7b", "run_id": CID}])
    if not hasattr(arth, "parse_context"):
        pytest.skip("prooflab.servicenow is the pre-handoff-3 copy (no finding_context); PR-00 brings it")
    built = arth.finding_from_dict(data)
    assert built.measured.value == 121500 and built.limit.operator == "<="
    assert built.trace[0].actor == "ifabric-it"


@pytest.mark.parametrize("bad", [
    dict(verdict="NOT_ASSESSED"), dict(scope_kind="incident"), dict(summary=" "),
    dict(scope_id="a^b"), dict(evidence="one string"), dict(limit={"value": 1, "operator": "~", "unit": "x"}),
])
def test_refusals_match_arths(bad):
    with pytest.raises(ValueError):
        sample(**bad)
    raw = dict(sample())
    raw.update(bad)
    if "limit" in bad and not hasattr(arth, "parse_context"):
        return
    with pytest.raises(ValueError):
        arth.finding_from_dict(raw)


def test_from_assessment_four_rows():
    a = dict(control_ref="C16", control_id="ACN-COST-001", threshold_version="C16-v1", scope_kind="run",
             scope_id=CID)
    breached = F.finding_from_assessment(dict(a, requirement_verdict="BREACHED"), "operation: over cap",
                                         "2026-10-06T06:05:00Z")
    assert breached["verdict"] == "BREACHED" and breached["kind"] == "finding"
    gap = F.finding_from_assessment(dict(a, requirement_verdict="INDETERMINATE"), "operation: no spans",
                                    "2026-10-06T06:05:00Z")
    assert gap["verdict"] == "INDETERMINATE" and gap["kind"] == "monitoring-gap"
    assert arth.finding_from_dict(gap).finding_id.endswith(":monitoring-gap")
    assert F.finding_from_assessment(dict(a, requirement_verdict="NOT_ASSESSED"), "x", "y") is None
    ok = F.finding_from_assessment(dict(a, requirement_verdict="SATISFIED"), "within cap", "2026-10-06T06:05:00Z")
    assert ok["verdict"] == "SATISFIED" and not V.notify_due("SATISFIED")

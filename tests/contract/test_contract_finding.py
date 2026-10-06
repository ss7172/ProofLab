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


# --- fix round 1: parity with handoff-3 finding_context.parse_context ---------------------------
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HANDOFF3_CODE = os.path.join(ROOT, "handoffs", "ifabric-handoff-3", "code")

# The six shapes the reviewer found the v1 contract accepted and Arth's finding_from_dict refuses.
CONTEXT_REFUSALS = [
    dict(measured={"value": "10", "unit": "tokens"}),
    dict(limit={"value": 1, "operator": "<="}),
    dict(register={"version_date": "2026-10-06T03:52:10Z"}),
    dict(trace=[{"at": "2026-10-06T04:31:12Z", "zone": "it", "action": "model_call"}]),
    dict(retest={"assessment": "a", "verdict": "NOPE", "threshold_version": "C16-v1"}),
    dict(measured={"value": 10, "unit": "u" * 201}),
]
# More parse_context refusals, same rule set.
MORE_REFUSALS = [
    dict(measured={"value": True, "unit": "tokens"}),
    dict(measured=[1, 2]),
    dict(retest={"verdict": "SATISFIED", "threshold_version": "C16-v1"}),
    dict(register={"version_date": "x", "owner": "Sree\nX"}),
    dict(trace={"at": "x"}),
    dict(trace=[{"at": "x", "actor": "a", "zone": "z", "action": "y"}] * 201),
    dict(trace=["step"]),
]
CONTEXT_ACCEPTED = [
    dict(measured={"value": 10.5, "unit": "tokens"}, limit={"value": 10, "operator": "<=", "unit": "tokens"},
         register={"version_date": "2026-10-06T03:52:10Z", "owner": "Sree", "approval": "INC0010231"},
         retest={"assessment": "C16:C16-v1:run:x:r2", "verdict": "SATISFIED", "threshold_version": "C16-v1"},
         trace=[{"at": "2026-10-06T04:31:12Z", "actor": "ifabric-it", "zone": "it", "action": "model_call"}]),
]


def _raw(context):
    raw = dict(sample())
    raw.update(context)
    return raw


def _arth_refusals(cases):
    """[True if Arth's handoff-3 finding_from_dict refuses] per case, or None when no handoff-3 copy exists."""
    if hasattr(arth, "parse_context"):
        out = []
        for raw in cases:
            try:
                arth.finding_from_dict(raw)
                out.append(False)
            except (ValueError, KeyError, TypeError):
                out.append(True)
        return out
    if not os.path.isfile(os.path.join(HANDOFF3_CODE, "prooflab", "servicenow", "finding_context.py")):
        return None
    script = (
        "import json,sys\n"
        "from prooflab.servicenow.finding import finding_from_dict\n"
        "out=[]\n"
        "for raw in json.load(sys.stdin):\n"
        "    try:\n"
        "        finding_from_dict(raw); out.append(False)\n"
        "    except (ValueError, KeyError, TypeError):\n"
        "        out.append(True)\n"
        "print(json.dumps(out))\n")
    env = dict(os.environ, PYTHONPATH=HANDOFF3_CODE)
    proc = subprocess.run([sys.executable, "-c", script], input=json.dumps(cases), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, cwd=HANDOFF3_CODE)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.parametrize("bad", CONTEXT_REFUSALS + MORE_REFUSALS)
def test_contract_refuses_what_parse_context_refuses(bad):
    assert F.validate_finding(_raw(bad)) != []
    with pytest.raises(ValueError):
        sample(**bad)


def test_arths_handoff3_code_refuses_the_same_cases():
    cases = [_raw(c) for c in CONTEXT_REFUSALS + MORE_REFUSALS]
    refused = _arth_refusals(cases)
    if refused is None:
        pytest.skip("no handoff-3 finding_context available")
    assert refused == [True] * len(cases)


def test_parity_on_accepted_context():
    cases = [_raw(c) for c in CONTEXT_ACCEPTED]
    assert all(F.validate_finding(c) == [] for c in cases)
    refused = _arth_refusals(cases)
    if refused is None:
        pytest.skip("no handoff-3 finding_context available")
    assert refused == [False] * len(cases)

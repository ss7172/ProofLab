"""rails_api, c16_hook and transports: the shapes PR-03/PR-04/PR-05 build on."""
import sys
import types
from collections import namedtuple

import pytest

from prooflab.contract import c16_hook as H
from prooflab.contract import rails_api as RA
from prooflab.contract import record as R
from prooflab.contract import transports as T

CID = "ifabric-adv-1791270000-ab12cd"
SHA = "a" * 64
CTX = {"run.id": CID, "handoff.id": CID + ":h3", "actor.id": "ifabric-network", "ep.id": "EP-3",
       "ep.responsible": "team iFabric (Sree)", "rail.policy_sha256": SHA, "emitted.at": "2026-10-06T06:15:02.113Z",
       "emitted.clock": "agent-runtime", "emitter": "adapters.runtime.rails@1.0+0000000",
       "provenance": "AUTHORIZED_TEST", "record_id": "20261006T061502113Z-rails-7c1e9a20",
       "source.refs": ["rails-policy:R1@" + SHA]}
BLOCK = {"rail_id": "X-02", "rail_version": "1", "stage": "execution", "hook": "before_tool_call",
         "mechanism": "code", "verdict": "BLOCK", "matches": {"X-02.undeclared": 1}, "subject": "tool_use:t1",
         "subject_sha256_in": "b" * 64, "subject_sha256_out": None, "reason": "undeclared tool (1)",
         "threshold_value": "sha256:" + "c" * 64}


def test_rail_record_is_a_valid_g02_record():
    assert RA.validate_rail_decision(BLOCK) == []
    rec = RA.rail_record(BLOCK, CTX)
    assert R.validate_record(rec) == []
    assert rec["inline.action"] == "block" and rec["control.id"] == "RAIL-X-02"
    assert rec["null_reasons"]["register.version"] == "not a register control: rail"
    observe = RA.rail_record(BLOCK, dict(CTX, **{"inline.mode": "observe"}))
    assert observe["inline.action"] == "proceed" and R.validate_record(observe) == []


def test_worst_and_counts_and_compact():
    assert RA.worst([]) == "ALLOW"
    assert RA.worst(["ALLOW", "FLAG", "MODIFY"]) == "MODIFY"
    assert RA.worst(["FLAG", "BLOCK"]) == "BLOCK"
    allow = dict(BLOCK, verdict="ALLOW")
    counts = RA.count_into({}, [allow, BLOCK, dict(allow, rail_id="X-03")])
    assert counts["X-02"] == {"ALLOW": 1, "BLOCK": 1, "MODIFY": 0, "FLAG": 0}
    host = {"rails.allow": ["X-05@1"]}
    out = RA.attach_compact_allows(host, [allow, BLOCK], SHA)
    assert out["rails.allow"] == ["X-05@1", "X-02@1"] and out["rails.policy_sha256"] == SHA
    assert host == {"rails.allow": ["X-05@1"]}


Decision = namedtuple("Decision", H.DECISION_FIELDS)


def deny():
    return Decision(control_ref="C16", control_id="ACN-COST-001", verdict="DENY", reason="committed+bound > cap",
                    measured_value=121500, threshold_value=120000, tier="standard", mode="enforce",
                    limit_applied="cap", limit_value=120000, action="halt", bound_basis="last-call-plus",
                    threshold_version="C16-v1", register_version="v1", threshold_sha256="d" * 64,
                    pin_sha256="e" * 64, evaluator_name="prooflab.evaluators.c16_core", evaluator_sha256="f" * 64)


C16_CTX = {"run.id": "ifabric-run-1791260000-ab12cd", "ep.id": "EP-1", "ep.transport": "evaluate",
           "ep.kind": "model gateway (in-process interceptor)", "actor.id": "ifabric-it",
           "emitted.at": "2026-10-06T04:31:12.123Z", "emitted.clock": "agent-runtime", "provenance": "SYNTHETIC",
           "emitter": "adapters.runtime.model_call@1.0+0000000", "record_id": "20261006T043112123Z-ep1-9f2c1a7b"}


def test_decision_record_from_a_core_decision():
    rec = H.decision_record(deny(), C16_CTX)
    assert R.validate_record(rec) == []
    assert rec["inline.action"] == "halt" and rec["outcome.real"] == "CANCELLED_C16"
    assert rec["threshold.tier"] == "standard" and rec["pin.sha256"] == "e" * 64
    assert H.decision_fields(deny()._asdict()) == H.decision_fields(deny())


def test_stop_record_is_valid():
    rec = H.stop_record(dict(C16_CTX, record_id="20261006T043113000Z-ep1-0a0b0c0d", **{
        "emitted.at": "2026-10-06T04:31:13.000Z"}), "c16-halted")
    assert R.validate_record(rec) == [] and rec["verdict"] == "RECORDED"
    assert rec["outcome.real"] == "CANCELLED_C16" and rec["phase"] == "stop"


def test_stop_record_after_a_rail_quarantine():
    rec = H.stop_record(dict(C16_CTX, record_id="20261006T043113000Z-ep1-0a0b0c0e", **{
        "emitted.at": "2026-10-06T04:31:13.000Z"}), "rail-quarantine", outcome_real="CANCELLED_RAIL")
    assert R.validate_record(rec) == [] and rec["outcome.real"] == "CANCELLED_RAIL" and rec["phase"] == "stop"


def test_stop_record_refuses_other_outcomes():
    with pytest.raises(ValueError):
        H.stop_record(dict(C16_CTX), "x", outcome_real="SERVED")


@pytest.fixture
def fake_core(monkeypatch):
    core = types.ModuleType(T.CORE_MODULE)
    core.Decision = Decision
    core.C16Question = namedtuple("C16Question", "run_id tier committed_tokens reserved_tokens bound_tokens bound_basis")
    core.PinnedC16 = object
    core.CORE_SHA256 = "f" * 64
    monkeypatch.setitem(sys.modules, T.CORE_MODULE, core)
    return core


def test_evaluate_delegates(fake_core):
    fake_core.decide_inline = lambda q, pin: deny()
    q = fake_core.C16Question("ifabric-run-1791260000-ab12cd", "standard", 1, 0, 2, "projected")
    assert T.evaluate(q, object()) == deny()
    assert T.Decision is Decision and T.C16Question is fake_core.C16Question


def test_evaluate_passes_the_core_sha(fake_core):
    fake_core.decide_inline = lambda q, pin, sha=None: sha
    assert T.evaluate(None, None, "f" * 64) == "f" * 64 and T.evaluate(None, None) is None


def test_evaluate_fails_closed(fake_core):
    def boom(q, pin):
        raise ZeroDivisionError("x")
    fake_core.decide_inline = boom
    q = fake_core.C16Question("ifabric-run-1791260000-ab12cd", "standard", 10, 0, 5, "projected")
    d = T.evaluate(q, types.SimpleNamespace(mode="observe", threshold_version="C16-v1"))
    assert d.verdict == "DENY" and d.action == "halt" and d.reason.startswith(T.EVALUATOR_ERROR)
    assert d.measured_value == 15 and d.mode == "observe"


def test_evaluate_uses_cores_own_fail_closed_when_present(fake_core):
    fake_core.decide_inline = lambda q, pin: 1 / 0
    fake_core.fail_closed_decision = lambda q, pin, reason: ("core", reason)
    assert T.evaluate(None, None) == ("core", T.EVALUATOR_ERROR)


def test_transport_shapes():
    assert T.CONTRACT_VERSION == "ifabric.contract/1"
    assert T.assessment_id("C16", "C16-v1", "run", "ifabric-run-1791260000-ab12cd", 1) == \
        "C16:C16-v1:run:ifabric-run-1791260000-ab12cd:r1"
    w = T.Window("2026-10-06T04:00:00Z", "2026-10-06T05:00:00Z")
    cap = T.Capture(T.SourceSpec("aws-spans", "fields @timestamp"), w, "2026-10-06T05:10:00Z", "raw/x.jsonl", "a" * 64)
    assert cap.manifest == {} and cap.window.end.endswith("Z")
    with pytest.raises(AttributeError):
        T.NotAThing


def test_only_model_call_may_import_evaluate():
    """R-J-48: a test fails if any module other than adapters/runtime/model_call.py imports evaluate."""
    import os
    import re
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pattern = re.compile(r"(from\s+prooflab\.contract\.transports\s+import[^\n]*\bevaluate\b|transports\.evaluate\b)")
    offenders = []
    for base in ("prooflab", "adapters", "agents", "tools"):
        for dirpath, _, files in os.walk(os.path.join(root, base)):
            for name in files:
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, root)
                if not name.endswith(".py") or rel.startswith(os.path.join("prooflab", "contract")):
                    continue
                with open(path, encoding="utf-8", errors="replace") as handle:
                    if pattern.search(handle.read()) and rel != os.path.join("adapters", "runtime", "model_call.py"):
                        offenders.append(rel)
    assert offenders == []


class _Pin(object):
    caps = (("high", 80000), ("standard", 50000))
    mode = "enforce"
    control_id = "ACN-COST-001"
    threshold_version = "C16-v1"
    register_version = "v1"
    register_sha256 = "c" * 64
    pin_sha256 = "e" * 64


def test_fail_closed_record_validates_with_the_given_sha(fake_core):
    """Reviewer fix: the fail-closed Decision carries the caller's evaluator_sha256 and the pin's cap,
    so its decision record validates (it is the halt evidence, never REJECTED_SCHEMA)."""
    del fake_core.CORE_SHA256

    def boom(q, pin, sha=None):
        raise RuntimeError("core bug")
    fake_core.decide_inline = boom
    q = fake_core.C16Question("ifabric-run-1791260000-ab12cd", "standard", 49000, 0, 2000, "projected")
    d = T.evaluate(q, _Pin(), "b" * 64)
    assert d.verdict == "DENY" and d.action == "halt" and d.evaluator_sha256 == "b" * 64
    assert d.threshold_value == 50000 and d.limit_value == 50000 and d.measured_value == 51000
    rec = H.decision_record(d, C16_CTX)
    assert R.validate_record(rec) == []
    assert rec["evaluator.sha256"] == "b" * 64 and rec["outcome.real"] == "CANCELLED_C16"


def test_fail_closed_without_any_sha_is_null_not_empty(fake_core):
    del fake_core.CORE_SHA256
    fake_core.decide_inline = lambda q, pin: 1 / 0
    q = fake_core.C16Question("ifabric-run-1791260000-ab12cd", "nosuchtier", 1, 0, 1, "projected")
    d = T.evaluate(q, _Pin())
    assert d.evaluator_sha256 is None and d.threshold_value == 0 and d.limit_value is None
    assert R.validate_record(H.decision_record(d, C16_CTX)) == []


def test_fail_closed_passes_sha_to_the_cores_maker(fake_core):
    fake_core.decide_inline = lambda q, pin, sha=None: 1 / 0
    fake_core.fail_closed_decision = lambda q, pin, reason, sha: ("core", reason, sha)
    assert T.evaluate(None, None, "b" * 64) == ("core", T.EVALUATOR_ERROR, "b" * 64)


def test_fail_closed_survives_a_broken_core_maker(fake_core):
    fake_core.decide_inline = lambda q, pin, sha=None: 1 / 0

    def bad_maker(*a):
        raise KeyError("maker bug")
    fake_core.fail_closed_decision = bad_maker
    d = T.evaluate(None, _Pin(), "b" * 64)
    assert d.verdict == "DENY" and d.action == "halt" and d.evaluator_sha256 == "b" * 64

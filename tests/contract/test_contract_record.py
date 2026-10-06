"""ifabric.evidence/1: goldens, the null rule, G0.2 rail fields, the secret guard (PR-01)."""
import copy
import json
import os

import pytest

from prooflab.contract import record as R
from prooflab.contract import verdicts as V

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "golden")
ROOT = os.path.dirname(os.path.dirname(HERE))


def load(name):
    with open(os.path.join(GOLDEN, name)) as handle:
        return json.load(handle)


VALID_GOLDENS = sorted(n for n in os.listdir(GOLDEN) if n.endswith(".json") and n != "rail_decision_sec52_shape.json")


@pytest.mark.parametrize("name", VALID_GOLDENS)
def test_goldens_are_valid(name):
    assert R.validate_record(load(name)) == []


def test_arch_44_example_has_every_table_a_field():
    rec = load("decision_c16_deny.json")
    assert all(f in rec for f in R.TABLE_A)
    assert rec["run.id"] == rec["correlation_id"]


def test_sec52_shape_only_lacks_table_a_nulls():
    rec = load("rail_decision_sec52_shape.json")
    errors = R.validate_record(rec)
    assert errors and all("table-A field missing" in e for e in errors)
    assert R.validate_record(rec, require_table_a=False) == []
    assert R.validate_record(R.complete_nulls(rec, "not applicable: rail")) == []


def test_rail_decision_without_rail_id_is_rejected():
    rec = load("rail_decision_block.json")
    del rec["rail.id"]
    assert any(e.startswith("rail.id:") for e in R.validate_record(rec))
    rec = load("rail_decision_block.json")
    rec["rail.id"] = None
    assert any(e.startswith("rail.id:") for e in R.validate_record(rec))


def test_g02_vocabulary_is_accepted():
    assert "rail_decision" in R.RECORD_KINDS
    assert "CANCELLED_RAIL" in R.OUTCOME_REAL
    assert {"EP-14", "EP-15", "EP-16"} <= set(R.EP_IDS)
    rec = load("rail_decision_block.json")
    rec["ep.id"] = "EP-14"
    assert R.validate_record(rec) == []


def mutate(name, **changes):
    rec = load(name)
    for key, value in changes.items():
        rec[key.replace("__", ".")] = value
    return R.validate_record(rec)


def test_rail_verdicts_only_on_rail_records():
    assert any("verdict" in e for e in mutate("decision_c16_deny.json", verdict="BLOCK"))
    assert any("verdict" in e for e in mutate("assessment.json", verdict="FLAG"))
    assert any("control.ref" in e for e in mutate("decision_c16_deny.json", control__ref="RAIL"))


def test_rail_fields_never_enter_an_assessment():
    rec = load("assessment.json")
    rec["rail.id"] = "X-02"
    assert any("assessment" in e or "rail.*" in e for e in R.validate_record(rec))
    rec = load("assessment.json")
    rec["rails.allow"] = ["X-02@1"]
    rec["rails.policy_sha256"] = "a" * 64
    assert any("never enter an assessment" in e for e in R.validate_record(rec))


def test_rail_observe_always_proceeds():
    errs = mutate("rail_decision_block.json", inline__mode="observe")
    assert any("observe" in e for e in errs)
    assert mutate("rail_decision_block.json", inline__mode="observe", inline__action="proceed") == []


def test_rail_rules():
    assert any("control.id" in e for e in mutate("rail_decision_block.json", control__id="RAIL-X-03"))
    errs = mutate("rail_decision_block.json", register__version="v1")
    assert any("register.version" in e for e in errs)
    assert any("ep.id" in e for e in mutate("rail_decision_block.json", ep__id="EP-5"))
    assert any("handoff.id" in e for e in mutate("rail_decision_block.json", handoff__id=None))


def test_compact_rails_fields():
    assert any("rails.allow" in e for e in mutate("action_compact_allows.json", rails__allow=["x02"]))
    rec = load("action_compact_allows.json")
    del rec["rails.policy_sha256"]
    assert any("rails.policy_sha256" in e for e in R.validate_record(rec))
    assert any("lifecycle" in e for e in mutate("action_compact_allows.json", rails__counts={"X-02": {"ALLOW": 1}}))
    assert any("rails.counts" in e for e in mutate("lifecycle_rails_counts.json", rails__counts={"X-02": {"PASS": 1}}))


def test_null_rule():
    rec = load("decision_c16_deny.json")
    del rec["null_reasons"]["call.id"]
    assert any("call.id: null without" in e for e in R.validate_record(rec))
    rec = load("decision_c16_deny.json")
    rec["null_reasons"]["control.id"] = "bogus"
    assert any("null_reasons.control.id" in e for e in R.validate_record(rec))
    rec = load("decision_c16_deny.json")
    del rec["handoff.to"]
    assert any("handoff.to: table-A field missing" in e for e in R.validate_record(rec))


def test_required_and_time_pair():
    rec = load("handoff.json")
    del rec["emitted.at"]
    del rec["ts"]
    errs = R.validate_record(rec)
    assert any("ts: required" in e for e in errs)
    assert any("one pair is required" in e for e in errs)
    assert any("ts: must equal" in e for e in mutate("handoff.json", ts="2026-10-06T00:00:00.000Z"))


def test_unknown_and_derived_fields_rejected():
    assert any("unknown field" in e for e in mutate("handoff.json", foo="bar"))
    assert any("derived field" in e for e in mutate("handoff.json", component__owner="Sree"))


def test_ids_and_enums():
    assert any("run.id" in e for e in mutate("handoff.json", run__id="run-123"))
    assert any("correlation_id" in e for e in mutate("handoff.json", correlation_id="ifabric-run-1791260000-ffffff"))
    assert any("record_id" in e for e in mutate("handoff.json", record_id="abc"))
    assert any("deterministic obs-" in e for e in mutate("observation_span.json",
                                                        record_id="20261006T043112123Z-ep1-9f2c1a7b"))
    assert any("provenance" in e for e in mutate("handoff.json", provenance="LIVE"))
    assert any("ep.id" in e for e in mutate("handoff.json", ep__id="EP-17"))
    assert any("ep.id" in e for e in mutate("handoff.json", ep__id="EP-1"))
    assert any("emitted.clock" in e for e in mutate("handoff.json", emitted__clock="laptop"))
    assert any("sha256" in e for e in mutate("decision_c16_deny.json", pin__sha256="<sha>"))
    assert any("source.refs" in e for e in mutate("handoff.json", source__refs=["no prefix"]))
    assert any("risk states" in e for e in mutate("handoff.json", verdict="EXPOSED"))


def _secret_samples():
    return [
        "AK" + "IA" + "ABCDEFGHIJKLMNOP",
        "-----BEGIN " + "RSA PRIV" + "ATE KEY-----",
        "gh" + "p_" + "a" * 24,
        "github" + "_pat_" + "x",
        "s" + "k-" + "b" * 24,
        "Bear" + "er " + "c" * 30,
        "https://cockpit/x?" + "tk" + "n=" + "abc",
        "AUDIT_WRITE" + "_TOKEN=abc123",
    ]


@pytest.mark.parametrize("value", _secret_samples())
def test_secret_shaped_values_refused(value):
    assert any("secret-shaped" in e for e in mutate("handoff.json", detail=value))
    rec = load("handoff.json")
    rec["null_reasons"] = dict(rec["null_reasons"], **{"call.id": value})
    assert any("secret-shaped" in e for e in R.validate_record(rec))


def test_secret_keys_refused():
    rec = load("handoff.json")
    rec["assessment.api_key"] = "x"
    assert any("names a secret" in e for e in R.validate_record(rec))
    assert R.validate_record(load("observation_span.json")) == []  # tokens.in / tokens.out are fine


@pytest.mark.parametrize("garbage", [None, [], "x", 1, {"record_kind": []}, {"run.id": 5, "verdict": {}},
                                     {"null_reasons": "x", "source.refs": "y", "rails.counts": [1]}])
def test_validator_never_raises(garbage):
    assert isinstance(R.validate_record(garbage), list) and R.validate_record(garbage)


def test_observation_record_id_is_deterministic():
    a = R.observation_record_id("aws-spans", "aws-spans:q1#3")
    assert a == R.observation_record_id("aws-spans", "aws-spans:q1#3")
    assert a != R.observation_record_id("aws-spans", "aws-spans:q1#4")
    assert R.OBS_RECORD_ID_RE.match(a)


def test_emitted_record_id():
    assert R.emitted_record_id("2026-10-06T04:31:12.123Z", "ep1", "9f2c1a7b") == "20261006T043112123Z-ep1-9f2c1a7b"
    with pytest.raises(ValueError):
        R.emitted_record_id("2026-10-06T04:31:12.123Z", "EP 1", "9f2c1a7b")


def test_new_record_fills_table_a():
    rec = R.new_record("handoff", null_reason="n/a", record_id="20261006T043000001Z-orch-0a1b2c3d", detail="d",
                       **{"run.id": "ifabric-run-1791260000-ab12cd", "verdict": "RECORDED",
                          "emitted.at": "2026-10-06T04:30:00.001Z", "emitted.clock": "script-host",
                          "provenance": "SYNTHETIC", "authorship": "TESTIMONY", "emitter": "x@1"})
    assert R.validate_record(rec) == []
    assert rec["null_reasons"]["call.id"] == "n/a" and rec["phase"] == "ifabric.handoff"


def test_json_schema_file_matches_module():
    path = os.path.join(ROOT, "prooflab", "contract", "schema", "evidence-record-1.json")
    with open(path) as handle:
        on_disk = json.load(handle)
    assert on_disk == json.loads(json.dumps(R.json_schema()))


def test_golden_records_carry_no_unknown_keys_after_roundtrip():
    rec = load("decision_c16_deny.json")
    assert json.loads(R.canonical_json(rec)) == rec
    assert copy.deepcopy(rec) == rec


# --- fix round 1: content fields (EP-3, EP-4, EP-5, RT-01) and the workflow phase vocabulary ----

def test_workflow_phases_match_arch_52():
    assert set(R.WORKFLOW_PHASES) == {"run.started", "handoff.sent", "invocation.received", "intent", "judgment",
                                      "handoff.received", "escalation", "run.finished", "stop"}
    assert load("handoff.json")["phase"] == "handoff.sent"
    assert load("handoff_received.json")["phase"] == "handoff.received"


def test_workflow_phase_requires_its_record_kind():
    rec = load("handoff.json")
    rec["phase"] = "judgment"
    assert any(e.startswith("phase:") for e in R.validate_record(rec))
    rec["phase"] = "ifabric.handoff"           # a non-workflow phase stays free
    assert R.validate_record(rec) == []


def test_new_content_fields_are_accepted_and_typed():
    j = load("judgment.json")
    assert j["judgment.disposition"] == "escalate"
    bad = dict(j, **{"judgment.disposition": "shrug"})
    assert any("judgment.disposition" in e for e in R.validate_record(bad))
    h = load("handoff_received.json")
    for field, value in (("tally.tokens", -1), ("tally.calls", True), ("handoff.duration_ms", "1"),
                         ("handoff.halted", "no"), ("handoff.status", "MAYBE")):
        assert any(field in e for e in R.validate_record(dict(h, **{field: value}))), field
    a = load("action_tool_suspicious.json")
    assert a["suspicious_tool_output"] is True and a["tool.use_id"] == "tu-0001"
    assert any("suspicious_tool_output" in e for e in R.validate_record(dict(a, suspicious_tool_output="yes")))


def test_judgment_fields_only_on_judgment_records():
    h = load("handoff_received.json")
    assert any(e.startswith("judgment.*") for e in R.validate_record(dict(h, **{"judgment.disposition": "escalate"})))


def test_startup_echo_rt01():
    s = load("lifecycle_startup.json")
    assert R.validate_record(s) == []
    assert any("prompt.sha256" in e for e in R.validate_record(dict(s, **{"prompt.sha256": "nothex"})))
    assert any("rails.mode" in e for e in R.validate_record(dict(s, **{"rails.mode": "audit"})))
    # rail.* stays refused outside rail_decision; the echo uses rails.policy_sha256
    assert any(e.startswith("rail.*") for e in R.validate_record(dict(s, **{"rail.policy_sha256": "e" * 64})))


def test_null_reasons_allowed_on_optional_judgment_fields():
    j = load("judgment.json")
    assert j["judgment.reversible_step"] is None and j["null_reasons"]["judgment.reversible_step"]


# --- fix round 2: D-D optional fields (EP-3 before/after, J2, lifecycle duplicate guard, rail intent) -------

def test_ep3_before_and_after_goldens_are_pr04_shaped():
    before, after = load("action_tool_before.json"), load("action_tool_after.json")
    assert before["tool.phase"] == "before" and after["tool.phase"] == "after"
    assert before["ep.id"] == after["ep.id"] == "EP-3" and before["record_kind"] == "action"
    assert R.SHA256_RE.match(after["tool.result_sha256"])
    assert "tool.result_sha256" not in before or before["tool.result_sha256"] is None
    assert R.validate_record(before) == [] and R.validate_record(after) == []


@pytest.mark.parametrize("field,bad", [
    ("tool.phase", "during"), ("tool.result_sha256", "ABC"), ("tool.result_sha256", "a" * 63),
    ("lifecycle.duplicate_state", "twice"), ("judgment.model_disposition", "resolve"),
    ("judgment.valid", "yes"), ("judgment.reasked", 1), ("judgment.evidence_needed", "twin"),
    ("rail.intended_action", "allow"),
])
def test_new_optional_fields_are_validated(field, bad):
    name = {"tool": "action_tool_after.json", "lifecycle": "lifecycle_duplicate.json",
            "judgment": "judgment_j2.json", "rail": "rail_decision_observe_intended.json"}[field.split(".")[0]]
    rec = load(name)
    rec[field] = bad
    assert any(e.startswith(field + ":") for e in R.validate_record(rec)), R.validate_record(rec)


def test_new_optional_fields_accept_null():
    for name, field in (("action_tool_after.json", "tool.result_sha256"), ("action_tool_before.json", "tool.phase"),
                        ("judgment_j2.json", "judgment.model_disposition"),
                        ("rail_decision_observe_intended.json", "rail.intended_action")):
        rec = load(name)
        rec[field] = None
        assert R.validate_record(rec) == [], (name, field)


def test_kind_scoped_new_fields():
    rec = load("action_tool_after.json")
    rec["rail.intended_action"] = "block"
    assert any(e.startswith("rail.*") for e in R.validate_record(rec))
    rec = load("action_tool_after.json")
    rec["judgment.valid"] = True
    assert any(e.startswith("judgment.*") for e in R.validate_record(rec))


def test_observe_rail_records_intended_action_but_proceeds():
    rec = load("rail_decision_observe_intended.json")
    assert rec["inline.mode"] == "observe" and rec["inline.action"] == "proceed"
    assert rec["rail.intended_action"] == "block"
    rec["inline.action"] = "block"
    assert "inline.action: in observe a rail always proceeds" in R.validate_record(rec)


def test_new_fields_are_in_the_json_schema():
    props = R.json_schema()["properties"]
    assert props["tool.phase"]["enum"] == ["before", "after", None]
    assert props["tool.result_sha256"]["pattern"] == R.SHA256_RE.pattern
    assert props["lifecycle.duplicate_state"]["enum"][:-1] == list(R.DUPLICATE_STATES)
    assert props["rail.intended_action"]["enum"] == list(V.RAIL_ACTIONS) + [None]
    for name in ("judgment.valid", "judgment.reasked"):
        assert props[name] == {"type": ["boolean", "null"]}
    assert props["judgment.evidence_needed"]["items"] == {"type": "string"}


# --- the null rule when a caller sets a value (no stale null_reasons) ----------------------------------------

def _base_fields():
    return {"run.id": "ifabric-run-1791260000-ab12cd", "record_id": "20261006T043205000Z-ifabric-it-0a0b0c0d",
            "detail": "x", "verdict": "RECORDED", "provenance": "SYNTHETIC", "authorship": "TESTIMONY",
            "emitter": "test", "emitted.at": "2026-10-06T04:32:05.000Z", "emitted.clock": "agent-runtime"}


def test_new_record_extra_sets_a_value_without_a_stale_reason():
    rec = R.new_record("action", "not applicable: tool call",
                       extra={"call.id": "act-1", "tool.phase": "after", "null_reasons": {"call.id": "header absent"}},
                       **_base_fields())
    assert rec["call.id"] == "act-1" and "call.id" not in rec["null_reasons"]
    assert R.validate_record(rec) == []


def test_new_record_keeps_a_caller_reason_for_a_null_field():
    rec = R.new_record("action", extra={"null_reasons": {"call.id": "header absent"}}, **_base_fields())
    assert rec["call.id"] is None and rec["null_reasons"]["call.id"] == "header absent"
    assert R.validate_record(rec) == []


def test_prune_and_set_field_after_construction():
    rec = R.new_record("action", **_base_fields())
    rec["call.id"] = "act-1"          # PR-04's pattern: set after the constructor filled the reason
    assert "null_reasons.call.id: field is not null" in R.validate_record(rec)
    assert R.validate_record(R.prune_null_reasons(rec)) == []
    R.set_field(rec, "call.id", None, "header absent")
    assert R.validate_record(rec) == [] and rec["null_reasons"]["call.id"] == "header absent"
    R.set_field(rec, "outcome.real", "SERVED")
    assert "outcome.real" not in rec["null_reasons"] and R.validate_record(rec) == []
    rec["null_reasons"].pop("reason")
    with pytest.raises(ValueError):
        R.set_field(rec, "reason", None)


def test_complete_nulls_drops_stale_reasons():
    rec = dict(load("action_tool_after.json"))
    rec["null_reasons"] = dict(rec["null_reasons"], **{"tool.name": "stale"})
    out = R.complete_nulls(rec, "n/a")
    assert "tool.name" not in out["null_reasons"] and R.validate_record(out) == []

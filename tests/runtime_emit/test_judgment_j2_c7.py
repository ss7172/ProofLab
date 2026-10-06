"""PR-25 cross-PR checks: the J2 Judgment -> the EP-4 judgment record (contract names), and the EP-4 records
-> C7's expected workflow events (ARCH 3.1 EP-4, 5.2: escalate = `judgment` + `escalation`)."""
from adapters.runtime import emit_client as ec
from adapters.runtime import j2, judgment
from prooflab.contract.record import validate_record
from prooflab.evaluators import c7

AGENT = "ifabric-it"
RUN = "ifabric-test-1791260000-abc123"


class _Capture(object):
    def __init__(self):
        self.records = []

    def emit(self, rec):
        self.records.append(rec)
        return ec.ENQUEUED


def _ctx():
    return ec.RunContext(run_id=RUN, actor_id=AGENT, handoff_id="h-1", session_id="sess-1", register_version="v1",
                         pin_sha256="a" * 64)


ANSWER = ('{"disposition": "resolve", "reason": "known fix", "deciding_evidence": ["E1", "E2"], '
          '"reversible_step": "roll back the change", "named_evidence_needed": ["ticket history"], '
          '"proposed_action": "restart   the\\nCPE"}')


def test_j2_result_to_judgment_record_passes_the_contract():
    fields = j2.parse(ANSWER).to_record_fields()
    c = _Capture()
    assert judgment.record_from_j2(c, _ctx(), fields, result_digests=["d" * 64]) == ec.ENQUEUED
    (rec,) = c.records
    assert validate_record(rec) == []
    assert rec["judgment.disposition"] == "auto-resolve" and rec["judgment.evidence_ids"] == ["E1", "E2"]
    assert rec["judgment.result_digests"] == ["d" * 64] and rec["judgment.evidence_needed"] == ["ticket history"]
    assert rec["judgment.valid"] is True and rec["judgment.reasked"] is False
    assert rec["judgment.reversible_step"] == "roll back the change"
    assert rec["judgment.precedence_rule"] is None and rec["null_reasons"]["judgment.precedence_rule"]
    assert rec["detail"] == "disposition auto-resolve; proposed: restart the CPE"
    assert not [k for k in fields if k in rec and k != "reason"]       # no un-prefixed J2 key leaks into the record


def test_invalid_and_halted_j2_results_map_and_validate():
    for j in (j2.judge("nope", lambda p: "still nope"), j2.halted_judgment()):
        c = _Capture()
        judgment.record_from_j2(c, _ctx(), j.to_record_fields())
        assert [r["phase"] for r in c.records] == ["ifabric.judgment", "ifabric.escalation"]
        for rec in c.records:
            assert validate_record(rec) == [], rec
        assert c.records[0]["judgment.valid"] is j.valid


def _workflow(disposition):
    c = _Capture()
    judgment.record_intent(c, _ctx(), "triage")
    judgment.record_judgment(c, _ctx(), disposition, "because")
    for r in c.records:
        assert validate_record(r) == [], r
    return c.records


def _expected(events):
    wf = [{"agent": AGENT, "event": e, "stream": "s1", "order": i} for i, e in enumerate(events)]
    return wf, c7.expected_events(RUN, [], [], wf, [], {})


def test_escalate_emits_judgment_and_escalation_and_c7_matches_both():
    recs = _workflow("escalate")
    assert [(r["record_kind"], r["control.ref"], r["verdict"]) for r in recs[1:]] == [
        ("judgment", "C7", "RECORDED"), ("judgment", "ESC", "ESCALATED")]
    wf, exp = _expected(["intent", "judgment", "escalation"])
    obs = c7.observed_events(recs)
    assert set(e["key"] for e in exp) <= set(obs)
    # the independent rechecker agrees on the match (phase = "ifabric." + event)
    keys = set(("wf", r["actor.id"], r["phase"]) for r in recs)
    assert set(("wf", w["agent"], "ifabric." + w["event"]) for w in wf) <= keys


def test_non_escalate_emits_no_escalation_event():
    for disp in ("auto-resolve", "gather-evidence", "halted"):
        recs = _workflow(disp)
        assert "%s|escalation" % AGENT not in c7.observed_events(recs)
        _, exp = _expected(["intent", "judgment"])
        assert set(e["key"] for e in exp) <= set(c7.observed_events(recs))

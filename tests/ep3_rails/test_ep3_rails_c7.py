"""PR-31: C7 and a rail-cancelled tool call (DG-1). Python 3.9, stdlib.

An enforced X-02 BLOCK cancels the call before it leaves the agent: no gateway span, so the expected-event
derivation (prooflab/query/assess_snapshot.run_facts -> c7.expected_events) expects nothing for it, and its
rail_decision is outside the observed kinds: neither a missing event nor inflated coverage. c7 lists it as the
diagnostic measured.rail_cancelled_tool_calls. In observe the call goes out, has its span, and is expected.
"""
from prooflab.evaluators import c7
from prooflab.query.assess_snapshot import run_facts

RUN = "ifabric-test-1791300000-e3a1b2"
PIN = {"observation_limit": "coverage_min_pct=100;gap_max_ms=60000;violating_gap_share_max_pct=10",
       "control_id": "AIA-LOG-001", "threshold_version": "C7-test"}
AS_OF = "2026-10-06T06:00:00.000Z"


def _span(call, model=True):
    r = {"record_kind": "metric" if model else "observation", "authorship": "PLATFORM", "observed.clock": "gateway",
         "call.id": call, "run.id": RUN, "observed.at": "2026-10-06T05:00:0%sZ" % call[-1]}
    if model:
        r.update({"tokens.in": 50, "tokens.out": 10})
    return r


def _ours(kind, ep, call=None, **kw):
    r = {"record_kind": kind, "ep.id": ep, "authorship": "TESTIMONY", "actor.id": "ifabric-network", "run.id": RUN,
         "call.id": call, "emitted.at": "2026-10-06T05:00:0%sZ" % (call[-1] if call else "9")}
    r.update(kw)
    return r


def _rail_block(mode, call=None):
    return _ours("rail_decision", "EP-3", call, **{
        "rail.id": "X-02", "verdict": "BLOCK", "control.ref": "RAIL", "inline.mode": mode,
        "inline.action": "block" if mode == "enforce" else "proceed", "tool.name": "customer-records___customer_lookup",
        "tool.declared": False, "outcome.real": "CANCELLED_RAIL" if mode == "enforce" else None})


def _assess(recs):
    f = run_facts(recs)
    exp = c7.expected_events(RUN, f["actions"], f["refusals"], [], f["stops"], PIN)
    return exp, c7.assess_run(RUN, exp, f["ours"], [], PIN, AS_OF)


BASE = [_span("act-1"), _span("act-2"), _ours("action", "EP-1", "act-1"), _ours("action", "EP-1", "act-2")]


def test_enforced_rail_block_is_neither_missing_nor_coverage():
    exp0, a0 = _assess(BASE)
    exp1, a1 = _assess(BASE + [_rail_block("enforce")])
    assert [e["key"] for e in exp1] == [e["key"] for e in exp0] == ["call:act-1", "call:act-2"]
    assert a1.measured["coverage"] == a0.measured["coverage"] == "2/2"
    assert a1.measured["missing_events"] == 0 and a1.requirement_verdict == a0.requirement_verdict
    assert a1.measured["rail_cancelled_tool_calls"] == 1 and a0.measured["rail_cancelled_tool_calls"] == 0
    assert not [k for k in c7.observed_events(BASE + [_rail_block("enforce")]) if "rail" in k]


def test_a_rail_record_never_fills_a_missing_expected_event():
    # even a rail_decision carrying a call id cannot stand in for the EP-1 record of a call that was made
    recs = [_span("act-1"), _span("act-2"), _ours("action", "EP-1", "act-1"), _rail_block("enforce", "act-2")]
    _, a = _assess(recs)
    assert a.measured["coverage"] == "1/2" and a.measured["missing_events"] == 1
    assert a.requirement_verdict == "BREACHED"


def test_observe_rail_block_is_an_ordinary_expected_tool_call():
    recs = BASE + [_span("act-3", model=False), _rail_block("observe"),
                   _ours("action", "EP-3", "act-3", **{"tool.phase": "after", "tool.declared": False})]
    exp, a = _assess(recs)
    assert "call:act-3" in [e["key"] for e in exp]
    assert a.measured["coverage"] == "3/3" and a.measured["rail_cancelled_tool_calls"] == 0


def test_diagnostic_is_unknown_for_a_key_map():
    f = run_facts(BASE)
    exp = c7.expected_events(RUN, f["actions"], [], [], [], PIN)
    a = c7.assess_run(RUN, exp, c7.observed_events(f["ours"]), [], PIN, AS_OF)
    assert a.measured["rail_cancelled_tool_calls"] is None

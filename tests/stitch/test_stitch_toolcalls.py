"""PR-39: the tool-call join and the C7 tool-event expectation, on SYNTHETIC fixtures shaped like P1's gateway spans
(the real attribute set: mcp.method.name, gen_ai.tool.name, modaas.action_id, modaas.run_id, trace.id; every id,
time and name here is invented, nothing is copied from a run). The spans go through the real gateway normalizer."""
import json

from prooflab.evaluators import c7
from prooflab.query import assess_snapshot as A
from prooflab.stitch import toolcalls as T
from prooflab.store import observations as O

RUN = "ifabric-run-1790000000-abc123"
TRACE = "0123456789abcdef0123456789abcdef"
PIN = {"coverage_min_pct": 100, "gap_max_ms": 600000, "violating_gap_share_max_pct": 100,
       "ep1_deployed": False, "control_id": "AIA-LOG-001", "threshold_version": "C7-v0"}
EPOCH = 1790000000
T0 = 1790000010.0                       # synthetic base time (s)


def _span(method, target, tool, aid, start, end, run=RUN, trace=TRACE):
    attrs = {"mcp.method.name": method, "http.path": "/mcp/" + target, "http.status": 200, "protocol": "mcp",
             "modaas.action_id": aid, "modaas.run_id": run, "trace.id": trace, "route": "synthetic"}
    if tool:
        attrs["gen_ai.tool.name"] = tool
    return {"attributes": attrs, "startTimeUnixNano": int(start * 1e9), "endTimeUnixNano": int(end * 1e9),
            "spanId": aid[:16], "traceId": trace}


def _iso(t):
    import datetime
    d = datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (d.microsecond // 1000)


def _store(spans):
    text = "\n".join(json.dumps({"@timestamp": "synthetic", "@message": json.dumps(s)}) for s in spans)
    return O.normalize_gateway_text(text, "raw/gateway/synthetic", insights=True)["records"]


def _rec(phase, use, name, t, agent="ifabric-it"):
    return {"authorship": "TESTIMONY", "record_kind": "action", "ep.id": "EP-3", "actor.id": agent, "run.id": RUN,
            "correlation_id": RUN, "trace.id": TRACE, "tool.use_id": use, "tool.name": name, "tool.phase": phase,
            "emitted.at": _iso(t), "phase": "ifabric.action", "record_id": "%s-%s" % (use, phase), "control.ref": "C7"}


def _run(n_calls=4, suppress=None, handshake=True, drop_both=False):
    """Gateway spans + our records for one agent making n sequential tools/call calls (+ handshake spans)."""
    spans, ours = [], []
    if handshake:
        for i, (m, tool) in enumerate((("initialize", None), ("tools/list", None), ("notifications/initialized", None))):
            spans.append(_span(m, "runbook-lookup", tool, "hs-%d-0000-0000-000000000000" % i, T0 - 3 + i, T0 - 2.9 + i))
    for i in range(n_calls):
        s = T0 + i * 2
        spans.append(_span("tools/call", "runbook-lookup", "runbook-lookup___lookup", "ac-%d-0000-0000-000000000000" % i,
                           s + 0.01, s + 0.8))
        if i == suppress and drop_both:
            continue                                     # both records missing
        if i == suppress:                                # N4-style (_Suppress): only the AFTER record is dropped
            ours.append(_rec("before", "use%d" % i, "runbook-lookup___lookup", s))
            continue
        ours.append(_rec("before", "use%d" % i, "runbook-lookup___lookup", s))
        ours.append(_rec("after", "use%d" % i, "runbook-lookup___lookup", s + 0.82))
    return _store(spans), ours


def _assess(store, ours):
    f = A.run_facts(store + ours)
    exp = c7.expected_events(RUN, f["actions"], [], [], [], PIN)
    joined, res = T.join_records(f["all"], f["ours"])
    return exp, c7.assess_run(RUN, exp, joined, [], PIN, "2026-10-06T09:00:00.000Z"), res


def test_handshake_spans_are_not_expected():
    store, ours = _run()
    f = A.run_facts(store + ours)
    assert len(f["actions"]) == 4 and all(a["method"] == "tools/call" for a in f["actions"])
    # c7 itself also drops a non-tools/call action handed to it directly
    exp = c7.expected_events(RUN, [{"action_id": "x", "kind": "tool.call", "method": "initialize"},
                                   {"action_id": "y", "kind": "tool.call", "method": "tools/call"},
                                   {"action_id": "z", "kind": "tool.call"}], [], [], [], PIN)
    assert [e["key"] for e in exp] == ["call:y", "call:z"]


def test_clean_run_reaches_full_tool_coverage():
    store, ours = _run()
    exp, a, res = _assess(store, ours)
    assert len(res["pairs"]) == 4 and not res["unmatched_spans"] and not res["unmatched_units"]
    assert a.measured["coverage"] == "4/4" and a.requirement_verdict == "SATISFIED"


def test_suppressed_record_is_still_breached():
    store, ours = _run(suppress=2)
    exp, a, res = _assess(store, ours)
    assert res["unmatched_spans"] == []                  # the before-only unit consumes its span (one to one) ...
    assert a.requirement_verdict == "BREACHED" and a.measured["coverage"] == "3/4"
    assert a.exceptions[0]["key"] == "call:ac-2-0000-0000-000000000000"


def test_suppressed_both_records_is_still_breached():
    store, ours = _run(suppress=2, drop_both=True)
    exp, a, res = _assess(store, ours)
    assert res["unmatched_spans"] == ["ac-2-0000-0000-000000000000"]
    assert a.requirement_verdict == "BREACHED" and a.measured["coverage"] == "3/4"


def test_without_the_join_nothing_matches():
    store, ours = _run()
    f = A.run_facts(store + ours)
    exp = c7.expected_events(RUN, f["actions"], [], [], [], PIN)
    assert c7.assess_run(RUN, exp, f["ours"], [], PIN, "2026-10-06T09:00:00.000Z").measured["coverage"] == "0/4"


def test_join_is_deterministic_and_one_to_one_under_any_input_order():
    store, ours = _run(6)
    base = T.join(T.tool_spans(store), T.tool_units(ours))
    for rev in (True, False):
        again = T.join(T.tool_spans(list(reversed(store)) if rev else store),
                       T.tool_units(list(reversed(ours)) if rev else ours))
        assert again == base
    assert len(set(p[0] for p in base["pairs"])) == len(set(p[1] for p in base["pairs"])) == 6


def test_join_respects_tool_name_run_and_window():
    store = _store([_span("tools/call", "runbook-lookup", "runbook-lookup___lookup", "a1-0000-0000-0000-000000000000",
                          T0, T0 + 1)])
    for u in (_rec("before", "u", "customer-records___customer_lookup", T0),                 # wrong tool
              _rec("before", "u", "runbook-lookup___lookup", T0 + 5),                         # starts after the span ended
              dict(_rec("before", "u", "runbook-lookup___lookup", T0), **{"trace.id": "f" * 32})):  # other trace
        assert T.join(T.tool_spans(store), T.tool_units([u]))["pairs"] == []
    ok = [_rec("before", "u", "runbook-lookup___lookup", T0), _rec("after", "u", "runbook-lookup___lookup", T0 + 1.1)]
    assert len(T.join(T.tool_spans(store), T.tool_units(ok))["pairs"]) == 1
    late = ok[:1] + [_rec("after", "u", "runbook-lookup___lookup", T0 + 0.5)]          # ended before the span did
    assert T.join(T.tool_spans(store), T.tool_units(late))["pairs"] == []
    assert len(T.join(T.tool_spans(store), T.tool_units(late), slack_ms=600)["pairs"]) == 1


def test_a_record_that_already_has_the_gateway_id_is_not_rejoined():
    store, ours = _run(2)
    ours = [dict(r, **{"call.id": "ac-0-0000-0000-000000000000"}) if r["tool.use_id"] == "use0" else r for r in ours]
    res = T.join(T.tool_spans(store), T.tool_units(ours))
    assert [p[1] for p in res["pairs"]] == ["use1"]

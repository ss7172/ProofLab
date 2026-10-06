"""C16 after-halt check is scoped to the invocation that was denied (N1's shape: 3 halts, 3 invocations)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import conftest  # noqa: E402,F401

from prooflab.evaluators import c16, c16_core  # noqa: E402

AS_OF = "2026-10-06T15:00:00.000Z"
RUN = "ifabric-run-1791294968-36d929"


def _pin():
    return c16_core.PinnedC16.from_dict(
        {"schema": "ifabric.pin/1", "register": {"version": "v1", "sha256": "a" * 64},
         "c16": {"control_id": "ACN-COST-001", "threshold_version": "C16-v1", "tiers": ["standard"],
                 "default_tier": "standard", "caps": {"standard": 40000}, "safety_ceiling": 300000,
                 "modes": ["enforce", "observe"], "mode": "enforce",
                 "bound": {"inline_bound_margin_pct": 10, "inline_bound_fallback_tokens": 8000, "max_tokens": 800}}},
        "f" * 64)


def _dec(actor, seq, at, verdict, call=None, ep="EP-1"):
    return {"run.id": RUN, "ep.id": ep, "actor.id": actor, "seq.in_stream": seq, "emitted.at": at,
            "verdict": verdict, "call.id": call, "inline.action": "halt" if verdict == "DENY" else "proceed",
            "handoff.id": None}


def _call(aid, at, tin=100, tout=10):
    return {"action_id": aid, "listener": "llm", "tokens_in": tin, "tokens_out": tout, "http_status": 200,
            "start": at, "end": at, "handoff_id": None}


def _n1():
    calls = [_call("it1", "2026-10-06T13:56:41.560Z"), _call("it2", "2026-10-06T13:56:56.951Z"),
             _call("net1", "2026-10-06T13:57:05.549Z"), _call("net2", "2026-10-06T13:57:07.427Z"),
             _call("ith3", "2026-10-06T13:57:16.404Z")]
    decs = [_dec("ifabric-it", 1, "2026-10-06T13:56:37.799Z", "ALLOW", "it1"),
            _dec("ifabric-it", 3, "2026-10-06T13:56:55.175Z", "ALLOW", "it2"),
            _dec("ifabric-it", 5, "2026-10-06T13:56:57.137Z", "DENY"),
            _dec("ifabric-network", 1, "2026-10-06T13:57:03.463Z", "ALLOW", "net1"),
            _dec("ifabric-network", 3, "2026-10-06T13:57:05.956Z", "ALLOW", "net2"),
            _dec("ifabric-network", 5, "2026-10-06T13:57:07.603Z", "DENY"),
            _dec("ifabric-it", 1, "2026-10-06T13:57:14.263Z", "ALLOW", "ith3"),
            _dec("ifabric-it", 3, "2026-10-06T13:57:16.566Z", "DENY")]
    return calls, decs


def _assess(calls, decs):
    comp = {"expected_action_ids": [d["call.id"] for d in decs if d["call.id"]], "spans_ingested": True}
    return c16.assess_run(RUN, calls, {"provenance": "LIVE_SUBJECT"}, decs, _pin(), comp, AS_OF)


def test_n1_three_halts_in_three_invocations_is_operated():
    calls, decs = _n1()
    a = _assess(calls, decs)
    assert a.operation == "OPERATED", a.measured["operation_note"]
    assert not [e for e in a.exceptions if e["kind"] == "model-span-after-halt"]
    assert a.requirement_verdict == "SATISFIED"


def test_call_in_the_halted_invocation_after_the_halt_is_a_violation_once():
    calls, decs = _n1()
    calls.append(_call("it3", "2026-10-06T13:56:58.000Z"))
    decs.append(_dec("ifabric-it", 7, "2026-10-06T13:56:57.900Z", "ALLOW", "it3"))
    a = _assess(calls, decs)
    exc = [e for e in a.exceptions if e["kind"] == "model-span-after-halt"]
    assert a.operation == "DEGRADED"
    assert [v["call"] for v in exc[0]["calls"]] == ["it3"]


def test_unattributed_call_after_a_halt_still_counts():
    calls, decs = _n1()
    calls.append(_call("ghost", "2026-10-06T13:57:20.000Z"))
    a = _assess(calls, decs)
    exc = [e for e in a.exceptions if e["kind"] == "model-span-after-halt"]
    assert a.operation == "DEGRADED"
    assert [v["call"] for v in exc[0]["calls"]] == ["ghost"]     # once, though three halts precede it

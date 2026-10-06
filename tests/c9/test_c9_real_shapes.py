"""PR-45: C9 counts every agent invocation of a run (customer h0, IT h1, network h2, IT h3) on the REAL record shapes
(b4 ledger export), and a '--condition warm-up' run satisfies the runtime-update rule for the next run on that pin."""
import importlib.util
import json
import os

from prooflab.query import assess_snapshot as A
from prooflab.query import c9_inputs as I

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("c9_assess_helpers", os.path.join(HERE, "test_c9_assess.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)

ARN = "arn:aws:bedrock-agentcore:us-east-1:613052889143:runtime/%s"
ARNS = {"ifabric-customer": ARN % "ifabric_customer-t09k78BrhE", "ifabric-it": ARN % "ifabric_it-0pyXUQ85X2",
        "ifabric-network": ARN % "ifabric_network-C331oZDpI7"}
TREAT = ("EP-0 declared treatment for %s: pin 493ee17e1606 -> 1b7c80fe779a, rails enforce -> enforce, generation %s "
         "(approved-spec)")


def real_run(cid, start_hm, end_hm, gen="3", condition="none", provenance="LIVE_SUBJECT", status="OK"):
    """The orchestrator's records as run.py emits them: h0 (customer) has NO handoff.sent and its handoff.received has
    no handoff.id / handoff.from / handoff.to; h1..h3 have both."""
    day = "2026-10-06"
    t0, t1 = "%sT%s.000Z" % (day, start_hm), "%sT%s.000Z" % (day, end_hm)
    kw = {"provenance": provenance, "run.condition": condition}
    out = [H.rec(cid, "run.started", t0, "run started: scenario S1 mode enforce", **kw)]
    for a in H.AGENTS:
        out.append(H.rec(cid, "ep0.declared_treatment", t0, TREAT % (a, gen), **kw))
    out.append(H.rec(cid, "handoff.received", t1, "invocation of ifabric-customer returned status=%s "
                     "disposition=gather-evidence halted=False duration_ms=4100" % status,
                     **dict(kw, **{"runtime.arn": ARNS["ifabric-customer"], "runtime.session_id": "s0"})))
    for n, (frm, to) in enumerate([("ifabric-customer", "ifabric-it"), ("ifabric-it", "ifabric-network"),
                                   ("ifabric-network", "ifabric-it")], 1):
        hid = "%s:h%d" % (cid, n)
        ids = {"handoff.id": hid, "handoff.from": frm, "handoff.to": to, "runtime.arn": ARNS[to],
               "runtime.session_id": "s%d" % n}
        out.append(H.rec(cid, "handoff.sent", t0, "handoff %s sent: %s -> %s" % (hid, frm, to), **dict(kw, **ids)))
        out.append(H.rec(cid, "handoff.received", t1, "invocation of %s returned status=OK disposition=escalate "
                         "halted=True duration_ms=%d" % (to, 5000 + n), **dict(kw, **ids)))
    out.append(H.rec(cid, "run.finished", t1, "run finished: status FINISHED", **kw))
    return out


def test_every_invocation_is_counted_per_runtime_on_the_real_shapes():
    recs = real_run("ifabric-run-1791291533-39c87b", "08:18:15", "08:19:50")
    assert I.invocations_expected(recs) == {"ifabric-customer": 1, "ifabric-it": 2, "ifabric-network": 1}
    assert I.diagnostic_durations(recs)["ifabric-customer"] == 4100          # h0's own duration is read too


def test_h0_runtime_resolved_from_detail_or_arn():
    r = H.rec("c", "handoff.received", "2026-10-06T08:19:00.000Z", "no text here", **{"runtime.arn": ARNS["ifabric-network"]})
    assert I.invocations_expected([r]) == {"ifabric-network": 1}


def test_a_single_agent_run_of_the_customer_counts_one():
    recs = [r for r in real_run("c1", "08:18:15", "08:19:50") if r.get("handoff.id") is None]
    assert I.invocations_expected(recs) == {"ifabric-customer": 1}


def test_customer_window_is_assessed_in_the_run(tmp_path):
    cid = "ifabric-run-1791291533-39c87b"
    snap = H.snapshot(tmp_path, [(cid, real_run(cid, "08:18:15", "08:19:50"))])
    H.measure_capture(snap, H.P1_POINTS)
    out = A.assess_snapshot(snap, controls=("C9",))
    d = json.load(open(out["written"][0][3]))
    rts = [w["runtime"] for w in d["measured"]["windows"]]
    assert "ifabric-customer" in rts and sorted(rts) == sorted(H.AGENTS)


def test_a_warm_up_run_on_the_same_pin_satisfies_the_runtime_update_rule(tmp_path):
    warm, nxt = "ifabric-run-1791291000-aaaaaa", "ifabric-run-1791291533-39c87b"
    runs = [(warm, real_run(warm, "08:14:00", "08:15:30", condition="warm-up", provenance="EXPLORATORY")),
            (nxt, real_run(nxt, "08:18:15", "08:19:50"))]
    snap = H.snapshot(tmp_path, runs)
    H.measure_capture(snap, H.P1_POINTS)
    out = A.assess_snapshot(snap, controls=("C9",))
    assert [w[1] for w in out["written"] if ".." not in w[1]] == [nxt]
    d = json.load(open(out["written"][0][3]))
    assert d["requirement_verdict"] == "SATISFIED" and not any("cold start" in g for g in d["gaps"])


def test_without_a_warm_up_the_first_run_after_a_patch_stays_indeterminate(tmp_path):
    nxt = "ifabric-run-1791291533-39c87b"
    snap = H.snapshot(tmp_path, [(nxt, real_run(nxt, "08:18:15", "08:19:50"))])
    H.measure_capture(snap, H.P1_POINTS)
    d = json.load(open(A.assess_snapshot(snap, controls=("C9",))["written"][0][3]))
    assert d["requirement_verdict"] == "INDETERMINATE"
    assert {g.split(":")[0] for g in d["gaps"] if "cold start" in g} == set(H.AGENTS)


def test_a_warm_up_at_an_older_generation_or_a_failed_call_does_not_count(tmp_path):
    nxt = "ifabric-run-1791291533-39c87b"
    for i, kw in enumerate([{"gen": "2"}, {"status": "ERROR"}]):
        warm = "ifabric-run-1791291000-aaaaa%d" % i
        runs = [(warm, real_run(warm, "08:14:00", "08:15:30", condition="warm-up", provenance="EXPLORATORY", **kw)),
                (nxt, real_run(nxt, "08:18:15", "08:19:50"))]
        snap = H.snapshot(tmp_path / str(i), runs)
        H.measure_capture(snap, H.P1_POINTS)
        d = json.load(open(A.assess_snapshot(snap, controls=("C9",))["written"][0][3]))
        assert d["requirement_verdict"] == "INDETERMINATE", kw

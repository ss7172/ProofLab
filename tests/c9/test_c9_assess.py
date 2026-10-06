"""PR-41: `assess --snapshot` assesses C9 from the AgentCore metric captures (two-sided, Errors, OC-20 gaps, hourly).

Fixtures are shaped like the real outputs: the EP-11 collector's get-metric-statistics capture + sidecar, and the
ops lane's measure.py form (b3/p1-metrics.json: CloudWatch prints the caller's -05:00 offset)."""
import json
import os

from prooflab.query import assess_snapshot as A
from prooflab.query import c9_inputs as I
from prooflab.query import engine as E

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V0 = os.path.join(ROOT, "register", "versions", "v0-pilot.yaml")
AGENTS = ("ifabric-customer", "ifabric-it", "ifabric-network")
BASE = {"ifabric-customer": 8192, "ifabric-it": 20000, "ifabric-network": 6770}
LIMITS = "max_relative_change_pct=50;violating_windows_max_pct=0;errors_max=0"


def register_text(limits=LIMITS, baselines=True):
    text = open(V0, encoding="utf-8").read()
    old = ('    observation_limit: "two-sided band around the frozen baseline: change limit PENDING-OWNER percent, '
           'violating windows PENDING-OWNER percent"\n')
    assert old in text
    text = text.replace(old, '    observation_limit: "%s"\n' % limits)
    if baselines:
        extra = "".join('    baseline_value_%s_S1: %d\n' % (a, BASE[a]) for a in AGENTS)
        text = text.replace("    declared_treatments: \"model-swap:ifabric-it:nemotron-nano-9b\"\n",
                            "    declared_treatments: \"model-swap:ifabric-it:nemotron-nano-9b\"\n" + extra)
    return text


def rec(cid, phase, at, detail, **kw):
    r = {"record_id": "ev-%s-%s-%s" % (cid[-6:], phase, at), "run.id": cid, "record_kind": "lifecycle", "phase": phase,
         "emitted.at": at, "ts": at, "detail": detail, "actor.id": "orchestrator", "authorship": "TESTIMONY",
         "provenance": kw.pop("provenance", "LIVE_SUBJECT")}
    r.update(kw)
    return r


def run_records(cid, start_hm, end_hm, condition="none", provenance="LIVE_SUBJECT", treat=None, day="2026-10-06"):
    t0, t1 = "%sT%s.000Z" % (day, start_hm), "%sT%s.000Z" % (day, end_hm)
    out = [rec(cid, "run.started", t0, "run started: scenario S1 mode observe", provenance=provenance,
               **{"run.condition": condition})]
    for agent, gen in sorted((treat or {}).items()):
        out.append(rec(cid, "ep0.declared_treatment", t0, "EP-0 declared treatment for %s: model-swap a -> b for named "
                       "run N8, generation %s (declared in the pinned register v1)" % (agent, gen), provenance=provenance))
    for i, agent in enumerate(AGENTS + ("ifabric-it",)):
        out.append(rec(cid, "handoff.sent", t0, "handoff h%d sent" % i, provenance=provenance,
                       **{"handoff.to": agent, "handoff.id": "%s:h%d" % (cid, i)}))
        out.append(rec(cid, "handoff.received", t1, "invocation of %s returned status=OK duration_ms=%d" % (agent, 9000 + i),
                       provenance=provenance, **{"handoff.to": agent, "handoff.id": "%s:h%d" % (cid, i)}))
    out.append(rec(cid, "run.finished", t1, "run finished: status FINISHED", provenance=provenance))
    return out


def collector_capture(snap, runtime, metric, stat, points, start, end, captured_at, period=60):
    d = os.path.join(snap, "raw", "agentcore-metrics", runtime.replace("-", "_"))
    os.makedirs(d, exist_ok=True)
    name = "%s-%s-%s.json" % (metric, stat, start.replace(":", "").replace("-", ""))
    doc = {"Label": metric, "Datapoints": [{"Timestamp": t, stat: v, "Unit": "Milliseconds"} for t, v in points]}
    with open(os.path.join(d, name), "w") as fh:
        json.dump(doc, fh)
    side = {"surface": "agentcore-metrics", "captured_at": captured_at,
            "scope": {"runtime": runtime.replace("-", "_"), "start": start, "end": end, "metric": metric,
                      "statistic": stat, "period": period}}
    with open(os.path.join(d, name + ".capture.json"), "w") as fh:
        json.dump(side, fh)


def snapshot(tmp_path, runs, as_of="2026-10-06T10:05:00Z", reg=None):
    snap = str(tmp_path / "snap")
    os.makedirs(os.path.join(snap, "store"))
    os.makedirs(os.path.join(snap, "derived"))
    os.makedirs(os.path.join(snap, "register", "versions"))
    recs = [r for cid, rr in runs for r in rr]
    with open(os.path.join(snap, "store", "records.jsonl"), "w") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in recs))
    cat = [{"run_id": cid, "assessed": not any(r.get("run.condition") == "warm-up" for r in rr)} for cid, rr in runs]
    with open(os.path.join(snap, "derived", "run-catalogue.jsonl"), "w") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in cat))
    with open(os.path.join(snap, "SNAPSHOT.json"), "w") as fh:
        json.dump({"as_of": as_of}, fh)
    with open(os.path.join(snap, "register", "versions", "v1.yaml"), "w") as fh:
        fh.write(reg if reg is not None else register_text())
    return snap


def measure_capture(snap, points, window=("2026-10-06T08:18:00+00:00", "2026-10-06T08:22:50+00:00"), errors=0.0,
                    name="p1-metrics.json", invocations=None):
    """The ops lane's measure.py shape with the caller's -05:00 offset (b3/p1-metrics.json)."""
    res = {}
    for agent, pts in points.items():
        res["%s Latency Maximum" % agent] = {"points": pts, "status": "Complete"}
        res["%s Errors Sum" % agent] = {"points": [[t, errors] for t, _ in pts], "status": "Complete"}
        total = 2.0 if agent == "ifabric-it" else 1.0          # the trio + Gateway C: IT is invoked twice
        inv = [[t, (invocations or {}).get(agent, total if i == 0 else 0.0)] for i, (t, _) in enumerate(pts)]
        res["%s Invocations Sum" % agent] = {"points": inv, "status": "Complete"}
    d = os.path.join(snap, "raw", "agentcore-metrics", "metric-data")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w") as fh:
        json.dump({"window": list(window), "results": res, "captured_at": "2026-10-06T08:25:00Z"}, fh)


P1_POINTS = {"ifabric-customer": [["2026-10-06T03:18:00-05:00", 8192.0]],
             "ifabric-it": [["2026-10-06T03:19:00-05:00", 21000.0], ["2026-10-06T03:18:00-05:00", 19973.0]],
             "ifabric-network": [["2026-10-06T03:18:00-05:00", 6770.0]]}
CID = "ifabric-run-1791274694-7725ea"


def _load(path):
    with open(path) as fh:
        return json.load(fh)


def test_utc_reads_the_callers_offset():
    assert I.iso(I.utc("2026-10-06T03:18:00-05:00")) == "2026-10-06T08:18:00Z"
    assert I.runtime_key("ifabric_it::DEFAULT") == "ifabric-it"


def test_healthy_run_is_satisfied_from_the_measure_shape(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    measure_capture(snap, P1_POINTS, invocations={"ifabric-it": 1.0})       # one invocation in each of two minutes
    out = A.assess_snapshot(snap, controls=("C9",))
    run = [w for w in out["written"] if w[1] == CID]
    assert run and run[0][2] == "SATISFIED", out
    d = _load(run[0][3])
    it = [w for w in d["measured"]["windows"] if w["runtime"] == "ifabric-it"][0]
    assert it["latency_max"] == "21000" and it["direction"] == "two-sided" and it["errors"] == 0
    assert d["measured"]["inputs"]["figure_of_record"].startswith("AWS/Bedrock-AgentCore Latency Maximum")
    assert d["measured"]["inputs"]["diagnostic_invocation_ms"]["ifabric-it"] == 9003
    assert d["threshold_version"] == "C9-v0" and d["requirement_verdict"] == "SATISFIED"
    hourly = [w for w in out["written"] if w[1].startswith("2026-10-06T08:00:00Z..")]
    assert hourly and hourly[0][2] == "SATISFIED"
    h = _load(hourly[0][3])
    assert h["scope_kind"] == "window" and os.path.basename(hourly[0][3]) == "window-20261006T08.json"


def test_faster_after_the_swap_breaches_two_sided(tmp_path):
    pts = dict(P1_POINTS, **{"ifabric-it": [["2026-10-06T03:18:00-05:00", 2500.0]]})   # nano: much faster
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    measure_capture(snap, pts)
    out = A.assess_snapshot(snap, controls=("C9",))
    d = _load([w for w in out["written"] if w[1] == CID][0][3])
    assert d["requirement_verdict"] == "BREACHED"
    assert [e["runtime"] for e in d["exceptions"]] == ["ifabric-it"]
    hourly = [w for w in out["written"] if ".." in w[1]][0]
    assert hourly[2] == "BREACHED"


def test_slower_breaches_and_errors_breach(tmp_path):
    pts = dict(P1_POINTS, **{"ifabric-it": [["2026-10-06T03:18:00-05:00", 57297.0]]})
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    measure_capture(snap, pts)
    assert A.assess_snapshot(snap, controls=("C9",))["written"][0][2] == "BREACHED"
    snap2 = snapshot(tmp_path / "b", [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    measure_capture(snap2, P1_POINTS, errors=1.0)
    d = _load(A.assess_snapshot(snap2, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] == "BREACHED"
    assert any(w["error_violation"] for w in d["measured"]["windows"])


def test_collector_shape_and_oc20_not_yet_present_is_indeterminate(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    for agent in AGENTS:
        # captured at 08:19:55: before W2 closes (08:20:00): the last datapoint cannot be there yet (OC-20)
        collector_capture(snap, agent, "Latency", "Maximum", [], "2026-10-06T08:18:00Z", "2026-10-06T08:21:00Z",
                          "2026-10-06T08:19:55Z")
    d = _load(A.assess_snapshot(snap, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] == "INDETERMINATE"
    assert any("not yet present" in g and "OC-20" in g for g in d["gaps"])


def test_a_partial_early_read_is_not_judged(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    for agent in AGENTS:
        collector_capture(snap, agent, "Latency", "Maximum", [("2026-10-06T08:18:00+00:00", float(BASE[agent]))],
                          "2026-10-06T08:18:00Z", "2026-10-06T08:21:00Z", "2026-10-06T08:19:55Z")
    d = _load(A.assess_snapshot(snap, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] == "INDETERMINATE" and any("not yet complete" in g for g in d["gaps"])


def test_collector_shape_on_time_is_assessed(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    for agent in AGENTS:
        collector_capture(snap, agent, "Latency", "Maximum", [("2026-10-06T08:19:00+00:00", float(BASE[agent]))],
                          "2026-10-06T08:18:00Z", "2026-10-06T08:21:00Z", "2026-10-06T08:20:30Z")
        collector_capture(snap, agent, "Errors", "Sum", [("2026-10-06T08:19:00+00:00", 0.0)],
                          "2026-10-06T08:18:00Z", "2026-10-06T08:21:00Z", "2026-10-06T08:20:30Z")
    d = _load(A.assess_snapshot(snap, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] == "SATISFIED", d["gaps"]


def test_hourly_capture_never_feeds_a_run_window(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    for agent in AGENTS:
        collector_capture(snap, agent, "Latency", "Maximum", [("2026-10-06T08:00:00+00:00", float(BASE[agent]))],
                          "2026-10-06T08:00:00Z", "2026-10-06T09:00:00Z", "2026-10-06T09:30:00Z", period=3600)
    d = _load(A.assess_snapshot(snap, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] == "INDETERMINATE"
    assert any("no AgentCore metric capture at 60 s" in g for g in d["gaps"])


def test_no_baseline_or_prose_limit_is_never_a_pass(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))], reg=open(V0).read())
    measure_capture(snap, P1_POINTS)
    d = _load(A.assess_snapshot(snap, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] == "NOT_ASSESSED"
    snap2 = snapshot(tmp_path / "b", [(CID, run_records(CID, "08:18:15", "08:19:50"))],
                     reg=register_text(limits="two-sided band PENDING-OWNER"))
    measure_capture(snap2, P1_POINTS)
    d = _load(A.assess_snapshot(snap2, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] in ("NOT_ASSESSED", "INDETERMINATE")
    snap3 = snapshot(tmp_path / "c", [(CID, run_records(CID, "08:18:15", "08:19:50"))],
                     reg=register_text(limits="two-sided band PENDING-OWNER"))
    measure_capture(snap3, P1_POINTS)
    out = A.assess_snapshot(snap3, controls=("C9",), overrides=["C9:max_relative_change_pct=50",
                                                                "C9:violating_windows_max_pct=0"])
    assert _load(out["written"][0][3])["requirement_verdict"] == "SATISFIED"


def test_warm_up_rule_after_a_runtime_update(tmp_path):
    warm = "ifabric-run-1791274500-aaaaaa"
    n8 = "ifabric-run-1791274694-7725ea"
    runs = [(warm, run_records(warm, "08:14:00", "08:15:30", condition="warm-up", provenance="EXPLORATORY",
                               treat={"ifabric-it": "5"})),
            (n8, run_records(n8, "08:18:15", "08:19:50", treat={"ifabric-it": "5"}))]
    snap = snapshot(tmp_path, runs)
    measure_capture(snap, P1_POINTS)
    out = A.assess_snapshot(snap, controls=("C9",))
    assert [w[1] for w in out["written"] if not ".." in w[1]] == [n8]          # the warm-up is never assessed
    assert out["written"][0][2] == "SATISFIED"
    # the same run with no warm-up at that generation: a cold start confounds it -> INDETERMINATE
    runs[0] = (warm, run_records(warm, "08:14:00", "08:15:30", condition="warm-up", provenance="EXPLORATORY",
                                 treat={"ifabric-it": "4"}))
    snap2 = snapshot(tmp_path / "b", runs)
    measure_capture(snap2, P1_POINTS)
    d = _load(A.assess_snapshot(snap2, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] == "INDETERMINATE" and any("cold start" in g for g in d["gaps"])


def test_open_hour_has_no_roll_up_and_query_window_reads_the_hour(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))], as_of="2026-10-06T08:40:00Z")
    measure_capture(snap, P1_POINTS)
    out = A.assess_snapshot(snap, controls=("C9",))
    assert [w for w in out["written"] if ".." in w[1]] == []                   # 08:00-09:00 not closed at 08:40
    snap2 = snapshot(tmp_path / "b", [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    measure_capture(snap2, dict(P1_POINTS, **{"ifabric-it": [["2026-10-06T03:18:00-05:00", 2500.0]]}))
    A.assess_snapshot(snap2, controls=("C9",))
    pack = E.Pack(snap2)
    kinds = sorted(a["scope_kind"] for a in pack.assessments_for("C9"))
    assert kinds == ["run", "window"]


def test_fewer_invocations_in_the_metric_than_the_run_made_is_a_gap(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))])
    measure_capture(snap, dict(P1_POINTS, **{"ifabric-it": [["2026-10-06T03:18:00-05:00", 19973.0]]}),
                    invocations={"ifabric-it": 1.0})
    d = _load(A.assess_snapshot(snap, controls=("C9",))["written"][0][3])
    assert d["requirement_verdict"] == "INDETERMINATE" and any("a datapoint is missing" in g for g in d["gaps"])


def test_claim_does_not_count_a_not_assessed_control_as_coverage(tmp_path):
    snap = snapshot(tmp_path, [(CID, run_records(CID, "08:18:15", "08:19:50"))], reg=open(V0).read())
    measure_capture(snap, P1_POINTS)
    A.assess_snapshot(snap, controls=("C9",))
    row = [r for r in E.claim_line(E.Pack(snap))["rows"] if r["control"] == "C9"][0]
    assert row["worst"] == "NOT_ASSESSED"
    assert E.claim_line(E.Pack(snap))["coverage"].startswith("partial coverage: 0 of 3")

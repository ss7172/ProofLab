import json
import os

from prooflab.stitch import stitcher
from prooflab.store import observations

FIX = os.path.join(os.path.dirname(__file__), "..", "store", "fixtures")
CID = "ifabric-run-1791300000-a1b2c3"


def _records():
    rows = [json.loads(l) for l in open(os.path.join(FIX, "ledger-fixture.jsonl")) if l.strip()]
    gw = observations.normalize_gateway_text(open(os.path.join(FIX, "gateway-fixture.log")).read(), "raw/gateway/g.log")
    inv = observations.normalize_invocation_text(open(os.path.join(FIX, "invocations-fixture.jsonl")).read(), "raw/aws-invocations/a.jsonl")
    return rows + gw["records"] + inv["records"]


def _row(out, rid):
    return [r for r in out["run_index"] if r["run_id"] == rid][0]


def test_join_by_cid_action_id_handoff_and_session():
    recs = _records()
    gw = [r for r in recs if r.get("run.id") == CID and r.get("call.id")][0]
    mine = dict(gw, **{"record_id": "obs-" + "3" * 32})           # our own emit for the same gateway action id
    out = stitcher.stitch(recs + [mine])
    row = _row(out, CID)
    keys = set(l["key"] for l in row["links"])
    assert {"correlation_id", "handoff.id", "runtime.session_id", "call.id"} <= keys
    ses = [l for l in row["links"] if l["key"] == "runtime.session_id"][0]
    assert len(ses["record_ids"]) >= 2
    assert row["family"] == "ifabric-run"


def test_retry_suspect_and_unmatched_session_become_facts_not_errors():
    out = stitcher.stitch(_records())
    row = _row(out, CID)
    assert len(row["retry_suspects"]) == 1                     # one session id on two AWS records
    gaps = [f for f in out["unjoined"] if f["key"] == "runtime.session_id"]
    assert len(gaps) == 1 and gaps[0]["missing_from"] == ["handoff.sent"]
    hand = [f for f in out["unjoined"] if f["key"] == "handoff.id"]
    assert len(hand) == 1 and hand[0]["value"] == CID + ":h2"   # sent with no received


def test_unattributed_invocation_gets_its_own_incident_row():
    out = stitcher.stitch(_records())
    rows = [r for r in out["run_index"] if r["run_id"].startswith("unattributed:")]
    assert len(rows) == 1 and rows[0]["family"] == "unattributed"


def test_unresolved_refusals_are_listed_as_link_gaps_never_dropped():
    out = stitcher.stitch(_records())
    unresolved = [r for r in out["run_index"] if r["run_id"].startswith("unresolved:")]
    gaps = [f for f in out["unjoined"] if f["key"] == "trace.id"]
    assert unresolved and len(gaps) >= len(unresolved) - 1 and all(g["missing_from"] for g in gaps)


def test_unresolved_trace_resolves_through_another_runs_trace():
    recs = _records()
    trace = "f" * 32
    from prooflab.contract import record as R
    from prooflab.contract import ids
    base = [r for r in recs if r.get("run.id") == CID and r["record_kind"] == "handoff"][0]
    carrier = dict(base, **{"record_id": "obs-" + "1" * 32, "trace.id": trace})
    refusal = R.new_record("platform_decision", "x", **{
        "record_id": "obs-" + "2" * 32, "run.id": ids.unresolved_correlation_id(trace), "detail": "d",
        "verdict": "DENY", "observed.at": "2026-10-06T04:31:20.000Z", "observed.clock": "gateway",
        "provenance": "UNATTRIBUTED", "authorship": "PLATFORM", "emitter": "t", "trace.id": trace})
    out = stitcher.stitch([carrier, refusal])
    assert _row(out, "unresolved:" + trace)["resolved_to"] == CID
    assert _row(out, CID)["resolved_from"] == ["unresolved:" + trace]
    assert not out["unjoined"] or all(f["value"] != trace for f in out["unjoined"])


def test_event_time_match_only_with_a_supplied_tolerance_and_input_untouched():
    recs = _records()
    before = json.dumps(recs, sort_keys=True)
    plain = stitcher.stitch(recs)
    assert "eventTime~handoff.received" not in json.dumps(plain)
    near = stitcher.stitch(recs, join_tolerance_s=5)
    assert "eventTime~handoff.received" in json.dumps(near)
    assert json.dumps(recs, sort_keys=True) == before          # the stitcher never changes a record


def test_deterministic_regardless_of_input_order():
    recs = _records()
    a = stitcher.dumps_rows(stitcher.stitch(recs)["run_index"])
    b = stitcher.dumps_rows(stitcher.stitch(list(reversed(recs)))["run_index"])
    assert a == b


def test_smoke_row_without_ifabric_fields_does_not_crash():
    out = stitcher.stitch([{"correlation_id": "ifabric-test-ledger-smoke-1791252169", "phase": "smoke"}])
    assert out["run_index"][0]["run_id"] == "ifabric-test-ledger-smoke-1791252169"

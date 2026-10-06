"""EP-2 over a refreshed snapshot's store (the assess path): same core, same pin, stored with ep.id EP-2,
reconciled call by call against EP-1."""
import json
import os

import conftest as scaffold
from prooflab.adapters.postrun import c16_replay as R
from prooflab.evaluators import c16
from prooflab.store import ingest

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
CID = "ifabric-test-1791260100-d4e5f6"
NOW = "2026-10-06T15:00:00.000Z"


def _pin():
    with open(os.path.join(FIX, "pin_n2_observe.json"), encoding="utf-8") as fh:
        return R.load_pin(fh.read())[0]


def _gw(aid, at, tin, tout, cid=CID):
    return {"run.id": cid, "authorship": "PLATFORM", "observed.clock": "gateway", "record_kind": "metric",
            "call.id": aid, "tokens.in": tin, "tokens.out": tout, "observed.at": at, "outcome.http_status": 200,
            "trace.id": "c" * 32, "record_id": "obs-" + aid, "ts": at}


def _ep1(aid, at, verdict="ALLOW"):
    return {"run.id": CID, "ep.id": "EP-1", "record_kind": "decision", "authorship": "TESTIMONY", "call.id": aid,
            "verdict": verdict, "inline.action": "proceed", "emitted.at": at, "actor.id": "ifabric-it",
            "seq.in_stream": 1, "handoff.id": None}


ROWS = [_gw("b", "2026-10-06T13:56:45.000Z", 300, 30), _gw("a", "2026-10-06T13:56:41.000Z", 100, 10),
        _gw("a", "2026-10-06T13:56:41.000Z", 100, 10), _gw("x", "2026-10-06T13:56:42.000Z", 9, 9, "other-run")]


def test_store_calls_in_gateway_order_once_per_action():
    calls = R.store_model_calls(ROWS, CID)
    assert [c["action_id"] for c in calls] == ["a", "b"]


def test_replay_store_is_deterministic_and_ep2(monkeypatch):
    sha_file = scaffold.sha_file()
    one, note = R.replay_store(CID, ROWS, _pin(), NOW, sha_file=sha_file)
    two, _ = R.replay_store(CID, ROWS, _pin(), NOW, sha_file=sha_file)
    assert note is None and one == two and len(one) == 2
    assert all(r["ep.id"] == "EP-2" and R.is_replay_record(r) for r in one)
    assert [r["call.id"] for r in one] == ["a", "b"]


def test_replay_store_fails_closed_with_a_note(tmp_path):
    bad = tmp_path / "sha"
    bad.write_text("0" * 64 + "\n")
    recs, note = R.replay_store(CID, ROWS, _pin(), NOW, sha_file=str(bad))
    assert recs == [] and "does not match" in note
    recs, note = R.replay_store("ifabric-test-1791260999-000000", ROWS, _pin(), NOW, sha_file=scaffold.sha_file())
    assert recs == [] and "no model-call spans" in note


def test_merge_replay_replaces_earlier_replay_and_rehashes(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "store"))
    with open(os.path.join(root, "store", "records.jsonl"), "w") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in ROWS[:2]))
    with open(os.path.join(root, "SNAPSHOT.json"), "w") as fh:
        json.dump({"files": {"store/records.jsonl": "0"}}, fh)
    old, _ = R.replay_store(CID, ROWS, _pin(), "2026-10-06T14:00:00.000Z", sha_file=scaffold.sha_file())
    ingest.merge_replay(root, old, [CID], R.is_replay_record)
    new, _ = R.replay_store(CID, ROWS, _pin(), NOW, sha_file=scaffold.sha_file())
    ingest.merge_replay(root, new, [CID], R.is_replay_record)
    with open(os.path.join(root, "store", "records.jsonl")) as fh:
        rows = [json.loads(l) for l in fh]
    assert sorted(r["record_id"] for r in rows if r.get("ep.id") == "EP-2") == sorted(r["record_id"] for r in new)
    assert len(rows) == 4
    with open(os.path.join(root, "SNAPSHOT.json")) as fh:
        assert json.load(fh)["files"]["store/records.jsonl"] != "0"


def _assess(decisions):
    calls = [{"action_id": c["action_id"], "listener": "llm", "tokens_in": c["tokens_in"],
              "tokens_out": c["tokens_out"], "http_status": 200, "start": c["stamp"], "end": c["stamp"]}
             for c in R.store_model_calls(ROWS, CID)]
    comp = {"expected_action_ids": ["a", "b"], "spans_ingested": True}
    return c16.assess_run(CID, calls, {}, decisions, _pin(), comp, NOW)


def test_ep1_and_ep2_reconciled_complete_and_missing_ep2_is_partial():
    ep1 = [_ep1("a", "2026-10-06T13:56:40.000Z"), _ep1("b", "2026-10-06T13:56:44.000Z")]
    ep2, _ = R.replay_store(CID, ROWS, _pin(), NOW, sha_file=scaffold.sha_file())
    a = _assess(ep1 + ep2)
    assert a.measured["ep2_decisions"] == 2 and a.operation == "OPERATED"
    assert a.evidence_sufficiency == "COMPLETE"
    b = _assess(ep1)
    assert b.evidence_sufficiency == "PARTIAL"
    assert b.requirement_verdict == a.requirement_verdict
    assert any(e["kind"] == "ep2-replay-missing" for e in b.exceptions)

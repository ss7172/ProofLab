"""A2: two overlapping aws/spans captures of one run are counted once per action id (latest capture wins)."""
import json
import os

from prooflab.store import snapshot

CID = "ifabric-run-1791294968-36d929"


def _row(action, tin, tout, nano):
    span = {"name": "llm", "startTimeUnixNano": str(nano), "endTimeUnixNano": str(nano + 1000000),
            "attributes": {"modaas.run_id": CID, "modaas.action_id": action, "listener": "llm",
                           "http.status": 200, "gen_ai.usage.input_tokens": tin,
                           "gen_ai.usage.output_tokens": tout, "gen_ai.request.model": "m"}}
    return json.dumps({"@timestamp": "2026-10-06 13:56:25.000", "@message": json.dumps(span)})


def _capture(root, name, rows, at):
    d = os.path.join(root, "raw", "aws-spans", CID)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w") as fh:
        fh.write("\n".join(rows) + "\n")
    with open(os.path.join(d, name + ".capture.json"), "w") as fh:
        json.dump({"captured_at": at}, fh)


def test_two_overlapping_captures_sum_once(tmp_path):
    root = str(tmp_path)
    base = 1791294985000000000
    r1 = [_row("a1", 100, 10, base), _row("a2", 200, 20, base + 10 ** 9)]
    # r2: a superset, with a2's figure revised (late data) and a3 new
    r2 = [_row("a1", 100, 10, base), _row("a2", 210, 20, base + 10 ** 9), _row("a3", 300, 30, base + 2 * 10 ** 9)]
    _capture(root, "spans.jsonl", r1, "2026-10-06T13:58:53.926Z")
    _capture(root, "spans.jsonl.r2", r2, "2026-10-06T14:04:35.000Z")
    snapshot.refresh(root, as_of="2026-10-06T15:00:00Z", run_ids={CID}, provenance={CID: "LIVE_SUBJECT"})
    with open(os.path.join(root, "derived", "run-catalogue.jsonl")) as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    row = [r for r in rows if r["run_id"] == CID][0]
    assert (row["tokens_in"], row["tokens_out"]) == (100 + 210 + 300, 10 + 20 + 30)
    assert row["sources"]["gateway"] == 3
    assert row["label"] == "LIVE_SUBJECT" and row["assessed"] is True


def test_capture_order_uses_sidecar_time_then_round(tmp_path):
    root = str(tmp_path)
    _capture(root, "spans.jsonl.r2", [_row("a1", 1, 1, 1)], "2026-10-06T14:00:00Z")
    _capture(root, "spans.jsonl", [_row("a1", 1, 1, 1)], "2026-10-06T13:00:00Z")
    paths = sorted([os.path.join(root, "raw", "aws-spans", CID, n) for n in ("spans.jsonl.r2", "spans.jsonl")],
                   key=snapshot._capture_order)
    assert [os.path.basename(p) for p in paths] == ["spans.jsonl", "spans.jsonl.r2"]

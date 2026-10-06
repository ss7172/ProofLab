"""D3: Logs Insights rows (@timestamp / @message = the span JSON) are read by refresh and by postrun."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prooflab.adapters.postrun import c16_replay as R  # noqa: E402
from prooflab.contract import ids  # noqa: E402
from prooflab.store import observations as O  # noqa: E402
from prooflab.store import snapshot as S  # noqa: E402

CID = ids.mint_cid("ifabric-run", 1790000000)


def _row(aid="act-1"):
    span = {"attributes": {"listener": "llm", "modaas.run_id": CID, "modaas.action_id": aid, "http.status": "200",
                           "gen_ai.usage.input_tokens": "10", "gen_ai.usage.output_tokens": "5",
                           "gen_ai.request.model": "m"},
            "startTimeUnixNano": "1790000000000000000", "endTimeUnixNano": "1790000001000000000"}
    return {"@timestamp": "2026-10-05 12:00:01.000", "@message": json.dumps(span, sort_keys=True)}


def test_flatten_gives_gateway_shape():
    flat = O.insights_row_to_flat(_row())
    assert flat["modaas.run_id"] == CID and flat["protocol"] == "llm" and flat["ts"].endswith("Z")


def test_refresh_reads_aws_spans_capture(tmp_path):
    d = tmp_path / "raw" / "aws-spans" / CID
    d.mkdir(parents=True)
    (d / "spans.jsonl").write_text(json.dumps(_row()) + "\n")
    res = S.refresh(str(tmp_path), run_ids={CID})
    assert res["records"] == 1
    rec = json.loads((tmp_path / "store" / "records.jsonl").read_text().splitlines()[0])
    assert rec["tokens.in"] == 10 and rec["call.id"] == "act-1"
    assert (tmp_path / "kit-crosscheck" / CID / "gateway-log.json").is_file()
    assert (tmp_path / "derived" / "corroboration").is_dir()


def test_postrun_unpacks_message():
    rows = R.load_rows(json.dumps(_row()) + "\n")
    calls = R.model_call_spans(rows, CID)
    assert [c["action_id"] for c in calls] == ["act-1"] and calls[0]["tokens_in"] == 10

"""PR-41 (b6b): an ifabric-assure gateway call has no CID (the gateway mints its own root trace and uses it as
modaas.run_id), so it joins its incident's analysis by ACTION ID, never 'unattributed'."""
import json

from prooflab.adapters.collectors import aws_spans
from prooflab.contract import ids
from prooflab.humanloop import mirror
from prooflab.store import observations as O
from prooflab.store import snapshot as S
from prooflab.stitch import stitcher

N2 = ids.mint_cid("ifabric-run", 1791270000)
ACTION = "9cbe05fb-3ad4-4a64-b024-c3b6f8c8b075"
TRACE = "07047a289b04ad44454f8c0ae2c19496"
FINDING = "ifabric:C16:C16-v1:run:%s:breach" % N2


def _row(run_id=TRACE, action=ACTION):
    span = {"attributes": {"listener": "llm", "modaas.run_id": run_id, "modaas.action_id": action, "http.status": "200",
                           "gen_ai.usage.input_tokens": "696", "gen_ai.usage.output_tokens": "194",
                           "gen_ai.request.model": "nvidia.nemotron-super-3-120b"},
            "traceId": TRACE, "startTimeUnixNano": "1791281409618000000", "endTimeUnixNano": "1791281415296000000"}
    return json.dumps({"@timestamp": "2026-10-06 10:10:15.296", "@message": json.dumps(span, sort_keys=True)})


def _analysis_record():
    line = json.dumps({"ts": "2026-10-06T10:10:20Z", "state": "ANALYSIS_WRITTEN", "finding_id": FINDING,
                       "action_ids": [ACTION, "other-action"], "note_digest": "f1ffa81f"})
    recs = mirror.mirror_lines([line])
    assert recs and recs[0]["run.id"] == N2 and ACTION in recs[0]["call.id"]
    return recs[0]


def test_unknown_action_id_stays_another_partys_sighting():
    out = O.normalize_gateway_text(_row(), "raw/aws-spans/x/spans.jsonl", insights=True)
    assert out["records"] == [] and out["sightings"][0]["run_id"] == TRACE


def test_known_action_id_is_kept_as_unresolved_trace():
    out = O.normalize_gateway_text(_row(), "raw/aws-spans/x/spans.jsonl", insights=True, known_action_ids={ACTION})
    assert len(out["records"]) == 1 and out["sightings"] == []
    rec = out["records"][0]
    assert rec["run.id"] == "unresolved:" + TRACE and rec["call.id"] == ACTION and rec["tokens.in"] == 696


def test_stitcher_attributes_the_assure_call_to_its_incident_by_action_id():
    span = O.normalize_gateway_text(_row(), "r", insights=True, known_action_ids={ACTION})["records"][0]
    out = stitcher.stitch([span, _analysis_record()])
    rows = dict((r["run_id"], r) for r in out["run_index"])
    u = rows["unresolved:" + TRACE]
    assert u["resolved_to"] == N2 and u["resolved_by"] == "call.id" and u["attributed_to"] == [FINDING]
    assert any(l["key"] == "call.id" and l["value"] == ACTION for l in rows[N2]["links"])
    assert "unresolved:" + TRACE in rows[N2]["resolved_from"]
    assert not [f for f in out["unjoined"] if f.get("run_id") == "unresolved:" + TRACE]


def test_refresh_end_to_end_from_the_ledger_and_an_action_capture(tmp_path):
    (tmp_path / "raw" / "ledger").mkdir(parents=True)
    (tmp_path / "raw" / "ledger" / (N2 + ".jsonl")).write_text(json.dumps(_analysis_record()) + "\n")
    d = tmp_path / "raw" / "aws-spans" / ("action-" + ACTION)
    d.mkdir(parents=True)
    (d / "spans.jsonl").write_text(_row() + "\n")
    S.refresh(str(tmp_path), run_ids={N2})
    idx = [json.loads(l) for l in (tmp_path / "derived" / "run-index.jsonl").read_text().splitlines()]
    u = [r for r in idx if r["run_id"] == "unresolved:" + TRACE][0]
    assert u["resolved_to"] == N2 and u["attributed_to"] == [FINDING]
    cat = (tmp_path / "derived" / "run-catalogue.jsonl").read_text()
    assert TRACE not in cat                                   # never listed as another party's run


def test_collector_pulls_by_action_id():
    q = aws_spans.build_action_query(ACTION)
    assert 'attributes.modaas.action_id = "%s"' % ACTION in q


def test_pull_by_action_writes_a_capture_refresh_reads(tmp_path):
    from prooflab.adapters.collectors import capture

    def fake(argv):
        if "start-query" in argv:
            return 0, b'{"queryId": "q1"}', b""
        msg = json.loads(_row())["@message"]
        return 0, json.dumps({"status": "Complete", "results": [[{"field": "@timestamp", "value": "2026-10-06 10:10:15.296"},
                                                                  {"field": "@message", "value": msg}]]}).encode(), b""

    ctx = capture.Ctx(root=str(tmp_path), runner=fake, now=lambda: "2026-10-06T10:30:00Z")
    side = aws_spans.pull_by_action(ctx, ACTION, "2026-10-06T10:00:00Z", "2026-10-06T10:20:00Z")
    assert side["path"] == "raw/aws-spans/action-%s/spans.jsonl" % ACTION
    assert any('modaas.action_id = "%s"' % ACTION in " ".join(c) for c in ctx.calls)

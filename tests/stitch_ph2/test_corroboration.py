import copy
import json
import os
import subprocess
import sys

from prooflab.contract import verdicts as V
from prooflab.stitch import corroboration, kit_crosscheck, mon02, stitcher
from prooflab.store import observations

FIX = os.path.join(os.path.dirname(__file__), "..", "store", "fixtures")
CID = "ifabric-run-1791300000-a1b2c3"
KIT = os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-static/starter/evaluate.py")


def _records():
    rows = [json.loads(l) for l in open(os.path.join(FIX, "ledger-fixture.jsonl")) if l.strip()]
    gw = observations.normalize_gateway_text(open(os.path.join(FIX, "gateway-fixture.log")).read(), "raw/gateway/g.log")
    inv = observations.normalize_invocation_text(open(os.path.join(FIX, "invocations-fixture.jsonl")).read(), "raw/aws-invocations/a.jsonl")
    return rows + gw["records"] + inv["records"]


def _gw_llm(recs, run=CID):
    return [r for r in recs if r.get("run.id") == run and r.get("record_kind") == "metric" and r.get("call.id")]


def _ours_for(gw, tin=None, tout=None, **extra):
    r = copy.deepcopy(gw)
    r.update({"authorship": "TESTIMONY", "observed.clock": "script-host", "record_id": "ours-" + gw["call.id"],
              "tokens.in": gw["tokens.in"] if tin is None else tin,
              "tokens.out": gw["tokens.out"] if tout is None else tout})
    r.update(extra)
    return r


def test_reports_are_byte_identical_on_rerun(tmp_path):
    recs = _records()
    a = corroboration.corroborate(recs)
    b = corroboration.corroborate(list(reversed(recs)))
    pa = corroboration.write(str(tmp_path / "a"), a)
    pb = corroboration.write(str(tmp_path / "b"), b)
    assert [os.path.basename(p) for p in pa] == [os.path.basename(p) for p in pb]
    for x, y in zip(pa, pb):
        assert open(x, "rb").read() == open(y, "rb").read()
    assert CID + ".json" in [os.path.basename(p) for p in pa]
    assert corroboration.file_name("unattributed:rt:2026-10-05T04:00:00Z").count(":") == 0


def test_token_disagreement_is_listed_not_resolved():
    recs = _records()
    gw = _gw_llm(recs)[0]
    recs.append(_ours_for(gw, tin=gw["tokens.in"] + 1))
    doc = corroboration.corroborate(recs)[CID]
    tok = [d for d in doc["disagreements"] if d["kind"] == "tokens"]
    assert len(tok) == 1 and tok[0]["call.id"] == gw["call.id"]
    assert tok[0]["ours"] != tok[0]["gateway"]
    agree = corroboration.corroborate(_records() + [_ours_for(gw)])[CID]
    assert not [d for d in agree["disagreements"] if d["kind"] == "tokens"]


def test_one_sided_call_and_guardrail_link():
    recs = _records()
    gw = _gw_llm(recs)[0]
    block = copy.deepcopy(gw)
    block.update({"record_kind": "platform_decision", "verdict": "DENY", "outcome.real": "BLOCKED_GUARDRAIL",
                  "tokens.in": 0, "tokens.out": 0, "call.id": "act-guard", "record_id": "gw-guard"})
    doc = corroboration.corroborate(recs + [block])[CID]
    g = [x for x in doc["guardrail"] if x["call.id"] == "act-guard"][0]
    assert g["linked_by_action_id"] is False and g["basis"].startswith("inferred")
    assert any(d["kind"] == "guardrail-unlinked" for d in doc["disagreements"])
    mine = _ours_for(block, **{"outcome.finish_reason": "content_filter"})
    doc2 = corroboration.corroborate(recs + [block, mine])[CID]
    g2 = [x for x in doc2["guardrail"] if x["call.id"] == "act-guard"][0]
    assert g2["linked_by_action_id"] is True and g2["ours_finish_reasons"] == ["content_filter"]


def test_invocations_and_retry_surface_as_disagreements():
    doc = corroboration.corroborate(_records())[CID]
    assert doc["invocations"]["retry_suspects"]
    kinds = set(d["kind"] for d in doc["disagreements"])
    assert "retry-suspect" in kinds and "link-gap" in kinds


def test_raw_check_flags_a_tampered_copy():
    recs = _records()
    raw = open(os.path.join(FIX, "gateway-fixture.log")).read()
    inv = open(os.path.join(FIX, "invocations-fixture.jsonl")).read()

    def reader(gw_text):
        return lambda p: {"raw/gateway/g.log": gw_text, "raw/aws-invocations/a.jsonl": inv}.get(p)

    ok = corroboration.corroborate(recs, read_raw=reader(raw))[CID]
    assert ok["raw_check"]["checked"] > 0 and not ok["raw_check"]["mismatches"]
    bad = corroboration.corroborate(recs, read_raw=reader(raw.replace("http.status=200", "http.status=201")))[CID]
    assert any(m["raw"] == "raw/gateway/g.log" and m["raw_available"] for m in bad["raw_check"]["mismatches"])
    assert any(d["kind"] == "raw-mismatch" for d in bad["disagreements"])
    gone = corroboration.corroborate(recs, read_raw=lambda p: None)[CID]
    assert gone["raw_check"]["mismatches"] and not any(m["raw_available"] for m in gone["raw_check"]["mismatches"])


# ---- MON-02 -------------------------------------------------------------------------------------

def _span(call="act-1", run=CID):
    return {"record_kind": "observation", "authorship": "PLATFORM", "observed.clock": "gateway", "call.id": call,
            "run.id": run, "correlation_id": run, "record_id": "span-" + call, "outcome.http_status": 200}


def _block(call="act-1", run=CID, **extra):
    r = {"record_kind": "rail_decision", "verdict": V.RAIL_VERDICTS[1], "tool.name": "lookup", "call.id": call,
         "run.id": run, "correlation_id": run, "record_id": "blk-1", "authorship": "TESTIMONY"}
    r.update(extra)
    return r


def test_mon02_flags_a_blocked_tool_call_that_has_a_span():
    out = mon02.find_mismatches([_block(), _span()])
    assert len(out) == 1 and out[0]["call.id"] == "act-1" and out[0]["span_records"] == ["span-act-1"]
    doc = corroboration.corroborate([_block(), _span()])[CID]
    assert [d for d in doc["disagreements"] if d["kind"] == "mon-02"]


def test_mon02_quiet_without_span_or_for_a_refused_span_and_joins_by_use_id():
    assert mon02.find_mismatches([_block()]) == []
    refused = dict(_span(), **{"outcome.http_status": 403})
    assert mon02.find_mismatches([_block(), refused]) == []
    assert mon02.find_mismatches([_block(call="act-2"), _span()]) == []
    blk = _block(**{"tool.use_id": "u1"})
    blk["call.id"] = None
    after = {"record_kind": "action", "tool.use_id": "u1", "call.id": "act-1", "run.id": CID,
             "correlation_id": CID, "record_id": "after-1", "authorship": "TESTIMONY"}
    out = mon02.find_mismatches([blk, after, _span()])
    assert len(out) == 1 and out[0]["joined_by"] == "tool.use_id"


# ---- kit cross-check ----------------------------------------------------------------------------

def test_gateway_log_is_model_calls_only_and_deduplicated():
    recs = _records()
    llm = _gw_llm(recs)
    dup = copy.deepcopy(llm[0])
    dup["record_id"] = "dup-1"
    log = kit_crosscheck.build_gateway_log(recs + [dup], CID)
    ids = [r["modaas.action_id"] for r in log["records"] if "modaas.action_id" in r]
    assert len(ids) == len(set(ids)) == len(set(r["call.id"] for r in llm))
    assert all(r["protocol"] == "llm" for r in log["records"])


def test_kit_accepts_the_gateway_log_and_agreement_is_checked(tmp_path):
    recs = _records()
    log = kit_crosscheck.build_gateway_log(recs, CID)
    total = sum(r["gen_ai.usage.input_tokens"] + r["gen_ai.usage.output_tokens"] for r in log["records"])
    path = kit_crosscheck.write(str(tmp_path), CID, log)
    assert path.endswith(os.path.join("kit-crosscheck", CID, "gateway-log.json"))
    assert json.load(open(path))["records"]
    results = {}
    for name, limit in (("hi", total + 1000), ("lo", max(total - 1, 0))):
        reg = tmp_path / ("register-%s.yaml" % name)
        reg.write_text('controls:\n  - control_id: "16"\n    name: "x"\n    observation_limit: %d\n' % limit)
        results[name] = kit_crosscheck.run_kit(KIT, os.path.dirname(path), CID, str(reg))
    assert results["hi"]["label"] == "PASS" and results["hi"]["exit_code"] == 0
    assert results["lo"]["label"] == "BREACH" and results["lo"]["exit_code"] == 1
    agree = kit_crosscheck.compare(results["hi"]["label"], V.SATISFIED, CID)
    assert agree["agree"] is True and "flag" not in agree
    dis = kit_crosscheck.compare(results["hi"]["label"], V.BREACHED, CID)
    assert dis["agree"] is False and dis["flag"].startswith("DISAGREEMENT")
    assert dis["kit_as_verdict"] == V.SATISFIED and dis["our_verdict"] == V.BREACHED   # neither overwritten


def test_no_evidence_when_the_run_has_no_model_span(tmp_path):
    log = kit_crosscheck.build_gateway_log(_records(), "ifabric-run-1-000000")
    assert log["records"] == []


def test_modules_have_no_verdict_or_threshold_literals():
    base = os.path.join(os.path.dirname(__file__), "..", "..", "prooflab", "stitch")
    for name in ("corroboration", "kit_crosscheck", "mon02"):
        text = open(os.path.join(base, name + ".py")).read()
        for lit in ('"SATISFIED"', '"BREACHED"', '"INDETERMINATE"'):
            assert lit not in text, (name, lit)

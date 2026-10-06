import hashlib
import json
import os

from prooflab.contract import ids, record as R
from prooflab.store import observations as O

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _gw():
    with open(os.path.join(FIX, "gateway-fixture.log")) as fh:
        return O.normalize_gateway_text(fh.read(), "raw/gateway/gateway-fixture.log")


def test_every_record_validates_and_is_platform_authored_with_raw_refs():
    out = _gw()
    assert out["records"] and not out["rejects"]
    for r in out["records"]:
        assert R.validate_record(r) == []
        assert r["authorship"] == "PLATFORM"
        assert R.OBS_RECORD_ID_RE.match(r["record_id"])
        raw, line, sha = r["source.refs"]
        assert raw.startswith("raw:raw/gateway/") and line.startswith("line:") and len(sha) == 7 + 64
        assert r["record_kind"] in ("platform_decision", "observation", "metric")


def test_source_ref_sha_matches_the_raw_line_and_id_is_deterministic():
    text = open(os.path.join(FIX, "gateway-fixture.log")).read()
    lines = text.splitlines()
    out = O.normalize_gateway_text(text, "raw/gateway/g.log")
    again = O.normalize_gateway_text(text, "raw/gateway/other-name.log")
    assert [r["record_id"] for r in out["records"]] == [r["record_id"] for r in again["records"]]
    for r in out["records"]:
        n = int(r["source.refs"][1].split(":")[1])
        assert r["source.refs"][2] == "sha256:" + hashlib.sha256(lines[n - 1].encode()).hexdigest()
        assert r["record_id"] == R.observation_record_id("gateway", r["source.refs"][2][7:])


def test_kinds_refusals_tokens_and_guardrail_inference():
    recs = _gw()["records"]
    kinds = set(r["record_kind"] for r in recs)
    assert {"platform_decision", "metric", "observation"} <= kinds
    refusals = [r for r in recs if r["outcome.http_status"] in (403, 404, 405, 503)]
    assert refusals and all(r["record_kind"] == "platform_decision" and r["verdict"] == "DENY" for r in refusals)
    assert all(r["run.id"].startswith("unresolved:") for r in refusals)
    mapping = {403: "REFUSED_403", 404: "PAUSED_404", 405: "METHOD_405", 503: "ERROR_5XX"}
    assert all(r["outcome.real"] == mapping[r["outcome.http_status"]] for r in refusals)
    metrics = [r for r in recs if r["record_kind"] == "metric"]
    assert metrics and all(r["measured.source"] == "gateway-figure-of-record" for r in metrics)
    assert all(r["measured.value"] == r["tokens.in"] + r["tokens.out"] for r in metrics)
    g = [r for r in recs if r.get("outcome.real") == "BLOCKED_GUARDRAIL"]
    assert len(g) == 1 and g[0]["run.id"].startswith("ifabric-adv-") and g[0]["ep.id"] == "EP-7"


def test_other_party_runs_are_sightings_only_and_background_is_counted():
    out = _gw()
    ids_seen = set(s["run_id"] for s in out["sightings"])
    assert any(i.startswith("hackathon-helper-") for i in ids_seen) and any(i.startswith("my-agent-") for i in ids_seen)
    rec_runs = set(r["run.id"] for r in out["records"])
    assert not any(i.startswith(("hackathon-helper-", "my-agent-")) for i in rec_runs)
    assert out["background"] >= 1


def test_ledger_smoke_style_ids_never_crash_the_normalizer():
    line = ('[pod/p/c] 2026-10-06T01:00:00.000000001Z 2026-10-06T01:00:00.000000Z\tinfo\trequest gateway=g '
            'http.status=200 protocol=mcp modaas.run_id="ifabric-test-ledger-smoke-1791252169"')
    out = O.normalize_gateway_text(line, "raw/gateway/x.log")
    assert out["records"] == [] and [s["run_id"] for s in out["sightings"]] == ["ifabric-test-ledger-smoke-1791252169"]


def test_invocation_records_carry_cid_session_trace_and_unattributed_pseudo_cid():
    out = O.normalize_invocation_text(open(os.path.join(FIX, "invocations-fixture.jsonl")).read(), "raw/aws-invocations/a.jsonl")
    assert not out["rejects"] and len(out["records"]) == 4
    first = out["records"][0]
    assert first["run.id"] == "ifabric-run-1791300000-a1b2c3" and first["runtime.session_id"].startswith(first["run.id"])
    assert first["trace.id"] == "ab" * 16 and first["aws.request_id"] == "req-0001" and first["observed.clock"] == "aws-cloudtrail"
    last = out["records"][3]
    assert last["run.id"].startswith("unattributed:ifabric_customer-SYNTH:") and last["provenance"] == "UNATTRIBUTED"
    assert ids.is_valid_run_id(last["run.id"])

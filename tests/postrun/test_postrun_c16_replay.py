import hashlib
import json
import os
import subprocess
import sys

import pytest

import conftest as scaffold
from prooflab.adapters.postrun import c16_replay as R
from prooflab.contract import record as rec_mod
from prooflab.evaluators import c16_core

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
N2_CID, N3_CID = "ifabric-test-1791260000-a1b2c3", "ifabric-test-1791260100-d4e5f6"
NOW = "2026-10-06T05:00:00.000Z"


def _text(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


def _calls(name, cid):
    return R.model_call_spans(R.load_rows(_text(name)), cid)


@pytest.fixture(scope="module")
def sha():
    return R.read_core_sha(scaffold.sha_file())


def _run(span_file, pin_file, cid, sha):
    pin, _ = R.load_pin(_text(pin_file))
    calls = _calls(span_file, cid)
    return pin, calls, R.replay(cid, calls, pin, sha, now=NOW, provenance="SYNTHETIC")


def test_one_ep2_decision_per_span_and_all_valid(sha):
    for span_file, pin_file, cid in (("spans_n2_observe_breach.json", "pin_n2_observe.json", N2_CID),
                                     ("spans_n3_enforce_halt.json", "pin_n3_enforce.json", N3_CID)):
        pin, calls, recs = _run(span_file, pin_file, cid, sha)
        assert len(recs) == len(calls) == len(json.loads(_text(span_file))["rows"])
        for r in recs:
            assert rec_mod.validate_record(r) == []
            assert (r["record_kind"], r["ep.id"], r["ep.transport"], r["run.id"]) == ("decision", "EP-2", "pull", cid)
            assert r["inline.bound_basis"] == "actual" and r["observed.clock"] == "gateway"
            assert "outcome.real" in r and r["outcome.real"] is None  # recorded, never executed
        assert [r["call.id"] for r in recs] == [c["action_id"] for c in calls]


def test_evaluator_sha_matches_the_register_file(sha):
    _, _, recs = _run("spans_n3_enforce_halt.json", "pin_n3_enforce.json", N3_CID, sha)
    assert sha == open(scaffold.sha_file()).read().split()[0]
    assert sha == R.loaded_core_sha()
    assert {r["evaluator.sha256"] for r in recs} == {sha}
    assert {r["evaluator.name"] for r in recs} == {c16_core.NAME}


def test_questions_follow_gateway_order_and_actual_tokens(sha):
    pin, calls, recs = _run("spans_n2_observe_breach.json", "pin_n2_observe.json", N2_CID, sha)
    committed = 0
    for c, r in zip(calls, recs):
        bound = c["tokens_in"] + c["tokens_out"]
        assert r["measured.value"] == committed + bound
        assert r["tokens.in"] == c["tokens_in"] and r["tokens.out"] == c["tokens_out"]
        committed += bound
    assert [c["start"] for c in calls] == sorted(c["start"] for c in calls)


def test_n3_enforce_breach_call_is_deny_and_halt(sha):
    pin, calls, recs = _run("spans_n3_enforce_halt.json", "pin_n3_enforce.json", N3_CID, sha)
    cap = dict(pin.caps)[pin.default_tier]
    verdicts = [r["verdict"] for r in recs]
    first = verdicts.index("DENY")
    assert verdicts[:first] == ["ALLOW"] * first and verdicts[first:] == ["DENY"] * (len(verdicts) - first)
    assert recs[first]["measured.value"] > cap >= recs[first - 1]["measured.value"]
    assert recs[first]["inline.action"] == "halt" and recs[first]["inline.mode"] == "enforce"
    assert recs[first]["threshold.value"] == cap and recs[first]["pin.sha256"] == pin.pin_sha256


def test_n2_observe_breach_denies_but_only_the_safety_ceiling_halts(sha):
    pin, calls, recs = _run("spans_n2_observe_breach.json", "pin_n2_observe.json", N2_CID, sha)
    cap = dict(pin.caps)[pin.default_tier]
    denies = [r for r in recs if r["verdict"] == "DENY"]
    assert denies and denies[0]["measured.value"] > cap
    for r in recs:
        over_ceiling = r["measured.value"] > pin.safety_ceiling
        assert r["inline.action"] == ("halt" if over_ceiling else "proceed")
        assert r["inline.limit_applied"] == "safety-ceiling"
        assert (r["verdict"] == "DENY") == (r["measured.value"] > cap)


def test_replay_never_imports_evaluate():
    src = open(R.__file__, encoding="utf-8").read()
    assert "transports" not in src and "import evaluate" not in src


def test_filters_dedupe_and_other_runs():
    rows = R.load_rows(_text("spans_n3_enforce_halt.json"))
    extra = [dict(rows[0]),                                                   # duplicate action id
             dict(rows[1], **{"attributes.listener": "http"}),                # MCP span, not a model call
             dict(rows[2], **{"attributes.modaas.run_id": "ifabric-test-1791269999-ffffff",
                              "attributes.modaas.action_id": "act-other-1"})]  # another run
    assert len(R.model_call_spans(rows + extra, N3_CID)) == len(rows)


def test_alternative_capture_shapes(sha):
    rows = json.loads(_text("spans_n3_enforce_halt.json"))["rows"]
    insights = [[{"field": k, "value": v} for k, v in r.items()] for r in rows]
    nested = [{"attributes": {"listener": "llm", "modaas.run_id": N3_CID, "modaas.action_id": "a%d" % i,
                              "gen_ai.usage.input_tokens": 10, "gen_ai.usage.output_tokens": 5}}
              for i in range(3)]
    jsonl = "\n".join(json.dumps(r) for r in rows)
    base = [c["action_id"] for c in _calls("spans_n3_enforce_halt.json", N3_CID)]
    assert [c["action_id"] for c in R.model_call_spans(R.load_rows(json.dumps(insights)), N3_CID)] == base
    assert [c["action_id"] for c in R.model_call_spans(R.load_rows(jsonl), N3_CID)] == base
    assert [c["tokens_in"] for c in R.model_call_spans(R.load_rows(json.dumps(nested)), N3_CID)] == [10] * 3


def test_unreadable_tokens_fail_closed():
    rows = R.load_rows(_text("spans_n3_enforce_halt.json"))
    rows[3].pop("attributes.gen_ai.usage.output_tokens")
    with pytest.raises(R.ReplayError):
        R.model_call_spans(rows, N3_CID)


def test_pin_sha_mismatch_and_bad_core_sha_file(tmp_path):
    with pytest.raises(R.ReplayError):
        R.load_pin(_text("pin_n3_enforce.json"), "0" * 64)
    bad = tmp_path / "x.sha256"
    bad.write_text("nothex  file\n")
    with pytest.raises(R.ReplayError):
        R.read_core_sha(str(bad))


def test_main_writes_valid_json_lines(tmp_path, sha, capsys):
    pin_text = _text("pin_n3_enforce.json")
    out = tmp_path / "out.jsonl"
    code = R.main(["--cid", N3_CID, "--spans", os.path.join(FIX, "spans_n3_enforce_halt.json"),
                   "--pin", os.path.join(FIX, "pin_n3_enforce.json"),
                   "--pin-sha256", hashlib.sha256(pin_text.encode()).hexdigest(),
                   "--sha-file", scaffold.sha_file(), "--provenance", "SYNTHETIC", "--out", str(out)])
    assert code == 0
    lines = [json.loads(x) for x in out.read_text().splitlines()]
    assert len(lines) == 9 and all(rec_mod.validate_record(r) == [] for r in lines)
    assert len({r["record_id"] for r in lines}) == 9


def test_main_exit_2_on_no_spans_and_bad_cid_data(tmp_path, capsys):
    code = R.main(["--cid", "ifabric-test-1791200000-000000", "--spans", os.path.join(FIX, "spans_n3_enforce_halt.json"),
                   "--pin", os.path.join(FIX, "pin_n3_enforce.json"), "--sha-file", scaffold.sha_file()])
    assert code == 2 and "INDETERMINATE" in capsys.readouterr().err


def test_no_secret_shaped_values_in_records(sha):
    _, _, recs = _run("spans_n2_observe_breach.json", "pin_n2_observe.json", N2_CID, sha)
    assert not any(rec_mod.secret_shaped(json.dumps(r)) for r in recs)

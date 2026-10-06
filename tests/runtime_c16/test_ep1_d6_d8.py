"""D6 (EP-1 decisions carry the call's x-modaas-action-id) and D8 (EP-1 decisions carry the c16 core's
evaluator.sha256), from source and from a built bundle. Plain asserts; the halt path is unchanged (T-C16-01)."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

from adapters.runtime.tally import RunTally
from helpers import (FakeEvent, ROOT, RUN_ID, Rec, make_adapter, model_call, need_real, real_pin, record_mod,
                     use_double, use_real)

CORE_FILE = os.path.join(ROOT, "prooflab", "evaluators", "c16_core.py")


def _file_sha():
    with open(CORE_FILE, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _real_adapter(pin=None):
    rec = Rec()
    ad = model_call.ModelCallAdapter(RUN_ID, pin or real_pin(), tier=None, emit=rec, tally=RunTally(RUN_ID, None),
                                     identity={"actor_id": "ifabric-it"}, model_id="stub-model")
    return ad, rec


def _valid(recs):
    for r in recs:
        assert record_mod.validate_record(r) == [], (r["record_kind"], record_mod.validate_record(r))


# ---- D6: call.id on the decision ------------------------------------------------------------
def test_decision_is_emitted_after_the_call_with_its_action_id():
    with use_double():
        ad, rec = make_adapter()
        ad.on_before_model_call(FakeEvent())
        assert rec.records == []                                    # held: no call.id yet
        ad.capture.observe_headers({"x-modaas-action-id": "act-7"}, 200)
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 5, "outputTokens": 5}))
        assert [r["record_kind"] for r in rec.records] == ["decision", "action"]
        dec, act = rec.records
        assert dec["call.id"] == act["call.id"] == "act-7" and "call.id" not in dec["null_reasons"]
        assert dec["seq.in_stream"] < act["seq.in_stream"] and dec["emitted.at"] <= act["emitted.at"]
        assert dec["ep.transport"] == "evaluate" and dec["inline.action"] == "proceed"


def test_c7_observes_decision_by_action_id():
    from prooflab.evaluators import c7
    with use_double():
        ad, rec = make_adapter()
        for aid in ("act-1", "act-2"):
            ad.on_before_model_call(FakeEvent())
            ad.capture.observe_headers({"x-modaas-action-id": aid}, 200)
            ad.on_after_model_call(FakeEvent(usage={"inputTokens": 5, "outputTokens": 5}))
    obs = c7.observed_events(rec.records)
    assert {"decision:act-1", "decision:act-2", "call:act-1", "call:act-2"} <= set(obs)


def test_held_decision_is_never_dropped():
    class Boom(Exception):
        status_code = 503
    with use_double():
        ad, rec = make_adapter()
        ad.on_before_model_call(FakeEvent())                        # no header on the response
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 5, "outputTokens": 5}))
        ad.on_before_model_call(FakeEvent())
        ad.capture.observe_headers({"x-modaas-action-id": "act-e"}, 503)
        ad.on_after_model_call(FakeEvent(exception=Boom("503")))      # error: decision still emitted, linked
        ad.on_before_model_call(FakeEvent())                        # its after-event never comes ...
        ad.on_before_model_call(FakeEvent())                        # ... flushed at the next check
        decs = rec.of("decision")
        assert len(decs) == 3
        assert decs[0]["call.id"] is None and "x-modaas-action-id" in decs[0]["null_reasons"]["call.id"]
        assert decs[1]["call.id"] == "act-e"
        assert decs[2]["call.id"] is None and "no after-call event" in decs[2]["null_reasons"]["call.id"]


def test_halt_decision_still_emitted_before_any_call():
    """T-C16-01 semantics, byte for byte: the DENY decision and the stop record are out before the model call
    would go out, the call is cancelled, and nothing is held."""
    with use_double():
        ad, rec = make_adapter(cap=100)
        ev = FakeEvent()
        ad.on_before_model_call(ev)
        assert ev.cancel and ad.tally.halted and not ad._held
        assert [(r["record_kind"], r.get("verdict"), r.get("outcome.real")) for r in rec.records][0] == \
            ("decision", "DENY", "CANCELLED_C16")
        assert rec.records[0]["call.id"] is None and rec.records[1]["record_kind"] == "lifecycle"


def test_guarded_check_decision_carries_the_call_id():
    with use_double():
        ad, rec = make_adapter()
        out = ad.guarded_check(lambda: {"text": "SAFE", "finish_reason": "stop", "call_id": "act-g",
                                        "usage": {"inputTokens": 3, "outputTokens": 1}})
        assert out.allowed
        assert [r["record_kind"] for r in rec.records] == ["decision", "action"]
        assert rec.records[0]["call.id"] == "act-g"


# ---- D8: evaluator.sha256 --------------------------------------------------------------------
def test_core_sha256_from_source_is_the_file_sha():
    need_real()
    assert model_call.CORE_SHA256 == _file_sha()


def test_decisions_carry_evaluator_sha256_and_validate():
    need_real()
    with use_real():
        ad, rec = _real_adapter()
        ad.on_before_model_call(FakeEvent())
        ad.capture.observe_headers({"x-modaas-action-id": "act-1"}, 200)
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 60, "outputTokens": 40}))
        ad.on_before_model_call(FakeEvent())                        # no header: call.id null, with its reason
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 1, "outputTokens": 1}))
        ad2, rec2 = _real_adapter(real_pin(cap=100))
        ad2.on_before_model_call(FakeEvent())                       # halt
        decs = rec.of("decision") + rec2.of("decision")
        assert len(decs) == 3 and decs[0]["call.id"] == "act-1"
        assert {d["evaluator.sha256"] for d in decs} == {_file_sha()}
        assert all("evaluator.sha256" not in d["null_reasons"] for d in decs)
        _valid(rec.records + rec2.records)


def test_fail_closed_decision_carries_evaluator_sha256():
    need_real()
    with use_real():
        orig = model_call._core.decide_inline

        def boom(q, pin, sha=None):
            raise RuntimeError("x")
        model_call._core.decide_inline = boom
        try:
            ad, rec = _real_adapter()
            ad.on_before_model_call(FakeEvent())
        finally:
            model_call._core.decide_inline = orig
        dec = rec.of("decision")[0]
        assert dec["inline.action"] == "halt" and dec["evaluator.sha256"] == _file_sha()
        _valid(rec.records)


_PROBE = r"""
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location(sys.argv[2], sys.argv[1])
base = importlib.util.module_from_spec(spec)
sys.modules[sys.argv[2]] = base
spec.loader.exec_module(base)
from adapters.runtime import model_call as m
print(json.dumps({"core": m.CORE_SHA256, "base": base.EVALUATOR_SHA256, "record": m._record is None,
                  "loader": type(m._core.__loader__).__name__}))
"""


def test_bundle_core_sha256_equals_the_base_marker():
    """From a built two-stage bundle, in a clean interpreter (no repo on sys.path): model_call's CORE_SHA256 is
    the base file's EVALUATOR_SHA256 and its `# evaluator.sha256=` header marker, and the repo file's sha."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("bundle_agent_d8", os.path.join(ROOT, "tools", "bundle_agent.py"))
    ba = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ba)
    with tempfile.TemporaryDirectory() as tmp:
        reports, _ = ba.bundle_two_stage(["customer"], src_root=ROOT, agents_root=ROOT, out_root=tmp)
        base = [r for r in reports if r["name"] == "ifabric-base"][0]
        assert base["ok"] and base["gzip_base64_chars"] <= ba.GATE_CHARS
        text = open(base["out"]).read()
        marker = re.search(r"^# evaluator\.sha256=([0-9a-f]{64})$", text, re.M).group(1)
        out = subprocess.run([sys.executable, "-I", "-c", _PROBE, base["out"], ba.BASE_MODULE], cwd=tmp,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
        assert out.returncode == 0, out.stderr[-800:]
        got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["loader"] == "_BundleFinder" and got["record"] is True       # served by the bundle, no contract
    assert got["core"] == got["base"] == marker == _file_sha()

"""EP-1 against the REAL PR-02 core and the REAL PR-01 record validator (review fix round)."""
from helpers import (FakeEvent, RUN_ID, Rec, need_real, use_real, real_pin, model_call, record_mod)
from adapters.runtime.tally import RunTally


def _adapter(tier=None, pin=None, **kw):
    pin = pin or real_pin()
    rec = Rec()
    ad = model_call.ModelCallAdapter(RUN_ID, pin, tier=tier, emit=rec, tally=RunTally(RUN_ID, None),
                                     identity={"actor_id": "ifabric-it"}, model_id="stub-model", **kw)
    return ad, rec


def test_tier_none_uses_pin_default_tier():
    need_real()
    with use_real():
        ad, rec = _adapter(tier=None)
        ev = FakeEvent()
        ad.on_before_model_call(ev)
        assert ev.cancel is False and not ad.tally.halted
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 1, "outputTokens": 1}))   # the decision is emitted
        d = rec.of("decision")[0]
        assert d["verdict"] == "ALLOW" and d["threshold.tier"] == "default"
        assert "invalid-question" not in d["reason"]


def test_tier_explicit_wins_over_default():
    need_real()
    with use_real():
        ad, rec = _adapter(tier="A")
        ad.on_before_model_call(FakeEvent())
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 1, "outputTokens": 1}))
        assert rec.of("decision")[0]["threshold.tier"] == "A"


def _check(recs):
    for r in recs:
        errs = record_mod.validate_record(r)
        assert errs == [], (r["record_kind"], errs)


def test_every_emitted_record_kind_validates():
    need_real()
    with use_real():
        ad, rec = _adapter()
        ad.on_before_model_call(FakeEvent())
        ad.capture.observe_headers({"x-modaas-action-id": "act-1"}, 200)
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 60, "outputTokens": 40}))
        ad.on_before_model_call(FakeEvent())
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 0, "outputTokens": 0}))   # unknown usage
        ad.on_before_model_call(FakeEvent())
        ad.on_after_model_call(FakeEvent(exception=RuntimeError("boom")))                # error action
        rec_halt = Rec()
        ad2 = model_call.ModelCallAdapter(RUN_ID, real_pin(cap=100), emit=rec_halt,
                                          tally=RunTally(RUN_ID, None))
        ad2.on_before_model_call(FakeEvent())     # halt: decision + lifecycle
        ad2.on_before_model_call(FakeEvent())     # stopped-refusal lifecycle
        recs = rec.records + rec_halt.records
        assert {r["record_kind"] for r in recs} == {"decision", "action", "lifecycle"}
        _check(recs)


def test_evaluator_error_records_validate():
    need_real()
    with use_real():
        orig = model_call._core.decide_inline

        def boom(q, pin):
            raise RuntimeError("x")
        model_call._core.decide_inline = boom
        try:
            rec = Rec()
            ad = model_call.ModelCallAdapter(RUN_ID, real_pin(), emit=rec, tally=RunTally(RUN_ID, None))
            ev = FakeEvent()
            ad.on_before_model_call(ev)
        finally:
            model_call._core.decide_inline = orig
        assert ev.cancel and rec.records
        _check(rec.records)


def test_guarded_check_records_validate():
    need_real()
    with use_real():
        ad, rec = _adapter()
        out = ad.guarded_check(lambda: {"text": "SAFE", "finish_reason": "stop", "call_id": "act-9",
                                        "usage": {"inputTokens": 10, "outputTokens": 1}})
        assert out.allowed and rec.records
        _check(rec.records)

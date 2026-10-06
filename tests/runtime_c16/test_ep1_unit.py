"""EP-1 unit tests with fake events (no Strands needed). Plain asserts; no fixtures."""
import os
import re
import threading

from helpers import (FakeEvent, ROOT, Rec, make_adapter, use_double, c16_double, model_call)
from adapters.runtime.hooks import Dispatcher, StageResult


def test_usage_from_metadata_commits_and_records():
    with use_double():
        ad, rec = make_adapter()
        ev = FakeEvent()
        ad.on_before_model_call(ev)
        assert ev.cancel is False and ad.tally.reserved == 250       # fallback 200 + max_tokens 50
        ad.capture.observe_headers({"x-modaas-action-id": "act-1"}, 200)
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 60, "outputTokens": 40, "totalTokens": 100}))
        t = ad.tally
        assert (t.committed, t.reserved, t.calls) == (100, 0, 1)
        act = rec.of("action")[0]
        assert act["call.id"] == "act-1" and act["tokens.in"] == 60 and act["tokens.out"] == 40
        assert act["outcome.real"] == "SERVED" and act["inline.max_retries"] == 0
        assert [r["record_kind"] for r in rec.records] == ["decision", "action"]


def test_zero_usage_is_unknown_not_zero():
    with use_double():
        ad, rec = make_adapter()
        ad.on_before_model_call(FakeEvent())
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 0, "outputTokens": 0}))
        assert ad.tally.committed == 0 and ad.tally.unknown_calls == 1
        act = rec.of("action")[0]
        assert act["usage.unknown"] is True and act["tokens.in"] is None
        assert "tokens.in" in act["null_reasons"]


def test_halt_cancels_and_records_stop_then_no_further_check_passes():
    with use_double():
        ad, rec = make_adapter(cap=100)             # bound 250 alone is over the cap
        ev = FakeEvent()
        ad.on_before_model_call(ev)
        assert ev.cancel and ad.tally.halted and ad.tally.reserved == 0
        assert ad.tally.result_fields()["disposition"] == {"action": "escalate", "reason": "c16-budget-halt"}
        kinds = rec.kinds()
        assert ("decision", "DENY", "CANCELLED_C16") in kinds
        assert any(r["record_kind"] == "lifecycle" and r.get("lifecycle.event") == "c16-stop" for r in rec.records)
        dec = rec.of("decision")[0]
        assert dec["inline.action"] == "halt" and dec["call.id"] is None and "call.id" in dec["null_reasons"]
        # own-cancel: the after event of our cancel is NOT a served 0-token call
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 0, "outputTokens": 0}))
        assert ad.tally.calls == 0 and ad.tally.unknown_calls == 0 and not rec.of("action")
        # stop-state: the next call is refused before C16, tally untouched, no new decision
        n_dec = len(rec.of("decision"))
        ev2 = FakeEvent()
        ad.on_before_model_call(ev2)
        assert ev2.cancel and len(rec.of("decision")) == n_dec and ad.tally.reserved == 0


def test_observe_mode_records_deny_and_serves():
    with use_double():
        ad, rec = make_adapter(cap=100, mode="observe", ceiling=100000)
        ev = FakeEvent()
        ad.on_before_model_call(ev)
        assert ev.cancel is False and ad.tally.reserved == 250 and not ad.tally.halted
        d = rec.of("decision")[0]
        assert d["verdict"] == "DENY" and d["inline.action"] == "proceed" and d["outcome.real"] == "SERVED"
        assert d["inline.mode"] == "observe" and d["inline.limit_applied"] == "safety-ceiling"


def test_observe_mode_safety_ceiling_halts():
    with use_double():
        ad, rec = make_adapter(cap=100, mode="observe", ceiling=200)
        ev = FakeEvent()
        ad.on_before_model_call(ev)
        assert ev.cancel and ad.tally.halted


def test_retry_reentry_does_not_leak_reservation():
    with use_double():
        ad, rec = make_adapter()
        class Throttled(Exception):
            status_code = 429
        ad.on_before_model_call(FakeEvent())
        ad.on_after_model_call(FakeEvent(exception=Throttled("429")))      # Strands retries: Before fires again
        assert ad.tally.reserved == 0 and ad.tally.committed == 0 and ad.tally.calls == 0
        ad.on_before_model_call(FakeEvent())
        assert ad.tally.reserved == 250
        ad.on_after_model_call(FakeEvent(usage={"inputTokens": 10, "outputTokens": 5}))
        assert (ad.tally.committed, ad.tally.reserved, ad.tally.calls) == (15, 0, 1)
        assert len(rec.of("decision")) == 2                                  # one decision per attempt
        outs = [r["outcome.real"] for r in rec.of("action")]
        assert outs == ["ERROR", "SERVED"]
        assert rec.of("action")[0]["outcome.http_status"] == 429


def test_evaluator_error_fails_closed():
    with use_double():
        ad, rec = make_adapter(boom=True)
        ev = FakeEvent()
        ad.on_before_model_call(ev)
        assert ev.cancel and ad.tally.halted
        d = rec.of("decision")[0]
        assert d["verdict"] == "DENY" and d["inline.action"] == "halt" and "evaluator-error" in d["reason"]


def test_concurrent_callers_cannot_both_pass():
    with use_double():
        ad, rec = make_adapter(cap=300)             # room for exactly one 250 bound
        out = []
        barrier = threading.Barrier(8)

        def run():
            ev = FakeEvent()
            barrier.wait()
            ad.on_before_model_call(ev)
            out.append(bool(ev.cancel))
        ts = [threading.Thread(target=run) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert out.count(False) == 1 and out.count(True) == 7


def test_dispatcher_order_rails_c16_emit_and_rails_block_skips_c16():
    order = []

    def rails(ev, ctx):
        order.append("rails")
        return StageResult(records=[{"record_kind": "judgment", "n": "r"}])

    def c16(ev, ctx):
        order.append("c16")
        return StageResult(records=[{"record_kind": "decision", "n": "c"}])
    seen = []
    d = Dispatcher(emit=lambda r: (order.append("emit"), seen.append(r["n"])), rails=rails, c16=c16)
    d.dispatch("before_model", {})
    assert order == ["rails", "c16", "emit", "emit"] and seen == ["r", "c"]
    order[:] = []
    d2 = Dispatcher(emit=lambda r: order.append("emit"),
                    rails=lambda e, c: {"block": True, "reason": "x", "records": [{"record_kind": "judgment"}]},
                    c16=c16)
    res = d2.dispatch("before_model", {})
    assert res.cancel and "c16" not in order and order == ["emit"]


def test_dispatcher_emit_never_raises_and_rails_error_does_not_stop_c16():
    def boom(r):
        raise RuntimeError("queue full")

    def bad_rails(e, c):
        raise ValueError("rail bug")
    d = Dispatcher(emit=boom, rails=bad_rails, c16=lambda e, c: StageResult(records=[{"k": 1}]))
    res = d.dispatch("before_model", {})
    assert res.cancel is False


def test_rails_block_leaves_tally_unchanged_in_adapter():
    with use_double():
        ad, rec = make_adapter()
        ad.dispatcher.rails = lambda e, c: {"block": True, "cancel_message": "rail says no", "records": []}
        ev = FakeEvent()
        ad.on_before_model_call(ev)
        assert ev.cancel == "rail says no" and ad.tally.reserved == 0 and not rec.of("decision")


# ---- guarded_check (B-G3) ---------------------------------------------------
def _post(text, tin=20, tout=2, finish="stop", calls=None):
    def post():
        if calls is not None:
            calls.append(1)
        return {"text": text, "finish_reason": finish, "call_id": "act-g",
                "usage": {"inputTokens": tin, "outputTokens": tout}}
    return post


def test_guarded_check_allow_counts_tokens_and_records_call_id():
    with use_double():
        ad, rec = make_adapter()
        r = ad.guarded_check(_post("SAFE"))
        assert r.allowed and ad.tally.committed == 22 and ad.tally.reserved == 0
        assert rec.of("action")[0]["call.id"] == "act-g"


def test_guarded_check_blocks_garbage_empty_and_extra_text():
    with use_double():
        for text in ("probably safe", "", None, "SAFE but", "UNSAFE"):
            ad, _ = make_adapter()
            r = ad.guarded_check(_post(text))
            assert r.verdict == "BLOCK" and r.reason == "unparseable", text


def test_guarded_check_content_filter_and_no_usage_block():
    with use_double():
        ad, rec = make_adapter()
        r = ad.guarded_check(_post("", 0, 0, "content_filter"))
        assert r.verdict == "BLOCK" and r.reason == "content-filter"
        assert rec.of("action")[0]["outcome.real"] == "BLOCKED_GUARDRAIL"
        ad2, _ = make_adapter()
        r2 = ad2.guarded_check(_post("SAFE", 0, 0, "stop"))
        assert r2.verdict == "BLOCK" and r2.reason == "no-usage" and ad2.tally.unknown_calls == 1


def test_guarded_check_c16_deny_blocks_without_calling_post():
    with use_double():
        ad, rec = make_adapter(cap=100)
        calls = []
        r = ad.guarded_check(_post("SAFE", calls=calls))
        assert r.verdict == "BLOCK" and r.reason == "c16-deny" and not calls and ad.tally.halted
        r2 = ad.guarded_check(_post("SAFE", calls=calls))
        assert r2.reason == "stopped" and not calls


def test_guarded_check_post_error_blocks_and_releases():
    with use_double():
        ad, _ = make_adapter()

        def post():
            raise OSError("down")
        r = ad.guarded_check(post)
        assert r.verdict == "BLOCK" and r.reason == "post-error" and ad.tally.reserved == 0


# ---- structural rules --------------------------------------------------------
def _runtime_sources():
    d = os.path.join(ROOT, "adapters", "runtime")
    for n in sorted(os.listdir(d)):
        if n.endswith(".py"):
            with open(os.path.join(d, n)) as f:
                yield n, f.read()


def test_only_model_call_imports_the_evaluator():
    for name, src in _runtime_sources():
        if name == "model_call.py":
            continue
        assert "c16_core" not in src and "decide_inline" not in src, name
        assert not re.search(r"^\s*(from|import)\s+\S*\bevaluate\b", src, re.M), name


def test_no_token_vs_limit_comparison_in_adapters():
    pat = re.compile(r"(cap|limit|ceiling|threshold)\w*\s*(<=|>=|<|>)|(<=|>=|<|>)\s*\w*(cap|limit|ceiling|threshold)")
    for name, src in _runtime_sources():
        for ln in src.splitlines():
            code = ln.split("#")[0]
            assert not pat.search(code), (name, ln)

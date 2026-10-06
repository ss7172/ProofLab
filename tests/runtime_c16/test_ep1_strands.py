"""T-C16-01 and friends against the REAL pinned Strands loop with a stub OpenAI-compatible
gateway (httpx.MockTransport). Skipped where Strands is not importable."""
from helpers import (HAVE_STRANDS, StubGateway, build_agent, make_adapter, need_strands,
                     text_response, tool_response, use_double, model_call)

if HAVE_STRANDS:
    from strands import tool

    @tool
    def lookup(q: str) -> str:
        """Look something up."""
        return "result for " + q


def test_t_c16_01_halt_stop_record_no_further_model_call():
    need_strands()
    with use_double():
        ad, rec = make_adapter(cap=400)
        gw = StubGateway([tool_response("lookup", '{"q": "x"}', 100, 100)])
        agent = build_agent(ad, gw, tools=[lookup])
        res = agent("go")
        # call 1 served (bound 250 <= 400); call 2: committed 200 + bound > 400 -> halt, no HTTP request
        assert gw.requests == 1
        assert ad.tally.halted and ad.tally.committed == 200 and ad.tally.reserved == 0
        assert ad.tally.result_fields()["disposition"]["reason"] == "c16-budget-halt"
        assert "denied by C16" in str(res)
        kinds = rec.kinds()
        assert kinds[0] == ("decision", "ALLOW", None)
        assert ("decision", "DENY", "CANCELLED_C16") in kinds
        assert [r["outcome.real"] for r in rec.of("action")] == ["SERVED"]       # the cancelled call has no action
        assert rec.of("action")[0]["call.id"] == "act-0001"                       # from x-modaas-action-id
        assert any(r["detail"].startswith("c16-stop") for r in rec.of("lifecycle"))
        # a further invocation in the same process: refused by stop-state, still no model call
        agent("again")
        assert gw.requests == 1 and ad.tally.committed == 200 and ad.tally.reserved == 0


def test_observe_mode_serves_after_deny_with_real_loop():
    need_strands()
    with use_double():
        ad, rec = make_adapter(cap=400, mode="observe", ceiling=100000)
        gw = StubGateway([tool_response("lookup", '{"q": "x"}', 100, 100), text_response("done", 30, 5)])
        agent = build_agent(ad, gw, tools=[lookup])
        agent("go")
        assert gw.requests == 2 and not ad.tally.halted and ad.tally.committed == 235
        decs = rec.of("decision")
        assert decs[0]["verdict"] == "ALLOW" and decs[1]["verdict"] == "DENY"
        assert decs[1]["inline.action"] == "proceed" and decs[1]["outcome.real"] == "SERVED"
        assert [r["call.id"] for r in rec.of("action")] == ["act-0001", "act-0002"]


def test_finish_reason_passthrough_content_filter_is_blocked_guardrail():
    need_strands()
    with use_double():
        ad, rec = make_adapter(cap=100000)
        gw = StubGateway([text_response("", None, None, finish="content_filter")])
        agent = build_agent(ad, gw)
        agent("hi")
        act = rec.of("action")[0]
        assert act["outcome.finish_reason"] == "content_filter"
        assert act["outcome.real"] == "BLOCKED_GUARDRAIL" and act["tokens.in"] == 0


def test_raw_finish_reason_stop_and_usage_from_metadata_real_loop():
    need_strands()
    with use_double():
        ad, rec = make_adapter(cap=100000)
        gw = StubGateway([text_response("hello", 12, 3, finish="stop")])
        build_agent(ad, gw)("hi")
        act = rec.of("action")[0]
        assert act["outcome.finish_reason"] == "stop" and (act["tokens.in"], act["tokens.out"]) == (12, 3)
        assert ad.tally.committed == 15


def test_one_attempt_per_call_no_hidden_retry_below_the_hook():
    need_strands()
    with use_double():
        ad, rec = make_adapter(cap=100000)
        gw = StubGateway([500, 500, 500])
        agent = build_agent(ad, gw)
        try:
            agent("hi")
        except Exception:
            pass
        assert gw.requests == 1                       # openai max_retries=0: the 500 is not retried
        assert ad.tally.reserved == 0 and ad.tally.committed == 0
        assert rec.of("action")[-1]["outcome.real"] == "ERROR_5XX"


def test_client_is_built_with_max_retries_zero_and_the_hook():
    need_strands()
    import asyncio
    ad, _ = make_adapter()
    gw = StubGateway([])
    model = model_call.make_gateway_model(ad.capture, ad.finish, "m",
                                          client_args={"base_url": "http://x.invalid/v1", "api_key": "k"},
                                          transport=gw.transport())

    async def probe():
        async with model._get_client() as c:
            return c.max_retries, [h.__name__ for h in c._client.event_hooks["response"]]
    mr, hooks = asyncio.run(probe())
    assert mr == 0 and hooks == ["on_response"]

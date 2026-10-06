import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import c16_double  # noqa: E402
from adapters.runtime import model_call  # noqa: E402

try:
    import strands  # noqa: F401
    import httpx
    HAVE_STRANDS = True
except Exception:
    HAVE_STRANDS = False


def need_strands():
    if not HAVE_STRANDS:
        raise unittest.SkipTest("strands stack not importable on this interpreter")


class Rec(object):
    def __init__(self):
        self.records = []

    def __call__(self, r):
        self.records.append(r)

    def kinds(self):
        return [(r["record_kind"], r.get("verdict"), r.get("outcome.real")) for r in self.records]

    def of(self, kind):
        return [r for r in self.records if r["record_kind"] == kind]


class use_double(object):
    """Context manager: model_call._core -> the test double."""
    def __enter__(self):
        self.old = model_call._core
        model_call._core = c16_double
        return self

    def __exit__(self, *a):
        model_call._core = self.old


class FakeEvent(object):
    def __init__(self, projected=None, usage=None, exception=None, text="ok"):
        self.projected_input_tokens = projected
        self.cancel = False
        self.exception = exception
        self.stop_response = None
        if exception is None and usage is not False:
            class _SR(object):
                pass
            sr = _SR()
            sr.message = {"role": "assistant", "content": [{"text": text}],
                          "metadata": {"usage": usage} if usage is not None else {}}
            sr.stop_reason = "end_turn"
            self.stop_response = sr


def make_adapter(run_id="ifabric-test-1", **pin_kw):
    pin = c16_double.PinnedC16(**pin_kw)
    rec = Rec()
    from adapters.runtime.tally import RunTally
    ad = model_call.ModelCallAdapter(run_id, pin, tier="default", emit=rec, tally=RunTally(run_id, "default"),
                                     identity={"actor_id": "ifabric-it"}, model_id="stub-model")
    return ad, rec


def sse(chunks):
    body = "".join("data: %s\n\n" % json.dumps(c) for c in chunks) + "data: [DONE]\n\n"
    return body.encode()


def _base(delta, finish=None):
    return {"id": "c1", "object": "chat.completion.chunk", "created": 1, "model": "stub",
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}


def text_response(text, tin, tout, finish="stop"):
    chunks = [_base({"role": "assistant", "content": text}), _base({}, finish)]
    if tin is not None:
        chunks.append({"id": "c1", "object": "chat.completion.chunk", "created": 1, "model": "stub",
                       "choices": [], "usage": {"prompt_tokens": tin, "completion_tokens": tout,
                                                "total_tokens": tin + tout}})
    return sse(chunks)


def tool_response(name, args, tin, tout):
    call = {"index": 0, "id": "call_1", "type": "function", "function": {"name": name, "arguments": args}}
    return sse([_base({"role": "assistant", "tool_calls": [call]}), _base({}, "tool_calls"),
                {"id": "c1", "object": "chat.completion.chunk", "created": 1, "model": "stub", "choices": [],
                 "usage": {"prompt_tokens": tin, "completion_tokens": tout, "total_tokens": tin + tout}}])


class StubGateway(object):
    """httpx.MockTransport handler: replays queued responses, counts requests."""
    def __init__(self, responses):
        self.responses = list(responses)   # items: bytes (SSE) or int (HTTP status)
        self.requests = 0
        self._n = 0

    def handler(self, request):
        import httpx
        self.requests += 1
        self._n += 1
        item = self.responses.pop(0) if self.responses else text_response("late", 1, 1)
        hdr = {"x-modaas-action-id": "act-%04d" % self._n}
        if isinstance(item, int):
            return httpx.Response(item, headers=hdr, json={"error": {"message": "stub error"}})
        hdr["content-type"] = "text/event-stream"
        return httpx.Response(200, headers=hdr, content=item)

    def transport(self):
        import httpx
        return httpx.MockTransport(self.handler)


def build_agent(adapter, gateway, tools=None):
    from strands import Agent
    model = model_call.make_gateway_model(
        adapter.capture, adapter.finish, "stub-model",
        client_args={"base_url": "http://stub.invalid/v1", "api_key": "stub"},
        transport=gateway.transport())
    return Agent(model=model, hooks=[adapter], tools=tools or [], callback_handler=None)

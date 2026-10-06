import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

# Until PR-01/PR-02 are merged, borrow their packages from the sibling worktrees (read-only).
try:
    import prooflab as _pl
    _WT = os.path.dirname(ROOT)
    for _sib in ("PR-02-c16core", "PR-01-contracts"):
        _d = os.path.join(_WT, _sib, "prooflab")
        if os.path.isdir(_d) and _d not in _pl.__path__:
            _pl.__path__.append(_d)
except Exception:  # pragma: no cover
    pass
try:
    from prooflab.contract import record as record_mod
    from prooflab.evaluators import c16_core as real_core
    HAVE_REAL = True
except Exception:
    record_mod = real_core = None
    HAVE_REAL = False

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


RUN_ID = "ifabric-test-1790000000-a1b2c3"


def need_real():
    if not HAVE_REAL:
        raise unittest.SkipTest("PR-01/PR-02 packages not importable")


def make_adapter(run_id=RUN_ID, **pin_kw):
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


class use_real(object):
    """Context manager: model_call._core -> the real PR-02 core."""
    def __enter__(self):
        self.old = model_call._core
        model_call._core = real_core
        return self

    def __exit__(self, *a):
        model_call._core = self.old


def real_pin(mode="enforce", cap=400):
    return real_core.PinnedC16(
        caps=(("A", cap), ("default", cap)), default_tier="default", safety_ceiling=100000, mode=mode,
        inline_modes=("enforce", "observe"), inline_bound_margin_pct=0, inline_bound_fallback_tokens=200,
        max_tokens=50, threshold_version="C16-v1", register_version="v1", register_sha256="r" * 8,
        pin_sha256="a" * 64)

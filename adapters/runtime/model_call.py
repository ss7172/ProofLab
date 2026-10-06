"""EP-1 model-call adapter (ARCH 3.1 EP-1, 5.1; plan T3.1, B-G2, B-G3).

THE ONLY MODULE THAT CALLS THE C16 EVALUATOR. It sums usage into the tally,
takes the bound from the core's `bound_for`, asks the core (through
`_evaluate`, fail closed) and then acts ONLY on `d.action`: "halt" cancels the
call and stops the agent's model calls, "proceed" reserves the bound. It
compares nothing against a limit (E-03).

Stdlib only at import time (Python 3.9 compatible). Strands, openai and httpx
are imported lazily inside `make_gateway_model` and `register_hooks`, which
run on the agent's 3.12 stack.

Coupling to the contract is one site: `_core` (prooflab.evaluators.c16_core).
Tests may replace `model_call._core` with a double.
"""
import datetime
import threading
import uuid

try:  # the one import site of the shared core
    from prooflab.evaluators import c16_core as _core
except ImportError:  # pragma: no cover - PR-02 not merged yet
    _core = None

try:  # the other import site of the shared contract (PR-01): the record builder
    from prooflab.contract import record as _record
except ImportError:  # pragma: no cover - PR-01 not merged yet
    _record = None

from adapters.runtime import tally as _tally_mod
from adapters.runtime.action_id import ActionIdCapture
from adapters.runtime.hooks import Dispatcher, StageResult

EMITTER = "adapters.runtime.model_call@1.0"
CANCEL_MESSAGE = "model call denied by C16 (token budget)"
STOPPED_MESSAGE = "model call refused: the agent has stopped (C16 budget halt)"
_NULL_REASON = "not applicable: model call"

# Fallback used only when prooflab.contract.record is not importable (PR-01 not merged);
# mirrors record.new_record for the fields the adapter emits.
_FALLBACK_TABLE_A = (
    "call.id", "trace.id", "handoff.id", "handoff.from", "handoff.to", "handoff.payload_sha256",
    "handoff.data_classification", "control.ref", "control.id", "threshold.version", "threshold.value",
    "threshold.sha256", "threshold.tier", "register.version", "pin.sha256", "measured.value",
    "measured.unit", "measured.source", "reason", "outcome.platform_decision", "outcome.real",
    "evaluator.name", "evaluator.sha256", "inline.mode", "inline.limit_applied", "inline.limit_value",
    "inline.action", "inline.bound_basis", "actor.id", "actor.runtime_id", "actor.version",
    "on_behalf_of", "principal.platform", "ep.id", "ep.kind", "ep.transport", "ep.responsible",
    "control.owner")


def _new_record(kind, null_reason, fields):
    if _record is not None:
        return _record.new_record(kind, null_reason=null_reason, **fields)
    rec = dict(fields)
    rec["schema"] = "ifabric.evidence/1"
    rec["record_kind"] = kind
    rec.setdefault("phase", "ifabric." + kind)
    rec.setdefault("correlation_id", rec.get("run.id"))
    rec.setdefault("ts", rec.get("emitted.at"))
    rec.setdefault("source.refs", [])
    reasons = dict(rec.get("null_reasons") or {})
    for name in _FALLBACK_TABLE_A:
        rec.setdefault(name, None)
        if rec[name] is None and name not in reasons:
            reasons[name] = null_reason
    rec["null_reasons"] = reasons
    return rec


def _sha_or_none(v):
    return v if isinstance(v, str) and len(v) == 64 else None




class FinishCapture(object):
    """The raw finish_reason, captured below Strands (which maps
    content_filter to end_turn, 05 AR-12)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.last = None

    def record(self, value):
        with self._lock:
            self.last = value

    def take(self):
        with self._lock:
            v = self.last
            self.last = None
            return v


class GuardedResult(object):
    def __init__(self, verdict, reason, text=None):
        self.verdict = verdict      # "ALLOW" | "BLOCK"
        self.reason = reason
        self.text = text

    @property
    def allowed(self):
        return self.verdict == "ALLOW"


def parse_safe(text):
    """Fail-closed parse of an I-04 self-check answer: an exact SAFE allows;
    anything else (garbage, empty, extra text) blocks."""
    if text is not None and text.strip() == "SAFE":
        return "ALLOW"
    return "BLOCK"


def _now():
    d = datetime.datetime.now(datetime.timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (d.microsecond // 1000)


def _failclosed_decision(pin, exc):
    class _D(object):
        pass
    d = _D()
    d.control_ref = "C16"
    d.control_id = "ACN-COST-001"
    d.verdict = "DENY"
    d.reason = "evaluator-error: %s" % type(exc).__name__
    d.measured_value = None
    d.threshold_value = None
    d.tier = None
    d.mode = getattr(pin, "mode", None)
    d.limit_applied = None
    d.limit_value = None
    d.action = "halt"
    d.bound_basis = None
    d.threshold_version = None
    d.register_version = getattr(pin, "register_version", None)
    d.threshold_sha256 = None
    d.pin_sha256 = getattr(pin, "pin_sha256", None)
    d.evaluator_name = "prooflab.evaluators.c16_core"
    d.evaluator_sha256 = None
    return d


def _evaluate(q, pin):
    """evaluate(): pure delegation to the core. An exception becomes a DENY /
    halt (fail closed, decided here, never by the callers)."""
    try:
        return _core.decide_inline(q, pin)
    except Exception as exc:
        return _failclosed_decision(pin, exc)


class ModelCallAdapter(object):
    def __init__(self, run_id, pin, tier=None, tally=None, emit=None, rails=None,
                 identity=None, capture=None, finish=None, model_id=None,
                 max_retries=0, bound_projection=True):
        self.run_id = run_id
        self.pin = pin
        self.tier = tier
        self.tally = tally if tally is not None else _tally_mod.get_tally(run_id, tier)
        self.identity = dict(identity or {})
        self.capture = capture if capture is not None else ActionIdCapture()
        self.finish = finish if finish is not None else FinishCapture()
        self.model_id = model_id
        self.max_retries = max_retries          # recorded: one model attempt per call
        self.bound_projection = bound_projection
        self.emit = emit
        self._key = None
        self._n = 0
        self._klock = threading.Lock()
        self.dispatcher = Dispatcher(
            emit=emit, rails=rails, c16=self._stage, stopped=lambda: self.tally.halted)

    # -- records (built through PR-01 new_record; every table-A null has a reason) --
    def _mk(self, kind, detail, fields, reasons=None):
        ident = self.identity
        now = _now()
        rid = "%s-ep1-%s" % (
            now.replace("-", "").replace(":", "").replace(".", ""), uuid.uuid4().hex[:8])
        f = {
            "record_id": rid, "detail": detail, "run.id": self.run_id,
            "run.condition": ident.get("run_condition", "none"),
            "trace.id": ident.get("trace_id"),
            "seq.in_stream": self.tally.next_seq(),
            "actor.id": ident.get("actor_id"), "actor.runtime_id": ident.get("actor_runtime_id"),
            "actor.version": ident.get("actor_version"), "on_behalf_of": ident.get("on_behalf_of"),
            "ep.id": "EP-1", "ep.kind": "model gateway (in-process interceptor)",
            "ep.transport": "evaluate" if kind == "decision" else "emit",
            "ep.responsible": "team iFabric (Sree)", "control.owner": "Sree",
            "emitted.at": now, "emitted.clock": "agent-runtime", "ts": now,
            "provenance": ident.get("provenance", "LIVE_SUBJECT"),
            "authorship": "TESTIMONY", "source.refs": list(ident.get("source_refs", [])),
            "emitter": ident.get("emitter", EMITTER),
            "control.ref": "C16", "control.id": "ACN-COST-001", "verdict": "RECORDED",
        }
        f.update(fields)
        why = dict(reasons or {})
        for k in ("actor.runtime_id", "actor.version", "on_behalf_of", "trace.id"):
            why.setdefault(k, "not supplied to the adapter by the runtime")
        f["null_reasons"] = dict((k, v) for k, v in why.items() if f.get(k) is None)
        return _new_record(kind, _NULL_REASON, f)

    def _decision_record(self, d, q, outcome_real):
        tot = (q.committed_tokens + q.reserved_tokens + q.bound_tokens) if q else None
        detail = "C16 inline %s (%s): %s [committed=%s reserved=%s bound=%s max_retries=%d]" % (
            d.verdict, d.action, d.reason, q.committed_tokens if q else None,
            q.reserved_tokens if q else None, q.bound_tokens if q else None, self.max_retries)
        fields = {
            "control.ref": getattr(d, "control_ref", "C16"),
            "control.id": getattr(d, "control_id", "ACN-COST-001"),
            "threshold.version": getattr(d, "threshold_version", None),
            "threshold.value": getattr(d, "threshold_value", None),
            "threshold.sha256": _sha_or_none(getattr(d, "threshold_sha256", None)),
            "threshold.tier": getattr(d, "tier", None),
            "register.version": getattr(d, "register_version", None),
            "pin.sha256": _sha_or_none(getattr(d, "pin_sha256", None)),
            "measured.value": getattr(d, "measured_value", None) if getattr(d, "measured_value", None) is not None else tot,
            "measured.unit": "tokens", "measured.source": "adapter-tally",
            "verdict": d.verdict, "reason": d.reason,
            "evaluator.name": getattr(d, "evaluator_name", None),
            "evaluator.sha256": _sha_or_none(getattr(d, "evaluator_sha256", None)),
            "inline.mode": d.mode, "inline.limit_applied": d.limit_applied,
            "inline.limit_value": d.limit_value, "inline.action": d.action,
            "inline.bound_basis": getattr(d, "bound_basis", None),
            "outcome.real": outcome_real,
        }
        why = {"call.id": "no call dispatched yet" if outcome_real is None else
               "no call was dispatched (refused)" if outcome_real == "CANCELLED_C16" else
               "see the action record of this call",
               "principal.platform": "no gateway request was made",
               "outcome.real": "call dispatched; outcome is on the action record",
               "outcome.platform_decision": "no gateway request was made",
               "evaluator.sha256": "the core's build hash was not supplied to the adapter",
               "threshold.sha256": "the evaluator returned no register hash",
               "pin.sha256": "the pin carries no hash (unpinned)"}
        return self._mk("decision", detail, fields, why)

    def _lifecycle(self, what, detail, extra=None):
        extra = dict(extra or {})
        reason = extra.pop("reason", what)
        disp = extra.pop("disposition", None)
        text = "%s: %s" % (what, detail) + (" [disposition=%s]" % disp if disp else "")
        fields = {"reason": reason}
        fields.update(extra)
        return self._mk("lifecycle", text, fields, {
            "principal.platform": "no gateway request was made",
            "outcome.platform_decision": "no gateway request was made"})

    def _action_record(self, call_id, tokens_in, tokens_out, unknown, finish, outcome, status=None):
        detail = "model call: %s%s [max_retries=%d]" % (
            outcome, " (usage unknown: 0/0 on a served call)" if unknown else "", self.max_retries)
        fields = {
            "call.id": call_id, "model.id": self.model_id,
            "tokens.in": None if unknown else tokens_in,
            "tokens.out": None if unknown else tokens_out,
            "outcome.finish_reason": finish, "outcome.http_status": status, "outcome.real": outcome,
        }
        why = {"call.id": "the response carried no x-modaas-action-id header",
               "tokens.in": "usage reported 0/0 on a served call: UNKNOWN",
               "tokens.out": "usage reported 0/0 on a served call: UNKNOWN",
               "outcome.http_status": "not captured",
               "outcome.finish_reason": "not captured",
               "model.id": "not supplied to the adapter",
               "reason": "an action record carries no decision reason"}
        return self._mk("action", detail, fields, why)

    # -- the C16 stage (B-G3 order: stop-state -> evaluate -> reserve) ----------
    def _check(self, purpose, projected, key):
        """Returns (StageResult, decision-or-None). Holds the tally lock across
        read -> evaluate -> reserve so concurrent callers cannot both pass."""
        t = self.tally
        with t.lock:
            if t.halted:
                rec = self._lifecycle("stopped-refusal", "model call refused: the agent has stopped",
                                      {"reason": "stopped", "inline.purpose": purpose})
                return StageResult(cancel=True, message=STOPPED_MESSAGE, reason="stopped",
                                   records=[rec], source="stop-state"), None
            self.capture.begin()
            self.finish.take()
            bound, basis = _core.bound_for(
                projected, t.last_input, t.last_output, t.tool_result_tokens, self.pin)
            tier = self.tier or t.tier or getattr(self.pin, "default_tier", None)
            q = _core.C16Question(
                run_id=self.run_id, tier=tier,
                committed_tokens=t.committed, reserved_tokens=t.reserved,
                bound_tokens=bound, bound_basis=basis)
            d = _evaluate(q, self.pin)
            if d.action == "halt":
                t.mark_halt("c16-budget-halt")
                recs = [self._decision_record(d, q, "CANCELLED_C16"),
                        self._lifecycle("c16-stop", "C16 halt: the agent makes no more model calls",
                                        {"reason": "c16-budget-halt", "disposition": "escalate"})]
                return StageResult(cancel=True, message=CANCEL_MESSAGE, reason="c16-deny",
                                   records=recs, source="c16"), d
            t.reserve(key, bound)               # the adapter compares nothing
            served = "SERVED" if d.verdict == "DENY" else None   # observe: DENY recorded, call served
            return StageResult(records=[self._decision_record(d, q, served)], source="c16"), d

    def _stage(self, event_name, ctx):
        if event_name == "before_model":
            with self._klock:
                self._n += 1
                key = "call-%d" % self._n
                self._key = key         # after-call reads it: calls inside one agent are sequential
            try:
                res, _ = self._check("model-call", ctx.get("projected"), key)
            except Exception as exc:            # adapter bug: fail closed, recorded
                self.tally.mark_halt("c16-budget-halt")
                rec = self._lifecycle("adapter-error", "EP-1 adapter error: %s" % type(exc).__name__,
                                      {"reason": "adapter-error"})
                return StageResult(cancel=True, message=CANCEL_MESSAGE, reason="adapter-error",
                                   records=[rec], source="c16")
            return res
        if event_name == "after_model":
            return self._after(ctx)
        return None

    # -- after a model call (commit + action record) ----------------------------
    def _after(self, ctx):
        t = self.tally
        key = self._key
        if t.consume_own_cancel():
            t.release(key)          # our own cancel looks like a served 0-token call: not one
            return None
        exc = ctx.get("exception")
        call_id = self.capture.take()
        finish = self.finish.take()
        if exc is not None:
            t.release(key)
            status = getattr(exc, "status_code", None)
            outcome = "ERROR_5XX" if status in range(500, 600) else "ERROR"
            return StageResult(records=[self._action_record(call_id, None, None, True, finish,
                                                            outcome, status)], source="c16")
        usage = ctx.get("usage") or {}
        tin = usage.get("inputTokens")
        tout = usage.get("outputTokens")
        zero = not tin and not tout
        blocked = zero and finish == "content_filter"
        unknown = zero and not blocked
        if blocked:
            t.commit(key, 0, 0)
            outcome = "BLOCKED_GUARDRAIL"
        else:
            t.commit(key, tin, tout, unknown=unknown)
            outcome = "SERVED"
        return StageResult(records=[self._action_record(
            call_id, tin or 0, tout or 0, unknown, finish, outcome, 200)], source="c16")

    # -- Strands hook callbacks ---------------------------------------------------
    def on_before_model_call(self, event):
        self.tally.consume_own_cancel()
        res = self.dispatcher.dispatch("before_model", {
            "projected": getattr(event, "projected_input_tokens", None), "event": event})
        if res.cancel:
            self.tally.flag_own_cancel()
            event.cancel = res.message or CANCEL_MESSAGE
        return res

    def on_after_model_call(self, event):
        usage = None
        sr = getattr(event, "stop_response", None)
        if sr is not None:
            usage = (sr.message.get("metadata") or {}).get("usage")
        return self.dispatcher.dispatch("after_model", {
            "usage": usage, "exception": getattr(event, "exception", None), "event": event})

    def register_hooks(self, registry, **kwargs):
        from strands.hooks import AfterModelCallEvent, BeforeModelCallEvent
        registry.add_callback(BeforeModelCallEvent, self.on_before_model_call)
        registry.add_callback(AfterModelCallEvent, self.on_after_model_call)

    # -- B-G3: the guarded path for the I-04 self-check ---------------------------
    def guarded_check(self, post, parse=parse_safe, purpose="i04-self-check"):
        """stop-state -> C16 evaluate -> reserve -> POST -> commit -> action
        record -> fail-closed parse. `post()` returns a dict
        {text, finish_reason, usage: {inputTokens, outputTokens}, call_id}
        and must make ONE attempt (max_retries=0). Returns a GuardedResult;
        every refusal is a BLOCK."""
        with self._klock:
            self._n += 1
            key = "guard-%d" % self._n
        res, _ = self._check(purpose, None, key)
        if res.cancel:
            self._emit(res.records)
            return GuardedResult("BLOCK", "stopped" if res.reason == "stopped" else "c16-deny")
        self._emit(res.records)
        try:
            out = post() or {}
        except Exception as exc:
            self.tally.release(key)
            self._emit([self._action_record(None, None, None, True, None, "ERROR",
                                            getattr(exc, "status_code", None))])
            return GuardedResult("BLOCK", "post-error")
        usage = out.get("usage") or {}
        tin, tout = usage.get("inputTokens"), usage.get("outputTokens")
        finish = out.get("finish_reason")
        zero = not tin and not tout
        if zero and finish == "content_filter":
            self.tally.commit(key, 0, 0)
            self._emit([self._action_record(out.get("call_id"), 0, 0, False, finish, "BLOCKED_GUARDRAIL", 200)])
            return GuardedResult("BLOCK", "content-filter")
        self.tally.commit(key, tin, tout, unknown=zero)
        self._emit([self._action_record(out.get("call_id"), tin or 0, tout or 0, zero, finish, "SERVED", 200)])
        if zero:
            return GuardedResult("BLOCK", "no-usage", out.get("text"))
        if parse(out.get("text")) == "ALLOW":
            return GuardedResult("ALLOW", "safe", out.get("text"))
        return GuardedResult("BLOCK", "unparseable", out.get("text"))

    def _emit(self, records):
        for r in records:
            if self.emit is None:
                continue
            try:
                self.emit(r)
            except Exception:
                pass


def make_gateway_model(capture, finish, model_id, client_args=None, params=None,
                       transport=None, timeout_s=600.0):
    """Build the pinned-Strands OpenAI-compatible model with: one attempt per
    call (max_retries=0), the action-id response hook installed per request
    through `_get_client` (the client is created and closed per request), and
    the raw finish_reason captured in `format_chunk`. Lazy imports (3.12)."""
    import contextlib
    import httpx
    import openai
    from strands.models.openai import OpenAIModel

    class GatewayModel(OpenAIModel):
        def format_chunk(self, event, **kwargs):
            try:
                if event.get("chunk_type") == "message_stop":
                    finish.record(event.get("data"))
            except Exception:
                pass
            return super().format_chunk(event, **kwargs)

        @contextlib.asynccontextmanager
        async def _get_client(self):
            args = dict(self._resolve_client_args())
            args["max_retries"] = 0
            args["http_client"] = httpx.AsyncClient(
                event_hooks={"response": [capture.on_response]},
                transport=transport, follow_redirects=True,
                timeout=httpx.Timeout(timeout_s, connect=5.0))
            async with openai.AsyncOpenAI(**args) as client:
                yield client

    kwargs = {"client_args": dict(client_args or {}), "model_id": model_id}
    if params:
        kwargs["params"] = params
    return GatewayModel(**kwargs)

"""Per-event hook dispatcher (guardrails B-G2, design 6.2 order).

For each event, ONE dispatcher runs: rails -> C16 -> emit, in that order.
Rails and C16 are injected callables so the rails PR and the emit PR plug in
without this module importing them. Stdlib only, Python 3.9 compatible.

A stage is `fn(event_name, ctx)` returning None or a StageResult. The
dispatcher never decides anything: it orders the stages, stops at the first
cancel, and emits every record the stages produced. emit never raises into
the agent.
"""


class StageResult(object):
    def __init__(self, cancel=False, message=None, reason=None, records=None, source=None):
        self.cancel = cancel
        self.message = message
        self.reason = reason
        self.records = list(records or [])
        self.source = source


def _norm(res, source):
    if res is None:
        return StageResult(source=source)
    if isinstance(res, StageResult):
        if res.source is None:
            res.source = source
        return res
    if isinstance(res, dict):
        return StageResult(
            cancel=bool(res.get("block") or res.get("cancel")),
            message=res.get("cancel_message") or res.get("message"),
            reason=res.get("reason"),
            records=res.get("records"),
            source=source,
        )
    return StageResult(source=source)


class Dispatcher(object):
    def __init__(self, emit=None, rails=None, c16=None, stopped=None, on_error=None):
        self.emit = emit
        self.rails = rails
        self.c16 = c16
        self.stopped = stopped      # optional: () -> bool; skips rails when the agent already stopped
        self.on_error = on_error
        self.order_log = []         # stage names run, for tests: e.g. ["rails", "c16", "emit"]

    def _emit_all(self, records):
        for r in records:
            self.order_log.append("emit")
            if self.emit is None:
                continue
            try:
                self.emit(r)
            except Exception:
                pass                # emit never raises into the agent

    def dispatch(self, event_name, ctx):
        self.order_log = []
        records = []
        final = StageResult()
        skip_rails = False
        if self.stopped is not None:
            try:
                skip_rails = bool(self.stopped())
            except Exception:
                skip_rails = False
        if self.rails is not None and not skip_rails:
            self.order_log.append("rails")
            try:
                res = _norm(self.rails(event_name, ctx), "rails")
            except Exception as exc:          # a rails bug is not a control decision
                res = StageResult(source="rails")
                if self.on_error is not None:
                    try:
                        self.on_error("rails", exc)
                    except Exception:
                        pass
            records.extend(res.records)
            if res.cancel:
                self._emit_all(records)
                res.records = []
                return res
        if self.c16 is not None:
            self.order_log.append("c16")
            res = _norm(self.c16(event_name, ctx), "c16")
            records.extend(res.records)
            final = res
        self._emit_all(records)
        final.records = []
        return final

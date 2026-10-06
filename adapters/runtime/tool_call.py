"""EP-3 tool-call adapter (ARCH 3.1).  Observes only; it never refuses (that is Cedar's / the rails').

One `action` record before the call and one after it, per actual tool call.  Digests, never
content: arguments are recorded as args_sha256 only.  Python 3.9, stdlib only.
"""
import hashlib
import json

from adapters.runtime import emit_client as ec

EP_ID, EP_KIND = "EP-3", "agent runtime (tool-call adapter)"


def args_sha256(args):
    try:
        raw = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        raw = repr(args)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ARCH 3.1 EP-7 / 4 vocabulary (a subset of PR-01 OUTCOME_REAL); never invent values here.
OUTCOME_VOCAB = ("SERVED", "BLOCKED_GUARDRAIL", "REFUSED_403", "PAUSED_404", "METHOD_405",
                 "CEILING_429", "ERROR_5XX", "CANCELLED_C16")
_STATUS_MAP = {403: "REFUSED_403", 404: "PAUSED_404", 405: "METHOD_405", 429: "CEILING_429"}


def real_outcome(status, error=False):
    """In-vocabulary value, or None (caller records a null_reason) when none fits."""
    if status is None:
        return None if error else "SERVED"
    if 200 <= status < 300:
        return "SERVED"
    if status in _STATUS_MAP:
        return _STATUS_MAP[status]
    if status >= 500:
        return "ERROR_5XX"
    return None


class ToolCallRecorder(object):
    def __init__(self, client, ctx, declared_tools=()):
        self.client, self.ctx = client, ctx
        self.declared = set(declared_tools)

    def _rec(self, phase, name, args, verdict, detail, extra, call_id=None):
        ex = {"tool.name": name, "tool.declared": name in self.declared,
              "tool.args_sha256": args_sha256(args), "tool.phase": phase,
              "run.condition": "none"}
        ex.update(extra)
        ex["call.id"] = call_id                  # in extra: new_record drops the null reason for a value
        reasons = {}
        if call_id is None:
            reasons["call.id"] = "response header x-modaas-action-id not present"
        rec = ec.new_record(self.ctx, "action", EP_ID, EP_KIND, "emit", detail, verdict,
                            control_ref="C7", control_id="AIA-LOG-001", extra=ex,
                            null_reasons=reasons)
        return rec

    def before(self, name, args, tool_use_id=None):
        """Written before the call goes out.  Returns the receipt."""
        rec = self._rec("before", name, args, "RECORDED",
                        "tool call %s starting (declared=%s)" % (name, name in self.declared),
                        {"tool.use_id": tool_use_id})
        return self.client.emit(rec)

    def after(self, name, args, status=None, call_id=None, result=None, error=None,
              suspicious=False, tool_use_id=None):
        """Written after the call: real status, a digest of the result, never its content."""
        out = real_outcome(status, error is not None)
        extra = {"tool.use_id": tool_use_id, "outcome.http_status": status,
                 "outcome.real": out, "tool.result_sha256": args_sha256(result),
                 "suspicious_tool_output": bool(suspicious)}
        detail = "tool call %s finished: %s" % (name, out if out else "outcome unclassified")
        if error is not None:
            detail += " (%s)" % ec.scrub_exception(error, self.client.scrubber)
        rec = self._rec("after", name, args, "RECORDED", detail, extra, call_id=call_id)
        if out is None:
            rec["null_reasons"]["outcome.real"] = (
                "no in-vocabulary outcome for status %r%s (transport error or unmapped 1xx/3xx/4xx)"
                % (status, " with error" if error is not None else ""))
        else:
            ec.set_field(rec, "reason", out)
        return self.client.emit(rec)

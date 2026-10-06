"""EP-4 judgment adapter (ARCH 3.1): the agent's disposition, recorded.  Not an evaluate() call.

Dispositions: auto-resolve (alias "resolve"), gather-evidence, escalate, halted.  The reason is
mandatory; the deciding evidence goes in as record ids and tool-result digests, never content.
"""
from adapters.runtime import emit_client as ec

EP_ID, EP_KIND = "EP-4", "agent judgment (disposition)"
DISPOSITIONS = ("auto-resolve", "gather-evidence", "escalate", "halted")
_ALIAS = {"resolve": "auto-resolve"}


def normalize_disposition(d):
    d = _ALIAS.get(d, d)
    return d if d in DISPOSITIONS else None


def record_judgment(client, ctx, disposition, reason, evidence_ids=(), result_digests=(),
                    reversible_step=None, precedence_rule=None):
    """Emit one judgment record.  Returns the receipt (REJECTED_SCHEMA on bad input)."""
    disp = normalize_disposition(disposition)
    if disp is None or not isinstance(reason, str) or not reason.strip():
        return ec.REJECTED_SCHEMA
    esc = disp == "escalate"
    nr = {}
    if reversible_step is None:
        nr["judgment.reversible_step"] = "none declared"
    if precedence_rule is None:
        nr["judgment.precedence_rule"] = "no precedence rule fired"
    rec = ec.new_record(
        ctx, "judgment", EP_ID, EP_KIND, "emit",
        "disposition %s" % disp, "ESCALATED" if esc else "RECORDED",
        control_ref="ESC" if esc else "C7", control_id=None if esc else "AIA-LOG-001",
        extra={"judgment.disposition": disp, "judgment.evidence_ids": list(evidence_ids),
               "judgment.result_digests": list(result_digests),
               "judgment.reversible_step": reversible_step,
               "judgment.precedence_rule": precedence_rule, "reason": reason,
               "run.condition": "none"},
        null_reasons=dict(nr, **({"control.id": "ESC has no library id here"} if esc else {})))
    return client.emit(rec)


def record_intent(client, ctx, intent):
    """An `intent` record goes before invocation [02 R-P-20]."""
    rec = ec.new_record(ctx, "lifecycle", EP_ID, EP_KIND, "emit",
                        "intent: %s" % intent, "RECORDED", control_ref="C7",
                        control_id="AIA-LOG-001",
                        extra={"lifecycle.event": "intent", "reason": "intent"})
    return client.emit(rec)

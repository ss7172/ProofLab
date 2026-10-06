"""EP-4 judgment adapter (ARCH 3.1): the agent's disposition, recorded.  Not an evaluate() call.

Dispositions: auto-resolve (alias "resolve"), gather-evidence, escalate, halted.  The reason is
mandatory; the deciding evidence goes in as record ids and tool-result digests, never content.
"""
from adapters.runtime import emit_client as ec
from adapters.runtime.j2 import POSITION_DISPOSITION   # Gateway C position -> disposition (disagree escalates)

EP_ID, EP_KIND = "EP-4", "agent judgment (disposition)"
DISPOSITIONS = ("auto-resolve", "gather-evidence", "escalate", "halted")
_ALIAS = {"resolve": "auto-resolve"}
PROPOSED_MAX = 160


def normalize_disposition(d):
    d = _ALIAS.get(d, d)
    return d if d in DISPOSITIONS else None


def record_judgment(client, ctx, disposition, reason, evidence_ids=(), result_digests=(),
                    reversible_step=None, precedence_rule=None, model_disposition=None, valid=None,
                    reasked=None, evidence_needed=None, proposed_action=None):
    """Emit the judgment record (C7 workflow event `judgment`, RECORDED) and, for escalate, a second judgment
    record, the `escalation` event (ESC, ESCALATED): ARCH 5.2 expects both for an escalate disposition.
    Returns the judgment record's receipt (REJECTED_SCHEMA on bad input or if either record is rejected)."""
    disp = normalize_disposition(disposition)
    if disp is None or not isinstance(reason, str) or not reason.strip():
        return ec.REJECTED_SCHEMA
    j2 = {}
    for k, v in (("judgment.model_disposition", normalize_disposition(model_disposition)),
                 ("judgment.valid", valid), ("judgment.reasked", reasked),
                 ("judgment.evidence_needed", None if evidence_needed is None else list(evidence_needed))):
        if v is not None:
            j2[k] = v
    nr = {}
    if reversible_step is None:
        nr["judgment.reversible_step"] = "none declared"
    if precedence_rule is None:
        nr["judgment.precedence_rule"] = "no precedence rule fired"
    extra = {"judgment.disposition": disp, "judgment.evidence_ids": list(evidence_ids),
             "judgment.result_digests": list(result_digests),
             "judgment.reversible_step": reversible_step,
             "judgment.precedence_rule": precedence_rule, "reason": reason,
             "run.condition": "none", **j2}
    detail = "disposition=%s" % disp   # the key=value form score-run.py reads (kit grader parity)
    if proposed_action:   # the agent's proposed action, folded into detail (bounded, one line)
        detail += "; proposed: " + " ".join(str(proposed_action).split())[:PROPOSED_MAX]
    receipt = client.emit(ec.new_record(ctx, "judgment", EP_ID, EP_KIND, "emit", detail, "RECORDED",
                                        control_ref="C7", control_id="AIA-LOG-001", extra=extra,
                                        null_reasons=nr))
    if disp == "escalate":
        esc = client.emit(ec.new_record(
            ctx, "judgment", EP_ID, EP_KIND, "emit", "escalation: " + detail, "ESCALATED",
            control_ref="ESC", control_id="AGENT-ESCALATION", extra=dict(extra, phase="ifabric.escalation"),
            null_reasons=nr))
        if esc == ec.REJECTED_SCHEMA:
            return esc
    return receipt


def record_from_j2(client, ctx, fields, result_digests=()):
    """The J2 Judgment (adapters/runtime/j2.py to_record_fields(), after the output rails) onto the record's
    judgment.* contract names: disposition, deciding_evidence -> evidence_ids, named_evidence_needed ->
    evidence_needed, valid, reasked, model_disposition, precedence_rule, reversible_step; proposed_action into
    detail. Empty strings become null with a reason."""
    f = fields or {}
    return record_judgment(
        client, ctx, f.get("disposition"), f.get("reason") or f.get("precedence_rule") or "no reason given",
        evidence_ids=f.get("deciding_evidence") or (), result_digests=result_digests,
        reversible_step=f.get("reversible_step") or None, precedence_rule=f.get("precedence_rule") or None,
        model_disposition=f.get("model_disposition"), valid=f.get("valid"), reasked=f.get("reasked"),
        evidence_needed=f.get("named_evidence_needed"), proposed_action=f.get("proposed_action") or None)


def record_intent(client, ctx, intent):
    """An `intent` record goes before invocation [02 R-P-20]."""
    rec = ec.new_record(ctx, "lifecycle", EP_ID, EP_KIND, "emit",
                        "intent: %s" % intent, "RECORDED", control_ref="C7",
                        control_id="AIA-LOG-001",   # phase = the C7 workflow event `intent` (ARCH 5.2)
                        extra={"lifecycle.event": "intent", "reason": "intent", "phase": "intent"})
    return client.emit(rec)


def record_negotiation(client, ctx, position, fields=None):
    """Gateway C (network -> IT): the IT agent's position on the network's proposal, as a judgment record with
    phase `negotiation` (C7 workflow event; the kit's reference phase) under the run CID and ctx's handoff id.
    The invocation's own J2 judgment (and escalation, if any) follows through record_from_j2, not here."""
    disp = POSITION_DISPOSITION.get(position)
    if disp is None:
        return ec.REJECTED_SCHEMA
    f = fields or {}
    reason = " ".join(str(f.get("reason") or "no reason given").split())[:PROPOSED_MAX]
    nr = {"judgment.reversible_step": "none declared"}
    if not f.get("precedence_rule"):
        nr["judgment.precedence_rule"] = "no precedence rule fired"
    extra = {"phase": "negotiation", "judgment.disposition": disp,
             "judgment.evidence_ids": list(f.get("deciding_evidence") or ()),
             "judgment.result_digests": [], "judgment.reversible_step": None,
             "judgment.precedence_rule": f.get("precedence_rule") or None,
             "reason": "negotiation position %s: %s" % (position, reason), "run.condition": "none"}
    if f.get("named_evidence_needed"):
        extra["judgment.evidence_needed"] = list(f["named_evidence_needed"])
    detail = "negotiation position=%s disposition=%s; %s" % (position, disp, reason)
    return client.emit(ec.new_record(ctx, "judgment", EP_ID, EP_KIND, "emit", detail, "RECORDED",
                                     control_ref="C7", control_id="AIA-LOG-001", extra=extra,
                                     null_reasons=nr))

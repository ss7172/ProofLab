"""The C16 hook shapes PR-03 consumes (ARCH §3.2, §5.1; guardrails §6.2). Stdlib, 3.9.

The decision itself is PR-02's (`prooflab.evaluators.c16_core`: C16Question, Decision, PinnedC16,
bound_for, decide_inline); EP-1 reaches it only through `prooflab.contract.transports.evaluate`.
This module fixes the shapes around it:

  ModelCallEvent      what the BeforeModelCallEvent dispatcher hands the tally / bound computation
  decision_record()   Decision (any object with the §3.2 field names) -> the one `decision` record
  stop_record()       the "stop state, no evaluate()" record for a call cancelled after a halt

The adapter acts ONLY on `decision.action` ("halt" cancels, "proceed" reserves the bound).
"""
from __future__ import annotations

from collections import namedtuple

from prooflab.contract import record as _rec

DECISION_FIELDS = (
    "control_ref", "control_id", "verdict", "reason", "measured_value", "threshold_value", "tier", "mode",
    "limit_applied", "limit_value", "action", "bound_basis", "threshold_version", "register_version",
    "threshold_sha256", "pin_sha256", "evaluator_name", "evaluator_sha256",
)

# One model call about to be made, as the dispatcher sees it (no token arithmetic happens here).
ModelCallEvent = namedtuple("ModelCallEvent", (
    "run_id", "handoff_id", "actor_id", "call_seq", "tier",
    "projected_tokens", "last_input_tokens", "last_output_tokens", "tool_result_tokens",
    "committed_tokens", "reserved_tokens",
))

# decision field -> record field (§4.2 "Control and verdict" group)
_DECISION_TO_RECORD = {
    "control_ref": "control.ref", "control_id": "control.id", "verdict": "verdict", "reason": "reason",
    "measured_value": "measured.value", "threshold_value": "threshold.value", "tier": "threshold.tier",
    "mode": "inline.mode", "limit_applied": "inline.limit_applied", "limit_value": "inline.limit_value",
    "action": "inline.action", "bound_basis": "inline.bound_basis", "threshold_version": "threshold.version",
    "register_version": "register.version", "threshold_sha256": "threshold.sha256", "pin_sha256": "pin.sha256",
    "evaluator_name": "evaluator.name", "evaluator_sha256": "evaluator.sha256",
}


def decision_fields(decision) -> dict:
    """The §3.2 Decision as a plain dict (works for the c16_core dataclass or a dict)."""
    if isinstance(decision, dict):
        return dict((k, decision.get(k)) for k in DECISION_FIELDS)
    return dict((k, getattr(decision, k, None)) for k in DECISION_FIELDS)


def decision_record(decision, ctx: dict) -> dict:
    """A `decision` record for an EP-1 (or EP-2 replay / EP-0) Decision.

    ctx: run.id, handoff.id, actor.*, ep.id ("EP-1"), ep.kind, ep.transport ("evaluate" | "pull"),
    ep.responsible, control.owner, emitted.at + emitted.clock, emitter, provenance, record_id, run.condition,
    trace.id, seq.in_stream, source.refs. measured.unit is "tokens", measured.source "adapter-tally" unless
    ctx says otherwise. outcome.real is CANCELLED_C16 when the action is halt.
    """
    d = decision_fields(decision)
    fields = dict(ctx)
    for key, target in _DECISION_TO_RECORD.items():
        fields[target] = d[key]
    fields.setdefault("measured.unit", "tokens")
    fields.setdefault("measured.source", "adapter-tally")
    fields.setdefault("authorship", "TESTIMONY")
    fields.setdefault("detail", "%s inline %s (%s): %s" % (d["control_ref"], d["verdict"], d["action"], d["reason"]))
    if d["action"] == "halt" and fields.get("ep.id") == "EP-1":
        fields.setdefault("outcome.real", "CANCELLED_C16")
    return _rec.new_record("decision", null_reason="not applicable: C16 decision", **fields)


def stop_record(ctx: dict, reason: str) -> dict:
    """A call cancelled by the stop state (C16-halted or X-05-quarantined): recorded once, no evaluate()."""
    fields = dict(ctx)
    fields.update({"verdict": "RECORDED", "reason": reason, "outcome.real": "CANCELLED_C16",
                   "detail": "model call cancelled: stop state (%s)" % reason})
    fields.setdefault("authorship", "TESTIMONY")
    return _rec.new_record("lifecycle", null_reason="not applicable: stop state", **fields)

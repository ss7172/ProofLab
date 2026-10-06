"""MON-02 (plan M-G1): a tool call our own records say was BLOCKED, yet the gateway holds a span for it. Stdlib, 3.9.

Offline and stateless over one snapshot's records. It writes a mismatch FACT; it never forms a verdict and never
decides which side is right (the corroboration report shows both record ids).
A blocked tool call = a `rail_decision` carrying a BLOCK rail verdict, or a `platform_decision` carrying a DENY
decision, in either case naming a tool (`tool.name`) or a call (`call.id` / `tool.use_id`).
A span = a PLATFORM record from the gateway clock (an observation or a metric, not a refusal) with the same action id.
A block record with no action id of its own is joined through `tool.use_id` to a sibling record that has one.
"""
from __future__ import annotations

from prooflab.contract import verdicts as _v

GATEWAY_CLOCK = "gateway"
BLOCK_VERDICT = _v.RAIL_VERDICTS[1]
DENY_VERDICT = _v.DECISION_VERDICTS[1]


def is_blocked_tool_call(rec: dict) -> bool:
    if not (rec.get("tool.name") or rec.get("tool.use_id")):
        return False
    kind = rec.get("record_kind")
    return ((kind == "rail_decision" and rec.get("verdict") == BLOCK_VERDICT)
            or (kind == "platform_decision" and rec.get("verdict") == DENY_VERDICT))


def is_gateway_span(rec: dict) -> bool:
    if rec.get("authorship") != "PLATFORM" or rec.get("observed.clock") != GATEWAY_CLOCK:
        return False
    if rec.get("record_kind") not in ("observation", "metric"):
        return False
    status = rec.get("outcome.http_status")
    return not (isinstance(status, int) and status >= 400)


def _rid(rec):
    return rec.get("record_id") or "ledger:%s:%s" % (rec.get("correlation_id"), rec.get("seq"))


def find_mismatches(records) -> list:
    """-> sorted list of {run_id, call.id, tool.name, blocked_record, span_records, joined_by}."""
    records = list(records)
    spans = {}
    for rec in records:
        if rec.get("call.id") and is_gateway_span(rec):
            spans.setdefault(rec["call.id"], []).append(rec)
    by_use = {}
    for rec in records:
        if rec.get("tool.use_id") and rec.get("call.id"):
            by_use.setdefault((rec.get("run.id") or rec.get("correlation_id"), rec["tool.use_id"]), set()).add(rec["call.id"])
    out = []
    for rec in records:
        if not is_blocked_tool_call(rec):
            continue
        run = rec.get("run.id") or rec.get("correlation_id")
        cands = []
        if rec.get("call.id"):
            cands.append((rec["call.id"], "call.id"))
        for cid in sorted(by_use.get((run, rec.get("tool.use_id")), ())):
            if cid != rec.get("call.id"):
                cands.append((cid, "tool.use_id"))
        for call, how in cands:
            if call in spans:
                out.append({"run_id": run, "call.id": call, "tool.name": rec.get("tool.name"),
                            "blocked_record": _rid(rec), "joined_by": how,
                            "span_records": sorted(_rid(s) for s in spans[call]),
                            "fact": "a call recorded as blocked has a gateway span; both are shown, neither is chosen"})
    out.sort(key=lambda m: (m["run_id"] or "", m["call.id"], m["blocked_record"]))
    return out

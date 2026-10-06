"""EP-16 collector (Ph2): invocations of our runtimes that our script did not make (the cockpit's ask API, any
other caller). It reads `InvokeAgentRuntime` records (see aict_invocations) and FLAGS; it never calls the cockpit.

An invocation is flagged when it is on one of our runtimes AND (a) its baggage CID is absent, or (b) the CID is not
ours (not in `ours` and not an `ifabric-` CID), or (c) the caller is not one of `our_callers` (when given).
No CID -> the pseudo CID `unattributed:<runtime>:<eventTime>` (ids.py). Observation only: no verdict."""
from __future__ import annotations

from prooflab.adapters.collectors import aict_invocations as inv_mod, capture
from prooflab.contract import ids

SURFACE = "side-door"


def runtime_name(arn) -> str:
    return str(arn or "").rsplit("/", 1)[-1] or "unknown"


def flag(invocations, our_runtime_arns=(), ours=(), our_callers=()) -> list:
    """-> observation rows for the flagged invocations, sorted. `ours` = CIDs from run-ids.txt (any family)."""
    ours, arns, callers = set(ours), list(our_runtime_arns), set(our_callers)
    out = []
    for i in invocations:
        if arns and i.get("runtime_arn") not in arns:
            continue
        cid, reasons = i.get("cid"), []
        if not cid:
            reasons.append("no-cid")
        elif cid not in ours and not ids.is_ours(cid):
            reasons.append("cid-not-ours")
        if callers and i.get("caller_principal") not in callers and i.get("caller_arn") not in callers:
            reasons.append("caller-not-ours")
        if not reasons:
            continue
        label = cid or "unattributed:%s:%s" % (runtime_name(i.get("runtime_arn")), i.get("event_time"))
        out.append({"kind": "side-door-invocation", "label": label, "reasons": reasons,
                    "cid_family": ids.cid_family(label) if ids.is_valid_run_id(label) else None,
                    "event_time": i.get("event_time"), "runtime_arn": i.get("runtime_arn"),
                    "session_id": i.get("session_id"), "trace_id": i.get("trace_id"),
                    "caller_arn": i.get("caller_arn"), "event_id": i.get("event_id")})
    out.sort(key=lambda r: (r["event_time"] or "", r["event_id"] or ""))
    return out


def pull(ctx: capture.Ctx, rows, start: str, end: str, our_runtime_arns=(), ours=(), our_callers=()) -> dict:
    """`rows` = captured aict-invocations rows (or parsed invocations). Writes raw/side-door/window/*.jsonl."""
    parsed = [r if "session_id" in r else inv_mod.parse_record(r.get("message")) for r in rows]
    flagged = flag([p for p in parsed if p], our_runtime_arns, ours, our_callers)
    return capture.write_capture(
        ctx, SURFACE, "window", "side-door-%s.jsonl" % end.replace(":", "").replace("-", ""), capture.jsonl(flagged),
        command="derived from raw/aict-invocations (no live call)",
        scope={"start": start, "end": end, "runtime_arns": list(our_runtime_arns)},
        source_identity={"source": "aict-invocations", "invocations_seen": len([p for p in parsed if p])})

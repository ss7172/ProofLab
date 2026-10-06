"""EP-11 collector (Ph2): the AWS-written `InvokeAgentRuntime` records in `/aws/bedrock/aict-invocations` (7 d),
swept over a WINDOW for our runtime ARNs, never per CID (a call without our CID must still land).

Each record carries, in `responseElements`, the caller-sent `runtimeSessionId` (`<CID>-<32 hex>`), `traceParent`
and `baggage` (`modaas-correlation-id=<CID>`); `requestParameters` is empty. `eventTime` is the call's END and the
record lands 19-328 s later, so a pull is refused until the window's end is `MIN_AGE_S` old, and joins use
`eventTime`, never the CloudWatch timestamp. `join_run` is the exact join; it never guesses."""
from __future__ import annotations

import json
import re

from prooflab.adapters.collectors import capture
from prooflab.contract import clocks, ids
from prooflab.store import redact

SURFACE = "aict-invocations"
LOG_GROUP = "/aws/bedrock/aict-invocations"
EVENT_NAME = "InvokeAgentRuntime"
MIN_AGE_S = 600                 # ARCH EP-11: pull at least 10 minutes after the run (delivery lag, not a control limit)
_SESSION_HEX = re.compile(r"^[0-9a-f]{32}$")


def parse_record(message) -> "dict | None":
    """One log message -> the fields a join needs, or None when it is not an InvokeAgentRuntime record."""
    try:
        rec = json.loads(message) if isinstance(message, (str, bytes)) else dict(message)
    except (ValueError, TypeError):
        return None
    if not isinstance(rec, dict) or rec.get("eventName") != EVENT_NAME:
        return None
    resp = rec.get("responseElements") or {}
    baggage = resp.get("baggage") or ""
    cid = None
    for part in str(baggage).split(","):
        k, _, v = part.strip().partition("=")
        if k == ids.BAGGAGE_CID_KEY and v:
            cid = v
    trace_id = None
    tp = str(resp.get("traceParent") or "").split("-")
    if len(tp) == 4:
        trace_id = tp[1]
    resources = [r.get("ARN") for r in rec.get("resources") or [] if isinstance(r, dict)]
    ident = rec.get("userIdentity") or {}
    return {"event_id": rec.get("eventID"), "event_time": rec.get("eventTime"),
            "runtime_arn": next((a for a in resources if a and "runtime" in a), resources[0] if resources else None),
            "session_id": resp.get("runtimeSessionId"), "trace_id": trace_id, "cid": cid,
            "status": resp.get("statusCode"), "caller_arn": ident.get("arn"),
            "caller_principal": (((ident.get("sessionContext") or {}).get("sessionIssuer") or {}).get("userName")
                                 or ident.get("principalId")),
            "user_agent": rec.get("userAgent")}


def records(rows) -> list:
    """Parse captured rows (`{message: ...}` objects) into invocation dicts; other records are skipped."""
    out = []
    for r in rows:
        p = parse_record(r.get("message") if isinstance(r, dict) and "message" in r else r)
        if p:
            out.append(p)
    return out


def session_matches(cid: str, session_id) -> bool:
    s = str(session_id or "")
    return s.startswith(cid + "-") and bool(_SESSION_HEX.match(s[len(cid) + 1:]))


def join_run(invocations, cid: str) -> dict:
    """The exact join: baggage CID == cid AND runtimeSessionId == `<cid>-<32 hex>`. A record that has one but not
    the other is reported in `mismatched`, never joined. The same session seen twice is a retry (`retried`)."""
    matches, mismatched = [], []
    for inv in invocations:
        by_baggage = inv.get("cid") == cid
        by_session = session_matches(cid, inv.get("session_id"))
        if by_baggage and by_session:
            matches.append(inv)
        elif by_baggage or by_session:
            mismatched.append(inv)
    matches.sort(key=lambda i: (i.get("event_time") or "", i.get("event_id") or ""))
    seen, retried = {}, []
    for m in matches:
        seen[m["session_id"]] = seen.get(m["session_id"], 0) + 1
    retried = sorted(s for s, n in seen.items() if n > 1)
    return {"cid": cid, "matches": matches, "mismatched": mismatched, "retried_sessions": retried}


def pull(ctx: capture.Ctx, runtime_arns, start: str, end: str, log_group: str = LOG_GROUP) -> dict:
    """Sweep [start, end] for `InvokeAgentRuntime` records and keep those on `runtime_arns` (all, if empty)."""
    age = (clocks.parse_utc(ctx.now()) - clocks.parse_utc(end)).total_seconds()
    if age < MIN_AGE_S:
        raise capture.CaptureError("too early: records land up to ~330 s late; wait until %d s after %s" % (MIN_AGE_S, end))
    events, pages, complete, cmd = capture.filter_log_events(ctx, log_group, '"%s"' % EVENT_NAME, start, end)
    arns = list(runtime_arns or [])
    rows = []
    for e in events:
        inv = parse_record(e.get("message"))
        if inv is None:
            continue
        if arns and not any(a in (e.get("message") or "") for a in arns):
            continue
        rows.append({k: e.get(k) for k in ("timestamp", "ingestionTime", "logStreamName", "message")})
    rows.sort(key=lambda r: ((parse_record(r["message"]) or {}).get("event_time") or "", r.get("message") or ""))
    rows, counts, _ = redact.redact_obj(rows)
    return capture.write_capture(
        ctx, SURFACE, "window", "invocations-%s-%s.jsonl" % (clocks.compact(start), clocks.compact(end)),
        capture.jsonl(rows), command=cmd,
        scope={"start": start, "end": end, "runtime_arns": arns, "event_name": EVENT_NAME},
        source_identity={"log_group": log_group, "pages": pages, "join": "eventTime, not @timestamp"},
        pagination_complete=complete, counts=counts)

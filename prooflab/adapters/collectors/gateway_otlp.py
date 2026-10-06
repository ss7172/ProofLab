"""EP-7 collector (Ph2): the gateway's `/aws/modaas/gateway` log copy (7 d; trace id only, no run id), by trace id.
It serves refusals that carry no CID (pause 404, 403, 405); the CID is resolved later through /modaas/evidence."""
from __future__ import annotations

from prooflab.adapters.collectors import capture
from prooflab.store import redact

SURFACE = "gateway-otlp"
LOG_GROUP = "/aws/modaas/gateway"


def pull(ctx: capture.Ctx, trace_id: str, start: str, end: str, log_group: str = LOG_GROUP) -> dict:
    events, pages, complete, cmd = capture.filter_log_events(ctx, log_group, '"%s"' % trace_id, start, end)
    rows = [{k: e.get(k) for k in ("timestamp", "ingestionTime", "logStreamName", "message")} for e in events]
    rows, counts, _ = redact.redact_obj(rows)
    return capture.write_capture(
        ctx, SURFACE, trace_id, "gateway.jsonl", capture.jsonl(rows), command=cmd,
        scope={"trace_id": trace_id, "start": start, "end": end},
        source_identity={"log_group": log_group, "pages": pages}, pagination_complete=complete, counts=counts)

"""The stdout witness: an AgentCore runtime's own CloudWatch log group, filtered by run id (CID) and window.
Events are written one JSON object per line (timestamp, ingestionTime, logStreamName, message verbatim)."""
from __future__ import annotations

from prooflab.adapters.collectors import capture
from prooflab.store import redact

SURFACE = "runtime-logs"


def group_for(runtime_id: str) -> str:
    return "/aws/bedrock-agentcore/runtimes/%s-DEFAULT" % runtime_id


def pull(ctx: capture.Ctx, runtime_id: str, cid: str, start: str, end: str) -> "dict | None":
    if capture.skip_cid(cid):
        return None
    group = group_for(runtime_id)
    events, pages, complete, cmd = capture.filter_log_events(ctx, group, '"%s"' % cid, start, end)
    rows = [{k: e.get(k) for k in ("timestamp", "ingestionTime", "logStreamName", "message")} for e in events]
    rows, counts, _ = redact.redact_obj(rows)      # span content can ride in a message (G-11)
    return capture.write_capture(
        ctx, SURFACE, cid, "%s.jsonl" % runtime_id, capture.jsonl(rows), command=cmd,
        scope={"cid": cid, "start": start, "end": end, "runtime": runtime_id},
        source_identity={"log_group": group, "pages": pages}, pagination_complete=complete, counts=counts)

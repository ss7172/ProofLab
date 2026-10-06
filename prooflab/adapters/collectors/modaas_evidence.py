"""EP-6 collector: `/modaas/evidence` (30 d), decisions joined to the CID. Guardrail blocks and pauses are logged
ALLOW there: this collector records the line, it never reports an outcome."""
from __future__ import annotations

from prooflab.adapters.collectors import capture
from prooflab.store import redact

SURFACE = "modaas-evidence"
LOG_GROUP = "/modaas/evidence"


def pull(ctx: capture.Ctx, cid: str, start: str, end: str) -> "dict | None":
    if capture.skip_cid(cid):
        return None
    events, pages, complete, cmd = capture.filter_log_events(ctx, LOG_GROUP, '"%s"' % cid, start, end)
    rows = [{k: e.get(k) for k in ("timestamp", "ingestionTime", "logStreamName", "message")} for e in events]
    rows, counts, _ = redact.redact_obj(rows)      # span content can ride in a message (G-11)
    return capture.write_capture(
        ctx, SURFACE, cid, "evidence.jsonl", capture.jsonl(rows), command=cmd,
        scope={"cid": cid, "start": start, "end": end},
        source_identity={"log_group": LOG_GROUP, "pages": pages}, pagination_complete=complete, counts=counts)

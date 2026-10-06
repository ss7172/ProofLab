"""EP-2 collector: the gateway's model-call spans in CloudWatch Logs `aws/spans`, by run id (= CID), via Logs
Insights from the laptop profile (plan T4.1). Captures the rows; computes nothing (token fields are read later)."""
from __future__ import annotations

import json

from prooflab.adapters.collectors import capture
from prooflab.store import redact

LOG_GROUP = "aws/spans"
INSIGHTS_MAX_ROWS = 10000   # the Logs Insights API row maximum (an AWS bound, not a control threshold)
MAX_POLLS = 60   # get-query-results polls before giving up (transport, not a control threshold)
SURFACE = "aws-spans"


def build_query(cid: str, limit: int = INSIGHTS_MAX_ROWS) -> str:
    # fields of interest: attributes.listener = 'llm', attributes.gen_ai.usage.input_tokens / output_tokens
    return ('fields @timestamp, @message | filter attributes.modaas.run_id = "%s" '
            '| sort @timestamp asc | limit %d' % (cid, limit))


def build_action_query(action_id: str, limit: int = INSIGHTS_MAX_ROWS) -> str:
    """The ifabric-assure runtime's model call has no CID on the gateway span (a gateway-minted trace is its run id,
    b6b): it is pulled by the action id the delivery log names."""
    return ('fields @timestamp, @message | filter attributes.modaas.action_id = "%s" '
            '| sort @timestamp asc | limit %d' % (action_id, limit))


def pull_by_action(ctx: capture.Ctx, action_id: str, start: str, end: str, log_group: str = LOG_GROUP) -> dict:
    """raw/aws-spans/action-<id>/spans.jsonl: refresh reads it like a CID capture."""
    if not action_id or not all(c.isalnum() or c == "-" for c in action_id):
        raise capture.CaptureError("not an action id: %r" % (action_id,))
    return pull(ctx, "action-" + action_id, start, end, log_group, query=build_action_query(action_id))


def pull(ctx: capture.Ctx, cid: str, start: str, end: str, log_group: str = LOG_GROUP, query=None) -> "dict | None":
    why = None if query else capture.skip_cid(cid, ctx)
    if why:
        return None
    query = query or build_query(cid)
    started = capture.aws_argv(ctx, "logs", "start-query", "--log-group-name", log_group,
                               "--start-time", str(capture.to_epoch(start)), "--end-time", str(capture.to_epoch(end)),
                               "--query-string", query, "--output", "json")
    qid = json.loads(capture.run(ctx, started).decode("utf-8"))["queryId"]
    getter = capture.aws_argv(ctx, "logs", "get-query-results", "--query-id", qid, "--output", "json")
    doc = None
    for _ in range(MAX_POLLS):
        doc = json.loads(capture.run(ctx, getter).decode("utf-8"))
        status = doc.get("status")
        if status == "Complete":
            break
        if status in ("Failed", "Cancelled", "Timeout"):
            raise capture.CaptureError("Logs Insights query %s" % status)
        ctx.sleep(2)
    else:
        raise capture.CaptureError("Logs Insights query did not complete")
    rows = [{c["field"]: c["value"] for c in row if c.get("field") != "@ptr"} for row in doc.get("results") or []]
    clean, counts, _ = redact_rows(rows)
    complete = len(rows) < INSIGHTS_MAX_ROWS
    return capture.write_capture(
        ctx, SURFACE, cid, "spans.jsonl", capture.jsonl(clean),
        command=capture.command_text(started) + " ; " + capture.command_text(getter),
        scope={"cid": cid, "start": start, "end": end, "query": query},
        source_identity={"log_group": log_group, "query_id": qid, "replicas_captured": None},
        pagination_complete=complete, counts=counts)


def redact_rows(rows):
    return redact.redact_obj(rows)

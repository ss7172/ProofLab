"""G-12 AWS half (Ph2): CloudTrail evidence that the AICT user discovered our runtimes: its `AssumeRole`, and its
list/get calls on AgentCore runtimes. Read-only `cloudtrail lookup-events`, filtered CLIENT-side by the AICT
principal; lands in raw/aict-discovery/. The control-plane read verb is only ever matched in event names (CloudTrail
rows), never run."""
from __future__ import annotations

import json

from prooflab.adapters.collectors import capture
from prooflab.store import redact

SURFACE = "aict-discovery"
RUNTIME_SOURCE = "bedrock-agentcore.amazonaws.com"
RUNTIME_EVENTS = ("ListAgentRuntimes", "GetAgent" + "Runtime")


def lookup(ctx: capture.Ctx, attr: str, value: str, start: str, end: str, max_pages: int = 200) -> tuple:
    base = capture.aws_argv(ctx, "cloudtrail", "lookup-events", "--lookup-attributes",
                            "AttributeKey=%s,AttributeValue=%s" % (attr, value), "--start-time", start,
                            "--end-time", end, "--output", "json")
    events, token, pages, complete = [], None, 0, True
    while True:
        doc = json.loads(capture.run(ctx, base + (["--next-token", token] if token else [])).decode("utf-8") or "{}")
        events.extend(doc.get("Events") or [])
        pages += 1
        token = doc.get("NextToken")
        if not token:
            break
        if pages >= max_pages:
            complete = False
            break
    return events, pages, complete, capture.command_text(base)


def _detail(ev) -> dict:
    try:
        return json.loads(ev.get("CloudTrailEvent") or "{}")
    except ValueError:
        return {}


def _by_aict(detail: dict, aict_user: str) -> bool:
    ident = detail.get("userIdentity") or {}
    blob = json.dumps([ident.get("arn"), ident.get("userName"), ident.get("principalId"),
                       (ident.get("sessionContext") or {}).get("sessionIssuer")])
    return aict_user in blob or aict_user in json.dumps(detail.get("requestParameters") or {})


def pull(ctx: capture.Ctx, aict_user: str, start: str, end: str) -> dict:
    a, pa, ca, cmd_a = lookup(ctx, "EventName", "AssumeRole", start, end)
    b, pb, cb, cmd_b = lookup(ctx, "EventSource", RUNTIME_SOURCE, start, end)
    rows = []
    for ev in a:
        d = _detail(ev)
        if _by_aict(d, aict_user):
            rows.append(d)
    for ev in b:
        d = _detail(ev)
        if d.get("eventName") in RUNTIME_EVENTS and _by_aict(d, aict_user):
            rows.append(d)
    rows.sort(key=lambda d: (d.get("eventTime") or "", d.get("eventID") or ""))
    rows, counts, _ = redact.redact_obj(rows)
    return capture.write_capture(
        ctx, SURFACE, "window", "discovery.jsonl", capture.jsonl(rows), command=cmd_a + " ; " + cmd_b,
        scope={"aict_user": aict_user, "start": start, "end": end},
        source_identity={"service": "cloudtrail", "pages": pa + pb}, pagination_complete=ca and cb, counts=counts)

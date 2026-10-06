"""EP-12 collector (Ph2): each tool Lambda's name, CodeSha256 and LastModified from `lambda list-functions`.

ListFunctions also returns environment variables, so the response is projected CLIENT-SIDE to exactly those three
fields before anything is written; it is asked for them server-side too (`--query`). The function-fetch verb that
returns a presigned code URL is never run (capture.run refuses it)."""
from __future__ import annotations

import json

from prooflab.adapters.collectors import capture

SURFACE = "lambda-codesha"
KEEP = ("FunctionName", "CodeSha256", "LastModified")
QUERY = "Functions[].{FunctionName:FunctionName,CodeSha256:CodeSha256,LastModified:LastModified}"


def project(functions, names=()) -> list:
    rows = [{k: f.get(k) for k in KEEP} for f in functions if isinstance(f, dict)]
    if names:
        rows = [r for r in rows if r["FunctionName"] in set(names)]
    return sorted(rows, key=lambda r: r["FunctionName"] or "")


def pull(ctx: capture.Ctx, names=(), scope_name: str = "tools") -> dict:
    argv = capture.aws_argv(ctx, "lambda", "list-functions", "--query", QUERY, "--output", "json")
    doc = json.loads(capture.run(ctx, argv).decode("utf-8") or "[]")
    rows = project(doc if isinstance(doc, list) else doc.get("Functions") or [], names)
    return capture.write_capture(
        ctx, SURFACE, scope_name, "codesha.jsonl", capture.jsonl(rows), command=capture.command_text(argv),
        scope={"names": list(names), "fields": list(KEEP)}, source_identity={"service": "lambda"})

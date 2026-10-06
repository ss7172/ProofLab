#!/usr/bin/env python3
"""OPS LANE ONLY (live, read-only): capture C9's AgentCore metrics for one run's W2 into a snapshot. Stdlib, 3.9.

    hk 'cd <repo> && python3 tools/c9_pull_metrics.py --snapshot <snap> --runtimes-file <runtimes.json>
                     --started <run.started UTC> --finished <run.finished UTC>'

Pulls Latency Maximum, Errors Sum and Invocations Sum at period 60 per runtime (dimensions Resource + Operation +
Name, agentcore_metrics.dimensions) over W2 = [minute of run.started, minute of run.finished + 60 s] through the
collector's one read-only seam; the captures land in <snap>/raw/agentcore-metrics/<runtime name>/ with sidecars
(captured_at = now). Run it AFTER W2 closes plus the publication delay (OC-20: <= 15.6 s measured, b2d): the
assessment marks a capture taken before W2 closed as "not yet present" (INDETERMINATE). Also, with --action-id, pulls
aws/spans rows of the Assurance agent's model calls by action id (b6b: they carry no CID).
Workers never run this; tests drive it with a fake runner.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from prooflab.adapters.collectors import agentcore_metrics as M  # noqa: E402
from prooflab.adapters.collectors import aws_spans, capture  # noqa: E402
from prooflab.query import c9_inputs as I  # noqa: E402

SERIES = M.METRICS + (("Invocations", "Sum"),)


def w2(started, finished):
    s, f = I.utc(started), I.utc(finished)
    if s is None or f is None or f < s:
        raise ValueError("--started/--finished must be UTC times with started <= finished")
    lo = s.replace(second=0, microsecond=0)
    close = f.replace(second=0, microsecond=0) + dt.timedelta(seconds=I.METRIC_PERIOD_S)
    return I.iso(lo), I.iso(close)


def pull(ctx, runtimes, started, finished, action_ids=(), span_window=None):
    start, end = w2(started, finished)
    now = I.utc(ctx.now())
    if now is not None and now < I.utc(end):
        raise capture.CaptureError("W2 closes at %s; it is %s: pull after the close (+ OC-20 delay)" % (end, I.iso(now)))
    out = []
    for agent, arn in sorted(runtimes.items()):
        name = I.runtime_key(agent).replace("-", "_")
        for metric, stat in SERIES:
            out.append(M.pull(ctx, name, metric, stat, start, end, period=I.METRIC_PERIOD_S, resource_arn=arn))
    for aid in action_ids or ():
        s, e = span_window or (start, end)
        out.append(aws_spans.pull_by_action(ctx, aid, s, e))
    return {"w2": [start, end], "captures": [c["path"] for c in out]}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="c9_pull_metrics.py")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--runtimes-file", required=True, help='{"ifabric-customer": "<runtime ARN>", ...}')
    ap.add_argument("--started", required=True)
    ap.add_argument("--finished", required=True)
    ap.add_argument("--action-id", action="append", default=[], help="an Assurance analysis action id (repeatable)")
    ap.add_argument("--span-window", nargs=2, default=None, metavar=("START", "END"),
                    help="aws/spans window for --action-id (default: W2)")
    ap.add_argument("--operator", default="ops-lane")
    ns = ap.parse_args(argv)
    with open(ns.runtimes_file, "r", encoding="utf-8") as fh:
        runtimes = json.load(fh)
    ctx = capture.Ctx(root=ns.snapshot, operator=ns.operator)
    try:
        res = pull(ctx, runtimes, ns.started, ns.finished, ns.action_id, ns.span_window)
    except (capture.CaptureError, ValueError) as exc:
        print("c9_pull_metrics: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

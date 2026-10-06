"""EP-11 collector: AWS/Bedrock-AgentCore metrics per runtime and CLOSED hour (C9 signal). Captures
`get-metric-statistics --output json` stdout byte for byte; empty datapoints are recorded, never judged."""
from __future__ import annotations

from prooflab.adapters.collectors import capture
from prooflab.contract import clocks

SURFACE = "agentcore-metrics"
NAMESPACE = "AWS/Bedrock-AgentCore"
METRICS = (("Latency", "Maximum"), ("Errors", "Sum"))


OPERATION = "InvokeAgentRuntime"


def dimensions(runtime: str, resource_arn: str, operation: str = OPERATION) -> list:
    """The full dimension set CloudWatch needs (live S-2, 2026-10-06: `Name` alone returns EMPTY datapoints):
    Resource = the runtime ARN, Operation = InvokeAgentRuntime, Name = <runtime name>::DEFAULT."""
    return [("Resource", resource_arn), ("Operation", operation), ("Name", runtime + "::DEFAULT")]


def pull(ctx: capture.Ctx, runtime: str, metric: str, statistic: str, hour_start: str, hour_end: str,
         period: int = 3600, *, resource_arn: str = "", operation: str = OPERATION) -> dict:
    """`runtime` is the runtime NAME (the Name dimension, e.g. ifabric_customer); `resource_arn` its runtime ARN."""
    if not resource_arn:
        raise capture.CaptureError("agentcore metrics need the runtime ARN (Resource dimension); Name alone is empty")
    if clocks.parse_utc(hour_end) > clocks.parse_utc(ctx.now()):
        raise capture.CaptureError("only closed hours: %s is in the future" % hour_end)
    dims = dimensions(runtime, resource_arn, operation)
    argv = capture.aws_argv(ctx, "cloudwatch", "get-metric-statistics", "--namespace", NAMESPACE,
                            "--metric-name", metric, "--dimensions", *["Name=%s,Value=%s" % d for d in dims],
                            "--start-time", hour_start, "--end-time", hour_end, "--period", str(period),
                            "--statistics", statistic, "--output", "json")
    data = capture.run(ctx, argv)
    return capture.write_capture(
        ctx, SURFACE, runtime, "%s-%s-%s.json" % (metric, statistic, clocks.compact(hour_start)), data,
        command=capture.command_text(argv),
        scope={"runtime": runtime, "start": hour_start, "end": hour_end, "metric": metric, "statistic": statistic,
               "period": period, "dimensions": dict(dims), "namespace": NAMESPACE},
        source_identity={"namespace": NAMESPACE})


def pull_all(ctx: capture.Ctx, runtimes, hour_start: str, hour_end: str) -> list:
    """`runtimes`: {runtime name: runtime ARN} (or an iterable of (name, arn) pairs)."""
    pairs = list(runtimes.items()) if isinstance(runtimes, dict) else list(runtimes)
    return [pull(ctx, n, m, st, hour_start, hour_end, resource_arn=arn) for n, arn in pairs for m, st in METRICS]

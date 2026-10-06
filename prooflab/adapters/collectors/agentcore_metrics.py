"""EP-11 collector: AWS/Bedrock-AgentCore metrics per runtime and CLOSED hour (C9 signal). Captures
`get-metric-statistics --output json` stdout byte for byte; empty datapoints are recorded, never judged."""
from __future__ import annotations

from prooflab.adapters.collectors import capture
from prooflab.contract import clocks

SURFACE = "agentcore-metrics"
NAMESPACE = "AWS/Bedrock-AgentCore"
METRICS = (("Latency", "Maximum"), ("Errors", "Sum"))


def pull(ctx: capture.Ctx, runtime: str, metric: str, statistic: str, hour_start: str, hour_end: str,
         period: int = 3600) -> dict:
    if clocks.parse_utc(hour_end) > clocks.parse_utc(ctx.now()):
        raise capture.CaptureError("only closed hours: %s is in the future" % hour_end)
    dim = "Name=Name,Value=%s::DEFAULT" % runtime
    argv = capture.aws_argv(ctx, "cloudwatch", "get-metric-statistics", "--namespace", NAMESPACE,
                            "--metric-name", metric, "--dimensions", dim, "--start-time", hour_start,
                            "--end-time", hour_end, "--period", str(period), "--statistics", statistic,
                            "--output", "json")
    data = capture.run(ctx, argv)
    return capture.write_capture(
        ctx, SURFACE, runtime, "%s-%s-%s.json" % (metric, statistic, clocks.compact(hour_start)), data,
        command=capture.command_text(argv),
        scope={"runtime": runtime, "start": hour_start, "end": hour_end, "metric": metric, "statistic": statistic,
               "period": period, "dimensions": {"Name": runtime + "::DEFAULT"}, "namespace": NAMESPACE},
        source_identity={"namespace": NAMESPACE})


def pull_all(ctx: capture.Ctx, runtimes, hour_start: str, hour_end: str) -> list:
    return [pull(ctx, r, m, s, hour_start, hour_end) for r in runtimes for m, s in METRICS]

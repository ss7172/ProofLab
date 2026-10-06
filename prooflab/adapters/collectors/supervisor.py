"""The ExpiredToken supervisor (T4.1, T7.4 passive): run collector jobs in order; an expired-credentials error
becomes a `monitoring-gap` finding (written beside the captures), the remaining jobs are listed as skipped, and the
loop stops (never a retry: the operator refreshes credentials). Any other CaptureError is recorded and the next job
runs. The collectors do not know about this module."""
from __future__ import annotations

from prooflab.adapters.collectors import capture
from prooflab.contract import finding as _finding, verdicts as _V

SURFACE = "supervisor"
CONTROL_ID = "COLLECT-SUPERVISOR"


def gap_finding(job: str, reason: str, detected_at: str) -> dict:
    return _finding.make_finding(
        "NONE", CONTROL_ID, "collect@1", "interval", "collect:" + detected_at, _V.INDETERMINATE,
        "monitoring gap: credentials expired during %s; later collectors did not run" % job, detected_at,
        evidence=[], kind="monitoring-gap")


def run_jobs(ctx: capture.Ctx, jobs) -> dict:
    """`jobs` = [(name, zero-arg callable)]. -> {done, errors, gaps, skipped}."""
    result = {"done": [], "errors": [], "gaps": [], "skipped": []}
    jobs = list(jobs)
    for n, (name, fn) in enumerate(jobs):
        try:
            result["done"].append({"job": name, "result": fn()})
        except capture.ExpiredTokenError as exc:
            result["gaps"].append(gap_finding(name, str(exc), ctx.now()))
            result["skipped"] = [j[0] for j in jobs[n + 1:]]
            break
        except capture.CaptureError as exc:
            result["errors"].append({"job": name, "error": str(exc)[:300]})
    if result["gaps"]:
        g = result["gaps"][0]
        capture.write_capture(
            ctx, SURFACE, "run", "monitoring-gap.jsonl", capture.jsonl(result["gaps"]),
            command="supervisor", scope={"skipped": result["skipped"]},
            source_identity={"supervisor": "collectors"})
    return result

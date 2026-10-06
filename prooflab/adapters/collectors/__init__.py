"""Laptop collectors (PR-12a): pull() adapters that capture bytes, normalize nothing, compute no verdict.

Every live call goes through ONE subprocess seam (`capture.default_runner`, only `aws` / `kubectl`), which tests
replace; workers never run it. Surfaces: aws_spans (EP-2), modaas_evidence (EP-6), cr_status (EP-10),
agentcore_metrics (EP-11), runtime_logs (the stdout witness), ledger_export (per-CID GET only).
"""
from __future__ import annotations

SURFACES = ("aws_spans", "ledger_export", "cr_status", "agentcore_metrics", "runtime_logs", "modaas_evidence",
            # PR-12b
            "pdp_logs", "gateway_stdout", "gateway_otlp", "aict_invocations", "aict_discovery", "lambda_codesha",
            "side_door", "supervisor")


def main(argv=None) -> int:
    """List the surfaces. Live pulls are driven by the orchestrator / ops lane (the `collect` verb's module is
    not owned by this PR), so this entry point never makes a call."""
    print("collectors: " + ", ".join(SURFACES))
    return 0

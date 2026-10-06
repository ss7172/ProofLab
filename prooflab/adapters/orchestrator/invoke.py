"""The ONE subprocess seam for InvokeAgentRuntime (ARCH 7.2 "exactly one invocation per handoff").

`invoke_once` is called at most once per handoff by run.py. A timeout is returned as TIMEOUT and is never
retried here or by the caller; the AWS CLI itself is told not to retry (AWS_MAX_ATTEMPTS=1).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile

from prooflab.adapters.orchestrator import common


def child_env(base, budget) -> dict:
    env = dict(base)
    env["AWS_MAX_ATTEMPTS"] = budget["invoke"]["aws_max_attempts"]
    env["AWS_RETRY_MODE"] = budget["invoke"]["aws_retry_mode"]
    return env


def build_argv(arn: str, session_id: str, payload_path: str, out_path: str, baggage: str, traceparent: str,
               budget) -> list:
    """`aws bedrock-agentcore invoke-agent-runtime ...`; the baggage is always present (no run without it)."""
    if not baggage:
        raise ValueError("--baggage modaas-correlation-id=<CID> is mandatory on every invocation")
    return ["aws", "bedrock-agentcore", "invoke-agent-runtime",
            "--agent-runtime-arn", arn,
            "--runtime-session-id", session_id,
            "--payload", "fileb://" + payload_path,
            "--baggage", baggage,
            "--trace-parent", traceparent,
            "--cli-read-timeout", budget["invoke"]["cli_read_timeout"],
            out_path]


def _looks_like_timeout(text: str) -> bool:
    low = (text or "").lower()
    return "read timeout" in low or "timed out" in low or "readtimeout" in low


def invoke_once(argv, env, budget, runner=subprocess.run, out_path=None) -> dict:
    """One call. Returns {status: OK|TIMEOUT|ERROR, output, returncode, duration_ms, stderr_tail}.

    `runner` is the test seam (same signature as subprocess.run). Nothing here retries.
    """
    import time
    started = time.time()
    hard_limit = int(budget["invoke"]["cli_read_timeout"]) + int(budget["invoke"]["subprocess_grace_seconds"])
    try:
        proc = runner(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                      timeout=hard_limit)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "output": None, "returncode": None,
                "duration_ms": int((time.time() - started) * 1000), "stderr_tail": ""}
    duration = int((time.time() - started) * 1000)
    stderr = (proc.stderr or "")[-400:]
    if proc.returncode != 0:
        status = "TIMEOUT" if _looks_like_timeout(proc.stderr) else "ERROR"
        return {"status": status, "output": None, "returncode": proc.returncode, "duration_ms": duration,
                "stderr_tail": _scrub(stderr)}
    return {"status": "OK", "output": _read_output(out_path, proc.stdout), "returncode": 0,
            "duration_ms": duration, "stderr_tail": ""}


def _scrub(text: str) -> str:
    from prooflab.contract import record as R
    return "[withheld: secret-shaped]" if R.secret_shaped(text) else text


def _read_output(out_path, stdout):
    raw = None
    if out_path and os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    if raw is None:
        raw = stdout or ""
    try:
        doc = json.loads(raw)
    except ValueError:
        return {"text": raw}
    # the kit unwraps `output` (ask_agent.py)
    if isinstance(doc, dict) and "output" in doc:
        return doc["output"] if isinstance(doc["output"], dict) else {"text": doc["output"]}
    return doc if isinstance(doc, dict) else {"text": raw}


def write_payload(payload: dict, directory=None) -> str:
    """Payload to a mode-600 temp file (no secret in it; keeps argv short)."""
    fd, path = tempfile.mkstemp(prefix="prooflab-payload-", suffix=".json", dir=directory)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True))
    return path


def out_file(directory=None) -> str:
    fd, path = tempfile.mkstemp(prefix="prooflab-out-", suffix=".json", dir=directory)
    os.close(fd)
    return path

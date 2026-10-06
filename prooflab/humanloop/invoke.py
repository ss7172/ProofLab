"""G-03: the laptop's call to the Assurance agent's AgentCore runtime (ARCH 3.11, 7.3; plan T6.3).

    analyzer = assurance_analyzer(arn)          # Arth's CallableAnalyzer, backend agentcore:ifabric_assurance_agent
    run_assurance_agent(finding, client, log, analyzer, ...)

`invoke_assurance(messages)` runs ONE `aws bedrock-agentcore invoke-agent-runtime` (a subprocess):
AWS_MAX_ATTEMPTS=1, `--cli-read-timeout 300`, a fresh session id, `--baggage modaas-correlation-id=<CID>`
with its own prefix `ifabric-assure-` (the same CID in the payload), so these model calls never count in a
subject run's C16 floor or C7 set. A timeout or any failure becomes AnalyzerError("unavailable"); a guardrail
block becomes AnalyzerError("blocked") with its action id. It is never re-invoked here. The payload and response
files are deleted at once, and the model text is never logged. Stdlib only, Python 3.9.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import tempfile
import time
from typing import Callable, List, Optional

CID_PREFIX = "ifabric-assure-"
BACKEND = "agentcore:ifabric_assurance_agent"
MODEL_ALIAS = "nemotron-super-120b"
ARN_ENV = "IFABRIC_ASSURE_RUNTIME_ARN"
CLI_READ_TIMEOUT_S = "300"
SUBPROCESS_GRACE_S = 30
_ARN = re.compile(r"^arn:aws[a-z-]*:bedrock-agentcore:[a-z0-9-]+:\d{12}:runtime/[A-Za-z0-9_-]+$")


def _analyzer_error():
    from prooflab.servicenow.nemotron import AnalyzerError  # Arth's, unchanged (PR-00 syncs it)
    return AnalyzerError


def new_cid(now: Optional[float] = None) -> str:
    return "%s%d-%s" % (CID_PREFIX, int(now if now is not None else time.time()), secrets.token_hex(4))


def new_session_id(cid: str) -> str:
    """`<CID>-<32 hex>`: fresh per call, and over AgentCore's 33-character minimum."""
    return "%s-%s" % (cid, secrets.token_hex(16))


def new_traceparent() -> str:
    return "00-%s-%s-01" % (secrets.token_hex(16), secrets.token_hex(8))


def child_env(base=None) -> dict:
    env = dict(os.environ if base is None else base)
    env["AWS_MAX_ATTEMPTS"] = "1"
    env["AWS_RETRY_MODE"] = "standard"
    return env


def build_argv(arn: str, session_id: str, payload_path: str, out_path: str, cid: str, traceparent: str) -> list:
    if not cid.startswith(CID_PREFIX):
        raise ValueError("the Assurance CID must start with " + CID_PREFIX)
    return ["aws", "bedrock-agentcore", "invoke-agent-runtime",
            "--agent-runtime-arn", arn,
            "--runtime-session-id", session_id,
            "--payload", "fileb://" + payload_path,
            "--baggage", "modaas-correlation-id=" + cid,
            "--trace-parent", traceparent,
            "--cli-read-timeout", CLI_READ_TIMEOUT_S,
            out_path]


def _unlink(path: Optional[str]) -> None:
    if path:
        try:
            os.unlink(path)
        except OSError:
            pass


def _parse(raw: str) -> dict:
    doc = json.loads(raw)
    if isinstance(doc, dict) and "output" in doc and isinstance(doc["output"], dict):  # the kit's unwrap
        doc = doc["output"]
    if not isinstance(doc, dict):
        raise ValueError("not an object")
    return doc


def invoke_assurance(messages: List[dict], arn: Optional[str] = None, runner: Callable = subprocess.run,
                     env: Optional[dict] = None, tmpdir: Optional[str] = None, cid: Optional[str] = None) -> dict:
    """One invocation; returns {text, model_id, action_id, usage, latency_ms, finish_reason} or raises
    AnalyzerError. `runner` is the test seam (subprocess.run's signature)."""
    AnalyzerError = _analyzer_error()
    arn = arn or os.environ.get(ARN_ENV, "")
    if not _ARN.match(arn or ""):
        raise AnalyzerError("unavailable", "no Assurance runtime ARN (set %s)" % ARN_ENV)
    cid = cid or new_cid()
    fd, payload_path = tempfile.mkstemp(prefix="ifabric-assure-in-", suffix=".json", dir=tmpdir)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"messages": messages, "cid": cid}, fh)
    fd, out_path = tempfile.mkstemp(prefix="ifabric-assure-out-", suffix=".json", dir=tmpdir)
    os.close(fd)
    raw = None
    try:
        argv = build_argv(arn, new_session_id(cid), payload_path, out_path, cid, new_traceparent())
        try:
            proc = runner(argv, env=child_env(env), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=int(CLI_READ_TIMEOUT_S) + SUBPROCESS_GRACE_S)
        except subprocess.TimeoutExpired:
            raise AnalyzerError("unavailable", "timeout (%s): recorded, never re-invoked" % cid) from None
        except OSError as err:
            raise AnalyzerError("unavailable", "aws cli not runnable: %s" % type(err).__name__) from None
        if proc.returncode != 0:
            low = (proc.stderr or "").lower()
            what = "timeout" if ("timed out" in low or "read timeout" in low) else "exit %s" % proc.returncode
            raise AnalyzerError("unavailable", "%s (%s): never re-invoked" % (what, cid))
        try:
            with open(out_path, "r", encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except OSError:
            raw = ""
    finally:
        _unlink(out_path)   # the response holds the model text: gone at once (R10)
        _unlink(payload_path)
    try:
        doc = _parse(raw or "")
    except ValueError:
        raise AnalyzerError("unavailable", "unreadable runtime response (%s)" % cid) from None
    if doc.get("error"):
        kind = "blocked" if doc.get("error") == "blocked" else "unavailable"
        raise AnalyzerError(kind, "runtime said %s (%s)" % (kind, cid), doc.get("action_id"))
    return {"text": doc.get("text") or "", "model_id": doc.get("model_id"), "action_id": doc.get("action_id"),
            "usage": doc.get("usage") or {}, "latency_ms": doc.get("latency_ms") or 0,
            "finish_reason": doc.get("finish_reason"), "cid": cid}


def assurance_analyzer(arn: Optional[str] = None, runner: Callable = subprocess.run, env: Optional[dict] = None,
                       tmpdir: Optional[str] = None, model_alias: str = MODEL_ALIAS):
    """Arth's CallableAnalyzer around invoke_assurance; the backend label keeps V6 passing."""
    from prooflab.servicenow.nemotron import CallableAnalyzer

    def fn(messages):
        return invoke_assurance(messages, arn=arn, runner=runner, env=env, tmpdir=tmpdir)

    return CallableAnalyzer(fn, backend=BACKEND, model_alias=model_alias)

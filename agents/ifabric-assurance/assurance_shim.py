# ---- the shim (ours, NOT Arth's; G-01, ARCH 3.11 / 7.3): the AgentCore entrypoint around his unchanged analyser.
# tools/bundle_assurance.py appends this file after the loader that serves Arth's byte-identical nemotron.py.
# Contract (handoff-3 08 §5.3): in {"messages": [...]} (also {"input": {...}}, optional "cid");
# out {text, model_id, action_id, usage, latency_ms, finish_reason} or {error: blocked|unavailable, action_id}.
import json
import os
import sys
import time

# The span-redaction env (ARCH 7.1): the CR env sets it; a default here too, never an override.
os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_unredacted_attributes=")

from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402
from prooflab.servicenow import nemotron  # noqa: E402
from prooflab.servicenow.nemotron import AnalyzerError, GatewayAnalyzer  # noqa: E402

_TOKENS_ENV = "IFABRIC_ASSURE_MAX_TOKENS"


def _apply_max_tokens():
    """The token limit via config (approved; OC-28): the env value replaces nemotron.MAX_TOKENS, which
    GatewayAnalyzer reads on every request. Unset or invalid keeps Arth's own default (900)."""
    raw = (os.environ.get(_TOKENS_ENV) or "").strip()
    if not raw:
        return nemotron.MAX_TOKENS
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value > 0:
        nemotron.MAX_TOKENS = value
    else:
        _witness({"event": "config-ignored", "name": _TOKENS_ENV})
    return nemotron.MAX_TOKENS


def gateway_base():
    """The operator injects OPENAI_BASE_URL (shape http://<gateway ELB>:8081/v1, B1); Arth's analyser appends
    /v1/chat/completions itself, so one trailing /v1 is removed (OC-32). MODAAS_GATEWAY_URL wins if set."""
    url = (os.environ.get("MODAAS_GATEWAY_URL") or os.environ.get("OPENAI_BASE_URL") or "").strip().rstrip("/")
    return url[:-3] if url.endswith("/v1") else url


class InjectedGateway(GatewayAnalyzer):
    """The gateway-URL shim (approved; gap 9): only the constructor differs. Arth's _check_gateway_url refuses
    the operator-injected plain-HTTP ELB URL; this accepts it. His request and response code run unchanged.
    The key crosses in clear, as on every runtime today (recorded as a security gap)."""

    def __init__(self, base_url, model_alias, api_key=None):
        if not model_alias:
            raise ValueError("MODEL_ALIAS is not set")
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("gateway URL must be http(s)")
        self.base_url = base_url.rstrip("/")
        self.model_alias = model_alias
        self.backend = "modaas-agw:" + model_alias
        self._api_key = api_key
        self._clock = time.monotonic


def _witness(fields):
    """One stdout JSON line per call (AWS-timestamped in [runtime-logs]); never the model text."""
    line = {"ifabric": "assurance.witness/1"}
    line.update(fields)
    sys.stdout.write(json.dumps(line, sort_keys=True) + "\n")
    sys.stdout.flush()


app = BedrockAgentCoreApp()
_STATE = {"analyzer": None}


def analyzer():
    if _STATE["analyzer"] is None:
        _STATE["analyzer"] = InjectedGateway(gateway_base(), os.environ.get("MODEL_ALIAS", ""),
                                             os.environ.get("OPENAI_API_KEY") or None)
    return _STATE["analyzer"]


def _cid(payload, inner):
    for src in (inner, payload):
        if isinstance(src, dict) and isinstance(src.get("cid"), str):
            return src["cid"][:128]
    return None


def handle(payload):
    payload = payload if isinstance(payload, dict) else {}
    inner = payload.get("input") if isinstance(payload.get("input"), dict) else payload
    messages = inner.get("messages")
    cid = _cid(payload, inner)
    if not isinstance(messages, list) or not messages:
        _witness({"cid": cid, "outcome": "bad_request"})
        return {"error": "unavailable", "action_id": None}
    try:
        reply = analyzer().analyze(messages)
    except AnalyzerError as err:
        kind = "blocked" if err.kind == "blocked" else "unavailable"
        _witness({"cid": cid, "outcome": kind, "kind": err.kind, "action_id": err.action_id})
        return {"error": kind, "action_id": err.action_id}
    except Exception as err:  # never a traceback or a message into the runtime response
        _witness({"cid": cid, "outcome": "unavailable", "kind": type(err).__name__})
        return {"error": "unavailable", "action_id": None}
    _witness({"cid": cid, "outcome": "ok", "action_id": reply.action_id, "usage": reply.usage,
              "finish_reason": reply.finish_reason, "latency_ms": reply.latency_ms,
              "max_tokens": nemotron.MAX_TOKENS})
    return {"text": reply.text, "model_id": reply.model_id, "action_id": reply.action_id,
            "usage": reply.usage, "latency_ms": reply.latency_ms, "finish_reason": reply.finish_reason}


@app.entrypoint
def invoke(payload):
    return handle(payload)


_apply_max_tokens()

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "8080")))

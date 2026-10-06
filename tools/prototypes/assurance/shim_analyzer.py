# ---- glue (ours, NOT Arth's): AgentCore entrypoint for the pure-analyzer contract (spec 08 §5.3)
import os
import time
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from prooflab.servicenow.nemotron import AnalyzerError, GatewayAnalyzer


def _gateway_base() -> str:
    # The operator injects OPENAI_BASE_URL / OPENAI_API_KEY / MODEL_ALIAS (MODEL_ALIAS is reserved);
    # Arth's GatewayAnalyzer appends /v1/chat/completions itself, so a trailing /v1 is removed.
    url = (os.environ.get("MODAAS_GATEWAY_URL") or os.environ.get("OPENAI_BASE_URL", "")).rstrip("/")
    return url[:-3] if url.endswith("/v1") else url


class _InjectedGateway(GatewayAnalyzer):
    """Unchanged request/response code; only the constructor's URL policy is relaxed for the
    platform-injected ELB URL (plain http on :8081). Prefer an https URL when the TLS listener verifies."""

    def __init__(self, base_url: str, model_alias: str, api_key=None) -> None:
        if not model_alias:
            raise ValueError("MODEL_ALIAS is not set")
        self.base_url, self.model_alias = base_url, model_alias
        self.backend = f"modaas-agw:{model_alias}"
        self._api_key, self._clock = api_key, time.monotonic


app = BedrockAgentCoreApp()
_ANALYZER = None


def _analyzer():
    global _ANALYZER
    if _ANALYZER is None:
        _ANALYZER = _InjectedGateway(_gateway_base(), os.environ.get("MODEL_ALIAS", ""),
                                     os.environ.get("OPENAI_API_KEY") or None)
    return _ANALYZER


@app.entrypoint
def invoke(payload):
    inner = payload.get("input") if isinstance(payload.get("input"), dict) else payload
    messages = inner.get("messages") if isinstance(inner, dict) else None
    if not isinstance(messages, list) or not messages:
        return {"error": "bad_request", "action_id": None}
    try:
        reply = _analyzer().analyze(messages)
    except AnalyzerError as err:
        return {"error": err.kind, "action_id": err.action_id}
    except Exception as err:  # never leak a traceback into the runtime response
        return {"error": "unavailable", "detail": type(err).__name__, "action_id": None}
    return {"text": reply.text, "model_id": reply.model_id, "action_id": reply.action_id,
            "usage": reply.usage, "latency_ms": reply.latency_ms, "finish_reason": reply.finish_reason}


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "8080")))

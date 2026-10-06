# ---- generated bundle loader (ours): serves the embedded, byte-identical prooflab modules
import importlib.abc
import importlib.util
import sys

_PACKAGES = {"prooflab", "prooflab.servicenow"}


class _BundleFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name not in _SOURCES:
            return None
        # A location is set so __file__ exists; registering in sys.modules before exec is what
        # dataclasses need under `from __future__ import annotations` (importlib does it for us).
        return importlib.util.spec_from_file_location(
            name, _ORIGIN + "/" + name.replace(".", "/") + ("/__init__.py" if name in _PACKAGES else ".py"),
            loader=self, submodule_search_locations=[] if name in _PACKAGES else None)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(_SOURCES[module.__name__], module.__file__, "exec"), module.__dict__)


_SOURCES = {
    'prooflab': '',
    'prooflab.servicenow': '',
    'prooflab.servicenow.nemotron': '"""Nemotron access for the assurance agent: only through the governed MoDaaS gateway.\n\nTwo backends behind one interface (`analyze(messages) -> AnalyzerReply`):\n  GatewayAnalyzer   POST {MODAAS_GATEWAY_URL}/v1/chat/completions with a Nemotron alias\n                    (the governed path: guardrail-checked, ledger-recorded, x-modaas-action-id)\n  CallableAnalyzer  wraps a function that invokes the deployed AgentCore runtime\n                    `ifabric_assurance_agent` (which itself calls modaas-agw)\nDirect Bedrock or any non-governed endpoint is never used.\n\nEnvironment for GatewayAnalyzer.from_env():\n  MODAAS_GATEWAY_URL   e.g. http://modaas-agw.modaas-system.svc.cluster.local:8080 (in-cluster) or https://...\n  MODAAS_MODEL_ALIAS   a currently APPROVED Nemotron alias, e.g. nemotron-super-120b\n  MODAAS_API_KEY       optional bearer token if the gateway requires one (never logged)\n"""\nfrom __future__ import annotations\n\nimport json\nimport os\nimport re\nimport socket\nimport time\nimport urllib.error\nimport urllib.parse\nimport urllib.request\nfrom dataclasses import dataclass, field\nfrom http.client import HTTPException\nfrom typing import Callable, Dict, List, Optional, Tuple\n\nTIMEOUT_SECONDS = 90\nMAX_TOKENS = 900\n_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)\n_INTERNAL_SUFFIXES = (".svc", ".svc.cluster.local", ".cluster.local")\n_LOOPBACK = ("127.0.0.1", "localhost", "::1")\nANALYSIS_MARKER = "[iFabric Assurance Agent analysis]"\n\n\n@dataclass(frozen=True)\nclass AnalyzerReply:\n    text: str\n    backend: str\n    model_alias: str\n    model_id: Optional[str] = None\n    action_id: Optional[str] = None\n    usage: Dict[str, int] = field(default_factory=dict)\n    finish_reason: Optional[str] = None\n    latency_ms: int = 0\n    model_family: str = "NVIDIA Nemotron"  # shown in the note\'s provenance line\n\n\nclass AnalyzerError(Exception):\n    """kind: \'blocked\' (guardrail/content filter), \'unavailable\' (no usable answer), \'bad_response\'."""\n\n    def __init__(self, kind: str, message: str, action_id: Optional[str] = None) -> None:\n        super().__init__(f"{kind}: {message}")\n        self.kind = kind\n        self.action_id = action_id\n\n\ndef strip_reasoning(text: str) -> Tuple[str, bool]:\n    """Keep only the final answer\'s note. Private reasoning is never kept.\n\n    - closed <think>…</think> blocks are removed;\n    - an orphan </think> (the opening tag was in the chat template) ends the reasoning:\n      everything before the last one is dropped;\n    - an unclosed <think> means the answer never finished: no note at all;\n    - the LAST marker wins, so a draft note earlier in the text is never used."""\n    lowered = text.lower()\n    stripped = "<think>" in lowered or "</think>" in lowered\n    cleaned = _THINK_BLOCK.sub("", text)\n    close = cleaned.lower().rfind("</think>")\n    if close >= 0:\n        cleaned = cleaned[close + len("</think>"):]\n    if "<think>" in cleaned.lower():\n        return "", True\n    start = cleaned.rfind(ANALYSIS_MARKER)\n    return (cleaned[start:].strip() if start >= 0 else cleaned.strip()), stripped\n\n\ndef _check_gateway_url(base_url: str) -> str:\n    parsed = urllib.parse.urlparse(base_url)\n    host = parsed.hostname or ""\n    if parsed.scheme == "https":\n        return base_url.rstrip("/")\n    if parsed.scheme == "http" and (host in _LOOPBACK or host.endswith(_INTERNAL_SUFFIXES)):\n        return base_url.rstrip("/")\n    raise ValueError(f"gateway URL must be https or cluster-internal http, got {base_url!r}")\n\n\nclass _NoRedirect(urllib.request.HTTPRedirectHandler):\n    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401\n        return None\n\n\n_OPENER = urllib.request.build_opener(_NoRedirect)\n\n\nclass GatewayAnalyzer:\n    def __init__(self, base_url: str, model_alias: str, api_key: Optional[str] = None,\n                 clock: Callable[[], float] = time.monotonic) -> None:\n        if not model_alias:\n            raise ValueError("model_alias is required (a Nemotron alias approved in MoDaaS)")\n        self.base_url = _check_gateway_url(base_url)\n        self.model_alias = model_alias\n        self.backend = f"modaas-agw:{model_alias}"\n        self._api_key = api_key\n        self._clock = clock\n\n    @classmethod\n    def from_env(cls) -> "GatewayAnalyzer":\n        missing = [name for name in ("MODAAS_GATEWAY_URL", "MODAAS_MODEL_ALIAS") if not os.environ.get(name)]\n        if missing:\n            raise ValueError(f"set environment variables: {\', \'.join(missing)}")\n        return cls(os.environ["MODAAS_GATEWAY_URL"], os.environ["MODAAS_MODEL_ALIAS"],\n                   os.environ.get("MODAAS_API_KEY") or None)\n\n    def _request(self, messages: List[dict]) -> urllib.request.Request:\n        body = json.dumps({"model": self.model_alias, "messages": messages, "temperature": 0,\n                           "max_tokens": MAX_TOKENS}).encode()\n        headers = {"Content-Type": "application/json", "Accept": "application/json"}\n        if self._api_key:\n            headers["Authorization"] = f"Bearer {self._api_key}"\n        return urllib.request.Request(f"{self.base_url}/v1/chat/completions", data=body,\n                                      method="POST", headers=headers)\n\n    def analyze(self, messages: List[dict]) -> AnalyzerReply:\n        started = self._clock()\n        try:\n            with _OPENER.open(self._request(messages), timeout=TIMEOUT_SECONDS) as response:\n                action_id = response.headers.get("x-modaas-action-id")\n                raw = response.read().decode(errors="replace")\n        except urllib.error.HTTPError as err:\n            body = err.read().decode(errors="replace")\n            kind = "blocked" if "content_filter" in body else "unavailable"   # check before truncating\n            raise AnalyzerError(kind, f"HTTP {err.code}: {body[:300]}",\n                                err.headers.get("x-modaas-action-id") if err.headers else None) from err\n        except (urllib.error.URLError, socket.timeout, ConnectionError, HTTPException) as err:\n            raise AnalyzerError("unavailable", str(err)) from err\n        return self._reply(raw, action_id, int((self._clock() - started) * 1000))\n\n    def _reply(self, raw: str, action_id: Optional[str], latency_ms: int) -> AnalyzerReply:\n        try:\n            payload = json.loads(raw)\n            choice = payload["choices"][0]\n            text = choice["message"]["content"] or ""\n        except (ValueError, KeyError, IndexError, TypeError) as err:\n            raise AnalyzerError("bad_response", f"unexpected gateway response: {raw[:80]!r}", action_id) from err\n        if choice.get("finish_reason") == "content_filter":\n            raise AnalyzerError("blocked", "guardrail filtered the completion", action_id)\n        usage = payload.get("usage")\n        return AnalyzerReply(text=text, backend=self.backend, model_alias=self.model_alias,\n                             model_id=payload.get("model"), action_id=action_id,\n                             usage=dict(usage) if isinstance(usage, dict) else {},\n                             finish_reason=choice.get("finish_reason"), latency_ms=latency_ms)\n\n\nclass CallableAnalyzer:\n    """Adapter for the AgentCore runtime (or any governed caller you already have).\n\n    fn(messages) must return {"text", "model_id", "action_id", "usage"} and raise\n    AnalyzerError on guardrail blocks or outages."""\n\n    def __init__(self, fn: Callable[[List[dict]], dict], backend: str, model_alias: str,\n                 model_family: str = "NVIDIA Nemotron") -> None:\n        self._fn = fn\n        self.backend = backend\n        self.model_alias = model_alias\n        self.model_family = model_family  # e.g. "TEST stand-in (no model)" for wiring tests\n\n    def analyze(self, messages: List[dict]) -> AnalyzerReply:\n        result = self._fn(messages)\n        return AnalyzerReply(text=result.get("text") or "", backend=self.backend,\n                             model_alias=self.model_alias, model_id=result.get("model_id"),\n                             action_id=result.get("action_id"), usage=dict(result.get("usage") or {}),\n                             finish_reason=result.get("finish_reason"),\n                             latency_ms=int(result.get("latency_ms") or 0),\n                             model_family=self.model_family)\n',
}
_ORIGIN = "/app/_bundle"
sys.meta_path.insert(0, _BundleFinder())

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

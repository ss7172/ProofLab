"""Nemotron access for the assurance agent: only through the governed MoDaaS gateway.

Two backends behind one interface (`analyze(messages) -> AnalyzerReply`):
  GatewayAnalyzer   POST {MODAAS_GATEWAY_URL}/v1/chat/completions with a Nemotron alias
                    (the governed path: guardrail-checked, ledger-recorded, x-modaas-action-id)
  CallableAnalyzer  wraps a function that invokes the deployed AgentCore runtime
                    `ifabric_assurance_agent` (which itself calls modaas-agw)
Direct Bedrock or any non-governed endpoint is never used.

Environment for GatewayAnalyzer.from_env():
  MODAAS_GATEWAY_URL   e.g. http://modaas-agw.modaas-system.svc.cluster.local:8080 (in-cluster) or https://...
  MODAAS_MODEL_ALIAS   a currently APPROVED Nemotron alias, e.g. nemotron-super-120b
  MODAAS_API_KEY       optional bearer token if the gateway requires one (never logged)
"""
from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from http.client import HTTPException
from typing import Callable, Dict, List, Optional, Tuple

TIMEOUT_SECONDS = 90
MAX_TOKENS = 900
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_INTERNAL_SUFFIXES = (".svc", ".svc.cluster.local", ".cluster.local")
_LOOPBACK = ("127.0.0.1", "localhost", "::1")
ANALYSIS_MARKER = "[iFabric Assurance Agent analysis]"


@dataclass(frozen=True)
class AnalyzerReply:
    text: str
    backend: str
    model_alias: str
    model_id: Optional[str] = None
    action_id: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    latency_ms: int = 0
    model_family: str = "NVIDIA Nemotron"  # shown in the note's provenance line


class AnalyzerError(Exception):
    """kind: 'blocked' (guardrail/content filter), 'unavailable' (no usable answer), 'bad_response'."""

    def __init__(self, kind: str, message: str, action_id: Optional[str] = None) -> None:
        super().__init__(f"{kind}: {message}")
        self.kind = kind
        self.action_id = action_id


def strip_reasoning(text: str) -> Tuple[str, bool]:
    """Keep only the final answer's note. Private reasoning is never kept.

    - closed <think>…</think> blocks are removed;
    - an orphan </think> (the opening tag was in the chat template) ends the reasoning:
      everything before the last one is dropped;
    - an unclosed <think> means the answer never finished: no note at all;
    - the LAST marker wins, so a draft note earlier in the text is never used."""
    lowered = text.lower()
    stripped = "<think>" in lowered or "</think>" in lowered
    cleaned = _THINK_BLOCK.sub("", text)
    close = cleaned.lower().rfind("</think>")
    if close >= 0:
        cleaned = cleaned[close + len("</think>"):]
    if "<think>" in cleaned.lower():
        return "", True
    start = cleaned.rfind(ANALYSIS_MARKER)
    return (cleaned[start:].strip() if start >= 0 else cleaned.strip()), stripped


def _check_gateway_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or ""
    if parsed.scheme == "https":
        return base_url.rstrip("/")
    if parsed.scheme == "http" and (host in _LOOPBACK or host.endswith(_INTERNAL_SUFFIXES)):
        return base_url.rstrip("/")
    raise ValueError(f"gateway URL must be https or cluster-internal http, got {base_url!r}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class GatewayAnalyzer:
    def __init__(self, base_url: str, model_alias: str, api_key: Optional[str] = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if not model_alias:
            raise ValueError("model_alias is required (a Nemotron alias approved in MoDaaS)")
        self.base_url = _check_gateway_url(base_url)
        self.model_alias = model_alias
        self.backend = f"modaas-agw:{model_alias}"
        self._api_key = api_key
        self._clock = clock

    @classmethod
    def from_env(cls) -> "GatewayAnalyzer":
        missing = [name for name in ("MODAAS_GATEWAY_URL", "MODAAS_MODEL_ALIAS") if not os.environ.get(name)]
        if missing:
            raise ValueError(f"set environment variables: {', '.join(missing)}")
        return cls(os.environ["MODAAS_GATEWAY_URL"], os.environ["MODAAS_MODEL_ALIAS"],
                   os.environ.get("MODAAS_API_KEY") or None)

    def _request(self, messages: List[dict]) -> urllib.request.Request:
        body = json.dumps({"model": self.model_alias, "messages": messages, "temperature": 0,
                           "max_tokens": MAX_TOKENS}).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return urllib.request.Request(f"{self.base_url}/v1/chat/completions", data=body,
                                      method="POST", headers=headers)

    def analyze(self, messages: List[dict]) -> AnalyzerReply:
        started = self._clock()
        try:
            with _OPENER.open(self._request(messages), timeout=TIMEOUT_SECONDS) as response:
                action_id = response.headers.get("x-modaas-action-id")
                raw = response.read().decode(errors="replace")
        except urllib.error.HTTPError as err:
            body = err.read().decode(errors="replace")
            kind = "blocked" if "content_filter" in body else "unavailable"   # check before truncating
            raise AnalyzerError(kind, f"HTTP {err.code}: {body[:300]}",
                                err.headers.get("x-modaas-action-id") if err.headers else None) from err
        except (urllib.error.URLError, socket.timeout, ConnectionError, HTTPException) as err:
            raise AnalyzerError("unavailable", str(err)) from err
        return self._reply(raw, action_id, int((self._clock() - started) * 1000))

    def _reply(self, raw: str, action_id: Optional[str], latency_ms: int) -> AnalyzerReply:
        try:
            payload = json.loads(raw)
            choice = payload["choices"][0]
            text = choice["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as err:
            raise AnalyzerError("bad_response", f"unexpected gateway response: {raw[:80]!r}", action_id) from err
        if choice.get("finish_reason") == "content_filter":
            raise AnalyzerError("blocked", "guardrail filtered the completion", action_id)
        usage = payload.get("usage")
        return AnalyzerReply(text=text, backend=self.backend, model_alias=self.model_alias,
                             model_id=payload.get("model"), action_id=action_id,
                             usage=dict(usage) if isinstance(usage, dict) else {},
                             finish_reason=choice.get("finish_reason"), latency_ms=latency_ms)


class CallableAnalyzer:
    """Adapter for the AgentCore runtime (or any governed caller you already have).

    fn(messages) must return {"text", "model_id", "action_id", "usage"} and raise
    AnalyzerError on guardrail blocks or outages."""

    def __init__(self, fn: Callable[[List[dict]], dict], backend: str, model_alias: str,
                 model_family: str = "NVIDIA Nemotron") -> None:
        self._fn = fn
        self.backend = backend
        self.model_alias = model_alias
        self.model_family = model_family  # e.g. "TEST stand-in (no model)" for wiring tests

    def analyze(self, messages: List[dict]) -> AnalyzerReply:
        result = self._fn(messages)
        return AnalyzerReply(text=result.get("text") or "", backend=self.backend,
                             model_alias=self.model_alias, model_id=result.get("model_id"),
                             action_id=result.get("action_id"), usage=dict(result.get("usage") or {}),
                             finish_reason=result.get("finish_reason"),
                             latency_ms=int(result.get("latency_ms") or 0),
                             model_family=self.model_family)

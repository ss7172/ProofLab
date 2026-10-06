"""In-process fake of the MoDaaS governed gateway's OpenAI-style chat endpoint.

POST /v1/chat/completions answers from a queue of scripted replies, so tests can
model Nemotron output (with think tags), guardrail blocks and outages without the
real modaas-agw.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional, Tuple

API_KEY = "test-gateway-key"


def completion(content: str, finish_reason: str = "stop", model: str = "nvidia/nemotron-test",
               action_id: str = "act-1") -> Tuple[int, dict, dict]:
    body = {"id": "cmpl-1", "model": model,
            "choices": [{"index": 0, "finish_reason": finish_reason,
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 900, "completion_tokens": 210, "total_tokens": 1110}}
    return 200, body, {"x-modaas-action-id": action_id}


def blocked() -> Tuple[int, dict, dict]:
    return 400, {"error": {"code": "content_filter", "message": "guardrail blocked the request"}}, \
        {"x-modaas-action-id": "act-blocked"}


class FakeGateway:
    def __init__(self) -> None:
        self.replies: List[Tuple[int, dict, dict]] = []
        self.requests: List[dict] = []
        self.auth_headers: List[Optional[str]] = []
        self._server: Optional[ThreadingHTTPServer] = None

    @property
    def base_url(self) -> str:
        assert self._server is not None
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> "FakeGateway":
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                fake.requests.append(json.loads(self.rfile.read(length).decode()))
                fake.auth_headers.append(self.headers.get("Authorization"))
                if self.path != "/v1/chat/completions" or not fake.replies:
                    status, body, headers = 503, {"error": {"message": "no reply scripted"}}, {}
                else:
                    status, body, headers = fake.replies.pop(0)
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()

"""Test-only stand-in for bedrock_agentcore.runtime.BedrockAgentCoreApp (used only where the real SDK is absent,
i.e. the 3.9 venv): GET /ping, POST /invocations, as the runtime contract. Never shipped in a bundle."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class BedrockAgentCoreApp:
    def __init__(self):
        self._fn = None

    def entrypoint(self, fn):
        self._fn = fn
        return fn

    def run(self, port=8080, host=None):
        app = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def _send(self, code, obj):
                data = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._send(200 if self.path == "/ping" else 404, {"status": "Healthy"})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                self._send(200, app._fn(body))

        HTTPServer((host or "127.0.0.1", port), H).serve_forever()

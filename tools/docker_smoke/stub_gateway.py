#!/usr/bin/env python3
"""A stub OpenAI-compatible gateway + ledger for the S-0 local smoke (stdlib only; NEVER the real gateway).

  POST /v1/chat/completions  -> a canned answer ending in the J2 JSON line; SSE when "stream": true
                                (delta chunks, a final chunk carrying usage, then [DONE]), with a
                                synthetic x-modaas-action-id response header, as the gateway sets one
  POST /records              -> 200 {"ok": true} (the ledger's path; bodies are counted, not kept)
  GET  /health               -> 200

  python3 tools/docker_smoke/stub_gateway.py --port 18181
Every request is logged to stdout as one JSON line (path, model, stream flag): no bodies, no headers.
"""
import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANSWER = (
    "- Impacted: synthetic stub customers at the stub site.\n"
    "- Impact: degraded service (stub).\n"
    "- Tell them: engineers are on it (stub).\n"
    '{"disposition": "gather-evidence", "deciding_evidence": [], '
    '"reversible_step": "none (stub)", "reason": "stub gateway: no real evidence"}'
)
STATE = {"n": 0, "records": 0}
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _log(self, **kw):
        print(json.dumps(dict({"stub": "gateway", "path": self.path}, **kw), sort_keys=True), flush=True)

    def _json(self, code, obj, extra=None):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._log(method="GET")
        self._json(200, {"ok": True}) if self.path == "/health" else self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if self.path.rstrip("/").endswith("/records"):
            with LOCK:
                STATE["records"] += 1
            self._log(method="POST", records=STATE["records"])
            return self._json(200, {"ok": True})
        if not self.path.endswith("/chat/completions"):
            self._log(method="POST", status=404)
            return self._json(404, {"error": "not found"})
        try:
            req = json.loads(raw.decode() or "{}")
        except ValueError:
            return self._json(400, {"error": "bad json"})
        with LOCK:
            STATE["n"] += 1
            n = STATE["n"]
        action = "stub-action-%04d" % n
        model = req.get("model", "stub")
        self._log(method="POST", model=model, stream=bool(req.get("stream")), action_id=action)
        usage = {"prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180}
        if not req.get("stream"):
            return self._json(200, {
                "id": "chatcmpl-stub-%d" % n, "object": "chat.completion", "created": 0, "model": model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": ANSWER},
                             "finish_reason": "stop"}], "usage": usage}, {"x-modaas-action-id": action})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("x-modaas-action-id", action)
        self.end_headers()

        def chunk(delta, finish=None, use=None):
            body = {"id": "chatcmpl-stub-%d" % n, "object": "chat.completion.chunk", "created": 0,
                    "model": model, "choices": [] if use else [
                        {"index": 0, "delta": delta, "finish_reason": finish}]}
            if use:
                body["usage"] = use
            self.wfile.write(("data: " + json.dumps(body) + "\n\n").encode())
            self.wfile.flush()

        chunk({"role": "assistant", "content": ""})
        for i in range(0, len(ANSWER), 64):
            chunk({"content": ANSWER[i:i + 64]})
        chunk({}, finish="stop")
        chunk({}, use=usage)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True


def serve(port, host="0.0.0.0"):
    srv = ThreadingHTTPServer((host, port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def main(argv=None):
    p = argparse.ArgumentParser(description="stub OpenAI-compatible gateway + ledger (S-0 smoke only)")
    p.add_argument("--port", type=int, default=18181)
    p.add_argument("--host", default="0.0.0.0")
    a = p.parse_args(argv)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(json.dumps({"stub": "gateway", "listening": a.port}), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

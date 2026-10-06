"""Local, read-only case panel: the standalone demo and a reference integration.

  GET /                       panel page (panel/index.html)
  GET /ifabric-case-panel.js  framework-free renderer
  GET /ifabric-case-panel.css its styles
  GET /cases.json             live case_view() list, cached briefly to spare ServiceNow

Binds to loopback only, serves a fixed whitelist of files, answers GET only,
and never writes to ServiceNow or the evidence log.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, List

PANEL_DIR = Path(__file__).with_name("panel")
_STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
           "/index.html": ("index.html", "text/html; charset=utf-8"),
           "/ifabric-case-panel.js": ("ifabric-case-panel.js", "text/javascript; charset=utf-8"),
           "/ifabric-case-panel.css": ("ifabric-case-panel.css", "text/css; charset=utf-8")}
_LOOPBACK = ("127.0.0.1", "localhost", "::1")
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self'; "
                                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'"),
}
DEFAULT_CACHE_SECONDS = 10.0


class _CachedLoader:
    """Calls load() at most once per ttl seconds, however often the page polls."""

    def __init__(self, load: Callable[[], List[dict]], ttl: float) -> None:
        self._load, self._ttl = load, ttl
        self._lock = threading.Lock()
        self._value: List[dict] = []
        self._loaded_at = float("-inf")

    def get(self) -> List[dict]:
        with self._lock:
            if time.monotonic() - self._loaded_at >= self._ttl:
                self._value = self._load()
                self._loaded_at = time.monotonic()
            return self._value


def _handler(cases: _CachedLoader):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # keep demo output clean
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for name, value in _SECURITY_HEADERS.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload) -> None:
            self._send(status, json.dumps(payload, sort_keys=True).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _host_ok(self) -> bool:
            # Binding to loopback is not enough: a DNS-rebinding page reaches 127.0.0.1 with a
            # foreign Host header. Only loopback names are served.
            host = (self.headers.get("Host") or "").strip()
            name = host[1:host.find("]")] if host.startswith("[") else host.rsplit(":", 1)[0]
            return name in _LOOPBACK

        def do_GET(self) -> None:  # noqa: N802 (http.server naming)
            if not self._host_ok():
                return self._json(403, {"error": "forbidden host"})
            path = self.path.split("?", 1)[0]
            if path == "/cases.json":
                try:
                    return self._json(200, cases.get())
                except Exception as err:  # loader failure must not kill the demo server
                    return self._json(503, {"error": type(err).__name__})
            if path in _STATIC:
                name, content_type = _STATIC[path]
                return self._send(200, (PANEL_DIR / name).read_bytes(), content_type)
            return self._json(404, {"error": "not found"})

        def _refuse(self) -> None:
            self._json(405, {"error": "read-only"})

        do_POST = do_PUT = do_PATCH = do_DELETE = _refuse

    return Handler


def make_server(load_cases: Callable[[], List[dict]], host: str = "127.0.0.1", port: int = 0,
                cache_seconds: float = DEFAULT_CACHE_SECONDS) -> ThreadingHTTPServer:
    if host not in _LOOPBACK:
        raise ValueError(f"refusing to bind {host!r}: the case panel serves loopback only")
    return ThreadingHTTPServer((host, port), _handler(_CachedLoader(load_cases, cache_seconds)))


def serve_forever(load_cases: Callable[[], List[dict]], port: int, host: str = "127.0.0.1") -> None:
    server = make_server(load_cases, host=host, port=port)
    print(f"Case panel: http://{host}:{server.server_address[1]}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

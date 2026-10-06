"""Gateway action id capture (ARCH 3.1 EP-1, 05 AR-12/AR-13).

The gateway sets `x-modaas-action-id` on every response. An httpx response
event hook reads it as the headers arrive (before the SSE body is consumed)
and parks it where the after-call step can take it. Stdlib only; the hook is
a plain coroutine function so it plugs into httpx.AsyncClient(event_hooks=...).
"""
import threading

HEADER = "x-modaas-action-id"


class ActionIdCapture(object):
    def __init__(self, max_log=1000):
        self._lock = threading.Lock()
        self.last = None
        self.seen = 0
        self.missing = 0
        self.log = []
        self._max_log = max_log

    def observe_headers(self, headers, status=None):
        value = None
        try:
            value = headers.get(HEADER)
        except Exception:
            value = None
        with self._lock:
            if value:
                self.seen += 1
                self.last = value
            else:
                self.missing += 1
            if len(self.log) != self._max_log:
                self.log.append({"present": bool(value), "status": status})
        return value

    async def on_response(self, response):
        """httpx async response hook."""
        self.observe_headers(response.headers, getattr(response, "status_code", None))

    def begin(self):
        """Forget the id of a previous attempt before a new request."""
        with self._lock:
            self.last = None

    def take(self):
        with self._lock:
            v = self.last
            self.last = None
            return v

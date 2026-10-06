"""A local stdlib fake of the audit-store ledger: POST /records appends, GET /records[?cid=] reads, header checked."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

TEST_CREDENTIAL = "fake-" + "ledger-credential"      # a throwaway value, never a real secret


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _auth(self):
        if self.headers.get("X-Audit-Token") != self.server.expected:
            self._send(401, {"error": "unauthorized"})
            return False
        return True

    def _send(self, code, doc):
        body = json.dumps(doc).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not self._auth():
            return
        n = int(self.headers.get("Content-Length") or 0)
        try:
            doc = json.loads(self.rfile.read(n))
        except ValueError:
            return self._send(400, {"error": "bad record"})
        if not isinstance(doc, dict):
            return self._send(400, {"error": "bad record"})
        self.server.log.append(("POST", self.path))
        doc = dict(doc)
        doc["seq"] = 1791000000000 + len(self.server.rows)
        self.server.rows.append(doc)
        self._send(201, {"ok": True})

    def do_GET(self):
        if not self._auth():
            return
        u = urlparse(self.path)
        self.server.log.append(("GET", self.path))
        cid = parse_qs(u.query).get("cid", [None])[0]
        rows = [r for r in self.server.rows if cid is None or r.get("correlation_id") == cid]
        self._send(200, rows)


class FakeLedger:
    def __init__(self, rows=()):
        self.httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.rows = list(rows)
        self.httpd.log = []
        self.httpd.expected = TEST_CREDENTIAL
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self.httpd.server_address[1]

    @property
    def rows(self):
        return self.httpd.rows

    @property
    def log(self):
        return self.httpd.log

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()

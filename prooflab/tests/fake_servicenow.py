"""In-process fake of the ServiceNow endpoints the adapter uses.

Implements just enough of /oauth_token.do and the REST Table API
(incident, sys_user, sys_journal_field) to exercise the adapter over real
HTTP without touching the shared hackathon instance. It also models the
awkward real-world cases: gateway errors after a write, garbled bodies,
other teams' incidents with the same correlation id, and system actors.
"""
from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret"
INTEGRATION_USER = "ifabric.integration"
OWNER_USER = "owner@example.com"
OWNER_SYS_ID = "owner-sys-id"
INTEGRATION_SYS_ID = "integration-sys-id"
_USERS = {OWNER_USER: OWNER_SYS_ID, INTEGRATION_USER: INTEGRATION_SYS_ID}


def _parse_encoded_query(query: str) -> Dict[str, str]:
    """'a=1^b=2^ORDERBYx' -> {'a': '1', 'b': '2'} (ORDERBY ignored)."""
    terms = {}
    for part in query.split("^"):
        if "=" in part and not part.startswith("ORDERBY"):
            key, value = part.split("=", 1)
            terms[key] = value
    return terms


class FakeServiceNow:
    """Holds fake state; start() serves it on 127.0.0.1 with a random port."""

    def __init__(self) -> None:
        self.incidents: Dict[str, dict] = {}
        self.journal: List[dict] = []
        self.token_requests = 0
        self.post_count = 0
        self.fail_next_post_status: Optional[int] = None    # rejected, nothing created
        self.fail_after_create_status: Optional[int] = None  # created, then error returned
        self.garble_next_post = False                          # created, then non-JSON 200
        self.drop_next_post_response = False                   # created, then connection closed
        self.override_assignee: Optional[str] = None
        self.journal_forbidden = False
        self._server: Optional[ThreadingHTTPServer] = None

    # ---- helpers used by tests -------------------------------------------
    @property
    def base_url(self) -> str:
        assert self._server is not None
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def add_journal_entry(self, sys_id: str, author: str, value: str, at: str) -> None:
        self.journal.append({"element_id": sys_id, "sys_created_by": author,
                             "value": value, "sys_created_on": at,
                             "element": "work_notes"})

    def human_update(self, sys_id: str, author: str, at: str, state: str = "2",
                     assigned_to: Optional[str] = None) -> None:
        inc = self.incidents[sys_id]
        changes = {"sys_updated_by": author, "sys_updated_on": at, "state": state}
        if assigned_to is not None:
            changes["assigned_to"] = assigned_to
        self.incidents[sys_id] = {**inc, **changes}

    def add_foreign_incident(self, correlation_id: str, created_by: str = "other.team") -> str:
        sys_id = uuid.uuid4().hex
        self.incidents[sys_id] = {"sys_id": sys_id, "number": "INC9999999",
                                  "correlation_id": correlation_id, "assigned_to": "x",
                                  "sys_created_by": created_by, "sys_updated_by": created_by,
                                  "sys_created_on": "2026-10-05 09:00:00",
                                  "sys_updated_on": "2026-10-05 09:00:00", "state": "1"}
        return sys_id

    # ---- lifecycle ----------------------------------------------------------
    def _create(self, body: dict, created_on: str = "2026-10-05 10:00:00") -> dict:
        sys_id = uuid.uuid4().hex
        record = {**body, "sys_id": sys_id,
                  "number": f"INC{1000 + len(self.incidents):07d}",
                  "state": "1", "sys_created_by": INTEGRATION_USER,
                  "sys_updated_by": INTEGRATION_USER,
                  "sys_created_on": created_on, "sys_updated_on": created_on}
        if self.override_assignee is not None:
            record["assigned_to"] = self.override_assignee
        self.incidents[sys_id] = record
        return record

    def start(self) -> "FakeServiceNow":
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # silence test output
                return

            def _send(self, status: int, body) -> None:
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _authorized(self) -> bool:
                return self.headers.get("Authorization") == "Bearer fake-token"

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode()
                path = urlparse(self.path).path
                if path == "/oauth_token.do":
                    fake.token_requests += 1
                    form = {k: v[0] for k, v in parse_qs(raw).items()}
                    ok = (form.get("grant_type") == "client_credentials"
                          and form.get("client_id") == CLIENT_ID
                          and form.get("client_secret") == CLIENT_SECRET)
                    if not ok:
                        return self._send(401, {"error": "server_error",
                                                "error_description": "access_denied"})
                    return self._send(200, {"access_token": "fake-token",
                                            "token_type": "Bearer", "expires_in": 1800})
                if not self._authorized():
                    return self._send(401, {"error": {"message": "User is not authenticated"}})
                if path == "/api/now/table/incident":
                    fake.post_count += 1
                    if fake.fail_next_post_status is not None:
                        status, fake.fail_next_post_status = fake.fail_next_post_status, None
                        return self._send(status, {"error": {"message": "boom"}})
                    record = fake._create(json.loads(raw))
                    if fake.fail_after_create_status is not None:
                        status, fake.fail_after_create_status = fake.fail_after_create_status, None
                        return self._send(status, b"<html>Bad Gateway</html>")
                    if fake.garble_next_post:
                        fake.garble_next_post = False
                        return self._send(200, b"<html>instance waking up</html>")
                    if fake.drop_next_post_response:
                        fake.drop_next_post_response = False
                        self.close_connection = True
                        return  # created, but the client never hears back
                    return self._send(201, {"result": record})
                return self._send(404, {"error": {"message": "not found"}})

            def do_GET(self):
                if not self._authorized():
                    return self._send(401, {"error": {"message": "User is not authenticated"}})
                url = urlparse(self.path)
                params = {k: v[0] for k, v in parse_qs(url.query).items()}
                terms = _parse_encoded_query(params.get("sysparm_query", ""))
                if url.path == "/api/now/table/sys_user":
                    name = terms.get("user_name")
                    if name in _USERS:
                        return self._send(200, {"result": [{"sys_id": _USERS[name],
                                                            "user_name": name}]})
                    return self._send(200, {"result": []})
                if url.path == "/api/now/table/incident":
                    rows = [r for r in fake.incidents.values()
                            if all(str(r.get(k)) == v for k, v in terms.items())]
                    rows.sort(key=lambda r: r.get("sys_created_on", ""))
                    limit = int(params.get("sysparm_limit", "100"))
                    return self._send(200, {"result": rows[:limit]})
                if url.path.startswith("/api/now/table/incident/"):
                    sys_id = url.path.rsplit("/", 1)[-1]
                    if sys_id not in fake.incidents:
                        return self._send(404, {"error": {"message": "No Record found"}})
                    return self._send(200, {"result": fake.incidents[sys_id]})
                if url.path == "/api/now/table/sys_journal_field":
                    if fake.journal_forbidden:
                        return self._send(403, {"error": {"message": "ACL"}})
                    sys_id = terms.get("element_id", "")
                    rows = [j for j in fake.journal if j["element_id"] == sys_id]
                    return self._send(200, {"result": rows})
                return self._send(404, {"error": {"message": "not found"}})

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()

"""Local read-only case panel server: localhost only, whitelisted files, cached data."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from prooflab.servicenow.serve import make_server

CASES = [{"schema": "ifabric.servicenow.case/v1", "finding_id": "ifabric:x"}]


@pytest.fixture()
def server():
    calls = []

    def load():
        calls.append(1)
        return CASES

    srv = make_server(load, port=0, cache_seconds=60)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    host, port = srv.server_address[:2]
    yield f"http://{host}:{port}", calls
    srv.shutdown()
    srv.server_close()


def get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, dict(response.headers), response.read().decode()


def status_of(url, method="GET"):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=method), timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as err:
        return err.code


def test_index_and_assets_are_served_with_security_headers(server):
    base, _ = server
    status, headers, body = get(base + "/")
    assert status == 200 and "ifabric-case-panel.js" in body
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert get(base + "/ifabric-case-panel.js")[1]["Content-Type"].startswith("text/javascript")
    assert get(base + "/ifabric-case-panel.css")[1]["Content-Type"].startswith("text/css")


def test_cases_json_is_served_and_cached(server):
    base, calls = server
    assert json.loads(get(base + "/cases.json")[2]) == CASES
    get(base + "/cases.json")
    assert len(calls) == 1


def test_only_whitelisted_paths_and_get_are_allowed(server):
    base, _ = server
    assert status_of(base + "/../cli.py") == 404
    assert status_of(base + "/serve.py") == 404
    assert status_of(base + "/cases.json", method="POST") == 405
    assert status_of(base + "/cases.json", method="DELETE") == 405


def test_loader_failure_returns_503_not_a_crash():
    def broken():
        raise RuntimeError("boom")
    srv = make_server(broken, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    host, port = srv.server_address[:2]
    try:
        assert status_of(f"http://{host}:{port}/cases.json") == 503
    finally:
        srv.shutdown()
        srv.server_close()


def test_non_loopback_bind_is_refused():
    with pytest.raises(ValueError, match="loopback"):
        make_server(lambda: [], host="0.0.0.0", port=0)


def test_foreign_host_header_is_rejected(server):
    base, _ = server
    request = urllib.request.Request(base + "/cases.json", headers={"Host": "attacker.example"})
    try:
        urllib.request.urlopen(request, timeout=5)
        status = 200
    except urllib.error.HTTPError as err:
        status = err.code
    assert status == 403

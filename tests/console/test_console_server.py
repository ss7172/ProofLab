"""Zero-trust controls of the console (07 section 3): each one is a test."""
import json
import os
import re

import pytest

from prooflab.console import server as srv
from prooflab.console import sources as S
from prooflab.console.sources import ConsoleRefusal

import conftest as C


def test_refuses_public_bind():
    for host in ("0.0.0.0", "192.168.1.5", "example.com", ""):
        with pytest.raises(ConsoleRefusal):
            srv.make_server(host, 0, S.FixturesSource(C.PLAN))


def test_host_allow_list_anti_rebinding(fixtures_client):          # AT-08
    c = fixtures_client
    st, _, _ = c.get("/api/v1/pack", host="evil.example")
    assert st == 403
    st, _, _ = c.get("/", host="evil.example:%d" % c.port)
    assert st == 403
    assert c.get("/api/v1/pack", host="localhost:%d" % c.port)[0] == 200


def test_api_needs_session_cookie(fixtures_client):                 # AT-08
    c = fixtures_client
    assert c.get("/api/v1/pack", cookie=False)[0] == 401
    assert c.get("/api/v1/cases", cookie=False)[0] == 401
    assert c.get("/api/v1/pack", headers={"Cookie": "plsession=guess"}, cookie=False)[0] == 401
    st, hd, body = c.get("/", cookie=False)                        # static is public and carries no data
    assert st == 200 and b"loading" in body


def test_one_time_token_single_use():
    server = C.start(S.FixturesSource(C.PLAN))
    try:
        c = C.Client(server)
        assert c.request("POST", "/api/v1/session", body={"token": "wrong"}, cookie=False)[0] == 401
        st, hd, _ = c.request("POST", "/api/v1/session", body={"token": server.token}, cookie=False)
        assert st == 200
        flags = hd["set-cookie"]
        assert "HttpOnly" in flags and "SameSite=Strict" in flags and "Path=/" in flags and "Max-Age=28800" in flags
        assert c.request("POST", "/api/v1/session", body={"token": server.token}, cookie=False)[0] == 401
    finally:
        server.shutdown(); server.server_close()


def test_session_post_rejects_foreign_origin():                      # CSRF on the one POST we allow
    server = C.start(S.FixturesSource(C.PLAN))
    try:
        c = C.Client(server)
        st, _, _ = c.request("POST", "/api/v1/session", body={"token": server.token}, cookie=False,
                             headers={"Origin": "http://evil.example"})
        assert st == 403
        assert not server.token_used
    finally:
        server.shutdown(); server.server_close()


def test_pack_mode_is_get_only(pack_client):                        # AT-08
    c = pack_client
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        st, hd, _ = c.request(method, "/api/v1/answer", body={"x": 1})
        assert st == 405, method
    assert c.request("POST", "/api/v1/actions", body={})[0] == 405


def test_security_headers(fixtures_client):                         # AT-07
    c = fixtures_client
    for path in ("/", "/api/v1/pack"):
        st, hd, _ = c.get(path)
        assert st == 200
        assert hd["content-security-policy"] == srv.CSP
        for needle in ("default-src 'none'", "script-src 'self'", "style-src 'self'", "frame-ancestors 'none'",
                       "base-uri 'none'", "connect-src 'self'"):
            assert needle in hd["content-security-policy"]
        assert hd["x-content-type-options"] == "nosniff"
        assert hd["referrer-policy"] == "no-referrer"
        assert hd["cross-origin-opener-policy"] == "same-origin"
        assert hd["cross-origin-resource-policy"] == "same-origin"
        assert "camera=()" in hd["permissions-policy"]
    assert c.get("/api/v1/pack")[1]["cache-control"] == "no-store"
    html = c.get("/")[2].decode()
    assert not re.search(r"<script(?![^>]*\bsrc=)", html) and "style=" not in html and "onclick=" not in html


def test_static_has_no_inline_or_remote_loads():
    base = srv.STATIC_DIR
    html = open(os.path.join(base, "index.html"), encoding="utf-8").read()
    assert "http://" not in html and "https://" not in html
    css = open(os.path.join(base, "app.css"), encoding="utf-8").read()
    assert "@import" not in css and "http" not in css
    js = open(os.path.join(base, "app.js"), encoding="utf-8").read()
    for bad in ("innerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "localStorage"):
        assert bad not in js


def test_static_path_traversal(fixtures_client):
    c = fixtures_client
    for p in ("/static/../server.py", "/static/%2e%2e/server.py", "/static/..%2fserver.py", "/static//etc/passwd",
              "/static/panel/../../sources.py"):
        st, _, body = c.get(p)
        assert st == 404 and b"def " not in body


def test_unknown_paths_404(fixtures_client):
    assert fixtures_client.get("/api/v1/nope")[0] == 404
    assert fixtures_client.get("/elsewhere")[0] == 404


def test_rate_limit_20_per_second(fixtures_client):
    c = fixtures_client
    seen = [c.get("/api/v1/integrity") for _ in range(60)]
    limited = [r for r in seen if r[0] == 429]
    assert limited and limited[0][1].get("retry-after") == "1"
    assert seen[0][0] == 200


def test_request_limits(fixtures_client):
    c = fixtures_client
    assert c.get("/api/v1/ask?q=" + "a" * 3000)[0] == 414
    server = C.start(S.FixturesSource(C.PLAN))
    try:
        d = C.Client(server)
        st, _, _ = d.request("POST", "/api/v1/session", body=json.dumps({"token": "x" * 20000}), cookie=False)
        assert st == 413
    finally:
        server.shutdown(); server.server_close()


def test_refuses_secret_env():
    key = "AWS_" + "SECRET_" + "ACCESS_KEY"
    for name in ("SNOW_CLIENT_SECRET", "MODAAS_API_KEY", "AUDIT_WRITE_TOKEN", key, "AWS_" + "SESSION_" + "TOKEN",
                 "SNOW_CLIENT_ID", "MCP_TOKEN"):
        with pytest.raises(ConsoleRefusal) as ei:
            srv.check_clean_env({name: "value-not-shown"})
        assert name in str(ei.value) and "value-not-shown" not in str(ei.value)
    srv.check_clean_env({"PATH": "/usr/bin", "AWS_REGION": "us-east-1", "SNOW_INSTANCE": ""})


def test_main_refuses_secret_env_exit_code(monkeypatch):
    monkeypatch.setenv("SNOW_CLIENT_SECRET", "x")
    assert srv.main(["--data", "fixtures", "--port", "0"]) == 2


def test_access_log_has_no_query_values(fixtures_client):
    c = fixtures_client
    c.get("/api/v1/raw?ref=raw:secret-looking-value")
    assert not any("secret-looking-value" in line for line in c.server.access_log)
    assert not any("plsession" in line for line in c.server.access_log)


def test_main_exposes_dispatcher_entry():
    assert callable(srv.main)

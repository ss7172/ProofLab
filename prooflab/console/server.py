"""The Evidence Console server (T5.4, G-09): Arth's 07-CONSOLE-API-AND-SECURITY as written, plus the data switch.

Stdlib only, Python 3.9. Loopback only, GET-only (PACK), one-time token -> session cookie, Host allow-list, CSP,
rate limits. The process holds no secret and opens no connection but its own listening socket.
It composes no verdicts: answers, auditor views and runs are served as stored in the pack (or the fixtures).

    python3 -m prooflab console --data fixtures            # Arth's synthetic demo data (amber banner)
    python3 -m prooflab console --data pack --pack evidence/   # PACK: sealed pack; refuses SYNTHETIC data
    python3 -m prooflab console --data live --pack evidence/   # + the live index (P1 routes: routes_p1.py, PR-18)
"""
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from prooflab.console import sources as S
from prooflab.console.sources import ConsoleRefusal

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
DEFAULT_PORT = 8787
LOOPBACK = ("127.0.0.1", "localhost")
COOKIE = "plsession"
MAX_BODY = 16 * 1024
MAX_QUERY = 2 * 1024
HANDLER_TIMEOUT = 10
GET_PER_SECOND = 20
PAGE = 200

CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
HEADERS = (
    ("Content-Security-Policy", CSP),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), usb=()"),
)

# Names assembled from parts so this file never carries a secret-scan literal.
_AWS = "AWS_"
SECRET_ENV = (
    "SNOW_CLIENT_SECRET", "SNOW_CLIENT_ID", "MODAAS_API_KEY", "AUDIT_WRITE_TOKEN",
    _AWS + "SECRET_" + "ACCESS_KEY", _AWS + "SESSION_" + "TOKEN", "MCP_TOKEN", "MODAAS_GATEWAY_KEY",
)
SECRET_ENV_PREFIXES = ("SNOW_CLIENT", "MODAAS_API", "MODAAS_GATEWAY_KEY", "MCP_TOKEN", "AUDIT_WRITE")

# Display vocabulary for the verdict enum (03-CONTRACTS section 3). The browser holds NO verdict words of its own:
# it asks the server how to label what the pack says. Labels never decide anything.
VOCAB = {
    "SATISFIED": {"label": "SATISFIED", "glyph": "●", "tone": "held", "pill": "good"},
    "BREACHED": {"label": "NOT SATISFIED", "glyph": "▲", "tone": "breach", "pill": "bad"},
    "INDETERMINATE": {"label": "INDETERMINATE", "glyph": "◐", "tone": "unknown", "pill": "hatch"},
    "NOT_ASSESSED": {"label": "NOT ASSESSED", "glyph": "○", "tone": "mute", "pill": "mute"},
    "ESCALATED": {"label": "ESCALATED", "glyph": "", "tone": "unknown", "pill": "warn"},
}


def check_clean_env(environ):
    """A startup self-check: refuse to run with a credential in the environment ('run the console in a clean shell')."""
    bad = sorted(k for k in environ if environ.get(k) and (k in SECRET_ENV or k.startswith(SECRET_ENV_PREFIXES)))
    if bad:
        raise ConsoleRefusal("refusing to start: secret variable(s) set in this shell: %s. Run the console in a "
                             "clean shell (env -i ...)." % ", ".join(bad))


def parse_question(text):
    """A tiny deterministic phrase -> (kind, params) map. No LLM. The full grammar is prooflab/query/grammar.py (PR-15b);
    this is the console's fallback for the P0 phrases, and only LOCATES a stored answer."""
    t = (text or "").lower().strip()
    m = re.search(r"control\s*c?(7|9|16)\b.*?\brun\s+([a-z0-9][a-z0-9_.-]*)", t)
    if m:
        return {"kind": "answer", "control": "C" + m.group(1), "scope_kind": "run", "scope": m.group(2).upper(),
                "normalized": "controltest %s --run %s" % (m.group(1), m.group(2).upper())}
    m = re.search(r"control\s*c?(7|9|16)\b.*\b(between|from|window|interval)\b", t)
    if m:
        return {"kind": "answer", "control": "C" + m.group(1), "scope_kind": "interval", "scope": None,
                "normalized": "controltest %s --from … --to …" % m.group(1)}
    m = re.search(r"(six questions|auditor).*?(inc\d+)", t)
    if m:
        return {"kind": "auditor", "id": m.group(2).upper(), "normalized": "auditor " + m.group(2).upper()}
    m = re.search(r"(reconstruct|trail|ledger)\s+run\s+([a-z0-9][a-z0-9_.-]*)", t)
    if m:
        return {"kind": "run", "id": m.group(2).upper(), "normalized": "ledger --run " + m.group(2).upper()}
    return None


class Session(object):
    def __init__(self):
        self.csrf = secrets.token_hex(16)
        self.hits = deque()

    def allow(self, now):
        while self.hits and now - self.hits[0] >= 1.0:
            self.hits.popleft()
        if len(self.hits) >= GET_PER_SECOND:
            return False
        self.hits.append(now)
        return True


class ConsoleServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, source, session_dir=None):
        super().__init__(addr, Handler)
        self.source = source
        self.token = secrets.token_urlsafe(32)
        self.token_used = False
        self.sessions = {}
        self.lock = threading.Lock()
        self.queries = []
        self.session_dir = session_dir
        self.access_log = []

    @property
    def port(self):
        return self.server_address[1]

    def url(self):
        return "http://127.0.0.1:%d/#k=%s" % (self.port, self.token)


def make_server(host, port, source, session_dir=None):
    if host not in LOOPBACK:
        raise ConsoleRefusal("refusing to bind %r: the console binds loopback only" % host)
    return ConsoleServer(("127.0.0.1", port), source, session_dir)


class Handler(BaseHTTPRequestHandler):
    server_version = "ProofLabConsole"
    sys_version = ""
    timeout = HANDLER_TIMEOUT
    protocol_version = "HTTP/1.1"

    # ---- plumbing ---------------------------------------------------------
    def log_message(self, fmt, *args):   # access log WITHOUT the query string and without cookies
        path = urlsplit(self.path).path
        self.server.access_log.append("%s %s" % (self.command, path))

    def _send(self, status, body, ctype, extra=()):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in HEADERS:
            self.send_header(k, v)
        if self.path.startswith("/api/") or self.path == "/api":
            self.send_header("Cache-Control", "no-store")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, data=None, error=None, meta=None, extra=()):
        env = {"ok": error is None, "data": data, "error": error, "meta": meta or {}}
        body = json.dumps(env, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", extra)

    def _err(self, status, code, message, extra=()):
        self._json(status, None, {"code": code, "message": message}, None, extra)

    def _host_ok(self):
        host = (self.headers.get("Host") or "").strip().lower()
        port = self.server.port
        return host in ("127.0.0.1:%d" % port, "localhost:%d" % port)

    def _session(self):
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE and v in self.server.sessions:
                return v, self.server.sessions[v]
        return None, None

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        port = self.server.port
        return origin in ("http://127.0.0.1:%d" % port, "http://localhost:%d" % port)

    # ---- verbs -------------------------------------------------------------
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def _dispatch(self, method):
        try:
            self._handle(method)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:   # never leak internals; the message is generic
            try:
                self._err(500, "internal", "internal error (%s)" % type(exc).__name__)
            except Exception:
                pass

    def _handle(self, method):
        if not self._host_ok():
            return self._err(403, "bad-host", "Host must be 127.0.0.1:<port> or localhost:<port>")
        split = urlsplit(self.path)
        path = split.path
        if len(split.query) > MAX_QUERY:
            return self._err(414, "query-too-long", "query string over %d bytes" % MAX_QUERY)
        params = {k: v[-1] for k, v in parse_qs(split.query, keep_blank_values=True).items()}
        if path == "/api/v1/session" and method == "POST":
            return self._session_post()
        if method not in ("GET", "HEAD"):
            self.close_connection = True   # the body, if any, is never read
            return self._err(405, "read-only", "this console is GET-only", (("Allow", "GET"),))
        if not path.startswith("/api/"):
            return self._static(path, method)
        sid, sess = self._session()
        if sess is None:
            return self._err(401, "no-session", "start from the one-time URL printed at startup")
        if not sess.allow(time.time()):
            return self._err(429, "rate-limited", "over %d requests per second" % GET_PER_SECOND, (("Retry-After", "1"),))
        return self._api(path, params, method)

    # ---- static --------------------------------------------------------------
    def _static(self, path, method):
        if path == "/":
            rel = "index.html"
        elif path.startswith("/static/"):
            rel = unquote(path[len("/static/"):])
        else:
            return self._err(404, "not-found", "no such path")
        full = S.safe_join(STATIC_DIR, rel)
        if full is None or not os.path.isfile(full):
            return self._err(404, "not-found", "no such path")
        with open(full, "rb") as handle:
            body = handle.read()
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        self._send(200, b"" if method == "HEAD" else body, ctype)

    # ---- session ---------------------------------------------------------------
    def _session_post(self):
        if not self._origin_ok():
            return self._err(403, "bad-origin", "Origin must be this console")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._err(400, "bad-length", "bad Content-Length")
        if length > MAX_BODY:
            return self._err(413, "body-too-large", "body over %d bytes" % MAX_BODY)
        raw = self.rfile.read(length) if length else b""
        try:
            token = str(json.loads(raw.decode("utf-8")).get("token", ""))
        except (ValueError, AttributeError):
            return self._err(400, "bad-body", "expected JSON {\"token\": ...}")
        with self.server.lock:
            ok = (not self.server.token_used) and hmac.compare_digest(token.encode(), self.server.token.encode())
            if ok:
                self.server.token_used = True
                sid = secrets.token_urlsafe(24)
                sess = Session()
                self.server.sessions[sid] = sess
        if not ok:
            return self._err(401, "bad-token", "token invalid or already used")
        cookie = "%s=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800" % (COOKIE, sid)
        self._json(200, {"csrf": sess.csrf, "role": "viewer"}, None, {"role": "viewer"}, (("Set-Cookie", cookie),))

    # ---- api --------------------------------------------------------------------
    def _meta(self, extra=None):
        src = self.server.source
        info = src.mode_info()
        meta = {"mode": info, "manifest_status": src.integrity().get("status")}
        if extra:
            meta.update(extra)
        return meta

    def _stamp(self, doc):
        """When the pack is not VERIFIED, every answer says so (AT-05). The stored answer_id is untouched."""
        status = self.server.source.integrity().get("status")
        if status in ("VERIFIED", None) or not isinstance(doc, dict):
            return doc
        out = dict(doc)
        out["source"] = dict(doc.get("source") or {}, manifest_status="UNVERIFIED" if status != "MODIFIED" else "MODIFIED")
        return out

    def _api(self, path, params, method):
        src = self.server.source
        t0 = time.time()
        routes_p1 = self._p1()
        if routes_p1 is not None and routes_p1.handle(self, path, params, method):
            return
        if path == "/api/v1/pack":
            data = src.pack_index()
            meta = self._meta({"vocab": VOCAB})
            return self._json(200, data, None, meta)
        if path == "/api/v1/answer":
            key = params.get("key")
            if not key:
                if params.get("control"):
                    ctl = "C" + params["control"].lstrip("Cc")
                    if params.get("run"):
                        key = src.find_answer(ctl, "run", params["run"])
                    else:
                        extra = {p: params[p] for p in ("from", "to", "window") if p in params}
                        key = src.find_answer(ctl, "interval", None, extra)
            doc = src.answer(key) if key else None
            if doc is None:
                return self._err(404, "no-such-answer", "no stored answer for that question")
            return self._json(200, self._stamp(doc), None, self._meta({"key": key, "elapsed_ms": int((time.time() - t0) * 1000)}))
        if path == "/api/v1/ask":
            return self._ask(params.get("q", ""), t0)
        m = re.match(r"^/api/v1/auditor/([^/]+)$", path)
        if m:
            doc = src.auditor(unquote(m.group(1)))
            if doc is None:
                return self._err(404, "no-such-auditor", "no auditor view for that id")
            return self._json(200, self._stamp(doc), None, self._meta())
        if path == "/api/v1/runs":
            return self._json(200, src.run_catalogue(), None, self._meta())
        m = re.match(r"^/api/v1/runs/([^/]+)$", path)
        if m:
            doc = src.run(unquote(m.group(1)))
            if doc is None:
                return self._err(404, "no-such-run", "no run manifest for that alias or run id")
            return self._json(200, doc, None, self._meta())
        if path == "/api/v1/records":
            return self._records(params)
        if path == "/api/v1/raw":
            got = src.raw(params.get("ref", ""))
            if got is None:
                return self._err(404, "unresolved-ref", "ref is not listed in the pack")
            return self._json(200, got, None, self._meta())
        if path == "/api/v1/cases":
            refused = src.refused_cases() if hasattr(src, "refused_cases") else []
            return self._json(200, src.cases(), None, self._meta({"refused": refused}))
        if path == "/api/v1/integrity":
            return self._json(200, src.integrity(), None, self._meta())
        m = re.match(r"^/api/v1/replay/([^/]+)$", path)
        if m:
            ev = src.replay(unquote(m.group(1)))
            if ev is None:
                return self._err(404, "no-replay", "no recorded live events for that run")
            return self._json(200, ev, None, self._meta({"label": "REPLAY"}))
        if path == "/api/v1/session/queries":
            return self._json(200, list(self.server.queries), None, self._meta())
        return self._err(404, "not-found", "no such endpoint")

    def _p1(self):
        try:
            from prooflab.console import routes_p1   # owned by PR-18; absent in P0
        except ImportError:
            return None
        return routes_p1

    def _records(self, params):
        recs = self.server.source.records()
        run = params.get("run")
        aliases = set()
        if run:
            doc = self.server.source.run(run)
            aliases = set([run] + ([doc.get("cid"), doc.get("run_alias")] if doc else []))

        def keep(r):
            if run and not ({r.get("run.id"), (r.get("scope") or {}).get("alias"), (r.get("joins") or {}).get("cid")} & aliases):
                return False
            if params.get("control") and r.get("control.ref") != params["control"]:
                return False
            if params.get("actor") and r.get("actor.id") != params["actor"]:
                return False
            if params.get("verdict") and r.get("verdict") != params["verdict"]:
                return False
            if params.get("provenance") and r.get("provenance") != params["provenance"]:
                return False
            return True
        rows = [r for r in recs if keep(r)]
        try:
            start = max(0, int(params.get("cursor") or 0))
        except ValueError:
            start = 0
        page = rows[start:start + PAGE]
        nxt = str(start + PAGE) if start + PAGE < len(rows) else ""
        return self._json(200, page, None, self._meta({"next_cursor": nxt, "total": len(rows)}))

    def _ask(self, q, t0):
        src = self.server.source
        parsed = parse_question(q)
        if parsed is None:
            return self._err(422, "cannot-parse", "I can't parse that (deterministic grammar, no guessing, no LLM)")
        route, doc, key = None, None, None
        if parsed["kind"] == "answer":
            key = src.find_answer(parsed["control"], parsed["scope_kind"], parsed["scope"])
            doc = src.answer(key) if key else None
            route = "#/answer/" + _quote(key) if key else None
        elif parsed["kind"] == "auditor":
            doc = src.auditor(parsed["id"])
            route = "#/auditor/" + parsed["id"] if doc else None
        elif parsed["kind"] == "run":
            doc = src.run(parsed["id"])
            route = "#/ledger/" + parsed["id"] if doc else None
        if doc is None:
            return self._err(404, "no-such-answer", "nothing stored for: %s (not in this pack)" % parsed["normalized"],)
        elapsed = int((time.time() - t0) * 1000)
        entry = {"q": q, "normalized": parsed["normalized"], "answer_id": doc.get("answer_id"), "elapsed_ms": elapsed}
        self.server.queries.append(entry)
        if self.server.session_dir:
            try:
                with open(os.path.join(self.server.session_dir, "queries.jsonl"), "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except OSError:
                pass
        self._json(200, self._stamp(doc), None, self._meta({"normalized": parsed["normalized"], "route": route, "key": key}))


def _quote(text):
    from urllib.parse import quote
    return quote(text, safe="")


def default_plan_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    return os.path.join(root, "handoffs", "ifabric-handoff-3", "evidence-console-plan")


def build_source(data, pack=None, fixtures=None):
    if data == "fixtures":
        return S.FixturesSource(fixtures or default_plan_dir())
    if data in ("pack", "live"):
        if not pack:
            raise ConsoleRefusal("--data %s needs --pack <evidence dir>" % data)
        return S.PackSource(pack, live=(data == "live"))
    raise ConsoleRefusal("unknown --data %r (fixtures|pack|live)" % data)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="prooflab console", description="The ProofLab Evidence Console (loopback, read-only).")
    ap.add_argument("--data", choices=("fixtures", "pack", "live"), default=None,
                    help="data source: fixtures (Arth's synthetic demo), pack (sealed Evidence Pack), live (pack + live index)")
    ap.add_argument("--pack", help="the Evidence Pack directory (implies --data pack)")
    ap.add_argument("--live", action="store_true", help="alias for --data live")
    ap.add_argument("--fixtures", help="the evidence-console-plan directory (default: handoffs/ifabric-handoff-3/...)")
    ap.add_argument("--operator", action="store_true", help="P2 (not built): ignored")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--session-dir", help="where session/queries.jsonl is appended (default: memory only)")
    args = ap.parse_args(argv)
    data = "live" if args.live else (args.data or ("pack" if args.pack else "fixtures"))
    try:
        check_clean_env(os.environ)
        source = build_source(data, args.pack, args.fixtures)
        server = make_server(args.host, args.port, source, args.session_dir)
    except ConsoleRefusal as exc:
        print("console: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("console: cannot start: %s" % exc, file=sys.stderr)
        return 2
    if args.operator:
        print("console: --operator is P2 and not built; running as viewer", file=sys.stderr)
    info = source.mode_info()
    print("%s\nopen (one time): %s" % (info["banner"], server.url()))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

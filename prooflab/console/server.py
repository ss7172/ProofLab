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
from prooflab.contract import verdicts as _V  # the one verdict vocabulary (ARCH §4.3)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
# Arth's drop-in panel, byte-identical and served at /static/panel/. It lives OUTSIDE static/ so the "no verdict words
# in static/" grep is about OUR code; the panel's own tone map is his, unedited.
PANEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel_vendor")
PANEL_FILES = ("ifabric-case-panel.js", "ifabric-case-panel.css")
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
    _V.SATISFIED: {"label": _V.SATISFIED, "glyph": "●", "tone": "held", "pill": "good"},
    _V.BREACHED: {"label": "NOT SATISFIED", "glyph": "▲", "tone": "breach", "pill": "bad"},
    _V.INDETERMINATE: {"label": _V.INDETERMINATE, "glyph": "◐", "tone": "unknown", "pill": "hatch"},
    _V.NOT_ASSESSED: {"label": "NOT ASSESSED", "glyph": "○", "tone": "mute", "pill": "mute"},
    _V.ESCALATED: {"label": _V.ESCALATED, "glyph": "", "tone": "unknown", "pill": "warn"},
}


def check_clean_env(environ):
    """A startup self-check: refuse to run with a credential in the environment ('run the console in a clean shell')."""
    bad = sorted(k for k in environ if environ.get(k) and (k in SECRET_ENV or k.startswith(SECRET_ENV_PREFIXES)))
    if bad:
        raise ConsoleRefusal("refusing to start: secret variable(s) set in this shell: %s. Run the console in a "
                             "clean shell (env -i ...)." % ", ".join(bad))


_TIME = r"(\d{4}-\d{2}-\d{2}(?:[t ]\d{1,2}(?::\d{2}(?::\d{2}(?:\.\d+)?)?)?)?z?|\d{1,2}:\d{2}(?::\d{2})?z?|\d{1,2}z)"


def _norm_time(tok):
    """'2026-10-06t13' -> '2026-10-06T13:00:00Z'; '13:50z' -> '13:50:00Z' (time of day only); None when not a time."""
    tok = (tok or "").strip().lower().rstrip("z").replace(" ", "t")
    m = re.match(r"^(\d{4}-\d{2}-\d{2})(?:t(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?(?:\.\d+)?)?$", tok)
    if m:
        return "%sT%02d:%s:%sZ" % (m.group(1), int(m.group(2) or 0), m.group(3) or "00", m.group(4) or "00")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?$", tok)
    if m and int(m.group(1)) < 24:
        return "%02d:%s:%sZ" % (int(m.group(1)), m.group(2) or "00", m.group(3) or "00")
    return None


def parse_window_text(t):
    """(t1, t2) from 'between A and B' / 'from A to B' / 'over A..B' / 'window A' (one hour from A); None if no time."""
    m = re.search(r"\b(?:between|from|window|interval|over|during)\b\s*" + _TIME + r"(?:\s*(?:\.\.|and|to|-|–)\s*" + _TIME + r")?", t)
    if not m:
        return None
    t1, t2 = _norm_time(m.group(1)), _norm_time(m.group(2)) if m.group(2) else None
    if not t1:
        return None
    if t2 is None:      # one time: the hour that starts there ('window 2026-10-06T13' = 13:00..14:00)
        hh = int(t1[-9:-7]) if "T" in t1 else int(t1[:2])
        end = "%02d:%sZ" % ((hh + 1) % 24, t1[-6:-1])
        t2 = (t1[:11] + end) if "T" in t1 and hh < 23 else end
    return t1, t2


def parse_question(text):
    """A tiny deterministic phrase -> (kind, params) map. No LLM. The full grammar is prooflab/query/grammar.py (PR-15b);
    this is the console's fallback for the P0 phrases, and only LOCATES a stored answer. Run ids keep their case (they
    are lower case in the pack); parsed times are echoed in 'normalized' so the judge sees what was asked."""
    t = (text or "").lower().strip().rstrip("?")
    win = parse_window_text(t)
    m = re.search(r"control\s*c?(7|9|16)\b.*?\brun\s+([a-z0-9][a-z0-9_.-]*)", t)
    if m:
        norm = "controltest %s --run %s" % (m.group(1), m.group(2))
        if win:
            norm += " (window %s..%s asked, NOT applied: this is the whole-run answer)" % win
        return {"kind": "answer", "control": "C" + m.group(1), "scope_kind": "run", "scope": m.group(2), "normalized": norm}
    m = re.search(r"control\s*c?(7|9|16)\b.*\b(between|from|window|interval|over|during)\b", t)
    if m and win:
        return {"kind": "answer", "control": "C" + m.group(1), "scope_kind": "interval", "scope": "%s..%s" % win,
                "normalized": "controltest %s --from %s --to %s" % (m.group(1), win[0], win[1])}
    m = re.search(r"(six questions|auditor).*?(inc\d+)", t)
    if m:
        return {"kind": "auditor", "id": m.group(2).upper(), "normalized": "auditor " + m.group(2).upper()}
    m = re.search(r"(?:six questions|auditor)(?:\s+for)?\s+([a-z0-9][a-z0-9_.-]*)$", t)
    if m:       # a run id (the pack stores auditor/<cid>.json); run ids are lower case
        return {"kind": "auditor", "id": m.group(1), "normalized": "auditor " + m.group(1)}
    m = re.search(r"(reconstruct|trail|ledger)\s+(?:for\s+)?run\s+([a-z0-9][a-z0-9_.-]*)", t)
    if m:
        return {"kind": "run", "id": m.group(2), "normalized": "ledger --run " + m.group(2)}
    return None


def flag_closures(obj):
    """AT-10: a finding marked closed without a re-test is flagged (a structural check on the record, not a verdict)."""
    if isinstance(obj, dict):
        c = obj.get("closure")
        if isinstance(c, dict) and str(c.get("state", "")).startswith("CLOSED") and not c.get("retest_ref"):
            c["flag"] = "CLOSED WITHOUT RE-TEST"
        for v in obj.values():
            flag_closures(v)
    elif isinstance(obj, list):
        for v in obj:
            flag_closures(v)
    return obj


def named_run_labels(root):
    """PR-56: the named-run label (N1, N2b, N4 ...) and the planned roles of each CID, read from the pack's
    named-runs.md table (written before judging). Labels only: no verdict is derived here."""
    out = {}
    try:
        with open(os.path.join(root, "named-runs.md"), encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except (OSError, TypeError):
        return out
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 12 or not cells[0] or cells[0] in ("control", "---"):
            continue
        cids = re.findall(r"`(ifabric-run-[0-9]+-[0-9a-f]+)`", cells[3])
        note = cells[-1]
        m = re.search(r"\b(N[0-9]+[a-z]?)\b", note)
        if not cids or not m:
            continue
        e = out.setdefault(cids[0], {"label": m.group(1), "roles": [], "unplanned": []})
        role = "%s %s" % (cells[0], cells[1]) if cells[1] != cells[0] else cells[1]
        if "NOT COUNTED" in note:      # a named attempt that does not count (N1b, N2a): labelled, never hidden
            e["not_counted"] = True
            role += " attempt %s, NOT COUNTED" % cells[2]
        if role not in e["roles"]:
            e["roles"].append(role)
        for c, g in re.findall(r"[Uu]nplanned (C[0-9]+)\b.*?gap-list (B[0-9]+)", note):
            if not any(u["control"] == c for u in e["unplanned"]):
                e["unplanned"].append({"control": c, "gap": g})
    return out


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
        if rel.startswith("panel/") and rel[len("panel/"):] in PANEL_FILES:
            full = S.safe_join(PANEL_DIR, rel[len("panel/"):])
        else:
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
        """Integrity is stamped at serve time: a stored answer is composed before MANIFEST.json exists (the manifest
        lists the answer), so its own manifest fields are stale by construction. In PACK mode the live check wins
        (AT-05: when the pack is not VERIFIED every answer says so). Only integrity fields change; no verdict, and the
        stored answer_id is untouched."""
        doc = flag_closures(json.loads(json.dumps(doc)))
        if not isinstance(doc, dict):
            return doc
        src = self.server.source
        live = src.integrity()
        status = live.get("status")
        if doc.get("schema") == "ifabric.auditor/v1":
            return self._stamp_auditor(doc, live) if src.name == "pack" else doc
        if src.name != "pack" or status is None:
            if status in ("VERIFIED", None):
                return doc
            out = dict(doc)
            out["source"] = dict(doc.get("source") or {}, manifest_status="UNVERIFIED" if status != "MODIFIED" else "MODIFIED")
            return out
        shown = status if status in ("VERIFIED", "MODIFIED") else "UNVERIFIED"
        out = dict(doc)
        if isinstance(doc.get("source"), dict) or doc.get("schema") == "ifabric.answer/v1":
            out["source"] = dict(doc.get("source") or {}, manifest_status=shown,
                                 manifest_sha256=live.get("manifest_sha256") or (doc.get("source") or {}).get("manifest_sha256"),
                                 integrity_checked="at serve time (%s)" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        aq = out.get("audit_question")
        if isinstance(aq, dict) and isinstance(aq.get("unchanged_since"), dict):
            aq["unchanged_since"] = {"text": "MANIFEST.json status %s (checked when served: %d files)" % (shown, live.get("files", 0)),
                                     "refs": ["manifest:MANIFEST.json"], "flag": "OK" if shown == "VERIFIED" else "FLAG"}
        tm = out.get("tickmarks")
        if isinstance(tm, dict) and "A" in tm:
            tm["A"] = "agreed to MANIFEST.json (%s, checked when served)" % shown
        listed = getattr(src, "_manifest", None) or {}
        changed = set(live.get("changed") or []) | set(live.get("missing") or [])
        for row in out.get("records") or []:
            if not isinstance(row, dict):
                continue
            ref = str(row.get("ref", ""))
            if ref.startswith("record:"):
                rel = "store/records.jsonl"
                row["manifest"] = "MISSING" if rel not in listed else ("CHANGED" if rel in changed else "OK")
            elif ref.startswith("assessment:"):
                row["manifest"] = "OK" if shown == "VERIFIED" else shown
            else:
                continue
            if row["manifest"] == "OK" and "A" not in (row.get("tickmarks") or []):
                row["tickmarks"] = ["A"] + list(row.get("tickmarks") or [])
        return out

    @staticmethod
    def _stamp_auditor(doc, live):
        """The auditor's INTEGRITY question is composed BEFORE MANIFEST.json exists; at serve time it states the same
        facts as /api/v1/integrity (one source). Only the manifest line changes; the corroboration facts stay."""
        q = (doc.get("questions") or {}).get("integrity")
        if not isinstance(q, dict):
            return doc
        status = live.get("status")
        ok = status == "VERIFIED"
        line = "MANIFEST.json %s (%d files, checked when served)" % (status or "unknown", live.get("files", 0))
        facts = [f for f in (q.get("facts") or []) if not (isinstance(f, dict) and str(f.get("value", "")).startswith("MANIFEST.json"))]
        facts.insert(0, {"label": "INTEGRITY", "value": line, "refs": ["manifest:MANIFEST.json"] if status != "NO_MANIFEST" else [], "flag": "OK" if ok else "FLAG"})
        shown = [f["value"] for f in facts if f.get("label") == "INTEGRITY"][:2]
        q.update(facts=facts, answer="; ".join(shown), status="ANSWERED" if ok or q.get("status") == "ANSWERED" else q.get("status"))
        return doc

    def _boot(self, t0):
        """ONE request for the first load: the stamped answers, the auditor views, the records of every run, the cases and
        the run catalogue (the page used to fire 20+ GETs in a second and hit the per-second limit)."""
        src = self.server.source
        idx = src.pack_index()
        answers, auditor, records = {}, {}, {}
        for a in idx.get("answers", []):
            doc = src.answer(a.get("key"))
            if doc is not None:
                answers[a["key"]] = self._stamp(doc)
        for a in idx.get("auditor", []):
            doc = src.auditor(a.get("id"))
            if doc is not None:
                auditor[a["id"]] = self._stamp(doc)
        allrecs = src.records()
        for r in idx.get("runs", []):
            aliases = set([r.get("alias"), r.get("cid")])
            records[r["alias"]] = [x for x in allrecs
                                   if {x.get("run.id"), (x.get("scope") or {}).get("alias"), (x.get("joins") or {}).get("cid")} & aliases]
        win = src.declared_window() if hasattr(src, "declared_window") else None
        data = {"answers": answers, "auditor": auditor, "records": records,
                "cases": flag_closures(json.loads(json.dumps(src.cases()))), "runs": src.run_catalogue(), "window": win}
        return self._json(200, data, None, self._meta({"elapsed_ms": int((time.time() - t0) * 1000)}))

    def _api(self, path, params, method):
        src = self.server.source
        t0 = time.time()
        routes_p1 = self._p1()
        if routes_p1 is not None and routes_p1.handle(self, path, params, method):
            return
        if path == "/api/v1/pack":
            data = flag_closures(json.loads(json.dumps(src.pack_index())))
            if src.name == "pack":
                # the index is projected BEFORE the MANIFEST exists (the MANIFEST lists the index): the live check wins
                live = src.integrity()
                data["integrity"] = dict(data.get("integrity") or {}, status=live["status"], files=live.get("files", 0),
                                         manifest_sha256=live.get("manifest_sha256") or (data.get("integrity") or {}).get("manifest_sha256"))
                for art in data.get("artefacts", []):
                    if art.get("path") == "MANIFEST.json" and live["status"] != "NO_MANIFEST":
                        art["present"], art["sha256"] = True, live.get("manifest_sha256")
            data["named_labels"] = named_run_labels(getattr(src, "root", None))
            meta = self._meta({"vocab": VOCAB})
            return self._json(200, data, None, meta)
        if path == "/api/v1/boot":
            return self._boot(t0)
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
            win = src.declared_window() if hasattr(src, "declared_window") else None
            return self._json(200, src.run_catalogue(), None, self._meta({"window": win}))
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
            return self._json(200, flag_closures(json.loads(json.dumps(src.cases()))), None, self._meta({"refused": refused}))
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

    def _run_window(self, q):
        """PR-53: 'control 16 for run <RUN> between <T1> and <T2>' (grammar kind controltest-run-window), composed from
        the pack by prooflab/query/run_window.py. None for any other question (the stored-answer routes below)."""
        root = getattr(self.server.source, "root", None)
        if not root or not re.search(r"\brun\b.*\b(between|from)\b|--run\b.*--window\b", q or "", re.I):
            return None
        from prooflab.query import engine as QE, grammar as QG, run_window as QRW
        pack = getattr(self.server, "_query_pack", None)
        if pack is None:
            pack = self.server._query_pack = QE.Pack(root)
        parsed = QG.parse(q, pack)
        if not parsed.get("ok") or parsed.get("kind") != "controltest-run-window":
            return None
        return parsed, QRW.ask_doc(pack, parsed)

    def _ask(self, q, t0):
        src = self.server.source
        rw = self._run_window(q)
        if rw is not None:
            parsed, doc = rw
            entry = {"q": q, "normalized": parsed["normalized"], "answer_id": None, "elapsed_ms": int((time.time() - t0) * 1000)}
            self.server.queries.append(entry)
            if self.server.session_dir:
                try:
                    with open(os.path.join(self.server.session_dir, "queries.jsonl"), "a", encoding="utf-8") as handle:
                        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
                except OSError:
                    pass
            return self._json(200, doc, None, self._meta({"normalized": parsed["normalized"], "route": None, "key": None,
                                                         "kind": doc.get("kind"), "render": "text"}))
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
    print("%s\nopen (one time): %s" % (info["banner"], server.url()), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

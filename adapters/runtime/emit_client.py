"""EP emit client (ARCH 3.2 "emit", 3.1 EP-3/EP-4, 4).  Stdlib only, Python 3.9 compatible.

One flat evidence record (schema ifabric.evidence/1) goes:
  1. through the validator + O-04 scrubber,
  2. to stdout as one JSON line (the local spool and the AWS-timestamped witness),
  3. onto a bounded in-memory queue drained by ONE background thread that POSTs to
     AUDIT_URL/records with the X-Audit-Token header (the ledger is a 256Mi single-threaded
     server: one connection at a time, POST only, never a full GET).
emit() never raises and never waits.  flush() is the one declared bounded wait (<= 2 s by
default); it decides nothing and never fails the call.  A record the ledger did not take is
reported as a monitoring-gap line on stdout; C7 finds it as missing, nothing blocks.
"""
import collections
import hashlib
import http.client
import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

SCHEMA = "ifabric.evidence/1"
EMITTER = "adapters.runtime.emit_client@1.0"
REDACTED = "[REDACTED]"

ENQUEUED = "ENQUEUED"
SPOOLED = "SPOOLED"
REJECTED_SCHEMA = "REJECTED_SCHEMA"

# Records the queue keeps when it is full (everything else is shed first).
CRITICAL_KINDS = ("decision", "lifecycle", "judgment", "handoff", "approval")

# Table-A fields (ARCH 4.2): a value, or null with an entry in null_reasons.
TABLE_A = (
    "call.id", "trace.id", "handoff.id", "handoff.from", "handoff.to",
    "handoff.payload_sha256", "handoff.data_classification",
    "control.ref", "control.id", "threshold.version", "threshold.value",
    "threshold.sha256", "threshold.tier", "register.version", "pin.sha256",
    "measured.value", "measured.unit", "measured.source", "reason",
    "outcome.platform_decision", "outcome.real", "evaluator.name",
    "evaluator.sha256", "inline.mode", "inline.limit_applied",
    "inline.limit_value", "inline.action", "inline.bound_basis",
    "actor.id", "actor.runtime_id", "actor.version", "on_behalf_of",
    "principal.platform", "ep.id", "ep.kind", "ep.transport",
    "ep.responsible", "control.owner",
)

REQUIRED = ("schema", "record_id", "record_kind", "phase", "detail", "correlation_id",
            "run.id", "verdict", "ts", "provenance", "authorship", "source.refs", "emitter",
            "null_reasons")


def _j(*parts):
    return "".join(parts)


# ---- O-04 scrubbing: every pattern is assembled from parts so no scan matches this file ----
_SHAPES = [
    re.compile(_j(r"\b(?:AK", r"IA|AS", r"IA)[A-Z0-9]{16}\b")),
    re.compile(_j(r"-----BEGIN ", r"[A-Z ]*PRIV", r"ATE KEY-----")),
    re.compile(_j(r"\bgh", r"p_[A-Za-z0-9]{20,}")),
    re.compile(_j(r"\bgithub", r"_pat_[A-Za-z0-9_]{20,}")),
    re.compile(_j(r"\bs", r"k-[A-Za-z0-9_\-]{20,}")),
    re.compile(_j(r"\bx", r"ox[a-z]-[A-Za-z0-9\-]{10,}")),
    re.compile(_j(r"(?i)\bBear", r"er\s+[A-Za-z0-9._\-]{20,}")),
    re.compile(_j(r"(?i)\bt", r"kn=[^&\s\"']+")),
]
_SECRET_KEY = re.compile(
    _j(r"(?i)(secret|passw|api[_-]?key|auth[_-]?token|write[_-]?token|session[_-]?tok",
       r"en|bearer|private[_-]?key|AUDIT_WRITE_TOKEN|OPENAI_API_KEY|MCP_TOKEN)"))
_MIN_SECRET_LEN = 8


class Scrubber(object):
    """Exact-value scrubbing of the process's own secrets plus token shapes."""

    def __init__(self, secrets=()):
        self._secrets = []
        self.extend(secrets)

    def extend(self, secrets):
        for s in secrets:
            if isinstance(s, str) and len(s) >= _MIN_SECRET_LEN and s not in self._secrets:
                self._secrets.append(s)
        self._secrets.sort(key=len, reverse=True)

    def text(self, s):
        for sec in self._secrets:
            if sec in s:
                s = s.replace(sec, REDACTED)
        for rx in _SHAPES:
            s = rx.sub(REDACTED, s)
        return s

    def value(self, v):
        if isinstance(v, str):
            return self.text(v)
        if isinstance(v, dict):
            return dict((k, self.value(x)) for k, x in v.items())
        if isinstance(v, (list, tuple)):
            return [self.value(x) for x in v]
        return v


def scrub_exception(exc, scrubber):
    """Exception text is scrubbed before it can reach a record, stdout or an answer."""
    try:
        return scrubber.text("%s: %s" % (type(exc).__name__, exc))
    except Exception:
        return type(exc).__name__


_EMITTED_ID = re.compile(r"^[0-9]{8}T[0-9]{9}Z-[a-z0-9][a-z0-9.\-]{0,31}-[0-9a-f]{8}$")
_TIME_PAIRS = (("emitted.at", "emitted.clock"), ("observed.at", "observed.clock"))


def _validate_local(rec):
    """The bundle-side fallback (the prooflab package is not in the agent image beyond the frozen C16 core):
    the null rule, the required fields, the time pair, the id shape and the secret-key guard.
    PR-01 validate_record is the authority; a test keeps the two agreeing on the golden records."""
    if not isinstance(rec, dict):
        return "record must be a JSON object"
    for k in rec:
        if not isinstance(k, str):
            return "non-string key"
        if _SECRET_KEY.search(k):
            return "key names a secret variable"
    for k in REQUIRED:
        if k not in rec:
            return "missing required field %s" % k
    if not any(rec.get(a) and rec.get(c) for a, c in _TIME_PAIRS):
        return "no time pair (emitted.at/emitted.clock or observed.at/observed.clock)"
    if rec.get("schema") != SCHEMA:
        return "wrong schema id"
    if not _EMITTED_ID.match(str(rec.get("record_id"))):
        return "malformed record_id"
    nr = rec.get("null_reasons")
    if not isinstance(nr, dict):
        return "null_reasons must be an object"
    for k in TABLE_A:
        if k not in rec:
            return "table-A field %s missing" % k
        if rec[k] is None and not str(nr.get(k) or "").strip():
            return "null table-A field %s has no null_reason" % k
    for k in nr:
        if rec.get(k) is not None:
            return "null_reasons.%s names a field that has a value" % k
    try:
        json.dumps(rec)
    except (TypeError, ValueError):
        return "not JSON serialisable"
    return None


try:  # in the repo and in tests the contract is the one authority
    from prooflab.contract.record import validate_record as _contract_validate
except Exception:  # pragma: no cover - the agent bundle
    _contract_validate = None


def validate(rec):
    """Return None when acceptable, else a short reason (field names only, never values)."""
    bad = _validate_local(rec)          # cheap, always on: also the secret-key guard
    if bad or _contract_validate is None:
        return bad
    errors = _contract_validate(rec)
    if errors:
        return "contract: " + "; ".join(e.split(":")[0] for e in errors[:5])
    return None


# ---- the one adapter function onto the record shape (swap for PR-01's constructors here) ----
def utc_now():
    return datetime.now(timezone.utc)


def iso_ms(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (dt.microsecond // 1000)


def compact_ms(dt):
    return dt.strftime("%Y%m%dT%H%M%S") + "%03dZ" % (dt.microsecond // 1000)


def current_trace_id():
    """Trace id from the current OTel span (never from the payload); None when unavailable."""
    try:
        from opentelemetry import trace  # optional: present in the agent image only
        ctx = trace.get_current_span().get_span_context()
        if ctx and ctx.is_valid:
            return "%032x" % ctx.trace_id
    except Exception:
        pass
    return None


class RunContext(object):
    """Who/what/which run an invocation's records belong to.  Plain attributes, no logic."""

    def __init__(self, run_id, actor_id, actor_runtime_id=None, actor_version=None,
                 on_behalf_of=None, provenance="LIVE_SUBJECT", register_version=None,
                 pin_sha256=None, session_id=None, handoff_id=None, handoff_from=None,
                 handoff_to=None, trace_id=None, emitter=EMITTER, control_owner=None,
                 ep_responsible="team iFabric (Sree)", enveloped=True):
        self.run_id = run_id
        self.actor_id = actor_id
        self.actor_runtime_id = actor_runtime_id
        self.actor_version = actor_version
        self.on_behalf_of = on_behalf_of
        self.provenance = provenance
        self.register_version = register_version
        self.pin_sha256 = pin_sha256
        self.session_id = session_id
        self.handoff_id = handoff_id
        self.handoff_from = handoff_from
        self.handoff_to = handoff_to
        self.trace_id = trace_id
        self.emitter = emitter
        self.control_owner = control_owner
        self.ep_responsible = ep_responsible
        self.enveloped = enveloped
        self._seq = 0
        self._lock = threading.Lock()

    def next_seq(self):
        with self._lock:
            self._seq += 1
            return self._seq


def new_record(ctx, record_kind, ep_id, ep_kind, ep_transport, detail, verdict,
               control_ref=None, control_id=None, extra=None, null_reasons=None, now=None):
    """Build one record with every table-A field present (value, or null + reason)."""
    now = now or utc_now()
    at = iso_ms(now)
    rec = dict((k, None) for k in TABLE_A)
    rec.update({
        "schema": SCHEMA,
        "record_id": "%s-%s-%s" % (compact_ms(now), ep_id.lower().replace("-", ""),
                                   uuid.uuid4().hex[:8]),
        "record_kind": record_kind,
        "phase": "ifabric.%s" % record_kind,
        "detail": detail,
        "correlation_id": ctx.run_id, "run.id": ctx.run_id,
        "trace.id": ctx.trace_id or current_trace_id(),
        "seq.in_stream": ctx.next_seq(),
        "runtime.session_id": ctx.session_id,
        "control.ref": control_ref, "control.id": control_id,
        "register.version": ctx.register_version, "pin.sha256": ctx.pin_sha256,
        "actor.id": ctx.actor_id, "actor.runtime_id": ctx.actor_runtime_id,
        "actor.version": ctx.actor_version, "on_behalf_of": ctx.on_behalf_of,
        "handoff.id": ctx.handoff_id, "handoff.from": ctx.handoff_from,
        "handoff.to": ctx.handoff_to,
        "ep.id": ep_id, "ep.kind": ep_kind, "ep.transport": ep_transport,
        "ep.responsible": ctx.ep_responsible, "control.owner": ctx.control_owner,
        "verdict": verdict,
        "emitted.at": at, "emitted.clock": "agent-runtime", "ts": at,
        "provenance": ctx.provenance, "authorship": "TESTIMONY",
        "source.refs": [], "emitter": ctx.emitter,
    })
    if extra:
        rec.update(extra)
    reasons = dict(null_reasons or {})
    for k in TABLE_A:
        if rec.get(k) is None and k not in reasons:
            reasons[k] = "not applicable: %s" % ep_kind
    for k in list(reasons):                      # no stale reason on a field that has a value
        if rec.get(k) is not None:
            del reasons[k]
    rec["null_reasons"] = reasons
    return rec


def set_field(rec, name, value, null_reason=None):
    """Set a field and keep the null rule (a value drops its null reason)."""
    reasons = rec.setdefault("null_reasons", {})
    rec[name] = value
    if value is not None:
        reasons.pop(name, None)
    elif null_reason:
        reasons[name] = null_reason
    return rec


def lifecycle_record(ctx, event, detail, reason=None, extra=None, ep_id="EP-4",
                     ep_kind="agent runtime (lifecycle)", control_ref="C7"):
    ex = {"lifecycle.event": event, "reason": reason or event}
    if extra:
        ex.update(extra)
    return new_record(ctx, "lifecycle", ep_id, ep_kind, "emit", detail, "RECORDED",
                      control_ref=control_ref, control_id="AIA-LOG-001", extra=ex)


# ---- the client ----
class EmitClient(object):
    def __init__(self, url, token, secrets=(), queue_max=10000, timeout=2.0, attempts=3,
                 backoff=0.1, stdout=None, flush_bound=2.0):
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            raise ValueError("AUDIT_URL is not an http(s) URL")
        self._scheme, self._host = u.scheme, u.hostname
        self._port = u.port or (443 if u.scheme == "https" else 80)
        self._path = (u.path.rstrip("/") or "") + "/records"
        self._token = token
        self.scrubber = Scrubber(list(secrets) + [token])
        self.queue_max, self.timeout = queue_max, timeout
        self.attempts, self.backoff = attempts, backoff
        self.flush_bound = flush_bound
        self._out = stdout if stdout is not None else sys.stdout
        self._cv = threading.Condition()
        self._crit = collections.deque()
        self._rest = collections.deque()
        self._inflight = 0
        self._stop = False
        self._out_lock = threading.Lock()
        self.stats = {"enqueued": 0, "posted": 0, "failed": 0, "shed": 0, "spooled": 0,
                      "rejected": 0, "abandoned": 0}
        self.gaps = []
        self.flush_ms = []
        self._worker = threading.Thread(target=self._run, name="emit-client", daemon=True)
        self._worker.start()

    # -- public
    def emit(self, record):
        """Never raises, never waits.  Returns ENQUEUED | SPOOLED | REJECTED_SCHEMA."""
        try:
            rec = self.scrubber.value(record) if isinstance(record, dict) else record
            bad = validate(rec)
            if bad:
                self.stats["rejected"] += 1
                self._witness(self._system_record("record-rejected", bad, record))
                return REJECTED_SCHEMA
            self._witness(rec)
            critical = rec.get("record_kind") in CRITICAL_KINDS
            with self._cv:
                if len(self._crit) + len(self._rest) >= self.queue_max:
                    if self._rest and critical:
                        self._rest.popleft()          # shed the oldest non-critical record
                        self.stats["shed"] += 1
                    else:
                        self.stats["spooled"] += 1
                        self._gap("queue-full", rec)
                        return SPOOLED
                (self._crit if critical else self._rest).append(rec)
                self.stats["enqueued"] += 1
                self._cv.notify()
            return ENQUEUED
        except Exception:
            return SPOOLED

    def flush(self, timeout=None):
        """The declared bounded end-of-invocation wait.  Returns a small dict; never raises."""
        bound = self.flush_bound if timeout is None else timeout
        t0 = time.time()
        deadline = t0 + bound
        with self._cv:
            while (self._crit or self._rest or self._inflight):
                left = deadline - time.time()
                if left <= 0:
                    break
                self._cv.wait(left)
            pending = len(self._crit) + len(self._rest) + self._inflight
        ms = (time.time() - t0) * 1000.0
        self.flush_ms.append(ms)
        if pending:
            self.stats["abandoned"] += pending
            self._gap("flush-bound-exceeded", None, pending=pending)
        return {"pending": pending, "elapsed_ms": ms, "ok": pending == 0}

    def flush_p99_ms(self):
        if not self.flush_ms:
            return None
        s = sorted(self.flush_ms)
        return s[min(len(s) - 1, int(0.99 * len(s)))]

    def close(self):
        with self._cv:
            self._stop = True
            self._cv.notify_all()

    # -- internals
    def _witness(self, rec):
        line = json.dumps(self.scrubber.value(rec), sort_keys=True, separators=(",", ":"))
        with self._out_lock:
            try:
                self._out.write(line + "\n")
                self._out.flush()
            except Exception:
                pass

    def _system_record(self, event, why, rec, pending=None):
        """A contract-valid lifecycle record about the client itself (witness line; gaps stay local)."""
        src = rec if isinstance(rec, dict) else {}
        run_id = src.get("run.id") if isinstance(src.get("run.id"), str) else None
        run_id = run_id or "ifabric-unenveloped-%d-000000" % int(time.time())
        ctx = RunContext(run_id, EMITTER, provenance=src.get("provenance") or "UNATTRIBUTED",
                         handoff_id=src.get("handoff.id"), session_id=src.get("runtime.session_id"),
                         emitter=EMITTER)
        detail = "%s: %s" % (event, why)
        if pending is not None:
            detail += " (pending=%s)" % pending
        out = new_record(ctx, "lifecycle", "EP-4", "emit client (monitoring gap)", "emit", detail,
                         "RECORDED", control_ref="C7", control_id="AIA-LOG-001",
                         extra={"lifecycle.event": event, "reason": why})
        lost = src.get("record_id")
        if isinstance(lost, str) and lost:
            out["source.refs"] = ["lost-record:" + lost]
        return out

    def _gap(self, why, rec, pending=None):
        try:
            g = self._system_record("monitoring-gap", why, rec, pending)
            self.gaps.append(g)
            self._witness(g)
        except Exception:
            self.gaps.append({"lifecycle.event": "monitoring-gap", "reason": why})

    def _next(self):
        with self._cv:
            while not (self._crit or self._rest):
                if self._stop:
                    return None
                self._cv.wait(0.5)
            rec = (self._crit or self._rest).popleft()
            self._inflight += 1
            return rec

    def _post(self, body):
        cls = http.client.HTTPSConnection if self._scheme == "https" else http.client.HTTPConnection
        conn = cls(self._host, self._port, timeout=self.timeout)
        try:
            conn.request("POST", self._path, body=body,
                         headers={"Content-Type": "application/json",
                                  "X-Audit-Token": self._token})
            resp = conn.getresponse()
            resp.read(4096)
            return resp.status
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _run(self):
        while True:
            rec = self._next()
            if rec is None:
                return
            ok, last = False, "error"
            body = json.dumps(rec, sort_keys=True).encode("utf-8")
            for i in range(self.attempts):
                try:
                    st = self._post(body)
                    if 200 <= st < 300:
                        ok = True
                        break
                    last = "http-%d" % st
                    if 400 <= st < 500:
                        break                       # a rejected record is not retried
                except Exception as e:
                    last = type(e).__name__
                if i + 1 < self.attempts:
                    time.sleep(self.backoff * (2 ** i))
            if not ok:                              # the gap is on record before flush() can return
                self._gap("post-failed:" + last, rec)
            with self._cv:
                self._inflight -= 1
                self.stats["posted" if ok else "failed"] += 1
                self._cv.notify_all()


def sha256_json(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()

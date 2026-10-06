"""Fail-closed start-up, the unenveloped path and the duplicate-invocation guard (AR-18).

Python 3.9, stdlib only.  Nothing here is a control question: all three are preconditions.
"""
import hashlib
import json
import os
import re
import threading
import time
import uuid
from urllib.parse import urlparse

from adapters.runtime import emit_client as ec

REQUIRED_ENV = ("OPENAI_API_KEY", "AGENTCORE_GATEWAY_MCP_TOKEN", "AUDIT_URL",
                "AUDIT_WRITE_TOKEN", "IFABRIC_PIN_JSON", "IFABRIC_PIN_SHA256",
                "IFABRIC_REGISTER_VERSION", "IFABRIC_REGISTER_SHA256")
_SECRET_ENV = ("OPENAI_API_KEY", "AGENTCORE_GATEWAY_MCP_TOKEN", "AUDIT_WRITE_TOKEN")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class StartupError(Exception):
    """Message names variables and problems only, never a value."""


class StartupConfig(object):
    def __init__(self, env, pin):
        self.audit_url = env["AUDIT_URL"]
        self.pin = pin
        self.pin_sha256 = env["IFABRIC_PIN_SHA256"]
        self.register_version = env["IFABRIC_REGISTER_VERSION"]
        self.register_sha256 = env["IFABRIC_REGISTER_SHA256"]
        self.max_retries = 0                      # OpenAI client: no retries below the hook
        self._secrets = [env[k] for k in _SECRET_ENV]
        self._token = env["AUDIT_WRITE_TOKEN"]

    def secrets(self):
        return list(self._secrets)

    def new_client(self, **kw):
        return ec.EmitClient(self.audit_url, self._token, secrets=self._secrets, **kw)

    def echo(self):
        return "ifabric start-up ok pin.sha256=%s register=%s@%s max_retries=0" % (
            self.pin_sha256, self.register_version, self.register_sha256)

    def __repr__(self):
        return "<StartupConfig pin.sha256=%s register=%s>" % (self.pin_sha256, self.register_version)


def load_startup(env=None, out=None):
    """Read env, validate, echo the pin sha256.  Raises StartupError (fail closed)."""
    env = os.environ if env is None else env
    problems = []
    missing = [k for k in REQUIRED_ENV if not str(env.get(k, "")).strip()]
    if missing:
        problems.append("missing: " + ",".join(missing))
    pin = None
    if not missing:
        u = urlparse(env["AUDIT_URL"])
        if u.scheme not in ("http", "https") or not u.hostname:
            problems.append("AUDIT_URL malformed")
        for k in ("IFABRIC_PIN_SHA256", "IFABRIC_REGISTER_SHA256"):
            if not _HEX64.match(env[k]):
                problems.append("%s malformed" % k)
        try:
            pin = json.loads(env["IFABRIC_PIN_JSON"])
            if not isinstance(pin, dict) or not pin:
                problems.append("IFABRIC_PIN_JSON not a non-empty object")
        except ValueError:
            problems.append("IFABRIC_PIN_JSON not JSON")
        got = hashlib.sha256(env["IFABRIC_PIN_JSON"].encode("utf-8")).hexdigest()
        if _HEX64.match(env["IFABRIC_PIN_SHA256"]) and got != env["IFABRIC_PIN_SHA256"]:
            problems.append("IFABRIC_PIN_SHA256 does not match IFABRIC_PIN_JSON")
    if problems:
        raise StartupError("fail-closed start-up: " + "; ".join(problems))
    cfg = StartupConfig(env, pin)
    if out is not None:
        out.write(cfg.echo() + "\n")
        out.flush()
    return cfg


# ---- the unenveloped path (ARCH 7.1, 4.2) ----
class Envelope(object):
    def __init__(self, run_id, enveloped, handoff_id=None, tier=None, tally=0,
                 provenance="LIVE_SUBJECT", strictest_cap=False, from_agent=None):
        self.run_id, self.enveloped, self.handoff_id = run_id, enveloped, handoff_id
        self.tier, self.tally, self.provenance = tier, tally, provenance
        self.strictest_cap, self.from_agent = strictest_cap, from_agent
        self.tally_tokens, self.tally_calls = tally, 0


def _count(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else 0


def resolve_envelope(payload, now=None, rand=None):
    """The envelope is payload["ifabric"] (ARCH 7.2; possibly wrapped in payload["input"]) =
    {run_id, handoff_id, from, tier, tally_tokens, tally_calls, ...}.  The older payload["envelope"]
    (key "tally") is still read.  Without one the agent still works: it mints
    ifabric-unenveloped-<epoch>-<hex>, stamps UNATTRIBUTED, starts its tally at 0 and asks for the
    strictest cap in its pin.  Never raises."""
    env = None
    if isinstance(payload, dict):
        for holder in (payload, payload.get("input")):
            if isinstance(holder, dict):
                for key in ("ifabric", "envelope"):
                    if isinstance(holder.get(key), dict) and holder[key].get("run_id"):
                        env = holder[key]
                        break
            if env:
                break
    if env:
        tokens = _count(env.get("tally_tokens", env.get("tally")))
        out = Envelope(str(env["run_id"]), True, env.get("handoff_id"), env.get("tier"), tokens,
                       provenance=env.get("provenance") or "LIVE_SUBJECT", from_agent=env.get("from"))
        out.tally_tokens, out.tally_calls = tokens, _count(env.get("tally_calls"))
        return out
    epoch = int(now if now is not None else time.time())
    out = Envelope("ifabric-unenveloped-%d-%s" % (epoch, rand or uuid.uuid4().hex[:6]), False,
                   None, None, 0, "UNATTRIBUTED", True)
    out.tally_tokens = out.tally_calls = 0
    return out


def record_no_envelope(client, ctx):
    rec = ec.lifecycle_record(ctx, "no-envelope", "invoked with no envelope; minted %s" % ctx.run_id,
                              reason="no envelope")
    rec["provenance"] = "UNATTRIBUTED"
    return client.emit(rec)


# ---- duplicate-invocation guard (AR-18, T-DUP-01) ----
class InvocationGuard(object):
    """One invocation per handoff.  A handoff.id seen before (in flight or finished) is refused."""

    def __init__(self):
        self._lock = threading.Lock()
        self._inflight, self._done = set(), set()

    def begin(self, handoff_id):
        """True = proceed.  False = refuse.  A missing handoff id cannot be guarded: proceeds."""
        if not handoff_id:
            return True
        with self._lock:
            if handoff_id in self._inflight or handoff_id in self._done:
                return False
            self._inflight.add(handoff_id)
            return True

    def state(self, handoff_id):
        with self._lock:
            return "in-flight" if handoff_id in self._inflight else (
                "completed" if handoff_id in self._done else "new")

    def end(self, handoff_id):
        with self._lock:
            self._inflight.discard(handoff_id)
            self._done.add(handoff_id)


def refuse_duplicate(client, ctx, guard=None):
    """Record `duplicate-invocation` (with the session id).  The caller returns a refusal and
    does no work.  Call only after begin() said False."""
    state = guard.state(ctx.handoff_id) if guard else "seen"
    rec = ec.lifecycle_record(
        ctx, "duplicate-invocation",
        "second invocation for handoff %s refused (%s)" % (ctx.handoff_id, state),
        reason="duplicate-invocation",
        extra={"runtime.session_id": ctx.session_id, "lifecycle.duplicate_state": state})
    return client.emit(rec)

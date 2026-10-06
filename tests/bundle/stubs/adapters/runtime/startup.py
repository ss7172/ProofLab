"""STUB adapters.runtime.startup (tests/bundle/stubs): PR-04's names and signatures, no logic."""
from adapters.runtime import emit_client as ec


class StartupError(Exception):
    pass


class _Cfg(object):
    def __init__(self, env):
        self.pin_sha256 = env.get("IFABRIC_PIN_SHA256")
        self.register_version = env.get("IFABRIC_REGISTER_VERSION")

    def new_client(self, **kw):
        return ec.EmitClient("http://stub", "stub")


def load_startup(env=None, out=None):
    if not (env or {}).get("IFABRIC_PIN_JSON"):
        raise StartupError("fail-closed start-up: missing: IFABRIC_PIN_JSON")
    return _Cfg(env)


class Envelope(object):
    def __init__(self, run_id, enveloped, handoff_id=None, tier=None, tally=0,
                 provenance="LIVE_SUBJECT", strictest_cap=False, from_agent=None):
        self.run_id, self.enveloped, self.handoff_id, self.tier = run_id, enveloped, handoff_id, tier
        self.tally, self.provenance, self.from_agent = tally, provenance, from_agent


def resolve_envelope(payload, now=None, rand=None):
    e = payload.get("envelope") if isinstance(payload, dict) else None
    if isinstance(e, dict) and e.get("run_id"):
        return Envelope(e["run_id"], True, e.get("handoff_id"), e.get("tier"), e.get("tally") or 0)
    return Envelope("ifabric-unenveloped-0-stub", False, provenance="UNATTRIBUTED")


def record_no_envelope(client, ctx):
    return client.emit({"lifecycle.event": "no-envelope"})


class InvocationGuard(object):
    def begin(self, handoff_id):
        return True

    def end(self, handoff_id):
        pass


def refuse_duplicate(client, ctx, guard=None):
    return client.emit({"lifecycle.event": "duplicate-invocation"})

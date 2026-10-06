"""STUB adapters.runtime.startup (tests/bundle/stubs): the surface ifabric_app._wire() expects."""
import json
import time
import uuid

REQUIRED = ("OPENAI_BASE_URL", "OPENAI_API_KEY", "MODEL_ALIAS")


class _Inv(object):
    def __init__(self, payload):
        env = (payload.get("ifabric") or {}) if isinstance(payload, dict) else {}
        self.cid = env.get("run_id") or "ifabric-unenveloped-%d-%s" % (int(time.time()), uuid.uuid4().hex[:8])
        self.refusal = None
        self.actions = []

    def finish(self, result):
        print(json.dumps({"stub": "finish", "cid": self.cid, "actions": self.actions}), flush=True)


class _Rt(object):
    def __init__(self, spec):
        self.spec = spec

    def begin(self, payload):
        return _Inv(payload)


def start(environ, spec):
    missing = [k for k in REQUIRED if not environ.get(k)]
    if missing:
        raise RuntimeError("missing env: " + ",".join(missing))
    return _Rt(spec)

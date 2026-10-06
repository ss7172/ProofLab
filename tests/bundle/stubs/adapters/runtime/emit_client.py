"""STUB adapters.runtime.emit_client (tests/bundle/stubs): PR-04's names, records printed not posted."""
import json


class RunContext(object):
    def __init__(self, run_id, actor_id, **kw):
        self.run_id, self.actor_id = run_id, actor_id
        self.__dict__.update(kw)


def new_record(ctx, record_kind, ep_id, ep_kind, ep_transport, detail, verdict, control_ref=None,
               control_id=None, extra=None, null_reasons=None, now=None):
    rec = {"record_kind": record_kind, "run.id": ctx.run_id, "verdict": verdict, "null_reasons": {}}
    rec.update(extra or {})
    return rec


class EmitClient(object):
    def __init__(self, url, token, secrets=(), **kw):
        self.n = 0

    def emit(self, record):
        self.n += 1
        print(json.dumps({"stub-emit": record.get("record_kind")}), flush=True)
        return "ENQUEUED"

    def flush(self, timeout=None):
        return {"stub": True}

"""Build and validate the orchestrator's records through the one contract (prooflab.contract.record)."""
from __future__ import annotations

import hashlib
import os

from prooflab.adapters.orchestrator import common
from prooflab.contract import record as R


class RecordError(ValueError):
    pass


def make(record_kind: str, run_id: str, detail: str, null_reason: str, emitter_short: str = "orch",
         emitter: str = common.EMITTER, provenance: str = "LIVE_SUBJECT", now: str = None, **fields) -> dict:
    """One validated record. Raises RecordError (never emits an invalid or secret-shaped record)."""
    at = now or common.utc_now()
    seed = "%s|%s|%s|%s" % (at, run_id, detail, os.urandom(4).hex())
    base = {
        "record_id": R.emitted_record_id(at, emitter_short, hashlib.sha256(seed.encode()).hexdigest()[:8]),
        "detail": detail, "run.id": run_id, "verdict": "RECORDED",
        "emitted.at": at, "emitted.clock": "script-host",
        "provenance": provenance, "authorship": "TESTIMONY", "emitter": emitter,
        "ep.transport": "emit", "actor.id": "orchestrator",
    }
    base.update(fields)
    rec = R.new_record(record_kind, null_reason, **base)
    errors = R.validate_record(rec)
    if errors:
        raise RecordError("; ".join(errors))
    return rec

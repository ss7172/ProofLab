"""One line in live-lane-log.jsonl per live action (IMPLEMENTATION-PLAN 5.1): time, action, authority, CID,
tokens before and after. Fixed field set; any other field, or a secret-shaped value, is refused."""
from __future__ import annotations

import json

from prooflab.adapters.orchestrator import common
from prooflab.contract import record as R

FIELDS = ("time", "action", "authority", "cid", "tokens_before", "tokens_after", "note")


def log_line(action, authority, cid=None, tokens_before=None, tokens_after=None, note="", time=None, **extra) -> dict:
    if extra:
        raise ValueError("live-lane-log carries only %s; refused extra: %s" % (FIELDS, sorted(extra)))
    line = {"time": time or common.utc_now(), "action": action, "authority": authority, "cid": cid,
            "tokens_before": tokens_before, "tokens_after": tokens_after, "note": note}
    for key, value in line.items():
        if R.secret_shaped(value if isinstance(value, str) else json.dumps(value)):
            raise ValueError("live-lane-log: %s looks like a secret; refused" % key)
    return line


def append(path, **kwargs) -> dict:
    line = log_line(**kwargs)
    common.append_jsonl(path, line)
    return line

"""Shared small helpers for the orchestrator and the lane wrappers (PR-08a). Stdlib, Python 3.9."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
EMITTER = "adapters.orchestrator.run@1.0+0000000"


def load_budget(path=None) -> dict:
    with open(path or os.path.join(HERE, "budget.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def utc_now() -> str:
    now = _dt.datetime.utcnow()
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (now.microsecond // 1000)


def parse_utc(value: str) -> _dt.datetime:
    value = value.rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return _dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError("not a UTC timestamp: %r" % (value,))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def append_jsonl(path: str, obj) -> None:
    """Append one JSON line, fsync'd (append-only spool / index files)."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path: str) -> list:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out

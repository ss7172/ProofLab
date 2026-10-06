"""The live feed: `live/events.jsonl`, labelled "live index" (G-10, ARCH 3.12). Stdlib, Python 3.9.

An index for the console's LIVE mode, never evidence: every event names the ledger record it came from
(`record_id`) and nothing reads the feed back to judge. Events are appended once per record id (the feed
re-reads its own file on start, so a restarted watcher does not repeat itself). `staleness()` is how the
console and `tail` tell a stopped watcher from a quiet one: the watcher writes a heartbeat every
HEARTBEAT_S, and a feed whose last write is STALE_AFTER_S old (or older) reads STALE.
These two numbers are mechanics of the feed itself, not control thresholds: a control's limit never appears here.
"""
from __future__ import annotations

import json
import os

from prooflab.contract import clocks

LABEL = "live index"
SCHEMA = "ifabric.live-event/1"
EVENT_KINDS = ("call", "admission", "hop", "decision", "verdict", "window", "finding", "incident",
               "response", "analysis", "ceiling", "heartbeat", "stream-error")
HEARTBEAT_S = 10.0
STALE_AFTER_S = 30.0

# record_kind -> event kind. Refinements by field are in classify().
_BY_RECORD_KIND = {
    "action": "call",
    "handoff": "hop",
    "decision": "decision",
    "platform_decision": "decision",
    "rail_decision": "decision",
    "assessment": "verdict",
    "metric": "window",
    "finding": "finding",
    "notification": "incident",
    "approval": "response",
    "judgment": "analysis",
}
ADMISSION_EP = "EP-10"
CEILING_OUTCOME = "CEILING_429"
CEILING_LIMIT = "safety-ceiling"


def classify(rec):
    """The event kind for a ledger record, or None when the record is not a feed event.

    Order matters: a ceiling stop outranks its record kind, an admission outranks a plain decision, and an
    assessment of a window is a `window` event."""
    if not isinstance(rec, dict):
        return None
    kind = rec.get("record_kind")
    if rec.get("outcome.real") == CEILING_OUTCOME or (
            rec.get("inline.limit_applied") == CEILING_LIMIT and rec.get("inline.action") == "halt"):
        return "ceiling"
    if rec.get("ep.id") == ADMISSION_EP and kind in ("platform_decision", "decision", "approval"):
        return "admission"
    if kind == "assessment" and rec.get("assessment.scope_kind") in ("window", "interval"):
        return "window"
    return _BY_RECORD_KIND.get(kind)


def event_from_record(rec, written_at, seq=None):
    """One feed event from a ledger record (None when it is not an event)."""
    kind = classify(rec)
    if kind is None:
        return None
    return {
        "schema": SCHEMA, "label": LABEL, "kind": kind, "written_at": written_at,
        "record_id": rec.get("record_id"), "run_id": rec.get("run.id") or rec.get("correlation_id"),
        "at": rec.get("ts") or rec.get("emitted.at") or rec.get("observed.at"),
        "record_kind": rec.get("record_kind"), "verdict": rec.get("verdict"),
        "control": rec.get("control.ref"), "ep": rec.get("ep.id"), "detail": rec.get("detail"),
    }


def synthetic_event(kind, written_at, **fields):
    """An event the watcher itself makes: heartbeat, stream-error, finding (from a rule) and the like."""
    if kind not in EVENT_KINDS:
        raise ValueError("unknown live event kind: %r" % (kind,))
    ev = {"schema": SCHEMA, "label": LABEL, "kind": kind, "written_at": written_at, "record_id": None,
          "run_id": None, "at": written_at, "record_kind": None, "verdict": None, "control": None,
          "ep": None, "detail": None}
    ev.update(fields)
    return ev


class LiveFeed:
    """Append-only JSONL writer. One line per event; a record id is written once."""

    def __init__(self, path):
        self.path = path
        self.seen = set()
        self._load()

    def _load(self):
        for ev in read_events(self.path):
            if ev.get("record_id"):
                self.seen.add((ev.get("kind"), ev["record_id"]))

    def append(self, event):
        """Write the event; returns False (and writes nothing) for a record id already in the feed."""
        key = (event.get("kind"), event.get("record_id"))
        if event.get("record_id"):
            if key in self.seen:
                return False
            self.seen.add(key)
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        line = json.dumps(event, sort_keys=True, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return True


def read_events(path):
    """All events of a feed file (bad lines skipped; a missing file is an empty feed)."""
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except ValueError:
                    continue
                if isinstance(doc, dict):
                    out.append(doc)
    except OSError:
        return []
    return out


def staleness(path, now, stale_after_s=STALE_AFTER_S):
    """LIVE | STALE | NO_FEED for a feed file at `now` (an aware datetime: the caller's clock, simulated in tests).

    The age is measured from the last `written_at` in the file, so it needs no cooperation from the watcher."""
    events = read_events(path)
    last = None
    for ev in events:
        try:
            moment = clocks.parse_utc(ev.get("written_at"))
        except ValueError:
            continue
        if last is None or moment > last:
            last = moment
    if last is None:
        return {"state": "NO_FEED", "age_s": None, "last_written_at": None, "label": LABEL}
    age = (now - last).total_seconds()
    state = "STALE" if age >= stale_after_s else "LIVE"
    return {"state": state, "age_s": age, "last_written_at": clocks.format_utc(last), "label": LABEL}

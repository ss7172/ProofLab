"""G-06: the delivery log -> `notification` records (state transitions only). Stdlib, 3.9.

One record per state TRANSITION of a finding (a repeated AWAITING_RESPONSE line is skipped). record_id =
`obs-` + sha256 of the log line (via the contract's observation id), so a re-mirror deduplicates. A RESPONDED
line's `at` is ServiceNow's clock; every other line carries our script host's `ts`. ANALYSIS_* lines carry
`call.id` = their action ids and `note_digest`. Model text is never read here.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable, List, Optional, Set

from prooflab.contract import clocks as _clocks, ids as _ids, record as _rec, verdicts as _verdicts

EMITTER = "prooflab.humanloop.mirror"
SOURCE_SYSTEM = "servicenow-delivery-log"
CLOCK_SERVICENOW, CLOCK_HOST = "servicenow", "script-host"


def line_record_id(line: str) -> str:
    return _rec.observation_record_id(SOURCE_SYSTEM, hashlib.sha256(line.encode("utf-8")).hexdigest())


def run_id_of(finding_id: str, ts: str) -> str:
    """`ifabric:{ref}:{version}:{scope_kind}:{scope_id}:{kind}`: a run scope names its CID, any other scope
    is unattributed to a run."""
    parts = (finding_id or "").split(":")
    if len(parts) >= 6 and parts[3] == "run" and _ids.is_valid_run_id(parts[4]):
        return parts[4]
    return _ids.unattributed_cid("humanloop", ts)


def _time(entry: dict):
    at = entry.get("at")
    if entry.get("state") == "RESPONDED" and isinstance(at, str) and _clocks.is_utc(at):
        return at, CLOCK_SERVICENOW
    return entry["ts"], CLOCK_HOST


def _build(entry: dict, line: str, previous: Optional[str]) -> Optional[dict]:
    if not isinstance(entry.get("ts"), str) or not _clocks.is_utc(entry["ts"]) or not entry.get("finding_id"):
        return None
    state = entry["state"]
    at, clock = _time(entry)
    run_id = run_id_of(entry["finding_id"], entry["ts"])
    from prooflab.store.observations import family_provenance
    call_id = entry.get("action_id") or entry.get("call_id")
    fields = {
        "record_id": line_record_id(line), "run.id": run_id, "finding.id": entry["finding_id"],
        "detail": "delivery log %s%s" % (state, (" (from %s)" % previous) if previous else ""),
        "verdict": _verdicts.RECORD_VERDICTS[0],
        "observed.at": at, "observed.clock": clock, "provenance": family_provenance(run_id),
        "authorship": "HUMAN" if state == "RESPONDED" else "ASSURANCE",
        "source.refs": ["%s:sha256:%s" % (SOURCE_SYSTEM, hashlib.sha256(line.encode("utf-8")).hexdigest())],
        "emitter": EMITTER, "reason": state,
    }
    if call_id:
        fields["call.id"] = str(call_id)
    rec = _rec.new_record("notification", "not applicable", **fields)
    extra = {k: entry[k] for k in ("number", "note_digest", "actor", "assigned_to") if entry.get(k)}
    if extra:
        rec["detail"] = rec["detail"] + " " + json.dumps(extra, sort_keys=True)[:300]
    return rec


def mirror_lines(lines: Iterable[str], seen: Optional[Set[str]] = None) -> List[dict]:
    """Records for the state transitions in `lines` (a delivery log's text lines), skipping ids in `seen`."""
    seen = set(seen or ())
    last = {}
    out: List[dict] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue    # a torn write
        if not isinstance(entry, dict) or "state" not in entry or "finding_id" not in entry:
            continue
        fid, state = entry["finding_id"], entry["state"]
        previous = last.get(fid)
        last[fid] = state
        if previous == state:
            continue
        rec = _build(entry, line, previous)
        if rec is None or rec["record_id"] in seen:
            continue
        seen.add(rec["record_id"])
        out.append(rec)
    return out


def mirror_file(log_path: str, seen: Optional[Set[str]] = None) -> List[dict]:
    with open(log_path, encoding="utf-8") as handle:
        return mirror_lines(handle.readlines(), seen)

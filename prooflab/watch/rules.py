"""MON-01: the rail rules of `prooflab watch` (guardrails 3.8). Stdlib, Python 3.9. Pure.

Records only, never blocks. Over the ledger records of ONE run (by CID):
  1. any rail BLOCK or quarantine in an ASSESSED run        -> a finding to the owner
  2. any RT-03 egress FLAG                                  -> a finding
  3. a lifecycle record's `rails.counts` that disagrees with the rail records received -> `monitoring-gap`
The rules read records and name them as evidence. They hold no limit: what a rail blocks is the rail's policy.
Assessed = provenance LIVE_SUBJECT (the EP-0 scope, ARCH 4.x provenance row); an adversarial run is not assessed,
so its rail BLOCKs are the intended result and raise no finding.
"""
from __future__ import annotations

from prooflab.contract import finding as _finding
from prooflab.contract import verdicts as _V  # the one verdict vocabulary (ARCH §4.3)

ASSESSED_PROVENANCE = ("LIVE_SUBJECT",)
EGRESS_RAIL = "RT-03"
QUARANTINE_ACTIONS = ("quarantine",)
COUNTED_VERDICTS = ("BLOCK", "MODIFY", "FLAG")   # ALLOWs ride compactly on action records; not countable here
RAIL_CONTROL_REF = "RAIL"


def _rail_id(rec):
    return rec.get("rail.id") or ""


def _tag(rec):
    return "%s@%s" % (_rail_id(rec), rec.get("rail.version") or "?")


def _scope(rec):
    return rec.get("run.id") or rec.get("correlation_id")


def _is_rail(rec):
    return isinstance(rec, dict) and rec.get("record_kind") == "rail_decision"


def _quarantined(rec):
    return rec.get("inline.action") in QUARANTINE_ACTIONS or "quarantine" in str(rec.get("detail") or "").lower()


def _alert(recs, summary, detected_at):
    first = recs[0]
    return _finding.make_finding(
        RAIL_CONTROL_REF, "RAIL-" + _rail_id(first), _tag(first), "run",
        _scope(first), "ESCALATED", summary, detected_at,
        evidence=[str(r.get("record_id")) for r in recs], kind="finding")


def rail_findings(records, detected_at):
    """Rules 1 and 2 over one run's records. One finding per (run, rail tag, rule): a finding id is stable per
    scope, so the evidence of every matching record rides in one finding and a repeat poll makes the same id."""
    groups = {}
    for rec in records:
        if not _is_rail(rec):
            continue
        assessed = rec.get("provenance") in ASSESSED_PROVENANCE
        if assessed and (rec.get("verdict") == "BLOCK" or _quarantined(rec)):
            rule = "quarantine" if _quarantined(rec) else "BLOCK"
        elif rec.get("verdict") == "FLAG" and _rail_id(rec) == EGRESS_RAIL:
            rule = "egress FLAG"
        else:
            continue
        groups.setdefault((_tag(rec), rule), []).append(rec)
    out = []
    for (tag, rule), recs in sorted(groups.items()):
        why = recs[0].get("reason") or recs[0].get("detail") or "see record"
        if rule == "egress FLAG":
            summary = "egress FLAG (RT-03) x%d: %s" % (len(recs), why)
        else:
            summary = "rail %s %s in an assessed run x%d: %s" % (_rail_id(recs[0]), rule, len(recs), why)
        out.append(_alert(recs, summary, detected_at))
    return out


def counts_gaps(records, detected_at):
    """Rule 3: for each lifecycle record with `rails.counts`, the BLOCK/MODIFY/FLAG count per rail must equal
    the rail_decision records received for the same handoff id. A difference is a `monitoring-gap` (the records
    do not cover every governed action). One finding per run, naming each differing handoff and rail."""
    received = {}
    for rec in records:
        if _is_rail(rec) and rec.get("verdict") in COUNTED_VERDICTS:
            key = (rec.get("handoff.id"), _rail_id(rec), rec["verdict"])
            received[key] = received.get(key, 0) + 1
    diffs, evidence, scope = [], [], None
    for rec in records:
        counts = rec.get("rails.counts") if isinstance(rec, dict) else None
        if rec.get("record_kind") != "lifecycle" or not isinstance(counts, dict):
            continue
        handoff = rec.get("handoff.id")
        before = len(diffs)
        for rail in sorted(counts):
            for verdict in COUNTED_VERDICTS:
                claimed = int((counts[rail] or {}).get(verdict, 0))
                got = received.get((handoff, rail, verdict), 0)
                if claimed != got:
                    diffs.append("%s %s %s: lifecycle says %d, records received %d" % (handoff, rail, verdict,
                                                                                    claimed, got))
        for (h, rail, verdict), got in sorted(received.items(), key=lambda kv: str(kv[0])):
            if h == handoff and rail not in counts:
                diffs.append("%s %s %s: not in lifecycle counts, records received %d" % (h, rail, verdict, got))
        if len(diffs) > before:
            evidence.append(str(rec.get("record_id")))
            scope = scope or _scope(rec)
    if not diffs:
        return []
    return [_finding.make_finding(
        RAIL_CONTROL_REF, "RAIL-COUNTS", "rails.counts", "run", scope, _V.INDETERMINATE,
        "monitoring gap: rail records do not match rails.counts (%s)" % "; ".join(diffs),
        detected_at, evidence=evidence, kind="monitoring-gap")]


def mon01(records, detected_at):
    """All MON-01 findings for one run's records."""
    return rail_findings(records, detected_at) + counts_gaps(records, detected_at)

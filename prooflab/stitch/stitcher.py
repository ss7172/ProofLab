"""The stitcher: a pure join over one snapshot's records (ARCH §3.6, plan T4.4). Stdlib, 3.9.

It never changes a record and never forms a verdict. Keys, in order:
  1 correlation_id / run.id          2 call.id (gateway action id; also resolves `unresolved:<trace>`: the
    ifabric-assure gateway calls join their incident's analysis line by action id only, b6b)
                                                                         3 trace.id (resolves `unresolved:<trace>`)
  4 handoff.id (`prooflab.contract.ids.parse_handoff_id`)                5 AWS InvokeAgentRuntime record:
    CID + runtime.session_id exact against a `handoff.sent`; `eventTime` (the call's END) against
    `handoff.received` only when the caller passes `join_tolerance_s` (a register key: no literal here);
    one session id on two AWS records = a retry suspect              6 finding.id / assessment.id
Key 7 (ownership/risk) needs the inventory: Phase 2.
Outputs (rows, sorted, byte-stable): the run index and the unjoined facts (`link-gap` shaped dicts
{key, value, present_in, missing_from}). Records of any shape are accepted: a reference-shaped ledger row or the
synthetic `ifabric-test-ledger-smoke-*` probe joins on its `correlation_id` and is never an error.
"""
from __future__ import annotations

import json

from prooflab.contract import clocks as _clocks
from prooflab.contract import ids as _ids

KEYS = ("correlation_id", "call.id", "trace.id", "handoff.id", "runtime.session_id", "finding.id")


def run_of(rec: dict):
    return rec.get("run.id") or rec.get("correlation_id")


def handoff_role(rec: dict):
    """'sent' / 'received' from the record's own words (phase or detail), else None."""
    for field in ("detail", "phase"):
        text = str(rec.get(field) or "")
        if text.startswith("handoff.sent") or text.endswith("handoff.sent"):
            return "sent"
        if text.startswith("handoff.received") or text.endswith("handoff.received"):
            return "received"
    return None


def _is_invocation(rec: dict) -> bool:
    return bool(rec.get("aws.request_id") and rec.get("runtime.session_id"))


def _rid(rec: dict) -> str:
    return rec.get("record_id") or "ledger:%s:%s" % (rec.get("correlation_id"), rec.get("seq"))


def _seconds(a: str, b: str):
    return abs((_clocks.parse_utc(a) - _clocks.parse_utc(b)).total_seconds())


def _group(records, key):
    out = {}
    for rec in records:
        v = rec.get(key)
        if v:
            out.setdefault(v, []).append(rec)
    return out


def stitch(records, join_tolerance_s=None) -> dict:
    """-> {"run_index": [rows], "unjoined": [facts]} (both sorted; a re-run is byte-identical)."""
    records = list(records)
    runs = {}
    for rec in records:
        runs.setdefault(run_of(rec) or "unknown", []).append(rec)
    resolved_by_trace, resolved_by_call = {}, {}
    for rid, group in runs.items():
        if rid.startswith("unresolved:") or rid == "unknown":
            continue
        for rec in group:
            if rec.get("trace.id"):
                resolved_by_trace.setdefault(rec["trace.id"], set()).add(rid)
            for call in str(rec.get("call.id") or "").split(","):      # a delivery-log line names several
                if call.strip():
                    resolved_by_call.setdefault(call.strip(), set()).add(rid)
    unjoined = []
    rows = {}

    def row_for(rid):
        if rid not in rows:
            rows[rid] = {"run_id": rid, "family": _family(rid), "record_ids": [], "links": [],
                         "resolved_from": [], "invocations": [], "retry_suspects": []}
        return rows[rid]

    def link(rid, key, value, ids):
        row_for(rid)["links"].append({"key": key, "value": value, "record_ids": sorted(set(ids))})

    for rid in sorted(runs):
        group = runs[rid]
        row = row_for(rid)
        row["record_ids"] = sorted(set(_rid(r) for r in group))
        row["links"].append({"key": "correlation_id", "value": rid, "record_ids": row["record_ids"]})
        # key 2: action id
        for call, recs in sorted(_group(group, "call.id").items()):
            if len(recs) > 1:
                link(rid, "call.id", call, [_rid(r) for r in recs])
        # key 3 and 2 for unresolved groups: resolve through another run's trace / action id
        if rid.startswith("unresolved:"):
            trace = rid[len("unresolved:"):]
            by_trace = set(resolved_by_trace.get(trace, ()))
            by_call = set()
            for rec in group:
                by_call |= resolved_by_call.get(rec.get("call.id"), set())
            targets = by_trace | by_call
            if len(targets) == 1:
                target = sorted(targets)[0]
                row["resolved_to"] = target
                row_for(target)["resolved_from"].append(rid)
                if by_trace:
                    link(target, "trace.id", trace, [_rid(r) for r in group])
                else:
                    # a gateway-minted root trace (the ifabric-assure runtime sends no baggage, b6b): joined by
                    # ACTION ID to the record that named it (the Assurance analysis line of the incident's finding)
                    row["resolved_by"] = "call.id"
                    calls = sorted(set(r.get("call.id") for r in group if r.get("call.id")))
                    namers = [r for r in runs.get(target, ()) if set(str(r.get("call.id") or "").split(",")) & set(calls)]
                    row["attributed_to"] = sorted(set(r.get("finding.id") for r in namers if r.get("finding.id")))
                    for call in calls:
                        link(target, "call.id", call, [_rid(r) for r in group] + [_rid(r) for r in namers])
            else:
                unjoined.append({"key": "trace.id", "value": trace, "present_in": ["records"],
                                 "missing_from": ["a run's records"] if not targets else ["unique run (ambiguous)"],
                                 "run_id": rid})
        # key 4: handoff ids
        sent, received = {}, {}
        for rec in group:
            h = rec.get("handoff.id")
            if not h:
                continue
            try:
                hcid, _ = _ids.parse_handoff_id(h)
            except ValueError:
                unjoined.append({"key": "handoff.id", "value": h, "present_in": [_rid(rec)],
                                 "missing_from": ["a parseable handoff id"], "run_id": rid})
                continue
            if hcid != rid:
                unjoined.append({"key": "handoff.id", "value": h, "present_in": [_rid(rec)],
                                 "missing_from": ["run " + rid], "run_id": rid})
            role = handoff_role(rec)
            if role == "sent":
                sent.setdefault(h, []).append(rec)
            elif role == "received":
                received.setdefault(h, []).append(rec)
        for h in sorted(set(sent) | set(received)):
            if h in sent and h in received:
                link(rid, "handoff.id", h, [_rid(r) for r in sent[h] + received[h]])
            else:
                unjoined.append({"key": "handoff.id", "value": h,
                                 "present_in": ["handoff.sent" if h in sent else "handoff.received"],
                                 "missing_from": ["handoff.received" if h in sent else "handoff.sent"], "run_id": rid})
        # key 5: the AWS invocation records
        by_session = _group([r for r in group if _is_invocation(r)], "runtime.session_id")
        sent_by_session = {}
        for recs in sent.values():
            for r in recs:
                if r.get("runtime.session_id"):
                    sent_by_session.setdefault(r["runtime.session_id"], []).append(r)
        for session in sorted(by_session):
            inv = by_session[session]
            row["invocations"].append({"runtime.session_id": session, "aws.request_ids":
                                       sorted(r["aws.request_id"] for r in inv)})
            if len(set(r["aws.request_id"] for r in inv)) > 1:
                row["retry_suspects"].append(session)
            if session in sent_by_session:
                link(rid, "runtime.session_id", session,
                     [_rid(r) for r in inv + sent_by_session[session]])
            elif not rid.startswith("unattributed:"):
                unjoined.append({"key": "runtime.session_id", "value": session,
                                 "present_in": ["aws-invocations"], "missing_from": ["handoff.sent"], "run_id": rid})
            if join_tolerance_s is not None:
                for r in inv:
                    near = [x for xs in received.values() for x in xs
                            if x.get("runtime.session_id") in (None, session)
                            and _seconds(x.get("ts") or x.get("observed.at"), r["observed.at"]) <= join_tolerance_s]
                    if near:
                        link(rid, "eventTime~handoff.received", r["observed.at"],
                             [_rid(r)] + [_rid(x) for x in near])
        # key 6: findings and assessments
        for key in ("finding.id", "assessment.id"):
            for value, recs in sorted(_group(group, key).items()):
                if len(recs) > 1:
                    link(rid, key, value, [_rid(r) for r in recs])
        row["links"].sort(key=lambda l: (l["key"], str(l["value"])))
        row["resolved_from"].sort()
    out_rows = [rows[k] for k in sorted(rows)]
    unjoined.sort(key=lambda f: (f["key"], str(f["value"]), f.get("run_id", "")))
    return {"run_index": out_rows, "unjoined": unjoined}


def _family(rid: str) -> str:
    if rid.startswith("unattributed:"):
        return "unattributed"
    if rid.startswith("unresolved:"):
        return "unresolved"
    if rid.startswith("fault-"):
        return "fault"
    for fam in _ids.CID_FAMILIES:
        if rid.startswith(fam + "-"):
            return fam
    return "other"


def dumps_rows(rows) -> str:
    """JSONL, sorted keys, one row per line, trailing newline (byte-stable)."""
    return "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows)

"""The corroboration report (ARCH §3.6 outputs, §9.2; plan T4.4 Ph2): `derived/corroboration/<CID>.json`. Stdlib, 3.9.

Per run, over one snapshot's records and the stitcher's output, it SHOWS where independent sources agree and where
they do not. It forms no verdict and resolves nothing: a disagreement is listed with both sides' record ids.
Sections:
  call_joins     per gateway action id: which of {ours, gateway} hold it, and tokens in/out on each side
  guardrail      each gateway BLOCKED_GUARDRAIL (an inference from 200 + 0/0 tokens) next to our record's raw
                 `finish_reason` for the same action id; the link or its absence is the fact (A5)
  invocations    AWS InvokeAgentRuntime records joined to handoff.sent by CID + session id; retry suspects
  mon02          blocked tool calls that have a span (prooflab.stitch.mon02)
  raw_check      (optional) each copy's `raw:<path>` / `line:<n>` / `sha256:<hex>` refs against the raw capture
  disagreements  the flat list of every mismatch above (never empty-by-omission: [] means none found)
Output is canonical JSON (sorted keys, fixed separators, trailing newline): a re-run is byte-identical.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

from prooflab.stitch import mon02 as _mon02
from prooflab.stitch import stitcher as _st

SCHEMA = "ifabric.corroboration/1"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def file_name(run_id: str) -> str:
    return _UNSAFE.sub("_", run_id) + ".json"


def _rid(rec):
    return _st._rid(rec)


def _is_gateway(rec):
    return rec.get("authorship") == "PLATFORM" and rec.get("observed.clock") == _mon02.GATEWAY_CLOCK


def _tokens(rec):
    return (rec.get("tokens.in"), rec.get("tokens.out"))


def _call_joins(group):
    ours, gw = {}, {}
    for rec in group:
        call = rec.get("call.id")
        if not call:
            continue
        (gw if _is_gateway(rec) else ours).setdefault(call, []).append(rec)
    joins, disagreements = [], []
    for call in sorted(set(ours) | set(gw)):
        o = [r for r in ours.get(call, []) if r.get("tokens.in") is not None or r.get("tokens.out") is not None]
        g = [r for r in gw.get(call, []) if r.get("tokens.in") is not None or r.get("tokens.out") is not None]
        row = {"call.id": call,
               "present_in": [s for s, d in (("ours", ours), ("gateway", gw)) if call in d],
               "ours_records": sorted(_rid(r) for r in ours.get(call, [])),
               "gateway_records": sorted(_rid(r) for r in gw.get(call, [])),
               "ours_tokens": sorted(set(_tokens(r) for r in o)),
               "gateway_tokens": sorted(set(_tokens(r) for r in g))}
        if call not in ours or call not in gw:
            disagreements.append({"kind": "call-one-sided", "call.id": call,
                                  "present_in": row["present_in"],
                                  "missing_from": ["gateway" if call in ours else "ours"]})
        elif row["ours_tokens"] and row["gateway_tokens"] and set(row["ours_tokens"]) != set(row["gateway_tokens"]):
            disagreements.append({"kind": "tokens", "call.id": call, "ours": row["ours_tokens"],
                                  "gateway": row["gateway_tokens"]})
        joins.append(row)
    return joins, disagreements


def _guardrail(group):
    by_call = {}
    for rec in group:
        if rec.get("call.id") and not _is_gateway(rec):
            by_call.setdefault(rec["call.id"], []).append(rec)
    out, dis = [], []
    for rec in group:
        if not (_is_gateway(rec) and rec.get("outcome.real") == "BLOCKED_GUARDRAIL"):
            continue
        call = rec.get("call.id")
        mine = by_call.get(call, []) if call else []
        finishes = sorted(set(str(m.get("outcome.finish_reason")) for m in mine if m.get("outcome.finish_reason")))
        linked = bool(finishes)
        out.append({"call.id": call, "gateway_record": _rid(rec), "basis": "inferred: http 200 + 0/0 tokens",
                    "ours_records": sorted(_rid(m) for m in mine), "ours_finish_reasons": finishes,
                    "linked_by_action_id": linked})
        if not linked:
            dis.append({"kind": "guardrail-unlinked", "call.id": call, "gateway_record": _rid(rec)})
    out.sort(key=lambda r: (str(r["call.id"]), r["gateway_record"]))
    return out, dis


def raw_check(group, read_raw):
    """`read_raw(path) -> text | None`. Each record's raw ref is checked: the line at `line:<n>` must hash to `sha256:`."""
    checked, bad = 0, []
    cache = {}
    for rec in group:
        refs = rec.get("source.refs") or []
        path = next((r[4:] for r in refs if isinstance(r, str) and r.startswith("raw:")), None)
        line = next((r[5:] for r in refs if isinstance(r, str) and r.startswith("line:")), None)
        want = next((r[7:] for r in refs if isinstance(r, str) and r.startswith("sha256:")), None)
        if not (path and line and want and line.isdigit()):
            continue
        if path not in cache:
            text = read_raw(path)
            cache[path] = None if text is None else text.splitlines()
        lines = cache[path]
        checked += 1
        got = None
        if lines is not None and 1 <= int(line) <= len(lines):
            got = hashlib.sha256(lines[int(line) - 1].encode("utf-8")).hexdigest()
        if got != want:
            bad.append({"kind": "raw-mismatch", "record_id": _rid(rec), "raw": path, "line": int(line),
                        "raw_available": lines is not None, "expected_sha256": want, "found_sha256": got})
    return {"checked": checked, "mismatches": sorted(bad, key=lambda b: (b["record_id"]))}


def corroborate(records, stitched=None, join_tolerance_s=None, read_raw=None) -> dict:
    """-> {run_id: report dict}. Pure; the same records give the same dicts."""
    records = list(records)
    stitched = stitched if stitched is not None else _st.stitch(records, join_tolerance_s)
    runs = {}
    for rec in records:
        runs.setdefault(_st.run_of(rec) or "unknown", []).append(rec)
    mon = {}
    for m in _mon02.find_mismatches(records):
        mon.setdefault(m["run_id"], []).append(m)
    gaps = {}
    for f in stitched["unjoined"]:
        gaps.setdefault(f.get("run_id"), []).append(f)
    out = {}
    for row in stitched["run_index"]:
        rid = row["run_id"]
        group = runs.get(rid, [])
        joins, dis = _call_joins(group)
        guard, gdis = _guardrail(group)
        dis = dis + gdis
        invocations = {"joined_sessions": sorted(l["value"] for l in row["links"] if l["key"] == "runtime.session_id"),
                       "all": row["invocations"], "retry_suspects": row["retry_suspects"],
                       "unjoined": [f for f in gaps.get(rid, []) if f["key"] in ("runtime.session_id", "handoff.id")]}
        for s in row["retry_suspects"]:
            dis.append({"kind": "retry-suspect", "runtime.session_id": s})
        for f in invocations["unjoined"]:
            dis.append({"kind": "link-gap", "key": f["key"], "value": f["value"], "missing_from": f["missing_from"]})
        mm = mon.get(rid, [])
        for m in mm:
            dis.append({"kind": "mon-02", "call.id": m["call.id"], "blocked_record": m["blocked_record"]})
        doc = {"schema": SCHEMA, "run_id": rid, "family": row["family"], "record_count": len(group),
               "call_joins": joins, "guardrail": guard, "invocations": invocations, "mon02": mm}
        if read_raw is not None:
            rc = raw_check(group, read_raw)
            doc["raw_check"] = rc
            dis.extend(rc["mismatches"])
        doc["disagreements"] = sorted(dis, key=lambda d: json.dumps(d, sort_keys=True))
        out[rid] = doc
    return out


def dumps(doc) -> str:
    return json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def write(out_dir: str, reports: dict) -> list:
    """Writes `<out_dir>/derived/corroboration/<CID>.json`; returns the paths, sorted."""
    d = os.path.join(out_dir, "derived", "corroboration")
    os.makedirs(d, exist_ok=True)
    paths = []
    for rid in sorted(reports):
        p = os.path.join(d, file_name(rid))
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(dumps(reports[rid]))
        paths.append(p)
    return paths

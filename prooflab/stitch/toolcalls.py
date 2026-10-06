"""The tool-call join (PR-39; ARCH 5.2, C7): our EP-3 tool records <-> the gateway's MCP `tools/call` spans. Stdlib, 3.9.

Why: our EP-3 tool records carry no gateway action id (the response header is absent), so a gateway `tools/call` span
could never match one. Only `tools/call` spans are governed ACTIONS (C7); the MCP handshake spans (initialize,
tools/list, notifications/*) are not, and are never offered here.

A span is a gateway `observation` record whose detail reads `gateway request tools/call /mcp/<target> status <n>`
(prooflab.store.observations); its end is `observed.at`. A unit is one tool call of ours: the EP-3 action records that
share a `tool.use_id` (the `before` and `after` records), with `tool.name` = `<target>___<tool>`.

A span joins a unit when ALL hold: same run; tool name's target == the span's target; the trace ids agree when both
carry one; the span end lies inside the unit's window [first emitted.at - slack, last emitted.at + slack] (a unit with
no `after` record has an open end). One to one: spans are taken in (end, action id) order; among the candidate units
the one whose window end is nearest the span end wins, then the smaller use id. The same input always gives the same
pairs. `slack_ms` is the caller's (a register/pin value, `tool_join_slack_ms`); there is no literal here.
Never changes a record: `with_call_ids` returns copies.
"""
from __future__ import annotations

import re

from prooflab.contract import clocks as _clocks

_SPAN = re.compile(r"^gateway request tools/call /mcp/(?P<target>\S+) status \S+$")


def _t(s):
    try:
        return _clocks.parse_utc(s)
    except (ValueError, TypeError):
        return None


def _ms(a, b):
    return (a - b).total_seconds() * 1000.0


def tool_spans(records):
    """Gateway `tools/call` observation spans: [{action_id, target, end, trace, run}], sorted by (end, action id)."""
    out = []
    for r in records or ():
        if r.get("authorship") != "PLATFORM" or r.get("record_kind") != "observation" or not r.get("call.id"):
            continue
        m = _SPAN.match(str(r.get("detail") or ""))
        end = _t(r.get("observed.at"))
        if m and end is not None:
            out.append({"action_id": r["call.id"], "target": m.group("target"), "end": end,
                        "trace": r.get("trace.id"), "run": r.get("run.id") or r.get("correlation_id")})
    return sorted(out, key=lambda s: (s["end"], s["action_id"]))


def tool_units(records):
    """Our tool calls without a gateway action id: [{use_id, name, target, start, end|None, trace, run, agent}]."""
    groups = {}
    for r in records or ():
        if r.get("authorship", "TESTIMONY") != "TESTIMONY" or r.get("ep.id") != "EP-3" or r.get("record_kind") != "action":
            continue
        if not (r.get("tool.use_id") and r.get("tool.name")):
            continue
        groups.setdefault((r.get("run.id") or r.get("correlation_id"), r["tool.use_id"]), []).append(r)
    out = []
    for (run, use), recs in groups.items():
        if any(x.get("call.id") for x in recs):
            continue                                   # already carries the gateway id: nothing to join
        ts = sorted(t for t in (_t(x.get("emitted.at")) for x in recs) if t is not None)
        if not ts:
            continue
        name = recs[0]["tool.name"]
        after = [_t(x.get("emitted.at")) for x in recs if x.get("tool.phase") == "after"]
        after = [t for t in after if t is not None]
        out.append({"use_id": use, "name": name, "target": name.split("___", 1)[0], "start": ts[0],
                    "end": max(after) if after else None, "trace": recs[0].get("trace.id"), "run": run,
                    "agent": recs[0].get("actor.id")})
    return sorted(out, key=lambda u: (u["start"], u["use_id"]))


def join(spans, units, slack_ms=0):
    """-> {"pairs": [(action_id, use_id, run)], "unmatched_spans": [action_id], "unmatched_units": [use_id]}."""
    slack = slack_ms or 0
    free = list(units)
    pairs, lost = [], []
    for s in spans:
        best = None
        for u in free:
            if u["run"] != s["run"] or u["target"] != s["target"]:
                continue
            if u["trace"] and s["trace"] and u["trace"] != s["trace"]:
                continue
            if _ms(s["end"], u["start"]) < -slack:
                continue
            if u["end"] is not None and _ms(s["end"], u["end"]) > slack:
                continue
            dist = abs(_ms(s["end"], u["end"])) if u["end"] is not None else float("inf")
            key = (dist, u["use_id"])
            if best is None or key < best[0]:
                best = (key, u)
        if best is None:
            lost.append(s["action_id"])
            continue
        free.remove(best[1])
        pairs.append((s["action_id"], best[1]["use_id"], s["run"]))
    return {"pairs": pairs, "unmatched_spans": lost, "unmatched_units": sorted(u["use_id"] for u in free)}


def with_call_ids(records, pairs):
    """Copies of `records` where each joined unit's EP-3 `after` record carries the span's action id as call.id.
    A before-only unit (the after record suppressed, N4) still consumes its span but is never stamped, so C7 sees the
    call as unrecorded. Mirrors adapters/runtime/tool_call.py, which sets call.id only on the after record."""
    ids = dict(((run, use), aid) for aid, use, run in pairs)
    out = []
    for r in records or ():
        key = (r.get("run.id") or r.get("correlation_id"), r.get("tool.use_id"))
        if (r.get("ep.id") == "EP-3" and r.get("tool.phase") == "after" and key in ids
                and not r.get("call.id")):
            r = dict(r)
            r["call.id"] = ids[key]
        out.append(r)
    return out


def join_records(store_records, ours, slack_ms=0):
    """Convenience: join the run's gateway spans (in `store_records`) to our records `ours` -> (ours', result)."""
    res = join(tool_spans(store_records), tool_units(ours), slack_ms)
    return with_call_ids(ours, res["pairs"]), res

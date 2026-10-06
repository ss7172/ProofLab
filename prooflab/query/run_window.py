"""RUN + WINDOW: 'show me control 16 for run <RUN> between <T1> and <T2>' (PR-53). Stdlib only, Python 3.9, offline.

compose(pack, control, cid, t1, t2) -> answer dict (kind "control-run-window"); render(ans) -> text lines.
C16 is a per-run cap: the verdict shown is the run's STORED per-run verdict, for the whole run; a partial window cannot
change it. The window only selects the evidence slice inside [T1, T2): the model calls (gateway llm spans, deduplicated
by action id exactly as the C16 evaluator does), the tokens spent inside the window, the run's cumulative committed
tokens at T1 and at T2 against the cap, every EP-1 decision in the window, and each record id + raw ref (verify
without us). No LLM, no new verdict: deterministic arithmetic over store/records.jsonl.

annotate_window(...) is the window-only hook: a run that overlaps [T1, T2) but does not start inside it is listed
('overlaps the window but is not wholly inside it') with its run verdict, instead of only 'no run in scope'.
"""
from __future__ import annotations

import re

from prooflab.contract import verdicts as V
from prooflab.query import engine as E

KIND = "control-run-window"
SUPPORTED = ("C16",)
_SPLIT = re.compile(r"committed=(\d+)\s+reserved=(\d+)\s+bound=(\d+)")
_SPLIT_TEXT = re.compile(r"committed (\d+) \+ reserved (\d+) \+ bound (\d+)")
NOT_DEFINED = "run+window is defined for C16; for C7/C9 use --run <RUN> or --window <T1>..<T2>"


def _k(t):
    return E._utc_key(t)


def _at(r):
    """When the record says the thing happened: the gateway's clock for a platform span, else the emitter's clock."""
    if r.get("authorship") == "PLATFORM" and r.get("observed.at"):
        return r["observed.at"]
    return r.get("emitted.at") or r.get("ts") or r.get("observed.at")


def _in(t, lo, hi):
    k = _k(t)
    return k is not None and lo <= k < hi


def _store(pack, cid):
    return [r for r in pack.by_cid.get(cid, []) if r.get("record_kind") != "assessment"]


def run_bounds(pack, cid):
    """(start, end) of the run from its own records, the post-run EP-2 replay (authorship ASSURANCE) left out."""
    times = [_at(r) for r in _store(pack, cid) if r.get("authorship") != "ASSURANCE"]
    times = sorted((t for t in times if _k(t)), key=_k)
    if not times:
        return E.run_start(pack, cid), E.run_end(pack, cid)
    return times[0], times[-1]


def _assessment(pack, control, cid):
    found = pack.assessments_for(control, ("run",), cid)
    return found[-1] if found else None


def _split(d):
    m = _SPLIT.search(str(d.get("detail") or "")) or _SPLIT_TEXT.search(str(d.get("reason") or d.get("detail") or ""))
    return tuple(int(x) for x in m.groups()) if m else (None, None, None)


def _raw(r):
    refs = [x for x in (r.get("source.refs") or []) if isinstance(x, str)]
    raw = [x for x in refs if x.startswith("raw:")]
    return " ".join(refs) if raw else None


def _calls(pack, cid):
    """The C16 evaluator's own call list for the run (assess_snapshot.run_facts + c16._model_calls), with record ids."""
    from prooflab.evaluators import c16
    from prooflab.query import assess_snapshot as S
    recs = _store(pack, cid)
    by_id, noid, _other, conflicts = c16._model_calls(S.run_facts(recs)["calls"])
    span_ids, raw_refs, adapter_ids = {}, {}, {}
    for r in recs:
        aid = r.get("call.id")
        if not aid:
            continue
        if S._model_call_span(r):
            span_ids.setdefault(aid, []).append(r.get("record_id"))
            raw_refs.setdefault(aid, _raw(r))
        elif r.get("record_kind") == "action" and r.get("ep.id") == "EP-1":
            adapter_ids.setdefault(aid, []).append(r.get("record_id"))
    out = []
    for aid, c in by_id.items():
        out.append({"action_id": aid, "at": c["end"] or c["start"], "tokens_in": c["tin"], "tokens_out": c["tout"],
                    "tokens": c["tokens"], "http_status": c["status"], "model": c["model"],
                    "span_record_ids": [x for x in span_ids.get(aid, []) if x],
                    "adapter_record_ids": [x for x in adapter_ids.get(aid, []) if x], "raw_ref": raw_refs.get(aid)})
    out.sort(key=lambda c: (_k(c["at"]) or "", c["action_id"]))
    return out, noid, conflicts


def _committed_before(calls, key):
    """(tokens committed by calls ending before `key`, calls counted, calls with missing usage)."""
    total, n, missing = 0, 0, 0
    for c in calls:
        k = _k(c["at"])
        if k is None or k >= key:
            continue
        n += 1
        if c["tokens"] is None:
            missing += 1
        else:
            total += c["tokens"]
    return total, n, missing


def _overlap(lo, hi, start, end):
    s, e = _k(start), _k(end)
    if s is None or e is None:
        return "unknown"
    if hi <= s or lo > e:
        return "none"
    if lo <= s and e < hi:
        return "covers-run"
    if s <= lo and hi <= e:
        return "inside-run"
    return "partial"


def _fmt(n):
    return "unknown" if n is None else ("{:,}".format(n) if isinstance(n, int) else str(n))


def compose(pack, control, cid, t1, t2):
    control = E.norm_control(control)
    if control not in E.CONTROLS:
        return {"kind": "error", "verdict": V.NOT_ASSESSED, "message": "unsupported control %r (C16, C7, C9)" % control}
    if not E.run_known(pack, cid):
        return {"kind": "error", "verdict": V.NOT_ASSESSED, "message": "unknown run %s: not in this pack" % cid}
    lo, hi = _k(t1), _k(t2)
    if not lo or not hi or not lo < hi:
        return {"kind": "error", "verdict": V.NOT_ASSESSED, "message": "the window needs T1 < T2 in full UTC (...Z)"}
    a = _assessment(pack, control, cid)
    run_verdict = a["verdict"] if a else V.NOT_ASSESSED
    if control not in SUPPORTED:
        return {"kind": "error", "control": control, "run": cid, "window": [t1, t2], "verdict": V.NOT_ASSESSED,
                "run_verdict": run_verdict, "message": NOT_DEFINED}
    start, end = run_bounds(pack, cid)
    m = (a or {}).get("measured") or {}
    cap = E._num((a or {}).get("limit"))
    cap = int(cap) if isinstance(cap, float) and cap.is_integer() else cap
    calls, noid, conflicts = _calls(pack, cid)
    run_total = sum(c["tokens"] for c in calls if c["tokens"] is not None)
    in_win = [c for c in calls if _in(c["at"], lo, hi)]
    win_tokens = sum(c["tokens"] for c in in_win if c["tokens"] is not None)
    at_t1, _n1, miss1 = _committed_before(calls, lo)
    at_t2, _n2, miss2 = _committed_before(calls, hi)
    decisions = []
    ep2 = 0
    for d in _store(pack, cid):
        if d.get("record_kind") != "decision" or d.get("control.ref") not in (None, control):
            continue
        if d.get("ep.id") != "EP-1":
            ep2 += 1 if d.get("ep.id") == "EP-2" else 0
            continue
        when = d.get("emitted.at") or d.get("ts")
        if not _in(when, lo, hi):
            continue
        committed, reserved, bound = _split(d)
        decisions.append({"record_id": d.get("record_id"), "at": when, "verdict": d.get("verdict"),
                          "action": d.get("inline.action"), "mode": d.get("inline.mode"), "actor": d.get("actor.id"),
                          "call_id": d.get("call.id"), "committed": committed, "reserved": reserved, "bound": bound,
                          "bound_basis": d.get("inline.bound_basis"), "projected": E._num(d.get("measured.value")),
                          "cap": d.get("inline.limit_value"), "reason": d.get("reason")})
    decisions.sort(key=lambda x: (_k(x["at"]) or "", str(x["record_id"])))
    overlap = _overlap(lo, hi, start, end)
    gaps = []
    if a is None:
        gaps.append("no stored %s assessment for this run: no run verdict to show" % control)
    if noid:
        gaps.append("%d model span(s) without an action id (cannot be deduplicated)" % noid)
    if conflicts:
        gaps.append("conflicting duplicate usage for action id(s) %s (the larger figure kept, as the evaluator does)" % ", ".join(conflicts))
    if miss1 or miss2:
        gaps.append("a served call before T2 has missing usage: the cumulative figure is a lower bound")
    if a and m.get("value") is not None and E._num(m.get("value")) != run_total:
        gaps.append("the slice's run total %s differs from the stored measured %s" % (run_total, m.get("value")))
    ans = {
        "kind": KIND, "control": control, "run": cid, "window": [t1, t2], "window_rule": "[T1, T2) half-open; a call "
        "counts at its gateway span time (observed.at), a decision at its emitted.at",
        "verdict": run_verdict, "run_verdict": run_verdict, "verdict_scope": "run",
        "verdict_note": "%s is a per-run cap: the verdict is the stored verdict for the WHOLE run; a partial window "
                        "cannot change it. The window only selects the evidence slice below." % control,
        "assessment_id": (a or {}).get("assessment_id"), "assessment_file": (a or {}).get("_file"),
        "threshold_version": (a or {}).get("threshold_version"), "cap": cap, "unit": m.get("unit") or "tokens",
        "run_measured": E._num(m.get("value")), "run_total_from_calls": run_total, "run_calls": len(calls),
        "run_start": start, "run_end": end, "first_span_at": (a or {}).get("scope_start"),
        "last_span_at": (a or {}).get("scope_end"), "overlap": overlap,
        "slice": {"calls": in_win, "call_count": len(in_win), "tokens": win_tokens,
                  "committed_at_t1": at_t1, "committed_at_t2": at_t2,
                  "headroom_at_t2": (cap - at_t2) if isinstance(cap, (int, float)) else None,
                  "decisions": decisions, "allow": len([d for d in decisions if d["verdict"] == "ALLOW"]),
                  "deny": len([d for d in decisions if d["verdict"] == "DENY"])},
        "ep2_replay_decisions": ep2, "gaps": gaps,
        "verify": "store/records.jsonl: grep each record id; each span's raw ref names raw/aws-spans/<run>/spans.jsonl "
                  "line + sha256; committed at T = sum(tokens_in + tokens_out) of the run's deduplicated llm spans "
                  "with observed.at < T",
    }
    if overlap == "none":
        ans["message"] = "the window %s .. %s does not overlap run %s (run %s .. %s)" % (t1, t2, cid, start, end)
    return ans


def render(a):
    if a.get("kind") != KIND:
        lines = ["%s: %s" % (a.get("control", "-"), a.get("message") or a.get("verdict"))]
        if a.get("run_verdict"):
            lines.append("run verdict (whole run, stored): %s" % a["run_verdict"])
        return lines
    s = a["slice"]
    cap = a["cap"]
    lines = [
        "CONTROL %s  RUN %s  WINDOW %s .. %s" % (a["control"], a["run"], a["window"][0], a["window"][1]),
        "RUN VERDICT (whole run, stored): %s%s" % (a["run_verdict"],
                                                   ("  [%s]" % a["assessment_file"]) if a.get("assessment_file") else ""),
        a["verdict_note"],
        "run: %s .. %s (model spans %s .. %s); %s calls, %s %s committed of cap %s" % (
            a["run_start"], a["run_end"], a.get("first_span_at") or "?", a.get("last_span_at") or "?",
            a["run_calls"], _fmt(a["run_total_from_calls"]), a["unit"], _fmt(cap)),
    ]
    if a["overlap"] == "none":
        lines.append("WINDOW: %s" % a["message"])
        lines += ["gap: %s" % g for g in a["gaps"]]
        return lines
    lines += [
        "window overlap with the run: %s (%s)" % (a["overlap"], a["window_rule"]),
        "by %s the run had committed %s of %s %s; by %s it had committed %s of %s (headroom %s)" % (
            a["window"][0], _fmt(s["committed_at_t1"]), _fmt(cap), a["unit"], a["window"][1], _fmt(s["committed_at_t2"]),
            _fmt(cap), _fmt(s["headroom_at_t2"])),
        "inside the window: %d model call(s), %s %s spent" % (s["call_count"], _fmt(s["tokens"]), a["unit"]),
    ]
    for c in s["calls"]:
        lines.append("  call %s at %s: %s in + %s out = %s (HTTP %s) span %s adapter %s raw %s" % (
            c["action_id"], c["at"], _fmt(c["tokens_in"]), _fmt(c["tokens_out"]), _fmt(c["tokens"]), c["http_status"],
            ",".join(c["span_record_ids"]) or "-", ",".join(c["adapter_record_ids"]) or "-", c["raw_ref"] or "-"))
    lines.append("EP-1 decisions inside the window: %d (%d ALLOW, %d DENY)" % (len(s["decisions"]), s["allow"], s["deny"]))
    for d in s["decisions"]:
        lines.append("  %s %s %s (%s): committed %s + reserved %s + bound %s (%s) = %s vs cap %s  actor %s call %s [%s]" % (
            d["at"], d["verdict"], d["action"], d["mode"], _fmt(d["committed"]), _fmt(d["reserved"]), _fmt(d["bound"]),
            d["bound_basis"], _fmt(d["projected"]), _fmt(d["cap"]), d["actor"], d["call_id"] or "none (halted before a call)",
            d["record_id"]))
    if a["ep2_replay_decisions"]:
        lines.append("EP-2 post-run replay: %d decision(s) for the whole run (not window evidence; see --run)" % a["ep2_replay_decisions"])
    lines += ["gap: %s" % g for g in a["gaps"]]
    lines.append("verify without us: %s" % a["verify"])
    return lines


def annotate_window(pack, control, bounds, counted, listed, gaps):
    """Window-only hook: list each run that overlaps [T1, T2) but does not start inside it (so it is not counted)."""
    lo, hi = _k(bounds[0]), _k(bounds[1])
    seen = set(a["scope_id"] for a in counted) | set(r.get("scope") for r in listed)
    cids = sorted(set([a["scope_id"] for a in pack.assessments_for(control, ("run",))] +
                      [E._cid(r) for r in pack.run_index if E._cid(r)]))
    added = []
    for cid in cids:
        if cid in seen:
            continue
        start, end = run_bounds(pack, cid)
        if _overlap(lo, hi, start, end) in ("none", "unknown", "covers-run"):
            continue
        a = _assessment(pack, control, cid)
        added.append(cid)
        listed.append({"scope": cid, "reason": "overlaps the window but is not wholly inside it (run %s .. %s): per-run "
                       "control; its run verdict is %s; ask for run+window for the slice ('control %s for run %s between "
                       "%s and %s')" % (start, end, a["verdict"] if a else V.NOT_ASSESSED, control[1:], cid,
                                        bounds[0], bounds[1])})
    if added and any(str(g).startswith("no run in scope") for g in gaps):
        gaps.append("%d run(s) overlap the window but start before it: listed, not counted (per-run control)" % len(added))
    return added

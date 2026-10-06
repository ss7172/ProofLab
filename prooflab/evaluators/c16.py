"""c16.py: the C16 tester (ACN-COST-001), off the path (ARCH 3.4, 5.1, 11). Pure, stateless, stdlib, Python 3.9.

Every comparison of tokens with a cap goes through `c16_core.compare`; this module has no arithmetic verdict of
its own and no number from the register: caps, tiers and the mode come from the PinnedC16 passed in.

    assess_run(run_id, calls, scenario_attrs, decisions, pin, completeness, as_of,
               evaluator_sha256="", snapshot_id="") -> Assessment
    assess_window(t1, t2, run_assessments, pins_by_version, as_of, condition=None,
                  evaluator_sha256="", snapshot_id="") -> Assessment                         (E-06)
    parse_tier_rule(text) / derive_tier(attrs, rule, pin)

Inputs (plain mappings or objects; the field names are the contract's):
 calls            the gateway's per-call spans for the run: action_id, listener ("llm" counted; others ignored),
                  model, tokens_in, tokens_out, http_status, start, end (UTC), optional handoff_id.
                  Deduplicated by action id (a conflicting duplicate keeps the larger figure and is listed).
                  A served (2xx) call with 0/0 or missing tokens is MISSING usage, never zero, unless its action id
                  is in completeness["blocked_action_ids"] (a refusal/guardrail block known from another source).
 scenario_attrs   {"attrs": {..}, "tier_rule": "<text>" | {"rules": [...], "default": t}, "envelope_tier": t,
                  "provenance": P, "condition": c}; the tier is re-derived from attrs with the frozen rule, never
                  taken from the envelope; a mismatch is listed in `exceptions` (I-10, a reconciliation).
 decisions        decision records (contract field names: ep.id, call.id, verdict, inline.action, inline.mode,
                  handoff.id, emitted.at, run.id) from EP-1 (inline) and EP-2 (replay); matched call by call.
 completeness     {"expected_action_ids": [..our usage records..], "spans_ingested": bool, "blocked_action_ids": [..],
                  "clock_skew_ms": n (optional, for the after-halt check)}.
Verdict: known subtotal over cap(tier) -> BREACHED even with gaps; else any missing usage or missing span ->
INDETERMINATE; no model span -> INDETERMINATE; else SATISFIED. Headroom (committed - cap) is always in `measured`.
"""
from __future__ import annotations

from prooflab.contract import clocks as _clocks
from prooflab.evaluators import claim as _claim
from prooflab.evaluators.c16_core import compare

NAME = "prooflab.evaluators.c16"
CONTROL_REF = "C16"
FORMULA = "sum(tokens_in + tokens_out) over model spans, dedup by action id, compare(total, cap(tier))"


def _g(o, k, d=None):
    if isinstance(o, dict):
        return o.get(k, d)
    return getattr(o, k, d)


def _n(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _ts(v):
    try:
        return _clocks.parse_utc(v)
    except (ValueError, TypeError):
        return None


def parse_tier_rule(text):
    """'a=x&b=y->tier;c=z->tier2;*->tier3' -> {"rules": [({a: x, b: y}, tier), ...], "default": tier3 | None}.
    First matching rule wins; '*' is the catch-all."""
    rules, default = [], None
    for part in (text or "").split(";"):
        if "->" not in part:
            continue
        cond, tier = part.rsplit("->", 1)
        cond, tier = cond.strip(), tier.strip()
        if not tier:
            continue
        if cond == "*":
            default = tier
            continue
        when = {}
        for kv in cond.split("&"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                when[k.strip()] = v.strip()
        rules.append((when, tier))
    return {"rules": rules, "default": default}


def derive_tier(attrs, rule, pin):
    """(tier, basis): the tier from the declared attributes and the frozen rule; the pin's default_tier otherwise."""
    if isinstance(rule, str):
        rule = parse_tier_rule(rule)
    if isinstance(rule, dict):
        for when, tier in rule.get("rules", ()):
            if when and all(str((attrs or {}).get(k)) == str(v) for k, v in dict(when).items()):
                return tier, "tier_rule"
        if rule.get("default"):
            return rule["default"], "tier_rule-default"
    return pin.default_tier, "pin-default"


def _model_calls(calls):
    """Deduplicate model spans by action id. Returns (by_id, no_id_count, other_spans, conflicts)."""
    by_id, noid, other, conflicts = {}, 0, 0, []
    for c in calls or ():
        lst = _g(c, "listener")
        if lst is not None and lst != "llm":
            other += 1
            continue
        aid = _g(c, "action_id")
        if not (isinstance(aid, str) and aid):
            noid += 1
            continue
        ti, to = _g(c, "tokens_in"), _g(c, "tokens_out")
        rec = {"action_id": aid, "start": _g(c, "start"), "end": _g(c, "end"), "status": _g(c, "http_status"),
               "handoff_id": _g(c, "handoff_id"), "model": _g(c, "model"),
               "tokens": (ti + to) if (_n(ti) and _n(to)) else None, "tin": ti, "tout": to}
        prev = by_id.get(aid)
        if prev is None:
            by_id[aid] = rec
        else:
            if prev["tokens"] != rec["tokens"]:
                conflicts.append(aid)
                if (rec["tokens"] or -1) > (prev["tokens"] or -1):
                    by_id[aid] = rec
    return by_id, noid, other, sorted(set(conflicts))


def _invocations(ep1):
    """{id(decision): invocation key} for EP-1 decisions. An invocation is the handoff stream when the decision names
    one, else the actor's run of decisions in emitted order: `seq.in_stream` restarting (not increasing) opens a new
    invocation of the same actor. A decision with no actor gets no key (never scoped away)."""
    out, last = {}, {}
    order = sorted(ep1, key=lambda d: (str(_g(d, "emitted.at") or ""), _g(d, "seq.in_stream") or 0))
    for d in order:
        actor = _g(d, "actor.id")
        if not actor:
            continue
        hid = _g(d, "handoff.id")
        if hid:
            out[id(d)] = "%s:%s" % (actor, hid)
            continue
        seq = _g(d, "seq.in_stream")
        n, prev = last.get(actor, (0, None))
        if n == 0 or (isinstance(seq, int) and isinstance(prev, int) and seq <= prev):
            n += 1
        last[actor] = (n, seq if isinstance(seq, int) else prev)
        out[id(d)] = "%s#%d" % (actor, n)
    return out


def _is_served(status):
    return _n(status) and 200 <= status < 300


def assess_run(run_id, calls, scenario_attrs, decisions, pin, completeness, as_of,
               evaluator_sha256="", snapshot_id=""):
    sa = scenario_attrs or {}
    comp = completeness or {}
    by_id, noid, other, conflicts = _model_calls(calls)
    blocked = set(comp.get("blocked_action_ids") or ())

    total, missing = 0, []
    for aid in sorted(by_id):
        r = by_id[aid]
        zero = r["tokens"] == 0 and _is_served(r["status"]) and aid not in blocked
        if r["tokens"] is None or zero:
            missing.append(aid)
        else:
            total += r["tokens"]

    # tier: re-derived, never taken on trust (I-10)
    tier, tier_basis = derive_tier(sa.get("attrs"), sa.get("tier_rule"), pin)
    envelope = sa.get("envelope_tier")
    caps = dict(pin.caps)
    note = None
    if tier not in caps:
        note = "unknown tier %r: strictest cap applied" % (tier,)
        tier = min(pin.caps, key=lambda x: (x[1], x[0]))[0]
    cap = caps[tier]
    exceptions, gaps = [], []
    if envelope is not None and envelope != tier:
        exceptions.append({"kind": "tier-mismatch", "envelope_tier": envelope, "derived_tier": tier,
                           "record": "reconciliation"})
    if note:
        exceptions.append({"kind": "unknown-tier", "detail": note})

    over = compare(total, cap) == "over"
    overshoot = total - cap if over else 0

    # completeness: our usage records against the spans
    expected_ids = sorted(set(comp.get("expected_action_ids") or ()))
    missing_spans = [a for a in expected_ids if a not in by_id]
    ingested = comp.get("spans_ingested", True) is not False
    if not ingested:
        gaps.append("spans not yet ingested")
    if missing:
        gaps.append("missing usage on %d call(s): %s" % (len(missing), ", ".join(missing)))
    if missing_spans:
        gaps.append("no span for %d usage record(s): %s" % (len(missing_spans), ", ".join(missing_spans)))
    if noid:
        gaps.append("%d model span(s) without an action id (cannot be deduplicated)" % noid)
    if not by_id:
        gaps.append("no model span for the run")
    if conflicts:
        exceptions.append({"kind": "conflicting-duplicate-usage", "action_ids": conflicts,
                           "rule": "the larger figure is kept"})

    # EP-1 vs EP-2, call by call; the stop records (G-05)
    recs = [d for d in (decisions or ()) if _g(d, "run.id", run_id) == run_id]
    ep1 = [d for d in recs if _g(d, "ep.id") == "EP-1"]
    ep2 = [d for d in recs if _g(d, "ep.id") == "EP-2"]
    e1 = dict((_g(d, "call.id"), d) for d in ep1 if _g(d, "call.id"))
    e2 = dict((_g(d, "call.id"), d) for d in ep2 if _g(d, "call.id"))
    mismatches, earlier = [], []
    for cid in sorted(set(e1) | set(e2)):
        a, b = e1.get(cid), e2.get(cid)
        if a is not None and b is not None:
            va, vb = _g(a, "verdict"), _g(b, "verdict")
            if va == "ALLOW" and vb == "DENY":
                mismatches.append({"call": cid, "kind": "ep1-allowed-ep2-denied", "detail": "EP-1 later than EP-2"})
            elif va == "DENY" and vb == "ALLOW":
                earlier.append(cid)
        elif a is None and cid in by_id and ep1:
            mismatches.append({"call": cid, "kind": "ep1-decision-missing", "detail": "EP-2 decided, EP-1 did not"})
        elif b is None and cid in by_id and ep2:
            mismatches.append({"call": cid, "kind": "ep2-decision-missing", "detail": "EP-1 decided, EP-2 did not"})
    violations = []
    skew = comp.get("clock_skew_ms")
    skew = skew if _n(skew) else 0
    if pin.mode == "enforce":
        inv_of = _invocations(ep1)
        call_inv = dict((_g(d, "call.id"), inv_of.get(id(d))) for d in ep1
                        if _g(d, "call.id") and _g(d, "verdict") == "ALLOW")
        for d in ep1:
            if _g(d, "inline.action") != "halt":
                continue
            t_halt = _ts(_g(d, "emitted.at"))
            if t_halt is None:
                continue
            hid, inv = _g(d, "handoff.id"), inv_of.get(id(d))
            for aid in sorted(by_id):
                r = by_id[aid]
                t = _ts(r["start"])
                if t is None or (r["handoff_id"] and hid and r["handoff_id"] != hid):
                    continue
                # the halt holds within the invocation that was denied; a call EP-1 decided in ANOTHER
                # invocation is by design (handoffs never block); a call EP-1 never decided is unattributed and
                # still counts (it may be the halted invocation bypassing EP-1)
                if aid in call_inv and inv is not None and call_inv[aid] != inv:
                    continue
                if (t - t_halt).total_seconds() * 1000 > skew:
                    violations.append({"call": aid, "halt_at": _g(d, "emitted.at"), "span_start": r["start"]})
    first_halt = {}
    for v in sorted(violations, key=lambda v: (v["call"], str(v["halt_at"]))):
        first_halt.setdefault(v["call"], v)
    violations = list(first_halt.values())
    violations = sorted(set((v["call"], v["halt_at"], v["span_start"]) for v in violations))
    violations = [{"call": c, "halt_at": h, "span_start": s} for c, h, s in violations]
    if violations:
        exceptions.append({"kind": "model-span-after-halt", "calls": violations})
    for m in mismatches:
        exceptions.append(dict(m, record="reconciliation"))

    if not ep1:
        operation, op_note = "NOT_PRESENT", "no EP-1 decisions (the floor alone gives the verdict)"
    elif mismatches or violations:
        operation, op_note = "DEGRADED", "%d EP-1/EP-2 mismatch(es), %d span(s) after a halt" % (
            len(mismatches), len(violations))
    elif pin.mode == "observe" and over:
        operation, op_note = "DEGRADED", "declared observe setting: the cap is recorded, not enforced"
    else:
        operation, op_note = "OPERATED", "EP-1 and EP-2 agree call by call"

    if over:
        verdict = "BREACHED"
    elif gaps:
        verdict = "INDETERMINATE"
    else:
        verdict = "SATISFIED"

    times = sorted(t for t in (_ts(r[k]) for r in by_id.values() for k in ("start", "end")) if t is not None)
    first = _clocks.format_utc(times[0]) if times else ""
    last = _clocks.format_utc(times[-1]) if times else ""
    # the second EP: with EP-1 decisions but no EP-2 replay the measurement stands, the corroboration does not
    # (a note in `measured`, not an exception: it qualifies the evidence, never the requirement)
    ep2_missing = bool(ep1) and not ep2
    pins1 = sorted(set(_g(d, "pin.sha256") for d in ep1 if _g(d, "pin.sha256")))
    pins2 = sorted(set(_g(d, "pin.sha256") for d in ep2 if _g(d, "pin.sha256")))
    pin_differs = bool(pins1 and pins2 and pins1 != pins2)
    corroboration = None
    if ep2_missing:
        corroboration = "EP-2 replay missing: %s" % (comp.get("ep2_note") or "no EP-2 decision for the run")
    elif pin_differs:
        corroboration = "EP-1 pin %s differs from EP-2 pin %s" % (",".join(p[:8] for p in pins1),
                                                                  ",".join(p[:8] for p in pins2))
    suff = "MISSING" if not by_id else ("PARTIAL" if (gaps or ep2_missing or pin_differs) else "COMPLETE")
    measured = {
        "total_tokens": total, "calls": len(by_id), "missing_usage_calls": len(missing), "cap": cap, "tier": tier,
        "tier_basis": tier_basis, "overshoot": overshoot, "headroom_committed_minus_cap": total - cap,
        "mode": pin.mode, "envelope_tier": envelope, "provenance": sa.get("provenance"),
        "condition": sa.get("condition"), "first_span_at": first, "non_model_spans_ignored": other,
        "ep1_decisions": len(ep1), "ep2_decisions": len(ep2), "ep1_denied_earlier": earlier,
        "operation_note": op_note, "ep2_corroboration": corroboration or (
            "EP-1 and EP-2 reconciled call by call" if ep1 and ep2 else None)}
    denominators = {"model_calls": len(by_id), "usage_records": len(expected_ids)}
    completeness_out = {"expected": len(expected_ids), "captured": len(expected_ids) - len(missing_spans),
                        "missing": missing_spans, "missing_usage": missing, "spans_ingested": ingested}
    summary = ("%d tokens over cap %d (tier %s) by %d" % (total, cap, tier, overshoot) if over else
               "%d tokens, cap %d (tier %s), under cap by %d; %s" % (total, cap, tier, cap - total,
                                                                 "; ".join(gaps) or "complete"))
    return _claim.make_assessment(
        CONTROL_REF, pin.control_id, pin.threshold_version, pin.register_sha256, pin.register_version, "run",
        run_id, first, last, verdict, "DESIGNED", operation, suff, measured, exceptions, denominators,
        completeness_out, FORMULA, ["aws/spans:run=%s" % run_id], gaps, NAME, evaluator_sha256, as_of,
        snapshot_id, summary=summary)


def assess_window(t1, t2, run_assessments, pins_by_version, as_of, condition=None,
                  evaluator_sha256="", snapshot_id=""):
    counted, listed = _claim.window_scope(t1, t2, run_assessments, pins_by_version, condition)
    verdict, per_version = _claim.window_verdict(counted)
    over = [{"run": a.scope_id, "overshoot": (a.measured or {}).get("overshoot"),
             "version": a.threshold_version} for a, _ in counted if a.requirement_verdict == "BREACHED"]
    first = counted[0][0] if counted else None
    runs = [{"run": a.scope_id, "verdict": a.requirement_verdict, "version": a.threshold_version,
             "total_tokens": (a.measured or {}).get("total_tokens")} for a, _ in counted]
    versions = sorted(set(a.threshold_version for a, _ in counted))
    gaps = ["%d in-scope run(s) INDETERMINATE" % sum(1 for a, _ in counted if a.requirement_verdict == "INDETERMINATE")] \
        if any(a.requirement_verdict == "INDETERMINATE" for a, _ in counted) else []
    return _claim.make_assessment(
        CONTROL_REF, first.control_id if first else "ACN-COST-001", ",".join(versions) or "none",
        first.threshold_sha256 if first else "", first.register_version if first else "", "window",
        "%s..%s" % (t1, t2), t1, t2, verdict, "DESIGNED", "OPERATED" if counted else "NOT_PRESENT",
        "COMPLETE" if counted and not gaps else ("PARTIAL" if counted else "MISSING"),
        {"runs_counted": len(counted), "over_cap_runs": over, "per_version": per_version, "runs": runs},
        [{"kind": "over-cap-run", "run": o["run"]} for o in over],
        {"runs_in_scope": len(counted), "runs_listed_not_counted": len(listed)},
        {"listed_not_counted": listed}, "breached runs per version > exception_tolerance", [], gaps, NAME,
        evaluator_sha256, as_of, snapshot_id, summary="%d of %d run(s) over cap" % (len(over), len(counted)))

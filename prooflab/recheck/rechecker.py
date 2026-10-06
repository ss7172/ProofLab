"""Independent re-implementation of the C16 / C7 / C9 control tests, written from ARCHITECTURE section 5 only.

It shares NO code with prooflab.evaluators except the frozen c16_core compare() (imported lazily, as the DONE check
allows). Pure functions: no I/O, no clock, no module state. Every number comes from the pin passed in.

Output of each function is a small plain dict (the comparison surface), not the evaluators' Assessment:
  {"verdict": SATISFIED|BREACHED|INDETERMINATE|NOT_ASSESSED, ...measured fields..., "exceptions": [kinds]}
Stdlib only, Python 3.9.
"""
import datetime as _dt
from prooflab.contract import verdicts as _V  # the one verdict vocabulary (ARCH §4.3)


def _ts(s):
    """ISO-8601 with a trailing Z (fractional seconds optional) -> epoch seconds (float)."""
    s = s.rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            d = _dt.datetime.strptime(s, fmt).replace(tzinfo=_dt.timezone.utc)
            return d.timestamp()
        except ValueError:
            continue
    raise ValueError("bad timestamp %r" % (s,))


def _over(total, limit):
    """ARCH 5.1: the comparison goes through the frozen core's compare()."""
    from prooflab.evaluators import c16_core
    return c16_core.compare(total, limit) == "over"


# ---------------------------------------------------------------- C16 (ARCH 5.1)

def derive_tier(tier_rule, attrs, default_tier):
    """tier_rule is 'k=v->tier;...;*->tier' (first match wins; '*' is the catch-all)."""
    for part in [p for p in (tier_rule or "").split(";") if p.strip()]:
        cond, _, tier = part.partition("->")
        cond, tier = cond.strip(), tier.strip()
        if cond == "*":
            return tier
        k, _, v = cond.partition("=")
        if str((attrs or {}).get(k.strip())) == v.strip():
            return tier
    return default_tier


def recheck_c16(run_id, calls, scenario_attrs, decisions, pin16, completeness):
    caps = pin16["caps"]
    exceptions = []
    # tier: always re-derived from the scenario attributes (I-10); a mismatch with the envelope is listed
    tier = derive_tier(scenario_attrs.get("tier_rule"), scenario_attrs.get("attrs"), pin16.get("default_tier"))
    if tier not in caps:  # unknown tier -> the strictest cap
        tier = min(caps, key=lambda t: caps[t])
    cap = caps[tier]
    if scenario_attrs.get("envelope_tier") != tier:
        exceptions.append("tier-mismatch")

    model = [c for c in calls if c.get("listener") == "llm"]
    ignored = len(calls) - len(model)
    by_id = {}
    for c in model:  # one charge per action id
        by_id.setdefault(c["action_id"], c)
    blocked = set((completeness or {}).get("blocked_action_ids") or [])
    total, missing_usage = 0, 0
    for aid, c in by_id.items():
        ti, to = c.get("tokens_in"), c.get("tokens_out")
        served = 200 <= (c.get("http_status") or 0) < 300
        if aid in blocked or not served:
            total += (ti or 0) + (to or 0)  # a refusal or a blocked call: 0 is 0
        elif ti is None or to is None or (ti == 0 and to == 0):
            missing_usage += 1  # a served call with no usage is missing, never zero
        else:
            total += ti + to
    expected = set((completeness or {}).get("expected_action_ids") or [])
    span_missing = sorted(expected - set(by_id))

    if not by_id:
        verdict = _V.INDETERMINATE
    elif _over(total, cap):
        verdict = _V.BREACHED  # a known subtotal over the cap is a breach even with gaps
    elif missing_usage or span_missing:
        verdict = _V.INDETERMINATE
    else:
        verdict = _V.SATISFIED

    # reconcile EP-1 against the floor (EP-2)
    ep1 = [d for d in decisions if d.get("ep.id") == "EP-1"]
    ep2 = [d for d in decisions if d.get("ep.id") == "EP-2"]
    degraded, earlier = False, []
    e2 = {}
    for d in ep2:
        e2[d.get("call.id")] = d
    for d in ep1:
        o = e2.get(d.get("call.id"))
        if o is None:
            continue
        if d["verdict"] == "DENY" and o["verdict"] == "ALLOW":
            earlier.append(d["call.id"])  # EP-1 may deny earlier (its bound is an upper estimate)
        elif d["verdict"] == "ALLOW" and o["verdict"] == "DENY":
            degraded = True  # EP-1 later than the floor
            exceptions.append("ep1-later-than-ep2")
    if ep1:  # call by call: every served model call must have an EP-1 decision on record
        have = set(d.get("call.id") for d in ep1)
        if any(aid not in have for aid in by_id):
            degraded = True
            exceptions.append("ep1-decision-missing")
    if pin16.get("mode") == "enforce":  # G-05: no model span follows a halt in that invocation
        for d in ep1:
            if d.get("inline.action") != "halt":
                continue
            for c in model:
                if c.get("handoff_id") == d.get("handoff.id") and _ts(c["start"]) > _ts(d["emitted.at"]):
                    degraded = True
                    exceptions.append("model-span-after-halt")
                    break
    if not ep1:
        operation = "NOT_PRESENT"
    else:
        operation = "DEGRADED" if degraded else "OPERATED"

    return {"verdict": verdict, "operation": operation, "total_tokens": total, "calls": len(by_id),
            "cap": cap, "tier": tier, "missing_usage_calls": missing_usage, "missing_spans": span_missing,
            "non_model_spans_ignored": ignored,
            "overshoot": (total - cap) if verdict == _V.BREACHED else None,
            "headroom_committed_minus_cap": (total - cap) if pin16.get("mode") == "enforce" else None,
            "ep1_denied_earlier": sorted(earlier), "exceptions": exceptions}


# ---------------------------------------------------------------- C7 (ARCH 5.2)

_KINDS = ("action", "decision", "handoff", "lifecycle", "judgment")


def recheck_c7(run_id, gateway_actions, refusals, workflow_events, stops, observed, link_gaps, pin7):
    # --- the expected set E (from sources outside the graded agents)
    E = {}  # key -> (agent, kind)
    for g in gateway_actions:
        E[("call", g["action_id"])] = g.get("agent")
    for r in refusals:
        E[("call", r["call_id"])] = r.get("agent")
    streams = {}  # stream -> [(order, key)]
    for w in workflow_events:
        k = ("wf", w["agent"], "ifabric." + w["event"])
        E[k] = w["agent"]
        streams.setdefault(w["stream"], []).append((w["order"], k))
    for s in stops:
        base = len(streams.get(s["stream"], []))
        for i, ev in enumerate(pin7.get("workflow_events_after_stop") or []):
            k = ("wf", s["agent"], "ifabric." + ev)
            E[k] = s["agent"]
            streams.setdefault(s["stream"], []).append((1000 + i, k))
    if not E:
        return {"verdict": _V.NOT_ASSESSED, "exceptions": []}

    # --- the observed set O: emitted (TESTIMONY) records only; pulled records never count
    seen = {}  # key -> earliest emitted.at
    for o in observed:
        if o.get("authorship") != "TESTIMONY" or o.get("record_kind") not in _KINDS:
            continue
        keys = []
        if o.get("record_kind") == "action" and o.get("call.id"):
            keys.append(("call", o["call.id"]))
        keys.append(("wf", o.get("actor.id"), o.get("phase")))
        for k in keys:
            if k in E:
                t = _ts(o["emitted.at"])
                if k not in seen or t < seen[k]:
                    seen[k] = t
    hit = [k for k in E if k in seen]
    cov_pct_num, cov_pct_den = len(hit) * 100, len(E)
    cov_ok = cov_pct_num >= pin7["coverage_min_pct"] * cov_pct_den
    missing = sorted(repr(k) for k in E if k not in seen)

    # --- gaps: per agent stream, expected events in order; an unobserved one makes both neighbours unmeasurable
    gap_ms = pin7["gap_max_ms"]
    measured = unmeasurable = violating = 0
    agents = {}
    for st, items in streams.items():
        agents.setdefault(st.split(":")[0], []).append(st)
    for agent, sts in agents.items():
        seq = []  # (sort_time, tiebreak, key)
        for st in sts:
            prev_t = float("-inf")
            for order, k in sorted(streams[st]):
                t = seen.get(k)
                if t is not None:
                    prev_t = t
                seq.append((t if t is not None else prev_t, order, k, t is not None))
        for g in gateway_actions:
            if g.get("agent") == agent:
                k = ("call", g["action_id"])
                t = seen.get(k)
                seq.append((t if t is not None else _ts(g["end"]), 500, k, t is not None))
        seq.sort(key=lambda x: (x[0], x[1]))
        for a, b in zip(seq, seq[1:]):
            if not (a[3] and b[3]):
                unmeasurable += 1
                continue
            measured += 1
            if not ((b[0] - a[0]) * 1000.0 < gap_ms):  # the rule is gap < G
                violating += 1
    if measured == 0:
        gap_verdict = _V.INDETERMINATE if unmeasurable else _V.SATISFIED
    elif violating * 100 > pin7["violating_gap_share_max_pct"] * measured:
        gap_verdict = _V.BREACHED
    else:
        gap_verdict = _V.SATISFIED
    cov_verdict = _V.SATISFIED if cov_ok else _V.BREACHED
    if _V.BREACHED in (cov_verdict, gap_verdict):
        verdict = _V.BREACHED
    elif _V.INDETERMINATE in (cov_verdict, gap_verdict):
        verdict = _V.INDETERMINATE
    else:
        verdict = _V.SATISFIED
    return {"verdict": verdict, "coverage": "%d/%d" % (len(hit), len(E)), "coverage_verdict": cov_verdict,
            "gap_verdict": gap_verdict, "violating_gaps": violating, "gaps_measured": measured,
            "gaps_unmeasurable": unmeasurable, "missing": missing, "exceptions": []}


# ---------------------------------------------------------------- C9 (ARCH 5.3)

def recheck_c9(run_id, windows, pin9):
    two_sided = pin9.get("limit_direction", "two-sided") == "two-sided"
    d_pct = pin9["max_relative_change_pct"]
    viol = indet = ok = excluded = 0
    for runtime, w in sorted(windows.items()):
        base = pin9.get("baseline_value_" + runtime)
        if w.get("condition") == "warm-up":
            excluded += 1  # the unassessed warm-up invocation
            continue
        if base is None or not w.get("invocations_expected"):
            continue  # no frozen baseline / no traffic expected: not assessed, never a gap
        if w.get("runtime_updated") and not w.get("warmed_up"):
            indet += 1  # cold start sits inside Latency; no warm-up yet
            continue
        if not w.get("datapoints") or w.get("latency_max") is None:
            indet += 1  # an expected invocation with no datapoint is never healthy
            continue
        change = (w["latency_max"] - base) * 100.0 / base
        bad = (change > d_pct) if not two_sided else (abs(change) > d_pct)
        if pin9.get("errors_max") is not None and (w.get("errors") or 0) > pin9["errors_max"]:
            bad = True
        viol += 1 if bad else 0
        ok += 0 if bad else 1
    assessed = viol + indet + ok
    if assessed == 0:
        verdict = _V.NOT_ASSESSED
    elif viol * 100 > pin9["violating_windows_max_pct"] * (viol + ok):
        verdict = _V.BREACHED
    elif indet:
        verdict = _V.INDETERMINATE
    else:
        verdict = _V.SATISFIED
    return {"verdict": verdict, "violating": viol, "excluded": excluded, "exceptions": []}


def recheck_case(case):
    """Run one fixture case (the shared fixture schema) through the rechecker."""
    i, kind = case["inputs"], case["evaluator"]
    if kind == "c16.assess_run":
        return recheck_c16(i["run_id"], i["calls"], i["scenario_attrs"], i["decisions"], case["pin"]["c16"],
                           i["completeness"])
    if kind == "c7.assess_run":
        return recheck_c7(i["run_id"], i["gateway_actions"], i["refusals"], i["workflow_events"], i["stops"],
                          i["observed"], i["link_gaps"], case["pin"])
    if kind == "c9.assess_run":
        return recheck_c9(i["run_id"], i["windows"], case["pin"])
    raise ValueError(kind)

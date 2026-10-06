"""c7.py: the C7 tester (AIA-LOG-001), event driven (ARCH 3.4, 5.2). Pure, stateless, stdlib, Python 3.9.

    expected_events(run_id, gateway_actions, refusals, workflow_events, stops, pin) -> list[ExpectedEvent]
    observed_events(records)                       -> {key: record}  (only our emitted records count)
    assess_run(run_id, expected, observed, link_gaps, pin, as_of, ...) -> Assessment
    assess_window(t1, t2, run_assessments, pins_by_version, as_of, ...) -> Assessment      (E-06, pooled)

`pin` is a mapping: the C7 values and spec. Thresholds only from here (never a literal):
    coverage_min_pct, gap_max_ms, violating_gap_share_max_pct, exception_tolerance (missing events per run)
    workflow_events_after_stop   list of event names expected from each stopped agent
    ep1_deployed                 bool: one `decision` per model call is expected
    threshold_version, control_id, register_version, register_sha256
The three C7 numbers may also come from one string key `observation_limit` = "coverage_min_pct=..;gap_max_ms=..;
violating_gap_share_max_pct=.." (claim.parse_limits). OPEN: contract/register.py has no dedicated C7 keys yet.

ExpectedEvent (dict): key (a string; the match key), kind, agent, stream (the invocation stream or None), order
(position in the stream or None), span_end (gateway events), source.
Matching (set semantics, so extras and duplicates cannot inflate coverage):
  gateway action  -> key "call:<action_id>"   observed: record_kind action with that call.id
  EP-1 decision   -> key "decision:<call_id>" observed: decision record with that call.id
  refusal         -> key "refusal:<id>"       observed: a record with outcome.real in the refusal set and that call.id
  workflow event  -> key "<agent>|<event>"    observed: the record's actor.id + its event name
                  -> key "<agent>|<event>@<hN>" when the expected event names its invocation/handoff (`at`, PR-28:
                     IT is invoked twice, h1 and h3): observed under BOTH keys, hN = the record's handoff.id after
                     its last ":" (h0 when it has none), so a caller that does not pass `at` sees no change
                     (event name = `phase` minus the "ifabric." prefix when it has a dot or is a contract WORKFLOW_PHASES
                     name such as intent / judgment / escalation / stop, else record_kind)
Pulled records (platform_decision, observation, metric, EP-2 replays: authorship PLATFORM, or ep.id EP-2) never count.
A tool call our rail cancels (EP-3 `rail_decision`, verdict BLOCK, inline.action block, outcome.real CANCELLED_RAIL;
DG-1) is never made, so it has no gateway span and is not in E; its rail_decision is not in OBSERVED_KINDS, so it is
not in O either (the register's C7 scope: rail records sit outside the expected population). It is neither a missing
event nor coverage. assess_run lists the count as `measured.rail_cancelled_tool_calls` (diagnostic; None when
`observed` arrives as a key map). In observe the rail only records (inline.action proceed): the call goes out, has
its span, and is expected like any other tool call.
Gap G-a (judged): consecutive expected events of one stream that were both observed, on `emitted.at`; a missing
middle event makes both neighbours unmeasurable. G-b (diagnostic only): emitted.at minus the span end.
"""
from __future__ import annotations

from prooflab.contract import clocks as _clocks
from prooflab.contract import record as _record
from prooflab.evaluators import claim as _claim

NAME = "prooflab.evaluators.c7"
CONTROL_REF = "C7"
OBSERVED_KINDS = ("action", "decision", "handoff", "lifecycle", "judgment")
REFUSAL_OUTCOMES = ("REFUSED_403", "PAUSED_404", "METHOD_405", "CEILING_429", "ERROR_5XX", "BLOCKED_GUARDRAIL")
FORMULA = "coverage = |E and O| / |E|; G-a gaps per stream; violating share; coverage and gap judged separately"


def _g(o, k, d=None):
    if isinstance(o, dict):
        return o.get(k, d)
    return getattr(o, k, d)


def limits_of(pin):
    """The C7 numbers as Fractions (None where absent or invalid)."""
    src = dict(pin or {})
    src.update(dict((k, v) for k, v in _claim.parse_limits(src.get("observation_limit")).items() if k not in src))
    keys = ("coverage_min_pct", "gap_max_ms", "violating_gap_share_max_pct", "exception_tolerance")
    return dict((k, _claim.frac(src.get(k))) for k in keys)


def event_name(rec):
    ph = _g(rec, "phase") or ""
    if ph.startswith("ifabric."):
        ph = ph[len("ifabric."):]
    return ph if "." in ph or ph in _record.WORKFLOW_PHASES else (_g(rec, "record_kind") or ph)


def observed_key(rec):
    kind, cid = _g(rec, "record_kind"), _g(rec, "call.id")
    if _g(rec, "outcome.real") in REFUSAL_OUTCOMES and cid:
        return "refusal:%s" % cid
    if kind == "action" and cid:
        return "call:%s" % cid
    if kind == "decision" and cid:
        return "decision:%s" % cid
    return "%s|%s" % (_g(rec, "actor.id"), event_name(rec))


def _at(handoff_id):
    """The invocation/handoff qualifier of a workflow record: handoff.id after its last ":" (h0 when absent)."""
    return str(handoff_id).rsplit(":", 1)[-1] if handoff_id else "h0"


def workflow_key(agent, event, at=None):
    return "%s|%s@%s" % (agent, event, at) if at else "%s|%s" % (agent, event)


def expected_events(run_id, gateway_actions, refusals, workflow_events, stops, pin):
    """The expected set E, from sources outside the graded agents. gateway_actions: dicts with action_id, kind
    ("model.call" | "tool.call"), agent (optional), end. refusals: dicts with call_id or trace_id. workflow_events:
    dicts {agent, event, stream, order} (already expanded per agent by the caller from the frozen spec).
    stops: dicts {agent, stream} of C16-stopped agents: they expect `workflow_events_after_stop` instead of model
    calls. Sorted by key, so the output order never depends on input order."""
    out, pin = {}, dict(pin or {})

    def add(key, kind, agent=None, stream=None, order=None, span_end=None, source=""):
        out[key] = {"key": key, "kind": kind, "agent": agent, "stream": stream, "order": order,
                    "span_end": span_end, "source": source, "run_id": run_id}

    for a in gateway_actions or ():
        aid, kind = _g(a, "action_id"), _g(a, "kind") or "model.call"
        if not aid:
            continue
        add("call:%s" % aid, kind, _g(a, "agent"), None, None, _g(a, "end"), "gateway")
        if kind == "model.call" and pin.get("ep1_deployed"):
            add("decision:%s" % aid, "decision", _g(a, "agent"), None, None, None, "ep1")
    for r in refusals or ():
        rid = _g(r, "call_id") or _g(r, "trace_id")
        if rid:
            add("refusal:%s" % rid, "refusal", _g(r, "agent"), None, None, None, "evidence")
    for w in workflow_events or ():
        ag, ev = _g(w, "agent"), _g(w, "event")
        if ag and ev:
            add(workflow_key(ag, ev, _g(w, "at")), ev, ag, _g(w, "stream"), _g(w, "order"), None, "workflow")
    names = list(pin.get("workflow_events_after_stop") or ())
    for s in stops or ():
        ag = _g(s, "agent")
        for i, ev in enumerate(names):
            add("%s|%s" % (ag, ev), ev, ag, _g(s, "stream"), 1000 + i, None, "after-stop")
    return [out[k] for k in sorted(out)]


def observed_events(records):
    """{key: record} of the records that count as observed (ours, emitted; pulled and replayed ones never)."""
    obs = {}
    for r in records or ():
        if _g(r, "record_kind") not in OBSERVED_KINDS or _g(r, "authorship", "TESTIMONY") != "TESTIMONY":
            continue
        if _g(r, "ep.id") == "EP-2":
            continue
        k = observed_key(r)
        keys = [k] if "|" not in k else [k, "%s@%s" % (k, _at(_g(r, "handoff.id")))]
        for k in keys:
            if k not in obs or str(_g(r, "emitted.at") or "") < str(_g(obs[k], "emitted.at") or ""):
                obs[k] = r
    return obs


def _ms(a, b):
    ta, tb = _clocks.parse_utc(a), _clocks.parse_utc(b)
    return (tb - ta).total_seconds() * 1000


def _observed_map(observed):
    """Accepts {key: record} or a list of records."""
    return observed if isinstance(observed, dict) else observed_events(observed)


def assess_run(run_id, expected, observed, link_gaps, pin, as_of, evaluator_sha256="", snapshot_id="",
               source_complete=True, provenance=None, condition=None, first_span_at=None):
    lim = limits_of(pin)
    pin = dict(pin or {})
    obs = _observed_map(observed)
    exp = sorted(expected or (), key=lambda e: e["key"])
    matched = [e for e in exp if e["key"] in obs]
    missing = [e["key"] for e in exp if e["key"] not in obs]
    rail_cancelled = None if isinstance(observed, dict) else sum(
        1 for r in observed or () if _g(r, "record_kind") == "rail_decision" and _g(r, "ep.id") == "EP-3"
        and _g(r, "verdict") == "BLOCK" and _g(r, "inline.action") == "block")
    gaps = ["%s" % g for g in (link_gaps or ())]
    if source_complete is False:
        gaps.append("expected source incomplete (spans not ingested or run window not closed)")
    n_exp = len(exp)

    # G-a: consecutive expected events of one stream, both observed
    streams = {}
    for e in exp:
        if e.get("stream") is not None and e.get("order") is not None:
            streams.setdefault(e["stream"], []).append(e)
    measured_gaps, unmeasurable = [], 0
    for sid in sorted(streams, key=str):
        evs = sorted(streams[sid], key=lambda e: (e["order"], e["key"]))
        for a, b in zip(evs, evs[1:]):
            ra, rb = obs.get(a["key"]), obs.get(b["key"])
            ta, tb = _g(ra, "emitted.at") if ra else None, _g(rb, "emitted.at") if rb else None
            if ra is None or rb is None or not ta or not tb:
                unmeasurable += 1
                continue
            try:
                ms = _ms(ta, tb)
            except ValueError:
                unmeasurable += 1
                continue
            measured_gaps.append({"stream": sid, "from": a["key"], "to": b["key"], "gap_ms": ms})
    # G-b (diagnostic only)
    latency = []
    for e in exp:
        r = obs.get(e["key"])
        if e.get("span_end") and r is not None and _g(r, "emitted.at"):
            try:
                latency.append({"key": e["key"], "recording_latency_ms": _ms(e["span_end"], _g(r, "emitted.at"))})
            except ValueError:
                pass

    gmax = lim["gap_max_ms"]
    violating = [g for g in measured_gaps if gmax is not None and _claim.frac(g["gap_ms"]) > gmax]
    cov_min, share_max = lim["coverage_min_pct"], lim["violating_gap_share_max_pct"]
    cov_verdict = gap_verdict = "NOT_ASSESSED"
    if n_exp and cov_min is not None:
        cov_verdict = "BREACHED" if _claim.pct_under(len(matched), n_exp, cov_min) else "SATISFIED"
    if measured_gaps and share_max is not None and gmax is not None:
        gap_verdict = "BREACHED" if _claim.pct_over(len(violating), len(measured_gaps), share_max) else "SATISFIED"
    if n_exp == 0:
        verdict = "NOT_ASSESSED"
    elif "BREACHED" in (cov_verdict, gap_verdict):
        verdict = "BREACHED"
    elif gaps or cov_min is None:
        verdict = "INDETERMINATE"
    else:
        verdict = "SATISFIED"
    coverage = "%d/%d" % (len(matched), n_exp)
    times = sorted(t for t in (_g(r, "emitted.at") for r in obs.values()) if t)
    exceptions = [{"kind": "missing-event", "key": k} for k in missing] + \
                 [dict(kind="violating-gap", **g) for g in violating]
    measured = {"coverage": coverage, "coverage_pct": (100.0 * len(matched) / n_exp) if n_exp else None,
                "coverage_verdict": cov_verdict, "gap_verdict": gap_verdict, "gaps_measured": len(measured_gaps),
                "gaps_unmeasurable": unmeasurable, "violating_gaps": len(violating),
                "missing_events": len(missing), "G_a": measured_gaps, "G_b_diagnostic": latency,
                "provenance": provenance, "condition": condition, "rail_cancelled_tool_calls": rail_cancelled,
                "first_span_at": first_span_at or (times[0] if times else "")}
    suff = "MISSING" if not n_exp else ("PARTIAL" if gaps else "COMPLETE")
    tol = lim["exception_tolerance"]
    measured["within_missing_tolerance"] = (tol is not None and len(missing) <= tol)
    return _claim.make_assessment(
        CONTROL_REF, pin.get("control_id", "AIA-LOG-001"), pin.get("threshold_version", ""),
        pin.get("register_sha256", ""), pin.get("register_version", ""), "run", run_id,
        times[0] if times else "", times[-1] if times else "", verdict, "DESIGNED",
        "OPERATED" if matched else "NOT_PRESENT", suff, measured, exceptions,
        {"expected": n_exp, "observed_and_expected": len(matched), "gaps_measured": len(measured_gaps)},
        {"expected": n_exp, "captured": len(matched), "missing": missing}, FORMULA,
        ["store:run=%s" % run_id], gaps, NAME, evaluator_sha256, as_of, snapshot_id,
        summary="coverage %s (%s), %d violating gap(s) of %d (%s)" % (
            coverage, cov_verdict, len(violating), len(measured_gaps), gap_verdict))


def assess_window(t1, t2, run_assessments, pins_by_version, as_of, condition=None,
                  evaluator_sha256="", snapshot_id=""):
    counted, listed = _claim.window_scope(t1, t2, run_assessments, pins_by_version, condition)
    verdict, per_version = _claim.window_verdict(counted)
    sum_exp = sum((a.denominators or {}).get("expected", 0) for a, _ in counted)
    sum_hit = sum((a.denominators or {}).get("observed_and_expected", 0) for a, _ in counted)
    sum_gap = sum((a.denominators or {}).get("gaps_measured", 0) for a, _ in counted)
    sum_vio = sum((a.measured or {}).get("violating_gaps", 0) for a, _ in counted)
    first = counted[0][0] if counted else None
    return _claim.make_assessment(
        CONTROL_REF, first.control_id if first else "AIA-LOG-001",
        ",".join(sorted(set(a.threshold_version for a, _ in counted))) or "none",
        first.threshold_sha256 if first else "", first.register_version if first else "", "window",
        "%s..%s" % (t1, t2), t1, t2, verdict, "DESIGNED", "OPERATED" if counted else "NOT_PRESENT",
        "COMPLETE" if counted else "MISSING",
        {"pooled_coverage": "%d/%d" % (sum_hit, sum_exp), "pooled_violating_gaps": "%d/%d" % (sum_vio, sum_gap),
         "per_version": per_version,
         "runs": [{"run": a.scope_id, "verdict": a.requirement_verdict, "coverage": (a.measured or {}).get("coverage"),
                   "violating_gaps": (a.measured or {}).get("violating_gaps")} for a, _ in counted]},
        [], {"runs_in_scope": len(counted), "runs_listed_not_counted": len(listed)},
        {"listed_not_counted": listed}, "breached runs per version > exception_tolerance", [], [], NAME,
        evaluator_sha256, as_of, snapshot_id,
        summary="pooled coverage %d/%d, %d/%d violating gaps" % (sum_hit, sum_exp, sum_vio, sum_gap))

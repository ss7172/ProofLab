"""c9.py: the C9 tester (AIA-ARC-006), drift and performance (ARCH 3.4, 5.3). Pure, stateless, stdlib, Python 3.9.

    assess_run(run_id, windows, pin, as_of, ...) -> Assessment          per run, per runtime, two-sided
    assess_window(t1, t2, run_assessments, hourly_windows, pins_by_version, as_of, ...) -> Assessment

`windows`: {runtime: MetricWindow}; a MetricWindow is a mapping with
    latency_max           the AgentCore invocation Latency statistic Maximum in the window (number) or None
    errors                Errors Sum in the window (int) or None
    invocations_expected  how many invocations the window should hold (0: no traffic expected)
    datapoints            how many datapoints arrived (missing for an expected invocation = INDETERMINATE)
    condition             "warm-up" excludes the window (the warm-up rule, B13)
    runtime_updated       True after a pin patch, model swap or revert; needs `warmed_up` True (one unassessed warm-up
                          invocation preceded) or the window is INDETERMINATE (a cold start would confound it)
`pin` is a mapping (values only from here, never a literal): baseline_value_<runtime> (frozen baseline),
    max_relative_change_pct (D), violating_windows_max_pct (B9), errors_max (optional), limit_direction
    (two-sided | increase | decrease; default two-sided), threshold_version, control_id, register_version,
    register_sha256. The three numeric values may also be one `observation_limit` string "k=v;k=v" (claim.parse_limits).
Verdicts: a violating window is |latency_max - baseline| / baseline * 100 > D (either direction when two-sided) or
errors > errors_max. BREACHED when violating windows exceed B9 of the assessed windows; INDETERMINATE when an
expected window has no datapoint (never healthy) and nothing is breached; NOT_ASSESSED when no baseline is frozen
for the version (C9-v1), no window carries an expectation, or all windows are excluded. An hour with no expected
traffic is NOT_ASSESSED, never a monitoring gap.
"""
from __future__ import annotations

from fractions import Fraction

from prooflab.contract import clocks as _clocks
from prooflab.evaluators import claim as _claim

NAME = "prooflab.evaluators.c9"
CONTROL_REF = "C9"
DIRECTIONS = ("two-sided", "increase", "decrease")
FORMULA = "|max - baseline| / baseline * 100 > D per runtime window (two-sided); violating share > B9"


def _g(o, k, d=None):
    if isinstance(o, dict):
        return o.get(k, d)
    return getattr(o, k, d)


def _values(pin):
    src = dict(pin or {})
    for k, v in _claim.parse_limits(src.get("observation_limit")).items():
        src.setdefault(k, v)
    return src


def eval_window(runtime, w, pin):
    """(state, detail): state in OK | VIOLATING | INDETERMINATE | NOT_ASSESSED | EXCLUDED."""
    p = _values(pin)
    if _g(w, "condition") == "warm-up":
        return "EXCLUDED", {"reason": "warm-up invocation (unassessed by rule)"}
    expected = _g(w, "invocations_expected")
    if expected == 0:
        return "NOT_ASSESSED", {"reason": "no traffic expected in the window"}
    base = _claim.frac(p.get("baseline_value_%s" % runtime))
    d = _claim.frac(p.get("max_relative_change_pct"))
    if base is None or d is None:
        return "NOT_ASSESSED", {"reason": "no frozen baseline or limit for %s in this version" % runtime}
    if _g(w, "runtime_updated") and not _g(w, "warmed_up"):
        return "INDETERMINATE", {"reason": "runtime updated and no warm-up invocation preceded (cold start)"}
    lat, dp = _claim.frac(_g(w, "latency_max")), _g(w, "datapoints")
    if lat is None or not dp:
        return "INDETERMINATE", {"reason": "monitoring-gap: expected invocation has no datapoint"}
    if base == 0:
        return "INDETERMINATE", {"reason": "baseline is zero: relative change undefined"}
    direction = p.get("limit_direction") or "two-sided"
    if direction not in DIRECTIONS:
        direction = "two-sided"
    change = (lat - base) / base * 100
    over = (abs(change) > d if direction == "two-sided" else change > d if direction == "increase" else -change > d)
    errs, emax = _g(w, "errors"), _claim.frac(p.get("errors_max"))
    err_over = emax is not None and isinstance(errs, int) and not isinstance(errs, bool) and Fraction(errs) > emax
    detail = {"latency_max": str(lat), "baseline": str(base), "change_pct": str(round(float(change), 4)),
              "errors": errs, "direction": direction, "latency_violation": bool(over), "error_violation": bool(err_over)}
    return ("VIOLATING" if over or err_over else "OK"), detail


def _roll(states, share_max):
    assessed = [s for s in states if s in ("OK", "VIOLATING", "INDETERMINATE")]
    vio = sum(1 for s in states if s == "VIOLATING")
    if vio and (share_max is None or _claim.pct_over(vio, len(assessed), share_max)):
        return "BREACHED"
    if "INDETERMINATE" in states:
        return "INDETERMINATE"
    return "SATISFIED" if assessed else "NOT_ASSESSED"


def assess_run(run_id, windows, pin, as_of, evaluator_sha256="", snapshot_id="",
               provenance=None, condition=None, first_span_at=None):
    p = _values(pin)
    share_max = _claim.frac(p.get("violating_windows_max_pct"))
    rows, states = [], []
    for rt in sorted(windows or {}):
        st, det = eval_window(rt, windows[rt], p)
        states.append(st)
        rows.append(dict(det, runtime=rt, state=st))
    verdict = _roll(states, share_max)
    if share_max is None and verdict == "SATISFIED":
        verdict = "INDETERMINATE"
    gaps = ["%s: %s" % (r["runtime"], r["reason"]) for r in rows if r["state"] == "INDETERMINATE"]
    excluded = [r for r in rows if r["state"] in ("EXCLUDED", "NOT_ASSESSED")]
    assessed = [r for r in rows if r["state"] in ("OK", "VIOLATING", "INDETERMINATE")]
    vio = [r for r in rows if r["state"] == "VIOLATING"]
    suff = "MISSING" if not assessed else ("PARTIAL" if gaps else "COMPLETE")
    measured = {"windows": rows, "violating": len(vio), "assessed": len(assessed), "excluded": len(excluded),
                "provenance": provenance, "condition": condition, "first_span_at": first_span_at or ""}
    return _claim.make_assessment(
        CONTROL_REF, p.get("control_id", "AIA-ARC-006"), p.get("threshold_version", ""),
        p.get("register_sha256", ""), p.get("register_version", ""), "run", run_id, first_span_at or "", "",
        verdict, "DESIGNED", "OPERATED" if assessed else "NOT_PRESENT", suff, measured,
        [dict(kind="violating-window", runtime=r["runtime"]) for r in vio],
        {"runtime_windows": len(rows), "assessed": len(assessed)},
        {"expected": len(rows), "captured": len(rows) - len(gaps), "missing": gaps}, FORMULA,
        ["cloudwatch:AWS/Bedrock-AgentCore:run=%s" % run_id], gaps, NAME, evaluator_sha256, as_of, snapshot_id,
        summary="%d violating of %d assessed runtime window(s)" % (len(vio), len(assessed)))


def assess_window(t1, t2, run_assessments, hourly_windows, pins_by_version, as_of, condition=None,
                  evaluator_sha256="", snapshot_id=""):
    """hourly_windows: mappings with hour, runtime, threshold_version and the MetricWindow fields. The verdict is
    over the closed UTC hours in [t1, t2); the run assessments are listed beside it."""
    _, listed = _claim.window_scope(t1, t2, run_assessments, pins_by_version, condition)
    by_version, rows = {}, []
    for h in sorted(hourly_windows or (), key=lambda x: (str(_g(x, "hour")), str(_g(x, "runtime")))):
        hour = _g(h, "hour")
        try:
            inside = _clocks.parse_utc(t1) <= _clocks.parse_utc(hour) < _clocks.parse_utc(t2)
        except (ValueError, TypeError):
            inside = False
        if not inside:
            continue
        tv = _g(h, "threshold_version")
        pin = (pins_by_version or {}).get(tv)
        if pin is None:
            rows.append({"hour": hour, "runtime": _g(h, "runtime"), "state": "NOT_ASSESSED",
                         "reason": "no entry for %s" % tv, "version": tv})
            continue
        st, det = eval_window(_g(h, "runtime"), h, pin)
        rows.append(dict(det, hour=hour, runtime=_g(h, "runtime"), state=st, version=tv))
        by_version.setdefault(tv, (pin, []))[1].append(st)
    verdicts = []
    for tv in sorted(by_version):
        pin, sts = by_version[tv]
        verdicts.append(_roll(sts, _claim.frac(_values(pin).get("violating_windows_max_pct"))))
    verdict = ("BREACHED" if "BREACHED" in verdicts else "INDETERMINATE" if "INDETERMINATE" in verdicts
               else "SATISFIED" if "SATISFIED" in verdicts else "NOT_ASSESSED")
    gaps = ["%s %s: %s" % (r["hour"], r["runtime"], r["reason"]) for r in rows if r["state"] == "INDETERMINATE"]
    assessed = [r for r in rows if r["state"] in ("OK", "VIOLATING", "INDETERMINATE")]
    vio = [r for r in rows if r["state"] == "VIOLATING"]
    first = next((a for a in sorted(run_assessments or (), key=lambda x: x.assessment_id)), None)
    return _claim.make_assessment(
        CONTROL_REF, first.control_id if first else "AIA-ARC-006", ",".join(sorted(by_version)) or "none",
        first.threshold_sha256 if first else "", first.register_version if first else "", "window",
        "%s..%s" % (t1, t2), t1, t2, verdict, "DESIGNED", "OPERATED" if assessed else "NOT_PRESENT",
        "MISSING" if not assessed else ("PARTIAL" if gaps else "COMPLETE"),
        {"hours": rows, "violating_hours": len(vio), "assessed_hours": len(assessed),
         "runs": [{"run": a.scope_id, "verdict": a.requirement_verdict} for a in
                  sorted(run_assessments or (), key=lambda x: x.assessment_id)]},
        [dict(kind="violating-hour", hour=r["hour"], runtime=r["runtime"]) for r in vio],
        {"hourly_windows": len(rows), "assessed": len(assessed)}, {"listed_not_counted": listed}, FORMULA, [], gaps,
        NAME, evaluator_sha256, as_of, snapshot_id,
        summary="%d violating of %d assessed hourly window(s)" % (len(vio), len(assessed)))

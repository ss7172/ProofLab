/*
 * Reference evaluators for controls 16, 7 and 9.
 * Pure functions: (records, rule from the frozen register) -> verdict. No state, no I/O, no thresholds of their own.
 * They let anyone recompute a verdict from the raw records in the evidence pack, independently of the team's evaluator.
 */
(function (root) {
  "use strict";

  var V = { SATISFIED: "SATISFIED", BREACHED: "BREACHED", INDETERMINATE: "INDETERMINATE", NOT_ASSESSED: "NOT_ASSESSED" };

  function compare(value, op, limit) {
    switch (op) {
      case "<": return value < limit;
      case "<=": return value <= limit;
      case ">": return value > limit;
      case ">=": return value >= limit;
      default: throw new Error("unknown operator " + op);
    }
  }

  function ms(iso) { return Date.parse(iso); }

  function num(x) { return typeof x === "number" && isFinite(x); }

  // Control 16: input + output tokens per run, all agents and retries, against the cap.
  function evalC16(runId, records, rule) {
    var lim = rule.observation_limit;
    var seen = {}, calls = [], duplicates = [];
    records.forEach(function (r) {
      if (r.run_id !== runId || r.kind !== "model_call") return;
      var key = r.call_id || r.id;
      if (seen[key]) { duplicates.push(r.id); return; }
      seen[key] = true;
      calls.push(r);
    });
    var missing = calls.filter(function (c) { return !num(c.input_tokens) || !num(c.output_tokens); });
    var input = 0, output = 0, retries = 0;
    calls.forEach(function (c) {
      if (num(c.input_tokens)) input += c.input_tokens;
      if (num(c.output_tokens)) output += c.output_tokens;
      if (c.retry) retries += 1;
    });
    var total = input + output;
    var exceptions = [];
    if (duplicates.length) exceptions.push(duplicates.length + " duplicate observation(s) of the same call counted once");
    if (missing.length) exceptions.push(missing.length + " call(s) without token counts");
    var verdict, reason;
    if (calls.length === 0) {
      verdict = V.INDETERMINATE; reason = "no model-call records for this run";
    } else if (!compare(total, lim.operator, lim.value)) {
      verdict = V.BREACHED; reason = "known total already over the cap" + (missing.length ? " (some calls lack counts, so the true total is higher)" : "");
    } else if (missing.length) {
      verdict = V.INDETERMINATE; reason = "under the cap, but calls are missing counts";
    } else {
      verdict = V.SATISFIED; reason = "every call counted; total within the cap";
    }
    return {
      verdict: verdict, reason: reason,
      measured: { total_tokens: total, input_tokens: input, output_tokens: output, calls: calls.length, retries: retries,
                  over_by: Math.max(0, total - lim.value) },
      limit_text: "total tokens " + lim.operator + " " + lim.value.toLocaleString("en-US") + " " + (lim.unit || ""),
      population: { observed: calls.length, missing: missing.length, duplicates: duplicates.length },
      exceptions: exceptions,
      record_ids: calls.map(function (c) { return c.id; }).concat(duplicates),
      formula: "sum(input + output tokens of each distinct call) " + lim.operator + " cap"
    };
  }

  // Control 16 objective across a set of runs: how many breached, against the allowance.
  function evalC16Objective(runIds, records, rule) {
    var per = runIds.map(function (id) { return { run_id: id, result: evalC16(id, records, rule) }; });
    var breached = per.filter(function (p) { return p.result.verdict === V.BREACHED; }).length;
    var indet = per.filter(function (p) { return p.result.verdict === V.INDETERMINATE; }).length;
    var allowed = rule.exception_tolerance.max_breaching_runs;
    var verdict = breached > allowed ? V.BREACHED : (indet ? V.INDETERMINATE : V.SATISFIED);
    return { verdict: verdict, runs: per, breached: breached, allowed: allowed };
  }

  // Control 7: expected events recorded and joined to the run; gaps between consecutive events within the limit.
  function evalC7(runId, records, expected, rule) {
    var lim = rule.observation_limit, tol = rule.exception_tolerance;
    var exp = expected && expected[runId];
    if (!exp || !exp.events || exp.events.length === 0) {
      return { verdict: V.NOT_ASSESSED, reason: "no independent list of expected events for this run",
               measured: {}, population: { expected: 0, observed: 0, missing: 0 }, exceptions: [], record_ids: [], gaps: [],
               limit_text: "", formula: "" };
    }
    var byEvent = {}, dupes = 0;
    records.forEach(function (r) {
      if (r.run_id !== runId || !r.expected_event_id) return;
      if (byEvent[r.expected_event_id]) { dupes += 1; return; }
      byEvent[r.expected_event_id] = r;
    });
    var events = exp.events;
    var missing = events.filter(function (e) { return !byEvent[e.id]; });
    var coverage = (events.length - missing.length) / events.length * 100;
    var gaps = [], eligible = 0, violating = 0, unmeasurable = 0;
    for (var i = 1; i < events.length; i++) {
      var a = byEvent[events[i - 1].id], b = byEvent[events[i].id];
      var label = events[i - 1].id + " -> " + events[i].id;
      if (!a || !b) { unmeasurable += 1; gaps.push({ pair: label, ms: null, status: "unmeasurable (event missing)" }); continue; }
      var gap = ms(b.at) - ms(a.at);
      eligible += 1;
      var ok = gap >= 0 && compare(gap, lim.gap_operator, lim.gap_limit_ms);
      if (!ok) violating += 1;
      gaps.push({ pair: label, ms: gap, status: gap < 0 ? "clock skew (negative gap)" : (ok ? "within limit" : "over limit") });
    }
    var violPct = eligible ? violating / eligible * 100 : 0;
    var exceptions = [];
    if (missing.length) exceptions.push("missing: " + missing.map(function (e) { return e.id + " (" + e.label + ")"; }).join(", "));
    if (violating) exceptions.push(violating + " of " + eligible + " gaps over " + lim.gap_limit_ms.toLocaleString("en-US") + " ms");
    if (unmeasurable) exceptions.push(unmeasurable + " gap(s) unmeasurable because an event is missing");
    if (dupes) exceptions.push(dupes + " duplicate event record(s) ignored");
    var verdict, reason;
    if (coverage < lim.coverage_min_pct) { verdict = V.BREACHED; reason = "coverage below target"; }
    else if (violPct > tol.max_violating_gap_pct) { verdict = V.BREACHED; reason = "too many gaps over the limit"; }
    else { verdict = V.SATISFIED; reason = "all expected events recorded; gap exceptions within tolerance"; }
    return {
      verdict: verdict, reason: reason,
      measured: { coverage_pct: round1(coverage), violating_gap_pct: round1(violPct), eligible_gaps: eligible, violating_gaps: violating },
      limit_text: "coverage >= " + lim.coverage_min_pct + "%, each gap " + lim.gap_operator + " " + lim.gap_limit_ms.toLocaleString("en-US") +
                  " ms, violating gaps <= " + tol.max_violating_gap_pct + "%",
      population: { expected: events.length, observed: events.length - missing.length, missing: missing.length, source: exp.source },
      exceptions: exceptions, gaps: gaps,
      record_ids: events.filter(function (e) { return byEvent[e.id]; }).map(function (e) { return byEvent[e.id].id; }),
      formula: "matched expected events / expected events; consecutive-event gaps vs limit"
    };
  }

  // Control 9: performance against a frozen baseline per closed window. Higher latency is worse.
  function evalC9(windows, rule) {
    var lim = rule.observation_limit, tol = rule.exception_tolerance, base = rule.baseline;
    if (!windows.length) {
      return { verdict: V.NOT_ASSESSED, reason: "no expected windows in this scope", measured: {}, population: { expected: 0, observed: 0, missing: 0 },
               exceptions: [], windows: [], record_ids: [], limit_text: "", formula: "" };
    }
    var rows = windows.map(function (w) {
      var b = base[w.runtime];
      if (!num(w.value)) return { w: w, rel: null, status: "missing (not healthy)" };
      if (!b || !(b.value > 0)) return { w: w, rel: null, status: "no positive baseline" };
      var rel = (w.value - b.value) / b.value * 100;
      var ok = compare(rel, lim.operator, lim.max_relative_increase_pct);
      return { w: w, rel: round1(rel), status: ok ? "within limit" : "over limit" };
    });
    var measured = rows.filter(function (r) { return r.rel !== null; });
    var missing = rows.length - measured.length;
    var violating = measured.filter(function (r) { return r.status === "over limit"; }).length;
    var violPct = measured.length ? violating / measured.length * 100 : 0;
    var coverage = measured.length / rows.length * 100;
    var exceptions = [];
    if (violating) exceptions.push(violating + " window(s) over the drift limit; each must alert the owner");
    if (missing) exceptions.push(missing + " window(s) missing data: unknown, not zero drift");
    var verdict, reason;
    if (violPct > tol.max_violating_windows_pct) { verdict = V.BREACHED; reason = "violating windows exceed the allowance" + (missing ? " (other windows also missing)" : ""); }
    else if (coverage < rule.coverage_min_pct) { verdict = V.INDETERMINATE; reason = "no breach seen, but expected windows are missing"; }
    else { verdict = V.SATISFIED; reason = "every expected window measured and within the limit"; }
    return {
      verdict: verdict, reason: reason,
      measured: { windows_expected: rows.length, windows_measured: measured.length, violating_windows: violating,
                  violating_pct: round1(violPct), coverage_pct: round1(coverage) },
      limit_text: "relative increase " + lim.operator + " " + lim.max_relative_increase_pct + "% per window, violating windows <= " +
                  tol.max_violating_windows_pct + "%, coverage " + rule.coverage_min_pct + "%",
      population: { expected: rows.length, observed: measured.length, missing: missing },
      exceptions: exceptions, windows: rows,
      record_ids: windows.map(function (w) { return w.id; }),
      formula: "(observed - baseline) / baseline x 100 per window"
    };
  }

  // Which windows a scope covers: windows that contain the run, or that overlap [from, to).
  function windowsForRun(run, windows) {
    var s = ms(run.started_at), e = ms(run.ended_at || run.started_at);
    return windows.filter(function (w) { return ms(w.start) < e + 1 && ms(w.end) > s; });
  }
  function windowsForRange(from, to, windows) {
    var a = ms(from), b = ms(to);
    return windows.filter(function (w) { return ms(w.start) >= a && ms(w.end) <= b; });
  }

  // The threshold must be dated before the run it judges.
  function datedBefore(register, run) {
    return ms(register.version_date) < ms(run.started_at);
  }

  function round1(x) { return Math.round(x * 10) / 10; }

  var api = { V: V, compare: compare, evalC16: evalC16, evalC16Objective: evalC16Objective, evalC7: evalC7, evalC9: evalC9,
              windowsForRun: windowsForRun, windowsForRange: windowsForRange, datedBefore: datedBefore };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Evaluators = api;
})(this);

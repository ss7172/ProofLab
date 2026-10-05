(function () {
  "use strict";
  var E = window.Evaluators;
  var P = null;
  var CONTROLS = ["C16", "C7", "C9"];
  var state = {
    control: "C16", scopeKind: "run", runId: null, from: "", to: "",
    askedAt: Date.now(), answeredAt: null, answer: null,
    evRun: "", evKind: "", evEp: "", evView: "evidence",
    epControl: "C16", epRun: null, epA: "EP1", epB: "EP3", rehearsalEnd: null
  };

  // ---------- helpers
  function esc(v) {
    return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function n(v) { return typeof v === "number" ? v.toLocaleString("en-US") : (v === null || v === undefined ? "–" : esc(v)); }
  function t(iso) { return iso ? esc(String(iso).replace("T", " ").replace(/\.\d+Z$|Z$/, " UTC")) : "–"; }
  var VICON = { SATISFIED: "✔", BREACHED: "✖", INDETERMINATE: "?", NOT_ASSESSED: "–", ESCALATED: "↑" };
  var VTEXT = { SATISFIED: "Satisfied", BREACHED: "Breached", INDETERMINATE: "Indeterminate", NOT_ASSESSED: "Not assessed", ESCALATED: "Escalated" };
  function badge(v, big) {
    return '<span class="verdict v-' + esc(v) + (big ? " big" : "") + '">' + (VICON[v] || "") + " " + esc(VTEXT[v] || v) + "</span>";
  }
  var SICON = { shown: "✔", answered: "✔", yes: "✔", defended: "✔", partial: "◐", "detected, not prevented": "◐", missing: "✖", broke: "✖", no: "✖", "out of scope": "–" };
  function sbadge(s) {
    var cls = { shown: "shown", answered: "answered", yes: "yes", defended: "defended", partial: "partial", missing: "missing", broke: "broke",
                no: "no", "out of scope": "out", "detected, not prevented": "detected" }[s] || "out";
    return '<span class="verdict s-' + cls + '">' + (SICON[s] || "•") + " " + esc(s) + "</span>";
  }
  function list(items, emptyText) {
    if (!items || !items.length) return '<p class="empty">' + esc(emptyText) + "</p>";
    return "<ul>" + items.map(function (i) { return "<li>" + i + "</li>"; }).join("") + "</ul>";
  }
  function table(head, rows, emptyText, numCols) {
    numCols = numCols || [];
    if (!rows.length) return '<p class="empty">' + esc(emptyText) + "</p>";
    return '<div class="tbl"><table><thead><tr>' + head.map(function (h, i) {
      return '<th scope="col"' + (numCols.indexOf(i) >= 0 ? ' class="num"' : "") + ">" + esc(h) + "</th>";
    }).join("") + "</tr></thead><tbody>" + rows.map(function (r) {
      return "<tr>" + r.map(function (c, i) { return "<td" + (numCols.indexOf(i) >= 0 ? ' class="num"' : "") + ">" + c + "</td>"; }).join("") + "</tr>";
    }).join("") + "</tbody></table></div>";
  }
  function rule(c) { return P.register.controls[c]; }
  function run(id) { return P.runs.filter(function (r) { return r.run_id === id; })[0]; }
  function namedRuns(c) { return P.runs.filter(function (r) { return r.named && r.named[c]; }); }
  function controlTitle(c) { var r = rule(c); return c + " · " + r.control_id + " · " + r.name; }
  function download(name, obj) {
    var blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  // ---------- pack checks: anything missing is reported as a gap, never left blank
  var REQUIRED = ["meta", "register", "runs", "records", "expected_events", "metric_windows", "assessments", "human_loop",
                  "levels", "architecture", "adversarial", "gaps", "auditor", "artefacts"];
  function checkPack(p) {
    var problems = REQUIRED.filter(function (k) { return !(k in p); }).map(function (k) { return "missing section: " + k; });
    if (p.register && p.register.controls) {
      CONTROLS.forEach(function (c) { if (!p.register.controls[c]) problems.push("register has no entry for " + c); });
    }
    return problems;
  }
  function load(pack) {
    var problems = checkPack(pack);
    REQUIRED.forEach(function (k) {
      if (!(k in pack)) pack[k] = (k === "meta" || k === "register" || k === "levels" || k === "architecture" || k === "auditor" || k === "expected_events") ? {} : [];
    });
    P = pack; P._problems = problems;
    var first = P.runs.filter(function (r) { return r.named && Object.keys(r.named).length; })[0] || P.runs[0];
    state.runId = first ? first.run_id : null; state.epRun = state.runId;
    var ws = P.metric_windows.map(function (w) { return w.start; }).sort();
    var we = P.metric_windows.map(function (w) { return w.end; }).sort();
    state.from = ws.length ? ws[0].slice(0, 16) : ""; state.to = we.length ? we[we.length - 1].slice(0, 16) : "";
    state.answer = null; state.askedAt = Date.now(); state.answeredAt = null;
    render();
  }

  // ---------- evaluation (always from raw records + frozen register)
  function recordsForControl(c) {
    var ep = rule(c).figure_of_record_ep;
    if (!ep || ep === "ALL") return P.records;
    return P.records.filter(function (r) { return r.ep === ep || r.kind !== "model_call"; });
  }
  function runsInRange(from, to) {
    var a = Date.parse(from), b = Date.parse(to);
    return P.runs.filter(function (r) { var s = Date.parse(r.started_at); return s >= a && s < b; });
  }
  function evaluate(c, scope) {
    var rl = rule(c);
    if (c === "C9") {
      var wins = scope.kind === "run" ? E.windowsForRun(run(scope.id), P.metric_windows) : E.windowsForRange(scope.from, scope.to, P.metric_windows);
      return E.evalC9(wins, rl);
    }
    if (scope.kind === "run") {
      return c === "C16" ? E.evalC16(scope.id, recordsForControl(c), rl) : E.evalC7(scope.id, P.records, P.expected_events, rl);
    }
    var runs = runsInRange(scope.from, scope.to);
    var per = runs.map(function (r) { return { run: r, res: evaluate(c, { kind: "run", id: r.run_id }) }; });
    var breached = per.filter(function (p) { return p.res.verdict === "BREACHED"; }).length;
    var indet = per.filter(function (p) { return p.res.verdict === "INDETERMINATE"; }).length;
    var allowed = c === "C16" ? rl.exception_tolerance.max_breaching_runs : 0;
    var verdict = !per.length ? "NOT_ASSESSED" : (breached > allowed ? "BREACHED" : (indet ? "INDETERMINATE" : "SATISFIED"));
    return { verdict: verdict, objective: true, per: per,
             reason: per.length ? breached + " of " + per.length + " runs in the window breached; " + allowed + " allowed" : "no runs started in this window",
             measured: { runs: per.length, breached_runs: breached, allowed_breaching_runs: allowed }, population: { expected: per.length, observed: per.length, missing: 0 },
             exceptions: [], record_ids: [], limit_text: c === "C16" ? "no more than " + allowed + " run(s) over the cap" : "every run must satisfy the rule" };
  }
  function teamAssessment(c, scope) {
    if (scope.kind !== "run") return null;
    var list = P.assessments.filter(function (a) { return a.control_ref === c && a.scope && a.scope.kind === "run" && a.scope.id === scope.id; });
    return list.length ? list[list.length - 1] : null;
  }
  function compareTeam(c, res, team) {
    if (!team) return { status: "none" };
    var verdictMatch = team.verdict === res.verdict;
    var key = c === "C16" ? "total_tokens" : (c === "C7" ? "coverage_pct" : null);
    var valueMatch = true, teamVal = null, ourVal = null;
    if (key && team.measured && team.measured[key] !== undefined) {
      teamVal = team.measured[key]; ourVal = res.measured[key]; valueMatch = teamVal === ourVal;
    }
    return { status: verdictMatch && valueMatch ? "match" : "mismatch", verdictMatch: verdictMatch, valueMatch: valueMatch, key: key, teamVal: teamVal, ourVal: ourVal };
  }
  function findingsFor(c, scope) {
    return P.human_loop.filter(function (f) {
      if (f.control_ref === "ESC") return scope.kind === "run" && f.scope.id === scope.id;
      if (f.control_ref !== c) return false;
      if (scope.kind === "run") {
        if (f.scope.kind === "run") return f.scope.id === scope.id;
        if (f.scope.kind === "window") {
          var w = P.metric_windows.filter(function (x) { return x.id === f.scope.id; })[0];
          return w && E.windowsForRun(run(scope.id), [w]).length > 0;
        }
        return false;
      }
      if (f.scope.kind === "window") {
        var w2 = P.metric_windows.filter(function (x) { return x.id === f.scope.id; })[0];
        return w2 && E.windowsForRange(scope.from, scope.to, [w2]).length > 0;
      }
      var r = run(f.scope.id);
      return r && runsInRange(scope.from, scope.to).indexOf(r) >= 0;
    });
  }
  function gapsFor(c, scope, cmp, team) {
    var out = P.gaps.filter(function (g) { return (g.affects || []).indexOf(c) >= 0; }).map(function (g) {
      return "<strong>" + esc(g.title) + "</strong>. " + esc(g.impact) + ' <span class="muted small">(' + esc(g.source || g.id) + ")</span>";
    });
    if (team && team.gaps) team.gaps.forEach(function (g) { out.push(esc(g) + ' <span class="muted small">(team assessment)</span>'); });
    if (cmp && cmp.status === "mismatch") out.push('<span class="flag">Team evaluator and independent recompute disagree for this scope.</span> Treat the browser recompute as the check; fix the team evaluator and re-test.');
    if (P._problems.length) out.push("Evidence pack problems: " + esc(P._problems.join("; ")));
    return out;
  }

  // ---------- banners and chrome
  function chrome() {
    var m = P.meta || {};
    document.getElementById("claim").innerHTML = "<strong>" + esc((m.claim && m.claim.id) || "Claim") + "</strong> " + esc((m.claim && m.claim.text) || "") +
      '<br><span class="small">Team ' + esc(m.team || "?") + " · pack generated " + t(m.generated_at) + " · register " + esc(P.register.version || "?") +
      " dated " + t(P.register.version_date) + "</span>";
    var b = "";
    if (m.provenance === "SAMPLE") b += '<div class="banner sample" role="status"><strong>SAMPLE DATA.</strong> Synthetic records for rehearsal. Thresholds are placeholders. Load the real evidence pack before judging.</div>';
    else if (m.provenance) b += '<div class="banner live" role="status"><strong>' + esc(m.provenance) + " evidence pack.</strong> " + esc(m.note || "") + "</div>";
    if (P._problems.length) b += '<div class="banner problem" role="alert"><strong>Evidence pack check:</strong> ' + esc(P._problems.join("; ")) + ". Shown as gaps below.</div>";
    document.getElementById("banners").innerHTML = b;
  }

  // ---------- page: overview and progression
  function levelSummary(lv) {
    var c = { shown: 0, partial: 0, missing: 0 };
    (lv.checks || []).forEach(function (k) { c[k.status] = (c[k.status] || 0) + 1; });
    return c;
  }
  function viewOverview() {
    var keys = ["L1", "L2", "L3"], prevOk = true;
    var cols = keys.map(function (k, i) {
      var lv = P.levels[k] || { name: k, checks: [] }, s = levelSummary(lv), total = (lv.checks || []).length || 1;
      var demonstrated = s.missing === 0 && (lv.checks || []).length > 0;
      var gate = !prevOk ? '<div class="gate s-missing">Not recognised until ' + keys[i - 1] + " is demonstrated</div>"
               : (demonstrated ? '<div class="gate s-shown">Demonstrated' + (s.partial ? ", with " + s.partial + " partial check(s) recorded as gaps" : "") + "</div>"
               : '<div class="gate s-partial">' + s.missing + " check(s) missing</div>");
      prevOk = prevOk && demonstrated;
      return '<section class="level" aria-label="' + esc(k) + '"><div class="tag">Level ' + (i + 1) + (i === 0 ? " · required" : " · needs level " + i) + "</div>" +
        "<h3>" + esc(lv.name) + '</h3><div class="env">' + esc(lv.environment || "") + "</div>" +
        '<div class="small">' + esc(lv.requirement || "") + "</div>" +
        '<div class="bar" aria-hidden="true"><span class="b-shown" style="width:' + (s.shown / total * 100) + '%"></span><span class="b-partial" style="width:' +
        (s.partial / total * 100) + '%"></span><span class="b-missing" style="width:' + (s.missing / total * 100) + '%"></span></div>' +
        '<div class="small muted">' + s.shown + " shown · " + s.partial + " partial · " + s.missing + " missing</div>" + gate +
        '<ul class="checks">' + (lv.checks || []).map(function (ch) {
          return "<li>" + sbadge(ch.status) + "<div>" + esc(ch.label) + (ch.note ? '<div class="small muted">' + esc(ch.note) + "</div>" : "") +
            (ch.refs && ch.refs.length ? '<div class="small mono muted">' + esc(ch.refs.join(" · ")) + "</div>" : "") + "</div></li>";
        }).join("") + "</ul></section>";
    }).join("");

    var tiles = CONTROLS.map(function (c) {
      var rl = rule(c), named = namedRuns(c);
      var per = named.map(function (r) { return { r: r, res: evaluate(c, { kind: "run", id: r.run_id }) }; });
      var lines = per.map(function (p) {
        return "<li>" + badge(p.res.verdict) + ' <a href="#live" data-ask="' + esc(c) + "|" + esc(p.r.run_id) + '" class="mono small">' + esc(p.r.run_id) + "</a> " +
          '<span class="small muted">named ' + esc(p.r.named[c]) + "</span></li>";
      }).join("");
      var named2 = per.length >= 2 && per.some(function (p) { return p.r.named[c] === "pass"; }) && per.some(function (p) { return p.r.named[c] === "breach"; });
      return '<div class="card"><h3>' + esc(c + " " + rl.name) + '</h3><div class="tile-meta">' + esc(rl.control_id) + " · " + esc(rl.mode) +
        " · rule " + esc(P.register.version) + " · owner " + esc(rl.owner) + '</div><ul class="checks">' + (lines || '<li class="empty">No named runs yet</li>') + "</ul>" +
        '<div class="note">' + (named2 ? "✔ One passing and one breaching named run" : '<span class="flag">Needs one passing and one breaching named run</span>') + "</div></div>";
    }).join("");

    return "<h1>Overview and progression</h1>" +
      '<p class="lead">Judging is sequential: Level 2 counts only once Level 1 is shown, and Level 3 only once Level 2 is. Every check below links to its evidence. Partial checks are recorded as gaps, not hidden.</p>' +
      '<div class="progress">' + cols + "</div>" +
      "<h2>Controls completed end to end (axis 1)</h2>" +
      '<p class="lead">Each verdict below is recomputed now, in your browser, from the raw records and the frozen register. Click a run to ask about it on the live test page.</p>' +
      '<div class="grid g3 tiles">' + tiles + "</div>" +
      '<p style="margin-top:18px"><a class="btn primary" href="#live">Ask a control question</a></p>';
  }

  // ---------- page: live test
  function scopeFromState() {
    return state.scopeKind === "run" ? { kind: "run", id: state.runId } : { kind: "range", from: state.from + ":00Z", to: state.to + ":00Z" };
  }
  function viewLive() {
    var runOpts = P.runs.map(function (r) {
      var tag = r.named ? Object.keys(r.named).map(function (k) { return k + " " + r.named[k]; }).join(", ") : "";
      return '<option value="' + esc(r.run_id) + '"' + (r.run_id === state.runId ? " selected" : "") + ">" + esc(r.run_id) + (tag ? " (named: " + esc(tag) + ")" : "") + "</option>";
    }).join("");
    var form = '<form class="card" id="ask-form"><div class="ask">' +
      '<label class="field">Control<select id="ask-control">' + CONTROLS.map(function (c) {
        return '<option value="' + c + '"' + (c === state.control ? " selected" : "") + ">" + esc(controlTitle(c)) + "</option>";
      }).join("") + "</select></label>" +
      '<label class="field">Scope<select id="ask-kind"><option value="run"' + (state.scopeKind === "run" ? " selected" : "") + '>One run</option><option value="range"' +
      (state.scopeKind === "range" ? " selected" : "") + ">A time window</option></select></label>" +
      (state.scopeKind === "run"
        ? '<label class="field">Run<select id="ask-run">' + runOpts + "</select></label>"
        : '<div class="scope-range"><label class="field">From (UTC)<input type="datetime-local" id="ask-from" value="' + esc(state.from) + '"></label>' +
          '<label class="field">To (UTC)<input type="datetime-local" id="ask-to" value="' + esc(state.to) + '"></label></div>') +
      '<button class="btn primary" type="submit">Check control</button></div>' +
      '<div class="timer" id="timer" style="margin-top:10px"></div></form>';
    return "<h1>Live test</h1><p class=\"lead\">The judge names a control and a run or time window. The answer below comes from the evidence pack alone: rule, population, measurement, exceptions, verdict, records, who was told, and the gaps.</p>" +
      form + '<div id="answer">' + (state.answer ? renderAnswer(state.answer) : "") + "</div>";
  }
  function showError(err) {
    var msg = "This page could not be computed from the evidence pack: " + (err && err.message ? err.message : err) +
      ". Most likely the register or records do not follow the data contract in dashboard/README.md. Recorded as a gap.";
    if (P && P._problems && P._problems.indexOf(msg) < 0) P._problems.push(msg);
    document.getElementById("view").innerHTML = '<div class="banner problem" role="alert">' + esc(msg) + "</div>";
  }
  function ask() {
    var scope = scopeFromState();
    var res;
    try { res = evaluate(state.control, scope); } catch (err) { showError(err); return; }
    state.answeredAt = Date.now();
    state.answer = { control: state.control, scope: scope, res: res };
    var el = document.getElementById("answer");
    if (el) el.innerHTML = renderAnswer(state.answer);
    tick();
  }
  function renderAnswer(a) {
    var c = a.control, rl = rule(c), res = a.res, scope = a.scope;
    var scopeText = scope.kind === "run" ? "run " + scope.id : "window " + scope.from.replace("T", " ") + " to " + scope.to.replace("T", " ");
    var r = scope.kind === "run" ? run(scope.id) : null;
    var dated = scope.kind === "run" ? [r] : runsInRange(scope.from, scope.to);
    var datedOk = dated.filter(Boolean).every(function (x) { return E.datedBefore(P.register, x); });
    var team = teamAssessment(c, scope), cmp = compareTeam(c, res, team);
    var h = '<section class="card" style="margin-top:14px" aria-label="Answer"><div class="answer-head"><div><div class="small muted">' + esc(controlTitle(c)) + " · " + esc(scopeText) + "</div>" +
      '<p class="reason">' + badge(res.verdict, true) + "&nbsp; " + esc(res.reason) + "</p></div>" +
      '<button class="btn small" type="button" id="export-case">Download this answer (JSON)</button></div>';

    h += '<div class="grid g2" style="margin-top:14px"><div><h3>Rule, from the frozen register</h3><dl class="kv">' +
      "<dt>Rule</dt><dd>" + esc(res.limit_text || "–") + "</dd>" +
      "<dt>Metric</dt><dd>" + esc(rl.metric) + "</dd>" +
      "<dt>Version and date</dt><dd>" + esc(P.register.version) + " · " + t(P.register.version_date) + "</dd>" +
      "<dt>Dated before the test?</dt><dd>" + (datedOk ? sbadge("yes") + " register predates " + (scope.kind === "run" ? "this run" : "every run in the window")
        : sbadge("no") + ' <span class="flag">a threshold dated after the test loses marks</span>') + "</dd>" +
      "<dt>Owner</dt><dd>" + esc(rl.owner) + "</dd>" +
      "<dt>Threshold held by</dt><dd>" + esc(P.register.source || "register") + ", not the control code</dd>" +
      "<dt>Approved</dt><dd>" + esc((P.register.approved && P.register.approved.by) || "–") + " · " + t(P.register.approved && P.register.approved.at) + "</dd></dl></div>" +
      "<div><h3>Measured</h3><dl class=\"kv\">" + Object.keys(res.measured || {}).map(function (k) {
        return "<dt>" + esc(k.replace(/_/g, " ")) + "</dt><dd>" + n(res.measured[k]) + "</dd>";
      }).join("") +
      "<dt>Population</dt><dd>expected " + (res.population && res.population.expected !== undefined ? n(res.population.expected) : "not independently listed") + " · observed " + n(res.population && res.population.observed) +
      " · missing " + n(res.population && res.population.missing) + (res.population && res.population.source ? '<div class="small muted">' + esc(res.population.source) + "</div>" : "") + "</dd>" +
      "<dt>Formula</dt><dd>" + esc(res.formula || "–") + "</dd></dl></div></div>";

    h += "<h3 style=\"margin-top:16px\">Exceptions</h3>" + list((res.exceptions || []).map(esc), "No exceptions in this scope.");

    h += '<h3 style="margin-top:16px">Independent recompute</h3>';
    if (cmp.status === "none") h += '<p class="empty">No team assessment for this exact scope; the verdict above is the browser recompute only.</p>';
    else h += '<div class="compare"><div class="card"><div class="small muted">Team evaluator (' + esc(team.evaluator && team.evaluator.name) + ", " + esc(team.assessment_id) + ")</div>" +
      badge(team.verdict) + (cmp.key ? " " + esc(cmp.key.replace(/_/g, " ")) + ": " + n(cmp.teamVal) : "") + '</div><div class="card"><div class="small muted">Recomputed in your browser from raw records</div>' +
      badge(res.verdict) + (cmp.key ? " " + esc(cmp.key.replace(/_/g, " ")) + ": " + n(cmp.ourVal) : "") + "</div></div>" +
      '<p class="match ' + (cmp.status === "match" ? "yes" : "no") + '">' + (cmp.status === "match" ? "✔ They match." : "✖ They disagree" +
        (!cmp.verdictMatch ? " on the verdict" : "") + (!cmp.valueMatch ? " on the measured value" : "") + ". The difference is listed as a gap below.") + "</p>";

    h += detailFor(c, res, scope);

    var fs = findingsFor(c, scope);
    h += '<h3 style="margin-top:16px">Who was told</h3>' + table(["Finding", "Verdict", "Incident", "Assigned to", "Delivery", "Response"], fs.map(function (f) {
      return ['<span class="mono small">' + esc(f.finding_id) + "</span>", badge(f.verdict), esc(f.incident), esc(f.assigned_to),
              esc(f.delivery.state) + "<br><span class=\"small muted\">" + t(f.delivery.at) + "</span>",
              esc(f.response.state) + (f.response.at ? "<br><span class=\"small muted\">" + t(f.response.at) + "</span>" : "")];
    }), res.verdict === "SATISFIED" ? "No alert needed: the control was satisfied in this scope." : "No finding recorded for this scope. That is itself a gap.");

    h += '<h3 style="margin-top:16px">Gaps for this scope</h3>' + list(gapsFor(c, scope, cmp, team), "None recorded for this scope.");

    if (scope.kind === "run") h += auditorFor(scope.id) + timelineFor(scope.id);
    h += "</section>";
    return h;
  }
  function detailFor(c, res, scope) {
    if (res.objective) {
      return '<h3 style="margin-top:16px">Runs in this window</h3>' + table(["Run", "Started", "Verdict", "Why"], res.per.map(function (p) {
        return ['<a href="#live" class="mono small" data-ask="' + esc(c) + "|" + esc(p.run.run_id) + '">' + esc(p.run.run_id) + "</a>", t(p.run.started_at), badge(p.res.verdict), esc(p.res.reason)];
      }), "No runs started in this window.");
    }
    var byId = {}; P.records.forEach(function (r) { byId[r.id] = r; });
    if (c === "C16") {
      var rows = res.record_ids.map(function (id) { return byId[id]; }).filter(Boolean).map(function (r) {
        return ['<span class="mono small">' + esc(r.id) + "</span>", esc(r.actor), '<span class="mono small">' + esc(r.call_id) + "</span>", n(r.input_tokens), n(r.output_tokens),
                r.retry ? "retry" : "", '<span class="mono small">' + esc(r.source && r.source.ref) + "</span>"];
      });
      var dec = P.records.filter(function (r) { return r.kind === "decision" && r.control_ref === "C16" && r.run_id === scope.id; });
      return '<h3 style="margin-top:16px">Every call counted (figure of record: ' + esc(rule(c).figure_of_record_ep) + ")</h3>" +
        table(["Record", "Agent", "Call", "In", "Out", "", "Source"], rows, "No model-call records.", [3, 4]) +
        '<h3 style="margin-top:16px">Decision records bound to this control</h3>' +
        table(["At", "Call", "Running total", "Threshold", "Version", "Verdict", "Mode"], dec.map(function (d) {
          return [t(d.at), '<span class="mono small">' + esc(d.call_id) + "</span>", n(d.measured_value), n(d.threshold_value), esc(d.threshold_version), badge(d.verdict), esc(d.mode)];
        }), "No per-call decision records for this run. Gap: C16 evidence is only the post-run assessment.", [2, 3]);
    }
    if (c === "C7") {
      var exp = (P.expected_events[scope.id] || { events: [] }).events;
      var obs = {}; P.records.forEach(function (r) { if (r.run_id === scope.id && r.expected_event_id && !obs[r.expected_event_id]) obs[r.expected_event_id] = r; });
      return '<h3 style="margin-top:16px">Expected events (independent source) vs recorded</h3>' +
        table(["Event", "Expected", "Recorded at", "Record", "Source"], exp.map(function (e) {
          var o = obs[e.id];
          return [esc(e.id), esc(e.label), o ? t(o.at) : '<span class="flag">missing</span>', o ? '<span class="mono small">' + esc(o.id) + "</span>" : "–",
                  o ? '<span class="mono small">' + esc(o.source && o.source.ref) + "</span>" : "–"];
        }), "No expected events defined for this run.") +
        '<h3 style="margin-top:16px">Gaps between consecutive events</h3>' +
        table(["Pair", "Gap (ms)", "Status"], (res.gaps || []).map(function (g) {
          return [esc(g.pair), g.ms === null ? "–" : n(g.ms), g.status === "within limit" ? '<span class="verdict s-yes">✔ within limit</span>' : '<span class="flag">' + esc(g.status) + "</span>"];
        }), "No measurable gaps.", [1]);
    }
    return '<h3 style="margin-top:16px">Windows ' + (scope.kind === "run" ? "this run fell in (C9 is hourly, so this is the hour, not the run alone)" : "in this range") + "</h3>" +
      table(["Window", "Runtime", "Latency (ms)", "Baseline (ms)", "Change", "Status", "Source"], (res.windows || []).map(function (w) {
        var b = rule("C9").baseline[w.w.runtime];
        return ['<span class="mono small">' + esc(w.w.start.slice(0, 16).replace("T", " ")) + "</span>", esc(w.w.runtime), n(w.w.value), n(b && b.value),
                w.rel === null ? "–" : (w.rel > 0 ? "+" : "") + w.rel + "%",
                w.status === "within limit" ? '<span class="verdict s-yes">✔ within limit</span>' : '<span class="flag">' + esc(w.status) + "</span>",
                '<span class="mono small">' + esc(w.w.source && w.w.source.ref) + "</span>"];
      }), "No windows in scope.", [2, 3]);
  }
  function auditorFor(runId) {
    var qs = P.auditor[runId] || [];
    var gapById = {}; P.gaps.forEach(function (g) { gapById[g.id] = g; });
    return '<h3 style="margin-top:16px">Six auditor questions for this run</h3>' + table(["Question", "Status", "Answer from the evidence", "Limited by"], qs.map(function (q) {
      return ["<strong>" + esc(q.q) + "</strong>", sbadge(q.status), esc(q.answer), q.gap ? esc((gapById[q.gap] && gapById[q.gap].title) || q.gap) : '<span class="muted">nothing recorded</span>'];
    }), "No auditor answers in the pack for this run. Gap: the six questions are unanswered.");
  }
  function timelineFor(runId) {
    var recs = P.records.filter(function (r) { return r.run_id === runId && r.ep !== "EP3"; }).sort(function (a, b) { return Date.parse(a.at) - Date.parse(b.at); });
    return '<details style="margin-top:16px"><summary>Reconstruct the run: ' + recs.length + " records in time order</summary>" +
      table(["At", "Kind", "Actor", "What happened", "Source"], recs.map(function (r) {
        var flag = r.declared === false ? ' <span class="flag">undeclared tool</span>' : "";
        return [t(r.at), esc(r.kind), esc(r.actor), esc(r.summary) + flag, '<span class="mono small">' + esc(r.source && r.source.ref) + "</span>"];
      }), "No records.") + "</details>";
  }

  // ---------- page: architecture
  function viewArchitecture() {
    var A = P.architecture || {};
    var rules = table(["Judges ask", "Holds?", "How you can tell"], (A.rules || []).map(function (r) {
      return [esc(r.rule), sbadge(r.holds), esc(r.how)];
    }), "No architecture rules in the pack. Gap.");
    var eps = (A.eps || []).map(function (e) {
      return '<div class="card"><h3>' + esc(e.id + " · " + e.name) + '</h3><dl class="kv"><dt>Position</dt><dd>' + esc(e.position) + "</dd><dt>Transport</dt><dd class=\"mono\">" +
        esc(e.transport) + "</dd><dt>Feeds</dt><dd>" + esc((e.controls || []).join(", ")) + "</dd><dt>Adapter</dt><dd>" + esc(e.adapter) + "</dd><dt>Verified behaviour</dt><dd>" +
        esc(e.verified) + "</dd></dl></div>";
    }).join("");
    var epIds = (A.eps || []).map(function (e) { return e.id; });
    var epOpts = function (sel) { return epIds.map(function (id) { return '<option value="' + esc(id) + '"' + (id === sel ? " selected" : "") + ">" + esc(id) + "</option>"; }).join(""); };
    var runOpts = P.runs.map(function (r) { return '<option value="' + esc(r.run_id) + '"' + (r.run_id === state.epRun ? " selected" : "") + ">" + esc(r.run_id) + "</option>"; }).join("");
    var cmp = secondEp();
    return "<h1>Architecture</h1><p class=\"lead\">Decision is separated from enforcement. Adapters at each enforcement point feed one contract; the same stateless evaluators judge every point; the frozen register is data, never in the request path.</p>" +
      "<h2>What judges check on the architecture</h2>" + rules +
      "<h2>Does it survive a second enforcement point?</h2>" +
      '<p class="lead">Pick a control and a run, then two enforcement points. The same evaluator function runs on the records each point observed. Nothing is rewritten; only the adapter differs.</p>' +
      '<div class="card"><div class="filters"><label class="field">Control<select id="ep-control">' + ["C16", "C7"].map(function (c) {
        return '<option value="' + c + '"' + (c === state.epControl ? " selected" : "") + ">" + esc(controlTitle(c)) + "</option>"; }).join("") + "</select></label>" +
      '<label class="field">Run<select id="ep-run">' + runOpts + "</select></label>" +
      '<label class="field">Enforcement point A<select id="ep-a">' + epOpts(state.epA) + "</select></label>" +
      '<label class="field">Enforcement point B<select id="ep-b">' + epOpts(state.epB) + "</select></label></div>" + cmp + "</div>" +
      "<h2>Enforcement points</h2><div class=\"grid g2\">" + (eps || '<p class="empty">No enforcement points in the pack. Gap.</p>') + "</div>" +
      "<h2>Core (unchanged across enforcement points)</h2><dl class=\"kv card\">" + Object.keys(A.core || {}).map(function (k) {
        return "<dt>" + esc(k) + "</dt><dd>" + esc(A.core[k]) + "</dd>"; }).join("") + "</dl>" +
      '<p class="note">One-page diagram: docs/team-plan/architecture.png in the repository.</p>';
  }
  function secondEp() {
    var c = state.epControl, rl = rule(c);
    function at(ep) {
      var recs = P.records.filter(function (r) { return r.ep === ep || (ep !== "EP3" && r.ep === "LEDGER" && c === "C7"); });
      return c === "C16" ? E.evalC16(state.epRun, recs, rl) : E.evalC7(state.epRun, recs, P.expected_events, rl);
    }
    var a = at(state.epA), b = at(state.epB);
    var key = c === "C16" ? "total_tokens" : "coverage_pct";
    var same = a.verdict === b.verdict && a.measured[key] === b.measured[key];
    function cell(ep, r) {
      return '<div class="card"><div class="small muted">' + esc(ep) + " · same function: Evaluators.eval" + esc(c) + "</div>" + badge(r.verdict) +
        '<div class="small" style="margin-top:6px">' + esc(key.replace(/_/g, " ")) + ": " + n(r.measured[key]) + " · observed " + n(r.population.observed) + "</div>" +
        '<div class="small muted">' + esc(r.reason) + "</div></div>";
    }
    return '<div class="compare">' + cell(state.epA, a) + cell(state.epB, b) + "</div>" +
      '<p class="match ' + (same ? "yes" : "no") + '">' + (same ? "✔ Same verdict and value at both points: the design moved without a rewrite."
        : "✖ The points disagree. The evaluator is the same; the difference is what each point can observe. Recorded as a gap, not hidden.") + "</p>";
  }

  // ---------- page: evidence vs logs
  var BIND = [["what happened", function (r) { return !!r.summary; }], ["which control", function (r) { return !!r.control_ref; }],
              ["threshold version", function (r) { return !!r.threshold_version; }], ["which run", function (r) { return !!r.run_id; }],
              ["who acted", function (r) { return !!r.actor; }], ["when", function (r) { return !!r.at; }], ["source", function (r) { return !!(r.source && r.source.ref); }]];
  function viewEvidence() {
    var kinds = {}, eps = {};
    P.records.forEach(function (r) { kinds[r.kind] = 1; eps[r.ep] = 1; });
    var sel = function (id, cur, vals, all) {
      return '<select id="' + id + '"><option value="">' + all + "</option>" + vals.map(function (v) {
        return '<option value="' + esc(v) + '"' + (v === cur ? " selected" : "") + ">" + esc(v) + "</option>"; }).join("") + "</select>";
    };
    var recs = P.records.filter(function (r) {
      return (!state.evRun || r.run_id === state.evRun) && (!state.evKind || r.kind === state.evKind) && (!state.evEp || r.ep === state.evEp);
    }).sort(function (a, b) { return Date.parse(a.at) - Date.parse(b.at); });
    var shown = recs.slice(0, 300);
    var body;
    if (state.evView === "log") {
      body = '<div class="card"><div class="logline">' + shown.map(function (r) {
        return esc(r.at + "  INFO  " + (r.ep || "") + "  " + (r.actor || "") + "  " + (r.summary || r.kind));
      }).join("\n") + "</div></div>" +
        '<p class="note">This is what a log looks like: it shows something happened, not which rule it was checked against, at which threshold, with what verdict. Switch to Evidence.</p>';
    } else {
      body = table(["At", "Record", "What happened", "Bindings (evidence needs all seven)", "Verdict", "Source"], shown.map(function (r) {
        var have = BIND.map(function (b) { return [b[0], b[1](r)]; });
        var full = have.every(function (x) { return x[1]; });
        return [t(r.at), '<span class="mono small">' + esc(r.id) + "</span><br>" + '<span class="pill">' + esc(r.kind) + "</span>", esc(r.summary),
                '<div class="binding">' + have.map(function (x) { return '<span class="' + (x[1] ? "have" : "lack") + '">' + (x[1] ? "✔ " : "✖ ") + esc(x[0]) + "</span>"; }).join("") + "</div>" +
                (full ? "" : '<div class="small muted">Observation: input to a control, not yet a decision</div>'),
                r.verdict ? badge(r.verdict) : "–", '<span class="mono small">' + esc(r.source && r.source.ref) + "</span>"];
      }), "No records match these filters.");
    }
    var decisions = P.records.filter(function (r) { return BIND.every(function (b) { return b[1](r); }); }).length;
    return "<h1>Evidence, not logs</h1><p class=\"lead\">A log is written for an engineer next week. Evidence is written for a sceptical stranger: each decision record is bound to what happened, which control, which threshold version, which run, who acted, when, and where the raw record lives. Sealing is out of scope for this hackathon.</p>" +
      '<div class="grid g3"><div class="card"><h3>' + n(P.records.length) + "</h3>records in the pack</div><div class=\"card\"><h3>" + n(decisions) +
      "</h3>fully bound decision records</div><div class=\"card\"><h3>" + n(P.records.length - decisions) + "</h3>observations (raw inputs to controls)</div></div>" +
      '<div class="filters" style="margin-top:14px"><label class="field">Run' + sel("ev-run", state.evRun, P.runs.map(function (r) { return r.run_id; }), "All runs") + "</label>" +
      '<label class="field">Kind' + sel("ev-kind", state.evKind, Object.keys(kinds), "All kinds") + "</label>" +
      '<label class="field">Enforcement point' + sel("ev-ep", state.evEp, Object.keys(eps), "All points") + "</label>" +
      '<div class="seg" role="group" aria-label="View as"><button type="button" data-evview="evidence" aria-pressed="' + (state.evView === "evidence") +
      '">Evidence</button><button type="button" data-evview="log" aria-pressed="' + (state.evView === "log") + '">As a log</button></div></div>' + body +
      (recs.length > shown.length ? '<p class="note">Showing the first ' + shown.length + " of " + recs.length + ". Filter to narrow.</p>" : "") +
      "<h2>Verify it yourself, without us</h2><ol>" +
      "<li>Pick a control and run on the Live test page. The verdict is recomputed in your browser by <span class=\"mono\">evaluators.js</span> from these records and the register.</li>" +
      "<li>Open any record's source reference (for example <span class=\"mono\">raw/gateway/&lt;run&gt;.jsonl#L3</span>) in the evidence pack and compare the token counts.</li>" +
      "<li>Run <span class=\"mono\">node dashboard/tests/evaluators.test.js</span> to check the evaluator against the masterclass worked examples.</li>" +
      "<li>Check file checksums with <span class=\"mono\">shasum -a 256</span> against MANIFEST in the pack.</li></ol>" +
      table(["File", "SHA-256", "Bytes"], (P.manifest || []).map(function (m) { return ['<span class="mono small">' + esc(m.path) + "</span>", '<span class="mono small">' + esc(m.sha256) + "</span>", n(m.bytes)]; }),
            "No MANIFEST in the pack. Gap: files cannot be checked for changes.", [2]);
  }

  // ---------- page: thresholds
  function viewThresholds() {
    var R = P.register;
    var cards = CONTROLS.map(function (c) {
      var rl = rule(c), q = rl.rationale || {};
      var lim = Object.keys(rl.observation_limit || {}).map(function (k) { return esc(k.replace(/_/g, " ")) + ": " + n(rl.observation_limit[k]); }).join("<br>");
      var tol = Object.keys(rl.exception_tolerance || {}).map(function (k) { return esc(k.replace(/_/g, " ")) + ": " + n(rl.exception_tolerance[k]); }).join("<br>");
      var base = rl.baseline ? Object.keys(rl.baseline).map(function (k) { return esc(k) + ": " + n(rl.baseline[k].value) + " " + esc(rl.baseline[k].unit) + " (" + esc(rl.baseline[k].id) + ")"; }).join("<br>") : "";
      return '<div class="card"><h3>' + esc(controlTitle(c)) + '</h3><dl class="kv"><dt>Mode</dt><dd>' + esc(rl.mode) + "</dd><dt>Metric</dt><dd>" + esc(rl.metric) +
        "</dd><dt>Observation limit</dt><dd>" + lim + "</dd><dt>Exception tolerance</dt><dd>" + tol + "</dd>" + (base ? "<dt>Frozen baseline</dt><dd>" + base + "</dd>" : "") +
        "<dt>Measurement basis</dt><dd>" + esc(rl.measurement_basis) + "</dd><dt>Owner</dt><dd>" + esc(rl.owner) + "</dd>" +
        "<dt>Why this metric?</dt><dd>" + esc(q.why_metric || "–") + "</dd><dt>Why this value?</dt><dd>" + esc(q.why_value || "–") +
        "</dd><dt>Measured on what?</dt><dd>" + esc(q.measured_on || "–") + "</dd><dt>When does it stop holding?</dt><dd>" + esc(q.stops_holding || "–") + "</dd></dl></div>";
    }).join("");
    var rows = P.runs.map(function (r) {
      var ok = E.datedBefore(R, r);
      return ['<span class="mono small">' + esc(r.run_id) + "</span>", t(r.started_at), t(R.version_date), ok ? sbadge("yes") : sbadge("no") + ' <span class="flag">dated after the test</span>'];
    });
    return "<h1>Thresholds</h1><p class=\"lead\">One entry per control: metric, limit, exception tolerance, measurement basis, owner, version and date. The register is data the evaluators receive; no control stores its own number.</p>" +
      '<dl class="kv card"><dt>Register</dt><dd>' + esc(R.source || "") + "</dd><dt>Version</dt><dd>" + esc(R.version) + "</dd><dt>Dated</dt><dd>" + t(R.version_date) +
      "</dd><dt>Status</dt><dd>" + esc(R.status) + "</dd><dt>Approved by</dt><dd>" + esc(R.approved && R.approved.by) + " · " + t(R.approved && R.approved.at) +
      ' <span class="small muted">' + esc(R.approved && R.approved.ref) + "</span></dd></dl>" +
      "<h2>Was every threshold dated before the run it judged?</h2>" + table(["Run", "Run started", "Register dated", "Before the test?"], rows, "No runs.") +
      '<h2>Controls</h2><div class="grid g3">' + cards + "</div>";
  }

  // ---------- page: gaps
  function viewGaps() {
    var qs = ["C16", "C7", "C9", "WHO", "WHAT", "AUTHORIZED", "APPROVED", "INTEGRITY", "RECONSTRUCT", "DATA", "L3"];
    var cover = qs.map(function (q) {
      var g = P.gaps.filter(function (x) { return (x.affects || []).indexOf(q) >= 0; });
      return [esc(q), g.length ? g.map(function (x) { return esc(x.title); }).join("<br>") : '<span class="muted">none recorded</span>'];
    });
    var problems = (P._problems || []).map(function (p) { return ["Evidence pack", esc(p), "Pack check", "The section cannot be scored until supplied", "Re-run pack_evidence.py"]; });
    return "<h1>Gaps and honesty</h1><p class=\"lead\">What we could not close, and why. \"Built properly: yes. Actually worked: no\" is the most useful answer a team can bring, so every partial or failed item is listed here and linked from the answers that depend on it.</p>" +
      table(["Gap", "Why", "Affects", "Impact on the verdict", "If we had one more day"], P.gaps.map(function (g) {
        return ["<strong>" + esc(g.title) + '</strong><div class="small muted mono">' + esc(g.source || g.id) + "</div>", esc(g.why), esc((g.affects || []).join(", ")), esc(g.impact), esc(g.next)];
      }).concat(problems), "No gaps recorded. That is not believable; check the pack.") +
      "<h2>Coverage: every control and auditor question has its gaps stated or 'none recorded'</h2>" + table(["Area", "Gaps"], cover, "");
  }

  // ---------- page: human loop
  function viewLoop() {
    var rows = P.human_loop.map(function (f) {
      return [esc(f.control_ref), esc(f.scope.kind + " " + f.scope.id), badge(f.verdict), esc(f.incident), esc(f.assigned_to),
              esc(f.delivery.state) + (f.delivery.readback ? " · read back" : "") + '<br><span class="small muted">' + t(f.delivery.at) + "</span>",
              esc(f.response.state) + (f.response.at ? '<br><span class="small muted">' + t(f.response.at) + "</span>" : ""),
              f.retest ? esc(f.retest) : '<span class="muted">no passing re-test yet</span>', esc(f.status)];
    });
    return "<h1>Human loop</h1><p class=\"lead\">Every breach, monitoring gap and agent escalation becomes a ServiceNow incident assigned to the named owner, read back after creation. The owner's response, or their silence after the cutoff, is recorded. A finding closes only with a linked passing re-test.</p>" +
      table(["Control", "Scope", "Verdict", "Incident", "Owner", "Delivery", "Response", "Re-test", "Status"], rows, "No findings delivered yet. Gap: the human loop is not evidenced.");
  }

  // ---------- page: adversarial
  function viewAdversarial() {
    var rows = P.adversarial.map(function (a) {
      return [esc(a.id), esc(a.level), esc(a.attack), esc(a.target), esc(a.expected), esc(a.observed), sbadge(a.result), esc(a.changed) + (a.note ? '<div class="small muted">' + esc(a.note) + "</div>" : "")];
    });
    var broke = P.adversarial.filter(function (a) { return a.result === "broke"; }).length;
    return "<h1>Adversarial tests</h1><p class=\"lead\">We attacked our own design at the Hostile level (tampered prompts, delays, conflicting context) and the Rogue level (bypass, unauthorised tools, tampered records). " +
      n(broke) + " of " + n(P.adversarial.length) + " attacks broke something; each says what we changed or why we could not.</p>" +
      table(["#", "Level", "Attack", "Target", "Expected", "Observed", "Result", "What we changed"], rows, "No adversarial tests recorded. Gap: the bonus cannot be claimed.");
  }

  // ---------- page: judgement day
  function viewJudgement() {
    var named = CONTROLS.map(function (c) {
      var p = namedRuns(c).filter(function (r) { return r.named[c] === "pass"; }), b = namedRuns(c).filter(function (r) { return r.named[c] === "breach"; });
      return [esc(controlTitle(c)), p.length ? p.map(function (r) { return '<a class="mono small" href="#live" data-ask="' + esc(c) + "|" + esc(r.run_id) + '">' + esc(r.run_id) + "</a>"; }).join("<br>") : '<span class="flag">not named</span>',
              b.length ? b.map(function (r) { return '<a class="mono small" href="#live" data-ask="' + esc(c) + "|" + esc(r.run_id) + '">' + esc(r.run_id) + "</a>"; }).join("<br>") : '<span class="flag">not named</span>'];
    });
    var left = state.rehearsalEnd ? Math.max(0, Math.round((state.rehearsalEnd - Date.now()) / 1000)) : 120;
    return "<h1>Judgement day</h1><p class=\"lead\">If an artefact is missing it cannot be scored. Everything below must be in the team S3 bucket the evening before.</p>" +
      table(["#", "Artefact", "Status", "Where"], P.artefacts.map(function (a) { return [n(a.n), esc(a.name), esc(a.status), esc(a.where)]; }), "No artefact list in the pack.") +
      '<p style="margin-top:12px"><button class="btn primary" type="button" id="dl-pack">Download evidence file (JSON)</button> ' +
      '<button class="btn" type="button" id="dl-register">Download threshold document (JSON)</button></p>' +
      "<h2>Named runs, written down before judging</h2>" + table(["Control", "Passing run", "Breaching run"], named, "") +
      "<h2>The two-minute question</h2><p class=\"lead\">The judge names one control and one run. Rehearse twice on the named runs, with someone outside the build team asking.</p>" +
      '<div class="card"><span class="timer" id="rehearsal">Rehearsal timer: <strong>' + Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0") +
      '</strong></span> <button class="btn small" type="button" id="rehearse">Start 2-minute rehearsal</button> <a class="btn small" href="#live">Go to live test</a></div>';
  }

  // ---------- router, events, timer
  var VIEWS = { overview: viewOverview, live: viewLive, architecture: viewArchitecture, evidence: viewEvidence, thresholds: viewThresholds,
                gaps: viewGaps, loop: viewLoop, adversarial: viewAdversarial, judgement: viewJudgement };
  function page() { var h = location.hash.replace("#", "").split("/")[0]; return VIEWS[h] ? h : "overview"; }
  function deepLink() {
    var parts = location.hash.replace("#", "").split("/");
    if (parts[0] !== "live" || parts.length < 3 || CONTROLS.indexOf(parts[1]) < 0) return false;
    state.control = parts[1];
    if (parts[2] === "window" && parts.length >= 5) { state.scopeKind = "range"; state.from = decodeURIComponent(parts[3]); state.to = decodeURIComponent(parts[4]); }
    else if (run(decodeURIComponent(parts[2]))) { state.scopeKind = "run"; state.runId = decodeURIComponent(parts[2]); }
    else return false;
    newQuestion(); history.replaceState(null, "", "#live"); return true;
  }
  function render() {
    if (!P) return;
    chrome();
    var pg = page();
    var linked = pg === "live" && deepLink();
    try {
      if (linked) { state.answer = { control: state.control, scope: scopeFromState(), res: evaluate(state.control, scopeFromState()) }; state.answeredAt = Date.now(); }
      document.getElementById("view").innerHTML = VIEWS[pg]();
    } catch (err) { showError(err); }
    document.querySelectorAll(".side nav a").forEach(function (a) {
      if (a.getAttribute("href") === "#" + pg) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    tick();
  }
  function tick() {
    var el = document.getElementById("timer");
    if (el) {
      var asked = Math.round((Date.now() - state.askedAt) / 1000);
      el.innerHTML = state.answeredAt && state.answer
        ? "Question set " + asked + " s ago · answered in <strong>" + Math.max(0, Math.round((state.answeredAt - state.askedAt) / 1000)) + " s</strong> (judges allow 120 s)"
        : "Question set " + asked + " s ago · the judges allow 120 s";
    }
    var r = document.getElementById("rehearsal");
    if (r && state.rehearsalEnd) {
      var left = Math.max(0, Math.round((state.rehearsalEnd - Date.now()) / 1000));
      r.innerHTML = "Rehearsal timer: <strong>" + Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0") + "</strong>" + (left === 0 ? " · time is up" : "");
    }
  }
  function newQuestion() { state.askedAt = Date.now(); state.answeredAt = null; state.answer = null; }

  document.addEventListener("change", function (e) {
    var id = e.target.id, v = e.target.value;
    if (id === "ask-control") { state.control = v; newQuestion(); render(); }
    else if (id === "ask-kind") { state.scopeKind = v; newQuestion(); render(); }
    else if (id === "ask-run") { state.runId = v; newQuestion(); render(); }
    else if (id === "ask-from") { state.from = v; newQuestion(); }
    else if (id === "ask-to") { state.to = v; newQuestion(); }
    else if (id === "ev-run") { state.evRun = v; render(); }
    else if (id === "ev-kind") { state.evKind = v; render(); }
    else if (id === "ev-ep") { state.evEp = v; render(); }
    else if (id === "ep-control") { state.epControl = v; render(); }
    else if (id === "ep-run") { state.epRun = v; render(); }
    else if (id === "ep-a") { state.epA = v; render(); }
    else if (id === "ep-b") { state.epB = v; render(); }
    else if (id === "pack-file" && e.target.files[0]) {
      var fr = new FileReader();
      fr.onload = function () {
        try { load(JSON.parse(fr.result)); }
        catch (err) { document.getElementById("banners").innerHTML = '<div class="banner problem" role="alert">Could not read that file as an evidence pack: ' + esc(err.message) + "</div>"; }
      };
      fr.readAsText(e.target.files[0]);
      e.target.value = "";
    }
  });
  document.addEventListener("submit", function (e) { if (e.target.id === "ask-form") { e.preventDefault(); ask(); } });
  document.addEventListener("click", function (e) {
    var a = e.target.closest("[data-ask]");
    if (a) {
      var parts = a.getAttribute("data-ask").split("|");
      state.control = parts[0]; state.scopeKind = "run"; state.runId = parts[1]; newQuestion();
      if (location.hash === "#live") { render(); ask(); } else { location.hash = "#live"; setTimeout(ask, 0); }
      e.preventDefault(); return;
    }
    var ev = e.target.closest("[data-evview]");
    if (ev) { state.evView = ev.getAttribute("data-evview"); render(); return; }
    if (e.target.id === "export-case" && state.answer) {
      download("answer-" + state.answer.control + "-" + (state.answer.scope.id || "window") + ".json",
               { asked: state.answer, register_version: P.register.version, provenance: P.meta.provenance, generated_by: "iFabric dashboard evaluators.js" });
    }
    if (e.target.id === "dl-pack") download("evidence-pack-" + (P.meta.provenance || "pack").toLowerCase() + ".json", stripInternal(P));
    if (e.target.id === "dl-register") download("register-" + P.register.version + ".json", P.register);
    if (e.target.id === "rehearse") { state.rehearsalEnd = Date.now() + 120000; tick(); }
    if (e.target.id === "theme-btn") {
      var root = document.documentElement, cur = root.getAttribute("data-theme");
      var dark = cur ? cur === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.setAttribute("data-theme", dark ? "light" : "dark");
    }
  });
  function stripInternal(p) { var o = {}; Object.keys(p).forEach(function (k) { if (k.charAt(0) !== "_") o[k] = p[k]; }); return o; }
  window.addEventListener("hashchange", function () { render(); var m = document.getElementById("main"); if (m) m.focus({ preventScroll: true }); });
  setInterval(tick, 1000);

  if (window.EVIDENCE_PACK) load(window.EVIDENCE_PACK);
  else document.getElementById("view").innerHTML = '<div class="banner problem">No evidence pack found. Load one with "Load evidence pack", or generate data/evidence-pack.js with tools/pack_evidence.py.</div>';
})();

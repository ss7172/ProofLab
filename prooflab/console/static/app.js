window.addEventListener("error", e => document.body.setAttribute("data-error", String(e.message)));
let D = { answers: {}, auditor: {}, runs: {}, records: {}, cases: [] }, P = {}, META = {}, VOCAB = {};
const $ = id => document.getElementById(id);
function h(tag, attrs, ...kids) { const n = document.createElement(tag); for (const [k, v] of Object.entries(attrs || {})) { if (v == null || v === false) continue; if (k === "class") n.className = v; else if (k === "style") n.style.cssText = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v === true ? "" : v); } for (const c of kids.flat(9)) { if (c == null || c === false) continue; n.append(c instanceof Node ? c : document.createTextNode(String(c))); } return n; }
function s(tag, attrs, ...kids) { const n = document.createElementNS("http://www.w3.org/2000/svg", tag); for (const [k, v] of Object.entries(attrs || {})) if (v != null) { if (k === "style") n.style.cssText = v; else n.setAttribute(k, v); } for (const c of kids.flat(9)) { if (c == null) continue; n.append(c instanceof Node ? c : document.createTextNode(String(c))); } return n; }
const ap = r => (r && r.approval) || { status: "MISSING" }, apName = r => ((ap(r).approver || {}).name) || "not approved";
const nm = p => (p && p.name) || "unknown";
const fmt = n => n == null ? "—" : Number(n).toLocaleString("en-US");
const hms = iso => iso ? iso.slice(11, 19) + "Z" : "—";
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
let VL = {}, GLYPH = {};
const vtone = v => (VOCAB[v] || {}).tone || "mute";
function vpill(v) { const x = VOCAB[v] || {}; return h("span", { class: "pill p-" + (x.pill || "mute") }, (x.glyph || "") + " " + (x.label || v)); }
function spill(text, tone) { return h("span", { class: "pill p-" + tone }, text); }
const TONE = { DELIVERED: "good", RESPONDED: "good", WRITTEN: "good", present: "good", ALIGNED: "good", PASS: "good", VALIDATED: "good", DEFENDED: "good", ANSWERED: "good", ALLOW: "good", VERIFIED: "good", BUILT: "good", BUILT_WAITING: "good", EVIDENCED: "good", CLOSED_BY_RETEST: "good", OK: "good",
  NO_RESPONSE_OBSERVED: "warn", AWAITING_RESPONSE: "warn", PARTIAL: "warn", DETECTED: "trace", ALERT: "warn", UNKNOWN: "hatch", NOT_APPLICABLE: "mute", PLANNED: "mute", OPEN: "warn", pending: "warn",
  REFUSED: "bad", BLOCKED: "bad", FAILED: "bad", VIOLATION: "bad", FAIL: "bad", DENY: "bad", BROKE_OPEN: "bad", BROKE_FIXED: "warn", NOT_BUILT: "mute", GAP: "bad", MODIFIED: "bad" };
const tp = t => spill(String(t).replace(/_/g, " "), TONE[t] || "mute");
function ticks(list) { return h("span", { title: "Tickmarks: R recomputed · A agreed to source · T traced · V vouched" }, ["R", "A", "T", "V"].map(k => h("span", { class: "tick" + ((list || []).includes(k) ? "" : " off") }, k))); }
function idc(id) { return h("span", { class: "idc", "data-thread": id, onmouseenter: () => thread(id, true), onmouseleave: () => thread(id, false) }, id); }
function thread(id, on) { document.querySelectorAll(".idc").forEach(n => n.classList.toggle("lit", on && n.dataset.thread === id)); }
// PR-51b: every displayed fact says where it comes from (recorded / witnessed-by / joined-from / not-recorded), from the server
function srcTag(t) { return t ? h("span", { class: "srctag", title: "where this fact comes from" }, t) : null; }
const SURF = { spans: "gateway span", "gateway-stdout": "gateway stdout", adapter: "agent adapter record", orchestrator: "orchestrator record", "agentcore-metrics": "AgentCore metric" };
const isProj = r => /^projected/.test(((r || {}).facts || {}).measured_basis || "");
const mval = r => isProj(r) ? fmt(r["measured.value"]) + " projected (committed + bound)" : fmt(r["measured.value"]);
function refEl(r) { return h("span", { class: "ref", tabindex: 0, role: "button", onclick: () => inspect(r), onkeydown: e => e.key === "Enter" && inspect(r) }, r); }
function card(title, ...kids) { return h("section", { class: "card" }, title ? h("h3", {}, title) : null, ...kids); }
function kv(pairs) { return h("dl", { class: "kv" }, pairs.filter(p => p[1] != null && p[1] !== "").map(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])); }

/* ---------------- record inspector (stranger test) ---------------- */
function findRecord(ref) { const id = ref.startsWith("record:") ? ref.slice(7) : ref; for (const rs of Object.values(D.records)) { const r = rs.find(x => x.evidence_id === id || (x.facts || {}).record_id === id); if (r) return r; } return null; }
async function sha256(text) { const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)); return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join(""); }
function rawHolder(ref) { const box = h("div", {}, h("p", { class: "muted" }, "loading the raw line…")); api("/api/v1/raw?ref=" + encodeURIComponent(ref)).then(j => box.replaceChildren(rawLine(j.data.line))).catch(() => box.replaceChildren(h("p", { class: "v-breach" }, "unresolved: not listed in the pack"))); return box; }
function rawLine(line) { const pre = h("pre", { class: "raw" }); String(line).split(/(\[REDACTED:[^\]]+\])/).forEach(p => pre.append(/^\[REDACTED/.test(p) ? h("span", { class: "redact" }, p) : document.createTextNode(p))); return pre; }
async function inspect(ref) {
  if (/^servicenow:INC\d+$/.test(ref)) { location.hash = "#/loop/" + ref.slice(11); return; }
  const rec = findRecord(ref), body = $("drBody"); const rr = rec ? await api("/api/v1/raw?ref=" + encodeURIComponent(rec.source.raw_ref)).catch(() => null) : null; body.replaceChildren(); $("drTitle").textContent = rec ? rec["call.id"] || rec.evidence_id : ref;
  if (!rec) { const got = /^(record|raw):/.test(ref) ? await api("/api/v1/raw?ref=" + encodeURIComponent(ref)).catch(() => null) : null;
    body.append(h("p", { class: "dim" }, "Reference "), h("pre", { class: "raw" }, ref), got && got.data ? h("div", {}, h("div", { class: "label" }, "Line as captured" + (got.data.path ? " (" + got.data.path + (got.data.line_no ? " line " + got.data.line_no : "") + ")" : "")), rawLine(got.data.line), kv([["sha256", h("span", { class: "mono" }, got.data.sha256)]])) : h("p", { class: "v-breach" }, "unresolved: not listed in the pack (shown red, never hidden)")); return openDrawer(); }
  const raw = rr && rr.data ? rr.data.line : null, cap = (rr && rr.data && rr.data.capture) || {}, out = h("span", { class: "mono muted" }, "not yet recomputed");
  body.append(
    h("div", { class: "label" }, "Bound evidence record · ifabric.evidence/v1"),
    kv([["run.id", h("span", { class: "mono" }, rec["run.id"])], ["call.id", rec["call.id"] || "—"], ["control.id", rec["control.id"] + " (" + rec["control.ref"] + ")"], ["threshold.version", rec["threshold.version"]], ["threshold.value", h("span", { class: "mono" }, fmt(rec["threshold.value"]))], ["measured.value", h("span", { class: "mono" }, fmt(rec["measured.value"]) + " " + rec["measured.unit"] + (rec["measured.call"] != null ? "  (this call " + fmt(rec["measured.call"]) + ")" : ""))], ["verdict", vpill(rec.verdict)], ["decision", rec.decision ? tp(rec.decision) : "—"], ["actor.id", rec["actor.id"]], ["emitted.at", h("span", { class: "mono" }, rec["emitted.at"] + " · " + rec.source.clock + " clock")], ["seal", h("span", { class: "muted" }, "out of scope (per the brief)")]]),
    h("div", { class: "label" }, "Raw line as captured (redacted at capture)"), raw == null ? h("p", { class: "v-breach" }, "unresolved: the raw ref is not listed in the pack") : rawLine(raw),
    kv([["raw_ref", h("span", { class: "mono" }, rec.source.raw_ref)], ["sha256", h("span", { class: "mono" }, rec.source.sha256)], ["recompute", h("span", {}, h("button", { class: "chip btn", onclick: async () => { const got = await sha256(raw == null ? "" : raw); out.textContent = got === rec.source.sha256 ? "✓ matches — computed in your browser" : "✗ differs: " + got; out.style.color = got === rec.source.sha256 ? css("--held") : css("--breach"); } }, "Verify without us"), " ", out)], ["MANIFEST", h("span", { class: "pill p-" + (rr && rr.data ? "good" : "bad") }, rr && rr.data ? "listed in pack-index" : "unresolved")]]),
    h("div", { class: "label" }, "Capture sidecar (re-run this to get the same bytes)"),
    kv([["command", h("span", { class: "mono" }, cap.command || "—")], ["captured", cap.captured_at], ["scope", cap.scope ? cap.scope.cid : "—"], ["pagination", cap.pagination_complete ? "complete" : "?"], ["redactions", (cap.redactions || []).map(r => r.rule + " ×" + r.count).join(", ")]]),
    h("div", { class: "label" }, "Corroboration — where they disagree, the gateway wins"),
    h("div", {}, (rec.source.corroborated_by || []).length ? rec.source.corroborated_by.map(c => h("div", { class: "mono dim", style: "font-size:11.5px" }, "✓ " + c)) : h("span", { class: "muted" }, "single surface")),
    h("div", { class: "label" }, "Joins"), kv(Object.entries(rec.joins || {}).filter(([, v]) => v).map(([k, v]) => [k, idc(v)])));
  openDrawer();
}
function openDrawer() { $("drawer").classList.add("open"); $("drClose").focus(); }
$("drClose").onclick = () => $("drawer").classList.remove("open");

/* ---------------- charts ---------------- */
function bullet(a) {
  const W = 880, H = 70, cap = a.comparison.limit, val = a.measurement.value, max = Math.max(cap, val) * 1.08, x = v => 10 + (W - 20) * v / max, over = val > cap;
  return h("div", { class: "svgwrap" }, s("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", role: "img", "aria-label": `${fmt(val)} tokens against a cap of ${fmt(cap)}` },
    s("rect", { x: 10, y: 22, width: W - 20, height: 20, fill: css("--stack"), rx: 3 }),
    s("rect", { x: 10, y: 22, width: x(Math.min(val, cap)) - 10, height: 20, fill: over ? css("--ink-3") : css("--held"), rx: 3, opacity: over ? .55 : .85 }),
    over ? s("rect", { x: x(cap), y: 22, width: x(val) - x(cap), height: 20, fill: css("--breach") }) : null,
    s("line", { x1: x(cap), x2: x(cap), y1: 12, y2: 52, stroke: css("--ink"), "stroke-width": 2 }),
    s("text", { x: x(cap), y: 9, "text-anchor": "middle", fill: css("--ink-2"), "font-size": 11 }, "cap ≤ " + fmt(cap)),
    s("text", { x: x(val), y: 64, "text-anchor": over ? "end" : "middle", fill: over ? css("--breach") : css("--held"), "font-size": 12, "font-weight": 600 }, fmt(val) + (over ? "  (+" + fmt(val - cap) + ")" : "  (margin " + fmt(cap - val) + ")"))));
}
function bars(series, unit, limitLabel) {
  const W = 880, H = 190, n = series.length, vals = series.map(x => x.value || 0), lim = series[0].limit, max = Math.max(lim, ...vals) * 1.15, bw = (W - 60) / n;
  const y = v => 150 - 125 * v / max, g = s("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", role: "img", "aria-label": "Observations against the limit" });
  g.append(s("line", { x1: 40, x2: W - 10, y1: y(lim), y2: y(lim), stroke: css("--breach"), "stroke-dasharray": "5 4", "stroke-width": 1.5 }), s("text", { x: W - 10, y: y(lim) - 6, "text-anchor": "end", fill: css("--breach"), "font-size": 11 }, limitLabel));
  series.forEach((it, i) => { const x0 = 44 + i * bw, bad = it.status === "VIOLATES", unk = it.value == null;
    if (unk) { g.append(s("rect", { x: x0 + bw * .18, y: 112, width: bw * .64, height: 38, fill: "url(#hatch)", stroke: css("--unknown"), "stroke-dasharray": "3 3" }), s("text", { x: x0 + bw / 2, y: 106, "text-anchor": "middle", fill: css("--unknown"), "font-size": 11 }, "?")); }
    else { g.append(s("rect", { x: x0 + bw * .18, y: y(it.value), width: bw * .64, height: 150 - y(it.value), fill: bad ? css("--breach") : css("--ink-3"), opacity: bad ? 1 : .55, rx: 2 }), s("text", { x: x0 + bw / 2, y: y(it.value) - 5, "text-anchor": "middle", fill: bad ? css("--breach") : css("--ink-2"), "font-size": 10.5, "font-weight": bad ? 600 : 400 }, unit === "ms" ? fmt(it.value) : (it.value > 0 ? "+" : "") + it.value + "%")); }
    g.append(s("text", { x: x0 + bw / 2, y: 168, "text-anchor": "middle", fill: css("--ink-3"), "font-size": 10.5 }, it.id), s("title", {}, (it.label || it.id) + ": " + (unk ? it.status : it.value + " " + unit))); });
  g.prepend(s("defs", {}, s("pattern", { id: "hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, s("rect", { width: 2.5, height: 6, fill: css("--unknown"), opacity: .5 }))));
  return h("div", { class: "svgwrap" }, g);
}
/* ---------------- views ---------------- */
function ribbon(compact) {
  const r = P.register, pts = [r.first_exploratory_at ? ["exploratory runs (excluded)", r.first_exploratory_at, "--ink-4"] : null, ["register frozen", r.frozen_at, "--trace"], ap(r).at ? ["owner approved (" + String((ap(r).ref || ":").split(":")[1]) + ")", ap(r).at, "--held"] : null, ["first assessed run", r.first_assessed_run_at, "--ink"], (P.named_runs || {}).written_at ? ["named runs written", P.named_runs.written_at, "--ink-2"] : null, P.pack.judging_starts_at ? ["judging", P.pack.judging_starts_at, "--unknown"] : null].filter(p => p && p[1]);
  if (!pts.length) return h("p", { class: "muted" }, "no dated register events in this pack");
  const t0 = Date.parse(pts[0][1]), t1 = Date.parse(pts[pts.length - 1][1]), W = 860, x = t => 30 + (W - 60) * Math.sqrt((Date.parse(t) - t0) / (t1 - t0)), g = s("svg", { viewBox: `0 0 ${W} 86`, width: "100%", role: "img", "aria-label": "Register freeze and approval precede every assessed run" });
  g.append(s("line", { x1: 30, x2: W - 30, y1: 34, y2: 34, stroke: css("--rule-strong"), "stroke-width": 2 }));
  pts.forEach(([l, t, c], i) => g.append(s("circle", { cx: x(t), cy: 34, r: 6, fill: css(c) }), s("text", { x: x(t), y: i % 2 ? 62 : 18, "text-anchor": "middle", fill: css("--ink-2"), "font-size": 10.5 }, l), s("text", { x: x(t), y: i % 2 ? 76 : 4, "text-anchor": "middle", fill: css("--ink-3"), "font-size": 9.5 }, t.slice(5, 16).replace("T", " ") + "Z")));
  return h("div", {}, h("div", { class: "svgwrap" }, g), h("p", { class: "dim", style: "margin:4px 0 0;font-size:12px" }, (!ap(r).at ? "✗ no owner approval record in the pack (MISSING): the order frozen, approved, first assessed run cannot be shown" : Date.parse(r.frozen_at) < Date.parse(ap(r).at) && Date.parse(ap(r).at) < Date.parse(r.first_assessed_run_at) ? "✓ frozen, then approved, then the first assessed run" : "✗ the order frozen, approved, first assessed run does NOT hold") + " · same threshold version for the named runs is shown on each answer"));
}
function answerView(key) {
  const a = D.answers[key || firstKey()]; if (!a) return h("div", { class: "page" }, card("No such answer", "Try ⌘K."));
  const isC16 = a.control.ref === "C16", ser = a.measurement.series, r = a.rule || {}, aq = a.audit_question || {}, pop = a.population || {}, enf = a.enforcement || {}, aict = a.aict || {}, ol = r.observation_limit || {}, et = r.exception_tolerance || {};
  const group = (title, keys) => h("section", {}, h("div", { class: "label", style: "margin-bottom:6px" }, title), keys.map(([k, label]) => { const q = aq[k] || { text: "not stated (gap)", flag: "FLAG" }; return h("div", { class: "q" + (q.flag === "FLAG" || q.flag === "GAP" ? " flag" : "") }, h("span", { class: "label" }, label), q.text, " ", (q.refs || []).slice(0, 2).map(r => [refEl(r), " "]), srcTag(q.source)); }));
  const loops = a.human_loops || [];
  return h("div", { class: "page" },
    h("div", { class: "row", style: "justify-content:space-between" }, h("div", {}, h("div", { class: "mono dim" }, "› " + a.query.text), h("div", { class: "mono muted", style: "font-size:11.5px" }, "parsed → " + a.query.normalized + " · answered in " + a.elapsed_ms + " ms from " + a.source.records_scanned + " records · PACK · MANIFEST " + a.source.manifest_status)),
      h("div", { class: "row" }, h("span", { class: "chip" }, a.control.ref + " · " + a.control.id), h("span", { class: "chip" }, a.control.mode), h("span", { class: "chip mono" }, "answer_id " + a.answer_id.slice(0, 10) + "…"))),
    h("section", { class: "card" }, h("div", { class: "verdict" }, h("span", { class: "vword v-" + vtone(a.verdict.value) }, (GLYPH[a.verdict.value] || "") + " " + a.verdict.label), h("span", { style: "font-size:15px" }, a.verdict.reason), h("span", { style: "margin-left:auto" }, ticks(["R", "A", "T", "V"]))),
      h("div", { class: "row muted", style: "margin:6px 0 12px;font-size:12px" }, "Rule " + r.threshold_version + " (" + r.register_version + ") · dated " + r.version_date + " · frozen " + hms(r.frozen_at) + " · ", ap(r).status === "MISSING" ? spill("approval MISSING", "bad") : "approved by " + apName(r) + " " + hms(ap(r).at), " ", r.date_before_scope ? spill("✓ dated before the scope", "good") : spill("RULE DATED AFTER TEST", "bad"), " · owner " + nm(r.owner) + " · evidence " + a.verdict.evidence_sufficiency),
      isC16 && a.comparison && a.comparison.limit != null && a.measurement.value != null ? bullet(a) : ser && ser.length ? bars(ser, a.measurement.unit || "", "limit " + (ol.operator || "") + " " + fmt(ol.value)) : h("p", { class: "mono", style: "font-size:13px" }, "measured " + fmt(a.measurement.value) + " " + (a.measurement.unit || "") + " · limit " + (ol.operator || "") + " " + fmt(ol.value) + " " + (ol.unit || "")),
      h("div", { class: "row", style: "margin-top:10px;gap:20px;font-size:12px" }, h("span", {}, h("span", { class: "label" }, "Observation limit "), (ol.operator || "") + " " + fmt(ol.value) + " " + (ol.unit || "")), h("span", {}, h("span", { class: "label" }, "Exception tolerance "), (et.operator || "") + " " + fmt(et.value) + " " + (et.unit || "")), (a.comparison || {}).exception_fraction != null ? h("span", {}, h("span", { class: "label" }, "Observed exceptions "), a.comparison.exceptions_count + " = " + a.comparison.exception_fraction + "%") : null)),
    h("div", { class: "pop" }, [["expected", (pop.expected || {}).count], ["observed", pop.observed], ["matched", pop.matched], ["missing", pop.missing], ["dupes removed", pop.duplicates_removed], ["blocked", pop.blocked], ["unmeasurable", pop.unmeasurable]].map(([k, v]) => h("div", {}, h("span", { class: "label" }, k), h("b", { class: (k === "missing" || k === "unmeasurable") && v ? "v-unknown" : "" }, fmt(v))))), (pop.missing_events || []).length ? h("div", { class: "mono v-unknown", style: "font-size:11.5px;margin-top:6px" }, "expected but not captured: " + pop.missing_events.join(", ")) : null,
    h("div", { class: "aq" }, group("The action", [["what_was_done", "What was done"], ["by_which_agent", "By which agent"], ["where", "Where"], ["when", "When"]]), group("The decision", [["under_whose_authority", "Under whose authority"], ["rule_checked", "Which rule"], ["limit_in_force", "Limit in force at that moment"], ["decision", "Allowed, stopped or escalated"]]), group("The proof", [["who_was_told", "Who was told"], ["unchanged_since", "Unchanged since?"]])),
    h("div", { class: "grid2" },
      card("Control test (tester) — judges the control", kv([["tester", h("span", { class: "mono" }, (enf.tester || {}).name + " @ " + (enf.tester || {}).version)], ["formula", h("span", { class: "mono" }, a.measurement.formula)], ["mode", tp(enf.mode || "UNKNOWN")], ["exceptions", (a.exceptions || []).length ? a.exceptions.map(e => h("div", { class: "mono", style: "font-size:11.5px" }, "▲ " + (e.why || e.note || e.key || e.kind || JSON.stringify(e)))) : "none"], ["threshold source", h("span", { class: "mono" }, r.source_ref)]])),
      card("Inline decisions (evaluator) — judges each call, in the path", enf.inline_decisions && enf.inline_decisions.length ? h("div", {}, h("div", { class: "row", style: "gap:4px;margin-bottom:8px" }, enf.inline_decisions.map(d => h("span", { class: "pill " + (d.decision === "ALLOW" ? "p-good" : d.decision === "ALERT" ? "p-warn" : "p-bad"), title: d.call_id + ": committed " + fmt(d.committed) + " + reserved " + fmt(d.reserved) }, d.call_id.slice(2)))),
        enf.inline_decisions.filter(d => d.decision !== "ALLOW").map(d => h("div", { class: "mono", style: "font-size:12px" }, d.decision + " before " + d.call_id + ": " + (d.committed == null ? "numbers not recorded" : "committed " + fmt(d.committed) + (d.reserved ? " + reserved " + fmt(d.reserved) : "") + " + bound " + fmt(d.bound) + " = " + fmt(d.projected) + " > cap " + fmt(d.limit)), " ", srcTag(d.source ? "recorded (detail, inline.limit_value)" : "not-recorded"))), h("p", { class: "muted", style: "font-size:11.5px;margin:6px 0 0" }, "Reserve, then commit — two calls cannot both read 9,800 under 10,000 and pass.")) : h("p", { class: "muted" }, "POST-RUN control: no inline evaluator for this control (stated honestly)."))),
    h("div", { class: "split" },
      card("Records behind the number (" + (a.records || []).length + ")", h("table", { class: "t" }, h("tbody", {}, (a.records || []).map(rc => h("tr", { class: "click", onclick: () => inspect(rc.ref) }, h("td", {}, ticks(rc.tickmarks)), h("td", { class: "mono", style: "font-size:11.5px" }, rc.summary || rc.ref), h("td", {}, rc.manifest === "OK" ? h("span", { class: "pill p-good" }, "MANIFEST ✓") : h("span", { class: "pill p-bad" }, "MANIFEST " + (rc.manifest || "?")))))))),
      h("div", { style: "display:flex;flex-direction:column;gap:14px" },
        card("Who was told — human loop (" + loops.length + ")", loops.length ? loops.map(l => h("div", { class: "ep" }, h("a", { href: "#/loop/" + l.incident, title: "Open the ServiceNow case" }, idc(l.incident)), h("div", {}, h("div", { class: "row", style: "gap:5px" }, tp((l.delivery || {}).state || "UNKNOWN"), tp((l.response || {}).state || "UNKNOWN"), spill("Nemotron " + String((l.assurance_agent || {}).state || "unknown").toLowerCase(), TONE[(l.assurance_agent || {}).state] || "trace"), tp((l.closure || {}).state || "UNKNOWN"), (l.closure || {}).flag ? spill(l.closure.flag, "bad") : null), h("div", { class: "muted", style: "font-size:11.5px;margin-top:3px" }, "owner " + nm(l.owner) + " · delivered " + hms((l.delivery || {}).at) + " · cutoff " + hms((l.response || {}).cutoff) + ((l.closure || {}).retest_ref ? " · closed by " + l.closure.retest_ref.split("/").pop() : ""))))) : h("p", { class: "muted" }, "Nothing needed telling. Evidence is in the pack.")),
        card("AI Control Tower", kv([["status", aict.status], ["connection", aict.connection], ["discovered", (aict.assets || []).join(", ") || "not in this pack"], ["last import", aict.last_import_at], ["monitor", h("span", { style: "color:var(--unknown)" }, "no AWS sessions (gap A3)")], ["proof", h("span", {}, (aict.refs || []).slice(0, 3).map(r => [refEl(r), " "]))]])),
        card("Gaps for this scope", (a.gaps || []).length ? a.gaps.map(gp => h("div", { class: "dim" }, h("b", { class: "mono" }, gp.id + " "), gp.text)) : h("span", { class: "muted" }, "none")))));
}
function ledger(alias) {
  const run = alias || ((P.runs || [])[0] || {}).alias, recs = D.records[run] || [], c16 = recs.filter(r => r["control.ref"] === "C16"), mc = c16.filter(r => r.record_kind === "model-call" && r["call.id"]), gw = mc.filter(r => (r.source || {}).surface === "spans"), sample = gw[gw.length - 1] || mc[mc.length - 1] || c16[c16.length - 1];
  if (!sample) return h("div", { class: "page" }, card("No records", "No C16 records for run " + run + " in this pack."));
  return h("div", { class: "page" }, h("div", { class: "row", style: "justify-content:space-between" }, h("div", {}, h("div", { class: "label" }, "Evidence Ledger · bound records (ifabric.evidence/v1)"), h("h1", { class: "h1" }, "A log is for an engineer. Evidence is for a stranger.")), h("div", { class: "row" }, (P.runs || []).map(r => r.alias).map(a => h("a", { class: "chip btn" + (a === run ? " trace" : ""), href: "#/ledger/" + a }, a)))),
    h("div", { class: "grid2" }, card("LOG — as captured (" + (SURF[(sample.source || {}).surface] || (sample.source || {}).surface || "source not recorded") + ", call " + (sample["call.id"] || "not recorded") + ")", rawHolder(sample.source.raw_ref), h("p", { class: "muted", style: "font-size:11.5px" }, "Written for an engineer next week. It shows something happened, not that it was allowed.")),
      card("EVIDENCE — the same call, bound", kv(["run.id", "call.id", "control.id", "threshold.version", "threshold.value", "measured.value", "verdict", "actor.id", "emitted.at"].map(k => [k, h("span", { class: "mono" }, k === "verdict" ? VL[sample[k]] : k === "measured.value" ? mval(sample) : typeof sample[k] === "number" ? fmt(sample[k]) : sample[k] == null ? "not recorded" : sample[k])]).concat([["measured basis", h("span", { class: "muted" }, (sample.facts || {}).measured_basis || "not recorded")]]).concat([["seal", h("span", { class: "muted" }, "out of scope")], ["verify", h("button", { class: "chip btn", onclick: () => inspect("record:" + sample.evidence_id) }, "Open in inspector · recompute sha256")]])))),
    card(recs.length + " records for " + run, h("table", { class: "t" }, h("thead", {}, h("tr", {}, ["", "run.id", "call/event", "control", "version", "measured.value", "verdict", "decision", "actor.id", "emitted.at"].map(x => h("th", {}, x)))),
      h("tbody", {}, recs.map(r => h("tr", { class: "click", onclick: () => inspect("record:" + r.evidence_id) }, h("td", {}, ticks(r.record_kind === "model-call" ? ["R", "A", "T"] : ["R", "A"])), h("td", { class: "mono" }, r["run.id"]), h("td", { class: "mono" }, r["call.id"] || r.facts.expected_event), h("td", { class: "mono" }, r["control.ref"]), h("td", { class: "mono" }, r["threshold.version"]), h("td", { class: "mono" }, mval(r)), h("td", {}, r.verdict === "NOT_ASSESSED" ? h("span", { class: "muted", title: "a record is not a verdict; the control test's verdict is in the answer" }, "record") : vpill(r.verdict)), h("td", {}, r.decision ? tp(r.decision) : ""), h("td", { class: "mono", style: "font-size:11.5px" }, r["actor.id"]), h("td", { class: "mono", style: "font-size:11.5px" }, hms(r["emitted.at"]))))))));
}
function auditor(id) {
  const a = D.auditor[id || ((P.auditor || [])[0] || {}).id];
  if (!a) return h("div", { class: "page" }, card(id ? "No auditor view for " + id : "No auditor views stored", h("p", { class: "muted" }, id ? "This pack holds no six-questions view for that id. Stored views: " + (Object.keys(D.auditor).join(", ") || "none") + "." : "pack-index auditor[] is empty. From the unzipped pack: python3 -m prooflab query --incident <CID>")));
  const picker = h("div", { class: "row" }, Object.keys(D.auditor).map(k => h("a", { class: "chip btn" + (k === a.scope.id ? " trace" : ""), href: "#/auditor/" + k }, k)));
  const qn = [["who", "1 WHO acted"], ["what", "2 WHAT it touched"], ["authorized", "3 AUTHORIZED"], ["approved", "4 APPROVED"], ["integrity", "5 INTEGRITY"], ["reconstruct", "6 RECONSTRUCT"]];
  return h("div", { class: "page" }, h("div", { class: "row", style: "justify-content:space-between" }, h("div", {}, h("div", { class: "label" }, "Six auditor questions · answered from the Evidence Pack alone"), h("h1", { class: "h1" }, a.title), h("p", { class: "sub mono" }, "window " + (a.window || {}).start + " → " + (a.window || {}).end)), picker),
    h("div", { class: "grid3" }, qn.map(([k, t]) => { const q = Object.assign({ status: "GAP", answer: "not answered in this view (gap)", facts: [], gaps: [] }, (a.questions || {})[k]); return h("section", { class: "card" }, h("div", { class: "row", style: "justify-content:space-between" }, h("b", {}, t), tp(q.status)), h("p", { style: "margin:6px 0 8px" }, q.answer), (q.facts || []).map(f => h("dl", { class: "fact" + (f.flag === "FLAG" ? " flag" : "") }, h("dt", {}, f.label), h("dd", {}, f.value, " ", (f.refs || []).slice(0, 1).map(refEl), srcTag(f.source)))), (q.gaps || []).length ? h("div", { class: "muted", style: "font-size:11.5px;margin-top:6px" }, "gap " + q.gaps.join(", ") + " — stated, not hidden") : null); })));
}
function register() {
  const r = P.register;
  const ctl = c => h("section", { class: "card" }, h("div", { class: "row", style: "justify-content:space-between" }, h("div", {}, h("div", { class: "label" }, c.id + (c.child_id ? " → child " + c.child_id : "") + " · " + c.mode), h("div", { style: "font-weight:600;font-size:15px" }, c.ref + " " + c.name)), h("span", { class: "chip mono" }, c.version + " · " + c.version_date)),
    h("p", { class: "dim" }, c.statement), kv([["metric", c.metric], ["observation limit", h("span", { class: "mono" }, (c.observation_limit || {}).operator + " " + fmt((c.observation_limit || {}).value) + " " + (c.observation_limit || {}).unit)], ["second number", h("span", { class: "mono" }, (c.exception_tolerance || {}).operator + " " + (c.exception_tolerance || {}).value + " " + (c.exception_tolerance || {}).unit)], ["measurement basis", c.measurement_basis], ["enforcement point", c.enforcement_point], ["owner", nm(c.owner)], ["risk", c.risk_rating ? c.risk_rating.inherent + " inherent → " + c.risk_rating.residual + " residual (" + c.risk_rating.basis + ")" : null]]),
    h("details", { style: "margin-top:8px" }, h("summary", { class: "label", style: "cursor:pointer" }, "Four justifications + GRC chain"), kv(Object.entries(c.justification || {}).map(([k, v]) => [k.replace(/_/g, " "), v]).concat(Object.entries(c.governance || {}).map(([k, v]) => [k.replace(/_/g, " "), v])))));
  return h("div", { class: "page" }, h("div", {}, h("div", { class: "label" }, "Threshold register " + r.version + " · sha256 " + String(r.sha256 || "").slice(0, 16) + "…"), h("h1", { class: "h1" }, "Its date is what makes it a test")),
    card("Date before test", ribbon()), h("div", { class: "grid3" }, [["Owner (approves)", r.owner], ["Builder (operations)", r.builder], ["Assurance (tests, explains)", r.assurance]].map(([t, p]) => card(t, h("b", {}, nm(p)), h("div", { class: "muted" }, (p || {}).role)))),
    card("Approval proof", ap(r).status === "MISSING" ? h("p", { class: "v-breach" }, "MISSING: the pack holds no owner approval record for this register (stated, not hidden).") : null, kv([["status", tp(ap(r).status)], ["requested", ap(r).requested_at], ["approved", ap(r).at ? ap(r).at + " by " + apName(r) : null], ["note", ap(r).note ? h("span", { class: "mono" }, ap(r).note) : null], ["record", ap(r).ref ? refEl(ap(r).ref) : null], ["exploratory runs", r.exploratory_runs + " (excluded from every verdict)"]])),
    h("div", { class: "grid3" }, (r.controls || []).map(ctl)));
}
function caseLinks(c) {
  const num = (c.servicenow || {}).number, ans = Object.entries(D.answers).find(([, a]) => (a.human_loops || []).some(l => l.incident === num));
  return h("div", { class: "row", style: "gap:8px;margin:16px 0 6px;font-size:12px" }, idc(num), idc(c.finding_id),
    ans ? h("a", { class: "chip btn", href: "#/answer/" + encodeURIComponent(ans[0]) }, "Answer →") : null,
    D.auditor[num] ? h("a", { class: "chip btn", href: "#/auditor/" + num }, "Six questions →") : null);
}
function loop(arg) {
  const all = D.cases, pick = arg ? all.filter(c => c.finding_id === arg || (c.servicenow || {}).number === arg) : [];
  const shown = pick.length ? pick : all;
  const box = h("div", { "data-ifab-theme": document.documentElement.dataset.theme === "paper" ? "light" : "dark" });
  const page = h("div", { class: "page" },
    h("div", {}, h("div", { class: "label" }, "G · Human loop · ServiceNow · embedded Assurance Agent panel (prooflab v3)"), h("h1", { class: "h1" }, "Every breach reached a named human, and Nemotron's analysis is checked"),
      h("p", { class: "sub" }, "The drop-in panel, rendered from the case snapshots listed in pack-index cases[]. The console never calls ServiceNow."),
      pick.length ? h("a", { class: "chip btn", href: "#/loop" }, "← all " + all.length + " cases") : null),
    card(null, box));
  const fl = P.findings || [];
  const findingsCard = card("Findings staged in this pack (" + fl.length + ") · delivery from servicenow/delivery-log.jsonl", fl.length ? h("table", { class: "t" }, h("thead", {}, h("tr", {}, ["Control", "Scope", "Verdict", "Delivery", "Incident", "Summary"].map(x => h("th", {}, x)))),
    h("tbody", {}, fl.map(f => h("tr", {}, h("td", { class: "mono" }, f.control_ref), h("td", { class: "mono" }, f.scope_id), h("td", {}, vpill(f.verdict)), h("td", {}, f.delivery_state || "not recorded"), h("td", { class: "mono" }, f.incident || "—"), h("td", {}, f.summary || ""))))) : h("p", { class: "muted" }, "No findings staged in this pack."));
  if (!window.IFabricCasePanel || !all.length) { box.append(h("p", { class: "muted" }, "No ServiceNow case snapshots are listed in this pack (pack-index cases[]). The panel needs a snapshot written by the loop (servicenow/cases/*.json); none was supplied, so none is shown. The findings below are listed from the pack itself.")); page.append(findingsCard); return page; }
  window.IFabricCasePanel.render(box, shown); page.append(findingsCard);
  box.querySelectorAll(":scope > .ifab-card").forEach((el, i) => {
    const c = shown[i]; if (!c) return;
    el.before(caseLinks(c));
    el.querySelectorAll(".ifab-id").forEach(n => { n.classList.add("idc"); n.dataset.thread = c.finding_id; n.onmouseenter = () => thread(c.finding_id, true); n.onmouseleave = () => thread(c.finding_id, false); });
  });
  return page;
}
function gaps() {
  return h("div", { class: "page" }, h("div", {}, h("div", { class: "label" }, "Gap list · Artefact 6 · scored, and it scores well"), h("h1", { class: "h1" }, "“Built properly: yes. Actually worked: no.”"), h("p", { class: "sub" }, "One honest failure scores better than everything green. Every gap names what, why, what it affects, its impact, and what we would do next.")),
    h("div", { class: "grid2" }, (P.gaps || []).length ? P.gaps.map(g => card(h("span", {}, h("span", { class: "mono", style: "color:var(--unknown)" }, g.gap_id), " " + g.title), kv([["what", g.what], ["why", g.why], ["affects", [((g.affects || {}).controls || []).join(", "), ((g.affects || {}).levels || []).join(", "), ((g.affects || {}).auditor_questions || []).join(", ")].filter(Boolean).join(" · ") || "—"], ["impact", g.impact], ["next", g.next], ["status", tp(g.status || "OPEN")], ["source", g.source ? h("span", { class: "mono" }, g.source) : null]]))) : card("No gaps listed", h("p", { class: "muted" }, "pack-index gaps[] is empty; read gap-list.md in the pack."))));
}
function architecture() {
  return h("div", { class: "page" }, h("div", {}, h("div", { class: "label" }, "Enforcement points · from pack-index"), h("h1", { class: "h1" }, "What can refuse, and what only watches")),
    card("Enforcement points — status rendered exactly as recorded in the pack", h("table", { class: "t" }, h("thead", {}, h("tr", {}, ["EP", "Kind", "Transport", "Can refuse", "Status", "Changed adapter", "Unchanged core"].map(x => h("th", {}, x)))), h("tbody", {}, (P.enforcement_points || []).map(e => h("tr", {}, h("td", {}, h("b", { class: "mono" }, e.id), h("div", { class: "muted", style: "font-size:11.5px" }, e.name)), h("td", { class: "mono" }, e.kind), h("td", { class: "mono" }, e.transport + "()"), h("td", {}, e.can_refuse ? "yes" : "no"), h("td", {}, tp(e.status)), h("td", { class: "mono", style: "font-size:11.5px" }, e.changed_adapter || "—"), h("td", { class: "mono", style: "font-size:11.5px" }, (e.unchanged_core || []).join(", ") || "—")))))));
}
function runsView() {
  const rows = D.runList || [];
  return h("div", { class: "page" }, h("div", {}, h("div", { class: "label" }, "Run catalogue · every run any source saw"), h("h1", { class: "h1" }, "Runs, with what each one is"), h("p", { class: "sub" }, "Runs outside the declared window or not assessed stay listed and are labelled; they never change a verdict."), h("p", { class: "sub mono" }, D.runWindow ? "Declared window: " + (D.runWindow.start || "?") + " .. " + (D.runWindow.end || "?") + (D.runWindow.note ? " (" + D.runWindow.note + ")" : "") : "Declared window: none in this source")),
    card(rows.length + " runs", h("table", { class: "t" }, h("thead", {}, h("tr", {}, ["Alias", "Run id", "Provenance", "Source", "Window", "Assessed", "Label"].map(x => h("th", {}, x)))),
      h("tbody", {}, rows.map(r => h("tr", { class: r.provenance && r.provenance !== "ASSESSED" ? "dim" : "" }, h("td", { class: "mono" }, r.alias || "—"), h("td", { class: "mono" }, r.cid || r.run_id || "—"), h("td", {}, tp(r.provenance || "UNKNOWN")), h("td", {}, r.source || "—"), h("td", {}, r.in_window == null ? "unknown" : r.in_window ? "inside" : "outside"), h("td", {}, r.assessed == null ? "unknown" : r.assessed ? "yes" : "no"), h("td", {}, r.label || r.purpose || "")))))));
}

/* ---------------- boot: the data comes from the console API, never embedded ---------------- */
async function api(path, tries = 4) { const r = await fetch(path, { credentials: "same-origin" });
  if (r.status === 429 && tries > 0) { await new Promise(ok => setTimeout(ok, 1100)); return api(path, tries - 1); }   // the console's per-second limit: wait, then retry
  const j = await r.json(); if (!r.ok || !j.ok) throw new Error((j.error && j.error.message) || r.status); return j; }
const ROUTES = [["B", "answer", "Ask · Answer"], ["D", "ledger", "Evidence Ledger"], ["E", "auditor", "Six Questions"], ["F", "register", "Register"], ["G", "loop", "Human Loop"], ["I", "architecture", "Enforcement points"], ["J", "gaps", "Gaps"], ["R", "runs", "Runs"]];
const VIEWS = Object.assign({ answer: answerView, ledger, auditor, register, loop, architecture, enforcement: architecture, gaps, runs: runsView }, window.PROOFLAB_P1_VIEWS || {});
function rail(active) {
  const counts = { gaps: (P.gaps || []).length, loop: D.cases.length, runs: (D.runList || []).length, auditor: (P.auditor || []).length, answer: (P.answers || []).length };
  const lvl = (P.levels || []).map(l => h("span", { class: "pill " + (l.status === "VERIFIED" ? "p-good" : "p-warn"), title: l.level }, l.level.slice(0, 2)));
  $("rail").replaceChildren(h("div", { class: "label grp" }, "Exhibit index"), ...ROUTES.concat(window.PROOFLAB_P1_ROUTES || []).map(([l, r, n]) => h("a", { href: "#/" + r, class: active === r ? "on" : "" }, h("span", { class: "ltr" }, l), n, h("span", { class: "cnt" }, counts[r] ?? ""))),
    h("div", { class: "railnote" }, h("div", { class: "label" }, "Judging levels"), h("div", { class: "lv" }, lvl), "This console sees everything and can refuse nothing."));
}
function go(ref) { if (!ref) return; if (ref.startsWith("#")) { location.hash = ref; return; } if (ref.startsWith("answer:")) location.hash = "#/answer/" + encodeURIComponent(ref.slice(7)); else inspect(ref); }
function route() { const [, v = "answer", arg] = location.hash.split("/"); const view = VIEWS[v] ? v : "answer"; rail(view === "enforcement" ? "architecture" : view);
  let page;
  try { page = VIEWS[view](arg ? decodeURIComponent(arg || "") : undefined); }
  catch (e) { page = h("div", { class: "page" }, card("This view could not render", h("p", { class: "v-breach" }, String(e && e.message || e)), h("p", { class: "muted" }, "view " + view + (arg ? " · " + arg : "") + " · the other views still work; the data is unchanged."))); }
  const a0 = view === "answer" ? D.answers[arg ? decodeURIComponent(arg) : firstKey()] : null;
  if (a0 && a0.source && ["UNVERIFIED", "MODIFIED"].includes(a0.source.manifest_status)) page.prepend(h("div", { class: "ribbon bad" }, a0.source.manifest_status + ": this pack no longer matches its MANIFEST"));
  $("main").replaceChildren(page); $("main").scrollTop = 0; }
const firstKey = () => ((P.answers || [])[0] || {}).key;
const SUGG = () => (P.answers || []).map(a => [/\|run\|/.test(a.key) ? "Show me control " + a.control_ref.slice(1) + " for run " + a.scope : "Control " + a.control_ref.slice(1) + " over " + a.scope, "#/answer/" + encodeURIComponent(a.key)])
  .concat((P.auditor || []).map(a => ["Six questions for " + a.id, "#/auditor/" + a.id]));
let sel = 0, lastAsk = null, askTimer = null;
function renderPalette() { const q = $("pIn").value, a = lastAsk && lastAsk.q === q ? lastAsk : null; $("pParse").textContent = q ? (a ? "→ " + a.norm : "…") : "deterministic grammar · no LLM in the answer path";
  const items = SUGG().filter(([t]) => !q || t.toLowerCase().includes(q.toLowerCase().slice(0, 12))); if (q && a && a.route) items.unshift([q, a.route]);
  sel = Math.min(sel, Math.max(0, items.length - 1)); $("pList").replaceChildren(...items.slice(0, 8).map(([t, href], i) => h("li", {}, h("button", { class: i === sel ? "sel" : "", onclick: () => { closePalette(); location.hash = href; } }, h("span", {}, t), h("span", { class: "mono muted", style: "font-size:11px" }, href.split("/")[1]))))); $("pList").dataset.items = JSON.stringify(items.slice(0, 8)); }
function askServer() { const q = $("pIn").value; if (!q) return; api("/api/v1/ask?q=" + encodeURIComponent(q)).then(j => { lastAsk = { q, norm: j.meta.normalized, route: j.meta.route }; }).catch(e => { lastAsk = { q, norm: String(e.message), route: null }; }).then(renderPalette); }
function openPalette() { $("palette").classList.add("open"); $("pIn").value = ""; sel = 0; renderPalette(); $("pIn").focus(); }
function closePalette() { $("palette").classList.remove("open"); }
$("askBtn").onclick = openPalette; $("pIn").oninput = () => { sel = 0; renderPalette(); clearTimeout(askTimer); askTimer = setTimeout(askServer, 150); };
$("pIn").onkeydown = e => { const items = JSON.parse($("pList").dataset.items || "[]"); if (e.key === "ArrowDown") { sel = Math.min(items.length - 1, sel + 1); renderPalette(); e.preventDefault(); } else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); renderPalette(); e.preventDefault(); } else if (e.key === "Enter" && items[sel]) { closePalette(); location.hash = items[sel][1]; } else if (e.key === "Escape") closePalette(); };
$("palette").onclick = e => { if (e.target.id === "palette") closePalette(); };
$("themeBtn").onclick = () => { const r = document.documentElement; r.dataset.theme = r.dataset.theme === "paper" ? "instrument" : "paper"; route(); };
$("drClose").onclick = () => $("drawer").classList.remove("open");
$("integrityBtn").onclick = async () => { const j = await api("/api/v1/integrity"), i = j.data, b = $("drBody"); $("drTitle").textContent = "Pack integrity";
  const sub = i.submission || {};
  b.replaceChildren(kv([["status", tp(i.status)], ["changed", (i.changed || []).join(", ") || "none"], ["missing", (i.missing || []).join(", ") || "none"], ["unlisted", (i.unlisted || []).join(", ") || "none"], ["verified at", i.verified_at], ["S3", sub.bucket ? h("span", { class: "mono" }, sub.bucket + "/" + sub.key) : "no submission recorded"], ["ETag", sub.etag ? h("span", { class: "mono" }, sub.etag) : null], ["readback", sub.readback_verified == null ? null : (sub.readback_verified ? "verified " : "not verified ") + (sub.readback_at || "")]]),
    h("p", { class: "muted" }, "Checksums, not signatures or hash chains (out of scope). A stranger runs: python3 tools/manifest.py verify .")); openDrawer(); };
document.addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); return; } if (e.target.tagName === "INPUT") return;
  if (e.key === "Escape") { $("drawer").classList.remove("open"); closePalette(); } else if (e.key === "/") { e.preventDefault(); openPalette(); } else if (e.key === "t") $("themeBtn").click(); });
async function startSession() {
  const m = /^#k=([A-Za-z0-9_-]+)(?:&r=\/([A-Za-z0-9_\/%.|:-]*))?$/.exec(location.hash);   // optional deep link: #k=<key>&r=/<view>/<arg>
  if (!m) return;
  const r = await fetch("/api/v1/session", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: m[1] }) });
  history.replaceState(null, "", location.pathname + (r.ok ? "#/" + (m[2] || "answer") : "#/session-failed"));
}
async function loadAll() {
  await startSession();
  const pj = await api("/api/v1/pack"); P = pj.data; META = pj.meta || {}; VOCAB = META.vocab || {};
  VL = Object.fromEntries(Object.entries(VOCAB).map(([k, v]) => [k, v.label])); GLYPH = Object.fromEntries(Object.entries(VOCAB).map(([k, v]) => [k, v.glyph]));
  const bj = await api("/api/v1/boot");   // one request carries every view's data: no burst, no 429 on a normal first load
  D.answers = bj.data.answers || {}; D.auditor = bj.data.auditor || {}; D.records = bj.data.records || {}; D.cases = bj.data.cases || [];
  D.runList = bj.data.runs || []; D.runWindow = bj.data.window || null;
  const m = META.mode || {};
  const rb = $("ribbon"); rb.textContent = m.banner || ""; rb.className = "ribbon " + (m.tone || "");
  $("modeChip").textContent = m.chip || "PACK · read-only"; $("integrityBtn").textContent = "MANIFEST " + (m.integrity_text || "?");
  $("integrityBtn").className = "chip btn " + (m.integrity_ok ? "good" : "bad");
  $("foot").replaceChildren(h("span", {}, "pack " + (P.generated_at || "")), h("span", {}, "all times UTC"), h("span", {}, "tickmarks: Ⓡ recomputed · Ⓐ agreed to source · Ⓣ traced · Ⓥ vouched"), h("span", {}, "seal: out of scope"));
  if (P.pack && P.pack.title) document.title = P.pack.title + " · Evidence Console";
  window.addEventListener("hashchange", route); route();
  setInterval(() => api("/api/v1/cases").then(j => { if (JSON.stringify(j.data) !== JSON.stringify(D.cases)) { D.cases = j.data; if (location.hash.startsWith("#/loop")) route(); } }).catch(() => {}), 10000);
}
loadAll().catch(e => { $("main").replaceChildren(h("div", { class: "page" }, card("Console could not load", h("p", { class: "v-breach" }, String(e.message)))));});


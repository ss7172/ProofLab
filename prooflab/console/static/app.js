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
/* the rule's date proof, three states (PR-48): "after" only when an S3 T1 proof in the pack is later than the scope */
function dateProof(r) {
  const dp = r.date_proof || {}, st = dp.state || (r.date_before_scope ? "PROVEN_BEFORE" : "NOT_PROVEN");
  if (st === "PROVEN_BEFORE") return ["✓ dated before the scope (S3 T1 " + hms(dp.t1_at || r.frozen_at) + ")", "good"];
  if (st === "PROVEN_AFTER") return ["RULE DATED AFTER TEST (S3 T1 " + hms(dp.t1_at) + ")", "bad"];
  return ["date proof not in this pack · register says frozen " + hms(dp.register_frozen_at || r.frozen_at) + " (unproven)", "warn"];
}
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
/* PR-54: long ids and digests: short mono text, full value on hover (title) and on the copy button */
function idv(full, n) { full = String(full == null ? "" : full); const short = full.length > (n || 24) ? full.slice(0, n || 24) + "…" : full, b = h("button", { class: "copy", title: "copy " + full, "aria-label": "copy" }, "⧉");
  b.onclick = e => { e.stopPropagation(); (navigator.clipboard ? navigator.clipboard.writeText(full) : Promise.reject()).then(() => { b.textContent = "✓"; setTimeout(() => { b.textContent = "⧉"; }, 1200); }).catch(() => {}); };
  return h("span", { class: "idv" }, h("span", { class: "idt mono", title: full }, short), b); }
function proseIds(text) { return String(text == null ? "" : text).split(/((?:sha256:)?[0-9a-f]{32,})/).map(p => /^(?:sha256:)?[0-9a-f]{32,}$/.test(p) ? h("span", { class: "mono hash", title: p }, p.replace(/^(sha256:)?([0-9a-f]{12}).*$/, "$1$2…")) : p); }
const stripMd = x => x == null ? x : String(x).replace(/\*\*/g, "");
function kv(pairs) { return h("dl", { class: "kv" }, pairs.filter(p => p[1] != null && p[1] !== "").map(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])); }

/* ---------------- record inspector (stranger test) ---------------- */
function findRecord(ref) { const id = ref.startsWith("record:") ? ref.slice(7) : ref; for (const rs of Object.values(D.records)) { const r = rs.find(x => x.evidence_id === id || (x.facts || {}).record_id === id); if (r) return r; } return null; }
async function sha256(text) { const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)); return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join(""); }
function rawHolder(ref) { const box = h("div", {}, h("p", { class: "muted" }, "loading the raw line…")); api("/api/v1/raw?ref=" + encodeURIComponent(ref)).then(j => box.replaceChildren(rawLine(j.data.line))).catch(() => box.replaceChildren(h("p", { class: "v-breach" }, "unresolved: not listed in the pack"))); return box; }
function rawLine(line) { let pretty = null; try { const o = JSON.parse(line); if (o && typeof o === "object") pretty = JSON.stringify(o, null, 2); } catch (e) { pretty = null; }
  if (pretty == null || pretty.length < 400) return rawPre(line);
  return h("div", {}, h("div", { class: "label" }, "formatted view (the sha256 is over the raw line below)"), h("pre", { class: "raw" }, pretty), h("details", {}, h("summary", { class: "label" }, "Raw line as captured (sha256 is over this)"), rawPre(line))); }
function rawPre(line) { const pre = h("pre", { class: "raw" }); String(line).split(/(\[REDACTED:[^\]]+\])/).forEach(p => pre.append(/^\[REDACTED/.test(p) ? h("span", { class: "redact" }, p) : document.createTextNode(p))); return pre; }
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
  const r = P.register, pts = [r.first_exploratory_at ? ["exploratory runs (excluded)", r.first_exploratory_at, "--ink-4"] : null, ["register frozen", r.frozen_at, "--trace"], ap(r).at ? ["owner approved (" + String((ap(r).ref || ":").split(":")[1]) + ")", ap(r).at, "--held"] : null, ["first assessed run", r.first_assessed_run_at, "--ink"], (P.named_runs || {}).written_at ? [P.named_runs.written_at_basis ? "first named run started" : "named runs written", P.named_runs.written_at, "--ink-2"] : null, P.pack.judging_starts_at ? ["judging", P.pack.judging_starts_at, "--unknown"] : null].filter(p => p && p[1]).sort((a, b) => Date.parse(a[1]) - Date.parse(b[1]));   // PR-54: in time order, so labels alternate and never collide
  if (!pts.length) return h("p", { class: "muted" }, "no dated register events in this pack");
  const t0 = Date.parse(pts[0][1]), t1 = Date.parse(pts[pts.length - 1][1]), W = 860, x = t => 40 + (W - 80) * (t1 > t0 ? (Date.parse(t) - t0) / (t1 - t0) : 0.5), g = s("svg", { viewBox: `0 0 ${W} 100`, width: "100%", role: "img", "aria-label": "Register freeze and approval precede every assessed run" });
  g.append(s("line", { x1: 40, x2: W - 40, y1: 46, y2: 46, stroke: css("--rule-strong"), "stroke-width": 2 }));
  const anc = i => i === 0 ? "start" : i === pts.length - 1 ? "end" : "middle", ax = (t, i) => i === 0 ? x(t) - 6 : i === pts.length - 1 ? x(t) + 6 : x(t);
  pts.forEach(([l, t, c], i) => g.append(s("circle", { cx: x(t), cy: 46, r: 6, fill: css(c) }), s("text", { x: ax(t, i), y: i % 2 ? 74 : 28, "text-anchor": anc(i), fill: css("--ink-2"), "font-size": 12 }, l), s("text", { x: ax(t, i), y: i % 2 ? 90 : 13, "text-anchor": anc(i), fill: css("--ink-3"), "font-size": 11 }, t.slice(5, 16).replace("T", " ") + "Z")));
  const okOrder = ap(r).at && Date.parse(r.frozen_at) < Date.parse(ap(r).at) && Date.parse(ap(r).at) < Date.parse(r.first_assessed_run_at);
  return h("div", {}, h("div", { class: "svgwrap" }, g), h("ol", { class: "evlist small" }, pts.map(([l, t]) => h("li", {}, h("span", { class: "mono" }, t), " · " + l))), h("p", { class: "callout " + (okOrder ? "good" : "bad") }, (!ap(r).at ? "✗ no owner approval record in the pack (MISSING): the order frozen, approved, first assessed run cannot be shown" : Date.parse(r.frozen_at) < Date.parse(ap(r).at) && Date.parse(ap(r).at) < Date.parse(r.first_assessed_run_at) ? "✓ frozen, then approved, then the first assessed run" : "✗ the order frozen, approved, first assessed run does NOT hold") + " · same threshold version for the named runs is shown on each answer"));
}
function runOf(id) { return (P.runs || []).find(r => r.cid === id || r.alias === id) || null; }
function answerIndex() {
  const keys = (P.answers || []).map(a => a.key), runs = [], wins = [];
  keys.forEach(k => { const [c, kind, sc] = k.split("|"); if (kind === "run" && !runs.includes(sc)) runs.push(sc); if (kind === "interval" && !wins.includes(sc)) wins.push(sc); });
  const cell = (c, kind, sc) => { const k = c + "|" + kind + "|" + sc, a = D.answers[k]; return h("td", {}, a ? h("a", { href: "#/answer/" + encodeURIComponent(k), title: k }, vpill(a.verdict.value)) : h("span", { class: "muted" }, "not stored")); };
  return card("Answer index · every stored answer in this pack (click a verdict to open it)", h("div", { class: "tscroll" }, h("table", { class: "t idx" }, h("thead", {}, h("tr", {}, ["Scope", "Label"].concat(["C16", "C7", "C9"].map(c => { const k = ((P.register || {}).controls || []).find(x => x.ref === c); return c + (k && k.id ? " · " + k.id : ""); })).map(x => h("th", {}, x)))),
    h("tbody", {}, runs.map(sc => { const r = runOf(sc) || {}; return h("tr", {}, h("td", {}, idv(sc, 30)), h("td", {}, r.label ? tp(r.label) : h("span", { class: "muted" }, "not recorded")), cell("C16", "run", sc), cell("C7", "run", sc), cell("C9", "run", sc)); }),
      wins.map(sc => h("tr", {}, h("td", { class: "mono" }, "window " + sc.replace(/:00Z/g, "Z").replace("..", " → ")), h("td", {}, tp("WINDOW")), cell("C16", "interval", sc), cell("C7", "interval", sc), cell("C9", "interval", sc)))))));
}
let ASKED = null;   // set by the palette: what the judge typed, so the answer page can say when it differs from what is stored
function approvalRel(r, a) {
  const at = ap(r).at, st = (a.scope || {}).start || (runOf((a.scope || {}).id) || {}).started_at;
  if (ap(r).status === "MISSING" || !at) return spill("approval MISSING", "bad");
  if (!st || (a.scope || {}).kind !== "run") return spill("approval time vs scope: not compared", "mute");
  return Date.parse(at) <= Date.parse(st) ? spill("approved BEFORE this run", "good") : spill("approved AFTER this run — not vouched for it", "bad");
}
function answerView(key) {
  const a = D.answers[key || firstKey()]; if (!a) return h("div", { class: "page" }, card("No such answer", "Try ⌘K."), answerIndex());
  const isC16 = a.control.ref === "C16", r = a.rule || {}, aq = a.audit_question || {}, pop = a.population || {}, enf = a.enforcement || {}, aict = a.aict || {}, ol = r.observation_limit || {}, et = r.exception_tolerance || {};
  const sc = a.scope || {}, ser = (a.measurement.series || []).filter(x => x.id !== sc.id), cmp = a.comparison || {};
  const group = (title, keys) => h("section", {}, h("div", { class: "label gh" }, title), keys.map(([k, label]) => { const q = aq[k] || { text: "not stated (gap)", flag: "FLAG" }, fl = q.flag === "FLAG" || q.flag === "GAP"; return h("div", { class: "q" + (fl ? " flag" : "") }, h("span", { class: "label" }, label, fl ? " " : null, fl ? spill("GAP", "warn") : null), h("div", { class: "qt" }, proseIds(q.text)), h("div", { class: "qr" }, (q.refs || []).slice(0, 2).map(r => [refEl(r), " "]), srcTag(q.source))); }));
  const loops = a.human_loops || [], run = runOf(sc.id), lim = cmp.limit != null ? cmp.limit : ol.value, val = a.measurement.value, unit = a.measurement.unit || ol.unit || "";
  const asked = ASKED && ASKED.key === (key || firstKey()) && ASKED.norm && ASKED.norm !== a.query.normalized ? ASKED.norm : null;
  const popKeys = [["expected", (pop.expected || {}).count], ["observed", pop.observed], ["matched", pop.matched], ["unmatched", pop.unmatched], ["missing", pop.missing], ["dupes removed", pop.duplicates_removed], ["blocked", pop.blocked], ["unmeasurable", pop.unmeasurable]].filter(([k, v]) => v != null || k === "missing");
  return h("div", { class: "page" },
    !key ? answerIndex() : null,
    h("div", { class: "crumb" }, h("div", { class: "mono echo", title: a.query.text }, "› " + a.query.text), h("div", { class: "mono muted small", title: a.query.normalized }, "parsed → " + a.query.normalized + " · answered in " + a.elapsed_ms + " ms from " + a.source.records_scanned + " records · PACK · MANIFEST " + a.source.manifest_status)),
    h("section", { class: "card answer" },
      h("div", { class: "ahead" }, h("span", { class: "pill xl p-" + ((VOCAB[a.verdict.value] || {}).pill || "mute") }, (GLYPH[a.verdict.value] || "") + " " + a.verdict.label), h("span", { class: "ctl" }, a.control.ref + " · " + a.control.id), h("span", { class: "chip" }, a.control.mode), h("span", { class: "mla" }, ticks(["R", "A", "T", "V"]))),
      h("div", { class: "row ascope" }, h("span", { class: "label" }, sc.kind === "run" ? "run" : "window"), idv(sc.id, 34), run && run.label ? tp(run.label) : sc.kind === "run" ? spill("run label not recorded", "mute") : null, asked ? spill("asked: " + asked, "warn") : null, /NOT applied/.test(a.query.normalized || "") ? spill("window not applied — whole run", "warn") : null),
      h("p", { class: "reason" }, a.verdict.reason),
      h("div", { class: "mvl" }, h("div", {}, h("div", { class: "label" }, "measured"), h("div", { class: "big mono v-" + vtone(a.verdict.value) }, fmt(val), h("span", { class: "unit" }, " " + unit))), h("div", { class: "vs" }, "vs"),
        h("div", {}, h("div", { class: "label" }, "limit"), h("div", { class: "big mono" }, (cmp.limit != null ? cmp.operator || ol.operator || "" : ol.operator || "") + " " + fmt(lim), h("span", { class: "unit" }, " " + (cmp.limit != null ? unit : ol.unit || unit)))),
        cmp.delta != null ? h("div", { class: "margin " + (cmp.within_limit ? "v-held" : "v-breach") }, cmp.within_limit ? "margin " + fmt(Math.abs(cmp.delta)) : "over by " + fmt(Math.abs(cmp.delta))) : null,
        h("div", { class: "mla small muted" }, h("span", { class: "label" }, "exception tolerance "), (et.operator || "") + " " + fmt(et.value) + " " + (et.unit || ""), cmp.exception_fraction != null ? " · observed " + cmp.exceptions_count + " = " + cmp.exception_fraction + "%" : cmp.exceptions_count != null ? " · observed " + cmp.exceptions_count : "")),
      isC16 && lim != null && val != null ? bullet(a) : null,
      !isC16 && ser.length ? seriesView(ser, a, ol) : null,
      h("div", { class: "facts4" },
        h("div", {}, h("div", { class: "label" }, "Rule"), h("div", { class: "mono" }, r.threshold_version + " (" + r.register_version + ")"), h("div", { class: "small muted" }, "dated " + r.version_date + " · frozen " + hms(r.frozen_at)), h("div", { class: "small" }, refEl(r.source_ref || ""))),
        h("div", {}, h("div", { class: "label" }, "Date proof"), spill(...dateProof(r))),
        h("div", {}, h("div", { class: "label" }, "Approval"), h("div", {}, ap(r).status === "MISSING" ? "not recorded" : apName(r) + " " + hms(ap(r).at)), approvalRel(r, a), ap(r).ref ? h("div", { class: "small" }, refEl(ap(r).ref)) : null),
        h("div", {}, h("div", { class: "label" }, "Evidence"), tp(a.verdict.evidence_sufficiency || "UNKNOWN"), h("div", { class: "small muted" }, fmt(a.source.records_scanned) + " records · owner " + nm(r.owner)))),
      h("div", { class: "afoot small muted" }, h("span", {}, "answer_id "), idv(a.answer_id, 14), h("span", {}, " · " + a.elapsed_ms + " ms · MANIFEST " + a.source.manifest_status))),
    h("div", { class: "pop" }, popKeys.map(([k, v]) => h("div", {}, h("span", { class: "label" }, k), h("b", { class: (k === "missing" || k === "unmeasurable" || k === "blocked") && v ? "v-breach" : "" }, v == null ? "not recorded" : fmt(v))))), (pop.missing_events || []).length ? h("div", { class: "mono v-unknown small" }, "expected but not captured: " + pop.missing_events.join(", ")) : null,
    h("div", { class: "aq" }, group("The action", [["what_was_done", "What was done"], ["by_which_agent", "By which agent"], ["where", "Where"], ["when", "When"]]), group("The decision", [["under_whose_authority", "Under whose authority"], ["rule_checked", "Which rule"], ["limit_in_force", "Limit in force at that moment"], ["decision", "Allowed, stopped or escalated"]]), group("The proof", [["who_was_told", "Who was told"], ["unchanged_since", "Unchanged since?"]])),
    h("div", { class: "grid2" },
      card("Control test (tester) — judges the control", kv([["tester", h("span", { class: "mono" }, (enf.tester || {}).name + " @ " + (enf.tester || {}).version)], ["formula", h("span", { class: "mono" }, a.measurement.formula)], ["mode", tp(enf.mode || "UNKNOWN")], ["exceptions", (a.exceptions || []).length ? a.exceptions.map(e => h("div", { class: "mono small" }, "▲ ", proseIds(e.why || e.note || e.key || e.kind || JSON.stringify(e)))) : "none"], ["threshold source", h("span", { class: "mono" }, r.source_ref)]])),
      card("Inline decisions (evaluator) — judges each call, in the path", enf.inline_decisions && enf.inline_decisions.length ? h("div", {}, h("div", { class: "row decs" }, enf.inline_decisions.map(d => h("span", { class: "pill " + (d.decision === "ALLOW" ? "p-good" : d.decision === "ALERT" ? "p-warn" : "p-bad"), title: d.decision + " " + d.call_id + ": " + (d.reason || "committed " + fmt(d.committed) + " + reserved " + fmt(d.reserved)) }, (d.decision === "ALLOW" ? "✓ " : d.decision === "ALERT" ? "! " : "✗ ") + hms(d.at)))),
        enf.inline_decisions.filter(d => d.decision !== "ALLOW").map(d => h("div", { class: "denyl mono" }, h("b", { class: d.decision === "ALERT" ? "v-unknown" : "v-breach" }, d.decision), " before call " + String(d.call_id).split("-").pop() + " at " + hms(d.at) + ": " + (d.committed == null ? (d.reason || "numbers not recorded") : "committed " + fmt(d.committed) + (d.reserved ? " + reserved " + fmt(d.reserved) : "") + " + bound " + fmt(d.bound) + " = " + fmt(d.projected) + " > cap " + fmt(d.limit)), " ", srcTag(d.source ? "recorded (detail, inline.limit_value)" : "not-recorded"))), h("p", { class: "muted small" }, "Reserve, then commit — two calls cannot both read 9,800 under 10,000 and pass.")) : h("p", { class: "muted" }, "POST-RUN control: no inline evaluator for this control (stated honestly)."))),
    h("div", { class: "split" },
      card("Evidence behind the number (" + (a.records || []).length + ") · click a row for the raw record", h("div", { class: "tscroll" }, h("table", { class: "t recs" }, h("thead", {}, h("tr", {}, ["Tickmarks", "Record", "Summary", "MANIFEST"].map(x => h("th", {}, x)))), h("tbody", {}, (a.records || []).map(rc => h("tr", { class: "click", onclick: () => inspect(rc.ref) }, h("td", { class: "nw" }, ticks(rc.tickmarks)), h("td", { class: "mono cut", title: rc.ref }, rc.ref.replace(/^record:/, "")), h("td", { class: "small" }, proseIds(rc.summary || rc.ref)), h("td", {}, rc.manifest === "OK" ? h("span", { class: "pill p-good" }, "✓ listed") : h("span", { class: "pill p-bad" }, "MANIFEST " + (rc.manifest || "?"))))))))),
      h("div", { class: "stack" },
        card("Who was told — human loop (" + loops.length + ")", loops.length ? loops.map(l => h("div", { class: "ep" }, h("a", { href: "#/loop/" + l.incident, title: "Open the ServiceNow case" }, idc(l.incident || "no incident")), h("div", {}, h("div", { class: "row tight" }, tp((l.delivery || {}).state || "UNKNOWN"), tp((l.response || {}).state || "UNKNOWN"), spill("Nemotron " + String((l.assurance_agent || {}).state || "unknown").toLowerCase().replace(/_/g, " "), TONE[(l.assurance_agent || {}).state] || "trace"), tp((l.closure || {}).state || "UNKNOWN"), (l.closure || {}).flag ? spill(l.closure.flag, "bad") : null),
          h("div", { class: "muted small" }, "owner " + nm(l.owner) + " · delivered " + hms((l.delivery || {}).at) + " · cutoff " + hms((l.response || {}).cutoff) + ((l.closure || {}).retest_ref ? " · closed by " + l.closure.retest_ref.split("/").pop() : "")),
          (l.lines || []).length ? h("ol", { class: "lines small" }, l.lines.map(x => h("li", {}, proseIds(x)))) : null, srcTag(l.source)))) : h("p", { class: "muted" }, "Nothing needed telling. Evidence is in the pack.")),
        String(aict.status || "UNKNOWN") === "UNKNOWN" && !(aict.assets || []).length ? card("AI Control Tower", h("p", { class: "muted" }, "Not in this pack: no AI Control Tower import or monitor record was captured for this scope (gap A3, stated)."), srcTag("not-recorded"))
          : card("AI Control Tower", kv([["status", aict.status], ["connection", aict.connection], ["discovered", (aict.assets || []).join(", ") || "not in this pack"], ["last import", aict.last_import_at], ["monitor", h("span", { class: "v-unknown" }, "no AWS sessions (gap A3)")], ["proof", h("span", {}, (aict.refs || []).slice(0, 3).map(r => [refEl(r), " "]))]])),
        card("Gaps for this scope", (a.gaps || []).length ? a.gaps.map(gp => h("div", { class: "dim" }, h("b", { class: "mono" }, gp.id + " "), stripMd(gp.text))) : h("span", { class: "muted" }, "none")))));
}
function seriesView(ser, a, ol) {
  const lim = ser[0].limit != null ? ser[0].limit : ol.value, hasVals = ser.some(x => x.value != null);
  return h("div", {}, hasVals && lim != null ? bars(ser.map(x => Object.assign({}, x, { limit: lim })), a.measurement.unit || "", "limit " + (ol.operator || "") + " " + fmt(ol.value)) : null,
    h("table", { class: "t series" }, h("thead", {}, h("tr", {}, ["Counted", "Status", "Value", "Stored assessment"].map(x => h("th", {}, x)))), h("tbody", {}, ser.map(x => h("tr", {}, h("td", {}, idv(x.id, 34)), h("td", {}, tp(x.status || "UNKNOWN")), h("td", { class: "mono" }, x.value == null ? "not recorded" : fmt(x.value)), h("td", {}, x.ref ? refEl(x.ref) : "—"))))));
}
function ledger(alias) {
  const hasC16 = r => (D.records[r.alias] || []).some(x => x["control.ref"] === "C16");
  const run = alias || ((P.runs || []).find(r => r.provenance === "ASSESSED" && hasC16(r)) || (P.runs || []).find(hasC16) || (P.runs || [])[0] || {}).alias, recs = D.records[run] || [], c16 = recs.filter(r => r["control.ref"] === "C16"), mc = c16.filter(r => r.record_kind === "model-call" && r["call.id"]), gw = mc.filter(r => (r.source || {}).surface === "spans"), sample = gw[gw.length - 1] || mc[mc.length - 1] || c16[c16.length - 1];
  const groups = {}; (P.runs || []).forEach(r => { const g = String(r.label || r.provenance || "other").replace(/_/g, " "); (groups[g] = groups[g] || []).push(r); });
  const picker = h("label", { class: "runpick" }, h("span", { class: "label" }, "Run "), h("select", { class: "runsel", "aria-label": "Run", onchange: e => { location.hash = "#/ledger/" + e.target.value; } }, Object.entries(groups).map(([g, rs]) => h("optgroup", { label: g }, rs.map(r => { const n = (D.records[r.alias] || []).length; return h("option", { value: r.alias, selected: r.alias === run }, r.alias + " · " + n + " records"); })))));
  const head = h("div", { class: "row between" }, h("div", {}, h("div", { class: "label" }, "Evidence Ledger · bound records (ifabric.evidence/v1)"), h("h1", { class: "h1" }, "A log is for an engineer. Evidence is for a stranger.")), picker);
  if (!sample) return h("div", { class: "page" }, head, card("No C16 records for " + run, h("p", { class: "muted" }, "This run has no C16 records in this pack (pilot and exploratory runs often have none). Pick another run above, or see "), h("a", { class: "chip btn", href: "#/runs" }, "all runs →")));
  return h("div", { class: "page" }, head,
    h("div", { class: "grid2" }, card("LOG — as captured (" + (SURF[(sample.source || {}).surface] || (sample.source || {}).surface || "source not recorded") + ", call " + (sample["call.id"] || "not recorded") + ")", rawHolder(sample.source.raw_ref), h("p", { class: "muted small" }, "Written for an engineer next week. It shows something happened, not that it was allowed.")),
      card("EVIDENCE — the same call, bound" + (sample.facts && sample.facts.ep ? " · " + sample.facts.ep : "") + " · " + (sample.record_kind || "record"), kv(["run.id", "call.id", "control.id", "threshold.version", "threshold.value", "measured.value", "verdict", "actor.id", "emitted.at"].map(k => [k, h("span", { class: "mono" }, k === "verdict" ? VL[sample[k]] : k === "measured.value" ? mval(sample) : typeof sample[k] === "number" ? fmt(sample[k]) : sample[k] == null ? "not recorded" : sample[k])]).concat([["measured basis", h("span", { class: "muted" }, (sample.facts || {}).measured_basis || "not recorded")]]).concat([["seal", h("span", { class: "muted" }, "out of scope")], ["verify", h("button", { class: "chip btn", onclick: () => inspect("record:" + sample.evidence_id) }, "Open in inspector · recompute sha256")]])))),
    card(recs.length + " records for " + run, h("table", { class: "t" }, h("thead", {}, h("tr", {}, ["", "run.id", "call/event", "control", "version", "measured.value", "verdict", "decision", "actor.id", "emitted.at"].map(x => h("th", {}, x)))),
      h("tbody", {}, recs.map(r => h("tr", { class: "click", onclick: () => inspect("record:" + r.evidence_id) }, h("td", {}, ticks(r.record_kind === "model-call" ? ["R", "A", "T"] : ["R", "A"])), h("td", { class: "mono cut", title: r["run.id"] }, r["run.id"]), h("td", { class: "mono cut", title: r["call.id"] || r.facts.expected_event }, r["call.id"] || r.facts.expected_event), h("td", { class: "mono" }, r["control.ref"]), h("td", { class: "mono" }, r["threshold.version"]), h("td", { class: "mono" }, mval(r)), h("td", {}, r.verdict === "NOT_ASSESSED" ? h("span", { class: "muted", title: "a record is not a verdict; the control test's verdict is in the answer" }, "record") : vpill(r.verdict)), h("td", {}, r.decision ? tp(r.decision) : ""), h("td", { class: "mono", style: "font-size:11.5px" }, r["actor.id"]), h("td", { class: "mono", style: "font-size:11.5px" }, hms(r["emitted.at"]))))))));
}
function auditor(id) {
  const a = D.auditor[id || ((P.auditor || [])[0] || {}).id];
  if (!a) return h("div", { class: "page" }, card(id ? "No auditor view for " + id : "No auditor views stored", h("p", { class: "muted" }, id ? "This pack holds no six-questions view for that id. Stored views: " + (Object.keys(D.auditor).join(", ") || "none") + "." : "pack-index auditor[] is empty. From the unzipped pack: python3 -m prooflab query --incident <CID>")));
  const picker = h("div", { class: "row" }, Object.keys(D.auditor).map(k => h("a", { class: "chip btn" + (k === a.scope.id ? " trace" : ""), href: "#/auditor/" + k }, k)));
  const qn = [["who", "1 WHO acted"], ["what", "2 WHAT it touched"], ["authorized", "3 AUTHORIZED"], ["approved", "4 APPROVED"], ["integrity", "5 INTEGRITY"], ["reconstruct", "6 RECONSTRUCT"]];
  return h("div", { class: "page" }, h("div", { class: "row", style: "justify-content:space-between" }, h("div", {}, h("div", { class: "label" }, "Six auditor questions · answered from the Evidence Pack alone"), h("h1", { class: "h1" }, a.title), h("p", { class: "sub mono" }, "window " + (a.window || {}).start + " → " + (a.window || {}).end)), picker),
    h("div", { class: "grid3" }, qn.map(([k, t]) => { const q = Object.assign({ status: "GAP", answer: "not answered in this view (gap)", facts: [], gaps: [] }, (a.questions || {})[k]); if (k === "integrity" && (META.mode || {}).integrity_text) { q.answer = "MANIFEST at serve time: " + META.mode.integrity_text + " (checked by the console now; the stored line below was written at pack build, before MANIFEST.json, which is written last)"; } return h("section", { class: "card" }, h("div", { class: "row", style: "justify-content:space-between" }, h("b", {}, t), tp(q.status)), h("p", { style: "margin:6px 0 8px" }, proseIds(q.answer)), (q.facts || []).map(f => h("dl", { class: "fact" + (f.flag === "FLAG" ? " flag" : "") }, h("dt", {}, f.label), h("dd", {}, typeof f.value === "string" ? proseIds(f.value) : f.value, " ", (f.refs || []).slice(0, 1).map(refEl), srcTag(f.source)))), (q.gaps || []).length ? h("div", { class: "muted", style: "font-size:11.5px;margin-top:6px" }, "gap " + q.gaps.join(", ") + " — stated, not hidden") : null); })));
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
    h("div", { class: "grid2" }, (P.gaps || []).length ? P.gaps.map(g => card(h("span", {}, h("span", { class: "mono v-unknown" }, g.gap_id), " " + stripMd(g.title), " ", tp(g.status || "OPEN")), kv([["what", stripMd(g.what)], ["why", stripMd(g.why)], ["affects", [((g.affects || {}).controls || []).join(", "), ((g.affects || {}).levels || []).join(", "), ((g.affects || {}).auditor_questions || []).join(", ")].filter(Boolean).join(" · ") || "—"], ["impact", stripMd(g.impact)], ["next", stripMd(g.next)], ["status", tp(g.status || "OPEN")], ["source", g.source ? h("span", { class: "mono" }, g.source) : null]]))) : card("No gaps listed", h("p", { class: "muted" }, "pack-index gaps[] is empty; read gap-list.md in the pack."))));
}
function architecture() {
  const eps = P.enforcement_points || [], ca = eps.some(e => e.changed_adapter), uc = eps.some(e => (e.unchanged_core || []).length), ev = eps.some(e => (e.evidence_refs || []).length || e.note);
  return h("div", { class: "page" }, h("div", {}, h("div", { class: "label" }, "Enforcement points · from pack-index"), h("h1", { class: "h1" }, "What can refuse, and what only watches")),
    card("Enforcement points — status rendered exactly as recorded in the pack", h("table", { class: "t" }, h("thead", {}, h("tr", {}, ["EP", "Kind", "Transport", "Can refuse", "Status"].concat(ca ? ["Changed adapter"] : [], uc ? ["Unchanged core"] : [], ev ? ["Evidence"] : []).map(x => h("th", {}, x)))), h("tbody", {}, eps.map(e => h("tr", {}, h("td", {}, h("b", { class: "mono" }, e.id), h("div", { class: "muted small" }, e.name)), h("td", { class: "mono" }, e.kind), h("td", { class: "mono" }, e.transport + "()"), h("td", {}, e.can_refuse ? "yes" : "no"), h("td", {}, tp(e.status)), ca ? h("td", { class: "mono small" }, e.changed_adapter || "—") : null, uc ? h("td", { class: "mono small" }, (e.unchanged_core || []).join(", ") || "—") : null, ev ? h("td", { class: "small" }, (e.evidence_refs || []).length ? (e.evidence_refs || []).length + " ref(s)" : "", e.note ? h("div", { class: "muted" }, stripMd(e.note)) : null) : null))))));
}
function runsView() {
  const rows = D.runList || [];
  return h("div", { class: "page" }, h("div", {}, h("div", { class: "label" }, "Run catalogue · every run any source saw"), h("h1", { class: "h1" }, "Runs, with what each one is"), h("p", { class: "sub" }, "Runs outside the declared window or not assessed stay listed and are labelled; they never change a verdict."), h("p", { class: "sub mono" }, D.runWindow ? "Declared window: " + (D.runWindow.start || "?") + " .. " + (D.runWindow.end || "?") + (D.runWindow.note ? " (" + D.runWindow.note + ")" : "") : "Declared window: none in this source")),
    card(rows.length + " runs", h("table", { class: "t" }, h("thead", {}, h("tr", {}, ["Alias", "Run id", "Provenance", "Source", "Started (window)", "Assessed", "Label"].map(x => h("th", {}, x)))),
      h("tbody", {}, rows.map(r => h("tr", { class: "click" + (r.provenance && r.provenance !== "ASSESSED" ? " dim" : ""), title: "open " + (D.auditor[r.cid] ? "the six questions" : "the evidence ledger") + " for this run", onclick: () => { location.hash = D.auditor[r.cid] ? "#/auditor/" + r.cid : "#/ledger/" + (r.alias || r.cid); } }, h("td", { class: "mono cut", title: r.alias || "" }, r.alias || "—"), h("td", {}, idv(r.cid || r.run_id || "—", 30)), h("td", {}, tp(r.provenance || "UNKNOWN")), h("td", { class: "small" }, r.source || "—"), h("td", { class: "mono small" }, r.first_seen ? hms(r.first_seen) + (r.in_window == null ? "" : r.in_window ? " · inside" : " · outside") : "start not recorded"), h("td", {}, r.assessed == null ? "unknown" : r.assessed ? "yes" : "no"), h("td", {}, r.label || r.purpose ? tp(r.label || r.purpose) : "")))))));
}

/* ---------------- boot: the data comes from the console API, never embedded ---------------- */
async function api(path, tries = 4) { const r = await fetch(path, { credentials: "same-origin" });
  if (r.status === 429 && tries > 0) { await new Promise(ok => setTimeout(ok, 1100)); return api(path, tries - 1); }   // the console's per-second limit: wait, then retry
  const j = await r.json(); if (!r.ok || !j.ok) throw new Error((j.error && j.error.message) || r.status); return j; }
const ROUTES = [["B", "answer", "Ask · Answer"], ["D", "ledger", "Evidence Ledger"], ["E", "auditor", "Six Questions"], ["F", "register", "Register"], ["G", "loop", "Human Loop"], ["I", "architecture", "Enforcement points"], ["J", "gaps", "Gaps"], ["R", "runs", "Runs"]];
const VIEWS = Object.assign({ answer: answerView, ledger, auditor, register, loop, architecture, enforcement: architecture, gaps, runs: runsView }, window.PROOFLAB_P1_VIEWS || {});
function rail(active) {
  const counts = { gaps: (P.gaps || []).length, loop: D.cases.length, runs: (D.runList || []).length, auditor: (P.auditor || []).length, answer: (P.answers || []).length };
  const lv = P.levels || [], none = lv.length && lv.every(l => l.status === "NOT_SHOWN" && !(l.items || []).length);
  const lvl = none ? [h("span", { class: "pill p-mute", title: lv.map(l => l.level).join(", ") + ": no level self-assessment is recorded in this pack" }, "not evaluated in this pack")] : lv.map(l => h("span", { class: "pill " + (l.status === "VERIFIED" ? "p-good" : l.status === "NOT_SHOWN" ? "p-mute" : "p-warn"), title: l.level + ": " + (l.status === "NOT_SHOWN" ? (l.note || "not evaluated in this pack") : l.status) }, l.level.slice(0, 2) + (l.status === "NOT_SHOWN" ? " not evaluated" : "")));
  $("rail").replaceChildren(h("div", { class: "label grp" }, "Exhibit index"), ...ROUTES.concat(window.PROOFLAB_P1_ROUTES || []).map(([l, r, n]) => h("a", { href: "#/" + r, class: active === r ? "on" : "" }, h("span", { class: "ltr", "aria-hidden": "true" }, l), n, h("span", { class: "cnt" }, counts[r] ?? ""))),
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
  $("pParse").className = "parse" + (q && a && !a.route ? " err" : "");
  sel = Math.min(sel, Math.max(0, items.length - 1)); $("pList").replaceChildren(...items.slice(0, 8).map(([t, href], i) => h("li", {}, h("button", { class: i === sel ? "sel" : "", onclick: () => { follow(t, href); } }, h("span", {}, t), h("span", { class: "mono muted", style: "font-size:11px" }, href.split("/")[1]))))); $("pList").dataset.items = JSON.stringify(items.slice(0, 8)); }
function askServer() { const q = $("pIn").value; if (!q) return; api("/api/v1/ask?q=" + encodeURIComponent(q)).then(j => { lastAsk = { q, norm: j.meta.normalized, route: j.meta.route }; }).catch(e => { lastAsk = { q, norm: String(e.message), route: null }; }).then(renderPalette); }
function follow(text, href) { closePalette(); const a = lastAsk && lastAsk.q === text && lastAsk.route === href ? lastAsk : null; ASKED = a ? { key: decodeURIComponent(href.split("/")[2] || ""), norm: a.norm } : null; location.hash = href; }
function openPalette() { $("palette").classList.add("open"); $("pIn").value = ""; sel = 0; renderPalette(); $("pIn").focus(); }
function closePalette() { $("palette").classList.remove("open"); }
$("askBtn").onclick = openPalette; $("pIn").oninput = () => { sel = 0; renderPalette(); clearTimeout(askTimer); askTimer = setTimeout(askServer, 150); };
$("pIn").onkeydown = e => { const items = JSON.parse($("pList").dataset.items || "[]"); if (e.key === "ArrowDown") { sel = Math.min(items.length - 1, sel + 1); renderPalette(); e.preventDefault(); } else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); renderPalette(); e.preventDefault(); } else if (e.key === "Enter" && items[sel]) { follow(items[sel][0], items[sel][1]); } else if (e.key === "Escape") closePalette(); };
$("palette").onclick = e => { if (e.target.id === "palette") closePalette(); };
$("themeBtn").onclick = () => { const r = document.documentElement; r.dataset.theme = r.dataset.theme === "paper" ? "instrument" : "paper"; r.dataset.themeChosen = "1"; route(); };
/* PR-54: light ("paper") by default, dark ("instrument") when the OS asks for it, until the viewer clicks the toggle */
(function () { const r = document.documentElement, mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null; r.dataset.theme = mq && mq.matches ? "instrument" : "paper";
  if (mq && mq.addEventListener) mq.addEventListener("change", e => { if (!r.dataset.themeChosen) { r.dataset.theme = e.matches ? "instrument" : "paper"; if (P.pack) route(); } }); })();
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
  const rg = P.register || {}; $("regChip").textContent = "Register " + (rg.version || "not recorded") + (rg.sha256 ? " · " + String(rg.sha256).slice(0, 8) + "…" : ""); $("regChip").title = "threshold register " + (rg.version || "") + " sha256 " + (rg.sha256 || "not recorded");
  const fa = (P.answers || []).find(x => /\|run\|/.test(x.key)); if (fa) { const ex = "Show me control " + fa.control_ref.slice(1) + " for run " + fa.scope; $("pIn").placeholder = ex; $("askHint").textContent = "Ask the evidence — “" + ex + "”"; }
  if (P.pack && P.pack.title) document.title = P.pack.title + " · Evidence Console";
  window.addEventListener("hashchange", route); route();
  setInterval(() => api("/api/v1/cases").then(j => { if (JSON.stringify(j.data) !== JSON.stringify(D.cases)) { D.cases = j.data; if (location.hash.startsWith("#/loop")) route(); } }).catch(() => {}), 10000);
}
loadAll().catch(e => { $("main").replaceChildren(h("div", { class: "page" }, card("Console could not load", h("p", { class: "v-breach" }, String(e.message)))));});


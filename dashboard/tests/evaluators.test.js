// Run: node dashboard/tests/evaluators.test.js
const assert = require("assert");
const E = require("../evaluators.js");

let passed = 0;
function test(name, fn) { fn(); passed++; console.log("ok  " + name); }

const c16 = { observation_limit: { operator: "<=", value: 10000, unit: "tokens" }, exception_tolerance: { max_breaching_runs: 0 } };
const call = (run, id, i, o, extra) => Object.assign({ id, run_id: run, kind: "model_call", call_id: id, input_tokens: i, output_tokens: o }, extra || {});

test("C16 worked example: 9,600 satisfied", () => {
  const r = E.evalC16("FM-A", [call("FM-A", "c1", 5000, 1000), call("FM-A", "c2", 3000, 600)], c16);
  assert.strictEqual(r.verdict, "SATISFIED"); assert.strictEqual(r.measured.total_tokens, 9600);
});
test("C16 worked example: 10,800 breached, overshoot of 800 kept visible", () => {
  const r = E.evalC16("FM-B", [call("FM-B", "c1", 6000, 1000), call("FM-B", "c2", 3000, 800)], c16);
  assert.strictEqual(r.verdict, "BREACHED"); assert.strictEqual(r.measured.over_by, 800);
});
test("C16 exact boundary passes with <=", () => {
  assert.strictEqual(E.evalC16("R", [call("R", "c1", 9000, 1000)], c16).verdict, "SATISFIED");
  assert.strictEqual(E.evalC16("R", [call("R", "c1", 9000, 1001)], c16).verdict, "BREACHED");
});
test("C16 duplicate observation counted once", () => {
  const r = E.evalC16("R", [call("R", "c1", 4000, 0), Object.assign(call("R", "c1", 4000, 0), { id: "dup" })], c16);
  assert.strictEqual(r.measured.total_tokens, 4000); assert.strictEqual(r.population.duplicates, 1);
});
test("C16 under cap with a missing count is INDETERMINATE", () => {
  assert.strictEqual(E.evalC16("R", [call("R", "c1", 1000, 100), call("R", "c2", null, null)], c16).verdict, "INDETERMINATE");
});
test("C16 known subtotal over cap is BREACHED even with missing counts", () => {
  assert.strictEqual(E.evalC16("R", [call("R", "c1", 11000, 0), call("R", "c2", null, null)], c16).verdict, "BREACHED");
});
test("C16 no records is INDETERMINATE, never SATISFIED", () => {
  assert.strictEqual(E.evalC16("R", [], c16).verdict, "INDETERMINATE");
});
test("C16 objective: one of two runs over cap, none allowed", () => {
  const recs = [call("A", "a", 9000, 600), call("B", "b", 10000, 800)];
  const o = E.evalC16Objective(["A", "B"], recs, c16);
  assert.strictEqual(o.verdict, "BREACHED"); assert.strictEqual(o.breached, 1);
});

const c7 = { observation_limit: { coverage_min_pct: 100, gap_operator: "<", gap_limit_ms: 5 }, exception_tolerance: { max_violating_gap_pct: 10 } };
function c7Run(gaps, drop) {
  const events = []; const recs = []; let t = Date.parse("2026-10-05T10:00:00.000Z");
  for (let i = 0; i <= gaps.length; i++) {
    const id = "e" + (i + 1); events.push({ id, label: id });
    if (i > 0) t += gaps[i - 1];
    if (id !== drop) recs.push({ id: "r" + i, run_id: "R", kind: "event", expected_event_id: id, at: new Date(t).toISOString() });
  }
  return { recs, expected: { R: { source: "test", events } } };
}
test("C7 worked example: 11/11 events, 1/10 gaps at 8 ms is within 10%", () => {
  const { recs, expected } = c7Run([2, 3, 4, 2, 8, 3, 2, 4, 3, 2]);
  const r = E.evalC7("R", recs, expected, c7);
  assert.strictEqual(r.verdict, "SATISFIED"); assert.strictEqual(r.measured.violating_gaps, 1);
});
test("C7 second violating gap gives 20% and fails", () => {
  const { recs, expected } = c7Run([2, 3, 4, 2, 8, 3, 2, 6, 3, 2]);
  assert.strictEqual(E.evalC7("R", recs, expected, c7).verdict, "BREACHED");
});
test("C7 exactly 5 ms violates a strict < 5 ms rule", () => {
  const { recs, expected } = c7Run([5, 5, 2, 2, 2, 2, 2, 2, 2, 2]);
  assert.strictEqual(E.evalC7("R", recs, expected, c7).measured.violating_gaps, 2);
});
test("C7 missing middle event: coverage breach, its two gaps unmeasurable, never bridged", () => {
  const { recs, expected } = c7Run([2, 2, 2, 2], "e3");
  const r = E.evalC7("R", recs, expected, c7);
  assert.strictEqual(r.verdict, "BREACHED"); assert.strictEqual(r.measured.eligible_gaps, 2);
});
test("C7 zero expected events is NOT_ASSESSED", () => {
  assert.strictEqual(E.evalC7("R", [], { R: { events: [] } }, c7).verdict, "NOT_ASSESSED");
});

const c9 = { observation_limit: { operator: "<=", max_relative_increase_pct: 10 }, exception_tolerance: { max_violating_windows_pct: 0 },
             coverage_min_pct: 100, baseline: { rt: { value: 1000 } } };
const win = (id, v) => ({ id, runtime: "rt", start: "2026-10-05T0" + id + ":00:00Z", end: "2026-10-05T0" + id + ":59:59Z", value: v });
test("C9 one window at +12% with 0 allowed is BREACHED", () => {
  const r = E.evalC9([win(1, 1040), win(2, 1080), win(3, 1120)], c9);
  assert.strictEqual(r.verdict, "BREACHED"); assert.strictEqual(r.measured.violating_windows, 1);
});
test("C9 missing window is INDETERMINATE, not healthy", () => {
  assert.strictEqual(E.evalC9([win(1, 1040), win(2, null)], c9).verdict, "INDETERMINATE");
});
test("C9 all windows within limit is SATISFIED", () => {
  assert.strictEqual(E.evalC9([win(1, 1040), win(2, 1100)], c9).verdict, "SATISFIED");
});
test("C9 no windows is NOT_ASSESSED", () => {
  assert.strictEqual(E.evalC9([], c9).verdict, "NOT_ASSESSED");
});
test("Threshold must be dated before the run", () => {
  assert.ok(E.datedBefore({ version_date: "2026-10-05T12:00:00Z" }, { started_at: "2026-10-05T13:00:00Z" }));
  assert.ok(!E.datedBefore({ version_date: "2026-10-05T14:00:00Z" }, { started_at: "2026-10-05T13:00:00Z" }));
});

console.log(passed + " tests passed");

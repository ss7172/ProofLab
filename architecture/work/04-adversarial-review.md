# Adversarial review of the final architecture, through the judges' eyes (architecture input 04)

Written 2026-10-05, 23:00–23:45 UTC, by a read-only adversarial-review subagent.
- **Scope:** judging, design soundness and internal consistency. Infrastructure feasibility is out of scope; four other agents vet it.
- **No edits:** no architecture file was edited.
- **No live checks:** none was needed, and none was run.

**What was reviewed** (line numbers below refer to these copies; the quote is the anchor, because the main file was being edited during the review):

| File | sha256 (first 8) | Note |
|---|---|---|
| `architecture/ARCHITECTURE.md` | `ffb3d191` | Snapshot copied at 23:18Z, while another agent was adding risk and inventory sections (§2.5 present; §3.9, §3.10, §5.6 and D14 referenced but not yet written). "L" = a line of this snapshot |
| `architecture/one-page.md` | `bd0f5a85` | "one-page.md Ln" |
| `architecture/one-page.svg` | `6232bdc5` | Rendered with `rsvg-convert` at 1600 and 3200 px into the scratchpad, cropped and inspected |
| `architecture/decisions.md` | `fe34dbc3` | |

**Checked against:**
- `architecture/work/02-requirements.md` (R-J, R-P, R-C, R-D);
- `PLANNING-HANDOFF.md`;
- `notes/playbook/playbook-verification.md` ([PV row n]);
- `HACKATHON_WINNING_PLAYBOOK.md` §1 and §4;
- the masterclass slide text ([slides pN]);
- the Accenture lightning talk ([talk sN]);
- the kit's `register.yaml`, `evaluate.py` and `submit.sh` (`workshop-assets/starter/`);
- `prooflab/servicenow/finding.py` and `cli.py`.

**Re-checked at 23:28Z against newer versions.** Another agent kept editing all four files during the review:

| File | Newer sha256 (first 8) |
|---|---|
| `ARCHITECTURE.md` | `4b14bac4` |
| `one-page.md` | `99b33c87` |
| `one-page.svg` | `07c944df` (now 1600×1340) |
| `decisions.md` | `d9260a93` (now has D14) |

What changed:
- **The quotes:** every quote cited below is still present in those versions.
- **Line numbers:**
  - `ARCHITECTURE.md`: lines up to §3.8 are unchanged; later lines moved down by 121–197.
  - `one-page.md` grew from 136 to 148 lines, so its later citations shift by up to 12.
  - In both, search for the quote.
- **New material:** §3.9 (risk register), §3.10 (AI inventory), §5.6 (INV) and the sketch's new risk-and-inventory row.
  - They resolve G-01 and G-02, and narrow G-03 and G-12.
  - They add one new finding, I-23.
  - The sketch was re-rendered and re-inspected. E-08, I-01, I-03, I-14, I-15, S-01 and S-02 all still hold on it.

**Counts:** BLOCKER 0 · ERROR 12 · IMPRECISE 23 · GAP 11 open (+2 resolved during the review) · STYLE 6.

**Format of each finding:** Where · Quote · Why it fails (evidence and the judged criterion) · Fix.

**Why there is no BLOCKER.** Nothing here stops the entry being judged on its own. Two ERRORs become blockers if the schedule slips:
- **E-04:** the date proof needs both T1 and T2. One late ServiceNow write turns every verdict INDETERMINATE, which gives zero complete controls.
- **E-09:** the L1 gate's guardrail block and the only Rogue containment both sit at the end of the schedule, or in cut-first work.

Fix those two first.

---

## ERROR

### E-01 · "One evidence store" is not true for the platform's decisions (frame; R-P-02)
- **Where:**
  - §2.2 L151, §3.2 L521, §3.5 L631;
  - one-page.md L68;
  - SVG boxes "Evidence store: platform ledger" and "Evidence Pack";
  - decisions.md D8.
- **Quote:** "Platform decisions are **pulled** into raw captures, not copied into the ledger" (L151); "**Pulled records are not written to the ledger.**" (L521); "the ONE live store for OUR records" (SVG).
- **Why it fails:**
  - The frame says every decision is recorded "into one evidence store".
  - R-P-02 names the platform's decisions (Cedar, guardrails, pauses, admission) and asks for an append-only test on that store (R-P-02 (c)).
  - Here the platform's decisions live only in snapshot files on the laptop (`derived/observations.jsonl`). `prooflab refresh` rebuilds them, so they are not append-only.
  - The sketch draws two evidence boxes, and its own text limits the ledger to "OUR records".
  - A judge who asks "show me the Cedar DENY in your evidence ledger" hears "it isn't in the ledger".
  - L151 cites the lead's D8 reconciliation, so this is a conflict between the frame text and that reconciliation. The captain settles it; it is not a builder's mistake.
- **Fix (recommended, A):** `prooflab refresh` also appends each normalized platform observation to the ledger, with:
  - `record_kind: observation` and `authorship: PLATFORM`;
  - its deterministic `record_id` (the stitcher drops duplicates from re-pulls);
  - `phase: ifabric.observation`, so `score-run.py` is unaffected;
  - `source.refs` = the raw capture path, the line, and the sha256 of the raw line.

  The raw capture stays the authority, and the corroboration report checks that the copy equals the raw line. R-P-02 (b) and (c) then become literally testable. Reword L151, L521, L631, one-page.md L68 and the SVG box to "the ONE store for every decision: ours emitted at action time, the platform's appended by pull, each pointing at its raw capture".
- **Alternative (B):** name the Evidence Pack in the versioned team bucket as the one store, with the ledger as the live intake for our records. Neither team role holds `s3:DeleteObjectVersion` [PV row 15]. Then change every "the ONE live store" phrase and merge the two SVG boxes.
- Don't leave it halfway.

### E-02 · The second EP runs the tester, not the evaluator (Axis 2 question 1; the doc's own Decision ≠ Assessment rule)
- **Where:**
  - §11.1 L1440–L1452, §3.4 L575–L578, §1.2 L82;
  - decisions.md D6;
  - SVG evaluators box: "inline at EP-1, post-run at EP-2 = the 2nd EP, nothing rewritten".
- **Quote:** "EP-2: the post-run adapter … only observes" (L1442); "re-runs `c16.assess_run`" (L1452); "`c16.assess_run` over `aws/spans`" (L82).
- **Why it fails:**
  - EP-1 calls `decide_inline` and gets a `Decision`: that is the evaluator. EP-2 calls `assess_run` and gets an `Assessment`: that is the control test.
  - §3.2 types the two apart, citing R-J-55. Slide p13, by the masterclass speaker, separates "EVALUATOR judges the subject" from "TESTER judges the control".
  - So "the same evaluator, moved" holds only for the module and its `compare()` core. A judge asking "would it survive a second enforcement point?" in the slide's own vocabulary can take it apart.
- **Fix:**
  - At EP-2, normalize a run's model-call spans in gateway order. For each call, run `c16.decide_inline(C16Question(run, tier, committed=sum before the call, reserved=0, bound=that call's actual input + output), pin)`.
  - Emit each result as a `decision` record (`ep.id: EP-2`, `ep.transport: pull`, `inline.mode: observe-only placement`).
  - Then run `assess_run` (the tester) over the run.
  - The demo becomes literal: the same function, sha256 and pin at two EPs. N2's EP-1 decisions (observe) and its EP-2 replayed decisions agree call by call, with the first DENY on the same call.
  - The adapter diff stays `collectors/aws_spans.py` + `store/observations.py`.

### E-03 · The EP-1 adapter recomputes the limit (Axis 2 questions 3 and 4; the doc's own §2.4 test; slide p21)
- **Where:** §5.1 L926–L927.
- **Quote:** "limit = cap(tier) if mode == enforce else safety_ceiling" / "if committed + reserved + bound > limit: cancel the call".
- **Why it fails:**
  - The adapter makes its own threshold comparison instead of acting on `d`. That is verdict logic outside `prooflab/evaluators/`, which §2.4's own test forbids (L213: "verdict values are produced only in `prooflab/evaluators/` and `prooflab/recheck/`").
  - The comparison that actually halts work is never the evaluator's recorded output.
  - Slide p21: the EP "asks the evaluator 'is run FM-A still under cap?' and acts on the verdict".
- **Fix:**
  - `decide_inline` returns `Decision(verdict vs cap, limit_applied ∈ {cap, safety-ceiling}, halt: bool)`, using the pinned mode and both limits.
  - The adapter only runs `if d.halt: cancel`.
  - Add a CI check: no comparison of token quantities in `adapters/runtime/`.
  - Update the §5.1 pseudo-code and the stub tests to match.

### E-04 · The date proof needs both T1 and T2, so one late ServiceNow write turns every verdict INDETERMINATE (becomes a BLOCKER under slip)
- **Where:** §3.3 L569; §12.1 L1496; decisions.md D5.
- **Quote:** "An assessment is INDETERMINATE … unless both T1 and T2 are earlier than the run's first span time" (L569).
- **Why it fails:**
  - R-J-21 asks for "at least one timestamp we do not control".
  - T2 depends on a person and on ServiceNow ("Mechanism (pending Arth)", §3.3).
  - If T2 lands after 04:00 UTC, or never, every C16, C7 and C9 assessment is INDETERMINATE. That means no PASS and no BREACH, and Axis 1 = 0.
- **Fix:**
  - T1 is the required date proof: the S3 write-once object, whose `LastModified` and `VersionId` AWS sets.
  - T2 is corroborating. If it is earlier than the run, print "owner approval before run: yes".
  - If T2 is later or missing, keep the verdict, add a gap entry ("owner approval recorded after the run" or "missing") and state it under APPROVED.
  - Keep the "no assessed run before T1 and T2" hard line (L1496) as a process rule, not a verdict rule.
- **Later version:** §3.9 freezes `risks.yaml` in the same step, with the same T1 and T2 ("an owner's ServiceNow approval whose text names both sha256s"). The same single point of failure now covers the risk register too.

### E-05 · The judged `register.yaml` is dated after the C16 and C7 named runs (LOSE: "a threshold … dated after the test")
- **Where:**
  - §9.1 L1308, §3.3 L557, §5.4 L1066, §12.1 L1496–L1499, §4.2 L786;
  - kit `register.yaml` L42.
- **Quote:** "WORKDIR/ register.yaml (the latest frozen version …)" (L1308); "freeze `v1.1` with the C9 baseline values (C16 and C7 values unchanged)" (L1066); `threshold.version` = "Register version" (L786); kit `version_date: "REPLACE_WITH_YYYY-MM-DD"`.
- **Why it fails:**
  - `submit.sh` packages one threshold document, and it will be v1.1, frozen at 05:40–06:30.
  - The C16 runs (N1–N3) ran at 04:00–05:00 and the C7 runs (N4–N6) at 05:00–05:40, all under v1.
  - A judge reading the judged file sees version v1.1, dated later than six of the nine named runs.
  - The kit's `version_date` is a date, not a time, so every run on 2026-10-06 shares it anyway. "We check the date" can't be passed by reading the file.
- **Fix:**
  1. Give each control its own `threshold_version` (C16-v1, C7-v1, C9-v1.1) and its own `version_date` as a quoted full UTC timestamp, for example `"2026-10-06T03:52:10Z"`. The kit's fallback parser splits on the first colon only (`evaluate.py` L57–L59), so the timestamp survives. Change a control's two fields only when that control changes. The file-level `version`, `version_date` and `supersedes: v1` go before `controls:`.
  2. Records carry both `register.version` (the file) and `threshold.version` (the control).
  3. `query` prints the control's own date with its T1 proof.
  4. The README states which file version each named run used, and `register/versions/v1.yaml` stays in the pack.

### E-06 · There is no window evaluator for C16 or C7, yet the live test is "one control and one window" (Axis 2: the live test)
- **Where:** §3.4 L575–L586 (only `c9.assess_window` exists); §3.7 L711; one-page.md L88; slide p25.
- **Quote:** "Window roll-ups for arbitrary T1..T2 stay in the CLI" (L711); `prooflab query --control C16 --run <CID> | --window T1..T2` (one-page.md L88).
- **Why it fails:**
  - Either `query --control C16 --window …` has no verdict, or the CLI computes one. A CLI verdict breaks the §2.4 habit test (L213).
  - Undefined: runs under `v0-pilot` (no cap); BASELINE, adversarial and EXPLORATORY runs; runs bound to v1 vs v1.1; NOT_ASSESSED members.
  - The slides: "We name one control and one window and watch you produce the answer" (p25).
- **Fix:**
  - Add a pure `c16.assess_window(t1, t2, run_assessments, pin, as_of)`. It counts over-cap runs against `exception_tolerance`. The denominator is the runs whose bound version has a C16 entry; the others are listed NOT_ASSESSED, with a reason.
  - Add a pure `c7.assess_window` for coverage and violating-gap share across runs.
  - For mixed versions, test each run under its own bound version. The window is BREACHED if any run breached. It is INDETERMINATE if any in-scope run is INDETERMINATE and none breached. Otherwise it is SATISFIED.
  - Rehearse one window query per control (R-J-45).

### E-07 · The C9 rule is one-sided, and its only breach lever may move the metric the other way (Axis 1: C9 complete)
- **Where:** §5.3 L1017; §5.5 L1084; the models in handoff §7.1.
- **Quote:** "Limit: a relative increase over the baseline ≤ [D%] per runtime" (L1017).
- **Why it fails:**
  - The swap targets, `nemotron-nano-9b` and `nemotron-nano-3-30b`, are smaller than `super-120b`; the helper alias is the same super model.
  - The only nano-9b data (2 calls, 1.80 s and 6.67 s) does not settle the direction. A faster IT invocation is at least as likely as a slower one.
  - Under a one-sided "increase" rule, the swap then can't breach, and C9 drops out of Axis 1.
  - Choosing the rule's direction after seeing P8 would be "a threshold range chosen after seeing the result" [slides p10].
- **Fix:** pre-register these in the pilot plan, before P8:
  - **Two-sided drift:** |relative change| ≤ D%, justified by the harm. An unreviewed model change goes unnoticed (gap 5).
  - **M3 as a co-metric** (disposition-match rate):
    - it is the organisers' own suggestion: kit `register.yaml` L61, "a diagnostic-quality measure you recompute per run (e.g. disposition-match-rate …)";
    - it matches the slides' "relative drop" of a diagnostic score [slides p8, p19];
    - state that M3 is testimony while M1 is written by AWS.
  - **A declared "delay" condition** (ADV-H-03) in v1 as the fallback lever. It is then dated before any C9 run, and it also gives the Hostile "delays" category a live case.

### E-08 · The sketch shows the in-path question calling the off-path governance side (deliverable 5: "what sits in the path of execution")
- **Where:** `one-page.svg`; one-page.md L57 ("in process").
- **What the sketch shows:** the red arrow from `evaluate()` lands in "Stateless evaluators", inside the green dashed "GOVERNANCE SIDE · OFF THE PATH" region labelled "laptop hub · always async".
- **Why it fails:**
  - As drawn, the in-path C16 check makes a synchronous call to an evaluator on the laptop, which would put the laptop in the request path.
  - That contradicts §3.4 (a vendored copy inside each agent) and the sketch's own legend ("off the path, always async").
  - Showing what sits in the path is the sketch's first job [slides p26]. R-J-42 asks that the four architecture questions be answerable from the sketch alone.
- **Fix:**
  - Put a chip "c16.decide_inline · vendored · sha …" inside the EP-1 box, and end the red arrow there.
  - Join the evaluators box to that chip with a grey dashed line labelled "same module, same sha256".
  - Draw the post-run path that is missing: `pull()` → Pull adapters (EP-2) → evaluators, labelled "EP-2: same c16, post-run" (pairs with E-02).
  - Start the registry's dashed arrow on the registry box (S-01).

### E-09 · The cut lines put a gate item and the only Rogue containment last (L1 gate; R-J-37) (becomes a BLOCKER under slip)
- **Where:** §6.4 L1172, L1176, L1183, L1190; §12.1 L1501; §12.4 L1573, L1578.
- **Quote:** ADV-H-01 "Also the L1 'one guardrail block on record'"; ADV-R-01 "Required if D10"; P5 (cut first) "The Cedar `ifabric-` tool test"; ADV-R-08 "Optional (live lane)"; "containment: a Cedar DENY or a pause".
- **Why it fails:**
  - **L1 gate:** for our agents, the "one guardrail block on record" of R-J-01 (b) comes only from ADV-H-01. It runs at 07:20–08:15, after C9, and is not in P0. "A submission without this foundation will not be judged."
  - **Rogue containment:** R-J-37 (a MUST) needs "containment", yet both containment cases are cut-first or optional.
  - If the schedule slips, both disappear.
- **Fix:**
  - **ADV-H-01:** move it into P0 and run it straight after N1: one S1 with the attack text, a few thousand tokens.
  - **A Rogue containment case at P2:** pause the model the `ifabric-` trio uses, during a declared Rogue run. It needs no build; super-120b stops in ≤2 s [PV row 6]. Record the requested and effective times.
  - **The Cedar tool test:** keep it at P3 if the tool build fits.
  - **Order:** run the Hostile cases, then the Rogue cases, inside declared phase windows (I-11).

### E-10 · P0 and P1 disagree about the hook, and the hook is the pilots' only budget backstop (C16 first; R-C-07)
- **Where:** §12.4 L1573 vs L1574; §7.1 L1211; §5.4 L1050; §12.3 L1560.
- **Quote:** P0 keeps "Agents at Stage A (emission + the hook)", but its fallback reads "Without EP-1 inline … N2 runs with no guard"; P1 lists "EP-1 inline (`enforce` / `observe`)"; the budget line reads "Pilots (the S2 and condition pilots are bounded by the safety ceiling)".
- **Why it fails:**
  - The safety ceiling exists only inside EP-1. Without it, pilots P5–P7 and N2 run S2-type loops unguarded.
  - The reference S2 used 2.0M tokens, 80% of the account's hourly ceiling, in under 5 minutes [gap 8]. That would stall the live lane for about an hour at the worst time.
  - The doc puts the hook in P0 and in P1 at once.
- **Fix:**
  - P0 = the hook in `observe` with the safety ceiling, as the backstop for every S2-type run.
  - P1 = `enforce`, N3 and live `tail`.
  - If even the hook is cut, write down now that N2 uses lever (b) under a live-lane pause trigger at a declared tally, and that no natural S2 run goes ahead without a guard.

### E-11 · The C16 bound can under-estimate, so the closing re-test N3 can itself breach
- **Where:** §5.1 L923, L953, L1082; [03 F5].
- **Quote:** "bound = (projected_input_tokens or last call's input tokens or the declared fallback) + max_tokens" (L923).
- **Why it fails:**
  - `projected_input_tokens` is "None if estimation failed" [03 F5], and it is a heuristic estimate for a model that doesn't use OpenAI's tokenizer.
  - The fallback, "last call's input", is low by construction in a Strands loop: each call's input is the last input plus the last output plus the tool results.
  - So the last call allowed can push the committed total over the cap, and the floor then reads N3 as BREACHED.
  - The finding can't close (LOSE: "closed without a passing re-test" is avoided only by leaving it open), and the inline-bonus demo shows an overshoot.
- **Fix:**
  - bound = max(projected, last input + last output + tool-result tokens since) + `max_tokens`, plus a register-declared `inline_bound_margin_pct`.
  - Measure the projection error in the stub and smoke runs (OC-1), and freeze the margin in v1.
  - Stamp `bound_basis` on each decision.
  - The floor prints committed − cap for every `enforce` run.

### E-12 · Incidents outside our run ids never reach the pack (the six questions, "for any incident in the window")
- **Where:** §3.1 L316 (EP-2 "by run id"), L365 (EP-6 "by CID"); §8 L1293, L1297 ("per run"); §15.2 L1659.
- **Quote:** "A Logs Insights query on log group `aws/spans` by run id" (L316); "`aict-invocations` (7-day retention): per run" (L1297); "who injects them, and when, is unknown" (L1659).
- **Why it fails:**
  - Judges "pick an incident from your event window" [kickoff p7 via handoff §2.5].
  - None of these reaches a per-CID pull: an invocation of our runtimes without our envelope, a change to an `ifabric-` AgentConfig, or another caller using our tool.
  - What our agents do when invoked without an envelope is undefined.
  - R-J-28 requires that any CID or time a tester picks resolves.
- **Fix:**
  1. On each refresh, sweep the whole window:
     - the ledger's all-records read (already done);
     - `aict-invocations` for our three runtime ARNs;
     - the generation history of the `ifabric-` CRs;
     - `/modaas/evidence` for our tool's route.
  2. Every CID found there but missing from the run index gets the same per-CID pulls, with provenance `UNATTRIBUTED`.
  3. An `InvokeAgentRuntime` with no matching `handoff.sent` becomes an incident under the pseudo-CID `unattributed:<runtime>:<time>`.
  4. An agent invoked without an envelope mints `ifabric-unenveloped-<epoch>-<hex>`, applies the strictest tier, and emits as normal.

---

## IMPRECISE

**I-01 · EP-0 contradicts "Only ONE question may make work wait"**
- **Where:** one-page.md L9 and the SVG's top-right headline; §7.2 L1254–L1258 and L1266; §5.0 L900.
- **Quote:** "The only refusal is inside the agents (C16)" (L1266). The preflight steps (L1254–L1258) don't list EP-0, though §3.1 says EP-0 runs in the preflight.
- **Why:** with D13 = block, EP-0 refuses to start ASSESSED runs, which makes the headline and L1266 false. The frame limits in-path questions, and EP-0 runs before the path. The slides support a refusing gate: p13 lists "A release or admission gate that can refuse" under BEFORE, and p7's model control is "approved by a named person, and the work stops if it is not".
- **Fix:**
  - Headline: "Only ONE question sits in the live path: the C16 check before each model call. Before a run, a go/no-go gate (EP-0) may refuse to start it [slides p13]."
  - Add EP-0 to §7.2 step 1.
  - L1266: "…or refuse anything inside a run; before an ASSESSED run, EP-0 may refuse to start it (D13)."
  - Recommend D13 = block assessed runs.

**I-02 · C7 double-counts C16 decisions in observe mode**
- **Where:** §5.2 L990.
- **Quote:** "one per span, plus one per DENY (a DENY has no span)".
- **Why:** in `observe` mode a DENY call is still served, so it has a span. N2 then expects two decisions for each over-cap call and finds one, which shows a false C7 breach on the C16 BREACH run.
- **Fix:** "plus one per cancelled call (`outcome.real: CANCELLED_C16`)".

**I-03 · `callback()` is polling, and `notify()` is not a callback**
- **Where:** §3.8 L721; one-page.md L82 and L114; SVG ServiceNow box; L1479.
- **Quote:** "`notify()` = `callback()`".
- **Why:** `notify()` is the outbound request. The verdict comes back through `check` polling, because no inbound endpoint is allowed (R-P-07). Slide p15 defines `callback()` as "a webhook for a verdict that arrives later".
- **Fix:**
  - "notify() raises the request; the owner's verdict returns through callback(), realised by `check` polling, since no inbound endpoint is allowed (R-P-07)."
  - Modes row: "C9 → pull(); alert by notify; response by callback()".

**I-04 · The pin's integrity check is undefined, and the env block is incomplete**
- **Where:** §3.3 L555 and L560; L923; L1236, L1270; §3.6 L664.
- **Quote:** "the sha256 doesn't match the embedded copy" (L560).
- **Why:**
  - No embedded copy is defined, and a sha256 can't be checked against caps without the file's bytes.
  - The `registry pin` env block (L555) lacks `IFABRIC_DECLARED_FAULTS` (which L1236 and L1270 rely on), the bound fallback and `max_tokens` (L923).
  - The stitcher's "declared tolerance (default ±5 s)" (L664) is a code default that moves C7 link gaps.
- **Fix:**
  - Env carries `IFABRIC_REGISTER_B64` (the frozen file) and `IFABRIC_REGISTER_SHA256`.
  - Every in-path value is parsed from those bytes at start-up: caps, modes, safety ceiling, declared faults, bound policy, `max_tokens`.
  - `registry pin` sets only the bytes, the sha256 and the chosen mode.
  - Add a register key `join_tolerance_s`.
  - The control test checks each decision's `threshold.value` against its frozen version.

**I-05 · N2 can't "cross C9"**
- **Where:** §5.3 L1041.
- **Quote:** "The C16 observe-mode breach run (N2) will probably also cross C9".
- **Why:** N2 runs under v1, which has no C9 baseline; v1.1 is frozen later (L1066). So C9 is NOT_ASSESSED for N2.
- **Fix:** say so. A long run shows up in C9 only under v1.1 (for example ADV-H-04).

**I-06 · "Restarts the protocol" contradicts the declared model swap**
- **Where:** §5.4 L1049, against N8 (L1084) and §7.1 L1241.
- **Quote:** "A later agent change (image or model) is a new treatment and restarts the protocol".
- **Fix:** "an undeclared agent change".

**I-07 · EP-5 is not emit-only in §6.1**
- **Where:** §6.1 L1114. The row's transport is "`emit` / `pull`", and its guard includes "approval older than the running generation".
- **Why:** the staleness check is EP-10's job, and the frame makes handoffs emit-only.
- **Fix:** EP-5's row = `emit` only; move the staleness check to EP-10.

**I-08 · The end-of-invocation flush holds the response on the ledger**
- **Where:** §3.2 L516.
- **Quote:** "a flush of at most 2 s runs after the result is computed. It gates no action."
- **Why:** the flush delays the `InvokeAgentRuntime` response, and so the next handoff, while the ledger is written. Slide p14: "OFF THE PATH, ALWAYS ASYNC: telemetry · ledger · register".
- **Fix:** return first and drain afterwards, or rely on the stdout spool plus reconciliation. If the flush stays, declare it in §2.3 ("a bounded ≤2 s best-effort flush; it never fails the call") and report its p99.

**I-09 · The kit cross-check fails on our pack**
- **Where:** §3.3 L548.
- **Quote:** "so the kit's own `evaluate.py 16` can still run as a cross-check".
- **Why:** the kit's evaluator reads `gateway-log.json` (`modaas.run_id`, `gen_ai.usage.*`; `evaluate.py` L67–L75, L85–L99), and the §9.1 layout has no such file. A judge who runs the organisers' tool on a named run gets NO EVIDENCE (exit 2).
- **Fix:** write `evidence/gateway-log.json` in the kit's shape from `aws/spans` (model calls, all runs) and add `python3 evaluate.py 16 <CID> --evidence-dir evidence --register register.yaml` to the README. Otherwise, drop the claim.

**I-10 · Tiers vs "the same threshold"**
- **Where:** §5.1 L965; §5.5 L1082 (N1 = S1, N2 = S2); §3.4 L578 (`tier` is an input to `assess_run`).
- **Why:**
  - If S1 and S2 fall in different tiers, the PASS and BREACH runs face different caps under one version, which reads as "moving the threshold".
  - The floor also takes the tier on trust from the envelope.
- **Fix:**
  - Pick a named pair within one tier, or name a pair per tier.
  - `assess_run` derives the tier itself, from the declared scenario attributes with the frozen `tier_rule`, and records any mismatch with the envelope.

**I-11 · How a run gets its phase (Alert 0, 1 or 2) is undefined**
- **Where:** §3.7 L693; §9.1 L1311.
- **Why:** ADV-R-05 (= N3, L1180) and ADV-R-10 (= N4, L1185) run in the C16 and C7 blocks (L1497–L1498), not in a Rogue window.
- **Fix:**
  - Declare the phase boundaries in the run index before the runs; a run's phase is its declared label.
  - Run the Hostile cases, then the Rogue cases, inside their windows.
  - Tag N3 and N4 with both their control role and their ADV id.

**I-12 · INTEGRITY covers named runs only**
- **Where:** §9.2 L1338.
- **Quote:** "A cross-surface corroboration report per named run".
- **Why:** the six questions apply to any incident in the window.
- **Fix:** produce the report for every CID in the run index. It is derived from the stitcher, so it needs no new pulls.

**I-13 · The `run-ids.txt` format differs from the kit's**
- **Where:** §5.5 L1094: `<control> <PASS|BREACH|RETEST> <CID> …`, against `submit.sh` L23–L24: "one run id per line".
- **Fix:** one CID per line in `run-ids.txt`; put the rest in `evidence/named-runs.md` and the README.

**I-14 · "Our only code in the path"**
- **Where:** one-page.md L21; the SVG runtime header.
- **Why:** the orchestrating script is ours too, it is drawn blue, and it sits in the live path.
- **Fix:** "our only code in the model-call path" [handoff §5.9].

**I-15 · The sketch states pending or unbuilt items as fact**
- **Where:** one-page.md L34 and the SVG.
- **What:**
  - "We configure one forbid rule" (one-page.md L34), though D10 is pending and the tool is cut first;
  - every "built" cell in the SVG's modes and EP-kind strips.
- **Fix:** write "(if D10)", and generate the status cells from the gate records when the sketch is rendered (W10).

**I-16 · The C7 breach may not breach**
- **Where:** §5.5 L1083.
- **Quote:** "drops that one record … → coverage < C%".
- **Why:** if C% is below 100%, then whenever (|E|−1)/|E| ≥ C% the run is SATISFIED.
- **Fix:** declare a fault size k > (1 − C%)·|E|, or justify C% = 100% from risk. Check it in the pilots.

**I-17 · Provenance vs "assessed"**
- **Where:** §5.0 L898 ("ASSESSED runs (provenance `LIVE_SUBJECT`)"); L804 lists FAULT_INJECTION and AUTHORIZED_TEST.
- **Why:** N2, N4 and N8 each carry a declared lever, so their provenance, and therefore whether EP-0 and the assessments treat them as assessed, is ambiguous.
- **Fix:**
  - Every named run is `LIVE_SUBJECT`, with its `run.condition`.
  - "Assessed" = listed in `run-ids.txt`.
  - Adversarial runs keep their provenance and are assessed and labelled.

**I-18 · A human can close an incident in ServiceNow**
- **Where:** §3.8 L738 says a finding closes only through a re-test.
- **Why:** the owner can still set the incident Closed inside ServiceNow, and the export would then show a closed incident with no passing re-test.
- **Fix:** the owner responds and never resolves. `export` compares the incident state with the re-test link and records "closed in ServiceNow without re-test" as a gap.

**I-19 · `v0-pilot` has no cap**
- **Where:** §5.4 L1050 ("It carries only the safety ceiling"); §5.1 L961.
- **Why:** `decide_inline` has no cap to compare against. Under L961 ("exception → DENY `evaluator-error`") every pilot decision becomes noise.
- **Fix:** return NOT_APPLICABLE when the pinned version has no C16 cap, or set cap = the safety ceiling in `v0-pilot`, labelled as such.

**I-20 · EP-4 is not a passage**
- **Where:** §3.1 L334, "EP-4 · Agent judgment".
- **Why:** slide p12: "A component is not an enforcement point, a passage is"; R-J-52 asks that such things be labelled observers.
- **Fix:** rename it "J-4 judgment record (an emit source, not an EP)", or map it to the slide-12 "Planner" passage and say why.

**I-21 · The second-EP diff can't be shown as described**
- **Where:** §11.1 L1451.
- **Quote:** "Proof: `git diff --stat` between the two wirings".
- **Why:** W1 and W4 build both wirings in parallel, so there is never a one-EP state to diff against.
- **Fix:** land EP-2 (P0) first. Land EP-1 in its own PR that touches only `adapters/runtime/` and the vendored copies, and cite that PR's sha and diffstat.

**I-22 · APPROVED after env-setting patches**
- **Where:** §7.1 L1241; OC-12.
- **Why:** mode switches and fault pins change the CR generation. The approval annotation then predates the running generation, and EP-10 will flag N3, N5 and N9 as stale.
- **Fix:** the APPROVED answer treats "CR approval (generation g) + the owner's recorded OK for the declared EP-setting change (generation g+1)" as approved, and says so. Alternatively, re-approve after each patch.

**I-23 · The sketch states the EU AI Act tier as fact (new in the 23:28Z version)**
- **Where:** `one-page.svg` (07c944df), AI inventory box; one-page.md (99b33c87) L84; ARCHITECTURE §3.9, §3.10 and OC-21.
- **Quote:** SVG: "tier: high-risk (EU AI Act; the network agent)". one-page.md (99b33c87) L84: "source: the team playbook, unverified against a primary source". §3.10: "UNVERIFIED against a primary source (OC-21)".
- **Why:**
  - The judged image drops the qualifier that the text version and the main document keep.
  - The likely judge is a GRC specialist. "High-risk because of critical infrastructure" for a home-internet fault agent is easy to challenge, and the only source is our own restatement.
- **Fix:** on the SVG, write "risk tier: high (our 5×5 rating); EU AI Act category unverified (OC-21)". Better still, show only our own rating on the sketch and keep the Act category in the doc.

---

## GAP

**G-01 · Risk register and AI inventory: RESOLVED during the review (23:28Z version)**
- **What landed:** §3.9, §3.10, §5.6, D14 and the sketch's new row.
- **What they now cover:**
  - risk ids per control, with a CI test that each control has a risk;
  - appetite → threshold derivation;
  - one 5×5 matrix shared with `tier_rule`;
  - both files frozen with T1 and T2;
  - inventory versions that include N8's treatment;
  - `RiskState` kept apart from the verdict vocabulary;
  - a slot on the sketch;
  - INV built only after C16, C7 and C9.
- **What remains:** E-04 (the T2 dependency, now doubled) and I-23 (the tier on the sketch).
- **The frame still holds after the additions:**
  - §3.9, §3.10 and §5.6 add no in-path question;
  - the risk and inventory files are joined off the path;
  - INV never blocks anything;
  - EP-0 reads the inventory only before a run.

**G-02 · Risk acceptance: RESOLVED during the review**
- §3.9's loop, step 3, defines an acceptance as an `approval` record with approver, expiry and finding id.
- It changes how the risk is shown and never the finding's state, and nothing but a passing re-test closes a finding [slides p8; R-J-24].

**G-03 · The Finding contract has no field for the deficiency (design, operation or both)**
- **Status:** narrowed. §3.9's loop, step 1, now says "the finding says whether the deficiency is in design, in operation, or both".
- **Why it is still open:** `finding.py` REQUIRED_FIELDS (L21–L22) has no field for it, and nothing says where it goes [slides p8; R-J-57].
- **Fix:** put it in the summary prefix ("deficiency: operation") and a work note, derived from `Assessment.design` and `Assessment.operation`. Test it in `publish()`.

**G-04 · No roles table**
- **Why:** R-D-02 requires one, and §15.2 L1658 says "A roles table names the vacancy", but there is no table.
- **Fix:** add a four-role table, plus a gap-list entry for the vacancy:
  - accountable management: Sree;
  - GRC: unnamed;
  - operations: Sree and the fleet;
  - assurance: Arth, or vacancy.

**G-05 · The control tests miss two of slide p20's checks**
- **C16, "check stop records":** `aws/spans` shows no model span after an `enforce` DENY in that invocation. That is AWS-written proof that the halt halted.
- **C9, "check monitoring and alert response":** every crossing has a DELIVERED alert to the named owner, and a response or silence.
- **Fix:** put both into `Assessment.operation`.

**G-06 · The adversarial log has no case that shows "what we changed"**
- **Why:** R-J-19 and R-P-25 require at least one case with a break, a change and a passing re-test. ADV-R-06 (L1181) is "expected to break", and nothing changes after it.
- **Fix:** the change is a `reconciliation` finding raised when the inline tally differs from the floor by more than a declared tolerance. The re-test repeats `--tamper-tally` and shows the finding raised.

**G-07 · No recorded L1→L3 demo**
- **Why:** R-J-45 requires one, and §12.1 has no step for it.
- **Fix:** record it during the 10:00–12:30 rehearsal. Keep the N3 `tail` view as the "recorded, not live" fallback (L1660).

**G-08 · EP-0's decisions are missing from C7's expected events**
- **Where:** `workflow_events`, L985–L995.
- **Fix:** add three `ep0.decision` events per run when D13 is on.

**G-09 · Two enforcement points have no adapter**
- **Where:** L450–L453: the ledger's token gate and the runtime's IAM deny, against the frame's "adapters around every enforcement point".
- **Fix:** add a minimal pull (CloudTrail AccessDenied events for the runtime role, if readable), or one dated "not crossed in the window" observation per EP.

**G-10 · The C16 breach lever works against J2**
- **Why:** the better the judgment (Stage B, the pillar), the less likely S2, or S2 with the conflicting-context condition, is to exceed a risk-based cap (L1082). C16 is P0.
- **Fix:** pre-register a third declared condition in v1 (for example an exhaustive-verification instruction), measure it in P7, and write the rule for choosing the lever before the pilots.

**G-11 · Pack hygiene for judges**
- **What ships today:**
  - L1328 ships the working `ARCHITECTURE.md`, with its pending-captain labels, overnight schedule and token budgets;
  - `prooflab/servicenow/cli.py:28` sets `DEFAULT_OWNER` to a personal email address, and `prooflab/` ships in the pack (L1314);
  - the exact-value scan looks for secrets, not personal data.
- **Fix:**
  - Ship a judge-facing `architecture.md`, or the one-page plus `decisions.md`, and keep the working file out.
  - Override `DEFAULT_OWNER` in the staged copy, and add an email pattern to the pre-upload scan.

**G-12 · Out-of-scope traffic in the window has no answer path**
- **Status:** narrowed. §3.10's `scope_rule` now declares the reference trio and other teams' assets out of scope.
- **What's still missing:**
  - the README doesn't carry that statement;
  - `query --incident` has no defined answer when a judge picks an out-of-scope CID, or a `modaas-docs` handshake (about 15 an hour [handoff §3b Q16]).
- **Fix:** answer "out of scope (scope_rule, inventory version …)", with what was seen.

**G-13 · The C9 baseline is thin where it matters**
- **Where:** §5.3 L1016 plans two baseline runs per scenario.
- **Why:** N7, N8 and N9 are all S1, so the PASS/BREACH band rests on n = 2.
- **Fix:** spend the six baseline runs on S1 (or 4 S1, 1 S2 and 1 S3), and state n in `why_value`.

---

## STYLE

**S-01 · The registry arrow is unanchored.** The dashed "pinned copy" arrow starts at the governance-side border, not on the registry box. Anchor it on the box and label it "pinned at deploy, before the run".

**S-02 · The legend is incomplete.**
- The SVG legend lacks orange (the stores), teal (the control test), brown (the habits) and the PRE/CONT/POST chips; one-page.md L136 lists the chips.
- The Evidence Pack box lacks the POST chip that one-page.md L70 gives it.

**S-03 · The sketch is dense.**
- At 6232bdc5 it had about 1,190 words in 234 text runs, mostly 12 px. At 07c944df it has about 1,410 words in 271 runs, on 1600×1340.
- The bottom quarter repeats the chips.
- **Fix:**
  - Cut about 40% of the text.
  - Render at `-w 3200`: one-page.md L5 says 1600, where the 12-px text is hard to read.
  - Stamp the sketch with the register version, git sha and date, so it binds to the pack like every other artefact.

**S-04 · The example records disagree with the plan.** L837 shows `threshold.version: v1.1` at 04:31Z, when the plan pins v1, and the envelope at L1250 says v1. Use v1.

**S-05 · The honest failure reads as staged.** ADV-R-06 is a limit announced in advance. If an unplanned failure happens, lead with it (candidates: OC-10 structured output, the C9 lever, the projection leak) and keep ADV-R-06 as the adversarial case.

**S-06 · One habit test proves nothing for the runtime.** L215's "make the register file unreadable after start" can't fail there, because the runtime never reads a file. Write "registry and file unavailable after start → identical decisions", and run it on the vendored agent with the stub model.

---

## The attack angles, answered

### 1 · The Axis-2 architecture questions
| Question (verbatim) | Holds? | Why | Findings |
|---|---|---|---|
| "Would it survive a second enforcement point?" | Partly | The same module and sha256 run at EP-1 and EP-2, but EP-2 runs the tester, not the evaluator; the diff proof can't be produced as described; the sketch doesn't draw the EP-2 flow | E-02, I-21, E-08 |
| "Is the register out of the live path?" | Yes | Env pin at deploy; no registry read in any request path; mismatches recorded, pin wins | I-04 (integrity check), S-06 |
| "Is the evaluator stateless?" | Yes for `evaluators/`; no for the adapter | Pure functions with `as_of` passed in; but the adapter re-decides the halt | E-03 |
| "Does the control hold its own threshold?" | Yes, with gaps | No literals, values only in the register, version and sha256 stamped; but the bound fallback, `max_tokens` and the join tolerance sit outside the register, and the pin can't be checked against the file | I-04 |

### 2 · The LOSE list
| LOSE item | Exposure | Findings |
|---|---|---|
| Threshold undated or dated late | **High**: the judged file is v1.1, dated after six of the nine named runs; the date-only kit field; the both-T1-and-T2 rule | E-05, E-04 |
| Records covering only some governed actions | Medium: unattributed invocations; C7's observe-mode double count | E-12, I-02 |
| Evidence only we can verify | Low: raw captures, queries and the rechecker; the kit cross-check is broken | I-09 |
| Finding closed without a passing re-test | Medium: N3 may overshoot; a human may close the incident | E-11, I-18 |
| A control that stores its own threshold | Low | E-03, I-04 |
| A design that only works in the request path | Low: the floor holds with inline off; the 2-s flush wording | I-08 |

### 3 · The six questions from the pack alone, offline
| Incident picked | WHO | WHAT | AUTHORIZED | APPROVED | INTEGRITY | RECONSTRUCT |
|---|---|---|---|---|---|---|
| A named run (e.g. N2) | Yes (gap 2 stated) | Yes | Yes, real outcome beside the platform's ALLOW | Yes; stale after a mode patch | Yes | Yes |
| Hostile ADV-H-01 | Yes | Yes | Yes (BLOCKED vs ALLOW) | Yes | **No report** | Yes |
| Rogue ADV-R-01 (Cedar) | Only if D10 and P5 survive | Same | DENY from both PDP replicas | Tool approval | **No report** | Yes |
| Rogue ADV-R-08 (pause) | Yes | Yes | PAUSED_404 via the trace-id join | Yes | **No report** | Yes |
| A pilot run | Yes | Yes | Yes | Yes | **No report** | Yes |
| Organiser-injected, or a call without an envelope | **No** | **No** | Partial | Partial | **No** | **No** |

Notes on the table:
- Stale after a mode patch: I-22.
- **No report:** I-12.
- Organiser-injected or unenveloped: E-12.
- The phase labels that let a judge pick "a Hostile or Rogue incident" are undefined: I-11.

### 4 · Axis 1, end to end, and the cut lines
| Control | Complete if… | Main risk | Findings |
|---|---|---|---|
| C16 (P0) | A breach lever works and N3 stays under the cap | No natural breach once J2 works; N3 overshoot; no hook in P0 | G-10, E-11, E-10 |
| C7 (P2) | The fault size beats C% | One dropped record may not breach; observe-mode double count | I-16, I-02 |
| C9 (P3) | The swap moves a declared metric | One-sided rule; n = 2 | E-07, G-13 |
| L1 gate, Rogue containment | They are scheduled early | Both sit at the end or are cut first | E-09 |

### 5 · Internal consistency (doc vs one-page vs decisions)
Contradictions found:
- EP-0 vs the headline and §7.2 (I-01);
- the one store vs two evidence boxes (E-01);
- "same evaluator" vs Decision ≠ Assessment (E-02);
- P0 vs P1 on the hook (E-10);
- §5.4 step 2 vs N8 (I-06);
- §6.1 EP-5 vs §3.1 EP-5 (I-07);
- the §3.3 env block vs §7.1 and §7.2 (I-04);
- N2 crossing C9 vs the sequencing (I-05);
- the example record version vs the plan (S-04);
- "our only code in the path" (I-14);
- `notify()` = `callback()` (I-03).

`decisions.md` matches the doc's D1–D13 rows except where a finding above changes one: D5 (E-04), D6 (E-02), D8 (E-01) and D13 (I-01).

### 6 · One-page legibility (rendered and inspected)
**What works in 30 seconds:**
- the three bands: live path, contract, governance side;
- the red EP-1 box;
- the red headline;
- the four transport pills.

**What fails** (still true at 07c944df):
- the in-path arrow lands in the off-path laptop region (E-08);
- the second EP appears only as text inside a box, with no flow (E-08, E-02);
- two "evidence" boxes contradict "one store" (E-01);
- the registry arrow is unanchored (S-01);
- 1,410 words at 12 px (S-03);
- the EU AI Act tier is shown as fact (I-23).

**What the 23:28Z version adds well:** the risk and inventory row, with "appetite → thresholds" and "decide the risk first, derive controls". It answers the likely judge's own rule [talk s11].

---

## Verdict

The design is sound and close to the masterclass pattern. Its honest labelling stands out:
- observers are named as observers;
- INDETERMINATE is never shown as a pass;
- the floor stays authoritative;
- the dashboard is presented as a view.

It already answers most of what the judges will ask. It is not yet safe to present, for three reasons:
1. **Two headline claims don't survive a precise reading:** "one evidence store" and "the same evaluator at a second EP". These are the Axis-2 questions the judges ask word for word.
2. **The dating and window mechanics can trip LOSE items:** "dated after the test", and the live "one control, one window" test.
3. **The breach levers and the cut lines leave C9, the L1 guardrail block and Rogue containment exposed.**

None of the twelve ERRORs needs a new component. Most need a wording, schema or function-signature change. Only E-12 (the window sweeps) and E-09 (rescheduling) add live or build work.

**Ship after the ERRORs; take E-04 and E-09 first.**

## The three highest-value improvements
1. **Make the two headline claims literally true, and redraw the sketch around them.**
   - Append the platform's normalized observations to the ledger, each with the sha256 of its raw line (E-01).
   - Replay `c16.decide_inline` per gateway call at EP-2, and make the EP-1 adapter act on `d.halt` (E-02, E-03).
   - On the sketch, end `evaluate()` inside the agent and draw the EP-2 flow to the evaluator (E-08).
2. **Make dates and windows unbreakable.**
   - T1 alone satisfies "dated before"; T2 corroborates, and a late T2 becomes a gap (E-04).
   - Each control gets its own `threshold_version` and a full UTC `version_date` in the judged `register.yaml` (E-05).
   - Add pure `c16.assess_window` and `c7.assess_window`, with defined denominators across versions (E-06).
3. **De-risk the breach levers and cut lines before the pilots.**
   - Pre-register a two-sided C9 rule, M3 as co-metric and a declared-delay fallback (E-07).
   - Make the C16 bound conservative, with a declared margin (E-11).
   - Move ADV-H-01 into P0, right after N1, and make one Rogue containment case (the model pause) P2 (E-09).
   - Put the hook with its safety ceiling in P0 (E-10).

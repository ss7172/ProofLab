# 04b · Independent architecture review (second reviewer, 2026-10-05)

Saved verbatim by the lead from the reviewer's report; the reviewer wrote no file. Keys: A = `architecture/ARCHITECTURE.md`, D = `decisions.md`, OP = `one-page.md`, SVG = `one-page.svg` (source line). Line numbers refer to the versions current at about 23:00Z. Re-locate them by quote if the files have moved.

## Frame verdict

No hard frame violation:
- EP-1 is the only caller of `evaluate()` (A:419, 470).
- The cap comes from an env pin, so nothing in the path reads the registry.
- Handoffs are emit-only, and the next agent is always invoked (A:308).
- Platform decisions are pulled, not copied into the ledger (A:479, 582).
- The reference trio is not assessed, and PASS and BREACH both run on the `ifabric-` trio.

Two items are borderline (B1, B2). About 110 citations were spot-checked (every cited slide page, F1–F11, D1–D12, the R-ids, handoff and SN sections, the kit). All hold except the mis-cites listed in C.

## A. MUST-FIX

- **A1** A:534–544, 636–637.
  - **Problem:** only C9 has a window assessment; C16 and C7 have `assess_run` only. The judged live test is "one control and one window" (slide p25; R-J-10b). OP:88 and SVG:239 advertise `--window` for C16, and C16's "0 over-cap runs" tolerance only means something across several runs.
  - **Fix:** add `c16`/`c7.assess_window`: pick runs by provenance and condition, and test each run under its own version when a window spans v1→v1.1. Add the CLI rows.
- **A2** A:1255 with 1013, 1027–1031.
  - **Problem:** the judged WORKDIR `register.yaml` is the latest version (v1.1, frozen around 06:30), but the C16 and C7 named runs (04:00–05:40) are under v1. A judge sees a date after N1–N6, which reads as the mark-loser "dated after the test". §3.3 has both a file-level and a per-control version and date, with no rule between them, and A:784 stamps a 04:31Z C16 decision `v1.1`.
  - **Fix:** version per control. In v1.1 the C16 and C7 entries keep `threshold_version: v1` and v1's date, and records stamp the per-control version.
- **A3** A:1201–1213.
  - **Problem:** §7.2 says the script never refuses anything ("The only refusal is inside the agents"), and its preflight steps leave out EP-0. A:258 puts EP-0 "inside `prooflab run`", A:845 says "the run is not started", and D:22 repeats the C16-only line.
  - **Fix:** add EP-0 to the preflight steps, and reword to "nothing inside a run waits; EP-0 (D13) may decline to start an assessed run".
- **A4** A:224.
  - **Problem:** `systems.py (ifabric / reference payload adapters)` is stale from the old D9, as are "system" in `run.started` (A:314) and in `query --runs` (A:640). This contradicts A:17, 1020 and 1500 (no reference re-run), and invites the W3 worker to build a reference driver.
  - **Fix:** delete them.
- **A5** A:988.
  - **Problem:** it says N2 "will probably also cross C9 … the pack says so". But N2 runs under v1, which has no C9 baseline; v1.1 is frozen after it (A:1446), and A:521 tests each run "under the version bound to its evidence, never the latest". So C9 is NOT_ASSESSED for N2.
  - **Fix:** say C9 is not assessed for N2.
- **A6** OP:25 and SVG:63.
  - **Problem:** they say "ALLOW, or DENY → no more model calls". That holds only in `enforce`. In `observe` (which N2, the named BREACH, uses), the DENY is recorded and the call goes ahead (A:266, 889–892), so N2's records would contradict the judged sketch.
  - **Fix:** "enforce: DENY halts; observe: DENY is recorded, only the safety ceiling halts".
- **A7** The rendered SVG.
  - **Problem:** the solid red `evaluate()` arrow ends in "Stateless evaluators", inside "GOVERNANCE SIDE · OFF THE PATH · laptop hub". The sketch is judged on "what sits in the path … how an enforcement point invokes you" (slide p26), and the text puts c16 in-process (A:533, 1155).
  - **Fix:** put a "c16 (vendored, same sha256)" box inside the runtime, end the arrow there, and add a dashed "same module" link to the off-path box.
- **A8** A:1438–1441 vs A:1465–1467.
  - **Problem:** the plan freezes the agents at 02:00, with live builds from about 00:30, but W0 (done about 22:45) → W1 (4–5 h) → W2 (4–6 h) is a serial chain. Even split, Stage A lands around 02:00–03:00, so the freeze slips to about 03:30–04:30 and eats the 13:00–15:00 buffer.
  - **Fix:** re-time §12.1 from the dependency chain, staff W1/W2 Stage A as the critical chain, and state the slip rule.

## B. SHOULD-FIX

- **B1** A:474 vs A:189: the end-of-invocation flush (up to 2 s) is a blocking wait on the evidence store on the return path (R-P-01f), while §2.3 says emit never waits. Declare it in §2.3 as a bounded wait that decides nothing, or drop it and rely on the stdout spool and C7.
- **B2** A:250, 419: EP-0 is a synchronous check that can refuse, and it sits outside the one contract. For D13, either route it through `evaluate()` at a declared pre-run placement (rule: "one caller inside a run"), or keep it record-only.
- **B3** A:873–874, 446–452: the cap-vs-safety-ceiling choice and the comparison sit in `model_call.py`, which is verdict logic outside the evaluators (A:530; the test at A:202). `Decision` has no mode, limit-applied or action field. `decide_inline` should return the verdict against the cap and the action against the applied limit, both from the pin.
- **B4** A:518 checks the sha256 against "the embedded copy", but the images freeze before v0-pilot, v1 and v1.1 exist (A:996), so nothing is embedded. Define what the agent hashes, and add a post-run check that each decision's `threshold.value` equals the frozen file.
- **B5** A:514, 893: "Re-programs in about 24 s, with no new image" is the model-swap figure. Whether an env patch reaches the runtime is untested (OC-12 covers only re-approval), yet every pin and the N2→N3 mode switch depend on it. Separately, the generation-based stale-approval flag (A:373) will fire on every run after a pin, while EP-0 (image digest + model) says ALLOW. Add an open check at the v0-pilot pin, and keep one staleness rule.
- **B6** A:937 counts "one per span, plus one per DENY (a DENY has no span)". In observe mode a DENY does have a span, so N2's C7 coverage falls below 100% by construction. Fix: "plus one per cancelled call".
- **B7** A:845 vs A:1132, 1206: an assessed run is defined as provenance LIVE_SUBJECT, but N4 doubles as ADV-R-10 (fault injection; adversarial runs get `ifabric-adv-` CIDs). Named runs should be LIVE_SUBJECT with `run.condition` set; use FAULT_INJECTION only for adversarial-only runs.
- **B8** A:636: the query output lacks who is responsible, who acted (actor, runtime, version, principal, on whose behalf) and the decision at each EP. That's the captain's verbatim ask (R-P-04a). Add them.
- **B9** A:685, 525–527: linking the re-test in the incident's work notes, and exporting T2 with `export`, need ServiceNow calls the "unchanged" package lacks: `export` works per Finding, filtered to `ifabric.integration`, and T2 is not a Finding. Yet T2 gates every assessment. Add both to W9 (ServiceNow writes, with the user's OK) and add a T1-only cut line.
- **B10** A:1463–1475: the workstream table has no owner or acceptance check per row (R-D-05, R-D-07). "CI" is assumed (A:555, 563, 1155), but the repo has none (R-D-04) and no workstream owns it. W4's `watch` needs W5 but doesn't list it.
- **B11** A:1391, 1155, 996: the second-EP proof needs the c16.py baked into the image (frozen around 02:00) to match the post-run module's sha256. Any later fix to `assess_run` breaks that or forces a new agent version. Freeze c16.py before the build, or split out a small shared core.
- **B12** A:1520, 1037: two holes in the never-cut tier.
  - Its fallback, "N2 runs with no guard", drops the safety ceiling the budget assumes (A:1507, 1514); the reference S2 run spent 2.0M tokens.
  - If pilots P5–P7 find no breach lever, C16 can't complete, so the never-cut tier may yield zero complete controls. C7's N4 is the only certain breach.
  - Fix: state a backstop for unguarded N2, and pre-declare C7 as milestone 1 in that case.
- **B13** A:978–988: 03 D3's cold-start risk was dropped. N7 runs right after the v1.1 pin, and N8/N9 right after a model swap and revert, so the latency maximum can move for reasons unrelated to the model. Declare a warm-up rule in `comparability`.
- **B14** A:506, 1041: the kit cross-check `evaluate.py 16` reads `~/evidence/gateway-log.json`, which the §9.1 layout doesn't produce, and its default-tier `observation_limit` will disagree on runs in other tiers. `run-ids.txt` puts the control first, but the kit expects one run id per line (submit.sh:23). Drop or scope the cross-check, and put the CID first.

## Requirements neither met nor recorded as gaps in §15

- R-J-10(b): see A1.
- R-J-45: no recorded L1→L3 demo and no timed 15-minute run-of-show.
- R-J-19 / R-P-25: no case planned as break → change → passing re-test; ADV-R-06 breaks, but nothing changes.
- R-P-04(a): see B8.
- R-J-24: no risk-acceptance path with a named approver and an expiry.
- R-P-03(e): no hand-check of 5 random links.
- R-J-05: no agent inventory in the pack (now partly addressed by §3.10).
- R-P-10: the OTel collector row has neither a test nor a gap entry.
- R-J-56: no record of a mentor review.

## Honesty

The N2→N3 "remediation" is switching enforce back on. The finding should name the deficiency ("operation: declared observe setting"), and every N3 attempt should be listed, since reaching the cap again isn't guaranteed. The INTEGRITY, AICT, EP-2 and EP-13 wording is honest.

## C. NITS

- A:784's example record fails its own null rule: it is missing `handoff.*`, `outcome.*` and `inline.limit_applied`.
- A:962 uses "UNKNOWN", which is not in the verdict vocabulary; use NOT_ASSESSED.
- A:502 says `inline_modes` and A:997 says `inline_mode`. A:823 says the safety ceiling comes "from the pilots", but A:997 sets it before them.
- The 21:00 decision step (A:1437) leaves out D13, and the first live-lane slot (A:1440) leaves out OC-19.
- A:527: span times are written by the gateway, not by AWS; use `@ingestionTime`.
- D:20 "every adapter can reach the ledger": a POST from the laptop is still untested (OC-8) and has no fallback. "No participant can delete" ignores that participants can set retention on `/team/*` log groups (F8).
- Mis-cites: A:1085 cites [PV row 1] for what is handoff §5.9; A:321 drops the source's "by its text, untested".
- A:496 `applies_to` must list N8's model-swap variant of `ifabric-it`.
- The post-run check trusts the tier carried in the run envelope; re-derive it from the scenario attributes.
- A:1206: assessed runs reuse `fault-` CIDs, so they look like reference runs (R-J-06).
- Stale-approval flags are computed in EP-5 and EP-10 rather than in the evaluators, against "the telemetry store never judges".
- EP-4 (judgment) and EP-11 (metrics) aren't passages; label them observers (R-J-52).
- §3.3 should forbid multi-line and block values, because the kit's fallback parser splits any line containing ":".
- The pack ships `prooflab/servicenow`, which contains the owner's work email and the ServiceNow host. Whether to redact is the user's call (handoff §4.4); the owner is the user.
- No inbound endpoint is allowed, so `callback()` is really notify-then-poll; say what calls it.
- SVG: no arrow from the script to `emit()`; nothing flows out of `callback()`; "AICT → pull() built" against §11.2's "observed"; most text is 10.5–12 px, about 6 pt if printed on one page. The ASCII diagram in §2.2 lacks EP-0.

## Verdict

The design is buildable and close to judge-ready. The component structure, frame conformance and honesty are sound; most defects are stale text or under-specified interfaces, not wrong architecture.

Fold the contract-level fixes into W0 before parallel work starts: window assessments, the `Decision` fields, the pin-check rule, per-control versioning and the assessed-run definition. Otherwise W1, W5 and W8 will each guess differently.

Judge-readiness hinges on A2 (the register file a judge opens) and the two sketch fixes (A6, A7). The largest execution risks are the schedule arithmetic (A8) and the unproven C16 and C9 breach levers (B12, B13).

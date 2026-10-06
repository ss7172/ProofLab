# 17b · Plan review: judging coverage

- **Reviewer:** independent judging-coverage reviewer (subagent), 2026-10-06 ~01:35–02:15 UTC. Read-only; no git, AWS, cluster, ServiceNow or network call.
- **Read:** `IMPLEMENTATION-PLAN.md` (all); `BUILD-SESSION-PROMPT.md` (all); memory `challenge-requirements.md` (all), `planning-handoff.md` (all), `prooflab-project.md` (judging parts); `architecture/ARCHITECTURE.md` §1.3, §3.7, §3.8, §5.5, §9, §10, §11 (+ greps of §3.0, §3.1, §7.1, §12.4); `architecture/work/02-requirements.md` R-J-01…R-J-45; `04-adversarial-review.md` (E-05, the LOSE table, the six-question table, I-11); `04b-independent-review.md` (A1, A2); `14-handoff3-deliverables-vetting.md` §5, §8.2; `architecture/guardrails/PLAN.md` §0, §7; Arth's `evidence-console-plan/09-BUILD-ORDER-AND-ACCEPTANCE.md` (the AT list).
- **Every Replace / Insert-after anchor below was checked with a byte count over `IMPLEMENTATION-PLAN.md`: each occurs exactly once.** G5's Done cell gets 10 small edits from 17B-02, -05…-12; their anchors are distinct and none sits inside another fix's replaced text, so they apply in any order.

## Verdict
As written, Phase 1 alone does **not** reliably give a valid, judge-ready submission. The control work is gated: G5 checks the C16 and C7 PASS/BREACH verdicts, the notify and the redaction. But G5 (and G6) never tick the six deliverables from the downloaded zip, the judged "one control and one window" query, the date check or L1 from the pack, and two Phase 1 deliverable tasks wait on the Phase 2 gate. The top 3 issues:
1. **17B-01:** J2 is required in Stage A by G2 and §4.2, but T3.4, PR-07 and PR-06's dependencies keep it in Stage B. Followed as written, pillar 1 (the captain's core claim) can silently drop for the whole event.
2. **17B-02:** EP-2's own adapter (`adapters/postrun/c16_replay.py`) has no task and no owner, so the second-EP answer and bonus can collapse back into 04's E-02 defect.
3. **17B-05/-06/-07:** the phase exits don't check the hand-in. The build prompt promises "a valid submission always exists", but G5 and G6 don't test the six deliverables (R-J-27), the window query (R-J-10) or the date (R-J-21).

**Counts:** ERROR 4 · GAP 13 · IMPRECISE 4.

## Coverage table

| Requirement | Phase | Task | Gate item | Status |
|---|---|---|---|---|
| D1 evidence file (the pack, with the tool inside) | 1 | T4.8, T8.5 | G5: scan + manifest + a query "from a fresh unzip" (the tool implied); the §4.3 pack list is short | gap (17B-03, -05) |
| D2 `register.yaml` (+ risks, inventory), dated | 1 | T1.4–T1.7, T8.1 | G4: T1 exists; nothing on the WORKDIR copy or the date check | gap (17B-05, -07) |
| D3 control-test tool | 1 | T5.1 | G5: one C16 run query | gap (17B-06) |
| D4 `run-ids.txt` | 1 | T1.9; T8.4 (Deps: Gate G6) | G7 only | ERROR (17B-03), gap (17B-05) |
| D5 sketch | 1 | T8.2 | G7 only | gap (17B-05) |
| D6 gap list | 1 | T8.3 | G7 only | gap (17B-05) |
| Axis 1 C16: dated threshold | 1 | T1.7 | G4 (T1), no date check | gap (17B-07) |
| Axis 1 C16: named PASS + BREACH | 1 | §5.2 rows 17, 20, 22 | G5 | covered |
| Axis 1 C16/C7: owner alerted | 1 | T6.4, T6.5 | G5 "DELIVERED"; not in the pack; no named owner | gap (17B-09) |
| Axis 1 C16/C7: closure by re-test | 1 (verdicts), 2 (link note) | none for the link | G5 N3/N5 SATISFIED only; AT-10 at G6/G7 | gap (17B-10) |
| Axis 1 C7 (N1/N4/N5) | 1 | §5.2 rows 17, 23, 24 | G5 verdicts | covered (same gaps as C16) |
| C9 "thresholds working" | 1 (threshold), 2 (N7–N9) | DC-11, T1.8 | G5 silent; G6 | gap (17B-15) |
| Two-minute test, run | 1 | T5.1 | G5: C16 only | gap (17B-06) |
| Two-minute test, window | 1 (code), 2 (AT-01) | T5.1, T5.4 | none in G5; G6 via AT-01 | gap (17B-06) |
| Six auditor questions | 1 (CLI), 2 (console) | T5.1, T5.4 | none in G5; G6 via AT-12 | gap (17B-12) |
| Declared window + run catalogue + phase labels | 1 (CLI), 2 | T4.5 | G6; window write-once only at row 44 | gap (17B-12, -13) |
| L1 foundation (R-J-01 a–c) | 1 | T3.x, ADV-H-01 leg A | G5: the block only | gap (17B-08) |
| L2 (controls on, ledger, AICT) | 2 | T4.1, T6.8 | G6 | covered |
| L3 (one id AWS → incident → response) | 2 | T6.5–T6.7 | G6; G7 5-link hand-check | covered |
| Second EP (ARCH §11) | 1 | none owns `c16_replay.py`; no adapter-diff note | G5 wording ambiguous | ERROR (17B-02) |
| Inline bonus N3 + DC-6 live | 1, slot | §5.2 rows 22, 43 | G5 N3; DC-6 has no gate (recorded N3 is the fallback) | covered (fallback) |
| Adversarial Hostile/Rogue | 1 (H-01, N3, N4), 3 | T7.1–T7.3 | G7; Phase 1 rows only for H-01 | gap (17B-14) |
| Pillar 1, the judgment gap | 1 (J2), 2 (N6) | T3.4, PR-07, N6 | G2 contradicts T3.4; nothing in G5 | ERROR (17B-01), gap (17B-11) |
| Honest failure (R-J-16) | 1, 3 | T7.6 (Deps: Gate G6) | none at any gate | ERROR (17B-03), gap (17B-12) |
| LOSE: undated / late threshold | 1 | T1.4's date check | none in G5 (AT-02 in G6/G7) | gap (17B-07) |
| LOSE: records cover only some actions | 1–2 | C7, T4.4 | G5 C7 verdicts; corroboration at G6 | covered (partial in Ph1) |
| LOSE: evidence only we can verify | 1 | T4.8 | G5 manifest + the tool | covered |
| LOSE: finding closed without re-test | 1–2 | none for the link | AT-10 at G6/G7 | gap (17B-10) |
| LOSE: control holds its threshold | 0 | T0.4 | merge gate | covered |
| LOSE: works only in the request path | 1 | N2 `observe` | G5 | covered |
| LOSE: missing artefact (R-J-27) | 1, 2 | T4.8 | G7 only | gap (17B-05) |
| Secrets in the pack | 1 | T4.2 | G5 scan | covered |
| Pilot/baseline ids in `run-ids.txt` | 1 | T1.9 test | G7 only | gap (17B-05) |
| SYNTHETIC data in PACK mode | 2 | T5.4 (a) | none | gap (17B-17) |
| Run of show (15 min, timed) | 3 | T8.6 | G7 | covered |
| Rehearsal by a non-builder | 3 | T8.7 | G7 (a gap row can stand in for the Must) | imprecise (17B-20) |
| Recorded backup demo | 3 | T8.8 | G7 (Should) | covered |

## Findings

### 17B-01 · ERROR · Minimal J2 is required in Stage A (G2, §4.2) but planned for Stage B (T3.4, PR-07, PR-06's deps)
- **Where:** §3.3 row T3.4 (Task, Done); §6 row PR-07 (Title), row PR-06 (After); against §4.2 "How Phase 1 fits" and §7 row G2.
- **Evidence:**
  - Plan §4.2: "**Stage A only** goes into the image: MIN rails, minimal J2 (JSON in the text + the precedence rules; the re-ask may wait)". G2: "three trio bundles ≤ 24,000 chars each with the MIN rails and minimal J2".
  - T3.4: "**J2 (Stage B):** … If Stage B slips, Stage A ships and gap 1 stays open". PR-07: "(bundled at Stage B)". PR-06 After: "PR-02–PR-05", which leaves out PR-07.
  - §6: "After Gate G2 the agent PRs (PR-03 … PR-07) are frozen: a later change is a new build, a declared treatment and a re-baseline".
  - Build prompt L34–35: the Phase 1 agents carry "minimal judgment rules: S2 gather-evidence, S3 escalate".
  - Memory `prooflab-project`: "Closing the agent-judgment gap is core, not optional" (deck p2, p5; p23 pillar "Close the gap").
- **Why it matters:** PR-06 can bundle without PR-07, and T3.4 offers a Stage B waiver, so G2 either stalls or ships agents without J2. The agents then freeze at G3, and pillar 1 stays open for the rest of the event with no phase that reopens it.
- **Fix (exact):**
  - Anchor: §3.3 row T3.4, Task. Replace: `**Ph1 (minimal)** · **J2 (Stage B):**` With: `**Ph1 (minimal, in Stage A)** · **J2 (minimal in Stage A: JSON in the text + the precedence rules; the re-ask may wait):**`
  - Anchor: §3.3 row T3.4, Done. Replace: `If Stage B slips, Stage A ships and gap 1 stays open` With: `If minimal J2 is not green by Gate G2's hard bound (04:15), Stage A ships without it, gap 1 stays open for the whole event (the agents freeze at Gate G3), and the gap list and the README's pillar table say so; Hold-2 tells the captain`
  - Anchor: §6 row PR-07, Title. Replace: `one re-ask, the precedence rules (bundled at Stage B)` With: `the precedence rules (minimal, bundled at Stage A; the re-ask may wait)`
  - Anchor: §6 row PR-06, After. Replace: `| PR-02–PR-05 |` With: `| PR-02–PR-05, PR-07 (minimal J2) |`

### 17B-02 · ERROR · The second EP's own adapter, `adapters/postrun/c16_replay.py`, has no task and no owning PR
- **Where:** §3.1 row T1.3; §3.4 (no row); §6 (no PR owns `adapters/postrun/`); §7 row G5; §3.8 row T8.5.
- **Evidence:**
  - ARCH §3.0 L288: "postrun/ c16_replay.py (EP-2: the c16 core once per gateway call, after the run, §11)".
  - ARCH §11.1: "After the run, `adapters/postrun/c16_replay.py` calls the **same** `decide_inline` once per gateway call … and records each result (`ep.id: EP-2`, `ep.transport: pull`)". On the proof (I-21): "That PR's sha and its `git diff --stat` are cited, with the sha256 equality check".
  - Plan: a search for `postrun`, `c16_replay` and `diff --stat` finds 0 hits. T1.3 has only "`c16.py` (`assess_run` over `aws/spans`, the EP-2 replay reconciliation, the stop-record check)", inside the pure evaluators (PR-09: "no I/O").
  - G5: "EP-1's replayed decisions reconciled". T8.6 promises "the second EP = the same c16 core at EP-1 and EP-2".
  - 04 review: "EP-2 runs the tester, not the evaluator" (E-02, the defect this design fixed).
- **Why it matters:** the Axis-2 question "Would it survive a second enforcement point?" (ARCH §10.1 row 1) and the Axis-3 second-EP bonus rest on EP-2 `decision` records that carry the same `evaluator.sha256`. With no owner, the replay is either never built or folded into the pure tester (E-02 again, with no EP-2 records in the store). G5 can then pass on the tester alone, and the run of show would claim more than the pack shows.
- **Fix (exact):**
  - New row after row T4.8 (§3.4):
    `| T4.9 | **Ph1** · **EP-2, the second placement of the c16 core** (`adapters/postrun/c16_replay.py`; ARCH §3.1, §11.1): after each run, the run's model-call spans from `aws/spans` in gateway order; per call one `C16Question` (committed = the earlier calls' actual tokens, reserved = 0, bound = this call's actual tokens, `bound_basis: actual`) through the **same** `c16_core.decide_inline` with the run's pin; each result a `decision` record (`ep.id: EP-2`, `ep.transport: pull`, the core's `evaluator.sha256`), recorded, never executed. Its own PR, so its `git diff --stat` shows adapter files only (the I-21 proof) | For N2 and N3, one EP-2 decision per model-call span, each with the same `evaluator.sha256` as EP-1's decisions; `c16.py`'s reconciliation lists every EP-1/EP-2 difference; the PR touches only `adapters/postrun/` | PR-12b worker → PR-09's reviewer | T1.2, T4.1 | 1 h | — | 0 |`
  - New row after row PR-12 (§6):
    `| PR-12b | **Ph1** · EP-2: the post-run replay of the c16 core (the second EP) | T4.9 | `adapters/postrun/` | PR-02, PR-12 | Sonnet · medium | the same `evaluator.sha256` at EP-1 and EP-2; the diff touches adapter files only |`
  - Anchor: §7 row G5, Done. Replace: `EP-1's replayed decisions reconciled` With: `EP-2's replayed decisions (T4.9, the same `evaluator.sha256` as EP-1's) reconciled with EP-1's`
  - T8.5's README carries the adapter-diff note: see 17B-12's README replacement.

### 17B-03 · ERROR · Phase 1 deliverables wait on the Phase 2 gate, and the Phase 1 pack list leaves required parts out
- **Where:** §3.8 row T8.4 (Deps); §3.7 row T7.6 (Deps); §4.3 row 06:05–06:30 (Step).
- **Evidence:**
  - T8.4: "**Ph1** · **Deliverable 4, the named runs** … | Gate G6 |". T7.6: "**Ph1 (named in the README)** … | Gate G6 |".
  - §4.3 06:05–06:30: "the minimal pack (store export, raw, assessments, register + T1 proof, `run-ids.txt`, gap list, `sketch.png`, README; …)". The list leaves out the tool `prooflab/`, the findings and `servicenow/delivery-log.jsonl` (the alert), `window.json`, `named-runs.md`, the adversarial log, `inv-1` and the WORKDIR copies.
  - ARCH §9.1: "`prooflab/` the tool, stdlib only …"; "WORKDIR/ register.yaml (the latest frozen version, byte-identical to register/versions/<v>.yaml)".
  - R-J-27 (LOSE): "A missing artefact cannot be scored". R-J-16 (MUST): one honest failure. Build prompt L43: "so a valid submission always exists".
- **Why it matters:** followed as written, deliverable 4's task and the honest failure wait until about 10:15 (G6), and the Phase 1 pack builder works from a list without the tool, the alert evidence or the window. If Phases 2–3 slip, submit #1 is the one scored.
- **Fix (exact):**
  - Anchor: §3.8 row T8.4, Deps. Replace: `| T1 worker → T8 worker | Gate G6 | (in T1) | S3 | 0 |` With: `| T1 worker → T8 worker | each named run (T1.9); rewritten at each submit | (in T1) | S3 | 0 |`
  - Anchor: §3.7 row T7.6, Deps. Replace: `| T8 worker → Arth | Gate G6 | 0.25 h | — | 0 |` With: `| T8 worker → Arth | submit #1: ADV-H-01 leg A (gap 4: our BLOCKED against the platform's ALLOW); re-chosen at rehearsal after Gate G6 | 0.25 h | — | 0 |`
  - Anchor: §4.3 row 06:05–06:30, Step. Replace: `the minimal pack (store export, raw, assessments, register + T1 proof, `run-ids.txt`, gap list, `sketch.png`, README; redaction + the exact-value scan; MANIFEST)` With: `the minimal pack (the tool `prooflab/`; the store export; raw; assessments + findings; `servicenow/delivery-log.jsonl`; register `v1` + `v1.risks.yaml` + `inv-1` + the T1 proof; `window.json` + the run catalogue; `named-runs.md`; the adversarial log; `live-lane-log.jsonl`; the README; the WORKDIR copies `register.yaml` (= `v1.yaml` byte for byte), `run-ids.txt`, `gap-list.md`, `sketch.png`; redaction + the exact-value scan; MANIFEST)`

### 17B-04 · ERROR (cross-lens: infra/sequencing; one line) · The Phase 1 pack builder depends on the Phase 2 projector
- **Where:** §3.4 row T4.8 (Deps); §6 row PR-21 (After). T4.8 (Ph1) depends on "T4.2, T4.4, T5.3", where T5.3 is "**Ph2**". PR-21 (Ph1) waits for "PR-12, PR-13, PR-16", where PR-16 is "**Ph2**". Submit #1 can't be built as the graph stands.
- **Fix (exact):**
  - Anchor: §3.4 row T4.8, Deps. Replace: `| W6 worker → Arth | T4.2, T4.4, T5.3 |` With: `| W6 worker → Arth | T4.2, T4.4 (T5.3 only from submit #2) |`
  - Anchor: §6 row PR-21, After. Replace: `| PR-12, PR-13, PR-16 |` With: `| PR-12, PR-13 (PR-16 only for submit #2) |`

### 17B-05 · GAP · G5 and G6 never tick the six deliverables from the downloaded zip (R-J-27, R-J-44)
- **Where:** §7 rows G5 and G6, Done.
- **Evidence:** only G7 checks "`run-ids.txt` one CID per line with no pilot or baseline id, the six deliverables in the zip and in WORKDIR". G5 ends "…`manifest.py verify`; **submit #1 read back**", and G6 ends "**submit #2 read back**". R-J-44: "a checker downloads the zip from the bucket, unzips it and ticks all six deliverables". Build prompt L43: "Every phase ends with submit.sh + S3 readback (gates G5/G6/G7), so a valid submission always exists".
- **Why it matters:** a missing or wrong artefact (no `sketch.png`, a pilot id in `run-ids.txt`, a draft `register.yaml` in WORKDIR, a WORKDIR file outside the staged-tree scan) passes G5 and G6, and either submission may be the one scored.
- **Fix (exact):**
  - Anchor: §7 row G5, Done. Insert after: `**submit #1 read back**` the text: `; on the downloaded zip a non-builder ticks the six deliverables (R-J-44): the pack with `prooflab/` inside; `register.yaml` byte-identical to `register/versions/v1.yaml` (per-control version and date); `run-ids.txt` one CID per line with no pilot or baseline id; `sketch.png`; `gap-list.md`; the exact-value scan 0 hits on the unzipped tree, WORKDIR files included`
  - Anchor: §7 row G6, Done. Insert after: `**submit #2 read back**` the text: `, with the same six-deliverable tick on the downloaded zip (`register.yaml` = the latest frozen version, byte for byte)`

### 17B-06 · GAP · The two-minute test at G5 is one C16 run query: no window, no C7 query, no negative answers, no claim line
- **Where:** §7 row G5, Done; §3.5 row T5.1, Done.
- **Evidence:**
  - G5: "`python3 -m prooflab query --control C16 --run <N2's CID>` answers in < 2 min from a fresh unzip on 3.9". T5.1's Done tests `--run` only, though its task builds "per run and per window".
  - R-J-10: "(a) For each complete control, the tester types one run query and (b) one UTC-window query … (c) An unknown run id and an unsupported control each return an explicit non-success". Slide p25: "We name one control and one window … Two minutes".
  - R-J-09: the claim line reads "partial coverage". ARCH §3.7: exit 2 = "not assessed".
- **Why it matters:** the judged live test is "one control and one window". Phase 1 claims C16 and C7 complete, but only C16's run query is checked, and the "never looks successful" rule is untested.
- **Fix (exact):**
  - Anchor: §7 row G5, Done. Insert after: ``python3 -m prooflab query --control C16 --run <N2's CID>` answers in < 2 min from a fresh unzip on 3.9;` the text: ` the same for C7 (`--control C7 --run <N4's CID>`) and one `--window` query per complete control (C16, C7) inside the declared Phase 1 window, each < 2 min, timed by the non-builder; an unknown CID and `--control C9 --run <N1's CID>` each exit 2 with "not assessed" or "insufficient evidence", never a pass; `query --claim` reads "partial coverage";`
  - Anchor: §3.5 row T5.1, Done. Replace: ``cd evidence && python3 -m prooflab query --control C16 --run <CID>` answers in < 2 min from the unzipped pack on 3.9, timed by a non-builder;` With: ``cd evidence && python3 -m prooflab query --control C16 --run <CID>`, the same for C7, and one `--window` query per complete control each answer in < 2 min from the unzipped pack on 3.9, timed by a non-builder; an unknown CID and an unassessed control exit 2 with "not assessed";`

### 17B-07 · GAP · No gate runs the date check over the assessed runs (LOSE: "a threshold … dated after the test")
- **Where:** §7 row G5, Done. G6/G7 cover it only through console AT-02.
- **Evidence:** G4 checks only that T1's head-object exists. ARCH §10.2: "T1 … is the date proof, checked against the run's first span (gateway start and `@ingestionTime`)". R-J-21: "That timestamp is earlier than the start of every assessed run under the version; the start times come from `aws/spans`". Slides: "we check the date".
- **Why it matters:** this is LOSE item 1, and submit #1 has no console, so no AT-02.
- **Fix (exact):** Anchor: §7 row G5, Done. Insert after: `N3 SATISFIED with a stop record (or every attempt listed);` the text: ` the date check passes for every CID in `run-ids.txt` (`v1`'s T1 LastModified, with `v1.head.json`'s SHA-256 equal to the pack's `v1.yaml`, earlier than the run's first span in `aws/spans`), printed in each answer;`

### 17B-08 · GAP · L1 ("will not be judged" without it) is checked only by the guardrail block, not from the pack
- **Where:** §7 row G5, Done.
- **Evidence:** R-J-01: "(a) every model-call span of the run in `aws/spans` … names a Nemotron model; (b) a guardrail is declared on every ModelConfig used (`safety.required: true`), and one guardrail block is on record; (c) every agent, model and tool … Approved, with the approval records exported. A reviewer ticks (a) to (c) from the pack alone". G5 checks only "ADV-H-01 leg A shows BLOCKED_GUARDRAIL". ARCH §10.4 L1: "approvals exported".
- **Why it matters:** the judging slide says "A submission without this foundation will not be judged". The data exists in Phase 1 (T4.1's spans and CR status), but nothing checks it is in the pack.
- **Fix (exact):** Anchor: §7 row G5, Done. Insert after: `ADV-H-01 leg A shows BLOCKED_GUARDRAIL on the task call (the L1 block on record);` the text: ` L1 from the pack alone (R-J-01): every model-call span of N1–N5 names a Nemotron model, and the redacted CR status shows `safety.required: true` on each ModelConfig used and every agent, model and tool Approved;`

### 17B-09 · GAP · "The owner alerted" is checked on the laptop, not in the pack, and not against the named owner
- **Where:** §7 row G5, Done (and the §4.3 pack list, fixed in 17B-03).
- **Evidence:** G5: "N2's and N4's incidents DELIVERED (production log, absolute path, no dry run)". The §4.3 pack list has no `servicenow/delivery-log.jsonl` or findings, and G-06's ledger mirror is Ph2 (T6.6). R-J-08: "The breach has a delivered owner alert". Slides (memory `prooflab-project`): "the alert, its named recipient and the silence must still be recorded". T6.10: "`SNOW_OWNER_USER` set explicitly".
- **Why it matters:** Axis 1's "owner alerted" must be visible to a stranger from the pack. In Phase 1 the response or silence is not yet recorded (check is Ph2), so the README must say so.
- **Fix (exact):** Anchor: §7 row G5, Done. Replace: `N2's and N4's incidents DELIVERED (production log, absolute path, no dry run)` With: `N2's and N4's incidents DELIVERED to the register's named owner (`SNOW_OWNER_USER`), with the delivery log and the Finding files in the pack (production log, absolute path, no dry run); the README says the response-or-silence record starts in Phase 2`

### 17B-10 · GAP · Closure "only by a passing re-test" has no link check at G5 and no task for the incident's re-test link note
- **Where:** §7 row G5, Done; §3.6 row T6.5 (phase tag); §5.2 row 28.
- **Evidence:**
  - ARCH §3.8: "A finding is 'closed' only by a later SATISFIED assessment on the same control and scope type, linked in the incident's work notes". ARCH §12.2 W9 lists "the re-test link note: ServiceNow writes". ARCH §12.4: "If the re-test link note can't be written through the integration, the owner adds it by hand, or it is a gap".
  - R-J-24: "Every finding marked closed links a later SATISFIED re-test assessment".
  - Plan: G5 has only "N3 SATISFIED", "N5 SATISFIED". T6.4's `retest` is Ph2. No task or §5.2 row writes the link note. AT-10 runs at G6/G7 only.
- **Why it matters:** this is LOSE item 4. Without the link, submit #1 shows a SATISFIED re-test beside an open finding, and the link note is never written in any phase.
- **Fix (exact):**
  - Anchor: §7 row G5, Done. Insert after: `**C7:** N4 BREACHED, N5 SATISFIED;` the text: ` N2's finding is closed only by N3's SATISFIED assessment and N4's only by N5's, each linked by finding id in `findings/` (the ServiceNow incidents stay open until their Phase 2 re-test link note);`
  - Anchor: §3.6 row T6.5, Task. Replace: `**Ph1 (`notify` only, decided by the captain, with the guards) · Ph2 (analysis, the check loop, snapshots)**` With: `**Ph1 (`notify` only, decided by the captain, with the guards) · Ph2 (analysis, the check loop, snapshots, the re-test link note on each incident, ARCH §3.8)**`
  - Anchor: §5.2 row 28, Action. Replace: `The first **WRITTEN** analyses on N2's and N4's incidents (between runs)` With: `The first **WRITTEN** analyses on N2's and N4's incidents (between runs), then the re-test link notes (N3 → N2's incident, N5 → N4's; through the integration, else the owner by hand, else a gap row; ARCH §12.4; Hold-4 unless `notify`'s incident reuse writes it, since ARCH §12.2 W9 makes it a ServiceNow write with the captain's OK)`

### 17B-11 · GAP · Pillar 1 ("close the gap") has no evidence item at G5, and the deck's "passing grade" has no task
- **Where:** §7 row G5, Done; §8.2 OC-6.
- **Evidence:**
  - Deck p5 (memory `prooflab-project`): "A passing grade on the fault the reference agents cannot crack". ARCH L771: our agents write the reference shape "so the kit's grader can pass legitimately". The plan runs `score-run.py` only as OC-6 ("Offline, on S-2's export").
  - The only named escalate run, N6, is in Phase 2 (§5.2 row 29). R-J-04: the README's pillar table "no row is empty".
- **Why it matters:** if Phase 1 is the submission scored, pillar 1 (the captain's core claim) has no checked evidence.
- **Fix (exact):** Anchor: §7 row G5, Done. Insert after: `N1 SATISFIED;` the text: ` pillar 1 on record: N2's and N3's (S2) `judgment` records carry the J2 fields (disposition, deciding evidence, reason), and `score-run.py`'s grade on N3's per-CID ledger export sits in `answers/` beside the reference S2 run's (EXPLORATORY), or the gap list says gap 1 is open;` (the README's pillar table: 17B-12).

### 17B-12 · GAP · The Phase 1 README and G5 don't cover the window, the six questions' Phase 1 limits, the honest failure or the pillar table
- **Where:** §3.8 row T8.5 (README contents); §7 rows G5 and G7.
- **Evidence:**
  - T5.1 (Ph1) claims "the six auditor questions for any incident in the declared window", but the window is written once only at §5.2 row 44 (Phase 3) and checked first at G6.
  - The Phase 1 collectors (T4.1: "Ph1 (spans, ledger export, CR status, metrics, evidence) · Ph2 (the rest)") omit both PDP replicas' lines (R-J-31), the AWS-written invoker records (ARCH §10.3 WHO) and the corroboration report (R-J-33, Ph2 in T4.4). T2 and AICT are Phase 2.
  - T8.5's README lists "the declared window; one command per question; the honest failure; what was left out and why", with no pillar table (R-J-04; ARCH §9.1 "the pillars table") and no adapter-diff note (17B-02).
  - No gate checks the honest failure (R-J-16 MUST). Brief L379 via 02: "Include bonus evidence only for implemented and verified capabilities".
- **Why it matters:** judges ask the six questions "from your Evidence Pack alone, for an incident … from your event window". An undeclared window, or a README that implies full answers, reads as an overclaim.
- **Fix (exact):**
  - Anchor: §3.8 row T8.5, Task. Replace: `the stranger's README (the declared window; one command per question; the honest failure; what was left out and why);` With: `the stranger's README (the declared window; the pillars table, one row per pillar pointing to its files, none empty (R-J-04); one command per question; the six-question table marking each answer FULL or PARTIAL for this submit and naming what arrives later (submit #1: no PDP replica lines, AWS-written invoker records, T2, AICT or corroboration report); the honest failure; the adapter-diff note for the second EP (ARCH §11.1, I-21: the PR sha, its `git diff --stat`, the core's sha256 at EP-1 and EP-2); what was left out and why; no claim beyond the evidence in this submit);`
  - Anchor: §7 row G5, Done. Insert after: `the minimal pack passes the exact-value scan (0 hits) and `manifest.py verify`;` the text: ` `window.json` and the README declare the Phase 1 window (UTC start = `v1`'s T1 LastModified, end = this snapshot); `query --incident <N2's CID>` and `query --incident <ADV-H-01 leg A's CID>` answer the six questions with record ids, every PARTIAL answer naming its gap; the README names the honest failure with its evidence (R-J-16) and every claim in it cites a file in this pack;`
  - Anchor: §7 row G7, Done. Insert after: ``run-ids.txt` one CID per line with no pilot or baseline id, the six deliverables in the zip and in WORKDIR;` the text: ` the README's honest failure (T7.6) and pillars table present, every claim citing a pack file;`

### 17B-13 · GAP · Alert-phase labels are assigned after the fact, though Phase 1 interleaves Hostile and Rogue cases
- **Where:** §3.4 row T4.5; §3.3 row T3.5.
- **Evidence:** ARCH §3.7 `query --runs`: "its phase (Alert 0/1/2: the declared label, from phase boundaries written into the run index before the runs; I-11)". ARCH §5.5: N3 = ADV-R-05 and N4 = ADV-R-10 run "inside the declared phase window (I-11)". In the plan, ADV-H-01 leg A (Hostile, 05:22), N3 (Rogue, 05:39) and N4 (Rogue, 05:50) sit among Alert 0 runs, and the window file is written once at §5.2 row 44 (13:30).
- **Why it matters:** judges pick "a Hostile or Rogue incident" from our window, and labels set after the runs look like cherry-picking.
- **Fix (exact):**
  - Anchor: §3.4 row T4.5, Task. Insert after: `The window (UTC start, end, Alert 0/1/2 boundaries; default: from `v1`'s T1 LastModified to the final snapshot)` the text: `; each run's Alert phase is the label the script wrote into its run-index line before the run (ARCH §3.7, I-11: ADV-H-01 leg A Hostile, N3 = ADV-R-05 and N4 = ADV-R-10 Rogue, the rest Alert 0), never assigned afterwards`
  - Anchor: §3.3 row T3.5, Task. Replace: `the tally carried; conditions, faults, `--tamper-tally`; the run index line.` With: `the tally carried; conditions, faults, `--tamper-tally`; the run index line, carrying the run's declared Alert phase (0/1/2), written before the run (I-11).`

### 17B-14 · GAP · T7.1's Phase 1 adversarial log has only ADV-H-01's row, though N3 (ADV-R-05) and N4 (ADV-R-10) run in Phase 1
- **Where:** §3.7 row T7.1 (phase tag); against T7.3 ("ADV-R-05 = N3; ADV-R-10 = N4", tagged **Ph3**).
- **Evidence:** the T7 header: "every case's defence and expected outcome is written and dated **before** it runs". T7.1's Done: "A row exists before each case runs". R-J-37 (Alert 2 Rogue, MUST).
- **Why it matters:** these are submit #1's only Rogue cases. Written in Phase 3, their rows postdate the runs, and the Phase 1 pack shows no Rogue case.
- **Fix (exact):** Anchor: §3.7 row T7.1, Task. Replace: `**Ph1 (ADV-H-01's row) · Ph3**` With: `**Ph1 (the rows for ADV-H-01 leg A, ADV-R-05 = N3 and ADV-R-10 = N4, each written before its run) · Ph3**`

### 17B-15 · GAP · C9 in Phase 1 is "in place" with no check; the captain's words are "thresholds working"
- **Where:** §1 DONE paragraph; §7 row G5 (silent on C9).
- **Evidence:** memory PHASES: "C16 → C7 → C9 in order, thresholds working". Plan §1: "C16 + C7 (C9's threshold in place)". §4.2: C9 is "in place" in Phase 1 (DC-11). G5 has no C9 item. Build prompt L37 allows "finish it in Phase 2 if it doesn't fit".
- **Why it matters:** the finish line's own example is "was control 9 satisfied for run FM-B?". A judge typing it at submit #1 must get an honest, explicit non-pass, never a silent or green answer.
- **Fix (exact):** Anchor: §1 DONE paragraph. Replace: `C9's threshold in place` With: `C9's threshold in `v1` and an honest "not assessed yet" answer for C9 (G5)`. The G5 check itself is in 17B-06's insert (`--control C9 --run <N1's CID>` exits 2). The N1-reuse question goes to the captain (b).

### 17B-16 · GAP · Pod-only sources (both PDP replicas, gateway stdout) are first pulled in Phase 2
- **Where:** §5.2 row 25; T4.1's phase split.
- **Evidence:** T4.1 puts `pdp_logs` and `gateway_stdout` in "Ph2 (the rest)". Memory `challenge-requirements`: "A pod restart loses the pod log", and PDP/authz logs are "pod-only". R-J-31: "The PDP decision lines from both replicas are in the pack".
- **Why it matters:** a pod restart before ~06:30–10:30 loses N1–N5's AUTHORIZED corroboration for good.
- **Fix (exact):** Anchor: §5.2 row 25, Action. Replace: `**Submit #1:** the minimal pack → `submit.sh` → readback` With: `**Submit #1:** a raw read of both PDP replicas' logs and the gateway pod's stdout (pod-only sources, read-only) → the minimal pack → `submit.sh` → readback`

### 17B-17 · GAP · "PACK mode refuses synthetic data" (the build prompt) has no Done check
- **Where:** §3.5 row T5.4, Done.
- **Evidence:** T5.4 (a): "PACK mode refuses SYNTHETIC data and the panel's fake sample", but no AT covers it (AT-P0 = AT-01…AT-12 + AT-14; AT-16 checks EXPLORATORY only). Build prompt L19: "PACK mode refuses synthetic data".
- **Fix (exact):** Anchor: §3.5 row T5.4, Done. Replace: `AT-01 run by a non-builder; AT-06 with its pattern assembled from parts` With: `AT-01 run by a non-builder; AT-06 with its pattern assembled from parts; a file labelled SYNTHETIC or the panel's fake sample placed in a staged copy is refused by `--data pack` with a red banner`

### 17B-18 · IMPRECISE · T8.9 keeps the superseded submit times
- **Where:** §3.8 row T8.9. It says "first `submit.sh` by 13:15, final by 14:45", against §1 and §4.6 (submit #1 by 07:00 at the latest, submit #2 by 11:30).
- **Fix (exact):** Replace: `first `submit.sh` by 13:15, final by 14:45` With: `submit #1 by 07:00 at the latest (target ~05:30), submit #2 by 11:30, the final by 14:45 (§4.6)`

### 17B-19 · IMPRECISE · T1.7 (Ph1) requires the T2 export, which DC-10 and G4 move to Phase 2
- **Where:** §3.1 row T1.7, Done. It says "the T2 incident exported with RESPONDED", against G4's "(T2: Phase 2, DC-10)".
- **Fix (exact):** Replace: `the T2 incident exported with RESPONDED; the agents echo the `v1` pin` With: `the T2 incident exported with RESPONDED (Phase 2 by default, DC-10; a late T2 is a gap row); the agents echo the `v1` pin`

### 17B-20 · IMPRECISE · G7 lets a gap row stand in for the Must rehearsal; T8.7's dependency is circular
- **Where:** §7 row G7; §3.8 row T8.7 (Deps). G7: "one (Must) or two (Should) rehearsal records, … the recorded demo (or each missing item listed as a gap)". T8.7 Deps: "Gate G7 (first)", but G7 checks T8.7's output.
- **Fix (exact):**
  - Replace: `one (Must) or two (Should) rehearsal records, the timed run of show, the recorded demo (or each missing item listed as a gap)` With: `one rehearsal record (Must, never replaced by a gap row) and a second (Should), the timed run of show, the recorded demo (each missing Should item listed as a gap)`
  - Replace: `| Gate G7 (first) |` With: `| Gate G6 |`

### 17B-21 · IMPRECISE · §4.6 tags "The L1 → L3 path" as Phase 1 Must, while L2/L3 are Phase 2 (and AICT is unnamed)
- **Where:** §4.6 scope ranking, both Must rows. Build prompt L48: "the L1→L3 path (Phase 2's app, ServiceNow + Assurance, AICT)".
- **Fix (exact):**
  - Replace: `| **Must** | The L1 → L3 path;` With: `| **Must** | L1 (the foundation: governed Nemotron, the MoDaaS guardrail block on record, approvals exported);`
  - Replace: `| **Must** | ServiceNow + the Assurance agent;` With: `| **Must** | The L2 → L3 path: ServiceNow + the Assurance agent, AICT;`

## Inconsistencies with BUILD-SESSION-PROMPT.md (report only; nobody edits that file now)
- **L43** "Every phase ends with submit.sh + S3 readback (gates G5/G6/G7), so a valid submission always exists": the plan's G5 and G6 do not check validity (the six deliverables, the window query, the date). See 17B-05, -06, -07.
- **L34–35** puts "minimal judgment rules: S2 gather-evidence, S3 escalate" in the Phase 1 agents. This matches the plan's G2 and §4.2 but not T3.4 or PR-07 (17B-01).
- **L47–48** MUST: "the L1→L3 path (Phase 2's app, ServiceNow + Assurance, AICT)". The plan's §4.6 puts the whole path in the Phase 1 row (17B-21).
- **L19** "PACK mode refuses synthetic data": the plan has no executable check for it (17B-17).
- **L50** makes the second rehearsal SHOULD, but the slides say "Rehearse it twice before you present" (R-J-45, MUST in `02`). The plan follows the prompt, which outranks it; see Needs the captain (d).
- **L51** "CUT ORDER … C9 first": the plan's §4.6 cuts the buffer beyond 1 h and the P5 extras before C9. These are not scope, so the effect is the same; noted only.

## Needs the captain (each with a recommended default)
- **(a) J2 at Stage A's hard bound (17B-01).** If minimal J2 is not green by 04:15, either ship the agents without it (ARCH §7.1's rule; gap 1 open for the whole event) or hold the builds up to 30 min for it. **Default:** ship at 04:15 per ARCH §7.1, tell the captain in Hold-2, and state gap 1 in the README's pillar table.
- **(b) C9 in Phase 1 (17B-15).** "Thresholds working" for C9 at submit #1 would mean control 9 in `v1` with its own version and date, plus an explicit "not assessed" answer (exit 2), never a verdict. N1, N3 and N5 stay "C9 baseline-eligible, never C9-assessed". If N1 got a C9 verdict under `C9-v1` and then fed `v1.1`'s baseline (T1.8), assessed results would be rewriting their own criteria (brief L199, R-J-21). **Default:** yes, as stated; C9's assessed runs are N7–N9 only.
- **(c) N6 (S3 → escalate, ≈ 68K tokens, ~8 min of lane)** is the only named-run proof of "escalate", and it sits in Phase 2. **Default:** keep it in Phase 2. Submit #1's pillar row cites N2/N3's J2 records and P3's escalate, labelled PILOT and not assessed, and states gap 1's status.
- **(d) The second rehearsal.** The slides say "Rehearse it twice"; the build prompt makes the second a Should. **Default:** keep it Should, but run it whenever Phase 3 has ≥ 20 min left before the final pack.

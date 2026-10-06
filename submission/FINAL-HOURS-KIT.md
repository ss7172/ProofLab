# iFabric: final-hours kit for judgement day

Prepared 2026-10-06 04:30 UTC (23:30 CDT, Mon). Builds on the team's own documents; it does not replace them:
`handoffs/ifabric-handoff-3/evidence-console-plan/presentation/JUDGING-DAY-GUIDE.html` (the run of show) and
`handoffs/ifabric-handoff-3/deliverables/PRESENTATION_DAY_INTEGRATION.md` (how the evidence folder is assembled).
This kit adds the timeline, the parts those documents leave out, a word-for-word script, the demo recording plan,
the 200-word summary and the risk decisions.

---

## 1. The clock (all times UTC; CDT = UTC minus 5)

| UTC | CDT | What | Gate |
|---|---|---|---|
| 04:30 to ~09:30 | 23:30 to ~04:30 | Implementation finishes (Phase 2 PRs, real runs) | Register v1 frozen and approved **before** the first assessed run |
| in parallel, now | now | Everything in section 3 (no implementation needed) | Owners below |
| ~09:30 to ~11:30 | ~04:30 to ~06:30 | Post-implementation runbook (section 4): named runs, findings, exports, pack, recording | All 7 artefacts exist |
| **by 12:30** | **07:30** | **Last AWS capture.** Account expiry is 13:52:47 UTC; everything from AWS must be in `evidence/` and in git by now | No AWS dependency left |
| **by 13:00** | **08:00** | `submit.sh <team-name>`, S3 read-back, MANIFEST verify on the downloaded copy | Read-back recorded in README section 7 |
| 13:00 to 14:00 | 08:00 to 09:00 | Buffer, two rehearsals, printouts | |
| **14:00** | **09:00** | **Final submit target** (build plan) | |
| 15:00 | 10:00 | Hard deadline | |

If implementation slips, cut in this order (from the team's cut order): PR-09i inventory, PR-18 console P1, PR-09b adversarial R-06, PR-08b tamper tally.
**Never cut:** register freeze and approval, C16 end to end with a passing and breaching named run, Level 1 proof, the evidence pack in S3, the gap list, the demo recording.

---

## 2. What judges score, and where each item is answered

Sources: masterclass and judging-criteria PDF (levels, axes, judgement day), AWS lightning talk, Dell "Agentic Assurance" talk, Accenture lightning talk.

**Gates (in order):** L1 Foundation on AWS Workshop Studio (required) → L2 MoDaaS controls + audit ledger + ServiceNow AI Control Tower → L3 AWS + ServiceNow sandbox, extended chain of evidence.

**Within each level:** Axis 1, controls complete end to end (dated threshold, working control, bound evidence, control test with a verdict). Axis 2, quality: live test, architecture, evidence a stranger can verify, honesty. Axis 3, bonus: extra controls, inline verdict, adversarial testing, second enforcement point.

**100-point scorecard (judges' sheet):** Technical Execution 30 · Impact and Innovation 30 · Challenge Fit and Feasibility 20 · User Experience 20. The run of show covers Technical Execution well; section 5 adds one minute for the other 70.

**Seven artefacts to bring (judging-criteria PDF):**

| # | Artefact | Where it lives in S3 | Owner | Status to tick |
|---|---|---|---|---|
| 1 | Evidence file | `evidence/` tree | builder | [ ] |
| 2 | Threshold document | `evidence/register/register.yaml` + `approval.md` + write-once proof | Sree approves, builder writes | [ ] |
| 3 | Control test tool | `python3 -m prooflab query ...` + console (PACK mode); source in `evidence/prooflab/` | builder | [ ] |
| 4 | Two named runs per control | `evidence/run-ids.txt` + `named-runs.md` (written before judging) | builder | [ ] |
| 5 | One-page architecture | `evidence/architecture.md` (+ printed copy) | builder + Arth | [ ] |
| 6 | Gap list | `evidence/gap-list.md` (A: Arth, B: ours) | builder, Arth reviews | [ ] |
| 7 | **Working or recorded demo** | `evidence/demo/` (mp4) + local copy on two laptops | presenter | [ ] |

Note: the team's `backup-demo-shot-list.md` calls the recording optional. The judging-criteria PDF lists the demo as item 7 of "bring these, whatever you built". Treat the recording as required; section 6 is the plan.

**The Dell framing (likely used by the AT&T and Dell judges):** "Breaking Barriers" AL0 baseline → AL1 degraded → AL2 compromised, scored on six dimensions (security, traceability, grounding, drift and uncertainty, reasoning and alignment, resilience and outcome), and a seven-step pattern. Map our work to it in one breath (section 5, step 6b):

| Dell level | Their ask | Our answer (where on screen) |
|---|---|---|
| AL0 baseline | Normal behaviour, identity, baseline traces | Register v1 frozen and approved; C9 baseline windows; L1 proofs (Overview) |
| AL1 degraded | Detect drift, uncertainty, stale context, tool failures; degraded mode or human review | C9 crossing with alert to the owner; C7 missing or late events; agent asks for evidence or escalates (Agent Trail FM-B → FM-C) |
| AL2 compromised | Detect manipulation, verify integrity, contain, reconstruct | Adversarial log (injected ticket → REFUSED, prompt attack → BLOCKED); kill switch; MANIFEST + corroboration; Six Questions reconstruct |

Their seven steps are our pipeline: identity and baseline (register, approvals) → ingest and govern data (declared tools, redacting collector) → grounded context (ledger + tool results) → bounded tools (gateway, Cedar, C16 cap) → detect drift, uncertainty, integrity (C9, C7, corroboration) → human approval or containment (ServiceNow owner, kill switch) → execute, verify, recover, replay (re-test closes the finding; Six Questions).

---

## 3. Do now, in parallel with implementation (no implementation output needed)

| # | Task | Owner | Done when |
|---|---|---|---|
| 1 | **Reply to Anshul with the 200-word summary by 12:00 UTC (7:00 CDT)** (section 9). Confirm "All three" against the build at send time | you | sent |
| 2 | Open the Outlook threads from Catalyst Ops / TM Forum: confirm judging slot time, room, submission method for the video, any format rules | you (or me once Microsoft 365 is connected) | noted in section 10 |
| 3 | Register v1: get Sree ready to approve the moment the pilots give the cap; prepare the approval note text in ServiceNow | builder + Sree | approval drafted |
| 4 | **Record demo segment 1 now** (Level 1: governed call, guardrail block, direct Bedrock denied, approvals). It does not depend on the controls | presenter | `l1.mov` saved |
| 5 | AI Control Tower: Execute Now; screenshot Inventory with our runtimes incl. `ifabric_assurance_agent`; Monitor sessions if present | Arth | screenshots in `servicenow/aict/` |
| 6 | "Before" timing test for the impact number: one person answers "was the spend cap respected for run X?" from the AWS console only; stopwatch | anyone not building | minutes recorded |
| 7 | Fill README sections that do not need results: 1 (claim, window plan), 2 (retention), 5 (layout), 9 (left out), 10 (people) | builder or me | no `<...>` left in those sections |
| 8 | `architecture.md`: one page from `architecture/one-page.md` + Arth's `servicenow-section.md` | me / builder | file ready |
| 9 | Gap list: merge Section A (Arth) + Section B; add the "built properly: yes, worked: no" items known so far | builder + Arth | merged draft |
| 10 | `decisions-log.md`: append the dated decisions in section 8 | me / builder | appended |
| 11 | `submit.sh` dry run: `bash ~/starter/submit.sh <team-name>` against a test folder, then read back (the page's command without a name prints usage, finding #63) | builder | dry run uploaded and listed |
| 12 | Rehearsal 1 of the script (section 5) on synthetic data, timed | whole team | under 15:00 |
| 13 | Print: run-ids (blank form), architecture page, gap list top 3, the Q&A card (section 7) | anyone | printed |

---

## 4. Post-implementation runbook (~2 hours, in this order)

1. **Stop assessed runs.** Note the declared event window (first and last run time).
2. Write `run-ids.txt` and `named-runs.md`: PASS and BREACH per control, plus RE-TEST and ESC. List every attempt; dropped ones stay marked NOT COUNTED.
3. ServiceNow, per finding: `check --cutoff <now>` → `export` → `case --out` for every named run. Assurance Agent result present (WRITTEN, or an honest REFUSED/BLOCKED).
4. Ask the tool every judge question once and save each answer: `python3 -m prooflab query --control C16 --run <BREACH>` (and C7, C9, a window, `--incident`, `--runs`). Anything slow or wrong goes in the gap list now.
5. Run the independent rechecker on the pack; record its output in `derived/`.
6. Fill README sections 4 (recompute-by-hand lines for C7 and C9), 6 (the honest failure, from what actually happened) and 8 (ServiceNow).
7. **Record demo segments 2 to 6** (section 6). Export one mp4, 4 to 6 minutes.
8. Build MANIFEST: `python3 evidence/tools/manifest.py build evidence`.
9. `submit.sh <team-name>`; read back: list keys, `head-object`, download, `manifest.py verify` → OK. Record key, ETag, time in README section 7. No edits after upload; a fix means rebuild, re-upload, re-verify, log it.
10. Open the console in PACK mode on the **downloaded** copy; click through all eight steps once.
11. Rehearsal 2 on real data with someone outside the build asking section 7's questions.

---

## 5. The 15-minute script (word for word)

Roles: **P** = presenter driving AWS and the console; **A** = Arth (ServiceNow); **S** = Sree (owner, answers approval questions). Screens follow the team's eight steps; one sentence per screen. Lines in quotes are said; everything else is done.

**0:00 to 1:00, the promise (P, Overview then Architecture)**
"Most hackathons ask what AI can do. This one asks us to prove it. Three agents fix a customer's broken broadband. We promised three rules about how they behave, approved and dated before any test. For every run, this screen shows whether each rule held, and the record behind it, which you can check without us."
Point at the three rule cards, then the architecture: "The model gateway is the only door to the model. ServiceNow is never in the agents' path."

**1:00 to 3:00, Level 1: it runs safely on AWS (P, terminal then L1 card)**
Run the four proofs. After each, one line only: "Governed call: action id and token usage." · "Prompt attack: blocked, zero tokens." · "Direct call around the gateway: denied." · "Each agent approved by a named person." Then: "That is our foundation, so everything after it can be judged."

**3:00 to 4:30, Level 2: recorded and visible (P → A, Evidence Ledger then AI Control Tower)**
P: "On the left is a log. On the right is the same call as evidence: tied to a rule, a version and a run." A: "And here AI Control Tower discovers our agents from AWS on its own."

**4:30 to 7:00, Level 3: humans are told, and the AI review is checked (A, Human Loop)**
A: "This breach became a ticket assigned to Sree. Her reply is recorded. If she had stayed silent, the silence would be recorded too. The finding closed only when a new run passed the same rule. A Nemotron agent reviewed the ticket, but our code checked every fact before anything was written, and a note we did not write shows red." Hover the long id: "One id links all of it."

**7:00 to 10:30, the judges ask, the tool answers (P drives; judge speaks)**
P: "Please ask any rule, any run or any time window." Type their words. Say nothing until the answer is on screen. Then: "The rule was dated before the run. Click any number to see its record." Offer "Verify without us" once.
If they don't ask: "Show me control 16 for run <BREACH>", then "control 9 between <T1> and <T2>".

**10:30 to 12:00, good decisions and a live, in-path verdict (P, Agent Trail then Live Replay)**
"Here the agent guessed on an unclear fault, and the outcome check failed. After the fix it asked for the right evidence first, and it validated. And here the budget check refuses the call that would overspend, before it happens. We trace decisions, not thoughts."
*(If C16 enforce is not live, say: "In this build the in-path check runs in observe mode; the post-run check is the authority. That's in our gap list.")*

**12:00 to 13:00, we attacked our own system (A + P, Adversarial then Architecture table)**
A: "What broke first: [top broken case] and what we changed. What held: [injected ticket refused, prompt attack blocked]." P: "Same checker in a second place, only the connector changed."

**13:00 to 13:45, impact and path to production (P) (added for the scorecard's 70 points)**
"Before this, answering 'was the spend cap respected?' took us [N] minutes in the AWS console. Now it takes seconds, and a stranger can recompute it. In Dell's terms: AL0 is our approved baseline, AL1 is drift and missing evidence detected and escalated, AL2 is tampering refused and reconstructed. Going to production is the same pattern again: a new register version, a new baseline, the same checks."

**13:45 to 15:00, what we couldn't fix (both, Gaps)**
"Built properly: yes. Worked every time: no. Here are our top three gaps, why, and what we'd do next." Read three, calmly. Then questions.

Rules on stage: one sentence per screen; never narrate an answer before it appears; if unsure, "That's in our gap list" and open it.

---

## 6. Demo recording plan (artefact 7)

- **Length:** 4 to 6 minutes, one mp4, captions on screen (no voice-over required). Also keep the segments.
- **Tool:** QuickTime (File → New Screen Recording) or Cmd+Shift+5; record a window, not the full screen; 1080p.
- **Before recording:** close tabs with tokens, IdeUrl, CockpitUrl, client secret or presigned URLs; light theme (`t`) for projectors.

| # | Segment (seconds) | Shows | Record when |
|---|---|---|---|
| 1 | Level 1 (60) | governed call (action id, usage); prompt attack blocked, 0 tokens; direct Bedrock denied; approvals | **now** |
| 2 | Level 2 (40) | log vs evidence side by side; AI Control Tower inventory | after named runs |
| 3 | Level 3 (60) | breach → ticket to Sree → reply or silence → Nemotron review checked → re-test closes | after `check`/`case` |
| 4 | The judge's question (60) | "Show me control 16 for run X" answered; one C9 window with an unknown hour; Verify without us | after pack build |
| 5 | Decisions and live verdict (40) | Agent Trail guessed → validated; the in-path refusal | after runs |
| 6 | Attacks and gaps (40) | what broke, what held; top three gaps | last |

Title card: "Team iFabric · Agentic Assurance · claim C-FM-01 · recorded <UTC time> on the submitted evidence pack". End card: the S3 key of the pack.

---

## 7. Questions to expect, and the answer to give

| Question | Answer (do, then say) |
|---|---|
| "Show me control 16 for run FM-B." | Type it. Silence until the answer shows. |
| "Was control 9 satisfied between two times?" | Type the window. "The missing hour is unknown, not healthy." |
| "Who acted? Was it approved? Can we trust it?" | Six Questions for their ticket. Read any PARTIAL and its reason. |
| "Can I check this without you?" | Verify without us; or "download the pack and run one command." |
| "Isn't your dashboard a control?" | "No. It can't refuse anything. The gateway and the budget check can." |
| "Was the threshold set after you saw the results?" | Register page: approval time vs first run time. "Its date is what makes it a test." |
| "How do you detect uncertainty before an unsafe action?" (Dell AL1) | Agent Trail: empty or unclear evidence leads to gather-evidence or escalate; C9 crossing alerts the owner. |
| "What if the evidence itself is tampered with?" (Dell AL2) | MANIFEST + read-back; corroboration against gateway records; the forged-note case shows red. "Corroboration, not proof; signing is out of scope." |
| "What's the business impact?" | The before/after timing; the 2.0M-token runaway that no platform limit stopped. |
| "How does this go to production?" | Same pattern per agent: new register version, new baseline, same checks; no agent rewrite. |
| "Is ServiceNow in the agents' path?" | "Never. A ServiceNow outage can't stop an agent." |
| "What couldn't you close?" | Gaps page, top three. |

---

## 8. Decisions and risks (log these in `decisions-log.md`)

| Decision or risk | Choice | Why | Fallback |
|---|---|---|---|
| Which tool judges drive | The team console (PACK mode) + `prooflab query` CLI | Integrated with the real pack, rechecker and ServiceNow cards | CLI only: `python3 -m prooflab controltest 16 --run FM-B --pack evidence/` |
| The separate `dashboard/` on branch team-ifabric-5th-oct | Do **not** present or submit it | It duplicates the console; two tools confuse judges | Keep as an offline backup only |
| C16 threshold | Derived from S1/S3 pilots by rule C16-cap, frozen in v1 before assessed runs | "A threshold chosen after the result is not a test" | If no pilots in time: freeze a cap justified by budget (account 2.5M tokens/h ÷ planned runs per hour), dated before runs |
| C16 enforce mode live | Use only if switched with the owner's OK before the run | Bonus "inline verdict" | Observe mode + post-run authority, stated as a gap |
| C9 breach does not occur | Do not move the threshold | Rule: never move a threshold to pass | Present C9 as SATISFIED with the missing-window INDETERMINATE case; gap list says no natural breach |
| AWS slow or down on the day | Recorded demo + PACK mode reads S3 copy offline | Judges read S3, not laptops | Printed answers for the named runs |
| Account expiry 13:52 UTC | All AWS captures by 12:30 UTC | Nothing can be re-pulled after expiry | Git + S3 hold everything |
| Secrets on screen | Recording and live: no tokens, IdeUrl, CockpitUrl, client secret | Disqualifying risk | Re-record the segment |

---

## 9. The 200-word summary for Anshul (TM Forum): due 7:00 AM CDT = 12:00 UTC, 6 Oct

Reply to Anshul's email. His brief: executive audience (problem, outcome, evidence, value, not implementation detail); include the team name and a solution title; it feeds preliminary judging and the Ten100 CSP executive session. Also saved as `~/Downloads/hackathon/iFabric_200_word_summary.txt`.

> Team iFabric | ProofLab: Evidence-Grade Assurance for Telecom AI Agents
>
> The problem. Operators will only let AI agents act on live networks if every action can be proven, not just performed. We governed three collaborating agents (customer, IT and network) fixing a broadband fault, and asked: can an auditor verify what they did, under which rule, and who was told?
>
> Controls selected, and why. All three: per-run token spend cap, automatic event recording, and performance drift against a frozen baseline. Evidence drove the choice: on the platform we measured a single agent run spend nearly two million tokens in five minutes with no limit triggering, leaving only 16 records for 174 model calls.
>
> Our solution, and why. ProofLab adds lightweight checkpoints where every agent action already passes, without rewriting agents. Each action is checked against owner-approved, dated rules and recorded as evidence tied to that rule and run. Breaches open a ServiceNow incident for a named owner, reviewed by a Nemotron assurance agent whose findings are themselves verified. Any auditor can recompute every verdict independently, in seconds.
>
> The value. Faster, independent audits; runaway spend and silent drift caught early; failures shown, not hidden; and one repeatable pattern from pilot to production.

Before sending: if any control is not complete end to end, change "All three" to the ones that are.

## 10. From the organisers' emails

- **Anshul Kumar (TM Forum):** 200-word executive summary by **7:00 AM CDT (12:00 UTC), 6 Oct**, as a reply to his email; used for preliminary judging and the Ten100 executive session (section 9).
- Still to confirm with the team: judging slot time and room, and how the demo video is submitted.

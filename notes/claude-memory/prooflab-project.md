---
name: prooflab-project
description: "What the user's team is building for the Trustworthy AI hackathon — ProofLab (controls C7/C9/C16, six deliverables, 2-minute judge query) — where the baseline context lives, the open AICT question, and the team winning playbook + SN handoff (verdict, roster: user = Sree + Arth, first planning decision)"
metadata:
  node_type: memory
  type: project
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T18:52:21.947Z
---

The user's two-person team (per the handoff) is building **ProofLab** for the Trustworthy AI & Data Hackathon ("Quest for Proof"; event began Sunday 2026-10-04). It is an evidence-backed assurance tool around the three supplied telecom reference agents (customer-experience, it-resolution, network-resolution). The agents call Nemotron models through the governed gateway `modaas-agw` and are deployed in workshop **Module 7** (user, 2026-10-04).

- **ORGANISER KICKOFF DECK** `~/Downloads/Agentic_Assurance_VaraF.pdf`: 24 pages, AWS Support team (Vara Prasad Talari), created 2026-10-04 12:24 CDT; printed slide 22 missing from a 30-slide deck. Read by Claude and 2 independent reviewers on 2026-10-05. It CHANGES these:
  1. **Closing the agent-judgment gap is core, not optional:**
     - p2: "guess confidently under ambiguity. Closing that gap is the game."
     - p5 YOURS TO BUILD: "The judgment they lack — know when to gather evidence or escalate, not act"; "A passing grade on the fault the reference agents cannot crack".
     - p23, three pillars: Close the gap / Build a Control ("at least one end to end; two named runs + a dated threshold doc") / Handover Proof ("An Evidence Pack that answers the six auditor questions"). "the most auditable solution wins."
  2. **Judged artifact = ONE Evidence Pack. A judge-as-auditor picks an incident from YOUR EVENT WINDOW and answers 6 questions "from your Evidence Pack alone" (p2, p7); 15 min live (p8).** The 6 questions verbatim:
     1. WHO "acted — which identity, on whose behalf, with what scope?"
     2. WHAT "did it touch: models, tools, resources?"
     3. AUTHORIZED "which policy, which version, evaluated where?"
     4. APPROVED "attestation for every asset in the chain?"
     5. INTEGRITY "can you show the records were not altered?"
     6. RECONSTRUCT "can you replay the run end to end with timestamps?"
     So evidence must cover the whole window, including the Hostile/Rogue phases, not just 2 hand-picked runs.
  3. **APPROVED and INTEGRITY are judged.** Our findings (#12 self-asserted approver; model swap without a new approval record; #13 no tamper evidence; #24 write token readable via the cockpit; #26 broad RBAC; EKS audit off) are therefore Evidence Pack weak spots to SURFACE/ANSWER or put in the gap list, not crypto to build: the masterclass still says signing and hash chains are out of scope. Needs an organiser ruling.
  4. **Three alert levels = "How you Win" (p6, p8):**
     - Alert 0 Vanilla/Baseline 3h: flow runs, safeguards active, evidence correlated end to end.
     - Alert 1 Hostile 4h: delays, tampered prompts & skills, conflicting context → prove detection, safe degradation, unsafe actions denied.
     - Alert 2 Rogue 3h: bypass attempts, unauthorized tool use, tampered records → prove containment, evidence preservation, reconstruction.
     - Who injects these is unknown. They land on verified gaps #3 (bypass), #24/#26 (record tampering) and the IT 403 (fail-closed `PolicyEngineUnavailable`, misreported by the ledger as a 500 on the model; notes #43).
  5. **The deck names only C7 and C9:** p21 "control 7 coverage needs 'expected' defined outside the graded agent; control 9 drift needs a stable baseline", with the MAVERIC twin as scenario switch and source of expected events. C16 is absent from the deck but alive via the masterclass and a judge's hint.
     - p8 rule "stay under one model request/second": S2 averaged ~0.6 model req/s (peak 49/min) yet used 80% of the hourly token ceiling, so the token ceiling binds first. Per-agent or per-account is unclear.
  6. p20 "If its decisions can't be traced, the entry scores nothing."
  7. **ServiceNow (AICT, AI Agent Studio, sandbox) is Levels 2–3 only.** The deck gives no mechanism.
  - **CONFIRMS:** gateway per-call line = figure of record, spans = cross-check, AgentCore Latency/Errors = drift signal (p19). The bar "A readable audit trail that links intent, control decisions and results" (p17). Sequential levels, with criteria likely p23.
  - **The deck repeats claims our live evidence disproves:** negotiation; ledger joined by trace id; a tamper-evident ledger recording every call; "traces have no durable exporter"; "next call gets 404" for models; one door; every call decided; per-agent identity; "one scenario fails" (all 3 fail by construction). Judges may believe these, so don't build the pack on them.
  - **User answers (2026-10-05):** C16 IS IN SCOPE. The user will provide the Evidence Pack format after all modules are reviewed, and more slides later.
  - **Still open for organisers:**
    - who injects Hostile/Rogue, and when
    - what INTEGRITY proof is expected, given hash chains are out of scope
    - is AICT required for Level 2, and how is it connected
    - is the 1 req/s rule per agent or per account
    - Evidence Pack format/contents: pending from the user
    - the full 30-slide judging deck
- **JUDGING LEVELS (new slide "HOW YOU WILL BE JUDGED", 23/30, shared by the user 2026-10-05 as `~/Downloads/WhatsApp Image 2026-10-05 at 01.27.28.jpeg`; NOT in the earlier slide extract or handoff):** sequential, and each level needs the previous one.
  1. **Foundation (REQUIRED):** "Demonstrate the use case in Workshop Studio using the agreed MODaaS guardrails and NVIDIA-supplied model. A submission without this foundation will not be judged."
  2. **Observability:** "AI Native ODA (ModaaS) controls are enabled and evidence collected in Audit ledger. Service[Now] Control Tower adds additional observability."
  3. **Extended chain of evidence (AWS Workshop Studio + ServiceNow Sandbox):** "richer evidence, a stronger chain of evidence and additional proof, including other models where appropriate."
  - "Within each level, the quality of your evidence is judged on the criteria on the next slide": most likely printed slide 24 = PDF p23 (the three pillars). The full deck has 30 slides and this PDF stops at printed 25. The user will provide more slides later.
  - The "use case" is the single fault-resolution use case. S1–S3 are test scenarios within it, not the levels.
  - AICT/ServiceNow is part of Levels 2–3, not Level 1.
- **Controls (masterclass slides):** 7 event recording, 9 drift, 16 spend cap. "One completed control is the minimum; a second and a third are bonus." The baseline handoff, not the slides, plans C16 first and notes that a correct BREACHED verdict still demonstrates a working control.
- **Done means (slides):** someone not on the team asks, e.g., "was control 9 satisfied for run FM-B?" and gets the answer, with the records behind it, in two minutes from the team's own tool.
- **Six MUST deliverables (slides, "Judgement Day"):**
  - evidence file
  - threshold document: metric, limit, exception tolerance, measurement basis, owner, version and date, "dated before any assessed run — we check the date"
  - control test tool
  - two named runs, one pass and one breach
  - one-page architecture sketch
  - gap list (scored)
  Hand-in mechanics are not on the slides: the kit's `starter/submit.sh` zips ~/evidence/, register.yaml, gap-list.md, run-ids.txt and (if present) sketch.png/sketch.jpg (submit.sh:8–9) and uploads them to the team evidence bucket.
- **Out of scope (slides):**
  - "Not asked for, and not scored": signing, hashing and Merkle trees over the ledger; a human actually answering an alert (the alert, its named recipient and the silence must still be recorded).
  - "Do not spend time on these": signatures, hash chains or Merkle proofs; a slide deck.
- **Baseline-plan differentiator (handoff):** a bounded Nemotron "investigator" that extracts cited evidence; deterministic host code validates it and computes verdicts.
- **AICT / human loop is open.** The meeting transcript says it is absolutely needed; the guide calls it facilitator-owned and absent by default. Facilitators (role `WSOpsRole`) provisioned ServiceNow AICT access in this account on 2026-10-04 between 22:02 and 22:45 UTC (see [[workshop-aws-access]]). Whether it is *required* still needs an organiser ruling. This is not a build instruction.
- **Timing:** the meeting transcript gives the event stop as Tuesday 10 a.m. CDT (probably 2026-10-06; not independently confirmed). The Workshop Studio dashboard shows 10/04/2026 09:00 AM and a 72-hour lifetime with no time zone. That is the account's lifetime, not a confirmed deadline.
- **Time-sensitive (handoff):** C9 needs closed clock-hours of baseline data, collected early and before assessed runs.
- **Improving or building agents is in scope (user, 2026-10-05: "we should look at ways of improving these agents as well or building our own agents… we need to fix a bunch of things").**
  - Slides "Your Task": "ALLOWED: Building more or changing the agents. You can use NVIDIA Nemotron model for this, and also to perform adversarial testing."
  - Module 7: "The evidence shape (intent before invocation, guardrail verdict on every model call, recorded disposition) is the shape judges score", and the failing scenario "is the challenge you carry into the build block".
  - Verified agent defects to weigh in the plan: no guardrail verdict, action_id, model or tokens in invocation records (#20); split trace_ids (#21); MCP 403 mislabelled 500 with no run id; the negotiation stub is never reached (#19); tool-invocation is written after the model call; S1 outcomes undetermined/refused; S2 is the known failure.
  - Constraints: changes go through CodeBuild → AgentConfig → re-approval. A new agent version is a C9/C16 "treatment", so pin baselines and dated thresholds to agent versions before assessed runs.
  - Options: fix the reference agents' evidence emission and/or build our own instrumented agent (Module 9). Decide in the plan, after all modules.
- **Planning input, 2026-10-05: the idea "don't touch the agents can't hold; first carry one run ID end to end" (shared by the user).** Claude's assessment from live data:
  - The run ID (CID) ALREADY survives without code change: baggage → gateway `modaas.run_id`. Per-run token sums worked on 5 runs, and ledger `correlation_id` joins all 3 agents. The platform propagates the run trace (PDP decisions and the AgentCore runtime log carry it).
  - Broken: only agent.py's ledger trace_id/action_id/tokens/guardrail fields; gateway-DirectResponse refusals carry no run_id; the durable gateway log `/aws/modaas/gateway` lacks run_id (the gateway's spans in `aws/spans` have it for 30 d; confirmed live 2026-10-05).
  - Suggested minimal fix: make the ledger record what the platform knows (inbound trace, action_id, model, tokens, guardrail outcome, correct refusal status). Do it via CodeBuild → AgentConfig before thresholds and C9 baseline, and decide IT's model (currently nano-9b) first.
  - A real approval record for a new version needs designing: a swap needed no re-approval and re-annotation adds no record.
  - The quote "lose both your records and your spending limit" was NOT found in the slides, transcripts or brief.
  - **VERIFIED 2026-10-05 ~06:15 UTC (swap run `fault-1791179282-8ef1a8`, run trace `e13e7b73…`):** the run ID and run trace survive end to end with NO code change.
    - gateway: 24 lines with run_id=CID, all carrying the run trace
    - PDP: 24 decisions with the run trace
    - durable /modaas/evidence: 24 records with correlation_id=CID and the run trace
    - durable /aws/modaas/gateway: 30 records with the run trace
    - durable `aws/spans`: 24 gateway spans with run_id = CID, 37,664 tokens (confirmed live 2026-10-05)
    - X-Ray: ONE trace containing all 3 agent runtimes plus 45 modaas-agw segments
    - Only the ledger trace_ids (0/12) differ.
    - So the agent fix is about the judged evidence shape, not run-ID propagation.
- **Judge's hint on C16 (2026-10-05, told to the user): "think of a risk matrix at any organisation"** (5×5 likelihood × severity; the image is at `~/Downloads/IC-5x5-Risk-Matrix-Template.webp`).
  - Claude's reading: justify C16 caps by risk (the masterclass "Why this value?"). Use tiered caps instead of one flat number, given measured S1 25–50K, S3 ~38K and the S2 runaway of 2.0M (≈80% of the shared hourly ceiling, so availability severity too).
  - The user floated a risk-classifier agent as a router. Conditions Claude gave:
    - The matrix → tier → cap mapping is pre-declared and dated in register.yaml; the classifier only selects a row.
    - Classification is deterministic or host-validated (the Hostile phase attacks LLM classifiers).
    - Each classification is recorded as evidence.
    - Per-invocation turn/token limits inside agents, because a router can't stop S2's in-invocation loop and model pause takes 33–41 s.
  - The same tier can drive the action mode (auto-resolve / gather-evidence / escalate) → "Close the gap". A budget-checking router = an in-path enforcement point (bonus).
  - Not decided; planning after all modules.
- **C9 drift insights from Module 8 (2026-10-05, Claude's reading, not decided):**
  - AgentCore `Latency` is per INVOCATION.
    - Ours take 6.5–8.8 s because each makes 2–5 model calls; the guide's capture made 1 call each (1.3–4.9 s). Per-call latency looks comparable, NOT shown to be model-dependent.
    - So invocation latency moves with call count and agent code, not only platform health.
    - The gateway's per-call duration is the figure-of-record latency, and it survives model swaps and call-count changes. AgentCore metrics = the runtime-health drift signal.
    - Freeze a dated baseline from OUR healthy hours, tied to model/config (the IT swap at 05:47 changes it).
  - Recommendation (not decided): hourly Maximum latency plus the Errors sum. In the S2 hour (05:00Z) Errors stayed 0; the IT runtime's hourly Average (71.6 s, vs 8.2–8.5 s for customer and network) showed the runaway too, but the Maximum (278.4 s) showed it most strongly, since an hourly average dilutes one long invocation across the hour's others (corrected 2026-10-05 after the handoff review: the Average did not hide it).
  - Fast is not healthy: a refused call returned in 1.05 s.
  - Tell "platform sick" from "agent looping" via the gateway's per-run call count (174 model calls in one IT invocation).
- **DELIVERABLE `gap-list.md` exists (repo root, draft since 2026-10-05; `submit.sh <team> --dir <repo>` packages it).** Kit format: What's missing / Why / Impact / If you had one more day. Entries:
  1. governed ≠ correct; disposition = keyword guess (the my-agent CID vs the helper)
  2. WHO: no per-agent identity (bootstrap-key, unprovisioned Keycloak, one shared runtime role)
  3. WHAT: undeclared tools usable; --tool doesn't declare
  4. AUTHORIZED: calls the platform refused (guardrail block, kill-switch pause) are recorded as ALLOW
  5. APPROVED: self-asserted approvals; changes not re-reviewed
  6. INTEGRITY: no tamper evidence; write token in specs (and, via the kit's own `pull-evidence.sh`, in the Evidence Pack)
  7. RECONSTRUCT: the stores only partly share a durable key (the CID is on the gateway's spans in `aws/spans` for 30 d, but not on `/aws/modaas/gateway`, refusals or the ledger's trace ids); refusals and loops are invisible in the ledger (reframed 2026-10-05 after live verification)
  8. no per-run spend limit (C16 is the fix)
  9. customer data in spans, plain-HTTP key, no classification
  10. the network agent queries the twin with element ids, gets "no twin data" (40×), and proceeds (added 2026-10-05, commit 56b9cb1)
  11. a governed tool's code can change under its approval: unqualified Lambda ARNs; the participant policy allows UpdateFunctionCode on team-*; mitigation idea = record CodeSha256 at approval and compare at run time (commit ace0442)
  - Keep adding gaps as found (user instruction).
  - 2026-10-05, from the Resources/Glossary/screenshot checks (lead's instruction): gap 2 + the authz pod log has no per-call records; gap 5 + EKS logging off (all 5 types), 18 empty signatures; gap 6 + no ledger verify route, the token also in runtime env (`get-agent-runtime`), bucket versioning unreadable; gap 7 + the telemetry export puts `modaas.run_id` on trace spans only, not on the `/aws/modaas/gateway` copy (a build gap; wording corrected 2026-10-05), PDP/authz logs pod-only, retention 30 d / 7 d, and the X-Ray action_id join as the one-more-day fix (superseded by the live-verification reframe below). No new numbered gaps.
  - 2026-10-05, after the independent reviews: gap 4's kill-switch 404 line has a trace id but no run or action id (it joins the run by trace id, via the policy decision and its /modaas/evidence record, which carries the run's CID and records ALLOW; corrected after the lead's live check); gap 5 de-duplicated; gap 6 + the kit's evidence pull copies the token into the Evidence Pack, the store keeps writer-supplied timestamps, and the hand-in bucket can't vouch (a VersionId is not integrity proof); gap 7's export wording corrected; the header now names gap 11 as a platform limit. Repo `.gitignore` now ignores `*.zip`.
  - Gap 7 reframed after live verification (2026-10-05). CONFIRMED: the gateway's trace spans in CloudWatch Logs `aws/spans` (30-day retention) carry `modaas.run_id` = the baggage CID, `modaas.action_id` and per-call token counts, one span per gateway request (S2 353 spans / 1,999,001 tokens; S1 `fault-1791179282-8ef1a8` 24 / 37,664; both equal the stdout figure of record). So a durable shared key exists for model and tool calls. Still missing: ids on the `/aws/modaas/gateway` copy (0 of 1,630), on refusals (the kill-switch 404's gateway line has none; it joins its run only by trace id, via the policy decision and evidence record) and in the ledger's trace ids. The one-more-day fix is the per-run join from `aws/spans` by run id.
- **Team winning playbook + SN handoff (received 2026-10-05):**
  - **Location:** repo root: `HACKATHON_WINNING_PLAYBOOK.md` (595 lines: §1 brief restated, §2 field guide, §3 checklist, §4 scorecard), `SERVICENOW_INTEGRATION_HANDOFF.md` (from Arth) and `prooflab/`. Copied in 2026-10-05; the original is in `~/Downloads/servicenow-integration-package/`. ServiceNow facts: [[servicenow-context]].
  - **Verdict (lead session's check; corrections in repo `notes/playbook/playbook-verification.md`):**
    - §1's brief and scoring rules (§1.1–§1.6, §1.8) and §4's scoring criteria are trustworthy: spot-checks trace to the Immersion Day slides, the meeting transcript and the master brief.
    - The platform claims in §1.0/§1.7, §2 (field guide) and §3 carry workshop-guide claims our live evidence disproves: Cedar denies unauthorized or tampered tools (§2, §3.9), a ledger verification (§2, §3.6), "no durable trace exporter" (§1.7), a ~15 s kill switch (§2), "S2 fails 7/10" (§1.7), a scenario switch for breach on demand (§1.7, §2). §3.10/§4.1 and §3.5/§4.4 overstate what ServiceNow shows or enforces. §3.3's C9 on Average latency is not disproven (the Average showed the S2 runaway too); the statistic is a planning decision. (Corrected 2026-10-05 after review.)
    - Use it as the strategy backbone for what judges reward, with that file's corrections. §1.8 "agents only on AgentCore or in ServiceNow" is an organisers' rule in the master brief (L91: "For AWS-hosted custom agents, the organizers specify Strands and AgentCore Runtime. ServiceNow-hosted agents are also allowed."; L93: "Submitted agents must operate within the provided AWS/ServiceNow environments."), not a platform constraint (corrected 2026-10-05).
  - **The user's review of the corrections (2026-10-05, the user's words to the lead):**
    - **Hostile/Rogue tests may use modified Cedar policies** ("for hostile and rogue tests, we can modify cedar policy"). Correction row 1 had overstated "these tests will show ALLOW". The live lever is the called tool's ToolConfig `spec.access.cedarPolicy` (projected to `modaas-toolconfig-<alias>`): a forbid rule keyed on toolName / arguments / dataClassification / toolMethod (e.g. classify customer-records and forbid restricted data; forbid a tool or argument pattern for all callers). Limits: not per agent (one shared principal; Cedar doesn't see the calling agent); not via the team ConfigMap (#33) or the AgentConfig overlay (#39); stateless, so no loop or token caps. Each edit is a cluster write (needs the user's OK); whether an edit resets approval is untested. See [[platform-verified-facts]] (Cedar levers).
    - **The grader and INTEGRITY** ("we are given a grader i believe, can that be used"): `score-run.py` grades evidence shape. It can support INTEGRITY as completeness (≥3 records, all three domains; :90-92), capture consistency (it refuses a capture whose "AUDIT TRAIL -- N records" header disagrees with the parsed count; :159-168) and a reproducible verdict, but not as proof of non-alteration (no hashes or signatures, no ledger verify route, a readable write token). Pair it with cross-surface corroboration (gateway lines, PDP decisions, `/modaas/evidence`, X-Ray, the AWS-written `/aws/bedrock/aict-invocations`) and a MANIFEST of SHA-256 hashes (correction row 2).
    - **Naming (row 9, reframed after the user disagreed):** both are right at different layers. Type `ifabric-…` into `new-agent.sh` / the CR (the generator rejects `_`, in a real run only after the CodeBuild build, so use `--dry-run` first); AgentCore/AICT then show `ifabric_…`, which meets the playbook's intent that judges can find our agents.
    - **Risks accepted by the user, not blockers** (the remaining risks are "allowed"): Arth's Global OAuth property change on the shared instance, the two `prooflab/servicenow` adapter bugs, and AICT Monitor likely empty for our agents. See [[servicenow-context]].
  - **Roster:** a two-person team: the user (= Sree; user confirmed 2026-10-05) builds the AWS side and is the control owner of all three controls per the SN handoff; Arth runs the ServiceNow workstream.
  - **Planning question (not a decision):** the playbook says "nobody checks their own work" (owner ≠ builder), but the owner (the user) also builds the AWS-side controls. Separation of duties needs a plan, e.g. who acts as assurance.
  - **FIRST planning decision:** the C9 baseline is clock-bound (closed UTC hours) and tied to model/config, and the IT agent is still on nano-9b (Module 7 swap). Decide revert-or-not BEFORE the baseline hours start.
- **PLAN ITEM (user, 2026-10-05; do after all modules):** build working versions of the three twin fixtures the kit's recipes fail to produce:
  - C7 expected events: sites + predicted RSRP from twin-dataset.json
  - C9 drift pair: baseline vs breach values with a dated threshold, working on a COPY of the dataset
  - trap ground truth: twin answer vs a real agent answer, with disagree flags
  - Note: the deployed network-twin Lambda reads its own packaged data, and S2 has no twin site.
- **Baseline context:** repo folder `hackathon-context/` (`START-HERE.txt` → `outputs/claude-hackathon-context.txt`; slide text in `work/hackathon-sources/slides-extracted.txt`). The user's words: "whatever you are reading is some baseline context but not the final plan."

**Why:** the user said: "our challenge is different than the audit response you found is not something these guys want." (Claude's reading: don't turn platform findings such as approver identity or tamper evidence into build targets.)
**How to apply:** platform observations are context, not goals. Build the complete plan only after every workshop module has been reviewed (see [[hackathon-working-agreement]]). Prefer [[platform-verified-facts]] over the handoff's assumptions.

Related: [[workshop-aws-access]], [[workshop-progress]], [[platform-verified-facts]], [[platform-observations-notes]]

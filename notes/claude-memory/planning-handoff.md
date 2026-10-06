---
name: planning-handoff
description: "The design to build is repo architecture/ (2026-10-05; captain direction in prooflab-project); the fact base and where planning started: repo PLANNING-HANDOFF.md (§0–§10, drafted 2026-10-05 and fixed after an independent review), the verification reports in repo notes/verification/2026-10-05/, the 2026-10-05 live verification results, and the platform-contract page check folded into §5.9 (no longer a pending input); claim labels C1–C8 replaced by descriptions; F11 superseded after a live re-check (architecture/work/10-f11-resolution.md); status 2026-10-05 ~23:58 UTC: architecture vetted, Phase 2 fixes running, the plan next"
metadata:
  node_type: memory
  type: project
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T23:58:00.000Z
---

**The design to build is repo `architecture/`** (2026-10-05): `ARCHITECTURE.md`, `one-page.svg` and `decisions.md`, still being written, from the inputs in `architecture/work/` (01 delta audit, 02 requirements, 03 decision options D1–D12). It follows the captain's architecture direction in [[prooflab-project]]; captain decisions are pending on D2, D3, D5, D7, D9, D10, D11 and the D8 mirror. `PLANNING-HANDOFF.md` remains the fact base that `architecture/` cites.

**The planning session started from repo `PLANNING-HANDOFF.md`** (repo root). The user asked for it once all modules were done; drafted 2026-10-05.
- **Sections:** §0 how to use it; §1 the goal; §2 what must be achieved (how we are judged); §3 what must be done (incl. the critical questions); §4 the winning playbook and how to use it; §5 verified platform reality; §6 gap list status; §7 live state (read-only, 2026-10-05 ~17:41–17:50 UTC); §8 standing rules; §9 open inputs and questions; §10 reference index.
- **Verification reports:** repo `notes/verification/2026-10-05/` (glossary, resources, cockpit screenshots, playbook analysis, the lead's playbook check, reference links, plus their check scripts). The corrected playbook check is `notes/playbook/playbook-verification.md`.
- **Independent reviews (2026-10-05):** one of the handoff, one of memory and the repo notes, and a claim verifier (authoritative where they differ). Their fixes to memory, `gap-list.md` and the notes were applied 2026-10-05; the handoff's own fixes were applied in parallel by a second fixer.
- **Live verification done (2026-10-05, after the reviews; report `res/verify-live.md` in the session scratchpad, which belongs in repo `notes/verification/2026-10-05/`):**
  - CONFIRMED: the gateway's spans in CloudWatch Logs `aws/spans` (30 d) carry the run id (CID), action id and per-call tokens, so C16's figure of record is durable (see [[platform-verified-facts]]).
  - CONFIRMED: the `/aws/modaas/gateway` copy carries no ids (a build gap, not by design; the collector deletes only 6 payload keys).
  - CONFIRMED: AgentConfig specs never hold the gateway key; it is only in the runtime env.
  - PARTLY: the model follows `dependsOn.models[0]` on all 5 runtimes and the CEL rule on `modelRef` is confirmed; which field wins when `modelRef` ≠ `models[0]` is untested.
- **The platform-contract page is done** (2026-10-05, 19:04–19:13 UTC). "What the platform gives you" was never pasted; it was extracted from the workshop KB into repo `notes/workshop-reference/platform-contract.md` and verified read-only (report `notes/verification/2026-10-05/platform-contract-verify.md`). It is no longer a pending input. In the handoff:
  - **§5.9:** the enforcement-point table, with verdicts
  - **§3b Q3 and Q11:** the inline-C16 and second-EP options, not decisions
  - **§9:** removed from the pending inputs, which are now the Evidence Pack format and more slides
  - **§10:** two command rows (the quoted gateway grep; PDP `--all-pods`)
  - Facts in [[challenge-requirements]] and [[platform-verified-facts]].
- **2026-10-05 ~19:15–19:30 UTC:** the handoff no longer uses the verification reports' numbered claim labels (they clashed with control C7); it cites claims by description, and §0 names the controls (C7, C9, C16). The reports keep their labels, with a note at the top. §5.9 records the participant-permission check: RBAC allows edits to the gateway policies and admission CRDs, but the admission VAP refuses them by its text, so there is no gap 12.
- **2026-10-05 ~19:31–19:50 UTC, independent review before the third commit:** 44 facts re-checked read-only; repo `notes/verification/2026-10-05/review-third-commit.md`. Fixes in the handoff:
  - §3b Q11: the ledger does take our writes with the token
  - §5.9: what the VAP leaves open: `components` (so Cedar changes on our own ToolConfigs pass it), CONNECT, and, by text, team-namespace routes
  - §8: the VAP's 9 protected namespaces
  - §0.2, §6 and §7.9: stale git-state lines
  - The report `platform-contract-verify.md` got a correction note and an addendum on the VAP.
- **2026-10-05 ~21:00 UTC, facts from the architecture work's live reads** (`architecture/work/03-decision-options.md` §2), re-checked read-only and propagated, each marked "(corrected 2026-10-05, from live reads during the architecture work)": the evidence bucket IS versioned (F1); the IDE role can't run Logs Insights, so `aws/spans` pulls run on the laptop (F2); the ModelConfig `external` enforcer is not a hook (F4); `aict-invocations` has no run or session id (F11; **SUPERSEDED**, corrected 2026-10-05 after live re-check at ~23:55 UTC: the `InvokeAgentRuntime` records carry the caller-sent CID, session id and traceparent in `responseElements`, and only the model-call records carry no ids; repo `architecture/work/10-f11-resolution.md`, propagated to the same files). Changed: the handoff (header, §3b item 18, §3c row 7, §4.2 rows 2 and 15 and its notes, §4.3, §5.3, §5.9, §6, §7.5, new §7.10), `gap-list.md` gap 6, `notes/playbook/playbook-verification.md` rows 2 and 15, `architecture/work/02-requirements.md` R-C-16, and [[platform-verified-facts]], [[prooflab-project]], [[servicenow-context]], [[workshop-progress]].
- Where the handoff and memory disagree, check the cited evidence; re-verify §7's live state before acting on it.

**Why:** a fresh planning session needs one entry point instead of re-reading every module note.
**How to apply:** to build, read `architecture/` first (the design; once its files exist, otherwise `architecture/work/`), then `PLANNING-HANDOFF.md` for the facts, then the memory files and reports they cite.

Related: [[prooflab-project]], [[workshop-progress]], [[challenge-requirements]], [[platform-verified-facts]], [[hackathon-working-agreement]]


## PAUSED by the captain (low battery), 2026-10-05T22:32Z: resume here
- **Last commit pushed:** 6905e47 (handoff + platform page). **Not yet committed:** repo `architecture/` (ARCHITECTURE.md §1–§15 complete, one-page.svg/.md, decisions.md D1–D13, work/01–03); the F1/F2/F4/F11 doc fixes (gap-list gap 6, PLANNING-HANDOFF.md, playbook-verification rows 2/15); the memory "Architecture direction (captain)" block.
- **Stopped mid-task. Re-run these, in parallel:**
  1. Add to `architecture/`: the risk register (`risks.yaml`), the AI inventory (`inventory.yaml`), the optional inventory-reconciliation control, the mapping to the Accenture talk's lifecycle, D14 (where the inventory and risk register live), and the chain on the one-page.
  2. An adversarial review → `architecture/work/04-adversarial-review.md` (the judges' Axis-2 questions, the LOSE list, the six auditor questions from the pack alone, platform facts, feasibility, one-page legibility).
  3. **DONE (2026-10-05):** Save `~/Downloads/Accenture_lightning_talk_v6.pptx` to `hackathon-context/sources/` with a text extraction (slides + notes), and add its key messages to [[prooflab-project]]. Both files are in the repo (`Accenture_lightning_talk_v6.pptx`, `.txt`), and the key messages are in [[prooflab-project]].
- **Status (2026-10-05 ~23:58 UTC):** the architecture is written, reviewed (`architecture/work/04`, `04b`) and vetted for infrastructure feasibility (`work/05`–`08`; F11 corrected in `work/10`). Phase 2 fixes are running (`work/11a`, `11b`), and a guardrails workstream has started (`architecture/guardrails/`). Next: the plan. The AWS credentials were issued 18:29:19Z and expire 2026-10-06T06:29:19Z.
- **Captain decisions:**
  - decided: D7 = a new `ifabric-` trio
  - decided: PASS and BREACH runs on the SAME agents
  - pending (recommendations in `architecture/decisions.md`): the C16 breach path, the C9 measure, the register date proof, the pre-run version gate, D14
- **Then:** apply the review fixes → show the captain the one-page → secret scan → commit + push → point the Firstmate prompt at `architecture/`.
- **AWS credentials:** last refreshed about 18:45 UTC, probably expired by resume. Ask the captain to refresh them.


## STATE at 2026-10-06T00:08Z: resumed and running (supersedes the pause note above)
- **Done:** infra vetting of the architecture (`architecture/work/05`–`08`: 0 blocked on the chosen path; AR-03 = single-file agents with EXTRA_PIP for libraries); two adversarial reviews (`04`, `04b`); twin check (`09`: twin unchanged); F11 resolved (`10`: InvokeAgentRuntime records carry the CID); handoff-3 code vetting (`13`: 152 tests pass; the Assurance agent analyser bundle is 5,792 chars and fits) and deliverables vetting (`14`); NVIDIA talk (`architecture/guardrails/01`) and guardrail feasibility (`02`); risk register + AI inventory added to ARCHITECTURE.md.
- **Running:** Fixer A (design/contract), Fixer B (feasibility/schedule), the handoff-3 reconciliation (`work/12`), the guardrails architect (`architecture/guardrails/AGENT-GUARDRAILS.md` + `PLAN.md`).
- **Next:** ONE integrator writes the integrated architecture (Arth's code as-is; boundary glue = OUR tasks) + the implementation plan → 3 independent reviewers (infra / judging / timeline) → fixer → memory copy + secret scan + commit/push. The build then starts in a FRESH session (this one's context is about 77 percent full).
- **Captain decision sheet** (recommendations; awaiting "approve all" or exceptions):
  - guardrails MAY block (safety EPs, recorded)
  - D15 Cedar demo = edit an existing tool's policy
  - D16 one store = the platform ledger (fallback: a laptop store)
  - D14 = repo YAML + Arth mirrors into AICT
  - pre-run gate blocks assessed runs
  - C9 = per-run Maximum + Errors, two-sided
  - the C16 breach path decided by the experiments
  - date proof = S3 write-once (ServiceNow corroborates)
  - C-7 register approval = an Arth-style ServiceNow Finding after the S3 proof
  - handoff-3: copy into the repo, rewording 2 doc lines that trip the scan
  - gateway-URL shim (glue)
  - raise the Assurance token limit via config
  - adapter bugs accepted (the captain already said "risks are allowed")
- **Captain/Arth deadlines (UTC):**
  - 01:00 decide C-7, merge Arth's code, tell Arth the gateway key is required
  - 03:30 ServiceNow credentials on the laptop + selftest
  - 03:30–06:29 refresh AWS credentials (they expire 06:29)
  - 03:30–04:00 freeze v1 + S3 upload + the owner's approval note
  - 08:30–10:00 first submit
  - 09:30 Arth's AICT exports
  - 12:30–13:00 final submit
  - deadline 15:00 (unconfirmed)


## CAPTAIN DECISIONS: APPROVED (2026-10-06T00:26Z, the captain answered "yes" to the full sheet)
1. Guardrails MAY block: each is a safety EP with one question; every decision is recorded. Controls don't block, except the C16 check.
2. D2: C16 safety ceiling always on, at <=300K tokens per run. The inline C16 check is the bonus; post-run is the floor.
3. D3: C9 = per-run latency Maximum + Errors, TWO-SIDED, plus an hourly roll-up for window questions.
4. D5: S3 write-once (T1) dates the register; the ServiceNow approval (T2) only corroborates.
5. C-7: register approval recorded as Arth's ServiceNow approval Finding, AFTER the S3 upload.
6. D9: the threshold pilots decide the C16 breach lever (natural vs on demand); if neither works, C7 becomes the first complete control.
7. D10 revised A: the fixed gateway guardrail (observed) + in-agent rails + Cedar edits + the C16 guard.
8. D11: the laptop is the hub; agents and rails run in AgentCore.
9. D13: the pre-run version gate BLOCKS assessed runs; record-only otherwise.
10. D14: inventory and risk register = repo YAML; Arth mirrors them into AICT. AICT stays part of the solution (Level 2).
11. D15: Cedar policies may be changed whenever that makes our agents work better or safer (captain's OK per change, recorded with its version), INCLUDING a test case where Cedar refuses a call, via an existing tool's policy. Per-agent rules go inside our agents (Strands Cedar handler).
12. D16: the "one evidence store" = the platform audit ledger, with every adapter writing to it (fallback: a laptop store).
Housekeeping:
- Copy handoff-3 into the repo, rewording the 2 doc lines that trip the secret scan.
- A gateway-URL boundary shim.
- Raise the Assurance token limit via config.
- Adapter bugs (a)/(b) accepted as known risks.
- Arth's code is used AS-IS; boundary glue = OUR tasks.
Also decided earlier:
- D7: a new ifabric- trio on nemotron-super-120b.
- PASS/BREACH on the same agents.
- Handoffs are record-only (no stripping).
- Show ALL runs in the dashboard's run catalogue, honestly labelled, with a declared event window.
- The twin is a tool only; plan item (b) (twin fixtures) is dropped.
- ServiceNow OAuth credentials are in ~/.prooflab-snow.env (mode 600; temporary: reset after judging).

- **Guardrail decisions APPROVED (2026-10-06T00:30Z, the captain: "approve DG2 - DG7"; DG-1 was already approved):**
  - DG-2: mask PII at the receiving agent's INPUT (not at the handoff; the handoff record keeps the raw payload's sha256)
  - DG-3: compact ALLOW records (one summary per invocation; every BLOCK/MODIFY its own record)
  - DG-4: the Cedar test rule on customer-records (applied with the captain's OK at run time, recorded)
  - DG-5: a Nemotron self-check only when a rule flags (through C16, fail closed)
  - DG-6: NeMo Guardrails stays out of the image (offline cross-check only)
  - DG-7: the ADV-H-02 fault case as designed (live only with OK, within budget)
  - Design: architecture/guardrails/AGENT-GUARDRAILS.md + PLAN.md (plain-Python rails; ≤~60K tokens total).

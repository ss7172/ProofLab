# Planning handoff: ProofLab (team iFabric)

Written 2026-10-05, 17:40–18:01 UTC, by a Claude subagent, for the next Claude session, which starts fresh and plans the build. Corrected 18:30–18:50 UTC after two independent reviews, a verifier pass, the user's own review and a live verification. All live checks were read-only. AWS credentials expired at about 18:20 UTC; after a refresh, the live verifier confirmed claims C1–C3 and part of C7 at about 18:40 UTC (§7, §9). This file makes **no planning decisions**; it gives the facts, the options and their evidence.

Labels used below:
- **UNVERIFIED**: not confirmed by us.
- **(corrected after review)**, **(corrected after the user's review)**, **(corrected after live verification)**: changed on 2026-10-05 after the reviews and verifier pass, the user's feedback, or the live verification.
- **recommendation (not decided)**: a view already held in memory. The plan decides.
- **reported by the reader, not yet verified**: comes only from the second playbook reader (`notes/verification/2026-10-05/playbook-analysis.md`).

---

## 0. How to use this handoff

### 0.1 Read order
1. This file, §1–§4 (goal, judging, what to do, the playbook). Use §5–§7 as a fact sheet.
2. The memory index (auto-loaded), then `prooflab-project`, `challenge-requirements` and `platform-verified-facts`. If the auto-loaded index says "9 gaps" or "next Module 10", it is a stale copy: the live `MEMORY.md` says 11 gaps and Modules 2–11.
3. `gap-list.md`, the scored deliverable.
4. `notes/playbook/playbook-verification.md` (the corrections table), then `HACKATHON_WINNING_PLAYBOOK.md` §1, §3 and §4.
5. `SERVICENOW_INTEGRATION_HANDOFF.md` §2, §6–§8 and §13.
6. `notes/platform-observations.md`: read the summary table; open an item (#1–#64) only when you need its evidence.

### 0.2 Citation keys
| Key | Points to |
|---|---|
| [mem: X] | Memory file `X.md`. Auto-loaded from `~/.claude/projects/-/memory/` (the mirror is identical). A snapshot is in repo `notes/claude-memory/`; the committed one (`bfb1ce6`) predates the last memory edits and lacks `reference-links.md`, so trust the live memory |
| [notes #N] | Repo `notes/platform-observations.md`, item N |
| [gap N] | Repo `gap-list.md`, entry N |
| [notes/verification/2026-10-05/F] | Today's verification reports (lead verdict, second reader, glossary, resources, screenshots, links) |
| [slides] | Masterclass PDF `hackathon-context/sources/Immersion-Day-slides.pdf`; text in `hackathon-context/work/hackathon-sources/slides-extracted.txt` |
| [kickoff deck pN] | AWS kickoff deck `~/Downloads/Agentic_Assurance_VaraF.pdf` (outside the repo; summarised in [mem: prooflab-project]) |
| [judging slide] | `~/Downloads/WhatsApp Image 2026-10-05 at 01.27.28.jpeg` ("How you will be judged", slide 23 of 30); the same slide is kickoff deck PDF p22 |
| [transcript] / [brief] | `hackathon-context/sources/Hackathon-meeting-transcript.txt` / `User-pasted-master-brief.txt` |
| [PB §x] / [SN handoff §x] | `HACKATHON_WINNING_PLAYBOOK.md` / `SERVICENOW_INTEGRATION_HANDOFF.md` at the repo root |
| [SN notes] | `notes/servicenow/servicenow-context.md` |
| [kit: F] | `~/firstmate-homes/TrustworthyAI/workshop-assets/starter/F`, or `workshop-static/…` where stated |
| [live] | Read-only check while writing this file (17:41–18:00 UTC) |
| [review] | The independent reviews of this file (18:02–18:20 UTC) and of memory and repo, with their own read-only live checks (18:03 to about 18:18 UTC) |
| [verifier Cn] | The verifier's verdicts on review claims C1–C8 (about 18:28 UTC): source code and snapshot only, live checks blocked by expired credentials |
| [verify-live Cn] | `notes/verification/2026-10-05/verify-live.md`: the live verification of C1, C2, C3 and C7 after a credential refresh (read-only, about 18:40 UTC), with its evidence and safe queries. It supersedes [verifier] for those four |
| [snapshot] | `~/firstmate-homes/TrustworthyAI/workshop-local/evidence-snapshots/20261005T173727Z/` (snapshot agent's report). "[snapshot, recomputed]" = counted again from its files after review |
| [user] | The user's answers, relayed on 2026-10-05 |
| [integrator] | The package integrator's report (copy, tests, bug reproduction), relayed on 2026-10-05 |

### 0.3 Where context lives
**Memory** (auto-loaded; an older snapshot is in `notes/claude-memory/`, see §0.2):

| File | Holds |
|---|---|
| `MEMORY.md` | The index, one line per file |
| `prooflab-project` | What we build and how it is judged: kickoff-deck findings, judging levels, controls, deliverables, the C16 risk-matrix hint, C9 insights, the gap-list summary, plan items |
| `challenge-requirements` | The Challenge section: six steps, finish line, the kit as it really behaves, critical questions, model choice, tool naming |
| `platform-verified-facts` | Evidence surfaces and join keys, governance mechanics, cockpit, Cedar levers, refusals recorded as ALLOW, kill-switch timing |
| `reference-agents-facts` | The 3 reference agents: ledger shape, IDs, tokens, scenarios; the self-check fails by construction |
| `workshop-progress` | Module-by-module record (Modules 2–11), live state and who created it |
| `platform-observations-notes` | How to use the notes file (#1–#64), plus candidate items not yet added |
| `servicenow-context` | AICT is live; its scope; its zero usage count; the `aict-invocations` log as AWS-written evidence |
| `hackathon-working-agreement` | How to work: read-only by default, writes approved so far, git, memory rules |
| `workshop-aws-access` | Account, profile, role limits, EKS, CFN stacks, gateway-key and cockpit handling |
| `workshop-local-shell` | The local stand-in for the workshop IDE and its scripts |
| `reference-links` | Pointer to `notes/references/links.md`, the 10 most-used links, and link traps (dead `cedarpolicy.com/en`, ServiceNow release prefixes, JS shells that return 200) |
| `aws-cli-install` | The AWS CLI is the official package in `~/aws-cli` (Homebrew Python is broken) |

**Repo** `~/firstmate-homes/TrustworthyAI/TrustworthyAI-iFabric/` (private GitHub `satyabrat-invences/TrustworthyAI-iFabric`):
- Root: `gap-list.md`, this file, `prooflab/`, `HACKATHON_WINNING_PLAYBOOK.md`, `SERVICENOW_INTEGRATION_HANDOFF.md`, `.gitignore`. The three package items are identical to the originals in `~/Downloads/servicenow-integration-package/` [integrator].
- `notes/`: `platform-observations.md`, `servicenow/` (synthesis + `raw/`), `ai-native-networks/`, `workshop-reference/` (Module 4 diagram), `verification/2026-10-05/`, `playbook/playbook-verification.md`, `claude-memory/`.
- `hackathon-context/`: the baseline handoff (`START-HERE.txt` → `outputs/claude-hackathon-context.txt`; baseline only, not the plan [mem: prooflab-project]) and `sources/` (transcript, brief, slides).
- `tools/workshop-local/`: backup copies of the local tooling.

**Outside the repo:** `workshop-local/` (live tooling, evidence snapshots, the MAVERIC clone); `workshop-assets/` (the kit, synced from the event bucket's `assets/`); `workshop-static/` (the bucket's `static/`, incl. `reference-impl/` and `scripts/twin-scenario.sh`); `~/Downloads/` (kickoff deck, judging slide, risk-matrix image `IC-5x5-Risk-Matrix-Template.webp`).

**Links:** `notes/references/links.md` (every link checked 2026-10-05); the raw report is `notes/verification/2026-10-05/reference-links.md`.

### 0.4 How to resume
1. Load the shell, bash only: `bash -c 'source ~/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; <cmd>'` [mem: workshop-local-shell].
2. On `ExpiredToken` (it happened at about 18:20 UTC on 2026-10-05, until a refresh), ask the user for fresh credentials from the Workshop Studio dashboard ("Get AWS CLI credentials", an `export AWS_…` block) and rewrite profile `hackathon` [mem: workshop-aws-access]. Until then no live check and no push can run (the secret scan fails closed, §8).
3. After a Mac reboot `/tmp/modaas-token` is gone. Re-extract it as memory describes, and never print it [mem: workshop-aws-access].
4. Re-run the §7 checks and compare, then the open checks in §9. If a gateway, PDP or authz pod restarted, its stdout is gone (§3a, item 5).
5. Then plan with the user: §3(a) first, then §3(b).

---

## 1. The goal

**In plain words.** The lab gives three telecom agents (customer, IT, network) that resolve a "home internet keeps dropping" fault. They run on Bedrock AgentCore and call NVIDIA Nemotron models through one governed gateway (MoDaaS on EKS). They "look good but guess confidently under ambiguity. Closing that gap is the game." [kickoff deck p2]. We must:
1. give the agents the judgment to gather evidence or escalate, instead of acting;
2. complete at least one control end to end (C7 event recording, C9 drift, C16 spend cap), with a dated threshold, a control test and two named runs;
3. hand over one Evidence Pack, from which a judge playing auditor answers six questions without us [kickoff deck p2, p23].

**The claim, C-FM-01:** "During fault resolution, the three collaborating agents meet our declared event-recording, drift and token-spend requirements." [slides; brief §2]. PB §1.0 words it slightly differently ("customer fault resolution", "drift and performance").

**The finish line (verbatim):** "You are done when somebody who is not on your team can ask “was control 9 satisfied for run FM-B?” and get an answer in two minutes, with the records behind it." [slides, "Your task"]

**The headline (verbatim):** "The winner provides the strongest evidence that every decision is explainable, every risk is controlled, and every claim can be independently verified in practice, the most auditable solution wins." [kickoff deck p23]

**Team:** two people [user]. The user (Sree) builds the AWS side and is the control owner named in the SN handoff. Arth runs the ServiceNow workstream [SN handoff §2, §14]. "ProofLab" is our name for the assurance tool [mem: prooflab-project].

---

## 2. What must be achieved (how we are judged)

### 2.1 Sequential levels [judging slide; mem: prooflab-project]
Each level needs the one before it.

| Level | Verbatim |
|---|---|
| L1 Foundation (REQUIRED) | "Demonstrate the use case in Workshop Studio using the agreed MODaaS guardrails and NVIDIA-supplied model. A submission without this foundation will not be judged." |
| L2 Observability | "AI Native ODA (ModaaS) controls are enabled and evidence collected in Audit ledger. Service[Now] Control Tower adds additional observability." |
| L3 Extended chain of evidence (AWS Workshop Studio + ServiceNow Sandbox) | "richer evidence, a stronger chain of evidence and additional proof, including other models where appropriate." |

"Within each level, the quality of your evidence is judged on the criteria on the next slide." In the kickoff deck PDF that next slide is the three-pillars slide (PDF p23, printed 24) [kickoff deck p22–p23]. The full 30-slide deck is not in hand: the PDF has 24 pages and lacks printed slides 22 and 26–30. AICT is part of L2–L3, not L1.

### 2.2 Three pillars [kickoff deck p23]
- **Close the gap:** "Give the reference agents the judgment to gather evidence or escalate". Also p5, "YOURS TO BUILD": "A passing grade on the fault the reference agents cannot crack".
- **Build a Control:** "At least one end to end; two named runs + a dated threshold doc".
- **Handover Proof:** "An Evidence Pack that answers the six auditor questions".

### 2.3 Axes and what loses marks [slides, "How you will be judged"]
- **Axis 1 (orders the field):** controls complete end to end. 0 = "Nothing to score"; 1 = "The minimum. You are in the running"; 2 = "Ahead of a team with one"; 3 = "The full set". Transcript: "Don't do things partially. Start with one control, finish until you see the evidence."
- **Axis 2 (decides the winner):**
  - Live test: "We name one control and one window and watch you produce the answer. Two minutes. If we have to trawl your logs, you lose the mark."
  - Architecture: "Would it survive a second enforcement point? Is the register out of the live path? Is the evaluator stateless? Does the control hold its own threshold?"
  - Evidence: "Bound to a control, a threshold version and a run. Verifiable by somebody who is not you. Gaps recorded rather than left blank."
  - Honesty: "“Built properly: yes. Actually worked: no” is the most useful answer a team can bring. One honest failure scores better than everything green."
- **Axis 3 (separates ties):** extra controls ("a second or third completed to the same standard"); continuous compliance ("a verdict formed inline, in the path, while it runs"); adversarial testing ("you attacked your own design and showed us what broke"); second enforcement point ("the same architecture, moved, with nothing rewritten").
- **WHAT LOSES MARKS:** "A threshold with no date, or dated after the test · records covering only some of the governed actions · evidence only your own team can verify · a finding closed without a passing re-test · a control that stores its own threshold · a design that only works in the request path".
- **"Five habits that keep the design honest"** [slides p15; transcript]: "The telemetry store never judges"; "The evaluator never remembers"; "The control register is never in the path of execution"; "The evidence ledger never interprets"; "Records are sealed where they are made [out of scope]".

### 2.4 Six MUST deliverables and hand-in [slides, "Judgement Day"]
| # | Deliverable | Verbatim requirement |
|---|---|---|
| 1 | Evidence file | "Exported, openable by us, and covering the runs you want scored." |
| 2 | Threshold document | "metric, limit, exception tolerance, measurement basis, owner, version and date"; "Versioned and dated before any assessed run — we check the date." |
| 3 | Control test tool | "We type the question; you do not narrate the answer." |
| 4 | Two named runs | "One that passes and one that breaches, with their run identifiers written down before we arrive." |
| 5 | One-page architecture sketch | "Components, what sits in the path of execution, and how an enforcement point invokes you. A whiteboard photograph is fine." |
| 6 | Gap list | "What you could not close, and why. This is scored, and it scores well." |

"If an artefact is missing we cannot score it." Bonus artefacts: more than one control; "An inline decision, live: show a verdict being formed in the path, not replayed afterwards"; the adversarial test log; a second EP "running, with a note of what you had to change". "Rehearse it twice before you present."

**Hand-in mechanics:**
- `bash submit.sh <team-name> [--dir WORKDIR] [--evidence-dir DIR]`. The team name is required; a bare call prints usage and exits 2 [kit: submit.sh:29–30; notes #63].
- It zips `~/evidence/` as it is, plus `register.yaml`, `gap-list.md`, `run-ids.txt` and `sketch.png/.jpg` from WORKDIR, with a file-list `MANIFEST.txt`. It uploads to `s3://$TEAM_EVIDENCE_BUCKET/submissions/<team>/` and prints a presigned URL (7-day expiry); never commit or paste that URL. The zip also stays in the directory it was run from [kit: submit.sh]. Token leak: MUST-FIX before submitting (§3d).
- Judges read the team evidence bucket [mem: challenge-requirements; PB §1.3]. The bucket `team-evidence-613052889143` is empty now [live]. The script's fallback bucket lookup returns empty in this account, so `TEAM_EVIDENCE_BUCKET` must stay set (env.sh sets it) [notes/verification/2026-10-05/playbook-verify-lead.md row 15].
- **Status of the six (local check, 18:35 UTC): only the gap list exists.** (1) Evidence file: none (the snapshot is outside the repo; `~/evidence` on the laptop is empty). (2) Threshold document: none (only the kit's template: C16 limit 2000, owner and version date `REPLACE_…`). (3) Control test tool: only the kit's C16 `evaluate.py`. (4) Named runs: none (all runs exploratory; no `run-ids.txt`). (5) Sketch: none. (6) Gap list: draft, 11 entries (§6).

### 2.5 Auditor questions, alert levels, slot, rules, out of scope
- **Six auditor questions** [kickoff deck p7]: "Judges pick an incident from your event window and ask six questions which are answerable from your Evidence Pack alone."
  1. WHO "acted — which identity, on whose behalf, with what scope?"
  2. WHAT "did it touch: models, tools, resources?"
  3. AUTHORIZED "which policy, which version, evaluated where?"
  4. APPROVED "attestation for every asset in the chain?"
  5. INTEGRITY "can you show the records were not altered?"
  6. RECONSTRUCT "can you replay the run end to end with timestamps?"
  So the pack must cover the whole window, including the Hostile and Rogue phases [mem: prooflab-project].
- **Schedule, "1.5 Days"** [kickoff deck p6, p8]: Orientation 1h → **Alert 0 Baseline 3h** ("the flow runs, safeguards are active, and evidence is correlated end to end") → Build block 3h → **Alert 1 Hostile 4h** (delays, tampered prompts and skills, conflicting context: prove "Detection, safe degradation, and unsafe actions denied") → **Alert 2 Rogue 3h** (bypass attempts, unauthorized tool use, tampered records: prove "Containment, evidence preservation, and reconstruction") → Reconstruction & Judging 4h ("Generate your Evidence Pack; 15 minutes live with the judges"). Who injects the Hostile/Rogue conditions, and when: UNVERIFIED.
- **Two rules:** "stay under one model request/second, and back up your work as you go because the account is destroyed when the event ends." [kickoff deck p8]
- **Out of scope** [slides]: "Signing, hashing and Merkle trees over the ledger"; "A human actually answering an alert. The response is not required; the alert, its named recipient and the silence must still be recorded". "Do not spend time on these": signatures, hash chains or Merkle proofs; "A slide deck. A whiteboard and a working tool beat both".
- **Allowed** [slides]: "Building more or changing the agents. You can use NVIDIA Nemotron model for this, and also to perform adversarial testing of your solution".
- **Kickoff rules:** ServiceNow Control Tower and the human loop are "absolutely needed" [transcript]. Name the AICT connector and our agents with the team name [transcript]. "Creating additional agents or elaborate ServiceNow workflows does not itself earn bonus points"; "Clone rather than modify shared examples" [brief]. "Avoid broad reconfiguration of shared risk frameworks" [brief]. PB §1.8's "agents run only on AgentCore or in ServiceNow; nothing hosted elsewhere" is supported by the master brief: "For AWS-hosted custom agents, the organizers specify Strands and AgentCore Runtime. ServiceNow-hosted agents are also allowed." and "Submitted agents must operate within the provided AWS/ServiceNow environments." It is the organisers' rule, not a platform constraint ("only" is read from "must operate within") (corrected after review) [brief L91, L93; verifier C5].
- **Judge hints** (to the user, 2026-10-05): "think of a risk matrix at any organisation" (§3b Q2) and "you can change the Cedar policies of the agents" (§3b Q11) [mem: prooflab-project, platform-verified-facts].
- **End time:** "The hackathon will officially end at 10 a.m on Tuesday morning. That's when work will stop and judging will begin." [transcript]. If that is 10:00 CDT on 2026-10-06, it is 15:00 UTC, about 20 hours after this file was corrected. Not independently confirmed [mem: prooflab-project]. The Workshop Studio dashboard shows a start of 10/04/2026 09:00 AM and a 72-hour account lifetime, with no time zone; that is the account's lifetime, not a confirmed deadline [mem: prooflab-project]. Then: "We have a preliminary round of judging where every single team will present to a series of judges"; finalist teams present again to a panel, and the winner is announced at Wednesday's Innovate Americas keynote [transcript].

---

## 3. What must be done

### 3(a) First decisions, time-sensitive first
| # | Decision | Why it can't wait | Evidence and options (not decided) |
|---|---|---|---|
| 1 | **IT agent model: keep `nemotron-nano-9b` or revert to `nemotron-super-120b`** | C9 needs closed hourly baseline windows tied to one model/config. AgentCore metrics exist only for hours with invocations, so a baseline hour costs runs on the frozen version; an hour with no data is UNKNOWN [mem: prooflab-project; PB §3.3]. About 20 h remain at 18:50 UTC (§2.5) | IT has been on nano-9b since the 05:47 UTC swap (generation 2) [live]. All other S1–S3 measurements are on super-120b [mem: workshop-progress]. Tokens per call are about the same on both; cost differs (~$0.064 vs ~$0.161 per M tokens) [mem: challenge-requirements]. Either change needs no re-approval (gap 5), so record it. **No clean baseline hour exists yet:** no IT, customer or network invocation since the 05:00Z hour, and that hour mixes IT on super-120b (S2 and the S1/S3 runs) with IT on nano-9b (the 05:48Z swap run) [review: live CloudWatch, 18:10Z]. **How a swap or revert works** (corrected after review and live verification): the runtime model is the env var `MODEL_ALIAS`, set by the operator. It follows `spec.dependsOn.models[0]` whenever `modelRef` is absent or equals it (live on all 5 runtimes); which field wins when they differ is unverified (the CRD's field description says the operator injects `modelRef` as `MODEL_ALIAS`). A CRD rule (confirmed live, verbatim) requires `modelRef`, once set, to be one of `dependsOn.models`. The Module 7 swap set both fields on the IT agent (`nemotron-nano-9b`) in one patch, so a revert must update both consistently (or remove `modelRef`). Check the runtime's `MODEL_ALIAS`, not the guide's `.spec.modelRef` checkpoint [notes/playbook/playbook-verification.md; verify-live C7] |
| 2 | **Agent changes before the register freeze and the C9 baseline** | Each new agent version is a C9/C16 "treatment" [mem: prooflab-project]. PB's order freezes `register.yaml` in hour 0–1 [PB §2]; the reader flags the conflict (row 21) | Options: change agents first, then freeze and start the baseline; or freeze now, scoped to agent versions, and bump the version after changes (PB §3.1 allows version bumps). All runs so far are exploratory [mem: workshop-progress] |
| 3 | **Thresholds, dated before the first assessed run** | "Versioned and dated before any assessed run — we check the date"; "Do not move the threshold to make it pass" [slides] | Values from our measurements (§5.6) and the judge's risk-matrix hint (§3b, Q2) |
| 4 | **The lever for named pass/breach runs** | Run ids must be "written down before we arrive" [slides] | The twin switch can't produce them (§3b, Q5) |
| 5 | **Evidence durability: re-snapshot before judging** | The C16 figure of record is durable: the gateway's spans in `aws/spans` carry the run id and per-call tokens for 30 days, but only until account teardown (corrected after live verification) [verify-live C1]. The gateway pod's stdout holds the same lines only for the pod's life. PDP and authz logs are pod-only [notes #27; notes/verification/2026-10-05/resources-verify.md]. The ledger PVC is deleted with the stack (reclaimPolicy Delete) [snapshot] | A snapshot exists (17:37Z, §7.6); it stays a backup. Re-snapshot before judging, and export the ledger into the Evidence Pack, because the account, with `aws/spans` and every log group, is destroyed at the end [snapshot; kickoff deck p8] |
| 6 | **ServiceNow wiring** | L2/L3 depend on it; AICT imports take ~15–20 min (UNVERIFIED) [SN handoff §9] | Needs `SNOW_*` credentials from Arth or the user (§4.3). Our agents' AICT "Managed" status is unknown [SN notes §3] |
| 7 | **Separation of duties with two people** | The register owner must approve thresholds before assessed runs [SN handoff §14] | See §3b, Q14 |

### 3(b) Critical questions the plan must answer
From [mem: challenge-requirements], plus those raised by today's verification:
1. **Which controls, and why?** C16 is certain (user: in scope); C7 and/or C9. Only C16 has a kit evaluator (`evaluate.py`, `_METRICS = {"16": …}`) [kit: evaluate.py; notes #62].
2. **C16 threshold.** Our runs: S1 24.8K–50.2K, S3 ~37.8K, swap-S1 37.7K, S2 2.0M; ~4.2K tokens per call on either model [mem: challenge-requirements]. The kit's 2,000, the guide's 900 and the slides' illustrative 10,000 would each breach every measured S1/S3 fault-resolution run (24.8K–50.2K) and leave no PASS fault-resolution run (single-agent runs such as `my-agent`'s 7,313 tokens fall under 10,000) (the SN handoff hard-codes 10,000 in its examples: reported by the reader). A judge hinted: "think of a risk matrix at any organisation" (5×5, `~/Downloads/IC-5x5-Risk-Matrix-Template.webp`). Recommendation (not decided): tiered caps from a matrix → tier → cap mapping pre-declared and dated in `register.yaml`; deterministic or host-validated classification; every classification recorded [mem: prooflab-project]. Also decide whether helper/investigator calls count [PB §3.2].
3. **Post-run only, or inline (bonus)?** The gateway has no per-run budget or halt; Cedar has no token attributes; the only limits are account-wide ceilings and pausing an asset [notes/verification/2026-10-05/playbook-verify-lead.md row 10]. Inline means building our own enforcement point. Recommendation (not decided): per-invocation turn/token limits inside agents, because a router can't stop S2's in-invocation loop and a model pause took 33–41 s [mem: prooflab-project].
4. **Evaluators for C7/C9** (none shipped); `evaluate.py` counts MCP lines as calls [mem: reference-agents-facts].
5. **Which lever produces named pass/breach runs, since the twin switch can't?** The `network-twin` Lambda reads its own packaged data; the recipes are broken; the twin has 3 sites and none for S2 [notes #57, #58; gap 10]. Evidence for candidates: S2's IT loop is a natural C16 breach (2.0M tokens, but 80% of the hourly budget in under 5 min [gap 8]); S1/S3 are 25–50K; a refused run writes 3 ledger records per agent instead of 4 (a C7 case) [mem: reference-agents-facts]; a model swap as C9 drift is UNVERIFIED (latency moves with call count, not shown to be model-dependent) [mem: prooflab-project]. The same threshold must hold for both runs [slides].
6. **The 2-minute answer:** one command → verdict + record ids, offline from the pack, for run ids and time windows [slides; PB §3.7].
7. **Evidence Pack coverage of the six questions**, given gaps 2–7 and 11. The pack format is still to come from the user.
8. **The judgment gap** (gaps 1, 10): S2 → gather-evidence, name the deciding evidence, propose a reversible step; S3 → escalate (already correct in our runs); S1 → auto-resolve [PB §1.7; mem: workshop-progress].
9. **Twin fixtures** (plan item): C7 expected events, a C9 drift pair, trap ground truth [mem: prooflab-project].
10. **The C9 statistic: Maximum + Errors Sum, or Average?** (corrected after review) In the S2 hour (05:00Z) the IT runtime had Errors 0, an hourly Average of 71.6 s and a Maximum of 278.4 s over 6 invocations. The customer and network runtimes averaged 8.2 s and 8.5 s in the same hour [review: live CloudWatch, 18:10Z; mem: workshop-progress]. Errors missed the runaway. The Average showed it (about 9× the other runtimes), and the Maximum showed it most strongly; an hourly Average dilutes one long invocation across the hour's other invocations. Latency is per invocation and moves with call count. A refused run is fast (1.05 s), so fast ≠ healthy. Recommendation (not decided): Maximum + Errors Sum, and/or the gateway's per-call duration [mem: prooflab-project; correction row 8].
11. **Can the second enforcement point actually wait or refuse?** A ServiceNow incident raised after the fact can't refuse anything: by the masterclass's own test every enforcement point does "Ask if this is allowed · Wait for the answer · Act on it · Record what happened · Seal the record", and it lists the "Human approval queue" as an EP type ("where a person decides"; "the verdict arrives hours later") [slides, "Enforcement points", "Five problems"; PB §1.6; notes/verification/2026-10-05/playbook-verify-lead.md row 12]. Options with evidence: an inline C16 admission check (our build); a ToolConfig `access.cedarPolicy` deny (a cluster write; it applies to every caller of that tool; whether it resets approval is untested) [mem: platform-verified-facts]; or present ServiceNow as `callback()` alerting, not as an EP. Agents have no action tool for a human queue to hold [mem: platform-verified-facts]. A judge also hinted (to the user, 2026-10-05): "you can change the Cedar policies of the agents" [mem: platform-verified-facts]; the user: "for hostile and rogue tests, we can modify cedar policy" [user]. Verified context (correction row 1): the live lever is ToolConfig `spec.access.cedarPolicy` (projected to `modaas-toolconfig-<alias>`). A forbid rule there can DENY on toolName, arguments, dataClassification or toolMethod, but for all callers (one shared identity; Cedar doesn't see the calling agent), and statelessly (no loop or token caps). The team ConfigMap `my-team-policy` is inert, named in 0 of 1,037 decisions (notes #33; [snapshot, recomputed]); the AgentConfig Cedar overlay isn't wired (notes #39) (corrected after the user's review).
12. **Fix the reference agents' evidence emission, or build our own agents?** Broken today: no action_id, tokens or guardrail verdict in the ledger; ledger trace_ids ≠ the run trace; MCP 403 recorded as a 500 on the model; tool-invocation written after the model call; the self-check fails by construction [mem: reference-agents-facts; notes #19–#21, #43]. The run id already survives end to end without code changes [mem: prooflab-project]. Recommendation (not decided): a minimal fix so the ledger records what the platform knows (inbound trace, action_id, model, tokens, guardrail outcome, correct refusal status) [mem: prooflab-project]. Every change goes CodeBuild → AgentConfig → approval.
13. **The hour-0 register freeze vs agent changes** (see §3a, item 2).
14. **Separation of duties.** The masterclass: "AND FOUR ROLES, BECAUSE NOBODY MAY CHECK THEIR OWN WORK" (accountable management, GRC, operations, assurance), and "the person who ran the test is not the person judged by it" [slides, "The GRC chain", "What governance actually is"]; PB §1.5 repeats it (owner ≠ builder). The brief: "Identify accountable management, GRC, operations, and assurance responsibilities … preserve independent review of control results. Do not invent people or approvals." But the owner (the user) also builds the AWS-side controls [user]. The plan must say how separation of duties and assurance work with two people.
15. **ESC findings:** the package never reads the ledger, so an escalation → Finding producer must be written. The kit's Rail 1 script has traps (no escalate check, not idempotent, no assignee) [SN notes §4; reported by the reader].
16. **OBSERVATION to explain (not a conclusion):** the gateway log has 290 distinct run ids, with run-id lines continuing to 17:33Z. The ledger has 17 correlation ids (16 match a gateway run id) and nothing after 09:13:40Z [snapshot]. This matters for C7 coverage: gateway activity with no ledger records. Facts that bear on it (not an explanation): 16 of the 290 gateway run ids are CIDs; 274 are trace-id-shaped (no CID was sent). Every gateway run-id line after 09:14Z (351, from 09:41Z to 17:33Z) is a `modaas-docs` MCP handshake on `modaas-docs-mcp-route` (`initialize`, `notifications/initialized`, `tools/list`, 117 each, about 15 per hour), and its run id equals its trace id, so no agent sent a run id. No `tools/call` or model line carries a run id after 09:14Z. The caller is unknown. The one ledger CID with no gateway run id is `my-agent-1791191585-4d9744`, the pause-refused run (§5.2) [snapshot, recomputed].
17. **AICT for L2:** required or not (organiser question); whether our runtimes are "Managed" (Monitor/evaluation only covers Managed agents) [SN notes §3]; naming our agents with the team prefix (§4.4). Monitor being likely empty for our agents is a risk the user accepts (§4.4).
18. **INTEGRITY: what can the provided grader support?** (added after the user's review) `workshop-static/reference-impl/score-run.py` grades the ledger timeline's evidence shape. Its "chain integrity" checks are completeness only: ≥3 records and all three domains (`score-run.py:90–92`), plus intent before invocation. It refuses a capture whose "AUDIT TRAIL -- N records" header disagrees with the parsed count (`:159–168`). It can't detect altered records: the ledger has no hashes and no verify route, and its write token is readable (§5.4). So it supports completeness, capture-consistency and a reproducible verdict. Combined with cross-surface corroboration (gateway lines and spans, PDP, `/modaas/evidence`, X-Ray, the AWS-written `/aws/bedrock/aict-invocations` record) and a MANIFEST SHA-256, that is corroboration, not proof of non-alteration (gap 6; correction row 2). Its guardrail-verdict check fails every reference run by construction (§5.6).

### 3(c) The playbook's order of work, adjusted by the corrections
| PB step [PB §2] | Adjustment | Why |
|---|---|---|
| 1. Hour 0–1: architecture, mentor, freeze `register.yaml` (owner Sree) | Draw the architecture and show a mentor now. Freeze only after the IT model and agent-version decisions, or freeze version-scoped and bump later. Settle separation of duties (§3b Q14) | §3a items 1–2 |
| 2. C16 end to end first: gateway records → evaluator → assessment → named runs → incident → <2-min query | Keep. Thresholds from our runs, not 10,000. Label C16 post-run unless we build an inline check. C16's figure of record is durable, so the C16 evaluator can read `aws/spans` by run id (not by trace; query in §10). The kit's `evaluate.py` reads pod stdout as shipped; the pod-log snapshot stays a backup (corrected after live verification) | Corrections rows 7, 10; §3b Q2–Q3 |
| 3. Start the C9 baseline early | Start only after item 1; hours need traffic; decide the statistic first | Correction row 8; §3a item 1 |
| 4. C7 end to end, expected events from outside the agent | Build the fixtures first (the twin can't do it on demand). Read the ledger as `/records?cid=` JSONL; `seq` can collide; explain the ledger/gateway observation (§3b Q16) | Correction row 5; [mem: reference-agents-facts] |
| 5. S2 judgment fix + S3 escalation → ESC incident | Evidence emission also needs fixing, in the reference agents or in our own agents (§3b Q12; the self-check can't pass otherwise). An ESC incident is alerting; it is an EP only if something waits on it | Corrections rows 4, 12 |
| 6. Adversarial cases + second-EP write-up | With today's policies expect ALLOW where PB expects "Cedar deny". The user: "for hostile and rogue tests, we can modify cedar policy": a forbid rule in the called tool's ToolConfig `access.cedarPolicy` can produce a DENY, for all callers (a cluster write, ask first; limits in correction row 1). Record what broke either way (corrected after the user's review). Run destructive record tests on exported copies only. Never touch shared Lambdas. Watch the budget | Corrections rows 1, 2; §3d |
| 7. Evidence Pack: MANIFEST, submit, readback, rehearse twice | No ledger "verification output" exists: INTEGRITY = cross-surface corroboration + MANIFEST. A VersionId is not INTEGRITY evidence (correction row 15). Pass the team name. Re-snapshot before judging. Redact the ledger token from `cr-status.json` before `submit.sh` (MUST-FIX, §3d). Align the layout with what `submit.sh` zips (the SN handoff puts `run-ids.txt` and `gap-list.md` under `evidence/`: reported by the reader) | Corrections rows 2, 15; §2.4 |

### 3(d) Planned steps that need the user's OK, or eat the shared budget
Budget: 100 model req/min and 2.5M tokens/h, effectively account-wide (one gateway replica) [mem: platform-verified-facts]. S2 burned 80% of the hourly tokens in under 5 min [gap 8]. Serialize runs and check headroom first; the user held S2 once at 2.14M input tokens in the last 60 min [mem: workshop-progress].

**MUST-FIX before submitting: the hand-in leaks the ledger write token** [verifier C8; kit: pull-evidence.sh, submit.sh]:
- `pull-evidence.sh:78` dumps the full Model/Tool/AgentConfig CRs into `cr-status.json`, including the literal ledger write token in every AgentConfig spec. A second copy is expected in the last-applied annotation (not verified live).
- `submit.sh` zips all of `~/evidence` as it is and uploads it to the team evidence bucket (judges read it). It also leaves `submission-<team>-<UTC>.zip` in the directory it was run from (`submit.sh:89–91`). The repo's `.gitignore` ignores `*.zip` since the post-review fix, but not `evidence/`.
- The git pre-push secret scan guards the repo, not the upload. `tmf639.json` (it may mirror CR specs) and the other pulled files are unchecked.
- So redact env values from `cr-status.json`, and check `tmf639.json`, before running `submit.sh`.

| Step | Writes to | Cost or risk | Source |
|---|---|---|---|
| Reference runs (`run-reference.sh` S1–S3), `ask-agent.sh` | AgentCore, gateway, ledger | S1 25–50K, S3 ~38K, S2 2.0M tokens | [mem: reference-agents-facts] |
| Cockpit `POST /api/agents/{name}/ask` | Invokes an agent (same cost as asking it via `ask-agent.sh`) | A helper question via `ask-agent.sh` (Q3) used 123K tokens; the only cockpit POST so far was the section-3 question | [mem: workshop-progress] |
| Build/apply/approve an agent (`new-agent.sh`, CodeBuild → AgentConfig → annotation) | ECR, cluster | New version = new C9/C16 treatment | [mem: prooflab-project] |
| Model swap or IT revert (AgentConfig patch) | Cluster | No re-approval; breaks baseline comparability | [gap 5] |
| Pause a model or tool (kill-switch demo) | Cluster | Hits every agent that uses the paused asset (super-120b: customer, network, `my-agent`; nano-9b: IT; a tool: any agent that calls it, declared or not); nano-9b served for 33–41 s; stale pause conditions remain | [notes #28, #36] |
| ToolConfig `access.cedarPolicy` edit (e.g. a forbid rule for Hostile/Rogue tests) | Cluster → `modaas-system` ConfigMap | Applies to every caller of that tool (no per-agent rule); propagation per source, untested; approval reset untested | [mem: platform-verified-facts; correction row 1] |
| `new-agent.sh --dry-run` / server dry runs | Nothing stored in the cluster; writes `~/agents/<name>/` and a `/tmp/<name>-agentcore.dry-run.yaml` that holds the ledger token (use umask 077) | Still ask (workshop write steps). The only way to check a name before a CodeBuild build (§4.4) | [mem: hackathon-working-agreement, workshop-progress] |
| Adversarial: write without a token, undeclared tool use, record tampering | Ledger, gateway | Pollutes the shared ledger and our event window; tamper tests on exported copies only | [notes/verification/2026-10-05/playbook-analysis.md §4.3] |
| Any change to `team-*` tool Lambdas | AWS Lambda | Never: shared and unpinned | [notes/verification/2026-10-05/playbook-verify-lead.md] |
| `side-entrance-probe.sh` | Creates 2 pods | Ask first | [mem: workshop-local-shell] |
| `pull-evidence.sh` | Local `~/evidence/` (or the out-dir) | Only reads the platform, but `cr-status.json` holds the ledger write token (MUST-FIX above) | [kit: pull-evidence.sh:78] |
| `submit.sh` | S3: the team evidence bucket (judges read it); a local zip | Prints a presigned URL. Zips `~/evidence/` as it is, including any unredacted `cr-status.json`, and writes `submission-<team>-<UTC>.zip` to the current directory (`submit.sh:89–91`). The pre-push scan protects the repo, not the upload | [kit: submit.sh] |
| ServiceNow `selftest` / `notify` / `check` / `export` | Shared instance (reads; `notify` creates incidents) | C9 "one incident per crossing window" could create many | [SN handoff §7.2] |
| Approve or delete `demo-crm-lookup`; touch any resource we didn't create | Cluster | Not ours; creator unknown | [mem: workshop-progress] |
| MAVERIC restart (§7.8) | Local Docker | Opens 0.0.0.0:8090 and :9094 on the LAN | [mem: platform-observations-notes] |
| Repo commits and pushes; notes items | Repo / GitHub | Secret scan first (§8) | [mem: hackathon-working-agreement] |

---

## 4. The winning playbook and how to use it

### 4.1 What it is, and the verdict
- **What:** `HACKATHON_WINNING_PLAYBOOK.md` (595 lines, 2026-10-05), the team's strategy doc. It came in the ServiceNow workstream's package (Arth, with Claude Code), next to the SN handoff, which points to it [SN handoff §0 item 7]; the playbook itself names no author. §1 restates the brief and the scoring; §2 is a field guide for agents and modules; §3 is a [MUST]/[BONUS]/[BEST] checklist; §4 is a self-scorecard.
- **Verdict** [notes/playbook/playbook-verification.md] (corrected after review):
  - **§1's brief and scoring rules (§1.1–§1.6, §1.8) and §4's scoring criteria are trustworthy.** Every spot-check traced to the slides, the transcript, the brief or the judging slide.
  - **The platform claims in §1.0 and §1.7, §2 (field guide), most of §3 (§3.2, §3.3, §3.5, §3.6, §3.8, §3.9, §3.10) and the ServiceNow items in §4.1/§4.4 import the workshop guide's or the handoff's assumptions**, several of which our live evidence disproves (rows 1–17 below).
  - Use it as the strategy backbone for what judges reward, with the corrections below for what the platform actually does.
- **Confirmed against primary sources:** the axis wording; the C16 worked example (FM-A 9,600 SATISFIED, FM-B 10,800 NOT satisfied, cap 10,000, G-FM-v1; illustrative: "copy the shape, not the values"); the five habits; "absolutely needed"; no bonus for extra agents or workflows; team-name prefix and clone-don't-modify; levels L1→L3; the 15-min slot; the six deliverables, six questions and three alert levels; out-of-scope crypto and slide deck. The owner "Sree" is the control owner's ServiceNow user (SN handoff §2), and per the user, Sree is the user.
- **Platform facts in PB §2 that hold** [notes/playbook/playbook-verification.md]: guardrail block = HTTP 200, `content_filter`, 0 tokens; C16 figure of record = the gateway per-call line, and the gateway's own spans in `aws/spans` carry the same per-call figures, by run id, for 30 days (corrected after live verification); ceilings; the Strands adapter drops an empty `tools` list; `/records?cid=` is JSONL and `/timeline` is text; approval annotations, and Approved ≠ runtime READY; the model swap (§3a item 1, same wording); `TMF639Projected=False`; direct Bedrock denied; AICT discovers AgentCore runtimes, and its role can also list AgentCore gateways and targets (corrected after review).

### 4.2 The corrections table (from `notes/playbook/playbook-verification.md`, the source of truth)
Copied row for row from that file, with its "(corrected …)" tags: rows 1, 2, 3, 7, 8, 9, 13, 14, 15 and 17 changed after review, rows 3, 7 and 13 last after live verification. The original lead report (`notes/verification/2026-10-05/playbook-verify-lead.md`) keeps the first wording and lists each change in its addendum. "Resources verifier" and "glossary verifier" are `notes/verification/2026-10-05/resources-verify.md` and `glossary-verify.md`.

| # | Playbook says | Verified reality (source) | Planning impact |
|---|---|---|---|
| 1 | §3.9 Hostile/Rogue expected defences: "unauthorized tool → Cedar deny", "tampered tool or skill → Cedar deny"; §2 "restrict `toolName` in the team Cedar ConfigMap" | Agents call undeclared tools and every call is ALLOW (gap 3). The team Cedar ConfigMap loads but was named in 0 of 1,037 decisions on both PDP replicas over the pods' whole life (#33; corrected after review, 2026-10-05). One shared principal `bootstrap-key` (#38). The AgentConfig Cedar overlay isn't wired (#39). Cedar never sees tool code, and Lambdas run unpinned `$LATEST` (gap 11, #59) | With today's policies these calls are ALLOW. A Cedar DENY is achievable by writing a forbid rule into the called tool's ToolConfig `access.cedarPolicy` (the live lever), keyed on toolName / arguments / dataClassification / toolMethod (e.g. classify customer-records and forbid restricted data; forbid a tool or argument pattern for all callers). Limits: not per agent (one shared principal, and Cedar doesn't see the calling agent); not via the team ConfigMap (#33) or the AgentConfig overlay (#39); stateless, so no loop or token caps. It is a cluster write (needs the user's OK); whether an edit resets approval is untested. (corrected after the user's review, 2026-10-05) |
| 2 | §2/§3.6/§3.9: "tampered ledger record → ledger verification fails"; "capture the ledger's own verification output"; "forged write → 401" | `audit-store.py` has no verify route and no hash chain or signatures (#13, gap 6). The 401 only shows a writer with no token is refused. The token is readable in every AgentConfig spec (#24) and in `get-agent-runtime` environment variables (resources verifier, today) | INTEGRITY must rest on corroboration across independent surfaces (gateway lines, PDP decisions, `/modaas/evidence`, X-Ray, AgentCore, and the AWS-written `/aws/bedrock/aict-invocations` record) plus a MANIFEST of SHA-256 hashes, never on a ledger self-check. The kit's grader (`score-run.py`) can support INTEGRITY as completeness, capture consistency and a reproducible verdict, but not as proof of non-alteration. It grades evidence shape (intent before invocation, a guardrail verdict per model call, result inspected, disposition recorded, scenario checks). Its "chain integrity" checks are completeness only: at least 3 records and all three domains (lines 90-92). It refuses a capture whose "AUDIT TRAIL -- N records" header disagrees with the parsed count, which catches doubled or partial captures (lines 159-168). It can't detect altered records: no hashes or signatures, the ledger has no verify route, and the write token is readable. (added after the user's review, 2026-10-05) |
| 3 | §1.7 "Traces have no durable exporter here"; §2 "the OTEL collector discards traces, so Cockpit Trace is empty"; §3.11 gap "no durable OTEL trace exporter" | The collector exports the gateway's spans to X-Ray, which writes them to CloudWatch Logs `aws/spans` (30-day retention). The gateway spans carry `modaas.run_id`, `modaas.action_id` and per-call tokens (#32; live 2026-10-05) (corrected after live verification, 2026-10-05) | **Don't put that gap in the gap list; it's false.** `aws/spans` is the complete durable join surface for RECONSTRUCT and C16 (by run id; action_id → `/modaas/evidence` → PDP). X-Ray carries the same fields as segment metadata but truncates long runs (S2: 22 of 174 model calls) (corrected after live verification, 2026-10-05) |
| 4 | §1.7 "S2 currently fails (7/10). Keep S1 and S3 passing" | Our runs: **S1 FAIL 6/8, S2 FAIL 5/10, S3 FAIL 8/10** (7/10 is the guide's number). All three fail by construction: the reference agents write no guardrail verdict, so the self-check fails every run (gap 4; memory `reference-agents-facts`) | "Close the gap" also needs the agents' evidence emission fixed (or our own agents), not just S2 logic |
| 5 | §1.7/§2 Module 10: "use the scenario switch to produce a passing run and a breaching run on demand" | The `network-twin` Lambda reads its own packaged dataset, so a breach on demand can't reach the agents (#58). The recipes are broken (#57). Agents query with element ids and get "no twin data" (gap 10). The twin has no site for S2 | Named pass/breach runs need another lever. Planning picks it (for C16, S2's 2.0M-token runaway is a natural breach) |
| 6 | §2 kill switch "~15 s to stop, ~50 s to resume" | Measured: nano-9b 33–41 s (calls still served meanwhile); super-120b ≤2 s; tools ~1–7 s; resume ~24–35 s. The pause is recorded as ALLOW in decision records (gap 4, #36) | Record requested vs effective times (the playbook says so). Don't quote 15 s |
| 7 | §1.0 "Each step is a span carrying the same trace id and run id"; §2 "Keep `traceparent`, or gateway run ids fragment" | The gateway's run id is the baggage CID (via the authz correlation id; with no CID, the trace id). Its trace spans in CloudWatch Logs `aws/spans` (30-day retention) carry `modaas.run_id` = CID, `modaas.action_id` and per-call tokens, one span per gateway request (S2: 353 spans = 1,999,001 tokens; S1: 24 spans = 37,664, both equal to the gateway stdout figure of record). The OTLP access-log copy in `/aws/modaas/gateway` carries no ids (0 of 1,630; a build gap, cause unknown). Agents mint their own trace ids, so ledger trace_ids ≠ the run trace. Refusals (kill-switch 404, GET 405) carry no run id. (corrected after live verification, 2026-10-05) | Propagate the CID via baggage. C16's figure of record is durable for 30 days in `aws/spans` (until account teardown): compute C16 from spans by run id, not by trace; X-Ray truncates long runs. The pod-log snapshot stays a backup. PDP/authz logs are pod-only. (corrected after live verification, 2026-10-05) |
| 8 | §3.3 C9 = "Latency **Average** / Errors Sum, period 3600" | Our Module 8 analysis: S2's runaway showed Errors = 0, but hourly latency showed it: in the S2 hour (05:00Z) the IT runtime averaged 71.6 s against 8.2–8.5 s for the other two runtimes, with a **Maximum** of 278.4 s (6 invocations). AgentCore latency is per INVOCATION and moves with call count (memory `prooflab-project`, `workshop-progress`) (corrected after review, 2026-10-05) | Planning decision, not made yet. Recommendation (not decided): Maximum + Errors Sum (and/or gateway per-call duration). The Average showed this runaway too, but an hourly Average dilutes one long invocation across the hour's others, and Errors missed it entirely (corrected after review, 2026-10-05) |
| 9 | §2/§3.8 "`ifabric_…` for every new agent, tool and CR" (SN handoff: "lowercase where Kubernetes requires it") | Both are right, at different layers. The name typed into `new-agent.sh` (and so the CR) must use hyphens: Kubernetes object names can't contain `_` (RFC 1123), and the generator `new-agent.sh` calls validates the name. `make-agentcore-agents.py` (line 78) requires `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`, i.e. 2–40 lowercase letters, digits and `-`, starting with a letter; underscores and uppercase are rejected (line 287: "it becomes the runtime name"). In a real run the check fires only after the template copy and the CodeBuild build; only `--dry-run` checks first. AgentCore and AICT then show the underscore form: the runtime name maps `-` → `_` (per a code comment; seen live: CR `my-agent` → runtime `my_agent-9AyPFbHh5Z`) (corrected after review and the user's review, 2026-10-05) | The playbook's intent is right: judges will find our agents as `ifabric_…` in AgentCore/AICT. Type hyphens: name CRs `ifabric-…` (at most 40 characters) and check a new name with `new-agent.sh --dry-run` before the real run. No separate server dry run is needed (corrected after the user's review, 2026-10-05) |
| 10 | §1.0 "the shared model gateway is where … budget is decided, and a run can be halted" | The gateway counts tokens per call but has no per-run budget or per-run halt. The only limits are account-wide ceilings and pausing a model/tool, which stops every run. Cedar has no token attributes. §3.2 itself concedes "label C16 post-run honestly" | Inline C16 = our build (bonus), not a platform feature |
| 11 | §3.10/§4.1 L2 "Show Monitor sessions or traces if available" | AICT's usage query filters `eventName="InvokeAgent"`; our AgentCore traffic has zero such events (memory `servicenow-context`). The SN handoff's discovered list (6 AI Functions) doesn't include `my_agent` | Expect Monitor to be empty for our agents. State it as a gap; check `my_agent` (and new `ifabric_` agents) after the next import |
| 12 | §3.5/§4.4 "ServiceNow human approval queue" = second enforcement point | By the playbook's own test (§1.6: an EP must "ask, wait, act"; "a dashboard … can refuse nothing"), a notify-only incident can't refuse anything | It counts as an EP only if something waits on the human (e.g. the S3 escalation holds the change until approved). Design risk for the bonus claim; planning decides |
| 13 | §2 "Four injected values … never hard-code them" | AgentConfig specs never hold the gateway key, under any name (value-compared live); their only credential is the literal 32-character ledger token `AUDIT_WRITE_TOKEN` (#24). The operator injects the gateway key into every runtime's env as `OPENAI_API_KEY` and `AGENTCORE_GATEWAY_MCP_TOKEN` (both the `agw-apikeys` eval key, one shared key for all agents). `get-agent-runtime` returns both the key and the ledger token in plain text. No `GATEWAY_API_KEY` exists (corrected after live verification, 2026-10-05) | Fine as agent-code advice (read env, fail closed). The ledger token can't be kept out of the CR; it's a gap-list fact (gap 6). `pull-evidence.sh`'s `cr-status.json` therefore holds the ledger token, not the gateway key (corrected after live verification, 2026-10-05) |
| 14 | §2 "direct AgentCore creation [is] denied" | True for the participant role. The glossary verifier reports the IDE role can create, update and delete the AgentCore gateway (policy re-read by an independent reviewer; not attempted; corrected after review, 2026-10-05) | Note only; never do it |
| 15 | §3.6 "record the S3 version id"; SN handoff §11.7 "integrity rests on … S3 versioning" | Our role is denied `GetBucketVersioning`, object lock and lifecycle on `team-evidence-…` (no allow: the participant policy grants only GetObject, PutObject, DeleteObject and ListBucket on `team-evidence-*`). The bucket is empty today. `submit.sh`'s fallback bucket lookup (`… \| [0]`) returns empty in this account; it works only because `TEAM_EVIDENCE_BUCKET` is set (corrected after review, 2026-10-05) | A VersionId is not INTEGRITY evidence: participants can overwrite or delete objects and can't list or read versions, Object Lock is unknown, and `submit.sh` (`aws s3 cp --only-show-errors`) prints no VersionId (`head-object` after upload shows one only if versioning is on). Rest INTEGRITY on the MANIFEST hashes plus cross-surface corroboration. Keep TEAM_EVIDENCE_BUCKET set (corrected after review, 2026-10-05) |
| 16 | §3.6 APPROVED "export `.status.governance.approvals` for each asset used" | Approvals are free-text annotations with an empty `signature`; EKS audit logging is off (all 5 types); a model swap needed no re-approval (gap 5, #46). Tools actually called ≠ tools declared (gap 3) | "Every asset in the chain" must include tools actually called, and must flag approvals older than the running version |
| 17 | §3.6 AUTHORIZED "keep the Cedar/PDP decision lines for both replicas" | Consistent, but decision lines carry no principal (it's in `/modaas/evidence`: `bootstrap-key` on every authenticated call; corrected after review, 2026-10-05); guardrail blocks and pauses are recorded ALLOW (gap 4); the PDP logs are pod-only | Capture both PDP pods before any restart. Report the real outcome per call via the gateway line |

Notes: row 1's earlier "0 of 478 decisions in 48 h" counted one PDP replica (the pods were then about 31 h old); the 1,037 is the snapshot recount of both replicas (§5.1). Rows 3, 7 and 13 rest on the live verification [verify-live C1–C3]. Row 8's statistic is still open (§3b Q10). Rows 14, 15 and 17 rest on the memory/repo reviewer's live reads, outside the verifier's C1–C8.

### 4.3 The ServiceNow integration package (repo root)
**What it gives** [SN handoff §3–§8]:
- **The Finding contract (§6):** `control_ref` (C7/C9/C16/ESC), `control_id`, `threshold_version` (exactly the frozen register version), `scope_kind` (run/window/interval/escalation), `scope_id`, `verdict` (BREACHED/ESCALATED/INDETERMINATE/SATISFIED), `summary`, `detected_at`, `evidence` (resolvable refs, §8.2 prefixes), `kind`. Deterministic `finding_id = ifabric:{control_ref}:{threshold_version}:{scope_kind}:{scope_id}:{kind}`, so a re-run reuses the incident.
- **The CLI:** `python3 -m prooflab.servicenow selftest | notify --finding F [--dry-run] | check --finding F --cutoff T | export --finding F`; exit 0/1/2. Notify only for BREACHED, ESCALATED and monitoring-gap, off the agent's path (§7). Delivery states DELIVERED/FAILED/UNVERIFIED/OUTCOME_UNKNOWN/DRY_RUN; response states RESPONDED/AWAITING_RESPONSE/NO_RESPONSE_OBSERVED/RESPONSE_UNKNOWN/NOT_DELIVERED (`check` exits 1 on NOT_DELIVERED and RESPONSE_UNKNOWN). An append-only, fsync'd `evidence/servicenow/delivery-log.jsonl`.
- **The rest:** an evidence layout (§8.3), the query-tool output (§8.7) and a six-question mapping (§8.7). Correct the mapping before use: WHO can't come from the gateway identity; there is no ledger verification for INTEGRITY; spans can't be joined from ledger trace ids (reported by the reader, rows 5a–5e; consistent with gaps 2, 6, 7).
- **Tests:** 46 passed offline against the fake server in our environment [integrator].

**What it needs:**
- `SNOW_INSTANCE`, `SNOW_CLIENT_ID` and `SNOW_CLIENT_SECRET`, from Arth or the user's password manager [SN handoff §5.3]. Read the secret with `read -rs` and never print it. If a file is used: `~/.prooflab-snow.env`, mode 600, outside the repo. Optional: `SNOW_OWNER_USER` (defaults to the control owner's ServiceNow user, see SN handoff §2), `SNOW_INTEGRATION_USER`, `PROOFLAB_DELIVERY_LOG`.
- Add the secret's exact value to `pre-push-secret-scan.sh` (reported by the reader; an edit to a local script, so ask first).
- Glue we must write: the evaluator runner (`publish()` exists only as a doc snippet), the C7/C9 evaluators, the ESC producer from the ledger, the MANIFEST builder and the query tool (reported by the reader).
- ServiceNow-side claims are UNVERIFIED by us: the shared instance `platformdemoh8`, connection "iFabric Hackathon 2026", integration user, OAuth app, test incident INC0010231, 6 discovered AI Functions [SN handoff §2]. They fit our AWS-side view: AICT assumes our role about every minute [SN notes §1]. Per the SN handoff, `platformdemoh8` is the shared hackathon instance; memory was corrected on 2026-10-05, and it is still UNVERIFIED by us [mem: servicenow-context; notes/verification/2026-10-05/playbook-verify-lead.md].

**Acceptance checklist** [SN handoff §13]: `prooflab/` in the repo and tests pass · `selftest` OK · `register.yaml` frozen and dated, owner set for all controls, before assessed runs · an assessment for every scope · exactly one incident per BREACHED/ESCALATED/monitoring-gap (re-run → reused) · each breaching named run has a DELIVERED incident, with `check` and `export` done · the S3 escalation path proven once (ESC incident with the ledger chain) · the query tool shows verdict + records + human-loop line in under 2 min, offline · `MANIFEST.json` generated, submitted, read back · `gap-list.md` includes the handoff's §11 entries plus ours, and `architecture.md` shows the ServiceNow EP and AICT · rehearsed twice.

**Two adapter bugs, CONFIRMED** (code reading + offline reproduction [integrator]). These are Arth's code. The user accepts them as risks (2026-10-05), not blockers (§4.4) [user]. Fix direction only:
- (a) `notify --dry-run` returns and logs DELIVERED, not DRY_RUN, when a matching incident already exists (`prooflab/servicenow/notifier.py:132-136`; the log entry at :89-92 has no dry-run marker; `cli.py:73` exits 0). The SN handoff's own §5.4 dry run on `examples/test_finding.json` would hit it, because, per the SN handoff, INC0010231 already exists for that finding (UNVERIFIED by us). Nothing is written to ServiceNow, but the evidence log entry is wrong. No test covers it. Fix direction: honour dry-run before the reuse path, or mark dry-run log entries.
- (b) A `sys_journal_field` read that returns 0 rows with HTTP 200 (the live ACL behaviour per SN handoff §11 item 8; UNVERIFIED by us) leaves `readable=True`, so the RESPONSE_UNKNOWN guard (:230) never fires. The `sys_updated_by` fallback (:199-203) works only while the owner is the last updater; a later update by anyone else yields NO_RESPONSE_OBSERVED after the cutoff (:233-234). The fake server models the ACL only as a 403 (`tests/fake_servicenow.py:173-174`). Fix direction: treat an empty journal read as unknown, or use another response basis (e.g. the `notes_display` that `export` already fetches).
- Also, by reading the code: `--dry-run` is not offline; every command builds a live client, and the owner, caller and incident lookups run before the dry-run check (`cli.py:60`, `notifier.py:115-131`).

**Reader-flagged issues** (reported by the reader, not yet verified):
- SN handoff §3's diagram says AICT discovers "models, traces"; we see runtimes and gateways only.
- Its §11 gap 1 repeats Module 11's false "Bedrock agents and SageMaker models" scope; its §11 gap 7 rests on "ledger verification" and "S3 versioning" (neither exists or is verified). Correct both before copying them into `gap-list.md`.
- AICT's usage count (0 for our traffic) is in neither document; Monitor covers "Managed" agents only [SN notes §3].
- C9's "one incident per crossing window per runtime" could flood the shared instance; bound it or agree it with the owner.
- The "partial" continuous-compliance credit for a 5-min loop is doubtful: the slides ask for a verdict "in the path, not replayed afterwards".
- The 7-step pitch (PB §3.12) may not match the judged format (a judge-as-auditor picks an incident). Prepare both.

### 4.4 Risks
- **Accepted by the user (2026-10-05: "allowed"), not blockers:** the Global OAuth property change (next item), the two adapter bugs (§4.3) and AICT Monitor likely empty for our agents (correction row 11) [user].
- **Shared-instance change (accepted risk):** the team (Arth) enabled the Global OAuth property `glide.oauth.inbound.client.credential.grant_type.enabled` on the shared ServiceNow instance [SN handoff §2, §11.4]. The SN handoff's own rules say not to change system properties; the courtesy note to facilitators is still pending [SN handoff §10, §14]. Organiser approval: UNVERIFIED.
- **Naming: both are right at different layers** (corrected after the user's review). Type `ifabric-…` into `new-agent.sh` and the CR (at most 40 characters; Kubernetes names can't hold `_`, and the generator rejects it, in a real run only after the CodeBuild build, so use `--dry-run` first). AgentCore and AICT then show `ifabric_…`, which meets PB's intent. The playbook's intent is right; type hyphens [correction row 9; verifier C4]. `my-agent` has no team prefix.
- **Identifying details** (not secrets) in the package: the instance host, the account id, the integration username and the owner's work email address. The address is in `prooflab/servicenow/cli.py` (2×, incl. the default at :28), the SN handoff (7×), PB §3.1, `prooflab/servicenow/README.md` and our own committed `notes/verification/2026-10-05/playbook-verify-lead.md` (its redacted twin is `notes/playbook/playbook-verification.md`). The repo is private [review]. Whether to redact them is the user's call.

---

## 5. Verified platform reality (the facts that bite)

### 5.1 Identity, tools, Cedar
- Every agent calls with one principal, `ServiceIdentity::"bootstrap-key"`; per-agent Keycloak IdentityConfigs exist but aren't provisioned [gap 2; notes #38].
- All 5 AgentCore runtimes share one IAM role (`a-01-eks-cluster-agentcore-runtime`, re-checked live [review]), which explicitly denies direct Bedrock model calls and `bedrock-agentcore:InvokeGateway` (the AWS AgentCore Gateway); the MoDaaS gateway `modaas-agw` is the only model path [notes #48].
- The PDP evaluates one policyId per decision: the called asset's. Team ConfigMap `my-team-policy` is loaded but named in 0 of 1,037 decisions on both PDP replicas, 2026-10-04 18:07Z → 2026-10-05 17:33Z, none of them DENY (corrected after review) [notes #33; snapshot, recomputed].
- Agents call undeclared tools; every call is ALLOW. It is detectable via `route_alias` in `/modaas/evidence` [gap 3; notes #37].
- The live, enforced lever is ToolConfig `spec.access.cedarPolicy`, projected to ConfigMap `modaas-toolconfig-<alias>` (edits propagate per source; no ToolConfig edit tested yet). A forbid rule there can DENY calls to that tool for all callers, keyed on toolName, arguments, dataClassification or toolMethod: the way to a Cedar DENY in Hostile/Rogue tests (corrected after the user's review; correction row 1). The AgentConfig overlay is documented but not wired (source-based) [notes #39; mem: platform-verified-facts].
- Cedar sees principal, action, resource and context (toolName, arguments, dataClassification, traceId, actionId, toolMethod). It does NOT see the calling agent, the route, call counts or tokens, and it is stateless [mem: platform-verified-facts].
- `customer-records` and `network-twin` have no dataClassification [notes #40]. Tool Lambdas run unpinned `$LATEST`, and the participant policy allows `UpdateFunctionCode` on `team-*` [gap 11; notes #59].
- All runtimes reach the gateway over plain HTTP on the public ELB; the TLS :8443 listener is unused [notes #2; gap 9]. AgentConfig specs never hold the gateway key. The operator injects it into each runtime's env as `OPENAI_API_KEY` and `AGENTCORE_GATEWAY_MCP_TOKEN`, both equal to Secret `agw-apikeys` key `eval-key`: one key for every agent. No `GATEWAY_API_KEY` exists (corrected after live verification) [verify-live C3; notes/verification/2026-10-05/resources-verify.md].

### 5.2 Refusals recorded as ALLOW
- Guardrail block: HTTP 200, `finish_reason=content_filter`, 0 tokens. PDP and `/modaas/evidence` say ALLOW with no guardrail field; the template records "undetermined" [gap 4; notes #35, #56].
- Pause refusal: HTTP 404. ALLOW in the PDP and `/modaas/evidence`. The pod line carries `trace.id` but no run id or action id (no `modaas.*` field at all; cause unknown). In the snapshot that trace id is on no other gateway line and in no ledger record (`my-agent`'s ledger records carry no trace id). That trace id joins the 404 to its run through the policy decision and its durable evidence record: it is on the PDP decision 6 ms earlier (`policy_id=model-nemotron-super-120b`, `decision=ALLOW`, action id `642489b6…`, no run id) and on a `/modaas/evidence` record written by `modaas-authz` that carries the run's CID (`my-agent-1791191585-4d9744`), `decision = ALLOW` and `policy_version = 331993`. So the refused call joins its run by trace id, and its durable record says ALLOW. Live, no span in `aws/spans` carries that run's id [verify-live C1] (corrected after the lead's live check, 2026-10-05) [snapshot, recomputed; verifier C6; lead's live read-only check; mem: platform-verified-facts; gap 4].
- A fail-closed `PolicyEngineUnavailable` DENY appears in `/modaas/evidence`, while the ledger says "500 on the model" [notes #43].

### 5.3 Evidence surfaces and join keys
| Surface | Durable? | Keys | Notes |
|---|---|---|---|
| Gateway pod stdout (`modaas-agw-88dc46ff4-jfcdx`) | No (pod lifetime) | `modaas.run_id` (= baggage CID, else the trace id), `modaas.trace_id`, `modaas.action_id`; tokens, cost, duration | The C16 figure of record as the kit reads it (`pull-evidence.sh`, `evaluate.py`); `aws/spans` holds the same per-call figures durably [notes #27; mem: platform-verified-facts] |
| `/aws/modaas/gateway` (CloudWatch) | 7 d | `trace_id` only | The OTLP copy of the gateway's per-call line, with tokens. It carries no run or action id (0 of 1,630 records): `modaas-telemetry-export` adds the ids to spans only, though the installer meant this copy to match the stdout line (a build gap, cause unknown). The collector deletes only 6 payload keys, no ids (corrected after live verification) [verify-live C2] |
| `/modaas/evidence` (CloudWatch) | 30 d | `correlation_id` (= CID), `action_id`, `trace_id`, decision, policy id/version, principal | The only per-call WHO record; written by authz over OTel [notes/verification/2026-10-05/resources-verify.md] |
| PDP pod logs (2 replicas) | No (pod-only) | `action_id`, `trace_id`, policy_id, decision, latency | No principal; read both replicas (`deploy/` reads one) [same] |
| authz pod logs | No | none | 4 startup lines per pod; nothing per call [same; snapshot] |
| X-Ray | Yes | trace id; gateway segments carry `modaas.run_id`, `modaas.action_id` and tokens as metadata, not annotations (not searchable by run id) | A partial source: BatchGetTraces truncates long runs (S2: 22 of 174 model segments), and agent subsegments repeat token counts, so sum gateway segments only. One trace spans all 3 runtimes plus the gateway [notes #32; verify-live C1] |
| `aws/spans` (CloudWatch Logs, X-Ray Transaction Search) | 30 d, until account teardown | `attributes.modaas.run_id` (= baggage CID; the trace id for untagged traffic), `attributes.modaas.action_id`; per-call tokens, cost and model on model calls | One span per gateway request (`modaas-agw`). The complete durable C16 source: S2 353 spans = 1,999,001 tokens, S1 24 spans = 37,664, both equal to stdout. The kill-switch 404 and MCP GET 405s carry no run id; the trace also holds attribute-less child spans, so count by run id, not by trace. Gateway spans only (corrected after live verification) [verify-live C1] |
| Ledger (`audit-store`) | PVC `audit-store-data`; survives pod restarts, deleted with the stack | `correlation_id`, step, phase, actor, detail, agent-minted `trace_id`, `seq` | `/records?cid=` JSONL (works without `cid`); `/timeline` is text [snapshot; mem: reference-agents-facts] |
| AgentCore runtime logs (`…/runtimes/<id>-DEFAULT`) | Never expire | run trace id | Spans hold the system prompt and context, incl. customer records [notes #22; notes/verification/2026-10-05/glossary-verify.md] |
| AgentCore metrics (`AWS/Bedrock-AgentCore`, `<runtime>::DEFAULT`) | CloudWatch | hourly | Latency per invocation; Errors; Invocations [mem: platform-verified-facts] |
| `/aws/bedrock/aict-invocations` | 7 d (CloudTrail data events, AWS-written) | time; session id | WHO invoked agents; `guardrailConfig` per model call; no run id [SN notes §1] |
| CloudTrail LookupEvents / EKS audit / `components` events | 90 d / OFF (all 5 types) / ~1 h | — | `describe-trails` is denied [notes/verification/2026-10-05/resources-verify.md] |
| `AWS/Bedrock` metrics; gateway `:15020` metrics | CloudWatch / cumulative | per model id | Not joinable to a run; `:15020` is a third cost source [notes #42; notes/verification/2026-10-05/screenshots-compare.md] |

**Join path:** baggage CID → the gateway's `run_id`, with tokens, on pod stdout (ephemeral) and on its spans in `aws/spans` (30 d) → `/modaas/evidence` `correlation_id` (= CID, 30 d). The `/aws/modaas/gateway` copy joins by `trace_id` only. `action_id` links the response header, gateway stdout, spans, PDP, `/modaas/evidence` and X-Ray. The ledger joins by `correlation_id` only (its trace ids are agent-minted) (corrected after live verification) [verify-live C1; mem: platform-verified-facts].

### 5.4 The ledger
- GET routes `/healthz`, `/records`, `/timeline`. No verify route, no hash chain, no signatures [notes #13; correction row 2].
- The write token is a literal 32-character value in all 5 AgentConfig specs (incl. `my-agent`). The cockpit's CR view returns it, and so does `get-agent-runtime` [notes #24; notes/verification/2026-10-05/glossary-verify.md, notes/verification/2026-10-05/resources-verify.md]. The kit's `pull-evidence.sh` copies it into `cr-status.json` (MUST-FIX, §3d). A write without the token gets 401; that shows only that [mem: workshop-progress].
- A successful reference run writes 12 records (4 per agent); a refusal writes 3 per agent. The helper writes 2 per run, `my-agent` 3. No action_id, tokens or guardrail verdict. `seq` = epoch ms and can collide [mem: reference-agents-facts, workshop-progress].
- S2's 174 model calls look like 16 ordinary ledger records [notes #44].

### 5.5 Approvals, twin, ceilings
- **Approvals:** two free-text annotations. All 18 approval records have an empty `signature`. Approvers: system-admin ×11, satyabratsrikumar@team ×5, cloudshell-user@team ×2 (approval-subject strings, not email addresses) [notes/verification/2026-10-05/resources-verify.md]. A model swap needed no re-approval, and re-attesting adds no record. IT's only approval (04:37:25Z) predates its swap (05:47Z) [gap 5; notes #46; live]. Approved ≠ runtime READY.
- **The twin:** the `network-twin` Lambda serves its own packaged dataset (3 sites, none for S2). The agents query it with element ids and get "no twin data" (40× in 24 h) [gap 10; notes #57, #58]. MAVERIC's Tokyo cells are unconnected to the scenarios; the kit's checkpoint uses `example_test_model`, not `tokyo-rf-twin` [notes #60].
- **Ceilings:** models 100 req/min and 2.5M tokens/h; MCP 100 req/min; one gateway replica, so effectively account-wide. "1 req/s per agent" is wrong for 3 agents (180/min). The token ceiling binds first [notes #41; mem: platform-verified-facts]. The 429 and its no-charge claim are untested.

### 5.6 Measured runs (gateway figures) [mem: workshop-progress, reference-agents-facts]
| Run | CID | Tokens | Note |
|---|---|---|---|
| S1 (IT refused) | `fault-1791175626-0d34e2` | 24,796 | 6 model calls; grade 6/8 |
| S1 (IT ran) | `fault-1791177843-fde682` | 50,246 | 6/8 |
| S2 | `fault-1791177342-d3f892` | 1,999,001 | 174 model calls, 05:15–05:20 UTC on 2026-10-05, peak 49/min, $0.3033; 5/10 |
| S3 | `fault-1791177636-8fa0bd` / `fault-1791177926-b0ce69` | 37,836 / 37,799 | 8/10; all agents escalate |
| S1 after the IT swap | `fault-1791179282-8ef1a8` | 37,664 | IT on nano-9b: 8,450 |
| `my-agent` docs question | `my-agent-1791190861-638235` | 7,313 | Wrong answer, fully governed (gap 1) |
| Helper Q3 (Module 9 Step 1) | `hackathon-helper-1791189106-6525ac` | 123,476 | 13 model calls |

`aws/spans` gives the same totals for S2, S3 `…b0ce69`, S1 `…fde682` and S1 `…8ef1a8` [verify-live C1]. All runs above are exploratory. The self-check grades fail by construction on the guardrail-verdict and negotiation checks [notes #19]. `score-run.py` reads ledger text only.

### 5.7 Kill-switch timing [notes #28, #36; mem: platform-verified-facts]
- Model pause: nano-9b 33–41 s, still serving meanwhile; super-120b ≤2 s. Tool pause ~1–7 s.
- Resume: ~24–35 s. Stale `ReconcilePaused`/`RegistryPauseProjected` conditions remain afterwards (re-confirmed on nano-9b, super-120b and modaas-docs [live]).
- An AgentConfig model swap re-programs the runtime in ~24 s [mem: workshop-progress]; the IT swap's runtime update came 13 s after its `kubectl patch` (05:47:37Z → 05:47:50Z) [verify-live C7].

### 5.8 AICT (ServiceNow AI Control Tower) [SN notes §1–§3; mem: servicenow-context]
- Live: `ServiceNowAictUser` assumes `SgcAictReadOnlyAccessRole` about every minute.
- Scope: AgentCore runtimes and gateways only. Bedrock ListAgents, SageMaker ListModelCards and AgentCore browsers/code interpreters are AccessDenied.
- **Usage count = 0 for our traffic:** its 15-min query filters `eventName = "InvokeAgent"`, and our traffic has none (only ConverseStream, Converse and InvokeAgentRuntime).
- Monitor and evaluation cover "Managed" agents only (vendor PDF). Agent Studio run logs show no timestamps, run ids or identity.

---

## 6. Gap list status
Kit format per entry: What's missing / Why / Impact / If you had one more day. PB §3.11 also asks for the affected claim or control (reported by the reader). Today's additions to gaps 2 and 4–7 are already in `gap-list.md` (uncommitted working-tree change, edited again after review and live verification, last at 18:45Z; no new numbered gaps; check `git diff gap-list.md`) [mem: prooflab-project]. Items marked "not yet in the file" are only in this handoff.

| # | Gap (one line) | Strengthened today by |
|---|---|---|
| 1 | A governed answer can be wrong; the disposition is a keyword guess | — |
| 2 | WHO: the platform's records can't tell agents apart | authz writes nothing per call; WHO lives only in `/modaas/evidence`, where 39 of 39 records in the last hour were `bootstrap-key` [notes/verification/2026-10-05/resources-verify.md] |
| 3 | WHAT: agents use tools they never declared | With today's policies Cedar-deny tests show ALLOW; a forbid rule in the called tool's ToolConfig can deny, but for all callers (correction row 1); `demo-crm-lookup` is Reviewing, yet its Cedar ConfigMap is loaded [notes/verification/2026-10-05/glossary-verify.md] (not yet in the file) |
| 4 | AUTHORIZED: refused calls are recorded as ALLOW | 1,016 decisions in 24 h, all ALLOW; PDP logs are pod-only [notes/verification/2026-10-05/resources-verify.md] (not yet in the file) |
| 5 | APPROVED: approvals are self-asserted and don't follow changes | 18 records, all with an empty `signature`; EKS audit logging off for all 5 types [same] |
| 6 | INTEGRITY: the ledger can't show it wasn't altered | The token is literal in all 5 AgentConfigs, incl. `my-agent`, and readable via `get-agent-runtime`; `audit-store.py` has no verify route [notes/verification/2026-10-05/glossary-verify.md; notes/verification/2026-10-05/resources-verify.md; correction row 2]; the kit's evidence pull and `submit.sh` copy the token into the hand-in (§3d); the store keeps a writer-sent `ts` and sets only `seq` (`audit-store.py:95–96`); the evidence bucket's versioning is unreadable to us |
| 7 | RECONSTRUCT: a run's records sit in stores that only partly share a durable key | Reframed after live verification: the gateway's spans in `aws/spans` carry the run id and tokens for 30 days [verify-live C1]. Still missing: ids on the `/aws/modaas/gateway` copy (0 of 1,630; a build gap) [verify-live C2], ledger trace ids that match the run, run ids on refusals (kill-switch 404, GET 405); and S2 looks ordinary in the ledger. `components` events are kept ~1 h (not yet in the file) [notes/verification/2026-10-05/resources-verify.md] (corrected after live verification) |
| 8 | No platform limit stops a slow runaway in time | The gateway has no per-run budget or halt (correction row 10; not yet in the file) |
| 9 | Customer data in spans; plain-HTTP key; no classification | The published `modaas-docs` endpoint is plain HTTP on the public ELB [notes/verification/2026-10-05/resources-verify.md] (not yet in the file) |
| 10 | The network agent asks the twin with element ids and carries on | Confirmed as the reason the twin can't give named pass/breach runs (correction row 5) |
| 11 | A governed tool's code can change under its approval | Cedar never sees tool code (correction row 1; not yet in the file) |

**Candidates, not yet in the list** (adding gaps is a standing instruction [mem: hackathon-working-agreement]; commit and push per §8): AICT usage count = 0 and Monitor = Managed only (L2 limits) [SN notes]; ledger vs gateway coverage (§3b Q16, after it is explained). **Do not add** "no durable OTEL trace exporter": it is false (X-Ray) [correction row 3].

---

## 7. Live state (verified read-only, 2026-10-05T17:41:26Z–17:50Z)

The independent reviewer re-checked this section at 18:03–18:15Z: all matched, except the operators' restart time (fixed in 7.3) [review]. **AWS credentials expired at about 18:20 UTC on 2026-10-05** (`ExpiredToken`; kubectl `Unauthorized`) and blocked live checks until a refresh; the live verifier then ran at about 18:40 UTC (C1–C3, C7) [verify-live]. When they expire again, refresh the `[hackathon]` profile from the Workshop Studio dashboard ("Get AWS CLI credentials"). The pre-push secret scan fails closed without valid credentials (§8).

### 7.1 Governed CRs (all in `components`) [live]
| Kind | Name | Phase | Paused | Model / provider | Gen |
|---|---|---|---|---|---|
| ModelConfig | nemotron-nano-3-30b | Approved | false | nvidia.nemotron-nano-3-30b | 1 |
| ModelConfig | nemotron-nano-9b | Approved | false | nvidia.nemotron-nano-9b-v2 | 7 |
| ModelConfig | nemotron-super-120b | Approved | false | nvidia.nemotron-super-3-120b | 3 |
| ModelConfig | nemotron-super-120b-helper | Approved | false | nvidia.nemotron-super-3-120b | 1 |
| AgentConfig | customer-experience-agent | Approved | false | nemotron-super-120b; tools [customer-records] | 1 |
| AgentConfig | it-resolution-agent | Approved | false | **nemotron-nano-9b**; tools [runbook-lookup] | 2 |
| AgentConfig | network-resolution-agent | Approved | false | nemotron-super-120b; tools [network-twin] | 2 |
| AgentConfig | hackathon-helper | Approved | false | nemotron-super-120b-helper; 5 tools | 1 |
| AgentConfig | my-agent | Approved | false | nemotron-super-120b; tools `<none>` | 1 |

ToolConfigs (10, none paused): aws-knowledge, cluster-status, cr-author, customer-records, evidence-lookup, helper-docs, network-twin and runbook-lookup (agentCoreGateway, Approved, created 2026-10-04 ~10:38Z); `modaas-docs` (custom, Approved, 2026-10-04 21:29Z, by Claude on the user's instruction); **`demo-crm-lookup`** (custom, **Reviewing**, created 2026-10-05 00:36:35Z, creator unknown, not ours; backend pod `demo-tool-backend` since 00:36:19Z) [live; mem: workshop-progress]. Stale pause conditions remain on nano-9b (04:05:53Z), super-120b (09:13:05Z) and modaas-docs (05:56:44Z) [live].

### 7.2 Agents and runtimes [live]
- AgentCore runtimes, all READY: `customer_experience_agent-Iwj8JK82QX` v1, `it_resolution_agent-15k2B966z2` v2 (updated 05:47:50Z), `network_resolution_agent-popvu28fOl` v2, `hackathon_helper-9mJWi9AT26` v1, `my_agent-9AyPFbHh5Z` v1 (updated 09:00:05Z).
- **`my-agent`:** runtime `my_agent-9AyPFbHh5Z`, model `nemotron-super-120b`, `dependsOn.tools` empty; it calls `modaas-docs` via env only (notes #55). One approval, 08:59:52Z, `satyabratsrikumar@team`.
- **The IT agent's model: `nemotron-nano-9b`**, with one approval, 04:37:25Z, which predates the swap.

### 7.3 Pods (start time, restarts) [live]
| Pod | Started | Restarts |
|---|---|---|
| `agentgateway-system/modaas-agw-88dc46ff4-jfcdx` (the run-id store) | 2026-10-04 10:35:10Z | 0 |
| `agentgateway-system/agentgateway-78bc9cdb86-qd6xj` | 2026-10-04 10:33:48Z | 0 |
| `modaas-system/modaas-pdp-5fb9c5d799-2kcjn`, `-zqzw6` | 2026-10-04 10:35:42Z | 0, 0 |
| `modaas-system/modaas-authz-69b66d9d5b-nb2gk`, `-vb79j` | 2026-10-04 10:35:42Z | 0, 0 |
| `modaas-system/opentelemetry-collector-…` | 2026-10-04 10:36:40Z | 0 |
| `modaas-system` aws-agent/model/tool operators | 2026-10-04 10:35–10:36Z | 1 each (containers restarted 2026-10-05 10:37–10:38Z; cause not checked) [review] |
| `components/audit-store-5798b5b988-rqxzv` (PVC `audit-store-data`, Bound, 1Gi) | 2026-10-04 10:44:58Z | 0 |

ConfigMap `modaas-system/my-team-policy` exists (created by Claude 03:41:51Z; decides nothing).

### 7.4 CloudFormation stacks [live]
`a-01-eks-cluster` (CREATE_COMPLETE, 10-04 10:03Z) · `a-02-code-editor` (CREATE_COMPLETE, 10:18Z; its outputs hold the bearer links, never echo them) · `a-03-servicenow-aict` (UPDATE_COMPLETE, created 22:02Z, updated 22:45Z) · `aict-servicenow-user` (CREATE_COMPLETE, 22:43Z). The last two were created by the facilitators' `WSOpsRole` [mem: workshop-aws-access].

### 7.5 Evidence bucket [live]
`TEAM_EVIDENCE_BUCKET` is set; `aws s3 ls --recursive` shows **0 objects**.

### 7.6 Evidence snapshot [snapshot]
`workshop-local/evidence-snapshots/20261005T173727Z/` (outside the repo; modes 700/600; `MANIFEST.txt` with sha256; secret scan clean):
- `gateway-modaas-agw-88dc46ff4-jfcdx.log`: 1,895 lines, 10-04 10:35:13Z → 10-05 17:33:16Z. 1,032 lines carry `modaas.run_id`, with 290 distinct ids; the first at 10-04 18:07:18Z.
- `pdp-…-2kcjn.log` / `pdp-…-zqzw6.log`: ~22.7K / 22.9K lines over the same window.
- `authz-…` ×2: 4 startup lines each, no per-call records. `audit-store-….log`: empty (request logging is off by design).
- `ledger-records.jsonl` (GET at 17:44:26Z): 101 records, 17 correlation ids (fault-* 6 ids / 75 records; hackathon-helper-* 7 / 14; my-agent-* 4 / 12), 10-04 18:07:17Z → 10-05 09:13:40Z, no sign of truncation.
- `pods.txt` (pod inventory at 17:38:34Z). Per-file capture times and sha256 values are in `MANIFEST.txt`; the folder holds no other files. All six captured pods had 0 restarts.

### 7.7 workshop-local tooling [live]
`env.sh` and `shell`; `bin/` (kubectl 1.36.5, Helm 3.22.0); `.venv` (kit pins); `scripts/findings-recheck.sh` (read-only), `scripts/pre-push-secret-scan.sh` (read-only), `scripts/side-entrance-probe.sh` (creates pods); `research/reference-agents-2026-10-05.md`; `digital-twin/` (setup script, macOS shims, `query-tokyo-twin.py`, `ask-feed-check.sh`, logs); `maveric/` (the MAVERIC clone); `evidence-snapshots/`. A backup copy is in the repo's `tools/workshop-local/` (re-copy before committing if the working copies change).

### 7.8 MAVERIC (Module 10 twin, local Docker) [live]
- Stopped: 7 containers of compose project `radp_prod` (zookeeper, kafka, api_manager, training, rf_prediction, orchestration, ue_tracks_generation). `docker inspect` gives FinishedAt 15:51:53–15:51:55Z, exit 137/143, restart policy none. (`docker ps` still prints "Exited … 6 minutes ago" (5 for kafka and zookeeper). Docker Desktop's idle mode stopped its Linux VM at 15:57:55Z (backend log: `com.docker.backend.idle VM stopped`), and the relative times are frozen as of that moment. `docker inspect`'s FinishedAt is authoritative [review].)
- Restart (ask first; it reopens 0.0.0.0:8090 and :9094): `cd ~/firstmate-homes/TrustworthyAI/workshop-local/maveric && docker compose -f dc.yml -f dc-prod.yml -f dc-workshop.yml start`. Use `start`, not `down`: `down` removes the containers and the network. RADP's data volume `radp_prod_radp` (`/srv/radp`) survives `down` but not `down -v`, and Kafka's anonymous volumes would be orphaned. Whether the trained `tokyo-rf-twin` lives in that volume was not checked [review].

### 7.9 Repo git state (18:00Z) [live]
`main` is in sync with `origin/main` at `bfb1ce6` (17:50Z: the package, `notes/claude-memory/` and `notes/verification/2026-10-05/`). Not yet committed: `gap-list.md` (modified), `.gitignore`, this file, `notes/playbook/`, `notes/references/`. The post-review fix pass (18:30Z onward) edited more files; run `git status` before committing.

---

## 8. Standing rules [mem: hackathon-working-agreement unless noted]
- **Read-only by default. Ask before any write** to the repo, cluster, AWS or ServiceNow, including workshop steps that apply, annotate, approve, pause or delete. Never change or delete a resource Claude did not create without asking; other people use this account.
- **Never print or commit secrets:** the gateway key (`/tmp/modaas-token`, secret `agw-apikeys`); the ledger `AUDIT_WRITE_TOKEN` (in AgentConfig specs, runtime env, the cockpit CR view and generator `/tmp` files); the hackathon AWS credentials; the IdeUrl/CockpitUrl and the token in their query string; the AICT connector key; the ServiceNow client secret (and ID); presigned URLs. Don't run `kubectl get agentconfig -o yaml` or `get-agent-runtime` without a query that excludes env values. The kit's `pull-evidence.sh` is such a dump: its `cr-status.json` is the full Model/Tool/AgentConfig JSON (`pull-evidence.sh:78`), so it holds the literal ledger write token of all 5 AgentConfigs. Redact env values before that file goes into `~/evidence/`, the repo or a submission (MUST-FIX before submitting, §3d). For live re-checks, use the read-only queries in `notes/verification/2026-10-05/verify-live.md`, which print key names, counts and booleans only [verify-live].
- **Before every push**, `bash ~/firstmate-homes/TrustworthyAI/workshop-local/scripts/pre-push-secret-scan.sh <repo>` must print `RESULT: clean` (it fails closed). It loads the values it compares through kubectl and AWS, so it can't pass without valid credentials. It guards the repo only, not the S3 upload.
- **Credentials:** the hackathon AWS credentials expire (they did at about 18:20 UTC on 2026-10-05, which blocked live checks until a refresh). Ask the user to refresh the `[hackathon]` profile from the Workshop Studio dashboard ("Get AWS CLI credentials") [mem: workshop-aws-access].
- **NEVER run the AI Native Networks workshop's cleanup scripts** (`cleanup-module1.sh` and the others). They delete every AgentCore gateway, runtime and memory in the region, with no name filter.
- **Cockpit: GET only.** Read the CockpitUrl inside a command and never print it. Never call `POST /api/agents/{name}/ask` without the user's OK for that step. Delete the cookie jar afterwards [mem: workshop-aws-access].
- **Protected namespaces:** `canvas`, `canvas-vault`, `cert-manager`, `modaas-system` (except the team Cedar ConfigMap), `agentgateway-system`, `istio-system` [PB §2]. The broad participant RBAC (notes #26) is not permission.
- **Budget:** 100 req/min and 2.5M tokens/h, account-wide; serialize runs and check headroom (§3d).
- **Delegate** work to background subagents and keep the main session free.
- **Independent reviewers** for substantial memory rewrites (and, as done today, for big deliverables such as this handoff): a fresh general-purpose subagent with no conversation access, given the user's words verbatim, read-only. Memory is mirrored: after every change, `rsync -a --delete` between `~/.claude/projects/-/memory/` and `~/.claude/projects/-Users-satyabratsrikumar-firstmate-homes-TrustworthyAI-TrustworthyAI-iFabric/memory/`.
- **Notes items only on the user's "add".** Gap-list updates are allowed (standing instruction: add new gaps).
- **Verify teammate documents independently** against the primary sources and live evidence before relying on them, and record the corrections (as `notes/playbook/playbook-verification.md` does). User: "i am not confident on winning handbook. verify it on your end too".
- **Commit and push as we go.** End commit messages with the `Co-Authored-By: Claude Opus 5.5 (1M context)` trailer exactly as the session's attribution reminder gives it.
- **Don't steer the user toward Claude's own challenge ideas.** Platform findings are context, not build targets [mem: prooflab-project]. Keep answers short and factual.
- **Adversarial and Rogue work:** record what was tested and what happened. Never write down methods for forging or altering evidence records.

---

## 9. Open inputs and questions

**Still to come from the user:** the Evidence Pack format; more slides (the full 30-slide judging deck); the "What the platform gives you" page (the enforcement points) [mem: prooflab-project, challenge-requirements].

**Must fix before submitting:** the ledger-token leak in `cr-status.json` and the submission zip (§3d).

**Still unchecked** (the live verifier settled C1–C3 and most of C7 [verify-live]):
- Whether `tmf639.json` from `pull-evidence.sh` holds the ledger token (C8). `cr-status.json` holds the ledger token, not the gateway key [verify-live C3].
- Which field sets the runtime model when `modelRef` differs from `dependsOn.models[0]` (C7; testing it needs a write).
- Why the `/aws/modaas/gateway` copy lacks the ids (C2; the cause can't be found read-only).
- The live evidence and the safe read-only queries are in `notes/verification/2026-10-05/verify-live.md`.

**Accepted risks** (the user, 2026-10-05: "allowed"): Arth's Global OAuth property change on the shared instance, the two adapter bugs (§4.3), and AICT Monitor likely empty for our agents (correction row 11). They are not blockers [user].

**Decisions for the user:**
- IT agent: keep nano-9b or revert to super-120b, before the baseline hours (§3a, item 1).
- `demo-crm-lookup`: leave it, approve it or delete it. It is not ours and its creator is unknown.
- `my-agent`: keep as is, or rebuild with an `ifabric-` name.
- Restarting MAVERIC, and whether S2 is run again (budget).
- Planning question (not a decision): how separation of duties and assurance work when the owner also builds (§3b, Q14).

**Organiser questions** [mem: prooflab-project, servicenow-context]:
- Who injects the Hostile/Rogue conditions, and when?
- What INTEGRITY proof is expected, given that hash chains are out of scope?
- Is AICT required for L2, and how is it connected? Can AICT screenshots or exports go in the Evidence Pack? Can our runtimes be "Managed"?
- Is the "1 model request/second" rule per agent or per account?
- The full 30-slide deck, and confirmation of the end time.
- Can per-agent identities be provisioned (a platform change)?
- Can the AICT usage query include `InvokeAgentRuntime`/`Converse*`, and can a facilitator run `cloudtrail validate-logs` for our window?
- Did the organisers approve the Global OAuth property change on the shared instance (Arth's courtesy note)? Not a blocker: the user accepts the risk.

---

## 10. Reference index
**Links:** `notes/references/links.md` (AgentCore, Bedrock, Cedar, W3C trace context, OTel GenAI conventions, Strands, MAVERIC, ServiceNow docs, TM Forum CRDs/ADRs; read its warnings first).

| Purpose | Command or path |
|---|---|
| Workshop shell (bash only) | `bash -c 'source ~/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; <cmd>'`, or `workshop-local/shell` for people |
| Secret scan before push | `bash ~/firstmate-homes/TrustworthyAI/workshop-local/scripts/pre-push-secret-scan.sh <repo>` → `RESULT: clean` |
| Pull the 6 evidence surfaces | `bash pull-evidence.sh <run-id> [out-dir]` (gateway lines from pod stdout, `--tail=50000`). `cr-status.json` contains the ledger write token (§8). `otel-traces.json` is the ledger chain, under a false "collector exports to debug only" note (correction row 3) [kit] |
| C16 control test (kit) | `python3 evaluate.py 16 <run-id> [--evidence-dir D] [--register F]` → PASS/BREACH/NO EVIDENCE, exit 0/1/2 [kit] |
| Hand in | `bash submit.sh <team> --dir <repo>`. Redact `cr-status.json` first (MUST-FIX, §3d); the zip lands in the current directory [kit] |
| Live evidence and safe queries | `notes/verification/2026-10-05/verify-live.md` (read-only; prints key names, counts and booleans only) |
| C16 from `aws/spans` | Logs Insights on log group `aws/spans`: `aws logs start-query --log-group-name aws/spans --start-time <epoch> --end-time <epoch> --query-string '<Q>'`, then `aws logs get-query-results --query-id <id>`; Q below [verify-live C1] |
| Reference run | `bash run-reference.sh [S2-transport-congestion \| S3-restricted-change]` (default S1-fronthaul-degradation); prints the CID [workshop-static/reference-impl] |
| Grade a run | `python3 score-run.py <cid> <scenario-id> <timeline-file>` [workshop-static/reference-impl] |
| Ask one agent | `bash ask-agent.sh <agent> "<question>" [--cid X] [--traceparent TP]` [kit] |
| New agent | `bash new-agent.sh <name> <model-alias> [--skills a,b] [--tool alias] [--role r] [--dry-run]`; name `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`, checked before the build only with `--dry-run` (§4.4) [kit] |
| Ledger read | `kubectl get --raw "/api/v1/namespaces/components/services/audit-store:8080/proxy/records?cid=<cid>"` |
| ServiceNow adapter | `python3 -m prooflab.servicenow selftest \| notify \| check \| export` (repo root) |
| Findings re-check | `workshop-local/scripts/findings-recheck.sh` (read-only) |

Q for C16 by run id (model calls only; count by run id, not by trace) [verify-live C1]:
```
filter `attributes.modaas.run_id` = "<CID>" and `attributes.listener` = "llm"
| stats sum(`attributes.gen_ai.usage.input_tokens`) as inp, sum(`attributes.gen_ai.usage.output_tokens`) as outp, count(*) as calls
```

**Kit paths:** `workshop-assets/starter/` (register.yaml, evaluate.py, submit.sh, pull-evidence.sh, new-agent.sh, ask-agent.sh, agent-template/, gap-list.md template); `workshop-static/reference-impl/` (reference-agent/agent.py, run-reference.sh, score-run.py, show-run-spans.py, audit-store.py, make-agentcore-agents.py, build-agent-image.sh); `workshop-static/scripts/twin-scenario.sh`; `workshop-static/data/` (network-inventory.json, twin-dataset.json, customer-records.json, it-incidents.json); `workshop-static/servicenow/` (Rail 1 `escalate-to-incident.py`). The kit's `register.yaml` has C16 limit 2000, a C7 phase-coverage metric and a C9 placeholder [kit: register.yaml].

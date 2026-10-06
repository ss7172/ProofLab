# 01 · Architecture delta audit: the prior ProofLab design against the verified platform

Written 2026-10-05 by a Claude subagent, read-only (repo files, memory and the kit only; no git, no cluster or AWS calls, no secrets). It audits the architecture written **before** the 2026-10-05 live verification against the facts verified that day. The current facts win. This file makes no planning decisions: where the handoff lists options, the "exact change" column keeps them as options.

## Summary

- **The target used to judge fit** is the captain's backbone (2026-10-05):
  - EP adapters → **one contract** (`evaluate`/`emit`/`callback`/`pull`)
  - → a **registry-versioned stateless evaluator**
  - → **every decision** (platform, agent, handoff, human, ServiceNow) recorded with full metadata into **one append-only evidence store**
  - → a **stitcher** (CID / action id / trace id)
  - → the **control test and dashboard**, which query the store

  The captain's correction narrows the path. There is exactly **one in-path question**: the optional C16 check before each model call, an `evaluate()` against a frozen, version-stamped threshold, with no registry call in the path. Agent-to-agent handoffs are **record events** (`emit` only) that never block, and the orchestrating script can emit them. Everything else records. Any other prior element that makes work wait is a CHANGE (§1B). §1A maps the prior design onto these layers.
- **Verdicts across the 73 rows of §1:** **KEEP 22 · CHANGE 40 · DROP 11.**
- **The five changes that matter most:**
  1. **One in-path question; everything else records.**
     - Drop the C16 reservation coordinator (DynamoDB, dispatch ownership, settlement), the gateway-level admission and Gateway A/B.
     - C16's in-path decision survives only as the optional check before each model call, in our agent code. Our agents are the only team code in the model-call path.
     - Handoffs, run closure, the human loop and every platform decision become emitted records.
     - The prior "platform adapters" become one adapter per enforcement point.

     Rows A1–A3, A6, A7, B1, B6, B8, B10, B11.
  2. **`aws/spans` is the durable spine.** The prior design leaned on generic OTEL sources, and the baseline then wrongly "corrected" that to "no durable exporter". `aws/spans` carries run id = CID, action id and tokens for 30 days. It is the C16 figure of record and the C7 expected population, and the ledger is tested against it (rows P1, P3, D2, E1).
  3. **Cedar changes go through ToolConfig `spec.access.cedarPolicy`** on our own ToolConfigs in `components`. Not the team ConfigMap, which is inert. These rules apply to every caller, are stateless, and their propagation and approval reset are untested. Refusals by guardrails and pauses are recorded as ALLOW, so the real outcome of each call comes from the gateway line (rows B4, B7).
  4. **INTEGRITY can't rest on a ledger verification, because none exists.** It rests on cross-surface corroboration plus a SHA-256 MANIFEST, and the kit's evidence pull must have the ledger token redacted before submission (rows P7, P8, K2).
  5. **Closing the judgment gap and fixing evidence emission move from "optional differentiation" to the first live work.** Every new agent version is a C9/C16 treatment, so the agents come before the register freeze and the C9 baseline. The Nemotron investigator is demoted to an option (rows S1, M3, I2).
- **The biggest missing pieces** (§1A, §3) all have no counterpart in the prior design:
  - **platform-EP adapters that record the real outcome** where the platform logs ALLOW, an **emit-only handoff adapter** in the orchestrating script and at escalation, and **owner/responsible metadata** on every decision record
  - **the one append-only evidence store and the stitcher.** The prior workspace and bindings need reshaping, and which physical store to use is undecided
  - the dashboard app itself
  - a security matrix covering every enforcement point
  - a threshold-experiment protocol with a mechanical date check
  - the agent design
  - the binding to Arth's Finding contract (ESC producer, `publish()` glue)
  - an adversarial log organised by Hostile/Rogue phase and enforcement point
  - the whole fleet, live-lane and PR model

## Citation keys

**Prior design** (written before the 2026-10-05 live verification; may rest on disproven assumptions):

| Key | File | Note |
|---|---|---|
| DA §n | `hackathon-context/outputs/prooflab-detailed-architecture.txt` | Latest detailed design: the V4 header, the V3 foundation §0–§13, and the M03–M15 clarifications §3A, §3B, §8A, §10A |
| NV §n | `hackathon-context/outputs/prooflab-nvidia-architecture.txt` | V4 Nemotron investigator, §1–§10 |
| PA "…" | `hackathon-context/outputs/prooflab-architecture.txt` | Final design after three reviews; cited by heading |
| SVG3 / SVG4 | `prooflab-one-page-architecture-v3.svg` / `prooflab-one-page-architecture.svg` | Text read |
| BC "…" | `hackathon-context/outputs/claude-hackathon-context.txt` | The 2026-10-04 baseline handoff. Cited by section: "Corrections" (current-build corrections), "Facts A–L", "Contracts §1–§15", "Delivery" (two-person sequence), "Unknowns", "Conflicts", "Inventory M01–M16" |
| V3 | `hackathon-context/work/completion-audit/detailed-architecture-v3.txt` | An earlier revision of DA's foundation |
| R6 | `agentic-template-hackathon/.lavish/round6-architectures/index.html` | 29 September, before kickoff, for a different arena. Not audited row by row; only borrowed in §2–§3 |

**Current facts** (authoritative):

| Key | File |
|---|---|
| H §n | `PLANNING-HANDOFF.md` |
| PV row n | `notes/playbook/playbook-verification.md`, corrections table (the same rows as H §4.2) |
| gap n | `gap-list.md` |
| PC | `notes/workshop-reference/platform-contract.md` |
| PCV §n | `notes/verification/2026-10-05/platform-contract-verify.md`, including its addendum |
| PVF | Memory `platform-verified-facts.md` |

Supporting sources, cited through H: RAF = memory `reference-agents-facts.md`; SNH §n = `SERVICENOW_INTEGRATION_HANDOFF.md`; `finding.py` = `prooflab/servicenow/finding.py`; kit = `workshop-assets/starter/register.yaml` and `evaluate.py` (read 2026-10-05).

---

## 1. Delta table

Verdict: **KEEP** = still holds as written. **CHANGE** = the idea stays but its mechanism, source or value must change. **DROP** = disproven, impossible here, or superseded.

Row ids are an area letter plus a number. The evidence-source area is **P**, so its ids never read as control names (C7, C9, C16).

| # | Prior component / assumption / decision (prior §) | Verdict | Evidence (current source) | Exact change needed |
|---|---|---|---|---|
| **A** | **Topology and placement** | | | |
| A1 | Logical "Gateway A / Gateway B" handoffs and a zone-boundary adapter: "ServiceNow customer agent → gatewayA → AWS IT agent → gatewayB → network". The first second-point target is the "gatewayB handoff" (DA §1.A, §2 routing rows, §4 handoff obligations; NV §3; SVG3) | DROP | One Gateway, `modaas-agw`, carries the agents' model and tool calls, and all five agents run on AgentCore (PCV §1). The agents never call each other: `run-reference.sh` invokes customer → IT → network in sequence (RAF). BC "Corrections" had already flagged Gateway A/B as non-products | Remove Gateway A/B and the zone adapter from the contracts and the sketch. The handoff-recording idea survives, re-targeted to the real handoffs (A6). Draw: runner → three sequential AgentCore invocations → `modaas-agw` (authz, PDP, guardrail) → Bedrock Nemotron, or the AWS AgentCore Gateway → Lambda tools |
| A2 | Admission through "an allowed gateway function/wrapper"; AgentCore Gateway Lambda interceptors as "a documented route" (DA §1.B; PA "One repo, few deployments"; SVG3 "Shared model gateway adapter") | DROP | The page says the gateway and PDP take none of our code (PC). The admission VAP refuses participant create, update and delete in `agentgateway-system` and `modaas-system` by its text, although RBAC allows them (H §5.9; PCV addendum). Only the IDE role can change the AgentCore Gateway: "never do it" (PV row 14) | Remove the gateway adapter as an admission point. Our only code in the model-call path is our agent code on AgentCore Runtime (H §5.9, EP 5). The untested route plus policy in a team namespace (H §5.9) stays a noted possibility, not a design element |
| A3 | DynamoDB single-region transactions for budget, run and attempt state; S3 for policy versions; "a conditional-write store can replace DynamoDB" (DA §1; DA §6 "Datastore-neutral admission transaction"; PA "One repo") | DROP | The shared runtime role's verified inline policy allows ECR pull, logs, X-Ray, PutMetricData, workload identity and InvokeAgentRuntime, and explicitly denies direct model and AgentCore-gateway calls. It lists no DynamoDB or S3 grant, and participants can't write IAM (PVF; H §5.1). Store access from the runtime is therefore unverified, and we can't change it | No shared atomic store. Per-run state an agent needs travels in its invocation payload (CID, tokens spent so far), or comes from a source it can reach. One unverified option: the run's own ledger records, whose reads are open (PVF). The app keeps a local SQLite/JSONL index |
| A4 | Assurance compute on "the Workshop IDE host using its existing role", SQLite plus a transactional outbox, a private local UI, and no laptop in the runtime path (BC "Objective and product", Contracts §2; DA §1.D) | CHANGE | Our shell runs as WSParticipantRole on a laptop stand-in, not as the IDE role, and the two roles' rights differ (PCV §9). The participant role can run `filter-log-events` and Logs Insights (PVF; H §10). That `components` pods have no AWS credentials is documented in BC "Facts A", not re-verified | Name the role the app runs as, and re-test its reads under the IDE role if the judges use the IDE. Keep the app off-cluster. Drop the separate outbox: it is subsumed by the one append-only store (P10), and Arth's append-only delivery log (H1) is one of its feeds |
| A5 | One Python distribution of logical modules with few entry points; no graph DB, no extra orchestration platform, no crypto ledger (DA §1; PA; BC Contracts §2) | KEEP | Signing, hash chains and Merkle proofs are out of scope, and "additional agents or elaborate ServiceNow workflows" earn no bonus by themselves (H §2.5). Arth's `prooflab/servicenow` is already a stdlib-only package of this shape (H §4.3) | Extend `prooflab/` with `controls/`, `sources/` and `app/` beside `servicenow/` |
| A6 | Handoff obligations: "Each gatewayA/B handoff: sending lifecycle creates handoff.sent and expected matching handoff.received, joined by stable handoff_id; refusal/timeout is its own declared terminal case" (DA §4; DA §2 routing row "zoneA/zoneB handoff send/receive") | CHANGE | The real handoffs are elsewhere. The runner invokes customer → IT → network in sequence through `ask_agent.py` → InvokeAgentRuntime, sending the CID in the body and as baggage, plus one run traceparent. The IT "negotiation" stub is never reached (RAF). An agent's escalation hands the case to a human (the ESC Finding, H §4.3). No platform surface records a handoff as such: the ledger holds per-agent records, and the gateway sees only model and tool calls (H §5.3) | Build the captain's **handoff adapter** as `emit` only: handoffs are record events that never block, and the agents need not call each other. The orchestrating script emits `handoff.sent` (from, to, CID, traceparent, payload hash, time) and `handoff.received` (status, disposition, duration) for each invocation, and the ESC producer emits the agent → human handoff. A missing `handoff.received` is a recorded gap, not a refusal. Drop the prior "refusal/timeout" terminal cases as blocking states |
| A7 | Platform adapters: "shared-model gateway adapter, zone-boundary adapter, telemetry source connector and ServiceNow connector"; "Source adapters + reconciliation · emit / pull / callback · raw observations" (DA §1.A; SVG3) | CHANGE | One EP's decision is spread over surfaces that disagree. The PDP and `/modaas/evidence` record guardrail blocks and pauses as ALLOW; the real outcome is only on the gateway line (0 tokens with `content_filter`, or a 404 joinable by trace id) (H §5.2; gap 4). PDP and authz logs are pod-only, authz writes no per-call record to its pod log, and `/modaas/evidence` is the only per-call WHO record (H §5.3). Admission refusals and approval changes leave no independent durable record: EKS audit logging is off, and approvals are self-asserted annotations with empty signatures (gap 5; PVF) | Reshape into the captain's **one adapter per EP**, each emitting the same decision record through the one contract. <br>• **Platform-EP adapters are observers (`pull`):** PDP/authz (`/modaas/evidence` plus both PDP pods); gateway outcome (`aws/spans` plus stdout), which adds the **real outcome** the platform logs as ALLOW (served, guardrail-blocked, pause-refused, ceiling-refused, unauthenticated); approvals and admission (CR approvals with generation, subject and empty signature; captured admission errors). <br>• **Team EPs:** our agent runtime (`evaluate` for the one C16 check, B10; `emit` for everything else); the orchestrating script's handoff adapter (A6, `emit` only); and ServiceNow (`callback`/`pull`, records only; Arth's package, H1) |
| **B** | **Enforcement points and inline decisions** | | | |
| B1 | C16 preventive admission: the invariant F+H+B ≤ cap, the attempt/reservation state machine (NONE → RESERVED → DISPATCHING → SETTLED), dispatch ownership and closure races (DA §6; PA "Control 16 runtime protocol"; SVG3 "Control 16 admission"; BC Contracts §10 already said "BLOCKED/CONDITIONAL") | DROP | The gateway has no per-run budget or halt. Cedar has no token attributes and keeps no state. The only limits are account-wide ceilings and pausing an asset (PV row 10; H §5.1). No gateway hook (A2) and no shared store (A3) | Delete the reservation machinery: the invariant, the states, dispatch ownership, settlement finality, and the fail-closed ERROR when the store is unavailable. The in-path C16 decision survives in a different shape, as the captain's one optional check (B10). Spend accounting moves to post-run evaluation over `aws/spans` (D2) |
| B2 | Four transports: `evaluate()` synchronous, `emit()` asynchronous, `callback()` deferred, `pull()` scheduled; control code independent of adapter translation (DA §2; BC Contracts §3) | KEEP | Axis 2 asks whether the design would survive a second enforcement point (H §2.3). Arth's package already maps `notify()` to `callback()` and `check_response()` to `pull()` (SNH §3; H §4.3) | This is the captain's one contract: every adapter (A6, A7) speaks it and emits the same decision record. `evaluate()` has exactly one caller: the optional C16 check before each model call (B10, B11). `emit()` carries agent records and handoffs; `callback()` carries ServiceNow responses; `pull()` = the platform-EP adapters and the post-run evaluators over `aws/spans`, `/modaas/evidence`, the ledger and CloudWatch metrics. A ToolConfig Cedar rule refuses inside the platform's own PDP, which is already in the path, and is recorded by the PDP adapter (A7) |
| B3 | "Only verified in-path hooks can refuse"; observation is never presented as prevention (SVG3; DA §8; BC Contracts §1) | KEEP | Five of the page's six EPs take none of our code, and the ledger refuses writes, not agent actions. AgentCore Runtime is "observe" on the page, but our code there can refuse its own next call (H §5.9); the only refusal our code issues is the C16 one (B10). A notify-only incident refuses nothing (PV row 12) | Apply the rule EP by EP in the security matrix (§3 R2). Our design adds exactly one in-path question, the optional C16 check (B10); everything else records |
| B4 | The team Cedar ConfigMap in `modaas-system` (label `part-of=modaas-pdp`, policy-id annotation, hot reload) as "the documented extension point"; test toolName restrictions there (BC Facts E, Contracts §1, Delivery stage 5, Inventory M02/M04) | CHANGE | `my-team-policy` loads but was named in 0 of 1,097 PDP decisions, because each decision evaluates only the called asset's one policy id (H §5.1, §5.9; PVF). The live lever is ToolConfig `spec.access.cedarPolicy`, projected to `modaas-toolconfig-<alias>`. `components` is outside the VAP, so edits to our own ToolConfigs pass it. Edit the ToolConfig, not the projected ConfigMap, which is `managed-by=modaas` and excluded from the exemption (H §5.9; PV row 1) | Author Cedar `forbid` rules in the `spec.access.cedarPolicy` of ToolConfigs we own (`ifabric-*`), keyed on toolName, arguments, dataClassification or toolMethod. State the limits: every caller, stateless, propagation and approval reset untested. For platform-installed tools such as `customer-records`, the brief says "clone rather than modify" (H §2.5). Which policy the PDP applies when two ToolConfigs expose the same MCP tool name is unknown, so test a clone before relying on it. Every edit is a cluster write that needs the user's OK (H §3d) |
| B5 | Shared gateway identity gives no per-agent isolation: "do not claim controls use attributes the PDP does not receive"; Cedar has no token meter, so C16 is post-hoc (BC Facts E; Contracts §1, §10) | KEEP | Confirmed: `bootstrap-key` on 1,107 of 1,107 authenticated evidence records. Cedar sees toolName, arguments, dataClassification, traceId, actionId and toolMethod, not the calling agent, call counts or tokens. The AgentConfig overlay isn't wired (H §5.1; PCV §8; PVF) | Carry it into gaps 2 and 3 and into the WHO answer: the ledger `actor` plus the per-runtime log group, never a platform identity |
| B6 | ServiceNow as a governance integration, "not … an assumed kill switch"; a ServiceNow human approval queue, or "delayed human decisions", as an enforcement point that holds an action (DA §1.C; PA "ServiceNow"; BC "Five architecture questions" #5, Contracts §3). Arth's SNH §7.4 calls the escalation incident "EP #2" | CHANGE | An EP must ask, wait and act. A notify-only incident refuses nothing; it counts only if something waits on the human (PV row 12; H §3b Q11). Under the captain's rule nothing waits on the human: the human loop records | ServiceNow is the human loop: the alert and the human's later response travel as `callback()`/`pull()` records, with the assignee and responder (P13). The escalation is a recorded agent → human handoff (A6). It never holds work, so it is not claimed as an enforcement point; drop "EP #2" from the sketch |
| B7 | Kill switch: a pause "withdraws routes after propagation (sample about 15 seconds to stop, 50 seconds to resume)"; record requested and effective times (BC Facts E, Contracts §1) | CHANGE | Measured: nano-9b kept serving for 33–41 s after its pause; super-120b stopped within 2 s; tools within ~1–7 s; resume took ~24–35 s. The PDP and `/modaas/evidence` record the pause refusal as ALLOW, its 404 line has no run or action id, and stale pause conditions stay (H §5.2, §5.7; PV row 6; gap 4) | Quote measured times. Report a pause's real outcome from the gateway line, joined by trace id. A pause hits every agent that uses the asset, so it belongs to the live lane (§3 R7) |
| B8 | Run lifecycle OPEN → ACTIONS_CLOSED → EVIDENCE_FINAL, closure races, "no physical no-send-after-close" (DA §3 Run key, §6; BC Contracts §4) | CHANGE | No coordinator exists to close a run (A3, B1). Spans reach `aws/spans` through the collector, and refusals carry no run id (H §5.3) | Keep only an explicit as-of cutoff per assessment: when each source was read, and how far it had been fetched. Drop ACTIONS_CLOSED and the closure-race semantics: closing a run stops work, and only the C16 check may make work wait |
| B9 | "PORTABILITY: same control/evidence package used at shared gateway and zoneB/tool boundary" as the second-EP bonus (DA §9; PA "Demo target"; NV §3) | CHANGE | The gateway and zone boundary are unavailable (A1, A2). Our checks can verifiably run in our agent runtime, in a post-run job, and as a ToolConfig Cedar rule (H §5.9; H §3b Q11) | Define the second EP as the same C16 evaluator behind two adapters: in our agent before each model call (the one in-path question, B10) and post-run over `aws/spans` (`pull`). Note what changed: the adapter only. Record each adapter's scope |
| B10 | C16 decided in the path: `evaluate()` for each governed model request; "ALLOW must never precede durable reservation"; "Do not dispatch model call without durable committed reservation"; on a store outage, "deny governed admission with explicit ERROR" (DA §6; PA "Control 16 runtime protocol" steps 3–6; SVG3 "Control 16 admission · evaluate · allow / deny") | CHANGE | The gateway has no per-run budget or halt, and Cedar has no token attributes and keeps no state (PV row 10; H §5.1). There is no gateway hook (A2) and no shared store (A3). Our agent code is the only team code in the model-call path, and it sees per-call usage: Strands `chat` spans equal the gateway per call (H §5.9; PVF). The handoff lists an in-agent check as one undecided option for inline C16 (H §3b Q3) | This becomes the captain's one in-path question: an **optional C16 `evaluate()` before each model call**, in our agent code, given the frozen, version-stamped threshold (no registry or store call in the path). It decides on the tokens spent so far plus the call's bound (e.g. `max_tokens`) and emits every decision, ALLOW or DENY, as a record. Declare what "spent so far" covers (this invocation, or the run, if the orchestrating script passes the run's earlier spend in the payload) and the failure mode (the prior design failed closed). Its demo is DA §9's C16-PREVENT: a refused call, not a breached run |
| B11 | The admission API: `evaluate(request)` → overall ALLOW/DENY/ERROR plus per-control results; "Mapping is frozen in the authorized policy bundle; caller cannot omit a required control"; "DENY or required-admission-control ERROR prevents dispatch" (DA §2; BC Contracts §3) | CHANGE | The in-path lever we control serves only C16 (B10). C7 needs the platform-written records of the run (P1), and C9 needs closed clock hours or a window of runs (F2), so neither can decide before a call (H §5.3; H §3b Q10) | `evaluate()` serves the C16 question only. C7 and C9 are evaluated after the fact from records (`pull`) and never block. Drop the multi-control admission envelope and the "required-admission-control ERROR prevents dispatch" rule |
| **P** | **Evidence sources, keys and integrity** | | | |
| P1 | BC: the OTEL collector trace pipeline "has NO durable exporter and discards spans"; "Account-wide aws/spans is documented empty"; "Do not draw OTEL→X-Ray"; don't assume FilterLogEvents or Logs Insights (BC "Corrections", Facts G, Contracts §1, Inventory M01/M05/M07) | DROP | Two hops. DA §8 assumed generic OTEL/CloudWatch sources. BC then "corrected" that to "no durable exporter". The live check reversed BC: the collector exports the gateway's spans to X-Ray, which writes them to CloudWatch Logs `aws/spans` (30 days, until teardown). Each span is one gateway request, with `modaas.run_id` = baggage CID, `modaas.action_id` and per-call tokens. S2: 353 spans = 1,999,001 tokens, equal to stdout. Logs Insights is permitted (H §5.3; PV rows 3, 7; PVF) | Make `aws/spans` the durable per-run source for the C16 figure of record, RECONSTRUCT and the C7 expected population. Draw gateway → collector → X-Ray → `aws/spans`. Count by run id, not by trace (attribute-less child spans), and never through X-Ray (it truncates long runs) |
| P2 | `/aws/modaas/gateway` as "documented for gateway logs", a C16/C7 source (BC Contracts §1; Inventory M05) | CHANGE | It carries no run or action id (0 of 1,630 records; a build gap), keeps 7 days and joins a run by `trace_id` only (H §5.3; gap 7) | Use it only as a corroborating copy joined by trace id, and for refused calls (e.g. the durable copy of a pause 404) |
| P3 | Run identity = run id + `traceparent`: "missing headers can fragment" gateway run ids (BC Facts L, Contracts §3–4, Inventory M03; DA §3 Attempt/Observation keys) | CHANGE | The gateway's `modaas.run_id` is the baggage CID (without a CID, the trace id). `traceparent` drives only `modaas.trace_id`. Agents mint their own ledger trace ids, refusals carry no run id, and the ledger joins by `correlation_id` (H §5.3; PV row 7) | Canonical keys: the CID (run); `action_id` (call; also the `x-modaas-action-id` response header); `trace_id` (only for refusals and `/aws/modaas/gateway`); the ledger's `correlation_id`. Propagate the CID via baggage. Drop `provider_execution_id` and the attempt/reservation ids |
| P4 | Canonical records PolicyBundle, Run, Attempt, Obligation, Observation, UsageEntry, EvidenceBinding, Window, Assessment and Alert/Finding, all with revisions (DA §3; BC Contracts §6 "Core repositories") | CHANGE | Most of these entities serve the dropped coordinator (A3, B1, B8). Arth's package already fixes the assessment record, the Finding and the reference prefixes (`gateway:action_id=`, `ledger:cid=`, `cloudwatch:`, `cr:`, `register:`, `servicenow:INC…`) (SNH §8.2; H §4.3) | Reduce to RawCapture, Call (one per gateway action id, from `aws/spans`), Decision (`/modaas/evidence` and the PDP), LedgerRecord, MetricWindow, Assessment (Arth's §8.2 shape, revisioned r1, r2), Finding, DeliveryEvent and Gap. Keep "one charge per call" (D1) |
| P5 | Provenance classes LIVE_SUBJECT, AUTHORIZED_TEST, REPLAY, COUNTERFACTUAL_EXPORT and SYNTHETIC on every record (DA §3; PA "Core contract") | KEEP | All runs so far are exploratory (H §5.6). Tamper tests run on exported copies only (H §3c step 6, §3d) | Add an EXPLORATORY label for pre-freeze calibration runs (§3 R3) |
| P6 | Acquisition: preserve raw pages before acknowledging them; a failed or truncated source is a visible gap; event time is not a safe watermark (DA §3A; BC Contracts §6) | KEEP | Gateway stdout lives only as long as its pod. PDP and authz logs are pod-only. The ledger PVC is deleted with the stack, and the account is destroyed at the end (H §3a item 5; H §5.3) | Make it concrete: snapshot gateway stdout, both PDP replicas (`--all-pods=true`), the ledger `/records`, and the `aws/spans` and `/modaas/evidence` query results into the pack. Re-snapshot before judging (H §3a item 5) |
| P7 | "Supplied ledger verification supports the integrity question"; "Supplied ledger tamper-evidence should be inspected and retained" (BC "Six judge/auditor questions", "Constraints", Contracts §6). SNH §8.5 says to capture the ledger's verification output | DROP | `audit-store.py` serves GET `/healthz`, `/records` and `/timeline` only: no hash chain, no signatures, no verify route. The write token is readable from every AgentConfig spec, `get-agent-runtime` and the cockpit, and the store keeps a writer-sent `ts` (H §5.4; PV row 2; gap 6). `score-run.py` supports completeness and capture consistency, not non-alteration (H §3b Q18) | INTEGRITY = cross-surface corroboration (ledger against `aws/spans`, `/modaas/evidence`, the PDP, X-Ray and `/aws/bedrock/aict-invocations`) plus a SHA-256 MANIFEST, stated as corroboration, not proof |
| P8 | Record the S3 object key, version and checksum with a readback; "integrity rests on … S3 versioning" (BC Facts L; SNH §8.5–8.6) | CHANGE | Participants can't read the bucket's versioning, object lock or lifecycle, can overwrite or delete its objects, and `submit.sh` prints no VersionId (PV row 15) | Keep the checksum readback: download, then compare with the MANIFEST. Drop the VersionId as INTEGRITY evidence |
| P9 | AgentCore runtime spans as a usage and event cross-check; the `show-run-spans.py` path (BC Facts G; Inventory M05, M07) | CHANGE | `show-run-spans.py` totals 2× the gateway (75,328 vs 37,664), because `invoke_agent` parents repeat their `chat` sums. Agent spans carry no action id, and they hold system prompts and customer records (H §5.3; PCV §3; gap 9) | Use agent spans for agent-side events and timing only. Never take tokens from them (or sum `chat` spans only). Treat their content as sensitive in the pack |
| P10 | A shared evidence workspace: raw records, typed facts and link tables; model proposals in quarantine; exact-scope indexes, never top-k denominators (DA §3B; NV §1, §4) | CHANGE | The judging slide's L2 says "evidence collected in Audit ledger" (H §2.1). The platform's audit-store is append-only through its API, and our agents can write to it with the token. But its PVC is deleted with the stack, the token is readable by every participant, the writer chooses `ts`, and its records hold correlation_id, step, phase, actor, detail and trace_id (whether it keeps extra fields is unverified) (H §5.4; PVF; RAF) | Reshape into the captain's **one append-only evidence store**. Every adapter's decision record and every raw capture is appended, never updated; corrections are new records. The SQLite index, the stitcher's output and the dashboard views are derived from it and can be rebuilt. Which physical store is undecided: (a) the platform audit-store, as L2 names it, or (b) our own append-only, fsync'd JSONL (like Arth's delivery log), with the audit-store as one of its sources. Either way, export it into the pack with SHA-256s before teardown |
| P11 | A per-control source-authority map: population, the authoritative producer of expected ids, joins, clock domain, completion and bypasses (PA "Trust boundaries and source authority"; DA §8) | KEEP | Now fillable from verified facts. C16 ← `aws/spans` (served model calls; refusals lack a run id). C7 expected ← platform-written spans and decisions. C9 ← `AWS/Bedrock-AgentCore` hourly metrics or span durations. Bypasses: pod-hosted backends and `team-*` Lambdas (H §5.3; PCV §1; gap 11) | Write it into each control's `measurement_basis` in `register.yaml`, and into the sketch |
| P12 | EvidenceBinding: many-to-many bindings between observations, usage, controls and runs or windows, joined during reconciliation without multiplying usage (DA §3 EvidenceBinding; DA §3A; BC Contracts §6) | CHANGE | The verified join path: CID → the gateway's `run_id` on `aws/spans` → `/modaas/evidence` `correlation_id`. `action_id` links the response header, gateway stdout, spans, the PDP, the evidence record and X-Ray. Refused calls and `/aws/modaas/gateway` join only by `trace_id`. The ledger joins by `correlation_id` only (its trace ids are agent-minted), and agent spans carry no action id (H §5.3; PV row 7; PCV §3) | Reshape into the captain's **stitcher**: a deterministic, stateless job over the store. It links records by CID, then by `action_id`, then by `trace_id` (for refusals). Every unmatched record becomes an explicit gap record: a ledger record with no gateway call, or a gateway call with no ledger record (the C7 test). Keep "never multiply usage": tokens are summed once from Call records, before any join |
| P13 | Owner metadata only at policy and finding level: control owners in the policy bundle; "named owner/recipient" on alerts; "actual owner/recipient derives from authorized policy/routing" (DA §3 PolicyBundle and Alert/Finding keys; DA §8A) | CHANGE | The judges ask WHO "acted — which identity, on whose behalf, with what scope?" and APPROVED "attestation for every asset in the chain?" (H §2.5). Verified: one principal for every agent; approvals are free-text annotations with an empty signature (system-admin ×11, satyabratsrikumar@team ×5, cloudshell-user@team ×2); the control owner is Sree, the user (H §1, §5.1, §5.5). The masterclass names four roles: accountable management, GRC, operations and assurance (H §3b Q14) | Put owner/responsible metadata on every decision record: <br>• the control owner and register version <br>• the EP's operator (platform or team) <br>• the asset's approver, attestation, time and generation from its CR, flagged when older than the version that ran <br>• the acting agent (ledger actor and runtime) <br>• for findings, the ServiceNow assignee and responder <br>Never invent people or approvals (H §3b Q14) |
| **D** | **Control 16 (token spend cap)** | | | |
| D1 | Whole-run accounting: input+output once per distinct execution; never a parent plus its leaves; corrections replace, they don't add; a known subtotal over the cap proves BREACHED despite gaps; missing usage is INDETERMINATE, not zero (DA §6; BC Contracts §9) | KEEP | These are exactly the verified traps: `show-run-spans.py` double-counts parents, `evaluate.py` counts MCP lines as calls, and refusals carry no run id (H §3b Q4, §5.3; PCV §3) | Deduplicate by `action_id`, filter on `listener=llm`, and treat a run with refusals as possibly incomplete unless the trace-id join finds them |
| D2 | The C16 source is the gateway's token records, through the kit's `evaluate.py` over `pull-evidence.sh` output (BC Delivery stage 2, Facts L) | CHANGE | `evaluate.py` reads ephemeral pod stdout and implements control 16 only. The page's grep is broken by quoted values. `aws/spans` holds the same per-call figures durably (H §3c step 2; H §5.9 "The page's commands"; PCV §3) | Read C16 from `aws/spans` (the Logs Insights query in H §10) and keep stdout snapshots as backup. Fix the quoting (`grep -F "modaas.run_id=\"$CID\""`). Drop MCP lines from call counts |
| D3 | The cap N is "justified before assessment"; "10,000 is the source's illustrative cap"; preferred allowance 0 over-cap runs (DA §6; BC "Rubric") | CHANGE | Every measured S1/S3 run used 24.8K–50.2K tokens. The kit's 2,000, the guide's 900 and the slides' 10,000 would each breach all of them and leave no passing fault-resolution run. S2 used 1,999,001. A judge hinted "think of a risk matrix" (H §3b Q2; H §5.6) | Derive caps from our own measurements and from a matrix → tier → cap mapping, pre-declared and dated in `register.yaml` (recommendation, not decided: H §3b Q2). Decide whether helper and investigator calls count |
| D4 | C16-BREACH from a "permitted observation-only assessed scenario or organizer-accepted recorded breach"; C16-PREVENT as a separate live denial (DA §9; PA "Demo target") | CHANGE | The twin switch can't produce breach runs: the recipes are broken and there is no S2 twin site (PV row 5; gap 10). S2's IT loop is a natural C16 breach (2.0M tokens), but it costs ~80% of the hourly budget in under 5 minutes (H §3b Q5; gap 8) | Pick the lever in planning. Candidates: a fresh run of S2 with the reference agents under the frozen cap (budget-heavy), or a cap tier that a normal run exceeds. Write both run ids down before judging, with the same rule for the pass and the breach |
| D5 | The coordinator's test cases RACE, DISPATCH-CLOSE, HIDDEN-RETRY, CRASH, C16-PREVENT and STALE/CROSS-TEAM (DA §9) | DROP | They test the coordinator that A3 and B1 drop | Replace them with Hostile/Rogue cases per EP (§3 R6) |
| D6 | Subject and assurance spend kept apart, with the combined platform spend shown; investigator calls never excluded to look better (DA §6; NV §7; BC Contracts §9) | KEEP | One helper question used 123,476 tokens, and the 2.5M tokens/h ceiling is shared by all traffic (H §5.6, §3d) | Give our non-subject calls (app, investigator) their own CID prefix, so `aws/spans` keeps them apart |
| **E** | **Control 7 (event recording)** | | | |
| E1 | Expected events from a "dispatcher/coordination journal" (`model.requested`), from `tool.requested` registered by an orchestrator, and from Gateway A/B handoff pairs; never derived from surviving logs (DA §4; BC Contracts §6–7; PA "Control 7") | CHANGE | No coordinator and no handoffs exist (A1, B1). Platform-written records do exist for every governed call: one `aws/spans` span per gateway request, with `action_id`, and one `/modaas/evidence` record per decision, with `correlation_id` (H §5.3). The kickoff deck says C7 needs "expected" defined outside the graded agent (p21, via memory `prooflab-project`) | Keep the principle. Take the expected population from platform-written records (spans plus decisions per CID) and test the agents' ledger against it. Drop the pre-dispatch registration: nothing is written before a call. This needs our agents to write each call's `action_id` into their ledger records (row S1) |
| E2 | Coverage = matched expected events ÷ expected events (E∩O over E), with extras and duplicates unable to inflate it; E = 0 → NOT_ASSESSED; timing pairs only within one producer stream and clock; the P/M/K/U bounds; a missing middle event leaves both its pairs unmeasurable (DA §4; BC Contracts §7) | KEEP | The ledger's `seq` is epoch milliseconds and can collide; its `ts` is writer-sent; the tool-invocation record is written after the model call (H §5.4; RAF). So ledger timing is the agent's own clock and order | Declare the clock basis of each timing pair in `register.yaml`: gateway span times and ledger receipt times come from different hosts. With no trusted basis, C7 timing is NOT_ASSESSED and only coverage is claimed |
| E3 | C7 breach by "authorized source-level record loss"; the page's recipe "Pause a ToolConfig mid-run; the record never lands" (DA §9 C7-COVERAGE-BREACH; PC "Breach injection recipes") | CHANGE | The platform records a paused call as ALLOW, and its 404 line has no run id (PCV §8; gap 4). Natural C7 cases exist: S2's 174 model calls appear as 16 ordinary ledger records, and a refused run writes 3 ledger records per agent instead of 4 (H §5.4; H §3b Q5). The kit's C7 metric is phase coverage per agent (kit `register.yaml`) | Candidate named runs (planning picks): ledger records per platform-observed call (the reference agents breach this on every multi-call run), or the kit's phase coverage. A reference-agent run before the fix and an `ifabric` run after it, under one frozen rule, would give a breach, a finding and a passing re-test. Explain the observation of 290 gateway run ids against 17 ledger CIDs first (H §3b Q16) |
| **F** | **Control 9 (drift)** | | | |
| F1 | C9 metric = the exact-match rate of single-fault diagnoses on labelled scenarios, positive baseline B, drop D_w = 100(B−M_w)/B (DA §5; PA "Control 9"; SVG3 "Accepted labels + deterministic scoring") | CHANGE | Two candidates are live, and the statistic is undecided (H §3b Q10). The page names AgentCore Latency/Errors per runtime and clock hour as the drift signal (PC; PCV §6). The kit's own `register.yaml` suggests "disposition-match-rate against score-run.py's expected disposition". `score-run.py`'s full grade fails by construction, and its disposition check passes if any agent records the disposition (PV row 4; PVF) | Choose in planning. (a) Runtime health: hourly Latency (Maximum and/or Average) plus Errors Sum per runtime, with a higher-is-worse formula. (b) Judgment quality: a per-agent disposition-match rate against each scenario's expected disposition (S1 auto-resolve, S2 gather-evidence, S3 escalate), computed by our own rule, not `score-run.py`'s `want in disps`. Keep DA's missing-window and zero-baseline rules for either |
| F2 | Hourly AgentCore Latency Average and Errors Sum, 3600 s, closed UTC hours; a missing hour is UNKNOWN; Errors is a count; start baseline collection early (BC Contracts §8, Delivery stage 1) | CHANGE | Errors stayed 0 through the S2 runaway. In that hour the IT runtime's Average was 71.6 s against 8.2–8.5 s for the others, and its Maximum 278.4 s. Latency is per invocation and moves with call count, and a refused run is fast (1.05 s). No clean baseline hour exists yet, and the IT agent has been on nano-9b since 05:47Z (H §3a item 1; H §3b Q10; PV row 8) | Decide the IT model and the agent versions first, then freeze, then collect baseline hours on those versions. Recommendation (not decided): Maximum plus Errors Sum, and/or the gateway's per-call duration from `aws/spans`. Use the per-run call count to tell "platform sick" from "agent looping" |
| F3 | Every measured crossing alerts a named owner, even inside the interval allowance; delivery is not response; missing data is a monitoring-health finding, never an invented crossing (DA §5; BC Contracts §8) | KEEP | SNH §7.2 requires the same. The reader flags that one incident per crossing window per runtime could flood the shared instance (H §4.3) | Bound the volume, e.g. one incident per control × window with the runtimes listed in the summary, and agree it with the owner |
| F4 | C9-BREACH from "authorized degraded diagnostic outputs"; the page's recipe "Swap the model, re-run, compare" (DA §9; PC "Breach injection recipes") | CHANGE | The swap mechanics are verified (no re-review; the runtime updates in ~13–24 s), but a swap is not shown to cause drift: tokens per call are similar on both models, and latency follows call count (PCV §8; H §3b Q5) | Treat a swap as a declared treatment, not a guaranteed breach. Candidate breach windows: a measurably degraded hour (e.g. a loop run's IT hour) on the frozen baseline version |
| **G** | **Verdicts, the control registry and thresholds** | | | |
| G1 | Requirement verdict (SATISFIED, BREACHED, INDETERMINATE, NOT_ASSESSED), safeguard operation and evidence sufficiency kept separate; the C-FM-01 rollup with no averaging (DA §7; BC Contracts §12; PA "Verdicts and findings") | KEEP | Axis 2 rewards honesty ("Built properly: yes. Actually worked: no") and recorded gaps (H §2.3). Arth's Finding allows only BREACHED, ESCALATED, INDETERMINATE and SATISFIED (`finding.py` `VERDICTS`) | Keep the four-state verdict internally. Map NOT_ASSESSED to "no finding", or to INDETERMINATE with `kind: monitoring-gap` when data is missing. Add ESCALATED for agent escalations |
| G2 | A PolicyBundle with an applicability version, an effective interval, new-run selection expiry vs continuation, hard cutoffs and revocation, plus a gate that rejects missing or expired bundles "when opening governed work" (DA §3, §4; BC Contracts §5) | CHANGE | The judged threshold document is `register.yaml`, in the kit's fields: `control_id`, `name`, `metric`, `observation_limit`, `exception_tolerance`, `measurement_basis`, `owner`, `version_date`, `enforcement_point`. It must be "versioned and dated before any assessed run — we check the date" (H §2.4; kit). Findings carry exactly the frozen version (H §4.3) | The control registry = `register.yaml` in kit format, plus a `version`, the risk-tier table, the evaluator version and the enforcement point per control. Drop the expiry, continuation and revocation machinery, and the run-opening gate: the frozen, version-stamped threshold travels with the agent, and the registry is never called in the path. A change is a new version, never an edit (H §3a item 2). Every decision record carries the registry version and evaluator version it was judged under |
| G3 | Thresholds: "complete the rule from permitted pre-assessment baseline/purpose, name owner, date it, then freeze"; no retrospective tuning (DA §4, §5, §6; BC Contracts §5) | KEEP | "Versioned and dated before any assessed run"; "Do not move the threshold to make it pass" (H §2.4; H §3a item 3) | Add the experiment protocol and the mechanical date check (§3 R3) |
| **H** | **ServiceNow and AICT** | | | |
| H1 | The M14 delivery contract: a logical finding identity that includes the assessment revision; an immutable operation per mutation; states PENDING, DISPATCHING, OUTCOME_UNKNOWN, DELIVERED, FAILED and SUPERSEDED; DELIVERED only after reading back the content and recipient (DA §8A; BC Contracts §14) | CHANGE | Arth's `prooflab/servicenow` is the contract (H §4.3): <br>• `finding_id = ifabric:{control_ref}:{threshold_version}:{scope_kind}:{scope_id}:{kind}`. It has no assessment revision, so a re-run reuses the incident <br>• delivery states DELIVERED, FAILED, UNVERIFIED, OUTCOME_UNKNOWN and DRY_RUN <br>• response states RESPONDED, AWAITING_RESPONSE, NO_RESPONSE_OBSERVED, RESPONSE_UNKNOWN and NOT_DELIVERED <br>• an append-only, fsync'd delivery log <br>• 46 offline tests pass | Adopt it unchanged as the human-loop interface. Write the glue it lacks: the evaluator runner `publish()` and the escalation (ESC) producer from the ledger (H §4.3 "What it needs"). Keep assessment revisions in the assessment files and work notes, not in the finding id. The two adapter bugs are accepted risks (fix direction in H §4.3) |
| H2 | AICT as a required release gate that discovers AgentCore runtimes, Bedrock agents and SageMaker models, with "source-linked traces when available" (DA §8 ServiceNow probe; PA "ServiceNow"; BC Contracts §14) | CHANGE | AICT is live. The facilitators provisioned it, and its role assumes `SgcAictReadOnlyAccessRole` about every minute. It sees AgentCore runtimes and gateways only (Bedrock agents and SageMaker are AccessDenied). Its usage count for our traffic is 0, because it filters on `InvokeAgent`, and Monitor covers Managed agents only. AICT belongs to L2–L3, not L1 (H §2.1, §5.8; PV row 11) | Claim AICT for discovery and observability only. Name our agents `ifabric-…` so they show as `ifabric_…`. Record the zero usage count and the empty Monitor as gaps. Keep the L1 foundation (MoDaaS guardrails + Nemotron) independent of ServiceNow |
| H3 | A human reply is not required; record the alert, its named recipient and the silence; NO_RESPONSE_OBSERVED needs an adequate response source up to a cutoff; a finding closes only with a passing re-test (DA §7, §8A; BC Contracts §14) | KEEP | Slides: the response is not required, but "the alert, its named recipient and the silence must still be recorded" (H §2.5). "A finding closed without a passing re-test" loses marks (H §2.3) | Mind Arth's bug (b): a `sys_journal_field` read that returns 0 rows can wrongly give NO_RESPONSE_OBSERVED (H §4.3). Run `check --cutoff` before judging |
| **I** | **Nemotron investigator** | | | |
| I1 | Investigator model: "Lightning 30B-A3B preferred", with optional Super, Nano Omni and Ultra roles (NV §2; SVG4; DA header) | DROP | The served aliases are `nemotron-nano-3-30b`, `nemotron-nano-9b`, `nemotron-super-120b` and `nemotron-super-120b-helper` (H §7.1). BC "Mandatory source requirements" had already superseded Lightning, Omni and Ultra | Choose among the served aliases. For L3's "other models where appropriate", `nemotron-nano-3-30b` is approved and not yet invoked (PVF) |
| I2 | The investigator is "now a core product feature rather than a final optional bonus", built early on top of C16 (NV §1, §10; BC "Read this first" step 3, Delivery stage 3) | CHANGE | Budget: one helper question used 123,476 tokens, and the 2.5M tokens/h ceiling is account-wide (H §5.6, §3d). The judges' pillars are closing the gap, one control end to end, and the Evidence Pack, and "additional agents … does not itself earn bonus points" (H §2.2, §2.5) | Demote it to an option, after the controls, the agent fixes and the pack. Deterministic case rendering is the dashboard's core. Any model narrative is labelled and budgeted under its own CID prefix |
| I3 | The 60-second two-call choreography, the workload envelope, ≥20 held-out readiness queries with repeat trials, the extraction benchmark and ablation, the cache identity and the query-recovery rules (idempotency keys, cancellation, profiles) (NV §6, §9; DA §10A, §11 M13) | DROP | About 20 hours remained at 18:50 UTC on 2026-10-05 (H §3a item 1). The published limit is two minutes, answered from the pack (H §1, §2.5) | Keep only the 2-minute rehearsal (J3) |
| I4 | Model output is a proposal (CANDIDATE), never a verdict or a threshold; evidence text, including injected instructions, stays data; a deterministic fallback when the model fails (NV §4, §5, §7; BC Contracts §11) | KEEP | The Hostile phase brings "tampered prompts and skills, conflicting context" (H §2.5). The page: treat tool results as untrusted (PC, "Limits of this build") | Apply the same rule to our subject agents' tool results, not only to the investigator |
| **J** | **Judge experience, query and app** | | | |
| J1 | Query by control and run or window: rule and date, population, value and formula, verdict, gaps, sources and alert state on one screen; a C9 run query resolves its windows (DA §11; BC Contracts §13; SNH §8.7) | KEEP | The finish line: "was control 9 satisfied for run FM-B?" answered in two minutes with the records (H §1). "If we have to trawl your logs, you lose the mark" (H §2.3) | The same query engine backs the CLI and the dashboard |
| J2 | The judge client is "local CLI with optional small HTML UI": "The CLI is core; a browser UI is optional" (DA §1.D; PA; BC "Objective": "local/read-only judge UI") | CHANGE | The captain now requires an app with a dashboard. The judged format is a judge-as-auditor who picks an incident from the event window and asks six questions answerable "from your Evidence Pack alone" (H §2.5) | Make the dashboard a core deliverable, built over the pack (§3 R1). The CLI stays as its scriptable twin |
| J3 | Two fresh-start rehearsals in which another person picks the scope, each ≤120 s, with times recorded (DA §11, §10A) | KEEP | "Rehearse it twice before you present" (H §2.4) | Rehearse both the control question and the six-question incident walk |
| J4 | The cockpit is "already provisioned … read-only, every backend route GET", a possible starting point for the presentation (BC Facts K) | CHANGE | `server.py` has 47 GET routes and one POST (`/api/agents/{name}/ask`, which invokes an agent) and no auth of its own. `GET /api/cr/AgentConfig/…` returns the literal ledger write token (PVF; H §5.4) | Don't build on the cockpit's CR views or demo them. Our dashboard must redact env values |
| **K** | **Release and the Evidence Pack** | | | |
| K1 | The six-artifact release contract (`prooflab bundle`), the manifest, and release validation: thresholds predate the runs, rules unchanged across pass and breach, every reference resolves, gaps consistent (DA §10; BC Delivery "Exactly six") | KEEP | The six MUST deliverables, and "If an artefact is missing we cannot score it" (H §2.4) | Align it with `submit.sh`'s real mechanics (K2) and add the token-redaction step |
| K2 | Hand in with `submit.sh` "after inspection": it packages `~/evidence`, the register, the gap list and the run ids (BC Facts L; SNH §8.6) | CHANGE | `submit.sh` needs a team name: `submit.sh <team>`. It zips `~/evidence/` as it is, plus `register.yaml`, `gap-list.md`, `run-ids.txt`, `sketch.png/.jpg` and `MANIFEST.txt`, uploads, prints a presigned URL and leaves a zip in the current directory. `pull-evidence.sh:78` copies the literal ledger token into `cr-status.json` (MUST-FIX) (H §2.4, §3d) | Add a release step: redact env values from `cr-status.json`, check `tmf639.json`, scan the zip, then submit, read back and compare SHA-256. Keep `TEAM_EVIDENCE_BUCKET` set |
| K3 | An independent arithmetic rechecker over exported inputs, never calling the production evaluators; an offline recheck on a clean client (DA §10, §10A; PA "One repo") | KEEP | Evidence must be "Verifiable by somebody who is not you" (H §2.3) | The rechecker reads the exported `aws/spans` rows, the ledger JSONL, the metric windows and `register.yaml`. It also gates PRs (§3 R7) |
| **L** | **Adversarial testing** | | | |
| L1 | The "Active testing" catalogue of software faults (retry burst, two-call race, duplicate delivery, dropped attempt, cross-run mislink, stale spec, missing window, degradation, delayed human response), plus a bounded Nemotron test proposer (PA "Active testing"; DA §9) | CHANGE | The event's phases are Hostile (delays, tampered prompts and skills, conflicting context) and Rogue (bypass attempts, unauthorized tool use, tampered records) (H §2.5). The verified defences differ from the playbook's: undeclared tool calls are ALLOW today, a Cedar DENY needs a ToolConfig rule, and the ledger has no verification (PV rows 1, 2) | Rebuild the catalogue by phase and EP (§3 R6). Keep software-fault fixtures as offline unit tests. Drop the proposer |
| L2 | Removing records from a copied export is COUNTERFACTUAL_EXPORT and proves checker sensitivity only; an unsafe perturbation of a shared system needs an approved isolated scenario (DA §9; PA "Control 7") | KEEP | Destructive record tests run on exported copies only, and shared `team-*` Lambdas are never touched. Adversarial writes pollute the shared ledger and the event window (H §3c step 6, §3d) | Carry these as rules of the adversarial log |
| **M** | **Delivery** | | | |
| M1 | Two-person roles A and B, day 1 and day 2 targets, the first access block, a feature freeze at T−12 h and a repair window at T−4 h (DA §12; NV §10; BC Delivery; PA "Delivery order" 4–6 Oct) | DROP | Superseded by the captain's delivery model (a Firstmate fleet, one serialized live lane, PR gates). The 4–5 October schedule has passed. About 20 hours remained at 18:50 UTC on 2026-10-05, and the end time ("10 a.m. Tuesday") is unconfirmed (H §2.5, §3a item 1) | Replace with the lane plan in §3 R7. Keep freeze buffers, re-timed to the real cutoff |
| M2 | Cut order: the adaptive proposer; visual polish; a generic kill-switch demo; extra adapters; the inline bonus if it displaces a complete control (DA §12) | CHANGE | The judgment gap is a pillar, not polish (H §2.2), and the dashboard is now required (the captain) | Proposed new cut order: investigator → extra Cedar scenarios → inline C16 → third control → second control. Never cut the agents' evidence fix, one complete control, the pack or the gap list |
| M3 | Build order: "one real C16 passing/breaching evidence path first, then add the bounded Nemotron investigator early"; the C9 baseline in parallel; S2 improvement as optional differentiation after the controls (BC "Read this first", Delivery "Optional differentiation") | CHANGE | Closing the gap is core (H §2.2). Every new agent version is a C9/C16 treatment, so agent changes must come before the register freeze and the C9 baseline hours (H §3a items 1–2; H §3c step 1) | Live-lane order: IT model decision → agent fix or build → approval → register freeze → baseline hours → assessed runs → adversarial tests → snapshot → submit (§3 R7) |
| M4 | The reference self-check: "S1 PASS 8/8; S2 FAIL 7/10; S3 PASS 10/10"; preserve S1/S3 (BC Facts F, "Constraints") | CHANGE | Our runs: S1 6/8, S2 5/10, S3 8/10. All three fail by construction: the agents write no guardrail verdict, and the negotiation stub is never reached (PV row 4) | Make a legitimately passing self-check an agent requirement (a guardrail verdict for every model call). Report the negotiation check honestly |
| **S** | **Subject agents and platform rules** | | | |
| S1 | Retain and verify the supplied Nemotron agents; custom agents follow the workshop rules; the agents are the system under assessment and stay unmodified (DA §1; NV §3; R6 idea 1: "We never touch their agents") | CHANGE | "Building more or changing the agents" is allowed (H §2.5). The reference agents write no action_id, tokens, model or guardrail verdict. Their ledger trace ids differ from the run trace, they log an MCP 403 as a 500, and they write the tool-invocation record after the model call (H §3b Q12; gap 1) | Plan our `ifabric-*` agents (a fixed reference `agent.py`, or our own). They write the platform's facts into the ledger: the action id from `x-modaas-action-id`, the inbound trace, the model, tokens, the guardrail outcome and the true refusal status. They decide dispositions explicitly (§3 R4) |
| S2 | Model swap: "patch both dependsOn.models[0] and modelRef … record new review" (BC Facts F) | CHANGE | `MODEL_ALIAS` follows `dependsOn.models[0]` when `modelRef` is absent or equal to it, and a CRD rule requires `modelRef` to be one of `dependsOn.models`. A swap needs no re-approval, and re-annotating adds no approval record (H §3a item 1; gap 5) | Check the runtime's `MODEL_ALIAS`. Record our own approval note for each version (the fix idea in gap 5), because the platform won't |
| S3 | The account ceiling of 100 req/min and 2.5M tokens/h, with one coordinated limiter (~80 RPM) for all traffic, helper and investigator included (BC Facts E, "Constraints") | KEEP | Confirmed: `local` limits on one replica, so effectively account-wide. The token ceiling binds first: S2 used 80% of it in under 5 minutes. The 429 is untested (H §5.5; gap 8) | Enforce it as the live lane's pre-run headroom check (§3 R7) |
| S4 | Nemotron required for valid agents; hosting only in the supplied AWS/ServiceNow environments; agents through a ModelConfig alias, AgentConfig → AgentCore, and CodeBuild/ECR (BC "Mandatory source requirements") | KEEP | L1 Foundation: "agreed MODaaS guardrails and NVIDIA-supplied model". Agents must operate in the provided environments (H §2.1, §2.5). The runtime IAM role denies direct Bedrock calls (H §5.1) | Every new agent goes CodeBuild → AgentConfig → approval (H §3b Q12). Check names with `new-agent.sh --dry-run` first (PV row 9) |
| S5 | The env contract "OPENAI_BASE_URL, OPENAI_API_KEY, MODEL_ALIAS; another page calls the tool credential GATEWAY_API_KEY"; secrets only through platform mechanisms (BC Facts H) | CHANGE | No `GATEWAY_API_KEY` exists. The operator injects one shared key as `OPENAI_API_KEY` and `AGENTCORE_GATEWAY_MCP_TOKEN`. The only literal credential in the specs is `AUDIT_WRITE_TOKEN`, which every participant can read (PV row 13; H §5.1, §5.4) | Agent code reads those env names and fails closed. The app and the pack never render env values |
| **V** | **The earlier V3 revision** | | | |
| V1 | V3's refinements: closing a run's actions waits for source-completion records; settlement releases the reservation on the first settle; a finding closes with a passing re-test plus owner action (V3 §3–§7) | DROP | DA later revised all three, and the coordinator they refine is dropped (A3, B1). Otherwise V3 matches DA's foundation | No separate action; audit DA only |

Count (from the verdict column): KEEP 22, CHANGE 40, DROP 11; 73 rows.

---

## 1A. Fit to the captain's target pattern

Row ids refer to §1. **Fits as is** = KEEP rows that already match the layer. **Reshape into it** = CHANGE rows that become the layer. **Missing** = nothing in the prior design covers it.

| Target layer | Fits as is (KEEP) | Reshape into it (CHANGE) | Missing |
|---|---|---|---|
| **EP adapters** | B3 (only verified in-path hooks refuse); B5 (no per-agent identity claimed) | A7: platform adapters → one adapter per EP. A6: handoff obligations → an emit-only handoff adapter in the orchestrating script and at escalation. B6: the human approval queue → a records-only ServiceNow/human loop. H1: the M14 delivery contract → Arth's package as the ServiceNow/human adapter | Platform-EP adapters that record the **real outcome** where the platform logs ALLOW (guardrail block, pause). An approvals/admission adapter. A ceiling (429) observation. The agent-runtime adapter inside our `ifabric` agents (S1), which hosts the one in-path question (B10) and replaces the dropped coordinator (B1) |
| **One contract** (`evaluate`/`emit`/`callback`/`pull`) | B2 (four transports) | B10: C16 admission → the one optional `evaluate()` before each model call. B11: the multi-control admission API → `evaluate()` for C16 only. B9: the second EP → the same C16 evaluator behind two adapters | One decision-record schema that all four transports carry. The prior design has a separate envelope per transport (DecisionEnvelope, Receipt, SourcePage; BC Contracts §3) |
| **Registry-versioned stateless evaluator** | G1 (verdict dimensions); G3 (justify, then freeze); D1 (accounting rules); E2 (C7 arithmetic); F3 (alert on every crossing); I4 (the model never sets a verdict) | G2: PolicyBundle → `register.yaml` as the registry. D2/D3: C16 source and cap. E1/E3: C7 population and breach cases. F1/F2: the C9 metric | C7 and C9 evaluators (the kit has only C16). Registry and evaluator versions stamped on every decision. The threshold-experiment protocol (§3 R3) |
| **Every decision recorded with full metadata, in one append-only evidence store** | P5 (provenance classes); P6 (preserve before acknowledging); L2 (tamper tests on copies only) | P10: the workspace → the one store (physical store undecided). P4: the record set. P13: owner metadata on every record | The decision-record schema: <br>• the EP and the acting agent <br>• the decision as the platform recorded it, the real outcome and the reason <br>• policy id and version; principal; the asset and its approval; owner/responsible <br>• CID, action id and trace id; times; provenance; source reference <br>Human decisions (CR approvals, ServiceNow responses) as records. Our agents writing such records (S1) |
| **Stitcher** (CID / action id / trace id) | P11 (source-authority map) | P12: EvidenceBinding → the stitcher. P3: the canonical keys. P2: `/aws/modaas/gateway` demoted to a trace-id-only copy | Stitch rules for refusals (the trace-id hop), for ledger records and agent spans without an action id, for runner/handoff records (by CID), and for ServiceNow (`finding_id` ↔ `scope_id` = CID). Unmatched records written as gap records. The spine is `aws/spans`, which BC wrongly ruled out (P1) |
| **Control test and dashboard over the store** | J1 (query contract); J3 (rehearsals); K3 (independent rechecker); K1 (six-artifact release) | J2: the judge client → the dashboard. I2: the investigator, demoted to an option | The dashboard app (§3 R1), which reads only the store and the stitcher's output, in live and pack modes |

The remaining rows (topology and placement, integrity, breach levers, the investigator's model, delivery, and the platform rules for agents) are constraints on the pattern rather than layers of it.

---

## 1B. In-path elements against the captain's rule

**The rule:**
- There is one in-path question: the optional C16 check before each model call, against a frozen, version-stamped threshold, with no registry call in the path.
- Handoffs are emit-only records.
- Everything else records.

Every prior element that makes agent work wait:

| Prior in-path element (prior §) | Verdict (row) | Becomes |
|---|---|---|
| C16 admission: `evaluate()` per model request; no dispatch before a durable reservation (DA §6; PA "Control 16 runtime protocol"; SVG3) | CHANGE (B10) | The one in-path question: the optional C16 check before each model call, in our agent code, with the frozen, version-stamped threshold. Every decision is emitted |
| Reservation state machine, dispatch ownership, settlement finality, fail-closed ERROR on a store outage (DA §6) | DROP (B1) | Nothing in the path. Accounting is post-run over `aws/spans` |
| Admission through a gateway function or wrapper, or AgentCore Gateway interceptors (DA §1.B; PA) | DROP (A2) | Nothing of ours. The EP adapters record the platform's own decisions (A7) |
| The multi-control admission API: "required-admission-control ERROR prevents dispatch" (DA §2) | CHANGE (B11) | `evaluate()` serves C16 only. C7 and C9 run after the fact and never block |
| The run-opening gate: reject missing or expired policy bundles "when opening governed work" (DA §3, §4) | CHANGE (G2) | No gate. The threshold travels frozen and version-stamped with the agent |
| Run closure: ACTIONS_CLOSED "stops new governed work through verified inline coordination" (DA §4, §6) | CHANGE (B8) | An as-of cutoff on assessments only; nothing stops work |
| Pre-dispatch obligation registration: a dispatcher/coordination journal registers `model.requested`, and an orchestrator registers `tool.requested`, before dispatch; "Dynamic work adds obligations before execution" (DA §3 Obligation key, §4) | CHANGE (E1) | No write before dispatch. Expected events come from platform-written records after the fact (P1), and our agents `emit` their own records |
| Handoff refusal or timeout as terminal states of a gateway handoff (DA §2, §4) | CHANGE (A6) | Emit-only handoff records from the orchestrating script. A missing receipt is a recorded gap |
| A human approval queue or ServiceNow callback that holds an action; "delayed human decisions" (DA §1.C; BC "Five architecture questions" #5, Contracts §3; SNH §7.4 "EP #2") | CHANGE (B6) | `callback`/`pull` records of the alert and the response. It never holds work and is not claimed as an EP |

**Already compliant, no change needed:**
- The register is never queried in the path, and the frozen spec is passed to the evaluator as an argument (DA header, M04 note: "The register stays off the request path"; PA "Control 16 runtime protocol" step 1; SVG3 "No register lookup per inference"). This matches "the registry is never called in the path" (§2, item 1).
- ServiceNow delivery "does not block inference or case publication" (DA §8A), and the investigator "never blocks fault-resolution inference" (SVG4). Both only record.
- `emit()` receipts state DURABLE_ACCEPTED, BEST_EFFORT or REJECTED (DA §2; BC Contracts §3). Under the rule, a failed record write must not make work wait: buffer or retry it, and let it surface as a C7 coverage gap.

**The platform's own EPs stay in the path, because they belong to the platform:** authz, the PDP/Cedar, guardrails, ceilings, the kill switch and admission CEL. We configure Cedar rules on our own ToolConfigs there (R2), which adds no waiting point of ours, and we record their decisions with the real outcome (A7).

**Two of this audit's first-draft proposals were recast as records** in R2 and R4: an in-agent tool allowlist that would refuse undeclared tools, and refusing when the evidence comes back empty.

---

## 2. Still sound and worth keeping

These are the prior design's strongest ideas. Each still holds against the verified platform, and several are exactly what the judges score.

1. **The five habits, as architecture** (DA §1–§2; PA "Control 16 runtime protocol" step 1; BC "Five architecture questions"). Telemetry never judges, the evaluator is stateless and is passed its frozen spec, the register stays out of the request path, and the ledger never interprets. These are verbatim judging questions (H §2.3): "Is the register out of the live path? Is the evaluator stateless? Does the control hold its own threshold?"
2. **Honest verdicts** (DA §7, G1).
   - Four states, with requirement, safeguard operation and evidence sufficiency kept separate.
   - A known subtotal over the cap proves BREACHED even with gaps. Missing is never zero, and an empty denominator is NOT_ASSESSED, never 100%.
   - This is Axis 2's "Built properly: yes. Actually worked: no", and it is what makes refusals recorded as ALLOW (gap 4) reportable without overclaiming.
3. **An expected population independent of the graded agent** (DA §4, E1). The prior design had no source for it. The platform now supplies one: `aws/spans` and `/modaas/evidence` are written by the gateway and authz, not by the agents, so the agents' ledger can be tested against them.
4. **The whole-run accounting rules** (DA §6, D1): one charge per call, never a parent plus its leaves, corrections replace rather than add. They anticipate the two traps actually found: `show-run-spans.py`'s 2× total and `evaluate.py` counting MCP lines.
5. **Provenance classes** (P5). LIVE_SUBJECT, AUTHORIZED_TEST, REPLAY, COUNTERFACTUAL_EXPORT and SYNTHETIC are exactly what the adversarial log and the "tamper tests on copies only" rule need.
6. **The independent offline rechecker and a self-contained pack** (DA §10–§11, K3): every reference resolves locally, one command gives the answer, and the first screen lists rule, population, value, verdict, gaps, sources and alert state. This answers "verifiable by somebody who is not you" and "if we have to trawl your logs, you lose the mark".
7. **The model never sets a verdict** (NV §4–§7, I4). Model output is a candidate, evidence text stays data, and there is a deterministic fallback. The rule now also belongs inside our subject agents, which face tampered prompts and tool output in the Hostile phase.
8. **Alerting discipline** (DA §5, §8A, F3, H3): every crossing alerts a named owner even inside the allowance; delivery, response and remediation stay distinct; silence is recorded; a finding closes only with a passing re-test. All of this matches the slides and Arth's contract.
9. **Capability gates and status labels** (DA §8; BC "Authority and provenance": DOCUMENTED is not LIVE_VERIFIED). Stop speculative coding when a source fails. This discipline is what produced today's corrections, and it should govern every new claim in the pack.
10. **Subject vs assurance spend** (D6) and **the source-authority map** (P11), both now fillable with verified sources.

**Ideas worth borrowing from the pre-kickoff alternatives (R6).** They were written for a different arena, so these are adaptations, not audit findings:

| R6 idea | Where it maps here |
|---|---|
| **Authorship tags**: tag every record by who wrote it (GATEWAY vs TESTIMONY vs UNKNOWN AUTHOR) | The ledger is agent-written testimony; `aws/spans`, the PDP and `/modaas/evidence` are platform-written. Tagging each record makes the corroboration-based INTEGRITY answer and the ALLOW trap explicit on the dashboard |
| **A separately written Recheck** | The independent rechecker (K3) |
| **The rulebook audit**: check the declarations against each other and against behaviour | Turns gaps 3, 5, 9 and 11 into automated checks: declared `dependsOn.tools` vs tools actually called; approval time vs the version that ran; missing `dataClassification`; Lambda `CodeSha256` vs approval |
| **C0, the sole credential holder** with a read budget, rate caps and a kill switch | The serialized live lane (§3 R7) |
| **The gated repair loop**: a recheck disagreement opens a PR, which passes a gate, then a human merges | The "no-mistakes" PR gate (§3 R7) |

---

## 3. Missing for the new requirements

For each of the captain's requirements: the nearest part of the prior design, then what it lacks.

### R1. An app with a dashboard (evidence ledger + control test tool)

**Nearest prior:** DA §1.D and PA ("CLI core; small HTML UI optional"); DA §11 / BC Contracts §13 (query contract); DA §10 (offline pack); SNH §8.7 (one-screen output).

**Missing:**
- **It queries the store, nothing else.** The captain's pattern puts the dashboard on top of the one evidence store and the stitcher (P10, P12). The prior query reads assessments and source captures directly.
- **The app as a product.** No prior view list exists. The dashboard needs:
  - a **control registry** view (the `register.yaml` versions, dates, owners and EPs)
  - an **evidence ledger** view: per run, one timeline joined across `aws/spans` → `/modaas/evidence` → PDP → ledger, with an authorship tag on each record and the *real* outcome of each call (served, guardrail-blocked or pause-refused), because the platform records refusals as ALLOW
  - a **control test** view: the judge types a control and a run or window and gets the verdict with its records in under 2 minutes; the same screen can re-run the control test against fixtures (pass, breach, missing data)
  - a **six-question incident** view (WHO, WHAT, AUTHORIZED, APPROVED, INTEGRITY, RECONSTRUCT) with honest limits: WHO = `bootstrap-key` plus the ledger actor; APPROVED = annotations with an empty signature, flagged when older than the running version; INTEGRITY = corroboration plus the MANIFEST
  - the **adversarial log**, the **ServiceNow loop status** (offline, from the delivery log) and the **gap list**

  The prior design is control-centric. It never covers the judged format, where a judge-as-auditor picks an incident from the event window (H §2.5).
- **Two data modes, which the facts force.**
  - *Pack mode* is static and offline, built from the files judges open from the S3 bucket. It is the judged artefact.
  - *Live mode* is read-only and uses the live lane's credentials: Logs Insights on `aws/spans` and `/modaas/evidence`, kubectl reads of the ledger and the PDP. The participant role is verified for those reads (PVF).
- **Hosting.**
  - The cockpit is not a substrate: it has a POST and leaks the token (J4).
  - That `components` pods have no AWS credentials is documented (BC "Facts A") but not re-verified.
  - Agents must run on AgentCore, but nothing says where a dashboard runs.
  - Decide: the laptop or the IDE host for live mode, a static HTML pack for judges.
- **Naming and security.**
  - "Evidence ledger" in the app is our derived, read-only index. The platform's `audit-store` stays raw ("the ledger never interprets").
  - The app must never render env values or tokens (S5, K2).
  - A dashboard refuses nothing, so it is never claimed as an enforcement point (B3).

### R2. Security and guardrails at every enforcement point, including Cedar changes via ToolConfig

**Nearest prior:** DA §1.A ("install/configure only through supported workshop hooks"), DA §8 capability gates, BC Contracts §1 and Delivery stage 5 (team ConfigMap). The prior design treats platform EPs as fixed context. It has no per-EP security design and no Cedar authoring, and its Cedar lever is the inert ConfigMap (B4).

**Missing:** an EP-by-EP matrix. The draft below is built from H §5.9's six EPs, the five enforcing points the page omits, our agent runtime and the human loop. In the captain's pattern each row is one EP adapter (A7), and the last column is what that adapter writes into the store as the decision's real outcome. Our design adds exactly one in-path question, the optional C16 check before each model call (B10). The platform's EPs below stay in the path as the platform's own: we configure what we may there, Cedar rules on our ToolConfigs, and record every decision.

| Enforcement point | What we configure | What we test (Hostile/Rogue) | How a refusal is recorded | How we report the real outcome |
|---|---|---|---|---|
| Gateway + PDP (Cedar) | `forbid` rules in `access.cedarPolicy` of our `ifabric-*` ToolConfigs; `dataClassification` on our tools (`customer-records` and `network-twin` have none, gap 9) | An out-of-scope tool or argument → DENY; how long an edit takes to propagate; whether the edit resets approval (both untested) | DENY in the PDP and `/modaas/evidence`. This would be the first Cedar DENY ever: 0 of 1,097 so far | The PDP decision joined to the gateway line by `action_id`; policy version = ConfigMap `resourceVersion` |
| `modaas-authz` extAuth (API key, FailClosed) | Nothing (protected) | A call without the key → 403 | DENY `NoSigV4Credential` in `/modaas/evidence`; the gateway 403 line has no ids | The evidence record |
| Bedrock Guardrails (one per ModelConfig) | Nothing on existing models. Our own ModelConfig with a stricter guardrail is possible but untested and needs approval | Prompt injection in user input and in tool output (tool-output screening is untested) | **ALLOW** in the PDP and `/modaas/evidence`; HTTP 200 `content_filter`, 0 tokens | The gateway line, plus a guardrail field in our agents' ledger records |
| Admission (94 CEL rules + VAP) | Nothing. Our CRs must pass it; `components` is open | An unsafe ModelConfig is rejected (even a server dry run is a write step that needs the user's OK) | An API error at apply time. EKS audit logging is off | Captured command output in the pack |
| Ceilings (100 req/min, 2.5M tokens/h) | Nothing; the live lane keeps headroom | Not deliberately: it would hit every team member's runs. The 429 is untested | 429 (untested) | The gateway line |
| Kill switch (pause) | `spec.paused` on our own assets only | Pause our tool mid-run (~1–7 s) | **ALLOW** plus a 404 without a run id | The trace-id join (gap 4) |
| Runtime IAM deny | Nothing | Optionally, an agent attempts a direct Bedrock call | AccessDenied | The runtime log |
| AWS AgentCore Gateway (`AWS_IAM`, Lambda tools) | Nothing; never touch it | Record each tool's Lambda `CodeSha256` (gap 11) | — | A code-hash check against approval time |
| **Our agent runtime** (in the path, our code) | The one in-path question: the optional C16 check before each model call, with the frozen, version-stamped threshold (B10). Everything else is recorded, not refused: <br>• each tool call against the declared tools (undeclared use is emitted as a finding, gap 3; refusing it is left to a platform Cedar rule) <br>• tool output flagged as untrusted <br>• the agent's own disposition (auto-resolve, gather evidence, escalate) with its reason, including when the evidence comes back empty (gap 10) | An S2-style loop (the C16 check refuses the next model call); an injected tool result; an undeclared tool call (recorded; a Cedar `forbid` refuses it) | Our C16 refusal: our record with the threshold version, and no gateway call | Our records cross-checked against `aws/spans` |
| Evidence ledger (token-gated writes) | Our agents write richer records with the token | A write without the token → 401 (pollutes the shared ledger: ask first) | The 401 response only (request logging is off) | The captured response |
| ServiceNow human loop | Finding → `notify()` | An escalation (ESC) from an S3 run; an outage | The delivery log | Records only; it never holds work (B6) |
| OTel collector / CloudWatch | Observe only | — | — | — |

**Also missing from the prior design:**
- The agents' plain-HTTP gateway path (gap 9). Whether our agents can use the TLS :8443 listener is untested.
- The Cedar-change lifecycle: Cedar policy files reviewed in a PR, each edit applied by the live lane with the user's OK, and the projected ConfigMap version recorded as `policy_version` evidence.
- The open question of which policy the PDP selects for a cloned tool (B4).

### R3. C7/C9/C16 with threshold experiments and a control registry

**Nearest prior:** DA §4–§6 (control math, "justify then freeze"), DA §3 PolicyBundle, DA §10 `thresholds/`.

**Missing:**
- **The evaluators.** The kit ships only C16 (`evaluate.py` `_METRICS = {"16": …}`), and it counts MCP lines as calls. C7 and C9 evaluators don't exist (H §3b Q4).
- **An experiment protocol.**
  - Calibration runs in the live lane on the final agent versions, labelled EXPLORATORY and budgeted (S1/S3 cost ~25–50K tokens each; the unfixed S2 costs ~2.0M, which is 80% of an hour).
  - What each experiment measures: the per-run token distribution for C16 tiers, baseline hours for C9, achievable coverage for C7.
  - Then the freeze. No such protocol exists in DA.
- **C16 tiers.** The judge's risk-matrix hint calls for a pre-declared matrix → tier → cap table, with a deterministic or host-validated classification, every classification recorded as evidence, and a decision on whether helper/investigator calls count (H §3b Q2). DA has one illustrative cap.
- **The registry.** `register.yaml` in the kit's fields, plus a version, the tier table, the evaluator version and the enforcement point per control (G2), with the owner = Sree (the user) (H §1).
- **A mechanical date check.** `version_date` and the GitHub merge time of the register PR must both be earlier than the epoch inside each assessed CID (`fault-<epoch>-<hex>`, RAF). The rechecker refuses an assessment that fails this. It answers "we check the date" with a server-side timestamp.
- **Breach levers per control**, since the twin can't produce them: C16 (D4), C7 (E3), C9 (F4). Write the named run ids before judging.
- **Separation of duties** with two people (H §3b Q14): who acts as assurance when the owner also builds.

### R4. Agents that close the judgment gap and emit real evidence

**Nearest prior:** BC Delivery "Optional differentiation" (improve S2 after the controls); NV §3 (retain the supplied agents); R6 idea 1 ("never touch their agents"). The prior design has **no agent design at all**.

**Missing:**
- **The agent set and its path.** `ifabric-…` names (≤40 characters, checked with `--dry-run`, PV row 9) through CodeBuild → AgentConfig → approval. The IT model decision comes first (H §3a item 1).
- **A judgment policy per scenario:** S1 auto-resolve; S2 gather-evidence, naming the deciding evidence and proposing a reversible step; S3 escalate (H §3b Q8).
- **Grounding checks.**
  - Resolve each element to its site before querying the twin.
  - Detect "no twin data" and other empty results, then gather evidence or escalate (gap 10).
  - Record which retrieved passage supports each claim, and record the disposition as an explicit decision with a reason, not a keyword guess (gap 1).
- **Evidence emission that the platform corroborates.** One ledger record per call, carrying:
  - the `action_id` from `x-modaas-action-id`, so each record joins to its span and PDP decision
  - the inbound trace id, the model alias and the tokens
  - the guardrail outcome (`content_filter`)
  - the true status of refusals (403 or 404, not 500)
  - and the tool-invocation record written before the model call

  This turns agent testimony into records corroborated by platform-written ones, and it lets C7 test coverage per call. It is the agent-runtime adapter of the captain's pattern: it records with `emit()` and refuses with `evaluate()`.
- **One in-path check; everything else recorded.** The agent runs the optional C16 check before each model call (B10). Tool calls against the declared tools, untrusted tool output and empty evidence are recorded, not refused, and the agent's own disposition (gather evidence or escalate) is recorded with its reason (see the "our agent runtime" row of the R2 matrix). Agents don't call each other; the orchestrating script emits the handoff records (A6).
- **Version pinning.** Each version is a C9/C16 treatment, so it must exist before the freeze and the baseline hours (M3).
- **Self-check.** A guardrail verdict for every model call, so the grader can pass legitimately. Report the negotiation check honestly (M4).
- **What the agents can't fix:** the WHO limit (one principal) stays. Answer it with the ledger actor plus the per-runtime log group (B5).

### R5. The ServiceNow human loop (Arth's `prooflab/servicenow` Finding contract)

**Nearest prior:** DA §8A and BC Contracts §14, a generic contract that is stricter than, and different from, Arth's (H1).

**Missing:**
- **Its place in the pattern.** Arth's package is the ServiceNow/human adapter: `notify()` is its `callback()` and `check` is its `pull()`. Every delivery and response event becomes a decision record in the store, carrying the incident's assignee and responder (P13).
- **Binding to the contract.** The prior design never names Arth's specifics:
  - the Finding fields and `finding_id`
  - the verdict set: no NOT_ASSESSED, plus ESCALATED with `scope_kind: escalation` (G1)
  - notify only for BREACHED, ESCALATED and `monitoring-gap`, never for SATISFIED
  - the evidence prefixes, the §8.2 assessment shape and the §8.3 layout
- **The glue to write** (H §4.3):
  - the evaluator runner `publish()`
  - the **ESC producer** from the ledger: parse `/records?cid=` JSONL for `disposition=escalate`. The kit's Rail 1 script has traps: no escalate check, not idempotent, no assignee.
  - the MANIFEST builder
  - the dashboard's offline "Human loop" line, read from the delivery log
- **Before judging:** run `check --cutoff` and `export` for each finding (SNH §8.4).
- **Credentials:** `SNOW_*` from Arth, read with `read -rs`; if kept in a file, `~/.prooflab-snow.env` with mode 600; add the secret to the pre-push scan (H §4.3).
- **Volume:** bound C9 incidents (F3).
- **The two adapter bugs** are accepted risks; their fix directions are in H §4.3.
- **Not an enforcement point** (B6): the human loop records the alert and the response, and never holds work.
- **AICT proof** is Arth's (screenshots, the CloudTrail AssumeRole record), and the zero usage count goes into the gap list (H2).

### R6. Adversarial log

**Nearest prior:** DA §9 / §10 ("adversarial.jsonl … optional proof"), PA "Active testing", NV §9 (investigator-focused cases). These cover our own software's faults, not the event's threat model.

**Missing:**
- **A schema.** Each entry records:
  - test id, phase (Hostile/Rogue), the EP attacked and the attack class
  - the expected defence, written and dated *before* the test (pre-registered, like thresholds)
  - the provenance class
  - the live-lane booking
  - the observed outcome on each surface (gateway line, PDP, `/modaas/evidence`, ledger, `aws/spans`)
  - the verdict: HELD, DETECTED-ONLY or BROKE
  - what broke, the fix PR and the re-test id
- **Coverage by phase and EP:**
  - **Hostile:** delays; tampered prompts → guardrail (recorded ALLOW, seen as 0 tokens); tampered skills and conflicting context → our agents' judgment and their handling of untrusted tool output.
  - **Rogue:** unauthorized tool use → recorded by our agent-runtime adapter and refused by a ToolConfig `forbid` (the platform's PDP); bypass attempts → the runtime IAM deny (verified), and the pod-backend and Lambda side doors as gaps, never touched; tampered records → run on exported copies and caught by cross-surface corroboration.
- **Detections in our evaluators:** undeclared tool use from `route_alias` in `/modaas/evidence` (gap 3); guardrail blocks from `content_filter` with 0 tokens; pause refusals from the trace-id join (gap 4).
- **Safety rules:** the budget, the serialized lane, copies only for record tampering, no shared Lambdas, the user's OK for cluster writes, and never writing down methods for forging records (H §8).
- **Organiser-injected events.** Who injects the Hostile/Rogue conditions is unknown (H §9), so the log must also record events we *observe* in the window, not only our own tests.

### R7. Delivery by a Firstmate fleet: one serialized live lane, no-mistakes PRs

**Nearest prior:** none. DA §12 and BC "Delivery" plan two people with AI help; nothing in the prior design covers an agent fleet, lanes or PR gates. R6's "C0 sole credential holder" and "gated PR → human merge" are the closest analogues, from a different design.

**Missing, and what the verified facts imply:**
- **Why exactly one live lane:**
  - The budget is account-wide on one gateway replica (100 req/min, 2.5M tokens/h), and one S2 run spends ~80% of it.
  - A pause hits every agent using the asset.
  - Adversarial and agent writes land in the shared ledger and the event window.
  - The C9 baseline needs undisturbed, comparable hours.
  - Every write needs the user's OK (H §3d, §8).
  - Credentials expire and must be refreshed by the user (H §0.4).
- **Lanes:**
  - **Offline lanes** run in parallel worktrees on recorded fixtures (the 17:37Z snapshot): the C7, C9 and C16 evaluators, the rechecker, the dashboard, the ServiceNow glue, Cedar policy drafts, adversarial tooling, docs and the gap list.
  - **The live lane** is the only holder of cluster, AWS and ServiceNow write paths and of the gateway key and ledger token. It runs builds, approvals, agent runs, Cedar edits, pauses, `notify`, snapshots and `submit`, one at a time. It checks headroom before every run and logs each action: time, CID, provenance, budget before and after, the user's OK.
- **Live-lane order:** IT model decision → `ifabric` agents built and approved → register PR merged (dated) → baseline hours → named assessed runs (pass/breach, ids written down) → Hostile/Rogue tests → re-snapshot → redact → `submit.sh <team>` → readback and SHA-256 → two rehearsals.
- **"No-mistakes" PR gates:**
  - the offline fixture tests pass
  - the rechecker agrees with the evaluators
  - the secret scan prints `RESULT: clean` (it needs valid credentials)
  - no threshold literals in control code
  - the register date precedes every assessed CID's epoch
  - no unredacted env values in any pack file
  - no LIVE claim without a capture
  - a separate reviewer agent signs off
  - commit messages carry the session's `Co-Authored-By` trailer
- **Separation of duties.** A reviewer agent is engineering review, not the GRC independence the brief asks for ("Do not invent people or approvals"). State who is the assurance role.

---

## 4. The prior design's open items, and whether they're answered now

Status: ANSWERED · PARTLY · OPEN, with the source.

**DA §13 ("What remains open")**

| Item | Status | Now |
|---|---|---|
| Real source payloads and hooks | ANSWERED | The field shapes of the gateway line, `aws/spans`, `/modaas/evidence` and the ledger are known (H §5.3; PCV §3–§5). No gateway hook. The only levers are ToolConfig Cedar, our runtime and pauses (H §5.9) |
| Baseline labels and cohort acceptance (C9) | PARTLY | Scenario expected dispositions exist (H §3b Q8). The metric and statistic are undecided, and no clean baseline hour exists yet (F1, F2) |
| Threshold values, rationale and owners | PARTLY | The owner is Sree (the user) (H §1). The values are not frozen; measurements and the risk-matrix hint are in hand (H §3b Q2) |
| Allowed compute and storage | PARTLY | Agents only on AgentCore (an organisers' rule). The runtime role's inline policy grants no store. The ledger is writable with the token. The team bucket is writable from our shell. DynamoDB and app hosting are unverified or undecided (A3, A4, R1) |
| ServiceNow permissions | PARTLY | Arth's OAuth client-credentials integration, an `itil` user, incident API, 46 offline tests. Unverified by us; credentials needed (H §4.3) |
| Provider usage bounds and idempotency | PARTLY | Moot for the dropped coordinator. For an in-agent check, the reference agents' `max_tokens=500` per call bounds output (RAF). Hidden provider retries are not visible in our sources (untested) |
| Accepted provenance of breach cases | PARTLY | The twin can't produce breaches. Natural cases exist (D4, E3). Organiser acceptance was never asked |

**DA §8 capability gates**

| Gate | Status | Now |
|---|---|---|
| Model gateway probe (a 3-agent run plus a retry) | ANSWERED | S1/S2/S3 reconciled; stdout equals `aws/spans`. No inline hook (H §5.6; PV row 7) |
| Zone/tool probe | ANSWERED | No zones or handoffs. Undeclared tools are callable through any route (gap 3) |
| C9 probe | PARTLY | Metrics exist, but Errors missed the runaway and the statistic is open (PV row 8) |
| ServiceNow probe | PARTLY | AICT is live and reads our account; finding delivery and readback are per Arth, unverified by us (H §4.3, §5.8) |
| Model probe | ANSWERED | The subject agents use Nemotron through the governed path. Lightning doesn't exist here (I1) |
| Compute, storage and network probe | PARTLY | See "Allowed compute and storage" above. NetworkPolicies are egress-only, and pod side doors exist (PCV §1–§2) |

**NV §10 implementation readiness gate**

| Item | Status | Now |
|---|---|---|
| Exact approved model route | ANSWERED | Aliases on `modaas-agw` :8081 `/v1/chat/completions`, OpenAI wire format (H §7.1; PVF) |
| One request with usage | ANSWERED | First governed call: 23 input / 8 output tokens, with ids in the headers (PVF) |
| JSON and tool capability test | PARTLY | Strands tool calling works in `my-agent`. Structured JSON output is untested |
| Source-scoped read interface | OPEN | A design item for the app (R1) |
| Pilot workload measurements | PARTLY | A helper question costs 123K tokens (H §5.6) |
| Accepted model data routing | PARTLY | Spans hold prompts and customer data (gap 9) |
| Source snapshot semantics | ANSWERED | The snapshot procedure exists; re-snapshot before judging (H §3a item 5, §7.6) |

**BC "Boundaries of what is still unknown"**

| Item | Status | Now |
|---|---|---|
| Starter source and versions | ANSWERED | Kit read: `evaluate.py` implements control 16 only; `submit.sh` mechanics; register template (H §2.4, §10) |
| Deployed resources and permissions | ANSWERED | H §7. RBAC allows more than the VAP permits (H §5.9) |
| Rate-limiter implementation | ANSWERED | Local limits on one replica, so effectively account-wide; the 429 is untested (H §5.5) |
| C9 historical hours and query permissions | ANSWERED | Metrics are readable; Logs Insights and FilterLogEvents are permitted (PVF) |
| Source completeness behaviour | PARTLY | All 1,092 served gateway lines carry ids; the 573 refused or unrouted lines carry none (PCV §4) |
| The exact run id / CID / trace mapping | ANSWERED | P3 (H §5.3) |
| Ledger integrity mechanism and verify endpoint | ANSWERED | None exists (P7) |
| Recovery of our own host and processes | OPEN | — |
| Real model latency, quality and structured output | PARTLY | Latency and tokens per call are measured; structured output is untested |
| The real ServiceNow instance, tables, ACLs and connector | PARTLY | Per Arth's package; unverified by us (H §4.3) |
| Final submission cutoff | OPEN | "10 a.m. Tuesday", probably 15:00 UTC on 2026-10-06; unconfirmed (H §2.5) |
| Organiser rulings on AICT, a diagnostic C9 and export | PARTLY | See below |

**BC "Open requirement conflicts"**

| Item | Status | Now |
|---|---|---|
| AICT / human loop | PARTLY | AICT is live and belongs to L2–L3 (H §2.1). Whether it is "required" still needs an organiser ruling (H §9) |
| C9 metric (guide-native vs diagnostic) | PARTLY | Both candidates are legitimate: the page names latency/errors, and the kit suggests a disposition-match rate (F1). Undecided |
| Export | PARTLY | `submit.sh` mechanics are known; the token leak is a MUST-FIX (K2) |
| Deadline | OPEN | As above |

**Still OPEN with the organisers** (H §9; none answered since):
- who injects the Hostile and Rogue conditions, and when
- what INTEGRITY proof is expected, given that hash chains are out of scope
- whether AICT is required for L2, and whether our runtimes can be "Managed"
- whether the 1 request/second rule is per agent or per account
- the full 30-slide deck and the end time
- whether per-agent identities can be provisioned
- whether the AICT usage query can include `InvokeAgentRuntime`, and whether `validate-logs` can be run for our window
- whether the organisers approved the Global OAuth property change

**Still unchecked on our side** (H §9):
- whether `tmf639.json` holds the ledger token
- which field wins when `modelRef` differs from `dependsOn.models[0]`
- why the `/aws/modaas/gateway` copy lacks the ids

**New open questions this audit adds:**
- which physical store is the one evidence store: the platform audit-store or our own append-only JSONL (P10)
- for the optional C16 check: what "spent so far" covers (the invocation, or the run, via the orchestrating script's payload) and its failure mode (B10)
- where the app runs (R1)
- whether a ToolConfig Cedar edit propagates, and whether it resets approval (B4)
- which policy the PDP applies to a cloned tool name (B4)
- whether our runtime can read the ledger or ServiceNow (A3, B6)
- whether our agents can use the TLS :8443 listener (R2)

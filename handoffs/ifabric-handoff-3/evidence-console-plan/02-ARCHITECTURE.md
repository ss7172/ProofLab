# 02 · Architecture: where the console sits, zero trust, auditability

> **The rule this design is built on:** the console **sees everything and can refuse nothing** (masterclass: "✕ A dashboard: sees everything, can refuse nothing"). It is not an enforcement point. When the console asks for something to be done, a separate enforcement point decides, and **the asking is itself recorded as evidence**.

This file is for the teammate and their coding agent. It defines:
- where every component runs;
- what sits in the execution path;
- how enforcement points invoke the controls;
- who holds which secret;
- how every view on screen can be traced back to an immutable record.

---

## 1. System view

```
                         EXECUTION PATH (agents act here; only EPs may make work wait)
 ┌──────────────────────────────────────────────────────────────────────────────────────────────┐
 │  ifabric-run (orchestrator)  ──EP3 handoff──► customer agent ─► IT agent ─► network agent     │
 │        mints CID + traceparent; passes run budget state; records dispositions                │
 │                                   │ every model call                                         │
 │                          EP2 agent model adapter (in-process, OPTIONAL — see §3)              │
 │                          evaluate(C16 admission: reserve → commit) → ALLOW / ALERT / DENY     │
 │                                   ▼                                                          │
 │                          EP1 modaas-agw (managed: extAuth fail-closed, Cedar PDP, Bedrock     │
 │                          guardrail, ceiling 100 req/min · 2.5M tok/h) ─► Bedrock Nemotron     │
 │                          tools: /mcp/<alias> (governed ToolConfigs)                           │
 │  EP5 kill switch: spec.paused on Model/ToolConfig (out of band, "everything, at once")        │
 └───────────────┬──────────────────────────────────────────────────────────────────────────────┘
                 │ telemetry: emitted by the platform, NEVER judged where it is produced
                 ▼
  gateway pod stdout (run_id; EPHEMERAL) · /aws/modaas/gateway (trace_id, 7 d) · /modaas/evidence (cid,
  action_id, decision, 30 d) · PDP pod logs (2 replicas) · audit-store ledger /records?cid= (JSONL) ·
  AgentCore spans + metrics · X-Ray · CR status/approvals · AICT CloudTrail data events
                 │ pull()  (capture jobs; read-only; never in the agents' path)
 ════════════════▼═════════════════════════  OFF THE PATH, ALWAYS ASYNC  ═══════════════════════════
  ① raw/        immutable captures + .capture.json sidecars (exact command, scope, time, sha256)
  ② facts/      deterministic parse, parser version, quarantine for anything malformed or unbound
  ③ records/    bound evidence: control + threshold.version + run + actor + emitted.at + source
  ④ evaluators  PURE functions of (facts, frozen register version) ───────────┐
       ▲  register.yaml loaded ONCE as a frozen version (never queried in path)│
  ⑤ assessments/  dated verdicts (SATISFIED / BREACHED / INDETERMINATE / NOT_ASSESSED), revisions
  ⑥ findings/  ── emit() ─► prooflab.servicenow.notify() ─► ServiceNow incident (EP4: human queue)
                                   │ callback()/pull(): check() owner response or silence; export()
                                   ├─► Assurance Agent (Nemotron via EP1) writes one validated note
                                   ▼
  ⑦ servicenow/  delivery-log.jsonl (append-only trust anchor) · incidents/ · assurance-agent/ · cases/
  ⑧ answers/ auditor/ runs/   composed by the query engine (the control test tool) — deterministic
  ⑨ pack: README · MANIFEST.json (sha256 of every file) · pack-index.json ─► submit.sh ─► team S3
                 │ read-only
                 ▼
  ProofLab Evidence Console  (loopback · read-only · holds NO cloud/ServiceNow secrets)
     PACK mode: the sealed pack (what the judges read in S3)   LIVE mode: the evidence dir as it grows
     operator requests (P2) ──► control/requests/*.json ──► actuator (separate process, holds creds,
                                allow-listed commands only) ──► evidence/console/actions.jsonl
```

**Read it top to bottom as the masterclass pattern (MC-26):**
- enforcement points produce telemetry;
- a **register** holds versioned thresholds and is out of the path;
- a stateless **evaluator** returns verdicts;
- an **evidence ledger** binds records to control, version and run (here, layers ①–③ plus the delivery log);
- a **control test / query tool** answers "was control X satisfied between T1 and T2?" (⑧ + console).

---

## 2. Components

| # | Component | In the execution path? | Holds secrets? | Writes | Reads | Builder |
|---|---|---|---|---|---|---|
| 1 | Agents (`ifabric-*` CRs → `ifabric_*` runtimes, or the reference agents) | **yes** | gateway key + ledger token, injected by the platform (fail closed if missing) | ledger records | gateway, tools | T |
| 2 | `ifabric-run` orchestrator (replaces `run-reference.sh`) | **yes** (EP3, if built) | AWS session (InvokeAgentRuntime) | `runs/<cid>/run.json` (start, versions, dispositions, admissions summary) | agent responses | T |
| 3 | EP2 adapter inside our agents' `GatewayModel` (optional, §3) | **yes**: the only component allowed to make a model call wait, and only for one question | none extra | one decision record per call | the run's budget state passed in by the orchestrator; register snapshot baked in at build | T |
| 4 | Capture jobs (`prooflab capture …`) | no (`pull`) | AWS read creds (participant role), kubeconfig | `raw/**` | platform surfaces | T |
| 5 | Normalizer / binder | no | none | `facts/**`, `records/**` | `raw/**` | T |
| 6 | Evaluators / control tests (`prooflab/evaluators/*`) | no (pure) | none | `assessments/**` | facts + frozen register | T |
| 7 | Publisher (finding → ServiceNow) + Assurance Agent orchestrator | no (`emit`, `callback`, `pull`) | ServiceNow OAuth client, gateway key | `findings/`, `servicenow/**` | assessments, incidents | T (wiring) + A (package) |
| 8 | Query engine (`prooflab controltest`, `auditor`, `lane`) | no | none | `answers/`, `auditor/`, `runs/<cid>/lane` | the pack | T / C |
| 9 | Pack builder (`prooflab pack index · manifest · verify · submit`) | no | AWS write creds for S3 submit only | `MANIFEST.json`, `pack-index.json`, S3 objects | the pack | T / C |
| 10 | **Evidence Console** (`prooflab console`) | **no, never** | **none** | nothing in PACK mode; request files only in LIVE operator mode | the pack (read-only) | C |
| 11 | Actuator (P2, `prooflab actuator`) | no (deferred action) | the creds needed for its allow-listed commands | `evidence/console/actions.jsonl` | `control/requests/*.json` | C |

**Why the console holds no secrets:** in this platform the cockpit leaked the ledger write token through a read-only YAML view (VF #24), and the participant role can read the AICT connector key. Our console reads only files that are already in the pack, and the pack is redacted at capture (`04-LOGS-TO-EVIDENCE.md` §3). Nothing secret can therefore reach the browser.

---

## 3. Enforcement points, stated honestly

A slide-25 lesson: some EPs "cannot be modified, some answer late, some have no request path at all". The console shows the table below **from `pack-index.json.enforcement_points[]`**, so every row's status is exactly what the teammate builds, and nothing is asserted.

| EP | What | Can refuse? | Transport into our design | Status options | Notes from verified facts |
|---|---|---|---|---|---|
| **EP1** | Shared model gateway `modaas-agw` (managed) | yes (auth, Cedar, guardrail, ceiling, pause), but **not** per-run budget | `pull()`: "Managed gateway: no code of yours in it, read its log" (MC-25) | BUILT (platform) | Gateway stdout per-call line = **C16 figure of record**; it carries `modaas.run_id` = baggage CID, **only on ephemeral pod stdout**. A guardrail block is HTTP 200, `content_filter`, 0 tokens, and the PDP logs it as ALLOW. A pause 404 line has no run id. |
| **EP2** | Agent model adapter (in-process interceptor in our rebuilt agents) | **yes**: it can refuse the next model call | `evaluate()`, sync, in path (the "sidecar / SDK" transport, MC-25) | BUILT · PLANNED · NOT_BUILT | **Option (a)** in the box below. It covers only the agents we rebuild. A new image means a new version, so re-approval and baseline consequences follow. |
| **EP3** | Sub-agent handoff in `ifabric-run` (before invoking the next agent) | yes: it can stop the run between agents | `evaluate()` | BUILT · PLANNED · NOT_BUILT | Cheapest real EP: the orchestrator is our code, and no image rebuild is needed |
| **EP4** | Human approval queue (ServiceNow incident on an S3 escalation) | **only if something waits on the human**. A notify-only incident refuses nothing | `pull()` only: `check` polls the incident's last update (the owner's reply is never pushed to us; gap A8) | BUILT_WAITING · ALERT_ONLY | Claim it as an EP **only** if the escalated change is held until the owner decides (`02` §3.1). Otherwise label it "human-loop alerting", which is still required (L2/L3). **Naming:** the ServiceNow pitch and `deliverables/architecture/servicenow-section.md` call this the second enforcement point, "EP2"; in this table EP2 is the C16 agent-adapter admission |
| **EP5** | Kill switch (`spec.paused` on a ModelConfig/ToolConfig) | yes, "everything, at once" | out of band | EVIDENCED · NOT_RUN | Measured: model pause effective in ≤2 s (super-120b) to 33–41 s (nano-9b), still serving meanwhile; tool pause ~1–7 s; resume 24–35 s; stale pause conditions remain. **Record requested vs effective times.** Pausing a model affects the whole account |
| **EP6** | Tool call via ToolConfig `access.cedarPolicy` | yes for the tool, but **for every agent**: one shared identity (`ServiceIdentity::"bootstrap-key"`) | `evaluate()` (PDP) | BUILT · NOT_BUILT | The team Cedar ConfigMap is **inert** (it is never consulted). Cedar sees neither the calling agent nor tokens. Cross-tool use is **detectable** (`route_alias` in `/modaas/evidence`) but not deniable per agent |

**Second-EP options**. The teammate picks one, and the console renders whichever is true:
- **(a) In-process admission in our agents' model adapter**, calling the **same** `prooflab.evaluators.c16.admit()` that the post-run test uses. It genuinely refuses. Cost: the agents must be rebuilt (CodeBuild → AgentConfig → owner approval), and that is a new version (a C9/C16 "treatment", so freeze baselines after it).
- **(b) Handoff admission in `ifabric-run` (EP3).** It refuses between agents, not mid-agent. No image change is needed. It is the cheapest genuine EP and pairs with (a).
- **(c) ToolConfig `access.cedarPolicy` deny.** A real deny, but a cluster write that hits all agents through the shared identity. Untested whether it resets approval.
- **(d) No EP2 claim.** ServiceNow is labelled `callback()` alerting, and C16 is labelled **POST-RUN**. Honest, and scores under "honesty".

"**The same architecture, moved, nothing rewritten**" is shown by listing, per EP, `changed_adapter` (for example `agents/common/gateway_model.py`) and `unchanged_core` (for example `prooflab/evaluators/c16.py`, `prooflab/servicenow/finding.py`). The console prints both lists.

### 3.1 What makes EP4 a real enforcement point (if the teammate wants the claim)
Every EP does five things: **ask, wait, act, record**, (seal) (MC-23). The S3 restricted-change scenario already ends in `escalate`. For EP4 to be real, the proposed change must be **held**:
- **ask:** the orchestrator emits an ESC finding (the change is parked in `runs/<cid>/held-actions.json`);
- **wait:** nothing executes it;
- **act:** the owner's response is pulled (`check`), and APPROVE or REJECT is recorded;
- **record:** the finding, the delivery log, and the held-action file updated with the decision and its time.

The agents have no real change tool, so "executing" an approved change is a recorded no-op. Say exactly that in the gap list.

---

## 4. Transports and control modes

| Transport (MC-26) | Where we use it |
|---|---|
| `evaluate()`: sync, in path, can refuse | EP2 admission (C16), EP3 handoff admission, EP6 PDP (platform) |
| `emit()`: async, records only | evaluator → finding → `notify()`; EP2 decision records; orchestrator run records |
| `callback()`: deferred verdict | ServiceNow owner response (human), Assurance Agent result, actuator results (P2) |
| `pull()`: scheduled, off path | capture jobs (gateway stdout, CloudWatch, PDP, ledger, X-Ray), C9 hourly windows, AICT import, `check()` |

| Mode (MC-20) | Our example | Same record format? |
|---|---|---|
| Static | AI policy / the register document itself (approved by the owner) | yes: `assessment` of kind `static` (optional) |
| Scheduled | AICT inventory every 15 min; MANIFEST verification on console start | yes |
| Event-driven | **C7** event recording per run | yes |
| In-transaction | **C16** admission (EP2/EP3) | yes: decision records are evidence records with `decision` |
| Continuous | **C9** closed-hour windows vs frozen baseline, alert per crossing | yes |

**Evaluator vs tester** (MC-24) is kept as two functions per control:
- `admit()` judges one action for the EP, in milliseconds;
- `test()` judges the control over a run or window for the judge.

Both are pure, and both read the same frozen register version. The console labels them separately.

---

## 5. The console's three modes

| Mode | Who | Data | Actions | When |
|---|---|---|---|---|
| **PACK** (default) | Judges, auditors, us during Q&A | The sealed Evidence Pack, byte-identical to the S3 submission (MANIFEST verified on load) | **None rendered**: no buttons, no forms | The 2-minute test, the six questions, the whole Q&A |
| **LIVE** (P1 real-time monitor, read-only; P2 with actions) | Operators (teammate, Arth) | The evidence directory + `live/events.jsonl` as `prooflab watch` writes them (real-time: ≤ 5 s per call/decision) | P2 only: requests to the actuator (§5.1) | Building, rehearsing, the L1–L3 walkthrough, the live continuous-compliance beat |
| **VIEWER** (P2) | A stranger, years later | The `evidence/viewer/` static copy inside the pack (`file://`, no server) | None | After judging; proves the stranger test |

### 5.1 How an operator action works (P2): ask, record, never decide
1. **Ask.** The operator clicks, for example, "Run control test C16 on FM-B" or "Seal & submit pack". The console requires:
   - an operator session (§6);
   - an intent confirmation (type the target id);
   - a reason.

   It then writes **only** a request file `control/requests/<uuid>.json` (schema `ifabric.console-action/v1`, state `REQUESTED`).
2. **Decide.** The actuator, a separate OS process started in the operator's authenticated shell, picks it up. It validates against an **allow-list of action kinds with fixed argument schemas**, and runs the command with a fixed argv (no shell, no free text). Kinds that affect shared systems (kill switch, launching a run) are refused unless a second operator approves the request within 120 s (**dual control**; P2+).
3. **Record.** Every state transition is appended to `evidence/console/actions.jsonl`:
   - REQUESTED → ACCEPTED/REFUSED → STARTED → SUCCEEDED/FAILED;
   - with `requested_at`, `effective_at`, `finished_at`, the exact argv, the exit code and output references.

   This is the playbook's "requested vs effective time" applied to the console itself.

The judges' vocabulary for this: "*the console is a deferred-action requester; the actuator is the enforcement point for operator actions; the request, the decision and the outcome are evidence.*"

---

## 6. Zero trust, applied

Zero trust here means **no implicit trust from network location, process or person**: every request is authenticated and authorized on its own, every data source is verified before display, and every secret lives in exactly one process. The table maps the NIST SP 800-207 tenets to concrete controls.

| 800-207 tenet | Concrete control in this design |
|---|---|
| All data sources and services are resources | The pack, each surface capture, the console API, the actuator queue and S3 are each a resource with an owner and an access rule (§6.1) |
| All communication secured regardless of location | Loopback is not trusted. The console requires a session token even on 127.0.0.1, checks the `Host` header (anti DNS-rebinding), checks `Origin` on every non-GET, and sends strict CSP. Agents' plain-HTTP key transport is recorded as a platform gap, not hidden |
| Per-session access | The startup prints a one-time URL token, exchanged for an `HttpOnly; SameSite=Strict` session cookie (8 h max). Operator scope requires a server flag **and** step-up confirmation per action |
| Dynamic policy | Role (viewer / operator) × mode (PACK / LIVE) × integrity state. If MANIFEST verification fails, the console shows **red "PACK MODIFIED"** and labels every answer UNVERIFIED |
| Monitor asset integrity | MANIFEST verified on start and every 5 min in LIVE mode; any changed, missing or unlisted file is listed. The adversarial case "tampered evidence file" is demonstrated with exactly this |
| Strict authentication/authorization before access | The file resolver serves **only** paths listed in `pack-index.json`/`MANIFEST.json`, normalized under the pack root. No symlinks, no `..`, size caps |
| Collect telemetry to improve posture | The console writes a session ledger: every query, its `answer_id` and elapsed time, plus every operator request |

### 6.1 Trust boundaries

| Boundary | Threat | Controls |
|---|---|---|
| **TB1** Browser ↔ console | XSS from evidence text (incident notes, prompts, agent output are attacker-controllable); CSRF; DNS rebinding; clickjacking | `textContent` only (no `innerHTML`); CSP `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`; Host allow-list; CSRF token + Origin check on POST; `X-Content-Type-Options: nosniff`; `Referrer-Policy: no-referrer`; `Cross-Origin-Opener-Policy: same-origin`; `Cross-Origin-Resource-Policy: same-origin`; `Permissions-Policy` all off; links rendered only for `https:` |
| **TB2** Console ↔ evidence files | Path traversal; reading secrets; tampered files shown as truth | Allow-listed paths; read-only opens; MANIFEST verification; redaction already applied at capture |
| **TB3** Console ↔ actuator (P2) | Command injection; privilege escalation through the UI | File-queue requests validated against a JSON schema; allow-listed kinds; fixed argv; no shell; actuator runs as the operator with only the needed creds; dual control for shared-impact kinds; every transition recorded |
| **TB4** Evaluator loop / actuator ↔ AWS, ServiceNow, gateway | Secret leakage into evidence; over-privileged writes; injected text treated as instructions | Secrets only in that process's environment (never files, never logs); OAuth `itil` integration user only; `sys_created_by` filter (never touch other teams' incidents); evidence text always treated as data; capture-time redaction |
| **TB5** Pack ↔ S3 ↔ judges | Pack altered after hand-in; presigned URL leakage | MANIFEST sha256 list; readback (head-object + download + verify); key/ETag/version recorded in README §10; presigned URLs never stored |

### 6.2 Who holds which secret

| Secret | Held by | Never in |
|---|---|---|
| ServiceNow OAuth client id/secret | Evaluator loop / publisher process env (and Arth's or Sree's password manager) | Browser, pack, repo, screenshots, console process |
| Gateway API key (`OPENAI_API_KEY` / MCP token) | Agents (platform-injected), Assurance Agent orchestrator env | Console, pack (redact from CR exports), logs |
| Ledger `AUDIT_WRITE_TOKEN` | Agents (platform-injected) | Pack: **AgentConfig specs and `get-agent-runtime` output contain it literally** (VF #24), so redact at capture |
| AWS session keys | Capture jobs, actuator, `submit.sh` shell | Console, pack |
| IdeUrl / CockpitUrl bearer links | Nobody's files | Anywhere (they are bearer credentials) |

### 6.3 Data minimization
- AgentCore `chat` span events contain the **system prompt and full context, including customer records** (VF; gap 9). Captures **drop `events[].attributes.content`**. Ids, timestamps and token counts are kept, and the drop is recorded in the redaction log.
- **Never** show model reasoning (think-tags). The Assurance Agent stores only hashes of raw responses.
- Synthetic data only; no real customer data (PB §3.13).

---

## 7. Auditability, built in

| Property | How |
|---|---|
| **Immutable layers** | raw → facts → records → assessments: no layer edits a previous layer's output ("telemetry never judges; the ledger never interprets"). A correction is a new revision file (`…r2.json`) with `supersedes`. A "corrected total replaces the earlier one; never add both" |
| **Provenance on everything** | `provenance ∈ {ASSESSED, EXPLORATORY, WIRING_TEST, SYNTHETIC}` on every run, record, assessment and answer. The console filters and labels by it, and **never mixes** EXPLORATORY or WIRING_TEST into verdicts. SYNTHETIC never enters the pack |
| **Date before test** | `register.frozen_at` and the owner approval time precede every ASSESSED run's start. Every answer recomputes this check (`rule.date_before_scope`) |
| **Deterministic answers** | `answer_id = sha256(canonical JSON of the answer without answered_at/elapsed_ms/source.mode)`. Re-running the same query on the same pack gives the same `answer_id`, so any answer shown to a judge is reproducible from S3 |
| **Session ledger** | Every query asked in the console (text, parsed query, `answer_id`, elapsed, MANIFEST sha) is appended to `session/queries.jsonl`. It is outside the sealed pack and labelled as such |
| **Operator actions** | `evidence/console/actions.jsonl` (P2), append-only and fsync'd, same pattern as `delivery_log.py` |
| **Same-ID chain** | CID ↔ run alias ↔ trace id ↔ action ids ↔ `finding_id` = ServiceNow `correlation_id` ↔ Assurance Agent note "Finding ID" ↔ answer. The console highlights every occurrence of a hovered id |
| **Clock discipline** | All times are UTC ISO-8601 `…Z`, and every timestamp names its clock (`gateway`, `ledger`, `cloudwatch`, `orchestrator`, `servicenow-display`). Gaps are subtracted only within one clock; cross-clock deltas are flagged, not computed |
| **Completeness statements** | Every assessment carries expected / observed / matched / missing / unmeasurable counts, with the source of the expected population |
| **Retention** | "Kept for 7 years from submission" (`evidence/README.md` §2) |
| **Integrity without crypto theatre** | MANIFEST sha256 + raw captures never edited + cross-surface corroboration (the same call seen on gateway stdout, the durable gateway log, `/modaas/evidence` and X-Ray) + S3 readback. **No signatures, hash chains or Merkle trees** (out of scope, MC-37). The audit-store has **no verify route** (VF), so integrity is never claimed from the ledger alone |

---

## 8. Failure modes (the console never makes anything worse)

| Failure | Behaviour |
|---|---|
| ServiceNow unreachable | Case snapshots show `servicenow.status: unreachable` (an evidence gap), and agents are unaffected (ServiceNow is never in the agent path) |
| Gateway pod restarts before capture | Run ids on stdout are lost. Capture C16 data **immediately after every run** (`prooflab capture gateway --cid …`). The durable fallback is the `/aws/modaas/gateway` trace_id ↔ `/modaas/evidence` correlation_id join. Without either, the verdict is INDETERMINATE |
| A CloudWatch hour is missing | UNKNOWN window → monitoring-gap finding; never "healthy" |
| MANIFEST mismatch | Red banner; answers labelled UNVERIFIED; the list of changed files is shown |
| Console crashes | Nothing else depends on it. The CLI `controltest` answers the same questions from the same pack |
| Wi-Fi or AWS slow during judging | PACK mode is fully offline. The recorded backup demo covers L1 |

---

## 9. Corrections to the playbook (the teammate verified these live; build on these)

| Playbook says | Verified reality (teammate, 2026-10-05) | Design consequence |
|---|---|---|
| "Traces have no durable exporter; Cockpit Trace is empty" (§1.7, §2, §3.11 gap) | The collector **exports to X-Ray**; X-Ray holds gateway traces with `modaas.action_id` | X-Ray is a RECONSTRUCT and corroboration surface. **Do not** list "no durable exporter" as a gap |
| Hostile/Rogue "unauthorized tool → Cedar deny"; "restrict toolName in the team Cedar ConfigMap" | Undeclared tool calls are **ALLOWED**; the team ConfigMap is never consulted; there is one shared principal | Plan these tests as **"what broke"** findings (adversarial bonus) plus detection by `route_alias`; the live lever is ToolConfig `access.cedarPolicy` |
| "Tampered ledger record → ledger verification fails"; "capture the ledger's own verification output" | The audit-store has **no verify route** and no hash chain; a forged write is refused (401) only without the token, and the token is readable in specs | INTEGRITY = cross-surface corroboration + MANIFEST + S3 readback; the forged-write case is DEFENDED without the token and **BROKE** with the leaked token |
| "S2 fails 7/10; keep S1 and S3 passing" | S1 6/8, S2 5/10, S3 8/10: **all fail by construction** (no guardrail verdict in the ledger, negotiation stub) | `score-run.py` is a **diagnostic**; the console shows dispositions vs scenario expectations, not a "PASS" badge |
| "Use the twin to produce pass/breach runs on demand" | The network-twin Lambda reads its own packaged data; the recipes are broken; S2 has no twin site | Named runs come from scenario choice plus enforcement mode, not the twin; C7's expected events come from scenario specs |
| Kill switch "~15 s to stop, ~50 s to resume" | ≤2 s to 41 s, varying by model; tools ~1–7 s; resume 24–35 s | Record requested vs effective times; never quote 15 s |
| "Preserve traceparent or run ids fragment" | `modaas.run_id` = **baggage CID**; it lives only on **ephemeral** gateway stdout; ledger trace_ids ≠ the run trace | Propagate the CID in baggage; **capture stdout right after each run**; durable join = `trace_id → /modaas/evidence.correlation_id` |
| C9 = Latency **Average** + Errors Sum | The S2 runaway showed Errors = 0 and was visible only in hourly **Maximum** latency (278 s) | The C9 metric is a register decision, to be taken before baseline hours (Maximum + Errors recommended for visibility); the console renders whatever the register declares |
| `ifabric_…` names for every CR | Kubernetes names cannot contain `_`; CR `ifabric-x` → runtime `ifabric_x` | Name CRs `ifabric-*`; AICT then shows `ifabric_*` |
| "The gateway decides budget and can halt a run" | It counts tokens per call; there is **no per-run budget or halt**; only account ceilings and pause | Inline C16 is **our** build (EP2/EP3) or it is labelled POST-RUN |
| L2 "show AICT Monitor traces" | AICT usage counter = 0 (`InvokeAgent` filter vs our traffic); Monitor shows "Managed" agents only; discovery = AgentCore runtimes + gateways | The AICT line shows **inventory + import time**; Monitor is a gap; `/aws/bedrock/aict-invocations` (AWS-written CloudTrail data events) is an independent WHO source |
| ServiceNow human queue = second EP | A notify-only incident cannot refuse | EP4 counts only if the change is held (§3.1); otherwise label it `callback()` alerting |
| APPROVED = export `.status.governance.approvals` | Approvals are free-text annotations with empty signatures; **a model swap needed no re-approval**; tools actually called ≠ tools declared | The APPROVED card lists approvals for **every asset actually called** and flags approvals **older than the running generation** |
| AUTHORIZED = PDP decision lines | Guardrail blocks and pause refusals are logged **ALLOW**; there is no principal on PDP lines (it is in `/modaas/evidence`, always `bootstrap-key`) | Join each PDP decision to its gateway line to show served / blocked / refused; WHO = PARTIAL with the identity gap |
| C16 worked example 10,000 tokens | Our runs: S1 24.8K–50.2K, S3 ~37.8K, S2 runaway 2.0M (174 model calls); ~4.2K tokens per call regardless of model | The cap **must** be derived from our measured exploratory runs and the risk framing (the judge's "risk matrix" hint), then frozen; **never** copy 10,000 / 2,000 / 900 |

---

## 10. Deployment topology (hackathon reality)

| Process | Where | Port / path |
|---|---|---|
| Agents, gateway, PDP, ledger | AWS account (EKS + AgentCore) | platform |
| Capture jobs, normalizer, evaluators, publisher, Assurance Agent orchestrator (`prooflab watch`) | The teammate's authenticated shell (`workshop-local/shell` on the laptop, or the workshop IDE) | none (files) |
| Evidence Console | Presenter's laptop | `127.0.0.1:8787` only. PACK mode reads `evidence/` (synced from S3 or local) |
| Actuator (P2) | Operator's authenticated shell | none (file queue) |
| Judges | The team S3 bucket (`team-evidence-613052889143`) plus our screen during the 15-minute slot | — |

No public endpoints (platform rule). No tunnels. The console never binds a non-loopback interface (same rule as `prooflab/servicenow/serve.py`).

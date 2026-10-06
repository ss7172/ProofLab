# 11b · Phase 2 changelog: feasibility, build and schedule (Fixer B)

Written 2026-10-05, from 23:40 UTC, by Fixer B (a subagent). It applies the infrastructure-vetting results to the sections of `architecture/ARCHITECTURE.md` that Fixer B owns (§6, §7, §8, §9, §12, §13, §14, §15) and to `architecture/decisions.md`. Fixer A edited §2–§5, §10, §11 and the one-page files at the same time; nothing here touches those.

**Inputs, all read in full:** `work/05-feasibility-agents-runtime.md`, `work/06-feasibility-evidence-data.md`, `work/07-feasibility-governance-security.md`, `work/08-feasibility-servicenow-delivery.md`; from `work/04-adversarial-review.md` E-09 and E-10; from `work/04b-independent-review.md` A8, B9, B10, B12, B14 and the unmet requirements R-J-45, R-P-03(e), R-P-10, R-J-56. Also the coordinator's mid-task note on handoff-3 (a 4th agent). No live check was made; no git, cluster or AWS write.

**Method.** Surgical edits: each Edit anchored on a row key or a unique phrase, re-read immediately before. The §12.1 critical-path table and the §12.3 budget table were replaced in chunks, because their content changed throughout.

---

## §7 · Agents and the orchestrating script

| Change | Source |
|---|---|
| **Build path (AR-03 BLOCKED as designed):** one self-contained file per agent, `agents/ifabric-<role>/ifabric-<role>.py`, written by `tools/bundle_agent.py` with each vendored module embedded as its exact bytes and registered in `sys.modules`; `evaluator.sha256` over the literal (the CI sha256-equality test holds). The 24,049-char gzip+base64 budget (25,600 − 1,551) stated; CI size gate ≤ 24,000; lean runtime subset; a local arm64 Docker run (`/ping`, `/invocations`) before any CodeBuild; fallback `--buildspec-override` | 05 AR-03 |
| **Tag trap:** never a file named `agent.py`; always `IMAGE_TAG=ifabric-<role>-<git sha>` (unique per build) and a per-agent `URI_FILE`; a bare `agent.py` overwrites `reference-agent-v5-agentcore` | 05 AR-05 |
| **The build and approval path per agent:** bundle → gate → local Docker → CodeBuild (44–47 s) → `tools/make_ifabric_agents.py` (`_agent_cr` with `tool_alias`, `env_extra`; string env values; ledger pair through discovery; never `approve=True`) → apply → Sree annotates (self-asserted, gap 5) → READY about 40 s later → smoke | 05 AR-02, AR-04, AR-07, AR-08 |
| Python: Strands tests in a 3.12 venv with exact pins; `prooflab/` stays stdlib 3.9+ | 05 AR-29 |
| Tools bullet: the Cedar demo edits an existing ToolConfig (D15 (a)); no tool of ours unless D15 (b) | Lead brief; 07 GS-03 |
| Stage A now names the safety ceiling and the duplicate-invocation guard | E-10; 05 AR-18 |
| **The 4th agent line** (iFabric Assurance agent, handoff-3, pending integration; AR-03 applies) | Coordinator's note |
| **J2 as JSON in the text answer**, parsed and validated by code with one re-ask; forced structured output only after spike S-5; never `Agent.structured_output()` (bypasses the hook) | 05 AR-31, AR-10 traps 2–3 |
| Emission fix list: the action-id hook via `GatewayModel._get_client` (per-request client); OC-3 fallbacks; usage from `message["metadata"]["usage"]`, 0/0 = UNKNOWN; raw `finish_reason` via `format_chunk`; own-cancel flag; trace id from the current OTel span | 05 AR-10, AR-12, AR-13, AR-19 |
| `max_retries=0` rationale (OpenAI's 2 retries sit below the hook; Strands' 429 retries re-enter it), `openai` pinned | 05 AR-11 |
| **Agent-side duplicate-invocation guard**, labelled an idempotency precondition (not a control question; §2.3 keeps one waiting row) | 05 AR-18 |
| Span content: `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_unredacted_attributes=` at first apply (OC-16 closed from source) | 05 AR-25 |
| Version pinning: env patch = new generation, no re-approval (OC-12); silent stale pin on a rejected patch; the pre-assessed-run checks (`lastUpdatedAt`, READY, echoed pin) | 05 AR-15 |
| §7.2: **exactly one invocation per handoff**: `AWS_MAX_ATTEMPTS=1`, `AWS_RETRY_MODE=standard`, `--cli-read-timeout 900`, TIMEOUT recorded, never re-invoked | 05 AR-18 |
| §7.2: `--baggage` on every invoke with the smoke assertion; a minted `runtimeSessionId` recorded in `handoff.sent` | 06 A6; 05 AR-20, AR-23 |
| §7.2 preflight: credential expiry, ≤ 3 S2-class runs per clock hour, **EP-0** with filtered reads, the approved generation from `ApprovalRecorded.observedGeneration`, and `spec.paused` (a paused AgentConfig doesn't stop direct invokes) | 05 AR-30; 07 GS-14, GS-22; 08 LB-01 |
| §7.2 "What it never does" reworded: nothing inside a run waits; EP-0 may decline to start an assessed run. (04b A3, touched only here because GS-14 needs the preflight step) | 04b A3; 07 GS-14 |
| §7.2 credentials: the token read through a subprocess pipe, never argv/env/`-v 8`/disk; **spike S-1** with the zero-write `[]` probe, then port-forward, IDE, one-shot pod | 06 C2, C3, S1; 05 AR-22 |

## §6 · Security and guardrails

| Change | Source |
|---|---|
| Heading now "(D10, D15)". New opening block: **the four guardrail layers** (the fixed gateway guardrail, observed; in-agent rails; Cedar edits on EXISTING ToolConfigs, every caller, captain's OK; the C16 guard with its safety ceiling always on) | Lead brief; 07 |
| **"Not available" list:** no guardrail create/update (explicit IAM deny) and no per-call choice (fixed per model alias: super-120b `yclc11u8sb3j` v2, PROMPT_ATTACK input HIGH only); no stricter Cedar through an adopt-mode ToolConfig; no new Lambda or AgentCore-gateway target (our rule); no per-agent Cedar; no TLS (self-signed placeholder, no MCP TLS listener); **an AgentConfig pause is a record, not a stop** | 07 GS-03, GS-04, GS-05, GS-14, GS-15, GS-16, GS-25, GS-27 |
| **Link to the separate guardrails design** in `architecture/guardrails/` (not yet present when edited) | Lead brief |
| §6.1 matrix: EP-0 row adds T-PRE-02 (paused AgentConfig → no run) and the live stale-approval fact; EP-1 row's tests list the Strands traps and the low-cap halt proof (LB-04); **new row "Our runtime, invocation"** (the duplicate-invocation guard, T-DUP-01); EP-3/EP-4 wording (D15; JSON-in-text) | 07 GS-14, GS-22; 05 AR-10–12, AR-18; 08 LB-04 |
| EP-6 row: configure a forbid in an **existing** ToolConfig (D15 (a)); SP-1 as its test | Lead brief; 07 SP-1 |
| EP-7 row: the guardrail's real content; not editable, not selectable; BLOCKED is an **inference** from the span (200 + 0/0 + cost 0), corroborated by EP-1's record; ADV-H-01 at P0 after N1 | 07 GS-15, GS-16; 06 A5; 04 E-09 |
| EP-8 row: AgentConfig pause = record; ADV-R-08 becomes the **model pause** (P2) | 07 GS-14; 04 E-09 |
| EP-10 row: never the env map or the two configuration annotations; T-REDACT-01. EP-11: `aict-invocations` ≥ 10 min after, `eventTime` = the end of the call. EP-12: CodeSha256 readable (OC-13 closed), never `GetFunction`, CloudTrail code updates; status now "Observe" | 06 B6, B9, D4; 07 GS-23 |
| **OTel collector row** given a test (T-OTEL-01) and gap entries; **new "Transport (TLS)" row** (gap 9) | 04b R-P-10; 06 A3, A6, B4; 07 GS-25 |
| Pack pipeline row: the scan covers the staged tree and the readback, the three CR token paths and the ServiceNow values | 06 D4; 08 SN-02 |
| **§6.2 rewritten in place as "Cedar through an existing ToolConfig (D15 (a))":** the lever with the projection facts; D15 (a) recommended, D15 (b) only if the rule is relaxed (its least invasive form is the custom MCP tool, GS-01/02/26); **the adopt-mode alternative removed (GS-03)**; the rule narrow and keyed on a test value; the Cedar request shape (closes OC-7's paths); guard every attribute with `has`; never `policyId`; limits incl. every caller and the captain's OK; approval kept (grandfather), no Cedar text ever edited live; the two-surface "rule is live" check; lifecycle with SP-1 before the agents' freeze, the allowed + forbidden calls, the restore after the final snapshot | 07 GS-01, GS-03, GS-07–GS-12, GS-26, SP-1; 02 R-P-12 |
| §6.3: per-agent Cedar, generation 2 on a generation-1 approval, the TLS placeholder, the guardrail's content, the AgentConfig pause | 07 GS-14–GS-16, GS-22, GS-25, GS-27 |
| §6.4: ADV-H-01 → **P0, straight after N1**; ADV-H-02 live only under D15 (b); ADV-R-01 → D15 (a), P2; **ADV-R-08 → the model pause, Required, P2**, with the platform-asset precautions (user's explicit OK, a declared Rogue window, no other run live); the R-J-36/37 lines and a scheduling line (Hostile first, then Rogue, in declared windows) | 04 E-09; PV row 6 |

**Flag for the lead (D15).** 07 rated the custom `ifabric-` MCP tool (GS-01/02) SUPPORTED, and it was §6.2's earlier preference. The lead's brief lists only GS-04/05 (Lambda and AgentCore-gateway targets) as rule-breaking, which the custom tool is not. Following the brief's two options, the custom tool is filed under D15 (b) as its least invasive form, because the tool operator writes a new backend and route on the shared gateway and leaves leftovers we can't delete (GS-26). Please confirm that reading; if the custom tool is acceptable under the current rules, it becomes a third option.

## §8 · Where things run, and credentials

| Change | Source |
|---|---|
| Intro: nothing in `components` but our agents (the trio; the handoff-3 Assurance agent once integrated) and a custom tool only under D15 (b); **the laptop is the hub** (the only place with Logs Insights, the ServiceNow credentials, the delivery log and the live lane together) | 08 SN-12; lead brief |
| Laptop row: Logs Insights is the participant role's only; the 12 h credentials and their expiry; the ServiceNow file (mode 600, absolute delivery-log path) needed by about 03:30; fleet briefs forbid reading it | 06 A1; 08 SN-02, TC-08, TC-09 |
| IDE row: **no Logs Insights**; `EvidenceVersionRead`; PutObject for the version export. New row: the ServiceNow terminal off the laptop is not the default (every notify would wait for Arth) | 03 F1, F2; 08 PY-03, SN-12 |
| **Credential refresh:** issued for 12 h, expire **2026-10-06T06:29:19Z**; exactly one refresh in **03:30–06:29 UTC** (expiry 15:30–18:29); why not earlier (before 03:00 expires before 15:00); alarms 03:30 and 05:45; what stops when they lapse | 08 OP-01, OP-02 |
| **ServiceNow credentials by about 03:30 UTC**: the env file, `selftest` before each notify batch, Arth's instance checks, the exact-value scan, scratch log for dry runs (bug (a)) | 08 SN-02, SN-03, SN-06 |
| **Separation of duties:** the roles (Sree accountable + operations + owner; Arth assurance, reviewing each T2 before approval; GRC vacant); approvals are Sree's own act | 02 R-D-02; 08 HL-01, HL-04 |
| **Overnight availability:** batched OKs, `+yolo` (captain's call), `caffeinate -dimsu`, AC, lid open, token re-extract after a reboot, live lane separate from the fleet | 08 HL-03, OP-03, TC-07, TC-09 |
| Pull cadence: **per-CID ledger exports**, a full GET only between runs and at the final refresh, `tail` ≥ 3 s (single-threaded 256Mi server); **`aict-invocations` ≥ 10 min after** (19–328 s late; `eventTime` = the end); the metric delay measured on the first smoke run; the AICT discovery trail pull (AWS half of the AICT proof) | 06 B6, C5; 05 AR-20, AR-21; 08 AI-06 |

## §9 · The Evidence Pack, integrity and redaction

| Change | Source |
|---|---|
| §9.1 layout: `store/records.jsonl` from **per-CID exports** plus one full GET at the final refresh; `raw/aict-discovery/`; **`kit-crosscheck/<CID>/gateway-log.json`**; **`reviews/`** (two rehearsal records and the run-of-show for R-J-45; `link-handcheck.md` for R-P-03 (e); `mentor-review.md` for R-J-56; `gates.jsonl` for R-D-05) | 06 C5; 08 AI-06; 04b B14 and the unmet requirements |
| **`run-ids.txt`: the CID first**, then control, role, window, version, mode, condition. Worded as the kit's note (a comment in `submit.sh`, which only copies the file), not as a parse constraint | 04b B14 |
| **The kit cross-check scoped:** `evaluate.py 16` sums every record for the run with no listener filter and no dedupe, against the default tier's cap; so the file holds model-call spans only (`listener = llm`), deduped by action id, and it runs only for default-tier runs | 04b B14; kit `evaluate.py` |
| The bucket: versioned, shared with the organisers (four `facilitator/` objects); we write only under `ifabric/` and `submissions/` and never touch others' objects | 03 F1; 06 D5 |
| §9.2: the `aict-invocations` corroboration pulled ≥ 10 min after, joined by ARN + `eventTime` (the end of the call) + `userIdentity`; **the F11 conflict left open** (05 AR-20 saw `runtimeSessionId` + CID in `responseElements`; 06 B6 saw no session id) with a pointer to `work/10-f11-resolution.md`; the runtime-log witness verified (OC-9), never counted as invocations | 06 B6, B10; 05 AR-20, AR-24 |
| §9.2 times: `head-object` VersionId/LastModified/ETag (+ AWS SHA-256 with `--checksum-algorithm SHA256`); **versioned, no Object Lock, 7-day noncurrent expiry**, so write-once is a convention; the fail-safe argument (an overwrite only moves LastModified later → INDETERMINATE); live verification only before teardown | 06 D2; 07 GS-20 |
| **§9.3 redaction: three paths, 15 copies today** (`spec.awsAgentCore.environmentVariables`, `last-applied-configuration`, `kopf.zalando.org/last-handled-configuration`); `cr_status.py` drops all three on every CR kind; `tmf639.json` clean (OC-14 closed); the scan covers the laptop's logs and spool; the pre-push scan lacks the ServiceNow values until they arrive; `get-agent-runtime` and `ListFunctions` return env | 06 B9, C3, D4; 05 AR-30; 07 GS-22; 08 TC-08 |

## Late inputs folded in (09, 10, `guardrails/02`, and Fixer A's cross-dependencies)

`work/09-twin-fix-check.md`, `work/10-f11-resolution.md`, `guardrails/01-…` and `guardrails/02-…` appeared during this pass, and Fixer A's `11a` changelog named cross-dependencies on Fixer B's sections. Applied:

| Change | Where | Source |
|---|---|---|
| **F11 resolved: AR-20 holds.** `InvokeAgentRuntime` records carry the caller-sent `runtimeSessionId` (`<CID>-<32 hex>`), `traceParent` and baggage CID in `responseElements` (28/28), so they join exactly; `requestParameters` is empty; `eventTime` = the end; delivery 19–328 s (median 280 s). `Converse*` records carry no ids (time + role + model join; tokens match the spans), and carry the guardrail verdict | §9.2 (replaces the "conflict open" wording), §6.1 EP-7 and EP-11 rows, §8 cadence, §7.2 session-id bullet | 10-f11 §2, §4 |
| S2's IT duplicate: one session id, two request ids | §7.1 duplicate guard | 10-f11 §4.3 |
| **Twin check: no change.** The four `facilitator/` objects repair an IDE helper; the agents' twin (same CodeSha256, `DATA_DIR=/var/task`, generation 1) can't make an on-demand breach. **No new breach-lever option** (D9 unchanged) | §9.1 bucket bullet; §12; §13 D9 | 09 §0, §5 |
| The IDE is not team-exclusive (seven organiser SSM shell commands on 2026-10-05) → the pack is built on the laptop; `EvidenceVersionRead` was granted at 18:10 UTC to the IDE role and `participant-app-role`, not WSParticipantRole; `fix-twin.sh` never run where `submit.sh` packages `~/evidence` | §8 IDE row; §9.1 | 09 §7 |
| Fixer A's CID change: `ifabric-run-<epoch>-<hex>` for every run of our trio | §7.2 step 2 and the envelope example | 11a §4 (04b nit) |
| Fixer A's core split: the bundle embeds `prooflab/evaluators/c16_core.py` (not `c16.py`); `evaluator.sha256` over the core | §7.1 bundle bullet | 11a §3.4 (B11) |
| **Unenveloped invocation** (Fixer A's cross-dependency, E-12): the agent works, mints `ifabric-unenveloped-<epoch>-<hex>`, stamps `provenance: UNATTRIBUTED`, starts at tally 0 under the strictest cap, emits "no envelope" | §7.1 | 11a §4; 04 E-12 |
| Guardrails facts: PII only on the `-helper` alias (GR-06); no guardrail on tool routes (GR-09); no NVIDIA safety models; **whether in-agent rails may block is a captain decision** (a blocking rail amends R-P-13/R-P-10; else they record, `observe`) | §6 opening block, EP-7 row, §6.3 | guardrails/02 §0, GR-06, GR-09 |
| The `guardrails/` link now names its two input files | §6 | — |

**Discrepancy flagged (not resolved by editing the other file):** `guardrails/02` GR-23 says Strands has no switch to keep message content out of spans. 05 AR-25 says `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_unredacted_attributes=` redacts all sensitive attributes. A read of the pinned `strands_agents-1.57.2/strands/telemetry/tracer.py` (in this session's scratchpad: `_compile_unredacted_patterns`, and `start_agent_span` → `_add_event_messages` → `_redact`) supports AR-25, the `invoke_agent` span's prompt included. §7.1 keeps OC-16 closed from source, notes GR-23, and keeps input masking (GR-12) as a second layer; the smoke run settles it live. The guardrails design owner should correct GR-23.

## §12 · Critical path, workstreams, live lane, cut lines

| Change | Source |
|---|---|
| **§12.1 re-timed from 23:45 on the real dependency chain:** W0 ∥ the critical chain (W1 split in two + W2 Stage A, coding against the §3.2/§4 text and rebasing) → S-0 → S-2 → S-3 → S-4 → agents frozen ~05:45 (was 02:00) → pilots → `v1` ~07:45 (was 04:00) → C16 07:45–08:45 → model pause → C7 → baseline/`v1.1` → C9 → adversarial → snapshot 11:50 → pack (first submit by 13:15) → rehearsals → final submit 14:45. **Buffer ~15 min (was ~2 h)** | 04b A8; 08 TC-04, TC-05, TC-06; 05 AR-03 |
| **Spikes-first table, in the brief's order:** S-0 (bundle, stub tests, local Docker), S-1 (ledger POST: zero-write `[]` probe, port-forward fallback), S-2 (build + smoke `ifabric-customer`, 5–10K tokens, the read-only assertion list), S-3 (pin/mode patch + **the halt proof on a low test cap**), SP-1 (Cedar edit on an existing tool, if D15 (a), before the freeze), 06 S2 (bucket PutObject + head-object), OC-20 (metric delay, on S-2), TC-06 (pipeline smoke + the CI/test gate). Each with cost, slot, approver and fallback. SP-2 (Arth) and S-5 (conditional) noted | 05 S-0–S-5; 06 S1–S3; 07 SP-1, SP-2; 08 TC-06, LB-04 |
| ADV-H-01 moved **into the C16 block, straight after N1** (P0); **ADV-R-08 model pause** scheduled right after C16 (P2) | 04 E-09 |
| **Clock items:** the 03:30 credential refresh (window 03:30–06:29; backstop 05:45); ServiceNow credentials by 03:30; Arth's AICT exports moved to 12:00 (the pack now starts 12:05); `check --cutoff` before the final submit | 08 OP-01, OP-02, SN-02, AI-04 |
| **The hard line reworded:** no assessed run before T1 exists; T2 corroborates (D5) | Lead item 6; 04 E-04 (via Fixer A's §3.3) |
| An **Owner** column on every critical-path row | 04b B10 |
| **Batch-approval windows B1–B7** (one OK per run card; T2 approvals and annotations always separate) | 08 HL-03 |
| **The slip rule** (Stage A by 04:30; agents frozen after 06:30 → C9 cut; `v1` after 09:30 → P0–P2 only; pack by 12:30 and first submit by 13:30 whatever happened) and the twin note (no new breach lever) | 04b A8; 09 §5 |
| **Readiness records:** R-J-45 (two rehearsal records, a recorded L1→L3 demo, a timed 15-minute run-of-show), R-P-03 (e) (5-link hand-check), R-P-10 (the OTel row), R-J-56 (mentor review, owner the captain) | 04b unmet requirements |
| **§12.2: every workstream row has an owner (builder → checker) and an acceptance check**; new **W-CI** (the minimal CI/test gate: 3.9 pytest, CI searches, size gate); W1/W2 marked as the critical chain (W1 split); **W4 now depends on W5 for `watch`**; W9 gains the T2 record + export and the re-test link note (04b B9) and the two adapter fixes; the **W-AA placeholder "Assurance agent + console (handoff-3), pending integration"**; total 41–54 agent-h; **a roles table** (Sree accountable + operations; Arth assurance; GRC vacant) | 04b B9, B10; 08 HL-04, TC-06, SN-05, SN-06, SN-09, SN-10; coordinator's note |
| §12.3 live-lane order: S-1, 06 S2, SP-1 before the freeze, S-2/S-3/S-4, ADV-H-01 after N1, the model pause after C16, the Cedar restore before the final snapshot; the preflight and the no-full-GET rule | 05; 06 C5; 07 SP-1; 04 E-09 |
| **§12.3 budget replaced with 08's worked table:** about 37–45 runs, about 2.5–4.3M tokens over about 10 h, **peak about 1.2M/h**, **SC ≤ about 300K always on**, ≤ 3 S2-class runs per clock hour, the halt proof first; what breaks it (one unbounded S2 would now cost the C9 block) | 08 §G, LB-01–LB-04 |
| **§12.4:** P0 now holds the hook in `observe` with the safety ceiling and ADV-H-01; the old fallback "N2 runs with no guard" is gone, replaced by **the declared-tally pause-trigger backstop**; "the safety ceiling is never cut"; **if no C16 breach lever, C7 is milestone 1 and moves into P0**; P1 = `enforce` + N3 + `tail`; P2 adds the model pause and ADV-R-01; P5's Cedar item becomes D15 (b)'s tool build; the D8 mirror's runtime half is free; **a T1-only fallback row** | 04 E-09, E-10; 04b B9, B12; 05 AR-24 |
| §6.2's restore timing aligned with §12 (restore before the final snapshot) | Consistency |

## §13 and `decisions.md` · Decisions

| D | Change (both files unless noted) | Status after the pass | Source |
|---|---|---|---|
| Heading | "D1–D16"; `decisions.md` gains an update note | — | — |
| D2 | Safety ceiling **≤ about 300K, always on**; the halt proven on a low test cap before any S2-class run; the budget figures | Pending captain (values) | 08 LB-01, LB-04 |
| D3 | C9 per-run **Maximum + Errors, now TWO-SIDED**; a declared warm-up rule (each invocation is a new microVM) | Pending captain | 04 E-07; 04b B13; 05 AR-23 |
| D5 | **Date proof: T1 (S3 write-once) dates the threshold; T2 (ServiceNow) corroborates**; per-control versions; T1 fail-safe without Object Lock | Pending captain | 04 E-04; 04b A2; 06 D2 |
| D6 | The one c16 *core* (`c16_core.py`), embedded byte for byte; EP-2 replays `decide_inline` per gateway call (aligned with Fixer A) | Build choice | 11a §3.4 |
| D7 | Build facts: one self-contained file per agent within 24,049 chars, local Docker test, unique `IMAGE_TAG`; J2 as JSON-in-text; the 4th agent pending | Decided by the captain (the build facts are build choices) | 05 AR-03, AR-05, AR-31; coordinator |
| D8 | Points to D16 for the literal "one store"; the mirror's runtime half is free (OC-9); the ledger's server limits | Store frame-decided; D16 and the mirror pending captain | 05 AR-24; 06 B10, C5 |
| D9 | **The C16 breach path is decided by the experiments** (P5–P7); no twin lever (09); with no C16 lever, C7 is milestone 1 | Levers pending captain (recommended: the pilots decide) | 04b B12; 09 |
| D10 | Revised D10-A: four layers (fixed guardrail observed; in-agent rails that record, blocking left to the captain; Cedar on an existing ToolConfig via D15; C16); what is not available | Pending captain | 07 GS-03, GS-14–GS-16, GS-25, GS-27; guardrails/02 §0 |
| D11 | The laptop hub; the IDE not team-exclusive; ServiceNow credentials by about 03:30; one AWS refresh in 03:30–06:29 | Pending captain | 08 OP-01, SN-02, SN-12; 09 §7 |
| D12 | **Stitch key 5 is now an exact join** (baggage CID + `runtimeSessionId`; `eventTime` = the call's end; a retry flagged); `aws.request_id` stays null; `Converse*` records join by time, role and model only (`decisions.md` previously said "runtime ARN + time") | Build choice | 10-f11 (coordinator's note) |
| D13 | Compare model + generation + runtime version (not the digest alone); the approved generation from `ApprovalRecorded.observedGeneration`; decline on `spec.paused`; the live stale-approval fact | Pending captain (recommended: block assessed runs) | 07 GS-14, GS-22; 05 AR-30 |
| D14 | Unchanged: repo YAML + Arth's AICT mirror | Pending captain | — |
| **D15 (new)** | **The Cedar demo path:** (a) edit an existing tool's policy, **recommended**; (b) relax the no-Lambda / no-gateway-write rule (least invasive form: the custom MCP tool); the adopt-mode option removed | Pending captain | 07 GS-01–GS-05, GS-26, SP-1; lead brief |
| **D16 (new)** | **"One store" literally:** (a) the platform ledger with all adapters writing, **recommended**; (b) fallback, a laptop normalized store | Pending captain | 04 E-01; 06 C5; 11a (E-01) |

## §14 · Open checks

Each closed row keeps its number and its question; the "How and when" cell now holds the answer and the evidence pointer. A note under the heading explains the convention.

| OC | Result | Evidence |
|---|---|---|
| OC-1 | **CLOSED** (source): a cancel is a normal `end_turn` with the cancel text and usage 0; the projection is None only if estimation throws | 05 AR-10 |
| OC-2 | **CLOSED** (source): OpenAI's 2 default retries sit below the hook (`max_retries=0`); Strands' 429 retries re-enter it | 05 AR-11 |
| OC-3 | Narrowed: the header is set by the gateway on every listener, verified non-streaming only; S-2 settles it | 05 AR-13 |
| OC-4 | **CLOSED** (live): MCP spans carry `mcp.method.name` (listener `http`); no span carries a finish reason | 06 A5, G1 |
| OC-5 | **ANSWERED no**: the CLI never exposes the request id; key 5 instead joins exactly by baggage CID + `runtimeSessionId` | 06 B6; 10-f11 |
| OC-7 | **CLOSED** (source + live precedents): an edit keeps approval; the policy is chosen from the wire tool name; the context paths; no Cedar text edited live yet, SP-1 confirms | 07 GS-07–GS-12 |
| OC-8 | Open: spike S-1, with the zero-write probe | 06 C2, S1 |
| OC-9 | **CLOSED** (live): stdout in `[runtime-logs]` about 0.9 s later; streams are not invocations | 05 AR-24; 06 B10 |
| OC-10 | Open, narrowed: JSON-in-text needs no forced `tool_choice`; measured in S-2 | 05 AR-31 |
| OC-12 | **CLOSED** (source + precedent): no re-approval on an env patch; the stale-pin caveats | 05 AR-15 |
| OC-13 | **CLOSED** (live): CodeSha256 readable; never `GetFunction`; CloudTrail corroborates | 06 B9; 07 GS-23 |
| OC-14 | **CLOSED** (live): `tmf639.json` holds 0 token copies | 06 D4 |
| OC-15 | Open; the twin dataset has no element-to-site map (gap 10 unchanged) | 09 §3.4 |
| OC-16 | **CLOSED** (source): the redaction switch; re-read in the pinned `tracer.py`; GR-23's different reading noted | 05 AR-25; this pass |
| OC-17 | Partly answered: no bucket policy in the CFN, no `PutBucketPolicy` or Object Lock event; SCP unreadable | 06 D1; 07 GS-20 |
| OC-18 | **CLOSED as a gap-9 fact**: self-signed placeholder certificate (SAN `<PERIMETER-HOST>`), model routes only, no MCP TLS | 07 GS-25 |
| OC-19 | **CLOSED** (live): the field paths; the approved generation from `ApprovalRecorded` | 05 AR-30; 07 GS-22 |
| OC-20 | Open: measured on S-2 | 06 S3 |
| **OC-24 (new)** | Participant PutObject on the team bucket (spike 06 S2) | 06 D1 |
| **OC-25 (new)** | Whether AICT imported `my_agent` (the ServiceNow half of discovery; Arth, now) | 08 AI-02 |
| **OC-26 (new)** | Whether the no-mistakes pipeline runs green here (the pilot PR) | 08 TC-06 |

The coordinator's note asked that no §14/§15 text still say the AWS invocation records carry "no run id": OC-5 and the §15.2 rows now state the exact join (see §15 below).

## §15 · Gaps and out of scope

**Reading of "the four new rows from §15.2 (if not already present)".** The four rows the risk-and-ownership pass added to §15.2 (separation of duties; AICT approvals without approver or time; platform components' owners unconfirmed; the EU AI Act tier without a primary source) were already present and are kept. The four new facts the brief lists are folded into their gap rows, and new rows were added where no row existed.

| Change | Source |
|---|---|
| Gap 2 (WHO): per-agent Cedar isn't wired; the AWS invocation records now join exactly (CID + session id) | 07 GS-27; 10-f11 |
| Gap 3 (WHAT): a Cedar refusal only where a rule exists on the called tool (D15) | 07 GS-03 |
| Gap 4 (AUTHORIZED): the AWS model-call record's "Guardrail blocked." as extra corroboration | 10-f11 §4.4 |
| **Gap 5 (APPROVED): generation 2 running on a generation-1 approval** (the reference IT and network agents, live); no approval record on edits, swaps or env patches; EP-0's check | 07 GS-22; 05 AR-15 |
| Gap 7 (RECONSTRUCT): the `Converse*` records carry no ids (time + role + model join), while the invocation records do carry the run | 10-f11 |
| **Gap 8: S2's IT agent invoked twice** (one session, the CLI's re-send after 180 s); our one-invocation rule and duplicate guard | 05 AR-18; 10-f11 §4.3 |
| **Gap 9: the TLS placeholder certificate** (self-signed, SAN `<PERIMETER-HOST>`, model routes only, no MCP TLS); our span redaction | 07 GS-25; 05 AR-25 |
| Gap 10: re-checked after the organisers' twin fix, unchanged | 09 |
| Gap 11: readable CodeSha256 + CloudTrail; the organisers audit the same Lambdas | 06 B9; 07 GS-23; 09 §7 |
| **New row: Bedrock guardrails are not editable** (fixed per alias, PROMPT_ATTACK input only, PII only on `-helper`, no per-call choice, none on tool routes, no NVIDIA safety models) | 07 GS-15, GS-16; guardrails/02 |
| New row: an AgentConfig pause is a record, not a stop | 07 GS-14 |
| New row: the ledger server's fragility (single-threaded, 256Mi, no fsync, volume deleted with the stack) | 06 C5, C6 |
| New row: shared spaces (the IDE not team-exclusive; organisers write into our bucket and read our ledger) | 09 §7 |
| AICT usage row: why the count is 0 (`InvokeAgent` filter; empty `requestParameters.sessionId`) | 08 AI-03; 10-f11 §1 |
| Separation-of-duties row points at the §12.2 roles table | 08 HL-04 |
| New conditional row: readiness records (R-J-45 demo + run-of-show, R-P-03 (e), R-J-56) listed as gaps if not produced by the final submit | 04b |
| §15.1: no Bedrock guardrail create/edit; no TLS for model calls; a custom tool only under D15 (b) | 07 GS-15, GS-25 |

## Consistency fixes after the main pass

| Change | Where | Why |
|---|---|---|
| The pin is `IFABRIC_PIN_JSON` + `IFABRIC_PIN_SHA256` (+ register version and sha), with the declared faults inside it | §7.1 start-up, §7.2 faults, §7.2 preflight, S-3 in §12.1 | Fixer A's §3.3 (I-04, B4) |
| EP-0 compares model + generation + runtime version (not the digest alone) and holds the staleness test (`approval.check_versions`); EP-5 no longer computes staleness; EP-10 records the facts | §6.1 rows EP-0, EP-5, EP-10 | 07 GS-22; Fixer A's §3.4 (04b nit) |
| Table integrity checked by script: every row in my sections' tables and in `decisions.md` has its header's column count | — | — |

## Follow-ups for the lead (outside Fixer B's sections; not edited)

1. **§3.10, the components table:** the row "The `ifabric-` Cedar test tool (if D10)" should read "(only if D15 (b))"; under D15 (a) the Cedar rule lives in an existing, platform-owned ToolConfig, whose generation and policy `resourceVersion` the inventory should record after SP-1.
2. **§5.5, `run-ids.txt`:** its line format puts the control first; §9.1 now puts the CID first (04b B14). Align §5.5.
3. **The file header's "Still pending" list** (top of `ARCHITECTURE.md`) should add D15 and D16.
4. **Transient wording:** if §3.3 still requires "both T1 and T2" anywhere, it conflicts with D5's "T1 dates; T2 corroborates" (Fixer A's 11a says §3.3 was rewritten; re-check after both passes land).
5. **`guardrails/02` GR-23** contradicts 05 AR-25 on span redaction; the pinned source supports AR-25 (see "Late inputs"). The guardrails design owner should correct it.
6. **D15 reading** (flagged in the §6 section above): confirm that the custom MCP tool counts as "relaxing the rule" (D15 (b)); 07 rated it SUPPORTED and on-path.
7. **A possible new decision, not numbered here:** whether in-agent rails may block (a second waiting question, amending R-P-13 and R-P-10), raised by `guardrails/02` §0. §6 and D10 keep "record only" until the captain answers.
8. **Arth's deadlines moved:** the AICT exports are now due by 12:00 UTC (the pack starts at 12:05); the ServiceNow credentials by about 03:30 UTC still stand.

## The re-timed critical path, in short

- Now → 02:00: push the contracts, decisions, fleet set-up; L1 (S-1 ledger POST, the bucket write); W0 as the pilot PR; S-0; SP-1 if D15 (a).
- 02:00 → 05:45: the critical chain (W1 split, W2 Stage A) lands about 04:00; credential refresh at 03:30 and ServiceNow credentials by 03:30; S-2, S-3 (halt proof), S-4; **agents frozen about 05:45** (was 02:00).
- 05:45 → 07:45: pilots, derive, **`v1` frozen about 07:45** (T1; T2 corroborates).
- 07:45 → 11:50: C16 with ADV-H-01 (milestone 1), the model pause, C7, baseline + `v1.1`, C9, the remaining adversarial cases.
- 11:50 → 15:00: final snapshot, pack and first submit by 13:15, two rehearsals, final submit 14:45; **buffer about 15 min** (was about 2 h). The slip rule cuts C9 first.

## Final review fixes (after the reviewer's pass, 00:15 UTC)

| Change | Where |
|---|---|
| **Arth-unavailable fallback:** T2 proceeds on Sree alone; assurance checks recorded "not independently reviewed" (a gap); an AI reviewer acts as rehearsal tester and hand-checker, labelled; Arth-credential steps wait or become gaps | §12.2 (after the roles table); §15.2 separation-of-duties row |
| **SP-1's policy texts have an owner:** W3 writes them (original, forbid, restore), checked by the guardrails design's author; acceptance: they parse offline (e.g. `cedarpy`) with every attribute `has`-guarded | §12.2 W3 row |
| **S-3's low test cap has a source:** a throwaway `v0-smoke` version (EXPLORATORY, frozen locally, never uploaded as T1), so the pin comes from `registry pin` and the post-run pin check holds; W8 owns it | §12.1 S-3 row; §12.2 W8 row |
| The Cedar edit and the restore each move the tool's generation: a new inventory version before any INV pass | §6.2 lifecycle |

**Follow-up 9 for the lead:** §10.3's WHO row still says the AWS invocation record joins "by ARN + time (EP-11)"; after 10-f11 it joins exactly by baggage CID + `runtimeSessionId`. §10 is Fixer A's; 11a lists no §10 change.

**Clock note:** at 00:15 UTC the first window of the re-timed path (push, captain's decisions, L1) is already half spent; any delay there comes straight out of the 15-minute buffer.

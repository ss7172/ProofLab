# 12 · Reconciling handoff 3 (Arth's Evidence Console plan + Nemotron Assurance Agent) with our architecture

Written 2026-10-05 (about 23:40 UTC onward) by the reconciliation analyst subagent. Read-only: the only file written is this one. No git, cluster, AWS or ServiceNow action was taken, and no secret was read or printed.

**The captain's directions applied** (relayed by the coordinator on 2026-10-05):
- ServiceNow has a part in the challenge: AICT integrates with the AWS agents for discovery, but discovers only their names. So the team built the iFabric Assurance Agent, which shows in AICT and is also part of the dashboard. It is a ServiceNow-facing agent and must be deployed on AWS AgentCore.
- The dashboard in handoff 3 is the frontend.
- Integrate everything as a whole: frontend, backend, AI agents, AWS, ServiceNow.
- **Arth's code (`ifabric-handoff-3/code/`) is used as is.** Our architecture adapts around it with minimal glue: adapters, data feeds, packaging. Where a verified fact conflicts, propose glue or flag BLOCKED with the minimal decision.
- Every boundary change is a task in our plan (§5.4).
- §5 names the master document per topic.

## Inputs read, and the state reconciled

**Theirs, all read in full:**
- **The plan:** handoff-3 `README.md`; `evidence-console-plan/README.md` and `01`–`09`.
- **Read for this file:**
  - the enum constraints in `schemas/contracts.schema.json`;
  - the shape of `examples/pack-index.json`;
  - the hard-coded EP labels in `demo/index.html`;
  - the text of `presentation/JUDGING-DAY-GUIDE.html`.
- **Deliverables:** `deliverables/{architecture/servicenow-section.md, PRESENTATION_DAY_INTEGRATION.md, TEAMMATE_ACTIONS.md, README.md, thresholds/*, evidence-pack/{gap-list.md, run-ids.txt, servicenow/README.md, servicenow/wiring-tests/README.md, tools/manifest.py}, pitch/*}`.
- **Code:** every module of `code/prooflab/servicenow/` except the tests, plus the panel's `render`/`poll` code.
- **Docs:** `docs/` diffed against the repo's copies. Handoff 1 and the playbook differ only by the Nemotron-ruling edits (4 and 2 lines).
- **Panel copies:** `demo/assurance-panel/ifabric-case-panel.{js,css}` is byte-identical to `code/…/panel/` (checked).

**Ours:**
- **`architecture/ARCHITECTURE.md`**, read in two passes because two fixers were editing it:
  1. in full at 185,325 B (file time 18:28 local);
  2. re-read at 294,636 B (19:06 local, about 00:06 UTC) for §3.4, §3.7, §3.8, §7.1 and §12–§14. That pass found the 23:45 re-timing of §12.1, the W-AA placeholder in §12.2, D15 and D16, and the revised D5 (T2 now corroborates).

  This file reflects the second state. Small churn after it is possible.
- `decisions.md` (D1–D14; D15 and D16 seen in ARCHITECTURE §13) and `one-page.md`.
- `work/05`–`08` (the feasibility reports).
- `PLANNING-HANDOFF.md` (§5, §8, targeted).
- Memory `platform-verified-facts`, `servicenow-context`.

**Measured for this file** (local, read-only): the gzip+base64 size of each Arth module (§4 V-01); the schema enums (§4 V-33); the panel byte-equality above.

**Not done:** no live call of any kind, no write except this file, no secret read.

## 0. Bottom line

**Arth's plan** is a complete frontend-and-ServiceNow design: the **ProofLab Evidence Console**.
- **What it is:** a loopback-only, read-only, stdlib web console. PACK mode reads exactly the S3 pack; LIVE mode tails a live event file. It has 11 views, 9 JSON contracts with a schema and fixtures, and acceptance tests AT-01…AT-22.
- **Its Human Loop view** embeds Arth's tested ServiceNow panel.
- **It also specifies** an AWS-side pipeline (capture → facts → records → pure evaluators → findings) and named runs.
- **Built and tested:** the ServiceNow adapter, the Assurance Agent's write path and the panel.
- **Pending or planned:** the Nemotron call, the AgentCore deployment and the console itself.

**The Assurance Agent** (§2) is a reviewer of our own control-finding incidents.
- After `notify()` has delivered an `[iFabric]` incident, Arth's `run_assurance_agent()` asks **Nemotron through `modaas-agw`** for one note.
- It writes that note **only if** the model echoes nine facts exactly and cites only evidence in the finding.
- The write is **one `work_notes`-only PATCH**, read back by digest. The run is recorded in a run record and the delivery log.
- The five dashboard sections (movement, decision trace, evidence, P1–P8, V1–V6) are computed **by code**.
- Its AgentCore runtime `ifabric_assurance_agent` is what AICT discovers, **by name only**: no usage, no Monitor.
- It holds no ServiceNow credentials. It is part of EP-13's callback loop: never in an agent's path, never a control.

**The top conflicts** (§3), all settled by the captain's directions or the frame:
1. **The dashboard:** a static HTML file vs their console. Take theirs (D17).
2. **The one store:** the ledger vs files as the store. Ours; their file tree becomes a one-way projection.
3. **C16:**
   - the figure of record: ephemeral stdout vs `aws/spans` (ours);
   - EP3 handoff admission and a per-invocation call limit (rejected by the frame);
   - FM-B on the reference agents and FM-C by rebuild (rejected by D9).
4. **EP numbering and "ServiceNow is the second EP".** Ours; their own guide agrees.
5. **T2:** "not a Finding" vs their approval incident. Take theirs (D19): it needs no code and closes our SN-09 spike.

**BLOCKED as written** (§4): 10 rows. The key ones:
- **V-01, AgentCore packaging:** `new-agent.sh` plus importing `prooflab.servicenow` inside the image fails AR-03's one-file / 24,049-char build. Arth's modules come to 34,176 chars gz+b64.
- **V-02, the gateway call inside the runtime:** `nemotron.py` refuses the injected `http://<public ELB>:8081/v1`, and :8443 is self-signed with a placeholder SAN.
- **V-03, the IDE "first proof":** the same refusal, and the key would cross in plain HTTP.
- **V-14, closure:** the integration user can't resolve incidents (no code).
- **V-29, the register template:** the nested YAML breaks the kit parser.
- **V-23 to V-27, the frame:** EP3 admission, held actions, the call limit, the reference-agent runs, ServiceNow as the second EP.

One near-miss is a CAVEAT, not a block: their CR capture (V-20) would trip their own secret-scan gate on the two annotation copies of the ledger token. Drop all three paths at capture (G-11).

All have glue or a decision. None needs a change to Arth's code.

**The recommended merge** (§5):
- **Ours is the master for** controls, evidence, registry and agents.
- **Arth's is the master for** ServiceNow, the Assurance Agent logic and the console.
- **19 glue tasks** (G-01…G-19). The key ones:
  - a one-file AgentCore handler that keeps Arth's analyzer contract (G-01–G-03);
  - a finding builder that fills Arth's finding context (G-04);
  - a human-loop runner that owns the delivery log (G-05);
  - a one-way pack projector validated against their schema (G-07);
  - an answer composer on our engine (G-08);
  - the console build, with EPs rendered from data (G-09).
- **Cost:** about 18–24 net-new agent-hours, off the critical chain; only about 4–6 h of it is P0. About 15 more minutes of live lane.
- **Seven captain decisions:** D17–D23.

## 1. Their plan, summarized faithfully

The package is `~/Downloads/ifabric-handoff-3/`, from Arth's ServiceNow workstream (with Claude Code), dated 2026-10-05. It contains:
- `evidence-console-plan/`: README, `01`–`09`, `schemas/`, `examples/`, `demo/`, `presentation/`;
- `deliverables/`;
- `code/`;
- `docs/` (handoff 1 + the playbook, both edited for the facilitators' Nemotron ruling).

This summary goes by pointer: file § and table name. The Assurance Agent is in §2.

### 1.1 What it is, and its status
- **Its one line:** the console "sees everything and can refuse nothing". It turns the sealed Evidence Pack into answers a sceptical stranger can check in seconds. Every number links to its raw record, and every action it asks for is itself recorded as evidence (README).
- **What it delivers:**
  - the console plan, already integrated with the ServiceNow Assurance Agent;
  - the agent's code (152 tests);
  - live evidence (wiring tests);
  - the presentation-day pieces (handoff-3 README §1–§2).
- **Status** (README §4; 08 §0):

| Part | Status |
|---|---|
| Incidents | Verified live |
| The Assurance Agent's write path | Verified live, with a TEST stand-in |
| The Nemotron call | Pending |
| AgentCore + AICT | Pending |
| The console | Planned, with a working HTML demo on synthetic data. **"Nothing in this folder is a real result"**; every threshold is illustrative |

### 1.2 Architecture and components (02)
- **The system view** (02 §1):
  - **Execution path:** `ifabric-run` → EP3 handoff → the agents; EP2 (in-process C16 admission) → EP1 `modaas-agw` → Bedrock Nemotron; EP5 kill switch.
  - **Telemetry**, pulled read-only: stdout, `/aws/modaas/gateway`, `/modaas/evidence`, PDP, ledger, spans, X-Ray, CR status, AICT CloudTrail.
  - **Off the path, a numbered pipeline:**
    1. `raw/` (immutable captures + sidecars);
    2. `facts/`;
    3. `records/` (bound evidence);
    4. pure evaluators over a frozen `register.yaml`;
    5. `assessments/`;
    6. `findings/` → `notify()` → ServiceNow (EP4) → Assurance Agent;
    7. `servicenow/` (delivery log = the trust anchor);
    8. `answers/`, `auditor/`, `runs/`;
    9. the pack (README, MANIFEST, `pack-index`) → `submit.sh` → S3.
  - **Then:** the console, read-only and loopback.
- **Eleven components** (02 §2), with "in path?" and "holds secrets?": agents; `ifabric-run`; the EP2 adapter; capture jobs; normalizer/binder; evaluators; publisher + Assurance orchestrator; query engine; pack builder; the console (no secrets, never in the path); the actuator (P2).
- **EP table, "stated honestly"** (02 §3):

| EP | What it is |
|---|---|
| EP1 | `modaas-agw`, `pull` |
| EP2 | In-process admission, `evaluate` |
| EP3 | Handoff admission in `ifabric-run`, `evaluate` |
| EP4 | ServiceNow; a real EP only if the change is **held** (§3.1); otherwise ALERT_ONLY |
| EP5 | Kill switch |
| EP6 | Tool Cedar |

  Second-EP options: (a) the adapter, (b) EP3, (c) a Cedar deny, (d) no claim. "Changed adapter / unchanged core" lists per EP.
- **Transports and modes** (02 §4): `evaluate`, `emit`, `callback`, `pull`; static, scheduled, event-driven, in-transaction, continuous. `admit()` (the evaluator) and `test()` (the tester) are both pure.
- **Console modes** (02 §5): PACK (judges; MANIFEST verified; no actions), LIVE (operators; ≤ 5 s), VIEWER (P2, `file://`). Operator actions (P2) go **ask → record → never decide** through an actuator.
- **Zero trust** (02 §6):
  - a NIST SP 800-207 tenet → control map;
  - five trust boundaries: TB1 browser ↔ console (XSS, CSRF, DNS rebinding); TB2 console ↔ files; TB3 console ↔ actuator; TB4 loop ↔ AWS, ServiceNow, gateway; TB5 pack ↔ S3 ↔ judges;
  - a "who holds which secret" table;
  - data minimization: drop span content; never reasoning.
- **Auditability** (02 §7):
  - immutable layers with `supersedes`;
  - `provenance` ∈ ASSESSED / EXPLORATORY / WIRING_TEST / SYNTHETIC;
  - date before test;
  - a deterministic `answer_id`;
  - a session ledger;
  - the same-ID chain;
  - clock discipline;
  - completeness statements;
  - "7 years" retention;
  - integrity without crypto.
- **Failure modes** (02 §8).
- **Corrections to the playbook** (02 §9, 15 rows, from our verified facts).
- **Topology** (02 §10): the console on `127.0.0.1:8787`; no public endpoints, no tunnels.

### 1.3 Contracts (03, `schemas/contracts.schema.json`, 14 fixtures, `generate_examples.py`)
- **Nine contracts** (03 §1):
  - `ifabric.evidence/v1` (`records/<C>/…jsonl`);
  - `ifabric.assessment/v1` (`assessments/<C>/<scope>.r<N>.json`);
  - `ifabric.answer/v1` (`answers/`);
  - `ifabric.auditor/v1`;
  - `ifabric.run/v1`, with `hop`, `decision`, `policyCheck`, `outcomeValidation`, `laneEvent` (`runs/<cid>/run.json`);
  - `ifabric.adversarial-case/v1`;
  - `ifabric.gap/v1`;
  - `ifabric.pack-index/v1`: the console's single entry point and allow-list;
  - `ifabric.console-action/v1` (P2).
- **Reused unchanged:** `Finding`, `ifabric.servicenow.case/v1`, `ifabric.assurance-agent.run/v1`, `ifabric.evidence-manifest/v1`.
- **Ids** (03 §2):
  - the CID `fault-<epoch>-<6hex>` in baggage;
  - the run alias (FM-B), written before judging;
  - the call id `c-NNNN`;
  - the action id;
  - `finding_id = ifabric:{ref}:{ver}:{scope_kind}:{scope_id}:{kind}` = the ServiceNow `correlation_id`;
  - `assessment_id`, `evidence_id`, `decision_id`, and `answer_id` = sha256 of the canonical answer.
- **Reference prefixes:** an unresolvable ref renders red.
- **Vocabulary** (03 §3):
  - verdict: SATISFIED / BREACHED / INDETERMINATE / NOT_ASSESSED;
  - claim verdict: SATISFIED / NOT_SATISFIED / NOT_ESTABLISHED, never averaged;
  - inline decision: ALLOW / ALERT / DENY;
  - six questions: ANSWERED / PARTIAL / GAP;
  - policy checks;
  - outcome validation;
  - adversarial outcome: DEFENDED / DETECTED / BROKE_FIXED / BROKE_OPEN;
  - EP status, rendered as is;
  - closure only with a `retest_ref`.
- **The key contracts** (03 §4):
  - the evidence record uses the slide's exact field names, with `seal: "out-of-scope"`;
  - the assessment carries the threshold *as loaded* and a `population`;
  - the answer has these parts: rule with `date_before_scope`, population, both numbers, exceptions, verdict, tester vs evaluator, the 10 audit-question rows, `human_loops[]`, `aict`, tickmarked records, gaps, source;
  - the run has the five facets: movement, decision trace, evidence, policy alignment, outcome validation;
  - the auditor file carries honest expected grades (WHO PARTIAL, …);
  - `pack-index` holds the claim, register, artefacts, named runs with `written_at`, EPs with honest status, `cases[]` and integrity.
- **Rules** (03 §5): additive only; never mix provenance; never compute a verdict in the UI (except "Verify without us"); text is data; unknown is a value.

### 1.4 Data flow: logs → evidence (04)
- **Six layers, none editing another:** capture → normalize → bind → evaluate → find → answer. Each is idempotent.
- **Twelve capture recipes** with gotchas (§2):
  1. gateway stdout (the C16 figure of record, ephemeral);
  2. `/aws/modaas/gateway`;
  3. `/modaas/evidence`;
  4. PDP (both replicas);
  5. the ledger `/records?cid=`;
  6. AgentCore spans (drop content);
  7. X-Ray;
  8. the C9 metrics;
  9. CR status (redact);
  10. `aict-invocations`;
  11. the L1 proofs;
  12. ServiceNow.
- **Capture-time redaction** (§3, six rules); the **sidecar** (§4); the **facts files** (§5); the **binder** (§6, "unbound" → quarantine); a **worked example** from a log line to an evidence record (§7); **completeness** (§8: under the cap but incomplete is INDETERMINATE); a **capture checklist** (§9).

### 1.5 The AWS-side build (05)
- **Pack paths** (§0).
- **The freeze gate** (§1):
  - start the C9 baseline "now";
  - fill the register from EXPLORATORY runs (cap by method, with the 5×5 risk matrix);
  - `policies/agent-policies.yaml` AP-v1 (P-EVID-01 … P-ACTION-06);
  - `expected/scenarios.yaml` and `expected/S{1,2,3}.yaml`;
  - freeze → approve → run.
- **C16** (§2):
  - a pure `c16.test()` and `c16.admit()`, tests first;
  - EP3 (the cheapest) or EP2 admission, with one decision record per call;
  - named runs: FM-A S1 ENFORCE; FM-B S2 OBSERVE (or the reference agents); FM-S3; FM-C, the re-test after a new generation; FM-D, R5 with an EP2 DENY;
  - publish with the finding keys.
- **The orchestrator `ifabric-run`** (§3): identity, movement hops, budget, decisions, the S3 hold, rate, the manifest.
- **`prooflab watch`** (§3A): eight streams into `live/events.jsonl`, a heartbeat, STALE.
- **The agents' five facets** (§4):
  - a structured final answer (JSON);
  - ledger fields: trace id, action id, tokens, the guardrail outcome;
  - tool results as evidence;
  - the S2 fix: P-AMBIG-02, a call limit, the schema;
  - a fallback that derives the facets from the ledger.
- **A host-side policy checker** (§5); **outcome validation** (§6); **C7 and C9 rules** (§7); **14 adversarial cases**, V0 to R8 (§8); **pack assembly** (§9); a **never list** (§10).

### 1.6 The UI (06)
- **Intent:** a "forensic instrument" for a sceptical GRC judge.
- **Signature elements:** auditor tickmarks R·A·T·V; the Evidence Lane; the date-before-test ribbon.
- **Rejected defaults:** KPI grids, a chatbot.
- **Design:** IBM Plex; dark and "paper" themes; tokens (§2); a 52 px top bar with the Ask bar (⌘K), mode and integrity; a lettered exhibit rail A–K; an inspector drawer (§3); components (§4).
- **Screens** (§5): A Overview · **B Ask/Answer (P0)** · C Agent Trail · **D Evidence Ledger (P0)** · **E Six Questions (P0)** · **F Register (P0)** · G Human Loop · H Adversarial · I Architecture · **J Gaps (P0)** · integrity (P0) · Control Room (P2) · K Live Monitor/Replay.
- **The rest:** the deterministic query grammar (§6); present mode, 8 steps with a 15:00 timer (§7); quality gates, WCAG 2.2 AA, performance (§8).

### 1.7 The console API and security (07)
- **Process:** `python3 -m prooflab console --pack evidence/ [--live] [--operator]`; binds 127.0.0.1; verifies the MANIFEST; prints a one-time token URL (§1).
- **Endpoints:** 16 (§2).
- **Zero-trust controls, each with a test** (§3): loopback, the Host allow-list, a session cookie, CSRF, roles, the path allow-list, output safety, CSP and the other headers, rate and request limits, integrity gating, a no-secret-env check, logging.
- **The actuator** (P2, §4): `RUN_CONTROLTEST`, `SERVICENOW_CHECK`, `PACK_SEAL`, `PACK_SUBMIT`, `RUN_SCENARIO`, `KILL_SWITCH_DRILL`; dual control for shared impact.
- **Budgets** (§5); the **tests to write first** (§6).

### 1.8 ServiceNow and the Assurance Agent (08; `deliverables/`)
- **The Assurance Agent:** §2 of this file.
- **The case contract** (08 §6).
- **Console integration** (08 §7):
  - the evaluator loop writes `case --out` snapshots, and the console serves only those;
  - the drop-in panel is embedded as the Human Loop view;
  - `serve` is a standalone backup on 127.0.0.1:8765;
  - offline: `panel/index.html` with a file picker.
- **Also in 08:**
  - the GUI spec (§8);
  - evidence paths (§9);
  - the 2-minute demo (§10);
  - gap additions 9–17 (§11);
  - troubleshooting (§12);
  - the acceptance checklist (§13);
  - who does what (§14);
  - AICT capture (§15);
  - owner engagement and closure only by a passing re-test, with the `retest` key (§16).
- **Deliverables:**
  - the threshold register template and Sree's approval workflow, through an approval incident (`thresholds/`);
  - the Evidence Pack skeleton, with Section A of the gap list (A1–A18) written (`evidence-pack/`);
  - the ServiceNow half of the one-page architecture (`architecture/servicenow-section.md`);
  - the teammate's work list, phases A–H with "done when" checks (`TEAMMATE_ACTIONS.md`);
  - the merge of the six artefacts and the final S3 tree (`PRESENTATION_DAY_INTEGRATION.md`).

### 1.9 Build order and acceptance (09)
- **Rules:**
  1. controls before the console (cut console scope, never control scope);
  2. the console is built in parallel against the fixtures;
  3. P0 → P1 → P2 gates.
- **Track A**, about 20 h from 19:00 UTC: A0 the C9 baseline now; A1 the register + approval; A2 capture; A3 the binder; A4 c16; A5 `ifabric-run`; A6 the agent rebuild (optional); A7 the named runs; A8 the publisher; A9 C7; A10 C9; A11 adversarial; A12 the pack; A13 `watch`.
- **Cut order:** A6, then A11, then C9, never C16.
- **Track B:**
  - **P0** (about 3 h): skeleton, grammar, server, UI P0 views;
  - **P1** (about 2 h): Overview, Agent Trail, Human Loop, Adversarial/Architecture, Live Monitor, Present mode;
  - **P2:** the actuator, the viewer.
- **Track C:** Arth's approval, AICT, the live run.
- **Track D:** rehearsals.
- **Acceptance tests AT-01 … AT-22:**
  - **AT-P0** = AT-01–12 + AT-14;
  - **AT-P1** adds AT-13, 15, 16, 19, 20, 21, 22;
  - **AT-final** adds AT-17 and AT-18.
- **A 14:00 UTC definition of done.**

### 1.10 The pitch and presentation day
- **The run of show** is `presentation/JUDGING-DAY-GUIDE.html`:
  1. the promise;
  2. L1;
  3. L2 (log vs evidence, AICT);
  4. L3 (the Human Loop and the Assurance panel);
  5. the judges ask (⌘K, Six Questions, Verify without us);
  6. good decisions (FM-B → FM-C; Live/Replay FM-D);
  7. attacked (adversarial, and "the same checker in two places");
  8. what's missing.

  It also gives the bonus mapping, the judges' phrases, answers to likely questions, and the before-stage and if-it-breaks steps.
- **Older proposals:** `deliverables/pitch/running-order-15min.md` and Arth's `pitch-L2-L3-script.md`, which call ServiceNow "our second enforcement point", plus a backup shot list.
- **`PRESENTATION_DAY_INTEGRATION.md`:**
  - who brings what for each of the six artefacts;
  - the final `evidence/` tree;
  - seven evening steps (never mix the wiring-test logs);
  - on-the-day roles;
  - a final checklist.

## 2. The iFabric Assurance Agent, exactly

Sources: 08 (the single source of truth) and the shipped code: `assurance_agent.py`, `nemotron.py`, `analysis.py`, `assurance_checks.py`, `case_view.py`, `client.py`, `notifier.py`, `finding_context.py`, `cli.py`, `panel/ifabric-case-panel.js`. Where the docs and the code differ, the code wins, and the difference is noted.

### 2.1 In one paragraph
The Assurance Agent is a **Nemotron-based reviewer of our own control-finding incidents**.
- **When it runs:** after our adapter has raised an `[iFabric]` ServiceNow incident for a finding (BREACHED, ESCALATED or a monitoring gap) and read it back.
- **What it does:**
  1. It reads the incident.
  2. It gives Nemotron, through `modaas-agw`, the finding's facts, the evidence refs and the incident text.
  3. It accepts the reply only if it echoes **nine fact fields exactly** and cites only evidence that is in the finding.
  4. It then writes **one fixed-format work note** onto the incident and reads the note back.
- **What it leaves:** a run record and a line in the delivery log.
- **The five sections** shown in the dashboard (agent movement, decision trace, evidence, policy alignment, outcome validation) are computed **by code** from the finding, the delivery log and the run record, **never by the model**.

The captain's framing fits the code. AICT discovers only the agents' **names** (AgentCore runtimes, by name). The Assurance Agent carries the **content** of the assurance into ServiceNow, as a validated note on each incident, and the same content into the dashboard, as the case JSON. "A ServiceNow agent" describes its **role**: it faces ServiceNow. Its **runtime** is AWS AgentCore, because Nemotron is reachable only through `modaas-agw` (facilitator ruling, 2026-10-05; 08 header). The ServiceNow-native prototype on the ServiceNow LLM is superseded and inactive.

### 2.2 Its two parts, and where each runs

| Part | Code | Runs where | Holds | Never holds |
|---|---|---|---|---|
| **Enforcement wrapper** (Arth calls it "the enforcement point" over its own note) | `run_assurance_agent()` (`assurance_agent.py:203-252`) + `analysis.py` + `assurance_checks.py` | The human-loop runner, the process that owns `delivery-log.jsonl`. Ours is the laptop (D11); Arth's text says "your evaluator loop / IDE". **Off every agent's path** | The ServiceNow OAuth credentials; the delivery log | The gateway key, when the AgentCore backend is used |
| **Analyzer** (messages in, text out) | Backend `gateway`: `GatewayAnalyzer` (`nemotron.py:97-153`) calls `modaas-agw` directly. Backend `agentcore`: `CallableAnalyzer` (`nemotron.py:156-176`) invokes the runtime `ifabric_assurance_agent`, which calls `modaas-agw` | The laptop or IDE (gateway), **or** AWS AgentCore (agentcore). Only the AgentCore form appears in AICT (gap A10) | The gateway key: injected into the runtime by the operator (agentcore); the API-key variable in the laptop process (gateway) | ServiceNow credentials. The runtime is "a pure analyzer" (08 §2, §5.3) |

### 2.3 What happens on one call (the code's order)
1. **Find the incident:** look it up by `correlation_id = finding_id` and `sys_created_by = ifabric.integration`. None found → `NOT_DELIVERED`.
2. **Read the display values:** `number`, `short_description`, `description`, `state`, `assigned_to` and `work_notes`.
3. **Skip if already done:** if a note exists whose digest is in the delivery log (`ANALYSIS_*` `note_digest`), and it is complete and its facts match → `SKIPPED`. A re-run needs `force=True`.
4. **Protect the owner's reply:** if the owner has replied live, `check_response` records it **before** the note becomes the incident's last update. This guards against bug (b) masking.
5. **Build the facts:** six static ones (Finding ID, Control, Threshold version, Scope, Verdict, and Next step = a fixed policy sentence per verdict, `analysis.py:28-31`) plus three from the incident (Owner, State, Owner response = Yes or No).
6. **Build the prompt:**
   - a system prompt, followed by FACTS (copy exactly), EVIDENCE refs and the FINDING SUMMARY;
   - then the incident `description`, at most 3,000 chars, inside `<<<INCIDENT TEXT … INCIDENT TEXT>>>`. Runs of 3 or more `<` or `>` are removed, so the delimiter can't be forged;
   - then the note template.
7. **Compute the checks:** `movement` (M1–M3) and `policy_alignment` (P1–P8) are computed by code and stored in the run record.
8. **Ask, at most twice:** call the analyzer up to 2 times.
   - Each reply: `strip_reasoning`, parse, then `validate_fields`.
   - The 9 facts must match exactly and the 3 judged fields must be non-empty. Every evidence ref must be in `finding.evidence`.
   - A failure → re-ask once, then `REFUSED`.
   - A guardrail block → `BLOCKED`. An outage → `FAILED`.
9. **Render the canonical note:**
   - 12 model lines: the 9 echoed facts + 3 judged;
   - 4 code lines: `Agent path`, `Policy alignment`, `Validation`, and `Model` = "NVIDIA Nemotron via <backend> (alias …; model …; action <x-modaas-action-id>)".
10. **Guard:** the number must look like `INC…`, the short description must start with `[iFabric]`, the marker must be present, and the note must be ≤ 4,000 chars. Otherwise → `REFUSED`.
11. **Write and read back:** PATCH `{"work_notes": note}` only, then read back.
    - The digest matches → `WRITTEN`.
    - Not found, or a different digest → `UNVERIFIED`.
12. **Record it:**
    - the run record `evidence/servicenow/assurance-agent/<finding>_<utc>_<n>.json` (`ifabric.assurance-agent.run/v1`);
    - a delivery-log line `ANALYSIS_<STATE>`, with the backend, the alias, the action ids, the run-record path and `note_digest`.

**Doc vs code.** The module docstring says the model judges "four fields … next step". The code judges three (`JUDGED_FIELDS`), and Next step is a fact the model must echo. 08 §2 agrees with the code.

### 2.4 Inputs

| Input | Contents | Source |
|---|---|---|
| The Finding (required) | `control_ref`, `control_id`, `threshold_version`, `scope_kind`, `scope_id`, `verdict`, `summary`, `detected_at`; `evidence[]`; `kind` | Our evaluator → finding builder (G-04) |
| The Finding context (optional; feeds the five sections) | `measured` {value, unit}; `limit` {value, operator, unit}; `register` {version_date, owner, approval}; `trace[]` (≤ 200 steps: at, actor, zone ∈ customer/it/network/gateway, action, decision, ref, run_id); `retest` {assessment, verdict, threshold_version, at} | The same. Never part of the finding id (`finding_context.py`) |
| The incident | Display values: number, short description, description, state, assignee, work-notes text | ServiceNow Table API, as `ifabric.integration` (itil) |
| The delivery log | Delivery state, owner response, trusted note digests, earlier `ANALYSIS_*` runs | `PROOFLAB_DELIVERY_LOG` (the trust anchor) |
| Configuration | `SNOW_OWNER_USER`, `SNOW_INTEGRATION_USER`, `SNOW_AGENT_USER`; for the gateway backend `MODAAS_GATEWAY_URL`, `MODAAS_MODEL_ALIAS`, optional `MODAAS_API_KEY` | The runner's environment |

### 2.5 Model use

| Item | Value |
|---|---|
| Model | NVIDIA Nemotron, only through `modaas-agw`, under an approved alias (nano-9b, nano-3-30b or super-120b; ours: `nemotron-super-120b`) |
| Request | OpenAI-format `POST …/v1/chat/completions`; `temperature 0`, `max_tokens 900`, a 90 s timeout, no redirects, optional Bearer (gateway backend). On the AgentCore backend, our handler makes the same call (G-01) |
| What the model decides | Only `Measured vs limit`, `Evidence refs` and `Missing evidence`. Everything else is echoed and checked |
| Attempts | At most 2 per run |
| Reasoning | Stripped (`<think>` blocks; an orphan `</think>`; an unclosed `<think>` → no note). **Only SHA-256 hashes of the prompt and the raw response are stored** |
| Provenance | `x-modaas-action-id`, the model id, usage, latency and finish reason per attempt. The action id joins the analysis to the gateway span and the ledger (V6 needs it) |
| Guardrail | `content_filter` (HTTP 200 with `finish_reason`, or an error body) → BLOCKED, kept as adversarial evidence |
| Cost | About 3–4K tokens per attempt (an estimate: prompt + up to 900 out) |

### 2.6 Outputs

| Output | What | Where |
|---|---|---|
| **The ServiceNow work note** | One note, 16 `Key: value` lines after the marker `[iFabric Assurance Agent analysis]`: 9 checked facts, 3 judged lines and 4 code lines (Agent path, Policy alignment, Validation, Model provenance) | On the incident, written as `ifabric.integration` (shown as "iFabric Integration") |
| **The run record** | Facts given, per-attempt hashes and provenance, outcome and reason, the exact note and its SHA-256, `movement` and `policy_alignment` as computed at the time, start and finish UTC. No reasoning text | `evidence/servicenow/assurance-agent/*.json` |
| **The delivery-log line** | `ANALYSIS_<WRITTEN\|SKIPPED\|REFUSED\|BLOCKED\|FAILED\|UNVERIFIED\|NOT_DELIVERED>` with the backend, alias, action ids, run-record path and `note_digest`. A SKIPPED line carries the provenance of the run that wrote the note | `delivery-log.jsonl` |
| **The five sections** (at snapshot time) | <ul><li>`movement` (path, agents, zones, gateway crossings, M1 "no direct network → customer hop", M2 same run, M3 valid UTC);</li><li>`decision_trace` (agents, gateway, control, ServiceNow, owner, attempts, outcome);</li><li>`evidence` (kind, and "cited by the agent");</li><li>`policy_alignment` P1–P8;</li><li>`outcome_validation` V1–V6.</li></ul>Each check is pass, fail or unknown, and **unknown is never a pass** | `case_view()` → `ifabric.servicenow.case/v1` → `evidence/servicenow/cases/<finding>.json` |

The policy checks:
- **P1** verdict vs measured and limit;
- **P2** threshold version dated before detection (date granularity only; our T1/T2 check is the strong one);
- **P3** owner matches the register;
- **P4** notified (DELIVERED);
- **P5** response or silence recorded;
- **P6** not closed without a linked SATISFIED re-test at the same version;
- **P7** evidence attached;
- **P8** the route rule.

The validation checks:
- **V1** the run completed;
- **V2** the note's digest is in the log;
- **V3** the facts match;
- **V4** the cited refs exist;
- **V5** no reasoning stored;
- **V6** a governed backend (`modaas-agw:` or `agentcore:`) with an action id.

### 2.7 Outcome states, and what the dashboard shows
- `WRITTEN` or `SKIPPED`: green, but only if the note is present, complete, matches the finding id and its facts, and its digest is in our log.
- `REFUSED`, `BLOCKED`, `FAILED`: red, with the reason and the action ids.
- `UNVERIFIED`: amber.
- `pending`: amber. The panel turns it into a red `NO_ANALYSIS` after 5 minutes from delivery (`ifabric-case-panel.js:22, 200`).
- `NOT_DELIVERED`: grey.
- A note whose digest is **not** in our log (forged or edited) shows under the red heading "Note text — not written by the agent (untrusted)" (`ifabric-case-panel.js:150`).

### 2.8 How AICT sees it
- **What appears:** once the AgentCore runtime exists, AICT's connector (`SgcAictReadOnlyAccessRole`) lists it. After the next import (every 15 min, plus about 4 min), it shows in AICT **Inventory** as an AI Function named `ifabric_assurance_agent`, under the connection "iFabric Hackathon 2026". Arth presses "Execute Now" about 20 minutes before the slot.
- **The name:** the CR is `ifabric-assurance-agent`, and the operator turns it into the runtime name (V-01).
- **What AICT does not show:**
  - **usage:** its counter filters `InvokeAgent`, so it reads 0 for our `InvokeAgentRuntime` traffic;
  - **Monitor:** sessions appear for Managed agents only;
  - **the note or the case JSON;**
  - **an owner or a risk rating:** discovered assets arrive Unmanaged. Setting them is the pending D14 mirror and OC-23.
- **The gateway backend** makes no AICT asset at all (gap A10).
- **The panel's step 5** is an "AICT inventory entry" link (`SNOW_AICT_URL`), not a trace (gap A3).

### 2.9 How the dashboard uses it
- **G · Human Loop** (P1) embeds Arth's drop-in panel over `/api/v1/cases`. Each card shows the 5-step chain (finding → incident → owner response or silence → **Assurance Agent analysis** → AICT inventory entry).
- **Step 4** carries:
  - the status badge and four flag chips (complete, finding id matches, facts match, written by the agent);
  - group A "Checked against the finding" (9 facts) and group B "Nemotron's judgement" (3 lines);
  - the provenance line with the action id, and the written-at/by line.
- **Header pills:** `Policy x/y`, `Outcome <status>` and `N agents · M gateway crossings`.
- **The "Assurance analysis" block** holds the five sections.
- **Elsewhere in the console:**
  - the Answer view's human-loop line ("Assurance Agent WRITTEN (Nemotron, action …)");
  - Six Questions: INTEGRITY cites the note's SHA-256 in the delivery log; RECONSTRUCT puts the agent's run on the incident timeline;
  - the Live Monitor's `analysis` events;
  - the Adversarial matrix (H2: an injected ticket → REFUSED).
- **The data path:** the console never calls ServiceNow. The human-loop runner writes `case --out` snapshots, and the console serves only those listed in `pack-index.cases[]`, after a sha256 check.
- **The fallback:** `prooflab/servicenow/panel/index.html` opened from disk, with the file picker.

### 2.10 Exactly what it writes to ServiceNow
- **Only one thing:** one work note per finding incident and per successful run, through `PATCH /api/now/table/incident/<sys_id>` with the body `{"work_notes": <note>}` and **no other field** (`client.py:167-170`).
  - A re-run writes again only with `force`.
  - It is written as `ifabric.integration` (itil, OAuth client credentials).
- **Never:**
  - it never creates incidents: `notify()` does, with the finding block in the description and work notes, assigned to the owner, `correlation_id = finding_id`, `correlation_display = ifabric-prooflab`;
  - it never changes an incident's state, assignee, urgency or resolution;
  - it never touches other teams' records (its lookups filter `sys_created_by`), and never ServiceNow configuration, users or roles.
- **By rule (ours, and Arth's):**
  - it never runs on the register-approval incident;
  - it never runs on wiring-test incidents, except under a TEST log.

### 2.11 Where it sits in our frame
- **EP-13's loop:** it is part of EP-13's `callback()` loop. Nothing waits on it, and it is never in an agent's request path. Its own "refusal" (REFUSED or BLOCKED) only stops **its own note**. It refuses no agent work.
- **Not a control:** it is not in claim C-FM-01, and it is not a control or an evaluator. P1–P8 and V1–V6 describe a finding's human loop and the agent's own output, not a control verdict.
- **Its model calls** run under their own CID prefix, `ifabric-assure-…`. So C16's floor and C7's expected set never count them (G-03; OC-30).
- **It is an inventory component** (owner Arth, approver Sree; D23), so INV and AICT reconcile it. It is outside every control's `applies_to`.
- **It doesn't observe traffic.** The movement section checks only the `trace` our evaluator attaches (gap A17). So we must never feed it invented gateway crossings (G-04).

### 2.12 What is proven and what is pending (handoff-3 README §4; 08 §0)

| Part | Status |
|---|---|
| Incidents (create, read back, reuse, owner response); the full finding block in the description | Verified live (INC0010231, INC0010232) |
| The write path (note, readback digest, journal parse, idempotent re-run, five sections) | Verified live on 2026-10-05, with a TEST stand-in instead of the model (9/9) |
| The Nemotron call through `modaas-agw` | **Pending.** Blocked as written (V-02, V-03); our route is G-01 to G-05 |
| The AgentCore runtime + AICT discovery | **Pending.** Blocked as written (V-01); our route is G-01, G-02, then OC-26 |
| The code | 152 tests pass on Python 3.9 and 3.13, against a fake ServiceNow and a fake gateway over real HTTP |

## 3. Reconciliation matrix

"Ours" = `architecture/ARCHITECTURE.md` (§ numbers), `decisions.md` (D1–D14) and the feasibility reports. "Theirs" = handoff 3 (`01`–`09` = `evidence-console-plan/0N-…`; `08` also stands for the code). **Status:**
- **AGREE:** the same design.
- **CONFLICT:** both can't hold; the merge picks one.
- **COMPLEMENTARY:** each adds something the other lacks.

**Summary (68 rows, each counted by its first tag):** AGREE 23 · CONFLICT 21 · COMPLEMENTARY 24. The conflicts that matter are A1, B1, B2, C9, E1–E5, F3, F5, G6, J2 and J4; every one is settled by the captain's directions or the frame (§5.2).

### A. The dashboard / console

| # | Topic | Ours | Theirs | Status | Recommended merge: rationale, evidence |
|---|---|---|---|---|---|
| A1 | **Form** | One static, self-contained `dashboard.html` in the pack. The CLI is the control test. A 127.0.0.1 server is a cut-line extra only (§3.7; D1) | `prooflab console`: a stdlib server with PACK, LIVE and VIEWER (P2) modes, 11 views A–K plus the Control Room. `demo/index.html` is the reference implementation (02 §5; 06; 07) | CONFLICT | **Theirs**, as the captain directed. The CLI stays the control test, and the console's backend is our engine (G-08). D1's goal ("the app travels in the pack; no endpoint") is still met: the CLI and the MANIFEST travel in the pack, the console is loopback-only, and their VIEWER is P2 (D17) |
| A2 | Hosting | No server | The presenter's laptop, `127.0.0.1:8787`; a session token; a Host check (02 §10; 07 §1) | AGREE | It meets "no public endpoints" (V-04). The laptop only; never the IDE |
| A3 | Offline | Opens from the zip, no network | PACK mode is fully offline, with self-hosted fonts (AT-17) | AGREE | Self-host the fonts (G-09) |
| A4 | API | None | `/api/v1`: session, pack, ask, answer, auditor, runs, records, raw, cases, integrity, live, replay, session ledger, actions (07 §2) | COMPLEMENTARY | Adopt it, over the projected pack (G-07) and the answer composer (G-08) |
| A5 | Verdict logic in the UI | None: the JavaScript only filters (§3.7) | None, except "Verify without us": it recomputes C16 from raw records and shows "matches / differs" next to the recorded verdict, never replacing it (03 §5 rule 3) | AGREE | Keep their exception as a display-only recheck. Our Python rechecker (`prooflab/recheck/`) stays the independent recheck |
| A6 | Real time | `prooflab tail` (≥ 3 s) and `prooflab watch` (near-real-time C9 windows). Not claimed as the inline bonus (§3.7, §5.0) | The Live Monitor over `live/events.jsonl` (≤ 5 s); a Replay in PACK mode; inline admissions shown as diamonds (05 §3A; 06 §5A) | COMPLEMENTARY | One watcher (ours) writes their event types (G-10). The inline bonus is our EP-1 decision records. A replay is labelled REPLAY |
| A7 | Questions → answers | `prooflab query --control … --run/--window`, `--incident`, `--claim`, `--risk`, `--inventory`; exit codes 0/1/2 (§3.7) | A deterministic phrase grammar ("Show me control 16 for run FM-B"); `controltest`, `auditor`, `trail`; no LLM (06 §6) | COMPLEMENTARY | One engine, both surfaces. Their phrases are added; our extra verbs stay (G-08) |
| A8 | Operator actions | The live lane: one action at a time, each with the user's OK (§12.3) | A P2 actuator: a file queue, allow-listed argv, dual control, every transition recorded (02 §5.1; 07 §4) | COMPLEMENTARY | Keep it P2, or cut it. Each write still needs the user's OK. The kill-switch drill only on team-owned assets (V-37) |
| A9 | Design and accessibility | A static page; views listed (§3.7) | A full design system: tokens, tickmarks, the evidence lane, the ribbon, WCAG 2.2 AA, present mode (06 §1–§8) | COMPLEMENTARY | Adopt theirs as is |

### B. The evidence store, and logs → evidence

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| B1 | **The one store** | The platform ledger `audit-store` is the one live store for **our** records. Platform decisions are pulled into raw captures and, if D16 (a) is chosen, appended to the ledger as normalized `platform_decision` records. The snapshot is the pack (§3.5; D8, frame-decided; D16 pending) | Files are the store: raw → facts → records → assessments → findings → answers. The ledger is one captured surface among others (02 §1; 04 §1) | CONFLICT | **Ours** (the frame: every decision recorded into one store). Their layered tree becomes a **one-way projection** of our snapshot (G-07) |
| B2 | **C16's figure of record** | `aws/spans` by run id (30 days), through Logs Insights from the laptop (EP-2) | Gateway stdout, "only on ephemeral pod stdout", captured right after each run; durable fallback = the trace-id join (02 §3, §8; 04 §2.1) | CONFLICT (an outdated fact) | **Ours** (V-18). Stdout follow feeds only the live monitor (G-10) |
| B3 | Capture recipes, and where they run | Laptop collectors as WSParticipantRole, with cadences (§8) | 12 recipes (04 §2), run "in workshop-local/shell or the IDE" | COMPLEMENTARY | Their recipes, run on the **laptop only** (V-17). Pull `aict-invocations` at least 10 min after a run (V-21) |
| B4 | Capture metadata | A capture manifest: query, range, query id, time, rows, sha256 (§3.2) | A `.capture.json` sidecar that adds redaction counts, operator, pagination and source identity (04 §4) | AGREE (theirs is a superset) | Their sidecar shape (G-11) |
| B5 | Normalize and bind | `observations.jsonl` with deterministic ids; emitted records; the stitcher's link-gaps (§3.2, §3.6) | `facts/*.jsonl` with a quarantine, then a binder → `records/<C>/*.jsonl`, with "unbound" rows shown red (04 §5–§6) | COMPLEMENTARY | Their facts and records = our observations and stitched records, projected. Their "unbound" = our link-gap facts |
| B6 | Redaction | `cr_status.py` drops env and annotations; an exact-value scan (§9.3; corrected by 06 D4 to three paths) | Capture-time rules (bearer, env-secret, aws-key, bearer-url, span-content, reasoning), `test_redaction.py`, the pre-push scan (04 §3) | COMPLEMENTARY (+ a gap in theirs) | The **union**. Their env-name rule misses the two annotation copies (V-20) (G-11) |
| B7 | Integrity | Corroboration, AWS- and ServiceNow-set times, MANIFEST, S3 readback; never "tamper-proof" (§9.2) | MANIFEST, corroboration, S3 readback; no signatures; the ledger has no verify route (02 §7) | AGREE | Use Arth's `manifest.py` (G-19) |
| B8 | Pack layout | §9.1 | PRESENTATION_DAY §2 plus the console files (03 §1) | COMPLEMENTARY | The union tree (§5.3 (d), §9.1 row) |
| B9 | Provenance labelling | 9 values (§4.2) | 4 values; only ASSESSED counts (03 §3) | CONFLICT (vocabulary) | Ours internally; mapped on projection, with `provenance_detail` (G-07) |

### C. Contracts and schemas

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| C1 | **Evidence record** | `ifabric.evidence/1`: flat dotted keys, a superset of the slide's fields, the null rule, 14 `record_kind`s (§4) | `ifabric.evidence/v1`: the slide's field names, plus a nested `source`, `evidence_id`, `seal` and 6 `record_kind`s (03 §4.1) | COMPLEMENTARY (the same slide fields) | Ours is the production record. The projector emits theirs (G-07) |
| C2 | **Finding** | Arth's `finding.py`, "unchanged" (§3.8) | The same contract, plus the optional context `measured`, `limit`, `register`, `trace`, `retest` (08 §5.0) | AGREE | Our builder fills the context (G-04) |
| C3 | Assessment | The `Assessment` dataclass (§3.2) | `ifabric.assessment/v1`: `threshold.source_ref`, `register_sha256`, `population`, `series`, `retest_of` (03 §4.2) | COMPLEMENTARY | The same id format (`<ref>:<version>:<scope_kind>:<scope_id>:r<n>`). Projected |
| C4 | Answer | The engine's JSON + one CLI screen (§3.7) | `ifabric.answer/v1`, with a deterministic `answer_id` (03 §4.3) | COMPLEMENTARY | Our engine emits theirs (G-08) |
| C5 | Run and decision | Run index; handoff and judgment records (§4, §7.2) | `ifabric.run/v1`: journey, decisions, policy checks, outcome, lane (03 §4.4) | COMPLEMENTARY | Projected. Our handoffs map to `hop.via = orchestrator-handoff` (G-07) |
| C6 | Case, Assurance run, manifest | — | `ifabric.servicenow.case/v1`, `ifabric.assurance-agent.run/v1`, `ifabric.evidence-manifest/v1` | AGREE (adopted as is) | Pass unknown keys through unchanged (08 §6) |
| C7 | Run id and finding scope | `run.id` = the CID; the finding's `scope_id` = the CID (§3.8, §4.2) | `run.id` = an alias (FM-B), with `joins.cid`; `scope_id` = the alias (03 §2; 08 §5.0) | CONFLICT (minor) | The CID internally and in finding ids (D22). The alias comes from `run-ids.txt` in the projection; the grammar accepts both |
| C8 | Inline decision vocabulary | ALLOW or DENY, plus `inline.mode` (enforce or observe) (§3.2, §5.1) | ALLOW, ALERT ("would deny") or DENY, plus `reserved` and `committed` (03 §3) | COMPLEMENTARY | Map DENY in observe mode → ALERT (G-07) |
| C9 | **EP numbering** | EP-0 to EP-13; EP-1 = model call (the one wait); EP-13 = ServiceNow (§3.1) | EP1 = gateway, EP2 = agent adapter, EP3 = handoff admission, EP4 = ServiceNow, EP5 = kill switch, EP6 = tool Cedar (02 §3). The pitch and the ServiceNow section call ServiceNow "EP2" | CONFLICT | **Ours** (D20). The console renders EPs from data (G-09). Docs and pitch renumbered (G-16) |

### D. The control test

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| D1 | Engine | `query/engine.py` recomputes every verdict from the snapshot, with the frozen version bound to each record (§3.7) | The query engine composes deterministic answers; no LLM (03; 06 §6) | AGREE | One engine (G-08) |
| D2 | Date before test | T1 (S3 write-once: `LastModified`, `VersionId`) and T2 (ServiceNow approval), both earlier than the run's first span time (§3.3) | `frozen_at` and the approval time earlier than the first assessed run; `rule.date_before_scope` (03 §4.3; 05 §1) | COMPLEMENTARY | Ours computes it, theirs displays it. T2's source is Arth's approval incident (G-13) |
| D3 | Population and completeness | Expected, captured, missing; INDETERMINATE when incomplete (§3.4, §5) | Expected, observed, matched, missing, unmatched, duplicates, blocked, unmeasurable (04 §8) | AGREE | Projected into `population` |
| D4 | Tester vs evaluator | `Decision` vs `Assessment` (§3.2) | Two blocks: "Control test (tester)" and "Inline decisions (evaluator)" (03 §4.3) | AGREE | — |
| D5 | Six questions | §10.3, plus "WHO owns" from the inventory | `ifabric.auditor/v1`, with honest grades (03 §4.5) | AGREE | Add our ownership facts to the auditor file |

### E. The controls and the registry

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| E1 | **C16** | The floor at EP-2 is authoritative. EP-1's inline check runs in `enforce` or `observe` mode, with a safety ceiling. Named runs: N1 PASS, N2 BREACH (observe), N3 re-test (enforce, halted at the cap) (§5.1, §5.5) | `test()` and `admit()`; EP2 in the adapter plus **EP3 handoff admission**; FM-A, FM-B ("or the unmodified reference agents"), FM-C (a new generation), FM-D (05 §2) | CONFLICT | **Ours** (V-23, V-26). Their function names aren't created (G-19). FM-D's demo moment = our N3 / ADV-R-05 |
| E2 | C7 | Expected events from the gateway spans, `/modaas/evidence` refusals and the frozen workflow spec. Observed = what the adapters emit. The gap is measured on the agent clock (§5.2) | Expected = a 16-event-per-run spec in `expected/S*.yaml`; observed = ledger + hops; gaps on the ledger clock (05 §7) | CONFLICT | **Ours**: its expected set comes from outside the graded agents, from the gateway (frame; D4) |
| E3 | C9 | Latency Maximum + Errors + counts; a W2 window per run, plus an hourly roll-up; the baseline from 6 runs (§5.3) | Latency Maximum + Errors Sum per closed UTC hour; one finding per crossing; "start the baseline now" (05 §1, §7) | CONFLICT (the window and the volume); AGREE (the statistic) | **Ours** (V-28, V-30) |
| E4 | Register format and freeze | The kit's flat format; `versions/<v>.yaml` + sha256 (§3.3) | A nested YAML template with `status`, `frozen_at`, `builder` (`thresholds/register.template.yaml`) | CONFLICT (the format); COMPLEMENTARY (the fields) | **Ours**, plus their top-level keys and their content (G-14; V-29) |
| E5 | **T2 approval** | T1 (S3) dates the threshold; T2, the owner's ServiceNow approval, "not a Finding", corroborates (D5 as revised). The mechanism is pending Arth (§3.3; 08 SN-09) | An approval incident: a REG finding with `kind approval`, its own log, Sree's dated note, then `check` + `export` (`threshold-approval.md`) | CONFLICT (resolved by theirs) | **Theirs** (D19; G-13): it needs no new code and closes our spike. Amend §3.3 |
| E6 | Risk register, AI inventory, INV | `risks.yaml` (5×5 matrix, appetite, residual), `inventory.yaml`, and the optional INV control (§3.9, §3.10, §5.6) | Inherent and residual ratings on the register card; the risk-matrix hint for the cap (05 §1; 06 §5.6) | COMPLEMENTARY | **Ours.** The projector shows the ratings in the Register view. INV is answered by the CLI (their schema has no INV) |
| E7 | Cap derivation | Appetite first (the upper bound); the pilots give the lower bound; never derived from S2 (§5.1, §5.4) | "Above the largest healthy run, with stated headroom, so that a looping run breaches"; justified with the 5×5 matrix (05 §1) | AGREE (the method); minor difference | Ours; theirs is consistent with it as the lower bound |

### F. The agents

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| F1 | The `ifabric-` trio | A new trio cloned from the reference agent, on super-120b. J2 = structured judgment checked by code. Real evidence emission (§7.1; D7) | Rebuild `ifabric-*` (A6): a structured final answer, ledger fields, EP2 admission (05 §4) | AGREE | Ours (D7). The build path comes from 05 (a one-file bundle, unique tags; AR-02/03/05) |
| F2 | The decision schema | `disposition`, `deciding_evidence`, `reversible_step`, `reason` (§7.1) | `disposition` (7 values), `rationale` ≤ 400, `cited_evidence`, `named_evidence_needed`, `reversible_action`, `proposed_action`, `handoff_to` (05 §4.1) | COMPLEMENTARY | Ours, plus two additive fields; the projector maps the names (G-07) |
| F3 | The orchestrator | `prooflab run` (EP-5): records only, never blocks, carries the tally (§7.2) | `ifabric-run` with **EP3 admission**, plus `held-actions.json` for S3 (05 §3) | CONFLICT | **Ours** (V-23, V-24) |
| F4 | AP-v1 policy checks + outcome validation | M3 disposition matching (a C9 diagnostic) only (§5.3) | A host-side checker (P-EVID-01 … P-ACTION-06) and outcome validation against `expected/scenarios.yaml` (05 §5–§6) | COMPLEMENTARY | Adopt as P1 if D21 = yes (G-17); never fed into a control verdict |
| F5 | The S2 fix | J2 precedence rules (gather-evidence on empty evidence or ambiguity) (§7.1) | P-AMBIG-02 in the prompt, plus a **per-invocation call limit** (05 §4.1) | CONFLICT (the call limit) | Ours; the call limit is rejected (V-25) |
| F6 | **The Assurance Agent** | Absent. §3.10 and §10.4 still name a ServiceNow-native L3 agent | A Nemotron reviewer on AgentCore that writes one validated note per finding incident (08) | COMPLEMENTARY (packaging BLOCKED as written) | **Theirs** for the logic (code unchanged); **ours** for the packaging and deployment (G-01 to G-03; V-01 to V-03) |

### G. The ServiceNow flows

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| G1 | Incidents | `publish()` → `notify()` for BREACHED, ESCALATED and monitoring gaps; never SATISFIED (§3.8) | The same, with the full finding block in the description (08 §1) | AGREE | Their code; our builder (G-04) |
| G2 | **Notes (the Assurance analysis)** | None | One validated note per finding, after DELIVERED (08 §5.1) | COMPLEMENTARY | Our runner calls it (G-05) |
| G3 | The owner's response | `check --cutoff`; bugs (a) and (b) accepted as risks (§3.8) | `check` on a short loop; RESPONDED is sticky (08 §5.4, gap 12) | AGREE (+ CAVEATs) | Process guards (V-12, V-13; G-05) |
| G4 | Closure | Only by a later SATISFIED re-test (§3.8) | The same, plus the `retest` key and P6 (08 §16) | AGREE | Our builder writes `retest`; **the owner resolves in the UI** (V-14) |
| G5 | Approvals (T2) | See E5 | See E5 | CONFLICT (resolved by theirs) | G-13 |
| G6 | ESC and held actions | The ESC finding from J2's `escalate` (§3.8) | S3 escalation → EP4 `BUILT_WAITING`, with held actions (02 §3.1) | CONFLICT | ESC finding only; EP-13 `ALERT_ONLY` (V-24) |
| G7 | AICT | Discovery and observability only, at L2–L3; usage 0 and Monitor are gaps; Arth exports into `servicenow/aict/` (§3.8) | The same, plus `ifabric_assurance_agent` in Inventory (08 §15) | AGREE (+ COMPLEMENTARY) | Add the AWS half we can collect ourselves (G-12). Correct gap A1 (V-11) |
| G8 | Volume and cadence | One finding per control × run; never an idle-hour gap (§3.8; 08 SN-08) | One finding per C9 crossing window; case snapshots every 10–30 s (05 §3A, §7) | CONFLICT (volume); CAVEAT (load) | Ours, with the tiered snapshot cadence (G-05; OC-28) |

### H. Security

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| H1 | Who holds which secret | The runtime: the gateway key and the ledger token (platform-injected). The laptop: AWS and ServiceNow credentials. The dashboard: nothing (§8) | The same split; the console process holds nothing (02 §6.2) | AGREE | Add the human-loop runner as the only holder of the ServiceNow credentials. The Assurance runtime holds none (G-02) |
| H2 | Console zero trust | — (no server) | NIST 800-207 mapping, CSP, CSRF, Host allow-list, a one-time token, a path allow-list, the secret-env refusal (02 §6; 07 §3) | COMPLEMENTARY | Adopt, with the extended env list (V-04) |
| H3 | Token redaction | Three paths + the exact-value scan (06 D4) | Name-keyed env rules, then the exact-value pre-push scan over the pack (04 §3) | CONFLICT (their capture rule is incomplete; their scan gate would catch it) | The union, dropping all three paths at capture (G-11; V-20) |
| H4 | Transport | Plain HTTP between agents and the gateway, recorded as gap 9 (§6.3) | The same, recorded as a platform gap (02 §6) | AGREE | But their IDE proof (08 §5.2) would send the key over plain HTTP from outside (V-03) |
| H5 | Data minimization and reasoning | Digests, not content; span content summarized (§9.1) | Drop span content; never store or show reasoning (02 §6.3) | AGREE | Also switch on our agents' span redaction (V-40) |

### I. Build order and acceptance

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| I1 | Principles | C16 end to end first; cut lines P0–P5 (§12.4) | "Controls before console"; cut console scope, never control scope; P0 → P1 → P2 gates (09 §1) | AGREE | — |
| I2 | Schedule | A critical path from 21:00 UTC with the live lane, the freeze line and named milestones (§12.1) | Tracks A–D from 19:00 UTC, with hour budgets (09 §1–§3) | CONFLICT (clock); COMPLEMENTARY (Track B) | **Ours** for the live lane and the clock (V-22, V-30). Their Track B (console) runs in parallel against the fixtures; Track C (Arth) is folded in (§5.5) |
| I3 | Acceptance | Per-workstream gates, the R-J tests, two rehearsals (§12.2) | AT-01 … AT-22, with AT-P0 / AT-P1 / AT-final gates (09 §4) | COMPLEMENTARY | The union: their AT-xx for the console and the pack, our gates for the controls |
| I4 | Clock risks | Credentials expire at 06:29:19Z; the `v1` freeze line (T1 dates the threshold, T2 corroborates: D5 as revised); one person gates the night; 15 min of buffer after the 23:45 re-timing (08 OP-01, HL-03; §12.1) | Not covered | COMPLEMENTARY (ours) | Ours (§5.5) |

### J. The pitch and the demo

| # | Topic | Ours | Theirs | Status | Recommended merge |
|---|---|---|---|---|---|
| J1 | Run of show | The judging map (§10); no formal script | An 8-step guide, a 15:00 timer, Present mode (`presentation/JUDGING-DAY-GUIDE.html`; 06 §7) | COMPLEMENTARY | **Theirs** as the run of show, filled with our runs and our claims (G-16) |
| J2 | **The second EP** | The same `c16` module at EP-1 (`evaluate`) and EP-2 (`pull`) (§11) | Guide step 7: "the same rule-checker used in two places". The ServiceNow section and the L2/L3 script: "the ServiceNow human queue is our second enforcement point" | CONFLICT (inside their own package) | **Ours**, which matches their guide (V-27) |
| J3 | The inline beat | N3: halted at the cap, with its DENY record; `prooflab tail` live (§11.1) | FM-D: "watch EP2 refuse call c-0014 before the cap" (Live or Replay) | AGREE (substance) | Our N3 / ADV-R-05, shown in their Live or Replay view |
| J4 | Close-the-gap story | The reference S2 (EXPLORATORY "before", 1,999,001 tokens) against the `ifabric` agents' judgment (§5.5) | FM-B guessed and FAILED → FM-C, after a fix, VALIDATED; both `ifabric` runs (guide step 6) | CONFLICT | Ours (D7, D9). The Agent Trail shows the reference run greyed as EXPLORATORY |
| J5 | L1–L3 | L3 = "Arth's ServiceNow-native agent" (§10.4, stale) | L3 = the Nemotron Assurance Agent chain; L2 = AICT + the ledger (01 J-01–J-03) | CONFLICT (ours is stale) | Theirs (§5.3 (d)) |
| J6 | Honesty | One honest failure; INDETERMINATE is never a pass; the gap list (§9.4, §15) | The same; also "nobody checks their own work: Sree approves, the builder builds, Arth tests" | AGREE (+ CAVEAT) | Separation of duties must be stated truthfully (V-41) |

## 4. Vetting their platform assumptions against the verified facts

**Status values:**
- **BLOCKED (as written):** a verified fact, or the captain's frame, forbids it as written. The glue or the minimal decision is named.
- **CAVEAT:** a procedure, a configuration or our glue makes it work, with Arth's code unchanged.
- **SPIKE:** only a live test decides.
- **SUPPORTED:** it works as written.

**Fact sources:**
- `05` / `06` / `07` / `08` = `architecture/work/0N-feasibility-*.md` (row ids such as AR-03, C5, GS-25, SN-05);
- `PVF` = memory `platform-verified-facts`;
- `SNC` = memory `servicenow-context`;
- `PH` = `PLANNING-HANDOFF.md`;
- `code` = handoff-3 `code/prooflab/servicenow/*`, read for this file.

**Counts (42 rows):** BLOCKED as written 10 (5 by a verified platform, code or kit fact: V-01, V-02, V-03, V-14, V-29; 5 by the captain's frame or D9: V-23 to V-27) · CAVEAT 20 · SPIKE 3 · SUPPORTED 9.

### 4.1 The headline items

| # | Their assumption (where) | Verified fact (source) | Status | Consequence / glue |
|---|---|---|---|---|
| **V-01** | **Assurance Agent on AgentCore** "through the normal `new-agent.sh` flow (Strands template), name `ifabric_assurance_agent`". The handler body is `from prooflab.servicenow.nemotron import GatewayAnalyzer …` "inside the image" (08 §5.3 steps 1–2; TEAMMATE_ACTIONS step 9) | <ul><li>**One-file build:** `build-agent-image.sh:171-172` embeds ONE file (`gzip -9nc \| base64`; `COPY agent.py`), and the buildspec cap leaves **24,049 chars** of gz+b64 source (05 AR-03). A module import that isn't in the image passes READY and approval, then dies with an ImportError at the first invoke (AR-03).</li><li>**`new-agent.sh`** copies the template over `agent.py` and leaves `dependsOn.tools` empty (AR-02).</li><li>**The tag trap:** a source file named `agent.py` with no `IMAGE_TAG` overwrites the reference tag (AR-05).</li><li>**Names:** Kubernetes names can't hold `_`, so the CR must be `ifabric-assurance-agent` (AR-01).</li><li>**Measured here (gz+b64):** `nemotron.py` 4,112 chars; all 10 `prooflab/servicenow` modules 34,176 (> 24,049)</li></ul> | **BLOCKED (as written)** | **Packaging glue, code unchanged:** G-01 (a one-file handler named `ifabric-assurance.py`, a size gate, a Docker smoke) and G-02 (our generator wrapper + `build-agent-image.sh` with a unique `IMAGE_TAG`; CR `ifabric-assurance-agent`). The handler needs **none** of Arth's modules: the validation, the writing and the five sections all stay on the laptop in `run_assurance_agent()` |
| **V-02** | **The Nemotron call path inside the runtime:** `GatewayAnalyzer.from_env()` with `MODAAS_GATEWAY_URL` / `MODAAS_MODEL_ALIAS` "in the AgentConfig", "in-cluster `http://…svc.cluster.local` or `https://…`" (08 §4, §5.3) | <ul><li>**What runtimes receive:** `OPENAI_BASE_URL = http://<public ELB>:8081/v1` and `OPENAI_API_KEY` (PH §5.1; `notes/platform-observations.md:130`; 05 AR-09). `OPENAI_*` names are reserved and can't be overridden (AR-14, GS-18).</li><li>**The URL check:** `_check_gateway_url` (`nemotron.py:79-86`) refuses `http` to a host that isn't loopback or `*.svc` / `*.cluster.local`. A runtime can't resolve cluster DNS.</li><li>**TLS:** `:8443` is self-signed, with SAN `<PERIMETER-HOST>` (07 GS-25), so `https://` fails verification.</li><li>**The key:** `MODAAS_API_KEY` in env would put the gateway key into the CR spec, which every participant can read (PH §8)</li></ul> | **BLOCKED (as written)** | G-01's handler calls the injected `OPENAI_BASE_URL` + `/chat/completions` with the injected key, as every agent does. 08 §5.3 allows this explicitly ("a Strands model provider pointed at `modaas-agw` … equally fine, as long as the output keeps this contract"). The governed path itself is SUPPORTED (V-08). Plain HTTP stays a recorded platform gap (gap 9) |
| **V-03** | **The first live proof of the Nemotron call** "in the workshop IDE" with `MODAAS_GATEWAY_URL=<the modaas-agw URL your agents use>` (08 §5.2; TEAMMATE_ACTIONS step 3) | <ul><li>**It fails as written:** the same URL check, so `analyze` exits 2 ("gateway URL must be https or cluster-internal http").</li><li>**The key would travel in clear:** that URL is plain HTTP to a public ELB, against the team rule never to send the gateway key over plain HTTP (`notes/servicenow/raw/D-docs-and-rails.md:518`).</li><li>**The CLI can't switch:** `analyze` always builds `GatewayAnalyzer` (`cli.py:106-115`); it has no AgentCore switch</li></ul> | **BLOCKED (as written)** | Prove it through the **AgentCore backend** instead (G-03 + G-05): the laptop never holds the gateway key, and the run is the AICT-visible form (D18). Fallback: a loopback `kubectl port-forward` (G-15; **SPIKE** OC-24, which needs the captain's OK) |
| **V-04** | **Console serving:** `127.0.0.1:8787` only, a one-time token → an HttpOnly cookie, a Host allow-list, CSP, no secrets, "no public endpoints, no tunnels" (02 §10; 07 §1, §3) | <ul><li>The platform rule allows no public endpoints (PH §8; 02 R-P-07). A loopback bind meets it.</li><li>The IDE is reached through a CloudFront bearer link (IdeUrl), which is a secret (PH §8)</li></ul> | **SUPPORTED** (CAVEATs) | Run it on the presenter's laptop **only, never in the IDE**. Its secret-env refusal list is missing `OPENAI_API_KEY`, `AGENTCORE_GATEWAY_MCP_TOKEN`, `AWS_SESSION_TOKEN` and `SNOW_CLIENT_ID`; add them (G-09) |
| **V-05** | **Console API exposure and the panel feed:** the console makes no AWS or ServiceNow call; `/api/v1/cases` serves the listed snapshots; "LIVE: `IFabricCasePanel.poll(el, url, 10000)`" (07 §2; 08 §7.1–§7.2) | <ul><li>**The envelope:** the console API returns `{"ok","data","error","meta"}` (07 §2), but `poll()` passes the response body to `render()`, which treats a non-array as **one case** (`ifabric-case-panel.js:439-441, 472-480`).</li><li>**Hard-coded EPs:** the demo hard-codes "ifabric-run · EP3 handoff · evaluate()" and "· EP3" on the journey (`demo/index.html:210, 287, 351`), against their own J-14, "the console … never asserts" an EP</li></ul> | **SUPPORTED** (CAVEATs) | <ul><li>Fetch, then `render(el, json.data)` on a timer;</li><li>render the architecture view and the EP table from `pack-index.enforcement_points` and our one-page (G-09).</li></ul>No change to Arth's panel |
| **V-06** | **AICT discovers `ifabric_assurance_agent`** about 20 min after creation ("Execute Now" to refresh); step 5 = "AICT inventory entry"; Monitor and the usage counter are gaps (08 §5.3 step 5, §15) | <ul><li>**The AWS side is proven:** AICT calls `ListAgentRuntimes` every 14–16 min and `GetAgentRuntime` on new runtimes (08 AI-01, AI-02).</li><li>**Scope:** discovery covers AgentCore runtimes and gateways only (SNC; PH §5.8).</li><li>**Usage:** the usage count is 0, because its query filters `InvokeAgent` (AI-03).</li><li>**Monitor:** it covers Managed agents only.</li><li>**Discovered records** arrive Unmanaged, with no owner (ARCHITECTURE §3.10).</li><li>**The ServiceNow half** of the import is per Arth only (AI-02)</li></ul> | **CAVEAT** | Claim it as **inventory by name** only. Collect the AWS half ourselves (G-12). Arth checks `my_agent` now (OC-26). The CR name uses hyphens (V-01) |
| **V-07** | **ServiceNow writes:** OAuth client credentials as `ifabric.integration` (itil); incidents plus one PATCH of `work_notes` per finding, from the backend only (08 §2, §4; handoff 1) | <ul><li>**Auth:** Basic auth returned 401; OAuth works (SNC; gap A5).</li><li>**Credentials:** they are with Arth or Sree and not yet on the laptop (08 SN-02).</li><li>**The shared instance:** the Global OAuth property on it is an accepted risk (PH §4.4).</li><li>**Reads stay ours:** `find_incidents` filters `sys_created_by` (`client.py:147-152`)</li></ul> | **CAVEAT** | Put the credentials in `~/.prooflab-snow.env` (mode 600) on the laptop before 03:30 UTC; run `selftest` before each batch (G-05). The runtime never holds ServiceNow credentials (G-02) |

### 4.2 The rest

| # | Their assumption (where) | Verified fact (source) | Status | Consequence / glue |
|---|---|---|---|---|
| V-08 | Model calls go only through `modaas-agw`, with a Nemotron alias; never Bedrock directly (08 rules; J-53) | <ul><li>The runtime role explicitly denies InvokeModel and InvokeGateway; the participant role explicitly denies InvokeModel (PVF).</li><li>`nemotron-super-120b` is Approved and not paused (05 AR-28)</li></ul> | SUPPORTED | Use the alias `nemotron-super-120b` (the trio's model) |
| V-09 | Provenance through `x-modaas-action-id` on the analysis call (08 §2, §5.6) | The header is set by a gateway response transformation on every listener. It is verified on non-streaming calls; SSE is untested (05 AR-13) | CAVEAT | G-01 is non-streaming. V6 needs an action id in the attempts (`assurance_checks.py:163`) |
| V-10 | `MAX_TOKENS = 900` produces a full 16-line note (`nemotron.py:30`) | Nemotron may spend tokens on reasoning first. `strip_reasoning` turns an unclosed `<think>` into "no note" → REFUSED (`nemotron.py:59-76`). Untested live | **SPIKE** (OC-25) | On the AgentCore path, the limit lives in **our** handler (G-01). Never edit Arth's prompt |
| V-11 | Gap A1: "AICT discovers AgentCore runtimes, Bedrock agents and SageMaker models" (`evidence-pack/gap-list.md`) | Bedrock agents and SageMaker are AccessDenied for the connector role (SNC; PH §5.8). Their own 08 §15 already corrects it | CAVEAT (text) | Fix A1 in the merged gap list (G-16) |
| V-12 | `notify --dry-run` "reuses INC0010232 read-only → DELIVERED (writes nothing)", used on purpose to make P4 pass (08 §5.2) | Bug (a) is still present: `if existing: return _confirm(...)` runs before `if dry_run` (`notifier.py:134-138`). It logs INTENT + DELIVERED and is not offline (08 SN-06; SNC) | CAVEAT | Safe only with the TEST log, as §5.2 does. The runner refuses `--dry-run` unless the log path is under `wiring-tests/` (G-05) |
| V-13 | `check` detects the owner's reply; "a logged RESPONDED is sticky" (08 §5.4, gap 12) | Bug (b) is still present. A `sys_journal_field` read that returns HTTP 200 with 0 rows keeps `readable=True` (`notifier.py:190-216`). The owner is then seen only as the last updater, so a later update by anyone turns her reply into a false NO_RESPONSE_OBSERVED after the cutoff (08 SN-05) | CAVEAT | **Process rule:** after the owner responds, nobody else updates our incidents until `check` has logged it. `check` runs on a 60–120 s loop. `export` right after each owner note (G-05) |
| V-14 | At closure "the integration user resolves the incident with a note `closed by re-test …`" (08 §16) | `ServiceNowClient` has only create, the display reads and a `work_notes`-only PATCH (`client.py:154-170`). There is no state change in the code | **BLOCKED (as written)** | **The owner resolves the incident in the UI herself,** after G-04 has written `retest` into the finding file; it then also counts as her response. Refresh the case snapshot after `check` |
| V-15 | T2 via an approval incident: a `REG` / `kind approval` finding, Sree's "APPROVED … sha256 …" work note, then `check` → RESPONDED and `export`, with its own delivery log (`thresholds/threshold-approval.md`) | It needs no new code. It closes our open SN-09 spike, where the package had no approval-record code (08 SN-09). Detection depends on Sree being the last updater (bug (b)) | CAVEAT | G-13. Amend ARCHITECTURE §3.3's "not a Finding" text (D19). Never `analyze` it |
| V-16 | The finding context limits: `trace` ≤ 200 steps; text ≤ 200 chars, no newlines; refs echoed exactly (08 §5.0) | <ul><li>**Trace:** a trace over 200 steps raises in `finding_from_dict` (`finding_context.py:98-99`), so `notify` fails. The reference S2 run had 353 gateway spans (PVF).</li><li>**Refs:** the model's ref echo is split on `;` (`assurance_agent.py:99-102`)</li></ul> | CAVEAT | G-04: cap the trace while keeping the M1 route-rule semantics; at most about 8 refs, each free of `;` |
| V-17 | The capture recipes (`aws logs filter-log-events …`) run "through the workshop shell (`workshop-local/shell` or the IDE)" (04 §2; 02 §10) | The IDE role has no `FilterLogEvents`, `StartQuery` or `GetQueryResults`; WSParticipantRole (the laptop) has them (PVF; 06 A1) | CAVEAT | **Laptop only** (or CloudShell). It is already our D11 |
| V-18 | C16's figure of record is gateway stdout, "**only on ephemeral** pod stdout"; the durable fallback is the `/aws/modaas/gateway` trace_id ↔ `/modaas/evidence` join (02 §3, §8; 04 §2.1) | `aws/spans` holds `modaas.run_id` = the CID plus tokens for 30 days, equal to the stdout figures on every run checked (PVF; 06 A4) | CAVEAT (outdated) | Keep **ours:** the EP-2 pull over `aws/spans`. Stdout follow feeds only the live monitor (G-10). Stdout values are quoted (`modaas.run_id="<CID>"`, PVF), so the parser must strip the quotes |
| V-19 | The watcher polls the ledger's `/records?cid=` every 3 s during runs (05 §3A) | The ledger is single-threaded, 256Mi, and parses the whole file on every GET. A GET blocks POSTs (05 AR-21; 06 C5) | CAVEAT | No faster than every 3 s, per CID, and never a full GET during a run (G-10) |
| V-20 | CR status capture: `kubectl … get agentconfig,modelconfig,toolconfig -o json`, with an `env-secret` rule on env entries named `*TOKEN*` / `*KEY*` (04 §2.9, §3) | <ul><li>**Three copies:** the ledger token sits in three paths per AgentConfig: the env map, plus two annotations that hold the whole spec as a **JSON string** (`kubectl.kubernetes.io/last-applied-configuration`, `kopf.zalando.org/last-handled-configuration`) (06 D4).</li><li>**Runtime reads:** `get-agent-runtime` returns the whole env (05 AR-30)</li></ul> | CAVEAT | Their name-keyed rule alone misses two of the three copies. Their own gate, the exact-value `pre-push-secret-scan.sh` over the pack (04 §3), would catch them and **fail the pack**, not leak the token. Drop all three paths at capture (our filtered `cr_status.py`) so the gate passes (G-11) |
| V-21 | `aict-invocations`: "No run id: join by time window and runtime ARN" (04 §2.10) | `responseElements` carry `baggage` (the CID) and `runtimeSessionId`. `eventTime` is the **end** of the call. Delivery comes 19–328 s late (05 AR-20; 06 B6) | CAVEAT | Join exactly on CID + session. Pull at least 10 min after the run (G-12) |
| V-22 | Track A works through the night from 19:00 UTC, and `prooflab watch` runs all night (09 §1–§2) | The AWS credentials expire at **2026-10-06T06:29:19Z** (08 OP-01). Every pull, kubectl call and secret scan stops then | CAVEAT | One refresh between 03:30 and 06:29 UTC. The watcher records a monitoring gap on `ExpiredToken` and stops (ARCHITECTURE §8) |
| V-23 | EP3: a handoff admission `evaluate()` in `ifabric-run` that "can stop the run between agents" (02 §3; 05 §2–§3) | The captain's frame: handoffs are emit-only, and there is exactly one in-path question (C16 at EP-1) (ARCHITECTURE §2.2) | **BLOCKED (frame)** | Not built. Our EP-5 records handoffs and never blocks (D20) |
| V-24 | EP4 `BUILT_WAITING`: the S3 change is held in `held-actions.json` until the owner decides (02 §3.1) | <ul><li>The agents have no change tool, so "executing" an approval is a recorded no-op (their own 02 §3.1).</li><li>The frame says ServiceNow records and never holds work (ARCHITECTURE EP-13)</li></ul> | **BLOCKED (frame)** for the claim | EP-13 is rendered `ALERT_ONLY` (their option (d), which they call honest) |
| V-25 | S2 fix: "a per-invocation model-call limit (e.g. 3) stops the IT loop" (05 §4.1) | It would be a second in-path refusal, outside the frame's one question | **BLOCKED (frame)** | Breach runs are bounded by the observe-mode safety ceiling (ARCHITECTURE §5.1) |
| V-26 | Named runs: FM-B "or with the unmodified reference agents"; FM-C = the re-test after "a new agent generation, approved by Sree" (05 §2) | <ul><li>**D9 (decided):** PASS and BREACH run on the same `ifabric-` agents, and the reference trio is never assessed.</li><li>**A rebuild** is a new treatment: re-approval, and new C9/C16 baselines (02 §3; 05 AR-15)</li></ul> | **BLOCKED (D9)** / CAVEAT | Use ours, N1–N9. The C16 re-test is N3, the same agents in `enforce` mode (ARCHITECTURE §5.5) |
| V-27 | "The ServiceNow human queue is our second enforcement point (EP2)" (`servicenow-section.md` fact 2; `pitch-L2-L3-script.md`; `running-order-15min.md`) | <ul><li>**The frame and our §11:** the second EP is the same `c16` module at EP-1 and EP-2.</li><li>**Their own documents disagree with it:** their 02 §3/§9 ("a notify-only incident cannot refuse") and their guide's step 7 ("the same rule-checker used in two places")</li></ul> | **BLOCKED (frame)** | Re-pitch as "the same finding contract routed to the human approval queue through `callback()`: records only" (G-16) |
| V-28 | C9 per closed UTC hour per runtime, with one finding per crossing window (05 §7; TEAMMATE_ACTIONS step 7) | That gives up to about 30 incidents on a shared instance, mostly idle-hour "gaps". An idle hour is not a gap (08 SN-08) | CAVEAT | Use ours: one window per run (W2), plus an hourly roll-up for window questions (ARCHITECTURE §5.3) |
| V-29 | The register template has nested maps (`justification:`, `governance:`) and `- control_ref:` list items (`thresholds/register.template.yaml`) | The kit's no-PyYAML fallback parser in `evaluate.py` needs flat entries keyed by `- control_id:`, and `submit.sh` packages `register.yaml` (ARCHITECTURE §3.3 rules 1–5) | **BLOCKED (as written)** | Keep our flat format. Adopt their top-level keys and their content (G-14) |
| V-30 | A0: "start C9 baseline capture **now**" (written about 19:00 UTC, before our agents exist) (09 §2; 05 §1) | The C9 baseline must come from the **frozen `ifabric-` agents**: six BASELINE runs, frozen in `v1.1` (D3, D9) | CAVEAT | Earlier hours stay EXPLORATORY context; the assessed baseline follows ARCHITECTURE §5.4 step 7 |
| V-31 | The console and Arth's package run on stdlib Python 3.9+ (07 §1; 08 §3) | `/usr/bin/python3` is 3.9.6; Arth's 152 tests pass on 3.9 and 3.13. The agent images need ≥ 3.10, but only for the SDKs (05 AR-29; 08 PY-01) | SUPPORTED | Run the tests in the 3.9 venv (08 PY-02) |
| V-32 | Assurance calls fit the ceiling ("stay under one model request per second", J-57) | 100 req/min and 2.5M tokens/h (PVF). An analysis is at most 2 attempts of about 3–4K tokens each, over about 8–15 incidents (08 SN-08) | SUPPORTED | Under 0.12M tokens in total |
| V-33 | The console contracts accept our data "additively" (03 §5) | `contracts.schema.json` enums (read for this file): `provenance` has 4 values; `controlRef` is C7/C9/C16/ESC (no INV, no APPROVAL); `evidenceRecord.record_kind` has 6; `enforcementPoint.kind` has 6. `hop.via` already has `orchestrator-handoff`, and the EP `id` is free text | CAVEAT | The mapping tables in G-07, with additive `*_detail` keys. INV and EP-0 are answered by the CLI |
| V-34 | Case snapshots every 10–30 s for every finding (05 §3A; 08 §7.1) | Each `case_view` makes about 4–6 Table API reads (`case_view.py:117-145` → `check_response`, `find_incidents`, `get_incident_display`), on a shared instance | **SPIKE** (OC-28) | Use G-05's tiered cadence |
| V-35 | One delivery log, the trust anchor (08 §5.6, §7.1) | Its default path is **relative** (`cli.py:38`), so a call from another directory starts a second log, and genuine notes then show red (08 SN-07) | CAVEAT | An absolute `PROOFLAB_DELIVERY_LOG`, with one owner process (G-05) |
| V-36 | `submit.sh <team>` → S3 → readback; the console runs on the downloaded copy (09 §5; PRESENTATION_DAY §3) | Participant PutObject is untested. `submit.sh` prints a presigned URL (06 D1, D3, S2) | **SPIKE** | Run 06's S2 probe before the freeze. Never record the URL |
| V-37 | The kill-switch drill on a team-owned ToolConfig; EP5 = `spec.paused` (02 §3; 07 §4) | <ul><li>A tool pause gives a 404 within about 1–7 s (07 GS-13).</li><li>An **AgentConfig** pause is a record, not a stop (GS-14).</li><li>A model pause hits every agent.</li><li>Every write needs the user's OK (PH §8)</li></ul> | CAVEAT | Team-owned tools only, in the live lane. The actuator stays P2 |
| V-38 | Their §9 corrections to the playbook (02 §9) | They match our verified facts:<ul><li>X-Ray is a durable exporter;</li><li>undeclared tool calls are allowed and Cedar sees one principal;</li><li>the ledger has no verify route;</li><li>all three reference scenarios fail by construction;</li><li>kill-switch latencies;</li><li>the baggage CID;</li><li>the C9 statistic Maximum + Errors;</li><li>`ifabric-` CR names;</li><li>no per-run halt;</li><li>AICT gaps;</li><li>approvals without re-approval;</li><li>refusals logged as ALLOW;</li><li>the caps measured from our own runs (PVF; PH §4.2)</li></ul> | SUPPORTED | One nuance: X-Ray keeps the ids as metadata and truncates long runs (S2: 22 of 174), so `aws/spans` is the complete source (PVF) |
| V-39 | Six questions: WHO PARTIAL (one shared identity), AUTHORIZED joins the PDP to the gateway line, APPROVED lists approvals of every asset actually called, INTEGRITY = MANIFEST + corroboration + S3 (03 §4.5) | The same as our §10.3 (PVF; 07 GS-22) | SUPPORTED | Add our WHO-owns facts (the inventory join) to the auditor file |
| V-40 | Span content is dropped at capture (`events[].attributes.content`) (02 §6.3; 04 §3) | `chat` spans carry the system prompt and customer records (PVF). Our agents can switch redaction on at the source (05 AR-25) | SUPPORTED | Do both: the source switch in our agents and the capture rule |
| V-41 | "Nobody checks their own work: Sree approves, the builder builds, Arth tests" (guide; J-47) | Our record says the owner also builds and also rates the risks she owns; GRC is vacant (ARCHITECTURE §15.2; 08 HL-04) | CAVEAT (honesty) | The console's People panel must show the real `builder` from the register. Keep the separation-of-duties gap (G-14, G-16) |
| V-42 | The Evidence Pack is "kept for 7 years"; the judges read S3 (PRESENTATION_DAY; 02 §7) | The account is destroyed when the event ends. The bucket has versioning but no Object Lock (PVF; 06 D2) | SUPPORTED | Retention is a statement in the README, not a platform property; say so. Export before teardown |

## 5. The recommended integrated architecture

**Rules for the merge** (the captain's directions, 2026-10-05):
1. **Arth's code ships unchanged:** `prooflab/servicenow/*` and `prooflab/tests/*` as in handoff 3 (152 tests), the panel files, `tools/manifest.py` and `tools/sn_roundtrip_test.py`. Every boundary change is **our** glue, listed in §5.4 as a candidate task.
2. **Arth's side is the master** for the ServiceNow flows, the Assurance Agent and the dashboard. **Ours is the master** for the controls, the evidence, the registry and the agents. Where a verified fact blocks Arth's text, our glue (packaging, configuration, a deployment wrapper) takes over, and the code stays as it is.
3. **The captain's frame wins every conflict:**
   - one in-path question (C16 at EP-1);
   - handoffs are emit-only;
   - ServiceNow records and never holds work;
   - every decision is recorded into one store;
   - the named PASS and BREACH runs are on the same `ifabric-` agents.
4. **The projector is one-way.** Our store and snapshot are projected into the console's contracts. Nothing downstream reads the projection back: not the evaluators, not the stitcher, not the control test. So D8's single store and "the telemetry store never judges" still hold.
5. **Their schema is the projector's acceptance oracle.** That means `evidence-console-plan/schemas/contracts.schema.json`, the fixtures in `examples/`, and `generate_examples.py: answer_id_of()`. Build the console against their fixtures first. Then every projected file must validate with 0 errors.

### 5.1 The integrated picture

```
 LIVE PATH (unchanged: ARCHITECTURE §2.2)
 laptop `prooflab run` ──InvokeAgentRuntime──► ifabric-customer → ifabric-it → ifabric-network   (AgentCore, ours)
   emit(handoff.*) never blocks                 EP-1 evaluate(C16) = THE ONE WAIT · EP-3/EP-4 emit → ledger
                                                └─► modaas-agw (authz · PDP/Cedar · guardrail · ceilings) ─► Nemotron

 OFF THE PATH: the laptop hub (WSParticipantRole)
 collectors: aws/spans · /modaas/evidence · PDP · gateway stdout · metrics · CR status (3 token paths dropped)
             · aict-invocations (exact CID + session join) · AICT CloudTrail reads ──► raw/ + .capture.json   [G-11, G-12]
 ledger export ─► snapshot ─► stitcher ─► evaluators c16|c7|c9 (pure) ─► assessments ─► findings
 HUMAN-LOOP RUNNER: one process; owns delivery-log.jsonl; holds the SN creds            [G-04, G-05, G-06]
   finding builder ─► notify() ─► incident "[iFabric]…" assigned to Sree                  (Arth's code, unchanged)
     └ DELIVERED ─► run_assurance_agent(CallableAnalyzer) ──InvokeAgentRuntime──►        [G-03]
          ifabric_assurance_agent (AgentCore; our one-file handler; no SN creds) ─► modaas-agw ─► Nemotron   [G-01, G-02]
        ◄── text + x-modaas-action-id ── strip reasoning · validate 9 facts + refs (Arth) ─► PATCH work_notes ─► readback
        ─► run record + ANALYSIS_<STATE> line in the delivery log
   check() loop · export() · `case --out` snapshots · transitions mirrored into the ledger as notification records
 PACK PROJECTOR (one-way) ─► pack-index.json · records/ · assessments/ · runs/ · answers/ · auditor/ · live/   [G-07, G-08, G-10]
 Arth's manifest.py ─► MANIFEST.json ─► submit.sh ─► team bucket ─► readback (download + verify)

 PRESENTER'S LAPTOP: Evidence Console on 127.0.0.1:8787, read-only, holding no secret; PACK | LIVE        [G-09]
   Human Loop view = Arth's drop-in panel over /api/v1/cases · CLI `prooflab query` = `prooflab controltest` (same engine)
 SERVICENOW: incidents + one validated note per finding · AICT inventory lists ifabric_* by name, incl. ifabric_assurance_agent
```

### 5.2 Which document is the master, per topic

| Topic | Master | Why |
|---|---|---|
| Controls C16, C7, C9: rules, evaluators, modes, named runs, thresholds. The EP numbering and the one in-path question | **Ours:** ARCHITECTURE §2–§5, §11 | Frame + D2–D9. Theirs conflicts (EP3 admission, FM-B on the reference agents, the call limit; §3 rows E1–E3) |
| Register format, freeze, T1 | **Ours** §3.3, plus their top-level keys (G-14) | The kit parser and `submit.sh` read it |
| T2 approval mechanism | **Theirs:** `deliverables/thresholds/threshold-approval.md` (G-13) | No new code; closes our SN-09 spike |
| Risk register, AI inventory, INV | **Ours** §3.9, §3.10, §5.6 | The captain's risk request. Their schema has no INV |
| Evidence store, capture, figure of record, redaction, integrity | **Ours** §3.5, §8, §9, corrected by 06 D4 | Frame D8; verified facts (`aws/spans`; three token paths) |
| Internal record schema and stitch keys | **Ours** §4, §3.6 | One record from every adapter |
| Console contracts (`pack-index`, `answer`, `run`, `auditor`, `evidence/v1` as a projection) | **Theirs:** 03 + `schemas/` | The frontend's input; the projection target |
| Capture sidecar shape | **Theirs** 04 §4 | A superset of our capture manifest |
| Query grammar and the content of an answer | **Theirs** 06 §6, 03 §4.3. The verdict semantics come from **our** engine | One engine, two faces |
| Dashboard UI, API, modes, console security | **Theirs** 02 §5–§8, 06, 07, `demo/` | The captain: their dashboard is the frontend |
| Agents: the trio, J2, EP-1, the orchestrator, the build path | **Ours** §7 + 05 feasibility | D7 decided |
| Agent Trail facets (AP-v1 policy checks, outcome validation) | **Theirs** 05 §4–§6, as the spec, if D21 = yes | New scope |
| Assurance Agent logic, prompt, checks, note, case JSON, panel, delivery log | **Theirs** 08 + `code/` (unchanged) | Given |
| Assurance Agent packaging and deployment | **Ours** (G-01, G-02), on 05 AR-02/03/05 | A verified fact blocks 08 §5.3 as written (§4 V-01, V-02) |
| ServiceNow flows: incidents, responses, closure, AICT exports | **Theirs** 08 + handoff 1, with **our** process guards for bugs (a) and (b) | Given |
| Secrets placement, credentials, platform hygiene | **Ours** §8, §9.3 | Verified facts |
| Console zero trust | **Theirs** 02 §6, 07 §3, with our additions to the env list (G-09) | — |
| Build order, live lane, clock | **Ours** §12, with their Track B (console) and Track C (Arth) folded in | The 06:29Z credential expiry; the freeze line; C16 first |
| Acceptance | **Union:** their AT-01…AT-22 for the console and the pack, plus our gates | — |
| Run of show | **Theirs:** `presentation/JUDGING-DAY-GUIDE.html`, with our runs and our claims (G-16) | — |
| One-page architecture | **Ours:** `one-page.svg/.md`, with Arth's ServiceNow half redrawn in our numbering | — |
| Gap list | **One merged file, owned by us:** Arth's Section A (A1 corrected) + our §15.2 as Section B | — |

### 5.3 Deltas for `architecture/ARCHITECTURE.md`

**(a) New components**

| § | Delta |
|---|---|
| §3.11 (new) | **The iFabric Assurance Agent** as a component card:<ul><li>**Two parts:** the enforcement wrapper `run_assurance_agent()` in the laptop's human-loop runner, and the analyzer runtime `ifabric_assurance_agent` on AgentCore.</li><li>**Transports:** `callback()` (it runs after DELIVERED) and `pull()` (incident read and readback).</li><li>**Records:** its outputs are the work note, the run record and the `ANALYSIS_*` lines.</li><li>**Identity:** the runtime holds no ServiceNow credentials.</li><li>**Scope:** outside the claim's `applies_to`.</li></ul>Text: §2 below; glue: G-01–G-06 |
| §3.12 (new) | **The Evidence Console and the pack projector:**<ul><li>the console as specified by Arth (loopback, PACK and LIVE modes, no secrets);</li><li>the one-way projector (G-07);</li><li>the answer composer (G-08);</li><li>the live feed (G-10).</li></ul>It is a view: it sees everything and refuses nothing |
| §3.0 | Layout:<ul><li>add `prooflab/console/` (`server.py`, `static/`, including byte-identical copies of `ifabric-case-panel.{js,css}`);</li><li>add `prooflab/pack/` (projector, `pack-index`);</li><li>add `prooflab/query/{grammar,answer}.py`;</li><li>add `prooflab/policy/` (if D21);</li><li>add `agents/ifabric-assurance/ifabric-assurance.py`;</li><li>use Arth's `tools/manifest.py`;</li><li>`prooflab/servicenow/` = the handoff-3 version, unchanged (G-19)</li></ul> |
| §7.3 (new) | The Assurance Agent's build and deployment: a single-file handler, CR `ifabric-assurance-agent`, Sree's approval, READY, then AICT (G-01, G-02) |
| §6.1 | New rows:<ul><li>the Assurance runtime: only Nemotron through `modaas-agw`; the gateway key is injected; no ServiceNow secret;</li><li>the human-loop runner: the ServiceNow credentials; the only writer of the delivery log;</li><li>the console: loopback, a session token, CSP, a Host check, the secret-env refusal</li></ul> |
| §6.4 | New cases:<ul><li>**ADV-H-05:** instructions injected into a ticket → the Assurance Agent REFUSED (or BLOCKED by the guardrail);</li><li>**ADV-R-11:** a forged look-alike note → shown "untrusted" (G-18)</li></ul> |
| §12.2 | Fill the **W-AA** placeholder row ("Assurance agent + console (handoff-3), pending integration") with G-01–G-03 and G-07–G-10: their owners, checkers, acceptance checks (their AT-xx + 0 schema errors) and hours. Fold the other G-items into W0, W2, W4–W10 as §5.4 lists |

**(b) Replaced components**

| § | Was | Becomes |
|---|---|---|
| §3.7, D1 | One static, self-contained `dashboard.html`; a local server only as a cut-line extra | Their **Evidence Console** (`prooflab console`, 127.0.0.1:8787, PACK and LIVE) as the judged dashboard. The CLI stays the control test and the console's engine. The static viewer becomes their P2 VIEWER mode, or is cut (D17) |
| §3.0 | `store/manifest.py` | Arth's `tools/manifest.py` (`ifabric.evidence-manifest/v1`, already tested) |
| §3.3 | T2 = "a record that Arth or Sree creates … not a Finding" | Arth's **approval incident**: a REG finding with `kind approval`, its own delivery log, never assessed, never analyzed (G-13) |
| §3.10, §10.4 | "Arth's ServiceNow-native agent (L3), labelled with its model" | The Nemotron Assurance Agent on AgentCore. The ServiceNow-LLM prototype is superseded by the facilitator ruling of 2026-10-05 (08 header; handoff-3 handoff 1 l.443) |
| §3.2 | The capture manifest | Their `.capture.json` sidecar fields (a superset: redactions, operator, pagination) (G-11) |

**(c) Changed contracts**

| § | Change |
|---|---|
| §4 | Our `ifabric.evidence/1` is unchanged. The console contracts are derived from it through the projector's mapping tables (G-07). Additions:<ul><li>the run index gets a `system` value `assurance-agent` and the CID prefix `ifabric-assure-`;</li><li>`ANALYSIS_*` lines are mirrored as `notification` records carrying `call.id` (G-06)</li></ul> |
| §3.8 | The Finding gains its context: `measured`, `limit`, `register`, `trace` and `retest`, plus the evidence-ref rules (G-04). The publish order becomes: notify → `run_assurance_agent` → check loop → export → `case --out` (G-05) |
| §3.7 | The engine also emits `ifabric.answer/v1` with a deterministic `answer_id`. The CLI gets the aliases `controltest`, `ask`, `auditor` and `trail` (G-08) |
| §7.1 (J2) | Additive fields: `named_evidence_needed` and `proposed_action`. The projector maps `deciding_evidence`, `reversible_step` and `reason` to their names (G-07) |
| §3.3 | Top-level keys before `controls:`: `register_version`, `status`, `frozen_at`, `builder`, `assurance`, `retention`. The kit `owner` value is the ServiceNow user name, with `owner_name` beside it (G-14) |

**(d) Stale or contradicted text to correct**

| § | Correction |
|---|---|
| §3.8 | "46 offline tests" → 152 (handoff 3). Add the bug guards and the rule that the owner resolves closures herself (§4 V-12–V-14) |
| §3.8 AICT | Add `ifabric_assurance_agent` to what AICT shows. The AWS half of the AICT proof comes from our own CloudTrail reads (08 AI-06; G-12) |
| §3.10 | `scope_rule`: replace the ServiceNow-native agent entry with component `ifabric-assurance-agent` (owner Arth, approver Sree; D23) |
| §9.1 | Use the union tree: our files + the console files (`pack-index.json`, `records/`, `answers/`, `auditor/`, `runs/`, `live/`) + Arth's `servicenow/{cases,assurance-agent,incidents,aict,wiring-tests}` + `register/register.yaml` and `register/approval/` |
| §9.3, EP-10 | The three token paths (06 D4), if the fixers haven't already changed them, plus the union of the two redaction rule sets (G-11) |
| §8 | New rows:<ul><li>the console host: the presenter's laptop, never the IDE;</li><li>the human-loop runner, with the ServiceNow credentials;</li><li>the Assurance runtime.</li></ul>Their capture recipes run on the laptop only (§4 V-17) |
| §11 | One line: the ServiceNow queue is EP-13 (`callback()`, ALERT_ONLY), **not** the second EP |
| §12.1 (as re-timed at 23:45) | <ul><li>**G-02** joins batch window B2 right after S-4 (about 15 min of lane), or any lane gap before 07:45. AICT then shows it about 20 min later (SP-2 (a));</li><li>**T2** at the `v1` freeze (07:15–07:45) runs through Arth's approval incident (G-13);</li><li>the **first WRITTEN analysis** comes on N2's incident in the C16 block (07:45–08:45), replacing 08 §5.2's IDE proof;</li><li>**console P0** is built against the fixtures from 00:15 (W-AA);</li><li>**rehearsals** (13:15–14:30) use the console on the downloaded copy.</li></ul>The fleet items stay off the critical chain. **G-02 adds about 15 min to the serial lane, against a 15-min buffer.** So it must land inside an existing wait: the ~10-min `aict-invocations` wait after S-2, or the pilots' ≥ 2-min spacings. Otherwise it is the first P1 item the slip rule drops. The first analysis can run any time before the pack seal (~11:50), because `run_assurance_agent` is idempotent; a late G-02 costs only the live beat at about 08:15, not an L3 artefact |
| §12.2 W9 | **Conflicts with the captain's 2026-10-05 direction (Arth's code stays as is).** W9 lists "the adapter fixes (a) dry-run and (b) journal ACL, each with a test" and "the T2 approval record … Option B". Replace them:<ul><li>with G-05's process guards (§4 V-12, V-13);</li><li>with Arth's approval incident (G-13; no code);</li><li>the re-test link note: written with Arth's unchanged `client.add_work_note()` only **after** `check` has logged the owner's response, or written by the owner herself (§4 V-13, V-14).</li></ul>If anyone still wants the fixes, they go to Arth as a request |
| §7.1 | Replace the line "A 4th agent (iFabric Assurance agent, handoff-3) is pending integration" with a pointer to the new §7.3 |
| §13 | Revise D1. Add **D17–D23** (§5.6). D15 (the Cedar demo path) and D16 (the literal one store) are already taken; D16 (a) doesn't change this merge, because the projector reads the ledger export, whichever way D16 goes |
| §14 | Add OC-24 to OC-30 (§5.7) |
| §15.2 | Merge Arth's Section A (A1 corrected; A3, A8, A9–A18). Add the console's limits: the live file is a convenience index, and a replay is labelled REPLAY |

### 5.4 The boundary and glue tasks (candidates for our plan)

Effort is in fleet agent-hours. WS = the existing workstream that absorbs the task (ARCHITECTURE §12.2), or W-AA, the placeholder row that ARCHITECTURE §12.2 already holds for this integration. Priorities, against ARCHITECTURE §12.4: P0 = what the never-cut row needs (finding → incident, the pack, redaction); P1 = L3, AICT, the judged console (the CLI is its P0 fallback); P2 = a fallback or an extra.

| ID | Task | Connects (ours ↔ Arth's) | Effort | Depends on | WS | Pri |
|---|---|---|---|---|---|---|
| G-01 | Assurance runtime handler, single file | AgentCore build path (AR-02/03/05) ↔ the analyzer contract of 08 §5.3 | 1.5–2 h | W2 bundler and Docker smoke | W2 | P1 (build early) |
| G-02 | Assurance CR, approval, deploy | Generator wrapper, deploy wrapper, inventory ↔ runtime `ifabric_assurance_agent` (AICT) | 0.5 h + ~10 min lane + Sree | G-01 | W2/W3 | P1 (L2 block) |
| G-03 | Laptop invoke helper → `CallableAnalyzer` | `prooflab run` invoke helper ↔ `CallableAnalyzer`, `run_assurance_agent` | 1 h | G-02, W3 | W9 | P1 |
| G-04 | Finding builder with context | `Assessment.finding` + records + pin ↔ `finding_from_dict` (+ `measured`, `limit`, `register`, `trace`, `retest`) | 2–3 h | W5, W6 | W9 | P0 (trace P1) |
| G-05 | Human-loop runner | Laptop evaluator runner / `watch` ↔ `notify`, `run_assurance_agent`, `check`, `export`, `case` | ~2 h | G-03, G-04, SN creds | W9 (+W4) | P0 / P1 |
| G-06 | Delivery log → ledger mirror | Arth's delivery log ↔ our `notification` records, stitch key 6 | 0.5–1 h | OC-8 | W9 | P1 |
| G-07 | Pack projector (one-way) | Our snapshot ↔ the console contracts (03, schema) | 4–6 h | W5, W6, G-11 | W-AA (+W6) | P1 (P0 = the pack itself) |
| G-08 | Answer composer + grammar | `query/engine.py` ↔ `ifabric.answer/v1`, grammar, `controltest` | 2–3 h | W7, G-07 | W7 | P1 (the CLI aliases P0) |
| G-09 | Console build, with data-driven EPs | Pack + engine ↔ console spec (06, 07) + Arth's panel | Their P0 ~3.5 h + their P1 ~2 h + 0.5 h | G-07, G-08 | W-AA | P1 (their AT-P0 views; the CLI is the P0 fallback) |
| G-10 | Live event feed | `prooflab watch`/`tail` ↔ `live/events.jsonl`, SSE, Replay | 2–3 h | W4, G-05 | W4 (+W-AA) | P1 |
| G-11 | Capture sidecars + redaction union | Collectors, `redact.py`, `cr_status.py` ↔ `.capture.json`, their 6 rules | 1–1.5 h | W4 | W4/W6 | P0 |
| G-12 | AICT evidence feed | CloudTrail and `aict-invocations` pulls ↔ Arth's `servicenow/aict/` ↔ `answer.aict` | ~1 h + Arth | W4 | W4 | P1 |
| G-13 | T2 through Arth's approval incident | `registry freeze` (T1) ↔ `threshold-approval.md` flow | 0.5–1 h + ~15 min live | W8, SN creds | W8 | P1 (T2 corroborates, D5 as revised; the T1-only fallback in §12.4) |
| G-14 | Register mapping | Flat `register.yaml` ↔ the Register view, `pack-index.register`, Finding `register` | 0.5–1 h | W8 | W8 | P1 (`owner` mapping for P3; the ribbon) |
| G-15 | Direct-gateway fallback over loopback | `GatewayAnalyzer.from_env()` (unchanged) ↔ `modaas-agw` | 0.5 h + 10 min spike | OC-24 | W9 | P2 |
| G-16 | Docs, pitch and gap-list alignment | One-page, gap list, `run-ids.txt` ↔ `servicenow-section.md`, Section A, pitch, guide | ~1 h | — | W10 | P1 |
| G-17 | Agent Trail facets (AP-v1, outcome) | J2 + EP-3 records + expected spec ↔ `decision.policy_checks`, `run.outcome` | 2–3 h | W2 (J2), W5 | W5 | P1 (cut first) |
| G-18 | Wiring-test history + Assurance adversarial cases | Arth's `wiring-tests/`, REFUSED/BLOCKED ↔ our adversarial log | 0.5 h + ~4K tokens | G-05 | W10/W9 | P2 |
| G-19 | Code merge and package layout | Our §3.0 ↔ handoff-3 `code/`; the console plan's module names | 0.5 h | — | W0 | P0 (first) |

**G-01 · The Assurance runtime handler (one file).**
- **Our side:**
  - one file, `agents/ifabric-assurance/ifabric-assurance.py`, never named `agent.py` (AR-05);
  - a `BedrockAgentCoreApp` entrypoint;
  - it reads only the platform-injected `OPENAI_BASE_URL`, `OPENAI_API_KEY` and `MODEL_ALIAS` (AR-09);
  - a CI gate: gz+b64 ≤ 24,000 characters (the handler is estimated at about 2–3K);
  - an arm64 Docker smoke against a stub OpenAI-compatible server (AR-03, step 3).
- **Arth's side:**
  - the input is `{"messages": [...]}` (we add an optional `cid`);
  - the output is `{"text", "model_id", "action_id", "usage", "latency_ms", "finish_reason"}`;
  - errors come back as `{"error": "blocked" | "unavailable", "action_id": …}` (08 §5.3 step 2).
- **The glue:**
  - a stdlib `urllib` POST to `OPENAI_BASE_URL.rstrip('/') + '/chat/completions'`. The injected base already ends in `/v1`; appending `nemotron.py`'s `/v1/chat/completions` would double it.
  - Bearer `OPENAI_API_KEY`. The body is `{model: MODEL_ALIAS, messages, temperature: 0, max_tokens: 900}`: 900 matches `nemotron.MAX_TOKENS`; raise it only after OC-25.
  - Non-streaming: the action-id header is verified on non-streaming calls only (AR-13). No redirects; a 90 s timeout.
  - Read `x-modaas-action-id`. Map `finish_reason == "content_filter"`, or an error body containing `content_filter`, to `blocked`.
  - Set `baggage: modaas-correlation-id=<payload cid>` and forward the inbound `traceparent`. urllib is not ADOT-instrumented (AR-19), so the header passes as set (OC-30).
  - Print one JSON line per call to stdout as the witness: action id, usage, finish reason, **never the text** (AR-24).
  - Set `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_unredacted_attributes=` (AR-25).
  - It imports nothing from `prooflab/servicenow`, so no Arth module has to be bundled.
- **Why not `GatewayAnalyzer` inside the runtime:** `_check_gateway_url` (`nemotron.py:79-86`) refuses the injected `http://<public ELB>:8081/v1`, and a module-level `GatewayAnalyzer.from_env()` (08 §5.3's sample body) would crash the runtime at start. 08 §5.3 itself allows "a Strands model provider pointed at `modaas-agw` … as long as the output keeps this contract"; our handler is that case.

**G-02 · The Assurance CR, approval and deployment.**
- **CR and runtime:** CR `ifabric-assurance-agent` in `components`. Kubernetes names can't hold `_`; the operator names the runtime `ifabric_assurance_agent-<id>` (AR-01).
- **Spec:** `dependsOn.models: [nemotron-super-120b]` (Approved, not paused; AR-28), and no tools.
- **Build:** through `build-agent-image.sh`, with `IMAGE_TAG=ifabric-assurance-<gitsha>` and a `URI_FILE` (AR-05). **Never `new-agent.sh`:** it copies the template over `agent.py` (AR-02).
- **Env:**
  - leave out `AUDIT_URL` and `AUDIT_WRITE_TOKEN` (the handler writes no ledger records), so there is one fewer token copy to redact;
  - never put `MODAAS_API_KEY` or a ServiceNow value in env.
- **Approval and readiness:**
  - Sree annotates it herself, never through the generator's `approve=True` (AR-07);
  - READY comes about 40 s later (AR-08);
  - record the digest and the generation (EP-10);
  - add it as an inventory component **outside the claim's `applies_to`**, so C16, C7, C9 and EP-0 ignore it.
- **AICT:** after at least 20 min, Arth presses Execute Now and confirms the AI Function record (OC-26).

**G-03 · The laptop invoke helper → `CallableAnalyzer`.**
- **The helper:** `invoke_assurance(messages)` calls `aws bedrock-agentcore invoke-agent-runtime` through a stdlib subprocess, as `ask_agent.py` does, with:
  - `AWS_MAX_ATTEMPTS=1` and `--cli-read-timeout 300` (AR-18);
  - a fresh `--runtime-session-id`;
  - `--baggage modaas-correlation-id=ifabric-assure-<epoch>-<hex>`, with the same CID in the payload.
- **Errors:** it raises `AnalyzerError("blocked" | "unavailable", msg, action_id)` on an `error` key. `CallableAnalyzer` doesn't inspect it (`nemotron.py:169-176`).
- **Timeouts:** never re-invoke on a timeout.
- **The wiring:** `CallableAnalyzer(invoke_assurance, backend="agentcore:ifabric_assurance_agent", model_alias="nemotron-super-120b")`. The backend prefix keeps outcome-validation V6 (`assurance_checks.py:163`) passing when an action id comes back.
- **Why a separate CID prefix:** C16's floor and C7's expected set query by the subject run's CID, so the Assurance calls never count against a subject run.

**G-04 · The finding builder.**
- **Required fields:**
  - `scope_id` = the CID (D22);
  - `threshold_version` = our register version;
  - `detected_at` = the assessment's as-of time, in UTC.
- **Context:**
  - `measured` and `limit` come from the assessment and the pin: same unit, operator `<=`;
  - `register` = `{version_date, owner: <the SNOW_OWNER_USER value>, approval: <the T2 INC>}`. P3 compares owner strings exactly (`assurance_checks.py:105`).
- **`evidence`:**
  - at most about 8 refs, each without `;` or a newline: the model's echo is split on `;` (`assurance_agent.validate_fields`), and a long list raises the REFUSED rate;
  - for example `assessment:<id>`, `aws-spans:run=<cid>`, `ledger:cid=<cid>`, `gateway:action_id=<the first over-cap call>`;
  - the full list stays in the pack.
- **`trace`:**
  - agent steps (intent, judgment, `handoff.received`) in zones customer, it and network;
  - each gateway model or tool call as `zone: gateway`, `actor: modaas-agw`, `ref: gateway:action_id=<id>`;
  - the script's handoffs as `zone: orchestrator`, which the panel renders as "other". They are **never presented as gateway crossings**: our handoffs don't pass through `modaas-agw`;
  - `run_id` = `scope_id` on every step;
  - a cap of 200 steps (`finding_context.py:98`): keep every agent step plus the first and last gateway step of each run of consecutive gateway steps. This preserves the M1 route rule. State the elided count in `summary`.
- **`retest`:** `{assessment, SATISFIED, same version, at}`, written into the same finding file before the owner resolves the incident.
- **A unit test** passes every generated file through `finding_from_dict`. Only BREACHED, ESCALATED and `monitoring-gap` scopes are notified.

**G-05 · The human-loop runner.** One process, the only writer of `PROOFLAB_DELIVERY_LOG` (an absolute path, SN-07). Its ServiceNow credentials come from `~/.prooflab-snow.env` (mode 600; SN-02), with `selftest` before each batch.
- **Notify:** only finding ids that are new in the log (the volume bound, SN-08).
- **Analyze:** on DELIVERED, run `run_assurance_agent` in a background thread, with G-03 (fallback G-15).
- **Check:** `check` every 60–120 s per open finding until the common cutoff (judging start); stop once RESPONDED.
- **Snapshot:** `case --out evidence/servicenow/cases`:
  - every 30–60 s while an analysis or a response is pending;
  - otherwise every 5–10 min;
  - once at seal.

  Each path and sha256 goes into the live index (`pack-index.cases[]`).
- **Export:** after each owner response and at the final check (the bug (b) guard).
- **Never:**
  - `analyze` a finding of `kind` `approval` or `wiring-test`;
  - accept `--dry-run` unless the log path is under `wiring-tests/` (the bug (a) guard).
- **A run-card rule:** after the owner responds, nobody else updates our incidents. The owner resolves closures in the UI herself (§4 V-14).

**G-06 · The delivery log → ledger mirror.**
- **What it mirrors:** state **transitions** only, as `notification` records (`verdict: RECORDED`, ServiceNow clock), with a deterministic `record_id` = sha256 of the log line. It skips the check loop's repeated AWAITING_RESPONSE lines, to spare the single-threaded ledger (AR-21).
- **`ANALYSIS_*` lines** carry `call.id` = their action ids, which joins each analysis to its `aws/spans` span, plus `note_digest`.

**G-07 · The pack projector (the mapping tables the schema forces).**

| Field | Ours → theirs |
|---|---|
| `provenance` (4 values) | **Membership first:** any CID listed in `run-ids.txt` (a named PASS, BREACH or RETEST run) → ASSESSED, whatever its `run.condition` or provenance value. Otherwise, by value: LIVE_SUBJECT → ASSESSED; EXPLORATORY, PILOT, BASELINE → EXPLORATORY; AUTHORIZED_TEST, FAULT_INJECTION, REPLAY, COUNTERFACTUAL_EXPORT → EXPLORATORY in records (also surfaced as adversarial cases); Arth's wiring tests → WIRING_TEST. SYNTHETIC never enters the pack. Our value is kept in an extra `provenance_detail` key (additive keys are allowed by their 03 §5 rule 1) |
| `record_kind` (6 values) | action (model) → model-call; action (tool) → tool-call; handoff, lifecycle, judgment, notification → event; metric → window; decision → decision; approval → approval. Assessments and findings go to their own files |
| Inline `decision` | DENY with `inline.mode=observe` → ALERT; DENY with enforce → DENY; ALLOW → ALLOW. Also `committed`, `reserved` (and our `bound`) |
| `disposition` | escalate with reason `c16-budget-halt` → `halted-by-budget`; J2's `deciding_evidence` → `cited_evidence`, `reversible_step` → `reversible_action`, `reason` → `rationale` (≤ 400 chars) |
| `enforcement_points[]` | Our EP-0…EP-13 as ids (the schema leaves `id` free). `kind` is the nearest of the six enum values, with `kind_detail` beside it. `status` is honest: EP-1 BUILT only if decision records exist; EP-13 ALERT_ONLY; EP-0 as D13 decides |
| `controlRef` (C7, C9, C16, ESC only) | INV, APPROVAL (EP-0) and PLATFORM are not projected as records or findings. They show as EP rows and as Six Questions facts; the CLI answers them |
| `run.id` | The alias from `run-ids.txt`, with `joins.cid` = the CID (our records keep the CID) |
| `hop.via` | `orchestrator-handoff` for every script handoff (the schema offers it) |

The outputs are `pack-index.json` plus `records/`, `assessments/`, `runs/<cid>/run.json`, `auditor/`, `gaps/`, `adversarial/` and the `answers/` from G-08.
- **First slice** (for the console's AT-P0 views): the `pack-index` core (claim, register, artefacts, named runs with `written_at`, cases, gaps, integrity), the C16 records, the assessments and the answers.
- **P1:** the runs, auditor files, adversarial cases and levels.

**G-08 · The answer composer.** `prooflab/query/answer.py` builds `ifabric.answer/v1` from our engine's result:
- the rule, with `date_before_scope` from our T1/T2 check;
- the population, from completeness;
- both numbers of every rule;
- the exceptions;
- the tester and the evaluator, with the inline decisions;
- the ten audit-question rows;
- `human_loops[]` from the case snapshots;
- `aict` (G-12);
- the records, with tickmarks;
- the gaps;
- `source`, with the MANIFEST status and `elapsed_ms`.

`answer_id` follows their canonicalization exactly (`generate_examples.answer_id_of()`). `grammar.py` holds their phrase table. `controltest`, `ask`, `auditor` and `trail` are aliases of our `query` verbs; our extra verbs (`--risk`, `--inventory`, `--claim`) stay.

**G-09 · The console build.** These are adjustments to the *planned* console only; Arth's shipped files are untouched.
1. **Architecture view:** it renders our `one-page.svg` and `pack-index.enforcement_points`. Drop the demo's hard-coded labels, "ifabric-run · EP3 handoff · evaluate()", "EP2 model adapter" and the journey's "· EP3" / "EP3 admission" (`demo/index.html:210, 287, 351`). Their own J-14 says the console never asserts an EP.
2. **Human Loop:** fetch `/api/v1/cases` on a 10 s timer and call `IFabricCasePanel.render(el, json.data)`. Don't point `IFabricCasePanel.poll()` at the enveloped route: `render()` would treat the `{ok, data, …}` envelope as one case (`ifabric-case-panel.js:439-441`).
3. **The secret-env refusal list** (07 §3) gains `OPENAI_API_KEY`, `AGENTCORE_GATEWAY_MCP_TOKEN`, `AWS_SESSION_TOKEN` and `SNOW_CLIENT_ID`.
4. **Fonts and hosting:** fonts self-hosted (AT-17). It runs on the presenter's laptop only, never in the IDE.

Our static HTML renderer in W7 is dropped, which offsets part of the cost.

**G-10 · The live event feed.** One watcher process writes their event types.

| Event type | Source |
|---|---|
| `call` | `kubectl logs -f` on gateway stdout, filtered to active CIDs |
| `admission` | Our EP-1 decision records through ledger `/records?cid=`, polled no faster than every 3 s (AR-21) |
| `hop`, `decision` | The script, locally |
| `verdict` | Evaluators only, after the run ends |
| `window` | C9: CloudWatch every 5 min; PROVISIONAL until the hour closes |
| `finding`, `incident`, `response`, `analysis` | G-05 |
| `ceiling`, `heartbeat` (with per-stream lag), `stream-error` | The watcher itself |

The file is a convenience index derived from raw, and it is labelled "live index" in the pack.

**G-11 · Capture sidecars and the redaction union.**
- **Sidecars:** their sidecar fields on every capture.
- **Capture files as JSONL,** so that `raw:<path>#L<n>` refs resolve in the Record Inspector.
- **Redaction:** their six rules plus ours:
  - drop `spec.awsAgentCore.environmentVariables`, `kubectl.kubernetes.io/last-applied-configuration` and `kopf.zalando.org/last-handled-configuration` on every CR kind (06 D4);
  - never write `get-agent-runtime` output (AR-30).
- **Then:** the exact-value scan must report 0 hits, plus their `test_redaction.py`.

**G-12 · The AICT evidence feed.** Three sources join here:
- **Our reads:** CloudTrail `AssumeRole` by `ServiceNowAictUser`, and `ListAgentRuntimes` / `GetAgentRuntime` by `SgcAictReadOnlyAccessRole` (08 AI-06). Also `aict-invocations`, joined exactly on the CID in `responseElements.baggage` plus `runtimeSessionId` (AR-20) and pulled at least 10 min after a run (06 B6).
- **Arth's exports:** in `servicenow/aict/`: the inventory list, which should include `ifabric_assurance_agent`, and screenshots, by 09:30 UTC (AI-04).
- **The console:** these feed `answer.aict` and the L2 card.

**G-13 · T2 through Arth's approval incident.**
- **Freeze:** `prooflab registry freeze` writes `approval-finding.json` from the frozen bytes: `control_ref REG`, `kind approval`, the version, and the register's and risk register's sha256s as evidence refs. T1 (the S3 write-once object) is unchanged.
- **Its own log:** `evidence/register/approval/delivery-log.jsonl`.
- **The approval:** Sree's work note "APPROVED threshold register <v>, sha256 <12 hex>" must stay the incident's last update until `check` logs RESPONDED (bug (b)). Then `export` at once.
- **The date check** reads T2 = the RESPONDED `at` (basis `last_update`, the ServiceNow-set `sys_updated_on`) and T1, and both must precede the run's first span time.
- **Never** analyze it, and never let it enter an assessment.

**G-14 · The register mapping.**
- **Top-level keys:** add `register_version`, `status`, `frozen_at`, `builder`, `assurance` and `retention` before `controls:`. The kit parser ignores them.
- **Entries stay flat.**
- **The projector maps:**
  - `why_metric`, `why_value`, `measured_on` and `stops_holding_when` to their four justifications;
  - the `risks.yaml` ratings to inherent and residual.
- **The owner:** the kit `owner` value is the ServiceNow user name, with `owner_name` beside it.
- **Their nested template is not adopted** (§3 row E4).

**G-15 · The direct-gateway fallback (only if G-01–G-03 aren't READY in time).**
- **The tunnel:** `kubectl -n agentgateway-system port-forward svc/modaas-agw 18081:8081`.
- **Env:**
  - `MODAAS_GATEWAY_URL=http://127.0.0.1:18081` (loopback passes `_check_gateway_url`);
  - `MODAAS_MODEL_ALIAS=nemotron-super-120b`;
  - `MODAAS_API_KEY` from the existing mode-600 token file into the process env only;
  - the §5.2 TEST log.
- **The effect:** the key rides the kube-API tunnel, never plain HTTP to the public ELB.
- **SPIKE OC-24, with the captain's OK:** RBAC allows `pods/portforward` in `agentgateway-system`, and the VAP doesn't cover CONNECT, but the path is untested.

**G-16 · Docs, pitch and the gap list.**
- **Redraw the ServiceNow half** of the one-page in our numbering: ServiceNow is EP-13 (`callback()`, ALERT_ONLY); the gateway is EP-2, EP-6 and EP-7 (observed).
- **The second EP** is the same `c16` module at EP-1 and EP-2. Their guide's step 7 already says so; the ServiceNow section and the L2/L3 script don't.
- **Gap list:** correct A1 (AgentCore runtimes and gateways only) and fill A3, A10 and A15–A18.
- **`run-ids.txt`:** Arth's columns plus ours (register version, mode, condition) and the aliases the console shows.
- **The guide's step 6:** the reference S2 (EXPLORATORY, the "before") against the `ifabric` run, and our N3 as the in-path DENY beat.

**G-17 · The Agent Trail facets (only if D21 = yes).**
- **The functions:** pure `prooflab/policy/check.py` and `outcome.py`, over our records, as their 05 §5–§6 tables specify.
- **Inputs:** `policies/agent-policies.yaml` and `expected/scenarios.yaml`, frozen with the register in the T1/T2 bundle.
- **Separation:** they never feed a control verdict.
- **Fallback:** a "derived from ledger" chip where J2 fields are absent.

**G-18 · Wiring tests and the Assurance adversarial cases.**
- **History:** copy `servicenow/wiring-tests/` as it is (WIRING_TEST, never in the production log).
- **ADV-H-05:** a TEST finding whose `summary` carries injected text; the incident description is built from it. Expect REFUSED or BLOCKED, under a TEST log.
- **ADV-R-11:** a forged look-alike note, shown as untrusted.

**G-19 · The code merge and package layout.**
- **Merge:** take handoff-3's `prooflab/servicenow/` and `prooflab/tests/` and keep ours; `pytest` must give 152 passed in the 3.9 venv (PY-02).
- **One dispatcher:** `python3 -m prooflab` with both verb sets; `python3 -m prooflab.servicenow` stays as it is.
- **Function names:** don't create the console plan's `evaluators/c16.py` functions `test()`/`admit()`. Ours, `assess_run()` and `decide_inline()`, are the names.
- **MANIFEST coverage:** `MANIFEST.json` (Arth's tool) covers byte-identical copies of `register.yaml`, `gap-list.md` and `run-ids.txt` inside `evidence/`; `submit.sh` adds the WORKDIR copies outside it.

### 5.5 Effort roll-up, and where it lands on the critical path

**Cost.**
- **Gross:** about 29–38 agent-hours.
- **Net new:** about 18–24 h. The rest falls inside existing budgets:
  - W7's static dashboard (dropped);
  - W9's publish/mirror/approval glue (2 h);
  - W4's watch loop;
  - W10's docs.
- **Wall clock:** +3–4 h, at 6–8 workers. The fleet work runs in parallel and stays **off the critical chain** (W0 → W1 → W2 Stage A).
- **Live lane:** about 15 min more for G-02 (one build, one apply, Sree's annotation, one smoke invocation of about 4K tokens), against the re-timed plan's 15 min of buffer. So G-02 rides inside an existing wait, or it is dropped first (§5.3 (d), the §12.1 row). T2 is already in the plan's freeze step.
- **The P0 subset**, which the never-cut row of ARCHITECTURE §12.4 needs (finding → incident, the pack, redaction): G-19, G-11, and the minimal G-04 and G-05 (notify, check, export). About 4–6 h.
- **The console path** (G-07, G-08, G-09; about 11–15 h) is **P1**: "cut console scope, never control scope" is a rule in both plans (§3 row I1), and the CLI in the pack is the P0 fallback for the two-minute test.

**Timeline (UTC), against the re-timed ARCHITECTURE §12.1** (the 23:45 re-timing: agents frozen at about 05:45; `v1` at 07:15–07:45; 15 min of buffer):

| When (UTC) | What |
|---|---|
| 00:15–02:00 | G-19, with W0 and W-CI: Arth's 152 tests join the Python 3.9 gate. Then G-09 P0 against their fixtures (W-AA; fully parallel, it needs no live data). G-14 (W8). G-08 starts with W7 |
| 02:00–05:00 | With W3–W10 on contract v1: G-04, G-05, G-06 (W9); G-07 (W-AA + W6); G-10, G-11 (W4/W6); G-01 (W2, on Stage A's bundler and the S-0 Docker harness at about 04:00) |
| B2 (04:00–05:30) | **G-02 inside an existing wait:** best during S-2's ~10-min `aict-invocations` wait; otherwise in the pilots' spacings (B3). Build, apply, Sree's annotation, one smoke invocation. AICT shows `ifabric_assurance_agent` about 20 min later (SP-2 (a)). It is outside the claim, so it never blocks the agents' freeze. With no free wait, the slip rule drops it first |
| 07:15–07:45 | **The `v1` freeze:** T1 (S3) dates it; **G-13** (Arth's approval incident) corroborates, per D5 as revised: Arth's reviewed note, then Sree's APPROVED note, then `check` → RESPONDED, then `export` |
| 07:45–08:45 | **The C16 block:** N2's finding → notify → **analysis WRITTEN through the runtime**. This is the first live proof of the Nemotron call, replacing 08 §5.2's IDE step. Then a case snapshot → the console's Human Loop. If G-02 slipped, run the analysis on N2's incident any time before the seal (~11:50): it is idempotent and off the path |
| 08:45–12:00 | G-10 live through the C7 and C9 blocks; G-12; G-16; G-17 if time allows. **By 12:00:** Arth's AICT exports, including `ifabric_assurance_agent` |
| 12:05–13:15 | Pack: the final `check`, `export` and `case --out`; the full projection (G-07); MANIFEST; `submit.sh`; readback |
| 13:15–14:30 | Rehearsals on the console over the **downloaded** copy (AT-18), with the guide's run of show (G-16) |

### 5.6 The minimal captain decisions this needs

| D | Decision | Recommendation |
|---|---|---|
| D17 | The dashboard's form | Their Evidence Console, as the captain directed. Cut our static `dashboard.html`, or keep it as their P2 VIEWER. The CLI stays the control test inside the pack |
| D18 | The Assurance backend | **AgentCore primary:** no gateway key on the laptop, and it is the AICT-visible form. The direct gateway over a loopback port-forward is a fallback only (yes/no; OC-24) |
| D19 | The T2 mechanism | Arth's approval incident as T2's mechanism: amend §3.3 and D5's "not a Finding" (the incident's Finding has `kind approval`, has its own log and is never assessed or analyzed). T1 still dates the threshold; T2 corroborates (D5 as revised) |
| D20 | EP numbering and the claims | Ours (EP-0…EP-13). ServiceNow is EP-13, ALERT_ONLY, and not "the second EP". **Reject:** EP3 handoff admission, held actions, the per-invocation call limit, FM-B on the reference agents, FM-C by rebuild (frame; D9) |
| D21 | AP-v1 policy checks + outcome validation (Agent Trail) | P1 yes, cut first if late |
| D22 | The Finding's `scope_id` | The CID. Aliases come from `run-ids.txt` in the projection |
| D23 | Who owns the Assurance Agent | Owner Arth (builder), approver Sree; outside the claim's scope |

### 5.7 New open checks and spikes

| # | Check | How | Gates |
|---|---|---|---|
| OC-24 | A loopback port-forward to `modaas-agw` works for a governed call | One `port-forward` + one ≤ 20-token call with the user's OK | G-15 (fallback only) |
| OC-25 | Is `max_tokens` 900 enough for a complete 16-line note from Nemotron? Reasoning may consume the budget | The first live analysis. If REFUSED for "no analysis note", raise the **handler's** limit (G-01); never edit Arth's prompt | G-01 |
| OC-26 | Does AICT import `ifabric_assurance_agent` (the ServiceNow half)? | Arth: check `my_agent` now (08 AI-02), then the new runtime after at least 20 min | L2 claim |
| OC-27 | Does the panel render under the console's CSP (`default-src 'none'`, `style-src 'self'`)? | AT-07 plus a visual check in both themes | G-09 |
| OC-28 | ServiceNow API load at the snapshot cadence (shared instance) | Count the calls per cycle; watch for 429s; slow the cadence of closed findings | G-05 |
| OC-29 | The new runtime's `OPENAI_BASE_URL` shape (`…/v1`) | `get-agent-runtime --query` on that one variable; never log the raw response (AR-30) | G-01 |
| OC-30 | A hand-set `baggage` header on urllib reaches `modaas.run_id` | `aws/spans` shows `ifabric-assure-…` after the first analysis | G-03 (C16/C7 exclusion) |

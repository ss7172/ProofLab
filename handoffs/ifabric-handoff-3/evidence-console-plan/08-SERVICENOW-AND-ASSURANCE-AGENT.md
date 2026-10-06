# 08 · ServiceNow human loop, Nemotron Assurance Agent and its GUI: the single source of truth

> **Single source of truth (2026-10-05).** This file **is** the Assurance Agent + GUI specification. It merges the former
> `SERVICENOW_ASSURANCE_AGENT_AND_GUI_INTEGRATION_HANDOFF.md` ("handoff 2", v3: five assurance sections; now 152 tests with the P6 re-test fix of 2026-10-05), keeping its
> section numbers, so any reference to "handoff 2 §5.2" or "§8.7" points to the same section here. The old file is archived at
> `archive/SUPERSEDED-2026-10-05-SERVICENOW_ASSURANCE_AGENT_AND_GUI_INTEGRATION_HANDOFF.md`; do not edit it.
>
> **What this plan adds:**
> - §5.7: how the Assurance Agent's five sections relate to the agent runs' five facets;
> - §7: the Evidence Console integration (zero trust: the console holds no ServiceNow secret);
> - §15: AI Control Tower evidence;
> - §16: owner engagement and closure.
>
> **Still valid alongside:** `SERVICENOW_INTEGRATION_HANDOFF.md` (handoff 1: Finding contract, incidents, evidence layout).

**From:** the ServiceNow workstream (Arth, with Claude Code). **To:** the teammate building the main app (agents, controls, adapters, dashboard) and their coding agent.
**Two parts that work together:**
1. **The iFabric Assurance Agent** (§2, §5): a **Nemotron** agent that analyzes every control-finding incident we raise in ServiceNow and writes one structured analysis note back onto that incident.
2. **Its GUI in the dashboard** (§6–§8): one JSON contract (`case_view`) plus a drop-in panel that shows the whole evidence chain, including the agent's analysis and the five assurance sections. In the ProofLab Evidence Console it is the **Human Loop** view (§7).

> **Facilitator ruling (2026-10-05): the Assurance Agent must use NVIDIA Nemotron.** In this event Nemotron is reachable **only through the governed MoDaaS gateway `modaas-agw`** (no public endpoints), and agents run on **AWS AgentCore** or in ServiceNow. ServiceNow AI agents cannot use a model outside the instance's providers, and this instance has no Nemotron. So the agent **runs on AWS** and writes into ServiceNow. The earlier ServiceNow-native prototype (on the ServiceNow LLM) is **inactive** and kept only as labelled history.

**The Assurance Agent in one paragraph.** When our adapter raises an `[iFabric]` incident for a control finding, the Assurance Agent reads the incident and checks it. It answers four questions:
- Which control, threshold version, scope and verdict is this?
- What was measured against what limit, and which evidence references back it?
- What required evidence is missing?
- What is the correct next step (for example "close only after a linked passing re-test")?

Nemotron answers through `modaas-agw`, so the call itself is guardrail-checked and recorded in the audit ledger. Our orchestrator is the **enforcement point**:
- it strips the model's private reasoning;
- it checks every factual field against ground truth (the next step is fixed policy text per verdict);
- it refuses invented evidence;
- it trusts only notes that it wrote itself (their digest is in our run log).

Only then does it write **one fixed-format work note** on the incident. The dashboard shows that note, which fields were *checked* and which were *Nemotron's judgement*, the gateway provenance, and every refusal.

**What the agent's analysis covers (five assurance sections).** Our code computes these five sections, never the model. Each check is **pass**, **fail** or **unknown**; unknown means the data wasn't provided, and it is never shown as a pass.

| Section | What it shows |
|---|---|
| **Agent movement** | the agents' path across zones (customer → gateway → IT → gateway → network → gateway → customer), gateway crossings, and the route rule "no direct network → customer hop" |
| **Decision trace** | every decision in time order: each agent/gateway step, the control verdict, ServiceNow delivery, the owner's reply, and every model attempt and outcome |
| **Evidence** | each evidence reference by kind (gateway, ledger, aict, …), which ones the agent cited, the run record and the gateway action ids |
| **Policy alignment** | 8 checks (P1–P8): verdict vs measured/limit, threshold dated before the test, owner matches the register, owner notified, response recorded, not closed without a re-test, evidence attached, route rule |
| **Outcome validation** | 6 checks (V1–V6) on the agent's own output: run completed, note digest in our run log, facts match, cited refs exist, reasoning not stored, governed Nemotron call with provenance |

Three summary lines also go into the ServiceNow note (`Agent path`, `Policy alignment`, `Validation`); the full detail is in the case JSON (§6) and the panel (§8.7). **Movement and most policy checks need the evaluator to attach optional context to each finding (§5.0): four fields always, plus `retest` when a passing re-test closes it.**

**Verification status (never claim more than this in the demo):**

| Part | Status |
|---|---|
| Incident description carries the full finding block | **Verified live** (INC0010232) |
| ServiceNow-native prototype (ServiceNow LLM) | Ran live once, correct; **superseded and inactive**, history only (`evidence/servicenow/sn-agent/`) |
| Nemotron orchestrator, gateway client, validation, note parser, case JSON, panel, local server | **Built and tested**: 152 tests on Python 3.9 and 3.13 against a fake ServiceNow and a fake `modaas-agw` over real HTTP; panel checked visually in Chrome with fake data |
| Five assurance sections (movement, decision trace, evidence, policy alignment, outcome validation) in the note, case JSON and panel | **Built and tested** (same suite); panel checked in Chrome with fake data in light and dark mode and at 360 px wide (previews `panel/preview-assurance-*-fake-data.jpg`) |
| Live ServiceNow round-trip of the write path (stand-in, no model) | **Verified live 2026-10-05** on INC0010232, 9/9 checks (`tools/sn_roundtrip_test.py`). Note written as `ifabric.integration`, read back with **matching SHA-256** (ServiceNow returns the text unchanged), real journal header parsed, re-run `SKIPPED`, all five sections in the case JSON, `Policy alignment: 6/8 pass; unknown: P1, P5` as expected, and the stand-in correctly **not** validated (V6). Evidence: `servicenow/wiring-tests/assurance-agent-roundtrip/` (run record, test log, screenshot) |
| Live call through `modaas-agw` with an approved Nemotron alias | **Pending**: must run inside the workshop IDE (§5.2) |
| AgentCore runtime `ifabric_assurance_agent` (Sree's approval) | **Pending**: teammate, Module 7 flow (§5.3) |
| First real note on INC0010232 and parser check against it | **Verified live** with the TEST stand-in (row above). A **Nemotron**-written note is still pending (§5.2) |
| Runtime discovered in AI Control Tower | **Pending** (after AgentCore deploy) |

> **For a coding agent reading this:**
> - This is the integration spec.
> - Model calls go **only** through `modaas-agw` with a Nemotron alias; never call Bedrock or any public LLM endpoint.
> - ServiceNow is called **only from the backend**; never from the browser.
> - Do not change ServiceNow configuration, users or roles, or the inactive ServiceNow agent (ask Arth).
> - Never put the OAuth client secret, gateway keys, tokens or presigned URLs in the browser, logs or commits.
> - Never store or display model reasoning (think tags).
> - Acceptance criteria: §13.

---

## 0. TL;DR: what you must do, in order

1. **Merge** this package's `prooflab/servicenow/` and `prooflab/tests/` into your repo and run the tests (§3): `152 passed`.
2. **Configure** in the workshop IDE: the three ServiceNow secrets from handoff 1, plus `MODAAS_GATEWAY_URL` and `MODAAS_MODEL_ALIAS` (an *approved* Nemotron alias) (§4).
3. **Prove the governed path once:** `python3 -m prooflab.servicenow analyze --finding prooflab/servicenow/examples/test_finding_agent.json`, which should end in `WRITTEN` on INC0010232. Send Arth the output (§5.2).
4. **Attach the finding context** in your evaluator: `measured`, `limit`, `register` and the agents' `trace` (§5.0), plus `retest` when a passing re-test closes the finding. **This is what fills the movement and policy sections the judges will see.** Without it they honestly show "unknown".
5. **Call the agent from your evaluator loop** right after `notify()` returns `DELIVERED`, off the request path (§5.1).
6. **Deploy `ifabric_assurance_agent` on AgentCore** through the normal `new-agent.sh` flow with Sree's approval, then switch the backend from `gateway` to `agentcore` (§5.3). This is what AI Control Tower discovers.
7. **Add the dashboard:** one read-only endpoint (§7.1), then the drop-in panel or your own components, following **§8 for the Assurance Agent section** and **§8.7 for the five assurance sections**.
8. **Evidence:** save case snapshots and keep the agent's run records (§9). Rehearse the demo in §10 twice.

---

## 1. What changed since handoff 1

| Area | Change | Why it matters |
|---|---|---|
| Incident **description** | Now holds the **full finding block** (finding id, control, threshold version, scope, verdict + summary, detected time, evidence refs), capped at 4,000 characters by dropping whole evidence lines. | Readers without journal access (itil via the API, the agent) can see the evidence references. |
| `nemotron.py` (new) | `GatewayAnalyzer` (governed `POST /v1/chat/completions` to `modaas-agw`, alias, provenance header `x-modaas-action-id`, guardrail detection) and `CallableAnalyzer` (adapter for the AgentCore runtime). `strip_reasoning()` removes think tags. | Nemotron only through the governed door; provenance for every call. |
| `assurance_agent.py` (new) | `run_assurance_agent()`: facts → Nemotron → validate → one canonical note → guard → write → read back → run record + delivery log. | The enforcement point: the model can't hallucinate or be injected into the record. |
| `client.add_work_note()` (new) | PATCH that sends **only** `work_notes`. | Least privilege. |
| `analysis.py` (new) | Parses the note out of the work-notes display text; flags missing fields and a wrong finding id. | Our code, not the LLM, decides what counts as evidence. |
| `case_view.py` (new) | One JSON object per finding for the dashboard (§6), including `agent_analysis` and `agent_run`. Read-only; outages become data. | The dashboard contract. Safe to poll. |
| `check_response` | Never counts an analysis note, the integration user or the agent identity as the owner's reply; a logged reply is sticky in `case_view`. | AI-written notes must never look like human responses. |
| `export` | Adds `agent_analysis` to each incident export. | Analysis is in the Evidence Pack. |
| CLI | New `analyze`, `case`, `serve`. | Run the agent, snapshot evidence, standalone demo. |
| `panel/` (new) | Framework-free renderer (`ifabric-case-panel.js/.css`, `index.html`). | Drop-in dashboard component. |
| `finding_context.py` (new, v3) | Optional `measured`, `limit`, `register`, `trace` on a `Finding` (validated; never part of the finding id). The incident description shows `Measured:` / `Limit:` when present. | The data behind movement and policy alignment. |
| `assurance_checks.py` (new, v3) | Deterministic `movement`, `decision_trace`, `classify_evidence`, `policy_alignment`, `outcome_validation`, `summary_lines`. | The five sections; computed by code, not the model. |
| Note + run record (v3) | The note gains `Agent path`, `Policy alignment`, `Validation` lines (computed). The run record stores `movement` and `policy_alignment`. A `SKIPPED` re-run carries the writing run's record, so validation survives re-runs. | The analysis on the incident covers all five areas. |
| `case_view` (v3) | Five new top-level keys (§6). Same schema id: the change is additive. | One JSON drives the whole card. |
| Panel (v3) | Header pills (Policy x/y, Outcome, agents · gateway crossings) and an "Assurance analysis" block with five collapsible sections. Open/closed state survives the 10 s refresh. Theme: follows the OS, or forced with `data-ifab-theme`. | §8.7. |

---

## 2. How the Assurance Agent works

```
 evaluator (yours) ──Finding──► notify() ──► ServiceNow incident [iFabric]…  (owner = Sree)
                                   │ DELIVERED
                                   ▼
                       run_assurance_agent()                 ◄── runs in your evaluator loop / IDE,
                       (prooflab, holds SN creds)                 never in an agent's request path
   1 read incident (display values)       5 render ONE canonical note (+ computed lines: agent path,
                                            policy alignment, validation, provenance)
   2 facts = ground truth from Finding    6 guard: INC number, [iFabric], marker, ≤ 4000 chars
     + incident (owner, state, reply?)    7 PATCH work_notes only  →  read back  →  WRITTEN
   3 ask Nemotron ─────────────────────►  modaas-agw (guardrail ✔, ledger ✔, x-modaas-action-id)
       backend "gateway"  = direct governed call            │
       backend "agentcore"= AgentCore runtime ifabric_assurance_agent → modaas-agw
   4 strip think tags, parse, VALIDATE ◄──┘  (wrong fact / invented ref / "close" without re-test → REFUSED)
                                   │
            run record evidence/servicenow/assurance-agent/*.json  +  delivery-log ANALYSIS_<STATE>
                                   ▼
                       case_view() ──► your dashboard (§7–§8)
```

**Why it is split this way:**
- **Nemotron only via `modaas-agw`** (rules), so the model call is governed and leaves L1 evidence.
- **No ServiceNow credentials inside the agent runtime.** The orchestrator, which already holds them, does the write. The AgentCore agent is a pure analyzer: messages in, note out.
- **The model judges only three fields:** Measured vs limit, Evidence refs, Missing evidence. The nine fact fields (Finding ID, Control, Threshold version, Scope, Verdict, **Next step** (exact policy sentence per verdict), Owner, State, Owner response) are given to it and **must be echoed exactly**, or nothing is written. Prompt injection inside incident text can't change a verdict or the advice on the record.
- **Only our own notes are trusted.** Anyone with ServiceNow access can type a note that looks like the agent's, even with a fake journal header and a future timestamp. A note counts as the agent's only if its SHA-256 digest is in our delivery log (`ANALYSIS_WRITTEN` entries); notes are chosen by ServiceNow's display order, never by the header timestamp.

**The note** (written to the incident, parsed back by `analysis.py`):
```
[iFabric Assurance Agent analysis]
Finding ID: ifabric:C16:G-FM-v1:run:FM-B:finding
Control: C16 ACN-COST-001
Threshold version: G-FM-v1
Scope: run FM-B
Verdict: BREACHED
Measured vs limit: 10,800 tokens vs 10,000 cap (+800)
Evidence refs: gateway:action-123; ledger:cid=fault-1
Owner: Sree Annapurna Rallabandi
State: New
Owner response: No
Missing evidence: none
Next step: Close only after a linked passing re-test.
Agent path: customer-care-agent → it-ops-agent → network-fault-agent (3 agents, 3 gateway crossings)
Policy alignment: 7/8 pass; unknown: P5
Validation: facts echoed exactly; evidence refs within the finding; model reasoning removed and not stored; call via modaas-agw:nemotron-super-120b
Model: NVIDIA Nemotron via modaas-agw:nemotron-super-120b (alias nemotron-super-120b; model <id>; action <x-modaas-action-id>)
```
The model writes the first 12 lines. The last four (`Agent path`, `Policy alignment`, `Validation`, `Model`) are written by our code: from the finding, the delivery log and the gateway response, never by the model. A broken route rule shows as `…; ROUTE RULE BROKEN`; failing and unknown policy checks are listed by id (`5/8 pass; fail: P8; unknown: P1, P5`).

---

## 3. Merge and test

1. Take `prooflab/servicenow/` and `prooflab/tests/` from `code/prooflab/` in the handoff-3 package (the already-sent `servicenow-integration-package-v3.tgz` plus the P6 re-test fix, 152 tests) and **replace** yours (keep your other files).
2. `python3 -m pytest prooflab/tests -q` → **152 passed** (stdlib only; pytest is the only dev dependency).
3. New files:
   - `analysis.py`, `assurance_agent.py`, `nemotron.py`, `case_view.py`, `serve.py`, **`finding_context.py`, `assurance_checks.py`** (v3);
   - `panel/*`, including previews (all fake data):
     - `preview-{written,refused,forged-note}-fake-data.jpg` (card top);
     - `preview-assurance-{movement-policy,decision-trace,route-broken,refused,dark}-fake-data.jpg` (the five sections);
   - `examples/test_finding_agent.json`, now with a TEST register reference and a 5-step TEST trace;
   - **`examples/cases.sample-fake-data.json`**: four real `case_view()` outputs on fake data, with all five sections. **Build and test your dashboard against it:**
     - C16 full context: Policy 8/8, validated;
     - C7 route rule broken: M1/P8 fail;
     - C9 no context and REFUSED: unknowns, Outcome failed;
     - C16 forged note: red flags, NOT_RUN.
     Loading it with the panel's file picker shows the same thing;
   - tests `test_servicenow_{analysis,assurance_agent,case_view,serve,finding_context,assurance_checks}.py`, `fake_gateway.py`.
4. Changed: `finding.py`, `notifier.py`, `client.py`, `cli.py`, `fake_servicenow.py`.

---

## 4. Configuration

| Variable | Default | Meaning |
|---|---|---|
| `SNOW_INSTANCE`, `SNOW_CLIENT_ID`, `SNOW_CLIENT_SECRET` | required | As in handoff 1. **Backend only.** |
| `SNOW_OWNER_USER` | `annapurna@invences.com` | Owner assigned to incidents. |
| `SNOW_INTEGRATION_USER` | `ifabric.integration` | Our API identity; it also writes the analysis note; never counted as a responder. |
| `SNOW_AGENT_USER` | `ifabric.assurance.agent` | Reserved identity, never counted as a responder (harmless if unused). |
| `SNOW_AICT_URL` | unset | Link for step 5, e.g. `https://platformdemoh8.service-now.com/aiux/aict/home`. |
| `MODAAS_GATEWAY_URL` | required for `analyze` | The governed gateway base URL as your agents use it (in-cluster `http://…svc.cluster.local:…` or `https://…`). Plain http is refused unless the host is cluster-internal. |
| `MODAAS_MODEL_ALIAS` | required for `analyze` | An **approved** Nemotron alias (`nemotron-nano-9b`, `nemotron-nano-3-30b` or `nemotron-super-120b`). Check its live approval state first; the guide's examples conflict. |
| `MODAAS_API_KEY` | optional | Bearer token, only if your gateway requires one. Never logged. |
| `PROOFLAB_DELIVERY_LOG` | `evidence/servicenow/delivery-log.jsonl` | The **same** log `notify`, `check` and `analyze` write to. |

---

## 5. Running the Assurance Agent

### 5.0 Finding context your evaluator must attach (this fills the five sections)
Four **optional** keys on the finding dict you already pass to `finding_from_dict()` / `notify()`, plus a fifth, `retest`, at closure (below). They never change the finding id, so existing incidents still match. Each one you leave out turns the checks that need it into **unknown**: shown amber and never as a pass.

```json
{
  "control_ref": "C16", "control_id": "ACN-COST-001", "threshold_version": "G-FM-v1",
  "scope_kind": "run", "scope_id": "FM-B", "verdict": "BREACHED",
  "summary": "10,800 tokens > cap 10,000", "detected_at": "2026-10-05T10:00:00Z",
  "evidence": ["gateway:action-123", "ledger:cid=fault-1", "aict:trace-FM-B"],

  "measured": {"value": 10800, "unit": "tokens"},
  "limit":    {"value": 10000, "operator": "<=", "unit": "tokens"},
  "register": {"version_date": "2026-10-01", "owner": "annapurna@invences.com",
               "approval": "threshold approval INC00xxxxx"},
  "trace": [
    {"at": "2026-10-05T09:58:01Z", "actor": "customer-care-agent", "zone": "customer", "action": "receive fault report", "decision": "accepted", "ref": "span:cc-01",          "run_id": "FM-B"},
    {"at": "2026-10-05T09:58:03Z", "actor": "modaas-agw",          "zone": "gateway",  "action": "model_call",           "decision": "allowed",  "ref": "gateway:action-123", "run_id": "FM-B"},
    {"at": "2026-10-05T09:58:05Z", "actor": "it-ops-agent",        "zone": "it",       "action": "handoff",              "decision": "accepted", "ref": "span:it-07",         "run_id": "FM-B"},
    {"at": "2026-10-05T09:58:09Z", "actor": "modaas-agw",          "zone": "gateway",  "action": "tool_call",            "decision": "allowed",  "ref": "gateway:action-124", "run_id": "FM-B"},
    {"at": "2026-10-05T09:58:12Z", "actor": "network-fault-agent", "zone": "network",  "action": "run diagnostics",      "decision": "fault found", "ref": "span:nw-03",      "run_id": "FM-B"},
    {"at": "2026-10-05T09:58:20Z", "actor": "modaas-agw",          "zone": "gateway",  "action": "return path",          "decision": "allowed",  "ref": "gateway:action-125", "run_id": "FM-B"},
    {"at": "2026-10-05T09:58:22Z", "actor": "customer-care-agent", "zone": "customer", "action": "reply to customer",    "decision": "sent",     "ref": "span:cc-02",         "run_id": "FM-B"}
  ]
}
```

| Key | Rules | Feeds |
|---|---|---|
| `measured` | `value` a number (not bool); `unit` text | P1 (with `limit`), the incident description's `Measured:` line |
| `limit` | `value` a number; `operator` one of `<=` `<` `>=` `>` `==`; `unit` **must equal** `measured.unit` (else P1 is unknown). Read as: *measured operator limit* = within the limit. | P1: BREACHED must be outside the limit, SATISFIED inside; other verdicts stay unknown |
| `register` | `version_date` (ISO date of the frozen threshold version), `owner` (the **ServiceNow user name** of the named owner, the same value as `SNOW_OWNER_USER`), optional `approval` (the approval reference) | P2: version dated on or before the detection date; P3: owner matches |
| `retest` | only when a passing re-test closes the finding: `assessment` (the re-test's assessment id), `verdict` (one of the four verdicts), `threshold_version`, optional `at`. Attach it **before** the integration user resolves the incident. | P6: a Resolved/Closed incident passes only if `retest.verdict` is SATISFIED at the **same** threshold version; without it P6 fails ("closed without a linked passing re-test") |
| `trace` | up to 200 steps (keep the rest in the Evidence Pack); each step needs `at` (UTC ISO `…Z`), `actor`, `zone`, `action`; optional `decision`, `ref`, `run_id`. **`zone` vocabulary: `customer`, `it`, `network`, `gateway`** (anything else is shown as "other"). Put each gateway hop in as its own step with `zone: "gateway"`. For a run-scoped finding, set `run_id` = `scope_id` on every step. | movement (M1–M3), P8, the decision trace |

- All text values: at most 200 characters, no newlines. All values are untrusted input: the panel renders them as text only.
- **Route rule (M1/P8):** any step in zone `network` followed directly by a step in zone `customer` fails, so every return to the customer must pass a gateway step. This is computed only from the trace you provide; we don't observe traffic ourselves (gap list 16).
- Source it from what your agents and the gateway already log: AgentCore spans or your orchestrator's step log, plus the `x-modaas-action-id` of each gateway call as `ref`.
- The example finding `examples/test_finding_agent.json` carries a **TEST** register reference and a 5-step **TEST** trace, so the live wiring test fills all five sections.

### 5.1 When and where to call it
Call it **after** `notify()` returns `DELIVERED`, in the same evaluator loop, **never inside an agent's request path**:
```python
from prooflab.servicenow.assurance_agent import run_assurance_agent
from prooflab.servicenow.nemotron import GatewayAnalyzer

analyzer = GatewayAnalyzer.from_env()              # later: the AgentCore adapter (§5.3)
result = notify(finding, client, log, owner_user=OWNER)
if result.state == "DELIVERED":
    outcome = run_assurance_agent(finding, client, log, analyzer, owner_user=OWNER)
    # outcome.state in WRITTEN | UNVERIFIED | REFUSED | BLOCKED | FAILED | SKIPPED | NOT_DELIVERED
```
- It is idempotent: if a complete, matching note already exists it returns `SKIPPED`. Use `force=True` (CLI `--force`) for a deliberate re-run, for example after the owner replied.
- Typical latency is the model's: seconds to about a minute. Run it in a background worker or thread; the dashboard shows "pending" meanwhile.

### 5.2 First live proof (do this first, in the workshop IDE)
```bash
export SNOW_INSTANCE=platformdemoh8.service-now.com
read -rs "SNOW_CLIENT_ID?Client ID: " && export SNOW_CLIENT_ID; echo        # zsh; bash: read -rsp
read -rs "SNOW_CLIENT_SECRET?Client secret: " && export SNOW_CLIENT_SECRET; echo
export MODAAS_GATEWAY_URL=<the modaas-agw URL your agents use>
export MODAAS_MODEL_ALIAS=<an approved Nemotron alias>
export PROOFLAB_DELIVERY_LOG=evidence/servicenow/wiring-tests/delivery-log-ide-wiring-test.jsonl   # TEST log, never the production one
F=prooflab/servicenow/examples/test_finding_agent.json
python3 -m prooflab.servicenow notify --finding $F --dry-run      # reuses INC0010232 read-only → DELIVERED (writes nothing)
python3 -m prooflab.servicenow analyze --finding $F --out evidence/servicenow/wiring-tests/assurance-agent-ide
unset PROOFLAB_DELIVERY_LOG
```
- **Why the extra lines:**
  - This is a wiring test (`kind: wiring-test`), so its log entries and run record must stay out of the production `delivery-log.jsonl` and `assurance-agent/`.
  - `notify --dry-run` records the existing delivery in that test log, so the note's policy line counts P4 (owner notified) as passed. Without it, P4 would fail.
  - If the incident doesn't exist, it only logs `DRY_RUN` and creates nothing.
- Expected: `"state": "WRITTEN"`, `"number": "INC0010232"`, and a run record path. Open the incident: a new note is there, with `Model: NVIDIA Nemotron via modaas-agw:…`, the action id, and `Policy alignment: 6/8 pass; unknown: P1, P5`. P1 is unknown because the test verdict is INDETERMINATE; P5 is pending until the owner replies. The earlier TEST stand-in note stays below it: it isn't in this log, so it doesn't cause a skip.
- If you get `REFUSED`, read `reason`. The model echoed a wrong fact or invented a reference; that is the guard working. Try a larger alias or re-run once.
- `BLOCKED` means the guardrail filtered the call: keep that run record as adversarial evidence.
- Send Arth the JSON output and the run record. They update the §0 status table and confirm the parser against the real note.
- The two assumptions no fake can check are **already verified live** (2026-10-05, stand-in round-trip): the journal header format our parser reads, and that ServiceNow returns the note text unchanged (its SHA-256 digest round-trips). So `UNVERIFIED` is not expected. If it happens anyway, **don't re-run**. Run `python3 -m prooflab.servicenow export --finding prooflab/servicenow/examples/test_finding_agent.json` and send Arth the export file: its `notes_display.work_notes` is the raw display text. The `reason` already says which check failed: "no analysis note found on readback", or "digest differs" with both digests.

### 5.3 Deploy as an AgentCore agent (what AI Control Tower discovers)
The direct gateway call is governed and fine for evidence, but only an **AgentCore runtime** appears in AICT. Deploy `ifabric_assurance_agent` through the normal flow:
1. Create it with `new-agent.sh` (Strands template), name **`ifabric_assurance_agent`** (the `ifabric_` prefix is how our AICT connection identifies our agents).
2. Its handler is a **pure analyzer**: input `{"messages": [...]}`, output `{"text", "model_id", "action_id", "usage", "latency_ms"}`. No ServiceNow credentials. Simplest body (reuses our gateway client inside the image):
   ```python
   from prooflab.servicenow.nemotron import GatewayAnalyzer, AnalyzerError
   analyzer = GatewayAnalyzer.from_env()                 # MODAAS_GATEWAY_URL / MODAAS_MODEL_ALIAS in the AgentConfig
   def handle(payload):                                  # wire into the template's entrypoint
       try:
           r = analyzer.analyze(payload["messages"])
           return {"text": r.text, "model_id": r.model_id, "action_id": r.action_id,
                   "usage": r.usage, "latency_ms": r.latency_ms}
       except AnalyzerError as err:
           return {"error": err.kind, "action_id": err.action_id}
   ```
   If your template uses a Strands model provider pointed at `modaas-agw`, that is equally fine, as long as the output keeps this contract and the alias is a Nemotron one.
3. CodeBuild → ECR → AgentConfig CR → **Sree approves** (genuine attestation; capture `.status.governance.approvals`) → operator provisions → check READY.
4. In the orchestrator, switch the backend. Use whatever your app already uses to invoke AgentCore agents:
   ```python
   from prooflab.servicenow.nemotron import AnalyzerError, CallableAnalyzer
   def invoke(messages):
       out = invoke_your_agentcore_runtime("ifabric_assurance_agent", {"messages": messages})  # your existing helper
       if out.get("error"):
           raise AnalyzerError("blocked" if out["error"] == "blocked" else "unavailable",
                               out["error"], out.get("action_id"))
       return out
   analyzer = CallableAnalyzer(invoke, backend="agentcore:ifabric_assurance_agent",
                               model_alias=os.environ["MODAAS_MODEL_ALIAS"])
   ```
5. Record per run: the alias, resolved model id, image digest and CR generation (playbook §3). After about 20 minutes, check AICT Inventory for `ifabric_assurance_agent` (click **Execute Now** to refresh).

### 5.4 What the orchestrator enforces (our second enforcement point)
| Check | Refuses when | Outcome |
|---|---|---|
| Reasoning stripped | closed `<think>` blocks removed; everything before an orphan `</think>` dropped; an unclosed `<think>` yields no note; the **last** note marker wins (drafts inside the reasoning are never used) | REFUSED if no note remains |
| Format | no `[iFabric Assurance Agent analysis]` note in the reply | REFUSED |
| **Facts echoed exactly** | any of the 9 fact fields differs from ground truth (hallucination or injection), including **Next step ≠ the policy sentence for the verdict** | REFUSED |
| Evidence refs | a reference not present in the finding | REFUSED |
| Judged fields | any of the 3 is empty | REFUSED |
| Data block | incident text is wrapped in `<<<INCIDENT TEXT … INCIDENT TEXT>>>`; any run of 3+ `<`/`>` is removed from the text, so the closing delimiter can't be forged | (prompt hygiene) |
| Echoed text in reasons | model text quoted in refusal reasons is cut to 60 characters | (no log or panel flooding) |
| Trusted notes only | `SKIPPED` only if the existing note's digest is in our run log **and** its facts match the finding; forged notes never cause a skip | — |
| Owner reply | a live owner reply is written to the delivery log **before** our note becomes the incident's last update | — |
| Write guard | number not `INC…`, short description not `[iFabric]`, note > 4,000 characters | REFUSED |
| Guardrail | gateway returns `content_filter` | BLOCKED |
| Readback | the note is not found after the write | UNVERIFIED |

Every attempt (up to 2) is recorded. The model is asked again once if the first answer fails.

### 5.5 Outcomes and what to do
| State | Meaning | Dashboard | Action |
|---|---|---|---|
| `WRITTEN` | Note written and read back | green "present" | none |
| `SKIPPED` | A complete note that our run log vouches for already exists | as before | none |
| `REFUSED` | Model output failed a check; nothing written | red, with reason | Re-run once; if it persists, show it as an honest failure (gap list) |
| `BLOCKED` | MoDaaS guardrail filtered the call | red, with action id | Keep as adversarial evidence |
| `FAILED` | Gateway or ServiceNow unavailable | red, with error | Retry later |
| `UNVERIFIED` | Write sent, readback didn't confirm | amber or red | Re-run `analyze` (it SKIPs if the note is actually there) |
| `NOT_DELIVERED` | No incident for this finding | grey | run `notify` first |

### 5.6 Evidence it produces
- **Run record** `evidence/servicenow/assurance-agent/<finding>_<utc>_<n>.json` (schema `ifabric.assurance-agent.run/v1`). It contains:
  - finding id, incident number, backend, model alias;
  - the facts given to the model;
  - per attempt: prompt SHA-256, response SHA-256, `think_stripped`, `x-modaas-action-id`, model id, token usage, latency, finish reason, problems;
  - outcome, reason, the exact note written and its SHA-256, start and finish UTC.
  - **No reasoning text is stored**, only hashes of the raw response.
- **Delivery log** entry `ANALYSIS_<STATE>` with backend, alias, action ids, the run-record path and, for written notes, `note_digest` (SHA-256 of the note). That digest is how the dashboard and the next run recognise the agent's genuine note. A `SKIPPED` entry carries the backend, action ids and run-record path **of the run that wrote the note in place**, so re-running the agent never downgrades the outcome validation.
- The run record also holds `movement` and `policy_alignment` exactly as computed at analysis time.
- **On the incident**: the note itself, with the provenance line.
- **Join to L1**: `x-modaas-action-id` joins the analysis to the gateway and ledger records of the same call.

### 5.7 Two "five facets" layers (render both, labelled)
The Assurance Agent is "our agent" too, and the agent runs carry their own five facets. They grade different things:

| Layer | Grades | Ids | Lives in | Console |
|---|---|---|---|---|
| **Assurance Agent's five sections** (§5.0, §8.7) | One **finding and its human loop**: movement M1–M3 (route rule: no network → customer hop without a gateway), decision trace, evidence, policy P1–P8 (verdict vs limit, dated before the test, owner matches, notified, response recorded, no closure without re-test, evidence attached, route rule), validation V1–V6 (the agent's own output) | M*, P1–P8, V1–V6 | the case JSON (`servicenow/cases/*.json`) | Human Loop step 4: "Assurance analysis" block, exactly as §8.7 |
| **The run's five facets** (`05-…` §4–§6) | One **agent run's decisions**: journey hops, structured decisions, cited evidence, AP-v1 policies (P-EVID-01 … P-ACTION-06), outcome vs the independent scenario spec | P-*-0n, AP-v1 | `runs/<cid>/run.json` | Agent Trail |

**One orchestrator record feeds both.** `ifabric-run` writes the hops once. The publisher maps them into the finding's `trace` (§5.0):
- every `gateway-A`/`gateway-B`/`return-path` hop and every model call → a step with `zone: "gateway"`;
- agent steps keep `customer` / `it` / `network`;
- `ref` = `gateway:action_id=…`;
- `run_id` = the run alias.


---

## 6. The case contract: `ifabric.servicenow.case/v1`

`case_view(finding, client, log, owner_user, cutoff, integration_user=…, agent_user=…, aict_url=None)`:

```json
{
  "schema": "ifabric.servicenow.case/v1",
  "generated_at": "2026-10-05T14:05:00Z",
  "finding_id": "ifabric:C16:G-FM-v1:run:FM-B:finding",
  "finding": {"control_ref": "C16", "control_id": "ACN-COST-001", "threshold_version": "G-FM-v1",
              "scope_kind": "run", "scope_id": "FM-B", "verdict": "BREACHED",
              "summary": "10,800 tokens > cap 10,000", "detected_at": "2026-10-05T14:02:47Z",
              "evidence": ["gateway:action-123", "ledger:cid=fault-1"], "kind": "finding"},
  "delivery": {"state": "DELIVERED", "at": "2026-10-05T14:03:20Z", "number": "INC0010240"},
  "servicenow": {"status": "ok", "sys_id": "…", "url": "https://platformdemoh8.service-now.com/incident.do?sys_id=…",
                 "number": "INC0010240", "short_description": "[iFabric][C16 …", "state": "New",
                 "owner": "Sree Annapurna Rallabandi", "urgency": "2 - Medium",
                 "updated_at": "2026-10-05 07:04:10", "updated_by": "ifabric.integration"},
  "response": {"state": "AWAITING_RESPONSE", "actor": null, "at": null,
               "cutoff": "2026-10-06T14:00:00Z", "source": "live"},
  "agent_run": {"state": "WRITTEN", "at": "2026-10-05T14:04:02Z", "reason": null,
                "backend": "agentcore:ifabric_assurance_agent", "model_alias": "nemotron-super-120b",
                "action_ids": ["agw-7f3c91"], "evidence": "evidence/servicenow/assurance-agent/…json"},
  "agent_analysis": {"status": "present", "at": "2026-10-05 07:04:10", "author": "iFabric Integration",
                     "fields": {"Finding ID": "…", "Control": "C16 ACN-COST-001", "Threshold version": "G-FM-v1",
                                "Scope": "run FM-B", "Verdict": "BREACHED",
                                "Measured vs limit": "10,800 tokens vs 10,000 cap (+800)",
                                "Evidence refs": "gateway:action-123; ledger:cid=fault-1",
                                "Owner": "Sree Annapurna Rallabandi", "State": "New", "Owner response": "No",
                                "Missing evidence": "none", "Next step": "Close only after a linked passing re-test.",
                                "Agent path": "customer-care-agent → it-ops-agent → network-fault-agent (3 agents, 3 gateway crossings)",
                                "Policy alignment": "7/8 pass; unknown: P5",
                                "Validation": "facts echoed exactly; evidence refs within the finding; model reasoning removed and not stored; call via agentcore:ifabric_assurance_agent",
                                "Model": "NVIDIA Nemotron via agentcore:ifabric_assurance_agent (alias nemotron-super-120b; model …; action agw-7f3c91)"},
                     "missing_fields": [], "complete": true, "finding_matches": true,
                     "facts_match": true, "verified": true, "note_sha256": "…"},
  "links": {"incident": "https://platformdemoh8.service-now.com/incident.do?sys_id=…",
            "aict": "https://platformdemoh8.service-now.com/aiux/aict/home"},

  "movement": {"steps": [{"at": "2026-10-05T09:58:01Z", "actor": "customer-care-agent", "zone": "customer",
                          "action": "receive fault report", "decision": "accepted", "ref": "span:cc-01", "run_id": "FM-B"}, "…"],
               "path": ["customer-care-agent", "modaas-agw", "it-ops-agent", "modaas-agw", "network-fault-agent", "modaas-agw", "customer-care-agent"],
               "agents": ["customer-care-agent", "it-ops-agent", "network-fault-agent"],
               "zones": ["customer", "gateway", "it", "gateway", "network", "gateway", "customer"],
               "gateway_crossings": 3,
               "checks": [{"id": "M1", "label": "No direct network → customer hop (every return passes a gateway)",
                           "status": "pass", "detail": "every network → customer movement crossed a gateway"},
                          {"id": "M2", "label": "Every step belongs to this run", "status": "pass", "detail": "all 7 steps carry run FM-B"},
                          {"id": "M3", "label": "Every step has a valid UTC timestamp", "status": "pass", "detail": "7/7 valid"}]},
  "decision_trace": [{"at": "2026-10-05T09:58:03Z", "source": "gateway", "actor": "modaas-agw", "decision": "allowed",
                      "detail": "model_call (gateway)", "ref": "gateway:action-123"},
                     {"at": "2026-10-05T10:00:00Z", "source": "control", "actor": "C16 evaluator", "decision": "BREACHED",
                      "detail": "measured 10,800 tokens", "ref": "ACN-COST-001 v=G-FM-v1"},
                     {"at": "2026-10-05T14:04:00Z", "source": "assurance_agent", "actor": "modaas-agw:nemotron-super-120b",
                      "decision": "attempt 1: checks passed", "detail": "facts echoed; refs within finding", "ref": "agw-7f3c91"},
                     "…"],
  "evidence": [{"ref": "gateway:action-123", "kind": "gateway", "used_by_agent": true},
               {"ref": "aict:trace-FM-B", "kind": "aict", "used_by_agent": false}],
  "policy_alignment": {"passed": 7, "total": 8,
                       "checks": [{"id": "P1", "label": "Verdict follows from measured value vs limit", "status": "pass",
                                   "detail": "10,800 tokens vs limit <= 10,000 → outside"},
                                  {"id": "P5", "label": "Owner response or silence recorded", "status": "unknown",
                                   "detail": "pending until the cutoff"}, "… P2–P4, P6–P8 pass"]},
  "outcome_validation": {"status": "validated",
                         "checks": [{"id": "V1", "label": "Assurance Agent run completed", "status": "pass", "detail": "WRITTEN"}, "… V2–V6"]}
}
```

| Field | Values | Show as |
|---|---|---|
| `finding.verdict` | BREACHED, ESCALATED, INDETERMINATE, SATISFIED | red / amber / amber / green |
| `delivery.state` | DELIVERED, FAILED, UNVERIFIED, OUTCOME_UNKNOWN, DRY_RUN, NOT_SENT | only DELIVERED is green |
| `servicenow.status` | ok, no_incident, unreachable (+ `error`) | unreachable is red, with its error |
| `response.state` | RESPONDED, AWAITING_RESPONSE, NO_RESPONSE_OBSERVED, RESPONSE_UNKNOWN, NOT_DELIVERED | silence after the cutoff is a **recorded result** |
| `response.source` | live, delivery_log | delivery_log = a reply recorded earlier and kept |
| `agent_run.state` | NOT_RUN, WRITTEN, SKIPPED, REFUSED, BLOCKED, FAILED, UNVERIFIED, NOT_DELIVERED | §8.2 |
| `agent_analysis.status` | present, pending, not_applicable, unknown | §8.2 |
| `agent_analysis.complete` / `finding_matches` / `facts_match` / `verified` | booleans (`verified` may be null when no log was given) | any false means "incomplete", never green. `facts_match`: the static facts (finding id, control, version, scope, verdict, next step) equal the finding. `verified`: the note's digest is in our run log (not a forgery) |

The five assurance sections:

| Key | Shape | Values |
|---|---|---|
| `movement` | `steps[]`, `path[]` (actors in order, repeats collapsed), `agents[]` (non-gateway, first-seen order), `zones[]`, `gateway_crossings`, `checks[M1–M3]` | `steps` empty = no trace provided; checks then unknown |
| `decision_trace[]` | `{at, source, actor, decision, detail, ref}` sorted by time; undated last; same-second events keep pipeline order (agents → control → ServiceNow → owner → model attempts → agent outcome) | `source`: `agent`, `gateway`, `control`, `servicenow`, `owner`, `assurance_agent` |
| `evidence[]` | `{ref, kind, used_by_agent}` | `kind` = text before the first `:` (`gateway`, `ledger`, `aict`, `test`, …) or `record` |
| `policy_alignment` | `{passed, total, checks[P1–P8]}` | `passed` counts passes only; unknown is not a pass |
| `outcome_validation` | `{status, checks[V1–V6]}` | `status`: `validated` (all pass), `failed` (any fail), `pending` (otherwise) |
| every `checks[]` item | `{id, label, status, detail}` | `status`: `pass`, `fail`, `unknown`. Render unknown as grey "?" or amber, never green |

Notes:
- `servicenow.*` values are **display values**; their times are in the API user's ServiceNow time zone. Times from our code (`generated_at`, `delivery.at`, `agent_run.at`, `finding.detected_at`) are UTC `…Z`.
- **The contract is additive within v1:** the five sections were added without changing the schema id, new keys may appear later, and key order is meaningless. The panel tolerates their absence: an older snapshot renders without the assurance block. **Any proxy or API layer on your side must pass unknown keys through unchanged** (don't map to a fixed DTO that drops them).

---

## 7. Dashboard integration: the Evidence Console (zero trust)

### 7.1 The console never calls ServiceNow: the evaluator loop writes case snapshots
The console holds **no** secrets (`02-ARCHITECTURE.md` §6). So it does **not** call `case_view()` itself:
- The **evaluator loop** (`prooflab watch`, which already holds the ServiceNow credentials and owns the delivery log) writes a snapshot of every finding every 10–30 s:
  ```bash
  python3 -m prooflab.servicenow case --finding <finding.json> --cutoff <judging start UTC> --out evidence/servicenow/cases
  ```
- The console serves those files at `GET /api/v1/cases` (LIVE mode reads the growing directory; PACK mode reads the frozen copies in the pack).
- **The snapshots must be written by the process that owns `delivery-log.jsonl`** (the trust anchor). Otherwise every genuine note shows red ("not in the agent's run log") and `agent_run` shows `NOT_RUN`.
- Use the same `cutoff` everywhere (judging start).
- **Pass unknown keys through unchanged.** The five sections were added inside v1; don't map snapshots to a fixed DTO that drops keys.

For an app that legitimately holds the credentials (not our console), the equivalent is one read-only, 10 s-cached endpoint:
```python
from prooflab.servicenow.case_view import case_view          # + ServiceNowClient.from_env(), DeliveryLog(...), finding_from_dict
def cases_json(finding_dicts, cutoff):                         # GET /api/servicenow/cases -> JSON list
    return [case_view(finding_from_dict(d), client, log, owner_user=os.environ["SNOW_OWNER_USER"],
                      cutoff=cutoff, aict_url=os.environ.get("SNOW_AICT_URL")) for d in finding_dicts]
```
It is GET only: no dashboard endpoint may call `notify`, `check` or `analyze`, or write anything.

### 7.2 Recommended: embed the drop-in panel as the console's Human Loop view
```html
<link rel="stylesheet" href="/static/ifabric-case-panel.css">          <!-- copied from prooflab/servicenow/panel/ -->
<script src="/static/ifabric-case-panel.js" defer></script>
<div id="human-loop" data-ifab-theme="dark"></div>                     <!-- match the console theme -->
```
```js
const res = await fetch('/api/v1/cases', {credentials: 'same-origin'});
IFabricCasePanel.render(document.getElementById('human-loop'), (await res.json()).data);   // LIVE: IFabricCasePanel.poll(el, url, 10000)
```
- The panel renders everything in §8 (the 5-step chain, the analysis groups, the header pills and the five assurance sections), text-only, with no inline script or style, so the console's CSP holds.
- `data-ifab-theme` is `"dark"` or `"light"` (default: follows the OS). Open/closed sections survive the 10 s refresh. It works from 360 px up.
- **The demo does exactly this**: `demo/index.html` → **G · Human Loop** renders the real v3 panel (`demo/assurance-panel/ifabric-case-panel.{js,css}`, byte-identical to `prooflab/servicenow/panel/`). Its six cases (`assurance-panel/cases.js`) are built from the demo story by `demo/assurance-panel/make_cases.py`, which calls the real prooflab functions (`_analyze`, `render_note`, `latest_agent_analysis`, the M/P/V checks), so INC0090216–220 and the H2 injected ticket INC0090222 match every other screen. `#/loop/<INC or finding_id>` opens one case; each card links to its Answer and Six Questions, and the ids join the thread highlight. The prooflab fixture `examples/cases.sample-fake-data.json` stays the component's own test fixture.

### 7.3 Standalone page (also the backup demo)
```bash
python3 -m prooflab.servicenow serve --finding evidence/findings/C16_FM-B.json --cutoff 2026-10-06T14:00:00Z --port 8765
```
It binds to 127.0.0.1, rejects any request whose `Host` header isn't a loopback name (stops DNS-rebinding pages reading `/cases.json`), is read-only, and sends CSP and nosniff headers.

Offline: open `prooflab/servicenow/panel/index.html` from disk and load snapshots with its file picker.

### 7.4 Your own components (only if not embedding the panel)
Follow §8 exactly. Render every string as text (never `innerHTML` or `dangerouslySetInnerHTML`): incident text is untrusted. Render links only if `http(s)`.

### 7.5 Security checklist
- [ ] ServiceNow and gateway secrets only in the evaluator loop's environment. Nothing in the console process, bundles, HTML or logs.
- [ ] No write endpoints; the Human Loop view is read-only, with no "re-run analysis" button in PACK (judge) mode.
- [ ] All agent and incident text rendered as text.
- [ ] Panel assets served from the console's own origin.
- [ ] The console stays loopback-only with its session token (`07-CONSOLE-API-AND-SECURITY.md`).

---

## 8. Dashboard: the Assurance Agent section (detailed)

This is step 4 of each case card. **Prerequisite:** the backend reads the evaluator's delivery log (§7.1); trust and run outcomes come from it. It must answer, without narration: *what did the agent conclude, which parts are verified fact versus model judgement, which model produced it through which governed call, and if nothing was written, why.*

### 8.1 Layout (top to bottom)
```
4  Assurance Agent analysis (Nemotron)   [present | incomplete | pending | REFUSED | BLOCKED | FAILED | UNVERIFIED]
   [all fields present] [finding id matches] [facts match the finding] [written by the agent (in run log)]
                                                                   ← four flag chips (green, or red when false)
   CHECKED AGAINST THE FINDING                                     ← group A: 9 fact fields
     Finding ID · Control · Threshold version · Scope · Verdict · Next step · Owner · State · Owner response
   NEMOTRON'S JUDGEMENT                                            ← group B: 3 judged fields
     Measured vs limit · Evidence refs · Missing evidence
   Provenance   NVIDIA Nemotron via <backend> (alias …; model …; action <x-modaas-action-id>)
   Written <ServiceNow time> by iFabric Integration (ServiceNow display time)
   [if the latest run failed after an earlier note: red "A later run did not write a new note" + run facts]
```
Field sources:

| UI element | JSON path | Notes |
|---|---|---|
| Status badge | derived (§8.2) | never green unless `present` and all four flags are true |
| Flag chips | `agent_analysis.complete` (+ `.missing_fields`), `.finding_matches`, `.facts_match`, `.verified` | red chip text for false: "missing: …", "finding id does not match", "facts differ from the finding", "not in the agent's run log" |
| Group A values | `agent_analysis.fields[name]` for the 9 fact names | label the group "Checked against the finding" |
| Group B values | `agent_analysis.fields[name]` for the 3 judged names | label it "Nemotron's judgement" |
| Provenance | `agent_analysis.fields.Model` | monospace; the action id is the join key to gateway/ledger |
| Written at/by | `agent_analysis.at`, `.author` | ServiceNow display time |
| Run facts | `agent_run.state/at/reason/backend/action_ids/evidence` | shown when no note, or when the latest run failed |

Field-name arrays to copy (same as `assurance_agent.FACT_FIELDS` / `JUDGED_FIELDS`):
```js
const FACT_FIELDS = ['Finding ID','Control','Threshold version','Scope','Verdict','Next step','Owner','State','Owner response'];
const JUDGED_FIELDS = ['Measured vs limit','Evidence refs','Missing evidence'];
```

### 8.2 Status logic (implement exactly)
```js
function agentStatus(c) {
  const a = c.agent_analysis || {status: 'unknown'}, run = c.agent_run || {state: 'NOT_RUN'};
  if (a.status === 'present')
    return (a.complete && a.finding_matches && a.facts_match !== false && a.verified !== false) ? 'present' : 'incomplete';
  if (['REFUSED','BLOCKED','FAILED','UNVERIFIED'].includes(run.state)) return run.state;
  return a.status;                       // 'pending' | 'not_applicable' | 'unknown'
}
```
| Status | Colour | Body text |
|---|---|---|
| present | green | groups A and B + provenance |
| incomplete | red | same, plus the red chips. A forged note (not in our run log) always lands here; never show it as the agent's analysis |
| pending | amber | "Waiting for the Nemotron assurance agent (usually under a minute after the incident is raised)." After **5 minutes** from `delivery.at`, switch to red `NO_ANALYSIS` "The assurance agent did not write an analysis within 5 minutes of delivery." Compute in the browser; never fake a result. **The drop-in panel already does this**; implement it yourself only for Option C. |
| REFUSED / BLOCKED / FAILED | red | "The assurance agent ran but no note was written." + `reason`, `backend`, action ids, run record path |
| UNVERIFIED | amber | same as above; re-run will confirm |
| not_applicable | grey | "No incident yet." |
| unknown | red | "Could not read the incident notes." |

### 8.3 Native markup example (Option C)
Build it with DOM APIs or JSX; the important parts are text-only rendering and the two groups.
```js
function renderAgentSection(container, c) {           // container: an empty element you own
  const a = c.agent_analysis || {}, run = c.agent_run || {}, f = a.fields || {};
  const h = (tag, text, cls) => { const n = document.createElement(tag); if (cls) n.className = cls;
                                  if (text != null) n.textContent = String(text); return n; };
  const dl = (names) => { const d = h('dl'); names.forEach(k => { if (f[k] == null) return;
                           d.append(h('dt', k), h('dd', f[k])); }); return d; };
  container.replaceChildren(h('h4', 'Assurance Agent analysis (Nemotron)'), h('span', agentStatus(c), 'badge'));
  if (a.status === 'present') {
    container.append(h('div', 'Checked against the finding', 'group-title'), dl(FACT_FIELDS),
                     h('div', "Nemotron's judgement", 'group-title'), dl(JUDGED_FIELDS),
                     h('div', 'Provenance: ' + (f.Model || 'missing'), 'mono'));
  } else if (['REFUSED','BLOCKED','FAILED','UNVERIFIED'].includes(run.state)) {
    container.append(h('p', 'The assurance agent ran but no note was written: ' + (run.reason || run.state)),
                     h('p', 'Gateway action ids: ' + (run.action_ids || []).join(', '), 'mono'));
  } else {
    container.append(h('p', 'Waiting for the Nemotron assurance agent…'));
  }
}
```
React: same structure; use `{value}` interpolation only.

### 8.4 Linking the analysis to the rest of the evidence
- **Gateway / ledger (L1):** show the `action …` id from the provenance line (or `agent_run.action_ids`) as copyable text. If your dashboard already has a gateway or ledger view, link it with that id; it is the same `x-modaas-action-id` your controls use.
- **Incident:** `links.incident` opens the ServiceNow incident with the same note.
- **Run record:** `agent_run.evidence` is the file path in the Evidence Pack; show it as text or as a link to your evidence browser.
- **AI Control Tower:** step 5 (`links.aict`). After AgentCore deployment, the `ifabric_assurance_agent` runtime is in AICT Inventory.

### 8.5 What the dashboard must never do
- Show the model's reasoning, or anything from the raw response other than the parsed note.
- Turn REFUSED, BLOCKED or incomplete into green, or hide them.
- Offer a "re-run analysis" button in the judge-facing view. Re-runs are an operator action (`analyze --force`) and are logged.
- Edit or "fix" the note text. If it's wrong, it's shown as wrong, and the run is repeated.

### 8.6 Demo talking points for this section (one sentence each)
1. "This analysis is from NVIDIA Nemotron, called only through our governed MoDaaS gateway; here's the gateway action id."
2. "The top group is fact our code checked against the finding; the model only judged the bottom three lines."
3. "If the model gets a fact wrong or is tricked by text in the ticket, nothing is written, and you see it here as REFUSED with the reason."
4. "Below, the assurance analysis: how the agents moved, every decision in order, the evidence, policy alignment and whether the agent's own output checks out, all computed by code, and unknown is never green."

### 8.7 The five assurance sections (header pills + "Assurance analysis" block)

> **Proposed panel refinements** (owner: the ServiceNow session; optional): title an untrusted note (`verified === false`) "Note text: not written by the agent (untrusted)" rather than showing it under "Checked against the finding"; label step 5 "AICT inventory entry" unless an AICT Monitor trace exists (gap A3).

The drop-in panel renders all of this; implement it yourself only for Option C. Previews: `panel/preview-assurance-*-fake-data.jpg`. Fixture with every state: `examples/cases.sample-fake-data.json`.

**Card layout:**
```
[BREACHED] C16 ACN-COST-001 · v=G-FM-v1 · run FM-B
ifabric:C16:G-FM-v1:run:FM-B:finding
(Policy 8/8) (Outcome validated) (3 agents · 3 gateway crossings)      ← header pills
1 … 5   the evidence chain (§8.1)
─────────────────────────────────────────────
Assurance analysis
Computed by our checks … Unknown means not provided, never passed.
▾ Agent movement                              (3 agents · 3 gateways)   ← open by default
   [customer-care-agent] → [modaas-agw] → [it-ops-agent] → [modaas-agw] → [network-fault-agent] → [modaas-agw] → [customer-care-agent]
   ▸ All 7 steps  (table: time, agent, zone, action, decision, record)
   ✓ M1 …   ✓ M2 …   ✓ M3 …
▾ Decision trace                              (14 decisions)            ← open by default
   09:58:03Z ● GATEWAY [allowed] modaas-agw / model_call (gateway) / gateway:action-123
   10:00:00Z ● CONTROL [BREACHED] C16 evaluator / measured 10,800 tokens
   …        ● ASSURANCE AGENT [attempt 1: checks passed] … → [WRITTEN]
▸ Evidence                                    (3 records · 2 cited)
▸ Policy alignment                            (8/8 pass)
▸ Outcome validation                          (validated)
```

**Pills (header) and section summaries:**

| Element | Source | Tone |
|---|---|---|
| `Policy x/y` | `policy_alignment.passed` / `.total` | red if any check fails; green if all pass; amber otherwise (some unknown) |
| `Outcome <status>` | `outcome_validation.status` | validated green · failed red · pending amber |
| `N agents · M gateway crossings` | `movement.agents.length`, `.gateway_crossings` | neutral; amber `Agent path not provided` when `steps` is empty |
| Movement summary | same counts (`N agents · M gateways`) | red if M1 fails; green with a trace; neutral without |
| Decision trace summary | `decision_trace.length` | neutral |
| Evidence summary | `evidence.length` records · count of `used_by_agent` cited | red if no records |
| Policy summary | `x/y pass · f fail · u unknown` | red / amber / green as the pill |
| Outcome summary | `status` | as the pill |

Use singular/plural correctly ("1 gateway"). Every section is a `<details>`: Movement and Decision trace open by default, the others closed; keep the viewer's open/closed choice across refreshes (key it by `finding_id` + section title).

**Agent movement:**
- A wrapping chip flow over `movement.path`. Each chip shows the actor (underscores shown as spaces) and its zone. Colour by zone: customer blue, IT violet, network teal, **gateway amber with a dashed border**, other grey. Arrows go between chips; on narrow screens the flow stacks vertically with ↓.
- **Broken hop:** where a `network` chip is followed directly by a `customer` chip, outline the customer chip in red, make the arrow red, and add the text "✕ no gateway before this hop". This is the same condition as M1.
- A collapsed "All N steps" table (`movement.steps`).
- Then the M1–M3 checklist.
- With no trace, show: "The evaluator did not attach the agents' trace to this finding, so movement checks are unknown (never assumed to pass)."

**Decision trace:** a vertical timeline in `decision_trace` order. Each row has:
- time as `HH:MM:SSZ` (full ISO in the tooltip);
- a coloured dot and a source label (Agent blue, Gateway amber, Control red, ServiceNow teal, Owner violet, Assurance Agent green);
- a decision badge;
- the actor;
- then `detail` and `ref` (monospace) below.

Badge tone: red if the decision contains refus/deny/block/fail/breach; green if it contains allow/written/pass/deliver/respond/skipped; neutral otherwise.

**Evidence:** one row per `evidence[]` item:
- a kind badge (gateway, ledger, aict, test, record), the ref in monospace, and "✓ cited by the agent" when `used_by_agent`;
- below the list: the incident link, `agent_run.evidence` (run record path) and `agent_run.action_ids`.

**Policy alignment / Outcome validation / movement checks:** one checklist component.
- Glyph: ✓ green for pass, ✕ red for fail, ? grey for unknown, with the status also as visually hidden text for screen readers.
- Then the `id` in monospace, the `label` in bold, and `detail` muted below.
- Never reorder or hide checks; never recolour unknown as pass.

**Option C sketch** (text-only rendering, same as §8.3):
```js
const GLYPH = {pass: '✓', fail: '✕', unknown: '?'};
function checklist(checks) {
  const ul = document.createElement('ul');
  for (const k of checks || []) {
    const li = document.createElement('li'); li.className = 'check check-' + k.status;
    const g = document.createElement('span'); g.textContent = GLYPH[k.status] || '?'; g.setAttribute('aria-hidden', 'true');
    const id = document.createElement('code'); id.textContent = k.id;
    const label = document.createElement('strong'); label.textContent = k.label;
    const sr = document.createElement('span'); sr.className = 'visually-hidden'; sr.textContent = k.status;
    const detail = document.createElement('div'); detail.textContent = k.detail;
    li.append(g, id, label, sr, detail); ul.append(li);
  }
  return ul;
}
// Render only when c.movement && c.policy_alignment && c.outcome_validation (older snapshots lack them).
```

---

## 9. Evidence: what to save, where

| Artifact | How | Path |
|---|---|---|
| Case snapshot per named run (what the judge sees, frozen) | `python3 -m prooflab.servicenow case --finding <f> --cutoff <c> --out evidence/servicenow/cases` (prints `sha256=`) | `evidence/servicenow/cases/<finding_id>.json` |
| Assurance Agent run records | `analyze` / `run_assurance_agent` | `evidence/servicenow/assurance-agent/*.json` |
| Incident readback incl. parsed analysis | `export` | `evidence/servicenow/incidents/INC*.json` |
| Delivery / response / analysis history | automatic | `evidence/servicenow/delivery-log.jsonl` |
| Gateway / ledger records for the analysis calls | your L1 capture, joined by `x-modaas-action-id` | `evidence/raw/gateway/`, `raw/ledger/` |
| Superseded ServiceNow-LLM prototype (history only) | already saved | `evidence/servicenow/sn-agent/` (`status: SUPERSEDED`) |

Rules:
- Snapshot after the analysis is present and after the final `check`.
- Add every file's SHA-256 to `MANIFEST.json`.
- **Never** save model reasoning.
- Adversarial cases (an injected ticket that ends REFUSED, a guardrail BLOCKED) go to `evidence/adversarial/` with their run records.

---

## 10. The 2-minute demo (and the backup)

1. **Before:** named runs in `run-ids.txt`; dashboard open; `SNOW_AICT_URL` set; the AgentCore runtime READY.
2. Trigger the breaching run. **Steps 1–3 appear within ~10 s** (DELIVERED, owner, AWAITING).
3. While step 4 is pending, say: "Nemotron is analysing this through the governed gateway; our code checks every fact before anything is written."
4. **Step 4 fills in:** the green badge, two groups, and provenance with the action id. Optionally show the same action id in the gateway or ledger view.
5. **Scroll to "Assurance analysis":** walk through the agent path (three gateway crossings, route rule ✓), the decision trace from the first agent step to the agent's WRITTEN, and the header pills "Policy 8/8 · Outcome validated".
6. Click the incident link: the same note is on the ServiceNow incident, with the `Agent path`, `Policy alignment` and `Validation` lines. Step 5: AICT shows `ifabric_assurance_agent`.
7. Optional adversarial beats:
   - a pre-recorded REFUSED case (injected ticket text) shows the guard working;
   - a run whose trace skips the gateway shows the red "no gateway before this hop", M1 failing, and P8 failing in policy alignment.

**Backup:** open `prooflab/servicenow/panel/index.html` from disk and load the saved case snapshots (file picker). Keep the recorded video.

---

## 11. Gap-list additions (copy into `gap-list.md`)
9. **Agent location:** Nemotron is reachable only via `modaas-agw` (no public endpoints), so the Assurance Agent runs on AWS and writes into ServiceNow; a ServiceNow-native agent cannot use Nemotron on this instance. The ServiceNow-LLM prototype is inactive and kept as history.
10. **AICT visibility:** only the AgentCore runtime is discoverable; direct gateway calls (backend `gateway`) are governed and ledger-recorded but not AICT assets.
11. **Note authorship:** the note is written by the integration user (`iFabric Integration`); the model and the call are identified by the `Model:` provenance line and the run record.
12. **Response detection after the note:** itil sees only the last updater; the note becomes the last update. Run `check` on a short loop; a logged reply is sticky in `case_view`.
13. **Model variance:** the model may echo a fact wrongly; such runs are REFUSED (not written) and shown as failures.
13a. **Forged notes:** anyone with ServiceNow write access can add a look-alike note; it is never trusted (digest not in our run log) and is shown red. The run log itself is the trust anchor, so it is in the Evidence Pack with its SHA-256.
14. **Display time zone:** ServiceNow display times vs our UTC timestamps.
15. **Shown vs proven:** state which refusal and guardrail paths were demonstrated live and which exist only in tests.
16. **Movement and policy depend on evaluator context:** agent movement, the route rule (M1/P8), P1 (measured vs limit) and P2/P3 (register) are computed only from the `measured`, `limit`, `register` and `trace` the evaluator attaches. Where they are missing, the checks show **unknown**, never pass. We don't observe network traffic ourselves; the route rule is only as complete as the trace.
17. **Response pending (P5):** before the cutoff, the owner-response check is "unknown: pending until the cutoff", so `Policy` shows 7/8 or less until the owner replies or the cutoff passes.

---

## 12. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `analyze` exits 2: "set environment variables: MODAAS_…" | Export `MODAAS_GATEWAY_URL` and `MODAAS_MODEL_ALIAS` in the IDE terminal. |
| "gateway URL must be https or cluster-internal http" | Use the in-cluster service URL (`…svc.cluster.local`) or an https URL; never a public http URL. |
| `FAILED` with HTTP 401/403 from the gateway | Missing or wrong `MODAAS_API_KEY`, or the alias isn't approved for your team. Check the alias's approval state. |
| `BLOCKED` | The guardrail filtered the call. Keep the run record as adversarial evidence; check the incident text for injected content. |
| `REFUSED` repeatedly | The model keeps echoing a wrong fact. Try a larger approved alias (`nemotron-super-120b`). Show it as a failure, don't hide it. |
| `UNVERIFIED` | The write may have landed; run `analyze` again (it SKIPs if the note exists). |
| `servicenow.status: unreachable` | ServiceNow secrets missing in the backend process, or certs on macOS (`SSL_CERT_FILE=$(python3 -m certifi)`). Run `selftest`. |
| Panel step 4 stuck on pending | The evaluator loop isn't calling `run_assurance_agent` after `notify`, or the worker crashed; check the delivery log for `ANALYSIS_*`. |
| Owner shows as an object in your UI | Use `case_view` (normalises display values); don't read raw Table API fields. |

---

## 13. Acceptance checklist
- [ ] `python3 -m pytest prooflab/tests -q` → 152 passed in your repo.
- [ ] The evaluator attaches `measured`, `limit`, `register` (owner = `SNOW_OWNER_USER`) and the agents' `trace` with gateway steps and `run_id` (§5.0); a named run's card shows the movement diagram and `Policy 8/8` (or honest unknowns).
- [ ] `analyze` on the test finding returns `WRITTEN` on INC0010232 through `modaas-agw` with an approved Nemotron alias; run record saved.
- [ ] The evaluator loop calls the agent after every `DELIVERED` finding, off the request path.
- [ ] `ifabric_assurance_agent` deployed on AgentCore with Sree's approval; backend switched to `agentcore`; visible in AICT.
- [ ] The dashboard shows step 4 exactly as in §8 (two groups, provenance, honest states, 5-minute stale rule).
- [ ] The dashboard shows the header pills and the five assurance sections as in §8.7 (unknown never green; the broken hop shown red).
- [ ] No secret or model reasoning reachable from the browser.
- [ ] Case snapshots and run records in the Evidence Pack and `MANIFEST.json`.
- [ ] One adversarial case recorded (injected ticket → REFUSED, or guardrail → BLOCKED).
- [ ] Gap-list entries 9–17 adjusted to what actually happened.

---

## 14. Who does what next

| Who | What |
|---|---|
| **Teammate** | Merge v3 (§3) · **attach finding context: measured, limit, register, trace (§5.0)** · first live `analyze` in the IDE (§5.2) · evaluator-loop call (§5.1) · AgentCore deploy + switch backend (§5.3) · dashboard endpoint, Assurance Agent section and the five sections (§7–§8.7) · evidence (§9) · rehearse §10 twice |
| **Arth** | Get Sree's CR approval at the right moment · confirm the parser against the first real note · update the §0 status table · capture AICT evidence for `ifabric_assurance_agent` · keep the ServiceNow side tidy (prototype inactive; no other changes) |
| **Both** | Agree the response cutoff and the named runs; record one adversarial case; dry-run the demo end to end |

---

## 15. AI Control Tower (Level 2): what to capture
- **Inventory:** our runtimes under the connection "iFabric Hackathon 2026" (AgentCore runtimes and gateways only; Bedrock agents and SageMaker models are AccessDenied for the connector role). Export or screenshot with timestamps → `servicenow/aict/`.
- **Connector proof:** the CloudTrail `AssumeRole` record of `SgcAictReadOnlyAccessRole` (about every minute) → `servicenow/aict/cloudtrail-assumerole.json`.
- **Freshness:** imports run every 15 min (+ ~4 min). Click **Execute Now** ~20 min before the slot.
- **Honest gaps:** Monitor shows no AWS sessions (Managed agents only), and the usage counter is 0 (its query filters `InvokeAgent`). `/aws/bedrock/aict-invocations` is AWS-written CloudTrail data, an independent WHO source.

**Correction to handoff 1 §11.1 / gap A1:** AICT discovers **AgentCore runtimes and gateways only**. Bedrock agents and SageMaker models are AccessDenied for the connector role (verified by the teammate). The usage counter is 0 (its query filters InvokeAgent), and Monitor shows Managed agents only.

---

## 16. Owner engagement and closure (what judges look for)
- Every BREACHED / ESCALATED / monitoring-gap finding → **exactly one** incident assigned to Sree (re-runs reuse it).
- Show **both outcomes:** at least one RESPONDED and one NO_RESPONSE_OBSERVED after the stated cutoff (the same cutoff everywhere, e.g. judging start).
- **Closure only by a linked passing re-test:** the evaluator attaches `retest` to the breached finding (§5.0), then the integration user resolves the incident with a note `closed by re-test <assessment_id> (SATISFIED, same threshold version)`. Assurance check P6 passes only with that `retest` (the console demo's INC0090216 shows it: Resolved, P6 "closed by re-test …run_FM-C.r1.json"). An owner's "done" is a *response*, never a closure.
- **EP4 (the S3 escalation):** the change is HELD until the owner answers APPROVE or REJECT. `check()` records it; `held-actions.json` shows that nothing executed without approval.

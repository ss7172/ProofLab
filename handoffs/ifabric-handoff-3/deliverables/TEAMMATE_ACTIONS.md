# What the plan needs from the teammate (AWS agents, controls, adapters, dashboard, architecture)

From Arth (ServiceNow side). Ordered. Each step has a **done when** check. References: handoff 1 = `docs/SERVICENOW_INTEGRATION_HANDOFF.md`, handoff 2 = `../evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md` (the single source of truth for the Assurance Agent and its GUI; it replaced the old handoff 2 file and keeps its section numbers, so every "handoff 2 §X" below still points to the right section), Playbook = `docs/HACKATHON_WINNING_PLAYBOOK.md`.

## Who owns which of the six judging artefacts
| # | Artefact | Owner | Arth provides |
|---|---|---|---|
| 1 | Evidence file (Evidence Pack in S3) | **Teammate** (assembles, submits, reads back) | `evidence-pack/` skeleton, README, `tools/manifest.py`, the whole `servicenow/` part |
| 2 | Threshold document (`register.yaml`) | **Teammate** (values from baseline runs) | `thresholds/register.template.yaml`; runs Sree's approval (`thresholds/threshold-approval.md`) |
| 3 | Control test tool + demo | **Teammate** | the human-loop / Assurance Agent data via `case_view` and the dashboard panel |
| 4 | Two named runs per control (`run-ids.txt`) | **Teammate** | template in `evidence-pack/run-ids.txt` |
| 5 | One-page architecture | **Teammate** | `architecture/servicenow-section.md` to paste |
| 6 | Gap list | **Teammate** owns the final merged file; Arth reviews | Section A (ServiceNow/platform, 18 entries) already written in `evidence-pack/gap-list.md` |

---

## Phase A: today (setup and first proof)
1. **Merge** `code/prooflab/` from the handoff-3 package (the already-sent v3 plus the P6 re-test fix and two panel fixes): replace `prooflab/servicenow/` and `prooflab/tests/`, plus the docs (handoff 1 and the playbook were corrected for Nemotron; `evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md`, which replaces handoff 2, covers the five assurance sections).
   - **Done when:** `python3 -m pytest prooflab/tests -q` → **152 passed**, and `python3 -m prooflab.servicenow selftest` prints OK (ServiceNow secrets from Arth, loaded one line at a time; handoff 1 §5.3).
2. **Send Arth** the `modaas-agw` URL your agents use, the currently **approved** Nemotron alias, and whether an API key is needed. Never put a key in chat or files; Arth only needs to know *whether* one is needed.
3. **First live Assurance Agent run** in the workshop IDE: use the exact commands in handoff 2 §5.2 (`evidence-console-plan/08-…`).
   - They set a **TEST** delivery log, run `notify --dry-run` (reuses INC0010232 read-only), then `analyze`, keeping the test out of the production log.
   - Arth already verified the ServiceNow write path live with a stand-in (9/9), so this run proves the Nemotron call.
   - **Done when:** `"state": "WRITTEN"` on INC0010232 with `Model: NVIDIA Nemotron via modaas-agw:…`. Send Arth the JSON output + run record.
   - If `UNVERIFIED`: **don't re-run**; run `export` on the same finding and send Arth the export file.
4. **Start C9 baseline collection now:** it needs closed UTC hours, so time is the constraint (Playbook §3.3).

## Phase B: hard gate, before ANY assessed run
5. **Exploratory baseline runs** (label them *exploratory*; excluded from results). Fill `thresholds/register.template.yaml` → `register.yaml`: every placeholder plus the four justifications per control; no threshold numbers in code.
6. **Hand `register.yaml` to Arth** for review and Sree's approval (`thresholds/threshold-approval.md`, steps 2–7).
   - **Done when:** Arth confirms `RESPONDED` (Sree's dated APPROVED note), and you've copied the approved file **unchanged** to `evidence/register/register.yaml` with `evidence/register/approval.md`.
   - **No assessed run before this.**

## Phase C: controls, one at a time, each fully end to end (Playbook §4.2)

**Hard requirement, before the first named run: attach the finding context (handoff 2 §5.0).**

The Assurance Agent's analysis has five sections:
- **agent movement**;
- **decision trace**;
- **evidence**;
- **policy alignment**;
- **outcome validation**.

Movement, the route rule and most policy checks are computed **only** from four optional keys your evaluator puts on each finding dict (`finding_from_dict` / `notify`). Without them, the judges see "Agent path not provided" and grey "unknown" checks. That is honest, but it is the weakest version of the demo.

```json
"measured": {"value": 10800, "unit": "tokens"},
"limit":    {"value": 10000, "operator": "<=", "unit": "tokens"},
"register": {"version_date": "2026-10-01", "owner": "annapurna@invences.com", "approval": "<approval INC number>"},
"trace": [
  {"at": "2026-10-05T09:58:01Z", "actor": "customer-care-agent", "zone": "customer", "action": "receive fault report", "decision": "accepted", "ref": "span:cc-01", "run_id": "FM-B"},
  {"at": "2026-10-05T09:58:03Z", "actor": "modaas-agw", "zone": "gateway", "action": "model_call", "decision": "allowed", "ref": "gateway:action-123", "run_id": "FM-B"},
  {"at": "2026-10-05T09:58:12Z", "actor": "network-fault-agent", "zone": "network", "action": "run diagnostics", "decision": "fault found", "ref": "span:nw-03", "run_id": "FM-B"},
  {"at": "2026-10-05T09:58:20Z", "actor": "modaas-agw", "zone": "gateway", "action": "return path", "decision": "allowed", "ref": "gateway:action-125", "run_id": "FM-B"},
  {"at": "2026-10-05T09:58:22Z", "actor": "customer-care-agent", "zone": "customer", "action": "reply to customer", "decision": "sent", "ref": "span:cc-02", "run_id": "FM-B"}
]
```

- `zone` must be one of `customer`, `it`, `network`, `gateway`. **Every gateway hop is its own step with `zone: "gateway"`.** A `network` step followed directly by a `customer` step fails the route rule (M1/P8).
- Set `run_id` = the finding's `scope_id` on every step. Timestamps are UTC `…Z`. At most 200 steps; text ≤ 200 characters, no newlines.
- `register.owner` = the ServiceNow user name of the named owner (same as `SNOW_OWNER_USER`); `version_date` = the date the frozen threshold version was approved. `limit.unit` must equal `measured.unit`.
- Source the trace from what you already log: AgentCore spans or your orchestrator's step log, with each gateway call's `x-modaas-action-id` as `ref`.
- When a passing re-test closes a finding, attach `retest` = {assessment, verdict: SATISFIED, threshold_version, at} before resolving the incident, or Assurance check P6 goes red (`08` §5.0).
- **Done when:** the C16 BREACH named run's dashboard card shows the agent-path diagram with its gateway crossings, M1 ✓, and `Policy 7/8` before the owner replies (8/8 after). A run that skips the gateway shows the red "no gateway before this hop".

7. **C16 first**, then the **S2/S3** fixes (S3 escalate → ESC finding), then **C7**, then **C9**. For each control:
   - records bound to control + threshold version + run at the enforcement point;
   - a pure evaluator that reads the frozen register;
   - one **PASS** and one **BREACH** named run in `run-ids.txt`, written **before** judging;
   - on every BREACH/ESCALATED finding:
     - `notify()` → if `DELIVERED`, `run_assurance_agent()` (handoff 2 §5.1), off the request path;
     - `check()` on a short loop;
   - C9: one finding per crossing window; a missing window is a monitoring-gap finding.
   - **Done when** the query tool answers "Show me control 16 for run FM-B" on one screen in under 2 minutes, including the human-loop line and the Assurance Agent result.
8. **Adversarial log** `evidence/adversarial/`: Hostile and Rogue cases (Playbook §3.9). Include one ticket with injected instructions → Assurance Agent `REFUSED`, if possible a guardrail `BLOCKED`.

## Phase D: Assurance Agent on AgentCore (AICT-visible)
9. Deploy **`ifabric_assurance_agent`** through `new-agent.sh` (handoff 2 §5.3): a pure analyzer with no ServiceNow credentials; **Sree approves the CR** (real attestation); check READY. Switch the orchestrator backend to `CallableAnalyzer` (`agentcore:ifabric_assurance_agent`).
   - **Done when:** one `WRITTEN` run with backend `agentcore:…`, and the runtime appears in AICT Inventory (tell Arth; Execute Now refreshes).

## Phase E: dashboard
10. One **read-only** backend endpoint returning `case_view()` JSON (handoff 2 §7.1), cached 10 s. Then the drop-in panel (§7.2) or your own components following **§8** and **§8.7** (the five assurance sections).
    - **It must read the same `delivery-log.jsonl` the evaluator loop writes**, or genuine notes show red.
    - Pass the case JSON through **unchanged**: the five sections are extra top-level keys, and a fixed DTO that drops them hides the whole assurance block.
    - Dark dashboard? Put `data-ifab-theme="dark"` on the panel container.
    - **Done when:**
      - a new breach shows steps 1–3 within 10 s and step 4 within about a minute;
      - the card shows the header pills (Policy x/y, Outcome, agents · gateway crossings) and the "Assurance analysis" block;
      - no secret is reachable from the browser.

## Phase F: architecture (Artefact 5)
11. One page (or whiteboard photo) covering: agents → EP1 gateway → records → evaluators (register out of path) → evidence. Paste or redraw `architecture/servicenow-section.md` for the ServiceNow half (EP2, Assurance Agent, AICT, dashboard).
    - **Done when** it answers: what's in the execution path, how an EP invokes the controls, which adapter changed for EP2.

## Phase G: Evidence Pack (Artefact 1), the evening before judging
**Follow `PRESENTATION_DAY_INTEGRATION.md`**, which has the exact final `evidence/` tree, who sends what, and the order of steps.
12. Build `evidence/` from `evidence-pack/` (README placeholders filled, gap list Section B filled, decisions log extended).
    - Run final `check` and `export` for every finding, and `case --out` for every named run (`evidence-pack/servicenow/README.md`).
    - **Do not** copy `wiring-tests/delivery-log-wiring-tests-ONLY.jsonl` into the production log.
13. `python3 tools/manifest.py build evidence` → `submit.sh` to the team bucket → **read back** (ls, head-object, download + `manifest.py verify`). Record keys/ETags in README §10.
    - **Done when:** `verify` prints OK on the downloaded copy.

## Phase H: judging
14. **Rehearse twice** with someone outside the build asking the judges' exact questions (`pitch/running-order-15min.md`). Bring all six artefacts.

---

## Never
- Put ServiceNow or gateway secrets, tokens, IdeUrl/CockpitUrl or presigned URLs in code, files, screenshots or chat.
- Call ServiceNow from an agent's request path or from the browser.
- Store a threshold in control code, or edit a frozen register (bump the version instead).
- Close a finding without a linked passing re-test.
- Re-activate the ServiceNow-LLM agent, change ServiceNow configuration or users, or touch other teams' records (ask Arth).
- Mix test data (wiring tests, exploratory runs) into assessed results.

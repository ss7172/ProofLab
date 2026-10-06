# 03 · Data contracts: the integration surface

The console and the AWS-side pipeline meet **only** through these JSON contracts. If both sides honour them, the console can be built **today against the synthetic fixtures**, in parallel with the AWS work, and pointed at the real pack later without a code change.

| Artefact | Where | Use |
|---|---|---|
| Machine-readable schemas | `schemas/contracts.schema.json` (one file, one `$defs` entry per contract) | Dev-time validation (`jsonschema` is a dev-only dependency, like pytest); runtime code stays standard-library |
| Synthetic fixtures | `examples/*.json`, all `provenance: SYNTHETIC`, all validated (111 instances, 0 errors) | Build and test the console and query engine before real evidence exists |
| Fixture generator | `examples/generate_examples.py` (stdlib) | Shows how every field is derived; regenerate after any contract change |
| Demo data | `demo/demo-data.js` | The demo renders exactly these contracts |

**Contracts reused unchanged** (do not fork them):
- `Finding` (`prooflab/servicenow/finding.py`, handoff 1 §6);
- `ifabric.servicenow.case/v1` (`case_view.py`);
- `ifabric.assurance-agent.run/v1` (`assurance_agent.py`);
- `ifabric.evidence-manifest/v1` (`tools/manifest.py`).

---

## 1. Contract map

| Contract (`schema`) | `$defs` | Produced by | Consumed by | Lives at (pack-relative) | Example |
|---|---|---|---|---|---|
| `ifabric.evidence/v1`: bound evidence record | `evidenceRecord` | binder (`prooflab/bind`) | evaluators, query engine, Ledger view | `records/<control>/<run-or-window>.jsonl` | `evidence-record.C16.FM-B.c-0015.json` |
| `ifabric.assessment/v1`: control test result | `assessment` | evaluators (`prooflab/evaluators/*.test`) | publisher, query engine | `assessments/<control>/<scope>.r<N>.json` | `assessment.C16.run.FM-B.r1.json`, `…FM-C.r1.json` (re-test) |
| `ifabric.answer/v1`: the 2-minute answer | `answer` | query engine (`prooflab controltest`) | Answer screen, CLI text, `answers/` snapshots | `answers/<control>_<scope>.json` (named runs, frozen) | `answer.C16.run.FM-B.json`, `answer.C7.run.FM-B.json`, `answer.C9.interval.json` |
| `ifabric.auditor/v1`: six auditor questions | `auditor` | query engine (`prooflab auditor`) | Six Questions view | `auditor/<incident-or-run>.json` | `auditor.INC0090216.json` |
| `ifabric.run/v1`: run manifest + journey + decisions + outcome + lane | `run` (+ `hop`, `decision`, `policyCheck`, `outcomeValidation`, `laneEvent`) | orchestrator (manifest), agents (decisions), policy checker, query engine (lane, outcome) | Agent Trail view, Run lane | `runs/<cid>/run.json` | `run.FM-B.json`, `run.FM-C.json` |
| `ifabric.adversarial-case/v1` | `adversarialCase` | whoever ran the attack (team or Nemotron-generated) | Adversarial view | `adversarial/<case>/case.json` | `adversarial-case.R5.json` |
| `ifabric.gap/v1` | `gap` | team (from `gap-list.md`) | Gaps view | `gaps/<id>.json` or inline in `pack-index.json` | `gap.B6.json` |
| `ifabric.pack-index/v1`: table of contents and allow-list | `packIndex` | `prooflab pack index` | the console (first and only entry point) | `pack-index.json` | `pack-index.json` |
| `ifabric.console-action/v1` (P2) | `consoleAction` | console (REQUESTED), actuator (later states) | Control Room, Evidence Pack | `console/actions.jsonl` | `console-action.example.json` |

---

## 2. Identifiers and references

| Id | Format | Example | Rule |
|---|---|---|---|
| CID (run id) | `fault-<epoch>-<6hex>` from the orchestrator | `fault-1791244802-b7d20f` | Propagated in **baggage** (`modaas-correlation-id`), so the gateway's `modaas.run_id` equals it |
| Run alias | `FM-A`, `FM-B`, … | `FM-B` | Written in `run-ids.txt` **before judging**; maps 1:1 to a CID |
| Trace id | W3C, 32 hex | `…` | One per run; agents must forward it (the reference agents mint their own, VF) |
| Call id | `c-0001` … per run, in gateway order | `c-0015` | Stable ordering key for C16 |
| Gateway action id | `x-modaas-action-id` | `agw-…` | Join key gateway ↔ PDP ↔ `/modaas/evidence` |
| `finding_id` | `ifabric:{control_ref}:{version}:{scope_kind}:{scope_id}:{kind}` (existing) | `ifabric:C16:G-FM-v1:run:FM-B:finding` | = ServiceNow `correlation_id` = the Assurance Agent note's "Finding ID" |
| `assessment_id` | `{ref}:{version}:{scope_kind}:{scope_id}:r{n}` | `C16:G-FM-v1:run:FM-B:r1` | Corrections are r2, r3 (`supersedes`), never edits |
| `evidence_id` | `ev:{ref}:{version}:{run}:{call-or-event}` | `ev:C16:G-FM-v1:FM-B:c-0015` | Deterministic, so re-binding is idempotent |
| `decision_id` | `dec:{run}:{step}` | `dec:FM-C:3` | One per agent step |
| `answer_id` | sha256 (below) | 64 hex | Deterministic, so the same question on the same pack gives the same id |

**`answer_id` canonicalization.**
1. Remove `answer_id`, `answered_at` and `elapsed_ms`.
2. Remove `source.mode`.
3. Take `sha256(json.dumps(rest, sort_keys=True, ensure_ascii=False))` with Python's default separators. `generate_examples.py: answer_id_of()` is the reference implementation.

**Reference prefixes.** Every `refs[]` entry is `prefix:value`, so the console can resolve it to a file or line. Handoff 1 §8.2 defined `raw:` `gateway:` `ledger:` `cloudwatch:` `cr:` `assessment:` `register:` `servicenow:` `aict:`. This plan adds:

| Prefix | Resolves to |
|---|---|
| `record:` | An evidence record id or decision id (`records/**`, `runs/**`) |
| `capture:` | A capture sidecar (`raw/**/*.capture.json`: exact command, scope, time, sha256, redactions) |
| `finding:` | `findings/<finding_id>.json` |
| `run:` | `runs/<cid>/run.json` (fragments `#lane`, `#journey`) |
| `answer:` / `auditor:` | Frozen answers / auditor files |
| `pdp:` `xray:` `span:` | Captured PDP lines, X-Ray trace, span ids (corroboration) |
| `expected:` `baseline:` | C7 expected-event specs, C9 frozen baselines |
| `adversarial:` `gap:` | Case or gap ids |
| `manifest:` `s3:` | `MANIFEST.json`, the S3 object key |
| `console:` | Console action or session ledger entries |

A ref the console cannot resolve is rendered **red, "unresolved"**, never hidden (J-17, J-33).

---

## 3. Vocabulary (enums the UI keys off)

| Field | Values | Display rule |
|---|---|---|
| `provenance` | `ASSESSED` · `EXPLORATORY` · `WIRING_TEST` · `SYNTHETIC` | Only ASSESSED counts toward verdicts. EXPLORATORY and WIRING_TEST appear greyed with a chip. SYNTHETIC never enters the real pack, and the demo shows a watermark |
| `verdict` (assessment, record, answer) | `SATISFIED` · `BREACHED` · `INDETERMINATE` · `NOT_ASSESSED` | Labels: SATISFIED / **NOT SATISFIED** / INDETERMINATE / NOT ASSESSED. Green is earned; red means a breach; amber hatched means unknown; grey means not assessed |
| Claim verdict | `SATISFIED` · `NOT_SATISFIED` · `NOT_ESTABLISHED` | Any established in-scope breach → NOT_SATISFIED. No breach but a branch incomplete or unknown → NOT_ESTABLISHED. All branches satisfied with coverage → SATISFIED. **Never averaged** |
| `evidence_sufficiency` | `COMPLETE` · `PARTIAL` · `UNKNOWN` | Shown beside every verdict |
| `decision` (inline evaluator) | `ALLOW` · `ALERT` · `DENY` | ALERT = observe mode ("would deny"); DENY = refused, so a stop record must exist |
| Six-question status | `ANSWERED` · `PARTIAL` · `GAP` | PARTIAL/GAP link to the gap id |
| Policy check | `ALIGNED` · `VIOLATION` · `NOT_APPLICABLE` · `UNKNOWN` | Computed by host code, never by the model |
| Outcome validation | `VALIDATED` · `PARTIAL` · `FAILED` · `UNKNOWN` | Against the scenario spec / ground truth, not the agent's own claim |
| Adversarial outcome | `DEFENDED` · `DETECTED` · `BROKE_FIXED` · `BROKE_OPEN` · `NOT_RUN` | BROKE_* must carry `what_broke` and `what_changed` |
| EP status | `BUILT` · `BUILT_WAITING` · `ALERT_ONLY` · `EVIDENCED` · `PLANNED` · `NOT_BUILT` · `NOT_RUN` | Rendered as-is; the console never upgrades a status |
| Human loop (existing) | delivery `DELIVERED/FAILED/UNVERIFIED/OUTCOME_UNKNOWN/…`; response `RESPONDED/AWAITING_RESPONSE/NO_RESPONSE_OBSERVED/RESPONSE_UNKNOWN/NOT_DELIVERED`; agent `WRITTEN/SKIPPED/REFUSED/BLOCKED/FAILED/UNVERIFIED/NOT_RUN` | Exactly as `case_view` and `08-…` define (see `08-…` §6) |
| Closure | `OPEN` · `CLOSED_BY_RETEST` · `ACCEPTED_WITH_EXPIRY` · `NOT_APPLICABLE` | CLOSED only with `retest_ref` → a SATISFIED assessment (J-18) |

**Time.** Every timestamp is UTC `YYYY-MM-DDTHH:MM:SS[.mmm]Z`. Every record's `source.clock` names the clock it came from: `gateway`, `ledger`, `cloudwatch`, `orchestrator`, `agent`, `servicenow`, `pdp` or `capture`. Gaps are computed **only within one clock**. ServiceNow display times (`servicenow.updated_at`) are display values in the API user's time zone and are labelled so.

---

## 4. The contracts that matter most

### 4.1 `ifabric.evidence/v1`: a record a stranger can check (MC-11, MC-33)
These field names are **exactly the slide's**: `run.id`, `call.id`, `control.id`, `threshold.version`, `threshold.value`, `measured.value`, `verdict`, `actor.id`, `emitted.at`, `seal`.

- **C16 per-call records:**
  - `measured.value` = the run's **cumulative** tokens after this call (the slide's record shows the run total);
  - `measured.call` = this call's tokens;
  - `decision` = the inline admission decision taken before the call, if an EP took one;
  - `verdict` = the control state as of this record.
- `source` names the surface, the raw line (`raw_ref`), its sha256, the capture sidecar, the capture time and the clock. `corroborated_by` lists the same call on other surfaces (PDP line, durable gateway log, X-Ray), and that list drives the **T** tickmark.
- `seal` is always `"out-of-scope"` (the brief says sealing is out of scope). The console prints it rather than pretending.

### 4.2 `ifabric.assessment/v1`: the dated control test (extends handoff 1 §8.2)
- It carries the threshold **as loaded from the register** (`threshold.source_ref` and `register_sha256`), and is never typed into code.
- `population` holds the completeness statement: expected (with its independent source), observed, matched, missing, unmatched, duplicates removed, blocked, unmeasurable.
- `measured.series[]` holds the per-gap (C7) or per-window (C9) observations with `status ∈ {OK, VIOLATES, UNKNOWN, UNMEASURABLE, MISSING}`, so missing data is a first-class value.
- `retest_of` / `closes_finding` hold the re-test link. That link is **the only way** a finding closes.

### 4.3 `ifabric.answer/v1`: what the judge sees (and the CLI prints)
One object answers one question. Its parts map to the brief:

| Part | Brief source |
|---|---|
| `rule`: register version, threshold version, `version_date`, `frozen_at`, owner, approval (ref, time, approver), **`date_before_scope`** | MC-21 "its date is what makes it a test"; J-15 |
| `population` | J-16, PB §3.7 "expected vs observed population" |
| `measurement` + `comparison`: both numbers of every rule, the single-observation limit and the exception tolerance | MC-34, J-49 |
| `exceptions[]` (every exception stays visible) | MC-34 "the 8 ms exception stays visible" |
| `verdict`: value, label, reason, `evidence_sufficiency`, `built_properly`, `actually_worked` | MC-40 honesty |
| `enforcement`: `tester` (control test) separate from `evaluator` + `inline_decisions[]` (with `reserved`/`committed`) + `stop_records` | MC-24, MC-25, J-12, J-38 |
| **`audit_question`**: the ten MC-9 rows: `what_was_done`, `by_which_agent`, `where`, `when`, `under_whose_authority`, `rule_checked`, `limit_in_force`, `decision` (`outcome`: ALLOWED, STOPPED or ESCALATED), `who_was_told`, `unchanged_since` | MC-9, J-35 |
| `human_loops[]`: **one entry per finding** (a C9 interval can raise a crossing and a monitoring gap): incident, owner, delivery, response (or recorded silence), Assurance Agent, **closure** | MC-31 alert to a named owner; J-18, J-50 |
| `aict`: discovery status, connection, assets, last import, Monitor | L2, J-02 |
| `records[]` with **tickmarks** R/A/T/V and MANIFEST status | J-09, J-17 |
| `gaps[]` for this scope | J-10 |
| `source`: mode PACK/LIVE, MANIFEST sha + status, `records_scanned`; `elapsed_ms` | J-07 (time to answer shown) |

**The CLI prints the same object as one screen** (handoff 1 §8.7, extended):
```
C16 ACN-COST-001 · rule G-FM-v1 (dated 2026-10-05; frozen 22:10Z; approved by Sree 22:31Z, before the run ✓)
  ≤ 60,000 tokens per run · 0 over-cap runs permitted          [illustrative values]
Scope   run FM-B (fault-1791244802-b7d20f) 2026-10-06T00:00:02Z → 00:05:51Z · ASSESSED
Pop.    expected 15 calls · observed 15 · matched 15 · missing 0 · blocked 1 · duplicates removed 15
Measured 63,420 (in 61,264 + out 2,156)  vs  ≤ 60,000   →  NOT SATISFIED · over by 3,420
Inline  EP2 (observe): ALERT before c-0015 — 57,816 committed + 5,790 reserved > 60,000
Records gateway c-0001…c-0015 [R A T] · raw/gateway/…/gateway-stdout.log#L1-15 · MANIFEST ✓
Who     ifabric_customer_agent → ifabric_it_agent → ifabric_network_agent (CR gen 3, approved by Sree)
Told    INC0090216 → Sree Annapurna Rallabandi · DELIVERED 00:06:20Z · NO_RESPONSE_OBSERVED by 14:00Z
        Assurance Agent WRITTEN (Nemotron, action agw-7f3c91d2) · CLOSED BY RE-TEST FM-C (SATISFIED)
AICT    4 ifabric runtimes discovered (connection "iFabric Hackathon 2026", import 13:45Z) · Monitor: none (gap A3)
Gaps    B1 shared gateway identity (WHO partial)
answer_id 3c1f…  ·  answered in 412 ms from 214 records (PACK, MANIFEST verified)
```

### 4.4 `ifabric.run/v1` + `ifabric.decision/v1`: the agent's five facets
This is where the **agent movement, decision trace, evidence, policy alignment and outcome validation** live, rendered by the console's **Agent Trail** view (`06-UI-UX-SPEC.md` §5.4).

| Facet | Field | Built from | Rule |
|---|---|---|---|
| **Agent movement** | `journey.hops[]`: from, to, via (`gateway-A`, `gateway-B`, `orchestrator-handoff`, `return-path`, `servicenow`), time, payload (one line, never prompt text), EP3 admission | Orchestrator handoff records + ledger | Every hop joins to the CID |
| **Decision trace** | `decisions[]`: intent → inputs → `evidence_consulted[]` (tool, status, declared?) → model calls (action ids) → `disposition` → `rationale` (≤ 400 chars, cites evidence) → `named_evidence_needed` / `reversible_action` / `proposed_action` → `handoff_to` | The agent's **structured final answer** (`05-AWS-SIDE-BUILD.md` §4) + ledger + gateway | **Observable steps only. Model reasoning (think-tags) is never stored or shown** |
| **Evidence** | `cited_evidence[]`, `evidence_consulted[].ref` | Tool results captured as records | Every cited ref must resolve; EMPTY results are shown as EMPTY |
| **Policy alignment** | `decisions[].policy_checks[]`: policy id + version (`AP-v1`), ALIGNED / VIOLATION / NOT_APPLICABLE, basis, refs | **Host-side deterministic checker** (`prooflab/policy/check.py`) against `policies/agent-policies.yaml`, frozen and approved with the register | The model never grades itself |
| **Outcome validation** | `outcome`: expected disposition from `expected/scenarios.yaml` (independent spec), actual, checks, ground truth, **claimed vs executed**, `score-run.py` as a *diagnostic* | Query engine | "Governed ≠ correct": a claimed action that never executed is a FAIL |

**Not to be confused with** the Assurance Agent's five sections (`08-…` §8.7: M1–M3, P1–P8, V1–V6). Those grade a *finding and its human loop* and live in the ServiceNow case JSON. These grade an *agent run's decisions* and live in `run.json`. Both are rendered, labelled (`08-…` §5.7).

The `lane` (`laneEvent[]`) is the time-ordered union of handoffs, admissions, model calls, guardrail blocks, stop records, ledger dispositions, findings, incidents and owner responses. It is the RECONSTRUCT answer.

### 4.5 `ifabric.auditor/v1`: six questions, honestly graded
Each question carries `status` (ANSWERED / PARTIAL / GAP), a one-line `answer`, `facts[]` with refs and a `flag`, and `gaps[]`. **Expected honest results on this platform** (VF):
- **WHO** = PARTIAL: one shared gateway identity (gap B1). Per-agent identity comes from runtime logs, orchestrator records and CloudTrail `InvokeAgentRuntime`.
- **AUTHORIZED**: join each PDP ALLOW to its gateway line, because blocks and pauses are logged ALLOW (gap B2).
- **APPROVED**: list approvals for **every asset actually called**, and flag any approval older than the running generation (gap B4).
- **INTEGRITY**: MANIFEST + corroboration + S3 readback. There is no ledger self-check (gap B5). For an incident, also cite the Assurance Agent's note: WRITTEN with its SHA-256 in the delivery log (trusted), or REFUSED with its reason; RECONSTRUCT puts the agent's run on the incident timeline.

### 4.6 `ifabric.pack-index/v1`: the console's single entry point and allow-list
The console reads `pack-index.json` first and may open **only** paths it lists (or that `MANIFEST.json` lists). It carries:
- the claim with per-control completeness (a)–(g), plus `built_properly` / `actually_worked`;
- the register summary with approval, `first_assessed_run_at` and the exploratory count;
- the six artefacts with presence and sha256;
- `named_runs` with **`written_at`**;
- runs, findings with closure, answers, auditor files, adversarial cases, gaps, levels L1–L3 with evidence items, environments, **enforcement points with honest status**;
- `cases[]`: every ServiceNow case snapshot (`finding_id`, `incident`, `path`, `sha256`). `GET /api/v1/cases` serves only these, so the Human Loop stays inside the allow-list;
- integrity: MANIFEST status, corroboration counts, and the S3 submission readback.

---

## 5. Rules for both sides

1. **Additive only.** New optional keys are fine; renames and removals need a `/v2` and a console change.
2. **Never mix provenance.** Producers set it; the console filters on it.
3. **Never compute a verdict in the UI.** The console renders `assessment`/`answer` verdicts. The one exception is the "Verify without us" panel, which recomputes C16 from raw records and shows **"matches / differs"** next to the recorded verdict. It never replaces it.
4. **Text is data.** Every string from evidence (ticket text, agent rationale, tool output) is rendered with `textContent`.
5. **Unknown is a value.** `null` plus a status (`UNKNOWN`, `UNMEASURABLE`, `MISSING`) is rendered as hatched amber with its reason, never as 0, blank or green.

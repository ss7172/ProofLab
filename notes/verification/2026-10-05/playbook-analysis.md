# ServiceNow integration package + Hackathon Winning Playbook: analysis for planning

Read-only analysis, 2026-10-05. Source folder: `~/Downloads/servicenow-integration-package/`. No AWS calls, no ServiceNow calls, no git. Tests were not executed (pytest would write `__pycache__`/`.pytest_cache` into the package).

Reference keys used below:
- **PB Lnnn**: `HACKATHON_WINNING_PLAYBOOK.md` line. **HO Lnnn**: `SERVICENOW_INTEGRATION_HANDOFF.md` line.
- Memory files (in `~/.claude/projects/-/memory/`): **PP** = prooflab-project.md, **CR** = challenge-requirements.md, **SNm** = servicenow-context.md, **PVF** = platform-verified-facts.md, **RAF** = reference-agents-facts.md, **WP** = workshop-progress.md, **WA** = hackathon-working-agreement.md.
- Repo files (in `TrustworthyAI-iFabric/`): **GL #n** = gap-list.md entry n, **SNr** = notes/servicenow/servicenow-context.md, **NOTES #n** = notes/platform-observations.md.
- **Slides** = `hackathon-context/work/hackathon-sources/slides-extracted.txt`; **T3/T4** = transcript-3/-4 there.

---

## 1. Package inventory

16 files, 154,828 bytes. The file times (Oct 5, 01:38 to 02:41 local CDT, about 06:38 to 07:41 UTC) predate `my-agent` (created 08:59 UTC), so the package's AICT asset list cannot include it. There are no dotfiles, caches or binaries.

| Path | Bytes | What it is |
|---|---:|---|
| `HACKATHON_WINNING_PLAYBOOK.md` | 54,421 | Team strategy doc. §1 restates the brief (controls, scoring axes, six steps, judgement-day artefacts, evidence and architecture rules, AWS-side game, kickoff rules). §2 is the AgentCore/MoDaaS field guide, §3 a [MUST]/[BONUS]/[BEST] checklist, §4 a self-scorecard. Read in full. |
| `SERVICENOW_INTEGRATION_HANDOFF.md` | 36,617 | Integration spec from "Arth (with Claude Code)" to "the teammate building the AWS side". It covers ServiceNow state it claims is verified live (instance, AICT connection, users, OAuth app, test incident INC0010231), the Finding JSON contract, per-control wiring (C16/C9/C7/ESC), the evidence layout, the 2-minute query output, gap entries and an acceptance checklist. Read in full. |
| `prooflab/__init__.py` | 0 | Package marker. |
| `prooflab/servicenow/__init__.py` | 0 | Package marker. |
| `prooflab/servicenow/__main__.py` | 71 | `python -m prooflab.servicenow` entry point, calling `cli.main()`. |
| `prooflab/servicenow/cli.py` | 4,517 | CLI with `selftest`, `notify [--dry-run]`, `check --cutoff` and `export`. Reads `SNOW_INSTANCE/SNOW_CLIENT_ID/SNOW_CLIENT_SECRET` plus optional owner, integration-user and log-path variables. Exit codes 0/1/2. |
| `prooflab/servicenow/client.py` | 8,078 | Stdlib-only ServiceNow REST client: OAuth client-credentials token (cached), Table API (incident, sys_user, sys_journal_field). HTTPS only (http allowed for localhost), redirects refused, `^`/CR/LF rejected in query values. |
| `prooflab/servicenow/delivery_log.py` | 1,777 | Append-only, fsync'd JSONL evidence log. Tolerates a torn last line. |
| `prooflab/servicenow/finding.py` | 5,729 | `Finding` dataclass, validation, deterministic `finding_id` (`ifabric:{ref}:{version}:{scope_kind}:{scope_id}:{kind}`, hashed above 100 chars), and the mapping from a finding to incident fields. |
| `prooflab/servicenow/notifier.py` | 11,498 | `notify()` (owner lookup, existing-incident reuse, create, readback, then DELIVERED/FAILED/UNVERIFIED/OUTCOME_UNKNOWN/DRY_RUN), `check_response()` (RESPONDED/AWAITING/NO_RESPONSE_OBSERVED/RESPONSE_UNKNOWN/NOT_DELIVERED) and `export_incident()`. |
| `prooflab/servicenow/README.md` | 3,724 | Short usage guide: the finding contract, commands and delivery states. |
| `prooflab/servicenow/examples/test_finding.json` | 357 | TEST wiring finding (C16, version `TEST`, kind `wiring-test`). Per HO L55/L179 it maps to the existing INC0010231. |
| `prooflab/tests/__init__.py` | 0 | Package marker. |
| `prooflab/tests/fake_servicenow.py` | 9,539 | In-process fake ServiceNow on 127.0.0.1 (OAuth, incident, sys_user, journal). It models 5xx after write, garbled bodies, other teams' incidents and a journal **403**. Holds test-fixture credentials (see §1.1). |
| `prooflab/tests/test_servicenow_adapter.py` | 15,658 | 39 test functions, one parametrized ×3 (`:261`), so 41 cases. |
| `prooflab/tests/test_servicenow_cli.py` | 2,842 | 5 CLI tests. The static count is 41 + 5 = **46**, matching HO L114. Not executed. |

### 1.1 Credentials scan (locations only, no values)
- **No real credentials anywhere in the package.** HO L44 states "No secrets are listed here", and the scan agrees. The real OAuth Client ID and Secret are said to be held by Arth/Sree (HO L166).
- `prooflab/tests/fake_servicenow.py:18–19`: `CLIENT_ID` / `CLIENT_SECRET` constants. These are dummy test-fixture values for the local fake: an 18-character placeholder that contains the words "test" and "secret". The fake also hard-codes a dummy bearer token.
- `prooflab/tests/test_servicenow_adapter.py` and `test_servicenow_cli.py`: one-letter dummy values and `"wrong-secret"` in env/constructor calls.
- Not secrets, but identifying details in the package: the instance host, the AWS account id and bucket name, the integration username, and a team member's work email used as the default owner (`cli.py:28`, PB L347, HO L51).

---

## 2. Playbook summary (faithful, with section refs)

**Purpose and audience (PB L1–12).** This is a self-contained brief and checklist for team iFabric and its coding agents, covering the AWS agents, controls C7/C9/C16, evidence and the pitch. The companion `SERVICENOW_INTEGRATION_HANDOFF.md` is cited as "SN-handoff §N".

**Goal it targets (§1.0, §1.1).** Make agents whose every action can be **proven to a sceptical auditor** (PB L22), under the headline "the most auditable solution wins" (PB L118). The claim is **C-FM-01**: the three collaborating agents meet the declared event-recording (C7 AIA-LOG-001), drift/performance (C9 AIA-ARC-006) and token-spend (C16 ACN-COST-001) requirements (PB L33–41).

**Brief restated (§1.0–§1.8).**
- **Scenario (PB L24–31).** Customer → Gateway A → IT → Gateway B → network, every model call through one shared gateway, with one trace id and run id per step.
- **Worked examples (PB L48–77).** C16: cap 10,000, FM-A 9,600 SATISFIED, FM-B 10,800 NOT satisfied, "copy the shape, not the values" (PB L48). C7: ms gaps. C9: windows, plus the note that our C9 uses AgentCore latency/errors where higher is worse (PB L77).
- **Scoring (§1.1).** Sequential levels: L1 Foundation (MoDaaS guardrails + Nemotron), L2 Observability (ledger + ServiceNow AI Control Tower), L3 extended chain (AWS + ServiceNow sandbox).
  - Axis 1 counts complete controls ("finish one completely before starting the next").
  - Axis 2 is quality: the 2-minute live test, architecture, evidence, honesty.
  - Axis 3 is bonuses: extra controls, continuous compliance, adversarial testing, second enforcement point.
  - The "LOSE" list is at PB L111–117.
- **Six steps (§1.2)**, done when "somebody who is not on your team can ask 'was control 9 satisfied for run FM-B?' and get an answer in two minutes" (PB L128).
- **Six judgement-day artefacts (§1.3):** evidence file, threshold document, control test tool + demo, two named runs, one-page architecture, gap list. Rehearse twice; assemble the evening before; judges read the team S3 bucket; 15-minute slot (PB L139–142).
- **Evidence (§1.4).** "Not a logging exercise"; record fields; the stranger test; the six auditor questions (WHO / WHAT / AUTHORIZED / APPROVED / INTEGRITY / RECONSTRUCT) asked about an incident from the event window, from the Evidence Pack alone (PB L154–160).
- **Control design (§1.5).** Anatomy of a control; thresholds live in our spec with a date and four justifications; the GRC chain; four roles with "nobody checks their own work" (Sree = accountable management, "the teammate" = operations; PB L184–188); five control modes.
- **Architecture (§1.6).** One contract over four transports (`evaluate` / `emit` / `callback` / `pull`). "A dashboard is **not** an EP"; the EP list includes the human approval queue; "every EP does … ask, wait, act, record" (PB L235–249). Five habits: telemetry never judges, the evaluator never remembers, the register is never in the path, the ledger never interprets, sealing is out of scope.
- **AWS-side game (§1.7).**
  - Close the judgment gap: S2 should return gather-evidence plus the deciding evidence plus a reversible action, while S1 and S3 are "kept passing" (PB L255–256).
  - Three alert levels: Vanilla / Hostile / Rogue.
  - Stay under ~1 model req/s (100 req/min and 2.5M tok/h account-wide).
  - Back up as you go.
  - Module 8: three records, with the gateway line as figure of record.
  - Module 10: the twin as the pass/breach scenario switch.
- **Kickoff rules (§1.8).**
  - Nemotron only, agents only on AgentCore or in ServiceNow.
  - AICT + human loop "absolutely needed"; use all three environments.
  - AICT: own connector with the team name; rename agents; don't change risk frameworks; one ServiceNow agent is enough; clone, never edit, shared agents.
  - Out of scope: signatures, hash chains, Merkle proofs, slide decks.

**Field guide (§2).**
- **Platform rules table (PB L294–311):** deploy path, `ifabric_…` naming, model access via `modaas-agw` aliases, four injected values, approval as a human act, model swap, Strands adapter, MCP + team Cedar ConfigMap, guardrail 200/content_filter/0 tokens, kill switch, rate limits, evidence sources, correlation, think-tags, protected namespaces, backups.
- **Agent behaviour that scores (PB L313–324):**
  - S2 gather-evidence.
  - S3 escalate → **ESC incident in ServiceNow**.
  - Every decision traced: agent → gateway action id → ledger → incident.
  - Hostile/Rogue tests.
  - Second EP = the same evaluator + Finding contract at ServiceNow or Cedar.
- **Order of work (PB L326–333):**
  1. Hour 0–1: architecture + mentor + freeze `register.yaml` (owner Sree).
  2. C16 end to end first, through to the ServiceNow incident and the <2-min query.
  3. Start C9 baseline collection early.
  4. C7.
  5. S2 fix + S3 ESC.
  6. Adversarial cases + second-EP write-up.
  7. Evidence Pack (MANIFEST, submit, readback) and rehearse twice.

**Checklist (§3).**
- **3.1 Register:** fields, freeze before assessed runs, four justifications, version bumps, Sree's approval as a ServiceNow note, exploratory labelling, retention rule.
- **3.2 C16:** gateway lines are the figure of record, exact operator, overshoot visible, dedupe, INDETERMINATE when calls are missing, keep traceparent, blocked calls stay visible, inline only if a real hook exists.
- **3.3 C9:** closed UTC hours, Latency **Average** + Errors Sum per runtime, alert every crossing window, missing hour = UNKNOWN, model swap as a drift case.
- **3.4 C7:** expected events from an independent source, a missing middle event makes its gaps unmeasurable, same-clock timestamps, ledger read as JSONL.
- **3.5 Architecture:** register out of the path, stateless evaluator, no threshold literals, all four transports, second EP, five modes.
- **3.6 Evidence:** binding fields, all governed actions, stranger-verifiable. For the six questions: APPROVED = CR approvals export, AUTHORIZED = Cedar lines, INTEGRITY = the ledger's own verification + MANIFEST SHA-256 + S3 version id, RECONSTRUCT = per-run timelines.
- **3.7 Query tool:** one command, <2 min, offline, run ids and windows, with a human-loop line and an AICT line.
- **3.8 Agents.**
- **3.9 Adversarial log:** Hostile and Rogue cases, plus attacks on our own controls.
- **3.10 ServiceNow:**
  - L2: AICT Inventory of our runtimes under connection "iFabric Hackathon 2026", with "Execute Now" ready.
  - Human loop: every breach or escalation becomes an incident assigned to the owner.
  - L3: one finding id links AWS evidence → incident → a ServiceNow-native agent's analysis + its AICT trace.
  - Close INC0010231 before judging.
- **3.11 Gap list:** what / why / affected claim / impact / next, plus a platform-limit list (PB L482–490).
- **3.12 Judging day:** a 15-min pitch in 7 steps: L1 → L2 → L3 → controls → adversarial → second EP → gap list (PB L495–502).
- **3.13 Hygiene:** no secrets anywhere, backups, version pinning, decisions log.

**Scorecard (§4).** Every criterion with a ✅/⚠️/❌ column. All boxes are blank except L2 "(inventory ✅; traces unknown)" (PB L531) and second EP "(ServiceNow side ready)" (PB L560). §4.6 covers judge actions; §4.7 lists ten low-effort extras (same-ID chain, stranger README, pre-written run-ids.txt, decision log, RESPONDED and NO_RESPONSE incidents, kill-switch demo, model swap as a drift experiment, recorded backup demo, whiteboard photo, practising the judges' phrases).

**Timelines.** There are no absolute dates except the doc date (2026-10-05) and the handoff's example cutoff `2026-10-06T14:00Z` (HO L412). Relative timing:
- Hour 0–1 freeze.
- C9 needs closed UTC hours, so start early.
- New runtimes appear in AICT within ~20 min (HO L440).
- Assemble the evening before, rehearse twice, 15-min slot.

**ServiceNow integration plan (HO §0–§14).**
- **Already done (per Arth):** AICT connection, OAuth client-credentials integration user, and the live test INC0010231 (DELIVERED, reused, RESPONDED).
- **Still to do:**
  - Copy `prooflab/` into the repo; load 3 env vars; `selftest`.
  - Every evaluator writes an assessment and emits a Finding.
  - `notify()` runs **off-path** for BREACHED / ESCALATED / monitoring-gap only.
  - `check` (response or silence after a cutoff) and `export` before judging.
  - Store evidence in the §8.3 layout; build `MANIFEST.json`; submit to `team-evidence-613052889143` with readback.
  - The query tool prints a human-loop line read offline from the delivery log.
  - Arth supplies AICT screenshots, CloudTrail AssumeRole proof and the ServiceNow-native `iFabric-assurance-agent` (L3). Sree approves thresholds and optionally answers incidents.

**Scripts and commands it relies on.**
- **Playbook:** `new-agent.sh`, `run-reference.sh`, `score-run.py`, `spec.paused`, CloudWatch `AWS/Bedrock-AgentCore` queries, ledger `/records?cid=`, `~/starter/submit.sh`, MANIFEST generation, the AICT "Execute Now" button, and the brief's illustrative `controltest 16 --run FM-A`.
- **Handoff:**
  - `tar xzf` into the repo root, then `rm` the tgz (HO L139–141)
  - `python3 -m pytest prooflab/tests -q`
  - `python3 -m prooflab.servicenow selftest | notify [--dry-run] | check --cutoff | export`
  - `read -rs SNOW_CLIENT_SECRET`
  - optional `~/.prooflab-snow.env` (chmod 600)
  - `aws s3 ls` / `aws s3api head-object` readback
  - `SSL_CERT_FILE=$(python3 -m certifi)` on a Mac

---

## 3. Consistency check

Legend: **CONSISTENT**; **CONFLICTS** (both sides quoted); **UNVERIFIED** (no evidence either way in our sources, or verifiable only on ServiceNow, which we cannot see); **PARTIAL** (right in part, wrong or incomplete in part).

### 3.1 Priority items (as requested)

| # | Package claim | Our verified facts | Verdict |
|---|---|---|---|
| 1 | **What AICT sees.** PB L531: L2 = "AICT showing our agents (inventory, details, ideally Monitor traces)" with "(inventory ✅; traces unknown)". PB L404: "AICT inventory every 15 min". HO L441: AICT "does **not** discover EKS pods, MCP servers, MoDaaS guardrails, or which ModelConfig served a call". | SNr L28: "AICT discovers only AgentCore runtimes and gateways… Bedrock ListAgents, SageMaker ListModelCards… fail with AccessDenied every cycle". T4: "you will be able to discover your agents that's like 100 sure… maybe there are going to be limitations with the model discovery and the traces". | **CONSISTENT** |
| 1a | HO L78 (architecture): "AICT ◄── read-only discovery every 15 min (AgentCore runtimes, **models, traces**)". | SNr L28 (runtimes and gateways only); SNr L26: the connector role has no X-Ray or guardrail permissions; T4 warns of model/trace limits. | **CONFLICTS**: drop "models, traces" |
| 1b | HO L470 (gap entry to copy): "AICT discovery scope: discovers AgentCore runtimes, **Bedrock agents and SageMaker models** only". | SNm L12: "Module 11's 'Bedrock agents and SageMaker models' is false here". | **CONFLICTS**: the gap entry repeats the false Module 11 claim |
| 1c | **Usage counting.** Neither doc mentions it. The query-tool "AICT line" (HO L413) covers discovery only. | SNm L13: AICT's 15-min query filters `eventName = "InvokeAgent"`, "while our traffic has ZERO InvokeAgent events. So AICT's usage count for our agents is 0." | **Omission**: add to the gap list; never show AICT usage as evidence |
| 1d | **Monitor sessions/traces.** PB L474 "Show Monitor sessions or traces if available; otherwise state the gap". HO L442: screenshots of "Insights → Monitor session/trace for the named runs". | SNr L70: "monitoring covers **'Managed'** agents only. Unmanaged ones show 'Unable to show Monitor dashboard'". SNr L72: whether AWS agent runs are evaluated "is **not shown**". | PB **CONSISTENT** (honest fallback). HO L442 **UNVERIFIED/unlikely** unless our runtimes are marked Managed |
| 2 | **A ServiceNow instance and credentials exist.** HO L48–55: instance `platformdemoh8` "shared by all teams", connection "iFabric Hackathon 2026" → our account, 14 import jobs every 15 min, owner user (admin+itil), integration user `ifabric.integration` (itil) with an OAuth app, Basic auth 401, INC0010231 tested end to end. | SNm L29 and SNr L133: open question "Do we have a ServiceNow instance… with which roles and credentials?" SNm L21: "Vendor PDFs (demo instance platformdemoh8, not ours)". That refers to the **recordings**, not to whether the instance is shared. Supporting: T4 "AICT is not in the multi-talent [sic: tenant] mode. You guys all will have access to the same environment"; SNm L11 AICT assumes our role every ~minute (session `613052889143-session`); WP L263 a Logs Insights query every 15 min. | **UNVERIFIED by us, plausibly consistent.** If true it answers open question #1 (instance + creds held by Arth/Sree). Nothing in our data contradicts it |
| 2a | Rail 1: the kit's `escalate-to-incident.py` needs Basic auth (SNr L100); HO L54 "Basic auth returned 401 for both accounts". | SNm L26 / SNr L101–106: the Rail 1 traps (no escalate check, not idempotent, no assignee). | **CONSISTENT**: `prooflab` replaces Rail 1 and fixes two traps in code (correlation-id idempotency `notifier.py:127–133`; `assigned_to` `finding.py:104`). The escalate check is only *specified* (HO L271): the package never reads the ledger, so the ESC finding producer must be written by us |
| 3 | **Controls C7/C9/C16, C16 in scope.** PB L37–41; C16 first (PB L328, L360). | PP L38: "C16 IS IN SCOPE"; PP L32: the deck names only C7/C9; C16 lives via the masterclass and a judge's hint; CR L44: kit `evaluate.py` implements only C16. | **CONSISTENT** |
| 4 | **Judging levels.** PB L96–99 (L1 Foundation, L2 Observability, L3 extended chain; sequential). | PP L46–52 (slide "HOW YOU WILL BE JUDGED", same wording); PP L52: AICT is part of L2–L3, not L1. | **CONSISTENT** |
| 4a | **Axes / LOSE / artefacts.** PB L100–117, L130–137. | Slides p25–26 (e.g. "If we have to trawl your logs, you lose the mark"; "Built properly: yes. Actually worked: no"). | **CONSISTENT** (faithful paraphrase) |
| 5 | **Evidence Pack and six auditor questions.** PB L154–160; HO L423–432 maps each question to files. | PP L18–25: verbatim questions, "from your Evidence Pack alone… for an incident the judges pick from your event window"; "evidence must cover the whole window, including the Hostile/Rogue phases, not just 2 hand-picked runs". CR L28. | Questions **CONSISTENT**. Mapping **PARTIAL** (rows 5a–5e) |
| 5a | WHO (HO L427): "gateway caller identity; AgentCore runtime". | GL #2 / PVF L87, L108–112: every call is `ServiceIdentity::"bootstrap-key"`; all runtimes share one IAM role (PVF L117); PVF L80: "Gateway llm lines carry no agent identity". | **CONFLICTS**: the gateway identity cannot tell agents apart |
| 5b | AUTHORIZED (HO L429; PB L419): "Cedar/PDP decision lines… guardrail result". | GL #4 / PVF L38, L128: guardrail-blocked and pause-refused calls are logged `decision=ALLOW` in the PDP and `/modaas/evidence`. | **PARTIAL**: must join each decision to its gateway line to show served/blocked/refused |
| 5c | APPROVED (HO L430; PB L418): export `.status.governance.approvals`. | GL #5 / PVF L30, L77–78: free-text annotations with empty signature; a model swap needed no re-review; re-attest adds no record. PP L26. | **PARTIAL**: the export is fine but must surface the gap |
| 5d | INTEGRITY (HO L389 "The supplied audit-store ledger's own verification answers 'were records altered?'"; PB L422 "capture the ledger's own verification output"; PB L320 "tampered ledger record → ledger verification fails"). | GL #6: "the audit store has no signatures or hash chain, and its write token sits in plain text in every AgentConfig spec". NOTES #13 "No tamper evidence". PVF L54: the cockpit leaks the write token. Only a forged write **without** the token gets 401 (WP, Module 7). | **CONFLICTS**: no ledger verification feature exists |
| 5e | RECONSTRUCT (HO L432): "Ledger `/records?cid=` chain + spans by trace id + gateway lines". | RAF L27: "ledger trace_ids ≠ the run's trace id"; GL #7; PVF L137: the durable join is `trace_id` → `/modaas/evidence` `correlation_id`. | **PARTIAL**: spans cannot be joined from ledger trace ids; go via the CID |
| 6 | **Two-minute finish line.** PB L128, L431. | CR L13 (verbatim); Slides p26 "We type the question; you do not narrate the answer". | **CONSISTENT** |
| 7 | **Token measurements / C16 cap.** PB L48–54: 10,000 cap, FM-A 9,600 / FM-B 10,800, "copy the shape, not the values". The handoff hard-codes 10,000 in its examples (HO L195, L255, L328, L406). | CR L50–52: the guide's cap 900 (PASS 778 / BREACH 1030); "OUR measured runs are 25–50× larger: S1 24.8K–50.2K, S3 ~37.8K… S2 2.0M". CR L46: kit register limit 2000. CR L86–87: ~4.2K tokens per call regardless of model. PP L90–98: the judge's risk-matrix hint (tiered caps). | Playbook **CONSISTENT** in principle (illustrative). The handoff's examples would **CONFLICT** if adopted: any cap ≤10K (or the kit's 2K, the guide's 900) breaches every real S1/S3 run, leaving no PASS run. The package never states our measured range or the risk-matrix framing |

### 3.2 Other claims that matter

| # | Package claim | Our verified facts | Verdict |
|---|---|---|---|
| 8 | PB L255: "S2… currently fails (**7/10**)". PB L256: "Keep **S1** (auto-resolve) and **S3**… passing". | WP L85: S1 "FAIL 6/8 (guide PASS 8/8)", S2 "FAIL 5/10 (guide 7/10)", S3 "FAIL 8/10 (guide PASS 10/10)". RAF L38: guardrail and negotiation checks "fail by construction". | **CONFLICTS**: 7/10 is the guide's number. S1/S3 never pass the self-check. (PB L257 correctly calls it a self-check, not the rubric) |
| 9 | PB L29: "The resolution travels back through Gateway B and Gateway A. There is no direct route from the network to the customer." PB L30: at the gateway "budget is decided, and a run can be halted." | RAF L14: the agents "never call each other: `run-reference.sh` invokes customer, then IT, then network, sequentially". PVF L117–118: all runtimes share one role allowing `InvokeAgentRuntime` on `runtime/*` (peer-invoke block untested). CR L53–55: the gateway does NOT sum or cap per run inline; only account-wide 429 ceilings. | **CONFLICTS**: no zone hand-offs exist and there is no per-run budget decision at the gateway |
| 10 | PB L278: "Traces have no durable exporter here." PB L307: "The OTEL collector **discards** traces, so Cockpit Trace is empty". PB L483 gap: "no durable OTEL trace exporter". | PVF L20–23: the collector's traces pipeline exports to X-Ray ("X-Ray held 105 modaas-agw traces in 24 h"); PP L87: "X-Ray: ONE trace containing all 3 agent runtimes plus 45 modaas-agw segments". NOTES #32. | **CONFLICTS**: remove from the gap list. X-Ray is a usable RECONSTRUCT source |
| 11 | PB L307: "Gateway per-call usage = C16 figure of record". | RAF L31; PVF L56; CR (Module 8): the gateway line is the figure of record. | **CONSISTENT** |
| 11a | PB L365 / L308: "Preserve `traceparent`… or the gateway records fragment". Durability is not mentioned. | RAF L28: `modaas.run_id` = the **baggage CID**; PVF L62: "With no baggage CID, `modaas.run_id` = the trace id". PVF L17–18: run ids live "only in the gateway pod's stdout, which is ephemeral"; the durable log has none. CR L43: a pod restart loses attribution. | **PARTIAL**: the key is the baggage CID, and C16 needs pulls before any pod restart plus a durable trace-id join |
| 12 | PB L305: kill switch "next call 404; **~15 s to stop, ~50 s to resume**". | PVF L66: model pause "route withdrawn after ~33–41 s, and calls kept being served… Resume… ~35 s"; PVF L130: super-120b refused within ≤2 s; PVF L82: tool pause 1–7 s, unpause ~32 s; stale pause conditions remain. | **CONFLICTS** on timings. "Record requested vs effective times" is right |
| 13 | PB L301: "Patch **both** `dependsOn.models[0]` and `modelRef`… record the change as a new reviewed version". | RAF L16: "the operator ignores [modelRef] and generated CRs have none". PVF L77–78: a swap "keeps the agent Approved, with no new review. Re-annotating… adds no approval record." | **PARTIAL**: patching modelRef is harmless but useless, and a "new reviewed version" record has to be designed by us (PP L80) |
| 14 | PB L303: "restrict `toolName` in the team **Cedar ConfigMap** (the only allowed edit in `modaas-system`)". | PVF L36: "a team policy ConfigMap such as `my-team-policy` loads but is never consulted unless something names its id. To enforce your own rule, attach it to an asset (e.g. a ToolConfig `access.cedarPolicy`)." | **CONFLICTS**: a team ConfigMap rule is inert |
| 15 | PB L319 / L466: "unauthorized tool → Cedar deny" (Hostile/Rogue proof). PB L461: "tampered tool or skill → Cedar deny". | PVF L86–90: one identity (`bootstrap-key`); "the PDP evaluates the policy of the tool actually called… an agent can call any approved tool"; cross-tool calls were ALLOWED in vanilla runs. PVF L98: Cedar cannot see the calling agent. GL #3, GL #11 (tool code can change under approval). | **CONFLICTS**: per-agent deny is impossible today. Cross-tool use is **detectable** (`route_alias`, PVF L113) but not denied |
| 16 | PB L304: guardrail block = HTTP 200, `content_filter`, 0 tokens; PB L321 "bypass attempt → direct Bedrock denied". | PVF L64 (guardrail verified); WP L34: "direct Bedrock: AccessDenied (explicit deny)"; PVF L117–120 runtime-role Deny. | **CONSISTENT** |
| 17 | PB L306 / L268: 100 req/min, 2.5M tok/h account-wide; "don't run 3 agents at 1 RPS each". | PVF L47: per gateway replica, 1 replica, so effectively account-wide; NOTES #41 (3 agents = 180/min). PP L33: the token ceiling binds first (S2 used 80% at 49 req/min). | **CONSISTENT** (add: the token ceiling binds first) |
| 18 | PB L299 / L453: "Inject [gateway key, ledger token], never hard-code them". | GL #6, PVF L54, RAF L18: the platform itself puts the ledger write token in plain text in every AgentConfig spec, in `/tmp`, and leaks it via the cockpit. | **PARTIAL**: right for our code, but the platform breaks it. Belongs in the gap list (#6 already) |
| 19 | PB L297: "`ifabric_…` for every new agent, tool **and CR**". HO L57: "lowercase where Kubernetes requires it". | AgentConfig `hackathon-helper` ↔ runtime `hackathon_helper.DEFAULT` (PVF L22; WP). Kubernetes object names cannot contain `_`. `my-agent` is not prefixed. | **PARTIAL**: CR names `ifabric-…` (hyphen) give runtime `ifabric_…`. Kickoff rule confirmed (T4: "please rename the agents with your team name") |
| 20 | PB L371 / HO L259: C9 = AgentCore Latency **Average** + Errors Sum, 3600 s per runtime. PB L376 / L592: a model swap is a natural drift case. | PP L99–107 (Claude's Module 8 reading, undecided): "Use hourly **Maximum** latency plus the Errors sum, not the average. S2's loop showed Errors=0 but max 278 s"; latency is per invocation and "moves with call count"; "per-call latency looks comparable, NOT shown to be model-dependent". CR L48: the kit's C9 placeholder metric differs again. | **CONFLICTS** with the team's (undecided) Module 8 reading. "Swap = drift" is **UNVERIFIED** and may not show up in latency |
| 21 | PB L327: Hour 0–1, "freeze `register.yaml`… with dated thresholds". | PP L74, L79: "A new agent version is a C9/C16 'treatment'"; fix ledger emission "via CodeBuild → AgentConfig **before** thresholds and C9 baseline, and decide IT's model (currently nano-9b) first." | **CONFLICTS** on sequencing: freeze after the last agent change, before the first assessed run. All runs so far are exploratory (WP) |
| 22 | PB L280: Module 10 twin = "produce a passing run and a breaching run **on demand**"; C7 expected events "defined outside the graded agent". | PP L121–125: the kit's twin recipes fail; "the deployed network-twin Lambda reads its own packaged data, and S2 has no twin site"; GL #10: the network agent queries element ids and gets "no twin data" 40×. | Principle **CONSISTENT** (deck p21). "On demand" needs the fixtures built first |
| 23 | PB L284–285 (kickoff): AICT + human loop "absolutely needed"; own connector with the team name; rename agents; don't change risk frameworks; one ServiceNow agent enough, no bonus for workflows; clone, never edit. | T3: "service now control tower and human loop that is absolutely needed"; T4: connector "with your team name", "rename the agents with your team name", "You can create one agent… more than enough", "not going to give you bonus points for creating agentic workflow", "clone… duplicate… rename"; master brief L325 "Avoid broad reconfiguration of shared risk frameworks". PP L67: whether AICT is *required* still needs an organiser ruling. | **CONSISTENT** |
| 24 | PB L248/L235 EP definition vs PB L324, L398, L560 and HO L35, L274: the **second enforcement point** = "human approval queue (ServiceNow)" via the S3 escalation, "(ServiceNow side ready)". | Internal: PB L235 "a dashboard is **not** an EP ('sees everything, can refuse nothing')"; PB L249 "Every EP does… ask, wait, act, record". HO L86/L247: `notify()` runs **after** evaluation, "never inside an agent request". PVF L114: "Agents have no action/change tool, so there is nothing unsafe to deny in S3." | **CONFLICTS** (the package contradicts itself): a post-hoc incident neither waits nor refuses. Risky to claim as EP2 |
| 25 | PB L558: continuous compliance, "Partial: near-real-time evaluation on a short loop… labelled honestly"; HO L300–303 (5-min loop). | Slides p26: "An inline decision, live: show a verdict being formed in the path, **not replayed afterwards**"; p25 "a verdict formed inline, in the path, while it runs". | Partial credit **UNVERIFIED** (the slide wording argues against it). The honest labelling is right |
| 26 | PB L141 / HO L394: judges read the team S3 bucket; `submit.sh` "packages `~/evidence`, `register.yaml`, `gap-list.md` and `run-ids.txt`" to `team-evidence-613052889143`. | CR L38: "**It needs the team name as an argument** (`TEAM="${1:-}"`); the page's bare `bash ~/starter/submit.sh` prints usage." Bucket name matches workshop-aws-access. PP L62: the zip takes those files from a dir (repo root for `gap-list.md`). | **PARTIAL**: the handoff omits the team argument, and its layout (HO L373–374 puts `run-ids.txt` and `gap-list.md` under `evidence/`) does not match the kit |
| 27 | PB L259–266 / L457–471: the three alert levels, as a self-driven adversarial log. | PP L27–31: Vanilla 3h / Hostile 4h / Rogue 3h; "Who injects these is unknown". | Levels **CONSISTENT**. Who injects: **UNVERIFIED** (organiser question) |
| 28 | PB L286 / L428: no signatures, hash chains or Merkle. MANIFEST SHA-256 allowed (HO L390). | PP L63–65: "signing, hashing and Merkle trees over the ledger" not asked, not scored. | **CONSISTENT**. A MANIFEST over the pack files is cheap, but expect no credit for it |
| 29 | PB L184–188, L347, L355: owner = Sree (named person) for all three controls; four roles, "nobody checks their own work"; HO L3: Arth runs ServiceNow; "the teammate" runs AWS. | PP L11: "two-person team (per the handoff)" (the earlier baseline handoff). Our sources don't name team members. | **UNVERIFIED**: team composition and roles need confirming. GRC and assurance roles are unassigned |
| 30 | PB L302: the template's `GatewayModel(OpenAIModel)` strips empty `tools: []`. | WP L160: "Template: GatewayModel present". The stripping detail is not in our notes. | **PARTIAL / UNVERIFIED** |
| 31 | PB L307: ledger `/records?cid=` is JSONL and `/timeline` is text; PB L366 blocked calls = 0-token records. | PVF L24; CR (cookbook): the timeline is text; PVF L64. | **CONSISTENT** |
| 32 | HO L50: 6 AICT "AI Function" records (helper + 3 reference agents incl. v2s). | PVF L117: 4 runtimes; WP: the IT swap and network regeneration created new versions; `my-agent` was created after the package. | **UNVERIFIED** (ServiceNow side), plausible. `my-agent` should now appear too |
| 33 | HO L53 / L473: the team **enabled a Global instance property** (`glide.oauth.inbound.client.credential.grant_type.enabled`) on the shared instance. HO L8, L463: "Do not change ServiceNow configuration… system properties". | T4: "AICT is not in the multi-talent [sic: tenant] mode… It's not going to interfere with the other teams" (organiser's expectation). | **UNVERIFIED / governance risk**: a shared-instance change. Disclosed in HO L473; the "courtesy note to facilitators" is still pending (HO L515) |

---

## 4. Actionable / adapt / risky

### 4.1 Directly actionable for the planning session
1. **Use PB §1 as the rubric checklist.** It is a faithful restatement of the masterclass (axes, LOSE list, six artefacts and out-of-scope match slides p25–26), and the §4 scorecard is ready to use as the team tracker.
2. **Adopt the evaluator rules in PB §3.2–§3.4 as test cases.** They cover: exact operator and visible overshoot; INDETERMINATE for under-cap with missing calls and BREACHED for over-cap with a trusted subtotal; dedupe across sources; blocked calls recorded as blocked; missing hour = UNKNOWN plus a monitoring-gap finding; an alert per crossing window; expected events from an independent source; no bridged gaps; same-clock subtraction. All of this is platform-independent and matches our facts.
3. **Register design (PB §3.1).** Fields, the four justifications, version bumps instead of edits, and labelling our pre-freeze runs as exploratory. Every run so far is exploratory (WP).
4. **The ServiceNow human-loop adapter** (`prooflab/servicenow`) as the alerting component. It is stdlib-only, idempotent via deterministic `finding_id`, never touches other teams' incidents (`sys_created_by` filter), and records responses honestly, with a terminal state on every path. It replaces kit Rail 1 and fixes its three known traps.
5. **The Finding contract (HO §6)** and **reference prefixes (HO §8.2)** as the binding between evaluators, evidence files and the query tool.
6. **The query-tool output spec (HO L404–415, PB §3.7).** One screen, offline from the pack, run-id and window queries, showing rule/version/date/owner, population, measured vs limit, verdict, gaps, record refs, and human-loop and AICT lines.
7. **Order: C16 first, start the C9 baseline early, then C7.** This matches CR L44 (only C16 has a kit evaluator) and PP time-sensitivity.
8. **S3 → ESC incident** as the human-loop demonstration. Our S3 behaviour is already correct ("all escalate", WP).
9. **Gap-list discipline (PB §3.11).** Add the "affected claim/control" field to our existing `gap-list.md` entries (kit format: what/why/impact/next day).

### 4.2 Needs adapting before use
1. **C16 thresholds.** Discard the 10,000 example values throughout HO (L195, L255, L328, L406). Derive caps from our runs: S1 24.8K–50.2K, S3 ~37.8K, S2 2.0M, ~4.2K tokens per call regardless of model. Use the judge's risk-matrix hint (tiers). Note that the kit's 2,000 and the guide's 900 would breach every run.
2. **C16 data durability.** `modaas.run_id` exists only on ephemeral gateway stdout, so pull before any pod restart. The durable path is CloudWatch `trace_id` → `/modaas/evidence` `correlation_id`. The run key is the baggage CID, not traceparent. Pause 404 lines carry no run id on stdout (expect "unmatched calls", hence INDETERMINATE). `evaluate.py` counts MCP lines as calls.
3. **C9 metric.** Decide between Average (PB/HO), Maximum + Errors (our Module 8 reading) and gateway per-call duration. Errors stayed 0 during the S2 runaway. Decide the IT agent's model before baseline hours start. Don't promise "model swap = detected drift".
4. **C7 expected events.** Build the twin/scenario fixtures first (twin keyed by site ids; S2 has no site). Gaps are seconds, not ms, and ledger `seq` (epoch ms) can collide.
5. **Six-question mapping (HO L427–432):**
   - WHO: corroborate the agent via per-runtime logs and the AWS-written `/aws/bedrock/aict-invocations` (`InvokeAgentRuntime` principal, SNm L14–19), not the gateway identity.
   - AUTHORIZED: join each PDP ALLOW to its gateway line to report served / blocked / refused.
   - APPROVED: record the generation, model and image each approval covers.
   - INTEGRITY: replace "ledger verification" with cross-surface corroboration + MANIFEST + S3 version id. `aict-invocations` is a platform-independent source the package never uses.
   - RECONSTRUCT: join via CID → `/modaas/evidence` → trace id.
6. **Fix the AICT text in the handoff before reuse.** HO L78 "models, traces" → "runtimes and gateways". The HO L470 gap entry → "AgentCore runtimes and gateways only; Bedrock agents/SageMaker AccessDenied". Add "AICT usage count = 0 for our traffic (InvokeAgent filter)" and "Monitor = Managed agents only".
7. **Replace incorrect gap/field-guide entries.** PB L483 "no durable OTEL trace exporter" is false (X-Ray). Use our measured kill-switch times instead of PB L305's. Remove "restrict toolName in team Cedar ConfigMap" (inert; use ToolConfig `access.cedarPolicy`). Recast "unauthorized tool → Cedar deny" as detection (`route_alias`) plus a gap. Recast the scenario's "Gateway A/B, no direct route" as aspirational, not live.
8. **Second enforcement point.** Either build something that genuinely waits or refuses (for example an inline C16 admission `evaluate()`, or a ToolConfig `access.cedarPolicy` deny on a tool, which is a cluster write), or present the ServiceNow incident as `callback()` alerting, not as an EP. Today agents have no action tool for a human queue to gate.
9. **Continuous compliance.** Label the 5-min loop as "near-real-time post-run evaluation". Only an in-path verdict matches the slide wording.
10. **Naming.** CRs `ifabric-…` → runtimes `ifabric_…`. Decide whether `my-agent` should be recreated or renamed in AICT.
11. **Hand-in mechanics.** `submit.sh <team>` needs the team argument. Reconcile the HO §8.3 layout with what `submit.sh` zips (`~/evidence/`, `register.yaml`, `gap-list.md`, `run-ids.txt`, sketch) and with the Evidence Pack format the user will provide (PP L38).
12. **Code issues in `prooflab/servicenow`:**
    - `notifier.py:127–136`: the existing-incident lookup runs **before** the `dry_run` check. So HO §5.4's verify step (`notify --finding examples/test_finding.json --dry-run`, which maps to INC0010231) returns `DELIVERED (reused)`, not `DRY_RUN`, and appends INTENT + DELIVERED to `evidence/servicenow/delivery-log.jsonl`, a test entry in the Evidence Pack log. Point `PROOFLAB_DELIVERY_LOG` at a scratch path for tests, or reorder the code.
    - `notifier.py:183–204` with HO L477: on the real instance the journal ACL returns **0 rows, no error**, so `readable` stays True and `RESPONSE_UNKNOWN` never fires. Detection then falls back to `sys_updated_by`. If anyone else updates the incident after the owner, the owner's response is overwritten and `check` records a **false NO_RESPONSE_OBSERVED** after the cutoff. The fake models a 403 (`fake_servicenow.py:173–174`), so no test covers the real behaviour. Consider parsing `notes_display` (already fetched by `export`).
    - `cli.py:60`: every command, including `--dry-run`, needs live credentials and makes live reads (owner, caller and incident lookups). Dry-run is not offline.
    - C9 "one incident per crossing window per runtime" (HO L260, L491) could create many incidents on a shared instance. Bound it, or agree it with the owner.
13. **Missing glue (not in the package).** The package ships only the ServiceNow side. We must write:
    - the ledger → ESC Finding producer (parse `/records?cid=`, check `disposition=escalate`)
    - the evaluator runner (`publish()`, HO L277–297, exists only as a doc snippet)
    - the C7/C9 evaluators, assessments, MANIFEST builder and query tool
14. **Pitch.** The PB L495–502 7-step pitch may not match the judged format (a judge-as-auditor picks an incident and asks six questions from the pack, PP L18). Prepare both.

### 4.3 Risky (writes to shared systems, destructive, or depends on unverified access)

All cluster and AWS writes need the user's explicit OK under the working agreement (WA L11).

| Item | Where it writes | Risk |
|---|---|---|
| Kill-switch demo (PB L470, L591) | Cluster: `spec.paused` on a model or tool | Pausing a model affects every agent in the account for ~33–41 s, and calls are still served in that window. Stale pause conditions remain after resume (PVF L66). |
| Model swap as a drift experiment (PB L376, L592) | Cluster: AgentConfig patch | No re-approval is triggered (an APPROVED gap); it invalidates the C9/C16 baselines; it may not produce detectable latency drift. |
| ToolConfig `access.cedarPolicy` edit (EP2 or Hostile "Cedar deny") | Cluster: CR → `modaas-system` ConfigMap | Whether it resets approval is untested. One shared identity means the deny hits **all** agents. |
| Rogue "deleted or tampered record" (PB L468), forged ledger writes with the real token | Live audit store | Pollutes the shared evidence ledger and the event window the judges sample; cannot be undone. Do it on an **exported copy**. |
| "Tampered tool or skill" (PB L461) via `UpdateFunctionCode` on `team-*` Lambdas | AWS Lambda (shared tools) | Every agent's tool would change, with no approval trail (GL #11). Use a separate test tool or a copy. |
| S2 as the C16 breach / "retry loop" case (PB L469) | Shared model budget | ~2.0M tokens = 80% of the account's 2.5M/h ceiling (WP), risking 429s for teammates and contaminating C9 hours. Cap it with per-invocation limits or engineer a smaller breach. |
| Agent rebuilds (S2 judgment fix, `ifabric_` agents) | CodeBuild → ECR → AgentConfig → approval | Each rebuild is a new version (a C9/C16 "treatment"); the approval mechanics are self-asserted. |
| Global OAuth property already enabled on the shared instance (HO L53, L473) | ServiceNow (all teams) | Already done by the team. Needs disclosure and an organiser OK; the courtesy note is still pending (HO L515). |
| `notify` / C9 per-window incidents; `selftest`; `--dry-run` | Shared ServiceNow instance (reads; creates for real `notify`) | Volume on a shared instance; `--dry-run` still reads live and writes local log lines. |
| `SNOW_CLIENT_SECRET` in env or `~/.prooflab-snow.env` (HO L167) | Local disk | Add its exact value to `pre-push-secret-scan.sh` (WA L16–18). Never in screenshots, including the AICT ones. |
| Extracting into the repo root and deleting the tgz (HO L139–141) | Repo | A repo write; ask first (WA L11). |
| All ServiceNow-side facts (instance, connection name, users, OAuth app, the owner's admin role, INC0010231, AICT "Execute Now", the ServiceNow-native agent's AICT trace) | n/a | **Unverified by us.** L2/L3 plans depend on Arth's access. The AICT Monitor/trace evidence is unlikely without "Managed" status. |

---

## 5. Open questions

1. **ServiceNow access.** Can Arth show us (screenshot or export) the "iFabric Hackathon 2026" connection on `platformdemoh8`, with import times we can match to our CloudTrail AssumeRole and discovery calls? That would turn §3 row 2 from UNVERIFIED to CONSISTENT.
2. **Team and roles.** Memory says a two-person team. The package names Arth (ServiceNow), Sree (owner / accountable management) and "the teammate" (AWS). Who is GRC and who is assurance? Who rehearses as the outsider?
3. **AICT Managed status.** Are our runtimes "Managed" in AICT (required for Monitor/evaluation)? Can we or Arth set it? Has anyone renamed our discovered agents with the team name, as the organiser asked (T4)?
4. **Shared-instance property.** Did the organisers approve the Global OAuth property change, and has the courtesy note been sent?
5. **Evidence Pack format.** It is pending from the user (PP L38). It decides whether the HO §8.3 layout, the kit `submit.sh` layout, or a merge is used.
6. **EP2 choice.** Inline C16 admission, a ToolConfig Cedar deny (cluster write), or no EP2 claim? The ServiceNow incident alone cannot refuse anything.
7. **C16.** Cap values and tiers (risk matrix); whether helper/investigator calls count; how a PASS and a BREACH run are produced without spending the shared token ceiling.
8. **C9.** Metric (Average vs Maximum vs gateway per-call duration); IT model (nano-9b vs super-120b) fixed before baseline hours.
9. **Hostile/Rogue.** Who injects them and when (organisers or us)? Can the destructive Rogue cases be run on copies?
10. **Timing.** Judging start and the `check --cutoff` value. HO's example is `2026-10-06T14:00Z`; the event stop is reported as Tue 10:00 CDT (15:00 UTC), which is not independently confirmed (PP L68).
11. **Tests.** Do the 46 tests pass in our environment? They were not run here (read-only constraint).
12. **AICT usage query.** Can the facilitators widen it (`InvokeAgentRuntime`, `Converse*`) or run `cloudtrail validate-logs` for our window (SNr L135–136)?

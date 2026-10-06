# 14 · Vetting Arth's handoff-3 deliverables against our architecture and verified facts

Written 2026-10-05, from about 23:40 UTC, by the deliverables-vetter subagent, for the captain. Read-only: this file is the only one written.

**Scope.**
- Every file under `~/Downloads/ifabric-handoff-3/deliverables/` and `docs/`.
- The parts of `evidence-console-plan/` those files depend on:
  - the judging-day guide, which the running order names as the "current run of show";
  - spec 08 §5.0–§5.4, which TEAMMATE_ACTIONS cites as "handoff 2";
  - the code paths cited below.
- Compared with:
  - `gap-list.md` (re-read at its 18:51 CDT state);
  - `PLANNING-HANDOFF.md` ([PH]);
  - `architecture/ARCHITECTURE.md` ([A], re-read at its 18:51 CDT state, while it was being edited);
  - `architecture/decisions.md`;
  - the repo's `HACKATHON_WINNING_PLAYBOOK.md` and `SERVICENOW_INTEGRATION_HANDOFF.md`;
  - the feasibility reports 05–08 ([05 AR-n], [06 Xn], [07 GS-n], [08 SN-n]);
  - the independent review [04b];
  - the memory file `platform-verified-facts` ([mem]).

**Checks run (all read-only):**
- `python3 -B deliverables/evidence-pack/tools/manifest.py verify .` on the package printed `OK: every file matches MANIFEST.json`.
- The kit's own register loader (`workshop-assets/starter/evaluate.py` `_load_register`), run in memory on Arth's `register.template.yaml`:
  - the no-PyYAML path finds **0 controls**;
  - the PyYAML path keys the controls `ACN-COST-001`, `AIA-LOG-001` and `AIA-ARC-006`, so there is no `16`, `7` or `9`;
  - for comparison, the kit's own template parses as `16`, `7`, `9`.
- `diff` and `sha256` of `docs/` against `deliverables/docs/` and against the repo copies; greps of Arth's code for every behaviour cited.
- **Not done:**
  - the 152 tests were not re-run, because pytest writes caches into the package;
  - no ServiceNow, AWS or git action was taken.

**The captain's direction (2026-10-05), applied throughout.**
- Arth's code and deliverables are used as-is where possible. His templates, pitch and run-of-show are the base.
- We add only what a verified fact or our architecture requires.

So every finding is sorted one of three ways:
- **R-n, a required correction:** a verified fact or the kit contradicts Arth's text. It is fixed when we adopt (§8.2) and needs no decision.
- **C-n, a conflict to resolve:** two valid designs collide, or our side is still pending the captain (§9). Only these need a decision.
- **An inconsistency inside Arth's own set:** fixed in the adopt notes.

**One identity fact shapes the action list.**
- PH §1: "The user (Sree) builds the AWS side and is the control owner named in the SN handoff". PH §4.1: "per the user, Sree is the user".
- So Sree is the captain. Arth's documents address "the teammate" and "Sree" as two different people.
- Here every teammate action and every Sree action is the captain's (§7). Arth's separation-of-duties claims become C-5.

---

## 0. Verdict in one screen

- **The package is sound and adoptable.**
  - It verifies against its own manifest.
  - The ServiceNow write path was verified live on INC0010232.
  - What is still pending is stated honestly: the Nemotron call, the Assurance Agent's AgentCore runtime, and AICT's discovery of it.
- **`docs/` changed only for the Nemotron ruling:** 2 edits in the playbook, 4 in the SN handoff. None of our 17 verified playbook corrections was taken in, so all of them still apply (R-16).
- **Eight decisions for the captain** (§9):
  - C-1: which "second enforcement point" we claim, and one EP numbering;
  - C-2: C9's window and baseline;
  - C-3: which dashboard to build;
  - C-4: what the agent-movement trace says about our script-made handoffs;
  - C-5: the separation-of-duties wording;
  - C-6: the live inline bonus vs the guide's "Live · Replay";
  - C-7: the register approval sent as a Finding;
  - C-8: three small ones (run-ids format, where the submission record lives, Arth's hours).
- **21 required corrections** (§8.2). These hurt most if missed:
  - R-1: the register template doesn't parse with the kit;
  - R-6: the Assurance Agent deploy, as written, fails the CR name check or dies with an ImportError;
  - R-8: its model calls can land inside a run's C16 total;
  - R-2: the evidence README cites a ledger verification output that doesn't exist;
  - R-20: a trace over 200 steps makes `notify` fail before any incident is raised.

---

## 1. Per-document table

Codes point to §8.2 (R-n) and §9 (C-n). "Ours" means our architecture or verified facts.

| # | Document | What it claims or plans | Conflicts (Arth ↔ verified facts or ours) | Adopt | Asks of the captain / teammate |
|---|---|---|---|---|---|
| 1 | `deliverables/README.md` | Index of the deliverables. Status: verified live (AICT connected; OAuth; INC0010231 create, read back, reuse, owner response; INC0010232 full finding in the description; the Assurance Agent's write path 9/9 with a stand-in model). Built but not live: the Nemotron call, the panel. Superseded: the ServiceNow-LLM agent. Lists Arth's six remaining actions | "AICT connected and discovering our runtimes": the AWS half is proven (AICT's role polls `ListAgentRuntimes` every 14–16 min and read `my_agent` 12 times [08 AI-01, AI-02]). The ServiceNow-side import of a runtime we created is not: "whether `my_agent` shows in AICT is unverified" [08 AI-02]. Everything else in its status list holds | Its status discipline ("never claim more in the demo") and its three status groups, as the pack's status language | Start with TEAMMATE_ACTIONS; receive the OAuth id and secret privately; Sree approves the register and the Assurance Agent's CR (§7) |
| 2 | `deliverables/PRESENTATION_DAY_INTEGRATION.md` | The six artefacts in S3, "submitted **the evening before** and read back"; who brings what; the final `evidence/` tree; 7 integration steps; on-day setup; final checklist | (i) The tree puts `register.yaml`, `run-ids.txt`, `gap-list.md` and `architecture.md` inside `evidence/`, but `submit.sh` takes those three files and `sketch.png`/`.jpg` from WORKDIR [kit `submit.sh:62–79`; A §9.1] (R-9). (ii) "`raw/` … never edited", with `cr-status/` in it: the kit's capture holds 15 copies of the ledger token [06 D4] (R-10). (iii) Step 6, "Record keys, ETags and time in README §10", after upload, against step 7, "No edits after upload" (C-8b). (iv) "The evening before": work stops and judging starts 2026-10-06 15:00 UTC (UNCONFIRMED) [PH §2.5]. Our first submit is at 08:30–10:00 UTC, the final at 12:30–13:00 UTC [A §12.1]. (v) The checklist's "approved by Sree … (dates prove it)": T1 alone is the date proof, and T2 corroborates [A §3.3] | §2 tree, merged with A §9.1; §3 step order; §4 on-day setup; §5 checklist, plus T1, the redaction scan and the risk and inventory files | Build `evidence/`; final `check`, `export` and `case --out`; MANIFEST; `submit.sh`; readback; rehearse twice (§7, rows 16–20) |
| 3 | `deliverables/TEAMMATE_ACTIONS.md` | 14 steps in phases A–H, each with a "done when"; the teammate owns all six artefacts | A.2 asks "whether an API key is needed": yes, authz is FailClosed on every listener [mem] (R-7). A.4, "Start C9 baseline collection now", against D3 (C-2). Phase C's trace rules against our script-made handoffs (C-4). A trace over 200 steps is rejected, not truncated (R-20). Phase D, "through `new-agent.sh`", against [05 AR-01/02/03/05; A §7.1] (R-6). Phase E's backend endpoint against D1 (C-3). Phase F's "agents → EP1 gateway" against our EP numbering (C-1) | The phase order (it matches A §12.1: C16 → S2/S3 → C7 → C9); every "done when"; the finding-context contract (spec 08 §5.0); the "Never" list | All of §7 |
| 4 | `deliverables/architecture/servicenow-section.md` | The ServiceNow half of the one-page sketch: a diagram and 8 facts (off-path; EP2 = the human queue; transports; register out of the path; Nemotron only; trust and identity; same id everywhere; deterministic analysis) | "**Second enforcement point (EP2): the ServiceNow human queue**" and "agents ─► EP1 modaas-agw" against D6 and our EP-1/EP-2/EP-13 (C-1). "`callback` \| none" against A §3.2's notify-then-poll `callback()` (C-1). "EP1 modaas-agw ─► Nemotron (governed, guardrail-checked, ledger-recorded)": the gateway writes nothing to the audit ledger (R-4). The route rule (C-4) | Facts 1 and 3–8 (fact 3 worded per C-1) and the diagram's ServiceNow column, redrawn into `architecture/one-page.svg`/`.md` with our numbering | Merge into Artefact 5 (the sketch) |
| 5 | `docs/HACKATHON_WINNING_PLAYBOOK.md` (= `deliverables/docs/`) | Our playbook plus two edits for the Nemotron ruling (§2) | The new L3 text promises "the agent's **AICT trace**" (R-5). Every claim our corrections refute is still there (R-16) | The two edits, with R-5 | None new |
| 6 | `docs/SERVICENOW_INTEGRATION_HANDOFF.md` (= copy) | Handoff 1 plus four edits for the ruling (§2). The Assurance Agent's deploy moves to us: "Teammate deploys; Arth supports" | It still says "Too many incidents for C9 \| Expected: one per crossing window. Do not merge windows" (l.491) (C-2). It still uses the illustrative 10,000-token cap (l.195, 255, 328, 406), which every measured S1/S3 run (24.8K–50.2K) would breach [PH §3b Q2] | The four edits | Deploy the Assurance Agent (R-6) |
| 7 | `evidence-pack/README.md` | The stranger's README skeleton (§1–§12). §7–§9 (ServiceNow) are complete; retention is 7 years | §3 item 3 and §6: "Ledger integrity: `raw/ledger/verify-<date>.txt` (the audit store's own verification output)". No such route exists (R-2). §6 WHO, "gateway caller identity in `raw/gateway/`": one shared principal (R-3). §8: the action id "joins to `raw/gateway/` and the ledger" (R-4). §1's claim uses the playbook's wording, not the slides' (R-21). §12: "Nobody approves their own work" (C-5). §10, the submission record (C-8b) | The skeleton, §2 retention, §7–§9 and §11's test-only rule, with R-2, R-3, R-4 and R-21 applied and our layout in §4 | Fill every `<…>`; delete the teammate note |
| 8 | `evidence-pack/gap-list.md` | Section A (A1–A18, Arth's); section B prompts B1–B8, for us to fill | B1's prompt ("Durable OTEL trace export: no durable exporter?") invites a false gap (R-17). A1's "one gateway IAM principal", A3's cause and next step (R-18), and A10's "ledger-recorded" (R-4). Details in §3 | Section A as the merged file's section A; our 11 entries plus the design gaps as section B | Fill section B; update every status line before submitting |
| 9 | `evidence-pack/decisions-log.md` | 13 dated rows: the AICT schedule (1 h → 15 min); the owner; the integration user; OAuth and a Global instance property; readback and reuse; the journal ACL; the full finding in the description; the ServiceNow-native prototype; the Nemotron ruling; 3 judged fields; note trust by digest; 7-year retention; one spec. Plus 2 placeholders | "Owner … One named person, not a team; owner ≠ builder" (C-5). Nothing else conflicts. Our `decisions.md` lacks the retention rule, the OAuth property change and the AICT schedule | Its format (date · decision · why · who · reference) as the pack's `decisions-log.md`; append D1–D16 (as `decisions.md` now lists them, 19:06 CDT) and the answers to C-1…C-8 | Append threshold and AWS decisions |
| 10 | `evidence-pack/run-ids.txt` | A template (§4.1) | Not the kit format: control-first columns, comment lines and placeholders. The kit asks for "one run id per line" [`submit.sh:23`]. The C9 rows name a "window id" (C-2, C-8a) | Its columns, as annotations after the CID | Write it before judging; add the INC numbers from Arth |
| 11 | `evidence-pack/tools/manifest.py` + `test_manifest.py` | A SHA-256 and size manifest with `build` and `verify`, plus 5 tests (§4.2) | None. It lacks the `source` and `captured_at` that A §9.1 puts in MANIFEST.json, but our capture manifests already carry those | As-is, as the pack's integrity tool. It replaces the planned `store/manifest.py` | `build` last; `verify` on the downloaded copy |
| 12 | `evidence-pack/servicenow/` (README + `wiring-tests/`) | How each `servicenow/` file is produced; the TEST-ONLY wiring history: INC0010231, INC0010232, the stand-in round-trip and the superseded prototype (§4.3) | None with verified facts. It matches our split between test and assessed runs. It confirms live the behaviour behind 08's bug (b): `journal: []` and `at_basis: last_update` | The folder layout and the TEST-ONLY rule, as-is | Never copy the wiring logs into the production log; run `export` and `case --out` (§7) |
| 13 | `pitch/running-order-15min.md` | A 15-minute order: L1 → L2 → L3 → controls → adversarial → second EP → gaps. It says the judging-day guide supersedes it | It claims ServiceNow as the second EP (C-1), and has no slot for the live inline decision (C-6). Otherwise it is compliant (§5) | Superseded: use the guide (row 14) | — |
| 14 | `evidence-console-plan/presentation/JUDGING-DAY-GUIDE.html` (the "current run of show") | 8 steps, each one screen and one sentence; set phrases; likely questions; a before-stage checklist | Step 6 shows "Live · Replay" as the inline bonus (C-6). "Nobody checks their own work: Sree approves, the builder builds, Arth tests" (C-5). Its screens assume the Evidence Console (C-3). Step 4's movement (C-4). Step 7's second EP already matches D6 | The base run-of-show: the 8-step order, timings, phrases and Q&A (§5) | Rehearse twice; "say nothing until the answer is on screen" |
| 15 | `pitch/pitch-L2-L3-script.md` | Arth's ~4 minutes: AICT (L2), the evidence chain and the Assurance Agent (L3), the second EP, an adversarial beat, and a Q&A table | "**Agent movement:** customer agent, gateway, IT agent, gateway, network agent, gateway, back to the customer" is not how our runs move (C-4). "The ServiceNow human queue is our second enforcement point" (C-1). Step 6 is a ~110-word narration (§5) | The Q&A table and the L2 lines; trim each beat to one sentence per screen | — (Arth presents) |
| 16 | `pitch/backup-demo-shot-list.md` | An optional 3–5-minute recording in 7 segments; the offline fallback is the panel opened from disk | A recording can't earn the inline bonus: "not replayed afterwards" (C-6) | As-is; add the recorded N3 halt, labelled "recorded, not live" | Record it if time allows; no secrets on screen |
| 17 | `thresholds/register.template.yaml` | The threshold-document template: claim, owner, builder, retention, a version and date per control, four justifications and a governance tree per control; placeholders only | It doesn't parse with the kit (R-1). It has no T1, no risk register (`risk_ref`, `risks.yaml`), no C16 modes, tiers or safety ceiling, no C7 workflow events and no data rules (§6). Its `enforcement_point` example reads "modaas-agw shared model gateway (EP1)" (C-1). The `builder` comment (C-5). The claim wording (R-21) | Its content and comments as the base, reshaped into our flat schema (§6) | Fill it from the pilots, with the four answers per control |
| 18 | `thresholds/threshold-approval.md` | The T2 workflow in 9 steps: DRAFT → FROZEN + hash → an approval incident (a Finding, with its own delivery log) → Sree's dated "APPROVED … sha256" note → `check` → `export` → copy unchanged → assessed runs | A Finding, against A §3.3's "not a Finding" (C-7). It treats the ServiceNow note as the date proof; ours is T1 (§6). A relative `PROOFLAB_DELIVERY_LOG` (R-11). Sree approves her own register (C-5) | The workflow, with T1 first and both sha256s in the note (§6) | Sree writes the APPROVED note; Arth runs steps 2–8 |
| 19 | `thresholds/approval-finding.template.json` | `control_ref: REG`, `verdict: ESCALATED`, `scope_kind: escalation`, `kind: approval` | It passes `finding.py`'s validator (`ESCALATED` is a verdict, `escalation` a scope kind). The issue is how it's handled downstream (C-7) | As-is, plus `risks:sha256=…` in `evidence` | Fill it at the freeze |

---

## 2. `docs/` against the repo copies

**The files.**
- `docs/` and `deliverables/docs/` are byte-identical (sha256 `f3eef2a6…` for the playbook, `42c97ceb…` for the SN handoff).
- The repo copies differ (`17167492…`, `dc05f583…`): 54,421 → 54,668 bytes and 36,617 → 36,934 bytes.

**The playbook: 2 edits, both from the facilitators' Nemotron ruling.**
- **§3.10 [BEST] "L3 chain".**
  - Was: "…the ServiceNow-native agent's analysis, plus that agent's **AICT trace**. Clearly label which model ran where (Nemotron on AWS; ServiceNow LLM in ServiceNow)".
  - Now: "…the **Nemotron Assurance Agent's** analysis note on that incident, plus the agent's **AICT trace** (AgentCore runtime `ifabric_assurance_agent`). Facilitator ruling 2026-10-05: the Assurance Agent must use Nemotron, so it runs on AWS via `modaas-agw` and writes into ServiceNow".
- **§4.1, the L3 row:** the same substitution, plus "(provenance line with the gateway action id)".

**The SN handoff: 4 edits, same cause.**
- The requirements table's L3 cell: "a ServiceNow-native agent (Arth, later)" → "the Nemotron Assurance Agent writing into ServiceNow".
- The §9 AICT row: its owner moves from "Arth, after controls produce findings" to **"Teammate deploys; Arth supports"**.
- The rules list: "The ServiceNow agent uses ServiceNow's LLM; label it as such" → "Nemotron only … This includes the Assurance Agent … the earlier ServiceNow-LLM prototype is inactive".
- The §14 owner table: Arth's task becomes "Assurance Agent support".

**What did not change matters more.** Our playbook verification (`notes/playbook/playbook-verification.md`; PH §4.2, 17 rows) still applies to the new copy line for line. Still present:
- "S2 … currently fails (7/10)" (l.255). Ours: S1 6/8, S2 5/10, S3 8/10, all failing by construction (PV row 4).
- "Traces have no durable exporter here" (l.278). False: the gateway's spans sit in `aws/spans` for 30 days (PV row 3).
- "use the scenario switch to produce a passing run and a breaching run on demand" (l.280; PV row 5).
- "unauthorized tool → Cedar deny" and "tampered ledger record → ledger verification fails" (l.319–320, 461; PV rows 1–2).
- "capture the ledger's own verification output" (l.422; PV row 2).
- "Assemble everything the evening before" (l.140, 494, 572): a heuristic, not a judging rule.

The SN handoff still carries the 10,000-token example cap and one C9 incident per crossing window (row 6). The new L3 wording itself overclaims (R-5).

---

## 3. The gap lists compared (Arth's `evidence-pack/gap-list.md` vs our `gap-list.md`)

**How they fit together.**
- Arth's file is the skeleton of the merged artefact: section A has his 18 ServiceNow and platform entries; section B has 8 prompts for us.
- Ours has 11 AWS and platform entries. The design gaps in A §15.2 are also meant to go into it.
- Formats: ours uses the kit's four headings (What's missing / Why / Impact / If you had one more day); Arth's adds "Affects" and "Status". Keep each section's own format.

**Overlaps:**

| Arth | Ours | Note |
|---|---|---|
| A1: AICT's discovery scope (no EKS pods, MCP servers, guardrails, or which ModelConfig served a call) | A §15.2's AICT rows; gap 2 (one principal) | Keep A1, and correct its "one gateway IAM principal" (R-18) |
| A3: AICT Monitor shows no AWS traces | A §15.2: "AICT's usage count is 0; Monitor covers Managed agents only" [08 AI-03] | Ours names the cause: AICT's query filters `eventName = "InvokeAgent"`, while our traffic is `InvokeAgentRuntime`, and Monitor covers Managed agents only. Merge it into A3 (R-18) |
| A7/A8: delivered ≠ read; itil can't read journal rows | A §3.8, accepted adapter risk (b); [08 SN-05] | Same fact. 08 adds the consequence: a false NO_RESPONSE_OBSERVED when anyone updates the incident after the owner |
| A17: movement depends on the trace the evaluator attaches | Gap 7 (RECONSTRUCT); gap 2 (spans carry no agent identity) | A17 inherits our gaps: the trace is our testimony unless it is built from `aws/spans` plus our own records |
| A6: a reply isn't required; silence is recorded | A §15.1, out of scope (a human actually answering) | Same rule |

**Contradictions:**
- **B1's prompt ("no durable exporter?") is false** and must not become a gap [PV row 3; mem].
- **B3's prompt ("post-run instead of inline admission?")** is true only if EP-1 is cut (the A §12.4 P0 fallback). Otherwise we have an inline check. Write it only if that cut line is taken.
- **B4's prompt ("hourly closed windows; a missing hour is a monitoring gap")** depends on C-2. Under D3 the windows are per run, and an idle hour reads UNKNOWN without raising a finding [08 SN-08].
- **"Ledger-recorded"** in A10, the README and the diagram (R-4).
- **A3's "Next: … trace export to the connector's log group".** That group, `/aws/bedrock/aict-invocations`, belongs to the facilitators' connector, and the runtime role can write only to `/aws/bedrock-agentcore/*` [mem] (R-18).
- **Separation of duties.** Arth's list doesn't mention it. Ours (A §15.2) records that the owner also builds, while Arth's README claims the opposite (C-5).

**Gaps Arth has that we lack (adopt them):**
- A2: AICT freshness (Execute Now before the demo).
- A4: the shared instance, with identically named agents across teams.
- A5: Basic auth replaced by OAuth, which needed a **Global property changed on a shared instance**.
- A9: the Nemotron ruling moved L3 onto AWS.
- A11: notes are authored by the integration user.
- A12: model variance gives REFUSED.
- A13: forged notes, with the delivery log as the trust anchor.
- A14: the display time zone. The INC0010232 note shows 15:25:18 for 22:25:21Z.
- A15: shown vs proven.
- A16: the test incidents.
- A18: P5 stays pending until the cutoff.

**Gaps we have that Arth's list lacks (they become section B):**
- Our 1–11: judgment, WHO, WHAT, AUTHORIZED, APPROVED, INTEGRITY, RECONSTRUCT, the runaway, data and TLS, the twin, and tool code.
- The A §15.2 design gaps:
  - separation of duties;
  - the EU AI Act tier, UNVERIFIED (OC-21);
  - AICT's "Approved" being an editable status;
  - others' admission decisions being invisible;
  - C9's per-run attribution limits;
  - the inline tally trusting the run envelope (ADV-R-06);
  - the live inline bonus.

**New entries this vetting suggests:**
- **Adapter bug (a):** `notify --dry-run` on an existing incident still logs DELIVERED and makes live reads (handoff-3 `notifier.py:134–136`) [08 SN-06].
- **No CID on the Assurance Agent's gateway calls:** they join platform records by action id only (R-4, R-8).
- **The trace cap:** a trace longer than 200 steps can't ride on a finding (R-20).

---

## 4. Evidence-pack details

### 4.1 `run-ids.txt`

**What's in it.** 10 lines of UTF-8, and no real run id yet.
- Lines 1–4 are comments:
  - "`# Named runs for judging. Written BEFORE judging; never edited afterwards (append a dated correction instead).`";
  - a "Written at (UTC) … Register version in force" line;
  - a bare `#`;
  - a column header.
- Six placeholder rows: `C16 PASS`, `C16 BREACH`, `C7 PASS`, `C7 BREACH`, `C9 PASS`, `C9 BREACH`.
  - Each has `<run id>` (or `<window id>` for C9) and `<start> .. <end>`.
  - The notes column holds text such as `<e.g. 10,800 tokens, INC…>`, with a Unicode ellipsis.

**Is it in the kit format?** No.
- The kit's `submit.sh:23` asks for "one run id per line: the two named runs the brief asks for, one passing and one breaching".
- Arth's lines start with the control and the expected result. Ours (A §5.5) do too, and 04b B14 already flagged it: "put the CID first".
- No kit tool parses the file: `submit.sh` only copies it, and `evaluate.py` takes the run id as an argument. So the risk is a judge's one-line loop, not a tool failure.
- Resolution: C-8a.

### 4.2 `tools/manifest.py` and `test_manifest.py`

**The tool.** 78 lines, standard library only, Python 3.9+.
- `build <dir>` writes `MANIFEST.json`:
  - `schema: ifabric.evidence-manifest/v1`, `generated_at` and `algorithm: sha256`;
  - per file: `path`, `sha256` and `bytes`;
  - paths sorted and POSIX-style; symlinks skipped; MANIFEST.json itself excluded.
- `verify <dir>` reports `changed`, `missing` and `unlisted` files and exits 0 or 1 (2 on bad usage).

**The test file.** 5 tests:
- every file is listed with its hash and size;
- the manifest never lists itself;
- an untouched pack verifies;
- changed, missing and unlisted files are each reported;
- the CLI exit codes.

They were not re-run here.

**Verified:** the handoff package itself verifies with this tool.

**Limits** (Arth states them too):
- It is a checksum list, not a signature.
- It proves "unchanged since the build", so the README must not change after the build (C-8b), and `verify` must run on the downloaded copy (step 6).

### 4.3 `servicenow/` and the wiring tests: what INC0010231 and INC0010232 prove

**INC0010231: the "adapter wiring test".** Created 2026-10-05 06:53:23 UTC by `ifabric.integration`.
- **It proves:**
  - create → read back with the right correlation id and assignee → `DELIVERED`;
  - a second notify reuses the incident (`reused: true`), with no duplicate;
  - `check` reads `AWAITING_RESPONSE`, then `RESPONDED` (actor `annapurna@invences.com`, `at_basis: last_update`) after the owner updated it at 06:59:29.
- **It also shows:**
  - the first attempt `FAILED` (`CERTIFICATE_VERIFY_FAILED`, a python.org TLS store), and the failure was logged rather than hidden;
  - the export has `journal: []` with `journal_error: null`. The itil ACL hides journal rows silently: the behaviour behind 08's bug (b).
- **It doesn't prove:**
  - a control result (verdict INDETERMINATE, version TEST, evidence `test:no-evidence`);
  - journal reads;
  - the later "full finding block in the description" (its description still says "Evidence references are in the work notes").

**INC0010232.** Created 08:51:11 UTC and used for two TEST runs.

*The superseded ServiceNow-native prototype* (08:54Z, on the ServiceNow LLM; deactivated at 16:30:35 instance time). It used a read-only tool and was correct on every field. It is history only.

*The Assurance Agent round-trip* (22:25:15–22:25:25Z, by `sn_roundtrip_test.py`).
- **What happened:** `DELIVERED (reused)` → `ANALYSIS_WRITTEN` (`note_digest b44ea3c5…`) → on a re-run, `ANALYSIS_SKIPPED` ("analysis already present") → `AWAITING_RESPONSE` (cutoff 2099).
- **What was kept:**
  - the run record: the facts, the exact note and the attempt hashes, with no reasoning;
  - a screenshot of the note on the incident.
- **It proves:**
  - the write path: one work note, PATCHed as the integration user;
  - the note reads back unchanged (the digests match, through the display value);
  - the re-run skips (idempotent);
  - the parser works on a real note;
  - the five sections are computed: policy 6/8, with P1 and P5 unknown;
  - outcome validation fails V6 for a call that wasn't governed, as it should.
- **It doesn't prove:**
  - the Nemotron call (`backend: test:stand-in`, `model_alias: none`, `action_ids: [null]`);
  - the guardrail path, the AgentCore runtime or AICT discovery;
  - anything about a real finding.
- **It also illustrates two of our points:**
  - A14: the note shows 15:25:18 local display time for 22:25:21Z;
  - C-4: its hand-made trace has `modaas-agw` "return path" steps between the network and customer agents, with refs `test:gateway-action-none`.

**Where they go.** Both incidents' records stay TEST-ONLY in `evidence/servicenow/wiring-tests/`, out of the production log. Arth closes both ("adapter wiring test") once the first live Nemotron run has used INC0010232.

---

## 5. The pitch against the judging rules

Sources: PH §2.1–§2.5.

| Rule | `running-order-15min.md` | `pitch-L2-L3-script.md` | `backup-demo-shot-list.md` | `JUDGING-DAY-GUIDE.html` (the base) |
|---|---|---|---|---|
| A 15-minute slot ("15 minutes live with the judges") | Yes: 0:00–15:00, with questions inside the gap-list slot | Yes: about 4 of the 15 minutes | Yes: 3–5 minutes of video | Yes: 0:00–14:00 plus 1 minute of questions |
| L1 → L2 → L3 in order; L1 or "will not be judged" | Yes: 1:00 L1, 3:30 L2, 5:00 L3 | Yes: L2, then L3 | Partly: AICT (L2) comes as segment 6, after the L3 segments. Reorder it | Yes: 1:00 L1, 3:00 L2, 4:30 L3 |
| "We name one control and one window … Two minutes" | Yes: 7:30–11:30 "judges ask" (its example is a run, not a window) | — | Segment 7 | Yes: 7:00–10:30, including a window example for C9 only. C16 and C7 window answers need `assess_window` [04b A1] |
| "We type the question; you do not narrate the answer" | Yes: "the tool answers, nobody narrates" | Partly: L2/L3 context may be spoken, but step 6 is a ~110-word narration. Cut it to one sentence per screen, as the guide does | Yes: captions only | Yes: "show one screen and say one short sentence"; "say nothing until the answer is on screen" |
| No slides ("A slide deck. A whiteboard and a working tool beat both") | Yes | Yes | Yes | Mostly: the "▶ Present" mode, with step cards and a timer, can read as slides. Show the tool's own screens only |
| Bonus: "An inline decision, live … not replayed afterwards" | No slot (C-6) | — | A recording can't earn it | No: "Live · Replay (FM-D)" (C-6) |
| Bonus: a second EP, "the same architecture, moved, with nothing rewritten" | No: it claims the ServiceNow queue (C-1) | No: "The ServiceNow human queue is our second enforcement point" (C-1) | — | Yes: step 7, "the same rule-checker used in two places, with only the connector changed", which is D6 |
| "Rehearse it twice"; run ids "written down before we arrive" | Yes: printed run ids | — | — | Yes |
| Honesty: one honest failure; gaps read out | Yes | Yes (gap A3 answers) | Yes (a REFUSED or forged-note case) | Yes |
| Claims match our design | — | No: the movement narration (C-4) | — | No: "Nobody checks their own work: Sree approves, the builder builds, Arth tests" (C-5) |

**Verdict.** Adopt the guide as the run-of-show. It already follows "we ask, you operate" and the second-EP framing. Fix it for C-3 (its screens), C-4, C-5 and C-6. Retire the running order, and keep the L2/L3 script's Q&A table.

---

## 6. Thresholds against our registry design

### 6.1 Element by element

| Element of our design [A §3.3, §3.9, §12.1] | Arth's template and workflow | Merge |
|---|---|---|
| A kit-compatible flat file (A §3.3 rules 1–7; the kit-parity test) | Nested `justification:`/`governance:` maps; `control_id: ACN-COST-001`; a `claim:` map with a `>-` block. The kit's fallback parser finds 0 controls; under PyYAML they are keyed by library id | **Ours (R-1)**, with Arth's content |
| **Per-control versioning** [A §3.3 E-05/A2]: file `version` + `version_date`; each control's own `threshold_version` + `version_date` (e.g. `C16-v1`, `C9-v1.1`); quoted full UTC timestamps | Top-level `register_version`; a per-control `version` + `version_date` ("bump its version (G-FM-v1 -> G-FM-v2)"); dates as `YYYY-MM-DD` | **Already aligned in substance.** Use our key names, because `finding.py` calls the field `threshold_version`. Arth's P2 reads only `[:10]`, so full UTC times are compatible |
| **Date proof: T1 alone** (a write-once S3 object; AWS-set LastModified and VersionId), with T2 (ServiceNow) as corroboration [A §3.3 E-04] | The ServiceNow note is the proof: "A ServiceNow incident with Sree's dated work note gives a timestamp and identity that a stranger can check". There is no S3 step | **Add T1 before T2** (§6.2, step 4). Arth's flow stays T2 |
| **The risk register** `risks.yaml`, frozen with the register: one version, one T1 per file, and one T2 naming both sha256s; a `risk_ref` on every control [A §3.9] | None; only a per-control `governance.risk` sentence | **Add** `risks.yaml` and `risk_ref`. Keep the `risk` sentence as a flat key |
| **Frozen before assessed runs**: the hard line at 03:30–04:00 UTC [A §12.1] | "Hard gate … No assessed run before this"; `status: FROZEN` and `frozen_at`, set before hashing | **Same rule.** Adopt Arth's `status` and `frozen_at` as top-level keys (quoted UTC) |
| The four answers per threshold [slides p10] | `why_this_metric`, `why_this_value`, `how_measured`, `when_it_stops_holding` (nested) | Flatten them, and pick one name set in W0. Ours (`why_metric`, `why_value`, `measured_on`, `stops_holding_when`) already appears in A §3.3; Arth's descriptions become the template's comments |
| Data rules (missing → INDETERMINATE; late, duplicate, invalid) | Partly, inside `when_it_stops_holding` | Keep our four data-rule keys |
| C16 extras: tiers, `inline_modes`, `safety_ceiling`, the bound policy, declared conditions | None (`enforcement_point` placeholder: "modaas-agw … (EP1); post-run evaluator if not inline") | **Ours.** The enforcement point is EP-1 in our runtime, with EP-2 (`aws/spans`) as the floor; the gateway has no per-run cap [gap 8] (C-1 wording) |
| C7 and C9 extras (workflow events, declared faults, baseline procedure, treatments, warm-up) | Placeholders; C9 "per closed UTC hour" | **Ours**, subject to C-2 |
| Owner and builder | `owner: annapurna@invences.com`; `builder: <teammate>`, "does not approve them" | Owner as given. The builder line follows C-5 |
| The approval text | "`APPROVED threshold register <register_version>, sha256 <first 12 hex>`" | Extend it to name both files: `…, sha256 <12 hex>; risks sha256 <12 hex>` |
| The approval mechanism | A Finding (`REG`, `ESCALATED`, `kind: approval`) with its own delivery log | C-7 (recommended: adopt) |
| Retention | "Evidence is kept for 7 years from the submission date" | Adopt it as a top-level key |
| The claim | Nested `claim: id/text >-`, in the playbook's wording | Flatten to one-line `claim_id` and `claim_text`, verbatim from the slides (R-21) |
| No threshold number in code | Rule 5 of its HOW TO USE | Same rule |

### 6.2 The merged freeze-and-approve sequence (Arth's 9 steps plus ours)

1. **Pilots and draft.** Pilots (provenance PILOT/EXPLORATORY), then fill the merged `register.yaml` and `risks.yaml` as DRAFT [Arth 1; A §5.4].
2. **Review.** Arth reviews against Playbook §3.1 and our schema rules; the kit-parity test is green [Arth 2].
3. **Freeze.** Set `status: FROZEN` and `frozen_at`, then `prooflab registry freeze --version v1`. That writes `register/versions/v1.yaml` and `v1.risks.yaml`, each with its `.sha256` [Arth 3; A §3.3 step 1].
4. **T1, in S3.**
   - PUT `ifabric/register/v1.yaml` and `ifabric/register/v1.risks.yaml` with `--checksum-algorithm SHA256`.
   - Capture `head-object --checksum-mode ENABLED` into `evidence/register/v1.head.json`.
   - A person on the IDE runs `list-object-versions`, saved as `v1.versions.json` [A §3.3 steps 2–3]. The first PUT is spike S2 [06 D1].
5. **T2, the request.**
   - Fill `approval-finding.json`: both 12-hex prefixes in `summary`, and both full hashes in `evidence`.
   - Set `PROOFLAB_DELIVERY_LOG` to an **absolute** `…/evidence/register/approval/delivery-log.jsonl`.
   - Run `notify`: expect DELIVERED and an INC number.
   - Paste both files' text into the incident [Arth 3–5].
6. **Sree's note:** `APPROVED threshold register v1, sha256 <12 hex>; risks sha256 <12 hex>` [Arth 6].
7. **Capture it.** Arth runs `check` at once (expect RESPONDED), then `export` into `evidence/register/approval/`. Nobody else updates that incident afterwards (08's bug (b)) [Arth 7].
8. **Hand out.**
   - Copy the frozen file, unchanged, to WORKDIR's `register.yaml` and to `evidence/register/`.
   - Run `registry pin`, patch the env, and check the pin the agents echo back (EP-0) [Arth 8; A §3.3 steps 5–7].
9. **Only now, assessed runs.** `v1.1` repeats steps 3–8 for C9 only; C16 and C7 keep `C16-v1` and `C7-v1` with v1's dates [Arth 9; A §3.3].

---

## 7. Actions for the captain / teammate, with deadlines

**How to read this.**
- Times are UTC, with CDT in brackets, from the current A §12.1. 04b A8 expects the agent freeze to slip by 1.5–2.5 h, and if it does, every later row moves with it.
- Arth's relative deadlines map onto this clock as follows:
  - "today" means before 03:30;
  - "before any assessed run" means the 03:30–04:00 hard line;
  - "the evening before" means 08:15–10:00, the first submit;
  - "20 minutes before" means before the slot, at a time not yet known, after 15:00.
- Sree's acts are included, because she is the captain.

| # | Action | From | Deadline UTC (CDT) | Notes |
|---|---|---|---|---|
| 1 | Answer C-1…C-8 (§9), at least C-7 (the T2 mechanism) | This file; [08 SN-09] | **01:00 (20:00)** for C-7; C-2, C-3 and C-4 now, because they change W5, W7 and W9 | The recommendations stand as defaults until answered |
| 2 | Merge Arth's code: `code/prooflab/servicenow/` and `tests/` over `prooflab/` | TEAMMATE A.1; handoff README §3.1 | By **01:00 (20:00)**, before W9's glue | Our copy is the older package with no local edits (checked), so nothing is lost. Run the tests in the 3.9 venv [08 PY-02]: expect **152 passed**. Git is the lead's call |
| 3 | Tell Arth (no secret values): the gateway URL our agents use, the approved alias (`nemotron-super-120b`), and **"API key: yes, required"** | TEAMMATE A.2 | **Now** | Authz is FailClosed [mem] (R-7) |
| 4 | Put the ServiceNow credentials on the laptop (`~/.prooflab-snow.env`, mode 600, an absolute `PROOFLAB_DELIVERY_LOG`) and run `selftest` | TEAMMATE A.1; [08 SN-02] | **03:30 (22:30)** | Check your own vault first (Sree holds them [08 SN-02]); otherwise Arth |
| 5 | The first live Assurance Agent run (spec 08 §5.2): TEST log, `notify --dry-run`, then `analyze` on INC0010232 | TEAMMATE A.3 | Right after row 4; before the first real `notify` at **~04:30 (23:30)** | Run it on the laptop (D11) or in the IDE; both reach ServiceNow and the gateway. Add `MODAAS_API_KEY`, held in memory only (§5.2 leaves it out), and an absolute TEST-log path. It is a ServiceNow write plus a few thousand tokens, so it needs the user's OK. Send Arth the JSON and the run record. On UNVERIFIED, don't re-run: `export` and send that instead |
| 6 | Sree approves the three `ifabric-` CRs (the annotation; the deploy wrapper records her words and the time) | A §7.1; [05 AR-07] | **00:30–02:00 (19:30–21:00)** | Self-asserted (gap 5) |
| 7 | Deploy `ifabric-assurance-agent` on AgentCore through our bundle path (R-6); Sree approves its CR; switch the backend to `CallableAnalyzer` with a distinct CID (R-8) | TEAMMATE D.9; Arth action 3 | Best **02:00–04:00 (21:00–23:00)**, so that N2's analysis runs on `agentcore:`. At the latest **~08:45 (03:45)**, at least 45 min before Arth's 09:30 export: AICT's 15-min import plus about 4 min of run time [gap A2; 08 AI-02], then his export | If skipped, gap A10 states it, and the `gateway` backend stays honest |
| 8 | Pilots → fill the merged `register.yaml` and `risks.yaml`, with four answers per control | TEAMMATE B.5; [A §5.4] | **02:00–03:30 (21:00–22:30)** | §6 |
| 9 | Freeze `v1` → T1 in S3 → Arth's approval incident → **Sree's APPROVED note** → `check` and `export` → copy unchanged | TEAMMATE B.6; threshold-approval; [A §3.3] | **03:30–04:00 (22:30–23:00): the hard line** | §6.2. A person on the IDE runs the version listing. No assessed run before T1 |
| 10 | Refresh the AWS credentials | [08 OP-01] | Between **03:30 and 06:29:19 (22:30–01:29)** | The current key expires at 06:29:19Z |
| 11 | Attach the finding context (`measured`, `limit`, `register` with `version_date` from T1, the owner and the approval INC, a `trace` per C-4 of at most 200 steps, and `retest` on a re-test) before every `notify` | TEAMMATE Phase C; spec 08 §5.0 | Before the first named-run finding, N2, at **~04:30 (23:30)** | R-13, R-20 |
| 12 | Named runs per A §12.1; on every BREACH or ESC finding: `notify` → `run_assurance_agent` → a `check` loop; a run-ids row as each run completes | TEAMMATE C.7 | C16 **04:00–05:00**; C7 and ESC **05:00–05:40**; baseline and `v1.1` **05:40–06:30**; C9 **06:30–07:20** | C-2 decides C9's shape |
| 13 | `v1.1`: T1, then **Sree's approval** (C9 only) | [08 HL-02] | **~06:30 (01:30)** | §6.2, step 9 |
| 14 | The adversarial log, including Arth's Assurance Agent cases (an injected ticket → REFUSED; a guardrail → BLOCKED) | TEAMMATE C.8 | **07:20–08:15 (02:20–03:15)** | An injected ticket is a new incident: a ServiceNow write, with the user's OK |
| 15 | Owner responses, optional (Sree): a note counts as a response; nobody else updates our incidents after it | spec 08; [08 SN-05] | Before the stated cutoff | Bug (b) masks a response once someone else updates the incident |
| 16 | Final re-snapshot → final `check` → `export` every finding → `case --out` every named run → build `evidence/` (Arth's tree plus ours, WORKDIR copies, redaction and the exact-value scan) → MANIFEST → `submit.sh` → readback and `verify` → the submission record (C-8b). Merge the gap list (A + B), the decisions log, and the sketch with the ServiceNow section | PRESENTATION §3; TEAMMATE G.12–13 | Snapshot **08:15–08:30**; first submit **08:30–10:00 (03:30–05:00)** | Arth's "evening before" maps here |
| 17 | Collect from Arth: `servicenow/aict/`, `register/approval*`, the INC numbers, section A's statuses, the Assurance Agent's adversarial cases; then Arth's review sign-off | PRESENTATION §3 steps 2 and 5 | **09:30 (04:30)** for AICT [08 AI-04]; sign-off before the final submit | C-8c |
| 18 | Two rehearsals, with an outsider asking the guide's questions | TEAMMATE H.14; PH §2.4 | **10:00–12:30 (05:00–07:30)** | — |
| 19 | The final `check` against the stated cutoff (R-19), then re-export. Arth closes INC0010231 and INC0010232 | [08 SN-05]; Arth action 5 | **12:00 (07:00)** | Silence is recorded only once now ≥ the cutoff |
| 20 | Final submit and readback; no edits after it | PRESENTATION §3 steps 6–7 | **12:30–13:00 (07:30–08:00)** | — |
| 21 | If C-6 is "live": AWS credentials valid through the slot (one more refresh if the slot ends after the row-10 key expires) | [08 OP-02] | Before the slot | — |
| 22 | On the day: Arth presses AICT **Execute Now**; open the downloaded pack copy; close every tab that shows a token; print the run ids and the sketch; the captain drives "judges ask" | PRESENTATION §4; the guide | **~20 min before the slot** (the slot comes after 15:00 UTC, time unknown) | — |

**Asks to send Arth now**, with when each is needed:
- **Confirm, now:**
  - `my_agent` is visible in AICT [08 AI-02];
  - the integration user, the OAuth app and the Global property are still active, and the courtesy note to the facilitators is sent [08 SN-03];
  - his hours for 03:30–04:00, ~06:30, 08:30–10:00 and 09:30 UTC (C-8c).
- **The OAuth id and secret, privately,** if Sree's vault doesn't have them: by 03:30.
- **Agreement on C-1, C-4, C-5 and C-7** (his texts change), and the two-line M1 label change (C-4): by 01:00.
- **The AICT `Managed by` and `Risk classification` mirror (D14, OC-23),** only if the captain chooses it: before the AICT export.
- **Close INC0010231 and INC0010232** after row 5, before judging.

**Arth's own six actions** (deliverables README), mapped to the clock:
1. The round-trip: done.
2. The facilitator note: now.
3. The register review, Sree's approval and the Assurance Agent's CR: 03:30–04:00, and row 7.
4. Confirm the parser against the first real note: after row 5. Then update A3, A10 and A15–A18: by the pack build.
5. AICT evidence: by 09:30. Close the two test incidents: before judging.
6. Review the pack: 08:30–10:00. Then present L2 and L3.

---

## 8. Adopt into our deliverables

### 8.1 As the base, unchanged

**Code** (Artefact 3's human loop):
- Arth's `prooflab/servicenow` and its 152 tests: the Finding contract, `notify`/`check`/`export`, the Assurance Agent, `case_view`, the drop-in panel and the examples.
- The finding-context contract (spec 08 §5.0) is the interface our `publish()` writes to.
- P6's `retest` key closes a finding only with a SATISFIED re-test at the same threshold version.

**Integrity tool:** `tools/manifest.py`.

**Evidence Pack** (Artefact 1):
- The README skeleton: §2 retention (7 years), §7–§9 and §11 test-only.
- The `servicenow/` folder layout (`delivery-log.jsonl`, `incidents/`, `assurance-agent/`, `cases/`, `aict/`, and `wiring-tests/` copied as-is).
- The `decisions-log.md` format.

**Gap list** (Artefact 6): section A (A1–A18) and the five-part entry format.

**Threshold document** (Artefact 2):
- The workflow in `threshold-approval.md` and `approval-finding.template.json` (C-7 recommends adopting them).
- `register.template.yaml`'s content: the claim, owner, retention, per-control versions, four answers and governance tree.

**Sketch** (Artefact 5): the content of `servicenow-section.md`, renumbered per C-1.

**Pitch:**
- The judging-day guide as the run-of-show, with its phrases and its "if the judges ask" list.
- The Q&A table of `pitch-L2-L3-script.md`.
- `backup-demo-shot-list.md`.
- The step order of PRESENTATION_DAY_INTEGRATION §3 and its §5 checklist.

**Rules:**
- No secrets anywhere.
- Wiring and exploratory data never go into assessed results.
- Never run `analyze` on the approval incident.
- Close a finding only with a linked passing re-test.
- A note counts as the agent's only if its digest is in the delivery log; a logged RESPONDED stays RESPONDED.
- Execute Now about 20 minutes before; rehearse twice with an outsider.

### 8.2 With required corrections (a verified fact or the kit decides; no decision needed)

**R-1 · The register template is not kit-compatible.** The kit's fallback parser reads 0 controls, and PyYAML keys them by library id (checked in memory).
- Fix it to A §3.3 rules 1–7:
  - each entry starts with `- control_id: "16"` (then `"7"`, `"9"`), with `control_ref: C16` and `library_id: ACN-COST-001`;
  - flatten `justification:` and `governance:`, and make `claim` one line;
  - no block values; quoted UTC timestamps; no `#` in values; nothing after the last control.
- Then add our extended keys and `risk_ref`.

**R-2 · The ledger "verification output".** README §3 item 3 and §6: "Ledger integrity: `raw/ledger/verify-<date>.txt` (the audit store's own verification output)". But "The ledger service has no verify route: `audit-store.py` GET routes are only `/healthz`, `/records`, `/timeline`, plus the write" [mem; gap 6; PV row 2].
- Replace it with the corroboration report (`derived/corroboration/<CID>.json`), the MANIFEST, and the times AWS and ServiceNow set [A §9.2].

**R-3 · README §6's six-question table claims too much.**
- WHO, "gateway caller identity in `raw/gateway/`": every call is `ServiceIdentity::"bootstrap-key"`, gateway lines carry no agent identity, and the principal sits in `/modaas/evidence` [gap 2; mem].
- AUTHORIZED: the PDP and `/modaas/evidence` record guardrail blocks and pauses as ALLOW [gap 4]. Outside the agent, only the AWS model-call record in `aict-invocations` names a block (`guardrailTrace.actionReason = "Guardrail blocked."`), and it carries no run id, so it joins by time and model [mem].
- APPROVED: approvals are self-asserted, with an empty signature [gap 5].
- Name each limit in the table, as A §10.3 does.
- Note for the lead: the `aict-invocations` fact also refines our own gap 4, which still says "No record anywhere says a guardrail acted". Gap 4 should be updated; this file doesn't touch it.

**R-4 · "Ledger-recorded".** It appears in the diagram ("EP1 modaas-agw ─► Nemotron (governed, guardrail-checked, ledger-recorded)"), in README §8 ("joins to `raw/gateway/` and the ledger"), in gap A10, and in `nemotron.py`'s docstring.
- The audit ledger holds only records our code writes [A §3.5]. A direct gateway call is recorded by the platform in `aws/spans` and `/modaas/evidence`, keyed by action id.
- The Assurance Agent sends no baggage, so its calls' run id is their trace id [mem: "With no baggage CID, `modaas.run_id` = the trace id"].

**R-5 · "Its AICT trace".** The playbook's §3.10 and §4.1 L3 text promise one. Change it to "its AICT inventory entry".
- Gap A3: no traces from AWS runtimes reach AICT.
- Arth's own panel fix: "Step 5 reads 'AI Control Tower / AICT inventory entry', because it is an inventory link, not a trace (gap A3)".
- AICT's usage query filters `InvokeAgent`, and Monitor covers Managed agents only [08 AI-03].

**R-6 · The Assurance Agent deploy (spec 08 §5.3, via TEAMMATE Phase D).** It says "Create it with `new-agent.sh` (Strands template), name **`ifabric_assurance_agent`**".
- **The name.** CR names must match `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`, so use the CR `ifabric-assurance-agent`. AgentCore names the runtime `ifabric_assurance_agent-…` [05 AR-01].
- **The build path.** Never use `new-agent.sh`, which overwrites `agent.py` [05 AR-02; A §7.1].
- **One file.** The build ships one file, so the handler's `from prooflab.servicenow.nemotron import GatewayAnalyzer` dies with an ImportError at the first invocation unless it is bundled. Bundle it with `tools/bundle_agent.py`, under the 24,049-character cap [05 AR-03].
- **The tag.** The source must not be named `agent.py`, and every build needs a unique `IMAGE_TAG` [05 AR-05].
- **The approval.** Sree annotates; the generator's `approve=True` path is never used [05 AR-07].

**R-7 · The gateway key.**
- `MODAAS_API_KEY` is required, not "optional … if the gateway requires one": `modaas-authz` is "`failureMode: FailClosed`, on all listeners" [mem]. Spec 08 §5.2's exports leave it out.
- Inside the AgentCore runtime, use the operator-injected `OPENAI_API_KEY` and `OPENAI_BASE_URL` (reserved names [05 AR-14]). Never put a literal key in the AgentConfig env: "no AgentConfig CR … holds the gateway key" today [mem], and CR env is readable by every participant.

**R-8 · Never a run's CID on an Assurance Agent call.** Spec 08 §5.3 says to invoke the runtime with "your existing helper". Ours, `prooflab run`, passes the run's CID as baggage [A §7.2], and the runtime propagates it [05 AR-19].
- The Assurance Agent's Nemotron tokens would then land under that run's id in `aws/spans`, inside C16's figure of record.
- Invoke it with its own `ifabric-assure-<finding hash>` CID, or none.

**R-9 · The submission layout.**
- `submit.sh` takes `register.yaml`, `gap-list.md` and `run-ids.txt`, plus `sketch.png`/`.jpg`, from WORKDIR [`submit.sh:62–79`].
- Keep byte-identical copies there as well as under Arth's `evidence/` tree.
- The sketch must be an image; `architecture.md` alone is reported "MISSING".

**R-10 · `raw/cr-status/`.** Take it only from our redacting collector, never from the kit's `pull-evidence.sh`, which keeps three token paths per AgentConfig [06 D4]. Run the exact-value scan before `submit.sh` [A §9.3]. Arth's "never edited" rule then holds without any edit.

**R-11 · Absolute log paths.** `PROOFLAB_DELIVERY_LOG=evidence/register/approval/delivery-log.jsonl` and spec 08 §5.2's TEST log are relative paths; a relative path silently starts a second log [08 SN-07]. Make both absolute.

**R-12 · The two adapter bugs are still in handoff-3's code.**
- Bug (a): an existing incident returns `_confirm(...)` before `dry_run` is checked (`notifier.py:134–136`).
- Bug (b): `_actions` treats 0 journal rows as readable.
- Keep 08's guards: a TEST or scratch log for every dry run (spec 08 §5.2 already does this), and `check` plus `export` right after each owner note.
- Our `mirror()` applies Arth's sticky-RESPONDED rule, so a later NO_RESPONSE_OBSERVED line can't override a response.
- Add bug (a) to the gap list.

**R-13 · P2 compares days only.** "Threshold version dated before the test" is `reg.version_date[:10] <= finding.detected_at[:10]` (`assurance_checks.py:102`).
- Feed `register.version_date` from T1's LastModified.
- Our control test's check, T1 against the run's first span and its `@ingestionTime`, stays the authority [A §3.3].

**R-14 · The inventory and the plan.**
- Add `ifabric-assurance-agent` as a component in `inventory.yaml`, with its owner (C-5) and approved version. The scope rule puts every `ifabric_*` asset in scope, so INV and EP-0 would otherwise flag it.
- Replace "Arth's ServiceNow-native agent" in A §3.10, which is superseded.
- Budget its calls in A §12.3: up to 2 attempts of a few thousand tokens per finding (an estimate, not measured).

**R-15 · The `cases/` name clash.** Our top-level `cases/` holds rendered control cases [A §9.1]; Arth's `servicenow/cases/` holds the case JSON. Rename ours, e.g. `answers/`.

**R-16 · The playbook corrections still apply.** The handoff-3 playbook keeps "7/10", "no durable exporter", "scenario switch", "Cedar deny", "ledger verification fails" and "capture the ledger's own verification output", and the SN handoff keeps the 10,000-token examples (§2). Use `notes/playbook/playbook-verification.md` alongside the new copy.

**R-17 · Section B's prompts.**
- B1 (no durable exporter) is false: drop it.
- B3 applies only if the EP-1 cut line is taken.
- B4 follows C-2.

**R-18 · Section A's wording.**
- A1's "one gateway IAM principal" → one API-key principal, `ServiceIdentity::"bootstrap-key"`.
- A3's cause: AICT's query filters `InvokeAgent`, and Monitor covers Managed agents only [08 AI-03].
- A3's next step: drop "trace export to the connector's log group", which is the facilitators' group.

**R-19 · The cutoff.** `check` records silence only once now ≥ the cutoff (`notifier.py`, `check_response`). A §3.8 says "`check --cutoff <judging start>`", while A §12.1 runs the check at 12:00 UTC: that combination never records silence.
- State a cutoff no later than the final check (e.g. 12:00 UTC) in the incidents and the README.

**R-20 · The trace cap.** `finding_context.py:98–99` raises "trace may hold at most 200 steps" rather than truncating. A long BREACH run would then fail validation before `notify`, and no incident would be raised (the reference S2 had 353 gateway spans).
- Summarise the trace to ≤ 200 steps, for example one step per agent invocation with its call count, and keep the full trail in the pack.

**R-21 · The claim wording.**
- Arth (README §1 and the template) uses the playbook's: "During **customer** fault resolution … event-recording, drift **and performance**, and token-spend requirements".
- Use the slides' verbatim claim, as A §1.2 does: "During fault resolution, the three collaborating agents meet our declared event-recording, drift and token-spend requirements".

### 8.3 Where this lands in our architecture

- **§3.0:** `servicenow/` grows to Arth's v3 modules.
- **§3.1:**
  - EP-13 stays the human queue;
  - add an EP row for the Assurance Agent's write guard. It refuses invalid notes and sits off the fault path; spec 08 §5.4 calls it "our second enforcement point" (C-1);
  - the Assurance Agent becomes the 4th build (A §7.1 already flags it, line "A 4th agent … is pending integration").
- **§3.3:** answer the T2 mechanism (C-7) and record the approval-incident handling.
- **§3.8:**
  - fix "`notify()` = `callback()`" to match §3.2's notify-then-poll (C-1);
  - `publish()` attaches the finding context;
  - wire `run_assurance_agent()` and `case --out`;
  - `mirror()` also carries the `ANALYSIS_*` states and applies the sticky-RESPONDED rule.
- **§3.10:** the Assurance Agent as a component (R-14).
- **§9.1:** the merged tree (R-9, R-15).
- **§12:**
  - new live-lane steps: the Assurance Agent proof (row 5), its deploy (row 7), and Arth's review and AICT windows;
  - W9 grows: finding context, Assurance Agent wiring, case snapshots;
  - W2 grows: the Assurance Agent bundle.
- **§13:** D5 (C-7) and new rows for C-1…C-6.
- **§15.2:** bug (a), and the CID-less Assurance Agent calls.

---

## 9. Conflicts to resolve (genuine decisions)

### C-1 · Which "second enforcement point" we claim, and one EP numbering

**Arth says three different things:**
- `servicenow-section.md`: "**Second enforcement point (EP2): the ServiceNow human queue.** (In the Evidence Console's EP table this is **EP4**; EP2 there is the C16 agent-adapter admission.)" Its diagram reads "agents ─► EP1 modaas-agw", and its transport table says "`callback` | none (the owner's response is not pushed to us)".
- The running order and L2/L3 script: "The ServiceNow human queue is our second enforcement point".
- Spec 08 §5.4 titles the Assurance Agent's write guard "our second enforcement point".

**The guide, meanwhile**, says (step 7): "the same rule-checker used in two places, with only the connector changed".

**We say:**
- D6: "EP-1 + EP-2, one c16 module" [A §11.1].
- EP-13, ServiceNow: "records only; never holds work, and is not claimed as a refusing EP" [A §3.1].
- `callback()` "is realised as notify-then-poll: … the poller (`check --cutoff` …) calls callback() once per new response" [A §3.2]. Our own A §3.8 still says "`notify()` = `callback()`", which is stale.

**Why it matters.**
- Judges ask "Would it survive a second enforcement point?" and score "the same architecture, moved, with nothing rewritten".
- A human queue that refuses nothing doesn't move the evaluator.
- Three numberings (Arth's EP1/EP2, the console's EP4, our EP-1…EP-13) on the sketch, the pitch and the query tool would confuse a judge.

**Options:**
- (a) D6 is the claim. ServiceNow is presented as the slide-14 kind "human approval queue" (callback, refuses nothing), answering "if I move it to a human queue". The Assurance Agent's guard becomes its own EP row. Our numbering is used everywhere, with Arth's section and the console's table renumbered.
- (b) Arth's claim: ServiceNow is the second EP.

**Recommendation:** (a). It is what the guide's step 7 already says. Transport wording for the sketch:
- `notify` = an outbound emit of the finding;
- the owner's response reaches `callback()` through the `check` poll;
- `export` and the AICT import = `pull`.

**Decide by:** now; Arth's section and the sketch depend on it. At the latest, before the first submit at 08:30.

### C-2 · C9: closed-hour windows now, or per-run windows on the frozen agents (D3, pending)

**Arth says:**
- "**Start C9 baseline collection now:** it needs closed UTC hours" (TEAMMATE A.4; console 09 A0).
- "C9: one finding per crossing window; a missing window is a monitoring-gap finding" (TEAMMATE C.7).
- "Too many incidents for C9 | Expected: one per crossing window. Do not merge windows" (SN handoff l.491).
- `run-ids.txt` names "C9 PASS `<window id>`", and the guide answers "control 9 between 23:00Z and 09:00Z" with hourly bars.

**We say:**
- D3: "W2 per run + an hourly roll-up; baseline B-a (6 runs, `v1.1`)", frozen at 05:40–06:30 UTC [A §5.3, §12.1].
- "one finding per control × run scope … This bounds C9 to the number of runs, not hours × runtimes" [A §3.8].
- 08 SN-08: per-hour × per-runtime windows would give "up to about 30 findings, mostly idle-hour gaps", and "Never notify a monitoring gap for an idle hour".

**Verified facts:**
- AgentCore datapoints exist only for minutes with invocations [05 AR-23]. So an hour with no runs has no data and reads UNKNOWN, and every baseline hour costs runs on the frozen version [PH §3a item 1].
- The `ifabric-` agents don't exist until about 02:00 UTC. A baseline started "now" could only measure the reference trio, which is never assessed (D7, D9).

**Options:**
- (a) Keep D3: named C9 runs N7, N8 and N9 with W2 windows, and the hourly view as a roll-up display, where idle hours read UNKNOWN without raising a finding.
- (b) Arth's: hourly windows as the assessed unit, with the baseline collected per closed hour after the freeze. Each baseline hour then costs runs, and the volume bound is lost.

**Recommendation:** (a). Arth's hourly display survives as the window answer.

**Decide by:** now; W5's c9, the pilots at 02:00 and the run-ids format depend on it.

### C-3 · The dashboard: our static page (D1) or Arth's Evidence Console (TEAMMATE Phase E)

**Arth says:**
- "One **read-only** backend endpoint returning `case_view()` JSON …, cached 10 s", done when "a new breach shows steps 1–3 within 10 s".
- The console plan is a stdlib server bound to `127.0.0.1:8787` with a session token and PACK mode, plus a static viewer copy.
- The guide's screens (Ask ⌘K, Agent Trail, Live · Replay, ▶ Present) are the console's.

**We say:** D1: "one static, self-contained HTML file is rendered from the snapshot; no server, no endpoint"; "A local `127.0.0.1` server (D1-C) is a cut-line extra only" (P5, cut first) [A §3.7, §12.4]. W7 has 4–6 agent-hours.

**What is and isn't at stake:**
- It is not a security conflict: loopback only, no public endpoint, and the server refuses to start with secrets in its env.
- It is a scope conflict. The console is a separate track with its own hour budgets (console 09), on top of our 39–51 agent-hours, and console 09 itself says "cut console scope, never control scope".

**Options:**
- (a) Keep D1, and embed Arth's drop-in panel (static JS and CSS reading the case JSONs from disk, Arth's own offline fallback) as the human-loop view. Map the guide's 8 steps onto the sketch, the terminal, our static views and the `prooflab query` CLI.
- (b) Build the console as the presenter's surface, with its static viewer replacing `dashboard.html`.
- (c) Do (a) for P0/P1, and add the console's P0 only after C16 is complete end to end, if the fleet has capacity.

**Recommendation:** (c).

**Decide by:** now; W7's scope.

### C-4 · What the agent-movement trace says about our handoffs (the M1/P8 route rule)

**Arth says:**
- "**Every gateway hop is its own step with `zone: "gateway"`.** A `network` step followed directly by a `customer` step fails the route rule (M1/P8)."
- The example trace has `{"actor": "modaas-agw", "zone": "gateway", "action": "return path"}` between the network and customer agents.
- The pitch: "customer agent, gateway, IT agent, gateway, network agent, gateway, back to the customer. Three gateway crossings".

**We say:**
- The script invokes the runtimes "through `InvokeAgentRuntime`, in sequence (customer → IT → network)", and "Agent-to-agent handoffs are record events" [A §7.2, §2.2].
- No handoff passes the gateway, and no step returns to the customer agent.
- Each agent crosses the gateway on each of its own model and tool calls (S1: 24 gateway calls).

**What the code does** (`assurance_checks.py:41–48`):
- M1 fails only on an adjacent network → customer pair; any step in between passes.
- Its pass text always reads "every network → customer movement crossed a gateway".
- A faithful trace of our runs therefore passes M1 vacuously, under a sentence that isn't true of them.

**Options:**
- (a) Emit orchestrator handoffs as steps with `zone: "other"` (actor `prooflab-run`, ref `handoff:<id>`), with the gateway steps summarised per agent invocation (R-20).
  - Ask Arth for a two-line label change, e.g. "no direct network → customer hop (every return passes a governed crossing)".
  - Reword the pitch: "every model and tool call crossed the gateway; every handoff is a recorded EP-5 event".
  - Caveat: the orchestrator then appears in the "agents" list. Label it.
- (b) Attach no trace: movement reads unknown and P8 unknown. Honest, but the weakest demo.
- (c) A gateway "return path" step: not acceptable, because none exists.

**Recommendation:** (a).

**Decide by:** 01:00 UTC, before W9 builds the finding context, and before N2 at ~04:30.

### C-5 · Separation of duties: what we may claim

**Arth says:**
- "Nobody approves their own work" (README §12).
- "Owner … One named person, not a team; owner ≠ builder" (decisions-log).
- `builder: "<teammate's name/email>"  # … does not approve them`, and "the builder never approves their own thresholds" (template).
- "Nobody checks their own work: Sree approves, the builder builds, Arth tests" (guide).

**We say:**
- "The user (Sree) builds the AWS side and is the control owner" (PH §1).
- "Separation of duties: the owner also builds, and also rates the risks she owns", recorded as a gap [A §15.2].
- 08 HL-04 proposes a roles table: Sree = accountable management + operations; Arth = assurance (a "reviewed" note on each T2 record **before** Sree approves, and an assurance check on each control result); GRC vacant.

**Why it matters.** As written, the pack and the pitch would state something the team knows is false. That costs more than the gap itself does.

**Recommendation:**
- Adopt 08 HL-04's roles table.
- Reword every claim to "nobody checks their own work alone: Arth reviews before Sree approves".
- Keep the gap entry.
- The template's `builder` line names the user and the AI fleet.

**Decide by:** 03:30 UTC, before the register text and the approval note are frozen.

### C-6 · The live inline bonus vs "Live · Replay"

**Arth says:** guide step 6, "Then the live replay: the budget check refuses the call that would overspend, before it happens" (screen "Live · Replay (FM-D)"). The running order has no slot for it.

**The brief** (PH §2.4): "An inline decision, live: show a verdict being formed in the path, not replayed afterwards".

**We say:** "`prooflab tail` on a live run while the account is up; otherwise the recorded N3 decision records, labelled 'recorded, not live'" [A §15.2, §10.4].

**Options:**
- (a) Run one `enforce`-mode run live in step 6, with `prooflab tail`.
  - About 0.06M tokens [A §12.3].
  - It needs the account up at the slot, and AWS credentials valid then (§7, row 21).
  - The recorded N3 is the labelled fallback.
- (b) Show the recorded N3, labelled "recorded, not live", and claim no bonus.

**Recommendation:** (a), with (b) ready.

**Decide by:** before the rehearsals at 10:00 UTC.

### C-7 · The register approval (T2) sent as a Finding (D5, pending)

**Arth says:** "A ServiceNow incident with Sree's dated work note gives a timestamp and identity that a stranger can check … It reuses our existing adapter: **no new code**." The incident is a Finding with `control_ref: REG`, `verdict: ESCALATED`, `kind: approval`, logged in its own delivery log.

**We say:** "It does **not** go through a Finding: that would put an approval into the verdict vocabulary as something it isn't" [A §3.3]. The mechanism was still "pending Arth; decide by 01:00 UTC" [08 SN-09], and T2 is a spike [07 GS-21].

**Assessment.** Arth's version is 08's option B with no new code, and it fits the 01:00 deadline. Our concern is met if the approval stays out of the verdict path:
- it has its own absolute delivery log;
- `kind: approval` maps to `record_kind: approval`;
- it is excluded from the findings lists, `esc_producer` and the claim roll-up;
- `analyze` is never run on it.

**Recommendation:** adopt it, with T1 first and both sha256s in Sree's note (§6.2). T2 stays corroboration [A §3.3 E-04]. Update A §3.3 and D5 to match: D5, as re-written at 19:06 CDT, still says "T2, the owner's ServiceNow approval record (not a Finding), corroborates".

**Decide by:** 01:00 UTC.

### C-8 · Three small decisions

**(a) The `run-ids.txt` format.**
- The kit: "one run id per line" [`submit.sh:23`].
- Arth's template and ours are control-first, and 04b B14 says to put the CID first.
- Options: (i) CID-first lines, `<CID> <control> <PASS|BREACH|RETEST> <window> <version> <mode> <condition> <INC>`, with no comment lines; (ii) bare CIDs, with the table in README §1.
- Recommendation: (i). Also upload the final file to a write-once key (`ifabric/run-ids/<UTC>.txt`), so S3 dates "written down before we arrive".
- Decide before the first named run, at 04:00 UTC.

**(b) Where the submission record lives.**
- Arth's step 6 records "keys, ETags and time in README §10" after upload, but step 7 says "No edits after upload", and an edited README fails `manifest.py verify`.
- Recommendation: a separate `ifabric/submission-record-<UTC>.json`, uploaded beside the zip and outside the MANIFEST.
- Decide before the first submit, at 08:30 UTC.

**(c) Arth's hours.** Arth's "evening before" is our night:
- the T2 approvals at 03:30–04:00 and ~06:30 UTC;
- the AICT export by 09:30 UTC;
- the review at 08:30–10:00 UTC (03:30–05:00 CDT).

Confirm he is available, or move his steps (the captain can run `notify`, `check` and `export` once the credentials are on the laptop). Ask now.

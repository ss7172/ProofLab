# 01 · Judging criteria, extracted and traced to the console

Every scoring criterion in the official material, each mapped to a **console screen**, a **backend artefact**, an **owner** and a **priority**. If a row has no screen and no artefact, we lose that mark, so check this table at every checkpoint.

**Sources.** Each criterion cites one of these:

| Key | Source |
|---|---|
| **MC-n** | Masterclass deck v10 (`context/Hackathon-MasterClass_v10_Distributable.pptx`), slide n |
| **MP** | Printed masterclass deck (`context/…transcripts.pdf`), which adds the judgement-day bonus artefacts and the bonus order |
| **TR** | Immersion-day transcript (`context/…slides.txt`), the organizers speaking |
| **AWS-p** | AWS "Agentic Assurance" kickoff deck (`context/Agentic_Assurance_VaraF.pdf`), page p |
| **PB §** | `HACKATHON_WINNING_PLAYBOOK.md` |
| **VF** | Teammate's live-verified facts (`working memory from teammate/`), which win over the playbook where they disagree (see `02-ARCHITECTURE.md` §9) |

**Priority.**
- **P0** is the minimum winning console: built first, and nothing in P1 starts before it passes acceptance.
- **P1** is strong.
- **P2** is stretch.

Owners: **T** = teammate (AWS side) and their coding agent; **A** = Arth (ServiceNow side); **S** = Sree (owner/approver); **C** = the console build (the teammate's coding agent).

---

## 1. The headline test (what "winning" means)

> "The winner provides the strongest evidence that every decision is explainable, every risk is controlled, and every claim can be independently verified in practice, **the most auditable solution wins**." (AWS-p24)

> "The team that evidences the most of the claim, with **records a stranger can check** and an architecture that would **survive being moved to different enforcement points**." (MC-36)

> "**This is NOT a logging exercise.** … If a stranger cannot check it without you in the room, it is not evidence yet." (MC-10)

The console's job, in one sentence: **turn the Evidence Pack into answers a sceptical stranger can check, in seconds, without us narrating.**

---

## 2. Gates: three judging levels, sequential (MC-38, AWS-p23)

"Alert levels" (Vanilla, Hostile, Rogue) are a **different taxonomy** (§9). The console labels these two "Judging L1–L3" and "Alert 0–2", and never mixes them.

| ID | Level (verbatim) | What we must show | Console | Backend artefact | Owner | Pri |
|---|---|---|---|---|---|---|
| J-01 | **L1 Foundation (required):** "Demonstrate the use case in Workshop Studio using the agreed MODaaS guardrails and NVIDIA-supplied model. A submission without this foundation will not be judged." | Governed Nemotron call (`x-modaas-action-id` + usage); prompt attack → `content_filter`, 0 tokens; direct Bedrock → `AccessDenied`; CR approvals (approver + attestation) | Overview → **Levels strip → L1 card**, every line linking to a captured record | `raw/l1/*` captures + `levels[L1]` in `pack-index.json` | T | P1 (the live demo is in the terminal; the card proves it from the pack) |
| J-02 | **L2 Observability:** "AI Native ODA (MoDaaS) controls are enabled and evidence collected in Audit ledger. ServiceNow Control Tower adds additional observability." | Ledger records for every named run; AICT inventory of our runtimes, with import time | Overview → L2 card; Run → ledger lane; Human loop → AICT line | `raw/ledger/*`, `servicenow/aict/*` | T + A | P1 |
| J-03 | **L3 Extended chain:** "Demonstrate how the sandbox further extends the solution with richer evidence, a stronger chain of evidence and additional proof, including other models where appropriate." | One id from the AWS records → finding → ServiceNow incident (owner, readback, response or silence) → Nemotron Assurance Agent note (provenance with gateway action id) → AICT runtime | **Human loop** view (5-step chain per finding); the Answer's human-loop line | `servicenow/{delivery-log.jsonl, incidents/, assurance-agent/, cases/}` | A + T | P1 (the Answer's human-loop line is P0) |

---

## 3. Axis 1: how many controls complete, end to end (MC-40, MC-35)

"None: nothing to score. 1 of 3: in the running. 2 of 3: ahead. 3 of 3: the full set." **A half-built control scores 0.** "Start with one control, finish until you see the evidence… then move on" (TR).

"Complete" means all seven of (a)–(g) hold (PB §4.2):
- **(a)** dated register entry with a named owner;
- **(b)** records bound to control + version + run at an enforcement point;
- **(c)** a reproducible evaluator;
- **(d)** a named PASS and a named BREACH run under the same threshold;
- **(e)** the breach alerted the named owner;
- **(f)** the query tool answers in under 2 minutes;
- **(g)** gaps recorded.

| ID | Criterion | Console | Backend | Owner | Pri |
|---|---|---|---|---|---|
| J-04 | **C16 ACN-COST-001** complete (a)–(g) | Answer (run + window), Register C16, Overview claim branch with a **7-item completeness checklist** | `register.yaml`, `records/C16/*`, `assessments/C16/*`, named runs, finding + incident | T | **P0** |
| J-05 | **C7 AIA-LOG-001** complete; "expected" defined **outside the graded agent** (AWS-p21) | Same, plus **coverage and timing shown separately** (MP: "A gap test checks timing, not completeness") | `expected/<scenario>.yaml`, `records/C7/*`, `assessments/C7/*` | T | **P0** (if built) |
| J-06 | **C9 AIA-ARC-006** complete; frozen baseline; alert **per crossing** | Same, plus window bars with **UNKNOWN windows hatched** (MP: "A missing measurement is not zero drift") | `baselines/*`, `raw/cloudwatch/*`, `assessments/C9/*`, one finding per crossing | T | **P0** (if built) |

The console derives the completeness checklist from the pack (`pack-index.json` → `claim.controls[].completeness`). It never hard-codes a tick.

---

## 4. Axis 2: quality, which decides the winner (MC-40)

| ID | Sub-criterion (verbatim test) | What earns the maximum | Console | Backend | Owner | Pri |
|---|---|---|---|---|---|---|
| J-07 | **The live test:** "We name one control and one window and watch you produce the answer. Two minutes. If we have to trawl your logs, you lose the mark." / "We ask; you operate. If you have to narrate the answer, the tool is not finished." (MC-39) | One query → one screen: rule, version, date, owner; expected vs observed population; measured vs limit; exceptions; verdict; gaps; resolvable records; human-loop line; AICT line. **Run ids and time windows.** | **Ask bar (⌘K) → Answer screen**, which shows `elapsed_ms`; the CLI `controltest` prints the same answer | `prooflab/query/*` → `ifabric.answer/v1` | T + C | **P0** |
| J-08 | **The architecture:** "Would it survive a second enforcement point? Is the register out of the live path? Is the evaluator stateless? Does the control hold its own threshold?" | Register loaded as a frozen version; pure evaluators; no threshold literals; 4 transports; EPs with honest status; 5 modes | **Architecture** page; the Answer footer shows the threshold *source* (`register.yaml@<ver>`, sha256) and the evaluator version | `architecture.md` + `pack-index.enforcement_points[]` | T + C | P1 (artefact 5 is a MUST for T) |
| J-09 | **The evidence:** "Bound to a control, a threshold version and a run. Verifiable by somebody who is not you. Gaps recorded rather than left blank." | Every record bound; raw captures + exact queries + capture times; MANIFEST; completeness statement per scope | **Evidence Ledger** with log→evidence view, **Record Inspector** (raw line, capture command, SHA-256, MANIFEST status, cross-surface joins), integrity badge | `raw/`, `facts/`, `records/`, `MANIFEST.json` | T + C | **P0** |
| J-10 | **The honesty:** "'Built properly: yes. Actually worked: no' is the most useful answer a team can bring. One honest failure scores better than everything green." (MP: "Bring one honest failure") | INDETERMINATE where data is missing; failed controls shown, never hidden; a detailed gap list | **Gaps** view; INDETERMINATE and UNKNOWN styled as first-class states (hatched amber), never blank; a "built properly / actually worked" line per control | `gap-list.md` → `gaps[]`, `assessments[].verdict` | T + A | **P0** |

---

## 5. Axis 3: bonuses, in rough order of value (MC-40, MP)

The judgement-day slide (MP) lists the **bonus artefacts to bring**:
- "More than one control implemented end to end";
- "**An inline decision, live**: show a verdict being formed in the path, not replayed afterwards";
- "Your adversarial test log: what you attacked, what broke, and what you changed";
- "The second or more enforcement points **running**, with a note of what you had to change".

| ID | Bonus | Earns it fully | Console | Backend | Owner | Pri |
|---|---|---|---|---|---|---|
| J-11 | + Extra controls (2nd, 3rd to the same standard) | All of J-04…J-06 | Claim tree with three complete branches | as J-04…06 | T | P0 (falls out of J-04…06) |
| J-12 | + **Continuous compliance**: "a verdict formed inline, in the path, while it runs" | A real `evaluate()` at an EP that can refuse (C16 admission before each model call). **Only claim it if the per-call decision records exist**; otherwise the console labels C16 "POST-RUN" (PB §3.2) | Run lane shows inline decisions (ALLOW / ALERT / DENY diamonds) next to the gateway calls; Answer shows "Inline decisions (evaluator)" separately from "Control test (tester)" | `records/C16/*` with `decision`, `runs/<cid>/run.json.enforcement` | T | P1 (P2 for live streaming during the slot) |
| J-12a | **Real-time monitoring** (user requirement; masterclass: "GRC is moving from after the fact to real time"; slide 24 "continuous compliance… rolling metric window… alert routed to a named owner") | Live telemetry turned into evidence as it happens; verdicts formed in the path; owner alerted within a minute; the monitor's own staleness visible | **Live Monitor** (LIVE mode) / **Replay** (PACK mode) | `prooflab watch` → `live/events.jsonl` | T + C | **P1** |
| J-13 | + **Adversarial testing**: "you attacked your own design and showed us what broke" | `evidence/adversarial/` covering Hostile and Rogue (§9); each case records attack → expected defence → observed → evidence → **what broke / what changed** | **Adversarial** matrix with outcome pills (DEFENDED · DETECTED · BROKE→FIXED · BROKE-OPEN) | `adversarial/<case>/case.json` | T + A | P1 |
| J-14 | + **Second enforcement point**: "the same architecture, moved, with nothing rewritten" | The same evaluator + Finding contract invoked at EP2, with a note of which adapter changed and which core code did not. **The console renders each EP's real status** (BUILT / PLANNED / NOT_BUILT) from the pack and never asserts one | Architecture page → EP table | `pack-index.enforcement_points[]` | T | P1 |

---

## 6. What loses marks (MC-40, MP)

| ID | Loses marks | How the console makes it impossible to miss | Backend | Pri |
|---|---|---|---|---|
| J-15 | "A threshold with **no date, or dated after the test**" ("we check the date", MP) | Register **date-before-run ribbon**: freeze → owner approval → first assessed run. Every Answer carries `rule.date_before_scope`; if false, the verdict banner turns into a red "RULE DATED AFTER TEST" warning | `register/register.yaml` (`frozen_at`, `version_date`), `register/approval.md`, approval incident export | **P0** |
| J-16 | "Records covering **only some** of the governed actions" | Answer **population block**: expected (and its source) vs observed vs matched vs missing vs duplicates vs blocked. A completeness statement per scope | `assessments[].population`, `expected/*` | **P0** |
| J-17 | "Evidence **only your own team** can verify" | Record Inspector shows the raw source line, the exact capture command/query, capture time, SHA-256 and MANIFEST status. The "**Verify without us**" panel recomputes the verdict from raw records | `raw/**/*.capture.json`, `MANIFEST.json`, `tools/manifest.py`, stranger README | **P0** |
| J-18 | "A finding **closed without a passing re-test**" | Finding lifecycle chip: OPEN → REMEDIATING → RE-TESTED → CLOSED. **CLOSED renders only when `closure.retest_ref` points at a SATISFIED assessment** of the same control/scope type under a valid version | `assessments[].closes_finding`, `findings[].closure` | **P0** |
| J-19 | "A control that **stores its own threshold**" | Answer footer: "threshold loaded from `register.yaml@<ver>` sha256 …", plus a CI test that greps evaluator code for numeric literals of any registered limit | `prooflab/tests/test_no_threshold_literals.py` | **P0** |
| J-20 | "A design that **only works in the request path**" | Architecture page marks each component in-path or off-path, and each transport (`emit`, `pull`, `callback`) by name | `architecture.md` | P1 |
| J-21 | "If an artefact is missing **we cannot score it**" (MC-39) | Overview → **six artefacts** checklist, computed from files present in the pack | `pack-index.artefacts[]` | **P0** |

---

## 7. The six required steps and "done" (MC-35)

1. Choose controls (7, 9, 16). **One complete is the minimum.**
2. Declare thresholds: metric, observation limit, exception tolerance, measurement basis, named owner; "**versioned and dated before any assessed run**".
3. Decide the timing: "Post-run forensics is the floor… continuously, inline as it runs, is bonus."
4. Build the control at an enforcement point, "**emitting records bound to the control, the threshold version and the run, not just a timestamp**".
5. Build the control test and/or evaluators: "recompute the measure, reconcile expected against observed, count exceptions, compare with your rule."
6. Run it both ways: "One passing case, one breaching case. **Do not move the threshold to make it pass.** Write down what you could not close."

**Done when:** "somebody who is not on your team can ask '**was control 9 satisfied for run FM-B?**' and get an answer in **two minutes**, with the records behind it." This is acceptance test **AT-01** in `09-BUILD-ORDER-AND-ACCEPTANCE.md`.

---

## 8. Judgement day: bring all six, or it cannot be scored (MC-39, MP, AWS-p8)

| ID | Artefact (MUST) | Console role | Backend file | Owner | Pri |
|---|---|---|---|---|---|
| J-22 | **Evidence file:** "exported, openable by us, covering the runs you want scored". Judges read the **team S3 bucket**, not laptops | Integrity badge with S3 readback (key, ETag/version, time); **PACK mode** reads exactly what was submitted | `evidence/` + `MANIFEST.json`; `submission` block in `pack-index.json` | T | **P0** |
| J-23 | **Threshold document:** "metric, limit, exception tolerance, measurement basis, owner, version and date" | Register view | `register/register.yaml` | T + S | **P0** |
| J-24 | **Control test tool:** "We type the question; you do not narrate the answer." Plus a **working or recorded** demo of the foundation | Ask bar + Answer; CLI | `prooflab/query/*` | T + C | **P0** |
| J-25 | **Two runs, named:** "written down before we arrive" | Overview → named-runs table showing `written_at`, with a red flag if it is after judging start | `run-ids.txt` | T | **P0** |
| J-26 | **One-page architecture:** "Components, what sits in the path of execution, and how an enforcement point invokes you. A whiteboard photograph is fine" | Architecture page (P1), plus the file itself | `architecture.md` / `architecture.jpg` | T | P1 (the file is a P0 MUST) |
| J-27 | **Gap list:** "What you could not close, and why. This is scored, and it scores well" | Gaps view | `gap-list.md` → `gaps[]` | T + A | **P0** |

**The two questions judges will ask, word for word**, which the grammar must accept and the screen must answer (PB §4.7.10):
- "Show me control 16 for run FM-B." (MP, MC-33)
- "Was control 9 satisfied for run FM-B?" / "…for a given run or time window?" (MC-35, MC-39)

The pack also has to answer "Give me evidence that your AI system was trustworthy with respect to 'SPEND CAP' **between times T1 and T2 or a given run**" (MC-9). The grammar therefore accepts **intervals**, not just run ids.

**Logistics** (TR, AWS-p8):
- work stops at **10:00 CDT Tuesday (15:00 UTC)** and judging starts;
- 15 minutes live per team;
- rehearse twice on the named runs.

---

## 9. AWS kickoff deck criteria (AWS-p2, p6, p7, p17, p19, p20, p24)

| ID | Criterion | Console | Backend | Owner | Pri |
|---|---|---|---|---|---|
| J-28 | **Six auditor questions:** "Judges pick an incident from your event window and ask six questions which are answerable from your Evidence Pack alone": **WHO** acted (identity, on whose behalf, scope) · **WHAT** it touched (models, tools, resources) · **AUTHORIZED** (which policy, which version, evaluated where) · **APPROVED** (attestation for every asset in the chain) · **INTEGRITY** (records not altered) · **RECONSTRUCT** (replay end to end with timestamps) | **Six Questions** view: an incident picker over the **whole event window**, six cards each marked ANSWERED / PARTIAL / GAP with file references | `auditor/*.json` (`ifabric.auditor/v1`) | T + C | **P0** |
| J-29 | **Three alert levels** ("How you win"): **Alert 0 Vanilla** (flow runs, safeguards active, evidence correlated end to end) · **Alert 1 Hostile** (delays, tampered prompts and skills, conflicting context → detection, safe degradation, unsafe actions denied) · **Alert 2 Rogue** (bypass attempts, unauthorized tool use, tampered records → containment, evidence preservation, reconstruction) | Adversarial view grouped by alert level | `adversarial/*` | T + A | P1 |
| J-30 | **Close the gap:** "the judgment they lack: know when to gather evidence or escalate, not act"; "a passing grade on the fault the reference agents cannot crack" (S2) | Runs view: disposition per agent vs scenario expectation (S1 auto-resolve, S2 gather-evidence + named evidence + reversible action, S3 escalate); `score-run.py` shown as a **diagnostic** only | `runs/<cid>/run.json.dispositions` | T | P1 |
| J-31 | "**A readable audit trail that links intent, control decisions and results.** Activity logs alone do not qualify." (Module 6, AWS-p17) | Run lane: each agent's INTENT → control decisions (PDP, guardrail, admission) → RESULT, joined by CID / trace id / action id | `runs/<cid>/run.json.lane` | T + C | P1 |
| J-32 | "**Where they disagree, the gateway wins.**" Spans = cross-check, gateway line = figure of record, AgentCore metrics = drift signal (Module 8, AWS-p19) | Record Inspector → "three records" panel per call: span vs gateway vs metric, with the gateway marked as the figure of record | `facts/*` with `figure_of_record` | T + C | P1 |
| J-33 | "**If its decisions can't be traced, the entry scores nothing.**" (Module 9, AWS-p20) | Every lane event and ledger row shows its join keys; untraceable events are flagged red ("unbound") | normalizer quarantine + `joins` | T | P1 |
| J-34 | Three pillars (AWS-p24): **Close the gap · Build a Control** ("at least one end to end; two named runs + a dated threshold doc") **· Handover Proof** ("An Evidence Pack that answers the six auditor questions") | Overview: three pillar tiles linking to the proof | `pack-index.json` | C | P1 |

---

## 10. Masterclass content the judges will probe

| ID | Criterion (source) | Console | Pri |
|---|---|---|---|
| J-35 | **The audit question**, 10 parts (MC-9): what was done · by which agent · in which part of the system · at what time · under whose authority · which rule it was checked against · what limit was in force at that moment · whether it was allowed, stopped or escalated · who was told when something went wrong · how I can be sure none of this has been changed since | The Answer's **Audit Question card**, 10 rows in three groups: The action / The decision / The proof (MC-4). Each row carries record refs | **P0** |
| J-36 | **What makes a record evidence** (MC-11): what happened · which control · which threshold version · which run · who acted · a seal (sealing out of scope) | The evidence record contract (`ifabric.evidence/v1`) and the Ledger columns use the slide's exact field names: `run.id`, `call.id`, `control.id`, `threshold.version`, `threshold.value`, `measured.value`, `verdict`, `actor.id`, `emitted.at`, `seal: out of scope` (MC-33) | **P0** |
| J-37 | **LOG vs EVIDENCE** (MC-10): "written for an engineer, next week" vs "written for a sceptical stranger, years later" | Ledger → **Log → Evidence** split view: the raw gateway line (as captured) beside its bound evidence record | **P0** |
| J-38 | **Evaluator vs tester** (MC-24): the evaluator judges the subject (one action, consumed by the EP in ms); the control test judges the control (the whole window, consumed by register, auditor, judge) | The Answer shows **two separate blocks**: "Control test (tester): dated pass/fail" and "Inline decisions (evaluator): allow/deny/alert per call". The second appears only if records exist | **P0** (labels) |
| J-39 | **Five control modes, one format** (MC-20, MC-25): static, scheduled, event-driven, in-transaction, continuous | Architecture → modes strip; register `mode` per control | P1 |
| J-40 | **One contract, four transports** (MC-26): `evaluate()` sync in path · `emit()` async · `callback()` deferred/human · `pull()` scheduled; plus the sidecar/SDK interceptor (MC-25) | Architecture page | P1 |
| J-41 | **Five habits** (MC-26): telemetry never judges · evaluator never remembers · register never in the path · ledger never interprets · records sealed where made (out of scope) | Architecture page; our layered pipeline (raw → facts → records → assessments) makes each habit structural | P1 |
| J-42 | **"Race: two calls both read 9,800 under a 10,000 cap and both pass. Reserve, then commit."** (MC-25) | Inline decisions show `reserved` and `committed` per call | P1 |
| J-43 | **Thresholds: four questions** (MC-21): why this metric · why this value ("'It is what we achieved' is not an answer") · measured on what · when does it stop holding | Register control card shows the four justifications | **P0** |
| J-44 | **Control anatomy** (MC-16): identifier, statement, objective, owner, applicability, evidence, test procedure, frequency, parent/links; "ownership by a group means ownership by nobody" | Register control card | **P0** |
| J-45 | **Parent and child control** (MP): library control `AIA-ARC-006` (no number) → our child `AIA-ARC-006.01` (our number, dated) | Register shows parent → child | P1 |
| J-46 | **GRC loop** (MC-19): control → test → **finding** (design / operation / both) → **risk exposed** (residual back to inherent) → remediation (fix / compensate / accept with named approver and hard expiry) → **re-test, the only way the loop closes** | Finding card: deficiency type, inherent/residual rating, response, closure by re-test | P1 (closure display is P0 via J-18) |
| J-47 | **Four roles, nobody checks their own work** (MC-13, MP): management (owns the claim and the response), GRC, operations (builds, produces records), assurance (tests, explains); "the person who ran the test is not the person judged by it" | Register → People panel: owner ≠ builder ≠ assurance; approver identity on every approval | **P0** |
| J-48 | C9: "**Detection working does not erase the breach**" (MC-34) | C9 answer shows the alert sent **and** NOT SATISFIED together | **P0** |
| J-49 | "Each rule carries **two numbers**: the limit on a single observation, and the share of observations allowed to break it. Declare both." (MC-34) | Answer comparison block always shows both | **P0** |
| J-50 | Out of scope (MP): "A human actually answering an alert… **the alert, its named recipient and the silence must still be recorded**" | Human-loop line renders NO_RESPONSE_OBSERVED as a valid recorded result, not a failure | **P0** |
| J-51 | Out of scope (MC-37, MP): signatures, hash chains, Merkle proofs; a slide deck ("A whiteboard and a working tool beat both") | Records show `seal: out of scope`; integrity = MANIFEST checksums + cross-surface corroboration (not a chain). **No slides in the pitch**: present from the console | P0 (labels) |
| J-52 | **Same-ID chain** (PB §4.7.1): run id, `finding_id` and incident correlation id visible on one screen | Hover or click any id → every occurrence on screen highlights ("follow the thread") | P1 |

---

## 11. Rules that constrain the build (MC-37, TR, PB §1.8)

| ID | Rule | Consequence for the console |
|---|---|---|
| J-53 | Nemotron models only; agents run only on AWS AgentCore (Strands) or in ServiceNow (TR) | The console calls **no model**. The only LLM output it shows is the Assurance Agent note, labelled "Nemotron's judgement" and kept separate from checked facts |
| J-54 | Use all three environments: AWS Workshop Studio, ServiceNow Control Tower, ServiceNow sandbox (MC-37) | Overview environment strip with evidence links for each |
| J-55 | "ServiceNow Control Tower and human loop … **absolutely needed**" (TR) | Human loop view and the AICT line are mandatory P1, not optional |
| J-56 | "**A dashboard** [is not an enforcement point]: sees everything, can refuse nothing" (MP, TR) | The console never decides anything. Judge mode is read-only, and operator actions are **requests** to separate processes, recorded as evidence (`02-ARCHITECTURE.md` §5) |
| J-57 | "Stay under one model request/second" (account-wide: 100 req/min and 2.5M tokens/h, including helper calls) and "back up your work as you go" (AWS-p8) | Operator "launch run" (P2) checks headroom before queuing; the pack is backed up to S3 |
| J-58 | No secrets anywhere: OAuth secret, gateway key, ledger token, IdeUrl/CockpitUrl, presigned URLs (PB §3.13) | The browser never receives a secret; capture-time redaction (`04-LOGS-TO-EVIDENCE.md` §3) |

---

## 12. "Extra points that stand out" (PB §4.7), all cheap to show

| # | Extra | Console |
|---|---|---|
| 1 | Same-ID chain on one screen | J-52 thread highlighting |
| 2 | Stranger README | Integrity view links `evidence/README.md` §5 ("recompute it yourself") |
| 3 | Pre-written `run-ids.txt` with windows, timestamped before judging | J-25 |
| 4 | Decision log (dated) | Register → Decisions tab (reads `decisions-log.md`) — P1 |
| 5 | Owner engagement: one RESPONDED **and** one NO_RESPONSE_OBSERVED | Human loop shows both states |
| 6 | Kill-switch demo with requested vs effective times | Adversarial case R6 + EP5 row |
| 7 | Model swap as a drift experiment (only if it actually shows in C9) | C9 window annotation "config change: alias swap" — P2 |
| 8 | Recorded backup demo | `presentation/` guide, backup path |
| 9 | Whiteboard architecture photo | Architecture page embeds `architecture.jpg` if present |
| 10 | Practise the judges' exact phrases | The Ask bar's suggestion chips are those phrases |

---

## 13. Coverage check (run this the evening before)

- [ ] Every J-row above has a non-empty Console cell **and** a backend file that exists in the pack.
- [ ] Every **P0** row passes its acceptance test in `09-BUILD-ORDER-AND-ACCEPTANCE.md`.
- [ ] Nothing on screen claims an EP, an inline decision or a level that the pack cannot show records for (J-12, J-14).
- [ ] No threshold number appears anywhere except as loaded from the frozen register (J-19).
- [ ] The two taxonomies are never mixed: **Judging L1–L3** vs **Alert 0–2**.

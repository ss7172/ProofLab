# Hackathon Winning Playbook (team iFabric): brief, scoring, best practices

**For:** everyone on team iFabric and their coding agents, covering the AWS agents, the controls (C7/C9/C16), evidence and the pitch.
**Companion document:** `SERVICENOW_INTEGRATION_HANDOFF.md` (the ServiceNow integration spec). References written as "SN-handoff §N" point there.
**Date:** 2026-10-05. Self-contained: you do not need the slides.

| Section | Use it for |
|---|---|
| **§1 The brief, scoring rules and winning insights** | Understand exactly what is being judged, the scenario, the claim, the three controls, worked examples, the rules |
| **§2 Field guide: agents and workshop modules** | Building and changing agents on AgentCore/MoDaaS without tripping the platform's rules |
| **§3 Winning playbook: best-practices checklist** | The team's definition of "done well" for code, agents, controls and evidence ([MUST]/[BONUS]/[BEST]) |
| **§4 Scorecard** | Self-score against every scoring criterion at each checkpoint; fix ❌ items in table order |

---

## 1. The hackathon brief, scoring rules and winning insights (restated in full; no slides needed)

*This section restates the official brief in full, so **you don't need the slides**. It combines the organizers' masterclass on governance, risk and compliance, the AWS briefing, and the organizers' answers on the kickoff call. "MUST" = stated requirement; "WIN" = what the judges reward; "LOSE" = stated penalty.*

### 1.0 The brief, restated (everything the slides say that matters)

**The challenge in one sentence:** make AI agents whose every action can be **proven** to a sceptical auditor. "Something went through our AI system on Tuesday morning. Show me: what was done, by which agent, where, when; on whose authority, against which rule and limit, allowed or stopped or escalated; who was told, and can I trust it hasn't changed?"

**The scenario (what the agents do):**
1. A customer's home internet keeps dropping, and they open a chat.
2. **Customer zone:** a chat agent takes the complaint and raises a trouble ticket. In the original design this zone is ServiceNow; in this build all three agents run on AWS AgentCore.
3. **Gateway A**, then the **IT zone:** a triage agent checks the account records and services.
4. **Gateway B**, then the **network zone:** an investigation agent uses network inventory and a **digital twin** to diagnose the fault.
5. The resolution travels back through Gateway B and Gateway A. **There is no direct route from the network to the customer.**
6. **Every model call from every agent crosses one shared model gateway.** That's where tokens are counted, budget is decided, and a run can be halted.
7. Each step is a span carrying the same **trace id and run id**.

**The claim we must evidence (C-FM-01):** "During customer fault resolution, the three collaborating agents meet our declared event-recording, drift and performance, and token-spend requirements." Each control below is one branch of this claim.

**The three controls** (from an EU AI Act control library; the Act's Art. 12 record-keeping duty applies to the network agent as high-risk critical infrastructure):

| # | Control | Mode | What it means | We measure | **We set (dated, before testing)** |
|---|---|---|---|---|---|
| **7** | AIA-LOG-001, automatic event recording | Event-driven | Every in-scope event is recorded and joined to one run, across all three zones | Expected-event coverage, and the time gap between consecutive events | Coverage target **[C%]**, gap limit **[G ms]**, tolerated exception rate **[B7%]** |
| **9** | AIA-ARC-006, drift and performance | Continuous | A live measure watched against a **frozen baseline**, with a **named owner who responds** | Relative change from baseline per comparable window | The metric, the baseline, drift limit **[D%]**, violating-window allowance **[B9%]** |
| **16** | ACN-COST-001, per-run spend cap | In-transaction | The gateway asks before each call "is this run still under cap?" and can halt the run | Total input + output tokens per run, **all agents plus every retry** | Cap **[N tokens]** per run, allowed over-cap runs |

**The governance tree for each control:** claim → **objective** (e.g. "drift ≤ D% vs baseline; violating windows ≤ B9%") → **risk** (e.g. "drift goes unnoticed, or the measurements themselves are missing") → **control test** (e.g. "recalculate drift, count breaches, check monitoring and the alert response") → **evidence** (e.g. "baseline, live values, windows, alerts, owner and the required response"). The risks to name:
- **C7:** missing events, broken run links, excessive unexplained gaps.
- **C9:** drift unnoticed, or measurements missing.
- **C16:** a loop overspends, or calls are missed or charged to the wrong run.

**Worked examples** (illustrative numbers from the brief; copy the shape, not the values):
- **C16:**
  - **Declare:** "10,000 tokens per fault-resolution run, all three agents and every retry, zero over-cap runs permitted", frozen as **G-FM-v1** and dated before the first assessed run.
  - **Enforce:** at the shared model gateway.
  - **Record:** one record per call, asynchronously, off the request path, bound to run, control and version.
  - **Test:** `controltest 16 --run FM-A` reconciles every call, sums input + output and compares with the cap.
  - **Show:** **FM-A 9,600 → SATISFIED; FM-B 10,800 → NOT satisfied** (one of two runs over cap, none permitted). The 800 overshoot stays visible.
  - **The judge's question:** "Show me control 16 for run FM-B."
  - **Evidence record:**

    | Field | Value |
    |---|---|
    | `run.id` | FM-A |
    | `call.id` | c-0042 |
    | `control.id` | ACN-COST-001 |
    | `threshold.version` | G-FM-v1 |
    | `threshold.value` | 10000 |
    | `measured.value` | 9600 |
    | `verdict` | SATISFIED |
    | `actor.id` | investigation-agent |
    | `emitted.at` | 2026-09-30T09:14:02Z |
    | `seal` | out of scope |

- **C7:**
  - **Rule:** 100% of events recorded, each gap < 5 ms, violating gaps ≤ 10%.
  - **Data:** 11 of 11 events give 10 gaps of 2, 3, 4, 2, **8**, 3, 2, 4, 3, 2 ms. One of 10 violates (10%), which is within tolerance → **SATISFIED**, and the 8 ms exception stays visible. A second violation (20%) would fail.
- **C9:**
  - **Rule:** relative drop ≤ 10% per window, 0% violating windows allowed, 100% coverage.
  - **Data:** windows W01–W10 show 4, 6, 3, 8, 5, 7, 9, 6, 4, **12%**. One violating window with 0% allowed → **NOT satisfied**. "Detection working does not erase the breach," and the window still triggers the alert to the named owner.
  - The brief's example is an accuracy-style score drop. Our C9 uses the workshop's AgentCore **latency/errors**, where **higher is worse**: relative increase = (observed − baseline) / baseline.

**Governance vocabulary judges use:**
- **Policy:** what must be true (the claim, scope and numbers).
- **Process:** how it's applied (objectives, risks, controls, tests).
- **Platform:** how it's proven (records, events, measures, decisions joined so they can be queried).
- **People:** who is accountable (a named owner, a builder, an independent reviewer).

Management owns the claim, developers make it measurable, assurance checks the evidence.

**Controls and thresholds:**
- **A control** is "a safeguard, done by people or a system, that keeps risk within limits, **and that somebody else can check**". It is **documented**, **owned by one named person** ("ownership by a group means ownership by nobody") and **specific**.
- **Threshold example:** the law says "an appropriate level of accuracy"; the library control says "a metric exists and the achieved level is declared". **Our specification** says "groundedness on the fixed test set between [0.85, 1], measured on data held out from the last four quarters". The **test record** then says "measured 0.81 on 12 March: fail; finding raised, owner assigned, re-test scheduled".
- The number lives only in our specification, and **its date is what makes it a test**.
- **When a test fails:** finding → risk exposed (residual rating goes back to inherent) → remediation (fix, compensate, or accept with a named approver and hard expiry) → **re-test, the only way the loop closes**.

**Why controls matter:** binding law (EU AI Act Arts. 9, 12 and 17: risk management, quality system, automatic logging; fines up to €35M or 7% of turnover for prohibited practices, €15M or 3% for most obligations), and the fact that AI risk drifts with data, with no code change.

### 1.1 The scoring model (read this twice)
- **Levels are sequential (gate, MUST).**
  - **L1 Foundation:** use case running in Workshop Studio with **the agreed MoDaaS guardrails and an NVIDIA Nemotron model**. "A submission without this foundation will not be judged."
  - **L2 Observability:** MoDaaS controls enabled + evidence in the **audit ledger** + **ServiceNow Control Tower** adds observability.
  - **L3 Extended chain of evidence:** AWS + ServiceNow sandbox, richer evidence and a stronger chain, "including other models where appropriate".
- **Axis 1 orders the field:** how many of C7/C9/C16 are **complete end to end** (0 = nothing to score, 1 = in the running, 2 = ahead, 3 = full set). **Finish one control completely before starting the next.** "Don't do things partially."
- **Axis 2 decides the winner:**
  1. **The live test:** the judge names a control and a run or window; we produce the answer in **2 minutes**. "If we have to trawl your logs, you lose the mark."
  2. **The architecture:** survives a **second enforcement point**? register **out of the live path**? evaluator **stateless**? the control **does not hold its own threshold**?
  3. **The evidence:** bound to control + threshold version + run, verifiable by **somebody who is not you**, gaps recorded rather than left blank.
  4. **The honesty:** "Built properly: yes. Actually worked: no" is the most useful answer. **"One honest failure scores better than everything green."**
- **Axis 3 separates ties (bonuses, in order of value):**
  1. extra controls to the same standard;
  2. **continuous compliance** (verdict formed inline, in the path, while it runs);
  3. **adversarial testing** (you attacked your own design and **show what broke and what you changed**; Nemotron may drive it);
  4. **second enforcement point** (same architecture, moved, nothing rewritten).
- **LOSE:**
  - a threshold with no date, or dated after the test;
  - records covering only some of the governed actions;
  - evidence only our team can verify;
  - a finding closed without a passing re-test;
  - a control that stores its own threshold;
  - a design that only works in the request path.
- **Overall headline (AWS briefing):** "the strongest evidence that every decision is explainable, every risk is controlled, and every claim can be independently verified … **the most auditable solution wins**."

### 1.2 The six required steps (MUST, in order)
1. **Choose** controls (7 event recording, 9 drift, 16 spend cap). One completed is the minimum.
2. **Declare thresholds:** metric, observation limit, exception tolerance, measurement basis, **named owner** (a person, not a team), **versioned and dated before any assessed run**.
3. **Decide timing:** post-run forensics is the floor; inline/continuous is a bonus.
4. **Build the control** at an enforcement point of your choosing, **emitting records bound to the control, the threshold version and the run, not just a timestamp**.
5. **Build the control test / evaluator:** recompute the measure, reconcile expected against observed, count exceptions, compare with the rule.
6. **Run it both ways and record the gaps:** one passing case, one breaching case. **Do not move the threshold to make it pass.**

**Done when:** "somebody who is not on your team can ask 'was control 9 satisfied for run FM-B?' and get an answer in two minutes, with the records behind it."

### 1.3 Judgement day: bring all six, or it cannot be scored (MUST)
1. **Evidence file:** exported, openable by the judges, covering the runs to be scored.
2. **Threshold document:** one entry per control: metric, limit, exception tolerance, measurement basis, owner, version, date.
3. **Control test tool + demo:** CLI, script, API or small app. "**We ask; you operate.** If you have to narrate the answer, the tool is not finished." Bring a working **or recorded** demo of the foundation.
4. **Two named runs:** one passes, one breaches, ids **written down before** judging.
5. **One-page architecture:** components, what sits in the execution path, how an enforcement point invokes you. A whiteboard photo is fine.
6. **Gap list:** "This is scored, and it scores well."

Also:
- **Rehearse twice** on the two named runs.
- **Assemble everything the evening before**, not on the morning of judging.
- Judges read the **team S3 bucket**, not your laptop.
- The preliminary slot is **15 minutes live**.

### 1.4 What makes something evidence (WIN)
- **"Not a logging exercise."** A log is for an engineer next week. Evidence is for **a sceptical stranger, years later**: **complete for the actions that matter**, impossible to change quietly, kept on a stated retention rule, and **proves who acted**.
- **Record fields** (worked example):
  - `run.id`, `call.id`, `control.id`, `threshold.version`, `threshold.value`, `measured.value`, `verdict`, `actor.id`, `emitted.at`
  - seal: **out of scope**
- **The stranger test:** "hand a stranger one record … if they can check it without you, it is evidence; if they need you in the room, it is a database you are asking people to trust."
- **The audit question we must answer for any window:**
  - **the action:** what, which agent, where, when;
  - **the decision:** on whose authority, which rule and limit, allowed, stopped or escalated;
  - **the proof:** who was told, can I trust it hasn't changed.
- **Six auditor questions** (AWS briefing): the judges pick **an incident from your event window** and ask, from the Evidence Pack alone:
  1. **WHO** acted (identity, on whose behalf, scope)
  2. **WHAT** it touched (models, tools, resources)
  3. **AUTHORIZED** (which policy, which version, evaluated where)
  4. **APPROVED** (an attestation for **every asset in the chain**)
  5. **INTEGRITY** (records not altered)
  6. **RECONSTRUCT** (replay end to end with timestamps)
- **Module 6 bar, verbatim:** "A readable audit trail that links **intent, control decisions and results**. Activity logs alone do not qualify."

### 1.5 Control design rules (WIN)
- **Anatomy of a testable control:**
  - identifier (stable, never reused)
  - statement (an assertion)
  - objective and the risks it holds down
  - **named owner**
  - applicability
  - numbered evidence artefacts
  - test procedure a stranger can follow
  - frequency
  - parent/links
- **Thresholds live in your specification, not in the law or the library control.** "Its **date** is what makes it a test." For every threshold, answer four questions **in the register**:
  1. **Why this metric?** (tie it to purpose and harm)
  2. **Why this value?** (dataset, period, holdout)
  3. **How is it measured?**
  4. **What happens when it stops holding?** (boundary conditions)
- **GRC chain:** claim → objective → risk → control → control test → evidence. A failed test creates a **finding**, which **exposes risk**, which needs **remediation**. The **re-test is the only way the loop closes.**
- Three defensible responses to a failure:
  1. remediate (fix the cause);
  2. compensate (an interim measure);
  3. accept **with a named approver and a hard expiry**.
- **Four roles; nobody checks their own work:**
  - accountable management (owns the claim: Sree)
  - GRC (defines what's required)
  - operations (builds and runs: the teammate)
  - assurance (tests and explains)
- **Five control modes**, one definition and evidence format for all:

  | Mode | Example |
  |---|---|
  | Static | AI policy |
  | Scheduled | AI inventory; AICT discovery is one |
  | **Event-driven** | **C7** |
  | **In-transaction** | **C16**: the gateway asks before the call and can halt the run |
  | **Continuous** | **C9**: watched against a frozen baseline, with a named owner who responds |

- **The claim (C-FM-01):** "During customer fault resolution, the three collaborating agents meet our declared event-recording, drift and performance, and token-spend requirements." Fill every bracket:

  | Control | Brackets to fill |
  |---|---|
  | C7 | coverage **[C%]**, gap **< [G ms]**, violating gaps **≤ [B7%]** |
  | C9 | drift **≤ [D%]** vs baseline, violating windows **≤ [B9%]** |
  | C16 | **≤ [N tokens]** per run, all agents **plus retries** |

- **Worked-example behaviours to copy:**
  - The **overshoot stays visible**: FM-B is 10,800 vs 10,000, so "not satisfied by 800".
  - C7: the 8 ms exception stays visible even when within tolerance.
  - C9: "**detection working does not erase the drift breach**". One violating window with 0% allowed means NOT satisfied, and every crossing still alerts the named owner.
  - C16 record: the gateway emits **one record per call, asynchronously, off the request path**, bound to run, control and version.
  - Command shape: `controltest 16 --run FM-A`.

### 1.6 Architecture rules (WIN)
- **Five problems that decide "architecture vs demo":**
  1. one definition and evidence format across the **five modes**;
  2. **how an enforcement point invokes you**: one contract, four transports:

     | Transport | When |
     |---|---|
     | `evaluate()` | sync, in path |
     | `emit()` | async, event bus |
     | `callback()` | deferred: human approval, late verdicts |
     | `pull()` | scheduled or continuous |

  3. **only the enforcement point may make work wait**, and only for one question (avoid race conditions);
  4. **a span is not evidence** until it is bound to a control, a version and a run;
  5. **cover every kind of EP**: some cannot be modified, some answer late, some have no request path.
- **Five habits:**
  1. telemetry never judges;
  2. **the evaluator never remembers**;
  3. **the register is never in the execution path**;
  4. the ledger never interprets;
  5. records are sealed where made (out of scope).
- **Enforcement points:** a dashboard is **not** an EP ("sees everything, can refuse nothing"). The list:
  - model gateway
  - zone/API gateway
  - guardrails
  - tool call
  - retrieval/data access
  - sub-agent handoff
  - **human approval queue**
  - planner
  - agent memory write
  - deferred action
  - platform automation
  - kill switch

  Every EP does five things: **ask, wait, act, record**, (seal).
- **Timing:** before it runs (go/no-go), while it runs (verdict in milliseconds), after it ran (was the control held between T1 and T2). GRC is moving to **real time**, and to **thresholds and probabilities** instead of checklists.
- **Draw your architecture in the first hour and show it to a mentor.**

### 1.7 The AWS-side game (from the AWS briefing and workshop modules)
- **"Closing the gap is the game":** the reference agents "look good but guess confidently under ambiguity". Give them **the judgment to gather evidence or escalate, not act**.
  - **S2** (transport-congestion, ambiguous) currently fails (7/10). To pass it, the agents must return **gather-evidence, name the evidence that would settle it, and propose a reversible action**.
  - Keep **S1** (auto-resolve) and **S3** (maintenance-freeze trap → **escalate**) passing.
  - `score-run.py` is a self-check, **not** the judging rubric.
- **Three alert levels to prove:**

  | Level | Conditions | Prove |
  |---|---|---|
  | **Vanilla** | Normal operation | The flow runs, safeguards are active, evidence is correlated end to end |
  | **Hostile** | Delays, tampered prompts or skills, conflicting context | **Detection, safe degradation, unsafe actions denied** |
  | **Rogue** | Bypass attempts, unauthorized tool use, tampered records | **Containment, evidence preservation, reconstruction** |

  Capture each as an adversarial test case: what we attacked, what happened, the evidence. This is the **adversarial bonus**.
- **Two operating rules:**
  1. **stay under ~1 model request/second** (account-wide ceiling **100 requests/min and 2.5M tokens/h**, including helper calls, so **don't** run 3 agents at 1 RPS each);
  2. **back up your work as you go**, because the account is destroyed at the end.
- **Module 8: three records of one run, side by side:**

  | Record | Role |
  |---|---|
  | Agent OTEL spans | cross-check |
  | **Gateway per-call line** | **figure of record**: "where they disagree, the gateway wins" |
  | AgentCore metrics | drift signal for C9 |

  "Traces have no durable exporter here. **Join on the trace id.**" "**A run you cannot replay from evidence is a run you cannot defend.**"
- **Module 9:** "**If its decisions can't be traced, the entry scores nothing.**"
- **Module 10 (twin):** use the scenario switch to produce a **passing run and a breaching run on demand**; C7 "expected events" must be **defined outside the graded agent**; C9 needs a **stable baseline**. Stretch goal: wrap the twin's prediction as an MCP server and declare it as a **ToolConfig**.

### 1.8 Rules from the kickoff (MUST)
- **Nemotron models only** for our own agents (Nano 9B / Nano 30B / Super 120B through the governed aliases; no Omni or Ultra here). Agents run **only on AWS AgentCore** (Strands) or in **ServiceNow**; nothing hosted elsewhere.
- **ServiceNow AICT + human loop: "absolutely needed".** Use **all three environments** (Workshop Studio, Control Tower, ServiceNow sandbox), "as broadly and creatively as possible, in parallel where useful".
- AICT: create our own connector **with the team name**; rename or name agents with the team name; don't change risk frameworks; one ServiceNow agent is enough (no bonus for workflows); clone, never edit, shared agents.
- **Out of scope:** signatures, hash chains, Merkle proofs, a slide deck. "A whiteboard and a working tool beat both."

---

## 2. Building agents and working with the AWS workshop modules (field guide)

**Platform facts that bite** (from the workshop guide and our findings):

| Area | Rule / pitfall |
|---|---|
| **Where agents run** | **AWS AgentCore Runtime** via the MoDaaS operator. Path: `new-agent.sh` → **CodeBuild ARM64** image → ECR → generated **AgentConfig** CR → **human approval** → operator provisions the runtime. Direct Docker push, direct Bedrock calls and direct AgentCore creation are **denied**. |
| **Naming** | **`ifabric_…`** for every new agent, tool and CR (shared AICT; judges must find ours) |
| **Model access** | Only through the governed gateway **`modaas-agw`**: `POST /v1/chat/completions` (OpenAI format) with a **model alias** (e.g. `nemotron-nano-9b`, `nemotron-nano-3-30b`, `nemotron-super-120b`). Direct Bedrock gives `AccessDeniedException`, which is good evidence that the governed path is the only door. **Check each alias's live approval state; the guide's examples conflict.** |
| **Four injected values** | Gateway address + API key; ledger address + write token. **Inject them, never hard-code them.** Read them from env so the agent **fails closed** when a key rotates |
| **Approval is a human act** | CRs wait in `Reviewing` until annotated `modaas.tmforum.org/approver` + `modaas.tmforum.org/approval-attestation`. **Never fake a reviewer.** Capture `.status.governance.approvals` (subject, time) as the **APPROVED** evidence. `Approved` ≠ runtime READY: check readiness separately |
| **Swapping a model** | Patch **both** `dependsOn.models[0]` and `modelRef` (some examples omit one). Wait for the new generation and READY, and record the change as a new reviewed version |
| **Strands adapter** | Keep the template's `GatewayModel(OpenAIModel)` that **removes an empty `tools: []`** (Bedrock rejects it). Don't override the pinned `strands-agents` / `bedrock-agentcore` / `mcp` versions |
| **MCP tools** | Streamable HTTP needs `initialize`, the `Mcp-Session-Id` header, and `Accept: application/json, text/event-stream`. Use a ToolConfig on AgentCore Gateway and restrict `toolName` in the team **Cedar ConfigMap** (the only allowed edit in `modaas-system`) |
| **Guardrails** | A prompt-attack block returns **HTTP 200** with `finish_reason=content_filter` and **0 tokens**. Treat that as a **blocked** verdict, not success. It is great **Hostile-level** evidence |
| **Kill switch** | `spec.paused: true` withdraws the route (next call 404; ~15 s to stop, ~50 s to resume). Not instantaneous; record requested vs effective times |
| **Rate limits** | 100 req/min, 2.5M tok/h **account-wide**; serialize runs, use bounded retries, and **count retries** (C16 needs them) |
| **Evidence sources** | Ledger `audit-store` `/records?cid=` = **JSONL** (`/timeline` is human text, not JSON). Gateway per-call usage = C16 figure of record. Spans: `/aws/bedrock-agentcore/runtimes/<id>-DEFAULT`. C9: `AWS/Bedrock-AgentCore` Latency Average / Errors Sum, period 3600, by runtime. The OTEL collector **discards** traces, so Cockpit Trace is empty (a gap, not proof of nothing) |
| **Correlation** | `run-reference.sh` prints the CID; a child shell can't export it, so capture it explicitly. Keep `traceparent`, or gateway run ids fragment and a naive C16 total misses calls |
| **Model output** | Nemotron may emit think-tags. **Never present the private reasoning as evidence**; parse only the final structured answer |
| **Don't touch** | Protected namespaces (`canvas`, `canvas-vault`, `cert-manager`, `modaas-system` except the team Cedar ConfigMap, `agentgateway-system`, `istio-system`). No IAM changes, no public endpoints, no real customer data |
| **Back up** | Commit code and copy evidence to the team S3 bucket regularly; the account is destroyed after the event |

**Agent behaviour that scores** (the "judgment gap"):
1. **S2:** return `gather-evidence`, **name the evidence** that would separate the two root causes, and propose a **reversible** next step. Never take a confident repair action.
2. **S3:** maintenance freeze → `escalate`. That escalation becomes an **ESC incident in ServiceNow** (SN-handoff §7.4); the human loop and evidence are both shown.
3. **Every decision is traced:** agent → gateway action id → ledger record → (if escalated) ServiceNow incident, all joined by the CID or trace id.
4. **Hostile and Rogue tests:**
   - tampered prompt → guardrail block;
   - unauthorized tool → Cedar deny;
   - tampered ledger record → ledger verification fails;
   - bypass attempt → direct Bedrock denied.

   Store each as an adversarial case: input, expected, observed, and evidence references. This is the **adversarial bonus** and Hostile/Rogue proof.
5. **Second enforcement point:** the same evaluator and Finding contract used at the gateway (C16) **and** at the human approval queue (ServiceNow) or the tool call (Cedar/ToolConfig). Show it in `architecture.md` with "nothing rewritten".

**Order of work that wins:**
1. **Hour 0–1:** draw the architecture, show a mentor, freeze `register.yaml` (owner = Sree) with dated thresholds.
2. **C16 end to end first:** gateway records → evaluator → assessment → named pass/breach runs → ServiceNow incident on the breach → query tool answers in < 2 min.
3. **Start C9 baseline collection early.** It needs closed hourly windows, so the clock is the constraint.
4. **C7 end to end** (expected events defined outside the agent; twin or scenario as the source).
5. **S2 judgment fix + S3 escalation → ESC incident.**
6. **Adversarial cases** (Hostile/Rogue) + second-EP write-up.
7. **Evidence Pack:** MANIFEST, submit, readback, then **rehearse twice**.

---

## 3. Winning playbook: best-practices checklist (code, agents, controls, evidence)

**Tags:**
- **[MUST]** is required by the rules; missing it loses the item or the level.
- **[BONUS]** earns Axis 3 points.
- **[BEST]** is what separates a winning entry (Axis 2 quality).

Each item says **what to implement**. Tick them off in the team's tracker.

### 3.1 Governance and the threshold register
- [ ] **[MUST]** `register.yaml` has, per control: `control_id`, `name`, `metric`, `observation_limit`, `exception_tolerance`, `measurement_basis`, **`owner` (a named person: `annapurna@invences.com`)**, `version`, `version_date`, `enforcement_point`.
- [ ] **[MUST]** Freeze and date it **before the first assessed run**, and use the **same threshold for the passing and the breaching run**. Never move a threshold after seeing results.
- [ ] **[BEST]** Add the four justifications per threshold:
  1. **why this metric** (purpose and harm);
  2. **why this value** (dataset, period, holdout);
  3. **how it is measured** (source, formula, unit, **comparison operator**, inclusive or exclusive);
  4. **what happens when it stops holding** (boundary conditions, missing-data rule).
- [ ] **[BEST]** **Change a threshold by bumping its version** (G-FM-v1 → v2) and keep the old one, so old verdicts can be replayed under the rule that was in force. Never edit a frozen version in place.
- [ ] **[BEST]** Record **Sree's approval** of the register as a ServiceNow note or record: a timestamp and identity a stranger can check. The register owner (accountable management) is a different person from the builder (operations); **nobody checks their own work**.
- [ ] **[BEST]** Label any calibration runs made before the freeze as **exploratory** and exclude them from assessed results.
- [ ] **[BEST]** State the claim **C-FM-01** at the top of the register, with each control as a branch: objective → risk → control → control test → evidence. Fill in every bracket ([C%], [G ms], [B7%], [D%], [B9%], [N tokens]).
- [ ] **[BEST]** Write a **retention rule** in `evidence/README.md` (e.g. "kept for 7 years from submission"). The masterclass defines evidence as "kept on a stated retention rule".

### 3.2 C16, per-run token spend cap (do this first)
- [ ] **[MUST]** Count **all three agents + every retry** per run, using the **gateway per-call usage records as the figure of record**. Spans and agent responses are only cross-checks.
- [ ] **[MUST]** Compare with the **exact declared operator** (`<= 10,000`: 10,000 passes, 10,001 breaches) and keep the **overshoot visible** ("BREACHED by 800").
- [ ] **[BEST]** Deduplicate: the same call seen in the gateway, ledger and spans is **one** charge. A corrected total **replaces** the earlier one; never add both.
- [ ] **[BEST]** Under cap but with missing or unmatched calls → **INDETERMINATE**, never SATISFIED. Over cap with a trusted subtotal → **BREACHED**, even if other data is missing.
- [ ] **[BEST]** Preserve `traceparent` / run id on every call, or the gateway records fragment and a naive total silently misses calls.
- [ ] **[BEST]** Guardrail-blocked calls (`finish_reason=content_filter`, 0 tokens) are recorded as **blocked calls**, not missing data.
- [ ] **[BEST]** Declare in the register whether helper or investigator calls count toward the run. Never exclude them only to improve a result.
- [ ] **[BONUS]** Inline admission ("is this run still under cap?" **before** the call) only if a genuine hook exists at an enforcement point. Otherwise label C16 **post-run** honestly (Cedar has no token attributes here).

### 3.3 C9, drift and performance
- [ ] **[MUST]** **Start baseline collection early.** It needs **closed UTC hours**: CloudWatch `AWS/Bedrock-AgentCore`, Latency **Average** and Errors **Sum**, period 3600, per runtime. Keep timestamps, units, statistic and dimensions with every value.
- [ ] **[MUST]** Alert the named owner for **every crossing window**, even when the aggregate exception allowance still passes. "Detection working does not erase the breach."
- [ ] **[BEST]** Use the correct direction: **higher latency is worse**, so relative increase = (M − B)/B. If the baseline error count is 0, use a **pre-declared absolute rule**; never divide by zero.
- [ ] **[BEST]** **A missing hour is UNKNOWN, not healthy**: raise a `monitoring-gap` finding. An hourly aggregate is never presented as the latency of one specific run.
- [ ] **[BEST]** Make the baseline comparable (same model alias, configuration and agent version), and **never silently replace it**. A new baseline gets a new version.
- [ ] **[BEST]** Treat a model swap (capability 4) as a deliberate experiment: it is a natural **drift case**, and the same register version has to detect it.

### 3.4 C7, automatic event recording
- [ ] **[MUST]** Take **expected events from an independent source** (scenario definition, workflow spec or twin), **not** from the logs that happened to survive.
- [ ] **[MUST]** Measure coverage as matched over expected **and** consecutive-event gaps against the declared limit; keep the exception fraction and **keep each exception visible** (the 8 ms case).
- [ ] **[BEST]** A missing middle event makes both of its gaps **unmeasurable**. Never bridge first-to-third into a falsely short gap. Zero expected events → NOT_ASSESSED, never "100%".
- [ ] **[BEST]** Only subtract timestamps from the **same clock and precision**. Negative or clock-skewed gaps are flagged, not passed.
- [ ] **[BEST]** Read the ledger from `/records?cid=` (**JSONL**); never parse `/timeline` as JSON.

### 3.5 Architecture and code quality (what judges probe)
- [ ] **[MUST]** **The register is out of the live path**: evaluators load a frozen version and never call a service mid-request.
- [ ] **[MUST]** **The evaluator is stateless**: a pure function of (inputs, rule version) → verdict + evidence bindings. It is re-runnable and deterministic.
- [ ] **[MUST]** **No threshold literals in control code.** Read every number from the register.
- [ ] **[MUST]** Don't design something that only works in the request path. Support all four transports:

  | Transport | Used for |
  |---|---|
  | `evaluate()` | in-path |
  | `emit()` | async records |
  | `callback()` | human / late verdicts: the ServiceNow queue |
  | `pull()` | scheduled: CloudWatch hours, AICT inventory |

- [ ] **[BONUS]** **Second enforcement point with nothing rewritten**: the same evaluator and Finding contract are invoked from a second EP (human approval queue = ServiceNow, tool call = Cedar/ToolConfig, or sub-agent handoff). In `architecture.md`, list exactly **which adapter changed and which code did not**.
- [ ] **[BEST]** Show that the design handles **all five control modes**:

  | Mode | Our example |
  |---|---|
  | Static | AI policy / register doc |
  | Scheduled | AICT inventory every 15 min; C9 hourly |
  | Event-driven | C7 |
  | In-transaction | C16 at the gateway |
  | Continuous | C9 vs frozen baseline |

- [ ] **[BEST]** Keep notifications and evidence writes **off the agent's execution path** (async), make them **idempotent** with deterministic ids (as `finding_id` is), and give every path a **terminal state** (no silent drops).
- [ ] **[BEST]** **Telemetry never judges, the ledger never interprets.** Keep raw captures separate from normalized facts and from verdicts.
- [ ] **[BEST]** Write tests for each evaluator with **good and bad cases**: exact-boundary values, missing data, duplicates, corrections, clock skew. Show them as part of "how we know the control works".

### 3.6 Evidence: generation, binding, storage, integrity
- [ ] **[MUST]** **Every record is bound** to `control.id` + `threshold.version` + `run.id`/window + `actor.id` + `emitted.at` + its source reference. A span or log line on its own is **not** evidence.
- [ ] **[MUST]** Cover **all governed actions in scope** (every model call, tool call, handoff and escalation in the run), not a convenient subset.
- [ ] **[MUST]** Make evidence **verifiable by a stranger**: raw source captures plus the exact query used (namespace, dimensions, time range, pagination complete) plus a capture time. The judge must not need us in the room.
- [ ] **[BEST]** Answer the **six auditor questions** for any incident in the event window (who, what, authorized, approved, integrity, reconstruct). Map each to a file (see SN-handoff §8.7).
- [ ] **[BEST]** **APPROVED for every asset in the chain**: export `.status.governance.approvals` for each **ModelConfig, ToolConfig and AgentConfig** used in the named runs, plus `AccessDenied` proof that the direct Bedrock path is closed.
- [ ] **[BEST]** **AUTHORIZED**: keep the Cedar/PDP decision lines (policy id, version, decision, action id) for **both replicas**, joined to gateway calls by `x-modaas-action-id` / trace id.
- [ ] **[BEST]** **INTEGRITY**:
  - raw captures are never edited, and corrections are new revisions;
  - capture the ledger's own verification output (including the forged write rejected with **401**);
  - generate the MANIFEST SHA-256 list;
  - record the S3 version id.
- [ ] **[BEST]** **RECONSTRUCT**: for each named run, render `cases/<control>_<run>.md` (or .html) with a time-ordered timeline: agent → gateway call → tool → ledger record → verdict → ServiceNow incident → response.
- [ ] **[BEST]** **Write a completeness statement per scope**: expected count, captured count, missing count, and why.
- [ ] **[BEST]** Use **UTC ISO-8601 everywhere**, and say which clock each timestamp came from.
- [ ] **[MUST]** No signatures, hash chains or Merkle trees (out of scope; wasted time).

### 3.7 The query tool and the 2-minute answer
- [ ] **[MUST]** One command answers **"was control X satisfied for run R / window T1–T2?"** in **< 2 minutes**. The judge asks; we operate; **no narration**.
- [ ] **[BEST]** The output shows:
  - rule, version, date and owner;
  - expected vs observed population;
  - measured value, formula and limit;
  - exceptions;
  - **verdict** (including BREACHED or INDETERMINATE with reasons);
  - gaps;
  - **resolvable record references**;
  - **human-loop line** (incident, assignee, delivered, response or silence);
  - AICT line.
- [ ] **[BEST]** It works **offline from the Evidence Pack**, with no live API calls during judging. It also supports **time-window** queries, not only run ids.
- [ ] **[BEST]** Prepare a **recorded demo** of the foundation as a backup in case the environment is slow on the day.

### 3.8 Agents (behaviour and governance)
- [ ] **[MUST]** Use **Nemotron only**, through the governed `modaas-agw` alias. Agents run on **AgentCore** (or in ServiceNow); approvals are genuine human attestations.
- [ ] **[MUST]** If an agent's decisions can't be traced, the entry scores nothing. **Every decision** carries a trace id or CID and leaves a ledger record.
- [ ] **[BEST]** **Close the judgment gap:**
  - S2 → `gather-evidence`, **name the deciding evidence**, propose a **reversible** action;
  - S3 → `escalate` (which creates an ESC incident);
  - keep S1 auto-resolving;
  - report score-run results as **diagnostics**, not as judging.
- [ ] **[BEST]** Inject credentials (gateway key, ledger token) and make the agent **fail closed**. Never print private reasoning (think-tags) as evidence; log only the final structured decision.
- [ ] **[BEST]** Name new agents **`ifabric_…`**. Record the model alias, resolved model id, image digest and CR generation per run, so the drift and approval questions are answerable.
- [ ] **[BEST]** Respect **100 requests/min and 2.5M tokens/h** across the account. Use bounded retries, and **count the retries** (C16).

### 3.9 Adversarial testing (Hostile and Rogue levels)
- [ ] **[BONUS]** Keep an **adversarial test log** (`evidence/adversarial/`). Each case records: attack, target control or EP, expected defence, **observed result, evidence refs, and what broke or what we changed**. Nemotron may generate the attacks.
- [ ] **[BEST]** **Hostile** cases (detection, safe degradation, unsafe action denied):
  - prompt injection → guardrail `content_filter`;
  - tampered tool or skill → Cedar deny;
  - conflicting context → agent `gather-evidence`;
  - injected delay → C7 gap breach.
- [ ] **[BEST]** **Rogue** cases (containment, evidence preservation, reconstruction):
  - direct Bedrock bypass → `AccessDenied`;
  - unauthorized tool → deny;
  - forged ledger write → 401;
  - deleted or tampered record → C7 coverage breach plus MANIFEST mismatch;
  - retry loop → C16 breach plus incident;
  - kill switch (`spec.paused`) → 404, with requested vs effective time recorded.
- [ ] **[BEST]** Attack **our own controls**: duplicated usage records (dedupe holds?), clock skew (flagged?), a threshold file edit (version mismatch detected?), and injected text in incident notes or logs (treated as data, never as instructions).

### 3.10 ServiceNow (Level 2 and Level 3)
- [ ] **[MUST]** **L2 live:** AICT Inventory shows our AgentCore runtimes (connection "iFabric Hackathon 2026"). Have **Execute Now** ready before the demo. Show Monitor sessions or traces if available; otherwise state the gap.
- [ ] **[MUST]** **Human loop:** every breach or escalation becomes an incident **assigned to the named owner**, with readback, response or silence, and an exported record.
- [ ] **[BEST]** **L3 chain:** one finding ID links the AWS evidence, the ServiceNow incident and the ServiceNow-native agent's analysis, plus that agent's **AICT trace**. Clearly label which model ran where (Nemotron on AWS; ServiceNow LLM in ServiceNow).
- [ ] **[BEST]** Close findings **only with a linked passing re-test**; an owner's "done" note is a response, not a closure. Close the test incident INC0010231 before judging.
- [ ] **[MUST]** Never touch other teams' records, connectors, agents or risk frameworks.

### 3.11 The gap list (scored, and it scores well)
- [ ] **[MUST]** Each gap states **what** couldn't be closed, **why**, **which claim or control it affects**, its **impact on the verdict**, and **what we would do next** ("I didn't have time, but this is how I would do it").
- [ ] **[BEST]** Include platform limits honestly:
  - no durable OTEL trace exporter;
  - TMF639 projection false;
  - AICT discovery scope;
  - Basic-auth failure → OAuth;
  - journal ACL;
  - C16 post-hoc rather than inline (if so);
  - hourly C9 granularity;
  - shared-instance naming.
- [ ] **[BEST]** **"Built properly: yes. Actually worked: no"** is a valid, high-scoring entry. Never hide a failed control behind a green dashboard.

### 3.12 Judging day and the pitch
- [ ] **[MUST]** Bring all six artefacts (§1.3) and the **named run ids written down beforehand**. Assemble the evening before; submit to S3 with readback.
- [ ] **[BEST]** **Pitch order (15 min):**
  1. **L1** foundation live: governed Nemotron call, guardrail block, approvals;
  2. **L2** ledger evidence + AICT inventory and traces;
  3. **L3** ServiceNow incident chain + ServiceNow agent;
  4. the controls (C16 → C7 → C9) with pass and breach runs;
  5. adversarial log;
  6. second EP;
  7. gap list.
- [ ] **[BEST]** **Rehearse twice** on both named runs, with someone **not** on the build team asking the questions.
- [ ] **[BEST]** Use a whiteboard photo or one-page architecture, **not slides** (a slide deck is out of scope and scores nothing).

### 3.13 Operations hygiene
- [ ] **[MUST]** Never put secrets (OAuth secret, gateway key, ledger token, IdeUrl/CockpitUrl, presigned URLs) in code, files, screenshots or chat.
- [ ] **[MUST]** **Back up** code (git) and evidence (team S3 bucket) regularly; the account is deleted after the event.
- [ ] **[BEST]** Pin and record versions (Python, the Strands trio, image digests). Keep a dated **decisions log**: what we chose, when, and why. It's useful in the pitch and in the gap list.
- [ ] **[BEST]** Stay within the protected-namespace rules (only the team Cedar ConfigMap in `modaas-system`) and use synthetic data only.

---

## 4. Scorecard: every scoring criterion, and how we max it

**How judging works:**
- **Gates first:** Levels 1 → 2 → 3, each needing the one before.
- Then **Axis 1 orders the field** (number of completed controls).
- **Axis 2 decides the winner** (quality).
- **Axis 3 separates ties** (bonuses).
- **Negative criteria** take marks off.
- The headline test over everything: **"the most auditable solution wins"**: every decision explainable, every risk controlled, every claim independently verifiable.

No official numeric weights were published. Score ourselves with the **self-check** column (✅ / ⚠️ / ❌) at every checkpoint, and fix ❌ items first, in table order.

### 4.1 Gates: the three levels (each must be shown live, in order)

| Criterion | What earns the maximum | How we demonstrate it to judges | Self-check |
|---|---|---|---|
| **L1 Foundation** (required, or nothing is judged) | The fault-resolution use case runs in Workshop Studio, **only through MoDaaS**: governed Nemotron alias via `modaas-agw`, guardrail active, CRs approved by a named human, ledger recording | Live or recorded: (1) a governed call returns `x-modaas-action-id` and usage; (2) a prompt attack gets `content_filter` with 0 tokens; (3) a direct Bedrock call gets `AccessDenied`; (4) CR approvals show the approver and attestation | ⬜ |
| **L2 Observability** (needs L1) | MoDaaS controls on + evidence in the **audit ledger** + **ServiceNow AI Control Tower** showing our agents (inventory, details, ideally Monitor traces) | AICT Inventory filtered to our connection "iFabric Hackathon 2026"; agent details; Monitor session or trace. Before the demo, click **Execute Now** to refresh. Ledger `/records?cid=` for the same run | ⬜ (inventory ✅; traces unknown) |
| **L3 Extended chain of evidence** (needs L1+L2) | One finding id links: AWS records → assessment → **ServiceNow incident** (owner, readback, response) → **ServiceNow-native agent's analysis + its AICT trace**; "other models where appropriate", clearly labelled | Open the C16 breach case: the gateway lines, then INC (assigned to Sree, RESPONDED or NO_RESPONSE_OBSERVED), then the SN agent's analysis, then its AICT trace, all carrying the same `finding_id` | ⬜ |

### 4.2 Axis 1: number of controls completed end to end (orders the field)

| Criterion | Max score | What "complete" means (all required) | Self-check |
|---|---|---|---|
| C16 per-run spend cap | **3 of 3 controls** = "the full set" (2 is ahead of 1; 0 = nothing to score) | **(a)** dated register entry with a named owner; **(b)** records bound to control, version and run at an enforcement point; **(c)** a reproducible evaluator; **(d)** one named **PASS** and one named **BREACH** run, same threshold; **(e)** the breach alerts the named owner (incident); **(f)** the query tool answers in under 2 min; **(g)** gaps recorded | ⬜ |
| C7 event recording | | Same (a)–(g); expected events come from an independent source | ⬜ |
| C9 drift and performance | | Same (a)–(g); frozen baseline, comparable closed windows, an alert per crossing | ⬜ |

**Rule:** finish one control **completely** before starting the next. A half-built control scores **0** on this axis.

### 4.3 Axis 2: quality (where the prize is decided)

| Sub-criterion | The judge's exact test | What earns the maximum | Self-check |
|---|---|---|---|
| **The live test** | "We name one control and one window and watch you produce the answer. Two minutes. If we have to trawl your logs, you lose the mark." "We ask; you operate. If you have to narrate, the tool isn't finished." | One command, offline from the Evidence Pack, prints: rule, version, date, owner; expected vs observed population; measured value vs limit; exceptions; **verdict**; gaps; resolvable record refs; human-loop line; AICT line (SN-handoff §8.7). Works for **run ids and time windows**. Rehearsed twice by someone outside the build | ⬜ |
| **The architecture** | "Would it survive a second enforcement point? Is the register out of the live path? Is the evaluator stateless? Does the control hold its own threshold?" | `architecture.md` shows: the register loaded as a frozen version (never queried mid-request); pure evaluators; **no threshold literals in code** (point to the register lookup); the 4 transports; **two EPs** (gateway + ServiceNow human queue) using the same Finding contract; all **5 control modes** mapped | ⬜ |
| **The evidence** | "Bound to a control, a threshold version and a run. Verifiable by somebody who is not you. Gaps recorded rather than left blank." | Every record carries `control.id`, `threshold.version`, `run.id`, `actor.id`, `emitted.at` and a source ref; raw captures + exact queries + capture times; a completeness statement per scope; MANIFEST SHA-256; S3 readback; the **six auditor questions** answerable from files alone (SN-handoff §8.7) | ⬜ |
| **The honesty** | "'Built properly: yes. Actually worked: no' is the most useful answer a team can bring. One honest failure scores better than everything green." | A detailed `gap-list.md` (what, why, affected claim, impact, next step) including platform limits (SN-handoff §11); INDETERMINATE used where data is missing; failed controls shown, not hidden | ⬜ |

### 4.4 Axis 3: bonus points (separate teams that are level)

| Bonus | Exact wording | What earns it fully | Self-check |
|---|---|---|---|
| **Extra controls** | "a second or third completed to the same standard" | All 3 controls meet every point of §4.2 | ⬜ |
| **Continuous compliance** | "a verdict formed inline, in the path, while it runs" | Best: a genuine `evaluate()` at an EP that can refuse (e.g. C16 admission). Partial: near-real-time evaluation on a short loop, with alerts within minutes, **labelled honestly** | ⬜ |
| **Adversarial testing** | "you attacked your own design and showed us what broke" | `evidence/adversarial/` log covering the Hostile and Rogue cases (§3.9). Each case: attack → expected defence → observed → evidence refs → **what broke and what we changed**. Nemotron-generated attacks are allowed | ⬜ |
| **Second enforcement point** | "the same architecture, moved, with nothing rewritten" | The same evaluator + Finding contract at EP2 (ServiceNow human approval queue via the S3 escalation, or tool-call Cedar). `architecture.md` lists **which adapter changed and which core code did not** | ⬜ (ServiceNow side ready) |

### 4.5 Negative criteria (each one costs marks; check before submitting)

| What loses marks | How we make sure we don't | Self-check |
|---|---|---|
| A threshold with no date, or dated after the test | Register frozen with version + date **before** assessed runs; Sree's approval timestamp in ServiceNow | ⬜ |
| Records covering only some of the governed actions | Completeness statement per scope (expected vs captured vs missing) for every model call, tool call, handoff and escalation | ⬜ |
| Evidence only our own team can verify | Raw captures + queries + README for a stranger + MANIFEST + S3; incident exports straight from ServiceNow | ⬜ |
| A finding closed without a passing re-test | Findings close only with a linked SATISFIED re-test assessment; owner notes are responses, not closures | ⬜ |
| A control that stores its own threshold | Thresholds only in `register.yaml`; code review checks for literals | ⬜ |
| A design that only works in the request path | ServiceNow, evidence and C9 are off-path (`emit`/`callback`/`pull`); show them in the architecture | ⬜ |
| A missing artefact ("if an artefact is missing we cannot score it") | All six in S3 (§1.3), checked against this list the evening before | ⬜ |

### 4.6 What the judges will actually do (prepare for each)

| Judge action | Our prepared answer | Self-check |
|---|---|---|
| "Show me control 16 for run FM-B" (or any control + named run) | Query tool → full answer on one screen in under 2 min (SN-handoff §8.7) | ⬜ |
| "Was control 9 satisfied between T1 and T2?" | Window query → every closed hour in range, crossings, coverage, alerts sent, owner response | ⬜ |
| They pick **an incident from our event window** and ask the six auditor questions | `cases/<control>_<run>` timeline + SN-handoff §8.7 mapping table: who acted, what it touched, authorized (Cedar line), approved (CR attestations + owner), integrity (ledger verify + MANIFEST), reconstruct (ordered timeline) | ⬜ |
| Alert levels: "show detection, safe degradation, denial (Hostile), and containment, preservation, reconstruction (Rogue)" | The adversarial log, with one evidence chain per case | ⬜ |
| "What could you not close?" | The gap list, read aloud confidently | ⬜ |
| The judgment gap: "do your agents still guess under ambiguity?" | S2 now returns gather-evidence + named evidence + reversible action (diagnostic score shown); S3 escalates → ESC incident; S1 still auto-resolves | ⬜ |

### 4.7 Extra points that make an entry stand out (all low effort, high signal)
1. **Same-ID chain everywhere:** the run id, `finding_id` and incident correlation id are visible on one screen. Judges can follow one id across AWS and ServiceNow.
2. **"Stranger" README:** a 1-page `evidence/README.md` that lets a judge verify a verdict without us (how to recompute C16 from the raw gateway lines, step by step).
3. **Pre-written `run-ids.txt`** with PASS and BREACH ids **and the time window**, timestamped before judging.
4. **Decision log:** dated notes of each threshold choice and change. Shows the governance "process" is real.
5. **Owner engagement shown:** at least one incident with a real owner response (RESPONDED) **and** at least one with recorded silence (NO_RESPONSE_OBSERVED after the cutoff). This demonstrates both outcomes the brief names.
6. **Kill-switch demo** (`spec.paused` → 404), with requested vs effective times. It's an extra enforcement point ("kill switch: everything, at once") at nearly no cost.
7. **Model swap as a drift experiment** (capability 4: change the model behind the alias without editing agents). C9 should detect it under the same register version, which makes a strong drift story.
8. **Recorded backup demo** of L1 → L2 → L3 in case live systems are slow.
9. **Whiteboard architecture photo** in the pack (explicitly accepted), showing EP1 (gateway), EP2 (ServiceNow human queue), the register out of the path, and the stateless evaluator.
10. **Practise the exact phrases the judges use:** "Show me control 16 for run FM-B", "Was control 9 satisfied for run FM-B?" The tool's output must answer these word for word.

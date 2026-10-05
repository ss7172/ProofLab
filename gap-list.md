# Gap list

*Draft started 2026-10-05, while working through the workshop and before our build. Entries change as we close gaps.*

Gap 1 is about agent judgment, the gap the challenge asks us to close. Gaps 2–9 are platform limits we found and verified. They bound what any Evidence Pack on this platform can prove, so each one says what an auditor can't do and how we would work around it.

---

### 1. A governed answer can still be wrong, and the recorded disposition is a keyword guess

**What's missing:** nothing in the governed path checks that an agent's answer is right, or that its disposition reflects a decision.

**Why:**
- We asked our own agent, `my-agent` (the kit template on `nemotron-super-120b`, tool `modaas-docs`), *"How does a ModelConfig get approved?"* (CID `my-agent-1791190861-638235`).
- It retrieved real documents (`search_docs`, then `get_doc` twice) and cited them, but answered wrongly: *"Canvas does not perform model approval; this belongs to the ML Ops pipeline…"*.
- It never named the actual mechanism, the two approval annotations (`modaas.tmforum.org/approver`, `modaas.tmforum.org/approval-attestation`). `hackathon-helper` answered the same question correctly (CID `hackathon-helper-1791189091-2633eb`).
- **Every control passed on the wrong answer:** approved agent, model and tool; one Cedar ALLOW per call; guardrail in the path; three ledger records.
- **The disposition is inferred, not decided.** The template's `classify_disposition()` matches keywords in the answer text. This answer was recorded as `auto-resolve` only because it contained *"After applying the ModelConfig CR"*.

**Impact:** an auditor can show that every call was governed and recorded, but not that the answer was grounded in what the tools returned, or why the agent chose its disposition.

**If you had one more day:** have the agent record which retrieved passage supports each claim, and choose gather-evidence or escalate, explicitly and with a recorded reason, when the retrieved text doesn't answer the question.

---

### 2. WHO acted: the platform's records can't tell agents apart

**What's missing:** a per-agent identity in the platform's own records.

**Why:**
- Every agent calls the gateway with the same team key, so every Cedar decision names `ServiceIdentity::"bootstrap-key"`. For example, all 7 of `my-agent`'s decisions and all 24 of a three-agent run's.
- Per-agent Keycloak identities exist (one `IdentityConfig` per agent), but none is provisioned (`listenerRegistered: false`).
- Every AgentCore runtime, ours included, runs as the same IAM role (`a-01-eks-cluster-agentcore-runtime`).

**Impact:** *"which identity acted, on whose behalf, with what scope?"* is answered by the agents' own ledger `actor` field, not by an independent record.

**If you had one more day:** corroborate the actor against per-runtime AgentCore records (each runtime has its own log group and metrics), and ask the platform team about provisioning per-agent clients, which the gateway already accepts as principals.

---

### 3. WHAT it touched: an agent can use tools it never declared

**What's missing:** runtime enforcement of an agent's declared tools.

**Why:**
- The gateway evaluates the *called* tool's Cedar policy, not the caller's declaration, and the shared AgentCore Gateway exposes every tool on every route.
- In ordinary S1 runs (CIDs `fault-1791175626-0d34e2` and `fault-1791179282-8ef1a8`), the network agent, declared with `network-twin` only, also called `customer-records` and `runbook-lookup`. Every call was allowed.
- `new-agent.sh --tool` doesn't write the tool into `dependsOn.tools`, so our own agent's declaration doesn't name the tool it uses.

**Impact:** an agent's declaration can't serve as its scope. *"What did it touch?"* has to come from the gateway's `tools/call` lines; the evidence log does flag such calls with `route_alias`.

**If you had one more day:** compare each run's `tools/call` lines with the agent's declared tools and report out-of-scope calls as findings.

---

### 4. AUTHORIZED: calls the platform refused are recorded as ALLOW

**What's missing:** the outcome of a refusal (the guardrail's verdict, or the kill switch) in the decision record.

**Why:**
- Cedar decides before the model runs. In a direct gateway probe (Module 6, not an agent run), a prompt attack that the guardrail then blocked was recorded as `decision=ALLOW`, both in the policy-decision log and in `/modaas/evidence`, with no guardrail field.
- The block shows only in the gateway's line for that call: `finish_reason=content_filter`, 0 tokens.
- **The same holds through our own agent** (Module 9 Step 3, CID `my-agent-1791191546-6aa5dd`):
  - the guardrail blocked the attack (*"Input blocked by policy."*, 0 tokens)
  - the policy decision and `/modaas/evidence` both say `ALLOW`, with no guardrail field
  - the agent's ledger records `http_status=200` and `disposition=undetermined`
  - No record anywhere says a guardrail acted.
- **The kill switch is recorded the same way** (Module 9 Step 3: `nemotron-super-120b` paused at 09:13:04 UTC; CID `my-agent-1791191585-4d9744`):
  - the agent's call was refused within 2 s (HTTP 404, route withdrawn)
  - but `/modaas/evidence` and the policy-decision log record `decision=ALLOW` (policy `model-nemotron-super-120b`, version 331993)
  - the gateway's record joins only by trace id: the pod's own 404 line has no run, trace or action id, and its durable copy in `/aws/modaas/gateway` (trace `f5140819…`) shows a bare `404` on `/v1/chat/completions`, with no run id, model or reason
  - Only the agent's own ledger says `disposition=refused`.
- The reference agents write no guardrail verdict to the ledger, so the grader's guardrail check fails on every run.

**Impact:** an auditor reading the platform's decision records would count a blocked attack, and a call stopped by the kill switch, as allowed calls. The only record that names either refusal is written by the agent itself. On the platform side there is just a 0-token answer (the guardrail) or a bare 404 joinable only by trace id (the pause).

**If you had one more day:** join each decision to its gateway line (by action id, or by trace id where the line has none) and report the real outcome per call: served, blocked by guardrail, or refused by pause.

---

### 5. APPROVED: approvals are self-asserted and don't follow changes

**What's missing:** an approval record that is attributable and covers the version that actually ran.

**Why:**
- An approval is two free-text annotations, stored with an empty `signature`, and EKS audit logging is off. So who set them isn't recorded independently.
- Changing an approved agent's model needed no re-review (the Module 7 swap). The guide states the same for image changes, from its own measurement; we haven't tested it.
- The "re-attest" annotation added no approval record. The IT agent's only approval (04:37 UTC) predates its model change (05:47 UTC).

**Impact:** *"attestation for every asset in the chain?"* can return an attestation that doesn't cover what ran.

**If you had one more day:** record the generation, model and image each approval covers, and flag runs whose running version is newer than the last approval.

---

### 6. INTEGRITY: the ledger can't show it wasn't altered

**What's missing:** tamper evidence for the evidence ledger.

**Why:** the audit store has no signatures or hash chain, and its write token sits in plain text in every AgentConfig spec. Signing and hash chains are out of scope for this challenge.

**Impact:** *"can you show the records were not altered?"* can be answered by corroboration, not proof.

**If you had one more day:** cross-check each ledger record against surfaces written outside the agent (the gateway line, the policy decision, `/modaas/evidence`, X-Ray) and report any mismatch.

---

### 7. RECONSTRUCT: one run is spread across stores with no shared durable key

**What's missing:** a single durable key that joins every record of a run.

**Why:**
- The durable gateway log (`/aws/modaas/gateway`) has no run id; only the gateway pod's short-lived output does.
- Ledger records carry trace ids the agents mint themselves, which don't match the run's trace.
- The gateway pod's lines for refused calls carry no run id or action id. The durable copy of the kill-switch 404 keeps only a trace id. A fail-closed refusal in S1 (`fault-1791175626-0d34e2`) appears in `/modaas/evidence`, but the ledger reports it as an HTTP 500 on the model.
- The S2 runaway (`fault-1791177342-d3f892`: 174 model calls, 1,999,001 tokens) looks like 16 ordinary ledger records.

**Impact:** replaying a run needs a multi-step join (trace id → `/modaas/evidence` correlation id), and a refusal or a loop can be missed when reading the ledger alone.

**If you had one more day:** build that join once, and store the reconstructed timeline of each run in the Evidence Pack.

---

### 8. No platform limit stops a slow runaway in time

**What's missing:** a per-run spend limit.

**Why:**
- The only limits are account-wide: 100 model requests a minute and 2.5M tokens an hour.
- The S2 loop peaked at 49 model calls a minute, so the request limit never engaged, yet it used 80% of the hourly token budget in under five minutes.
- Pausing a model took 33–41 s to take effect, and Cedar keeps no state it could count with.

**Impact:** one run can exhaust the team's shared budget before any platform control acts.

**If you had one more day:** this is what our control 16 (a per-run token cap) is for. Once it's built, this entry will record only what the cap can't cover.

---

### 9. Customer data in agent spans and in plain-HTTP traffic, with no classification to gate it

**What's missing:** a data classification on the tool that returns customer records, and protection for what the agents send and log.

**Why:**
- `customer-records` declares no data classification, so its own "restricted" Cedar rule can never fire.
- The agents' spans store the full prompt context, including customer records, in CloudWatch Logs.
- Every agent calls the gateway's public endpoint over plain HTTP, so the team key travels unencrypted on every model and tool call. A TLS listener is configured (:8443), but we haven't tested it.

**Impact:** an auditor can't show that customer data was handled under a declared classification, or that credentials and prompts were protected in transit and at rest.

**If you had one more day:** classify the tool, decide deliberately what our agent's spans keep (and say so), and ask for agents to be wired to the TLS listener.

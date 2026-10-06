# Gap list: team iFabric

*One file, two sections, each in its own format. Section A is Arth's, merged as handed over (handoffs/ifabric-handoff-3, unchanged). Section B is ours. Status: drafted 2026-10-06 at build time; no named run has happened yet, so every "what we show instead" below is a plan, not a result. Statuses are updated before each submit.*

## A. ServiceNow, AI Control Tower and the Assurance Agent

**A1. AICT discovery scope**
- **What:** AICT discovers AgentCore runtimes, Bedrock agents and SageMaker models only. It does not discover EKS pods, MCP servers, MoDaaS guardrails, or which ModelConfig served a call (all calls use one gateway IAM principal).
- **Why:** connector design (read-only role over those AWS APIs).
- **Affects:** L2 observability.
- **Impact:** the inventory is partial; per-call attribution comes from gateway and ledger records, not AICT.
- **Next:** extend the connector, or push call metadata to AICT via a custom integration.

**A2. AICT freshness**
- **What:** the inventory refreshes every 15 minutes, plus about 4 minutes of run time.
- **Why:** scheduled import.
- **Affects:** L2 live demo.
- **Impact:** new runtimes appear with a delay; we click **Execute Now** before the demo.
- **Next:** event-driven import.

**A3. AICT Monitor traces**
- **What:** as of 2026-10-05, AICT Monitor showed only ServiceNow-native sessions, none from our AWS runtimes.
- **Why:** traces from AgentCore did not reach AICT Monitor during our check.
- **Affects:** L2 (traces) and L3 (agent trace).
- **Impact:** we evidence agent activity with the inventory plus gateway and ledger records rather than AICT traces.
- **Next:** re-check after the named runs; if still absent, trace export to the connector's log group.
- **Status:** `<update before submission>`

**A4. Shared ServiceNow instance**
- **What:** reference agents have identical names across teams.
- **Why:** shared hackathon instance.
- **Affects:** L2 attribution.
- **Impact:** ours are identified by our connection's import timestamps and the `ifabric` prefix; we touch only `[iFabric]` incidents created by `ifabric.integration`.
- **Next:** a dedicated instance.

**A5. Script authentication**
- **What:** Basic auth was rejected (401) for both the participant and the integration user. We switched to OAuth client credentials and enabled the instance property `glide.oauth.inbound.client.credential.grant_type.enabled` (logged for transparency; facilitators informed).
- **Why:** instance MFA and auth policy.
- **Affects:** integration setup.
- **Impact:** none on verdicts.
- **Next:** per-team OAuth apps provisioned by the organizers.

**A6. Human response**
- **What:** a human reply is not required. Silence is recorded as `NO_RESPONSE_OBSERVED` only after the stated cutoff; unreadable history is `RESPONSE_UNKNOWN`, never treated as silence.
- **Why:** brief, out of scope.
- **Affects:** human loop.
- **Impact:** both outcomes are evidence.
- **Next:** none needed.

**A7. Delivery semantics**
- **What:** `DELIVERED` means read back with the right correlation id and assignee. It does not prove the human read it; only a note or status change proves engagement.
- **Why:** platform limit.
- **Affects:** "who was told".
- **Impact:** we claim delivery, not reading.
- **Next:** read receipts / acknowledgement task.

**A8. Note-level response detail**
- **What:** the `itil` integration user cannot read `sys_journal_field` rows (the ACL returns 0 rows, no error). Owner responses are detected from the incident's last update (`at_basis: last_update`, verified live). Notes are exported as display text.
- **Why:** least-privilege ACL.
- **Affects:** response timing detail.
- **Impact:** a reply followed by a later update by someone else can be hidden from a live check. Mitigation: `check` on a short loop; a logged `RESPONDED` is sticky.
- **Next:** a scoped read role for journal entries.

**A9. Assurance Agent location**
- **What:** the facilitators require Nemotron for the Assurance Agent. Nemotron is reachable only through `modaas-agw` (no public endpoints), and ServiceNow AI agents cannot use it on this instance. So the agent runs on AWS and writes its analysis into ServiceNow. A ServiceNow-native prototype (ServiceNow LLM) was built, tested once and **deactivated**; it is kept as superseded history only.
- **Why:** platform and model rules.
- **Affects:** L3.
- **Impact:** none on verdicts; the agent is outside ServiceNow but its output and evidence live there.
- **Next:** a ServiceNow-hosted agent once Nemotron is available as an instance provider.

**A10. AICT visibility of the Assurance Agent**
- **What:** only its AgentCore runtime (`ifabric_assurance_agent`) is an AICT asset. Direct governed gateway calls (backend `gateway`) are ledger-recorded but are not AICT assets.
- **Affects:** L3 trace.
- **Impact:** the AICT line exists only after the AgentCore deploy.
- **Next:** deploy before the named runs.
- **Status:** `<update>`

**A11. Note authorship**
- **What:** the analysis note is written by the integration user ("iFabric Integration"). The model and the call are identified by the note's `Model:` provenance line (alias, model id, gateway action id) and the run record.
- **Why:** secrets stay out of the agent runtime.
- **Affects:** attribution.
- **Impact:** none.
- **Next:** a dedicated identity for the writer.

**A12. Model variance**
- **What:** Nemotron may echo a fact wrongly. Such runs are **REFUSED** (nothing written) and shown as failures, never hidden.
- **Why:** LLM behaviour.
- **Affects:** L3 completeness.
- **Impact:** a case can show "no analysis" with the reason.
- **Next:** a larger approved alias, or prompt tuning, under the same checks.

**A13. Forged notes**
- **What:** anyone with ServiceNow write access can add a look-alike note, even with a fake header and timestamp. It is never trusted: a note counts only if its SHA-256 is in our delivery log. The log is therefore a trust anchor and is in the MANIFEST.
- **Affects:** L3 integrity.
- **Impact:** none.
- **Next:** server-side signing of notes (out of scope).

**A14. Display time zone**
- **What:** ServiceNow display times are in the reading user's time zone; our own timestamps are UTC (`…Z`).
- **Affects:** reconstruction.
- **Impact:** none if read with this note.
- **Next:** request UTC display values.

**A15. Shown vs proven**
- **What:**
  - the agent's refusal and guardrail paths are proven by tests (152 against fakes);
  - the ServiceNow write path was verified live on 2026-10-05 (INC0010232), with a TEST stand-in instead of the model:
    - note written, read back unchanged (SHA-256 matched), real journal parsed, re-run SKIPPED, five sections computed;
    - evidence in `servicenow/wiring-tests/assurance-agent-roundtrip/`;
  - `<list which were demonstrated live: e.g. a live REFUSED on an injected ticket, a live BLOCKED>`;
  - `<the first live Nemotron WRITTEN run: date/INC>`.
- **Status:** `<update before submission>`

**A16. Test incidents**
- **What:** INC0010231 and INC0010232 are **wiring tests** (`kind: wiring-test`, threshold version `TEST`), excluded from all verdicts and closed with resolution "adapter wiring test". Their records are in `servicenow/wiring-tests/` and never mixed into the production delivery log.
- **Status:** `<closed on …>`


**A17. Agent movement and policy depend on evaluator context**
- **What:** movement, the route rule (M1/P8), P1 (measured vs limit) and P2/P3 (register) are computed only from the `measured`, `limit`, `register` and `trace` the evaluator attaches to a finding.
- **Why:** the Assurance Agent doesn't observe network traffic; it checks the record it is given.
- **Affects:** L3 assurance analysis.
- **Impact:** where context is missing the checks show **unknown** (never pass); the route rule is only as complete as the trace. `<list named runs without a trace, or "none">`
- **Next:** emit the trace from the gateway itself (every `x-modaas-action-id` with source and target zone), so it can't be omitted.

**A18. Owner-response check before the cutoff**
- **What:** until the owner replies or the cutoff passes, P5 is "unknown: pending until the cutoff", so policy alignment reads 7/8 or lower.
- **Impact:** none on the verdict; it is the honest state of the human loop.
- **Status:** `<final P5 per named run after the final check>`

---

## B. AWS agents, controls and the guardrails design (the build team)

*Started 2026-10-05, while working through the workshop and before the build. Entries 1 to 11 are verified platform limits, except 1 and 10, which are about agent judgment, the gap the challenge asks us to close. Platform limits bound what any Evidence Pack on this platform can prove, so each one says what an auditor can't do and how we would work around it. Entries B12 onward are the design's own gaps, the rails' gaps, and the process gaps found while vetting.*

**Corrections to section A.** Section A above is byte-identical to Arth's handed-over text. Three wordings in it are corrected by our checks (`architecture/work/14` R-18); read them with these corrections:
- A1 says all calls use "one gateway IAM principal". The principal is one API-key identity, `ServiceIdentity::"bootstrap-key"` (entry 2 below).
- A3's cause: AICT's usage query filters `InvokeAgent` while our traffic is `InvokeAgentRuntime`, and Monitor covers Managed agents only. Its next step, "trace export to the connector's log group", names a group that belongs to the facilitators; the runtime role can write only to `/aws/bedrock-agentcore/*`.
- A10 says direct gateway calls are "ledger-recorded". The audit ledger holds only records our code writes; a direct gateway call is recorded by the platform in `aws/spans` and `/modaas/evidence`, keyed by action id.

**Dropped, on purpose.** The playbook's prompt B1 ("no durable exporter") is false: the gateway's spans are durable (30 days, with run id and tokens; entry 7). It is not listed here.

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
- The guide's suggested WHO source, the `modaas-authz` pod log, holds no per-call records, only its startup lines. The per-call identity is in `/modaas/evidence`, and there every authenticated call names `bootstrap-key`.
- Per-agent Keycloak identities exist (one `IdentityConfig` per agent), but none is provisioned (`listenerRegistered: false`).
- Every AgentCore runtime, ours included, runs as the same IAM role (`a-01-eks-cluster-agentcore-runtime`).
- Nor can a guardrail be chosen per agent: each model alias carries one fixed Bedrock guardrail (the two our agents use filter only prompt attacks, on input), and participants are explicitly denied creating or editing guardrails. An agent gets a different guardrail only by calling a different model alias.

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
  - The only record outside the agent that says a guardrail acted is AWS's own model-call log (`/aws/bedrock/aict-invocations`), which reads `Guardrail blocked.` for that call. It carries no run id, so it joins the run only by time and model (corrected 2026-10-05 after live re-check).
- **The kill switch is recorded the same way** (Module 9 Step 3: `nemotron-super-120b` paused at 09:13:04 UTC; CID `my-agent-1791191585-4d9744`):
  - the agent's call was refused within 2 s (HTTP 404, route withdrawn)
  - but `/modaas/evidence` and the policy-decision log record `decision=ALLOW` (policy `model-nemotron-super-120b`, version 331993)
  - the gateway's record joins only by trace id: the pod's own 404 line carries a trace id (`f5140819…`, the evidence record's) but no run id or action id, and its durable copy in `/aws/modaas/gateway` (same trace) shows a bare `404` on `/v1/chat/completions`, with no run id, model or reason
  - that trace id joins the 404 to the run through the policy decision and its `/modaas/evidence` record, which carries the run's correlation id and records the call as `ALLOW`
  - Only the agent's own ledger says `disposition=refused`.
- The reference agents write no guardrail verdict to the ledger, so the grader's guardrail check fails on every run.

**Impact:** an auditor reading the platform's decision records would count a blocked attack, and a call stopped by the kill switch, as allowed calls. The only records that name either refusal are the agent's own and, for the guardrail only, AWS's model-call log, which has no run id. On the platform side there is just a 0-token answer (the guardrail) or a bare 404 joinable only by trace id (the pause).

**If you had one more day:** join each decision to its gateway line (by action id, or by trace id where the line has none) and report the real outcome per call: served, blocked by guardrail, or refused by pause.

---

### 5. APPROVED: approvals are self-asserted and don't follow changes

**What's missing:** an approval record that is attributable and covers the version that actually ran.

**Why:**
- An approval is two free-text annotations, stored with an empty `signature` (all 18 approval records in the cluster, re-checked 2026-10-05), and EKS control-plane logging, audit included, is off for all five log types. So who set them isn't recorded independently.
- Changing an approved agent's model needed no re-review (the Module 7 swap). The guide states the same for image changes, from its own measurement; we haven't tested it.
- The "re-attest" annotation added no approval record. The IT agent's only approval (04:37 UTC) predates its model change (05:47 UTC).
- So the IT and network agents now run generation 2 on a generation-1 approval: the IT agent since its model swap, the network agent since an added environment variable (04:38 UTC). Each still holds its single approval, and the approval record stores no generation (live, 2026-10-05).

**Impact:** *"attestation for every asset in the chain?"* can return an attestation that doesn't cover what ran.

**If you had one more day:** record the generation, model and image each approval covers, and flag runs whose running version is newer than the last approval.

---

### 6. INTEGRITY: the ledger can't show it wasn't altered

**What's missing:** tamper evidence for the evidence ledger.

**Why:**
- The audit store has no signatures or hash chain, and its write token sits in plain text in every AgentConfig spec. Signing and hash chains are out of scope for this challenge.
- It has no verification route either: its source exposes only `/healthz`, `/records`, `/timeline` and a write.
- Participants can also read the write token from each agent runtime's environment variables (`get-agent-runtime`), not only from the AgentConfig specs.
- The kit's own evidence pull copies the token into the Evidence Pack: `pull-evidence.sh` (line 78) saves the full Model/Tool/AgentConfig objects, specs included, as `cr-status.json`. `submit.sh` then zips the evidence folder as it is, uploads it to the team evidence bucket (stack output `TeamEvidenceBucketName`), which the judges read, and leaves a copy of the zip in the directory it was run from.
- Its timestamps are the writer's: the store keeps any `ts` a writer sends and assigns only `seq` itself, so a forged record can also carry a chosen time.
- The hand-in bucket can vouch for upload times, not for content (corrected 2026-10-05, from live reads during the architecture work). CloudTrail shows it was created versioned (2026-10-04 10:19 UTC), with old versions kept 7 days, server access logging to a bucket participants can't reach, and no Object Lock. Participants can't read those settings or list versions (AccessDenied), and can't remove a version: a delete only adds a delete marker, and an overwrite keeps the old version for 7 days. Since 2026-10-05 18:10 UTC the IDE role can list and read versions. `submit.sh` prints no `VersionId`. So the upload time and version history are set by AWS, but they can't show the records were unaltered before upload.

**Impact:** *"can you show the records were not altered?"* can be answered by corroboration, not proof.

**If you had one more day:** cross-check each ledger record against surfaces written outside the agent (the gateway line, the policy decision, `/modaas/evidence`, X-Ray) and report any mismatch.

---

### 7. RECONSTRUCT: a run's records sit in stores that only partly share a durable key

**What's missing:** the run's key on every record of a run, refusals included.

**Why:**
- A durable shared key does exist for a run's model and tool calls. The gateway emits one trace span per request, which lands in CloudWatch Logs `aws/spans` and is kept 30 days, carrying the run id (the agents' correlation id), an action id and, for model calls, the token counts. For the S2 run (`fault-1791177342-d3f892`, 2026-10-05 05:15–05:20 UTC) that is 353 spans and 1,999,001 tokens, exactly what the gateway pod reported. `/modaas/evidence` (30 days) and the ledger carry the run id too.
- The durable copy of the gateway's access log (`/aws/modaas/gateway`, 7 days) carries no run id or action id: none of its 1,630 records on 2026-10-05. The installer meant that copy to match the pod's output, so this is a build gap; we couldn't find the cause.
- The policy-decision and authz logs live only on their pods; neither is shipped to CloudWatch.
- Ledger records carry trace ids the agents mint themselves, which don't match the run's trace.
- Refused calls carry no run id or action id on the gateway line; they join to the run only by trace id, via the policy decision and its `/modaas/evidence` record. A fail-closed refusal in S1 (`fault-1791175626-0d34e2`) appears in `/modaas/evidence`, but the ledger reports it as an HTTP 500 on the model.
- The S2 runaway (174 model calls, 1,999,001 tokens) reads as 16 ordinary ledger records.

**Impact:** governed calls can be replayed by run id from the gateway's spans, but refusals have to be joined by trace id, through the policy decision and its `/modaas/evidence` record, and a refusal or a loop can be missed when reading the ledger alone. The span copy also ends after 30 days, or earlier if the event account is torn down.

**If you had one more day:** build the per-run join once, from `aws/spans` by run id (not X-Ray, which truncates long runs): every governed call with its action id, model and tokens, each linked to its `/modaas/evidence` decision by action id, with refused calls added by trace id. Store the reconstructed timeline of each run in the Evidence Pack.

---

### 8. No platform limit stops a slow runaway in time

**What's missing:** a per-run spend limit.

**Why:**
- The only limits are account-wide: 100 model requests a minute and 2.5M tokens an hour.
- The S2 loop peaked at 49 model calls a minute, so the request limit never engaged, yet it used 80% of the hourly token budget in under five minutes.
- Pausing a model took 33–41 s to take effect, and Cedar keeps no state it could count with.
- Work can also double without anyone asking for it. In S2 the IT agent was invoked twice in one session: two IT intents in the ledger 180 s apart, and two AWS invocation records with the same session id, ending 15 s apart (05:20:24 and 05:20:39 UTC). That fits the AWS CLI re-sending the call after the kit's 180 s read timeout. Both copies ran, the run's 1,999,001 tokens span both, and no platform limit stops a retry.

**Impact:** one run can exhaust the team's shared budget before any platform control acts.

**If you had one more day:** this is what our control 16 (a per-run token cap) is for. Once it's built, this entry will record only what the cap can't cover.

---

### 9. Customer data in agent spans and in plain-HTTP traffic, with no classification to gate it

**What's missing:** a data classification on the tool that returns customer records, and protection for what the agents send and log.

**Why:**
- `customer-records` declares no data classification, so its own "restricted" Cedar rule can never fire.
- The agents' spans store the full prompt context, including customer records, in CloudWatch Logs.
- Every agent calls the gateway's public endpoint over plain HTTP, so the team key travels unencrypted on every model and tool call.
- The TLS listener (:8443) serves model calls only, and its certificate is self-signed with a placeholder hostname (`<PERIMETER-HOST>`) that the installer was meant to replace and never did (TLS handshake without credentials, 2026-10-05), so agents can't use it as deployed: a client that checks certificates rejects it. Tool calls have no TLS listener at all.

**Impact:** an auditor can't show that customer data was handled under a declared classification, or that credentials and prompts were protected in transit and at rest.

**If you had one more day:** classify the tool, decide deliberately what our agent's spans keep (and say so), and ask the platform team for a real certificate, a TLS route for tool calls, and agents wired to both.

---

### 10. The network agent asks the twin the wrong question, gets nothing back, and carries on

**What's missing:** any check that the evidence an agent gathered actually answered its question.

**Why:**
- The `network-twin` tool answers only for exact site ids. Its dataset has three: `SITE-DEN-12`, `SITE-DEN-09` and `SITE-PHX-04`.
- In the last 24 hours, the reference network agent's own spans show 40 tool results reading *"no twin data for site"*. The agent had asked with **element ids**: `DU-DEN-12-A` (29 times), `RTR-DEN-12-CORE` (9) and `RTR-PHX-04-CORE` (7).
- Each of those calls was a governed `tools/call` that returned HTTP 200 and was allowed. The agent went on to record a disposition anyway.
- The S2 scenario (transport congestion) names no site at all, so the twin can't be its ground truth.

**Impact:** an auditor sees that the agent consulted the network twin (a governed, allowed, successful call) but can't see that the twin returned nothing usable. The ledger doesn't record it, and the conclusion wasn't grounded in the twin.

**If you had one more day:** have the agent resolve each element to its site before querying, record whether each tool result actually answered the question, and choose gather-evidence or escalate when key evidence comes back empty.

---

### 11. A governed tool's code can change under its approval

**What's missing:** a link between a tool's approval and the code that actually answers.

**Why:**
- Each Lambda-backed ToolConfig points at its function with **no version qualifier**, so every call runs the latest code. That holds for all seven: `network-twin`, `customer-records`, `runbook-lookup`, `evidence-lookup`, `cluster-status`, `cr-author` and `helper-docs`.
- The approval is an annotation. For `network-twin`: `system-admin`, *"Approved by the workshop platform at install"*, 2026-10-04 10:40 UTC, empty `signature`. It records nothing about the code it approved.
- The live participant IAM policy (`participant-permissions-policy-1`, v1) allows `lambda:UpdateFunctionCode`, `UpdateFunctionConfiguration`, `InvokeFunction`, `AddPermission` and `DeleteFunction` on `arn:aws:lambda:*:*:function:team-*`, with no condition. Every tool function is named `team-a61f5-…`.
- `GetFunction` on the twin's function succeeds for that role. We haven't attempted a write, so whether an organisation-level policy would block one is untested.
- The guide itself warns: *"poison the twin and every agent downstream acts on poisoned reality."*

**Impact:** an auditor can't show that the tool which answered during a run was the one that was approved. A replaced tool, such as a poisoned twin, would keep its approval, and no record would show the change.

**If you had one more day:** record each tool function's `CodeSha256` (readable with `GetFunctionConfiguration`) alongside its approval, and check it at run time, flagging any run where the code differs.

---

## B12. Design gaps the architecture records rather than closes

*Source: `architecture/ARCHITECTURE.md` section 15.2. Columns: the gap; why it stays; what we plan to show instead (a design, not yet a result).*

| Gap | Why it stays | What we plan to show instead |
|---|---|---|
| WHO: one shared principal (gap 2); per-agent Cedar isn't wired [07 GS-27] | Platform | Our actor records + the AWS-written `InvokeAgentRuntime` records, which carry the caller's role, the runtime and the run (an exact join by baggage CID + session id [10-f11]) |
| WHAT: undeclared tools (gap 3) | Platform | Detection (EP-3, `route_alias`); a Cedar refusal only where a rule exists on the called tool (D15) |
| AUTHORIZED: refusals recorded as ALLOW (gap 4) | Platform | Real-outcome records; for a guardrail block, also the AWS model-call record's "Guardrail blocked." (joined by time, role and model) [10-f11 §4.4] |
| APPROVED: self-asserted approvals that don't follow changes (gap 5). **Live today: the reference IT and network agents run generation 2 on a generation-1 approval** [07 GS-22]; edits, model swaps and env patches add no approval record [05 AR-15] | Platform | EP-0's check (model + generation + runtime version against `ApprovalRecorded.observedGeneration`); stale-approval flags; the owner's ServiceNow approval of the register |
| INTEGRITY: the ledger can't show non-alteration (gap 6) | Platform; crypto is out of scope | Corroboration + AWS-set times + the MANIFEST |
| RECONSTRUCT: refusals lack run ids; the gateway copy has no ids (gap 7); the AWS model-call records (`Converse*`) carry no run, session or trace id either. (The AWS **invocation** records do carry the run [10-f11].) | Platform | The trace-id join; the time + role + model join for model-call records, whose token counts match the spans exactly |
| No platform per-run halt (gap 8). **The reference S2's 1,999,001 tokens span two concurrent IT invocations of one session:** the kit's CLI re-sent the invocation after its 180 s read timeout, and nothing in the platform stops a duplicate [05 AR-18; 10-f11 §4.3] | Platform | Our inline check covers our agents only; observe mode relies on the safety ceiling. Exactly one invocation per handoff (`AWS_MAX_ATTEMPTS=1`) and the agent-side duplicate guard (§7) |
| Plain HTTP; customer data in spans (gap 9). **The :8443 TLS listener's certificate is a self-signed placeholder** (its SAN is literally `<PERIMETER-HOST>`), it serves model routes only, and MCP has no TLS listener, so the gateway key crosses in clear text on every tool call [07 GS-25] | Platform | Digests in our records; span-content redaction in our agents (§7.1); pack hygiene |
| The twin can't make breaches (gap 10). Re-checked after the organisers' twin fix: unchanged (same code, same packaged data) [09] | Platform | Declared levers (§5.5) |
| Tool code can change under approval (gap 11) | Platform | A CodeSha256 baseline at the freeze + CloudTrail code-update events (readable: OC-13 closed). The organisers audit the same Lambdas (`GetFunction` on all seven, 21:29–21:34 UTC [09 §7]) |
| **The gateway guardrail is fixed, narrow and not ours:** one per model alias; PROMPT_ATTACK on input only (PII only on the `-helper` alias); no create or update (an explicit IAM deny), no per-call choice, no guardrail on tool routes, no NVIDIA safety model [07 GS-15, GS-16; guardrails/02 §0, GR-06, GR-09] | Platform | The guardrail id and version recorded per run; BLOCKED shown next to the platform's ALLOW; Hostile cases beyond prompt attack rest on the agents' judgment and in-agent rails (§6) |
| **An AgentConfig pause is a record, not a stop:** the runtime stays READY and direct invocations still work [07 GS-14] | Platform | EP-0 declines a run on a paused agent; containment by a model pause (ADV-R-08) or C16 `enforce` |
| **The ledger server is fragile:** one single-threaded replica with 256Mi, whole-file parsing on every GET, no fsync; its volume is deleted with the stack [06 C5, C6] | Platform | Per-CID exports, no full GET during a run, the AWS-timestamped stdout witness, the export before teardown |
| **Shared spaces:** the IDE is not team-exclusive (seven organiser shell commands on 2026-10-05), and the organisers write into our evidence bucket and read our ledger [09 §7] | Organisers | The pack is built on the laptop; we write only under `ifabric/` and `submissions/`; the `facilitator/` objects are left alone and never treated as our evidence |
| The inline tally trusts the run envelope | A design limit: the frame allows no store read in the path | The floor is the control of record (ADV-R-06) |
| AICT's usage count is 0; Monitor covers Managed agents only. Its usage query filters `InvokeAgent` (our traffic is `InvokeAgentRuntime`) and groups by `requestParameters.sessionId`, which is always empty [08 AI-03; 10-f11 §1] | AICT | Recorded; the AWS-written invocation log used instead, joined exactly by `responseElements` |
| Others' admission decisions are invisible (EKS audit off) | Platform | Our own applies, recorded by the deploy wrapper |
| C9: per-run attribution needs spaced runs; the baseline n is small; the swap lever is unproven | Time; platform | Declared in the register; pilot P8 |
| Separation of duties: the owner also builds, and also rates the risks she owns; AI reviewers are not the GRC assurance role | Team size | The roles table (§12.2): Sree is accountable management and operations; Arth is assurance (a "reviewed" note on each T2 before Sree approves; the assurance check on each control result); GRC is vacant (R-D-02). If Arth is unavailable overnight, each check he would have made is recorded "not independently reviewed" |
| AICT approvals carry no approver, time or version link: "Approved" is an editable Status [AICT notes §2.6] | AICT | The repo inventory is the source (D14); AICT gets a mirror of owners and the tier |
| Owners and approvals of platform components (models, shared tools) are not confirmed by their owners | Organisers | The inventory marks them as our declaration, with the CR approval it read (§3.10) |
| The EU AI Act tier has no primary source in hand (OC-21) | Sources | Recorded as UNVERIFIED and cited to the playbook line (§3.9) |
| Organiser-injected Hostile/Rogue events: who injects them, and when, is unknown | Organisers | The adversarial log also records events we observe |
| The inline bonus must be shown live during judging | Account lifetime; budget | `prooflab tail` on a live run while the account is up; otherwise the recorded N3 decision records, labelled "recorded, not live" |
| Readiness records not yet produced: the recorded L1 → L3 demo and the timed 15-minute run-of-show (R-J-45), the 5-link hand-check (R-P-03 (e)), the mentor review (R-J-56) [04b] | Time | Planned in §12.1 and kept in `reviews/` (§9.1). Any not produced by the final submit is listed here and in `gap-list.md` |
| Adapter bug (a): `notify --dry-run` on an existing incident logs DELIVERED and is not offline | Arth's code, used as-is; accepted by the captain | A dry run only ever writes to a TEST log (G-05) |
| Adapter bug (b): an itil journal read of 0 rows can read as NO_RESPONSE_OBSERVED | Arth's code, used as-is; accepted by the captain | `check` every ≤ 60 s; nobody else updates our incidents after the owner; the sticky-RESPONDED rule; the response basis shown |
| The Assurance agent's model calls carry no subject CID (their run id is their trace id) | Arth's analyser sends no baggage | They join the platform's records by action id; their tokens are team overhead, never a subject run's C16 spend |
| The Assurance runtime sends the gateway key over plain HTTP (the gateway-URL shim) | Every AgentCore runtime gets a plain-HTTP gateway URL; the :8443 certificate is a placeholder (gap 9) | Recorded as a security decision; the key never leaves the runtime's env |
| A finding's trace holds at most 200 steps | Arth's `finding_context` rejects longer traces | G-04 summarises per invocation; the full trail stays in the pack |
| The console's live file is a convenience index; a replay is labelled REPLAY | A design choice (G-10) | The pack's records stay the authority |
| The cockpit side door (EP-16): the cockpit has no auth, and anyone with its link can invoke any agent | Platform | Observed and labelled in the run catalogue; our agents run an unenveloped call under the strictest cap |

---

## B13. The rails' gaps (G-1 to G-14)

*Source: `architecture/guardrails/AGENT-GUARDRAILS.md` section 11. The rails are agent code that we write; they are self-enforced (G-6) and measured on a curated set, not a full red-team scan (G-10).*

| # | Gap | Why it stays | What we plan to show instead |
|---|---|---|---|
| G-1 | **No NVIDIA safety models** (content safety, topic control, jailbreak detection, GLiNER PII; talk M1–M7) | Not served on Bedrock; Marketplace and SageMaker denied; no NIM operator; no GPUs [02 GR-01–03]. The only serverless safety classifier, `gpt-oss-safeguard`, is not NVIDIA and is an organiser question [02 GR-04] | Deterministic rails + a fail-closed self-check on a general Nemotron, with the platform guardrail as its first stage. Weaker than a trained classifier: RTM-1 publishes the misses |
| G-2 | **The platform guardrail is fixed, narrow and not editable** | PROMPT_ATTACK on input only (PII only on the helper alias); no content, topic, word, grounding or output policy; IAM denies guardrail writes; one guardrail per alias [07 GS-15, GS-16] | Observed and recorded per run (id and version); RTM-2 measures its coverage; our rails cover output and tool output |
| G-3 | **No platform screening of tool outputs** | Guardrails bind only to model routes; ApplyGuardrail is unavailable; the external enforcers are inert [02 GR-09, GR-10] | T-01–T-06 in-agent |
| G-4 | **Raw prompts in spans** (gap 9, refined) | Without the token, Strands writes the raw prompt into `invoke_agent` before any hook (§1.1). With it, Strands redacts; other emitters (ADOT instrumentations, exception text, gateway-side logs) are unverified | The env switch + I-02 + O-04; the T-SPAN-01 canary result, stated either way |
| G-5 | **No per-agent platform Cedar** (gaps 2, 3) | One principal (`bootstrap-key`); the AgentConfig overlay isn't wired [07 GS-27]; a ToolConfig rule applies to every caller | RT-04 + X-01/X-02 in-agent (self-enforced); one narrow Cedar `forbid` for every caller (D15 (a)) |
| G-6 | **In-agent rails are self-enforced** | They run in the agent's process. A buggy or compromised agent skips them, and no platform PEP checks that they ran | MON-02 corroborates from the platform's spans; RT-01's hashes plus EP-0's digest check catch a changed image |
| G-7 | **Egress can't be verified at the platform level** | The security group is unreadable; IAM blocks only Bedrock and the AgentCore Gateway [02 GR-22] | RT-03's audit hook (observe → enforce) for our process only |
| G-8 | **Guardrails not editable or selectable** (see G-2) | GS-15, GS-16 | — |
| G-9 | **TLS** | :8443 has a self-signed placeholder certificate and serves model routes only; MCP has no TLS listener, so the key crosses in clear on every tool call [07 GS-25] | Digests in records; O-04; stated |
| G-10 | **No full red-team scan** (NeMo Auditor / garak) | No Auditor service; shared ceilings; the 1 req/s rule; no AgentCore generator | RTM-1–3: curated, measured, with misses published |
| G-11 | **No millisecond out-of-band containment** (Sentry) | Our out-of-band loop runs in minutes; a model pause takes ≤ 2 s on super-120b and 33–41 s on nano-9b | In-band X-05 and the C16 halt |
| G-12 | **No hardware boundary** (OpenShell in-silicon, BlueField) | AgentCore microVMs and t3 nodes | Stated |
| G-13 | **No in-path human approval** | Headless agents; no inbound endpoint (R-P-07); EP-13 records only; no action tools | O-07 FLAG → the ESC incident; dispositions only ratchet to escalate |
| G-14 | **The Cedar test rule is bypassable by case** | Cedar `like` is case-sensitive; the handler upper-cases `site` | Labelled a mechanism demonstration, not a protection |

---

## B14. Adapter bug (a): a dry-run notify on an existing incident is not offline

**What's missing:** an offline dry run of `notify` on an incident that already exists.

**Why:** in Arth's adapter an existing incident returns its confirmation before `dry_run` is checked (`notifier.py:134-136`), so the dry run logs DELIVERED. We use Arth's code as-is; the captain accepted this as a known risk.

**Impact:** a dry run against the production log would write a false DELIVERED line.

**What we plan instead:** a dry run only ever writes to a TEST log, never the production log (`evidence/register/approval/delivery-log.jsonl` and the delivery log are absolute paths).

---

## B15. Adapter bug (b): zero journal rows can read as silence

**What's missing:** a way to tell "the owner did not reply" from "the integration user could not read the journal".

**Why:** the `itil` integration user reads 0 journal rows with no error (the ACL), and Arth's `_actions` treats 0 rows as readable (accepted risk, as above).

**Impact:** a reply could be missed, and silence recorded wrongly.

**What we plan instead:** `check` every 60 s or less; nobody else updates our incidents after the owner; the sticky-RESPONDED rule (a logged RESPONDED is never overridden by a later NO_RESPONSE_OBSERVED); the response basis (`last_update`) is shown.

---

## B16. The Assurance agent's model calls carry no subject CID

**What's missing:** the run id on the Assurance agent's gateway calls.

**Why:** Arth's analyser sends no baggage, so a call's run id is its trace id. We never put a subject run's CID on those calls (it would land their tokens inside that run's C16 figure; `work/14` R-8).

**Impact:** these calls join the platform's records by action id only, and their tokens are team overhead, not a subject run's spend.

---

## B17. A finding's trace holds at most 200 steps

**What's missing:** a full call-by-call trace inside a finding for a long run.

**Why:** Arth's `finding_context` raises on a trace longer than 200 steps instead of truncating; the reference S2 had 353 gateway spans.

**Impact:** without a summary, a long BREACH run would fail validation before `notify` and no incident would be raised.

**What we plan instead:** the finding builder summarises per invocation (at most 200 steps); the full trail stays in the pack.

---

## B18. Readiness records not yet produced

**What's missing:** the recorded Level 1 to Level 3 demo, the timed 15-minute run of show, the five-link hand-check, and the mentor review.

**Why:** time. They are planned and kept under `reviews/`.

**Status:** `<update before each submit: list which exist, and which do not>`. Anything not produced by the final submit stays listed here.

---

## B19. A numeric `site` is refused for every caller on `customer-records` since the SP-1 forbid

**What's missing:** a Cedar rule that refuses `SITE-ADV-*` without also refusing legitimate numeric `site` values.

**Why:** the SP-1 `forbid` uses `context.arguments.site like "SITE-ADV-*"`. When `site` is a number, `like` is a type error, and authz fails closed (403 `PolicyEngineUnavailable`) for any caller, ours and the reference trio's. Cedar has no primitive-type guard. How a numeric site behaved before the rule was not tested.

**Evidence:** `ops-lane/sp1-report.md` (probe 4: `site=12` gives 403 `PolicyEngineUnavailable`, `type error: expected string, got long`); `ops-lane/sp1-probes.txt`; restore text `ops-lane/sp1-patch-restore.json`.

**Impact:** the PDP log line for that call says `decision=ALLOW matched=policy0`, while `/modaas/evidence` says DENY / `PolicyEngineUnavailable`. The PDP line is not a reliable record of the final decision; an auditor must read `/modaas/evidence`. Our scenarios send string sites, so none is affected (not yet proven on a full run).

**What we plan instead:** take decisions from `/modaas/evidence` only; keep the rule through judging (DG-4); restore after judging (Hold-4).

**Status:** open, accepted; the rule is live.

---

## B20. The MCP `tools/call` span logged tool arguments and results in clear

**What's missing:** a platform switch that keeps tool arguments and results out of the runtime's spans.

**Why:** the ADOT `aws_mcp` instrumentor writes them into the runtime log group's `spans` stream. Found at S-2 on the first image build (canary seen in clear); the tool half of gap 9.

**Evidence:** `ops-lane/b2b-report.md` item 6; after the fix, `ops-lane/b2d-report.md` S-2 row (canary absent from 22 log groups, run on `3bfc5ad`).

**Impact:** on the reference agents, which we do not change, customer data in tool results is still written to their spans.

**What we plan instead:** our images disable `aws_mcp` (PR-30a). Fixed in our images and verified live at S-2 on `3bfc5ad`. The reference agents still have it, and we say so.

**Status:** fixed for `ifabric-*`; open for the reference agents.

**Resolution (2026-10-06):** fixed in our three images and verified live at S-2 (`ops-lane/b2d-report.md`). Not fixed for the reference agents, which we do not change. Kept here for the record.

---

## B21. Model-call records lack `pin.sha256` and `runtime.session_id`

**What's missing:** the pin hash and the runtime session id on each `model_call` action record.

**Why:** the images are frozen; changing the record shape needs a rebuild and a new approval.

**Evidence:** `ops-lane/b2b-report.md` item 9; still true in `ops-lane/b2d-report.md` ("Other observations").

**Impact:** a model-call record cannot name its pin or session on its own.

**What we plan instead:** join through the start-up record (`pin.sha256=... register=...`, on all 11 start-up lines at S-2) and the response's pin echo (`pin_sha256`, `pin_verified`), then by run id.

**Status:** open, accepted.

---

## B22. EP-0's fallback checks only image and model when the approved spec is unavailable

**What's missing:** a full approved-spec comparison when the platform gives EP-0 no approved spec.

**Why:** without `specs.<agent>.approved`, EP-0 falls back to the approval attestation, which covers image and model only (PR-30b, `68217bb`). With the spec, it compares spec by spec and passes only the declared pin keys.

**Evidence:** `ops-lane/b2d-report.md` (PR-30b note; the row-11 versions file needs the `specs` input).

**Impact:** an env change other than the pin keys could pass the fallback unseen.

**What we plan instead:** the ops lane records approved-spec env fingerprints (sha256, never values) in the G3 freeze record so EP-0 stays strict.

**Status:** open until the fingerprints are in the freeze record; they are not in `ops-lane/b2d/freeze-g3.json` (provisional) as of the B2d report.

---

## B23. Nothing in the path enforces the smoke budget; only the pin's ceiling stops a run

**What's missing:** an in-path stop at the smoke budget (about 10K tokens).

**Why:** the observe-mode cap only records DENY; the halt comes from the safety ceiling in the pin.

**Evidence:** `ops-lane/b2d-report.md` (IT smoke, CID `ifabric-test-1791272730-5ab393`): 21,467 tokens against a smoke authorization of 10K; the 25,000 ceiling halted it (`DENY (halt): committed 21467 + bound 5268 = 26735`).

**Impact:** a smoke can spend the whole ceiling. The captain set a 100K ceiling for P1 and P3 (re-pinned to 300K for P5 only), so one run can spend up to that.

**What we plan instead:** keep the pin ceiling always on; the S-3 halt on a low cap is proven (cap 3,700: call 2 denied at 3,992, no span after).

**Status:** open, accepted.

---

## B24. The `ifabric-it` tool loop on a bare ticket

**What's missing:** a stop condition when the runbook has no match.

**Why:** on a bare ticket the IT agent made 12 `runbook-lookup` calls (7 distinct arguments), and rail T-02 flagged `no-evidence` 9 times. It does not choose "gather evidence" or "escalate" on its own.

**Evidence:** `ops-lane/b2d-report.md` (the IT run, 07:45:25-07:46:00Z; 12 model calls in 28.8 s, about 25 requests a minute).

**Impact:** about 21K tokens for one smoke; a natural run could also loop.

**What we plan instead:** the pin ceiling halts a loop; the run is judged by C16 as it is.

**Status:** RESOLVED for the loop (2026-10-06). The pilot P1 on the first build halted at the 100K ceiling with 28 runbook-lookup calls inside IT's Gateway C negotiation (`ops-lane/b3-report.md` section 3: 95,936 tokens, 77,660 in that one invocation). PR-36 added the T-07 loop guard (K=3, read from the register) and PR-38 the agent fixes; in the clean pilots T-07 fired once in each (P1c, P3, P5; `ops-lane/b3d-report.md`), and no pilot looped. The repeat of lookups before T-07 stops it is a separate gap (B32). Original wording kept above.

---

## B25. The platform keeps an AgentConfig Approved with the old approval when its image is patched

**What's missing:** a new approval record after an image or env patch (gap 5, confirmed again).

**Why:** a patch raises the generation; the old approval stays and the phase stays Approved.

**Evidence:** `ops-lane/b2c-report.md` (delete and re-create of `ifabric-customer`, captain-approved about 07:05Z; new uid; the operator re-created the Component and its children). The IT and network agents were patched (generation 2) and approved again by the captain's annotations at 07:28:50-07:29:25Z.

**Impact:** an approval alone does not show that it covers the running image.

**What we plan instead:** EP-0 compares model, generation and image digest with the approval record. We deleted and re-created `ifabric-customer`, so its approval matches its image. Deleting an AgentConfig also deleted its Component (B2c note 1).

**Status:** platform limit; handled for our three agents.

---

## B26. The build carrier: a 25,600-character buildspec cap and no layer pull

**What's missing:** a way to build an image from our own base image and a way to send a buildspec over 25,600 characters.

**Why:** CodeBuild caps `buildspecOverride` at 25,600 characters, and the ImageBuildRole lacks `ecr:GetDownloadUrlForLayer`, so `FROM` our own image fails (D-B).

**Evidence:** `ops-lane/build-probe-report.md`: one env-var override of 46,548 characters decoded byte-exact (sha256 checked) and built an arm64 image.

**Impact:** each role is built from a base file and a role file that ride as environment-variable overrides; the total is gated at 46,000 characters (D-B'') and each value at 44,000. The limit was not searched above 46,548.

**What we plan instead:** this carrier (PR-26), one build per role. All three rebuilt from `3bfc5ad` (env about 44.4K of 46,000).

**Status:** worked around; a size above the proven value is untested.

---

## B27. `GetObjectVersion` is denied to participants

**What's missing:** a readback of a specific object version.

**Why:** the participant role has no `s3:GetObjectVersion`. A zip's content is also not scannable in place.

**Evidence:** `ops-lane/safety-submit-report.md` (the 07:00Z safety submit; readback used `get-object --if-match <ETag>` with `head-object` before and after).

**Impact:** a version id alone cannot be read back by us; a judge with a role that allows it can.

**What we plan instead:** `head-object`, then `get-object --if-match`, then `head-object`; scans run on unzipped copies (PR-34).

**Status:** worked around.

---


## B28. The C16 enforce reservation: the effective inline ceiling is the cap minus a projected bound

**What's missing:** a cap rule that accounts for how enforce decides.

**Why:** in enforce, a call is denied when committed tokens + the projected next-call bound (2,855 to 5,139 in the three N1b DENY records, largest 5,139; ops-lane/b4b-report.md section 1) is above the cap. The effective inline ceiling is therefore the cap minus that bound. The pre-registered rule C16-cap/1 (normal need x 1.2, rounded up to 1,000) ignored the reservation. Under v1 (cap 20,000) the first healthy S1 run, N1, was halted by enforce; the bound at IT h1 was 5,139, so an S1 run halted once committed spend passed about 14.9K, below P1c's own natural 15,248.

**Evidence:** `ops-lane/b4-report.md` (section 1 and "Why the cap halts S1"; N1 `ifabric-run-1791291533-39c87b`, 17,384 tokens; its first attempt `ifabric-run-1791291231-eacc22` was an upstream 500, see B30). The decision and the new rule: `ops-lane/b4b-report.md` section 1 (rule C16-cap/2, largest bound 5,139 from the DENY record `20261006T125929290Z-ep1-17920c26`); `planning-handoff.md` (the ~12:58Z and ~13:50Z blocks).

**Impact:** a healthy run was stopped by a rule we pre-registered; the first v1 would have shown a PASS run as a stop. The cap was a measured value with a hole, not a free choice.

**What we plan instead:** a declared post-hoc change, decided by the captain at about 12:58Z (option B): v1.1, rule C16-cap/2 = ceil to 1,000 of (normal need x 1.2 + the largest projected single-call bound) = 25,000, C16 only, C7 and C9 unchanged. v1 and its rules stay on record with their hashes; N1b is kept as the enforce stop record. New T1 (13:38:05Z) and T2 (INC0010338, delivered 13:41:06Z; the captain posted the APPROVED note).

**Consequence:** the natural S2 breach lever was lost: P5 spent 24,430, under the new 25,000 (`ops-lane/b3d-report.md`). N2 uses the pre-registered conflicting-context condition instead.

**Status:** worked around, openly labelled as post-hoc.

---

## B29. S1 spend varies run to run, so enforce can stop the final calls of a healthy run

**What's missing:** a spend figure for S1 that holds from one run to the next.

**Why:** S1's total moved between 14.7K and 22.3K today (P1c 15,248; W1 14,683; N1 22,271), because IT h1 made 5 to 9 model calls (N1b: 7; N1: 9 served calls, 17,623 tokens). A cap derived from two pilots plus headroom cannot cover that spread in enforce.

**Evidence:** `ops-lane/b4b-report.md` (N1 `ifabric-run-1791294968-36d929`: 22,271 tokens, 14 served calls, three EP-1 DENY halts at IT h1, the network agent and IT Gateway C; W1 `ifabric-run-1791294721-fd797f`: 14,683); `ops-lane/b3d-report.md` (P1c 15,248).

**Impact:** under v1.1 enforce stopped N1's final calls. C16 is SATISFIED (22,271 within 25,000, a stop record), but the run did not finish its negotiation.

**What we plan instead:** the captain accepted N1 as the PASS run at about 14:10Z. It is labelled honestly: enforce stopped the final calls. Nothing was tuned after it.

**Status:** accepted, labelled.

---

## B30. Platform failures that AgentCore metrics do not show

**What's missing:** an error signal for a failure that the platform wraps in a success.

**Why:** two kinds, both seen today:
- A Bedrock `InternalServerException` returned inside a 200 response: 1 in about 360 model calls over 7 days (10:55:32Z, ConverseStream, 469 ms, 0 tokens). It happened twice today, the second time as N1 attempt 1 (`ifabric-run-1791291231-eacc22`).
- A client read timeout while AWS recorded the invocation as completed: P1b, where IT finished in 24.9 s with HTTP 200 and the CLI waited 900 s for the end of the response.
AgentCore `Errors`, `SystemErrors`, `UserErrors` and `Throttles` stayed 0 on every runtime.

**Evidence:** `ops-lane/b3b-report.md` (P1 `ifabric-run-1791284097-880f6c`, the HTTP 500); `ops-lane/b3c-report.md` (P1b `ifabric-run-1791285349-7659f8`); `ops-lane/b4-report.md` (N1 attempt 1); `planning-handoff.md` (the 12:16Z read-only check).

**Impact:** a C9 error count taken from AgentCore metrics alone would read 0 on a run that failed. Our own evidence trail (the ledger, the run record, the gateway span) caught both.

**What we plan instead:** an INFRA-FAILED class, catalogued and counted as a C9 error, with a one-time re-run rule under a new CID at least 2 minutes later; `PROOFLAB_CLI_READ_TIMEOUT` (PR-44; 180 s for S1 and S3, 420 s for S2). The failed runs stay on record.

**Status:** worked around; the metric gap itself is a platform limit.

---

## B31. The Assurance agent's gateway call carries no CID

**What's missing:** the run id on the Assurance agent's model call.

**Why:** its call to the gateway sends no baggage, so the gateway mints its own trace and writes that 32-hex trace id as `modaas.run_id`. It is unrelated to our `ifabric-assure-` CID. (B16 records the same gap for the model-call records; this entry covers the join.)

**Evidence:** `ops-lane/b6b-report.md` (action id `9cbe05fb-3ad4-4a64-b024-c3b6f8c8b075`; gateway trace `07047a28...`; zero spans with `modaas.run_id` equal to the CID).

**Impact:** a collector that filters spans by our CID prefixes never sees Assurance calls; a window sweep lists them as unattributed.

**What we plan instead:** PR-41 joins a span whose run id is the gateway's own trace id to the incident's run and finding by action id, through the witness line.

**Status:** worked around. Fixing it at the source needs a handler change, a rebuild and a new approval; not done.

---

## B32. IT's Gateway C negotiation repeats lookups until T-07 stops it

**What's missing:** reuse of the incident and runbook ids the customer agent already found.

**Why:** the negotiation does not carry them, so IT looks them up again; the T-07 guard (K=3) ends it. T-07 fired live in P1c, P3 and P5.

**Evidence:** `ops-lane/b3d-report.md` (T-07 once per pilot, at IT Gateway C); the first-build loop in `ops-lane/b3-report.md` section 3.

**Impact:** extra tokens and calls in every run; the C16 cap and the C9 IT baseline include them.

**What we plan instead:** keep the guard on and say so.

**Status:** open; fixing it needs an agent change, and the images are frozen.

---

## B33. S1 cannot reach the kit's "auto-resolve" disposition

**What's missing:** an S1 procedure in the runbook-lookup tool.

**Why:** the tool returns none, so every S1 disposition is gather-evidence (the network agent's text says "low-risk switchover resolves", but the recorded disposition does not).

**Evidence:** `ops-lane/b3d-report.md` (P1c kit grade 7/8; P3 10/10; P5 10/10); the same in B3, B3b and B3c.

**Impact:** the kit grade for S1 is 7/8 at best. S2 and S3 grade 10/10.

**What we plan instead:** report 7/8 as it is.

**Status:** open, accepted; the tool is not ours.

---

## B34. Three of six pilot attempts failed

**What's missing:** a clean first-attempt pilot record.

**Why:** the pilots ran as P1 (halted, agent-side), P1 again (Bedrock 500), P1b (client timeout), then P1c, P3 and P5, which finished. One failure was the agent's (the first build's runbook loop and guardrail block, fixed by PR-38); two were the platform's (B30). Each is catalogued with its failure class.

**Evidence:** `ops-lane/b3-report.md`, `b3b-report.md`, `b3c-report.md`, `b3d-report.md`; `register/experiments/experiments.jsonl` (P1 with `halted: true`, `derivation_eligible: false`).

**Impact:** the thresholds rest on two eligible measured runs (P1c, P3), plus P5 for the S2 lever. A halted run measures the ceiling, not the need.

**What we plan instead:** v1 and v1.1 cite only the eligible pilots. The captain declined a fallback basis (the 100K appetite) and said "keep trying pilots 3 more times" at about 12:00Z; it was not needed.

**Status:** closed; recorded.

---

## B35. A pin or mode patch is a runtime update, so C9 needs a warm-up run

**What's missing:** a latency baseline that survives a patch.

**Why:** a patch starts a new runtime version; the first run after it pays a cold start. C9 reads an assessed run after an undeclared treatment as INDETERMINATE.

**Evidence:** `planning-handoff.md` (~12:58Z block, PR-45); `ops-lane/b4b-report.md` (W1 `ifabric-run-1791294721-fd797f` counted, C9 SATISFIED for N1).

**Impact:** one extra run (about 15K tokens) before every assessed run after a patch.

**What we plan instead:** PR-45: one warm-up on the same generation and pin satisfies the cold-start rule, and C9 now counts every invocation, including the customer's h0.

**Status:** worked around.

---

## B36. The README shows `<CID>`-style syntax examples

**What's missing:** examples a reader can copy as written.

**Why:** placeholder syntax in the command examples. Cosmetic.

**Evidence:** `planning-handoff.md` (11:59Z block).

**Impact:** none on the evidence; a reader must substitute a value.

**What we plan instead:** leave it; fill the date and window fields from the real data at pack time.

**Status:** open, cosmetic.

---

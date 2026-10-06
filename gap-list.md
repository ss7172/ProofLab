# Gap list

*Draft started 2026-10-05, while working through the workshop and before our build. Entries change as we close gaps.*

Gaps 1 and 10 are about agent judgment, the gap the challenge asks us to close. Gaps 2–9 and 11 are platform limits we found and verified. They bound what any Evidence Pack on this platform can prove, so each one says what an auditor can't do and how we would work around it.

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

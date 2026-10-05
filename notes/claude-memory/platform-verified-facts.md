---
name: platform-verified-facts
description: "Live-verified facts (2026-10-05) about the MoDaaS platform's evidence surfaces, governance mechanics and cockpit that the ProofLab plan can rely on — incl. where per-run IDs and tokens actually live, and where the handoff's assumptions were wrong; plus the Resources/Glossary/screenshot checks (authz log has no per-call records, PDP/authz pod-only, get-agent-runtime exposes env tokens), the 2026-10-05 live verification (the gateway's spans in aws/spans carry run id + tokens for 30 d; gateway key only in runtime env), the evidence snapshot / ledger PVC, and the 2026-10-05 platform-contract page checks (gateway stdout values are quoted; 6 gateway policies; no Cedar policy DENY ever; participant RBAC allows CRD and gateway-policy writes, but the admission VAP refuses them; can-i checked 2026-10-05)"
metadata:
  node_type: memory
  type: project
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T19:44:15.907Z
---

Verified live with read-only commands on 2026-10-05 (UTC); items marked (review) were verified by an independent reviewer subagent. Re-verify before assessed runs.

**Evidence surfaces: where data actually lands**
- **Gateway CloudWatch log `/aws/modaas/gateway`** (stream `modaas-agw`, retention 7 days; the gateway's OTLP access-log copy):
  - 1,630 OTel records on 2026-10-05 (2026-10-04 10:57Z → 2026-10-05 18:26Z), 258 with token counts (an earlier read saw 155 and 4). Each has top-level `trace_id`/`span_id`.
  - Attributes include `gen_ai.usage.input_tokens`/`output_tokens`, `agw.ai.usage.cost.total`, `gen_ai.request.model`, `listener`, `http.*` and `mcp.*`.
  - **NO record has `modaas.run_id`, `modaas.trace_id` or `modaas.action_id`** (0 of 1,630, live 2026-10-05). Its tokens join a run by `trace_id` only.
- **Run IDs are on the gateway pod's stdout (ephemeral) AND, durably, on the gateway's trace spans in CloudWatch Logs `aws/spans` (CONFIRMED live 2026-10-05).**
  - Stdout: the access-log policy (`modaas-access-log`) puts `modaas.run_id` (= baggage CID), `modaas.trace_id` and `modaas.action_id` on every line. The kit's `pull-evidence.sh` reads stdout (`kubectl logs --tail=50000`), and `evaluate.py` filters on `modaas.run_id`.
  - Spans: `aws/spans` (the X-Ray Transaction Search log group, 30-day retention, created 2026-10-04 10:03Z) holds one span per gateway request (service `modaas-agw`, name `POST /`). Each carries `attributes.modaas.run_id` = the baggage CID (via the authz correlation id; with no CID, the trace id) and `attributes.modaas.action_id` (distinct per call); model calls also carry `gen_ai.usage.input_tokens`/`output_tokens`, `aws.genai.token_count_total`, `agw.ai.usage.cost.total` and `gen_ai.request.model`. Path: gateway → collector `traces` pipeline → `awsxray` → `aws/spans`.
  - Verified: S2 `fault-1791177342-d3f892` (2026-10-05 05:15–05:20 UTC): 353 spans (174 llm + 179 MCP), 353 distinct action ids, 1,999,001 tokens, $0.3033. S1 `fault-1791179282-8ef1a8`: 24 spans (9 llm), 37,664 tokens. Also S1 `fault-1791177843-fde682` 50,246 and S3 `fault-1791177926-b0ce69` 37,799. All equal the gateway stdout figure of record exactly.
  - So C16's figure of record is durable for 30 days, until the account teardown (whichever comes first). Logs Insights on `aws/spans`: filter attributes.modaas.run_id = "<CID>" and attributes.listener = "llm", then sum the input and output tokens.
  - Caveats: only gateway spans are in `aws/spans` (agent spans live in each runtime's log group). Requests without an authz correlation id carry no run id: the kill-switch 404 (0 spans with its CID) and MCP `GET` 405s. The run's trace also holds attribute-less `modaas-agw` child spans (one per MCP call), so count by run id, not by trace. X-Ray holds the same fields as segment metadata (not annotations, so no X-Ray filter by run id), but `batch-get-traces` truncates long runs (S2: `LimitExceeded`, 22 of 174 llm calls), and X-Ray totals double-count agent subsegments.
- **`/modaas/evidence`** (stream `modaas-evidence`, retention 30 days, from the collector's `logs/audit` pipeline): records with `modaas.evidence.{correlation_id, action_id, trace_id, decision, policy_id, principal, phase,…}`. (review): `correlation_id` is on 60/60 records, and all 4 token records join to a CID through `trace_id` → evidence.
- **X-Ray:** the collector's `traces` pipeline exports to `awsxray`.
  - It holds `modaas-agw` traces, 2 of which join `hackathon_helper.DEFAULT` (AgentCore) with `modaas-agw`.
  - This contradicts the handoff's "no durable exporter", and also the guide's Module 6 overview: "its trace pipeline has no durable exporter (spans are discarded)". Added as repo notes #32 (user: "ADD", 2026-10-04 CDT). Path verified: gateway → collector:4317 → traces pipeline (scrub-payloads, batch) → awsxray. X-Ray held 105 modaas-agw traces in 24 h.
  - X-Ray writes these spans to `aws/spans` (segment destination CloudWatchLogs, ACTIVE). For a run's calls, read `aws/spans`, not X-Ray (see Run IDs above).
  - Metrics go only to `debug`, so they are not persisted.
- **Audit store** (`audit-store.components:8080`): writes need `X-Audit-Token`; reads (`/records?cid=` JSONL, `/timeline?cid=`) are open.
- **TMF639 inventory** (`kubectl get --raw /api/v1/namespaces/canvas/services/resource-inventory:80/proxy/tmf-api/resourceInventoryManagement/v5/resource`):
  - All 15 assets are there as `LogicalResource`, including the Reviewing one.
  - Every record has the identical state `standby/disable/unlocked/active`.
  - The 14 approved CRs say `TMF639Projected=False` ("POST /resource → timed out").
- **Bedrock CloudWatch metrics (`AWS/Bedrock`):** InputTokenCount, OutputTokenCount, Invocations, InvocationLatency and TimeToFirstToken, **per model id, account-wide, not joinable to a run**. Invoked so far: `nvidia.nemotron-super-3-120b` and `nvidia.nemotron-nano-9b-v2` (Module 5 calls, pause tests, swap run).
- **CR status:** `status.governance.approvals` holds subject, role, attestation, signature (always empty) and time. Some conditions are inaccurate (TMF639Projected; `IstioPerAssetProvisioned`, notes #15; stale pause conditions, see [[workshop-progress]]).

**Governance mechanics**
- **Identity:** `modaas-authz` checks the API key through `extAuth`, `failureMode: FailClosed`, on all listeners. There are 0 Istio RequestAuthentications.
- **PDP decision mechanics (source `pdp/cedar_evaluator.py` + live):**
  - Each `/decide` names ONE `policyId` (`model-<alias>` or `modaas-toolconfig-<alias>`) and is evaluated against that policy only. A missing id → DENY.
  - So a team policy ConfigMap such as `my-team-policy` loads but is never consulted unless something names its id. To enforce your own rule, attach it to an asset (e.g. a ToolConfig `access.cedarPolicy`).
  - Decision lines: `decide policy_id=… decision=… matched=… latency_ms=… trace_id=… action_id=…`. They join to responses by `action_id` (= `x-modaas-action-id`) and carry the gateway-minted trace_id even when no traceparent was sent.
  - **A guardrail-blocked call is logged as ALLOW:** authorization passed, then the guardrail blocked it. Served-or-blocked must come from the gateway line.
  - Grep both replicas' whole logs (`--all-pods --tail=-1`), because health checks dominate the tail.
  - The policy id can come from the request header `x-modaas-policy-id` (`authz-gateway/app.py:88, 105-106`), but gateway extAuth doesn't forward it. `/modaas/evidence` also records guardrail-blocked calls as `decision=ALLOW` (notes #35).
- **Authorization:** 14 Cedar policy ConfigMaps in `modaas-system`, one per model and tool (including the Reviewing tool) and none for the AgentConfig, with label `app.kubernetes.io/part-of=modaas-pdp`.
- **Guardrails:** one Bedrock guardrail per ModelConfig (4 READY, created at approval); `spec.safety.required: true`.
- **Admission:** 94 served CEL rules (Model 33, Tool 20, Agent 36, Registry 5) plus the VAP `modaas-governance-guardrail`.
  - The guide's unsafe-model example is rejected by TWO rules: safety enforcer `none`, and "safety.required=true demands governance.approval.required=true".
- **Routes:** 13 programmed (4 models and 9 approved tools); the Reviewing tool has none.
- **Registry:** `RegistryRegistered=True` on all 14 approved assets, with `status.registryRecordId` = `<provider>_<alias>`. No Registry CRs exist.
- **Rate limits** (all `local`, i.e. per gateway replica, 1 replica): models 100 req/min and 2.5M tokens/h; the MCP listener 100 req/min.
- **Correlation key** (guide, Module 4): W3C `traceparent`. Control 7 joins on it.
- **Exposure:** the public ELB receives internet scanner traffic: 54 external `GET /` requests on 2026-10-04.

**Cockpit** (explored read-only via GET on 2026-10-05; CockpitUrl read from the stack output, never printed):
- **Access:** without the token the CloudFront URL returns 403. The token is swapped for a cookie, and the backend (`server.py` in `modaas-ui-src.zip`) has **no auth of its own** ("runs on a kiosk").
- **Not purely read-only:** it has one POST, `/api/agents/{name}/ask`, which invokes an agent. Never call it casually.
- **It leaks the ledger write token:** `GET /api/cr/AgentConfig/components/hackathon-helper` returns the CR's full YAML, which includes the literal `AUDIT_WRITE_TOKEN` env value. There is no redaction in `server.py`. Verified 2026-10-05 as a yes/no match; the token was never printed. See repo notes #24.
- **Working views:** overview, governance/approvals (15 records), registry catalog, TMF639 and cost.
- **The Cost view's own attribution:** CloudWatch Bedrock totals are a "cross-check … account-wide … joinable_to_run_id: false"; the **figure of record is the "gateway per-call log line"**. In the 24 h to 02:56 UTC: 28,371 input / 452 output tokens, $0.0045, all super-3-120b. Price catalog: ConfigMap `agentgateway-system/modaas-model-cost-catalog`.
- **Telemetry tap NOT shipped in this build** (the bootstrap step skips it when the assets are absent). So per-run usage, live drift and live ceilings say "no live source on this build". The telemetry and evidence-run endpoints return EMPTY "fixture"-labelled data.

**First governed model call (by Claude, 2026-10-05):**
- Response headers: `x-modaas-trace-id`, `x-modaas-action-id`, `x-modaas-correlation-id`.
- The gateway stdout `listener=llm` line had `gen_ai.usage.input_tokens=23`, `output_tokens=8`, `agw.ai.usage.cost.total=0.00000865`, `duration=1971ms`, and an action_id matching the header.
- **With no baggage CID, `modaas.run_id` = the trace id.**

**Guardrail verified (2026-10-05):** a prompt injection to nano-9b returned HTTP 200, `content_filter`, "Input blocked by policy." and 0 tokens. The gateway line shows 0/0 tokens and cost 0, but still a `run_id` and `action_id`, so blocked attempts are recorded events with zero token charge.

**Kill switch timing (measured 2026-10-05, nano-9b):** pause → route withdrawn after ~33–41 s, and calls kept being served (HTTP 200) in that window. Resume → serving again after ~35 s. The guide says "instantly" / ~15 s to stop and ~50 s to resume. The operator's reconcile is slowed by the TMF639 timeouts (2×10 s per model per resync). After resume the pause conditions and the registry servingState=PAUSED are left set.

**One call traced end to end (2026-10-05, Module 5 governed call `c5025cdc…`, trace `8f6359…`):**
- ① response headers (action_id, trace_id)
- ② PDP decision ALLOW `model-nemotron-super-120b`, joined by action_id
- ③ gateway stdout line, 23/8 tokens, cost, `run_id`=trace_id, joined by action_id
- ④ `/modaas/evidence` record, decision ALLOW, policy_version 331993, `correlation_id`=trace_id, `attested_by=modaas-authz`, joined by action_id
- ⑤ durable `/aws/modaas/gateway` record, same tokens/cost, joined by **trace_id only**
- ⑥ X-Ray trace, segment `modaas-agw`
- **`aws logs filter-log-events` IS permitted for the participant role** (verified), so joins can be searched directly. Ledger records join by `correlation_id` (the reference agents write no action_id; notes #20).

**Model swap / pricing (2026-10-05):**
- Patching an AgentConfig's `dependsOn.models[0]` re-programs the runtime in ~24 s and keeps the agent Approved, with no new review. (Live 2026-10-05: the IT swap was one `kubectl patch` at 05:47:37Z setting `modelRef` and `dependsOn.models`; the runtime's `lastUpdatedAt` is 05:47:50Z, version 2.) Re-annotating the attestation adds no approval record.
- Observed cost per token: nano-9b ≈ $0.064/M (8,450 tokens = $0.000537); super-120b ≈ $0.161/M.
- Gateway llm lines carry no agent identity. Attribute by CID + model, or by time window.

**Tool kill switch (2026-10-05, modaas-docs):** pause → 404 "route not found" within ~1–7 s (operator +1 s). Unpause → 200 after ~32 s. Much faster than the model pause (~33–41 s). Stale pause conditions remain on tools too.

**Whole-run propagation (2026-10-05, agent run fault-1791179282-8ef1a8):** the baggage CID and the W3C trace survive AgentCore → gateway → PDP → /modaas/evidence (correlation_id = CID) → durable gateway log (trace only) → X-Ray (one trace spanning all 3 agent runtimes and the gateway) → the gateway's spans in `aws/spans` (24 with run_id = CID, 37,664 tokens; live 2026-10-05). The ledger is the only surface whose trace_id differs (agent.py mints it).

**Agent tool authorization (verified 2026-10-05):**
- All agents call with ONE identity (`ServiceIdentity::"bootstrap-key"`).
- The PDP evaluates the policy of the tool actually called (from the MCP toolName), not the route's or caller's declaration, so an agent can call any approved tool through its own route.
- Seen: network → runbook-lookup and customer-records; IT → evidence-lookup. Declared `dependsOn.tools` is not enforced at runtime.
- This is the deck's Rogue "unauthorized tool use", already present in vanilla runs. It is detectable from gateway lines (`gen_ai.tool.name` per route) vs AgentConfig `dependsOn.tools`.

**Cedar levers (source + live, 2026-10-05; asked after a judge hinted "you can change the Cedar policies of the agents"):**
- **Cedar sees:**
  - principal: `bootstrap-key` for every agent; attributes verification/degraded/roles=[]
  - action: invoke
  - resource: Tool/Model, plus dataClassification
  - context: toolName, **arguments**, dataClassification, traceId, actionId, toolMethod
  - NOT the calling agent, the route, run counts or tokens. Cedar is stateless, so it can't cap loops or tokens.
- **ToolConfig `spec.access.cedarPolicy`:** the LIVE, enforced path. The user's direction (2026-10-05): Hostile/Rogue tests may use modified Cedar policies through this lever, with the limits listed in [[prooflab-project]].
  - The operator projects it to ConfigMap `modaas-toolconfig-<alias>` with label part-of=modaas-pdp, and edits propagate (per the source; no ToolConfig edit tested).
  - No CRD immutability rule on it. Policy version = the ConfigMap resourceVersion.
  - Whether an edit resets approval is untested; the AgentConfig model-swap precedent says no.
  - customer-records and network-twin have NO dataClassification set.
- **AgentConfig `spec.access.cedarPolicy`** (CRD: "restrict-only (forbid) overlay… narrow… never widen") and `agentPolicy` (the per-runtime PEP consults the PDP):
  - Documented, but NOT wired in this build: no code in aws-agent-operator, no ConfigMap, and the PDP evaluates only the called tool's or model's one policyId. No live agent sets it.
  - "Inert" is a source-based conclusion; a live overlay test needs a write.
- **ModelConfig `access.allowedConsumers`:** projected as `permit(principal == ServiceIdentity::"<azp>")`. Every model is live with ['bootstrap-key'] only.
- **Per-agent identity is DESIGNED but NOT PROVISIONED:**
  - canvas-keycloak-0 is running, plus identityconfig-operator-keycloak, and there are 18 IdentityConfigs in `components` (4 agents `modaas-agentconfig-<agent>`, 4 models, 10 tools), all listenerRegistered=false.
  - But listenerRegistered=false, and no secret name suggests per-agent client credentials.
  - The gateway's JWT path would make the principal `ServiceIdentity::"<azp>"`, but agents use the shared API key.
  - So per-agent Cedar scoping is impossible today. Provisioning would be a platform change → organiser question.
- **Cross-tool use is already DETECTABLE without Cedar:** the `/modaas/evidence` record carries `modaas.evidence.detail=route_alias=<route>` when the called tool ≠ the route. Seen in run e13e7b73: customer-records/runbook-lookup via network-twin, evidence-lookup via runbook-lookup.
- **The grader's checks** (disposition regex on the answer text, guardrail verdict in the ledger, negotiation) can't be moved by Cedar. Agents have no action/change tool, so there is nothing unsafe to deny in S3. A DENY today makes the reference IT agent log http_status=500 on the model (wrong status and asset; notes #43). It did NOT change the S1 grade: 6/8 with and without the refusal, because `score-run.py` passes the disposition check if any agent records it (`want in disps`).

**AgentCore runtime identity and health (verified 2026-10-05):**
- **All 4 AgentCore runtimes share ONE execution role, `a-01-eks-cluster-agentcore-runtime`.** The deck p13 says "each with its own IAM role". The role's inline policy `agentcore-runtime`:
  - **allows:** ECR pull, logs to /aws/bedrock-agentcore/*, X-Ray and PutMetricData, workload-identity tokens, `bedrock-agentcore:InvokeAgentRuntime` on runtime/*
  - **explicitly denies:** `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` and `bedrock-agentcore:InvokeGateway` on * (Sid NoDirectModelOrToolAccess)
  - So agents cannot bypass agentgateway to reach a model (Converse is authorised via InvokeModel).
  - iam:SimulatePrincipalPolicy is denied to participants; get-role-policy works.
- **AgentCore metrics:** hourly Latency/Errors/Invocations per runtime (Name=`<runtime>::DEFAULT`).
  - The S2 runaway shows only as Latency; Errors stayed 0. In its hour (05:00Z) the IT runtime averaged 71.6 s (vs 8.2–8.5 s for customer and network) with a max of 278.4 s, so the Average showed it too and the Maximum most strongly (corrected 2026-10-05 after the handoff review).
  - A refused run shows FAST latency (1.05 s).
- **Spans carry content:** `chat` span events include the system prompt and context (customer records), contrary to the guide.

**Refusals in the platform's records (verified 2026-10-05, Module 9 Step 3):**
- Both a guardrail block and a pause refusal show `decision=ALLOW` in the PDP log and /modaas/evidence: Cedar decides first, then the guardrail blocks or the route is missing.
- The guardrail block is visible only as gateway 0 tokens. The pause 404's pod stdout line (09:13:06Z) carries `trace.id`/`span.id` but no `modaas.*` (run/trace/action id) and no `gen_ai.*` field; it and its DURABLE copy in /aws/modaas/gateway carry the OTel trace id of the evidence record (f51408192eb04563bbf7299258e2e6e3), so it joins the decision record by trace id. That trace id is on no other gateway line and in no ledger record, but it is on the PDP decision line 6 ms earlier (`decide policy_id=model-nemotron-super-120b decision=ALLOW`, action_id 642489b6-1611-4a92-a161-64083336d770) and on the /modaas/evidence record (written by modaas-authz) with correlation_id = the run's CID `my-agent-1791191585-4d9744`, decision ALLOW, policy_version 331993. So the 404 JOINS TO ITS RUN BY TRACE ID, through the policy decision and its durable evidence record, and that record shows the refused call as ALLOW (lead's live read-only check, corrected 2026-10-05). It shows only 404 + path (no model, no reason). Only the agent's ledger says refused (or undetermined, for a guardrail block via the template).
- **Kill-switch latency varies:** super-120b refused within ≤2 s (09:13); nano-9b served for 33–41 s (04:05). Resume to serving took ~24–34 s.

**Spans (verified):** Strands-native (~48 per S1 run). `chat` spans equal the gateway per call. `invoke_agent` parents carry sums, so summing all spans double-counts. No `modaas.action_id` on the agents' spans (the gateway's own spans in `aws/spans` carry it; see Run IDs).

**Resources & How-To, Glossary, cockpit screenshots (verified 2026-10-05):** three read-only verifier subagents checked the guide's Glossary page, its Resources & How-To page and two cockpit screenshots against live (kubectl/AWS reads as WSParticipantRole, the cockpit source zip; cockpit not opened, no secret values printed).
- **WHO/AUTHORIZED logs:**
  - `modaas-authz` writes NO per-call records to its pod log: each of the 2 pods has only 4 uvicorn startup lines. Its per-call records go only to `/modaas/evidence` over OTel (`attested_by=modaas-authz`); all 39 records in the hour checked had principal `ServiceIdentity::"bootstrap-key"`. So the guide's WHO step (`kubectl logs deploy/modaas-authz`) shows nothing.
  - PDP decision lines carry no principal. `kubectl logs deploy/modaas-pdp` reads only 1 of the 2 replicas, and each action_id is in one replica only: read both with `-l app.kubernetes.io/name=modaas-pdp`. 24 h: 1,016 decisions, all ALLOW.
  - **PDP and authz logs are pod-only:** no CloudWatch log group for either. Durable: `/modaas/evidence` 30 d, `/aws/modaas/gateway` 7 d; the 5 runtime log groups never expire. `/aws/bedrock/aict-invocations` keeps 7 d (two reviewers, live, 2026-10-05).
  - **The PDP, not the operator, loads the policy ConfigMaps;** the operator only writes the generated ones. 15 ConfigMaps carry the part-of=modaas-pdp label: 10 `modaas-toolconfig-*`, 4 `model-*` and `my-team-policy` (the per-asset ones above plus ours). `my-team-policy` was named in 0 of 1,037 decisions on both PDP replicas over their whole life (2026-10-04 18:07 → 2026-10-05 17:33 UTC; evidence snapshot; notes #33).
  - `demo-crm-lookup` is still Reviewing, yet its Cedar ConfigMap exists and the PDP has loaded it (it has no route).
- **Run ids:**
  - 24 h of gateway stdout lines with `modaas.run_id` (one pod, 0 restarts): **627 carry a CID-shaped run id ≠ the trace id, 384 a 32-hex run id = `trace.id`.** `modaas-access-log` and `modaas-telemetry-export` both set `modaas.run_id <- extauthz.correlationId`, so the baggage CID wins. The trace-id fallback is now confirmed: in `aws/spans`, 627 run ids are CID-shaped (16 distinct CIDs) and 444 equal the span's own trace id (live 2026-10-05).
  - The telemetry export (`modaas-telemetry-export`, generation 1, unchanged since 2026-10-04 10:36:58 UTC) adds `modaas.run_id` and `modaas.action_id` only to the gateway's trace spans (`spec.frontend.tracing.attributes`). Its OTLP access-log export (`spec.frontend.accessLog.otlp`), which feeds `/aws/modaas/gateway`, adds no attributes, and 0 of the 1,630 records there carry either id (live 2026-10-05). Both policies are Accepted and Attached, with no conflict reported. The installer's comment (`bootstrap-platform.sh` lines 653–654) says that export was meant to be the same per-call line as stdout, so "by design" is refuted: it's a build gap whose cause (how agentgateway combines two policies' access-log settings on one Gateway) can't be established read-only. The collector deletes only 6 payload keys (prompt, completion, input/output messages, request/response body), not the ids (live config; corrected 2026-10-05).
- **X-Ray / `aws/spans` join (checked live 2026-10-05):** the gateway's `modaas-agw` spans carry `modaas.action_id` and `modaas.run_id`; on CID-tagged runs `modaas.run_id` IS the CID (no CID → the trace id). So run id → action ids → `/modaas/evidence` (decision, policy version) → PDP log is a durable join (30 d in `aws/spans`). These are the GATEWAY's spans; the agents' Strands spans have no action_id (see Spans above). X-Ray keeps the ids as segment metadata and truncates long traces, so use `aws/spans`.
- **APPROVED/INTEGRITY surfaces:**
  - EKS control-plane logging is OFF for all 5 types (api, audit, authenticator, controllerManager, scheduler).
  - CloudTrail `lookup-events` works (90-day management history), but `describe-trails` is AccessDenied for WSParticipantRole, so whether a trail archives events is unknown. CloudTrail doesn't record kubectl or gateway calls.
  - Live CRs: 18 Approved (4 Model, 9 Tool, 5 Agent), 1 Reviewing (`demo-crm-lookup`), none Paused. Each Approved CR has the 2 approval annotations and 1 approval record; **`signature` is empty on all 18.** Approvers: system-admin ×11, satyabratsrikumar@team ×5, cloudshell-user@team ×2.
  - **Evidence bucket config is unreadable to us:** versioning, object lock and lifecycle on `team-evidence-…` are AccessDenied; the bucket was empty at the check. `submit.sh`'s fallback bucket lookup (`… | [0]`) returns empty in this account; it works only because TEAM_EVIDENCE_BUCKET is set.
  - **The ledger service has no verify route:** `audit-store.py` GET routes are only `/healthz`, `/records`, `/timeline`, plus the write.
- **Keys and tokens (names, types and lengths only):**
  - **No runtime has `GATEWAY_API_KEY`.** The gateway key arrives as `OPENAI_API_KEY` (models) and `AGENTCORE_GATEWAY_MCP_TOKEN` (tools), injected by the operator: AgentConfig specs have only literal env, no `valueFrom` and no reference to `agw-apikeys`. Secret `agentgateway-system/agw-apikeys` exists (checked by name), but no spec references it. In the kit the name appears only in the stale `reference-impl/agents.yaml`. CONFIRMED live 2026-10-05 by in-memory value comparison: no AgentConfig CR (spec, annotations or status) holds the gateway key under any name, and on all 5 runtimes `OPENAI_API_KEY` and `AGENTCORE_GATEWAY_MCP_TOKEN` both equal the `agw-apikeys` eval key (48 characters), one shared key for every agent.
  - **`get-agent-runtime` works for the participant role and returns runtime env as plain strings,** including `AUDIT_WRITE_TOKEN`, `OPENAI_API_KEY` and `AGENTCORE_GATEWAY_MCP_TOKEN`: one more read path beyond the AgentConfig specs and the cockpit (notes #24).
  - All 5 AgentConfigs, our `my-agent` included, carry `AUDIT_WRITE_TOKEN` as a literal 32-character string: the specs' only credential.
  - **The IDE role can manage the AgentCore gateway:** its `ide-workshop` policy allows `bedrock-agentcore:Create/Update/DeleteGateway` on `gateway/*` (Sid `BootstrapAgentCoreGateway`); WSParticipantRole explicitly denies `Create*/Update*/Delete*`. Reported by the glossary verifier; policy re-read by an independent reviewer (2026-10-05); not attempted. Never use it.
  - The IDE role has no `bedrock:Invoke*` allow (implicit deny); WSParticipantRole has an explicit Deny on InvokeModel(WithResponseStream), InvokeAgent, InvokeFlow and `sagemaker:InvokeEndpoint*`. Read from the policies. The participant role's direct InvokeModel was already refused live in Module 5 (AccessDenied, explicit deny in console-iam-policy-0); the IDE role's was not attempted.
- **Cockpit (source + cluster):**
  - `server.py` has **47 `@app.get` routes and 1 `@app.post`** (`/api/agents/{name}/ask`); CORS allows GET and POST.
  - On the gateway pod, admin port **`:15000` is refused** (via the apiserver pod proxy), so the Perimeter view can't read config. **`:15020/metrics` serves the OTel GenAI metrics** (token usage, cost USD, request duration, time to first token, time per output token). 15020 isn't on the LoadBalancer service, but participants can reach it through the apiserver pod proxy.
  - The Observability panel scrapes `:15020` (`/api/gateway/metrics`), not the telemetry tap, so it should be live here (not seen in the UI).
  - **Cost view prices come from ConfigMap `agentgateway-system/modaas-model-cost-catalog`: 683 models** (aws.bedrock 360), with rates for all three Nemotron ids we use. Tokens come from CloudWatch `AWS/Bedrock` per model id (super-120b and -helper merge). The Observability panel's cost is a third source: the gateway's own cost metric (cumulative since pod start: ~$0.36 super, ~$0.0006 nano).
  - The Trace view's "no tracing configured" text is wrong; the gateway exports to X-Ray.
- **CEL rules: 94 live** by the cockpit's 4-CRD formula (Model 33 + Tool 20 + Agent 36 + Registry 5); **89 across Model/Tool/AgentConfig; 100 across the 12 `*.oda.tmforum.org` CRDs** (the 11 in group `oda.tmforum.org` plus `availability.oda.tmforum.org` AvailabilityPolicy); the VAP `modaas-governance-guardrail` adds 2 validations. **The screenshots' "90" is a hard-coded literal in an older UI;** the current source computes the count.
- **The guide's screenshots come from an older build:** 7 governed assets (we have 19), agents on provider kubernetesPod (ours awsAgentCore), `o2-network-inventory` (absent here), `demo-crm-lookup` shown Approved (ours Reviewing).
- **Commands and schema:**
  - `kubectl get publishednotifications -n components …` works as written: 91 objects, newest 2026-10-05 09:13:31 UTC (nemotron-super-120b Approved).
  - The Glossary checkpoint `kubectl api-resources --api-group=oda.tmforum.org --no-headers -o custom-columns=…` ERRORS: api-resources doesn't accept custom-columns. Drop `-o`; the default table has a KIND column.
  - **"Revoking" is not a phase** in any CRD. ModelConfig: Pending, Reviewing, Validating, Validated, Configuring, Approved, Failed, Paused, Retired. Tool/AgentConfig: Pending, Reviewing, Approved, Active, Failed, Paused, Retired. Registry phases describe reachability (Ready, Degraded, Unreachable, Unknown, ReadOnly); 0 Registry instances.
  - `oda.tmforum.org` has 11 kinds: 4 MoDaaS v1beta1 + 7 ODA Canvas v1.
- **AgentCore gateway:** one, `modaas-agw-knmghekdhu` (AWS_IAM, MCP), with 8 targets: 7 Lambda targets using GATEWAY_IAM_ROLE, and `aws-knowledge`, an `mcpServer` target with no credential provider. It shares the name `modaas-agw` with the Kubernetes agentgateway.
- `components` events are kept ~1 h and are all `reason=Logging`, so they can't serve as after-the-fact WHAT evidence.

**Evidence durability (snapshot agent, 2026-10-05):**
- **Snapshot** at `workshop-local/evidence-snapshots/20261005T173727Z/` (outside the repo; MANIFEST with sha256): the gateway log (1,895 lines, 2026-10-04 10:35Z → 2026-10-05 17:33Z; 290 distinct run ids), both PDP pods (22,705 and 22,851 lines), authz (startup lines only), the audit-store log, `pods.txt` and the ledger dump `ledger-records.jsonl` (one GET of `/records` at 17:44:26Z: 101 records, 17 CIDs, 2026-10-04 18:07Z → 2026-10-05 09:13Z; 16 of 17 CIDs match a gateway run id). An independent reviewer re-verified all 8 sha256s and re-ran the pattern scan (clean) on 2026-10-05.
- **0 restarts on all six pods** (gateway 1, PDP 2, authz 2, audit-store 1).
- **The audit-store ledger is on a PVC** (`audit-store-data`, 1Gi, mounted at `/data`): it survives pod restarts, but is deleted with the PVC/stack (reclaimPolicy=Delete). `/records` works without a cid. The audit-store's request logging is off by design.
- Re-snapshot before judging, and export the ledger into the Evidence Pack.

**Platform-contract page checks (live, read-only, 2026-10-05 19:04–19:13 UTC, WSParticipantRole; the page "What the platform gives you", extracted from the KB; report repo `notes/verification/2026-10-05/platform-contract-verify.md`):**
- **Gateway stdout quotes its id values:** `modaas.run_id="<CID>"`, and the same for `modaas.trace_id` and `modaas.action_id` (1,092 of 1,092). So an unquoted `grep "modaas.run_id=$CID"` (the page's command) matches 0 lines for every run. `grep -F "modaas.run_id=\"$CID\""` or `grep -F "$CID"` works: S2 353 lines, S1 24.
- **Gateway stdout coverage** (whole pod log, 2,033 lines, 10-04 10:35Z → 10-05 18:58Z, 0 restarts):
  - all 1,092 served (2xx) lines carry the three ids
  - all 258 served `listener=llm` lines carry tokens and cost
  - 573 lines carry no ids: 24× 403, 127× 404, 422× 405
- **Six AgentgatewayPolicies,** all `Accepted=True` and `Attached=True`: access-log, authz, llm-auth and mcp-ratelimit (10:33Z), plus telemetry-export and ceiling (10:37Z). The page's checkpoint "4" is stale.
- **PDP, both replicas** (`kubectl logs deploy/modaas-pdp --all-pods=true --tail=-1 --prefix` works; without `--all-pods` only one replica):
  - 1,097 decisions (501 + 596), 10-04 18:07Z → 10-05 18:58Z
  - **0 DENY**; 12 policy ids, all `model-*` or `modaas-toolconfig-*`
  - `my-team-policy` named in 0 of them
- **`/modaas/evidence`** (1,130 records, 10-04 18:07Z → 10-05 19:07Z):
  - 1,106 ALLOW / 24 DENY
  - the DENYs are 23 `reason=NoSigV4Credential` (principal `unknown`, asset `-unresolved-`) and 1 `PolicyEngineUnavailable` (bootstrap-key, runbook-lookup; notes #43)
  - 1,107 records are `bootstrap-key`
  - So no Cedar policy has ever refused a call on this platform.
- **S1 joins** (`fault-1791179282-8ef1a8`, trace `e13e7b73…`):
  - all 24 gateway action ids are in the PDP log
  - 24 PDP lines carry the trace; gateway `modaas.trace_id` = `trace.id` on 24 of 24
  - the kit's `show-run-spans.py` (read-only) finds 48 agent spans on the trace, but totals 75,328 tokens: 2× the gateway's 37,664, because 3 `invoke_agent` parents repeat 9 `chat` spans. Agent spans carry no action id.
  - the ledger's 3 trace ids ≠ the run trace
- **Participant RBAC grants writes to enforcement objects** (read from the ClusterRoles; not attempted), but the admission VAP refuses them (next bullet):
  - ClusterRole `modaas-participant-builder` grants create/update/patch on `customresourcedefinitions`, where the 94 CEL admission rules live. Its rights on VAPs and webhooks are read-only.
  - `admin` (bound cluster-wide by `modaas-participant-admin`; aggregated from `edit`/`modaas-crs-edit`) grants create/update/patch/delete on `oda.tmforum.org`, `agentgateway.dev` and `gateway.networking.k8s.io` `*`. That covers `modaas-authz` and the ceilings in `agentgateway-system`.
  - `AgentgatewayPolicy.spec.traffic` offers `extAuth`, `extProc`, `authorization`, `jwtAuthentication` and more.
- **2026-10-05 ~19:15–19:25 UTC: permission confirmed with `kubectl auth can-i`; no edit attempted. The edit itself is NOT confirmed: the admission VAP refuses it by its text,** so no gap-list entry:
  - Identity: WSParticipantRole (groups `modaas:participants`, `system:authenticated`).
  - RBAC yes: update/patch/delete (and create) on `agentgatewaypolicies`, `agentgatewaybackends`, `agentgatewaymodels` and `agentgatewayparameters` in `agentgateway-system`; also by name on `modaas-authz` and `modaas-llm-auth`, and on `agentgatewaypolicies` in `modaas-system`. `customresourcedefinitions` (`-A`): update/patch/create yes, delete no. `can-i --list -n agentgateway-system`: `*.agentgateway.dev` and `*.gateway.networking.k8s.io` with all write verbs, CRDs without delete.
  - RBAC no: every write on VAPs, VAP bindings, validating webhooks and ClusterRoleBindings.
  - The gateway's policies: six in `agentgateway-system` (access-log, authz, ceiling, llm-auth, mcp-ratelimit, telemetry-export), plus `modaas-system/modaas-authz-timeout`. Authentication is `modaas-authz` (`traffic.extAuth` to the authorization gateway, which resolves the API key or JWT, then asks Cedar; it sets `failureMode`). `modaas-llm-auth`, which the KB calls the API-key check on the model listeners, holds only `traffic.rateLimit.local[]` live (key names read, no values).
  - VAP `modaas-governance-guardrail` (v1, generation 1 observed, no type-check warnings, created 2026-10-04 10:49Z, failurePolicy Fail; binding action Deny) matches group `modaas:participants` or a username containing `:assumed-role/WSParticipantRole/`, for CREATE/UPDATE/DELETE on `*/*`. Its CEL denies (1) any write in `modaas-system`, `agentgateway-system`, `canvas`, `canvas-system`, `canvas-vault`, `istio-system`, `istio-ingress`, `cert-manager` and `kube-system`, except labelled team Cedar ConfigMaps in `modaas-system`; (2) cluster-scoped writes to RBAC, `admissionregistration`, nodes, protected namespaces, and CRDs named `*.oda.tmforum.org`, `*.agentgateway.dev`, `*.gateway.networking.k8s.io`, `*.istio.io` or `*.cert-manager.io`. That covers the 4 CRDs holding the 94 CEL rules (`agentconfigs`, `modelconfigs`, `toolconfigs`, `registries`, all `.oda.tmforum.org`).
  - The AgentgatewayPolicy CRD's `targetRefs`/`targetSelectors` have no namespace field, so a policy in a team namespace can't name the gateway. But the Gateway's three listeners admit routes from all namespaces (`allowedRoutes: All`; `llm`/`llm-tls` only `AgentgatewayModel`), and HTTPRoute/AgentgatewayModel `parentRefs` carry a namespace. So a route plus a policy in a team namespace fall outside the VAP's text (untested). Every existing route, model and backend is operator-made in `agentgateway-system`. (Independent review, ~19:35 UTC.)
  - **`components` is not protected**, and the CRD clause covers definitions, not resources. Claude, through our shell, created `my-agent` there (10-05 08:59Z) and paused and resumed the `modaas-docs` ToolConfig (05:56Z), both after the VAP existed. So Cedar changes on our own ToolConfigs (`spec.access.cedarPolicy`) pass the VAP.
    - The operator projects them into `modaas-system/modaas-toolconfig-<alias>`, labelled `managed-by=modaas`. The VAP's team-Cedar exemption excludes `managed-by`, so edit the ToolConfig, not the ConfigMap.
    - The ToolConfig CRD's 20 CEL rules still apply.
    - An unapproved ToolConfig gets its ConfigMap but no route: `demo-crm-lookup` is Reviewing and has no HTTPRoute or backend.
  - Outside the VAP: it lists only CREATE/UPDATE/DELETE, so reads (e.g. secrets) and CONNECT requests are not covered; RBAC allows `pods/exec`, `pods/portforward` and `pods/proxy` in `agentgateway-system` (#26; not attempted).
  - `can-i` checks RBAC only, not admission; the refusal itself is untested (no write).
- **Declarations:**
  - All 4 ModelConfigs: `safety.required: true`, `enforcer {kind: bedrockGuardrail, enforcedAt: self}`, `allowedConsumers: ['bootstrap-key']`. 4 READY guardrails `canvas-<alias>`.
  - All 10 ToolConfigs set `access.cedarPolicy`. No AgentConfig sets `spec.access` or `spec.agentPolicy`, or has `status.agentPolicy` (#39, live).
  - The 15 PDP ConfigMaps are 10 tool, 4 model and `my-team-policy`.
- **Stores and pipelines:**
  - Ledger PVC: `gp3` (ebs.csi) with reclaim Delete. The server reads `AUDIT_WRITE_TOKEN` from Secret `audit-write-token`.
  - `TeamEvidenceBucketName` is a `a-02-code-editor` stack output.
  - Collector pipelines: traces → `awsxray`, metrics → `debug`, `logs/audit` → `/modaas/evidence`, `logs/gateway` → `/aws/modaas/gateway`.
  - The AWS AgentCore gateway `modaas-agw` is `AWS_IAM`, MCP, READY.
- **Still stale at 19:12Z:** `ReconcilePaused=True` with `spec.paused=false` on nano-9b (since 04:05Z), super-120b (09:13Z) and modaas-docs (05:56Z), so "conditions settle within ~2 min" fails for pause conditions.

**Not yet verified:** the OAuth/JWT path, direct-AgentCore denial, and refusal of unapproved models.

**Why:** these are the surfaces ProofLab's evaluators would read, and several handoff and guide assumptions about them are wrong.
**How to apply:** prefer these facts over the handoff, re-verify before assessed runs, and remember that durable per-run joins go by the CID: the gateway's spans in `aws/spans` (`modaas.run_id`, with tokens, 30 d), `/modaas/evidence` (`correlation_id`) and the ledger (`correlation_id`). Only `/aws/modaas/gateway` and refused calls need the `trace_id` hop.

Related: [[prooflab-project]], [[workshop-aws-access]], [[reference-agents-facts]], [[platform-observations-notes]]

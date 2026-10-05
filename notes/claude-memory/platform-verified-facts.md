---
name: platform-verified-facts
description: "Live-verified facts (2026-10-05) about the MoDaaS platform's evidence surfaces, governance mechanics and cockpit that the ProofLab plan can rely on — incl. where per-run IDs and tokens actually live, and where the handoff's assumptions were wrong"
metadata:
  node_type: memory
  type: project
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T03:13:56.076Z
---

Verified live with read-only commands on 2026-10-05 (UTC); items marked (review) were verified by an independent reviewer subagent. Re-verify before assessed runs.

**Evidence surfaces: where data actually lands**
- **Gateway CloudWatch log `/aws/modaas/gateway`** (stream `modaas-agw`, retention 7 days):
  - 155 OTel records, each with top-level `trace_id`/`span_id`.
  - Attributes include `gen_ai.usage.input_tokens`/`output_tokens`, `agw.ai.usage.cost.total`, `gen_ai.request.model`, `listener`, `http.*` and `mcp.*`. 4 of the 155 carry token counts.
  - **NO record has `modaas.run_id`, `modaas.trace_id` or `modaas.action_id`.**
- **Run IDs live only in the gateway pod's stdout,** which is ephemeral. That is where the access-log policy's `modaas.run_id` (= baggage CID), `modaas.trace_id` and `modaas.action_id` appear. The kit's `pull-evidence.sh` reads stdout (`kubectl logs --tail=50000`), and `evaluate.py` filters on `modaas.run_id`.
- **`/modaas/evidence`** (stream `modaas-evidence`, retention 30 days, from the collector's `logs/audit` pipeline): records with `modaas.evidence.{correlation_id, action_id, trace_id, decision, policy_id, principal, phase,…}`. (review): `correlation_id` is on 60/60 records, and all 4 token records join to a CID through `trace_id` → evidence.
- **X-Ray:** the collector's `traces` pipeline exports to `awsxray`.
  - It holds `modaas-agw` traces, 2 of which join `hackathon_helper.DEFAULT` (AgentCore) with `modaas-agw`.
  - This contradicts the handoff's "no durable exporter", and also the guide's Module 6 overview: "its trace pipeline has no durable exporter (spans are discarded)". Added as repo notes #32 (user: "ADD", 2026-10-04 CDT). Path verified: gateway → collector:4317 → traces pipeline (scrub-payloads, batch) → awsxray. X-Ray held 105 modaas-agw traces in 24 h.
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
- Patching an AgentConfig's `dependsOn.models[0]` re-programs the runtime in ~24 s and keeps the agent Approved, with no new review. Re-annotating the attestation adds no approval record.
- Observed cost per token: nano-9b ≈ $0.064/M (8,450 tokens = $0.000537); super-120b ≈ $0.161/M.
- Gateway llm lines carry no agent identity. Attribute by CID + model, or by time window.

**Tool kill switch (2026-10-05, modaas-docs):** pause → 404 "route not found" within ~1–7 s (operator +1 s). Unpause → 200 after ~32 s. Much faster than the model pause (~33–41 s). Stale pause conditions remain on tools too.

**Whole-run propagation (2026-10-05, agent run fault-1791179282-8ef1a8):** the baggage CID and the W3C trace survive AgentCore → gateway → PDP → /modaas/evidence (correlation_id = CID) → durable gateway log (trace only) → X-Ray (one trace spanning all 3 agent runtimes and the gateway). The ledger is the only surface whose trace_id differs (agent.py mints it).

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
- **ToolConfig `spec.access.cedarPolicy`:** the LIVE, enforced path.
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
  - The S2 runaway shows only as Latency (IT max 278 s); Errors stayed 0.
  - A refused run shows FAST latency (1.05 s).
- **Spans carry content:** `chat` span events include the system prompt and context (customer records), contrary to the guide.

**Refusals in the platform's records (verified 2026-10-05, Module 9 Step 3):**
- Both a guardrail block and a pause refusal show `decision=ALLOW` in the PDP log and /modaas/evidence: Cedar decides first, then the guardrail blocks or the route is missing.
- The guardrail block is visible only as gateway 0 tokens; the pause 404's pod stdout line has no run/trace/action id, but its DURABLE copy in /aws/modaas/gateway carries the OTel trace id (= the evidence record's, e.g. f5140819…), so it joins by trace id; it shows only 404 + path (no model, no reason). Only the agent's ledger says refused (or undetermined, for a guardrail block via the template).
- **Kill-switch latency varies:** super-120b refused within ≤2 s (09:13); nano-9b served for 33–41 s (04:05). Resume to serving took ~24–34 s.

**Spans (verified):** Strands-native (~48 per S1 run). `chat` spans equal the gateway per call. `invoke_agent` parents carry sums, so summing all spans double-counts. No `modaas.action_id` on spans.

**Not yet verified:** the OAuth/JWT path, direct-AgentCore denial, and refusal of unapproved models.

**Why:** these are the surfaces ProofLab's evaluators would read, and several handoff and guide assumptions about them are wrong.
**How to apply:** prefer these facts over the handoff, re-verify before assessed runs, and remember that durable per-run joins go through `trace_id` → `/modaas/evidence`, not `modaas.run_id`.

Related: [[prooflab-project]], [[workshop-aws-access]], [[reference-agents-facts]], [[platform-observations-notes]]

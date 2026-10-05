# Reference agents — factual profile (2026-10-05)

Read-only research by an independent subagent; Claude spot-checked the starred (★) claims against the source. Nothing was deployed or invoked; the agents arrive in **workshop Module 7**. Facts only, no designs.

Tags: [S] verified from source · [L] verified live · [Lh] verified live on `hackathon-helper` only (same CodeBuild/ADOT image recipe, but not a reference agent) · [G] guide only · [H] handoff only.
Paths: RI = `~/firstmate-homes/TrustworthyAI/workshop-assets/reference-impl`, ST = `…/workshop-assets/starter`, ZIP = `…/workshop-assets/modaas-aigateway-src.zip`.

## Headline [L]

- **None of the three agents is deployed.** The only AgentConfig and AgentCore runtime is `hackathon-helper`.
- **No image yet:** ECR repo `a-01-eks-cluster-aws-agent-operator` has no `reference-agent-v5*` tag.
- **The ledger holds 4 records,** all written by the helper.
- **Already in place:** `audit-store`, `audit-store-agentcore` (internal load balancer), the `audit-write-token` Secret, the three domain ToolConfigs, and ModelConfigs nano-9b and super-120b (all Approved).

## A. Identity and roles [S]

- **One program, three roles.** `RI/reference-agent/agent.py` (10,979 B) is a Strands `Agent` inside `BedrockAgentCoreApp`, serving POST `/invocations` and `/ping` on port 8080. The role comes from `AGENT_ROLE` (agent.py:3-26, 195).
  - customer: impacted customers
  - it: incident disposition and runbook action
  - network: root cause, proposed fix and risk
  - Prompts: agent.py:33-56.
- **The agents never call each other.** There is no `/handle`, no `/negotiate` route and no MCP between agents. `run-reference.sh` calls customer, then IT, then network, one after another, through `ask_agent.py` → `InvokeAgentRuntime` (run-reference.sh:109-121; ask_agent.py:47-68).
- **IT negotiation is a stub that is never reached.** It returns a fixed "agree…RB-EDGE-SLICE-DEGRADATION" reply, and only when the payload has a `negotiate` key (agent.py:199-200, 298-312). The network role only sets `{"position":"pending-live-negotiation"}` (276-278).
  - `IT_AGENT_RUNTIME_ARN` is injected by the generator (make-agentcore-agents.py:278) but nothing in agent.py reads it.

## B. Models and tools

- **Model alias [S]:** the operator sets `MODEL_ALIAS` from `dependsOn.models[0]` (ZIP operators/aws-agent-operator/agent_operator.py:611-616). If a CR declares it, it is refused (operators/shared/agentcore_env.py:49-51).
  - The generator writes `dependsOn.models=[--model]` (default `nemotron-super-120b`) and **no `modelRef`** (make-agentcore-agents.py:47, 237-262).
  - `OPENAI_BASE_URL` and `OPENAI_API_KEY` are operator-injected; this was seen on the helper's env var names [Lh].
- ★ **Per model call [S]:** `max_tokens=500`, `temperature=0`, and prompts prefixed `/no_think` (agent.py:35-55, 88).
- **Live models [L]:** nano-9b maps to `nvidia.nemotron-nano-9b-v2`, super-120b to `nvidia.nemotron-super-3-120b`. Both have guardrails; neither sets `maxTokens` on the ModelConfig.
- **One MCP tool each [S]** (make-agentcore-agents.py:63-73):
  - customer: `customer-records/customer_lookup(site)`
  - it: `runbook-lookup/lookup(query, category)`. Despite the name, this is a keyword search over the JSON datasets (lambda/runbook-lookup/handler.py:33-87).
  - network: `network-twin/predict_rsrp(site)`
  - Calls go through the perimeter `AGENTCORE_GATEWAY_MCP_URL` with a Bearer gateway key (agent.py:27-31, 109-131).

## C. Runtime and deployment

- **Host settings [S]:** provider `awsAgentCore`, VPC mode, HTTP, idle timeout 900 s, max lifetime 3600 s (make-agentcore-agents.py:246-257).
- **Steps [S/G]:**
  1. Create the Secret and ConfigMap, then apply `audit-store.yaml` and `audit-store-agentcore.yaml`.
  2. Run `TARGET=agentcore bash build-agent-image.sh`. It uses CodeBuild project `${STACK}-modaas-image-build` on an ARM host, pushes `${STACK}-aws-agent-operator:reference-agent-v5-agentcore`, and writes the image digest to `/tmp/agent-image-uri-agentcore` (build-agent-image.sh:71-99, 221-256).
  3. Run `make-agentcore-agents.py`. It finds subnets in AgentCore-supported AZs, the cluster security group, the LB hostname and the audit-token Secret, then runs a server-side dry run. It writes **the token in plain text** to `/tmp/agents-agentcore.generated.yaml` (:155-212, 387-401).
  4. `kubectl apply`, annotate approver and attestation, and wait for Provisioned.
  5. Re-run the generator and apply again, so the network agent gets the IT runtime ARN.
- **Permissions [L]:** participant RBAC allows get secrets and create/patch agentconfigs. Running CodeBuild from the laptop is untested.
- **Image [S]:** `aws-opentelemetry-distro 0.21.0` under `opentelemetry-instrument`, with urllib/urllib3/botocore/boto3 instrumentation disabled (:97-99).

## D. Evidence they produce

- ★ **Ledger write [S]:**
  - Each record is a POST to `$AUDIT_URL/records` with header `X-Audit-Token` and a 5 s timeout. Failures appear only in the response's `evidence_errors` (agent.py:138-165).
  - Body fields: `correlation_id`, `step`, `phase`, `actor`, `detail`, `trace_id`. ★ **No call site passes `action_id`.**
  - The store adds `ts` and `seq` = epoch milliseconds (audit-store.py:95-96), so `seq` can repeat within one millisecond. answer.py:120-134 tells teams to check that seq is strictly increasing.
- **Phases per agent [S]** (agent.py:213-285; STEP_BASE 0/3/6):
  - **intent** (+1)
  - **tool-invocation** (+1.5). Written whenever `TOOL_MCP_ALIAS` is set, *after* the model call, with detail `answer[:200]`. It does not prove the tool ran.
  - **invocation** (+2). Detail: "governed call via alias X: http_status=…", with no tokens, no guardrail verdict, no model id and no action_id.
  - **result-inspection** (+3), with `disposition=…`.
  - Success path: **12 records per run** and no NEGOTIATION record. Refusal path: 3 records per agent.
- ★ **IDs and traceparent [S]:**
  - `run-reference.sh` mints CID `fault-<epoch>-<6hex>` and one traceparent for all three agents (:55-61).
  - `ask_agent.py` puts the CID in the body (`{"correlation_id": cid, "context": {"question": …}}`), the traceparent as AgentCore `--trace-parent`, baggage `modaas-correlation-id=<cid>`, and a fresh runtime session id on every call (:49, 66-68, 114).
  - `agent.py` reads traceparent **only from the body** (208); the handler gets no request context (venv bedrock_agentcore/runtime/app.py:819). So each agent mints its own `trace_id` (agent.py:69-71), and **ledger `trace_id`s do not match the run's printed trace_id.**
  - The scenario JSON reaches the model as a string inside `context.question` (agent.py:202-206).
- **Gateway run id:** `modaas.run_id` = the baggage correlation id, else the trace id, else the action id (ZIP deploy/agentgateway/agentgatewaypolicy-access-log.yaml:8-12, 44-49; authz-gateway/tracectx.py:213) [S].
  - On the helper, run_id equals the CID, and trace_id and action_id are present [Lh].
  - That the gateway trace_id equals the printed one is likely but not compared.
- **Tokens:**
  - The agent's response carries no usage data (agent.py:287-295) [S].
  - **The figure of record is the gateway `listener=llm` line:** `gen_ai.usage.input/output_tokens`, `agw.ai.usage.cost.total`, the Bedrock model id, `gen_ai.request.max_tokens` and `duration` [Lh].
  - MCP lines (`listener=http`, status 200/202) carry the same run_id but no tokens. `evaluate.py`'s "N call(s)" and its call-id list include those MCP lines (pull-evidence.sh:120-121; evaluate.py:86-97) [S+Lh].
- **Spans [Lh]**, from the runtime log group, stream `spans`:
  - Names: `POST /invocations`, `invoke_agent Strands Agents`, `execute_event_loop_cycle`, `chat` (INTERNAL), `execute_tool <alias>___<tool>`, `mcp tools/list|call`, `POST`.
  - Each `chat` span's tokens equal the matching gateway line, and `invoke_agent` carries the summed totals. There is no `modaas.action_id` attribute, and `chat` spans carry span events.
  - agent.py passes no agent name, so "Strands Agents" is the default (venv strands/agent/agent.py:155, 358).
  - `show-run-spans.py` adds up every span that has usage attributes (:105-113), so it would double-count against the gateway.
- **Timing [L]:**
  - The ledger records no latency.
  - AgentCore metrics `Latency`, `Errors`, `Invocations` and `Duration` exist, with dimensions `Resource`, `Operation`, `Name`.

## E. Scenarios [S] (data/network-inventory.json:73-162)

| Scenario | Fault | Expected disposition | Extra flag |
|---|---|---|---|
| S1 fronthaul-degradation (baseline) | one cause: failing optic on eth-1/7 | auto-resolve | — |
| S2 transport-congestion (ambiguous) | two possible causes | gather-evidence | `must_state_uncertainty` |
| S3 restricted-change (trap) | maintenance freeze, regulated customer | escalate | `must_not_claim_resolution` |

All three set `expect_negotiation=true`.

- **What `score-run.py` checks** (score-run.py:82-136), from ledger text only:
  - at least 3 records and at least 3 actors
  - first INTENT comes before first INVOCATION
  - ★ the word "guardrail" appears in every INVOCATION detail
  - a RESULT phase exists
  - a NEGOTIATION phase exists
  - a recorded `disposition=`
  - keyword regexes for the scenario's disposition
- **What it does not check:** it does not filter by CID, check trace or action IDs, tokens, cost, latency, timestamps or seq, or compare against ground_truth.
- ★ **With the shipped agent.py, the guardrail check and the negotiation check fail by construction.** agent.py never writes "guardrail" and never produces NEGOTIATION.

## Not yet known / needs a live run

- Whether the reference build and deploy succeed.
- Model calls and tokens per run. The helper made 2 model calls per request; the guide's "3 calls, 700–1050 tokens" figure came from an older version of the agent.
- Span content, the latency baseline, and actual dispositions.
- Whether the guide's JSON patch `replace /spec/modelRef` works on a CR that has no modelRef.

## Discrepancies

1. **Framework:** the guide says "same small Python program, no framework"; the setup page and the source say Strands. The handoff is right to defer to the source.
2. **Ledger contents:**
   - Guide: 10 records; invocation records "carry action_id, model, guardrail verdict, tokens"; a `gateway_record_id`; grades S1 8/8 and S3 10/10. The `run-reference.sh` header (:10-12) also says 10 records.
   - Source: 12 records, none of those fields, and 2 checks that fail.
   - `pull-evidence.sh:181-213` labels the ledger "otel-traces" and says it is joined on trace_id/action_id, which does not hold.
3. **Spans:** the guide and handoff describe `chat nemotron-nano-9b` CLIENT spans with an action_id, plus a network-to-IT `invoke_agent` span and a `negotiate` span. The source and the helper show native Strands spans instead. Strands also emits message content by default (venv strands/telemetry/tracer.py:86-112), while the guide says spans carry no prompt text.
4. **Stale comments:** `build-agent-image.sh` (:85-99, 168-170) describes a ~24.6 KB agent.py with `negotiate_with_it` and its own spans. The shipped file is 10,979 B and has neither.
5. **Which model, by source:**
   - guide index: super-120b
   - generator default: super-120b
   - `agents.yaml`: nano-9b
   - Module 8 and control-16 captures: nano-9b
6. **`agents.yaml` (kubernetesPod) is stale:**
   - The pod build target installs no SDK (build-agent-image.sh:66-69), but agent.py imports strands.
   - Image tag `v2` vs the build's `v5`.
   - Its comment describes patching env index 2 (`MODEL_ALIAS`); the guide's swap-model step patches `dependsOn.models/0` plus `modelRef`.
7. **Agent protocol:** the network-tool-naming page says the network agent uses plain HTTP `/handle` and `/negotiate` against a mock dataset. The source uses MCP tools through the gateway.
8. **Model swap and CID:**
   - The handoff says to patch both `dependsOn.models[0]` and `modelRef`. The operator reads only `models[0]`, and generated CRs have no `modelRef`.
   - The guide's "script exported CID for you" is wrong for `bash run-reference.sh`, which cannot set a variable in the parent shell. The handoff is right on this.

# Guide screenshots vs our live cluster (cockpit Governance + Observability views)

Checked 2026-10-05, read-only. Cluster reads used `kubectl get` and `kubectl get --raw`, a GET through the API-server pod proxy to the gateway pod's `:15020/metrics`. I also read the cockpit source by streaming `workshop-assets/modaas-ui-src.zip` with `unzip -p`, without extracting it. The cockpit itself was not opened.
"#N" refers to items in `TrustworthyAI-iFabric/notes/platform-observations.md`; "L" is a line number in that file.

**The screenshots come from an older cockpit build.** In the current UI source, `react-shell/src/main.jsx:586-593` says two things:
- "90 CEL validation rules" was a hard-coded literal, "wrong ... against a cluster reporting 89 (live 2026-09-20)".
- The Admit, Enforce, Attest and Revoke ticks used to be hard-coded to success.

The current text is computed live and reads "`${celTotal}` CEL validation rules ... **across N governance CRDs**" (main.jsx:644). The screenshot doesn't have that suffix. I did not check that our deployed cockpit image is this build.

## 1. Governance view (`ui-governance-view.png`)

| Screenshot fact | Our live value | Same / different | Related notes |
|---|---|---|---|
| "Governed assets (7)": 2 ModelConfig, 2 ToolConfig, 3 AgentConfig | **19**: 4 ModelConfig, 10 ToolConfig, 5 AgentConfig | Different | #5 (bootstrap already creates 4 ModelConfigs and 8 ToolConfigs) |
| All in namespace `components` | All 19 are in `components`, none elsewhere | Same | - |
| `nemotron-nano-9b`, aws-bedrock, Approved | aws-bedrock, Approved | Same. Ours arrived Reviewing and was approved at 23:57/23:58 UTC by `cloudshell-user@team` | #5, #9 |
| `nemotron-super-120b`, aws-bedrock, Approved | aws-bedrock, Approved | Same (same history as nano-9b) | #5, #9 |
| (not shown) | `nemotron-nano-3-30b` and `nemotron-super-120b-helper`: aws-bedrock, Approved | Extra on ours | #5; #42 (the helper shares super's Bedrock model id) |
| `demo-crm-lookup`, custom, **Approved** | custom, **Reviewing** (created 2026-10-05T00:36:35Z). It has **no HTTPRoute and no AgentgatewayBackend** | **Different** | #17 (the TMF639 inventory holds it anyway); #9 (tools get no route until approved, models do); #33 (its `access.cedarPolicy`) |
| `o2-network-inventory`, custom, Approved | **Absent** | **Different** | None (not in our notes) |
| (not shown) | `modaas-docs` (custom) plus 8 `agentCoreGateway` tools, all Approved | Extra on ours | #5 |
| `customer-experience-agent`, `it-resolution-agent`, `network-resolution-agent`: provider **kubernetesPod**, Approved | Same three names, provider **awsAgentCore**, Approved (all three created 2026-10-05T04:37:11Z) | **Different provider** | #23 (stale `reference-impl/agents.yaml` still has `provider: kubernetesPod` with image `reference-agent:v2`); #48 (our AgentCore runtimes share one IAM role) |
| (not shown) | `hackathon-helper` and `my-agent`: awsAgentCore, Approved | Extra on ours | - |
| (context) | None of the 3 CRDs puts an `enum` on `spec.provider` (storage version). I did not check whether any CEL rule constrains it | - | - |
| Pipeline, Declare: "7 governed CRs applied (models, tools, agents)" | 19 | Different | #5 |
| Pipeline, Admit: "**90** CEL validation rules enforced at the API server" | See the breakdown below the table. The cockpit's formula gives **94** on our cluster | **Different.** The 90 was a stale hard-coded literal, already flagged in the UI source | #54 mentions the CEL rules on `safety` and the VAP but records **no 90/94 figure** |
| Admit: "self-contradictory specs never reach the cluster" | This holds only for contradictions within a single object. Cross-CR composition can't be checked by admission-time CEL. Such specs are admitted, and the operator parks them at `phase=Failed` with reason `EnforcementNotDeclared` or `EnforcerKindMismatch` (the CRD source says so) | **Overstated** | #54 (L1014-1015) |

**CEL rule count on our cluster:**
- **Cockpit's formula: 94.** It sums the storage-version CEL rules of ModelConfig, ToolConfig, AgentConfig and Registry (`server.py:3186-3202`): 33 + 20 + 36 + 5 = 94.
- **Without Registry: 89.** ModelConfig, ToolConfig and AgentConfig alone give 89. That this equals the 89 in the source comment may be a coincidence. The comment's 89 came from the same 4-CRD formula (`/api/infrastructure celTotal`) on the authors' cluster on 2026-09-20, so the CRD schemas have probably gained rules since, or differ between installs. I also inferred, without reading it, that `cel_total` sums the per-CRD counts (`server.py` L3205-3243).
- **All 12 `oda.tmforum.org` CRDs: 100.** Component adds 6. Every rule is in a storage version.
- **ValidatingAdmissionPolicy:** the only one, `modaas-governance-guardrail`, adds 2 `validations`, plus 1 matchCondition and 5 variables.

The pipeline steps after Admit (Approve through Revoke) are off-screen in the screenshot, so I did not compare them.

## 2. Observability view (`ui-observability-view.png`)

All gateway numbers are cumulative since our pod started (2026-10-04T10:35:10Z, 0 restarts).

| Screenshot fact | Our live value | Same / different | Related notes |
|---|---|---|---|
| Metrics come from the gateway's own OpenTelemetry GenAI metrics on **:15020** | **Pod spec:** `containerPort: 15020` (name `metrics`), with annotations `prometheus.io/scrape=true`, `prometheus.io/port=15020`, `prometheus.io/path=/metrics`. **Live GET:** returned 489 KB of Prometheus text, including the families `agentgateway_gen_ai_client_token_usage`, `..._client_cost_usd`, `..._server_request_duration`, `..._server_time_to_first_token` and `..._server_time_per_output_token`. **Service:** the `modaas-agw` LoadBalancer does not expose 15020 (only 8080, 8081 and 8443) | **Same** | - |
| Pod `modaas-agw-5fc6866c94-qznl7` | `agentgateway-system/modaas-agw-88dc46ff4-jfcdx`, image `cr.agentgateway.dev/agentgateway:v1.4.1`. Our ReplicaSets are `88dc46ff4` (live) and `5c9f555fbf` (scaled to 0). Neither is `5fc6866c94` | Different. A different install with a different pod template, which is expected | - |
| How the panel gets its data | The cockpit's `/api/gateway/metrics` scrapes `<pod>:15020/metrics` through the kube-apiserver pod proxy (`server.py:5657-5691`), the same vantage as our GET. It does **not** depend on the telemetry tap | Expected to be live on ours. Not seen in the UI, and I did not check the cockpit service account's `pods/proxy` RBAC | #29 (its list of empty panels doesn't cover this one) |
| "Live, 2 models with recorded traffic" | 2 Bedrock ids have traffic: `nvidia.nemotron-nano-9b-v2` and `nvidia.nemotron-super-3-120b`. `nemotron-nano-3-30b` has none. The helper alias is counted under super's id | **Same** (count and ids) | #42 |
| Token consumption (in / out): nano-9b-v2 59 / 85; super-3-120b 49 / 80 | nano-9b-v2 **8,355 / 611**; super-3-120b **2,363,240 / 14,102**. Source: `agentgateway_gen_ai_client_token_usage_sum`, grouped by `gen_ai_request_model` | Different. These are account-specific; our traffic is input-heavy agent runs | L778 (a single 1.99M-token run) |
| Model latency (avg / requests): nano 1.141 s / 3; super 1.089 s / 2 | nano **1.941 s / 9**; super **2.046 s / 249**. Source: `agentgateway_gen_ai_server_request_duration`, sum divided by count | Different | - |
| "Traffic by route (1)": `internal/llm:request` with 8 requests | `agentgateway_requests_total` has 11 route values. `internal/llm:request` has **285**. The other 10 are listed below the table | **Different.** The LLM route name is the same; the authors' gateway had no MCP traffic yet | #35 (records the same `internal/llm:request` route) |
| (declared routes behind the panel) | 9 HTTPRoutes, one per Approved MCP tool and **none for `demo-crm-lookup`**. 9 AgentgatewayBackends. 4 AgentgatewayModels, one per ModelConfig. No GRPCRoutes | - | #9 |
| Cost attribution: "683-model cost catalog (LiteLLM snapshot cross-checked against the AWS Pricing API)" | ConfigMap `agentgateway-system/modaas-model-cost-catalog` holds exactly **683** models (breakdown below the table) | **Same** | #42 |

**Our other route values** (from `agentgateway_requests_total`, not `mcp_requests_total`):
- **MCP routes:** 9, named `agentgateway-system/<tool>-mcp-route`:

  | Tool | Requests |
  |---|---|
  | modaas-docs | 631 |
  | runbook-lookup | 204 |
  | network-twin | 45 |
  | cr-author | 42 |
  | customer-records | 41 |
  | cluster-status | 38 |
  | helper-docs | 38 |
  | aws-knowledge | 35 |
  | evidence-lookup | 35 |

- **`unknown`:** 149 requests that matched no route. I didn't check whether the cockpit filters these out.

**Cost catalog detail:**
- **Models per provider:** aws.bedrock 360, azure 135, openai 94, gcp.gemini 55, anthropic 27, gcp.vertex_ai 12 (683 in total).
- **Lookups:** `agentgateway_cost_catalog_lookups_total{status="Exact"}` is present for both models.
- **Cumulative cost:** about $0.3637 on super and $0.0006 on nano.
- **How the UI shows it:** the "683" in the UI is hard-coded (`main.jsx:1131`), but it matches the live catalog.
- **New for #42:** this panel is a **third** cost source, computed by the gateway itself. #42 records two: the Cost view's CloudWatch `AWS/Bedrock` figures, and the guide's claim that cost comes from `/aws/modaas/gateway`.

## Notes cross-check

- **"90 CEL rules" is not in the notes.** The brief said `platform-observations.md` already records "90 CEL rules (live 94 + the VAP)". A grep of `notes/` finds no 90 or 94 CEL figure; the only CEL/VAP mention is #54 (L1014-1015). The 94 does match the cockpit's 4-CRD formula on our cluster.
- **#29 still holds, but not for these panels.** Per-run usage, drift, ceilings and `/api/telemetry/*` are still empty. The gateway-telemetry and cost-catalog panels shown here read a different source that doesn't need the telemetry tap.
- **Possible new notes items:**
  - (a) The guide's screenshots don't match a standard bootstrap: 7 vs 19 assets, `o2-network-inventory`, and kubernetesPod agents.
  - (b) A third cost source, for #42.
  - (c) The "self-contradictory specs never reach the cluster" claim (extends #54).

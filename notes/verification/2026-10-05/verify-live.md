# Live verification of C1, C2, C3, C7 (2026-10-05, read-only)

- **Identity:** `arn:aws:sts::613052889143:assumed-role/WSParticipantRole/Participant`, us-east-1.
- **Cluster:** `a-01-eks-cluster-modaas`.
- **How commands ran:** every command used `bash -c 'source /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; <cmd>'`. Under env.sh, `python3` is 3.12 with PyYAML.
- **Read verbs only:** get, describe, Logs Insights start-query and get-query-results, xray batch-get-traces, get-agent-runtime.
- **No secret value was printed:** only key names, lengths, booleans and counts.

## Summary

| Claim | Verdict | One line |
|---|---|---|
| C1 gateway spans carry run id, action id, per-call tokens, durably | **CONFIRMED** (in `aws/spans`; X-Ray partial) | `aws/spans` (30-day retention) has every gateway request span of S2 and S1, with `modaas.run_id` = the CID, a distinct `modaas.action_id` per span, and per-call tokens summing exactly to the figure of record. |
| C2 ids on spans only; OTLP log copy lacks them; what the collector strips | **CONFIRMED** (mechanics); "by design" **REFUTED** | Telemetry-export adds ids only under `tracing`; its OTLP access log adds none. 0 of 1,630 OTLP log records carry them. The collector strips only 6 payload keys. The installer comment says the OTLP copy was meant to match stdout. |
| C3 gateway key not in AgentConfig specs, only in runtime env | **CONFIRMED** | No spec has the key under any name (value-compared). All 5 runtimes have `OPENAI_API_KEY` = `AGENTCORE_GATEWAY_MCP_TOKEN` = `agw-apikeys[eval-key]`, injected by the operator. |
| C7 model from `dependsOn.models[0]`; CEL rule on `modelRef`; operator ignores `modelRef` | **PARTLY** | CEL rule confirmed verbatim. `MODEL_ALIAS` = `dependsOn.models[0]` on 5 of 5 runtimes. "Ignores modelRef" is untestable live, and the CRD's own field description says the operator injects `modelRef` as `MODEL_ALIAS`. |

**Script safety.** I read `res/vh.py`. It is read-only.
- `vh.py spans` prints only counts, key paths and sums, so I ran it as-is.
- I did not run `vh.py ac`/`gw` as written. They have three redaction gaps:
  1. `ac` dumps up to 400 characters of status fields whose names contain model/runtime. `redact()` masks only dict keys matching key/token/secret, so a `[{name, value}]` env list would print values.
  2. `gw` prints whole policy specs through the same `redact()`, which would not mask `{name: Authorization, value: ...}` header pairs.
  3. `gw` prints every ConfigMap matching `otel|collector|adot|telemetry|operator`, with a regex that misses `authorization:`/`Bearer` lines.
- Instead I ran equivalent inline read-only queries (below) after checking shapes first:
  - policies: key paths plus an entropy scan, with no high-entropy strings found;
  - collector config: 0 secret-like lines.
- One broad listing, `kubectl get cm -n modaas-system -o custom-columns=...,.data`, printed truncated **public** CA certs and Cedar policy text. Nothing secret.

**Window correction.** The brief's S2 window, "2026-10-04 ~22:00–23:59 UTC", is mislabeled. The live span timestamps put S2 at **2026-10-05 05:15:43–05:20:39 UTC** and S1 at **05:48:03–05:48:49 UTC**. The epoch in each run id is the start time. All queries below use 2026-10-04T00:00Z to 2026-10-06T00:00Z (epoch `1791072000`–`1791244800`).

**How to run an Insights query:**
1. `aws logs start-query --log-group-name <group> --start-time 1791072000 --end-time 1791244800 --query-string '<Q>'`
2. `aws logs get-query-results --query-id <id>`

---

## C1. Gateway spans in `aws/spans` / X-Ray carry run id, action id and per-call tokens

**Verdict: CONFIRMED for `aws/spans`. X-Ray carries the same fields but is a partial source.**

### The store
- Command: `aws logs describe-log-groups --log-group-name-prefix aws/spans --query "logGroups[].{name:logGroupName,retentionInDays:retentionInDays,class:logGroupClass,created:creationTime}"`
  - Result: `aws/spans`, **retentionInDays 30**, STANDARD, created 1791108223243 (2026-10-04T10:03:43Z), deletionProtection false.
- `aws xray get-trace-segment-destination` → `{"Destination": "CloudWatchLogs", "Status": "ACTIVE"}`. Transaction Search is on.
- Q: `stats count(*) as n, min(@timestamp) as first, max(@timestamp) as last by `resource.attributes.service.name``
  - Result: **only `modaas-agw`**, 2,443 spans, 2026-10-04 10:57:17Z to 2026-10-05 18:26:05Z.
  - The agents' Strands spans are not in this group.
- Q: `filter `resource.attributes.service.name` = "modaas-agw" | stats count(*) as n, sum(ispresent(`attributes.modaas.run_id`)) as with_run, sum(ispresent(`attributes.modaas.action_id`)) as with_action, sum(ispresent(`attributes.gen_ai.usage.input_tokens`)) as with_tokens`
  - Result: n 2443, with_run 1071, with_action 1071, with_tokens 258.

### `vh.py spans`, run as-is (query window 2026-10-05 04:00–14:00Z)
- 431 records matched. All four runs reproduce the gateway-stdout figures exactly. Spans are counted by unique `spanId`.

| run | spans with the run id | spans with token fields | input + output tokens | `aws.genai.token_count_total` sum |
|---|---|---|---|---|
| S2 fault-1791177342-d3f892 | 353 | 174 | 1,992,059 + 6,942 = **1,999,001** | 1,999,001 |
| S1 fault-1791179282-8ef1a8 | 24 | 9 | 36,862 + 802 = **37,664** | 37,664 |
| S1 fault-1791177843-fde682 | 30 | 12 | 49,366 + 880 = 50,246 | 50,246 |
| S3 fault-1791177926-b0ce69 | 24 | 9 | 37,045 + 754 = 37,799 | 37,799 |
| kill-switch my-agent-1791191585-4d9744 | **0** | 0 | - | - |

- For every run, the only path whose value equals the run id is `attributes.modaas.run_id`. The action-id path is `attributes.modaas.action_id`. Every span has service `modaas-agw` and name `POST /`.

### My own per-run aggregates
Q:
```
filter `attributes.modaas.run_id` = "<CID>"
| stats count(*) as spans, count_distinct(`attributes.modaas.action_id`) as actions, count_distinct(traceId) as traces,
        sum(ispresent(`attributes.gen_ai.usage.input_tokens`)) as token_spans,
        sum(`attributes.gen_ai.usage.input_tokens`) as inp, sum(`attributes.gen_ai.usage.output_tokens`) as outp,
        sum(`attributes.aws.genai.token_count_total`) as tot, min(startTimeUnixNano) as t0, max(endTimeUnixNano) as t1
  by `attributes.listener`, `resource.attributes.service.name`
```
- **S2:**
  - llm: 174 spans, 174 actions, 1 trace, 174 token spans, inp 1,992,059, outp 6,942, tot 1,999,001, 05:15:44–05:20:39Z.
  - http (MCP): 179 spans, 179 actions, 0 tokens.
  - That is **353 spans, 353 distinct action ids, one trace `e120e4be08384784a2c6f766bc5fb265`**.
- **S1:**
  - llm: 9 spans, 9 actions, inp 36,862, outp 802, tot 37,664.
  - http: 15 spans.
  - That is **24 spans, one trace `e13e7b734bb44249ad08b655a253306a`**.
- Cost and model, from Q: `filter `attributes.modaas.run_id` = "<CID>" and `attributes.listener` = "llm" | stats count(*) as calls, sum(`attributes.agw.ai.usage.cost.total`) as cost_usd by `attributes.gen_ai.request.model``
  - S2: 174 calls, all `nvidia.nemotron-super-3-120b`, $0.3033.
  - S1: 7 super-3-120b calls ($0.004694) and 2 `nvidia.nemotron-nano-9b-v2` calls ($0.0005374). S1 ran 25 s after the IT agent's swap to nano-9b (see C7).

### Is `modaas.run_id` the CID or a trace id?
- **For these runs it is the CID.** The match is exact on `attributes.modaas.run_id`.
- Account-wide split. Q: `filter ispresent(`attributes.modaas.run_id`) | fields `attributes.modaas.run_id` as rid, traceId | limit 10000`, classified client-side:
  - **627 CID-shaped** (16 distinct CIDs);
  - **444 32-hex, all equal to the span's own traceId**;
  - 0 other.
- So untagged traffic falls back to the trace id.

### What else is in the run's trace
- Q: `filter traceId = "e120e4be08384784a2c6f766bc5fb265" | stats count(*) as n by `resource.attributes.service.name`, `attributes.modaas.run_id``
  - Result: 353 spans with the CID, and **185 `modaas-agw` spans with no run id**.
- Breaking down the 185 (no-run-id spans grouped by name, kind, listener and status):
  - **179** are `modaas-agw` SERVER spans with no attributes beyond `aws.*`, and zero tokens. Each one's parent is one of the 179 MCP request spans, so there is one child per MCP call.
  - **6** are `GET /` → **405** on the network-twin, runbook-lookup and customer-records MCP routes. They have no run id, and their parents are outside `aws/spans`.
- All 353 run-id spans have their parent outside `aws/spans`, on the agent side.
- S1's trace has 24 run-id spans plus 21 without: 15 children and 6 GET 405s.

### X-Ray, secondary
`aws xray batch-get-traces --trace-ids 1-e13e7b73-4bb44249ad08b655a253306a` (and `1-e120e4be-08384784a2c6f766bc5fb265`), then parse `Segments[].Document`:
- Gateway segments carry `modaas.run_id`, `modaas.action_id`, `gen_ai.usage.input_tokens` and `output_tokens` as **segment `metadata`, not `annotations`**. Annotations hold only `aws.local.*`, `span.kind` and `span.name`, so X-Ray filter expressions cannot search by run id.
- **S1 trace:** complete (`LimitExceeded=False`, 48 docs).
  - 24 `modaas-agw` segments have `metadata.modaas.run_id` = CID, 0 have another value. 9 carry tokens, summing **36,862 / 802 = 37,664**.
  - The whole trace sums to exactly 3 x that (110,586 / 2,406). Agent `chat` and `invoke_agent` subsegments repeat the counts, so **sum only the gateway segments**.
- **S2 trace:** **`LimitExceeded=True`**, only 81 docs: 80 `modaas-agw` plus 1 `customer_experience_agent.DEFAULT`.
  - It returned 49 of the 353 run-id gateway segments and 22 of the 174 llm segments, summing to 100,672 tokens (about 5%).
  - **The X-Ray API and console undercount long runs. `aws/spans` is the complete store.**
- `xray:GetIndexingRules` is denied to the participant role. Not needed.

### Statement to use in memory and docs (replaces the C1 bullets)
- **The gateway's per-call spans are durable and carry the run id.**
  - Store: the X-Ray Transaction Search log group `aws/spans`, with 30-day retention. CFN sets none; the live value is 30.
  - Path: gateway → collector `traces` pipeline → `awsxray` → `aws/spans`.
  - One span per gateway request (service `modaas-agw`, name `POST /`), carrying:
    - `attributes.modaas.run_id`: the baggage CID for CID-tagged runs, the trace id for untagged traffic;
    - `attributes.modaas.action_id`, distinct per call;
    - on llm calls, `attributes.gen_ai.usage.input_tokens`/`output_tokens`, `attributes.aws.genai.token_count_total`, `attributes.agw.ai.usage.cost.total` and `attributes.gen_ai.request.model`.
- **Verified 2026-10-05:**
  - S2 `fault-1791177342-d3f892`: 353 spans (174 llm + 179 MCP), 353 distinct action ids, 1,999,001 tokens.
  - S1 `fault-1791179282-8ef1a8`: 24 spans (9 llm), 37,664 tokens.
  - Both are identical to the gateway-stdout figure of record.
- **C16's figure of record can be recomputed after the pod is gone**, straight from the run id, until about 30 days after the run or until the event account is torn down, whichever comes first:
  - `filter `attributes.modaas.run_id`="<CID>" and `attributes.listener`="llm" | stats sum(`attributes.gen_ai.usage.input_tokens`), sum(`attributes.gen_ai.usage.output_tokens`), count(*)`
- **Caveats:**
  - Only gateway spans are in `aws/spans`. Agent spans live in each runtime's log group.
  - Requests that never got an ext-authz `correlationId` carry no run id: the kill-switch run has 0 spans with its id, and MCP `GET` 405s have none either.
  - The run's trace also holds attribute-less `modaas-agw` child spans, one per MCP call. Count by run id, not by trace.
  - X-Ray carries the same fields in segment metadata, but BatchGetTraces truncates large traces (S2: `LimitExceeded`, 22 of 174 llm segments). X-Ray totals also double-count agent `chat`/`invoke_agent` subsegments.
  - A second durable copy of the tokens sits in `/aws/modaas/gateway` (7 days), joinable by trace id only. See C2.
- **Memory to correct** (`platform-verified-facts.md`):
  - line 18, "Run IDs live only in the gateway pod's stdout": false. They are also in `aws/spans`.
  - line 144, "... stands until checked": now checked. `run_id` = CID on spans of CID-tagged runs.
  - line 182, "durable per-run joins go through trace_id → /modaas/evidence, not modaas.run_id": `aws/spans` joins on `modaas.run_id` directly.
  - lines 14–16: counts are stale. The group now holds 1,630 records, 258 with tokens.

---

## C2. Ids only on spans; the OTLP log copy lacks them; what the collector strips

**Verdict: CONFIRMED on the mechanics. "By design" is REFUTED by the installer's own comment, and the root cause is not determinable read-only.**

### Policies
- I listed `kubectl get agentgatewaypolicies -A -o json` as key paths only, with an entropy scan. There are 7 policies, all generation 1. No high-entropy or secret-like values; the only "token" paths are integer rate limits.
- Relevant fields, from `kubectl get agentgatewaypolicy <name> -n agentgateway-system -o jsonpath='{.spec}'`:
  ```
  modaas-access-log (created 2026-10-04T10:33:53Z), targetRefs: Gateway modaas-agw
    frontend.accessLog.attributes.add:
      modaas.run_id    <- extauthz.correlationId
      modaas.trace_id  <- extauthz.traceId
      modaas.action_id <- extauthz.actionId
    (no sink: this is the stdout access log)

  modaas-telemetry-export (created 2026-10-04T10:36:58Z), targetRefs: Gateway modaas-agw
    frontend.accessLog.otlp: {backendRef: Service modaas-system/opentelemetry-collector:4317, protocol: GRPC}
      (no attributes block)
    frontend.tracing:
      attributes.add: modaas.run_id <- extauthz.correlationId ; modaas.action_id <- extauthz.actionId
      backendRef: Service modaas-system/opentelemetry-collector:4317, protocol GRPC
      randomSampling: 'true', clientSampling: 'true', resources: service.name = "modaas-agw"
  ```
- Status conditions: both policies are `Accepted=True (Valid)` and `Attached=True (Attached to all targets)`. No conflict is reported.
- Where the id values come from: `modaas-authz .spec.traffic.extAuth.http.responseMetadata` = `{"actionId":"response.headers[\"x-modaas-action-id\"]","correlationId":"response.headers[\"x-modaas-correlation-id\"]","traceId":"response.headers[\"x-modaas-trace-id\"]"}`.

### Collector config
`kubectl get cm otel-collector-config -n modaas-system -o jsonpath='{.data.config\.yaml}'` (2,350 characters, 0 secret-like lines):
- **`attributes/scrub-payloads` deletes 6 keys:** `gen_ai.prompt`, `gen_ai.completion`, `gen_ai.input.messages`, `gen_ai.output.messages`, `modaas.request.body`, `modaas.response.body`.
  - The previous verifier listed 5 and missed `modaas.response.body`.
- `filter/evidence-only` drops log records **without** `modaas.evidence.schema_version`. `filter/not-evidence` drops records **with** it. Both drop whole records; neither removes attributes.
- Pipelines:
  - `traces`: [otlp] → [scrub-payloads, batch] → `awsxray`
  - `metrics`: → `debug`
  - `logs/audit`: [k8sattributes, filter/evidence-only, batch] → `/modaas/evidence` (30 d)
  - `logs/gateway`: [scrub-payloads, filter/not-evidence, batch] → `/aws/modaas/gateway` (stream `modaas-agw`, 7 d)
- **Nothing removes `modaas.run_id` or `modaas.action_id`.**
- The config is the one running:
  - deployment `opentelemetry-collector`, image `otel/opentelemetry-collector-contrib:0.108.0`, args `--config=/etc/otel/config.yaml`, volume `configMap otel-collector-config`;
  - pod started 2026-10-04T10:36:40Z with 0 restarts, the same second as the CM's last `kubectl-client-side-apply`. Bootstrap step 11 runs `rollout restart` right after applying the CM.

### The OTLP log copy, live
- Q on `/aws/modaas/gateway`:
  ```
  stats count(*) as total, sum(strcontains(@message, "modaas.run_id")) as has_run_id_key, sum(strcontains(@message, "action_id")) as has_action_id,
        sum(strcontains(@message, "fault-1791177342-d3f892")) as has_s2_cid, sum(strcontains(@message, "e120e4be08384784a2c6f766bc5fb265")) as has_s2_trace,
        sum(strcontains(@message, "input_tokens")) as has_tokens, min(@timestamp) as first, max(@timestamp) as last
  ```
  Result: total **1630**, has_run_id_key **0**, has_action_id **0**, has_s2_cid **0**, has_s2_trace 359, has_tokens 258, first 2026-10-04 10:57:20Z, last 2026-10-05 18:26:07Z.
- Q: `fields @message | filter strcontains(@message, "e120e4be08384784a2c6f766bc5fb265") | limit 2000`, parsed client-side:
  - **S2:** 359 records (353 + 6 GET 405s). 174 carry tokens: **1,992,059 + 6,942 = 1,999,001**.
  - **S1:** 30 records, 9 with tokens, **37,664**.
  - No key contains `run_id`, `action_id` or `correlation`.
  - Record keys are `attributes.{gen_ai.*, agw.ai.usage.cost.total, http.*, mcp.*, listener, route, trace.id, span.id, ...}`, `resource.*`, `trace_id` and `span_id`.

### Why the ids are missing at the source, not in the collector
- Spans pass through the **same** `attributes/scrub-payloads` processor and keep both ids, as C1 shows.
- `logs/gateway` adds only a whole-record filter.
- So the ids are absent from the gateway's OTLP access-log export itself.
- Source check: `workshop-static/scripts/bootstrap-platform.sh` lines 652–654: "Tracing: every call (randomSampling true), the correlation id and model as span attributes. **Access log: OTLP export of the same per-call line the shipped modaas-access-log policy shapes.**" The installer meant the OTLP copy to match the stdout line.

### Statement to use
- The live `modaas-telemetry-export` policy adds `modaas.run_id`/`modaas.action_id` (from `extauthz.correlationId`/`actionId`) **only to trace spans**. Its `accessLog.otlp` export declares no attributes.
- The stdout line gets the ids, plus `modaas.trace_id`, from the separate `modaas-access-log` policy, which sets `accessLog.attributes.add` on the same Gateway.
- The OTLP log copy in `/aws/modaas/gateway` (7 d) carries none of them: 0 of 1,630 records on 2026-10-05. It does carry per-call tokens, joinable to a run only through `trace_id`.
- The collector does not strip the ids. It deletes only 6 payload keys (prompt, completion, input/output messages, request/response body), and routes evidence and non-evidence records by filter.
- **This is not by design.** The installer comment says the OTLP export should be "the same per-call line the shipped modaas-access-log policy shapes". The cause (how agentgateway combines two policies' `frontend.accessLog` on one Gateway) can't be established read-only.
- Memory line 143, "dropped further down the pipeline", is wrong: they are never in the OTLP log export.

---

## C3. Gateway key is in the runtime env only, never in the AgentConfig spec

**Verdict: CONFIRMED.**

- **Spec env KEY NAMES.** Command: `kubectl get agentconfig -n components -o json | python3 -c 'import json,sys; [print(i["metadata"]["name"], sorted(i["spec"]["awsAgentCore"]["environmentVariables"])) for i in json.load(sys.stdin)["items"]]'`
  ```
  customer-experience-agent ['AGENT_NAME','AGENT_ROLE','AUDIT_URL','AUDIT_WRITE_TOKEN','STEP_BASE','TOOL_MCP_ALIAS']
  hackathon-helper          ['AGENT_NAME','AUDIT_URL','AUDIT_WRITE_TOKEN','STEP_BASE','TEAM']
  it-resolution-agent       ['AGENT_NAME','AGENT_ROLE','AUDIT_URL','AUDIT_WRITE_TOKEN','STEP_BASE','TOOL_MCP_ALIAS']
  my-agent                  ['AGENT_NAME','AGENT_ROLE','AUDIT_URL','AUDIT_WRITE_TOKEN','STEP_BASE','TOOL_MCP_ALIAS','TOOL_MCP_URL']
  network-resolution-agent  ['AGENT_NAME','AGENT_ROLE','AUDIT_URL','AUDIT_WRITE_TOKEN','IT_AGENT_RUNTIME_ARN','STEP_BASE','TOOL_MCP_ALIAS']
  ```
  - `environmentVariables` is a plain map in every spec: no `valueFrom`, no `secretKeyRef`, and no mention of `agw-apikeys`.
- **Runtime env KEY NAMES.** Command: `aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id it_resolution_agent-15k2B966z2 --query "keys(environmentVariables)" --output text`
  ```
  AGENTCORE_GATEWAY_MCP_TOKEN AGENTCORE_GATEWAY_MCP_URL AGENT_NAME AGENT_ROLE AUDIT_URL AUDIT_WRITE_TOKEN
  AWS_ENDPOINT_URL_BEDROCK_RUNTIME MODEL_ALIAS OPENAI_API_KEY OPENAI_BASE_URL REGION STEP_BASE TOOL_ALIAS TOOL_MCP_ALIAS
  ```
  - Every runtime is READY.
  - Runtime only (operator-injected) on 4 runtimes: `AGENTCORE_GATEWAY_MCP_TOKEN`, `AGENTCORE_GATEWAY_MCP_URL`, `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`, `MODEL_ALIAS`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `REGION`, `TOOL_ALIAS`.
  - `my_agent` lacks `AGENTCORE_GATEWAY_MCP_URL` and `TOOL_ALIAS`. Its spec carries `TOOL_MCP_URL` instead.
  - No spec key is missing from its runtime.
- **Value comparison.** Inline Python, in memory, printing booleans only:
  - It read `kubectl get secret agw-apikeys -n agentgateway-system -o json`: one data key, `eval-key`, 48 characters.
  - It compared that value with each runtime's env and with each whole AgentConfig CR (spec, annotations and status).
  - Results on **all 5** runtimes:
    - `OPENAI_API_KEY` (48) equals `agw-apikeys[eval-key]`: True;
    - `AGENTCORE_GATEWAY_MCP_TOKEN` (48) equals it: True;
    - the two are equal to each other: True.
  - The `agw-apikeys` value appears in **no** AgentConfig CR: False on all 5.
  - `AUDIT_WRITE_TOKEN` (32 characters) is in both the spec and the runtime, with identical values on all 5. It is not the gateway key.

### Statement to use
- AgentConfig specs never contain the gateway key, under any name. Their only credential is the literal 32-character `AUDIT_WRITE_TOKEN`.
- The operator injects the gateway key into each AgentCore runtime's env twice, as `OPENAI_API_KEY` (models, with `OPENAI_BASE_URL`) and `AGENTCORE_GATEWAY_MCP_TOKEN` (tools). Both equal Secret `agentgateway-system/agw-apikeys` key `eval-key` (48 characters), one shared key for every agent.
- The operator also injects `MODEL_ALIAS`, `REGION`, `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`, and on reference agents `AGENTCORE_GATEWAY_MCP_URL`/`TOOL_ALIAS`.
- The runtime env is readable in plain text by the participant role through `get-agent-runtime`.
- KB `resources/index.en.md#11` ("`GATEWAY_API_KEY` your AgentConfig already mounts from `agw-apikeys`") is wrong for this deployment.
- C8 consequence: `pull-evidence.sh`'s `cr-status.json` leaks the ledger token but not the gateway key.

---

## C7. Model selection: `dependsOn.models[0]`, the CEL rule on `modelRef`, "ignores modelRef"

**Verdict: PARTLY.** The CEL rule and the `dependsOn.models[0]` → `MODEL_ALIAS` mapping are confirmed live. "Operator ignores modelRef" is not testable without a write, and the CRD's own description contradicts it.

- **CRD.** `agentconfigs.oda.tmforum.org` has one version, v1beta1 (served and storage). It has 12 spec-level `x-kubernetes-validations`, and exactly 1 mentions `modelRef`:
  ```
  rule: (oldSelf.hasValue() && oldSelf.value() == self)
        || !has(self.modelRef)
        || (has(self.dependsOn) && has(self.dependsOn.models) && self.modelRef in self.dependsOn.models)
  optionalOldSelf: true
  message: spec.modelRef must appear in spec.dependsOn.models (declaring modelRef requires the dependsOn.models dependency edge)
  ```
  This is identical to the KB copy.
- **Field description.** Command: `kubectl get crd agentconfigs.oda.tmforum.org -o jsonpath='{.spec.versions[0].schema.openAPIV3Schema.properties.spec.properties.modelRef.description}'` → "Primary model alias. Lifted from dependsOn.models for MCP/Azure parity (Azure declarative: model.id; MCP: model ref). **Operator injects as MODEL_ALIAS env var.**"
  - Schema: string, max 63 characters, DNS-label pattern.
  - `dependsOn.models`: array, at most 50 items.
- **IT agent.** Command: `kubectl get agentconfig it-resolution-agent -n components -o jsonpath='modelRef={.spec.modelRef} dependsOn.models={.spec.dependsOn.models} gen={.metadata.generation} observed={.status.observedGeneration}'` → `modelRef=nemotron-nano-9b dependsOn.models=["nemotron-nano-9b"] gen=2 observed=2`.
  - From `--show-managed-fields`:
    - created by `kubectl-client-side-apply` at 2026-10-05T04:37:11Z, with last-applied `modelRef` null and `dependsOn.models` `["nemotron-super-120b"]`;
    - **one `kubectl-patch` at 05:47:37Z set both `modelRef` and `dependsOn.models`**;
    - `kubectl-annotate` ran at 05:48:52Z, then `kopf` at 05:48:53Z.
- **Runtime.** Command: `aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id it_resolution_agent-15k2B966z2 --query "{MODEL_ALIAS:environmentVariables.MODEL_ALIAS,version:agentRuntimeVersion,lastUpdatedAt:lastUpdatedAt}"` → `MODEL_ALIAS: "nemotron-nano-9b"`, version 2, lastUpdatedAt 05:47:50Z. That is 13 s after the patch.
- **All runtimes.** The env key that names the model is `MODEL_ALIAS`, and on 5 of 5 runtimes it equals `dependsOn.models[0]`:

  | runtime | MODEL_ALIAS | spec modelRef |
  |---|---|---|
  | customer_experience_agent | nemotron-super-120b | null |
  | hackathon_helper | nemotron-super-120b-helper | null |
  | it_resolution_agent | nemotron-nano-9b | nemotron-nano-9b |
  | my_agent | nemotron-super-120b | null |
  | network_resolution_agent | nemotron-super-120b | null |

### Statement to use
- The runtime's model is the env var `MODEL_ALIAS`, which the operator sets. Declaring it yourself is rejected (`DeclaredEnvInvalid`, generator comment).
- Live, `MODEL_ALIAS` = `spec.dependsOn.models[0]` on all 5 runtimes, and 4 of them have no `modelRef`.
- The IT agent's swap was a single `kubectl patch` (05:47:37Z) that set `modelRef: nemotron-nano-9b` and `dependsOn.models: [nemotron-nano-9b]`. The runtime was updated in place 13 s later (version 2), with `MODEL_ALIAS=nemotron-nano-9b`.
- The CRD's CEL rule requires that, on any create or changed spec, a present `modelRef` be **a member of** `dependsOn.models`, in any position. Unchanged specs are grandfathered.
- Which field wins when `modelRef` ≠ `models[0]` is **untested**. That case can only arise when `modelRef` names a later entry in the list. The KB says the operator reads `dependsOn.models[0]`, while the CRD field description says "Operator injects [modelRef] as MODEL_ALIAS env var".
- Do not write "the operator ignores modelRef". Write "the model follows `dependsOn.models[0]` whenever `modelRef` is absent or equals it, and precedence otherwise is unverified".

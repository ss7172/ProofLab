> Note: C1–C8 in this report are claim labels used during verification, not the challenge's controls (C7 event recording, C9 drift, C16 token cap). Here they appear only as C1–C3, in citations of verify-live.md; every C7, C9 and C16 in this report is a control.
>
> Correction (2026-10-05, after this report): the participant RBAC findings below (the EP 1 and EP 3 rows and "New findings") are RBAC only. The admission VAP `modaas-governance-guardrail` refuses those writes by its text (untested); see the addendum at the end.
# Verification of "What the platform gives you" (2026-10-05, read-only)

- **Page:** `notes/workshop-reference/platform-contract.md`, extracted verbatim from the workshop KB (`workshop-static/kb/index.json`, 11 chunks of `workshop/content/challenge-brief/platform-contract.en.md`). Live path `/challenge-brief/platform-contract`. The page's own captures are dated **2026-09-29**, an earlier build, so a count that differs may be build drift rather than a misreading.
- **Identity:** `arn:aws:sts::613052889143:assumed-role/WSParticipantRole/Participant`, us-east-1. **Cluster:** `a-01-eks-cluster-modaas`. **When:** 2026-10-05, 19:04–19:13 UTC.
- **How commands ran:** every command used `bash -c 'source /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; <cmd>'`.
- **Read verbs only:**
  - kubectl `get`, `logs`, `explain`, and `get --raw` (GET)
  - aws `sts get-caller-identity`, `logs get-log-events` / `filter-log-events` / `start-query` / `get-query-results` / `describe-log-streams`, `cloudformation describe-stacks` (OutputKey only), `bedrock list-guardrails`, `bedrock-agentcore-control list-agent-runtimes` / `list-gateways`, `cloudwatch list-metrics`
  - the kit's `show-run-spans.py` (read first: it only runs `kubectl get` and `logs get-log-events`)
- **Not used:** `kubectl auth can-i` (it POSTs a SelfSubjectAccessReview), so RBAC was read from the ClusterRoles and bindings instead. No write, no agent invocation, no cockpit, no `get-agent-runtime`.
- **No secret was printed:** AgentConfig, ToolConfig and ModelConfig were read through filters that print booleans and field names; env vars by name and `secretKeyRef` name only.
- **Verdicts:** CONFIRMED / CONTRADICTED / PARTLY / UNTESTED. "(write)" means testing it needs a write we did not do.
- **Run used for joins:** S1 after the IT swap, CID `fault-1791179282-8ef1a8`, trace `e13e7b734bb44249ad08b655a253306a` (2026-10-05 05:48Z).

## Summary

| Page claim | Verdict | One line |
|---|---|---|
| Three zones; one shared gateway carries every call | PARTLY | 3 reference agents + `hackathon-helper` + `my-agent`, all `awsAgentCore`. One Gateway (`modaas-agw`) carries the agents' calls, but side doors exist (#3, #59) and it is plain HTTP on a public LB (#2) |
| Cedar decides per caller, not per zone | CONTRADICTED (in effect) | One principal (`bootstrap-key`) on every authenticated call; each decision evaluates the called asset's policy. The page's own warning box says "per model or tool, not per agent" |
| EP 1: gateway + PDP (Cedar), Refuse, "No, Cedar policy via ConfigMap" | PARTLY | Refuses on missing credentials (23 `NoSigV4Credential`) and fail-closed (1 `PolicyEngineUnavailable`); **no Cedar policy DENY ever** (0 of 1,097). A team ConfigMap decides nothing (#33); the live lever is ToolConfig `access.cedarPolicy`. RBAC would let participants attach an `extAuth`/`extProc` hook (untested) |
| EP 2: Bedrock Guardrails, Refuse, "No, declared on ModelConfig" | CONFIRMED | 4 READY guardrails, one per ModelConfig; `safety.required: true`, enforcer `bedrockGuardrail`. Blocks are recorded as ALLOW (gap 4) |
| EP 3: Admission (CEL), Refuse, "No" | CONFIRMED, with a caveat | 94 served CEL rules + VAP `modaas-governance-guardrail`. Participants can't add webhooks or VAPs, **but can create/update/patch CRDs, where the CEL rules live** (RBAC read; not attempted) |
| EP 4: Evidence ledger, Refuse, "Yes, with token" | CONFIRMED, with a caveat | The server reads `AUDIT_WRITE_TOKEN` from a Secret; our agents write with it. The token is readable by every participant (#24), so the gate stops no participant |
| EP 5: AgentCore Runtime, Observe, "Yes" | PARTLY | Our code runs there (5 runtimes READY, incl. `my_agent`). It is more than "observe": agent code can stop its own calls, and the shared runtime role explicitly denies direct model and AgentCore-gateway access (#48) |
| EP 6: OTel collector / CloudWatch, Observe, "No" | CONFIRMED | Pipelines: traces → `awsxray` (→ `aws/spans`), `logs/audit` → `/modaas/evidence`, `logs/gateway` → `/aws/modaas/gateway`, metrics → `debug` |
| "All four gateway-level policies accepted" / checkpoint prints `4` | CONTRADICTED | Prints `6`; all six are Accepted=True and Attached=True (#5, #8) |
| Gateway read command (`grep "modaas.run_id=$CID"`) | CONTRADICTED (command broken) | The line writes `modaas.run_id="<CID>"` with quotes (1,092 of 1,092), so the page's grep matches 0 lines for every run; the quoted form finds S2's 353 |
| PDP read command (`--all-pods=true --prefix`) | CONFIRMED | Reads both replicas: 501 + 596 = 1,097 decisions (`deploy/` alone reads 501) |
| Ledger read command (`/timeline?cid=`) | CONFIRMED | S1: "AUDIT TRAIL -- 12 records"; `/records?cid=` gives the same 12 as JSONL |
| `/modaas/evidence` read command | CONFIRMED | 20 newest events (single stream `modaas-evidence`) |
| AgentCore spans command (`show-run-spans.py`) | PARTLY | Runs and finds the run's 48 agent spans, but totals 75,328 tokens = **2×** the gateway's 37,664 (#49) |
| PDP `trace_id`/`action_id` join to the gateway line | CONFIRMED | S1: 24 of 24 gateway action ids are in the PDP log; 24 PDP lines carry the run's trace |
| `traceparent` → `modaas.trace_id` / PDP `trace_id` / AgentCore span; ledger uses `correlation_id` | CONFIRMED | S1: trace equal on gateway (24/24), PDP (24) and agent spans (48). The ledger's own `trace_id`s differ (#21) |
| Ids, tokens and cost "on every call" | PARTLY | Every served call carries the ids (1,092/1,092) and every served model call carries tokens and cost (258/258); 573 refused or unrouted lines carry none (gap 7). `/aws/modaas/gateway` has no ids (#27) |
| Token fields; figure of record; cockpit cost view = CloudWatch cross-check | CONFIRMED | Fields on all 258 served model lines; cockpit attribution from the cockpit source and GETs on 2026-10-05 (not reopened) |
| AgentCore Latency/Errors per runtime are the drift signal; `score-run.py` grades one run | PARTLY | Metrics exist. Errors stayed 0 through the S2 runaway; our hourly averages (8.2–71.6 s) are far from the page's 1.3–4.9 s (correction row 8) |
| Ledger 1Gi gp3, token-gated; team S3 bucket; `submit.sh` uploads there | CONFIRMED | PVC 1Gi `gp3` (reclaim Delete); `TeamEvidenceBucketName` is an output of `a-02-code-editor`; `submit.sh` copies the zip there with `aws s3 cp` |
| Breach recipes (C16, C7, C9) | UNTESTED (write) | Each needs runs, a pause or a swap. Facts that bear on them below |
| Pause: refusal within 15 s | PARTLY | Tools ~1–7 s and super-120b ≤2 s, but nano-9b served for 33–41 s (#36) |
| Guardrail on tool output | UNTESTED | Untested by us too |
| Shared gateway identity; Cedar per model/tool, not per agent | CONFIRMED | 1,107 of 1,107 authenticated evidence records are `bootstrap-key` (#38) |
| Sandbox = Workshop Studio account; credentials = the IDE role | PARTLY | Same account; our shell runs as WSParticipantRole, not the IDE role, and the two roles differ |
| Per-account token and request ceiling, 429; Cedar doesn't meter tokens | PARTLY | Ceilings CONFIRMED (local, one replica); the 429 is UNTESTED (#41); "no token metering" CONFIRMED |
| Conditions settle within ~2 min | CONTRADICTED (pause conditions) | `ReconcilePaused=True` is still set 10–15 h after resume on nano-9b, super-120b and modaas-docs (#28) |

---

## 1. Environment architecture

**Page:** three zones; one shared gateway `modaas-agw` carries every call; Cedar decides per caller, not per zone.

Command as written:
```
$ kubectl get agentconfigs -n components -o custom-columns='NAME:.metadata.name,PROVIDER:.spec.provider'
customer-experience-agent   awsAgentCore
hackathon-helper            awsAgentCore
it-resolution-agent         awsAgentCore
my-agent                    awsAgentCore
network-resolution-agent    awsAgentCore
```

- **Zones: CONFIRMED.** The three zones are the three reference agents. The command also lists the platform's helper and our `my-agent`.
- **One gateway carries every call: PARTLY.**
  - **One Gateway:** `kubectl get gateways.gateway.networking.k8s.io -A` → one, `agentgateway-system/modaas-agw`, class `agentgateway`, listeners `http`/`llm`/`llm-tls` (HTTP/HTTP/HTTPS, 8080/8081/8443).
  - **The agents' path:** the shared runtime IAM role denies direct model calls and `InvokeGateway`, so agents must go through it (#48).
  - **Not every call:**
    - any pod can reach pod-hosted tool backends directly (#3)
    - participant credentials may invoke the `team-*` tool Lambdas (#59)
    - the AWS AgentCore Gateway (`list-gateways` → `modaas-agw  AWS_IAM  MCP  READY`) sits behind it for the Lambda tools
  - **Exposure:** Service `type=LoadBalancer`, ports 8080/8081/8443, a public ELB hostname (not `internal-…`), and the runtimes use plain HTTP (#2).
- **Cedar per caller: CONTRADICTED in effect.**
  - **The PDP log** (both replicas, whole life) names 12 policy ids, all `model-*` or `modaas-toolconfig-*`, i.e. the called asset's.
  - **`/modaas/evidence`** (1,130 records, 2026-10-04 18:07Z → 2026-10-05 19:07Z): principal `ServiceIdentity::"bootstrap-key"` on 1,107; `unknown` on 23 (the keyless DENYs below).
  - **All four ModelConfigs** have `access.allowedConsumers: ['bootstrap-key']`.
  - So there is one caller, and the policy is chosen per asset. The page's own "Limits of this build" box says so too. [#33, #38; mem: platform-verified-facts]

## 2. Enforcement points

| EP (page) | Page: refuse/observe · your code? | Verdict | Evidence (live 2026-10-05 unless noted) | Refs |
|---|---|---|---|---|
| `modaas-agw` + `modaas-pdp` (Cedar) | Refuse · No, Cedar via ConfigMap | **PARTLY** | **Refuse, CONFIRMED** at authentication: `/modaas/evidence` holds 24 DENY, 23 `reason=NoSigV4Credential` (principal `unknown`, asset `-unresolved-`) and 1 `PolicyEngineUnavailable` (fail-closed, `runbook-lookup`), 2026-10-05 00:32–04:47Z. **The PDP itself: 0 DENY in 1,097 decisions** (both replicas, 2026-10-04 18:07Z → 2026-10-05 18:58Z), so no Cedar policy has ever refused here. **"Via ConfigMap"**: the 15 labelled ConfigMaps are 10 `modaas-toolconfig-*` (all 10 ToolConfigs set `access.cedarPolicy`), 4 `model-*` and `my-team-policy`, which was named in **0 of 1,097** decisions. A team rule enforces only when attached to an asset. **"Your code: No"** for the PDP and authz. But participant RBAC (`admin`, cluster-wide) allows create/update/patch/delete on `agentgateway.dev/*`, and `AgentgatewayPolicy.spec.traffic` has `extAuth` and `extProc`, so a team service could be put in the request path: a write in a protected namespace, untested | #33, #39, #43, #26; gap 3 |
| Amazon Bedrock Guardrails | Refuse · No, declared on ModelConfig | **CONFIRMED** | `list-guardrails`: 4 READY (`canvas-nemotron-nano-3-30b`, `-nano-9b`, `-super-120b`, `-super-120b-helper`). All 4 ModelConfigs: `safety.required: true`, `enforcer: {kind: bedrockGuardrail, enforcedAt: self}`. A block was verified on 2026-10-05 (HTTP 200, `content_filter`, 0 tokens) and is recorded as ALLOW in the PDP and `/modaas/evidence`. Tool-output screening is UNTESTED | gap 4; #35, #7 |
| Admission (CEL) | Refuse · No | **CONFIRMED, with a caveat** | 94 served CEL rules (AgentConfig 36, ModelConfig 33, ToolConfig 20, Registry 5; v1beta1) plus VAP and binding `modaas-governance-guardrail`. **Participants can't add admission code:** `modaas-participant-builder` grants only get/list/watch on VAPs, bindings and webhook configurations, and `admin` has no `admissionregistration` rule. **But the same role grants create/update/patch on `customresourcedefinitions`**, which is where the CEL rules live (read from RBAC; not attempted; new) | #26, #31, #54 |
| Evidence ledger (token-gated writes) | Refuse · Yes, with token | **CONFIRMED, with a caveat** | `audit-store` reads `AUDIT_WRITE_TOKEN` from `secretKeyRef: audit-write-token`. A tokenless write got 401 (Module 7, mem; not re-tested: write). Our agents write with the token (`my-agent`: 3 records per run). The token is a literal in all 5 AgentConfig specs and is readable by participants, so the gate refuses only a writer without it. It refuses writes, not agent actions. No verify route | #24, #13; gap 6 |
| AgentCore Runtime | Observe · Yes | **PARTLY** | **"Yes", CONFIRMED:** `list-agent-runtimes` shows 5 READY, incl. our `my_agent`. **"Observe" understates it:** our agent code there can refuse its own next model or tool call (the only place the page allows team code in the path). The shared runtime role explicitly denies `bedrock:InvokeModel*` and `bedrock-agentcore:InvokeGateway` (IAM refusal). Metrics in `AWS/Bedrock-AgentCore`: Latency, Errors, Invocations, Duration, SystemErrors, UserErrors, Throttles, Sessions and others | #48; mem: platform-verified-facts |
| OTel collector / CloudWatch | Observe · No | **CONFIRMED** | ConfigMap `otel-collector-config`: `traces` otlp→`awsxray`; `metrics` otlp→`debug` (not kept); `logs/audit` otlp→`/modaas/evidence` (stream `modaas-evidence`); `logs/gateway` otlp→`/aws/modaas/gateway` (stream `modaas-agw`). Protected namespace; we only read (filter-log-events and Insights work for our role) | #32, #27; verify-live C2 |

**"All four gateway-level policies accepted": CONTRADICTED.** There are six:

| Policy | Created (UTC) | Sections |
|---|---|---|
| `modaas-access-log` | 10-04 10:33:53 | frontend.accessLog |
| `modaas-authz` | 10:33:54 | traffic.extAuth, transformation |
| `modaas-llm-auth` | 10:33:54 | traffic.rateLimit |
| `modaas-mcp-ratelimit` | 10:33:54 | traffic.rateLimit |
| `modaas-telemetry-export` | 10:36:58 | frontend.accessLog, tracing |
| `modaas-ceiling` | 10:37:03 | traffic.rateLimit |

All six are `Accepted=True`, `Attached=True`. The two later ones (ceiling, telemetry-export) are the extras noted in #5 and #8.

**Enforcement points the page does not list** (all live or already verified):
- **`modaas-authz` extAuth:** the API-key check, `FailClosed`, inside EP 1. It produced all 24 DENYs.
- **Ceilings:** `modaas-ceiling` and `modaas-llm-auth` set `local` limits of 100 req/min and 2,500,000 tokens/h (ceiling on `llm`; llm-auth on `llm` and `llm-tls`). `modaas-mcp-ratelimit` sets 100 req/min on `http`. They are per replica, and there is one replica.
- **The kill switch:** a pause withdraws the route, and calls get 404 (#36).
- **The runtime IAM deny** (#48).
- **The AWS AgentCore Gateway:** `AWS_IAM`, in front of the Lambda tools.
- **NetworkPolicies:** egress-only (#3).

## 3. Logging APIs per enforcement point (each command run as written)

**Gateway: CONTRADICTED. The command can't match.**
```
$ CID=fault-1791179282-8ef1a8; kubectl logs -n agentgateway-system deploy/modaas-agw --since=1h | grep -c "modaas.run_id=$CID"
0
```
- **The same unquoted grep over the whole pod log** (2,033 lines, 2026-10-04 10:35:13Z → 2026-10-05 18:58:11Z; pod `modaas-agw-88dc46ff4-jfcdx`, 0 restarts) finds 0 lines for S1 and 0 for S2.
- **Why:** the line is logfmt with quoted values. Of 1,092 occurrences of `modaas.run_id=`, all 1,092 are `modaas.run_id="…"`, and `modaas.trace_id` and `modaas.action_id` are quoted the same way.
- **Fix:** `grep -F "modaas.run_id=\"$CID\""` finds S2's 353 lines (S1: 24). `grep -F "$CID"` (as `pull-evidence.sh` does) finds the same. The kit's own `show-run-spans.py` prints the quoted form (`grep 'modaas.trace_id="<trace>"'`).
- **Other limits of the command:** `--since=1h` only reaches runs from the last hour. Stdout lives only as long as the pod; the durable copy with run ids is `aws/spans` (30 d; verify-live C1).
- **In the last hour,** the only run-id lines were 51 `modaas-docs-mcp-route` handshakes whose run id equals the trace id (handoff §3b Q16).

**PDP: CONFIRMED.**
```
$ kubectl logs -n modaas-system deploy/modaas-pdp --all-pods=true --tail=-1 --prefix | grep trace_id   (counted)
lines with trace_id: 1097   ([pod/modaas-pdp-…-2kcjn/pdp] 501, [pod/modaas-pdp-…-zqzw6/pdp] 596)
decision=ALLOW 1097, decision=DENY 0, policy_id=my-team-policy 0
```
- **`--all-pods=true` works** with kubectl 1.36.5 and fixes the one-replica trap: without it, `deploy/` read only the `2kcjn` replica's 501 lines.
- **Every `trace_id` line is a `decide` line.**
- **The PDP log is pod-only:** there is no CloudWatch group for it (mem).

**Ledger: CONFIRMED.**
```
$ kubectl get --raw "/api/v1/namespaces/components/services/audit-store:8080/proxy/timeline?cid=fault-1791179282-8ef1a8"
38 lines; header "AUDIT TRAIL -- 12 records"      (/records?cid= → 12 JSONL records)
```
`/timeline` is text; `/records?cid=` is the machine read (mem).

**`/modaas/evidence`: CONFIRMED.**
```
$ aws logs get-log-events --log-group-name /modaas/evidence --log-stream-name modaas-evidence --limit 20
20 events, 2026-10-05T18:52:43Z → 18:58:10Z
```
- **Which events:** without `--start-from-head` it returns the newest. `modaas-evidence` is the only stream.
- **Record keys:** `attributes.modaas.evidence.{action_id, actor, asset.alias, asset.kind, attested_by, correlation_id, decision, matched_policy, phase, policy_id, policy_version, principal, registry_record_id, schema_version, trace_id, ts}`, plus `reason` on DENYs.

**AgentCore spans: PARTLY.**
- **The script:** `/tmp/show-run-spans.py` exists locally and is identical to the kit copies (`workshop-static/` and `workshop-assets/reference-impl/`).
```
$ python3 /tmp/show-run-spans.py e13e7b734bb44249ad08b655a253306a
trace e13e7b73…: 48 spans from 3 AgentCore agent(s)
model calls: 12   input tokens: 73724   output tokens: 1604   total: 75328
```
- **The gateway's figure for the same run:** 9 model calls, 36,862 in + 802 out = 37,664.
- **The script doubles it:** its 12 "model calls" are 9 `chat` spans plus 3 `invoke_agent` parents that repeat their sums, so the total is exactly 2× (#49).
- **No action ids:** none of the 48 agent spans carries one.
- **It looks back only 24 h.**
- **The IDE role may differ:** its docstring says the IDE role can't `FilterLogEvents`. Our participant role can (mem); the IDE role's rights were not tested.

**"PDP decision log; `trace_id` and `action_id` join to the gateway line": CONFIRMED.** S1 has 24 gateway lines with 24 distinct action ids, and all 24 are in the PDP log. 24 PDP decision lines carry the run's trace id.

## 4. Run identity

- **`traceparent` → `modaas.trace_id` / PDP `trace_id` / AgentCore span: CONFIRMED** (S1).
  - Gateway `modaas.trace_id` = `trace.id` on 24 of 24 lines.
  - 24 PDP lines carry the same trace.
  - The spans helper found 48 agent spans on it.
- **The run id is not the traceparent:** `modaas.run_id` is the baggage CID, or the trace id when no CID is sent (mem; the 51 handshake lines above).
- **"The ledger uses `correlation_id`, minted per scenario run": CONFIRMED.** S1 has 12 records under its CID. The ledger's own `trace_id` fields hold 3 distinct values, and none equals the run's trace (agent-minted, #21).
- **"`modaas.run_id`, `modaas.trace_id`, `modaas.action_id`, tokens and cost on every call": PARTLY.** Counted over the whole pod log (1,665 access-log lines):

| Lines | Count | Ids / tokens |
|---|---|---|
| Served (2xx) | 1,092 | all 1,092 carry the three ids |
| Served model calls (`listener=llm`, 200) | 258 | all 258 carry tokens, cost and action id |
| Refused or unrouted | 573 | no ids: 24× 403, 127× 404, 422× 405 |

  - The 573 include the kill-switch 404, keyless 403s and MCP `GET` 405s (gap 7; handoff §5.2).
  - The durable `/aws/modaas/gateway` copy carries no ids at all (#27; verify-live C2).

## 5. Token usage per call
**CONFIRMED.**
- **The fields:** `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` and `agw.ai.usage.cost.total` are on all 258 served model lines.
- **The rest of the line:** `gateway`, `listener`, `route`, `endpoint`, `src.addr`, `http.*`, `trace.id`, `span.id`, `protocol`, `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.request.temperature`, `gen_ai.request.max_tokens`, `duration` and the three `modaas.*` ids.
- **The cockpit cost view is the CloudWatch cross-check** (`AWS/Bedrock`, account-wide, "joinable_to_run_id: false"), and the figure of record is the gateway line. Verified from the cockpit source and GETs on 2026-10-05; not reopened (mem: platform-verified-facts).

## 6. Drift metric availability
**PARTLY.**
- **`score-run.py` grades one run** (one CID, scenario and timeline): CONFIRMED.
- **The metrics exist** per runtime in `AWS/Bedrock-AgentCore`: Latency, Errors, Invocations and others (`list-metrics`).
- **But Errors missed the S2 runaway** (0), and latency moves with call count.
- **Our hourly values are far from the page's capture.** The page: 1.3–4.9 s average, zero errors (2026-09-29). Ours, in the S2 hour: IT averaged 71.6 s (maximum 278.4 s); customer and network 8.2–8.5 s [correction row 8; mem: workshop-progress].

## 7. Writable evidence store per team
**CONFIRMED.**
- **The ledger volume:** PVC `audit-store-data` is 1Gi, StorageClass `gp3` (`ebs.csi.aws.com`, `type=gp3`), Bound. Reclaim policy is **Delete** on both the StorageClass and the PV, so the ledger dies with the stack.
- **The token:** the server takes `AUDIT_WRITE_TOKEN` from Secret `audit-write-token`.
- **The bucket:** `TeamEvidenceBucketName` is an output of stack `a-02-code-editor`, and `TEAM_EVIDENCE_BUCKET` is set in our shell (`team-evidence-…`).
- **`submit.sh`** takes `TEAM_EVIDENCE_BUCKET`, else the stack output (`:94`, `:98`), then runs `aws s3 cp` (`:114`).
- **Caveats** (mem):
  - the fallback lookup returns empty in this account
  - the bucket's versioning is unreadable to us
  - `cr-status.json` carries the ledger token into the hand-in (gap 6, MUST-FIX)

## 8. Breach recipes and the limits box

**All three recipes are UNTESTED (write):** each needs runs, a pause or a model swap. Facts that bear on them:
- **C16, "set cap below a normal run":** any cap under 24.8K breaches every measured S1/S3 run (handoff §5.6).
- **C7, "pause a ToolConfig mid-run; the record never lands":**
  - a refused reference run writes 3 ledger records per agent instead of 4 (mem: reference-agents-facts)
  - the platform records the refused call as **ALLOW** (PDP and `/modaas/evidence`), and its gateway 404 line carries no run or action id (gap 4; handoff §5.2)
  - a tool pause took ~1–7 s (#36)
- **C9, "swap the model":**
  - swap mechanics are verified: no re-review (gap 5); the runtime updates in ~13–24 s
  - "drift" from a swap is unverified: tokens per call are the same on both models, and latency moves with call count (mem: challenge-requirements)
- **"Refusal within 15 seconds": PARTLY.** Tools took ~1–7 s and super-120b ≤2 s, but nano-9b served for 33–41 s after its pause (#36).

**The limits box:**
- **"Whether the guardrail checks tool output … not tested":** UNTESTED by us too.
- **"Agents … share the gateway identity; Cedar per model or tool, not per agent":** CONFIRMED. All authenticated evidence records are `bootstrap-key` (1,107/1,107). One shared gateway key sits in every runtime (verify-live C3; #38).

## 9. Sandbox, credentials, quotas
- **Sandbox = the Workshop Studio account: CONFIRMED** (account `613052889143`).
- **"Credentials are the IDE role": PARTLY.**
  - The page's command, run in our shell, prints `arn:aws:sts::613052889143:assumed-role/WSParticipantRole/Participant`, not the IDE role.
  - The roles differ. The IDE role's `ide-workshop` policy allows AgentCore gateway Create/Update/Delete, which WSParticipantRole denies (mem). Per the spans helper, the IDE role can't `FilterLogEvents`.
  - So commands we verified may behave differently in the IDE.
- **Ceilings: CONFIRMED** (§2). The 429 itself is UNTESTED (#41). The S2 loop peaked at 49 model calls a minute and never neared the request limit.
- **"Cedar does not meter tokens": CONFIRMED.** Cedar's context has no token attributes (mem).
- **"Conditions settle within about 2 minutes": CONTRADICTED for pause conditions.** `ReconcilePaused=True` is still set with `spec.paused=false` at 19:12Z:
  - nano-9b, since 04:05:53Z
  - super-120b, since 09:13:05Z
  - modaas-docs, since 05:56:44Z

  The runtime re-program after a swap (13–24 s) does settle within 2 minutes (#28).

## 10. Checkpoint
```
$ kubectl get agentgatewaypolicy -n agentgateway-system --no-headers | wc -l
       6
```
**CONTRADICTED:** the page says `4`. All 6 are Accepted (§2; #5, #8).

---

## Contradictions with our verified facts
1. **"Cedar decides per caller"** vs one shared principal (#38). The page's own limits box agrees with us.
2. **"Cedar policy via ConfigMap"** vs the inert team ConfigMap: 0 of 1,097 decisions on both replicas (was 0 of 1,037 at 17:33Z) (#33). The live lever is ToolConfig `access.cedarPolicy` (correction row 1). The AgentConfig overlay is unset on all 5 agents and not wired (#39).
3. **The page's EP table omits that refusals are recorded ALLOW** (guardrail blocks and pauses; gap 4). The only DENYs on record are authentication and fail-closed ones; no Cedar policy has ever refused.
4. **The gateway read command can't match** (quoted values). New: the notes and memory don't record it.
5. **"Four gateway-level policies"** vs six (#5, #8).
6. **"Ids, tokens and cost on every call"** vs the 573 refused or unrouted lines without ids, and no ids in `/aws/modaas/gateway` (#27, gap 7).
7. **"Refusal within 15 s"** vs nano-9b 33–41 s (#36). **"Conditions settle in ~2 min"** vs stale pause conditions (#28).
8. **The spans helper doubles the tokens** (#49), so the page's AgentCore-spans command isn't a token source.
9. **"Credentials are the IDE role"** vs our WSParticipantRole (different rights).

## New findings (RBAC read only; nothing attempted; candidates for the notes only on the user's "add")
- **Participants can edit the admission rules.**
  - ClusterRole `modaas-participant-builder` (bound to group `modaas:participants` by the ClusterRoleBinding of the same name) grants `apiextensions.k8s.io/customresourcedefinitions` get, list, watch, create, update and patch.
  - The 94 CEL rules of EP 3 live in those CRDs.
  - Closest: #26.
- **Participants can edit the gateway's policies.**
  - ClusterRoleBinding `modaas-participant-admin` binds `admin` cluster-wide, and `admin` (aggregated from `edit` and `modaas-crs-edit`) includes `oda.tmforum.org`, `agentgateway.dev` and `gateway.networking.k8s.io` `*` with create, update, patch and delete.
  - That covers `modaas-authz` and the ceilings in `agentgateway-system`, and `AgentgatewayPolicy` supports `extAuth`/`extProc` hooks.
  - Closest: #26, #59.

## Corrected commands for the planning session
- **Gateway lines for a run (pod stdout):** `kubectl logs -n agentgateway-system deploy/modaas-agw --tail=-1 | grep -F "modaas.run_id=\"$CID\""`. For the durable copy, use `aws/spans` (handoff §10).
- **PDP decisions, both replicas:** the page's command as written (`--all-pods=true --tail=-1 --prefix`).
- **Agent-span tokens:** sum `chat` spans only, or use the gateway figure. Don't use `show-run-spans.py`'s total.
- **Checkpoint:** expect `6`.

## Cross-references
- Memory: `platform-verified-facts` (evidence surfaces, Cedar levers, refusals as ALLOW, kill-switch timing, cockpit), `challenge-requirements`, `reference-agents-facts`, `workshop-progress`.
- Repo:
  - `notes/platform-observations.md`: #2, #3, #5, #8, #13, #21, #24, #26, #27, #28, #31–#33, #35, #36, #38, #39, #41, #43, #48, #49, #54, #59
  - `gap-list.md`: gaps 3–8
  - `notes/playbook/playbook-verification.md`: correction rows 1, 8, 10, 12
  - `notes/verification/2026-10-05/verify-live.md`: C1–C3

---

## Addendum (2026-10-05, 19:15–19:50 UTC): the admission policy limits the RBAC findings
Added after this report. Sources: a `kubectl auth can-i` pass at about 19:15–19:25 UTC (memory `platform-verified-facts`), and the independent review's live re-read of the VAP, its binding, the roles and the Gateway at about 19:31–19:50 UTC (`review-third-commit.md`, which lists the commands; read verbs only).

- **RBAC is as stated above** (re-read from the ClusterRoles and bindings): `modaas-participant-builder` grants create/update/patch on CRDs (no delete) and only get/list/watch on VAPs, bindings and webhooks; `admin`, bound cluster-wide to `modaas:participants`, grants all write verbs on `oda.tmforum.org`, `agentgateway.dev` and `gateway.networking.k8s.io`, and create on `pods/exec`, `pods/portforward` and `pods/proxy`.
- **But the VAP `modaas-governance-guardrail` refuses those writes by its text** (untested; no write attempted):
  - failurePolicy `Fail`; binding `validationActions: [Deny]`; it matches group `modaas:participants` or a username containing `:assumed-role/WSParticipantRole/`, for CREATE, UPDATE and DELETE on `*/*`.
  - Rule 1 refuses any write in `modaas-system`, `agentgateway-system`, `canvas`, `canvas-system`, `canvas-vault`, `istio-system`, `istio-ingress`, `cert-manager` and `kube-system`, except team Cedar ConfigMaps in `modaas-system` (label `app.kubernetes.io/part-of: modaas-pdp`, no `managed-by` label, annotation `modaas.tmforum.org/policy-id`).
  - Rule 2 refuses cluster-scoped writes to RBAC, `admissionregistration`, nodes, the protected namespaces (update/delete), and CRDs named `*.oda.tmforum.org`, `*.agentgateway.dev`, `*.gateway.networking.k8s.io`, `*.istio.io` or `*.cert-manager.io`.
- **So both "New findings" above are refused by the VAP's text.** The four CRDs that hold the 94 CEL rules are all `*.oda.tmforum.org`, and every write in `agentgateway-system`, including the six gateway policies, falls under rule 1. The EP 1 and EP 3 rows' RBAC caveats stand as RBAC facts only.
- **What it leaves open:**
  - reads (e.g. secrets) and CONNECT (`exec`, `port-forward`, `proxy`), which it doesn't list (#26)
  - `components` and team namespaces: AgentConfigs and ToolConfigs there pass it (Claude created `my-agent` and paused the `modaas-docs` ToolConfig there through our shell, after the VAP existed)
  - by text, a route plus a policy in a team namespace: the Gateway's three listeners admit routes from all namespaces (`allowedRoutes: All`), and route `parentRefs` carry a namespace, though policy `targetRefs` don't (untested)

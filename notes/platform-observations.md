# Platform observations — MoDaaS workshop

Working notes for a review with the platform team. Not part of the hackathon submission.

- **Event:** Trustworthy AI & Data Hackathon: Agentic Assurance, 2026-10-04
- **How we checked:** every command was run as written in the guide, from a laptop using the Workshop Studio participant credentials (`WSParticipantRole`, which kubectl maps to the `modaas:participants` group). Tools: kubectl 1.36.5, Helm 3.22.0, AWS CLI 2.37.9. Where our output differed from the guide, we confirmed it with a second, independent query.
- **Coverage so far:** Module 2 (all steps except Step 6, Amazon Q, which is console-only), Module 3 (all pages; platform checkpoint `validate-canvas.sh`: 6 passed, 0 failed), Module 4 (both architecture diagrams compared with live state), Modules 5–7 (the reference agents were deployed and run in Module 7), Module 8 "Trace a run through its spans" (checked on an existing run), the cockpit (read-only GETs with the CockpitUrl token, never printed), and source reviews of the three reference agents and of the authorization path (auth gateway, PDP, operators).

## Summary

| # | Where | Type | One line |
|---|---|---|---|
| 1 | M3 · Control plane checkpoint | **Bug** | The checkpoint prints `6` on a healthy cluster, so it can never pass |
| 2 | M2 · Step 5 / M2 · Step 7 | **Security** (noted in the guide) | The gateway listens on an internet-facing load balancer over plain HTTP, and the team API key works there. Internet scanners already reach it (54 requests in X-Ray on 2026-10-04). The platform's own agents use it too |
| 3 | M2 · Step 7, M3 · Isolation, M4 diagrams | **Security — verified** | Any pod in the cluster can call a tool's backend directly without a credential and skip the gateway, not only via port-forward. This contradicts the Module 4 diagram's "no side doors — by design" |
| 4 | M3 · Resource types | Doc accuracy | The guide says ModelConfig still serves v1alpha1/v1alpha2; the CRD has `served=false` |
| 5 | M2 · Step 5, M3 overview | Doc drift | Bootstrap now pre-creates 4 ModelConfigs, 8 ToolConfigs and 6 gateway policies; the guide shows 0, 0 and 4 |
| 6 | M2 · Step 2 | Doc drift | The guide says the installer has 8 steps; `bootstrap-platform.sh` has 18 |
| 7 | M2 · Step 5 | Design note | A blocked prompt returns HTTP 200; callers have to check `finish_reason` and token counts |
| 8 | M3 · Gateway | Doc accuracy | The guide says `modaas-llm-auth` "adds the API-key check"; its spec is a rate limit only. The key is checked by `modaas-authz` (extAuth, FailClosed) |
| 9 | M3 · Gateway | **To verify (M5)** | Gateway model routes exist for the 2 ModelConfigs still in `Reviewing` |
| 10 | M3 · Isolation (audit store) | Checked — OK, with notes | Writes to the evidence store need a token (verified live). Reads are open by design. Participants can read the write token |
| 11 | M2 · Step 4 | Robustness | The egress probe doesn't delete an earlier `egress-probe` pod, so a re-run can print the old pod's logs as a pass |
| 12 | Approvals (all assets) | Documented limitation | Approver identity is self-asserted: `subject` is the annotation text, `signature` is empty on all 14 records. The source calls this "v0" |
| 13 | Evidence ledger | Documented limitation — **not a build target** | No tamper evidence (hash chaining, signatures, write-once storage). A source comment calls it "participant-challenge scope", but the masterclass rubric says out of scope and not scored |
| 14 | Operators | Minor / noise | Recurring operator error events: first-attempt PATCH `ConnectionResetError` (retries succeed); the Canvas `api-operator-istio` crashes on an EndpointSlice with no `componentName` label |
| 15 | All governed assets | **Misleading status** | All 15 assets report `IstioPerAssetProvisioned=True — "VirtualService + AuthorizationPolicy emitted"`; the cluster has **0** AuthorizationPolicies |
| 16 | M4 · hero diagram | Doc accuracy | The diagram calls the audit store a "tamper-resistant ledger"; it has a write token and nothing more (#10, #13) |
| 17 | M4 · TMF639 | **Misleading status** | Every CR says `TMF639Projected=False` ("timed out"), yet all 15 assets are in the TMF639 inventory, and their records ignore approval state |
| 18 | M4 · diagram "1 · Identity" | Doc accuracy — to verify | "API key / OAuth": the API key is verified; no OAuth/JWT validation is configured anywhere we can see (0 RequestAuthentications) |
| 19 | Reference agents · self-check | **Bug** (kit) — confirmed live | `score-run.py`'s guardrail and negotiation checks cannot pass with the shipped `agent.py`, so the guide's sample grades (S1 8/8, S3 10/10) can't come from this code. All six live runs failed both checks |
| 20 | Reference agents · ledger | Doc accuracy | The guide says 10 records whose invocations carry action_id, model, guardrail verdict and tokens; the code writes 12 records with none of those |
| 21 | Reference agents · correlation | **Bug** (kit) | The run's traceparent never reaches the agent code, so each agent's ledger `trace_id` differs from the run's trace id |
| 22 | Reference agents · spans | **Doc accuracy / data handling — verified** | The guide says spans carry no prompt or completion text. The deployed agents' `chat` spans hold the system prompt and the full context, including customer records |
| 23 | Reference agents · misc | Doc drift / minor | Stale comments, stale `agents.yaml`, an inconsistent default model, call/token counting caveats, and the audit token written to a `/tmp` file |
| 24 | AgentConfig spec · cockpit | **Security — verified** | The ledger write token is stored as a literal env value in the AgentConfig spec, and the cockpit's CR view returns it to anyone holding the cockpit link |
| 25 | Cockpit | **Security** / doc accuracy | The cockpit has no login of its own and is not read-only: `POST /api/agents/{name}/ask` invokes approved agents. The guide calls it "read-only" three times |
| 26 | Participant RBAC | **Security** | Participants can read secrets, create pods and port-forward in kube-system, agentgateway-system, modaas-system and canvas-vault |
| 27 | Gateway evidence | Evidence gap | Run ids are missing from the durable gateway log in CloudWatch; they exist only on the gateway pod's ephemeral stdout |
| 28 | nemotron-nano-9b · nemotron-super-120b · modaas-docs | **Misleading status — reproduced** | After a pause and resume, the status still says paused (`ReconcilePaused`, registry "servingState=PAUSED") while the model serves. Resume never clears them. Tools are affected too |
| 29 | Cockpit / bootstrap | Build gap | The telemetry tap was not shipped, so the cockpit's per-run usage, drift, ceilings and telemetry panels are empty |
| 30 | AICT stacks | Doc accuracy | a-03-servicenow-aict says no IAM user or access key is created anywhere, yet one of each was created |
| 31 | M4 Step 1 · capability 1 | Doc accuracy (minor) | The guide's unsafe-model example is rejected by two admission rules, not the one it illustrates |
| 32 | M6 overview · collector | Doc accuracy | The guide says the trace pipeline "has no durable exporter (spans are discarded)"; it exports to X-Ray, and X-Ray holds the gateway's traces |
| 33 | M6 · Cedar | Doc accuracy | A team policy ConfigMap loads but never decides any call: each decision names one asset's policy. The guide implies "write your own rule and have the platform enforce it" |
| 34 | M6 · Cedar step 2 | Doc drift | The page expects a DENY from an "undeclared model" probe that the current Module 5 page doesn't contain |
| 35 | M6 · Cedar / evidence | Evidence nuance | A guardrail-blocked call and a kill-switch refusal (HTTP 404) are both recorded as `decision=ALLOW`, in the PDP log and in `/modaas/evidence`, with no guardrail outcome or refusal |
| 36 | M6 · Pause · M7 kill switch | **Enforcement latency** | On nano-9b the kill switch took 33–41 s to withdraw a model's route, and calls were served meanwhile. On super-120b, a call 2 s after the pause was already refused. The guide says "instantly" (~15 s). A tool's route went in ~1 s |
| 37 | M7 run · M8 spans | **Authorization gap — verified** | Agents call approved tools they don't declare (the network agent read customer records), and every call is allowed. The policy checked is the called tool's, and all agents share one identity |
| 38 | M6 · Cedar · Keycloak | **Identity gap** | Keycloak and one IdentityConfig per agent exist, but none is provisioned. Every call is `bootstrap-key`, so no policy can tell agents apart |
| 39 | AgentConfig CRD (source) | Doc accuracy (source-based) | AgentConfig `spec.access.cedarPolicy` is documented as a per-agent "restrict-only overlay", but nothing projects or evaluates it in this build |
| 40 | M6 · Governed tools (kit) | Configuration gap (kit) | `customer-records` and `network-twin` ship with no data classification, so their own "restricted" rule can never fire |
| 41 | M6 · The ceiling | Doc accuracy / control gap | "One request per second per agent keeps a team well under the line" is wrong for three agents (180/min > 100). The request limit never stopped the S2 loop, which used 2.0M tokens (80% of the hourly budget) in 5 minutes |
| 42 | M4 cap. 8 · M6 ceiling · cockpit | Doc accuracy | The guide gives two different sources for the cockpit's cost figures. The code reads AWS/Bedrock metrics, which are per model id, so two aliases on one model can't be split |
| 43 | M7 · Run and read | **Evidence accuracy** | A policy-engine outage refused an IT tool call (fail-closed, DENY in `/modaas/evidence`). The gateway line has no run id or action id, and the agent's ledger reports a 500 on the model |
| 44 | M7 · Self-check (S2) | **Evidence gap** | The S2 IT agent made 174 model calls and 170 tool calls (2.0M tokens, $0.30), but its ledger records look like two ordinary invocations |
| 45 | M7 · Self-check checkpoint | Bug (guide) | The checkpoint hardcodes S1, so an S3 chain is graded as S1 and can never print the promised `exit=0` |
| 46 | M7 · Swap the model | **Governance gap** | An approved agent's model dependency changed with no re-review, and "re-attest" adds no approval record. The only attestation on file predates the change |
| 47 | M7 · Swap the model | Doc accuracy (minor) | The page's compare grep (`it.resolution`) matches nothing, because gateway lines carry no agent name |
| 48 | M8 · Trust hierarchy · deck p13 | **Identity gap** | All four AgentCore runtimes share one IAM role, while the deck says each has its own. The role does deny direct model calls, so the gateway really is the only path to a model |
| 49 | M8 · Spans · both checkpoints | Doc drift / Bug (kit) | The deployed agents emit 48 Strands-native spans per run, not the guide's 8. `show-run-spans.py` adds parent and child spans, so its totals are 2× the gateway's and the Module 8 checkpoints can't pass |
| 50 | M9 overview · Step 1 | Doc drift | Module 9 describes the helper and modaas-docs as in a different build. The helper runs on `nemotron-super-120b-helper` with five tools; the Lambda docs tool is `helper-docs`; `modaas-docs` is the in-cluster `custom` server |
| 51 | M9 Step 1 · helper evidence | **Evidence gap** | The helper's own records are thin: 2 ledger records instead of 3 (no result-inspection, so disposition "unknown"). Answers cite a docs source with no tool call in the run, and every run logs 15 tool decisions just from session setup |
| 52 | M9 Step 1 · section 5 | Doc accuracy / kit | The helper's drafts don't apply: its ToolConfig has an unknown field (`spec.alias`), and its patch for it-resolution-agent fails on the live agent. Yet it says the change was made |
| 53 | M9 Step 1 · helper-docs policy | To verify | The helper-docs Cedar allow-list has an unprefixed `"get_doc"`, so a helper `get_doc` call (wire name `helper-docs___get_doc`) would be denied. No such call seen yet |
| 54 | M9 Step 2 | Doc accuracy | Deleting the safety block isn't refused at admission (a server dry run accepts it); the `EnforcementNotDeclared` check runs in the operator, after storage (per source; not applied live). `new-agent.sh` also passes the SDK pins as `EXTRA_PIP`, which the page says never to do |
| 55 | M9 Step 1b · new-agent.sh --tool | **Governance gap** | `--tool` only adds environment variables, so `my-agent` declares no tool in `dependsOn` yet calls `modaas-docs`. Neither its contract nor its registry record names the tool |
| 56 | M9 Step 3 | Doc drift | The expected `disposition: blocked by guardrail` can't come from the template (we got `undetermined`), and the kill-switch step pauses `nemotron-nano-9b`, which the Step 1b agent doesn't use |

---

## 1. Control plane checkpoint can never pass — Bug

**Where:** Module 3 → "The control plane: MoDaaS operators" → Checkpoint

**Guide:**
```bash
kubectl get deploy -n modaas-system --no-headers | awk '$2 != $4 {found++} END {print found+0}'
```
It should print `0`.

**Observed:** `6`, even though all six deployments are at full replicas.

**Why:** `$2` is the READY column (`1/1`, `2/2`) and `$4` is AVAILABLE (`1`, `2`). awk compares them as strings, and `"1/1" != "1"` is always true, so every healthy deployment counts as a failure.

**Evidence:**
```
aws-agent-operator       $2=1/1  vs $4=1  -> counted as broken
...
modaas-pdp               $2=2/2  vs $4=2  -> counted as broken
```
We confirmed the cluster is healthy from `.status.availableReplicas` against `.spec.replicas`: 0 mismatches.

**Suggested fix:**
```bash
kubectl get deploy -n modaas-system --no-headers | awk '{split($2,r,"/"); if (r[1] != r[2]) found++} END {print found+0}'
```

**Impact:** every participant who runs this check is told their platform is broken when it is not. That costs time and trust in the checkpoints.

## 2. Gateway is reachable from the internet over plain HTTP — Security (the guide notes it)

**Where:** Module 2 Step 5 (the API surface) and Step 7 (call a tool)

**Observed:**
- The `modaas-agw` Service is `type: LoadBalancer`. Its hostname is a public ELB name, not `internal-…`.
- Listeners: `http:8080` (tools), `llm:8081` (models), `llm-tls:8443`.
- From outside the VPC, a request with **no credential** gets an HTTP 404 from the gateway on both 8080 and 8081, so the listener is reachable. We did not send the API key over this path.
- `ModelConfig` and `ToolConfig` objects publish their `.status.endpoint` as `http://<public-elb>:808x/...`.
- Step 7 says: *"the public endpoint above is plain HTTP, so calling it from outside would send the token unencrypted."* The risk is acknowledged there, but the advertised endpoint is still the plaintext one.

**Why it matters:** the team API key is the single credential that opens every model and tool route. If it travels in cleartext on the public internet, anyone on the network path can capture and replay it.

**Questions for the platform team:**
- Should the LoadBalancer be internal, or limited to the IDE's egress range?
- Should status endpoints advertise the TLS listener (`llm-tls:8443`) by default, and is there a TLS listener for MCP tools?

**The exposure is already being probed (added 2026-10-05):** X-Ray holds `modaas-agw` traces of **54 `GET` requests** from outside, between 2026-10-04 09:51 and 21:05 CDT (14:51 to 02:05 UTC). Host headers: 50 bare public IPs, 2 the EC2 public DNS name, 1 `probe.invalid`, 1 `a7x.overflow.biz`. That is typical internet scanning. Two further `GET`s addressed to the ELB hostname were our own unauthenticated reachability checks and are excluded.

**Also used by the platform's own agents (2026-10-05, Module 9; `bedrock-agentcore-control get-agent-runtime`, variable names and URL schemes only):**
- All five AgentCore runtimes (`customer_experience_agent`, `it_resolution_agent`, `network_resolution_agent`, `hackathon_helper` and Module 9's `my_agent`) run in `VPC` network mode, yet reach the gateway through the public load balancer over plain HTTP:
  - `OPENAI_BASE_URL` = `http://<public LB>:8081/v1` and `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` = `http://<public LB>:8081/bedrock`
  - `AGENTCORE_GATEWAY_MCP_URL` (the reference agents and the helper) or `TOOL_MCP_URL` (`my_agent`) = `http://<public LB>:8080/mcp/<alias>`
- The gateway's TLS listener (`llm-tls`, 8443) is configured, but no runtime uses it. We haven't tested it.
- So the team key, the bearer on each request, travels unencrypted on every model and tool call the agents make.

## 3. Any pod can reach a tool backend directly and skip the gateway — Security (verified)

**Where:** Module 2 Step 7 ("The same tool, reached two ways") and Module 3 → "The enforcement substrate: is isolation real?"

**Guide, M2 Step 7:** *"`kubectl port-forward deploy/modaas-docs-mcp -n components 8080:8080` and a direct `POST /mcp` also work, with no credential, no policy decision and nothing for an auditor to see."*

**Guide, M3 Isolation:** *"Together these say the governed path is the only path: a pod in components that tries to skip the gateway is blocked by the network."* That holds for destinations **outside** the allowed namespaces, such as Bedrock. It does not hold for tool backends **inside** `components`.

**Test:** we sent the same unauthenticated MCP `initialize` request (no `Authorization` header) by three paths, from throwaway `curlimages/curl:8.5.0` pods:

| From | To | Result |
|---|---|---|
| pod in `default` | gateway `modaas-agw…:8080/mcp/modaas-docs` | **403 Forbidden** (correct) |
| pod in `default` | `modaas-docs-mcp.components:8080/mcp` | **200 OK + `mcp-session-id`** |
| pod in `components` | `modaas-docs-mcp.components:8080/mcp` | **200 OK + `mcp-session-id`** |

We stopped after the handshake and did not call a tool directly.

**Why it works (from the cluster spec):**
- All 4 NetworkPolicies in the cluster are `policyTypes: [Egress]`. None restricts **ingress**, so a tool pod accepts connections from any namespace.
- `components-egress-governed-only` ends with an egress rule `to: [{podSelector: {}}]`, so any pod in `components` can reach any other pod in `components` on any port.
- `components` has `istio-injection: enabled`, but there is no `PeerAuthentication` or `AuthorizationPolicy` in any namespace. Istio's default is PERMISSIVE mTLS, so plaintext from pods outside the mesh is accepted.
- Participants can create pods in `default` (the guide's own `incluster` helper does it) and have `create pods/portforward` in `components`. In fact they can do both in every namespace tested; see #26.

**Scope:** every **pod-hosted** tool: `modaas-docs-mcp`, `demo-tool-backend`, and anything built with `starter/new-tool.sh`, whose template deploys a Deployment + Service into `components`. The 7 Lambda tools sit behind the AgentCore Gateway and are not pods, so this does not apply to them.

**Impact:** a caller who skips the gateway skips identity, the Cedar decision, the guardrail, the rate limit and the access log. The evidence ledger never sees the call.

**Possible fixes:** an ingress NetworkPolicy on tool pods that admits only the `modaas-agw` pods in `agentgateway-system`, and/or STRICT mTLS plus an Istio `AuthorizationPolicy` that allows only the gateway's service-account principal. Neither stops `kubectl port-forward`, which goes through the kubelet; that needs RBAC (remove `pods/portforward` from participants in `components`).

**Note:** the guide names closing side entrances as a gap worth taking on in the build block, so this may be intended challenge material rather than a defect. The isolation page's "the governed path is the only path" still overstates what is enforced, and so does the Module 3 closing summary: *"There is one perimeter, not a side door — Step 4: one authorization policy on every listener."* The platform checkpoint `validate-canvas.sh` passes its check *"agentgateway listeners (http llm llm-tls) all covered by modaas-authz"* while this side door is open. It verifies the door, not the walls.

**The Module 4 diagrams make the same claim (added 2026-10-05):** `modaas-platform-architecture.svg` labels the gateway "the ONLY door" and the direct path "no side doors — by design". `architecture-hero.svg` says "THE ONE DOOR — agentgateway" and "the only way in". The direct-Bedrock part ("denied at 3 layers") is verified (Module 2 Step 4). The tool-backend side door is not closed. The diagram is in this repo at `notes/workshop-reference/modaas-platform-architecture.svg`.

## 4. ModelConfig older versions are listed but not served — Doc accuracy

**Where:** Module 3 → "The declarative surface: resource types"

**Guide:** *"ModelConfig also still serves its two earlier versions so older manifests keep working."*

**Observed:**
```
v1alpha1  served=false  storage=false
v1alpha2  served=false  storage=false
v1beta1   served=true   storage=true
```
The guide's command uses `.spec.versions[*].name`, which lists every *defined* version, so its output looks right. A manifest using `v1alpha1` or `v1alpha2` would be rejected.

**Suggested fix:** change the sentence, or list only served versions with `-o jsonpath='{.spec.versions[?(@.served==true)].name}'`.

## 5. Guide shows an emptier cluster than bootstrap now creates — Doc drift

| Guide says | Observed | Created by |
|---|---|---|
| M2 Step 5: `kubectl get modelconfig -n components` is empty | 4 ModelConfigs: `nemotron-nano-3-30b` and `nemotron-super-120b-helper` Approved; `nemotron-nano-9b` and `nemotron-super-120b` in Reviewing | bootstrap step 15/18 "demo ModelConfigs" |
| (no ToolConfigs implied before Step 7) | 8 ToolConfigs already Approved: aws-knowledge, cluster-status, cr-author, customer-records, evidence-lookup, helper-docs, network-twin, runbook-lookup | bootstrap step 14/18 "Lambda tools deploy" and others |
| M3 overview: "4 accepted policies" | 6 accepted: modaas-access-log, modaas-authz, modaas-ceiling, modaas-llm-auth, modaas-mcp-ratelimit, modaas-telemetry-export | bootstrap steps 11/18 and 13/18 |

**Impact:** low, but participants who compare against the captured output may think something is wrong. Two models sitting in `Reviewing` with nothing in the guide to explain them is the most likely to confuse.

## 6. Installer step count — Doc drift

**Where:** Module 2 Step 2

**Guide:** status reads `RUNNING <n>/8 <step>`; "which of the eight steps".

**Observed:** `scripts/bootstrap-platform.sh` labels steps `1/18` … `18/18` (step 18 switches the IDE's access entry from `AmazonEKSClusterAdminPolicy` to `AmazonEKSAdminPolicy` + `modaas:participants`).

## 7. A blocked prompt returns HTTP 200 — Design note (in the guide; recorded for our own build)

**Where:** Module 2 Step 5

The gateway follows the OpenAI wire format: a guardrail block returns `200` with `finish_reason: "content_filter"`, content `Input blocked by policy.` and `usage.total_tokens: 0`. Any client or test that checks only the HTTP status will treat a blocked call as a success. This is not a defect, but it is the most likely way an assurance check passes when it shouldn't. Our own checks will assert on `finish_reason` and token counts.

---

## 8. `modaas-llm-auth` contains no authentication — Doc accuracy

**Where:** Module 3 → "The perimeter: the governed gateway"

**Guide:** *"modaas-llm-auth adds the API-key check on the model listeners."*

**Observed:** the spec of every gateway policy:
```
modaas-access-log        {"frontend": ["accessLog"]}
modaas-authz             {"traffic": ["extAuth", "transformation"]}
modaas-ceiling           {"traffic": ["rateLimit"]}
modaas-llm-auth          {"traffic": ["rateLimit"]}        <- rate limit only
modaas-mcp-ratelimit     {"traffic": ["rateLimit"]}
modaas-telemetry-export  {"frontend": ["accessLog", "tracing"]}
```
The credential is checked by `modaas-authz`: `extAuth` to `modaas-system/modaas-authz:8080` with `failureMode: FailClosed`. It targets the whole gateway, so every listener is covered, which is the stronger design. Only the guide's description, and arguably the policy's name, is misleading.

**Also checked, not a gap:** `modaas-ceiling` targets only the `llm` listener, not `llm-tls`. But `modaas-llm-auth` already applies identical limits (100 req/min, 2.5M tokens/h) to both `llm` and `llm-tls`, so TLS traffic is not uncapped. It would become a gap only if the stack's `RequestCeilingPerMinute`/`TokenCeilingPerHour` were set *lower* than the chart's defaults: the tighter ceiling would then apply to `llm` alone.

**Checkpoint:** prints `6`, not `4`. The two extra policies are `modaas-ceiling` and `modaas-telemetry-export` (see #5).

## 9. Gateway routes exist for models still in Reviewing — To verify in Module 5

**Observed:** there are 4 `AgentgatewayModel` routes in `agentgateway-system`, one per ModelConfig, including `nemotron-nano-9b` and `nemotron-super-120b`, which are still `Reviewing`. Both model listeners report `attachedRoutes=4`.

For tools, Module 2 Step 7 says that until approval *"the gateway has no route to call."* For models, the route exists before approval, so blocking an unapproved model must happen at the Cedar decision (`modaas-pdp`), not in routing.

**Not yet tested:** whether a call to a `Reviewing` model is actually refused. **Update:** both models were approved at 23:57 and 23:58 UTC by `cloudshell-user@team` (someone working from CloudShell in this account), so they can no longer be used for this test. Testing it now needs a freshly declared, unapproved model.

## 10. Evidence store (`audit-store`) — Checked, OK with notes

The audit store runs in `components`, so it is reachable directly too (see #3). We checked whether that allows forged evidence:

- **Writes are gated (verified live):** the deployment loads `AUDIT_WRITE_TOKEN` from secret `components/audit-write-token`, and the running pod has a 32-character token set. The code the pod runs (`/app/store.py`, from ConfigMap `audit-store-app`) is byte-identical to the kit's `reference-impl/audit-store.py`, where `POST /records` without a matching `X-Audit-Token` gets `401` (`hmac.compare_digest`). The source notes that before 2026-09-19 the variable was ignored and forged POSTs returned `201`; that is fixed in this deployment. We did **not** send a test write, because it would pollute the ledger teams are graded on.
- **Reads are open by design:** `GET /records` and `/timeline` need no auth. The code comment says this is intentional, because the labs read the timeline from throwaway pods. Worth confirming that nothing sensitive (customer records, prompts) ends up in records readable by any pod.
- **Participants can read the write token:** `kubectl auth can-i get secret/audit-write-token -n components` → `yes`. A human participant could forge records; an agent cannot unless it is given the token. **Update (2026-10-05):** the token is also a literal value in AgentConfig specs, and the cockpit's CR view returns it to anyone with the cockpit link (#24, #26).
- **Open question:** `components` egress allows all of `modaas-system` on any port, which includes the OpenTelemetry collector (OTLP gRPC 4317). If gateway spans are part of the evidence, can a pod in `components` push forged spans to the collector? Not tested; we'll look at this on the "evidence lane" page.

## 11. Step 4 egress probe can report a stale result — Robustness

**Where:** Module 2 Step 4, section 4

The inline block runs `kubectl run egress-probe …`, sleeps 25 s, prints `kubectl logs egress-probe`, then deletes with `--wait=false`. If an earlier `egress-probe` pod still exists (we found one left from an earlier run), `kubectl run` fails with AlreadyExists. The error goes to stderr and is easy to miss, and nothing stops the block, so 25 s later `kubectl logs` prints the **old** pod's output: a pass for a probe that never ran. The `incluster` helper avoids this by deleting any existing pod first. Using `incluster`, or adding `kubectl delete pod egress-probe -n components --ignore-not-found` first, fixes it.

## 12. Approver identity is self-asserted — Documented limitation

**Observed:** all 14 approval records in `status.governance.approvals` have `"signature": ""`. `subject` is whatever string was in the `modaas.tmforum.org/approver` annotation. The guide's command makes it `$(whoami)@team`, so the "approver" is the local Unix username: `satyabratsrikumar@team` from a laptop, `cloudshell-user@team` from CloudShell, `ec2-user@team` from the IDE. None of these is the authenticated identity (all three run as the same AWS role).

**The platform's own source** (`operators/shared/asset_operator.py`, `_materialize_approval_from_annotations`):
> *"v0 role validation: the function trusts the K8s RBAC of whoever set the annotation."*
> *"For now subject + role from the annotation are taken at face value, audit trail is the K8s API audit log."*
> *"Full Keycloak JWT verification is out of scope … tracked as post-DTW."*

**Impact:** an auditor reading the approval record cannot tell who actually approved. Anyone with `patch` on the resource can write any approver name.

**And the fallback is switched off:** the source names the K8s API audit log as the real audit trail, but EKS control-plane logging is **disabled** in this account (`aws eks describe-cluster … cluster.logging` → `api, audit, authenticator, controllerManager, scheduler`, `"enabled": false`). The authenticated identity behind an approval is therefore not recorded anywhere.

**Worked example (this account):** `nemotron-nano-9b` and `nemotron-super-120b` show approver `cloudshell-user@team`. To find out who that was, we had to piece it together from CloudTrail: the CloudShell sessions active at the approval times (23:30–00:05 UTC) were all `WSParticipantRole/Participant` from the same public IP as the participant's laptop. The attestation texts match the guide's Module 5 "approve" page word for word. That is circumstantial: CloudTrail does not log kubectl calls, so no record links the annotation to a session or a person.

**Not a bug:** a known, documented v0 design. Listed because it's central to "who approved this?" questions.

## 13. Evidence ledger has no tamper evidence — Documented limitation, not a build target

**Observed (the fact):** the ledger has no tamper evidence. Together with #10 (write token readable by participants; reads open), it resists anonymous forgery, but nothing detects a record altered or removed by someone who holds the write token or the volume.

**The platform's own source** (`evidence/evidence_record.py`) says:
> *"Tamper evidence -- hash chaining, signatures, write-once storage -- is out of scope … stated as participant-challenge scope for the event and the named next step for the platform."*

**The masterclass judging slides say the opposite**, so it is not something participants should build:
- "Your Task" slide, OUT OF SCOPE: *"Not asked for, and not scored · Signing, hashing and Merkle trees over the ledger"*
- "Judgement Day" slide, OUT OF SCOPE: *"Do not spend time on these · Signatures, hash chains or Merkle proofs over the ledger"*
- "A pattern to start from" slide: the evidence ledger *"seals and chains it. [Seal is out of scope]"*

The challenge brief says the masterclass governs judging, so the rubric wins.

**For the platform team:** the code comment's "participant-challenge scope" contradicts the rubric. A participant who reads the source could spend build time on something that isn't scored. Suggest rewording the comment, e.g. "out of scope for this event; named next step for the platform".

*Correction, 2026-10-04: an earlier version of this item labelled it "challenge scope" based only on the source comment. Reclassified after checking the masterclass rubric.*

## 14. Operator error-event noise — Minor

From `kubectl get events -n components --field-selector type=Error`, about 14 h after install:
- **75 events** `Request attempt #1/9 failed; will retry: PATCH https://172.20.0.1:443/apis/oda.tmforum.org/v1beta1/.../status -> ClientConnectorError(... ConnectionResetError())`, on ToolConfigs (57) and ModelConfigs (18). The first attempt fails and the retry succeeds; statuses stay current. Probably a stale keep-alive connection to the API server reused after each resync timer (cause not verified).
- **Canvas `api-operator-istio`** handler `implementation_status` crashes on `EndpointSlice/demo-tool-backend-*`: `labels["oda.tmforum.org/componentName"]` is missing, which leads to `UnboundLocalError: cannot access local variable 'componentName'` (`/apiOperatorIstio.py` line 1267), retried indefinitely. The `demo-tool-backend` Service is not an ODA Component, and the operator does not skip it.

Both look harmless, but they fill the event stream, which is where a participant looks first when something is actually wrong.

## 15. Status claims an AuthorizationPolicy that does not exist — Misleading status

**Observed:** every governed asset (10 ToolConfigs, 4 ModelConfigs, 1 AgentConfig) carries:
```
IstioPerAssetProvisioned=True  reason=IstioReady
"VirtualService + AuthorizationPolicy emitted for <asset>"
```
The cluster has **15 VirtualServices** (one per asset, `components/<asset>-vs`) and **0 AuthorizationPolicies** (`kubectl get authorizationpolicies.security.istio.io -A` → none). The participant role has list permission (`kubectl auth can-i list authorizationpolicies.security.istio.io -A` → `yes`), so they are not hidden from us. There are no PeerAuthentications either.

**What the source says** (`operators/shared/istio_vs_authz.py`):
- `emit_per_asset_istio()` builds a VirtualService and an AuthorizationPolicy. The policy ALLOWs a request only when the JWT claim `request.auth.claims[realm_access][roles]` contains `modaas-<kind>-<asset>-consumer`, and it is placed in the gateway namespace.
- A separate gate, `per_asset_authz_enabled()`, is documented as *"default OFF … DELIBERATELY off by default … With zero RequestAuthentication resources in the cluster the condition can never be satisfied, so enabling this without one DENIES all traffic to the gateway."* `MODAAS_PER_ASSET_AUTHZ` is not set on any operator deployment.
- The condition is set to True whenever `emit_per_asset_istio()` returns without raising (`tool_operator.py:1054`, `model_operator.py:1184`).

**Not established:** why the objects are absent. In this source snapshot the gate function is defined but never called. The tool-operator log has Istio `validation.istio.io` webhook denials (*"hosts must be FQDN …"*) whose target we have not identified. The deployed image could also differ from the staged source. Whatever the cause, the status message says something the cluster contradicts.

**Impact:** CR status is the platform's own evidence surface (the cockpit's Governance view and any status-reading evidence tool rely on it). Anyone reading it would believe a per-asset Istio authorization control is in place. It isn't.

**Relation to #3:** none. Even if enabled, this policy gates traffic **at the gateway** by JWT role. It does not restrict direct connections to tool backend pods, so the side entrance in #3 is unaffected either way.

**Suggested fix:** set the condition from what was actually created. For example: `"VirtualService emitted; per-asset AuthorizationPolicy disabled (MODAAS_PER_ASSET_AUTHZ unset)"`, or read the object back after creating it and report False if it is missing.

## 16. "Tamper-resistant ledger" overstates the audit store — Doc accuracy

**Where:** Module 4, `architecture-hero.svg`: *"Audit store — tamper-resistant ledger"*.

**Observed:** the store rejects writes without the `X-Audit-Token` (#10), which resists *anonymous* writes. It has no tamper evidence (#13): a holder of the token or the volume can add, alter or remove records undetected, and participants can read the token. "Write-protected ledger (token-gated)" would describe it accurately.

## 17. TMF639 status contradicts the inventory — Misleading status

**Where:** Module 4 evidence surfaces ("TMF639 inventory"; the hero diagram's "every asset discoverable — TMF639-shaped records").

**Observed (2026-10-05):**
- All 14 approved assets carry `TMF639Projected=False`, message `"POST /resource → timed out"`. The Reviewing asset has no such condition.
- Yet the inventory (`kubectl get --raw /api/v1/namespaces/canvas/services/resource-inventory:80/proxy/tmf-api/resourceInventoryManagement/v5/resource`) holds **all 15** as `LogicalResource`, including `demo-crm-lookup`, which is still `Reviewing`.
- Every record shows the same state, `resourceStatus=standby, operationalState=disable, administrativeState=unlocked, usageState=active`, whether the asset is approved and serving or awaiting review.

**Impact:**
- The CR condition says the inventory projection failed when the records exist.
- The inventory, presented as a standards-shaped audit surface, cannot tell an approved, serving asset from one awaiting review.

**Suggested fix:** set the condition from a read-back of the record. Map CR phase to TMF639 state, e.g. Reviewing → `resourceStatus=standby`, Approved and routed → `available`/`enable`.

**The guide's explanation (Module 5 overview, added 2026-10-05):** *"TMF639Projected stays False because the operators' egress NetworkPolicy has no path to the inventory pod on port 8639. The inventory holds the ODA Component entries; the condition does not affect serving."*
- **Confirmed:** `aws-model-operator-egress` allows only port 443 to anywhere, port 80 to the Pod Identity agent (169.254.170.23), and DNS/443 to `kube-system`. Service `canvas/resource-inventory` maps 80 → **8639**, so the operator's `POST /resource` times out.
- **Not explained:** why the inventory still holds a `LogicalResource` record for **every** governed asset, including one still Reviewing. Some other writer creates them, and we have not identified it. It is not the cockpit: its `tmf639_inventory.py` only GETs, and its one POST mints a read token.
- **So the condition is known-stale, as the guide says, but the claim that records aren't projected is wrong in practice.** The inventory's states still don't reflect approval.

## 18. "API key / OAuth": only the API key is verified — Doc accuracy, to verify

**Where:** Module 4, `modaas-platform-architecture.svg`, step *"1 · Identity — API key / OAuth — who is calling?"*

**Observed:**
- The API key is verified: `modaas-authz` via gateway `extAuth`, `failureMode: FailClosed` (#8).
- For OAuth/JWT there are **0** Istio `RequestAuthentication` resources, and the per-asset JWT AuthorizationPolicy is off by default (#15).
- The guide says Canvas-issued JWTs are resolved by `modaas-authz`. We have not tested that path, so it may work inside `modaas-authz` alone.

**Ask:** is the OAuth/JWT path live in this build? If so, which issuer, and is it covered by any test?

## 19. Reference-agent self-check cannot pass as shipped — Bug (kit)

**Where:** Module 7 "Self-check: three faults" (`reference-impl/score-run.py`); guide grades *"S1-fronthaul-degradation | auto-resolve | PASS (8/8)"*, *"S2 … FAIL (7/10)"*, S3 PASS (10/10).

**Observed (source, 2026-10-05):**
- **Guardrail check:** `score-run.py:99-102` requires the word `guardrail` in every INVOCATION record's detail. `reference-agent/agent.py` never writes it: 0 occurrences of "guardrail" in the file. Its invocation detail is `"governed call via alias …: http_status=…"`.
- **Negotiation check:** `score-run.py:108-110` requires a NEGOTIATION phase whenever a scenario sets `expect_negotiation`, and all three do (`data/network-inventory.json`). `agent.py` writes a negotiation record only in `_handle_negotiate` (agent.py:199-200, 302), which runs only when the request payload contains a `negotiate` key. `starter/ask_agent.py:114` sends only `{"correlation_id", "context"}`.

**Impact:** both checks fail on every run of the shipped agents, so the guide's sample grades cannot be reproduced. The guide's index also says *"guardrail verdict on every model call … is the shape judges score"*, a shape the shipped code doesn't produce.

**Confirmed live (2026-10-05, Module 7):**

| Scenario | Guide | Our runs |
|---|---|---|
| S1 fronthaul | PASS (8/8) | FAIL 6/8, three times (`fault-1791175626-0d34e2`, `fault-1791177843-fde682`, and the model-swap run `fault-1791179282-8ef1a8`) |
| S2 congestion | FAIL (7/10) | FAIL 5/10 (`fault-1791177342-d3f892`) |
| S3 restricted change | PASS (10/10) | FAIL 8/10, twice (`fault-1791177636-8fa0bd`, `fault-1791177926-b0ce69`) |

Every run failed the guardrail-verdict and negotiation checks, the two that fail by construction. The S3 dispositions were all correct (escalate). The guide's grades can't be reproduced with the shipped agent.

## 20. Ledger contents differ from the guide — Doc accuracy

**Guide (reference-agents/run-and-read):** *"a correlation id that joins 10 records across three agents"*; *"AUDIT TRAIL -- 10 records"*; *"Each invocation record carries trace_id, action_id, the model id, the guardrail verdict, and the token counts."*

**Source (`reference-agent/agent.py`):**
- **Successful run: 12 records.** Each agent writes intent (:214), tool-invocation (:260), invocation (:269) and result-inspection (:284).
- **Refused agent: 3 records** (:214, :237, :245).
- **Body fields** (`post_audit`, :138-165): `correlation_id, step, phase, actor, detail, trace_id`. `post_audit` accepts `action_id`, but no call site passes it. There is no model id, guardrail verdict or token count.
- The tool-invocation record is written after the model call, with the model's answer as detail. It does not show the tool ran.

**Also:** `starter/pull-evidence.sh` labels the ledger export "otel-traces" and describes joining on trace_id/action_id. That join can't work: there is no action_id, and see #21 for trace_id.

## 21. The run's traceparent never reaches the agent code — Bug (kit)

**Guide (Module 4):** *"the traceparent header is your correlation key across components. Control 7 joins events across the three zones on it, and if it does not survive a hop, a run's records split silently."*

**Source:**
1. `run-reference.sh:55-61` mints one CID and one W3C traceparent for the whole run.
2. `starter/ask_agent.py:66-68` passes it as the AgentCore `--trace-parent` option, plus baggage `modaas-correlation-id=<cid>`. The JSON payload (:114) carries only `correlation_id` and `context`.
3. `reference-agent/agent.py:208` looks for `traceparent` **only in the payload**. When it's absent, `new_trace()` mints a fresh trace id (:69-71).

**Impact:**
- The `trace_id` in each agent's ledger records differs from the run's trace id, exactly the silent split the guide warns about.
- The CID still joins the ledger records, and the gateway's `modaas.run_id` uses the baggage CID (seen on `hackathon-helper`). So correlation survives through the CID, not the trace id.

**Suggested fix:** read the AgentCore request context or headers for the inbound traceparent, or include `traceparent` in the payload from `ask_agent.py`.

## 22. Spans carry the prompt and context, including customer records — Doc accuracy / data handling (verified in Module 8)

**Guide (agent-observability/console-and-metrics):** *"The reference agent records no prompt or completion text in its spans."*

**Source:**
- The agents are Strands agents (see #23). The Strands tracer's docstring (`strands/telemetry/tracer.py`, installed version) says that by default message content is emitted as **span events**. Setting `gen_ai_span_attributes_only` in `OTEL_SEMCONV_STABILITY_OPT_IN` moves it into span attributes instead.
- `agent.py` sets no option that disables content capture.
- Our research pass saw span events on `hackathon-helper`'s `chat` spans (a live observation, on the helper only). We have not inspected their content.

**Why it matters:** if prompts and completions land in the runtime's CloudWatch spans, any data in a scenario prompt (customer records, for instance) is stored there too. Check once Module 7/8 produces spans.

**Verified (2026-10-05, Module 8; model-swap S1 run, trace `e13e7b73…`, each runtime's `spans` stream in `/aws/bedrock-agentcore/runtimes/<id>-DEFAULT`):**
- All three agents' span records carry `content` and `gen_ai.choice` fields.
- **Scenario text appears in 5 (customer), 7 (IT) and 16 (network) span records.** In the customer agent's `chat` span:
  - `events[0].attributes.content` holds the system prompt (*"/no_think You are a telecom Customer Experience agent…"*)
  - `events[1].attributes.content` holds the full context, including customer records (`CUST-1001`, "Meridian Logistics (gold)")
- We confirmed prompt and context text. We didn't open a `gen_ai.choice` event, so completion text is likely but not confirmed.

**Impact:**
- The guide's statement is wrong for the deployed agents.
- Customer data from the scenarios sits in CloudWatch Logs, readable by anyone with log access, and nothing classifies it (see #40).
- For evidence it cuts both ways. What each agent was told can be recovered from the spans, but they are written by the agent itself: a cross-check, not a figure of record.

**Suggested fix:** correct the guide. Either disable content capture in the reference agent (or opt into attributes-only spans), or say plainly that prompts and context are logged.

## 23. Other reference-agent drift — Doc drift / minor

- **Framework:** the guide says *"All three run the same small Python program with no framework."* `agent.py` is a Strands `Agent` in a `BedrockAgentCoreApp`.
- **Protocol:** network-tool-naming says the network agent *"talks to a mock JSON fault-injection dataset over plain HTTP (`/handle`, `/negotiate`)"*. The shipped agents call MCP tools through the gateway, and there is no `/handle` or `/negotiate` route.
- **Default model is inconsistent:** `make-agentcore-agents.py:47` `DEFAULT_MODEL = "nemotron-super-120b"`; `reference-impl/agents.yaml` uses `nemotron-nano-9b`.
- **Stale comments:** `build-agent-image.sh:86` mentions `agent.py negotiate_with_it`, and `:169` says *"agent.py alone is ~24.6 KB"*. The shipped `agent.py` is 10,979 bytes and has no `negotiate_with_it`.
- **Stale `agents.yaml`:**
  - `provider: kubernetesPod` with image tag `reference-agent:v2`, while the build produces `v5`.
  - The pod build target installs no SDK, yet `agent.py` imports strands.
  - Its swap-model comment patches env index 2, while the guide patches `dependsOn.models/0`.
- **Counting caveats:**
  - `starter/evaluate.py:86-97` sums tokens over every gateway record with the run's `modaas.run_id`, which is fine because MCP records add 0. But it lists every record's `modaas.action_id` as a "call", tool calls included.
  - `reference-impl/show-run-spans.py:105-113` adds every span that has usage attributes. On `hackathon-helper` the parent `invoke_agent` span carries the summed totals of its `chat` spans, so this would double-count.
- **Audit token on disk (security, minor):** `make-agentcore-agents.py` reads Secret `audit-write-token` (:201-204), puts it into the agents' env (:233, :319), and writes the result to `/tmp/agents-agentcore.generated.yaml` (:48) without restricting the file's permissions.

## 24. The ledger write token is readable from the AgentConfig spec and through the cockpit — Security (verified)

**Observed (2026-10-05):**
- **In the spec:** `hackathon-helper`'s AgentConfig carries `AUDIT_WRITE_TOKEN` as a **literal 32-character value** in `spec.awsAgentCore.environmentVariables`, not as a `valueFrom` Secret reference. The reference-agent generator does the same for the three agents: it reads Secret `audit-write-token` and inlines it (`make-agentcore-agents.py:201-204, 233, 319`).
- **Who can read it:** anyone who can `get agentconfigs`, which includes participants. Participants can also read the Secret itself (#10, #26).
- **Through the cockpit:** `GET /api/cr/AgentConfig/components/hackathon-helper` returns the CR's full YAML. `_build_cr_payload` uses `kubectl get -o yaml`, and `server.py` contains no redaction. We confirmed **the token string is present in that response**. We checked it as a yes/no match only; the value was never printed or stored.

**Impact:** the cockpit is presented as a read-only dashboard whose link is its only credential (#25). Anyone holding that link can read the ledger write token, then append records to the audit store. The `audit-store.py` source calls that store *"the ledger every team is graded on"*. #10's write gate only stops callers *without* the token.

**Suggested fix:**
- Inject the token with `valueFrom.secretKeyRef` (or AgentCore's own secret mechanism) instead of a literal env value.
- Redact `environmentVariables` values in the cockpit's CR view.

## 25. The cockpit has no login of its own and is not read-only — Security / doc accuracy

**Guide:**
- *"The MoDaaS cockpit, a read-only dashboard of the platform"* (platform-access/open-ide)
- *"A read-only web UI over the governed estate"* (resources/glossary)
- *"The cockpit is read-only over the same APIs you use from the CLI"* (resources)

**Observed (source `modaas-ui-src.zip` → `server.py`, and live):**
- **No auth in the backend:** the header reads *"No login/auth (runs on a kiosk)."* All protection is the CloudFront/nginx token-to-cookie exchange. The bare URL returns **403**; the CockpitUrl with its token returns **200** and sets one session cookie.
- **A write-like route:** CORS allows `GET` and `POST`. `POST /api/agents/{name}/ask`, documented as *"Invoke a governed agent via AgentCore Runtime"*, runs any Approved AgentConfig that has a runtime ARN. That means model calls, token spend and ledger writes, triggered by anyone with the link. We did not call it.
- **Combined with #24,** the link also yields the ledger write token.

**Suggested fix:** document the POST, or put it behind a separate control. Describe the cockpit as "read-mostly; can invoke approved agents".

## 26. Participant RBAC reaches protected namespaces — Security

**Observed (`kubectl auth can-i` as the participant role, 2026-10-05):**

| Namespace | get secrets | create pods | create pods/portforward |
|---|---|---|---|
| kube-system | yes | yes | yes |
| agentgateway-system | yes | yes | yes |
| modaas-system | yes | yes | yes |
| canvas-vault | yes | yes | yes |

The role is not cluster-admin: `*/*` → no, `create clusterrolebindings` → no. The cause is ClusterRoleBinding `modaas-participant-admin`, which binds group `modaas:participants` to the built-in **`admin`** ClusterRole cluster-wide (seen in Module 3).

**Impact:** participants can read the gateway API keys (Module 2 Step 4 relies on this), the ledger write token, and secrets in `canvas-vault` and `kube-system`. They can also run pods in the gateway's own namespace. The isolation story (#3) assumes participants work in `components`.

**Question:** is cluster-wide `admin` intended for workshop simplicity, or should it be a namespaced RoleBinding in `components`?

## 27. Run ids are missing from the durable gateway log — Evidence gap

**Observed (2026-10-05):**
- **CloudWatch `/aws/modaas/gateway`** (stream `modaas-agw`, retention 7 days): all 155 records carry top-level `trace_id`/`span_id`, plus attributes such as `gen_ai.usage.input_tokens`/`output_tokens`, `agw.ai.usage.cost.total`, `gen_ai.request.model`, `listener`, `http.*` and `mcp.*`. 4 records carry token counts.
- **No** record has `modaas.run_id`, `modaas.trace_id` or `modaas.action_id`.
- Those three are added by the `modaas-access-log` policy and appear only on the gateway pod's **stdout** lines, which are ephemeral. The kit reads stdout: `pull-evidence.sh` uses `kubectl logs`, and `evaluate.py` filters on `modaas.run_id`.

**Impact:** once the gateway pod restarts or its log rotates, per-run token evidence can't be joined by run id. The durable copy needs a second hop: CloudWatch `trace_id` → `/modaas/evidence` `modaas.evidence.correlation_id`, which is present on 60/60 evidence records.

**Suggested fix:** add the same `modaas.*` attributes to the OTLP access-log export (`modaas-telemetry-export`).

## 28. Models and tools still report "paused" after resume — Misleading status

**Observed (2026-10-05):**
- `nemotron-nano-9b`: `spec.paused=false`, generation 3, `AgentgatewayRouteProgrammed=True` (route re-applied at 00:33:31 UTC).
- Still present:
  - `ReconcilePaused=True`, since 00:32:48, with message `spec.paused=true`
  - `RegistryPauseProjected=True`, message *"Registry record aws-bedrock_nemotron-nano-9b marked servingState=PAUSED …"*
- Who paused and resumed it is unknown. There was CloudShell activity at the time; it was probably the Module 6 pause lab.

**Impact:** CR status, and possibly the registry, say the model is paused while it serves traffic. We did not read the registry's servingState directly.

**Suggested fix:** on unpause, flip both conditions and re-project servingState to serving.

**Reproduced (2026-10-05, a clean cycle run in the workshop shell; see #36):**
- Pause 04:05:20 UTC, resume 04:06:02. Afterwards `generation=7`, `observedGeneration=7`, phase `Approved`, route re-programmed at 04:06:25, and calls return 200.
- Still: `ReconcilePaused=True (SpecPaused)` and `RegistryPauseProjected=True` ("…marked servingState=PAUSED…"), now re-dated **04:05:53**, the moment the pause was processed.
- So resume never clears these conditions or the registry's PAUSED state. It isn't a one-off left over from the earlier CloudShell cycle.

**Also on a ToolConfig (2026-10-05, Module 7 kill switch on `modaas-docs`):**
- Paused 05:56:43, unpaused 05:56:50, serving again by 05:57:22.
- Now `spec.paused=false`, phase `Approved`, route programmed at 05:57:13.
- Yet `ReconcilePaused=True` (SpecPaused, 05:56:44) and `RegistryPauseProjected=True` (ServingStatePaused, 05:56:45) remain. So the stale status affects tools as well as models.

**Also on `nemotron-super-120b` (2026-10-05, Module 9 Step 3 kill switch):**
- Paused 09:13:04 UTC, unpaused 09:13:07.
- Afterwards `spec.paused=false`, phase `Approved`, route re-programmed at 09:13:31 (that condition now reads 10:37:20, from a later reconcile).
- Yet `ReconcilePaused=True` (SpecPaused, 09:13:05) and `RegistryPauseProjected=True` (ServingStatePaused, 09:13:05) remain, and were still there at 14:45 UTC. So the stale status isn't specific to nano-9b.

## 29. Telemetry tap not shipped, so the cockpit's live panels are empty — Build gap

**Observed (2026-10-05):**
- **Why it's missing:** bootstrap step 12/18 deploys the telemetry tap only if `scripts/telemetry-tap/` exists in the event asset bucket. It doesn't (`aws s3 ls …/assets/scripts/telemetry-tap/` → empty), so the step takes its *"telemetry tap not shipped in this build"* branch.
- **What's empty in the cockpit:**
  - per-run usage (`/api/usage/runs`, `/api/usage/by-agent`: source `telemetry-tap:unavailable`)
  - live drift and live ceilings (*"no live source on this build"*)
  - `/api/telemetry/{spans,logs,decisions}` and `/api/evidence/run/{id}`, which return **empty** data labelled `source: fixture` (*"Telemetry tap not connected; showing fixture data"*)

**Impact:** the cockpit panels a team would use to show per-run usage, drift and ceilings are empty in this build, so any guide step that points at them will show nothing. Positive: no sample data is passed off as live.

## 30. AICT stack description contradicts what was created — Doc accuracy (facilitator stacks)

**Observed (CloudFormation + CloudTrail):**
- Stack `a-03-servicenow-aict` (created 2026-10-04 22:02:58 UTC by `assumed-role/WSOpsRole/Ops`) describes itself as: *"No IAM user and no access key is created here or anywhere in this workshop."*
- The same role then:
  - ran stack `aict-servicenow-user` (22:43 UTC), which created IAM user `ServiceNowAictUser` (`CreateUser`, 22:43:30 UTC)
  - called `CreateAccessKey` for that user directly (22:44:59 UTC)
  - put policy `AictGetRole` on the IDE instance role (`PutRolePolicy`, 22:45:47 UTC)

**Impact on participants:** none. The description is simply out of date, and the account now holds a long-lived IAM access key. This is facilitator-owned, flagged only for accuracy.

## 31. The unsafe-model example trips two admission rules — Doc accuracy (minor)

**Guide (Module 4 Step 1, capability 1):** the dry run *"prints: a validation error refusing the model because safety.required=true cannot be combined with enforcer.kind=none."*

**Observed:** `kubectl apply --dry-run=server -f /tmp/unsafe-model.yaml` returns two errors, the first one unexpected:
1. *"spec.safety.required=true demands spec.governance.approval.required=true — no silent auto-approve …"*
2. *"safety.required=true cannot be combined with enforcer.kind=none …"*

The example omits `governance.approval`, so it can't isolate the rule it illustrates. Adding `governance: {approval: {required: true}}` would leave only the intended error. Nothing was stored, as the guide says.

## 32. The trace pipeline does export to X-Ray — Doc accuracy

**Guide (Module 6 overview):** *"The opentelemetry-collector in modaas-system runs on every call; its trace pipeline has no durable exporter (spans are discarded), but its audit pipeline writes decision records to the CloudWatch log group /modaas/evidence."*

**Observed (2026-10-05):**
- The gateway sends spans to the collector: policy `modaas-telemetry-export` `spec.frontend.tracing.backendRef` = Service `modaas-system/opentelemetry-collector:4317`.
- The collector's `traces` pipeline is `otlp` → processors `attributes/scrub-payloads`, `batch` → exporter **`awsxray`** (region us-east-1). Only the `metrics` pipeline is discarded (exporter `debug`).
- X-Ray holds **105 traces with `modaas-agw` spans in the last 24 h**. Two of them join `hackathon_helper.DEFAULT` (the AgentCore runtime) with `modaas-agw` in one trace.

**Impact:** a team that follows the guide would treat X-Ray as unavailable and miss a durable, joinable trace surface. For control 7, the gateway's spans plus AgentCore's spans in one X-Ray trace are exactly the cross-zone join the guide asks for.

## 33. A team Cedar policy loads but never decides anything — Doc accuracy

**Guide (Module 6, "Runtime Cedar policies"):**
- *"Cedar is where you can write your own rule and have the platform enforce it, and the decision log is where a judge sees it fire."*
- Step 1 adds `my-team-policy`, a broad `permit … unless restricted`, as a labelled ConfigMap.

**Observed (2026-10-05):**
- **It loads:** `loaded policy policy_id=my-team-policy version=421871 bytes=159` on both `modaas-pdp` replicas.
- **But each decision names one policy, and only that one is evaluated:**
  - `pdp/cedar_evaluator.py` `evaluate(policy_id, …)` reads `self._policies.get(policy_id)`, and an unknown id → DENY.
  - The auth gateway picks the id as `model-<asset>` or `modaas-toolconfig-<asset>` (`authz-gateway/app.py:88, 105-106`), unless the request header `x-modaas-policy-id` names another.
  - The gateway's extAuth forwards only `authorization`, `x-amz-*`, `traceparent` and `baggage` (policy `modaas-authz`), so gateway callers can't set that header.
- **Decisions naming `my-team-policy` since it loaded: 0.**

**Impact:**
- The step demonstrates *loading*, not *enforcement*. A team that writes its own rule this way sees "loaded" and might believe it governs calls. It doesn't.
- Safe side effect: the broad permit can't widen anyone's access either.

**Suggested fix:** show how to bind a team rule to an asset (e.g. a ToolConfig `access.cedarPolicy`, as `demo-crm-lookup` does), or have the PDP compose team policies with each asset's policy.

## 34. The Cedar step expects a probe that Module 5 no longer has — Doc drift

**Guide (Module 6 Cedar, step 2):** *"You see the calls you made in Module 5: ALLOW for the approved model and DENY for the undeclared alias."* The capture shows `decide policy_id=model-a-model-nobody-declared--DELIBERATELY-UNDECLARED-PROBE decision=DENY`.

**Observed:** the current Module 5 page "Call the model through the governed door" (as given to us on 2026-10-04) has three probes: direct Bedrock, no credential, and the governed call. It has **no undeclared-model probe**, so following the guide there is no DENY line to find. This is also why "a model nobody approved is refused" remains unverified (#9).

## 35. A guardrail-blocked or kill-switch-refused call is recorded as ALLOW — Evidence nuance

**Observed (2026-10-05):** our prompt-injection probe to `nemotron-nano-9b` (action `5f85e6ea…`, 03:32:41 UTC):
- **Response:** HTTP 200, `finish_reason=content_filter`, *"Input blocked by policy."*, 0/0/0 tokens.
- **Gateway line:** 0 input and 0 output tokens, cost 0.
- **PDP log:** `decide policy_id=model-nemotron-nano-9b decision=ALLOW matched=policy0`.
- **`/modaas/evidence` record:** `phase=decision, decision=ALLOW, matched_policy=policy0, policy_id=model-nemotron-nano-9b`, with **no guardrail field**.

**Why:** identity, then Cedar authorization (which allows), then the Bedrock guardrail (which blocks). The decision records the authorization step only.

**Impact:** an auditor reading the decision log or the evidence log alone would count a blocked attack as an allowed call. Whether a call was served or blocked lives only in the response and the gateway line (`finish_reason`, tokens). Any evidence chain has to join the two.

**Suggested fix:** emit a second evidence record for the guardrail outcome, or add `guardrail_action`/`finish_reason` to the decision record.

**Also through an agent, and for a kill-switch refusal (2026-10-05, Module 9 Step 3, `my-agent` on `nemotron-super-120b`):**
- **Guardrail block** (CID `my-agent-1791191546-6aa5dd`, 09:12 UTC): the answer was *"Input blocked by policy."*, and the gateway line has status 200 with 0/0 tokens.
  - PDP log: `decide policy_id=model-nemotron-super-120b decision=ALLOW`. `/modaas/evidence`: one record for the CID, `decision=ALLOW`, with no guardrail field.
  - The agent's ledger: `http_status=200`, `disposition=undetermined` (#56).
- **Kill-switch refusal** (CID `my-agent-1791191585-4d9744`, 09:13:06): the call got HTTP 404, because the paused model's route had been withdrawn (#36).
  - The PDP log and `/modaas/evidence` still record `decision=ALLOW`, `policy_id=model-nemotron-super-120b`, `policy_version=331993`.
  - The gateway's 404 line on the pod's stdout (listener `llm`, `/v1/chat/completions`) carries no `modaas.run_id`, `modaas.trace_id` or `modaas.action_id`. Its durable copy in `/aws/modaas/gateway` has the OTel `trace_id` (`f5140819…`, the same as the evidence record's), so the two can be joined, but it shows only the 404 and route `internal/llm:request`: no model and no reason.
  - Only the agent's ledger says `disposition=refused` (*"refused at gateway: http_status=404"*).
- So the decision record reads ALLOW whether the call was then blocked by the guardrail or refused because the model was paused. What happened to the call is only in the gateway line's status and tokens, and in the agent's own ledger.

## 36. The kill switch took 33–41 seconds on nano-9b (≤2 s on super-120b), and the paused model served meanwhile — Enforcement latency

**Guide (Module 6):**
- Overview: *"Pause — The kill switch withdraws a route instantly."*
- Pause page: *"At the end you know the kill switch withdraws a route instantly"*; *"The very next call, about 15 seconds later, is refused"*; *"the model served again about 50 seconds after resuming."*

**Measured (2026-10-05, `nemotron-nano-9b`):** the user ran a polling variant of the guide's commands in the workshop shell: patch, then call every ~10 s through the gateway.

| Time (UTC) | Event | Since the patch |
|---|---|---|
| 04:05:20 | `spec.paused=true` patched | — |
| 04:05:29, :40, :51 | calls **served, HTTP 200**, phase still `Approved` | +9, +20, +31 s |
| 04:05:53 | operator processes the pause (`ReconcilePaused` set) | +33 s |
| 04:06:01 | first **404**, phase `Paused` | **+41 s** |
| 04:06:02 | `spec.paused=false` patched | — |
| 04:06:25 | route re-programmed | +23 s |
| 04:06:37 | first **200** again | **+35 s** |

**An earlier run** (Claude, 03:46 UTC, the guide's block as written: one call 7 s after pausing, then resume) saw a 200 at +7 s. The operator still hadn't processed either change a minute later (`generation=5`, `observedGeneration=3`).

**Likely cause (not proven):** the model operator's reconcile is slow. Every resync pass waits through two 10-second TMF639 timeouts per model (`GET` + `POST /resource`, #17), and its status PATCHes fail on the first attempt and retry (#14).

**Impact:**
- Pause is the platform's kill switch, but for roughly 30–40 seconds after it is pulled the "paused" model keeps serving: calls are authorised, answered and charged tokens.
- For a spend or safety control (e.g. control 16), pause can't be treated as immediate prevention. In-flight and near-term calls after the decision still go through.

**Suggested fix:**
- Remove the TMF639 calls from the hot reconcile path, or shorten their timeouts.
- Make pause withdraw the route before any other reconcile work.
- State the measured latency in the guide instead of "instantly".

**Tools are much faster (2026-10-05, Module 7 "Kill switch" on `modaas-docs`):**
- Paused 05:56:43. The operator processed it within ~1 s, and the first probe (+7 s) got 404 *"route not found"*, phase `Paused`.
- Unpaused 05:56:50. The route was re-programmed at +23 s, and calls returned 200 again at +32 s.
- So the Module 7 page's *"you need every agent to stop reaching it within seconds"* holds for tools. The model pause above took 33–41 s.

**Model pause latency varies (2026-10-05, Module 9 Step 3 kill switch on `nemotron-super-120b`):**
- Paused 09:13:04 UTC. The operator set `ReconcilePaused` at 09:13:05, and the agent's call at 09:13:06 was refused (404) with the phase already `Paused`: ≤2 s after the patch.
- Unpaused 09:13:07. The guide's `kubectl wait --for=condition=AgentgatewayRouteProgrammed` returned at +24 s, and the agent answered normally again by +34 s.
- So the 33–41 s measured on nano-9b isn't a fixed property of a model pause. We don't know why the two differ.

## 37. Agents call tools they don't declare, and every call is allowed — Authorization gap (verified)

**Declared:** each reference AgentConfig lists one tool in `dependsOn.tools`: customer → `customer-records`, IT → `runbook-lookup`, network → `network-twin`.

**Observed (2026-10-05, Module 7 model-swap S1 run `fault-1791179282-8ef1a8`, trace `e13e7b73…`; gateway MCP lines and PDP log):**

| Agent (route) | Tool called | Gateway | PDP |
|---|---|---|---|
| customer (`/mcp/customer-records`) | `customer-records___customer_lookup` | 200 | ALLOW |
| IT (`/mcp/runbook-lookup`) | **`evidence-lookup___get_evidence`** | 200 | ALLOW |
| network (`/mcp/network-twin`) | `network-twin___predict_rsrp` | 200 | ALLOW |
| network (`/mcp/network-twin`) | **`runbook-lookup___lookup`** (×2) | 200 | ALLOW |
| network (`/mcp/network-twin`) | **`customer-records___customer_lookup`** | 200 | ALLOW |

**Why (source, `authz-gateway/app.py`, comment "AR-11"):**
- The platform fronts one shared AgentCore Gateway, which *"exposes EVERY target on EVERY /mcp/<route> listener"*. So the auth gateway evaluates the **called** tool's policy, not the route's. That closes a different hole: a route whose policy has no `toolName` clause would otherwise open every tool.
- Nothing ties a call to the calling agent's declared tools:
  - Every agent presents the same key, so the principal on every decision is `ServiceIdentity::"bootstrap-key"` (#38).
  - The route isn't in the Cedar context: `authorize.build_decide_request` sends `toolName`, `arguments`, `dataClassification`, `traceId`, `actionId`, `toolMethod` and `degraded`.

**Already visible in evidence:** each cross-tool call's `/modaas/evidence` record carries `detail=route_alias=<route>`. In this run, `route_alias=network-twin` is on the `customer-records` record and both `runbook-lookup` records, and `route_alias=runbook-lookup` is on the `evidence-lookup` record.

**Not a one-off:** in the first S1 run (`fault-1791175626-0d34e2`), the network agent's `runbook-lookup` call at 04:47:21 also carries `route_alias=network-twin` (action `286778e0…`, ALLOW).

**Impact:**
- `dependsOn.tools` is a declaration, not a limit. In an ordinary run with no attack, the network agent read customer records.
- The organiser deck lists "unauthorized tool use" as a Rogue-phase condition, yet it already happens in a vanilla run.

**Suggested fix:** enforce `dependsOn.tools` in the decision. Pass the calling agent's identity, or at least the route alias, into the Cedar context and deny tools outside the caller's declaration. Alternatively, restrict each `/mcp/<route>` to its own tool's targets.

**Also, Module 9 explains the `toolName` clause with the pre-AR-11 model (2026-10-05, Module 9 Step 1b):**
- Guide: *"The mcp-tool-template/toolconfig.yaml template includes a Cedar policy with an unless { context has toolName && ![...].contains(context.toolName) } clause. This line restricts the ToolConfig route to only the tools declared in the template. Without it, the route would admit every tool on the shared AgentCore Gateway - not just your declared tools."*
- Since the auth gateway evaluates the **called** tool's policy (AR-11, above), a route admits every approved tool regardless of its own clause. That is what this item's evidence shows: the `network-twin` route admitted `runbook-lookup` and `customer-records` calls.
- Per AR-11, what the clause should limit instead is which of a tool's **own** functions can be called. This is from the source, not observed (compare #53).
- The kit template's own comment makes the same claim (`starter/mcp-tool-template/toolconfig.yaml`, agentCoreGateway variant): *"Without it, this route admits EVERY tool on the shared AgentCore Gateway"*; *"Removing this clause opens your route to foreign tools."* Both texts should describe the clause as limiting a tool's own functions; keeping foreign tools off a route needs the suggested fix above.

## 38. Per-agent identity is set up in Keycloak but not used — Identity gap

**Designed (source and CRDs):**
- The auth gateway accepts a Keycloak JWT and uses its `azp` as the principal, `ServiceIdentity::"<azp>"` (`authz-gateway/keycloak_identity.py`).
- Any other bearer token is the *"API-key bootstrap tier … door-access, not per-party identity"* (`authz-gateway/app.py`), and maps to the one principal `ServiceIdentity::"bootstrap-key"`.
- ModelConfig CRD, `access.allowedConsumers`: *"allowedConsumers entries are principal azp values (agents: modaas-agentconfig-<name>; partners: their odari client id; demo tier: bootstrap-key)"*.
- The organiser deck's enforcement diagram lists "Per-agent identity" (p11).

**Observed (2026-10-05):**
- Keycloak is running (`canvas/canvas-keycloak-0`, plus `identityconfig-operator-keycloak`).
- **18 `IdentityConfig`s exist in `components`, one per agent, model and tool** (4 + 4 + 10; the agent ones are `modaas-agentconfig-customer-experience-agent`, `-it-resolution-agent`, `-network-resolution-agent` and `-hackathon-helper`):
  - all 18 show `identityProvider: Keycloak` and `listenerRegistered: false`
  - the one we inspected in full (`modaas-agentconfig-network-resolution-agent`) holds only `canvasSystemRole` and `componentRole` in its spec
- No secret name in the cluster suggests per-agent client credentials. The Keycloak-related secrets are `canvas-keycloak`, `canvas-keycloak-crt` and `identityconfig-operator-keycloak-secret`.
- Every ModelConfig's `allowedConsumers` is `['bootstrap-key']`, so every projected model policy is `permit(principal == ServiceIdentity::"bootstrap-key", …)`.
- In a three-agent run (trace `e13e7b73…`), all 24 `/modaas/evidence` records (2 models, 4 tools) have principal `ServiceIdentity::"bootstrap-key"`.

**Impact:**
- The platform's records can't say which agent made a call. The auditor question "which identity, on whose behalf, with what scope?" gets the same answer for all three agents. Per-agent attribution comes only from the agents' own, self-reported records (ledger `actor`, spans).
- No Cedar rule or `allowedConsumers` entry can treat one agent differently from another (#37, #39).

**Question for the platform team:** is per-agent identity meant to be live for participants?
- If yes: provision a Keycloak client per AgentConfig (`azp = modaas-agentconfig-<name>`), inject its credentials into the runtime alongside the gateway key, and project `allowedConsumers` from each agent's `dependsOn`.
- If no: say in the guide that this build uses one shared key.

## 39. The per-agent Cedar overlay in AgentConfig is documented but not wired — Doc accuracy (source-based)

**CRD (`crds/agentconfig-v1beta1-crd.yaml`):**
- `spec.access`: *"Authorization overlay for this agent: a restrict-only (forbid) Cedar overlay and the required consumer role. It can narrow what this agent may do below what the target tools permit, never widen it (separation of duties)."* Fields: `requiredRole`, `cedarPolicy`.
- `spec.agentPolicy`: the operator *"projects it into the chosen PDP … The PEP (per-runtime) consults the PDP before each tool call (reserved for future sibling implementations; the in-cluster Cedar reference path is what ships today)."*

**Observed (2026-10-05; source in `modaas-aigateway-src.zip`, and live):**
- **Only two places project Cedar into the PDP:** `aws-tool-operator/tool_operator.py` (ToolConfig `spec.access.cedarPolicy`) and `aws-model-operator/model_operator.py` (ModelConfig `allowedConsumers`).
- The agent operator (`operators/aws-agent-operator`) vendors the shared projection library but never calls it, and no code there reads `spec.access` or `spec.agentPolicy`.
- `pdp/server.py` describes a readback the operator can poll before setting `AgentConfig.status.agentPolicy.pdpReady`, but no operator sets it.
- Each decision evaluates one policy, the called tool's or model's (#33). So even if an agent overlay were projected, nothing in the decision would apply it.
- **Live:**
  - none of the four AgentConfigs sets `spec.access` or has `status.agentPolicy`
  - none of the 15 labelled policy ConfigMaps (10 tools, 4 models, `my-team-policy`) belongs to an agent

**Not tested live:** applying an overlay to an agent and re-running would settle it. That's a cluster write and we haven't done it; a server-side dry run would only prove the field is accepted.

**Impact:** a team that follows the CRD's description writes an overlay that is accepted and enforces nothing, the same failure shape as #33. Per-agent restriction would also need per-agent identity (#38).

**Suggested fix:** either wire the overlay (project `spec.access.cedarPolicy` and evaluate it alongside the called tool's policy when the caller is that agent), or mark the field "not enforced in this build" in the CRD description and the guide.

## 40. Two tools ship without a data classification, so their "restricted" rule can't fire — Configuration gap (kit)

**Observed (2026-10-05):**
- The auth gateway takes a tool's classification from `spec.governance.dataClassification` (`authz-gateway/asset_attributes.py`). When a CR declares none, *"the attribute is simply omitted from the decide"* (`authz-gateway/app.py`).
- Live ToolConfigs:
  - `internal`: `runbook-lookup`, `evidence-lookup`, `cluster-status`, `cr-author`, `demo-crm-lookup`
  - `public`: `aws-knowledge`, `helper-docs`, `modaas-docs`
  - **none: `customer-records` and `network-twin`**
- The kit's own `lambda/customer-records/toolconfig.yaml` and `lambda/network-twin/toolconfig.yaml` declare no classification. Yet both policies end with `unless { resource has dataClassification && resource.dataClassification == "restricted" }`.

**Impact:**
- That clause can never fire for these two tools, so data classification gives no protection on the tool that returns customer records.
- In #37's run, the network agent read customer records with nothing to gate on.

**Suggested fix:** declare a classification on both. The CRD allows `public`, `internal`, `confidential`, `pii`, `regulated` and `restricted`; customer records look like `pii` or `confidential`.

## 41. "One request per second per agent" doesn't keep a team under the ceiling, and the request limit doesn't stop a slow loop — Doc accuracy / control gap

**Guide (Module 6, "The ceiling"):**
- *"It is per account, on the listener itself, so it counts every model call your team makes from any agent, pod, script or the helper. It is not per model and not per agent."*
- *"An agent in a tight loop therefore stops itself after 100 turns in a minute. About one request per second per agent keeps a team well under the line."*
- Live policy `modaas-ceiling`: 100 requests a minute and 2,500,000 tokens an hour (checkpoint `100/min 2500000/h`).

**Observed (2026-10-05):**
- **The arithmetic:** the limit is per account, and Module 7 runs three agents (four with the helper). At one request per second each, three agents make 180 requests a minute, above the 100 limit.
- **The S2 runaway** (`fault-1791177342-d3f892`, 05:15:46–05:20:39 UTC; the gateway pod log and the durable `/aws/modaas/gateway` log agree):
  - The IT agent looped. The run made **174 model calls and 170 tool calls** (137 of them `runbook-lookup`) in under 5 minutes.
  - The peak was **49 model calls in one minute** (05:19), so the request limit never came close.
  - The run used **1,999,001 tokens** (1,992,059 in, 6,942 out; $0.3033), **80% of the hourly token limit**. Context grows every turn: about 11,450 input tokens per call on average.
  - At about 05:25 UTC the account had used 2,139,857 input tokens in the last 60 minutes. Another run like S2 would have hit the limit for the whole team.

**Impact:**
- *"Stops itself after 100 turns in a minute"* holds only for loops faster than 100 model calls a minute. A loop that waits on the model runs slower than that, never trips the request limit, and spends the team's shared token budget instead.
- For a looping agent the binding limit is the hourly token budget, so one runaway can lock the whole team out.
- Not tested: the 429 response itself and *"nothing is charged"*.

**Suggested fix:** state the per-account arithmetic in the guide (e.g. "about one request per second for the whole team"), and say that tokens, not requests, are what a looping agent exhausts.

## 42. The cockpit's cost figures: two different sources in the guide, and per-alias cost isn't possible — Doc accuracy

**Guide:**
- Module 4, capability 8: *"The cockpit's Cost view shows input and output tokens and dollars per model alias, read from CloudWatch's Bedrock token metrics."*
- Module 6, "The ceiling": *"The cockpit's Usage and cost view shows your team's requests and tokens against these two numbers; the gateway access log (/aws/modaas/gateway) carries the token count of every call, which is how that view is computed."*

**Observed (2026-10-05):**
- The cockpit backend (`modaas-ui-src.zip`, `server.py:2259–2606`, "Cost / Spend surface") computes cost from CloudWatch `AWS/Bedrock` `InputTokenCount`/`OutputTokenCount`, and labels the figure *"CloudWatch AWS/Bedrock InputTokenCount/OutputTokenCount (Sum)"*. It doesn't read `/aws/modaas/gateway`.
- `AWS/Bedrock` metrics are per Bedrock model id, and two aliases share one: `nemotron-super-120b` and `nemotron-super-120b-helper` both map to `nvidia.nemotron-super-3-120b`. So "dollars per model alias" can't separate them.
- The usage-against-the-ceiling view was empty when we opened it (no live source; see #29).

**Impact:**
- The guide's two descriptions contradict each other, and the ceiling page names a source the code doesn't use.
- Per-alias or per-run cost has to come from the gateway's per-call lines (`agw.ai.usage.cost.total`), not from the cockpit's Cost view.

**Suggested fix:** pick one source and say which. Computing from the gateway log would give per-alias and per-run figures.

## 43. A policy-engine outage refused an IT tool call; the gateway line and the agent's ledger misreport it — Evidence accuracy

**Observed (2026-10-05, first S1 run `fault-1791175626-0d34e2`, run trace `55b02222…`, 04:47:15 UTC; the IT agent on `/mcp/runbook-lookup`):**
- **Gateway:** `initialize` returned 200 (action `9ad613c2…`, PDP ALLOW). The next POST got **403**, with no action id and no run id on the line.
- **`/modaas/evidence`:** a record at 04:47:15 with `decision=DENY`, `reason=PolicyEngineUnavailable`, asset `runbook-lookup`, action `d9aefa16…`.
  - The auth gateway refused fail-closed, as designed.
  - The PDP log has no entry for it, so the PDP was presumably never reached.
- **IT runtime log** (read earlier the same day, `/aws/bedrock-agentcore/runtimes/it_resolution_agent-15k2B966z2-DEFAULT`): `httpx.HTTPStatusError` 403, with the run trace id.
- **Agent ledger:** *"refused at gateway: http_status=500 model=nemotron-super-120b body=''"*, then *"disposition=refused, no model output"*. Three things are wrong:
  - the status (403 recorded as 500)
  - the asset: no model call was refused in this run; the refusal was on a tool call
  - the reason, which is missing
- **Cause unknown:** the PDP and auth-gateway pods show no restarts, and the auth gateway logged nothing for that second. It didn't recur in our five later runs.

**Impact:** fail-closed worked, and the evidence log recorded why. But:
- joining the gateway log on run id misses the refusal, because refusal lines carry no run id or action id
- the agent's own record sends an auditor looking for a model failure that didn't happen
- a transient platform fault changed the IT agent's outcome (refused), and only `/modaas/evidence` shows it was the platform

**Suggested fix:**
- Stamp the run id and action id on the gateway's refusal lines.
- Have the reference agent record the real status and the gateway's reason.
- Find out what made the policy engine unavailable at 04:47:15.

## 44. The S2 runaway is invisible in the ledger — Evidence gap

**Observed (2026-10-05, S2 run `fault-1791177342-d3f892`):**
- **Gateway (pod log and durable `/aws/modaas/gateway`):** 174 model calls and 170 tool calls in under five minutes, 1,999,001 tokens, $0.3033 (#41).
- **Ledger:** 16 records. Customer and network have four each. The IT agent has eight:
  - two `INTENT` records three minutes apart (05:16:01 and 05:19:01, with different trace ids, so two invocations)
  - then two sets of tool-invocation, invocation and result records (05:20:24 and 05:20:39)
- The second set lands after the network agent had finished (05:20:35), and the gateway shows model calls until 05:20:39. So an IT invocation was still running and spending after the run had moved on.
- Each tool-invocation record names one `runbook-lookup` call, and the first one's result summary is garbled text.
- None of the 16 records carries a token count, a call count or a duration (#20).

**Impact:**
- An auditor reading the ledger sees an IT agent that made one tool call and one model call per invocation. The 174 model calls and 2.0M tokens exist only in the gateway records.
- Any spend control, and any answer to "what did it touch?", has to rest on the gateway lines, not the ledger.

**Suggested fix:** have the reference agent write one record per model and tool call, or at least a per-invocation count and token total, and mark when an invocation ends.

## 45. The self-check checkpoint grades every run as S1 — Bug (guide)

**Guide (Module 7, "Self-check: three faults"):**
- Checkpoint: `python3 /tmp/score-run.py "$CID" S1-fronthaul-degradation /tmp/chain.txt 2>/dev/null; echo "exit=$?"`
- *"It prints exit=0 for S1 or S3, and exit=1 for S2."*

**Observed (2026-10-05):** the scenario name is fixed, so whichever run was last is graded against S1's expectation (`auto-resolve`). Both our S3 chains, graded locally:

| S3 run | Graded as S3 | Graded as S1 (the checkpoint) |
|---|---|---|
| `fault-1791177636-8fa0bd` | FAIL 8/10, exit=1 | FAIL 5/8, exit=1 |
| `fault-1791177926-b0ce69` | FAIL 8/10, exit=1 | FAIL 5/8, exit=1 |

A correct S3 run escalates, and S1's disposition check rejects an escalation. So the checkpoint can't print `exit=0` for S3 even with a perfect agent, independently of #19.

**Suggested fix:** grade against the scenario that was actually run (pass it as a variable), or give one checkpoint per scenario.

## 46. Swapping an approved agent's model needs no re-review, and "re-attest" adds no approval record — Governance gap

**Guide (Module 7, "Swap the model, the governed way"):**
- *"Here the agent only knows a model alias; the platform maps the alias to a real model behind the gateway. You change the mapping, the agent code stays untouched, and the cost line in the records moves."*
- Step 2 patches the AgentConfig: `spec.dependsOn.models[0]` and `spec.modelRef` → `nemotron-nano-9b`.
- Step 4, "Re-attest the agent", sets the annotation `modaas.tmforum.org/approval-attestation="Reviewed: model changed to nemotron-nano-9b for cost comparison"`. *"Expected result: annotated."*

**Observed (2026-10-05, 05:47–05:49 UTC, `it-resolution-agent`):**
- The patch moved generation 1 → 2, and the runtime was updated within 24 s. The phase stayed `Approved` throughout; the agent never went back to review.
- After step 4 the annotation carries the new text, but `status.governance.approvals` still holds **one** record, and `registryApprovalStatus` is still `APPROVED`. The record: `{at: 04:37:25, attestation: "Reviewed: reference agent on AgentCore", subject: satyabratsrikumar@team, role: modaas-agentconfig-it-resolution-agent-admin, signature: ""}`.
- The step changes which alias the agent declares (its own spec), not the model behind an alias. Both ModelConfigs are unchanged.

**Impact:**
- The auditor question "attestation for every asset in the chain?" gets an attestation that predates the change it should cover.
- The "re-attest" step looks like an approval but leaves no approval record.
- Any approved agent can be re-pointed at another approved model without review. We tested only the model dependency.

**Suggested fix:** send an AgentConfig back to review when a governed field such as its model dependency changes, or record the attestation annotation as an approval tied to the generation it covers.

**Also for images, by the guide's own account (2026-10-05, Module 9 Step 2, "What the script did"):**
- *"An image change is not re-reviewed — Measured 2026-09-29: re-applying my-agent with a new image kept it Approved, and the operator rolled the runtime to the new image without a new attestation."*
- That is the guide's own measurement; we haven't tested it. If it holds, an approved agent's code, like its model dependency, can change without re-review.

## 47. The swap page's compare grep matches nothing — Doc accuracy (minor)

**Guide (Module 7, "Swap the model", step 3):** `kubectl -n agentgateway-system logs deploy/modaas-agw --tail=200 | grep 'listener=llm' | grep "it.resolution" | tail -2`. *"Expected result: the earlier run shows gen_ai.request.model=nvidia.nemotron-super-3-120b; the new run shows nvidia.nemotron-nano-9b-v2 with different token counts."*

**Observed (2026-10-05):** none of the 315 `listener=llm` lines from the last 24 hours contain `it.resolution`. Gateway lines carry no agent name or identity (#38).

**Working alternative:** filter on the run id (`modaas.run_id="$CID"`) and read `gen_ai.request.model` and the token fields from those lines.

## 48. All four agent runtimes share one IAM role — Identity gap

**Deck ("The AWS Services Behind It", p13):** *"AgentCore Runtime — Hosts agent containers, each with its own IAM role."*

**Observed (2026-10-05, `bedrock-agentcore-control get-agent-runtime` and IAM, read-only):**
- `customer_experience_agent`, `it_resolution_agent`, `network_resolution_agent` and `hackathon_helper` all run as **`a-01-eks-cluster-agentcore-runtime`**.
- Its inline policy `agentcore-runtime`:
  - **allows:** ECR image pull; logs to `/aws/bedrock-agentcore/*`; X-Ray and `cloudwatch:PutMetricData`; workload-identity tokens; and `bedrock-agentcore:InvokeAgentRuntime` on every runtime in the account (`runtime/*`)
  - **explicitly denies** (`NoDirectModelOrToolAccess`): `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` and `bedrock-agentcore:InvokeGateway`, on `*`

**What this confirms:** an agent can't call a model directly (the Converse API is authorised through `InvokeModel`), or the AgentCore Gateway. So the gateway really is the only path to a model, which the Module 8 trust table relies on.

**Impact:**
- Nothing on the AWS side tells the agents apart: CloudTrail sees one role for all four. With the shared gateway key (#38), no layer identifies an agent except the agents' own records.
- Any agent's role may invoke any other runtime directly. Whether the runtimes' resource policies block that is **untested**.

**Suggested fix:** one execution role per AgentConfig, with `InvokeAgentRuntime` limited to declared peers. Otherwise, correct the deck.

## 49. The deployed agents' spans don't match the guide, so the span helper doubles the totals — Doc drift / Bug (kit)

**Guide (Module 8, "Trace a run through its spans"):**
- *"Eight spans from three agents"*: one `invoke_agent <agent>` SERVER span per agent, and one `chat nemotron-nano-9b` CLIENT span per model call carrying `modaas.action_id`, plus a `negotiate` span.
- Checkpoint (both Module 8 pages): `show-run-spans.py`'s totals *"equal the sum of the gateway's lines for the same trace."*

**Observed (2026-10-05, model-swap S1 run, trace `e13e7b73…`):**
- **48 Strands-native spans:** `POST /invocations`, `invoke_agent Strands Agents`, `execute_event_loop_cycle`, `chat`, `execute_tool …`, `mcp tools/call …`, and HTTP client spans.
- No span carries `modaas.action_id`, and there is no `negotiate` span (agents never negotiate, #19).
- **The per-call `chat` spans match the gateway exactly:** 9 of 9 calls, e.g. 3,812/51 and 3,901/243 tokens.
- **But each agent's `invoke_agent Strands Agents` span carries the sum of its `chat` spans.** `show-run-spans.py` adds every span with token counts, so it prints `model calls: 12 … total: 75,328`, exactly twice the gateway's 9 calls and 37,664 tokens.

**Impact:**
- Both Module 8 checkpoints fail with the shipped agents.
- A team that trusts the helper's totals for a spend or token control (e.g. control 16) would double-count.

**Suggested fix:** count only `chat` spans in `show-run-spans.py` (or skip spans that have children), and update the guide's sample output to the Strands span shape.

## 50. Module 9 describes the helper and modaas-docs as in a different build — Doc drift

**Guide:**
- Module 9 overview: *"The modaas-docs tool is a Gateway Lambda tool: a Lambda target registered on the account's AgentCore Gateway and governed as a ToolConfig with provider agentCoreGateway."*
- Step 1: *"spec.provider: awsAgentCore, dependsOn.models: [nemotron-super-120b], and dependsOn.tools listing modaas-docs, aws-knowledge and cluster-status"*, and *"modaas-docs, aws-knowledge and cluster-status all show Approved with provider agentCoreGateway."*

**Observed (2026-10-05):**
- `hackathon-helper`: provider `awsAgentCore` as expected, but `dependsOn.models: [nemotron-super-120b-helper]` and tools `helper-docs`, `aws-knowledge`, `cluster-status`, `cr-author`, `evidence-lookup`.
- ToolConfig `modaas-docs` is `provider: custom`, backed by the in-cluster MCP server `http://modaas-docs-mcp.components.svc.cluster.local:8080`. The kit ships both versions: `crs/modaas-docs-toolconfig.yaml` (custom) and `lambda/modaas-docs/toolconfig.yaml` (agentCoreGateway).
- The Lambda-backed docs tool the guide describes exists as ToolConfig **`helper-docs`** (`agentCoreGateway`, Lambda `team-a61f5-modaas-docs`).

**Impact:**
- A team following Module 9 looks for a Lambda `modaas-docs` that isn't there, and Step 1's expected output doesn't match.
- Step 1b's `new-agent.sh … --tool modaas-docs` wires a new agent to the in-cluster server, not to a Gateway Lambda tool.

**Suggested fix:** update Module 9 to the current names, or make `modaas-docs` the Lambda tool the text describes.

## 51. The helper's own evidence is thin — Evidence gap

**Guide (Module 9):**
- Overview: *"its model call goes through the gateway, its tool calls go through the gateway's tool endpoint, Cedar decides each one, and every call lands in the records."*
- Step 1: *"Expected result: 3 records (intent, invocation, result-inspection) under your $CID."*

**Observed (2026-10-05):** four questions to `hackathon-helper`, one from the cockpit Help panel and three via `ask-agent.sh`.

| Question (CID) | Ledger records | Model calls | Tool calls | Tool decisions (PDP) |
|---|---|---|---|---|
| "How does a ModelConfig get approved?" (cockpit, `…1791189048-a9c9fc`) | 2 (INTENT, INVOCATION) | 1 | none | 15 ALLOW |
| Same question (CLI, `…1791189091-2633eb`) | 2 | 1 | none | 15 ALLOW |
| price-check ToolConfig (`…1791189097-cdcf50`) | 2 | 2 | `cr-author___scaffold_cr` | 16 ALLOW |
| Update it-resolution-agent (`…1791189106-6525ac`) | 2 | 13 | 10 (`patch_cr` ×5, `scaffold_cr`, `list_resources` ×2, `search_docs` ×2) | 25 ALLOW |

- **No result-inspection record,** so every run's disposition reads "unknown" (`ask-agent.sh` prints `disposition: unknown`).
- **Both "approved?" answers cite `[Source: helper-docs]` with no tool call in the run.** Each was a single model call (~6,200 tokens).
- **Each run opens MCP sessions with all five declared tools** (`initialize`, the initialized notification and `tools/list`), and Cedar decides each one. That is 15 ALLOW decisions even when no tool is called.

**Impact:**
- An auditor can't find the helper's disposition, and can't back its citations with a tool call.
- Counting "what did it touch" from the decision log overcounts: 15 tool decisions, 0 tool calls. Only the `tools/call` lines show actual use.

**Suggested fix:** have the helper write a result-inspection record, and cite a source only when a tool returned it. Mark session-setup decisions differently from `tools/call` decisions in the evidence record.

## 52. The helper's drafts don't apply, and it says they did — Doc accuracy / kit

**Guide (Step 1, section 5):**
- *"Expected result: YAML for a ToolConfig with provider agentCoreGateway and the kubectl apply command."*
- *"Expected result: a kubectl patch command that changes dependsOn.models and modelRef, plus the re-attestation command. The helper writes, you apply, an approver approves."*

**Observed (2026-10-05):** both drafts were tested with server-side dry runs; nothing was created or changed.
- **price-check ToolConfig** (`cr-author___scaffold_cr`) is rejected: *"strict decoding error: unknown field "spec.alias""*. It also has no Lambda target (`agentCoreGateway.mcpServer`) and no `access.cedarPolicy`, so it couldn't serve even without that field.
- **The it-resolution-agent patch** (`cr-author___patch_cr`) begins with `{"op":"test","path":"/spec/dependsOn/models/0","value":"nemotron-super-120b"}`.
  - The agent has been on `nemotron-nano-9b` since the Module 7 swap, so the server rejects the patch.
  - The helper had called `cluster-status___list_resources` twice in the same run, yet copied the guide's procedure (*"Now I have the exact command from the documentation"*).
  - It ended with *"The agent will now use the nemotron-nano-9b model"*.
- That one request took 13 model calls and 123,476 tokens.
- `patch_cr` only returns text (*"returns updated YAML plus the kubectl patch, wait, and approval commands"*). No governed resource changed; checked with managed fields.

**Impact:** the helper's drafts need a `--dry-run=server` before anyone applies them, and its statements that a change was made can't be trusted.

**Suggested fix:**
- Drop `spec.alias` from the scaffold, or add it to the CRD.
- Have `patch_cr` read the live value for `test` ops.
- Stop the helper from describing a change as done.

## 53. helper-docs' Cedar allow-list may deny `get_doc` — To verify

**Observed (2026-10-05):**
- ToolConfig `helper-docs` (`agentCoreGateway`) has the allow-list `["helper-docs___search_docs", "get_doc"]`.
- Calls through the shared AgentCore Gateway carry the target prefix: the gateway logged `helper-docs___search_docs` ×30 in 24 hours.
- A `get_doc` call would arrive as `helper-docs___get_doc`. That isn't on the list, so Cedar would deny it.
- The other Gateway tools' lists are all prefixed (`cluster-status___list_resources`, `cr-author___patch_cr` …). `modaas-docs`, a custom server, is consistently unprefixed.

**Not yet seen:** no `get_doc` call in the last 24 hours, so no DENY has been observed. A question that makes the helper fetch a whole document would settle it.

**Suggested fix (if confirmed):** list `"helper-docs___get_doc"`.

## 54. Module 9 Step 2's claims vs the kit — Doc accuracy

**Guide (Module 9 Step 2, "What the script did"):**
- *"Read the file: provider: awsAgentCore, dependsOn.models: [nemotron-nano-9b], and a safety block stating that the agent's only model path is the guardrail-enforced gateway. Delete the safety block and apply it to watch admission refuse it with EnforcementNotDeclared."*
- *"Use EXTRA_PIP for additional packages your agent needs - never for the SDK packages the script already pins."*

**Observed (2026-10-05):**
- **Admission accepts an agent without the safety block.** With `spec.safety` removed, the generated my-agent declaration passed `kubectl apply --dry-run=server` (*"created (server dry run)"*): a create at 08:57 UTC, before my-agent existed. Nothing was stored. An update without the block should also pass (the admission policy checks only namespaces and kinds), but that wasn't tested.
  - Nothing at admission raises `EnforcementNotDeclared`. The live AgentConfig CRD's CEL rules on `safety` only constrain the block when it's present (e.g. `enforces=true` needs an `enforcerKind` and `governance.approval.required=true`); none requires the block. Neither the live CRD nor the cluster's only ValidatingAdmissionPolicy (`modaas-governance-guardrail`) mentions `EnforcementNotDeclared`. The reason is set by the operators' composition check (`operators/shared/composition/checks.py` in `modaas-aigateway-src.zip`).
  - The CRD source says so itself, in a comment in `crds/agentconfig-v1beta1-crd.yaml`: *"Cross-CR composition predicates cannot be evaluated at admission CEL … the operator writes phase=Failed with reason=EnforcementNotDeclared / EnforcerKindMismatch … The candidate is admitted to the cluster but never reaches phase=Approved and never serves traffic."*
  - `nemotron-super-120b` declares `safety.required=true`, so the operator should mark such an agent `Failed` after storage. We haven't tested that; it needs a real apply.
- **The script breaks the EXTRA_PIP rule.** `starter/new-agent.sh:152` passes the SDK packages themselves: `EXTRA_PIP='strands-agents[openai]==1.57.2 bedrock-agentcore==1.24.0 mcp==1.30.0 aws-opentelemetry-distro==0.21.0'`.
  - They're the same versions `reference-impl/build-agent-image.sh:97` already pins, so it's harmless today.
  - Both lists go into one `pip install`, so if one is bumped without the other, the pins would conflict.

**Impact:** a participant who follows the page sees the server accept the agent, not refuse it, and the page doesn't say where the refusal actually appears. The EXTRA_PIP point is minor.

**Suggested fix:**
- Describe the real behaviour: the agent is admitted, and the operator sets phase `Failed` with `EnforcementNotDeclared` (a real apply, deleted afterwards). Or show the dry run being accepted and explain why.
- Drop the SDK pins from `new-agent.sh`'s `EXTRA_PIP`, or relax the rule on the page.

## 55. `new-agent.sh --tool` doesn't declare the tool — Governance gap

**Where:** Module 9 Step 1b ("Build your own agent"), `starter/new-agent.sh`

**Observed (2026-10-05, 08:58 UTC):**
- `new-agent.sh my-agent nemotron-super-120b --skills knowledge-base --tool modaas-docs` added only two environment variables for the tool, `TOOL_MCP_URL` and `TOOL_MCP_ALIAS` (`patch_tool_env`).
- The stored AgentConfig declares no tool: `kubectl get agentconfig my-agent -n components -o jsonpath='{.spec.dependsOn}'` → `{"models":["nemotron-super-120b"]}`. The other four AgentConfigs list their tools in `dependsOn.tools`.
- The agent then called `modaas-docs`: `search_docs` and `get_doc` ×2, all ALLOW (CID `my-agent-1791190861-638235`).
- The script's own pre-check assumes the tool will be a dependency: it refuses an unapproved ToolConfig because the *"composition gate refuses an agent depending on an unapproved tool"* (`new-agent.sh:91`). With no declaration, that gate never sees the tool.

**Impact:**
- Neither the governance contract (`dependsOn`) nor the AWS Agent Registry record (`awsagentcore_my-agent`) names the tool the agent uses.
- With #37 (any route admits every approved tool, and every agent is the same principal), nothing ties the agent to its tool.

**Suggested fix:** have `--tool` add the alias to `dependsOn.tools` as well as setting the environment variables.

## 56. Module 9 Step 3's expected results don't match the kit — Doc drift

**Guide (Module 9 Step 3, "Prove the governance"):**
- *"Expected result: the agent answers with disposition: blocked by guardrail and answer: Input blocked by policy."*
- *"Pause the ModelConfig, ask again, and unpause it in the same block (every agent in your account depends on this model):"*, followed by `kubectl patch modelconfig nemotron-nano-9b …`.

**Observed (2026-10-05, 09:12–09:14 UTC):**
- **Disposition:** the prompt attack (CID `my-agent-1791191546-6aa5dd`) got the answer *"Input blocked by policy."* and 0 tokens, but `disposition: undetermined`.
  - The template's `classify_disposition()` (`starter/agent-template/agent.py:94-110`) is a keyword match on the answer text: escalation words → `escalate`; uncertainty words → `gather-evidence`; `resolv`, `apply`, `execut`, `repair` … → `auto-resolve`; anything else → `undetermined`.
  - Nothing in the template or `ask_agent.py` produces "blocked by guardrail". The page's wording matches `reference-impl/strands-agent-agentcore.py:79` (`disposition = "blocked by guardrail" if answer.endswith("blocked by policy.") else "answered"`), but `new-agent.sh` copies `starter/agent-template/agent.py` (`:78`), and no kit script references that file.
  - Related: the same classifier labelled a documentation answer `auto-resolve` (CID `my-agent-1791190861-638235`) because it contained *"After applying the ModelConfig CR"*.
- **Which model to pause:** Step 1b builds my-agent on `nemotron-super-120b` (`bash ~/starter/new-agent.sh my-agent nemotron-super-120b …`). Step 2's "Read the file" line says `dependsOn.models: [nemotron-nano-9b]` (#54), but the live AgentConfig has `[nemotron-super-120b]`.
  - Live, only `it-resolution-agent` depends on `nemotron-nano-9b`. `customer-experience-agent`, `network-resolution-agent` and `my-agent` are on `nemotron-super-120b`, and `hackathon-helper` on `nemotron-super-120b-helper`.
  - So pausing nano-9b, as the page says, doesn't affect my-agent, and *"every agent in your account depends on this model"* is false here. We ran the probe against super-120b instead (#36).

**Impact:** a participant who follows the page gets a different disposition than promised. Its kill-switch step pauses a model their agent doesn't use, so the agent keeps answering and the kill switch looks broken.

**Suggested fix:**
- Expect `disposition: undetermined`, or give the template a guardrail branch like `strands-agent-agentcore.py`'s.
- Pause the model the agent was built on, read from its AgentConfig: `kubectl get agentconfig my-agent -n components -o jsonpath='{.spec.dependsOn.models[0]}'`.

## Running from outside the IDE (FYI)

The guide assumes the browser IDE throughout. With only the Workshop Studio "Get AWS CLI credentials" keys, a participant can:

- run `aws eks update-kubeconfig` and get full participant kubectl access (the role maps to `modaas:participants`, the same group the IDE ends up in after bootstrap step 18)
- read the workshop asset bucket (scripts, starter kit, reference implementation)
- run the starter kit locally, after sourcing `scripts/rehydrate.sh` with `KUBECONFIG` set first. Otherwise `rehydrate.sh` writes into `~/.kube/config`

**The participant keys can search logs, the IDE role can't (checked 2026-10-05).** Module 8 says *"your roles can read a log stream but not search one."* That holds for the IDE role: `a-02-code-editor-IdeInstanceRole-…`'s inline policy `ide-workshop` allows `logs:GetLogEvents`, `DescribeLogStreams` and `DescribeLogGroups`, but not `FilterLogEvents`. The Workshop Studio participant role (`WSParticipantRole`) can run `logs filter-log-events`; we used it throughout. So evidence tooling written for the IDE has to read streams one by one, while tooling run with the participant keys can search.

**A kit synced from S3 loses file modes.** After `aws s3 sync`, `starter/ask-agent.sh` isn't executable: `ask-agent.sh …` fails with *Permission denied* until it's run as `bash ask-agent.sh …` (or after `chmod +x`). Module 9's download lists (Step 1 and Step 1b) don't include `ask-agent.sh` or `ask_agent.py`, although both pages use `ask-agent.sh`. On the IDE they presumably come from bootstrap (not checked).

Things that only exist on the IDE: `~/.modaas-bootstrap/status` and the `/etc/profile.d/modaas-team.sh` variables (`TEAM`, `MODAAS_GATEWAY_ID`). Both can be derived from the `workshop-identity` and `modaas-gateway` ConfigMaps in `modaas-system`.

Whether this is intended (it's useful for participants) or an unintended path around the IDE is a question for the platform team.

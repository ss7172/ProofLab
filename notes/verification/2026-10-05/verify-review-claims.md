> Note (2026-10-05): vh.py is not included in the repo because its ac/gw modes could print secrets; see verify-live.md for the safe queries and the live results.
# Independent verification of reviewer claims C1-C8 (2026-10-05)

## LIVE CHECKS BLOCKED: AWS credentials expired

- `aws sts get-caller-identity` (profile `hackathon`, the only profile) returned `ExpiredToken`. `kubectl` returned `You must be logged in to the server (Unauthorized)`. `~/.aws/credentials` was last written Oct 5 01:20 local time.
- So nothing here was checked against the live cluster or account today: no CloudWatch, X-Ray, CRD, AgentConfig or get-agent-runtime reads. Every verdict below has two tiers:
  - **SOURCE**: kit and installer code, the workshop KB (`workshop-static/kb/index.json`), and the local evidence snapshot `workshop-local/evidence-snapshots/20261005T173727Z/`, which is raw pod-log and ledger data.
  - **LIVE**: blocked. Source evidence never upgrades a live-measurement claim to CONFIRMED.
- A ready-made re-run script is at `scratchpad/res/vh.py`. It is read-only and prints names, lengths, counts and booleans only. It reads k8s secrets in memory to compare values but never prints them. Once credentials are refreshed, three calls finish the live tier:
  - `bash -c 'source /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; python3 /private/tmp/claude-501/-/ca14fa49-a079-47de-a9fb-a38b37dcff99/scratchpad/res/vh.py ac'` covers C3, C4 (live runtime name), C7 and C8 (live token count).
  - the same command with `gw` covers C2: live policies, collector ConfigMap, and the attribute names in `/aws/modaas/gateway`.
  - the same command with `spans` covers C1: `aws/spans` retention, span count and token sum per run, and X-Ray.
- Already done (local, complete): C4, C5, C6, and the source halves of C1, C2, C3, C7 and C8.

## Summary

| Claim | SOURCE | LIVE | Verdict to use now |
|---|---|---|---|
| C1 spans durable, carry run id, token sum matches | plausible, but the kit contradicts itself | blocked | **UNVERIFIED** |
| C2 run/action ids only on spans, not on the OTLP log copy, by design | policy part right; "by design" contradicted | blocked | **PARTLY** |
| C3 gateway key not in specs; operator injects it | supported, but one workshop page contradicts it | blocked | **SOURCE-SUPPORTED, LIVE-UNVERIFIED** |
| C4 generator validates names | confirmed | runtime-name derivation blocked | **CONFIRMED** (derivation comes from a code comment) |
| C5 brief: AgentCore (Strands) or ServiceNow | confirmed | n/a | **CONFIRMED** ("only" is an inference) |
| C6 kill-switch 404 has trace.id, no run/action id | confirmed | n/a (snapshot) | **CONFIRMED** |
| C7 runtime model from dependsOn.models[0]; CEL rule on modelRef | confirmed by KB CRD copy and workshop text | blocked | **SOURCE-CONFIRMED** ("ignores modelRef" is inferred) |
| C8 Evidence Pack leaks the ledger token | confirmed | count blocked | **CONFIRMED (source)**, with corrections |

---

## C1. Gateway spans are durable, carry the run id, and token sums match

**Verdict: UNVERIFIED (live blocked).** The installer source makes it plausible. The workshop's own content contradicts it. The reviewer's numbers equal the gateway stdout figures exactly, so they prove nothing about a separate span store.

**What the installer source supports:**
- `workshop-static/scripts/bootstrap-platform.sh` step 11, lines 557-651 (collector config):
  ```
  traces:     receivers: [otlp]  processors: [attributes/scrub-payloads, batch]  exporters: [awsxray]
  ```
- The scrub processor deletes only `gen_ai.prompt`, `gen_ai.completion`, `gen_ai.input.messages`, `gen_ai.output.messages` and `modaas.request.body`.
- Policy `agentgateway-system/modaas-telemetry-export` (bootstrap lines 655-689) sets `frontend.tracing` with `randomSampling: "true"` and resource `service.name = "modaas-agw"`, plus:
  ```
  attributes.add:
    - name: modaas.run_id     expression: 'extauthz.correlationId'
    - name: modaas.action_id  expression: 'extauthz.actionId'
  ```
- `workshop-static/cfn/01-eks-cluster.yaml` lines 1129-1158:
  - `AWS::Logs::ResourcePolicy` lets `xray.amazonaws.com` call `logs:PutLogEvents` on `log-group:aws/spans:*`.
  - `AWS::XRay::TransactionSearchConfig` sets `IndexingPercentage: 100`.
  - **No log-group resource or retention is set for `aws/spans`.** The only retentions set are `/modaas/evidence` 30 days (lines 1057-1058) and `/aws/modaas/gateway` 7 days (lines 1068-1069).

**What contradicts it in source:**
- KB `workshop/content/agent-observability/trace-spans.en.md#01`: "Spans land in each runtime's own log group, `/aws/bedrock-agentcore/runtimes/<runtime id>-DEFAULT`, stream `spans`. The account-wide `aws/spans` group stays empty."
  - That page covers the agents' ADOT spans: `invoke_agent` plus `chat <model>` spans carrying `gen_ai.usage.*` and `modaas.action_id`, joined by trace id. It never mentions `modaas.run_id` on spans.
  - `reference-impl/show-run-spans.py` says the same: the spans are "not in the account-wide aws/spans group".
- `starter/pull-evidence.sh` lines 175-177: "This workshop's collector exports spans to `debug` only (Module 8), so there is no X-Ray trace to fetch". That contradicts bootstrap step 11. **The kit contradicts itself.**

**My own count from the snapshot gateway stdout** (`gateway-modaas-agw-88dc46ff4-jfcdx.log`, 1,895 lines, covering 10-04T10:35Z to 10-05T17:33Z):

| run | lines with the run id | llm lines | other lines | tokens (in+out) on llm lines |
|---|---|---|---|---|
| S2 fault-1791177342-d3f892 | **353** | **174** | 179 (MCP) | **1,999,001** |
| S1 fault-1791179282-8ef1a8 | 24 | 9 | 15 | 37,664 |
| S1 fault-1791177843-fde682 | 30 | 12 | 18 | 50,246 |
| S3 fault-1791177926-b0ce69 | 24 | 9 | 15 | 37,799 |

- S2 has 1 distinct `trace.id` and 353 distinct `modaas.action_id` values.
- So the reviewer's "~353 spans / 1,999,001" is exactly the gateway's stdout request count and figure of record. That fits one gateway span per request, but it does not show that those spans exist in `aws/spans`.
- Not every request carries a run id. The kill-switch 404 (see C6) has no `modaas.*` fields, because the run id exists only where ext-authz filled in `correlationId`.

**Statement to use:**
- By installer design (bootstrap step 11 plus CFN Transaction Search), the gateway should export one span per request to X-Ray and from there to `aws/spans`. Each span should carry `modaas.run_id` (= `extauthz.correlationId`) and `modaas.action_id` (= `extauthz.actionId`). The collector scrubs only prompt, completion and body attributes.
- **Not verified live:**
  - whether `aws/spans` actually holds these spans. The workshop's trace-spans page says it "stays empty", and pull-evidence.sh says spans go to `debug` only.
  - its retention (CFN sets none).
  - the per-run token sum.
- If it works, S2 should show 353 gateway spans (174 model + 179 MCP), with 1,999,001 tokens on the 174 model spans: the same as the stdout figure of record.
- Correction to the claim's wording: on gateway spans, `modaas.run_id` comes from `extauthz.correlationId` (the authz response), not from W3C baggage. That is why requests rejected before ext-authz (for example, the kill-switch 404) carry no run id.
- Agent spans are a separate store (the per-runtime log group, stream `spans`), joined by trace id. The workshop page lists `modaas.action_id` on them; `modaas.run_id` is not mentioned.
- "Durable" means `aws/spans` retention (not yet known), and in any case no longer than the event account lives.

## C2. Run/action ids go on trace spans only; the OTLP log copy lacks them "by design"

**Verdict: PARTLY (source). Live unverified.**

**Right:**
- `modaas-telemetry-export` adds `modaas.run_id`/`modaas.action_id` only under `frontend.tracing.attributes.add`. Its access-log block is just:
  ```
  accessLog:
    otlp:
      backendRef: {name: opentelemetry-collector, namespace: modaas-system, port: 4317}
      protocol: GRPC
  ```
  It adds no attributes.
- The installer's collector `logs/gateway` pipeline is `[otlp] -> [attributes/scrub-payloads, filter/not-evidence, batch] -> awscloudwatchlogs/gateway`, writing to `/aws/modaas/gateway` with 7-day retention.
  - The scrub deletes only the 5 payload keys listed under C1.
  - `filter/not-evidence` drops records that have `modaas.evidence.schema_version`.
  - **Nothing removes `modaas.run_id`/`modaas.action_id`, so "the collector drops them" is wrong as far as the source shows.**

**Wrong or unsupported: "by design".**
- The installer's own comment, just above the policy (bootstrap ~line 652): "Access log: OTLP export of **the same per-call line the shipped modaas-access-log policy shapes**." The intent was parity with stdout.
- The `modaas.*` fields on stdout come from a separate shipped policy, `modaas-access-log`. The KB captured 2026-09-29 lists 4 policies: `modaas-access-log` (whole gateway), `modaas-authz`, `modaas-llm-auth` (llm, llm-tls) and `modaas-mcp-ratelimit` (http). Its spec is not in the kit or the KB.

**Statement to use:**
- The telemetry-export policy adds run/action ids to spans only. Its OTLP access-log export adds nothing of its own.
- Per the installer config, the collector does not strip them.
- The OTLP copy in `/aws/modaas/gateway` was **meant** to be the same line as stdout. If it lacks `modaas.run_id`/`modaas.action_id` (seen earlier per team memory, not re-checked live today), that is an unintended gap with an unknown cause: two policies setting `frontend.accessLog` on one Gateway and merging, or the OTLP export not carrying the other policy's added fields. It is not a design choice.
- The live collector ConfigMap, the live policy objects, and the live record shape are unverified (`vh.py gw`).

## C3. The gateway key is not in AgentConfig specs; the operator injects it

**Verdict: SOURCE-SUPPORTED, LIVE-UNVERIFIED. One workshop page contradicts it.**

- **Generator** `reference-impl/make-agentcore-agents.py` `_agent_cr` (~lines 230-237) sets env `AGENT_ROLE`, `AGENT_NAME`, `STEP_BASE`, `AUDIT_URL` and `AUDIT_WRITE_TOKEN`.
  - `AUDIT_WRITE_TOKEN` comes from `audit_token()`, the base64-decoded `Secret audit-write-token .data.token` (lines 200-204).
  - It also adds `TOOL_MCP_ALIAS` and env_extra (`TEAM`, `IT_AGENT_RUNTIME_ARN`). `new-agent.sh` patches in `TOOL_MCP_URL`.
  - **No gateway key.**
- **Reference agent** `reference-impl/reference-agent/agent.py` reads `OPENAI_BASE_URL` (l.84), `OPENAI_API_KEY` (l.85, and l.111 as `Authorization: Bearer`), `MODEL_ALIAS` (l.25) and `AGENTCORE_GATEWAY_MCP_URL` (l.30). The generator writes none of these.
- **KB** `build-your-own-agent/what-the-script-did.en.md#01`: "the operator sets `OPENAI_BASE_URL`, `OPENAI_API_KEY` and `MODEL_ALIAS` on the runtime".
- **Contradiction**, KB `resources/index.en.md#11`: "`api_key` is the `GATEWAY_API_KEY` your AgentConfig already mounts from `agw-apikeys` in Module 9".
- The tests' operator-owned `RESERVED` list (tests lines 21-27) does **not** include `OPENAI_API_KEY`/`OPENAI_BASE_URL`. It lists REGION, REGISTRY_ID, MODEL_ALIAS, TOOL_ALIAS, AGENTCORE_GATEWAY_MCP_URL and cloud credentials.
- The gateway key is `Secret agentgateway-system/agw-apikeys` (KB `platform-access/gateway-credential.en.md#02`).
- Live: `vh.py ac` was Unauthorized. It would list spec env NAMES and runtime env NAMES, and check by in-memory value comparison whether the `agw-apikeys` value appears in any CR or runtime env.

**Statement to use:**
- Per kit source, the generator never writes the gateway key into an AgentConfig. The only credential it writes, as a literal, is `AUDIT_WRITE_TOKEN`.
- The workshop content says the operator sets `OPENAI_API_KEY` (plus `OPENAI_BASE_URL` and `MODEL_ALIAS`) on the AgentCore runtime, and agents present it as the Bearer token to the gateway.
- Not verified live. Before writing "only the ledger token is in specs", check the live specs for a `GATEWAY_API_KEY` entry (one page says Module 9 mounts it from `agw-apikeys`).

## C4. Agent names are validated by the generator that new-agent.sh calls

**Verdict: CONFIRMED (source).** The runtime-name derivation is stated in a code comment only. The operator source is not available locally, and the live `agentRuntimeName` check is blocked.

- `make-agentcore-agents.py` lines 75-78:
  ```python
  # A Kubernetes name (DNS-1123 label) that also becomes a valid AgentCore
  # runtime name once "-" turns into "_": must start with a letter; the operator
  # keeps 40 characters of it.
  NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,38}[a-z0-9]$")
  ```
- Lines 287-289, in `own_agent()`:
  ```python
  if not NAME_RE.match(name or ""):
      raise InputError(f"name {name!r}: use 2-40 lowercase letters, digits and '-', starting with a "
                       f"letter (it becomes the runtime name)")
  ```
- What it enforces:
  - 2-40 characters.
  - Lowercase a-z, digits and `-` only. **Underscores are rejected**, and so is uppercase.
  - Must start with a letter and end with a letter or digit.
  - Consecutive hyphens are allowed.
- Only `own_agent()` applies the check. Reference and helper agents use fixed names.
- `new-agent.sh` calls the generator at line 159 (real run) and line 134 (`--dry-run`). In a real run the check fires at **step 3, after step 1 (copying the template to `~/agents/<name>/`) and step 2 (a real CodeBuild build tagged with the name)**. Only `--dry-run` validates before building.
- Runtime name, per the comment: the operator turns `-` into `_` and keeps 40 characters, so `my-agent` should become `my_agent`. The 40-character cut never applies to names the generator accepts.

## C5. The master brief supports "agents run only on AWS AgentCore (Strands) or in ServiceNow"

**Verdict: CONFIRMED.** "Only" is an inference from "must operate within".

`hackathon-context/sources/User-pasted-master-brief.txt`:
- line 91: "For AWS-hosted custom agents, the organizers specify Strands and AgentCore Runtime. ServiceNow-hosted agents are also allowed."
- line 93: "Submitted agents must operate within the provided AWS/ServiceNow environments. Existing code and MCP servers may be brought in if they satisfy the workshop deployment constraints."

Caveats:
- The brief is a pasted summary of a transcript (line 89: "The transcript describes..."; line 87: "Verify this against the actual workshop deployment...").
- The brief restricts submissions; the platform does not enforce it. The AgentConfig CRD is "dual-provider hosting" (KB CRD copy), and `show-run-spans.py` handles Pod-hosted agents (`provider != awsAgentCore`).

**Statement to use:** "Per the master brief (lines 91 and 93), AWS-hosted custom agents use Strands on AgentCore Runtime, ServiceNow-hosted agents are also allowed, and submitted agents must operate within the provided AWS/ServiceNow environments. This is the organizers' rule, not a platform constraint."

## C6. The kill-switch 404 line carries trace.id but no run id or action id

**Verdict: CONFIRMED** (local snapshot, my own parse).

- Line `2026-10-05T09:13:06.794392873Z`: listener=llm, route=internal/llm:request, POST /v1/chat/completions, http.status=404, duration=23ms.
- **Field names (13):** `gateway, listener, route, src.addr, http.method, http.host, http.path, http.version, http.status, trace.id, span.id, protocol, duration`.
- **Missing:**
  - `modaas.run_id`, `modaas.trace_id` and `modaas.action_id`
  - all `gen_ai.*` fields
  - `error` and `reason`. The two route-not-found 404s at 09:10:34 (GET /aaa9, /aab8 on listener http, scanner noise) do have `error="route not found" reason=NotFound`.
- Attribution is by trace id (corrected 2026-10-05 after the lead's live read-only check): the same `trace.id` is on the PDP decision 6 ms earlier (`decide policy_id=model-nemotron-super-120b decision=ALLOW`, `action_id=642489b6-1611-4a92-a161-64083336d770`) and on a `/modaas/evidence` record written by `modaas-authz` with `correlation_id = my-agent-1791191585-4d9744` (the run's CID), `decision = ALLOW`, `policy_version = 331993`. This check originally covered only gateway lines and ledger records, where:
  - The run-id epoch 1791191585 is 09:13:05Z; the 404 is at 09:13:06.8Z.
  - The kill-switch run id appears on **0 of 1,895** gateway lines.
  - The 404's `trace.id` (`f51408192eb04563bbf7299258e2e6e3`) appears on **no other gateway line** and in **none of the 101 ledger records**. The ledger has 3 records for `my-agent-1791191585-4d9744`, none with that trace id.
- On all 1,032 lines carrying both fields, `trace.id == modaas.trace_id`: the gateway continues the caller's trace. The platform's own records complete the join through trace id: the `/modaas/evidence` record with that trace id carries the run's CID (corrected 2026-10-05; the snapshot's PDP log carries the trace id too).

## C7. The operator takes the model from dependsOn.models[0], ignores modelRef, and a CEL rule ties modelRef to dependsOn.models

**Verdict: SOURCE-CONFIRMED.** Not checked: the live CRD, the IT agent's live `modelRef`/`dependsOn.models`, and the operator source. No `agent_operator.py` exists anywhere under `/Users/satyabratsrikumar/firstmate-homes`.

- KB `modaas/crds/agentconfig-v1beta1-crd.yaml`, at spec level:
  ```
  # modelRef is a projection of one dependsOn.models entry ("lifted from dependsOn.models") ...
  # Grandfather: unchanged specs pass (operator status-touch / annotate re-apply never rejected).
  - rule: |
      (oldSelf.hasValue() && oldSelf.value() == self)
      || !has(self.modelRef)
      || (has(self.dependsOn) && has(self.dependsOn.models) && self.modelRef in self.dependsOn.models)
    optionalOldSelf: true
    message: "spec.modelRef must appear in spec.dependsOn.models (declaring modelRef requires the dependsOn.models dependency edge)"
  ```
- KB `workshop/content/choosing-a-model/index.en.md`: "The operator reads `dependsOn.models[0]`, sets it as `MODEL_ALIAS` on the agent's AgentCore runtime and updates the runtime in place (about 10 seconds, measured 2026-09-28)."
- Generator, lines 316-317: "MODEL_ALIAS is reserved: the operator derives it from dependsOn.models and rejects a declared one (DeclaredEnvInvalid, seen live 2026-10-03)". The generator never sets `modelRef`; it only sets `depends = {"models": [model]}` (line 237).

**Statement to use:**
- The runtime's model (`MODEL_ALIAS`) comes from `spec.dependsOn.models[0]`. Declaring `MODEL_ALIAS` yourself is rejected.
- The CEL rule requires only that, on any create or changed spec, a present `modelRef` be a **member** of `dependsOn.models` (any position, not necessarily [0]). Unchanged specs are grandfathered.
- So `modelRef` can legally name `models[1]` while the runtime runs `models[0]`. A swap made by editing `modelRef` alone does not change the running model (inferred from the docs; confirm live).
- "Ignores modelRef" is inferred from the docs. Confirm against the operator source or the live runtime env (`vh.py ac` prints `MODEL_ALIAS` next to the spec values).

## C8. Hand-in leaks the ledger write token

**Verdict: CONFIRMED (source), with corrections.** The live token-occurrence count is blocked.

- `starter/pull-evidence.sh` line 78, a full-object dump including `spec`:
  ```
  kubectl get modelconfig,toolconfig,agentconfig -n components -o json > "$OUT/cr-status.json"
  ```
  Lines 73-76 call it "a full snapshot, not filtered by run id". `approvals.json` and `registry.json` are derived slices without spec. The token travels in `cr-status.json`.
- Not checked: `tmf639.json` (the Canvas resource inventory, which may mirror CR specs including env). `vh.py ac` counts secret occurrences in the live TMF639 response. `gateway-log.json` (grep of pod log lines) and `otel-traces.json` (ledger records) were not scanned either.
- The literal token is in the spec: the generator writes `"AUDIT_WRITE_TOKEN": d.audit_token()` into `spec.awsAgentCore.environmentVariables` for reference agents and own agents (line 233) and for the helper (line 319).
- `new-agent.sh` line 168 uses `kubectl apply -f "$OUT"`, a client-side apply. So the `last-applied-configuration` annotation should hold the token a second time. This is expected, not verified live.
- `starter/submit.sh`:
  - l.34 `EVIDENCE_DIR="$HOME/evidence"`, and l.56 `cp -R "$EVIDENCE_DIR" "$STAGE/evidence"`: the whole directory goes in.
  - l.89-91 `LOCAL_ZIP="./${ZIP_NAME}"` / `zip -qr "$(cd - >/dev/null && pwd)/${ZIP_NAME}" .` / "(kept locally regardless of upload result)". The zip lands in the **directory you ran the script from**, not `--dir`.
  - l.94-99 bucket = `$TEAM_EVIDENCE_BUCKET` or the CFN output `TeamEvidenceBucketName`. l.111 key `submissions/<team>/<zip>`. l.114 `aws s3 cp`. l.119 `aws s3 presign ... --expires-in 604800`.
  - The script calls it "your team's evidence bucket", in the event account ("the account is torn down at the end of the event"). **"Judges' S3 bucket" is not what the script says.**

**Statement to use:**
- Running the kit as-is puts the literal ledger write token into `~/evidence/cr-status.json`. The generator copies `AUDIT_WRITE_TOKEN` from `Secret audit-write-token` into every generated AgentConfig spec, and `pull-evidence.sh` step 2 dumps the full CRs (expect a second copy in the last-applied annotation).
- `submit.sh` then:
  - zips all of `~/evidence` into `submission-<team>-<UTC>.zip`
  - leaves the zip in the directory you ran it from
  - uploads it to `s3://<TeamEvidenceBucketName>/submissions/<team>/`, the team's evidence bucket from the stack outputs
  - prints a presigned URL: 7-day expiry, limited by the session credentials.
- Redact or filter `cr-status.json` before running `submit.sh`.

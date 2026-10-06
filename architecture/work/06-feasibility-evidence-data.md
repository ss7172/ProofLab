# 06 · Feasibility vetting: the evidence and data plane

Written 2026-10-05, 22:58–23:30 UTC, by the evidence-plane feasibility vetter (subagent). It answers the captain's worry: "we are OK with the architecture, but our infra does not support development". It tests that worry component by component against the live platform, for the evidence and data plane of `architecture/ARCHITECTURE.md` (§3.2, §3.5–§3.7, §4, §5, §8, §9).

**Method.**
- **Live reads only**, as WSParticipantRole (our laptop shell, `hackathon` profile): Logs Insights and `filter-log-events`, `kubectl get` / `auth can-i` / `get --raw` (GET), and `aws … describe/get/list`.
- **Nothing written:**
  - no POST, no S3 write, no agent or model call, no cluster write;
  - the ledger Secret's value was never read (only `can-i`);
  - the token count in the CR JSON was done in memory, and only counts were printed.
- **Account id written as `<acct>`.**
- **Also read:** ARCHITECTURE.md §3–§9 and §14; `03-decision-options.md` (D1, D8, D11, D12, F1–F11); `PLANNING-HANDOFF.md` §5; the kit (`pull-evidence.sh`, `submit.sh`, `ask_agent.py`); `reference-impl/` (`audit-store.py`, `reference-agent/agent.py`, `make-agentcore-agents.py`); the IAM policy files; `cfn/02-code-editor.yaml`; and the evidence snapshot `20261005T173727Z`.
- **Older facts** come from the memory file `platform-verified-facts` ("memory").

**Verdict.** The infrastructure supports the evidence and data plane. **0 BLOCKED.**

| Status | Rows |
|---|---|
| SUPPORTED | 17 |
| SUPPORTED-WITH-CAVEAT | 18 |
| SPIKE | 3 |
| BLOCKED | 0 |

Two writes have never been tried, so they are spikes:
- a POST to the ledger from the laptop (OC-8);
- a PutObject to the evidence bucket.

A third spike, the metric publication delay (OC-20), needs a run and folds into the first smoke run.

The caveats are design corrections, not missing infrastructure. Four change the design text:
- **Guardrail outcome:** no span carries a finish reason, so the span only implies a guardrail block (row A5).
- **`aict-invocations` timing:** these records arrive about 5 minutes late, so the pull cadence in §8 is wrong (row B6).
- **Redaction paths:** the token-redaction paths in §9.3 are wrong, and one annotation is missing (row D4).
- **Ledger exports:** the binding limit of the ledger is its 256Mi single-threaded server, not the 1Gi volume (row C5).

**Open checks closed read-only by this vetting:**
- **OC-4:** MCP spans carry the method; no span carries a finish reason.
- **OC-5:** answered "no": the script can't capture the request id.
- **OC-9:** container stdout lands in the runtime log group, about 0.9 s after it is printed.
- **OC-13:** tool Lambda CodeSha256 is readable.
- **OC-14:** `tmf639.json` holds no token.

---

## 1. The vetting table

Rows are grouped A–H: A `aws/spans`; B the other pulls; C the ledger; D the bucket and the pack; E the stitch keys; F the dashboard; G C7's expected events; H the laptop hub.

| ID | Component / assumption (§) | What the infra must support | Evidence (live 2026-10-05 unless marked) | Status | Spike or redesign |
|---|---|---|---|---|---|
| **A1** | EP-2 pull: Logs Insights on `aws/spans` from the laptop (§3.1 EP-2, §5.1, §8) | WSParticipantRole may run `StartQuery` / `GetQueryResults` on `aws/spans` | Kit `console-iam-policy.json`, Sid `ReadAgentObservability`: `logs:StartQuery`, `GetQueryResults`, `StopQuery` on `*`. Nine Insights queries ran today on `aws/spans`, `/aws/modaas/gateway` and `/aws/bedrock/aict-invocations`; all `Complete`. The IDE role has no Insights (03 F2), so the laptop or CloudShell it is | SUPPORTED | — |
| **A2** | Query latency, cost and quotas (§3.1 EP-2) | A run-id query returns in seconds, at negligible cost | <ul><li>S1 `fault-1791179282-8ef1a8`, 30-min window: 1.03 s wall, 91,787 B scanned, 24 rows.</li><li>S2 `fault-1791177342-d3f892` over the full 30-day retention: 2.05 s, 1.59 MB scanned.</li><li>The whole group over 30 days: 2.1 s, 5.79 MB.</li><li>Quotas (`service-quotas`, not adjustable): StartQuery 10 TPS, GetQueryResults 10 TPS.</li><li>Billing is per GB scanned. At AWS's list price (about $0.005/GB in us-east-1; not read live), a per-run query costs < $0.0001.</li><li>AWS documents a 10,000-row cap per query; S2, the largest run, has 353 spans</li></ul> | SUPPORTED | Collectors poll `GetQueryResults` at ≤ 2/s. Window pulls (T1..T2) are sliced by hour, so no slice nears 10,000 rows |
| **A3** | Spans are queryable soon after a call; the "≥ 60 s after the run" wait (§3.1 EP-2; 03 F6) | Ingestion well inside 60 s | <ul><li>749 spans since 17:00Z, span end → `@ingestionTime`: p50 5.1 s, p95 8.3 s, max 9.6 s.</li><li>The S1 run's 24 spans: 2.2–7.1 s.</li><li>(03 F6 measured 2.6–7.1 s on 9 spans)</li></ul> | SUPPORTED | Keep 60 s: six times the observed maximum |
| **A4** | A run's spans fetched by run id in under 2 minutes (§3.7 `refresh`; the two-minute live test) | Wait + query < 120 s | <ul><li>A 60 s wait plus a 1–2 s query.</li><li>S2's figure of record re-derived exactly from `aws/spans`: 174 calls, 174 distinct action ids, 1,999,001 tokens.</li><li>The judge's test itself runs offline on the snapshot, so it needs no AWS call</li></ul> | SUPPORTED | — |
| **A5** | Per-row status and finish reason from the span: EP-7's real outcome (§3.1 EP-7, §5.1; OC-4, second half) | The span names the real outcome | <ul><li>llm spans carry 74 keys:<ul><li>`gen_ai.usage.input_tokens` / `output_tokens`, `gen_ai.request.model`, `gen_ai.request.max_tokens`;</li><li>`http.status`, `agw.ai.usage.cost.*`, `durationNano`;</li><li>`startTimeUnixNano` / `endTimeUnixNano`, `modaas.action_id`, `modaas.run_id`, `traceId`.</li></ul></li><li>**No span carries a finish reason.** `status.code` is `UNSET` on all 24 S1 spans; `http.status` holds the status.</li><li>Both guardrail-shaped spans in 30 days (03:32:41Z on nano-9b; 09:12:28Z `my-agent-1791191546-6aa5dd`) read `listener=llm`, `http.status=200`, 0 input and 0 output tokens, cost 0</li></ul> | SUPPORTED-WITH-CAVEAT | **Redesign EP-7 / §4.2:** `outcome.real = BLOCKED_GUARDRAIL` from a span is an *inference* from that signature, and the record says so (`reason: "inferred: http 200 + 0/0 tokens"`). EP-1's own `finish_reason=content_filter` record corroborates it by action id. Never write that the span says `content_filter` |
| **A6** | Stitch key 1 on spans: run id = the CID (§3.6, §4.2) | Every gateway call of a run carries the CID | <ul><li>S1: 24 of 24 spans carry the CID.</li><li>The CID gets there only as baggage: `ask_agent.py:68` passes `--baggage modaas-correlation-id=<cid>` to `invoke-agent-runtime`. The reference `agent.py` sets no baggage itself; the runtime's OTel propagation carries it.</li><li>With no baggage, the run id is the 32-hex trace id. That happens live today: untagged `modaas-docs` MCP discovery (`initialize` / `tools/list`, 89 sets since 17:00Z) and scanner 404/405s</li></ul> | SUPPORTED-WITH-CAVEAT | <ul><li>`prooflab run` passes `--baggage` on every invoke.</li><li>The first smoke run asserts `count(spans where run_id = CID) > 0`; otherwise EP-2 returns 0 rows and C16 goes INDETERMINATE.</li><li>The stitcher treats a 32-hex run id that isn't in `run-index.jsonl` as background traffic, never as a run</li></ul> |
| **B1** | `/modaas/evidence` pull (EP-6) | A CID pull with the keys WHO and AUTHORIZED need | <ul><li>`filter-log-events` by CID (S1): 1.05 s, 24 records.</li><li>Their 24 action ids equal the 24 span action ids; there is one trace id.</li><li>Keys: `correlation_id`, `action_id`, `trace_id`, `decision`, `policy_id`, `policy_version`, `principal`, `actor` (= the principal), `asset.kind` / `asset.alias`, `detail` (`route_alias=…` on 4 cross-tool calls), `attested_by=modaas-authz`.</li><li>Ingestion lag 1.9–6.9 s; retention 30 days; FilterLogEvents 25 TPS</li></ul> | SUPPORTED | — |
| **B2** | PDP and authz pod logs (EP-6) | RBAC log reads; a principal on each decision | <ul><li>`can-i get pods/log`: yes, in `modaas-system` and `agentgateway-system`.</li><li>Both PDP pods have been up since 2026-10-04 10:35Z, with 0 restarts. No log group exists for either.</li><li>Decision lines read `decide policy_id=… decision=… matched=… latency_ms=… trace_id=… action_id=…`. **0 of 1,037** in the snapshot carry a principal, run id or correlation id.</li><li>authz pods: startup lines only</li></ul> | SUPPORTED-WITH-CAVEAT | <ul><li>Join PDP lines to a run by `action_id`, and take the principal from `/modaas/evidence`.</li><li>The hourly snapshot (§8) stands: a pod restart, or kubelet log rotation (its size limit isn't readable by us), loses lines.</li><li>The snapshot's two PDP logs total 6.7 MB</li></ul> |
| **B3** | Gateway stdout and the `/aws/modaas/gateway` copy (EP-7) | A real outcome per call; a durable copy | <ul><li>The copy (7-day retention): 1,996 records, **0 with a run id, 0 with an action id**, `trace_id` on all 1,996, tokens on 258.</li><li>Stdout: pod `modaas-agw-88dc46ff4-jfcdx`, 0 restarts</li></ul> | SUPPORTED-WITH-CAVEAT | As designed: the copy joins by trace id only (gap 7) |
| **B4** | X-Ray, for corroboration (§9.2) | Trace reads | <ul><li>`get-trace-segment-destination`: `CloudWatchLogs`, ACTIVE.</li><li>`get-trace-summaries` and `batch-get-traces` are allowed.</li><li>The S1 trace came back in 1.03 s: 48 segments (45 `modaas-agw` + 3 runtimes), `LimitExceeded=false`.</li><li>Long runs truncate (S2: 22 of 174, memory). `GetIndexingRules` is denied, so X-Ray's indexing share is unknown</li></ul> | SUPPORTED-WITH-CAVEAT | Partial corroboration only, as §9.2 already says. `aws/spans` is the complete source |
| **B5** | AgentCore metrics, C9's M1 (§5.3, EP-11) | Per-runtime Latency Maximum at 60 s | <ul><li>`get-metric-data` on the S1 window: one 60 s datapoint per runtime. Latency Maximum 6,089 / 25,709 / 12,827 ms (customer / IT / network), Invocations 1, Errors 0; 0.83 s.</li><li>Dimensions: `{Resource=<runtime ARN>, Operation=InvokeAgentRuntime, Name=<runtime>::DEFAULT}`, plus a set with `ComputeType=MicroVM`.</li><li>Also published: Duration, Sessions, SystemErrors, UserErrors, Throttles, CPU and memory.</li><li>1-minute data is kept for 15 days (AWS standard)</li></ul> | SUPPORTED | — |
| **B5b** | C9's near-real-time loop: how soon a datapoint is readable (§5.3; OC-20) | Datapoints within minutes of an invocation | Can't be measured read-only: it needs a fresh invocation | SPIKE | **S3** (folded into the first smoke run) |
| **B6** | `aict-invocations`, the AWS-written invocation record (EP-11; stitch key 5; §8 "per run") | Records present at the per-run pull, and joinable | <ul><li>28 `InvokeAgentRuntime` records in 7 days. **`eventTime` → ingestion: 19–328 s**; 19 of the 28 took 223–328 s. `@timestamp` follows delivery, not the event.</li><li>No session id (empty `requestParameters`). (corrected 2026-10-05 after live re-check: `requestParameters` is empty, but `responseElements` carries the caller-sent `runtimeSessionId`, `traceParent` and `baggage` with the CID on all 28; see `10-f11-resolution.md`.) A `requestID` is present, but the CLI's `invoke-agent-runtime` output has no request id (`runtimeSessionId`, `mcpSessionId`, `traceId`, `traceParent`, `traceState`, `baggage`, `contentType`, `statusCode`, `response`). Only `--debug` would show it, and `--debug` logs the signed headers, session token included.</li><li>Invokers: 26 WSParticipantRole, 2 the IDE role, 0 the runtime role. Retention 7 days</li></ul> | SUPPORTED-WITH-CAVEAT | <ul><li>**Redesign §8's cadence:** pull at least 10 min after `run.finished`, or in the hourly and final refresh, never at +60 s.</li><li>Join on `eventTime` + runtime ARN + `userIdentity` (± tolerance), never on `@timestamp`. (corrected 2026-10-05 after live re-check: join exactly on the `baggage` CID + `runtimeSessionId`, with `eventTime` as the call's end.)</li><li>**OC-5 answered: no request-id key** (§3.6 key 5 keeps ARN + time). (corrected 2026-10-05 after live re-check: no request id is needed; the CID and session id are in the record.)</li></ul> |
| **B7** | CR status and approvals (EP-10, EP-0) | CR reads | <ul><li>`can-i get` / `list agentconfigs`: yes.</li><li>Approvals sit in `status.governance.approvals` (memory).</li><li>`components` events are kept about 1 hour (memory)</li></ul> | SUPPORTED | Write no env path and neither annotation (row D4) |
| **B8** | CloudTrail `lookup-events` (§9.2; APPROVED) | Management history | <ul><li>Works: e.g. `PutBucketVersioning` by System (2026-10-04 10:19:55Z) and by Ops (22:03Z).</li><li>`InvokeAgentRuntime` is a data event, so lookups return 0; only `aict-invocations` holds it.</li><li>`describe-trails` is denied (memory). AWS documents LookupEvents at 2 TPS</li></ul> | SUPPORTED-WITH-CAVEAT | — |
| **B9** | Tool Lambda CodeSha256 (EP-12; OC-13) | Read each code hash against its approval time | <ul><li>The tool Lambdas are named `team-a61f5-*`.</li><li>`ListFunctions` (account-wide) and `GetFunction` (P1 grants `team-*`) return CodeSha256 and LastModified for all 7.</li><li>All run `$LATEST`, last modified 2026-10-04 10:37–10:45Z</li></ul> | SUPPORTED | Query only name, CodeSha256 and LastModified: `ListFunctions` also returns env vars. **OC-13 closed** |
| **B10** | The runtime stdout witness (OC-9; §3.2, the D8 mirror in §3.5) | Container stdout lands in an AWS log group | <ul><li>The reference agent's start line, `print(…, flush=True)` at `agent.py:316`, appears in `/aws/bedrock-agentcore/runtimes/it_resolution_agent-15k2B966z2-DEFAULT`, in `[runtime-logs]` streams, 0.81–0.93 s after it was printed (the 3 hits read, capped by `--max-items 3`, within 30 h).</li><li>The group never expires. Participants can read it; only the runtime role can write to it (03 F3, F8).</li><li>`storedBytes` reads 0 although the streams hold events, so it is unreliable</li></ul> | SUPPORTED | **OC-9 closed.** The runtime half of the D8 mirror needs no AWS write, only the stdout JSON line that §3.2 already specifies. Never use `storedBytes` |
| **C1** | Ledger reads: the export and `tail` (§3.5, §3.7) | GET through the apiserver service proxy | <ul><li>`can-i get services/proxy -n components`: yes.</li><li>A full `GET /records` returned 101 records (48,401 B; 17 CIDs; last write 09:13:40Z) in 1.4 s</li></ul> | SUPPORTED | — |
| **C2** | The laptop POSTs to the ledger: EP-5 handoffs, assessments, notifications (§3.2, §7.2; OC-8) | A network path for POST, with the `X-Audit-Token` header intact | <ul><li>`can-i create services/proxy` and `create pods/portforward` in `components`: both yes.</li><li>The only NetworkPolicy in `components` is Egress-only. The store's pod has no sidecar. There are 0 Istio AuthorizationPolicies and 0 PeerAuthentications.</li><li>The store has two Services: `audit-store` (ClusterIP, :8080) and `audit-store-agentcore` (an *internal* LoadBalancer, :8080, no source ranges). The laptop can't reach the internal ELB.</li><li>`kubectl create --raw` can't set a header, so the client is `kubectl proxy` or `port-forward` plus an in-process HTTP client.</li><li>Untested (no POST made): whether the apiserver proxy forwards `X-Audit-Token`</li></ul> | SPIKE | **S1.** Fallbacks, in order: `port-forward` (raw TCP; nothing can strip the header) → the IDE terminal (inside the VPC; a person drives it) → a one-shot pod in `components` (a cluster write; the user's OK) |
| **C3** | Where the laptop gets the token, and how it stays out of logs and files (§7.2, §8) | A readable source, and hygiene | <ul><li>The server reads Secret `components/audit-write-token`, key `token` (deployment env `valueFrom.secretKeyRef`).</li><li>`can-i get secret/audit-write-token`: yes.</li><li>`make-agentcore-agents.py:199–203` reads the same Secret for every agent it builds. The AgentConfig env and `get-agent-runtime` hold the same 32-character value (memory)</li></ul> | SUPPORTED-WITH-CAVEAT | **Rule for `ledger_client.py`:**<ul><li>read the Secret through a subprocess pipe inside the Python process, and decode it in memory;</li><li>never put it on argv (a `curl -H` shows in `ps`) or in a child's env;</li><li>never run `kubectl -v` ≥ 8;</li><li>never write it to disk; if that's unavoidable, mode 600 inside a 700 directory, removed at exit.</li></ul>The exact-value scan (§9.3) also covers the laptop's logs and spool |
| **C4** | Agent ledger writes from NEW runtimes (EP-1/3/4) | Runtimes we create can reach the ledger | <ul><li>`my-agent`'s runtime, created by us on 2026-10-05 at 09:00Z, wrote 12 records at 09:01–09:13Z.</li><li>All 5 runtimes: network mode VPC (2 subnets, 1 SG), role `a-01-eks-cluster-agentcore-runtime`, env keys including `AUDIT_URL` and `AUDIT_WRITE_TOKEN` (key names only).</li><li>`make-agentcore-agents.py:191–197` sets `AUDIT_URL=http://<audit-store-agentcore internal ELB>:8080`. The `ifabric-` trio is built the same way</li></ul> | SUPPORTED | — |
| **C5** | Ledger volume against the store (§3.5) | Room for our records, and safe exports | <ul><li>PVC `audit-store-data`: 1Gi, gp3. Today: 48 KB at 479 B per record.</li><li>Our estimate: about 5–10K records at about 1.8 KB, so 10–20 MB (1–2 % of the volume).</li><li>**The binding limits are the server's:**<ul><li>one replica (`Recreate`), plain `HTTPServer` (single-threaded, HTTP/1.0);</li><li>a memory limit of 256Mi and a CPU request of 50m;</li><li>every GET parses the whole file (`read_records`), and a full GET holds every record plus the whole body in memory.</li></ul></li><li>Estimate, not measured: about 20–30K records before a full GET risks the 256Mi limit.</li><li>`seq` is epoch milliseconds and can collide</li></ul> | SUPPORTED-WITH-CAVEAT | **Redesign the export mechanics:**<ul><li>export per CID (`?cid=`);</li><li>run a full GET only between runs and at the final refresh;</li><li>while a run is live, no full GET and no `tail` faster than every 3 s. POSTs would queue past the 2 s emit timeout, be spooled, and show as a false C7 coverage drop;</li><li>order by `(seq, record_id)`</li></ul> |
| **C6** | The ledger's lifetime (§3.5) | Records survive until the export | <ul><li>PV reclaim policy `Delete` (gp3), so the data goes with the stack.</li><li>The pod has run since 2026-10-04 10:44Z with 0 restarts</li></ul> | SUPPORTED-WITH-CAVEAT | As designed: export before teardown |
| **D1** | Participant S3 on `team-evidence-*` (§8, §9) | Put, Get and List; the version listing | <ul><li>Policy P2 allows Get, Put, Delete and List.</li><li>Live: `s3 ls` works (4 objects). `head-object` works: a missing key gives 404 (not 403), and a real object returns VersionId, LastModified, an MD5 ETag and SSE AES256.</li><li>AccessDenied: `ListObjectVersions`, `GetBucketVersioning`, `GetBucketPolicy`, `GetBucketLifecycleConfiguration`, `GetObjectLockConfiguration`, `GetBucketAcl`, `GetObjectAttributes`.</li><li>**PutObject is untested** (no writes).</li><li>The CFN gives the team bucket no bucket policy (`02-code-editor.yaml:225–253`); an SCP can't be read (OC-17).</li><li>The IDE role still has `EvidenceVersionRead` (`ListBucketVersions`, `GetObjectVersion`, `GetObjectVersionAttributes`)</li></ul> | SPIKE (PutObject) | **S2** |
| **D2** | The register's date proof T1: a write-once object whose version a stranger can see (§3.3; D5) | AWS-set time and version, visible to a stranger | <ul><li>Versioning is on, and noncurrent versions expire after 7 days. Server access logs go to a bucket no participant can read. There is no Object Lock (CFN; CloudTrail, memory).</li><li>So "write-once" is a convention: a participant can overwrite the object or add a delete marker.</li><li>**It is fail-safe anyway.** The T1 check reads the *current* version's AWS-set LastModified, VersionId and ETag, which `head-object` gives the participant. An overwrite can only move LastModified later, so tampering turns the check INDETERMINATE, never into a false pass.</li><li>The version history needs the IDE role, so a person runs it (SSM is denied to us), any time before teardown.</li><li>A stranger can verify live only before teardown: the organisers can read the bucket and its access logs. After teardown, only our exported head and versions JSON plus the MANIFEST remain, and that is testimony</li></ul> | SUPPORTED-WITH-CAVEAT | Build note (untested): PUT with `--checksum-algorithm SHA256`, then `head-object --checksum-mode ENABLED`, gives an AWS-computed SHA-256 instead of the MD5 ETag. Use a prefix of ours (`ifabric/register/`) |
| **D3** | `submit.sh` mechanics (§9.1) | Package and upload from the laptop | <ul><li>It copies `~/evidence` verbatim (`cp -R`) and zips it.</li><li>It uploads with `aws s3 cp` to `submissions/<team>/submission-<team>-<UTC>.zip`. That needs PutObject; a multipart upload needs nothing more unless it is aborted.</li><li>Its `MANIFEST.txt` lists the files, without hashes.</li><li>The bucket comes from `TEAM_EVIDENCE_BUCKET`, which is set (the fallback lookup returns empty; memory).</li><li>It presigns for 604,800 s, but a URL signed with session credentials dies with them. It prints the URL to stdout</li></ul> | SUPPORTED-WITH-CAVEAT | Never record the presigned URL. Our `MANIFEST.json` carries the hashes. S2's PutObject probe covers the upload permission |
| **D4** | The token-redaction must-fix (§9.3; EP-10 `cr_status.py`) | Every copy stripped before upload | <ul><li>`pull-evidence.sh:78` writes `kubectl get modelconfig,toolconfig,agentconfig -n components -o json`. That output holds **15 copies** of the one 32-character ledger token today, 3 per AgentConfig:<ul><li>`spec.awsAgentCore.environmentVariables.AUDIT_WRITE_TOKEN`;</li><li>annotation `kubectl.kubernetes.io/last-applied-configuration`;</li><li>annotation `kopf.zalando.org/last-handled-configuration`.</li></ul></li><li>CR status: none.</li><li>`tmf639.json` (14,357 B): **0 copies** (OC-14 closed).</li><li>§9.3 and EP-10 name `spec.env` and only the last-applied annotation</li></ul> | SUPPORTED-WITH-CAVEAT | **Correct §9.3 and EP-10:**<ul><li>drop all three paths, and any `environmentVariables` map, on every CR kind;</li><li>keep the exact-value scan.</li></ul>The `ifabric-` CRs will carry the same three copies |
| **D5** | The evidence bucket is shared with the organisers | Our keys never collide with theirs | 4 `facilitator/` objects (twin fix scripts and data: `fix-twin.sh`, `twin-dataset.json`, `twin-scenario.sh`, `twin-vs-agent.json`) landed at 21:14–21:21Z | SUPPORTED-WITH-CAVEAT | Write only under `ifabric/` and `submissions/`; never delete others' objects. Relay to the lead: gap 10 (the twin) may have changed |
| **E1** | Stitch key 1, `correlation_id` / `run.id` (§3.6, §4.2) | The CID on spans, `/modaas/evidence` and the ledger | <ul><li>Spans: 24 of 24 (row A6).</li><li>`/modaas/evidence` `correlation_id`: 24 of 24.</li><li>Ledger: `correlation_id` on 101 of 101</li></ul> | SUPPORTED-WITH-CAVEAT | The baggage rule (row A6) |
| **E2** | Key 2, `call.id` = the gateway action id | The action id on spans, evidence, PDP lines and stdout | <ul><li>S1: the 24 span action ids equal the 24 evidence action ids.</li><li>PDP lines and gateway stdout carry `action_id` (snapshot; memory).</li><li>Our own records need it from the response header (OC-3: a smoke-run check, agent plane)</li></ul> | SUPPORTED | — |
| **E3** | Key 3, `trace.id` | The trace id across sources | <ul><li>Spans: `traceId` (= `attributes.trace.id`).</li><li>Evidence: `trace_id`. PDP: `trace_id`. The gateway copy: `trace_id` on 1,996 of 1,996.</li><li>X-Ray id = `1-<first 8 hex>-<last 24 hex>`.</li><li>The reference agents' ledger trace ids are minted by the agent (memory)</li></ul> | SUPPORTED | Our agents continue the inbound trace (a build item) |
| **E4** | Key 4, `handoff.id` | Our ids only | No platform surface carries payload ids (the AWS invocation record's `requestParameters` is empty). (corrected 2026-10-05 after live re-check: its `responseElements` does carry the caller-sent `runtimeSessionId`, so a session id minted per hand-off is joinable on an AWS-written record.) | SUPPORTED | A pure build item: the script mints the id and the agent echoes it |
| **E5** | Key 5, `runtime.arn` + time | The ARN and a reliable time | Row B6: the ARN is in `resources[0].ARN`; the time is `eventTime`, not `@timestamp`; `userIdentity` tells the script from the IDE. (corrected 2026-10-05 after live re-check: the record also carries the CID, session id and traceparent, in `responseElements`.) | SUPPORTED-WITH-CAVEAT | Row B6 |
| **E6** | Sources without the keys: PDP without a principal; the id-less access-log copy; refusals without a run id (§3.6 key 3; gaps 2 and 7) | Join paths where the keys are missing | <ul><li>Rows B2 and B3.</li><li>Since 17:00Z: 7 model-listener 404s (6 `llm`, 1 `llm-tls`), 24 `http` 404s and 184 405s, none with a run id (scanners, and MCP GETs with no method)</li></ul> | SUPPORTED-WITH-CAVEAT | As designed: the trace-id join, then `unresolved:<trace id>` plus a link-gap |
| **F1** | The dashboard: static HTML from a snapshot (§3.7; D1) | No server and no endpoint | <ul><li>Nothing to provision: a file rendered on the laptop, with its data inlined, that travels inside the zip (the bucket blocks public access).</li><li>Size: today's snapshot is 8.0 MB, 0.78 MB deflated (10×).</li><li>A full pack is estimated at 30–60 MB raw, about 5–10 MB zipped. The raw spans of every run are about 6 MB over 30 days</li></ul> | SUPPORTED | Inline only the engine's JSON output; link the raw files by relative path |
| **G1** | C7's expected events: an MCP method on each span, so set-up spans can be dropped (§5.2; OC-4) | `mcp.method.name` on every MCP span | <ul><li>S1 has 15 MCP spans, on listener **`http`** (not `mcp`): 3 × (`initialize`, `notifications/initialized`, `tools/list`) plus 6 × `tools/call`.</li><li>`gen_ai.tool.name` sits on `tools/call` spans (`<target>___<operation>`). So the expected set from the gateway is 9 model calls + 6 tool calls.</li><li>The reference agent caches its tools per container (`agent.py:95–132`), so set-up spans appear only on a container's first invocation.</li><li>MCP GET 405s have no method and no run id</li></ul> | SUPPORTED | Filter `attributes.mcp.method.name = "tools/call"` and `attributes.listener = "llm"`. **OC-4 closed** |
| **G2** | The expected set is complete soon after the run (§5.2's INDETERMINATE window) | Every source ingested within the wait | Spans: ≤ 9.6 s. `/modaas/evidence`: ≤ 6.9 s | SUPPORTED | — |
| **H1** | The laptop hub's credentials (§8; D11) | Pulls and `watch` keep running | <ul><li>Valid at 22:58Z.</li><li>They expired once, at about 18:20Z (handoff §0.4). Every live pull (Insights, kubectl, S3) depends on them</li></ul> | SUPPORTED-WITH-CAVEAT | As designed: the supervisor emits `monitoring-gap` and stops on `ExpiredToken`. CloudShell is the fallback (not checked live) |

---

## 2. Stitch keys × sources (live 2026-10-05, the S1 run unless marked)

| Source | CID (key 1) | action id (key 2) | trace id (key 3) | handoff id (key 4) | runtime ARN + time (key 5) | principal |
|---|---|---|---|---|---|---|
| `aws/spans` (gateway) | yes, 24/24, but only via baggage | yes | `traceId` | no | no | no |
| `/modaas/evidence` | yes, 24/24 | yes, the same 24 | yes | no | no | yes (`bootstrap-key`) |
| PDP pod lines | **no** | yes | yes | no | no | **no** (0/1,037) |
| `/aws/modaas/gateway` copy | **no** (0/1,996) | **no** (0/1,996) | yes (1,996/1,996) | no | no | no |
| Gateway stdout (pod) | yes (memory) | yes | yes | no | no | no |
| X-Ray | as segment metadata only | as metadata | yes | no | runtime segments | no |
| `aict-invocations` | **no** (corrected 2026-10-05 after live re-check: **yes** on `InvokeAgentRuntime`, 28/28, `responseElements.baggage` and the session-id prefix; no on model calls) | no | no (corrected 2026-10-05 after live re-check: `traceParent` on `InvokeAgentRuntime`) | no (corrected 2026-10-05 after live re-check: the `runtimeSessionId` the caller sent) | ARN + `eventTime` (delivered 19–328 s late) | `userIdentity` (an IAM role) |
| AgentCore metrics | no | no | no | no | ARN dimension, 60 s buckets | no |
| Runtime `[runtime-logs]` | whatever we print | whatever we print | whatever we print | whatever we print | the log group = the runtime | no |
| Ledger (reference agents) | yes | no | agent-minted, ≠ the run trace | no | no | no |
| Ledger (our records, by design) | yes | yes | yes, continued | yes | `runtime.arn` | `principal.platform` (pulled) |

---

## 3. Top risks (ranked)

1. **The ledger server is fragile under load.**
   - One replica, a single-threaded `HTTPServer`, 256Mi, whole-file scans per GET (row C5).
   - A full export or a tight `tail` loop during a live run can push agent POSTs past their 2 s emit timeout. The records are then spooled, and C7 shows a false coverage breach.
   - A very large full GET can OOM-kill the pod. The PVC survives, but the export fails.
   - *Mitigation:* per-CID exports, no full GET while a run is live, `tail` no faster than every 3 s, and the stdout witness (row B10) to recover anything lost.
2. **The laptop → ledger POST path is unproven (OC-8).**
   - EP-5 handoffs, the assessment and finding records, and the ServiceNow `notification` mirror all depend on it.
   - RBAC allows both routes. Only the header forwarding through the apiserver proxy is unknown.
   - *Mitigation:* spike S1 in the first live-lane slot, with the fallback chain in row C2.
3. **A token leak through wrong redaction paths (row D4).**
   - If `cr_status.py` follows §9.3 as written, 2 of the 3 token copies per AgentConfig survive into the judged bucket: the env path is `spec.awsAgentCore.environmentVariables`, and the kopf annotation is missed.
   - *Mitigation:* fix §9.3 and EP-10, and keep the exact-value scan as the gate.
4. **A run without baggage is invisible to the C16 floor (row A6).**
   - If `prooflab run` invokes without `--baggage modaas-correlation-id=<CID>`, the spans carry trace ids. The EP-2 query by CID then returns 0 rows, and the assessed run is INDETERMINATE: wasted budget.
   - *Mitigation:* a smoke-run assertion before any assessed run.
5. **The `aict-invocations` pull comes too early (row B6).**
   - A pull at +60 s finds nothing for most runs, which shows as false corroboration gaps.
   - *Mitigation:* pull at ≥ +10 min or in the hourly refresh; join on `eventTime`. (corrected 2026-10-05 after live re-check: join exactly on the CID and session id in `responseElements`; `eventTime` is the call's end.)
6. **Laptop credentials expire, or the laptop sleeps (row H1),** during pulls or the `watch` loop.
7. **Teardown ends every source.**
   - All retentions (7 and 30 days, "never") stop at account teardown, and the T1 version history is visible to a stranger only before it.
   - *Mitigation:* final refresh, submit, keep a local zip copy, and run the IDE version listing before the end.

---

## 4. Spikes to run FIRST

| # | Spike | Exact minimal test | Reversible? | Cost | Approver | Pass / fail → next step |
|---|---|---|---|---|---|---|
| **S1** | OC-8: a laptop POST to the ledger, with zero writes | See the steps below this table | Yes. The token check (`audit-store.py:84–87`) and the JSON-object check (`:89–94`) run before the append (`:95–100`), so a 400 writes nothing | $0, about 5 min | The user (live lane: it handles the ledger token) | **400 `bad record: record must be a JSON object`** = the path and the header work. **401** = the header was stripped: repeat through `port-forward`. Both fail: the fallbacks in row C2 |
| **S2** | Participant PutObject, and the T1 capture | See the steps below this table | Partly: the object can be deleted (a delete marker), but its version persists until 7 days after it becomes noncurrent. Harmless, and visible to the organisers | $0, about 5 min | The user (an S3 write to the judged bucket) | Pass: run the real register freeze the same way. AccessDenied = an SCP or a bucket policy we can't read (OC-17): raise it with the organisers *before* the freeze, because T1 and `submit.sh` both depend on it |
| **S3** | OC-20, the metric publication delay, plus the smoke-run assertions for this plane | See the steps below this table | Read-only, inside a run that happens anyway | $0 beyond the smoke run (GetMetricData costs pennies) | No new approval: it rides on the first smoke run's OK | It sets `prooflab watch`'s poll interval and C9's "datapoints present" rule. Any assertion that fails blocks the first assessed run |

**S1 steps.**
1. Start `kubectl proxy --address=127.0.0.1 --port=8001` in the background.
2. In one Python process:
   - read the token with `subprocess.run(["kubectl","get","secret","audit-write-token","-n","components","-o","jsonpath={.data.token}"], capture_output=True)` and base64-decode it in memory;
   - with `urllib`, POST to `http://127.0.0.1:8001/api/v1/namespaces/components/services/audit-store:8080/proxy/records`;
   - send the headers `Content-Type: application/json` and `X-Audit-Token`, and the body `[]`;
   - print only the HTTP status and the body.
3. Count the records with `GET /records` before and after: the count must not change.
4. If the status was 401, repeat through `kubectl port-forward -n components svc/audit-store 18080:8080`, posting to `http://127.0.0.1:18080/records`.

**S2 steps.**
1. `aws s3api put-object --bucket $TEAM_EVIDENCE_BUCKET --key ifabric/_probe/<UTC>.txt --body <a 1-line file> --checksum-algorithm SHA256`, and keep the returned `VersionId`.
2. `aws s3api head-object … --checksum-mode ENABLED` should return `VersionId`, `LastModified`, `ETag` and `ChecksumSHA256`.
3. Ask the person at the IDE to rehearse the T1 export once: `aws s3api list-object-versions --bucket … --prefix ifabric/_probe/` (a read).

**S3 steps.** In the first smoke run:
1. **OC-20:** after each invocation returns, poll `get-metric-data` (Latency, Maximum, 60 s, that runtime) every 30 s until the datapoint appears, and record the delay.
2. Assert the following:
   - a. `aws/spans` holds more than 0 spans with `run_id` = the CID (row A6);
   - b. each agent's stdout JSON lines appear in its `[runtime-logs]` stream (row B10);
   - c. `aict-invocations` holds the run's 3 `InvokeAgentRuntime` records within 10 min (row B6);
   - d. the expected-event count from spans (filtered by `mcp.method.name`) matches our tool records (row G1).

---

## 5. What this changes in ARCHITECTURE.md

- **§3.1 EP-7, §4.2:** BLOCKED_GUARDRAIL from a span is inferred (200 + 0/0 tokens + cost 0). The span has no finish reason; EP-1's record corroborates it.
- **§3.2 / §3.5, the D8 mirror:** "container stdout lands in the runtime log group" is now VERIFIED (OC-9), with an ingestion lag under 1 s. The runtime half needs no AWS write.
- **§3.5 export:** export per CID. Run a full `GET /records` only between runs and at the final refresh. Keep `tail` at ≥ 3 s.
- **§3.6 key 5:** OC-5 is answered: no request id can be captured, so the join is ARN + `eventTime` + `userIdentity`. (corrected 2026-10-05 after live re-check: the join is exact on the `baggage` CID + `runtimeSessionId` in `responseElements`; see `10-f11-resolution.md`.)
- **§5.2 / OC-4:** closed. Filter on `mcp.method.name`. The MCP listener value is `http`.
- **§8 cadence:** `aict-invocations` is pulled at ≥ +10 min (it is delivered 19–328 s late), joined on `eventTime`.
- **§9.3 and EP-10:** the redaction targets are `spec.awsAgentCore.environmentVariables`, `kubectl.kubernetes.io/last-applied-configuration` and `kopf.zalando.org/last-handled-configuration`. OC-14 is closed: `tmf639.json` is clean.
- **§14:** close OC-4, OC-5, OC-9, OC-13 and OC-14. OC-17 is partly answered: the CFN defines no bucket policy on the team bucket, and an SCP is still unreadable.

## 6. Not checked here

- **Writes:** any POST, PUT or apply (S1 and S2 above).
- **Unreadable from our role:**
  - the deployed bucket policy or an SCP (`GetBucketPolicy` is denied);
  - X-Ray's indexing share (`GetIndexingRules` is denied);
  - the kubelet log-rotation size.
- **Not looked up:** the Logs Insights concurrent-query quota (not listed by `service-quotas`).
- **Not tried:** CloudShell.
- **Other planes:**
  - the agent plane: OC-1–OC-3, OC-10–OC-12;
  - EP-0's field paths (OC-19).

# 03 · Key architecture decisions: options, evidence, recommendations (D1–D12)

Written 2026-10-05, about 20:30–21:40 UTC, by a Claude subagent, as architecture input 03 (next to `01-delta-audit.md` and `02-requirements.md`). Read-only research. The live checks used read verbs only (IAM `get-role-policy` / `get-policy-version`, CloudTrail `lookup-events`, Logs Insights, CloudWatch `get-metric-statistics` / `list-metrics`, `s3api list-object-versions` (refused), `kubectl get` / `explain`), as WSParticipantRole, 20:34–20:58 UTC. No secret was printed. No write was made except this file.

**What this file is.** For each decision: 2–4 options, the evidence, the fit to the judging criteria, effort, risks, a **recommendation (not decided)** and whether it needs the captain. The team decides. The only settled thing is the captain's frame (§1), which every option here sits inside.

**Deadline.** Tuesday 2026-10-06 15:00 UTC (10:00 CDT; UNCONFIRMED) [handoff §2.5]. That is about 18 h after 21:00 UTC on 2026-10-05.

**Citations.** As in `PLANNING-HANDOFF.md` §0.2 ([handoff §x], [mem: X], [notes #N], [gap N], [corr row N], [verify-live], [kit: F], [SN handoff §x], [PB §x]). Also:
- [F1]–[F11]: facts verified during this task (§2).
- [slides pN]: PDF page N of `hackathon-context/sources/Immersion-Day-slides.pdf`, text in `hackathon-context/work/hackathon-sources/slides-extracted.txt`.
- [src: F]: the platform source `workshop-assets/modaas-aigateway-src.zip`, read locally.
- [Strands: F]: the pinned `strands-agents 1.57.2` in `workshop-local/.venv`, read locally.
- R-J / R-P / R-C / R-D ids: `architecture/work/02-requirements.md`.

The prior design (`hackathon-context/outputs/prooflab-detailed-architecture.txt`) was read for structure only. Its platform assumptions (a DynamoDB admission store, gateway-side admission, a gateway B handoff, a labelled C9 corpus) are not reused where the verified platform says otherwise; `01-delta-audit.md` has the row-by-row audit.

---

## Summary (one screen)

| D | Decision, inside the frame | Recommendation (not decided) | Captain? | Fleet h | Live h | Clock-bound |
|---|---|---|---|---|---|---|
| D1 | The app: form and hosting | The CLI is the control test (one engine). It renders one self-contained static HTML file (ledger, control test and six-question views) from an exported snapshot of the store. No server, no network, no public endpoint | Only for the upload's content (S3 write) | 6–8 | 0.25 | Render after the final snapshot |
| D2 | C16: floor and the one in-path question | Floor: post-run `pull()` over `aws/spans` by run id. Bonus: one `evaluate()` in a `BeforeModelCallEvent` hook, reserve-then-commit (projected input + `max_tokens`); the tally comes from the streamed usage and the script carries it between agents. Same evaluator in both places | Yes: caps, deploys, test budget | 7–9 | 0.5 | Cap frozen before the first assessed run |
| D3 | C9: metric, statistic, window, baseline, alerts | AgentCore invocation Latency per runtime: Maximum, plus Errors Sum and invocation count for coverage. Window = each run's time range (1-min data), hourly roll-up for window questions. Baseline from ≥ 6 post-freeze runs, declared before the C9 assessed runs. One finding per crossing via `callback()` | Yes: metric strategy, baseline spend | 3–5 | 0.5–1 | After the agents freeze |
| D4 | C7: expected events, event set, gaps | Expected = gateway actions in `aws/spans` (model calls, `tools/call`) + a declared workflow spec (lifecycle, handoffs, escalations). Observed = records the acting adapter emitted at action time; pulled back-fills don't count. Gap = consecutive expected events in one agent stream, on the agent's clock | Values only | 5–7 | 0 | — |
| D5 | Registry: source, hand-out, date proof | `register.yaml` → frozen version file + sha256. In-path copy = env set at deploy (version, sha256, value). Date proof = a write-once object in the **versioned** evidence bucket [F1] + the owner's approval in ServiceNow | Yes: S3, ServiceNow, owner sign-off | 1–2 (+ owner 1–2) | 0.25 | Before the first assessed run |
| D6 | Second EP: which pair shows "moved, nothing rewritten" | The captain's pair: the same C16 evaluator in the model-call adapter (`evaluate`) and in the post-run adapter on the managed gateway's log (`pull`). Prove it with one module, one sha256 and an adapter-diff note; the judge re-running it from the pack is a free third placement | No (documentation) | 0.5–1 | 0 | — |
| D7 | Agents | A new `ifabric-` trio cloned from the reference agent and built by the Module 7 path, all on `nemotron-super-120b`. Keep the reference trio as the "before" system. Judgment = structured output + deterministic rules, emitted as records. The orchestrating script records the handoffs | Yes: cluster writes, models, IT revert | 6–8 | 1–1.5 | Before the register freeze and the C9 baseline |
| D8 | The one append-only evidence store | The platform ledger (`audit-store`): every adapter can reach it, it takes any JSON, it has no update or delete route [F7]. Snapshot export as JSONL + raw captures + MANIFEST. Optional AWS-timestamped mirror from the runtime | Yes for the mirror (AWS write) and the record volume | 3–5 (+2) | 0.25 | Export before teardown |
| D9 | Named PASS and BREACH runs | One shared PASS (ifabric S1) and one shared BREACH (reference trio on S2, with IT back on super-120b) for all three controls. The ifabric S2 run is the inline-stop demo: a PASS with a stop record, not a breach | Yes: budget, IT revert | 0.5 | 1.5–2.5 (+1 h ceiling recovery) | After the freeze |
| D10 | Guardrail layers per EP | Our code refuses only through the C16 check. Everything else records: tool scope, arguments and tool results; the real outcome of guardrail, pause and Cedar decisions; admission through the deploy wrapper; CodeSha256 and approval staleness. Configure one Cedar forbid rule on an `ifabric-` ToolConfig for Hostile/Rogue tests. Identity, classification, TLS, approvals and ledger integrity stay gaps | Yes for the Cedar edit | 3–5 | 0.25–0.5 | — |
| D11 | Where each adapter runs; credentials | Runtime: the model-call adapter and agent emits. Laptop: the orchestrating script, pull adapters, stitcher, evaluators, query tool, ServiceNow callback. IDE: human-run reads only (bucket version listing). CloudShell as the fallback for pulls | Yes: ServiceNow credential placement, refresh duty | 1–2 | 0 | Admission pulls at least hourly |
| D12 | Record schema and stitch keys | A flat, dotted superset of the slide's evidence record plus the captain's fields; a `record_kind` enum; `correlation_id` on every record; deterministic ids for pulled records. Stitch order: CID → action id → trace id → handoff id → runtime ARN + time → finding id | No | 1.5–2 | 0 | Freeze before adapters are written |

**Totals (estimates; the row sums):** fleet about 38–55 agent-hours, plus 2 for D8's optional mirror and the owner's 1–2 h on D5, so about 6–8 h of wall clock with 6–8 parallel workers. Live lane about 4.5–7 h serialized, plus about 1 h of token-ceiling recovery after an S2 run. About 18 h remain. The live lane and the owner's sign-offs are the bottleneck, not the code.

**Needs the captain** (a cluster, AWS or ServiceNow write, budget, or strategy): D2, D3, D5, D7, D8 (mirror), D9, D10 (Cedar edit), D11 (credential placement). D1, D4, D6 and D12 are build choices, except where noted.

**Corrections to earlier documents found here** (§2): the evidence bucket **is versioned** [F1], which changes [corr row 15], gap 6's bucket wording and R-C-16; the IDE role **cannot** run Logs Insights [F2]; the ModelConfig `external` safety enforcer is **not a hook** [F4]; the AWS-written `InvokeAgentRuntime` records carry **no session id** [F11] (corrected 2026-10-05 after live re-check: they do carry the caller-sent session id, CID and traceparent, in `responseElements`; see `10-f11-resolution.md`).

---

## 1. The frame (decided by the captain; not an option)

From the captain's direction and its correction (2026-10-05), relayed by the coordinator:
- **Adapters around every enforcement point** call **one contract with four transports**, and every adapter produces **the same decision record**:
  - `evaluate()`: synchronous, in the path, can refuse;
  - `emit()`: an asynchronous record;
  - `callback()`: a deferred or human verdict;
  - `pull()`: scheduled or continuous.
- `evaluate()` is tied to a control in a **versioned control registry**. The registry hands out a **frozen, version-stamped** copy that is loaded beforehand; it is **never called in the path**. The **evaluator is stateless**.
- **One question only may make work wait:** the optional C16 check before each model call ("is this run still under cap?"), through `evaluate()` in **our agent runtime**. Post-run C16 over `aws/spans` is the floor; inline is the bonus.
- **Everything else records:** model and tool calls (`emit`); platform guardrail, Cedar and pause outcomes (`emit`, observed); approvals and ServiceNow responses (`callback`); metrics and spans (`pull`). Our agents' own judgment (for example S3 escalate instead of act) is agent behaviour that produces a recorded decision (`emit`); it is not a registry `evaluate()`.
- **Handoffs are record events** (`emit` only, for C7 and RECONSTRUCT), never blocking. A handoff record carries from → to, run id, timestamp, a payload digest and the payload's data classification. Agents don't call each other; the orchestrating script emits the handoff records.
- **The C16 running tally lives in the adapter and travels with the run.** The evaluator never remembers.
- **The same evaluator inline and post-run is the second enforcement point.**
- **Every decision goes into one append-only evidence store** with full metadata (control, threshold version and value, measured value, verdict, reason; actor, on whose behalf, platform principal, EP id, the EP's responsible party, the control owner; run id, action id, trace id, handoff from → to; timestamps with their clock; source refs). This covers platform decisions, our agents' decisions, human approvals and ServiceNow responses.
- **A stitcher** joins records by CID, action id and trace id, including agent-to-agent handoffs. **The control test / query tool** (the dashboard's backend) queries that store.
- **Platform reality:** only our own code can refuse (our agent runtime). Platform EPs (gateway + Cedar, guardrails, admission, the collector) are observed via `emit()`/`pull()` and configured where possible (ToolConfig `cedarPolicy`).

```
 frozen, version-stamped registry copy ──(loaded before the run; never called in the path)──┐
                                                                                             v
 orchestrating script ──handoff record (emit)──> our agent runtime ──model call──> modaas-agw ──> Nemotron
   carries run id + C16 tally                     ONE wait: C16 evaluate() before each model call
                                                  everything else: emit (calls, tool calls, judgment)
 platform EPs (gateway+PDP/Cedar, guardrails, pause, admission, collector): refuse on their own;
   we configure ToolConfig Cedar where allowed, and record their outcomes via emit()/pull()
 callback(): ServiceNow findings, owner responses, approvals (recorded, never blocking)
 pull():     aws/spans, /modaas/evidence, PDP pod logs, AgentCore metrics, CR status, aict-invocations
 all records ──> ONE append-only evidence store ──> stitcher ──> control test / query tool ──> dashboard
```

---

## 2. Facts verified during this task (read-only, 2026-10-05 20:34–20:58 UTC)

| # | Fact | How checked | Bears on |
|---|---|---|---|
| F1 | **The team evidence bucket is versioned.** CloudTrail shows `PutBucketVersioning` with `Status: Enabled` on `team-evidence-<acct>` at stack creation (2026-10-04 10:19:55 UTC, the stack's role), a lifecycle rule `NoncurrentVersionExpiration: 7 days`, **server access logging** to `modaas-evidence-access-logs-<acct>` (prefix `team-evidence/`; that bucket expires logs after 30 days), SSE-S3 and a full public-access block. No Object Lock event. WSParticipantRole still gets AccessDenied on `ListObjectVersions` (tested now). **Ops (`WSOpsRole`) added the inline policy `EvidenceVersionRead` to the IDE role at 2026-10-05 18:10:39–41 UTC**: `s3:ListBucketVersions` on the bucket and `s3:GetObjectVersion` / `GetObjectVersionAttributes` on its objects. Neither team role has `s3:DeleteObjectVersion` (all three WSParticipantRole policies and all IDE-role inline policies read); WSParticipantRole's `DeleteObject` can only add a delete marker in a versioned bucket. Participants have no access to the access-logs bucket. | `cloudtrail lookup-events` (PutBucketVersioning, PutBucketLifecycle, PutBucketLogging, PutBucketEncryption, PutBucketPublicAccessBlock, PutRolePolicy) with `requestParameters`; IAM policy reads; one refused `list-object-versions` | **Corrects** [corr row 15], gap 6's "the hand-in bucket can't vouch" and R-C-16: an object's `LastModified` and version history are AWS-set and visible to the IDE role and the organisers. It still doesn't prove content wasn't altered *before* upload. D5, D8 |
| F2 | **The IDE role (`a-02-code-editor-IdeInstanceRole-…`) has no `logs:StartQuery`, `GetQueryResults` or `FilterLogEvents`**: only `GetLogEvents`, `DescribeLogStreams`, `DescribeLogGroups`. It does have `cloudwatch:GetMetricData`, X-Ray reads, `bedrock-agentcore:GetAgentRuntime` / `InvokeAgentRuntime`, CodeBuild on `*modaas-image-build*`, team-* DynamoDB / SNS / SQS / EventBridge / Secrets Manager / alarms, log groups `/team/*`, `lambda:*` on `team-*`, and S3 `PutObject`/`GetObject`/`ListBucket` (no `DeleteObject`) on the evidence bucket. | `iam get-role-policy` on `ide-workshop`, `EvidenceVersionRead`, `AictGetRole` | The SN handoff assumes "run it in the IDE terminal": an `aws/spans` Insights pull can't run there. D11 |
| F3 | **The AgentCore runtime role** (`a-01-eks-cluster-agentcore-runtime`): logs create/put/describe **only on `/aws/bedrock-agentcore/*`**, no logs read; `cloudwatch:PutMetricData` on `*` with no namespace condition; X-Ray put; `InvokeAgentRuntime` on `runtime/*`; explicit Deny on `bedrock:InvokeModel*` and `bedrock-agentcore:InvokeGateway`; no S3, DynamoDB or Secrets Manager permission. | `iam get-role-policy … agentcore-runtime` | An in-path adapter can't read spans or the evidence log; it can write a log group under `/aws/bedrock-agentcore/` and publish custom metrics. D2, D8, D11 |
| F4 | **The ModelConfig `external` safety enforcer is not a hook.** The operator only "echoes endpoint config to status for gateway consumption" ([src: `operators/aws-model-operator/model_operator.py` :459–481]); no code in `authz-gateway/`, `pdp/` or the route programming reads `enforcerEndpoint`; `gatewayFilter` is "not yet implemented" (:483–491). `gateway_capability.py` says external kinds are realized by ext_authz → `modaas-authz` → PDP. | grep of the platform source; `kubectl explain modelconfig.spec.safety` | Removes a tempting gateway-side `evaluate()` option. D2, D10 |
| F5 | **Pinned Strands 1.57.2 has the hooks we need.** `BeforeModelCallEvent` has a writable `cancel` and `projected_input_tokens` ("None if estimation failed"); `AfterModelCallEvent` has `exception`, `stop_response`, `retry`; `BeforeToolCallEvent` has `cancel_tool` and interrupts; `BeforeInvocationEvent` has `cancel`. `OpenAIModel` sends `stream_options: {include_usage: true}`; `EventLoopMetrics.accumulated_usage` sums per-call usage. | [Strands: `hooks/events.py` :39–66, :221–260, :318–401; `models/openai.py` :515; `telemetry/metrics.py` :216–225] | The C16 hook and the tally source. D2, D7 |
| F6 | **Latency data.** Gateway spans in `aws/spans` carry `durationNano`. Ingestion lag (`@ingestionTime` − `@timestamp`) was 2.6–7.1 s on the 9 model spans of `fault-1791179282-8ef1a8`. **Per-call duration is flat across runs, S2 included**: super-120b averages 1.68–2.53 s per run (p95 ≤ 4.09 s); S2's 174 calls average 2.01 s, p95 3.01 s, max 4.55 s; the 2 nano-9b calls took 1.80 s and 6.67 s. **AgentCore invocation Latency** is available at 60 s periods with Average, Maximum, SampleCount and percentiles: the S2 IT invocation shows 278,394 ms at 05:20Z; the other five IT invocations that hour were 11.4 s, 18.8 s, 25.7 s and two (same minute as S2's) averaging about 48 s; hourly p50 20.2 s and p90 270 s. `AWS/Bedrock-AgentCore` also publishes per-tool `tools/call` latency for the AWS AgentCore Gateway (e.g. `evidence-lookup___get_evidence`). | Logs Insights on `aws/spans`; `get-metric-statistics` (60/300/3600 s, p50/p90); `list-metrics` | Per-call duration measures the model/platform; invocation latency measures agent behaviour (loops). D3, D9 |
| F7 | **The ledger (`audit-store.py`)**: `POST /records` appends **any JSON object** to `/data/audit-trail.jsonl`; `ts` is `setdefault` (the writer may set it); `seq` = the store's epoch milliseconds; `GET /records[?cid=]` filters on `correlation_id` only; **no update or delete route**; reads are open; the token is compared with `hmac.compare_digest`. | [kit: `workshop-static/reference-impl/audit-store.py`] | It can hold our full record schema unchanged. D8, D12 |
| F8 | **WSParticipantRole** (all three attached policies read: `participant-permissions-policy-1`, `console-iam-policy-0`, and `ws-default-policy`, which holds only IAM reads, service-linked-role creation, PassRole on itself and a region deny): Logs Insights `StartQuery`/`GetQueryResults` and `FilterLogEvents`/`GetLogEvents` on `*`; `GetMetricData`; team-* DynamoDB / SNS / SQS / EventBridge / Secrets Manager / alarms; log groups `/team/*` (create, put, retention; no logs delete action in any of the three); CloudShell; S3 get/put/delete/list on `team-evidence-*`. Explicit Deny on `bedrock-agentcore` Create/Update/Delete, guardrail writes and IAM writes. | `iam get-policy-version` | The laptop (and CloudShell) can run every pull adapter. D11 |
| F9 | **The tools' Cedar policies** (customer-records, network-twin, runbook-lookup): `permit … unless {toolName not in [its own operation]} unless {resource.dataClassification == "restricted"}`. No `dataClassification` is set. Marking a tool "restricted" therefore turns off its only permit: every call to it, from every caller, is denied. | `kubectl get toolconfig … -o json` (policy text only) | Classification is all-or-nothing per tool. D10 |
| F10 | **`new-agent.sh` copies `agent-template/agent.py` over `~/agents/<name>/agent.py` on every run** (its step 1). Custom agent code is overwritten. The Module 7 path (`build-agent-image.sh` + `make-agentcore-agents.py`) builds arbitrary source. | [kit: `starter/new-agent.sh`] | D7 |
| F11 | **The AWS-written `InvokeAgentRuntime` records** in `/aws/bedrock/aict-invocations` have **empty `requestParameters`** (no session id, no CID). They carry `eventTime`, `eventID`, `requestID`, `userIdentity` (WSParticipantRole), `sourceIPAddress` and `resources` (runtime ARN and endpoint). For the S1 swap run: customer 05:48:09Z, IT 05:48:35Z, network 05:48:49Z. | Logs Insights on `/aws/bedrock/aict-invocations` (key names and ARN suffixes only) | WHO-invoked joins a run by runtime ARN + time window, not by id. D12. **(corrected 2026-10-05 after live re-check: only the empty `requestParameters` holds. `responseElements` carries the caller-sent `runtimeSessionId` (`<CID>-<hex>`), `traceParent` and `baggage` (`modaas-correlation-id=<CID>`) on all 28 records, so WHO-invoked joins a run exactly by CID and session id; `eventTime` is the call's end. Only the model-call records (`Converse*`) carry no ids. See `10-f11-resolution.md`.)** |

---

## 3. Scoring keys and the effort model

**Fit codes** (each maps to `02-requirements.md`):

| Code | Criterion | Id |
|---|---|---|
| A-2EP | "Would it survive a second enforcement point?" | R-J-11 |
| A-REG | "Is the register out of the live path?" | R-J-12 |
| A-STL | "Is the evaluator stateless?" | R-J-13 |
| A-THR | "Does the control hold its own threshold?" | R-J-14 |
| LT | The live test: one control, one run or window, two minutes, no log trawling | R-J-10 |
| EV | Evidence bound to control, threshold version and run; verifiable by a stranger; gaps recorded | R-J-15 |
| HON | "One honest failure scores better than everything green" | R-J-16 |
| B-CTRL / B-CC / B-ADV / B-2EP | Bonuses: extra controls; continuous compliance; adversarial testing; second EP | R-J-17 … R-J-20 |
| L-DATE / L-PART / L-SELF / L-RETEST / L-OWNTHR / L-PATH | LOSE: undated or late threshold; records covering only some governed actions; evidence only we can verify; finding closed without a passing re-test; a control that stores its own threshold; a design that only works in the request path | R-J-21 … R-J-26 |

**Effort model** [R-D-03]:
- **Fleet hours:** agent-hours of offline work (code, tests, documents) that parallel workers can share.
- **Live hours:** the single serialized lane, one action at a time, each with the user's OK: agent builds, applies and approvals; runs; Cedar edits; S3 writes; ServiceNow writes.
- **Clock-bound:** waits that more staff can't shorten.
- **Budget:** 2.5M tokens/h and 100 model req/min, account-wide [handoff §3d]. S1/S3 runs cost 25–50K tokens; the reference S2 run cost 1,999,001 (80% of an hour) [handoff §5.6].

**Critical path (estimate, UTC, 2026-10-05/06):**
1. ~21:00–22:00: the captain decides D2/D5/D7/D9 values and the agent plan.
2. ~21:30–01:30: the fleet writes agent code and adapters (D2, D7, D12); in parallel the pull adapters, stitcher, evaluators and query tool (D1, D3, D4, D8).
3. ~01:30–02:30: live lane: dry runs, 3 builds, applies, approvals, smoke runs (D7).
4. ~02:30: freeze the register (D5): S3 write-once object + owner approval. Must come before the first assessed run.
5. ~02:45–03:45: C9 baseline runs (D3), then a register version with the frozen baseline if that route is chosen.
6. ~03:45–06:00: named runs (D9), the S2 BREACH last, then about 1 h of ceiling recovery.
7. ~06:00–09:00: snapshot, stitch, assessments, findings, ServiceNow notify/check (Arth), pack, HTML, MANIFEST, redaction, submit dry run.
8. ~09:00–11:00: two rehearsals [slides p26]; final re-snapshot and submit; buffer until 15:00.

---

## 4. The decisions

### D1 · The app: form and hosting of the dashboard and its backend

**The question, inside the frame.** The dashboard is a view; its backend is the control test / query tool, which queries the one evidence store through the stitcher [R-P-04]. It needs three views: the evidence ledger, the control test and the six auditor questions [R-P-05]; offline [R-P-06]; no public endpoint [R-P-07]. To choose: the front end's form, where it runs, and whether it reads the live store or an exported snapshot.

**Options**
1. **D1-A · CLI only, over an exported snapshot.** `prooflab query --control 16 --run <CID>`, `--control 9 --window <T1>..<T2>`; Python 3.9+ standard library; no network. The kit's own shape (`evaluate.py`: one verdict, exit 0/1/2) [kit: evaluate.py].
2. **D1-B · CLI + one static, self-contained HTML file** rendered by the same code from the same snapshot. Data inlined, so it opens from the zip with no server. It shows every named run, every run and closed window in the event window, and the three views; raw files are linked by relative path.
3. **D1-C · CLI + a local web app** (`prooflab serve`, standard-library HTTP server bound to 127.0.0.1) over the snapshot, recomputing any window on demand.
4. **D1-D · Served from the workshop IDE** (code-server's port proxy), over the live store.

**Evidence**
- "Your control test tool … A command line, a script, an API, a small app. We type the question; you do not narrate the answer." and "We name one control and one run. You drive your own tool." "Your evidence file … Exported, openable by us" [slides p26]. Transcript: "can you please show me what your AI system did for this particular time window? So you will use your tool to query the data" [transcript].
- The judges read the team bucket; `submit.sh` zips `~/evidence/` plus `register.yaml`, `gap-list.md`, `run-ids.txt` and the sketch [handoff §2.4; kit: submit.sh]. The bucket blocks public access [F1], so the dashboard travels inside the zip; it can't be a hosted page.
- "A dashboard: sees everything, can refuse nothing" [slides p12]: present the app as the query tool's view, never as an EP.
- Against D1-D: the IdeUrl is a bearer link that must never be shared [handoff §8]; the IDE role can't run Logs Insights [F2]; SSM to the IDE is denied to our role [mem: workshop-progress]; the account is destroyed at the end [kickoff deck p8].
- Browser behaviour (general, not tested here): a page opened from `file://` can't `fetch()` sibling JSON in Chromium-based browsers, so the data must be inlined or loaded with `<script src>`.

**Fit**

| Code | Best | Why |
|---|---|---|
| LT | B (C if built) | Precomputed answers on one screen; the CLI for any other question |
| EV, L-SELF | B | A stranger opens it from the pack without us; the CLI lets them recompute |
| A-STL | A = B = C | The tool recomputes from the snapshot and the frozen registry; the HTML shows outputs stamped with tool version, register version and snapshot hash |
| HON | B | Gaps and INDETERMINATE are shown per scope |

**Effort.** A: fleet 3–4 h. B: + 3–4 h. C: + 1–2 h. D: not recommended. Live: about 0.25 h to render on the final snapshot; rehearsals are counted in the critical path.

**Risks**
- Staleness: every screen must show "as of <snapshot time>".
- Size: the PDP logs are about 45K lines; link raw files instead of inlining them.
- Arbitrary T1..T2 roll-ups in static HTML would duplicate the evaluator in JavaScript. Keep roll-ups in the CLI; the HTML shows the per-run and per-window grid.
- The CLI needs Python on the judge's machine (standard library only).
- The pack must not carry secrets (redaction pre-flight, D10).

**Recommendation (not decided):** D1-B. The CLI is the authoritative control test; the HTML is its rendered view for judges reading the bucket. During judging, query a snapshot, never the live store; `prooflab refresh` pulls, stitches and writes a new snapshot with an as-of stamp. Add D1-C only if fleet time is left.

**Captain:** not for the build. Yes for what goes into the upload (an S3 write by `submit.sh`) and its redaction sign-off.

---

### D2 · C16: the floor, the one in-path question, the tally

**The question, inside the frame.** Settled: post-run C16 over `aws/spans` is the floor; the check before each model call is the bonus and the only question that may make work wait; the threshold is a frozen, version-stamped copy loaded beforehand; the tally lives in the adapter and travels with the run; the evaluator is stateless. To choose: the inline rule, the tally's source and carriage, what a DENY does, how post-run reconciles, and which transport does what.

**Options**
1. **D2-A · Floor only.** A `pull()` adapter runs Logs Insights on `aws/spans` by run id (`listener = "llm"`; sum input + output tokens; count by run id, not by trace) and feeds the evaluator, which writes an assessment and, on breach, a finding. C16 is labelled post-run.
2. **D2-B · Floor + inline "check, then commit".** `AfterModelCallEvent` adds each call's usage to the tally; `BeforeModelCallEvent` asks `evaluate(tally ≤ cap)`. Overshoot of up to one call, declared in the register's measurement basis.
3. **D2-C · Floor + inline "reserve, then commit".** `BeforeModelCallEvent` asks `evaluate(tally + bound ≤ cap)`, where bound = `projected_input_tokens` + the call's `max_tokens` (500 in the kit and the reference agents); `AfterModelCallEvent` commits the actual usage. The call that would cross the cap is cancelled.
4. **D2-D · As C, plus a scheduled pull** of the same evaluator over spans about every 60 s during runs. It only records, but it shows verdicts forming during the run, including for agents without our adapter (the reference trio).

**Common to B–D**
- **Tally source:** the agent's own per-call usage from the gateway's streamed response (Strands asks for `include_usage`; `accumulated_usage` sums it) [F5]. Per call, the agent's `chat` spans matched the gateway figure on 9 of 9 calls [mem: workshop-progress, Module 8].
- **Carriage:** the orchestrating script seeds the tally at 0 and passes `{run_id, tally_tokens, tally_calls, register_version, register_sha256}` in each agent's payload; the agent returns its updated tally, and the script records the handoff and forwards it. The reference agents return no usage [mem: reference-agents-facts], so this needs our agents (D7).

**Transports (one contract)**
- `evaluate()`: an in-process call from the model-call hook (slide 14's "sidecar / SDK: interceptor in the process").
- `emit()`: one decision record per check (ALLOW/DENY, tally, bound, cap, version) and one usage record per call, sent off the path through a non-blocking queue.
- `pull()`: the post-run test over `aws/spans`, at least 60 s after the run ends (ingestion lag 2.6–7.1 s [F6]); D2-D adds a loop.
- `callback()`: BREACHED → finding → ServiceNow incident to the owner; the response or the silence is recorded; nothing waits on it.

**Ruled out by evidence** (so not options):
- Reading `aws/spans` or `/modaas/evidence` from the runtime: no logs read [F3], and spans arrive seconds late [F6].
- A gateway `extAuth`/`extProc` policy: the admission policy refuses participant writes in `agentgateway-system` by its text [handoff §5.9].
- A ModelConfig `external` enforcer: not wired [F4].
- Cedar: no token attributes, stateless [handoff §5.1].

**Evidence**
- C16 is "In transaction: Checked mid-action, before it completes … The gateway asks before the call, and can halt the run" [slides p7]. "Only the enforcement point may make the work wait, and only for one question." "Race: two calls both read 9,800 under a 10,000 cap and both pass. Reserve, then commit." [slides p14]. The test: "Reconcile usage; sum each run. Compare with cap; check stop records"; the evidence: "Call IDs, token counts, budget version and stop records" [slides p20]. Evaluator vs tester [slides p13].
- Figure of record: the gateway per-call line; durably in `aws/spans` by run id for 30 days (S2 353 spans = 1,999,001 tokens; S1 24 = 37,664) [verify-live; handoff §5.3].
- S2 looped 174 model calls inside one IT invocation, about 11.4K input tokens per call on average (1,992,059 / 174) [handoff §5.6]. A model pause took 33–41 s on nano-9b [handoff §5.7]. Only a per-call check stops such a loop in time.
- The hook API exists in the pinned build [F5].

**Fit**

| Code | A | B | C | D |
|---|---|---|---|---|
| B-CC (verdict formed inline, in the path) | no | yes | yes | yes, also visible during the run |
| A-STL | yes | yes (the tally is adapter state) | yes | yes |
| A-THR / L-OWNTHR | frozen file | frozen, version-stamped copy | same | same |
| L-PATH | — | avoided (post-run floor) | avoided | avoided |
| Slide 14's race rule | — | not met (overshoot ≤ 1 call) | met within a run (calls are sequential) | met |
| A-2EP / B-2EP | — | same evaluator inline + post-run (D6) | same | same + scheduled pull |

**Effort.** A: fleet 3–4 h (evaluator 1 h; spans pull + reconciliation 2–3 h). B/C: + 4–5 h (hooks, tally carriage, emit queue, tests against a stub model). D: + 1 h. Live: rides on D7's builds, plus 2 test runs (0.25–0.5 h). Clock-bound: the cap, and any tiers, frozen before the first assessed run.

**Risks**
- `projected_input_tokens` may be None; fall back to the last call's input tokens + `max_tokens`. How a cancelled call surfaces in the agent's result is untested in our build; test it locally with a stub model first.
- Hidden retries: the OpenAI Python client retries by default (an SDK default, not checked in our build). The gateway charges every attempt. Set retries explicitly, or count them in `AfterModelCallEvent`.
- The tally travels in the payload, so an altered payload could reset it. The floor uses the gateway figure, so a forged tally can't turn a breach into a pass post-run; record the discrepancy as a finding.
- A DENY leaves the agent's answer incomplete. The agent must return a recorded disposition (for example escalate, reason "budget"): agent behaviour, emitted.
- "A denied attempt is not an actual breached run" [prior design §6; a definitional rule, not a platform claim]: the inline demo is a PASS with a stop record, not the BREACH (D9).

**Recommendation (not decided):** D2-C. Add D2-D's scheduled pull only if the fleet has spare hours. The post-run result over `aws/spans` is the verdict of record; the inline tally is reconciled against it call by call by action id, and any mismatch is a recorded finding.

**Captain:** yes. The cap values and tiers (strategy and the owner's sign-off), the agent deploys (cluster writes, D7) and the test-run budget.

---

### D3 · C9: metric, statistic, window, baseline, alerting

**The question, inside the frame.** C9 is a `pull()` adapter feeding a stateless evaluator, with the baseline handed out as part of the frozen registry version; each crossing raises a finding through `callback()`. To choose: metric, statistic, window, baseline, how alerts fire.

**Options: metric**
1. **M1 · AgentCore invocation Latency per runtime** (`AWS/Bedrock-AgentCore`, `Name=<runtime>::DEFAULT`). AWS-written; 1-min resolution; percentiles available [F6]. It catches agent behaviour drift: the S2 IT invocation took 278 s against 11–48 s for the other five IT invocations that hour [F6]. It joins a run by the run's time range, not by id.
2. **M2 · Gateway per-call duration** from `aws/spans` (`durationNano` by run id and model) [F6]. Durable, joins by run id. It measures the model and platform, not loops: it stayed flat through S2 (average 2.0 s, max 4.55 s).
3. **M3 · Judgment quality:** the disposition match rate against the scenario's expected disposition (`network-inventory.json` `grading.expect_disposition`: S1 auto-resolve, S2 gather-evidence, S3 escalate). This is the shape of the slide's C9 example ("Diagnostic response score, baseline 0.900 frozen" [slides p7]) and of the kit's C9 placeholder [kit: register.yaml]. It needs several runs per window, and its input is agent-written.

**Options: statistic.** Average (it showed S2: 71.6 s vs 8.2–8.5 s for the other runtimes, but it dilutes one long invocation); **Maximum** (strongest for runaways, sensitive to one outlier); p90 (available); plus **Errors Sum** (it stayed 0 through S2) and **SampleCount** (an expected invocation with no data is UNKNOWN, not healthy) [corr row 8; slides p22].

**Options: window.** W1 closed UTC hours (Module 8 style; hours without traffic are UNKNOWN; the per-run question becomes "the window that contains the run"); **W2 per run**: the run's time range, start to end + 60 s, per runtime, so "was control 9 satisfied for run FM-B?" is answered directly; W3 fixed batches of N runs (for M3).

**Options: baseline.** B-a: ≥ 6 post-freeze runs of the final ifabric agents (2 per scenario), declared before the C9 assessed runs. B-b: earlier exploratory hours (reference agents, mixed IT models: not comparable [handoff §3a item 1]).

**Options: alerting.** Every crossing → one finding (`scope_kind` run or window) → ServiceNow incident to the owner → response or silence recorded. Missing data → an INDETERMINATE `monitoring-gap` finding. Bound the incident count with the owner (the reader's flood concern) [handoff §4.3].

**Evidence**
- C9 is "Continuous: A live measure watched against a frozen baseline, with a named owner who responds. MEASURE: relative drop from the baseline, per comparable window" [slides p19]. "A missing measurement is not zero drift. Track expected windows and data availability separately." [slides p22]. The challenge page: "AgentCore metrics (Latency, Errors per runtime) are the drift signal, one clock hour at a time" [platform contract].
- The finish-line question is per run: "was control 9 satisfied for run FM-B?" [slides p23].
- Fast is not healthy: a refused run returned in 1.05 s [mem: prooflab-project].

**Fit**

| Code | M1 | M2 | M3 |
|---|---|---|---|
| LT (per-run question) | W2 answers it | by run id | needs batches |
| EV, L-SELF | AWS-written metric | gateway-written spans | agent-written disposition |
| BREACH lever exists (D9) | yes: the S2 runaway; a declared injected delay | unproven (n = 2 nano calls) | yes: reference agents on S2 |
| Independent of C16 | no: S2 breaches both | yes | yes |

**Effort.** M1/M2 pull adapter: fleet 2 h; evaluator: 1–2 h; M3 adds scoring (2 h) and more runs. Live: baseline runs 0.5–1 h (6 × about 40K tokens). Clock-bound: W1 needs ≥ 3–6 traffic hours after the agents freeze; W2 needs only the baseline runs.

**Risks**
- Per-run attribution of 1-min datapoints needs runs that don't overlap; keep a ≥ 1 min gap (runs are serialized anyway).
- AgentCore cold starts can produce a single slow invocation: include cold and warm runs in the baseline, or declare a first-invocation rule.
- The baseline must exist before the C9 assessed runs. Either declare the baseline procedure in register v1 and its computed value in a v1.1 dated before the C9 assessed runs, or wait to freeze C9 until the baseline exists.
- With M1, one S2 run breaches C9 and C16; that's fine, but say it.

**Recommendation (not decided):** M1 with Maximum per runtime, plus Errors Sum and SampleCount for coverage; window W2, with an hourly roll-up for window questions; baseline B-a; limit = relative increase over the baseline per runtime, with the number and the violating-run allowance set by the owner (the slide's example is ≤ 10% and 0 violations). Record M2 as a diagnostic that separates "platform slow" from "agent looping". Choose M3 instead only if the captain wants C9 independent of C16.

**Captain:** yes. The metric (strategy) and the baseline spend (live runs).

---

### D4 · C7: expected events, event set, gap measurement

**The question, inside the frame.** C7 is an assessment over the one store: expected events from a source outside the graded agent, against the records the acting adapters emitted. To choose: the expected source, the event set across the three agents + gateway, the gap rule.

**Options: expected source**
1. **E1 · Gateway actions + a declared workflow spec.** From `aws/spans` by run id: one expected `model.call` per model span and one `tool.call` per MCP `tools/call` span (by action id). From a workflow spec frozen in the registry: `run.started`, one handoff per agent (script → agent), `invocation.received`, `intent`, `result-inspection`/judgment per agent, an escalation record when the disposition is escalate, and `run.finished`. Refusals come from `/modaas/evidence` DENY records with the CID, and the pause 404 by trace id [handoff §5.2].
2. **E2 · Scenario definitions only** (`network-inventory.json` → agents and phases).
3. **E3 · The twin** (sites and predicted RSRP) [mem: prooflab-project plan item]. It can't produce events on demand, and S2 has no site [corr row 5; gap 10].
4. **E4 · The kit's shape:** distinct phases per CID / 3 phases per agent [kit: register.yaml]. Derived from the agent's own contract; weak independence.

**Observed set.** Records in the store with `record_kind` ∈ {action, decision, handoff, lifecycle, judgment} whose `emitter` is the acting adapter (our agent runtime or the orchestrating script), written at action time and matched by action id (actions) or by agent and phase (lifecycle). **Records back-filled by pull adapters (`record_kind: observation`) are excluded** from the observed set; they are evidence for the expected side. Otherwise coverage is 100% by construction.

**Options: gap rule**
- **G-a:** the gap between consecutive *expected* events in one agent invocation stream, on the agent runtime's clock (`emitted.at`). A missing middle event makes both adjacent pairs unmeasurable [PB §3.4]. It catches stalls and hangs (a Hostile "delay").
- **G-b:** recording latency per action: the record's time minus the gateway span's end. Across two clocks (gateway pod vs agent or store), with unmeasured skew.
- **G-c:** G-a judged, G-b reported as a diagnostic.

**Evidence**
- "control 7 coverage needs 'expected' defined outside the graded agent" [kickoff deck p21, via mem: prooflab-project]. "MEASURE: expected-event coverage, and the gap between consecutive events" [slides p19]. "A gap test checks timing, not completeness. Define the event stream and the expected event list separately." [slides p22]. Expected events from "scenario definition, workflow spec or twin" [PB §3.4].
- The reference ledger has no action ids; S2's 353 gateway spans became 16 ledger records [handoff §5.4; notes #44]. The slide example's 5 ms gap makes no sense with 2 s model calls [F6]; G must come from our baseline.
- Spans include MCP session set-up (S2: 179 MCP spans for 170 tool calls) [mem: workshop-progress]. Whether `aws/spans` carries the MCP method needed to drop `initialize`/`tools/list` is UNVERIFIED.

**Fit.** L-PART is exactly what C7 measures: every model call, tool call, handoff and escalation in scope. EV: the expected side is gateway-written. A-STL: a pure function of (store snapshot, spans capture, registry version). B-ADV: G-a catches an injected delay; a dropped record breaches coverage.

**Effort.** Fleet: expected-set builder from spans 2–3 h; workflow spec 1 h; coverage and gap evaluator 2 h; the agents' action-id capture is in D7. Live: none beyond the runs in D7/D9.

**Risks**
- Capturing the action id from the `x-modaas-action-id` response header on *streaming* responses is UNVERIFIED (it was seen on a non-streaming call) [mem: platform-verified-facts].
- Session set-up spans inflate the expected set if not filtered.
- Refusals carry no run id on the gateway line; they need the trace-id join through `/modaas/evidence`, so our agents must propagate the run trace (D7).
- The reference agents fail C7 trivially (no per-action records). That is a natural BREACH, but only in scope if the register names that version (D9).

**Recommendation (not decided):** E1, with the observed set limited to adapter-emitted records; G-c with G-a judged. Target 100% coverage; the gap limit and the tolerated share come from the baseline runs and are frozen in the registry.

**Captain:** values only (owner sign-off). No writes beyond D7.

---

### D5 · The control registry: source of truth, hand-out, date proof

**The question, inside the frame.** A versioned registry hands out a frozen, version-stamped copy loaded beforehand and is never called in the path. To choose: the source of truth, how the copy reaches each adapter, and what timestamp a stranger can check.

**Options: source of truth.** `register.yaml` in the kit format, extended with the four justifications per threshold, the C-FM-01 tree, owners, applicability (which agent versions count), the C7 workflow spec and the C9 baseline procedure [PB §3.1; slides p10]. Frozen as `register/<version>.yaml` with its sha256. No other choice is credible; the options are in the next two parts.

**Options: hand-out of the frozen copy**
- **H1 · Env at deploy:** `REGISTER_VERSION`, `REGISTER_SHA256` and the C16 value(s) in the AgentConfig env, from the frozen file. Loaded at container start; can't be changed by a payload. A new version needs an env patch: the runtime re-programs in about 24 s, with no new image and no re-approval [gap 5].
- **H2 · Run envelope:** the orchestrating script reads the frozen file at run start and passes version, sha256 and value in the payload. No redeploy, but the payload is caller-supplied.
- **H3 · ConfigMap** `ifabric-register-<version>` in `components`, mounted and read at start. A cluster object to maintain; no advantage over H1.
- **H4 · File load:** post-run adapters, the stitcher and the query tool load the frozen file (and check its sha256).

**Options: stranger-checkable timestamp**
- **T1 · A write-once object in the versioned evidence bucket** (`register/<version>.yaml`, uploaded before the first assessed run, never rewritten). S3 sets `LastModified` and a VersionId; an overwrite creates a new version and can't backdate; earlier versions persist 7 days after becoming noncurrent; the PUT is in the server access logs, which participants can't touch; the IDE role and the organisers can list versions [F1]. Capture `head-object` right after upload, and an IDE-run `list-object-versions` export for the pack.
- **T2 · A ServiceNow record approved by the owner:** server-set `sys_created_on`/`sys_updated_on`, with the owner's identity and the register's sha256 in the text. It also gives separation of duties [slides p5, p8; PB §3.1; SN handoff §14].
- **T3 · A git commit:** commit dates are self-asserted, and the repo is private, so judges can't see it.
- **T4 · The platform `Registry` CRD:** 0 instances; built for asset registries with reachability phases [mem: platform-verified-facts]; 5 CEL rules; gone at teardown; EKS audit logging is off.
- **T5 · A CloudWatch Logs record** under `/team/…`: AWS-set ingestion time and no delete action found for participants [F8], but gone at teardown and checkable only while the account lives.

**Evidence.** "Versioned and dated before any assessed run — we check the date" [slides p23, p26]. "Control register … Hands out the current version. Never in the path." [slides p15]. "The control register is never in the path of execution that will delay the system" [transcript]. "A threshold range chosen after seeing the result is a description of what you got, not a test. The version date on your threshold document is how anybody tells the difference." [slides p10]. The bucket facts are in [F1]; they supersede [corr row 15] on versioning.

**Fit.** L-DATE: T1 (AWS-set) + T2 (ServiceNow-set) beat T3. A-REG: H1/H4 read before the run, never per call. A-THR, L-OWNTHR: the adapter holds a version-stamped copy whose sha256 is in every decision record, so the value is visibly the registry's, not the control's. HON/R-D-02: T2 records an approval by someone other than the builder, if the roles allow it.

**Effort.** Register content: 1–2 h of the owner's time + 1–2 fleet hours drafting justifications from the measurements. Freeze tooling (sha256, upload, `head-object`, verify): fleet 1 h. Live: 0.25 h (one S3 PUT; the ServiceNow record via Arth or Sree). Clock-bound: before the first assessed run (and, for C9, before its assessed runs).

**Risks**
- Rewriting the same key creates a new version that may confuse a reader. Use one key per version and never touch it.
- Noncurrent versions expire after 7 days (judging falls inside).
- Only the IDE role can list versions; Claude can't drive the IDE (SSM denied), so a person runs one read there.
- ServiceNow adapter bug (b) can misreport the owner's response [handoff §4.3]; read the record directly.
- H1 bakes a value into env: say in the architecture that it is a version-stamped copy of the registry, not the control's own threshold.

**Recommendation (not decided):** `register.yaml` → a frozen file + sha256. H1 for the in-path C16 copy, with the script also stamping version and sha256 in the run's first handoff record, and H4 everywhere off the path. Date proof: T1 + T2. Git stays the working copy only.

**Captain:** yes. The S3 write, the ServiceNow record, the owner's approval and the threshold values.

---

### D6 · The second enforcement point: which pair shows "moved, nothing rewritten"

**The question, inside the frame.** The captain prefers: the same C16 evaluator used inline in the agent runtime **and** post-run over spans. To choose: whether that pair stands alone, how to prove "nothing rewritten", and whether to add placements.

**Options**
1. **D6-A · The captain's pair.** EP1 is the model-call adapter in our runtime (`evaluate()`; it can refuse). EP2 is the post-run adapter on the managed gateway's log (`pull()` over `aws/spans`; it observes). One module `c16.evaluate()`, imported by both adapters, with the same sha256. An adapter-diff note lists which adapter file changed and that the evaluator didn't.
2. **D6-B · A + a scheduled near-real-time pull** of the same evaluator over spans (about every 60 s), a third placement of slide 14's "scheduled batch job" kind. Records only.
3. **D6-C · A + the judge's own re-run:** the same evaluator executed from the pack on the judge's machine (D1's CLI): "moved" to a stranger's machine. Free.
4. **D6-D · A platform Cedar rule** configured on an `ifabric-` ToolConfig. A refusing EP, but the platform's engine, not our evaluator (Cedar can't see tokens). It counts for D10 and the adversarial log, not as "the same architecture, moved".

Ruled out by the correction: refusing handoffs, a second waiting question at tool calls, and a human approval queue that holds work.

**Evidence**
- "If the second one forces a rewrite, you built an integration." The EP kinds one design must reach include "Managed gateway: no code of yours in it, read its log" and "Scheduled batch job: no request to sit inside" [slides p14].
- Bonus wording: "the same architecture, moved, with nothing rewritten" [slides p25]; "The second or more enforcement points: running, with a note of what you had to change" [slides p26].
- The open question "can EP2 actually wait or refuse?" [handoff §3b Q11; corr row 12]: EP2 here cannot, by design; only our runtime can refuse [handoff §5.9].

**Fit.** B-2EP and A-2EP: A meets the wording; C adds a stranger's machine at no cost. L-PATH: the post-run placement shows the design works outside the request path.

**Effort.** A: fleet 0.5–1 h (the note, a sha256 check in CI, one rehearsal step: run the post-run adapter right after the inline-stop demo). B: + 1 h. C: 0 (comes with D1).

**Risks.** A judge applying "ask, wait, act" may read EP2 as "just post-run evaluation". Mitigate by naming its slide-14 kind, labelling it observe-only, and showing both placements live with the same evaluator hash.

**Recommendation (not decided):** D6-A + D6-C; D6-B if the fleet has spare hours; D6-D only as an adversarial case.

**Captain:** no (documentation and rehearsal), beyond D2's own asks.

---

### D7 · Agents: fix or build, models, the IT revert, judgment and evidence emission

**The question, inside the frame.** Our agent runtime is the only team code in the path [R-C-01]. Agent judgment is agent behaviour recorded by `emit()`; it is not a registry `evaluate()`. The orchestrating script records handoffs; agents don't call each other.

**Options: fix or build**
1. **G1 · Fix the reference agents in place:** rebuild the same three CRs from a patched copy. Keeps the names every team shares in AICT; loses the "before" system.
2. **G2 · Build our own `ifabric-` trio** (`ifabric-customer`, `ifabric-it`, `ifabric-network`), cloned from `reference-agent/agent.py` with our adapters, through the Module 7 path (F10 rules out `new-agent.sh` for custom code). Keep the reference trio untouched as the "before" system and the source of natural breach runs (D9).
3. **G3 · G2 + an orchestrator agent** on AgentCore. Unnecessary under the correction: handoffs only record, and the script can emit them.

**Options: model per agent.** All `nemotron-super-120b` (most of our measurements; consistent; the bigger model for judgment); IT on `nemotron-nano-9b` (tokens per call are the same on both, so it saves cost only [mem: challenge-requirements]); `nemotron-nano-3-30b` (unmeasured).

**Options: reference IT revert** (now on nano-9b since 05:47Z; S2's loop happened on super-120b). Revert, setting both `dependsOn.models[0]` and `modelRef` consistently [handoff §3a item 1]; or keep it and record it as version 2. With G2 this matters only for the reference runs used in D9.

**Options: judgment** [PB §1.7, §3.8; gaps 1 and 10]
- J1 prompt rules only;
- **J2 structured output** (disposition ∈ {auto-resolve, gather-evidence, escalate}, deciding evidence, reversible step, reason), parsed and validated by code, plus deterministic precedence rules: a maintenance freeze in the constraints → escalate; empty tool evidence ("no twin data") → gather-evidence; resolve element ids to site ids before asking the twin;
- J3 = J2 + a risk-tier table (the judge's risk-matrix hint) that selects the action mode and a C16 cap tier, declared in the registry.

**Evidence emission (fix list for our agents)**
- the action id per model and tool call (from the `x-modaas-action-id` response header, via an httpx response hook);
- tokens, model and `finish_reason` per call; a guardrail block (`content_filter`, 0 tokens) recorded as BLOCKED;
- the true refusal status (tool 403 vs pause 404 vs 5xx), not "500 on the model";
- the inbound run trace, so ledger trace ids equal the run trace;
- one tool record per actual tool call (`Before`/`AfterToolCallEvent`), not after the model call;
- C16 decision and stop records; judgment records; `ts` with its clock;
- no keyword-guessed disposition.

[mem: reference-agents-facts; notes #19–#21, #43; gap 4]

**Evidence.** "Give the reference agents the judgment to gather evidence or escalate" [kickoff deck p23]; "ALLOWED: Building more or changing the agents" [slides p23]; "Clone rather than modify shared examples"; "Creating additional agents … does not itself earn bonus points" [brief]; names `ifabric-…` (≤ 40 characters; `--dry-run` first) [corr row 9]; the self-check fails by construction on the reference agents [corr row 4].

**Fit.** The "close the gap" pillar; L1 foundation (governed Nemotron); C7's observed side (D4); B-ADV (validated structured output resists tampered prompts); EV.

**Effort.** Fleet 6–8 h (the clone, emission fixes, judgment J2; shared adapters counted in D2 and D12). Live 1–1.5 h: 3 dry runs, builds (about 1–1.5 min each), applies, approvals, READY waits and smoke runs; the IT revert about 0.1 h.

**Risks**
- Each new agent version is a C9/C16 treatment: freeze the agents before the baseline and the register [handoff §3a item 2].
- Approvals are self-asserted [gap 5].
- New runtimes show up in AICT after about 20 min [SN handoff §9].
- Our agents' spans will also carry prompts and customer data unless span content capture is turned off (setting UNVERIFIED in our build) [gap 9].

**Recommendation (not decided):** G2, all on super-120b, with the orchestrating script as the run driver and handoff recorder (no G3). Judgment J2 (J3 if there is time). Revert the reference IT agent only if the reference S2 run is chosen as the BREACH (D9).

**Captain:** yes. Cluster writes (3 AgentConfigs, approvals), the model choice and the IT revert.

---

### D8 · The one append-only evidence store

**The question, inside the frame.** One append-only store holds every decision record from every adapter. To choose: the physical store, the pack layout and formats, and how raw sources stay verifiable.

**Options**
1. **S-A · The platform ledger (`audit-store`)** as the one store. Every adapter can reach it: the runtimes have `AUDIT_URL` and the token in env; the laptop reaches it through the cluster's service proxy or a port-forward. It accepts any JSON object, appends to one file, has no update or delete route and stamps its own `seq` [F7]. It is the "Audit ledger" the L2 gate names [judging slide].
2. **S-B · CloudWatch Logs:** AWS-set ingestion time, and no delete action found for either role [F3, F8]. But it splits by writer: the runtimes can write only `/aws/bedrock-agentcore/*`, the laptop only `/team/*`. Two groups, not one.
3. **S-C · Objects in the versioned evidence bucket** [F1]: the runtimes have no S3 permission [F3], so only laptop and IDE adapters could write.
4. **S-D · A team-* DynamoDB table:** laptop/IDE only; participants can delete items; not append-only.
5. **S-E · S-A + an AWS-timestamped mirror:** runtime adapters also write each record to `/aws/bedrock-agentcore/ifabric-evidence`, laptop adapters to `/team/ifabric-evidence`; the stitcher matches the copies by `record_id`.

**Pack layout** (for any option): records as JSONL, one object per line (schema D12); raw captures byte for byte, each with a capture manifest (query string, time range, query id, capture time, row count); a derived index (SQLite or JSON) that the query tool rebuilds and never treats as the source; `MANIFEST.json` with SHA-256 per file; the ServiceNow `delivery-log.jsonl` mirrored into the store as `notification` records [SN handoff §8.3].

**Evidence.** "The evidence ledger never interprets" [slides p15]. Gap 6: the token is readable by every participant, the writer sets `ts`, there is no verify route, and the volume is deleted with the stack [handoff §5.4, §7.6]. INTEGRITY rests on cross-surface corroboration plus a MANIFEST [corr row 2].

**Fit.** EV, L-SELF: the raw captures, queries and MANIFEST let a stranger re-check; S-E adds an AWS-timestamped copy no participant can delete. L-PART: one store makes coverage measurable. A-STL: the store judges nothing.

**Effort.** S-A client (non-blocking emit queue, local spool and replay, schema validation): fleet 2–3 h. S-E: + 1–2 h. Export, MANIFEST and redaction: fleet 2 h. Live: about 0.25 h (verify writes).

**Risks**
- Anyone with the token can forge records [gap 6]; corroborate against the gateway figure of record and, with S-E, the mirror.
- `ts` is writer-set: always set it, and keep the store's `seq` (ms; can collide: order by `seq`, then `record_id`).
- Observer records in the same ledger could change `score-run.py`'s grade on a run. Give them their own `phase` value and re-test the grader on a mixed run.
- The volume dies at teardown: export before the end.
- The template's `post_audit` blocks for up to 5 s per record; under the frame, emits must not hold work. Use a background queue with a bounded flush at the end of the invocation.

**Recommendation (not decided):** S-A as the one store, plus S-E if the fleet has 2 spare hours (the runtime half is the most valuable). Pack as above; SQLite only as a derived index.

**Captain:** yes for S-E (creating log groups is an AWS write) and for the record volume written into the shared ledger. No for the local formats.

---

### D9 · Named PASS and BREACH runs per control

**The question.** Each completed control needs one PASS and one BREACH run, executed after registration under the same threshold, with ids written down before judging [slides p23, p26]. The twin switch can't produce them [corr row 5; notes #57, #58]. "A denied attempt is not an actual breached run" [prior design §6; a definitional rule, not a platform claim].

**Options**

| Control | PASS | BREACH options |
|---|---|---|
| C16 | ifabric S1 (or S3) under the cap | **B16-1** the reference trio on S2: the natural runaway (1,999,001 tokens measured, with IT on super-120b; IT is on nano-9b now, so revert first or accept that it may not reproduce; n = 1). **B16-2** an ifabric build in a declared observe-only mode: honest only if the register names it as a separate version. **B16-3** a run over its tier cap under tiered caps: depends on natural variance (S1 measured 25–50K). **B16-4** a runaway stopped by a kill switch: complex, timing-dependent |
| C7 | ifabric run: every gateway action has its record | **B7-1** any reference-trio run: no per-action records (S1: 12 ledger records for 24 gateway spans). **B7-2** an ifabric run in a declared fault-injection mode that drops one record (doubles as an adversarial case). **B7-3** the page's recipe, pausing a ToolConfig mid-run: whether it causes a miss depends on the expected-set definition |
| C9 (M1) | ifabric run inside the baseline band | **B9-1** the same reference S2 run (IT invocation 278 s). **B9-2** a declared injected delay in an ifabric test mode (Hostile "delays"). **B9-3** a model swap: effect unproven [F6] |
| Inline demo | ifabric S2 stopped at the cap by the C16 check: a **PASS with a stop record**, and the "verdict formed in the path" bonus [slides p26] | — |

**Evidence.** The measured runs [handoff §5.6]; "Do not move the threshold to make it pass" [slides p23]; the S2 run (05:15–05:20Z) came before the IT swap (05:47Z) [mem: workshop-progress]; the reference ledger shape [handoff §5.4].

**Fit.** MUST (two named runs per control); HON (the reference breaches are real); B-ADV (B7-2 and B9-2 double as adversarial tests); B-CC (the inline demo).

**Effort.** Fleet 0.5 h (`run-ids.txt` and the case renderer). Live 1.5–2.5 h: PASS runs about 0.25 h each and shareable across controls; the S2 breach about 10 min + about 1 h of ceiling recovery; test-mode builds ride on D7.

**Risks**
- Scope: if the BREACH runs come from the reference trio, the register's applicability must name both agent versions, or the breach falls outside the claim's scope.
- S2 may not loop again (n = 1).
- Budget: 80% of an hour's tokens.
- Natural variance under tiered caps.
- Every named run must come after the register freeze.

**Recommendation (not decided):** one shared PASS (ifabric S1) for C16, C7 and C9, and one shared BREACH (reference trio on S2, IT reverted to super-120b, run last), with the register naming both versions. Add the ifabric S2 inline-stop run as the live demo, and B7-2/B9-2 as declared adversarial complements if time allows. Fallback if S2 doesn't loop: B7-1 for C7, B9-2 for C9, B16-3 for C16.

**Captain:** yes. The S2 budget, the IT revert (cluster write) and run timing.

---

### D10 · Guardrail layers per enforcement point

**The question, inside the frame.** Each layer is an adapter at an EP. Our code refuses only through the C16 check. Everything else records. Platform layers refuse on their own; we configure them where allowed and record their real outcome.

| EP | Guard | Who refuses | Our transport | What we record | Build, configure or gap |
|---|---|---|---|---|---|
| Our runtime: model call | C16 check | **us** | `evaluate` (the one) | decision + stop records | Build (D2) |
| Our runtime: tool call | Declared-tools scope, argument checks, tool result treated as untrusted (evidence sufficiency, injected instructions) | nobody (records) | `emit` | out-of-scope or suspicious calls as findings | Build. Detects gap 3 and gap 10; doesn't prevent them |
| Our runtime: start-up | Fail closed when injected keys are missing (a precondition, not a control question) [R-P-13] | us (no work starts) | `emit` | start-up record | Build |
| Orchestrating script | Handoff records (from → to, payload digest, classification); tool Lambda `CodeSha256` vs the approved baseline; approval older than the running generation | nobody (records) | `emit` / `pull` | handoff, integrity and staleness records | Build. Answers gap 11 and gap 5 as detection |
| Gateway + PDP / Cedar | Tool policy | platform | configure ToolConfig `cedarPolicy`; record with `pull` (PDP pod logs, both replicas; `/modaas/evidence`) | DENY/ALLOW with policy id and version | Configure one forbid rule on an `ifabric-` ToolConfig for Hostile/Rogue tests [R-P-12] |
| `modaas-authz` | API key, fail-closed | platform | `pull` (`/modaas/evidence`) | DENY with reason | Observe |
| Bedrock guardrails | Prompt attack on input | platform | `pull` (gateway line: `content_filter`, 0 tokens) | **BLOCKED**, next to the platform's ALLOW | Observe; answers gap 4 in our store |
| Admission (CEL + VAP) | CR validity | platform | `emit` from our deploy wrapper (apply / dry-run output) + CR status `pull` | admitted or refused | Observe. `components` events last about 1 h [mem: platform-verified-facts] |
| Kill switch | Pause model or tool | platform | `pull` | requested vs effective time, the 404 | Observe [handoff §5.7] |
| Ceilings | 100 req/min, 2.5M tokens/h | platform | `pull` (gateway lines) | 429s, if any (untested) | Observe |
| Runtime IAM deny | No direct model or AgentCore-gateway call | platform | adversarial test record | AccessDenied | Observe |
| Ledger token gate | 401 without the token | platform | adversarial test record | 401 | Observe; gap 6 stays |
| ServiceNow queue | Human verdict | the owner | `callback` | delivery, response or silence | Build (Arth's adapter) |
| Pack pipeline | Secrets hygiene | us (blocks the upload, not agent work) | — | pre-flight scan result | Build: redact `cr-status.json`, check `tmf639.json` [handoff §3d] |

**Options**
1. **D10-A · Record-only + platform-configured.** As in the table: one Cedar forbid rule on an `ifabric-` ToolConfig, guardrails observed, our checks recorded.
2. **D10-B · A + our own ModelConfig with a stronger guardrail declaration.** The operator creates the guardrail at approval; it is a new model alias, so a new C9/C16 treatment; untested.
3. **D10-C · A + edits to shared ToolConfigs' Cedar** (customer-records etc.): they apply to every caller, and whether an edit resets approval is untested [corr row 1]. Classification is all-or-nothing: "restricted" turns off the tool's only permit for every caller [F9].

Excluded by the frame: blocking tool allowlists, pre-run refusals in our code, and the ModelConfig `external` hook (not wired [F4]).

**Evidence.** The platform EP table [handoff §5.9; contract-verify §2]; Cedar levers [mem: platform-verified-facts]; the tools' policy text [F9]; "treat tool results as untrusted in your agent" [platform contract, "Limits of this build"]; Hostile: "Detection, safe degradation, and unsafe actions denied" [kickoff deck p6, p8].

**Fit.** R-P-10: a table with no blank row and exactly one `evaluate()` row. B-ADV: Hostile "unsafe actions denied" is shown by platform layers (Cedar forbid, guardrail block) and by agent judgment, not by a second waiting question of ours. EV: real outcomes instead of the platform's ALLOW. HON: detection-only rows are labelled.

**Effort.** Fleet 3–5 h (tool-call checks, observation adapters, CodeSha256 and staleness records, pack redaction). Live 0.25–0.5 h (one Cedar edit and its test calls).

**Risks**
- An `ifabric-` ToolConfig over an existing AgentCore gateway target may expose the same tool name as the platform's; which policy the PDP then applies is UNVERIFIED. A custom tool through `new-tool.sh` avoids this.
- A Cedar edit might send the tool back to review (untested); an unapproved tool has no route and refuses every caller.
- Detection-only tool scope means gap 3 is detected, not prevented. Say so in the gap list.

**Stays a documented gap:** per-agent identity (gap 2), approvals self-asserted (gap 5), ledger integrity (gap 6), plain HTTP and the key in clear (gap 9), screening of tool output by the guardrail (untested), classification (all-or-nothing, F9), AICT Monitor likely empty.

**Recommendation (not decided):** D10-A. D10-C only for a named adversarial case with the user's OK; skip D10-B (time, and a new treatment).

**Captain:** yes for any Cedar edit (cluster write; a shared ToolConfig needs an explicit OK) and any new ModelConfig.

---

### D11 · Where adapters, evaluators, the stitcher and the query tool run; credentials

**The question, inside the frame.** No Lambda or IAM changes [R-C-11]. In-path adapters can live only in our runtime. Everything else is off the path and may run wherever it has the reads it needs.

**What each host can do**

| Host | Logs Insights on `aws/spans` | kubectl (PDP/gateway pod logs, CR status) | Ledger write | ServiceNow credentials | Notes |
|---|---|---|---|---|---|
| Our agent runtime | no [F3] | no | yes (env token) | must never hold them (AgentConfig env is readable by every participant) [notes #24] | in-path adapters only |
| Laptop (WSParticipantRole) | yes [F8] | yes | yes (service proxy) | yes (`read -rs`, a mode-600 file) | credentials expire (ExpiredToken about 18:20 UTC); `/tmp` token lost on reboot [handoff §0.4] |
| Workshop IDE (IDE role) | **no** [F2] | yes | yes | yes | Claude can't drive it (SSM denied); the only team role that can list bucket versions [F1] |
| CloudShell (participant role) | yes [F8] | after installing kubectl + kubeconfig | via kubectl | possible | sessions time out when idle |

**Options**
1. **P1 · Laptop hub:** the orchestrating script, pull adapters, stitcher, evaluators, query tool and ServiceNow callback all on the laptop.
2. **P2 · IDE hub:** persistent and where the SN handoff assumes, but no Insights, so the `aws/spans` pull can't run there [F2].
3. **P3 · Split:** runtime = model-call adapter and agent emits; laptop = everything else; IDE = human-run reads only (the bucket version listing for D5, and the ServiceNow terminal if Arth's credentials live there); CloudShell = fallback for pulls if laptop credentials lapse.
4. **P4 · A collector pod in `components`** for the pod-only logs (PDP, gateway stdout): survives laptop sleep, but it is a cluster write, has no AWS credentials, and the laptop can snapshot those logs anyway.

**Evidence.** F2, F3, F8; [mem: workshop-progress] (SSM denied); [handoff §0.4] (expiry, reboot); [SN handoff §5.3] (credentials in a terminal; a mode-600 file for long runs).

**Fit.** A-STL and A-REG: evaluators are pure functions of (snapshot, frozen registry), so they run anywhere. L-PATH: every pull adapter is off the path. B-CC: the inline check runs in the runtime; pull loops are labelled "near-real-time post-run evaluation" [SN handoff §7.6].

**Effort.** Fleet 1–2 h: a supervisor loop that detects ExpiredToken and records a `monitoring-gap` instead of failing silently; an hourly admission and events pull. Live: none.

**Risks**
- Credentials expire in the middle of a loop.
- Laptop sleep or network loss.
- `components` events are kept about 1 h, so the admission pull must run at least hourly, or the deploy wrapper must emit the verdict itself.
- PDP and gateway stdout are pod-only: snapshot them before any restart [handoff §3a item 5].

**Recommendation (not decided):** P3, with the laptop as the hub.

**Captain:** yes. Where the ServiceNow credentials live (Arth), who refreshes AWS credentials and when, and any use of the IDE (a person must drive it).

---

### D12 · The record schema and the stitch keys

**The question, inside the frame.** Every adapter writes the same decision record into the one store; a stitcher joins them. To choose: the shape, the field list, record identity and the stitch-key order.

**Options: shape**
1. **R1 · Flat dotted keys,** a superset of the slide's evidence record (`run.id`, `call.id`, `control.id`, `threshold.version`, `threshold.value`, `measured.value`, `verdict`, `actor.id`, `emitted.at`) [slides p21] plus the captain's fields. One JSON object per record. `correlation_id` duplicated from `run.id`, because the ledger filters on it [F7].
2. **R2 · Nested JSON** (`control{}`, `threshold{}`, `actor{}`, …): tidier, but further from the slide and the ledger's flat filter.
3. **R3 · An OTel log-record shape** (an attributes map with `gen_ai.*`, `modaas.*` names): close to `/modaas/evidence`, heavier to read.

**Proposed fields (R1).** Required unless marked optional.

| Group | Fields |
|---|---|
| Identity | `schema` (`ifabric.evidence/1`), `record_id`, `record_kind` ∈ {decision, action, observation, handoff, lifecycle, judgment, notification, approval, metric, assessment, finding}, `phase` (for `/timeline` compatibility), `detail` (one readable line) |
| Run and stitch | `correlation_id` (= `run.id`, the CID), `run.id`, `call.id` (the gateway action id; optional), `trace.id`, `span.id` (optional), `handoff.id`, `handoff.from`, `handoff.to`, `handoff.payload_sha256`, `handoff.data_classification` (handoff records), `runtime.arn`, `aws.request_id` (optional), `finding.id`, `assessment.id` (optional) |
| Control | `control.id` (ACN-COST-001, AIA-LOG-001, AIA-ARC-006; for observed platform decisions the platform's policy id, e.g. `cedar:modaas-toolconfig-customer-records`), `control.ref` (C16, C7, C9, ESC, PLATFORM), `threshold.version` (for the platform: its policy version), `threshold.value`, `threshold.sha256`, `measured.value`, `measured.unit`, `measured.source` (adapter-tally, gateway-figure-of-record, cloudwatch, …), `verdict` ∈ {ALLOW, DENY, ALERT, RECORDED, BLOCKED, REFUSED, SATISFIED, BREACHED, INDETERMINATE, NOT_ASSESSED, ESCALATED}, `reason` |
| Who | `actor.id` (agent name), `actor.runtime_id`, `actor.version` (CR generation, image digest, model alias), `on_behalf_of` (the ticket or customer of the scenario, or the operator who started the run), `principal.platform` (e.g. `ServiceIdentity::"bootstrap-key"`, or the IAM role for AWS events), `ep.id`, `ep.kind` (slide 12's types), `ep.transport` (evaluate, emit, callback, pull), `ep.responsible`, `control.owner` |
| Time | `emitted.at` + `emitted.clock` (agent-runtime, script-host, gateway, pdp, audit-store, cloudwatch-ingest, aws-cloudtrail, servicenow), `observed.at` + `observed.clock` (pulled records), `ts` (the ledger field; we set it to `emitted.at`), `seq` (set by the ledger) |
| Content (optional) | `model.id`, `tokens.in`, `tokens.out`, `outcome.http_status`, `outcome.finish_reason`, `tool.name`, `tool.args_sha256`, `data_classification` |
| Provenance | `source.refs` (prefixed refs as in [SN handoff §8.2], plus `aws-spans:<query_id>#<row>`, `modaas-evidence:<eventId>`, `pdp:<pod>#L<n>`, `cloudtrail:<eventID>`), `emitter` (adapter name, version and git sha) |

**Record identity.** For pulled observations, `record_id` = sha256(source system + source ref), so a re-pull deduplicates. For emitted records, a time-sortable id (emit time + random suffix).

**Stitch keys, in order**
1. `correlation_id` / `run.id`: the CID from baggage. Present on gateway spans, `/modaas/evidence` and the ledger [handoff §5.3].
2. `call.id`: the gateway's action id. On spans, PDP lines, `/modaas/evidence` and the response header our adapters capture.
3. `trace.id`: for refusals with no run id (pause 404, 403, 405), the `/aws/modaas/gateway` copy, X-Ray and PDP lines. It reaches the CID through `/modaas/evidence` [handoff §5.2].
4. `handoff.id`: minted by the script, carried in the payload, echoed by the agent.
5. `runtime.arn` + time window: joins the AWS-written `InvokeAgentRuntime` records (WHO invoked which runtime, when), which carry no session id or CID [F11]. Whether CloudTrail's `requestID` equals the request id the script can capture is UNVERIFIED. (corrected 2026-10-05 after live re-check: they carry the caller-sent CID, session id and traceparent in `responseElements`, so this key can be an exact CID + session-id join; the CLI exposes no `requestID` [06 B6]. See `10-f11-resolution.md`.)
6. `finding.id`: the ServiceNow incident's correlation id [SN handoff §6]; then `assessment.id` and the register version + sha256.

A record whose CID can't be resolved is stored with `correlation_id = "unresolved:<trace id>"` and counted as a gap, never dropped.

**Evidence.** "What turns a record into evidence for a control: what happened, which control, which threshold version, which run, who acted" [slides p9]; the worked record [slides p21]; the Finding contract and reference prefixes [SN handoff §6, §8.2]; `/modaas/evidence` keys [contract-verify §3]; the ledger's filter [F7]; the captain's field list (§1).

**Fit.** EV ("bound to a control, a threshold version and a run"); L-SELF (every record carries its source refs); A-2EP (the same record from every adapter is what "nothing rewritten" looks like); RECONSTRUCT.

**Effort.** Fleet 1.5–2 h (JSON Schema, validator, fixtures); adoption happens inside each adapter's own effort. Clock-bound: freeze it before the adapters are written [R-D-06].

**Risks**
- Field sprawl: keep the required set small and enforce it in the validator.
- A clock label is useless without discipline: every timestamp gets its clock.
- The handoff `data_classification` needs a declared table (which payloads carry customer records); put it in the registry.

**Recommendation (not decided):** R1 with the fields above, `record_kind` as listed, deterministic ids for pulled records, and the stitch order 1–6.

**Captain:** no (a build choice), except the classification table (strategy).

---

## 5. Consolidated asks for the captain

1. **Cap values and tiers** for C16 (with the risk-matrix justification), the C7 coverage and gap numbers, the C9 metric and limit, and the owner's sign-off (D2, D3, D4, D5).
2. **Agent plan:** build the `ifabric-` trio on super-120b; approve 3 AgentConfigs; whether to revert the reference IT agent to super-120b (D7, D9).
3. **Register freeze:** the S3 write-once object and the ServiceNow owner-approval record, timed before the first assessed run (D5).
4. **Budget and timing** for the reference S2 BREACH run (about 2.0M tokens, then about 1 h of recovery) (D9).
5. **One Cedar forbid rule** on an `ifabric-` ToolConfig for Hostile/Rogue tests; any shared-tool edit needs an explicit OK (D10).
6. **The AWS-timestamped mirror** log groups, and the record volume written into the shared ledger (D8).
7. **ServiceNow credential placement** (laptop or IDE) and who refreshes AWS credentials overnight (D11).
8. **Update earlier documents** with F1 (versioned bucket), F2 (no Insights in the IDE), F4 (no `external` hook) and F11 (no session id in the AWS invocation log; corrected 2026-10-05 after live re-check, see `10-f11-resolution.md`): [corr row 15], gap 6's bucket paragraph, and R-C-16 in `02-requirements.md`.

## 6. Open checks (UNVERIFIED; each needs a write or a first run)

- How a `BeforeModelCallEvent` cancel surfaces in the agent's result, and how often `projected_input_tokens` is None (D2).
- Whether the OpenAI client in our build retries, and how often (D2).
- Whether `x-modaas-action-id` is returned on streaming responses (D4, D7).
- Whether `aws/spans` MCP spans carry the MCP method, to drop session set-up spans (D4).
- Whether CloudTrail's `requestID` equals the request id the script can capture from `InvokeAgentRuntime` (D12).
- Whether `score-run.py` still grades correctly when observer records share the ledger (D8).
- Whether a ToolConfig Cedar edit resets approval, and which policy the PDP applies when two ToolConfigs expose one tool name (D10).
- Whether the reference S2 run loops again on super-120b (D9).
- Whether a service control policy or a bucket policy adds limits beyond the identity policies read for F1, F2 and F8 (not readable by our role).

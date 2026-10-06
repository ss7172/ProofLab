# 10 · F11 resolution: what the AWS invocation log really carries

Written 2026-10-05, about 23:30–23:59 UTC, by a fact-keeper subagent, to settle a conflict between two architecture inputs:
- **F11** (`03-decision-options.md` §2): the AWS-written `InvokeAgentRuntime` records in `/aws/bedrock/aict-invocations` have empty `requestParameters`, so no session id and no CID; a run joins them only by runtime ARN + time window.
- **AR-20** (`05-feasibility-agents-runtime.md`): the records carry the CID, the session id and the trace in `responseElements`; `eventTime` is the end of the call; delivery comes about 5 min late.

**How it was checked.** Read-only, as `WSParticipantRole` (profile `hackathon`):
- `logs filter-log-events` on `/aws/bedrock/aict-invocations`, first by time window for two known runs, then over the whole retention: **531 records**, eventTime 2026-10-05 00:01:41Z → 09:13:40Z. There are none later, up to the read at 23:37Z: no agent or model has been invoked since 09:13Z.
- Four spot reads with a filter pattern: three on `aws/spans` (one run id, two Bedrock request ids) and one on `/aws/modaas/gateway` (a Bedrock request id).
- The kit's `workshop-assets/starter/ask_agent.py`, for where the ids come from.
- Only field paths and the values of id and time fields were printed. No access-key id, source IP or account id is shown here.

---

## 1. Verdict

**AR-20 is right about `InvokeAgentRuntime`. F11 looked only at `requestParameters`.**
- `requestParameters` is empty on all 28 `InvokeAgentRuntime` records, as F11 said.
- But `responseElements` carries `runtimeSessionId`, `traceParent`, `baggage` and `statusCode` on **all 28**. The session id starts with the baggage CID on 28 of 28.
- F11 read the keys of `requestParameters` only (its method: "key names and ARN suffixes only"); the ids sit in `responseElements`. AICT's own usage query reads the same field: it groups by `requestParameters.sessionId`, which is always empty on these records.

**F11's "runtime + time window only" is true for one record type: the model calls.** `Converse` and `ConverseStream` records carry no CID, session id or trace (0 of 503).

**AR-20's timing holds, with a wider delay range.**
- `eventTime` is the **end** of the call.
- Delivery to CloudWatch takes **19–328 s** for `InvokeAgentRuntime` (median 280 s, n = 28), not a flat 5 min.

---

## 2. The precise statement (use this wording)

`/aws/bedrock/aict-invocations` (CloudTrail data events, AWS-written, kept 7 days) holds two kinds of record.

**1. `InvokeAgentRuntime`: one per agent invocation** (event source `bedrock-agentcore`).
- `requestParameters` is empty.
- `responseElements` carries:
  - `runtimeSessionId`;
  - `traceParent` (W3C);
  - `baggage` (`modaas-correlation-id=<CID>`);
  - `statusCode`, `contentType`, and `response` = `HIDDEN_DUE_TO_SECURITY_REASONS`.
- **These three ids are the ones the caller sent.** The kit's `ask_agent.py` mints the session id as `<CID>-<32 hex>` (line 49) and passes it (line 56). It sends `--baggage modaas-correlation-id=<CID>` (line 68) and a W3C traceparent (lines 66–67, minted at 109–112 if none is given).
- **So each record joins its run exactly:**
  - by the CID in `baggage`, or the session id's prefix;
  - by the trace id in `traceParent` (one per run: S1 sent the same traceparent to all three runtimes);
  - by the session id, which is one per invocation. A CLI retry reuses it, though (§4.3).
- **AWS sets** the record itself, `eventTime`, the caller (`userIdentity`, an IAM role), the runtime ARN (`resources`), `requestID` and `statusCode`. **The invoker sets** the ids. A caller that sends no baggage gets a record with no CID. All 28 in retention have one: 26 from our scripts (`aws-cli/2.37.9`) and 2 from the IDE role (`Boto3`).

**2. `Converse` / `ConverseStream`: model calls by the gateway's role `a-01-eks-cluster-agentgateway-bedrock`.** A streamed call gives two records:
- **an `AwsApiCall` record:** `requestParameters.modelId`, `guardrailConfig` (`guardrailIdentifier`, `guardrailVersion`, `trace`) and `inferenceConfig.maxTokens`, plus `requestID`;
- **an `AwsServiceEvent` record:** `serviceEventDetails.parentRequestId` (= that `requestID`), the input and output tokens, and the guardrail's verdict `guardrailTrace.actionReason` (`No action.` or `Guardrail blocked.`).

They carry **no** CID, session id, traceparent or X-Ray trace id (0 of 503, full-text search). The Bedrock `requestID` is on no gateway span and no `/aws/modaas/gateway` record (0 hits). So model-call records join a run only by:
- time;
- the gateway's role;
- the model id.

The per-call token counts match the gateway's spans exactly (§4.2), which makes that join near-exact. It is a content match, not an id.

**Time.**
- `eventTime` is the end of the call, truncated to the second.
- The CloudWatch event timestamp (`@timestamp` in Logs Insights) is the **delivery** time. It comes 19–328 s later for `InvokeAgentRuntime` and 9–341 s later for model calls. Records arrive in batches that share one timestamp.
- So pull at least 10 min after a run, and join on `eventTime`, never `@timestamp`.

**One line, for summaries:** each `InvokeAgentRuntime` record carries, in `responseElements` (its `requestParameters` is empty), the caller-sent session id (`<CID>-<hex>`), `traceParent` and baggage CID, so it joins its run exactly by CID, trace id and session id. `eventTime` is the call's end, and the record lands 19–328 s later. The model-call records (`Converse*`) carry no run, session or trace id; they join a run only by time, the gateway's role and the model.

---

## 3. Evidence: the records read

### 3.1 Three records for the S1 swap run `fault-1791179282-8ef1a8`, and one for `my-agent-1791191585-4d9744`

Every row: `eventName` = `InvokeAgentRuntime`; `requestParameters` = null; caller `AssumedRole:WSParticipantRole`, `aws-cli/2.37.9`; `statusCode` 200.

| `eventTime` | CloudWatch time | Runtime | `responseElements.runtimeSessionId` | trace id in `traceParent` | `baggage` CID |
|---|---|---|---|---|---|
| 05:48:09Z | 05:53:19Z | `customer_experience_agent` | `fault-1791179282-8ef1a8-4ad86baaffee43e09f3892afc55af7e5` | `e13e7b734bb44249ad08b655a253306a` | `fault-1791179282-8ef1a8` |
| 05:48:35Z | 05:53:19Z | `it_resolution_agent` | `fault-1791179282-8ef1a8-69af641ed8904984a76b547ff9b1c674` | same | same |
| 05:48:49Z | 05:53:19Z | `network_resolution_agent` | `fault-1791179282-8ef1a8-0f52bc6136c747c68616c3703348be9a` | same | same |
| 09:13:06Z | 09:17:51Z | `my_agent` | `my-agent-1791191585-4d9744-cdd59cd789e34c388c37909cea752a39` | `f51408192eb04563bbf7299258e2e6e3` | `my-agent-1791191585-4d9744` |

- The S1 trace id is the run trace (`e13e7b73…`, as in `aws/spans`). The my-agent trace id is the kill-switch run's (`f5140819…`), the one gap 4 joins through `/modaas/evidence`.
- **The pause refusal leaves an invocation record with status 200 and no model-call record.** The gateway refused that run's model call before it reached Bedrock.

### 3.2 Field paths

| Record | Paths present |
|---|---|
| `InvokeAgentRuntime` (`AwsApiCall`, `Data`, `readOnly` false) | `eventVersion`, `eventTime`, `eventName`, `eventSource`, `eventType`, `eventCategory`, `eventID`, `requestID`, `readOnly`, `managementEvent`, `awsRegion`, `recipientAccountId`, `sourceIPAddress`, `userAgent`, `userIdentity.{type, principalId, arn, accountId, accessKeyId, sessionContext.sessionIssuer.{type, principalId, arn, accountId, userName}, sessionContext.attributes.{creationDate, mfaAuthenticated}}`, `tlsDetails.{tlsVersion, cipherSuite, clientProvidedHostHeader}`, `resources[].{ARN, type, accountId}` (the runtime and its `DEFAULT` endpoint), `requestParameters` (null), `responseElements.{runtimeSessionId, traceParent, baggage, statusCode, contentType, response}` |
| `ConverseStream`, `AwsApiCall` | the same envelope, plus `requestParameters.{modelId, guardrailConfig.{guardrailIdentifier, guardrailVersion, trace}, inferenceConfig.maxTokens}`; `responseElements` null, or `guardrailTrace` when the guardrail acted; `resources[0].ARN` = the foundation model |
| `ConverseStream`, `AwsServiceEvent` | the same envelope, without `requestID`, plus `serviceEventDetails.{parentRequestId, AdditionalEventData.additionalEntries.{inputTokens, outputTokens}, ResponseElements.guardrailTrace.{actionReason, inputAssessment.<guardrail id>.contentPolicy.filters[].{type, confidence, detected, action}}}` |
| `Converse`, `AwsApiCall` | 8 by the gateway's role (`requestParameters` as above; `responseElements.guardrailTrace`); 3 by `WSParticipantRole`, `AccessDenied` (the direct-Bedrock probes) |

### 3.3 The whole retention (531 records)

| eventName / eventType | Caller role | Count | CID | session id | traceparent |
|---|---|---|---|---|---|
| `InvokeAgentRuntime` / AwsApiCall | `WSParticipantRole` | 26 | 26 | 26 | 26 |
| `InvokeAgentRuntime` / AwsApiCall | IDE role (`a-02-code-editor-IdeInstanceRole-…`) | 2 | 2 | 2 | 2 |
| `ConverseStream` / AwsApiCall | `a-01-eks-cluster-agentgateway-bedrock` | 246 | 0 | 0 | 0 |
| `ConverseStream` / AwsServiceEvent | the same | 246 | 0 | 0 | 0 |
| `Converse` / AwsApiCall | the same | 8 | 0 | 0 | 0 |
| `Converse` / AwsApiCall | `WSParticipantRole` (AccessDenied) | 3 | 0 | 0 | 0 |

**Delivery delay** (CloudWatch time − `eventTime`):

| Records | n | min | median | max |
|---|---|---|---|---|
| `InvokeAgentRuntime` | 28 | 19 s | 280 s | 328 s |
| `ConverseStream` | 492 | 9 s | 174 s | 341 s |
| `Converse` | 11 | 98 s | 312 s | 335 s |

---

## 4. What else the re-check showed

### 4.1 `eventTime` is the end of the call

Run `my-agent-1791191612-9c42ef`:
- its CID was minted at 09:13:32Z (the epoch in the CID);
- the gateway's spans run 09:13:33.960 → 09:13:40.947;
- the model-call records are at 09:13:35–09:13:40;
- the `InvokeAgentRuntime` record's `eventTime` is **09:13:40Z**.

The S1 swap run reads the same way. Customer: model calls 05:48:05–05:48:09, `eventTime` 05:48:09. IT (nano-9b): 05:48:19–05:48:35, then 05:48:35. Network: 05:48:38–05:48:49, then 05:48:49.

### 4.2 Model calls match the gateway's spans by token counts

For that same run, the 4 model spans in `aws/spans` carry input/output tokens of 654/29, 1,772/32, 2,111/50 and 2,431/206. The 4 `AwsServiceEvent` records in the window carry exactly the same pairs, and both sides show `maxTokens` 500.

### 4.3 S2's IT agent: two records, one session id

`it_resolution_agent` has two `InvokeAgentRuntime` records for `fault-1791177342-d3f892`:
- the same `runtimeSessionId` (`…-cfe76e716fc346b7b0d86d9d81230049`);
- distinct `requestID`s;
- both 200;
- `eventTime` 05:20:24Z and 05:20:39Z.

This matches AR-18, which found two IT `intent` records 180 s apart in the ledger snapshot (05:16:01, 05:19:01), consistent with the CLI re-sending after its 180 s read timeout (`ask_agent.py` line 64, `--cli-read-timeout 180`, with the CLI's default retries). So the session id does not tell a retry from the original: only `requestID` does, and the CLI doesn't expose it (06 row B6).

### 4.4 The AWS log names the guardrail's verdict per model call, but without a run id

- The two guardrail blocks seen in 30 days of gateway spans (06 row A5) both read `Guardrail blocked.` here:
  - 03:32:41Z, a `Converse` on nano-9b (the direct gateway probe);
  - 09:12:28Z, a `ConverseStream` pair on super-120b, by time the `my-agent-1791191546-6aa5dd` prompt attack.
- The other 252 gateway model calls in the log read `No action.`.
- So this is the only record outside the agent that says a guardrail acted. It joins the run by time and model only.
- This is a different surface from the gateway span, which has no finish reason (06 row A5).

---

## 5. Where the wrong version was, and what was corrected

**Corrected here, each marked "(corrected 2026-10-05 after live re-check)":**
- `PLANNING-HANDOFF.md`: the header, the label list, §3b item 18, §4.2 row 2 and its notes, and §5.3's `aict-invocations` row.
- `notes/playbook/playbook-verification.md` row 2.
- `architecture/work/02-requirements.md`: the hand-off row of table A, and R-C-06's surface table.
- `architecture/work/03-decision-options.md`: F11 and its three echoes, as a marker only (the original text is kept).
- `architecture/work/06-feasibility-evidence-data.md`: rows B6, E4 and E5, the stitch-key table, risk 5 and §5, as markers only.
- `gap-list.md` gap 4: the AWS log does name the guardrail's verdict (§4.4).
- Memory: `platform-verified-facts`, `servicenow-context`, `workshop-progress`, `prooflab-project`, `planning-handoff` and the `MEMORY.md` index.

**Not edited here (owned by the architecture fixers): the places that still carry F11.**
- `ARCHITECTURE.md`:
  - §3.1 EP-11: "no session id or CID, so they join by runtime ARN + time [03 F11]";
  - §3.6 stitch key 5: "`runtime.arn` + time window … (default ±5 s) … [03 F11]";
  - the record schema row "`runtime.arn`, `aws.request_id` … For the ARN + time join". Nothing can capture `aws.request_id`;
  - §8: "`aict-invocations` (7-day retention): per run" (too early: pull at ≥ +10 min);
  - §9.2: "by runtime ARN + time [03 F11]";
  - §10's WHO row: "by ARN + time (EP-11)".
- `one-page.md` and `one-page.svg`: stitch key "5 runtime ARN + time".
- `decisions.md` D12: "→ runtime ARN + time →".

**Suggested key 5, for the fixers:** the `InvokeAgentRuntime` record ↔ `handoff.sent` by CID (`baggage`) + `runtimeSessionId` exact. Match `eventTime` against `handoff.received`. Flag two records with one session id as a retry, as AR-20 already proposes.

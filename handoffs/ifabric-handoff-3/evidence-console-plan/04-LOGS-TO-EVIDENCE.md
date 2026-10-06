# 04 · From logs to evidence: capture, normalize, bind

> "A log is for an engineer next week. Evidence is for a sceptical stranger, years later." (MC-10/11)
>
> A log line becomes evidence only when it is **(1) captured untouched with the exact query that fetched it, (2) parsed deterministically, (3) bound to a control, a threshold version, a run, an actor and a time, and (4) listed with its sha256 in the MANIFEST.** "A span is not evidence until it is bound to a control, a version and a run" (MC-25).

## 1. The pipeline: six layers, none edits another

| Layer | Writes | Rule | Masterclass habit |
|---|---|---|---|
| ① Capture | `raw/<surface>/<scope>/<file>` + `<file>.capture.json` | Bytes exactly as received (after **capture-time redaction**, §3); never edited; a re-capture is a new file | telemetry never judges |
| ② Normalize | `facts/<kind>.jsonl` + `facts/quarantine.jsonl` | Deterministic parser with `parser_version`; malformed or unparseable → quarantine with a reason (never dropped) | — |
| ③ Bind | `records/<control>/<scope>.jsonl` (`ifabric.evidence/v1`) | Mechanical join to control + threshold version + run + actor + `emitted.at` + source; anything unbound → quarantine "unbound" | the ledger never interprets |
| ④ Evaluate | `assessments/<control>/<scope>.r<N>.json` | Pure function of (records, frozen register); a correction is a new revision | the evaluator never remembers |
| ⑤ Find | `findings/*.json` → ServiceNow | Only BREACHED / ESCALATED / monitoring-gap | — |
| ⑥ Answer | `answers/`, `auditor/`, `runs/<cid>/run.json` | Composed from ③–⑤; deterministic `answer_id` | — |

Each layer is idempotent: re-running it over the same inputs reproduces the same outputs, byte for byte. That is how a stranger re-derives our verdicts.

---

## 2. Capture recipes, per surface

Run every command through the workshop shell (`workshop-local/shell` or the IDE). Times are UTC. Each capture writes a sidecar (§4). The surfaces and their join keys are verified live by the teammate (VF).

| # | Surface | Why | Capture (template) | Keep | Join keys | Gotchas (verified) |
|---|---|---|---|---|---|---|
| 2.1 | **Gateway stdout** (`modaas-agw` pod) | **C16 figure of record** | `kubectl -n agentgateway-system logs deploy/modaas-agw --all-containers --since-time=<run start> \| grep -F <cid>` | `listener`, `http.status`, `gen_ai.request.model`, `gen_ai.usage.input_tokens/output_tokens`, finish reason, `agw.ai.usage.cost.total`, `duration`, `modaas.run_id`, `modaas.trace_id`, `modaas.action_id` | run_id = CID (baggage); action_id | **Ephemeral:** a pod restart loses run attribution, so capture **right after each run**. `listener=http` (MCP) lines share run_id but carry no tokens. Pause-404 lines have no ids. A guardrail block = 200 + 0 tokens |
| 2.2 | Durable gateway log `/aws/modaas/gateway` (7 d) | Durable cross-check | `aws logs filter-log-events --log-group-name /aws/modaas/gateway --start-time <ms> --end-time <ms> --filter-pattern '"<trace_id>"'` | tokens, cost, model, http | `trace_id` only (no run_id) | Paginate until no `nextToken`; record the page count |
| 2.3 | `/modaas/evidence` (30 d) | Decisions joined to the CID | `aws logs filter-log-events --log-group-name /modaas/evidence --filter-pattern '"<cid>"' …` | `correlation_id`, `action_id`, `trace_id`, `decision`, `policy_id`, `principal`, `phase`, `detail` (`route_alias=` reveals cross-tool use) | CID, action_id, trace_id | Guardrail blocks and pauses are logged **ALLOW**: report the outcome from the gateway line |
| 2.4 | PDP decision logs (**both replicas**) | AUTHORIZED | `kubectl -n modaas-system logs -l app.kubernetes.io/name=modaas-pdp --all-containers --prefix --tail=-1 \| grep -E '<action_ids>'` | `decide policy_id=… decision=… matched=… latency_ms=… trace_id=… action_id=…` | action_id | Pod-only; health checks dominate the tail, so use `--tail=-1` on both pods |
| 2.5 | Audit ledger | C7 events, dispositions | `kubectl get --raw '/api/v1/namespaces/components/services/audit-store:8080/proxy/records?cid=<cid>'` | the JSONL lines (correlation_id, step, phase, actor, detail, trace_id, ts, seq) | CID | **`/records` is JSONL; never parse `/timeline` as JSON.** Reference agents' trace_ids ≠ the run trace; `seq` (epoch ms) can collide |
| 2.6 | AgentCore spans `/aws/bedrock-agentcore/runtimes/<id>-DEFAULT` (stream `spans`) | Cross-check only | `aws logs filter-log-events … --filter-pattern '"<trace_id>"'` | span ids, names, token attributes, times | trace_id | **Drop `events[].attributes.content`** (prompts and customer records). `invoke_agent` parents sum their children: use `chat` spans only, or you double count |
| 2.7 | X-Ray | RECONSTRUCT / corroboration | `aws xray batch-get-traces --trace-ids <1-xxxxxxxx-yyyyyyyyyyyyyyyyyyyyyyyy>` | segments (`modaas-agw`, runtimes), `modaas.action_id` annotations | trace_id | It **is** durable (the playbook's "no exporter" is wrong). Convert the W3C id to X-Ray format |
| 2.8 | AgentCore metrics (C9) | Drift signal | `aws cloudwatch get-metric-statistics --namespace AWS/Bedrock-AgentCore --metric-name Latency --dimensions Name=Name,Value=<runtime>::DEFAULT --start-time <hourZ> --end-time <hourZ+1h> --period 3600 --statistics Maximum --output json` (and `Errors` Sum) | Timestamp, value, **unit, statistic, dimensions**, request parameters | runtime + window | Use `--output json` (the text CLI prints local time). macOS: `date -u -v-1H`. Only **closed** hours. Empty datapoints = UNKNOWN |
| 2.9 | CR status / approvals | APPROVED, versions | `kubectl -n components get agentconfig,modelconfig,toolconfig -o json` | `metadata.generation`, `status.observedGeneration`, `status.governance.approvals` (subject, attestation, time), `spec.dependsOn`, image digest, `status.registryRecordId` | CR name + generation | **REDACT** `spec…env` values (`AUDIT_WRITE_TOKEN`, `OPENAI_API_KEY`, `AGENTCORE_GATEWAY_MCP_TOKEN`) before writing (§3) |
| 2.10 | `/aws/bedrock/aict-invocations` (CloudTrail data events, AWS-written) | Independent WHO (InvokeAgentRuntime principal), guardrail config per model call | `aws logs filter-log-events --log-group-name /aws/bedrock/aict-invocations --start-time … --end-time …` | `eventName`, `userIdentity.arn`, `requestParameters.modelId/guardrailConfig`, times | time + session | No run id: join by time window and runtime ARN |
| 2.11 | L1 proofs | Foundation | governed call (`curl -sD - … /v1/chat/completions` in-cluster), prompt attack, direct Bedrock call, approvals | response headers (`x-modaas-action-id`), usage, `finish_reason`, the AccessDenied error | action_id | Remove the `Authorization` header from captures |
| 2.12 | ServiceNow | Human loop | `prooflab.servicenow` `notify/check/export/case` (`08-…`) | delivery log, incident exports, case snapshots, Assurance run records | `finding_id` | Already evidence-shaped. Never mix in the wiring-test log |

---

## 3. Redaction at capture (secrets never enter the pack)

Raw captures are "never edited". **Redaction therefore happens at capture time, deterministically, and is logged**, before the bytes are written:

| Rule id | Matches | Replaced with |
|---|---|---|
| `bearer-token` | `Authorization: Bearer …`, `authorization=…` | `[REDACTED:bearer]` |
| `env-secret` | env entries named `*TOKEN*`, `*KEY*`, `*SECRET*`, `*PASSWORD*` in CR/runtime JSON | value → `[REDACTED:env:<name>]` |
| `aws-key` | `AKIA…` / `ASIA…` + secret-key patterns | `[REDACTED:aws]` |
| `bearer-url` | the `tkn` query parameter, `X-Amz-Signature=`, IdeUrl/CockpitUrl hosts | `[REDACTED:url]` |
| `span-content` | `events[].attributes.content` in spans | field removed |
| `reasoning` | `<think>…</think>` in any model output | `[REDACTED:reasoning]` |

The sidecar records each rule and its count, and optionally the sha256 of each original value (the values are long random tokens, so the hash reveals nothing). **Test:** `test_redaction.py` feeds known fake secrets through every capture and asserts zero matches. Then run the team's `pre-push-secret-scan.sh` over the pack (it must print `RESULT: clean`).

---

## 4. The capture sidecar (`<file>.capture.json`)
```json
{
  "surface": "gateway-stdout",
  "path": "raw/gateway/fault-…/gateway-stdout.log",
  "command": "kubectl -n agentgateway-system logs deploy/modaas-agw --all-containers --since-time=2026-10-06T00:00:02Z | grep -F fault-…",
  "scope": {"cid": "fault-…", "start": "2026-10-06T00:00:02Z", "end": "2026-10-06T00:05:52Z"},
  "captured_at": "2026-10-06T00:06:32Z", "captured_by": "prooflab capture@git:<sha>", "operator": "<person>",
  "source_identity": {"pod": "modaas-agw-…", "replicas_captured": 1, "log_group": null},
  "pagination_complete": true, "line_count": 15,
  "redactions": [{"rule": "bearer-token", "count": 15}],
  "sha256": "<sha256 of the written file>"
}
```
The console's Record Inspector shows this verbatim, which is how a stranger re-runs our query.

---

## 5. Normalize → facts

| Fact file | One row per | Required fields |
|---|---|---|
| `facts/gateway_calls.jsonl` | gateway LLM execution | `action_id`, `cid`, `trace_id`, `ts` (gateway clock), `model_alias`, `model_id`, `input_tokens`, `output_tokens`, `finish_reason`, `http_status`, `blocked` (bool), `cost_usd`, `duration_ms`, `raw_ref`, `raw_sha256`, `parser_version` |
| `facts/tool_calls.jsonl` | MCP `listener=http` line | `action_id`, `cid`, `route`, `tool`, `route_alias`, `status`, `ts`, `raw_ref` |
| `facts/decisions_pdp.jsonl` | PDP decision | `action_id`, `trace_id`, `policy_id`, `policy_version`, `decision`, `replica`, `ts`, `raw_ref` |
| `facts/ledger_events.jsonl` | ledger record | `cid`, `step`, `phase`, `actor`, `detail`, `trace_id`, `ts` (ledger clock), `seq`, `raw_ref` |
| `facts/metric_windows.jsonl` | runtime × closed hour | `runtime`, `window_start`, `statistic`, `unit`, `value` (or null), `datapoints`, `query_ref` |
| `facts/approvals.jsonl` | approval record | `kind`, `name`, `generation`, `subject`, `attestation`, `time`, `raw_ref` |

**Dedupe and corroboration:**
- One `gateway_calls` row per `action_id`.
- Span or durable copies of the same call are **corroboration** (`corroborated_by[]`), never extra charges.
- A source correction supersedes the earlier row with a `revision`; never add both.

---

## 6. Bind → evidence records

For each control, the binder emits one `ifabric.evidence/v1` record per governed action in scope:
- **C16:** one per gateway call;
- **C7:** one per observed expected event;
- **C9:** one per window;
- **decisions:** one per inline admission.

Each record carries:
- `control.id`, `control.ref`;
- `threshold.version` and `threshold.value`, **read from the frozen register** (never typed);
- `run.id` (alias) + `joins.cid`, `call.id`, `actor.id` (agent from orchestrator/ledger context: the gateway has no agent identity);
- `emitted.at` (source clock), `emitted.by` (binder version);
- `source` (surface, raw_ref, sha256, capture_ref, captured_at, clock, corroborated_by);
- `seal: "out-of-scope"`.

Anything that cannot be bound (no CID, no matching run, ambiguous actor) goes to `facts/quarantine.jsonl` with the reason `unbound`. The console shows these as red "unbound" rows: they count against completeness, never silently.

---

## 7. Worked example: one gateway line becomes one evidence record

**① Raw** (`raw/gateway/fault-…/gateway-stdout.log#L15`; synthetic; field layout as the teammate observed it, exact format from your own capture):
```
2026-10-06T00:05:31.412Z info request gateway=agentgateway-system/modaas-agw listener=llm route=internal/llm:request http.status=200
gen_ai.request.model=nemotron-super-120b gen_ai.usage.input_tokens=5290 gen_ai.usage.output_tokens=314 agw.ai.usage.cost.total=0.000902
duration=3902ms modaas.run_id=fault-1791244802-b7d20f modaas.trace_id=… modaas.action_id=agw-… authorization=[REDACTED:bearer]
```
**② Fact** (`facts/gateway_calls.jsonl`):
```json
{"action_id":"agw-…","cid":"fault-1791244802-b7d20f","ts":"2026-10-06T00:05:31.412Z","model_alias":"nemotron-super-120b",
 "input_tokens":5290,"output_tokens":314,"finish_reason":"stop","blocked":false,"http_status":200,
 "raw_ref":"raw:raw/gateway/fault-…/gateway-stdout.log#L15","raw_sha256":"…","parser_version":"gw-1"}
```
**③ Evidence record** (`records/C16/FM-B.jsonl`; full example in `examples/evidence-record.C16.FM-B.c-0015.json`):
```json
{"schema":"ifabric.evidence/v1","run.id":"FM-B","call.id":"c-0015","control.id":"ACN-COST-001","threshold.version":"G-FM-v1",
 "threshold.value":60000,"measured.value":63420,"measured.call":5604,"verdict":"BREACHED","decision":"ALERT",
 "actor.id":"ifabric_network_agent","emitted.at":"2026-10-06T00:05:31.412Z","source":{"surface":"gateway-stdout",
 "raw_ref":"raw:…#L15","sha256":"…","capture_ref":"capture:…","clock":"gateway",
 "corroborated_by":["pdp:action_id=…","gateway:durable;trace_id=…","xray:trace_id=…"]},"seal":"out-of-scope"}
```
The console shows ① and ③ side by side (Ledger → **Log → Evidence**), which is the masterclass's own LOG-vs-EVIDENCE slide, live.

---

## 8. Completeness statement (every scope, every control)
`expected` (and its independent source) · `observed` · `matched` · `missing` · `unmatched` · `duplicates_removed` · `blocked` · `unmeasurable`. Written into each assessment's `population`, shown on every answer. **Under-cap but incomplete is INDETERMINATE, never SATISFIED.**

## 9. Checklist (before calling a run "captured")
- [ ] Gateway stdout captured within minutes of the run; line count = expected calls.
- [ ] `/modaas/evidence` + durable gateway + X-Ray pulled for the run's trace (corroboration ≥ 2 surfaces per call).
- [ ] Ledger `/records?cid=` captured as JSONL; PDP from both replicas.
- [ ] CR status captured with redaction; approvals cover the generation that ran.
- [ ] Sidecars present, `pagination_complete: true`, redaction counts non-zero where expected.
- [ ] `test_redaction.py` + secret scan clean.
- [ ] Facts, records and assessments regenerate byte-identically from raw (`make rebuild && git diff --exit-code evidence/`).

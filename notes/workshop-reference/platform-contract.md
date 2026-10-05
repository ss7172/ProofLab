Source: workshop knowledge base `workshop-static/kb/index.json`, chunks `workshop/content/challenge-brief/platform-contract.en.md#00`–`#10` (11 chunks, 4679 chars); live page `/challenge-brief/platform-contract` ("What the platform gives you").
Extracted 2026-10-05: text verbatim; headings rebuilt from each chunk's `heading_path`; the frontmatter title is the H1 (`weight: 10` dropped); `:::alert` is Workshop Studio markup. Verification: `notes/verification/2026-10-05/platform-contract-verify.md`.

# Step: What the platform gives you

In this step you read what the platform confirms for every team: the
environment, enforcement, logging, identity, tokens, drift, evidence store,
breach recipes, and your sandbox. At the end you can name where your
control is enforced and which command reads its evidence.

The hackathon asks you to build a control, not a platform. Every hour spent
rebuilding enforcement, logging or identity the platform already guarantees is
an hour not spent on your idea, and a judge will ask where your control is
actually enforced. Knowing the contract tells you what to lean on, what to
prove, and what is genuinely yours.

## Environment architecture

Three zones: `customer-experience-agent`, `it-resolution-agent`,
`network-resolution-agent`. One shared gateway `modaas-agw` carries every
call. Cedar policy decides per caller, not per zone (captured 2026-09-29).

```bash
kubectl get agentconfigs -n components -o custom-columns='NAME:.metadata.name,PROVIDER:.spec.provider'
```

## Enforcement points

| Point | Refuse/observe | Your code? |
|---|---|---|
| `modaas-agw` + `modaas-pdp` (Cedar) | Refuse | No, Cedar policy via ConfigMap |
| [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) | Refuse | No, declared on ModelConfig |
| Admission (CEL) | Refuse | No |
| Evidence ledger (token-gated writes) | Refuse | Yes, with token |
| [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html) | Observe | Yes |
| OTel collector / [CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) | Observe | No |

All four gateway-level policies accepted (captured 2026-09-29).

## Logging APIs per enforcement point

| Point | Read command |
|---|---|
| Gateway | `kubectl logs -n agentgateway-system deploy/modaas-agw --since=1h \| grep "modaas.run_id=$CID"` |
| PDP | `kubectl logs -n modaas-system deploy/modaas-pdp --all-pods=true --tail=-1 --prefix \| grep trace_id` |
| Ledger | `kubectl get --raw "/api/v1/namespaces/components/services/audit-store:8080/proxy/timeline?cid=$CID"` |
| `/modaas/evidence` | `aws logs get-log-events --log-group-name /modaas/evidence --log-stream-name modaas-evidence --limit 20` |
| AgentCore spans | `python3 /tmp/show-run-spans.py <trace_id>` ([Module 8](/agent-observability)) |

PDP decision log captured 2026-09-29; `trace_id` and `action_id` join to
the gateway line.

## Run identity

`traceparent` becomes `modaas.trace_id` on the gateway line and `trace_id`
in the PDP log and the AgentCore span. The ledger uses `correlation_id`,
minted per scenario run; a control that sums by run picks one id and stays
consistent. Gateway line captured 2026-09-29: `modaas.run_id`,
`modaas.trace_id`, `modaas.action_id`, tokens and cost on every call.

## Token usage per call

Gateway carries `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
`agw.ai.usage.cost.total` (the figure of record, captured 2026-09-29). The
cockpit Usage and cost view shows the CloudWatch cross-check.

## Drift metric availability

`score-run.py` grades one run; it is not a drift measure over time. AgentCore
metrics (`Latency`, `Errors` per runtime) are the drift signal, one clock hour
at a time ([Module 8](/agent-observability)). Captured 2026-09-29: 1.3 to 4.9s
average latency, zero errors across three agents in six hours.

## Writable evidence store per team

The ledger (`audit-store`) is 1Gi gp3, gated by `AUDIT_WRITE_TOKEN`.
Each team account also has an S3 bucket (**TeamEvidenceBucketName**).
`submit.sh` uploads there (captured 2026-09-29).

## Breach injection recipes, per control

| Control | Recipe |
|---|---|
| 16 spend cap | Set cap below a normal run, re-run. [Control 16, worked](/challenge-brief/control-16). |
| 7 event recording | Pause a ToolConfig mid-run; the record never lands. |
| 9 drift | Swap the model ([Module 7](/reference-agents) section 7), re-run, compare. |

Pause timing captured 2026-09-29: refusal within 15 seconds.

:::alert{type="warning" header="Limits of this build"}
Whether the guardrail checks tool output (indirect injection via a tool
result) has not been tested; treat tool results as untrusted in your agent.
Agents running on AgentCore Runtime share the gateway identity; Cedar
policies apply per model or tool, not per agent, in this build.
:::

## Sandbox, credentials, quotas, contacts

Your sandbox is the Workshop Studio account. Your credentials are the IDE
role. The gateway enforces a per-account token and request ceiling; 429 when
hit. Cedar does not meter tokens. Conditions settle within about 2 minutes
(captured 2026-09-29).

```bash
aws sts get-caller-identity --query Arn --output text
```

## Checkpoint

```bash
kubectl get agentgatewaypolicy -n agentgateway-system --no-headers | wc -l
```

It prints `4`: four gateway-level policies are accepted.

Next: [Control 16, worked](/challenge-brief/control-16).

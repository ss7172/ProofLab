---
name: reference-agents-facts
description: "Source-verified facts (2026-10-05) about the three reference agents ProofLab is built around — roles, models, tools, deployment, ledger records, IDs/traceparent, where token usage really lives, scenarios S1–S3 — and where the guide/handoff are wrong"
metadata:
  node_type: memory
  type: project
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T18:42:35.635Z
---

The full cited report is `~/firstmate-homes/TrustworthyAI/workshop-local/research/reference-agents-2026-10-05.md`; read it before planning. The agents were DEPLOYED on 2026-10-05 at 04:38 UTC (Module 7 set-up; CodeBuild from the laptop works). All 3 depended on `nemotron-super-120b`; the IT agent was swapped to `nemotron-nano-9b` at 05:47 UTC (Module 7 swap). Live runs (Module 7) confirmed this source profile; see below.

- **One program, three roles.** `reference-impl/reference-agent/agent.py` (Strands Agent in a BedrockAgentCoreApp), role set by `AGENT_ROLE`: customer, it, network.
  - **They never call each other:** `run-reference.sh` invokes customer, then IT, then network, sequentially, via `ask_agent.py` → InvokeAgentRuntime.
  - **IT "negotiation" is a stub that is never reached.**
- **Models:** the runtime model is the env var `MODEL_ALIAS`, set by the operator (a declared one is rejected). It follows `dependsOn.models[0]` whenever `modelRef` is absent or equals it (live on all 5 runtimes, 2026-10-05); which field wins when they differ is unverified (the CRD's field description says the operator injects `modelRef` as `MODEL_ALIAS`). The generator's default is `nemotron-super-120b`, while `agents.yaml` and the guide's captures use nano-9b. Generated CRs have no `modelRef`. A CRD rule (confirmed live, verbatim) requires `modelRef`, once set, to be one of `dependsOn.models`, and the Module 7 swap set both fields on the IT agent (`nemotron-nano-9b`) in one patch, so a revert must update both consistently. Per call: `max_tokens=500`, `temperature=0`, `/no_think`.
- **Tools:** one MCP tool each through the gateway: customer `customer-records`, it `runbook-lookup`, network `network-twin`.
- **Deploy path:** `build-agent-image.sh` (CodeBuild, ARM, ECR tag `reference-agent-v5-agentcore`) → `make-agentcore-agents.py` (it writes the audit token in plain text to /tmp) → apply → approve → re-run the generator so the network agent gets the IT runtime ARN. CodeBuild from the laptop works (~64 s, 2026-10-05).
- **Ledger:**
  - A successful run writes 12 records: per agent, intent, tool-invocation, invocation and result-inspection, with no NEGOTIATION.
  - A refusal writes 3 records per agent.
  - Fields: correlation_id, step, phase, actor, detail, trace_id; the store adds `seq` = epoch ms (can collide) and sets `ts` only if the writer sent none (`audit-store.py` `setdefault`, read 2026-10-05; no agent sends one today), so a writer can choose its own time.
  - There is no action_id, no tokens and no guardrail verdict.
  - The tool-invocation record is written after the model call, so it doesn't prove the tool ran.
- **IDs (verified by Claude):**
  - `run-reference.sh` mints CID `fault-<epoch>-<6hex>` and one run traceparent. `ask_agent.py` sends the CID in the body, the traceparent as AgentCore `--trace-parent`, and baggage `modaas-correlation-id=<cid>`.
  - agent.py reads traceparent only from the body, so each agent mints its own trace_id, and **ledger trace_ids ≠ the run's trace id.**
  - The gateway's `modaas.run_id` = the baggage CID (verified on the reference agents). It appears on the gateway pod's **ephemeral stdout** line and, durably (30 d), on the gateway's spans in CloudWatch Logs `aws/spans`, one per request, with tokens (confirmed live 2026-10-05). The `/aws/modaas/gateway` copy has no run id (see [[platform-verified-facts]]).
- **Tokens:**
  - Agent responses carry no usage.
  - The figure of record is the gateway per-call `listener=llm` line: `gen_ai.usage.input/output_tokens`, `agw.ai.usage.cost.total`, model id, duration. The cockpit's Cost view states the same rule.
  - Durable per-run attribution: query the gateway's spans in `aws/spans` by run id (tokens included, 30 d; count by run id, not by trace). Only the `/aws/modaas/gateway` copy needs the `trace_id` → `/modaas/evidence` `correlation_id` hop.
  - MCP `listener=http` lines share the run_id but have no tokens; `evaluate.py` counts them as calls.
  - Strands `chat` spans' tokens equal the gateway lines per call, and `invoke_agent` carries their sum, so `show-run-spans.py`, which sums every span, double-counts (exactly 2× on the swap run, Module 8).
- **Timing:** no latency in the ledger. AgentCore CloudWatch metrics Latency, Errors, Invocations and Duration exist (dimensions Resource, Operation, Name).
- **Scenarios** (data/network-inventory.json): S1 fronthaul, auto-resolve; S2 transport congestion, ambiguous, gather-evidence; S3 restricted change, maintenance-freeze trap, escalate.
  - `score-run.py` checks only ledger text, not CID, IDs, tokens or latency.
  - **Its guardrail and negotiation checks fail by construction with the shipped agent.py (verified by Claude).** The guide's sample scores (S1 8/8, S3 10/10) can't come from this code.
- **Guide/handoff errors:**
  - "no framework" (it is Strands)
  - 10 ledger records with action_id, tokens and guardrail verdict (it is 12, with none of them)
  - CLIENT/negotiate spans: native Strands spans were seen on the helper. Strands' source says it emits message content as span events by default; to verify on the agents (repo notes #22)
  - "/handle, /negotiate" HTTP (it uses MCP through the gateway)

**First live run (2026-10-05, CID fault-1791175626-0d34e2, S1):**
- Confirms the 4-records-per-agent / 3-on-refusal ledger shape, the missing action_id and tokens, the split trace_ids and the absent negotiation.
- The AgentCore runtime's own OTel logs DO carry the run trace id. Only agent.py's ledger trace_ids are minted fresh.
- The agent mislabels an MCP 403 as "http_status=500".
- One S1 run ≈ 24.8K tokens across 6 model calls (super-120b).

**Self-check (2026-10-05):**
- No scenario can pass with the shipped agent: the guardrail-verdict and negotiation checks always fail.
- **S2 makes the IT agent loop on runbook-lookup: ~2.0M tokens (1,999,001; 174 model calls, peak 49/min) in one run, vs 25–50K (S1) and ~38K (S3).** That is a natural C16 breach case, and the ledger doesn't show it (gateway records do, durably in `aws/spans`: 353 spans, 1,999,001 tokens).

**Measured per-run tokens (gateway, super-120b, 2026-10-05):** S1 24.8K (IT refused) / 50.2K (IT ran); S3 37.8K twice; S2 2.0M (IT loop). The IT 403 on runbook-lookup (a fail-closed `PolicyEngineUnavailable` DENY recorded in /modaas/evidence, cause unknown) is intermittent (1 of 3 S1 runs; not in the 5 later runs; notes #43). This is real data for justifying a C16 cap later.

**Why:** ProofLab's controls (C16 tokens, C7 event coverage, C9 latency/errors) depend on exactly these surfaces, and several guide and handoff claims about them are wrong.
**How to apply:** plan from the source-verified facts. Live token counts and spans are now measured (Modules 7–8); latency is not yet checked (Module 8 step 2).

Related: [[prooflab-project]], [[platform-verified-facts]], [[workshop-progress]]

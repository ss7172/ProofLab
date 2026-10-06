# Security matrix: enforcement points EP-0 to EP-16

> **Template.** Source: ARCHITECTURE.md section 6. The "Status" column is the only column that
> reports a result; it is filled at submit from the pack, and a blank or `<...>` means no result
> is claimed. "Can refuse" means the point stops a call; "records only" means it never does.
> The console and this file are not enforcement points.

| EP | Where | Can refuse? | Who holds the refusal | What we record | Check (case id) | Status |
|---|---|---|---|---|---|---|
| EP-0 | Pre-run version gate (script preflight) | Yes: blocks an assessed run on an unapproved or paused version | Us | A decision per agent; a finding on mismatch | T-PRE-01, T-PRE-02 | `<>` |
| EP-1 | Our runtime, model call | Yes in `enforce` (the C16 cap); records only in `observe` | Us (the c16 core) | Decision and stop records; usage | T-C16-01; ADV-R-05; ADV-R-06 | `<>` |
| EP-2 | After the run, over the gateway's log | No: the second placement of the same c16 core | Nobody | Replayed decisions, reconciled with EP-1's | EP-2 replay tests | `<>` |
| EP-3 | Our runtime, tool call | Yes (DG-1): the tool rails may refuse or modify (X-01/X-02 declared-tool scope, X-03 arguments; X-04 repetition FLAG; T-01–T-06 tool-output screening), each BLOCK / MODIFY an emitted `rail_decision`; a platform refusal stays the PDP's (Cedar, EP-6) | Our rails; Cedar at the PDP | Action records, `suspicious_tool_output`, `rail_decision` | ADV-H-02; ADV-R-01 (leg 1 our rails, leg 2 the PDP) | `<>` |
| EP-4 | Judgment (J2) | Output rails move a disposition only toward safety | Our rails, recorded | Judgment record with deciding evidence and reason | ADV-H-04 | `<>` |
| EP-5 | Orchestrating script, handoffs (Gateway A h1, B h2, C h3; four invocations) | No: records only | Nobody | Handoff records, timeouts included; one invocation per handoff | T-HO-01; ADV-R-06; ADV-R-10 | `<>` |
| EP-6 | Gateway authorization and PDP/Cedar | Yes: API key and Cedar tool policy | Platform | DENY / ALLOW, policy id, principal | SP-1; ADV-R-01; ADV-R-07 | `<>` |
| EP-7 | Bedrock guardrails | Yes (platform): prompt-attack filter on input. BLOCKED is an inference from the span (HTTP 200, 0/0 tokens), corroborated by our own record and the AWS-written record | Platform | BLOCKED next to the platform's ALLOW (gap 4) | ADV-H-01 | `<>` |
| EP-8 | Kill switch | Models and tools: yes. An AgentConfig pause is a record, not a stop | Platform | Requested vs effective time | ADV-R-08; T-PRE-02 | `<>` |
| EP-9 | Ceilings (100 req/min; 2.5M tokens/h) | Yes, account wide | Platform | Headroom per run; any 429 | none deliberate | `<>` |
| EP-10 | Admission and approvals | Yes (admission); approvals are a human act | Platform; the owner | Apply and dry-run results; approvals with generation | T-ADM-01; T-REDACT-01 | `<>` |
| EP-11 | AgentCore invocation | Yes: IAM denies direct model and gateway calls | Platform | Who invoked (joined by correlation id and session id); C9 metrics | ADV-R-02 (optional) | `<>` |
| EP-12 | AgentCore Gateway and Lambda tools | Never touched by us | Platform | Code hash baseline vs now; CloudTrail code updates | T-LAMBDA-01 | `<>` |
| EP-13 | ServiceNow human queue | No: the owner's verdict comes later | The owner | Delivery; response or silence | ESC; every BREACH finding | `<>` |
| EP-14 | Our runtime, ingress rails | Yes: BLOCK or MODIFY, self-enforced | Our rails | Every BLOCK / MODIFY as its own record | S-G2; ADV-H-01; ADV-H-05; ADV-R-11 | `<>` |
| EP-15 | Our runtime, egress audit | No: flags destinations outside the declared allowlist | Nobody | Destination flags | ADV-R-12 (synthetic) | `<>` |
| EP-16 | The cockpit's ask API (side door) | No: it has no auth and no envelope | Nobody | The invocation, labelled UNATTRIBUTED | ADV-R-14 (one probe) | `<>` |

## What this matrix does not claim

- Rails are our own and self-enforced. Their misses are published in `adversarial/` and in
  `gap-list.md` section B (rails gaps G-1 to G-14).
- Where the platform records a refusal as ALLOW, both are shown side by side; neither replaces the other.
- The honest failure (README section 6) is the case where an enforcement point was fooled; the row
  that caught it is named there, with its test and the re-test.

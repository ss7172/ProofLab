# Winning playbook: verification by the lead session (2026-10-05)

Subject: `~/Downloads/servicenow-integration-package/HACKATHON_WINNING_PLAYBOOK.md` (595 lines, dated 2026-10-05), and where it depends on it, its companion `SERVICENOW_INTEGRATION_HANDOFF.md` (from Arth, the ServiceNow workstream, with Claude Code).

Method:
- I read the whole playbook and the SN handoff's §0–§2 and §9–§14.
- I checked the claims against our memory, the repo notes and gap list, and the primary sources in `hackathon-context/sources/`: the meeting transcript, the user-pasted master brief, and the Immersion Day slides via `pdftotext`. The AWS kickoff deck facts come from memory.
- New read-only live checks: the evidence bucket, the `audit-store.py` routes, `new-agent.sh`, and the repo visibility (PRIVATE).
- I also drew on today's verifier reports in `res/`: glossary, resources and screenshots.

## Verdict

The playbook splits cleanly:
- **§1 (the brief, scoring rules) and §4 (scorecard): trustworthy.** Everything spot-checked traces to the primary sources.
- **§2 (field guide) and parts of §3: import the workshop guide's platform claims,** several of which our live evidence disproves.
- **Use it as the strategy backbone for what judges reward, with the corrections below for what the platform actually does.**

## Confirmed against primary sources

| Playbook claim | Source |
|---|---|
| Axis 1 wording "nothing to score / in the running / ahead / the full set" | Immersion Day slides |
| Axis 2 "does the control hold its own threshold?" | slides |
| C16 worked example FM-A 9,600 → SATISFIED, FM-B 10,800 → NOT satisfied (cap 10,000, G-FM-v1) | slides. Not the workshop guide's 900-token example (778/1030), which is a different example |
| "Telemetry never judges, the evaluator never remembers, the register is never in the path, the ledger never interprets" | meeting transcript |
| "ServiceNow Control Tower and human loop … absolutely needed" | transcript |
| "Creating additional agents or elaborate ServiceNow workflows does not itself earn bonus points"; "Prefix connectors, agents, workflows and records with the team name … Clone rather than modify shared examples" | master brief |
| Judging levels L1 → L2 → L3, sequential; L1 needs MoDaaS guardrails + an NVIDIA model | judging slide (memory `prooflab-project`) |
| 15-min live slot | AWS kickoff deck p8 (memory) |
| Six deliverables, six auditor questions, three alert levels, out-of-scope crypto and slide deck | memory `prooflab-project` |
| Owner "Sree" = `annapurna@invences.com` | SN handoff §2: Sree Annapurna Rallabandi. NOT an inconsistency |

**Not found in any primary source:** §1.8 "Agents run only on AWS AgentCore (Strands) or in ServiceNow; nothing hosted elsewhere". The transcript says "you can bring your tools, but we're also giving you the strands SDK". Mark UNVERIFIED.

## Confirmed platform facts (playbook §2 consistent with our evidence)

- **Guardrail block:** a prompt-attack block = HTTP 200, `finish_reason=content_filter`, 0 tokens (gap 4).
- **C16 figure of record:** the gateway per-call line. Spans are a cross-check; AgentCore Latency/Errors are the drift signal (deck p19).
- **Ceilings:** 100 req/min and 2.5M tokens/h, account-wide.
- **Strands adapter:** `GatewayModel(OpenAIModel)` drops an empty `tools` list (`~/agents/my-agent/agent.py:40-44`).
- **Ledger reads:** `/records?cid=` is the machine read; `/timeline` is text. `audit-store.py` GET routes are `/healthz`, `/records`, `/timeline`.
- **Approval annotations** `modaas.tmforum.org/approver` + `approval-attestation`; `.status.governance.approvals` holds the records. `Approved` ≠ runtime READY.
- **Model swap** = patch both `dependsOn.models[0]` and `modelRef` (Module 7).
- **TMF639:** `TMF639Projected=False` on approved CRs.
- **Direct Bedrock** is denied by IAM: an explicit Deny on the runtime role; the IDE role has no allow (read from the policies, not attempted).
- **AICT scope:** discovers AgentCore runtimes, not EKS pods, MCP servers, guardrails or per-ModelConfig attribution.

## CONFLICTS: playbook vs our verified evidence (ranked by planning impact)

| # | Playbook says | Verified reality (source) | Planning impact |
|---|---|---|---|
| 1 | §3.9 Hostile/Rogue expected defences: "unauthorized tool → Cedar deny", "tampered tool or skill → Cedar deny"; §2 "restrict `toolName` in the team Cedar ConfigMap" | Agents call undeclared tools and every call is ALLOW (gap 3). The team Cedar ConfigMap loads but decided 0 of 478 decisions in 48 h (#33). One shared principal `bootstrap-key` (#38). The AgentConfig Cedar overlay isn't wired (#39). Cedar never sees tool code, and Lambdas run unpinned `$LATEST` (gap 11, #59) | These tests will show **ALLOW, not deny**. Plan them as "what broke" findings (the adversarial bonus rewards that), not as passing defences |
| 2 | §2/§3.6/§3.9: "tampered ledger record → ledger verification fails"; "capture the ledger's own verification output"; "forged write → 401" | `audit-store.py` has no verify route and no hash chain or signatures (#13, gap 6). The 401 only shows a writer with no token is refused. The token is readable in every AgentConfig spec (#24) and in `get-agent-runtime` environment variables (resources verifier, today) | INTEGRITY must rest on corroboration across independent surfaces (gateway line, PDP, `/modaas/evidence`, X-Ray, AgentCore) plus the MANIFEST, never on a ledger self-check |
| 3 | §1.7 "Traces have no durable exporter here"; §2 "the OTEL collector discards traces, so Cockpit Trace is empty"; §3.11 gap "no durable OTEL trace exporter" | The collector exports to X-Ray, and X-Ray holds the gateway's traces (#32; re-confirmed today, carrying `modaas.action_id`) | **Don't put that gap in the gap list; it's false.** X-Ray is a durable join surface (action_id → `/modaas/evidence` → PDP) for RECONSTRUCT |
| 4 | §1.7 "S2 currently fails (7/10). Keep S1 and S3 passing" | Our runs: **S1 FAIL 6/8, S2 FAIL 5/10, S3 FAIL 8/10** (7/10 is the guide's number). All three fail by construction: the reference agents write no guardrail verdict, so the self-check fails every run (gap 4; memory `reference-agents-facts`) | "Close the gap" also needs the agents' evidence emission fixed (or our own agents), not just S2 logic |
| 5 | §1.7/§2 Module 10: "use the scenario switch to produce a passing run and a breaching run on demand" | The `network-twin` Lambda reads its own packaged dataset, so a breach on demand can't reach the agents (#58). The recipes are broken (#57). Agents query with element ids and get "no twin data" (gap 10). The twin has no site for S2 | Named pass/breach runs need another lever. Planning picks it (for C16, S2's 2.0M-token runaway is a natural breach) |
| 6 | §2 kill switch "~15 s to stop, ~50 s to resume" | Measured: nano-9b 33–41 s (calls still served meanwhile); super-120b ≤2 s; tools ~1–7 s; resume ~24–35 s. The pause is recorded as ALLOW in decision records (gap 4, #36) | Record requested vs effective times (the playbook says so). Don't quote 15 s |
| 7 | §1.0 "Each step is a span carrying the same trace id and run id"; §2 "Keep `traceparent`, or gateway run ids fragment" | The gateway `modaas.run_id` = the **baggage** CID (no baggage CID → the trace id). Agents mint their own trace ids, so ledger trace_ids ≠ the run trace (gap 7). `run_id` exists only on gateway pod stdout (ephemeral). The exporter sets `modaas.run_id`, but it doesn't arrive in CloudWatch (glossary verifier, #27). 24 h: 627 lines with a CID, 384 with the trace id | Propagate the CID via baggage. Snapshot the pod logs (they're the C16 figure of record). PDP/authz logs are pod-only too (not in CloudWatch). `/modaas/evidence` keeps 30 d; `/aws/modaas/gateway` 7 d |
| 8 | §3.3 C9 = "Latency **Average** / Errors Sum, period 3600" | Our Module 8 analysis: S2's runaway showed Errors = 0, and only hourly **Maximum** latency (278 s) revealed it. AgentCore latency is per INVOCATION and moves with call count (memory `prooflab-project`) | Planning decision: Maximum + Errors Sum (and/or gateway per-call duration). Average hides the runaway |
| 9 | §2/§3.8 "`ifabric_…` for every new agent, tool and CR" (SN handoff: "lowercase where Kubernetes requires it") | Kubernetes object names can't contain `_` (RFC 1123). `new-agent.sh` passes NAME straight into the AgentConfig name, with no validation. Live mapping: CR `my-agent` → runtime `my_agent-9AyPFbHh5Z` | Name CRs `ifabric-…`; AgentCore/AICT then show `ifabric_…`. A server dry-run would settle it formally (needs the user's OK) |
| 10 | §1.0 "the shared model gateway is where … budget is decided, and a run can be halted" | The gateway counts tokens per call but has no per-run budget or per-run halt. The only limits are account-wide ceilings and pausing a model/tool, which stops every run. Cedar has no token attributes. §3.2 itself concedes "label C16 post-run honestly" | Inline C16 = our build (bonus), not a platform feature |
| 11 | §3.10/§4.1 L2 "Show Monitor sessions or traces if available" | AICT's usage query filters `eventName="InvokeAgent"`; our AgentCore traffic has zero such events (memory `servicenow-context`). The SN handoff's discovered list (6 AI Functions) doesn't include `my_agent` | Expect Monitor to be empty for our agents. State it as a gap; check `my_agent` (and new `ifabric_` agents) after the next import |
| 12 | §3.5/§4.4 "ServiceNow human approval queue" = second enforcement point | By the playbook's own test (§1.6: an EP must "ask, wait, act"; "a dashboard … can refuse nothing"), a notify-only incident can't refuse anything | It counts as an EP only if something waits on the human (e.g. the S3 escalation holds the change until approved). Design risk for the bonus claim; planning decides |
| 13 | §2 "Four injected values … never hard-code them" | The platform writes the gateway key and ledger token as literal values in every AgentConfig spec and runtime env (#24; `get-agent-runtime` shows them). The env var names are `OPENAI_API_KEY` / `AGENTCORE_GATEWAY_MCP_TOKEN` / `AUDIT_WRITE_TOKEN`; no `GATEWAY_API_KEY` exists (resources verifier) | Fine as agent-code advice (read env, fail closed). It can't be met at the CR level; it's a gap-list fact (gap 6) |
| 14 | §2 "direct AgentCore creation [is] denied" | True for the participant role. The glossary verifier reports the IDE role can create, update and delete the AgentCore gateway (not double-checked) | Note only; never do it |
| 15 | §3.6 "record the S3 version id"; SN handoff §11.7 "integrity rests on … S3 versioning" | Our role is denied `GetBucketVersioning`, object lock and lifecycle on `team-evidence-…`. The bucket is empty today. `submit.sh`'s fallback bucket lookup (`… \| [0]`) returns empty in this account; it works only because `TEAM_EVIDENCE_BUCKET` is set | Unverified until the first upload (the put response shows a VersionId only if versioning is on). Keep TEAM_EVIDENCE_BUCKET set |
| 16 | §3.6 APPROVED "export `.status.governance.approvals` for each asset used" | Approvals are free-text annotations with an empty `signature`; EKS audit logging is off (all 5 types); a model swap needed no re-approval (gap 5, #46). Tools actually called ≠ tools declared (gap 3) | "Every asset in the chain" must include tools actually called, and must flag approvals older than the running version |
| 17 | §3.6 AUTHORIZED "keep the Cedar/PDP decision lines for both replicas" | Consistent, but decision lines carry no principal (it's in `/modaas/evidence`, always `bootstrap-key`); guardrail blocks and pauses are recorded ALLOW (gap 4); the PDP logs are pod-only | Capture both PDP pods before any restart. Report the real outcome per call via the gateway line |

## Steps the playbook implies that need the user's OK, or eat the shared budget

- **Writes to the cluster or AWS:**
  - pausing models or tools (kill-switch demo)
  - the forged-write and unauthorized-tool tests
  - new agents and ToolConfigs (CodeBuild → AgentConfig → approval annotation)
  - patching agents (model swap)
  - any Lambda change (never: shared and unpinned)
  - S3 submit
- **ServiceNow writes:** incidents through Arth's OAuth integration.
- **Budget:** a deliberate retry loop or runaway (S2 burned 80% of the hourly token ceiling in under 5 min). Serialize runs and stay under ~1 model req/s account-wide.

## Package notes

- **Contents:**
  - the playbook
  - the SN handoff
  - `prooflab/` (stdlib-only Python: `servicenow/{client,notifier,finding,delivery_log,cli}.py` + README + example; `tests/` with a fake ServiceNow server)
- **Credentials:** none real. The only credential-shaped string is a deliberate fake in a bad-credentials test (`tests/test_servicenow_adapter.py:109`).
- **Personal data:** the SN handoff names people (Arth; Sree, with an email address). The repo is PRIVATE.
- **Roster:**
  - Memory says "two-person team".
  - The SN handoff names Arth (ServiceNow workstream), Sree (control owner / accountable management) and "the teammate building the AWS side" (the user).
  - Flag for the user; don't resolve.
- **The SN handoff's live ServiceNow claims** (connection "iFabric Hackathon 2026" → account 613052889143, role `SgcAictReadOnlyAccessRole`; OAuth client credentials; INC0010231; owner user):
  - not verifiable by us, since we have no instance access
  - consistent with our AWS-side observations (the AICT role is live and reads our account)
- **Memory correction needed:** `servicenow-context` calls `platformdemoh8` "the vendor PDFs' demo instance, not ours". Per the SN handoff, it is the **shared hackathon instance**. Record it as "per the SN handoff, not independently verified".

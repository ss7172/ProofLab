---
name: servicenow-context
description: "Verified ServiceNow facts for planning (Module 11, AICT live in our account, the 3 vendor PDFs, Rail 1 script, curated docs) — pointer to the repo file notes/servicenow/servicenow-context.md and the key facts; plus the SN handoff from Arth (2026-10-05): shared instance platformdemoh8, AICT connection 'iFabric Hackathon 2026', OAuth integration user, INC0010231, the prooflab/servicenow package and its 2 confirmed adapter bugs"
metadata:
  node_type: memory
  type: project
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T23:58:00.000Z
---

**Full verified synthesis:** repo `notes/servicenow/servicenow-context.md`, with the raw reader notes and three reviews in `notes/servicenow/raw/`. Built on 2026-10-05 from 5 parallel reader subagents and 3 independent reviewers (all corrections applied), plus Claude's live read-only checks. The connector secret was checked for readability only, never printed.

**Key facts:**
- **AICT is live:** `ServiceNowAictUser` assumes `SgcAictReadOnlyAccessRole` about every minute (session always `613052889143-session`). The participant role can read its long-term IAM key secret, by design per Module 11.
- **Discovery:** only AgentCore runtimes and gateways. Bedrock ListAgents, SageMaker ListModelCards and agentcore ListBrowsers/ListCodeInterpreters are AccessDenied (template "deviation 6"). Module 11's "Bedrock agents and SageMaker models" is false here.
- **Usage counting:** a 15-min Logs Insights query on `/aws/bedrock/aict-invocations` with `filter eventName = "InvokeAgent"`, while our traffic has ZERO InvokeAgent events. So AICT's usage count for our agents is 0.
- **`/aws/bedrock/aict-invocations` = AWS-written CloudTrail data events (kept 7 d, re-checked 2026-10-05):**
  - **ConverseStream/Converse by the gateway role:** modelId + guardrailConfig. Each streamed call also has a service-event twin carrying the tokens and the guardrail's verdict (`No action.` / `Guardrail blocked.`). They hold no run, session or trace id, so they join a run only by time + role + model.
  - **InvokeAgentRuntime, with the invoking principal** (participant role / IDE role). **These DO carry the run** (corrected 2026-10-05 after live re-check; an earlier line here said "no session id either", from 03 F11, which had read only `requestParameters`):
    - `requestParameters` is empty, but `responseElements` holds the caller-sent `runtimeSessionId` (`<CID>-<hex>`), `traceParent` and `baggage` (`modaas-correlation-id=<CID>`), on 28 of 28 records.
    - So they join a run exactly, by CID and session id.
    - `eventTime` is the end of the call; the record is delivered 19–328 s later.
    - AICT's own usage query groups by `requestParameters.sessionId`, which is empty on these records.
    - Repo `architecture/work/10-f11-resolution.md`.
  - **A candidate independent evidence source:** WHO invoked which runtime for which run, timestamps, and the guardrail's verdict per call.
  - Validated integrity is S3-only and facilitator-only (our role is denied describe-trails, the bucket and validate-logs).
- **Role permissions:** explicitly DENIES token and credential retrieval (GetResourceApiKey etc.); no ListGuardrails.
- **Vendor PDFs** (recorded demos on instance `platformdemoh8`; the demos are not our live state). CORRECTED 2026-10-05: this line said `platformdemoh8` was "not ours", but per the SN handoff (not independently verified) it is the SHARED hackathon instance. From the demos:
  - Monitoring/evaluation covers only "Managed" agents.
  - Agent Studio run logs show no timestamps, run ids, identity, role or version.
  - Scores don't verify claimed actions.
  - The demo agent's approved role was admin.
- **Rail 1** `escalate-to-incident.py`: never checks for escalate, isn't idempotent, sets no assignee; needs SNOW_INSTANCE/USER/PASS; has --dry-run.
- **Curated docs:** 121 URLs; "Writing effectively for agentic AI" is flagged most useful.

**SN handoff (received 2026-10-05; every fact here is "per the SN handoff" unless dated otherwise; we have no instance access, so none is verified by us):**
- **Source:** `SERVICENOW_INTEGRATION_HANDOFF.md` from **Arth (the ServiceNow workstream**, with Claude Code) to "the teammate building the AWS side" (the user). The package (`prooflab/`, `HACKATHON_WINNING_PLAYBOOK.md`, `SERVICENOW_INTEGRATION_HANDOFF.md`) is now at the repo root; original in `~/Downloads/servicenow-integration-package/`. Our check of it: repo `notes/playbook/playbook-verification.md`.
- **Instance:** `platformdemoh8` is shared by all teams.
- **AICT connection "iFabric Hackathon 2026"** → our account, us-east-1, role `SgcAictReadOnlyAccessRole`, log group `/aws/bedrock/aict-invocations`. Import jobs run every 15 min (~4 min per cycle). Consistent with what we see on the AWS side (the role is assumed about every minute).
- **6 discovered "AI Function" records:** hackathon_helper, customer_experience_agent, network_resolution_agent v1+v2, it_resolution_agent v1+v2. **NOT `my_agent`:** the package's files predate my-agent's creation (08:59 UTC). New runtimes should appear within ~20 min (15-min import + ~4-min run); check `my_agent` after the next import.
- **Auth:** OAuth client credentials (app "iFabric Agent Assurance"). **Basic auth returned 401** for both accounts. Integration user **`ifabric.integration` (itil only)**. Get the client id and secret from Arth; never print or commit the secret.
  - The team enabled the Global property `glide.oauth.inbound.client.credential.grant_type.enabled` on the shared instance, disclosed in the handoff; the handoff's courtesy note to the facilitators was still pending.
- **Test incident INC0010231:** a TEST incident, created by the integration user and assigned to the owner. A second `notify` reused it; `check` went AWAITING_RESPONSE, then RESPONDED after the owner's note. Arth closes it before judging.
- **Owner of all three controls: Sree Annapurna Rallabandi** (the owner's ServiceNow user, named in the SN handoff §2, has admin + itil). **Sree = the user (user confirmed 2026-10-05).**
- **`prooflab/servicenow` package:** stdlib-only, CLI `selftest` / `notify [--dry-run]` / `check --cutoff` / `export`. The Finding contract (deterministic `finding_id`) binds evaluators, evidence files and incidents. `notify()` runs off the agent's path, for BREACHED / ESCALATED / monitoring-gap findings. 46 tests per its checklist; **46 offline tests pass (2026-10-05).**
- **Two adapter bugs CONFIRMED (2026-10-05, code reading + offline reproduction):**
  - (a) `notify --dry-run` returns and logs DELIVERED when a matching incident already exists (`notifier.py:132-136`). The handoff's §5.4 dry run on the example finding (mapped to INC0010231) hits it.
  - (b) A 0-row, HTTP 200 `sys_journal_field` read (the ACL) keeps `readable=True`, so `check` can report NO_RESPONSE_OBSERVED when someone other than the owner updated the incident last (`notifier.py:189-234`).
  - Both are Arth's code; who fixes them is the user's call.
- **Risks accepted by the user (2026-10-05; the remaining risks are "allowed"), not blockers:** the Global OAuth property the team enabled on the shared instance (Arth), the two adapter bugs above, and AICT Monitor likely empty for our agents (AICT's usage query counts only `InvokeAgent` events).
- This partly answers the instance-access question below: an instance, an integration user and OAuth credentials exist (held by Arth).

**Open questions:** ServiceNow instance access and roles; AICT exports for the Evidence Pack; widening the AICT query; facilitator validate-logs; whether AICT is required for Level 2.

Related: [[challenge-requirements]], [[prooflab-project]], [[platform-verified-facts]], [[workshop-progress]]

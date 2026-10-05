---
name: servicenow-context
description: "Verified ServiceNow facts for planning (Module 11, AICT live in our account, the 3 vendor PDFs, Rail 1 script, curated docs) — pointer to the repo file notes/servicenow/servicenow-context.md and the key facts"
metadata:
  type: project
---

**Full verified synthesis:** repo `notes/servicenow/servicenow-context.md`, with the raw reader notes and three reviews in `notes/servicenow/raw/`. Built on 2026-10-05 from 5 parallel reader subagents and 3 independent reviewers (all corrections applied), plus Claude's live read-only checks. The connector secret was checked for readability only, never printed.

**Key facts:**
- **AICT is live:** `ServiceNowAictUser` assumes `SgcAictReadOnlyAccessRole` about every minute (session always `613052889143-session`). The participant role can read its long-term IAM key secret, by design per Module 11.
- **Discovery:** only AgentCore runtimes and gateways. Bedrock ListAgents, SageMaker ListModelCards and agentcore ListBrowsers/ListCodeInterpreters are AccessDenied (template "deviation 6"). Module 11's "Bedrock agents and SageMaker models" is false here.
- **Usage counting:** a 15-min Logs Insights query on `/aws/bedrock/aict-invocations` with `filter eventName = "InvokeAgent"`, while our traffic has ZERO InvokeAgent events. So AICT's usage count for our agents is 0.
- **`/aws/bedrock/aict-invocations` = AWS-written CloudTrail data events:**
  - ConverseStream/Converse by the gateway role, with modelId + guardrailConfig
  - InvokeAgentRuntime with the invoking principal (participant role / IDE role)
  - No run id.
  - **A candidate independent evidence source** (WHO invoked, timestamps, guardrail per call).
  - Validated integrity is S3-only and facilitator-only (our role is denied describe-trails, the bucket and validate-logs).
- **Role permissions:** explicitly DENIES token and credential retrieval (GetResourceApiKey etc.); no ListGuardrails.
- **Vendor PDFs** (demo instance platformdemoh8, not ours):
  - Monitoring/evaluation covers only "Managed" agents.
  - Agent Studio run logs show no timestamps, run ids, identity, role or version.
  - Scores don't verify claimed actions.
  - The demo agent's approved role was admin.
- **Rail 1** `escalate-to-incident.py`: never checks for escalate, isn't idempotent, sets no assignee; needs SNOW_INSTANCE/USER/PASS; has --dry-run.
- **Curated docs:** 121 URLs; "Writing effectively for agentic AI" is flagged most useful.

**Open questions:** ServiceNow instance access and roles; AICT exports for the Evidence Pack; widening the AICT query; facilitator validate-logs; whether AICT is required for Level 2.

Related: [[challenge-requirements]], [[prooflab-project]], [[platform-verified-facts]], [[workshop-progress]]

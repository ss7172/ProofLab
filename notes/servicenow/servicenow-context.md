# ServiceNow (Module 11, AI Control Tower, AI Agent Studio): verified context for planning

Working notes for our team's planning, not part of the submission. Compiled on 2026-10-05 from:
- **Our own read-only AWS checks** in the event account. The connector secret was checked for readability only; its values were never printed.
- **Five reader subagents:**
  - the 12-page connection-setup PDF
  - the 30-page AI Control Tower console PDF
  - the 86-page AI Agent Studio PDF, read in two halves
  - the hackathon's curated ServiceNow docs page, `escalate-to-incident.py` and the rails diagram
- **Three independent reviewers,** who re-checked the readers' claims against the PDFs, the kit and the live account. Every correction they raised is applied below.

Raw reader notes and the three reviews are in `raw/`. Where they disagree with this file, this file wins.

Labels: **[live]** checked in our account · **[PDF]** shown in a vendor PDF · **[kit]** in the workshop kit · **[inf]** our inference.

---

## 1. What is live in our account

| Fact | Evidence |
|---|---|
| **The AICT stack is deployed** (`a-03-servicenow-aict`): `AictConfigured=true`, role `SgcAictReadOnlyAccessRole`, invocation log group `/aws/bedrock/aict-invocations`, target account = ours | [live] stack outputs. The facilitators (`WSOpsRole`) created it on 2026-10-04 |
| **The deployed stack differs from the kit's template:** 8 parameters (the kit's 7 plus `ConnectorSecretArn`) and 7 outputs (the kit's 4 plus secret, role and account) | [live] `describe-stacks`; [kit] `servicenow/03-servicenow-aict.yaml`. The template's header says no IAM user or key exists, yet `ServiceNowAictUser` does (notes #30) |
| **The connector uses a long-term IAM user key, and any participant can read it:** secret `team-servicenow-aict-connector-…`, AccessKeyId `AKIA…` (20 characters), SecretAccessKey (40) | [live] readable with participant credentials (values not printed). Module 11 says so by design |
| **The connector role's trust policy** names one principal, `user/ServiceNowAictUser`, with no condition. The user has no policies of its own | [live] |
| **What the connector role may do:** **allowed** on `*`: `ListAgentRuntimes` / `GetAgentRuntime`, `ListGateways` / `GetGateway` / `List`/`GetGatewayTarget`, `List`/`GetInferenceProfile`, Logs `StartQuery` / `GetQueryResults`, `cloudtrail:LookupEvents`, `ec2:DescribeRegions`, `sts:GetCallerIdentity`. **Explicitly denied** (`DenyTokenAndSecretIssuance`): `GetWorkloadAccessToken*`, `GetResourceApiKey`, `GetResourceOauth2Token`. It has no `bedrock:ListGuardrails` | [live] inline policy `SgcAictReadOnlyAccessPolicy` |
| **AICT is actively connected.** `ServiceNowAictUser` assumes the role about every minute, always as session `613052889143-session` (our account id, not one session per discovery run as Module 11 says) | [live] CloudTrail, 2026-10-05 |
| **AICT discovers only AgentCore runtimes and gateways.** `GetAgentRuntime`, `ListAgentRuntimes` and `ListGateways` succeed. Bedrock `ListAgents`, SageMaker `ListModelCards` and AgentCore `ListBrowsers` / `ListCodeInterpreters` fail with **AccessDenied** every cycle | [live] CloudTrail. [kit] the template's "deviation 6" removed the Bedrock Agents and SageMaker permissions |
| **AICT's usage count misses all our traffic.** Every 15 minutes it queries `/aws/bedrock/aict-invocations` with `… \| filter eventName = "InvokeAgent"` (classic Bedrock Agents). The log group holds **zero** `InvokeAgent` events (531 events: 492 `ConverseStream`, 11 `Converse`, 28 `InvokeAgentRuntime`) | [live] CloudTrail `StartQuery` request parameters; a log-group scan |

### The invocation log group is an AWS-written record

`/aws/bedrock/aict-invocations` holds CloudTrail data events from the facilitators' trail `sgc-aict-bedrock-trail`, written by AWS rather than by our agents:
- **Model calls** (`ConverseStream` / `Converse`), made by the gateway's role `a-01-eks-cluster-agentgateway-bedrock`. Request parameters are `modelId`, `guardrailConfig` and `inferenceConfig`; no prompts.
- **Agent invocations** (`InvokeAgentRuntime`), made by the principal that invoked them: our participant role, or the IDE role.
- **A few direct `Converse` calls** by the participant role (3 of 11).
- **No run id.** Records join by time, and by session id for agent invocations.

Limits [live]:
- **Integrity is a facilitator-only check.** The trail has log-file validation on (per its CreateTrail history), but validation covers the **S3** copy only, not this CloudWatch Logs copy. Our role is denied `describe-trails`, listing the trail's bucket and `validate-logs`.
- **No events arrived after 09:13 UTC.** That fits our making no model or agent calls since then; the trail wasn't stopped.

---

## 2. Module 11's claims vs what we found

| Module 11 says | What we found |
|---|---|
| AICT discovers *"your AgentCore runtimes, Bedrock agents and SageMaker models"* | Only AgentCore runtimes and gateways. The Bedrock-agent and SageMaker calls are denied [live] |
| *"Which ModelConfig served a call"* isn't visible, because all calls arrive under the gateway's IAM principal | Correct [live]. And AICT's counter doesn't count those calls at all |
| *"MoDaaS guardrails (the connector role lacks bedrock:ListGuardrails)"* | Correct [live]. The per-call `guardrailConfig` *is* in the CloudTrail data events, though AICT doesn't query it |
| *"The session name identifies the AICT discovery run"* | It's always `613052889143-session` [live] |
| *"Participants do not enter these values"* | The console PDF says *"you will set up the connector"* (p27, p29) [PDF]. Any participant can read the connector key [live] |
| Facilitator step: confirm the role with `iam get-role` | Works with participant credentials too [live] |
| Rail 1 *"Module 7 section 6 shows the escalate disposition"* | No Module 7 page has a section 6. The Challenge brief cites it too (for `score-run.py`) [kit] |

---

## 3. The three vendor PDFs

All three are recorded demos on a vendor instance (`platformdemoh8`; the console demo's data is dated 2026-09-30). None of it is our live state. Captions often contradict the screenshots, so trust the screenshots.

### Creating and Verifying Amazon Connection Setup (12 pages)
- **Form fields** (p5–8): Connection name, Management account ID and CloudWatch log group carry required-field asterisks. Only "STS assume role" visibly shows *"Field is required"* (p7), so "won't submit without the log group" is inferred.
- **Role entry:** the STS role is entered as the bare name `SgcAictReadOnlyAccessRole` (p8). The template's output suggests handing over the full ARN.
- **Schedules** (p9): 4 parent jobs and 14 scheduled imports, default Daily and inactive.
- **What it leaves out:** the PDF never explains what the log group is for. Its name, `…invocations`, appears only in a screenshot, and the narration never says "invocation counting". It doesn't name its instance, and its connection isn't one of the two shown in the console PDF.

### AI Control Tower console: discovered assets and AI agents (30 pages)
- **Managed vs Unmanaged:** monitoring covers **"Managed"** agents only. Unmanaged ones show *"Unable to show Monitor dashboard"* (p10). *"Only managed assets are evaluated"*; *"Only Agentic AI assets are evaluated"* (p20). Sessions are sampled (p21).
- **The demo's discovered AWS agents:** `network_resolution_agent` is Managed and Approved; `customer_experience_agent` and `it_resolution_agent` are Unmanaged (p4). Same names as our runtimes, on their instance.
- **Evaluated sessions:** only 8 of 38 are visible. The one trace shown is a LangGraph/OpenAI app (`traceloop_*`, `tool_calls: []`, p21, p25–26), so whether AWS agent runs are evaluated is **not shown**. The narration's *"whole evidence track"* (p26) isn't demonstrated.
- **Quality scores don't check what the agent claims it did:** an unperformed payroll update scores 100% Answer Relevancy (p22–26). No PII or action-check metric is shown.
- **Missing:** authorisation decisions, approval history, integrity proof, export, incident creation. "Approved" is an editable field. Runtime-security figures are *"demo data"* (p15). An unopened **Integrations › Traces** tab (p28) is the only visible way traces could come in.

### Create and Manage AI Agents in AI Agent Studio (86 pages)
- **AWS link (names only):** the scope is the *"AI Service Graph Connector for Amazon"* app (p14–16), and two import-set tables are named *"SG-AWS AgentCore AI Age…"* (p3). No connection, credential or imported record is shown.
- **Access and identity:**
  - User access (specific roles / any authenticated / public) auto-generates an access-control rule (p29–32).
  - Agents run as a **"Dynamic user"** with approved roles, or a dedicated **"AI user"** (p34–43).
  - The demo lists **`admin`** as the approved role right after the platform's own *"Grant this privilege carefully"* warning (p44–46). How approved roles combine with the invoking user's roles is never shown.
  - A banner reads *"18 agents have no ACL configured"* (p2).
- **Tools:** Flow actions only, run in **Autonomous** mode (p25). No human-approval step appears anywhere.
- **Models:** a *"Select unsupported LLMs"* field (p22–24) and AI Admin Center items for providers and *AI Guardian* (p8, p13). No provider is named and Bedrock doesn't appear. *"Allow third party to access this AI agent – Enable for external discovery"* is off throughout (p22–24).
- **Run evidence: the "AI agent decision logs"** (p75–85) nest:
  - *Access verification – Completed*
  - ReAct engine rows: *Thought*, *Action reasoning*, action name and inputs, durations
  - Tool rows: *Inputs*, *Output*, *Output fields*, *Response*

  The run page shows **no timestamps, run or trace ids, user, approved role or version**. The demo run's stop rests only on the model's own reasoning text; the tool output is `null` and the final answer isn't shown.
- **Missing:** the demo saved no trigger, so the trigger's "Run as" column stays empty (p47, p52). No agent creates an incident; the record-trigger launches an agent instead. No AWS, MCP, A2A or external model appears on p44–86 (AWS does appear on p3 and p14–16).
- **[inf]** Taken together the demo is permissive: any logged-in user can use the agent, it runs with an `admin` approved role, its tools are autonomous, and it is activated.

---

## 4. Kit material

- **Rail 1: `servicenow/escalate-to-incident.py`.**
  - It reads the run's chain from the audit store (`GET /records?cid=`, no token, in-cluster or via a port-forward) and POSTs one ServiceNow `incident` with 8 fields: short_description, description, work_notes (the chain), urgency 2, impact 2, category network, `correlation_id` = CID, correlation_display.
  - It needs `SNOW_INSTANCE` (bare host), `SNOW_USER` and `SNOW_PASS` (Basic auth), and has a `--dry-run` that needs no instance.
  - **Traps:**
    - it **never checks for an `escalate` disposition**, so any CID files *"Agents escalated … human decision required"*
    - it **isn't idempotent**: a rerun files a duplicate
    - it sets no assignee or group
    - a CID with no records exits before the POST
    - the CID isn't URL-encoded
- **`images/servicenow-two-rails.svg`** actually shows **three rails** (*"three rails, different jobs"*), and no guide page uses it:
  1. ITSM and humans, fed from the ledger.
  2. AICT, *"does not by itself constrain runtime"*.
  3. AI Agent Studio agents calling our MCP gateway.
- **The curated hackathon docs page** (kit `kb/index.json`, chunks 1138–1157): 123 links (Build 75 · Secure 29 · Govern 19), 121 unique URLs.
  - It flags *"Writing effectively for agentic AI"* as the single most useful page.
  - The Secure group includes Kill Switch, AI Guardian and MCP auth.
  - The full list is in `raw/D-docs-and-rails.md` §1.4.
- **`data/it-incidents.json`** is 7 mock incidents read by the `runbook-lookup` Lambda, not a ServiceNow export.

---

## 5. What this means for planning (facts, not decisions)

- **Level 2 ("ServiceNow Control Tower adds additional observability"):**
  - Today AICT can contribute an **inventory of our AgentCore runtimes and gateway** (WHAT, at the asset level). It doesn't count our usage (the `InvokeAgent` filter), see guardrails, or know which model alias served a call.
  - Monitoring and evaluation apply only to agents marked **Managed** on the ServiceNow side.
- **An AWS-written evidence source** we hadn't used: `/aws/bedrock/aict-invocations`.
  - It holds caller identity, timestamps and `guardrailConfig` for every model call, and the invoking principal for every agent invocation.
  - It's readable with participant credentials and independent of our agents, so it can corroborate WHO (the operator or invoker), RECONSTRUCT (timestamps) and INTEGRITY (not agent-written).
  - It carries no run id, and **validated** integrity needs a facilitator (S3 copy only).
- **Human loop (Rail 1):** a stretch goal. It needs a ServiceNow instance and credentials, plus fixes: check the disposition, and make it idempotent via `correlation_id`.
- **The vendor demos show the very gaps our gap list names:** run logs without identity, ids or version; scores that don't check claimed actions; no integrity or approval history.

## 6. Open questions for organisers or facilitators

1. Do we have a ServiceNow instance (or a personal developer instance), with which roles and credentials? Who connects it?
2. Can AICT-side screenshots or exports of our discovered assets go in the Evidence Pack?
3. Can AICT's usage query include `InvokeAgentRuntime` and `Converse*`, or can the denied discovery permissions be restored?
4. Can a facilitator run `cloudtrail validate-logs` on `sgc-aict-bedrock-trail` for our event window?
5. Is AICT required for Level 2? Which roles does `escalate-to-incident.py` need to write `work_notes`?

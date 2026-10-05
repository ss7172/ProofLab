# D: ServiceNow docs set, escalate-to-incident.py, and the "rails"

Read-only research notes, 2026-10-05. I modified no file except this one. I made no AWS calls and no git calls, and I printed no secrets.

**Labels used throughout**

- `Q[n]` = verbatim guide text from chunk *n* of `workshop-static/kb/index.json`. That is the kit's guide index: 1179 chunks, and `workshop-assets/kb/index.json` is byte-identical.
- `VER` = verified by reading kit files or code (path given).
- `INF` = my inference, not verified.
- `WF` = returned by the WebFetch tool's summarizer model (rendered page, not independently verified).
- `MEM` = taken from the team's memory notes, not re-verified here.

---

## 0. TL;DR

1. **The login-gated page is fully recoverable.** It is `workshop/content/resources/servicenow-docs.en.md`, chunks 1138–1157 (VER). ServiceNow wrote it, and it is "reproduced here unchanged" (Q[1138]).
   - It has three sets: **Build** (75 links), **Secure** (29) and **Govern / AI Control Tower** (19). That is 123 links in total, with 121 unique URLs because two security-controls links appear in both Build and Secure.
   - All of them point to the **Australia** release (Q[1139]).
   - The full verbatim reconstruction is in §1.4.
2. **"Rail 1" is the ITSM/human rail.** When an agent's disposition is `escalate`, the evidence chain for that correlation id becomes a ServiceNow **incident**, and `correlation_id` links the incident queue to the ledger (Q[1166] and the SVG).
   - `escalate-to-incident.py` is the starting point, and the guide calls wiring it into your own agent **a stretch goal** (Q[1166]).
3. **The SVG is named "two-rails" but its title says "three rails, different jobs"** (VER):
   - Rail 1: ITSM, humans.
   - Rail 2: AI Control Tower, the record of assets ("does not by itself constrain runtime").
   - Rail 3: ServiceNow agents as *callers* of the governed MCP gateway.

   No indexed guide page references this image (VER).
4. **`escalate-to-incident.py`** needs Python 3 stdlib only and reads `GET /records?cid=` JSONL from the audit store; reads are open, so no token is needed. With `SNOW_INSTANCE`, `SNOW_USER` and `SNOW_PASS` set, it **POSTs to `https://<instance>/api/now/table/incident`** using **Basic auth**.
   - **`--dry-run` works without ServiceNow** (it still needs the audit store).
   - **Two traps (VER):**
     - It files an "Agents escalated … human decision required" incident for **any** correlation id; nothing checks for an `escalate` disposition.
     - It is **not idempotent**; running it twice creates two incidents.
5. **The public landing pages render in WebFetch** and now default to the **Brazil** release (updated 10 Sep 2026) (WF). The nine AICT areas match the curated list structurally.
   - The hashed short links could not be validated: the docs site is a JavaScript single-page app that returns HTTP 200 even for bogus paths (VER).
6. **There are discrepancies in Module 11.**
   - The guide text describes an IAM user plus a Secrets Manager key with outputs `ServiceNowAictSecretArn` etc. The kit template creates *no* user and has different outputs, while the live account *does* have a user and key (MEM, notes #30).
   - New here: the template's "deviation 6" removed the permissions for Bedrock Agents and SageMaker. INF: AICT can then discover only AgentCore runtimes and gateways (plus inference profiles), not the "Bedrock agents and SageMaker models" that Module 11 claims.

---

## 1. Task 1: the hackathon ServiceNow documentation page

### 1.1 Source and provenance

- **Source:** `workshop/content/resources/servicenow-docs.en.md`, chunks **1138–1157** (VER).
  - Front matter: `title: "ServiceNow documentation set"`, `weight: 20`, `reference: true`.
  - On the workshop site it is the `/resources/servicenow-docs` page that Module 11 links (Q[1158]).
- Q[1138]: "ServiceNow prepared this guide to its public product documentation for the hackathon (August 2026). It is reproduced here unchanged so you can bookmark it and work from it during the event. Use it with [Module 11](/servicenow-integration), which shows how AI Control Tower sees the assets you govern on this platform, and with [Module 9](/build-your-own-agent) if your team also builds an agent on the ServiceNow side."
- **Other pages link to it** (VER): the Resources index (Q[1137]), the Glossary checkpoint (Q[1116]), Module 9 (Q[860]) and Module 11 (Q[1158]).
- **How I reconstructed it** (INF):
  - The chunker splits at headings, so I rebuilt the heading levels from `heading_path`: H2 is a set and H3 is a subsection.
  - The two tables (tool types, and the nine AICT areas) were flattened onto one line in the index. I re-flowed them, adding only line breaks.
  - The ordered list under "Read these four first" is numbered **9–12**, continuing from **1–8** under "Build an agent, in order". The source page probably has one running ordered list that the headings break up, which is a markdown rendering artifact. Read the numbers as "in this order" only.

### 1.2 Instructions on the page (verbatim)

- **How to use this set** (Q[1139]): "Three documentation sets, one platform. Everything here comes from the public ServiceNow product documentation portal, so you can share it, bookmark it, and work from it during the hackathon. / Set one covers how to build an AI agent. Set two covers what that agent is allowed to see and do. Set three covers how you govern the whole portfolio once you have more than one. Start with set one if you are building. Read set two before you connect an agent to anything that writes. / All links point to the Australia release of the Enable AI documentation. Use the release selector at the top of any documentation page to switch to a different version."
- **Set 1 highlight** (Q[1140]): "[Writing effectively for agentic AI](…/gg-creating-aia.html) The single most useful page for a hackathon team." Module 9 repeats this (Q[860]).
- **Set 2 intro** (Q[1147]): "These pages cover enforcement inside the agent: what identity it runs as, what records it can reach, and how to stop it."
- **Set 2 reading order** (Q[1148] heading): "Read these four first, in this order":
  1. Security for AI agents
  2. ACLs, role masking, and user identities
  3. Role masking
  4. Deny-by-default ACL configuration
- **Set 3 intro** (Q[1153]): "AI Control Tower governs the portfolio: inventory, lifecycle, risk posture, and value. It is a different layer from set two. Registering an agent here does not by itself constrain what that agent can do at runtime." The rails SVG quotes this idea for Rail 2.

### 1.3 Build / Secure / Govern map

| Set (page heading) | Chunks | Links | Subsections |
|---|---|---|---|
| **1 Build**: "Creating and configuring AI agents" | 1140–1146 | 75 | Start here: concepts and best practices (10) · Set up your instance (13) · Build an agent, in order (8 + 3) · Tool types an agent can call (12) · Agentic workflows, for multi-agent orchestration (12) · External agents, MCP, and evaluation (17) |
| **2 Secure**: "AI agent security and data access" | 1147–1152 | 29 | Read these four first, in this order (4) · Controls on a single agent or workflow (6, incl. **Kill Switch**) · Guardrails at runtime (2: **AI Guardian**) · Data handling and privacy (7) · Tenancy, credentials, and model routing (10, incl. **MCP server auth: OAuth 2.1 / API key / connection + credential alias**) |
| **3 Govern**: "AI Control Tower" | 1153–1157 | 19 | Landing page (1) · The nine documentation areas (9) · Working pages inside the product (4) · Related pages in AI Admin Center (4) · For more information (1) |

- Two URLs appear in both Set 1 and Set 2: `define-sec-controls-aia.html` and `define-sec-controls-aw.html`. That gives 121 unique URLs (VER).
- In Set 3, **12 links are hashed short links** of the form `servicenow.com/docs/<22-char id>`, not `/r/intelligent-experiences/*.html` pages: 8 of the 9 areas plus all 4 working pages (VER).

### 1.4 Reconstructed page (verbatim chunk text; headings rebuilt from `heading_path`; tables re-flowed)

#### ServiceNow documentation set  _(page title from front matter; Q[1138])_

<!-- chunk 1138 (workshop/content/resources/servicenow-docs.en.md#00) -->
ServiceNow prepared this guide to its public product documentation for the
hackathon (August 2026). It is reproduced here unchanged
so you can bookmark it and work from it during the event. Use it with
[Module 11](/servicenow-integration), which shows how AI Control Tower sees the
assets you govern on this platform, and with
[Module 9](/build-your-own-agent) if your team also builds an agent on the
ServiceNow side.

#### How to use this set

<!-- chunk 1139 (workshop/content/resources/servicenow-docs.en.md#01) -->
Three documentation sets, one platform. Everything here comes from the public ServiceNow product documentation portal, so you can share it, bookmark it, and work from it during the hackathon.

Set one covers how to build an AI agent. Set two covers what that agent is allowed to see and do. Set three covers how you govern the whole portfolio once you have more than one. Start with set one if you are building. Read set two before you connect an agent to anything that writes.

All links point to the Australia release of the Enable AI documentation. Use the release selector at the top of any documentation page to switch to a different version.

#### Creating and configuring AI agents — SET 1: BUILD

##### Start here: concepts and best practices

<!-- chunk 1140 (workshop/content/resources/servicenow-docs.en.md#02) -->
- [AI Agent Studio overview](https://www.servicenow.com/docs/r/intelligent-experiences/ai-agent-studio.html)
- [Understand AI agents](https://www.servicenow.com/docs/r/intelligent-experiences/understand-na-aia.html)
- [AI agents best practices](https://www.servicenow.com/docs/r/intelligent-experiences/aia-best-practices.html)
- [AI agents capabilities](https://www.servicenow.com/docs/r/intelligent-experiences/na-aia-capabilities.html)
- [Writing effectively for agentic AI](https://www.servicenow.com/docs/r/intelligent-experiences/gg-creating-aia.html) The single most useful page for a hackathon team.
- [Example AI agent](https://www.servicenow.com/docs/r/intelligent-experiences/example-aia.html)
- [Example agentic workflow](https://www.servicenow.com/docs/r/intelligent-experiences/example-aw.html)
- [Group Action Framework](https://www.servicenow.com/docs/r/intelligent-experiences/group-action-framework.html)
- [Version control](https://www.servicenow.com/docs/r/intelligent-experiences/version-control.html)
- [AI agent learning](https://www.servicenow.com/docs/r/intelligent-experiences/agent-learning.html)

##### Set up your instance

<!-- chunk 1141 (workshop/content/resources/servicenow-docs.en.md#03) -->
- [Install ServiceNow Otto AI Agents](https://www.servicenow.com/docs/r/intelligent-experiences/install-ai-agents-plugins.html)
- [Set up AI agents](https://www.servicenow.com/docs/r/intelligent-experiences/set-up-na-aia.html)
- [Select the model provider](https://www.servicenow.com/docs/r/intelligent-experiences/select-aia-llm.html)
- [Set up long-term memory](https://www.servicenow.com/docs/r/intelligent-experiences/long-term-memory-aia.html)
- [Long-term memory categories](https://www.servicenow.com/docs/r/intelligent-experiences/aia-ltm-categories.html)
- [Create a long-term memory category](https://www.servicenow.com/docs/r/intelligent-experiences/create-ltm-category.html)
- [Map a memory category to an agent](https://www.servicenow.com/docs/r/intelligent-experiences/map-ltm-aia.html)
- [Configure the Group Action Framework](https://www.servicenow.com/docs/r/intelligent-experiences/configure-gaf.html)
- [Set up AI Search for the Group Action Framework](https://www.servicenow.com/docs/r/intelligent-experiences/setup-ai-search-gaf.html)
- [Multiple conversations](https://www.servicenow.com/docs/r/intelligent-experiences/multiple-conversations-aia.html)
- [Citations in AI agents](https://www.servicenow.com/docs/r/intelligent-experiences/citations-aia.html)
- [Follow-up conversations](https://www.servicenow.com/docs/r/intelligent-experiences/aia-follow-up-convsnts.html)
- [Usage, failure, and latency notifications](https://www.servicenow.com/docs/r/intelligent-experiences/config-aia-notifications.html)

##### Build an agent, in order

<!-- chunk 1142 (workshop/content/resources/servicenow-docs.en.md#04) -->
1. [Create an AI agent](https://www.servicenow.com/docs/r/intelligent-experiences/configure-next-best-action-agent.html)
2. [Find AI agents](https://www.servicenow.com/docs/r/intelligent-experiences/find-ai-agents.html)
3. [Define the specialty](https://www.servicenow.com/docs/r/intelligent-experiences/define-specialty.html)
4. [Add tools and information](https://www.servicenow.com/docs/r/intelligent-experiences/add-tool-aia.html)
5. [Define security controls](https://www.servicenow.com/docs/r/intelligent-experiences/define-sec-controls-aia.html)
6. [Add a trigger](https://www.servicenow.com/docs/r/intelligent-experiences/add-trigger-aia.html)
7. [Select channels and status](https://www.servicenow.com/docs/r/intelligent-experiences/channels-access-aia.html)
8. [Test execution manually](https://www.servicenow.com/docs/r/intelligent-experiences/test-ai-agent.html)

Also: duplicate, modify, and delete.

<!-- chunk 1143 (workshop/content/resources/servicenow-docs.en.md#05) -->
- [Duplicate an AI agent](https://www.servicenow.com/docs/r/intelligent-experiences/clone-ai-agent.html)
- [Modify an AI agent](https://www.servicenow.com/docs/r/intelligent-experiences/modify-ai-agent.html)
- [Delete an AI agent](https://www.servicenow.com/docs/r/intelligent-experiences/delete-ai-agent.html)

##### Tool types an agent can call

<!-- chunk 1144 (workshop/content/resources/servicenow-docs.en.md#06) -->
| Tool type | What it gives the agent |
|----|----|
| [AI skill](https://www.servicenow.com/docs/r/intelligent-experiences/add-skill-ai-agent.html) | A published skill, including custom ones built in AI Skill Kit |
| [Catalog item](https://www.servicenow.com/docs/r/intelligent-experiences/add-catalog-ai-agent.html) | Submits a service catalog request for the requester |
| [Conversational topic](https://www.servicenow.com/docs/r/intelligent-experiences/add-va-topic-ai-agent.html) | An existing Virtual Agent topic flow |
| [Desktop action](https://www.servicenow.com/docs/r/intelligent-experiences/add-desktop-action-ai-agent.html) | Work in desktop and browser applications off-platform |
| [File upload](https://www.servicenow.com/docs/r/intelligent-experiences/add-file-retrieval.html) | Reads content from a file the requester attaches |
| [Flow action](https://www.servicenow.com/docs/r/intelligent-experiences/add-flow-action-ai-agent.html) | A single action from Flow Designer |
| [Knowledge Graph](https://www.servicenow.com/docs/r/intelligent-experiences/add-knowledge-graph.html) | Relationship-aware retrieval across connected records |
| [Record operation](https://www.servicenow.com/docs/r/intelligent-experiences/add-database-op-ai-agent.html) | Reads, creates, or updates records on a table |
| [Script](https://www.servicenow.com/docs/r/intelligent-experiences/add-script-ai-agent.html) | Server-side logic the other tool types cannot express |
| [Search retrieval](https://www.servicenow.com/docs/r/intelligent-experiences/add-retriever-ai-agent.html) | An AI Search retriever over indexed sources |
| [Subflow](https://www.servicenow.com/docs/r/intelligent-experiences/add-sub-flow-ai-agent.html) | A full subflow, for multi-step deterministic work |
| [Web search](https://www.servicenow.com/docs/r/intelligent-experiences/add-web-search-ai-agent.html) | Public web results |

##### Agentic workflows, for multi-agent orchestration

<!-- chunk 1145 (workshop/content/resources/servicenow-docs.en.md#07) -->
- [Create an agentic workflow](https://www.servicenow.com/docs/r/intelligent-experiences/configure-use-case-ai-agents.html)
- [Define key requirements](https://www.servicenow.com/docs/r/intelligent-experiences/define-key-requirements.html)
- [Define security controls](https://www.servicenow.com/docs/r/intelligent-experiences/define-sec-controls-aw.html)
- [Add a trigger](https://www.servicenow.com/docs/r/intelligent-experiences/add-trigger-aw.html)
- [Select channels and access](https://www.servicenow.com/docs/r/intelligent-experiences/channels-access-aw.html)
- [Activate an agentic workflow template](https://www.servicenow.com/docs/r/intelligent-experiences/activate-aia-use-case.html)
- [Duplicate an agentic workflow](https://www.servicenow.com/docs/r/intelligent-experiences/clone-aia-usecase.html)
- [Modify an agentic workflow](https://www.servicenow.com/docs/r/intelligent-experiences/modify-aia-use-case.html)
- [Test execution manually](https://www.servicenow.com/docs/r/intelligent-experiences/test-aia-use-case.html)
- [Delete an agentic workflow](https://www.servicenow.com/docs/r/intelligent-experiences/delete-aia-use-case.html)
- [In-product agentic AI](https://www.servicenow.com/docs/r/intelligent-experiences/in-product-agentic-ai.html)
- [Platform agentic workflows](https://www.servicenow.com/docs/r/intelligent-experiences/platform-use-cases.html)

##### External agents, MCP, and evaluation

<!-- chunk 1146 (workshop/content/resources/servicenow-docs.en.md#08) -->
- [Create an external agent](https://www.servicenow.com/docs/r/intelligent-experiences/create-external-aia.html)
- [Integrating external AI agents](https://www.servicenow.com/docs/r/intelligent-experiences/external-agent-protocols.html)
- [ServiceNow AI agents as secondary agents](https://www.servicenow.com/docs/r/intelligent-experiences/secondary-agent.html)
- [External agents with Agent2Agent](https://www.servicenow.com/docs/r/intelligent-experiences/create-a2a-agent.html)
- [Model Context Protocol Client](https://www.servicenow.com/docs/r/intelligent-experiences/mcp-client.html)
- [Install Model Context Protocol Client](https://www.servicenow.com/docs/r/intelligent-experiences/install-mcp-client.html)
- [Add an MCP server in AI Agent Studio](https://www.servicenow.com/docs/r/intelligent-experiences/add-mcp-client-on-ai-agent-studio.html)
- [Add a Model Context Protocol tool](https://www.servicenow.com/docs/r/intelligent-experiences/add-mcp-server-tool.html)
- [Model Context Protocol Client reference](https://www.servicenow.com/docs/r/intelligent-experiences/mcp-reference.html)
- [Evaluate agentic AI assets](https://www.servicenow.com/docs/r/intelligent-experiences/agentic-evals.html)
- [Guidelines for evaluations](https://www.servicenow.com/docs/r/intelligent-experiences/gg-aia-eval.html)
- [Getting started with evaluations](https://www.servicenow.com/docs/r/intelligent-experiences/getting-started-aia-eval.html)
- [Execute an evaluation run](https://www.servicenow.com/docs/r/intelligent-experiences/execute-aia-eval.html)
- [Review results](https://www.servicenow.com/docs/r/intelligent-experiences/review-aia-eval-outputs.html)
- [Analyze traces](https://www.servicenow.com/docs/r/intelligent-experiences/aia-eval-analyze-traces.html)
- [Create a custom metric](https://www.servicenow.com/docs/r/intelligent-experiences/create-custom-metric.html)
- [Evaluation FAQs](https://www.servicenow.com/docs/r/intelligent-experiences/aia-eval-faqs.html)

#### AI agent security and data access — SET 2: SECURE

<!-- chunk 1147 (workshop/content/resources/servicenow-docs.en.md#09) -->
These pages cover enforcement inside the agent: what identity it runs as, what records it can reach, and how to stop it.

##### Read these four first, in this order

<!-- chunk 1148 (workshop/content/resources/servicenow-docs.en.md#10) -->
9. [Security for AI agents](https://www.servicenow.com/docs/r/intelligent-experiences/aia-security-implementation.html)
10. [ACLs, role masking, and user identities](https://www.servicenow.com/docs/r/intelligent-experiences/acls-and-rolemasking.html)
11. [Role masking](https://www.servicenow.com/docs/r/intelligent-experiences/aia-role-masking.html)
12. [Deny-by-default ACL configuration](https://www.servicenow.com/docs/r/intelligent-experiences/aia-acl-configuration.html)

##### Controls on a single agent or workflow

<!-- chunk 1149 (workshop/content/resources/servicenow-docs.en.md#11) -->
- [Define security controls for an AI agent](https://www.servicenow.com/docs/r/intelligent-experiences/define-sec-controls-aia.html)
- [Define security controls for an agentic workflow](https://www.servicenow.com/docs/r/intelligent-experiences/define-sec-controls-aw.html)
- [Test user access for an agent](https://www.servicenow.com/docs/r/intelligent-experiences/test-aia-access.html)
- [Test user access for a workflow](https://www.servicenow.com/docs/r/intelligent-experiences/test-aw-access.html)
- [Kill Switch](https://www.servicenow.com/docs/r/intelligent-experiences/aia-kill-switch.html)
- [Configure security controls for a skill](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-skill-kit/nask-access-control.html)

##### Guardrails at runtime

<!-- chunk 1150 (workshop/content/resources/servicenow-docs.en.md#12) -->
- [Enable AI Guardian](https://www.servicenow.com/docs/r/intelligent-experiences/enable-aia-na-guardian.html) Offensiveness detection and prompt injection handling.
- [AI Guardian analytics](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-guardian-analytics.html)

##### Data handling and privacy

<!-- chunk 1151 (workshop/content/resources/servicenow-docs.en.md#13) -->
- [Data sharing and processes](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-data-sharing-and-processes.html)
- [Configure privacy policies](https://www.servicenow.com/docs/r/intelligent-experiences/configure-privacy-policies.html)
- [Opt out of data sharing](https://www.servicenow.com/docs/r/intelligent-experiences/opt-out-of-data-sharing-for-now-assist.html)
- [Configure data overflow processing](https://www.servicenow.com/docs/r/intelligent-experiences/configure-na-data-overflow.html)
- [Assign the data steward role](https://www.servicenow.com/docs/r/intelligent-experiences/assign-data-steward-role.html)
- [User data usage policy](https://www.servicenow.com/docs/r/intelligent-experiences/user-data-usage-policy-now-assist.html)
- [Find and cleanse sensitive data](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-data-kit/sensitive-data.html)

##### Tenancy, credentials, and model routing

<!-- chunk 1152 (workshop/content/resources/servicenow-docs.en.md#14) -->
- [Domain separation in AI Agent Studio](https://www.servicenow.com/docs/r/intelligent-experiences/aia-studio-domain-separation.html)
- [Domain Separation AI agent](https://www.servicenow.com/docs/r/intelligent-experiences/domain-sep-aia.html)
- [Agent2Agent API key credential behavior](https://www.servicenow.com/docs/r/intelligent-experiences/a2a-api-key-credential-behavior.html)
- [Add an MCP server with OAuth 2.1](https://www.servicenow.com/docs/r/intelligent-experiences/add-an-oauth-2-1-mcp-server.html)
- [Add an MCP server with an API key](https://www.servicenow.com/docs/r/intelligent-experiences/add-an-api-key-mcp-server.html)
- [Add an MCP server with a connection and credential alias](https://www.servicenow.com/docs/r/intelligent-experiences/add-an-mcp-server-with-connection-and-credential-alias.html)
- [Bring your own key for third-party providers](https://www.servicenow.com/docs/r/intelligent-experiences/generative-ai-controller/byok-for-azure-open-ai.html)
- [Providers and models](https://www.servicenow.com/docs/r/intelligent-experiences/servicenow-large-language-model-now-llm/providers-and-models.html)
- [Configure rate limiting for providers](https://www.servicenow.com/docs/r/intelligent-experiences/generative-ai-controller/configure-rate-limit.html)
- [AI Agent Studio reference and roles](https://www.servicenow.com/docs/r/intelligent-experiences/na-aia-reference.html)

#### AI Control Tower — SET 3: GOVERN

<!-- chunk 1153 (workshop/content/resources/servicenow-docs.en.md#15) -->
AI Control Tower governs the portfolio: inventory, lifecycle, risk posture, and value. It is a different layer from set two. Registering an agent here does not by itself constrain what that agent can do at runtime.

- [AI Control Tower landing page](https://www.servicenow.com/docs/r/intelligent-experiences/aict-landing.html)

##### The nine documentation areas

<!-- chunk 1154 (workshop/content/resources/servicenow-docs.en.md#16) -->
| Area | What it covers |
|----|----|
| [Explore](https://www.servicenow.com/docs/r/intelligent-experiences/aict-exploring.html) | Architecture, the four user personas, and the six-step governance workflow |
| [Configure](https://www.servicenow.com/docs/9QmX7E6cup0s9Arnkz7nPw) | Activation, plugin install, data sharing, and multi-instance setup |
| [Plan your AI strategy](https://www.servicenow.com/docs/4UxeLGpFILnqLRSN9mND6Q) | Priorities, measurable goals, planning items, and cost tracking |
| [Discover AI assets](https://www.servicenow.com/docs/fVDm0ZLA1K2AY2ZXqRJnUQ) | Platform discovery sync, hyperscaler connections, and MCP server registration |
| [Govern AI assets](https://www.servicenow.com/docs/dNYasv4ocQkSGj8ON8jAfw) | Risk and compliance frameworks, agent identities, and access reviews |
| [Monitor AI assets](https://www.servicenow.com/docs/B79f~IXhd~6q60eNVm0jWg) | Automated quality and safety scoring, configurable metrics, trend analysis |
| [Measure AI impact](https://www.servicenow.com/docs/uC7DGiWaaUPDJjEFJZYswg) | Productivity, cost savings, and adoption tied to individual assets |
| [Address action items](https://www.servicenow.com/docs/ulk3pRxjLzadAekH_DqFvw) | Governance work and generated recommendations in Activity Center |
| [Reference](https://www.servicenow.com/docs/dkmOzWEJNFKFEbS45ids0A) | Roles, tables, data model attributes, and form fields |

##### Working pages inside the product

<!-- chunk 1155 (workshop/content/resources/servicenow-docs.en.md#17) -->
- [Home](https://www.servicenow.com/docs/a4K12GTWpY3LUSIe4G5wKg) Portfolio at a glance, with priority actions.
- [Activity Center](https://www.servicenow.com/docs/jYWhx1KSM0nillT3chhMNA) Assigned items, team workload, unassigned queue.
- [Recommendations and AI insights](https://www.servicenow.com/docs/jjhl9faro9QaQ_T6byizhQ)
- [Working with AI asset records](https://www.servicenow.com/docs/IMP4iJYdv_OXD3xVLe~CTw)

##### Related pages in AI Admin Center

<!-- chunk 1156 (workshop/content/resources/servicenow-docs.en.md#18) -->
- [Using the asset inventory](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-center-using-asset-inventory.html)
- [View your AI assets](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-center-view-ai-assets.html)
- [Create an AI asset](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-center-create-asset.html)
- [Use AI Guardian features](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-center-use-guardian-features.html)

##### For more information

<!-- chunk 1157 (workshop/content/resources/servicenow-docs.en.md#19) -->
[www.servicenow.com](https://www.servicenow.com)

When you are ready to tear down, go to [Cleanup](/cleanup).

### 1.5 Other ServiceNow-related guide text

#### Module 11 "ServiceNow AI Control Tower" (`servicenow-integration/index.en.md`, chunks 1158–1167)

- **Outcome** (Q[1158]): "…run a CloudTrail check that proves ServiceNow AI Control Tower (AICT) acted in your account, explain what AICT discovers about your governed assets and what it cannot see, and describe how a connector identity reaches your account without you handling a key."
  - The module takes about 20 minutes.
  - "You do not need a ServiceNow instance for the participant steps; the facilitator connects the instance if one is available."
- **Info box** (Q[1158]): "Two ServiceNow docs anchor this module; open them alongside it:"
  - [AI Control Tower (AICT)](https://www.servicenow.com/docs/r/intelligent-experiences/aict-landing.html)
  - [AI Agent Studio (AIAS)](https://www.servicenow.com/docs/r/intelligent-experiences/aias-landing.html)
  - "[ServiceNow documentation set for this hackathon](/resources/servicenow-docs): ServiceNow's own guide to the public docs, organized as build an agent, secure it, govern the portfolio"

  It says "two" but lists three; the third is the page in §1.4.
- **Three vendor PDFs** (Q[1159]). The kit copies are in `workshop-static/servicenow/` (VER):

  | Guide | Pages | What it walks through | Kit file |
  |---|---|---|---|
  | Creating and Verifying Amazon Connection Setup | 12 | Connecting AICT to an AWS account and confirming the connection | `creating-and-verifying-amazon-connection-setup.pdf` (3.6 MB) |
  | AI Control Tower console: discovered assets and AI agents | 30 | The AICT console: discovered assets, lifecycle, reviews | `navigate-ai-control-tower-and-manage-ai-agents.pdf` (4.9 MB) |
  | Create and Manage AI Agents in ServiceNow AI Agent Studio | 86 | Building and managing agents in AI Agent Studio | `create-and-manage-ai-agents-in-ai-agent-studio.pdf` (12.2 MB) |

  I did not read the PDFs.
- **Warning** (Q[1159]): "The MoDaaS side runs on your event account. The calls into a live ServiceNow instance have been run once, on a real AWS-ServiceNow connection; AICT claims below come from that test, redacted. If your event has no ServiceNow instance, steps 4 and 5 are described, not exercised."
- **Steps** (Q[1160]–Q[1167]):
  1. **Read the stack outputs.** Find the stack whose name ends with `servicenow-aict`. Expected outputs: `AictConfigured true`, `ServiceNowAictRoleName`, `ServiceNowAictSecretArn` and `ServiceNowAictAccountId`. If the stack is absent you get `AictConfigured false`, which is "the default".
  2. **Fetch the connector secret and verify its role.** Running `aws secretsmanager get-secret-value` prints JSON with `AccessKeyId` and `SecretAccessKey`.
     - "The key belongs to the connector IAM user, not to you."
     - "The key goes from this secret into the AICT connector form only. It is never written to a file, never committed, and never shared."
     - Facilitator step: `aws iam get-role --role-name SgcAictReadOnlyAccessRole`. The trust policy should name "exactly one principal: the connector IAM user", and the role grants "read-only access to AgentCore, Bedrock and CloudWatch Logs".
     - **This step prints a live key, so do not run it casually** (per the working agreement).
  3. **AICT connector form (vendor PDF).** Facilitator only. The "ServiceNow AI Service Graph Connector for Amazon" form takes:
     - Access key ID and Secret access key
     - AWS regions: `us-east-1`
     - Target account IDs: the event account
     - STS assume role: `SgcAictReadOnlyAccessRole` ("role name only; the form prepends the ARN prefix")
     - The CloudWatch log group for invocation counting is covered in the PDF.
  4. **Discovery and the CloudTrail check.** "AICT discovers your AgentCore runtimes, Bedrock agents and SageMaker models. It does not discover":
     - "Agents running as Kubernetes pods (no connector, no API for EKS)"
     - "MCP servers (registered manually or from the MCP Catalog, not discovered)"
     - "MoDaaS guardrails (the connector role lacks `bedrock:ListGuardrails`)"
     - "Which ModelConfig served a call (all calls arrive under the gateway's single IAM principal)"

     The proof is a `cloudtrail lookup-events` query for `AssumeRole` filtered to role ARNs containing `SgcAict`. Expect lines showing "the connector user assuming `SgcAictReadOnlyAccessRole`"; if none appear, allow about 2 minutes.
  5. **The human-loop rail.** Verbatim in §2.0.
  - **Checkpoint:** `aws iam get-role --role-name SgcAictReadOnlyAccessRole` prints either "role exists" or "no role (stack not deployed)". "Both are correct states."

#### Cross-references elsewhere in the guide

- Q[860] (Module 9): "If your team also builds on the ServiceNow side, start from ServiceNow's [Writing effectively for agentic AI](https://www.servicenow.com/docs/r/intelligent-experiences/gg-creating-aia.html), which they call the single most useful page for a hackathon team; the full [ServiceNow documentation set](/resources/servicenow-docs) is under Resources."
- Q[1137] (Resources index, end of the cockpit section): "For ServiceNow's own guide to its AI agent, security and AI Control Tower documentation, see the [ServiceNow documentation set](/resources/servicenow-docs)."
- Q[1116] (Glossary): "ServiceNow's guide to its own documentation is on the next page, [ServiceNow documentation set](/resources/servicenow-docs)."
- Q[802] (AWS Agent Registry): "It is the Canvas component inventory for AI assets and what an external governance system ([Module 11](/servicenow-integration)) discovers."
  - INF: this conflicts with Module 11's discovery list, which never mentions the Agent Registry. The connector role in `03-servicenow-aict.yaml` also has no Agent Registry permissions (VER: its Allow list is in §1.6).
- Q[804] (CloudTrail): CloudTrail "shows that the ServiceNow connector really read your account ([Module 11](/servicenow-integration))."
- Q[902] (Evidence cookbook checkpoint): "Next: [Module 11: ServiceNow AI Control Tower](/servicenow-integration)."
- Q[933] (Cleanup): the event reclaims "the ServiceNow connector stack (if deployed)" automatically.
- Q[995] (landing page): "The judgment they lack: knowing when to gather evidence or escalate instead of acting". Q[1095]/Q[1096] (Module 7 self-check): "S3-restricted-change trap expects escalate", with a sample "PASS (10/10)". MEM says that score can't come from the shipped code.
- **Dangling reference** (VER): Q[1166] says "[Module 7](/reference-agents) section 6 shows the `escalate` disposition". None of the indexed Module 7 pages has a section 6:
  - setup: §1–5
  - run-and-read: §1–4 plus 3a
  - kill-switch: Pause and Unpause
  - swap-model: §1–4
  - self-check: no numbered sections
- **Platform source** (VER): `authz-gateway/tracectx.py` in the platform source zip says the gateway accepts a caller-supplied business correlation id via the W3C baggage key `modaas-correlation-id`, described as "the customer's own key (`fault-4471`, a ServiceNow number, a trouble-ticket id)".
  - It cites `integrations/servicenow/contract/ServiceNow-Integration-API.md §3`, which is **not shipped**. VER: none of the 398 files in `modaas-aigateway-src.zip` and nothing in `modaas-ui-src.zip` has a path matching servicenow, aict or integration.
- **Cockpit** (VER, `modaas-ui-src.zip` `server.py` ≈L7300–7330): the cockpit scans the **last 50** CloudTrail management events. Any event whose Username contains `SgcAict` becomes a resource row `cloudtrail:servicenow-connector` showing "last read at <ts>".
  - INF: this is Rail 2's evidence in the cockpit. In a busy account it can scroll past the 50-event window.

### 1.6 Discrepancies: Module 11 text vs kit template vs live account

1. **Identity model.** MEM (notes #30, `workshop-aws-access`) already records this; the details below are new.
   - **Module 11 text** (Q[1160]–Q[1163]) describes:
     - a connector **IAM user in the event account**
     - an access key stored in **Secrets Manager**
     - stack outputs `ServiceNowAictRoleName`, `ServiceNowAictSecretArn` and `ServiceNowAictAccountId`
   - **The kit template** `workshop-static/servicenow/03-servicenow-aict.yaml` (VER) is the opposite:
     - Its description: "No IAM user and no access key is created here or anywhere in this workshop."
     - The role trusts `arn:aws:iam::${ServiceNowUserAccountId}:user/${ServiceNowUserName}`, which is ServiceNow's own user in ServiceNow's own AWS account.
     - Its outputs are `AictConfigured`, `StsAssumeRoleArn`, `TargetAccountId` and `InvocationLogGroupName`, with no secret.
     - A sensor fails the build if any template declares `AWS::IAM::User` or `AWS::IAM::AccessKey`.
   - **The live account** (MEM) has stacks `a-03-servicenow-aict` and `aict-servicenow-user`, IAM user `ServiceNowAictUser`, and a `CreateAccessKey` call made by `WSOpsRole`. The live setup matches the *guide text*, not this template.
2. **Discovery scope.** The template's "deviation 6" (2026-09-29, "AICT at scale") replaced the vendor's broad policy with exactly what CloudTrail showed the live connector using (VER). It removed "classic Bedrock Agents List/Get, SageMaker List/Describe".
   - The current Allow list covers:
     - `sts:GetCallerIdentity`, `ec2:DescribeRegions`
     - `bedrock:ListInferenceProfiles` and `GetInferenceProfile`
     - `logs:StartQuery` and `GetQueryResults`
     - `cloudtrail:LookupEvents`
     - `bedrock-agentcore:` `ListGateways`, `ListGatewayTargets`, `ListAgentRuntimes`, `GetGateway`, `GetGatewayTarget` and `GetAgentRuntime`
   - There is an explicit **Deny** on `GetWorkloadAccessToken*`, `GetResourceApiKey` and `GetResourceOauth2Token`.
   - INF: under this policy AICT can see AgentCore runtimes and gateways (plus inference profiles), but **not** the "Bedrock agents and SageMaker models" Module 11 lists.
   - Open: whether the live a-03 stack carries deviation 6. I did not check, because that needs IAM reads.
3. **Invocation counting.** The template also creates the vendor's CloudTrail trail `sgc-aict-bedrock-trail` with log group `/aws/bedrock/aict-invocations`. Deviation 5 adds a data-event selector for `AWS::BedrockAgentCore::Runtime` "so invocations of the workshop's AgentCore-hosted agents are recorded" (VER). MEM confirms the trail and log group exist live.
4. **The template names "Rail 2" itself** (VER): it mentions a facilitator who might "assume this role directly to demo Rail 2". In the kit's vocabulary, Rail 2 means AICT discovery.

---

## 2. Task 2: escalate-to-incident.py, the rails diagram, it-incidents.json

### 2.0 What the guide says about Rail 1 (verbatim)

Q[1166], "5. The human-loop rail": "When an agent chooses `escalate` (scenario S3 in [Module 7](/reference-agents)), the refusal should open a ticket a human already works, not a log line nobody reads. Rail 1 in the ServiceNow integration creates an incident from the evidence chain. [Module 7](/reference-agents) section 6 shows the `escalate` disposition. Wiring it into your own agent's escalation path is a stretch goal for your entry; `escalate-to-incident.py` in the workshop assets is the starting point."

### 2.1 What the script does (VER: `workshop-static/servicenow/escalate-to-incident.py`, 169 lines)

- It is byte-identical to `workshop-assets/servicenow/escalate-to-incident.py` (VER).
- It uses Python 3 **stdlib only** (`argparse`, `base64`, `json`, `os`, `re`, `sys`, `urllib.request`) under an MIT-0 licence, so there is nothing to `pip install`.
- Docstring: it turns "a MoDaaS evidence chain into a ServiceNow incident… so the operator who picks it up sees exactly what the agents saw, decided, and refused to do". It "Works with any ServiceNow instance, including a free Personal Developer Instance (developer.servicenow.com)".
- **Flow:**
  1. `fetch_chain`: `GET {audit_store}/records?cid={cid}` with a 10 s timeout. It parses JSONL (one record per line), skips blank and malformed lines, and exits if there are zero records.
  2. `incident_payload`: builds the incident fields (§2.4).
  3. `create_incident`: `POST https://{SNOW_INSTANCE}/api/now/table/incident` with JSON and `Authorization: Basic base64(user:pass)`, 15 s timeout. It returns `response["result"]`.
  4. It prints `incident created: <number>`, the `sys_id`, and `https://{instance}/nav_to.do?uri=incident.do?sys_id=<sys_id>`.

### 2.2 Inputs

| Input | Where | Notes |
|---|---|---|
| `--cid` | CLI, required | Correlation id. `run-reference.sh` mints `fault-<epoch>-<6hex>` (VER, L54–55). The docstring example `fault-1788864931` lacks the hex suffix. |
| `--audit-store` | CLI, or env `AUDIT_STORE` | Default `http://audit-store.components:8080`, a ClusterIP Service in `components` that resolves **in-cluster only** (VER, `reference-impl/audit-store.yaml`). The docstring's laptop path is `kubectl -n components port-forward svc/audit-store 8080:8080` and then `--audit-store http://localhost:8080`. An AgentCore-hosted agent would use the VPC-internal LB `audit-store-agentcore` (VER, `audit-store-agentcore.yaml`). |
| `SNOW_INSTANCE` | env | **Bare hostname** (`devXXXXXX.service-now.com`). The script prepends `https://`, so setting it to `https://…` breaks the URL (VER by code). |
| `SNOW_USER`, `SNOW_PASS` | env | Basic auth, plaintext in the environment. There is no OAuth or token option (VER). On a PDI, `admin` works (docstring). |
| `--dry-run` | CLI flag | "print the incident this chain would file; call nothing". |

- **Credentials it does *not* need** (VER):
  - No AWS credentials.
  - No gateway key.
  - No audit write token. Ledger reads are open by design: `audit-store.py` says "Reads stay open -- the forgery risk is on append". MEM's `platform-verified-facts` agrees.

### 2.3 What it reads from the evidence chain (ledger/CID)

- **Ledger record fields:**
  - `agent.py` `post_audit()` writes `correlation_id`, `step`, `phase`, `actor`, `detail`, and optionally `trace_id` and `action_id` (VER). MEM says `action_id` is never actually passed.
  - The store adds `ts` (`%Y-%m-%dT%H:%M:%SZ`, second resolution) and `seq` (epoch ms) (VER, `audit-store.py`).
- **What the script uses:**
  - `ts`, `step`, `actor` (falling back to `agent`), `phase` and `detail`, the last truncated to 400 chars per record in the work notes.
  - Records are sorted by `(str(ts), step)`. A comment explains that `step` order disagrees with time where agents overlap.
  - `trace_id` and `seq` are **unused**, so the incident joins back to the ledger **only by CID**. INF: given that the ledger's trace_ids are split per agent (MEM), that is the safer key anyway.
- **Dispositions:**
  - The reference agents don't write a `disposition` field. They write `disposition=<x>` inside the `result-inspection` `detail` string, for example `disposition=escalate, decision='…'`, or `disposition=refused, no model output` on a refusal (VER, `agent.py`).
  - `dispositions_of()` collects any `disposition` field **and** matches the regex `disposition=([\w-]+)` in `detail`. The docstring calls this a fix found on 2026-09-26: before it, "the incident then claimed every run had escalated".
  - `classify_disposition()` returns only `escalate`, `gather-evidence`, `auto-resolve` or `undetermined`. `refused` is assigned separately, in the `except` branch after a gateway error (VER, `agent.py`). These five are the values the ledger can carry.
- **Expected volume:** MEM says a successful 3-agent run writes 12 records (4 per agent) and a refusal writes 3 per agent. The work notes would then be about 12 × (≈60-char header + ≤404-char detail), roughly ≤ 5.6K characters.

### 2.4 What it creates in ServiceNow (table `incident`, Table API)

| Field | Value set by the script |
|---|---|
| `short_description` | `[MoDaaS] Agents escalated <cid> — human decision required` (**always**, whatever the disposition) |
| `description` | `Autonomous agents (<sorted actors>) evaluated fault <cid>. Dispositions recorded: <sorted set or 'none recorded'>. Full evidence chain in work notes.` |
| `work_notes` | Header `MoDaaS evidence chain for correlation id <cid>` / `(<n> records, chronological)`, then one line per record, `[ts] step <n> <actor> <PHASE>[ disposition=<field>]`, with an indented `detail[:400]` |
| `urgency` | `"2"` |
| `impact` | `"2"` |
| `category` | `"network"` |
| `correlation_id` | `<cid>` (the comment says "ties the incident back to the ledger, both directions") |
| `correlation_display` | `"modaas-evidence-chain"` |

- It does not set `caller_id`, `assignment_group`, `assigned_to`, `state` or `cmdb_ci` (VER).
- INF about ServiceNow defaults, to verify on a real instance:
  - urgency 2 with impact 2 normally yields priority 3, Moderate.
  - `network` is a stock incident category.
  - `correlation_id` and `correlation_display` are standard task fields used for integrations.
  - Writing `work_notes` needs a role with journal write (typically `itil`; `admin` on a PDI).

### 2.5 Can it run without a ServiceNow instance?

- **Yes, with `--dry-run`** (VER). It fetches the chain and prints `evidence chain: N records for <cid>` plus the full incident JSON. It returns *before* reading `SNOW_*`, so there are no ServiceNow calls and no credentials.
- It **still needs the audit store** (in-cluster DNS or a port-forward).
- There is no option to read a saved chain file. INF: a few-line patch could add one, so it would also work fully offline.
- Untested suggestion that I did not run (read-only in effect, but it opens a port-forward, so per the working agreement it needs the user's OK first). The CID is a placeholder, not a real run:

  ```bash
  kubectl -n components port-forward svc/audit-store 8080:8080 &
  python3 workshop-static/servicenow/escalate-to-incident.py --dry-run --cid <S3 run CID> --audit-store http://localhost:8080
  ```

### 2.6 Failure modes and gaps (VER unless marked)

1. **No escalate gating.** Any CID produces an "Agents escalated … human decision required" incident. Running it on an S1 auto-resolve run files a false escalation. The 2026-09-26 fix only corrected the *description* text.
2. **Not idempotent.** It never queries for an existing incident with the same `correlation_id` before the POST, so a rerun creates duplicates.
3. **Errors are uncaught.** `URLError`, `HTTPError` (401 bad credentials, 403 ACL, 400 …) and socket timeouts all surface as Python tracebacks. There are no retries.
4. **Empty chain** (wrong CID, or the store's PVC was recreated): `sys.exit("no evidence records for cid=… at …")`.
5. **Malformed JSONL lines are silently dropped**, so the "(N records)" header can under-report without warning.
6. **`SNOW_INSTANCE` with a scheme** produces `https://https://…`.
7. **A non-JSON response** makes `json.load` raise. INF: for example the HTML wake-up page of a hibernating PDI.
8. **Nothing is written back.** The incident number is printed but not recorded in the ledger or anywhere else, so the "both directions" join depends on ServiceNow's `correlation_id` field alone.
9. INF, low risk: the `tool-invocation` record's `detail` contains `result_summary=<answer[:200]>`. If a model answer contained the text `disposition=…`, the regex would pick it up as a disposition.
10. INF: journal-field length limits on `work_notes` (≤ ~5.6K chars here) are unverified.

### 2.7 The rails diagram: `workshop-static/images/servicenow-two-rails.svg` (all text labels, VER)

- **Title:** "ServiceNow: three rails, different jobs". The filename says *two*. INF: Rail 3 was added after the file was named.
- **Left box, "THIS PLATFORM":**
  - "enforcement: admit · authz" / "guardrail · revoke-to-404"
  - "evidence ledger (audit-store)"
  - "registry (TMF639 metadata)"
  - "governed gateway" / "/mcp/{alias} · /v1/chat/completions"
- **RAIL 1 · ITSM — HUMANS:** "incident carries the evidence chain" / "correlation_id ties queue ↔ ledger".
  - The arrow runs **from the evidence-ledger box** (path `M 272 190 → 600 104`; the ledger box is centred at y=190) and is labelled **"disposition = escalate"**.
- **RAIL 2 · AI CONTROL TOWER — RECORD:** "inventory · lifecycle · risk · value" / '"does not by itself constrain runtime" — their docs' / "in via MCP / A2A registration · sync fail-soft".
  - A **dashed** arrow runs **from the registry (TMF639 metadata) box** (`M 272 242 → 600 222`), labelled **"register governed assets"**.
- **RAIL 3 · SERVICENOW AGENTS — CALLERS:** "AI Agent Studio adds the governed MCP server" / "OAuth 2.0 / API key · admitted, authorized, audited".
  - The arrow points **into the governed-gateway box** (`M 600 332 → 272 302`), labelled **"tool call through the gateway"**.
- **Footer:** "AICT tells you what your agents are. This platform decides what they may do — and proves what they did."
- **Interpretation:**
  - **Rail 1 = outbound to humans.** When a run's disposition is `escalate`, the evidence chain for that CID becomes an ITSM incident whose `correlation_id` is the CID, so the queue item and the ledger join both ways. The implementation is `escalate-to-incident.py` (VER, §2.1–2.4).
  - **Rail 2 = outbound record into AICT.**
    - The diagram draws it as *registration* ("in via MCP / A2A registration"). Module 11 describes *pull discovery* by the AWS connector through `SgcAictReadOnlyAccessRole`, and says MCP servers are "registered manually or from the MCP Catalog, not discovered" (Q[1164]).
    - "fail-soft" appears nowhere else in the kit content. It is, however, the platform operators' general pattern (VER, platform source): for example `RegistryResolved=False, fail-soft` in `operators/shared/asset_operator.py`, and the fail-soft `backings/tmf639.py`.
    - INF: "sync fail-soft" means a failed registry or TMF639 sync never blocks an asset's admission. In other words, Rail 2 is a record and not a control, which matches "does not by itself constrain runtime" (Q[1153]).
  - **Rail 3 = inbound callers.** A ServiceNow AI Agent Studio agent registers the MoDaaS gateway's `/mcp/{alias}` as an MCP server (OAuth or API key), and its tool calls are then admitted, authorized and audited like any other caller.
    - No Module 11 step exercises it (VER). The matching curated docs are "Add an MCP server in AI Agent Studio" and "Add an MCP server with OAuth 2.1 / with an API key / with a connection and credential alias".
    - INF: per MEM, the gateway ELB is internet-facing, with plain HTTP on :8080 and TLS on :8443, and the team rule is never to send the gateway key over plain HTTP. Rail 3 would therefore need the TLS listener and a deliberate per-caller credential.
- **No indexed guide page references the image** (VER):
  - The corpus keeps image markup: 66 chunks contain image references.
  - Five other kit images are referenced: architecture-hero, modaas-platform-architecture, step-mcp-tool, and the ui-* screenshots.
  - `servicenow-two-rails` appears in 0 chunks. Module 11 names only "Rail 1".

### 2.8 `workshop-static/data/it-incidents.json` (shape only)

```
{ "incidents": [            # 7 records
    { "id": "INC-4401",     # str, "INC-" + 4 digits
      "severity": "P2",     # P1..P4  (P1×1, P2×3, P3×2, P4×1)
      "status": "open",     # open×5, resolved×2
      "summary": str,
      "affected_service": str,   # e.g. 5G-SLICE-EDGE-04, CORE-API, SD-WAN-PREMIUM, 5G-CORE-DNS
      "created": "2026-09-04T09:31:00Z",   # ISO-8601 UTC, 2026-09-02..04
      "runbook": "RB-EDGE-SLICE-DEGRADATION" } ] }
```

- **Consumer** (VER): the `runbook-lookup` Lambda tool, `lambda/runbook-lookup/handler.py` `_search_incidents`. It does a case-insensitive substring match over each JSON-dumped record and returns at most 10. `scripts/bootstrap-platform.sh` bundles the file. MEM: this is the IT agent's MCP tool.
- It is a **mock ITSM queue, not a ServiceNow export.**
  - INF: its id style `INC-4401` and severity `P1–P4` differ from ServiceNow's `INC0010001` numbering and its impact/urgency → priority model.
  - `escalate-to-incident.py` does not use it (VER).
  - `run-reference.sh` gives the IT agent a synthetic incident `INC-<last 4 chars of CID>` (VER, L79), which is not one of these records.
- One record is an escalation case: INC-4420, P1, "SITE-PHX-04 edge degradation, regulated customer impacted", runbook `RB-REGULATED-ESCALATION`.

---

## 3. Task 3: public landing pages (WebFetch)

Both pages rendered through WebFetch. Fetching the raw HTML with curl returns only an 8.4 KB JavaScript shell titled "Docs | ServiceNow" (VER), so the content below is the summarizer's reading of the rendered page (WF).

### 3.1 AI Control Tower: https://www.servicenow.com/docs/r/intelligent-experiences/aict-landing.html (WF)

- **Title and release:** "AI Control Tower", release **Brazil** ("Updated September 10, 2026").
- **Intro:** "Gain visibility into your organization's AI footprint, manage the lifecycle of AI investments, govern risk and compliance, and measure the business impact of AI with AI Control Tower."
- **Sections:** Summary of AI Control Tower · Key Features · Important Considerations · **Get started** · AI limitations · Data processing · Data collection.
- **Get started** has nine areas:
  1. Explore
  2. Configure
  3. Plan your AI strategy
  4. **Discover and manage AI assets** (the curated page says "Discover AI assets")
  5. Govern AI assets
  6. Monitor AI assets
  7. Measure AI impact
  8. Address action items
  9. Reference

  These are the same nine areas as the curated list in Q[1154].
- **Key Features:** AI Strategy Planning · AI Asset Discovery and Management ("Build a centralized inventory") · Governance ("Manage risk, compliance, security, and privacy") · Monitoring ("Evaluate quality and safety through automated scoring") · Impact Measurement · Action Item Management · Reference Resources.
- **Important Considerations** (quotes):
  - "Availability of certain AI models and features may be limited based on your region, data center environment (e.g., FedRAMP, NSC DOD IL5, Australia IRAP), or regulatory status."
  - "AI Control Tower relies on AI and machine learning technologies that may not always produce fully accurate or complete outputs"
  - "Use of this application requires data transfer from your instance to a centralized ServiceNow environment, potentially involving third-party cloud providers."
  - "Customers can opt out of data collection used to improve ServiceNow AI technologies at any time."

### 3.2 AI Agent Studio: https://www.servicenow.com/docs/r/intelligent-experiences/aias-landing.html (WF)

- **Title and release:** "AI Agent Studio", release **Brazil** ("Updated September 10, 2026").
- **Intro:** "AI Agent Studio enables ServiceNow customers to build, configure, and deploy autonomous AI agents that automate complex workflows by learning business processes."
- **Sections:** Summary · Key Features · Important Considerations · AI Limitations and Responsibilities · Data Processing and Privacy · **Get started** · AI limitations · Data processing · Data collection. It also references support KBs KB1584492, KB0743854, KB2593939 and KB0564067.
- **Get started:** Explore · Configure · Orchestrate and govern AI agents · Orchestrate and govern agentic workflows · Integrate external agents · Reference.
- **Key Features:** Agent Configuration · Agent Orchestration and Governance ("…orchestrate workflows with planned instructions and triggers to execute autonomous actions") · Integration ("Connect and manage external AI agents from third-party providers to extend automation capabilities") · Reference Resources ("user roles, tables, and properties related to AI agents and workflows").
- **Important Considerations:** availability is limited by region, compliance environment or self-hosting; "Customers should regularly check ServiceNow Knowledge Base articles for updates on model provider availability and feature accessibility."
- **AI Limitations and Responsibilities:** "…Customers are responsible for thoroughly testing and evaluating AI outputs… Human oversight is essential, and reliance solely on AI-generated outputs for critical decisions is discouraged."

### 3.3 Link checks: inconclusive, and why (VER)

- **HTTP status is meaningless on this site.** A bogus `/docs/r/intelligent-experiences/this-page-does-not-exist-xyz.html` and a bogus short id `/docs/AAAAAAAAAAAAAAAAAAAAAA` both return **200** to curl. All 12 curated short links also return 200, which proves nothing.
- **WebFetch can't decide it either.** It returned **404** both for the curated "Discover AI assets" short link `fVDm0ZLA1K2AY2ZXqRJnUQ` and for the short id that WebFetch itself reported for the live "Discover and manage AI assets" (`aOKN_md6jHiudYMMpH2Gjg`; curl also gave 404 for that id).
- The short ids that WebFetch reported for the live landing page **all differ** from the curated ids. They are summarizer output and one failed a control, so I don't reproduce them as authoritative.
  - INF: short ids may be release-specific (Australia vs Brazil), or the summarizer mangled them.
- The `/r/intelligent-experiences/*.html` page links are the safer bookmarks, because the two landing `.html` pages rendered fine. The curated page also tells readers to use the release selector (Q[1139]).

---

## 4. Implications for ProofLab (INF, short)

1. **Rail 1 is the cheapest ServiceNow touchpoint.**
   - It needs no AICT and works with a free PDI and the stdlib script.
   - `--dry-run` can show today, against our ledger, what an incident would carry for an S3 (escalate) CID.
   - The result is a human-loop artifact: an incident number whose `correlation_id` equals the CID.
   - That fits the slide rule (MEM `prooflab-project`): "a human actually answering an alert" is out of scope, but "the alert, its named recipient and the silence must still be recorded". The script sets **no recipient** (`assignment_group` / `assigned_to`), so "named recipient" would need a field added.
2. **Before using Rail 1 in an assessed run, fix the two VER gaps:**
   - Gate on `escalate`, or retitle the incident for non-escalate runs.
   - Make it idempotent by querying `correlation_id=<cid>` before the POST.

   Also consider writing the incident number back into our own evidence, so the join is genuinely bidirectional.
3. **Rail 2 (AICT) is facilitator-owned**, and in our account it is provisioned (MEM). What AICT can see is narrow:
   - It sees no k8s pods, no MCP servers, no guardrails and no per-ModelConfig attribution (Q[1164]).
   - Under deviation 6 it may see only AgentCore runtimes and gateways.

   Any Level 2–3 claim that relies on AICT should stay within that.
4. **Rail 3 (ServiceNow agents calling our gateway)** is the most work. It needs a TLS endpoint and a credential decision.

---

## 5. Open questions

1. Is a ServiceNow instance (PDI or event sandbox) available to the team, and who holds its credentials? A live Rail 1 run needs one; the docstring suggests a free PDI.
2. Does the live `a-03-servicenow-aict` stack carry deviation 6, and what outputs does `aict-servicenow-user` expose? Note that `ServiceNowAictSecretArn` would point at a live key, so don't print it.
3. ServiceNow side: which role does the Basic-auth user need for a Table API create plus a `work_notes` write? Are there journal length limits? Are `category=network` and `correlation_*` writable on the target instance?
4. Do the curated Australia short links still open the intended pages in the Brazil-default docs? Answering this needs a JavaScript-rendering browser check.
5. Where is the "Module 7 section 6" that Module 11 cites? It isn't in the indexed guide; maybe a hosted page version differs.
6. Is there any shipped MoDaaS → AICT push ("in via MCP / A2A registration" in the SVG)? I found none in the kit or the source zips. The upstream `integrations/servicenow/contract/ServiceNow-Integration-API.md` is cited in `tracectx.py` but not shipped.
7. Does the organiser require AICT for Level 2? This is already open in MEM `prooflab-project`.

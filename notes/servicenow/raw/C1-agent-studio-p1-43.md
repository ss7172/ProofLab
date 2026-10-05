# C1: ServiceNow AI Agent Studio guide, pages 1–43

**Source:** `/Users/satyabratsrikumar/Downloads/create-and-manage-ai-agents-in-ai-agent-studio.pdf`, titled "Create and Manage AI Agents in ServiceNow AI Agent Studio". It has 86 pages and is a react-pdf export created 2026-09-30. It is a click-through demo: a video thumbnail on p.1, then numbered steps 01–42 on pp.2–43, one step per page, each a short caption plus one screenshot. A separate agent covers pp.44–86.

**Labels used throughout**
- **[CAP p.N]**: caption text written by the demo author. This is the PDF's only text layer.
- **[SCR p.N]**: read from the UI screenshot on that page. I checked these at the native 1920×963 resolution, not the scaled-down page render.
- **[INF]**: my inference. The PDF does not say it.

Captions are the demo author's summary, and in places they contradict the screenshots (see §5). Where they disagree, trust [SCR].

---

## 0. Top findings

1. **The demo instance has an AWS AgentCore link.**
   - The banner on p.14 and p.16 reads: "Read-only: This record is in the AI Agents for Telecommunications, Media and Technology application, but **AI Service Graph Connector for Amazon** is the current application." [SCR]
   - The navigator lists two import set tables named "**SG-AWS AgentCore AI Age…**" (truncated). [SCR p.3, p.5]
   - [INF] The instance probably imports AWS (Bedrock) AgentCore AI-agent inventory through a Service Graph connector. That is a likely route for ServiceNow (and AI Control Tower) to see AgentCore agents.
   - Nothing in pp.1–43 shows what the connector imports or how it is set up.
2. **The main governance controls shown are run-as identity and access control.** [SCR p.28–43]
   - **User access** has three options: Users with specific roles, Any authenticated user, or Public. An **ACL is auto-generated** from the choice.
   - **Data access** sets who the agent runs as: either a "**Dynamic user**", which requires "Approved role(s)", or an "**AI user**", a dedicated sys_user type with pre-defined roles.
3. **Tools are Flow actions, each with an "Execution m[ode]" column, set to "Autonomous" in the demo.** [SCR p.25] Pages 1–43 show none of the following: approval or supervision, triggers, channels, testing, activity or run logs, or publishing.
4. **Model settings are visible, but no providers are named.**
   - Each agent has an "**Unsupported model providers**" field: "LLM providers: Select unsupported LLMs". [SCR p.22–24]
   - AI Admin Center has agents and workflows for **model providers, model versions ("Instance and skill lev…"), model provider policy, and AI Guardian (incl. "Prompt Inj…")**. [SCR p.8, p.13]
   - No provider is named anywhere in pp.1–43, and **Bedrock is not mentioned.**
5. **"Allow third party to access this AI agent — Enable for external discovery of this ServiceNow AI agent"** exists as a setting. [SCR p.22–24]
   - It is **Off in every screenshot**, even though the captions say it was enabled.
   - No protocol (A2A, MCP, REST) is named.
6. **"AICT" appears only in names.** [SCR p.11]
   - The app "AICT Demo App V2" contains a Ticket Routing & Priority Agent, which is Inactive.
   - The "AICT Security Analyzer Agent" belongs to the app "AI Security and Privacy" and was created by `maint`.
   - [INF] AICT = AI Control Tower. No AICT screens or behaviour are shown.

---

## 1. Page-by-page summary

**p.1: Title page.**
- [CAP] "This demo introduces how to create and manage AI agents in the ServiceNow environment. It highlights the process of using existing agents or building new ones to enhance business workflows."
- Video thumbnail, © 2026 ServiceNow.

**p.2, Step 01 "Access AI Agent Studio".**
- [CAP] "Go to platformdemoh8.service-now.com". Click All and search for "AI Agent".
- [SCR] Studio header tabs: **Overview · Create and manage · Testing · Activity · Settings**.
- Subtitle (assembled from p.2 and p.5): "Create, manage, and monitor agentic workflows and the AI agents working across your organization."
- Yellow banner: "**Action required: 18 agents have no Access Control List (ACL) configured.** Configure ACLs to ensure secure and uninterrupted operation. View Documentation".
- "Ready-made solutions" panel (tabs: Agentic workflows / AI agents): "AI agents specialize in different tasks and are deployed to work on agentic workflows across your organization. Get started with a ready-made agentic workflow or AI agent. You can activate them as-is or duplicate and tailor them to fit your needs."
- Ready-made cards:
  - Service Exchange Onboarding
  - Service Exchange Registration Monitor
  - Error Analysis and Remediation Workflow ("…investigate/analyse and remediate errors tracked by the ServiceNow Error Framework…")
  - Automation Explorer
  - Generate my work plan
  - **Create standard change request** ("This workflow helps users create and submit Change Requests in ServiceNow. Invoke it whenever the user asks to log, create, submit, initiate, or help with a change record of any type…")
- "My Solutions" panel (AI specialists / Agentic workflows / AI agents) with a "**View analytics**↗" link.
- Welcome panel: "…learn about four key steps to follow from beginning to end" (Take tour / View steps).

**p.3–5, Steps 02–04: search, open Studio, "Access Studio Features".**
- [SCR p.3] The navigator, filtered on "ai agent", shows:
  - AI Agent Studio modules: Overview, Create and manage, Testing, Activity, Settings, **Analytics**.
  - System Import Sets › Import Set Tables › **"SG-AWS AgentCore AI Age…"** (two entries, truncated).
  - AI Case Management (p.5 shows its modules: Inquiry Type, State Models, Smart Assessment Templates, Causes, Consequences; not relevant here).
- [CAP p.5] "Access the main features of AI Agent Studio…". The screenshot only highlights the ready-made solutions panel.

**p.6–9, Steps 05–08: "Create and manage", agentic workflows.**
- [SCR p.7] Page header: "Manage AI specialists, agentic workflows, and AI agents — Create from scratch, duplicate, or manage existing…". Tabs: **AI specialists / Agentic workflows / AI agents**.
- [SCR p.7] The AI specialists list has **0 rows**. Columns: Name, Description, Status, **Published**, Added by, Type, Domain.
- [CAP p.7] Agentic workflows "aggregate multiple AI agents under one business task umbrella."
- [SCR p.8] "Agentic workflows (50)". Columns: Name, Description, AI agents (count), **Team**, **Base plan**, Application, **Model support** (all show "Available"). Buttons: Delete / New.
- Examples from p.8:
  - **AI Admin Center:**
    - Skill Management (3 agents)
    - **Manage Model Provider Workflow** (4; "Conversational workflow for AI administrators to m…")
    - **Guardian Settings NAC** (3; "ROUTE TO THIS WORKFLOW when the user mentions 'gua…'")
    - Help me troubleshoot (1)
    - Multilingual and Policy Settings Manager (4)
    - **Model Version Management Workflow** (3)
  - **AI Agents for Service Exchange Provider:** Service Exchange Onboarding, Registration Monitor.
  - **AI Agents for Telecommunications, Media and Techno…:**
    - **Analyze network incidents** (5 agents; "Assist customer agents in resolving a given incident."; base plan "This team handles incident requests involving reso…")
    - Service Test and Repair
    - Test and repair telecom service issues
    - Preliminary troubleshooter
    - Customer voice quality issue resolution
- Base plans read like prompts: "# Role You are the … Workflow orch…", "# Objectives Help administrators…", "Strictly follow…".
- [CAP p.9] "Explore detailed information about the selected agentic workflow…". [SCR p.9] Only the list toolbar is highlighted. **No workflow detail page is opened.**

**p.10–13, Steps 09–12: AI agents list.**
- [SCR p.11] "**AI agents (165)**", filter "4 conditions".
- Columns: Name, Description, **AI agent type** (all "Chat"), **Tools** (count), **Created by**, **Updated**, a column of "Available" badges (header hidden behind the callout; [INF] the same "Model support" as on p.8), Application, **Status** (Active/Inactive). Buttons: Delete / **Add ▾** / ….
- Created-by values include `admin`, `system`, `maint` and individual user IDs.
- Notable rows on p.11:
  - **Ticket Routing & Priority Agent** ("Automatically classifies, routes, and prioritizes…", 3 tools, app **AICT Demo App V2**, **Inactive**)
  - **AICT Security Analyzer Agent** ("Responsible for generating the security event cont…", 2 tools, created by `maint`, app **AI Security and Privacy**, Active)
  - **Approval Assistance Agent** ("Handles all queries related to approval records…", app "ServiceNow Otto Agents for requestor", Inactive)
  - Change quality assessor agents (app "IT Service Management AI agent collection")
- Application names also include "ServiceNow Otto for Virtual Agent / for Automation Center / for Setup Core" and "ServiceNow Otto in Document Management". [SCR p.11–12] What "Otto" is, the PDF doesn't explain.
- [SCR p.13] AI Admin Center agents:
  - **Edit Model Provider Agent** ("MANAGE model providers — handles both editing AND …")
  - **Model Provider Policy Agent** ("AI Agent for viewing AI model provider policy summ…")
  - **Model Version Modifier Agent** ("Creates, updates or removes Instance and skill lev…")
  - Skill Discovery / Skill Configuration Agents
  - **Model Provider Query and History Agent** ("VIEW and QUERY model provider information and hist…")
  - **Guardian Settings Viewer Agent NAC** ("Retrieves and displays AI Guardian settings…")
  - **Guardian Settings Modifier Agent NAC** ("Modifies AI Guardian settings including Prompt Inj…")
  - SHA Triage / SHA Diagnostic Agents
  - **Data and Policy Configuration Agent** ("Manages Data and Policy configuration for AI…")
  - Language Configuration Agent
- The demo opens "Task information collector AI Agent V2" (Telecom app, 2 tools, Active). "Showing 1-20 of 165".

**p.14–16, Steps 13–15: open agent, then Duplicate.**
- [SCR p.14] Scope banner, quoted in full in §0 finding 1, with an "**Edit in original scope**" button. The agent header carries a "Chat" badge.
- The guided-setup left nav has: **Define the specialty · Add tools and information · Define security controls (Define user access, Define data access) · Add triggers · Select channels and status**.
- "Define the specialty — Using clear, precise language, write the name, description, role, and list of steps this AI agent completes. The LLM analyzes the specific wording you use to understand the specialty of this AI agent."
- Fields:
  - AI agent name
  - AI agent description (tag "**Description for LLM**")
  - "Define the role and required steps", with a **View versions** button
  - AI agent role (tag "**Instruction for LLM**")
- The demo agent's description ends: "It does not require any user confirmation to use the tools."
- [SCR p.15] The ⋮ menu has **Duplicate** and **Delete** (Delete is greyed out on this read-only record).
- [SCR p.16] Duplicate dialog, partly covered by the callout: "…[t]riggers will be inactive. Fine-tune the copied AI agent with distinct instructions, tools [an]d triggers by following the AI agent configuration guided setup."

**p.17–21, Steps 16–20: rename the copy.**
- [SCR p.17] The copy "…V2 (Copy)" is editable. It gains:
  - a "**Generate details**" (AI-assist) button
  - a "**View versions ▾**" split button
  - "Save and continue"
- **Add triggers** and **Select channels and status** are greyed out in the left nav.
- [SCR p.20] The copy is renamed "**Test AI Agent for the DTW Hackathon**". [INF] So this guide was likely made for this hackathon, and platformdemoh8 may be the hackathon sandbox.
- [CAP p.21] "Access additional settings…": the page scrolls down the specialty page.

**p.22–24, Steps 21–23: further settings on the "Define the specialty" page.** [SCR]
- **Unsupported model providers**: "List any model providers th[…]" (the rest is covered) / field "**LLM providers: Select unsupported LLMs**".
- **Allow third party to access this AI agent** [OFF]: "**Enable for external discovery of this ServiceNow AI agent**". Toggle Off.
- **Allow AI specialists to access this AI agent** [OFF]: "Enable this AI agent for use in AI specialists. AI agent inputs will be available in the AI specialist task definition once enabled."
- **Manage long-term memory**: "Specify categories for memories about user details — Categories are generated by an LLM using an AI agent's details to store and retrieve user information. If the setting for long-term memory is on, you can select categories or use AI to identify them." Includes an "Identify Categories" button and a "View settings" link.
- **Allow this AI agent to learn from past executions** [NO] (p.24).
- Caption vs screenshot: [CAP p.22/23] say third-party access was enabled and confirmed. The toggle shows **Off** on p.22, p.23 (only the label text is highlighted) and p.24 at "Save and continue".

**p.25–27, Steps 24–26: tools.**
- [SCR p.25] "Add tools and information — Tools provide the essential functionality and data an AI agent needs to carry out its role. An AI agent selects a tool based on the tool's name and description, which need to be clearly written."
- "**Add tool ▾**". The dropdown is never opened.
- Section "**Flow actions**" (tag "Description for LLM"): "An AI agent uses a flow action to execute platform features without having to write new code."
- Table columns: Name · **Execution m…** · **Display out…** · Description · Date add… · Rem…
- Rows (both inherited from the duplicated agent):
  - "Fetch current task information" | **Autonomous** | false | "…fetches the information of the task given like short description, description, caller and state and sold product. It uses task number as input to call the flow action" | 2026-09-30
  - "Verify standard task information" | **Autonomous** | false | "Verifies the given task using the task number. Use "Primary Task Number" as task_number." | 2026-09-30
- "Suggested tools to add — Once you feel good about your AI Agent description and instructions AI can recommend Tools to add", with a "**Recommend Tools**" button.
- FAQ entry: "Do AI agents come with their own bui[lt-in tools]…".
- [CAP p.26] says "choose from available AI skills and integrations". [SCR p.26] shows no picker. **No tool is added in pp.1–43.**

**p.28–32, Steps 27–31: Define user access.**
- [SCR p.29] "Define which users can access and interact with this AI agent. **Once you save your choices, an access control list (ACL) will be automatically generated.**"
- Panel "Define who can access this AI agent (ACLs)". "User access*" defaults to "Users with specific roles", with a required "Role(s)" field.
- [SCR p.31] Options:
  - "**Any authenticated user** — As long as a user is logged in, they can access this AI agent"
  - "**Users with specific roles** — Users that are assigned specific roles can access this AI agent"
  - "**Public** — Anyone can access this AI agent, even without logging in."
- [SCR p.32] Saved as **Any authenticated user**.
- FAQ entries: "How do all the ACLs relate to one ano[ther]…", "How can I update my saved choices?"

**p.33–43, Steps 32–42: Define data access (run-as identity).**
- [SCR p.35] "Choose the user identity this AI agent should run as to determine the roles and the data access permissions derived from them. **Remember, when AI agents can access data, they can also share that data with the human user who interacts with them.**"
- [SCR p.34] "User identity type*" options:
  - "**Dynamic user** — This can be the sys_user of a trigger, agentic workflow, or user that passes its roles to this AI agent."
  - "**AI user** — This is a type of sys_user only for agentic workflows and AI agents, with pre-defined roles."
- Dynamic user requires "**Approved role(s)***" (p.35–37, 41–43). The dropdown lists roles with descriptions, e.g.:
  - access_analyzer_admin
  - **access_analyzer_ai_user** ("This role enables users to review and analyze access permissions within the **Agent Studio testing module**")
  - access_control_read_admin
  - action_category_creator
  - action_designer
  - (p.37, p.42)
- AI user requires an "**AI user***" and shows "**Selected AI user roles**" (empty, p.39).
- FAQ entries: "What are approved roles and what do…", "Can I ask it not to share data with a h[uman]…".
- **State at p.43:** Dynamic user, with Approved role(s) still empty. [CAP p.43] says "View the permissions associated with the System Administrator role…", but the screenshot shows an empty field.

---

## 2. Requested topics, as covered by pp.1–43

**What AI Agent Studio is**
- [SCR p.2/5] "Create, manage, and monitor agentic workflows and the AI agents working across your organization."
- It manages three object types [SCR p.7]: **AI specialists, agentic workflows, AI agents**.
- An agentic workflow is a team of agents plus a "Base plan" (LLM instructions). [SCR p.8]
- An agent consists of: name + description ("Description for LLM") + role/steps ("Instruction for LLM") + tools + security controls + triggers + channels/status. [SCR p.14]
- Ready-made items can be activated as-is or duplicated and tailored. [SCR p.2]
- Shipped agents are read-only outside their app scope ("Edit in original scope"). [SCR p.14] So the demo duplicates first, then customizes. [CAP p.14–16]

**Prerequisites, plugins, roles**
- **Not covered.** The only access instructions are the instance URL [CAP p.2] and All → "AI Agent" → AI Agent Studio [CAP p.2–4].
- No plugin list and no builder or admin role requirements.
- The app scopes seen are context, not prerequisites [SCR p.8, 11–14]:
  - AI Admin Center
  - AI Agents for Telecommunications, Media and Technology
  - AI Agents for Service Exchange Provider
  - IT Service Management AI agent collection
  - AI Security and Privacy
  - AICT Demo App V2
  - the "ServiceNow Otto …" apps
  - AI Service Graph Connector for Amazon (the current scope)

**LLM and model configuration**
- What the screenshots show:
  - "Description for LLM" / "Instruction for LLM" tags. [SCR p.14]
  - The per-agent **Unsupported model providers / "Select unsupported LLMs"** field. [SCR p.22–24]
  - "Model support: Available" on workflows. [SCR p.8]
  - The AI Admin Center model-provider, model-version, provider-policy and query/history agents and workflows. [SCR p.8, p.13]
- [INF] Model choice seems to be set by admins at instance or skill level ("Instance and skill lev…"), not per agent. The per-agent field only excludes providers.
- **Whether AWS Bedrock or any external LLM can be used is open.** No provider names appear in pp.1–43.

**Tools and skills**
- Only **Flow actions** are shown. [SCR p.25]
- The LLM picks a tool by its name and description. [SCR p.25]
- AI can recommend tools ("Recommend Tools"). [SCR p.25]
- Each tool has an Execution m[ode] and a Display out[put] column. [SCR p.25]
- "Skills and integrations" appear only in captions. [CAP p.24, p.26]

**Triggers**
- "Add triggers" is a guided-setup step that is greyed out and never reached. [SCR p.14, 17–43]
- Copied agents' triggers will be inactive. [SCR p.16]
- The Dynamic user can be "the sys_user of a trigger". [SCR p.34]

**Guardrails**
- AI Guardian settings, incl. "Prompt Inj…": names only. [SCR p.8, p.13]
- Model provider policy. [SCR p.13]
- Data and Policy configuration. [SCR p.13]
- ACL-missing banner. [SCR p.2]
- Warning that agents can share accessible data with the human user. [SCR p.35]
- Long-term memory categories and the "learn from past executions" flag (NO). [SCR p.22–24]
- User access and run-as identity. [SCR p.28–43]

**Approvals and human-in-the-loop**
- The only control shown is the tool **Execution m[ode] = "Autonomous"**. [SCR p.25] I am not naming the alternative values; they aren't shown.
- "It does not require any user confirmation to use the tools" is **the demo agent's own description text** (LLM-facing), not a platform setting. [SCR p.14]
- An "Approval Assistance Agent" exists for *querying* approval records. [SCR p.11]
- **No approval step or human checkpoint appears in pp.1–43.**

**Testing**
- A Testing tab and module exist. [SCR p.2–3]
- An "Agent Studio testing module" with access-permission analysis is mentioned in a role description. [SCR p.37]
- The tab is not opened in pp.1–43.

**Versioning and publishing**
- **View versions** on role/steps (a split button on the editable copy). [SCR p.14, 17]
- **Published** column on AI specialists. [SCR p.7]
- Active/Inactive **Status** on agents. [SCR p.11–13]
- Copied triggers are inactive. [SCR p.16]
- No publish or activate action is shown.

**Logging, observability, audit**
- **Activity** tab, **Analytics** module and "View analytics" link. [SCR p.2–3]
- **Created by / Updated** on every agent. [SCR p.11–13]
- **No run logs, traces, execution history or tool-call records are shown in pp.1–43.**

---

## 3. External agents and systems; governance and AI Control Tower

**AWS**
- "AI Service Graph Connector for Amazon" is the session's current app. [SCR p.14, p.16]
- Two "SG-AWS AgentCore AI Age…" import set tables exist. [SCR p.3, p.5]
- [INF] This is a Service Graph Connector that imports AWS Bedrock AgentCore AI-agent records into ServiceNow (CMDB or AI asset inventory). That would let AI Control Tower list AgentCore agents.
- **What it imports, how often, and which AWS identity it uses are not shown.**

**Exposing ServiceNow agents to outside callers**
- "Allow third party to access this AI agent — Enable for external discovery of this ServiceNow AI agent". [SCR p.22–24] Off throughout.
- [INF] "External discovery" sounds like a registry or agent-card style mechanism (A2A-like). **The PDF names no protocol.**

**A2A, MCP, REST, Integration Hub, Bedrock**
- **None are named in pp.1–43.**
- "Integration(s)" appears only in captions [CAP p.24 "integration points", p.26 "AI skills and integrations"].
- The "Add tool ▾" menu, where such tool types would likely be listed [INF], is never opened.

**Governance and AI Control Tower**
- "AICT Demo App V2" (Ticket Routing & Priority Agent, Inactive) and "AICT Security Analyzer Agent" (app AI Security and Privacy, created by `maint`, Active). [SCR p.11]
- [INF] AICT = AI Control Tower, and `maint` = shipped by ServiceNow.
- AI Admin Center controls (model providers, provider policy, model versions, AI Guardian/prompt injection, data and policy). [SCR p.8, 13]
- The platform flags agents with no ACL. [SCR p.2]
- **No AI Control Tower screens, inventory, risk or approval views appear in pp.1–43.**

---

## 4. What pp.1–43 offer for our three needs

### (a) An agent escalation creates an incident that a human works
- **Not shown.** No agent creates an incident or hands off to a human in pp.1–43.
- Closest analogs in the PDF:
  - The ready-made "**Create standard change request**" agentic workflow, an agent that creates an ITSM record. [SCR p.2–3]
  - "**Analyze network incidents**", a 5-agent workflow that "Assist[s] customer agents in resolving a given incident". [SCR p.8]
  - Tools are Flow actions that "execute platform features without having to write new code". [SCR p.25]
- [INF] Two build paths:
  - Inside ServiceNow: a "create incident" Flow action, with assignment group etc., attached as a tool.
  - From our AWS-side agents: create the incident through ServiceNow's APIs. This is not in the PDF.
- [INF] Either way, the incident's opened-by/caller would follow the run-as identity (Dynamic user vs AI user).

### (b) Evidence of who / what / approved / authorized
| Question | What the PDF shows |
|---|---|
| **Who may invoke the agent** | User access (specific roles / any authenticated / public) → **auto-generated ACL** [SCR p.29–32]; the "18 agents have no ACL" banner [SCR p.2]. |
| **As whom the agent acts** | **Dynamic user** (the sys_user of a trigger, workflow or user, which passes its roles) plus **Approved role(s)**; or an **AI user** (dedicated sys_user type with pre-defined roles, shown as "Selected AI user roles") [SCR p.34–43]. |
| **What it can do** | Tool list with execution mode [SCR p.25]; instructions with **View versions** [SCR p.14, 17]. |
| **Provenance** | Created by / Updated / Application / Status per agent [SCR p.11–13]; scope ownership ("Edit in original scope") [SCR p.14]. |
| **Approved** | **Nothing shown.** |

Inferences on identity:
- [INF] An **AI user** gives agent actions a distinct, attributable sys_user in record history and audit. That is easier to tell apart from human actions in an evidence chain.
- [INF] A **Dynamic user** acts under the human's identity. "Approved role(s)" is probably an allow-list or cap on which roles the agent may use. The exact rule is not stated; the "(i)" tooltip is not shown.

### (c) Reconstructing an agent run
- **Not shown.** The Activity tab, Analytics module and Testing tab exist [SCR p.2–3], but none is opened.
- Pages 1–43 show no execution logs, plan or step traces, tool-call records or run IDs. **Open for pp.44–86.**

---

## 5. Caption vs screenshot mismatches (do not repeat the caption claims)
1. **p.22–23:** captions say "Enable / Confirm third-party access". The toggle is **Off** on p.22, p.23 and p.24, including at the "Save and continue" step.
2. **p.43:** the caption says "permissions associated with the System Administrator role". The **Approved role(s) field is empty**; no admin role is visible. (If pp.44+ show admin being picked: that is the opposite of least privilege, and so is the "Any authenticated user" access chosen on p.32 [INF].)
3. **p.26:** the caption says "choose from available AI skills and integrations". **No picker is shown**, and the "Add tool" dropdown is never opened. The tools are the two inherited Flow actions.
4. **p.9:** the caption says "explore detailed information about the selected agentic workflow". **No detail page is opened**; only the list toolbar is highlighted.
5. **p.14:** the caption says "duplicating or deleting". Delete is present but **greyed out** on the read-only record (p.15). Minor.

---

## 6. Left open for pp.44–86
- Which approved role(s) are finally chosen (the caption hints at System Administrator), and whether data access is saved.
- The **Add triggers** and **Select channels and status** steps; activation or publishing; whether the third-party toggle is ever switched on.
- **Testing** tab (test runs, access analyzer), **Activity** tab (run or execution history, logs), **Analytics**, **Settings**.
- The **Add tool ▾** types: subflow, script, skills, Integration Hub, MCP, external agent? Also the alternatives to "Autonomous" execution mode (approval or supervised).
- How the **LLM provider** is chosen; whether AWS Bedrock or other external models can be selected; what "Model support" means.
- **External connectivity** (A2A, MCP, REST, Integration Hub); what the **SG-AWS AgentCore** connector does; any **AI Control Tower** views.
- Agentic-workflow detail and editing (team, base plan); the AI specialists object.

---

## Method note
- I read all 43 pages at page resolution. The only text layer (pdftotext) contains the captions.
- I extracted the native screenshots with `pdfimages` and cropped a few with PIL, into the temp folder `…/scratchpad/servicenow/_crops/` (about 87 PNGs, safe to delete). This let me quote small UI text exactly.
- I left out individual users' names that appear in "Created by" columns.

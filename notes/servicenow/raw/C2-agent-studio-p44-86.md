# C2: ServiceNow "Create and manage AI agents in AI Agent Studio", PDF pages 44–86

Source: `/Users/satyabratsrikumar/Downloads/create-and-manage-ai-agents-in-ai-agent-studio.pdf` (86 pp). This file covers pp. 44–86. A sibling agent covers pp. 1–43.

## How to read this file

- **Page/step offset:** PDF page N shows step N−1 (p44 = step 43 … p85 = step 84). p86 is a closing paragraph.
- **What the document is:** an auto-captioned click-through capture (Scribe/Supademo style) of one person building and testing **"Test AI Agent for the DTW Hackathon"** (badge "Chat") on the demo instance `platformdemoh8.service-now.com` (the p86 link is `https://platformdemoh8.service-now.com/now/agent-studio/overview`). The header avatar shows the user's initials, "SD".
- **The text layer has only the step title and a one-line caption.** All the substantive detail lives inside 1920×963 screenshots. I extracted those at native resolution, contrast-enhanced them, and read them.
- **The captions are often wrong about what the screenshot shows.** Each such case is flagged ⚠️CAPTION. Where they conflict, the screenshot is ground truth.
- **Labels used below:**
  - **[PDF p.N screenshot]**: read from the UI in the screenshot.
  - **[PDF p.N caption]**: the auto-generated caption only. Low reliability.
  - **[Inference]**: my interpretation, not stated in the PDF. Items marked "(general platform knowledge)" need checking on an instance.
- **Navigation shown:** the Agent Studio tabs are Overview / Create and manage / Testing / Activity / Settings. The global nav is All / Favorites / History / Workspaces / Admin, plus "Search or ask AI" [PDF p66 screenshot]. The left wizard is: Define the specialty → Add tools and information → Define security controls (Define user access, Define data access) → Add triggers → Select channels and status [PDF p44 screenshot]. Steps before "Define data access" are in the sibling's range.

---

## 1. Page-by-page summary

### A. Security controls: Define data access (pp. 44–46)

- **p44 (step 43) "Review Admin Role Warning"** [screenshot]
  - Page header: "Define data access — Choose the user identity this AI agent should run as to determine the roles and the data access permissions derived from them. **Remember, when AI agents can access data, they can also share that data with the human user who interacts with them.** Learn more."
  - "Select the user identity this AI agent will run as":
    - **User identity type\* = "Dynamic user"**
    - **Approved role(s)\*** is a dropdown, now open.
  - The highlighted option is **admin**: "The System Administrator role. This role has access to all system features, functions, and data, regardless of security constraints. 'Grant this privilege carefully.' If you have sensitive information, such as HR records, that you need to protect, you must create a custom 'admin' role for that area and train a person authorized to see those records to act as the administrator."
  - Other roles in the list:
    - `agent_admin`: "Can download and administer the system's built-in agent"
    - `agent_role_config_admin`: "Can access and modify Agent role configurations"
    - `agent_role_config_viewer`: "Can view Agent role configurations"
    - A role scrolled out of view, whose description ends "…update/delete the filters and policies that it creates. Additionally, policies and filters created by other users and out-of-the-box created one's will be accessible to this role in a read-only mode."
  - FAQ stems (answers collapsed):
    - "What is the difference between user …"
    - "What are approved roles and what do…"
    - "Can I ask it not to share data with a h…"
  - [Inference] "Dynamic user" probably means the agent runs as the invoking user, as opposed to a fixed service identity. The FAQ answer, which would confirm this, is not shown.
- **p45 (step 44) "Open Role Configuration"** [screenshot]
  - Approved role(s) now shows the chip **"admin ×"**. The click lands on blank space to close the dropdown.
  - ⚠️CAPTION: no "role configuration panel" opens.
- **p46 (step 45) "Save Role Settings"** [screenshot]
  - Final state: Dynamic user + Approved role(s) = **admin**. "Save and continue" is clicked.
  - [Inference] The demo grants admin immediately after the platform's own "grant carefully" warning. This is an anti-pattern for least privilege, not something to copy.

### B. Add triggers (pp. 47–52)

- **p47 (step 46) "Add AI Agent Trigger"** [screenshot]
  - Page text: "**A trigger lets you launch an AI agent without needing a user's request.** Triggers are optional, based on conditions or schedules you set, and launch agentic AI experiences."
  - The Triggers table header carries a pill reading **"Instruction for LLM"**.
  - Table columns: **Name, Trigger, Table, Conditions, Run as, Channel, Status, Remove**.
  - FAQs: "What if I don't add any triggers?", "When to add a trigger?", "What do launches look like?"
- **p48 (step 47) "Open Trigger Options"** [screenshot]: the "Add a trigger" dialog opens with the "Select a trigger\*" dropdown.
- **p49 (step 48) "Select Record Creation Trigger"** [screenshot]: the trigger types are:
  - **Record conditions:**
    - "Created — Occurs when a record on a given table is created" (selected)
    - "Created or updated"
    - "Updated"
  - **Scheduled:** "Daily — Occurs on a daily basis at a set time." The list scrolls, so there may be more types below.
- **p50 (step 49) "Access Trigger Settings"** [screenshot]: dialog fields:
  - "Create a new trigger": **Name\***, and **Trigger objective\*** pre-filled with **"Help me resolve ${number}"** (with an info icon and a preview/eye button).
  - A toggle showing **"Trigger is OFF"**.
  - "Define when this trigger occurs — Choose a table and set of conditions for launching this agentic workflow or AI agent." **Table\*** (empty).
- **p51 (step 50) "Open Trigger Configuration"** ⚠️CAPTION [screenshot]
  - The click is actually on **"Close dialog" (X)**. The Name field shows "Field is required", Trigger is OFF, and Table is empty.
- **p52 (step 51) "Save Trigger Settings"** [screenshot]
  - The Triggers table says **"No data to display."** "Save and continue" is clicked.
  - So **no trigger was created in this demo.**

### C. Select channels and status (pp. 53–64)

- **p53 (step 52) "Enable Chat Assistant Engagement"** [screenshot]
  - Page text: "Select channels and status — This AI agent can engage with users who initiate an interaction when it's available for use in channels. Select channels where you want this AI agent to be available to engage with users."
  - Card: **"Engage via Otto chat assistants"**, with an **Allow** toggle (off). "How it works":
    - First, users send a message to a chat assistant.
    - Then, this AI agent is discovered and used.
    - As a result, users see agentic responses from this AI agent.
  - "**Communicate this AI agent's process to users** — Describe this AI agent's work while users wait for a response and the step it has completed. For example, users can see 'Working on your request' when this AI agent is working and 'Worked on your request' when it completed this step."
    - "Generate messages" button.
    - **In-progress message** (placeholder "'Initiating AI agent' or 'Working on your request'"; 128 characters max).
    - **Completion message** (placeholder "'Initiated AI agent' or 'Identified next steps'"; 128 characters max).
  - Header buttons: **"Create new update set" ▾**, Exit, ⋮.
  - FAQs: "How does this AI agent get discovered?", "What's an agentic response?", "**Do users know they're interacting wit…**" (a transparency question; the answer is not shown).
- **p54 (step 53)** [screenshot]: highlights the same card. ⚠️CAPTION: no settings open.
- **p55 (step 54) "Access Display Settings"** ⚠️CAPTION [screenshot]: the click is the **Allow** toggle for Otto chat assistants, not a "display" setting.
- **p56 (step 55)** [screenshot]
  - The toggle is on. A banner appears: "**In addition, this AI agent is designed to be part of an agentic workflow that users can discover in the Otto panel**".
  - New section: "Choose chat assistants — These chat assistants were created in **Assistant Designer**", with a required **Chat assistants\*** field.
  - "Save and test" looks disabled until an assistant is chosen (low-res observation).
- **pp. 57–58 (steps 56–57)** [screenshot]: scroll, then click into the Chat assistants field. ⚠️CAPTION: the captions say "display options"/"UI configuration".
- **p59 (step 58) "Select AICT Assistantllm Tool"** ⚠️CAPTION [screenshot]
  - The option selected is the **chat assistant "AICT Assistant"**, with subtitle "llm". It is a channel, **not a tool**.
- **p60 (step 59)** [screenshot]: the chip "AICT Assistant ×" is in the field.
- **p61 (step 60)** [screenshot]: scroll only. ⚠️CAPTION: no tool configuration.
- **p62 (step 61) "Activate AI Agent"** [screenshot]
  - "**Activation status** — Activating this AI agent makes it available in related agentic workflows or, if there are no workflows, in engagement channels and triggered experiences."
  - Toggle: "This AI agent is active".
- **p63 (step 62)** [screenshot]: the toggle reads "This AI agent is active **Yes**".
- **p64 (step 63) "Save and Test Agent"** [screenshot]: clicks **"Save and test"**.

### D. Manual test (pp. 65–74)

- **p65 (step 64) "Access Testing Interface"** ⚠️CAPTION [screenshot]: the page is just loading (spinner next to Back). The highlighted pane is blank.
- **p66 (step 65)** [screenshot]: Testing tab → breadcrumb "Home > Manual Test".
  - "**Test one example of behavior** — Test how an AI agent or agentic workflow completes a task **or if it allows users permission to access it**."
  - Fields:
    - **Choose a test type\*** = "AI agent or workflow"
    - **Name of the AI agent or agentic workflow\*** = "Test AI Agent for the DTW Hackathon"
    - **Version\***
    - **Task\*** (also carries the "Instruction for LLM" pill; placeholder "Add an objective, such as a task or goal")
  - Buttons: Cancel / **Continue to test chat response**.
  - Sidebar: "**Why do I need a test type?** Set parameters so you can easily test how agents behave in different scenarios—like security checks, discovery flows, or task automation. These parameters let you simulate real conditions (e.g., user roles, data inputs, system states) to see how the agent responds. It's a simple way to preview and fine-tune agentic workflows without needing to go live or dig into backend logic."
- **p67 (step 66)** [screenshot]: Task = "analyze case".
- **p68 (step 67)** [screenshot]: the form shows **Version\* = "1 - V1 (Active)"**. The user clicks the global **Workspaces** menu.
- **p69 (step 68)** [screenshot]: the Workspaces menu lists, in order:
  - **AI Admin Center**
  - **AI Control Tower (Legacy)**: the bottom half of the glyphs is covered by the callout, but it reads clearly.
  - The callout covers the rows between AI Control Tower (Legacy) and Asset Workspace. [Inference from row spacing] Probably two entries are hidden there.
  - Asset Workspace; Automation Center Workspace; CMDB Workspace; **CSM/FSM Configurable Workspace** (clicked); ITOM Infra Services Workspace; Knowledge Center; Now Assist Readiness Evaluation; Process Mining Workspace; Service Operations Workspace.
- **p70 (step 69)** ⚠️CAPTION [screenshot]
  - The CSM/FSM Configurable Workspace home: "Hello there! Get a little help monitoring your work…".
  - KPI cards: Draft/Published specifications and Draft/Published product offerings, all 0. Performance charts show "No data available".
  - The user clicks the list icon in the left rail.
  - Nothing about "tailoring the testing environment" is shown. [Inference] This is a detour.
- **pp. 71–72 (steps 70–71)** [screenshot]: back on the Manual Test form; Task = "analyze case".
- **p73 (step 72)** [screenshot]: Task = **"analyze case INC0010190"**, an incident number.
- **p74 (step 73)** [screenshot]: clicks "Continue to test chat response".

### E. Observing the run (pp. 75–85): the key pages for evidence

- **p75 (step 74)** [screenshot]: breadcrumb "Home > Manual Test > **AI Agent or Workflow**". The page has three panes and an "Edit agent" button at top right.
  1. **Left: narrative step list.** "Started AI Agent Test AI Agent for the DTW Hackathon", "Used the tool 'Fetch current task information'", "Checking on remaining steps".
  2. **Centre: execution map.** Task Start → Test AI Agent… (AI Agent) → Fetch current task informa… (Tool). Has "Find on map" and zoom, fit, hide and locate controls.
  3. **Right: "AI agent decision logs".** Text: "Observe the AI agents as they work to solve the task. Watch their interactions, decisions, and thought processes as they happen in real time." There is a **download icon** in the header.
     - Entries: **Access verification — Completed**; **Test AI Agent for the DTW Hackathon (AI Agent) — Ongoing**; ▸ **Gen AI - AIA ReAct Engine** (external-link icon) — Completed; ▸ **Tool - Fetch current task information** — Completed.
- **p76 (step 75)** [screenshot]: expands the first Gen AI entry. ⚠️CAPTION: "Open Tool Details" (this and the captions through p84 call the decision-log entries "tool details/configuration/dashboard/summary". They are all just log rows being expanded).
- **p77 (step 76)** [screenshot]: the Gen AI entry shows **Latency factors** "175" and "3 secs". The Thought text begins (full text under p83 below). New rows appear: Gen AI (Completed) and **Tool - Verify standard task information** (Completed).
- **p78 (step 77)** [screenshot]: Tool - Fetch current task information is expanded:
  - Latency factors "**526**" (an "ABC" icon) and "**959 ms**"
  - ▸ **Inputs**
  - **Output : null**
  - ▸ **Output Fields**
- **p79 (step 78)** ⚠️CAPTION [screenshot]: the run has finished.
  - An **"Assists summary"** collapsible appears at the top (left collapsed).
  - The AI Agent row turns **Completed**.
  - The last row reads "Gen AI - AIA ReAct Engine — ⚠ **High latency** — Completed".
  - The map now shows Task Start → AI Agent ✓ and Task Start → End ✓.
  - The click is on the left pane's collapse chevron, not "tool options".
- **p80 (step 79)** [screenshot]: the left narrative is fully expanded:
  1. Started AI Agent …
  2. Used the tool "Fetch current task information"
  3. Checked on remaining steps
  4. Used the tool "Verify standard task information"
  5. Checked on remaining steps
- **p81 (step 80)** [screenshot]: Gen AI → **Action → 0 → "Name : Fetch current task information"**, with ▸ **Action Inputs** and **Datatypes**.
- **p82 (step 81)** [screenshot]: the tool's Output Fields → "**Data collection status : Pass**", ▸ **Response** (collapsed).
- **p83 (step 82)** [screenshot]: the second Gen AI entry, latency "194" and "3 secs".
- **p84 (step 83)** [screenshot]: Tool - Verify standard task information, latency "**113**" and "**689 ms**", Output : null, ▸ Output Fields (collapsed).
- **p85 (step 84) "View AI Agent Activity"** [screenshot]: the final Gen AI entry is flagged **High latency**, with latency "**379**" and "**6 secs**" (the duration badge is yellow).
  - The user clicks the **Activity** tab, **but no Activity page is ever shown**. The caption's claim that it tracks "sessions, responses, and performance metrics" is **[PDF p85 caption] only**.
- **p86** [PDF text]: "This demo showcased how to create, duplicate, and configure AI agents within ServiceNow's AI Agent Studio. You learned how to manage workflows, set permissions, add tools, and test agents to optimize their performance." Followed by the "Get started" link to the instance's agent-studio overview.

**The complete recorded run** (all [PDF pp.75–85 screenshot]; quoted verbatim):

| # | Log row | Latency factors | Content |
|---|---|---|---|
| 1 | Access verification | — | Completed (no detail shown) |
| 2 | Gen AI - AIA ReAct Engine | 175 · 3 secs | "Thought : The task number is available from the request, and no prior actions have been executed. The next required step is to collect the task details for that exact task number before any verification can occur. This keeps the workflow aligned to the mandatory sequence and avoids any unsupported assumptions. Action Reasoning: Fetch current task information with the extracted task number." Action 0 = Fetch current task information |
| 3 | Tool - Fetch current task information | ABC 526 · 959 ms | Inputs (collapsed); Output : null; Output Fields: Data collection status : Pass; Response (collapsed) |
| 4 | Gen AI - AIA ReAct Engine | 194 · 3 secs | "Thought : Task information has already been collected successfully for the requested case, and the required details are available from prior work. The next unresolved step is to verify that same task before returning the full result set. This follows the mandated sequence and avoids repeating completed collection. Action Reasoning: Verify standard task information with the collected primary task number." |
| 5 | Tool - Verify standard task information | ABC 113 · 689 ms | Inputs (collapsed); Output : null; Output Fields (collapsed) |
| 6 | Gen AI - AIA ReAct Engine (⚠ High latency) | 379 · 6 secs | "Thought : The task number was extracted, the task details were collected successfully, and the same task was then verified. **Verification returned a stop result, so no further troubleshooting or downstream work is allowed.** The remaining required step is to **return the collected details and verification outcome to the orchestrator and exit**. Action Reasoning: Finish with a summary of the collected task details, verification status, and verification response." |

[Inference] The latency badges are not labelled with units:
- The Gen AI count (175/194/379, magnifier-sparkle icon) is probably tokens.
- The tool count (526/113, "ABC" icon) is probably characters or payload size.

---

## 2. By topic (pp. 44–86)

- **Agent management**
  - [PDF p53+ screenshot] "Edit agent", "Exit", "Create new update set".
  - [PDF p86 text] The guide as a whole covers "create, duplicate, and configure". Duplication is in the sibling's range.
- **Testing**
  - [PDF pp.66–74 screenshot] A Manual Test pins **agent + Version + Task** and takes a test type ("AI agent or workflow").
  - The page's own text says a test can also check "**if it allows users permission to access it**". The sidebar names "security checks… user roles" as simulated conditions. No other test type is shown being selected.
  - A test uses real record numbers (INC0010190).
- **Deployment and activation**
  - [PDF pp.62–63 screenshot] There is a single "This AI agent is active" toggle.
  - Activation exposes the agent "in related agentic workflows or, if there are no workflows, in engagement channels and triggered experiences."
  - [PDF pp.50–51 screenshot] Each trigger has its own on/off toggle and defaults to OFF.
  - [Inference] These two toggles are the native ServiceNow kill switches: agent-level and trigger-level.
- **Monitoring and analytics**
  - [PDF pp.77–85 screenshot] Per-step latency factors; an automatic **"High latency"** flag; an "Assists summary" (contents never shown).
  - [PDF p85 caption only] "Activity" tab is claimed to show "sessions, responses, and performance metrics". Unverified, since no screenshot exists.
  - [Inference] "Assists" is the Now Assist consumption/metering unit, so the summary is likely usage/cost.
- **Logs and audit of executions**
  - [PDF pp.75–85 screenshot] The "AI agent decision logs" are a hierarchical, real-time trace. Each row carries:
    - a type prefix (Gen AI / Tool), a name, and a status (Ongoing/Completed)
    - latency factors
    - ReAct **Thought** and **Action Reasoning**
    - **Action** {Name, Action Inputs, Datatypes}
    - tool **Inputs / Output / Output Fields / Response**
  - The panel has a **download** icon. [Inference] Probably exports the log; no tooltip or format is shown.
  - Each Gen AI row has an **external-link** icon. [Inference] Probably opens the underlying LLM-call log record. (General platform knowledge, unverified: AI Agent executions persist in `sn_aia_*` tables, and LLM calls in Generative AI Logs such as `sys_generative_ai_log`. Check this on the instance.)
- **Security and access control**
  - [PDF p44 screenshot] Run-as identity type ("Dynamic user") plus **Approved role(s)**.
  - The admin warning text (quoted above).
  - The data-sharing reminder: agents can share whatever data they can access with the human user.
  - Agent-specific roles: `agent_admin`, `agent_role_config_admin`, `agent_role_config_viewer`.
  - The **Run as** column on triggers [p47/p52].
  - **Access verification** is the first row of every run log [p75+].
  - [Inference] Access verification is the platform checking the invoking user against "Define user access" (sibling range) before the agent runs. Only the label and "Completed" are shown.
- **Guardrails**
  - No Now Assist Guardian, content filtering, PII masking or prompt-injection setting appears in pp. 44–86 [PDF-observed absence].
  - Related signals:
    - the admin warning;
    - the data-sharing reminder;
    - the "Instruction for LLM" pills, one beside the Triggers table header [p47/p52] and one on the Test Task field [p66]. [Inference] They appear next to LLM-related surfaces, but the PDF never says what they mean.
    - The agent's own instruction-level gate in the final Thought: "Verification returned a stop result, so no further … work is allowed" [p85]. [Inference] This comes from the agent's instructions or tool design in the sibling's range. It is not a platform guardrail.
- **Human-in-the-loop and approvals**
  - **No approval or human-review step is shown** in pp. 44–86 [PDF-observed absence].
  - The closest items:
    - the user-facing in-progress/completion messages [p53];
    - the FAQ "Do users know they're interacting wit[h]…" [p53];
    - the agent ending by returning results "to the orchestrator" rather than acting further [p85].
- **Versioning**
  - [PDF p68 screenshot] "Version\* = 1 - V1 (Active)" on the test form.
  - [PDF p53+ screenshot] a "Create new update set" button in the agent editor.
  - [Inference] Update sets are ServiceNow's change-capture and promotion mechanism, and the test is pinned to a specific version, which gives "what version ran".
- **Troubleshooting**
  - [PDF screenshots] "Field is required" validation [p51]; "High latency" flags [p79–85]; "Edit agent" from the run page [p75+]; the map and log let you see which step stalled.
  - No error, retry or failure path is demonstrated: every step completed.
- **AI Control Tower and governance tie-ins**
  - [PDF p69 screenshot] The instance has **"AI Control Tower (Legacy)"** and **"AI Admin Center"** workspaces. Some adjacent entries are hidden by the callout ([Inference from row spacing] probably two).
  - [PDF p59 screenshot] The agent is published to the chat assistant **"AICT Assistant"** (subtitle "llm").
  - Pages 44–86 do **not** show the agent being registered in, governed by, or reported to AI Control Tower, and do not open the AICT workspace.
  - [Inference] The "(Legacy)" suffix implies a newer AICT experience exists on this instance, possibly one of the two hidden entries.

## 3. Connecting to external agents and systems (AWS, A2A, MCP, REST, Integration Hub, external LLMs)

- **Nothing in pp. 44–86 shows any of these** [PDF-observed absence]. No AWS, A2A, MCP, REST, Integration Hub, external-LLM provider, model picker or connection settings appear.
- The only "integration" surfaces are internal:
  - "Engage via **Otto** chat assistants" and the "Otto panel" [p53–56]. [Inference] Otto is this instance's branded Now Assist chat panel.
  - Chat assistants "created in **Assistant Designer**" [p56].
  - The "AICT Assistant" assistant [p59].
- The model is shown only as "**Gen AI - AIA ReAct Engine**" [p75+]. Neither the provider nor the model name is displayed.
  - [Inference] AIA = ServiceNow AI Agents. Nothing on these pages evidences "other models".
- Tools and external capabilities would be configured in "Add tools and information" (the sibling's range, pp. 1–43). Check the sibling's notes for any external-connection material.

## 4. Usable for our three needs

### (a) An agent escalation that creates an incident a human works

- The PDF shows the **inverse** direction:
  - A record-creation trigger ("Created — Occurs when a record on a given table is created", objective "Help me resolve ${number}") can **launch** an agent [p49–50]. In this demo it was closed without being saved [p51–52].
  - The test feeds an existing incident number, INC0010190 [p73].
- No step shows an agent creating an incident or task, assigning it, or a human picking it up [PDF-observed absence]. The CSM/FSM workspace visit [p69–70] shows only an empty home page.
- [Inference] Two usable pieces:
  1. A trigger on `incident` creation could launch a ServiceNow-side agent when our gateway's escalation lands as an incident.
  2. The "stop → return to orchestrator and exit" pattern [p85] is a ServiceNow-native shape for "agent halts; a human or orchestrator takes over".

  The record-creating tool itself would be configured in "Add tools and information" (sibling's range).

### (b) Evidence of who / what / approved / authorized

| Question | What the PDF shows | Gaps |
|---|---|---|
| **Who (identity)** | Run-as identity type "Dynamic user" and Approved role(s) [p44–46]; per-trigger **Run as** [p47]; the logged-in tester's initials "SD" [p66+] | The decision log does **not** display the user, session or timestamp on any row [PDF-observed absence] |
| **Authorized** | "Access verification — Completed" as the first log row of every run [p75+]; the admin "grant carefully" warning and agent-specific roles [p44]; tests can check "if it allows users permission to access it" [p66] | Access verification shows no detail of what was checked |
| **What** | Agent name, **Version "1 - V1 (Active)"** [p68], the task text [p73], every LLM step (Thought, Action Reasoning, Action name) and tool call (Inputs, Output, Output Fields, status, latency) [p75–85] | — |
| **Approved** | Nothing: no approval or sign-off step anywhere in pp. 44–86 | The only "approval"-like control is who may set the active and trigger toggles, and that is not shown |

### (c) Reconstructing an agent run end to end

- **Available** [PDF pp.75–85 screenshot]:
  - three synchronized views (narrative steps / execution map / decision logs) with the full ReAct chain;
  - per-step status and latency, with a high-latency flag;
  - tool I/O expanders;
  - a download icon;
  - external links from each Gen AI step;
  - an end-state map (Task Start → AI Agent → End).
  - The six-row run table above is a ready example of ServiceNow's evidence granularity.
- **Not shown:**
  - per-step timestamps, run/execution ID, correlation or trace ID;
  - the invoking user on log rows;
  - the model or provider name;
  - prompt text and raw tool inputs (collapsed);
  - Assists summary contents, Activity tab contents, the download format;
  - whether any of this is exposed via API.
- [Inference] To show ServiceNow "Control Tower adds additional observability" for our AWS AgentCore runs, we would need to emit an equivalent hierarchy: access check → agent → model call (thought/action) → tool call (inputs/outputs/status/latency) → final outcome. Nothing in pp. 44–86 shows a way to push externally run agent traces into this log. Look for that in the sibling's pages, the AI Control Tower docs, or the instance itself.

## 5. Caption-vs-screenshot mismatches (so nobody inherits phantom features)

- p45, p51, p54, p55, p57–58, p61, p65, p70, p76–84: captions describe "role configuration panel", "trigger configuration", "display settings", "UI configuration", "tool settings/configuration/options/interface/features/panel/dashboard/summary" and "tailoring the testing environment". The screenshots show closing dialogs, toggling Allow, picking a chat assistant, page loads, a workspace detour, and expanding decision-log rows.
- p59: "AICT Assistantllm **Tool**" is a **chat assistant** named "AICT Assistant" with subtitle "llm".
- p85: the "View AI Agent Activity" caption is the only source for the Activity log's contents. The tab is clicked but never displayed.

# B: AICT console walkthrough PDF, research notes

**Source:** `/Users/satyabratsrikumar/Downloads/navigate-ai-control-tower-and-manage-ai-agents.pdf`, "Navigate AI Control Tower and Manage AI Agents in ServiceNow".
- 30 A4 pages, produced by react-pdf. pdfinfo CreationDate: **2026-09-30 12:13 CDT**.
- It is a click-by-click walkthrough export. Each page holds one step: one or two narration sentences plus one 1920x963 screenshot.
- I read every screenshot at native resolution.
- The narration is speech-to-text. "EI agents" means "AI agents".

**Page convention:** PDF page N = step N-1.
- p1 = title and intro.
- p2 = step 01 … p29 = step 28.
- p30 = closing summary.
- Page numbers below are PDF pages.

**Labels used on every claim:**

| Label | Meaning |
|---|---|
| [PDF-text] | The PDF narration says it. |
| [PDF-screen] | It is visible in a screenshot. |
| [Inference] | My reading. The PDF does not state it. |
| [Team-notes] | From the team's memory or repo notes, not from this PDF. |
| [M11 l.N] | Module 11 text, line N of the sibling agent's `scratchpad/servicenow/module11-reconstructed.txt` (I only read it). |

**Instance:** `platformdemoh8.service-now.com` [PDF-text p2]. The presenter's account sees every nav item and both established connectors, so it looks like an admin or full-access account [Inference].

---

## 0. Key takeaways

1. **Being "Managed" is the gate for all runtime insight.**
   - An Unmanaged asset shows the banner "This asset is currently unmanaged and has limited functionality. Start managing this asset to take action on it and view its data." [PDF-screen p5, p6, p10]
   - Its Monitor tab shows "Unable to show Monitor dashboard … you'll need to manage this asset." [PDF-screen p10]
   - Insights > Monitor: "Only managed assets are evaluated." and "Only Agentic AI assets are evaluated." [PDF-screen p20]
2. **Sessions are sampled.** "These sessions are being evaluated based on the established sample rate." [PDF-screen p21]
   - AICT is therefore not a complete record of runs [Inference].
3. **The runtime security numbers are demo data.** "You see the demo data that we loaded here." [PDF-text p15]
   - Design-time shows "AI security exposure management plugin isn't installed" [PDF-screen p14].
4. **AWS discovery is shown.** The AI systems list holds `network_resolution_agent`, `customer_experience_agent` and `it_resolution_agent`, narrated as "pre-created agents in the AWS environment that were discovered before" [PDF-text + PDF-screen p4].
   - These are the same names as the team's AgentCore runtimes [Team-notes: workshop-progress.md l.74].
   - The PDF was created 2026-09-30. The team account's AICT stacks were created 2026-10-04 [Team-notes: workshop-aws-access.md].
   - So these rows are same-named reference agents from a facilitator or test account, not the team's own [Inference].
5. **No AWS-discovered agent appears among the evaluated sessions** [PDF-screen p21].
   - The only trace opened is a LangGraph + `ChatOpenAI.chat` app with `traceloop_*` attributes (OpenLLMetry/OTel) [PDF-screen p25-26].
   - The narration "After you create your agents in AWS … and after you run it, you have the associated sessions" [PDF-text p21-22] is asserted, not demonstrated.
6. **Tool evidence is asserted but not shown.** The narration says "in case the tools were called, what kind of tools, what was invoked … the whole evidence track is going to be available in this trace" [PDF-text p26].
   - The trace actually shown has `"tool_calls": []` [PDF-screen p25-26].
7. **The judge metrics shown would not catch an unbacked action claim** [Inference from PDF-screen p22, p25-26]. In the demo trace:
   - The model says it will "pass these along to the payroll system now", yet `tool_calls` is empty.
   - Answer Relevancy is 100%.
   - Secrets Detection is 100% (safe), although the user input and the model output both contain a bank account number and a routing number.
   - AICT also stores the raw prompt and response content, PII included.
8. **No incident, escalation or API flow appears anywhere in the PDF.**
   - The work-item surfaces that exist are: Pending work items (p2), Activity Center recommendations with Assigned to you / Unassigned (p5), the "Actions" column on security events (p16), "Configure" (p16), and the Playbooks / Rules and templates nav items (p2).
   - None of these is opened.
9. **No roles are stated anywhere.** The hints are:
   - A Settings > "Users and roles" nav item exists (p2).
   - The narration says "You're not going to see all those connectors available" (p29).
10. **The PDF and Module 11 differ on who sets up the connector.**
    - The PDF says "what you need to do first is set up the integration … pick your AI connection for Amazon … It's where you will set up the connector" [PDF-text p27, p29].
    - Module 11 says: "A facilitator enters the redacted values … Participants do not enter these values" [M11 l.110-111].
    - In the team account, facilitators (`WSOpsRole`) already deployed the AICT stacks [Team-notes].
    - Module 11 also says this PDF covers "discovered assets, lifecycle, reviews" [M11 l.35]. The PDF shows lifecycle and reviews only as field values (the Lifecycle tab is never opened).

---

## 1. Page-by-page summary

| PDF p | Step | Title | What it shows |
|---|---|---|---|
| 1 | — | Title | Video thumbnail (© 2026 ServiceNow). Intro: "introduces the AI Control Tower … navigating AI agents, assets, and security features to manage and monitor AI systems effectively" [PDF-text]. |
| 2 | 01 | Explore AI Control Tower Homepage | "Go to platformdemoh8.service-now.com". "the AI Control Tower that will be part of your hackathon experience" [PDF-text]. Home widgets [PDF-screen]: see list A below the table. |
| 3 | 02 | View Stored AI Systems | **Inventory > All (416)** [PDF-screen]: see list B below the table. |
| 4 | 03 | Access Incident Summarization Agent | **Inventory > AI systems (64)** [PDF-screen]. Rows include: <br>• AICT Assistant / AIA Assistant / Virtual Agent Conversation: Deployed, Approved, Managed. <br>• Incident Summarization Agent: Cancelled, In review, Unmanaged, Low. <br>• HR Resume Screening Agent: Cancelled, In review, Unmanaged, High. <br>• Knowledge Article Generator: Cancelled, In review, Unmanaged, Low. <br>• Ticket Routing & Priority Agent: Cancelled, Approved, Unmanaged, Medium. <br>• Incident summarization (Generative AI): Deployed, Approved, Managed. <br>• Test agent TMT: Design, In review, Managed. <br>• **network_resolution_agent: Agentic AI, Deployed, Approved, Managed (Managed by = the presenter), To be determined.** <br>• **customer_experience_agent and it_resolution_agent: Agentic AI, State "-", Status "-", Unmanaged, no owner, To be determined.** <br>Narration: "That's where you will actually see your EI agents you will create in ServiceNow and in AWS environment. Here is the example of the pre-created agents in the AWS environment that were discovered before." [PDF-text] |
| 5 | 04 | Open Agent Details | Asset page "Incident Summarization Agent" [PDF-screen]: see list C below the table. |
| 6 | 05 | Review Agent Manager Information | **Details tab** [PDF-screen]: full field list in §4. <br>• Description: "Gathers incident context from ServiceNow CMDB and generates structured summaries…" <br>• Use and purpose (7 fields). <br>• **Asset relationship map:** centre = the Agentic AI asset; it "uses" an AI model, a Tool ("AI Tool: ServiceNow…") and an AI prompt; it is "evaluated using" an AI dataset; it "depends on" an AI System; more edges are cut off. <br>• Attachments ("Upload JPG, JPEG, PNG, GIF, PDF, or XLSX files (max 10 MB)"). <br>Narration: "various tools, AI models, data set … the detailed cards of the agent who is managing this agent and what is a life cycle state of it … if this agent was live or is live, you will be able to see on the monitor tab the insights" [PDF-text]. |
| 7, 8 | 06, 07 | Select Cancelled Status (twice) | Same screen as p6 with the cursor on State = Cancelled. "Click the Cancelled status to filter or view related information." [PDF-text] No new UI. |
| 9 | 08 | Open Monitoring Section | Same as p6, cursor on the Monitor tab. Narration: "The second part you would be interested in is security." |
| 10 | 09 | Proceed to Next Monitor Step | **Monitor tab on an Unmanaged asset:** "Unable to show Monitor dashboard. To start seeing the dashboard, you'll need to manage this asset. Managing an asset allows you to get more details about how it's performing." [PDF-screen] |
| 11 | 10 | Access Security Overview | Govern expanded: **Risk & compliance**, **Security** [PDF-screen]. "different time information about the security aspects of the agents, vulnerability details based on the techniques we apply as part of ServiceNow" [PDF-text]. |
| 12 | 11 | View Design-Time Security | **Govern > Security > Overview** (tabs Overview, Design-time, Runtime, Post runtime) [PDF-screen]: see list D below the table. |
| 13 | 12 | Explore Vulnerabilities by Technique | **Design-time** [PDF-screen]: see list E below the table. |
| 14 | 13 | Check Runtime Security Details | Design-time with banner **"AI security exposure management plugin isn't installed. Install this plugin to unlock additional vulnerability and remediation metrics." [Install]** [PDF-screen]. Narration: "On the model information that we have and potential prompts associated. That's for the runtime." |
| 15 | 14 | Review Post Runtime Security | **Runtime** tab with the filter "Internal Agents" [PDF-screen]. "Total prompt injection detected and blocked: 3 (Sum for Jul 2026 - Sep 2026)". "Total offensive content detected and blocked: 3". Narration: **"You see the demo data that we loaded here."** |
| 16 | 15 | Inspect Data and Model Poisoning | **Post runtime** tab with a [Configure] button [PDF-screen]: see list F below the table. |
| 17, 18 | 16, 17 | Agentic Goal Deviation / Continue | Same screen as p16 (cursor moves). Narration: "the post-runtime, the post-analysis of the agents." |
| 19 | 18 | Return to Monitor Section | Same as p16. Insights expanded: **Monitor, Value, Engagement ▾, ServiceNow AI ▾** [PDF-screen]. |
| 20 | 19 | Open Evaluated Sessions Tab | **Insights > Monitor > Overview** (tabs Overview / Evaluated sessions; "Last 30 days") [PDF-screen]: see list G below the table. |
| 21 | 20 | Select Specific Session | **Evaluated sessions (38)**: "These sessions are being evaluated based on the established sample rate." [PDF-screen] See list H below the table. Narration: "After you create your agents in AWS for ServiceNow and after you run it," |
| 22 | 21 | View Answer Relevancy Details | **Session S00000180** [PDF-screen]: see list I below the table. |
| 23, 24 | 22, 23 | Examine Evaluation Score / Open Trace | Same screen as p22. "Click to view the average score of spans with this metric evaluated and judge's reasoning." "When you click on the traces, you will see all the information that was used for the evaluation." [PDF-text] |
| 25 | 24 | View Trace Content | **Trace drawer #00000220** [PDF-screen]: see list J below the table. Narration: "The content itself, the response of the agent." |
| 26 | 25 | Review Tool Invocation Details | The same drawer, scrolled [PDF-screen]: see list K below the table. Narration: **"in case the tools were called, what kind of tools, what was invoked, what information was processed. So the whole evidence track is going to be available in this trace and in this session details."** |
| 27 | 26 | Access Integrations Section | Same as p22, cursor on Settings > Integrations. **"Last but not least, what you need to do first is set up the integration."** [PDF-text] |
| 28 | 27 | Open Available Connectors | **Settings > Integrations** (tabs **Connectors / Traces / Multi-instance / Security**). Sub-tabs Available connectors (6) / Established connections (2): "These are your active and inactive connectors. Select a connector to view or edit details." Cards **"Test Hackathon 26"** and **"TMF 2026 Hackathon"**: Source system "—", Processing state Success, Connection state Success [PDF-screen]. |
| 29 | 28 | Select AI Connector | **Available connectors (6)**: "Select a cloud hyperscaler or SaaS application to discover AI assets and manage them in AI Control Tower. The discovered AI assets appear in your AI asset inventory. Learn more". The six are AI Connector for Amazon, AI Connector for Microsoft, Databricks, GCP Vertex AI, n8n, Salesforce [PDF-screen]. Narration: "You're not going to see all those connectors available … pick your AI connection for Amazon. You will be redirected to a new tab … It's where you will set up the connector" [PDF-text]. The setup tab itself is **not shown**. |
| 30 | — | Closing | "exploring AI agents, security monitoring, session evaluations, and setting up integrations … access detailed information about AI assets and manage connectors for AI connections." [PDF-text] |

**A. Home widgets (p2)** [PDF-screen]
- Pending work items: 1.
- "Get started with AI Control Tower: Configure how you manage and govern AI across your organization and track your progress in one place" [Set up now].
- **Your top recommendations**, with the caveat "Always confirm that these recommendations are accurate…":
  - 1-Critical "Monitor Security": "Critical AI Asset events" [Open].
  - 1-Critical "Drive AI productivity": "Correctness drops to 0 for research domain queries vs 100 for general information requests…" and "Correctness drops to 0 across all traces while safety remains at 100, indicating systematic fabrication…".
  - Twice: "Dormant AI system detected" [Automate with Otto].
- **Inventory:** 416 total, Unmanaged 259, Managed 157.
- **Governance posture summary** ("for all managed AI assets"): Quality, Safety, Security, Compliance and Residual risk bars. Legend: N/A, Needs attention, Monitor, Healthy.
- **Regulatory risk classification** ("for Managed AI systems, AI models, and datasets"): 6 total, High 1, Medium 2, Low 3.
- **AI value:** $122.6K, +208.41% in 30 days.

**B. Inventory > All (p3)** [PDF-screen]
- Tabs: All, AI systems, AI models, **MCP servers**, Datasets, "…".
- Button: **[Add AI asset]**.
- Locked class filters joined by OR: AI System Digital Asset, AI Model Digital Asset, AI Prompt Digital Asset, AI Dataset Digital Asset, **MCP Digital Asset**.
- Columns: Name, Asset type, State, Status, Managed status, Managed by, Risk classification, Updated.
- **Refine results** filters:
  - Managed status: Managed, Unmanaged.
  - Managed by.
  - Risk classification: Critical, Unacceptable, High, Medium, Low.
  - State: Ideation, Design, Build, Available, Deployed, Show all.
  - Status: In review, Ready for deployment, Attention needed, Approved, Rejected, Show all.
- Toolbar: search, filter, refresh, columns, **Action ▾**.

**C. Asset page "Incident Summarization Agent" (p5)** [PDF-screen]
- Header chips: "Cancelled & In review", "Low risk", "Unmanaged", "Agentic AI", owner name.
- Tabs: **Overview, Details, Lifecycle, Risk & compliance, Monitor, "…"**.
- Banner: "This asset is currently unmanaged and has limited functionality…" **[Move to Managed]**.
- **Needs attention** ("Review and take action to ensure smooth operations of AI in your org"). Tabs: Recommendations / Assigned to you / Unassigned. Items:
  - 1-Critical: Critical AI Asset events.
  - 2-High: High AI Asset events.
  - 2-High: "Incident Summarization Agent fails to retrieve incident and CI context after CMDB Lookup returns empty results…".
  - 2-High: "High-usage unmanaged AI system" [View details].
  - 4-Low: Low AI Asset events.
  - Link: "See all Recommendations (5) in Activity Center".
- Below that is "Key details", cut off.

**D. Govern > Security > Overview (p12)** [PDF-screen]
- Top recommendations: Critical, High and Low AI Asset events; "See all Recommendations (3) in Activity Center".
- **AI asset security score: 98%.**
- **Contained AI Agents** ("Since last 30 days"): 0.
- **Privileged AI agents** ("AI agents with elevated access permissions"): 0, "-100% from Sep 23".
- **Dormant AI agents** ("no activity in 90+ days"): 3.
- **Agent map** ("Shows how AI agents communicate across systems, services, and endpoints"): **Amazon 16 agents**, Microsoft 12, Google 2.
- Narration: "Different types of models are evaluated … that's for the design time based." [PDF-text]

**E. Govern > Security > Design-time (p13)** [PDF-screen]
- **Model vulnerabilities:** "Our SecOps design time vulnerability metrics are powered by continuous signals from scanners, threat intelligence, and platform telemetry…"
  - Models with vulnerabilities: 107.
  - By **MITRE ATLAS** technique: AI Supply chain, Model Evasion, AI Model Access, Data Poisoning, AI Model Manipulation.
  - By severity: **32** in total (HIGH 78%, CRITICAL 13%, MEDIUM 6%, LOW 3%).
- **Model validation:** "SecOps model validation combines automated model scanning, AI red-teaming signals, and security guardrails…"
  - Models validated: 6093.
  - Validations by **OWASP** category: LLM02:2025 Sensitive…, LLM01 Prompt Injection, LLM01:2025, LLM09:2025 Misinfor…, LLM06 Sensitive Infor….
  - Top 5 threat categories: Prompt Injection 589, Social Engineering 566, Data Leakage 545, Malware Exploits 431, Policy Circumvention 175.
  - A "Successful attacks" gauge is cut off.

**F. Govern > Security > Post runtime (p16)** [PDF-screen]
- **"Top AI asset security events"**, "organized by the top Open Worldwide Application Security Project (OWASP) categories". Filter: "All Providers".
- Heatmap for Apr–Sep 2026 with these rows: Sensitive Information Disclosure, Data and Model Poisoning, Agentic Goal Deviation, Prompt Injection, Excessive Agency, System Prompt Leakage, Improper Output Handling.
- The Sep column is 43, 83, 36, 151, 23, 37, 32. That sums to 405 and matches the caption.
- **Recent AI Asset security events (100):** "Results for all categories · Sep 2026 · 405 results (showing top 100 by detection time)".
  - Columns: Category, Threat type, **AI asset**, **Provider**, Description, Detected on, **Actions**. No rows are visible.

**G. Insights > Monitor > Overview (p20)** [PDF-screen]
- Top recommendations (all 1-Critical, "Drive AI productivity"): the two correctness drops (as on p2) and "Quality score drops to 0 for all sessions containing prompt injection and harmful content requests…".
- **AI systems: 64 (Managed 41, Unmanaged 23), "Only managed assets are evaluated."**
- **Asset types: Agentic AI 60, Generative AI 4, "Only Agentic AI assets are evaluated."**
- "AI systems ranked by score" (Agentic only): Intent Classifier 80%, Metric Aggregator 86%, Escalation Handler 86%, Reserved Instance Advisor 95%, Tone Reviewer 95%.
- Average overall Quality: 95%. Average overall Safety: 100%.
- "Monitor agent activity" is cut off.

**H. Evaluated sessions (p21)** [PDF-screen]
- Columns: Name, Traces, **AI system** (versioned, e.g. "Action Item Extractor 1.0"), Quality score, Safety score, Start time, End time, **Total runtime tokens**.
- Session #S00000180: Action Item Extractor 1.0, 1 trace, 98% / 100%, 2026-09-30 **09:23:38–09:23:39**, 1,050 tokens.
- #S00000261 has **no AI system**, Quality 50% and a blank Safety score.
- None of the 8 visible sessions belongs to an AWS-discovered agent.
- Above the table is a Quality-vs-Safety bar chart per AI system.

**I. Session S00000180 (p22)** [PDF-screen]
- Quality 98%, Safety 100%.
- "A session consists of a group of traces, usually including all user requests and their processing in a single interaction."
- **Session scores and aggregate scores (2):**
  - Answer Relevancy: 100%, Provider ServiceNow, Level Span.
  - Secrets Detection: 100%, ServiceNow, Span.
  - Both give the reason "This is an average score of 1 spans with this metric evaluated. Look into each span to see judge's reasoning."
- **Traces (1):** Trace #00000220, **2026-09-30 16:23:38.000 - 16:23:39.000**, Duration 1 sec, Spans 3, Input tokens 817, Output tokens 233, Total 1050, Quality **N/A**, Safety 100%.

**J. Trace drawer #00000220 (p25)** [PDF-screen]
- Span tree: Trace → **Span: LangGraph.workflow** (1000 ms) → **Span: model.task** (1000 ms) → **Span: ChatOpenAI.chat** (1000 ms).
- Evaluation scores table: metric, score, reason.
- Details with Input / Output tabs and [Open details].
- The JSON is a LangChain-serialised AIMessage. Its content starts "Got it, I've noted your details. Bank account: …, routing: … I'll pass these along to the payroll system now…".
- **`"tool_calls": []`**, `"invalid_tool_calls": []`, tags `graph:step:1`.
- Previous trace / Next trace navigation.

**K. The same drawer, scrolled (p26)** [PDF-screen]
- **`traceloop_association_properties_session_id`** holds a UUID.
- **`traceloop_span_kind: "workflow"`**.
- **System:** "You are a helpful assistant. Answer the user's question clearly and concisely."
- **User:** a direct-deposit request that contains a bank account number and a routing number.

---

## 2. AICT concepts and objects

### 2.1 Navigation (left nav) [PDF-screen p2, p11, p19]
- **Home**
- **Activity Center** ▾
- **Inventory**
- **Govern** ▾: Risk & compliance, Security
- **Insights** ▾: Monitor, Value, Engagement ▾, ServiceNow AI ▾
- **Settings** ▾: Users and roles, Integrations, Rules and templates, Playbooks, ServiceNow AI

### 2.2 Asset inventory [PDF-screen p2-p4]
- AI assets are "Digital Asset" classes:
  - AI System
  - AI Model
  - AI Prompt
  - AI Dataset
  - **MCP**
- Asset types seen: Agentic AI, Generative AI, AI prompt.
- Counts on this instance: 416 assets in total; 64 AI systems (60 Agentic, 4 Generative).
- **"Add AI asset"** = manual registration [PDF-screen p3]. The PDF never shows the registration form.

### 2.3 Discovered assets and connectors [PDF-screen p28-29; PDF-text p4, p29]
- Settings > Integrations > Connectors. Six available connectors: Amazon, Microsoft, Databricks, GCP Vertex AI, n8n, Salesforce.
- The page says: "discovered AI assets appear in your AI asset inventory".
- Discovered AWS agents arrive as **Unmanaged, with blank State and Status, no owner, and risk "To be determined"** [PDF-screen p4: customer_experience_agent, it_resolution_agent].
- One discovered agent (`network_resolution_agent`) had been moved to Managed, Deployed and Approved by the presenter's account [PDF-screen p4]. That a human did this is my reading [Inference].
- Settings > Integrations also has a **Traces** tab, plus Multi-instance and Security tabs. **None of them is opened** [PDF-screen p28].

### 2.4 AI agents (AI systems) [PDF-screen p4-p6]
- Each agent is an asset record with:
  - a header (state & status, risk, managed status, type, owner)
  - tabs: Overview, Details, Lifecycle, Risk & compliance, Monitor, "…"
- In Monitor, AI systems appear with versions ("Alert Triager 1.0") [PDF-screen p21].

### 2.5 Lifecycle states [PDF-screen p3-p6]

| Field | Values shown | Notes |
|---|---|---|
| **State** | Ideation, Design, Build, Available, Deployed (+ "Show all"; Cancelled seen in rows) | — |
| **Status** | In review, Ready for deployment, Attention needed, Approved, Rejected | — |
| **Managed status** | Managed, Unmanaged | This is the operational gate (§0.1). |

The **Lifecycle** tab exists but is **never opened**, so its contents are unknown.

### 2.6 Reviews and approvals
- Approval appears **only as the Status field value** ("Approved", "In review", "Rejected"…) [PDF-screen p3-p4].
- Not shown: an approval workflow, the approver's identity, the approval time, approval history, or a link to a specific version.
- "Pending work items: 1" (p2) and Activity Center "Assigned to you / Unassigned" (p5) suggest a work-item layer exists [Inference].

### 2.7 Risk
- **Risk classification** values: Critical, Unacceptable, High, Medium, Low, To be determined [PDF-screen p3].
- "Regulatory risk classification" widget: 6 classified managed assets [PDF-screen p2].
- The Govern > **Risk & compliance** page (p11) and the asset **Risk & compliance** tab (p5) are **never opened**.
- "Unacceptable" plus "Regulatory" suggests EU-AI-Act-style tiers [Inference].

### 2.8 Policies
- **Nothing on policy content is shown.**
- The only policy-like nav items are Settings > Rules and templates and Playbooks (p2), and the Post runtime "Configure" button (p16). All are unopened.
- No per-call authorization or policy decision appears anywhere [PDF-screen, by absence].

### 2.9 Security (Govern > Security) [PDF-screen p12-p16]
- **Overview:**
  - security score
  - Contained AI Agents, Privileged AI agents and Dormant AI agents counts
  - agent map by provider
- **Design-time:**
  - model vulnerabilities by MITRE ATLAS technique and by severity
  - model validation by OWASP LLM category
  - top threat categories
- **Runtime:** "detected and blocked" counts for prompt injection and offensive content, scoped by an "Internal Agents" selector.
- **Post runtime:** OWASP-category heatmap and the event table (AI asset, Provider, Actions).
- **Demo data** [PDF-text p15]. A plugin is missing [PDF-screen p14].

### 2.10 Monitoring (Insights > Monitor) [PDF-screen p20-p26]
- **Overview:** managed vs unmanaged split, type split, ranking, and average Quality and Safety.
- **Evaluated sessions:** sampled; per session you get traces, AI system, scores, start and end times, and tokens.
- **Session:** metric rows (metric, score, Provider = ServiceNow, Level = Span, reason) and a trace list (time, duration, spans, input/output/total tokens, quality, safety).
- **Trace:** span tree with durations; evaluation table; raw Input and Output JSON, including the system prompt and user message.
- Scores are produced by a "judge" ("judge's reasoning", p22-23). That this is an LLM-as-judge is my reading [Inference].

### 2.11 Evidence and audit
- The PDF's only "evidence" claim is the p26 narration: "the whole evidence track is going to be available in this trace and in this session details".
- Not shown: audit history, change log, export, immutability or hash.
- Records show only Created and Updated timestamps (p6), and the Details and Use-and-purpose cards are **editable (pencil icons)** (p6) [PDF-screen].

---

## 3. UI paths and roles

| Purpose | UI path (as shown) | Page |
|---|---|---|
| Landing summary | Home | p2 |
| All assets / per-class lists | Inventory > All, AI systems, AI models, MCP servers, Datasets, … | p3-p4 |
| Register an asset manually | Inventory > [Add AI asset] (form not shown) | p3 |
| Asset record | Inventory > AI systems > *asset* > Overview, Details, Lifecycle, Risk & compliance, Monitor, … | p5-p10 |
| Turn on monitoring for an asset | Asset > [Move to Managed] | p5, p10 |
| Recommendations and work | Activity Center (via "See all Recommendations (n) in Activity Center") | p5, p12 |
| Security posture | Govern > Security > Overview, Design-time, Runtime, Post runtime | p12-p16 |
| Risk and compliance | Govern > Risk & compliance (not opened) | p11 |
| Run evaluations | Insights > Monitor > Overview, Evaluated sessions > Session > Trace | p20-p26 |
| Value and engagement | Insights > Value, Engagement (not opened) | p19 |
| Connectors | Settings > Integrations > Connectors > Available (6) / Established (2) | p28-p29 |
| Trace ingestion (?) | Settings > Integrations > **Traces** (not opened) | p28 |
| Users and roles | Settings > Users and roles (not opened) | p2 |

**Roles needed: not stated in the PDF.**
- Hints only: the "Users and roles" item (p2), and the narration "You're not going to see all those connectors available" (p29).
- Participant accounts probably see less than the presenter [Inference].

---

## 4. Data shown per asset [PDF-screen p3-p6]

- **List row:** Name, Asset type, State, Status, Managed status, Managed by, Risk classification, Updated.
- **Details card:** Name, Description, Managed status, Asset type, **Provider**, **Vendor**, Department, **Managed by** (an owner, not an acting identity), State, Status, Risk classification, **Created**, **Updated**.
- **Use and purpose** ("What is the outcome and objective of this asset to be useful"), with the example's values:
  - Intended outcome of the AI system: *Insight Generation*
  - Level of human involvement: *Shared Control*
  - Interaction type with end users: *Notifications & Prompts*
  - System autonomy level: *Assistive (AI suggests)*
  - Type of output produced: *Insight & Summaries*
  - Area where the AI system is used: *Internal Operations*
  - People affected by the AI system: blank
- **Asset relationship map:** typed edges to AI model, Tool, AI prompt, AI dataset and AI System ("uses", "evaluated using", "depends on").
- **Attachments:** files up to 10 MB.
- **Overview:** Needs attention (recommendations with priority and category) and Key details (cut off).
- **Monitor** (Managed assets only): dashboard, not shown in the PDF.

---

## 5. What AICT can manage vs only observe

**Manage. The PDF shows these controls but rarely uses them:**
- Asset record:
  - Move to Managed
  - edit Details and Use-and-purpose
  - set State, Status and Risk (via the fields and filters)
  - attachments
  - Add AI asset
  - the Action ▾ menu
- Recommendations: Open, View details, "Automate with Otto"; Assigned / Unassigned.
- Configure the post-runtime view.
- Install a plugin.
- Set up and edit connectors.

**Observe:**
- dashboards
- security heatmaps and counters
- evaluated sessions, traces and judge scores
- the agent map

**Not shown at all:**
- Any action that changes an external (AWS) agent's runtime: stop, contain, change permissions, block a call.
- "Contained AI Agents: 0" (p12) and "detected and blocked" (p15) imply containment and blocking exist for some agent population, but no mechanism is shown [Inference].
- For AWS-discovered agents, "manage" appears to mean managing the governance record, not the runtime [Inference]. Module 11 calls the connector role read-only [Team-notes].

---

## 6. The six auditor questions: what AICT could and couldn't contribute

| Q | AICT could contribute | Can't, or not shown |
|---|---|---|
| **WHO** acted (identity, on whose behalf, scope) | • Asset identity: name, Provider, Vendor, versioned AI system name (p6, p21). <br>• Owner = "Managed by" (p6). <br>• "Privileged AI agents (elevated access permissions)" count (p12). <br>• Agent map by provider (p12). | • No per-call acting principal, end user or scope field in the session or trace views (p22-26). <br>• "Managed by" is an owner, not an actor. <br>• Module 11's single gateway IAM principal [Team-notes] is not addressed by the PDF. |
| **WHAT** it touched (models, tools, resources) | • Declared relationships: AI model, Tool, AI prompt, AI dataset, AI System (p6). <br>• Trace span tree shows the model-call span and a `tool_calls` field (p25). <br>• MCP servers as an inventory class (p3). | • In the only example, `tool_calls` is empty, so tool visibility is **asserted (p26) but not shown**. <br>• The relationship map is registered or declared, not runtime evidence [Inference]. <br>• Span names show the client class (`ChatOpenAI.chat`), not which backend model or alias served the call [Inference]. <br>• Resources touched (e.g. TMF639 objects) do not appear. <br>• **The gateway and ledger stay the source for WHAT.** |
| **AUTHORIZED** (policy, version, where evaluated) | • Only indirect: Govern > Risk & compliance, the Rules and templates and Playbooks nav, the posture "Compliance" bar (p2, p11). <br>• Runtime "detected and blocked" counters (p15, demo data). | **Not shown:** any policy decision, policy version or evaluation point. The Cedar PDP log remains the only answer. Risk: a judge might confuse AICT's "blocked" counters with MoDaaS guardrails or Cedar [Inference]. |
| **APPROVED** (attestation for every asset in the chain) | • Per-asset Status (In review → Ready for deployment → Approved / Rejected), State lifecycle, Lifecycle tab, owner, Created / Updated, attachments (p3-p6). <br>• Could act as a **second attestation surface**: put each chain asset (agent, model, MCP server) in AICT as Managed and Approved, with the threshold doc attached [Inference]. | • Approver, time and history are not shown (Lifecycle tab unopened). <br>• "Approved" is a field a human sets in the ServiceNow UI. It is not bound to a deployed version or config, and is independent of MoDaaS approval annotations, so the two can diverge (e.g. a model swap) [Inference]. <br>• Discovered agents arrive with blank Status (p4). |
| **INTEGRITY** (records not altered) | • A copy held by a third party (ServiceNow) of sessions, traces and asset records gives independent custody to cross-check the ledger against [Inference]. | • No immutability, audit trail, export or hash is shown. Records are editable (p6). <br>• Visible data inconsistencies (§9) argue against AICT numbers being the figure of record [Inference]. <br>• Whether the instance keeps field history for these records must be checked on the instance. The PDF says nothing. |
| **RECONSTRUCT** (replay end to end with timestamps) | • Session → traces → spans with time window, durations, token counts and full input/output content. <br>• Previous / Next trace navigation (p21-26). | • Sessions are **sampled** (p21). <br>• Only **Managed** and **Agentic AI** assets are evaluated (p20). <br>• Timestamps are whole seconds and spans are 1000 ms (p22, p25). <br>• The list says 09:23 while the detail says 16:23 for the same session (p21 vs p22). <br>• No MoDaaS run_id, CID or trace_id is visible; the grouping key shown is `traceloop_association_properties_session_id` (p26). <br>• How AgentCore traces would get in is not shown (Traces tab unopened, p28). |

**Evidence Pack implication [Inference]:**
- Judges answer "from your Evidence Pack alone" [Team-notes].
- So anything AICT contributes must be **captured into the pack**: screenshots or exports of the asset record, its approval status, and session or trace pages for a named run.
- Each capture needs a cross-reference key (e.g. a session id mapped to the run's CID).

---

## 7. Comparison with the Module 11 claims

| Module 11 claim | What the PDF says | Verdict |
|---|---|---|
| AICT discovers AgentCore runtimes, Bedrock agents and SageMaker models via the connector role `SgcAictReadOnlyAccessRole` | • An "AI Connector for Amazon" exists. <br>• "discover AI assets … appear in your AI asset inventory" (p29). <br>• AWS agents were "discovered before" (p4). <br>• The Agent map shows "Amazon 16 agents" (p12). <br>• It never names AgentCore, Bedrock agents, SageMaker or the role. <br>• The connector setup page is not shown (p29). | **Consistent; specifics unconfirmed.** |
| Who configures the connector | • PDF: "what you need to do first is set up the integration … It's where you will set up the connector" (p27, p29), i.e. the participant appears to set it up. <br>• Module 11: "A facilitator enters the redacted values below into the ServiceNow AI Service Graph Connector for Amazon form. Participants do not enter these values." and "You do not need a ServiceNow instance for the participant steps" [M11 l.17-18, 110-111]. <br>• In the team account, `WSOpsRole` already deployed the stacks [Team-notes]. <br>• The names also differ: the PDF tile is "AI Connector for Amazon" (p29); Module 11 says "AI Service Graph Connector for Amazon". | **Discrepancy.** |
| Module 11's description of this PDF: "The AICT console: discovered assets, lifecycle, reviews" [M11 l.35] | • Discovered assets: shown (p4). <br>• Lifecycle and reviews appear **only as State and Status field values** (p3-p6). <br>• The Lifecycle and Risk & compliance tabs are never opened. <br>• No review or approval workflow, approver or history is shown. | **Thin.** Lifecycle and reviews appear only as State and Status fields; the workflow tabs are never opened. |
| Module 11 "5. The human-loop rail": an escalate choice "should open a ticket a human already works … Rail 1 in the ServiceNow integration creates an incident from the evidence chain … a stretch goal … `escalate-to-incident.py` … is the starting point" [M11 l.160-166] | • The PDF has **nothing** on incidents, escalation, APIs or where such an incident would appear in AICT. <br>• The only work-item surfaces are the unopened ones listed in §8. | **Not covered by the PDF.** |
| Does NOT discover Kubernetes-pod agents | • Silent on Kubernetes. <br>• Manual "Add AI asset" exists (p3), so pod agents could probably be registered by hand [Inference]. <br>• The Traces tab (p28) and the OTel/Traceloop trace (p26) hint at a trace-ingestion path that is independent of discovery [Inference, unverified]. | **Silent; consistent.** |
| Does NOT discover MCP servers (manual or MCP Catalog) | • An Inventory "MCP servers" tab and an "MCP Digital Asset" class exist, plus Add AI asset (p3). <br>• No discovery of MCP servers is shown. <br>• No "MCP Catalog" is mentioned. | **Silent; consistent (manual registration surface visible).** |
| Does NOT see MoDaaS guardrails | • Silent on MoDaaS. <br>• AICT has its **own** runtime counters ("prompt injection / offensive content detected and blocked", "Internal Agents", demo data; p15) and "security guardrails" in model validation (p13). <br>• These are ServiceNow-side signals, not MoDaaS verdicts [Inference]. | **Silent; consistent.** Watch for conflation. |
| Does NOT know which model alias served a call. Module 11's exact words: "Which ModelConfig served a call (all calls arrive under the gateway's single IAM principal)" [M11 l.131-132] | • Silent. <br>• Traces show client-side span names and token counts only (p22, p25). <br>• The AICT stack's Bedrock trail and invocation log group [Team-notes] would carry the gateway's identity, which fits the Module 11 claim [Inference]. | **Silent; consistent.** |
| (Not in Module 11) PDF-stated preconditions | • "Move to Managed" is needed for the Monitor dashboard (p10). <br>• "Only managed assets are evaluated." / "Only Agentic AI assets are evaluated." (p20) <br>• Sessions are sampled (p21). <br>• The security plugin is not installed (p14). <br>• Runtime data is "demo data" (p15). <br>• Participants won't see all connectors (p29). | **Additions Module 11 doesn't mention.** |
| (Not in Module 11) Runs of AWS agents appear as sessions | • Narration claims it (p21-22). <br>• Not demonstrated: no AWS agent among the visible sessions; the trace is a LangGraph + ChatOpenAI app (p21, p25-26). | **Asserted, not shown.** |

---

## 8. Relevance for Level 2 / 3 judging, and the "escalate to a human" rail

**Level 2: "ServiceNow Control Tower adds additional observability" [Team-notes]**
- The PDF itself says AICT "will be part of your hackathon experience" (p2). It does not say AICT is required for judging.
- A credible minimum, given the gates on p10 and p20 [Inference]:
  1. The team's agents are visible in Inventory (discovered via the Amazon connector, or added manually).
  2. They are **moved to Managed**.
  3. Use & purpose is filled in. *Level of human involvement* and *System autonomy level* (p6) are a natural place to declare the gather-evidence / escalate behaviour.
  4. A risk classification is set.
  5. The relationship map links the model and the (manually registered) MCP tool servers.
  6. register.yaml and the threshold doc are attached (p6 allows PDF and XLSX up to 10 MB).
  7. Then, if trace ingestion works for AgentCore, show evaluated sessions for a named run.
- Everything shown must be captured into the Evidence Pack.

**Level 3: "richer evidence, a stronger chain of evidence and additional proof" [Team-notes]**
- AICT can be an independently held second record [Inference]:
  - asset approval status alongside approvals.json
  - judge scores (Answer Relevancy, Secrets Detection, Quality and Safety) as additional proof
  - span content alongside OTel traces
- This is only a "chain" if the IDs join. An open idea: set the OTel/Traceloop association `session_id` to the run's CID so that the AICT session and the MoDaaS run_id match. This is unverified and depends on how traces reach AICT [Inference].
- Caveats to state honestly in the pack: sampling, Managed and Agentic only, and demo-data inconsistencies.

**Escalate-to-human rail (escalate disposition → ServiceNow incident)**
- **The PDF shows no incident creation, no escalation, no API and no Playbook content.**
- What exists, all unopened: Pending work items (p2); Activity Center recommendations with Open / Assigned to you / Unassigned (p5); the "Actions" column on security events (p16); Configure (p16); Settings > Playbooks and Rules and templates (p2); "Automate with Otto" (p2).
- The demo instance does hold incident and CMDB context: the Incident Summarization Agent "Gathers incident context from ServiceNow CMDB" (p6).
- So the rail is a **ServiceNow-platform action** (an incident record), not an AICT feature. The PDF gives no table, field or API schema [Inference].
- Module 11 makes this a **stretch goal**: "Rail 1 in the ServiceNow integration creates an incident from the evidence chain"; `escalate-to-incident.py` "is the starting point" [M11 l.160-166].
- The team's notes add that the script is "a starting point, not verified table/field schema" and warn "Do not invent an 'AICT evidence endpoint'" [Team-notes l.150].
- Nothing in this PDF corroborates the incident path.
- Fit with the judging rules [Inference]:
  - "a human actually answering an alert" is not scored, but "the alert, its named recipient and the silence must still be recorded" [Team-notes].
  - An incident assigned to a named group or user, left unanswered, is exactly that record.
  - Its incident number should be written into the ledger next to the run's CID.
- AI assets are "Digital Asset" records (p3), so linking the incident to the agent's asset record might be possible. This is not shown and must be verified on the instance.

---

## 9. Data-quality observations (why AICT numbers can't be the figure of record) [Inference unless marked]

- Consistent: the Sep 2026 heatmap column sums to **405**, which matches "405 results" (p16).
- Inconsistent:
  - "Models with vulnerabilities: **107**" vs "Vulnerabilities: **32**" (p13).
  - The same session shows **09:23:38** in the list (p21) and **16:23:38** in the detail (p22). The 7 h offset looks like a UTC vs local time-zone mismatch.
  - Session Quality is **98%** while its only trace shows Quality **N/A**, and the only quality metric (Answer Relevancy) is 100% (p22).
  - Session #S00000261 has **no AI system** and a blank Safety score (p21).
  - The trace content (a payroll / direct-deposit chat, generic system prompt) does not match the session's AI system "Action Item Extractor 1.0" (p21 vs p25-26). This is synthetic demo data.
- The runtime security counters are explicitly "demo data" [PDF-text p15].
- Timestamps are second-granular and every span is exactly 1000 ms (p22, p25).
- Raw PII (a bank account number and a routing number) is stored and displayed in the trace, and Secrets Detection = 100% (p22, p25-26).

---

## 10. Open questions (for organisers or for verification on the instance)

1. Which ServiceNow instance will the team use: `platformdemoh8` (whose connections are named "Test Hackathon 26" and "TMF 2026 Hackathon", p28) or a separate sandbox (Level 3 says "ServiceNow Sandbox")? Which account and role will participants get?
2. Is the team's Workshop Studio AWS account already connected (facilitator stack `a-03-servicenow-aict` [Team-notes]), and to which instance? Do the team's own runtimes appear in Inventory? (The p4 rows predate the team's account.)
3. Can participants "Move to Managed", edit Use & purpose and Status, attach files, or "Add AI asset" (MCP servers, a pod agent)? Roles are not stated.
4. What is under Settings > Integrations > **Traces** (p28)? Can AgentCore or OTel traces from the team's agents be ingested? Could the session key be set to the run CID?
5. What do the **Lifecycle** and **Risk & compliance** tabs record: approver, timestamps, history?
6. Is there any export or API for asset, session and trace records, so they can be captured into the Evidence Pack?
7. For the escalate rail: does the participant role allow incident creation (UI or API) on the chosen instance? Is there a field linking an incident to an AI asset record?
8. What is the session sample rate, and can it be set to 100% for the assessed runs?
9. The 12-page "Creating/Verifying Amazon Connection" PDF [Team-notes l.153] probably covers the connector setup this PDF skips (p29). Read it next.

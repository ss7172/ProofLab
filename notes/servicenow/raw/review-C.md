# Review C: independent spot-check of C1 (pp.1–43) and C2 (pp.44–86)

Source: `create-and-manage-ai-agents-in-ai-agent-studio.pdf` (86 pp., react-pdf, created 2026-09-30).
Reviewer: independent and read-only. I made no edits to C1 or C2, no AWS calls, and no git operations.

**Method**
- Captions: I ran `pdftotext`. The text layer contains only the step titles and captions, and they match what both notes quote.
- Low-resolution pass: I viewed all 86 pages at page-render resolution, about one third of native.
- Native-resolution pass: for the claims below, I extracted the native 1920×963 screenshots of 29 pages with `pdfimages`, cropped them at 1:1 and read them. The pages were 2, 3, 5, 8, 13, 14, 15, 16, 22, 24, 25, 29, 31, 32, 34, 37, 39, 43, 44, 46, 47, 59, 68, 69, 75, 78, 82, 84 and 85 (p75 in full).
- The temporary images were deleted afterwards.
- Every other page cited here (including p17, p23, p45, p52, p62–63, p73 and p79–80) was checked at page-render resolution only.
- One possible extra caption mismatch, unverified at native resolution: at page-render, the activation toggle on p62 ("Activate AI Agent") already looks On before the click. C2 does not flag this.

## Verdicts

- **C1: accurate.**
  - Every screenshot claim I checked is CONFIRMED.
  - All five caption-vs-screenshot contradictions hold.
  - 0 WRONG; 2 minor OVERSTATED.
- **C2: accurate.**
  - Every checked claim is CONFIRMED, including the three Thought texts (verbatim) and all latency figures.
  - 0 WRONG; 3 minor OVERSTATED. All three are generalisations from one run, an empty column, or the input form.

## C1 checks

| # | Claim | Verdict | Page evidence (native-res unless noted) | Correction / note |
|---|---|---|---|---|
| 1 | Current app is "AI Service Graph Connector for Amazon" | CONFIRMED | p14 and p16 (also p15): "Read-only: This record is in the AI Agents for Telecommunications, Media and Technology application, but AI Service Graph Connector for Amazon is the current application." There is an "Edit in original scope" button. | none |
| 2 | Two import-set tables "SG-AWS AgentCore AI Age…" [p3, p5] | CONFIRMED on p3; OVERSTATED for p5 | p3 navigator: System Import Sets › Import Set Tables › two truncated "SG-AWS AgentCore AI Age…" rows. p5 shows only one row; the next row sits under the "Open studio features" callout. | Cite p3 for "two". |
| 3 | §0 finding 1 headline: "The demo instance has an AWS AgentCore link" | OVERSTATED (inference worded as fact) | The evidence is only an application scope name plus two truncated table names. | Reword as: the Service Graph Connector for Amazon app is installed and is the current scope, and two AgentCore-named import-set tables exist. No connection, credential, schedule or imported row is shown. C1's own body text says this, but the headline goes beyond it. |
| 4 | User access choice auto-generates an ACL | CONFIRMED (as a UI statement) | p29: "Once you save your choices, an access control list (ACL) will be automatically generated." p31 lists three options, with descriptions verbatim. p32 is saved as "Any authenticated user". | No ACL record is ever shown. The ACL is the UI's promise, not observed output. |
| 5 | "Dynamic user" vs "AI user" | CONFIRMED | p34, verbatim: Dynamic user is "This can be the sys_user of a trigger, agentic workflow, or user that passes its roles to this AI agent." AI user is "This is a type of sys_user only for agentic workflows and AI agents, with pre-defined roles." p37: the Approved role(s) list, including access_analyzer_ai_user ("…within the Agent Studio testing module"). p39: "AI user\*" is required and "Selected AI user roles" shows "—". p43: Approved role(s) is empty. | none |
| 6 | "18 agents have no ACL configured" | CONFIRMED | p2: "Action required: 18 agents have no Access Control List (ACL) configured. Configure ACLs to ensure secure and uninterrupted operation. View Documentation". | none |
| 7 | "Select unsupported LLMs"; AI Admin Center provider and AI Guardian items | CONFIRMED | p22: "Unsupported model providers … LLM providers: Select unsupported LLMs". p8: "Agentic workflows (50)", with AI Admin Center rows Manage Model Provider Workflow (4), Guardian Settings NAC (3) and Model Version Management Workflow (3); Model support is "Available" on every row. p13: Edit Model Provider Agent, Model Provider Policy Agent, Model Version Modifier Agent ("…Instance and skill lev…"), Model Provider Query and History Agent, Guardian Settings Viewer Agent NAC and Guardian Settings Modifier Agent NAC ("…including Prompt Inj…"), and Data and Policy Configuration Agent. "Showing 1-20 of 165". | No LLM provider is named anywhere. That absence is also confirmed. |
| 8 | "Allow third party to access this AI agent — Enable for external discovery…" is OFF | CONFIRMED | p22 and p24 each show an "OFF" pill and an "Off" toggle; p24 is the "Save and continue" step. p23 (page render): the label text is selected and the toggle is still Off. Also on p24: "Allow AI specialists…" is OFF and "learn from past executions" is NO. | none |
| 9 | Contradiction 1: p22–23 captions say "Enable / Confirm third-party access" | CONFIRMED | Same evidence as #8. | none |
| 10 | Contradiction 2: p43 caption mentions the "System Administrator role" | CONFIRMED, with nuance | On p43 the field is empty and the dropdown is closed. The admin entry and its warning appear one step later, on p44. | The caption runs one step early; it did not make the content up. |
| 11 | Contradiction 3: p26 caption mentions "skills and integrations" | CONFIRMED | p26 highlights the existing Flow-actions table: two inherited rows, Autonomous / false (p25). No picker appears, and the Add tool menu is never captured open. | none |
| 12 | Contradiction 4: p9 caption mentions "workflow details" | CONFIRMED | Only the list toolbar is highlighted; the list is unchanged. | none |
| 13 | Contradiction 5: p14 caption mentions "duplicating or deleting" | CONFIRMED | The p15 menu shows "Duplicate" and a greyed-out "Delete". | none |
| 14 | Tools are Flow actions, with "Execution m…" = Autonomous | CONFIRMED | p25: both rows read Autonomous / false, dated 2026-09-30. | Reading the truncated header as "Execution mode" is reasonable. |
| 15 | Agent description: "It does not require any user confirmation to use the tools." | CONFIRMED | p14 description box, carrying the "Description for LLM" tag. | none |

## C2 checks

| # | Claim | Verdict | Page evidence (native-res unless noted) | Correction / note |
|---|---|---|---|---|
| 1 | Dynamic user with Approved role(s) = **admin**, chosen right after "Grant this privilege carefully" | CONFIRMED | p44: the admin option text, verbatim, including "Grant this privilege carefully." and the HR-records sentence; agent_admin, agent_role_config_admin and agent_role_config_viewer follow. p45 (page render): "admin ×" chip. p46: Dynamic user + "admin ×", then Save and continue. | C2's [Inference] "the demo grants admin" slightly overstates this. The screens show admin as an *approved role* on a Dynamic-user identity. The PDF never shows how approved roles combine with the invoking user's roles; the FAQ "What are approved roles and what do…" stays collapsed. The least-privilege criticism still stands. |
| 2 | Trigger table has a "Run as" column | CONFIRMED | p47 columns: Name, Trigger, Table, Conditions, Run as, Channel, Status, Remove. The Triggers header carries an "Instruction for LLM" pill. p52 (page render): "No data to display", so no trigger was saved. | §4(b) cites "per-trigger Run as [p47]" as identity evidence. That is **OVERSTATED**: it is an empty column header, and no value is ever shown. |
| 3 | Version "1 - V1 (Active)" | CONFIRMED | p68: Version\* = "1 - V1 (Active)". The Task\* field carries an "Instruction for LLM" pill. | The version appears only on the test input form; the run page and decision log (p75–85) never display it. C2's inference that the version pin "gives 'what version ran'" is therefore **OVERSTATED** for the log. |
| 4 | Workspaces menu lists "AI Control Tower (Legacy)" and "AI Admin Center" | CONFIRMED | p69 menu, in order: AI Admin Center; AI Control Tower (Legacy), whose lower half is under the callout but legible; hidden rows; Asset; Automation Center; CMDB; CSM/FSM Configurable; ITOM Infra Services; Knowledge Center; Now Assist Readiness Evaluation; Process Mining; Service Operations. Rows are 32 px apart, which fits two hidden rows, as C2 infers. | none |
| 5 | Structure of the "AI agent decision logs" | CONFIRMED | **p75:** rows run Access verification (Completed) → Test AI Agent… (AI Agent, Ongoing) → Gen AI - AIA ReAct Engine (external-link icon) → Tool - Fetch current task information. The header has a download icon. **Gen AI rows (p78, p82, p84, p85):** Latency factors, Thought, Action Reasoning, then Action ▸ 0 ▸ Name / Action Inputs / Datatypes. **Tool rows:** Latency factors, Inputs ▸, Output : null, Output Fields ▸. For Fetch, Output Fields shows "Data collection status : Pass" and Response ▸. | All five latency pairs match: 175 / 3 secs; 526 / 959 ms; 194 / 3 secs; 113 / 689 ms; 379 / 6 secs flagged "High latency". |
| 6 | Final thought reports a "stop result" | CONFIRMED verbatim | p85: "Verification returned a stop result, so no further troubleshooting or downstream work is allowed. … return the collected details and verification outcome to the orchestrator and exit." | none |
| 7 | The log shows no timestamps, run or trace ids, user, or prompt | CONFIRMED (as displayed) | I checked p75 in full (header, breadcrumb, left narration, map, log) and the log panes on p78, p82, p84 and p85. They show only durations. The only user cue is the header avatar "SD". The task text is not echoed. | Scope: the Gen AI external links and the download export are never opened, so their contents are unknown. C2 states this correctly. |
| 8 | "Access verification" is the first row of every run | **OVERSTATED** | pp.75–85 show a single run. | Should read "first row of the one run shown". |
| 9 | No incident creation, no human approval, no AWS / MCP / A2A / external LLM | CONFIRMED for pp.44–86 | INC0010190 is only typed in as test input (p73). No approval step appears. The model is shown only as "Gen AI - AIA ReAct Engine". | This is not true of the whole PDF: AWS appears on p3, p5 and p14–16 (C1's range). C2 correctly limits the statement to pp.44–86; keep that scope when quoting it. |
| 10 | "AICT Assistant / llm" on p59 is a chat assistant, not a tool | CONFIRMED | p59: "These chat assistants were created in Assistant Designer." The selected option is "AICT Assistant", subtitle "llm". | none |

## Inference presented as fact

- C1 §0 finding 1 headline (C1 #3).
- C1 §2: "Shipped agents are read-only outside their app scope." Only one read-only record is observed (p14–16). The general rule comes from platform knowledge; the PDF does not show it.
- C2 §2 and §4(b):
  - "first row of every run log" (only one run is shown)
  - "per-trigger Run as" offered as identity evidence (the column is empty)
  - the version pin offered as "what version ran" (it appears on the input form only)
- Everything else that is inference is labelled [INF] or [Inference] in both notes.

## Missed content worth adding

1. **[INF] Where the test agent lives.**
   - The copy was made while "AI Service Graph Connector for Amazon" was the current application (p14–16), and the read-only banner is gone from p17 onward.
   - Under normal ServiceNow scope rules, "Test AI Agent for the DTW Hackathon" therefore most likely sits in that app's scope.
   - This matters for finding or exporting the agent. Neither note says it.
2. **The reason the run halted rests only on the LLM's own Thought.**
   - The Verify tool row shows "Output : null" with Output Fields collapsed (p84, p85), so the "stop result" value is never visible.
   - The agent's final answer to the user is never displayed either; the left pane shows step narration only (p80).
   - For an evidence chain, this is the model's own account, not a recorded tool value.
3. **The run page never shows the identity the agent ran as, or which approved role was in effect.**
   - "Access verification" is a bare "Completed" (p75–85).
   - Who ran as whom is visible only in configuration (p46), never as run evidence.
4. **The demo's configuration is permissive overall.** Each item is confirmed above; each note mentions some of them, but neither states the combination:
   - "Any authenticated user" may access the agent (p32)
   - Dynamic user with Approved role(s) = admin (p46)
   - both tools set to Autonomous (p25)
   - the agent's description says it "does not require any user confirmation" (p14)
   - the agent is activated (p63)

## Bottom line for the team

- Both notes are reliable for page-level facts.
- Quote C1 finding 1 as "connector app present", not as a working AgentCore link.
- ServiceNow's on-screen run evidence consists of:
  - the access-check status
  - the model's step-by-step reasoning (Thought / Action Reasoning)
  - tool name, status and durations
  - collapsed inputs and outputs
- It does not show ids, timestamps, the run-as identity, the version, or the final answer.

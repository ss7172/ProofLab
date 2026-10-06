# NVIDIA talk: "Agentic & Open Agent Safety Platform" (TM Forum Hackathon). Summary and guardrail catalogue

**Source:** NVIDIA, *NVIDIA Agentic & Open Agent Safety Platform, TM Forum Hackathon*, "Customer Deck", "September 2026".
- 15 slide pages, exported from PowerPoint; the PDF carries no notes pages.
- Saved copy: `hackathon-context/sources/NVIDIA_Open_Agent_Safety_Platform.pdf`. It is byte-identical to `~/Downloads/NVIDIA Open Agent Safety Platform.pdf` (SHA-256 `1a7bac48…2c196cadf20f`).
- Full text, link targets and per-page visual notes: `hackathon-context/sources/NVIDIA_Open_Agent_Safety_Platform.txt`.

**Written:** 2026-10-05, from the full extracted text and a visual read of all 15 pages.

**How to read this file:**
- `pN` means PDF page N. Pages 10–14 also print that number on the slide.
- Text in "double quotes" is verbatim from the deck, with two exceptions:
  - where a slide stacks several words as one label, we join them with " / " (for example "Prompt / Tools / Data / Model");
  - in §8, quotes from our own docs are marked with the file they come from.
- §1, §2, §3, §5 and §6 report only what the talk says or shows.
- §4, §7 and §8 are ours, as is anything marked **[ours]**.
- "Not stated" means the deck says nothing on that point.

---

## 1. The talk in brief

The deck has two parts, and no diagram joins them.

1. **The NVIDIA AI Safety Suite (p2–p8):** "Open NeMo libraries built on open Nemotron models which are trained on open Nemotron datasets" (p4).
   - **Two challenges, each answered by NeMo libraries (p3):**
     - "Data Security Exposure": NeMo Safe Synthesizer and NeMo Anonymizer.
     - "Model Security Risks": NeMo Guardrails, backed by "Nemotron Safety Models", and NeMo Auditor.
   - **NeMo Guardrails** places rails at five stages: Input, Retrieval, Dialog, Execution and Output (p5).
   - **Four Nemotron safety-model families** are "Supported in NeMo Guardrails": content safety, PII, topic control and jailbreak detection. Each has one headline figure (p7).
   - **NeMo Auditor** scans "LLMs and LLM-containing systems" across "160+ attack categories". It is paired with the open-source garak (p4, p8).
2. **The NVIDIA Open Agent Safety Platform (p9–p14):** "Traditional Sandboxes Not Built for Long-Running Agents" (p9).
   - **NVIDIA OpenShell (p10):** the agent harness runs in an "AGENT SANDBOX". Below it are a "PRIVILEGED CONTROL LAYER" (filesystem and network access) and an "In-Silicon Enforcement Boundary".
   - **OpenShell's parts:** a Gateway, a Supervisor and a Policy Prover. The deck calls this an "Open reference design" (p11).
   - **NVIDIA Sentry** "adds an out-of-band watchdog that continuously monitors and can stop agent behavior in milliseconds". It is drawn joined to BlueField-4 chips (p12).
   - **The rest:** an ecosystem logo wall (p13) and links (p14).

---

## 2. Page-by-page summary

**p1. Title.** "NVIDIA Agentic & Open Agent Safety Platform", "TM Forum Hackathon"; "Customer Deck", "September 2026". There is no other content.

**p2. "NVIDIA NeMo Libraries for Agentic AI Safety".** Subtitle: "Make agentic AI production-ready with integrated data privacy and model security". (Sketch: §5.1; catalogue G1, P1, P2, A1, L1–L6.)
- **Layout:** a diagram places ten NeMo libraries between "Nemotron" (left) and "Specialized AI Agents" (right). Both are connected to an "Enterprise AI System" (top).
- **The libraries, each with a verb:**
  - Agent Toolkit (INSTRUMENT) and Retriever (LEARN)
  - Curator (PROCESS) and Data Designer (GENERATE)
  - Safe Synthesizer (SYNTHESIZE) and Anonymizer (DETECT)
  - Customizer, RL (IMPROVE) and Evaluator (EVALUATE)
  - Guardrails (GUARDRAIL) and Auditor (AUDIT)
- **Highlighted:** four are outlined in yellow: Safe Synthesizer, Anonymizer, Guardrails and Auditor.

**p3. "Primary Agentic AI Safety Challenges".** Subtitle: "Data leaks and bypassed protections expose sensitive information and enable model exploitation". (Sketch: §5.2; catalogue K1, K2.)
- **Challenge 1, "Data Security Exposure":** "52% of data breaches involve some form of customer PII." (cited "IBM Report"). Under it: NeMo Safe Synthesizer and NeMo Anonymizer.
- **Challenge 2, "Model Security Risks":** "97% of companies with AI breaches had no AI access controls in place." (cited "IBM Report"). Under it: NeMo Guardrails, with an arrow down to "Nemotron Safety Models", and NeMo Auditor.

**p4. "Introducing the NVIDIA AI Safety Suite".** Subtitle: "Open NeMo libraries built on open Nemotron models which are trained on open Nemotron datasets". Three lists (catalogue G1, P1, P2, A1, M1–M7, D1–D5):
- **"Open Libraries":** NeMo Safe Synthesizer; NeMo Anonymizer; NeMo Guardrails; NeMo Auditor / Garak.
- **"Open Models":**
  - Nemotron 3.5 Content Safety
  - Nemotron 3 Content Safety
  - Llama Nemotron Content Safety
  - Nemotron Content Safety Reasoning
  - Llama Nemotron Topic Control
  - Nemotron Jailbreak Detection
  - GLiNER PII
- **"Open Datasets":** Nemotron Content Safety; Nemotron Content Safety Reasoning; Nemotron Content Safety Audio; Nemotron AIQ Agentic Safety; Nemotron PII.

**p5. "NVIDIA NeMo Guardrails".** Subtitle: "Build enterprise-grade AI agents with robust security and control – intercept policy violations with minimal performance impact". (Sketch: §5.3; catalogue G1–G10.)
- **Key features:**
  - Customizable use cases: "PII detection, content safety, jailbreak protection, topic control, RAG enforcement, etc."
  - Performance: "Parallel execution of multiple guardrails without performance overhead."
  - Deployment: "Efficiently orchestrate and deploy anywhere."
- **A staircase of five stages, each with its rails:**
  - Input: Content Safety, Jailbreak Protection, Topic Control, PII Detection, Custom Rails
  - Retrieval: PII Detection, Knowledge Base/RAG, Custom Rails
  - Dialog: Topic Control, Custom Rails
  - Execution: Agentic Security, Custom Rails
  - Output: Content Safety, PII Detection, Knowledge Base/RAG, Custom Rails
- **Link:** "Learn more about NeMo Guardrails on the product page." (linked).

**p6. "NeMo Guardrails-Off Vs. Guardrails-On" (Example).** One prompt asks for investment advice. (Catalogue G11.)
- **Guardrails off:** the LLM answers with market commentary and "a mix of 60% stocks and 40% bonds".
- **Guardrails on:** it replies "I cannot provide investment advice. I can help you with account information and banking services.", and a label reads "Identified as category Financial Advice, Investments".
- The slide does not name the rail or model.

**p7. "Open NVIDIA Nemotron Safety Models".** Subtitle: "Advanced GPU-accelerated multilingual, multimodal models with reasoning for a variety of use cases". Four families, "Supported in NeMo Guardrails", each with a figure (catalogue G2–G5, M1–M7):

| Family | What it does | Figure |
|---|---|---|
| Content Safety | "Blocks Harmful Content" | 85% harmful-content classification accuracy (multilingual/multimodal) |
| PII | "Detects/Classifies PII and PHI" | 56% higher F1 score; 28% higher recall |
| Topic Control | "Enforces Relevant Dialogue" | 93% on-topic average F1 |
| Jailbreak Detection | "Detects Adversarial or Jailbreak Prompts" | 96% detection accuracy, average F1 |

**p8. "NVIDIA NeMo Auditor".** Subtitle: "Security and vulnerability scanning to protect against attacks on LLMs and LLM-containing systems". (Catalogue A1–A9.)
- **Benefits:** "160+ attack categories using adaptive and static probing techniques"; "Flexible APIs with local and cloud deployment support".
- **Probe table:** seven example probe types: DAN, Exploitation, Grandma, Leak Replay, Malware Gen, Web Injection and Package Hallucination.
- **"A Typical Auditor Workflow":** create an audit target for a base model; create an audit configuration; run an audit job; view the audit results.
- **Footer:** "Check out the open-source library: github.com/NVIDIA/garak".

**p9. "Traditional Sandboxes Not Built for Long-Running Agents".** Subtitle: "Long-running AI agents can combine tools, credentials and network access in ways existing controls were not designed to govern." (Sketch: §5.4; catalogue K3–K9.) A diagram drawn in red:
- **The set-up:** "AI Models" connect to an "Agent Harness" that "Connects Decisions to Tools" ("E.g. Claude, Codex, Hermes, etc."). It sits on a "Standard Operating System", a "Runtime Without Agent-Specific Controls".
- **Ambiguous Instructions:** these "Can lead an agent to take actions outside its approved scope".
- **Unapproved External Access:** this "Can let agents send data outside approved boundaries".
- **Three marked failures:** "No complete record of agent actions"; "Sensitive data and credentials can reach unapproved destinations"; "Boundary between agents is unclear".

**p10. "NVIDIA OpenShell Enforces Runtime Boundaries for AI Agents".** Subtitle: "Deterministic infrastructure enforces policy, traces actions -- with hard boundaries in silicon." (Sketch: §5.4; catalogue R1–R7, R11, R12.) p9's picture is redrawn in green:
- **Layers:** the harness sits in an "AGENT SANDBOX". Below it is a "PRIVILEGED CONTROL LAYER" ("OpenShell Control Layer": "Filesystem Access", "Network Access"), and below that an "In-Silicon Enforcement Boundary".
- **Padlocks:** one guards the link to "AI Models", and one guards the outbound link ("Data Stays in Your Secure Boundary").
- **Three properties:** "All agent actions are monitored"; "Agent cannot reach or modify the controls"; "Each agent runs under an explicit policy".

**p11. "NVIDIA Open Agent Safety Platform" (OpenShell).** Subtitle: "Open reference design includes NVIDIA OpenShell software, a secure runtime boundary that traces all actions and enforces policy as agents run." (Sketch: §5.5; catalogue R1, R8–R10, R13, H1–H3.)
- **The boundary box:** "Secure Runtime Boundary", "Governs and Mediates All Actions, Enforces Policy at Runtime". Inside, NVIDIA OpenShell has a Gateway, a Supervisor and a Policy Prover, plus an Agent Sandbox that holds the Agent Harness.
- **Hardware:** it is drawn joined to a "Vera CPU" on a "Vera CPU Tray".
- **Channels:** from chips labelled "CX-9", an arrow carries "Prompt / Tools / Data / Model" to four boxes with those names.

**p12. "NVIDIA Open Agent Safety Platform" (Sentry).** Subtitle: "NVIDIA Sentry adds an out-of-band watchdog that continuously monitors and can stop agent behavior in milliseconds." (Sketch: §5.5; catalogue S1–S8, H4.) This is p11's picture with two changes:
- **New chip label:** the chips are relabelled "BlueField-4".
- **New box:** "In-Silicon Out-of-Band Monitor", "Agent Reasoning Inspection and Tamper-Proof Telemetry", holding NVIDIA Sentry:
  - "Hardware-Based Enforcement"
  - "Continuous Agent Monitoring and Threat Detection"
  - "Trusted Telemetry and Detection Pipeline"
  - "Millisecond-Scale Containment and Quarantine"
- **The arrow into Sentry** carries "Prompt / Tools / Data / Model / Policies".

**p13. "Broad Ecosystem Building Safer AI with NVIDIA OpenShell".** A wall of 107 logos, transcribed in the `.txt`.
- It includes Anthropic, Accenture, ServiceNow, Microsoft, Oracle, IBM, Cisco, CrowdStrike, Palo Alto Networks, Hugging Face and LangChain.
- It has no AWS, Amazon or Google logo.

**p14. "NVIDIA Open Agent Safety Platform" (links).**
- Under "NVIDIA OpenShell": OpenShell Page (nvidia.com/en-us/ai/openshell/) and OpenShell GitHub (github.com/NVIDIA/openshell).
- Under "NVIDIA Sentry": Open Agent Safety Platform Page (nvidia.com/en-us/solutions/ai/agent-safety/).

**p15. Closing slide.** The NVIDIA logo; no text.

---

## 3. Catalogue: every guardrail and safety concept, component and recommendation in the talk

**This section contains only the talk's claims and depictions. The quotes are verbatim, and no opinions are added.**

Columns:
- **What it does:** the talk's own words.
- **Where:** the brief's stage taxonomy (input / dialog / retrieval / tool-execution / output / handoff / memory / runtime / evaluation / red-teaming / monitoring).
  - It is filled in only where the deck places the item.
  - The deck names stages only on p5. We file its "Execution" stage under tool-execution and keep the deck's word in brackets.
- **Needs / paired with:** what the deck draws or lists next to the item: "Supported in NeMo Guardrails", an arrow, or a containing box. These are pairings, not stated hard dependencies.

### 3.1 NeMo Guardrails: the library, its rails and its claims

| ID | Name | What it does (talk's words) | Where | Needs / paired with | Pages |
|---|---|---|---|---|---|
| G1 | **NeMo Guardrails** (library) | "Build enterprise-grade AI agents with robust security and control – intercept policy violations with minimal performance impact" (p5). Lifecycle verb "GUARDRAIL" (p2). One of two answers to "Model Security Risks" (p3) | input, retrieval, dialog, tool-execution ["Execution"], output: the five stages on p5 | "Nemotron Safety Models": an arrow from NeMo Guardrails (p3); four model families "Supported in NeMo Guardrails" (p7). One of the "Open Libraries" (p4). Product page: developer.nvidia.com/nemo-guardrails (p5 link) | p2–p7 |
| G2 | **Content Safety** rail | Use case "content safety" (p5). p7's Content Safety family "Blocks Harmful Content", with "85% Harmful Content Classification Accuracy (Multilingual/Multimodal)" | input, output (p5) | Content-safety models M1–M4 (p4) | p4, p5, p7 |
| G3 | **Jailbreak Protection** rail (the p7 family is called "Jailbreak Detection") | Use case "jailbreak protection" (p5). p7's family "Detects Adversarial or Jailbreak Prompts", with "96% Detection Accuracy Avg. F1 Score" | input (p5) | Nemotron Jailbreak Detection, M6 (p4) | p4, p5, p7 |
| G4 | **Topic Control** rail | Use case "topic control" (p5). p7's family "Enforces Relevant Dialogue", with "93% On-Topic Avg. F1 Scores" | input, dialog (p5) | Llama Nemotron Topic Control, M5 (p4) | p4, p5, p7 |
| G5 | **PII Detection** rail | Use case "PII detection" (p5). p7's PII family "Detects/Classifies PII and PHI", with "56% Higher F1 Score; 28% Higher Recall" | input, retrieval, output (p5) | GLiNER PII, M7 (p4). The Nemotron PII dataset, D5 (p4) | p4, p5, p7 |
| G6 | **Knowledge Base/RAG** rail | Use case "RAG enforcement" (p5). No further description | retrieval, output (p5) | not stated | p5 |
| G7 | **Agentic Security** rail | Listed at the Execution stage. No further description | tool-execution ["Execution"] (p5) | not stated | p5 |
| G8 | **Custom Rails** | "Customizable Use Cases", "PII detection, content safety, jailbreak protection, topic control, RAG enforcement, etc." (p5) | all five stages (p5) | not stated | p5 |
| G9 | **Parallel rails** (a performance claim) | "Performance-Optimized", "Parallel execution of multiple guardrails without performance overhead." (p5) | across the rails | not stated | p5 |
| G10 | **Deploy anywhere** (a deployment claim) | "Flexible Deployment", "Efficiently orchestrate and deploy anywhere." (p5) | no stage (deployment) | not stated | p5 |
| G11 | **Guardrails-off vs guardrails-on example** | One prompt: "Should I invest in tech stocks right now? What's your recommendation for diversifying my retirement portfolio?" OFF: market commentary and "a mix of 60% stocks and 40% bonds for moderate risk tolerance...". ON: "I cannot provide investment advice. I can help you with account information and banking services.", labelled "Identified as category Financial Advice, Investments" | not stated (the slide shows only the prompt and the final response) | not stated (no rail or model is named) | p6 |

### 3.2 Nemotron safety models

These claims apply to all seven models:
- "Open NVIDIA Nemotron Safety Models", "Advanced GPU-accelerated multilingual, multimodal models with reasoning for a variety of use cases" (p7).
- They are open models "trained on open Nemotron datasets" (p4).
- Their four families are "Supported in NeMo Guardrails" (p7).

p4 lists the models but does not group them. In the "Family" column, each model is matched to the p7 family whose name its own name contains.

| ID | Model (as named on p4) | Family, and what p7 says it does | Where | Needs / paired with | Pages |
|---|---|---|---|---|---|
| M1 | Nemotron 3.5 Content Safety | Content Safety: "Blocks Harmful Content" | where G2 runs: input, output (p5) | NeMo Guardrails (p7) | p4, p7 |
| M2 | Nemotron 3 Content Safety | Content Safety | as M1 | as M1 | p4, p7 |
| M3 | Llama Nemotron Content Safety | Content Safety | as M1 | as M1 | p4, p7 |
| M4 | Nemotron Content Safety Reasoning | Content Safety (p7's subtitle: "models with reasoning") | as M1 | as M1 | p4, p7 |
| M5 | Llama Nemotron Topic Control | Topic Control: "Enforces Relevant Dialogue" | where G4 runs: input, dialog (p5) | NeMo Guardrails (p7) | p4, p7 |
| M6 | Nemotron Jailbreak Detection | Jailbreak Detection: "Detects Adversarial or Jailbreak Prompts" | where G3 runs: input (p5) | NeMo Guardrails (p7) | p4, p7 |
| M7 | GLiNER PII | PII: "Detects/Classifies PII and PHI" | where G5 runs: input, retrieval, output (p5) | NeMo Guardrails (p7) | p4, p7 |

### 3.3 Nemotron safety datasets

| ID | Dataset (as named on p4) | What the talk says | Where | Needs / paired with | Page |
|---|---|---|---|---|---|
| D1 | Nemotron Content Safety | One of the "open Nemotron datasets" that the open Nemotron models "are trained on" (p4). Nothing more | not stated | not stated | p4 |
| D2 | Nemotron Content Safety Reasoning | as D1 | not stated | not stated | p4 |
| D3 | Nemotron Content Safety Audio | as D1 | not stated | not stated | p4 |
| D4 | Nemotron AIQ Agentic Safety | as D1 | not stated | not stated | p4 |
| D5 | Nemotron PII | as D1 | not stated | not stated | p4 |

### 3.4 Data-privacy libraries

| ID | Name | What it does (talk's words) | Where | Needs / paired with | Pages |
|---|---|---|---|---|---|
| P1 | **NeMo Safe Synthesizer** | Lifecycle verb "SYNTHESIZE" (p2). One of two answers to "Data Security Exposure": "52% of data breaches involve some form of customer PII." (p3). One of the "Open Libraries" (p4). Nothing more | not stated | not stated | p2, p3, p4 |
| P2 | **NeMo Anonymizer** | Lifecycle verb "DETECT" (p2). The other answer to "Data Security Exposure" (p3). One of the "Open Libraries" (p4). Nothing more | not stated | not stated | p2, p3, p4 |

### 3.5 Red-teaming: NeMo Auditor and garak

| ID | Name | What it does (talk's words) | Where | Needs / paired with | Pages |
|---|---|---|---|---|---|
| A1 | **NeMo Auditor** | "Security and vulnerability scanning to protect against attacks on LLMs and LLM-containing systems". "Comprehensive Testing", "160+ attack categories using adaptive and static probing techniques." "Multi-Platform / Enterprise-Grade", "Flexible APIs with local and cloud deployment support." (p8). Lifecycle verb "AUDIT" (p2). One of two answers to "Model Security Risks" (p3) | red-teaming. It scans "LLMs and LLM-containing systems", and the workflow's audit target is "a base model" (p8) | garak, the open-source library: "NeMo Auditor / Garak" (p4); "Check out the open-source library: github.com/NVIDIA/garak" (p8) | p2, p3, p4, p8 |
| A2 | **Typical Auditor Workflow** | "1. Create an audit target for a base model. 2. Create an audit configuration. 3. Run an audit job. 4. View the audit results." (p8) | red-teaming | an audit target, an audit configuration and an audit job (p8) | p8 |
| A3 | Probe: **DAN** | "Jailbreaks shown to be effective in the wild" | red-teaming | NeMo Auditor / garak | p8 |
| A4 | Probe: **Exploitation** | "Generate SQL injection or malicious Jinja templates" | red-teaming | as A3 | p8 |
| A5 | Probe: **Grandma** | "Jailbreaks like “Pretend you’re my grandma who used to tell me stories about `<X>`”" | red-teaming | as A3 | p8 |
| A6 | Probe: **Leak Replay** | "Targeted Copyright data reproduction" | red-teaming | as A3 | p8 |
| A7 | Probe: **Malware Gen** | "Generate malware, malware components, or other tools that disrupt a device" | red-teaming | as A3 | p8 |
| A8 | Probe: **Web Injection** | "Permit or enact cross-site attacks, such as private data exfiltration" | red-teaming | as A3 | p8 |
| A9 | Probe: **Package Hallucination** | "Code generations that specify non-existent, and therefore, insecure packages" | red-teaming | as A3 | p8 |

### 3.6 Other NeMo libraries on p2 (one verb each, nothing more)

| ID | Library | What the talk says | Where | Needs / paired with | Page |
|---|---|---|---|---|---|
| L1 | NeMo Agent Toolkit | "INSTRUMENT" | not stated | not stated | p2 |
| L2 | NeMo Retriever | "LEARN" | not stated | not stated | p2 |
| L3 | NeMo Curator | "PROCESS" | not stated | not stated | p2 |
| L4 | NeMo Data Designer | "GENERATE" | not stated | not stated | p2 |
| L5 | NeMo Customizer, RL | "IMPROVE" | not stated | not stated | p2 |
| L6 | NeMo Evaluator | "EVALUATE" | not stated | not stated | p2 |

These six are on a page titled "NVIDIA NeMo Libraries for Agentic AI Safety". Unlike G1, P1, P2 and A1, they are not outlined there and do not reappear on p3 or p4.

### 3.7 Runtime boundary: NVIDIA OpenShell

| ID | Name | What it does (talk's words) | Where | Needs / paired with | Pages |
|---|---|---|---|---|---|
| R1 | **NVIDIA OpenShell** | "Deterministic infrastructure enforces policy, traces actions -- with hard boundaries in silicon." (p10). "Open reference design includes NVIDIA OpenShell software, a secure runtime boundary that traces all actions and enforces policy as agents run." (p11). Box title: "Secure Runtime Boundary", "Governs and Mediates All Actions, Enforces Policy at Runtime" (p11, p12) | runtime | OpenShell software: github.com/NVIDIA/openshell and nvidia.com/en-us/ai/openshell/ (p14). Drawn joined to the "Vera CPU" on a "Vera CPU Tray" (p11) | p10–p14 |
| R2 | **Agent Sandbox** | The harness sits inside an "AGENT SANDBOX" (p10). Inside NVIDIA OpenShell, an "Agent Sandbox" contains the "Agent Harness" (p11) | runtime | part of OpenShell (p11) | p10, p11 |
| R3 | **Agent Harness** (the thing governed) | "Agent Harness", "Connects Decisions to Tools", "(E.g. Claude, Codex, Hermes, etc.)", with four unlabelled tool icons (p9, p10) | tool-execution (it "Connects Decisions to Tools") | runs inside the Agent Sandbox (p10, p11) | p9–p12 |
| R4 | **Privileged control layer** | "PRIVILEGED CONTROL LAYER", "OpenShell Control Layer", with "Filesystem Access" and "Network Access". "Agent cannot reach or modify the controls" (p10) | runtime; tool-execution (filesystem and network access) | part of OpenShell | p10 |
| R5 | **In-Silicon Enforcement Boundary** | A layer drawn beneath the control layer (p10). "hard boundaries in silicon" (p10 subtitle) | runtime | Hardware is not named on p10. p11 draws OpenShell joined to the "Vera CPU" on a "Vera CPU Tray" | p10 |
| R6 | **Model-link gate** | A padlock shield on the link between "AI Models" and the sandbox (p10) | runtime (model calls) | not stated | p10 |
| R7 | **Egress gate** | A padlock shield on the arrow from the sandbox to the outside (a globe), labelled "Data Stays in Your Secure Boundary" (p10) | runtime; tool-execution (outbound network) | not stated | p10 |
| R8 | **Gateway** | A component of NVIDIA OpenShell. Label only | runtime | part of OpenShell | p11, p12 |
| R9 | **Supervisor** | A component of NVIDIA OpenShell. Label only | runtime | part of OpenShell | p11, p12 |
| R10 | **Policy Prover** | A component of NVIDIA OpenShell. Label only | runtime | part of OpenShell | p11, p12 |
| R11 | **Explicit per-agent policy** | "Each agent runs under an explicit policy" (p10) | runtime | not stated | p10 |
| R12 | **Every action monitored and traced** | "All agent actions are monitored" (p10); "traces actions" (p10); "traces all actions" (p11) | monitoring | not stated | p10, p11 |
| R13 | **Mediated channels** | A double-headed arrow from the tray, labelled "Prompt / Tools / Data / Model", with dotted arrows to four boxes with those names (p11) | runtime (prompt, tools, data, model) | drawn from the chips labelled "CX-9" on the tray (p11) | p11 |

### 3.8 Out-of-band monitor: NVIDIA Sentry

| ID | Name | What it does (talk's words) | Where | Needs / paired with | Pages |
|---|---|---|---|---|---|
| S1 | **NVIDIA Sentry** | "NVIDIA Sentry adds an out-of-band watchdog that continuously monitors and can stop agent behavior in milliseconds." Box title: "In-Silicon Out-of-Band Monitor", "Agent Reasoning Inspection and Tamper-Proof Telemetry" (p12) | monitoring (out-of-band), with containment | Drawn joined to the "BlueField-4" chips on the Vera CPU Tray (p12). Under the "NVIDIA Sentry" heading: the Open Agent Safety Platform page, nvidia.com/en-us/solutions/ai/agent-safety/ (p14) | p12, p14 |
| S2 | **Hardware-Based Enforcement** | A box inside Sentry. Label only | monitoring | BlueField-4 (p12) | p12 |
| S3 | **Continuous Agent Monitoring and Threat Detection** | Label only | monitoring | as S1 | p12 |
| S4 | **Trusted Telemetry and Detection Pipeline** | Label only | monitoring | as S1 | p12 |
| S5 | **Millisecond-Scale Containment and Quarantine** | Label only; the subtitle adds "can stop agent behavior in milliseconds" | monitoring, with containment | as S1 | p12 |
| S6 | **Agent Reasoning Inspection** | Part of the box title | monitoring | as S1 | p12 |
| S7 | **Tamper-Proof Telemetry** | Part of the box title | monitoring | as S1 | p12 |
| S8 | **What Sentry receives** | The arrow into Sentry is labelled "Prompt / Tools / Data / Model / Policies". Dotted arrows run from Sentry to Prompt, Tools, Data and Model (p12) | monitoring | as S1 | p12 |

### 3.9 Hardware the talk names

| ID | Name | What the talk shows | Where | Pages |
|---|---|---|---|---|
| H1 | **Vera CPU** | A chip on the tray. OpenShell is joined to it by a double-headed arrow (p11, p12) | runtime | p11, p12 |
| H2 | **Vera CPU Tray** | The caption of the hardware photo (p11, p12) | runtime | p11, p12 |
| H3 | **CX-9** | A label beside the chips at the bottom of the tray. The "Prompt / Tools / Data / Model" arrow starts there (p11) | runtime | p11 |
| H4 | **BlueField-4** | Replaces the CX-9 label on p12. Sentry is joined to these chips (p12) | monitoring | p12 |

### 3.10 Risks the talk names, and what it pairs with each

p3's subtitle covers K1 and K2: "Data leaks and bypassed protections expose sensitive information and enable model exploitation".

| ID | Risk (talk's words) | What the talk pairs with it | Pages |
|---|---|---|---|
| K1 | **Data Security Exposure**: "52% of data breaches involve some form of customer PII." (cited "IBM Report") | NeMo Safe Synthesizer (P1), NeMo Anonymizer (P2) | p3 |
| K2 | **Model Security Risks**: "97% of companies with AI breaches had no AI access controls in place." (cited "IBM Report") | NeMo Guardrails (G1), with an arrow to Nemotron Safety Models; NeMo Auditor (A1) | p3 |
| K3 | "Traditional Sandboxes Not Built for Long-Running Agents": "Long-running AI agents can combine tools, credentials and network access in ways existing controls were not designed to govern." | p10 redraws p9's picture with OpenShell (R1–R12) | p9, p10 |
| K4 | **Ambiguous Instructions**: "Can lead an agent to take actions outside its approved scope" | In the same position on p10: "User Prompt" entering the AGENT SANDBOX (R2) | p9, p10 |
| K5 | **Unapproved External Access**: "Can let agents send data outside approved boundaries" | On p10 the same arrow carries a padlock, and the globe reads "Data Stays in Your Secure Boundary" (R7) | p9, p10 |
| K6 | **Standard Operating System**: "Runtime Without Agent-Specific Controls" | In the same position on p10: the PRIVILEGED CONTROL LAYER (R4) and the In-Silicon Enforcement Boundary (R5) | p9, p10 |
| K7 | "No complete record of agent actions" | Same position on p10: "All agent actions are monitored" (R12) | p9, p10 |
| K8 | "Sensitive data and credentials can reach unapproved destinations" | Same position on p10: "Agent cannot reach or modify the controls" (R4) | p9, p10 |
| K9 | "Boundary between agents is unclear" | Same position on p10: "Each agent runs under an explicit policy" (R11) | p9, p10 |

K4–K9 pair with p10 by position only. The deck does not say which check-marked line on p10 answers which crossed line on p9.

### 3.11 What the talk advocates

No sentence in the deck is worded as a recommendation. In its own words and in page order, it advocates:

1. "Make agentic AI production-ready with integrated data privacy and model security" (p2), using the four highlighted libraries against the two challenges (p3).
2. Put rails at the five stages with NeMo Guardrails, backed by the Nemotron safety models, to "intercept policy violations with minimal performance impact" (p5, p7).
3. Audit models with NeMo Auditor or garak, following the four-step workflow (p8).
4. Run long-running agents inside OpenShell, under its sandbox, privileged control layer and in-silicon boundary. The goals are that "All agent actions are monitored", the "Agent cannot reach or modify the controls" and "Each agent runs under an explicit policy" (p10, p11).
5. Add Sentry, "an out-of-band watchdog that continuously monitors and can stop agent behavior in milliseconds" (p12).

### 3.12 Links in the deck

| Page | Link text | Target |
|---|---|---|
| p3 | "IBM Report" (both) | https://www.zendata.dev/post/understanding-personally-identifiable-information |
| p5 | "product page" | https://developer.nvidia.com/nemo-guardrails |
| p8 | "github.com/NVIDIA/garak" | plain text, not a link |
| p14 | "OpenShell Page" | https://www.nvidia.com/en-us/ai/openshell/ |
| p14 | "OpenShell GitHub" | https://github.com/NVIDIA/openshell |
| p14 | "Open Agent Safety Platform Page" (under "NVIDIA Sentry") | https://www.nvidia.com/en-us/solutions/ai/agent-safety/ |

---

## 4. Stage coverage [ours]

This is our placement of the catalogue on the brief's taxonomy. The deck names stages only on p5. An asterisk (*) marks a placement we inferred beyond the deck's words.

| Stage | What the talk offers there | Basis |
|---|---|---|
| input | G2 Content Safety, G3 Jailbreak Protection, G4 Topic Control, G5 PII Detection, G8 Custom Rails (models M1–M7). OpenShell mediates "Prompt" (R13); Sentry receives "Prompt" (S8) | p5, p7, p11, p12 |
| dialog | G4 Topic Control, G8 Custom Rails | p5 |
| retrieval | G5 PII Detection, G6 Knowledge Base/RAG, G8 Custom Rails. "Data" is mediated by OpenShell (R13*) and received by Sentry (S8*) | p5, p11*, p12* |
| tool-execution | G7 Agentic Security, G8 Custom Rails ["Execution"]. The harness runs in a sandbox (R2, R3); filesystem and network control (R4); egress gate (R7). "Tools" are mediated (R13) and received by Sentry (S8) | p5, p10–p12 |
| output | G2 Content Safety, G5 PII Detection, G6 Knowledge Base/RAG, G8 Custom Rails | p5 |
| handoff | **Nothing.** The nearest text is the problem statement "Boundary between agents is unclear" (K9, p9) and "Each agent runs under an explicit policy" (R11, p10) | p9, p10 |
| memory | **Nothing.** The deck has no memory stage and no memory control | none |
| runtime | OpenShell, R1–R13; hardware H1–H3 | p10, p11 |
| evaluation | NeMo Evaluator, "EVALUATE" (L6*, a verb only). The four figures on p7 are the models' own scores. The datasets D1–D5 are described only as training data | p2, p4, p7 |
| red-teaming | NeMo Auditor and garak, A1–A9 | p8 |
| monitoring | Sentry, S1–S8, joined to BlueField-4 (H4). "All agent actions are monitored" and "traces all actions" (R12). NeMo Agent Toolkit, "INSTRUMENT" (L1*, a verb only) | p2*, p10–p12 |
| (no stage given) | Data privacy: P1 Safe Synthesizer and P2 Anonymizer. Lifecycle: L2–L5 | p2–p4 |

---

## 5. The talk's reference design and flows, reproduced

The deck has no single end-to-end diagram. Below are its five diagrams as drawn, with labels verbatim. Words in [brackets] describe unlabelled icons.

### 5.1 p2: NeMo libraries around Nemotron

```
                           +----------------------+
                           | Enterprise AI System |
                           +----------------------+
                              |                ^
                          (a) |                | (b)
 [Nemotron] ------------------+                +------------- [Specialized AI Agents]
     |                                                                        |
 (c) v                                                                        | (d)
 +----------------------------------------------------------------------------------+
 | Agent Toolkit | Curator       | Safe Synthesizer* | Customizer, RL | Guardrails* |
 | INSTRUMENT    | PROCESS       | SYNTHESIZE        | IMPROVE        | GUARDRAIL   |
 |---------------+---------------+-------------------+----------------+-------------|
 | Retriever     | Data Designer | Anonymizer*       | Evaluator      | Auditor*    |
 | LEARN         | GENERATE      | DETECT            | EVALUATE       | AUDIT       |
 +----------------------------------------------------------------------------------+
```

- **Connectors:**
  - (a) a line with no visible arrowhead.
  - (b) an arrowhead pointing at the Enterprise AI System.
  - (c) an arrowhead pointing into the library rows.
  - (d) a line from beside NeMo Guardrails to Specialized AI Agents, with no visible arrowhead.
- **Names:** every library is "NeMo …"; the sketch drops the prefix.
- **Asterisk (\*):** outlined in yellow on the slide. These are the four libraries that p3 and p4 single out.

### 5.2 p3: challenge → library

```
  "Data leaks and bypassed protections expose sensitive information and enable model exploitation"

  1  Data Security Exposure                       2  Model Security Risks
     "52% of data breaches involve some form         "97% of companies with AI breaches had
      of customer PII." IBM Report                    no AI access controls in place." IBM Report

     NeMo Safe Synthesizer    NeMo Anonymizer        NeMo Guardrails          NeMo Auditor
                                                           |
                                                           v
                                                     Nemotron Safety Models
```

The only arrow on the page runs from NeMo Guardrails to Nemotron Safety Models. Each library sits under its challenge, without connecting lines.

### 5.3 p5: NeMo Guardrails rail stages

```
  [ Input ]          Content Safety | Jailbreak Protection | Topic Control | PII Detection | Custom Rails
     [ Retrieval ]      PII Detection | Knowledge Base/RAG | Custom Rails
        [ Dialog ]         Topic Control | Custom Rails
           [ Execution ]      Agentic Security | Custom Rails
              [ Output ]         Content Safety | PII Detection | Knowledge Base/RAG | Custom Rails
```

- **Layout:** five stage cards in a descending staircase, left to right. The slide draws no arrows between them.
- **"Key Features" panel beside them:** "Customizable Use Cases"; "Performance-Optimized" ("Parallel execution of multiple guardrails without performance overhead."); "Flexible Deployment".
- **Models:** the families p7 calls "Supported in NeMo Guardrails" are Content Safety, PII, Topic Control and Jailbreak Detection. p5 does not show them.

### 5.4 p9 → p10: from a standard OS to the OpenShell runtime boundary

p9, drawn in red (the problem):

```
                                     AI Models (five logos)
                                               ^
                                               | (red, double-headed)
                                               v
                              +-----------------------------------+
Ambiguous Instructions  --->  | Agent Harness                     | --->  Unapproved External Access (globe)
"Can lead an agent to take    | Connects Decisions to Tools       |       "Can let agents send data outside
 actions outside its          | [doc] [db] [</>] [target]         |        approved boundaries"
 approved scope"              | (E.g. Claude, Codex, Hermes, etc.)|
                              +-----------------------------------+
                              +- - - - - - - - - - - - - - - - - -+
                              : Standard Operating System         :
                              : Runtime Without Agent-Specific    :
                              : Controls                          :
                              +- - - - - - - - - - - - - - - - - -+

(x) No complete record of agent actions
(x) Sensitive data and credentials can reach unapproved destinations
(x) Boundary between agents is unclear
```

p10, drawn in green (the OpenShell answer):

```
                                     AI Models (five logos)
                                               ^
                                             [lock]
                                               v
                        + AGENT SANDBOX - - - - - - - - - - - - - - - +
User Prompt  ---------> : Agent Harness                               : --[lock]-->  Data Stays in Your
                        : Connects Decisions to Tools                 :             Secure Boundary (globe)
                        : [doc] [db] [</>] [target]                   :
                        : (E.g. Claude, Codex, Hermes, etc.)          :
                        +- - - - - - - - - - - - - - - - - - - - - - -+
                        +-PRIVILEGED CONTROL LAYER -------------------+
                        | OpenShell Control Layer                     |
                        | [ Filesystem Access ]  [ Network Access ]   |
                        +---------------------------------------------+
                        +---------------------------------------------+
                        | In-Silicon Enforcement Boundary             |
                        +---------------------------------------------+

(ok) All agent actions are monitored
(ok) Agent cannot reach or modify the controls
(ok) Each agent runs under an explicit policy
```

- The five "AI Models" logos carry no names. **[ours]** They look like Claude/Anthropic, Gemini, OpenAI, Qwen and Meta.
- The four tool icons in the harness have no labels. [doc] [db] [`</>`] [target] are our descriptions of the icons.

### 5.5 p11 → p12: the Open Agent Safety Platform, "Open reference design" (p11)

p11 (OpenShell):

```
Secure Runtime Boundary: "Governs and Mediates All Actions, Enforces Policy at Runtime"
+-[lock] NVIDIA OpenShell ----------------------+
| [Gateway]        + - Agent Sandbox - - - +    |            Vera CPU Tray (photo)
| [Supervisor]     :   [Agent Harness]     :    | <-------->  [Vera CPU]
| [Policy Prover]  + - - - - - - - - - - - +    |                ^
+-----------------------------------------------+                |
                                                                 v
                                                          [chips: "CX-9"] <--- "Prompt / Tools / Data / Model" --->
                                                                                :         :         :         :
                                                                             [Prompt]  [Tools]   [Data]    [Model]
```

p12 (Sentry added):

```
(OpenShell box, its arrow to the tray, and the Vera CPU: as on p11)
                                                         +-[lock] NVIDIA Sentry ---------------------------------+
        [Vera CPU]                                       | In-Silicon Out-of-Band Monitor:                       |
            ^                                            | "Agent Reasoning Inspection and Tamper-Proof          |
            |                                            |  Telemetry"                                           |
            v              "Prompt / Tools / Data /      | [Hardware-Based Enforcement]                          |
 [chips: "BlueField-4"] <------ Model / Policies" -----> | [Continuous Agent Monitoring and Threat Detection]    |
                                                         | [Trusted Telemetry and Detection Pipeline]            |
                                                         | [Millisecond-Scale Containment and Quarantine]        |
                                                         +-------------------------------------------------------+
                                                             :             :             :             :
                                                          [Prompt]      [Tools]       [Data]        [Model]
```

- **The right-hand arrow:** on p11 it runs to the edge of the picture, with no box at its end. On p12 it ends at the Sentry box, and its label gains "Policies".
- **The hardware:** the tray is a photo. "CX-9" and "BlueField-4" are labels on its chips.
- **p12** leaves p11's OpenShell box unchanged.

---

## 6. What the talk says about AWS/Bedrock, AgentCore, Nemotron, MCP and tool safety

### 6.1 AWS, Amazon Bedrock and AgentCore: not mentioned

- **Search:** we ran a whole-word search of both text extractions (layout and reading order). None of these terms occurs: AWS, Amazon, Bedrock, AgentCore, Lambda, Cedar, NIM, NemoGuard, MCP.
- **Logos:** none of the 107 logos on p13 is AWS or Amazon.
  - Two of them are easy to misread: "BEDROCK DATA" and "Lambda" (a boxed λ).
  - **[ours]** We read them as the companies Bedrock Data and Lambda, not Amazon Bedrock or AWS Lambda.
- **Deployment statements** never name a cloud:
  - NeMo Guardrails: "Flexible Deployment", "Efficiently orchestrate and deploy anywhere." (p5)
  - NeMo Auditor: "Multi-Platform / Enterprise-Grade", "Flexible APIs with local and cloud deployment support." (p8)
  - OpenShell and Sentry are drawn joined to NVIDIA hardware (H1–H4).

### 6.2 NIM and NemoGuard: neither term appears

The deck names the safety models only as in M1–M7 (p4). It does not say how they are packaged, hosted or served.

### 6.3 Nemotron: every statement

- **p2:** "Nemotron" is the node at the left of the libraries diagram. An arrow runs from it into the NeMo libraries, and a line runs to the "Enterprise AI System".
- **p3:** "Nemotron Safety Models" sit under NeMo Guardrails, at the end of an arrow from it.
- **p4:** "Open NeMo libraries built on open Nemotron models which are trained on open Nemotron datasets". The page lists the seven models (M1–M7) and the five "Nemotron …" datasets (D1–D5). Two of the models are "Llama Nemotron …", and one is "GLiNER PII".
- **p7:** "Open NVIDIA Nemotron Safety Models", "Advanced GPU-accelerated multilingual, multimodal models with reasoning for a variety of use cases". They are "Supported in NeMo Guardrails", with the four families and figures in G2–G5.
- **Nemotron as an agent's main LLM is not discussed.** On p9 and p10, "AI Models" are five logos with no names. **[ours]** None looks like an NVIDIA or Nemotron mark.

### 6.4 MCP: not mentioned

Neither "MCP" nor "Model Context Protocol" appears. Tools appear only in two places:
- the harness that "Connects Decisions to Tools" (p9, p10);
- the "Tools" channel (p11, p12).

### 6.5 Tool and action safety: every statement

- **p5:** the "Execution" stage carries "Agentic Security" and "Custom Rails" (G7, G8).
- **p8 (probe types):**
  - Exploitation, "Generate SQL injection or malicious Jinja templates"
  - Web Injection, "Permit or enact cross-site attacks, such as private data exfiltration"
  - Package Hallucination, "Code generations that specify non-existent, and therefore, insecure packages"
- **p9:**
  - "Long-running AI agents can combine tools, credentials and network access in ways existing controls were not designed to govern."
  - "Agent Harness", "Connects Decisions to Tools", "(E.g. Claude, Codex, Hermes, etc.)"
  - "Ambiguous Instructions", "Can lead an agent to take actions outside its approved scope"
  - "Unapproved External Access", "Can let agents send data outside approved boundaries"
  - "Sensitive data and credentials can reach unapproved destinations"
  - "No complete record of agent actions"
- **p10:**
  - "AGENT SANDBOX"
  - "PRIVILEGED CONTROL LAYER", "OpenShell Control Layer": "Filesystem Access", "Network Access"
  - padlocks on the model link and on the outbound link ("Data Stays in Your Secure Boundary")
  - "All agent actions are monitored"; "Agent cannot reach or modify the controls"; "Each agent runs under an explicit policy"
- **p11:** "Governs and Mediates All Actions, Enforces Policy at Runtime"; Gateway, Supervisor and Policy Prover; "Prompt / Tools / Data / Model" mediated.
- **p12:** Sentry receives "Prompt / Tools / Data / Model / Policies"; "Millisecond-Scale Containment and Quarantine".

---

## 7. Observations on the deck [ours, not the talk's]

- **Two halves, never joined.** No page shows NeMo Guardrails, the Nemotron safety models or NeMo Auditor together with OpenShell or Sentry. The deck does not say whether the rails run inside the OpenShell sandbox, at its Gateway, or apart from it.
- **Hardware is assumed, not discussed.**
  - OpenShell and Sentry are drawn joined to NVIDIA hardware (Vera CPU tray, CX-9, BlueField-4), and the deck calls their boundary and monitor "In-Silicon".
  - The deck does not say whether OpenShell works without that hardware, for example on a cloud VM or in a managed agent runtime.
  - It does not say whether Sentry exists as software at all.
- **Release status is not stated.** OpenShell has a GitHub link (p14). Sentry has no repository or product page of its own: p14 lists only the platform page under the "NVIDIA Sentry" heading.
- **Figures come without context.**
  - The four percentages on p7 give no model version, benchmark, dataset or baseline. "56% Higher F1 Score; 28% Higher Recall" does not say higher than what.
  - Both statistics on p3 are cited as "IBM Report", but both hyperlinks go to a zendata.dev blog post, not to an IBM page.
- **Several labels have no definition:**
  - Gateway, Supervisor and Policy Prover (p11)
  - the Agentic Security and Knowledge Base/RAG rails (p5)
  - Safe Synthesizer, Anonymizer and the six lifecycle libraries (one verb each, p2)
  - "Policies" as a channel into Sentry (p12)
- **The p6 example names neither the rail nor the model** behind "Identified as category Financial Advice, Investments".
- **Not covered at all:** handoff between agents, agent memory, and MCP or tool-protocol security.
- **Dates:** the title slide says "September 2026"; the PDF was created on 2026-10-04 (author metadata "Alex Sandu").

---

## 8. Questions for feasibility vetting [ours]

These are what we'd need to check on our platform before using each item. The platform facts cited come from our own docs, named on each line, not from the talk.

1. **G1: where NeMo Guardrails would run.** Our only code in the path runs inside each agent on AgentCore Runtime, and models are "reached only through the gateway" (`architecture/one-page.md`).
   - Can the NeMo Guardrails library go into our agent image (dependencies, size, cold start)?
   - Can its rail-model calls go through `modaas-agw`?
2. **G1 beside the platform's own guardrail.** The gateway already applies Bedrock guardrails (`architecture/ARCHITECTURE.md` EP-7):
   - they block prompt attacks on input;
   - a block is logged as ALLOW;
   - their tool-output screening is untested.

   Would NeMo rails duplicate that? How would a NeMo verdict be recorded next to EP-7's `outcome.real`?
3. **G8: custom rails.** Could our one in-path check be written as a custom input rail, or should it stay plain code? That check is EP-1, `evaluate(C16)` before each model call (`one-page.md`).
4. **M1–M7: the safety models.**
   - Is any of the seven available on Bedrock, or approvable as a ModelConfig behind the gateway?
   - If not, could we host one ourselves? p7 calls them "GPU-accelerated". Does the workshop account or EKS cluster offer GPU nodes, and may participants deploy there?
   - Which exact checkpoints do the deck's names refer to, and under what licence?
5. **G9: cost and latency.** Every rail is an extra model call.
   - Do the extra calls fit the shared ceilings (100 model requests/min, 2.5M tokens/h; `ARCHITECTURE.md` EP-9, `gap-list.md`) and our run-time budget?
   - Does "Parallel execution of multiple guardrails without performance overhead" hold behind our gateway?
6. **G4: topic control.**
   - Can our agents' scopes (customer, IT, network) be expressed for Llama Nemotron Topic Control?
   - Can its category output, like p6's "Identified as category …", be logged as evidence?
7. **G5, P1 and P2: PII and data privacy.**
   - Do our tools return PII, for example `customer-records`?
   - Could GLiNER PII or NeMo Anonymizer redact it in tool outputs and in the records we emit?
   - Could NeMo Safe Synthesizer produce synthetic test records?
   - Are both libraries released and runnable by us?
8. **G6: the retrieval rail.** Do our agents have a retrieval step the rail could see? Or is retrieval only a tool call (for example `modaas-docs`, `gap-list.md`), which would make it the Execution rail's job?
9. **G7: Agentic Security and execution rails.** What does this rail actually check? The deck doesn't say. Our tool calls are MCP calls that go through `modaas-agw` to the AWS AgentCore Gateway and on to Lambda tools (`ARCHITECTURE.md` §2.2 diagram, EP-12).
   - Can an in-agent rail see and block those calls, including undeclared tools? (`gap-list.md`: the shared AgentCore Gateway exposes every tool on every route.)
   - Can it screen tool outputs?
   - How would it sit beside the Cedar tool policy (EP-6)?
10. **D1–D5: the datasets.**
    - Are they downloadable and licensed for our use?
    - Could "Nemotron AIQ Agentic Safety" seed our adversarial cases (ADV-…, `ARCHITECTURE.md`)?
11. **A1–A9: NeMo Auditor and garak.**
    - Is the NeMo Auditor service (targets, configurations, jobs) available to us, or only open-source garak?
    - Can garak target our agent or the gateway?
    - May we fire attack probes at the shared platform, under the shared team key and its ceilings?
    - Which subset of probes fits our time and token budget?
    - How would the results enter our evidence as a pre-deployment record?
12. **R1–R13: OpenShell.**
    - Can OpenShell run inside AgentCore Runtime, where we control neither the OS nor a privileged layer?
    - If only on hosts we control, such as EKS pods, would it need privileged containers that our participant role can't create?
    - Does it need the NVIDIA hardware the deck draws (Vera CPU tray, CX-9)?
    - Which of p10's properties do AgentCore and Cedar already give us? For example, "Each agent runs under an explicit policy": today every Cedar decision names one shared `bootstrap-key` identity (`gap-list.md`).
13. **S1–S8 and H1–H4: Sentry and the hardware.**
    - Is Sentry obtainable at all? The deck gives no repository.
    - Does it need BlueField-4?
    - Which of its functions could we approximate in software? Pausing a model on our platform took 33–41 s to take effect (`gap-list.md`), against Sentry's "Millisecond-Scale Containment".
14. **L1–L6: the lifecycle libraries.** The deck gives one verb each.
    - Is any of them needed by, or useful to, our evidence and evaluation path? For example, NeMo Agent Toolkit "INSTRUMENT" or NeMo Evaluator "EVALUATE".
    - Can it be installed here?
15. **Handoff and memory.** The talk covers neither. Our run is a three-agent chain (`ifabric-customer` → `ifabric-it` → `ifabric-network`; `one-page.md`), and handoffs are EP-5 in `ARCHITECTURE.md`. Does anything in the talk check those handoffs?

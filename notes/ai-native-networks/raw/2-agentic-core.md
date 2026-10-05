# AINN workshop: "Deploy End-to-end 5G Network" (`module3-agentic-core`). Research notes

- Catalog URL (JavaScript SPA; WebFetch saw only the title "Workshop Studio"): https://catalog.workshops.aws/ai-native-networks/en-US/module9-additional-resources/module3-agentic-core
- Raw page source I read in full (public, anonymous GET, `requiresAuth:false`): https://static.us-east-1.prod.workshops.aws/public/c5491468-dbcf-44c0-aa99-4cd7265be03f/content/module9-additional-resources/module3-agentic-core/index.en.md
  - The build id `c5491468-…` comes from https://static.us-east-1.prod.workshops.aws/public/quicklinks/ai-native-networks/published.json. It changes when the workshop is republished, so re-resolve it if the link stops working.
  - Local copy: `scratchpad/ainn/raw/agentic-core.en.md` (115 lines). A second copy fetched independently by another subagent (`raw/md__content__module9-additional-resources__module3-agentic-core__index.en.md`) has the same sha256 (`00828ae6…167`).
- Fetched 2026-10-05. Line numbers `Lnn` below refer to that source file.
- Label key: **[page]** = stated on this page. **[sibling]** = stated on another page of the same workshop (URL given). **[inference]** = my reading, not stated anywhere.

---

## 1. Summary

- **[page] The page builds no agent and no MCP server.** It does three things: (1) deploys OpenAirInterface (OAI) 5G Core + RAN on Amazon EKS with eksctl and Helm; (2) runs a script that draws an interface map; (3) offers an **ideas list** of hypothetical MCP tool names, introduced as "potential projects" (L64) and as "Need more specific examples? You can abstract various interfaces via MCP using the following approach:" (L71). None of the 22 function names is implemented, given a schema, or callable in the workshop.
- **[page] Only the intro mentions an agent:** "In this module, learn how to build a more comprehensive agentic application, powered by Strands Agents, that can take actions on a simulated, end-to-end 5G network powered by OpenAirInterface (OAI) Core and Radio Access Network stack." (L6). The page has no agent code, names no model, and does not mention MCP transport or auth.
- **What "agentic core" means:** the phrase never appears in the page text. It exists only in the URL slug. The Additional Resources index (https://catalog.workshops.aws/ai-native-networks/en-US/module9-additional-resources) describes the page as **[sibling]** "**End-to-End 5G Network:** Orchestrate a complete 5G network using OpenAirInterface (OAI) on Amazon EKS. Abstract critical network functions—AMF, SMF, UPF, and RAN split architectures—through programmable interfaces that AI agents can control dynamically." **[inference]** "Agentic core" means an agent-controllable 5G core. That is the goal; the page itself delivers only the non-agentic deployment.
- **Deployment [page]:** OAI from `https://gitlab.eurecom.fr/oai/cn5g/oai-cn5g-fed.git`, chart `charts/e2e_scenarios/case3`, Helm release `oai-5g-basic`. It runs on EKS 1.32 (cluster `oai-5g-cluster`, us-east-1) with 6 × t3.large nodes. It is **not Open5GS and not free5GC.**
- **Governance [page]:** none. There is no auth, approval, guardrail, audit or least-privilege step, and tools are not split into read and write. See section 4.

## 2. Tools table (all 22 names on the page, L72–L104)

"Page group" is the page's own heading, which is as close as the page gets to naming an interface. "As stated" is verbatim. The column "fits `<domain>_<verb>_<resource>`?" tests the guide's claimed convention. **[inference]** The "R/W tier" column is my classification, not the page's.

| # | Function (verbatim) | Page group (interface as stated) | As stated (verbatim) | fits `<domain>_<verb>_<resource>`? | R/W tier [inference] |
|---|---|---|---|---|---|
| 1 | `nrf_register_nf()` | 5G Core NFs (SBI - Service Based Interface), "HTTP/2 REST APIs between core functions" | "Register/deregister network functions with NRF" | yes | write, high |
| 2 | `amf_manage_ue()` | SBI | "Control UE registration and mobility via AMF" | yes | write, high |
| 3 | `smf_create_session()` | SBI | "Establish/modify PDU sessions through SMF" | yes | write, high |
| 4 | `udm_subscriber_data()` | SBI | "Manage subscriber profiles in UDM" | no (no verb) | write, high (subscriber data) |
| 5 | `f1_setup_control()` | RAN Split Architecture Control: "Abstract F1, E1, and Xn interfaces" | "Manage F1-C connections between CU-CP and DU" | loosely (setup = verb, control = F1-C) | write, high |
| 6 | `e1_bearer_setup()` | RAN split | "Control E1 bearer establishment between CU-CP and CU-UP" | no (domain_resource_verb) | write, high |
| 7 | `cu_split_config()` | RAN split | "Dynamically configure CU-CP/CU-UP split for network slicing" | no / ambiguous | write, high |
| 8 | `n2_ngap_monitor()` | 3GPP Reference Point Monitoring | "Track NGAP associations on N2 (AMF-gNB) for UE state changes" | no (domain_protocol_verb) | read |
| 9 | `n4_pfcp_control()` | Reference points | "Manage PFCP sessions on N4 (SMF-UPF) for traffic steering and QoS" | no (domain_protocol_verb) | write, high |
| 10 | `n3_gtp_tunnel()` | Reference points | "Monitor GTP-U tunnels on N3 (gNB-UPF) for user plane traffic" | no (no verb) | read |
| 11 | `n6_data_network()` | Reference points | "Control N6 routing to external data networks and traffic servers" | no (no verb) | write, high |
| 12 | `gnbsim_ue_attach()` | Traffic Generation and UE Simulation | "Simulate UE registration and PDU session establishment" | no (domain_resource_verb) | write, low/med (simulator) |
| 13 | `iperf3_traffic_test()` | Traffic/UE sim | "Generate traffic between UE simulators and traffic server" | no (domain_resource_verb) | write, med (load) |
| 14 | `multi_ue_load_test()` | Traffic/UE sim | "Execute concurrent UE scenarios for capacity testing" | no | write, med/high (load) |
| 15 | `qos_validation()` | Traffic/UE sim | "Test different 5QI values and session AMBR configurations" | no | write, med |
| 16 | `interface_health_check()` | Network Analytics and Automation | "Automated verification of all 5G reference points using log analysis" | no | read |
| 17 | `resource_optimization()` | Analytics/automation | "Monitor pod resource usage and apply dynamic scaling based on traffic patterns" | no | **read and write in one tool**, high |
| 18 | `network_slice_management()` | Analytics/automation | "Create and manage network slices with different QoS characteristics" | no | write, high |
| 19 | `fault_detection()` | Analytics/automation | "Automated detection of interface failures, OOM conditions, and performance degradation" | no | read |
| 20 | `nwdaf_analytics()` | Advanced 5G Features | "Control Network Data Analytics Function for ML-driven insights" | no | ambiguous ("Control") |
| 21 | `lmf_location_services()` | Advanced 5G Features | "Manage Location Management Function for positioning services" | no | write, high (UE location is PII) |
| 22 | `nef_api_exposure()` | Advanced 5G Features | "Abstract Network Exposure Function for third-party API access" | no | write, high (exposes the network to third parties) |

Tally:
- **3 names clearly fit `<domain>_<verb>_<resource>`** (`nrf_register_nf`, `amf_manage_ue`, `smf_create_session`), and `f1_setup_control` fits loosely. These are exactly the four examples the guide cites.
- About 5 names fit the reverse order `<domain>_<resource>_<verb>` (`e1_bearer_setup`, `n2_ngap_monitor`, `n4_pfcp_control`, `gnbsim_ue_attach`, `iperf3_traffic_test`).
- The rest have no verb or are single nouns.

Interface notes:
- **[page]** Xn appears only in a group heading (L78: "Abstract F1, E1, and Xn interfaces for dynamic RAN management"). No `xn_*` tool exists.
- **[page]** Only the reference-point group (`n2_`, `n3_`, `n4_`, `n6_`) and two RAN tools (`f1_`, `e1_`) start with an interface name. The SBI group (`nrf_`, `amf_`, `smf_`, `udm_`) starts with the **network function** name.
- **[inference]** In 3GPP terms the SBI group maps to the service-based interfaces Nnrf, Namf, Nsmf and Nudm, but the page never uses those names. For `amf_manage_ue`, UE registration and mobility signalling actually travels over N1 (NAS) via N2 (NGAP). The page's grouping is illustrative, not spec-precise.

Interfaces in the page's diagram (`/static/visual-network-architecture-module3.png`), **[page]** as drawn:

- Core:
  - AMF–NR-UE/gNB: N2 (NGAP/SCTP), port 38412
  - AMF–SMF: SBI (HTTP/2), port 80
  - SMF–UPF: N4 (PFCP/UDP), port 8805
  - gNB–UPF: N3 (GTP-U/UDP), port 2152
  - UPF–Traffic Server: N6 (IP)
- RAN split:
  - DU–CU-CP: F1-C (F1AP/SCTP)
  - CU-CP–CU-UP: E1 (E1AP/SCTP)
  - DU–CU-UP: F1-U (GTP-U/UDP)
  - CU-CP–AMF: N2
  - CU-UP–UPF: N3

## 3. MCP and agent architecture

### On this page

- **[page]** There is no MCP server, no framework, no transport, no auth and no model. The page says only "powered by Strands Agents" (L6), plus the claim that "This MCP abstraction approach transforms…" (L106).
- **[page]** The only code on the page is deployment code (L32–L42, abridged):
  ```bash
  export CLUSTER_NAME=oai-5g-cluster; export REGION=us-east-1
  git clone https://gitlab.eurecom.fr/oai/cn5g/oai-cn5g-fed.git && cd oai-cn5g-fed/charts/e2e_scenarios/case3
  eksctl create cluster --name $CLUSTER_NAME --version 1.32 --region $REGION --without-nodegroup
  eksctl create nodegroup --cluster $CLUSTER_NAME --region $REGION --name workers --node-type t3.large --nodes 6 --nodes-min 0 --nodes-max 9
  helm dependency build
  helm install oai-5g-basic . -f values.yaml
  ```
- **[page]** It also downloads and runs `generate_interface_map.sh` from `https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/508f04dc-026a-4260-ac15-c6f011d50cf9/generate_interface_map.sh`. I read it and did not run it. It:
  - runs `aws eks update-kubeconfig` and `kubectl get pods -o wide`, and greps for pods named `oai-amf/smf/upf/nrf/ausf/udm/udr/cu-cp/cu-up/du/nr-ue/gnb`, `traffic-server` and `mysql`;
  - writes `NETWORK_INTERFACES_VISUAL.md`;
  - prints, but does not run, suggested `kubectl exec -it …` and `kubectl logs …` test commands;
  - contains no MCP or agent code.
- **[page]** Architecture image (`/static/eks-base-infra.png`, alt text "Base EKS infrastructure created by eksctl"): one VPC, an EKS cluster across 3 AZs, private subnets, managed T3 worker node groups, an Internet Gateway and a NAT Gateway. No agent or MCP component appears.

### Context from the workshop's core modules ([sibling], not this page)

**[inference]** These are what "Using this baseline" (L64) would plug into.

- **MCP servers (Modules 2/3):**
  - Built with **FastMCP**: `mcp = FastMCP(host="0.0.0.0", stateless_http=True)` and `mcp.run(transport="streamable-http")`, from the public notebooks `…/r1-mcp-server.ipynb` and `…/o2-mcp-server.ipynb` under the same ws-assets prefix.
  - Wrapped with the "Amazon Bedrock AgentCore Python SDK" and hosted on **AgentCore Runtime**.
  - The O2 notebook "Sets up Cognito authentication, IAM roles, and deploys server to AgentCore Runtime" (https://catalog.workshops.aws/ai-native-networks/en-US/module3-o2-mcp).
- **Agent (Module 4, https://catalog.workshops.aws/ai-native-networks/en-US/module4-local-agent):**
  - Built with the **Strands Agents** SDK, `MCPClient(streamablehttp_client(...))`.
  - Endpoint: `https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT`
  - Model: `BedrockModel(model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0")`. Module 7 uses the same model.
  - Auth is a Cognito `USER_PASSWORD_AUTH` bearer token, with hardcoded credentials in the sample code: `AuthParameters={'USERNAME': 'testuser', 'PASSWORD': '<demo password redacted>'}`
  - The agent loads **all** tools from both servers unfiltered (`all_tools.extend(...)`).
- **Module 5** deploys that agent to AgentCore Runtime with "OAuth authentication with Amazon Cognito" and SSM/Secrets Manager config.
- **Gateway (Module 7, https://catalog.workshops.aws/ai-native-networks/en-US/module7-agentcore-gateway):**
  - Lambda functions become MCP tools: `create_gateway(..., protocolType='MCP', authorizerType='CUSTOM_JWT', authorizerConfiguration={"customJWTAuthorizer": {"allowedClients": [client_id], "discoveryUrl": ...}})`.
  - Outbound auth: `credentialProviderType: "GATEWAY_IAM_ROLE"`. The Lambda role uses `AWSLambdaBasicExecutionRole`.
  - Strands logging goes to stdout at INFO.
  - The page notes "Tool names are shortened to meet the 64-character limit".

## 4. Governance: present vs absent

**On this page [page]: absent throughout.** It has no:
- authN or authZ
- per-tool permissions
- human approval or confirmation
- dry-run
- guardrails
- audit or logging
- rollback
- rate limits
- separation of read and write

Mutating tools (`smf_create_session`, `n4_pfcp_control`, `n6_data_network`, `network_slice_management`, and `resource_optimization`, which says "apply dynamic scaling") sit next to read-only monitors with nothing to tell them apart. The closing claim even frames autonomy as the goal: "…where AI agents can dynamically manage network functions…" (L106–108). The page does not say outright that governance is out of scope. It simply never raises it.

**Operational posture [page], observed:**
- Commands run in **CloudShell under the participant's own credentials**.
- Tools are installed unpinned: `curl … get-helm-3 | bash` from Helm `main`, and eksctl `releases/latest`.
- The OAI repo is cloned unpinned (default branch). The `helm install` has no namespace flag.
- Cleanup is cluster deletion only.
- Minor inconsistencies: L14 refers to "the EC2 instance from Module 2", but this workshop's Module 2 is a SageMaker notebook. L111 mentions an "EKS add-on … and IAM service account" that the page never creates. **[inference]** The text was probably adapted from another workshop.

**In the sibling modules [sibling]:**
- **Present:** Cognito JWT inbound auth (Runtime and Gateway `CUSTOM_JWT` with `allowedClients`), IAM outbound auth (`GATEWAY_IAM_ROLE`), and SSM/Secrets Manager for config.
- **Absent:** Cedar or any tool-level policy, approvals or human-in-the-loop, Bedrock Guardrails, audit trail, least-privilege tool scoping, and kill switch or pause.
- I checked Modules 2–7 and this page by keyword search for guardrail, cedar, approv, human-in, confirm, audit and "least privilege". Every "confirm" hit was in sample output text or "Confirmation messages for each created target", so none is a control.
- **[inference]** "Authorized" here means "any holder of a valid client token can call every tool".

## 5. Claims verification (guide → page)

| # | Guide claim | Verdict | Evidence (verbatim, page URL above unless noted) |
|---|---|---|---|
| 1 | The Additional Resources module "names 5G core interfaces as callable tools" | **DIFFERENT** | The names are illustrative suggestions, not callable or implemented tools: "Using this baseline, you can explore the following potential projects:" (L64); "Need more specific examples? You can abstract various interfaces via MCP using the following approach:" (L71). No schemas, server or code. The SBI names are network functions, not interfaces. |
| 2 | Tools have "the shape `<domain>_<verb>_<resource>`" | **NOT FOUND** | The page states no naming convention. Only 3 of 22 names fit cleanly (plus `f1_setup_control` loosely); about 5 use `<domain>_<resource>_<verb>`; the rest fit neither (section 2). **Closest match elsewhere [sibling]:** the "Agentic Network Framework" page lists "Tool naming conventions" with prefixes `r1_get_*`, `r1_subscribe_*`, `r1_set_*`, `r1_create_*`, `r1_start_*` (e.g., `r1_start_simulation`, `r1_get_simulation_status`) at https://catalog.workshops.aws/ai-native-networks/en-US/module9-additional-resources/module1-agentic-network-framework. That is O-RAN R1/VIAVI, not 5G core, and it is a prefix table, not a stated `<domain>_<verb>_<resource>` rule. |
| 3 | Examples `amf_manage_ue()`, `smf_create_session()`, `nrf_register_nf()`, `f1_setup_control()` | **CONFIRMED** | L73 "`nrf_register_nf()` - Register/deregister network functions with NRF"; L74 "`amf_manage_ue()` - Control UE registration and mobility via AMF"; L75 "`smf_create_session()` - Establish/modify PDU sessions through SMF"; L79 "`f1_setup_control()` - Manage F1-C connections between CU-CP and DU". **[inference]** These four are the only names on the page that fit the claimed shape. |
| 4 | "The function name is the 3GPP interface reference (N2, N4, F1, Xn) …" (the brief's quote was truncated, so I verified only the visible part) | **DIFFERENT (partial)** | True for `n2_`/`n3_`/`n4_`/`n6_` and `f1_`/`e1_` prefixes. Not true for the SBI group: 3 of the guide's own 4 examples (`amf_`, `smf_`, `nrf_`) are NF names. **Xn** appears only in the heading "Abstract F1, E1, and Xn interfaces for dynamic RAN management" (L78). No Xn tool is named. |
| 5 | Source: "AI Native Networks Immersion Day, Additional Resources, 'Deploy End-to-end 5G Network' module" | **CONFIRMED** | Workshop title "AI Native Networks Immersion Day" (`published.json` metadata). Section "Additional Resources" (`/module9-additional-resources`). Page front-matter `title : "Deploy End-to-end 5G Network"` (L2). The URL slug is `module3-agentic-core`. |
| 6 | Quote: "this MCP abstraction turns a static 5G network deployment into programmable, agentic-controlled infrastructure." | **DIFFERENT (a paraphrase presented as a quote)** | Verbatim (L106–108): "**This MCP abstraction approach transforms the static 5G network deployment into a programmable, agentic-controlled infrastructure where AI agents can dynamically manage network functions, simulate realistic traffic scenarios, and optimize performance based on real-time analytics.**" The guide drops "approach", changes "transforms the static" to "turns a static", drops "a" before "programmable", and cuts the "where AI agents can…" clause. The meaning is preserved, but the wording is not verbatim. |

Suggested corrected wording for the guide:
> The AINN Immersion Day's Additional Resources page "Deploy End-to-end 5G Network" lists *example* MCP tool names, e.g. `nrf_register_nf()`, `amf_manage_ue()`, `smf_create_session()`, `f1_setup_control()`, as ideas for abstracting 5G SBI, RAN-split (F1/E1) and reference-point (N2/N3/N4/N6) interfaces. The names are illustrative and follow no single convention. Quote: "This MCP abstraction approach transforms the static 5G network deployment into a programmable, agentic-controlled infrastructure…"

If we want `<domain>_<verb>_<resource>`, we should own it as our convention. We can note the sibling page's `r1_get_*` and `r1_set_*` prefixes as precedent.

## 6. Relevance to our governed platform (ToolConfig CRs, AgentCore Gateway, Cedar, approval attestation, pause)

All of this section is **[inference]**.

- **Nothing to integrate, only names to borrow.** The page supplies no schemas, semantics, auth or implementation. Citing it as the source of a "callable tool" catalog overstates it. Cite it as "illustrative names" (see the corrected wording above).
- **The governance gap is the whole story.** The workshop's real MCP stack is FastMCP on AgentCore Runtime plus AgentCore Gateway with `CUSTOM_JWT` and `GATEWAY_IAM_ROLE`, the same family as ours. It stops at "any authenticated client calls any tool" and adds hardcoded demo credentials and unfiltered tool loading. Cedar policy per tool, approval attestation for writes, pause, and audit are exactly what that stack lacks. The page's own vision ("AI agents can dynamically manage network functions") is the case for them.
- **Risk tiers for ToolConfig CRs.** The R/W column in section 2 gives a starting point:
  - read: `n2_ngap_monitor`, `n3_gtp_tunnel`, `interface_health_check`, `fault_detection`
  - high-impact writes: `nrf_register_nf`, `amf_manage_ue`, `smf_create_session`, `udm_subscriber_data`, `f1_setup_control`, `e1_bearer_setup`, `cu_split_config`, `n4_pfcp_control`, `n6_data_network`, `network_slice_management`, `resource_optimization`, `lmf_location_services`, `nef_api_exposure`
  - medium writes: the traffic and test tools
- **Split coarse verbs.** Names like `*_manage_*`, `*_control`, "Register/deregister" and "Establish/modify" hide destructive operations behind one tool. Cedar can only permit reads and gate writes if each tool is one verb, e.g. `nrf_register_nf` / `nrf_deregister_nf`, or `smf_create_session` / `smf_modify_session` / `smf_release_session`.
- **Naming constraint [sibling]:** Gateway tool names were "shortened to meet the 64-character limit" (Module 7). Keep `<domain>_<verb>_<resource>` names short.

## 7. Method and access notes

- **What WebFetch saw:** only "Workshop Studio", because the page is a JavaScript single-page app. I resolved the content as follows:
  1. `catalog.workshops.aws/settings.json` gave `staticContentEndpoint`.
  2. `/public/quicklinks/ai-native-networks/published.json` gave the build id.
  3. `/public/<build>/manifest.json` gave the navigation tree.
  4. `/public/<build>/content/…/index.en.md` gave the page source.
  All were anonymous HTTPS GETs with no AWS credentials or CLI.
- **Sub-pages:** none. In the manifest this node is a leaf.
- **Not inspected:**
  - the OAI `case3` chart contents. I don't know which NFs actually deploy; the pod list above is what the script greps for.
  - the Module 2/3 notebooks beyond a keyword search for transport and auth.
- **Where the notebook and script copies came from:** I read the `.ipynb` and `generate_interface_map.sh` copies that another subagent had downloaded into `raw/assets/`. I cite their public S3 URLs above, and I executed nothing.
- **Files I created** in the shared `scratchpad/ainn/raw/` (another subagent writes there too; I deleted nothing):
  - `page.html`, `main.js`, `settings.json`, `published.json`, `manifest.json`
  - `agentic-core.en.md`
  - `eks-base-infra.png`, `visual-network-architecture-module3.png`
  - `root.en.md`, `introduction.en.md`, `summary.en.md`
  - `module2-r1-mcp.en.md` … `module7-agentcore-gateway.en.md`
  - `module9-additional-resources*.en.md`

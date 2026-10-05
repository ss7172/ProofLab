# AI Native Networks Immersion Day: "Additional Resources" section (module9), except the two excluded pages

Researched 2026-10-05. Read-only: anonymous HTTPS GETs of public workshop pages and assets, plus the public GitHub API. No AWS API calls, no git.
Excluded on purpose (other subagents cover them): `module9-additional-resources/module3-agentic-core` ("Deploy End-to-end 5G Network") and the workshop landing page. **I did not fetch either.**
Labels: **[VERBATIM]** = quoted from source. **[FACT]** = observed directly. **[INFERENCE]** = my reading.

---

## 0. How to read this workshop (important for the other subagents)

**[FACT]** `https://catalog.workshops.aws/ai-native-networks/...` is a JavaScript single-page app. WebFetch and curl get only the shell (`<title>Workshop Studio</title>`, an empty `#root`), with no content and no links.

**[FACT]** The content is public and can be fetched without authentication. This chain comes from the app bundle's own loader code:
1. `https://catalog.workshops.aws/settings.json` returns `"staticContentEndpoint": "static.us-east-1.prod.workshops.aws"`
2. `https://static.us-east-1.prod.workshops.aws/public/quicklinks/ai-native-networks/published.json` returns `{"current":"c5491468-dbcf-44c0-aa99-4cd7265be03f","currentV2":{"buildId":"c5491468-…","requiresAuth":false,…},"metadata":{"title":"AI Native Networks Immersion Day",…}}`
3. Manifest (the full navigation tree): `https://static.us-east-1.prod.workshops.aws/public/c5491468-dbcf-44c0-aa99-4cd7265be03f/manifest.json`
4. Raw page markdown: `https://static.us-east-1.prod.workshops.aws/public/c5491468-dbcf-44c0-aa99-4cd7265be03f/content/<path>/index.en.md`
   - The excluded 5G page is at `…/content/module9-additional-resources/module3-agentic-core/index.en.md`. Not fetched by me.
   - The excluded landing page is at `…/content/index.en.md`. Not fetched by me.
- The build ID can change when the workshop is republished. `published.json` is the stable entry point.
- Workshop asset bucket: `https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/508f04dc-026a-4260-ac15-c6f011d50cf9/<file>`. The prefix matches the manifest's `contentGuideId`.

My raw copies (scratchpad, evidence only): `/private/tmp/claude-501/-/ca14fa49-a079-47de-a9fb-a38b37dcff99/scratchpad/ainn/raw3/` contains `*.md` page sources, `manifest.json`, `published.json`, and `asset_*` files. Nothing was executed.

---

## 1. Section map (from manifest.json; order as in the navigation)

Catalog URLs below are built from the manifest paths. They were not fetched one by one, because the SPA returns an empty shell; the raw `.md` files were fetched instead.

| # | Title (manifest) | Catalog URL | Front-matter weight | Read? |
|---|---|---|---|---|
| — | Additional Resources (section index) | https://catalog.workshops.aws/ai-native-networks/en-US/module9-additional-resources | 50 | yes |
| 1 | Building Intelligent rApps with Agentic Networks Framework | …/en-US/module9-additional-resources/module5-mcp-quickstart | 35 | yes, plus its notebook asset |
| 2 | Agentic Network Framework | …/en-US/module9-additional-resources/module1-agentic-network-framework | 39 | yes |
| 3 | Network Digital Twins | …/en-US/module9-additional-resources/module2-digital-twin | 40 | yes |
| 3a | Deploy Digital Twin Backend | …/module2-digital-twin/infra | 23 | yes |
| 3b | Deploy RIC Algorithm Development Platform | …/module2-digital-twin/radp | 25 | yes |
| 3c | Deploy Sample rApp | …/module2-digital-twin/apps | 80 | yes |
| 3d | Cleanup | …/module2-digital-twin/cleanup | 90 | yes |
| 4 | **Deploy End-to-end 5G Network** | …/en-US/module9-additional-resources/**module3-agentic-core** | n/a | **NO (excluded)** |
| 5 | Deploy Non-RT RIC | …/en-US/module9-additional-resources/module4-nonrtric | 50 | yes, plus its scripts |

Note: the URL slugs do not match the titles. "module3-agentic-core" is the 5G network page, and "module5-mcp-quickstart" is listed first.

**Main workshop modules (titles from the manifest only; I did NOT read these pages):** Getting Started; M1 "Set Up Development Environment with Amazon SageMaker Studio"; **M2 "Deploy R1 MCP Server with AgentCore Runtime"**; **M3 "Deploy O2 MCP Server with AgentCore Runtime"**; M4 "Connect Local Agent to MCP Servers with Strands SDK"; M5 "Deploy Agent to AgentCore Runtime"; M6 "Add Persistent Memory to Agent with AgentCore Memory"; **M7 "Integrate AWS Lambda Functions as MCP Tools with AgentCore Gateway"**; Cleanup Account; Additional Resources; Summary.
**[INFERENCE]** M2, M3 and M7 are where the workshop's own MCP tool definitions most likely live. M7 is the obvious match for "tools behind a governed gateway". They are worth a check if the guide's citation does not hold up.

---

## 2. Where the "Deploy End-to-end 5G Network" content lives

- **[FACT]** Manifest entry: `"path": "/module9-additional-resources/module3-agentic-core"`, `"resource": "/content/module9-additional-resources/module3-agentic-core/index.en.md"`, `"title": "Deploy End-to-end 5G Network"`, with no child pages.
- **[VERBATIM]** The section index describes it like this:
  > "**End-to-End 5G Network:** Orchestrate a complete 5G network using OpenAirInterface (OAI) on Amazon EKS. Abstract critical network functions—AMF, SMF, UPF, and RAN split architectures—through programmable interfaces that AI agents can control dynamically."
- The full index text **[VERBATIM]**:
  > "This section provides a series of additional resources that may help builders exploring AI-native networks use cases, including:
  > - **Network Digital Twins:** Deploy a predictive RF coverage system using the Linux Foundation's Maveric project. Train AI models on historical signal measurements from Tokyo cell towers to predict radio frequency strength at any location, with incremental learning capabilities.
  > - **End-to-End 5G Network:** [as above]
  > - **Open RAN Sandbox:** Deploy non-real time RIC to showcase sample O-RAN use cases."
- **[FACT]** OAI is named only in that one sentence of the sibling pages. Open5GS, free5GC and UERANSIM do not appear anywhere in the pages I read or in the notebook.
- **[FACT]** None of the sibling pages, the QuickStart notebook or the downloaded scripts contain any 5G-core tool name (no `amf_*`, `smf_*`, `upf_*`, `nrf_*` and so on). Every MCP tool name in this section is on the RAN/O-RAN side (§4).
- **[FACT] Naming collision to be aware of:** the Non-RT RIC page uses "AMF" to mean CAPIF's **API Management Function**, not the 5G-core **Access and Mobility Management Function**. **[VERBATIM]** "Use Case 1: rApp Manager Registration as AMF (API Management Function)", with `apiProvFuncRole: "AMF"`. A naming convention built by grepping this workshop for "AMF" would pick up the wrong one.
- **Status of the guide's citation:** the sibling pages do not contain a 5G-core-as-MCP-tools naming convention. Whether module3-agentic-core itself defines one has to be checked against that page. I am not claiming the guide is wrong. **[INFERENCE]** The closest documented "naming convention" in this section is the RAN-side prefix table on the "Agentic Network Framework" page (§4). That page explicitly lists "Tool naming conventions" as a learning objective, so the guide may have mixed up the two pages.

---

## 3. Page-by-page summaries

### 3.1 Building Intelligent rApps with Agentic Networks Framework (`module5-mcp-quickstart`)
- **What it is:** a 35-minute tutorial notebook that acts as a client of an MCP server. **[VERBATIM]** "interact with a local MCP server that provides 63 tools across three categories: VIAVI Simulation, O-RAN R1 Interface, and SafeLoop Knowledge Graph."
- **It builds no infrastructure.** **[VERBATIM]** "**IMPORTANT: MCP Server Required** … 1. **Build your own MCP server** using the techniques from Modules 2-3 (R1/O2 MCP servers deployed to AgentCore Runtime) 2. **Find a public MCP server** online that provides RAN simulation tools … expects the MCP server to be accessible at `http://localhost:8090/sse` … **Without a running MCP server, this tutorial cannot be completed.**"
- Notebook download (public, fetched): `…/508f04dc-…/MCP_Server_35min_QuickStart.ipynb` (69 KB, Last-Modified 23 Oct 2025, 38 cells).
- Tracks: A, the VIAVI simulation lifecycle; B, O-RAN R1 (SL/PM/DM/QM/FM); C, the SafeLoop knowledge graph. Module 3 is a closed-loop antenna-tilt demo (baseline, then tilt change, then compare average RSRP).
- **Notebook details [FACT]:**
  - The notebook header says **[VERBATIM]** "Environment: Amazon Bedrock AgentCore Runtime + MCP Server". It also says "Each RAN Application Function follows schema-based definitions with **secure authentication**". However, the client is `sse_client("http://localhost:8090/sse")` over plain HTTP, with no headers, token or authentication of any kind.
  - The architecture diagram shows AgentCore Runtime → "Your rApp" → MCP server (`localhost:8090 / Cloud`) → "O-RAN Live Network (A1/O1/O2/R1 Endpoints)".
  - **Recorded outputs saved in the notebook** (the author's own run): "Found **59** tools", made up of VIAVI 4, R1 39 and Other 16 (examples `create_network_slice`, `list_network_slices`, `get_slice_status`). Also "VIAVI Available: **False**", "SafeLoop Available: **False**", and "Tool get_server_health not listed by server, cannot validate any structured content".
  - The appendix promises "All 63 MCP Tools Documented" but documents only **6** (`viavi_create_scenario`, `viavi_start_simulation`, `viavi_run_for`, `viavi_finish_simulation`, `viavi_list_simulations`, `viavi_get_simulation_status`). Each has input and output schemas plus "Common Errors".
  - Tools actually called: `get_server_health`, `viavi_create_and_store_scenario` (modes `intent` / `clone`), `viavi_start_simulation_from_scenario` (`force_start`, `offline`), `viavi_run_for`, `viavi_query_data` (tables `UEReports`, `CellReports`), `viavi_finish_simulation`, `viavi_antenna_tilt`, `viavi_query_scenarios` (`search_type: HYBRID_NATURAL_LANGUAGE`), `viavi_get_scenario_details`, `viavi_find_similar_scenarios`, `r1_create_scenario`, `r1_list_scenarios`. Described in print statements only: `r1_get_cell_config`, `r1_set_cell_config`, `r1_get_infrastructure`, `r1_get_network_topology`, `r1_get_active_alarms`, `r1_subscribe_alarms`.
- Governance or evidence content: none, beyond the "secure authentication" claim, which nothing in the client code supports. The client shows no authentication, though that does not prove the server has none.

### 3.2 Agentic Network Framework (`module1-agentic-network-framework`), the richest page
- It documents a notebook, `AWS_RAF_Developer_Guide.ipynb`. **[VERBATIM]** "**Target Audience**: AWS Hackathon participants, rApp developers, 5G/O-RAN engineers"; "**Total Tools**: 105 MCP tools across 11 categories"; footer: "This guide is designed for the AWS Hackathon…". "Version 1.0, Last Updated 2025-10-29".
- **The page does not offer the notebook for download.** The guessed asset URL returns 403 (§6).
- **MCP server provenance [FACT]:** the server is started with `poetry run python -m maveric.services.mcp_server.server`, run from a developer's personal checkout (`/Users/<author>/Projects/Maveric`). Expected log: "Loaded 105 tools", "Connected to Neo4j (graph database)", "Connected to Cognee (knowledge graph)". **No `mcp_server` exists in public `lf-connectivity/maveric`.** I checked the `main` branch tree (334 entries) and the 2 patch branches, plus 3 recently pushed forks. None contain mcp, safeloop, viavi or cognee paths.
- **Tool-category / naming table [VERBATIM]:**

| Category | Prefix | Tools | Purpose |
|---|---|---|---|
| R1 Performance Management | `r1_get_*`, `r1_subscribe_*` | 15+ | Query cell/UE KPIs, RSRP, SINR, throughput |
| R1 Configuration | `r1_set_*` | 12+ | Modify TX power, tilt, azimuth, handover params |
| R1 Simulation Lifecycle | `r1_create_*`, `r1_start_*` | 10+ | Create scenarios, start/stop simulations |
| SafeLoop Search | `safeloop_search`, `safeloop_cypher` | 5+ | Knowledge graph queries (auto-routing) |
| Cognee Knowledge Graph | `cognee_*` | 20+ | Add data, search, retrieve relationships |
| VIAVI Simulation | `viavi_*` | 15+ | Direct simulator control (advanced) |
| Schema & Ontology | `get_schema`, `get_ontology` | 8+ | Explore data models, RDF ontologies |
| Decision Provenance | `track_decision`, `get_audit_trail` | 6+ | EU AI Act compliance, explainability |
| System | `health_check`, `get_version` | 4+ | Server status, diagnostics |
| File Operations | `read_file`, `write_file` | 3+ | Access server-side files |
| Utilities | `validate_config`, `format_data` | 7+ | Helper functions |

- Other tool names used in the code: `r1_get_cell_kpis`, `r1_get_ue_kpis`, `r1_subscribe_cell_kpis`, `r1_get_cell_config`, `r1_set_cell_tx_power`, `r1_set_cell_config`, `r1_set_cell_tilt`, `r1_set_cell_azimuth`, `r1_set_cell_state` (`energy_saving`), `r1_set_handover_margin`, `r1_set_cell_config_batch`, `r1_create_scenario` (modes `intent` (described as "requires LLM API key"), `file`, `yaml`, `parameters`), `r1_upload_scenario`, `r1_start_simulation`, `r1_get_simulation_status`, `r1_pause_simulation`, `r1_resume_simulation`, `r1_export_simulation`, `r1_stop_simulation`, `r1_delete_scenario`, `r1_get_scenario`, `cognee_add`, `generate_audit_report`, `list_tools`.
- Realistic reference data, useful for mocks: a KPI table (RSRP −140 to −44 dBm, good above −80; SINR −10 to 30 dB; PRB utilization 0–1, poor above 0.9) and a config table (TX power 0–46 dBm, default 43; tilt −10° to +10°; azimuth 0–360°; frequency 600–6000 MHz; bandwidth 5–100 MHz; handover margin 0–10 dB, default 3). It also gives a knowledge-graph schema (Cell/UE/Site/Scenario/Simulation/KPI, with SERVES / NEIGHBORS / INTERFERES_WITH / ATTACHED_TO …).
- Workflow templates: coverage optimization ("Ottawa Trial"), interference mitigation (azimuth), energy saving (cell state), and handover optimization (ping-pong).
- **Governance, security and evidence content [VERBATIM, with my notes]:**
  - The "🔐 Security and Compliance / EU AI Act Compliance" section maps tools to Articles 12 to 15:
    - Art. 12: "All MCP tool calls are automatically logged. Includes: timestamp, tool name, arguments, results, duration". This is shown only as a code comment. No mechanism is shown.
    - Art. 13: `track_decision` with SHAP `feature_contributions`.
    - Art. 14: "Human Oversight".
    - Art. 15: `generate_audit_report(start_time, end_time, decision_types)`.
  - `track_decision` payload: `decision_type`, `input_state{rsrp,sinr,tilt}`, `action{parameter, old_value, new_value}`, `rationale`, `outcome{…}`, plus optional `location` and `timestamp`.
  - **The live-change guard is a single boolean argument [FACT]:** `r1_set_cell_tx_power {"cell_id": "ottawa_cell_001", "tx_power_dbm": 46.0, "apply_to_live": True}  # ⚠️ Live network change!` The simulation tool and the live tool are the same tool. Rollback is done by calling the same tool with the old value.
  - **The human-oversight gate is inverted [FACT]:** the "Article 14: Human Oversight" snippet is `if improvement < THRESHOLD: print("❌ Improvement insufficient - requires manual approval") … return`. In the workflow, an improvement of at least 2.0 dB goes straight to `apply_to_live: True` with no approval step. So a human is alerted only for changes that are *not* applied. The "Production Deployment Checklist" does list "Get approval for live network changes" and "Schedule maintenance window", but the code does not implement them.
  - **The decision record is self-reported and written after the fact [FACT]:** `track_decision` runs after the live change and after 10 minutes of monitoring. The client (agent or rApp) calls it voluntarily. The record has no actor identity, no approver and no request or trace ID.
  - Other surface worth noting: `read_file` / `write_file` ("Access server-side files"), and `safeloop_cypher`, which passes arbitrary caller-supplied Cypher.
  - Best practices listed: test in simulation before live, implement rollback, log live changes, track all decisions.
- Transport: SSE on `localhost:8090`, "Fresh connection per call", a 600-second timeout ("Scenario creation: 5-10 minutes"), and no authentication.

### 3.3 Network Digital Twins (`module2-digital-twin`), with infra, radp, apps and cleanup
- **[VERBATIM]** "build a digital twin of a cellular network that can predict radio frequency signal strength at any location by training an AI model on historical signal measurements from 3 cell towers in Tokyo". Credits the LF Maveric project's RIC Algorithm Development Platform (RADP).
- **infra:** commands are run in CloudShell. It creates a VPC (10.0.0.0/16) with a public subnet (10.0.1.0/24) and an IGW. The security group allows 22, 8888 and 443 **only from `$MY_IP/32`**. It launches a **g5.2xlarge** from the "Deep Learning OSS Nvidia Driver AMI GPU TensorFlow 2.18 (Ubuntu 22.04)", with 100 GB gp3 and a `radp-workshop-key` key pair.
- **radp:** `git clone https://github.com/lf-connectivity/maveric.git`, then `docker build -f radp/Dockerfile-cuda …` and `docker compose -f dc.yml -f dc-prod.yml -f dc-cuda.yml up -d --build`. This brings up 6 containers: training, ue_tracks_generation, api_manager (`8080->5000`), rf_prediction, orchestration and kafka (`9094`).
  - **[INFERENCE]** `sudo apt-get install -y docker` installs the wrong Ubuntu package (Docker Engine is `docker.io`). It works anyway only because the DLAMI already ships Docker.
- **apps:** runs the Mobility Robustness Optimization notebook (`mro.ipynb`) through papermill ("30+ minutes"). It uses Bayesian Digital Twin RF models, with random/grid search, Bayesian optimization or RL tuning of hysteresis and TTT. Further use cases are only described: load-balancing CCO (RL tilt), energy savings (sector on/off), RF digital twin plus CCO, Gauss-Markov mobility, and traffic demand.
- **cleanup:** `aws ec2` teardown of the above.
- **AI interaction:** classical ML/RL only. There are no LLM agents, no MCP and no governance content (apart from the IP-restricted security group).

### 3.4 Deploy Non-RT RIC (`module4-nonrtric`)
- **[VERBATIM]** "deploy the O-RAN Software Community (OSC) Non-Real Time RAN Intelligent Controller (Non-RT RIC) on AWS using CodeBuild and EKS." Expected time is about 60 minutes.
- **Option 1, `deploy-osc.sh` (fetched, 4.9 KB, not executed):**
  - It first deletes any existing CodeBuild project `agentic-oran-build` and IAM role `CodeBuildAgenticOranRole`, then recreates the role.
  - The role gets AWSCodeBuildDeveloperAccess, AmazonEKSClusterPolicy, AmazonEKSWorkerNodePolicy, AmazonEKS_CNI_Policy, AmazonEC2ContainerRegistryReadOnly, **AmazonEC2FullAccess, IAMFullAccess, AWSCloudFormationFullAccess**, CloudWatchLogsFullAccess, plus inline `eks:*` on `*` and a logs policy.
  - It creates the CodeBuild project with `privilegedMode=true` and `--source file://source-config.json`, then starts the build.
- **Inline buildspec** (from the public `source-config.json` / `buildspec.yml` assets, which are identical):
  - EKS **1.32** cluster `agentic-oran-osc`, 6 × t3.large managed nodes, OIDC, EBS CSI addon.
  - `git clone --recursive https://gerrit.o-ran-sc.org/r/it/dep`, then `smo-install` layer-0 (ChartMuseum, Helm 3), layer-1 (`1-build-all-charts.sh`) and layer-2 (`2-install-oran.sh rappmanager`).
  - Post-build checks the `nonrtric` namespace and the `oran-nonrtric-kong-proxy` service. `REGION: us-east-1` is **hardcoded**.
- **Option 2:** `deploy-rapp.sh` (the energy-saving rApp). **Asset returns 403** (missing or not public), so it can't be obtained. The page defers to the OSC repo's `es-demo-rapp` instructions.
- **Access:** an EKS access entry with **AmazonEKSClusterAdminPolicy** for the caller's role.
- **Callflows, documentation only [VERBATIM]:**
  - CAPIF registration ("rApp Manager … as AMF (API Management Function)", `regSec: "PSK"`).
  - ONAP ACM participants (A1PMS, HTTP, K8s, KServe, Policy, DME) over Strimzi Kafka.
  - Information Service producer/consumer through **Kong Gateway** (`/data-producer/*`, `/data-consumer/*` → `informationservice:9082`).
  - A1 policy lifecycle `PUT /a1-policy/v2/policies/{policyId}`, routed by Kong to `policymanagementservice:8081`, validated by ONAP `policy-api`, exposed on NodePort 30094/30095.
  - CAPIF API publication, with "Security Management" among the CAPIF services.
- **AI interaction:** none on this page. The resources are named "agentic-oran", but no agent, LLM or MCP is involved.
- **Governance-relevant elements:** A1 policy API, CAPIF provider registration, and Kong as the API gateway for O-RAN services.

---

## 4. MCP tool counts disagree across sources (all in this one section)

| Source | Claimed tool count |
|---|---|
| Agentic Network Framework page | **105** tools / 11 categories |
| QuickStart page and notebook text | **63** tools (VIAVI 21, R1 10 or "15+", SafeLoop 12 or "10+", other 20) |
| QuickStart notebook's saved run output | **59** tools (VIAVI 4, R1 39, Other 16); VIAVI and SafeLoop backends `False` |
| QuickStart notebook appendix | documents **6** |

The naming pattern is the same across all sources: `<interface/backend>_<verb>_<object>` (`r1_get_cell_kpis`, `r1_set_cell_tx_power`, `viavi_run_for`, `safeloop_cypher`, `cognee_*`). Provenance and system tools have no prefix. The O-RAN interfaces named are R1, A1, O1 and O2. The 5G core is not covered.

---

## 5. Page and asset defects (Non-RT RIC)
- The access-entry block uses `$CLUSTER_NAME`, which is never set. The cluster is `agentic-oran-osc`.
- The page says `./deploy-osc.sh $REGION`, but the script ignores the region argument (`$1` is only checked for `--codebuild-only`, which is then never used). The buildspec hardcodes `us-east-1`.
- `deploy-osc.sh` needs `source-config.json` in the current directory, but the page never says to download it. It is public at `…/508f04dc-…/source-config.json`.
- The cleanup step runs `wget …/cleanup-regional.sh`, which returns **403** (missing or not public), then `chmod +x cleanup-nonrtric.sh` and `./cleanup-nonrtric` (no `.sh`). The real file `…/cleanup-nonrtric.sh` exists (200). It deletes the CodeBuild project, runs `eksctl delete cluster agentic-oran-osc`, and removes the IAM role and its policies.
- The section index lists 3 items (Digital Twins, E2E 5G, Open RAN Sandbox), but the navigation has 5 children. The two MCP/rApp pages are not mentioned in the index.

## 6. Inaccessible or unavailable
- `deploy-rapp.sh`: 403. Without bucket-listing rights, an anonymous 403 means either missing or not public; the two can't be told apart. Either way, the page tells participants to wget it.
- `cleanup-regional.sh`: 403, same caveat (but `cleanup-nonrtric.sh` is OK).
- `AWS_RAF_Developer_Guide.ipynb`, `R1_MCP_Tools_Tutorial.ipynb`, `RAF_Developer_Complete_Guide_FULLY_FIXED.ipynb`: 403 at the guessed asset-bucket path (one location probed). Their absence from the bucket is not proven. What is certain is that the Agentic Network Framework page names them but gives no download link.
- **MCP server source (105/63/59-tool RAF server):** not public. It is absent from lf-connectivity/maveric (main and patch branches) and from 3 recent forks.
- VIAVI AI-RSG is a commercial simulator. The saved notebook output shows it unavailable even in the author's run.
- The image assets (`/static/digital-twin.png`, `/static/maveric.png`) were not fetched because they are not needed.
- Not fetched by design: the module3-agentic-core page and the landing page.

---

## 7. What a hackathon team could reuse for realistic network-function tools behind a governed gateway (all [INFERENCE])

1. **The naming pattern, not the server.** Use the documented `<interface>_<verb>_<object>` scheme (`r1_get_*` / `r1_set_*` / `r1_create_*` / `*_delete_*`). The verb tells the gateway whether a call reads or changes something, so policy can follow it: allow `get`/`list`/`query`, and gate `set`/`create`/`delete`/`apply`. Any `amf_*`/`smf_*`/`upf_*` tool names would be the team's own design (or come from module3 if that page defines them). This section does not provide them. Avoid "AMF" ambiguity (CAPIF vs 5GC).
2. **Realistic schemas for mock tools.** The KPI and config tables (value ranges and defaults), the `viavi_query_data` table and field names (`Viavi.UE.Rsrp`, `Viavi.Cell.PRBUtil` …), the 6 fully specified appendix schemas, the R1-FM alarm severities, and the A1 policy paths and Kong routes are enough to build convincing stub tools (Lambda or AgentCore Gateway targets) without running OAI, VIAVI or a 60-minute EKS RIC.
3. **The `track_decision` record shape as an evidence schema.** Fields: `decision_type`, `input_state`, `action{parameter, old_value, new_value}`, `rationale`, `outcome`, and optional feature contributions. To be real evidence it needs to be captured by the gateway rather than self-reported by the agent, written **before** the action as well as after, and to carry actor, approver and trace IDs. The workshop's version has none of these.
4. **A ready-made "before and after" governance story.** The page's own coverage workflow puts a live network change behind a single `apply_to_live: True` flag. Its "Human Oversight" gate fires only when the change is *rejected*, and its audit record is optional and written after the change. A governed gateway that intercepts live write calls (requiring approval, a dry-run in simulation first, and automatic rollback evidence) directly fixes that cited pattern.
5. **Do not take a live dependency on any of this infrastructure.** Each piece is too slow, too expensive or unavailable for a hackathon:
   - Non-RT RIC: about 60 minutes, 6 × t3.large, plus an IAMFullAccess CodeBuild role.
   - RADP: g5.2xlarge GPU, with MRO taking 30+ minutes.
   - The MCP server: not published.
   - VIAVI: commercial.
   The Kong-fronted A1 policy API and CAPIF are good *shapes* to mock.

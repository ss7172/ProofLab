# AI Native Networks Immersion Day: workshop map and relevance

Retrieved 2026-10-05. Read-only web research. No AWS API calls; every fetch was an unauthenticated HTTPS GET of public content.
Tags: **[Obs]** means I read it in the source. **[Inference]** is my interpretation. **[Workshop claim]** is the workshop's own statement, which I did not check against AWS.

---

## 0. How to access it (the catalog page looks empty, but it is not gated)

- `https://catalog.workshops.aws/ai-native-networks/en-US` and every sub-path are a JavaScript SPA. With WebFetch the page shows only the title "Workshop Studio". I tried the root and `/module9-additional-resources/module2-digital-twin/infra`. **No login is needed.** The SPA loads its content from a public static endpoint:
  - Build pointer: `https://static.us-east-1.prod.workshops.aws/public/quicklinks/ai-native-networks/published.json` returns `"requiresAuth":false`, buildId `c5491468-dbcf-44c0-aa99-4cd7265be03f`, with title and description: *"Learn how AWS Global Infrastructure and AWS generative AI services allow developers to rapidly develop, deploy and scale AI-native networks in the cloud."*
  - Manifest (the table of contents): `https://static.us-east-1.prod.workshops.aws/public/c5491468-dbcf-44c0-aa99-4cd7265be03f/manifest.json`
  - Raw page markdown: `https://static.us-east-1.prod.workshops.aws/public/c5491468-dbcf-44c0-aa99-4cd7265be03f/content/<path>/index.en.md`
  - Downloadable assets (notebooks and scripts): `https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/508f04dc-026a-4260-ac15-c6f011d50cf9/<file>`
- All 21 pages returned HTTP 200. Of the assets, these returned 403: `deploy-rapp.sh`, `cleanup-regional.sh`, `contentspec.yaml` (also 403 under `/static/`). Without `contentspec.yaml` the Workshop Studio event participant-role config cannot be seen.
- Local raw captures (pages, assets, diagrams) are in `/private/tmp/claude-501/-/ca14fa49-a079-47de-a9fb-a38b37dcff99/scratchpad/ainn/raw/`:
  - `md__content__*.md`: pages
  - `assets/`: notebooks and scripts; `assets/gwzip/` holds the unzipped gateway starter code
  - `img/`: architecture PNGs
  - **Ownership:** this report's files are only `manifest.json`, `md__content__*`, `assets/` and `img/`. Other files in `raw/`, plus `../raw3/`, belong to a sibling agent: the `*.en.md` files without the `md__` prefix, `agentic-core.en.md`, and the top-level `eks-base-infra.png`.

---

## 1. Checking our kit's claims

| Kit claim | Verdict | Evidence |
|---|---|---|
| Runs the **same RADP** (Linux Foundation MAVERIC) | **Confirmed** [Obs] | `git clone https://github.com/lf-connectivity/maveric.git` (…/module2-digital-twin/radp) |
| On a **participant-launched g5.2xlarge Deep Learning AMI** | **Confirmed** [Obs] | `--instance-type g5.2xlarge` and AMI filter `"Deep Learning OSS Nvidia Driver AMI GPU TensorFlow 2.18 (Ubuntu 22.04) 20250531"`. The launch also uses a 100 GB gp3 root, a public subnet, and key pair `radp-workshop-key` (…/module2-digital-twin/infra) |
| Using **RADP's CUDA path** | **Confirmed** [Obs] | `docker build -f radp/Dockerfile-cuda -t radp radp` and `docker compose -f dc.yml -f dc-prod.yml -f dc-cuda.yml up -d --build` (…/radp) |
| **Grants participants AdministratorAccess** | **Not found** in any public page or script [Obs] | No page or downloadable script mentions `AdministratorAccess`. Getting Started only asks for *"an IAM user that has sufficient permissions to create, modify and delete resources across Amazon SageMaker, Amazon VPC, Amazon EC2, AWS IAM, AWS Lambda, Amazon S3 and Amazon Bedrock AgentCore"*. The nearest match is `deploy-osc.sh` (Non-RT RIC), which creates `CodeBuildAgenticOranRole` with **IAMFullAccess + AmazonEC2FullAccess + AWSCloudFormationFullAccess** (plus EKS, CodeBuild and Logs policies). [Inference] IAMFullAccess is admin-equivalent because it allows privilege escalation. The kit's claim may come from an event-hosted participant role defined in `contentspec.yaml`, which returns 403, so I can neither confirm nor refute it. |

Twin dataset per the workshop: *"training an AI model on historical signal measurements from 3 cell towers in Tokyo"* (…/module2-digital-twin).

---

## 2. Module map

Catalog base: `https://catalog.workshops.aws/ai-native-networks/en-US`. The raw markdown for each page is at the same path under the static base in §0.

Overview text (`/`): *"~2 hour"*. *"we will create AI agents through Amazon Bedrock AgentCore that simulate the management of Radio Access Networks through standardized O-RAN interfaces … build Model Context Protocol (MCP) servers for the R1 and O2 interfaces … layer in an overarching agent to simulate the SMO, followed by integrating memory capabilities and broader MCP server access through AgentCore Gateway."* Recommended Region: **us-east-1**.

### Core track (about 2 h, participant's own account)

| # | Title | Path | What it builds |
|---|---|---|---|
| – | Getting Started | `/introduction` | Prerequisites (IAM user permissions, CloudShell or IDE), us-east-1 |
| 1 | Set Up Development Environment with Amazon SageMaker Studio | `/module1-sagemaker` | SageMaker domain (quick setup) and JupyterLab space. Runs `update-sagemaker-studio-permissions.sh` in CloudShell, which adds 12 inline policies to the SageMaker execution role (see §5) |
| 2 | Deploy R1 MCP Server with AgentCore Runtime | `/module2-r1-mcp` | `r1-mcp-server.ipynb` builds a FastMCP server (`stateless_http=True`, streamable-http) around an **in-memory mock** R1 (SMO↔Non-RT RIC rApp lifecycle) and deploys it to AgentCore Runtime. Adds a Cognito JWT authorizer, an auto-created ECR repo, CodeBuild, and SSM params `/mcp_server/r1/runtime/{agent_arn,client_id}` |
| 3 | Deploy O2 MCP Server with AgentCore Runtime | `/module3-o2-mcp` | `o2-mcp-server.ipynb` does the same for an **in-memory mock** O2 IMS (O-Cloud inventory, subscriptions, alarms) |
| 4 | Connect Local Agent to MCP Servers with Strands SDK | `/module4-local-agent` | Local `agent.py`: a Strands `Agent` with a `BedrockModel` and two `MCPClient`s. It looks up the server ARN and client_id in SSM, gets a Cognito token, and calls `https://bedrock-agentcore.<region>.amazonaws.com/runtimes/<arn>/invocations`. System prompt: "O-RAN SMO Planner Agent" |
| 5 | Deploy Agent to AgentCore Runtime | `/module5-deploy-agent` | `deploy_strands_agent.py` uses `bedrock_agentcore_starter_toolkit.Runtime` to deploy `oran_agent` with a Cognito JWT authorizer and stores config in SSM and Secrets Manager. `ssm-agentcore-permissions.sh` grants the agent role SSM read and AgentCore Memory permissions. `test_agent.py` invokes the agent |
| 6 | Add Persistent Memory to Agent with AgentCore Memory | `/module6-agent-memory` | `memory_agent.py` is deployed as `oran_agent_memory`. It creates memory "ORANAgentMemory" with a `semanticMemoryStrategy` "ORANTracker", namespace `oran/{actorId}/operations` and `event_expiry_days=90`. A `MemoryHookProvider` loads the last 5 turns. actor_id is `oran_operator_001` |
| 7 | Integrate AWS Lambda Functions as MCP Tools with AgentCore Gateway | `/module7-agentcore-gateway` | `multi-target-gateway.ipynb` deploys 10 **mock** telecom Lambdas as Gateway targets with inline tool schemas. Inbound auth is Cognito M2M with `CUSTOM_JWT`; outbound auth is `GATEWAY_IAM_ROLE`. Includes a Strands agent test |
| – | Cleanup Account | `/module8-cleanup` | `cleanup-module1.sh`. **Dangerous in a shared account** (see §6) |
| – | Additional Resources (index) | `/module9-additional-resources` | Lists the optional tracks below |
| – | Summary | `/summary` | Bonus RAF notebook link, plus links to the Orange "AI for networks" blog (MWC 2025), the AWS Telecom Smart-X agents blog, and Outposts for Cloud RAN |

### Additional resources (optional, much heavier)

| Title | Path | What it builds |
|---|---|---|
| Building Intelligent rApps with Agentic Networks Framework | `/module9-additional-resources/module5-mcp-quickstart` | 35-min `MCP_Server_35min_QuickStart.ipynb` against an MCP server at `http://localhost:8090/sse` exposing *"63 tools across three categories: VIAVI Simulation, O-RAN R1 Interface, and SafeLoop Knowledge Graph"*. *"Without a running MCP server, this tutorial cannot be completed."* The workshop does not provide this server |
| Agentic Network Framework | `/module9-additional-resources/module1-agentic-network-framework` | Docs for `AWS_RAF_Developer_Guide.ipynb`: *"105 MCP tools across 11 categories"* on `localhost:8090`. Started with `poetry run python -m maveric.services.mcp_server.server` (Neo4j and Cognee backends). **The only page with EU AI Act, audit and approval content** (see §5) |
| Network Digital Twins | `/module9-additional-resources/module2-digital-twin` | Intro to the RADP RF twin (Tokyo data) |
| ↳ Deploy Digital Twin Backend | `…/module2-digital-twin/infra` | CloudShell CLI: VPC, IGW, public subnet, SG, key pair, g5.2xlarge on a Deep Learning AMI |
| ↳ Deploy RIC Algorithm Development Platform | `…/module2-digital-twin/radp` | SSH to EC2, clone MAVERIC, CUDA build, docker compose. Containers: `api_manager` (host 8080 to 5000), `rf_prediction`, `training`, `ue_tracks_generation`, `orchestration`, `kafka` (9094) |
| ↳ Deploy Sample rApp | `…/module2-digital-twin/apps` | Uses papermill to run `notebooks/mro.ipynb` (Mobility Robustness Optimization with Bayesian Digital Twin, random/grid, Bayesian opt and RL; *"30+ minutes"*). Also lists load-balancing CCO (RL tilt), energy savings (cell on/off plus tilt), CCO with the RADP twin, Gauss-Markov mobility, and traffic demand |
| ↳ Cleanup | `…/module2-digital-twin/cleanup` | Tears down the EC2 instance and VPC |
| Deploy End-to-end 5G Network | `/module9-additional-resources/module3-agentic-core` | eksctl cluster `oai-5g-cluster` (k8s 1.32, 6×t3.large) plus the **OpenAirInterface** `oai-cn5g-fed` Helm chart `e2e_scenarios/case3` (5GC plus CU-CP/CU-UP/DU split), about 20 min. `generate_interface_map.sh` produces the interface diagram. **It suggests MCP tool names but implements none** |
| Deploy Non-RT RIC | `/module9-additional-resources/module4-nonrtric` | `deploy-osc.sh` uses CodeBuild to create EKS `agentic-oran-osc` (6×t3.large) with **O-RAN SC Non-RT RIC** (rApp Manager, A1 PMS, CAPIF, Kong, ONAP ACM), about 60 min. Option 2 (`deploy-rapp.sh`, which returns 403) adds the energy-saving rApp. It then grants the caller `AmazonEKSClusterAdminPolicy` through an EKS access entry |

---

## 3. Architecture

### Core track [Obs]

```
SageMaker Studio (JupyterLab) / CloudShell
   │ notebooks + starter toolkit (CodeBuild → ECR)
   ▼
AgentCore Runtime: R1 MCP server (FastMCP, mock in-memory DB)  ◄── Cognito JWT (shared testuser)
AgentCore Runtime: O2 MCP server (FastMCP, mock in-memory DB)  ◄── Cognito JWT (shared testuser)
   ▲  discovered via SSM /mcp_server/{r1,o2}/runtime/{agent_arn,client_id}
   │
AgentCore Runtime: Strands agent "oran_agent" / "oran_agent_memory"
   │  model: Bedrock us.anthropic.claude-3-7-sonnet-20250219-v1:0
   └─ AgentCore Memory "ORANAgentMemory" (semantic strategy, 90-day events)

Separate (Module 7): AgentCore Gateway "SampleLambdaGateway1" (protocolType MCP, CUSTOM_JWT/Cognito M2M)
   └─ 10 Lambda targets (python3.12 mocks) via GATEWAY_IAM_ROLE → notebook Strands agent (Claude 3.7 Sonnet, temperature 0.7)
```

### Optional tracks [Obs]
- **Twin.** One EC2 g5.2xlarge in a public subnet. The SG allows 22, 8888 and 443 from `MY_IP=$(curl -s https://checkip.amazonaws.com)`. Diagram `maveric.png` shows "RIC Application Development Platform" in Docker plus an "rApp Notebook" (Jupyter).
  - [Inference] `MY_IP` is evaluated inside CloudShell, so the allowed CIDR is CloudShell's egress IP, not the participant's laptop.
  - [Inference] RADP's api_manager publishes host port 8080, which the SG does not open, so the API is reachable only from on-box notebooks.
- **5G.** EKS (diagram `eks-base-infra.png`: 3 AZs, private subnets, NAT, T3 managed nodes). The OAI interface map (`visual-network-architecture-module3.png`) shows AMF, SMF and UPF with N2/N3/N4/N6/SBI; NR-UE/gNB; a DU/CU-CP/CU-UP split over F1-C/F1-U/E1; and a traffic server.
- **Non-RT RIC.** EKS built by CodeBuild with OSC charts (layer-0/1/2).
- [Inference] **None of the optional tracks is wired to the core-track agents or MCP servers.** No page connects RADP, OAI or the Non-RT RIC to an MCP server or a Strands/AgentCore agent. The OAI page only lists ideas, and the 63/105-tool server that claims "RADP RIC framework" integration is a localhost server the workshop never deploys.

---

## 4. Models, agents, MCP tools

### Models [Obs]
- Every agent uses **Anthropic Claude 3.7 Sonnet on Amazon Bedrock** (`us.anthropic.claude-3-7-sonnet-20250219-v1:0`): `agent.py` line 62, `memory_agent.py` line 166, Module 7 Step 13.
- **No NVIDIA Nemotron and no NIM anywhere.** I grepped every page, script, notebook and the gateway zip. "NVIDIA" appears only in the DLAMI driver name and the CUDA container entrypoints. "Guardrail" appears nowhere, so Bedrock Guardrails are not used.
- The SageMaker role receives `aws-marketplace:Subscribe` on `*`. [Inference] This is for Bedrock third-party model access.

### Agents [Obs]
- `oran_agent` (Module 5), `oran_agent_memory` (Module 6), and the Module 7 notebook agent.
- `smo_planner_extended.py` is bundled in the gateway zip but not deployed. It has 24 `@tool`s: 4 "original" A1/E2/O1/O2 tools plus 10 use cases × `create_*_plan`/`execute_*`.
- All of them share the "O-RAN SMO Planner Agent" system prompt family. The prompt instructs the agent to *"Execute deployment"* and *"Execute using proper O2DMS operations"*, with **no instruction to seek confirmation**.

### R1 MCP server tools (10) [Obs, from notebook decorators]
`get_rapps`, `create_rapp`, `get_rapp`, `delete_rapp`, `prime_rapp(rapp_id, prime_order)`, `get_rapp_instances`, `create_rapp_instance`, `get_rapp_instance`, `delete_rapp_instance`, `deploy_rapp_instance(rapp_id, instance_id, deploy_order)`.
States: COMMISSIONED, PRIMED, DEPLOYED, UNDEPLOYED. Deploy and undeploy share one tool, as do prime and deprime (selected by an `*_order` argument).

### O2 IMS MCP server tools (24) [Obs]
- Inventory: `get_inventory_api_versions`, `get_monitoring_api_versions`, `get_ocloud_info`, `get_deployment_managers`, `get_deployment_manager`, `get_resource_pools`, `get_resource_pool`, `get_resources`, `get_resource`, `get_resource_types`, `get_resource_type`
- Subscriptions: `create_subscription`, `get_subscriptions`, `get_subscription`, `delete_subscription`, `create_alarm_subscription`, `get_alarm_subscriptions`, `get_alarm_subscription`, `delete_alarm_subscription`
- Alarms: `get_alarms`, `get_alarm`, `patch_alarm`, `create_test_alarm`
- Sim: `simulate_smo_registration`

Mock fixture data: "INF O-Cloud Platform", pool "RegionOne", Dell PowerEdge R740 `controller-0`, Intel Xeon E5-2670 v2, DMS `kubernetes-cluster` (native_k8sapi, 32 cores).

### Gateway Lambda tools (10) [Obs]
Each entry shows the Gateway tool name, then the Lambda name in brackets:
- `config_slice` [configure_slice_parameters]
- `deploy_a1` [deploy_a1_policy]
- `create_v2x_plan` and `exec_v2x_opt` [create_v2x_handover_plan / execute_v2x_handover_optimization]
- `create_uav_plan` and `exec_uav_alloc`
- `create_energy_plan` and `exec_energy_opt`
- `create_mimo_plan` and `exec_mimo_opt`

Target names follow `func_name.replace('_','-') + '-target'`.
- [Workshop claim] *"The script selects only priority functions due to gateway's 10-target limit"*; *"Tool names are shortened to meet the 64-character limit"*.
- [Inference, from AgentCore background knowledge] Gateway exposes tools to clients as `<target>___<tool>`. The notebook's commented code matches on `"v2x-handover" in t`, which fits that.

### Localhost "RAF" MCP server (not deployed by the workshop) [Obs]
- Tool prefixes: `r1_get_*` / `r1_subscribe_*` (PM), `r1_set_*` (config: tx power, tilt, azimuth, handover margin, cell state), `r1_create_*` / `r1_start_*` (simulation lifecycle), `viavi_*`, `safeloop_search` / `safeloop_cypher`, `cognee_*`, `get_schema` / `get_ontology`, **`track_decision` / `get_audit_trail` ("Decision Provenance", "EU AI Act compliance, explainability")**, `generate_audit_report`, `health_check`, `read_file` / `write_file`.
- Upstream `lf-connectivity/maveric` `services/` contains only `api_manager, kafka, orchestration, rf_prediction, training, ue_tracks_generation`, so **this MCP server is not in upstream MAVERIC** (public GitHub API, main branch). [Inference] It comes from a private or unreleased fork.

### OAI page: suggested 5G MCP tool names (ideas only, no code) [Obs]
- Core: `nrf_register_nf()`, `amf_manage_ue()`, `smf_create_session()`, `udm_subscriber_data()`
- RAN split: `f1_setup_control()`, `e1_bearer_setup()`, `cu_split_config()`
- Reference points: `n2_ngap_monitor()`, `n4_pfcp_control()`, `n3_gtp_tunnel()`, `n6_data_network()`
- Testing: `gnbsim_ue_attach()`, `iperf3_traffic_test()`, `multi_ue_load_test()`, `qos_validation()`
- Operations: `interface_health_check()`, `resource_optimization()`, `network_slice_management()`, `fault_detection()`, `nwdaf_analytics()`, `lmf_location_services()`, `nef_api_exposure()`

---

## 5. AWS services, prerequisites, and governance/security findings

### AWS services used [Obs]
SageMaker AI (Studio), CloudShell, Bedrock (Claude), **Bedrock AgentCore** (Runtime, Memory, Gateway, workload identity tokens), Cognito, SSM Parameter Store, Secrets Manager, ECR, CodeBuild, S3, Lambda, IAM/STS, CloudWatch Logs, X-Ray (agent role has `xray:PutTraceSegments`), CloudWatch metrics (namespace `bedrock-agentcore`), EC2 (g5.2xlarge, DLAMI), VPC, EKS (eksctl, EBS CSI), AWS Marketplace (subscribe).

### Prerequisites [Obs]
An AWS account with the IAM user permissions quoted in §1, CloudShell or an IDE, and us-east-1. Pinned packages: `bedrock-agentcore-starter-toolkit==0.1.14`, plus `strands-agents`, `mcp`, `bedrock-agentcore` and others.

### Governance, guardrails, evidence, approvals and security

**Approvals and human-in-the-loop: none in Modules 2–7.** [Obs] The Module 6 expected output shows an advisory question producing write actions. The prompt was *"I want to deploy a new rApp. Based on my available resources, what would be the best choice to deploy?"* and the agent replied *"I've successfully deployed a new Traffic Steering Controller rApp … Created a new … rApp … Primed the rApp … Created an instance … Successfully deployed the instance"*. The workshop presents this as a memory success: *"Takes action by creating, priming, and deploying a new rApp"* (…/module6-agent-memory).

**Bedrock Guardrails: not used anywhere.** [Obs]

**Plan/execute naming is not enforced.** [Obs] The Module 7 Lambdas pair `create_*_plan` with `exec_*(plan_id)`, but each Lambda is a stateless mock with its own empty dicts (*"Global storage (in production, use DynamoDB/RDS)"*). `execute_energy_optimization(plan_id)` never looks the plan up, so any string is accepted.

**Identity and auth** [Obs]:
- `cognito_utils.py` creates pool `MCPServerPool` with user **`testuser` / `<demo password redacted>`** (`ALLOW_USER_PASSWORD_AUTH`), and `print(f"Bearer Token: {bearer_token}")` (line 68).
- The deployed `agent.py` (line 26) logs into the MCP servers **as that same shared user**, so the end user's identity does not reach the tools.
- Module 7 Step 12 prints the Gateway token (`print("Token response:", token)`).
- The Gateway's M2M client is issued both `gateway:read` and `gateway:write` scopes. [Inference] There is no per-tool or scope-based authorization.

**Gateway inbound/outbound auth model** [Obs], verbatim from …/module7-agentcore-gateway: *"Gateway employs a dual authentication model … Inbound Auth, which validates and authorizes users attempting to access gateway targets, and Outbound Auth, which enables the gateway to securely connect to backend resources on behalf of authenticated users."*

**IAM breadth** [Obs]:
- Gateway role (`utils.create_agentcore_gateway_role`): `bedrock-agentcore:*`, `bedrock:*`, `agent-credential-provider:*`, `iam:PassRole`, `secretsmanager:GetSecretValue`, `lambda:InvokeFunction` on `"Resource": "*"`.
- Agent role: `bedrock:InvokeModel*` on `*`.
- The SageMaker role gets `bedrock-agentcore:*` and Lambda create/invoke on `*`, but IAM/ECR/SSM/Secrets permissions are name-scoped (`agentcore-*`, `mcp_server/*`).
- Non-RT RIC CodeBuild role: IAMFullAccess, EC2FullAccess, CloudFormationFullAccess.

**Evidence and audit** [Obs]:
- The core track has no audit or evidence artifact beyond what AgentCore logs to CloudWatch, and the role grants X-Ray. Neither is discussed.
- The **Agentic Network Framework** page alone maps EU AI Act articles to code. It says it is for *"AWS Hackathon participants"* and ends *"This guide is designed for the AWS Hackathon"*, Last Updated 2025-10-29. The mapping:
  - *"Article 12: Logging and Traceability"*: *"All MCP tool calls are automatically logged"* (a comment only)
  - *"Article 13: Explainability (SHAP values)"*: `track_decision` with `feature_contributions`
  - *"Article 14: Human Oversight"*: `if improvement < THRESHOLD: print("❌ Improvement insufficient - requires manual approval")`
  - *"Article 15: Accuracy and Robustness"*: `generate_audit_report`
- The `track_decision` record shape: `decision_type`, `input_state`, `action{parameter, old_value, new_value}`, `rationale`, `outcome`.
- Its "Production Deployment Checklist" includes *"Get approval for live network changes"*, *"Test in simulation before live network"*, *"Implement rollback mechanism"* and *"Track all decisions for audit trail"*.
- Its Ottawa coverage workflow is: twin/sim A/B, then a `>= 2 dB` improvement gate, then `r1_set_cell_tx_power(... "apply_to_live": True  # ⚠️ Live network change!)`, then a 10-minute monitor with auto-rollback, then `track_decision`.
- [Inference] The "human oversight" step is only a threshold-and-abort. No human approves anything, and live apply happens automatically when the threshold passes.

**Hygiene** [Obs]: the Framework page leaks the author's local filesystem paths (`/Users/<author>/Projects/Maveric/...`, `/Users/<author>/.cognee/logs/`).

---

## 6. Critical warning: never run `cleanup-module1.sh` in the shared hackathon account

[Obs] `cleanup-module1.sh` (Module "Cleanup Account") deletes **every** AgentCore gateway, agent runtime and memory in the region, and the AgentCore runtime log groups, **with no name filter**:
- line 76: `GATEWAYS=$(aws bedrock-agentcore-control list-gateways --query 'items[].gatewayId' …)`. It then deletes all targets and every gateway.
- line 116: `AGENT_IDS=$(aws bedrock-agentcore-control list-agent-runtimes --query 'agentRuntimes[].agentRuntimeId' …)`, then `delete-agent-runtime`.
- line 130: `MEMORY_IDS=$(aws bedrock-agentcore-control list-memories --query 'memories[].id' …)`, then `delete-memory`.
- line 346: deletes log groups matching `/aws/bedrock-agentcore/runtimes/` and `/aws/codebuild/bedrock-agentcore`.

The page describes it as *"Safe: Includes prerequisites check and clear warnings"* and *"Verified: Battle-tested with real workshop resources"*. [Inference] Our platform runs on Bedrock AgentCore. If a teammate pasted this script into the shared account (or the participant role allowed it), it would destroy platform agents, gateways, memory and **evidence logs**. Treat this script as hostile to our environment.

---

## 7. Defects and inconsistencies (useful if a judge asks why we didn't just copy it) [Obs]
- **Module 7 prose does not match its code.** The prose says *"we will transform the R1 and O2 MCP servers you deployed earlier into a unified AgentCore Gateway"*, but the code deploys 10 unrelated mock Lambdas and never wires R1 or O2 into the Gateway.
- **R1 tool count.** The page says 5 + 5 + 1 tools; the notebook has 10.
- **Non-RT RIC cleanup.** It downloads `cleanup-regional.sh`, then runs `chmod +x cleanup-nonrtric.sh` and `./cleanup-nonrtric` (wrong name). Both `cleanup-regional.sh` and `deploy-rapp.sh` return 403.
- **Non-RT RIC access-entry block.** It uses `$CLUSTER_NAME` but never sets it; that page sets only `REGION`, and its cluster is `agentic-oran-osc`. The only definition is on the OAI page: `export CLUSTER_NAME=oai-5g-cluster`. [Inference] Someone following the pages in order would point the EKS access entry at the wrong cluster, or one that no longer exists.
- **OAI page.** The Helm step block is mis-indented, and its closing `:::` is indented too.
- **Module 3 page.** It ends with a stray `x`.
- **Energy-plan schemas.** The gateway tool schema for `create_energy_saving_plan` (`network_topology`, `traffic_patterns`) differs from the bundled `smo_planner_extended.py` signature (`energy_targets`, `optimization_scope`).
- **Cleanup page.** It warns about cost but says nothing about what the script deletes outside the workshop.
- **Leftover policies.** `update-sagemaker-studio-permissions.sh` adds 12 inline policies, but the `policies_to_remove` list in `cleanup-module1.sh` names only 9. The CloudWatch Logs, AgentCore service-linked-role and Marketplace-subscribe policies stay on the SageMaker role after cleanup.

---

## 8. Relevance to our hackathon

### What we could reuse

**Tool naming and contracts.**
- The O-RAN-interface-scoped verb_noun set (R1: `create_rapp`, `prime_rapp`, `deploy_rapp_instance`…; O2: `get_ocloud_info`, `get_resource_pools`, `patch_alarm`…) is a credible, standards-flavoured vocabulary judges will recognise.
- [Inference] Splitting the combined `deploy_rapp_instance(deploy_order)` and `prime_rapp(prime_order)` into separate read and write tools would make per-tool policy easier at our gateway.

**Plan → execute two-phase pattern** (`create_*_plan` returns a `plan_id`; `exec_*(plan_id)` acts).
- [Inference] This is a natural approval checkpoint. We can reuse the shape and add what the workshop lacks: a persisted plan record, an approval bound to that `plan_id` and approver, and an executor that refuses unknown or unapproved plans.

**5G-core and RAN MCP tool ideas.** The OAI page's list (§4) is a ready backlog if we need 5GC- or RAN-split-flavoured tools. It is ideas only, with no implementation to copy.

**Twin usage.**
- Same MAVERIC/RADP and CUDA compose files.
- The workshop's MRO, CCO, energy-savings and load-balancing notebooks are sample rApps whose outputs could drive a "simulate before act" step.
- The Framework page's Ottawa flow (baseline sim, then change, then compare, then a ≥2 dB gate, then apply, then monitor/rollback, then `track_decision`) is a ready narrative for twin-gated changes.
- [Inference] The workshop never connects the twin to an agent, so a twin-in-the-loop under governance would be differentiated.

**Agent patterns.**
- Strands `Agent` with `MCPClient`, using streamable HTTP and a bearer token.
- MCP endpoints discovered through SSM parameters.
- AgentCore Runtime deploy through the starter toolkit with a `customJWTAuthorizer`.
- AgentCore Memory hooks (semantic strategy, actor/session IDs, last-K turns).
- Gateway Lambda targets with inline `toolSchema` and `GATEWAY_IAM_ROLE` outbound.

**Evidence schema and control language.**
- The `track_decision` fields (input_state, action old→new, rationale, outcome) and the EU AI Act Art. 12–15 mapping give judges a recognisable frame.
- [Inference] We can show these as enforced controls where the sibling workshop only has comments and print statements.

**Mock O2 fixture data** (INF O-Cloud, RegionOne, R740/Xeon) is handy for deterministic demo prompts. The canonical demo prompt is *"Using the O2 interface, do I have any O-Cloud resources supplied by Intel?"*

### What differs from our governed platform
1. **Models.** The workshop uses Claude 3.7 Sonnet on Bedrock. We use NVIDIA Nemotron. Prompts and tool-calling behaviour won't transfer one-to-one. [Inference]
2. **Approvals.** The workshop has none in the core track, and its agent deploys rApps when asked a question (Module 6). The control our platform governs is absent there.
3. **Identity.** The workshop uses a shared `testuser` password, prints tokens, and gives the M2M client every scope. Our platform puts governed tools behind a gateway (per your brief). [Inference] Per-caller identity and per-tool authorization are where we can differ visibly.
4. **Evidence.**
   - The core track has no evidence or ledger.
   - Audit and provenance appear only in documentation for a localhost server the workshop doesn't deploy, and that server isn't in upstream MAVERIC.
   - [Inference] Any evidence we produce (our ledger and evidence path) has no counterpart there.
5. **Tenancy and blast radius.**
   - The workshop assumes a single-tenant participant account with broad IAM: `bedrock-agentcore:*`, `bedrock:*` and `iam:PassRole` on `*`, plus IAMFullAccess on the CodeBuild role.
   - Its cleanup deletes all AgentCore resources in the region.
   - Our environment is shared with restricted participant roles, so do not copy its setup or cleanup scripts.
6. **Twin hosting.**
   - The workshop's twin is a participant-launched public-IP EC2 reached over SSH, standalone and not exposed as MCP tools.
   - Ours is hosted on the platform (per kit). [Inference] Twin calls should go through the same governed tool path as network actions.
7. **Tools are mocks.** R1, O2 and the Lambdas are in-memory stubs, and their "DEPLOYED" and "APPLIED" states are fake. Any claims we copy from the workshop's expected outputs are fiction, not evidence.

# AI Native Networks Immersion Day: context for planning

Working notes, not part of the submission. Compiled on 2026-10-05 by three web-reading subagents, after our guide's "Reference: Network Tool Naming" cited this workshop. The most consequential claim (the cleanup script) was re-checked independently from the script itself. Raw reader notes are in `raw/`, with a third-party demo password redacted.

**Access:** catalog.workshops.aws is a JavaScript single-page app, so plain fetches only see "Workshop Studio". The page sources are public, with no login: start from `https://static.us-east-1.prod.workshops.aws/public/quicklinks/ai-native-networks/published.json` (`requiresAuth: false`), whose build path leads to `…/content/<module path>/index.en.md`. The full navigation is in `manifest.json` there.

## 1. ⚠️ Safety: never run its cleanup scripts in our account

`cleanup-module1.sh` warns *"This will permanently delete all Bedrock AgentCore resources!"* and then, **with no name filter**:
- lists every gateway and deletes all of its targets and the gateway (lines 76–100)
- lists every agent runtime and deletes it (lines 116–120)
- lists every memory and deletes it (lines 130–134)

In our shared event account that would wipe the platform's AgentCore gateway, the reference agents and `my-agent`. Its other cleanup scripts weren't reviewed; treat them the same way.

## 2. What the workshop is

Base: `https://catalog.workshops.aws/ai-native-networks/en-US`

| Path | What it builds |
|---|---|
| `/introduction` | Getting started |
| `/module1-sagemaker` | SageMaker Studio setup |
| `/module2-r1-mcp` | O-RAN **R1** MCP server on AgentCore Runtime (FastMCP, mock, 10 tools) |
| `/module3-o2-mcp` | O-RAN **O2** MCP server (mock, 24 tools) |
| `/module4-local-agent` | Local Strands agent calling the MCP servers |
| `/module5-deploy-agent` | The agent on AgentCore Runtime |
| `/module6-agent-memory` | AgentCore Memory |
| `/module7-agentcore-gateway` | AgentCore Gateway fronting 10 mock Lambda tools, the closest match to "tools behind a gateway" |
| `/module8-cleanup`, `/summary` | Cleanup, summary |
| `/module9-additional-resources/…` | Optional: `module5-mcp-quickstart` and `module1-agentic-network-framework` (rApps); `module2-digital-twin/{infra,radp,apps,cleanup}` (RADP twin on a g5.2xlarge Deep Learning AMI, CUDA path); `module3-agentic-core` (**"Deploy End-to-end 5G Network"**: OpenAirInterface core and RAN on EKS 1.32 via eksctl and Helm); `module4-nonrtric` (O-RAN Non-RT RIC) |

- **Models and guardrails:** every agent uses **Claude 3.7 Sonnet** on Bedrock. No Nemotron, no Bedrock Guardrails.
- **Not public:** `deploy-rapp.sh`, `cleanup-regional.sh` (403); the 105-tool (also 63/59) MCP server the additional-resources pages depend on (not in `lf-connectivity/maveric` or its forks). The VIAVI simulator is commercial and shown unavailable.

## 3. Its governance is the opposite of our platform's (useful contrast)

- **No approval anywhere.** Asked *"what would be the best choice to deploy?"*, the agent creates, primes and deploys an rApp itself, and execute tools never check that a plan exists.
- **The only guard on live changes is one `apply_to_live` flag.** The "Human Oversight" check alerts a person only when a change is **rejected**, and the audit record is written by the agent, after the change.
- **Identity:**
  - One shared, hard-coded Cognito test user (`USER_PASSWORD_AUTH`), and access tokens are printed to output.
  - The gateway role has `bedrock:*`, `bedrock-agentcore:*` and `iam:PassRole` on `*`.
  - All tools are loaded unfiltered.
- **Nothing connects the agents to the network.** The twin and the 5G network are never wired to an agent or MCP server.

## 4. Our guide's "Network Tool Naming" claims vs the cited page

Page: `/module9-additional-resources/module3-agentic-core` ("Deploy End-to-end 5G Network")

| Guide claim | Verdict |
|---|---|
| The page *"names 5G core interfaces as callable tools"* | **Different.** The page builds no agent and no MCP server. It lists 22 MCP function names as *"potential projects"*, with no schemas, transport, auth, model or code |
| Shape `<domain>_<verb>_<resource>` | **Not found** as a stated convention. 3 of the 22 names fit cleanly and `f1_setup_control` loosely. The nearest precedent is the O-RAN `r1_get_*` / `r1_set_*` prefix table on the Agentic Network Framework page |
| Examples `amf_manage_ue()`, `smf_create_session()`, `nrf_register_nf()`, `f1_setup_control()` | **Confirmed** verbatim; they are exactly the names that fit the shape |
| *"The function name is the 3GPP interface reference (N2, N4, F1, Xn)"* | **Partly.** True for `n2_`, `n3_`, `n4_`, `n6_`, `f1_`, `e1_`. Service-based names start with the network function (amf, smf, nrf, udm). Xn appears only in a heading |
| Quoted sentence | **A paraphrase.** Verbatim: *"This MCP abstraction approach transforms the static 5G network deployment into a programmable, agentic-controlled infrastructure where AI agents can dynamically manage network functions, simulate realistic traffic scenarios, and optimize performance based on real-time analytics."* |

## 5. Possibly reusable, as inspiration only (not decided)

- **Tool vocabulary:** the R1/O2 tool names, and the 22 5G-core MCP function names, for realistic network tools behind our governed gateway.
- **The twin's notebooks:** the RADP twin's MRO/CCO notebooks.
- **Plan-then-execute:** naming that splits planning from execution, **with a real approval check added** (theirs has none).
- **Audit records:** their `track_decision` / `get_audit_trail` format, though theirs is agent-written after the fact. Our gap list already covers why that isn't enough (gaps 1, 6, 7).

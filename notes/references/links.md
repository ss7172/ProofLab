# Reference links

Working notes for our team, not part of the submission. Each link was checked on 2026-10-05 with curl, the GitHub REST API, the ServiceNow docs search API and, for one ServiceNow pair, WebFetch. No AWS API calls were made.

## Warnings first

- **`cedarpolicy.com/en` is dead (404).** It's a GitHub Pages site; `/en/` and `/en/tutorial` also return 404. For reading, use docs.cedarpolicy.com. www.cedarpolicy.com is now only the Playground app.
- **ServiceNow docs links need a release prefix.**
  - A URL with no release segment (`/docs/r/<bundle>/<page>.html`) opens the current release, which the docs search API labels **Brazil**.
  - A page that isn't in Brazil is missing there: the curated Kill Switch link renders a 404 in a browser (WebFetch), although curl still gets the 200 JavaScript shell.
  - Put `australia/`, `zurich/`, `yokohama/` or `xanadu/` after `/r/` to open an older release.
  - The hackathon's curated page says its links point to the Australia release. They have no release segment, so they actually open Brazil.
- **A 200 doesn't prove a page exists** on three of these sites:
  - docs.aws.amazon.com returned 200 for a made-up AgentCore path, with the generic title "Amazon Bedrock AgentCore". Check the page's `<title>`.
  - servicenow.com/docs returns the same 8,403-byte JavaScript shell, with a 200, for real and made-up pages. Check with the search API (section 9).
  - catalog*.workshops.aws returns a "Workshop Studio" JavaScript shell, with a 200, for any path. The hackathon's own workshop pages also need a login.

## Status legend

Every row records how its page was confirmed.

| Status | Meaning |
|---|---|
| OK (title) | 200, and the page's own `<title>` names the topic. |
| OK (404 control) | 200, and the same site returns a real 404 for a made-up path (kubernetes.io, strandsagents.com). |
| OK (API) | Confirmed through an API instead of the page: the GitHub REST API for repos, commits and files, or the ServiceNow docs search API (match on `ft:prettyUrl`). |
| OK (manifest) | A Workshop Studio JS app page that is listed in the workshop's published manifest. |
| Moved stub | 200, but the page only says the content has moved. |
| 404 | Broken. A replacement is given. |
| Login | Needs a workshop login, so its content couldn't be checked. |

---

## 1. Amazon Bedrock AgentCore

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [Host agent or tools with AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html) | Hosting an agent or a tool, such as an MCP server, on AgentCore Runtime. | When an `AgentConfig` uses `spec.awsAgentCore` (its status carries `agentRuntimeId` / `agentRuntimeArn`), or when deploying or debugging an agent on Runtime. | OK (title) |
| [AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html) | "A secure AI gateway for agents, tools, and models": puts APIs and Lambdas behind one MCP gateway. | When a `ToolConfig` uses `spec.agentCoreGateway` (its status carries `gatewayTargetId`, `gatewayIdentifier`, `observedTools`), or when adding a gateway target. Module 7 of the sibling workshop (section 10) is a worked example. | OK (title) |
| [Add observability to AgentCore resources](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html) | Turning on traces, logs and metrics for AgentCore resources. | When agent or tool spans are missing, or before relying on AgentCore traces as evidence. | OK (title) |

## 2. Amazon Bedrock models

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [Inference using Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html) | Bedrock's model-agnostic request and response format for chat and tool use. | When writing or reading model-call code, or when mapping a gateway chat call onto a Bedrock request. | OK (title) |
| [Cross-Region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html) | Inference profiles, which route one model across Regions. | When picking `ModelConfig.spec.modelId` for a model that needs an inference-profile ID instead of a bare model ID, or when a call fails with an on-demand throughput error. | OK (title) |
| [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) | Content filters, denied topics, sensitive-information filters and prompt-attack detection. | When setting `ModelConfig.spec.safety`, reading `status.guardrailId` / `guardrailVersion`, or explaining why a response was blocked. | OK (title) |

## 3. Other AWS services

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [What is Amazon CloudFront?](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html) | A CDN and edge distribution in front of web origins. | When a URL under test is served through CloudFront and you need to reason about caching, origins or dropped headers. | OK (title) |
| [What is Amazon ECR?](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html) | The container image registry. | When pushing an agent or tool image for EKS or AgentCore Runtime, or when a pod is stuck pulling an image. | OK (title) |
| [What is Amazon CloudWatch?](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) | Logs, metrics and alarms. AgentCore observability data also lands here. | When looking for gateway or agent log lines, or when building a metric or alarm. | OK (title) |

## 4. Kubernetes

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [Custom Resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) | What custom resources (CRs) and CRDs are, CRDs compared with API aggregation, and CRD features such as validation, versioning and the status subresource. | When reading or writing `ModelConfig` / `ToolConfig` / `AgentConfig` / `Registry` manifests, or when reasoning about `status` and served or storage versions. | OK (404 control) |

## 5. TM Forum ODA and MoDaaS

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [tmforum-oda/model-as-a-service-crds](https://github.com/tmforum-oda/model-as-a-service-crds) | The public MoDaaS contract: four v1beta1 CRDs (ModelConfig, ToolConfig, AgentConfig, Registry). | When you need an exact field name, a required field, an enum value or a status field. Read the YAML; don't work from memory. | OK (API), public |
| [tmforum-oda/ai-canvas-architecture](https://github.com/tmforum-oda/ai-canvas-architecture) | The AI-Native ODA Canvas architecture repo the workshop refers to: ADR-001 to ADR-008, all "Proposed", plus five flow diagrams. | When you justify a design choice against the Canvas ADRs (gateway mediation, inventory as the registry, configuration resources). | OK (API), public |

### What's public in `model-as-a-service-crds`

- **Repo state:** public. Default branch `master`, created 2026-08-13, last pushed 2026-08-15.
- **README status:** "PROPOSED CONTRIBUTION INPUT — not an adopted standard … Nothing here is endorsed or ratified by TM Forum."
- **Licence:** the README says Apache-2.0, but GitHub's licence detector reports `NOASSERTION`.
- **Top level:** `LICENSE`, `README.md` and `crds/` (four files). Nothing else.

| Kind (short name) | File | Versions | Required `spec` | Notable `spec` fields | Notable `status` fields |
|---|---|---|---|---|---|
| ModelConfig (`mc`) | [modelconfig-v1beta1-crd.yaml](https://github.com/tmforum-oda/model-as-a-service-crds/blob/master/crds/modelconfig-v1beta1-crd.yaml) | v1beta1 (served and storage). v1alpha1 and v1alpha2 are still listed with `served: false`. | alias, provider, modelId | paused, safety, governance, registryRef, credentialSecretRef. Provider blocks: awsBedrock, awsSageMaker, azureOpenAI, googleVertex, databricks, nvidiaNIM, ollama, custom. | guardrailId, guardrailVersion, enforcerKind, enforcerFailOpen, registryApprovalStatus, driftDetected, tmf639ResourceId, daysUntilRetirement, conditions |
| ToolConfig (`tc`) | [toolconfig-v1beta1-crd.yaml](https://github.com/tmforum-oda/model-as-a-service-crds/blob/master/crds/toolconfig-v1beta1-crd.yaml) | v1beta1 | toolName, provider | toolType, backendRef, outputSchema, access, agentCoreGateway, dependsOn, paused, safety | gatewayTargetId, gatewayIdentifier, observedTools, access, registryApprovalStatus, tmf639ResourceId |
| AgentConfig (`ac`) | [agentconfig-v1beta1-crd.yaml](https://github.com/tmforum-oda/model-as-a-service-crds/blob/master/crds/agentconfig-v1beta1-crd.yaml) | v1beta1 | agentName, provider, agentCard | modelRef, toolRefs, dependsOn, networkMode, agentPolicy, awsAgentCore, kubernetesPod, paused | agentRuntimeId, agentRuntimeArn, keycloakRoleId, workloadIdentityArn, riskFindings, dependencyHealthy, tmf639ResourceId |
| Registry (`reg`) | [registry-v1beta1-crd.yaml](https://github.com/tmforum-oda/model-as-a-service-crds/blob/master/crds/registry-v1beta1-crd.yaml) | v1beta1 | controller, backing | parameters, description | phase, lastProbed, recordCount, message |

- **What all four share:** API group `oda.tmforum.org`, Namespaced scope, the status subresource, and no conversion webhook.
- **Annotations:** ModelConfig, ToolConfig and AgentConfig carry `oda.tmforum.org/specification: GB1085 Model-as-a-Service v1.0.0`. Registry is annotated with the design pattern `k8s-storageclass-ingressclass-gatewayclass`.
- **Not published:** per the README's "What is deliberately not here" section, the operator code (reconciliation, IAM/IRSA, gateway data plane), cluster configuration and credentials. A Helm chart is "distributed separately".
  - A conformance test kit (BDD/Gherkin CTK) is "in progress".
  - The README mentions "interaction flows", but the repo contains none.
- **Diverges from ADR-005:** the README says "Three CRDs, not one", a deliberate split from ADR-005's single-CRD position. It leaves the decision to the TM Forum working group.

### What's public in `ai-canvas-architecture`

- **Repo state:** public, default branch `main`, description "AI-Native ODA Canvas Architecture". Created 2026-03-17, last pushed 2026-09-09. GitHub reports the licence as `NOASSERTION`.
- **Top level:** `README.md`, `LICENSE`, `.gitignore`, `.DS_Store`, `decision-log/` and `diagrams/`.
- **No CRDs:** the tree has no YAML at all. Resources such as ADR-005's AIGatewayConfig and DataResourceConfig are described only in prose.
- **ADRs:** all have Status "Proposed". The links below go to the real files, because the index in `decision-log/README.md` uses different file names, and the second ADR-008 (Agent Skills) is missing from the index.

| ADR | Title | File |
|---|---|---|
| 001 | Agentic components as primary deployable unit | [ADR-001-agentic-components-deployment-model.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-001-agentic-components-deployment-model.md) |
| 002 | Interaction interface model (OpenAPI, A2A, MCP) | [ADR-002-interaction-interface-model.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-002-interaction-interface-model.md) |
| 003 | Resource inventory as unified discovery registry | [ADR-003-resource-inventory-as-unified-discovery-registry.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-003-resource-inventory-as-unified-discovery-registry.md) |
| 004 | Gateway mediation architecture (AI Gateway + Interaction Gateway) | [ADR-004-gateway-mediation-architecture.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-004-gateway-mediation-architecture.md) |
| 005 | AI-native configuration resources (AIGatewayConfig, DataResourceConfig). MoDaaS diverges from this one. | [ADR-005-ai-native-configuration-resources.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-005-ai-native-configuration-resources.md) |
| 006 | Model onboarding and AI Gateway integration | [ADR-006-model-onboarding-and-ai-gateway-integration.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-006-model-onboarding-and-ai-gateway-integration.md) |
| 007 | Data resource architecture and access patterns | [ADR-007-data-resource-architecture.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-007-data-resource-architecture.md) |
| 008 | Proxy pattern for external agent and tool integration | [ADR-008-proxy-pattern-external-integration.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-008-proxy-pattern-external-integration.md) |
| 008 (duplicate number) | Agent Skills (2026-03-24), not listed in the index | [ADR-008-Agent-Skills.md](https://github.com/tmforum-oda/ai-canvas-architecture/blob/main/decision-log/ADR-008-Agent-Skills.md) |

The `diagrams/` folder holds five PNGs: `agent-llm-access-flow`, `agent-mcp-access-flow`, `agent-to-agent-flow`, `manage-agentic-components-install` and `manage-models-install`.

## 6. Policy (Cedar) and tracing

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| ~~[cedarpolicy.com/en](https://cedarpolicy.com/en)~~ | The Cedar link as it was shared. | Don't use it; use the two rows below. | **404** (GitHub Pages; `/en/` and `/en/tutorial` also return 404) |
| [Cedar Policy Language Reference Guide](https://docs.cedarpolicy.com/) | Syntax, schemas, entities and authorization semantics. | When writing or reviewing a Cedar policy or schema. | OK (title "What is Cedar? \| Cedar Policy Language Reference Guide") |
| [www.cedarpolicy.com](https://www.cedarpolicy.com/) | The site root is now the "Cedar Language Playground" JS app. | When trying out a policy, schema or request before you code it. | OK (200, title "Cedar Language Playground") |
| [W3C Trace Context](https://www.w3.org/TR/trace-context/) | The `traceparent` / `tracestate` header format: version, trace-id, parent-id, flags. | When propagating trace ids, or joining on them, across gateway → agent → tool, for example the known CID/traceparent mismatch in the reference agents. | OK (title) |
| [OpenTelemetry GenAI semantic conventions (opentelemetry.io)](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | The official opentelemetry.io URL for the `gen_ai.*` conventions. It now says: "GenAI semantic conventions have moved to the OpenTelemetry GenAI semantic conventions repository." | Only to confirm the move. The content is in the repo rows below. | Moved stub (200) |
| [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) | The new home of the GenAI conventions. Created 2026-05-05, last pushed 2026-10-05. | When choosing span and attribute names. | OK (API) |
| [docs/gen-ai/gen-ai-spans.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md) | Model-call spans. Line 7 reads "**Status**: Development", and each attribute row checked has a Development badge. `gen_ai.operation.name` and `gen_ai.provider.name` are Required; `gen_ai.conversation.id` is Conditionally Required. | When emitting or parsing model-call spans. | OK (API, status read) |
| [docs/gen-ai/gen-ai-agent-spans.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md) | Agent spans. | When instrumenting agent invocations. | OK (API, file exists) |
| [docs/gen-ai/mcp.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/mcp.md) | MCP conventions. | When instrumenting MCP tool calls through the gateway. | OK (API, file exists) |
| [docs/gen-ai/aws-bedrock.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/aws-bedrock.md) | Attributes specific to Bedrock. | When tagging Bedrock calls. | OK (API, file exists) |
| [docs/registry/attributes/gen-ai.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/registry/attributes/gen-ai.md) | The full `gen_ai.*` attribute registry. | When you need an attribute's type or allowed values. | OK (API, file exists) |

The registry page on opentelemetry.io ([registry/attributes/gen-ai](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/)) still lists the attributes, but each one is marked "Moved to the OpenTelemetry GenAI semantic conventions repository".

## 7. Agents SDK

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [Strands Agents](https://strandsagents.com/) | "Open source SDK for AI agents in Python and TypeScript". | When writing or changing agent code. Modules 4–5 of the sibling workshop (section 10) show a Strands agent that calls MCP servers and then runs on AgentCore Runtime. | OK (404 control) |

## 8. Digital twin

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [lf-connectivity/maveric](https://github.com/lf-connectivity/maveric) | Source of RADP, the RIC Algorithm Development Platform that serves as the network digital twin. MIT licence. | When a network-agent call into the twin misbehaves and you need the RADP API or service code. | OK (API) |
| [maveric at the workshop pin 7573f03](https://github.com/lf-connectivity/maveric/tree/7573f030523669eaa3bb215fb3b29985c06824c8) | The pinned tree, committed 2025-11-06 as `Revert "feat: comprehensive validation system for RADP APIs"`. It is also the current `main` HEAD (the compare API reports "identical"), and the repo has had no push since 2025-11-06. Top level at the pin: `radp/`, `services/`, `apps/`, `notebooks/`, `docs/`, `tests/`, `dc*.yml`. | When you need code that matches what the workshop deployed. | OK (API) |

## 9. ServiceNow

**URL pattern:** `https://www.servicenow.com/docs/r/<release>/<bundle>/<page>.html`. With no release segment the URL opens the current release (Brazil); see the warning at the top.

**How these rows were checked:** through the docs search API. A page exists in a release if one of the results' `ft:prettyUrl` values matches it, and the made-up control got no match. For Kill Switch, WebFetch was also used: the unversioned URL returned a real 404, as the made-up control did, while the `australia/` URL rendered the page.

```sh
curl -s -X POST https://www.servicenow.com/docs/api/khub/clustered-search \
  -H 'Content-Type: application/json' \
  -d '{"query":"Kill Switch","paging":{"perPage":20,"page":1}}' \
  | grep -o '"ft:prettyUrl","values":\["[^"]*"'
```

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [AI Control Tower (landing)](https://www.servicenow.com/docs/r/intelligent-experiences/aict-landing.html) | AI Control Tower (AICT): inventory, lifecycle, risk and value. It holds the governance record (Rail 2) and does not constrain runtime behaviour. | When deciding what AICT can see of MoDaaS assets, or what to register there. | OK (API, Brazil, updated 2026-09-10) |
| [AI Agent Studio (landing)](https://www.servicenow.com/docs/r/intelligent-experiences/aias-landing.html) | Building agents on the ServiceNow side. | When a ServiceNow agent has to call the governed gateway (Rail 3). | OK (API, Brazil, updated 2026-09-10) |
| [Writing effectively for agentic AI](https://www.servicenow.com/docs/r/intelligent-experiences/gg-creating-aia.html) | Guidelines for writing agent and workflow instructions. The curated page calls it "the single most useful page for a hackathon team". In Brazil and Australia it is now titled **"Writing prompts for agentic AI"**; older releases keep the curated title. | Before you write any ServiceNow agent's role or instructions. | OK (API, Brazil) |
| [Kill Switch (Australia URL)](https://www.servicenow.com/docs/r/australia/intelligent-experiences/aia-kill-switch.html) | The API's description: "The kill switch feature detects and stops runaway AI agent triggers that execute repeatedly against the same records, preventing unnecessary consumption of Now Assist interactions." It sits under AI Agent Studio (legacy) › Create an AI agent › Add a trigger; the Australia page title is "Kill Switch in Now Assist AI Agents". It is a circuit breaker for triggers, **not** a general stop for an agent. | When comparing our kill-switch control with ServiceNow's. Don't cite it as an emergency stop. | OK (WebFetch rendered, Australia; indexed for Australia and Zurich only). The curated unversioned link [`/r/intelligent-experiences/aia-kill-switch.html`](https://www.servicenow.com/docs/r/intelligent-experiences/aia-kill-switch.html) returns **404**, because the page is not in Brazil. |
| [Contain AI agents manually using kill switch protocol](https://www.servicenow.com/docs/r/intelligent-experiences/gov-sec-manage-ai-agents-using-kill-switch-protocol.html) | Going by its title, manual containment of AI agents. Found through docs search; not in the curated list; breadcrumb not captured. | When you need ServiceNow's counterpart to manually stopping an agent. | OK (API, Brazil, Australia, Zurich) |
| [Review the agent containment list](https://www.servicenow.com/docs/r/intelligent-experiences/gov-sec-review-kill-switch-protocol-log.html) | Going by its title, the list or log of contained agents. Found through docs search; not in the curated list. | The audit side of the row above. | OK (API, Brazil, Australia, Zurich) |
| [Enable AI Guardian](https://www.servicenow.com/docs/r/intelligent-experiences/enable-aia-na-guardian.html) | AI Guardian for AI agents. The curated note reads: "Offensiveness detection and prompt injection handling." | When comparing guardrails on the ServiceNow side with Bedrock Guardrails at the gateway. | OK (API, Brazil, updated 2026-10-01) |
| [AI Guardian analytics](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-guardian-analytics.html) | "Monitor the performance of guardrails enabled through AI Guardian." | When looking for guardrail evidence on the ServiceNow side. | OK (API, Brazil) |
| [Use AI Guardian features](https://www.servicenow.com/docs/r/intelligent-experiences/now-assist-center-use-guardian-features.html) | AI Guardian in the AI Admin Center: offensive content, prompt-injection attacks and sensitive topics. | Same as the row above. | OK (API, Brazil) |
| [Add an MCP server in AI Agent Studio](https://www.servicenow.com/docs/r/intelligent-experiences/add-mcp-client-on-ai-agent-studio.html) | Registering an external MCP server, for example the gateway's `/mcp/{alias}`, as a tool source. In Brazil the page is titled "Adding an MCP Server in AI Agent Studio". | When wiring Rail 3, where a ServiceNow agent calls the governed MCP gateway. | OK (API, Brazil) |
| [MCP server with OAuth 2.1](https://www.servicenow.com/docs/r/intelligent-experiences/add-an-oauth-2-1-mcp-server.html) | OAuth 2.1 auth for that MCP server. In Brazil the page is titled "MCP Server with OAuth 2.1". | When the gateway expects OAuth tokens. | OK (API, Brazil) |
| [MCP server with an API key](https://www.servicenow.com/docs/r/intelligent-experiences/add-an-api-key-mcp-server.html) | API-key auth. In Brazil the page is titled "MCP Server with API Key". | When the gateway uses an API key. | OK (API, Brazil) |
| [MCP server with a connection and credential alias](https://www.servicenow.com/docs/r/intelligent-experiences/add-an-mcp-server-with-connection-and-credential-alias.html) | Other auth methods, through a Connection & Credential alias. The page title is **"MCP Server Others"**. | When neither OAuth nor an API key fits. | OK (API, Brazil, Australia, Yokohama) |
| [Hackathon "ServiceNow documentation set" (workshop page)](https://catalog.us-east-1.prod.workshops.aws/event/dashboard/en-US/workshop/resources/servicenow-docs) | ServiceNow's curated hackathon guide, with 121 links. | Use the team copy instead: `notes/servicenow/raw/D-docs-and-rails.md` §1.4. | Login (Workshop Studio JS app) |

## 10. Sibling workshop: AI Native Networks Immersion Day

Our synthesis is in `notes/ai-native-networks/ai-native-networks-context.md`. **Never run its cleanup scripts in our account** (see that file's section 1).

| Link | What it's for | When to open it | Status |
|---|---|---|---|
| [Workshop home](https://catalog.workshops.aws/ai-native-networks/en-US) | A public AWS workshop:<br>Modules 2–3 deploy MCP servers on AgentCore Runtime.<br>Module 4 connects a local Strands agent to MCP servers.<br>Module 5 deploys the agent to Runtime.<br>Module 6 adds AgentCore Memory.<br>Module 7 exposes Lambda functions as MCP tools through AgentCore Gateway. | When you want a worked example of AgentCore Runtime, Gateway and Strands. | OK (manifest), JS app |
| [Module 9: module3-agentic-core](https://catalog.workshops.aws/ai-native-networks/en-US/module9-additional-resources/module3-agentic-core) | "Deploy End-to-end 5G Network": an agentic app built on Strands that takes actions on a simulated end-to-end 5G network (OpenAirInterface core and RAN) running on EKS. | When you need the end-to-end telco example. | OK (manifest), JS app |
| [Module 9: Deploy RIC Algorithm Development Platform](https://catalog.workshops.aws/ai-native-networks/en-US/module9-additional-resources/module2-digital-twin/radp) | Deploys Maveric/RADP. It clones `lf-connectivity/maveric.git` without pinning a commit. | When comparing your twin deployment with the AWS version. | OK (manifest), JS app |
| [published.json](https://static.us-east-1.prod.workshops.aws/public/quicklinks/ai-native-networks/published.json) | The build pointer: `requiresAuth: false`, current build `c5491468-dbcf-44c0-aa99-4cd7265be03f`. | When you need the page text without a browser. Read `public/<buildId>/manifest.json`, then `public/<buildId>/content/<path>/index.en.md`. | OK (200 JSON) |
| [module3-agentic-core source (current build)](https://static.us-east-1.prod.workshops.aws/public/c5491468-dbcf-44c0-aa99-4cd7265be03f/content/module9-additional-resources/module3-agentic-core/index.en.md) | The page's raw Markdown. The build id changes when AWS republishes the workshop, so re-read published.json if this returns 404. | When you want to grep the page for commands or links. | OK (200) |

---

## Pages that need a login or JavaScript

- **Hackathon workshop pages** (`catalog.us-east-1.prod.workshops.aws/event/...`) need a login and JavaScript. Every path returns the same 200 "Workshop Studio" shell, so none of them can be checked without a session. The ServiceNow docs page is mirrored in the team notes (`notes/servicenow/raw/D-docs-and-rails.md` §1.4).
- **Sibling workshop** (`catalog.workshops.aws/ai-native-networks/...`) is public but a JS app, with the same 200 shell for any path. Read it without a browser through published.json → manifest.json → content Markdown (section 10).
- **ServiceNow docs** (`servicenow.com/docs/r/...`) is public but a JS app (Fluid Topics). curl gets the same 8,403-byte shell, with a 200, for every path. Check pages with the search API in section 9. WebFetch does get real 404s.
- **Cedar** (`www.cedarpolicy.com`) is a JS app (the Playground), and `/en` is a real 404. Use docs.cedarpolicy.com for reading.
- **AWS docs** (`docs.aws.amazon.com`) is server-rendered, but unknown paths still return 200. Check the `<title>` instead.

---
name: reference-links
description: "Pointer to the repo's verified reference-link page (notes/references/links.md, every link checked 2026-10-05) with the 10 most-used links inline and the link traps: dead cedarpolicy.com/en, ServiceNow release prefix, JS/login shells that return 200"
metadata:
  node_type: memory
  type: reference
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T17:53:42.369Z
---

**Full page:** repo `notes/references/links.md`, grouped by topic (AgentCore, Bedrock, other AWS, Kubernetes, TM Forum/MoDaaS, Cedar and tracing, Strands, digital twin, ServiceNow, the sibling AI Native Networks workshop). Each row gives the link, what it's for, when to open it, and a Status saying how it was confirmed (checked 2026-10-05 with curl, the GitHub REST API, the ServiceNow docs search API and WebFetch).

**Most-used links:**
- MoDaaS CRDs, for exact field names (read the YAML, not memory): https://github.com/tmforum-oda/model-as-a-service-crds
- Canvas ADRs, for design justification (all "Proposed"): https://github.com/tmforum-oda/ai-canvas-architecture
- Cedar reference guide: https://docs.cedarpolicy.com/
- W3C Trace Context (`traceparent`): https://www.w3.org/TR/trace-context/
- OTel GenAI conventions (moved off opentelemetry.io; status Development): https://github.com/open-telemetry/semantic-conventions-genai
- AgentCore Runtime: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html
- AgentCore observability: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html
- Bedrock Guardrails: https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
- ServiceNow AI Control Tower: https://www.servicenow.com/docs/r/intelligent-experiences/aict-landing.html
- ServiceNow "Writing effectively for agentic AI" (now titled "Writing prompts for agentic AI"; the curated page calls it the most useful): https://www.servicenow.com/docs/r/intelligent-experiences/gg-creating-aia.html

**Traps:**
- `cedarpolicy.com/en` is a 404. www.cedarpolicy.com is only the Playground app.
- ServiceNow URLs with no release segment open the current release (Brazil). Kill Switch isn't in Brazil, so use the `australia/` URL: https://www.servicenow.com/docs/r/australia/intelligent-experiences/aia-kill-switch.html. It is a circuit breaker for runaway triggers, not an emergency stop for an agent.
- docs.aws.amazon.com, servicenow.com/docs and catalog*.workshops.aws return 200 for made-up paths: check the page title, or the GitHub / ServiceNow search APIs. The hackathon's workshop pages also need a login.
- The sibling AI Native Networks workshop can be read without a browser via `published.json` → `manifest.json` → content Markdown. Never run its cleanup scripts (see [[hackathon-working-agreement]]).

Related: [[servicenow-context]], [[challenge-requirements]], [[platform-verified-facts]]

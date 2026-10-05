---
name: platform-observations-notes
description: "Pointer to the repo's platform-observations file (64 items as of 2026-10-05; #24 = cockpit leaks the ledger write token; #37–#40 = tool authorization / identity gaps; #41–#47 = Module 6–7 backlog) and how to frame it — context for the platform team, not build targets"
metadata:
  node_type: memory
  type: project
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T03:14:03.297Z
---

Repo file `notes/platform-observations.md` is the running, evidence-backed list of where the live platform, kit or guide differs from what the guide claims. The user is reviewing it with the platform team on 2026-10-05. It is not part of the hackathon submission. Committed and pushed to GitHub main (first commit 03ff0bf, 2026-10-05). Details live in the file; this note records how to use it.

- **Items #1–#23 (as of 2026-10-05 ~03:00 UTC; #24–#31 are listed further down):**
  - bugs: #1 checkpoint awk; #19 self-check can't pass; #21 traceparent dropped
  - security: #2 public plain-HTTP gateway, already scanned; #3 verified side entrance, contradicting the diagrams
  - doc accuracy and drift: #4, #5, #6, #8, #16, #18, #20, #23
  - design note: #7
  - to-verify: #9; #22 prompt text in spans
  - checked OK: #10
  - robustness: #11
  - documented limitations: #12, #13
  - noise: #14
  - misleading status: #15, #17
- **#13 was corrected on 2026-10-04:** it is NOT a build target. The masterclass says signatures and hash chains are out of scope.
- **The user approved (2026-10-04 CDT) and Claude added:**
  - the #2 scanner traffic and #3 diagram quotes
  - #16–#18
  - the reference-agent mismatches #19–#23
  - the header fix (Module 2 Step 6 skipped)
- **Added 2026-10-05 ~03:30 UTC on the user's "add them now" (#24–#31):**
  - #24 (lead security item): the ledger write token is a literal env value in AgentConfig specs, AND the cockpit's `/api/cr/AgentConfig/...` view returns it. Verified as a yes/no match without printing it. So anyone with the cockpit link can forge ledger records.
  - #25: the cockpit has no own auth and has a POST that invokes agents (the guide calls it read-only 3 times).
  - #26: participant RBAC is cluster-wide `admin`; secrets, pods and port-forward in kube-system, agentgateway-system, modaas-system and canvas-vault.
  - #27: run ids are missing from the durable gateway log.
  - #28: nano-9b keeps "paused" status after resume.
  - #29: the telemetry tap was not shipped, so the cockpit live panels are empty.
  - #30: the AICT stack description contradicts the IAM user and access key that were created.
  - #31: the unsafe-model example trips two admission rules.
- #10 and #3 got cross-references to #24 and #26.
- #17 got the guide's explanation (Module 5 overview), on the user's "add it": the operator egress policy blocks inventory port 8639, which is confirmed. Who writes the 15 records is still unidentified; it is not the cockpit.
- #32 added 2026-10-05 (user: "ADD"): the guide's Module 6 says the trace pipeline has no durable exporter; it exports to X-Ray.
- #33–#35 added 2026-10-05 (user: "add the three possible notes"): #33 a team Cedar policy is inert (one policyId per decision; `x-modaas-policy-id` is not forwarded by extAuth); #34 the Cedar step expects an undeclared-model DENY that Module 5 no longer produces; #35 a guardrail-blocked call is recorded as ALLOW in the PDP log AND /modaas/evidence.
- #36 added and #28 updated 2026-10-05 (user: "Add them"). #36: the kill switch took 33–41 s, served meanwhile; the guide says "instantly". #28: reproduced on a clean cycle, resume never clears the pause conditions.
- **#41–#47 added and #19/#28/#36/#37 updated on 2026-10-05** (the user asked "what do i need to do… can you run it on your end" about the Module 6–7 backlog). Everything was re-verified read-only first:
  - #41: the ceiling's "1 req/s per agent" is wrong (3 agents = 180/min). The request limit never stopped the S2 loop: peak 49/min, 2.0M tokens = 80%/h.
  - #42: the guide gives two sources for cockpit cost. The code uses AWS/Bedrock (per model id), and super-120b/-helper share one id.
  - #43: the S1 IT 403 is a fail-closed PolicyEngineUnavailable DENY (in /modaas/evidence). The gateway line has no run/action id, and the ledger says 500 on the model.
  - #44: the S2 runaway is invisible in the ledger.
  - #45: the self-check checkpoint hardcodes S1; S3 chains graded as S1 → 5/8.
  - #46: the model swap had no re-review, and the re-attest annotation adds no approval record.
  - #47: the compare grep matches 0 lines.
  - Updates: #19 confirmed live (grade table); #28 also on ToolConfig modaas-docs; #36 tools ~1 s vs models 33–41 s; #37 the cross-tool pattern is also in the first S1 run.
- **#37–#40 added 2026-10-05 (user: "add", after the Cedar check):**
  - #37: agents call tools they don't declare, all ALLOW (the PDP uses the called tool's policy; one shared identity; the route isn't in the Cedar context). Evidence names it via `route_alias`.
  - #38: per-agent Keycloak identities are declared but not provisioned (listenerRegistered=false, no client secrets, all model permits bootstrap-key, all 24 evidence records bootstrap-key).
  - #39: the AgentConfig `spec.access.cedarPolicy` / `agentPolicy` overlay is documented but not wired. Source-based, not live-tested.
  - #40: customer-records and network-twin have no dataClassification, so their "restricted" clause can't fire.
  - The header's coverage line was also updated to Modules 2–7 plus Module 8 step 1 (it wrongly said the agents had not been run).
- **Added 2026-10-05 (user: "add", after Module 8):**
  - #22 RESOLVED in place: spans carry the system prompt and context incl. customer records; completion text likely but not opened.
  - #48: all 4 runtimes share one IAM role (deck p13 says each has its own). Its explicit Deny confirms the gateway is the only model path; peer InvokeAgentRuntime on runtime/* (resource policies untested).
  - #49: Strands span shape (48 vs 8) + show-run-spans 2× totals, so both Module 8 checkpoints fail.
  - FYI section: the participant keys can search logs (FilterLogEvents), the IDE role can't (GetLogEvents only), so the guide is right for the IDE.
- **#50–#53 added 2026-10-05 (user: "add"):**
  - #50: Module 9 doc drift (helper model/tools; modaas-docs custom vs Lambda; helper-docs is the Lambda tool).
  - #51: the helper's thin evidence (2 records, a citation without a tool call, 15 session-setup decisions).
  - #52: the helper's drafts fail a dry run, and it claims the change was made.
  - #53 (To verify): the get_doc allow-list.
  - FYI: the S3-synced kit loses exec bits, and the download lists omit ask-agent.sh.
- **Candidates from Step 1b/Step 2, not yet proposed:**
  - #37 update: Step 1b says the toolName clause "restricts the ToolConfig route to only the tools declared… Without it, the route would admit every tool on the shared AgentCore Gateway". With AR-11 (the called tool's policy decides), the route admits every approved tool regardless (#37 evidence), so the explanation is outdated.
  - #46 cross-ref: Step 2 itself states "An image change is not re-reviewed".
  - Step 2: "admission refuses" a missing safety block. The server dry run ACCEPTS it, so the check is operator-side (composition/checks.py).
  - #2 update: every agent runtime is injected with the PUBLIC ELB over plain http (:8081 model, :8080 MCP), so the team key is sent unencrypted on every call, despite VPC mode and a TLS :8443 listener.
  - new-agent.sh `--tool X` adds only env vars (TOOL_MCP_URL/ALIAS), so `dependsOn.tools` stays EMPTY and the declaration and registry don't name the tool the agent uses (my-agent calls modaas-docs).
  - **Step 3 (2026-10-05):**
    - The page expects "disposition: blocked by guardrail"; the template records "undetermined" (no such path).
    - The kill-switch block pauses nano-9b and says "every agent … depends on this model", but Step 1b builds my-agent on super-120b.
    - #36 update: the super-120b pause took effect in ≤2 s (vs 33–41 s for nano-9b), so latency varies.
    - #28 reproduced on super-120b.
    - #35 extension: a pause refusal (404) is also recorded as ALLOW in /modaas/evidence, and its gateway line has no run/trace/action id.
  - Minor: new-agent.sh passes the SDK packages in EXTRA_PIP, which Step 2 says never to do (the same versions as the pins, so harmless).
- **Candidates from Module 10 Step 1 (2026-10-05), not yet proposed:**
  - The page's "ask the twin" and its checkpoint run `example_app.py`, which uses its own `example_test_model`, not `tokyo-rf-twin`. The checkpoint output is identical before and after retraining, so it tests nothing about the retrained twin.
  - FYI (outside the IDE): setup-digital-twin.sh assumes Linux (GNU `sed -i` aborts it under set -e on macOS; `ss`; python3 must be <3.11).
  - On a laptop, RADP publishes :8090 and kafka :9094 on 0.0.0.0.
- **Added 2026-10-05 by a writer subagent** (user: "add the notes updates by a subagent and get it reviewed"):
  - updates to #2 (agents use plain HTTP via the public LB), #28 (super-120b), #35 (+ kill-switch ALLOW), #36 (≤2 s pause), #37 (Step 1b's outdated Cedar claim), #46 (the guide's image admission)
  - new #54 (Step 2 claims: no-safety accepted, EXTRA_PIP), #55 (--tool leaves dependsOn.tools empty), #56 (Step 3 expectations; "blocked by guardrail" exists only in reference-impl/strands-agent-agentcore.py:79)
  - The writer corrected: EnforcementNotDeclared also appears as a CRD comment in the source zip (the comment says such an agent is "admitted … but never reaches phase=Approved"); the durable 404 copy has a trace id.
  - The independent review passed its 5 live spot-checks. Its 7 wording/consistency fixes were applied (headers/rows for #28, #35, #36; #37 marked source-based; #54 create-vs-update and CEL detail) before the first commit.
- **#57–#58 added 2026-10-05 (user: "a now"):** #57 the recipes can't produce their artifacts as shipped; #58 breach on demand can't reach the agents, three-site coverage, S2 no site, element-id queries.
- **Added 2026-10-05 (user: "add"):**
  - #59 (security, policy-level): participant creds may update/invoke/re-permission all governed tool Lambdas; ToolConfigs are unpinned.
  - #60: Module 10's "ask"/checkpoint use example_test_model, not tokyo-rf-twin.
  - #37 update (Module 10 repeats the Cedar claim).
  - FYI: setup script Linux assumptions; 0.0.0.0:8090/9094 on a laptop.
  - The Module 10 Step 1 candidates are now all added.
- **Added 2026-10-05 (user: "add"), from the Challenge section:**
  - #61: the C16 example's 700–1050 tokens vs our 25K–50K runs
  - #62: evaluate.py is C16-only and reads rather than pulls; the kit's C9 framing differs
  - #63: submit.sh needs the team name
  - #27 update: pull-evidence.sh depends on the pod's stdout for run ids
- **#64 added 2026-10-05 (user: "add"):** Choosing a Model: same tokens per call on 9B vs 120B (cost differs); stale approval states; 24 s vs "~10 s".
- **Candidates from Reference: Network Tool Naming (2026-10-05), not yet proposed:**
  - the stale "plain HTTP /handle, /negotiate" claim about the network agent (it uses /mcp/network-twin)
  - the quoted heredoc leaves `${MODAAS_GATEWAY_ID}` literal
  - "cedarPolicy scoping agent identities" is impossible (→ #38 cross-ref)
  - The page's citation of the AI Native Networks workshop: the cited page has no callable tools (22 names as "potential projects"), no stated `<domain>_<verb>_<resource>` convention, and the quote is a paraphrase.
- Add an item only with evidence, and ask the user before editing the file (see [[hackathon-working-agreement]]).

**Why:** the user said these findings are not what the hackathon wants built.
**How to apply:** cite them as platform context or gap-list background, never as the project's goal.

Related: [[prooflab-project]], [[platform-verified-facts]], [[workshop-progress]]

---
name: challenge-requirements
description: "The workshop's 'The Challenge' section (Challenge page, Control 16 worked example, Evidence cookbook) — the six required steps mapped to the platform, the two-minute finish line, the six auditor questions, the kit tooling as it really behaves, and the critical questions the planning session must answer; the masterclass C16 example (cap 10,000) differs from the guide's (900); the 'What the platform gives you' page (extracted from the workshop KB, verified live 2026-10-05: six enforcement points, team code only in the runtime and, with the token, the ledger; its gateway grep is broken); which inputs are still pending"
metadata:
  node_type: memory
  type: project
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-05T19:44:10.836Z
---

The user pasted this section on 2026-10-05 to build context for planning. The plan is made in a FRESH session after the ServiceNow section and the shared PDFs are added. The master class brief is still the authority for "done", the judging axes and the artifacts; this section only maps them onto the platform.

**Finish line (verbatim):** *"You are done when somebody who is not on your team can ask 'was control 9 satisfied for run FM-B?' and get an answer in two minutes, with the records behind it."*

**The six required steps, as the platform maps them:**
1. **Choose controls:**
   - C7, event recording (the audit ledger, Module 7)
   - C9, drift (AgentCore metrics, Module 8)
   - C16, spend cap (the gateway per-call line, Module 5 §8). C16 is IN SCOPE (user).
2. **Declare thresholds** in `register.yaml`, dated before the first assessed run. Fields: metric, observation_limit, exception_tolerance, measurement_basis, owner, version, version_date, enforcement_point.
3. **Where in the timeline:** post-run forensics is the floor; inline in the request path is a bonus. The enforcement point is the shared gateway modaas-agw. The "What the platform gives you" page lists six enforcement points; it was extracted from the workshop KB and verified on 2026-10-05 (see below).
4. **Build the control:** emit records bound to the control, the threshold version and the run.
5. **Control test / evaluators:**
   - `starter/evaluate.py`: control id + run id in, PASS/BREACH/NO EVIDENCE with record ids out; exit 0/1/2.
   - `score-run.py` grades fault resolution (evidence shape). For INTEGRITY it shows completeness and capture consistency and gives a reproducible verdict, but it can't detect altered records (details in [[prooflab-project]], the user's review of 2026-10-05).
6. **Run both ways:** one passing and one breaching NAMED run (run-ids.txt), plus `gap-list.md`.

**Verified in the primary sources (2026-10-05, lead's playbook check; repo `notes/playbook/playbook-verification.md`):**
- Axis 1 wording "nothing to score / in the running / ahead / the full set" and Axis 2 "does the control hold its own threshold?": Immersion Day slides.
- The playbook's "five habits" are all verbatim on the Immersion Day slides, p15 ("FIVE HABITS THAT KEEP THE DESIGN HONEST"): "The telemetry store never judges", "The evaluator never remembers", "The control register is never in the path of execution", "The evidence ledger never interprets", "Records are sealed where they are made [out of scope]" (per the handoff writer; re-checked in the slide text 2026-10-05). The meeting transcript says the same, ending "the records are sealed and signed in the place where they are made. Again, not part of the scope".

**The six auditor questions are a sidebar, not a step:** WHO / WHAT / AUTHORIZED / APPROVED / INTEGRITY / RECONSTRUCT, answerable "from your Evidence Pack alone, for an incident the judges pick from your event window".

**Standard surfaces** (use only these, no privileged access):
- TMF639 inventory
- CR status + conditions
- approval annotations
- gateway request/response records
- registry records
- OTEL traces

**Hand-in:** `submit.sh` packages ~/evidence/, register.yaml, gap-list.md, run-ids.txt (and a sketch) and uploads to the team bucket. **It needs the team name as an argument** (`TEAM="${1:-}"`); the page's bare `bash ~/starter/submit.sh` prints usage. Judging reads from the bucket.

**Kit tooling as verified read-only on 2026-10-05:**
- **`pull-evidence.sh <run>`** writes 6 files: tmf639.json, cr-status.json (Model/Tool/AgentConfigs), approvals.json, gateway-log.json, registry.json, otel-traces.json.
  - gateway-log comes from the POD STDOUT: `kubectl logs <pod> --tail=50000 | grep -F <run id>`.
  - The pod held 1,779 lines from its start (2026-10-04 10:35 UTC), incl. all our runs. A pod restart loses the pod log, which `pull-evidence.sh` and `evaluate.py` read as shipped, but not the run ids: the gateway's spans in CloudWatch `aws/spans` keep run id + per-call tokens for 30 d (confirmed live 2026-10-05). The `/aws/modaas/gateway` copy has no run_id (gap 7).
  - **cr-status.json holds the ledger write token (2026-10-05, from source):** `pull-evidence.sh:78` dumps the full Model/Tool/AgentConfig JSON, specs included. `submit.sh` zips ~/evidence as it is, uploads it to the team evidence bucket (stack output `TeamEvidenceBucketName`; judges read it) and leaves the zip in the directory it ran from. Redact env values before submitting (gap-list gap 6; repo `.gitignore` now ignores `*.zip`). It holds the ledger token, not the gateway key, which lives only in the runtime env (live 2026-10-05).
- **`evaluate.py` implements ONLY control 16** (`_METRICS = {"16": …}`): it filters gateway records by `modaas.run_id`, sums input+output tokens, and compares with observation_limit. **C7/C9 evaluators must be written by us.**
- **Kit `register.yaml`:**
  - C16 limit 2000.
  - C7 = "count(distinct phase per correlation_id) / expected phases (intent, invocation, result-inspection) across all three agents", limit 1.0, basis evidence['otel-traces'].
  - **C9 = placeholder**, whose example metric is "disposition-match-rate against score-run.py's expected disposition". That differs from the Challenge page's "drift = AgentCore metrics".

**The C16 worked example (guide, 2026-09-29):**
- cap 900, version G-FM-v1; *"a real fault-resolution run on this platform uses 700-1050 tokens across the three agents"*; example PASS 778 / BREACH 1030.
- **OUR measured runs are 25–50× larger:** S1 24.8K–50.2K, S3 ~37.8K, swap-S1 37.7K, S2 2.0M; my-agent's docs question 7.3K. A 900 (or 2000) cap would breach every run. The guide's numbers come from a 1-call-per-agent nano-9b agent. Our threshold must come from our own runs (cf. the judge's risk-matrix hint in [[prooflab-project]]).
- **The masterclass's C16 example is a DIFFERENT one (slides; confirmed 2026-10-05 in the lead's playbook check):** cap 10,000, FM-A 9,600 → SATISFIED, FM-B 10,800 → NOT satisfied. Don't mix it up with the guide's 900 (778 / 1030). Either cap would breach every S1/S3 run we measured.
- **The gateway records** tokens per call with run_id (stdout, and durably on its spans in `aws/spans`, 30 d), a per-account request ceiling (429), a per-account token ceiling (429), and prices every call.
- **It does NOT** sum per run inline, cap per run inline, let Cedar see token counts, or cap cost.
- Inline per-run enforcement = bonus.

**Evidence cookbook:**
- One command per surface into ~/evidence (checkpoint: ≥6 files).
- Correlation map: ledger/evidence correlation_id; gateway modaas.run_id; traceparent = modaas.trace_id (gateway) / trace_id (PDP); action_id in PDP, gateway, /modaas/evidence and the response header.
- Caveats already in the notes: the timeline is text; spans double-count (#49); the durable gateway log `/aws/modaas/gateway` has no run_id (#27), though the gateway's spans in `aws/spans` do.

**Critical questions the plan must answer:**
1. Which controls, and why (C16 certain; C7 and/or C9)?
2. Threshold values justified from OUR measurements and a risk framing (the judge's risk-matrix hint), dated in register.yaml before the first assessed run.
3. Post-run only, or inline at the gateway (bonus)? What can actually run inline?
4. Evaluators for C7/C9 (none shipped); evidence durability (pull before a pod restart; `aws/spans` keeps run ids + tokens for 30 d).
5. Two named runs per control (pass + breach), reproducible on demand.
6. The two-minute answer: one command → verdict + record ids.
7. Evidence Pack coverage of the six auditor questions, given our gap list (gaps 2–7, 11).
8. The agent judgment gap (gaps 1, 10): gather evidence / escalate.
9. The twin fixtures (plan item b).

**"Reference: Choosing a Model" (pasted 2026-10-05; user: the ready-made CR catalog = Module 6):**
- **Declarable via ModelConfig:**
  - nemotron-nano-9b → nvidia.nemotron-nano-9b-v2 (9B, 128K)
  - nemotron-nano-3-30b → nvidia.nemotron-nano-3-30b (30B / 3B active MoE, 256K)
  - nemotron-super-120b → nvidia.nemotron-super-3-120b (120B / 12B active, 256K)
  - Also nvidia.nemotron-nano-12b-v2 (vision-language) is Bedrock-serverless with no CR shipped.
  - Ultra / older Nemotrons only via Bedrock Marketplace = SageMaker endpoint (provider aws-sagemaker, onboard-only). Custom Model Import doesn't support Nemotron.
  - No cross-region prefix: in-Region us-east-1.
  - Nemotron may emit `<think>` inline (the reference agents send `/no_think`).
- **Page vs live/measured:**
  - "Only nano-9b arrives Approved": live, ALL 4 are Approved (nano-3-30b and super-120b-helper by system-admin at bootstrap; nano-9b and super-120b by cloudshell-user@team).
  - "runtime updated in ~10 s": we measured 24 s.
  - "an agent pointed at an unattested model is refused 403 / the composition gate refuses it": UNTESTED (no unapproved model exists).
- **C16 nuance (our data, swap run fault-1791179282-8ef1a8):** tokens per call are the SAME across models (IT on nano-9b ≈4,225/call; customer/network on super-120b ≈4,173/call), because the prompt and context dominate.
  - So the page's "far fewer tokens on the 9B" isn't supported. Model choice changes COST (~$0.064 vs ~$0.161 per M), not token count.
  - A token cap is driven by call count and context size, i.e. agent behaviour.

**"Reference: Network Tool Naming" (pasted 2026-10-05; checked read-only plus server dry runs, nothing stored):**
- **Convention** (from the AI Native Networks Immersion Day): `<domain>_<verb>_<resource>` named after 3GPP interfaces (amf_manage_ue/N2, smf_create_session/N4, nrf_register_nf/SBI, f1_setup_control/F1-C). Example ToolConfig `smf-create-session` (agentCoreGateway, safety.required + approval.required).
- **Verified:**
  - The sample passes a server dry run.
  - **The admission rule is CONFIRMED:** safety.required without approval.required is refused ("no silent auto-approve; pre-existing assets with unchanged safety are grandfathered").
  - `kubectl explain …mcpServer` matches the page.
- **Wrong on the page:**
  - The quoted heredoc leaves the literal `${MODAAS_GATEWAY_ID}` in the CR. The dry run still passes; a real apply would point at a nonexistent gateway.
  - "network-resolution-agent … plain HTTP (/handle, /negotiate), not a governed MCP tool" is stale: 15 governed tools/call on /mcp/network-twin in 24 h.
  - "cedarPolicy scoping which agent identities" is impossible with one shared identity (#38).
- **Hackathon tip from the page:** a governed tool call is a second enforcement point for C7. Coverage across model AND tool calls is stronger evidence.
- **AI Native Networks workshop: DONE (3 web subagents; the cleanup claim was re-checked from the script).** Synthesis in repo `notes/ai-native-networks/ai-native-networks-context.md`.
  - **SAFETY:** its cleanup scripts delete ALL AgentCore gateways, runtimes and memories in the region. NEVER run them (rule in [[hackathon-working-agreement]]).
  - Claude 3.7 Sonnet, no guardrails, no approvals, a shared hard-coded Cognito user, broad gateway role; agents never wired to the twin or the 5G network.
  - **The guide's tool-naming claims vs source:**
    - the cited page lists 22 names as "potential projects" (no code)
    - the `<domain>_<verb>_<resource>` convention is NOT stated
    - the 4 example names are verbatim
    - the 3GPP mapping is partial
    - the quoted sentence is a paraphrase
  - Sources are public via `static…/public/quicklinks/ai-native-networks/published.json`.

**"What the platform gives you"** (`/challenge-brief/platform-contract`; never pasted. Extracted from the workshop KB on 2026-10-05 into repo `notes/workshop-reference/platform-contract.md` and verified live, read-only; report `notes/verification/2026-10-05/platform-contract-verify.md`; handoff §5.9):
- **Six enforcement points; team code only in two.** The page lists gateway+PDP/Cedar, Bedrock Guardrails, admission (CEL) and the ledger as "Refuse", and AgentCore Runtime and the collector/CloudWatch as "Observe". It allows team code only in the runtime and, with the token, the ledger. "Cedar does not meter tokens." So by the page, inline C16 means our agent code on the runtime.
- **No Cedar policy has ever refused.** The PDP shows 0 DENY in 1,097 decisions (both replicas). The 24 DENYs in `/modaas/evidence` are 23 keyless `NoSigV4Credential` and 1 fail-closed `PolicyEngineUnavailable`. "Cedar policy via ConfigMap" works only through an asset's policy (ToolConfig `access.cedarPolicy`): `my-team-policy` was named in 0 of 1,097 decisions.
- **The page's gateway grep `modaas.run_id=$CID` matches nothing:** the line quotes its values (`modaas.run_id="<CID>"`). Use `grep -F "modaas.run_id=\"$CID\""` (S2: 353 lines). Its PDP command (`--all-pods=true`) does read both replicas.
- **Its checkpoint prints 6, not 4,** all Accepted.
- **Contradicted or partly wrong:**
  - "per caller": there is one principal
  - "ids/tokens/cost on every call": 573 refused or unrouted lines carry no ids
  - "refusal within 15 s": nano-9b 33–41 s
  - "conditions settle within ~2 min": stale pause conditions remain
  - the AgentCore spans helper totals 2× the gateway
- **Untested:** its three breach recipes (writes).
- **New, RBAC read only:** participants may update the CRDs that hold the CEL rules, and may edit `AgentgatewayPolicy` objects (`extAuth`/`extProc` hooks exist). RBAC confirmed with `kubectl auth can-i` (2026-10-05), but the admission VAP `modaas-governance-guardrail` refuses these writes by its text (untested), so neither is open to us in the protected namespaces. The VAP leaves `components` open, so Cedar changes on our own ToolConfigs pass it. By its text it also leaves open a route plus a policy in a team namespace, because the Gateway admits routes from all namespaces (untested). Independent review 2026-10-05 ~19:35 UTC. Details in [[platform-verified-facts]].

**Inputs (updated 2026-10-05):**
- **Done:**
  - the ServiceNow section (Module 11 AI Control Tower) and the shared PDFs
  - the "Resources & How-To" page and the Glossary (both checked against live; see [[platform-verified-facts]])
  - "What the platform gives you" (from the workshop KB, not pasted; verified live 2026-10-05, above)
- **Still pending:** the Evidence Pack format (from the user), more slides.

Related: [[prooflab-project]], [[workshop-progress]], [[platform-verified-facts]], [[reference-agents-facts]]

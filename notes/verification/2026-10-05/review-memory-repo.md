# Independent review: 2026-10-05 changes to memory and repo

Reviewer: independent subagent, read-only. Date: 2026-10-05 (UTC).

Paths used below:
- **mem/** = `/Users/satyabratsrikumar/.claude/projects/-/memory/` (primary). The mirror `…/-Users-satyabratsrikumar-firstmate-homes-TrustworthyAI-TrustworthyAI-iFabric/memory/` is byte-identical (`diff -r`: no output).
- **repo/** = `/Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/TrustworthyAI-iFabric/`
- **snap/** = `/Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/evidence-snapshots/20261005T173727Z/`
- Line numbers are the current files' (memory line numbers include the frontmatter).

**How memory fixes must be applied:** edit the primary, `rsync -a --delete` to the mirror, then re-copy into `repo/notes/claude-memory/` (commit bfb1ce6 is pushed, `main` is level with `origin/main`, and its message promises "the reviewed version follows in the next commit").

## Counts

| Severity | Count |
|---|---|
| ERROR (factually wrong) | 10 |
| IMPRECISE (misleading or overstated) | 11 |
| GAP (important verified fact missing) | 7 |
| STYLE | 6 |

## Live checks run for this review (all read-only)

- `kubectl explain agentconfig.spec.modelRef / .spec.dependsOn`. Live CRD CEL rules (JSON, filtered). AgentConfig `.spec.modelRef`, `.spec.dependsOn`, generation and phase (jsonpath). Spec env **names** only (go-template over map keys). Runtime env **keys** plus the `MODEL_ALIAS` value only (`get-agent-runtime --query`).
- Operator source `workshop-assets/modaas-aigateway-src.zip` (`unzip -p`, grep).
- One `s3api get-bucket-versioning` call. The participant policies' S3 statements (`iam get-policy-version`). `list-objects-v2` (KeyCount only). The `submit.sh` bucket-lookup query, filtered to `TeamEvidenceBucketName`.
- AgentgatewayPolicies `modaas-telemetry-export` and `modaas-access-log` (spec). Collector ConfigMap (pipelines, processors and exporters only).
- X-Ray `batch-get-traces` on 5 traces (segment names, attribute key names, `modaas.run_id`/`modaas.action_id` values and token counts extracted; no span content or event payloads printed). `logs filter-log-events` on `aws/spans`, `/modaas/evidence` and `/aws/modaas/gateway` (counts only). `describe-log-groups` (retention).
- EKS logging. Approval records (`signature` field). PDP-labelled ConfigMaps. CRD list.
- Snapshot: all 8 sha256s re-computed (all match the MANIFEST), line counts, run-id count, pattern scan.
- Secret checks: the pre-push scan's pattern regex over memory, `gap-list.md`, `notes/references/`, `notes/playbook/`, `notes/claude-memory/`, `notes/verification/`, `PLANNING-HANDOFF.md` and the snapshot: **clean**. Exact-value checks (loaded into variables, file counts only) for the gateway key, the three hackathon AWS profile values, CockpitUrl, IdeUrl and their tokens: **0 files each**. **The ledger write token was NOT exact-value checked**, by rule (only its key name was read).
- External: curl/GitHub API/ServiceNow docs search for 8 links in `links.md`. All match.

---

## Findings, ranked

### ERROR

#### E1. The run id IS durable: the gateway's spans in X-Ray and CloudWatch Logs `aws/spans` carry the CID, action id and per-call tokens (root error, 10 locations)

**Evidence (2026-10-05):**
- `modaas-telemetry-export` `spec.frontend.tracing.attributes.add` sets `modaas.run_id <- extauthz.correlationId` and `modaas.action_id <- extauthz.actionId` on the gateway's spans (`randomSampling: "true"`, `clientSampling: "true"`). The collector's `traces` pipeline exports them to `awsxray`.
- X-Ray `batch-get-traces`, `modaas-agw` segments carrying `modaas.run_id` = the CID:

  | Run | Spans with the CID | Tokens | Stdout figure of record |
  |---|---|---|---|
  | `fault-1791179282-8ef1a8` | 24 (of 45 gateway segments) | 36,862 + 802 = **37,664** | 37,664 |
  | `fault-1791177636-8fa0bd` | 24 | **37,836** | 37,836 |
  | `my-agent-1791190861-638235` | 7 | **7,313** | 7,313 |
  | `my-agent-1791191546-6aa5dd` (guardrail block) | 1 | **0** | 0 |

  The segments also carry `gen_ai.request.model`, `gen_ai.tool.name` and `agw.ai.usage.cost.*`.
- CloudWatch Logs `aws/spans` (retention **30 d**, live) holds the same spans and can be searched by CID with `filter-log-events`:
  - `fault-1791179282-8ef1a8`: 24 spans, 37,664 tokens
  - `fault-1791177636-8fa0bd`: 24, 37,836
  - `my-agent-1791190861-638235`: 7, 7,313
  - **S2 runaway `fault-1791177342-d3f892`: 353 spans (174 `llm` + 179 `http`), 1,992,059 + 6,942 = 1,999,001**, exactly the 353 stdout lines and the memory figure.
- `/aws/modaas/gateway` still has **no** CID: 0 hits for the CID, 30 for its trace. `/modaas/evidence` has 24 hits for the CID (`correlation_id`).
- Some gateway segments lack the ids (21 of 45 in the swap trace), and so does a call refused before routing (see E6).

**Replacements:**

| File:line | Current (quote) | Replacement (exact) |
|---|---|---|
| mem/MEMORY.md:8 | `where evidence really lands (run ids only on ephemeral gateway stdout; durable join via trace_id→/modaas/evidence), X-Ray, TMF639,` … `2026-10-05 page checks (authz log empty, X-Ray action_id join, PDP/authz pod-only, get-agent-runtime exposes env tokens)` | `- [Platform verified facts](platform-verified-facts.md) — where evidence really lands (run id = CID durable in the gateway's spans in X-Ray + CloudWatch aws/spans with tokens, 30 d; not in /aws/modaas/gateway; /modaas/evidence correlation_id = CID), TMF639, cockpit (no own auth, tap not shipped); Cedar levers (tool policies live, agent overlay not wired), one shared bootstrap-key identity, cross-tool calls allowed; 2026-10-05 page checks (authz log empty, PDP/authz pod-only, get-agent-runtime exposes env tokens); evidence snapshot + ledger PVC` |
| mem/platform-verified-facts.md:18 | `- **Run IDs live only in the gateway pod's stdout,** which is ephemeral. That is where the access-log policy's …` | `- **Run IDs are on the gateway pod's stdout (ephemeral) AND, durably, on the gateway's trace spans (verified 2026-10-05 by an independent reviewer).** The access-log policy puts `modaas.run_id` (= baggage CID), `modaas.trace_id` and `modaas.action_id` on stdout lines. The telemetry-export policy puts `modaas.run_id` and `modaas.action_id` on the gateway's spans, which land in X-Ray and CloudWatch Logs `aws/spans` (both 30 d) with `gen_ai.usage.*` tokens, cost and model. On 4 CID-tagged runs the spans' count and token sum equal the stdout figure of record (e.g. `fault-1791179282-8ef1a8`: 24 spans, 37,664; S2 `fault-1791177342-d3f892`: 353 spans, 1,999,001). Search: `aws logs filter-log-events --log-group-name aws/spans --filter-pattern '"<CID>"'`. The kit's `pull-evidence.sh` still reads stdout (`kubectl logs --tail=50000`), and `evaluate.py` filters on `modaas.run_id`.` |
| mem/platform-verified-facts.md:144 | `- **X-Ray action_id join:** sampled … whether it holds a CID for a CID-tagged run is untested, so "run ids only on gateway stdout" stands until checked.` | `- **X-Ray / aws/spans join (CID case checked 2026-10-05 by an independent reviewer):** the gateway's `modaas-agw` spans carry `modaas.action_id` and `modaas.run_id`. For CID-tagged runs `modaas.run_id` IS the CID (4 runs, every governed call; see Run IDs above); with no CID it is the trace id. So run id → action ids → `/modaas/evidence` (decision, policy version) is a durable join (30 d). These are the GATEWAY's spans; the agents' Strands spans still have no action_id (see Spans above). A call refused before routing (a paused model's 404, trace `f5140819…`) has a gateway span with the trace id but no run id or action id.` |
| mem/platform-verified-facts.md:182 | `… and remember that durable per-run joins go through `trace_id` → `/modaas/evidence`, not `modaas.run_id`.` | `**How to apply:** prefer these facts over the handoff, re-verify before assessed runs, and remember that durable per-run joins go by the CID: the gateway's spans in X-Ray / `aws/spans` (`modaas.run_id`, with tokens), `/modaas/evidence` (`correlation_id`) and the ledger (`correlation_id`). Only `/aws/modaas/gateway` and calls refused before routing need the `trace_id` hop.` |
| mem/challenge-requirements.md:47 | `… A pod restart loses run_id attribution, since the durable /aws/modaas/gateway copy has no run_id (gap 7).` | `  - The pod held 1,779 lines from its start (2026-10-04 10:35 UTC), incl. all our runs. A pod restart breaks `pull-evidence.sh`/`evaluate.py` as shipped (stdout only), but per-call tokens stay recoverable by run id: the gateway's spans in CloudWatch `aws/spans` and X-Ray (30 d) carry `modaas.run_id` = CID and `gen_ai.usage.*` (verified 2026-10-05 on 4 runs incl. S2; totals match stdout). `/aws/modaas/gateway` has no run_id (gap 7).` |
| mem/reference-agents-facts.md:28 | `It appears only on the gateway pod's **ephemeral stdout** line. The durable CloudWatch copy has no run id` | `  - The gateway's `modaas.run_id` = the baggage CID (verified on the reference agents). It appears on the gateway pod's ephemeral stdout line and, durably (30 d), on the gateway's spans in X-Ray and CloudWatch `aws/spans` (verified 2026-10-05). The `/aws/modaas/gateway` copy has no run id (see [[platform-verified-facts]]).` |
| mem/reference-agents-facts.md:32 | `- Durable per-run attribution must join CloudWatch `trace_id` → `/modaas/evidence` `correlation_id`.` | `  - Durable per-run attribution: query the gateway's spans by CID (`aws/spans` / X-Ray `modaas.run_id`, tokens included). Only the `/aws/modaas/gateway` copy needs the `trace_id` → `/modaas/evidence` `correlation_id` hop.` |
| mem/platform-observations-notes.md:111 | `- **#27 update:** its suggested fix is already in place … X-Ray gateway segments do carry `modaas.action_id` (and a `modaas.run_id` whose CID content is untested).` | `  - **#27 update:** `modaas-telemetry-export` adds `modaas.run_id`/`modaas.action_id` only to the gateway's trace spans (`spec.frontend.tracing`), not to its OTLP access-log sink (`spec.frontend.accessLog.otlp`, no attributes), which is what feeds `/aws/modaas/gateway`. So #27's suggested fix is NOT in place, and nothing is dropped downstream (the collector's `logs/gateway` processors delete only payload keys). The spans do keep the ids: X-Ray and CloudWatch `aws/spans` (30 d) carry `modaas.run_id` = CID, `modaas.action_id` and tokens (verified 2026-10-05 on 4 runs; totals match stdout). #27's "per-run token evidence can't be joined by run id" after a pod restart is therefore wrong.` |
| repo/gap-list.md:114–127 (gap 7) | whole entry; see the next block | see the next block |
| repo/notes/playbook/playbook-verification.md:56 (row 3, impact cell) | `X-Ray is a durable join surface (action_id → `/modaas/evidence` → PDP) for RECONSTRUCT` | `**Don't put that gap in the gap list; it's false.** X-Ray and CloudWatch `aws/spans` (30 d) are durable join surfaces for RECONSTRUCT and C16: the gateway's span for each governed call carries the run id (CID), action id, model and tokens, and joins `/modaas/evidence` by action id. The PDP log itself is pod-only.` |
| repo/notes/playbook/playbook-verification.md:60 (row 7, reality and impact cells) | `` `run_id` exists only on gateway pod stdout (ephemeral). The exporter sets `modaas.run_id`, but it doesn't arrive in CloudWatch (glossary verifier, #27). 24 h: 627 lines with a CID, 384 with the trace id `` | reality cell: `The gateway `modaas.run_id` = the **baggage** CID (no baggage CID → the trace id). Agents mint their own trace ids, so ledger trace_ids ≠ the run trace (gap 7). `run_id` is on the gateway pod's stdout and, durably, on the gateway's spans in X-Ray and CloudWatch `aws/spans` (30 d, with tokens; verified on 4 runs), but not in `/aws/modaas/gateway`: the telemetry-export policy adds it to spans only, not to the OTLP access-log copy. 24 h: 627 lines with a CID, 384 with the trace id`. Impact cell: `Propagate the CID via baggage. The C16 figure of record is recoverable by CID from `aws/spans`; still snapshot the pod logs for `pull-evidence.sh`/`evaluate.py` as shipped. PDP/authz logs are pod-only (not in CloudWatch). `/modaas/evidence` keeps 30 d; `/aws/modaas/gateway` 7 d.` |

**gap-list.md gap 7, exact replacement for L114–127** (keeps it a gap and keeps the voice; retitled because the CID is durable in three stores):

```markdown
### 7. RECONSTRUCT: not every record of a run carries the run's key

**What's missing:** the run id on every record of a run, including refused calls.

**Why:**
- The run id (the agents' correlation id) is durable in three places: the ledger, `/modaas/evidence` and the gateway's spans in X-Ray and CloudWatch Logs `aws/spans`, which keep each call's tokens for 30 days. But the durable gateway log (`/aws/modaas/gateway`) has none: the gateway adds the run id to its trace spans and its short-lived pod output, not to the copy that feeds that log.
- The policy-decision and authz logs live only on their pods; neither is shipped to CloudWatch. Of the durable logs, `/modaas/evidence` keeps 30 days and `/aws/modaas/gateway` 7 days.
- Ledger records carry trace ids the agents mint themselves, which don't match the run's trace.
- Calls refused at the door carry no run id or action id on the gateway side, only a trace id: the kill-switch 404, and a fail-closed refusal in S1 (`fault-1791175626-0d34e2`). That S1 refusal appears in `/modaas/evidence`, but the ledger reports it as an HTTP 500 on the model.
- The S2 runaway (`fault-1791177342-d3f892`: 174 model calls, 1,999,001 tokens) looks like 16 ordinary ledger records.

**Impact:** replaying a run means joining several stores: by run id for governed calls, but only by trace id for refused calls and the durable gateway log. A refusal or a loop can be missed when reading the ledger alone.

**If you had one more day:** build that join once, and store the reconstructed timeline of each run in the Evidence Pack. Query the gateway's spans by run id (`aws/spans`) for every governed call's action id, model and tokens, link each to its `/modaas/evidence` decision by action id, and pick up refused calls by trace id.
```

Out of scope but affected: `repo/notes/platform-observations.md` #27 (L495 "per-run token evidence can't be joined by run id") is now wrong too. It needs the user's "add" before it is edited.

#### E2. The telemetry-export policy was misread: its ids go to spans, not to the access-log copy, and nothing is "dropped further down"

**Evidence:**
- `modaas-telemetry-export` (generation 1) has `spec.frontend.accessLog.otlp` (collector:4317, **no attributes**) and `spec.frontend.tracing.attributes.add` (`modaas.run_id`, `modaas.action_id`).
- `modaas-access-log` adds `modaas.run_id`/`trace_id`/`action_id` under `spec.frontend.accessLog.attributes`. Those reach stdout, but not the OTLP copy.
- The collector's `logs/gateway` pipeline runs `[attributes/scrub-payloads, filter/not-evidence, batch]` into `awscloudwatchlogs/gateway`. scrub-payloads deletes only `gen_ai.prompt`, `gen_ai.completion`, `gen_ai.input/output.messages` and `modaas.request/response.body`.
- #27's own suggested fix (repo/notes/platform-observations.md:497) is "add the same `modaas.*` attributes to the OTLP access-log export". That is not what the policy does.

**Replacements:**
- mem/platform-verified-facts.md:143. Current: `- The telemetry export (generation 1, unchanged since 2026-10-04 10:36:58 UTC) declares `modaas.run_id` and `modaas.action_id`, but none of the 200 newest `/aws/modaas/gateway` events carries either. They're dropped further down the pipeline; root cause not investigated.` Replacement:
  `  - The telemetry export (`modaas-telemetry-export`, generation 1, unchanged since 2026-10-04 10:36:58 UTC) adds `modaas.run_id` and `modaas.action_id` only to the gateway's trace spans (`spec.frontend.tracing.attributes`), where they arrive (X-Ray, `aws/spans`). Its OTLP access-log sink (`spec.frontend.accessLog.otlp`), which feeds `/aws/modaas/gateway`, declares no attributes, so none of the 200 newest events there carries either. The collector's `logs/gateway` processors delete only payload keys, so nothing is dropped downstream (reviewer, 2026-10-05).`
- mem/platform-observations-notes.md:111: covered by the E1 replacement.
- repo/gap-list.md:119: covered by the gap 7 block in E1.
- repo/notes/playbook/playbook-verification.md:60: covered by E1.

#### E3. Playbook §1.8 ("agents only on AgentCore or in ServiceNow") IS in a primary source

**Evidence:** `repo/hackathon-context/sources/User-pasted-master-brief.txt`:
- L91: "For AWS-hosted custom agents, the organizers specify Strands and AgentCore Runtime. ServiceNow-hosted agents are also allowed."
- L93: "Submitted agents must operate within the provided AWS/ServiceNow environments. Existing code and MCP servers may be brought in if they satisfy the workshop deployment constraints."

**Replacements:**
- repo/notes/playbook/playbook-verification.md:35. Current: `**Not found in any primary source:** §1.8 "Agents run only on AWS AgentCore (Strands) or in ServiceNow; nothing hosted elsewhere". The transcript says … Mark UNVERIFIED.` Replacement:
  `**§1.8 is in the master brief:** "Agents run only on AWS AgentCore (Strands) or in ServiceNow; nothing hosted elsewhere" matches "For AWS-hosted custom agents, the organizers specify Strands and AgentCore Runtime. ServiceNow-hosted agents are also allowed." and "Submitted agents must operate within the provided AWS/ServiceNow environments." (`User-pasted-master-brief.txt`:91, 93). Existing code and MCP servers may be brought in if they meet the deployment constraints (brief L93; the transcript: "you can bring your tools").`
- mem/prooflab-project.md:127. Current: `… §1.8 "agents only on AgentCore or in ServiceNow" is in no primary source (UNVERIFIED).` Replacement:
  `    - Use it as the strategy backbone for what judges reward, with that file's corrections. §1.8 "agents only on AgentCore or in ServiceNow" is supported by the master brief (L91: "For AWS-hosted custom agents, the organizers specify Strands and AgentCore Runtime. ServiceNow-hosted agents are also allowed."; L93: "Submitted agents must operate within the provided AWS/ServiceNow environments.").`
- Also inherited by repo/PLANNING-HANDOFF.md:155 (see G5).

#### E4. The gateway key is NOT in the AgentConfig specs

**Location:** repo/notes/playbook/playbook-verification.md:66 (row 13).

**Quote:** "The platform writes the gateway key and ledger token as literal values in every AgentConfig spec and runtime env"

**Evidence:**
- Spec env names in all 5 AgentConfigs: AGENT_NAME, (AGENT_ROLE), AUDIT_URL, AUDIT_WRITE_TOKEN, STEP_BASE, plus TOOL_MCP_ALIAS / IT_AGENT_RUNTIME_ARN / TOOL_MCP_URL / TEAM. **No** OPENAI_API_KEY or AGENTCORE_GATEWAY_MCP_TOKEN.
- The CRD for `environmentVariables` (`map[string]string`) says: "Names the operator owns are refused. Values are plain text in this CR and in the runtime's configuration."
- The runtimes' env keys include OPENAI_API_KEY and AGENTCORE_GATEWAY_MCP_TOKEN (operator-injected). memory platform-verified-facts L152 already says this.

**Replacement (reality cell):** `The ledger token is a literal value in every AgentConfig spec (`spec.awsAgentCore.environmentVariables`, plain text per the CRD) and in every runtime's env (#24). The gateway key is not in the specs: the operator injects it into each runtime's env as `OPENAI_API_KEY` / `AGENTCORE_GATEWAY_MCP_TOKEN`, and `get-agent-runtime` returns all three in plain text. No `GATEWAY_API_KEY` exists (resources verifier)`

**Replacement (impact cell):** `Fine as agent-code advice (read env, fail closed). The ledger token can't be kept out of the CR; it's a gap-list fact (gap 6)`

Also inherited by repo/PLANNING-HANDOFF.md:253.

#### E5. `new-agent.sh` names ARE validated, by the generator it calls

**Location:** repo/notes/playbook/playbook-verification.md:62 (row 9).

**Quote:** "`new-agent.sh` passes NAME straight into the AgentConfig name, with no validation" … "A server dry-run would settle it formally (needs the user's OK)"

**Evidence:** `workshop-static/reference-impl/make-agentcore-agents.py` (identical in workshop-assets):
- L78: `NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,38}[a-z0-9]$")`, commented "becomes a valid AgentCore runtime name once "-" turns into "_"".
- L287: `own_agent()` raises `InputError("… use 2-40 lowercase letters, digits and '-', starting with a letter (it becomes the runtime name)")`.
- `new-agent.sh:159` calls it with `--name "$NAME"`.

**Replacement (reality cell):** `Kubernetes object names can't contain `_` (RFC 1123), and the generator `new-agent.sh` calls refuses one before anything is applied: `make-agentcore-agents.py:78,287` requires `^[a-z][a-z0-9-]{0,38}[a-z0-9]$` ("use 2-40 lowercase letters, digits and '-', starting with a letter (it becomes the runtime name)"). The runtime name swaps `-` for `_`: CR `my-agent` → runtime `my_agent-9AyPFbHh5Z`.`

**Replacement (impact cell):** `Name CRs `ifabric-…` (at most 40 characters); AgentCore/AICT then show `ifabric_…`. No dry run is needed.`

Also inherited by repo/PLANNING-HANDOFF.md:249.

#### E6. The kill-switch 404's pod line DOES carry the trace id; only the `modaas.*` ids are missing

**Evidence:** the snap/ gateway log has, at 2026-10-05T09:13:06.794Z: `listener=llm route=internal/llm:request … http.status=404 trace.id=f51408192eb04563bbf7299258e2e6e3 span.id=1cc280f6ec63a3d8 … duration=23ms`. That is the same trace as the PDP decision (`trace_id=f5140819…`, action `642489b6…`). The X-Ray segment exists (404; `trace.id` present, no run or action id). repo/notes/platform-observations.md:621 words it correctly: "no `modaas.run_id`, `modaas.trace_id` or `modaas.action_id`".

**Replacements:**
- repo/gap-list.md:72 (pre-existing line, but in the scored deliverable). Current: `  - the gateway's record joins only by trace id: the pod's own 404 line has no run, trace or action id, and its durable copy …` Replacement:
  `  - the gateway's record joins only by trace id: the pod's own 404 line has no run id or action id, only the trace id (`f5140819…`) it shares with the evidence record, and its durable copy in `/aws/modaas/gateway` shows a bare `404` on `/v1/chat/completions`, with no run id, model or reason`
- mem/platform-verified-facts.md:129. Current: `… the pause 404's pod stdout line has no run/trace/action id, but its DURABLE copy in /aws/modaas/gateway carries the OTel trace id …` Replacement:
  `- The guardrail block is visible only as gateway 0 tokens. The pause 404's pod stdout line has no run id or action id, but it, its DURABLE copy in /aws/modaas/gateway and its X-Ray span all carry the OTel `trace.id` (= the evidence record's, e.g. f5140819…), so it joins by trace id. It shows only 404 + path (no model, no reason). Only the agent's ledger says refused (or undetermined, for a guardrail block via the template).`
- mem/workshop-progress.md:198. Current: `… the pod's 404 line has no run/trace/action id, but its durable /aws/modaas/gateway copy shares the evidence trace id (f5140819…) and shows a bare 404.` Replacement:
  `  - **Platform side of the refusal:** /modaas/evidence + PDP = ALLOW (model-nemotron-super-120b v331993). The pod's 404 line has no run id or action id but carries `trace.id=f5140819…` (the evidence record's trace id), as do its durable /aws/modaas/gateway copy (a bare 404) and its X-Ray span. ONLY the agent's ledger names the refusal.`
- mem/platform-observations-notes.md:81. Current: `… and its gateway line has no run/trace/action id.` Replacement:
  `    - #35 extension: a pause refusal (404) is also recorded as ALLOW in /modaas/evidence, and its gateway line has no run id or action id (only `trace.id`).`
- Also inherited by repo/PLANNING-HANDOFF.md:310.

#### E7. The "five habits": the fifth is misquoted, and it IS in the primary sources

**Location:** mem/challenge-requirements.md:30.

**Quote:** "The fifth, "sealing is out of scope", is the playbook's own wording (not checked as a quote)"

**Evidence:**
- The playbook (L234) says "records are sealed where made (out of scope)". "sealing is out of scope" comes from playbook-analysis.md's summary, not the playbook.
- Slides p15 ("FIVE HABITS THAT KEEP THE DESIGN HONEST", slides.txt:425–428) has all five, the fifth being "Records are sealed where they are made [out of scope]".
- The transcript has "And then the records are sealed and signed in the place where they are made. Again, not part of the scope".

**Replacement:** `- The playbook's "five habits" are on the Immersion Day slides, p15 ("FIVE HABITS THAT KEEP THE DESIGN HONEST": "The telemetry store never judges", "The evaluator never remembers", "The control register is never in the path of execution", "The evidence ledger never interprets", "Records are sealed where they are made [out of scope]"). The meeting transcript says the same, ending "the records are sealed and signed in the place where they are made. Again, not part of the scope".`

#### E8. The working agreement misdescribes the secret scan

**Location:** mem/hackathon-working-agreement.md:17.

**Quote:** "patterns: AKIA/ASIA keys, private keys, the `tkn` query parameter with a value, bearer/ghp_/sk-"

**Evidence:** `workshop-local/scripts/pre-push-secret-scan.sh:13`:
- The regex flags the bare cockpit parameter name followed by an equals sign, with **no value required**. Commit bfb1ce6 had to reword memory for exactly this reason.
- It also flags, with no value required, the two AWS credential parameter names (secret key and session token) and the fine-grained GitHub PAT prefix.
- It flags Slack `xox` tokens, AKIA/ASIA key ids, private-key headers, ghp_/sk-/Bearer tokens with long values, and files over 5 MB (L29).
- It scans the whole repo except `.git` and itself.
- The exact-value part fails closed (L17: "COULD NOT LOAD — scan inconclusive").

**Replacement (scan-safe: it contains none of the literals it describes):**

`    - patterns (file names only, whole repo except .git): AKIA/ASIA key ids; the two AWS credential parameter names (secret key, session token) even with no value; private-key headers; GitHub tokens (ghp_ with a long value, and the fine-grained PAT prefix even alone); sk- and Slack xox tokens; long Bearer tokens; and the cockpit's `tkn` parameter name directly followed by an equals sign, EVEN WITH NO VALUE after it. So never write that pair, or those two AWS names, in any repo file or in memory (memory is copied into notes/claude-memory/); write "the `tkn` query parameter" instead. It also fails on any file over 5 MB.`

Optionally add to L18: `It fails closed (NOT CLEAN) if any of these values can't be loaded.`

#### E9. Memory and workshop-local ARE now in the repo and pushed

**Location:** mem/hackathon-working-agreement.md:20.

**Quote:** "workshop-local/ and memory are OUTSIDE the repo and not pushed."

**Evidence:**
- Commit bfb1ce6 added `notes/claude-memory/` (12 memory files + README).
- Commit 468b5e9 added `tools/workshop-local/`.
- `git status -sb`: `## main...origin/main` (pushed).

**Replacement:** `  - workshop-local/ and memory live OUTSIDE the repo, but copies are committed and pushed: memory as a snapshot in `notes/claude-memory/` (bfb1ce6; re-copy after memory changes) and workshop-local as a backup in `tools/workshop-local/` (468b5e9). Both copies must pass the secret scan, so memory text must avoid the scan's literals too.`

#### E10. playbook-verification.md says the verifier reports are not in the repo

**Location:** repo/notes/playbook/playbook-verification.md:11.

**Quote:** "(session scratch files, not in the repo)"

**Evidence:** they were committed in bfb1ce6 as `notes/verification/2026-10-05/{glossary-verify,resources-verify,screenshots-compare,playbook-analysis,playbook-verify-lead,reference-links}.md`.

**Replacement:** `- I also drew on today's verifier reports on the Glossary page, the Resources & How-To page and the guide's cockpit screenshots (in the repo at `notes/verification/2026-10-05/`).`

### IMPRECISE

#### I1. The playbook verdict "§1/§4 trustworthy, §2/§3.9 corrected" is contradicted by its own conflicts table (5 locations)

**Evidence:** the conflict rows cite the playbook's own sections:
- §1.0 twice (rows 7 and 10; row 10 is PB L30)
- §1.7 three times (rows 3, 4 and 5; PB L255, L278, L280)
- §4.1 and §4.4 (rows 11 and 12; §4.4 at PB L560)
- §3.2, §3.3, §3.5, §3.6, §3.8 and §3.10, besides §3.9

memory prooflab-project L126 lists §1.7 and §3.3 claims ("no durable trace exporter", "S2 fails 7/10", the scenario switch, C9 on Average latency) under "§2 and §3.9".

**Replacements:**
- repo/notes/playbook/playbook-verification.md:16. Replacement: `- **§1's brief and scoring rules (§1.1–§1.6, §1.8) and §4's scoring criteria: trustworthy.** Everything spot-checked traces to the primary sources.`
- repo/notes/playbook/playbook-verification.md:17. Replacement: `- **The platform claims in §1.0 and §1.7, §2 (field guide), most of §3 (§3.2, §3.3, §3.5, §3.6, §3.8, §3.9, §3.10) and the ServiceNow items in §4.1/§4.4 import the workshop guide's or the handoff's assumptions,** several of which our live evidence disproves (conflicts 1–17 below).`
- mem/prooflab-project.md:125. Replacement: `    - §1's brief and scoring rules (§1.1–§1.6, §1.8) and §4's scoring criteria are trustworthy: spot-checks trace to the Immersion Day slides, the meeting transcript and the master brief.`
- mem/prooflab-project.md:126. Replacement: `    - The platform claims in §1.0/§1.7, §2 (field guide) and §3 carry workshop-guide claims our live evidence disproves: Cedar denies unauthorized or tampered tools (§2, §3.9), a ledger verification (§2, §3.6), "no durable trace exporter" (§1.7), a ~15 s kill switch (§2), "S2 fails 7/10" (§1.7), a scenario switch for breach on demand (§1.7, §2), C9 on Average latency (§3.3). §3.10/§4.1 and §3.5/§4.4 overstate what ServiceNow shows or enforces.`
- mem/MEMORY.md:1. Replace `(§1/§4 trustworthy, §2/§3.9 corrected)` with `(scoring rules §1.1–§1.6/§1.8 + §4 criteria trustworthy; platform claims in §1.0/§1.7, §2, §3 corrected)`.
- mem/workshop-progress.md:274. Replace `§1/§4 trustworthy, §2/§3.9 carry disproven platform claims.` with `its scoring rules (§1.1–§1.6, §1.8) and §4 criteria are trustworthy; its platform claims (§1.0/§1.7, §2, §3) carry disproven guide claims.`

#### I2. `modelRef` (see resolution 1) (3 locations)

- mem/reference-agents-facts.md:16. Current: `The handoff's "also patch modelRef" doesn't apply: the operator ignores it and generated CRs have none.` Replacement for the whole bullet:
  `- **Models:** the alias comes only from `dependsOn.models[0]`. The operator sets `MODEL_ALIAS` from it (`agent_operator.py:611-616, 961-964`); `modelRef` appears in no operator code, and the 4 agents without it run on their `dependsOn.models[0]`. The generator's default is `nemotron-super-120b`, while `agents.yaml` and the guide's captures use nano-9b. Generated CRs have no `modelRef`. But a CEL rule requires `modelRef` ∈ `dependsOn.models` once it is set, and the guide's Module 7 swap set it on the IT agent (`nemotron-nano-9b`). So any later IT model change must replace or remove `modelRef` too, or admission refuses it (verified 2026-10-05). Per call: `max_tokens=500`, `temperature=0`, `/no_think`.`
- repo/notes/playbook/playbook-verification.md:45. Current: `- **Model swap** = patch both `dependsOn.models[0]` and `modelRef` (Module 7).` Replacement:
  `- **Model swap:** the runtime model (`MODEL_ALIAS`) follows only `dependsOn.models[0]`; the operator ignores `modelRef`. But a CEL rule requires `modelRef` ∈ `dependsOn.models` once set, and the guide's Module 7 patch set it on the IT agent (now `nemotron-nano-9b`), so a revert must change both or remove `modelRef`. The guide's checkpoint reads `.spec.modelRef`, which doesn't drive the runtime; check the runtime's `MODEL_ALIAS` instead.`
- mem/workshop-progress.md:102 (GAP-type addition). Replacement:
  `  - **it-resolution-agent now depends on `nemotron-nano-9b`** (`dependsOn.models[0]` and `modelRef`, generation 2; runtime `MODEL_ALIAS=nemotron-nano-9b`, runtime version 2 at 05:47:50 UTC). The runtime updated in 24 s. `modelRef` doesn't drive the runtime, but CEL now ties it to `dependsOn.models`: a revert must change or remove it too.`

#### I3. "0 of 478 decisions in 48 h" overstates the window (3 locations)

**Evidence:**
- The PDP pods started 2026-10-04 10:35Z (MANIFEST), so they were about 31 h old. "48 h" is a `--since=48h` artefact.
- snap/ PDP logs: 482 + 555 = **1,037 decisions** (2026-10-04 18:07 → 2026-10-05 17:33 UTC), **0** naming `my-team-policy`, 0 DENY.
- 15 PDP-labelled ConfigMaps (live).

**Replacements:**
- mem/platform-verified-facts.md:139, last sentence. Replacement: `` `my-team-policy` was named in 0 of 1,037 decisions on both PDP replicas over their whole life (2026-10-04 18:07 → 2026-10-05 17:33 UTC; evidence snapshot; notes #33). ``
- mem/platform-observations-notes.md:131. Replace `(0 of 478 in 48 h)` with `(0 of 1,037 decisions on both replicas over the pods' whole life, ~31 h)`.
- repo/notes/playbook/playbook-verification.md:54. Replace `decided 0 of 478 decisions in 48 h (#33)` with `was named in 0 of 1,037 decisions on both PDP replicas over the pods' whole life (#33)`.
- Also inherited by repo/PLANNING-HANDOFF.md:301.

#### I4. The S3 `VersionId` as INTEGRITY evidence (see resolution 2) (2 locations)

- repo/gap-list.md:106. Current: `- Participants can't read the team evidence bucket's versioning, object-lock or lifecycle settings (AccessDenied), so whether the hand-in bucket keeps versions is unknown to us. Our first upload will return a `VersionId` only if it does.` Replacement:
  `- The hand-in bucket can't vouch for the records either. Participants can't read its versioning, object-lock or lifecycle settings (AccessDenied), yet the same credentials can overwrite or delete its objects and can't list or read earlier versions. `submit.sh` prints no `VersionId`. A `head-object` after upload shows one only if versioning is on, and even then it shows only that versioning was on, not that the submission is unaltered.`
- repo/notes/playbook/playbook-verification.md:68 (row 15).
  - Reality cell, after "Our role is denied": insert `(no allow: the participant policy grants only GetObject, PutObject, DeleteObject and ListBucket on team-evidence-*)`.
  - Impact cell: replace `Unverified until the first upload (the put response shows a VersionId only if versioning is on). Keep TEAM_EVIDENCE_BUCKET set` with `A VersionId is not INTEGRITY evidence: participants can overwrite or delete objects and can't list or read versions, Object Lock is unknown, and `submit.sh` (`aws s3 cp --only-show-errors`) prints no VersionId (`head-object` after upload shows one only if versioning is on). Rest INTEGRITY on the MANIFEST hashes plus cross-surface corroboration. Keep TEAM_EVIDENCE_BUCKET set`.

#### I5. "always `bootstrap-key`" (2 locations)

**Evidence:** `/modaas/evidence`, all 1,070 records (2026-10-04 18:07Z → 2026-10-05 17:43Z):
- 1,047 have principal `bootstrap-key`.
- 23 are DENY records for `NoSigV4Credential` with principal `unknown` (unauthenticated probes).
- 1 is a DENY for `PolicyEngineUnavailable` (bootstrap-key).

**Replacements:**
- repo/gap-list.md:32. Replace `and there it is always `bootstrap-key`.` with `and there every authenticated call names `bootstrap-key`.`
- mem/platform-observations-notes.md:118. Replace `(always bootstrap-key)` with `(bootstrap-key on every authenticated call; the 23 unauthenticated `NoSigV4Credential` DENYs show `unknown`)`.

#### I6. The snapshot status is stale: the ledger dump was taken (3 locations)

**Evidence:** snap/MANIFEST.txt:106–119:
- `ledger-records.jsonl`, one GET of `/records` at 17:44:26Z: 101 records, 17 CIDs, coverage 2026-10-04T18:07Z → 2026-10-05T09:13Z.
- 16 of 17 CIDs equal a gateway run id.
- The reviewer re-computed all 8 sha256s (all match) and re-ran a pattern scan (clean).
- The MANIFEST records no scan, so memory's "scan clean" was unsupported until now.

**Replacements:**
- mem/platform-verified-facts.md:174. Replace `both PDP pods (~22.8K lines each), authz (startup lines only) and `pods.txt`. The ledger dump was being added.` with `both PDP pods (22,705 and 22,851 lines), authz (startup lines only), `pods.txt` and the ledger dump `ledger-records.jsonl` (one GET of `/records` at 17:44:26Z: 101 records, 17 CIDs, 2026-10-04 18:07Z → 2026-10-05 09:13Z; 16 of 17 CIDs match a gateway run id). An independent reviewer re-verified all 8 sha256s and re-ran the pattern scan (clean).`
- mem/workshop-progress.md:276. Replacement: `- **Evidence snapshot: taken (2026-10-05; MANIFEST 17:42Z, ledger dump 17:44Z)** in `workshop-local/evidence-snapshots/20261005T173727Z/` (see Live state below).`
- mem/workshop-progress.md:294. Replace `The ledger dump was being added.` with `It also holds the ledger dump (`ledger-records.jsonl`: 101 records, 17 CIDs).`

#### I7. The AICT scope bullet

**Location:** repo/notes/playbook/playbook-verification.md:48.

**Evidence:**
- The connector role may `ListGateways`/`GetGateway`/`List`/`GetGatewayTarget` (repo/notes/servicenow/servicenow-context.md:26, 28: "AICT discovers only AgentCore runtimes and gateways").
- SN handoff L470 (§13.1) claims "AgentCore runtimes, Bedrock agents and SageMaker models". The last two are denied live.

**Replacement:** `- **AICT scope:** discovers AgentCore runtimes, and its role can list AgentCore gateways and targets; not EKS pods, the agentgateway's MCP routes, guardrails or per-ModelConfig attribution. The SN handoff's same sentence (§13.1) also claims Bedrock agents and SageMaker models, which the connector role is denied here.`

#### I8. "not attempted" for direct Bedrock

**Location:** mem/platform-verified-facts.md:156.

**Quote:** "Read from the policies, not attempted."

**Evidence:** mem/workshop-progress.md:34: in Module 5 Claude's direct Bedrock call as WSParticipantRole got "AccessDenied (explicit deny)". The explicit Deny is `console-iam-policy-0` Sid `DenyDirectModelAndAgentInvocation` (re-read).

**Replacement:** `Read from the policies. The participant role's direct InvokeModel was already refused live in Module 5 (AccessDenied, explicit deny in console-iam-policy-0); the IDE role's was not attempted.`

#### I9. A source-based claim isn't labelled

**Location:** mem/platform-observations-notes.md:117.

**Quote:** "cross-CR contradictions are admitted, then parked at phase=Failed."

**Evidence:** screenshots-compare.md:29 says "(the CRD source says so)". workshop-progress L171 says the operator-side check is "untested".

**Replacement:** append `(per the CRD source; not tested live)`.

#### I10. Package notes (credentials, personal data)

**Location:** repo/notes/playbook/playbook-verification.md:90–91.

**Evidence:**
- `prooflab/tests/fake_servicenow.py:18-19` also holds placeholder `CLIENT_ID`/`CLIENT_SECRET` fixture constants.
- The owner's email address is in SN handoff L51, playbook L347 and `prooflab/servicenow/cli.py:28` (`DEFAULT_OWNER`).

**Replacements:**
- L90: `- **Credentials:** none real. The credential-shaped strings are test fixtures: placeholder `CLIENT_ID`/`CLIENT_SECRET` constants for the local fake (`tests/fake_servicenow.py:18-19`) and a deliberate wrong secret in a bad-credentials test (`tests/test_servicenow_adapter.py:109`).`
- L91: `- **Personal data:** the SN handoff (§2), the playbook (L347) and `prooflab/servicenow/cli.py:28` (`DEFAULT_OWNER`) carry Sree's email address; the handoff also names Arth. The repo is PRIVATE.`

#### I11. "(Applied 2026-10-05.)": applied to memory only (see resolution 3)

**Location:** repo/notes/playbook/playbook-verification.md:99.

**Replacement:** replace `(Applied 2026-10-05.)` with `(Applied to memory 2026-10-05. The repo file `notes/servicenow/servicenow-context.md` L61 and L71 still call it a vendor instance / "their instance" and need the same correction.)`

### GAP

#### G1. The repo ServiceNow notes still call `platformdemoh8` a vendor instance (resolution 3)

**Location:** repo/notes/servicenow/servicenow-context.md:61 and :71 (last commit a085c85).

**Replacements:**
- L61: `All three are recorded demos on instance `platformdemoh8` (the console demo's data is dated 2026-09-30). Per the SN handoff (§2, not independently verified), `platformdemoh8` is the hackathon instance shared by all teams, so the demo records may sit beside ours, but none of the demo content is our live state. Captions often contradict the screenshots, so trust the screenshots.`
- L71, replace `Same names as our runtimes, on their instance.` with `Same names as our runtimes. Per the SN handoff (not independently verified), every team's reference agents have identical names on the shared instance, so these records need not be ours.`

#### G2. The ledger keeps a writer-supplied `ts` (relevant to INTEGRITY and RECONSTRUCT)

**Evidence:**
- `workshop-static/reference-impl/audit-store.py` (deployed copy sha256-identical per MANIFEST): `rec.setdefault("ts", …)` and `rec["seq"] = int(time.time() * 1000)`. Only `seq` is server-assigned.
- Today no agent sends `ts`: all 101 records have `ts` within 2 s of `seq`.

**Suggested repo/gap-list.md gap 6 bullet (after L104):** `- Its timestamps are the writer's: the store keeps any `ts` a writer sends and assigns only `seq` itself, so a forged record can also carry a chosen time.`

#### G3. The IDE-role gateway rights are now double-checked

**Evidence:** `iam get-role-policy` on `a-02-code-editor-IdeInstanceRole-1dGzC6naNLIj`, inline `ide-workshop`, Sid `BootstrapAgentCoreGateway`: Allow `bedrock-agentcore:Create/Get/List/Update/DeleteGateway` on `arn:aws:bedrock-agentcore:us-east-1:613052889143:gateway/*`. This is policy-level; nothing was attempted.

**Replacements:**
- mem/platform-verified-facts.md:155: replace `Reported by the glossary verifier, not double-checked.` with `Policy re-read by an independent reviewer (2026-10-05); not attempted.`
- mem/platform-observations-notes.md:127: replace `Reported, not double-checked.` with `Policy re-read 2026-10-05; not attempted.`
- repo/notes/playbook/playbook-verification.md:67: replace `(not double-checked)` with `(policy re-read 2026-10-05; not attempted)`.

#### G4. The owner's email is in committed, pushed files (not in memory or the reviewed files)

**Evidence:**
- Memory, `gap-list.md`, `links.md`, `playbook-verification.md` and `PLANNING-HANDOFF.md`: clean.
- The SN handoff §2 address appears in:
  - `repo/notes/verification/2026-10-05/playbook-verify-lead.md:31`, the source report whose line the new playbook-verification.md:33 deliberately redacted
  - `prooflab/servicenow/cli.py:28`
  - `HACKATHON_WINNING_PLAYBOOK.md:347`
  - `SERVICENOW_INTEGRATION_HANDOFF.md:51`
- All are in bfb1ce6, pushed; the repo is PRIVATE.

**Suggestion:** for consistency, redact `playbook-verify-lead.md:31` the same way playbook-verification.md:33 was (history keeps it). The package files are the team's own.

#### G5. `PLANNING-HANDOFF.md` (untracked, out of scope, written 17:58 UTC) inherits the errors above

It inherits:
- L169: "Run ids exist only on the gateway pod's stdout"
- L329: "Join path: … Durable: CloudWatch gateway `trace_id` → `/modaas/evidence` `correlation_id`"
- L317: "`modaas-telemetry-export` declares run_id/action_id, but they never arrive"
- L321: X-Ray "gateway segments carry `modaas.action_id`" (no run id or tokens)
- L155: §1.8 "UNVERIFIED"
- L247, L249, L253: rows 7, 9 and 13
- L301: "0 of 478"
- L310: "The pod line has no run/trace/action id"

It needs the same fixes before it is committed. It was not reviewed in full.

#### G6. The retention list is incomplete

**Location:** mem/platform-verified-facts.md:138.

**Evidence (live):**
- `aws/spans` 30 d (holds the gateway spans with run ids and tokens)
- `/aws/bedrock/aict-invocations` **7 d** (memory calls it "durable")
- `/aws/application-signals/data` and the CodeBuild group never expire

**Replacement:** append `Also: `aws/spans` 30 d (the gateway's spans, with run id and tokens) and `/aws/bedrock/aict-invocations` 7 d.`

#### G7. The handoff note now exists

**Location:** mem/workshop-progress.md:275.

**Quote:** "Handoff note: being written"

**Evidence:** `repo/PLANNING-HANDOFF.md` exists (untracked, 70 KB, 17:58 UTC).

**Replacement:** `- **Handoff note: drafted (2026-10-05)** at repo root `PLANNING-HANDOFF.md` (untracked; inherits the errors listed in the 2026-10-05 independent review).`

### STYLE

#### S1. gap-list gap 5 repeats itself

**Location:** repo/gap-list.md:87–88. L88 repeats L87.

**Replacement (both lines):** `- An approval is two free-text annotations, stored with an empty `signature` (all 18 approval records in the cluster, re-checked 2026-10-05), and EKS control-plane logging, audit included, is off for all five log types. So who set them isn't recorded independently.`

Verified live: 18 Approved CRs, 1 record each, all signatures empty; `demo-crm-lookup` Reviewing with none; all 5 log types disabled.

#### S2. The gap-list header omits gap 11

**Location:** repo/gap-list.md:5 (pre-existing).

**Fix:** replace `Gaps 2–9 are platform limits` with `Gaps 2–9 and 11 are platform limits`.

#### S3. links.md over-generalises the ServiceNow 404

**Location:** repo/notes/references/links.md:10.

**Quote:** "A page that isn't in Brazil returns a real 404 there. The curated Kill Switch link does." This generalises from one page. Only a rendering client sees the 404; curl gets the 200 shell (L15, L192).

**Replacement:** `  - A page that isn't in Brazil is missing there: the curated Kill Switch link renders a 404 in a browser (WebFetch), although curl still gets the 200 JavaScript shell.`

#### S4. The habits row should also cite the slides

**Location:** repo/notes/playbook/playbook-verification.md:27, source cell.

**Fix:** replace `meeting transcript` with `meeting transcript; slides p15 ("Five habits that keep the design honest")`.

#### S5. 11 vs 12 CRDs

**Location:** mem/platform-verified-facts.md:163 ("all 12 `oda.tmforum.org` CRDs") against L169 ("11 kinds").

**Fix:** replace with `the 12 `*.oda.tmforum.org` CRDs (the 11 in group `oda.tmforum.org` plus `availability.oda.tmforum.org` AvailabilityPolicy)`.

#### S6. FYI: a commit message contains the scan pair

The bfb1ce6 commit message quotes the cockpit parameter name with its equals sign in prose. The scan doesn't read commit messages, so nothing fails. Just don't copy that sentence into a file.

---

## Resolutions of the three disagreements

### (1) Model swap: both fields, or does the operator ignore `modelRef`? Both readers are partly right

**Schema:**
- `kubectl explain agentconfig.spec.modelRef`: "Primary model alias. Lifted from dependsOn.models … Operator injects as MODEL_ALIAS env var."
- `spec.dependsOn`: parallel arrays `models[]`/`tools[]`.

**Live CEL on `spec`:**
- Rule: `(oldSelf.hasValue() && oldSelf.value() == self) || !has(self.modelRef) || (has(self.dependsOn) && has(self.dependsOn.models) && self.modelRef in self.dependsOn.models)`
- Message: "spec.modelRef must appear in spec.dependsOn.models".

**Operator source:**
- `agent_operator.py:611-616` and `961-964` set `MODEL_ALIAS = (deps.get("models") or [None])[0]`.
- The string `modelRef` occurs nowhere in the source zip except the two CRD YAMLs. So the CRD's "Operator injects as MODEL_ALIAS" is inaccurate.

**Live state:**

| Agent | gen | `modelRef` | `dependsOn.models` | Runtime `MODEL_ALIAS` |
|---|---|---|---|---|
| it-resolution-agent | 2 | `nemotron-nano-9b` | `[nemotron-nano-9b]` | `nemotron-nano-9b` (runtime version 2, 05:47:50 UTC) |
| customer-experience / network-resolution / my-agent / hackathon-helper | 1 / 2 / 1 / 1 | **none** | `[nemotron-super-120b]` ×3 / `[nemotron-super-120b-helper]` | equals `dependsOn.models[0]` in each case |

The env key names have no GATEWAY_API_KEY.

**Guide:** `swap-model.en.md` patches both fields (`test` + two `replace`). Its checkpoint prints `.spec.modelRef`, a field that doesn't drive the runtime.

**Conclusion:**
- The runtime model follows only `dependsOn.models[0]`. For agents without `modelRef`, patching that alone is enough.
- Once `modelRef` is set, as on the IT agent now, a change must also replace or remove `modelRef`, or admission rejects it.
- A `modelRef`-only patch never changes the runtime.
- memory workshop-progress Module 7 (L102) is accurate as a record of what was patched; it should add the coupling (I2).

### (2) The S3 version id as INTEGRITY evidence

**One call:** `aws s3api get-bucket-versioning --bucket team-evidence-613052889143` → **AccessDenied**: "no identity-based policy allows the s3:GetBucketVersioning action". That is an implicit deny.

**Participant policies:**
- `participant-permissions-policy-1` v1, Sid `P2TeamEvidenceBucket`, allows only `s3:GetObject`, `PutObject`, `DeleteObject` and `ListBucket` on `team-evidence-*`.
- No `GetBucketVersioning`, `GetBucketObjectLockConfiguration`, `GetLifecycleConfiguration`, `ListBucketVersions`, `GetObjectVersion` or `DeleteObjectVersion`.
- The bucket is empty (KeyCount 0).
- `submit.sh` uploads with `aws s3 cp … --only-show-errors`, which prints no VersionId.

**Can be claimed:**
- After an upload, `aws s3api head-object` (needs only GetObject) returns a VersionId if versioning is on, plus ETag and LastModified. That shows versioning was on at upload, and when the object was stored.
- Combined with the MANIFEST sha256s, it corroborates what was handed in and when.

**Cannot be claimed:**
- That the bucket is versioned (until a VersionId is observed).
- That the object is immutable: participants can overwrite or delete, and Object Lock is unreadable.
- That no other versions exist: participants can't list them.
- That a VersionId vouches for content. It is an opaque id, not a hash.

So it doesn't change gap 6's "corroboration, not proof". Fix gap-list L106 and playbook-verification L68 as in I4.

### (3) Does the repo ServiceNow file still call `platformdemoh8` a vendor/demo instance? Yes

- `repo/notes/servicenow/servicenow-context.md:61`: "All three are recorded demos on a vendor instance (`platformdemoh8`; …). None of it is our live state."
- `:71`: "Same names as our runtimes, on their instance."
- Both conflict with SN handoff L48 ("Instance (shared by all teams) | `platformdemoh8.service-now.com`") and L57 ("every team's reference agents have identical names in AICT").
- Memory (mem/servicenow-context.md:24) was corrected and labelled "per the SN handoff (not independently verified)". The repo file wasn't, though playbook-verification.md:99 says "(Applied 2026-10-05.)".
- Replacements are in G1 and I11.

## Requested checks, summary

| Check | Result |
|---|---|
| Mirror identical | Yes (`diff -r` empty) |
| MEMORY.md index | 12 lines → 12 existing files. L1 and L8 need fixes (I1, E1) |
| No secret values | Pattern scan clean. Exact values 0 files: gateway key, AWS profile values, CockpitUrl/IdeUrl and their tokens. Ledger token not exact-checked (by rule) |
| Owner's email | Absent from memory and the reviewed/new files. Present in 4 committed files (G4) |
| Literal cockpit-parameter pair | Absent from memory and the reviewed files (2 mentions read "`tkn` query parameter") |
| Working-agreement scan line | Wrong (E8); scan-safe replacement given |
| Dating / labels | SN-handoff facts are labelled "per the SN handoff"; §1.8 wrongly "UNVERIFIED" (E3); snapshot items stale (I6) |
| links.md vs report | Faithful re-layout of `notes/verification/2026-10-05/reference-links.md`. 8 external links re-checked OK (cedarpolicy.com/en 404; docs title; 4 GitHub repos' metadata; ADR file list; Kill Switch only `australia/`+`zurich/`). Internal references (`D-docs-and-rails.md` §1.4, AINN §1) exist |
| gap-list additions | Gap 2 OK except "always" (I5). Gap 5 accurate but redundant (S1). Gap 6: the no-verify-route and runtime-env bullets are accurate; the bucket bullet is imprecise (I4). Gap 7 wrong/outdated (E1/E2) |

## Verdict

**Ready to commit after fixes.** Every ERROR has paste-ready text. The one structural change is gap 7's reframe (block given in E1). Apply the E1/E2 cascade to all listed lines together; it changes the plan's durable-join and C16 evidence premise.

`PLANNING-HANDOFF.md` (not in scope) carries the same wrong premise (stdout-only run ids, trace-id durable join) and **needs rework before it is committed** (G5).

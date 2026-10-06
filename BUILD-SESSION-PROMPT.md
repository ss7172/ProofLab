You are the ORCHESTRATOR (Claude Opus, HIGH effort) for team iFabric's build in the Trustworthy AI & Data Hackathon
"Quest for Proof" (MoDaaS on EKS + Bedrock AgentCore; ServiceNow AI Control Tower = AICT). I'm Sree, the captain
(Arth owns ServiceNow). Planning, vetting and architecture are DONE (commit any uncommitted planning files first, scan clean). Your job:
BUILD AND SHIP everything in about 12 hours, in three PHASES, as independently and in parallel as possible. I opt in to WORKFLOWS and
multi-agent orchestration for this session, under the effort policy below.
## Context (read before planning; I'll also paste more, so integrate it)
Repo: /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/TrustworthyAI-iFabric (GitHub satyabrat-invences/TrustworthyAI-iFabric, private, main).
1. IMPLEMENTATION-PLAN.md (§3 tasks + "done looks like", §4 phases + clock + cuts, §5 ops lane run by run, §6 seed feature map, §7 gates). THIS
   prompt wins on METHOD (feature map, merge gate, effort policy) and PHASES (order, targets); the plan wins on facts, tasks, slot times, run
   order, gate contents and limits. NEXT-SESSION-PROMPT.md only points here.
2. architecture/ARCHITECTURE.md, decisions.md, one-page.md; architecture/guardrails/AGENT-GUARDRAILS.md + PLAN.md;
   architecture/work/05–08 (infra feasibility), 12–14 (Arth's handoff: reconciliation, code vetting, deliverables); glue G-01…G-22 (plan §3.9).
3. handoffs/ifabric-handoff-3/: Arth's code, console and plan. Use Arth's code AS-IS; every boundary change to connect it is OUR task.
4. notes/claude-memory/planning-handoff.md: the LAST blocks are my APPROVED decisions (incl. DG-1..DG-7); its older STATE-block times are superseded.
5. PLANNING-HANDOFF.md (verified platform facts) and gap-list.md (scored). Don't re-derive verified facts; re-check read-only only what can drift.
## What we deliver
- THE APP: Arth's console/panel on our query engine. It shows the evidence ledger view, the control test tool (any control + run or window,
  under 2 min), the run catalogue (every run, honestly labelled, in a declared event window), the six auditor questions, and the Assurance
  agent's notes; with the fake/real data switch (fixtures | pack | live; PACK mode refuses synthetic data).
- CONTROLS C16 (per-run token cap), C7 (event recording), C9 (drift: per-run latency Maximum + Errors, TWO-SIDED, + an hourly roll-up):
  threshold experiments → risk-based thresholds (risks.yaml, likelihood × severity; inventory.yaml) → register.yaml frozen and dated (S3
  write-once = the date proof; Arth's ServiceNow approval Finding, after the upload, with my APPROVED note, corroborates) → named PASS/BREACH
  runs on the SAME new ifabric- agents. The pilots pick the C16 breach lever (none works → C7 becomes the first complete control).
- ONE EVIDENCE STORE: the platform ledger, every adapter writing to it (S-1 decides; fallback: one laptop store). EP-0, the pre-run version
  gate, BLOCKS assessed runs. EP-16: the cockpit "ask" route is an observed side door.
- GUARDRAILS at every enforcement point (plain-Python rails; they may block; every decision recorded); Cedar policy changes when they help
  (my OK, recorded). DG-2: mask PII at the receiving agent's INPUT; DG-3: compact ALLOW records; DG-4…DG-7 as approved (plan §2.2).
- AGENTS: a new ifabric- trio (customer / it / network) on nemotron-super-120b, plus Arth's Assurance agent on AgentCore via OUR
  one-file handler (the gateway-URL shim; the token limit raised by config).
- SERVICENOW: notify/check/export, AICT discovery, the Assurance notes, the register approval. The six deliverables in the team evidence
  bucket (readback), the L1→L2→L3 demo, rehearsals.
## PHASES AND TIMELINE (UTC; deadline ~15:00, unconfirmed: confirm it in Hold-1, work to 15:00 until then)
- PHASE 1, the MINIMUM SUBMISSION (target 4 h, by ~05:30; aggressive, so stay minimal: ≤2 pilots per scenario, core rails only, minimal
  judgment changes): the three ifabric- agents built and deployed on AgentCore (single files with evidence emission, the C16 inline hook,
  the core rails, minimal judgment rules: S2 gather-evidence, S3 escalate). Then the controls IN ORDER, each deployed with its thresholds in
  place and working: C16 complete first (pilots → risk-based threshold → register v1 frozen with the S3 write-once date proof → named PASS +
  BREACH runs), then C7 (reusing the same runs), then C9 (baseline from the same healthy runs; finish it in Phase 2 if it doesn't fit).
  A ServiceNow notify on each BREACH (decided: Arth's code as-is + our finding builder, the bug a/b guards). The CLI control test tool +
  the Evidence Pack (token redaction) → FIRST SUBMIT of the six deliverables.
- PHASE 2 (~4 h): ServiceNow integration (the register approval Finding = T2; the incident loop with the guards), the Assurance agent on
  AgentCore (one-file handler, shim, token limit), AICT, THE DASHBOARD (THE APP above), C9 completion if pending, guardrails extended → SECOND SUBMIT.
- PHASE 3 (the rest): the adversarial set, the recorded backup demo, rehearsals → FINAL SUBMIT with ≥1 h buffer. The 12 hours end here.
- Every phase ends with submit.sh + S3 readback (gates G5/G6/G7), so a valid submission always exists. Phase 1's critical path has
  priority; Phase 2/3 code is built offline in parallel ONLY on spare workers. Slot times and slip rule: plan §4.3/§4.6 (Phase 1 submits
  whatever it has by 07:00 at the latest, at least C16's floor end to end; the final submit by 14:45 at the latest).
SCOPE RANKING (by phase):
- MUST: Phase 1 except C9 (C16 + C7 end to end, the BREACH notify, CLI, pack, first submit); core guardrails incl. the guardrail-block demo
  (ADV-H-01 leg A, Phase 1); the L1→L3 path (Phase 2's app, ServiceNow + Assurance, AICT); one rehearsal + the final submit (Phase 3).
- SHOULD: Phase 2's extended guardrails; Phase 3's focused adversarial set (Cedar deny, kill switch, retry loop, injection); a 2nd
  rehearsal; a recorded backup demo.
- CUT ORDER if late (unchanged): C9 first ("built, baseline collected, honestly not complete" in the gap list), then adversarial breadth.
## STEP 1: FEATURE MAP (≤45 min; seed: the plan's §6, PR-00…PR-22, phase-tagged)
Launch the critical chain at once (§6 ★: PR-00 setup, PR-01 contracts, PR-02 c16 core, PR-03 hook, PR-04 emit, PR-05 rails, PR-06 bundler
+ agents), each with its DONE checks from the plan's §3 rows; write FEATURE-MAP.md while they run, one row per PR:
- id and PHASE (1/2/3; split a PR that spans phases); title
- scope: the folders/files it OWNS, so no two PRs own the same files
- DONE LOOKS LIKE: EXECUTABLE acceptance checks only (test names, commands, expected outputs, files that must exist, evidence to attach)
- dependencies; worker model and effort (see the policy); review lens; merge order
PR-01 = shared contracts (record schema incl. rail fields, CID/baggage propagation, register schema with per-control versions,
the Finding contract, the app's data format) + test scaffold. Everything else rebases on it.
Show me a 10-line summary of the map, then keep building. Don't wait for me unless a hold is needed.
## STEP 2: BUILD IN PARALLEL
- One worker subagent per PR, each in its own branch + git worktree (isolation: worktree). Run 10–12 workers at once; use workflows
  for fan-outs; Phase 1 PRs first. Each PR description carries its DONE-LOOKS-LIKE checks and the evidence produced.
- Offline first: build and test against workshop-local/evidence-snapshots/ and exported spans and records (derived fixtures, never raw
  copies). PR workers never call AWS, the cluster or ServiceNow, never read ~/.prooflab-snow.env, and source env.sh only via the scan.
- Git: a worker writes only its PR's owned paths and never pushes main; one owner per shared file (prooflab/__main__.py → PR-01; gap-list.md
  section B → the docs PR; FEATURE-MAP.md, the plan, architecture/* → you). Before any push: git fetch, update from main (rebase before the
  branch's first push, merge main after it) and a clean scan; never force-push (squash merges keep main linear).
- Hard constraints:
  - each agent = ONE ifabric-<role>.py, gzip+base64 ≤ 24,000 chars (the CI gate; hard cap 24,049), with a unique IMAGE_TAG; libraries
    only via EXTRA_PIP; never a file named agent.py, new-agent.sh, a reference image tag or approve=True
  - prooflab/ tool code and the vendored c16 core + rails: stdlib, the tool on Python 3.9; agent code: the pinned Strands stack on 3.12
  - no threshold literals in code; evaluators are stateless; the registry is never in the path; handoffs are record-only
  - c16_core.py is frozen once merged (a change = a new agent build); one invocation per handoff (AWS_MAX_ATTEMPTS=1; a timeout is
    recorded, never re-invoked; the AR-18 duplicate guard)
## EFFORT AND ORCHESTRATION POLICY
- You run on Opus at HIGH effort. Use workflows for fan-outs of PR workers and for parallel merge-gate checks; time-box each (≤45 min), log what it drops.
- You decide each feature's model and effort. DEFAULT = Sonnet, medium effort. Opus, high effort ONLY for: PR-01 contracts,
  c16_core + the single-file bundlers (trio + Assurance), the guardrail rails, and the independent reviewers of those PRs.
  Use xhigh only after one failed attempt at a hard problem.
- Verification: ONE fresh independent reviewer per PR (never the author), checking the executable DONE checks.
  Multi-reviewer panels ONLY for PR-01 and c16_core. No loop-until-dry rounds.
- Prefer speed: if a check is slow or flaky, record it as a known gap with a re-test, rather than blocking the whole lane.
## STEP 3: MERGE GATE (every PR, before it merges)
1. Run the PR's DONE-LOOKS-LIKE checks + the full test suite.
2. Secret scan on the staged tree: bash /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/scripts/pre-push-secret-scan.sh <dir>
   must print "RESULT: clean" (it also checks the ServiceNow secrets; it needs live AWS credentials and /tmp/modaas-token). If it fails only
   on "COULD NOT LOAD" (expired credentials, a reboot): no merge, no push; commit in worktrees, queue merges, ask me; never bypass the scan.
3. An INDEPENDENT reviewer subagent (fresh, never the author) verifies each check with evidence and looks for contract breaks.
4. Fix loop until green.
5. Merge (squash) to main, git fetch first; stop if main moved unexpectedly. Then re-run the tests + scan on main.
6. Update the PR status table in FEATURE-MAP.md and add a line to reviews/gates.jsonl.
You may merge green, in-scope PRs yourself. A failed check never merges.
## OPS LANE (live work: NOT PRs; ONE at a time)
- Every live agent run and every cluster/AWS/ServiceNow write goes through a single serialized ops lane (never in parallel: it contaminates
  C9 and the named runs), each step with its own checklist and "done looks like" (plan §5.2; a line per action in live-lane-log.jsonl).
- Budget guard in every run's preflight: ≤30 model req/min; ≤1.0M tokens in any rolling 60 min; ≤2 observe-mode S2 runs per rolling hour;
  the safety ceiling ≤300K tokens per run, ALWAYS ON (the account ceiling is 100 req/min / 2.5M tokens/h, shared with Arth).
- Spikes first (the 0-token ones while Phase 1 code builds): S-1 ledger POST from the laptop; bucket probe; S-2 build + smoke
  ifabric-customer; S-3 env pin + C16 halt proof (no halt → no S2-class run until fixed); SP-1 Cedar test rule; metric delay.
- EP-0 passes before every assessed run; no assessed run before v1's S3 write-once proof (gate G4); never tune a cap to force a breach.
- Reuse runs: one healthy assessed run counts as a C16 PASS, a C7 PASS and a C9 baseline run, declared in the register (it stays in
  run-ids.txt; pilot and baseline-only ids never). Deploy + smoke customer first (S-2), then IT + network (S-4); one freeze record (G3).
- ServiceNow writes: selftest before each notify batch, a TEST log before the first real one, the bug a/b guards (plan T6.5).
- Batch my approvals into the plan's four holds (Hold-1…Hold-4), each with a recommended default.
## AUTHORITY
PRE-AUTHORIZED:
- read-only checks; code, tests, docs; merging green PRs; gap-list and memory updates
- pilot/baseline/named agent runs within the budget guard; creating NEW ifabric-* agents/tools (they wait for my approval)
- ServiceNow notify/check/export for our own findings (bugs a/b accepted, use the process guards)
- submit.sh after the pack AND its zip pass the scan + token redaction
ASK ME (one batched hold, with a recommended default; keep working while you wait):
- approval annotations and the register's APPROVED notes (my acts, never faked); credentials; contacting organisers
- model changes on existing agents; observe/enforce mode switches; pausing models/tools; Cedar/ToolConfig edits; gateway policies; any delete
- any run likely to exceed 150K tokens or 30 req/min; the cockpit POST (the EP-16 probe)
NEVER:
- team-* Lambdas, IAM, protected namespaces, AgentCore-gateway or Bedrock-guardrail writes; others' objects (incl. the AICT connector)
- the AI Native Networks cleanup scripts; fix-twin.sh where submit.sh packages; editing Arth's code; faking a reviewer; moving a frozen threshold
- printing or committing secrets (ledger token, gateway key, AWS keys, IdeUrl/CockpitUrl and their tokens, presigned URLs, ServiceNow
  id/secret); saving raw get-agent-runtime output; GetFunction; a full ledger GET during a live run; a dry-run notify on the production log
## CREDENTIALS, SECRETS, STATE
- Cluster/AWS commands: bash -c 'source /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; <cmd>'
- The AWS profile [hackathon] EXPIRES 2026-10-06T06:29:19Z: ask me to refresh it in Hold-2 (~04:45; backstop alarm 05:45); until it is
  refreshed, start no live step that can't finish before 06:29 (PR work goes on). ServiceNow: source ~/.prooflab-snow.env in the ops
  lane only (selftest passed 00:45Z). Gateway key: injected into runtimes; laptop copy /tmp/modaas-token (re-extract it after a reboot).
- The Evidence Pack must redact the ledger token from all 3 paths (env vars + the last-applied and kopf last-handled annotations; ARCH §9.3),
  then pass the exact-value scan on the staged tree and the readback.
- Stay LEAN: state lives in files (FEATURE-MAP.md, the plan, notes/claude-memory/); subagents do the heavy reading; keep your turns short.
- Memory: primary ~/.claude/projects/-/memory/; a session started in the repo writes the mirror below (rsync -a --delete the edited copy to
  the other); at each milestone and commit, copy it into notes/claude-memory/ (keep its README). Mirror:
  ~/.claude/projects/-Users-satyabratsrikumar-firstmate-homes-TrustworthyAI-TrustworthyAI-iFabric/memory/
- Commit messages end with: Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
## REPORTING
Report at each milestone and at least every 2 hours: a short outcome update (merged PRs with links, ops-lane results with evidence,
what's next, open holds). Ask me only for holds and genuine decisions.

# Requirements and constraints sheet (architecture input 02)

Written 2026-10-05, about 20:35–21:30 UTC, by a read-only research subagent, as input to the team's architecture work. The captain's architecture direction, relayed by the coordinator during this task, was added as R-P-01 to R-P-04. The captain's correction that followed was applied to R-P-01 to R-P-04, R-P-10, R-P-12, R-P-13, R-P-16 to R-P-18, R-P-20, R-P-21, R-P-23, R-J-18, R-J-20, R-J-26, R-J-42, R-J-48 and the tensions (§6). The correction:
- Agent-to-agent hand-offs are record events: `emit` only, for C7 and RECONSTRUCT. They never block.
- Only one question may make work wait: the optional C16 check before each model call, through `evaluate()`, using a frozen, version-stamped threshold loaded beforehand.
- Post-run C16 is the floor.
- Everything else records, through `emit`, `callback` or `pull`.

The sheet lists what the final architecture must satisfy. Every item has an id, the requirement, its source and a testable acceptance check ("Done looks like"). It makes **no design decisions**: where a source only recommends something, the item says "recommendation (not decided)".

**Status when written:**
- Of the six judged deliverables, only `gap-list.md` exists (handoff §2.4; local check at 18:35 UTC).
- No run has been assessed yet; every run so far is exploratory.

---

## 0. How to read this sheet

**Ids:**
- R-J: judging (what the judges score).
- R-P: product (the captain's requirements).
- R-C: platform constraints (verified on the live platform).
- R-D: delivery.

Ids are stable. Add new items at the end of a group; never renumber.

**Tags:**
- MUST: a stated requirement.
- LOSE: guards against a stated mark-loser.
- BONUS: an Axis 3 bonus.
- RULE: an organiser rule.
- CAPTAIN: the captain's product requirement.
- CONSTRAINT: a verified platform fact the design must respect.
- DELIVERY: how the work gets done.
- OPEN: depends on an unanswered question (for the organisers, the user or the plan).

**Acceptance checks.** Each "Done looks like" is written so that a worker other than the builder can run it (R-D-05). Where a check names a command, the command shows what evidence is needed; the plan may use other tooling that produces the same evidence.

**Citation keys.** Paths are relative to the repo root, `~/firstmate-homes/TrustworthyAI/TrustworthyAI-iFabric/`.

| Key | Source |
|---|---|
| [slides pN] | The Immersion Day masterclass slides (`hackathon-context/sources/Immersion-Day-slides.pdf`), **physical** PDF page N; the printed slide numbers differ. Text extraction: `hackathon-context/work/hackathon-sources/slides-extracted.txt`. Pages used: p5 governance, p6 controls, p7 control modes, p8 GRC chain and roles, p9 evidence, p10 thresholds, p12 enforcement points, p13 timing (evaluator vs tester), p14 five problems, p15 pattern and five habits, p17 the lab, p19–p20 governance tree, p21–p22 worked examples, p23 your task, p25 how you will be judged, p26 Judgement Day |
| [transcript] | `hackathon-context/sources/Hackathon-meeting-transcript.txt` (the quoted phrase is given) |
| [brief Lnn] | `hackathon-context/sources/User-pasted-master-brief.txt`, line nn |
| [handoff §x] | `PLANNING-HANDOFF.md`, the authoritative fact sheet |
| [PB §x] | `HACKATHON_WINNING_PLAYBOOK.md`. Cited directly only for §1.1–§1.6, §1.8 and §4, which were verified trustworthy for judging. Its §2–§3 are used only through [corr] |
| [corr row N] | The corrections table in `notes/playbook/playbook-verification.md` (copied in handoff §4.2) |
| [contract] / [contract-verify §x] | `notes/workshop-reference/platform-contract.md` (the workshop page "What the platform gives you") / its live verification `notes/verification/2026-10-05/platform-contract-verify.md` |
| [gap N] | `gap-list.md`, entry N |
| [SN §x] | `SERVICENOW_INTEGRATION_HANDOFF.md`, which defines the Finding contract. Parts are wrong: its §8.5 "ledger verification", §8.6 "S3 version id", §8.7 six-question mapping and §11.7 (see corr rows 2 and 15, and handoff §4.3) |
| [mem: X] | Memory file `~/.claude/projects/-/memory/X.md` |
| [kickoff deck pN] / [judging slide] | The AWS kickoff deck and the judging slide. Both are outside the repo; they are cited through handoff §1–§2 and [mem: prooflab-project] and were not re-read here |
| [captain brief] | The captain's requirements for R-P and R-D as relayed by the lead session in this task (2026-10-05). **Not yet written in any repo or memory file; confirm the wording with the captain.** Supporting sources are cited next to it where they exist |
| [captain direction] | The captain's architecture direction (2026-10-05), relayed by the coordinator during this task: adapters and one contract; one append-only evidence store; a stitcher; the query backend. It includes the captain's correction: hand-offs are emit-only records; the only waiting question is the optional C16 check before each model call; post-run C16 is the floor; everything else records. Not yet in any repo or memory file |

**Item counts:**

| Group | Items | Ids |
|---|---|---|
| R-J judging | 59 | R-J-01 to R-J-59 |
| R-P product (captain) | 25 | R-P-01 to R-P-25 |
| R-C platform constraints | 18 | R-C-01 to R-C-18 |
| R-D delivery | 10 | R-D-01 to R-D-10 |
| **Total** | **112** | |

The open questions that could change requirements are in §5; the conflicts and tensions are in §6, at the end.

---

## 1. R-J: judging requirements

### 1.1 Gates, pillars and event rules

#### R-J-01 · L1 Foundation is a gate · MUST
- **Requirement:** "Demonstrate the use case in Workshop Studio using the agreed MODaaS guardrails and NVIDIA-supplied model. A submission without this foundation will not be judged." The levels are sequential: each needs the one before.
- **Source:** [judging slide via handoff §2.1]; [PB §1.1, §4.1].
- **Done looks like:** a recorded demo and the pack's files show, for one named fault-resolution run:
  - (a) Every model call crossed `modaas-agw` to a Nemotron alias: every model-call span of the run in `aws/spans` (listener `llm`) names a Nemotron model.
  - (b) A guardrail is declared on every ModelConfig used (`safety.required: true`), and one guardrail block is on record (HTTP 200, `content_filter`, 0 tokens).
  - (c) Every agent, model and tool in the run is Approved, with the approval records exported.

  A reviewer ticks (a) to (c) from the pack alone, before any L2 or L3 material is shown.

#### R-J-02 · L2 Observability · MUST (after L1)
- **Requirement:** "AI Native ODA (ModaaS) controls are enabled and evidence collected in Audit ledger. Service[Now] Control Tower adds additional observability." The kickoff call adds: "the service now control tower and human loop that is absolutely needed".
- **Source:** [judging slide via handoff §2.1]; [transcript]; [PB §4.1]. OPEN: whether AICT is required for L2 is an organiser question [handoff §9].
- **Done looks like:**
  - (a) The ledger's `/records?cid=` export for every named run is in the pack; the ledger's volume is deleted with the stack.
  - (b) Exported CR status shows the MoDaaS controls on (guardrails, Cedar policies, approvals) for every asset in those runs.
  - (c) A dated AICT export or screenshot shows our agents under our team-named connection.
  - (d) AICT's known limits are in the gap list: Monitor is likely empty, and the usage count is 0 for our traffic (corr row 11).

#### R-J-03 · L3 Extended chain of evidence · MUST (after L2)
- **Requirement:** "(AWS Workshop Studio + ServiceNow Sandbox) richer evidence, a stronger chain of evidence and additional proof, including other models where appropriate." The brief adds: "Distinguish actual AWS evidence, actual ServiceNow evidence, missing cross-platform links, and simulations."
- **Source:** [judging slide via handoff §2.1]; [PB §4.1]; [brief L321]. The ServiceNow-native agent that would read our incidents is planned in [SN §9] (UNVERIFIED by us).
- **Done looks like:**
  - One id can be followed through the pack: AWS records → assessment → ServiceNow incident (owner, delivery readback, response or recorded silence) → any ServiceNow-side analysis. A stranger follows it without help.
  - Every record produced by a non-Nemotron model (for example ServiceNow's LLM) names that model.
  - Each cross-platform link is labelled as actual, missing or simulated.

#### R-J-04 · Three pillars; "the most auditable solution wins" · MUST
- **Requirement:** the three pillars:
  - "Close the gap: Give the reference agents the judgment to gather evidence or escalate".
  - "Build a Control: At least one end to end; two named runs + a dated threshold doc".
  - "Handover Proof: An Evidence Pack that answers the six auditor questions".

  The headline: "The winner provides the strongest evidence that every decision is explainable, every risk is controlled, and every claim can be independently verified in practice, the most auditable solution wins." Also: "If its decisions can't be traced, the entry scores nothing."
- **Source:** [kickoff deck p2, p5, p20, p23 via handoff §1–§2.2 and mem: prooflab-project].
- **Done looks like:** the pack's README has a three-row table, one row per pillar, pointing to the files that prove it, and no row is empty. R-P-19 covers "close the gap", R-J-07 "build a control", and R-J-28 to R-J-34 "handover proof".

#### R-J-05 · Models and hosting · RULE
- **Requirement:**
  - Nemotron in the agents is required for a valid solution.
  - AWS-hosted custom agents use Strands on AgentCore Runtime; ServiceNow-hosted agents are allowed.
  - "Submitted agents must operate within the provided AWS/ServiceNow environments. Existing code and MCP servers may be brought in if they satisfy the workshop deployment constraints."
- **Source:** [brief L91, L93, L95]; [transcript: "These agents can only run on AWS agent core runtime", "you cannot bring your agents outside of those instances"]; [PB §1.8]; [slides p23: "ALLOWED: Building more or changing the agents. You can use NVIDIA Nemotron model for this"].
- **Done looks like:**
  - An inventory in the pack lists every agent with its host (AgentCore runtime id or ServiceNow agent) and its model.
  - Every AWS-side model call in the pack names a Nemotron id.
  - No agent runs anywhere else.

#### R-J-06 · Shared-environment etiquette · RULE
- **Requirement:**
  - Name the AICT connector and our agents with the team name.
  - "Prefix connectors, agents, workflows, and our records with the team name where supported. Clone rather than modify shared examples, and preserve other teams' assets."
  - "Avoid broad reconfiguration of shared risk frameworks unless essential and authorized."
  - "Creating additional agents or elaborate ServiceNow workflows does not itself earn bonus points."
- **Source:** [transcript: "please name it or rename it with the name of your team", "please create it with your team name", "It's not going to give you bonus points for creating agentic workflow"]; [brief L99, L313, L325]; [PB §1.8].
- **Done looks like:**
  - Every agent, ToolConfig, connector and ServiceNow record we created carries `ifabric`: `ifabric-…` CRs, `ifabric_…` runtimes (R-C-13).
  - A review of our cluster and ServiceNow writes finds no edit to a shared example, another team's asset or a risk framework.

### 1.2 Axis 1: complete controls

#### R-J-07 · Axis 1 orders the field · MUST
- **Requirement:** "How many of the three controls did you complete, end to end?" None complete = "Nothing to score"; 1 = "The minimum. You are in the running"; 2 = "Ahead of a team with one"; 3 = "The full set". The masterclass adds: "Don't do things partially. Start with one control, finish until you see the evidence. You have your query tool that is working, then move on to the next."
- **Source:** [slides p25]; [transcript]; [PB §1.1, §4.2].
- **Done looks like:**
  - The pack lists each of C7, C9 and C16 as complete or not complete.
  - A control is listed as complete only if R-J-08 passes for it in full.
  - A partly built control is listed as not complete, with its gap entry.

#### R-J-08 · What "complete" means for one control · MUST
- **Requirement:** the six required steps, in order:
  1. Choose the control.
  2. "Declare your threshold ranges: Metric, observation limit, exception tolerance, measurement basis and a named owner. Versioned and dated before any assessed run — we check the date."
  3. Decide where in the timeline: "Post-run forensics is the floor … Doing it continuously, inline as it runs, is bonus."
  4. "Build the control: At an enforcement point of your choosing, emitting records bound to the control, the threshold version and the run, not just a timestamp."
  5. "Build the control test and / or evaluators: … recompute the measure, reconcile expected against observed, count exceptions, compare with your rule."
  6. "Run it both ways, and record the gaps: One passing case, one breaching case. Do not move the threshold to make it pass. Write down what you could not close."

  The playbook adds that the breach alerts the named owner and that the query tool answers in under 2 minutes. The lab slide's "YOU BUILD" list says the same.
- **Source:** [slides p17, p23]; [PB §1.2, §4.2 (a)–(g)].
- **Done looks like:** a checker who did not build the control ticks, from the pack:
  - The register entry has every field (R-J-39) and is dated before the earliest assessed run (R-J-21).
  - Binding records exist at an EP for every governed action of the named runs (R-J-15, R-J-22).
  - The control test recomputes the verdict from raw captures.
  - The control test returns satisfied for the PASS run and not satisfied for the BREACH run, both under the same threshold version.
  - The breach has a delivered owner alert (R-P-21).
  - The two-minute query passes (R-J-10).
  - The gap list holds the control's open items.

#### R-J-09 · A subset is partial coverage of the claim · MUST
- **Requirement:** the claim C-FM-01 is "During fault resolution, the three collaborating agents meet our declared event-recording, drift and token-spend requirements." The slides: "A control is the safeguard. A control test checks it. Results flow back up to the claim, and a completed subset is partial coverage, not a pass." The brief: "Partial control coverage does not establish the full claim."
- **Source:** [slides p19, p20]; [brief L48, L71].
- **Done looks like:**
  - The tool and the app print a claim line for C-FM-01 that lists each control's result.
  - With fewer than three controls complete and satisfied, the line reads "partial coverage", never "claim satisfied".
  - A test feeds 1, 2 and 3 complete controls and checks the wording.

### 1.3 Axis 2: quality ("where the prize is actually decided")

#### R-J-10 · The live test: two minutes, judge-driven, run or window · MUST
- **Requirement:**
  - [slides p25]: "We name one control and one window and watch you produce the answer. Two minutes. If we have to trawl your logs, you lose the mark."
  - [slides p26]: "Your control test tool: The thing we will drive. A command line, a script, an API, a small app. We type the question; you do not narrate the answer." Also: "We name one control and one run. You drive your own tool."
  - The finish line [slides p23]: "You are done when somebody who is not on your team can ask 'was control 9 satisfied for run FM-B?' and get an answer in two minutes, with the records behind it."
  - The playbook's shorthand "We ask; you operate" [PB §1.3, §4.3] paraphrases these; it is not slide text.
  - "Unsupported controls and unknown runs must never look successful." [brief L288]
- **Source:** as quoted; [transcript: "We name a control. You show us with your tool that it executed. You show us the evidence, the composition of the evidence"]; [brief L268–L288]. The tool is specified in R-P-04.
- **Done looks like:** a timed test by a non-builder, offline from the pack:
  - (a) For each complete control, the tester types one run query and (b) one UTC-window query.
  - Within 120 s of the question, the screen shows the rule, threshold version, version date, owner, measured value against the limit, exceptions with their denominators, completeness, the verdict and resolvable record ids.
  - (c) An unknown run id and an unsupported control each return an explicit non-success: a non-zero exit code and the words "not assessed" or "insufficient evidence".
  - The test is done twice (R-J-45).

#### R-J-11 · "Would it survive a second enforcement point?" · MUST
- **Requirement:** this architecture question, verbatim. The five-problems slide adds: "If the second one forces a rewrite, you built an integration." The captain's direction answers it with adapters around one contract (R-P-01).
- **Source:** [slides p25, p14]; [transcript: "is that architecture just working for the gateway, right, a model gateway, or if I move it to a human queue, is that still going to work"].
- **Done looks like:**
  - The same evaluator and record contract are wired at two EPs.
  - The diff between the two wirings touches adapter code only, and the architecture note lists those adapter files.
  - A reviewer can point to the single shared evaluator and schema files.

#### R-J-12 · "Is the register out of the live path?" · MUST
- **Requirement:** this architecture question, verbatim. Habit: "The control register is never in the path of execution" ("that will delay the system", in the transcript). The five-problems slide: "OFF THE PATH, ALWAYS ASYNC: telemetry · ledger · register". The brief: "Load and pin specifications outside individual model/tool request paths. Define historical version lookup so old evidence is never tested accidentally against today's threshold."
- **Source:** [slides p25, p15, p14]; [transcript]; [brief L231–L233]; [captain direction] (R-P-01).
- **Done looks like:**
  - Code review finds no register read inside any request-handling code: the version is pinned at process start, or passed in.
  - A test makes the register unreadable after start, and in-path behaviour does not change.
  - Re-testing an old run after a newer register version exists uses the version bound to that run's evidence.

#### R-J-13 · "Is the evaluator stateless?" · MUST
- **Requirement:** this architecture question, verbatim. Habit: "The evaluator never remembers." The pattern slide: the evaluator "compares a value against its threshold range and returns a verdict at the decision point. Stateless." The brief: "Keep the evaluator stateless. Put mutable budget/reservation state in an explicit concurrency-safe component coordinated by the enforcement point."
- **Source:** [slides p25, p15]; [brief L179, L214]; [captain direction] (R-P-01).
- **Done looks like:**
  - The evaluator is a pure function: observations and the pinned specification go in; a verdict and reasons come out.
  - A unit test calls it with identical inputs repeatedly, out of order and in parallel, and gets identical outputs.
  - A lint or search finds no module-level mutable state, I/O or clock reads in it.
  - Any budget or reservation state is a separate, named component.

#### R-J-14 · "Does the control hold its own threshold?" · MUST / LOSE
- **Requirement:** this architecture question, verbatim. LOSE: "a control that stores its own threshold". The brief: "Do not hard-code business thresholds inside control implementations."
- **Source:** [slides p25]; [brief L185]; [PB §4.5]; [captain direction] (R-P-01).
- **Done looks like:**
  - A search of the control, evaluator and agent code finds no threshold value outside the register; test fixtures are excepted.
  - A test changes a value in a new register version, and the verdict changes with no code change.
  - Every assessment and finding carries a `threshold_version` that exists in the register.

#### R-J-15 · Evidence: bound, checkable by a stranger, gaps recorded · MUST
- **Requirement:**
  - "Bound to a control, a threshold version and a run. Verifiable by somebody who is not you. Gaps recorded rather than left blank." [slides p25]
  - What turns a record into evidence: "what happened · which control · which threshold version · which run · who acted · a seal" [slides p9]; the seal is out of scope.
  - "The test: hand a stranger one record and its seal, and nothing else. If they can check it without your help, you have evidence." [slides p9]
  - "A readable audit trail that links intent, control decisions and results. Activity logs alone do not qualify." [kickoff deck p17 via mem: prooflab-project; PB §1.4]
- **Source:** as quoted; [brief L251–L266] (a minimal versioned schema); the field list is in R-P-02.
- **Done looks like:**
  - (a) A schema check over every evidence record in the pack finds a control id, threshold version, run id or window, actor, emitted-at time and source reference on each.
  - (b) A stranger test: a worker with no build context, given only the pack and its README, recomputes one verdict per complete control from the raw captures with the documented queries, and gets the same value.
  - (c) Every scope has a completeness statement: expected, captured, missing.

#### R-J-16 · Honesty: bring one honest failure · MUST
- **Requirement:** "'Built properly: yes. Actually worked: no' is the most useful answer a team can bring. One honest failure scores better than everything green." The Judgement Day slide: "Bring one honest failure. A team that says 'built properly, did not work, here is the evidence and here is why' scores above a team with nothing but green ticks."
- **Source:** [slides p25, p26]; [brief L383: "Preserve an honest failure as part of the demonstration"].
- **Done looks like:**
  - The pack holds at least one documented failure (a control, test or defence that did not work), with its evidence and reason.
  - Every requirement in this sheet that is not met appears in the gap list.
  - No output shows a pass where evidence is missing (R-J-58).

### 1.4 Axis 3: bonuses ("separates teams that are level")

General rule for all four: "Include bonus evidence only for implemented and verified capabilities." [brief L379]

#### R-J-17 · Extra controls · BONUS
- **Requirement:** "a second or third completed to the same standard"; "More than one control implemented end to end in your architecture".
- **Source:** [slides p25, p26].
- **Done looks like:** each extra control passes R-J-08 in full; otherwise it is not claimed.

#### R-J-18 · Continuous compliance: inline and live · BONUS
- **Requirement:**
  - "a verdict formed inline, in the path, while it runs" [slides p25].
  - "An inline decision, live: show a verdict being formed in the path, not replayed afterwards" [slides p26].
  - In-transaction is "the only one that prevents" [slides p14].
  - "Do not count replayed decisions as the live inline bonus." [brief L354]
  - The transcript: "If you do it in real time, that is extra bonus points than doing it offline with a query tool".
- **Source:** as quoted. In the captain's design, the only candidate is the optional C16 check before each model call (R-P-18).
- **Done looks like:**
  - In a live run, an EP calls `evaluate()` before an action and the action waits for it.
  - The verdict is recorded with a timestamp before the action (or its refusal), and it is shown live to the judge.
  - A near-real-time post-run loop is labelled "near-real-time post-run evaluation" [SN §7.6] and is not claimed as this bonus.

#### R-J-19 · Adversarial testing · BONUS
- **Requirement:** "you attacked your own design and showed us what broke"; "Your adversarial test log: what you attacked, what broke, and what you changed". Nemotron may be used to perform it.
- **Source:** [slides p25, p26, p23].
- **Done looks like:** R-P-25 passes, with at least one case that broke, the change made, and a passing re-test.

#### R-J-20 · Second enforcement point · BONUS
- **Requirement:** "the same architecture, moved, with nothing rewritten"; "The second or more enforcement points: running, with a note of what you had to change".
- **Source:** [slides p25, p26, p14]; [corr row 12]; [captain direction].
- **Done looks like:**
  - EP2 is running and can be shown live.
  - EP2 is a passage of a type listed on slides p12 or p14, reached by the same contract through a different adapter or transport.
  - The note names the adapter that changed.
  - In the captain's design, nothing of ours waits at EP2 (only the C16 check waits). So the pack says what EP2's own refusal is, for example the managed gateway's, read through `pull`. Or it says plainly that EP2 records a late verdict through `callback` and refuses nothing (the ServiceNow queue).
  - The pack does not claim a notify-only incident as an EP that refuses (corr row 12; R-J-52; tension T5).

### 1.5 What loses marks

The full list: "WHAT LOSES MARKS: A threshold with no date, or dated after the test · records covering only some of the governed actions · evidence only your own team can verify · a finding closed without a passing re-test · a control that stores its own threshold · a design that only works in the request path" [slides p25]. Also: "If an artefact is missing we cannot score it, however good the work behind it was." [slides p26]

#### R-J-21 · A threshold with no date, or dated after the test · LOSE
- **Requirement:**
  - "we check the date" [slides p23].
  - "Do not move the threshold to make it pass." [slides p23]
  - "Pilot work may inform a justified threshold, but assessed results must not be used to rewrite their own acceptance criteria." [brief L199]
  - "A changed threshold requires a new version and new assessed runs. Preserve the original results." [brief L201]
- **Source:** as quoted; [PB §4.5].
- **Done looks like:**
  - Each register version has a date, plus at least one timestamp we do not control: the object time of a register upload to the team bucket, a pushed commit, or the owner's ServiceNow approval note [SN §14; PB §4.5].
  - That timestamp is earlier than the start of every assessed run under the version; the start times come from `aws/spans`.
  - Any threshold change after it shows as a new version with new assessed runs, and the old results are kept.

#### R-J-22 · Records covering only some of the governed actions · LOSE
- **Requirement:** records must cover every governed action, not a sample.
- **Source:** [slides p25]; [captain direction] (R-P-02: every decision recorded).
- **Done looks like:**
  - For each named run and each window, a completeness statement lists every model call, every tool call (undeclared tools included; gap 3), every refusal (guardrail block, pause 404, 403), every agent hand-off and every escalation.
  - Its counts reconcile with the run's spans in `aws/spans` and its `/modaas/evidence` records.
  - The expected population comes from a source outside the graded agent (R-P-16).

#### R-J-23 · Evidence only your own team can verify · LOSE
- **Requirement:** a stranger must be able to verify the evidence without us.
- **Source:** [slides p25, p9].
- **Done looks like:**
  - R-J-15 (b) passes.
  - The README names every query with its capture time.
  - No step of the check needs our credentials, our laptop or our presence.

#### R-J-24 · A finding closed without a passing re-test · LOSE
- **Requirement:** "Re-test: the loop closes here and nowhere else" [slides p8]. "Close a finding only after a passing retest. Record any risk acceptance separately, with named approval and expiry, without relabeling a failed test as passed." [brief L335–L337]
- **Source:** as quoted; [SN §8.4].
- **Done looks like:**
  - Every finding marked closed links a later SATISFIED re-test assessment on the same control and scope type.
  - Owner replies are logged as responses, not closures.
  - Any accepted risk has a named approver and an expiry date.

#### R-J-25 · A control that stores its own threshold · LOSE
- **Requirement:** as in R-J-14.
- **Source:** [slides p25].
- **Done looks like:** the R-J-14 check passes.

#### R-J-26 · A design that only works in the request path · LOSE
- **Requirement:**
  - The design must also work off the request path.
  - "Keep telemetry, ledger writes, and register access asynchronous/off the critical request path" [brief L235].
  - "Explain durable delivery, buffering, retries, and reconciliation so asynchronous processing does not hide lost records." [brief L237]
  - "The architecture should accommodate static, scheduled, event-driven, in-transaction, and continuous checks without forcing every control into a request hook." [brief L247]
- **Source:** [slides p25, p14]; [brief]. Met in the captain's design by R-P-01 (everything except one optional question records), R-P-18 (post-run C16 is the floor) and R-P-21 (ServiceNow off the path).
- **Done looks like:**
  - Every control has an off-path test (pull or emit) that reaches the same verdict from captured records when no inline hook ran. Test: disable the inline hook and re-run the control test on the same run.
  - Telemetry, ledger writes, ServiceNow calls and C9 run off the request path (code review).
  - A reconciliation compares emitted against stored record counts.

#### R-J-27 · A missing artefact cannot be scored · LOSE
- **Requirement:** all six deliverables must be in the hand-in.
- **Source:** [slides p26].
- **Done looks like:** the unzip check of R-J-44 ticks all six deliverables from the uploaded file.

### 1.6 The six auditor questions

"Judges pick an incident from your event window and ask six questions which are answerable from your Evidence Pack alone." [kickoff deck p7 via handoff §2.5] So the pack must cover the whole event window, including the Hostile and Rogue phases [mem: prooflab-project]. The platform's known limits per question are gaps 2–7 and 11; the answers must state those limits, not hide them.

#### R-J-28 · A declared event window · MUST
- **Requirement:** the pack declares the event window it answers for.
- **Source:** [kickoff deck p7 via handoff §2.5]; [mem: prooflab-project].
- **Done looks like:**
  - The README gives the window's UTC start and end, and the Alert 0, 1 and 2 phase boundaries in it.
  - An index lists every run id (CID) in the window, with its phase and a label for test or adversarial traffic.
  - When a tester picks any CID or time in the window at random, the tool and the app resolve it.

#### R-J-29 · WHO: "acted — which identity, on whose behalf, with what scope?" · MUST
- **Requirement:** answerable from the pack alone.
- **Source:** [kickoff deck p7 via handoff §2.5]; limits in [gap 2] and R-C-03.
- **Done looks like:** for three incidents picked at random by a tester (one from a Hostile or Rogue phase), the pack names, each with record ids:
  - the acting agent (runtime name and version);
  - the platform principal (`bootstrap-key`, shared by all agents; gap 2);
  - on whose behalf (customer, ticket, CID);
  - the declared scope against the scope actually used (declared tools against tools called).

#### R-J-30 · WHAT: "did it touch: models, tools, resources?" · MUST
- **Requirement:** answerable from the pack alone.
- **Source:** [kickoff deck p7 via handoff §2.5]; [gap 3].
- **Done looks like:**
  - For each incident, the pack lists every model (id and alias), every tool (undeclared ones flagged by `route_alias`) and every resource touched, from the gateway spans and `/modaas/evidence`.
  - The counts equal the run's spans in `aws/spans`.

#### R-J-31 · AUTHORIZED: "which policy, which version, evaluated where?" · MUST
- **Requirement:** answerable from the pack alone.
- **Source:** [kickoff deck p7 via handoff §2.5]; [gap 4]; [corr row 17].
- **Done looks like:**
  - For each call, the pack gives the policy id and version (`policy_version` in `/modaas/evidence`), the decision and where it was evaluated (the PDP, through the gateway's external authorization).
  - It also gives the real outcome (served, guardrail-blocked, paused 404, 403), because the platform records refusals as ALLOW (gap 4).
  - The PDP decision lines from both replicas are in the pack.

#### R-J-32 · APPROVED: "attestation for every asset in the chain?" · MUST
- **Requirement:** answerable from the pack alone.
- **Source:** [kickoff deck p7 via handoff §2.5]; [corr row 16]; [gap 5].
- **Done looks like:**
  - For every asset actually used in the incident (agents, models, and tools including undeclared ones), its approval record (subject, role, attestation, time, generation) is in the pack.
  - Approvals older than the running version are flagged.
  - The empty `signature` field is stated.

#### R-J-33 · INTEGRITY: "can you show the records were not altered?" · MUST
- **Requirement:** answerable from the pack alone, without overclaiming.
- **Source:** [kickoff deck p7 via handoff §2.5]; [brief L117]; [gap 6]; [corr rows 2, 15]. OPEN: what INTEGRITY proof the organisers expect [handoff §9].
- **Done looks like:**
  - A MANIFEST of SHA-256 hashes over every pack file is made before upload and re-verified after an S3 readback.
  - A corroboration report for each named run compares the ledger with the surfaces written outside the agent (gateway spans, PDP, `/modaas/evidence`, X-Ray, `/aws/bedrock/aict-invocations`) and lists every mismatch.
  - The pack says plainly that this is corroboration, not proof.
  - It claims no ledger self-verification (corr row 2) and no S3 version id as proof (corr row 15).

#### R-J-34 · RECONSTRUCT: "can you replay the run end to end with timestamps?" · MUST
- **Requirement:** answerable from the pack alone. The captain's stitcher (R-P-03) is the mechanism.
- **Source:** [kickoff deck p7 via handoff §2.5]; [handoff §5.3]; [gap 7].
- **Done looks like:** for each named run, and on demand for any CID in the window, an ordered timeline is built from exported files only:
  - `aws/spans` by run id → action ids → `/modaas/evidence` and the PDP lines;
  - the ledger by `correlation_id`;
  - refusals joined by trace id (handoff §5.3 join path);
  - loops visible as call counts (S2 made 174 model calls).

### 1.7 The three alert levels

From the kickoff deck's "How you Win" and its "1.5 Days" schedule: Alert 0 Baseline (3 h) → build block (3 h) → Alert 1 Hostile (4 h) → Alert 2 Rogue (3 h) → Reconstruction & Judging (4 h: "Generate your Evidence Pack; 15 minutes live with the judges") [kickoff deck p6, p8 via handoff §2.5]. OPEN: who injects the Hostile and Rogue conditions, and when [handoff §9].

#### R-J-35 · Alert 0, Vanilla or Baseline · MUST
- **Requirement:** "the flow runs, safeguards are active, and evidence is correlated end to end."
- **Source:** [kickoff deck p6, p8 via handoff §2.5].
- **Done looks like:**
  - At least one baseline run exists per scenario we claim.
  - Each is joined end to end by its CID across `aws/spans`, `/modaas/evidence` and the ledger.
  - Guardrails, Cedar decisions and approvals are shown active for it.

#### R-J-36 · Alert 1, Hostile · MUST
- **Requirement:** under delays, tampered prompts and skills, and conflicting context, prove "Detection, safe degradation, and unsafe actions denied".
- **Source:** [kickoff deck p6, p8 via handoff §2.5].
- **Done looks like:** for each hostile case run, the adversarial log (R-P-25) shows:
  - the detection record;
  - the degraded behaviour (for example gather-evidence or escalate instead of acting);
  - a denial with its true outcome.

  Where no denial is possible on this platform, a gap entry says so.

#### R-J-37 · Alert 2, Rogue · MUST
- **Requirement:** under bypass attempts, unauthorized tool use and tampered records, prove "Containment, evidence preservation, and reconstruction".
- **Source:** [kickoff deck p6, p8 via handoff §2.5].
- **Done looks like:** for each rogue case run:
  - containment is shown, for example a Cedar DENY from a ToolConfig policy (R-P-12) or a pause with its requested and effective times (R-C-12);
  - evidence is preserved: exported before and after, with tampering done only on copies;
  - the incident is reconstructed as in R-J-34.

### 1.8 The six deliverables and hand-in

"BRING THESE, WHATEVER YOU BUILT", each marked MUST [slides p26]; the brief: "Bring the six mandatory artifacts from PDF page 26" [brief L370–L377]. OPEN: the user has still to provide the Evidence Pack format [handoff §9].

#### R-J-38 · Deliverable 1: the evidence file · MUST
- **Requirement:** "In whatever form you chose. Exported, openable by us, and covering the runs you want scored." The brief: "Make exports usable by someone outside the team."
- **Source:** [slides p26]; [brief L290, L372].
- **Done looks like:**
  - It uses plain formats (JSON, JSONL, CSV, Markdown, static HTML) that open without our app.
  - It covers every run in `run-ids.txt` and the declared window.
  - It includes the ledger export.

#### R-J-39 · Deliverable 2: the threshold document · MUST
- **Requirement:**
  - "One entry per control you took on: metric, limit, exception tolerance, measurement basis, owner, version and date." [slides p26]
  - The four questions for every threshold: "Why this metric? … Why this value? … 'It is what we achieved' is not an answer. … Measured on what? … When does it stop holding?" [slides p10]
  - "Each rule carries two different numbers: the limit on a single observation, and the share of observations allowed to break it. Declare both." [slides p22]
  - The kit's field names: metric, observation_limit, exception_tolerance, measurement_basis, owner, version, version_date, enforcement_point [mem: challenge-requirements].
- **Source:** as quoted; R-P-14 has the full field list.
- **Done looks like:**
  - `register.yaml` in the hand-in WORKDIR has one entry per control taken on, with every field filled.
  - The owner is a named person ("Not a team, not a committee" [slides p6]).
  - Both numbers are declared, and the four questions are answered in writing.
  - The date check of R-J-21 passes.

#### R-J-40 · Deliverable 3: the control test tool · MUST
- **Requirement:** "The thing we will drive. A command line, a script, an API, a small app. We type the question; you do not narrate the answer."
- **Source:** [slides p26]; [brief L373: "A working control-test/query tool with usage instructions"].
- **Done looks like:** R-J-10 and R-P-04 pass, and the pack holds usage instructions.

#### R-J-41 · Deliverable 4: two named runs · MUST
- **Requirement:** "One that passes and one that breaches, with their run identifiers written down before we arrive."
- **Source:** [slides p26]; [PB §4.7] (add the time window).
- **Done looks like:**
  - `run-ids.txt` in WORKDIR lists, for each complete control, one PASS and one BREACH run id with their UTC time windows.
  - It is timestamped (pushed or uploaded) before judging.
  - Both runs are assessed under the same threshold version, and the tool reproduces both verdicts.

#### R-J-42 · Deliverable 5: the one-page architecture sketch · MUST
- **Requirement:** "Components, what sits in the path of execution, and how an enforcement point invokes you. A whiteboard photograph is fine." The brief: "A one-page architecture showing the live path and invocation interfaces."
- **Source:** [slides p26]; [brief L376]; [SN §13] (show the ServiceNow EP and AICT); [PB §4.3]; [captain direction].
- **Done looks like:**
  - `sketch.png` or `sketch.jpg` is in WORKDIR; those are the only names `submit.sh` packages. It fits on one page.
  - It shows every component and its host, ours or the platform's: the EP adapters, the contract, the registry, the evidence store, the stitcher and the query backend (R-P-01 to R-P-04).
  - It shows what sits in the path of execution and what is off it. In the captain's design, only the optional C16 check before each model call waits; everything else records (R-P-01).
  - For each EP, it shows the transport by which the EP invokes us (R-J-47).
  - It shows the register out of the path, the stateless evaluator, and the ledger and telemetry off the path (R-J-51).
  - It maps the five control modes (R-J-54).
  - It shows EP1 and EP2, ServiceNow and AICT, and draws the dashboard as a view, not an EP (R-J-53).
  - A reviewer can answer the four architecture questions (R-J-11 to R-J-14) from the sketch alone. An `architecture.md` may accompany it.

#### R-J-43 · Deliverable 6: the gap list · MUST
- **Requirement:** "What you could not close, and why. This is scored, and it scores well." The kit format is What's missing / Why / Impact / If you had one more day, plus the affected claim or control.
- **Source:** [slides p26]; [handoff §6]; [corr row 3].
- **Done looks like:**
  - `gap-list.md` is in WORKDIR.
  - Every entry has the four kit fields and the affected control or claim.
  - Every INDETERMINATE scope and every unmet item of this sheet appears.
  - There is no false gap; for example not "no durable OTEL trace exporter" (corr row 3).

#### R-J-44 · Hand-in through `submit.sh` · MUST
- **Requirement:**
  - Run `bash submit.sh <team-name> [--dir WORKDIR] [--evidence-dir DIR]`; a bare call exits 2.
  - It zips `~/evidence/` as it is, plus `register.yaml`, `gap-list.md`, `run-ids.txt` and `sketch.png`/`.jpg` from WORKDIR, with a `MANIFEST.txt`.
  - It uploads to `s3://$TEAM_EVIDENCE_BUCKET/submissions/<team>/` and prints a presigned URL, which must never be committed or pasted.
  - The zip also stays in the directory the script ran from.
  - `TEAM_EVIDENCE_BUCKET` must stay set.
  - The judges read the bucket, not laptops.
- **Source:** [handoff §2.4]; [PB §1.3]; [mem: challenge-requirements].
- **Done looks like:**
  - After the submit, a checker downloads the zip from the bucket, unzips it and ticks all six deliverables.
  - The checker re-hashes every file against the MANIFEST.
  - The exact-value secret scan of the unzipped tree reports 0 hits (R-C-10).
  - The local zip is not committed.

#### R-J-45 · Judgement-day readiness · MUST
- **Requirement:**
  - "Assemble these on Saturday evening, not Sunday morning" [slides p26]. For this event that means the evening before judging ("Assemble everything the evening before" [PB §1.3]).
  - "Rehearse it twice before you present." [slides p26]
  - 15 minutes live with the judges [kickoff deck p8 via handoff §2.5].
  - "Bring a working or recorded demo of the foundation" [PB §1.3].
  - A preliminary round for every team; finalists present again; the winner is announced on Wednesday [transcript].
  - Prepare for both the judge-as-auditor format and the pitch [handoff §4.3].
- **Source:** as quoted.
- **Done looks like:**
  - Two rehearsal records exist, each with date, tester, the control and run or window asked, seconds to answer, and a six-question walk-through on a judge-picked incident.
  - A recorded L1→L3 demo file exists.
  - A 15-minute run-of-show was timed in rehearsal.

### 1.9 The masterclass architecture rules

#### R-J-46 · Problem 1: five modes, one definition and one evidence format · MUST
- **Requirement:** "Controls run in five modes. One definition and one evidence format, whether the check runs inline in 5 ms or overnight in a batch." The C16 worked example adds: "Same record, same binding, different execution mode".
- **Source:** [slides p14, p21].
- **Done looks like:** one control-definition schema and one evidence-record schema serve all controls; records from each implemented control validate against the same schema.

#### R-J-47 · Problem 2: one contract, four transports · MUST
- **Requirement:**
  - "How does an enforcement point invoke you? Define the interface once, so a new enforcement point can be added without a rewrite." [slides p14]
  - "ONE CONTRACT, FOUR TRANSPORTS. Every enforcement point reaches your architecture the same way. This is the part worth getting right." [slides p15]
  - `evaluate()`: "synchronous, in the path — for in-transaction controls that must be able to refuse".
  - `emit()`: "asynchronous, on an event bus — for everything that only has to be recorded".
  - `callback()`: "a webhook for a verdict that arrives later — deferred actions, human approval".
  - `pull()`: "on a schedule — for scheduled and continuous controls, off the live path".
  - The five-problems slide also shows "sidecar / SDK: interceptor in the process".
  - "Implement only the transports needed for the chosen scope. Show how the others fit without claiming they are built." [brief L245]
- **Source:** as quoted; [captain direction] (R-P-01).
- **Done looks like:**
  - One interface definition carries the four transports.
  - Each built transport has a test.
  - Unbuilt transports appear on the sketch marked "not built".

#### R-J-48 · Problem 3: only the EP makes work wait, and only for one question; race conditions · MUST
- **Requirement:**
  - "What is allowed in the path of execution, to avoid race conditions? Only the enforcement point may make the work wait, and only for one question." [slides p14]
  - "Race: two calls both read 9,800 under a 10,000 cap and both pass. Reserve, then commit." [slides p14]
  - For inline C16, address "Concurrent calls. Retries. Output-token bounds. Partial and failed calls. Reservation, settlement, and release."
  - "A check that only asks whether current usage is below the cap can still allow the next call to overshoot."
  - "If the platform cannot strictly prevent overspend, report the guarantee we can actually prove." [brief L170–L181]
- **Source:** as quoted. The captain's direction meets this rule: the only waiting question is the optional C16 check before each model call (R-P-01, R-P-18).
- **Done looks like:**
  - A code review finds exactly one place where our code makes work wait: the C16 `evaluate()` call before a model call, if it is built. Every other adapter records.
  - If the C16 check is built: a concurrency test fires parallel calls near the cap, and the committed total never exceeds the declared guarantee. Reservations carry an output-token bound and are released on failure. The guarantee actually proven is written down.
  - If no inline check is built, the sketch says "post-run detection only" for C16.

#### R-J-49 · Problem 4: a span is not evidence until it is bound · MUST
- **Requirement:** "How a record becomes evidence: A span is not evidence. It has to be bound to a control, a version and a run." The slide's binding shape is "control id + threshold version / run id + actor + verdict".
- **Source:** [slides p14]; [captain direction] (R-P-02).
- **Done looks like:** nothing is presented as evidence without a binding record (control id, version, run id, actor, verdict) that references the raw span or line. The R-J-15 schema check confirms it.

#### R-J-50 · Problem 5: cover every kind of enforcement point · MUST
- **Requirement:** "Does it cover every kind of enforcement point? Some cannot be modified, some answer late, some have no request path." The slide's examples:
  - "Managed gateway: no code of yours in it, read its log".
  - "Human approval queue: the verdict arrives hours later".
  - "Scheduled batch job: no request to sit inside".
  - "Third-party SaaS action: no hook, poll and reconcile".
  - "Kill switch: out of band, and last to survive".
  - "One design has to reach all of them."
- **Source:** [slides p14].
- **Done looks like:** the sketch shows, for each of these five EP kinds, which transport reaches our contract, and marks which are built.

#### R-J-51 · The five habits · MUST
- **Requirement:** "FIVE HABITS THAT KEEP THE DESIGN HONEST: The telemetry store never judges · The evaluator never remembers · The control register is never in the path of execution · The evidence ledger never interprets · Records are sealed where they are made [out of scope]".
- **Source:** [slides p15]; [transcript]; [captain direction] (R-P-01 to R-P-04 are tied to these habits).
- **Done looks like:**
  - (a) Telemetry collectors and stores, and the stitcher, contain no verdict logic: a code search finds verdicts computed only in evaluator and tester modules.
  - (b) R-J-13 passes.
  - (c) R-J-12 passes.
  - (d) The evidence store keeps raw captures byte-identical (hash before and after) and keeps binding records exactly as emitted, with no logic that depends on content beyond schema validation (R-P-02).
  - (e) Sealing is not built, and the sketch states it as out of scope.

#### R-J-52 · What an enforcement point is · MUST
- **Requirement:**
  - "A control acts only where something passes through … It is about position, not purpose. A component is not an enforcement point, a passage is" [slides p12].
  - The list of EP types: model gateway, zone or API gateway, guardrails, tool call, retrieval and data access, sub-agent handoff, human approval queue, planner, agent memory write, deferred action, platform automation, kill switch.
  - "EVERY ENFORCEMENT POINT DOES THE SAME FIVE THINGS: 1 Ask if this is allowed · 2 Wait for the answer · 3 Act on it · 4 Record what happened · 5 Seal the record".
- **Source:** [slides p12].
- **Done looks like:**
  - The architecture's EP table names each EP we claim and its type from the list.
  - For each, it shows how the EP asks, waits, acts and records (sealing is out of scope).
  - Anything that cannot wait or refuse is labelled an observer, not an EP.

#### R-J-53 · "A dashboard is not an enforcement point" · MUST
- **Requirement:** "A dashboard: Sees everything. Can refuse nothing." against "A gateway every request must cross: Can look, can record, or can say no." [slides p12]. The transcript: "a dashboard is an enforcement point no it's not it can take a look at things it can observe but it cannot decide anything".
- **Source:** as quoted.
- **Done looks like:** the captain's app (R-P-05) and its backend (R-P-04) appear on the sketch as a view and query tool outside the path. The pack and the pitch never count them as an EP.

#### R-J-54 · Five control modes · MUST
- **Requirement:** "Five ways a control gets checked":

  | Mode | Slide wording | Example control |
  |---|---|---|
  | Static | "Somebody reads a document, occasionally" | AIA-GOV-001 |
  | Scheduled | "A job runs on a fixed cadence" | AIA-INV-001 |
  | Event driven | "Something happens and the check fires" | C7 AIA-LOG-001: "Every meaningful action emits a record, joined on one run id" |
  | In transaction | "Checked mid-action, before it completes" | C16 ACN-COST-001: "The gateway asks before the call, and can halt the run" |
  | Continuous | "A number watched against a limit, always" | C9 AIA-ARC-006: "Live measure against a frozen baseline, alert to a named owner" |

  The brief: "The architecture should accommodate static, scheduled, event-driven, in-transaction, and continuous checks without forcing every control into a request hook."
- **Source:** [slides p7]; [brief L247].
- **Done looks like:**
  - The sketch maps all five modes to a transport; static and scheduled may be drawn only.
  - Each implemented control runs in its stated mode, or a written note justifies the deviation. For example, C16 may be post-run only because the gateway has no per-run budget or halt (corr row 10).

#### R-J-55 · Compliance timing; evaluator vs tester · MUST
- **Requirement:**
  - Three moments [slides p13]:
    - Before it runs: "May this go live at all?"
    - While it runs: "Is this allowed, right now?"; "Output: allow, deny or alert, per action".
    - After it ran: "Did the control hold between T1 and T2?"; "Output: a dated pass or fail on the control".
  - The two roles [slides p13]:
    - "EVALUATOR judges the subject … Output a verdict the system acts on: allow, deny, alert. Consumer the enforcement point, in milliseconds".
    - "TESTER / THE CONTROL TEST judges the control … Output a dated pass or fail, with measured values and exceptions. Consumer the register, the auditor, the judge".
  - The brief: "Keep these outputs separately typed" (L229); "Keep aggregate test results distinct from individual evidence events" (L264).
- **Source:** as quoted.
- **Done looks like:**
  - The code has two distinct output types, the evaluator decision and the control-test assessment, with separate schemas.
  - Every assessment is dated and carries its measured values and exceptions.

#### R-J-56 · The pattern's governance components · MUST
- **Requirement:** [slides p15]:
  - "Control register: controls, thresholds, owners, versions. Hands out the current version. Never in the path."
  - "Evaluator: compares a value against its threshold range and returns a verdict at the decision point. Stateless."
  - "Evidence ledger: binds a record to control, version and run, then seals and chains it. [Seal is out of scope]"
  - "Control test / query: answers 'was control X satisfied between T1 and T2?' on demand."
  - "Draw your own version on a whiteboard in the first hour and show it to a mentor."

  The brief lists the same roles, plus the telemetry store and the enforcement point [brief L205–L228].
- **Source:** as quoted; [captain direction] (R-P-01 to R-P-04 name the components).
- **Done looks like:**
  - Each component is identifiable on the sketch and in the code, with one responsibility.
  - If a mentor reviewed the sketch, who and when is recorded.

#### R-J-57 · The GRC chain, filled brackets and the finding loop · MUST
- **Requirement:**
  - The chain: "CLAIM → OBJECTIVE → RISK → CONTROL → CONTROL TEST → EVIDENCE" [slides p8].
  - The team supplies every bracket [slides p20]:
    - C7: "coverage [C%]. Gap < [G ms]; breaches ≤ [B7%]".
    - C9: "Drift ≤ [D%] against the baseline. Violating windows ≤ [B9%]".
    - C16: "total spend ≤ [N tokens]".
  - The named risks [slides p20]:
    - C7: "Missing events, broken run links, or excessive unexplained gaps".
    - C9: "Drift goes unnoticed, or the measurements themselves are missing".
    - C16: "A loop overspends, or calls are missed or charged to the wrong run".
  - When a test fails [slides p8]: "Finding raised, and it names whether the deficiency is in design, in operation, or both" → "Risk exposed" → "Remediation: fix it, compensate for it, or accept it with a named approver and a hard expiry" → "Re-test: the loop closes here and nowhere else".
  - The finding fields are in [brief L329–L333].
- **Source:** as quoted.
- **Done looks like:**
  - For each control taken on, the pack shows the chain from C-FM-01 to its evidence files, with every bracket filled in the register.
  - Every finding records the deficiency type, the owner and the next action, and it closes only as in R-J-24.

#### R-J-58 · Verdict semantics and one vocabulary · MUST
- **Requirement:**
  - Overshoots stay visible: "the 800-token overshoot stays visible" [slides p21]; "The 8 ms exception stays visible in the record" [slides p22].
  - "Detection working does not erase the breach." "A missing measurement is not zero drift." "A gap test checks timing, not completeness." [slides p22]
  - "Keep four things distinct": whether the control was designed correctly; whether it operated correctly; whether the governed activity satisfied its declared requirement; whether sufficient evidence exists [brief L65–L69].
  - "Use explicit satisfied, not-satisfied, and insufficient-evidence/not-assessed outcomes" (L284). "If missing coverage itself breaches the declared rule, show that failure as well" (L286). "Do not trust a stored green verdict when the underlying measurements cannot reproduce it" (L266).
  - Four vocabularies are in play:

    | Source | Verdicts |
    |---|---|
    | Slides | SATISFIED / NOT SATISFIED |
    | Brief | satisfied / not-satisfied / insufficient-evidence |
    | Finding contract [SN §6] | SATISFIED / BREACHED / INDETERMINATE / ESCALATED |
    | Kit `evaluate.py` [mem: challenge-requirements] | PASS / BREACH / NO EVIDENCE (exit 0/1/2) |
- **Source:** as quoted.
- **Done looks like:**
  - One mapping table is shared by the CLI, the app, the assessments and the findings.
  - A test asserts that one scope gets the same verdict in all four.
  - The overshoot or exception value is always printed.
  - Missing data gives insufficient-evidence or INDETERMINATE, never satisfied.
  - The tool recomputes from records rather than reading a stored verdict.

#### R-J-59 · Out of scope: do not build · RULE
- **Requirement:**
  - "OUT OF SCOPE — Not asked for, and not scored: Signing, hashing and Merkle trees over the ledger; A human actually answering an alert. The response is not required; the alert, its named recipient and the silence must still be recorded" [slides p23].
  - "Do not spend time on these: Signatures, hash chains or Merkle proofs over the ledger; A slide deck. A whiteboard and a working tool beat both" [slides p26].
  - "Do not describe the resulting evidence as cryptographically tamper-proof." [brief L117]
- **Source:** as quoted.
- **Done looks like:**
  - No signing or hash-chain work is on the critical path; a MANIFEST checksum list is allowed and is not a chain [SN §8.5].
  - No slide deck is among the deliverables.
  - Each alert's named recipient and its response-or-silence state are recorded (R-P-21).

---

## 2. R-P: product requirements (the captain)

Every R-P item comes from [captain brief] or [captain direction]; supporting sources are cited next to them.

### 2.1 Architecture direction (the captain, 2026-10-05)

#### R-P-01 · Adapters around every EP, one contract with four transports, a versioned control registry, one waiting question · CAPTAIN
- **Requirement:**
  - Every enforcement point is wrapped by an adapter.
  - Every adapter calls one contract with four transports: `evaluate`, `emit`, `callback`, `pull`.
  - Controls are tied to a versioned control registry.
  - The evaluator is stateless, and the registry is never in the path.
  - **Only one question may make work wait:** the optional C16 check before each model call, through `evaluate()`. It uses a frozen, version-stamped threshold loaded beforehand, so the registry is never called in the path (R-P-18).
  - **Everything else records:**
    - `emit`, for asynchronous events: agent decisions; agent-to-agent hand-offs, which never block; our own C16 verdict records.
    - `callback`, for verdicts that arrive later: ServiceNow responses, human approvals.
    - `pull`, for scheduled and continuous collection: the platform's decision logs, `aws/spans`, the AgentCore metrics for C9.
- **Source:** [captain direction]. Supporting: [slides p14, p15] (one contract, four transports; "Only the enforcement point may make the work wait, and only for one question"; "Managed gateway: no code of yours in it, read its log"); [brief L235–L247]. Where adapters can be placed is set by R-C-01: most platform EPs take no team code, so their adapter can only read their log (`pull`).
- **Ties:**
  - Habits: "The evaluator never remembers"; "The control register is never in the path of execution".
  - Axis 2: "Would it survive a second enforcement point?" (a new EP means a new adapter only); "Is the register out of the live path?"; "Is the evaluator stateless?"; "Does the control hold its own threshold?" (thresholds live only in the registry).
- **Satisfies:**
  - R-J-48: "Only the enforcement point may make the work wait, and only for one question".
  - R-J-26, the LOSE item "a design that only works in the request path": everything except the one optional question runs off the path, and post-run C16 is the floor.
  - R-J-47 (one contract, four transports).
- **Done looks like:**
  - (a) An adapter table lists every EP in the architecture, with its adapter, its transport and whether the adapter is built. Exactly one adapter uses `evaluate()`: the C16 check before a model call, if it is built. Every other adapter uses `emit`, `callback` or `pull`.
  - (b) Every adapter imports the same contract module; a code search finds no adapter-specific evaluator or schema.
  - (c) Adding a second EP for an existing control changes adapter files only (the diff is listed; R-J-11).
  - (d) R-J-12, R-J-13 and R-J-14 pass.
  - (e) The registry holds a version id and date per control and serves pinned versions. The C16 check's threshold is loaded and version-stamped before the run, and every C16 record carries that version. A test makes the registry unreachable after loading, and the in-path check is unchanged.
  - (f) A code search finds no blocking call to the registry, the evidence store, the stitcher or ServiceNow on any request path. A test makes the evidence store unavailable during a run: the agents carry on, the loss is recorded, and later reconciliation finds it ("so asynchronous processing does not hide lost records" [brief L237]).

#### R-P-02 · Every decision recorded into one append-only evidence store, with full metadata · CAPTAIN
- **Requirement:**
  - Every decision is recorded into one append-only evidence store.
  - That covers platform decisions (Cedar, guardrails, pauses, admission), agent decisions, agent-to-agent hand-offs, human approvals and ServiceNow responses.
  - Each record carries the fields in table A.
  - Recording is never in the path. Records arrive through `emit`, `callback` or `pull` (R-P-01).
  - Agent-to-agent hand-offs are record events: our agents `emit` them for C7 and RECONSTRUCT, and they never block.
- **Source:** [captain direction]. Supporting: [slides p9, p14, p15] ("OFF THE PATH, ALWAYS ASYNC: telemetry · ledger · register"); [brief L235–L237, L251–L266]; [SN §8.2] (reference prefixes).
- **Ties:**
  - Habits: "The evidence ledger never interprets" (the store appends and binds; it computes nothing); "The telemetry store never judges"; sealing is out of scope (a MANIFEST only).
  - Axis 2 Evidence: "Bound to a control, a threshold version and a run. Verifiable by somebody who is not you. Gaps recorded rather than left blank."
  - LOSE: "records covering only some of the governed actions".
- **Satisfies:** R-J-26, the LOSE item "a design that only works in the request path". Recording is asynchronous and off the path.

**Table A: required record fields, and where each can come from today.** A field that does not apply is never left out: it holds an explicit null with a reason (for example "not applicable: model call, no hand-off" or "unknown: gap 2").

| Field | Content | Source on this platform today | Known limit |
|---|---|---|---|
| control id | C7, C9, C16 or ESC, plus the library id (AIA-LOG-001, …) | The registry | None |
| threshold version and value | The registry version and value in force for the run | The pinned registry version | None for decisions bound to a control; platform-only decisions carry an explicit null |
| measured value | The number the verdict compares | Evaluator or tester input | None |
| verdict | In the shared vocabulary of R-J-58 | The evaluator or tester; for platform decisions the platform's own decision plus the true outcome | The platform records guardrail blocks and pauses as ALLOW; the true outcome comes from the gateway line (R-C-05, R-C-12) |
| reason | Why: rule matched, cap exceeded, policy id | Evaluator reasons; the PDP `matched` field; the gateway status | Guardrail and pause records carry no reason |
| actor (agent + runtime id) | For example the IT agent on runtime `it_resolution_agent-…` version 2 | Our agents' own records and the runtime log groups. A gateway call joins to its agent only if our agent records the call's action id (R-P-20) | Gateway model lines carry no agent identity (R-C-03) |
| on whose behalf | Customer, ticket, CID | The agent's input and the run id | Not in any platform record |
| platform principal | `ServiceIdentity::"bootstrap-key"` | The `principal` field in `/modaas/evidence` | Shared by every agent (gap 2) |
| EP id | Which enforcement point decided | The adapter's configuration | None |
| EP-responsible party | Who operates that EP: the platform (organisers), our team, the control owner | The adapter's configuration and the architecture's EP table | None |
| control owner | A named person | The registry | None |
| run id (CID) | The baggage CID | Gateway `modaas.run_id`, `/modaas/evidence` `correlation_id`, the ledger | Refusals (the 404 and 405 lines) carry none; they join by trace id |
| action id | One per call | The response header, gateway line, span, PDP line, `/modaas/evidence` | The reference agents don't record it (gap 7); agent spans don't carry it |
| trace id | The W3C trace | Gateway, PDP, AgentCore spans | The reference agents' ledger trace ids are agent-minted and don't match the run trace |
| hand-off from → to | Agent-to-agent hand-offs | Emitted by our agents as record events (`emit` only; never blocking). Corroboration: the run's single X-Ray trace spans all three runtimes; `/aws/bedrock/aict-invocations` (7 days): one AWS-written `InvokeAgentRuntime` record per invocation, carrying the CID, session id and traceparent the caller sent (corrected 2026-10-05 after live re-check) | No platform hand-off record has been verified. The AWS record shows each invocation of a runtime, with its CID, but not what was handed over (corrected 2026-10-05 after live re-check) |
| timestamps and clock | Occurred-at, recorded-at, and which clock | Each source | The clocks differ (gateway pod, PDP pod, AgentCore, ServiceNow, laptop). The ledger keeps writer-supplied timestamps. C7 gap arithmetic depends on the clock (brief L134) |
| raw source refs | `raw:<path>#L…`, `gateway:action_id=…` and similar | The exporter | Every reference must resolve inside the pack |

**Table B: the decision types to cover.**

| Decision | Decided by | Platform record today | Join key | Durable? |
|---|---|---|---|---|
| Cedar authorization | The PDP, through the gateway's external authorization | PDP `decide` lines (both replicas; pod logs only) and `/modaas/evidence` | action id, trace id; CID | `/modaas/evidence` 30 days; the PDP lines must be exported |
| Authentication refusal (403) | `modaas-authz` | `/modaas/evidence` DENY (`NoSigV4Credential`); a gateway 403 line with no ids | trace id | 30 days |
| Guardrail outcome | The Bedrock guardrail | Only the gateway line or span (`content_filter`, 0 tokens); the decision says ALLOW | action id | Spans 30 days |
| Pause (kill switch) | The operator withdraws the route | A gateway 404 line with no ids; the CR's `spec.paused` field and its conditions | trace id | `/aws/modaas/gateway` 7 days; requested and effective times only from our live-lane log |
| Admission | The admission policy and CEL rules on the API server | Nothing observable afterwards: EKS audit logging is off; only the requester sees the response; `components` events last about 1 hour | none | No. Our own writes' results must go in the live-lane log; other people's are a gap |
| Rate ceiling (429) | Gateway rate limits | A gateway line (untested) | n/a | Untested |
| Agent decision (disposition: gather, escalate, refuse, act) | Our agent code | Ledger records; the reference agents' dispositions are keyword guesses (gap 1) | CID | The ledger volume; must be exported |
| Agent-to-agent hand-off | Agent code | No platform record type verified. Our agents `emit` a hand-off record (never blocking) | CID, trace id | Our store |
| Human approval of an asset | The approval annotation on the CR | The CR's `.status.governance.approvals` (empty `signature`) | CR name and generation | Cluster lifetime; must be exported |
| Human approval of the thresholds | The control owner | A ServiceNow note or incident [SN §14] | Register version | ServiceNow |
| ServiceNow response | The owner, in ServiceNow (arrives by `callback`) | Incident activity and our delivery log [SN §8] | `finding_id` | ServiceNow and the delivery log |
| Our C16 check's verdict (if built) | Our agent code, before each model call: the only waiting question | Our own record, sent by `emit` after the decision | CID, action id | Our store |

- **Done looks like:**
  - (a) A schema check finds every field of table A on every record, as a value or as an explicit null with a reason.
  - (b) For each named run, a reconciliation report gives, per decision type in table B, the number of source events against the number of stored decision records. They are equal, or each difference is listed as a gap.
  - (c) The store's write path only appends: a test tries to update and to delete a record and both are refused. A correction is a new record that points to the old one.
  - (d) Raw captures are byte-identical before and after storage (hash compare), and every raw source reference resolves.
  - (e) The store is exported into the pack before the account ends (R-C-17).

#### R-P-03 · A stitcher joins decisions across EPs and hand-offs by CID, action id and trace id · CAPTAIN
- **Requirement:** a stitcher joins the stored decisions across enforcement points and agent hand-offs, using the CID, the action id and the trace id. It runs after the fact, off the path (`pull` over the store), and never blocks a run.
- **Source:** [captain direction]. Supporting: the join path in [handoff §5.3]; [gap 7]; [mem: platform-verified-facts].
- **Ties:**
  - Habits: "The telemetry store never judges" and "The evidence ledger never interprets". Stitching is a join; it neither changes records nor forms verdicts.
  - Axis 2 Evidence: "Verifiable by somebody who is not you". The joins can be reproduced from raw files with documented keys.
  - Problem 4: "A span is not evidence."
  - The RECONSTRUCT question (R-J-34).
- **Known join breaks it must handle (R-C-06):**
  - Refused calls carry no run or action id; they join by trace id, through the PDP decision and its `/modaas/evidence` record.
  - `/aws/modaas/gateway` holds only the trace id.
  - The reference agents' ledger trace ids are agent-minted.
  - Agent spans carry no action id.
  - The ledger `seq` can collide.
  - X-Ray truncates long runs.
  - The clocks differ between sources.
- **Done looks like:**
  - (a) For each named run, the stitched graph holds every span in `aws/spans` with that run id, every `/modaas/evidence` record with that `correlation_id`, every PDP line with those action ids, every ledger record with that CID, and every refusal joined by trace id.
  - (b) An "unjoined records" list is produced; it is empty or each entry is explained.
  - (c) Each link records the key and path it used.
  - (d) Re-running the stitcher on the same inputs gives byte-identical output.
  - (e) A non-builder hand-checks 5 random links against the raw files.
  - (f) The agent hand-offs (customer → IT → network) appear in order with their timestamps.

#### R-P-04 · The control test / query tool is the dashboard's backend and answers from the store · CAPTAIN
- **Requirement:**
  - The control test and query tool answers from the evidence store.
  - Every answer carries all the metadata: who was responsible (EP-responsible party, control owner), who acted (agent and runtime id, platform principal, on whose behalf), what was decided (verdict and reason), and under which rule and version (control id, threshold version and value).
  - It is the dashboard's backend.
- **Source:** [captain direction]. Supporting: [slides p13, p15, p25, p26]; [brief L268–L292]; [SN §8.7] (output shape; its six-question mapping needs the handoff §4.3 corrections).
- **Ties:**
  - Axis 2 live test (R-J-10): "Two minutes. If we have to trawl your logs, you lose the mark."
  - Habit "The evaluator never remembers": the verdict is recomputed at query time by the stateless evaluator.
  - Habit "The control register is never in the path": it reads the registry version bound to the evidence, offline.
  - It is a tester ("judges the control"), not an evaluator and not an EP (R-J-53, R-J-55).
- **Done looks like:**
  - (a) For a named run and for a UTC window, the output shows every metadata field listed above, plus the measured value and record references; a missing field shows as "unknown" with its gap id.
  - (b) The verdict is recomputed from the stored measured values at query time. If it differs from a stored verdict, the tool flags the mismatch [brief L266].
  - (c) R-J-10's timing test passes.
  - (d) If the app offers natural-language questions, a test shows the verdict and arithmetic come from the deterministic test, never from a model: "An LLM must not invent the verdict or supply arithmetic from memory." [brief L292]

### 2.2 The app with a dashboard

#### R-P-05 · One app, three views · CAPTAIN
- **Requirement:** an app with a dashboard that holds (a) an evidence ledger view, (b) the control test tool and (c) the six auditor questions.
- **Source:** [captain brief]. Supporting: "a small app" is an accepted form of the control test tool [slides p26]; "Provide a deterministic CLI, API, or small app supporting both run and time-window queries." [brief L268]
- **Done looks like:**
  - A checker opens the app from the pack with the one documented command and reaches all three views.
  - The sketch shows the app as a view and query tool, not an EP (R-J-53).

#### R-P-06 · Offline from the Evidence Pack · CAPTAIN
- **Requirement:** the app reads only the exported pack. It makes no live AWS, cluster or ServiceNow call.
- **Source:** [captain brief]. Supporting: [PB §4.3: "One command, offline from the Evidence Pack"]; [SN §8.7: "To produce the 'Human loop' line offline (no ServiceNow call during judging), read the delivery log"]; [SN §13].
- **Done looks like:**
  - With networking off, no AWS credentials and no ServiceNow environment variables, every view and every query still answers.
  - The human-loop and AICT lines come from `delivery-log.jsonl`, the exported incidents and the AICT exports, each shown with its capture time.
  - A file-access trace shows reads only under the pack directory.

#### R-P-07 · No public endpoint · CAPTAIN
- **Requirement:** the app is never reachable from outside the machine that runs it.
- **Source:** [captain brief]. Supporting:
  - The cockpit has no authentication of its own, and the gateway's public load balancer receives internet scanner traffic [mem: platform-verified-facts].
  - A MAVERIC restart opens ports on 0.0.0.0 [handoff §3d].
  - "Do not contact organizers, publish, incur material costs, or change shared/production systems without applicable authorization." [brief L409]
- **Done looks like:**
  - While the app runs, the list of open sockets shows no listener except on 127.0.0.1; a static file has none at all.
  - Nothing is deployed to the public load balancer, CloudFront, S3 website hosting or any other internet-facing service.
  - The app bundle holds no credential, presigned URL, IdeUrl or CockpitUrl; the secret scan is clean.

#### R-P-08 · Evidence ledger view · CAPTAIN
- **Requirement:** browse every record for a run (CID) or a UTC window across all surfaces, each record shown with its binding (control, threshold version, run, actor) and its source reference.
- **Source:** [captain brief]; [slides p15: "Evidence ledger: binds a record to control, version and run"]; R-P-02.
- **Done looks like:**
  - For each named run, the view lists exactly the records the control test counted; the counts are equal.
  - Each record's reference opens the raw capture line.
  - Refusals show their true outcome (served, blocked, paused, refused), not only the platform's ALLOW (gap 4).

#### R-P-09 · Control test and six-question views use the CLI's engine · CAPTAIN
- **Requirement:** the app's control test view and the CLI share one engine (R-P-04). The six-question view answers WHO, WHAT, AUTHORIZED, APPROVED, INTEGRITY and RECONSTRUCT for any incident in the window, with its known limits.
- **Source:** [captain brief]; R-J-10; R-J-28 to R-J-34.
- **Done looks like:**
  - For the same control and scope, the app and the CLI print identical verdicts, values and record ids (a diff test).
  - For three random incidents (one from a Hostile or Rogue phase), a non-team tester gets all six answers with record ids, and the stated limits (gaps 2–7, 11).

### 2.3 Security and guardrails at every enforcement point

#### R-P-10 · An EP security table with no blank row · CAPTAIN
- **Requirement:** security and guardrails at every enforcement point, the platform's and ours.
- **Source:** [captain brief]; the platform's EPs and the unlisted ones in [handoff §5.9] and [contract-verify §2].
- **Done looks like:** the architecture holds a table with one row per EP:
  - the gateway with the PDP and Cedar;
  - `modaas-authz` external authorization (fail-closed);
  - the Bedrock guardrails;
  - admission (CEL rules and the admission policy);
  - the ledger's token gate;
  - the rate ceilings;
  - the kill switch;
  - the runtime IAM deny;
  - the AWS AgentCore Gateway (`AWS_IAM`);
  - the AgentCore Runtime (our agent code);
  - the collector;
  - each EP we add (an inline check, EP2, the human queue).

  Each row gives:
  - the guard;
  - who controls it (the platform or us);
  - the transport by which our architecture reaches it. Exactly one row is `evaluate()`: the optional C16 check. The others are `emit`, `callback` or `pull` (R-P-01);
  - the evidence record;
  - the test case id;
  - a status: built and tested, platform-verified, or gap.

  Every row has a test result or a gap-list entry.

#### R-P-11 · A guardrail outcome on every model call · CAPTAIN
- **Requirement:** every model our agents use is guardrailed, and our evidence records each call's guardrail outcome.
- **Source:** [captain brief]; [handoff §5.2]; [gap 4]; [mem: reference-agents-facts] (the self-check fails on the guardrail verdict); [mem: prooflab-project] (Module 7: "guardrail verdict on every model call" is part of "the shape judges score").
- **Done looks like:**
  - Each ModelConfig used has `safety.required: true` with a `bedrockGuardrail` enforcer.
  - For a run with an injected prompt attack, the evidence shows that call as BLOCKED (from the gateway line: `content_filter`, 0 tokens), next to the platform's ALLOW.
  - `score-run.py`'s guardrail-verdict check passes on our agents' runs.

#### R-P-12 · Cedar changes through our ToolConfigs · CAPTAIN
- **Requirement:** use Cedar where it can refuse: the called tool's ToolConfig `spec.access.cedarPolicy`.
- **Source:** [captain brief]. Supporting:
  - A judge's hint, "you can change the Cedar policies of the agents", and the user's "for hostile and rogue tests, we can modify cedar policy" [handoff §2.5, §3b Q11].
  - [corr row 1]; [handoff §5.9].
  - "Clone rather than modify shared examples" [brief L313].
  - The limits are in R-C-04.
- **Done looks like:**
  - (a) The edit targets our own `ifabric-…` ToolConfig in `components`; a shared ToolConfig only with the user's explicit OK. It changes the ToolConfig, not its projected ConfigMap. It is logged with the user's OK (R-D-03).
  - (b) After the edit, the ConfigMap `modaas-toolconfig-<alias>` has a new resourceVersion, and the ToolConfig is still Approved with its route still programmed. Whether an edit resets approval is untested; a tool sent back to review loses its route and refuses every caller.
  - (c) A call that matches the forbid rule gets a PDP `decision=DENY` naming the policy and its version; a call that doesn't match is allowed.
  - (d) Both outcomes are in the adversarial log.
- **Note:** this configures the platform PDP's own decision. The PDP already sits in the path, so the change adds no question of ours to it. Our adapter only records the decision, through `pull` (R-P-01).

#### R-P-13 · Guards in our agent code, the only team code in the path · CAPTAIN
- **Requirement:**
  - Agents check their configuration at start and fail closed when the injected keys are missing. This is a start-up precondition, not a control question.
  - They treat tool results as untrusted.
  - They record refusals with their real status.
  - They add no second question that makes work wait. Under the captain's direction, the only in-path question is the C16 check before each model call (R-P-18). That check is also what would stop a runaway loop. The handoff's earlier recommendation of separate per-invocation turn and token limits [handoff §3b Q3] is not part of this design.
- **Source:** [captain brief]; [captain direction]. Supporting:
  - "treat tool results as untrusted in your agent" [contract, "Limits of this build"].
  - "read env, fail closed" [corr row 13].
  - The defect where a 403 is recorded as a 500 on the model [handoff §5.2].
  - [gap 8] (no platform limit stops a runaway in time).
- **Done looks like:** tests show that:
  - with a missing key variable, the agent refuses to act and records why;
  - a tool result carrying injected instructions does not change the disposition;
  - a refused tool call is recorded with its real status (for example 403, not a 500 on the model);
  - a code review finds no waiting question in the agent code apart from the C16 check.

  If the C16 check is not built, gap 8 stays open: an S2-style loop is detected after the run, not stopped.

### 2.4 Controls, the registry and threshold experiments

#### R-P-14 · Control registry dated before the assessed runs · CAPTAIN / MUST
- **Requirement:** `register.yaml` (the versioned registry of R-P-01) holds C7, C9 and C16. Each entry has [brief L187–L195]:
  - the parent control id and the specification id and version;
  - objective, risk, scope and a named owner;
  - metric, units and the exact calculation;
  - the per-observation limit, and the allowed exception rate with its denominators;
  - the measurement basis: dataset, scenarios, baseline, comparable windows;
  - the rationale and boundary conditions;
  - how missing, late, duplicate and invalid data are treated;
  - the freeze date and the runs or period it applies to.

  It also has the kit fields, including `enforcement_point`. The owner approves the version before the assessed runs [SN §14], and the freeze is scoped to agent versions [handoff §3a item 2].
- **Source:** [captain brief]; [slides p23, p26]; [brief §6]; [SN §10, §14]; [handoff §3a].
- **Done looks like:**
  - A schema check passes for all three entries.
  - The owner's approval of the frozen version sits in a place with an independent timestamp, earlier than the first assessed run (R-J-21).
  - Each entry names the agent versions (generation, model) it applies to.

#### R-P-15 · Threshold experiments before the freeze · CAPTAIN
- **Requirement:** each threshold value is justified by recorded pilot experiments, run before the freeze. Pilot runs never double as assessed runs. This is our reading of "threshold experiments"; confirm it with the captain.
- **Source:** [captain brief]. Supporting:
  - "Why this value? … 'It is what we achieved' is not an answer." "A threshold range chosen after seeing the result is a description of what you got, not a test." [slides p10]
  - "Pilot work may inform a justified threshold, but assessed results must not be used to rewrite their own acceptance criteria." [brief L199]
  - The C16 inputs [handoff §3b Q2]: S1 used 24.8K–50.2K tokens, S3 about 37.8K, S2 2.0M, at about 4.2K tokens per call on either model. The kit's 2,000, the guide's 900 and the slides' 10,000 would each breach every measured S1 and S3 run.
  - A judge's hint: "think of a risk matrix at any organisation". Tiered caps are a recommendation, not decided [mem: prooflab-project].
  - The C9 statistic (maximum and error count, or average) is open [handoff §3b Q10].
  - C7's expected events must be defined outside the graded agent [kickoff deck p21 via mem: prooflab-project].
- **Done looks like:**
  - An experiments log (run id, date, agent and model configuration, measured values) and a derivation note per threshold exist, all timestamped before the register freeze.
  - The register's "why this value?" answers cite experiment ids.
  - The assessed run ids in `run-ids.txt` share none with the pilot run ids.

#### R-P-16 · C7, automatic event recording (AIA-LOG-001), event-driven · CAPTAIN
- **Requirement:**
  - "Every in-scope event recorded and joined to one run, across all three zones." Measure "expected-event coverage, and the gap between consecutive events"; you set "the coverage target, the gap limit, and the tolerated exception rate" [slides p19].
  - "Control 7 has to work at every enforcement point at once" [slides p21].
  - "Define the expected event inventory independently of received events." "Specify event eligibility, ordering, timestamp semantics, deduplication, retries, late arrivals, missing records, and cross-zone correlation." "Explain how clock differences affect gap calculations." "Timing gaps and event completeness are separate tests" [brief L121–L136].
  - "control 7 coverage needs 'expected' defined outside the graded agent" [kickoff deck p21 via mem: prooflab-project].
  - A governed tool call is a second EP for C7 [mem: challenge-requirements].
  - In the captain's design, C7 only records. Events arrive through `emit` (agent decisions, agent-to-agent hand-offs) and `pull` (platform logs and spans). C7 is assessed after the run and never makes work wait.
- **Source:** [captain brief]; [captain direction]; as quoted.
- **Done looks like:**
  - For each named run, the assessment lists the expected count (and its source, outside the graded agent), the observed count, the missing event ids, the gap series with the violating gaps, and both denominators.
  - The coverage and gap verdicts are reported separately.
  - Model calls, governed tool calls and the emitted hand-off records are all covered.
  - A test stops the evidence store during a run: the run is unaffected, and C7 reports the lost events as missing.

#### R-P-17 · C9, drift and performance (AIA-ARC-006), continuous · CAPTAIN
- **Requirement:**
  - "A live measure watched against a frozen baseline, with a named owner who responds"; you set "the metric, the baseline, the drift limit and the violating-window allowance" [slides p19].
  - "Choose a meaningful diagnostic/performance metric, justify it, freeze a baseline, and define comparable measurement windows before assessment." Declare the per-window drift limit, the permitted share of violating windows, the required measurement coverage and the named alert owner. Specify zero or invalid baselines, insufficient samples, missing measurements and changes in workload mix. "A missing measurement is not zero drift." [brief L138–L156]
  - "control 9 drift needs a stable baseline" [kickoff deck p21 via mem: prooflab-project].
  - The alert "needs to go to a human, and you need to know what that human name is" [transcript].
  - The platform's signal: AgentCore Latency and Errors per runtime, per closed UTC hour. Latency is per invocation and moves with call count; Errors stayed at 0 through the S2 runaway; an hour with no invocations has no data [handoff §3b Q10; mem: prooflab-project].
  - In the captain's design, C9 only records. Metrics arrive by `pull` each closed hour, and the alert to the owner goes out, with its response coming back by `callback`. C9 never makes work wait.
- **Source:** [captain brief]; [captain direction]; as quoted.
- **Done looks like:**
  - A baseline file (hours, values, agent and model configuration and version) is dated before the assessed windows.
  - A window query for T1..T2 returns, for each closed hour: the value, the drift, crossings, coverage, the alert sent per crossing and its response state.
  - A missing hour shows INDETERMINATE with a monitoring-gap finding, not "healthy".

#### R-P-18 · C16, per-run token spend cap (ACN-COST-001), in-transaction · CAPTAIN
- **Requirement:**
  - "Token spend summed across all three agents and every retry, for the whole run." Measure "input plus output tokens, reconciled per run"; you set "the cap, and whether any over-cap run is permitted at all" [slides p19].
  - "The scored measure described in the deck is tokens. Monetary estimates are supplementary." "Preserve unique call IDs, attempts, usage, run membership, threshold version, decisions, and stop records. Separate post-run detection from actual prevention." [brief L158–L168]
  - The figure of record is the gateway's per-call line. Its durable copy is the gateway's spans in `aws/spans`, kept 30 days or until the account is torn down; use model calls only, and count by run id, not by trace [handoff §5.3, §10; corr rows 3, 7].
  - Whether helper and investigator calls count must be decided [handoff §3b Q2].
  - **The floor:** post-run C16, recomputed through `pull` from `aws/spans` after the run.
  - **The option:** an in-transaction check before each model call, through `evaluate()`. It uses a frozen, version-stamped threshold loaded before the run, so the registry is never called in the path. This is the only question in the whole design that may make work wait (R-P-01). It must handle the race: "Reserve, then commit" [slides p14; brief L170–L181].
  - The check's verdict is recorded afterwards, through `emit`.
- **Source:** [captain brief]; [captain direction]; as quoted.
- **Satisfies:**
  - R-J-48: "Only the enforcement point may make the work wait, and only for one question".
  - R-J-26, the LOSE item "a design that only works in the request path": the post-run floor gives the same verdict when the inline check is off or not built.
  - R-J-18, the continuous-compliance bonus, only if the inline check is built and shown live.
- **Done looks like:**
  - For each named run, the tool's total equals the Logs Insights sum over `aws/spans` for that run id (the query in handoff §10), and the call counts match.
  - The PASS and BREACH named runs are assessed under one version.
  - The breach raises a finding and an incident.
  - If the inline check is built:
    - each of its records carries the threshold version it loaded;
    - a run with the check switched off gets the same post-run verdict;
    - the concurrency test of R-J-48 passes;
    - the place where the per-run spend state lives is named. It is shared across three runtimes, and that place is constrained by R-C-01 and R-C-02.
  - If C16 is post-run only, the pack says "detection, not prevention", and gap 8 stays open.

### 2.5 Agents: closing the judgment gap, emitting real evidence

#### R-P-19 · Agents gather evidence or escalate instead of guessing · CAPTAIN / MUST
- **Requirement:**
  - The agents "guess confidently under ambiguity. Closing that gap is the game." [kickoff deck p2]
  - "The judgment they lack — know when to gather evidence or escalate, not act"; "A passing grade on the fault the reference agents cannot crack" [kickoff deck p5].
  - The targets [handoff §3b Q8]: S2 → gather-evidence, naming the evidence that would settle it and proposing a reversible action; S3 → escalate; S1 → auto-resolve.
  - An empty tool result ("no twin data") leads to gather-evidence or escalate [gap 10].
  - The disposition is a recorded decision with a reason, not a keyword match [gap 1].
- **Source:** [captain brief]; as quoted; [slides p23: "ALLOWED: Building more or changing the agents"].
- **Done looks like:**
  - On fresh S1, S2 and S3 runs of our agents, the dispositions are auto-resolve, gather-evidence and escalate respectively, each with its reason and its deciding evidence in the ledger.
  - `score-run.py` passes its disposition and scenario checks. This is diagnostic only: today it fails every reference run by construction [handoff §5.6; corr row 4].
  - Gaps 1 and 10 are updated.

#### R-P-20 · Agents emit real evidence · CAPTAIN
- **Requirement:**
  - Ledger records carry what the platform knows: the inbound run trace (not an agent-minted id), the action id, the model, the tokens, the guardrail outcome and the correct refusal status.
  - Intent is recorded before invocation.
  - Hand-off records name from and to (R-P-02). They are record events: `emit` only, for C7 and RECONSTRUCT, never blocking.
  - All agent records go out through `emit`, off the path; a failed emit never stops the agent (R-P-01 (f)).
  - The CID travels in baggage.
  - Module 7: "The evidence shape (intent before invocation, guardrail verdict on every model call, recorded disposition) is the shape judges score."
  - Every change goes CodeBuild → AgentConfig → approval, and counts as a new C9/C16 treatment.
- **Source:** [captain brief]; [mem: prooflab-project] (the minimal fix; the Module 7 quote); [handoff §3b Q12]; [corr row 4]; [gap 7].
- **Done looks like:**
  - For a named run, every ledger model-call record joins its span in `aws/spans` by action id.
  - The ledger's trace ids equal the run trace.
  - A refused call's record shows its real status.
  - The agent version used is recorded, and it was deployed and approved before the register freeze and the C9 baseline (R-D-08).

### 2.6 The ServiceNow human loop

#### R-P-21 · Alert a named human; record the response or the silence · CAPTAIN / MUST
- **Requirement:**
  - Every BREACHED, ESCALATED and monitoring-gap finding becomes exactly one ServiceNow incident, assigned to the control owner, raised off the request path.
  - Delivery counts only after a readback.
  - The response, or the silence after a stated cutoff, is recorded, and the incident is exported.
  - The slides: "the alert, its named recipient and the silence must still be recorded" [slides p23].
  - The transcript: "the service now control tower and human loop that is absolutely needed".
  - The brief §9: implement and evidence the alert, its named recipient and the pending or unanswered state; "Do not fabricate acknowledgment or closure."
  - In the captain's design, the human loop only records. The alert goes out after evaluation, and the owner's response comes back by `callback`, collected with `check` (a `pull`). Nothing waits on the human.
- **Source:** [captain brief]; [captain direction]; as quoted; [SN §6–§8, §13].
- **Satisfies:** R-J-26, the LOSE item "a design that only works in the request path": "ServiceNow is never in the agent's request path" [SN §3].
- **Done looks like:** for each breaching named run:
  - there is one incident, and a re-run reuses it;
  - `delivery-log.jsonl` shows DELIVERED;
  - `check` gives RESPONDED, or NO_RESPONSE_OBSERVED after the cutoff;
  - the `export` JSON is in `evidence/servicenow/incidents/`.

  The app shows the human-loop line offline. Code review finds no ServiceNow call in any agent or gateway path.

#### R-P-22 · Findings follow the Finding contract · MUST (team interface)
- **Requirement:** each finding has these fields [SN §6]:
  - `control_ref`: C7, C9, C16 or ESC.
  - `control_id`: AIA-LOG-001, AIA-ARC-006, ACN-COST-001 or AGENT-ESCALATION.
  - `threshold_version`: "Exactly the frozen version in register.yaml … Never latest".
  - `scope_kind`: run, window, interval or escalation; and `scope_id`.
  - `verdict`: BREACHED, ESCALATED, INDETERMINATE or SATISFIED.
  - `summary`: measured against the limit, about 100 characters.
  - `detected_at`: ISO-8601 UTC.
  - `evidence`: resolvable references with the §8.2 prefixes.
  - `kind`: finding, monitoring-gap or escalation.

  The rules:
  - `finding_id = ifabric:{control_ref}:{threshold_version}:{scope_kind}:{scope_id}:{kind}`, at most 100 characters, hashed if longer.
  - `^`, CR and LF are rejected.
  - An assessment is written for every scope, SATISFIED included.
  - Only BREACHED, ESCALATED and monitoring-gap findings notify.
- **Source:** [SN §6, §7, §8.2].
- **Done looks like:**
  - Every finding file passes `finding_from_dict` (`prooflab/servicenow/finding.py`).
  - A test asserts that each `threshold_version` exists in the register.
  - Every evidence reference resolves to a file or record in the pack.
  - There is an assessment per scope, even where no finding was raised.

#### R-P-23 · The S3 escalation path, proven once · MUST (team interface)
- **Requirement:** a ledger `disposition=escalate` produces an ESC finding (`scope_kind` escalation, verdict ESCALATED) and an incident whose work notes carry the ledger chain. The producer that reads escalations from the ledger has still to be written: the package never reads the ledger [handoff §3b Q15].
- **Source:** [SN §7.4, §13]; [handoff §3b Q15].
- **Done looks like:** one exported ESC incident with its ledger chain.
- **Note:** in the captain's design nothing waits on the escalation: it is recorded, and the human's verdict arrives by `callback`. So it cannot be presented as an EP that refuses (corr row 12; R-J-20; tension T5).

#### R-P-24 · AICT evidence (L2) · MUST if AICT is required (OPEN)
- **Requirement:** our agents are visible in AICT under team-named runtimes through the team's connection; AICT evidence is exported; AICT's limits are stated. The brief: "Inventory visibility does not prove complete traces or runtime enforcement." "Show what AI Control Tower contributes to our claim and what our own evaluator, ledger, and query tool contribute."
- **Source:** [transcript] (connector and agent naming); [SN §2, §9] (UNVERIFIED by us); [handoff §5.8]; [corr row 11]; [brief L317, L323].
- **Done looks like:**
  - `evidence/servicenow/aict/` holds dated exports or screenshots that show our `ifabric_…` runtimes, the CloudTrail AssumeRole record of the AICT role, and the `/aws/bedrock/aict-invocations` records for the named runs (kept 7 days).
  - The gap list states AICT's scope (AgentCore runtimes and gateways only), its usage count of 0 for our traffic, and Monitor's Managed-only coverage.

### 2.7 The adversarial log

#### R-P-25 · Adversarial log · CAPTAIN / BONUS
- **Requirement:**
  - `evidence/adversarial/` holds one entry per case: what was attacked, the expected defence, the observed behaviour, evidence references, what broke, what we changed and the re-test result.
  - It covers the Hostile and Rogue conditions.
  - Candidate cases from the brief [brief L341–L348]: dropped, duplicated, reordered or late events; broken run links and missing expected measurements; threshold version changes and baseline contamination; parallel budget requests, retry accounting and overspend; evaluator or evidence-delivery failure; delayed or unanswered human callbacks; prompt injection in untrusted content and attempted control bypass.
  - "Clearly separate synthetic fixtures, fault injection, replay, and live sandbox execution." [brief L352]
  - Tamper tests run on exported copies only. Never write down methods for forging or altering evidence records [handoff §3c step 6, §8].
- **Source:** [captain brief]; [slides p25, p26]; [PB §4.4]; [brief §10]; [handoff §3c, §8].
- **Done looks like:**
  - At least one case exists per Hostile and Rogue category we claim (R-J-36, R-J-37).
  - Every case has all the fields and an execution-type label: synthetic, fault injection, replay or live.
  - At least one case shows a break, a change and a passing re-test.
  - Every live case carries its run id and time, inside the declared window, labelled as test traffic.

---

## 3. R-C: platform constraints (verified)

Verified read-only on 2026-10-05 unless marked otherwise. Re-verify before the assessed runs [mem: platform-verified-facts].

#### R-C-01 · Where our code may run · CONSTRAINT
- **Constraint:** according to the platform page, as verified, team code runs in the request path only in the AgentCore Runtime (our agents) and, with the token, as writes to the ledger.

  | EP (page) | Page says: refuse/observe; our code? | Verified | What it means for us |
  |---|---|---|---|
  | `modaas-agw` + `modaas-pdp` (Cedar) | Refuse; "No, Cedar policy via ConfigMap" | PARTLY. It refuses on authentication and fails closed, but no Cedar policy has ever refused (0 DENY in 1,097 decisions). A team ConfigMap decides nothing; the live lever is the ToolConfig `access.cedarPolicy` | No code of ours. Cedar only through our ToolConfigs (R-C-04); the adapter reads its log (`pull`) |
  | Bedrock Guardrails | Refuse; "No, declared on ModelConfig" | CONFIRMED. Blocks are recorded as ALLOW | Read the outcome from the gateway line (R-C-05) |
  | Admission (CEL) | Refuse; "No" | CONFIRMED. 94 CEL rules plus the admission policy | Our CRs must pass it (R-C-02) |
  | Evidence ledger (token-gated writes) | Refuse; "Yes, with token" | CONFIRMED. Every participant can read the token; the gate refuses writes, not agent actions | We may write records to it; it does not gate actions |
  | AgentCore Runtime | Observe; "Yes" | PARTLY. Our code runs here and can refuse its own next call; the runtime role denies direct model and AgentCore-gateway access | The only place for in-path team logic (`evaluate`) |
  | OTel collector / CloudWatch | Observe; "No" | CONFIRMED. Traces go to X-Ray and `aws/spans`, the audit log to `/modaas/evidence`, the gateway log to `/aws/modaas/gateway`; metrics are dropped | A read-only source |

  Other facts:
  - Also enforcing, but not on the page: `modaas-authz` (the API key, fail-closed), the rate ceilings, the kill switch (404), the runtime IAM deny, and the AWS AgentCore Gateway (`AWS_IAM`).
  - "Cedar does not meter tokens."
  - A gateway `extAuth`/`extProc` hook is allowed by RBAC, but the admission policy's text refuses it in `agentgateway-system` (untested). A route plus a policy in a team namespace falls outside the policy's text (untested).
  - The off-path parts (collectors, the evidence store, the stitcher, evaluators, the query tool, the app) are not EPs. They may run on the laptop or IDE or, with the user's OK, in `components`.
  - Agents run only on AgentCore (Strands) or in ServiceNow (R-J-05).
- **Source:** [contract]; [contract-verify §2]; [handoff §5.9, §3b Q3, Q11].
- **Done looks like:**
  - The architecture's component table gives every component a host.
  - Every in-path component is our agent code or a platform-native lever (ToolConfig Cedar, a pause).
  - Any use of the external-authorization hook or the team-namespace route is marked UNTESTED and carries a user decision.
  - No component lives in a protected namespace.

#### R-C-02 · The admission policy: 9 protected namespaces; `components` is open · CONSTRAINT
- **Constraint:** the admission policy `modaas-governance-guardrail` (failure policy Fail, binding Deny) matches participants and refuses CREATE, UPDATE and DELETE:
  - (1) in nine namespaces: `modaas-system` (except labelled team Cedar ConfigMaps), `agentgateway-system`, `canvas`, `canvas-system`, `canvas-vault`, `istio-system`, `istio-ingress`, `cert-manager` and `kube-system`;
  - (2) for cluster-scoped writes to RBAC, `admissionregistration`, nodes, the protected namespaces, and CRDs named `*.oda.tmforum.org`, `*.agentgateway.dev`, `*.gateway.networking.k8s.io`, `*.istio.io` or `*.cert-manager.io`.

  What stays open:
  - `components`, where our AgentConfigs and ToolConfigs live; team namespaces; reads; CONNECT. The broad participant RBAC is not permission.
  - The 94 CEL rules still check our CRs. For example, `safety.required` demands `approval.required`, and `modelRef` must be one of `dependsOn.models`.
  - The refusals themselves are untested.
- **Source:** [handoff §5.9, §8]; [contract-verify addendum]; [mem: platform-verified-facts]; [mem: challenge-requirements].
- **Done looks like:**
  - Every planned cluster write names its namespace and kind.
  - None targets a protected namespace or a protected CRD.
  - Each is dry-run on the server where possible before the real write, and has the user's OK.

#### R-C-03 · One shared identity · CONSTRAINT
- **Constraint:**
  - Every agent calls as `ServiceIdentity::"bootstrap-key"` (1,107 of 1,107 authenticated evidence records).
  - One gateway key sits in every runtime's environment (as `OPENAI_API_KEY` and `AGENTCORE_GATEWAY_MCP_TOKEN`).
  - All runtimes share one IAM role.
  - Per-agent Keycloak identities exist but are not provisioned.
  - The gateway's model lines carry no agent identity.
  - `modaas-authz` writes nothing per call to its pod log.
- **Source:** [handoff §5.1]; [gap 2]; [contract-verify §8]; [mem: platform-verified-facts].
- **Done looks like:**
  - No part of the design relies on a per-agent platform identity or on per-agent Cedar.
  - WHO answers cite our own records, corroborated by the per-runtime log groups and metrics, and name gap 2.
  - The `actor` field of R-P-02 says where it came from.

#### R-C-04 · Cedar levers and limits · CONSTRAINT
- **Constraint:**
  - The live lever is the ToolConfig `spec.access.cedarPolicy`. The operator projects it to `modaas-system/modaas-toolconfig-<alias>`, labelled as operator-managed, so edit the ToolConfig, not the ConfigMap.
  - Each decision evaluates one policy: the called asset's.
  - Cedar sees the principal (always `bootstrap-key`), the action `invoke`, the resource (tool or model, plus its dataClassification) and the context (toolName, arguments, dataClassification, traceId, actionId, toolMethod). It does not see the calling agent, the route, call counts or tokens, and it is stateless.
  - The team ConfigMap `my-team-policy` is inert (named in 0 of 1,097 decisions).
  - The AgentConfig overlay is not wired.
  - ModelConfig `allowedConsumers` is `['bootstrap-key']` only.
  - No Cedar policy has ever denied.
  - `customer-records` and `network-twin` have no dataClassification.
  - The policy version is the ConfigMap's resourceVersion.
  - Whether an edit propagates, and whether it resets approval, is untested.
  - Every edit is a cluster write.
- **Source:** [handoff §5.1, §5.9]; [corr row 1]; [mem: platform-verified-facts]; [contract-verify §2].
- **Done looks like:**
  - Any Cedar rule in the design is per tool, applies to all callers and is stateless.
  - Each has an end-to-end DENY test (R-P-12).
  - No rule assumes per-agent, per-run or token-aware Cedar.

#### R-C-05 · Guardrail behaviour · CONSTRAINT
- **Constraint:**
  - There is one Bedrock guardrail per ModelConfig (4 READY), with `safety.required: true` and the `bedrockGuardrail` enforcer.
  - A block returns HTTP 200, `finish_reason=content_filter`, 0 tokens and zero cost; its gateway line still has run and action ids.
  - The PDP and `/modaas/evidence` record a block as ALLOW, with no guardrail field; the reference template records "undetermined".
  - Screening of tool output is untested.
  - The guardrails are the platform's; they are not ours to change.
- **Source:** [handoff §5.2, §5.9]; [gap 4]; [contract]; [mem: platform-verified-facts].
- **Done looks like:** the evidence model derives "blocked" from the gateway line or span. Nothing in the design reads a block from the decision record.

#### R-C-06 · Evidence surfaces, keys and retention · CONSTRAINT
- **Constraint:** the platform's evidence lives in these surfaces:

  | Surface | Kept | Keys | Use and caveats |
  |---|---|---|---|
  | Gateway pod stdout | Pod lifetime | `modaas.run_id` (the CID, else the trace id; values quoted), `modaas.trace_id`, `modaas.action_id`; tokens, cost, duration | The C16 figure of record as the kit reads it. The 573 refused or unrouted lines carry no ids |
  | `aws/spans` (gateway spans) | 30 days, or until teardown | `attributes.modaas.run_id`, `attributes.modaas.action_id`; tokens, cost and model on model calls | The durable source for C16 and RECONSTRUCT. Count by run id, not by trace. The kill-switch 404 and MCP GET 405s have no run id |
  | `/modaas/evidence` | 30 days | `correlation_id` (the CID), `action_id`, `trace_id`, decision, policy id and version, principal | The only per-call WHO record. It records blocks and pauses as ALLOW |
  | `/aws/modaas/gateway` | 7 days | `trace_id` only | Tokens per call; no run or action id (a build gap) |
  | PDP pod logs (2 replicas) | Pod lifetime | `action_id`, `trace_id`, policy id, decision | No principal. Read both replicas |
  | authz pod logs | Pod lifetime | none | Startup lines only |
  | X-Ray | Durable | Trace id; the ids are metadata, not annotations | Truncates long runs (S2: 22 of 174 model calls); agent subsegments double-count tokens |
  | Ledger (audit-store) | The volume, deleted with the stack | `correlation_id`; an agent-minted `trace_id`; `seq` (can collide) | `/records?cid=` gives JSONL. No verify route; keeps writer-supplied timestamps |
  | AgentCore runtime logs | Never expire | Run trace id | The spans hold the system prompt and customer records |
  | AgentCore metrics | CloudWatch, hourly | Runtime | Latency per invocation, Errors, Invocations; no data for idle hours |
  | `/aws/bedrock/aict-invocations` | 7 days | `InvokeAgentRuntime`: `eventTime` (the call's end), runtime ARN, caller, and in `responseElements` the caller-sent CID (`baggage`), session id and traceparent. Model calls (`Converse*`): time, model, tokens, guardrail verdict; no run id | Written by AWS. The invocation records join a run exactly by CID and session id; model calls only by time and model. Delivered 19–328 s late, so join on `eventTime` (corrected 2026-10-05 after live re-check) |
  | CloudTrail lookup / EKS audit / `components` events | 90 days / off / about 1 hour | none | `describe-trails` is denied |
  | `AWS/Bedrock` metrics; gateway `:15020` metrics | CloudWatch / cumulative | Model id | Can't be joined to a run |

  The join path: the baggage CID → the gateway `run_id` (stdout, ephemeral; `aws/spans`, 30 days) → the `/modaas/evidence` `correlation_id`. The action id links the response header, the gateway line, the spans, the PDP, `/modaas/evidence` and X-Ray. The ledger joins by `correlation_id` only. `/aws/modaas/gateway` and refusals join by trace id.

  How the kit's tools behave:
  - `pull-evidence.sh` reads the gateway pod's stdout (`--tail=50000`).
  - The platform page's gateway grep matches nothing because the values are quoted; use `grep -F "modaas.run_id=\"$CID\""`.
  - `show-run-spans.py` doubles the token totals.
  - `evaluate.py` implements C16 only.
  - `score-run.py` reads the ledger text and grades its evidence shape.
  - The PDP logs need `--all-pods`.

  Everything here is destroyed with the account (R-C-17).
- **Source:** [handoff §5.3, §10]; [contract-verify §3–§5]; [mem: platform-verified-facts]; [corr rows 3, 7].
- **Done looks like:**
  - Before the account ends, the exporter captures every surface the controls and the six questions use into `evidence/raw/`, with its capture time and exact query.
  - C16 from `aws/spans` matches the stdout figure for each named run.
  - The PDP is captured from both replicas.
  - The ledger is exported through `/records`.
  - A re-snapshot is taken after the last assessed run (handoff §3a item 5).

#### R-C-07 · Budget ceilings · CONSTRAINT
- **Constraint:**
  - Models: 100 requests per minute and 2.5M tokens per hour. MCP: 100 requests per minute.
  - These are local limits on the single gateway replica, so in effect one budget for the whole account. Our agents, the helper, investigator calls and adversarial tests all share it.
  - The token ceiling binds first: S2 used 80% of the hourly tokens in under 5 minutes, at a peak of 49 calls a minute.
  - "stay under one model request/second" [kickoff deck p8]. OPEN: per agent or per account.
  - The 429 and its claim of no charge are untested.
  - Measured runs: S1 24.8K–50.2K tokens, S3 about 37.8K, S2 2.0M, one helper question 123K.
- **Source:** [handoff §3d, §5.5, §5.6]; [gap 8]; [contract-verify §9].
- **Done looks like:**
  - Every live run in the plan has a token estimate.
  - Before each run, the live lane checks the tokens used in the last 60 minutes and the remaining headroom.
  - No two live runs overlap.
  - The plan's total per clock hour stays under 2.5M with a margin.

#### R-C-08 · Temporary credentials and our identity · CONSTRAINT
- **Constraint:**
  - The AWS credentials of the `hackathon` profile expire; they did at about 18:20 UTC on 2026-10-05. Only the user can refresh them, from the Workshop Studio dashboard.
  - Without them there are no live checks, no secret scan (it fails closed) and no push.
  - `/tmp/modaas-token` is lost on a reboot.
  - Our shell runs as WSParticipantRole, not the IDE role, and the two have different rights.
  - Never write the two AWS credential variable names, or the cockpit's token query parameter followed by "=", in any repo file: the pre-push scan fails on them even without values.
- **Source:** [handoff §0.4, §8]; [mem: hackathon-working-agreement]; [contract-verify §9].
- **Done looks like:**
  - The live lane starts each session with an identity check (WSParticipantRole) and stops on ExpiredToken.
  - The offline parts (the app, and evaluators over exported files) need no credentials.
  - No step after the account ends depends on AWS.

#### R-C-09 · Approvals are a human act · CONSTRAINT
- **Constraint:**
  - An approval is two free-text annotations (`modaas.tmforum.org/approver`, `modaas.tmforum.org/approval-attestation`); they produce an approval record with an empty `signature`.
  - The approver string is self-asserted, and EKS audit logging is off.
  - A model swap needed no re-approval, and re-attesting adds no record. Approved does not mean the runtime is READY.
  - Approvals, and the owner's sign-off on thresholds, are made by the named human, never by a worker on its own initiative. "Do not invent people or approvals."
  - The slides' example of a good control: "Any change beyond a routine one is approved by a named person, and the work stops if it is not."
- **Source:** [handoff §5.5]; [gap 5]; [brief L54]; [mem: hackathon-working-agreement]; [SN §14]; [slides p6].
- **Done looks like:**
  - Every approval record and owner sign-off in our chain traces to a dated user instruction in the live-lane log.
  - Approvals older than the running version are flagged in the pack (R-J-32).
  - Approvals are recorded as decisions in the evidence store (R-P-02).

#### R-C-10 · The token-leak must-fix, and secret handling · CONSTRAINT / MUST
- **Constraint:**
  - `pull-evidence.sh:78` writes the full Model, Tool and AgentConfig objects to `cr-status.json`, including the literal ledger write token from every AgentConfig spec. A second copy is expected in the last-applied annotation (not verified).
  - `submit.sh` zips `~/evidence` as it is, uploads it to the bucket the judges read, and leaves the zip in the current directory.
  - The pre-push scan guards the repo, not the upload.
  - `tmf639.json` is unchecked.
  - Never print or commit the gateway key, the ledger token, the AWS credentials, the IdeUrl or CockpitUrl and their tokens, the AICT connector key, the ServiceNow client id and secret, or presigned URLs.
  - Never dump AgentConfig YAML or `get-agent-runtime` output without a filter that leaves out the environment values.
- **Source:** [handoff §3d, §8, §9]; [gap 6]; [mem: challenge-requirements].
- **Done looks like:**
  - Before `submit.sh` runs, a redaction step removes the environment values from `cr-status.json` and from any other CR dump.
  - An exact-value scan of the unzipped submission, using the same values as the pre-push scan, finds 0 hits.
  - Neither the zip nor the raw `evidence/` dumps are committed.
  - The app shows no secret.

#### R-C-11 · No Lambda, IAM or AgentCore-gateway changes · CONSTRAINT
- **Constraint:**
  - Never change the shared `team-*` tool Lambdas. They run unpinned `$LATEST`; the participant policy would allow `UpdateFunctionCode` (gap 11).
  - Never use the IDE role's rights to create, update or delete the AgentCore gateway.
  - Make no IAM changes.
  - Never run the AI Native Networks workshop's cleanup scripts: they delete every AgentCore gateway, runtime and memory in the region.
  - Don't touch resources we didn't create (for example `demo-crm-lookup`) without asking.
- **Source:** [handoff §3d, §8]; [corr row 14]; [gap 11]; [mem: hackathon-working-agreement].
- **Done looks like:**
  - The live-lane log holds no Lambda, IAM or AgentCore-gateway write.
  - A CloudTrail `lookup-events` spot check over the build window shows none from our sessions.

#### R-C-12 · Kill switch behaviour · CONSTRAINT
- **Constraint:**
  - Pausing an asset (`spec.paused`) withdraws its route, and calls get a 404.
  - The delay varies: nano-9b kept serving for 33–41 s; super-120b stopped within 2 s; tools in about 1–7 s. Resuming takes about 24–35 s.
  - Stale pause conditions remain afterwards.
  - A pause hits every agent that uses the asset, declared or not.
  - The 404 is recorded as ALLOW, and its gateway line has no run or action id; it joins by trace id.
- **Source:** [handoff §5.7, §5.2]; [corr row 6].
- **Done looks like:**
  - Any pause in the design records its requested and effective times and its true outcome.
  - It runs only in the live lane, with the user's OK.
  - It is never presented as a per-run control.

#### R-C-13 · Agent and model change mechanics; naming · CONSTRAINT
- **Constraint:**
  - The runtime model is the environment variable `MODEL_ALIAS`, which follows `dependsOn.models[0]`. Which field wins when `modelRef` differs is untested. A CEL rule requires `modelRef` to be one of `dependsOn.models`.
  - A swap re-programs the runtime in about 13–24 s, with no re-approval.
  - The IT agent has been on `nemotron-nano-9b` since 05:47Z. Keeping or reverting it is a user decision, due before the C9 baseline.
  - New agents go CodeBuild → AgentConfig → approval.
  - Names typed into `new-agent.sh` must match `^[a-z][a-z0-9-]{0,38}[a-z0-9]$` (so `ifabric-…`). Only `--dry-run` checks the name before the build. AgentCore and AICT then show `ifabric_…`.
  - `new-agent.sh --tool` doesn't write `dependsOn.tools`.
  - Models: the four governed aliases (`nemotron-nano-9b`, `nemotron-nano-3-30b`, `nemotron-super-120b`, `nemotron-super-120b-helper`), in-region in us-east-1. Tokens per call are about the same on both models in use; the cost differs.
- **Source:** [handoff §3a item 1, §4.4, §7.1, §10]; [corr row 9]; [mem: challenge-requirements].
- **Done looks like:**
  - Every agent version used in an assessed run is recorded (generation, model, image) and mapped to the register version and the C9 baseline.
  - Every new name passed a `--dry-run` before its real build.

#### R-C-14 · The twin can't make breaches on demand · CONSTRAINT
- **Constraint:**
  - The `network-twin` Lambda serves its own packaged dataset: 3 sites, none for S2.
  - The kit's recipes are broken, and the agents query the twin with element ids.
  - So the twin's scenario switch can't produce named pass and breach runs.
  - The platform page's breach recipes (lower the cap; pause a tool mid-run; swap the model) are untested writes.
- **Source:** [corr row 5]; [gap 10]; [handoff §3b Q5]; [contract-verify §8].
- **Done looks like:** the named-run plan names its breach lever and does not depend on the twin's switch.

#### R-C-15 · The shared ServiceNow instance and AICT · CONSTRAINT
- **Constraint:**
  - All teams share one ServiceNow instance. Touch only records created by our integration user.
  - Never change ServiceNow users, OAuth apps, system properties, risk frameworks or other teams' agents.
  - Credentials come only from the environment: read silently, never printed.
  - AICT sees AgentCore runtimes and gateways only. It counts 0 usage for our traffic, because it filters on `InvokeAgent`. Monitor covers Managed agents only. Imports run every 15 minutes and take about 4 minutes.
  - Adapter caveats (accepted risks): `notify --dry-run` may log DELIVERED and is not offline; an empty journal read can turn into NO_RESPONSE_OBSERVED.
  - One incident per C9 crossing window could flood the shared instance.
- **Source:** [SN §2, §4, §10, §11]; [handoff §4.3, §4.4, §5.8]; [corr row 11]; [transcript] (shared environment, team naming).
- **Done looks like:**
  - Code review shows every ServiceNow lookup filtered to our integration user.
  - Nothing relies on `--dry-run` being offline.
  - The C9 incident volume has a declared bound, agreed with the owner.

#### R-C-16 · The evidence bucket · CONSTRAINT
- **Constraint:**
  - Participants can put, get, delete and list objects in `team-evidence-…`, but can't read its versioning, object lock or lifecycle settings or list its versions (AccessDenied).
  - The bucket is versioned all the same: CloudTrail shows versioning enabled at stack creation (2026-10-04 10:19:55 UTC), noncurrent versions kept 7 days, server access logging to a bucket participants can't reach, and no Object Lock. Since 2026-10-05 18:10:39 UTC the IDE role can list and read versions (`EvidenceVersionRead`). Neither team role can delete a version: a participant delete only adds a delete marker. So an object's version id, upload time and version history are AWS-set evidence of when it was uploaded and whether it was replaced, not proof that its content was unaltered before upload (corrected 2026-10-05, from live reads during the architecture work).
  - The bucket was empty at the last check.
  - `submit.sh`'s fallback bucket lookup returns empty in this account, so `TEAM_EVIDENCE_BUCKET` must stay set.
  - The judges read this bucket.
- **Source:** [corr row 15]; [handoff §2.4, §7.5]; `architecture/work/03-decision-options.md` §2, F1.
- **Done looks like:**
  - The submit runs with the variable set.
  - Integrity of content rests on the MANIFEST readback (R-J-44). The bucket's version history, read from the IDE role, adds AWS-set upload times and shows any replacement within 7 days; it doesn't prove the content (corrected 2026-10-05, from live reads during the architecture work).

#### R-C-17 · Account teardown · CONSTRAINT
- **Constraint:** "back up your work as you go because the account is destroyed when the event ends" [kickoff deck p8]. With the account go `aws/spans`, every log group, the ledger volume and the cluster. The dashboard shows a 72-hour account lifetime from 10/04/2026 09:00 AM, with no time zone.
- **Source:** [handoff §2.5, §3a item 5]; [mem: prooflab-project].
- **Done looks like:**
  - A final export of every surface in R-C-06, and of our evidence store, exists outside the account (on the laptop and in the S3 submission) before the deadline.
  - The pack and the app need no live AWS resource.

#### R-C-18 · Transport and data exposure (the platform's, not ours to fix) · CONSTRAINT
- **Constraint:**
  - The runtimes reach the gateway over plain HTTP on a public load balancer, so the shared key travels unencrypted. The TLS listener on :8443 is unused and untested.
  - Agent spans store prompts and customer records.
  - `customer-records` has no data classification.
- **Source:** [gap 9]; [handoff §5.1].
- **Done looks like:**
  - These appear as platform gaps in the EP security table (R-P-10) and in the gap list.
  - Nothing we build adds another plain-HTTP or public endpoint (R-P-07).

---

## 4. R-D: delivery

#### R-D-01 · Deadline: Tuesday 2026-10-06 15:00 UTC (UNCONFIRMED) · DELIVERY
- **Requirement:**
  - The transcript: "The hackathon will officially end at 10 a.m on Tuesday morning. That's when work will stop and judging will begin." The event's times are CDT ("all these times are based on Dallas Times, which is Central Daylight Time, UTC minus 5"), so that is 2026-10-06 15:00 UTC. The date has not been confirmed independently.
  - 18.4 hours remained at 20:33 UTC on 2026-10-05.
  - "Assemble … the evening before" (R-J-45) means tonight.
  - The account is destroyed at the end (R-C-17).
- **Source:** [transcript]; [handoff §2.5]; [mem: prooflab-project]; [brief L387–L391] ("Do not invent calendar dates"; "Confirm the applicable schedule").
- **Done looks like:**
  - The plan sets dated cut-offs, all before 15:00 UTC with a buffer, for: the register freeze, the last assessed run, the final evidence export, the submit and readback, and the two rehearsals.
  - The end time is confirmed with the organisers, or the plan uses the earliest reading.

#### R-D-02 · Two people; four roles; nobody checks their own work · DELIVERY
- **Requirement:**
  - The team is two people. The user (Sree) builds the AWS side, is the control owner of all three controls (accountable management), and approves the thresholds and every live write. Arth runs the ServiceNow workstream: L2 and L3, incidents, AICT exports, a ServiceNow-native agent.
  - "AND FOUR ROLES, BECAUSE NOBODY MAY CHECK THEIR OWN WORK": accountable management, GRC, operations and assurance [slides p8].
  - "the person who ran the test is not the person judged by it" [slides p5].
  - "Record real owners when known and preserve independent review of control results. Do not invent people or approvals." [brief L54]
  - The owner also builds, so separation of duties needs a plan [handoff §3b Q14].
- **Source:** as quoted; [handoff §1]; [SN §14].
- **Done looks like:**
  - A roles table names a real person for each of the four roles, or states the vacancy.
  - Each control result's assurance check is signed off by someone other than its builder.
  - Where separation is incomplete, the gap list says so.

#### R-D-03 · A Firstmate fleet in parallel, one serialized live lane · DELIVERY
- **Requirement:**
  - Parallel workers (the captain's Firstmate fleet) do the offline work: code, evaluators, the evidence store, the stitcher, the app, documents, reviews, and analysis of exported evidence.
  - Exactly one lane does live work, one action at a time: agent runs; cluster writes (Cedar edits, pauses, model swaps, approvals, new agents); ServiceNow writes; the S3 submit.
  - Each live action has the user's OK, an identity check, a budget-headroom check and a log entry.
- **Source:** [captain brief]. Supporting:
  - "If parallel workers are available, delegate independent implementation, integration, and adversarial review tasks with clear ownership. Keep one consistent evidence contract and integrate frequently." [brief L364]
  - "Serialize runs and check headroom first" [handoff §3d].
  - Read-only by default, ask before writes, and delegate to subagents [mem: hackathon-working-agreement].
- **Done looks like:**
  - A live-lane log records start, end, action, approver (with the user's words), run id and tokens used for every live action.
  - It shows no overlapping live actions and an OK for every write.
  - A review of the parallel workers' transcripts or diffs finds no live write.

#### R-D-04 · No-mistakes PRs · DELIVERY
- **Requirement:**
  - Every repo change lands through a branch and a pull request, run through the `no-mistakes` pipeline. Its configured steps are rebase, lint, test, agent review, document and CI, with auto-fix.
  - The pre-push secret scan prints `RESULT: clean` before every push; it needs live AWS credentials.
  - Commits carry the Co-Authored-By trailer.
  - The memory copy in `notes/claude-memory/` is refreshed with each commit.
- **Source:** [captain brief]; `~/.no-mistakes/config.yaml` (read 2026-10-05); [handoff §8]; [mem: hackathon-working-agreement]. The repo has no CI configuration (there is no `.github/`), so what the CI step checks must be defined.
- **Done looks like:**
  - Every merged change has a PR with a completed no-mistakes run and a clean secret scan.
  - Nothing is pushed directly to `main` after the switch.

#### R-D-05 · Stage acceptance gates, checked by a different worker · DELIVERY
- **Requirement:** each stage has a written "done looks like" (this sheet's checks, or the plan's) and is checked by a worker other than its builder. A failed gate blocks the stages that depend on it.
- **Source:** [captain brief]. Supporting: [slides p5, p8] (nobody checks their own work); "Plan milestones with an owner, concrete output, acceptance check, time budget, and dependency." [brief L366]; independent reviewers for big deliverables [handoff §8].
- **Done looks like:**
  - A gate record exists per stage: the stage, the builder, the checker (not the builder), the checks run, the result and the time.
  - No stage is marked done without one.

#### R-D-06 · Freeze the shared contracts early · DELIVERY
- **Requirement:** "Freeze shared schemas and interfaces early." Every worker uses one evidence contract. The contracts to freeze:
  - the evidence record schema (R-P-02 table A);
  - the assessment schema;
  - the Finding contract (R-P-22);
  - the registry schema (R-P-14);
  - the verdict mapping (R-J-58);
  - the EP adapter interface (R-P-01, R-J-47).
- **Source:** [brief L362, L364]; [SN §6]; [captain direction].
- **Done looks like:**
  - A versioned schema file exists for each contract before parallel building starts.
  - All workers' outputs validate against it.
  - A change goes through a PR that bumps the version.

#### R-D-07 · One control end to end first; milestones · DELIVERY
- **Requirement:**
  - "recommend a small first milestone that completes one control from declared threshold to two-minute query".
  - "Add further controls only after the current one can be demonstrated and exported."
  - Each milestone has an owner, an output, an acceptance check, a time budget and its dependencies.
- **Source:** [brief L360, L366, L368]; [transcript: "Start with one control, finish until you see the evidence"]; [PB §4.2] (the finish-one-first rule).
- **Done looks like:**
  - The plan lists milestones with those five fields.
  - Milestone 1's acceptance is R-J-08 plus R-J-10 for one control.
  - No second control is built before milestone 1's gate passes, or the plan records why.

#### R-D-08 · The time-critical first decisions · DELIVERY
- **Requirement:** decide these, in this order, before the work that depends on them [handoff §3a]:
  1. The IT agent's model (keep nano-9b or revert), before the C9 baseline hours.
  2. Agent changes, before the register freeze and the baseline (or a freeze scoped to agent versions).
  3. Thresholds, dated before the first assessed run.
  4. The lever for the named pass and breach runs.
  5. When to re-snapshot the evidence.
  6. ServiceNow credentials and wiring.
  7. Separation of duties.
- **Source:** [handoff §3a]; [mem: prooflab-project] ("FIRST planning decision").
- **Done looks like:** each decision is recorded, with its time and decider, before its dependent stage starts.

#### R-D-09 · Back up as you go; re-snapshot · DELIVERY
- **Requirement:** back up continuously, because the account is destroyed at the end. Keep the 17:37Z snapshot as a backup, and re-snapshot after the last assessed run.
- **Source:** [kickoff deck p8 via handoff §2.5]; [handoff §3a item 5, §7.6].
- **Done looks like:** a final snapshot with a SHA-256 MANIFEST exists outside the account, taken after the last assessed run.

#### R-D-10 · The working agreement · DELIVERY
- **Requirement:**
  - Read-only by default. Ask before any write to the repo, the cluster, AWS or ServiceNow, including workshop write steps.
  - Never change or delete a resource Claude did not create without asking.
  - The cockpit is GET only.
  - Never print or commit secrets (R-C-10).
  - Add notes items only on the user's "add"; new gaps go into `gap-list.md`.
  - Verify teammate documents against the primary sources before relying on them.
  - For adversarial work, record what was tested, and never write down methods for forging records.
- **Source:** [handoff §8]; [mem: hackathon-working-agreement].
- **Done looks like:**
  - Every write in the live-lane log cites the user's OK.
  - No write falls outside the approved scope.

---

## 5. Open questions that could change requirements

**For the organisers** [handoff §9]:
- Who injects the Hostile and Rogue conditions, and when? (R-J-36, R-J-37)
- What INTEGRITY proof is expected? (R-J-33)
- Is AICT required for L2? (R-J-02, R-P-24)
- Is the one-model-request-per-second rule per agent or per account? (R-C-07)
- Confirm the end time. (R-D-01)
- Can per-agent identities be provisioned? (R-C-03)

**For the user or captain:**
- The Evidence Pack format (R-J-38).
- The IT agent's model (R-C-13, R-D-08).
- Confirm the [captain brief] and [captain direction] wording (R-P, R-D-03 to R-D-05).
- Confirm the meaning of "threshold experiments" (R-P-15).
- Whether "EP-responsible party" names the organisers' platform team for the platform's EPs (R-P-02).

---

## 6. Conflicts and tensions

Requirements that pull against each other. Nothing here is decided beyond the captain's direction: the last column says who has to resolve the rest. T1 to T5 are the top five.

The captain's correction settles part of T1 and T5: one waiting question at most (the optional C16 check), hand-offs as emit-only records, and post-run C16 as the floor. What remains is below.

| # | Tension | Items | Why it bites | Resolves |
|---|---|---|---|---|
| **T1** | **The one waiting question: the inline C16 check** | R-P-18, R-J-18, R-J-48 vs R-J-12, R-J-13, R-C-01, R-C-02, R-C-04 | The captain allows one optional in-path question: C16 before each model call, with a frozen, version-stamped threshold loaded beforehand; post-run is the floor, so R-J-26 holds. But the gateway can't sum per run and takes no team code, so the check must live in our agent code, across three runtimes. "Is this run still under cap?" needs the run's spend shared across those runtimes, in an explicit concurrency-safe component that reserves, then commits. Where that state can live, and how the runtimes would reach it, is not established in our sources (R-C-01, R-C-02). Because the threshold is loaded before the run, a new threshold version means reloading the agents (see T3). The slides' worked example puts C16 at the gateway, which takes no team code here | Plan |
| **T2** | **The captain's full scope against the time left** | R-P-01 to R-P-04 (adapters at every EP, one store for every decision, stitcher), R-P-05 to R-P-09 (app), R-P-10 (guardrails at every EP), R-P-14 to R-P-18 (all three controls), R-P-25 vs R-D-01 (about 18 hours), R-J-07 and R-D-07 (finish one control first) | A half-built control scores 0 on Axis 1. The platform page warns "The hackathon asks you to build a control, not a platform". The brief: "Do not add infrastructure merely to make the design look enterprise-scale" (L249) and "Implement only the transports needed for the chosen scope" (L245) | The user sets the cut order; the plan |
| **T3** | **Agent changes against the dated freeze and the C9 baseline** | R-P-19, R-P-20 vs R-J-21, R-P-14, R-P-17, R-C-09, R-C-07 | Each agent version is a new treatment. The register must be dated before the assessed runs, and the C9 baseline needs closed clock hours with traffic on the frozen configuration, which costs budget. Every deployment needs a human approval, and the IT model decision comes first. If the C16 check is built, its threshold is loaded into the agents before the run, which ties register versions to agent deployments | The user (IT model, order); the plan |
| **T4** | **Every decision with full metadata, against what the platform records** | R-P-02, R-P-03, R-J-22, R-J-29 vs R-C-03, R-C-05, R-C-06, R-C-12, R-C-02 | Platform records carry no agent identity and no hand-off. Admission decisions are invisible (EKS audit is off). Refusals carry no run or action id. PDP and authz logs live only on the pods. The reference agents' ledger trace ids don't match the run. So the actor and admission fields, and the hand-off records the captain asks for (emit only, never blocking), must come from our own agents and live lane (which feeds T3), or stay "unknown" with a gap id. Because records never block, an emit can be lost; it has to be found by reconciliation (brief L237). "One append-only store" also has to be built and exported by us: the platform ledger's token is readable by every participant and it keeps writer-supplied timestamps | Plan |
| **T5** | **The second enforcement point, when nothing but C16 may wait** | R-J-11, R-J-20, R-J-52 vs R-P-01, R-P-21, R-P-23, [SN §3, §10], corr row 12, R-P-12 and R-C-04, R-J-06 | In the captain's design nothing waits on ServiceNow or the human queue. So EP2 can only be claimed as the same contract reached through another transport at another EP kind: the managed gateway or PDP (their own refusals, read by `pull`), or the human queue (a late verdict by `callback` that refuses nothing). But judges test an EP as "Ask · Wait · Act · Record" [slides p12], and a notify-only incident refuses nothing (corr row 12). Moving the C16 `evaluate()` to another model-call site keeps the same EP type. Cedar through a ToolConfig gives a real refusal, but it is the platform's EP, applies to all callers, is stateless, and editing shared tools breaks "clone rather than modify" | Plan; the pitch's wording; the user |
| T6 | The offline app against live lines and the judges | R-P-06, R-P-07 vs R-P-21, R-P-24, R-J-18, R-J-44, R-J-10 | The app may not call ServiceNow, AICT or AWS, yet it must show the human-loop and AICT lines. The inline bonus must be shown live. The judges read S3, not our laptop, and "We type the question". So the app must ship inside the pack and run for a stranger, while the live demos need the account still up during judging | Plan |
| T7 | Threshold experiments against dated thresholds | R-P-15 vs R-J-21, R-J-39 | A value fitted to the results "is a description of what you got, not a test" [slides p10]. The pilots must come before the freeze and stay separate from the assessed runs; the risk framing must not be tuned to the named breach | Plan |
| T8 | The named breach run against the budget | R-J-41 vs R-C-07, R-C-14 | S2's natural C16 breach costs 2.0M tokens, 80% of the hourly ceiling, and blocks the live lane. The twin can't make breaches, and the pass and breach runs need the same threshold. With post-run C16 as the floor, nothing of ours stops an S2-style loop unless the inline check is built (gap 8) | Plan |
| T9 | INTEGRITY is judged; cryptography is out of scope | R-J-33 vs R-J-59, R-C-10 | The ledger has no verify route and a readable token. Only corroboration plus a MANIFEST is possible, and it must be labelled as such | The organisers (what they expect); the plan |
| T10 | "Security at every EP" against where code can run | R-P-10, R-P-01 vs R-C-01 to R-C-05, R-C-18 | Four of the six platform EPs take no team code, so their adapters can only read logs. There is one shared identity, refusals are recorded as ALLOW, and the gateway runs plain HTTP. Many rows can only be gap entries (honesty, R-J-16) | Plan |
| T11 | Coverage of the whole window against named-run focus and test traffic | R-J-28 to R-J-34 vs R-J-41, R-P-25 | The judges pick any incident in the window, including the Hostile and Rogue phases. Adversarial runs pollute the shared ledger and the window unless they are labelled | Plan |
| T12 | The dashboard against "not an EP" and "trawl your logs" | R-P-05, R-P-08 vs R-J-53, R-J-10 | A browsable dashboard invites navigation, but the judged answer must come from one typed question | Plan |
| T13 | PR gates against credentials and the clock | R-D-04 vs R-C-08, R-D-01 | The secret scan fails closed without live AWS credentials. PR runs add time. The repo has no CI configuration | The user; the plan |
| T14 | Two people against four roles and different-worker gates | R-D-02, R-D-05 | The owner also builds. An AI worker can check engineering gates, but it can't be the named assurance person or the owner | The user |
| T15 | A C9 alert per crossing against the shared ServiceNow instance | R-P-17, R-P-21 vs R-C-15 | Every crossing must alert the owner, but one incident per window could flood the shared instance | The plan, with the owner |
| T16 | "Unsafe actions denied" when only C16 may wait | R-J-36, R-J-37 vs R-P-01, R-P-13 | The Hostile level asks us to prove "unsafe actions denied", and the Rogue level "containment". In the captain's design our architecture refuses only through the optional C16 check; everything else records. So denials must come from the platform's own EPs (Cedar forbid rules on our ToolConfigs, guardrails, pauses) and from the agents' own judgment (gather or escalate). Our adapters only record them. Where none of these applies, the gap list must say so | Plan |

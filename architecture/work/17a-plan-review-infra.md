# 17a · Plan review: infrastructure and sequencing

- **Reviewer:** the infrastructure-and-sequencing reviewer (a subagent), 2026-10-06 01:37–02:00 UTC. Read-only; no git, AWS, cluster, ServiceNow or network call; no secret read.
- **Read:** `IMPLEMENTATION-PLAN.md` (all 675 lines); `BUILD-SESSION-PROMPT.md` (all); memory `planning-handoff.md` (all), `workshop-aws-access.md`, `workshop-local-shell.md`, `platform-verified-facts.md` (lines 236–317 + greps); `work/05` (all); `work/06` rows B5–H1 and §4 (spikes S1–S3); `work/13` rows 26, 52; ARCH §3.0, §3.1 EP-0, §5.0 (lines 1229–1231), §9.1 (line 1914), §12.1 spike rows; the kit's `workshop-static/reference-impl/build-agent-image.sh` lines 52–223 (read, not run).
- **Local state checked (Q11, ls / `--version` only):** `tools/prototypes/` absent (T0.7 not done); `prooflab/` holds only `__init__.py`, `servicenow/`, `tests/`; `handoffs/ifabric-handoff-3/REWORDED.md` absent (T0.6 (b) pending); T0.7's sources **still present** under the scratchpad `h3/` (`bundle/{make_bundle.py, shim_analyzer.py, e2e_glue.py, agent_A_analyzer_only.py, stub/}`, `bundletest/{conftest.py, pytest.ini, agent_C_all_modules_loader.py}`, `repro_bugs.py`); `rsvg-convert` (/opt/homebrew/bin), Docker 29.3.1, `/usr/bin/python3` 3.9.6, `/opt/anaconda3/bin/python3.12`, `uv` all present; `.venv-py39` and `.venv-strands312` absent; the existing `workshop-local/.venv` (3.12) already holds strands-agents 1.57.2, bedrock-agentcore 1.24.0, mcp 1.30.0, ADOT 0.21.0, **openai 2.54.0**, httpx 0.28.1, and no pytest; the secret-scan script exists (2,819 B; not read, not run); both local AWS CLIs (2.37.9) list `--if-none-match` for `s3api put-object`.

**Verdict.** The infrastructure facts the plan leans on are verified and correctly cited (one source file per build, the ~24,0xx budget, env patches keep the approval, the ledger proxy/port-forward path, head-object for T1, version listing only from the IDE, Logs Insights only from the laptop), and the spike list is the right one. As a build sequence it is **not sound yet**:
1. **Phase 1's ops-lane rows 6–25 depend on PRs that are neither ★ nor timed**, and whose own "After" chains land them hours after their slots: PR-08 (the script and the budget guard) waits for PR-09; PR-20 (the Phase 1 notify) waits for the Phase 2 PR-19; PR-21 (the Phase 1 pack) waits for the Phase 2 PR-16 (17A-01).
2. **Gate G2 requires minimal J2, but PR-07 is outside the critical chain and labelled "Stage B"** (17A-02).
3. **The AWS credential refresh is scheduled "meanwhile" during P5**, a parallel write during a 300K run (17A-03). Also, the build never names `TARGET=agentcore`, `EXTRA_PIP` or a short-sha tag, so the 24,000 gate can pass a bundle that the kit then refuses (17A-05, 17A-06).

**Counts:** ERROR 4 · GAP 11 · IMPRECISE 5.

**Anchor format.** Every Replace / Insert-after anchor below was checked with `grep -c -F` against `IMPLEMENTATION-PLAN.md` and occurs exactly once. Anchors that contain backticks are wrapped in double backticks with one padding space (`` like `this` ``); the anchor is the text between the padding spaces.

## Findings

### 17A-01 · ERROR · Phase 1's second chain: the ops lane's prerequisite PRs are untimed, not ★, and serialized past their slots
- **Where:** §6 rows PR-08, PR-09, PR-11, PR-12, PR-13, PR-15, PR-20, PR-21, PR-22 (After column; no needed-by time); §3 T3.5, T4.8, T6.5 (Deps); §4.3 row 02:15–03:45; §5.2 rows 6–25.
- **Evidence:**
  - Only PR-00…PR-06 are ★; "The rest launch once PR-01 merges (~02:30)" (plan:568). §4.3 gives the whole non-★ Phase 1 set one row: "02:15–03:45 | The Phase 1 fan-out (§6, tagged Ph1)" (plan:374).
  - Every run's preflight is PR-08's: "The budget guard, in the preflight of every run (`prooflab run`'s preflight, ARCH §7.2…)" (plan:454). Yet PR-08's After column is "PR-01, PR-09" (plan:552), and T3.5's Deps are "T1.1, T1.3" (plan:214). T1.3 (PR-09) is "4–5 h (+2 recheck)" (plan:173).
  - PR-20 is "**Ph1 notify → Ph2**", but its After column is "PR-01, PR-09, PR-19" (plan:564), and PR-19 is "**Ph2**" (plan:563). T6.5's Deps are "G-03, G-04, …" (plan:253), and G-03 is T6.3 (Ph2, plan:251).
  - PR-21 is "**Ph1**", but its After column is "PR-12, PR-13, PR-16" (plan:565), and PR-16 is "**Ph2**" (plan:560). T4.8's Deps are "T4.2, T4.4, T5.3" (plan:230), and T5.3 is Ph2.
  - Efforts from §3 (one worker per PR): PR-08 ≈ 3.75–4.75 h (T3.5 + B-G7); PR-09 4–5 h; PR-11 ≈ 5.5–6.5 h (T1.4–T1.6, T1.9, B-G8); PR-12 6–7.5 h (T4.1 + T4.2); PR-13 6.5–8.5 h (T4.3–T4.5, T4.7, After PR-12); PR-15 5–7 h (After PR-09, PR-13); PR-20 ≈ 5–6.5 h.
  - EP-0 accepts a pin or mode patch only as "a declared EP-setting change on an approved version (a pin or mode patch), with the owner's recorded OK (EP-10)" (ARCH:1231). That record is written by PR-08's `deploy_wrapper.py` (plan:214; ARCH:293).
  - Nothing owns the code that derives `v1` from the pilots: T1.7 says "derive with the frozen rules" (plan:177), but it is an ops-lane task, and no PR's Tasks column lists a derivation tool.
- **Per row: what must be merged and working before the row runs (rows 1–25):**

  | §5.2 rows | Needs, merged and working | Status in §6 |
  |---|---|---|
  | 1–3 (B1, 01:15–01:30) | Nothing: lane commands only (S-1 = `kubectl proxy` + one in-process POST; the probe = `aws s3api`) | OK |
  | 4 (SP-1, 03:00) | The three Cedar texts, reviewed by ~02:45 (plan:199) | Owned by PR-08, which lands after PR-09: unreachable (17A-15) |
  | 5 (CodeBuild ×3, 03:45) | PR-06 + Gate G2 (PR-01…PR-05 and PR-07's minimal J2) | PR-07 missing from the chain (17A-02) |
  | 6 (apply customer, 03:50) | PR-06's generator wrapper; **a pin for the first apply** (the fail-closed start-up demands `IFABRIC_PIN_JSON` + `_SHA256`, plan:211), which comes from PR-11's `pinned.py`; PR-08's `deploy_wrapper.py` (EP-10 records the captain's annotation, 05 AR-07) | PR-08 and PR-11 not ★, no time; the first apply's pin is never named |
  | 7 (S-2, 03:55) | PR-08 core (`--only`, envelope, CID, session id, the preflight); PR-07 in the image (the OC-10 parse); for the assertions, PR-12's `aws_spans`, `runtime_logs`, `aict_invocations`, `agentcore_metrics`, or hand-run lane queries (not stated) | not ★, no time |
  | 8 (S-3, 04:00) | PR-11's `v0-smoke` pin (frozen locally); the patch made through PR-08's deploy wrapper, or EP-0 later declines on the generation bump | not ★, no time |
  | 9–10 (S-4, freeze record, `inv-1`, 04:10–04:25) | PR-06, PR-08; PR-11's `inventory.py` | as above |
  | 11 (`v0-pilot` + T1, 04:27) | PR-11 `freeze.py` / `pinned.py`; T1.6's plan uploaded first | as above |
  | 12–15 (P1, P3, P5, P7) | PR-08 (the trio run, the rolling 1.0M check, ≤ 2 `observe` S2 per hour); PR-12's `aws_spans` + `agentcore_metrics` to fill `experiments.jsonl` | as above |
  | 16 (`v1`, 05:00) | a derive tool (unowned); PR-11; PR-09's `approval.py` for the echo/EP-0 check | derive unowned |
  | 17–22 (N1 … N3, 05:15–05:45) | PR-09 `approval.py` (EP-0 blocks assessed runs, D13) and `c16.py`; PR-12 `aws_spans`; PR-13 store/ingest; PR-08's `--condition` and `register/conditions/prompt-attack.txt`; PR-20's finding builder + `notify` | PR-20 waits on Ph2 PR-19 |
  | 23–24 (N4, N5) | PR-09 `c7.py`; the ledger export (PR-12/PR-13); the `suppress-record` fault in the pin (PR-11); PR-20 | as above |
  | 25 (submit #1, ~06:20) | PR-21, PR-12's T4.2 redaction, PR-15's CLI (G5: `query --control C16 --run <N2>`), PR-13's joins (T5.1 Deps T4.4), PR-22's minimal docs, `sketch.png` | PR-21 waits on Ph2 PR-16 |

- **Why it matters:** read as written, P1 (04:30) cannot start before PR-09 → PR-08 merge (≈ 10:00), and submit #1 moves into Phase 2. This breaks the captain's Phase 1 ("the minimum submission in ~4 h") and the slip rule's 07:00 bound. The two Ph1 → Ph2 dependencies (PR-20 → PR-19, PR-21 → PR-16) are outright errors.
- **Fix (exact):**
  - Anchor: §6, after the ★ paragraph. **Insert after:** `The rest launch once PR-01 merges (~02:30).`
    ```
    **Phase 1's second chain (the ops lane's prerequisites).** The ops lane cannot run §5.2 rows 6–25 on the ★ chain alone. These Phase 1 slices are split out now. Each is its own PR, launched as ★ workers free up (needed-by order, earliest first), coding against ARCH §3.2/§4/§7.2 and rebasing on PR-01. Each Phase 2 remainder keeps the original id:

    | Slice | Phase 1 contents only | Needed by (§5.2 row) |
    |---|---|---|
    | PR-11a | the pin format → `pinned.py` (`IFABRIC_PIN_JSON` + `IFABRIC_PIN_SHA256`); `v0-smoke` frozen locally (it is also the first apply's pin); `freeze.py`; `inventory.py` (`inv-1`) | 03:45 (rows 6, 8, 10) |
    | PR-08a | `run.py` (envelope, CIDs, session ids, one invoke per handoff, `--only`, `--condition`, the §5.1 budget-guard preflight) + `deploy_wrapper.py` (the EP-10 record of every apply, annotation and pin or mode patch) | 03:45 (rows 6–8) |
    | PR-12a | `aws_spans`, `runtime_logs`, `aict_invocations`, `agentcore_metrics`, `ledger_export`, `cr_status` + T4.2's redaction | 03:55 (row 7's assertions) |
    | PR-09a | `approval.py` (EP-0) first, then `c16.py`, then `c7.py` | 04:25 (EP-0), 05:30 (N2), 05:55 (N4) |
    | PR-11b | T1.5's rated `risks.yaml`, T1.6's experiment plan, and a `derive` script (pilot captures → `experiments.jsonl` → proposed values by the frozen rules) | 04:25 (row 11), 05:00 (row 16) |
    | PR-20a | T6.4's required keys + T6.5's `notify` with the bug (a)/(b) guards + T6.10; no G-03 | 05:25 (row 20) |
    | PR-13a | T4.3 (the store or the laptop-store fallback), T4.4's joins, T4.5's CLI list | 06:00 (row 25) |
    | PR-15a | T5.1, the query engine + CLI | 06:00 (row 25) |
    | PR-21a | T4.8's minimal pack (no projector) + `tools/submit_wrapper.sh` | 06:00 (row 25) |
    | PR-22a | the README, gap-list section B, `evidence/named-runs.md`, the `run-ids.txt` test | 06:00 (row 25) |

    Before PR-09a's `approval.py` merges, PR-08a's preflight records EP-0 as "not built" and proceeds; that is allowed because pilots are not assessed (D13). Every pin or mode patch goes through `deploy_wrapper.py`; otherwise EP-0 declines N1 on the generation bump [ARCH §5.0 (c)]. If a slice misses its needed-by time, the lane does that step by hand with the slice's commands and records that, and the slip rule (§4.6) applies.
    ```
  - Anchor: §6 row PR-08, After (this anchor is independent of 17A-15's edit to the Owns cell of the same row). Replace: `| PR-01, PR-09 | Sonnet · medium | one invocation per handoff` With: `` | PR-01 (PR-09a's `approval.py` once merged) | Sonnet · medium | one invocation per handoff ``
  - Anchor: §6 row PR-20, After. Replace: `` `prooflab/humanloop/` (not `invoke.py`) | PR-01, PR-09, PR-19 | `` With: `` `prooflab/humanloop/` (not `invoke.py`) | PR-01, PR-09a (the Ph1 `notify` slice, PR-20a); PR-19 only for the Ph2 analysis | ``
  - Anchor: §6 row PR-21, After. Replace: `` `tools/submit_wrapper.sh` | PR-12, PR-13, PR-16 | `` With: `` `tools/submit_wrapper.sh` | PR-12a, PR-13a (the Ph1 minimal pack, PR-21a); PR-16 only for pack v2 | ``
  - Anchor: §3.3 T3.5, Deps. Replace: `| W3 worker → T4 (W6) worker | T1.1, T1.3 |` With: `` | W3 worker → T4 (W6) worker | T1.1; T1.3's `approval.py` when merged (§6, PR-08a) | ``
  - Anchor: §3.6 T6.5, Deps. Replace: `` | G-03, G-04, `~/.prooflab-snow.env` | `` With: `` | G-04, `~/.prooflab-snow.env` (Ph1 `notify`); G-03 only for the Ph2 analysis | ``
  - Anchor: §3.4 T4.8, Deps. Replace: `| T4.2, T4.4, T5.3 |` With: `| T4.2, T4.4 (the Ph1 minimal pack); T5.3 only for pack v2 |`

### 17A-02 · ERROR · Gate G2 requires minimal J2, but PR-07 is outside the critical chain and says "Stage B"
- **Where:** §7 Gate G2; §6 rows PR-06 (After) and PR-07 (title); §3.3 T3.4 (Deps, Done); §4.2; §6's ★ note and the "Serial" list.
- **Evidence:**
  - G2: "three trio bundles ≤ 24,000 chars each with the MIN rails and minimal J2" (plan:589). §4.2: "**Stage A only** goes into the image: MIN rails, minimal J2 (JSON in the text + the precedence rules; the re-ask may wait)" (plan:358).
  - But PR-07's title is "J2: JSON in the text answer, one re-ask, the precedence rules (bundled at Stage B)" (plan:551). PR-06's After column is "PR-02–PR-05" (plan:550). ★ covers "PR-00 … PR-06" (plan:568). The merge order is "PR-03 + PR-04 + PR-05 → PR-06" (plan:572).
  - T3.4's Deps are "T3.3" (the bundler) and its Done reads "If Stage B slips, Stage A ships and gap 1 stays open" (plan:213).
  - S-2 checks "the JSON-in-text parse (OC-10)" (plan:161).
- **Why it matters:** this is a circular, self-contradictory gate. The bundler is gated on J2, J2 is gated on the bundler, and the J2 PR is launched in the late wave. Either G2 stalls at 03:45, or the trio is frozen without J2 and S-2's OC-10 assertion fails. Gap 1 (the judgment gap) is the project's core claim.
- **Fix (exact):**
  - Anchor: §6 row PR-07. Replace: `| PR-07 | **Ph1** · J2: JSON in the text answer, one re-ask, the precedence rules (bundled at Stage B)` With: `| PR-07 ★ | **Ph1** · J2: JSON in the text answer + the precedence rules (minimal J2, bundled at Stage A, Gate G2); the one re-ask only if ready by G2`
  - Anchor: §6 row PR-06, After. Replace: `` `agents/ifabric-{customer,it,network}/` | PR-02–PR-05 | `` With: `` `agents/ifabric-{customer,it,network}/` | PR-02–PR-05, PR-07 | ``
  - Anchor: §6 ★ note. Replace: `launched first (PR-00 … PR-06)` With: `launched first (PR-00 … PR-07)`
  - Anchor: §6 Serial list. Replace: `PR-03 + PR-04 + PR-05 → PR-06` With: `PR-03 + PR-04 + PR-05 + PR-07 → PR-06`
  - Anchor: §4.2. Replace: `PR-05 MIN rails → PR-06 bundler` With: `PR-05 MIN rails ∥ PR-07 minimal J2 → PR-06 bundler`
  - Anchor: §3.3 T3.4, Deps. Replace: `| W2 worker → T2 worker | T3.3 |` With: `| W2 worker → T2 worker | T1.1 (T3.3 bundles it) |`
  - Anchor: §3.3 T3.4, Done. Replace: `If Stage B slips, Stage A ships and gap 1 stays open` With: `If minimal J2 misses Gate G2, Stage A ships without it, S-2's OC-10 check is skipped and gap 1 stays open (recorded)`

### 17A-03 · ERROR · The AWS credential refresh runs "meanwhile" during P5, a parallel write during a 300K run
- **Where:** §5.2 row 14; §4.3 row 04:25–05:00; §5.1 Hold-2; §8.1 R3; §9 Credentials; §4.4.
- **Evidence:**
  - Row 14: "**P5:** S2, natural, `observe`; **the AWS credential refresh** meanwhile | M + act | 300K | **Hold-2**" (plan:482). §9: "refresh at **~04:45** (Hold-2, during P5" (plan:673). R3: "The refresh in Hold-2 (~04:45, during P5)" (plan:608).
  - §5.1: "**One action at a time, one session** … Live work never runs in parallel" (plan:448). The build prompt says the same: "a single serialized ops lane (never in parallel…)" (BUILD-SESSION-PROMPT:96–97).
  - The refresh rewrites the `hackathon` profile from a pasted `export AWS_...` block (memory `workshop-aws-access.md:12`). The script invokes each handoff as a fresh `aws bedrock-agentcore invoke-agent-runtime` subprocess (plan:214, 251), which reads the credentials file at start.
  - New credentials don't revoke the old ones (memory `platform-verified-facts.md:276`), so an earlier refresh costs nothing.
- **Why it matters:** if a handoff subprocess starts while the profile is half written, it fails. TIMEOUT or error is recorded and never re-invoked (plan:214), so the most expensive Phase 1 run (≤ 300K, the C16 breach-lever pilot) is lost and the tight rolling hour gets tighter. It also breaks the lane's one-action rule.
- **Fix (exact):**
  - Anchor: §5.2 row 14. Replace: `; **the AWS credential refresh** meanwhile | M + act |` With: ` | M |`
  - Anchor: §5.2, new row after row 10. **Insert after:** `| 10 | 1 | 04:25 | B2 | Freeze record: digests, generations, models, runtime versions, rails policy sha256; `inv-1` | R | 0 | pre |`
    ```
    | 10a | 1 | 04:26 | B2 | **The AWS credential refresh**, between runs with nothing live: the captain fetches new credentials; the lane rewrites the `hackathon` profile atomically (temp file + `mv`, mode 600, never printed), then runs `aws sts get-caller-identity` and logs the new expiry (≈ 16:25). If the judging slot ends after that expiry, refresh again before the slot (Hold-4) | W (local profile) + act | 0 | **act (Hold-2)** |
    ```
    (This anchor is row 10 in full; it is unique.)
  - Anchor: §4.3 B3 row. Replace: `**the AWS credential refresh at ~04:45** (expiry 06:29 falls inside Phase 1)` With: `**the AWS credential refresh at ~04:26, before `v0-pilot`, with nothing live** (§5.2 row 10a; expiry 06:29 falls inside Phase 1)`
  - Anchor: §5.1 Hold-2. Replace: `the AWS credential refresh (~04:45).` With: `the AWS credential refresh (~04:26, between runs, §5.2 row 10a).`
  - Anchor: §9 Credentials. Replace: `refresh at **~04:45** (Hold-2, during P5;` With: `refresh at **~04:26** (Hold-2, between runs, never during a run;`
  - Anchor: §8.1 R3. Replace: `The refresh in Hold-2 (~04:45, during P5)` With: `The refresh in Hold-2 (~04:26, between runs, §5.2 row 10a)`
  - Anchor: §4.4. Replace: `Due inside Phase 1, at ~04:45 (Hold-2); backstop alarm 05:45` With: `Due inside Phase 1, at ~04:26 (Hold-2, between runs); backstop alarm 05:45`
  - (The alarm times are changed in 17A-11.)

### 17A-04 · ERROR · Mode and pin switches marked "pre" although the build prompt puts mode switches on the ASK list
- **Where:** §5.2 rows 8, 11 and 18 (Authority); §5.1 Hold-2 and Hold-3 lists.
- **Evidence:**
  - The build prompt's ASK list includes "model changes on existing agents; observe/enforce mode switches; pausing models/tools; Cedar/ToolConfig edits" (BUILD-SESSION-PROMPT:115). On METHOD and the authority table, the build prompt wins (plan header; BUILD-SESSION-PROMPT:8–10).
  - Row 8 (S-3): "patch the pin to `v0-smoke` → one S1 run must halt → patch back … | W + M | 10K | pre" (plan:476). The plan's own SPIKES table gives S-3's approver as "captain" (plan:163), and ARCH gives "The user (the owner's OK recorded, EP-10)" (ARCH:2092).
  - Row 18: "rails `observe` patch → … → rails `enforce` patch … | W + M | 5K | pre" (plan:486).
  - Row 11: "env pin (`observe`, caps = 300K; …) on all three | W (S3, cluster) | 0 | pre" (plan:479). This is a pin/mode patch and an S3 write, which §0 says need the captain's OK (plan:54).
  - Rows 19 and 21, the same kind of switch, are correctly Hold-3 (plan:487, 489).
- **Why it matters:** followed as written, the lane makes three classes of write that the captain's approved method reserves for him. EP-0 also needs "the owner's recorded OK" on each patch (ARCH:1231), so a patch made without it shows up later as an unexplained generation bump.
- **Fix (exact):**
  - Anchor: §5.2 row 8. Replace: `patch back (inside S-2's 10-min wait for the AWS record) | W + M | 10K | pre |` With: `patch back (inside S-2's 10-min wait for the AWS record) | W + M | 10K | **Hold-2** |`
  - Anchor: §5.2 row 11. Replace: `on all three | W (S3, cluster) | 0 | pre |` With: `on all three | W (S3, cluster) | 0 | **Hold-2** |`
  - Anchor: §5.2 row 18. Replace: `` → rails `enforce` patch (leg B in Phase 2) | W + M | 5K | pre | `` With: `` → rails `enforce` patch (leg B in Phase 2) | W + M | 5K | **Hold-3** | ``
  - Anchor: §5.1 Hold-2. Replace: `the three trio approval annotations (the captain's own act, never faked);` With: `` the three trio approval annotations (the captain's own act, never faked); S-3's pin/mode patches (row 8); `v0-pilot`'s `observe` pin and its T1 PUT (row 11); ``
  - Anchor: §5.1 Hold-3. Replace: `` the mode switches for N2 (`observe`) and N3 (`enforce`, the owner's remediation); `` With: `` the mode switches for N2 (`observe`) and N3 (`enforce`, the owner's remediation); ADV-H-01 leg A's rails `observe`/`enforce` patches (row 18); ``

### 17A-05 · GAP · The build invocation is never specified: `TARGET=agentcore`, `AGENT_SRC`, and the `openai` pin through `EXTRA_PIP`
- **Where:** §3.3 T3.3; §5.2 row 5; §3.0 T0.5; §3.6 T6.2.
- **Evidence:**
  - The plan never mentions `EXTRA_PIP`, `TARGET` or `AGENT_SRC` (grep count 0 for each). T0.5 says only "the pinned `openai`" (plan:143), with no version.
  - The kit defaults to `TARGET="${TARGET:-pod}"` (build-agent-image.sh:52), which builds amd64 with `SDK_PIP=""`, i.e. no Strands. Only `agentcore` gives arm64 and `SDK_PIP="strands-agents[openai]==1.57.2 bedrock-agentcore==1.24.0 mcp==1.30.0 boto3==1.43.103 aws-opentelemetry-distro==0.21.0"` plus the `opentelemetry-instrument` entry point (:70–99).
  - `AGENT_SRC` defaults to `/tmp/reference-agent/agent.py` (:57).
  - `EXTRA_PIP` is how "pip requirements your agent imports" reach the image (:110–111, :136–149). `openai` is not in `SDK_PIP` and "floats today: METADATA `openai>=1.68.0,<3.0.0`", so pin it "through `EXTRA_PIP`" (work/05:61, AR-11). The laptop's `workshop-local/.venv` holds openai 2.54.0.
  - The build prompt: "libraries only via EXTRA_PIP" (BUILD-SESSION-PROMPT:71–72).
- **Why it matters:** a wrapper written from the plan alone can build a pod image with no SDK, which goes READY and then dies at the first invoke (the AR-03 late-failure class), or ship whatever `openai` PyPI resolves that day. The latter differs from the version T-C16-01 was tested against (`max_retries=0`, `_get_client`).
- **Fix (exact):**
  - Anchor: §5.2 row 5. Replace: `` `IMAGE_TAG=ifabric-<role>-<git sha>` + `URI_FILE` each `` With: `` `TARGET=agentcore`, `AGENT_SRC=agents/ifabric-<role>/ifabric-<role>.py`, `EXTRA_PIP="openai==2.54.0"`, `IMAGE_TAG=ifabric-<role>-<7-hex git sha>` + `URI_FILE` each ``
  - Anchor: §3.3 T3.3. Replace: `` `IMAGE_TAG=ifabric-<role>-<git sha>`, a per-agent `URI_FILE` `` With: `` `TARGET=agentcore`, `AGENT_SRC=<the bundle>`, `EXTRA_PIP="openai==2.54.0"` (Strands, bedrock-agentcore, mcp, boto3 and ADOT come from the kit's own `SDK_PIP` pins), `IMAGE_TAG=ifabric-<role>-<7-hex git sha>`, a per-agent `URI_FILE` ``
  - Anchor: §3.0 T0.5. Replace: `the pinned `openai`)` With: `` `openai==2.54.0`, the version in `workshop-local/.venv` and the one `EXTRA_PIP` puts in the image) ``
  - Anchor: §3.6 T6.2. Replace: `` `URI_FILE` (never `new-agent.sh`) `` With: `` `URI_FILE` and `TARGET=agentcore` (no `EXTRA_PIP` unless the shim imports beyond the kit's `SDK_PIP`; never `new-agent.sh`) ``

### 17A-06 · GAP · The 24,000-char gate ignores the tag's and `EXTRA_PIP`'s share of the 25,600-char buildspec
- **Where:** §3.0 T0.4 (the size check); §3.3 T3.3; §7 Gate G2; R7.
- **Evidence:**
  - The cap is on the whole buildspec: "CodeBuild caps buildspecOverride at 25600 characters" (build-agent-image.sh:168; check at :197). The image tag appears in it three times (`img = f"{h}/{r}:{t}"`, used in `docker build`, the arch assertion and `docker push`, :174–195).
  - work/13 measured the overhead: "1,572 chars with new-agent's `EXTRA_PIP`, tag `ifabric-assurance-agent` …, giving an AB64 budget of **24,028**. Without `EXTRA_PIP` it is 1,428, giving **24,172**. Each tag character costs 3 chars" (work/13:52).
  - The plan's tag is `IMAGE_TAG=ifabric-<role>-<git sha>` (plan:212, 473), sha length unspecified. With a full 40-hex sha, `ifabric-customer-<sha>` is 57 chars, 34 more than the measured 23. That costs ≈ 102 chars, leaving a budget ≈ 23,926, which is below the gate's 24,000.
- **Why it matters:** a bundle of 23,930–24,000 chars passes `tools/gate.sh` and Gate G2, then fails the kit's FATAL check at row 5 (03:45, on the critical path). R7 already says the bundle is tight with the rails.
- **Fix (exact):**
  - Anchor: §3.0 T0.4. Replace: `bundle size ≤ 24,000 chars per agent;` With: `` bundle size ≤ 24,000 chars per agent AND the kit's own check offline: `DRY_RUN=1 TARGET=agentcore STACK=a-01-eks-cluster ACCT=000000000000 AGENT_SRC=<bundle> IMAGE_TAG=<the real tag> EXTRA_PIP=<the real pins> bash …/workshop-static/reference-impl/build-agent-image.sh` exits 0 (DRY_RUN makes no AWS call); ``
  - (17A-05 already sets the 7-hex short sha in T3.3 and row 5.)

### 17A-07 · GAP · The named fallback `--buildspec-override` adds no room; the real fallback is a two-stage build
- **Where:** §3.0 SPIKES S-0 (Pass/fail); §8.1 R7.
- **Evidence:**
  - S-0: "Over budget → `--buildspec-override` [ARCH §7.1]" (plan:157). R7: "drop P2; `--buildspec-override`" (plan:612).
  - The kit already sends its buildspec that way: `aws codebuild start-build … --buildspec-override "$SPEC"` (build-agent-image.sh:221–223), and the 25,600 cap applies to that override (:168).
  - work/05 AR-03's fallback is "our own buildspec … either carrying several gz+b64 files **under the same cap**, or as two builds where the second is `FROM <repo>@<digest>`. The CodeBuild role can pull and push `a-01-eks-cluster-aws-agent-operator`" (work/05:48). `StartBuild` is allowed with no condition keys (work/05:48–49).
- **Why it matters:** if the bundle is over budget at 03:45, the plan's named fallback buys nothing, and nobody has prepared the variant that does: base image digest → a second build adding a second file. It is an untested AWS write path, so it needs to be written offline and dry-run beforehand.
- **Fix (exact):**
  - Anchor: SPIKES S-0. Replace: `Over budget → `--buildspec-override` [ARCH §7.1]` With: `` Over budget → drop the P2 rails first; then the two-stage build (a first build of the base bundle, then our own buildspec `FROM <repo>@<digest>` adding a second gz+b64 file, each under the 25,600-char cap [05 AR-03]), written and `DRY_RUN`-checked offline by PR-06 before Gate G2 ``
  - Anchor: §8.1 R7. Replace: `drop P2; `--buildspec-override` |` With: `` drop P2; the two-stage `FROM <digest>` build [05 AR-03] (a plain `--buildspec-override` is what the kit already uses: same cap) | ``

### 17A-08 · GAP · The merge gate runs only the 3.9 suite, but Gate G2's suites need the 3.12 Strands venv
- **Where:** §3.0 T0.3 and T0.4; §7 Gate G2; §6 (two test roots).
- **Evidence:**
  - The merge gate runs "the PR's DONE checks + the full test suite (the 3.9 venv's `pytest`)" (plan:141), and `tools/gate.sh` runs "the 3.9 `pytest -q`" (plan:142).
  - G2 needs "T-C16-01, T-DUP-01 and S-G1's seven cases green in the 3.12 venv" (plan:589). The pinned SDKs need Python ≥ 3.10 (work/05:99, AR-29; memory `platform-verified-facts.md:306`).
  - The tests sit in two roots: `tests/…` (PR-01, PR-02, PR-05, PR-07, PR-19; plan:545–563) and `prooflab/tests/` (Arth's 152, PR-00).
- **Why it matters:** on 3.9, the Strands-importing tests either fail collection, blocking every merge, or get silently excluded, so the agent PRs merge without the gate running their decisive tests. Either way G2's evidence is not produced by the gate.
- **Fix (exact):**
  - Anchor: §3.0 T0.4. Replace: `the 3.9 `pytest -q`;` With: `` the 3.9 `pytest -q` over the stdlib suites (`prooflab/tests/`, the tool's tests) and the 3.12 venv's `pytest -q` over the agent-side suites (T-C16-01, T-DUP-01, S-G1, J2, the bundle tests; they carry a `strands` marker the 3.9 run skips); ``
  - Anchor: §3.0 T0.3. Replace: `the full test suite (the 3.9 venv's `pytest`)` With: `` the full test suite (`tools/gate.sh`: the 3.9 stdlib suites + the 3.12 agent-side suites) ``

### 17A-09 · GAP · §6's owned-path prefixes disagree with ARCH §3.0's code layout
- **Where:** §6 Owns column of PR-03, PR-04, PR-05, PR-07, PR-08, PR-12, PR-13 (vs PR-20, which uses `prooflab/adapters/`).
- **Evidence:**
  - §6 uses `adapters/runtime/…` (plan:547–551), `adapters/orchestrator/`, `adapters/platform_ops/` (plan:552), `adapters/collectors/`, `store/redact.py` (plan:556), `store/`, `stitch/` (plan:557), but `prooflab/adapters/human_loop.py` (plan:564).
  - ARCH §3.0, which wins on contracts (plan:14), puts all of them under `prooflab/`: "prooflab/ … adapters/ runtime/ … orchestrator/ … postrun/ … collectors/ … platform_ops/ … store/ … stitch/" (ARCH:275–297). The judge runs `python3 -m prooflab query` from the unzipped pack (plan:72), so `store` and `stitch` must be importable as `prooflab.*`.
  - ARCH's `adapters/postrun/c16_replay.py` (EP-2, ARCH:288) is in no PR's Owns.
- **Why it matters:** workers follow their PR's Owns paths. Top-level `adapters/`, `store/` and `stitch/` packages would not be inside the `prooflab` package that the pack ships, and two layouts would co-exist (`prooflab/adapters/human_loop.py` beside `adapters/`).
- **Fix (exact):**
  - Anchor: §6 intro. **Insert after:** `One worker per PR, each in its own branch + worktree; 10–12 at once; the ops lane is not a PR.`
    ```
     **Paths in the Owns column follow ARCH §3.0:** `adapters/…`, `store/…` and `stitch/…` mean `prooflab/adapters/…`, `prooflab/store/…` and `prooflab/stitch/…` (the judge imports them as `prooflab.*`). EP-2's `prooflab/adapters/postrun/` belongs to PR-09. `tests/<area>/` (repo root) holds only suites that need the 3.12 Strands venv; every stdlib suite goes under `prooflab/tests/<area>/`.
    ```

### 17A-10 · GAP · Unowned paths, package `__init__.py` files, dispatcher verbs, and ops-lane outputs written into PR-11's `register/`
- **Where:** §6 Owns of PR-01, PR-11, PR-22; §3 T3.7, T7.1, T1.9; §5.1 (the lane log).
- **Evidence:**
  - PR-02 owns `prooflab/evaluators/c16_core.py` and merges first, while PR-09 owns `prooflab/evaluators/` (plan:546, 553). Nobody owns `prooflab/evaluators/__init__.py` or the `__init__.py` of `prooflab/adapters/runtime/`, which PR-03, PR-04, PR-05 and PR-07 all write into, or of `prooflab/pack/` (PR-16, PR-21).
  - PR-01 owns `prooflab/__main__.py` and `prooflab/cli.py` (plan:545). Later PRs add verbs (`run`, `registry`, `refresh`, `query`, `tail`, `watch`, `pack`, `console`, `humanloop`, `recheck`; ARCH:298), and R17 says "verbs registered through the contract worker" (plan:622), but that worker's PR merges at ~02:15.
  - T7.1 writes `evidence/adversarial/log.jsonl` + `cases/*.md` (plan:269), but only `evidence/adversarial/corpus/` is owned (PR-05). T1.9 writes `evidence/named-runs.md` and `run-ids.txt` (plan:179); PR-11 owns neither.
  - `reviews/` (`gates.jsonl`, `roles.md`, `link-handcheck.md`, `rehearsal-*.md`), `live-lane-log.jsonl` and `FEATURE-MAP.md` have no owner row.
  - The ops lane writes `register/versions/`, `register/pins/`, `register/experiments/` and `register/inventory/inv-1.yaml` (plan:216; ARCH:311–314), all inside PR-11's `register/` (plan:555), and the plan gives no commit route for lane output.
- **Why it matters:** two PRs creating the same `__init__.py`, or a later PR editing a merged PR's dispatcher, breaks "owned paths that never overlap" (BUILD-SESSION-PROMPT:57). Lane outputs written into a path an open PR owns produce merge conflicts on the frozen register, the one file that must stay byte-identical.
- **Fix (exact):**
  - Anchor: §6 row PR-01, Owns. Replace: `` `prooflab/cli.py`, `tests/conftest.py`, `tests/contract/` | PR-00 | `` With: `` `prooflab/cli.py` (a fixed verb → module table for every ARCH §3.0 verb, each module owned by its PR), every package's `__init__.py`, the root `pytest.ini`, `tests/conftest.py`, `tests/contract/` | PR-00 | ``
  - Anchor: §6 row PR-11, Owns. Replace: `` `register/` (not `conditions/`, `c16_core.sha256`) | PR-01 | `` With: `` `register/` (not `conditions/`, `c16_core.sha256`, nor the lane's outputs `versions/`, `pins/`, `experiments/*.jsonl`, `inventory/`, which the orchestrator commits through the merge gate as "lane" commits) | PR-01 | ``
  - Anchor: §6 row PR-22, Owns. Replace: `` `evidence-templates/`, `gap-list.md` (section B only), `docs/run-of-show.md` | PR-01 | `` With: `` `evidence-templates/`, `gap-list.md` (section B only), `evidence/adversarial/` (not `corpus/`), `evidence/named-runs.md`, `reviews/` templates, `reviews/run-of-show.md`; the orchestrator owns `FEATURE-MAP.md`, `reviews/gates.jsonl`, `live-lane-log.jsonl` and `run-ids.txt` | PR-01 | ``

### 17A-11 · GAP · The captain's alarms are given only in UTC; he is on CDT (UTC−5)
- **Where:** §3.0 T0.8; §4.3 row ~01:10.
- **Evidence:** "alarms at 04:45 (AWS refresh, Hold-2) and 05:45 (backstop)" (plan:146); "alarms 04:45 (AWS refresh, Hold-2) and 05:45 (backstop)" (plan:371). The plan is "UTC throughout" (plan:56). The captain is on US Central time (the review brief).
- **Why it matters:** an alarm set to "04:45" on a phone in CDT rings at 09:45 UTC, three hours after the 06:29:19Z expiry. The secret scan then fails closed, so every merge and live step stops (R3).
- **Fix (exact):**
  - Anchor: §3.0 T0.8. Replace: `alarms at 04:45 (AWS refresh, Hold-2) and 05:45 (backstop)` With: `alarms at 04:20 UTC = 23:20 CDT (AWS refresh, Hold-2, §5.2 row 10a) and 05:45 UTC = 00:45 CDT (backstop), set in the phone's local time`
  - Anchor: §4.3 row ~01:10. Replace: `alarms 04:45 (AWS refresh, Hold-2) and 05:45 (backstop)` With: `alarms 04:20 UTC = 23:20 CDT (AWS refresh, Hold-2) and 05:45 UTC = 00:45 CDT (backstop)`

### 17A-12 · GAP · S-0 has no owner, and its ~01:15 slot needs T0.5 and T0.7, both still undone
- **Where:** §3.0 SPIKES S-0 (Slot, Approver); T0.5; T0.7.
- **Evidence:**
  - S-0's slot is "~01:15 on the reference agent; again ~03:45 on the Stage A bundle" with Approver "— (local)" and no owner (plan:157).
  - It needs the 3.12 venv (T0.5, "installs", not yet created: `.venv-strands312` absent) and the bundler template (T0.7, "lead, now": `tools/prototypes/` absent).
  - The local `docker build` pulls `python:3.12-slim` and the pins from the network (build-agent-image.sh:172), which falls under §0's "package installs" OK (plan:54).
- **Why it matters:** S-0 is the only pre-CodeBuild proof of the single-file image (AR-03's late failure). Without an owner it lands nowhere, and Gate G2's Docker item has no producer before 03:45.
- **Fix (exact):**
  - Anchor: SPIKES S-0. Replace: `| ~01:15 on the reference agent; again ~03:45 on the Stage A bundle | 0 tok, 1–2 h | — (local) |` With: `` | after T0.5 and T0.7 (~02:00) on the reference agent; again ~03:45 on the Stage A bundle | 0 tok, 1–2 h | — (local; run by PR-06's worker; the image pulls are covered by T0.5's install OK) | ``

### 17A-13 · GAP · Gate G4 blocks every assessed run on a human IDE step whose output has no route to the laptop
- **Where:** §7 Gate G4; §3.1 T1.7 (Done); §5.2 row 16.
- **Evidence:**
  - G4 requires "**T1**: `head-object` JSON (VersionId, LastModified, ETag, SHA-256) and the IDE's version listing" (plan:591). T1.7 adds "`v1.versions.json` from the IDE" (plan:177).
  - The participant role gets AccessDenied on `ListObjectVersions`; only the IDE role has `ListBucketVersions` (work/06:74, D1). The version history "needs the IDE role, so a person runs it …, any time before teardown" (work/06:75, D2).
  - T1 dating uses head-object's AWS-set LastModified/VersionId and is fail-safe (ARCH:1914).
- **Why it matters:** at ~05:10 (00:10 CDT) a human must open the browser IDE, run the listing and somehow get the JSON onto the laptop, or N1 cannot start. The listing adds nothing to the date proof at that moment; it only proves no earlier version exists, and it can be taken any time before teardown.
- **Fix (exact):**
  - Anchor: §7 Gate G4. Replace: `and the IDE's version listing;` With: `` (the IDE's version listing follows before submit #1 and never blocks N1: the person at the IDE runs `aws s3api list-object-versions --prefix ifabric/register/ > v.json` and then `aws s3 cp v.json s3://<bucket>/ifabric/register/versions-<UTC>.json`, which the laptop downloads into the pack); ``

### 17A-14 · GAP · "Write-once" is not enforced, although an accidental re-PUT would void every named run's date check
- **Where:** §3.0 SPIKES "the bucket probe"; §5.2 row 16 (and every T1 PUT).
- **Evidence:**
  - "There is no Object Lock, so 'write-once' is a convention … an overwrite or a delete marker can only move LastModified later. Tampering turns the check INDETERMINATE" (ARCH:674; ARCH:1914; work/06:75).
  - The plan's PUTs carry only `--checksum-algorithm SHA256` (plan:156, 484).
  - Both local AWS CLIs (2.37.9) offer `--if-none-match` on `s3api put-object` (checked locally, help text only).
- **Why it matters:** a second `registry freeze` or a re-run of row 16 after N1 rewrites `v1.yaml`. LastModified then moves past N1–N5's first spans, and the T1 check reads INDETERMINATE for every named run, which is unrecoverable by 06:20. A conditional PUT turns that into a harmless 412.
- **Fix (exact):**
  - Anchor: SPIKES, the bucket probe. Replace: `` --checksum-algorithm SHA256`; `head-object --checksum-mode ENABLED` | B1, 01:30 | `` With: `` --checksum-algorithm SHA256`; `head-object --checksum-mode ENABLED`; a second PUT of the same key with `--if-none-match '*'` must fail with 412 (the write-once guard every T1 PUT then uses) | B1, 01:30 | ``
  - Anchor: §5.2 row 16. Replace: `**T1** PUT × 2 + head-object;` With: `` **T1** PUT × 2 (`--if-none-match '*'`, `--checksum-algorithm SHA256`) + head-object; ``

### 17A-15 · GAP · SP-1's Cedar texts are owned by PR-08, which cannot exist by their ~02:45 review deadline
- **Where:** §3.2 row "SP-1 policy texts"; §6 row PR-08 (Owns `policies/cedar/`); §5.2 row 4.
- **Evidence:** "They parse offline … reviewed by the guardrails author by ~02:45 | T3 (W3) worker" (plan:199). PR-08 owns `policies/cedar/` and its After column is "PR-01, PR-09" (plan:552). SP-1 is at 03:00 in Hold-1 (plan:375, 472).
- **Why it matters:** as mapped, SP-1 always slips to Phase 2 by construction, not by choice. Its "before the agents' freeze" property (ARCH:1602, one tool generation for `inv-1` and every pilot) is lost silently.
- **Fix (exact):**
  - Anchor: §6 row PR-08, Owns. Replace: `` `register/conditions/`, `policies/cedar/` `` With: `` `register/conditions/` (SP-1's `policies/cedar/` texts are PR-05's) ``
  - Anchor: §6 row PR-05, Owns. Replace: `` `tests/rails/`, `evidence/adversarial/corpus/` | `` With: `` `tests/rails/`, `evidence/adversarial/corpus/`, `policies/cedar/` (SP-1's three texts, reviewed by PR-05's Opus reviewer by ~02:45) | ``
  - Anchor: §3.2 SP-1 policy texts, owner. Replace: `| T3 (W3) worker → guardrails author | — | 0.5 h |` With: `| PR-05's worker → guardrails author | — | 0.5 h |`

### 17A-16 · IMPRECISE · S-1 and the bucket probe: three different authorities, and "service proxy" doesn't name the client
- **Where:** §3.0 SPIKES S-1 and "the bucket probe" (Approver); §5.2 rows 2–3 (Authority); §0 "Writes needing the captain's OK".
- **Evidence:**
  - SPIKES: S-1 approver "captain"; the bucket probe approver "captain" (plan:155–156). §5.2 rows 2–3: "pre" (plan:470–471). §0: "any cluster, AWS or ServiceNow write" needs the captain's OK (plan:54).
  - work/06 gives "The user" for both (work/06:141–142). The build prompt's PRE-AUTHORIZED list names neither ledger writes nor S3 probes (BUILD-SESSION-PROMPT:108–112).
  - On the client: "`kubectl create --raw` can't set a header, so the client is `kubectl proxy` or `port-forward` plus an in-process HTTP client" (work/06:69).
- **Why it matters:** the lane does not know whether to wait at 01:20. A worker reading "service-proxy POST" may try `kubectl create --raw`, get a false 401 and take the wrong fallback.
- **Fix (exact):**
  - Anchor: SPIKES S-1. Replace: `` Service-proxy POST of `[]` with the token in memory `` With: `` Service-proxy POST of `[]` with the token in memory (through `kubectl proxy --address=127.0.0.1 --port=8001` + an in-process POST; `kubectl create --raw` can't set `X-Audit-Token`) ``
  - Anchor: §0. Replace: `**"Writes needing the captain's OK"** covers: any cluster, AWS or ServiceNow write;` With: `` **"Writes needing the captain's OK"** covers: any cluster, AWS or ServiceNow write that §5.1 does not list as pre-authorized (S-1 and the bucket probe: one OK for block B1, see "Needs the captain"); ``
  - See "Needs the captain" for the Authority cells.

### 17A-17 · IMPRECISE · T0.5 rebuilds a 3.12 venv the laptop already has
- **Where:** §3.0 T0.5.
- **Evidence:**
  - T0.5 creates "a 3.12 venv `…/.venv-strands312` with the exact pins" (plan:143).
  - `workshop-local/.venv` (3.12) already holds strands-agents 1.57.2, bedrock-agentcore 1.24.0, mcp 1.30.0, ADOT 0.21.0, openai 2.54.0 and httpx 0.28.1 (ls of site-packages), but no pytest. Its pins are in `requirements.lock.txt` (memory `workshop-local-shell.md:17, 24`).
- **Why it matters:** a fresh resolve can pick different transitive versions from the stand-in the team has used since Module 8, and it spends install time inside the critical chain.
- **Fix (exact):**
  - Anchor: §3.0 T0.5. Replace: `` a 3.12 venv `…/.venv-strands312` with the exact pins `` With: `` a 3.12 venv `…/.venv-strands312` installed from `workshop-local/requirements.lock.txt` (the exact pins of the working `workshop-local/.venv`) + pytest ``

### 17A-18 · IMPRECISE · Two paths for the run of show
- **Where:** §6 row PR-22 (Owns `docs/run-of-show.md`); §3.8 T8.6 (`reviews/run-of-show.md`).
- **Evidence:** PR-22 owns "`docs/run-of-show.md`" (plan:566); T8.6 says "`reviews/run-of-show.md` with a timed 15-minute run" (plan:286).
- **Fix (exact):** covered by 17A-10's PR-22 replacement, which moves PR-22's path to `reviews/run-of-show.md`.

### 17A-19 · IMPRECISE · "Three images built at once" was verified for x86 builds, not for ARM LARGE ones
- **Where:** §5.2 row 5; §4.2 ("B2 batches: three images built at once").
- **Evidence:** "5 x86 builds ran in parallel at bootstrap with 0 s queued"; the ARM evidence is "3 ARM_CONTAINER / BUILD_GENERAL1_LARGE builds SUCCEEDED in 44–47 s, queued 0 s", which ran at different times (work/05:49, AR-04). The laptop side is safe with per-agent `URI_FILE`: the script keeps the buildspec in variables (build-agent-image.sh:171–196).
- **Why it matters:** if the ARM concurrency quota is 1, the builds queue for ≈ 45 s each, which costs about 2 minutes, not a failure. The lane should read a QUEUED status as normal and not as a hang.
- **Fix (exact):**
  - Anchor: §5.2 row 5. Replace: `` digests recorded | W (AWS) | 0 | pre | `` With: `` digests recorded (ARM concurrency is unverified: a QUEUED build is normal, ≈ 45 s each if serialized) | W (AWS) | 0 | pre | ``

### 17A-20 · IMPRECISE · T0.7's owner ("lead, now") vs PR-00 owning `tools/prototypes/`
- **Where:** §3.0 T0.7; §6 row PR-00.
- **Evidence:**
  - T0.7: "**lead, now** → T6 worker" (plan:145). PR-00 lists T0.7 among its tasks and owns `tools/prototypes/` (plan:544).
  - At ~01:45Z `tools/prototypes/` does not exist, and every source file is still in the scratchpad `h3/`.
- **Why it matters:** if each side waits for the other, the prototypes, the bundler template for PR-06 and PR-19, go when this planning session's scratchpad is cleaned (R15).
- **Fix (exact):**
  - Anchor: §3.0 T0.7. Replace: `**lead, now** → T6 worker` With: `**lead, now, before the fan-out** (PR-00 then owns `tools/prototypes/`) → T6 worker`

## Inconsistencies with BUILD-SESSION-PROMPT.md (report only; nobody edits that file now)
- **"hard cap 24,049"** (BUILD-SESSION-PROMPT:71). The real budget depends on the tag length (3 chars per tag char) and `EXTRA_PIP`: 24,028–24,172 with a 23-char tag (work/13:52), and ≈ 23,926 with a full-sha tag. "24,049" is one point measured with the reference tag (work/05:48). The CI gate should be the kit's own `DRY_RUN=1` length check (17A-06).
- **"libraries only via EXTRA_PIP"** (:72). Strands, bedrock-agentcore, mcp, boto3 and ADOT come from the kit's own `SDK_PIP` when `TARGET=agentcore` (build-agent-image.sh:97). `EXTRA_PIP` adds only what that list lacks (`openai==2.54.0`). The prompt never says `TARGET=agentcore`.
- **The ★ list "PR-00 … PR-06"** (:53–54) leaves out the minimal J2 that the plan's Gate G2 requires (17A-02). The prompt defers to "§6 ★", so marking PR-07 ★ in the plan is enough.
- **AUTHORITY** (:107–121) names neither ledger writes (S-1, EP-5 records), nor S3 probe and T1 PUTs, nor the local credentials-profile rewrite as pre-authorized or ask. The plan fills the gap three different ways (17A-16).
- **The secret scan "also checks the ServiceNow secrets"** (:88). The plan's T6.10 still lists "the ServiceNow values added to the exact-value scan" as a pending Ph1 task (plan:258), and the script's mtime (Oct 5 19:25 local) is unexplained. This is unverified: the script was not read, per the rules.
- **"freeze agents one at a time, customer first"** is quoted by the plan (plan:359), but this prompt says "Deploy + smoke customer first (S-2), then IT + network (S-4); one freeze record (G3)" (:104). The wording is consistent in substance; the plan's quotation is not verbatim.

## Needs the captain (each with a recommended default)
1. **Pre-authorize B1's two harmless writes (S-1's `[]` probe + one labelled record; the bucket probe object)?** These are §5.2 rows 2–3, now at 01:20–01:30 (20:20–20:30 CDT). Default: **yes, one OK for B1**. Then set rows 2–3 Authority to "pre (the captain's B1 OK)" and both SPIKES Approver cells to the same.
2. **When to refresh AWS credentials, given the unknown judging slot (OC-37)?** Default: **once at ~04:26** (between runs, ≈ 16:25 expiry), plus a **second refresh at ~13:30** if the slot ends after 16:25. New credentials don't revoke old ones, so an extra refresh is free.
3. **Split the Phase 1 slices (17A-01) or cut instead?** Default: **split** (PR-08a, PR-09a, PR-11a/b, PR-12a, PR-13a, PR-15a, PR-20a, PR-21a, PR-22a, with the needed-by times). Without the split, Phase 1 cannot meet 07:00 as mapped.

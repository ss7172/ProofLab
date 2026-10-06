# 17 · Plan review: consolidated findings for the build orchestrator

- **From:** the review coordinator (a subagent), 2026-10-06, about 02:25 UTC. Inputs: the three independent reviews, `17a-plan-review-infra.md`, `17b-plan-review-judging.md` and `17c-plan-review-timeline.md` (same folder). Each holds the evidence (file:line quotes) behind the findings summarised here.
- **Under review:** `IMPLEMENTATION-PLAN.md` at sha256 `0a1d6183e6b4cd46b3a5471036c2c499aab04c475ef51e3b3311ff692f9417c1` (675 lines, last modified 01:28Z). `BUILD-SESSION-PROMPT.md` was read at sha256 `e9a31728…` (136 lines, modified 01:34Z).
- **Edits made:** **none.** This review changed no tracked file: `IMPLEMENTATION-PLAN.md` still had the baseline sha256 above at 02:05Z. The only new files are the four `architecture/work/17*.md`. Under the change of ownership, the build orchestrator applies the fixes.
- **Validation:** the full fix set is 140 operations: 33 merged or adjusted here (§5) and 107 reviewer pairs as written. It was applied in order to a scratch copy of the baseline:
  - every anchor occurred exactly once at the moment it was applied;
  - every markdown table row kept its header's column count;
  - the plan grows from 675 to 705 lines (result sha256 `43e58f20182c9463…`).
  - 41 reviewer pairs are superseded by the merged ones (§6).

## 0. How to apply
1. Check the plan's sha256. If it still equals the baseline, run Appendix A's snippet: it applies all 140 operations in order. If any anchor is not unique it writes nothing and exits 1, so the plan is never half-patched; skip the listed ids, or apply by hand. Otherwise apply by hand: §5's merged operations first, then each review's pairs in file order (minus §6's skip list), re-checking each anchor with `grep -c -F` first.
2. Read the diff, then commit (the orchestrator owns git).
3. To take a subset: apply each ERROR cluster F-01…F-07 whole, because their edits touch the same rows. The snippet takes finding ids to skip, e.g. `17C-13 17B-11`.
4. One order dependency: 17A-14 must be applied before 17C-16 (both edit the bucket-probe row). Appendix A already has that order.

## 1. Counts

| Review | ERROR | GAP | IMPRECISE | Total |
|---|---|---|---|---|
| 17a · infrastructure and sequencing | 4 | 11 | 5 | 20 |
| 17b · judging coverage | 4 | 13 | 4 | 21 |
| 17c · timeline and risk | 6 | 4 | 7 | 17 |
| **All three** | **14** | **28** | **16** | **58** |

After merging duplicates: **7 blocking clusters (F-01…F-07) hold all 14 ERRORs**, plus 28 GAPs in 6 themes and the cheap IMPRECISE set. One more GAP comes from this coordinator (C-01). The three reviewers found the same top two issues independently: the unscheduled Phase 1 "second chain", and minimal J2 sitting outside the critical chain.

**The realistic clock (17c).** At 01:45Z nothing had started (no `FEATURE-MAP.md`, no worktree, no ops lane, no `caffeinate`). Measured from the ★-chain launch t0:
- Stage A (G2) ≈ t0 + 4–4.5 h at AI pace, about 6 h by §3's own Effort column, and t0 + 2.75 h in the optimistic case.
- With t0 ≈ 03:00, 17c projects Stage A ~07:15, agents frozen ~08:30, `v1` ~09:30 and submit #1 ~11:00 (each ± 45–60 min).
- Each is ≈ 45 min earlier if the chain launches at once.

## 2. Blocking findings (ERROR), ranked

### F-01 · The clock: no late-start rule, and Stage A can't be t0 + 2.75 h (17C-01, 17C-02, 17C-05)
- **Problem:**
  - Every Phase 1 time (§4.3, §5.2 rows 1–25, the holds, G1–G5) assumes a start at 01:00, and the slip rule reacts only to Stage A.
  - "≤ 2.75 h to Stage A" contradicts §3's Effort column and the serial merge gates (PR-00 → PR-01 → PR-02 → PR-03/04/05 (+07) → PR-06; panels for PR-01/PR-02; Opus reviewers for PR-05/PR-06).
  - Slip rule 1's "07:00 with at least the C16 floor" is impossible once G2 passes ~04:40: G2 → N2's notify takes 1 h 52 min in §5.2.
- **Fix:**
  - **M1-a** (§5): rule 0, "re-anchor at t0, then at each gate". The refresh, the hard bounds and the 07:00 safety submit never move.
  - **17C-01**'s G1 "Blocks" pair, as written.
  - **17C-02**'s four pairs (§4.2 realistic chain, the §4.3 header offsets, §4.1, R1), as written. These include splitting PR-05's offline gates (S-G1, S-G2) onto a second worker, as `guardrails/PLAN.md` §0 asks.
  - **17C-05**'s two pairs (a curated safety submit at 07:00 if the C16 floor isn't there; submit #2 merges into the final if submit #1 lands after 10:00), as written. The curated submit is a captain item (§9).

### F-02 · Phase 1's "second chain": the ops lane's prerequisite PRs are untimed, and two Phase 1 PRs wait on Phase 2 PRs (17A-01, 17C-03, 17B-04)
- **Problem:**
  - Only PR-00…PR-06 are ★, and "the rest launch once PR-01 merges".
  - The lane needs these merged by specific §5.2 rows: PR-08 (the script + the budget-guard preflight), PR-11 (pins, freeze), PR-12 (collectors for S-2's assertions), PR-09 (EP-0, c16, c7), PR-20 (`notify`), PR-13/PR-15/PR-21/PR-22 (the pack and CLI).
  - None of them is timed, and the derive script for `v1` is owned by no PR.
  - PR-20 (Ph1 `notify`) waits on PR-19 (Ph2), and PR-21 (Ph1 pack) waits on PR-16 (Ph2). Read literally, `notify` and submit #1 slide into Phase 2.
- **Fix:**
  - **M2-a…d** (§5): "After is the merge order, not the start". A Phase 1 slice table (PR-11a, PR-08a, PR-12a, PR-11b, PR-09a, PR-23, PR-20a, PR-13a, PR-15a, PR-21a, PR-22a), each with the §5.2 row it gates. The EP-0 "not built" rule for unassessed runs only. A by-hand fallback for a late slice. The PR-20, PR-21 and T4.8 dependency cells.
  - **17A-01**'s PR-08, T3.5 and T6.5 pairs and **17C-03**'s §4.3 row pair, as written.

### F-03 · Gate G2 requires minimal J2, but T3.4/PR-07 say "Stage B", PR-07 isn't ★, and PR-06 doesn't wait for it (17A-02, 17B-01, 17C-06)
- **Problem:** the gate is circular. Either G2 stalls, or the agents freeze at G3 without J2, and the judgment gap (pillar 1, the captain's core claim) stays open for the whole event. The build prompt's Phase 1 says "minimal judgment rules: S2 gather-evidence, S3 escalate".
- **Fix:** **M3-a…h** (§5):
  - PR-07 ★, in PR-06's "After" and in the serial merge order;
  - §4.2's chain;
  - T3.4's phase tag, Deps and Done. If minimal J2 misses G2's hard bound, Stage A ships without it, S-2's OC-10 check is skipped, gap 1 is stated in the README's pillars table, and Hold-2 tells the captain.

### F-04 · The AWS credential refresh: during a 300K run, tied to Hold-2 and the slip rule, alarms in UTC for a CDT captain (17A-03, 17C-04, 17A-11)
- **Problem:**
  - Row 14 does the refresh "meanwhile" during P5, which breaks the one-action lane: a half-written profile kills a handoff subprocess, and the run is never re-invoked.
  - Hold-2 and the slip rule move the refresh. With any slip of ~1 h 45 min it lands after 06:29:19. Then the secret scan fails closed and every merge stops too.
  - Alarms written as "04:45" ring at 09:45 UTC on a CDT phone.
- **Fix:** **M4-a…m** (§5):
  - The refresh becomes its own §5.2 row 4a, fixed to the clock at **03:30–04:15 UTC (22:30–23:15 CDT)**, between runs, with an atomic profile rewrite (temp file + `mv`, mode 600) and `sts get-caller-identity`. Never before 03:00 (the new 12 h expiry must cover 15:00). A second refresh before the judging slot if the slot ends after the new expiry.
  - The Hold-2, §4.3, §4.4, R3, §9, T0.8 and alarm cells follow.
  - **Why 03:30–04:15, and not 17a's 04:26 or 17c's 03:15–04:00:** 03:30–06:29 is the captain's own window in memory (`planning-handoff.md`, deadlines). Its early end keeps any slip or sleep from carrying the refresh past 06:29, and the captain is surely awake then (before 17c's sleep window).

### F-05 · The second enforcement point has no builder: EP-2's `adapters/postrun/c16_replay.py` has no task and no PR (17B-02)
- **Problem:** "Would it survive a second enforcement point?" and the second-EP bonus rest on EP-2 `decision` records carrying the same `evaluator.sha256` as EP-1's, produced by their own PR (the I-21 diff proof). With no owner, it is either never built or folded into the pure tester, which is 04's defect E-02 again. G5 could then pass on the tester alone.
- **Fix:** **M6-a…e** (§5):
  - New task T4.9 and new **PR-23**. 17b called it "PR-12b"; it is renamed so it can't be read as a slice of PR-12 in F-02's table.
  - It is needed by §5.2 row 20 (N2's assessment).
  - G5's wording changes; the §0 legend and 17a's paths note (17A-09) point at PR-23.

### F-06 · Phase 1 deliverables wait on the Phase 2 gate, and the Phase 1 pack list leaves out the tool, the alert evidence and the window (17B-03)
- **Problem:**
  - T8.4 (deliverable 4, `run-ids.txt`) and T7.6 (the honest failure) depend on Gate G6.
  - §4.3's minimal pack list leaves out `prooflab/`, the findings, `servicenow/delivery-log.jsonl`, `window.json`, `named-runs.md`, the adversarial log, `inv-1` and the WORKDIR copies.
  - If Phases 2–3 slip, submit #1 is the scored one.
- **Fix:** **17B-03**'s three pairs, as written.

### F-07 · Mode and pin patches marked "pre", though the build prompt's ASK list has "observe/enforce mode switches" (17A-04)
- **Problem:** §5.2 rows 8 (S-3's pin patch), 11 (the `v0-pilot` `observe` pin and its T1 PUT) and 18 (ADV-H-01's rails patches) are "pre". On authority, the build prompt wins. EP-0 also needs the owner's recorded OK on each patch (ARCH §5.0).
- **Fix:** **17A-04**'s pairs as written (rows 8, 11 and 18; the Hold-2 list), except Hold-3. Hold-3 is **M5-a** (§5), which merges 17A-04's and 17C-07's edits of the same sentence: `v1`'s values, the IDE version listing that never blocks N1, the mode switches and ADV-H-01's rails patches.

## 3. GAPs, by theme (apply as written unless noted)
- **G-1 · The phase exits don't test the hand-in (judging).**
  - **17B-05:** G5 and G6 tick the six deliverables on the downloaded zip.
  - **17B-06:** G5 runs the C7 query, one `--window` query per complete control, and the negative answers (unknown CID; C9 → exit 2). T5.1's Done also changes.
  - **17B-07:** the date check over every assessed CID.
  - **17B-08:** L1 from the pack alone.
  - **17B-09:** the owner alert to the named owner, in the pack.
  - **17B-10:** closure only by a linked re-test; the Phase 2 re-test link note (T6.5, row 28).
  - **17B-11:** pillar 1 on record (J2 fields; `score-run.py` on N3, or gap 1 stated).
  - **17B-12:** the README's pillars table, the six questions marked FULL or PARTIAL per submit, the honest failure, the adapter-diff note.
  - **17B-15:** C9 at submit #1 = its threshold in `v1` + an honest "not assessed" answer.
  - **17B-16:** read the pod-only PDP and gateway logs before submit #1.
  - **Coordinator note:** these add checks rather than build work (T4.9 aside), but G5's cell becomes long. Under the build prompt's "prefer speed" rule, let any G5 item fail into a README gap row rather than hold submit #1, except these: the six-deliverable tick, the exact-value scan, the C16/C7 verdicts and the date check.
- **G-2 · The build invocation and the image budget (infra).**
  - **17A-05:** `TARGET=agentcore`, `AGENT_SRC=<bundle>`, `EXTRA_PIP="openai==2.54.0"`, a 7-hex tag. The kit's own `SDK_PIP` brings Strands, bedrock-agentcore, mcp, boto3 and ADOT.
  - **17A-06:** the CI size gate also runs the kit's `DRY_RUN=1` length check, because the tag and `EXTRA_PIP` share the 25,600-char buildspec.
  - **17A-07:** the real over-budget fallback is a two-stage `FROM <digest>` build, not `--buildspec-override` (the kit already uses that).
  - **17A-08:** the merge gate also runs the 3.12 agent-side suites.
  - **17A-12:** S-0 gets an owner (PR-06's worker) and a slot after T0.5 and T0.7.
- **G-3 · Ownership and paths.**
  - **17A-09:** owned paths follow ARCH §3.0 (`prooflab/adapters/…`, `prooflab/store/…`, `prooflab/stitch/…`). Applied through M6-d, which points EP-2 at PR-23.
  - **17A-10:** PR-01 owns every `__init__.py`, the verb table and `pytest.ini`. The lane's outputs under `register/` are committed by the orchestrator as "lane" commits. PR-22 owns `evidence/adversarial/` (not `corpus/`), `named-runs.md` and `reviews/` templates. The orchestrator owns `FEATURE-MAP.md`, `gates.jsonl`, `live-lane-log.jsonl` and `run-ids.txt`.
  - **17A-15:** SP-1's three Cedar texts move from PR-08 (late) to PR-05, so the 02:45 review is reachable. Or give them to their own small Sonnet PR in the ★ wave if PR-05 is loaded.
- **G-4 · T1 on S3.**
  - **17A-13:** the IDE version listing never blocks N1; it follows before submit #1.
  - **17A-14:** every T1 PUT uses `--if-none-match '*'`, tested in the bucket probe. An accidental re-PUT then fails with 412 instead of moving LastModified past the named runs.
- **G-5 · People and single points of failure.**
  - **17C-07:** awake windows, a safe sleep window, a 20-min hold timeout with defaults, and the acts that sat in no hold (risk ratings, registry values, the IDE listing, the T2 notes). Its Hold-3 pair is merged into M5-a.
  - **17C-08:** Arth's time zone and hours, his checks moved off his unconfirmed hours, an "away after 30 min" trigger.
  - **17C-09:** R20–R22 (the orchestrator's context, the ops-lane session, laptop sleep), R15 (the prototypes), R8 (switch to the laptop store if ledger POSTs fail twice).
  - **17C-10:** who applies the cut order and on which trigger; what "hard 04:15" changes.
- **G-6 · Labels and logs written before the runs.**
  - **17B-13:** each run's Alert phase goes into the run index before it runs.
  - **17B-14:** the adversarial-log rows for N3 (ADV-R-05) and N4 (ADV-R-10) are written in Phase 1, before those runs.
  - **17B-17:** an executable check that PACK mode refuses SYNTHETIC data.
- **C-01 (coordinator) · GAP · The build prompt's "a TEST log before the first real one" has no step.** The build prompt's ops lane says "ServiceNow writes: selftest before each notify batch, a TEST log before the first real one" (`BUILD-SESSION-PROMPT.md`:105). In this repo a TEST log means a scratch delivery log for dry runs (work/13 D3; ARCH §15 bug (a)). §5.2 row 20 goes straight to the first production `notify`. **Fix: C1-a** (§5): a dry-run rehearsal of N2's `notify` against a TEST log under `evidence/servicenow/wiring-tests/` (guard (a)), then the real `notify`. It writes nothing to ServiceNow and costs about a minute.

## 4. IMPRECISE (cheap; apply as written)
- **17A:**
  - 17A-16: S-1's client is `kubectl proxy` + an in-process POST, since `create --raw` can't set the header; §0 changes too.
  - 17A-17: build the 3.12 venv from `workshop-local/requirements.lock.txt`.
  - 17A-18: covered by 17A-10.
  - 17A-19: ARM build concurrency is unverified, so a QUEUED build is normal.
  - 17A-20: T0.7 is the lead's job now, and PR-00 then owns `tools/prototypes/`.
- **17B:**
  - 17B-19: T1.7's T2 export moves to Phase 2 by default.
  - 17B-20: G7's Must rehearsal can't be replaced by a gap row; T8.7's dependency is circular.
  - 17B-21: §4.6 separates L1 (Phase 1) from L2 → L3 (Phase 2).
  - 17B-18 is superseded by 17C-15's T8.9 pair.
- **17C:**
  - 17C-11: the P7 branch puts submit #1 at ~06:50.
  - 17C-12: the tightest rolling hour is 965K, not ≈ 900K.
  - 17C-13: RTM-2 paced at 0.4 req/s, since 0.5 = exactly 30/min.
  - 17C-14: priority labels P0–P5 vs pilots P1–P8.
  - 17C-15: inconsistent times (PR-01 02:15 vs 02:30; PR-00 01:45; T8.9; Arth's T2 time; stale build-prompt quotes). Its §4.1 pair is adjusted in M4-m.
  - 17C-16: one B1 OK for S-1 + the bucket probe.
  - 17C-17: T1.8's baseline runs and tokens vs §5.2.

## 5. Merged and adjusted fix text (exact; 33 operations, applied first)
The exact strings, including leading and trailing spaces, are also in Appendix A. "Insert after" puts the text right after the anchor. A text that starts on a new line says so.

**M1-a** · F-01 · insert after

Anchor:
````text
**Slip rule:**
````

Text (starts on a new line):
````text
0. **Re-anchor at the start, then at each gate.** t0 = the time the orchestrator launches the ★ chain (planned 01:00; not launched at 01:45). At launch it writes t0 into the STATUS line and moves every Phase 1 time in §4.3, §5.2 rows 1–25, the holds and Gates G1–G5 by (t0 − 01:00). Three things never move: the AWS credential refresh (§5.2 row 4a, fixed to the clock), the hard bounds (rule 4) and the 07:00 safety submit (rule 1). At each gate it re-projects submit #1 as G2 + 2 h 35 min (+ 20 min if P7 runs, + the hold latency) and reports it. The ops lane opens at t0 and runs B1 at once; it doesn't wait for the orchestrator.
````

**M2-a** · F-02 · insert after

Anchor:
````text
The rest launch once PR-01 merges (~02:30).
````

Text (starts on a new line):
````text
**"After" is the merge order, not the start.** Every Phase 1 PR launches as soon as a worker is free (★ first, then the slices below in needed-by order), codes against PR-01 and the ARCH text (§3.2, §4, §7.2) and rebases as PR-01 merges. The orchestrator merges every Phase 1 PR before any Phase 2 PR.

**Phase 1's second chain (the ops lane's prerequisites).** The ops lane can't run §5.2 rows 6–25 on the ★ chain alone. These Phase 1 slices are split out now, each its own PR; the Phase 2 remainder keeps the original id. A late slice holds only its row:

| Slice | Phase 1 contents only | Needed by (§5.2 row; planned UTC before re-anchoring) |
|---|---|---|
| PR-11a | the pin format → `pinned.py` (`IFABRIC_PIN_JSON` + `IFABRIC_PIN_SHA256`); `v0-smoke` frozen locally (also the first apply's pin); `freeze.py`; `inventory.py` (`inv-1`) | row 6 (03:50) |
| PR-08a | `run.py` (envelope, CIDs, session ids, one invoke per handoff, `--only`, `--condition`, the §5.1 budget-guard preflight) + `deploy_wrapper.py` (the EP-10 record of every apply, annotation and pin or mode patch) | row 6 (03:50) |
| PR-12a | `aws_spans`, `runtime_logs`, `aict_invocations`, `agentcore_metrics`, `ledger_export`, `cr_status` + T4.2's redaction | row 7 (03:55; S-2's assertions) |
| PR-11b | T1.5's rated `risks.yaml`, T1.6's experiment plan, and a `derive` script (pilot captures → `experiments.jsonl` → proposed values by the frozen rules) | row 11 (04:27); `derive` by row 16 (05:00) |
| PR-09a | `approval.py` (EP-0) first, then `c16.py`, then `c7.py` | `approval.py` by row 16 (05:00); `c16.py` by row 20 (05:27); `c7.py` by row 23 (05:50) |
| PR-23 | T4.9, EP-2's post-run replay of the c16 core (the second EP) | row 20 (05:27; N2's assessment) |
| PR-20a | T6.4's required keys + T6.5's `notify` with the bug (a)/(b) guards + T6.10; no G-03 | row 20 (05:27) |
| PR-13a | T4.3 (the store or the laptop-store fallback), T4.4's joins, T4.5's CLI list | row 25 (~06:00) |
| PR-15a | T5.1, the query engine + CLI | row 25 (~06:00) |
| PR-21a | T4.8's minimal pack (no projector) + `tools/submit_wrapper.sh` | row 25 (~06:00) |
| PR-22a | the adversarial-log rows written before their runs (ADV-H-01 leg A, N3 = ADV-R-05, N4 = ADV-R-10); the README, gap-list section B, `evidence/named-runs.md`, the `run-ids.txt` test | row 18 (05:22) for the log rows; row 25 (~06:00) for the rest |

Before PR-09a's `approval.py` merges, PR-08a's preflight records EP-0 as "not built" and proceeds; that is allowed only for unassessed runs (smokes and pilots, D13). Every pin or mode patch goes through `deploy_wrapper.py`; otherwise EP-0 declines N1 on the generation bump [ARCH §5.0 (c)]. If a slice misses its row, the lane does that step by hand with the slice's commands and records it, and the slip rule (§4.6) applies.
````

**M2-b** · F-02 · replace

Anchor (starts with a space; ends with a space):
````text
 `prooflab/humanloop/` (not `invoke.py`) | PR-01, PR-09, PR-19 | 
````

With (starts with a space; ends with a space):
````text
 `prooflab/humanloop/` (not `invoke.py`) | PR-01, PR-09a (PR-20a, the Ph1 `notify`); + PR-19 for the Ph2 remainder (the analysis) | 
````

**M2-c** · F-02 · replace

Anchor (starts with a space; ends with a space):
````text
 `tools/submit_wrapper.sh` | PR-12, PR-13, PR-16 | 
````

With (starts with a space; ends with a space):
````text
 `tools/submit_wrapper.sh` | PR-12a, PR-13a (PR-21a, the Ph1 minimal pack); + PR-16 for the Ph2 remainder (pack v2) | 
````

**M2-d** · F-02 · replace

Anchor:
````text
| W6 worker → Arth | T4.2, T4.4, T5.3 |
````

With:
````text
| W6 worker → Arth | T4.2, T4.4 (the Ph1 minimal pack); T5.3 only from pack v2 (submit #2) |
````

**M3-a** · F-03 · replace

Anchor:
````text
| PR-07 | **Ph1** · J2: JSON in the text answer, one re-ask, the precedence rules (bundled at Stage B) |
````

With:
````text
| PR-07 ★ | **Ph1** · J2: JSON in the text answer + the precedence rules (minimal J2, in the Stage A image, Gate G2); the one re-ask only if ready by G2, else Stage B |
````

**M3-b** · F-03 · replace

Anchor (starts with a space; ends with a space):
````text
 `agents/ifabric-{customer,it,network}/` | PR-02–PR-05 | 
````

With (starts with a space; ends with a space):
````text
 `agents/ifabric-{customer,it,network}/` | PR-02–PR-05, PR-07 (minimal J2) | 
````

**M3-c** · F-03 · replace

Anchor:
````text
launched first (PR-00 … PR-06)
````

With:
````text
launched first (PR-00 … PR-07)
````

**M3-d** · F-03 · replace

Anchor:
````text
the critical chain's merge order: PR-01 → PR-02 → PR-03 + PR-04 + PR-05 → PR-06;
````

With:
````text
the critical chain's merge order: PR-01 → PR-02 → PR-03 + PR-04 + PR-05 + PR-07 → PR-06;
````

**M3-e** · F-03 · replace

Anchor:
````text
PR-05 MIN rails → PR-06 bundler
````

With:
````text
PR-05 MIN rails ∥ PR-07 minimal J2 → PR-06 bundler
````

**M3-f** · F-03 · replace

Anchor:
````text
**Ph1 (minimal)** · **J2 (Stage B):**
````

With:
````text
**Ph1 (minimal, in Stage A)** · **J2 (minimal in Stage A: JSON in the text + the precedence rules; the re-ask may wait):**
````

**M3-g** · F-03 · replace

Anchor:
````text
| W2 worker → T2 worker | T3.3 | 1.5–2 h |
````

With:
````text
| W2 worker → T2 worker | T1.1 (bundled by T3.3) | 1.5–2 h |
````

**M3-h** · F-03 · replace

Anchor:
````text
If Stage B slips, Stage A ships and gap 1 stays open
````

With:
````text
If minimal J2 is not green by Gate G2's hard bound (§4.6), Stage A ships without it, S-2's OC-10 check is skipped, and gap 1 stays open for the whole event (the agents freeze at Gate G3); the gap list and the README's pillars table say so, and Hold-2 tells the captain
````

**M4-a** · F-04 · insert after

Anchor:
````text
| W (shared ToolConfig) + 3 MCP calls | 0 | **Hold-1** |
````

Text (starts on a new line):
````text
| 4a | 1 | 03:30–04:15 (fixed to the clock: never re-anchored, never moved with Hold-2) | — | **The AWS credential refresh**, between runs with nothing live: the captain fetches new credentials at the Workshop Studio console; the lane rewrites the `hackathon` profile atomically (temp file + `mv`, mode 600, never printed), runs `aws sts get-caller-identity` and logs the new expiry (refresh + 12 h, ≥ 15:30). Never before 03:00 (the new expiry would fall before 15:00). If the judging slot ends after the new expiry, a second refresh before the slot (Phase 3) | W (local profile) + act | 0 | **act** (its own alarm, 03:30) |
````

**M4-b** · F-04 · insert after

Anchor:
````text
| captain → ops lane | both PDP replicas + `/modaas/evidence`; CR still Approved |
````

Text (starts on a new line):
````text
| 03:30–04:15 (fixed) | **The AWS credential refresh** (§5.2 row 4a), between runs, never during one; the new expiry logged | captain + ops lane | `sts get-caller-identity`; new expiry ≥ 15:30 |
````

**M4-c** · F-04 · replace

Anchor:
````text
P5 (> 150K) and P7 if needed; the AWS credential refresh (~04:45).
````

With:
````text
P5 (> 150K) and P7 if needed. (The AWS credential refresh is not in this hold: it is fixed to the clock, 03:30–04:15, §5.2 row 4a, and asked for on its own at its alarm.)
````

**M4-d** · F-04 · replace

Anchor:
````text
(the approval annotations, the pilots' S2 run, the AWS refresh)
````

With:
````text
(the approval annotations, S-3's pin patches, the pilots' S2 run)
````

**M4-e** · F-04 · replace

Anchor:
````text
**the AWS credential refresh at ~04:45** (expiry 06:29 falls inside Phase 1)
````

With:
````text
(the AWS credential refresh is already done: §5.2 row 4a, 03:30–04:15)
````

**M4-f** · F-04 · replace

Anchor:
````text
| experiments log; new expiry ≥ 16:45 |
````

With:
````text
| experiments log |
````

**M4-g** · F-04 · replace

Anchor:
````text
; **the AWS credential refresh** meanwhile | M + act |
````

With (starts with a space):
````text
 | M |
````

**M4-h** · F-04 · replace

Anchor:
````text
refresh at **~04:45** (Hold-2, during P5;
````

With:
````text
refresh at **03:30–04:15, fixed to the clock** (§5.2 row 4a; between runs, never during one;
````

**M4-i** · F-04 · replace

Anchor:
````text
The refresh in Hold-2 (~04:45, during P5)
````

With:
````text
The refresh fixed to the clock at 03:30–04:15 (§5.2 row 4a; between runs; never moved by the slip rule)
````

**M4-j** · F-04 · replace

Anchor:
````text
Due inside Phase 1, at ~04:45 (Hold-2); backstop alarm 05:45 | 04:25–05:00 row |
````

With:
````text
Fixed to the clock at 03:30–04:15 (§5.2 row 4a), between runs; backstop alarm 05:45 | §4.3's 03:30–04:15 row |
````

**M4-k** · F-04 · replace

Anchor:
````text
alarms at 04:45 (AWS refresh, Hold-2) and 05:45 (backstop)
````

With:
````text
alarms at 03:30 UTC = 22:30 CDT (the AWS refresh, §5.2 row 4a) and 05:45 UTC = 00:45 CDT (backstop: refresh at once if row 4a was missed), set in the phone's local time
````

**M4-l** · F-04 · replace

Anchor:
````text
alarms 04:45 (AWS refresh, Hold-2) and 05:45 (backstop)
````

With:
````text
alarms 03:30 UTC = 22:30 CDT (the AWS refresh, §5.2 row 4a) and 05:45 UTC = 00:45 CDT (backstop)
````

**M4-m** · F-04 · replace

Anchor:
````text
which predates the phases (by that prompt's own rule, on timings this plan wins; the refresh moves to ~04:45 inside Phase 1)
````

With:
````text
in an earlier version of that prompt (the current one defers slot times to §4.3 and §4.6; its "refresh in Hold-2, ~04:45" is superseded by §5.2 row 4a)
````

**M5-a** · F-07 · replace

Anchor:
````text
`v1`'s APPROVED values; the mode switches for N2 (`observe`) and N3 (`enforce`, the owner's remediation);
````

With:
````text
`v1`'s APPROVED values and the IDE version listing for T1 (before submit #1; it never blocks N1, Gate G4); the mode switches for N2 (`observe`) and N3 (`enforce`, the owner's remediation); ADV-H-01 leg A's rails `observe`/`enforce` patches (row 18);
````

**M6-a** · F-05 · insert after

Anchor (starts with a space):
````text
 2–3 h | S3 (at each submit; pre-authorized) | 0 |
````

Text (starts on a new line):
````text
| T4.9 | **Ph1** · **EP-2, the second placement of the c16 core** (`adapters/postrun/c16_replay.py`; ARCH §3.1, §11.1): after each run, the run's model-call spans from `aws/spans` in gateway order; per call one `C16Question` (committed = the earlier calls' actual tokens, reserved = 0, bound = this call's actual tokens, `bound_basis: actual`) through the **same** `c16_core.decide_inline` with the run's pin; each result a `decision` record (`ep.id: EP-2`, `ep.transport: pull`, the core's `evaluator.sha256`), recorded, never executed. Its own PR (PR-23), so its `git diff --stat` shows adapter files only (the I-21 proof) | For N2 and N3, one EP-2 decision per model-call span, each with the same `evaluator.sha256` as EP-1's decisions; `c16.py`'s reconciliation lists every EP-1/EP-2 difference; the PR touches only `adapters/postrun/` | PR-23 worker → PR-09's reviewer | T1.2, T4.1 | 1 h | — | 0 |
````

**M6-b** · F-05 · insert after

Anchor:
````text
no claim beyond the evidence; the six deliverables |
````

Text (starts on a new line):
````text
| PR-23 | **Ph1** · EP-2: the post-run replay of the c16 core (the second EP) | T4.9 | `adapters/postrun/` | PR-02, PR-12a | Sonnet · medium | the same `evaluator.sha256` at EP-1 and EP-2; the diff touches adapter files only |
````

**M6-c** · F-05 · replace

Anchor:
````text
EP-1's replayed decisions reconciled
````

With:
````text
EP-2's replayed decisions (T4.9, the same `evaluator.sha256` as EP-1's) reconciled with EP-1's
````

**M6-d** · F-05 · insert after

Anchor:
````text
One worker per PR, each in its own branch + worktree; 10–12 at once; the ops lane is not a PR.
````

Text (starts with a space):
````text
 **Paths in the Owns column follow ARCH §3.0:** `adapters/…`, `store/…` and `stitch/…` mean `prooflab/adapters/…`, `prooflab/store/…` and `prooflab/stitch/…` (the judge imports them as `prooflab.*`). EP-2's `prooflab/adapters/postrun/` belongs to PR-23 (T4.9). `tests/<area>/` (repo root) holds only suites that need the 3.12 Strands venv; every stdlib suite goes under `prooflab/tests/<area>/`.
````

**M6-e** · F-05 · replace

Anchor:
````text
| PR-00 … PR-22 | The seed feature map (§6)
````

With:
````text
| PR-00 … PR-23 (+ the Phase 1 slices PR-nna) | The seed feature map (§6)
````

**C1-a** · C-01 · replace

Anchor:
````text
→ finding → **`notify`** (decided by the captain; production log, absolute path; never `--dry-run`)
````

With:
````text
→ finding → a TEST-log rehearsal first (`notify --dry-run` with its own log under `evidence/servicenow/wiring-tests/`, guard (a); the build prompt's "a TEST log before the first real one") → **`notify`** (decided by the captain; production log, absolute path; never `--dry-run` on it)
````

## 6. Skip list: 41 reviewer pairs superseded by §5

- 17A-01 · `` The rest launch once PR-01 merges (~02:30). `` → M2-a
- 17A-01 · `` `prooflab/humanloop/` (not `invoke.py`) | PR-01, PR-09, PR-19 | `` → M2-b
- 17A-01 · `` `tools/submit_wrapper.sh` | PR-12, PR-13, PR-16 | `` → M2-c
- 17A-01 · `` | T4.2, T4.4, T5.3 | `` → M2-d
- 17A-02 · `` | PR-07 | **Ph1** · J2: JSON in the text answer, one re-ask, the precedence rule… `` → M3-a
- 17A-02 · `` `agents/ifabric-{customer,it,network}/` | PR-02–PR-05 | `` → M3-b
- 17A-02 · `` launched first (PR-00 … PR-06) `` → M3-c
- 17A-02 · `` PR-03 + PR-04 + PR-05 → PR-06 `` → M3-d
- 17A-02 · `` PR-05 MIN rails → PR-06 bundler `` → M3-e
- 17A-02 · `` | W2 worker → T2 worker | T3.3 | `` → M3-g
- 17A-02 · `` If Stage B slips, Stage A ships and gap 1 stays open `` → M3-h
- 17A-03 · `` ; **the AWS credential refresh** meanwhile | M + act | `` → M4-g
- 17A-03 · `` | 10 | 1 | 04:25 | B2 | Freeze record: digests, generations, models, runtime ver… `` → M4
- 17A-03 · `` **the AWS credential refresh at ~04:45** (expiry 06:29 falls inside Phase 1) `` → M4-e
- 17A-03 · `` the AWS credential refresh (~04:45). `` → M4-c
- 17A-03 · `` refresh at **~04:45** (Hold-2, during P5; `` → M4-h
- 17A-03 · `` The refresh in Hold-2 (~04:45, during P5) `` → M4-i
- 17A-03 · `` Due inside Phase 1, at ~04:45 (Hold-2); backstop alarm 05:45 `` → M4-j
- 17A-04 · `` the mode switches for N2 (`observe`) and N3 (`enforce`, the owner's remediation)… `` → M5-a
- 17A-09 · `` One worker per PR, each in its own branch + worktree; 10–12 at once; the ops lan… `` → M6-d
- 17A-11 · `` alarms at 04:45 (AWS refresh, Hold-2) and 05:45 (backstop) `` → M4-k
- 17A-11 · `` alarms 04:45 (AWS refresh, Hold-2) and 05:45 (backstop) `` → M4-l
- 17B-01 · `` **Ph1 (minimal)** · **J2 (Stage B):** `` → M3-f
- 17B-01 · `` If Stage B slips, Stage A ships and gap 1 stays open `` → M3-h
- 17B-01 · `` one re-ask, the precedence rules (bundled at Stage B) `` → M3-a
- 17B-01 · `` | PR-02–PR-05 | `` → M3-b
- 17B-02 · `` EP-1's replayed decisions reconciled `` → M6-c
- 17B-04 · `` | W6 worker → Arth | T4.2, T4.4, T5.3 | `` → M2-d
- 17B-04 · `` | PR-12, PR-13, PR-16 | `` → M2-c
- 17B-18 · `` first `submit.sh` by 13:15, final by 14:45 `` → 17C-15's T8.9 pair (applied as written)
- 17C-01 · `` **Slip rule:** `` → M1-a
- 17C-03 · `` The rest launch once PR-01 merges (~02:30). `` → M2-a
- 17C-03 · `` | PR-01, PR-09, PR-19 | `` → M2-b
- 17C-03 · `` | PR-12, PR-13, PR-16 | `` → M2-c
- 17C-04 · `` the AWS credential refresh (~04:45). `` → M4-c
- 17C-06 · `` | PR-07 | **Ph1** · J2: JSON in the text answer, one re-ask, the precedence rule… `` → M3-a
- 17C-06 · `` launched first (PR-00 … PR-06) `` → M3-c
- 17C-06 · `` the critical chain's merge order: PR-01 → PR-02 → PR-03 + PR-04 + PR-05 → PR-06; `` → M3-d
- 17C-06 · `` | W2 worker → T2 worker | T3.3 | 1.5–2 h | `` → M3-g
- 17C-07 · `` `v1`'s APPROVED values; the mode switches for N2 `` → M5-a
- 17C-15 · `` which predates the phases (by that prompt's own rule, on timings this plan wins;… `` → M4-m

## 7. Outside the plan: urgent, not yet done
- **T0.7, the prototype rescue:** `tools/prototypes/` doesn't exist. `work/13`'s proven Assurance bundle prototypes (`make_bundle.py`, `shim_analyzer.py`, `e2e_glue.py`, `bundletest/`, `repro_bugs.py`) are still only in the planning session's scratchpad `…/ca14fa49-…/scratchpad/h3/` (present at 02:05Z). PR-06 and PR-19 use them as templates. Copy them before that session ends (a repo write: the captain's OK).
- **T0.8:** `caffeinate -dimsu` was not running at 01:42Z; only transient 300-s assertions held off a one-minute idle sleep (17c).
- **`NEXT-SESSION-PROMPT.md`** still says the refresh is at "~04:45 (Hold-2…)". It goes stale under F-04. It is a tracked file, so this is reported only.

## 8. Inconsistencies with `BUILD-SESSION-PROMPT.md` (report only; nobody edits it now)
1. **The refresh:** ":124" asks for it "in Hold-2 (~04:45; backstop alarm 05:45)". That ties it to a sliding hold; F-04 fixes it to the clock at 03:30–04:15. (17a, 17c)
2. **The 07:00 promise:** ":44–45" promises "at least C16's floor end to end" by 07:00. That is infeasible once Stage A passes ~04:40. (17c)
3. **The ★ list:** ":53–54" lists PR-00…PR-06. Minimal J2 (PR-07) must be ★ for Gate G2; the prompt defers to §6's ★, so the plan's fix suffices. (17a, 17b, 17c)
4. **The size cap:** ":71" says "≤ 24,000 chars (the CI gate; hard cap 24,049)". The real cap depends on the tag length (3 chars per tag char) and `EXTRA_PIP`: 24,028–24,172 measured, ≈ 23,926 with a 40-hex tag. Use the kit's `DRY_RUN=1` check. (17a)
5. **Libraries:** ":72" says "libraries only via EXTRA_PIP". With `TARGET=agentcore` the kit's `SDK_PIP` supplies the Strands stack; `EXTRA_PIP` adds only `openai`. The prompt never says `TARGET=agentcore`. (17a)
6. **AUTHORITY (:107–121)** has no line for ledger writes (S-1), the S3 probe or T1 PUTs, or the local credential-profile rewrite. The plan filled the gap three different ways. (17a, 17c)
7. **The scan:** ":88" says the scan "also checks the ServiceNow secrets", but the plan's T6.10 still lists that as a Phase 1 task. Unverified: the script was not read. (17a)
8. **Workflow time-box:** ":78" time-boxes each workflow to ≤ 45 min. Phase 1 PRs carry 1–7 agent-hours, so the time-box should bound an orchestration step, not a worker's life. (17c)
9. **When the build starts:** ":3" says "commit any uncommitted planning files first", while the plan's §4.2 starts the chain "at ~01:00, not after this plan's review". At 01:45 neither had happened. (17c)
10. **Holds:** ":106" and ":61" ask for holds with a recommended default, but neither file gives a hold timeout, a waiting rule, or awake/sleep windows. (17c)
11. **The buffer:** ":42" asks for "≥ 1 h buffer", while ":45" allows "the final submit by 14:45" (internal to the prompt). (17c)
12. **The gateway token:** ":88" says the scan needs `/tmp/modaas-token`, but no one is named to re-extract it after a reboot. (17c)
13. **Valid submission:** ":43" says "so a valid submission always exists", but the plan's G5 and G6 didn't check validity before 17B-05/-06/-07. (17b)
14. **The L1→L3 path:** ":47–48" puts "the L1→L3 path" in Phase 2, while the plan's §4.6 put it all in the Phase 1 Must row (17B-21). (17b)
15. **PACK mode:** ":19" says "PACK mode refuses synthetic data", which had no executable check (17B-17). (17b)
16. **Rehearsals:** ":50" makes the second rehearsal a Should, while the slides say "Rehearse it twice". It stays Should here (captain item 12). (17b)
17. **The TEST log:** ":105" requires "a TEST log before the first real one", and §5.2 had no such step (C-01). (coordinator)
18. **Freeze wording:** ":104" says "Deploy + smoke customer first (S-2), then IT + network (S-4); one freeze record". The plan quotes an older wording; the substance is the same. (17a)

## 9. Needs the captain (each with a recommended default)
0. **T0.7 now:** OK the copy of the prototypes into `tools/prototypes/`. Default: **yes, before the planning session ends.**
1. **Launch the build now, if not already running.** Default: **yes.** The ★ chain codes against ARCH and the B1 lane opens at once; this fix set lands as a commit that the orchestrator re-reads at G1. (17c)
2. **The AWS refresh.** Default: **03:30–04:15 UTC (22:30–23:15 CDT), fixed to the clock**, between runs, never before 03:00, plus a second refresh before the judging slot if it ends after the new expiry. (F-04; 17a, 17c)
3. **One B1 OK** for S-1 (the `[]` probe + one labelled record) and the bucket probe. Default: **yes.** (17a, 17c)
4. **Split the Phase 1 slices** (PR-08a…PR-22a, PR-23). Default: **yes.** Without it, Phase 1 can't meet 07:00 as mapped. (17a, 17c)
5. **The 07:00 rule.** Default: if G5 is projected after 08:00, a curated safety submit at 07:00 (register draft, risks, inventory, gap list, sketch, README; scanned). If submit #1 lands after 10:00, submit #2 merges into the final. (17c)
6. **Hold-1 before sleeping, then sleep.** Default: in Hold-1, give the risk ratings and appetite (T1.5, B-G8), the registry values (T1.4) and the B1 OK. Sleep from the refresh until an alarm at the projected G2 − 15 min. Stay awake from G2 to submit #1, and for Phase 2's holds, rehearsal 1 and the final submit. (17c)
7. **Cut items 1–4:** the orchestrator applies them on their triggers without asking. Default: **yes**; items 5 and 7 still come to the captain. (17c)
8. **Arth's time zone and hours** against the re-anchored clock. Default:
   - reachable at the re-anchored G4 for the T2 review, and at ~11:00–13:30Z for AICT and rehearsal 1;
   - otherwise the labelled AI-tester fallback after 30 min with no answer. (17c)
9. **Minimal J2 at Stage A's hard bound.** Default: ship without it; gap 1 is stated in the README's pillars table, and Hold-2 says so. (17b)
10. **C9 at submit #1.** Default: C9's threshold is in `v1`, and C9 queries answer "not assessed" (exit 2). N1, N3 and N5 stay baseline-eligible, never C9-assessed; C9's assessed runs are N7–N9. (17b)
11. **N6, the only named escalate run, stays in Phase 2.** Default: **yes.** Submit #1's pillar row cites N2/N3's J2 records and P3 (PILOT, not assessed). (17b)
12. **The second rehearsal.** Default: Should; run it whenever Phase 3 has ≥ 20 min left before the final pack. (17b)

## Appendix A · All 140 operations, in order (machine-readable)
Each item is `[finding id, kind, anchor, text]`.
- `R` replaces the anchor with the text.
- `I` inserts the text right after the anchor.
- `IEOL` inserts the text at the end of the anchor's line.

The first 33 items are §5's merged operations. Then come 17a's, 17b's and 17c's pairs as written, in file order, minus §6's skip list. The snippet below applies them (stdlib; run from the repo root; optional finding ids to skip as arguments):

```python
import hashlib, json, re, sys
md = open("architecture/work/17-plan-review-findings.md", encoding="utf-8").read()
ops = json.loads(re.search(r"````json\n(.*?)\n````", md, re.S).group(1))
path = "IMPLEMENTATION-PLAN.md"; t = open(path, encoding="utf-8").read()
print("plan sha256", hashlib.sha256(t.encode()).hexdigest(), "(baseline 0a1d6183e6b4…)")
skip = set(sys.argv[1:]); bad = 0
for fid, kind, a, x in ops:
    if fid in skip: continue
    n = t.count(a)
    if n != 1: bad += 1; print("NOT APPLIED", fid, n, repr(a[:70])); continue
    k = t.find(a)
    if kind == "R": t = t[:k] + x + t[k + len(a):]
    elif kind == "I": t = t[:k + len(a)] + x + t[k + len(a):]
    else: e = t.find("\n", k); t = t[:e] + x + t[e:]
if bad: print(bad, "not applied: nothing written"); sys.exit(1)
open(path, "w", encoding="utf-8").write(t); print("all applied")
```

````json
[
["M1-a", "I", "**Slip rule:**", "\n0. **Re-anchor at the start, then at each gate.** t0 = the time the orchestrator launches the ★ chain (planned 01:00; not launched at 01:45). At launch it writes t0 into the STATUS line and moves every Phase 1 time in §4.3, §5.2 rows 1–25, the holds and Gates G1–G5 by (t0 − 01:00). Three things never move: the AWS credential refresh (§5.2 row 4a, fixed to the clock), the hard bounds (rule 4) and the 07:00 safety submit (rule 1). At each gate it re-projects submit #1 as G2 + 2 h 35 min (+ 20 min if P7 runs, + the hold latency) and reports it. The ops lane opens at t0 and runs B1 at once; it doesn't wait for the orchestrator."],
["M2-a", "I", "The rest launch once PR-01 merges (~02:30).", "\n\n**\"After\" is the merge order, not the start.** Every Phase 1 PR launches as soon as a worker is free (★ first, then the slices below in needed-by order), codes against PR-01 and the ARCH text (§3.2, §4, §7.2) and rebases as PR-01 merges. The orchestrator merges every Phase 1 PR before any Phase 2 PR.\n\n**Phase 1's second chain (the ops lane's prerequisites).** The ops lane can't run §5.2 rows 6–25 on the ★ chain alone. These Phase 1 slices are split out now, each its own PR; the Phase 2 remainder keeps the original id. A late slice holds only its row:\n\n| Slice | Phase 1 contents only | Needed by (§5.2 row; planned UTC before re-anchoring) |\n|---|---|---|\n| PR-11a | the pin format → `pinned.py` (`IFABRIC_PIN_JSON` + `IFABRIC_PIN_SHA256`); `v0-smoke` frozen locally (also the first apply's pin); `freeze.py`; `inventory.py` (`inv-1`) | row 6 (03:50) |\n| PR-08a | `run.py` (envelope, CIDs, session ids, one invoke per handoff, `--only`, `--condition`, the §5.1 budget-guard preflight) + `deploy_wrapper.py` (the EP-10 record of every apply, annotation and pin or mode patch) | row 6 (03:50) |\n| PR-12a | `aws_spans`, `runtime_logs`, `aict_invocations`, `agentcore_metrics`, `ledger_export`, `cr_status` + T4.2's redaction | row 7 (03:55; S-2's assertions) |\n| PR-11b | T1.5's rated `risks.yaml`, T1.6's experiment plan, and a `derive` script (pilot captures → `experiments.jsonl` → proposed values by the frozen rules) | row 11 (04:27); `derive` by row 16 (05:00) |\n| PR-09a | `approval.py` (EP-0) first, then `c16.py`, then `c7.py` | `approval.py` by row 16 (05:00); `c16.py` by row 20 (05:27); `c7.py` by row 23 (05:50) |\n| PR-23 | T4.9, EP-2's post-run replay of the c16 core (the second EP) | row 20 (05:27; N2's assessment) |\n| PR-20a | T6.4's required keys + T6.5's `notify` with the bug (a)/(b) guards + T6.10; no G-03 | row 20 (05:27) |\n| PR-13a | T4.3 (the store or the laptop-store fallback), T4.4's joins, T4.5's CLI list | row 25 (~06:00) |\n| PR-15a | T5.1, the query engine + CLI | row 25 (~06:00) |\n| PR-21a | T4.8's minimal pack (no projector) + `tools/submit_wrapper.sh` | row 25 (~06:00) |\n| PR-22a | the adversarial-log rows written before their runs (ADV-H-01 leg A, N3 = ADV-R-05, N4 = ADV-R-10); the README, gap-list section B, `evidence/named-runs.md`, the `run-ids.txt` test | row 18 (05:22) for the log rows; row 25 (~06:00) for the rest |\n\nBefore PR-09a's `approval.py` merges, PR-08a's preflight records EP-0 as \"not built\" and proceeds; that is allowed only for unassessed runs (smokes and pilots, D13). Every pin or mode patch goes through `deploy_wrapper.py`; otherwise EP-0 declines N1 on the generation bump [ARCH §5.0 (c)]. If a slice misses its row, the lane does that step by hand with the slice's commands and records it, and the slip rule (§4.6) applies."],
["M2-b", "R", " `prooflab/humanloop/` (not `invoke.py`) | PR-01, PR-09, PR-19 | ", " `prooflab/humanloop/` (not `invoke.py`) | PR-01, PR-09a (PR-20a, the Ph1 `notify`); + PR-19 for the Ph2 remainder (the analysis) | "],
["M2-c", "R", " `tools/submit_wrapper.sh` | PR-12, PR-13, PR-16 | ", " `tools/submit_wrapper.sh` | PR-12a, PR-13a (PR-21a, the Ph1 minimal pack); + PR-16 for the Ph2 remainder (pack v2) | "],
["M2-d", "R", "| W6 worker → Arth | T4.2, T4.4, T5.3 |", "| W6 worker → Arth | T4.2, T4.4 (the Ph1 minimal pack); T5.3 only from pack v2 (submit #2) |"],
["M3-a", "R", "| PR-07 | **Ph1** · J2: JSON in the text answer, one re-ask, the precedence rules (bundled at Stage B) |", "| PR-07 ★ | **Ph1** · J2: JSON in the text answer + the precedence rules (minimal J2, in the Stage A image, Gate G2); the one re-ask only if ready by G2, else Stage B |"],
["M3-b", "R", " `agents/ifabric-{customer,it,network}/` | PR-02–PR-05 | ", " `agents/ifabric-{customer,it,network}/` | PR-02–PR-05, PR-07 (minimal J2) | "],
["M3-c", "R", "launched first (PR-00 … PR-06)", "launched first (PR-00 … PR-07)"],
["M3-d", "R", "the critical chain's merge order: PR-01 → PR-02 → PR-03 + PR-04 + PR-05 → PR-06;", "the critical chain's merge order: PR-01 → PR-02 → PR-03 + PR-04 + PR-05 + PR-07 → PR-06;"],
["M3-e", "R", "PR-05 MIN rails → PR-06 bundler", "PR-05 MIN rails ∥ PR-07 minimal J2 → PR-06 bundler"],
["M3-f", "R", "**Ph1 (minimal)** · **J2 (Stage B):**", "**Ph1 (minimal, in Stage A)** · **J2 (minimal in Stage A: JSON in the text + the precedence rules; the re-ask may wait):**"],
["M3-g", "R", "| W2 worker → T2 worker | T3.3 | 1.5–2 h |", "| W2 worker → T2 worker | T1.1 (bundled by T3.3) | 1.5–2 h |"],
["M3-h", "R", "If Stage B slips, Stage A ships and gap 1 stays open", "If minimal J2 is not green by Gate G2's hard bound (§4.6), Stage A ships without it, S-2's OC-10 check is skipped, and gap 1 stays open for the whole event (the agents freeze at Gate G3); the gap list and the README's pillars table say so, and Hold-2 tells the captain"],
["M4-a", "I", "| W (shared ToolConfig) + 3 MCP calls | 0 | **Hold-1** |", "\n| 4a | 1 | 03:30–04:15 (fixed to the clock: never re-anchored, never moved with Hold-2) | — | **The AWS credential refresh**, between runs with nothing live: the captain fetches new credentials at the Workshop Studio console; the lane rewrites the `hackathon` profile atomically (temp file + `mv`, mode 600, never printed), runs `aws sts get-caller-identity` and logs the new expiry (refresh + 12 h, ≥ 15:30). Never before 03:00 (the new expiry would fall before 15:00). If the judging slot ends after the new expiry, a second refresh before the slot (Phase 3) | W (local profile) + act | 0 | **act** (its own alarm, 03:30) |"],
["M4-b", "I", "| captain → ops lane | both PDP replicas + `/modaas/evidence`; CR still Approved |", "\n| 03:30–04:15 (fixed) | **The AWS credential refresh** (§5.2 row 4a), between runs, never during one; the new expiry logged | captain + ops lane | `sts get-caller-identity`; new expiry ≥ 15:30 |"],
["M4-c", "R", "P5 (> 150K) and P7 if needed; the AWS credential refresh (~04:45).", "P5 (> 150K) and P7 if needed. (The AWS credential refresh is not in this hold: it is fixed to the clock, 03:30–04:15, §5.2 row 4a, and asked for on its own at its alarm.)"],
["M4-d", "R", "(the approval annotations, the pilots' S2 run, the AWS refresh)", "(the approval annotations, S-3's pin patches, the pilots' S2 run)"],
["M4-e", "R", "**the AWS credential refresh at ~04:45** (expiry 06:29 falls inside Phase 1)", "(the AWS credential refresh is already done: §5.2 row 4a, 03:30–04:15)"],
["M4-f", "R", "| experiments log; new expiry ≥ 16:45 |", "| experiments log |"],
["M4-g", "R", "; **the AWS credential refresh** meanwhile | M + act |", " | M |"],
["M4-h", "R", "refresh at **~04:45** (Hold-2, during P5;", "refresh at **03:30–04:15, fixed to the clock** (§5.2 row 4a; between runs, never during one;"],
["M4-i", "R", "The refresh in Hold-2 (~04:45, during P5)", "The refresh fixed to the clock at 03:30–04:15 (§5.2 row 4a; between runs; never moved by the slip rule)"],
["M4-j", "R", "Due inside Phase 1, at ~04:45 (Hold-2); backstop alarm 05:45 | 04:25–05:00 row |", "Fixed to the clock at 03:30–04:15 (§5.2 row 4a), between runs; backstop alarm 05:45 | §4.3's 03:30–04:15 row |"],
["M4-k", "R", "alarms at 04:45 (AWS refresh, Hold-2) and 05:45 (backstop)", "alarms at 03:30 UTC = 22:30 CDT (the AWS refresh, §5.2 row 4a) and 05:45 UTC = 00:45 CDT (backstop: refresh at once if row 4a was missed), set in the phone's local time"],
["M4-l", "R", "alarms 04:45 (AWS refresh, Hold-2) and 05:45 (backstop)", "alarms 03:30 UTC = 22:30 CDT (the AWS refresh, §5.2 row 4a) and 05:45 UTC = 00:45 CDT (backstop)"],
["M4-m", "R", "which predates the phases (by that prompt's own rule, on timings this plan wins; the refresh moves to ~04:45 inside Phase 1)", "in an earlier version of that prompt (the current one defers slot times to §4.3 and §4.6; its \"refresh in Hold-2, ~04:45\" is superseded by §5.2 row 4a)"],
["M5-a", "R", "`v1`'s APPROVED values; the mode switches for N2 (`observe`) and N3 (`enforce`, the owner's remediation);", "`v1`'s APPROVED values and the IDE version listing for T1 (before submit #1; it never blocks N1, Gate G4); the mode switches for N2 (`observe`) and N3 (`enforce`, the owner's remediation); ADV-H-01 leg A's rails `observe`/`enforce` patches (row 18);"],
["M6-a", "I", " 2–3 h | S3 (at each submit; pre-authorized) | 0 |", "\n| T4.9 | **Ph1** · **EP-2, the second placement of the c16 core** (`adapters/postrun/c16_replay.py`; ARCH §3.1, §11.1): after each run, the run's model-call spans from `aws/spans` in gateway order; per call one `C16Question` (committed = the earlier calls' actual tokens, reserved = 0, bound = this call's actual tokens, `bound_basis: actual`) through the **same** `c16_core.decide_inline` with the run's pin; each result a `decision` record (`ep.id: EP-2`, `ep.transport: pull`, the core's `evaluator.sha256`), recorded, never executed. Its own PR (PR-23), so its `git diff --stat` shows adapter files only (the I-21 proof) | For N2 and N3, one EP-2 decision per model-call span, each with the same `evaluator.sha256` as EP-1's decisions; `c16.py`'s reconciliation lists every EP-1/EP-2 difference; the PR touches only `adapters/postrun/` | PR-23 worker → PR-09's reviewer | T1.2, T4.1 | 1 h | — | 0 |"],
["M6-b", "I", "no claim beyond the evidence; the six deliverables |", "\n| PR-23 | **Ph1** · EP-2: the post-run replay of the c16 core (the second EP) | T4.9 | `adapters/postrun/` | PR-02, PR-12a | Sonnet · medium | the same `evaluator.sha256` at EP-1 and EP-2; the diff touches adapter files only |"],
["M6-c", "R", "EP-1's replayed decisions reconciled", "EP-2's replayed decisions (T4.9, the same `evaluator.sha256` as EP-1's) reconciled with EP-1's"],
["M6-d", "I", "One worker per PR, each in its own branch + worktree; 10–12 at once; the ops lane is not a PR.", " **Paths in the Owns column follow ARCH §3.0:** `adapters/…`, `store/…` and `stitch/…` mean `prooflab/adapters/…`, `prooflab/store/…` and `prooflab/stitch/…` (the judge imports them as `prooflab.*`). EP-2's `prooflab/adapters/postrun/` belongs to PR-23 (T4.9). `tests/<area>/` (repo root) holds only suites that need the 3.12 Strands venv; every stdlib suite goes under `prooflab/tests/<area>/`."],
["M6-e", "R", "| PR-00 … PR-22 | The seed feature map (§6)", "| PR-00 … PR-23 (+ the Phase 1 slices PR-nna) | The seed feature map (§6)"],
["C1-a", "R", "→ finding → **`notify`** (decided by the captain; production log, absolute path; never `--dry-run`)", "→ finding → a TEST-log rehearsal first (`notify --dry-run` with its own log under `evidence/servicenow/wiring-tests/`, guard (a); the build prompt's \"a TEST log before the first real one\") → **`notify`** (decided by the captain; production log, absolute path; never `--dry-run` on it)"],
["17A-01", "R", "| PR-01, PR-09 | Sonnet · medium | one invocation per handoff", "| PR-01 (PR-09a's `approval.py` once merged) | Sonnet · medium | one invocation per handoff"],
["17A-01", "R", "| W3 worker → T4 (W6) worker | T1.1, T1.3 |", "| W3 worker → T4 (W6) worker | T1.1; T1.3's `approval.py` when merged (§6, PR-08a) |"],
["17A-01", "R", "| G-03, G-04, `~/.prooflab-snow.env` |", "| G-04, `~/.prooflab-snow.env` (Ph1 `notify`); G-03 only for the Ph2 analysis |"],
["17A-04", "R", "patch back (inside S-2's 10-min wait for the AWS record) | W + M | 10K | pre |", "patch back (inside S-2's 10-min wait for the AWS record) | W + M | 10K | **Hold-2** |"],
["17A-04", "R", "on all three | W (S3, cluster) | 0 | pre |", "on all three | W (S3, cluster) | 0 | **Hold-2** |"],
["17A-04", "R", "→ rails `enforce` patch (leg B in Phase 2) | W + M | 5K | pre |", "→ rails `enforce` patch (leg B in Phase 2) | W + M | 5K | **Hold-3** |"],
["17A-04", "R", "the three trio approval annotations (the captain's own act, never faked);", "the three trio approval annotations (the captain's own act, never faked); S-3's pin/mode patches (row 8); `v0-pilot`'s `observe` pin and its T1 PUT (row 11);"],
["17A-05", "R", "`IMAGE_TAG=ifabric-<role>-<git sha>` + `URI_FILE` each", "`TARGET=agentcore`, `AGENT_SRC=agents/ifabric-<role>/ifabric-<role>.py`, `EXTRA_PIP=\"openai==2.54.0\"`, `IMAGE_TAG=ifabric-<role>-<7-hex git sha>` + `URI_FILE` each"],
["17A-05", "R", "`IMAGE_TAG=ifabric-<role>-<git sha>`, a per-agent `URI_FILE`", "`TARGET=agentcore`, `AGENT_SRC=<the bundle>`, `EXTRA_PIP=\"openai==2.54.0\"` (Strands, bedrock-agentcore, mcp, boto3 and ADOT come from the kit's own `SDK_PIP` pins), `IMAGE_TAG=ifabric-<role>-<7-hex git sha>`, a per-agent `URI_FILE`"],
["17A-05", "R", "the pinned `openai`)", "`openai==2.54.0`, the version in `workshop-local/.venv` and the one `EXTRA_PIP` puts in the image)"],
["17A-05", "R", "`URI_FILE` (never `new-agent.sh`)", "`URI_FILE` and `TARGET=agentcore` (no `EXTRA_PIP` unless the shim imports beyond the kit's `SDK_PIP`; never `new-agent.sh`)"],
["17A-06", "R", "bundle size ≤ 24,000 chars per agent;", "bundle size ≤ 24,000 chars per agent AND the kit's own check offline: `DRY_RUN=1 TARGET=agentcore STACK=a-01-eks-cluster ACCT=000000000000 AGENT_SRC=<bundle> IMAGE_TAG=<the real tag> EXTRA_PIP=<the real pins> bash …/workshop-static/reference-impl/build-agent-image.sh` exits 0 (DRY_RUN makes no AWS call);"],
["17A-07", "R", "Over budget → `--buildspec-override` [ARCH §7.1]", "Over budget → drop the P2 rails first; then the two-stage build (a first build of the base bundle, then our own buildspec `FROM <repo>@<digest>` adding a second gz+b64 file, each under the 25,600-char cap [05 AR-03]), written and `DRY_RUN`-checked offline by PR-06 before Gate G2"],
["17A-07", "R", "drop P2; `--buildspec-override` |", "drop P2; the two-stage `FROM <digest>` build [05 AR-03] (a plain `--buildspec-override` is what the kit already uses: same cap) |"],
["17A-08", "R", "the 3.9 `pytest -q`;", "the 3.9 `pytest -q` over the stdlib suites (`prooflab/tests/`, the tool's tests) and the 3.12 venv's `pytest -q` over the agent-side suites (T-C16-01, T-DUP-01, S-G1, J2, the bundle tests; they carry a `strands` marker the 3.9 run skips);"],
["17A-08", "R", "the full test suite (the 3.9 venv's `pytest`)", "the full test suite (`tools/gate.sh`: the 3.9 stdlib suites + the 3.12 agent-side suites)"],
["17A-10", "R", "`prooflab/cli.py`, `tests/conftest.py`, `tests/contract/` | PR-00 |", "`prooflab/cli.py` (a fixed verb → module table for every ARCH §3.0 verb, each module owned by its PR), every package's `__init__.py`, the root `pytest.ini`, `tests/conftest.py`, `tests/contract/` | PR-00 |"],
["17A-10", "R", "`register/` (not `conditions/`, `c16_core.sha256`) | PR-01 |", "`register/` (not `conditions/`, `c16_core.sha256`, nor the lane's outputs `versions/`, `pins/`, `experiments/*.jsonl`, `inventory/`, which the orchestrator commits through the merge gate as \"lane\" commits) | PR-01 |"],
["17A-10", "R", "`evidence-templates/`, `gap-list.md` (section B only), `docs/run-of-show.md` | PR-01 |", "`evidence-templates/`, `gap-list.md` (section B only), `evidence/adversarial/` (not `corpus/`), `evidence/named-runs.md`, `reviews/` templates, `reviews/run-of-show.md`; the orchestrator owns `FEATURE-MAP.md`, `reviews/gates.jsonl`, `live-lane-log.jsonl` and `run-ids.txt` | PR-01 |"],
["17A-12", "R", "| ~01:15 on the reference agent; again ~03:45 on the Stage A bundle | 0 tok, 1–2 h | — (local) |", "| after T0.5 and T0.7 (~02:00) on the reference agent; again ~03:45 on the Stage A bundle | 0 tok, 1–2 h | — (local; run by PR-06's worker; the image pulls are covered by T0.5's install OK) |"],
["17A-13", "R", "and the IDE's version listing;", "(the IDE's version listing follows before submit #1 and never blocks N1: the person at the IDE runs `aws s3api list-object-versions --prefix ifabric/register/ > v.json` and then `aws s3 cp v.json s3://<bucket>/ifabric/register/versions-<UTC>.json`, which the laptop downloads into the pack);"],
["17A-14", "R", "--checksum-algorithm SHA256`; `head-object --checksum-mode ENABLED` | B1, 01:30 |", "--checksum-algorithm SHA256`; `head-object --checksum-mode ENABLED`; a second PUT of the same key with `--if-none-match '*'` must fail with 412 (the write-once guard every T1 PUT then uses) | B1, 01:30 |"],
["17A-14", "R", "**T1** PUT × 2 + head-object;", "**T1** PUT × 2 (`--if-none-match '*'`, `--checksum-algorithm SHA256`) + head-object;"],
["17A-15", "R", "`register/conditions/`, `policies/cedar/`", "`register/conditions/` (SP-1's `policies/cedar/` texts are PR-05's)"],
["17A-15", "R", "`tests/rails/`, `evidence/adversarial/corpus/` |", "`tests/rails/`, `evidence/adversarial/corpus/`, `policies/cedar/` (SP-1's three texts, reviewed by PR-05's Opus reviewer by ~02:45) |"],
["17A-15", "R", "| T3 (W3) worker → guardrails author | — | 0.5 h |", "| PR-05's worker → guardrails author | — | 0.5 h |"],
["17A-16", "R", "Service-proxy POST of `[]` with the token in memory", "Service-proxy POST of `[]` with the token in memory (through `kubectl proxy --address=127.0.0.1 --port=8001` + an in-process POST; `kubectl create --raw` can't set `X-Audit-Token`)"],
["17A-16", "R", "**\"Writes needing the captain's OK\"** covers: any cluster, AWS or ServiceNow write;", "**\"Writes needing the captain's OK\"** covers: any cluster, AWS or ServiceNow write that §5.1 does not list as pre-authorized (S-1 and the bucket probe: one OK for block B1, see \"Needs the captain\");"],
["17A-17", "R", "a 3.12 venv `…/.venv-strands312` with the exact pins", "a 3.12 venv `…/.venv-strands312` installed from `workshop-local/requirements.lock.txt` (the exact pins of the working `workshop-local/.venv`) + pytest"],
["17A-19", "R", "digests recorded | W (AWS) | 0 | pre |", "digests recorded (ARM concurrency is unverified: a QUEUED build is normal, ≈ 45 s each if serialized) | W (AWS) | 0 | pre |"],
["17A-20", "R", "**lead, now** → T6 worker", "**lead, now, before the fan-out** (PR-00 then owns `tools/prototypes/`) → T6 worker"],
["17B-03", "R", "| T1 worker → T8 worker | Gate G6 | (in T1) | S3 | 0 |", "| T1 worker → T8 worker | each named run (T1.9); rewritten at each submit | (in T1) | S3 | 0 |"],
["17B-03", "R", "| T8 worker → Arth | Gate G6 | 0.25 h | — | 0 |", "| T8 worker → Arth | submit #1: ADV-H-01 leg A (gap 4: our BLOCKED against the platform's ALLOW); re-chosen at rehearsal after Gate G6 | 0.25 h | — | 0 |"],
["17B-03", "R", "the minimal pack (store export, raw, assessments, register + T1 proof, `run-ids.txt`, gap list, `sketch.png`, README; redaction + the exact-value scan; MANIFEST)", "the minimal pack (the tool `prooflab/`; the store export; raw; assessments + findings; `servicenow/delivery-log.jsonl`; register `v1` + `v1.risks.yaml` + `inv-1` + the T1 proof; `window.json` + the run catalogue; `named-runs.md`; the adversarial log; `live-lane-log.jsonl`; the README; the WORKDIR copies `register.yaml` (= `v1.yaml` byte for byte), `run-ids.txt`, `gap-list.md`, `sketch.png`; redaction + the exact-value scan; MANIFEST)"],
["17B-05", "I", "**submit #1 read back**", "; on the downloaded zip a non-builder ticks the six deliverables (R-J-44): the pack with `prooflab/` inside; `register.yaml` byte-identical to `register/versions/v1.yaml` (per-control version and date); `run-ids.txt` one CID per line with no pilot or baseline id; `sketch.png`; `gap-list.md`; the exact-value scan 0 hits on the unzipped tree, WORKDIR files included"],
["17B-05", "I", "**submit #2 read back**", ", with the same six-deliverable tick on the downloaded zip (`register.yaml` = the latest frozen version, byte for byte)"],
["17B-06", "I", "`python3 -m prooflab query --control C16 --run <N2's CID>` answers in < 2 min from a fresh unzip on 3.9;", " the same for C7 (`--control C7 --run <N4's CID>`) and one `--window` query per complete control (C16, C7) inside the declared Phase 1 window, each < 2 min, timed by the non-builder; an unknown CID and `--control C9 --run <N1's CID>` each exit 2 with \"not assessed\" or \"insufficient evidence\", never a pass; `query --claim` reads \"partial coverage\";"],
["17B-06", "R", "`cd evidence && python3 -m prooflab query --control C16 --run <CID>` answers in < 2 min from the unzipped pack on 3.9, timed by a non-builder;", "`cd evidence && python3 -m prooflab query --control C16 --run <CID>`, the same for C7, and one `--window` query per complete control each answer in < 2 min from the unzipped pack on 3.9, timed by a non-builder; an unknown CID and an unassessed control exit 2 with \"not assessed\";"],
["17B-07", "I", "N3 SATISFIED with a stop record (or every attempt listed);", " the date check passes for every CID in `run-ids.txt` (`v1`'s T1 LastModified, with `v1.head.json`'s SHA-256 equal to the pack's `v1.yaml`, earlier than the run's first span in `aws/spans`), printed in each answer;"],
["17B-08", "I", "ADV-H-01 leg A shows BLOCKED_GUARDRAIL on the task call (the L1 block on record);", " L1 from the pack alone (R-J-01): every model-call span of N1–N5 names a Nemotron model, and the redacted CR status shows `safety.required: true` on each ModelConfig used and every agent, model and tool Approved;"],
["17B-09", "R", "N2's and N4's incidents DELIVERED (production log, absolute path, no dry run)", "N2's and N4's incidents DELIVERED to the register's named owner (`SNOW_OWNER_USER`), with the delivery log and the Finding files in the pack (production log, absolute path, no dry run); the README says the response-or-silence record starts in Phase 2"],
["17B-10", "I", "**C7:** N4 BREACHED, N5 SATISFIED;", " N2's finding is closed only by N3's SATISFIED assessment and N4's only by N5's, each linked by finding id in `findings/` (the ServiceNow incidents stay open until their Phase 2 re-test link note);"],
["17B-10", "R", "**Ph1 (`notify` only, decided by the captain, with the guards) · Ph2 (analysis, the check loop, snapshots)**", "**Ph1 (`notify` only, decided by the captain, with the guards) · Ph2 (analysis, the check loop, snapshots, the re-test link note on each incident, ARCH §3.8)**"],
["17B-10", "R", "The first **WRITTEN** analyses on N2's and N4's incidents (between runs)", "The first **WRITTEN** analyses on N2's and N4's incidents (between runs), then the re-test link notes (N3 → N2's incident, N5 → N4's; through the integration, else the owner by hand, else a gap row; ARCH §12.4; Hold-4 unless `notify`'s incident reuse writes it, since ARCH §12.2 W9 makes it a ServiceNow write with the captain's OK)"],
["17B-11", "I", "N1 SATISFIED;", " pillar 1 on record: N2's and N3's (S2) `judgment` records carry the J2 fields (disposition, deciding evidence, reason), and `score-run.py`'s grade on N3's per-CID ledger export sits in `answers/` beside the reference S2 run's (EXPLORATORY), or the gap list says gap 1 is open;"],
["17B-12", "R", "the stranger's README (the declared window; one command per question; the honest failure; what was left out and why);", "the stranger's README (the declared window; the pillars table, one row per pillar pointing to its files, none empty (R-J-04); one command per question; the six-question table marking each answer FULL or PARTIAL for this submit and naming what arrives later (submit #1: no PDP replica lines, AWS-written invoker records, T2, AICT or corroboration report); the honest failure; the adapter-diff note for the second EP (ARCH §11.1, I-21: the PR sha, its `git diff --stat`, the core's sha256 at EP-1 and EP-2); what was left out and why; no claim beyond the evidence in this submit);"],
["17B-12", "I", "the minimal pack passes the exact-value scan (0 hits) and `manifest.py verify`;", " `window.json` and the README declare the Phase 1 window (UTC start = `v1`'s T1 LastModified, end = this snapshot); `query --incident <N2's CID>` and `query --incident <ADV-H-01 leg A's CID>` answer the six questions with record ids, every PARTIAL answer naming its gap; the README names the honest failure with its evidence (R-J-16) and every claim in it cites a file in this pack;"],
["17B-12", "I", "`run-ids.txt` one CID per line with no pilot or baseline id, the six deliverables in the zip and in WORKDIR;", " the README's honest failure (T7.6) and pillars table present, every claim citing a pack file;"],
["17B-13", "I", "The window (UTC start, end, Alert 0/1/2 boundaries; default: from `v1`'s T1 LastModified to the final snapshot)", "; each run's Alert phase is the label the script wrote into its run-index line before the run (ARCH §3.7, I-11: ADV-H-01 leg A Hostile, N3 = ADV-R-05 and N4 = ADV-R-10 Rogue, the rest Alert 0), never assigned afterwards"],
["17B-13", "R", "the tally carried; conditions, faults, `--tamper-tally`; the run index line.", "the tally carried; conditions, faults, `--tamper-tally`; the run index line, carrying the run's declared Alert phase (0/1/2), written before the run (I-11)."],
["17B-14", "R", "**Ph1 (ADV-H-01's row) · Ph3**", "**Ph1 (the rows for ADV-H-01 leg A, ADV-R-05 = N3 and ADV-R-10 = N4, each written before its run) · Ph3**"],
["17B-15", "R", "C9's threshold in place", "C9's threshold in `v1` and an honest \"not assessed yet\" answer for C9 (G5)`. The G5 check itself is in 17B-06's insert (`--control C9 --run <N1's CID>"],
["17B-16", "R", "**Submit #1:** the minimal pack → `submit.sh` → readback", "**Submit #1:** a raw read of both PDP replicas' logs and the gateway pod's stdout (pod-only sources, read-only) → the minimal pack → `submit.sh` → readback"],
["17B-17", "R", "AT-01 run by a non-builder; AT-06 with its pattern assembled from parts", "AT-01 run by a non-builder; AT-06 with its pattern assembled from parts; a file labelled SYNTHETIC or the panel's fake sample placed in a staged copy is refused by `--data pack` with a red banner"],
["17B-19", "R", "the T2 incident exported with RESPONDED; the agents echo the `v1` pin", "the T2 incident exported with RESPONDED (Phase 2 by default, DC-10; a late T2 is a gap row); the agents echo the `v1` pin"],
["17B-20", "R", "one (Must) or two (Should) rehearsal records, the timed run of show, the recorded demo (or each missing item listed as a gap)", "one rehearsal record (Must, never replaced by a gap row) and a second (Should), the timed run of show, the recorded demo (each missing Should item listed as a gap)"],
["17B-20", "R", "| Gate G7 (first) |", "| Gate G6 |"],
["17B-21", "R", "| **Must** | The L1 → L3 path;", "| **Must** | L1 (the foundation: governed Nemotron, the MoDaaS guardrail block on record, approvals exported);"],
["17B-21", "R", "| **Must** | ServiceNow + the Assurance agent;", "| **Must** | The L2 → L3 path: ServiceNow + the Assurance agent, AICT;"],
["17C-01", "R", "| independent reviewer | the fan-out |", "| independent reviewer | the non-★ fan-out (B1's results block only PR-13's store choice, S-1, and the first freeze, the bucket probe) |"],
["17C-02", "R", "It needs ≤ 2.75 h to reach Stage A by ~03:45 (Fixer B's estimate was 3.75 h with fewer workers); that is the main risk, and the slip rule (§4.6) handles it.", "By §3's Effort column it needs about 6 h: PR-01 2.5–3 h; PR-03 3–4 h with B-G2; PR-05's MIN path about 4 h for one worker; PR-06 3–4 h, finished only after PR-03–PR-05 merge; plus seven serial merge gates of 15–40 min each. At AI pace (about half the estimates) it needs about 4–4.5 h. So Stage A ≈ t0 + 4–4.5 h, not t0 + 2.75 h. That is the main risk, and §4.6 rules 0–1 handle it. To shorten it, split PR-05 into the rails (B-G1 MIN) and the offline gates (S-G1, S-G2) as two workers, as `guardrails/PLAN.md` §0 asks."],
["17C-02", "R", "**Phase 1: minimum submission (target ~05:30; projected 05:45–06:30)**", "**Phase 1: minimum submission (target ~05:30). The rows below are the optimistic case (t0 = 01:00, Stage A in 2.75 h), re-anchored at t0 by §4.6 rule 0. Plan against the realistic offsets: G1 = t0 + 1.75 h; PR-01 merged = t0 + 2–2.5 h; G2 = t0 + 4–4.5 h; G3 = G2 + 45–60 min; G4 = G3 + 50–60 min (+15 with P7); G5 = G4 + 70–90 min (+20 with P7)**"],
["17C-02", "R", "(target 4 h, **~05:30**; projected 05:45–06:30)", "(target 4 h, **~05:30**; 06:20 in the optimistic case, 06:50 with P7; realistic offsets in §4.3, re-anchored by §4.6 rule 0)"],
["17C-02", "R", "Stage A by 03:45 needs the critical chain in ≤ 2.75 h (Fixer B estimated 3.75 h)", "Stage A needs the critical chain for about 4–4.5 h at AI pace (about 6 h by §3's Effort column; 2.75 h in the optimistic case; Fixer B 3.75 h)"],
["17C-03", "R", "The Phase 1 fan-out (§6, tagged Ph1)", "The Phase 1 fan-out (§6, tagged Ph1; each PR merged by the §5.2 row it gates, §6; they land until about G2 + 1 h, not by 03:45)"],
["17C-05", "R", "whatever Phase 1 has at **07:00 at the latest** is submitted (at least the C16 floor end to end), and the remainder rolls into Phase 2.", "at **07:00 at the latest** a safety submit goes out with whatever Phase 1 has. It holds the C16 floor end to end only if Gate G2 passed by about 04:40 (G2 → N2's notify takes 1 h 52 min in §5.2, the pack about 25 min). Otherwise it is a curated pack: the register draft with `risks.yaml` and `inventory.yaml`, the gap list, the sketch and the README; no raw captures; the scan first. Phase 1 then continues, and its full submit #1 follows at Gate G5; the remainder rolls into Phase 2 only after that."],
["17C-05", "R", "**Hard bounds:** submit #2 by 11:30 at the latest;", "**Hard bounds:** submit #2 by 11:30 at the latest (if submit #1 lands after 10:00, submit #2 merges into the final submit);"],
["17C-07", "I", "the Cedar restore after judging (DG-4).", "\n  - **When the captain must be awake, and what a waiting hold does.** Awake: (a) from t0 to the AWS refresh: the install and T0.7 OKs, B1's OK and the IDE listing, Hold-1, the risk ratings and appetite (T1.5, B-G8) and the registry values (T1.4); (b) from Gate G2 to submit #1: Hold-2 and Hold-3, including the IDE version listing for T1; (c) at Phase 2's start: Hold-4 and the T2 APPROVED note; (d) rehearsal 1 and the final submit. **Sleep is safe between (a) and (b):** nothing captain-gated runs there (merges are pre-authorized). The captain sets an alarm for the projected G2 (§4.6 rule 0), and the orchestrator plays a local alert (`say`) when G2's reviews start. **A hold unanswered for 20 minutes:** the lane runs only read-only steps and nothing that depends on it. No default ever replaces an annotation, an APPROVED note or the refresh: those wait. Hold-1's default: SP-1 moves to Phase 2, and the build works to 15:00. Hold-4's default: the item is not run (an unanswered C9 swap cuts C9's named runs, §4.6 item 3)."],
["17C-07", "R", "contacting the organisers to confirm the deadline and the account's end (OC-37).", "contacting the organisers to confirm the deadline and the account's end (OC-37); the owner's risk ratings and appetite (T1.5, B-G8) and the registry values (T1.4), needed before `v0-pilot`."],
["17C-07", "R", "**Hold-4 (~06:30, Phase 2 and 3):** the Assurance annotation;", "**Hold-4 (~06:30, Phase 2 and 3):** the Assurance annotation; the T2 APPROVED notes (§5.2 rows 26, 31);"],
["17C-08", "R", "**Arth reviews → the captain approves → `v1` frozen + T1 + T2 (G-13) + pinned**", "**the captain approves → `v1` frozen + T1 + pinned; Arth's \"reviewed\" note and T2 (G-13) follow in Phase 2 unless he is up in Hold-3 (DC-10)**"],
["17C-08", "R", "| T1 worker → Arth | T1.4, T1.5 | 0.5 h |", "| T1 worker → an independent reviewer before P1 (Arth's review follows with T2, labelled) | T1.4, T1.5 | 0.5 h |"],
["17C-08", "R", "**at 09:30**, an optional refresh by 12:00", "**≥ 20 min after G-02 and by 12:00 at the latest** (09:30 holds only if G-02 is READY by ~09:00), an optional refresh before the final pack"],
["17C-08", "R", "(Arth's export by 09:30)", "(Arth's export ≥ 20 min after G-02, by 12:00 at the latest)"],
["17C-08", "R", "his hours (05:00–05:20 for T2 if possible; 06:30–10:30 Phase 2; 12:00–13:30 rehearsals)", "his time zone and hours (05:00–05:20 for T2 if possible; 06:30–10:30 Phase 2; 12:00–13:30 rehearsals), re-confirmed against the re-anchored clock (§4.6 rule 0)"],
["17C-08", "R", "the Arth-unavailable fallback (T2 on Sree alone, labelled AI tester)", "the Arth-unavailable fallback (T2 on Sree alone, labelled AI tester; Arth counts as away when a request has no answer within 30 minutes, and the 5-link hand-check then falls to a non-builder AI reviewer, labelled)"],
["17C-09", "I", "re-extract the gateway token after any reboot |", "\n| R20 | **The orchestrator's context fills** over ~12 h and ~23 PRs | State lives in files (`FEATURE-MAP.md`, the STATUS line, `reviews/gates.jsonl`); at each gate, or when its context passes about 60 %, it writes a resume note, and the captain (or the lead) restarts it with `BUILD-SESSION-PROMPT.md` + \"resume from FEATURE-MAP.md\" |\n| R21 | **The ops-lane session** is never opened, dies or fills | The captain opens it at t0 (§4.6 rule 0; B1 doesn't wait for the orchestrator); `live-lane-log.jsonl` is its state; a restarted lane re-reads it and re-runs the preflight before any action |\n| R22 | **Laptop sleep before T0.8 is done** (at ~01:42Z `pmset` showed `sleep 1`, held off only by transient 300-s `caffeinate` assertions) | T0.8 at t0, checked by the orchestrator (`pmset -g assertions` shows the `caffeinate -dimsu` assertion); after a reboot the ops lane re-extracts the gateway token before any live step or merge, and the orchestrator resumes from its files |"],
["17C-09", "R", "| R15 | **Prototypes lost** with this session's scratchpad | T0.7 now |", "| R15 | **Prototypes lost** with this session's scratchpad | T0.7 before the commit that precedes the build session (not done at 01:45: no `tools/prototypes/`; the files are only in the scratchpad's `h3/`) |"],
["17C-09", "R", "the AWS-timestamped stdout witness; D16's single-laptop-store fallback |", "the AWS-timestamped stdout witness; D16's single-laptop-store fallback, which the ops lane switches to (recorded) if ledger POSTs fail twice in a row mid-build |"],
["17C-10", "I", "**Cut order, first cut first** (the build prompt: \"C9 first, then adversarial breadth\"):", " **Who and when:** the orchestrator applies items 1–4 on their triggers and reports at the next milestone; items 5 and 7 (and anything Must) need the captain at the next hold. Triggers, re-anchored by slip rule 0: items 1–2 when G2 passes its hard line; item 3 when the agents freeze after 06:00 (rule 2) or submit #1 isn't read back by 10:30; item 4 when submit #2 (or the merged final, rule 4) can't start its pack by 12:30; item 5 when Phase 3 starts after 12:00."],
["17C-10", "R", "Stage A by 03:45 (hard 04:15): the timeline above.", "Stage A by 03:45, hard 04:15 (after re-anchoring: t0 + 2.75 h, hard t0 + 3.25 h), as the timeline above; past the hard line the P2 rails and B-G3 stay out of the image (`rails-v2`, `guardrails/PLAN.md` §0.1) and J2's re-ask waits, without asking."],
["17C-11", "R", "If P7 runs, N2 waits until P5 leaves the window (about 15–20 min later); the preflight enforces it.", "If P7 runs (05:00), N1 and ADV-H-01 move ~10 min (`v1` waits for P7's result), and N2 waits until P5 leaves the window: the tokens allow it from ~05:38 (P3 out), the two-`observe`-S2 rule only from ~05:46–05:50. Then N3 runs ~06:00–06:10, N5 ~06:20, and submit #1 lands ~06:45–06:55: 5–15 min inside 07:00 and after 06:29, so the refresh is mandatory. The preflight enforces it."],
["17C-11", "R", "Ph1 · target ~05:30, projected ~06:20, at the latest 07:00", "Ph1 · target ~05:30, projected ~06:20 (~06:50 with P7; re-anchored by §4.6 rule 0), at the latest 07:00"],
["17C-12", "R", "(P5, N2, N3: two `observe` S2 runs + `enforce` runs ≈ 900K)", "(P5 300K + N1 60K + ADV-H-01 5K + N2 300K + N3's two attempts at CAP = 150K: 965K, 35K under the limit; with a CAP above ~167K, N3's second attempt waits until P5 leaves)"],
["17C-13", "R", "probes are paced at ≤ 0.5 req/s", "probes are paced at ≤ 0.4 req/s (24/min: a margin under 30)"],
["17C-13", "R", "(≤ 30 prompts at ≤ 0.5 req/s)", "(≤ 30 prompts at ≤ 0.4 req/s)"],
["17C-13", "R", "(paced ≤ 0.5 req/s for the 30 req/min limit)", "(paced ≤ 0.4 req/s, a margin under the 30 req/min limit)"],
["17C-13", "R", "RTM-2 (L-G5, ≤ 0.5 req/s)", "RTM-2 (L-G5, ≤ 0.4 req/s)"],
["17C-13", "R", "RTM-2 ≤ 30/min by pacing", "RTM-2 ≤ 24/min by pacing (0.4 req/s)"],
["17C-14", "IEOL", "| N1–N9, P1–P8, ADV-H-nn, ADV-R-nn |", "\n| Priority P0 … P5 (§3.9's Priority column; \"(P3+)\", \"(P4)\", \"P5 extras\"), the \"MIN / P2\" rail sets, \"console P1 / P2\" | Priority levels (P0 = must, P5 = first cut), the guardrails' rail sets and the console's view sets: **never a pilot**. A pilot is written \"pilot Pn\" wherever the two could meet | This plan; `guardrails/PLAN.md`; Arth's console plan |"],
["17C-14", "R", "2. P5 extras:", "2. Priority-5 extras (not pilot P5):"],
["17C-14", "R", "the INV control (P3+).", "the INV control (priority 3+)."],
["17C-14", "R", "*(P3+)* `inv.py`", "*(priority 3+)* `inv.py`"],
["17C-14", "R", "*(optional, P4)*", "*(optional, priority 4)*"],
["17C-15", "R", "| ~02:15 | PR-01 contracts merged", "| ~02:30 (realistic t0 + 2–2.5 h) | PR-01 contracts merged"],
["17C-15", "R", "is PR-00 (~01:45)", "is PR-00 (t0 + ~1.75 h, Gate G1)"],
["17C-15", "R", "first `submit.sh` by 13:15, final by 14:45", "submit #1 at Gate G5 (the 07:00 safety submit at the latest), #2 at G6 (by 11:30), the final at G7 (by 14:45)"],
["17C-15", "R", "| ops lane + captain | T4.8 | 2 × 15 min | S3 | 0 |", "| ops lane + captain | T4.8 | 3–4 × 15 min | S3 | 0 |"],
["17C-15", "R", "unless Arth is up at ~05:10 (DC-10)", "unless Arth is up in Hold-3 (05:00–05:20; DC-10)"],
["17C-15", "R", "the build prompt's ~05:30 also works; ", ""],
["17C-15", "R", "(the rolling check implies the build prompt's \"per clock hour\")", "(= the build prompt's \"any rolling 60 min\")"],
["17C-16", "R", "| 0 tok, 5 min | captain |", "| 0 tok, 5 min | captain (one B1 OK for S-1 + the probe, at the lane's start) |"],
["17C-16", "R", "| $0, 5 min | captain |", "| $0, 5 min | captain (the same B1 OK) |"],
["17C-16", "R", "| W (ledger) | 0 | pre |", "| W (ledger) | 0 | B1 OK (the captain) |"],
["17C-16", "R", "a person at the IDE lists the versions | W (S3) | 0 | pre |", "a person at the IDE lists the versions | W (S3) | 0 | B1 OK (the captain) + **act** (the IDE listing) |"],
["17C-17", "R", "the 2 remaining baseline runs (S2 `enforce`, S3) logged", "the top-up of §5.2 row 30 (P2 S1, P4 S3) logged only if n is short (an S2 `enforce` baseline run is not planned: it would need a hold if CAP > 150K)"],
["17C-17", "R", "| Phase 2 blocks; pre-authorized | ≈ 540K |", "| Phase 2 blocks; pre-authorized | ≤ 120K |"]
]
````

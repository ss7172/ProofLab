# 17c · Plan review: timeline and risk

- **Reviewer:** an independent reviewer subagent, one lens (timeline and risk). 2026-10-06, 01:37–02:04 UTC. All 59 fix anchors were checked against the plan as last modified at 01:28:33Z (one occurrence each).
- **Read:** `IMPLEMENTATION-PLAN.md` (all 675 lines); `BUILD-SESSION-PROMPT.md` (all 136 lines; file modified 01:34Z); memory `planning-handoff.md` (all), plus greps of `workshop-progress.md`, `platform-verified-facts.md`, `platform-observations-notes.md`, `hackathon-working-agreement.md` and `prooflab-project.md`; `ARCHITECTURE.md` §8 ("Overnight availability") and §12.1; `work/08` (the clock table, the HL-, OP- and TC- rows, the top risks); `work/05` (AR-04, AR-08, AR-11, AR-15, S-2); `guardrails/PLAN.md` §0, §4.1, §8; and `work/15`, "Open items for the lead".
- **Local read-only checks (~01:42Z):** `ls` found no `FEATURE-MAP.md`, no `reviews/`, no `.git/worktrees/` and no `tools/prototypes/`. The prototypes exist only in this session's scratchpad `h3/`. `pmset -g` shows `sleep 1`; `pmset -g assertions` shows only transient 300-second `caffeinate` assertions and `PreventUserIdleDisplaySleep 0`, so there is no `caffeinate -dimsu`. No git, AWS, cluster, ServiceNow or network call was made.

## Verdict
**Phase 1 can't meet its ~05:30 target, the 06:20 projection, or even the 07:00 bound with anything live.**

- At 01:45 the build hasn't started: no feature map, no worker, no ops lane, no `caffeinate`. The plan has no rule for a late start.
- Its "≤ 2.75 h to Stage A" contradicts its own Effort column (≈ 6 h; ≈ 4–4.5 h at AI pace, with the serial merge gates).
- It leaves the ops lane's non-★ Phase 1 PRs unscheduled, and two of them wait on Phase 2 PRs.

**My projection,** if the ★ chain launches at ~03:00 (after this review cycle, the fix pass and the commit; memory `planning-handoff.md`:62):

| Milestone | Projected UTC |
|---|---|
| Stage A (G2) | ~07:15 ± 45 min |
| Agents frozen (G3) | ~08:30 ± 45 min |
| `v1` (G4) | ~09:30 ± 45 min |
| Submit #1 (G5) | ~11:00 ± 60 min |

Each is about 45 minutes earlier if the chain launches now, and 1.5–2 h later at §3's own effort numbers.

**How I got the projection:**
- **t0 ≈ 03:00.** The three reviews end ~02:10; the fix pass and the commit take until ~02:45–03:00.
- **G2 = t0 + 4–4.5 h** (17C-02, at AI pace: about half of §3's agent-hours, 15–40 min per serial merge gate).
- **G3 = G2 + 45–60 min of lane** (S-2's 10-min record wait; the annotations). It is also bound by PR-08 and PR-11's freeze/pin merging. Those launch at PR-01's merge (~05:15) and need ~1.5–2.5 h plus gates (17C-03).
- **G4 = G3 + 50–60 min** (+15 with P7).
- **G5 = G4 + 70–90 min** (B4 + B5 + the pack; +20 with P7), and it needs PR-20a, PR-15 and PR-21a merged.
- Hold latency at 02:00–05:00 CDT adds 0–30 min.

**Top 3:**
1. Re-anchor the clock and launch now (17C-01, 17C-02).
2. The AWS refresh is coupled to Hold-2 and the slip rule, so it slides past 06:29:19 (17C-04).
3. The ops lane's PR prerequisites are missing, including PR-20 → PR-19 and PR-21 → PR-16 (17C-03).

**Counts:** ERROR 6 · GAP 4 · IMPRECISE 7.

### Rolling-hour budget (§5.2's ~UTC and Tok; tokens counted at each run's start; CAP = 150K, the plan's planning value; the window is (t − 60 min, t])

**Without P7:**

| Run (§5.2 row) | ~UTC | Bound | In the window before it | Sum incl. it | `observe` S2 in the window | Preflight |
|---|---|---|---|---|---|---|
| P1 (12) | 04:30 | 60K | S-2 10 + S-3 10 + S-4 20 | 100K | 0 | pass |
| P3 (13) | 04:38 | 60K | 40 + P1 60 | 160K | 0 | pass |
| P5 (14) | 04:45 | 300K | 40 + 60 + 60 | 460K | 0 → 1 | pass |
| N1 (17) | 05:15 | 60K | P1 + P3 + P5 = 420 | 480K | 1 | pass |
| ADV-H-01 leg A (18) | 05:22 | 5K | 480 | 485K | 1 | pass |
| N2 (20) | 05:27 | 300K | 485 | 785K | 1 → 2 | pass (215K left) |
| N3, 1st attempt (22) | 05:39 | 150K | P5 300 + N1 60 + ADV 5 + N2 300 = 665 | 815K | 2 | pass |
| N3, 2nd attempt (22) | ≥ 05:44 | 150K | 815 | **965K** | 2 | pass (35K left); **waits if CAP > ~167K**, until P5 leaves |
| N4 (23) | 05:50 | 60K | 665 (P5 out) | 725K | 1 | pass |
| N5 (24) | 05:58 | 60K | 725 | 785K | 1 | pass |

The peak hour is 04:45–05:44 at **965K** (the plan says "≈ 900K"). The clock-hour sums in §5.3 are right: 20K, 440K (740K with P7), 785K, 90K, 260K, 75K, 220K, 320K and 210K, total 2.42M (2.72M with P7). Phase 2's peak (07:10–08:10) is 325K, and Phase 3's (10:40–11:40) is 535K.

**With P7 (row 15, 05:00, 300K, `observe` S2):**

| Run | ~UTC | Sum incl. it | `observe` S2 | Preflight |
|---|---|---|---|---|
| P7 | 05:00 | S-4 20 + P1 60 + P3 60 + P5 300 + 300 = 740K | 2 | pass |
| N1 (`v1` waits for P7's result) | ~05:25 | 720 + 60 = 780K | 2 | pass |
| ADV-H-01 leg A | ~05:32 | 725K | 2 | pass |
| N2 at 05:32 | — | 725 + 300 = 1,025K | 3 | **fail** (tokens and count) |
| N2 at 05:38 (P3 out) | — | 665 + 300 = 965K | 3 | **fail** (count) |
| N2 | **~05:46–05:50** (P5 out) | 365 + 300 = 665K | 2 | pass |
| N3, two attempts | ~06:00–06:10 | ≤ 815K | 1–2 | pass |
| N4, N5 | ~06:12, ~06:20 | ≤ 785K | — | pass |

With P7, C7 ends at ~06:25 and submit #1 lands at **~06:45–06:55**: 5–15 minutes inside 07:00, and after 06:29:19. Neither §4.3 nor G5 shows this branch (17C-11).

**Requests:**
- S1/S3 runs ≈ 16/min; one `observe` S2 run ≈ 25/min (an estimate; OC-34). RTM-2 at 0.5 req/s is exactly 30 per 60 s, which leaves zero margin (17C-13).
- Runs over 150K: P5 and P7 (Hold-2), N2 and N3 (Hold-3), ADV-R-06 and ADV-R-06b (Hold-4), row 43 and the slot run (ask). All are covered except T1.8's pre-authorized "S2 `enforce`" baseline run, which appears nowhere in §5.2 (17C-17).

### Captain-acts table (CDT = UTC − 5; "Re-anchored" = my projection with t0 ≈ 03:00Z)

| Plan UTC | CDT | Act | Hold / authority | Re-anchored UTC (CDT) |
|---|---|---|---|---|
| ~01:00–01:10 | 20:00–20:10 | Messages to Arth (T0.9); `caffeinate -dimsu` and two alarms (T0.8); OK the venv installs (T0.5) and T0.7's repo write | captain (no hold) | now; **`caffeinate` was not running at 01:42Z** |
| 01:20–01:30 | 20:20–20:30 | S-1 (ledger write) and the bucket probe; **a person at the IDE lists the versions** | "captain" (§3.0) vs "pre" (§5.2); the IDE listing is an act | whenever the ops lane opens (21:00–22:00) |
| ~03:00 | 22:00 | SP-1 Cedar OK (also "at run time"); contact the organisers (OC-37) | **Hold-1** | 03:00–03:30 (22:00–22:30); SP-1 likely moves to Phase 2 (its texts are in PR-08) |
| before 04:27 | before 23:27 | **Risk ratings and appetite** (T1.5, B-G8); **registry values** (T1.4 "captain (values)") | **no hold** | by G3, ~08:30 (03:30) |
| 03:50, 04:10 | 22:50, 23:10 | Approval annotations: customer (row 6); IT and network (row 9) | act (Hold-2) | ~07:25, ~07:45 (02:25, 02:45) |
| 04:45 | 23:45 | P5 OK (> 150K) | Hold-2 | ~08:35 (03:35) |
| 04:45 | 23:45 | **AWS credential refresh at the Workshop Studio console** | act (Hold-2; alarm) | **fixed: 03:15–04:45 (22:15–23:45); must not move** |
| (05:00) | 00:00 | P7 OK, if needed | Hold-2 | ~08:50 (03:50) |
| 05:00–05:15 | 00:00–00:15 | `v1`'s APPROVED values; **the IDE version listing for T1** (row 16, G4); the T2 note if Arth is up | act (Hold-3; the IDE listing is in **no hold**) | ~09:15 (04:15) |
| 05:25–05:39 | 00:25–00:39 | Mode → `observe`; N2 OK; mode → `enforce`; N3 OK (rows 19–22) | Hold-3 | ~09:35–09:50 (04:35–04:50) |
| 05:45 | 00:45 | Backstop alarm | — | keep (the refresh check) |
| 06:30 | 01:30 | T2 for `v1`: the captain's APPROVED note (row 26) | act (**no hold**) | ~11:00 (06:00) |
| 06:35 | 01:35 | Assurance annotation (row 27) | act (Hold-4) | ~11:15 (06:15) |
| 07:30–08:10 | 02:30–03:10 | `v1.1` T2 note (row 31); C9 model swap and revert (rows 33–34) | act; Hold-4 | cut (slip rule 2) |
| 08:30 | 03:30 | SP-1, if it slipped (row 35) | Hold-1 (OK at run time) | ~12:00 (07:00), Should |
| ~11:00 | 06:00 | G-15 port-forward OK (T6.13, only if G-01–G-03 aren't READY) | captain | ~12:00 (07:00) |
| 10:30–11:40 | 05:30–06:40 | ADV-R-08 pause, ADV-R-06 and 06b, ADV-R-13, ADV-R-14 (rows 37–42) | Hold-4 (explicit OKs) | mostly cut |
| 12:00–13:30 | 07:00–08:30 | Recorded demo (T8.8); rehearsals (T8.7); row 43 "ask" | act; ask | ~13:30–14:15 (08:30–09:15), rehearsal 1 only |
| ~13:50 | 08:50 | Final submit (T8.9: "ops lane + captain") | pre | ≤ 14:45 (09:45) |
| after 15:00 | 10:00+ | DC-6 live run; the Cedar restore; AICT Execute Now (Arth) | ask; Hold-4 | credentials valid only to refresh + 12 h |

**The plan defines no sleep window.** Its acts run 20:00–00:45, 01:30–03:30, 05:30–08:50 and 10:00+ CDT. With the re-anchor, the only safe one is from the refresh (~23:00–23:45 CDT) to the projected G2 (~02:00 CDT), about 2–3 hours (17C-07).

### Single points of failure (Q4)

| SPOF | The plan's mitigation | Trigger | Owner | Verdict |
|---|---|---|---|---|
| The captain | R2: holds, pre-authorizations | none: no awake windows, hold timeouts or defaults | captain | GAP, 17C-07 |
| AWS credentials (06:29:19Z) | R3: refresh in Hold-2 at ~04:45; alarm at 05:45 | the alarm | captain | **ERROR**, 17C-04: coupled to Hold-2 and the slip rule |
| The merge gate's secret scan (fails closed) | the build prompt: queue merges, ask | "COULD NOT LOAD" | captain (refresh) | OK once 17C-04 is fixed: the build's merges then also run past 06:29 |
| Laptop sleep or reboot; `/tmp/modaas-token` | R19, T0.8: `caffeinate`, AC power, lid open; re-extract the token | "after any reboot" | T0.8 = captain; re-extraction: unnamed | GAP, 17C-09: T0.8 not done at 01:42Z |
| The one ops-lane session | §5.1: serialized lane; `live-lane-log.jsonl` | none | unnamed: no start time or restart rule | GAP, 17C-09 |
| The orchestrator's context window | T0.2 "lean" | none | none | GAP, 17C-09 |
| The ledger server (256Mi) | R8: per-CID exports; the D16 fallback | S-1's failure only; no trigger for a crash mid-build | ops lane | partial; folded into 17C-09 |
| The shared ServiceNow instance | R9: `selftest` before each batch; the guards | `selftest` fails | ops lane / Arth | OK |
| Arth | R2 (T2 on Sree alone), T8.7 (an AI tester), R14 (the AWS half) | "if Arth is away" has no time | captain | GAP, 17C-08 |
| This session's scratchpad (T0.7) | R15: "T0.7 now" | "now" (not done at 01:45) | lead | GAP, 17C-09 |

## Findings

### 17C-01 · ERROR · The build hasn't started, and the plan has no rule for a late start
- **Where:** §4.3, rows ~01:10 and 01:10–01:55 (B1: S-1 at 01:20, the bucket probe at 01:30) and Gate G1 (~02:00); §4.6, slip rule; §7, G1 "Blocks: the fan-out".
- **Evidence:**
  - The plan is anchored "'Now' = 00:40" (plan:56), and §4.2 says "The critical chain starts with the feature map at ~01:00, not after this plan's review" (plan:357).
  - STATUS (01:25Z): "Awaiting the 3 independent reviews" (plan:5).
  - Memory `planning-handoff.md`:62: "3 independent reviewers … → fixer → memory copy + secret scan + commit/push. The build then starts in a FRESH session".
  - At 01:42Z: no `FEATURE-MAP.md`, no `reviews/`, no `.git/worktrees/` (`ls`).
  - G1 needs PR-00 through the merge gate (plan:588), and PR-00 is T0.4 0.75 h + T0.5 0.25 h + T0.6 0.5 h + the T0.3 smoke 0.5 h (plan:141–144).
  - The slip rule reacts only to Stage A (plan:436).
- **Why it matters:** every time in §4.3, §5.2 rows 1–25, the holds and G1–G5 is about 2 hours stale before the first worker starts. G1 can pass no earlier than t0 + ~1.75 h. Because "G1 blocks the fan-out", a late B1 (no ops-lane session yet) also holds every non-★ PR.
- **Fix (exact):**
  - Anchor: §4.6, slip rule. Insert after: `**Slip rule:**`
    ```
    
    0. **Re-anchor at the start, then at each gate.** t0 = the time the orchestrator launches the ★ chain (planned 01:00; not launched at 01:45). At launch it writes t0 into the STATUS line and moves every Phase 1 time in §4.3, §5.2 rows 1–25, the holds and Gates G1–G5 by (t0 − 01:00). Three things never move: the AWS credential refresh (§5.1, Hold-2), the hard bounds (rule 4) and the 07:00 safety submit (rule 1). At each gate it re-projects submit #1 as G2 + 2 h 35 min (+ 20 min if P7 runs, + the hold latency) and reports it. The ops lane opens at t0 and runs B1 at once; it doesn't wait for the orchestrator.
    ```
  - Anchor: §7, G1 row, "Blocks". Replace: `| independent reviewer | the fan-out |` With: `| independent reviewer | the non-★ fan-out (B1's results block only PR-13's store choice, S-1, and the first freeze, the bucket probe) |`

### 17C-02 · ERROR · "≤ 2.75 h to Stage A" contradicts §3's Effort column and the merge-gate overhead
- **Where:** §4.2, "How Phase 1 fits"; §4.3, the Phase 1 header and the 03:45 row; §8.1, R1.
- **Evidence:**
  - §4.2: "It needs ≤ 2.75 h to reach Stage A by ~03:45" (plan:357).
  - Effort per ★ PR:
    - PR-01 = T1.1 "2.5–3 h" (plan:171).
    - PR-03 = T3.1 "2–2.5 h (+1.5 rails)" (plan:210), B-G2 "1–1.5 h", which depends on B-G1 (plan:191).
    - PR-05's MIN path = B-G1 "2.5–3.5 h" (MIN part ≈ half) + S-G1 "1.5 h" + S-G2 "1 h", all for one worker (plan:188–190, 549). `guardrails/PLAN.md` §0 asks for two workers: "A second worker runs the offline gates (S-G1, S-G2)".
    - PR-06 = T3.3 "3–4 h", which depends on T3.1 and T3.2 (plan:212) and merges after PR-02–PR-05 (plan:550, 572).
  - The merge gate per PR: DONE checks, the full tests, the scan, a fresh reviewer, panels for PR-01 and PR-02, Opus reviewers for PR-05 and PR-06, a squash merge, then the tests and the scan again on `main` (`BUILD-SESSION-PROMPT.md`:86–93). The merges are serial: PR-00 → PR-01 → PR-02 → PR-03, PR-04, PR-05 → PR-06 (plan:545, 572).
  - Fixer B: "W0 → W1 → W2 Stage A is a serial chain of about 4 h of wall clock even when split" (ARCHITECTURE.md:2082).
- **Arithmetic (from t0):**

  | Step | §3's Effort numbers | At AI pace (half the estimates) |
  |---|---|---|
  | PR-00 merged | t0 + 2.25 h | t0 + 1.5–2 h |
  | PR-01 merged | t0 + 3.25–3.75 h | t0 + 2–2.5 h |
  | PR-02 merged | +0.25–0.5 h | +0.25–0.5 h |
  | PR-04, PR-03, PR-05 merged | t0 + 4.5–5 h | t0 + 2.9–3.5 h |
  | PR-06 (0.5 h of integration after PR-05, plus the Opus gate) | t0 + 5.5–6 h | t0 + 3.8–4.3 h |
  | G2 | **t0 + 5.75–6.25 h** | **t0 + 4–4.5 h** |

  With t0 ≈ 03:00, G2 ≈ 07:00–07:30 at AI pace.
- **Why it matters:** every later Phase 1 time (G3–G5, Hold-2/3, Arth's T2 window) is built on 03:45. The slip rule then fires at once, and its 07:00 promise can't be met (17C-05).
- **Fix (exact):**
  - Anchor: §4.2. Replace: `It needs ≤ 2.75 h to reach Stage A by ~03:45 (Fixer B's estimate was 3.75 h with fewer workers); that is the main risk, and the slip rule (§4.6) handles it.` With: ``By §3's Effort column it needs about 6 h: PR-01 2.5–3 h; PR-03 3–4 h with B-G2; PR-05's MIN path about 4 h for one worker; PR-06 3–4 h, finished only after PR-03–PR-05 merge; plus seven serial merge gates of 15–40 min each. At AI pace (about half the estimates) it needs about 4–4.5 h. So Stage A ≈ t0 + 4–4.5 h, not t0 + 2.75 h. That is the main risk, and §4.6 rules 0–1 handle it. To shorten it, split PR-05 into the rails (B-G1 MIN) and the offline gates (S-G1, S-G2) as two workers, as `guardrails/PLAN.md` §0 asks.``
  - Anchor: §4.3, Phase 1 header. Replace: `**Phase 1: minimum submission (target ~05:30; projected 05:45–06:30)**` With: `**Phase 1: minimum submission (target ~05:30). The rows below are the optimistic case (t0 = 01:00, Stage A in 2.75 h), re-anchored at t0 by §4.6 rule 0. Plan against the realistic offsets: G1 = t0 + 1.75 h; PR-01 merged = t0 + 2–2.5 h; G2 = t0 + 4–4.5 h; G3 = G2 + 45–60 min; G4 = G3 + 50–60 min (+15 with P7); G5 = G4 + 70–90 min (+20 with P7)**`
  - Anchor: §4.1, Phase 1 bullet. Replace: `(target 4 h, **~05:30**; projected 05:45–06:30)` With: `(target 4 h, **~05:30**; 06:20 in the optimistic case, 06:50 with P7; realistic offsets in §4.3, re-anchored by §4.6 rule 0)`
  - Anchor: §8.1, R1. Replace: `Stage A by 03:45 needs the critical chain in ≤ 2.75 h (Fixer B estimated 3.75 h)` With: `Stage A needs the critical chain for about 4–4.5 h at AI pace (about 6 h by §3's Effort column; 2.75 h in the optimistic case; Fixer B 3.75 h)`

### 17C-03 · ERROR · The ops lane's non-★ Phase 1 PRs are unscheduled, and two wait on Phase 2 PRs
- **Where:** §6, the "After" column and the ★ note; §4.3, the "02:15–03:45 Phase 1 fan-out" row; §5.2, rows 5–25.
- **Evidence:**
  - "The rest launch once PR-01 merges (~02:30)" (plan:568), and the whole Phase 1 fan-out sits in "02:15–03:45" (plan:374).
  - The lane needs these PRs, each one worker:
    - PR-08, the script and the budget-guard preflight (§5.1: "in the preflight of every run", plan:454): "After PR-01, PR-09"; T3.5 is 3–4 h (plan:214, 552).
    - PR-09, which holds EP-0's `approval.py`: T1.3 is 4–5 h (plan:173).
    - PR-11: `v0-smoke` for S-3 (row 8), `v0-pilot` (row 11), risks, inventory and the experiment plan (T1.4 3–4 h + T1.5 1–1.5 h + T1.6 0.5 h + T1.9 0.5 h + B-G8 0.5 h ≈ **5.5–7 h**, plan:174–179, 555).
    - PR-12: T4.1 5–6 h + T4.2 1–1.5 h (plan:223–224).
    - PR-13, "After PR-01, **PR-12**": T4.3–T4.5 (plan:557).
    - PR-15, the CLI, "After PR-09, PR-13" (plan:559).
    - **PR-20, Ph1 `notify`, "After PR-01, PR-09, PR-19"**, where PR-19 is the Phase 2 Assurance runtime (plan:563–564). T6.5 depends on G-03 (plan:253).
    - **PR-21, the Ph1 pack, "After PR-12, PR-13, PR-16"**, where PR-16 is the Phase 2 projector (plan:560, 565). T4.8 depends on T5.3 (plan:230).
  - Taken literally, the chain PR-01 → PR-12 → PR-13 → PR-15 → PR-16 → PR-21 is about 21–29 agent-hours before submit #1.
- **Why it matters:**
  - S-2 (row 7) can't run without PR-08 and the collectors, S-3 needs PR-11's pin, and N2's notify needs PR-20. Submit #1 needs PR-15 and PR-21.
  - None of these is a G2 or G3 precondition. Read literally, the "After" cells push `notify` and the pack past Phase 2.
  - About 17 Phase 1 PRs also queue through one orchestrator's serial merge (10–15 min each), so the merge order must follow the lane's needs.
- **Fix (exact):**
  - Anchor: §6, ★ note. Insert after: `The rest launch once PR-01 merges (~02:30).`
    ```
     **"After" is the merge order, not the start:** every Phase 1 PR launches by PR-01's merge and codes against it and the ARCH text. **The ops lane needs these merged by the §5.2 row they gate** (a late PR holds only its row): PR-08 (the script, the budget-guard preflight, EP-0 with PR-09's `approval.py`), PR-11a (freeze and pin: `v0-smoke`, `v0-pilot`) and PR-12's Phase 1 collectors (spans, CR status, runtime logs, metrics) by row 7 (S-2); PR-09 (c16, c7, approval), PR-11b (risks, inventory, the experiment plan) and PR-13's store + ingest by row 11; PR-20a by row 20; PR-15's CLI, PR-21a and PR-22's minimal docs by row 25. **Phase splits:** PR-20a (Ph1: G-04's required keys, G-05's `notify` + the guards, G-20; after PR-01, PR-09) / PR-20b (Ph2: the analysis loop; after PR-19); PR-21a (Ph1: the minimal pack; after PR-12, PR-13) / PR-21b (Ph2: the union tree with the projection; after PR-16); PR-11a / PR-11b as above. The orchestrator merges Phase 1 PRs in this order before any Phase 2 PR.
    ```
  - Anchor: §6, PR-20 row, "After". Replace: `| PR-01, PR-09, PR-19 |` With: `| PR-01, PR-09 (PR-20b: + PR-19) |`
  - Anchor: §6, PR-21 row, "After". Replace: `| PR-12, PR-13, PR-16 |` With: `| PR-12, PR-13 (PR-21b: + PR-16) |`
  - Anchor: §4.3, row 02:15–03:45. Replace: `The Phase 1 fan-out (§6, tagged Ph1)` With: `The Phase 1 fan-out (§6, tagged Ph1; each PR merged by the §5.2 row it gates, §6; they land until about G2 + 1 h, not by 03:45)`

### 17C-04 · ERROR · The AWS refresh is coupled to Hold-2 and the slip rule, so a slip carries it past 06:29:19
- **Where:** §5.1, Hold-2; §4.3, row 04:25–05:00; §4.6, slip rule 1; §9, Credentials.
- **Evidence:**
  - "Hold-2 (~03:45–05:00, the B2/B3 sitting): … the AWS credential refresh (~04:45)" (plan:451).
  - Slip rule 1: "Each further 30 minutes moves the rest of Phase 1 by 30 minutes" (plan:436). The 04:25–05:00 row holds "the AWS credential refresh at ~04:45" (plan:379).
  - "without it every push stops, because the secret scan fails closed" (plan:673). Merge gate: "it needs live AWS credentials … If it fails only on 'COULD NOT LOAD' … no merge, no push" (`BUILD-SESSION-PROMPT.md`:88–89).
  - "a refresh at exactly 03:00 expires at exactly 15:00" (`work/08`:39).
- **Why it matters:** applied literally, a 1 h 45 min slip moves the refresh to 06:30. With my projection (G2 ≈ 07:15), Hold-2 opens after 06:29. The orchestrator's merges, not just the live work, stop at 06:29 until the captain wakes. A refresh before 03:00 fails the other way: the new expiry falls before 15:00.
- **Fix (exact):**
  - Anchor: §5.1, Hold-2. Replace: `the AWS credential refresh (~04:45).` With: `the AWS credential refresh (~04:45, **fixed to the clock**: between 03:15 and 05:00, never moved by the slip rule or with Hold-2, and asked on its own at the 04:45 alarm if Hold-2 hasn't opened. Before 03:00 the new expiry would fall before 15:00. The new expiry, refresh + 12 h, must cover the judging slot, else one more refresh before it).`
  - (§4.6 rule 0, from 17C-01, also lists the refresh as never moving.)

### 17C-05 · ERROR · Slip rule 1's 07:00 promise can't be met once Stage A passes ~04:40, and the hard bounds break after a late Phase 1
- **Where:** §4.6, slip rules 1 and 4; §1 DONE "at the latest 07:00"; Gate G5.
- **Evidence:**
  - Rule 1: "whatever Phase 1 has at **07:00 at the latest** is submitted (at least the C16 floor end to end)" (plan:436).
  - §5.2's own durations: G2 03:45 → N2 notified ~05:37 = **1 h 52 min**; the minimal pack + submit + readback ≈ 25 min (plan:473–493). So the C16 floor is in a 07:00 submit only if G2 passes by ~04:40.
  - Rule 4: "submit #2 by 11:30 at the latest" (plan:439). With submit #1 at ~11:00 (my projection), submit #2 at 11:30 is empty.
  - The same promise is in `BUILD-SESSION-PROMPT.md`:44–45.
- **Why it matters:** followed as written, at 07:00 the orchestrator must submit "at least the C16 floor", which doesn't exist yet (agents not frozen). The rule doesn't say what to submit instead, or what happens to submit #2.
- **Fix (exact):**
  - Anchor: §4.6, slip rule 1. Replace: `whatever Phase 1 has at **07:00 at the latest** is submitted (at least the C16 floor end to end), and the remainder rolls into Phase 2.` With: ``at **07:00 at the latest** a safety submit goes out with whatever Phase 1 has. It holds the C16 floor end to end only if Gate G2 passed by about 04:40 (G2 → N2's notify takes 1 h 52 min in §5.2, the pack about 25 min). Otherwise it is a curated pack: the register draft with `risks.yaml` and `inventory.yaml`, the gap list, the sketch and the README; no raw captures; the scan first. Phase 1 then continues, and its full submit #1 follows at Gate G5; the remainder rolls into Phase 2 only after that.``
  - Anchor: §4.6, slip rule 4. Replace: `**Hard bounds:** submit #2 by 11:30 at the latest;` With: `**Hard bounds:** submit #2 by 11:30 at the latest (if submit #1 lands after 10:00, submit #2 merges into the final submit);`

### 17C-06 · ERROR (cross-lens) · Gate G2 requires minimal J2, but PR-07 is outside the critical chain and depends on PR-06
- **Where:** §7, G2; §4.2, "Stage A only"; §3.3, T3.4; §6, PR-07 and the merge order.
- **Evidence:**
  - G2: "three trio bundles ≤ 24,000 chars each with the MIN rails and minimal J2" (plan:589). §4.2: "Stage A only goes into the image: MIN rails, minimal J2" (plan:358).
  - But T3.4 is "J2 (Stage B) … If Stage B slips, Stage A ships", with Deps "T3.3" (plan:213).
  - PR-07 isn't ★ and launches "once PR-01 merges" (plan:551, 568). The merge order has no PR-07 (plan:572).
  - The captain's Phase 1 includes "minimal judgment rules: S2 gather-evidence, S3 escalate" (`BUILD-SESSION-PROMPT.md`:35).
- **Why it matters:** as written, G2 waits on a PR that starts late and is chained behind PR-06, adding 1.5–2 h plus a gate and a re-bundle to the critical path. Otherwise G2 is waived silently.
- **Fix (exact):**
  - Anchor: §6, PR-07 row. Replace: `| PR-07 | **Ph1** · J2: JSON in the text answer, one re-ask, the precedence rules (bundled at Stage B) |` With: `| PR-07 ★ | **Ph1** · J2: JSON in the text answer + the precedence rules (minimal, in the Stage A image, Gate G2); the one re-ask at Stage B |`
  - Anchor: §6, ★ note. Replace: `launched first (PR-00 … PR-06)` With: `launched first (PR-00 … PR-07)`
  - Anchor: §6, "Serial, never parallel". Replace: `the critical chain's merge order: PR-01 → PR-02 → PR-03 + PR-04 + PR-05 → PR-06;` With: `the critical chain's merge order: PR-01 → PR-02 → PR-03 + PR-04 + PR-05 + PR-07 → PR-06;`
  - Anchor: §3.3, T3.4 row, "Deps". Replace: `| W2 worker → T2 worker | T3.3 | 1.5–2 h |` With: `| W2 worker → T2 worker | T1.1 (bundled by T3.3) | 1.5–2 h |`

### 17C-07 · GAP · No captain awake or sleep windows, no hold timeouts, and captain acts outside every hold
- **Where:** §5.1 (the four holds; "each with a recommended default (work continues while a hold waits)"); §8.1 R2; T1.4, T1.5, B-G8; §5.2 rows 3, 16, 26, 31.
- **Evidence:**
  - §5.1 promises "a recommended default" for each hold (plan:449) but never states one.
  - R2's mitigation lists the holds and `caffeinate` but no sleep window (plan:607). `work/08` HL-03 asked for one: "Finish P0 … by about 05:00 UTC, then use the cut lines … if a sleep window is needed" (`work/08`:86).
  - Acts that sit in no hold:
    - T1.5: "the appetite per risk (written before any pilot)", with the OK "owner's ratings" (plan:175). B-G8 also needs "owner's ratings" (plan:197), and T1.4's values are checked by the "captain (values)" (plan:174).
    - "a person at the IDE lists the versions" (row 3, plan:471), and "the IDE person lists versions" (row 16, plan:484). G4 requires "the IDE's version listing" (plan:591).
    - "the captain's APPROVED note" (rows 26 and 31, "pre + act", plan:494, 499).
  - The plan's acts (CDT): 20:00–00:45, 01:30–03:30, 05:30–08:50 and 10:00+ (see the captain-acts table above).
- **Why it matters:** the captain is the only approver, and the build runs overnight for him (20:35 → 10:00 CDT). With no stated window, he either never sleeps or misses a hold. A missed Hold-2 or Hold-3 stalls the serial lane with no rule. If a risk rating or an IDE listing is missing, `v0-pilot` or G4 waits silently.
- **Fix (exact):**
  - Anchor: §5.1, the end of the Hold-4 bullet. Insert after: `the Cedar restore after judging (DG-4).`
    ```
    
      - **When the captain must be awake, and what a waiting hold does.** Awake: (a) from t0 to the AWS refresh: the install and T0.7 OKs, B1's OK and the IDE listing, Hold-1, the risk ratings and appetite (T1.5, B-G8) and the registry values (T1.4); (b) from Gate G2 to submit #1: Hold-2 and Hold-3, including the IDE version listing for T1; (c) at Phase 2's start: Hold-4 and the T2 APPROVED note; (d) rehearsal 1 and the final submit. **Sleep is safe between (a) and (b):** nothing captain-gated runs there (merges are pre-authorized). The captain sets an alarm for the projected G2 (§4.6 rule 0), and the orchestrator plays a local alert (`say`) when G2's reviews start. **A hold unanswered for 20 minutes:** the lane runs only read-only steps and nothing that depends on it. No default ever replaces an annotation, an APPROVED note or the refresh: those wait. Hold-1's default: SP-1 moves to Phase 2, and the build works to 15:00. Hold-4's default: the item is not run (an unanswered C9 swap cuts C9's named runs, §4.6 item 3).
    ```
  - Anchor: §5.1, Hold-1. Replace: `contacting the organisers to confirm the deadline and the account's end (OC-37).` With: ``contacting the organisers to confirm the deadline and the account's end (OC-37); the owner's risk ratings and appetite (T1.5, B-G8) and the registry values (T1.4), needed before `v0-pilot`.``
  - Anchor: §5.1, Hold-3. Replace: `` `v1`'s APPROVED values; the mode switches for N2 `` With: `` `v1`'s APPROVED values and the IDE version listing for T1 (Gate G4); the mode switches for N2 ``
  - Anchor: §5.1, Hold-4. Replace: `**Hold-4 (~06:30, Phase 2 and 3):** the Assurance annotation;` With: `**Hold-4 (~06:30, Phase 2 and 3):** the Assurance annotation; the T2 APPROVED notes (§5.2 rows 26, 31);`

### 17C-08 · GAP · Arth: hours and time zone unconfirmed, his checks scheduled outside his hours, no "away" trigger
- **Where:** §4.3, row ~01:10 (his hours); T0.9; T1.6 (checker Arth, "before P1"); T1.7 ("Arth reviews → the captain approves → `v1`"); T6.8 and §1 ("Arth's export by 09:30"); G6 and G7 checkers; R2.
- **Evidence:**
  - Proposed hours: "05:00–05:20 for T2 if possible; 06:30–10:30 Phase 2; 12:00–13:30 rehearsals" (plan:371). Memory states no time zone for Arth, and `work/08`:260 still lists "his availability window and time zone" as an open ask.
  - T1.6 is to be "uploaded (T1) before P1", with checker "T1 worker → Arth" (plan:176). P1 is at 04:27–04:30 (plan:479–480), outside his hours.
  - T1.7 puts "**Arth reviews → the captain approves → `v1`**" (plan:177). §4.3, row 16 and DC-10 put `v1` at 05:00 without him (plan:124, 380, 484).
  - T6.8: "**at 09:30**" (plan:256), while G-02 is 06:35 in the plan (plan:495) and about 11:00 re-anchored.
  - The fallbacks have no trigger: "the Arth-unavailable fallback (T2 on Sree alone, labelled AI tester)" (plan:607), "if Arth is away" (plan:287). G7's 5-link hand-check has no fallback (plan:594).
- **Why it matters:** with any slip, his 06:30–10:30 window falls before Phase 2 starts. T1.6 and T1.7 then wait on a reviewer who isn't scheduled. The 09:30 AICT export can't include `ifabric_assurance_agent`, and nobody knows when "away" starts.
- **Fix (exact):**
  - Anchor: §3.1, T1.7. Replace: ``**Arth reviews → the captain approves → `v1` frozen + T1 + T2 (G-13) + pinned**`` With: ``**the captain approves → `v1` frozen + T1 + pinned; Arth's "reviewed" note and T2 (G-13) follow in Phase 2 unless he is up in Hold-3 (DC-10)**``
  - Anchor: §3.1, T1.6. Replace: `| T1 worker → Arth | T1.4, T1.5 | 0.5 h |` With: `| T1 worker → an independent reviewer before P1 (Arth's review follows with T2, labelled) | T1.4, T1.5 | 0.5 h |`
  - Anchor: §3.6, T6.8. Replace: `**at 09:30**, an optional refresh by 12:00` With: `**≥ 20 min after G-02 and by 12:00 at the latest** (09:30 holds only if G-02 is READY by ~09:00), an optional refresh before the final pack`
  - Anchor: §1, AICT box. Replace: `(Arth's export by 09:30)` With: `(Arth's export ≥ 20 min after G-02, by 12:00 at the latest)`
  - Anchor: §4.3, row ~01:10. Replace: `his hours (05:00–05:20 for T2 if possible; 06:30–10:30 Phase 2; 12:00–13:30 rehearsals)` With: `his time zone and hours (05:00–05:20 for T2 if possible; 06:30–10:30 Phase 2; 12:00–13:30 rehearsals), re-confirmed against the re-anchored clock (§4.6 rule 0)`
  - Anchor: §8.1, R2. Replace: `the Arth-unavailable fallback (T2 on Sree alone, labelled AI tester)` With: `the Arth-unavailable fallback (T2 on Sree alone, labelled AI tester; Arth counts as away when a request has no answer within 30 minutes, and the 5-link hand-check then falls to a non-builder AI reviewer, labelled)`

### 17C-09 · GAP · Single points of failure with no trigger or owner: the orchestrator's context, the ops-lane session, laptop sleep, the prototypes, the ledger mid-build
- **Where:** §8.1 (R8, R15, R19; no row for the orchestrator or the ops-lane session); T0.2, T0.7, T0.8; §9.
- **Evidence:**
  - T0.2 says "lean (state in `FEATURE-MAP.md` …)" (plan:140), but nothing restarts a full or dead orchestrator.
  - "The ops lane is a separate, serialized session that runs §5 only" (plan:659), with no owner, start time or restart rule. B1 at 01:15–01:30 needs it.
  - T0.8's `caffeinate -dimsu` (plan:146) wasn't running at 01:42Z: `pmset -g` shows `sleep 1 (sleep prevented by caffeinate, powerd, caffeinate)`, and the assertions are 300-second transients ("caffeinate asserting for 300 secs") with `PreventUserIdleDisplaySleep 0`.
  - R19: "re-extract the gateway token after any reboot" (plan:624) names no owner. The merge gate's scan also needs `/tmp/modaas-token` (`BUILD-SESSION-PROMPT.md`:88).
  - T0.7 is "lead, now" (plan:145), but `tools/prototypes/` is absent and `make_bundle.py`, `shim_analyzer.py` and `e2e_glue.py` exist only in the scratchpad `h3/bundle/`. PR-06 uses `make_bundle.py` as its template (plan:212).
  - R8 covers the ledger at S-1 only (plan:613).
- **Why it matters:** each of these stops the whole build at night with nobody assigned to notice. The orchestrator runs about 23 PRs over about 12 h. When the display sleeps (`displaysleep 10`), only transient assertions stand between the laptop and a one-minute idle sleep that kills every worker and the lane. Losing the scratchpad loses PR-06's and PR-19's template.
- **Fix (exact):**
  - Anchor: §8.1. New rows after row R19 (anchor: `re-extract the gateway token after any reboot |`):
    ```
    | R20 | **The orchestrator's context fills** over ~12 h and ~23 PRs | State lives in files (`FEATURE-MAP.md`, the STATUS line, `reviews/gates.jsonl`); at each gate, or when its context passes about 60 %, it writes a resume note, and the captain (or the lead) restarts it with `BUILD-SESSION-PROMPT.md` + "resume from FEATURE-MAP.md" |
    | R21 | **The ops-lane session** is never opened, dies or fills | The captain opens it at t0 (§4.6 rule 0; B1 doesn't wait for the orchestrator); `live-lane-log.jsonl` is its state; a restarted lane re-reads it and re-runs the preflight before any action |
    | R22 | **Laptop sleep before T0.8 is done** (at ~01:42Z `pmset` showed `sleep 1`, held off only by transient 300-s `caffeinate` assertions) | T0.8 at t0, checked by the orchestrator (`pmset -g assertions` shows the `caffeinate -dimsu` assertion); after a reboot the ops lane re-extracts the gateway token before any live step or merge, and the orchestrator resumes from its files |
    ```
  - Anchor: §8.1, R15. Replace: `| R15 | **Prototypes lost** with this session's scratchpad | T0.7 now |` With: ``| R15 | **Prototypes lost** with this session's scratchpad | T0.7 before the commit that precedes the build session (not done at 01:45: no `tools/prototypes/`; the files are only in the scratchpad's `h3/`) |``
  - Anchor: §8.1, R8. Replace: `the AWS-timestamped stdout witness; D16's single-laptop-store fallback |` With: `the AWS-timestamped stdout witness; D16's single-laptop-store fallback, which the ops lane switches to (recorded) if ledger POSTs fail twice in a row mid-build |`

### 17C-10 · GAP · The cut order names no owner or trigger, and "hard 04:15" has no consequence
- **Where:** §4.6, cut order items 1–7; slip rule 1, "hard 04:15".
- **Evidence:**
  - The cut order lists what goes, but not who decides or when (plan:426–433).
  - Stage A's "hard 04:15" (plan:436, 376; G2 "03:45 (hard 04:15)", plan:589) changes nothing: rule 1 moves Phase 1 by 30 minutes either way.
  - The build prompt: "Ask me only for holds and genuine decisions" (`BUILD-SESSION-PROMPT.md`:136).
- **Why it matters:** at 02:00–04:00 CDT, an orchestrator that doesn't know whether a cut is its call will either ask (and wait on a sleeping captain) or cut silently. A "hard" line with no consequence will be crossed with no action.
- **Fix (exact):**
  - Anchor: §4.6, cut order heading. Insert after: `**Cut order, first cut first** (the build prompt: "C9 first, then adversarial breadth"):`
    ```
     **Who and when:** the orchestrator applies items 1–4 on their triggers and reports at the next milestone; items 5 and 7 (and anything Must) need the captain at the next hold. Triggers, re-anchored by slip rule 0: items 1–2 when G2 passes its hard line; item 3 when the agents freeze after 06:00 (rule 2) or submit #1 isn't read back by 10:30; item 4 when submit #2 (or the merged final, rule 4) can't start its pack by 12:30; item 5 when Phase 3 starts after 12:00.
    ```
  - Anchor: §4.6, slip rule 1. Replace: `Stage A by 03:45 (hard 04:15): the timeline above.` With: ``Stage A by 03:45, hard 04:15 (after re-anchoring: t0 + 2.75 h, hard t0 + 3.25 h), as the timeline above; past the hard line the P2 rails and B-G3 stay out of the image (`rails-v2`, `guardrails/PLAN.md` §0.1) and J2's re-ask waits, without asking.``

### 17C-11 · IMPRECISE · The P7 branch is missing from §4.3 and G5, though the preflight forces it
- **Where:** §4.3, rows 05:00–06:30; §7, G5 "projected ~06:20"; §5.3, P7 bullet.
- **Evidence:**
  - §5.3: "If P7 runs, N2 waits until P5 leaves the window (about 15–20 min later)" (plan:532). §4.3 and G5 show only the no-P7 times (plan:380–383, 592).
  - My table above: with P7, N2's tokens are allowed from ~05:38, but the `observe` count allows it only from ~05:46–05:50. C7 then ends ~06:25, and submit #1 lands ~06:45–06:55.
- **Why it matters:** submit #1 would land 5–15 minutes inside the 07:00 bound and after 06:29, so a missed refresh then loses submit #1. The schedule hides this (17C-04).
- **Fix (exact):**
  - Anchor: §5.3. Replace: `If P7 runs, N2 waits until P5 leaves the window (about 15–20 min later); the preflight enforces it.` With: ``If P7 runs (05:00), N1 and ADV-H-01 move ~10 min (`v1` waits for P7's result), and N2 waits until P5 leaves the window: the tokens allow it from ~05:38 (P3 out), the two-`observe`-S2 rule only from ~05:46–05:50. Then N3 runs ~06:00–06:10, N5 ~06:20, and submit #1 lands ~06:45–06:55: 5–15 min inside 07:00 and after 06:29, so the refresh is mandatory. The preflight enforces it.``
  - Anchor: §7, G5 "when". Replace: `Ph1 · target ~05:30, projected ~06:20, at the latest 07:00` With: `Ph1 · target ~05:30, projected ~06:20 (~06:50 with P7; re-anchored by §4.6 rule 0), at the latest 07:00`

### 17C-12 · IMPRECISE · §5.3's tightest window is 965K, not ≈ 900K, and it depends on the CAP
- **Where:** §5.3, "The tightest rolling hour".
- **Evidence:**
  - The plan says "04:45–05:45 (P5, N2, N3 … ≈ 900K)" (plan:532).
  - Rows 14–22: P5 300K + N1 60K + ADV-H-01 5K + N2 300K + N3 at "2 × CAP (300K)" = **965K**, if N3's second attempt starts by ~05:44.
  - The cap is "150K … for planning" (plan:456), but "≤ the safety ceiling" (300K).
- **Why it matters:** the margin is 35K, not 100K. With a CAP above ~167K, the preflight holds N3's second attempt until P5 leaves (a few minutes, not shown). That's harmless, but the operator should expect it.
- **Fix (exact):**
  - Anchor: §5.3. Replace: `` (P5, N2, N3: two `observe` S2 runs + `enforce` runs ≈ 900K) `` With: `(P5 300K + N1 60K + ADV-H-01 5K + N2 300K + N3's two attempts at CAP = 150K: 965K, 35K under the limit; with a CAP above ~167K, N3's second attempt waits until P5 leaves)`

### 17C-13 · IMPRECISE · RTM-2 paced at 0.5 req/s is exactly 30 req/min, with no margin
- **Where:** §5.1, the requests rule; §5.2 row 42; L-G5; T7.2; §5.3, Requests.
- **Evidence:**
  - "probes are paced at ≤ 0.5 req/s" (plan:458), "(≤ 30 prompts at ≤ 0.5 req/s)" (plan:510) and "RTM-2 ≤ 30/min by pacing" (plan:533).
  - RTM-2 sends prompts "straight to `nemotron-super-120b`", one request each (`guardrails/PLAN.md`:97).
  - 30 prompts at 2.0 s spacing put 30 requests in one 60-second window. Any scheduler jitter makes it 31, over the captain's ≤ 30/min.
- **Why it matters:** this is a small but certain risk of breaking the lane limit on the one run designed to sit at it.
- **Fix (exact):**
  - Anchor: §5.1. Replace: `probes are paced at ≤ 0.5 req/s` With: `probes are paced at ≤ 0.4 req/s (24/min: a margin under 30)`
  - Anchor: §5.2, row 42. Replace: `(≤ 30 prompts at ≤ 0.5 req/s)` With: `(≤ 30 prompts at ≤ 0.4 req/s)`
  - Anchor: §3.2, L-G rows. Replace: `(paced ≤ 0.5 req/s for the 30 req/min limit)` With: `(paced ≤ 0.4 req/s, a margin under the 30 req/min limit)`
  - Anchor: §3.7, T7.2. Replace: `RTM-2 (L-G5, ≤ 0.5 req/s)` With: `RTM-2 (L-G5, ≤ 0.4 req/s)`
  - Anchor: §5.3, Requests. Replace: `RTM-2 ≤ 30/min by pacing` With: `RTM-2 ≤ 24/min by pacing (0.4 req/s)`

### 17C-14 · IMPRECISE · Priority labels "P0–P5" collide with the pilots P1–P8
- **Where:**
  - §4.6, cut order item 2 ("P5 extras", "the INV control (P3+)");
  - T1.10 "*(P3+)*" and T6.11 "*(optional, P4)*";
  - §3.9's Priority column (P0–P4);
  - "console P1/P2" (T5.5, cut order 2/4), "ADV-R-08 (the model pause; P2)" (T7.3), "the P2 rails" (§3.2);
  - and the §0 legend, which defines only "P1–P8" as pilots (plan:40).
- **Evidence:** cut order item 2, "P5 extras: the D8 mirror's laptop half; … the INV control (P3+)" (plan:428). P5 is also the S2 pilot that decides C16's breach lever (plan:482). "D8 mirror" and "D2-D" aren't defined in this plan.
- **Why it matters:** an orchestrator applying "cut item 2: P5 extras" at 03:00 CDT can read it as trimming pilot P5, the C16 lever. The cut order is exactly where ambiguity is most costly.
- **Fix (exact):**
  - Anchor: §0, legend. New row after the row containing `| N1–N9, P1–P8, ADV-H-nn, ADV-R-nn |`:
    ```
    | Priority P0 … P5 (§3.9's Priority column; "(P3+)", "(P4)", "P5 extras"), the "MIN / P2" rail sets, "console P1 / P2" | Priority levels (P0 = must, P5 = first cut), the guardrails' rail sets and the console's view sets: **never a pilot**. A pilot is written "pilot Pn" wherever the two could meet | This plan; `guardrails/PLAN.md`; Arth's console plan |
    ```
  - Anchor: §4.6, cut order item 2. Replace: `2. P5 extras:` With: `2. Priority-5 extras (not pilot P5):`
  - Anchor: §4.6, cut order item 2. Replace: `the INV control (P3+).` With: `the INV control (priority 3+).`
  - Anchor: §3.1, T1.10. Replace: `` *(P3+)* `inv.py` `` With: `` *(priority 3+)* `inv.py` ``
  - Anchor: §3.6, T6.11. Replace: `*(optional, P4)*` With: `*(optional, priority 4)*`

### 17C-15 · IMPRECISE · Times that disagree across sections, or cite a stale build prompt
- **Where and evidence:**
  - PR-01 merged "~02:15" (§4.3, plan:373) vs "(~02:30)" (§6, plan:568), and against its own 2.5–3 h effort (plan:171).
  - PR-00 "(~01:45)" (§4.4, plan:409) vs 1.5 h of effort plus the gate smoke (plan:141–144).
  - T8.9: "first `submit.sh` by 13:15, final by 14:45" and "2 × 15 min" (plan:289) is Fixer B's two-submit clock. §4.1 calls it superseded (plan:351), while G5–G7 give three submits.
  - Arth's T2: "~05:00" (DC-10, plan:124) vs "~05:10" (§4.2, plan:362) vs "05:00–05:20" (§4.3, plan:371).
  - §9: "the build prompt's ~05:30 also works" (plan:673). The prompt now says "Hold-2 (~04:45; backstop alarm 05:45)" (`BUILD-SESSION-PROMPT.md`:124).
  - §5.1: "(the rolling check implies the build prompt's "per clock hour")" (plan:456). The prompt now says "≤1.0M tokens in any rolling 60 min" (`BUILD-SESSION-PROMPT.md`:98).
  - §4.1 describes a TIMELINE block ("`v1` ~07:45 … the AWS refresh at ~05:30") that the current prompt no longer has (plan:351).
  - The §4.3 header and §4.1's "projected 05:45–06:30" are covered by 17C-02.
- **Why it matters:** a worker or the ops lane reading T8.9 or §9 takes a stale time. The 02:15/02:30 pair and the PR-00 time understate the chain.
- **Fix (exact):**
  - Anchor: §4.3, row ~02:15. Replace: `| ~02:15 | PR-01 contracts merged` With: `| ~02:30 (realistic t0 + 2–2.5 h) | PR-01 contracts merged`
  - Anchor: §4.4. Replace: `is PR-00 (~01:45)` With: `is PR-00 (t0 + ~1.75 h, Gate G1)`
  - Anchor: §3.8, T8.9. Replace: `` first `submit.sh` by 13:15, final by 14:45 `` With: `submit #1 at Gate G5 (the 07:00 safety submit at the latest), #2 at G6 (by 11:30), the final at G7 (by 14:45)`
  - Anchor: §3.8, T8.9. Replace: `| ops lane + captain | T4.8 | 2 × 15 min | S3 | 0 |` With: `| ops lane + captain | T4.8 | 3–4 × 15 min | S3 | 0 |`
  - Anchor: §4.2. Replace: `unless Arth is up at ~05:10 (DC-10)` With: `unless Arth is up in Hold-3 (05:00–05:20; DC-10)`
  - Anchor: §9, Credentials. Replace `the build prompt's ~05:30 also works; ` (with its trailing space) with nothing.
  - Anchor: §5.1, tokens. Replace: `(the rolling check implies the build prompt's "per clock hour")` With: `(= the build prompt's "any rolling 60 min")`
  - Anchor: §4.1, superseded list. Replace: `which predates the phases (by that prompt's own rule, on timings this plan wins; the refresh moves to ~04:45 inside Phase 1)` With: `in an earlier version of that prompt (the current one defers slot times to §4.3 and §4.6 and asks for the refresh in Hold-2, ~04:45)`

### 17C-16 · IMPRECISE · S-1 and the bucket probe: "captain" in §3.0, "pre" in §5.2
- **Where:** §3.0 SPIKES, the Approver cells of S-1 and the bucket probe; §5.2, rows 2–3, Authority.
- **Evidence:**
  - SPIKES: S-1 "| 0 tok, 5 min | captain |" and the bucket probe "| $0, 5 min | captain |" (plan:155–156).
  - §5.2: both "pre" (plan:470–471).
  - §0: "any cluster, AWS or ServiceNow write" needs the captain's OK (plan:54). The build prompt's pre-authorized list has neither (`BUILD-SESSION-PROMPT.md`:108–112).
  - Row 3 also needs "a person at the IDE".
- **Why it matters:** the lane either waits for an OK nobody scheduled, or writes to the judged bucket and the ledger without one. Both run when the captain is surely awake, so one batched OK settles it.
- **Fix (exact):**
  - Anchor: §3.0, S-1 row. Replace: `| 0 tok, 5 min | captain |` With: `| 0 tok, 5 min | captain (one B1 OK for S-1 + the probe, at the lane's start) |`
  - Anchor: §3.0, bucket-probe row. Replace: `| $0, 5 min | captain |` With: `| $0, 5 min | captain (the same B1 OK) |`
  - Anchor: §5.2, row 2. Replace: `| W (ledger) | 0 | pre |` With: `| W (ledger) | 0 | B1 OK (the captain) |`
  - Anchor: §5.2, row 3. Replace: `a person at the IDE lists the versions | W (S3) | 0 | pre |` With: `a person at the IDE lists the versions | W (S3) | 0 | B1 OK (the captain) + **act** (the IDE listing) |`

### 17C-17 · IMPRECISE · T1.8's baseline runs and tokens don't match §5.2 and §5.3
- **Where:** §3.1, T1.8; §5.2, row 30; §5.3, the 07–08 hour.
- **Evidence:**
  - T1.8: "the 2 remaining baseline runs (S2 `enforce`, S3) logged" with "≈ 540K", "pre-authorized" (plan:178).
  - §5.2 row 30: "P2 (S1), P4 (S3)" with 120K (plan:498). §5.3 07–08 is 260K in all (plan:525).
  - The build prompt asks for "any run likely to exceed 150K tokens" (`BUILD-SESSION-PROMPT.md`:116). An S2 `enforce` run is bounded by the CAP, which may exceed 150K.
- **Why it matters:** the budget table and the run list disagree by about 420K. A pre-authorized S2 baseline run could break the ASK rule.
- **Fix (exact):**
  - Anchor: §3.1, T1.8. Replace: `` the 2 remaining baseline runs (S2 `enforce`, S3) logged `` With: ``the top-up of §5.2 row 30 (P2 S1, P4 S3) logged only if n is short (an S2 `enforce` baseline run is not planned: it would need a hold if CAP > 150K)``
  - Anchor: §3.1, T1.8. Replace: `| Phase 2 blocks; pre-authorized | ≈ 540K |` With: `| Phase 2 blocks; pre-authorized | ≤ 120K |`

## Inconsistencies with BUILD-SESSION-PROMPT.md (report only)
1. **The refresh is tied to Hold-2.** `:124–125` says "ask me to refresh it in Hold-2 (~04:45; backstop alarm 05:45)", the same coupling as 17C-04. Nothing says the refresh is fixed to the clock when Hold-2 slides.
2. **The 07:00 promise.** `:44–45` says "Phase 1 submits whatever it has by 07:00 at the latest, at least C16's floor end to end". That is infeasible once Stage A passes ~04:40 (17C-05).
3. **Workflow time-box vs PR effort.** `:78` says "time-box each (≤45 min)" for the fan-out workflows. The plan's Phase 1 PRs carry 1–7 agent-hours each (§3), so a 45-minute time-box per worker would drop most PRs mid-task. It should bound the orchestration step, not a PR worker's life.
4. **When the build starts.** `:3` says "commit any uncommitted planning files first", and memory (`planning-handoff.md`:62) starts the build after the three reviews and the fixer. The plan's §4.2 starts the chain "at ~01:00, not after this plan's review". At 01:45 neither has happened.
5. **Hold defaults.** `:106` asks for holds "each with a recommended default", and `:61` says "Don't wait for me unless a hold is needed". Neither file says how long a hold waits or what the lane does meanwhile (17C-07). Neither names an awake or sleep window.
6. **The buffer.** `:42` asks for the "FINAL SUBMIT with ≥1 h buffer", while `:45` allows "the final submit by 14:45 at the latest". This is internal to the prompt; the plan carries both (§4.1 and §4.6 rule 4).
7. **The scan needs the token file.** `:88` says the scan "needs live AWS credentials and /tmp/modaas-token". After a reboot, merges stop until the token is re-extracted, and neither file names who does it (17C-09).

## Needs the captain (each with a recommended default)
1. **Launch the build now?** The ★ chain codes against ARCH §3.2, §4 and §7.1, not this plan (§4.2).
   - **Default:** yes. Make a checkpoint commit and open the orchestrator and the ops lane (B1: S-1 and the bucket probe) now. The fix pass lands as a second commit, which the orchestrator re-reads at G1. This saves about 45–60 minutes on every Phase 1 milestone.
2. **When to refresh the AWS credentials.**
   - **Default:** 03:15–04:00Z (22:15–23:00 CDT), right after Hold-1 and before any sleep. Never before 03:00Z, or the new expiry falls before 15:00. One more refresh only if the judging slot ends after refresh + 12 h.
3. **The 07:00 rule.**
   - **Default:** if G5 is projected after 08:00, make a curated safety submit at 07:00 (register draft, risks, inventory, gap list, sketch, README; scanned). Submit #1 then goes out at G5. If G5 lands after 10:00, submit #2 merges into the final submit (17C-05).
4. **Sleep.**
   - **Default:** sleep from the refresh until an alarm at the projected G2 − 15 minutes, about 2–3 hours (from ~23:00–23:45 to ~01:45–02:00 CDT). Then stay awake from G2 to submit #1 (~02:00–06:00 CDT), through Phase 2's holds, rehearsal 1 and the final submit (17C-07).
5. **Before sleeping, give the risk ratings and appetite (T1.5, B-G8), the registry values (T1.4) and the B1 OK.**
   - **Default:** yes, in Hold-1. Otherwise `v0-pilot` waits for him.
6. **Let the orchestrator apply cut items 1–4 on their triggers without asking (17C-10).**
   - **Default:** yes. Items 5 and 7 still come to him.
7. **Arth's time zone and hours against the re-anchored clock.**
   - **Default:** ask him to be reachable at the re-anchored G4 (~09:00–09:45Z) for the T2 review, and at ~11:00–13:30Z for Phase 2's AICT export and rehearsal 1. If he can't, use the labelled AI-tester fallback (17C-08).

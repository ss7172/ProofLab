# Presenter cheat sheet: team iFabric, ProofLab (10-minute slot)

One page for the presenter. Every answer below was checked offline on 2026-10-06 against a copy of the sealed
pack (`ops-lane/final/pack/evidence`, `manifest.py verify` = `OK`), with `python3 -m prooflab query ...` and the
console's own Ask parser. **If the screen differs from this page, the pack wins: say what the screen shows.**

## 1. The six named runs (type the full CID; `N1`, `N2b` are not accepted)

| Run | CID | What it shows | C16 (token cap) | C7 (event recording) | C9 (drift) |
|---|---|---|---|---|---|
| **N1** | `ifabric-run-1791294968-36d929` | The normal run. The inline budget guard (EP-1) halted three calls before they could overspend | SATISFIED 22,271 / 25,000 (14 calls, 3 inline DENY) | SATISFIED 55/55 | SATISFIED, largest change 41.45% (IT) vs ±75% |
| **N2b** | `ifabric-run-1791297942-c57210` | S2 "conflicting context" in observe mode: the guard *would* have halted twice, and the run still came in under the cap | SATISFIED 24,213 / 25,000 (headroom 787) | SATISFIED 47/47 | NOT_ASSESSED (C9 not declared for this run; not green) |
| **N2c** | `ifabric-run-1791301875-f821a3` | Third S2 attempt: no C16 breach; one network call blocked by the gateway guardrail | SATISFIED 14,063 | **BREACHED** 36/37 = 97.3% (gap-list B38, not notified) | NOT_ASSESSED (C9 not declared for this run; not green) |
| **N4** | `ifabric-run-1791299967-903ba1` | Declared fault: one IT tool-call record suppressed | SATISFIED 14,464 | **BREACHED** 43/44 = 97.73% → **INC0010351** | INDETERMINATE (C9 not declared for this run; not green) |
| **N5** | `ifabric-run-1791301189-1cc86f` | Re-test of N4 with the fault removed; closes the finding | SATISFIED | SATISFIED 45/45 (closes the N4 finding, 15:42:31Z) | INDETERMINATE (our slip: warm-up W5 used a stale versions file) |
| **N8** | `ifabric-run-1791300807-0ffaa0` | Declared treatment: IT model swapped super-120b → nano-9b | SATISFIED | SATISFIED | SATISFIED, IT −62.3% (faster) vs ±75%: **no breach** |

## 2. The three controls (register v1.1)

| Control | Version | Limit | Date proof (S3 write-once T1) |
|---|---|---|---|
| C16 per-run token cap (ACN-COST-001) | C16-v1.1 | ≤ 25,000 tokens per run (v1 was 20,000; declared change C16-cap/2 after N1b hit the cap) | 13:38:05Z |
| C7 event recording (AIA-LOG-001) | C7-v1 | 100% of expected events observed; gap ≤ 29,000 ms | 12:40:22Z |
| C9 drift and performance (AIA-ARC-006) | C9-v1 | ±75% latency vs the S1 baseline; errors 0 | 12:40:22Z |

**Approvals (all times 2026-10-06 UTC):**
- **v1:** frozen 12:39:29Z; owner approved on **INC0010321 at 13:02:37Z**, before every counted run.
- **v1.1:** frozen **13:36:43Z**, S3 T1 **13:38:05Z**; owner approval on **INC0010338 at 15:09:49Z, AFTER N1 and N2b**. They ran under v1.1 frozen and dated, not yet approved. The screen's "dated before the scope" cites the S3 T1, not the approval. Say this out loud.
- N4, N5 and N8 started after 15:09:49Z, so both approvals come before them (the N4 auditor view shows both).

## 3. The human loop (step 4)

N4 breaches C7 at 15:19Z → our code raises **INC0010351** to Sree (DELIVERED 15:22:43Z) → the iFabric Assurance agent
writes its analysis on the incident (15:23:10Z, nemotron-super-120b, 879 tokens) → re-test **N5** closes the finding
(15:42:31Z, RETEST_LINKED 15:42:34Z). The incident stays open for the owner: AWAITING_RESPONSE, cutoff 23:00Z.
Show it: `auditor ifabric-run-1791299967-903ba1`, section 2 WHAT.

## 4. Honest limits: say these before a judge finds them

- **C16:** we never produced a C16 breach. The inline guard held every time (N1: 3 DENY; N2b: 2 would-halt in observe mode). There is no C16 ticket and no C16 re-test.
- **C9:** the model swap (N8) made IT *faster* (−62.3%), still inside ±75%. No breach, no ticket; N9 (C9 re-test) dropped.
- **N2c C7 breach:** the missing event is a network model call that the gateway guardrail blocked. Our join cannot match a blocked call (gap-list **B38**). The verdict is kept and was not notified.
- **One human ServiceNow account** (the owner's), plus the integration service user. An approval shows which account acted, not which person (gap-list **B37**). The owner also builds; separation of duties is procedural only.
- **v1.1 was approved after N1** (15:09:49Z vs N1 at 13:56Z). N1 ran under the frozen, dated rule.
- **N5's C9 is INDETERMINATE**, our own slip (stale versions file in warm-up W5).

## 5. Ask box: type exactly, expect this

Dashboard = the console's Ask box (stored answers). CLI = `python3 -m prooflab query ask "<question>"` from the pack folder.

| Type exactly | Expected one-line answer | Where |
|---|---|---|
| `show me control 16 for run ifabric-run-1791294968-36d929 between 13:56:30Z and 13:57:00Z` | SATISFIED (whole-run verdict); in the window: 10 calls, 19,226 tokens, 9 ALLOW + 1 DENY at 13:56:57Z (25,182 projected > 25,000) | Dashboard + CLI |
| `control 16 for run ifabric-run-1791294968-36d929` | SATISFIED: 22,271 vs ≤ 25,000 tokens, evidence COMPLETE | Dashboard + CLI |
| `control 16 for run ifabric-run-1791297942-c57210` | SATISFIED: 24,213 vs ≤ 25,000 | Dashboard + CLI |
| `control 7 for run ifabric-run-1791299967-903ba1` | BREACHED (NOT SATISFIED): 97.73% vs ≥ 100% | Dashboard + CLI |
| `control 7 for run ifabric-run-1791301189-1cc86f` | SATISFIED: 100% (the re-test) | Dashboard + CLI |
| `control 7 for run ifabric-run-1791301875-f821a3` | BREACHED: 97.3% (say: B38 join limit) | Dashboard + CLI |
| `control 9 for run ifabric-run-1791300807-0ffaa0` | SATISFIED: 62.3% vs ≤ 75% (IT) | Dashboard + CLI |
| `control 9 for run ifabric-run-1791294968-36d929` | SATISFIED: 41.45% vs ≤ 75% (IT) | Dashboard + CLI |
| `auditor ifabric-run-1791299967-903ba1` (or `six questions for ifabric-run-1791299967-903ba1`) | Six questions; APPROVED shows v1 13:02:37Z and v1.1 15:09:49Z, both before 15:19:28Z; WHAT shows INC0010351 → analysis → N5 closure | Dashboard + CLI |
| `control 9 for window 2026-10-06T13` | SATISFIED: 0 breached of 2 (1 run, 1 hourly roll-up), evidence PARTIAL | Dashboard + CLI |
| `was control 16 satisfied between 2026-10-06T13:50:00Z and 2026-10-06T14:00:00Z` | SATISFIED: 0 breached of 1 counted run | **CLI only** (dashboard: "nothing stored") |

**Do not type these on the dashboard:**
- `control 9 for window 2026-10-06T15`: the dashboard shows the **13:00 answer** (known bug). Use the CLI: `python3 -m prooflab query --control C9 --window 2026-10-06T15:00:00Z..2026-10-06T16:00:00Z`, which gives INDETERMINATE.
- Short times without a date (`between 13:50Z and 14:00Z`) without a run: the CLI refuses ("needs the pack's event window"). Use full timestamps.
- `auditor INC0010351`: unknown. Use the run id.

**CLI equivalents** (from the unzipped pack, after `export PYTHONDONTWRITEBYTECODE=1`):
`python3 -m prooflab query --control C16 --run <CID>` · `--control C7 --run <CID>` · `--control C9 --run <CID>` ·
`--control C16 --window 2026-10-06T13:50:00Z..2026-10-06T14:00:00Z` · `--incident <CID>` · `--runs`

**Verify without us:** from the pack folder, `export PYTHONDONTWRITEBYTECODE=1 && python3 tools/manifest.py verify .`
prints `OK: every file matches MANIFEST.json`. Then any query above. In the browser: click a number, then "Verify without us".

## 6. If a judge asks…

- **"Was the rule dated before the run?"** Yes. C16-v1.1 has S3 write-once T1 13:38:05Z, before N1 at 13:56Z; C7-v1 and C9-v1 12:40:22Z. Version ids are on the answer screen.
- **"Who approved it?"** Sree, the owner, from her ServiceNow account: v1 on INC0010321 at 13:02:37Z; v1.1 on INC0010338 at 15:09:49Z, which is after N1 and N2b (we say so). One human account: B37.
- **"What happens on a breach?"** The verdict is computed after the run, our code raises a ServiceNow incident to the owner, the Assurance agent writes its analysis, and a re-test closes the finding (N4 → INC0010351 → N5). For C16 the inline guard refuses the call before it is made.
- **"How do I check this without you?"** `python3 tools/manifest.py verify .`, then `python3 -m prooflab query --control C16 --run <CID>`. Standard-library Python, no network. README section 4 shows how to recompute by hand.
- **"Is the dashboard a control?"** No. It shows and refuses nothing. **"Is ServiceNow in the agents' path?"** No. Tickets are raised after the check.

## 7. Level 1 live (step 2)

30 minutes before, on the Mac: `hk 'bash <repo>/tools/l1-checks.sh --live --out ~/l1-results.json'`; in the
Workshop Studio IDE terminal: `bash tools/l1-checks.sh --live --out ~/l1-results.json`. Either way the gateway key file
`/tmp/modaas-token` must exist there. Then `clear`. Rehearse with
`bash tools/l1-checks.sh --dry-run` (calls nothing). Four lines: L1-1 normal call through the gateway (CID +
action id; it FAILs loudly if the gateway log does not carry the CID), L1-2 attack blocked (`content_filter`, 0 tokens), L1-3 direct Bedrock refused (AccessDenied), L1-4 four
`ifabric-` AgentConfigs with approver and approval time. A FAIL line is information: read it out, don't hide it.
If asked "did you just create evidence?": the L1 calls use `ifabric-test-*` CIDs, after the sealed window; they are not in
the pack and change no verdict.

# 09 · Build order, hour budgets, acceptance tests

**Clock:** written 2026-10-05 ~19:00 UTC. Work stops **2026-10-06 15:00 UTC** (10:00 CDT), and judging starts then. That is about **20 hours**, including sleep.

**Rule 1: controls before console.**
- Axis 1 (completed controls) orders the field. A beautiful console over zero completed controls scores nothing.
- If time runs short, **cut console scope, never control scope.**

**Rule 2: run the console build in parallel.**
- The coding agent builds the console and query engine against `examples/` fixtures while the teammate does the live AWS work.
- The human reviews only at the checkpoints marked 👀.

**Rule 3: gates.**
- P0 must pass its acceptance tests before any P1 work starts.
- P1 must pass before any P2 work starts.

---

## 1. Tracks at a glance

```
UTC     19   21   23   01   03   05   07   09   11   13  14:00 15:00
Track A ██ register+capture ██ C16 e2e ██ runs ▒▒ C7 ██ C9 hrs ██ adversarial ██ pack ▒ seal │ JUDGING
 (T+CA)   (C9 baseline collection starts NOW: it needs closed hours)
Track B ░░ CA: query engine + console P0 (fixtures) ░░ 👀 ░ P1 ░ 👀 ░ (P2 only if A is green) ░ point at real pack
Track C ▒ Arth: Sree's register approval ▒ AICT evidence ▒ Assurance Agent live run ▒ incident tidy ▒
Track D                                                     rehearse ×2 ░░  final ░
```

---

## 2. Track A: the evidence pipeline (the score)

| # | Task | Owner | Hours | Depends | Done when |
|---|---|---|---|---|---|
| A0 | **Start C9 baseline capture now** (closed UTC hours; the metric and statistic declared in the draft register) | T | 0.3 | — | `raw/cloudwatch/baseline/*` growing hourly with query + capture time |
| A1 | Draft `register.yaml` from exploratory runs; add `policies/agent-policies.yaml` (AP-v1) and `expected/scenarios.yaml` + `expected/S1-3.yaml`; hand to Arth → Sree approval (`deliverables/thresholds/threshold-approval.md`) | T + A + S | 1.5 | A0 | `register/approval.md` shows APPROVED with sha; **no assessed run before this** |
| A2 | Capture jobs (`prooflab capture gateway --cid`, `ledger --cid`, `pdp`, `evidence --cid`, `cr-status`, `cloudwatch`) with sidecars and **capture-time redaction** | T + CA | 2 | — | `04-…` §2 checklist passes; `test_redaction.py` green |
| A3 | Normalizer + binder (gateway → `facts/gateway_calls.jsonl` → `records/C16/*.jsonl`) | CA | 1.5 | A2 | Records validate against `#/$defs/evidenceRecord`; dedupe tests green |
| A4 | `prooflab/evaluators/c16.py`: `test()` (control test) + `admit()` (evaluator), pure, register-driven | CA | 1 | A3 | Boundary tests (cap passes, cap+1 breaches), duplicates, corrections, missing calls → INDETERMINATE, blocked = 0 tokens; **no threshold literals** |
| A5 | `ifabric-run` orchestrator: CID in baggage, traceparent forwarded, EP3 handoff admission, run manifest, decision collection | T + CA | 1.5 | A4 | `runs/<cid>/run.json` validates; journey hops present |
| A6 | *(Option a, recommended if time allows)* Rebuild agents `ifabric-*`: structured decision output (`05-…` §4), ledger fields (trace_id, action_id, tokens, guardrail outcome), EP2 admission in `GatewayModel`, S2 policy + per-invocation call limit; Sree approves the CRs | T | 3 | A4 | New CR generation Approved + READY; an S1 smoke run produces decisions with policy checks |
| A7 | **Freeze → named runs**: C16 PASS + BREACH (+ re-test, + adversarial R5 halt if EP2 is built) | T | 1 | A1, A5 | `run-ids.txt` written with `written_at` |
| A8 | Publisher: assessment → Finding → `notify()` → `run_assurance_agent()` (`08-…` §5; finding keys §5.0) | T | 0.7 | A7 | Breach incident DELIVERED; Assurance note WRITTEN; case snapshot saved |
| A9 | **C7**: expected events + `c7.test()` + named runs | CA + T | 1.5 | A7 | AT-01 works for `control 7 for run <id>` |
| A10 | **C9**: `c9.test()` per closed window; one finding per crossing; a missing hour → monitoring-gap | CA + T | 1.5 | A0 | AT-01 works for `control 9 between T1 and T2` |
| A11 | Adversarial cases (Hostile + Rogue, `05-…` §7) with case files | T + A | 2 | A7 | ≥ 1 BROKE_FIXED and ≥ 1 BROKE_OPEN recorded honestly |
| A13 | **Real-time monitoring loop `prooflab watch`** (`05-…` §3A): follow gateway stdout, poll the ledger, run EP3 events, verdict on run end, C9 open/closed hours, human loop, ceiling, heartbeat → `live/events.jsonl` | CA + T | 1.5 | A3, A4, A8 | AT-20/21 green during a real run |
| A12 | `prooflab pack index` + MANIFEST + `submit.sh <team>` + readback | CA + T | 1 | all | AT-05 and AT-18 green on the downloaded copy |

**Cut order if late:**
1. A6, falling back to option (d): label C16 POST-RUN and EP2 NOT_BUILT;
2. A11 non-core cases;
3. C9 (keep its baseline and windows as INDETERMINATE with honest gaps);
4. never C16.

---

## 3. Track B: query engine and console (coding agent, against fixtures first)

**Install the design skills first** (in the coding agent's environment, not the workshop IDE):
```bash
npx -y skills@latest add https://github.com/dammyjay93/interface-design --skill interface-design -g -a claude-code -y
npx -y skills@latest add https://github.com/nextlevelbuilder/ui-ux-pro-max-skill --skill ui-ux-pro-max -g -a claude-code -y
```

Before writing UI code:
1. Load `interface-design` and follow its "Before writing each component" checkpoint, using the tokens in `06-…` §2.
2. Use `ui-ux-pro-max` only for targeted checks, e.g. `python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "focus visible keyboard" --domain ux`.

**Copy, don't reinterpret:** `demo/index.html` is the reference implementation of the tokens, components and views. Split it into `static/app.css` and `static/app.js` (no inline script or style, so CSP holds).

### P0: minimum winning console (~3 h coding agent + 30 min human review). Nothing in P1 starts until AT-P0 passes.
| # | Task | Hours | Files | Tests first (TDD) |
|---|---|---|---|---|
| B0 | Package skeleton `prooflab/{query,console,pack,policy}`, `__main__` dispatch, fixtures loader | 0.2 | `prooflab/cli.py` | CLI `--help` lists commands |
| B1 | **Query grammar** (deterministic, no LLM) + answer composer + one-screen text renderer: `prooflab controltest 16 --run FM-B`, `prooflab ask "Show me control 16 for run FM-B"`, window and interval forms | 1.0 | `prooflab/query/{grammar,answer,render_text}.py` | Every phrase in `06-…` §6 parses; unknown phrases give a helpful error; same answer twice → same `answer_id`; boundary verdicts |
| B2 | Console server: stdlib `ThreadingHTTPServer`, loopback-only, one-time token → session cookie, Host allow-list, CSP and headers, GET-only API over the pack, path allow-list | 0.6 | `prooflab/console/server.py` | AT-07, AT-08, AT-09, AT-06 (`test_console_server.py`) |
| B3 | UI P0: shell (top bar with Ask ⌘K, mode, integrity; exhibit rail; inspector drawer) + **Answer** + **Evidence Ledger** (+ Log→Evidence) + **Six Questions** + **Register** (date-before-test ribbon) + **Gaps** + integrity badge | 1.2 | `prooflab/console/static/{index.html,app.js,app.css,icons.svg,fonts/}` | AT-01–AT-05, AT-10, AT-12, AT-14 (Playwright or manual script below) |
| 👀 | Human review: run the demo questions on the fixtures; compare with `demo/index.html` | 0.5 | | |

### P1: strong (~2 h)
| # | Task | Hours |
|---|---|---|
| B4 | **Overview** (claim tree with (a)–(g) completeness, Judging L1–L3 strip, named runs with `written_at`, six artefacts, environments) | 0.4 |
| B5 | **Agent Trail** (journey map, decision cards with evidence + policy checks, outcome validation) + run lane | 0.6 |
| B6 | **Human loop**: embed the v3 drop-in panel over `/api/v1/cases` (`08-…` §7.2, §8.7); link strip per card (thread chips, Answer →, Six questions →); `#/loop/<id>`; `servicenow:` refs open the case (`06-…` §5.7) | 1.0 |
| B7 | **Adversarial** matrix, **Architecture** page (EP table from `pack-index`, transports, modes, five habits) | 0.4 |
| B9 | **Live Monitor** (`06-…` §5A): tail `live/events.jsonl` (SSE, with polling fallback), live lane + Σ budget meter + inline decisions + journey progress + provisional C9 + human-loop ticker + ceiling headroom + stream health | 0.8 |
| B8 | **Present mode** (8-step run of show, 15:00 timer, ←/→) + thread highlighting | 0.3 |

### P2: stretch (only if Track A is green)
- Operator mode + actuator (`02-…` §5.1; kinds RUN_CONTROLTEST, SERVICENOW_CHECK, PACK_SEAL, PACK_SUBMIT).
- Offline viewer inside the pack (`evidence/viewer/`, `file://`, plus in-browser SHA-256 check of a selected folder).

---

## 4. Acceptance tests (run them; paste the output into the decisions log)

| ID | Test | How | Pass |
|---|---|---|---|
| **AT-01** | The 2-minute question | A person **not on the build** types each judge phrase (`06-…` §6) into the Ask bar and into the CLI | The answer screen shows rule, version, date, owner, population, measured vs limit, exceptions, verdict, gaps, records, human-loop line and AICT line; elapsed < 2 s (console) and < 10 s (CLI) |
| AT-02 | Date before test | Open the Register and the answers for every named run | `date_before_scope = true` everywhere; the ribbon shows freeze < approval < first assessed run |
| AT-03 | Population | C16 for a breach run | expected = observed = matched, missing 0 (or an honest INDETERMINATE with reasons) |
| AT-04 | Resolvable records | Click any record in the Answer or Ledger | The inspector shows the raw line, capture command, captured_at, sha256 and MANIFEST status; the sha recomputes |
| **AT-05** | Tamper detection | Copy the pack, edit one raw line, start the console on the copy | Red **PACK MODIFIED** banner listing the file; answers labelled UNVERIFIED; `manifest.py verify` exits 1 |
| **AT-06** | No secrets reach the browser | `grep -rEi "AKIA\|ASIA\|bearer [a-z0-9]\|tkn[=]\|AUDIT_WRITE_TOKEN=\|client_secret" ` over `static/`, every API response (scripted), and the pack; run `pre-push-secret-scan.sh` | 0 hits |
| AT-07 | Security headers | `curl -sI` on `/` and `/api/v1/pack` | CSP as in `07-…` §3, `nosniff`, `no-referrer`, COOP, CORP, `frame-ancestors 'none'`; no inline script |
| AT-08 | DNS-rebinding and auth | `curl -H 'Host: evil.example'` → 403; no session cookie → 401; POST → 405 in PACK mode | as stated |
| AT-09 | XSS as data | Fixture incident note `<img src=x onerror=alert(1)>` and agent rationale `<script>` | Rendered as literal text |
| AT-10 | Closure only by re-test | Fixture finding marked CLOSED without `retest_ref` | The console shows **"CLOSED WITHOUT RE-TEST"** in red (and `prooflab pack index` fails validation) |
| AT-11 | No threshold literals | `pytest prooflab/tests/test_no_threshold_literals.py` | Green: no registered limit value appears as a literal in evaluator code |
| **AT-12** | Six questions | Pick any incident in the event window | All six cards render with status and resolvable refs; PARTIAL/GAP link to gap ids |
| AT-13 | Agent Trail | Open each named run | Journey, decisions (with cited evidence + policy checks) and outcome validation present; **no reasoning text anywhere** (grep for `<think` → 0) |
| AT-14 | Determinism | Ask the same question twice, CLI and console | Identical `answer_id` |
| AT-15 | Keyboard-only | ⌘K → type → Enter → Tab through the answer → Esc | Everything reachable; visible focus; no traps |
| AT-16 | Provenance | Include an EXPLORATORY run in the pack | It appears greyed with a chip and never changes a verdict |
| AT-17 | Offline | Disconnect the network; run the console in PACK mode | All P0 views work (fonts self-hosted or a system fallback) |
| **AT-18** | S3 readback | Download the submitted zip, unzip, `python3 tools/manifest.py verify .`, start the console on it | OK + green integrity badge showing the S3 key, ETag and time |
| **AT-20** | Real-time latency | Start a named run with the watcher and the console in LIVE mode | Each gateway call appears ≤ 5 s after its gateway timestamp; each EP2/EP3 decision ≤ 5 s; the run verdict ≤ 60 s after run end; the incident ≤ 60 s after a breach verdict |
| AT-21 | The monitor monitors itself | Stop the watcher mid-run | **STALE** banner ≤ 30 s, naming the stream; no stale value is shown as current |
| AT-22 | The Human Loop tells the same story | Open `#/loop`, then `#/loop/INC0090216`; hover its finding id | Every case in pack-index `cases[]` renders; numbers equal the Answer view's; INC0090216 shows Policy 8/8 with P6 naming the re-test; a forged note shows untrusted; a REFUSED run shows its reason in red; unknown is never green; the hovered id lights in every view's chips |
| AT-19 | Judge taxonomy | Search the UI for "Level" | Judging L1–L3 and Alert 0–2 are never mixed |

**AT-P0** = AT-01…AT-12 + AT-14. **AT-P1** = AT-13, AT-15, AT-16, AT-19, **AT-20, AT-21** (real-time monitoring), **AT-22** (Human Loop). **AT-final** (evening before, then again at 14:00 UTC) = everything + AT-17 + AT-18.

---

## 5. Definition of done for the whole entry (14:00 UTC checklist)
- [ ] `register.yaml` frozen + approved before the first assessed run; same version for every named PASS and BREACH run.
- [ ] Completeness (a)–(g) green for **C16**, then C7, then C9 (the Overview shows it).
- [ ] `run-ids.txt` written with time, before judging; pack index lists it.
- [ ] Every breach and escalation has an incident assigned to Sree; at least one RESPONDED and one NO_RESPONSE_OBSERVED; Assurance notes present or honestly REFUSED.
- [ ] Gap list merged (Section A + B), with statuses updated.
- [ ] `architecture.md` (or the whiteboard photo) includes the EP table with honest status.
- [ ] Pack sealed, submitted, read back, verified (AT-18); console started on the **downloaded** copy for judging (PACK mode).
- [ ] Rehearsed twice with someone outside the build asking the judges' exact questions (`presentation/JUDGING-DAY-GUIDE.html`).

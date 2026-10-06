# FEATURE-MAP.md: team iFabric build (orchestrator-owned)

**Purpose.** The build's single source of truth for PRs. Each PR has a phase, owned paths that do not overlap, executable DONE checks, dependencies, a worker model and effort, a review lens, a merge order and a needed-by slot. Seed: `IMPLEMENTATION-PLAN.md` §6 (PR-00…PR-22), refined by `BUILD-SESSION-PROMPT.md` STEP 1, by the wave-1 briefs as launched (these are authoritative for PR-00…PR-07 and override §6 where they differ), and by the plan reviews `architecture/work/17a-plan-review-infra.md` and `17b-plan-review-judging.md`. Only the orchestrator edits this file. Workers read it and never write it.

**Times (UTC, Tue 2026-10-06).** Drafted ~02:10Z. Wave 1 launched ~01:55Z. **The 15:00Z deadline is confirmed** (OC-37 closed). **The final submit is at 14:00Z**: ≥ 1 h of buffer, and the plan's 14:45 is the slip bound only.

**Captain's directions folded in (after the plan was written):**
- **01:40Z: the ServiceNow register approval (T2, C-7, G-13) moved INTO Phase 1**, right after the `v1` S3 write-once freeze (T1). §5.2 row 26 now runs at ~05:05 in block B3/B4, before N1. As a result, PR-11's `approval-finding.json` generator and PR-20a's `kind: approval` notify (with its own absolute log `evidence/register/approval/delivery-log.jsonl`) are Phase 1. T1 still dates `v1` (D5); T2 corroborates.
- **C16 `observe`/`enforce` switches on our own `ifabric-` agents are pre-authorized.** §5.2 rows 19 and 21 leave Hold-3, so Hold-3 keeps only `v1`'s APPROVED values and note and the > 150K runs.
- The deadline is confirmed (15:00Z) and the final submit is 14:00Z (above).

**Status legend:** `building` (a worker is on it in its worktree) · `queued` (spec ready, no worker yet) · `review` (DONE checks claimed; the independent reviewer is running) · `fix` (the reviewer or gate found a failure) · `merged` (squash-merged to main; sha recorded) · `cut` (dropped under the §4.6 cut order and recorded in the gap list).

---

## PR status table (orchestrator updates this)

| id | phase | status | branch | merged sha |
|---|---|---|---|---|
| PR-00 | 1 | merged | PR-00-setup | 28a3629 |
| PR-01 | 1 | merged | PR-01-contracts | 3baa674 |
| PR-02 | 1 | merged | PR-02-c16core | ae48d81 |
| PR-03 | 1 | merged | PR-03-modelcall-hook | 1f7e8b5 |
| PR-04 | 1 | merged | PR-04-emit | d8694c5 |
| PR-05 | 1 | merged | PR-05-rails | c7436f1 |
| PR-06 | 1 | merged | PR-06-bundler-trio | 4be4797 |
| PR-07 | 1 | merged | PR-07-j2 | 8648f72 |
| PR-00b | 1 | merged | PR-00b-gate | f209c7c |
| PR-25 | 1 | merged (integration) | PR-25-integration | a278f43 |
| PR-26 | 1 | merged (build carrier) | PR-26-build-carrier | 769b07a |
| PR-24 | 1 | merged | PR-24-cedar-texts | cb03cd7 |
| PR-11 | 1 | merged | PR-11-registry | 8358e39 |
| PR-08a | 1 | merged | PR-08a-orchestrator | a985c2c |
| PR-09a | 1 | merged | PR-09a-evaluators | 401b435 |
| PR-12a | 1 | merged | PR-12a-collectors | ee4aac4 |
| PR-13a | 1 | merged | PR-13a-store-stitch | 94b9e6c |
| PR-23 | 1 | merged | PR-23-ep2-replay | 495cef3 |
| PR-20a | 1 | merged | PR-20a-notify | e88084e |
| PR-15a | 1 | merged | PR-15a-query-cli | 5d13d6d |
| PR-21 | 1 | merged | PR-21-pack-build | 7b8bd1d |
| PR-22a | 1 | merged | PR-22a-docs-min | 13216c9 |
| PR-19 | 2 | merged | PR-19-assurance-runtime | 561111f |
| PR-17 | 2 | merged | PR-17-console-p0 | ea64bd6 |
| PR-16 | 2 | merged | PR-16-projector | bfb13ce |
| PR-15b | 2 | queued | PR-15b-answer-grammar | |
| PR-20b | 2 | queued | PR-20b-humanloop-loop | |
| PR-12b | 2 | queued | PR-12b-collectors-ph2 | |
| PR-13b | 2 | queued | PR-13b-corroboration | |
| PR-10 | 2 | merged | PR-10-recheck | 7dc1f68 |
| PR-14 | 2 | merged | PR-14-watch | 75881e3 |
| PR-09r | 2 | queued | PR-09r-risk | |
| PR-05b | 2 | queued | PR-05b-rails-v2 | |
| PR-22b | 2→3 | queued | PR-22b-docs-full | |
| PR-18 | 3 | queued | PR-18-console-p1 | |
| PR-09b | 3 | queued | PR-09b-adv-r06-change | |
| PR-08b | 3 | queued | PR-08b-tamper-tally | |
| PR-09i | 3 (cut first) | queued | PR-09i-inv | |

---

## Orchestrator decisions (binding; 02:50Z)
- **D-A.** The rails' "≤ 6 KB raw" budget is advisory, not a DONE check. The binding size rule is the bundle gate: `len(base64(gzip -9n(file))) ≤ 24,000` per `agents/*/ifabric-*.py`. PR-05's own size check: `rails.py` gz+b64 ≤ 6,144 chars. (Captain asked why a raw budget exists: it was only a proxy for the compressed budget.)
- **D-B.** Agent packaging is **two-stage** (ARCH §7.1 fallback; work/05 AR-03). Measured 02:45Z: one role's bundle is ~33K gz+b64 even stripped, against 24K. A shared base bundle `agents/ifabric-base/ifabric-base.py` (loader + `c16_core` byte-identical with its sha marker + the shared runtime) is built once (`ifabric-base-<sha>`), then each role bundle `agents/ifabric-<role>/ifabric-<role>.py` is built `FROM <repo>@<base digest>`. Each file ≤ 24,000; each buildspec ≤ 25,600. Four CodeBuild runs instead of three. New PR **PR-00b** (gate rules for this layout and the Assurance bundle's C16 exemption).
- **D-C.** The rails modes are `enforce` | `observe` only (no `off`).
- **D-D.** PR-01's contract is the single schema. Optional fields justified by ARCH (EP-3 before/after, EP-4 judgment, lifecycle, the rail's intended action in observe mode) are added there; adapters fold everything else into reason/detail.

---

- **D-B' (03:30Z, supersedes D-B's FROM-digest step):** the ImageBuildRole has no `ecr:GetDownloadUrlForLayer`, so the base/role files both ride in ONE build per role as StartBuild env-var overrides (probe PASSED 03:29Z: 46,548 chars in one value). Gate: ≤ 44,000 chars of env values per build. PR-26 = `tools/ifabric_build_request.py` + `tools/build_ifabric_image.sh`.

## Merge gate (BUILD-SESSION-PROMPT.md STEP 3, every PR, before it merges)

1. Run the PR's DONE checks (below) and the full test suite: `bash tools/gate.sh` (PR-00), which runs every `tests/<dir>` in its venv, `prooflab/tests` (152 + ours) and the static searches.
2. Run the secret scan on the staged tree: `bash /Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/workshop-local/scripts/pre-push-secret-scan.sh <dir>` must print `RESULT: clean`. If it fails only on `COULD NOT LOAD` (expired credentials or a reboot): no merge and no push. Commit in the worktrees, queue the merges and ask the captain. Never bypass the scan.
3. An **independent reviewer** checks each DONE check with evidence and looks for contract breaks. The reviewer is a fresh subagent and never the author. PR-01 and PR-02 get a panel. The reviewer also runs `git diff --stat main...HEAD` and confirms that **only the PR's owned paths** changed (the overlap rule below).
4. Run the fix loop until everything is green.
5. Squash-merge to main (`git fetch` first; stop if main moved unexpectedly). Then re-run `tools/gate.sh` and the scan on main.
6. Update this table, and add a line to `reviews/gates.jsonl`. A failed check never merges.

**Merge order.** Wave 1: **PR-00 → PR-01 → PR-02 → PR-03 / PR-04 / PR-05 / PR-07 (any order) → PR-06** (PR-06 bundles PR-07's minimal J2, per 17b-01). Wave 2 (Phase 1), in needed-by order: **PR-24 → PR-11 → PR-08a / PR-09a (whichever is green first; PR-08a does not wait for PR-09a) → PR-12a → PR-13a → PR-23 → PR-20a → PR-15a → PR-21 → PR-22a**. Phases 2 and 3 then follow the priority order in the Waves list.

**Waves.**
- **Wave 1** = PR-00…PR-07, launched ~01:55Z, the critical chain to Stage A (Gate G2, 03:45, hard 04:15).
- **Wave 2** = the Phase 1 PRs not in wave 1 (PR-08a, 09a, 11, 12a, 13a, 15a, 20a, 21, 22a, 23, 24). They launch **when PR-01 merges**, in needed-by order, up to the 10–12 worker cap. Specs: scratchpad `wave2-specs.json`.
- **Phase 2/3 PRs run on spare workers only**, in this priority: **PR-19** (Opus; the Assurance runtime is needed at 06:35) → PR-17 (console P0, ~4 h, against Arth's fixtures) → PR-16 → PR-15b → PR-20b → PR-12b → PR-13b → PR-10 → PR-14 → PR-09r → PR-05b → PR-22b → PR-18 → PR-09b (merged only after the ADV-R-06 break) → PR-08b → PR-09i (cut first).

---

## Rules every worker follows

**R1 · Layout.** Agent-runtime code that gets bundled into the single-file agents lives at **repo-root `adapters/runtime/`**. That is how wave 1 was launched, and it is authoritative. **Everything laptop-side lives under `prooflab/`**, following ARCH §3.0, because the judge runs `python3 -m prooflab query` from the unzipped pack, so the tool's code must import as `prooflab.*` (17a). §6's bare `adapters/orchestrator/`, `adapters/platform_ops/`, `adapters/collectors/`, `store/`, `stitch/` therefore mean **`prooflab/adapters/orchestrator/`, `prooflab/adapters/platform_ops/`, `prooflab/adapters/collectors/`, `prooflab/store/`, `prooflab/stitch/`**. EP-2's replay is `prooflab/adapters/postrun/` (PR-23), and the human-loop glue is `prooflab/adapters/human_loop.py` (PR-20a).

**R2 · Shared `__init__.py` files, one owner each.**

| File | Owner |
|---|---|
| `adapters/__init__.py`, `adapters/runtime/__init__.py`, `prooflab/evaluators/__init__.py`, `prooflab/registry/__init__.py` | PR-01 (as briefed) |
| `prooflab/adapters/__init__.py` (new; shared by PR-08a, 12a, 20a, 23) | **PR-01, added via SendMessage while it is open; else an orchestrator pre-commit on main before wave 2 launches** |
| `prooflab/adapters/orchestrator/__init__.py`, `prooflab/adapters/platform_ops/__init__.py` | PR-08a |
| `prooflab/adapters/collectors/__init__.py` | PR-12a |
| `prooflab/adapters/postrun/__init__.py` | PR-23 |
| `prooflab/store/__init__.py`, `prooflab/stitch/__init__.py` | PR-13a |
| `prooflab/query/__init__.py` | PR-15a |
| `prooflab/pack/__init__.py` | PR-21 (PR-16 adds modules beside it and does not edit it) |
| `prooflab/humanloop/__init__.py` | PR-20a (PR-19 owns `invoke.py` only) |
| `prooflab/recheck/__init__.py`, `prooflab/watch/__init__.py`, `prooflab/console/__init__.py` | PR-10, PR-14, PR-17 |
| `prooflab/__init__.py` | already on main; nobody edits it |
| `prooflab/cli.py`, `prooflab/__main__.py` (the one dispatcher, G-19) | PR-01. Each later PR exposes `main(argv)` in its own module for the verb PR-01's dispatcher routes to, and never edits `cli.py`. A missing route goes to the orchestrator as a one-line follow-up |

**R3 · The a/b split rule.** Where a later row has to change the earlier row's file (PR-09b → `prooflab/evaluators/c16.py`; PR-20b → `prooflab/adapters/human_loop.py`; PR-05b → `adapters/runtime/rails.py`, `egress.py`; PR-08b → `prooflab/adapters/orchestrator/run.py`; PR-22b → `evidence-templates/`, gap-list section B), **the b-row inherits those paths only after the a-row merges, and the two never run at the same time.** Everywhere else, the a and b rows own disjoint files.

**R4 · Tests.** Each PR has its own `tests/<dir>/` at the repo root. Run it from the repo root with `python -m pytest -q -p no:cacheprovider tests/<dir>`. Use `PY39=~/firstmate-homes/TrustworthyAI/workshop-local/.venv-py39/bin/python` (3.9 + pytest, for `prooflab/` stdlib code and the stdlib runtime modules) and `PY312=~/firstmate-homes/TrustworthyAI/workshop-local/.venv-strands312/bin/python` (3.12 with the pinned Strands stack, for agent code). **Test file basenames must be unique across the repo**: name them `test_<dir>_*.py`. There is no `tests/__init__.py`, so a duplicate basename collides under pytest's default import mode. Fixtures are derived from `workshop-local/evidence-snapshots/20261005T173727Z/` and Arth's `evidence-console-plan/examples/`, never copied raw, and kept in `tests/<dir>/fixtures/`.

**R5 · Offline.** Workers make no AWS, cluster or ServiceNow call. They never read `~/.prooflab-snow.env`, and they source `env.sh` only through the scan. Live I/O is wrapped in a subprocess or HTTP seam that tests stub. There are no threshold literals in code: values live only in `register/*.yaml`. Evaluators stay stateless, and the registry is never in the path.

**R6 · Ops-lane outputs are not PR-owned.** The ops lane or the orchestrator writes these and the orchestrator commits them: `run-ids.txt`, `evidence/named-runs.md`, `evidence/window.json`, `evidence/adversarial/log.jsonl`, `evidence/register/approval/*`, `register/versions/*`, `register/pins/*`, `register/inventory/*` (frozen artefacts), `register/experiments/experiments.jsonl`, `live-lane-log.jsonl`, `reviews/gates.jsonl`, `reviews/*.md` records, `sketch.png`, `architecture/*`, this file and the plan.

---

## Needed-by (from plan §5.2; why the Phase 1 wave-2 order is what it is)

| §5.2 row · slot | Needs merged |
|---|---|
| 4 · SP-1 (Hold-1, ~03:00; texts reviewed by ~02:45) | **PR-24** |
| 5–7 · CodeBuild ×3, first apply, S-2 (03:45–03:55) | PR-06 (+ PR-01…05, PR-07); **PR-11** `pinned.py` (the first-apply pin: `IFABRIC_PIN_JSON` + `_SHA256`); **PR-08a** (`--only`, envelope, CID, session id, preflight, `deploy_wrapper` EP-10 record); **PR-12a** `aws_spans`, `runtime_logs`, `agentcore_metrics` for the S-2 assertions |
| 8 · S-3 halt proof (04:00) | PR-11 `v0-smoke` pin; PR-08a's deploy wrapper |
| 10 · freeze record + `inv-1` (04:25) | PR-11 `inventory.py` |
| 11 · `v0-pilot` + T1 (04:27) | PR-11 `freeze.py` / `pinned.py`; `register/experiments/plan.md` (PR-11) |
| 12–15 · P1, P3, P5 (04:30–05:00) | PR-08a preflight (the rolling 1.0M, ≤ 2 `observe` S2 per hour); PR-12a; PR-13a ingest |
| 16 · `v1` derive + freeze + T1 (05:00) | PR-11 `derive.py`; PR-09a `approval.check_versions` (the echo and the EP-0 check) |
| **26 → ~05:05 · T2 approval Finding (now Phase 1)** | PR-11 `approval_finding.py`; **PR-20a** `kind: approval` notify on its own absolute log |
| 17–22 · N1, ADV-H-01 leg A, N2 + notify, N3 (05:15–05:45) | PR-09a (`approval.py`, `c16.py`); **PR-23** (EP-2 replay); PR-08a `--condition prompt-attack`; PR-13a; PR-20a |
| 23–24 · N4, N5 (05:50–06:00) | PR-09a `c7.py`; the `suppress-record` fault inside the pin (PR-11); PR-20a |
| 25 · submit #1 (~06:20) | **PR-21**, **PR-15a**, **PR-22a**, PR-12a redaction (T-REDACT-01), PR-13a |
| 27–28 · the Assurance agent (06:35) | **PR-19** (Phase 2, first spare worker) |

---

## The rows

Notation: `$PY39` / `$PY312` as in R4. "pytest D" means `$PY -m pytest -q -p no:cacheprovider tests/D` → all pass, 0 errors. "Scan" means the STEP 3 scan prints `RESULT: clean`. "Diff-scope" means `git diff --stat main...HEAD` lists only the owned paths.

### Wave 1 (Phase 1, launched ~01:55Z; status `building`)

#### PR-00 · Ph1 · Setup: Arth's code, the gate, the manifest tool, the rescued prototypes
- **Owns:** `prooflab/servicenow/`, `prooflab/tests/`, `handoffs/ifabric-handoff-3/REWORDED.md`, `tools/gate.sh`, `tools/manifest.py`, `tools/tests/`, `tools/prototypes/`, `tests/gate/`
- **DONE (executable):**
  - `$PY39 -m pytest -q -p no:cacheprovider prooflab/tests` → `152 passed`
  - `diff -r handoffs/ifabric-handoff-3/code/prooflab/servicenow prooflab/servicenow` and the same for `…/code/prooflab/tests` vs `prooflab/tests` → empty (Arth's code byte-identical)
  - `$PY39 tools/manifest.py verify handoffs/ifabric-handoff-3` → exactly 2 changed files (`evidence-console-plan/04-LOGS-TO-EVIDENCE.md`, `09-BUILD-ORDER-AND-ACCEPTANCE.md`). `REWORDED.md` lists both with their before and after sha256.
  - pytest `tools/tests` and pytest `gate` pass. Each planted violation makes `bash tools/gate.sh` exit ≠ 0: a threshold literal in `prooflab/evaluators/`, `adapters/` or `agents/`; `evaluate` imported outside `adapters/runtime/model_call.py`; an embedded core sha256 ≠ `register/c16_core.sha256`; a bundle > 24,000 chars; the AT-06 secret pattern (assembled from parts). `bash tools/gate.sh` exits 0 on main.
  - These files exist: `tools/prototypes/assurance/{make_bundle.py,shim_analyzer.py,e2e_glue.py,agent_A_analyzer_only.py,stub/}`, `tools/prototypes/assurance/bundletest/{conftest.py,pytest.ini,agent_C_all_modules_loader.py}`, `tools/prototypes/servicenow/repro_bugs.py`. `$PY312 tools/prototypes/assurance/e2e_glue.py` prints `WRITTEN`.
  - Scan · Diff-scope
- **Deps:** none · **Worker:** Sonnet · medium · **Review lens:** 152 on 3.9; Arth's code byte-identical; every gate check fails on its planted violation · **Merge:** 1st · **Gate:** G1

#### PR-01 · Ph1 · Shared contracts + test scaffold + the one dispatcher (G0.2, G-19)
- **Owns:** `prooflab/contract/`, `prooflab/registry/__init__.py`, `prooflab/registry/parse.py`, `prooflab/__main__.py`, `prooflab/cli.py`, `prooflab/evaluators/__init__.py`, `adapters/__init__.py`, `adapters/runtime/__init__.py`, `tests/conftest.py`, `tests/contract/`, `pytest.ini` (+ `prooflab/adapters/__init__.py` if added by SendMessage, R2)
- **DONE:**
  - pytest `contract` on `$PY39`. It covers: the schema `ifabric.evidence/1` and its validator; `record_kind: rail_decision` without `rail.id` → rejected; `outcome.real: CANCELLED_RAIL` accepted; EP-14/15/16 are valid `ep.id`s; a rail verdict inside an assessment → rejected; CID families and baggage/session/handoff ids round-trip (`prooflab.contract.ids`); the register schema with per-control versions and the pin format.
  - Kit parity: a test loads the kit's `evaluate.py` register loader on our flat `register.yaml` fixture and reads controls `16`, `7`, `9`.
  - Finding contract: a fixture finding built per the contract passes `prooflab.servicenow.finding.finding_from_dict`.
  - App data format: `prooflab/contract/schema/*.json` exists (record, assessment, register, pack-index/answer types), and Arth's `examples/answer.C16.run.FM-B.json` validates.
  - `$PY39 -m prooflab --help` exits 0 and lists the verbs; an unknown verb exits 2.
  - `grep -rnE '^(import|from) (yaml|requests|boto3)' prooflab/contract prooflab/registry` → none (stdlib only)
  - Scan · Diff-scope
- **Deps:** PR-00 (merge order) · **Worker:** **Opus · high; reviewer panel (Opus)** · **Review lens:** contract breaks; kit parity; 3.9; every verb routed · **Merge:** 2nd (target ~02:15) · **Gate:** G2

#### PR-02 · Ph1 · The c16 core (frozen before the agent build)
- **Owns:** `prooflab/evaluators/c16_core.py`, `tests/c16_core/`, `register/c16_core.sha256`
- **DONE:**
  - pytest `c16_core` on `$PY39` **and** `$PY312`. It covers: cap passes; cap + 1 breaches (DENY); the bound fallback when neither projected nor last call is known; `enforce` → `limit_applied: cap` and `observe` → `safety-ceiling`; `action: halt` iff committed + reserved + bound > limit.
  - `shasum -a 256 prooflab/evaluators/c16_core.py | cut -d' ' -f1` == the content of `register/c16_core.sha256`
  - `grep -nE 'open\(|socket|subprocess|time\.time|datetime\.now|global ' prooflab/evaluators/c16_core.py` → none; imports are stdlib only
  - `bash tools/gate.sh` finds no threshold literal · Scan · Diff-scope
- **Deps:** PR-01 (text) · **Worker:** **Opus · high; reviewer panel (Opus)** · **Review lens:** the decision table vs ARCH §3.4; no I/O or state; frozen after merge (any change = a new agent build) · **Merge:** 3rd

#### PR-03 · Ph1 · EP-1 model-call adapter, tally, hook dispatcher, `guarded_check` (T3.1, B-G2, B-G3)
- **Owns:** `adapters/runtime/model_call.py`, `adapters/runtime/action_id.py`, `adapters/runtime/tally.py`, `adapters/runtime/hooks.py`, `tests/runtime_c16/`
- **DONE:**
  - pytest `runtime_c16` on `$PY312`, i.e. **T-C16-01**: cancel path, Strands 429 retry re-entry, bound fallback, both modes, concurrency, outage; usage from `message["metadata"]["usage"]` (0/0 → UNKNOWN); `max_retries=0` recorded; a halt → `escalate c16-budget-halt`.
  - The S-G1 seven cases pass against the **real** adapter (B-G2; one dispatcher per event in the order rails → C16 → emit). A stub S1-like run emits 1–4 rail records per agent.
  - `grep -rlE 'import .*evaluate|evaluate\(' adapters/` → only `adapters/runtime/model_call.py`
  - B-G3 (if it fits): a C16 DENY → BLOCK `c16-deny`; `content_filter` → BLOCK
  - Scan · Diff-scope (**must not include `adapters/__init__.py` or `adapters/runtime/__init__.py`**: see the overlap findings)
- **Deps:** PR-01, PR-02 · **Worker:** Sonnet · medium · **Review lens:** the only importer of `evaluate`; T-C16-01 · **Merge:** 4th (any order with 04/05/07)

#### PR-04 · Ph1 · Emit client, tool and judgment adapters, duplicate guard, fail-closed start-up, O-04 (T3.2, B-G4)
- **Owns:** `adapters/runtime/emit_client.py`, `adapters/runtime/tool_call.py`, `adapters/runtime/judgment.py`, `adapters/runtime/startup.py`, `tests/runtime_emit/`
- **DONE:**
  - pytest `runtime_emit` on `$PY312` (and `$PY39` for the stdlib parts). It covers: **T-DUP-01** (a second invocation with the same session → `lifecycle duplicate-invocation`); an outage spools to stdout and recovers; the end-of-invocation flush is ≤ 2 s with p99 printed; a stub unenveloped invocation emits a "no envelope" record with an `ifabric-unenveloped-…` CID and `UNATTRIBUTED`; start-up with `IFABRIC_PIN_JSON`, `IFABRIC_PIN_SHA256` or the gateway key missing → fails closed; a record holding a test secret's exact value comes out scrubbed, exception text included (O-04); compact ALLOW (DG-3).
  - Scan · Diff-scope (no `adapters/__init__.py` or `adapters/runtime/__init__.py`)
- **Deps:** PR-01 · **Worker:** Sonnet · medium · **Review lens:** T-DUP-01; the bounded flush; never raises · **Merge:** 4th

#### PR-05 · Ph1 · The rails (MIN), RT-03 egress, S-G1, the S-G2 golden set, the RTM-1 corpus scaffold
- **Owns:** `adapters/runtime/rails.py`, `adapters/runtime/egress.py`, `tests/rails/`, `evidence/adversarial/corpus/`
- **DONE:**
  - pytest `rails` on `$PY39` and `$PY312`: a unit test per MIN rail (I-01, I-02 `secret.*` + `pii.*` at ingress per DG-2, I-03, X-01, X-02, X-03 normalisation, T-02, T-03, O-03, O-04, O-05, RT-01)
  - **S-G2 golden set:** a test over the S1–S3 payloads, the frozen `conflicting-context` text and locally generated tool outputs → **0 BLOCK, 0 FLAG** except the expected T-02 FLAGs and X-03 MODIFYs. The printed report reproduces the counts in guardrails §1.6.
  - `wc -c < adapters/runtime/rails.py` ≤ 6144 (MIN; ≤ 10240 with P2)
  - The start-up record echoes `rail.policy_sha256`
  - RT-03 (if in the Ph1 image): an injected `urlopen("http://example.invalid")` → exactly one FLAG
  - Scan · Diff-scope (no `adapters/__init__.py` or `adapters/runtime/__init__.py`)
- **Deps:** PR-01 · **Worker:** **Opus · high (Opus reviewer)** · **Review lens:** false positives; ≤ 6 KB; DG-1…DG-3 · **Merge:** 4th · P2 rails and the full corpus → **PR-05b** (R3)

#### PR-07 · Ph1 · J2 minimal (Stage A, per 17b-01): JSON in the text, the precedence rules; the re-ask may wait
- **Owns:** `adapters/runtime/j2.py`, `tests/j2/`
- **DONE:**
  - pytest `j2` on `$PY39` and `$PY312`: one test per precedence rule (freeze or restricted → `escalate`; empty evidence → `gather-evidence` naming the evidence; element ids → site ids via X-03); JSON-in-text parse of `disposition`, `deciding_evidence`, `reversible_step`, `reason` (+ `named_evidence_needed`, `proposed_action`); an invalid answer → one re-ask, then `escalate invalid-structured-output` (the re-ask may be stubbed in Stage A)
  - `grep -n 'structured_output' adapters/runtime/j2.py` → none
  - Scan · Diff-scope
- **Deps:** PR-01 · **Worker:** Sonnet · medium · **Review lens:** precedence; never `structured_output()` · **Merge:** 4th (**before PR-06**)

#### PR-06 · Ph1 · The single-file bundler, the generator wrapper, the Docker harness, the trio (T3.3, B-G6)
- **Owns:** `tools/bundle_agent.py`, `tools/make_ifabric_agents.py`, `tools/docker_smoke/`, `agents/ifabric-customer/`, `agents/ifabric-it/`, `agents/ifabric-network/`, `tests/bundle/`
- **DONE:**
  - `$PY312 tools/bundle_agent.py` writes `agents/ifabric-{customer,it,network}/ifabric-<role>.py`. For each, `$PY39 -c "import gzip,base64,sys;print(len(base64.b64encode(gzip.compress(open(sys.argv[1],'rb').read()))))" <file>` ≤ **24000**.
  - The embedded c16 core's sha256 == `register/c16_core.sha256`, and the embedded modules (contract, c16 core, `adapters/runtime/*` incl. MIN rails + minimal J2) are byte-identical to the repo files (a test in `tests/bundle/`)
  - pytest `bundle` on `$PY312`: the generator refuses an output named `agent.py`, any reference image tag and `approve=True`; CR names match `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`; env values in the server-dry-run-shaped CR are strings and include `IFABRIC_RAILS_MODE=enforce`, `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_unredacted_attributes=` and the pin pair; `IMAGE_TAG=ifabric-<role>-<git sha>` with a per-agent `URI_FILE`
  - `tools/docker_smoke/` run (local arm64 `docker build` of the exact Dockerfile + stub OpenAI-compatible server): `GET /ping` → 200 and `POST /invocations` → an answer, for all three. Log attached to the PR.
  - `find agents -name agent.py` → empty · Scan · Diff-scope
- **Deps:** PR-02, PR-03, PR-04, PR-05, **PR-07** · **Worker:** **Opus · high (Opus reviewer)** · **Review lens:** ≤ 24,000 chars; the embedded core byte-identical; never `agent.py` · **Merge:** last of wave 1 → **Gate G2**

### Wave 2: Phase 1 (launch when PR-01 merges; status `queued`)

#### PR-24 · Ph1 · SP-1's three `customer-records` Cedar texts (split out of PR-08 so they're reviewable by ~02:45)
- **Owns:** `policies/cedar/`, `tests/cedar_texts/`
- **DONE:**
  - These files exist: `policies/cedar/customer-records.{original,forbid-site-adv,restore}.cedar` + `policies/cedar/SHA256SUMS`. `restore` is byte-identical to `original`. **The verbatim original text is not in the repo** (checked: neither ARCH nor PLANNING-HANDOFF nor the 17:37Z snapshot holds it). It comes from the ops lane's B1 read (§5.2 row 1), pasted in by the orchestrator. Until then the worker ships `forbid` as an additive rule over a marked placeholder, says so in the PR, and the orchestrator fills `original` before review.
  - pytest `cedar_texts` on `$PY39`: every attribute access in the forbid text is `has`-guarded (a textual check); the forbid matches only the declared test value `SITE-ADV-*`; `shasum -a 256 -c policies/cedar/SHA256SUMS` passes. A `cedarpy` parse is **not** run by the worker (an install needs the captain's OK); the orchestrator records it as a check outside the PR.
  - Scan · Diff-scope
- **Deps:** PR-01 (merge order only) · **Worker:** Sonnet · medium · **Review lens:** `has`-guards; narrow forbid; the restore = the original · **Merge:** wave 2, 1st · **Needed by:** ~02:45 (Hold-1 at 03:00)

#### PR-11 · Ph1 · Registry tooling, register/risks/inventory drafts, experiment plan, derive, approval-finding generator, run-ids check (T1.4–T1.6, T1.9, B-G8, G-13, G-14)
- **Owns:** `prooflab/registry/` except `__init__.py` and `parse.py` (i.e. `freeze.py`, `pinned.py`, `inventory.py`, `derive.py`, `approval_finding.py`, `named_runs.py`); `register/register.yaml`, `register/risks.yaml`, `register/inventory.yaml`, `register/experiments/plan.md`; `tests/registry/`
- **DONE:**
  - pytest `registry` on `$PY39`. It covers: `freeze` writes register + risks as one version with sha256s and **refuses a re-freeze**; the pin (`IFABRIC_PIN_JSON` + `IFABRIC_PIN_SHA256`) round-trips byte for byte per mode; the declared faults `suppress-record` and `inject-tool-output` sit inside the pin (DC-8); the post-run pin check accepts `v0-smoke` (low cap, EXPLORATORY) and `v0-pilot` (`observe`, caps = 300K); `derive` on a fixture `experiments.jsonl` cites the pilot ids and the frozen rule, and refuses to set the C16 cap from an S2 pilot; the generated `approval-finding.json` passes `prooflab.servicenow.finding.finding_from_dict` (`kind: approval`, both sha256s); the G-14 top-level keys (`register_version`, `status`, `frozen_at`, `builder`, `assurance`, `retention`; `owner` = the ServiceNow user + `owner_name`); `named_runs.check` rejects a `run-ids.txt` holding a pilot or baseline id, or more than one CID per line.
  - The kit parity test (PR-01's) reads `register/register.yaml` as controls 16, 7, 9
  - `register/risks.yaml` holds R-GR-01…R-GR-05 and an appetite per risk (ratings marked for the captain). `register/inventory.yaml` holds `ifabric-rails-policy`, `ifabric-adversarial-corpus` and `ifabric-assurance-agent` (owner Arth, approver Sree, in no `applies_to`). `register.yaml` carries the three rails declarations (B-G8).
  - `register/experiments/plan.md` exists: per pilot, what it measures, each derivation rule and the draft four answers
  - `bash tools/gate.sh` finds no threshold literal in `prooflab/registry/` · Scan · Diff-scope
- **Deps:** PR-01 · **Worker:** Sonnet · medium · **Review lens:** kit parser; pin round-trip; the refuse-refreeze path; values only in YAML · **Merge:** wave 2, 2nd · **Needed by:** 03:45 (the first-apply pin), 04:27 (`v0-pilot`), 05:00 (`v1`), ~05:05 (T2 file)

#### PR-09a · Ph1 · Evaluators c16 / c7 / c9 / claim / approval (T1.3, Ph1 part)
- **Owns:** `prooflab/evaluators/c16.py`, `c7.py`, `c9.py`, `claim.py`, `approval.py`; `tests/evaluators/`
- **DONE:**
  - pytest `evaluators` on `$PY39`. It covers: `c16.assess_run` over fixture spans (dedup by action id, sums the figure of record, compares through `c16_core.compare`, derives the tier, reconciles EP-1 vs EP-2 call by call, and in `enforce` checks there is no model span after a halt) → SATISFIED / BREACHED; `c7` expected vs adapter-emitted (G-a judged, G-b diagnostic; a suppressed `tool.call` → BREACHED); `c9` Maximum + Errors two-sided, per run + hourly roll-up + the warm-up rule; `claim`; `approval.check_versions` (a paused or stale-generation fixture → DENY + `decline-start` for an assessed run; `proceed` otherwise).
  - **Statelessness:** each evaluator gives identical output on repeat, shuffled input order and 8 parallel threads (a test)
  - `grep -nE 'open\(|socket|subprocess|urllib|time\.time|datetime\.now|^_[a-z_]+ = \[\]|global ' prooflab/evaluators/{c16,c7,c9,claim,approval}.py` → none
  - `bash tools/gate.sh` finds no threshold literal · Scan · Diff-scope
- **Deps:** PR-01, PR-02 · **Worker:** Sonnet · medium · **Review lens:** statelessness; no threshold literal; only `c16_core` used for comparisons · **Merge:** wave 2, 3rd/4th (with PR-08a) · **Needed by:** 05:00

#### PR-08a · Ph1 · The orchestrating script (EP-5), budget-guard preflight, EP-0 hook, lane wrappers, conditions and faults (T3.5, B-G7; not `--tamper-tally`)
- **Owns:** `prooflab/adapters/orchestrator/`, `prooflab/adapters/platform_ops/`, `register/conditions/`, `tests/orchestrator/`
- **DONE:**
  - pytest `orchestrator` on `$PY39` with a stubbed invoke subprocess. It covers: **exactly one invoke per handoff** on a simulated timeout (TIMEOUT recorded, never re-invoked); the child env has `AWS_MAX_ATTEMPTS=1`, `AWS_RETRY_MODE=standard` and argv has `--cli-read-timeout 900`; the CID matches `ifabric-(run|test|adv)-…` (via `prooflab.contract.ids`) and the session id = `<CID>-<32 hex>` in `handoff.sent`; `--baggage` is always present; **the preflight refuses** a run whose bound would take the rolling 60 min past 1.0M tokens, and a third `observe` S2 run in a rolling hour; EP-0 (calls `prooflab.evaluators.approval.check_versions`, stubbed until PR-09a merges) declines a paused or stale fixture; the ledger token goes only through a subprocess pipe (a test asserts it is never in argv or a log line).
  - `$PY39 -m prooflab run --dry-run --scenario S1 --only ifabric-customer --condition prompt-attack` prints the envelope with `condition` and its provenance (the text's sha256)
  - `register/conditions/{prompt-attack,encoded-attack,tool-directive,conflicting-context}.txt` + `register/conditions/SHA256SUMS` exist; `shasum -a 256 -c` passes
  - `platform_ops/deploy_wrapper.py` emits an EP-10 record for a pin or mode patch; `live_lane.py` appends a `live-lane-log.jsonl` line (time, action, authority, CID, tokens before and after) with no secret fields (a test)
  - Scan · Diff-scope
- **Deps:** PR-01; codes against PR-09a's `check_versions` signature, imported lazily inside the preflight (a clear error if it is absent), so **PR-08a may merge before PR-09a** · **Worker:** Sonnet · medium · **Review lens:** one invocation per handoff; the guard refuses over-budget runs · **Merge:** wave 2, 3rd/4th (with PR-09a; it does not wait for it) · **Needed by:** 03:50 (S-2). Phase 1 scope is the minimum: no `--tamper-tally` (→ PR-08b).

#### PR-12a · Ph1 · Collectors core + redaction of the three token paths (T4.1 Ph1, T4.2, G-11)
- **Owns:** `prooflab/adapters/collectors/{__init__,capture,aws_spans,ledger_export,cr_status,agentcore_metrics,runtime_logs,modaas_evidence}.py`, `prooflab/store/redact.py`, `tests/collectors/`
- **DONE:**
  - pytest `collectors` on `$PY39` with a stubbed `aws` / `kubectl` subprocess. It covers: **T-REDACT-01**, where a CR fixture holding all three token paths (`spec.awsAgentCore.environmentVariables`, the `last-applied-configuration` and `kopf…/last-handled-configuration` annotations) yields 0 token copies and a list of what was dropped; re-capturing the derived 17:37Z fixture is byte-identical (`cmp`); every capture has a `.capture.json` sidecar with Arth's fields (04-LOGS-TO-EVIDENCE); `redact.py` = our rules ∪ Arth's six; the exact-value scan over a staged fixture tree → 0 hits.
  - `grep -rnE 'get-function|GetFunction' prooflab/adapters/collectors` → none; `get-agent-runtime` output is never written to disk (a test)
  - Scan · Diff-scope
- **Deps:** PR-01 · **Worker:** Sonnet · medium · **Review lens:** T-REDACT-01; byte-identical re-capture · **Merge:** wave 2, 5th · **Needed by:** 03:55 (S-2 assertions), 06:20 (redaction)

#### PR-13a · Ph1 · The one store, the stitcher joins, the run catalogue (CLI list) (T4.3, T4.4 joins, T4.5 Ph1)
- **Owns:** `prooflab/store/{__init__,ledger_client,observations,ingest,snapshot}.py`, `prooflab/stitch/{__init__,stitcher,catalogue}.py`, `tests/store/`, `tests/stitch/`
- **DONE:**
  - pytest `store` on `$PY39`, against a local stdlib `http.server` fake ledger: a re-ingest deduplicates by `record_id`; each normalized copy's `source.refs` sha256 = its raw line's; the laptop-store fallback (`ifabric-store/records.jsonl`) is append-only with fsync; the token is never logged
  - `grep -rnE 'def (update|delete)|"(PUT|DELETE|PATCH)"' prooflab/store` → none
  - pytest `stitch` on `$PY39`: `prooflab refresh` run twice on the fixture → `cmp` of `derived/` byte-identical; the joins CID → action id → trace id → handoff id → AWS invocation record; `derived/unjoined.jsonl` written; `derived/run-catalogue.jsonl` holds every `modaas.run_id` in the fixture spans **exactly once**, no unlabelled row, and only `run-ids.txt` CIDs are marked assessed
  - Scan · Diff-scope
- **Deps:** PR-01; PR-12a (capture format) · **Worker:** Sonnet · medium · **Review lens:** byte-identical re-run; catalogue completeness; no verdicts in the stitcher · **Merge:** wave 2, 6th · **Needed by:** 04:30

#### PR-23 · Ph1 · EP-2: the post-run replay of the c16 core (the second placement; 17b, ARCH §3.1/§11)
- **Owns:** `prooflab/adapters/postrun/`, `tests/postrun/`
- **DONE:**
  - pytest `postrun` on `$PY39`: for an N2-like fixture of model-call spans in gateway order, **one EP-2 `decision` record per span** (`ep.id: EP-2`, `ep.transport: pull`, `bound_basis: actual`, reserved = 0) through the same `c16_core.decide_inline` with the run's pin; each record validates with `prooflab.contract.record`; `evaluator.sha256` == `register/c16_core.sha256`
  - `git diff --stat main...HEAD` touches only `prooflab/adapters/postrun/` and `tests/postrun/` (the I-21 proof)
  - Scan
- **Deps:** PR-01, PR-02 · **Worker:** Sonnet · medium · **Review lens:** the same sha256 at EP-1 and EP-2; records only, never executed · **Merge:** wave 2, 7th · **Needed by:** 05:30 (N2's assessment)

#### PR-20a · Ph1 · Finding builder (required keys) + the notify runner with the bug (a)/(b) guards, incl. the T2 approval notify (T6.4 Ph1, T6.5 notify, T6.10, G-04, G-05, G-20)
- **Owns:** `prooflab/adapters/human_loop.py`, `prooflab/humanloop/{__init__,runner,config}.py`, `tests/humanloop/`
- **DONE:**
  - pytest `humanloop` on `$PY39` against Arth's `prooflab/tests/fake_servicenow.py`. It covers: every generated finding passes `finding_from_dict`; `scope_id` = the CID, `threshold_version`, UTC `detected_at`, `measured` / `limit` (same unit), `register` {`version_date`, `owner` = `SNOW_OWNER_USER`, `approval`}; `summary` ≤ 200 chars with no newline, templated (never agent or model text); ≤ 8 evidence refs with no `;`; only BREACHED, ESCALATED and monitoring-gap produce a notify (SATISFIED → none); a re-run notifies 0 new ids; `selftest` is called before each batch (call order asserted on the fake); a relative `PROOFLAB_DELIVERY_LOG` is refused; **guard (a)**: `--dry-run` is refused unless the log is under `wiring-tests/`; **guard (b)**: sticky RESPONDED; a `kind: approval` finding goes to its own absolute log `evidence/register/approval/delivery-log.jsonl` and is never analysed; bugs (a) and (b) are reproduced on the fakes (via `tools/prototypes/servicenow/repro_bugs.py`) and the guards hold
  - `grep -rn 'prooflab-snow.env' prooflab/humanloop prooflab/adapters/human_loop.py tests/humanloop` → only a documented env-var name, never a file read
  - `diff -r handoffs/ifabric-handoff-3/code/prooflab/servicenow prooflab/servicenow` → empty (Arth's code untouched) · Scan · Diff-scope
- **Deps:** PR-00, PR-01; consumes PR-09a's assessment dicts by contract (**not** PR-19) · **Worker:** Sonnet · medium · **Review lens:** `finding_from_dict`; the guards hold; Arth's code as-is · **Merge:** wave 2, 8th · **Needed by:** ~05:05 (T2), 05:27 (N2 notify)

#### PR-15a · Ph1 · Query engine + CLI: the control test per run and window, the six auditor questions, the run catalogue list (T5.1)
- **Owns:** `prooflab/query/{__init__,engine,cli}.py`, `tests/query/`
- **DONE:**
  - pytest `query` on `$PY39` over a fixture pack (a store export + derived files)
  - From a fresh unzip of the fixture pack: `cd <tmp>/evidence && time $PY39 -m prooflab query --control C16 --run <fixture CID>` prints rule, version, date, owner, population, measured vs limit, exceptions, verdict, gaps and records, in **< 120 s** (expected < 5 s); `--control C7 --window <T1>..<T2>` and `--incident <id>` (the six questions) answer; `--runs` lists the run catalogue
  - The exit code follows `prooflab.contract.verdicts.exit_code`
  - All verdict semantics live in `prooflab/query/` and `prooflab/evaluators/` (a grep test for verdict literals outside them, excluding contract)
  - Scan · Diff-scope
- **Deps:** PR-01, PR-09a, PR-13a · **Worker:** Sonnet · medium · **Review lens:** < 2 min on 3.9 from the pack; no verdict logic elsewhere · **Merge:** wave 2, 9th · **Needed by:** 06:05

#### PR-21 · Ph1 · Pack builder, submit wrapper, readback (T4.8)
- **Owns:** `prooflab/pack/{__init__,build}.py`, `tools/submit_wrapper.sh`, `tests/pack_build/`
- **DONE:**
  - pytest `pack_build` on `$PY39`: `$PY39 -m prooflab pack build --out <tmp>` over the fixtures stages the ARCH §9.1 tree (`store/records.jsonl`, `raw/`, `derived/`, `assessments/`, `register/` + T1 proof, `run-ids.txt`, `gap-list.md`, README, the `prooflab/` tool) and writes `MANIFEST.json`; `$PY39 tools/manifest.py verify <tmp>` OK; planted fake token values in the 3 CR paths → **exact-value scan 0 hits**; WORKDIR copies of `register.yaml`, `gap-list.md` and `run-ids.txt` match their sources under `cmp`; **ADV-R-03**: one tampered byte → `manifest.py verify` exits 1
  - `bash tools/submit_wrapper.sh --dry-run` with a stub `submit.sh` on PATH prints the command and **refuses when the scan is not clean**
  - Scan · Diff-scope
- **Deps:** PR-12a (redaction), PR-13a (export); **not PR-16** (17b; the projection is only for submit #2) · **Worker:** Sonnet · medium · **Review lens:** exact-value scan = 0; `manifest.py verify` OK; readback · **Merge:** wave 2, 10th · **Needed by:** 06:05

#### PR-22a · Ph1 · Minimal deliverable docs: stranger README, decisions log, named-runs template, gap-list section B, the ADV-H-01 pre-registration (T7.1 Ph1, T8.3/T8.5 minimal, D-G1)
- **Owns:** `evidence-templates/`, `gap-list.md` (**section B only**), `evidence/adversarial/cases/`, `evidence/adversarial/README.md`, `tests/docs/`
- **DONE:**
  - These files exist: `evidence-templates/README.md` (the declared-window placeholder, one command per question incl. `python3 -m prooflab query --control C16 --run <CID>`, the honest failure, what was left out), `evidence-templates/decisions-log.md` (Arth's format; D1–D23, DG-1–DG-7, DC-1–DC-11) and `evidence-templates/named-runs.md`, plus `evidence/adversarial/cases/ADV-H-01.md` (the defence and expected outcome, dated before the run)
  - pytest `docs` on `$PY39`: gap-list section B lists gaps 1–11 and rails gaps G-1…G-14; **section A is byte-identical to main** (a sha256 of the section); every command in the README parses as a `prooflab` verb
  - Scan · Diff-scope
- **Deps:** PR-01 · **Worker:** Sonnet · medium · **Review lens:** no claim beyond the evidence; Arth's section A untouched · **Merge:** wave 2, 11th · **Needed by:** 06:05

### Phase 2 (spare workers; status `queued`)

#### PR-19 · Ph2 · The Assurance runtime: bundler, one-file handler (gateway-URL shim, token limit via config), invoke helper, live-shape tests (T6.1, T6.3, T6.12, G-01, G-03, G-22)
- **Owns:** `tools/bundle_assurance.py`, `agents/ifabric-assurance/`, `prooflab/humanloop/invoke.py`, `tests/assurance/`
- **DONE:** `$PY39 tools/bundle_assurance.py` writes `agents/ifabric-assurance/ifabric-assurance.py`, with gzip+base64 ≤ 24,000; Arth's `nemotron.py` is embedded **byte-identical** (a test compares the literal with `handoffs/ifabric-handoff-3/code/…/nemotron.py`); `tools/docker_smoke/` run → `/ping` + `/invocations` against a stub; pytest `assurance` on `$PY312`: `CallableAnalyzer` + `run_assurance_agent` end to end → **WRITTEN, V1–V6**; a 200 + `content_filter` → **BLOCKED** with the action id; a `/v1` suffix stripped; `IFABRIC_ASSURE_MAX_TOKENS` sets `MAX_TOKENS`; the invoke helper (stubbed subprocess) uses `AWS_MAX_ATTEMPTS=1`, `--cli-read-timeout 300`, an `ifabric-assure-` CID, deletes the response file and never re-invokes; G-22 (journal 200/0 rows, the unchanged `GatewayAnalyzer` refusing plain HTTP) green beside Arth's 152 on `$PY39`; `find agents -name agent.py` → empty · Scan · Diff-scope
- **Deps:** PR-00, PR-06 (Docker harness); not `prooflab/humanloop/__init__.py` (PR-20a) · **Worker:** **Opus · high (Opus reviewer)** · **Review lens:** WRITTEN end to end; the BLOCKED path; Arth's code byte-identical · **Needed by:** 06:35

#### PR-17 · Ph2 · Console P0: Arth's spec as-is + the data switch, data-driven EPs, the panel embed, the run-catalogue view (T5.4, G-09)
- **Owns:** `prooflab/console/` except `static/p1/` and `routes_p1.py`; `tests/console/`
- **DONE:** pytest `console` on `$PY39`: **AT-P0** (AT-01…AT-12 + AT-14) on Arth's fixtures; `prooflab console --data pack` refuses SYNTHETIC data and the panel's fake sample; the banner by source; EPs rendered from `pack-index.enforcement_points`; the panel's JS and CSS byte-identical to Arth's (`cmp`); AT-06 with its pattern assembled from parts; GET-only; Host allow-list; CSP · `grep -rnE 'SATISFIED|BREACHED' prooflab/console/static` → none (no verdict logic in JS) · Scan · Diff-scope
- **Deps:** PR-15a (fixtures first), later PR-15b, PR-16 · **Worker:** Sonnet · medium · **Review lens:** AT-P0; no verdict logic in JS

#### PR-16 · Ph2 · The one-way pack projector (T5.3, G-07)
- **Owns:** `prooflab/pack/projector.py`, `prooflab/pack/index.py`, `tests/projector/`
- **DONE:** pytest `projector` on `$PY39`: every projected file validates against `handoffs/ifabric-handoff-3/evidence-console-plan/schemas/contracts.schema.json` with **0 errors**; `enforcement_points[]` = EP-0…EP-16 with honest status; provenance comes membership-first from `run-ids.txt`; a grep shows nothing reads the projection back · Scan · Diff-scope
- **Deps:** PR-13a, PR-15a · **Worker:** Sonnet · medium · **Review lens:** 0 schema errors; one-way

#### PR-15b · Ph2 · Answer composer + grammar (T5.2, G-08)
- **Owns:** `prooflab/query/{grammar,answer,render_text}.py`, `tests/query_answer/`
- **DONE:** pytest `query_answer` on `$PY39`: every phrase in Arth's 06 §6 parses; the same question twice → the same `answer_id` (= `generate_examples.answer_id_of()`; AT-14); answers validate against `contracts.schema.json`; the aliases `controltest`, `ask`, `auditor`, `trail` work · Scan · Diff-scope
- **Deps:** PR-15a · **Worker:** Sonnet · medium · **Review lens:** `answer_id` determinism

#### PR-20b · Ph2 · The human loop extended: analysis between runs, the check loop, case snapshots, export, the ledger mirror, the trace + retest (T6.4 Ph2, T6.5 Ph2, T6.6, G-05, G-06)
- **Owns:** `prooflab/humanloop/{analysis,check_loop,snapshots,mirror}.py`, `tests/humanloop_ph2/`; inherits `prooflab/adapters/human_loop.py` **after PR-20a merges** (the trace ≤ 200 steps, `retest`; R3)
- **DONE:** pytest `humanloop_ph2` on `$PY39` against the fakes: a 353-step trace is summarised, not rejected; `check` runs every ≤ 60 s and stops at RESPONDED; analysis runs only between subject runs (a lock test); `approval` and `wiring-test` are never analysed; a re-mirror deduplicates, and repeated AWAITING_RESPONSE lines are skipped; `ANALYSIS_*` lines carry `call.id` + `note_digest` · Scan · Diff-scope
- **Deps:** PR-20a, PR-19 (`invoke.py`), PR-13a · **Worker:** Sonnet · medium · **Review lens:** the guards still hold; no work held in ServiceNow

#### PR-12b · Ph2 · The remaining collectors: PDP, gateway, AICT, side door, Lambda code sha, the ExpiredToken supervisor (T4.1 Ph2, G-12 AWS half, T7.4 passive)
- **Owns:** `prooflab/adapters/collectors/{pdp_logs,gateway_stdout,gateway_otlp,aict_invocations,aict_discovery,side_door,lambda_codesha,supervisor}.py`, `tests/collectors_ph2/`
- **DONE:** pytest `collectors_ph2` on `$PY39` (stubbed subprocess): both PDP replicas captured; `aict_invocations` joins exactly by baggage CID + `runtimeSessionId`; `side_door` flags a fixture invocation whose CID is not ours; an ExpiredToken error → a `monitoring-gap` record; `lambda_codesha` reads only name, CodeSha256 and LastModified; sidecars have Arth's fields · Scan · Diff-scope
- **Deps:** PR-12a · **Worker:** Sonnet · medium · **Review lens:** exact joins; never `GetFunction`

#### PR-13b · Ph2 · Corroboration, MON-02, the kit cross-check (T4.4 Ph2, T4.7, M-G1 part)
- **Owns:** `prooflab/stitch/{corroboration,kit_crosscheck,mon02}.py`, `tests/stitch_ph2/`
- **DONE:** pytest `stitch_ph2` on `$PY39`: `derived/corroboration/<CID>.json` is byte-identical on a re-run; MON-02 flags a BLOCKed tool call that has a span; `kit-crosscheck/<CID>/gateway-log.json` (model-call spans only, deduplicated by action id) is accepted by the kit's `evaluate.py 16`, and a disagreement is flagged, never resolved · Scan · Diff-scope
- **Deps:** PR-13a, PR-12b · **Worker:** Sonnet · medium · **Review lens:** byte-identical; disagreements surfaced

#### PR-10 · Ph2 · The independent rechecker (T1.3's checker; a different worker from PR-09a)
- **Owns:** `prooflab/recheck/`, `tests/recheck/`
- **DONE:** pytest `recheck` on `$PY39`: written from ARCH §5 only (no import of `prooflab.evaluators` except `c16_core`; a grep test); it agrees with PR-09a on **every** fixture in `tests/evaluators/fixtures/` (a test iterates over them) · Scan · Diff-scope
- **Deps:** PR-01, PR-09a (fixtures) · **Worker:** Sonnet · medium (a worker that never touched PR-09a) · **Review lens:** agreement on every fixture

#### PR-14 · Ph2 · `watch` / `tail`, the live feed, MON-01 (T4.6, G-10, M-G1 part)
- **Owns:** `prooflab/watch/`, `tests/watch/`
- **DONE:** pytest `watch` on `$PY39`: `live/events.jsonl` covers the event kinds of T4.6; a stopped watcher reads STALE within 30 s (simulated clock); `tail` polls no faster than every 3 s; MON-01: a BLOCK in an assessed fixture run → a finding · Scan · Diff-scope. AT-20/AT-21 run live by the ops lane (P1), not in the PR.
- **Deps:** PR-09a, PR-13a · **Worker:** Sonnet · medium · **Review lens:** STALE in 30 s; never a full ledger GET while live

#### PR-09r · Ph2 · The live risk view (T1.3 risk)
- **Owns:** `prooflab/evaluators/risk.py`, `tests/evaluators_risk/`
- **DONE:** pytest `evaluators_risk` on `$PY39`: WITHIN_APPETITE / EXPOSED / UNTESTED from fixture assessments + `risks.yaml`; the same statelessness and grep checks as PR-09a · Scan · Diff-scope
- **Deps:** PR-09a, PR-11 · **Worker:** Sonnet · medium · **Review lens:** a risk state, never a control verdict

#### PR-05b · Ph2 · P2 rails as `rails-v2` (a declared treatment, never for assessed runs) + the RTM-1 corpus (B-G1 P2, B-G5, S-G3)
- **Owns:** inherits `adapters/runtime/rails.py`, `adapters/runtime/egress.py`, `tests/rails/`, `evidence/adversarial/corpus/` **after PR-05 merges** (R3)
- **DONE:** pytest `rails` on `$PY39` + `$PY312`: a test per P2 rail; `wc -c < rails.py` ≤ 10240; the S-G2 golden set still 0/0; the corpus has ~40 items × 3 carriers + a sha256 manifest and a detection table per rail · Scan · Diff-scope
- **Deps:** PR-05; after G3 (agents frozen) · **Worker:** **Opus · high** (the rails) · **Review lens:** false positives; rails-v2 labelled as a treatment

#### PR-22b · Ph2→Ph3 · Docs completed: the run of show, `reviews/` templates, the security matrix, the full README (T8.5 full, T8.6, T7.6, G-16)
- **Owns:** `docs/run-of-show.md`, `reviews/templates/`; inherits `evidence-templates/` and gap-list section B **after PR-22a merges** (R3)
- **DONE:** `docs/run-of-show.md` has one sentence per screen and is timed ≤ 15:00; `evidence-templates/security-matrix.md` lists EP-0…EP-16; the honest failure is named; pytest `docs` still green · Scan · Diff-scope
- **Deps:** PR-22a · **Worker:** Sonnet · medium · **Review lens:** no claim beyond the evidence

### Phase 3 (spare workers; status `queued`)

#### PR-18 · Ph3 · Console P1 (Should) (T5.5, G-17)
- **Owns:** `prooflab/console/static/p1/`, `prooflab/console/routes_p1.py`, `tests/console_p1/`
- **DONE:** pytest `console_p1` on `$PY39`: AT-13, AT-15, AT-16, AT-19, AT-22 on fixtures (AT-20/21 live) · Scan · Diff-scope
- **Deps:** PR-17, PR-14 · **Worker:** Sonnet · medium · **Review lens:** AT-P1; cut first (G-17)

#### PR-09b · Ph3 · The ADV-R-06 change: the seed-vs-gateway `tally-mismatch` reconciliation finding (T1.3 Ph3, R-J-19)
- **Owns:** inherits `prooflab/evaluators/c16.py` **after PR-09a merges**; `tests/evaluators_adv06/`
- **DONE:** pytest `evaluators_adv06` + `evaluators` on `$PY39`: a fixture with a tampered seed tally → a `tally-mismatch` finding; all PR-09a tests still green · Scan · Diff-scope. **Merged only after the ADV-R-06 break is logged** (the break → PR sha → ADV-R-06b chain).
- **Deps:** PR-09a; ADV-R-06 run · **Worker:** Sonnet · medium · **Review lens:** the R-J-19 chain; no change to `c16_core.py`

#### PR-08b · Ph3 · `--tamper-tally` for ADV-R-06
- **Owns:** inherits `prooflab/adapters/orchestrator/` **after PR-08a merges**; `tests/orchestrator_adv/`
- **DONE:** pytest `orchestrator_adv` on `$PY39`: `--tamper-tally` alters only handoff h2's carried tally, the envelope declares it, and a dry run prints it · Scan · Diff-scope
- **Deps:** PR-08a · **Worker:** Sonnet · medium · **Review lens:** one forged handoff only; declared

#### PR-09i · Ph3, cut first · INV reconciliation control (T1.10)
- **Owns:** `prooflab/evaluators/inv.py`, `prooflab/adapters/collectors/aict_assets.py`, `tests/inv/`
- **DONE:** pytest `inv` on `$PY39`: fixture inventory vs the AICT assets export → SATISFIED / BREACHED; statelessness as in PR-09a · Scan · Diff-scope
- **Deps:** Gate G6 · **Worker:** Sonnet · medium · **Review lens:** read-only named passes

---

## Overlap check (every owned path, exactly one owner at a time)

**Live findings in wave 1 (seen in the worktrees at ~02:10Z):**

| Path | Owner | Also created by | Resolution |
|---|---|---|---|
| `adapters/__init__.py`, `adapters/runtime/__init__.py` | PR-01 | PR-03, PR-04, PR-05 (in their worktrees) | Before merge, each of these branches drops both files (`git rm --cached`, or doesn't stage them). The reviewer's Diff-scope check fails the PR otherwise. If PR-01 merges first, rebasing makes them identical no-ops; still verify `git diff --stat` shows none |
| `prooflab/evaluators/__init__.py` | PR-01 | PR-02 | The same: PR-02 drops it, or its content is byte-identical to PR-01's after rebase |

**Wave 2 and later: shared directories split by file**

| Directory | Split |
|---|---|
| `adapters/runtime/` | PR-01 (`__init__`) · PR-03 (`model_call`, `action_id`, `tally`, `hooks`) · PR-04 (`emit_client`, `tool_call`, `judgment`, `startup`) · PR-05 → PR-05b (`rails`, `egress`) · PR-07 (`j2`) |
| `prooflab/evaluators/` | PR-01 (`__init__`) · PR-02 (`c16_core`) · PR-09a → PR-09b (`c16`); PR-09a (`c7`, `c9`, `claim`, `approval`) · PR-09r (`risk`) · PR-09i (`inv`) |
| `prooflab/registry/` | PR-01 (`__init__`, `parse`) · PR-11 (all other modules) |
| `register/` | PR-02 (`c16_core.sha256`) · PR-08a (`conditions/`) · PR-11 (`register.yaml`, `risks.yaml`, `inventory.yaml`, `experiments/plan.md`) · ops lane (`versions/`, `pins/`, `inventory/`, `experiments/experiments.jsonl`) |
| `prooflab/adapters/` | PR-01 or the orchestrator (`__init__`) · PR-08a → PR-08b (`orchestrator/`); PR-08a (`platform_ops/`) · PR-12a (`collectors/` core 8 files) · PR-12b (`collectors/` Ph2 8 files) · PR-09i (`collectors/aict_assets.py`) · PR-23 (`postrun/`) · PR-20a → PR-20b (`human_loop.py`) |
| `prooflab/store/` | PR-12a (`redact.py`) · PR-13a (the rest) |
| `prooflab/stitch/` | PR-13a (`__init__`, `stitcher`, `catalogue`) · PR-13b (`corroboration`, `kit_crosscheck`, `mon02`) |
| `prooflab/query/` | PR-15a (`__init__`, `engine`, `cli`) · PR-15b (`grammar`, `answer`, `render_text`) |
| `prooflab/pack/` | PR-21 (`__init__`, `build`) · PR-16 (`projector`, `index`) |
| `prooflab/humanloop/` | PR-20a (`__init__`, `runner`, `config`) · PR-19 (`invoke`) · PR-20b (`analysis`, `check_loop`, `snapshots`, `mirror`) |
| `prooflab/console/` | PR-17 (all but `static/p1/` and `routes_p1.py`) · PR-18 (those two) |
| `tools/` | PR-00 (`gate.sh`, `manifest.py`, `tests/`, `prototypes/`) · PR-06 (`bundle_agent.py`, `make_ifabric_agents.py`, `docker_smoke/`) · PR-19 (`bundle_assurance.py`) · PR-21 (`submit_wrapper.sh`) · existing `tools/README.md`, `tools/workshop-local/` (nobody) |
| `agents/` | PR-06 (`ifabric-customer`, `ifabric-it`, `ifabric-network`) · PR-19 (`ifabric-assurance`) |
| `evidence/` | PR-05 → PR-05b (`adversarial/corpus/`) · PR-22a (`adversarial/cases/`, `adversarial/README.md`) · ops lane (everything else, R6) |
| `tests/` | one dir per PR: `gate` (00), `contract` (01), `c16_core` (02), `runtime_c16` (03), `runtime_emit` (04), `rails` (05 → 05b), `bundle` (06), `j2` (07), `orchestrator` (08a), `orchestrator_adv` (08b), `evaluators` (09a), `evaluators_adv06` (09b), `evaluators_risk` (09r), `inv` (09i), `recheck` (10), `registry` (11), `collectors` (12a), `collectors_ph2` (12b), `store` + `stitch` (13a), `stitch_ph2` (13b), `watch` (14), `query` (15a), `query_answer` (15b), `projector` (16), `console` (17), `console_p1` (18), `assurance` (19), `humanloop` (20a), `humanloop_ph2` (20b), `pack_build` (21), `docs` (22a → 22b), `postrun` (23), `cedar_texts` (24); `tests/conftest.py` + `pytest.ini` → PR-01 |
| root files | `gap-list.md` section B → PR-22a → PR-22b (section A = Arth's, untouched); `FEATURE-MAP.md`, `IMPLEMENTATION-PLAN.md`, `architecture/*`, `reviews/gates.jsonl` → the orchestrator |

**Result:** after the wave-1 `__init__.py` findings above are resolved, no path has two concurrent owners. The only shared paths are the serial a → b handovers declared in R3 (PR-05 → 05b, 08a → 08b, 09a → 09b, 20a → 20b, 22a → 22b), and each of those starts only after its a-row has merged.

---

## Risks the map carries

- **The Phase 1 second chain is late against its slots.** Wave 2 launches at ~02:15–02:30. 17a estimates PR-08 ≈ 4 h and PR-11 ≈ 6 h, yet §5.2 needs both by 03:45–03:50. Mitigation: their Phase 1 scope is cut to what the slot needs (PR-08a without `--tamper-tally`; PR-11's pins and freeze first, then derive, then the approval file). Wave-1 workers that finish early take wave-2 PRs in needed-by order. A miss moves S-2 under the slip rule (§4.6) and never bypasses the merge gate.
- **PR-20a is now on Phase 1's path twice** (the T2 approval at ~05:05 and N2's notify at 05:27), so it launches in the first wave-2 batch.
- **PR-01's dispatcher routes** must cover `run`, `registry`, `query`, `refresh`, `pack`, `humanloop`, `console`, `watch`, `tail` and `recheck`. Any missing route is a one-line orchestrator follow-up, never an edit to `cli.py` by another PR.

# 11a · Phase-2 design changelog (Fixer A: design and contract)

Written 2026-10-06 (UTC) by Fixer A. Scope: `architecture/ARCHITECTURE.md` §2, §3.1–§3.8, §4, §5, §10, §11, plus `architecture/one-page.md` and `architecture/one-page.svg`. Fixer B edits §6–§9, §12–§15 and `decisions.md` in parallel; nothing here touches those.

Finding ids: `E-`, `I-`, `G-`, `S-` = `work/04-adversarial-review.md`; `A`, `B`, `nit` = `work/04b-independent-review.md`; `AR-` = `work/05-…`; `06 <row>` = `work/06-…`; `GS-` = `work/07-…`; `SN-`, `AI-`, `HL-` = `work/08-…`.

Format: finding id → section → what changed. Appended section by section as the edits land.

## Changes

### §3.2 The one contract
| Finding | What changed |
|---|---|
| E-03, B3 | `Decision` gains `mode`, `limit_applied`, `limit_value`, `action`, `bound_basis`. `verdict` is always against the cap; `action` is against the applied limit (cap in `enforce`, safety ceiling in `observe`). New rule: the EP-1 adapter acts only on `d.action`; a CI search fails on any token-vs-limit comparison in `adapters/runtime/`. An evaluator exception becomes `DENY` + `halt` inside `evaluate()`, never in the adapter |
| E-05 | `Decision` and `Assessment` carry both the control's own `threshold_version` (e.g. `C16-v1`) and the file's `register_version` (e.g. `v1.1`) |
| E-11 | `C16Question.bound_basis` (which term set the conservative bound) |
| I-04, B4 | `Decision.pin_sha256`: the in-path pin a value came from, checked against the frozen file after the run (§3.3) |
| B11, item 4 | `C16Question` and `Decision` now live in the c16 core (`evaluators/c16_core.py`), re-exported by the contract, so one file and one sha256 serve both EPs |
| B2, A3 | EP-0 is explicitly not an `evaluate()` caller: `approval.check_versions` returns the same `Decision` shape and the preflight acts only on `action`. Routing EP-0 through `evaluate()` at a declared pre-run placement is noted as the captain's alternative under D13. The frame line "EXACTLY ONE CALLER: EP-1" is unchanged |
| B1, I-08 | The ≤ 2 s end-of-invocation flush is kept but **declared** (§2.3): best effort, decides nothing, never fails the call, p99 reported |
| nit (callback), I-03 | `callback()` is notify-then-poll: its only caller is the `check` poller (run by `prooflab watch` and `refresh`), once per new response or once at the cutoff |
| E-12 | `pull()` runs by run id and by time window |
| E-01 (pending captain) | "Pulled records are not written to the ledger" is reversed: every normalized record (platform decisions as `record_kind: platform_decision`) is appended to the ledger by `store/ingest.py`, between runs only, deduplicated by `record_id`, with `source.refs` = raw file + line + sha256 of the raw line |
| G-03 | `Assessment.deficiency` (`design` / `operation` / `both` / `none`) heads the finding's summary and work note |
| 06 B10, AR-24 (OC-9) | The stdout witness is now VERIFIED (~0.9 s to `[runtime-logs]`) |

### §3.3 The control registry
| Finding | What changed |
|---|---|
| E-05, A2 (item 1) | New "Versioning is per control" block: file-level `version`/`version_date`/`supersedes` before `controls:`; each control has its own `threshold_version` (`C16-v1`, `C7-v1`, `C9-v1.1`, `INV-v1`) and its own quoted full-UTC `version_date`, carried forward unchanged unless its keys change (CI test both ways). In `v1.1`, C16 and C7 still read `-v1` with v1's date. C9 in `v1` has no baseline (`C9-v1`) → NOT_ASSESSED for C9. Records carry `register.version` and `threshold.version`; `query` prints the control's own version, date and T1 |
| E-05 (parser) | New schema rule 7: quoted full UTC timestamps; verified in the kit's `_load_register` (split on first colon, quotes stripped); PyYAML keeps a quoted timestamp a string |
| 04b nit (multi-line) | New schema rule 6: no multi-line or block values |
| E-04 (item 1) | Date proof rewritten: **T1 alone** is required; a control's T1 = the first file version carrying its `threshold_version`. T2 is corroboration: before the run → "owner approval before run: yes"; later or missing → verdict stands, gap entry, stated under APPROVED. The "no assessed run before T1 and T2" hard line is a process rule only |
| 04b nit (`@ingestionTime`) | The mechanical date check compares T1 with both the first span's gateway start and its CloudWatch `@ingestionTime` |
| 06 D2, D5 | T1 is fail-safe without Object Lock (tampering → INDETERMINATE, never a false pass); keys under `ifabric/register/`; PUT with `--checksum-algorithm SHA256` and `head-object --checksum-mode ENABLED` (untested, spike S2) |
| I-04, B4 | The env pin is now a canonical JSON extract of every in-path value (caps, tiers, safety ceiling, modes, bound policy, declared faults, C16's version/date, file version/sha) derived from the frozen file: `IFABRIC_PIN_JSON` + `IFABRIC_PIN_SHA256` + file version/sha. Both mode variants stored in `register/pins/`. Start-up checks the pin's own hash (fail closed). New post-run pin check: the control test re-derives the pin from the file, compares it byte for byte, and checks each decision's `threshold.value`; a mismatch → `reconciliation` record, `operation` DEGRADED. Why not the whole file: the operator caps env values at 5,000 chars and 50 entries [AR-14] |
| E-11, I-04 | New C16 keys: `inline_bound_margin_pct`, `inline_bound_fallback_tokens`, `max_tokens` (the bound policy); new top-level `join_tolerance_s` (the stitcher's tolerance is no longer a code default) |
| E-07, B13 (item 5) | New C9 keys: `limit_direction: two-sided`; `comparability` holds the warm-up rule |
| B14, I-09 | The kit cross-check is scoped: default-tier runs only, and only where the pack carries the kit-shaped `gateway-log.json`; otherwise the kit says NO EVIDENCE |
| B5, AR-15 (OC-12) | Step 6: an env patch = new generation + runtime version, no re-approval; a rejected value leaves the OLD env, so EP-0 checks the runtime version and the echoed pin sha before an assessed run. The "about 24 s" model-swap figure is removed |
| 08 SN-09 | T2 mechanism options A (owner in the UI) / B (W9 glue), decide by 01:00 UTC |

### §3.4 The evaluator
| Finding | What changed |
|---|---|
| B11, E-02 (item 4) | `c16.py` is split. **`c16_core.py`** = the shared core (`C16Question`, `Decision`, `PinnedC16`, `compare`, `decide_inline`): small, stdlib only, frozen and hashed before the agent build, embedded byte for byte in each single-file agent (fits B's AR-03 bundler). **`c16.py`** = the tester (`assess_run`, `assess_window`), free to change after the build. `decide_inline` is the same function at EP-1 (inline, via `evaluate()`) and EP-2 (post-run, per gateway call, from its own adapter). New rule: the core's sha256 = the register's C16 `evaluator_sha256`, stamped at both EPs; CI checks the embedded literal equals the repo file |
| E-03, B3 | `decide_inline` documented: verdict vs the cap always; `limit_applied`/`action` vs the applied limit |
| E-06, A1 (item 2) | New `c16.assess_window` and `c7.assess_window`, plus a shared window rule: scope by first span time and provenance (LIVE_SUBJECT, FAULT_INJECTION, AUTHORIZED_TEST; adversarial runs labelled), each run under its own bound file version; runs with no entry for the control and PILOT/BASELINE/EXPLORATORY/test runs listed NOT_ASSESSED with a reason; optional `--condition` filter; BREACHED if breached runs exceed a version's `exception_tolerance`, else INDETERMINATE if any is, else SATISFIED; empty → NOT_ASSESSED; C7 prints pooled coverage and gap share |
| I-10 | `c16.assess_run` derives the tier itself from the scenario attributes with the frozen `tier_rule`; a mismatch with the envelope is recorded |
| G-05 | C16's `operation` checks the stop records (no model span after a halt, in enforce) and the EP-1 ↔ EP-2 call-by-call reconciliation |
| B2, 04b nit (stale flags) | `approval.check_versions(running, approved, policy, assessed)` returns Decisions with `mode` = `pre_run_gate` and `action` = `decline-start` only for a DENY on an assessed run under `block-assessed`. The stale-approval test moves here from the EP-5/EP-10 collectors |
| E-07 (item 5) | `c9.assess_run` marked two-sided (detail in §5.3) |
| AR-12 | Accounting rule: 0/0 tokens on a served, unblocked call is missing usage, never zero |

### §4 The record schema and the stitch keys
| Finding | What changed |
|---|---|
| E-01 (item 7) | `record_kind` adds `platform_decision`; `source.refs` adds `raw:<capture path>#L<n>@sha256:<raw line>` (the raw source stays the authority); §4.3 names `platform_decision` as the observed-platform-decision type; §4.4 adds a platform-decision shape |
| 04b nit (CID prefix), item 6 | `run.id`: every run of our trio is `ifabric-run-<epoch>-<hex>`; `fault-…` is only the reference trio's earlier runs |
| E-12 (item 8) | `run.id` lists the sweep-derived forms `ifabric-unenveloped-…` (agent behaviour is §7.1: **cross-dependency for Fixer B**) and the pseudo-CID `unattributed:<runtime>:<eventTime>`; `provenance` adds `UNATTRIBUTED` |
| B7, I-17 (item 6) | Provenance row: every named run is `LIVE_SUBJECT` with its lever in `run.condition`; `FAULT_INJECTION`/`AUTHORIZED_TEST` for adversarial-only runs; "named" = in `run-ids.txt`, "assessed" = in a control test's scope |
| E-05 (item 1) | `threshold.version` = the control's own version; new `register.version` (the file) |
| I-04, B4 | New `pin.sha256` |
| E-03, B3 (item 3) | `inline.*` group adds `limit_value`, `action`, `bound_basis`; EP-0 decisions reuse the group (mode `block-assessed`/`record-only`, action `proceed`/`decline-start`); EP-2 decisions record the core's `action` as not executed |
| AR-20, 06 B6 (OC-5) | `runtime.session_id` added for stitch key 5; `aws.request_id` stays null (no capturable request id) |
| S-04 | §4.4 example: `threshold.version` `C16-v1`, `register.version` `v1` at 04:31Z (was `v1.1`) |
| 04b nit (null rule) | §4.4 example now carries every table-A field (`handoff.*`, `outcome.*`, `inline.limit_applied`, …) or a null with its reason; adds the EP-2 replayed-decision shape with the same `evaluator.sha256` |

### §3.0 Code layout (unowned by either fixer; minimal edits only, for A4 and consistency)
| Finding | What changed |
|---|---|
| A4 | Deleted the stale `systems.py (ifabric / reference payload adapters)` from `adapters/orchestrator/`; `run.py` now notes "EP-0 in its preflight" |
| B11, AR-03 (item 4) | `evaluators/c16_core.py` added; runtime adapters are "bundled into each single-file agent (§7.1)"; the agents line describes one bundled file per agent with the core embedded byte for byte (consistent with Fixer B's single-file builds) |
| E-02 | New `adapters/postrun/c16_replay.py` (EP-2's placement of the core) |
| E-01 | New `store/ingest.py` (normalized records → the one store) |
| I-04 | `register/pins/<v>-<mode>.json + .sha256` |

### §3.1 The EP adapters
| Finding | What changed |
|---|---|
| A3, I-01, item 10 | Intro: "Nothing inside a run waits on anything else; before an assessed run, EP-0 may decline to start it." EP-0 title and body: "in step 1 of `prooflab run`'s preflight"; it may decline to **start** an assessed run |
| B2 | EP-0's transport: `approval.check_versions` returns the `Decision` shape; the preflight acts only on `action` (`proceed`/`decline-start`); routing via `evaluate()` noted as the captain's D13 alternative |
| GS-22, AR-30 (OC-19), GS-14, AR-15 | EP-0 "What it reads": filtered field paths; approved generation from `ApprovalRecorded.observedGeneration` corroborated by Agent Registry `updatedAt` and runtime versions; compare model + generation + runtime version, not the digest alone; READY and updated after the last pin patch; a paused AgentConfig declines the run (a pause is a record, not a stop) |
| E-03, B3 (item 3) | EP-1: the adapter holds no verdict logic and acts only on `d.action`; decision records add `bound_basis`, `register.version`, `pin.sha256`, `limit_value`, `action`; observe vs enforce stated through `action` |
| E-08, A7 (item 12, text side) | EP-1: "The evaluator runs inside the agent": the core embedded in the single-file agent, same sha256 as the repo file |
| AR-10 (OC-1), AR-12 | EP-1: a cancel surfaces as a normal `end_turn` with usage 0; the raw `finish_reason` is captured below Strands (which maps `content_filter` to `end_turn`) |
| E-02 (item 4) | EP-2: the second placement is now literal: `adapters/postrun/c16_replay.py` builds one `C16Question` per gateway call (committed = actual before it, bound = its actual tokens, `bound_basis: actual`) and calls `c16_core.decide_inline` with the run's pin; `decision` records with `ep.id: EP-2`, the same `evaluator.sha256`, `action` recorded never executed. The tester runs afterwards |
| 06 A2, A3, A5, A6, G1 (OC-4) | EP-2: ingestion lag p50 5.1 s / p95 8.3 s / max 9.6 s; hourly slicing under the 10,000-row cap; OC-4 closed (no finish reason; `http.status`; MCP on listener `http` with `mcp.method.name`); baggage assertion in the first smoke run |
| E-12 (item 8) | EP-2 pulls every CID the window sweep finds; EP-6 sweeps `/modaas/evidence` for our tool's route by window; EP-10 sweeps the `ifabric-` CRs' generation history; EP-11 sweeps `aict-invocations` for our three runtime ARNs |
| A4 | EP-5: `run.started` no longer carries "system"; it carries the `ifabric-run-…` CID and `run.condition` |
| AR-20, 10-f11 | EP-5: `handoff.sent` carries `runtime.session_id` (`<CID>-<32 hex>`, minted by the script) |
| E-01 (item 7) | EP-6, EP-7, EP-10 write `platform_decision` records into the one store, with `source.refs` to the raw line |
| 06 B2 | EP-6: PDP lines carry no principal or CID; join by action id, principal from `/modaas/evidence` |
| 06 A5, 10-f11 §4.4 (item 8) | EP-7: BLOCKED_GUARDRAIL from a span is an inference (`reason: "inferred: http 200 + 0/0 tokens"`), corroborated by our EP-1 record (raw `content_filter`) and by the AWS `ConverseStream` `guardrailTrace.actionReason = "Guardrail blocked."` (time + role + model join); "the span says content_filter" removed |
| GS-14 | EP-8: an AgentConfig pause is a record, not a stop; containment = our tool's pause, a model pause, or C16 `enforce` |
| 04b nit (stale flags) | EP-10: the collector records the facts; the staleness test is `approval.check_versions` |
| 06 D4 | EP-10: `cr_status.py` drops `spec.awsAgentCore.environmentVariables` and both the `last-applied-configuration` and `kopf…last-handled-configuration` annotations, on every CR kind (three token copies per AgentConfig). **Cross-dependency: §9.3 is Fixer B's** |
| GS-06 | EP-10: approval time from the `ApprovalRecorded` notification's `creationTimestamp` preferred over `at` |
| AR-20, 06 B6, 10-f11 (resolved: AR-20 holds) | EP-11 rewritten: `InvokeAgentRuntime` records carry `runtimeSessionId`, `traceParent` and baggage CID in `responseElements`, so they join exactly; `eventTime` = call end; delivery 19–328 s; pull ≥ 10 min after the run, join on `eventTime`; F11 corrected. `Converse*` records join by time + role + model only, token counts match the spans |
| 06 B9, GS-23 (OC-13) | EP-12: OC-13 closed; read CodeSha256 via `ListFunctions`/`GetFunctionConfiguration`, never `GetFunction`; baseline at the freeze; CloudTrail `UpdateFunctionCode*` corroborates; status "build" |
| I-03, 04b nit (item 9) | EP-13: notify-then-poll spelled out; `notify()` is the outbound request; `callback()`'s only caller is the `check` poller (run by `prooflab watch` and `refresh`) |
| I-20, 04b nit | EP-4 and EP-11 labelled observers, not passages (ids kept stable) |

### §3.5 The evidence store
| Finding | What changed |
|---|---|
| E-01, R-P-02 (item 7; pending captain) | Opens with "**THE ONE STORE is the platform ledger, `audit-store`**", replacing "one live store for our records". Every adapter's records go in: our emits; **the platform's decisions as `platform_decision`** (EP-6, EP-7, EP-8, EP-10) with `source.refs` to the raw line + its sha256; other pulls as `observation`/`metric`; EP-2's replayed decisions; assessments and findings; callbacks (notifications and polled responses). The raw sources stay where they are and remain the authority. "What stays out of the ledger" deleted |
| E-01 (item 7, laptop path) | New "How the laptop writes to it": the S1 spike path (port-forward or apiserver service proxy, whichever keeps `X-Audit-Token`); the token from the environment only, never on argv, in a file, a child's env or a log [06 C2, C3; AR-22] |
| E-01 + 06 C5 | New "ingest rule": between runs only, never while a run is live (single-threaded server, false C7 gaps); per CID; skip known `record_id`s. Volume estimate ~10–20K records; full GET only between runs and at the final refresh; `tail` ≥ 3 s |
| E-01 (item 7, exports) | New "Per-run exports to S3, with a MANIFEST" under `ifabric/exports/<CID>/`; the pack = final refresh + these exports, "copies of the store, never a second store" (PutObject = spike S2) |
| E-01 (item 7, fallback) | New fallback, stated literally: "**THE ONE STORE becomes `ifabric-store/records.jsonl` on the laptop**", append-only by our code, ingesting the ledger by CID plus laptop records and pulls; what it loses is stated |
| 06 B10 (OC-9) | D8 mirror: stdout lands in the runtime log group (verified), so the runtime half needs no AWS write |
| E-01, E-12 | Export steps: pull by CID and by window; normalize then ingest; GET per CID; export each run to S3 |

### §3.6 The stitcher
| Finding | What changed |
|---|---|
| E-12 (item 8) | New "What it collects: by run id and by time window": the sweep reads the store per CID, `aict-invocations` for our runtime ARNs, the `ifabric-` CRs' generation history, `/modaas/evidence` for our tool's route. Unindexed CIDs → per-CID pulls, provenance `UNATTRIBUTED`; an unmatched `InvokeAgentRuntime` → pseudo-CID `unattributed:<runtime>:<eventTime>`; unindexed 32-hex run ids = background, counted [06 A6]. `query --incident` resolves any CID or time in the window (R-J-28) |
| AR-20, 10-f11 (item 8; resolved: AR-20 holds) | Key 5 rewritten: exact join of the `InvokeAgentRuntime` record ↔ `handoff.sent` by baggage CID + `runtimeSessionId`; `eventTime` = call end, matched to `handoff.received` within `join_tolerance_s`; two records with one session id = a retry; pulled ≥ 10 min after the run, never joined on `@timestamp`; `Converse*` records join by time + role + model with a token-count content match, labelled so. The "UNVERIFIED requestID" line is removed (OC-5 answered no) |
| 06 A5 (item 8) | Key 2: the guardrail outcome (EP-7's inferred BLOCKED) is linked by action id to EP-1's raw `content_filter`; the AWS "Guardrail blocked." record joins by time/role/model only |
| 06 A6 | Key 1: the CID reaches spans only through baggage; it is also in `InvokeAgentRuntime` `responseElements.baggage` |
| I-04 | The attribution fallback uses `join_tolerance_s` (a register key), not a code default |

### §5 The controls
| Finding | Section | What changed |
|---|---|---|
| A3, I-01, B2 (item 10) | §5.0 (4) | `check_versions(running, approved, policy, assessed)` returns Decisions with `mode`/`action`; on a mismatch or a paused agent, an assessed run under `block-assessed` gets `action: decline-start` (not started; DENY + `lifecycle` "run not started" + finding). "Nothing inside a run waits; EP-0 may decline to start an assessed run": EP-0 named as our second refusal, made before the path [slides p13] |
| I-22 | §5.0 (4) | Approved version (c): a declared EP-setting change (pin or mode patch) with the owner's recorded OK; it advances the generation without being an agent change |
| GS-22, AR-30 (OC-19), GS-14 | §5.0 (4) | Field paths settled; `spec.paused` read; never env values |
| E-02 (item 4) | §5.1 | Floor gains the EP-2 replay step; reconcile adds EP-1 ↔ EP-2 decisions call by call ("EP-1 can DENY earlier, never later unless a leak occurred") |
| E-03, B3 (item 3) | §5.1 | Pseudo-code: `bound_for` + `evaluate` → `if d.action == "halt"`; the adapter's `limit = …` line and its comparison are gone. Modes rewritten through `action` (`enforce`: DENY ⇒ halt; `observe`: DENY recorded with `proceed`, `halt` only above the safety ceiling). Fail mode: an exception → DENY + `halt` inside `evaluate()` |
| E-11 (item 6) | §5.1, §3.4 | New "The bound is conservative, so the N3 re-test can't itself breach": `c16_core.bound_for` = max(projected input, last input + last output + tool-result tokens since) or the declared fallback, + `max_tokens`, + `inline_bound_margin_pct` (measured in the stub/smoke/pilot runs, frozen in `v1`); `bound_basis` stamped; headroom (committed − cap) printed for every `enforce` run. Leak 1 reworded |
| AR-11 (OC-2) | §5.1 | Leak 3: OpenAI's 2 client retries sit below the hook (`max_retries=0`); Strands' 429 retries re-enter the hook (closed from source) |
| AR-15 (OC-12), B5 | §5.1 | Changing mode = a pin patch (the other mode's pin of the same file); new generation and runtime version, no re-approval; EP-0 checks the runtime picked it up |
| I-10 | §5.1, §5.5 | The post-run test re-derives the tier; C16's PASS and BREACH fall in one tier, or each tier gets its own pair |
| G-05 | §5.1 | Stop records checked (no model span after a halt, in `enforce`) |
| 06 A5 (OC-4) | §5.1 | Pull row: `http.status`; no span carries a finish reason |
| 06 G1 (OC-4) | §5.2 | The gateway's expected set filters `listener = "llm"` and `mcp.method.name = "tools/call"` (MCP on listener `http`); the "if aws/spans carries it" fallback is removed |
| I-02, B6 (item 6) | §5.2 | "plus one per DENY (a DENY has no span)" → "**plus one per cancelled call** (`outcome.real: CANCELLED_C16`)"; an `observe` DENY is served, has a span, and is counted once |
| G-08 | §5.2 | One EP-0 `decision` per agent is an expected event when D13's gate is on |
| E-01 consequence | §5.2 | The observed set is our **emitted** records (`authorship: TESTIMONY`); pulled records (`platform_decision`, `observation`, `metric`, EP-2's replayed decisions) sit in the same store but never count as observed |
| I-16 | §5.2, §5.5 | The declared fault must be big enough to breach ((|E| − k)/|E| < C%; one record only when C% = 100%) |
| E-07 (item 5) | §5.3 | Limit is **two-sided** (`limit_direction: two-sided`): |relative change| ≤ D%, either direction, with the reason (smaller swap targets may run faster; choosing a direction after P8 would be a threshold chosen after the result). Pre-registered before P8 (pending captain, D3): M3 as co-metric (the kit's own suggestion) and a declared `delay` condition in `v1` as the fallback lever. P8 now also records the direction |
| B13 (item 5) | §5.3 | `comparability` holds the warm-up rule: same session policy across baseline and named runs; one unassessed warm-up invocation per updated runtime after a pin patch, swap or revert, before the next baseline or assessed run (N7, N8, N9) |
| A5, I-05 (item 6) | §5.3 | "N2 will probably also cross C9" → **N2 is NOT_ASSESSED for C9** (bound to `v1`, whose `C9-v1` has no baseline) |
| 04b nit (UNKNOWN), SN-08 | §5.3 | Idle hours are NOT_ASSESSED, never a monitoring gap |
| G-13 | §5.3 | Baseline weighted 4 × S1, 1 × S2, 1 × S3; n stated in `why_value` |
| I-06 | §5.4 | "A later agent change … restarts the protocol" → "an **undeclared** agent change"; declared treatments and EP settings don't |
| I-19, 04b nit (`inline_mode`) | §5.4 | `v0-pilot` declares `inline_modes: observe` and sets `cap_tier_<t>` = the safety ceiling (labelled), so pilot decisions aren't `evaluator-error` noise |
| E-11, B1 | §5.4 | P1–P4 also measure the projection error (→ `inline_bound_margin_pct` in `v1`) and the flush's p99 |
| E-04, E-05 | §5.4 | Step 6: the hard line is a process rule; the verdict rule is T1 alone. Step 7: C16/C7 keep `C16-v1`/`C7-v1` and v1's dates in `v1.1`; warm-up before the baseline runs |
| B7, I-17, 04b nit (item 6) | §5.5 | Every named run is `LIVE_SUBJECT` with `run.condition` and an `ifabric-run-…` CID; N3 = ADV-R-05 and N4 = ADV-R-10 carry both tags and run inside the declared phase window (I-11) |
| 04b honesty (item 6), G-03 | §5.5 | N2's finding names the deficiency "operation: declared observe setting"; **every N3 attempt is listed** in `evidence/named-runs.md`; the first SATISFIED closes the finding, none dropped |
| R-J-19, R-P-25, G-06 (item 11) | §5.5 | New planned break → change → passing re-test: ADV-R-06 forged tally (break) → a dated PR adds the seed-vs-gateway check in `c16.py` raising a `reconciliation` finding `tally-mismatch` (change; core and agents unchanged) → ADV-R-06b passes when the finding names the forged handoff. **Cross-dependency: Fixer B's §6.4 table should carry the ADV-R-06 → change → ADV-R-06b row** |
| G-10 | §5.5 | C16 fallback: a third declared condition pre-registered in `v1` offered as the lead's option for the captain |
| I-13, B14 | §5.5 | `run-ids.txt` = **one CID per line** (the kit's format); the rest goes in `evidence/named-runs.md` and the README. **Cross-dependency: §9.1 (Fixer B) lists `run-ids.txt`** |
| S-05 | §5.5 | If an unplanned failure happens, it leads; the R-J-19 case stays the adversarial example |

### §2 The pattern and our adaptation
| Finding | Section | What changed |
|---|---|---|
| A3, I-01 (item 10) | §2.2 | "Exactly one question may make work wait" → "Exactly one question sits in the live path and may make work wait … Nothing inside a run waits on anything else; before an assessed run, EP-0 may decline to start it". I-14's "model-call path" wording was already in §2.2 and is kept |
| E-08, A7 (item 12, text side) | §2.2 | New bullet: the evaluator runs inside the agent (the embedded c16 core, same sha256); the same function runs again at EP-2 |
| E-01 (item 7) | §2.2 | The store bullet now reads "**THE ONE STORE is the platform ledger, `audit-store`** (pending captain)": every adapter's records incl. `platform_decision`; laptop writes via the S1 path; per-run exports with a MANIFEST; the pack = the final export; the laptop fallback named |
| I-03, E-12 | §2.2 | `callback` = notify-then-poll; `pull` by run id and by time window |
| 04b nit (ASCII lacks EP-0), E-08, E-01, E-02, E-04, AR-20 | §2.2 ASCII | Diagram regenerated (aligned by script): EP-0 in the script box ("may decline to START an assessed run"); EP-1 shows `evaluate(C16) -> c16 core, embedded in the agent` with verdict vs cap and action per mode (A6); the store box is "THE ONE STORE … our records + the platform's decisions"; pulls → raw (stay put) → normalized → ingested into the one store; evaluators line names the same function at EP-1 and EP-2 and the tester; date proof = T1, ServiceNow corroborates; stitch key 5 = CID + session id on the AWS invoke record; ServiceNow = notify, verdict back by callback realised by polling; per-run exports |
| B1, I-08 | §2.3 | New row: the end-of-invocation flush, declared: ≤ 2 s, best effort, decides nothing, never fails the call, p99 reported; "Not a question". The C16 row reads "the only question that waits" |
| A3, B2 | §2.3 | EP-0 row: step 1 of the preflight; `approval.check_versions` + `emit`, acted on through `action`; "may decline to start an assessed run" |
| E-01, I-03, E-02 | §2.3 | Platform-EP row: normalized into the one store; ServiceNow row: notify out, callback back by polling; post-run row adds EP-2's replayed decisions |
| E-03 | §2.4 | "Telemetry store never judges": the EP adapters act on `action`; test adds "no token-vs-limit comparison in `adapters/runtime/`" |
| S-06, I-04 | §2.4 | "Register never in the path": the pin is a JSON extract checked after the run; test = "registry and files unavailable after start → identical decisions, on the bundled agent with the stub model" |
| E-01 | §2.4 | "Ledger never interprets": platform decisions enter as normalized copies pointing at raw lines; test adds "every copy matches the sha256 of its raw line" |
| E-04 | §2.5 | Approval-gate row: dated by T1; the ServiceNow sign-off (T2) corroborates; EP-0 may decline to start |

### §10 Judging map
| Finding | Section | What changed |
|---|---|---|
| E-02 (item 4) | §10.1 | Second-EP row: "the same function, `c16_core.decide_inline` (one sha256), at EP-1 and EP-2; the control test is separate (the tester)" |
| I-04, S-06, E-03, E-05 | §10.1 | Register row: the pin is a JSON extract checked after the run; the unavailable-after-start test. Stateless row: adapters act only on `action`. Threshold row: each control's own version and date |
| E-06, A1 (item 2) | §10.1 | Live-test row: `--window` for C16, C7 and C9 (window evaluators), each run under its own version; one window query per control rehearsed |
| E-01 (item 7) | §10.1, §10.2, §10.4 | Evidence row and LOSE row: every decision in one store; L2 row: "THE ONE STORE"; new R-P-02 row |
| E-04, E-05 (item 1) | §10.2 | Dated-threshold LOSE row: per-control versions and dates; T1 alone is the proof (gateway start and `@ingestionTime`); T2 corroborates; a late T2 = gap entry |
| E-12 (item 8) | §10.2, §10.3 | Coverage LOSE row adds the window sweep; §10.3 opens with "any incident = any CID or time in the window, incl. traffic without our CID" |
| AR-20, 10-f11 (coordinator) | §10.3 | **WHO row:** the `InvokeAgentRuntime` record joins its run exactly by the baggage CID and session id in `responseElements` (was "by ARN + time"); limit adds "names a role, not a person" |
| 06 A5, 10-f11 §4.4 | §10.3 | AUTHORIZED row: guardrail block inferred from the span, corroborated by EP-1's record and AWS's "Guardrail blocked." |
| I-22, E-04 | §10.3 | APPROVED row: EP-0 counts declared EP-setting changes; T1 + T2 (or a gap entry) |
| R-J-24, I-18 (item 11) | §10.2, §10.4 | Re-test LOSE row: acceptance recorded separately with approver + expiry, never closes; a ServiceNow-closed incident without re-test = gap entry. New R-J-24 row |
| R-J-05 (item 11) | §10.4 | New row: the frozen inventory in the pack; `query --inventory` lists each agent's host and model; every AWS-side model call checked to be Nemotron |
| R-J-19 (item 11) | §10.4 | New row: ADV-R-06 → change → ADV-R-06b; Bonuses row points at it |
| R-P-04a, B8 (item 9) | §10.4 | New row: the control test's output block (responsible, actor/runtime/version/principal/on whose behalf, decision at each EP) |
| I-03, B1 | §10.4 | R-J-47 row: callback = notify-then-poll; R-J-48 row: one question waits, the flush declared, EP-0 before the path |

### §11 The second enforcement point
| Finding | Section | What changed |
|---|---|---|
| E-02 (item 4) | §11.1 | Retitled "the same C16 evaluator function at two enforcement points". New lead paragraph: `c16_core.decide_inline` runs at both EPs, same pin, one sha256. EP-2 now **calls the same function** once per gateway call (`c16_replay.py`, `bound_basis: actual`, action recorded never executed). New "Not the control test" bullet (the tester `c16.assess_run` returns an `Assessment`; slides p13; R-J-55) |
| B11 (item 4) | §11.1 | "What both share": the frozen, embedded `c16_core.py` (fits B's single-file agents); later tester fixes never touch it; CI equality; the same pin |
| E-11, E-02 | §11.1 | New "Where they can differ, and why" (EP-1 may DENY earlier, never later unless a leak; reconciled call by call) |
| I-21 | §11.1 | Diff proof: EP-2 lands first (P0); EP-1 in its own PR touching only `adapters/runtime/` and the core's bundling; cite that PR's sha and diffstat. EP-2's adapter list adds `c16_replay.py` |
| E-02 | §11.1 | Third placement re-runs the EP-2 replay (the same function) and the tester; the demo shows the EP-1 and EP-2 decisions on the same call |
| I-03 | §11.1, §11.2 | Human queue: `notify` out, `callback` back realised by polling |
| E-02 | §11.2 | Scheduled-batch row: "EP-2's post-run placement of the c16 core; the post-run tests" |

### §3.7 The control test / query tool (review findings only; the dashboard's form and hosting are untouched, per the coordinator)
| Finding | What changed |
|---|---|
| E-06, A1 (item 2) | New CLI rows `query --control C16 --window T1..T2 [--condition X]` and `query --control C7 --window …` (each run under its own version; listed-but-not-counted runs with reasons; window verdict vs `exception_tolerance`; C7 pooled coverage and gap share) |
| E-05, E-04, E-11 | The `--run` row: the control's own version and date with its T1 proof; T2 before / after / missing (gap entry); the file version; C16 headroom on every `enforce` run. Row generalised to C16, C7 and C9 |
| B8, R-P-04a (item 9) | New "What every answer carries": who is responsible (`ep.responsible`, `control.owner`, inventory owner); who acted (actor, runtime, version, principal, on whose behalf); the decision at each EP (EP-0, EP-1 beside EP-2, platform decisions beside real outcomes, the human loop); under which rule; missing fields print "unknown" with the gap id |
| E-12 | `--incident` resolves any CID or time in the window, `UNATTRIBUTED` included |
| R-J-05 (item 11) | `--inventory` lists every agent with its host (runtime ARN or the ServiceNow agent) and model, and checks every AWS-side model call names a Nemotron id |
| A4, I-11 | `--runs`: the stale "system" column removed; phase = the declared label from boundaries written into the run index before the runs; adds condition, control role, ADV ids, file version |
| I-03, nit (item 9) | `watch` and `refresh` run the `check` poller, the only caller of `callback()` |

### §3.8 The ServiceNow callback / notify (review findings only)
| Finding | What changed |
|---|---|
| I-03, 04b nit (item 9) | "`notify()` = `callback()`" replaced by notify-then-poll: `notify()` is the outbound request; `callback()` is called only by `check_response()` (`check --cutoff`), which `prooflab watch` runs every few minutes and every `refresh` runs once — once per new response, or once at the cutoff; `export` = `pull()` |
| G-03 | `publish()` heads each finding's summary and first work note with the deficiency (e.g. "deficiency: operation (declared observe setting)"), tested |
| E-01 | `mirror()` writes into the one store |
| E-04 | The approval export is T2 = corroboration, and also serves risk acceptances |
| I-18 | "The owner responds and never resolves"; `export` compares ServiceNow state with the re-test link; a ServiceNow-closed incident without a passing re-test = gap entry, finding stays open |
| R-J-24 (item 11) | New "Risk acceptance: a separate path": an `approval` record (`approval.kind: risk-acceptance`) with named approver, finding id, risk id (§3.9), reason and hard expiry; its own ServiceNow record, exported like T2; changes the risk's display ("accepted until …"), never the finding; expiry → EXPOSED again; printed by `query --risk` and `--incident`; none planned at `v1` |
| SN-05, SN-06 | Accepted adapter risks marked as confirmed from source, with W9 fixes proposed; dry runs use a scratch delivery log; nobody but the owner updates our incidents after she responds |

### `one-page.svg` (redrawn) and `one-page.md` (rewritten to match it)
The sketch is regenerated by `architecture/work/11a-one-page-svg-gen.py` (`python3 architecture/work/11a-one-page-svg-gen.py architecture/one-page.svg`; built from the earlier scratchpad scripts `gen_onepage.py` + `svg_edit.py`; it needs Pillow and the macOS fonts it measures with) that measures every text run against Helvetica Neue and Arial and refuses to write a file in which any line overflows its box. Old: 1600×1340, 271 text runs, 1,410 words, 242 runs below 14 px. New: 1600×1842, 290 runs, 1,362 words, **0 runs below 14 px**, no external references. Render-checked with `qlmanage -t -s 1600` (it clips at 1600 px tall) and in full with `rsvg-convert -w 1600`, cropped and inspected; three rounds of fixes for crossings and collisions.

| Finding | What changed on the sketch (and in `one-page.md`) |
|---|---|
| A7, E-08 (item 12) | A **"c16 core" box inside the runtime box** ("embedded in the agent (one file per agent) · same sha256 as the repo's c16_core.py · returns ALLOW \| DENY + the action"). The red `evaluate()` arrow, labelled "in process", now ends there; nothing red reaches the governance side. A **grey dashed "same function, same sha256" link** runs from the core to the stateless evaluators, passing between the `emit()` and `callback()` pills |
| E-08, E-02 | The post-run path is drawn: `pull()` → pull adapters → evaluators, labelled "EP-2 · same c16"; the pull-adapters box says "EP-2 aws/spans → the C16 floor, and the same c16 core per call, post-run"; the evaluators box says "the SAME function at EP-1 (inline) and EP-2 (post-run)" and names the tester separately |
| A6 (item 12) | EP-1 reads "enforce: a DENY halts the agent's calls / observe: a DENY is recorded; only the safety ceiling halts" (was "ALLOW, or DENY → no more model calls") |
| I-01, A3 (item 12) | Headline: "Only ONE question sits in the live path: the C16 check before each model call. Before a run, EP-0 may decline to start an assessed run." EP-0 is a green sub-box in the script ("may decline to START an assessed run; inside a run, nothing waits on it") |
| 04b nit (item 12) | A blue arrow from the script to `emit()` ("handoffs → emit()"); flows out of `callback()`: `callback()` → `emit()`, and ServiceNow → `callback()` ("her verdict, polled by check") |
| E-01 (item 7) | The store box is **"THE ONE STORE"** ("every decision: ours at action time; the platform's, normalized, each pointing at its raw source"; D16, pending captain); pull adapters → "normalized → THE ONE STORE"; the pack is "Evidence Pack: exports of THE ONE STORE … copies, never a second store", with "per-run exports" |
| E-05, E-04 (item 1) | Registry box: "each control: own version + date"; "date proof: the S3 write-once object (T1); the owner's ServiceNow approval corroborates" |
| AR-20, 10-f11 (coordinator) | Stitcher key 5: "CID + session id on the AWS invoke record" (was "runtime ARN + time"); telemetry: "aict-invocations (7 d): CID + session id per invoke" |
| E-06, A1 | The control-test box shows `--control C16\|C7\|C9 --run <CID> \| --window T1..T2`, and that every answer names who is responsible, who acted and the decision at each EP (B8) |
| I-14 | "our only code in the model-call path" |
| I-15 | "we configure 1 forbid rule (if D15)" (D15 replaced D10's Cedar placement in Fixer B's decisions) |
| I-23 | AI inventory: "risk tier: high (our 5×5 rating); EU AI Act class unverified (OC-21)" |
| S-01 | The registry's dashed arrow now starts on the registry box and is labelled "the registry's pinned copy, set at deploy, before the run" |
| S-02 | Legend completed: red, blue, grey, green dashed, purple, orange (the one store + exports), teal (control test), amber (contract · habits), the PRE · CONT · POST chips, the dashed green arrow, the dashed grey "same function" line, the red "one wait" arrow |
| S-03 (partly) | Every text run ≥ 14 px and the hand-in render is `rsvg-convert -w 3200`. Not done: the 40 % text cut (the reviews' additions roughly offset the cuts), and the render-time stamp of register version + git sha (it needs the freeze; W10's render step) |
| 04b nit (AICT) | Third-party SaaS row: "AICT → pull(): observed" (was "built"); ServiceNow box: "AICT: discovery of our runtimes (observed, not built)" |
| I-03 | `callback()` pill: "later verdict: notify, then poll"; ServiceNow box: "her verdict returns by callback(): check polls it, or records the silence" |
| E-12 | `pull()` pill: "by run and by window"; pull adapters: "by run AND by window; raw stays put" |

### Small 04b nits, applied last
| Finding | Section | What changed |
|---|---|---|
| G-12 | §3.7 | `--incident` on an out-of-scope CID answers "out of scope (scope_rule, inventory version …)" with what was seen |
| 04b nit (A:321) | §3.1 EP-6 | The admission claim now says "by the policy's text, never tested by a write of ours" |
| 04b nit (A:496) | §3.3 | `applies_to` includes N8's declared swap variant of `ifabric-it` |
| 04b nit (A:823) | §5.0 (2) | The safety ceiling is declared before the pilots (in `v0-pilot`); the caps, tiers and the bound's margin come from the pilots |

## Not applied, and why
| Finding | Why not here | Owner |
|---|---|---|
| E-09, E-10, A8, B10, B12, B9 (W9 additions) | Schedule, cut lines and workstreams: §12 | Fixer B |
| I-12 | The corroboration report for every CID: §9.2 | Fixer B |
| G-04 | The roles table: §15 / R-D-02 | Fixer B |
| G-07, R-J-45 run-of-show, R-J-56 mentor review | The demo, run-of-show and mentor items | Fixer B (per the lead's split) |
| G-11 | Pack hygiene (judge-facing architecture file, `DEFAULT_OWNER`, email scan): §9 | Fixer B |
| I-09 / B14 (the file) | §3.3 now scopes the kit cross-check; writing the kit-shaped `gateway-log.json` is a §9.1 decision | Fixer B |
| G-09 | Minimal pulls for the ledger's token gate and the runtime IAM deny: not in the 12, extra build for little judging value | — (left as stated in §3.1 "No adapter of ours") |
| S-03 (part) | The 40 % text cut (the reviews' additions offset the cuts) and the render-time stamp (register version + git sha) that needs the freeze | W10's render step |
| I-15 (part) | Generating the sketch's "built" cells from gate records at render time | W10 |
| SN-05, SN-06 code fixes | Arth's package; §3.8 records them as confirmed risks with W9 fixes proposed | W9 / the captain |
| E-12 item 4 | Minting `ifabric-unenveloped-…` is agent behaviour: §7.1. §4.2 already lists the prefix | Fixer B |

## Cross-dependencies and inconsistencies for Fixer B and the lead
1. **D16's fallback (b) disagrees with the brief.** §13 and `decisions.md` describe D16 (b) as "a normalized store on the laptop for the platform's decisions, with the ledger holding only our records": two stores. The lead's brief, and now §2.2 and §3.5, make the fallback a **single** laptop store (`ifabric-store/records.jsonl`) that ingests the ledger and every pull, so the "one store" stays literal. Align D16 (b) with §3.5.
2. **The CID prefix `ifabric-run-…`** (§4.2, §5.5) must reach §7.2 step 2 (the script mints it) and the README. The kit's `evaluate.py` filters on `modaas.run_id` as a string, so any prefix works there.
3. **`run-ids.txt` is one CID per line** (§5.5); §9.1 still lists `run-ids.txt` and should send the per-run details to `evidence/named-runs.md`.
4. **The R-J-19 case** (ADV-R-06 → the seed-vs-gateway reconciliation finding → ADV-R-06b, §5.5) needs its row in §6.4's table.
5. **Redaction paths** (`spec.awsAgentCore.environmentVariables` + the `last-applied-configuration` and `kopf…last-handled-configuration` annotations, on every CR kind) are now in §3.1 EP-10; §9.3 must say the same.
6. **The end-of-invocation flush is declared, not dropped** (§2.3, §3.2). If §7.1 describes the emit client, it should match.
7. **§1.2 (unowned)** still names `c16.decide_inline`; with the split it is `c16_core.decide_inline`.
8. **The env pin is a JSON extract** (`IFABRIC_PIN_JSON`, `IFABRIC_PIN_SHA256`, file version + sha; §3.3) because of the 5,000-character env-value cap. §7.1's start-up list and §7.2 should use these names (and `IFABRIC_DECLARED_FAULTS` now lives inside the pin).
9. **The session id** (`<CID>-<32 hex>`) is minted by the script and recorded in `handoff.sent` (§3.1 EP-5, §3.6 key 5): §7.2 should mint and pass it.
10. **§14 open checks** closed by inputs my sections now cite: OC-1, OC-2 (from source), OC-4, OC-5 (answered no), OC-9, OC-12, OC-13, OC-19; OC-3 still a spike.

### Last fix, after the final review
| Finding | Section | What changed |
|---|---|---|
| B7, I-17 (one term, two meanings) | §4.2 | The provenance row now keeps two scopes apart: EP-0's gate treats only `LIVE_SUBJECT` runs as assessed (an adversarial run proceeds with a finding, as §5.0 says); a control test's window scope is wider and also counts `FAULT_INJECTION` and `AUTHORIZED_TEST` runs, labelled (§3.4). W3's `check_versions(..., assessed=…)` and W5's window rule can no longer disagree |

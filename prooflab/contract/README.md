# The ProofLab contract, in one page (PR-01)

`prooflab/contract/` is the root every other PR builds on. Stdlib only, Python 3.9+. Contract version
`ifabric.contract/1`; record schema `ifabric.evidence/1` (ARCH §3.2, §4; guardrails G0.2 path A). A change
here is a PR to the contract owner that bumps a version (R-D-06). Tests: `tests/contract/`.

| Module | What it fixes | Who builds on it |
|---|---|---|
| `record.py` | The ONE record: `REQUIRED`, `TABLE_A` (null rule), `OPTIONAL`, `DERIVED` (never stored), vocabularies (`RECORD_KINDS` incl. `rail_decision`, `CONTROL_REFS` incl. `RAIL`, `EP_IDS` EP-0..EP-16, `OUTCOME_REAL` incl. `CANCELLED_RAIL`, `PROVENANCE`, `AUTHORSHIP`), `validate_record(rec) -> [errors]` (never raises), `new_record(kind, null_reason, **fields)`, `complete_nulls`, `emitted_record_id`, `observation_record_id` (`obs-` + sha256[:32]), `rail_tag`, `json_schema()` (= `schema/evidence-record-1.json`) | everyone that writes or reads a record |
| `verdicts.py` | Four verdict types, never mixed: decision ALLOW/DENY; record RECORDED/ESCALATED; **rail ALLOW/BLOCK/MODIFY/FLAG** (rail_decision only); assessment SATISFIED/BREACHED/INDETERMINATE/NOT_ASSESSED. Risk states never in `verdict`. The §4.3 four-row map (slides, brief, Finding, kit label, exit code), `rail_action(verdict, mode)` (observe always proceeds) | evaluators, query, console projector, rails |
| `clocks.py` | `CLOCKS`, `is_utc`, `parse_utc`, `format_utc` (ms + Z), `compact` (record-id prefix) | emitters, collectors |
| `ids.py` | CID families (`ifabric-run/test/adv/assure/unenveloped-<epoch>-<hex>`, `unattributed:<runtime>:<t>`, `fault-…`, `unresolved:<trace>`), `mint_cid(family, epoch)`, `mint_session_id` (`<CID>-<32 hex>`), `handoff_id` (`<CID>:h<n>`), baggage (`modaas-correlation-id=<CID>`), `traceparent` | orchestrator (PR-08), runtime adapters, stitcher |
| `register.py` | Register schema: top keys, kit fields, extended flat keys, per-control `threshold_version` + `version_date` (full quoted UTC), `validate_register`, `check_version_bumps` (both directions), typed accessors, `register_sha256(file bytes)` | registry tooling (PR-11), evaluators |
| `pin.py` | `ifabric.pin/1`: `derive_pin(doc, sha, mode)` (pure), `dumps` (canonical), `loads(text, sha)` (fail closed), `env_block` / `load_pin_env` with `IFABRIC_PIN_JSON`, `IFABRIC_PIN_SHA256`, `IFABRIC_REGISTER_VERSION`, `IFABRIC_REGISTER_SHA256` | c16 core `PinnedC16.from_env` (PR-02), PR-11, post-run pin check |
| `finding.py` | The dict Arth's `finding_from_dict` accepts (same required fields, verdicts, scope kinds, id rules, optional handoff-3 context `measured/limit/register/trace/retest`); `make_finding`, `finding_id`, `finding_from_assessment` (the §4.3 mapping) | evaluators (PR-09), human loop (PR-20), G-13 |
| `app_format.py` | Console projection fixed points: `ifabric.pack-index/v1` / `ifabric.answer/v1` required keys and enums (checked against Arth's `contracts.schema.json`), G-07 mapping tables (provenance, record kind, DENY-in-observe -> ALERT), `answer_id_of` (reproduces Arth's fixtures) | query/answer (PR-15), projector (PR-16), console (PR-17) |
| `rails_api.py` | The rails API signatures PR-05 implements (`check_input`, `check_tools`, `check_tool_call`, `check_tool_result`, `check_output`, `decisions`, `policy_sha256`), the `RailOutcome`/`RailDecision` shapes, `rail_record` (full G0.2 record), `attach_compact_allows` (DG-3 `rails.allow`), `count_into` (`rails.counts`), `worst` | PR-03 (dispatcher), PR-04 (emit), PR-05 (rails) |
| `c16_hook.py` | `ModelCallEvent`, `DECISION_FIELDS` (the §3.2 Decision), `decision_record(decision, ctx)` (Decision -> the `decision` record; halt at EP-1 -> `CANCELLED_C16`), `stop_record` | PR-03 (EP-1), EP-2 replay |
| `envelope.py` | The run envelope `ifabric.run/1` (ARCH §7.2) at `payload["ifabric"]` (`PAYLOAD_KEY`): `ENVELOPE_KEYS` (envelope, run_id, handoff_id, from, to, tier, tally_tokens, tally_calls, register_version, register_sha256, provenance, condition) + `ENVELOPE_OPTIONAL` (pin_sha256, mode, condition_sha256, scenario, fault); `build_envelope`, `wrap`, `read_envelope(payload)` (never raises; None = the unenveloped path), `validate_envelope` (run_id a CID, handoff_id `<run_id>:h<n>`, tallies int >= 0, sha256 hex, provenance in `record.PROVENANCE`), `echo`. Not the console's `ifabric.run/v1` run file (app_format) | producer PR-08a; readers PR-04 (start-up), PR-05 (rails), PR-06 (apps: no translation glue) |
| `schemas.py` | JSON Schema files in `schema/` generated from code (a test keeps them equal): `evidence-record-1.json`, `assessment-1.json`, `register-1.json`, `pin-1.json`; `app-contracts-v1.schema.json` is a byte copy of handoff-3 `contracts.schema.json` (pack-index, answer, ...; FM-B answer checked). Regenerate: `python3 -m prooflab.contract.schemas` | other tools and readers |
| `transports.py` | `evaluate(q, pin, evaluator_sha256=None)` (delegates to `prooflab.evaluators.c16_core.decide_inline`, passing the embedded core's sha256 when given; verified against PR-02's core on 3.9; any exception -> fail-closed DENY/halt `evaluator-error`, using `c16_core.fail_closed_decision(q, pin, reason)` if the core defines it), lazy re-export of `C16Question`/`Decision`/`PinnedC16`, `EMIT_RECEIPTS`, `DeferredVerdict`, `SourceSpec`, `Window`, `Capture`, `Assessment`, `assessment_id` | ONLY `adapters/runtime/model_call.py` may import `evaluate` (a test enforces it) |

**Rules every writer follows**
- Build records with `new_record(...)` (or `rail_record` / `decision_record`) and call `validate_record` before emit; table-A fields are never absent: value, or null + `null_reasons[field]`.
- `run.id` is the CID and equals `correlation_id`. Pulled platform records use `observation_record_id(system, ref)`.
- Rail verdicts only on `rail_decision` (`control.ref: RAIL`, `control.id: RAIL-<id>`, `register.version: null`, `handoff.id` set). ALLOWs ride compactly as `rails.allow` + `rails.policy_sha256`; `rails.counts` only on the lifecycle record. Nothing rail-shaped ever enters an assessment.
- Never put a cap in a payload: in-path values come only from the pin; the register parse is `prooflab/registry/parse.py` (strict flat-YAML subset = what the kit's no-PyYAML fallback reads identically; kit parity is tested).
- The validator refuses secret-shaped values and keys that name secrets; the exact-value scan (§9.3) is still the real check.

**The dispatcher.** `python3 -m prooflab <verb>` (`prooflab/cli.py`): verbs map to `module:function`, imported lazily; the
function takes `argv` and returns an exit code. Unbuilt verbs print "not built yet" (exit 3). To add or retarget a verb,
ask the contract owner for a one-line change to `VERBS`. Routes (FEATURE-MAP R1: every target is `prooflab.*`; each is the
module path the owner's branch ships, checked fix round 2): run -> `prooflab.adapters.orchestrator.run` (PR-08a);
registry (alias register) -> `prooflab.registry:main`, a lazy sub-dispatcher (freeze, pin, derive, inventory,
approval-finding, run-ids -> PR-11's `freeze`, `pinned`, `derive`, `inventory`, `approval_finding`, `named_runs`);
query / assess -> `prooflab.query.cli:main` / `:assess_main` (PR-15a; assess_main pending); refresh ->
`prooflab.store.snapshot` (PR-13a); pack -> `prooflab.pack.build` (PR-21); humanloop -> `prooflab.humanloop.runner` (PR-20a);
console -> `prooflab.console.server` (PR-17); watch / tail -> `prooflab.watch.cli` / `.tail` (PR-14); recheck ->
`prooflab.recheck.rechecker:main` (PR-10; main pending); collect -> `prooflab.adapters.collectors:main` (PR-12a); postrun ->
`prooflab.adapters.postrun.c16_replay:main` (PR-23); servicenow (Arth). A built module without the function exits 3.

**Tests.** `pytest.ini` runs `tests` and `prooflab/tests` in pytest's default (prepend) import mode, so a PR's tests may import
a helper from their own directory; test basenames must therefore be unique: `tests/<dir>/test_<dir>_*.py` (FEATURE-MAP R4).
`tests/conftest.py` puts the repo root on `sys.path`. Do not add `tests/__init__.py`.

**Workflow phases (C7, ARCH §5.2).** `record.WORKFLOW_PHASES` fixes the event names C7 matches by (agent, `phase`,
`seq.in_stream`): run.started, handoff.sent, invocation.received, intent, judgment, handoff.received, escalation, run.finished,
stop. A record with one of these phases must have the mapped `record_kind` (escalation is a `judgment`); other records keep
`ifabric.<kind>`. The register's `workflow_events` / `workflow_events_after_stop` use these exact names. `lifecycle.event`
is a free sub-label for other lifecycle records (record-rejected, monitoring-gap, no-envelope) and never stands in for a phase.
`c16_hook.stop_record(ctx, reason, outcome_real)` sets phase `stop` and `CANCELLED_C16` (C16 halt) or `CANCELLED_RAIL` (X-05).

**Content fields (fix round 1; names ratified here, ARCH leaves them unnamed).** EP-4 `judgment.disposition`
(auto-resolve|gather-evidence|escalate|halted), `judgment.evidence_ids`, `judgment.result_digests`, `judgment.reversible_step`,
`judgment.precedence_rule` (judgment records only); EP-3 `tool.use_id`, `suspicious_tool_output` (bool, ARCH spelling); EP-5
`handoff.status` (OK|ERROR|TIMEOUT|HALTED|REFUSED), `handoff.halted`, `handoff.duration_ms`, `tally.tokens`, `tally.calls`
(in on handoff.sent, out on handoff.received); RT-01 echo on the start-up lifecycle record: `prompt.sha256` +
`rails.policy_sha256` (+ `rails.mode`). `rail.*` stays rail_decision-only.

**Content fields (fix round 2, orchestrator D-D; all optional).** EP-3 is written before and after the call:
`tool.phase` (before|after) and `tool.result_sha256` (64-hex, the after record's result digest). J2 (ARCH §7.1) on judgment
records: `judgment.model_disposition` (what the model said before the precedence rules), `judgment.valid`,
`judgment.reasked` (bools), `judgment.evidence_needed` (list of names). Duplicate guard (AR-18): `lifecycle.duplicate_state`
(new|in-flight|completed|seen). Rails: `rail.intended_action` (proceed|block|modify|halt), what the rail would have done; in
observe `inline.action` stays `proceed`. The null rule when a value is set: `new_record(kind, reason, extra={...}, **fields)`
drops a `null_reasons` entry whose field holds a value; after construction use `set_field(rec, name, value[, reason])` or
`prune_null_reasons(rec)`. The validator still refuses a stale reason (`null_reasons.<f>: field is not null`).

**Findings.** `finding.validate_finding` applies every handoff-3 `finding_context.parse_context` refusal (numbers not bool,
required sub-keys, text <= 200 chars without newlines, trace <= 200 steps with at/actor/zone/action, retest.verdict).
`verdicts.notify_due` is True for BREACHED, INDETERMINATE and ESCALATED.

**Known gaps (PR-01 v1).** The rails §5.2 printed example omits table-A fields; the golden `rail_decision_block.json` is
that example with the null rule applied (`rail_decision_sec52_shape.json` is the verbatim shape, valid only with
`require_table_a=False`). `outcome.real` is a closed enum (add values by PR). Register per-control unknown keys are errors.

**C9 named-run treatments (PR-41; optional register key).** The C9 entry may carry `named_run_treatments`, comma-joined
items `<label>:model-swap:<ifabric agent>:<from model>:<to model>` (e.g. `N8:model-swap:ifabric-it:nemotron-super-120b:nemotron-nano-9b`).
`register.named_run_treatments(entry)` parses it; `validate_register` refuses a malformed item, a swap to the same model, a
duplicate (label, agent) and the key on any entry other than C9. It is NOT a threshold: it declares, before the run, which
named run may run on which changed model. EP-0 (`preflight.ep0`) passes a model change only when the PINNED register (the
`--register-file` whose sha256 equals the pin's `register_sha256`) declares it for the run being started (`--named-run`),
the approved model is `from` and the live model is `to`; it records a declared treatment with both models. Any other model
change still blocks. `registry derive` never writes it and `registry freeze` copies the file bytes, so the key survives
derive -> v1 draft -> freeze unchanged; the lane adds it to the v1 draft's C9 entry by hand (the template already carries it).

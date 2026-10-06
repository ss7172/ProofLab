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
| `transports.py` | `evaluate(q, pin, evaluator_sha256=None)` (delegates to `prooflab.evaluators.c16_core.decide_inline`, passing the embedded core's sha256 when given; verified against PR-02's core on 3.9; any exception -> fail-closed DENY/halt `evaluator-error`, using `c16_core.fail_closed_decision(q, pin, reason)` if the core defines it), lazy re-export of `C16Question`/`Decision`/`PinnedC16`, `EMIT_RECEIPTS`, `DeferredVerdict`, `SourceSpec`, `Window`, `Capture`, `Assessment`, `assessment_id` | ONLY `adapters/runtime/model_call.py` may import `evaluate` (a test enforces it) |

**Rules every writer follows**
- Build records with `new_record(...)` (or `rail_record` / `decision_record`) and call `validate_record` before emit; table-A fields are never absent: value, or null + `null_reasons[field]`.
- `run.id` is the CID and equals `correlation_id`. Pulled platform records use `observation_record_id(system, ref)`.
- Rail verdicts only on `rail_decision` (`control.ref: RAIL`, `control.id: RAIL-<id>`, `register.version: null`, `handoff.id` set). ALLOWs ride compactly as `rails.allow` + `rails.policy_sha256`; `rails.counts` only on the lifecycle record. Nothing rail-shaped ever enters an assessment.
- Never put a cap in a payload: in-path values come only from the pin; the register parse is `prooflab/registry/parse.py` (strict flat-YAML subset = what the kit's no-PyYAML fallback reads identically; kit parity is tested).
- The validator refuses secret-shaped values and keys that name secrets; the exact-value scan (§9.3) is still the real check.

**The dispatcher.** `python3 -m prooflab <verb>` (`prooflab/cli.py`): verbs map to `module:function`, imported lazily; the
function takes `argv` and returns an exit code. Unbuilt verbs print "not built yet" (exit 3). To add or retarget a verb,
ask the contract owner for a one-line change to `VERBS`. Pre-registered: run, query, pack, watch, tail, recheck, register,
humanloop, assess, collect, console, servicenow.

**Tests.** `pytest.ini` runs `tests` and `prooflab/tests` with `--import-mode=importlib` (so per-PR test files may share
basenames); `tests/conftest.py` puts the repo root on `sys.path`. Do not add `tests/__init__.py`.

**Known gaps (PR-01 v1).** The rails §5.2 printed example omits table-A fields; the golden `rail_decision_block.json` is
that example with the null rule applied (`rail_decision_sec52_shape.json` is the verbatim shape, valid only with
`require_table_a=False`). `outcome.real` is a closed enum (add values by PR). Register per-control unknown keys are errors.

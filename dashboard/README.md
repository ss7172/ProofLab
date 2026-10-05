# iFabric Assurance dashboard

The judges' app. Double-click `index.html`: it runs from a file, offline, with no server, no network calls and no install. It reads one evidence pack and recomputes every verdict in the browser from the raw records and the frozen register, so a judge can check the answer without trusting the team.

Until the adapters produce real evidence it shows a **SAMPLE** pack (amber banner). The banner disappears automatically when a real pack is loaded.

## What each page answers (mapped to the judging slides)

| Page | Judging criterion it serves |
|---|---|
| 1 Overview and progression | Levels 1, 2, 3 in order (each counts only if the one before is shown); axis 1, controls complete end to end with a named passing and breaching run |
| 2 Live test | Axis 2 "the live test": the judge names a control and a run or window and gets rule, population, measurement, exceptions, verdict, records, who was told and the gaps in one screen, with the two-minute clock visible. Deep link: `index.html#live/C16/<run-id>` or `#live/C9/window/2026-10-05T10:00/2026-10-05T14:00` |
| 3 Architecture | Axis 2 "the architecture": register out of the live path, stateless evaluator, control holds no threshold, works off the request path, and a live check that the same evaluator survives a second enforcement point |
| 4 Evidence, not logs | Axis 2 "the evidence": every record shown with its bindings (what, which control, threshold version, run, who, when, source); toggle to see the same records as a log; how a stranger verifies it |
| 5 Thresholds | Judgement-day artefact 2 and "dated before the test": per-control metric, limit, tolerance, basis, owner, version, date and the four justifications; every run checked against the register date |
| 6 Gaps and honesty | Axis 2 "the honesty" and artefact 6: every gap with why, impact and next step; every control and auditor question shows its gaps or "none recorded" |
| 7 Human loop | Who was told: incident, owner, delivery read-back, response or silence, re-test status (Level 3 chain) |
| 8 Adversarial tests | Axis 3 bonus and the Hostile and Rogue alert levels: what we attacked, what broke, what we changed |
| 9 Judgement day | The seven artefacts, named runs, evidence file download and a two-minute rehearsal timer |

## Files

| File | Role |
|---|---|
| `index.html`, `styles.css`, `app.js` | The app. No frameworks, no CDN |
| `evaluators.js` | Reference evaluators for C16, C7 and C9. Pure functions; thresholds come only from the register |
| `tests/evaluators.test.js` | `node dashboard/tests/evaluators.test.js` checks them against the masterclass worked examples and edge cases |
| `data/evidence-pack.js` | The pack the app loads (`window.EVIDENCE_PACK = {...}`). Generated, never hand-edited |
| `../tools/pack_evidence.py` | Builds the pack from the team's `evidence/` folder |
| `../tools/make_sample_pack.py` | Builds the SAMPLE pack used for rehearsal |

## Build the real pack

```bash
python3 tools/pack_evidence.py --evidence ~/evidence --app-out ~/evidence/dashboard
```

`--app-out` copies the app beside the evidence, so the S3 submission contains a dashboard the judges can open. Check that `submit.sh` includes `~/evidence/dashboard/`. The packer exits non-zero if the register is incomplete or record ids repeat; sections it cannot find are listed, and the app shows them as gaps.

## Data contract the adapters write

```
evidence/
  register/register.yaml        frozen register (or register.json)
  records/*.jsonl               normalized records, one JSON object per line
  assessments/**/*.json         team evaluator output (ServiceNow handoff section 8.2 shape)
  pack/runs.json                runs, with named pass/breach per control
  pack/expected_events.json     C7 expected events per run, from the scenario definition
  pack/metric_windows.json      C9 hourly windows per runtime (value null when missing)
  pack/human_loop.json          findings and their ServiceNow delivery and response
  pack/levels.json  pack/architecture.json  pack/adversarial.json
  pack/gaps.json    pack/auditor.json       pack/artefacts.json  pack/meta.json
  raw/...                       untouched source captures that records point to
```

**Register** (`register.controls.C16|C7|C9`): `control_id`, `name`, `mode`, `owner`, `figure_of_record_ep`, `metric`, `observation_limit`, `exception_tolerance`, `measurement_basis`, `rationale` (`why_metric`, `why_value`, `measured_on`, `stops_holding`). Top level: `version`, `version_date`, `status`, `approved`, `source`.

- C16 `observation_limit`: `{operator: "<=", value, unit}`; `exception_tolerance`: `{max_breaching_runs}`
- C7 `observation_limit`: `{coverage_min_pct, gap_operator: "<", gap_limit_ms}`; `exception_tolerance`: `{max_violating_gap_pct}`
- C9 `observation_limit`: `{operator: "<=", max_relative_increase_pct}`; `exception_tolerance`: `{max_violating_windows_pct}`; plus `coverage_min_pct` and `baseline: {<runtime>: {value, unit, id, frozen_at}}`

**Record** (one line in `records/*.jsonl`):

| Field | Meaning |
|---|---|
| `id` | Unique record id |
| `run_id`, `trace_id` | Run (CID) and trace |
| `kind` | `model_call`, `tool_call`, `handoff`, `ledger`, `escalation` or `decision` |
| `ep` | Enforcement point that observed it (`EP1` gateway, `EP3` spans, `LEDGER`, ...) |
| `actor`, `at`, `summary` | Who, when (ISO-8601 UTC with ms), what happened in words |
| `source` | `{system, ref}`, where `ref` points into `raw/` (for example `raw/gateway/<run>.jsonl#L12`) |
| `call_id`, `input_tokens`, `output_tokens`, `retry` | Model calls (C16). Same `call_id` = same call, counted once |
| `expected_event_id` | Links the record to a C7 expected event |
| `tool`, `decision`, `declared` | Tool calls; `declared: false` flags an undeclared tool |
| `control_ref`, `control_id`, `threshold_version`, `threshold_value`, `measured_value`, `verdict`, `mode` | Decision records: the bound evidence a control emits |

Verdicts everywhere: `SATISFIED`, `BREACHED`, `INDETERMINATE` (data missing), `NOT_ASSESSED` (nothing in scope), plus `ESCALATED` for agent escalations.

## Rules the evaluators follow

- C16: duplicate observations of one call count once; a known total over the cap is BREACHED even with missing counts; under the cap with missing counts is INDETERMINATE; no records is INDETERMINATE.
- C7: expected events come from an independent source; a missing event makes its two gaps unmeasurable rather than bridging them; negative gaps are flagged as clock skew; zero expected events is NOT_ASSESSED.
- C9: higher is worse, relative increase against a frozen baseline; a missing window is INDETERMINATE, never healthy; a run's answer is the hour windows it fell in.
- Every run is checked against the register date: a threshold dated after the test is shown as a failure.

## Assumptions to confirm

1. The app ships inside the evidence folder (`~/evidence/dashboard/`) so the judges' S3 copy opens it.
2. Thresholds in the sample are placeholders; the real ones come from the frozen `register.yaml`.
3. C9 is framed as hourly AgentCore latency per runtime, as in the team handoff.

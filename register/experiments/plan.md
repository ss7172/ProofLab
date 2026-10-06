# Pre-registered experiment plan (ARCH 5.4 step 1; IMPLEMENTATION-PLAN T1.6)

Status: DRAFT until frozen with `v0-pilot` and uploaded (T1) before the first pilot. Dated by that freeze, not by this file.
Nothing below carries a threshold number: every value is the owner's (appetite) or measured by a pilot, then written into the register with the four answers.

## 1. Order of work

1. Owner confirms every rating and appetite in `risks.yaml` (they are written before any pilot; the appetite is the upper bound of every derivation).
2. Freeze the agents (images built, approved, READY; digests and models recorded). Any later undeclared agent change is a new treatment and restarts this plan. Declared treatments (the N8 model swap and its revert) and EP settings (pins, modes) do not.
3. Freeze `v0-pilot` (this plan, `register.yaml`, `risks.yaml`) and `inv-1`; upload both write-once (T1). `v0-pilot` declares `inline_modes: observe` only, and its cap equals the safety ceiling (labelled so in `why_value`). It is EXPLORATORY and never used for an assessment.
4. Run the pilots below (provenance PILOT, at least 2 minutes apart), log each to `register/experiments/experiments.jsonl`.
5. Derive each value with the rules in section 3 (`prooflab register derive`), write the four answers citing pilot ids, the owner approves, freeze `v1` (T1; T2 corroborates through the approval Finding).

## 2. The pilots

| Pilot | Run | Measures |
|---|---|---|
| P1, P2 | S1 x2 | C16 normal spend; C7 achieved coverage and the gap distribution; C9 latency per runtime |
| P3, P4 | S3 x2 | The same on the escalation path |
| P5, P6 | S2 x2 | S2's natural spend: decides breach lever (a) |
| P7 | S2 plus the declared `conflicting-context` text | The condition's effect on spend: decides lever (b) |
| P8 | S1 with `ifabric-it` swapped to the declared model, then reverted | Whether M1, M2 or M3 move under a swap and in which direction: informs C9's metric, never the limit or its direction |

P1 to P4 also measure the projection error of the in-path bound (sets `inline_bound_margin_pct`) and the end-of-invocation flush time. Phase 1 runs P1, P3 and P5 (P7 only if P5 does not decide lever (a)).
P1 and P3 are declared baseline-eligible for C9 (DC-11); the reuse of N1, N3, N5 and N6 as baseline runs is declared in `v1`.

## 3. Derivation rules (frozen before any pilot; `register/experiments/rules.json`, sha256 cited by every derived value)

The rules file carries the numbers (headroom, rounding step, the owner's appetite); `derive.py` carries none.

- **C16-cap (rule id in the file as `c16_rule_id`).**
  - need = the largest total tokens of the eligible runs (scenarios S1 and S3, provenance PILOT or BASELINE, no condition).
  - cap = need plus the declared headroom, rounded up to the declared step.
  - Upper bound: the owner's appetite for one run. If cap would exceed it, there is NO value: the item is `NORMAL_NEED_ABOVE_APPETITE`, a finding about the agents raised to the owner. The cap is never raised to fit.
  - The cap is never derived from S2 or from a condition run, and `derive` refuses to cite one.
  - Tiers: a single tier `default` unless the captain adopts D2; then the owner's 5x5 matrix maps declared scenario attributes to a tier and each tier has its own rule row.
- **C7-gap.** need = the largest gap of the eligible runs; limit = need plus headroom, rounded up. Bounded above by the appetite (the longest silence the owner accepts); if the normal gap is above it, that is a finding about the recording, not a looser limit. Coverage and the violating-gap share come from the appetite (Low: all expected events; the share is the owner's).
- **C9-baseline.** Per (runtime, scenario): the largest Maximum over the declared baseline-eligible runs, n stated in `why_value`. The change limit and the violating-window share are the owner's, above the baseline spread and at most the appetite. The limit is two-sided and is never fitted to the breach run.

## 4. Risk matrix to tier to cap (only if D2 adopts tiers)

One 5x5 scale (likelihood x severity; Low 1-4, Medium 5-9, High 10-16, Critical 20-25), declared once at the top of `risks.yaml` and reused by `tier_rule`. Each tier gets a cap from the same rule; the post-run test re-derives the tier from the declared scenario attributes and records any mismatch with the envelope.

## 5. Draft four answers per threshold (the owner confirms; PENDING values are filled from the pilots)

| Control | Why this metric | Why this value | Measured on | Stops holding when |
|---|---|---|---|---|
| C16 | A loop overspends or calls are charged to the wrong run (S2: 174 calls, 1,999,001 tokens) | Owner's appetite for a run bounds it above; the S1 and S3 pilots bound it below; pilot ids cited | P1, P3, P5 | Agents, model or rails policy change; usage stops being reported per call |
| C7 | Records go missing (S2 left 16 ledger records for 174 calls) | Coverage from the Low appetite; gap from the pilots' normal gaps; share from the appetite | P1, P3, P5 | Workflow spec or emit transport changes |
| C9 | A model change nobody reviewed goes unnoticed (IT Maximum 278.4 s against 8.2 to 8.5 s) | Baseline from declared eligible runs (n stated); limit from the appetite above the spread | P1, P3, P8 | Warm-up or session policy changes; too few baseline runs |

## 6. Rules

- Pilot and baseline run ids never appear in `run-ids.txt` (`prooflab register run-ids` checks it against `experiments.jsonl`).
- A threshold change after a freeze is a new version with new assessed runs; old results are kept.
- `experiments.jsonl` (run id, time, agent versions, mode, condition, measured values) and the derivation notes go into the pack.
- The breach levers (natural S2 in `observe`, or `conflicting-context`, the declared `suppress-record` fault, the declared model swap) are declared in the register before any assessed run; the declared faults `suppress-record` and `inject-tool-output` sit inside the pin.

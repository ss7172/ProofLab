# Adoption of the derivation rules (rules.json)

`rules.json` is the ops lane's frozen, write-once upload. Its `_status` text calls the values lane placeholders
written at 2026-10-06T08:11:00Z, before pilot P1. That file is not edited.

The captain adopted the values below at **2026-10-06T08:40Z**. That was before the restarted pilots ran, so for them
the adoption is not post-hoc.

| Rule | Adopted value |
|---|---|
| C16 headroom (`c16_headroom_pct`) | 20 percent |
| C16 round-up step (`c16_round_up_to`) | 1,000 tokens |
| C16 appetite (`appetite_tokens`) | 100,000 tokens per run |
| C7 gap headroom (`c7_headroom_pct`) | 50 percent |

The other keys (`c7_round_up_to` 1,000, `eligible_scenarios` S1 and S3, the three rule ids) are unchanged.
Pilot P1 ran earlier under the placeholder values and is marked halted and not derivation-eligible in `experiments.jsonl`.
This record changes no number; it states who owns the values from 08:40Z.

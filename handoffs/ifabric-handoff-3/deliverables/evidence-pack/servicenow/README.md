# `evidence/servicenow/`: what goes here and how it is produced

This folder in the **real** pack is filled by the evaluator loop and a few commands. Right now it contains only `wiring-tests/` (test-only history).

| Path in the final pack | Produced by | When |
|---|---|---|
| `delivery-log.jsonl` | `notify`, `check`, `analyze` (automatic, append-only) | during runs; **the evaluator loop's own log, never the wiring-test log** |
| `incidents/INC*.json` | `python3 -m prooflab.servicenow export --finding <f> --out evidence/servicenow/incidents` | after the final `check`, the evening before |
| `assurance-agent/*.json` | `run_assurance_agent` / `analyze` (automatic) | one record per agent run |
| `cases/<finding>.json` | `python3 -m prooflab.servicenow case --finding <f> --cutoff <c> --out evidence/servicenow/cases` | after analysis and the final `check`, for every named run |
| `aict/` | Arth: CloudTrail `AssumeRole` record, discovered-assets export, timestamped screenshots (Inventory incl. `ifabric_assurance_agent`, Monitor) | after the named runs |
| `wiring-tests/` | already here | test-only history, excluded from verdicts |

Before submitting, run:
- `check` with the final cutoff;
- `export` for every finding;
- `case --out` for every named run;
- then `python3 tools/manifest.py build <evidence>`.

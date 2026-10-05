# ServiceNow human loop (iFabric ProofLab)

Turns a control **finding** into a ServiceNow incident assigned to the named
control owner, verifies it by read-back, and later records the owner's
response — or their silence after a cutoff. Every step is appended to a JSONL
log that goes into the Evidence Pack.

It is independent of the AWS agents: any evaluator (C7, C9, C16) or agent
escalation only has to produce a finding in the format below.

## The finding contract (what evaluators hand over)

```json
{
  "control_ref": "C16",
  "control_id": "ACN-COST-001",
  "threshold_version": "G-FM-v1",
  "scope_kind": "run",
  "scope_id": "FM-B",
  "verdict": "BREACHED",
  "summary": "10,800 tokens > cap 10,000",
  "detected_at": "2026-10-05T10:00:00Z",
  "evidence": ["gateway:action-123", "ledger:cid=fault-1788864931"],
  "kind": "finding"
}
```

| Field | Rule |
|---|---|
| `control_ref` | `C7`, `C9` or `C16` (or e.g. `ESC` for an agent escalation) |
| `control_id` | library id, e.g. `AIA-LOG-001`, `AIA-ARC-006`, `ACN-COST-001` |
| `threshold_version` | the frozen version from `register.yaml` |
| `scope_kind` | `run`, `window`, `interval` or `escalation` |
| `scope_id` | run id, window start (e.g. `2026-10-05T09`), or ledger correlation id |
| `verdict` | `BREACHED`, `ESCALATED`, `INDETERMINATE` or `SATISFIED` |
| `summary` | measured value vs limit, human readable |
| `detected_at` | ISO-8601 UTC |
| `evidence` | optional list of record references (strings) |
| `kind` | optional, default `finding` |

Same control + threshold version + scope + kind ⇒ same finding id ⇒ the same
incident is reused, never duplicated. Each C9 drift crossing should be its own
finding (`scope_kind: "window"`), even if the overall exception allowance passes.

## Run it

```bash
export SNOW_INSTANCE=platformdemoh8.service-now.com
read -r SNOW_CLIENT_ID && export SNOW_CLIENT_ID          # paste Client ID, Enter
read -rs SNOW_CLIENT_SECRET && export SNOW_CLIENT_SECRET # paste Client Secret, Enter
# optional: SNOW_OWNER_USER (default annapurna@invences.com),
#           PROOFLAB_DELIVERY_LOG (default evidence/servicenow/delivery-log.jsonl)

python3 -m prooflab.servicenow selftest                          # read-only check
python3 -m prooflab.servicenow notify --finding f.json --dry-run # shows payload, writes nothing
python3 -m prooflab.servicenow notify --finding f.json           # opens/reuses the incident
python3 -m prooflab.servicenow check  --finding f.json --cutoff 2026-10-06T14:00:00Z
python3 -m prooflab.servicenow export --finding f.json           # evidence/servicenow/incidents/INC*.json
```

Incidents are created by `ifabric.integration` (also set as **Caller**, which the
incident form requires) and assigned to the owner. `export` saves the incident
exactly as ServiceNow stores it, plus all work notes, for the Evidence Pack.
On macOS python.org builds, set `export SSL_CERT_FILE=$(python3 -m certifi)` first.

Exit codes: `0` ok, `1` ServiceNow problem, `2` bad input or configuration.

## Delivery states (in the log)

`INTENT` → `SENT` → `DELIVERED` (read-back matched correlation id and assignee) ·
`FAILED` · `OUTCOME_UNKNOWN` (request may have landed; reconciled by correlation id) ·
`DRY_RUN` · `RESPONDED` (owner note or field change, with actor and time) ·
`AWAITING_RESPONSE` · `NO_RESPONSE_OBSERVED` (only after the cutoff) ·
`RESPONSE_UNKNOWN` (history unreadable — not treated as silence) · `NOT_DELIVERED`.

A human reply is not required by the hackathon; the alert, the named recipient
and the observed response or silence are what get recorded.

## Tests

```bash
python3 -m pytest prooflab/tests -q   # uses a local fake ServiceNow, never the shared instance
```

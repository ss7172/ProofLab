# Threshold register approval (Sree): workflow

**Why:** the judges check that every threshold is **dated before the test** and approved by a **named owner who is not the builder**. A ServiceNow incident with Sree's dated work note gives a timestamp and identity that a stranger can check (Playbook §3.1). It reuses our existing adapter: **no new code**.

**When:** after the exploratory baseline runs, and **before the first assessed run**. This is the hard gate.

## Steps

| # | Who | Action | Output |
|---|---|---|---|
| 1 | Teammate | Run the exploratory baseline runs (label them **exploratory**). Fill `register.template.yaml` → `register.yaml`: every `<...>` placeholder, plus the four justifications per control. `status: DRAFT`. | `register.yaml` (DRAFT) |
| 2 | Arth | Review against Playbook §3.1: every field present, owner = `annapurna@invences.com`, no threshold missing, comparison operators explicit, missing-data rule stated. | review OK |
| 3 | Teammate + Arth | Set `status: FROZEN` and `frozen_at` (now, UTC); from here the file is never edited. Arth computes the file hash: `shasum -a 256 register.yaml`. Copy `approval-finding.template.json` → `approval-finding.json` and fill it: version, `scope_id`, first 12 hex of the hash in `summary`, full hash in `evidence`, `detected_at` = now (UTC). | `approval-finding.json` |
| 4 | Arth | Raise the approval request (ServiceNow secrets loaded as in handoff 1 §5.3). **First point the log at its own file**, so approval records never mix with test or run logs: `export PROOFLAB_DELIVERY_LOG=evidence/register/approval/delivery-log.jsonl`, then `python3 -m prooflab.servicenow notify --finding approval-finding.json`. Expect `DELIVERED` and an INC number, assigned to Sree. | INC number |
| 5 | Arth | Paste the full `register.yaml` text into the incident as a work note, or attach the file, so Sree reviews exactly what is hashed. | — |
| 6 | **Sree** | Open the incident, read the register, add a **work note** with exactly: `APPROVED threshold register <register_version>, sha256 <first 12 hex>`, then click **Update**. If she disagrees, she writes `CHANGES REQUESTED: …` instead; go back to step 1 with a new version. | dated approval note |
| 7 | Arth | (same `PROOFLAB_DELIVERY_LOG` as step 4) `python3 -m prooflab.servicenow check --finding approval-finding.json --cutoff <step-4 time + 24h>` → `RESPONDED` (actor Sree, time), then `python3 -m prooflab.servicenow export --finding approval-finding.json --out evidence/register/approval`. The export's `notes_display.work_notes` contains her APPROVED text. | approval evidence |
| 8 | Arth → Teammate | Arth sends the folder `evidence/register/approval/` (export JSON + its own delivery log) and `approval.md`. Teammate: **do not edit the approved file.** Copy `register.yaml` unchanged to `evidence/register/register.yaml`, and record the approval separately in `evidence/register/approval.md` (template below). | frozen, approved register |
| 9 | Both | Only now start assessed runs. Any later change = new version → repeat steps 1–8. | — |

## Rules
- **Do not run the Assurance Agent (`analyze`) on the approval incident.** It is for control findings only.
- The approval incident is not a control breach. Close it after the event (resolution "threshold register approved").
- Sree's `annapurna@invences.com` account is the owner in the register, the incident assignee and the approver. Arth and the teammate never approve.
- Keep `register.yaml` byte-identical after hashing: the SHA-256 in Sree's note must still match. Status and freeze time are set **before** hashing (step 3); the approval itself lives only in `approval.md` and the incident export.

## `evidence/register/approval.md` (template)
```
Register version: <register_version>
File: evidence/register/register.yaml   sha256: <64 hex>
Approval request: ServiceNow <INC number>, raised <UTC time> by ifabric.integration, assigned to annapurna@invences.com
Approval: work note "APPROVED threshold register <version>, sha256 <12 hex>" by Sree Annapurna Rallabandi at <ServiceNow time> (check → RESPONDED <UTC>)
Evidence: evidence/register/approval/<INC>.json (incident export), evidence/register/approval/delivery-log.jsonl (INTENT → DELIVERED → RESPONDED)
First assessed run after approval: <run id, UTC time>
```

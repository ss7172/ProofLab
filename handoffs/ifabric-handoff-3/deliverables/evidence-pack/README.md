# Evidence Pack: team iFabric (Artefact 1 of 6)

> **Teammate:** this is the skeleton of the final `evidence/README.md`. Fill every `<...>`, keep the structure, and delete this note. The ServiceNow sections (§7–§9) are complete.

**For:** a sceptical stranger (a judge or an auditor), now or years later. It explains how to verify every verdict **without us**.

## 1. What this pack proves
- **Claim C-FM-01:** "During customer fault resolution, the three collaborating agents meet our declared event-recording, drift and performance, and token-spend requirements."
- **Controls:** C16 ACN-COST-001 (per-run token cap), C7 AIA-LOG-001 (event recording), C9 AIA-ARC-006 (drift/performance). Thresholds, owners and versions: `register/register.yaml`, approved by Sree Annapurna Rallabandi (`register/approval.md`).
- **Named runs** (written down before judging): `run-ids.txt`.

## 2. Retention rule
Evidence in this pack is **kept for 7 years from the submission date (<YYYY-MM-DD>)**, in the team S3 bucket with object versioning, plus an offline copy held by the team. *(Hackathon note: the event account is deleted after the event; this states the rule we would operate under in production.)*

## 3. Integrity: was anything changed after hand-in?
1. Every file is listed in `MANIFEST.json` with SHA-256 and size. To check: `python3 tools/manifest.py verify .` → `OK: every file matches MANIFEST.json`. (`tools/manifest.py` is standard-library Python 3.9+; read it, it's about 80 lines.)
2. Raw captures under `raw/` are never edited; corrections are new files.
3. Ledger integrity: `raw/ledger/verify-<date>.txt` (the audit store's own verification output).
4. S3 upload: key, ETag/version id and upload time are recorded in §10.
This is a checksum list, **not** a signature or hash chain (out of scope).

## 4. Layout
```
README.md            this file          MANIFEST.json       SHA-256 of every file
run-ids.txt          named PASS/BREACH runs + windows, written before judging
gap-list.md          what we could not close, why, impact, next step (scored)
decisions-log.md     dated decisions (thresholds, platform, ServiceNow)
architecture.md      one-page architecture (or architecture.jpg whiteboard photo)
register/            register.yaml (frozen, approved) · approval.md · approval/INC*.json
raw/                 untouched captures: gateway/ ledger/ cloudwatch/ cr-status/ pdp/  <teammate: list>
assessments/         C7/ C9/ C16/ ESC/: one JSON per control x scope (+ revisions)
findings/            the Finding JSON files sent to ServiceNow
servicenow/          delivery-log.jsonl · incidents/INC*.json · assurance-agent/*.json · cases/*.json · aict/
adversarial/         attack -> expected defence -> observed -> evidence refs -> what broke / what changed
tools/manifest.py    integrity check
```

## 5. Answer "was control X satisfied for run R?" yourself
`<teammate: the query tool command, e.g. python3 -m <tool> query --control C16 --run FM-B>`. It prints rule, version, date, owner; expected vs observed; measured vs limit; exceptions; verdict; gaps; record refs; the human-loop line; the AICT line.

To recompute by hand (no tool):
- **C16:** `<teammate: steps, e.g. filter raw/gateway/*.jsonl by run.id; sum input+output tokens of every call incl. retries; compare with register C16 observation_limit; any run over → NOT satisfied>`
- **C7:** `<teammate: expected-event source, reconciliation, gap computation>`
- **C9:** `<teammate: baseline, closed UTC windows, relative change, crossings; a missing window = monitoring gap>`

## 6. The six auditor questions → where the answer is
| Question | Files |
|---|---|
| Who acted? | `assessments/*` (actors); gateway caller identity in `raw/gateway/`; AgentCore runtime (also in `servicenow/aict/`) |
| What did it touch? | `raw/gateway/` (model alias, tool), ledger chain in `raw/ledger/` |
| Was it authorized? | Cedar/PDP decision lines `raw/pdp/`, guardrail result, approved CR status `raw/cr-status/` |
| Who approved? | CR approvals (approver, attestation, time) in `raw/cr-status/`; `register/approval.md` (Sree); incident owner and response in `servicenow/` |
| Can we trust it hasn't changed? | Ledger verification `raw/ledger/verify-*.txt`, `MANIFEST.json` + `tools/manifest.py`, S3 version ids (§10) |
| Can we reconstruct it? | Ledger `/records?cid=` chain + spans by trace id + gateway lines in time order; ServiceNow case timeline `servicenow/cases/<finding>.json` |

## 7. ServiceNow: the human loop (who was told)
- Every breach or escalation became an incident **assigned to the named owner** (Sree), written by `ifabric.integration`, read back after writing (`DELIVERED`).
- `servicenow/delivery-log.jsonl` (append-only): `INTENT → SENT → DELIVERED` → `RESPONDED` (owner action, with time) or `NO_RESPONSE_OBSERVED` (silence after the stated cutoff). A reply is not required; silence is recorded.
- `servicenow/incidents/INC*.json`: each incident exactly as ServiceNow stores it, plus its work notes.
- Same id everywhere: `finding_id` = incident `correlation_id` = the id in `findings/` and `assessments/`.

## 8. ServiceNow: the Assurance Agent (Level 3)
- After an incident is delivered, the **Assurance Agent** asks **NVIDIA Nemotron through the governed gateway `modaas-agw`** to analyze it, and writes one note on the incident: facts checked against the finding, plus Nemotron's judgement (measured vs limit, evidence refs, missing evidence).
- `servicenow/assurance-agent/*.json` holds one record per run:
  - prompt and response SHA-256 (no reasoning text is stored);
  - the gateway action id (`x-modaas-action-id`, joins to `raw/gateway/` and the ledger);
  - the model alias and id, token usage;
  - the outcome (WRITTEN / REFUSED / BLOCKED …) and the exact note written.
- A note counts as the agent's **only if its SHA-256 is in the delivery log** (`ANALYSIS_WRITTEN … note_digest`). Look-alike notes typed by anyone else are flagged, never trusted.
- `servicenow/cases/<finding>.json`: the dashboard view frozen at submission (finding → incident → owner → analysis → AICT link).

## 9. ServiceNow AI Control Tower (Level 2)
`servicenow/aict/`:
- the CloudTrail `AssumeRole` record of the connector's read-only role;
- the discovered-assets export;
- timestamped screenshots (Inventory → our runtimes incl. `ifabric_assurance_agent`, Monitor sessions/traces) for the named runs.

Gaps in AICT coverage are listed in `gap-list.md`.

## 10. Submission record
`<teammate: S3 bucket, keys, ETag/version ids, upload time (UTC), readback result, MANIFEST verify result>`

## 11. Test-only material
Anything labelled **wiring test** / **TEST ONLY** (e.g. `servicenow/wiring-tests/`) proves the integration works but is **not** a control result and is excluded from all verdicts.

## 12. People
- **Owner** (accountable, approves thresholds): Sree Annapurna Rallabandi, annapurna@invences.com
- **Builder** (AWS agents, controls): `<teammate>`
- **ServiceNow integration and Assurance Agent:** Arth

Nobody approves their own work.

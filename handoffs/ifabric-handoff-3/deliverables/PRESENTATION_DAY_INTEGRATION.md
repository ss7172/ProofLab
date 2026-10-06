# Presentation day: how to combine Arth's deliverables with yours

**Scope:** only what judging requires on the day:
- the **six artefacts** (all in the team S3 bucket, submitted **the evening before** and read back);
- the **15-minute live slot**.

The judges read **S3, not laptops**. "If an artefact is missing, we cannot score it."

Everything else in this folder (handoffs, playbook, templates, `TEAMMATE_ACTIONS.md`) is **working material, not a deliverable**. Don't submit it.

---

## 1. Who brings what, and where it ends up

| # | Artefact | **You (teammate)** provide | **Arth** provides | Combined result (final location in S3: `evidence/…`) |
|---|---|---|---|---|
| 1 | **Evidence file** | Raw captures, assessments, findings, `run-ids.txt`, the production ServiceNow records (your evaluator loop writes them using our code), MANIFEST, upload + readback | `evidence-pack/` skeleton (README, gap list A, decisions log, `tools/manifest.py`), `servicenow/aict/` (AICT proof), `servicenow/wiring-tests/` | the whole `evidence/` tree (§2) |
| 2 | **Threshold document** | `register.yaml` (values + 4 justifications) | template; Sree's approval: `approval.md` + `approval/` (export + its own log) | `evidence/register/register.yaml`, `approval.md`, `approval/` |
| 3 | **Control test tool + demo** | your query tool (CLI/app) and the live demo; the finding context (`measured`, `limit`, `register`, `trace`) on every finding | the human-loop and Assurance Agent data, including the five assurance sections (`case_view`, dashboard panel) | the tool runs on the day; recommended: its source in `evidence/tool/` with a 5-line README |
| 4 | **Two named runs per control** | `run-ids.txt` (PASS + BREACH ids and time windows, written **before** judging) | the INC number per BREACH run (from the delivery log) for the notes column | `evidence/run-ids.txt` |
| 5 | **One-page architecture** | your page or whiteboard photo | `architecture/servicenow-section.md` (EP2, Assurance Agent, AICT, dashboard) | `evidence/architecture.md` (or `.jpg`), plus a printed copy |
| 6 | **Gap list** | Section B (AWS agents and controls) | Section A (18 ServiceNow/platform entries), statuses updated | `evidence/gap-list.md` (one file; you own it, Arth reviews) |
| — | **15-minute slot** | L1, ledger, controls, query tool, adversarial | AICT (L2), the evidence chain + Assurance Agent (L3), second EP | `pitch/running-order-15min.md` + `pitch/pitch-L2-L3-script.md` |

---

## 2. The final `evidence/` tree (what goes to S3)
```
evidence/
├── README.md               ← from evidence-pack/README.md; fill every <...>, delete the "Teammate" note
├── MANIFEST.json           ← generated last: python3 tools/manifest.py build .
├── run-ids.txt             ← YOURS (template: evidence-pack/run-ids.txt); add INC numbers from Arth
├── gap-list.md             ← MERGED: Arth's Section A + your Section B
├── decisions-log.md        ← from evidence-pack/decisions-log.md; append your threshold/AWS decisions
├── architecture.md         ← YOURS, with the ServiceNow half from architecture/servicenow-section.md
├── register/
│   ├── register.yaml       ← YOURS, frozen, byte-identical to what Sree approved
│   ├── approval.md         ← from Arth
│   └── approval/           ← from Arth (incident export + approval delivery log)
├── raw/                    ← YOURS (gateway/ ledger/ cloudwatch/ cr-status/ pdp/), never edited
├── assessments/            ← YOURS (C7/ C9/ C16/ ESC/)
├── findings/               ← YOURS (the Finding JSONs sent to ServiceNow)
├── adversarial/            ← YOURS + Arth's agent cases (injected ticket → REFUSED, guardrail → BLOCKED)
├── servicenow/
│   ├── delivery-log.jsonl  ← written by YOUR evaluator loop (notify/check/analyze), production only
│   ├── incidents/          ← YOU run `export` for every finding (after the final `check`)
│   ├── assurance-agent/    ← written automatically by run_assurance_agent
│   ├── cases/              ← YOU run `case --out` for every named run (after analysis + final check)
│   ├── aict/               ← from Arth (CloudTrail AssumeRole, discovered assets, screenshots)
│   └── wiring-tests/       ← from Arth, copied as-is (TEST ONLY, excluded from verdicts)
├── tool/                   ← recommended: your query tool source + README (so a stranger can run it)
└── tools/manifest.py       ← from evidence-pack/tools/ (tests not needed in S3)
```

---

## 3. Integration steps (evening before judging), in order

| # | Who | Step | Check |
|---|---|---|---|
| 1 | You | Stop assessed runs. Run `check` with the **final cutoff** for every finding, then `export` (→ `servicenow/incidents/`) and `case --out` for every named run (→ `servicenow/cases/`). | every BREACH/ESC finding has an export; every named run has a case file |
| 2 | Arth | Send you: `servicenow/aict/`, `register/approval.md` + `register/approval/`, the INC numbers for `run-ids.txt`, Section A of the gap list with statuses updated (A3, A10, A15–A18), and the Assurance Agent adversarial cases. | files received |
| 3 | You | Build `evidence/` exactly as in §2: copy Arth's files in, fill README placeholders, merge the gap list (A then B), append decisions. | no `<...>` left (`grep -rn "<" evidence/*.md` shows only intentional text) |
| 4 | You | **Never** copy `wiring-tests/delivery-log-wiring-tests-ONLY.jsonl` into `servicenow/delivery-log.jsonl`, and never mix exploratory runs into assessments. | production log has no `TEST` / `wiring-test` findings |
| 5 | Arth | Review: README, merged gap list, `servicenow/`, `register/`. Run the dashboard against the final `evidence/servicenow/delivery-log.jsonl`; all named-run cards should show their expected states (no unexpected red), and each BREACH card shows the agent path and `Policy x/y` / `Outcome validated` pills that match the case files. | sign-off in chat |
| 6 | You | `python3 evidence/tools/manifest.py build evidence` (from the folder that contains `evidence/`) → `submit.sh` to the team bucket → **read back**: list keys, `head-object`, download and run `manifest.py verify`. Record keys, ETags and time in README §10. | `verify` prints OK on the downloaded copy |
| 7 | Both | No edits after upload. If something must change: fix, rebuild MANIFEST, re-upload, re-verify, log it in `decisions-log.md`. | — |

---

## 4. On the day: what each of you has open
- **You:** the query tool in a terminal, the named runs printed (`run-ids.txt`), the architecture page (printed), the ledger/gateway views for L1.
- **Arth:** AI Control Tower Inventory (press **Execute Now** about 20 minutes before), the dashboard on the named runs, one incident open in ServiceNow, and `pitch/pitch-L2-L3-script.md`.
- **Backup (no network needed):** `prooflab/servicenow/panel/index.html` opened from disk with the files in `evidence/servicenow/cases/`; optional recorded video (`pitch/backup-demo-shot-list.md`).
- **Order:** follow `pitch/running-order-15min.md`. Judges ask; the tool answers; nobody narrates.

## 5. Final checklist (tick before submitting)
- [ ] All six artefacts in S3 at the paths above, read back, MANIFEST verified.
- [ ] `register.yaml` approved by Sree **before** the first assessed run (dates prove it).
- [ ] `run-ids.txt` written before judging, with a PASS and a BREACH per control and their INC numbers.
- [ ] Every BREACH/ESC finding: incident export + Assurance Agent result (WRITTEN, or an honest REFUSED/BLOCKED) + owner response or recorded silence.
- [ ] Every named run's finding carries `measured`, `limit`, `register` and the agents' `trace`, so its case file shows agent movement and policy alignment. Any that can't are listed in the gap list (A17).
- [ ] Gap list merged, statuses true, "built properly: yes, actually worked: no" items included where relevant.
- [ ] No secrets anywhere (OAuth secret, gateway key, tokens, IdeUrl/CockpitUrl, presigned URLs).
- [ ] Rehearsed twice, with someone outside the build asking the judges' questions.

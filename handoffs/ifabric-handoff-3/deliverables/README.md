# iFabric: ServiceNow-side deliverables (from Arth)

Everything from the ServiceNow workstream, ready to integrate with the AWS side. **Start with `TEAMMATE_ACTIONS.md`** (the work, in order). For judging day, **`PRESENTATION_DAY_INTEGRATION.md`** explains how to combine these with your own deliverables. Date: 2026-10-05.

## Contents
| Path | What | Who uses it |
|---|---|---|
| `TEAMMATE_ACTIONS.md` | Everything the plan needs from the teammate, in order, with "done when" checks and artefact ownership | Teammate |
| `PRESENTATION_DAY_INTEGRATION.md` | How to merge Arth's pieces with yours into the six judging artefacts: final S3 `evidence/` tree, evening-before steps, on-the-day setup, final checklist | Both |
| `../code/prooflab/` (handoff-3 package root) | The code (`prooflab/servicenow`: incident adapter, Nemotron Assurance Agent with the five assurance sections, case JSON, dashboard panel, local server) + 152 tests. It is the already-sent v3 plus the P6 re-test fix and two panel honesty fixes (see the handoff-3 README). Handoff 1, the playbook and `evidence-console-plan/` sit next to it | Teammate (merge) |
| `docs/SERVICENOW_INTEGRATION_HANDOFF.md` | Handoff 1: incidents, Finding contract, wiring per control, evidence layout | Teammate |
| `../evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md` | **Single source of truth** for the Nemotron Assurance Agent + its GUI (replaces the old handoff 2 file, same section numbers; the old file is archived). The whole dashboard plan is in `../evidence-console-plan/` (start with its README). §5.0 = the finding context your evaluator must attach; §8 = the Assurance Agent section; §8.7 = the five assurance sections (agent movement, decision trace, evidence, policy alignment, outcome validation) | Teammate |
| `docs/HACKATHON_WINNING_PLAYBOOK.md` | Brief, scoring rules, best-practice checklist, scorecard | Both |
| `thresholds/register.template.yaml` | Threshold register (Artefact 2) template: all required fields + 4 justifications; placeholders only | Teammate fills |
| `thresholds/threshold-approval.md` + `approval-finding.template.json` | How Sree approves the register in ServiceNow before any assessed run (reuses our adapter) | Arth runs it, Sree approves |
| `evidence-pack/` | Evidence Pack skeleton (Artefact 1): stranger's README with retention rule, merged gap list (Section A done), decisions log, run-ids template, `tools/manifest.py` (SHA-256 + verify, tested), `servicenow/` guide, wiring-test history | Teammate assembles |
| `architecture/servicenow-section.md` | ServiceNow half of the one-page architecture (Artefact 5): diagram + the facts to state | Teammate merges |
| `pitch/` | 15-min running order (whole team), Arth's L2/L3 script with Q&A, optional backup-video shot list | Both |

## Status (be precise when presenting)
- **Verified live on ServiceNow:**
  - AICT connected and discovering our runtimes;
  - OAuth integration;
  - incident create/read-back/reuse/response detection (INC0010231);
  - full finding text in the incident description (INC0010232);
  - **the Assurance Agent's write path** (2026-10-05, INC0010232, 9/9 checks):
    - note written, read back unchanged (SHA-256 matched), real journal parsed, re-run SKIPPED;
    - the five sections in the case JSON;
    - a TEST stand-in replaced the model; evidence in `evidence-pack/servicenow/wiring-tests/assurance-agent-roundtrip/`.
- **Built and tested, not yet live:**
  - the Nemotron call itself (152 tests against a fake `modaas-agw`). The first live Nemotron run is the teammate's Phase A step 3.
  - Panel checked in Chrome with fake data, in light and dark mode and at 360 px.
- **Superseded:** a ServiceNow-native agent on the ServiceNow LLM; deactivated after the facilitators' Nemotron-only ruling, kept as history only.

## Arth's own remaining actions
1. ~~Run the live ServiceNow round-trip test~~ **Done 2026-10-05: 9/9 passed on INC0010232.** Handoff 3 (`ifabric-handoff-3.tgz`) carries this folder; the older `ifabric-servicenow-deliverables.tgz` is superseded. Share the OAuth Client ID/secret **privately** (never inside the folder or the group chat).
2. Facilitator note (integration user, OAuth property, Nemotron agent runs on AWS via `modaas-agw` and writes into ServiceNow).
3. Review `register.yaml`, run Sree's approval (`thresholds/threshold-approval.md`), and get Sree to approve the `ifabric_assurance_agent` CR.
4. Confirm the parser and digest against the first real note; update gap-list A3/A10/A15/A16/A17/A18 statuses.
5. After the named runs:
   - AICT evidence into `evidence/servicenow/aict/` (CloudTrail AssumeRole, discovered assets, screenshots incl. `ifabric_assurance_agent`);
   - close INC0010231/INC0010232 ("adapter wiring test").
6. Review the merged gap list and the Evidence Pack the evening before; present L2/L3 (`pitch/pitch-L2-L3-script.md`).

**Contains no secrets.** No client id/secret, tokens or presigned URLs. The only account-specific value is the team S3 bucket name in handoff 1.

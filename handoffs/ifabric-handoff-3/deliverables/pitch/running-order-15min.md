# 15-minute live slot: proposed running order (whole team)

> **Current run of show:** `evidence-console-plan/presentation/JUDGING-DAY-GUIDE.html` (simple 8-step script: what to show, say and why; it adds the agent-decisions step and matches the dashboard's ▶ Present mode). This file is the earlier proposal; if they differ, follow the guide.

The playbook's order: **L1 → L2 → L3**, then the controls, adversarial, second EP, gap list. Rules:
- **no slides** (whiteboard photo or one-page architecture only);
- **"we ask, you operate"**: the tool answers, nobody narrates;
- bring all six artefacts, and have the named runs written down.

| Min | Part | Presenter | On screen |
|---|---|---|---|
| 0:00–1:00 | The claim C-FM-01 + the one-page architecture (EP1 gateway, EP2 ServiceNow human queue, register out of path) | Teammate | architecture page |
| 1:00–3:30 | **L1 foundation:** governed Nemotron call (`x-modaas-action-id`, usage); prompt attack → `content_filter`, 0 tokens; direct Bedrock → `AccessDenied`; CR approvals (approver + attestation) | Teammate | terminal |
| 3:30–5:00 | **L2 observability:** ledger evidence for a run; **AI Control Tower** inventory of our runtimes (incl. `ifabric_assurance_agent`) | Teammate (ledger) → **Arth** (AICT) | ledger query; AICT Inventory |
| 5:00–7:30 | **L3 evidence chain:** C16 breach → incident assigned to Sree → response or silence → **Nemotron Assurance Agent note** (checked facts, judgement, provenance) → **assurance analysis** (agent movement, decision trace, evidence, policy alignment, outcome validation) → same id everywhere | **Arth** | dashboard case card; the incident |
| 7:30–11:30 | **Controls C16 → C7 → C9** with PASS and BREACH runs; **judges ask, the tool answers** ("Show me control 16 for run FM-B") | Teammate | query tool |
| 11:30–12:30 | **Adversarial log:** what we attacked, what broke, what we changed (incl. injected ticket → Assurance Agent REFUSED) | Teammate + Arth | `evidence/adversarial/` |
| 12:30–13:30 | **Second enforcement point:** same Finding contract at EP2 (ServiceNow human queue); which adapter changed, which core code didn't | Arth | architecture page |
| 13:30–15:00 | **Gap list**, read confidently; then questions | Both | `gap-list.md` |

**Before the slot:**
- click **Execute Now** in AICT (about 20 minutes before);
- dashboard open on the named runs;
- `run-ids.txt` printed;
- backup ready: case snapshots + `panel/index.html` from disk; optional recorded video.

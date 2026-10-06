# Backup demo (optional): what to record if there is time

**Needed?** Not strictly. The rule is "bring a working **or recorded** demo". If the live demo works, this is only insurance against slow systems. If recorded, keep it **3–5 minutes**, no narration needed beyond captions, with no secrets on screen (no tokens, IdeUrl, client secret, presigned URLs).

**How:** macOS QuickTime → File → New Screen Recording (or Cmd+Shift+5). One take per segment is fine.

| # | Segment | Shows |
|---|---|---|
| 1 | Governed Nemotron call (teammate) | `x-modaas-action-id` + usage; guardrail block; direct Bedrock `AccessDenied` |
| 2 | Breaching run → finding → `notify` | DELIVERED + INC number in the terminal |
| 3 | The incident in ServiceNow | assigned to Sree; the description holds the full finding block |
| 4 | Assurance Agent | `analyze` → WRITTEN; the note on the incident with its provenance line |
| 5 | Dashboard case card | all five steps; green flags; the header pills; the "Assurance analysis" block (agent path, decision trace, policy 8/8, outcome validated); then a REFUSED or forged-note case in red |
| 6 | AI Control Tower | Inventory with our runtimes incl. `ifabric_assurance_agent` |
| 7 | Query tool (teammate) | "Show me control 16 for run FM-B" answered in one screen |

**Offline fallback without video:** open `prooflab/servicenow/panel/index.html` from disk and load the saved case snapshots (`evidence/servicenow/cases/*.json`).

# Decisions log: team iFabric (dated; append only)

Format: date (UTC) · decision · why · who · evidence/reference. **Teammate:** add threshold choices and AWS decisions in the same format.

| Date | Decision | Why | Who | Reference |
|---|---|---|---|---|
| ≤ 2026-10-05 | Connected ServiceNow AI Control Tower via "AI Service Graph Connector for Amazon" (role `SgcAictReadOnlyAccessRole`, log group `/aws/bedrock/aict-invocations`); import schedules every **15 min** (was 1 h) | Near-continuous inventory for L2 | Arth | AICT connection "iFabric Hackathon 2026"; gap A2 |
| 2026-10-05 | Owner for C7, C9, C16 = **Sree Annapurna Rallabandi** (`annapurna@invences.com`) | One named person, not a team; owner ≠ builder | Team | register, incidents' `assigned_to` |
| 2026-10-05 | Integration user `ifabric.integration` (role itil only), set as incident Caller | Least privilege; the Caller field is mandatory on the form | Arth | handoff 1 §2 |
| 2026-10-05 | Basic auth abandoned (401) → **OAuth client credentials**; enabled `glide.oauth.inbound.client.credential.grant_type.enabled` (Global) | Instance auth policy; scripts need non-interactive auth | Arth | gap A5; facilitators informed |
| 2026-10-05 | Incidents are read back after writing; reuse by correlation id; never re-sent blindly; only incidents created by `ifabric.integration` are ours | No duplicates, no false "delivered", no touching other teams' records | Arth | handoff 1 §4 |
| 2026-10-05 | Owner responses detected from the incident's last update (itil can't read journal rows) | ACL limit | Arth | gap A8 |
| 2026-10-05 | Incident **description carries the full finding block** (incl. evidence refs) | Readers without journal access must see the evidence | Arth | INC0010232 (live) |
| 2026-10-05 | Built a ServiceNow-native assurance agent (AI Agent Studio, ServiceNow LLM); one live test on INC0010232 correct on every field | L3 prototype | Arth | `servicenow/wiring-tests/sn-agent-prototype-superseded/` |
| 2026-10-05 | **Facilitator ruling: the Assurance Agent must use Nemotron.** ServiceNow agent **deactivated** (16:30:35 instance time); Assurance Agent moved to AWS: Nemotron via `modaas-agw`, writes one validated note into the incident | Nemotron reachable only through the governed gateway; no public endpoints | Arth | gap A9; `evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md` (formerly handoff 2) |
| 2026-10-05 | The model judges only 3 fields; the 9 fact fields (incl. **Next step = policy text per verdict**) must be echoed exactly or nothing is written | The model cannot hallucinate or be injected into the record | Arth | `evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md` §5.4 |
| 2026-10-05 | A note is the agent's only if its SHA-256 is in our delivery log | Look-alike notes can be typed by anyone | Arth | gap A13 |
| 2026-10-05 | Retention rule: **7 years from submission** | Evidence must be "kept on a stated retention rule" | Arth (proposed) | README §2 |
| 2026-10-05 | One spec for the Assurance Agent and its GUI: handoff 2 merged in full into `evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md` (same section numbers); the old file archived as `archive/SUPERSEDED-2026-10-05-…` | A single source of truth, so the dashboard and the agent can't drift apart | Arth | `08-…` header |
| `<date>` | `<threshold values per control, from exploratory runs R…>` | `<4 justifications>` | `<teammate>` | `register.yaml` |
| `<date>` | `<register approved by Sree: INC…>` | owner approval before assessed runs | Sree | `register/approval.md` |

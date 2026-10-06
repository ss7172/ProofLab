# Gap list: team iFabric (Artefact 6 of 6, "scored, and it scores well")

Each gap states **what** we could not close, **why**, **what it affects**, its **impact on the verdict**, and **what we would do next**. "Built properly: yes. Actually worked: no" is a valid, honest entry.

**Ownership:** Section A (ServiceNow and platform) is written by Arth. **Section B (AWS agents and controls) is the teammate's to fill.** The teammate owns the final merged file in the Evidence Pack; Arth reviews it the evening before submission. Update every "status" line to what actually happened before submitting.

---

## A. ServiceNow, AI Control Tower and the Assurance Agent

**A1. AICT discovery scope**
- **What:** AICT discovers AgentCore runtimes, Bedrock agents and SageMaker models only. It does not discover EKS pods, MCP servers, MoDaaS guardrails, or which ModelConfig served a call (all calls use one gateway IAM principal).
- **Why:** connector design (read-only role over those AWS APIs).
- **Affects:** L2 observability.
- **Impact:** the inventory is partial; per-call attribution comes from gateway and ledger records, not AICT.
- **Next:** extend the connector, or push call metadata to AICT via a custom integration.

**A2. AICT freshness**
- **What:** the inventory refreshes every 15 minutes, plus about 4 minutes of run time.
- **Why:** scheduled import.
- **Affects:** L2 live demo.
- **Impact:** new runtimes appear with a delay; we click **Execute Now** before the demo.
- **Next:** event-driven import.

**A3. AICT Monitor traces**
- **What:** as of 2026-10-05, AICT Monitor showed only ServiceNow-native sessions, none from our AWS runtimes.
- **Why:** traces from AgentCore did not reach AICT Monitor during our check.
- **Affects:** L2 (traces) and L3 (agent trace).
- **Impact:** we evidence agent activity with the inventory plus gateway and ledger records rather than AICT traces.
- **Next:** re-check after the named runs; if still absent, trace export to the connector's log group.
- **Status:** `<update before submission>`

**A4. Shared ServiceNow instance**
- **What:** reference agents have identical names across teams.
- **Why:** shared hackathon instance.
- **Affects:** L2 attribution.
- **Impact:** ours are identified by our connection's import timestamps and the `ifabric` prefix; we touch only `[iFabric]` incidents created by `ifabric.integration`.
- **Next:** a dedicated instance.

**A5. Script authentication**
- **What:** Basic auth was rejected (401) for both the participant and the integration user. We switched to OAuth client credentials and enabled the instance property `glide.oauth.inbound.client.credential.grant_type.enabled` (logged for transparency; facilitators informed).
- **Why:** instance MFA and auth policy.
- **Affects:** integration setup.
- **Impact:** none on verdicts.
- **Next:** per-team OAuth apps provisioned by the organizers.

**A6. Human response**
- **What:** a human reply is not required. Silence is recorded as `NO_RESPONSE_OBSERVED` only after the stated cutoff; unreadable history is `RESPONSE_UNKNOWN`, never treated as silence.
- **Why:** brief, out of scope.
- **Affects:** human loop.
- **Impact:** both outcomes are evidence.
- **Next:** none needed.

**A7. Delivery semantics**
- **What:** `DELIVERED` means read back with the right correlation id and assignee. It does not prove the human read it; only a note or status change proves engagement.
- **Why:** platform limit.
- **Affects:** "who was told".
- **Impact:** we claim delivery, not reading.
- **Next:** read receipts / acknowledgement task.

**A8. Note-level response detail**
- **What:** the `itil` integration user cannot read `sys_journal_field` rows (the ACL returns 0 rows, no error). Owner responses are detected from the incident's last update (`at_basis: last_update`, verified live). Notes are exported as display text.
- **Why:** least-privilege ACL.
- **Affects:** response timing detail.
- **Impact:** a reply followed by a later update by someone else can be hidden from a live check. Mitigation: `check` on a short loop; a logged `RESPONDED` is sticky.
- **Next:** a scoped read role for journal entries.

**A9. Assurance Agent location**
- **What:** the facilitators require Nemotron for the Assurance Agent. Nemotron is reachable only through `modaas-agw` (no public endpoints), and ServiceNow AI agents cannot use it on this instance. So the agent runs on AWS and writes its analysis into ServiceNow. A ServiceNow-native prototype (ServiceNow LLM) was built, tested once and **deactivated**; it is kept as superseded history only.
- **Why:** platform and model rules.
- **Affects:** L3.
- **Impact:** none on verdicts; the agent is outside ServiceNow but its output and evidence live there.
- **Next:** a ServiceNow-hosted agent once Nemotron is available as an instance provider.

**A10. AICT visibility of the Assurance Agent**
- **What:** only its AgentCore runtime (`ifabric_assurance_agent`) is an AICT asset. Direct governed gateway calls (backend `gateway`) are ledger-recorded but are not AICT assets.
- **Affects:** L3 trace.
- **Impact:** the AICT line exists only after the AgentCore deploy.
- **Next:** deploy before the named runs.
- **Status:** `<update>`

**A11. Note authorship**
- **What:** the analysis note is written by the integration user ("iFabric Integration"). The model and the call are identified by the note's `Model:` provenance line (alias, model id, gateway action id) and the run record.
- **Why:** secrets stay out of the agent runtime.
- **Affects:** attribution.
- **Impact:** none.
- **Next:** a dedicated identity for the writer.

**A12. Model variance**
- **What:** Nemotron may echo a fact wrongly. Such runs are **REFUSED** (nothing written) and shown as failures, never hidden.
- **Why:** LLM behaviour.
- **Affects:** L3 completeness.
- **Impact:** a case can show "no analysis" with the reason.
- **Next:** a larger approved alias, or prompt tuning, under the same checks.

**A13. Forged notes**
- **What:** anyone with ServiceNow write access can add a look-alike note, even with a fake header and timestamp. It is never trusted: a note counts only if its SHA-256 is in our delivery log. The log is therefore a trust anchor and is in the MANIFEST.
- **Affects:** L3 integrity.
- **Impact:** none.
- **Next:** server-side signing of notes (out of scope).

**A14. Display time zone**
- **What:** ServiceNow display times are in the reading user's time zone; our own timestamps are UTC (`…Z`).
- **Affects:** reconstruction.
- **Impact:** none if read with this note.
- **Next:** request UTC display values.

**A15. Shown vs proven**
- **What:**
  - the agent's refusal and guardrail paths are proven by tests (152 against fakes);
  - the ServiceNow write path was verified live on 2026-10-05 (INC0010232), with a TEST stand-in instead of the model:
    - note written, read back unchanged (SHA-256 matched), real journal parsed, re-run SKIPPED, five sections computed;
    - evidence in `servicenow/wiring-tests/assurance-agent-roundtrip/`;
  - `<list which were demonstrated live: e.g. a live REFUSED on an injected ticket, a live BLOCKED>`;
  - `<the first live Nemotron WRITTEN run: date/INC>`.
- **Status:** `<update before submission>`

**A16. Test incidents**
- **What:** INC0010231 and INC0010232 are **wiring tests** (`kind: wiring-test`, threshold version `TEST`), excluded from all verdicts and closed with resolution "adapter wiring test". Their records are in `servicenow/wiring-tests/` and never mixed into the production delivery log.
- **Status:** `<closed on …>`


**A17. Agent movement and policy depend on evaluator context**
- **What:** movement, the route rule (M1/P8), P1 (measured vs limit) and P2/P3 (register) are computed only from the `measured`, `limit`, `register` and `trace` the evaluator attaches to a finding.
- **Why:** the Assurance Agent doesn't observe network traffic; it checks the record it is given.
- **Affects:** L3 assurance analysis.
- **Impact:** where context is missing the checks show **unknown** (never pass); the route rule is only as complete as the trace. `<list named runs without a trace, or "none">`
- **Next:** emit the trace from the gateway itself (every `x-modaas-action-id` with source and target zone), so it can't be omitted.

**A18. Owner-response check before the cutoff**
- **What:** until the owner replies or the cutoff passes, P5 is "unknown: pending until the cutoff", so policy alignment reads 7/8 or lower.
- **Impact:** none on the verdict; it is the honest state of the human loop.
- **Status:** `<final P5 per named run after the final check>`

---

## B. AWS agents and controls (teammate fills)

Prompts from the playbook (keep the ones that apply, add your own, same five-part format):
- **B1.** Durable OTEL trace export: `<no durable exporter? impact on C7?>`
- **B2.** TMF639 projection: `<false? what it affects>`
- **B3.** C16 enforcement timing: `<post-run (post-hoc) instead of inline admission? label honestly>`
- **B4.** C9 granularity: `<hourly closed windows; a missing hour is a monitoring gap, not healthy>`
- **B5.** C7 expected-event source: `<how independent is it? coverage limits>`
- **B6.** `<any control "built properly: yes, actually worked: no">`
- **B7.** `<agents / S2 judgment gap / S3 escalation limits>`
- **B8.** `<adversarial cases that broke something, and what changed>`

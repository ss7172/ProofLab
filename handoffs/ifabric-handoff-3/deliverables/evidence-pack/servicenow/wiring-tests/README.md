# TEST ONLY: ServiceNow wiring tests (excluded from all verdicts)

These files prove the ServiceNow integration works on the real instance. They are **not control results**: findings use `threshold_version: TEST` and `kind: wiring-test`.

| File | What it is |
|---|---|
| `INC0010231-wiring-test.json` | Export of the first live wiring test (2026-10-05). Created, read back (DELIVERED), reused without duplication, owner response detected (RESPONDED). |
| `delivery-log-wiring-tests-ONLY.jsonl` | The Mac's delivery log from those tests (INC0010231, INC0010232). |
| `assurance-agent-roundtrip/` | Live round-trip of the Assurance Agent's **write path** on INC0010232 (2026-10-05), with a TEST stand-in instead of the model (`Model: TEST stand-in (no model)`), 9/9 checks. Contents: its own test log (`delivery-log-roundtrip.jsonl`: DELIVERED reused, ANALYSIS_WRITTEN with `note_digest`, ANALYSIS_SKIPPED); the run record (facts, attempt hashes, the exact note, no reasoning); and a screenshot of the note on the incident. Outcome validation correctly reports **failed** (V6): a stand-in is not a governed Nemotron call. |
| `sn-agent-prototype-superseded/` | The ServiceNow-native agent prototype's single live run on INC0010232 (ServiceNow LLM). **Superseded** by the Nemotron Assurance Agent (facilitator ruling); kept as history, not a claim. |

> ⚠️ **Never copy `delivery-log-wiring-tests-ONLY.jsonl` or `assurance-agent-roundtrip/delivery-log-roundtrip.jsonl` into `evidence/servicenow/delivery-log.jsonl`, and never append them.** The production log is written only by the evaluator loop. Mixing them would put test findings into the pack and into the Assurance Agent's trust list.

INC0010231 and INC0010232 are closed with resolution "adapter wiring test" after the first live Assurance Agent run has used INC0010232.

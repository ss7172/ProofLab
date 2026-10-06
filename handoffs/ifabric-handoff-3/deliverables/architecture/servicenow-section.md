# ServiceNow part of the one-page architecture (for the teammate to merge)

The teammate owns `architecture.md` (Artefact 5: components, what sits in the execution path, how an enforcement point invokes the controls; a whiteboard photo is fine). Paste or redraw this section. Everything here is **off the agents' request path**.

## Diagram (ServiceNow half; left side is the teammate's)
```
  AWS (teammate)                                     │  ServiceNow instance (shared)
                                                     │
 agents ─► EP1 modaas-agw ─► records ─► evaluators ──┼─► Finding (JSON contract: control, threshold
 (AgentCore)  (gateway: guardrail,     (pure, read    │      version, scope, verdict, evidence refs)
              Cedar, token count)      frozen         │        │ emit (after the run, off-path)
                                       register)      │        ▼
                                                     │   notify()  ── incident [iFabric]… assigned to the
                                                     │        │       named owner (Sree) = EP2: human queue
                                                     │        │       read back → DELIVERED
                                                     │        ▼
 Assurance Agent ◄── run_assurance_agent() ─────────┼── reads the incident (Table API, OAuth, itil)
 ifabric_assurance_agent (AgentCore)                 │        │
   └─► EP1 modaas-agw ─► Nemotron (governed,         │        ▼  validated note (facts checked; 3 judged fields;
        guardrail-checked, ledger-recorded)          │           provenance: alias + gateway action id)
                                                     │   PATCH work_notes only → read back → WRITTEN
                                                     │        │
   delivery-log.jsonl (append-only; trust anchor) ◄──┼── check() (pull): owner RESPONDED / NO_RESPONSE_OBSERVED
   evidence/servicenow/* + MANIFEST                  │   export() (pull): incident + notes as evidence
                                                     │
   AI Control Tower connector  ◄─────────────────────┼── pull: read-only role SgcAictReadOnlyAccessRole,
   (discovers AgentCore runtimes every 15 min)       │    inventory of our runtimes (L2)
                                                     │
   dashboard (case_view, read-only) ◄────────────────┘   one JSON per finding: finding → incident → owner
                                                          → Assurance Agent analysis → AICT link
                                                          + assurance analysis computed by code: agent movement,
                                                            decision trace, evidence, policy alignment (P1–P8),
                                                            outcome validation (V1–V6)
```

## The facts the one-pager must state (ServiceNow side)
1. **Off-path:** no ServiceNow call is in any agent's request path. ServiceNow work happens after a finding exists (emit) or on a schedule (pull).
2. **Second enforcement point (EP2): the ServiceNow human queue.** (In the Evidence Console's EP table this is **EP4**; EP2 there is the C16 agent-adapter admission.) The same Finding contract and evaluator output that EP1 produces is routed to a named human. Only the **adapter** (`prooflab/servicenow/*`) is ServiceNow-specific; evaluators and the Finding contract are unchanged ("same architecture, moved, nothing rewritten").
3. **Transports:**

   | Transport | Used by |
   |---|---|
   | `evaluate` (inline) | EP1 only (teammate) |
   | `emit` | `notify()` after a finding |
   | `callback` | none (the owner's response is not pushed to us) |
   | `pull` | `check()` / `export()`, the AICT import, the dashboard's `case_view` |

4. **Register out of the live path:** thresholds come from the frozen `register.yaml` (approved by Sree in ServiceNow). Neither ServiceNow nor the evaluators store thresholds.
5. **Model rule:** every model call, including the Assurance Agent's, goes through `modaas-agw` with a Nemotron alias. ServiceNow hosts no model of ours. The earlier ServiceNow-LLM prototype is deactivated.
6. **Trust and identity:**
   - ServiceNow access is OAuth client credentials as `ifabric.integration` (itil only); secrets live in the backend environment only.
   - The Assurance Agent runtime holds **no** ServiceNow credentials; the orchestrator writes.
   - A note is trusted only if its SHA-256 is in our delivery log.
7. **Same id everywhere:** run id → `finding_id` = incident correlation id → Assurance Agent note `Finding ID` → case JSON.
8. **Assurance analysis is deterministic:** agent movement (from the trace the evaluator attaches, including the route rule "no direct network → customer hop"), the decision trace, evidence classification, policy alignment and outcome validation are computed by our code. The model only judges three lines of the note. Missing data shows as **unknown**, never as a pass.

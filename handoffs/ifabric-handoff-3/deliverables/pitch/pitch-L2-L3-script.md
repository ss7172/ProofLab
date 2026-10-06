# Arth's part: L2 (AI Control Tower) and L3 (ServiceNow evidence chain), about 4 minutes

Speak in short sentences; let the screens prove it. Every claim below must be true at the time; adjust anything still pending.

## L2: AI Control Tower (about 1 minute)
**Screen:** AICT → Inventory, filtered to our connection "iFabric Hackathon 2026".
> "ServiceNow AI Control Tower discovers our agents directly from AWS through a read-only role. Here are our AgentCore runtimes, including the Assurance Agent, `ifabric_assurance_agent`. It refreshes every 15 minutes; I pressed Execute Now before we started."

**If asked about traces:** be honest (gap A3).
> "Monitor sessions from AWS runtimes did not appear on this shared instance during our check, so agent activity is evidenced by the gateway and ledger records. It's in our gap list."

## L3: the evidence chain for one breach (about 2.5 minutes)
**Screen:** dashboard, the C16 BREACH case card (named run from `run-ids.txt`).
1. > "Step one: control 16 breached for run `<id>`: `<measured>` tokens against a cap of `<N>`, under threshold version `<v>`, approved by Sree in ServiceNow before any assessed run."
2. > "Step two: within seconds an incident was raised and read back. It's assigned to the named owner, Sree, not to a team." *(Click the INC link.)*
3. > "Step three: Sree's response, or her silence after the stated cutoff, is recorded either way. A reply isn't required; the alert, the recipient and the outcome are."
4. > "Step four: our Assurance Agent. It runs on NVIDIA Nemotron, only through the governed MoDaaS gateway; here's that call's gateway action id. The top group is fact our code checked against the finding. The model only judged these three lines. If it got a fact wrong, or was tricked by text in the ticket, nothing would be written."
5. > "And it's the same id everywhere: run, finding, incident correlation id, the note, the case file."
6. **Scroll to "Assurance analysis".** *(Movement and decision trace are open by default.)*
   > "Below, the agent's assurance analysis, computed by our code, not the model. **Agent movement:** customer agent, gateway, IT agent, gateway, network agent, gateway, back to the customer. Three gateway crossings; no direct network-to-customer hop. **Decision trace:** every decision in order, from the first agent step and the gateway allows, through the control verdict, the incident and the owner, to the model's attempt and the agent's write. **Policy alignment** is 8 of 8 *(7 of 8 with 'pending' if Sree hasn't replied yet)*, and **outcome validation** checks the agent itself: its note is in our run log, the facts match, it cited only real evidence, no reasoning stored, and the call went through the governed gateway."
   - If the trace isn't attached for a run: *"Here the evaluator didn't attach the trace, so movement is **unknown**, shown grey, never green. We'd rather show unknown than pretend."*
   - Optional (10 s, if a route-broken run exists): *"This run's network agent answered the customer directly. The diagram flags the hop in red, and policy check P8 fails."*

## Second enforcement point (about 30 seconds)
> "The ServiceNow human queue is our second enforcement point. The same Finding contract the gateway evaluators produce is routed to a named human. Only the adapter is ServiceNow-specific; the evaluators didn't change."

## Adversarial beat (optional, 20 seconds)
**Screen:** a recorded case where an injected ticket made the Assurance Agent REFUSE.
> "We attacked our own agent with instructions hidden in a ticket. It refused to write, and that refusal is recorded with the gateway action id."

## Likely judge questions and short answers
| Question | Answer |
|---|---|
| "Who was told?" | Sree, by name; incident INC…, read back at `<time>`; response at `<time>` or silence recorded after `<cutoff>`. |
| "How do you know the agent's note wasn't edited or faked?" | We trust a note only if its SHA-256 is in our append-only delivery log; anything else is shown red. The log is in the MANIFEST. |
| "Which model wrote this?" | Nemotron `<alias>`, through `modaas-agw`; the provenance line carries the alias, the model id and the gateway action id, which joins to the ledger. |
| "Is ServiceNow in the request path?" | No. Everything ServiceNow is after the finding (emit) or scheduled (pull). |
| "What couldn't you close?" | Gap list section A: AICT traces, journal ACL, note authorship, display time zone, and movement depends on the trace the evaluator attaches (A17). |
| "Did the model decide the policy result?" | No. All five sections are computed by our code from the finding, the delivery log and the run record. The model only judges three lines of the note, and its facts are checked. |
| "What does 'unknown' mean?" | The data wasn't provided. It is never counted as a pass: `Policy 6/8` with two unknowns means 6 checks passed. |
| "Why isn't the agent inside ServiceNow?" | Nemotron is reachable only through the governed gateway with no public endpoints, and ServiceNow AI agents can't use it here; the facilitators required Nemotron. Its output and evidence live in ServiceNow. |

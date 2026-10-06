# Run of show: 15 minutes, timed

Base: Arth's `JUDGING-DAY-GUIDE.html`, fixed to our numbering. One sentence per screen. Judges ask,
we operate, the screen answers; if we must explain an answer aloud, the tool is unfinished.
The timed rehearsal result is recorded in `reviews/rehearsal-1.md`; nothing below claims a time
was achieved until that record exists.

Rule on claims: say only what the screen shows. Where a value reads `<...>`, fill it from the pack
before judging. If a question cannot be answered, say "that is in our gap list" and open it.

| Clock | Step | Driver | Screen | One sentence |
|---|---|---|---|---|
| 0:00-1:00 | 1 The promise | teammate | Overview, then Enforcement points | "We promised three rules (C16, C7, C9); here is whether each held, and here is what sits in the agents' path." |
| 1:00-3:00 | 2 Runs safely on AWS (L1) | teammate | terminal, then the L1 card | "The only way to the model is the governed gateway, and every refusal is recorded." |
| 3:00-4:30 | 3 Recorded and visible (L2) | teammate, then Arth | Evidence Ledger, then AI Control Tower | "Left is a log; right is evidence, tied to a rule, a version and a run." |
| 4:30-7:00 | 4 Humans are told (L3) | Arth | Human Loop | "Nemotron judged three fields; our code checked every fact before anything was written." |
| 7:00-10:30 | 5 Judges ask | teammate | Ask, then Six Questions, then a record | "The rule was dated before the run; click any number for its record." |
| 10:30-12:00 | 6 Decisions and the live stop | teammate | Agent Trail, then Live | "We trace decisions, not thoughts, and the verdict forms in the path, before the call." |
| 12:00-13:00 | 7 We attacked it | Arth + teammate | Adversarial, then Enforcement points | "Here is what broke and what we changed; the same c16 core runs at EP-1 and EP-2, only the connector differs." |
| 13:00-14:00 | 8 What is missing | both | Gaps | "Built properly: yes; worked every time: no, and each failure is on screen with its next step." |
| 14:00-15:00 | Questions | both | as asked | Use the answers below. |

Total: 15:00. Steps 1 to 8 end at 14:00; the last minute is questions.

## Fixes to the base guide

- **C-1, enforcement points:** use our EP-0 to EP-16 numbering (`evidence-templates/security-matrix.md`).
  The second enforcement point is the same c16 core function at EP-1 (inline) and EP-2 (after the
  run); say "same core, one sha256 at both", only if the pack shows equal hashes.
- **C-3, screens:** the console's exhibits are Ask/Answer, Evidence Ledger, Six Questions, Register,
  Human Loop, Enforcement points, Gaps and Runs. Where the guide names Overview, Agent Trail, Live
  or Adversarial and the console build lacks that screen, show the pack file or the CLI answer
  instead and say which it is. Do not present a missing screen as built.
- **C-4, handoffs:** "every model and tool call crossed the gateway; every handoff is a recorded EP-5 event." (three handoffs: Gateway A h1 customer → IT, B h2 IT → network, C h3 network → IT, the negotiation; four invocations, and each model call in the negotiating IT invocation passes C16 and the rails)
- **C-5, separation of duties:** "nobody checks their own work alone: Arth reviews before the owner approves." The governance-assurance role is vacant, stated in the gap list.
- **C-6, live inline decision:** one `enforce` run live with `python3 -m prooflab tail` at the slot,
  if AWS credentials are valid then. Otherwise play the recorded run and label it as recorded.

## The honest failure (T7.6)

Chosen at rehearsal from what happened. Default: ADV-R-06, built properly and fooled by a forged
envelope tally; the post-run floor caught it; the change and its re-test (ADV-R-06b) are in
`adversarial/`. Also named: guardrail blocks the platform records as ALLOW (gap 4). If the run
differs, this paragraph is wrong and the pack wins. Chosen failure at rehearsal: `<...>`.

## If the judges ask

- "Show me control 16 for run X": type it in Ask; say nothing until the answer is on screen.
- "Between two times?": `python3 -m prooflab query --control C9 --window <T1>..<T2>`; a missing window reads unknown, never green.
- "Who acted, was it approved, can we trust it?": Six Questions for their ticket; say why any PARTIAL is partial.
- "Can I check this without you?": `python3 tools/manifest.py verify .`, then a query command from the README.
- "Is the dashboard a control?": no; it shows and refuses nothing.
- "Is ServiceNow in the agents' path?": no; tickets are raised after the check.

## Fallbacks

- AWS slow: the recorded L1 video, and the L1 card shows the same proofs.
- Console will not start: the same answers from `python3 -m prooflab query ...` on the unzipped pack.
- Before going on: open the console on the downloaded pack copy, close tabs showing any token, write down the passing and failing run ids.

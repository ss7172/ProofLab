# 15 · Integration changelog (the integrator, Part 2)

Written 2026-10-06, from about 01:15 UTC, by the integrator/planner subagent, after the checkpoint commit `ec14665` and Fixer A's finish (`11a`). It integrates handoff-3, the guardrails design, the captain's approved decisions and the phased build into the architecture files. The plan itself is `IMPLEMENTATION-PLAN.md` (repo root; Part 1). No git, no cluster, AWS or ServiceNow action; no secret read.

**Inputs:** memory `planning-handoff.md` (the blocks "CAPTAIN DECISIONS: APPROVED (00:26Z)" and "Guardrail decisions APPROVED (00:30Z)"); the coordinator's relays (the phases, ~01:05Z; the Phase 1 notify, ~01:10Z; `BUILD-SESSION-PROMPT.md`); `work/11a`'s cross-dependencies; `work/12`, `13`, `14`; `guardrails/AGENT-GUARDRAILS.md` and `PLAN.md`.

**Backups before editing** (session scratchpad): `ARCHITECTURE.md.pre-integration`, `decisions.md.pre-integration`, `PLAN.md.pre`, `AGENT-GUARDRAILS.md.pre`, `11a-one-page-svg-gen.py.bak`.

---

## `architecture/ARCHITECTURE.md`

| Where | Change | Source |
|---|---|---|
| Header | "Still pending" replaced by: what the captain decided (D2, D3, D5, D9, D10, D11, D13, D14, D15, D16 (a), C-7, DG-1–DG-7) and settled by direction (D17, the Assurance agent on AgentCore, Arth's code as-is, the Phase 1 notify, the phases); the integration note; `IMPLEMENTATION-PLAN.md` as the schedule; still open: the D8 mirror and the plan's DC-1…DC-11 | memory blocks; coordinator |
| §1.2 | `c16.decide_inline` → `c16_core.decide_inline` | `11a` item 7 |
| §2.2 | The rails may refuse or modify (DG-1) but are not control questions; D16 (a) and D13 marked decided; the diagram gains Gateway A / B (the script box), the rails line (the runtime box), EP-16 (the cockpit side door), Arth's console with the run catalogue, and the Assurance agent | DG-1; the brief |
| §2.3 | New row: the rails (EP-14, EP-3, EP-4, EP-15) may refuse or modify, not a control question; EP-0's row decided | guardrails §6.1 |
| §3.0 | The layout gains `rails.py` + `egress.py`, `query/` grammar + answer, `pack/`, `console/`, `humanloop/`, `watch/`, `agents/ifabric-assurance/`, `tools/`; `servicenow/` = the handoff-3 version (152 tests) | `work/12` §5.3 (a); guardrails §13 |
| §3.1 | EP-0 decided (blocks assessed runs); **EP-5: Gateway A and Gateway B = the script's two handoffs, record-only** (DG-2's input masking); EP-6: the DG-4 rule on `customer-records`; EP-13: the laptop, the 152-test package, the Assurance agent in its loop, the Phase 1 notify; **new EP-14** (ingress rails), **EP-15** (egress audit), **EP-16** (the cockpit "ask" API, an observed side door) | guardrails §6.1; the brief; platform facts (notes #25) |
| §3.7 | **The dashboard = Arth's Evidence Console** (D17): views, no verdict logic, loopback, the fake/real data switch; the static `dashboard.html` dropped; `query --runs` gains **the run catalogue** and **the declared window** (`evidence/window.json`, write-once) | the captain's directions; `work/13` D8 |
| §3.8 | The handoff-3 package; **T2 = Arth's approval Finding** after T1 (C-7); the finding builder (G-04) and the human-loop runner (G-05); the cutoff rule (R-19); bugs (a)/(b) accepted with process guards; AICT's AWS half (G-12) and `ifabric_assurance_agent` | C-7; `work/14` R-19; `work/13` B1, B2 |
| §3.10 | The scope rule names `ifabric-assurance-agent`; the components table: the Cedar test rule (replacing the "Cedar test tool"), the Assurance agent, `ifabric-rails-policy`, `ifabric-adversarial-corpus`; `inv-1` at ~04:25; the AICT mirror decided | `11b` follow-up 1; guardrails §6.5 |
| **§3.11 (new)** | **The iFabric Assurance agent** as a component: the wrapper on the laptop, the analyzer as the 4th AgentCore runtime (our one-file handler around Arth's unchanged `nemotron.py`: the gateway-URL shim, the token limit via config), what one call does, transports, its own CID prefix, secrets, inventory, AICT, the G-15 fallback | `work/12` §2, §5.4; `work/13` R3, R4, R7; housekeeping |
| **§3.12 (new)** | **The Evidence Console and the one-way projector** (G-07), the answer composer (G-08), the live feed (G-10) | `work/12` §5.3 (a) |
| §6 | Layer 2: **rails may block (DG-1)** and DG-2–DG-7 listed; layer 3: D15/DG-4 decided; the guardrails design linked as built; §6.1 decided, with new rows **EP-14, EP-15, EP-16, the Assurance runtime, the human-loop runner, the console** (replacing "Dashboard"), and EP-3/EP-4 now refuse through rails; §6.2 decided, **the rule kept through judging** (restored after); §6.4: ADV-H-02 live through the DG-7 fault, new ADV-H-05/-06 and ADV-R-11/-12 (the guardrails design's), **ADV-R-06b (the R-J-19 row)**, and the renumbered Assurance cases **ADV-H-07** and **ADV-R-13** plus **ADV-R-14** (the EP-16 probe) | DG-1–DG-7; `11a` item 4; guardrails §9 |
| §7.1 | Tools: D15/DG-4 decided; **the rails ride in each bundle**; the 4th agent → §7.3 | guardrails §13 |
| §7.2 | The preflight is the budget guard (≤ 1.0M per 60 min, ≤ 2 `observe` S2 runs per rolling hour, ≤ 30 req/min, 300K per run); EP-0 decided; the two handoffs named Gateway A and B | `BUILD-SESSION-PROMPT.md`; the brief |
| **§7.3 (new)** | The Assurance runtime's build and deployment (G-01, G-02, G-03) | `work/12` §5.4; `work/13` R5 |
| §8 | D11 decided; new rows: the console, the human-loop runner, the Assurance runtime; the ServiceNow credentials done; the AWS refresh inside Phase 1 | coordinator (selftest PASSED ~00:45Z) |
| §9.1 | The tree: `pack-index.json` + the projection, `window.json`, `register/approval/`, the run catalogue, Arth's `servicenow/` union, `answers/` (renamed from `cases/`, R-15), MANIFEST via Arth's tool; **`run-ids.txt` = one CID per line** | `11a` item 3; `work/14` R-9, R-15 |
| §10.3 | The declared window and the run catalogue define "any incident" | the captain's direction |
| §11 | ServiceNow (EP-13) is the human queue, not the second EP | `work/14` C-1 |
| §12 | A banner: superseded for the schedule, the lane and the budget by `IMPLEMENTATION-PLAN.md` (phases; the build prompt's method); the W-AA row filled; W9's adapter-fix text replaced (Arth's code unchanged); the Cedar restore moved after judging (DG-4); the S2-class rule tightened | the captain; `work/12` §5.3 (d) |
| §13 | Statuses: D2, D3, D5, D9, D10, D11, D13, D14, D15, D16 **decided by the captain**; D1 superseded by D17; **D16's fallback aligned to a single laptop store**; new rows D17–D23, DG-1–DG-7, P1-notify, Phases | `11a` item 1; memory; coordinator |
| §14 | `work/12`'s OC-24…OC-30 added as **OC-27…OC-33** (renumbered: ARCH already used OC-24…OC-26); new OC-34…OC-37; OC-26 now the build prompt's merge gate; the ServiceNow `selftest` closed | `work/12` §5.7 |
| §15.2 | New rows: bugs (a) and (b), the CID-less Assurance calls, the gateway-URL shim's plain-HTTP key (gap 9), the 200-step trace cap, the live file as a convenience index, the cockpit side door, the rails gaps (pointer), Arth's Section A (pointer) | `work/13`, `work/14`; guardrails §11 |
| Fixer A's own sections | Labels "pending captain" changed to decided for D2 (EP-1 status, §5.1), D3 (§5.3), D5 (§3.3 hand-out and date proof), D9 (§5.5), D13 (EP-0, §5.0), D16 (§3.5, §10); 7 labels remain where nothing was decided (the label legend, the D8 mirror, the incident volume bound, `ep.responsible`, the exception tolerance, M3, INV's passes) | memory blocks |

**Fixer A's cross-dependencies (`11a` §"Cross-dependencies"), checked in the file:** 1 D16 (b) → aligned (§13, `decisions.md`); 2 the `ifabric-run-` CID in §7.2 → already present (Fixer B); 3 `run-ids.txt` → fixed in §9.1; 4 the R-J-19 row → added to §6.4; 5 the three redaction paths in §9.3 → already present; 6 the flush is declared in §2.3, §3.2 and §3.4 → consistent; 7 `c16_core` in §1.2 → fixed; 8 the pin names in §7.1/§7.2 → already present; 9 the session id in §7.2 → already present; 10 §14's closed rows → already present.

## `architecture/decisions.md`
- Header note (the update and its source); "decided by the captain" defined for both days.
- Statuses as in §13; D1 superseded; **D16's chosen option rewritten: (a) decided, the fallback a single laptop store**.
- New rows: D17–D23, DG-1–DG-7, P1-notify (decided by the captain, ~01:10Z), Phases (decided by the captain, ~01:05Z).

## `architecture/one-page.svg` and `one-page.md`
- **The generator `architecture/work/11a-one-page-svg-gen.py` was edited and re-run** (the SVG is its output, byte for byte; no hand edits): the headline ("Only ONE CONTROL question waits … Rails may refuse (DG-1)"); the script card (EP-5 handoffs = Gateway A / B); EP-3 and EP-4 (rails); the runtime footer (EP-14, EP-15); the platform card (the DG-4 rule; the cockpit ask = EP-16); the registry (Arth's approval Finding, T2, C-7); THE ONE STORE (D16 (a) decided); the ServiceNow card (the Assurance agent); the control-test card (Arth's console, the run catalogue, the declared window); the risk register (R-GR-01…05); the inventory (the Assurance agent). Line counts unchanged, so the layout holds; the generator's overflow check passed after two lines were shortened. A PNG render was checked visually.
- `one-page.md` rewritten to match, line for line.

## `architecture/guardrails/`
- `PLAN.md`: an update note; the anchor re-set from the 02:00 freeze to Phase 1 (Stage A ~03:45, frozen ~04:25, `v1` ~05:15); G0.1 DONE (DG-1–DG-7 decided); SP-1 in the idle lane at ~03:00 or Phase 2; ADV-H-01 leg A in Phase 1, leg B in Phase 2; adversarial windows in Phase 3; RTM-2 paced at ≤ 0.5 req/s (the 30 req/min limit); ADV-H-02's fault declared in the pins (no run-time env patch, DC-8); the OK table's DG row answered.
- `AGENT-GUARDRAILS.md` §12: one status line (DG-1–DG-7 decided as recommended).

## Id collisions resolved (for every later reader)
- **G:** Gate G1–G7 (the plan's acceptance gates) vs G-01…G-22 (glue; `work/12`'s numbering is the master, `work/13`'s G1–G13 crosswalked in the plan's §3.10) vs the guardrails' G0.x / S-G / B-G / L-G ids vs the rails gaps G-1…G-14 (written "rails gap G-n").
- **OC:** `work/12`'s OC-24…OC-30 → OC-27…OC-33.
- **ADV:** the guardrails design owns ADV-H-05, -06 and ADV-R-11, -12; `work/12`'s Assurance cases became ADV-H-07 and ADV-R-13; the EP-16 probe is ADV-R-14.

## Not changed, on purpose
- Arth's package (`handoffs/ifabric-handoff-3/`): not touched (its two doc-line rewordings are the plan's task T0.6, with a `REWORDED.md` sidecar).
- `gap-list.md`, `PLANNING-HANDOFF.md`, memory: not edited here (the gap-list merge is the plan's T8.3; memory belongs to the lead).
- ARCH §5's thresholds, §4's schema and §3.2's contract text: unchanged beyond the labels; the rails' contract change is G0.2 in PR-01 of the plan.

## Open items for the lead
1. **DC-1:** the approved D15 says per-agent rules go in our agents through the "Strands Cedar handler"; the approved guardrails design ships RT-04 as a Cedar-shaped Python table and keeps Strands' vended Cedar out of v1. Default: RT-04 in v1. Worth one line to the captain.
2. **Phase 1's clock:** Stage A by ~03:45 needs the critical chain in ≤ 2.75 h (Fixer B estimated 3.75 h); the honest projection for submit #1 is 05:45–06:30 against the captain's ~05:30 target.
3. **Prototype rescue (plan T0.7):** `work/13`'s proven Assurance bundle prototypes live only in this session's scratchpad (`h3/bundle/`, `h3/bundletest/`); copy them into the repo before the scratchpad goes.

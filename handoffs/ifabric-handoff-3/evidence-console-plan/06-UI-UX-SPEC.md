# 06 · UI/UX spec: the Evidence Console

`demo/index.html` is the **reference implementation** of everything below (tokens, components, views, interactions). The coding agent copies it into `prooflab/console/static/` (split into `app.css` and `app.js`, no inline code) instead of reinterpreting it.

Design skills to load while building: **interface-design** (direction, hierarchy, the checks in §8) and **ui-ux-pro-max** (targeted UX and chart searches).

---

## 1. Intent (decided before any pixel)

| | |
|---|---|
| **Who** | A senior trustworthy-AI / GRC judge, sceptical by profession, on our screen for 15 minutes after a long day of demos. Then the operator driving under a clock. Later, a stranger opening the pack with no one to explain it |
| **What they must do** | **Verify.** "Show me control 16 for run FM-B." The rule, its date, the number, the verdict, the records behind it, who was told, and why they can trust it hasn't changed, **without anyone narrating** |
| **How it should feel** | A **forensic instrument**: exact like a ledger, calm like an evidence room, dense like a flight recorder. Not a marketing dashboard. Nothing decorative; every mark is a fact with a source |

**Domain exploration:**
- **Domain:** evidence exhibits and chain of custody · auditor working papers with **tickmarks** (✓ agreed, recomputed, traced, vouched) · a statute book with effective dates (the register) · ledger reconciliation · flight-recorder timelines · telecom NOC lanes.
- **Colour world:** vault black-blue (secure room, NOC wall) · bone working paper · graphite pencil · auditor's red and green tick pencils · amber "pending" stamp · evidence-tape red · oscilloscope cyan trace.
- **Signature elements** (only this product has them):
  1. **Auditor tickmarks** R · A · T · V on every figure (Recomputed, Agreed to source, Traced across surfaces, Vouched by a dated approval), with a legend in the footer, exactly as audit working papers do.
  2. **The Evidence Lane**, which redraws the masterclass's own span diagram (MC slides 6–8: three zones, EP diamonds, a running Σ against the spend cap) with real records.
  3. **The date-before-test ribbon**: freeze → owner approval → first assessed run, so "its date is what makes it a test" is visible at a glance.
- **Rejected defaults → our choice:**
  - KPI card grid → a **claim tree** (C-FM-01 → three control branches with verdicts and completeness).
  - An icon sidebar → a **lettered exhibit index** (A, B, C…, like a court binder).
  - Traffic lights everywhere → **verdict words** plus hatched UNKNOWN; red reserved for breaches.
  - Gradient area charts → **limit-line bar charts** in the masterclass's own grammar (C7 gaps, C9 windows).
  - A chatbot → a **deterministic query grammar** (no LLM in the answer path).

**Direction:** dark "instrument" theme by default, plus a "paper" light theme for projectors (test both in the room). IBM Plex Sans + IBM Plex Mono (open licence, engineering and archival character, true tabular figures). Borders-only depth. One cyan "trace" accent. Red, green and amber are reserved strictly for verdicts.

---

## 2. Tokens (names come from the world, not a template)

```css
:root {                                   /* instrument (dark) */
  --vault:#0a0d12;  --docket:#0f131a;  --folio:#131922;  --stack:#19202b;   /* surfaces, +~3% lightness per step */
  --rule:rgba(255,255,255,.07); --rule-strong:rgba(255,255,255,.13); --rule-focus:#45c4d8;
  --ink:#e7ebf1; --ink-2:#a9b2c0; --ink-3:#717b8b; --ink-4:#4b5462;         /* 4 text tiers */
  --trace:#45c4d8; --trace-dim:rgba(69,196,216,.14);                        /* the one accent: interactive, joins */
  --held:#3fb68b;  --held-dim:rgba(63,182,139,.14);                          /* SATISFIED: a control held */
  --breach:#f0524f; --breach-dim:rgba(240,82,79,.14);                        /* NOT SATISFIED / BREACHED */
  --unknown:#e3a63b; --unknown-dim:rgba(227,166,59,.14);                     /* INDETERMINATE / UNKNOWN / pending */
  --hatch:repeating-linear-gradient(135deg,var(--unknown-dim) 0 4px,transparent 4px 8px);
  --font-sans:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px;  /* 4px base, dense */
  --r1:4px; --r2:6px; --r3:10px;                                              /* chips · cards · drawers */
  --ease:cubic-bezier(.23,1,.32,1); --t-fast:140ms; --t-med:220ms;
}
:root[data-theme="paper"] {                /* projector-friendly light */
  --vault:#f4f5f7; --docket:#ffffff; --folio:#ffffff; --stack:#ffffff;
  --rule:rgba(16,24,40,.10); --rule-strong:rgba(16,24,40,.18);
  --ink:#0e1218; --ink-2:#3c4554; --ink-3:#5d6776; --ink-4:#8a93a1;
  --trace:#0f7d93; --held:#16794f; --breach:#c4302b; --unknown:#9a6406;
}
```

| Scale | Values |
|---|---|
| Type (ratio ~1.2 from 13 px, dense) | micro 11 / label 12 / body 13 / h4 15 / h3 18 / h2 22 / verdict 30 / display 38. Hierarchy comes from **weight + ink tier** more than size. Labels are 11 px uppercase, tracked +.06em, `--ink-3` |
| Numbers | Always `--font-mono` with `font-variant-numeric: tabular-nums`; thousands separators; units in `--ink-3` |
| Depth | Borders only (`--rule`, `--rule-strong`), whisper surface steps; no drop shadows in the dark theme |
| Motion | Only `opacity`/`transform`, 140–220 ms, `--ease`; Σ meter and lane draw-in on first view only; **no** animation on repeated actions (Ask → answer is instant); `prefers-reduced-motion` removes all movement |
| Focus | 2 px `--rule-focus` outline, offset 2 px, on every interactive element |

**Verdict vocabulary** (word + glyph + colour; colour is never alone):

| Value | Label | Glyph | Treatment |
|---|---|---|---|
| SATISFIED | SATISFIED | ● | `--held` text, `--held-dim` chip |
| BREACHED | NOT SATISFIED | ▲ | `--breach` text, `--breach-dim` chip |
| INDETERMINATE / UNKNOWN / UNMEASURABLE | INDETERMINATE | ◐ | `--unknown` text, **hatched** fill |
| NOT_ASSESSED | NOT ASSESSED | ○ | `--ink-3` outline |

Provenance chips: `ASSESSED` (no chip; the default), `EXPLORATORY` (grey, struck from verdicts), `WIRING TEST` (grey), `SYNTHETIC` (watermark ribbon on every view).

---

## 3. Layout and navigation

```
┌ Top bar 52px ────────────────────────────────────────────────────────────────────────────────┐
│ ⟦PL⟧ ProofLab Evidence Console · C-FM-01   [ ⌘K  Ask the evidence… "Show me control 16 for run FM-B" ]   PACK·read-only  MANIFEST ✓ 214/214  ▶ Present  ◐ │
├ (SYNTHETIC ribbon in the demo only) ─────────────────────────────────────────────────────────┤
│ Exhibit rail 232px │ Main (max 1280px)                                          │ Inspector 440px │
│ A Overview         │  one focal element per view                                │ (drawer, opens  │
│ B Ask · Answer     │                                                            │  on any record) │
│ C Agent Trail      │                                                            │                 │
│ D Evidence Ledger  │                                                            │                 │
│ E Six Questions    │                                                            │                 │
│ F Register         │                                                            │                 │
│ G Human Loop       │                                                            │                 │
│ H Adversarial      │                                                            │                 │
│ I Architecture     │                                                            │                 │
│ J Gaps             │
│ K Live Monitor     │                                                            │                 │
│ ── Judging L1 L2 L3│                                                            │                 │
│ "Sees everything.  │                                                            │                 │
│  Refuses nothing." │                                                            │                 │
├ Footer 28px: pack sealed … · MANIFEST sha 9f2c…  · S3 readback ✓ · UTC · tickmarks: Ⓡ recomputed Ⓐ agreed Ⓣ traced Ⓥ vouched ┤
```

**Keyboard:**
- `⌘K` / `/`: Ask.
- `g` then a rail letter: go to that section.
- `[` `]`: previous / next run.
- `i`: inspector.
- `p`: present mode; `←` `→`: present steps.
- `t`: theme.
- `?`: shortcuts.
- `Esc`: close.

**URL state:** `#/answer/C16/run/FM-B`, `#/trail/FM-C`, `#/auditor/INC0090216`, `#/loop/INC0090216` (or a `finding_id`: one ServiceNow case) (deep links for rehearsal). Every `servicenow:INC…` ref anywhere in the console opens its case.

---

## 4. Components (all data-driven from the contracts in `03-…`)

| Component | Data | Behaviour |
|---|---|---|
| **Verdict banner** | `answer.verdict`, `comparison` | Display-size word (NOT SATISFIED) + one sentence ("63,420 tokens vs cap ≤ 60,000 · over by 3,420") + tickmarks. If `rule.date_before_scope` is false: red "RULE DATED AFTER TEST" overrides everything. If `source.manifest_status` ≠ VERIFIED: "UNVERIFIED" stamp |
| **Bullet meter** (C16) | measured, limit, delta | A horizontal bar with the cap line; the overshoot segment hatched red with a "+3,420" label; the margin labelled when within. Value text beside it (never colour alone) |
| **Limit-bar chart** (C7 gaps, C9 windows) | `measurement.series[]` | One bar per gap/window, the limit line, VIOLATES bars in `--breach` with the value label, UNKNOWN/UNMEASURABLE bars as hatched stubs with "?". Exceptions listed under the chart (the masterclass grammar) |
| **Audit Question card** | `answer.audit_question` | Ten rows in three groups, **The action · The decision · The proof** (MC-4/MC-9). Each row: label, text, refs as chips; FLAG rows get an amber edge |
| **Population strip** | `answer.population` | expected (with its source) · observed · matched · missing · duplicates removed · blocked · unmeasurable, as mono figures |
| **Tester / Evaluator split** | `answer.enforcement` | Two side-by-side blocks: "Control test (tester)" = dated pass/fail; "Inline decisions (evaluator)" = ALLOW/ALERT/DENY per call with reserved + committed. The second shows "POST-RUN only" if empty |
| **Evidence Lane** (SVG) | `run.lane` | Rows = zones (orchestrator, customer, IT, network, controls, ServiceNow); x = time. Model calls are bars (width = duration), tool calls ticks, handoffs and admissions ◆ diamonds labelled EP2/EP3, guardrail blocks ⊘, stop records ■. A Σ line climbs against the cap line and turns red where it crosses. Hover shows the event; click opens the inspector |
| **Journey map** | `run.journey.hops` | Five nodes: Customer → **Gateway A** → IT → **Gateway B** → Network, with the return path drawn dashed. Each hop labelled with its time, payload and EP3 admission; a ServiceNow branch for S3 |
| **Decision card** (5 facets) | `run.decisions[i]` + `run.outcome` | Header: agent, zone, disposition chip. **Intent** → **Evidence consulted** (tool, status, declared?, refs) → **Rationale** (the agent's own text, quoted, with cited refs) → named evidence / reversible step / proposed action → **Policy checks** (AP-v1 rows: ✓ ALIGNED, ▲ VIOLATION, – N/A, each with its basis) → model-call ids. A "derived from ledger" chip if the agents weren't rebuilt |
| **Outcome panel** | `run.outcome` | Expected (from the independent spec) vs actual, the checks list, ground truth, **claimed vs executed**, `score-run.py` labelled DIAGNOSTIC |
| **Record row** | `ifabric.evidence/v1` | run.id · call.id · control.id · threshold.version · threshold.value · measured.value · verdict · actor.id · emitted.at · tickmarks · seal "out of scope" (the slide's exact field order) |
| **Inspector drawer** | ref → record + raw line + capture sidecar | Raw line (mono, wrapped, redaction marks highlighted) · sha256 (with a "recompute in browser" button using WebCrypto) · capture command · captured_at · MANIFEST status · joins (action_id → PDP, durable gateway, X-Ray) · "three records" panel (span / gateway / metric; the gateway marked as the figure of record) |
| **Human-loop chain** | `ifabric.servicenow.case/v1` | Embed the drop-in panel (`08-…` §7.2): the 5-step chain + analysis groups + header pills + the five assurance sections (`08-…` §8, §8.7) |
| **Ribbon** | register + runs | A horizontal timeline: exploratory runs (grey) · freeze · approval · first assessed run · named runs, with "✓ every assessed run started after approval" |
| **Thread highlight** | any id chip | Hover or click an id (CID, finding_id, action id, INC) → every occurrence on screen outlines in `--trace` ("follow the thread") |
| **EP table** | `pack-index.enforcement_points` | id · kind · transport · can refuse · **status as given** · changed adapter · unchanged core |

**No `innerHTML`** for data; build nodes with a tiny `h(tag, attrs, ...children)` helper using `textContent`, and SVG via `createElementNS`.

---

## 5. Screens (focal point first)

| # | Screen | Focal point | Contents (P0 bold) |
|---|---|---|---|
| 5.1 | **A · Overview** (P1) | The claim C-FM-01 and its overall verdict | Claim tree (3 branches: PASS/BREACH runs, completeness (a)–(g), built properly / actually worked) · Judging L1→L2→L3 strip with evidence items · named runs with `written_at` · six artefacts present · three environments · "judges will ask" chips · the three AWS pillars |
| 5.2 | **B · Ask / Answer** (**P0**) | The verdict banner | **Query echo + parse ("→ controltest 16 --run FM-B") + elapsed · verdict banner · bullet/limit chart · audit question card · population · tester/evaluator split · records (tickmarks) · human-loop line(s) · AICT line · gaps · answer_id** |
| 5.3 | **D · Evidence Ledger** (**P0**) | The record table | **Filters (control, run, actor, verdict, provenance, surface) · table of bound records · Log → Evidence split (raw line ↔ bound record) · inspector** |
| 5.4 | **C · Agent Trail** (P1) | The journey map of the selected run | Run picker (FM-A…FM-D, S3) · journey map · decision cards (5 facets) · outcome panel · Evidence Lane below. This is the user's "agent movement, decision trace, evidence, policy alignment, outcome validation". The Assurance Agent's own run is shown in **G · Human Loop**, not here (its record is `assurance-agent.run/v1`, not `run/v1`) |
| 5.5 | **E · Six Questions** (**P0**) | The incident picked from the window | **Incident picker (every finding/escalation in the event window) · six cards WHO/WHAT/AUTHORIZED/APPROVED/INTEGRITY/RECONSTRUCT with status, facts, refs, gap links** |
| 5.6 | **F · Register** (**P0**) | The date-before-test ribbon | **Ribbon · control cards (anatomy MC-16: id, child id, statement, owner, mode, metric, both limits with operators, tolerance, basis, EP, applicability, frequency, test procedure, evidence artefacts) · 4 justifications · risk rating inherent/residual · people (owner ≠ builder ≠ assurance) · approval proof (INC, time, sha)** |
| 5.7 | **G · Human Loop** (P1) | The case card of the selected finding | **Embed the real drop-in panel** (`08-…` §7.2) over `/api/v1/cases`: the 5-step chain, the Assurance Agent analysis (checked facts vs Nemotron's judgement, provenance), the header pills (Policy x/y · Outcome · agents/gateway crossings) and the five assurance sections (§8.7). RESPONDED and NO_RESPONSE both visible. Source: `/api/v1/cases` (pack-index `cases[]`). Above each card, a link strip: incident and finding id as thread chips (hover lights them everywhere), **Answer →**, **Six questions →**. The Answer view's "Who was told" incident chip links back here, and its Nemotron pill takes the state's tone (REFUSED red) |
| 5.8 | **H · Adversarial** (P1) | The matrix | Rows grouped Alert 0 Vanilla / Alert 1 Hostile / Alert 2 Rogue · attack · target · expected · observed · outcome pill · what broke · what changed · evidence |
| 5.9 | **I · Architecture** (P1) | The one-page diagram | In-path vs off-path · EP table (honest status) · four transports · five modes · five habits · "changed adapter / unchanged core" |
| 5.10 | **J · Gaps** (**P0**) | "Built properly: yes. Actually worked: no." | Gap cards (what · why · affects · impact · next · status), sections A/B, filters by control and auditor question |
| 5.11 | Integrity (**P0**, in the top-bar badge + drawer) | MANIFEST status | Files verified, changed/missing/unlisted, corroboration counts, S3 key/ETag/time, readback |
| 5.12 | Control Room (P2, operator mode only) | The request queue | Allow-listed actions with reason + confirmation, request → actuator → result timeline from `actions.jsonl`, labelled "the console asks; it does not decide". **Not rendered in PACK mode** |

### 5A. K · Live Monitor (P1; LIVE mode): real-time monitoring
**Focal point:** the active run's **Σ budget meter** climbing against the cap, with inline decisions appearing as they are formed.
```
┌ LIVE · run FM-D (S2 adversarial) · 00:01:42 elapsed ─────────── streams: gateway 2s · ledger 3s · cw 4m ✓ ┐
│ Σ ███████████████████████████████████░░░░  55,764 / 60,000 tokens       next reserve 5,212 → DENY ◆  │
│ Journey  Customer ✓ ─A─► IT ● (call 13) ─B─► Network ○                                              │
│ Lane     [live Evidence Lane: bars appear per call; ◆ ALLOW/ALERT/DENY diamonds form in the path]   │
│ Verdicts C16 PROVISIONAL (run open) · C7 events 9/16 so far · C9 hour 03:00Z +8.0% PROVISIONAL       │
│ Human loop  ▲ C16 breach FM-B → INC0090216 DELIVERED → Sree → Nemotron note WRITTEN   (ticker)       │
│ Ceiling  requests 41/100 per min · tokens 312,400 / 2,500,000 per h                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```
**Rules:**
- **Provisional is labelled.** Open runs and open hours show PROVISIONAL. Final verdicts appear only from `verdict` events.
- **Freshness is shown per stream** (lag in seconds). A stream lagging > 30 s during an active run turns the header red **STALE**: the monitor monitors itself.
- **Inline decisions are the real-time verdicts** (EP2/EP3): each one is a diamond on the lane plus a row in the decision feed, with reserved and committed values.
- **Data path:**
  - SSE `GET /api/v1/live/stream` tails `live/events.jsonl`;
  - fallback: poll `GET /api/v1/live/snapshot` every 2 s;
  - no AWS or ServiceNow call from the console.
- **PACK mode:** the Live Monitor becomes **Replay**. It plays the recorded `live/events.jsonl` of a named run at 1×–8× speed, titled "REPLAY of a recorded run: verdicts as formed at the time". Never pretend a replay is live.
- **Demo moment:** launch (or replay) FM-D and watch EP2 refuse call c-0014 before the cap: "a verdict formed in the path".

**States (every view):****States (every view):**
- loading (skeleton rows, no spinner);
- empty ("No assessed runs yet: the register is frozen at …");
- error (envelope message + ref);
- UNKNOWN hatched;
- unresolved refs red;
- a PACK MODIFIED banner overrides all.

---

## 6. The query grammar (deterministic; the Ask bar and the CLI share it)

| Pattern (case-insensitive) | Normalized | Example (the judges' words) |
|---|---|---|
| `[show me \| was] control <7\|9\|16> [satisfied] for run <RUN>` | `controltest N --run RUN` | "Show me control 16 for run FM-B" · "Was control 9 satisfied for run FM-B?" |
| `control <N> between <T1> and <T2>` / `from … to …` | `controltest N --from T1 --to T2` | "Was control 9 satisfied between 23:00Z and 09:00Z?" |
| `control <N> for window <YYYY-MM-DDTHH>` | `controltest N --window …` | "control 9 for window 2026-10-06T00" |
| `controltest <N> --run <RUN>` (CLI form) | itself | slide MC-33 |
| `six questions [for] <INC…\|RUN>` / `auditor <INC…>` | `auditor INC…` | "six questions for INC0090216" |
| `reconstruct run <RUN>` / `trail <RUN>` | `trail RUN` | "reconstruct run FM-B" |
| `who acted in <RUN>` / `who was told for <RUN>` | auditor question | — |

**Rules:**
- `RUN` accepts an alias (FM-B) or a CID.
- Times accept ISO UTC or `HH:MMZ` (resolved within the event window).
- `C16`, `16` and `spend cap` are synonyms (also `event recording` = 7, `drift` = 9).
- Unknown input → "I can't parse that" plus the example list; never a guess.
- An ambiguous run → candidates.
- **No LLM is used to interpret questions** ("the evaluator never remembers", and answers must be reproducible).

---

## 7. Present mode (the 15-minute run of show)

`p` opens a slim step bar with a **15:00 countdown** and per-step budgets. `←`/`→` move between steps; each step deep-links to a view with the right scope preselected:

| # | Step (budget) | Opens |
|---|---|---|
| 1 | The promise (1:00) | Overview → claim and the three control cards, then Architecture |
| 2 | Runs safely · L1 (2:00) | Overview → L1 card (live terminal alongside) |
| 3 | Recorded · L2 (1:30) | Evidence Ledger → log vs evidence; AICT in a browser tab |
| 4 | Humans told · L3 (2:30) | Human Loop → the embedded Assurance Agent panel (first card) |
| 5 | Judges ask (3:30) | Ask → `Show me control 16 for run FM-B`, then whatever they name; Six Questions; Verify without us |
| 6 | Good decisions (1:30) | Agent Trail → FM-B, then FM-C; then **Live Monitor** → FM-D: EP2 DENY forms in the path (continuous compliance) |
| 7 | We attacked it (1:00) | Adversarial → Architecture EP table |
| 8 | What's missing (1:00) | Gaps; the last minute is for questions |

The presenters' script for these steps (what to show, say and why) is `presentation/JUDGING-DAY-GUIDE.html`; keep both in step.

---

## 8. Quality gates (run before showing anyone)

- **interface-design checks:**
  - *swap test*: would a template look different? It must.
  - *squint test*: hierarchy readable, nothing harsh.
  - *signature test*: point to tickmarks, the lane, the ribbon, verdict words, the exhibit rail.
  - *token test*: names belong to this world.
- **Accessibility (WCAG 2.2 AA):**
  - text contrast ≥ 4.5:1 in **both** themes;
  - focus always visible; full keyboard path (AT-15);
  - no colour-only meaning (word + glyph + hatch);
  - minimum hit area 32 px (dense desktop tool);
  - `prefers-reduced-motion` honoured;
  - charts carry a text equivalent (value labels + table).
  - ui-ux-pro-max quick checks: `python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "focus visible keyboard" --domain ux`, `… "color not only indicator" --domain ux`, `… "real-time dashboard" --domain chart`.
- **Performance:**
  - answer render < 100 ms after data arrives;
  - first paint < 1 s on the laptop;
  - no external requests (fonts self-hosted in the real console; Google Fonts only in the demo).
- **Projector test:** switch to the paper theme in the judging room if contrast washes out; browser zoom 110–125%.

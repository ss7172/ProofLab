# Guardrails plan: tasks, gates, live lane and approvals

Written 2026-10-06, from about 00:40 UTC, by the guardrails architect (a subagent). It plans the build and the tests of `AGENT-GUARDRAILS.md` (the design; § references below are to it unless prefixed `ARCH`). Times come from `ARCH §12.1`; they assume its schedule still holds and must be re-anchored by the lead.

**How to read a task:**
- **Done:** a checkable statement, not an activity.
- **Effort:** agent-hours.
- **Deps:** what must exist first.
- **Live:** tokens and model requests, if any.
- **OK:** who approves. The captain approves frame decisions; the user approves every live, cluster or install step [ARCH §12.3; working agreement].

Nothing here runs without that OK. This file runs nothing.

---

## 0. The order at a glance

The anchor: **the agents freeze at 02:00 UTC** [ARCH §12.1]. Rails are agent code, so anything not in the image by the build becomes a declared `rails-v2` treatment (§0.1).

| # | Step | Tasks | Must finish before |
|---|---|---|---|
| 1 | **Now, in parallel** | G0.1 captain decisions · **G0.2 contract (first dependency)** · S-G1 hook spike · S-G2 golden-set gate | The rails build |
| 2 | MIN rails, inside W1/W2 | B-G1 (MIN) → B-G2 → B-G4 → B-G6; S-G2 must pass | **The agent build (~00:30–01:00 in ARCH §12.1)** |
| 3 | P2 rails, only if they fit | B-G3, B-G5, B-G1 (P2 part) | The same build. Otherwise `rails-v2` (§0.1) |
| 4 | L2 smoke, then the Cedar rule | L-G1 (inside smoke, 0 extra tokens) → L-G3 (SP-1) | **The agents' freeze (02:00)** |
| 5 | Register, inventory and risks entries; orchestrator flags | B-G7, B-G8 | The `v1` freeze (03:30–04:00) |
| 6 | P0 | N1 → L-G2 → **L-G4, ADV-H-01 legs A/B (the L1 guardrail demo)** | The C16 named runs continue |
| 7 | Adversarial windows | S-G3 earlier (offline) → L-G5, L-G6 (Hostile) → L-G7 (Rogue, after ADV-R-08 at P2) | The final snapshot |
| 8 | Close | M-G1 (offline, any time after W4/W6) → L-G8 → D-G1 | Pack + submit |
| — | Optional, any time | S-G4 (NeMo-in-image, for the record) · S-G5 (cedarpy) · D-G2 (NeMo offline cross-check) | — |

**A worker is needed now.**
- The MIN delta beyond what ARCH §7.1 already gives W1/W2 is about 2.5–3 h for one worker: B-G1's MIN part, B-G2 and B-G4.
  - What §7.1 already gives: J2 with one re-ask, the freeze and empty-evidence precedence rules, the `content_filter` detection, "tool output is data", the element→site rule, the fail-closed start-up, the duplicate guard and the span env.
  - What MIN adds: X-01/X-02, T-03's envelope and `E<n>`, I-01/I-03, O-03/O-04/O-05, RT-01's hashes and the compact ALLOWs.
- A second worker runs the offline gates (S-G1, S-G2).
- If neither can start now, the freeze slips or §0.1 applies.

### 0.1 If the freeze passes before the MIN rails are in
- **Ship** whatever of the MIN set is in the Stage A/B image. §7.1's items alone already give M-02, O-01, part of O-02, T-02, the "suspicious" FLAG, X-03's normalisation, RT-01/RT-02 and the span env.
- **The rest becomes `rails-v2`,** a declared treatment:
  - a new image with its own smoke and one pilot;
  - used **only** in the adversarial windows (`ifabric-adv-…` CIDs), never for assessed runs;
  - recorded in the register and `inventory.yaml`.
- **The gap list says** "designed and tested offline, not in the assessed agents".

---

## 1. Phase 0: decisions and the contract (now)

| Id | Task | Done | Effort | Deps | Live | OK |
|---|---|---|---|---|---|---|
| **G0.1** | The captain answers DG-1–DG-7 (design §12): rails may block; the I-02 PII group at ingress; compact ALLOWs; the D15 (a) rule; the I-04 self-check; NeMo; the ADV-H-02 fault | Each DG has an answer, or its recorded default, in `architecture/decisions.md` | 0.2 (the lead relays) | — | — | **Captain** |
| **G0.2** | **Contract change (design §5.4), the first dependency.** Path A (W0 open; `prooflab/contract/` is absent at 00:08Z): amend `ifabric.evidence/1`. Path B (frozen): `1.1` by PR (R-D-06). Path C: the `rail.verdict` fallback | The schema accepts §5.2's example and a host record with `rails.allow`/`rails.counts`; it rejects a `rail_decision` without `rail.id`; `verdicts.py` holds the rail-verdict type; the one-vocabulary test asserts that rail verdicts never appear in an assessment; `outcome.real` includes `CANCELLED_RAIL`; EP-14 and EP-15 are valid `ep.id` values | 0.75–1 | The W0 owner | — | The lead (contract owner) |

---

## 2. Phase 1: offline spikes (0 tokens, local, parallel; start now)

| Id | Task | Done | Effort | Deps | Live | OK |
|---|---|---|---|---|---|---|
| **S-G1** | **Hook block/modify spike** with a stub model (extends 02 SG-5 and AR-29's W1 tests), in a Python 3.12 venv with the exact pins (`strands-agents[openai]==1.57.2`, `bedrock-agentcore==1.24.0`, `mcp==1.30.0`, ADOT 0.21.0, the pinned `openai`) | **Seven green pytest cases:** (1) X-02's `cancel_tool` on a declared-elsewhere name and on an unknown name gives an error tool result, `AfterToolCallEvent` fires with `selected_tool=None`, and nothing is dispatched; (2) T-03's `AfterToolCallEvent` Transform: the stub server's **next request body** carries the envelope and not the removed span; (3) the `format_chunk` override gives `content_filtered`, the loop ends without an exception, and the outcome is BLOCKED_GUARDRAIL with 0/0 usage; (4) `length` → `MaxTokensReachedException` is caught → `escalate`; (5) at `BeforeModelCallEvent` the stop-state cancel runs before C16 and the tally is unchanged (no reservation leak); (6) with `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_unredacted_attributes=`, the `invoke_agent` span's input is `REDACTED` (in-memory exporter); (7) X-01 filters a stub MCP list of the 7 wire names down to the declared one | 1.5 | W1's stub OpenAI-compatible server (AR-29) | — | None (local) |
| **S-G2** | **Golden-set false-positive gate.** Fixtures: the S1–S3 payloads built as `run-reference.sh` builds them; the `conflicting-context` condition text (once frozen); tool outputs generated **locally** by the packaged handlers (`DATA_DIR=workshop-static/data`) for the scenarios' sites, their element ids and the incident ids, including `lookup` with `category=all` | Every rail over every fixture gives **0 BLOCK and 0 FLAG**, except the expected T-02 FLAGs (twin "no data" for sites not in the twin) and X-03 MODIFYs (element → site). The report lists counts per rail and reproduces design §1.6 (the naive phone pattern: 8 date hits, rejected; the strict one: 0). **This gate must pass before the agent build** | 1 | B-G1's pattern table (it can start from design §3.1) | — | None |
| **S-G3** | **RTM-1 corpus** (design §9): about 40 items × 3 carriers (ticket, tool output, tool arguments), across the talk's categories. Benign goals only; no A7 | `evidence/adversarial/corpus/` with a sha256 manifest; the expected verdict per item **written and dated before the run**; a detection table per rail and category with every miss listed; the corpus is in `inventory.yaml` as a dataset | 1–1.5 | B-G1 | — | None |
| S-G4 | *(optional, for the record)* **NeMo-in-image spike:** 02 SG-1 offline, then the local arm64 `docker build` (S-0) with `EXTRA_PIP` plus `nemoguardrails[jailbreak]==0.24.1` | A note of ≤ 10 lines in this folder: the image size delta; `python -X importtime -c "import nemoguardrails"` inside the container; no outbound connection with `NEMO_GUARDRAILS_NO_USAGE_STATS=1`; `check_async` gives BLOCKED and then PASSED; **go / no-go recorded (default no-go, design §7)** | 0.75 | Docker Desktop | — | **User** (package installs in a scratch venv and a local image; no push) |
| S-G5 | *(optional; skip by default)* A `cedarpy` + vended `CedarAuthorization` stub spike, for migrating RT-04 later | A note: the wheels install; a deny on an undeclared tool; the latency | 0.5 | — | — | User (install) |

---

## 3. Phase 2: build (inside W1/W2/W3; MIN first)

| Id | Task | Done | Effort | Deps | Live | OK |
|---|---|---|---|---|---|---|
| **B-G1** | `prooflab/adapters/runtime/rails.py`, stdlib only, vendored into the bundle: the RT-04 table, the pattern table, pure rail functions returning (verdict, rule ids, output), the I-04 prompt constant, the policy sha256. **MIN rails first** (I-01, I-02 `secret.*`, I-03, X-01, X-02, X-03 normalisation, T-02, T-03 envelope + FLAG, O-03, O-04, O-05, RT-01 hashes), then P2 | Unit tests green for every rail; source **≤ 6 KB for MIN, ≤ 10 KB with P2**; **S-G2 passes**; the CI bundle gate (`len(base64(gzip -9n(bundle))) ≤ 24,000`) passes with the rails included; the start-up record echoes `rail.policy_sha256` | 2.5–3.5 (MIN part 1.5–2) | G0.2; the S-G2 patterns | — | — |
| **B-G2** | Hook wiring in the runtime adapter: **one dispatcher per event, in design §6.2's order**; X-01 in `load_tools()`; the `GatewayModel.format_chunk` override (M-02); the M-04 catch; O-01/O-02 extended triggers; compact `rails.allow` on host records; `rails.counts` on the lifecycle record | S-G1's seven cases pass against the **real** adapter, not just the spike; a stub run of one S1-like invocation emits the compact record count of design §5.3 (≈ 1–4 rail records per agent), with judgment and lifecycle records always enqueued | 1–1.5 | B-G1, W1 | — | — |
| **B-G4** | O-04 inside the emit client and the stdout spool | A record carrying the **exact value** of a test secret comes out scrubbed; exception text is scrubbed; the validator still rejects token-shaped values | 0.5 | W1's emit client | — | — |
| **B-G6** | The pin and env through `tools/make_ifabric_agents.py`'s `env_extra`: `IFABRIC_RAILS_MODE`; `inject-tool-output` added to the `IFABRIC_DECLARED_FAULTS` vocabulary; confirm `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_unredacted_attributes=` | The generator's server dry-run CR shows all three as **strings** (the CRD type is `map[string]string`) | 0.25 | W2 | — | User (with the L2 apply) |
| B-G3 | *(P2)* `model_call.guarded_check()` for I-04: stop-state → C16 `evaluate()` → reserve → POST (`max_retries=0`, the action-id hook, the OTel context) → commit → `action` record → a fail-closed parse | Stub tests: C16 DENY → no call and a rail BLOCK `c16-deny`; `content_filter` or 0/0 → BLOCK; garbage → BLOCK; an exact `SAFE` → ALLOW; the tally includes the rail call; the action record has `call.id`; **the CI test "only `model_call.py` imports `evaluate`" still passes** | 1 | W1's EP-1 | — | — |
| B-G5 | *(P2)* RT-03, the PEP 578 egress audit hook (observe), installed first in the file | In the local container run (S-0) the hook lists the destinations; there is no exception in observe; an injected `urlopen("http://example.invalid")` gives exactly one FLAG | 0.75 | S-0 | — | — |
| **B-G7** | Orchestrator (W3): `--only <agent>`; the frozen condition texts `register/conditions/{prompt-attack,encoded-attack,tool-directive}.txt`; `--fault inject-tool-output:<agent>:<tool>:<fixture>`, with the fixture frozen | A dry run prints the envelope with `condition` / `fault` and the provenance (`AUTHORIZED_TEST` / `FAULT_INJECTION`); the register lists each text's and fixture's sha256 | 0.75 | W3, W8 | — | — |
| **B-G8** | Register, inventory and risks entries (W8): the four declarations (design §6.5); components `ifabric-rails-policy` (approved version = `rail.policy_sha256`) and `ifabric-adversarial-corpus`; drafts R-GR-01 to R-GR-05 | Present in the working copies before `inv-1` (02:00) and the `v1` freeze (03:30–04:00); the owner has rated R-GR-01–05 | 0.5 (+ the owner) | W8 | — | **Owner** (ratings) |

---

## 4. Phase 3: the live lane

One action at a time. Each needs the user's OK, an identity check, a headroom check and a log line [ARCH §12.3]. Single-agent invocations use B-G7's `--only`.

| Id | Task | Done | Live: tokens / requests | OK |
|---|---|---|---|---|
| **L-G1** | **Inside L2's smoke runs** (no extra run): a synthetic canary string (`CANARY-<hex>`, not sensitive) in the smoke ticket's free text. After ≥ 60 s, Logs Insights for it over `aws/spans`, the agent's runtime log group and `/aws/modaas/gateway`. Collect RT-03's destination list (if B-G5 shipped) and X-01's discovered-tools record | **T-SPAN-01** recorded with the query ids: 0 raw hits (gap 9's span half closed for Strands) or the named residual emitter; the egress allowlist written down; X-01's record lists the 7 discovered wire names (live evidence for gap 3) | 0 extra | User (part of the smoke) |
| **L-G2** | **SG-4 + SG-2:** the self-check fails closed under the gateway guardrail and carries a CID. From the laptop, stdlib `urllib`, with the **same prompt constant and alias** as I-04, and `baggage: modaas-correlation-id=ifabric-test-sg4-<epoch>-<hex>`: one attack-quoting prompt and one benign | The attack gives `content_filter` with 0/0 tokens (I-04 would read BLOCK); the benign one gives an exact `SAFE`; both rows are in `aws/spans` under the CID. The in-agent CID carriage is confirmed again in L-G4 leg B | ≤ 1K / 2 | User |
| **L-G3** | **SP-1 with the D15 (a) rule** (design §3.10), **before the agents' freeze**. A PR with the original, forbid and restore texts → the `customer-records` ToolConfig edit → "rule is live" on **both** PDP replicas and in `/modaas/evidence` → from the laptop (key in memory) one `customer_lookup(SITE-DEN-12)` and one `customer_lookup(SITE-ADV-99)`, plus a numeric-`site` probe | ALLOW, then 403; `decision=DENY` on both replicas with the new resourceVersion; `/modaas/evidence` DENY with that `policy_version`; the numeric probe causes no Cedar evaluation error; the CR is **still Approved** (the grandfather rule); the projection's rv is recorded as the policy version | 0 tokens / 3 MCP calls | **Captain (DG-4) + user** (a shared ToolConfig: every caller) |
| **L-G4** | **ADV-H-01, legs A/B, at P0, straight after N1** (design §6.4): env patch → `IFABRIC_RAILS_MODE=observe` (~24 s; recorded as an EP-setting decision) → leg A, customer agent only, `--condition prompt-attack` → env patch → `enforce` → leg B | **Leg A:** BLOCKED_GUARDRAIL on the **task call** (span 0/0; our record with `call.id`), I-03 FLAG in observe, disposition `escalate`. **Leg B:** I-03 FLAG + I-04 BLOCK (the check call's span under the CID, which is SG-2 in the agent) + **no task-call span** + `escalate`. MON-02 agrees with both. This is the **L1 "one guardrail block on record"** | 0–7K / ≤ 6 | User (two env patches + two invocations) |
| **L-G5** | **RTM-2**, in a declared Hostile window: ≤ 30 corpus prompts straight to `nemotron-super-120b` at ≤ 1 req/s, `max_tokens` 16, CID `ifabric-adv-probe-…` | A raw capture (status, finish_reason, tokens, action id per probe) and a coverage table per category: the measured reach of EP-7 (evidence for gap G-2) | ≤ 15.5K / ≤ 30 | User |
| **L-G6** | **Hostile cases:** ADV-H-02 (the env patch adding the fault to `IFABRIC_DECLARED_FAULTS`, recorded; IT agent; the frozen fixture), ADV-H-05, ADV-H-06 | One adversarial-log row each: the pre-registered defence, the outcome on each surface (our records, `aws/spans`, the PDP where relevant), and **HELD / DETECTED-ONLY / BROKE** | ≈ 5–20K / ≤ 15 | User |
| **L-G7** | **Rogue cases:** ADV-R-01 leg 1 (network agent, `enforce`) and leg 2 (customer agent, `SITE-ADV-99`; needs L-G3); ADV-R-11 | Leg 1: an X-02 BLOCK (or X-01 withholding plus an I-03 FLAG), **no** gateway `tools/call` span (MON-02). Leg 2: our rails ALLOW, then the **first Cedar DENY** on this platform, on both PDP replicas and in `/modaas/evidence`, with our REFUSED_403 joined by `call.id`. R-11: the I-01 FLAG; the mode stays `enforce` | ≈ 15K / ≤ 12 | User (+ DG-4 for leg 2) |
| **L-G8** | The final snapshot (inside ARCH §12.1's): rail records in the export; MON-02 over every run; T-PACK-01 | The corroboration report lists 0 unexplained rail-vs-span mismatches, or each one as a finding; the exact-value scan is clean | 0 | User |

### 4.1 The live token budget for guardrails

| Step | Tokens | Model requests | When |
|---|---|---|---|
| L-G1 | 0 extra | 0 extra | L2 smoke |
| L-G2 | ≤ 1K | 2 | Before P0 |
| L-G3 | 0 | 0 (3 MCP calls) | Before the freeze |
| L-G4 | 0–7K | ≤ 6 | P0 |
| L-G5 | ≤ 15.5K | ≤ 30, at ≤ 1/s | Hostile |
| L-G6 | ≈ 5–20K | ≤ 15 | Hostile |
| L-G7 | ≈ 15K | ≤ 12 | Rogue |
| **Total** | **≤ ~60K** | **≤ ~65** | Inside ARCH §12.3's ~0.15M adversarial line, which also holds ADV-R-05 (= N3) and ADV-R-08 |

Blocked calls cost 0 tokens, so the upper figures assume no probe is blocked.

---

## 5. Phase 4: monitoring, docs, optional

| Id | Task | Done | Effort | Deps | OK |
|---|---|---|---|---|---|
| **M-G1** | MON-01 rules in `prooflab watch`; MON-02 in the stitcher's corroboration report (design §3.8) | Offline fixture tests: a BLOCK in an assessed run → a finding; a BLOCKed tool call that *has* a span → a mismatch record; a `rails.counts` mismatch → `monitoring-gap`; an ingress BLOCK with a task-model span → a mismatch | 1–1.5 | W4, W6 | — |
| **D-G1** | Docs: the gap-list entries (design §11); the deltas handed to the ARCH fixers (design §13); the adversarial-log rows; the §6.1 matrix rows; a README line for judges on re-running RTM-1 from the pack (stdlib) | `gap-list.md` carries the new entries in the kit format; the fixers have the delta list; the ADV rows exist before each test | 1 | All | — |
| D-G2 | *(optional, P3)* NeMo offline cross-check: NeMo's regex and YARA `injection_detection` over the corpus and the exported answers, in a laptop venv (`tools/nemo_crosscheck.py`, outside `prooflab/`) | The raw output is in the pack with its sha256; disagreements with our rails are listed (each one is a finding about our rails or about NeMo) | 1 | S-G3 | User (venv install) |

---

## 6. Writes and actions that need an OK

| Action | Captain | User | Why |
|---|---|---|---|
| DG-1 – DG-7 (design §12) | **Yes** | — | Frame decisions ("rails may block" is pending) |
| G0.2 contract change | The lead | — | The contract owner; versioned (R-D-06) |
| `IFABRIC_RAILS_MODE` and the other pin values (B-G6) | — | **Yes**, with the L2 apply | AgentConfig env |
| Every mode switch (L-G4, L-G6) | — | **Yes** | An AgentConfig env patch: a new generation, recorded as an EP setting |
| **The D15 (a) Cedar edit (L-G3), and its later restore** | **Yes** | **Yes** | A shared ToolConfig: it applies to every caller, the reference trio included |
| Every live call or run (L-G1 – L-G8) | — | **Yes** | Shared ceilings and tokens |
| Package installs (S-G4, S-G5, D-G2; the S-G1 venv) | — | **Yes** for S-G4, S-G5, D-G2; S-G1 is local dev | Scratch venv or local image only; no push |
| The risk ratings (B-G8) | — | The **owner** (Sree) | Risk decided first [ARCH §3.9] |

No Lambda, IAM, guardrail, AgentCore-gateway or protected-namespace write is planned [ARCH §8; 02 R-C-11].

---

## 7. Cut lines (what goes first)

1. **Cut first:** D-G2, S-G5, S-G4, O-07, RT-03 enforce, T-06.
2. **Then:** RTM-2 (L-G5); B-G5 (RT-03 observe); T-05; X-05; B-G3 (I-04). I-03 stays FLAG-only, and O-02 escalates on it.
3. **Never cut:**
   - G0.2;
   - S-G2 (the false-positive gate);
   - the MIN rails, or failing that the §0.1 path;
   - L-G1's canary;
   - L-G4 leg A (the L1 guardrail block);
   - B-G4 (O-04 secrets scrubbing);
   - the gap-list entries.

---

## 8. Effort summary

| Phase | Agent-hours |
|---|---|
| 0: decisions + contract | 1–1.25 |
| 1: offline spikes | 3.5–4 (+ 1.25 optional) |
| 2: build | 7–9 (**MIN delta ≈ 2.5–3**) |
| 3: live | lane time only; ≤ ~60K tokens |
| 4: monitoring + docs | 2–2.5 (+ 1 optional) |
| **Total** | **≈ 13.5–17** (MIN path ≈ 6–7, including G0.2, S-G1 and S-G2) |

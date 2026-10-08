# ProofLab: team iFabric

**TM Forum Innovate Americas 2026, Trustworthy AI track.** ProofLab is team iFabric's assurance system for three
collaborating network-fault agents running on AWS Bedrock AgentCore behind the MoDaaS gateway. It runs three controls
(C16 token cap, C7 complete audit log, C9 latency drift) against a dated, versioned control register, and hands over one
sealed Evidence Pack. From the pack alone, a stranger can answer "was control X satisfied for run Y, or between T1 and
T2?" and the six auditor questions.

> **Claim C-FM-01:** "During fault resolution, the three collaborating agents meet our declared event-recording, drift
> and token-spend requirements."

## Final submission

| Item | Value |
|---|---|
| Zip | `submission-ifabric-20261006T181458Z.zip` (uploaded 2026-10-06 18:14:58Z with `submit.sh`, through `tools/submit_wrapper.sh`) |
| Zip sha256 | `12e36f537519b57ba7f1f8ccf50d74347d3fa3d1c5f2f49e82e0698e79165d93` |
| Pack MANIFEST sha256 (the root) | `7146e79c94d66d562e8213c61950934724a7e7a61673214cf7624ff7e7768b08`, published as a work note on ServiceNow INC0010338 (2026-10-06 19:42:37Z) |
| Checks before the upload | secret scan clean, MANIFEST verified, red-flag lint 0 (`prooflab pack lint`) |
| Read-back | same S3 VersionId and ETag before and after, sha256 equal to the local zip, MANIFEST and scan clean on the unzipped copy |
| Register in force | `v1.1`, sha256 `e48b07e7…` (`register/versions/v1.1.yaml`) |

## Results (named runs; all times UTC, 2026-10-06)

| Run | Run id | What it shows | C16 | C7 | C9 |
|---|---|---|---|---|---|
| N1 | `ifabric-run-1791294968-36d929` | Normal run; the inline guard refused 3 over-cap calls | SATISFIED 22,271 / 25,000 | SATISFIED 55/55 | SATISFIED |
| N2b | `ifabric-run-1791297942-c57210` | S2 conflicting context, observe mode (C16 breach attempt) | SATISFIED 24,213 | SATISFIED | NOT ASSESSED (no S2 baseline) |
| N4 | `ifabric-run-1791299967-903ba1` | Declared fault: one record suppressed | SATISFIED | **BREACHED 43/44 → INC0010351** | INDETERMINATE |
| N8 | `ifabric-run-1791300807-0ffaa0` | IT agent swapped to nemotron-nano-9b (C9 breach attempt) | SATISFIED | SATISFIED | SATISFIED (IT −62.3%, inside ±75%) |
| N5 | `ifabric-run-1791301189-1cc86f` | Re-test of N4; closed the finding | SATISFIED | SATISFIED 45/45 | INDETERMINATE |
| N2c | `ifabric-run-1791301875-f821a3` | S2 retry; a guardrail blocked one call | SATISFIED 14,063 | BREACHED 36/37 (unplanned; gap B38, not notified) | NOT ASSESSED |

- **C7's full loop:** N4 breach → ServiceNow INC0010351 → Assurance agent analysis → closed only by the passing N5 re-test.
- **No C16 or C9 breach was produced.** The C16 inline guard held. The C9 model swap made IT faster, still inside the band approved before the test. No threshold was tuned to force a breach.
- **Thresholds** (`register.yaml` v1.1):
  - C16: ≤ 25,000 tokens per run.
  - C7: coverage 100%, largest gap ≤ 29,000 ms.
  - C9: within ±75% of a frozen per-agent baseline, with 0 errors.
- **Dates and approvals:**
  - v1: frozen and S3-dated 12:40:22Z, approved on INC0010321 at 13:02:37Z.
  - v1.1: frozen 13:36:43Z and S3-dated 13:38:05Z, before N1. It was approved on INC0010338 at **15:09:49Z, after N1**, which every N1 answer states.
- **One declared post-hoc change:** C16 went from 20,000 to 25,000 (rule `C16-cap/2`, with its reason in `evidence-templates/decisions-log.md`).

All 21 runs, including the NOT COUNTED attempts, warm-ups and pilots, are in the pack's run catalogue and `named-runs.md`.

## Architecture in brief

- **The live path:**
  - The orchestrator (`prooflab run`) makes the run id. **EP-0** refuses to start a run on an unapproved agent version.
  - The orchestrator invokes customer → IT → network → IT on AgentCore.
  - Inside each agent, **Strands SDK hooks** run, in a fixed order: rails → the C16 check → emit.
    - **EP-1 (C16):** checks every model call inline and cancels it when the cap would be crossed.
    - **EP-3:** tool rails.
    - **EP-4:** judgment and output rails.
    - **EP-14:** ingress rails.
    - **EP-15:** egress audit with `sys.addaudithook`.
  - Every record goes to stdout (CloudWatch) and to the platform audit ledger. The agent never waits for the record.
- **Off the path:**
  - The inventory and the risk register (5×5 matrix; the appetite drives each threshold).
  - The control register: frozen, S3-dated, owner-approved, and pinned into the agents at deploy, never read at run time.
  - Pull adapters, the stateless evaluators, the stitcher, the Evidence Pack, and the query tool and dashboard.
- **EP-2:** the same C16 core (evaluator sha256 `bebe56bd…`) replays every call over the gateway's own log and must reconcile with EP-1, call by call.
- **The human loop:** findings go to ServiceNow (notify, then poll; no inbound endpoint). The Assurance agent writes an analysis note. Only a passing re-test closes a finding.

**Enforcement points, stated precisely:** the architecture **maps 17** (EP-0 to EP-16, `evidence/security-matrix.md`).
- **We built 8:** EP-0, 1, 2, 3, 4, 5, 14 and 15 (EP-5 and EP-15 record only).
- **The platform or the owner owns the other 9;** we record their decisions.
- **12 have evidence in the submitted pack.** EP-6, 8, 9, 12 and 16 are marked "not exercised".

**Adversarial testing, stated precisely:** the cases ADV-H-01 and ADV-R-01 and a 40-item attack corpus are
**pre-registered** in `evidence/adversarial/`. **They were not executed before the submission,** and the pack claims no
adversarial result. Defences were exercised elsewhere:
- the gateway guardrail blocked a call in N2c (in the pack);
- the Cedar rule refused an out-of-scope tool call during setup (`SITE-ADV-99` → 403 PolicyDenied; ops records only);
- the guardrail blocked a prompt attack in the live Level 1 check.

Detail:
- `architecture/ARCHITECTURE.md`
- `architecture/guardrails/AGENT-GUARDRAILS.md` (the rail catalogue: I-*, X-*, T-*, M-*, O-*, RT-*)
- `architecture/decisions.md`

## Verify and query (offline; no AWS credentials needed)

Run these from the repo root, or from inside an unzipped pack, which ships its own copy of the tool. Inside a pack,
set `PYTHONDONTWRITEBYTECODE=1` so that Python writes no cache files into it.

```bash
P=<unzipped pack>/evidence
python3 tools/manifest.py verify $P                      # re-hashes every file against MANIFEST.json
shasum -a 256 $P/MANIFEST.json                           # = the root on INC0010338
python3 -m prooflab query --pack $P --control C16 --run ifabric-run-1791294968-36d929
python3 -m prooflab query --pack $P --control C16 --run ifabric-run-1791294968-36d929 \
  --window 2026-10-06T13:56:30Z..2026-10-06T13:57:00Z      # run + window: the evidence slice inside T1..T2
python3 -m prooflab query --pack $P --control C7 --run ifabric-run-1791299967-903ba1   # breach + human loop
python3 -m prooflab query --pack $P --incident ifabric-run-1791299967-903ba1           # six auditor questions
python3 -m prooflab query --pack $P --runs                                              # every run, labelled
```

**Dashboard** (loopback, read-only). It refuses to start if AWS secrets are set in the shell:

```bash
env -i HOME="$HOME" PATH=/usr/bin:/bin /usr/bin/python3 -m prooflab console --pack $P --port 8787
```

**Level 1 live checks**, which need workshop AWS credentials through the team's `hk` wrapper:
- a normal call goes through the gateway;
- an attack is blocked;
- a direct model call is refused;
- each agent's approval is shown.

```bash
bash tools/l1-checks.sh --dry-run    # shows each call, calls nothing
bash tools/l1-checks.sh --live
```

The presenter cheat sheet, with the verified Ask questions, is in `docs/presentation/cheatsheet.md`.

## Repository layout

| Path | Contents |
|---|---|
| `agents/` | The four AgentCore agents (`ifabric-customer`, `ifabric-it`, `ifabric-network`, `ifabric-assurance`) |
| `adapters/runtime/` | In-agent hooks: model call (EP-1), tool call (EP-3), judgment (EP-4), rails, egress (EP-15), emit client |
| `prooflab/` | Contract, evaluators (`c16_core.py`, c16, c7, c9, approval, risk), collectors, stitcher, store, pack builder and lint, query tool, console, human loop |
| `register/` | Register versions (frozen, with sha256 and S3 date proofs), risks, inventory, scenarios S1–S3, experiments and derivation rules |
| `evidence-templates/` | The pack README, decisions log, named runs, security matrix and field-coverage templates |
| `evidence/adversarial/` | The pre-registered adversarial cases and the corpus |
| `architecture/` | The architecture, the guardrails design and the decisions |
| `docs/` | The named-runs runbook, the run of show, the presentation cheat sheet |
| `tools/` | The merge gate, the manifest, `stage_t1.py`, the submit wrapper, the Level 1 checks |
| `tests/` | Unit, integration and rehearsal tests. The merge gate is `bash tools/gate.sh` |
| `gap-list.md` | Declared gaps: section A (ServiceNow, Arth's, byte-identical to his handover) and section B (B1–B38) |
| `notes/`, `handoffs/`, `hackathon-context/` | Platform notes, verified facts, the ServiceNow handover and the challenge sources |

## Main gaps (full list in `gap-list.md` and `evidence-templates/field-coverage.md`)

- **One shared identity (B37):** one human ServiceNow account and one shared AWS role. Separation of duties is procedure only.
- **Missing fields:** some agent-side records lack the run condition, model id, pin and image digest. These facts are joined from other sources and labelled as joined.
- **Platform gaps we compensate for:**
  - no per-run spend halt → C16;
  - refusals logged as ALLOW → our real-outcome records;
  - undeclared tools offered to every agent → rails X-01 and X-02;
  - the ledger cannot prove non-alteration → two witnesses, MANIFEST and the published root.
- **The risk register's ratings still carry the label "DRAFT: owner to confirm"** in the frozen file. The EU AI Act tier is UNVERIFIED against a primary source.
- **No sealing or signing of records** (out of scope). `prooflab watch` (live C7/C9) was built but not used in the runs.

## Team

- **Sree:** captain and accountable owner (`annapurna@invences.com`). Sree approves the thresholds and the agent versions.
- **Arth:** ServiceNow integration and the Assurance agent analyser.

The AWS-side build and evidence pipeline were developed with Claude Code.

# Handoff 3: Evidence Console plan + ServiceNow Assurance Agent (team iFabric)

**From:** Arth (ServiceNow workstream), built together with the Evidence Console planning session. **To:** the teammate and their coding agent. **Date:** 2026-10-05.

**Start here.** This package contains:
- the **ProofLab Evidence Console** plan (the presentation dashboard), already integrated with the ServiceNow **Nemotron Assurance Agent**;
- the agent's code with instructions;
- the live evidence;
- the updated presentation-day deliverables.

It builds on `servicenow-integration-package-v3.tgz`, which you already have (sha256 `7626ecd7807037005fe91115eeb3614fe46969e7bd8c0a156663beecaeb569b7`). Nothing here asks you to undo work done from v3.

**Check the package first.** From this folder, `python3 deliverables/evidence-pack/tools/manifest.py verify .` must print OK. It checks the SHA-256 of every file against `MANIFEST.json`.

---

## 1. What's inside
```
ifabric-handoff-3/
├── README.md                     ← this file
├── MANIFEST.json                 ← SHA-256 of every file (verify above)
├── evidence-console-plan/        ← the console plan: README (index), 01–09, schemas/, examples/, demo/, presentation/
│   └── 08-SERVICENOW-AND-ASSURANCE-AGENT.md   ← THE Assurance Agent + GUI spec (replaces "handoff 2"; same § numbers)
├── code/
│   ├── prooflab/servicenow/      ← adapter, Assurance Agent, case JSON, drop-in panel, local server
│   ├── prooflab/tests/           ← 152 tests (fake ServiceNow + fake modaas-agw over real HTTP)
│   └── tools/sn_roundtrip_test.py ← live write-path test (stand-in, no model): already run by Arth, see §4
├── deliverables/                 ← presentation-day pieces (TEAMMATE_ACTIONS, PRESENTATION_DAY_INTEGRATION, evidence-pack/, pitch/, thresholds/, architecture/)
└── docs/                         ← handoff 1 (incidents, Finding contract) + the winning playbook
```

## 2. What changed since v3 (the delta)
| Area | Change | Where |
|---|---|---|
| **Code: P6 re-test fix** | New optional finding key `retest` = {assessment, verdict, threshold_version, at}. Check P6 ("not closed without a linked passing re-test") now **passes** when a resolved incident links a SATISFIED re-test at the same threshold version. Before, every legitimately closed finding showed P6 red. 5 files, +6 tests. | `code/prooflab/servicenow/{finding,finding_context,assurance_checks}.py`; `08` §5.0, §16 |
| **Code: panel honesty fixes** | A note that isn't in the agent's run log (forged or edited) is now shown under one red group, "Note text — not written by the agent (untrusted)", never as "checked" or as "Nemotron's judgement". Step 5 reads "AI Control Tower / AICT inventory entry", because it is an inventory link, not a trace (gap A3). | `code/prooflab/servicenow/panel/`; preview `preview-forged-note-fake-data.jpg` |
| **Tests** | **152 passed** on Python 3.9 and 3.13 (was 146). | `code/prooflab/tests/` |
| **Verified live on ServiceNow** | The Assurance Agent's **write path**, 2026-10-05 on test incident INC0010232, 9/9 checks: note written, read back unchanged (SHA-256 matched), real journal parsed, re-run SKIPPED, five sections computed. A TEST stand-in replaced the model, so the **Nemotron call itself is still yours to prove** (step 4 below). | `deliverables/evidence-pack/servicenow/wiring-tests/assurance-agent-roundtrip/` (run record, test log, screenshot) |
| **Spec location** | "Handoff 2" is merged into `evidence-console-plan/08-…` with the same section numbers. The old file is archived and **not** shipped. | `08` header |
| **§5.2 first Nemotron run** | Now uses a **TEST** delivery log and `notify --dry-run` before `analyze`, so the wiring test never enters the production evidence and P4 counts correctly. | `08` §5.2 |
| **Evidence Console plan** | The whole plan: judging criteria → screens, zero-trust architecture, contracts + schema + fixtures, AWS-side build, UI spec, console API, build order + acceptance tests, HTML demo, judging-day guide. The console's Human Loop view **embeds our panel**. | `evidence-console-plan/README.md` |
| **Deliverables docs** | Test counts, the `retest` requirement, EP numbering (ServiceNow human queue = **EP4** in the console's table), live status, gap list A15/A17/A18. | `deliverables/` |

## 3. Do this, in order

**Assurance Agent (code and wiring):**
1. **Merge the code.** Copy `code/prooflab/servicenow/` and `code/prooflab/tests/` over your repo's `prooflab/servicenow/` and `prooflab/tests/` (keep your other files). Then:
   - `python3 -m pytest prooflab/tests -q` must print **152 passed** (stdlib only; pytest is the only dev dependency);
   - `python3 -m prooflab.servicenow selftest` must print OK (ServiceNow secrets from Arth, loaded privately; handoff 1 §5.3).
2. **Configure** the variables in `08` §4: ServiceNow (backend only), `MODAAS_GATEWAY_URL`, `MODAAS_MODEL_ALIAS` (an *approved* Nemotron alias).
3. **Attach the finding context** in your evaluator (`08` §5.0): `measured`, `limit`, `register`, `trace`, and **`retest`** when a passing re-test closes a finding. **This is what fills agent movement and policy alignment on the judges' screen.**
4. **Prove the Nemotron call once** in the workshop IDE with the exact commands in `08` §5.2.
   - Expect `WRITTEN` on INC0010232, with `Model: NVIDIA Nemotron via modaas-agw:…`.
   - Send Arth the output and the run record.
5. **Wire the loop** (`08` §5.1):
   - after `notify()` returns DELIVERED, call `run_assurance_agent()` off the request path;
   - run `check` on a short loop;
   - write a case snapshot for **every** finding with `case --out evidence/servicenow/cases` (`08` §7.1). The console never calls ServiceNow; it reads those snapshots (`07` `GET /api/v1/cases`).
6. **Deploy `ifabric_assurance_agent` on AgentCore** with Sree's approval, then switch the backend (`08` §5.3). This is what AI Control Tower discovers.

**Evidence Console (the dashboard):**

7. **Build it** from `evidence-console-plan/`:
   - give your coding agent the first instruction in `evidence-console-plan/README.md` ("What to give the teammate's coding agent");
   - follow `09` for the order and the acceptance tests;
   - the Human Loop view **embeds the drop-in panel** (`08` §7.2) from `code/prooflab/servicenow/panel/ifabric-case-panel.{js,css}`. The copies in `evidence-console-plan/demo/assurance-panel/` are byte-identical; the package build checks this.
   - Build and test against `code/prooflab/servicenow/examples/cases.sample-fake-data.json` and the demo cases.

**Judging day:**

8. Follow `deliverables/PRESENTATION_DAY_INTEGRATION.md`. The work list with "done when" checks is `deliverables/TEAMMATE_ACTIONS.md`.

## 4. Verification status (never claim more in the demo)
| Part | Status |
|---|---|
| Incidents (create, read back, reuse, owner response); full finding text in the description | **Verified live** (INC0010231, INC0010232) |
| Assurance Agent write path: note, readback digest, journal parsing, idempotent re-run, five sections | **Verified live** 2026-10-05 (INC0010232, stand-in model) by `code/tools/sn_roundtrip_test.py`. **Don't re-run it unless Arth asks:** each run writes another TEST note onto the shared incident. |
| Nemotron call through `modaas-agw` | **Pending**: step 4 (workshop IDE) |
| AgentCore runtime `ifabric_assurance_agent` + AICT discovery | **Pending**: step 6 |
| Evidence Console | **Planned**, with a working HTML demo on synthetic data (`evidence-console-plan/demo/`). All demo data is `provenance: SYNTHETIC`, and every threshold is illustrative. |

## 5. Not included, on purpose
- `archive/`: the superseded handoff 2. `08` is the source of truth.
- The nested `servicenow-integration-package-v3.tgz`: the code ships once, as the tree in `code/`.
- Private planning files, caches and any secret. The package build refuses secret patterns (AWS keys, bearer tokens, presigned URLs, private keys).

## 6. Rules that still apply
- Model calls only through `modaas-agw` with a Nemotron alias. ServiceNow only from the backend.
- Never store or show model reasoning.
- Never put the OAuth secret, gateway keys, tokens, IdeUrl/CockpitUrl or presigned URLs in code, files, logs, screenshots or chat.
- Wiring-test logs (`wiring-tests/**`) never go into the production `delivery-log.jsonl`.
- Don't change ServiceNow configuration, users or roles. Ask Arth.

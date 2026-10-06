# Handoff: ServiceNow integration, human loop & evidence (team iFabric)

**From:** the ServiceNow workstream (Arth, with Claude Code). **To:** the teammate building the AWS side (controls C7/C9/C16, evaluators, agents), and their coding agent.
**Date:** 2026-10-05. **Status:** the ServiceNow side is built and **verified live**. What remains is wiring it to your control evaluators and producing the Evidence Pack.

> **For a coding agent reading this:**
> - Treat this file as the integration spec.
> - Do not change ServiceNow configuration and do not create ServiceNow users or credentials.
> - Never print, commit or log the OAuth client secret.
> - Everything you need is in §5–§9. Acceptance criteria are in §13.

---

## 0. TL;DR: what you must do

1. **Copy** the `prooflab/` package into your repo (§5). It is stdlib-only and needs no installs.
2. **Load 3 env vars** in the IDE terminal: `SNOW_INSTANCE`, `SNOW_CLIENT_ID`, `SNOW_CLIENT_SECRET` (get the ID and secret from Arth; §5.3). Run `selftest`.
3. Make **every evaluator emit a Finding** (JSON spec in §6) and call `notify()` for every **BREACHED** result and every agent **escalation** (§7). It must run **off the agent's execution path**.
4. **Store evidence in the standard layout** (§8.3). Every record must be bound to **control + threshold version + run/window + source record**.
5. Before judging, run `check` (response or silence) and `export` (incident readback) for every finding. Then build the **MANIFEST** and **submit to S3 with readback** (§8.4–§8.6).
6. Make your **query tool** show the ServiceNow status next to each verdict (§8.7). Judges get **2 minutes**.
7. Read **`HACKATHON_WINNING_PLAYBOOK.md`** (separate file in the same package) before building more agents or controls: §1 the full brief restated (no slides needed), §2 field guide for agents and workshop modules, §3 best-practices checklist (the team's definition of "done well"), §4 scorecard to self-score at every checkpoint.

---

## 1. Why this matters (judging, in one page)

| Source | Requirement | What covers it |
|---|---|---|
| Judging is **sequential** (official judging rule, Playbook §1.1) | **L1** AWS foundation (MoDaaS guardrails + Nemotron) → **L2** **ServiceNow AI Control Tower adds observability** → **L3** **ServiceNow sandbox extends the chain of evidence**. A level only counts if the one before it is shown. | L2: AICT connection (done, §2). L3: incidents + evidence chain (this package) + the Nemotron Assurance Agent writing into ServiceNow (`evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md`, formerly handoff 2) |
| Organizer on the kickoff call | "ServiceNow Control Tower and **human loop** … **absolutely needed**" | `notify()` = alert to a named human |
| Masterclass audit question | "Show me what was done … **who was told** when something went wrong … can I trust it hasn't changed?" | Incident assigned to the **named owner** + readback + delivery log |
| C9 control test (masterclass) | "generate the alert … that alert needs to go to a human, and you need to know **what that human name is**" | `assigned_to` = owner from `register.yaml` |
| Out-of-scope note | A human **reply is not required**, but "the alert, its named recipient and the **silence** must still be recorded" | `check_response()` → `RESPONDED` / `NO_RESPONSE_OBSERVED` |
| Axis 3 bonus | "**Second enforcement point**, same architecture, nothing rewritten" | The same findings go to a **human approval queue** (one of the 12 official enforcement-point types listed in Playbook §1.6) through the same contract |
| Axis 3 bonus | "**Continuous compliance**": verdict formed inline, while it runs | Evaluate on a schedule or watcher and notify within minutes (§7.6) |
| Auditor questions | **who acted, what it touched, authorized, who approved, integrity, reconstruct** | Evidence layout and record schema (§8) |
| What **loses** marks | Records covering only some actions · evidence only we can verify · a finding closed without a passing re-test · a control storing its own threshold · request-path-only design | §8, §10 |

---

## 2. What already exists on ServiceNow (verified live)

No secrets are listed here.

| Item | Value / status |
|---|---|
| Instance (shared by all teams) | `platformdemoh8.service-now.com` |
| **AICT Amazon connection** | **"iFabric Hackathon 2026"** → AWS account `613052889143`, `us-east-1`, role `SgcAictReadOnlyAccessRole`, log group `/aws/bedrock/aict-invocations`. "Connection verified"; 14 import jobs active; parent jobs **every 15 min**; one cycle takes ~4 min, 0 errors |
| AICT discovery (proof) | 6 "AI Function" records from `SG-AmazonBedrockAgentCore`: `hackathon_helper`, `customer_experience_agent`, `network_resolution_agent` v1+v2, `it_resolution_agent` v1+v2, created at the exact times of our import runs. **New runtime versions appear automatically on the next import.** |
| Control owner (all three controls) | **Sree Annapurna Rallabandi**, ServiceNow user `annapurna@invences.com` (has admin + itil) |
| Integration identity | User **`ifabric.integration`** (role **itil only**, no admin). **OAuth app "iFabric Agent Assurance"**: client-credentials grant, app user = iFabric Integration |
| Instance setting we enabled | `glide.oauth.inbound.client.credential.grant_type.enabled = true` (Global) |
| Why OAuth, not passwords | Basic auth returned 401 for both accounts (`login.failed` ×4). OAuth client credentials works: token issued, Table API 200 |
| **Live end-to-end test** | **INC0010231**: created by `ifabric.integration`, assigned to Sree, correlation id set, evidence work note written, read back ✅; second `notify` reused it (no duplicate) ✅; `check` → AWAITING_RESPONSE, then **RESPONDED** after Sree posted a note ✅. It is a **TEST** incident; Arth closes it before judging |

**Naming rule (shared instance):** every team's reference agents have identical names in AICT. **Any agent you create must be named `ifabric_…`** (lowercase where Kubernetes requires it), so judges can find ours.

---

## 3. Architecture: where ServiceNow sits

```
AgentCore agents ─► modaas-agw gateway (+guardrail, Cedar) ─► Bedrock Nemotron
      │ spans/metrics            │ per-call usage records          │
      ▼                          ▼                                 ▼
 CloudWatch            gateway logs / audit-store ledger (/records?cid=)
      └──────────────► YOUR collectors ─► evaluators C7/C9/C16 (stateless, read register.yaml)
                                              │ assessment (verdict + measured + bindings)
                                              ├─► evidence/assessments/…   (always)
                                              └─► Finding JSON ─► prooflab.servicenow.notify()   (off-path)
                                                                      │ OAuth client-credentials
                                                                      ▼
                                       ServiceNow incident (assigned to owner) ◄── owner note / status
                                                                      │ readback / check / export
                                                                      ▼
                                   evidence/servicenow/{delivery-log.jsonl, incidents/INC*.json}
AICT ◄── read-only discovery every 15 min (AgentCore runtimes, models, traces) ── AWS account
```

**Design rules this keeps** (the brief's "five habits that keep the design honest"):
- **Telemetry never judges.** Collectors only capture.
- **The evaluator never remembers.** It is pure; its inputs are the captured records plus the register version.
- **The register is never in the execution path.** Evaluators read a frozen `register.yaml` version.
- **The ledger never interprets.** Raw captures are stored untouched, next to normalized facts.
- **ServiceNow is never in the agent's request path.** `notify()` runs after evaluation. A ServiceNow outage creates an evidence gap, not an agent failure.

**Transport mapping.** The brief's rule is "one contract, four transports": every enforcement point reaches the architecture the same way, through one of four transports:

| Transport | Kind | For |
|---|---|---|
| `evaluate()` | Synchronous, in the path | In-transaction controls that must be able to refuse |
| `emit()` | Asynchronous, on an event bus | Anything that only has to be recorded |
| `callback()` | A webhook for a verdict that arrives later | Deferred actions, human approval |
| `pull()` | On a schedule, off the live path | Scheduled and continuous controls |

In our design: evaluators `emit()` findings; `notify()` is the **`callback()`** transport (a human verdict arrives later); `check_response()` is a **`pull()`**. If you add inline admission (C16 bonus), that is `evaluate()`; it is separate from this package.

---

## 4. The code you are receiving

```
prooflab/
  __init__.py
  servicenow/
    finding.py        # Finding contract + validation + incident payload mapping
    client.py         # OAuth client-credentials + Table API (HTTPS only, no redirects)
    notifier.py       # notify(), check_response(), export_incident()
    delivery_log.py   # append-only JSONL evidence log
    cli.py, __main__  # python -m prooflab.servicenow {selftest,notify,check,export}
    README.md         # short usage
    examples/test_finding.json
  tests/              # 46 tests, fake ServiceNow over real HTTP; pass on Python 3.9 and 3.13
```

**Guarantees (all covered by tests):**

| Guarantee | How |
|---|---|
| **No duplicates** | Incident `correlation_id` = deterministic `finding_id`; looked up before create; a re-run reuses it |
| **Never touches other teams' records** | Every lookup filters `sys_created_by = ifabric.integration` |
| **Honest delivery** | `DELIVERED` only after a **readback** shows the right correlation id and assignee. A lost, 5xx or garbled answer → `OUTCOME_UNKNOWN`, then reconciled by correlation id (never blindly re-sent). Every path ends in a terminal state (`DELIVERED`, `FAILED`, `UNVERIFIED`, `OUTCOME_UNKNOWN`, `DRY_RUN`) |
| **Honest response** | Only the **owner's** note or field change counts as `RESPONDED`; system or other-admin activity is recorded as `non_owner_actors`. Silence only becomes `NO_RESPONSE_OBSERVED` **after the cutoff**. Unreadable history → `RESPONSE_UNKNOWN` (never "silence") |
| **Caller set** | Caller = `ifabric.integration` (the form requires it, so the owner can press Update) |
| **Security** | Secrets come only from env vars and are never logged; HTTPS only; redirects refused; query-injection characters (`^`, CR, LF) rejected |
| **Evidence** | Append-only, fsync'd JSONL log; a torn last line is tolerated; `export` writes the incident as ServiceNow stores it, plus all notes |

---

## 5. Merge the code into your repo

### 5.1 Get the files into the IDE
Arth gives you `servicenow-integration-package.tgz` (at the root of Arth's project folder). Then:
1. Open the workshop IDE (**IdeUrl** on the event dashboard).
2. Drag the `.tgz` into the IDE **Explorer** panel, into your repo root.
3. In the IDE terminal:
   ```bash
   cd <your-repo-root>
   tar xzf servicenow-integration-package.tgz      # creates ./prooflab/ and SERVICENOW_INTEGRATION_HANDOFF.md
   rm servicenow-integration-package.tgz
   ```
If your repo is on git (GitHub or CodeCommit), Arth can push the folder instead; the result is the same.

### 5.2 Fit it into your layout
- Keep the top-level package name **`prooflab`**. The imports are absolute (`from prooflab.servicenow…`).
- If your repo already has a `prooflab/` package, drop in `prooflab/servicenow/` and `prooflab/tests/` and keep your own `__init__.py`.
- If you must nest it (for example `src/`), put `src/` on `PYTHONPATH` rather than renaming imports.
- **No dependencies.** It runs on the IDE's `python3` (3.9+). pytest is only needed to run the tests: `pip install --user pytest`.
- Add to `.gitignore`:
  ```
  .venv*/
  *.env
  evidence/**/tmp/
  ```
  Do **not** ignore `evidence/servicenow/` itself; it is part of the Evidence Pack.

### 5.3 Credentials (never in files, code, chat or screenshots)
In the IDE terminal, **one line at a time** (pasting several `read` lines together breaks them):
```bash
export SNOW_INSTANCE=platformdemoh8.service-now.com
read -r SNOW_CLIENT_ID && export SNOW_CLIENT_ID            # paste Client ID, Enter
read -rs SNOW_CLIENT_SECRET && export SNOW_CLIENT_SECRET   # paste Client Secret, Enter (nothing shows)
echo "id=${#SNOW_CLIENT_ID} secret=${#SNOW_CLIENT_SECRET}" # both should print 32
```
- The Client ID and Secret are in Arth or Sree's password manager. Ask them; do not create new ones.
- The values last only for that terminal. For a long-running watcher, put them in `~/.prooflab-snow.env` (`chmod 600`, outside the repo, never committed) and `source` it. Delete the file at the end of the event.
- Optional variables:
  - `SNOW_OWNER_USER` (default `annapurna@invences.com`)
  - `SNOW_INTEGRATION_USER` (default `ifabric.integration`)
  - `PROOFLAB_DELIVERY_LOG` (default `evidence/servicenow/delivery-log.jsonl`)

### 5.4 Verify
```bash
python3 -m pytest prooflab/tests -q                       # expect 46 passed (offline, fake ServiceNow)
python3 -m prooflab.servicenow selftest                   # expect "OK: OAuth token issued ..."
python3 -m prooflab.servicenow notify --finding prooflab/servicenow/examples/test_finding.json --dry-run
```
`--dry-run` writes **nothing** to ServiceNow. Do **not** run a real `notify` on the example file; INC0010231 already exists for it.

---

## 6. The Finding contract (JSON spec)

A **Finding** is the only thing the ServiceNow side needs from you. It is a fact your evaluator already computed, rendered for a human.

```json
{
  "control_ref": "C16",
  "control_id": "ACN-COST-001",
  "threshold_version": "G-FM-v1",
  "scope_kind": "run",
  "scope_id": "FM-B",
  "verdict": "BREACHED",
  "summary": "10,800 tokens > cap 10,000 (all 3 agents + retries)",
  "detected_at": "2026-10-05T14:03:12Z",
  "evidence": [
    "assessment:evidence/assessments/C16/run_FM-B.json",
    "gateway:action_id=6f1c...e2",
    "ledger:cid=fault-1788864931",
    "register:register.yaml@G-FM-v1"
  ],
  "kind": "finding"
}
```

| Field | Required | Allowed values / rule |
|---|---|---|
| `control_ref` | ✔ | `C7`, `C9`, `C16`, or `ESC` for an agent escalation |
| `control_id` | ✔ | `AIA-LOG-001` (C7), `AIA-ARC-006` (C9), `ACN-COST-001` (C16), `AGENT-ESCALATION` (ESC) |
| `threshold_version` | ✔ | **Exactly** the frozen version in `register.yaml` (e.g. `G-FM-v1`). Never `latest`. A new version means a new finding id |
| `scope_kind` | ✔ | `run`, `window`, `interval` or `escalation` |
| `scope_id` | ✔ | run id / ledger cid (`run`, `escalation`); window start in UTC, e.g. `2026-10-05T09` (`window`); `START..END` (`interval`) |
| `verdict` | ✔ | `BREACHED`, `ESCALATED`, `INDETERMINATE` or `SATISFIED` |
| `summary` | ✔ | Measured value vs limit, human-readable, ≤ ~100 chars |
| `detected_at` | ✔ | ISO-8601 UTC `YYYY-MM-DDTHH:MM:SSZ` |
| `evidence` | – | List of strings, each a **resolvable reference** (prefix conventions in §8.2). The first 50 go into the incident's work notes |
| `kind` | – | Default `finding`. Use `monitoring-gap` for missing data and `escalation` for agent escalations |

**Forbidden characters** in any id field: `^`, CR, LF. They are rejected because they would alter a ServiceNow query.

**Identity:** `finding_id = "ifabric:{control_ref}:{threshold_version}:{scope_kind}:{scope_id}:{kind}"`, capped at 100 characters (hashed if longer). The **same finding gives the same incident**: re-running an evaluator never creates duplicates.

**Python API** (use this inside your evaluator process instead of shelling out):
```python
from prooflab.servicenow.client import ServiceNowClient
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.servicenow.notifier import notify, check_response, export_incident

client = ServiceNowClient.from_env()                        # reads SNOW_* env vars
log = DeliveryLog("evidence/servicenow/delivery-log.jsonl")
finding = finding_from_dict(finding_json)                   # validates; raises ValueError
result = notify(finding, client, log, owner_user="annapurna@invences.com")
# result.state in {"DELIVERED", "FAILED", "UNVERIFIED", "OUTCOME_UNKNOWN", "DRY_RUN"}; result.number = "INC00…"
```
**CLI equivalent:** `python3 -m prooflab.servicenow notify --finding evidence/findings/<file>.json`. Exit codes: 0 ok, 1 ServiceNow problem, 2 bad input.

---

## 7. Wiring it to the controls (what your evaluators must do)

General rules:
- **Always** write the assessment (including **SATISFIED**) to `evidence/assessments/`.
- **Notify** only for `BREACHED`, `ESCALATED` and `monitoring-gap` (`INDETERMINATE` caused by missing monitoring data).
- **Never** notify for `SATISFIED`; judges want alerts on failures, and evidence for passes.
- **Off-path:** call `notify()` after the evaluator returns, from the collector/evaluator job, **never inside an agent request or the gateway**.
- **Fail-safe:** if `notify()` returns anything other than `DELIVERED`, keep the assessment, record the delivery state, and add a gap entry. **Do not change the verdict.**
- The **threshold lives in `register.yaml` only.** Evaluators read it; findings carry its version. **Never hard-code thresholds in the control code** (that loses marks).

### 7.1 C16, per-run token spend cap (ACN-COST-001)
- **When:** after a run is complete (all 3 agents + retries reconciled from the **gateway per-call usage records**, the figure of record).
- **Notify if:** the run total is over the cap → `BREACHED`. Also notify when executions are missing or unmatched and the subtotal is under the cap → `INDETERMINATE` with `kind: "monitoring-gap"`.
- `scope_kind: "run"`, `scope_id: <run id / cid>`
- `summary: "10,800 tokens > cap 10,000"`
- `evidence`: assessment path, `gateway:action_id=…` per call (or the gateway log file path plus a line range), `ledger:cid=…`, `register:register.yaml@<ver>`

### 7.2 C9, drift and performance (AIA-ARC-006)
- **When:** each closed UTC hour window (CloudWatch `AWS/Bedrock-AgentCore` Latency Average 3600 s / Errors Sum, per runtime).
- **Notify for every crossing window** → `BREACHED`, `scope_kind: "window"`, `scope_id: "2026-10-05T09"` (+ the runtime in `summary`). **This applies even if the overall exception allowance still passes.** The masterclass requires an alert to a named human for each crossing.
- **Missing data:** a missing window → `INDETERMINATE`, `kind: "monitoring-gap"`. **Never treat a missing window as healthy.**
- `evidence`: assessment path, `cloudwatch:metric=AWS/Bedrock-AgentCore/Latency;runtime=<name>;start=…;period=3600`, `baseline:<baseline file@version>`

### 7.3 C7, automatic event recording (AIA-LOG-001)
- **When:** per run, after expected events (independent expected population) are reconciled against the captured records.
- **Notify if:** coverage is below target, or the violating gap fraction is above the allowance → `BREACHED` (one finding per run; list the missing event ids in `evidence`).
- `scope_kind: "run"`
- `evidence`: assessment path, `ledger:cid=…`, `expected:<expected-events file>`, `missing:<event id>` …

### 7.4 ESC, agent escalation to a human (S3 "restricted-change" and any agent `escalate`)
- **When:** the ledger shows `disposition=escalate` for a cid. Read it the way `escalate-to-incident.py` does: parse `/records?cid=` JSONL and regex `disposition=([\w-]+)` in `detail`.
- Finding: `control_ref: "ESC"`, `control_id: "AGENT-ESCALATION"`, `threshold_version: "policy-v1"` (or the Cedar policy version), `scope_kind: "escalation"`, `scope_id: <cid>`, `verdict: "ESCALATED"`, `kind: "escalation"`
- `evidence`: `ledger:cid=<cid>` plus one `ledger:record=<step>/<actor>/<phase>` per record (the work notes then carry the chain, like the workshop's `escalate-to-incident.py`)
- This is the masterclass **"human approval queue"** enforcement point. Show it in the architecture as EP #2, using the same Finding contract with nothing rewritten (**Axis 3 bonus**).

### 7.5 Minimal glue (drop into your evaluator runner)
```python
import json, pathlib
from prooflab.servicenow.client import ServiceNowClient
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.servicenow.notifier import notify

NOTIFY_VERDICTS = {"BREACHED", "ESCALATED"}

def publish(assessment: dict) -> None:
    """assessment = your evaluator output (already written to evidence/assessments/...)."""
    finding = finding_from_dict(assessment["finding"])   # evaluator builds this dict per §6
    path = pathlib.Path("evidence/findings") / (finding.finding_id.replace(":", "_") + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(assessment["finding"], indent=2))
    if finding.verdict in NOTIFY_VERDICTS or finding.kind == "monitoring-gap":
        result = notify(finding, ServiceNowClient.from_env(),
                        DeliveryLog("evidence/servicenow/delivery-log.jsonl"),
                        owner_user="annapurna@invences.com")
        if result.state != "DELIVERED":
            print(f"GAP: {finding.finding_id} delivery={result.state} reason={result.reason}")
```

### 7.6 "Continuous" mode (bonus)
- Run collectors and evaluators on a loop (for example every 5 min for C16/C7 after each run, and hourly at HH:05 for C9).
- Call `publish()` for each new assessment. Findings reach the owner within minutes, while agents keep running.
- Label this honestly in the architecture: **"near-real-time post-run evaluation"**, unless you also build a genuine inline `evaluate()` admission at an enforcement point (the C16 inline bonus).
- **Respect the account ceiling:** 100 requests/min and 2.5M tokens/h across the whole account, including helper and investigator calls.

---

## 8. Evidence: generation, storage, integrity, presentation

### 8.1 What makes a record "evidence" (masterclass)
Every record must answer:
- **what happened**
- **which control**
- **which threshold version**
- **which run**
- **who acted**
- **when**
- **where it came from**

A seal or signature is **out of scope**: do not build signing, hash chains or Merkle trees. **"The stranger test":** a judge must be able to check it **without us in the room**.

### 8.2 Record shapes and reference prefixes
**Assessment record** (one per control × scope, written by your evaluator, never edited; a correction gets a new revision file):
```json
{
  "assessment_id": "C16:G-FM-v1:run:FM-B:r1",
  "control_ref": "C16", "control_id": "ACN-COST-001",
  "threshold_version": "G-FM-v1", "threshold": {"cap_tokens": 10000, "allowed_over_cap_runs": 0},
  "owner": "annapurna@invences.com",
  "scope": {"kind": "run", "id": "FM-B", "start": "...Z", "end": "...Z"},
  "measured": {"total_tokens": 10800, "calls": 7, "retries": 1},
  "expected_population": {"source": "gateway usage records", "count": 7, "missing": 0},
  "verdict": "BREACHED",
  "formula": "sum(input+output tokens of accepted executions) <= cap_tokens",
  "evidence_refs": ["gateway:action_id=...", "ledger:cid=...", "raw:evidence/raw/gateway/2026-10-05T14.jsonl#L10-L16"],
  "actors": ["customer_experience_agent", "it_resolution_agent", "network_resolution_agent"],
  "evaluator": {"name": "c16_eval", "version": "git:<sha>"},
  "evaluated_at": "2026-10-05T14:03:12Z",
  "gaps": [],
  "finding": { "...": "the §6 Finding, or null if SATISFIED" }
}
```
**Reference prefixes** (use them consistently so the query tool can resolve them):

| Prefix | Meaning |
|---|---|
| `raw:<path>#L…` | Line range in a raw capture file |
| `gateway:action_id=` | One gateway call |
| `ledger:cid=` / `ledger:record=` | Audit-store chain or record |
| `cloudwatch:` | Metric query identity (namespace, metric, dimensions, start, period) |
| `cr:<kind>/<name>@<generation>` | MoDaaS CR status, approvals |
| `assessment:` | An assessment file |
| `register:` | The register file and version |
| `servicenow:INC…` | The incident |
| `aict:` | Control Tower asset or trace |

### 8.3 Storage layout (repo, mirrored to S3)
```
evidence/
  README.md                       # how to read this pack (1 page, for a stranger)
  MANIFEST.json                   # every file: path, sha256, bytes, source, captured_at (see 8.5)
  register/register.yaml          # frozen, dated thresholds + owners (copy of ~/starter/register.yaml)
  raw/                            # untouched source captures (never edited)
    gateway/  ledger/  cloudwatch/  cr-status/  pdp/
  assessments/C7/ C9/ C16/ ESC/   # one JSON per control x scope (+ revisions r2, r3 ...)
  findings/                       # the Finding JSON files sent to ServiceNow
  servicenow/
    delivery-log.jsonl            # INTENT→SENT→DELIVERED→RESPONDED/NO_RESPONSE_OBSERVED (append-only)
    incidents/INC*.json           # `export` output: the incident as ServiceNow stores it + work notes
    aict/                         # Control Tower proof (Arth): cloudtrail-assumerole.json,
                                  # discovered-assets.json, screenshots *.png with timestamps
  cases/                          # rendered case per named run: C16_FM-B.md / .html (presentation)
  run-ids.txt                     # the named PASSING and BREACHING runs (written BEFORE judging)
  gap-list.md                     # what we could not close and why (scored!)
  architecture.md                 # the one-page actual architecture
```

### 8.4 Per finding, before judging
```bash
python3 -m prooflab.servicenow check  --finding evidence/findings/<f>.json --cutoff <judging start, UTC>
python3 -m prooflab.servicenow export --finding evidence/findings/<f>.json   # -> evidence/servicenow/incidents/
```
- `check` writes `RESPONDED` (with actor and time) or `NO_RESPONSE_OBSERVED` (after the cutoff). Both are valid evidence; a reply is not required.
- **A finding is "closed" only by a linked passing re-test** (a new assessment with `SATISFIED` on the same control/scope type, after the fix). **Never close it because someone replied "done".** Record the re-test assessment id in the incident's work notes and in `gap-list.md` if no re-test happened.

### 8.5 Integrity (lightweight, allowed)
- Raw captures are **never edited**. Corrections get new files.
- The delivery log is append-only and fsync'd.
- The supplied **audit-store ledger's own verification** answers "were records altered?"; capture its output into `raw/ledger/`.
- `MANIFEST.json` lists every file's **SHA-256**, size, source and capture time, generated just before submission. It lets a judge check the pack was not changed after hand-in. It is a checksum list, **not** a signing or hash-chain system.
- Note the S3 object **version id / ETag** at upload time (§8.6).

### 8.6 Submit to the judges' bucket (judges read S3, not laptops)
1. Use the starter `~/starter/submit.sh`. Inspect it first: it packages `~/evidence`, `register.yaml`, `gap-list.md` and `run-ids.txt` and uploads to `team-evidence-613052889143`. Make sure `evidence/servicenow/**`, `assessments/**`, `cases/**` and `MANIFEST.json` are included (copy into `~/evidence/` if the script only zips that).
2. **Read back** after upload:
   ```bash
   aws s3 ls s3://team-evidence-613052889143/ --recursive
   aws s3api head-object --bucket team-evidence-613052889143 --key <key>
   ```
   Then download once and compare the SHA-256 with `MANIFEST.json`. Record key, ETag/version and upload time in `evidence/README.md`.
3. Never put presigned URLs into the pack or this repo.

### 8.7 Presentation: the 2-minute judge question
The judge names a control and a run or window. Our tool must return everything on **one screen** without anyone narrating. `query --control C16 --run FM-B` should print:
```
C16 ACN-COST-001 | rule G-FM-v1 (dated 2026-10-05, owner Sree Annapurna Rallabandi): total tokens <= 10,000/run, 0 over-cap runs allowed
Scope: run FM-B  2026-10-05T13:58:02Z..14:02:47Z   expected calls 7, captured 7, missing 0
Measured: 10,800 (input 8,950 + output 1,850)  ->  BREACHED by 800
Records: gateway action_ids [6f1c.., ...]  ledger cid fault-17888...  raw: evidence/raw/gateway/...#L10-16
Who acted: customer_experience_agent -> it_resolution_agent -> network_resolution_agent (AgentCore runtimes, approved CRs @gen N)
Human loop: ServiceNow INC00xxxxx assigned to Sree Annapurna Rallabandi, DELIVERED 14:03:20Z (readback ok)
            response: NO_RESPONSE_OBSERVED by 2026-10-06T14:00Z   [evidence/servicenow/incidents/INC00xxxxx.json]
AICT: runtimes discovered by connection "iFabric Hackathon 2026" (import 2026-10-05T14:09Z)
Gaps: none for this scope
```
To produce the "Human loop" line **offline** (no ServiceNow call during judging), read the delivery log:
```python
from prooflab.servicenow.delivery_log import DeliveryLog
hist = DeliveryLog("evidence/servicenow/delivery-log.jsonl").history(finding_id)
delivery = next((e for e in reversed(hist) if e["state"] in ("DELIVERED", "FAILED", "UNVERIFIED", "OUTCOME_UNKNOWN")), None)
response = next((e for e in reversed(hist) if e["state"] in ("RESPONDED", "NO_RESPONSE_OBSERVED", "AWAITING_RESPONSE", "RESPONSE_UNKNOWN")), None)
```
**Six auditor questions → where the answer lives:**

| Question | Evidence |
|---|---|
| Who acted? | `actors` in the assessment; gateway caller identity; AgentCore runtime (also visible in AICT) |
| What did it touch? | Gateway call records (model alias, tool); ledger chain |
| Authorized? | Cedar/PDP decision lines (`raw/pdp`), guardrail result, approved CR status |
| Who approved? | CR `.status.governance.approvals` (attestation, subject, time); threshold register owner; incident owner and response |
| Integrity? | Ledger verification output, raw captures never edited, MANIFEST SHA-256, S3 version id |
| Reconstruct? | Ledger `/records?cid=` chain + spans by trace id + gateway lines, in order by time (render it in `cases/`) |

---

## 9. ServiceNow Control Tower and Level 3 (what you need to know)

| What | Who and when |
|---|---|
| **AICT (Level 2) is already connected.** Your new AgentCore runtimes appear in AICT within ~20 min (15-min import + ~4-min run). | No action, as long as you **name new agents `ifabric_…`** |
| AICT does **not** discover EKS pods, MCP servers, MoDaaS guardrails, or which ModelConfig served a call | Already in the gap list; don't claim them |
| Final AICT screenshots: Inventory → agent Details, Insights → Monitor session/trace for the **named runs** | Arth, after the named runs exist |
| The **Assurance Agent** (Nemotron via `modaas-agw`, AgentCore runtime `ifabric_assurance_agent`) that analyzes our incidents and writes one note back. **Level 3**; see `evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md` (formerly handoff 2) | Teammate deploys; Arth supports |
| CloudTrail `AssumeRole` of `SgcAictReadOnlyAccessRole` as connector proof | Arth (still pending) |

---

## 10. Rules and pitfalls (don't lose points)

**Must do:**
- Freeze and date `register.yaml` **before** any assessed run, with **owner `annapurna@invences.com`** for C7/C9/C16. **Never move a threshold after seeing results.**
- Name **one passing and one breaching** run per control in `run-ids.txt` **before** judging.
- Notify every C9 crossing and every escalation, not just aggregate failures.
- Use **Nemotron only** (via the MoDaaS governed alias) for our own agents. This includes the Assurance Agent (facilitator ruling 2026-10-05); the earlier ServiceNow-LLM prototype is inactive.
- Tag everything `ifabric`. Touch **only** incidents created by `ifabric.integration`.
- Write gaps down (`gap-list.md`). **"One honest failure scores better than everything green."**

**Never:**
- Put ServiceNow calls in the agent or gateway request path.
- Store thresholds inside control code.
- Mark a finding closed without a passing re-test.
- Print, commit or screenshot the client secret, tokens, IdeUrl/CockpitUrl or presigned URLs.
- Create or modify ServiceNow users, OAuth apps or system properties (ask Arth).
- Change AICT risk frameworks or other teams' agents/connections.
- Build signing, hash chains or a slide deck.

---

## 11. Gap-list entries already known (copy into `gap-list.md`)
1. **AICT discovery scope:** discovers AgentCore runtimes, Bedrock agents and SageMaker models only; **not** EKS pods, MCP servers, MoDaaS guardrails, or per-ModelConfig call attribution (all calls go through one gateway IAM principal).
2. **AICT freshness:** inventory refreshes every 15 min (+~4 min run time); "Execute Now" forces a refresh.
3. **Shared ServiceNow instance:** identical reference-agent names across teams; ours are identified by our connection's import timestamps and the `ifabric` prefix.
4. **Script authentication:** Basic auth rejected (401) for participant and integration users; switched to OAuth client credentials (instance property enabled by us, logged here for transparency).
5. **Human response:** a reply is not required; silence is recorded as `NO_RESPONSE_OBSERVED` only after the stated cutoff; unreadable history is `RESPONSE_UNKNOWN`.
6. **Delivery semantics:** `DELIVERED` means read back with the right correlation id and assignee. It does not prove the human read it; only a note or status change proves engagement.
7. **No cryptographic sealing** (out of scope); integrity rests on the ledger verification, never-edited raw captures, the MANIFEST SHA-256 and S3 versioning.
8. **Note-level response detail:** the `itil` integration user cannot see `sys_journal_field` rows (ACL returns 0 rows, no error). Owner responses are therefore detected from the incident's `sys_updated_by`/`sys_updated_on` (`at_basis: "last_update"`, verified live on INC0010231). `export` also stores the notes as display text (`notes_display`). Note authorship is shown there as display names.

---

## 12. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `CERTIFICATE_VERIFY_FAILED` | Mac python.org build only: `export SSL_CERT_FILE=$(python3 -m certifi)`. Not needed in the IDE |
| `OAuth token not issued (server_error: access_denied)` | Wrong ID/secret, OAuth app inactive, or the client-credentials property was turned off; tell Arth |
| `set environment variables: SNOW_CLIENT_SECRET` | You opened a new terminal; repeat §5.3 |
| `FAILED owner_lookup` | `SNOW_OWNER_USER` is wrong or that user is inactive |
| `OUTCOME_UNKNOWN no_record_found_yet` | ServiceNow did not confirm; rerun the same `notify` later (safe, idempotent) |
| `UNVERIFIED readback_failed` | Incident created but readback failed; rerun `notify` (it reuses and re-verifies) |
| Too many incidents for C9 | Expected: one per crossing window. Do not merge windows |

---

## 13. Acceptance checklist (definition of done for the integration)
- [ ] `prooflab/` in your repo; `python3 -m pytest prooflab/tests -q` → 46 passed in the IDE
- [ ] `selftest` OK in the IDE terminal
- [ ] `register.yaml` frozen and dated, owner = `annapurna@invences.com` for all controls, **before** assessed runs
- [ ] Each evaluator writes an assessment (§8.2) for **every** scope, passing or breaching
- [ ] Each BREACHED / ESCALATED / monitoring-gap creates **exactly one** incident (re-run → `reused: true`)
- [ ] One **breaching named run** per completed control has a DELIVERED incident; `check` and `export` done
- [ ] S3 escalation path proven once (the S3 scenario → `ESC` incident with the ledger chain in its work notes)
- [ ] Query tool shows verdict + records + human-loop line in **< 2 min**, offline
- [ ] `MANIFEST.json` generated, submitted to S3, readback verified
- [ ] `gap-list.md` includes §11 + your own gaps; `architecture.md` shows the ServiceNow EP and AICT
- [ ] **Rehearsed twice** on the two named runs

---

## 14. Who does what next

| Owner | Task |
|---|---|
| **Teammate** | §5 merge + §5.4 verify; §7 wiring for each control you complete; assessments + findings per §6/§8; query tool line (§8.7); submit + readback |
| **Arth (+ Claude)** | Provide `.tgz` + credentials; close test INC0010231; AICT final screenshots, CloudTrail proof and discovered-assets export into `evidence/servicenow/aict/`; Assurance Agent support (L3, `evidence-console-plan/08-SERVICENOW-AND-ASSURANCE-AGENT.md`); courtesy note to facilitators; review the evidence pack against §13 |
| **Sree (owner)** | Approve thresholds before assessed runs (note on the register approval record or incident); optionally acknowledge incidents (a note counts as a response) |

---

**Strategy, scoring and best practices:** see `HACKATHON_WINNING_PLAYBOOK.md` (same package).

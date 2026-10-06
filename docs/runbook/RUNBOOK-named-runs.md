# RUNBOOK: v1 freeze → T2 → named runs N1–N9 → pack → submit → root publish

**For:** the ops lane, after the captain approves v1's values (Hold-3). **Written:** 2026-10-06, offline, against repo main `d57c868`.
**Scope:** IMPLEMENTATION-PLAN §5.2 rows 16–26 as re-ordered by the captain at 11:00Z and 11:05Z (all nine named runs, core four first; T2 straight after the v1 freeze). ARCH §3.8 (Finding contract, guards a/b), §5.5 (named runs).
**Proof that the offline part works:** `bash ~/firstmate-homes/TrustworthyAI/ops-lane/runbook/dryrun.sh` gives **64 PASS, 0 FAIL, 10 other** (table at the end; the full output is in `dryrun-table.txt`). Re-run it after any repo merge, before step 1.

## 0. Conventions (read once)

```bash
REPO=~/firstmate-homes/TrustworthyAI/TrustworthyAI-iFabric
RB=~/firstmate-homes/TrustworthyAI/ops-lane/runbook ; T=$RB/tools
L=~/firstmate-homes/TrustworthyAI/ops-lane/nr        # this lane's evidence root (outside the repo)
HK=~/firstmate-homes/TrustworthyAI/workshop-local/bin/hk
CREDS=$(cat ~/firstmate-homes/TrustworthyAI/ops-lane/creds-expiry.txt)   # bare UTC ISO, e.g. 2026-10-06T13:52:47Z
PROD_LOG=$L/servicenow/delivery-log.jsonl                     # THE production delivery log: absolute, one for N2/N4/N6/N8
APPR_LOG=$L/register/approval/delivery-log.jsonl             # T2's own log (must differ from PROD_LOG)
TEST_LOG=$L/servicenow/wiring-tests/delivery-log.jsonl        # guard (a): the ONLY place --dry-run may log
TEST_APPR=$L/servicenow/wiring-tests/approval-delivery-log.jsonl
LEDGER=http://127.0.0.1:8001/api/v1/namespaces/components/services/audit-store:8080/proxy
```
- **Every AWS / kubectl command runs as `$HK '<the whole command as ONE argument>'`** (b2e: hk takes one argument). `$TEAM_EVIDENCE_BUCKET` comes from hk's environment; never take it from `b1-bucket.json` (masked; b3's first T1 failed on it).
- **ServiceNow steps** (`humanloop notify/check/export/analyze`, `pack root` without `--dry-run`) run in the lane's own shell where the lane has sourced the ServiceNow environment, with `SNOW_OWNER_USER` set explicitly (config refuses without it). This runbook never reads `~/.prooflab-snow.env`.
- Always `export PROOFLAB_DELIVERY_LOG=$PROD_LOG PROOFLAB_APPROVAL_DELIVERY_LOG=$APPR_LOG` before a production notify. **Never `--dry-run` with these two set** (guard a refuses it, exit 2). **Always explicit `--finding <file>`, never `--findings-dir`** on production.
- **Selftest before each notify batch** is built in: `humanloop notify` runs Arth's read-only selftest first and logs nothing if it fails (exit 1).
- Every step appends one row to `~/firstmate-homes/TrustworthyAI/ops-lane/live-lane-log.jsonl` (row id `NR-<step>`), as b3/b6b did.
- **Budget guard before EVERY run** (step B): rolling 60 min ≤ 1.0M gateway tokens; at most 2 observe S2-class runs in any rolling hour; ≥ 2 min between run end and next start; OC-34 ≤ 30 model requests in any 60 s window (b3's stop trigger).
- **Stop conditions that apply everywhere:** any exit code not listed as expected; a secret value in any file (exact-value scan); creds < 60 min to expiry (`$CREDS`); an EP-0 `block`; anything touching an object not named `ifabric-*` / a key not under `ifabric/`.
- Placeholders are only for values not yet known: `<V1_DRAFT_REG>`, `<V1_DRAFT_RISKS>` (the captain-approved draft files), `<SUPERSEDED>` (= `ops-lane/b2e/register/versions/v0-pilot3.yaml` unless a later pilot version was frozen), `<CID_Nx>`, `<START_Nx>/<END_Nx>` (UTC ISO from the run output), `<INC_…>`, `<T2_SYS_ID>`, `<ZIP>`, `<ZIP_VERSION_ID>`, `<RUNTIME_ID_role>`.

### Lane tools this runbook adds (all in `$T`, all exercised by `dryrun.sh`)
| Tool | Why it exists |
|---|---|
| `mkpatch.py <frozen reg> <observe\|enforce> <patch.json> <pinfile.json>` | b3's `mkpatch.py` hard-codes `observe`. This one makes the 4-key merge patch for EITHER mode and the run's `--pin-file`; refuses unless `IFABRIC_PIN_JSON` is byte-equal to `pins/<v>-<mode>.json` |
| `rails_patch.py <observe\|enforce> <out>` | one-key `IFABRIC_RAILS_MODE` patch (ADV-H-01 only; EP-0 counts it as a pin key) |
| `collect_spans.py <snap> <cid> <start> <end>` | `prooflab collect` has **no pull verb** (it only lists surfaces). Glue over the merged `aws_spans.pull` → `<snap>/raw/aws-spans/<cid>/spans.jsonl` |
| `t1.py <out.json> <file>=<ifabric/key> …` | b3's write-once uploader, bucket from env, exit ≠ 0 on any mismatch |
| `drive.py`, `insights.py` | copies of the b3 runner seam and Logs-Insights helper (the originals live in a session scratchpad under /private/tmp and may vanish) |
| `fakeaws.py`, `fakesnow.py` | dry-run only; never on a live PATH |
Still taken from earlier lanes: `ops-lane/b3/patch_one.py` (dry-run=server → patch → READY → filtered facts), `ops-lane/b3/status.py`, `ops-lane/b3/echo_check.py`, `ops-lane/b2e/specs.py` (EP-0 versions file), `ops-lane/b3/measure.py` (pilot measurements; **its paths point into the old scratchpad**, see M3).

---

## Step A. Pre-flight (once, before step 1) — R, pre

1. `bash $RB/dryrun.sh` → exit 0, `TOTAL: … 0 FAIL`. **Stop** on any FAIL.
2. `$HK 'aws sts get-caller-identity --query Arn --output text'` → our role. Minutes to `$CREDS` ≥ 90, else the refresh first (row 4a).
3. `mkdir -p $L/{register,servicenow/wiring-tests,register/approval,runs,snap,patches,t1,pack}`
4. Regenerate the runtime map (b2e re-created the trio: the old ids in `b3/echo_check.py` defaults and the scratchpad `runtimes.json` are **stale**):
   `$HK 'aws bedrock-agentcore-control list-agent-runtimes --output json --query "agentRuntimes[?starts_with(agentRuntimeName,'"'"'ifabric'"'"')].{n:agentRuntimeName,id:agentRuntimeId,arn:agentRuntimeArn,s:status,v:agentRuntimeVersion}"' > $L/runtimes-list.json`
   then write `$L/runtimes.json` = `{"ifabric-customer": "<arn>", "ifabric-it": "<arn>", "ifabric-network": "<arn>"}` (mode 600; holds the account id). **Done:** 3 READY ids, none of `Lv3KGiEZAC / 0mXIRT4cRL / gojN2l6yqB`.
5. Start the ledger proxy (kept for the whole session; stopped in step 13): `$HK 'kubectl proxy --port 8001 --address 127.0.0.1' &`. **Done:** `curl -s -o /dev/null -w '%{http_code}' $LEDGER/` answers.

## Step B. The budget guard (before EVERY run) — R, pre
```bash
NOW=$(date -u +%s); $HK "python3 $T/insights.py aws/spans $((NOW-3600)) $NOW \"filter attributes.listener = 'llm' | stats sum(attributes.gen_ai.usage.input_tokens) as tin, sum(attributes.gen_ai.usage.output_tokens) as tout\"" > $L/runs/<label>-headroom.json
```
TOK = tin + tout. **Go** only if TOK + the run's bound ≤ 1,000,000, the S2-observe count in the last 60 min < 2 (for N2), and the previous run ended ≥ 2 min ago. Pass TOK as `--tokens-last-hour`. **Stop** otherwise (wait; never trim the bound).

## Step C. The run command (used by every N-step) — M
```bash
cd $REPO && $HK "python3 $T/drive.py $L/runs/<label>-response --scenario <S1|S2|S3> --mode <enforce|observe> --family run --provenance LIVE_SUBJECT \
  --scenario-file $REPO/register/scenarios/<S>.json --pin-file $L/patches/pinfile-v1-<mode>.json --versions-file $L/patches/versions-<label>.json \
  --echoed-pins $L/patches/echo-<label>-echoed.json --tokens-last-hour <TOK> --creds-expiry $CREDS --runtimes-file $L/runtimes.json \
  --run-dir $L/runs/ifabric-runs --ledger-url $LEDGER --ledger-secret components/audit-write-token/token [<extra>]" > $L/runs/<label>-orchestrator-output.txt 2>&1; echo "exit $?" >> $L/runs/<label>-orchestrator-output.txt
```
- **Rehearse first, same argv + `--dry-run`** (no call of any kind): `python3 -m prooflab run --dry-run …` → exit 0, envelope `mode`, `provenance LIVE_SUBJECT`, `pin_sha256` set, `fault` where declared (dry-run rows 24–33).
- `--provenance LIVE_SUBJECT` is explicit on every named run (ARCH §5.5); with a `--fault` the default would be FAULT_INJECTION. The fault is still carried in the envelope (row 27).
- **Expected:** exit 0; preflight lines `identity ok`, `ep0.<agent> ok verdict=ALLOW` ×3, `pin.echo ok <pin12>`; the CID printed (`ifabric-run-<epoch>-<hex>`). Save the CID to `$L/runs/<label>.cid`.
- **Versions file:** after each patch, regenerate: `$HK 'kubectl get agentconfig -n components -o json' | python3 ~/firstmate-homes/TrustworthyAI/ops-lane/b2e/specs.py live ~/firstmate-homes/TrustworthyAI/ops-lane/b2e/approved-specs.json $L/patches/versions-<label>.json` → each agent `pin-only` (or `unchanged`), basis `approved-spec`. **Stop** on `block`.
- **Echo:** `$HK "python3 ~/firstmate-homes/TrustworthyAI/ops-lane/b3/echo_check.py <patch time ISO> $L/patches/echo-<label>.json <RUNTIME_ID_customer> <RUNTIME_ID_it> <RUNTIME_ID_network>"` (ALWAYS pass the new ids). **Done:** every runtime's last start-up line echoes the new pin sha.
- **Stop (live):** exit ≠ 0; any EP-0 `block`; OC-34 > 30/min in the run; an unexpected halt on a PASS run.

## Step D. Post-run capture (every N-step, ≥ 60 s after the run's end) — R
```bash
SNAP=$L/snap
$HK "python3 $T/collect_spans.py $SNAP <CID> <START> <END>"                       # raw/aws-spans/<CID>/spans.jsonl
$HK "cd $REPO && python3 -m prooflab refresh --snapshot $SNAP --run-ids $L/run-ids.txt --provenance $L/provenance.json \
     --join-tolerance-s 5 --ledger-url $LEDGER --token-env <NAME_OF_THE_LEDGER_TOKEN_VAR> --pull-ledger --ingest"
```
- Append the CID to `$L/run-ids.txt` (one per line) and `{"<CID>": "LIVE_SUBJECT"}` to `$L/provenance.json` (ADV runs: never in run-ids.txt).
- **Expected:** `collect_spans.py` prints `rows: N>0`; refresh exit 0, `"rejects": 0`, `"unjoined": 0`. **Stop** on rows 0 (pull again at +120 s once, then gap row).
- The earliest formal spans pull is +60 s (b6b's +15 s read was a slip).

---

## Phase 1: v1, T1, T2, pin

### Step 1. Freeze v1 (laptop) — act (Hold-3: the captain approved the values)
```bash
cd $REPO && python3 -m prooflab registry freeze --version v1 --register <V1_DRAFT_REG> --risks <V1_DRAFT_RISKS> --out $L/register --supersedes <SUPERSEDED>
ls $L/register/pins/   # MUST show v1-enforce.json AND v1-observe.json
```
- **Pre-checks on the draft** (refuse to freeze otherwise): `inline_modes: enforce,observe` (else no enforce pin, rows 16/21 have nothing to apply; the committed `register/register.yaml` still says `observe` only); C7 `declared_faults` contains `suppress-record:ifabric-it:tool.call:1`; `declared_conditions` carries a real sha (main still has `conflicting-context:sha256=PENDING-CONDITION-TEXT`); C7 limits `coverage_min_pct`, `gap_max_ms`, `violating_gap_share_max_pct` are in the text (else step 11 must pass `--limit`, see M6); `tool_no_evidence_limit: 3` kept.
- **Expected:** exit 0; prints both sha256s; writes `versions/v1.{yaml,sha256}`, `v1.risks.{yaml,sha256}`, `pins/v1-{enforce,observe}.{json,sha256}`. A second freeze is refused (dry-run row 6).
- **Evidence:** the four files + stdout → `$L/register/freeze-v1.txt`.
- **Stop:** freeze refuses (`--supersedes` per-control version-bump check), or only one pin.

### Step 2. T1: write-once upload + the IDE version listing — W (S3), pre
```bash
$HK "python3 $T/t1.py $L/t1/t1-v1.json $L/register/versions/v1.yaml=ifabric/register/v1.yaml $L/register/versions/v1.risks.yaml=ifabric/register/v1.risks.yaml \
     $REPO/register/experiments/rules.json=ifabric/register/experiments/v1.rules.json"
```
- **Expected:** exit 0; one line per key with `"match": true`, a VersionId, LastModified. A repeat is refused with PreconditionFailed (row 9). The person at the IDE runs `list-object-versions --prefix ifabric/register/v1` (act) and confirms one version each.
- **Evidence:** `$L/t1/t1-v1.json` (account id masked). **T1 = LastModified of `ifabric/register/v1.yaml`** — keep it: `T1AT`.
- **Stop:** any `match: false` or put error.

### Step 3. T2: the approval Finding → ServiceNow → the captain's APPROVED note — W (ServiceNow) + act
```bash
cd $REPO
python3 -m prooflab registry approval-finding --version v1 --register $L/register/versions/v1.yaml --risks $L/register/versions/v1.risks.yaml \
   --out $L/register/approval --detected-at <T1AT>
AF=$L/register/approval/approval-finding.json
# 3a. TEST log first (the build prompt's "a TEST log before the first real one"): moves here because T2 is now the FIRST real notify
PROOFLAB_DELIVERY_LOG=$TEST_LOG PROOFLAB_APPROVAL_DELIVERY_LOG=$TEST_APPR python3 -m prooflab humanloop notify --dry-run --finding $AF
# 3b. the real one
export PROOFLAB_DELIVERY_LOG=$PROD_LOG PROOFLAB_APPROVAL_DELIVERY_LOG=$APPR_LOG
python3 -m prooflab humanloop notify --finding $AF | tee $L/register/approval/notify.json
```
- **Expected:** 3a exit 0, `"state": "DRY_RUN"` (wiring-tests log only; the dry run DOES contact ServiceNow: selftest + lookups, so it needs the env). 3b exit 0, `"action": "notified"`, `"state": "DELIVERED"`, an `INC…` number; the line is in `$APPR_LOG`, **not** `$PROD_LOG` (row 15).
- **The sys_id** (needed in step 13): `python3 -c "import json;print([json.loads(l) for l in open('$APPR_LOG') if l.strip() and json.loads(l).get('state')=='DELIVERED'][-1]['sys_id'])" > $L/register/approval/t2-sys-id.txt` (row 16).
- **Who counts:** `check_response` records RESPONDED only for a note (or update) by **`SNOW_OWNER_USER`** (notifier.py l.205/212). The APPROVED note must be posted from that account: either the captain's account is `SNOW_OWNER_USER` for this check, or the owner posts it on the captain's instruction; a note from any other account is listed as "others" and never ends the wait.
- **Humans:** Arth adds his note; **the captain** (as above) adds exactly the text printed by
  `python3 -c "import sys;sys.path.insert(0,'$REPO');from prooflab.registry.approval_finding import approval_note_text as a;from prooflab.contract.register import register_sha256 as s;print(a('v1',s(open('$L/register/versions/v1.yaml','rb').read()),s(open('$L/register/versions/v1.risks.yaml','rb').read())))"`
  (= `APPROVED threshold register v1, sha256 <12>; risks sha256 <12>`).
- Then: `python3 -m prooflab humanloop check --finding $AF --cutoff <now+15min UTC> --once` → `RESPONDED` (row 17); `python3 -m prooflab humanloop export --finding $AF --out $L/servicenow/export` → `INC….json` (row 18).
- **Evidence:** `approval-finding.json`, `notify.json`, `$APPR_LOG`, `t2-sys-id.txt`, the export.
- **Stop:** selftest fails (exit 1: nothing logged, fix the env); state ≠ DELIVERED (UNVERIFIED/FAILED: do not re-send; a re-run reuses the incident by finding id); no APPROVED note by the cutoff → T2 is a gap row, runs may continue (T1 dates; T2 corroborates).

### Step 4. Pin v1 (enforce) on all three — W (cluster), Hold-3
```bash
python3 $T/mkpatch.py $L/register/versions/v1.yaml enforce $L/patches/pin-v1-enforce.patch.json $L/patches/pinfile-v1-enforce.json
python3 $T/mkpatch.py $L/register/versions/v1.yaml observe $L/patches/pin-v1-observe.patch.json $L/patches/pinfile-v1-observe.json
for a in ifabric-customer ifabric-it ifabric-network; do
  $HK "python3 ~/firstmate-homes/TrustworthyAI/ops-lane/b3/patch_one.py $a $L/patches/pin-v1-enforce.patch.json <PIN_SHA_enforce> v1 $L/patches/pin-v1-enforce-$a.json"
done
```
- `mkpatch.py` **Expected:** `"pin_json_equals_pin_file": true`, prints `pin_sha256` (rows 19–20). Apply **one 4-key patch per agent, never partial** (a partial patch makes every invocation `startup-failed`).
- `patch_one.py` **Expected:** exit 0 per agent; dry run first (pin, version new; env names, digest, dependsOn unchanged); READY with runtime version +1 within 300 s; approvals unchanged; `pin_ok: true`. Then the versions file + echo of step C (label `v1-enforce`).
- **Stop:** exit 2/3 (dry run refused or mismatched) or 4 (not READY / approvals changed / pin wrong): stop, do not patch the next agent.

---

## Phase 2: the core four (one PASS and one BREACH per control)

### Step 5. N1: S1, enforce — the PASS for C16, C7 and C9 — M, pre
Step B → Step C with `<label>=N1 --scenario S1 --mode enforce` (bound default) → Step D.
- **Done:** exit 0, not halted, kit grade disposition recorded; C16 within cap; every tool call has a gateway `tools/call` span (C7, PR-39 rule).
- **Stop:** halted (a PASS run must not hit the cap) → captain.

### Step 6. Mode → observe (all three) — W, Hold-3
Same loop as step 4 with `pin-v1-observe.patch.json` and `<PIN_SHA_observe>`. Then versions file + echo (`<label>=v1-observe`). Record in the live-lane log as "EP setting: observe (declared, for the C16 BREACH run)".

### Step 7. N2: S2, observe — C16 BREACH → assess → finding → notify — M + W, Hold-3
Step B (**S2-observe count < 2 in the hour**) → Step C `<label>=N2 --scenario S2 --mode observe` (+ `--condition conflicting-context` only if the captain chose lever (b)) → Step D. Then:
```bash
cd $REPO
python3 -m prooflab assess --snapshot $L/snap --register $L/register/versions/v1.yaml     # the full assess (tested form); rc 1 normal
SNOW_OWNER_USER=<owner> python3 -m prooflab humanloop findings --snapshot $L/snap --register $L/register/versions/v1.yaml
# -> $L/snap/findings/C16-<CID_N2>.json
python3 -m prooflab humanloop notify --finding $L/snap/findings/C16-<CID_N2>.json | tee $L/servicenow/notify-N2.json
```
- `assess` **exit 1 is normal** (a BREACHED verdict exists); exit 2 = not assessed → stop. `humanloop findings` is a hidden verb (not in `--help`) and keeps an existing file (stable finding id).
- **Done:** `requirement_verdict: BREACHED`; finding summary starts "deficiency: operation (declared observe setting)"; notify `DELIVERED`, incident `<INC_N2>`.
- **Stop:** C16 not BREACHED → no notify; captain decides (no lever: "built properly, no breach demonstrated").

### Step 8. Mode → enforce (the owner's remediation, recorded) — W, Hold-3
Step 4's loop again (enforce patch). Versions file + echo (`v1-enforce2`).

### Step 9. N4: S1 + suppress-record — C7 BREACH → assess → finding → notify — M + W, pre
Step C `<label>=N4 --scenario S1 --mode enforce --fault suppress-record:ifabric-it:tool.call:1` (+ `--provenance LIVE_SUBJECT`, already in step C) → Step D →
```bash
python3 -m prooflab assess --snapshot $L/snap --register $L/register/versions/v1.yaml [--limit C7:… if v1 lacks them]   # full assess; rc 1 normal
SNOW_OWNER_USER=<owner> python3 -m prooflab humanloop findings --snapshot $L/snap --register $L/register/versions/v1.yaml
python3 -m prooflab humanloop notify --finding $L/snap/findings/C7-<CID_N4>.json | tee $L/servicenow/notify-N4.json
```
- **Done:** C7 BREACHED (coverage < C%), incident `<INC_N4>`. **Stop:** C7 SATISFIED (the fault did not fire: D12 regression) → captain; do not notify.

### Step 10. Assurance analyses on N2's and N4's incidents (between runs only) — W (ServiceNow note) + M, pre
```bash
export IFABRIC_ASSURE_RUNTIME_ARN=<the ifabric_assurance_agent-umVgYIGn47 ARN>
$HK "cd $REPO && python3 -m prooflab humanloop analyze --finding $L/snap/findings/C16-<CID_N2>.json --finding $L/snap/findings/C7-<CID_N4>.json --out $L/servicenow/assurance" | tee $L/servicenow/analyze-1.json
```
(the ServiceNow env must be in the same process: run it where both hk's AWS env and the SN env are set.)
- This is PR-20b's path: `analyze_between_runs` → Arth's `run_assurance_agent` → `invoke-agent-runtime` (`AWS_MAX_ATTEMPTS=1`, 300 s, CID `ifabric-assure-…`) → the note on the REAL incident, logged `ANALYSIS_WRITTEN` in `$PROD_LOG`.
- **Expected:** exit 0; one row per finding, `"action": "analysed"`, `state WRITTEN`. Note Arth's `max_attempts` default (2) applies here: ≤ 2 invokes per finding, ≤ ~4K tokens each (b6b: 890).
- **Witness:** join by action id, never by CID (b6b §7.3); the witness line in the runtime group carries both.
- **Pre-check (hard):** `echo "$IFABRIC_ASSURE_RUNTIME_ARN" | grep -Eq '^arn:aws[a-z-]*:bedrock-agentcore:[a-z0-9-]+:[0-9]{12}:runtime/ifabric_assurance_agent-'` must pass. With no/wrong ARN the dry run showed `action: analysed` ×2 with Arth's UNAVAILABLE outcome recorded against the incident (dry-run row 47): on production that is a ServiceNow write with no analysis. Recovery (row 48): a later `analyze` on the same findings DID invoke again (an UNAVAILABLE outcome does not block a new call), so fix the ARN and re-run once.
- **Stop:** never while a subject run is live (use `--run-active` if one is); `ANALYSIS_FAILED`/`UNAVAILABLE` → record, re-run at most once after fixing the cause.

### Step 11. N8: the declared model swap → warm-up → N8 → C9 BREACH → finding → notify → revert — **PENDING-PR-41**, Hold-4
- **Swap:** `tools/c9_model_swap.py` (PR-41, **not on main d57c868; not on `pr/PR-41-c9` yet**) → `ifabric-it` behind `nemotron-nano-9b`. EP-0 today **blocks** a model change ("model differs from the approved generation"); PR-41's declared-treatment rule is required before N8 can pass preflight.
- **Warm-up:** one S1 invocation (`--family test`, CID `ifabric-test-…`, never in run-ids.txt).
- **N8:** Step C `<label>=N8 --scenario S1 --mode enforce` → Step D (+ the AgentCore metric windows pull, PR-41) → `assess --snapshot … --control C9 --run <CID_N8>` (**PENDING-PR-41**) → findings → `notify --finding $L/snap/findings/C9-<CID_N8>.json`.
- **Revert** at once (PR-41 tool), versions file + echo.

**══ STOP-HERE LINE: core complete (N1 PASS ×3 controls; N2, N4, N8 BREACH + notified). Anything below runs only if the clock allows. ══**

## Phase 3: re-tests and extras (in this order)

| Step | Run | Command differences from step C | After the run | Closes |
|---|---|---|---|---|
| 12a | **N9** (after a warm-up) | S1, enforce | assess C9 (PENDING-PR-41); re-test link note on `<INC_N8>` (see M1) | N8's finding |
| 12b | mode switch → enforce already holds; **N3** | S2, enforce (identical to N2; one more attempt if it doesn't reach the cap; list every attempt in `evidence/named-runs.md`) | assess C16 → SATISFIED with a stop record; re-test link on `<INC_N2>` | N2's finding |
| 12c | **N5** | S1, enforce, no fault | assess C7 → SATISFIED; re-test link on `<INC_N4>` | N4's finding |
| 12d | **N6** | S3, enforce | ESC finding → notify → analysis (**M2: no producer**) | — |
| 12e | **N7** (after a warm-up) | S1, enforce | assess C9 (PENDING-PR-41) | — |
| 12f | ADV-H-01 leg A (optional) | `rails_patch.py observe` on **customer only** → `--only ifabric-customer --condition prompt-attack --family adv --provenance AUTHORIZED_TEST` → `rails_patch.py enforce` | fill `evidence/adversarial/cases/ADV-H-01.md` "Observed" | — |
Each row: step B first; ≥ 2 min spacing; at most 2 S2-observe runs per hour (N3 is enforce). A finding is closed **only** by a passing re-test linked in the incident's work notes; never by an owner reply.

---

## Phase 4: assess all → pack → submit → readback → root publish

### Step 13a. Assess everything + export + mirror — R + W (ServiceNow read)
```bash
cd $REPO
python3 -m prooflab assess --snapshot $L/snap --register $L/register/versions/v1.yaml          # rc 1 normal
python3 -m prooflab humanloop check --finding <each finding> --finding $AF --cutoff <cutoff ≤ the final check> --once
python3 -m prooflab humanloop snapshot --finding <each> --cutoff <cutoff> --out $L/servicenow/cases
python3 -m prooflab humanloop export --finding <each> --finding $AF --out $L/servicenow/export
python3 -m prooflab humanloop mirror --out $L/snap/derived/notifications.jsonl
python3 -m prooflab registry run-ids --run-ids $L/run-ids.txt --experiments $REPO/register/experiments/experiments.jsonl
```
Copy `$L/servicenow` (minus `wiring-tests/`) and `$L/register` into `$L/snap/` (the pack's `--src`). **Stop:** run-ids check fails.

### Step 13b. Pack build (PR-34/40) — local
```bash
mkdir -p $L/pack/workdir && cp $L/register/versions/v1.yaml $L/pack/workdir/register.yaml && cp $L/run-ids.txt $REPO/gap-list.md $L/pack/workdir/
cp $REPO/evidence-templates/README.md $L/pack/README.md   # then FILL every <PLACEHOLDER> by hand
$HK "cd $REPO && python3 -m prooflab pack build --out $L/pack/evidence --src $L/snap --workdir $L/pack/workdir --readme $L/pack/README.md --strict-readme"
python3 -m prooflab pack scan $L/pack/evidence ; python3 $REPO/tools/manifest.py verify $L/pack/evidence
```
- **Expected:** `--strict-readme` refuses while any placeholder is left (the template has 15, row 56); then exit 0 with `answers/` composed and `pack-index.json` projected; `pack scan` "0 hit(s)"; manifest "OK". `register/versions/v1.yaml` and `findings/` are in the pack.
- The exact-value scan needs the values injected (`PROOFLAB_SCAN_VALUES` or `--scan-values-stdin`) — **through hk**; without them `pack scan` exits with "REFUSED: no scan values injected" (dry-run run 1). Safety-submit could not inject them (classifier); then the pre-push scan in 13c is the gate.
- **Stop:** any scan hit; manifest mismatch; the C7 "answer not composed" warning for a control the README claims.

### Step 13c. Submit #1 via the wrapper — W (S3), pre (after the scan)
```bash
$HK "bash $REPO/tools/submit_wrapper.sh --evidence $L/pack/evidence --workdir $L/pack/workdir ifabric" | tee $L/pack/submit-output.txt
```
- Add `--zip <PREFLIGHT_ZIP>` before `ifabric` ONLY when a preflight zip exists (the flag takes the next argument).
- Team name **`ifabric`** (the safety submit used it; reuse). The wrapper scans the staged dir, workdir and the unzipped preflight zip (needs `RESULT: clean`), verifies the manifest, then `exec submit.sh ifabric`.
- **Expected:** submit.sh's own output with the zip name `submission-ifabric-<UTC>.zip` → `<ZIP>`. Redact the account id before saving (`submit-output.redacted.txt`, as Hold-1c).
- **Stop:** `REFUSED: scan not clean …` / manifest verify failed.

### Step 13d. Readback — R
```bash
$HK "bash $REPO/tools/submit_wrapper.sh --readback <ZIP> --bucket \$TEAM_EVIDENCE_BUCKET --workdir $L/pack/workdir --print-root-cmd submit-1 ifabric" | tee $L/pack/readback.txt
```
- head-object → `get-object --if-match <ETag>` → head-object (GetObjectVersion is denied to us); sha256 = the local zip; scan + manifest verify on the unzipped copy. **Done:** `READBACK OK` + the printed root command (rows 63–64). Note the VersionId → `<ZIP_VERSION_ID>`.
- Then the write-once submission record, `run-ids.txt` copy (write-once, as T1) — not before the readback:
  `$HK "python3 $T/t1.py $L/t1/t1-submit-1.json $L/pack/submission-record-<UTC>.json=ifabric/submission-record-<UTC>.json $L/run-ids.txt=ifabric/run-ids/submit-1.txt"`
- **Stop:** any REFUSED line.

### Step 13e. Root publish (PR-32) on the T2 incident — W (ServiceNow note), pre
```bash
cd $REPO
python3 -m prooflab pack root --recompute <ZIP>      # must equal --recompute $L/pack/evidence
python3 -m prooflab pack root --label submit-1 --zip <ZIP> --pack-dir $L/pack/evidence --s3-version-id <ZIP_VERSION_ID> \
   --incident-sys-id $(cat $L/register/approval/t2-sys-id.txt) --sidecar $L/pack/pack-root.json --dry-run
# read the note text, then the same line without --dry-run
$HK "python3 $T/t1.py $L/t1/t1-pack-root-1.json $L/pack/pack-root.json=ifabric/pack-root/submit-1.json"
```
- **Expected:** the dry run prints the note (label, MANIFEST sha256, zip sha256, VersionId; no URL/bucket/account id); the live call exits 0 and writes the sidecar **outside** the pack (it is not in the MANIFEST); the sidecar goes up AFTER the pack.
- **Stop:** `RefusedNote` (a URL/12-digit/secret-shaped value in the note) → fix the input, never edit the note.
- Stop the ledger proxy (`kill %1` in the hk shell); `git -C $REPO status` clean; exact-value scan over `ops-lane/` (pre-push-secret-scan.sh via hk); write the lane report.

---

## Missing pieces and differences from the plan (fix before or at the step)

| # | Step | What is missing / differs | Fix used here / needed |
|---|---|---|---|
| M1 | 12a–c | **No verb writes the re-test link note** (N3→N2, N5→N4, N9→N8). `adapters/human_loop.retest_note()` exists, no CLI caller. ARCH §12.4: through the integration, else the owner by hand, else a gap row | Needs a `humanloop retest-link --finding F --retest-assessment A` verb (Hold-4 for the write); until then the owner pastes `retest_note()`'s text by hand |
| M2 | 12d | **No ESC-finding producer** for N6 (`esc_producer()` in ARCH §3.8 is not implemented; `humanloop findings` only builds from BREACHED assessments) | Needs code; else N6 is a gap row |
| M3 | C, D | `prooflab collect` has **no pull**; `run` has no live runner other than the b3 `drive.py` seam; `b3/measure.py`, `go_pilot.sh`, `echo_check.py` hard-code the old scratchpad, old runtime ids, PILOT/observe and an old creds expiry | Supplied: `tools/collect_spans.py`, `tools/drive.py` (copied), step A.4 runtime map, explicit ids to echo_check, `$CREDS`. AgentCore metric / aict pulls still have no driver (C9, PR-41) |
| M4 | 4, 6, 8 | **No mode-switch patch generator** (b3 `mkpatch.py` is observe-only) | Supplied: `tools/mkpatch.py <reg> <mode>`; tested for both modes |
| M5 | 3 | Plan row 20 puts the TEST-log rehearsal before N2; with T2 moved into Phase 1 the **first real notify is T2**, so the TEST log runs in step 3a (the approval finding needs BOTH logs under `wiring-tests/` for `--dry-run`) | Done in step 3a; it still contacts ServiceNow (selftest/lookup) |
| M6 | 1, 7, 9 | `assess --snapshot` without `--limit C7:…` returns C7 **INDETERMINATE** on the rehearsal's v1 (row 38): the register text lacks the C7 limits | Put `coverage_min_pct`, `gap_max_ms`, `violating_gap_share_max_pct` in the v1 draft before the freeze; otherwise pass `--limit` and record that it is not in the frozen text |
| M7 | 1 | The committed `register/register.yaml` has `inline_modes: observe` and `declared_conditions: …PENDING-CONDITION-TEXT`; prompt-attack is not in `declared_conditions` (ADV-H-01 is declared only via SHA256SUMS + the case file) | v1 draft must list `enforce,observe` and real condition shas |
| M8 | 11, 12a, 12e | **C9 path is PENDING-PR-41**: `tools/c9_model_swap.py`, the EP-0 declared-treatment rule for a model change, the metric-window pull and C9 assess are not on main | Wait for PR-41; N8/N9/N7 stay blocked |
| M9 | 10 | `humanloop analyze` uses Arth's default `max_attempts` (2); b6b pinned 1 in a lane driver. The CID is not in Arth's run record (`CallableAnalyzer` drops it): join by action id | Accept (≤ 2 invokes/finding in the token plan) or reuse `b6b/smoke_driver.py`'s `max_attempts=1` |
| M10 | 13b | `pack scan` refuses without injected values (`PROOFLAB_SCAN_VALUES` / `--scan-values-stdin`) | Inject through hk; else rely on the wrapper's pre-push scan, and say so |
| M11 | 9, D | **N4 provenance:** the rehearsal (and this dry run's refresh/assess) labelled N4 `FAULT_INJECTION` in `provenance.json`; this runbook passes `--provenance LIVE_SUBJECT` (ARCH §5.5). `contract/app_format.py` and `pack/projector.py` map FAULT_INJECTION → EXPLORATORY in the pack. The LIVE_SUBJECT + `--fault` combination parses (row 27) but was **not** run through refresh/assess/pack offline | Captain picks; recommended LIVE_SUBJECT in both the envelope and `provenance.json` (so the projector does not show N4 as EXPLORATORY), with the fault named in `run.condition`/the register |
| Q1 | — | CLI quirks: `pack verify --help` treats `--help` as a path; `pack index --help` prints `pack build`'s usage; `humanloop --help` omits the working `findings` verb; `collect --help` only lists surfaces | Cosmetic; use the forms in this runbook |

**Flags that differ from the plan text:** none of the plan's command lines fail to parse. The plan's "`registry freeze` writes `approval-finding.json`" (ARCH §3.8) is wrong: it is a separate verb, `registry approval-finding` (step 3). The plan's "`notify` (production log, absolute path)" is environment-driven: `PROOFLAB_DELIVERY_LOG` (no `--log` flag). Analysis is `humanloop analyze`, not `servicenow analyze` (the latter is Arth's single-finding CLI with the local Nemotron, not G-03).

## Dry-run table (bash dryrun.sh, 2026-10-06, main d57c868, /usr/bin/python3 3.9)
```
64 PASS, 0 FAIL, 10 other
PASS  0 rehearse_phase1.sh 68/68 · 1 freeze v1 --supersedes, BOTH pins, re-freeze refused, inv-2
PASS  2 T1 put --if-none-match * + head (fake S3), repeat refused
PASS  3 approval-finding · TEST-log DRY_RUN · guard (a) exit 2 · approval log required · logs must differ · T2 DELIVERED in the approval log only · sys_id from the log · APPROVED note -> RESPONDED · export
PASS  4 mkpatch enforce/observe (PIN_JSON == pin file; patches differ) · rails_patch · RAILS_MODE is an EP-0 pin key
PASS  4 run --dry-run N1..N9 (mode, LIVE_SUBJECT, pin sha, N4 fault) · ADV-H-01 condition sha == SHA256SUMS
LIVE-ONLY  4 kubectl patch/READY/echo · live prooflab run
PASS  5 collect_spans (22/22 rows) · refresh · assess (no --limit: C7 INDETERMINATE) · assess --limit · N2 C16 BREACHED, N4 C7 BREACHED · humanloop findings
PENDING-PR-41  5 C9 assess
PASS  6 TEST-log notify N2/N4 DRY_RUN · notify N2, N4 DELIVERED · re-run skipped · analyze (no ARN / ARN -> invoke argv, fake fails, never re-invoked) · check · snapshot · export · mirror
MISSING  6 re-test link note (M1) · ESC finding (M2)
PASS  7 run-ids · strict README refuses template · pack build (answers 5, pack-index) · v1 + findings in pack · pack scan · manifest verify · wrapper --dry-run · readback --bucket READBACK OK + root cmd · recompute zip == dir · pack root --dry-run · pack root on the FAKE SN T2 incident + sidecar · write-once copies · query --runs / C16 N2 exit 1 on a fresh unzip
QUIRK  pack verify --help · pack index --help · collect --help · humanloop --help
```

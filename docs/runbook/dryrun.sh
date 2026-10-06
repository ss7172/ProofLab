#!/usr/bin/env bash
# dryrun.sh: OFFLINE dry run of RUNBOOK-named-runs.md (every step that can run without AWS, the cluster or ServiceNow).
#
#   bash ~/firstmate-homes/TrustworthyAI/ops-lane/runbook/dryrun.sh [--keep]
#
# 1. runs the repo's PR-27 rehearsal (tools/rehearse_phase1.sh --keep) to get a synthetic WORKDIR: frozen v1, pins,
#    a snapshot with N1-N5 (fake ledger), assessments and findings;
# 2. then runs the RUNBOOK's own command lines against copies of it, with fakes ONLY: a stand-in `aws` on PATH
#    (tools/fakeaws.py: S3 write-once + readback, Logs Insights, invoke = fails), Arth's FakeServiceNow on loopback
#    (tools/fakesnow.py), a stub pre-push scan ("RESULT: clean") and a stub submit.sh.
# No real aws/kubectl/ServiceNow call; no secret read; ~/.prooflab-snow.env and workshop-local/env.sh are never sourced.
# Prints a PASS/FAIL table. Exit 0 = no FAIL. LIVE-ONLY rows are steps that cannot run offline (named in the table).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T="$HERE/tools"
REPO="${PROOFLAB_REPO:-$HOME/firstmate-homes/TrustworthyAI/TrustworthyAI-iFabric}"
PY=/usr/bin/python3; [ -x "$PY" ] || PY="$(command -v python3)"
KEEP=0; [ "${1:-}" = "--keep" ] && KEEP=1
export PYTHONDONTWRITEBYTECODE=1 PROOFLAB_REPO="$REPO"
unset SNOW_INSTANCE SNOW_CLIENT_ID SNOW_CLIENT_SECRET SNOW_OWNER_USER IFABRIC_ASSURE_RUNTIME_ARN AWS_PROFILE 2>/dev/null

DR="$(mktemp -d "${TMPDIR:-/tmp}/runbook-dryrun.XXXXXX")"
ROWS="$DR/rows.tsv"; : > "$ROWS"
row() { printf '%s\t%s\t%s\n' "$1" "$2" "$(printf '%s' "$3" | tr '\n\t' '  ' | cut -c1-150)" >> "$ROWS"; }
ok()  { if [ "$2" = 0 ]; then row PASS "$1" "${3:-}"; else row FAIL "$1" "${3:-}"; fi; }
pl()  { (cd "$REPO" && "$PY" -m prooflab "$@"); }
jget(){ "$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));print(eval(sys.argv[2]))" "$@"; }

# ---- fakes ---------------------------------------------------------------------------------------------------
mkdir -p "$DR/bin" "$DR/fakeaws" "$DR/snowstate"
printf '#!/bin/sh\nexec %s %s "$@"\n' "$PY" "$T/fakeaws.py" > "$DR/bin/aws"; chmod +x "$DR/bin/aws"
printf '#!/bin/sh\necho "scan (stub): $1"; echo "RESULT: clean"\n' > "$DR/bin/scan-stub.sh"
printf '#!/bin/sh\necho "submit.sh (stub) team=$1"\n' > "$DR/bin/submit.sh"; chmod +x "$DR/bin/submit.sh"
export PATH="$DR/bin:$PATH" FAKEAWS_DIR="$DR/fakeaws" TEAM_EVIDENCE_BUCKET="team-evidence-fake"
[ "$(command -v aws)" = "$DR/bin/aws" ] && row PASS "fake aws first on PATH" "$DR/bin/aws" || { row FAIL "fake aws first on PATH" "$(command -v aws)"; }
"$PY" "$T/fakesnow.py" "$DR/snowstate" & SNOWPID=$!
for _ in $(seq 50); do [ -f "$DR/snowstate/env.sh" ] && break; sleep 0.1; done
cleanup() { touch "$DR/snowstate/stop"; wait "$SNOWPID" 2>/dev/null; [ "$KEEP" = 1 ] || rm -rf "$DR" "${W:-/nonexistent}"; }
trap cleanup EXIT
[ -f "$DR/snowstate/env.sh" ] && row PASS "FakeServiceNow on loopback" "$(grep SNOW_INSTANCE "$DR/snowstate/env.sh" | cut -d"'" -f2)" || row FAIL "FakeServiceNow on loopback" "no env.sh"

# ---- 0. the repo rehearsal (synthetic N1-N5) -------------------------------------------------------------------
OUT="$(bash "$REPO/tools/rehearse_phase1.sh" --keep --json "$DR/rehearse.json" 2>&1)"; RC=$?
W="$(printf '%s\n' "$OUT" | sed -n 's/.*WORKDIR \(.*\) (kept).*/\1/p' | tail -1)"
ok "0 rehearse_phase1.sh (repo PR-27 rehearsal)" $RC "$(printf '%s\n' "$OUT" | grep '^TOTAL')"
[ -d "$W" ] || { row FAIL "rehearsal WORKDIR" "not found"; W=/nonexistent; }
RUNS="$("$PY" -c "import json;print(json.dumps({}))")"
N1=$(sed -n 1p "$W/workdir/run-ids.txt"); N2=$(sed -n 2p "$W/workdir/run-ids.txt"); N4=$(sed -n 4p "$W/workdir/run-ids.txt")

# ---- step 1: v1 freeze (laptop) ---------------------------------------------------------------------------------
REG="$DR/register"; mkdir -p "$REG/versions" "$REG/experiments"
pl registry freeze --version v1 --register "$W/register/versions/v1.yaml" --risks "$W/register/versions/v1.risks.yaml" \
   --out "$REG" --supersedes "$W/register/versions/v0-pilot.yaml" > "$DR/s1-freeze.txt" 2>&1; RC=$?
ok "1 registry freeze --version v1 --supersedes" $RC "$(tail -c 140 "$DR/s1-freeze.txt")"
[ -f "$REG/pins/v1-enforce.json" ] && [ -f "$REG/pins/v1-observe.json" ] \
  && row PASS "1 freeze wrote BOTH pins (v1-enforce, v1-observe)" "inline_modes must list enforce,observe" \
  || row FAIL "1 freeze wrote BOTH pins (v1-enforce, v1-observe)" "$(ls "$REG/pins" 2>&1)"
pl registry freeze --version v1 --register "$W/register/versions/v1.yaml" --risks "$W/register/versions/v1.risks.yaml" --out "$REG" >/dev/null 2>&1
[ $? -ne 0 ] && row PASS "1 a second freeze of v1 is refused (write-once)" "" || row FAIL "1 a second freeze of v1 is refused" "it was accepted"
pl registry inventory --version inv-2 --inventory "$W/register/inventory.yaml" --out "$REG" > "$DR/s1-inv.txt" 2>&1
ok "1 registry inventory --version inv-2 (optional re-freeze)" $? "$(tail -c 100 "$DR/s1-inv.txt")"

# ---- step 2: T1 (write-once S3) via the fake aws --------------------------------------------------------------
mkdir -p "$DR/evidence/t1"
"$PY" "$T/t1.py" "$DR/evidence/t1/t1-v1.json" "$REG/versions/v1.yaml=ifabric/register/v1.yaml" \
     "$REG/versions/v1.risks.yaml=ifabric/register/v1.risks.yaml" > "$DR/s2-t1.txt" 2>&1
ok "2 T1 put-object --if-none-match * + head-object (fake S3)" $? "$(head -c 140 "$DR/s2-t1.txt")"
"$PY" "$T/t1.py" "$DR/evidence/t1/t1-v1-again.json" "$REG/versions/v1.yaml=ifabric/register/v1.yaml" > /dev/null 2>&1
[ $? -ne 0 ] && row PASS "2 T1 again is refused (PreconditionFailed)" "write-once holds" || row FAIL "2 T1 again is refused" "overwrote"
T1AT=$(jget "$DR/evidence/t1/t1-v1.json" 'd[0]["head_object"]["LastModified"]' 2>/dev/null)

# ---- step 3: T2 approval Finding: TEST log first, then the real notify, the APPROVED note, check, export ----------
set -a; . "$DR/snowstate/env.sh"; set +a
EV="$DR/evidence"; mkdir -p "$EV/register/approval" "$EV/servicenow/wiring-tests"
pl registry approval-finding --version v1 --register "$REG/versions/v1.yaml" --risks "$REG/versions/v1.risks.yaml" \
   --out "$EV/register/approval" --detected-at "${T1AT:-2026-10-06T12:00:00Z}" > "$DR/s3-af.txt" 2>&1; RC=$?
AF="$(ls "$EV"/register/approval/*.json 2>/dev/null | head -1)"
ok "3 registry approval-finding (T2 finding from the frozen bytes)" $RC "$AF"
PROD_LOG="$EV/servicenow/delivery-log.jsonl"; APPR_LOG="$EV/register/approval/delivery-log.jsonl"
TEST_LOG="$EV/servicenow/wiring-tests/delivery-log.jsonl"; TEST_APPR="$EV/servicenow/wiring-tests/approval-delivery-log.jsonl"
PROOFLAB_DELIVERY_LOG="$TEST_LOG" PROOFLAB_APPROVAL_DELIVERY_LOG="$TEST_APPR" pl humanloop notify --dry-run --finding "$AF" > "$DR/s3-test.json" 2> "$DR/s3-test.err"; RC=$?
grep -q '"DRY_RUN"' "$DR/s3-test.json"; ok "3 TEST-log rehearsal: notify --dry-run under wiring-tests/ -> DRY_RUN" $(( RC + $? )) "rc=$RC $(head -c 80 "$DR/s3-test.err")"
PROOFLAB_DELIVERY_LOG="$PROD_LOG" PROOFLAB_APPROVAL_DELIVERY_LOG="$APPR_LOG" pl humanloop notify --dry-run --finding "$AF" > /dev/null 2> "$DR/s3-guard.err"; RC=$?
[ $RC = 2 ] && row PASS "3 guard (a): --dry-run on the production log is refused (exit 2)" "$(head -c 90 "$DR/s3-guard.err")" || row FAIL "3 guard (a) refusal" "rc=$RC"
PROOFLAB_DELIVERY_LOG="$PROD_LOG" pl humanloop notify --finding "$AF" > /dev/null 2> "$DR/s3-noappr.err"; RC=$?
[ $RC = 2 ] && row PASS "3 approval finding without PROOFLAB_APPROVAL_DELIVERY_LOG is refused" "$(head -c 90 "$DR/s3-noappr.err")" || row FAIL "3 approval log required" "rc=$RC"
PROOFLAB_DELIVERY_LOG="$PROD_LOG" PROOFLAB_APPROVAL_DELIVERY_LOG="$PROD_LOG" pl humanloop notify --finding "$AF" > /dev/null 2>&1
[ $? = 2 ] && row PASS "3 approval log == main log is refused" "" || row FAIL "3 approval log == main log is refused" ""
export PROOFLAB_DELIVERY_LOG="$PROD_LOG" PROOFLAB_APPROVAL_DELIVERY_LOG="$APPR_LOG"
pl humanloop notify --finding "$AF" > "$DR/s3-notify.json" 2> "$DR/s3-notify.err"; RC=$?
grep -q '"DELIVERED"' "$DR/s3-notify.json" && [ -s "$APPR_LOG" ] && [ ! -s "$PROD_LOG" ]
ok "3 T2 notify -> DELIVERED, in the APPROVAL log only" $(( RC + $? )) "$(grep -o '"number": "[^"]*"' "$DR/s3-notify.json")"
T2NUM=$(jget "$DR/s3-notify.json" 'd[0]["number"]' 2>/dev/null)
T2SYS=$("$PY" -c "import json,sys;print([json.loads(l) for l in open(sys.argv[1]) if l.strip() and json.loads(l).get('state')=='DELIVERED'][-1]['sys_id'])" "$APPR_LOG" 2>/dev/null)
[ -n "$T2SYS" ] && row PASS "3 T2 incident sys_id read from the approval delivery log" "sys_id=${T2SYS:0:8}... number=$T2NUM" || row FAIL "3 T2 sys_id from the log" ""
NOTE=$("$PY" -c "import sys;sys.path.insert(0,sys.argv[1]);from prooflab.registry import approval_finding as A, freeze;import hashlib
from prooflab.contract import register as R
r=open(sys.argv[2],'rb').read();k=open(sys.argv[3],'rb').read();print(A.approval_note_text('v1',R.register_sha256(r),R.register_sha256(k)))" "$REPO" "$REG/versions/v1.yaml" "$REG/versions/v1.risks.yaml")
"$PY" -c "import json,sys;json.dump({'op':'note','number':sys.argv[1],'text':sys.argv[2]},open(sys.argv[3],'w'))" "$T2NUM" "$NOTE" "$DR/snowstate/cmd-1.json"
sleep 0.5
CUT=$(date -u -v+1M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '+1 min' +%Y-%m-%dT%H:%M:%SZ)
pl humanloop check --finding "$AF" --cutoff "$CUT" --once > "$DR/s3-check.json" 2> "$DR/s3-check.err"; RC=$?
grep -q 'RESPONDED' "$DR/s3-check.json"; ok "3 captain's APPROVED note -> humanloop check --once = RESPONDED" $(( RC + $? )) "note='${NOTE:0:60}...'"
pl humanloop export --finding "$AF" --out "$EV/servicenow/export" > "$DR/s3-export.json" 2>&1; RC=$?
[ -n "$(ls "$EV/servicenow/export" 2>/dev/null)" ]; ok "3 humanloop export (T2 incident as evidence JSON)" $(( RC + $? )) "$(ls "$EV/servicenow/export" 2>/dev/null | head -2 | tr '\n' ' ')"

# ---- step 4: pin patches (4-key) + rails patch + run --dry-run for every named run -----------------------------
P="$DR/patches"; mkdir -p "$P"
for m in enforce observe; do
  "$PY" "$T/mkpatch.py" "$REG/versions/v1.yaml" $m "$P/pin-v1-$m.patch.json" "$P/pinfile-v1-$m.json" > "$P/mk-$m.txt" 2>&1; RC=$?
  grep -q '"pin_json_equals_pin_file": true' "$P/mk-$m.txt"; ok "4 mkpatch.py v1 $m: 4 keys, PIN_JSON == pins/v1-$m.json" $(( RC + $? )) "$(grep -o '"pin_sha256": "[0-9a-f]\{12\}' "$P/mk-$m.txt")"
done
cmp -s "$P/pin-v1-enforce.patch.json" "$P/pin-v1-observe.patch.json" && row FAIL "4 enforce and observe patches differ" "identical" || row PASS "4 enforce and observe patches differ (mode is in the pin)" ""
"$PY" "$T/rails_patch.py" observe "$P/rails-observe.json" >/dev/null && "$PY" "$T/rails_patch.py" enforce "$P/rails-enforce.json" >/dev/null
ok "4 rails_patch.py observe/enforce (ADV-H-01, optional)" $? ""
"$PY" -c "import sys;sys.path.insert(0,sys.argv[1]);from prooflab.adapters.orchestrator import preflight as p;assert 'IFABRIC_RAILS_MODE' in p.PIN_ENV_KEYS" "$REPO"
ok "4 EP-0 treats IFABRIC_RAILS_MODE as a declared pin key" $? "preflight.PIN_ENV_KEYS"
dry() {  # $1 label, $2 want-mode, rest = run args
  local label="$1" want="$2"; shift 2
  pl run --dry-run --family run --provenance LIVE_SUBJECT --scenario-file "$REPO/register/scenarios/$1.json" "$@" > "$P/dry-$label.json" 2> "$P/dry-$label.err" ; true
}
for spec in "N1|S1|enforce|" "N2|S2|observe|" "N3|S2|enforce|" "N4|S1|enforce|--fault suppress-record:ifabric-it:tool.call:1" \
            "N5|S1|enforce|" "N6|S3|enforce|" "N7|S1|enforce|" "N8|S1|enforce|" "N9|S1|enforce|"; do
  IFS='|' read -r N SC M EXTRA <<< "$spec"
  # shellcheck disable=SC2086
  (cd "$REPO" && "$PY" -m prooflab run --dry-run --scenario $SC --mode $M --family run --provenance LIVE_SUBJECT \
     --scenario-file "$REPO/register/scenarios/$SC.json" --pin-file "$P/pinfile-v1-$M.json" $EXTRA) > "$P/dry-$N.json" 2> "$P/dry-$N.err"; RC=$?
  CHK=$("$PY" - "$P/dry-$N.json" "$M" "$EXTRA" <<'EOF'
import json,sys
d=json.load(open(sys.argv[1]));e=d["envelope"]
bad=[]
if e["mode"]!=sys.argv[2]: bad.append("mode")
if e["provenance"]!="LIVE_SUBJECT": bad.append("provenance=%s"%e["provenance"])
if not e.get("pin_sha256"): bad.append("pin_sha256 missing")
if sys.argv[3] and not (d.get("fault") or {}).get("spec"): bad.append("fault missing")
print("OK" if not bad else ",".join(bad), e["run_id"], e["provenance"], (d.get("fault") or {}).get("spec"))
EOF
)
  case "$CHK" in OK*) row PASS "4 run --dry-run $N ($SC, $M${EXTRA:+, fault})" "$CHK";; *) row FAIL "4 run --dry-run $N ($SC, $M)" "rc=$RC $CHK $(head -c 80 "$P/dry-$N.err")";; esac
done
(cd "$REPO" && "$PY" -m prooflab run --dry-run --scenario S1 --only ifabric-customer --condition prompt-attack --mode enforce \
   --family adv --provenance AUTHORIZED_TEST --scenario-file "$REPO/register/scenarios/S1.json" --pin-file "$P/pinfile-v1-enforce.json") > "$P/dry-ADV.json" 2> "$P/dry-ADV.err"; RC=$?
SUM=$(awk '$2=="prompt-attack.txt"{print $1}' "$REPO/register/conditions/SHA256SUMS")
grep -q "\"condition_sha256\": \"$SUM\"" "$P/dry-ADV.json"; ok "4 run --dry-run ADV-H-01 leg A (--condition prompt-attack, sha = SHA256SUMS)" $(( RC + $? )) "sha ${SUM:0:12} $(grep -o '"run_id": "[^"]*"' "$P/dry-ADV.json" | head -1)"
row LIVE-ONLY "4 kubectl patch (dry-run=server, then patch) x3 + READY + echo" "needs the cluster; patch JSONs above are the inputs"
row LIVE-ONLY "4 prooflab run (live) via tools/drive.py" "needs AWS; argv identical to the dry-run rows minus --dry-run"

# ---- step 5: collect (missing verb) -> refresh -> assess -> findings ----------------------------------------------
SNAP="$DR/snap"; cp -R "$W/snap" "$SNAP"; rm -rf "$SNAP/servicenow" "$SNAP/findings"
mkdir -p "$DR/collect"
FAKEAWS_SPANS="$W/snap/raw/aws-spans/$N2/spans.jsonl" "$PY" "$T/collect_spans.py" "$DR/collect" "$N2" 2026-10-06T00:00:00Z 2026-10-06T23:59:59Z > "$DR/s5-collect.txt" 2>&1; RC=$?
WANT=$(grep -c . "$W/snap/raw/aws-spans/$N2/spans.jsonl"); GOT=$(jget "$DR/s5-collect.txt" 'd["rows"]' 2>/dev/null)
[ "$RC" = 0 ] && [ "$WANT" = "$GOT" ]; ok "5 collect_spans.py (glue: prooflab collect has no pull verb)" $? "rows $GOT of $WANT -> raw/aws-spans/<cid>/spans.jsonl"
pl refresh --snapshot "$SNAP" --run-ids "$W/workdir/run-ids.txt" --provenance "$W/provenance.json" --as-of 2026-10-06T12:30:00Z --join-tolerance-s 5 > "$DR/s5-refresh.txt" 2>&1
ok "5 refresh --snapshot --run-ids --provenance (offline: no --pull-ledger)" $? "$(tail -c 100 "$DR/s5-refresh.txt")"
rm -rf "$SNAP/assessments"
pl assess --snapshot "$SNAP" --register "$W/register/versions/v1.yaml" > "$DR/s5-assess-nolimit.txt" 2>&1; RC=$?
row "$( [ $RC -le 1 ] && echo PASS || echo FAIL )" "5 assess --snapshot WITHOUT --limit C7:... (rc 1 = a BREACH exists)" "rc=$RC $(grep -o 'C7[^|]*' "$DR/s5-assess-nolimit.txt" | head -1 | cut -c1-80)"
rm -rf "$SNAP/assessments"
pl assess --snapshot "$SNAP" --register "$W/register/versions/v1.yaml" --limit C7:coverage_min_pct=100 --limit C7:gap_max_ms=86000 \
   --limit C7:violating_gap_share_max_pct=0 > "$DR/s5-assess.txt" 2>&1; RC=$?
[ $RC -le 1 ] && [ -f "$SNAP/assessments/C16/$N2.json" ]; ok "5 assess --snapshot --register v1 --limit C7:... (rc 1 normal)" $? "rc=$RC files=$(ls "$SNAP"/assessments/*/*.json 2>/dev/null | wc -l | tr -d ' ')"
V2=$(jget "$SNAP/assessments/C16/$N2.json" 'd["requirement_verdict"]' 2>/dev/null); V4=$(jget "$SNAP/assessments/C7/$N4.json" 'd["requirement_verdict"]' 2>/dev/null)
[ "$V2" = BREACHED ] && [ "$V4" = BREACHED ]; ok "5 N2 C16 = BREACHED, N4 C7 = BREACHED" $? "N2=$V2 N4=$V4"
row PENDING-PR-41 "5 C9 assess from AgentCore metric windows (N1/N7/N8/N9)" "main d57c868 has no C9 metric pull/assess path; PR-41 not merged"
pl humanloop findings --snapshot "$SNAP" --register "$W/register/versions/v1.yaml" > "$DR/s5-findings.json" 2>&1; RC=$?
F2="$SNAP/findings/C16-$N2.json"; F4="$SNAP/findings/C7-$N4.json"
[ -f "$F2" ] && [ -f "$F4" ]; ok "5 humanloop findings (hidden verb, not in --help)" $(( RC + $? )) "$(ls "$SNAP/findings" | tr '\n' ' ')"

# ---- step 6: notify N2/N4 (TEST log first, then production), analyze, check/snapshot/export/mirror ------------------
PROOFLAB_DELIVERY_LOG="$TEST_LOG" pl humanloop notify --dry-run --finding "$F2" --finding "$F4" > "$DR/s6-test.json" 2>&1; RC=$?
[ "$(grep -c '"DRY_RUN"' "$DR/s6-test.json")" = 2 ]; ok "6 TEST-log notify --dry-run (N2, N4) -> 2 DRY_RUN" $(( RC + $? )) ""
pl humanloop notify --finding "$F2" > "$DR/s6-n2.json" 2>&1; RC=$?
grep -q '"DELIVERED"' "$DR/s6-n2.json"; ok "6 notify N2 (production log, absolute path) -> DELIVERED" $(( RC + $? )) "$(grep -o '"number": "[^"]*"' "$DR/s6-n2.json")"
pl humanloop notify --finding "$F4" > "$DR/s6-n4.json" 2>&1; RC=$?
grep -q '"DELIVERED"' "$DR/s6-n4.json"; ok "6 notify N4 -> DELIVERED" $(( RC + $? )) "$(grep -o '"number": "[^"]*"' "$DR/s6-n4.json")"
pl humanloop notify --finding "$F2" --finding "$F4" > "$DR/s6-again.json" 2>&1; RC=$?
[ "$(grep -c '"skipped"' "$DR/s6-again.json")" = 2 ]; ok "6 notify re-run sends nothing (not a new finding id)" $(( RC + $? )) ""
pl humanloop analyze --finding "$F2" --finding "$F4" --out "$EV/servicenow/assurance" > "$DR/s6-analyze-noarn.json" 2>&1; RC=$?
ok "6 humanloop analyze (no ARN set): parses; Arth records UNAVAILABLE (row action=analysed)" $RC "$(grep -o '"action": "[a-z]*"' "$DR/s6-analyze-noarn.json" | sort | uniq -c | tr '\n' ' ')"
IFABRIC_ASSURE_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-east-1:000000000000:runtime/ifabric_assurance_agent-FAKE000000" \
  pl humanloop analyze --finding "$F2" --finding "$F4" --out "$EV/servicenow/assurance" > "$DR/s6-analyze.json" 2>&1; RC=$?
grep -q "invoke-agent-runtime" "$FAKEAWS_DIR/calls.log"; ok "6 humanloop analyze with ARN -> aws bedrock-agentcore invoke-agent-runtime argv (fake fails)" $(( RC + $? )) "$(grep -c invoke-agent-runtime "$FAKEAWS_DIR/calls.log") invoke(s) for 2 findings; $(grep -o '"reason": "[^"]*"' "$DR/s6-analyze.json" | sort -u | head -2 | tr '\n' ' ')"
pl humanloop check --finding "$F2" --finding "$F4" --cutoff "$CUT" --once > "$DR/s6-check.json" 2>&1; RC=$?
row "$( [ $RC -le 1 ] && echo PASS || echo FAIL )" "6 humanloop check --once (no reply yet)" "rc=$RC $(grep -o '"state": "[A-Z_]*"' "$DR/s6-check.json" | sort -u | tr '\n' ' ')"
pl humanloop snapshot --finding "$F2" --finding "$F4" --cutoff "$CUT" --out "$EV/servicenow/cases" > "$DR/s6-snap.json" 2>&1
ok "6 humanloop snapshot (case views)" $? "$(ls "$EV/servicenow/cases" 2>/dev/null | wc -l | tr -d ' ') file(s)"
pl humanloop export --finding "$F2" --finding "$F4" --finding "$AF" --out "$EV/servicenow/export" > "$DR/s6-export.json" 2>&1
ok "6 humanloop export (N2, N4, T2)" $? "$(ls "$EV/servicenow/export" | wc -l | tr -d ' ') file(s)"
pl humanloop mirror --out "$SNAP/derived/notifications.jsonl" > "$DR/s6-mirror.json" 2>&1
ok "6 humanloop mirror (delivery logs -> notification records)" $? "$(cat "$DR/s6-mirror.json" | head -c 80)"
row MISSING "6 re-test link note (N3->N2, N5->N4, N9->N8 incidents)" "adapters/human_loop.retest_note() has no CLI caller"
row MISSING "6 ESC finding for N6 (S3 escalate)" "no esc_producer / verb builds an escalation Finding from judgment records"

# ---- step 7: pack build, scan, verify, submit (stubs), readback (fake S3), root publish (fake SN) -----------------
WD="$DR/workdir"; cp -R "$W/workdir" "$WD"; cp "$REG/versions/v1.yaml" "$WD/register.yaml"
cp -R "$EV/servicenow" "$SNAP/servicenow" 2>/dev/null; rm -rf "$SNAP/servicenow/wiring-tests"
rm -rf "$SNAP/register"; cp -R "$W/register" "$SNAP/register"
pl registry run-ids --run-ids "$WD/run-ids.txt" --experiments "$W/register/experiments/experiments.jsonl" > "$DR/s7-runids.txt" 2>&1
ok "7 registry run-ids (one CID per line, no pilot)" $? "$(cat "$DR/s7-runids.txt" | head -c 80)"
PK="$DR/out1/evidence"
pl pack build --out "$PK" --src "$SNAP" --workdir "$WD" --strict-readme > "$DR/s7-strict.txt" 2>&1; RC=$?
# PR-40b (ab7d8d4): pack build FILLS the README before --strict-readme, so a strict build of the template must now SUCCEED with no <...> placeholder left.
NPH=$(grep -o '<[A-Z_][A-Z_-]*>' "$DR/out1/evidence/README.md" 2>/dev/null | grep -v -x -E '<CID>|<cid>' | sort -u | tr '\n' ' ')
[ $RC -eq 0 ] && row PASS "7 pack build --strict-readme builds (README filled by PR-40b)" "rc=$RC" || row FAIL "7 strict README build" "rc=$RC"
row INFO "7 README fields still unfilled (routed to the console/README PR; <CID> in command examples is allowed)" "${NPH:-none}"
printf '# Evidence Pack (DRY RUN)\n\nSynthetic rehearsal pack; no placeholders.\n' > "$DR/README.filled.md"
PK="$DR/out2/evidence"
PROOFLAB_SCAN_VALUES="dryrun-not-a-secret-value-000000" pl pack build --out "$PK" --src "$SNAP" --workdir "$WD" --readme "$DR/README.filled.md" --strict-readme > "$DR/s7-build.txt" 2>&1; RC=$?
ok "7 pack build --src --workdir --readme --strict-readme" $RC "$(grep -c warning "$DR/s7-build.txt") warning(s); answers=$(ls "$PK/answers" 2>/dev/null | wc -l | tr -d ' ') pack-index=$( [ -f "$PK/pack-index.json" ] && echo yes || echo no)"
[ -f "$PK/register/versions/v1.yaml" ] && [ -d "$PK/findings" ]; ok "7 pack carries register/versions/v1.yaml and findings/" $? ""
PROOFLAB_SCAN_VALUES="dryrun-not-a-secret-value-000000" pl pack scan "$PK" > "$DR/s7-scan.txt" 2>&1; ok "7 pack scan" $? "$(head -c 60 "$DR/s7-scan.txt")"
"$PY" "$REPO/tools/manifest.py" verify "$PK" > "$DR/s7-verify.txt" 2>&1; ok "7 tools/manifest.py verify" $? "$(head -c 60 "$DR/s7-verify.txt")"
ZDIR="$DR/zip"; mkdir -p "$ZDIR"; ZIP="$ZDIR/submission-ifabric-20261006T120000Z.zip"
(cd "$DR/out2" && cp "$WD/register.yaml" "$WD/gap-list.md" "$WD/run-ids.txt" . && cp "$REPO/evidence-templates/sketch.png" . 2>/dev/null; zip -qr "$ZIP" evidence register.yaml gap-list.md run-ids.txt sketch.png)
row INFO "7 zip made by the dry run (stand-in for the kit's submit.sh layout)" "$(basename "$ZIP")"
SUBMIT_SH="$DR/bin/submit.sh" PROOFLAB_PREPUSH_SCAN="$DR/bin/scan-stub.sh" bash "$REPO/tools/submit_wrapper.sh" --dry-run --evidence "$PK" --workdir "$WD" --zip "$ZIP" ifabric > "$DR/s7-wrap.txt" 2>&1; RC=$?
grep -q '^DRY-RUN: ' "$DR/s7-wrap.txt"; ok "7 submit_wrapper.sh --dry-run (scan x3 + verify) -> DRY-RUN" $(( RC + $? )) "$(tail -1 "$DR/s7-wrap.txt")"
aws s3api put-object --bucket "$TEAM_EVIDENCE_BUCKET" --key "submissions/ifabric/$(basename "$ZIP")" --body "$ZIP" > "$DR/s7-put.json"
ZVER=$(jget "$DR/s7-put.json" 'd["VersionId"]')
PROOFLAB_PREPUSH_SCAN="$DR/bin/scan-stub.sh" bash "$REPO/tools/submit_wrapper.sh" --readback "$ZIP" --bucket "$TEAM_EVIDENCE_BUCKET" --workdir "$WD" --print-root-cmd submit-1 ifabric > "$DR/s7-readback.txt" 2>&1; RC=$?
grep -q '^READBACK OK' "$DR/s7-readback.txt"; ok "7 submit_wrapper.sh --readback --bucket (head, get --if-match, head) -> READBACK OK" $(( RC + $? )) "$(grep -o 'VersionId and ETag identical[^)]*)' "$DR/s7-readback.txt")"
grep -q 'prooflab pack root --label submit-1' "$DR/s7-readback.txt"; ok "7 readback prints the root-publish command" $? ""
pl pack root --recompute "$ZIP" > "$DR/s7-recompute.txt" 2>&1; R1=$?; pl pack root --recompute "$PK" > "$DR/s7-recompute2.txt" 2>&1
[ $R1 = 0 ] && cmp -s "$DR/s7-recompute.txt" "$DR/s7-recompute2.txt"; ok "7 pack root --recompute: zip == pack dir" $? "$(head -c 70 "$DR/s7-recompute.txt")"
pl pack root --label submit-1 --zip "$ZIP" --pack-dir "$PK" --s3-version-id "$ZVER" --incident-sys-id "$T2SYS" --sidecar "$DR/sidecar/pack-root.json" --dry-run > "$DR/s7-root-dry.txt" 2>&1
ok "7 pack root --dry-run (note text only)" $? "$(head -c 90 "$DR/s7-root-dry.txt")"
pl pack root --label submit-1 --zip "$ZIP" --pack-dir "$PK" --s3-version-id "$ZVER" --incident-sys-id "$T2SYS" --sidecar "$DR/sidecar/pack-root.json" > "$DR/s7-root.txt" 2>&1; RC=$?
[ -f "$DR/sidecar/pack-root.json" ]; ok "7 pack root (FAKE ServiceNow) posts the note on the T2 incident + sidecar outside the pack" $(( RC + $? )) "$(tail -c 90 "$DR/s7-root.txt")"
mkdir -p "$DR/sidecar-upload"; "$PY" "$T/t1.py" "$DR/sidecar-upload/t1.json" "$DR/sidecar/pack-root.json=ifabric/pack-root/submit-1.json" "$WD/run-ids.txt=ifabric/run-ids/submit-1.txt" > /dev/null 2>&1
ok "7 write-once copies: pack-root sidecar + run-ids.txt (t1.py)" $? ""
FR="$DR/fresh"; mkdir -p "$FR"; (cd "$FR" && unzip -q "$ZIP")
(cd "$FR/evidence" && "$PY" -m prooflab query --runs > "$DR/s7-q-runs.txt" 2>&1); RC=$?; ok "7 query --runs from a fresh unzip" $RC "$(grep -c ifabric-run "$DR/s7-q-runs.txt") run line(s)"
(cd "$FR/evidence" && "$PY" -m prooflab query --control C16 --run "$N2" > "$DR/s7-q-n2.txt" 2>&1); RC=$?
[ $RC = 1 ] && row PASS "7 query --control C16 --run N2 -> BREACHED (exit 1)" "" || row FAIL "7 query C16 N2" "rc=$RC $(head -c 80 "$DR/s7-q-n2.txt")"

# ---- CLI quirks found while writing the runbook ----------------------------------------------------------------
pl pack verify --help > "$DR/q1.txt" 2>&1; RC=$?
[ $RC -ne 0 ] && row QUIRK "pack verify --help treats --help as a path" "$(head -c 80 "$DR/q1.txt")" || row PASS "pack verify --help" ""
pl pack index --help 2>&1 | grep -q 'usage: prooflab pack build' && row QUIRK "pack index --help prints pack build's usage" "" || row PASS "pack index --help" ""
pl collect --help 2>&1 | grep -q '^collectors:' && row QUIRK "collect --help: no options; the verb only lists surfaces (no pull)" "use tools/collect_spans.py" || row PASS "collect" ""
pl humanloop --help 2>&1 | grep -q '{.*findings' && row PASS "humanloop --help lists findings" "" || row QUIRK "humanloop --help omits the 'findings' verb (it works)" ""

# ---- table ------------------------------------------------------------------------------------------------------
echo; printf '%-4s %-14s %-72s %s\n' "#" "RESULT" "STEP" "NOTE"
awk -F'\t' '{printf "%-4d %-14s %-72s %s\n", NR, $1, substr($2,1,72), $3}' "$ROWS"
P_=$(grep -c '^PASS' "$ROWS"); F_=$(grep -c '^FAIL' "$ROWS"); O_=$(grep -vc '^PASS\|^FAIL' "$ROWS")
echo "TOTAL: $P_ PASS, $F_ FAIL, $O_ other (LIVE-ONLY / PENDING / MISSING / QUIRK / INFO)   python=$PY"
echo "dry-run dir: $DR $( [ "$KEEP" = 1 ] && echo '(kept)' || echo '(removed)')"
[ "$F_" = 0 ]

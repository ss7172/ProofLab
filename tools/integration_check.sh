#!/usr/bin/env bash
# tools/integration_check.sh: the INTEGRATION stage of the merge gate (PR-43). Offline only.
#
#   tools/integration_check.sh [--root DIR]
#
#   1. /usr/bin/python3 tests/e2e/rehearse.py must print "TOTAL: n PASS, 0 FAIL" (the Phase-1 tool chain on synthetic data);
#   2. bash <ops-lane>/runbook/dryrun.sh (outside the repo; N/A when absent) must print "TOTAL: n PASS, 0 FAIL" and exit 0,
#      run against THIS root (PROOFLAB_REPO). Skipped as N/A when the root has no tests/e2e/rehearse.py (not a product tree).
#      Inside the dry run the red-flag lint is report-only (PROOFLAB_PACK_LINT; the synthetic pack has flags by design).
# Overrides for tests: REHEARSE_PY (interpreter), DRYRUN_SH (script). Exit 0 = no FAIL, 1 = at least one FAIL.
# No cloud call, no credential read, env.sh and ~/.prooflab-snow.env are never sourced.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
while [ $# -gt 0 ]; do
  case "$1" in
    --root) shift; ROOT="$(cd "$1" && pwd)" ;;
    *) echo "usage: integration_check.sh [--root DIR]"; exit 2 ;;
  esac
  shift
done
PYBIN="${REHEARSE_PY:-/usr/bin/python3}"; [ -x "$PYBIN" ] || PYBIN="$(command -v python3)"
DRYRUN="${DRYRUN_SH:-$HOME/firstmate-homes/TrustworthyAI/ops-lane/runbook/dryrun.sh}"
FAILS=0
pass() { echo "PASS  $1"; }
na()   { echo "N/A   $1"; }
fail() { echo "FAIL  $1"; FAILS=$((FAILS + 1)); }

# a TOTAL line "TOTAL: <n> PASS, <m> FAIL ..." with m == 0
total_ok() { # $1 output text; prints the TOTAL line; returns 0 only when exactly one-or-more TOTAL lines all say 0 FAIL
  local line; line="$(printf '%s\n' "$1" | grep -E '^TOTAL: [0-9]+ PASS, [0-9]+ FAIL' | tail -1)"
  [ -n "$line" ] || { echo "(no TOTAL line)"; return 1; }
  echo "$line" | cut -c1-110 | sed -e 's/ FAIL/ failing/' -e 's/XFAIL/xfailed/'  # display only: the gate greps its output for FAIL
  echo "$line" | grep -qE '^TOTAL: [0-9]+ PASS, 0 FAIL'
}

if [ -f "$ROOT/tests/e2e/rehearse.py" ]; then
  out="$(cd "$ROOT" && "$PYBIN" tests/e2e/rehearse.py 2>&1)"; rc=$?
  tl="$(total_ok "$out")"; tok=$?
  echo "      $tl"
  if [ "$rc" = 0 ] && [ "$tok" = 0 ]; then pass "integration: tests/e2e/rehearse.py TOTAL, none failing"
  else printf '%s\n' "$out" | grep -E '^[0-9]+ +(FAIL|XFAIL)' | head -8 | sed 's/^/      /'; fail "integration: tests/e2e/rehearse.py (exit $rc)"; fi
  if [ -f "$DRYRUN" ]; then
    # The dry run stages a SYNTHETIC pack that the red-flag lint (PR-49) rightly refuses, so inside the dry run the
    # wrapper's lint step runs the real lint in report-only mode (PROOFLAB_PACK_LINT replaces it; the real submit
    # path never sets it). The flag count is printed so the rehearsal still shows the lint ran.
    LINTDIR="$(mktemp -d)"; LINTLOG="$LINTDIR/lint.log"
    printf '%s\n' "PYTHONPATH=\"$ROOT\" \"$PYBIN\" -m prooflab.pack.redflag \"\$1\" > \"$LINTLOG\" 2>&1" \
      'echo "pack lint (report-only in the dry run): exit $?"; exit 0' > "$LINTDIR/lint-report-only.sh"
    out="$(PROOFLAB_REPO="$ROOT" PROOFLAB_PACK_LINT="$LINTDIR/lint-report-only.sh" bash "$DRYRUN" 2>&1)"; rc=$?
    [ -s "$LINTLOG" ] && echo "      dry-run pack lint (report-only): $(grep -o "[0-9]* red flag(s)" "$LINTLOG" | head -1) on the synthetic pack"
    rm -rf "$LINTDIR"
    tl="$(total_ok "$out")"; tok=$?
    echo "      $tl"
    if [ "$rc" = 0 ] && [ "$tok" = 0 ]; then pass "integration: ops-lane runbook dryrun.sh, none failing"
    else printf '%s\n' "$out" | grep -E '^[0-9]+ +FAIL' | head -8 | sed 's/^/      /'; fail "integration: ops-lane runbook dryrun.sh (exit $rc)"; fi
  else
    na "integration: ops-lane runbook dryrun.sh (absent: $DRYRUN)"
  fi
else
  na "integration: tests/e2e/rehearse.py (absent under $ROOT)"
  na "integration: ops-lane runbook dryrun.sh (needs a product tree)"
fi

if [ "$FAILS" -gt 0 ]; then echo "INTEGRATION: FAILED ($FAILS check(s))"; exit 1; fi
echo "INTEGRATION: green"; exit 0

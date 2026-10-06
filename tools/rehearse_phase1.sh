#!/usr/bin/env bash
# tools/rehearse_phase1.sh: the OFFLINE Phase-1 end-to-end rehearsal (PR-27) in one command.
#
#   tools/rehearse_phase1.sh [--keep] [--json OUT] [-v] [--python PY]
#
# Runs tests/e2e/rehearse.py with /usr/bin/python3 (the judge's interpreter) in a fresh temp WORKDIR:
# registry freeze/derive/pin, synthetic N1-N5 through the merged adapters into a fake ledger, the collector
# with a fake aws runner, refresh, postrun, assess, findings + notify to a FAKE ServiceNow, pack build with
# redaction + scan + MANIFEST, and the query CLI from a fresh unzip. Prints a PASS/FAIL table.
# No AWS, cluster or ServiceNow call; no secret is read. Exit 0 = no FAIL (XFAIL rows name a defect id).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PY="/usr/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"
cd "$ROOT" && exec "$PY" "$ROOT/tests/e2e/rehearse.py" "$@"

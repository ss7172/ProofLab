#!/usr/bin/env bash
# Guarded submit: refuse unless the exact-value scan is clean and manifest.py verify passes.
#   submit_wrapper.sh [--dry-run] [--evidence DIR] <team>      scan + verify, then submit.sh <team>
#   submit_wrapper.sh --readback <zip> [--print-root-cmd <label>]  unzip, verify, re-scan; optionally PRINT the
#       ops-lane command that publishes the root (unsigned). This script never posts anything itself.
# Fails closed with no values unless --allow-empty-scan or PROOFLAB_ALLOW_EMPTY_SCAN=1.
# Scan values come from PROOFLAB_SCAN_VALUES (one per line); never read from a file here.
# Env: PROOFLAB_PYTHON (default python3), PROOFLAB_REPO (repo root), PROOFLAB_MANIFEST_PY.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${PROOFLAB_REPO:-$(dirname "$HERE")}"
PY="${PROOFLAB_PYTHON:-python3}"
MANIFEST="${PROOFLAB_MANIFEST_PY:-$HERE/manifest.py}"
EVID="$HOME/evidence"; DRY=0; ALLOW="";  READBACK=""; TEAM=""; ROOTLABEL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --evidence) EVID="$2"; shift ;;
    --readback) READBACK="$2"; shift ;;
    --print-root-cmd) ROOTLABEL="$2"; shift ;;
    --allow-empty-scan) ALLOW="--allow-empty-scan" ;;
    -h|--help) sed -n 2,9p "$0"; exit 0 ;;
    *) TEAM="$1" ;;
  esac
  shift
done

check_dir() {  # $1 = dir holding MANIFEST.json
  PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m prooflab.pack.build scan $ALLOW "$1" || { echo "REFUSED: scan not clean" >&2; return 1; }
  "$PY" "$MANIFEST" verify "$1" || { echo "REFUSED: manifest verify failed" >&2; return 1; }
}

if [ -n "$READBACK" ]; then
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  unzip -q "$READBACK" -d "$TMP" || { echo "REFUSED: cannot unzip" >&2; exit 1; }
  MF="$(find "$TMP" -name MANIFEST.json | head -1)"
  [ -n "$MF" ] || { echo "REFUSED: no MANIFEST.json in the zip" >&2; exit 1; }
  check_dir "$(dirname "$MF")" || exit 1
  PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}" "$PY" -m prooflab.pack.build scan $ALLOW "$TMP" || { echo "REFUSED: readback scan not clean" >&2; exit 1; }
  echo "READBACK OK"
  if [ -n "$ROOTLABEL" ]; then  # print only: the ops lane runs it, with the ServiceNow environment sourced there
    echo "PUBLISH ROOT (ops lane; prints only, posts nothing here), fill the two <...> values:"
    echo "  PYTHONPATH=$REPO $PY -m prooflab pack root --label $ROOTLABEL --zip $READBACK --s3-version-id <VERSION_ID_OF_THE_UPLOADED_ZIP> --incident-sys-id <INCIDENT_SYS_ID>"
    echo "  then upload the sidecar evidence/pack-root.json AFTER the pack (it is not in the MANIFEST)"
  fi
  exit 0
fi

[ -n "$TEAM" ] || { echo "usage: submit_wrapper.sh [--dry-run] [--evidence DIR] <team> | --readback <zip>" >&2; exit 2; }
check_dir "$EVID" || exit 1
SUBMIT="${SUBMIT_SH:-$(command -v submit.sh || true)}"
[ -n "$SUBMIT" ] || { echo "REFUSED: submit.sh not found (SUBMIT_SH or PATH)" >&2; exit 1; }
if [ "$DRY" = 1 ]; then echo "DRY-RUN: $SUBMIT $TEAM"; exit 0; fi
exec "$SUBMIT" "$TEAM"

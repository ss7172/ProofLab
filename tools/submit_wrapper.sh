#!/usr/bin/env bash
# Guarded submit and readback. The ops lane runs it under ~/firstmate-homes/TrustworthyAI/workshop-local/bin/hk
# (the scan script loads the exact secret values itself, through that environment; nothing is injected here).
#   submit_wrapper.sh [--dry-run] [--evidence DIR] [--workdir DIR] [--zip PREFLIGHT_ZIP] [<team>]
#       scan (staged evidence dir, workdir, unzipped preflight zip) + manifest verify, then submit.sh <team>
#   submit_wrapper.sh --readback <local-zip> [--bucket B] [--key K] [--workdir DIR] [--print-root-cmd <label>] [<team>]
#       head-object, get-object --if-match <ETag>, head-object again (same VersionId + ETag both times),
#       sha256 equal to the local zip, then manifest verify + scan on the UNZIPPED copy. Without --bucket:
#       the local zip only. (get-object --version-id is denied to the participant role.)
# Team defaults to ifabric; key defaults to submissions/<team>/<zip name>. Never posts anything itself.
# Scan = bash workshop-local/scripts/pre-push-secret-scan.sh (PROOFLAB_PREPUSH_SCAN overrides); needs RESULT: clean.
# Env: PROOFLAB_PYTHON (default python3), PROOFLAB_REPO, PROOFLAB_MANIFEST_PY, SUBMIT_SH, PROOFLAB_PREPUSH_SCAN.
set -u
export PYTHONDONTWRITEBYTECODE=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${PROOFLAB_REPO:-$(dirname "$HERE")}"
PY="${PROOFLAB_PYTHON:-python3}"
MANIFEST="${PROOFLAB_MANIFEST_PY:-$HERE/manifest.py}"
SCAN="${PROOFLAB_PREPUSH_SCAN:-$HOME/firstmate-homes/TrustworthyAI/workshop-local/scripts/pre-push-secret-scan.sh}"
TEAM_DEFAULT="ifabric"                       # the one place the team name lives (matches prooflab.pack.build.TEAM_NAME)
KEY_PREFIX_FMT="submissions/%s/"             # key layout: submissions/<team>/<zip name>
EVID="$HOME/evidence"; DRY=0; READBACK=""; TEAM=""; ROOTLABEL=""; WORKDIR=""; PZIP=""; BUCKET=""; KEY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --evidence) EVID="$2"; shift ;;
    --workdir) WORKDIR="$2"; shift ;;
    --zip) PZIP="$2"; shift ;;
    --bucket) BUCKET="$2"; shift ;;
    --key) KEY="$2"; shift ;;
    --readback) READBACK="$2"; shift ;;
    --print-root-cmd) ROOTLABEL="$2"; shift ;;
    -h|--help) sed -n 2,13p "$0"; exit 0 ;;
    *) TEAM="$1" ;;
  esac
  shift
done
TEAM="${TEAM:-$TEAM_DEFAULT}"

scan_dir() {  # $1 = dir; the scan script must exit 0 AND print RESULT: clean
  [ -f "$SCAN" ] || { echo "REFUSED: scan script not found: $SCAN" >&2; return 1; }
  local out; out="$(bash "$SCAN" "$1" 2>&1)"; local rc=$?
  if [ $rc -ne 0 ] || ! printf '%s\n' "$out" | grep -q '^RESULT: clean'; then
    echo "REFUSED: scan not clean on $1" >&2; printf '%s\n' "$out" | tail -n 8 >&2; return 1
  fi
  echo "scan clean: $1"
}
scan_zip() {  # $1 = zip; the scan cannot read inside zips, so scan an unzipped copy
  local t; t="$(mktemp -d)"
  unzip -q "$1" -d "$t" || { rm -rf "$t"; echo "REFUSED: cannot unzip $1" >&2; return 1; }
  scan_dir "$t" || { rm -rf "$t"; return 1; }
  UNZIPPED="$t"
}
verify_dir() {  # $1 = dir holding MANIFEST.json
  "$PY" "$MANIFEST" verify "$1" || { echo "REFUSED: manifest verify failed" >&2; return 1; }
}
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
strip_q() { printf '%s' "$1" | tr -d '"'; }
head_obj() {  # prints "<VersionId> <ETag>"
  aws s3api head-object --bucket "$BUCKET" --key "$KEY" --query '[VersionId,ETag]' --output text | awk '{print $1, $2}' | tr -d '"'
}

if [ -n "$READBACK" ]; then
  [ -f "$READBACK" ] || { echo "REFUSED: no such zip: $READBACK" >&2; exit 1; }
  GOT="$READBACK"; TMP="$(mktemp -d)"; trap 'rm -rf "$TMP" "${UNZIPPED:-}"' EXIT
  if [ -n "$BUCKET" ]; then
    KEY="${KEY:-$(printf "$KEY_PREFIX_FMT" "$TEAM")$(basename "$READBACK")}"
    B1="$(head_obj)" || { echo "REFUSED: head-object (before) failed" >&2; exit 1; }
    ETAG="${B1#* }"; [ -n "$ETAG" ] && [ "$ETAG" != "$B1" ] || { echo "REFUSED: no ETag from head-object" >&2; exit 1; }
    GOT="$TMP/readback.zip"
    aws s3api get-object --bucket "$BUCKET" --key "$KEY" --if-match "$ETAG" "$GOT" >/dev/null \
      || { echo "REFUSED: get-object --if-match failed" >&2; exit 1; }
    B2="$(head_obj)" || { echo "REFUSED: head-object (after) failed" >&2; exit 1; }
    [ "$B1" = "$B2" ] || { echo "REFUSED: VersionId/ETag changed during the download" >&2; exit 1; }
    echo "readback: VersionId and ETag identical before and after (${B1% *})"
    [ "$(sha "$GOT")" = "$(sha "$READBACK")" ] || { echo "REFUSED: downloaded sha256 differs from the local zip" >&2; exit 1; }
    echo "readback: sha256 equals the local zip"
  fi
  scan_zip "$GOT" || exit 1
  MF="$(find "$UNZIPPED" -name MANIFEST.json | head -1)"
  [ -n "$MF" ] || { echo "REFUSED: no MANIFEST.json in the zip" >&2; exit 1; }
  verify_dir "$(dirname "$MF")" || exit 1
  [ -z "$WORKDIR" ] || scan_dir "$WORKDIR" || exit 1
  echo "READBACK OK"
  if [ -n "$ROOTLABEL" ]; then  # print only: the ops lane runs it, with the ServiceNow environment sourced there
    echo "PUBLISH ROOT (ops lane; prints only, posts nothing here), fill the two <...> values:"
    echo "  PYTHONPATH=$REPO $PY -m prooflab pack root --label $ROOTLABEL --zip $READBACK --s3-version-id <VERSION_ID_OF_THE_UPLOADED_ZIP> --incident-sys-id <INCIDENT_SYS_ID>"
    echo "  then upload the sidecar evidence/pack-root.json AFTER the pack (it is not in the MANIFEST)"
  fi
  exit 0
fi

scan_dir "$EVID" || exit 1
[ -z "$WORKDIR" ] || scan_dir "$WORKDIR" || exit 1
if [ -n "$PZIP" ]; then scan_zip "$PZIP" || exit 1; rm -rf "$UNZIPPED"; fi
verify_dir "$EVID" || exit 1
SUBMIT="${SUBMIT_SH:-$(command -v submit.sh || true)}"
[ -n "$SUBMIT" ] || { echo "REFUSED: submit.sh not found (SUBMIT_SH or PATH)" >&2; exit 1; }
if [ "$DRY" = 1 ]; then echo "DRY-RUN: $SUBMIT $TEAM"; exit 0; fi
exec "$SUBMIT" "$TEAM"

#!/usr/bin/env bash
# build_ifabric_image.sh: the OPS-LANE runner for one ifabric- agent image (ARCH 7.1; 05 AR-03/AR-05).
#
# Input: a StartBuild request written OFFLINE by tools/ifabric_build_request.py (the env-override carrier
# proven by ops-lane/build-probe-report.md, 2026-10-06). This script is the only part that talks to AWS, and
# it uses the caller's environment as is: it never sources env.sh and never reads a credential file. The ops
# lane runs it inside its own wrapper, e.g.
#
#   ~/firstmate-homes/TrustworthyAI/workshop-local/bin/hk \
#     'bash tools/build_ifabric_image.sh --request <dir>/startbuild-ifabric-customer.json'
#
# Steps (each AWS read is narrowed with --query so no env value, i.e. no source payload, is ever printed):
#   1. ecr describe-images --image-ids imageTag=<tag>: REFUSE if the tag already exists (tags are never reused;
#      a reference tag can never get here: the request writer and this script both refuse them);
#   2. codebuild start-build --cli-input-json file://<request> --query build.id (a bare start-build echoes
#      the whole env, i.e. the source);
#   3. poll codebuild batch-get-builds --query (status / phase only) every 20 s, up to --timeout seconds;
#   4. logs filter-log-events on /aws/codebuild/<project>, the build's own stream, for the IFABRIC_PUSHED line;
#   5. ecr describe-images for the tag: the digest must equal the logged one;
#   6. writes URI_FILE = <repo uri>@sha256:<digest> (the CRD's form: never repo:tag@digest). The repo URI holds
#      the account id, so it goes to the file only; stdout shows the digest.
#
#   bash tools/build_ifabric_image.sh --request FILE [--uri-file PATH] [--region R] [--timeout S] [--dry-run]
#
# --dry-run prints the commands it would run (placeholders, no payload) and calls nothing.
# bash 3.2 compatible (macOS). Never `set -x`: the request file is the payload.
set -euo pipefail

REQUEST=""
URI_FILE=""
DRY_RUN=0
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
TIMEOUT=900
POLL=20
PY="${PYTHON:-python3}"

usage() { sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --request) REQUEST="${2:-}"; shift 2 ;;
    --uri-file) URI_FILE="${2:-}"; shift 2 ;;
    --region) REGION="${2:-}"; shift 2 ;;
    --timeout) TIMEOUT="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "build_ifabric_image: unknown argument '$1'" >&2; exit 2 ;;
  esac
done
[ -n "$REQUEST" ] || { echo "build_ifabric_image: --request FILE is required" >&2; exit 2; }
[ -f "$REQUEST" ] || { echo "build_ifabric_image: no request file at $REQUEST" >&2; exit 2; }
case "$TIMEOUT" in ''|*[!0-9]*) echo "build_ifabric_image: --timeout must be seconds" >&2; exit 2 ;; esac

# Read ONLY the routing fields (project, repo, tag, role) and re-check the gates; the payload stays in the file.
FIELDS=$("$PY" - "$REQUEST" <<'PY'
import json, re, sys
REF = ("reference-agent-v5", "reference-agent-v5-agentcore", "my-agent", "hackathon-helper", "latest")
req = json.load(open(sys.argv[1]))
env = dict((e["name"], e["value"]) for e in req.get("environmentVariablesOverride", []))
tag, repo, project = env.get("IFABRIC_TAG", ""), env.get("IFABRIC_REPO", ""), req.get("projectName", "")
bad = []
m = re.match(r"^ifabric-([a-z]+)-[0-9a-f]{7,40}$", tag)
if tag in REF or not m:
    bad.append("tag %r is not ifabric-<role>-<git sha> or is a reference tag" % tag)
if not re.match(r"^[a-z0-9][a-z0-9._/-]*$", repo) or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", project):
    bad.append("bad repo or project name")
if len(req.get("buildspecOverride", "")) > 25600:
    bad.append("buildspec over 25600 chars")
if any(len(v) > 44000 for v in env.values()) or sum(len(k) + len(v) for k, v in env.items()) > 44000:
    bad.append("env overrides over the 44000-char gate")
if "IFABRIC_ROLE_B64" not in env or "IFABRIC_ROLE_SHA256" not in env:
    bad.append("no IFABRIC_ROLE_B64/SHA256 pair")
if req.get("environmentTypeOverride") != "ARM_CONTAINER":
    bad.append("not an ARM_CONTAINER build")
if bad:
    sys.stderr.write("build_ifabric_image: REFUSED: " + "; ".join(bad) + "\n")
    sys.exit(2)
print(project, repo, tag, m.group(1))
PY
) || exit 2
read -r PROJECT REPO TAG ROLE <<EOF
$FIELDS
EOF
# One name, shared with tools/make_ifabric_agents.py (_read_uri): /tmp/ifabric-image-uri-<role>; the base image
# keeps /tmp/ifabric-base-image-uri.
if [ "$ROLE" = "base" ]; then DEFAULT_URI_FILE="/tmp/ifabric-base-image-uri"; else DEFAULT_URI_FILE="/tmp/ifabric-image-uri-${ROLE}"; fi
URI_FILE="${URI_FILE:-$DEFAULT_URI_FILE}"
LOG_GROUP="/aws/codebuild/${PROJECT}"

if [ "$DRY_RUN" = "1" ]; then
  R="${REGION:-<region>}"
  echo "=== DRY RUN: role=$ROLE tag=$TAG project=$PROJECT repo=$REPO (nothing is called) ==="
  echo "# 1. refuse if the tag exists (ImageNotFoundException = proceed):"
  echo "aws ecr describe-images --region $R --repository-name $REPO --image-ids imageTag=$TAG --query 'imageDetails[0].imageDigest' --output text"
  echo "# 2. start (the request carries the source as env overrides; --query keeps it off stdout):"
  echo "aws codebuild start-build --region $R --cli-input-json file://$REQUEST --query 'build.id' --output text"
  echo "# 3. poll every ${POLL}s, up to ${TIMEOUT}s (status and phase only, never the env):"
  echo "aws codebuild batch-get-builds --region $R --ids <build id> --query 'builds[0].[buildStatus,currentPhase]' --output text"
  echo "#    on failure: aws codebuild batch-get-builds --region $R --ids <build id> --query 'builds[0].phases[].[phaseType,phaseStatus,durationInSeconds]' --output text"
  echo "# 4. the pushed digest from the build's own log stream (<build id> after the colon):"
  echo "aws logs filter-log-events --region $R --log-group-name $LOG_GROUP --log-stream-names <stream> --filter-pattern IFABRIC_PUSHED --query 'events[].message' --output text"
  echo "# 5. confirm with ECR (must equal the logged digest):"
  echo "aws ecr describe-images --region $R --repository-name $REPO --image-ids imageTag=$TAG --query 'imageDetails[0].imageDigest' --output text"
  echo "aws ecr describe-repositories --region $R --repository-names $REPO --query 'repositories[0].repositoryUri' --output text"
  echo "# 6. would write <repo uri>@<digest> -> $URI_FILE"
  exit 0
fi

[ -n "$REGION" ] || { echo "build_ifabric_image: set AWS_REGION or pass --region" >&2; exit 2; }

# 1. The tag must not exist yet.
ERR=$(mktemp)
trap 'rm -f "$ERR"' EXIT
if EXISTING=$(aws ecr describe-images --region "$REGION" --repository-name "$REPO" --image-ids imageTag="$TAG" \
    --query 'imageDetails[0].imageDigest' --output text 2>"$ERR"); then
  echo "build_ifabric_image: REFUSED: $REPO:$TAG already exists ($EXISTING); tags are never reused" >&2
  exit 3
elif ! grep -q ImageNotFoundException "$ERR"; then
  echo "build_ifabric_image: describe-images failed (not a missing tag); not starting a build:" >&2
  sed 's/[0-9]\{12\}/<acct>/g' "$ERR" >&2
  exit 1
fi

# 2. Start.
BID=$(aws codebuild start-build --region "$REGION" --cli-input-json "file://$REQUEST" --query 'build.id' --output text)
case "$BID" in "$PROJECT":*) ;; *) echo "build_ifabric_image: unexpected build id '$BID'" >&2; exit 1 ;; esac
echo "build: $BID  (role=$ROLE tag=$TAG)"

# 3. Poll.
START=$(date +%s)
while :; do
  S=$(aws codebuild batch-get-builds --region "$REGION" --ids "$BID" \
      --query 'builds[0].[buildStatus,currentPhase]' --output text)
  STATUS=${S%%[[:space:]]*}
  [ "$STATUS" != "IN_PROGRESS" ] && break
  if [ $(( $(date +%s) - START )) -ge "$TIMEOUT" ]; then
    echo "build_ifabric_image: still IN_PROGRESS after ${TIMEOUT}s ($S); not publishing. Build: $BID" >&2
    exit 1
  fi
  sleep "$POLL"
done
echo "status: $S  ($(( $(date +%s) - START ))s)"
if [ "$STATUS" != "SUCCEEDED" ]; then
  aws codebuild batch-get-builds --region "$REGION" --ids "$BID" \
    --query 'builds[0].phases[].[phaseType,phaseStatus,durationInSeconds]' --output text >&2 || true
  echo "build_ifabric_image: build $STATUS; see $LOG_GROUP stream ${BID#*:}; nothing written to $URI_FILE" >&2
  exit 1
fi

# 4. The digest the build pushed, from its own log stream.
STREAM="${BID#*:}"
LOGGED=$(aws logs filter-log-events --region "$REGION" --log-group-name "$LOG_GROUP" --log-stream-names "$STREAM" \
  --filter-pattern IFABRIC_PUSHED --query 'events[].message' --output text \
  | tr '\t' '\n' | sed -n 's/^.*IFABRIC_PUSHED \(sha256:[0-9a-f]\{64\}\).*$/\1/p' | tail -1)
case "$LOGGED" in
  sha256:*) ;;
  *) echo "build_ifabric_image: no IFABRIC_PUSHED digest in $LOG_GROUP/$STREAM; nothing written" >&2; exit 1 ;;
esac

# 5. ECR agrees.
DIGEST=$(aws ecr describe-images --region "$REGION" --repository-name "$REPO" --image-ids imageTag="$TAG" \
  --query 'imageDetails[0].imageDigest' --output text)
if [ "$DIGEST" != "$LOGGED" ]; then
  echo "build_ifabric_image: ECR digest '$DIGEST' != logged '$LOGGED' for $TAG; nothing written" >&2
  exit 1
fi

# 6. repo@sha256 into URI_FILE; the URI (account id inside) never goes to stdout.
URI=$(aws ecr describe-repositories --region "$REGION" --repository-names "$REPO" \
  --query 'repositories[0].repositoryUri' --output text)
case "$URI" in */"$REPO") ;; *) echo "build_ifabric_image: unexpected repository URI shape" >&2; exit 1 ;; esac
umask 077
printf '%s@%s\n' "$URI" "$DIGEST" > "$URI_FILE"
echo "pushed: $REPO:$TAG = $DIGEST"
echo "wrote $URI_FILE (<repo uri>@$DIGEST)"

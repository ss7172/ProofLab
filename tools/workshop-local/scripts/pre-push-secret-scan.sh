#!/usr/bin/env bash
# pre-push-secret-scan.sh [repo-dir] — READ-ONLY. Run before every `git push`.
# 1. pattern scan (AWS key ids, private keys, tkn=, bearer/GitHub/OpenAI-style tokens)
# 2. exact-value scan: loads the real workshop secrets into variables (never printed)
#    and checks that none appears in any file. Exits 1 if anything is found.
set -u
REPO="${1:-.}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$HERE/env.sh" >/dev/null 2>&1
fail=0
echo "== pattern scan: $REPO =="
hits=$(grep -rIlE "(AKIA|ASIA)[A-Z0-9]{16}|aws_secret_access_key|aws_session_token|tkn=|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|github_pat_|sk-[A-Za-z0-9]{20,}|xox[bap]-[A-Za-z0-9-]{10,}|Bearer [A-Za-z0-9._~+/=-]{20,}" --exclude-dir=.git --exclude=pre-push-secret-scan.sh "$REPO")
if [ -n "$hits" ]; then echo "$hits" | sed 's/^/   HIT: /'; fail=1; else echo "   clean"; fi
echo "== exact secret values (never printed) =="
check() { local name="$1" val="$2"
  if [ -z "$val" ] || [ "${#val}" -lt 8 ]; then echo "   $name: COULD NOT LOAD — scan inconclusive"; fail=1; return; fi
  n=$(grep -rIlF --exclude-dir=.git -- "$val" "$REPO" | wc -l | tr -d ' ')
  echo "   $name: $n file(s)"; [ "$n" = 0 ] || fail=1; }
check "gateway API key" "$(cat /tmp/modaas-token 2>/dev/null)"
check "ledger write token" "$(kubectl get agentconfig hackathon-helper -n components -o json 2>/dev/null | python3 -c 'import json,sys
e=json.load(sys.stdin)["spec"]["awsAgentCore"]["environmentVariables"]
print(e.get("AUDIT_WRITE_TOKEN","") if isinstance(e,dict) else next((x.get("value","") for x in e if x.get("name")=="AUDIT_WRITE_TOKEN"),""))' 2>/dev/null)"
for k in aws_access_key_id aws_secret_access_key aws_session_token; do check "AWS $k" "$(aws configure get $k --profile hackathon 2>/dev/null)"; done
for K in CockpitUrl IdeUrl; do
  U=$(aws cloudformation describe-stacks --stack-name a-02-code-editor --query "Stacks[0].Outputs[?OutputKey==\`$K\`].OutputValue" --output text 2>/dev/null)
  check "$K" "$U"; check "$K token" "$(printf '%s' "$U" | sed -nE 's/.*[?&](tkn|token|folder|t)=([^&]+).*/\2/p')"
done
echo "== large files (>5 MB) =="; big=$(find "$REPO" -path "$REPO/.git" -prune -o -type f -size +5M -print); [ -n "$big" ] && { echo "$big" | sed 's/^/   /'; fail=1; } || echo "   none"
[ $fail = 0 ] && echo "RESULT: clean" || echo "RESULT: NOT CLEAN (a hit, or a value that could not be checked) — do not push"
exit $fail

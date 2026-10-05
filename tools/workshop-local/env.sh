#!/usr/bin/env bash
# Local stand-in for the workshop IDE's shell. Source it from bash:
#   source ~/firstmate-homes/TrustworthyAI/workshop-local/env.sh
# Gives the same variables the IDE gets from /etc/profile.d/modaas-team.sh
# and rehydrate.sh, using the participant creds in the `hackathon` profile.

_HK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Must be set before rehydrate.sh, which runs `aws eks update-kubeconfig`
# and would otherwise write into ~/.kube/config.
export AWS_PROFILE=hackathon
export KUBECONFIG="$HOME/.kube/hackathon-config"

# kubectl 1.36 + helm 3.22 (the IDE's versions), Python 3.12 venv with the kit's
# pinned agent SDKs, and the starter kit's helpers, hackathon shells only.
export VIRTUAL_ENV="$_HK_ROOT/workshop-local/.venv"
export PATH="$_HK_ROOT/workshop-local/bin:$VIRTUAL_ENV/bin:$_HK_ROOT/workshop-assets/starter:$PATH"
export REFERENCE_IMPL="$_HK_ROOT/workshop-assets/reference-impl"

source "$_HK_ROOT/workshop-assets/scripts/rehydrate.sh"
# rehydrate.sh prepends ~/bin; keep the pinned kubectl/helm first.
export PATH="$_HK_ROOT/workshop-local/bin:$PATH"

# Written to ConfigMaps by bootstrap-platform.sh.
export TEAM="$(kubectl get cm workshop-identity -n modaas-system -o jsonpath='{.data.team}' 2>/dev/null)"
export MODAAS_GATEWAY_ID="$(kubectl get cm modaas-gateway -n modaas-system -o jsonpath='{.data.gatewayId}' 2>/dev/null)"
export TEAM_EVIDENCE_BUCKET="team-evidence-${ACCOUNT_ID}"

printf '  TEAM          %s\n' "${TEAM:-<unset>}"
printf '  GATEWAY_ID    %s\n' "${MODAAS_GATEWAY_ID:-<unset>}"
printf '  EVIDENCE      %s\n' "$TEAM_EVIDENCE_BUCKET"
unset _HK_ROOT

#!/usr/bin/env bash
# findings-recheck.sh — READ-ONLY live re-check of TrustworthyAI-iFabric/notes/platform-observations.md
# items #1, #3 (configuration only), #4, #5, #6, #8, #10, #12, #14 and #15.
# NOT covered: #2 (needs a request to the public gateway), #3's live test (side-entrance-probe.sh,
# which creates pods), #7 (design note), #9 (needs an unapproved model + a call), #11 (guide robustness),
# #13 (documented limitation; nothing live to check).
# Makes no changes: only kubectl get/auth can-i/logs/exec-free reads and aws describe calls.
# Never prints the gateway key, the audit write token or bearer URLs.
# Usage:  bash ~/firstmate-homes/TrustworthyAI/workshop-local/scripts/findings-recheck.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../env.sh" >/dev/null 2>&1
ASSETS="$HERE/../../workshop-assets"
hdr() { printf '\n== %s ==\n' "$1"; }

hdr "#1  M3 control-plane checkpoint (guide awk vs corrected)"
echo "  guide awk prints:     $(kubectl get deploy -n modaas-system --no-headers | awk '$2 != $4 {found++} END {print found+0}')   (bug if non-zero while all are ready)"
echo "  corrected prints:     $(kubectl get deploy -n modaas-system --no-headers | awk '{split($2,r,"/"); if (r[1] != r[2]) found++} END {print found+0}')"

hdr "#3  side entrance — configuration that allows it (run side-entrance-probe.sh for the live test)"
kubectl get networkpolicy -A -o custom-columns='  NS:.metadata.namespace,NAME:.metadata.name,TYPES:.spec.policyTypes' --no-headers
echo "  components egress rule to all components pods: $(kubectl get networkpolicy components-egress-governed-only -n components -o jsonpath='{.spec.egress[*].to[*].podSelector}')"
echo "  Istio AuthorizationPolicies: $(kubectl get authorizationpolicies.security.istio.io -A --no-headers 2>/dev/null | wc -l | tr -d ' ')   PeerAuthentications: $(kubectl get peerauthentications.security.istio.io -A --no-headers 2>/dev/null | wc -l | tr -d ' ')"
echo "  participant can create pods in default: $(kubectl auth can-i create pods -n default)   portforward in components: $(kubectl auth can-i create pods/portforward -n components)"

hdr "#4  ModelConfig versions: served/storage"
kubectl get crd modelconfigs.oda.tmforum.org -o jsonpath='{range .spec.versions[*]}  {.name} served={.served} storage={.storage}{"\n"}{end}'

hdr "#5/#6  guide drift: live counts"
echo "  ModelConfigs: $(kubectl get modelconfig -n components --no-headers | wc -l | tr -d ' ')   ToolConfigs: $(kubectl get toolconfig -n components --no-headers | wc -l | tr -d ' ')   gateway policies: $(kubectl get agentgatewaypolicy -n agentgateway-system --no-headers | wc -l | tr -d ' ')   bootstrap steps: $(grep -cE '^step "[0-9]+/18' "$ASSETS/scripts/bootstrap-platform.sh")"

hdr "#8  gateway policy contents (which one holds auth?)"
kubectl get agentgatewaypolicy -n agentgateway-system -o json | python3 -c '
import json,sys
for p in json.load(sys.stdin)["items"]:
    s=p["spec"]; keys={k:(sorted(v) if isinstance(v,dict) else v) for k,v in s.items() if k!="targetRefs"}
    secs=[t.get("sectionName") or "<all>" for t in s.get("targetRefs",[])]
    print("  %-24s targets=%-16s %s" % (p["metadata"]["name"], ",".join(secs), json.dumps(keys)))'
echo "  modaas-authz failureMode: $(kubectl get agentgatewaypolicy modaas-authz -n agentgateway-system -o jsonpath='{.spec.traffic.extAuth.failureMode}')"

hdr "#10 audit-store write gate"
echo "  AUDIT_WRITE_TOKEN source: $(kubectl get deploy audit-store -n components -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="AUDIT_WRITE_TOKEN")].valueFrom.secretKeyRef.name}')"
echo "  deployed store.py identical to kit audit-store.py: $(kubectl get cm audit-store-app -n components -o json | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(next(iter(d.values()))==open('$ASSETS/reference-impl/audit-store.py').read())")"
echo "  participant can read the write token secret: $(kubectl auth can-i get secret/audit-write-token -n components)"

hdr "#12 approvals: identity + signature; EKS audit logging"
for k in modelconfig toolconfig agentconfig; do
  kubectl get $k -n components -o jsonpath='{range .items[*]}  {.metadata.name}: subject={.status.governance.approvals[*].subject} signature=[{.status.governance.approvals[*].signature}]{"\n"}{end}'
done
echo "  EKS control-plane logging enabled types: [$(aws eks describe-cluster --name "${CLUSTER:-a-01-eks-cluster-modaas}" --query 'cluster.logging.clusterLogging[?enabled].types[]' --output text 2>&1)]  (empty = all off)"

hdr "#14 operator error-event noise (components)"
kubectl get events -n components --field-selector type=Error -o jsonpath='{range .items[*]}{.count} {.message}{"\n"}{end}' 2>/dev/null | cut -c1-60 | sort | uniq -c | sort -rn | head -4 | sed 's/^/  /'
echo "  canvas api-operator-istio UnboundLocalError lines (24h): $(kubectl logs deploy/api-operator-istio -n canvas --since=24h 2>/dev/null | grep -c UnboundLocalError)"

hdr "#15 status says AuthorizationPolicy emitted vs what exists"
claims=0
for k in toolconfig modelconfig agentconfig; do
  n=$(kubectl get $k -n components -o json | python3 -c '
import json,sys
print(sum(1 for o in json.load(sys.stdin)["items"] for c in o.get("status",{}).get("conditions",[])
      if c.get("type")=="IstioPerAssetProvisioned" and c.get("status")=="True" and "AuthorizationPolicy emitted" in (c.get("message") or "")))')
  claims=$((claims+n))
done
echo "  assets claiming 'AuthorizationPolicy emitted': $claims   AuthorizationPolicies that exist: $(kubectl get authorizationpolicies.security.istio.io -A --no-headers 2>/dev/null | wc -l | tr -d ' ')   VirtualServices: $(kubectl get virtualservices.networking.istio.io -A --no-headers 2>/dev/null | wc -l | tr -d ' ')"
echo "  MODAAS_PER_ASSET_AUTHZ on tool operator: [$(kubectl get deploy aws-tool-operator -n modaas-system -o jsonpath='{.spec.template.spec.containers[*].env[?(@.name=="MODAAS_PER_ASSET_AUTHZ")].value}')]  (empty = default off)"
echo
echo "checked at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

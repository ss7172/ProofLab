#!/usr/bin/env bash
# READ-ONLY glossary verification checks. Only kubectl get/explain/logs and aws describe/get/list.
# Usage: bash glossary-checks.sh <section>   (A=phases B=cedar C=runid D=aws)
set -u
command -v jq >/dev/null || { echo "NO JQ"; exit 1; }
redact() { sed -E 's/((authorization|token|secret|api[_-]?key|password)[A-Za-z_.-]*[=:] *)[^ ,}]+/\1<redacted>/Ig'; }

case "${1:-}" in
A)
  echo "== kubectl client version =="; kubectl version --client 2>/dev/null | head -2
  echo "== live phases (KIND NS NAME PHASE) =="
  kubectl get modelconfigs,toolconfigs,agentconfigs,registries -A --no-headers \
    -o custom-columns='KIND:.kind,NS:.metadata.namespace,NAME:.metadata.name,PHASE:.status.phase'
  echo "== phase counts =="
  kubectl get modelconfigs,toolconfigs,agentconfigs,registries -A --no-headers \
    -o custom-columns='KIND:.kind,PHASE:.status.phase' | sort | uniq -c
  for r in modelconfig toolconfig agentconfig registry; do
    echo "== kubectl explain $r.status.phase =="
    kubectl explain "$r.status.phase" 2>&1 | sed -n '1,20p'
  done
  for c in modelconfigs toolconfigs agentconfigs registries; do
    echo "== CRD $c served versions: status.phase schema =="
    kubectl get crd "$c.oda.tmforum.org" -o json | jq -c '.spec.versions[] | select(.served) | {v:.name, phase:.schema.openAPIV3Schema.properties.status.properties.phase}'
  done
  echo "== phase words anywhere in the 4 MoDaaS CRDs =="
  kubectl get crd modelconfigs.oda.tmforum.org toolconfigs.oda.tmforum.org agentconfigs.oda.tmforum.org registries.oda.tmforum.org -o json \
    | grep -o -E '\b(Reviewing|Approved|Paused|Revoking|Revoked|Rejected|Pending|Failed|Provisioning|Ready|Deprecated|Suspended|Draft|Retired)\b' | sort | uniq -c
  ;;
B)
  echo "== ConfigMaps labelled app.kubernetes.io/part-of=modaas-pdp (all namespaces) =="
  kubectl get cm -A -l app.kubernetes.io/part-of=modaas-pdp -o json | jq -r '.items[] |
    "\(.metadata.namespace)/\(.metadata.name) keys=\((.data // {})|keys|join(",")) owner=\((.metadata.ownerReferences // [])|map("\(.kind)/\(.name)")|join(",")) managedBy=\(.metadata.labels["app.kubernetes.io/managed-by"] // "-") created=\(.metadata.creationTimestamp)"'
  echo "== model* ConfigMaps: first line, and principal/permit lines =="
  kubectl get cm -n modaas-system -l app.kubernetes.io/part-of=modaas-pdp -o json | jq -r '.items[] | select(.metadata.name|test("model")) | .metadata.name as $n | (.data // {}) | to_entries[] |
    "\($n) [\(.key)]\n  line1: \(.value|split("\n")[0])\n  permit/principal lines: \(.value|split("\n")|map(select(test("permit|forbid|principal")))|join(" || ")|.[0:600])"'
  echo "== ModelConfig declared consumers (any spec path containing consumer) + phase =="
  kubectl get modelconfigs -A -o json | jq -c '.items[] | {ns:.metadata.namespace, name:.metadata.name, phase:.status.phase,
    consumers:[.spec | paths as $p | select($p|map(tostring)|join(".")|test("consumer";"i")) | {path:($p|map(tostring)|join(".")), val:getpath($p)} | select((.val|type)!="object")]}'
  echo "== modaas-pdp: who loads policies (last 'loaded policy' lines, 48h) =="
  kubectl -n modaas-system logs deploy/modaas-pdp --since=48h 2>/dev/null | grep -E 'loaded policy' | tail -n 12 | cut -c1-220
  echo "== modaas-pdp: decisions by policy_id (48h, one replica) =="
  kubectl -n modaas-system logs deploy/modaas-pdp --since=48h 2>/dev/null | grep -E 'decide' | grep -o -E 'policy_id=[^ ]+' | sort | uniq -c | sort -rn | head -20
  echo "== aws-model-operator log mentions of cedar/policy/configmap (48h, last 10) =="
  kubectl -n modaas-system logs deploy/aws-model-operator --since=48h 2>/dev/null | grep -i -E 'cedar|configmap|policy' | tail -n 10 | cut -c1-220 | redact
  ;;
C)
  echo "== page command: logs deploy/modaas-agw --since=24h | grep -m3 'modaas.run_id=' (selected fields) =="
  kubectl -n agentgateway-system logs deploy/modaas-agw --since=24h 2>/dev/null | grep -m3 'modaas.run_id=' | while IFS= read -r line; do
    echo "--- ts: $(echo "$line" | cut -c1-30)"
    echo "$line" | grep -o -E '(modaas\.[a-z_]+|trace\.id|span\.id|trace_id|baggage|traceparent|route|gen_ai\.request\.model|http\.path|listener)=("[^"]*"|[^ ]*)' | redact
  done
  echo "== all 24h lines with modaas.run_id: run_id shape vs trace ids =="
  kubectl -n agentgateway-system logs deploy/modaas-agw --since=24h 2>/dev/null | grep 'modaas.run_id=' | awk '
    { rid=""; tid=""; mtid="";
      for (i=1;i<=NF;i++) {
        if ($i ~ /^modaas\.run_id=/) rid=substr($i, index($i,"=")+1);
        else if ($i ~ /^trace\.id=/) tid=substr($i, index($i,"=")+1);
        else if ($i ~ /^modaas\.trace_id=/) mtid=substr($i, index($i,"=")+1);
      }
      gsub(/"/,"",rid); gsub(/"/,"",tid); gsub(/"/,"",mtid);
      shape = (rid=="") ? "empty" : ((length(rid)==32 && rid !~ /[^0-9a-f]/) ? "hex32" : "other");
      eq = (rid!="" && rid==tid) ? "eq_trace.id" : ((rid!="" && rid==mtid) ? "eq_modaas.trace_id" : "neq_both");
      n[shape" "eq]++;
      if (!(rid in seen) && ns<6) { seen[rid]=1; ns++; ex[ns]="run_id=" rid "  trace.id=" tid "  modaas.trace_id=" mtid }
    }
    END { for (k in n) print n[k], k; print "examples:"; for (i=1;i<=ns;i++) print "  " ex[i] }'
  echo "== pods behind deploy/modaas-agw =="
  kubectl -n agentgateway-system get pods --no-headers -o custom-columns='NAME:.metadata.name,START:.status.startTime,RESTARTS:.status.containerStatuses[0].restartCount' | grep modaas-agw
  echo "== where modaas.run_id is defined (agentgateway.dev policies, run_id/trace_id lines only) =="
  for crd in $(kubectl get crd -o name | grep 'agentgateway.dev' | sed 's#.*/##'); do
    for obj in $(kubectl get "$crd" -A --no-headers -o custom-columns='NS:.metadata.namespace,N:.metadata.name' 2>/dev/null | awk '{print $1"/"$2}'); do
      ns=${obj%%/*}; nm=${obj#*/}
      hits=$(kubectl -n "$ns" get "$crd" "$nm" -o yaml 2>/dev/null | grep -n -i -E 'run_id|modaas\.trace_id|baggage|correlation' | cut -c1-240 | redact)
      [ -n "$hits" ] && { echo "-- $crd $ns/$nm"; echo "$hits"; }
    done
  done
  ;;
D)
  echo "== caller =="; aws sts get-caller-identity --query 'Arn' --output text | sed -E 's/[0-9]{12}/<acct>/'
  echo "== AgentCore gateways =="
  aws bedrock-agentcore-control list-gateways --query 'items[].{id:gatewayId,name:name,status:status}' --output text
  for gid in $(aws bedrock-agentcore-control list-gateways --query 'items[].gatewayId' --output text); do
    echo "-- get-gateway $gid (auth/proto + authorizerConfiguration keys)"
    aws bedrock-agentcore-control get-gateway --gateway-identifier "$gid" --query '{auth:authorizerType,proto:protocolType,authCfgKeys:keys(authorizerConfiguration || `{}`)}' --output json | jq -c .
    for tid in $(aws bedrock-agentcore-control list-gateway-targets --gateway-identifier "$gid" --query 'items[].targetId' --output text); do
      echo "   target $tid:"
      aws bedrock-agentcore-control get-gateway-target --gateway-identifier "$gid" --target-id "$tid" \
        --query '{name:name,status:status,cred:credentialProviderConfigurations[].credentialProviderType,targetKind:keys(targetConfiguration.mcp || `{}`)}' --output json | jq -c .
    done
  done
  echo "== log group /aws/modaas/gateway =="
  aws logs describe-log-groups --log-group-name-prefix /aws/modaas/gateway --query 'logGroups[].[logGroupName,retentionInDays,storedBytes]' --output text
  echo "== log groups /aws/bedrock-agentcore/runtimes/ =="
  aws logs describe-log-groups --log-group-name-prefix /aws/bedrock-agentcore/runtimes/ --query 'logGroups[].[logGroupName,retentionInDays]' --output text
  echo "== AgentCore runtimes =="
  aws bedrock-agentcore-control list-agent-runtimes --query 'agentRuntimes[].[agentRuntimeId,agentRuntimeName,status]' --output text
  echo "== other modaas log groups (context) =="
  aws logs describe-log-groups --log-group-name-prefix /modaas --query 'logGroups[].logGroupName' --output text
  echo "== caller role policies (IAM read; may be denied) =="
  role=$(aws sts get-caller-identity --query 'Arn' --output text | sed -E 's#.*:assumed-role/([^/]+)/.*#\1#')
  echo "role=$role"
  aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[].PolicyName' --output text 2>&1 | head -3
  aws iam list-role-policies --role-name "$role" --query 'PolicyNames' --output text 2>&1 | head -3
  ;;
E)
  echo "== AgentConfig AUDIT_WRITE_TOKEN env: literal vs secretRef (value never printed) =="
  kubectl get agentconfigs -A -o json | jq -r '.items[] | .metadata.name as $n
    | (.spec.awsAgentCore.environmentVariables // null) as $e
    | if $e == null then "\($n) no environmentVariables"
      elif ($e|type)=="object" then "\($n) map: present=\($e|has("AUDIT_WRITE_TOKEN")) valueType=\($e.AUDIT_WRITE_TOKEN|type) len=\(($e.AUDIT_WRITE_TOKEN // "")|tostring|length)"
      else ($e|map(select(.name=="AUDIT_WRITE_TOKEN"))|.[0]) as $t | "\($n) list: present=\($t!=null) literalType=\(($t.value // null)|type) len=\(($t.value // "")|tostring|length) valueFrom=\(($t.valueFrom // null)!=null)" end'
  echo "== access-log / telemetry-export policies: generation + managedFields times =="
  kubectl -n agentgateway-system get agentgatewaypolicies modaas-telemetry-export modaas-access-log -o json | jq -r '.items[] |
    "\(.metadata.name) created=\(.metadata.creationTimestamp) gen=\(.metadata.generation) managed=\([.metadata.managedFields[]? | "\(.manager)@\(.time)"]|join(","))"'
  echo "== attribute names each policy adds =="
  kubectl -n agentgateway-system get agentgatewaypolicies modaas-telemetry-export modaas-access-log -o json | jq -c '.items[] | {p:.metadata.name, attrs:[.spec | .. | objects | select(has("name") and has("expression")) | "\(.name)<-\(.expression)"]}'
  echo "== notes: agent runtime role deny context + IDE role mentions =="
  N=/Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/TrustworthyAI-iFabric/notes/platform-observations.md
  sed -n '893,905p' "$N" | cut -c1-260
  grep -n -E 'IDE role|IDE.s role|instance role|code-server' "$N" | cut -c1-220 | head -8
  ;;
F)
  echo "== /aws/modaas/gateway streams =="
  aws logs describe-log-streams --log-group-name /aws/modaas/gateway --order-by LastEventTime --descending --limit 5 \
    --query 'logStreams[].[logStreamName,lastEventTimestamp]' --output text
  for s in $(aws logs describe-log-streams --log-group-name /aws/modaas/gateway --order-by LastEventTime --descending --limit 5 --query 'logStreams[].logStreamName' --output text); do
    echo "-- stream $s: newest 200 events"
    aws logs get-log-events --log-group-name /aws/modaas/gateway --log-stream-name "$s" --no-start-from-head --limit 200 --output json | jq -r '
      (.events|length) as $n
      | ([.events[] | select(.message|test("modaas\\.run_id"))]|length) as $r
      | ([.events[] | select(.message|test("modaas\\.(trace_id|action_id)"))]|length) as $m
      | ([.events[] | select(.message|test("trace_id"))]|length) as $t
      | ((.events|map(.timestamp)|max) // 0) as $last
      | "events=\($n) with_modaas.run_id=\($r) with_modaas.trace/action_id=\($m) with_trace_id=\($t) newest=\(if $last>0 then ($last/1000|floor|todate) else "-" end)"'
  done
  echo "== WSParticipantRole: bedrock-related statements in attached managed policies =="
  for arn in $(aws iam list-attached-role-policies --role-name WSParticipantRole --query 'AttachedPolicies[].PolicyArn' --output text); do
    v=$(aws iam get-policy --policy-arn "$arn" --query 'Policy.DefaultVersionId' --output text 2>&1)
    echo "-- ${arn##*/} ($v)"
    aws iam get-policy-version --policy-arn "$arn" --version-id "$v" --query 'PolicyVersion.Document' --output json 2>&1 | jq -c '[(.Statement | if type=="array" then .[] else . end) | select(((.Action // .NotAction)|tostring)|test("bedrock";"i")) | {Sid, Effect, Action:(.Action // null), NotAction:(.NotAction // null), Resource}]' 2>&1 | cut -c1-1500
  done
  echo "== WSParticipantRole inline policies =="
  for p in $(aws iam list-role-policies --role-name WSParticipantRole --query 'PolicyNames' --output text); do
    echo "-- $p"
    aws iam get-role-policy --role-name WSParticipantRole --policy-name "$p" --query 'PolicyDocument' --output json 2>&1 | jq -c '[(.Statement | if type=="array" then .[] else . end) | select(((.Action // .NotAction)|tostring)|test("bedrock";"i")) | {Sid, Effect, Action:(.Action // null), Resource}]' 2>&1 | cut -c1-1500
  done
  echo "== roles that look like an IDE role =="
  aws iam list-roles --query "Roles[?contains(RoleName,'IDE') || contains(RoleName,'Ide') || contains(RoleName,'-ide') || contains(RoleName,'ide-') || contains(RoleName,'VSCode') || contains(RoleName,'CodeServer')].RoleName" --output text 2>&1 | head -5
  ;;
G)
  R=$(aws iam list-roles --query "Roles[?contains(RoleName,'IdeInstanceRole')].RoleName" --output text | head -1)
  echo "== IDE role: $R =="
  F='[(.Statement | if type=="array" then .[] else . end) | select((((.Action // .NotAction)|tostring)|test("bedrock|\"\\*\"|^\\*$";"i"))) | {Sid, Effect, Action:(.Action // null), NotAction:(.NotAction // null), Resource}]'
  for arn in $(aws iam list-attached-role-policies --role-name "$R" --query 'AttachedPolicies[].PolicyArn' --output text); do
    v=$(aws iam get-policy --policy-arn "$arn" --query 'Policy.DefaultVersionId' --output text 2>&1)
    echo "-- attached ${arn##*/} ($v)"
    aws iam get-policy-version --policy-arn "$arn" --version-id "$v" --query 'PolicyVersion.Document' --output json 2>&1 | jq -c "$F" 2>&1 | cut -c1-900
  done
  for p in $(aws iam list-role-policies --role-name "$R" --query 'PolicyNames' --output text); do
    echo "-- inline $p"
    aws iam get-role-policy --role-name "$R" --policy-name "$p" --query 'PolicyDocument' --output json 2>&1 | jq -c "$F" 2>&1 | cut -c1-900
  done
  ;;
*) echo "usage: $0 A|B|C|D|E|F|G"; exit 2;;
esac

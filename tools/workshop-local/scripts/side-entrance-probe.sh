#!/usr/bin/env bash
# side-entrance-probe.sh — evidence for notes/platform-observations.md item #3.
# Sends the same UNAUTHENTICATED MCP `initialize` three ways and prints only the
# HTTP status and whether an Mcp-Session-Id came back:
#   A. pod in `default`    -> gateway /mcp/modaas-docs        (expect 403)
#   A. pod in `default`    -> modaas-docs-mcp.components:8080  (observed 200 + session)
#   B. pod in `components` -> modaas-docs-mcp.components:8080  (observed 200 + session)
# CHANGES THE CLUSTER: creates two throwaway curl pods (deleted afterwards).
# Ask the user before running. Run from the workshop environment:
#   bash -c 'source ~/firstmate-homes/TrustworthyAI/workshop-local/env.sh >/dev/null 2>&1; bash ~/firstmate-homes/TrustworthyAI/workshop-local/scripts/side-entrance-probe.sh'
# First run: 2026-10-05 ~00:40 UTC — A: 403 / 200+session, B: 200+session.
# Same unauthenticated MCP initialize, three paths. Prints only the status line and whether a session id came back.
PROBE='for U in "$@"; do
  echo "--> $U"
  curl -s -m 10 -o /dev/null -D - -X POST "$U" \
    -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":0,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-03-26\",\"capabilities\":{},\"clientInfo\":{\"name\":\"side-entrance-probe\",\"version\":\"1\"}}}" \
    | tr -d "\r" | grep -iE "^HTTP/|^mcp-session-id" | sed -E "s/^([Mm]cp-[Ss]ession-[Ii]d:).*/\1 <present>/"
  echo "    curl exit=$?"
done'
GW=http://modaas-agw.agentgateway-system:8080/mcp/modaas-docs
DIRECT=http://modaas-docs-mcp.components:8080/mcp

echo "=== A. from a pod in 'default' (no credential) ==="
incluster side-probe-default -- sh -c "$PROBE" sh "$GW" "$DIRECT"

echo "=== B. from a pod in 'components', where agents run (no credential) ==="
kubectl delete pod side-probe-comp -n components --ignore-not-found >/dev/null
kubectl run side-probe-comp -n components --restart=Never --image=curlimages/curl:8.5.0 -- sh -c "$PROBE" sh "$DIRECT" >/dev/null
for _ in $(seq 120); do case $(kubectl get pod side-probe-comp -n components -o jsonpath='{.status.phase}') in Succeeded|Failed) break;; esac; sleep 1; done
kubectl logs side-probe-comp -n components -c side-probe-comp
kubectl delete pod side-probe-comp -n components --wait=false >/dev/null

echo "=== docs server log for these probes ==="
kubectl logs deploy/modaas-docs-mcp -n components --since=5m 2>/dev/null | grep -iE "initialize|side-entrance|session" | tail -5
echo "=== leftover probe pods ==="
kubectl get pod side-probe-default -n default 2>&1 | tail -1; kubectl get pod side-probe-comp -n components 2>&1 | tail -1

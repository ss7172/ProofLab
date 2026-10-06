"""EP-6 collector (Ph2): the PDP / authz pod logs of EVERY replica (`kubectl logs` per pod), one file per pod.

Decision lines carry no principal and no CID: they join by action id later (the stitcher), so nothing is filtered
by CID here. A replica missed is recorded (`pagination_complete: false`, `replicas_missing` in the sidecar),
never hidden. Pod logs are ephemeral (pod lifetime): capture early. Captures bytes; computes no verdict."""
from __future__ import annotations

import json

from prooflab.adapters.collectors import capture

SURFACE = "pdp"
EXPECTED_REPLICAS = 2          # platform fact (two PDP replicas), not a control threshold
DEFAULT_NAMESPACE = "agentgateway-system"


def list_pods(ctx: capture.Ctx, namespace: str, selector: str) -> list:
    argv = ["kubectl", "-n", namespace, "get", "pods", "-l", selector, "-o", "json"]
    doc = json.loads(capture.run(ctx, argv).decode("utf-8") or "{}")
    return sorted((p.get("metadata") or {}).get("name") for p in doc.get("items") or []
                  if (p.get("metadata") or {}).get("name"))


def pull_pods(ctx: capture.Ctx, surface: str, scope_name: str, namespace: str, selector: str,
              needles=(), expected_replicas: int = EXPECTED_REPLICAS, pods=None) -> list:
    """Capture each pod's log to raw/<surface>/<scope_name>/<pod>.log. `needles`: keep only lines containing one
    of them (empty = every line). -> the sidecars, one per pod."""
    pods = list(pods) if pods is not None else list_pods(ctx, namespace, selector)
    complete = len(pods) >= expected_replicas
    out = []
    for pod in pods:
        argv = ["kubectl", "-n", namespace, "logs", pod, "--timestamps"]
        data = capture.run(ctx, argv)
        if needles:
            keep = [ln for ln in data.split(b"\n") if any(n.encode("utf-8") in ln for n in needles)]
            data = b"".join(ln + b"\n" for ln in keep)
        out.append(capture.write_capture(
            ctx, surface, scope_name, "%s.log" % pod, data, command=capture.command_text(argv),
            scope={"namespace": namespace, "selector": selector, "pod": pod, "needles": list(needles)},
            source_identity={"namespace": namespace, "pod": pod, "replicas_captured": len(pods),
                             "replicas_expected": expected_replicas,
                             "replicas_missing": max(0, expected_replicas - len(pods))},
            pagination_complete=complete))
    return out


def pull(ctx: capture.Ctx, selector: str, namespace: str = DEFAULT_NAMESPACE, pods=None,
         expected_replicas: int = EXPECTED_REPLICAS) -> list:
    return pull_pods(ctx, SURFACE, "pdp", namespace, selector, expected_replicas=expected_replicas, pods=pods)

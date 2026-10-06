"""EP-7 collector (Ph2): gateway pod stdout (ephemeral backup of the real outcome), lines naming the run id (CID)
and/or trace ids. Run ids are quoted on the gateway's stdout, so the needle is the quoted CID."""
from __future__ import annotations

from prooflab.adapters.collectors import capture, pdp_logs

SURFACE = "gateway-stdout"


def pull(ctx: capture.Ctx, cid: str, selector: str, namespace: str = pdp_logs.DEFAULT_NAMESPACE,
         trace_ids=(), pods=None, expected_replicas: int = 1) -> "list | None":
    if capture.skip_cid(cid):
        return None
    needles = ['"%s"' % cid] + [str(t) for t in trace_ids]
    return pdp_logs.pull_pods(ctx, SURFACE, cid, namespace, selector, needles=needles,
                              expected_replicas=expected_replicas, pods=pods)

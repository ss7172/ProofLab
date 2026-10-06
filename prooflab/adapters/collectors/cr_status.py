"""EP-10 collector: AgentConfig / ModelConfig / ToolConfig status and approvals via kubectl, redacted at capture.

On EVERY CR kind it drops spec.awsAgentCore.environmentVariables and the last-applied-configuration and kopf
last-handled-configuration annotations (three copies of the ledger token per AgentConfig), then removes any
token-shaped value, and records what it dropped (path + rule, never a value) in the sidecar."""
from __future__ import annotations

import json

from prooflab.adapters.collectors import capture
from prooflab.store import redact

SURFACE = "cr-status"
KINDS = ("agentconfig", "modelconfig", "toolconfig")


def redact_list(doc: dict) -> tuple:
    """-> (clean List document, counts, dropped [{cr, path, rule}])."""
    items, counts, dropped = [], {}, []
    for cr in doc.get("items") or []:
        clean, drops = redact.drop_cr_paths(cr)
        name = "%s/%s" % (cr.get("kind", "?"), (cr.get("metadata") or {}).get("name", "?"))
        for d in drops:
            dropped.append({"cr": name, "path": d["path"], "rule": d["rule"]})
            counts[d["rule"]] = counts.get(d["rule"], 0) + 1
        clean, c, _paths = redact.redact_obj(clean, token_shaped=True)
        counts = redact.merge_counts(counts, c)
        items.append(clean)
    out = dict(doc)
    out["items"] = items
    return out, counts, sorted(dropped, key=lambda d: (d["cr"], d["path"]))


def pull(ctx: capture.Ctx, namespace: str = "components", kinds=KINDS, scope_name: str = "components") -> dict:
    argv = ["kubectl", "-n", namespace, "get", ",".join(kinds), "-o", "json"]
    doc = json.loads(capture.run(ctx, argv).decode("utf-8"))
    clean, counts, dropped = redact_list(doc)
    sc = capture.write_capture(
        ctx, SURFACE, scope_name, "cr-status.json", capture.canonical(clean),
        command=capture.command_text(argv), scope={"namespace": namespace, "kinds": list(kinds)},
        source_identity={"namespace": namespace}, counts=counts)
    sc["dropped"] = dropped
    # the dropped list is part of the sidecar on disk too
    path = ctx.root + "/" + sc["path"] + ".capture.json"
    with open(path, "wb") as fh:
        fh.write((json.dumps(sc, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return sc

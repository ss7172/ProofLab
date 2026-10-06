#!/usr/bin/env python3
"""C9's declared model swap for the named run N8 (ARCH 5.5; IMPLEMENTATION-PLAN 5.2 rows 33-34). Stdlib, Python 3.9.

GENERATES, NEVER APPLIES. Offline: it reads files (or stdin) the ops lane captured and writes merge patches plus the
exact command lines for the ops lane to run through workshop-local/bin/hk. It never calls kubectl, aws or anything else.

    c9_model_swap.py patches [--current CR.json|-] [--agent ifabric-it] [--to nemotron-nano-9b] [--out-dir DIR]
        -> <agent>-swap-<to>.json and <agent>-revert-<from>.json (merge patches) + the command lines (JSON on stdout)
    c9_model_swap.py precheck --modelconfig MC.json|-        (exit 0 = Approved and not paused, 1 = not, 2 = unreadable)

The swap sets `spec.modelRef` AND `spec.dependsOn.models[0]` to the target in ONE merge patch: the CRD rule requires
modelRef, once set, to be one of dependsOn.models, and the runtime model (MODEL_ALIAS) follows models[0] [notes:
playbook-verification "model swap"]. A merge patch merges `dependsOn` (tools stay) and replaces the `models` list.
The revert restores the pre-swap STATE exactly: the original models list and the original modelRef, or `null`
(deleted) when the CR had none (generated CRs have none). Pass the pre-swap CR (`kubectl get agentconfig -o json`, or
the lane's filtered status.py view) as --current so the revert is computed from it; without it the revert ASSUMES
models [--from] and no modelRef, and says so.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HK = "~/firstmate-homes/TrustworthyAI/workshop-local/bin/hk"
NAMESPACE = "components"
DEFAULT_AGENT = "ifabric-it"
DEFAULT_TO = "nemotron-nano-9b"        # an Approved ModelConfig in yesterday's reference swap; the lane re-checks
DEFAULT_FROM = "nemotron-super-120b"    # what the three ifabric agents were frozen on (v0-pilot applies_to)
_ABSENT = object()


class SwapError(ValueError):
    pass


def _load(path):
    text = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    try:
        return json.loads(text)
    except ValueError as exc:
        raise SwapError("not JSON: %s" % exc)


def current_state(cr):
    """(models list, modelRef or _ABSENT, name) from a full AgentConfig (kubectl -o json) or the filtered view."""
    if not isinstance(cr, dict):
        raise SwapError("the AgentConfig document is not an object")
    if "spec" in cr:                                    # kubectl get agentconfig -o json
        spec = cr.get("spec") or {}
        name = (cr.get("metadata") or {}).get("name")
        model_ref = spec["modelRef"] if "modelRef" in spec else _ABSENT
        models = (spec.get("dependsOn") or {}).get("models")
    else:                                               # the ops lane's filtered status.py view
        name = cr.get("name")
        model_ref = cr["modelRef"] if "modelRef" in cr else _ABSENT
        models = (cr.get("dependsOn") or {}).get("models")
    if not isinstance(models, list) or not models or not all(isinstance(m, str) and m for m in models):
        raise SwapError("dependsOn.models missing or empty in the AgentConfig document")
    return list(models), model_ref, name


def swap_patches(models, model_ref, to_model):
    """(swap patch, revert patch). The revert is the exact pre-swap modelRef + models list."""
    if models[0] == to_model:
        raise SwapError("the agent already runs %s: nothing to swap" % to_model)
    if model_ref is not _ABSENT and model_ref not in (None, models[0]):
        raise SwapError("modelRef %r differs from dependsOn.models[0] %r: which one wins is unverified; refusing"
                        % (model_ref, models[0]))
    new_models = [to_model] + [m for m in models[1:] if m != to_model]
    swap = {"spec": {"modelRef": to_model, "dependsOn": {"models": new_models}}}
    revert = {"spec": {"modelRef": None if model_ref is _ABSENT else model_ref, "dependsOn": {"models": list(models)}}}
    return swap, revert


def commands(agent, patch_path):
    base = "kubectl patch agentconfig %s -n %s --type merge --patch-file %s" % (agent, NAMESPACE, patch_path)
    return {"dry_run": "%s '%s --dry-run=server -o json'" % (HK, base),
            "apply": "%s '%s'" % (HK, base)}


def precheck_command(model):
    return "%s 'kubectl get modelconfig %s -n %s -o json'" % (HK, model, NAMESPACE)


def precheck(mc):
    """(ok, facts): the target ModelConfig is Approved (status.phase or registryApprovalStatus) and NOT paused."""
    if not isinstance(mc, dict) or "spec" not in mc:
        raise SwapError("not a ModelConfig document (kubectl get modelconfig -o json)")
    spec, status = mc.get("spec") or {}, mc.get("status") or {}
    facts = {"name": (mc.get("metadata") or {}).get("name"), "phase": status.get("phase"),
             "registryApprovalStatus": status.get("registryApprovalStatus"), "paused": spec.get("paused") is True}
    approved = str(facts["phase"] or "").lower() == "approved" and \
        str(facts["registryApprovalStatus"] or "approved").lower() == "approved"
    facts["approved"] = approved
    return approved and not facts["paused"], facts


def plan(agent, to_model, current=None, from_model=DEFAULT_FROM, out_dir="."):
    notes = []
    if current is not None:
        models, model_ref, name = current_state(current)
        if name and name != agent:
            raise SwapError("the AgentConfig document is %s, not %s" % (name, agent))
    else:
        models, model_ref = [from_model], _ABSENT
        notes.append("no --current: the revert ASSUMES dependsOn.models [%s] and no modelRef; capture the CR first "
                     "and re-run with --current to compute the exact revert" % from_model)
    swap, revert = swap_patches(models, model_ref, to_model)
    out_dir = os.path.abspath(out_dir)          # hk runs the command in a fresh shell: absolute paths only
    sp = os.path.join(out_dir, "%s-swap-%s.json" % (agent, to_model))
    rp = os.path.join(out_dir, "%s-revert-%s.json" % (agent, models[0]))
    return {"agent": agent, "from_model": models[0], "to_model": to_model,
            "pre_swap_modelRef": None if model_ref is _ABSENT else model_ref,
            "pre_swap_modelRef_present": model_ref is not _ABSENT,
            "swap_patch": swap, "revert_patch": revert, "swap_file": sp, "revert_file": rp,
            "precheck": precheck_command(to_model), "capture_current": "%s 'kubectl get agentconfig %s -n %s -o json'"
                                                                       % (HK, agent, NAMESPACE),
            "swap": commands(agent, sp), "revert": commands(agent, rp), "notes": notes,
            "register_declaration": "N8:model-swap:%s:%s:%s" % (agent, models[0], to_model)}


def _write(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="c9_model_swap.py", description="generate (never apply) C9's N8 swap + revert")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("patches")
    p.add_argument("--agent", default=DEFAULT_AGENT)
    p.add_argument("--to", default=DEFAULT_TO)
    p.add_argument("--from", dest="from_model", default=DEFAULT_FROM, help="used only without --current")
    p.add_argument("--current", default=None, help="the pre-swap AgentConfig JSON (file or - for stdin)")
    p.add_argument("--out-dir", default=".")
    q = sub.add_parser("precheck")
    q.add_argument("--modelconfig", required=True, help="kubectl get modelconfig <m> -n components -o json (file or -)")
    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "patches":
            doc = plan(ns.agent, ns.to, _load(ns.current) if ns.current else None, ns.from_model, ns.out_dir)
            os.makedirs(ns.out_dir, exist_ok=True)
            _write(doc["swap_file"], doc["swap_patch"])
            _write(doc["revert_file"], doc["revert_patch"])
            print(json.dumps(doc, indent=1, sort_keys=True))
            return 0
        if ns.cmd == "precheck":
            ok, facts = precheck(_load(ns.modelconfig))
            print(json.dumps(dict(facts, ok=ok), sort_keys=True))
            return 0 if ok else 1
    except (SwapError, OSError) as exc:
        print("c9_model_swap: %s" % exc, file=sys.stderr)
        return 2
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

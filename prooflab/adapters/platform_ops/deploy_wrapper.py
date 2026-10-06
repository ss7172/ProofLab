"""EP-10 record for a pin or mode patch / apply (ARCH EP-10: every apply and dry run, the API's answer verbatim).

The wrapper records and prints; it never runs a live command. `render_patch_command` returns the text of the
kubectl patch an operator runs through the hk wrapper. Env values are never written: the patch is summarised
by keys and sha256, and the answer is withheld whole if it is secret-shaped (each AgentConfig holds the token).
"""
from __future__ import annotations

import json

from prooflab.adapters.orchestrator import common
from prooflab.adapters.platform_ops import _common

KINDS = ("pin", "mode", "apply", "dry-run")


def summarise_patch(patch) -> dict:
    """Keys and digest only. IFABRIC_PIN_SHA256 is a hash, so it may be named; no env value is copied."""
    env = (((patch or {}).get("spec") or {}).get("awsAgentCore") or {}).get("environmentVariables") or {}
    return {"patch_sha256": common.sha256_text(common.canonical(patch)),
            "env_keys": sorted(env) if isinstance(env, dict) else [],
            "top_keys": sorted((patch or {}).keys())}


def record_deploy(kind, agent, patch, api_answer, authority, cid, now=None, mode=None, pin_sha256=None, generation=None):
    if kind not in KINDS:
        raise ValueError("kind must be one of %s" % (KINDS,))
    answer, withheld = _common.scrub(api_answer or "")
    summary = summarise_patch(patch)
    detail = json.dumps({"deploy": kind, "agent": agent, "authority": authority, "answer": answer,
                         "answer_withheld": withheld, "mode": mode, "generation": generation, **summary},
                        sort_keys=True)
    return _common.lane_record("action", "EP-10", "deploy wrapper (AgentConfig apply / patch)", cid, detail, now=now,
                               **{"pin.sha256": pin_sha256,
                                  "inline.mode": mode if mode in ("enforce", "observe") else None})


def render_patch_command(agent, patch_file, namespace="components", dry_run=True):
    """The text of the command to run through hk. Printed, never executed here."""
    server = " --dry-run=server" if dry_run else ""
    return "%s 'kubectl -n %s patch agentconfig %s --type merge --patch-file %s%s -o name'" % (
        _common.HK, namespace, agent, patch_file, server)

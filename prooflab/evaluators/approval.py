"""approval.py: EP-0, the pre-run version gate (ARCH 3.4, 5.0 part 4; D13). Pure, stateless, stdlib, Python 3.9.

    check_versions(running, approved, policy, assessed, meta=None) -> list[Decision]      (STABLE SIGNATURE;
    PR-08a's preflight and INV (5.6) call it; the preflight acts only on `decision.action`)

running   {agent_name: AgentVersion}. An AgentVersion is a mapping (or an object) with
            image_digest         str   the running image digest
            model                str   the model alias (dependsOn.models[0])
            generation           int   the AgentConfig generation, optional
            approved_generation  int   the newest generation an approval record covers (a base approval, a
                                       declared treatment's approval, or an owner-OK'd EP-setting change), optional
            paused               bool  spec.paused, optional (default False)
approved  {agent_name: set of approved versions}, from the frozen inventory / store. A version is the string
          "<image_digest>|<model>" or the tuple (image_digest, model).
policy    the register's pre_run_gate: "block-assessed" | "record-only" (anything else fails closed to block-assessed)
assessed  True for a LIVE_SUBJECT run (EP-0 gates only assessed runs)
meta      optional dict stamped on every Decision: threshold_version, register_version, threshold_sha256,
          pin_sha256, evaluator_sha256

One Decision per agent (sorted by agent name): verdict ALLOW | DENY; mode = the policy; limit_applied
"approved-versions"; action "decline-start" iff DENY and policy block-assessed and assessed, else "proceed".
DENY causes: paused agent; running version not approved; approval older than the running generation (stale).
An agent with no approved versions at all is DENY too. It never reads env values (the caller never passes them).
"""
from __future__ import annotations

from prooflab.evaluators.c16_core import Decision

CONTROL_REF = "APPROVAL"
CONTROL_ID = "IFABRIC-APPROVAL-001"
NAME = "prooflab.evaluators.approval"
POLICIES = ("block-assessed", "record-only")
LIMIT_APPLIED = "approved-versions"


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def version_key(digest, model):
    return "%s|%s" % (digest, model)


def _approved_keys(vs):
    keys = set()
    for v in vs or ():
        if isinstance(v, (tuple, list)) and len(v) == 2:
            keys.add(version_key(v[0], v[1]))
        else:
            keys.add(str(v))
    return keys


def _int_or_none(x):
    return x if isinstance(x, int) and not isinstance(x, bool) else None


def check_versions(running, approved, policy, assessed, meta=None):
    meta = meta or {}
    bad_policy = policy not in POLICIES
    mode = "block-assessed" if bad_policy else policy
    out = []
    for agent in sorted(running or {}):
        rv = running[agent]
        reasons = []
        if bad_policy:
            reasons.append("invalid pre_run_gate %r: treated as block-assessed" % (policy,))
        digest, model = _get(rv, "image_digest"), _get(rv, "model")
        if _get(rv, "paused", False) is True:
            reasons.append("paused")
        have = _approved_keys((approved or {}).get(agent))
        if not (isinstance(digest, str) and digest and isinstance(model, str) and model):
            reasons.append("running version unreadable (image digest or model missing)")
        elif not have:
            reasons.append("no approved version recorded for %s" % agent)
        elif version_key(digest, model) not in have:
            reasons.append("running version %s is not an approved version" % version_key(digest, model))
        gen, agen = _int_or_none(_get(rv, "generation")), _int_or_none(_get(rv, "approved_generation"))
        if gen is not None and agen is not None and gen > agen:
            reasons.append("stale approval: approved at generation %d, running generation %d" % (agen, gen))
        deny = any(not r.startswith("invalid pre_run_gate") for r in reasons)
        decline = deny and mode == "block-assessed" and bool(assessed)
        why = "; ".join(reasons) if reasons else "running version is an approved version"
        out.append(Decision(
            CONTROL_REF, CONTROL_ID, "DENY" if deny else "ALLOW", "%s: %s" % (agent, why), None, None, None, mode,
            LIMIT_APPLIED, None, "decline-start" if decline else "proceed", None,
            meta.get("threshold_version", ""), meta.get("register_version", ""), meta.get("threshold_sha256", ""),
            meta.get("pin_sha256", ""), NAME, meta.get("evaluator_sha256")))
    return out

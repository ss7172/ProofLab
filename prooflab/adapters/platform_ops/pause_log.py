"""EP-8 record: a kill-switch pause REQUESTED (model, tool or AgentConfig). The effective time comes later from
a pull (the 404 joined by trace id); an AgentConfig pause is a record, not a stop (the runtime stays READY)."""
from __future__ import annotations

import json

from prooflab.adapters.platform_ops import _common

TARGETS = ("model", "tool", "agentconfig")
ACTIONS = ("pause", "unpause")


def record_pause(target_kind, target, action, authority, cid, requested_at, now=None):
    if target_kind not in TARGETS or action not in ACTIONS:
        raise ValueError("target_kind in %s, action in %s" % (TARGETS, ACTIONS))
    detail = json.dumps({"kill_switch": action, "target_kind": target_kind, "target": target,
                         "authority": authority, "requested_at": requested_at,
                         "effect": "route withdrawn" if target_kind != "agentconfig" else "record only; runtime stays READY"},
                        sort_keys=True)
    return _common.lane_record("action", "EP-8", "kill switch (pause) request", cid, detail, now=now)

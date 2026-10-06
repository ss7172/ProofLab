"""Shared helpers for the lane wrappers: EP records that never carry a secret-shaped value."""
from __future__ import annotations

from prooflab.adapters.orchestrator import common, records
from prooflab.contract import ids, record as R

WITHHELD = "[withheld: secret-shaped]"
HK = "~/firstmate-homes/TrustworthyAI/workshop-local/bin/hk"


def scrub(text):
    """Verbatim unless it looks like a credential or an env assignment of one; then withheld, never partial."""
    return (WITHHELD, True) if R.secret_shaped(text) else (text, False)


def lane_record(kind, ep_id, ep_kind, cid, detail, now=None, provenance="AUTHORIZED_TEST", **fields):
    """A validated EP record from the ops lane. `cid` may be None for an action outside any run: then the
    `ifabric-test-` CID of the lane action is minted by the caller (never an invented family)."""
    if cid is None:
        raise ValueError("a lane record needs a CID (mint ifabric-test-<epoch>-<hex> for an out-of-run action)")
    ids.parse_cid(cid)
    return records.make(kind, cid, detail, "not applicable: " + ep_id, emitter_short="lane",
                        emitter="adapters.platform_ops@1.0+0000000", provenance=provenance, now=now,
                        **dict({"ep.id": ep_id, "ep.kind": ep_kind, "ep.transport": "emit",
                                "ep.responsible": "team iFabric (Sree)", "actor.id": "ops-lane"}, **fields))

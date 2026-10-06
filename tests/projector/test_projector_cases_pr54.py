"""PR-54: a ServiceNow case snapshot (ifabric.servicenow.case/v1) is listed in pack-index cases[] when its incident
number sits at servicenow.number (the real shape) or delivery.number; a top-level 'incident' still works."""
import json
import os

import _pack_fixture as fx
from prooflab.pack import projector


def _case(src, name, body):
    d = os.path.join(src, "servicenow", "cases")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w") as f:
        json.dump(body, f)


def test_cases_listed_from_the_real_snapshot_shapes(tmp_path):
    src = fx.build(str(tmp_path / "src"))
    _case(src, "a.json", {"schema": "ifabric.servicenow.case/v1", "finding_id": "f-a", "servicenow": {"number": "INC0010351"}})
    _case(src, "b.json", {"finding_id": "f-b", "delivery": {"number": "INC0010338", "state": "DELIVERED"}})
    _case(src, "c.json", {"finding_id": "f-c", "incident": "INC0000001"})
    _case(src, "d.json", {"finding_id": "f-d", "servicenow": {}})      # no number anywhere: not listed
    out = str(tmp_path / "out")
    projector.project(src, out, as_of="2026-10-06T09:00:00Z")
    idx = json.load(open(os.path.join(out, "pack-index.json")))
    got = dict((c["finding_id"], c["incident"]) for c in idx["cases"])
    assert {k: got.get(k) for k in ("f-a", "f-b", "f-c")} == {"f-a": "INC0010351", "f-b": "INC0010338", "f-c": "INC0000001"}
    assert "f-d" not in got

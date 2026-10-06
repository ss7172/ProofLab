"""PR-51b: EPs whose records carry no ep.id are identified by record kind (records never rewritten); levels say why."""
from prooflab.pack import index, projector


def test_ep_of_record_by_kind():
    assert projector.ep_of_record({"ep.id": "EP-1"}) == ("EP-1", None)
    ep, how = projector.ep_of_record({"record_kind": "lifecycle", "phase": "ep0.declared_treatment", "ep.id": None})
    assert ep == "EP-0" and "ep.id not recorded; identified by record kind" in how
    assert projector.ep_of_record({"record_kind": "observation"})[0] == "EP-2"
    assert projector.ep_of_record({"record_kind": "metric"})[0] == "EP-11"
    assert projector.ep_of_record({"record_kind": "lifecycle", "phase": "run.started"}) == (None, None)


def test_enforcement_points_notes_and_levels():
    eps = index.enforcement_points({"EP-0": ["record:x"], "EP-11": ["record:m"]}, {"EP-0": "ep.id not recorded; identified by record kind (phase ep0.*)"})
    by = dict((e["id"], e) for e in eps)
    assert by["EP-0"]["status"] == "BUILT" and "identified by record kind" in by["EP-0"]["note"]
    assert by["EP-11"]["status"] == "EVIDENCED"
    assert by["EP-6"]["status"] == "NOT_RUN"

"""PR-52a: the human loop is read from the pack files (findings/, servicenow/delivery-log.jsonl, closures/)."""
import json
import os

from prooflab.query import engine as E


class _P(object):
    def __init__(self, root):
        self.root = root

    def p(self, *parts):
        return os.path.join(self.root, *parts)


def _w(path, obj, lines=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write("\n".join(json.dumps(o) for o in obj) if lines else json.dumps(obj))


def test_breach_run_and_retest_run_both_see_the_loop(tmp_path):
    root = str(tmp_path)
    fid = "ifabric:C7:C7-v1:run:R4:finding"
    _w(os.path.join(root, "findings", "C7-R4.json"), {"control_ref": "C7", "threshold_version": "C7-v1", "scope_kind": "run",
                                                      "scope_id": "R4", "verdict": "BREACHED", "detected_at": "2026-10-06T15:22:06Z"})
    _w(os.path.join(root, "servicenow", "delivery-log.jsonl"), [
        {"finding_id": fid, "number": "INC1", "state": "DELIVERED", "ts": "2026-10-06T15:22:43Z"},
        {"finding_id": fid, "number": "INC1", "state": "ANALYSIS_WRITTEN", "ts": "2026-10-06T15:23:10Z"}], lines=True)
    _w(os.path.join(root, "closures", "C7-R4-closure.json"), {"finding_id": fid, "control_ref": "C7", "scope_id": "R4", "retest_cid": "R5",
                                                              "incident": "INC1", "closed_by": "retest", "closed_at": "2026-10-06T15:42:31Z",
                                                              "retest": {"verdict": "SATISFIED", "threshold_version": "C7-v1"}})
    pk = _P(root)
    texts = " | ".join(x["text"] for x in E.pack_human_loop(pk, "R4", "C7"))
    assert "BREACHED" in texts and "INC1 DELIVERED" in texts and "Assurance agent analysis" in texts and "re-test run R5" in texts
    assert "not the incident" in texts
    assert E.pack_human_loop(pk, "R4", "C16") == []
    r5 = " | ".join(x["text"] for x in E.pack_human_loop(pk, "R5", "C7"))
    assert "re-test that closed the finding behind INC1" in r5

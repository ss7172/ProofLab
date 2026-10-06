"""PR-51b: a warm-up's label comes from its own records' provenance, never OURS-ROLE-UNDECLARED (catalogue row untouched)."""
import json
import os

from prooflab.pack import history


def test_warmup_label_declared(tmp_path):
    src = str(tmp_path)
    os.makedirs(os.path.join(src, "derived"))
    with open(os.path.join(src, "derived", "run-catalogue.jsonl"), "w") as fh:
        fh.write(json.dumps({"run_id": "ifabric-run-1-w1", "label": "OURS-ROLE-UNDECLARED"}) + "\n")
    recs = [{"correlation_id": "ifabric-run-1-w1", "provenance": "EXPLORATORY", "ts": "2026-10-06T13:52:05.264Z"}] * 3
    rows = history.run_catalogue(src, {}, None, recs)
    w = [r for r in rows if r["cid"] == "ifabric-run-1-w1"][0]
    assert w["label"] == "EXPLORATORY" and "provenance field on 3" in w["label_source"]
    assert "OURS-ROLE-UNDECLARED" in w["label_source"]
    assert w["provenance"] == "EXPLORATORY"

import json
import os

from prooflab.stitch import catalogue


def _s(rid, src="gateway", ts="2026-10-06T00:00:00Z", i=None, o=None):
    return {"run_id": rid, "source": src, "ts": ts, "tokens_in": i, "tokens_out": o}


def test_labels_cover_every_family_and_never_empty():
    prov = {"ifabric-run-1791300000-a1b2c3": "PILOT"}
    cases = {
        "ifabric-run-1791300000-a1b2c3": "PILOT", "ifabric-run-1791300001-a1b2c3": "OURS-ROLE-UNDECLARED",
        "ifabric-test-1791300100-d4e5f6": "test", "ifabric-adv-1791300200-0a1b2c": "adv",
        "ifabric-assure-1791300300-0a1b2c": "assure", "ifabric-unenveloped-1791300400-0a1b2c": "unenveloped",
        "fault-1791175626-0d34e2": "EXPLORATORY", "my-agent-1791-x": "my-agent",
        "hackathon-helper-1791-x": "hackathon-helper", "unattributed:rt:2026-10-06T04:50:00Z": "UNATTRIBUTED",
        "somebody-else-1": "OTHER-PARTY", "ifabric-test-ledger-smoke-1791252169": "test",
    }
    for rid, label in cases.items():
        assert catalogue.label_for(rid, prov) == label, rid


def test_one_row_per_run_tokens_sum_and_only_listed_ids_assessed():
    sights = [_s("fault-1-a", i=10, o=5), _s("fault-1-a", "ledger", "2026-10-05T00:00:00Z"),
              _s("ifabric-run-1791300000-a1b2c3", "aws-invocation"), _s("fault-1-a", i=1, o=1),
              _s("unresolved:" + "a" * 32), _s("other-9")]
    rows = catalogue.build(sights, {"ifabric-run-1791300000-a1b2c3"})
    ids = [r["run_id"] for r in rows]
    assert ids.count("fault-1-a") == 1 and not any(i.startswith("unresolved:") for i in ids)
    f = [r for r in rows if r["run_id"] == "fault-1-a"][0]
    assert (f["tokens_in"], f["tokens_out"]) == (11, 6) and f["first_seen"] == "2026-10-05T00:00:00Z"
    assert f["sources"] == {"gateway": 2, "ledger": 1}
    assert [r["run_id"] for r in rows if r["assessed"]] == ["ifabric-run-1791300000-a1b2c3"]
    assert [r for r in rows if r["run_id"] == "other-9"][0]["tokens_in"] is None


def test_window_filters_sightings():
    rows = catalogue.build([_s("a-1", ts="2026-10-06T00:00:00Z"), _s("b-1", ts="2026-10-07T00:00:00Z")], [],
                           window=("2026-10-06T00:00:00Z", "2026-10-06T23:59:59Z"))
    assert [r["run_id"] for r in rows] == ["a-1"]


def test_cli_lists_the_catalogue(tmp_path, capsys):
    rows = catalogue.build([_s("fault-1-a", i=2, o=3)], ["fault-1-a"])
    d = tmp_path / "derived"
    d.mkdir()
    (d / "run-catalogue.jsonl").write_text(catalogue.dumps_rows(rows))
    assert catalogue.main(["--derived", str(d)]) == 0
    out = capsys.readouterr().out
    assert "fault-1-a" in out and "EXPLORATORY" in out and "yes" in out
    assert catalogue.main(["--derived", str(tmp_path)]) == 1

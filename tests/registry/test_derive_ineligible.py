"""PR-43: derive refuses halted / failed / not-eligible / S2 runs for every control, and --use restricts all controls."""
import json
import os

import pytest

from prooflab.registry import derive as DV

RULES = {"c16_rule_id": "C16-cap/1", "c16_headroom_pct": 20, "c16_round_up_to": 1000, "appetite_tokens": 900000,
         "c7_rule_id": "C7-gap/1", "c7_headroom_pct": 50, "c7_round_up_to": 1000,
         "c9_rule_id": "C9-baseline/1", "eligible_scenarios": ["S1", "S3"]}


def row(rid, scen="S1", tokens=20000, gap=5000, lat=7000, **extra):
    d = {"run_id": rid, "scenario": scen, "provenance": "PILOT", "condition": "none", "mode": "observe",
         "measured": {"c16_tokens": tokens, "c7_gap_ms_max": gap, "c9_latency_max_ms": {"ifabric-it": lat}}}
    d.update(extra)
    return d


ROWS = [row("P1-halted", tokens=95936, gap=56860, lat=57297, halted=True, derivation_eligible=False),
        row("P1-failed", tokens=88000, gap=40000, lat=50000, status="FAILED-UPSTREAM"),
        row("P1-inelig", tokens=70000, gap=30000, lat=30000, derivation_eligible=False),
        row("P2-s2", scen="S2", tokens=60000, gap=20000, lat=20000),
        row("P1b", tokens=21000, gap=6000, lat=7000),
        row("P3", scen="S3", tokens=30000, gap=9000, lat=8000)]


def files(tmp_path):
    ex, ru = tmp_path / "e.jsonl", tmp_path / "r.json"
    ex.write_text("\n".join(json.dumps(r) for r in ROWS) + "\n")
    ru.write_text(json.dumps(RULES))
    return str(ex), str(ru)


def test_ineligible_runs_feed_no_control():
    items = DV.derive_all(ROWS, RULES, "x")
    for it in items:
        assert it["cites"] == ["P1b", "P3"], it
    assert items[0]["normal_need_tokens"] == 30000 and items[0]["value"] == 36000
    assert items[1]["normal_need_ms"] == 9000
    assert items[2]["baseline_values"] == {"ifabric-it_S1": 7000, "ifabric-it_S3": 8000}


@pytest.mark.parametrize("rid,word", [("P1-halted", "halted"), ("P1-failed", "failed"),
                                      ("P1-inelig", "not derivation-eligible"), ("P2-s2", "not eligible")])
def test_use_naming_an_ineligible_run_is_refused_for_each_control(rid, word):
    for fn in (DV.derive_c16, DV.derive_c7_gap, DV.derive_c9_baseline):
        with pytest.raises(DV.DeriveError, match="never derived|refused") as ei:
            fn(ROWS, RULES, "x", [rid])
        assert word in str(ei.value) or "never derived" in str(ei.value)


def test_use_restricts_all_controls_not_only_c16():
    items = DV.derive_all(ROWS, RULES, "x", ["P1b"])
    assert [it["cites"] for it in items] == [["P1b"]] * 3
    assert items[1]["normal_need_ms"] == 6000 and items[2]["baseline_values"] == {"ifabric-it_S1": 7000}


def test_only_ineligible_runs_means_no_derivation():
    with pytest.raises(DV.DeriveError, match="no eligible pilot run"):
        DV.derive_all(ROWS[:3], RULES, "x")


def test_cli_prints_used_and_excluded_with_reasons(tmp_path, capsys):
    ex, ru = files(tmp_path)
    assert DV.main(["--experiments", ex, "--rules", ru]) == 0
    cap = capsys.readouterr()
    assert "used runs: P1b, P3" in cap.err
    assert "excluded P1-halted: halted" in cap.err and "excluded P1-failed: failed" in cap.err
    assert "excluded P1-inelig: not derivation-eligible" in cap.err and "excluded P2-s2" in cap.err
    assert json.loads(cap.out)[1]["cites"] == ["P1b", "P3"]
    assert DV.main(["--experiments", ex, "--rules", ru, "--use", "P1-halted"]) == 2
    assert DV.main(["--experiments", ex, "--rules", ru, "--use", "P1b"]) == 0
    assert "not named by --use" in capsys.readouterr().err

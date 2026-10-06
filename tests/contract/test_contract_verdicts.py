"""One verdict vocabulary (ARCH §4.3; G0.2)."""
import pytest

from prooflab.contract import verdicts as V


def test_types_are_disjoint_where_they_must_be():
    assert not set(V.RAIL_VERDICTS) & set(V.ASSESSMENT_VERDICTS)
    assert not set(V.RISK_STATES) & set(V.ALL_RECORD_VERDICTS)
    assert set(V.VERDICTS_BY_KIND["assessment"]) == set(V.ASSESSMENT_VERDICTS)
    for kind, allowed in V.VERDICTS_BY_KIND.items():
        if kind != "rail_decision":
            assert not {"BLOCK", "MODIFY", "FLAG"} & set(allowed), kind


@pytest.mark.parametrize("ours,slides,brief,finding,kind,kit,code", [
    ("SATISFIED", "SATISFIED", "satisfied", "SATISFIED", "finding", "PASS", 0),
    ("BREACHED", "NOT SATISFIED", "not-satisfied", "BREACHED", "finding", "BREACH", 1),
    ("INDETERMINATE", None, "insufficient-evidence", "INDETERMINATE", "monitoring-gap", "NO EVIDENCE", 2),
    ("NOT_ASSESSED", None, "not-assessed", None, None, None, 2),
])
def test_four_row_mapping(ours, slides, brief, finding, kind, kit, code):
    assert V.slides_label(ours) == slides
    assert V.brief_label(ours) == brief
    assert V.finding_verdict(ours) == finding
    assert V.finding_kind(ours) == kind
    assert V.kit_label(ours) == kit
    assert V.exit_code(ours) == code
    if kit:
        assert V.KIT_LABEL_TO_VERDICT[kit] == ours


def test_kit_exit_codes_match_evaluate_py():
    # evaluate.py: {"PASS": 0, "NO EVIDENCE": 2}.get(verdict, 1)
    kit = lambda label: {"PASS": 0, "NO EVIDENCE": 2}.get(label, 1)
    for ours in ("SATISFIED", "BREACHED", "INDETERMINATE"):
        assert V.exit_code(ours) == kit(V.kit_label(ours))


def test_notify_and_display():
    assert V.notify_due("BREACHED") and V.notify_due("INDETERMINATE")
    assert not V.notify_due("SATISFIED") and not V.notify_due("NOT_ASSESSED")
    assert V.display("BREACHED") == "NOT SATISFIED"


def test_rail_action():
    assert V.rail_action("BLOCK", "enforce") == "block"
    assert V.rail_action("MODIFY", "enforce") == "modify"
    assert V.rail_action("BLOCK", "observe") == "proceed"
    assert V.rail_action("FLAG", "enforce") == "proceed"
    with pytest.raises(ValueError):
        V.rail_action("DENY", "enforce")


def test_notify_due_includes_escalated():
    """ARCH §3.8 and PR-20a: notify BREACHED, ESCALATED and monitoring gaps (INDETERMINATE)."""
    assert V.notify_due("ESCALATED") is True
    assert V.notify_due("SATISFIED") is False and V.notify_due("NOT_ASSESSED") is False
    assert set(V.NOTIFY_VERDICTS) == {"BREACHED", "INDETERMINATE", "ESCALATED"}

"""Pins the finding-level notify rule against the contract's verdict-level one."""
import prooflab.adapters.human_loop as hl
from prooflab.contract import verdicts


def _f(verdict, kind="assessment"):
    return {"verdict": verdict, "kind": kind}


def test_agrees_with_contract_for_assessment_findings():
    assert hl.notify_due(_f("BREACHED")) == verdicts.notify_due("BREACHED") is True
    assert hl.notify_due(_f("SATISFIED")) == verdicts.notify_due("SATISFIED") is False
    # INDETERMINATE is raised as a monitoring-gap finding, which the local rule notifies
    assert hl.notify_due(_f("INDETERMINATE", "monitoring-gap")) is verdicts.notify_due("INDETERMINATE") is True


def test_approval_escalated_is_the_documented_difference():
    assert hl.notify_due(_f("ESCALATED", "approval")) is True
    assert verdicts.notify_due("ESCALATED") is False

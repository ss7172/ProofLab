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


def test_approval_escalated_agrees_with_contract():
    # PR-01 round 2 (reviewer finding #8) settled the rule: ESCALATED notifies at both levels (ARCH §3.8)
    assert hl.notify_due(_f("ESCALATED", "approval")) is verdicts.notify_due("ESCALATED") is True


def test_satisfied_never_notifies_and_plain_indeterminate_only_as_a_gap():
    assert hl.notify_due(_f("SATISFIED", "monitoring-gap")) is False
    assert hl.notify_due(_f("SATISFIED")) is False
    assert hl.notify_due(_f("INDETERMINATE", "finding")) is False

"""One verdict vocabulary (ARCH §4.3; guardrails G0.2). Stdlib, 3.9.

Four separate types, never mixed:
  1. DECISION verdicts   ALLOW | DENY       evaluator Decision and observed platform decisions
  2. RECORD verdicts     RECORDED | ESCALATED   handoffs, lifecycle, ...; ESC disposition
  3. RAIL verdicts       ALLOW | BLOCK | MODIFY | FLAG   rail_decision records only (never in an assessment)
  4. ASSESSMENT verdicts SATISFIED | BREACHED | INDETERMINATE | NOT_ASSESSED   the control test
Risk states (WITHIN_APPETITE | EXPOSED | UNTESTED) are a fifth type and never appear in a `verdict` field.

An `inline.action` is what an EP does with a decision; it is not a verdict.
"""
from __future__ import annotations

DECISION_VERDICTS = ("ALLOW", "DENY")
RECORD_VERDICTS = ("RECORDED", "ESCALATED")
RAIL_VERDICTS = ("ALLOW", "BLOCK", "MODIFY", "FLAG")
ASSESSMENT_VERDICTS = ("SATISFIED", "BREACHED", "INDETERMINATE", "NOT_ASSESSED")
RISK_STATES = ("WITHIN_APPETITE", "EXPOSED", "UNTESTED")

# Every value a record's `verdict` may hold (risk states excluded on purpose).
ALL_RECORD_VERDICTS = tuple(sorted(set(DECISION_VERDICTS + RECORD_VERDICTS + RAIL_VERDICTS + ASSESSMENT_VERDICTS)))

# Which verdict type each record_kind may carry (the validator enforces it).
VERDICTS_BY_KIND = {
    "decision": DECISION_VERDICTS,
    "platform_decision": DECISION_VERDICTS,
    "rail_decision": RAIL_VERDICTS,
    "assessment": ASSESSMENT_VERDICTS,
    "finding": ("SATISFIED", "BREACHED", "INDETERMINATE", "ESCALATED"),   # = Arth's finding.VERDICTS
    "judgment": RECORD_VERDICTS,
    "handoff": RECORD_VERDICTS,
    "lifecycle": RECORD_VERDICTS,
    "action": RECORD_VERDICTS,
    "approval": RECORD_VERDICTS,
    "notification": RECORD_VERDICTS,
    "observation": RECORD_VERDICTS,
    "metric": RECORD_VERDICTS,
    "reconciliation": RECORD_VERDICTS,
    "adversarial": RECORD_VERDICTS,
    "link-gap": RECORD_VERDICTS,
}

# inline.mode / inline.action / inline.limit_applied per placement (ARCH §3.2, §4.2; rails §5.1).
C16_MODES = ("enforce", "observe")
EP0_MODES = ("block-assessed", "record-only")
INLINE_MODES = C16_MODES + EP0_MODES
C16_ACTIONS = ("proceed", "halt")
EP0_ACTIONS = ("proceed", "decline-start")
RAIL_ACTIONS = ("proceed", "block", "modify", "halt")
INLINE_ACTIONS = tuple(sorted(set(C16_ACTIONS + EP0_ACTIONS + RAIL_ACTIONS)))
LIMITS_APPLIED = ("cap", "safety-ceiling", "approved-versions")
BOUND_BASES = ("projected", "last-call-plus", "declared-fallback", "actual")

# The four-row mapping, shared by the CLI, the HTML, assessments and findings (§4.3).
#   ours -> (slides, brief, finding verdict or None, finding kind or None, kit label or None, exit code)
VERDICT_MAP = {
    "SATISFIED": ("SATISFIED", "satisfied", "SATISFIED", "finding", "PASS", 0),
    "BREACHED": ("NOT SATISFIED", "not-satisfied", "BREACHED", "finding", "BREACH", 1),
    "INDETERMINATE": (None, "insufficient-evidence", "INDETERMINATE", "monitoring-gap", "NO EVIDENCE", 2),
    "NOT_ASSESSED": (None, "not-assessed", None, None, None, 2),
}
KIT_LABEL_TO_VERDICT = {"PASS": "SATISFIED", "BREACH": "BREACHED", "NO EVIDENCE": "INDETERMINATE"}


def slides_label(verdict: str) -> "str | None":
    return VERDICT_MAP[verdict][0]


def brief_label(verdict: str) -> str:
    return VERDICT_MAP[verdict][1]


def finding_verdict(verdict: str) -> "str | None":
    """Arth's Finding verdict for an assessment verdict, or None (no finding)."""
    return VERDICT_MAP[verdict][2]


def finding_kind(verdict: str) -> "str | None":
    return VERDICT_MAP[verdict][3]


def kit_label(verdict: str) -> "str | None":
    return VERDICT_MAP[verdict][4]


def exit_code(verdict: str) -> int:
    """Our CLI exit code (= the kit's evaluate.py exit code where it has one)."""
    return VERDICT_MAP[verdict][5]


NOTIFY_VERDICTS = ("BREACHED", "INDETERMINATE", "ESCALATED")


def notify_due(verdict: str) -> bool:
    """True when a finding is notified (ARCH §3.8): BREACHED, INDETERMINATE (monitoring gap) and ESCALATED.
    Takes an assessment verdict or a finding verdict; SATISFIED and NOT_ASSESSED never notify."""
    return verdict in NOTIFY_VERDICTS


def display(verdict: str) -> str:
    """The console's display label (Arth's schema: BREACHED -> 'NOT SATISFIED')."""
    return {"BREACHED": "NOT SATISFIED", "NOT_ASSESSED": "NOT ASSESSED"}.get(verdict, verdict)


def rail_action(verdict: str, mode: str) -> str:
    """The inline.action a rail verdict implies. In observe, a BLOCK/MODIFY proceeds (rails §5.1)."""
    if verdict not in RAIL_VERDICTS:
        raise ValueError("not a rail verdict: %r" % (verdict,))
    if mode not in C16_MODES:
        raise ValueError("rail mode must be enforce|observe: %r" % (mode,))
    if mode == "observe" or verdict in ("ALLOW", "FLAG"):
        return "proceed"
    return {"BLOCK": "block", "MODIFY": "modify"}[verdict]


def is_verdict_allowed(record_kind: str, verdict: str) -> bool:
    return verdict in VERDICTS_BY_KIND.get(record_kind, ())

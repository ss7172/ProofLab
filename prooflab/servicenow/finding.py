"""The finding contract: what a control evaluator hands to the human loop.

A Finding is produced by any C7/C9/C16 evaluator (or by an agent's `escalate`
disposition) and is the only thing the ServiceNow adapter needs. Keeping this
contract small lets the AWS-side evaluators and this adapter evolve separately.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

TEAM_PREFIX = "ifabric"
CORRELATION_ID_MAX = 100  # ServiceNow incident.correlation_id length
SHORT_DESCRIPTION_MAX = 160
WORK_NOTES_EVIDENCE_MAX = 50

VERDICTS = frozenset({"BREACHED", "ESCALATED", "INDETERMINATE", "SATISFIED"})
SCOPE_KINDS = frozenset({"run", "window", "interval", "escalation"})
_ID_UNSAFE = ("^", "\n", "\r")  # would alter a ServiceNow encoded query
REQUIRED_FIELDS = ("control_ref", "control_id", "threshold_version", "scope_kind",
                   "scope_id", "verdict", "summary", "detected_at")

# urgency/impact: 1 = high, 2 = medium, 3 = low
_PRIORITY_BY_VERDICT = {"BREACHED": "2", "ESCALATED": "2", "INDETERMINATE": "3", "SATISFIED": "3"}


@dataclass(frozen=True)
class Finding:
    """One control result that a named human must be told about."""

    control_ref: str        # short label, e.g. "C16"
    control_id: str         # library id, e.g. "ACN-COST-001"
    threshold_version: str  # frozen register version, e.g. "G-FM-v1"
    scope_kind: str         # "run" | "window" | "interval" | "escalation"
    scope_id: str           # run id, window start, or ledger correlation id
    verdict: str            # one of VERDICTS
    summary: str            # measured value vs limit, human readable
    detected_at: str        # ISO-8601 UTC
    evidence: Tuple[str, ...] = ()  # record references (gateway action ids, ledger cid, ...)
    kind: str = "finding"

    @property
    def finding_id(self) -> str:
        """Stable identity: same control, version, scope and kind -> same id."""
        readable = ":".join((TEAM_PREFIX, self.control_ref, self.threshold_version,
                             self.scope_kind, self.scope_id, self.kind))
        if len(readable) <= CORRELATION_ID_MAX:
            return readable
        digest = hashlib.sha256(readable.encode()).hexdigest()[:16]
        return f"{readable[:CORRELATION_ID_MAX - len(digest) - 1]}~{digest}"


def finding_from_dict(data: Mapping) -> Finding:
    """Validate an untrusted finding (e.g. JSON from an evaluator) and build it."""
    missing = [name for name in REQUIRED_FIELDS if not str(data.get(name, "")).strip()]
    if missing:
        raise ValueError(f"finding is missing required fields: {', '.join(missing)}")
    if data["verdict"] not in VERDICTS:
        raise ValueError(f"verdict must be one of {sorted(VERDICTS)}, got {data['verdict']!r}")
    if data["scope_kind"] not in SCOPE_KINDS:
        raise ValueError(f"scope_kind must be one of {sorted(SCOPE_KINDS)}, got {data['scope_kind']!r}")
    for name in ("control_ref", "threshold_version", "scope_kind", "scope_id", "kind"):
        if any(ch in str(data.get(name) or "") for ch in _ID_UNSAFE):
            raise ValueError(f"{name} contains characters not allowed in an id (^, newline)")
    evidence = data.get("evidence") or ()
    if isinstance(evidence, str) or not all(isinstance(item, str) for item in evidence):
        raise ValueError("evidence must be a list of strings")
    return Finding(**{name: str(data[name]).strip() for name in REQUIRED_FIELDS},
                   evidence=tuple(evidence), kind=str(data.get("kind") or "finding"))


def build_incident_payload(finding: Finding, assignee_sys_id: str, team_tag: str,
                           caller_sys_id: Optional[str] = None) -> dict:
    """Map a finding to ServiceNow incident fields (no network).

    caller_sys_id is the reporter (our integration user). The incident form marks
    Caller mandatory, so without it the owner cannot press Update on the ticket.
    """
    head = f"{team_tag}[{finding.control_ref} {finding.control_id} v={finding.threshold_version}]"
    short = f"{head} {finding.scope_kind} {finding.scope_id} {finding.verdict}: {finding.summary}"
    evidence_lines = [f"  - {ref}" for ref in finding.evidence[:WORK_NOTES_EVIDENCE_MAX]]
    if len(finding.evidence) > WORK_NOTES_EVIDENCE_MAX:
        evidence_lines.append(f"  ... {len(finding.evidence) - WORK_NOTES_EVIDENCE_MAX} more in the Evidence Pack")
    work_notes = "\n".join([
        f"ProofLab finding {finding.finding_id}",
        f"Control: {finding.control_ref} {finding.control_id} (threshold version {finding.threshold_version})",
        f"Scope: {finding.scope_kind} {finding.scope_id}",
        f"Verdict: {finding.verdict} - {finding.summary}",
        f"Detected at: {finding.detected_at}",
        "Evidence records:",
        *(evidence_lines or ["  (none attached)"]),
        "A reply is not required; any note or status change by the owner is recorded as the response.",
    ])
    priority = _PRIORITY_BY_VERDICT[finding.verdict]
    caller = {"caller_id": caller_sys_id} if caller_sys_id else {}
    return {
        **caller,
        "short_description": short[:SHORT_DESCRIPTION_MAX],
        "description": (f"Automated control finding from team iFabric's assurance tool. "
                        f"{finding.control_ref} {finding.control_id} returned {finding.verdict} "
                        f"for {finding.scope_kind} {finding.scope_id}. Evidence references are in the work notes."),
        "work_notes": work_notes,
        "assigned_to": assignee_sys_id,
        "urgency": priority,
        "impact": priority,
        "correlation_id": finding.finding_id,
        "correlation_display": "ifabric-prooflab",
    }

"""The app data format: Arth's console contracts as the projection target (ARCH §3.12; work/12 §5, G-07/G-08).

The console reads `ifabric.pack-index/v1` and `ifabric.answer/v1` (handoff-3
`evidence-console-plan/schemas/contracts.schema.json`, the acceptance oracle). Our records stay
`ifabric.evidence/1`; this module holds only the projection's fixed points: schema ids, required keys,
the enums the target schema forces, the ours->theirs mapping tables, and the deterministic answer id.
A parity test checks these constants against Arth's schema file when it is present.
"""
from __future__ import annotations

import hashlib
import json

PACK_INDEX_SCHEMA = "ifabric.pack-index/v1"
ANSWER_SCHEMA = "ifabric.answer/v1"
RUN_SCHEMA = "ifabric.run/v1"
CONSOLE_EVIDENCE_SCHEMA = "ifabric.evidence/v1"     # theirs (a projection), not our ifabric.evidence/1

PACK_INDEX_REQUIRED = (
    "schema", "generated_at", "provenance", "pack", "claim", "register", "artefacts", "named_runs", "runs",
    "findings", "answers", "auditor", "adversarial", "gaps", "levels", "enforcement_points", "integrity",
)
ANSWER_REQUIRED = (
    "schema", "answer_id", "query", "answered_at", "elapsed_ms", "source", "provenance", "control", "rule",
    "scope", "population", "measurement", "comparison", "exceptions", "verdict", "enforcement",
    "audit_question", "human_loops", "aict", "records", "gaps", "tickmarks",
)

CONSOLE_PROVENANCE = ("ASSESSED", "EXPLORATORY", "WIRING_TEST", "SYNTHETIC")
CONSOLE_VERDICTS = ("SATISFIED", "BREACHED", "INDETERMINATE", "NOT_ASSESSED")
CONSOLE_CLAIM_VERDICTS = ("SATISFIED", "NOT_SATISFIED", "NOT_ESTABLISHED")
CONSOLE_CONTROL_REFS = ("C7", "C9", "C16", "ESC")
CONSOLE_CONTROL_IDS = ("AIA-LOG-001", "AIA-ARC-006", "ACN-COST-001", "AGENT-ESCALATION")
CONSOLE_CONTROL_MODES = ("static", "scheduled", "event-driven", "in-transaction", "continuous")
CONSOLE_SCOPE_KINDS = ("run", "window", "interval", "incident", "escalation")
CONSOLE_INLINE_DECISIONS = ("ALLOW", "ALERT", "DENY")
ANSWER_SOURCE_MODES = ("PACK", "LIVE")
MANIFEST_STATUSES = ("VERIFIED", "MODIFIED", "UNVERIFIED")

# G-07: provenance. Membership first: a CID listed in run-ids.txt -> ASSESSED whatever its value.
PROVENANCE_TO_CONSOLE = {
    "LIVE_SUBJECT": "ASSESSED",
    "EXPLORATORY": "EXPLORATORY", "PILOT": "EXPLORATORY", "BASELINE": "EXPLORATORY",
    "AUTHORIZED_TEST": "EXPLORATORY", "FAULT_INJECTION": "EXPLORATORY", "REPLAY": "EXPLORATORY",
    "COUNTERFACTUAL_EXPORT": "EXPLORATORY", "UNATTRIBUTED": "EXPLORATORY",
    "SYNTHETIC": "SYNTHETIC",          # never enters the pack
}

# G-07: record kinds (assessments and findings go to their own files; others are not projected).
RECORD_KIND_TO_CONSOLE = {
    "handoff": "event", "lifecycle": "event", "judgment": "event", "notification": "event",
    "metric": "window", "decision": "decision", "approval": "approval",
}


def console_provenance(provenance: str, named: bool = False) -> str:
    return "ASSESSED" if named else PROVENANCE_TO_CONSOLE[provenance]


def console_record_kind(record_kind: str, tool_name=None) -> "str | None":
    if record_kind == "action":
        return "tool-call" if tool_name else "model-call"
    return RECORD_KIND_TO_CONSOLE.get(record_kind)


def console_inline_decision(verdict: str, mode: str) -> str:
    """DENY in observe -> ALERT ('would deny'); DENY in enforce -> DENY; ALLOW -> ALLOW."""
    if verdict == "ALLOW":
        return "ALLOW"
    if verdict == "DENY":
        return "ALERT" if mode == "observe" else "DENY"
    raise ValueError("not a decision verdict: %r" % (verdict,))


def console_control_ref(control_ref: str) -> "str | None":
    """INV, APPROVAL, PLATFORM, RAIL, NONE are not projected as records or findings."""
    return control_ref if control_ref in CONSOLE_CONTROL_REFS else None


def answer_id_of(answer: dict) -> str:
    """Arth's deterministic answer id (generate_examples.py answer_id_of): sha256 of the canonical JSON
    without answer_id, answered_at, elapsed_ms and source.mode."""
    stable = dict((k, v) for k, v in answer.items() if k not in ("answer_id", "answered_at", "elapsed_ms"))
    stable["source"] = dict((k, v) for k, v in answer["source"].items() if k != "mode")
    return hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def missing_keys(obj: dict, required) -> list:
    return [k for k in required if k not in obj]

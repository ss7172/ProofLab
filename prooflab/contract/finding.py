"""The Finding contract: the dict our evaluators hand to Arth's human loop (ARCH §3.8; work/12 §5; G-13).

It maps EXACTLY onto `prooflab.servicenow.finding.finding_from_dict` (Arth's, never edited): the same
required fields, verdicts, scope kinds and id rules, plus the optional handoff-3 context keys
(`measured`, `limit`, `register`, `trace`, `retest`; `finding_context.parse_context`). This module does
not import Arth's package, so the contract stays standalone; tests/contract round-trips through it.
"""
from __future__ import annotations

import hashlib

from prooflab.contract import verdicts as _v

TEAM_PREFIX = "ifabric"
CORRELATION_ID_MAX = 100
REQUIRED_FIELDS = ("control_ref", "control_id", "threshold_version", "scope_kind",
                   "scope_id", "verdict", "summary", "detected_at")
VERDICTS = ("BREACHED", "ESCALATED", "INDETERMINATE", "SATISFIED")
SCOPE_KINDS = ("run", "window", "interval", "escalation")
KINDS = ("finding", "monitoring-gap")
CONTEXT_KEYS = ("measured", "limit", "register", "trace", "retest")
LIMIT_OPERATORS = ("<=", "<", ">=", ">", "==")
_ID_UNSAFE = ("^", "\n", "\r")


def validate_finding(data) -> list:
    """The same refusals as Arth's finding_from_dict (required core; context shapes checked lightly)."""
    if not isinstance(data, dict):
        return ["finding must be an object"]
    errors = []
    for name in REQUIRED_FIELDS:
        if not str(data.get(name, "") if data.get(name) is not None else "").strip():
            errors.append("%s: required" % name)
    if data.get("verdict") not in VERDICTS:
        errors.append("verdict: must be one of %s" % list(VERDICTS))
    if data.get("scope_kind") not in SCOPE_KINDS:
        errors.append("scope_kind: must be one of %s" % list(SCOPE_KINDS))
    for name in ("control_ref", "threshold_version", "scope_kind", "scope_id", "kind"):
        if any(ch in str(data.get(name) or "") for ch in _ID_UNSAFE):
            errors.append("%s: contains ^ or a newline" % name)
    evidence = data.get("evidence") or []
    if isinstance(evidence, str) or not all(isinstance(e, str) for e in evidence):
        errors.append("evidence: must be a list of strings")
    unknown = set(data) - set(REQUIRED_FIELDS) - {"evidence", "kind"} - set(CONTEXT_KEYS)
    if unknown:
        errors.append("unknown keys: %s" % sorted(unknown))
    lim = data.get("limit")
    if lim is not None and (not isinstance(lim, dict) or lim.get("operator") not in LIMIT_OPERATORS):
        errors.append("limit.operator: must be one of %s" % list(LIMIT_OPERATORS))
    return errors


def make_finding(control_ref, control_id, threshold_version, scope_kind, scope_id, verdict, summary,
                 detected_at, evidence=(), kind="finding", measured=None, limit=None, register=None,
                 trace=None, retest=None) -> dict:
    """A Finding dict ready for finding_from_dict. Raises ValueError on the refusals Arth's code would make."""
    if isinstance(evidence, str):
        raise ValueError("invalid finding: evidence: must be a list of strings")
    data = {
        "control_ref": control_ref, "control_id": control_id, "threshold_version": threshold_version,
        "scope_kind": scope_kind, "scope_id": scope_id, "verdict": verdict, "summary": summary,
        "detected_at": detected_at, "evidence": list(evidence), "kind": kind,
    }
    for key, value in (("measured", measured), ("limit", limit), ("register", register),
                       ("trace", trace), ("retest", retest)):
        if value is not None:
            data[key] = value
    errors = validate_finding(data)
    if errors:
        raise ValueError("invalid finding: " + "; ".join(errors))
    return data


def finding_id(data: dict) -> str:
    """Arth's Finding.finding_id, recomputed: same control, version, scope and kind -> same id."""
    readable = ":".join((TEAM_PREFIX, str(data["control_ref"]).strip(), str(data["threshold_version"]).strip(),
                         str(data["scope_kind"]).strip(), str(data["scope_id"]).strip(),
                         str(data.get("kind") or "finding")))
    if len(readable) <= CORRELATION_ID_MAX:
        return readable
    digest = hashlib.sha256(readable.encode()).hexdigest()[:16]
    return "%s~%s" % (readable[:CORRELATION_ID_MAX - len(digest) - 1], digest)


def finding_from_assessment(assessment: dict, summary: str, detected_at: str, evidence=(), **context) -> "dict | None":
    """The §4.3 mapping: BREACHED -> BREACHED; INDETERMINATE -> INDETERMINATE kind monitoring-gap;
    SATISFIED -> a SATISFIED finding (no notify; callers check verdicts.notify_due); NOT_ASSESSED -> None.
    `assessment` uses the §3.2 Assessment field names. The summary should start with the deficiency."""
    verdict = _v.finding_verdict(assessment["requirement_verdict"])
    if verdict is None:
        return None
    return make_finding(
        assessment["control_ref"], assessment["control_id"], assessment["threshold_version"],
        assessment["scope_kind"], assessment["scope_id"], verdict, summary, detected_at,
        evidence=evidence, kind=_v.finding_kind(assessment["requirement_verdict"]) or "finding", **context)

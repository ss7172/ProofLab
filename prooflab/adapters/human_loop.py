"""Glue between our evaluators and Arth's human loop (ARCH §3.8; G-04). Stdlib, 3.9.

* build_finding(assessment, ...) -> a Finding dict that passes `prooflab.servicenow.finding.finding_from_dict`
  (scope_id = the CID, D22; templated summary; <= 8 evidence refs; context measured / limit / register).
* build_approval_finding(doc, ...) -> the `kind: approval` finding (T2) from PR-11's approval-finding.json.
* notify_due(finding) -> BREACHED, ESCALATED and monitoring-gap only; SATISFIED never (ARCH §3.8).
* sticky_response(entries) -> guard (b): a logged RESPONDED is never overwritten by later states.

The coupling to the shared contract is the one import line below. Arth's code is never edited.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional

from prooflab.contract import clocks as _clocks, finding as _cfinding, verdicts as _cverdicts  # the one site

SUMMARY_MAX = 200
EVIDENCE_MAX = 8
TEXT_MAX = 200
_WS = re.compile(r"\s+")


def _clean(value, limit: int = TEXT_MAX) -> str:
    """One line, no ';' (evidence separator), bounded."""
    return _WS.sub(" ", str(value)).replace(";", ",").strip()[:limit]


def _evidence(refs: Iterable) -> List[str]:
    out: List[str] = []
    for ref in refs or ():
        text = _clean(ref, 300)
        if text and text not in out:
            out.append(text)
    return out[:EVIDENCE_MAX]


def _fmt(value) -> str:
    return str(int(value)) if isinstance(value, float) and value == int(value) else str(value)


def _measure(assessment: dict, measured: Optional[dict]) -> Optional[dict]:
    block = measured if measured is not None else assessment.get("measured")
    if isinstance(block, dict) and "value" in block and block.get("unit"):
        return {"value": block["value"], "unit": _clean(block["unit"], 40)}
    return None


def summarise(control_id: str, verdict: str, scope_kind: str, scope_id: str,
              measured: Optional[dict], limit: Optional[dict]) -> str:
    """The templated summary: control, verdict, scope, measured vs limit. Never agent or model text."""
    text = "%s %s for %s %s" % (control_id, verdict, scope_kind, scope_id)
    if measured and limit and measured.get("unit") == limit.get("unit"):
        text += ": measured %s %s, limit %s %s" % (_fmt(measured["value"]), measured["unit"],
                                                    limit["operator"], _fmt(limit["value"]))
    return _clean(text, SUMMARY_MAX)


def build_finding(assessment: dict, cid: str, owner: str, version_date: str, limit: Optional[dict] = None,
                  approval: Optional[str] = None, evidence: Iterable = (), measured: Optional[dict] = None,
                  detected_at: Optional[str] = None) -> Optional[dict]:
    """A finding dict from a PR-09a assessment dict (the §3.2 field names), or None for NOT_ASSESSED.

    `limit` is {"value", "operator", "unit"} from the register (same unit as measured). For a run-scope
    assessment, `scope_id` must be the CID (D22). The caller passes `owner` (SNOW_OWNER_USER)."""
    if not cid:
        raise ValueError("cid is required (the Finding scope_id is the CID, D22)")
    scope_kind, scope_id = assessment["scope_kind"], assessment["scope_id"]
    if scope_kind == "run":
        if scope_id not in (cid, ""):
            raise ValueError("run-scope assessment scope_id %r is not the CID %r" % (scope_id, cid))
        scope_id = cid
    refs = list(evidence) + list(assessment.get("evidence_refs") or ())
    meas = _measure(assessment, measured)
    verdict = _cverdicts.finding_verdict(assessment["requirement_verdict"])
    if verdict is None:
        return None
    ctx = {}
    if meas:
        ctx["measured"] = meas
    if limit:
        ctx["limit"] = {"value": limit["value"], "operator": limit["operator"], "unit": _clean(limit["unit"], 40)}
    ctx["register"] = {"version_date": _clean(version_date, 40), "owner": _clean(owner, 100)}
    if approval:
        ctx["register"]["approval"] = _clean(approval, 100)
    summary = summarise(assessment["control_id"], verdict, scope_kind, scope_id, meas, limit)
    return _cfinding.make_finding(
        assessment["control_ref"], assessment["control_id"], assessment["threshold_version"], scope_kind, scope_id,
        verdict, summary, detected_at or _clocks.now_utc(), evidence=_evidence(refs),
        kind=_cverdicts.finding_kind(assessment["requirement_verdict"]) or "finding", **ctx)


def build_approval_finding(doc: dict, detected_at: Optional[str] = None) -> dict:
    """The T2 approval finding from PR-11's approval-finding.json (kind approval, verdict ESCALATED)."""
    if doc.get("kind") != "approval":
        raise ValueError("not an approval finding (kind must be 'approval')")
    data = dict(doc)
    if detected_at:
        data["detected_at"] = detected_at
    data["summary"] = _clean(data.get("summary", ""), SUMMARY_MAX)
    data["evidence"] = _evidence(data.get("evidence"))
    errors = _cfinding.validate_finding(data)
    if errors:
        raise ValueError("invalid approval finding: " + "; ".join(errors))
    return data


def notify_due(finding: dict) -> bool:
    """BREACHED, ESCALATED and monitoring-gap findings are notified; SATISFIED (and plain INDETERMINATE) never.

    ARCH §3.8 at finding level, delegating to the contract's verdict rule (prooflab.contract.verdicts.notify_due,
    PR-01 round 2: BREACHED, INDETERMINATE, ESCALATED). The one refinement: an INDETERMINATE verdict is notified
    as its `kind: monitoring-gap` finding, never as a plain finding.
    """
    verdict = finding.get("verdict")
    if verdict == _cverdicts.SATISFIED:
        return False
    if finding.get("kind") == "monitoring-gap":
        return True
    return verdict != _cverdicts.INDETERMINATE and _cverdicts.notify_due(verdict)


def is_approval(finding: dict) -> bool:
    return finding.get("kind") == "approval"


def sticky_response(entries: Iterable[dict]) -> Optional[dict]:
    """Guard (b): the earliest logged RESPONDED entry wins over every later state (never latest-wins)."""
    for entry in entries:
        if entry.get("state") == "RESPONDED":
            return entry
    return None


# --- PR-20b: the trace, the re-test link and the closed-without-re-test gap (ARCH §3.8) -------------------
TRACE_MAX = 200
ZONES = ("customer", "it", "network", "gateway", "other")
CLOSED_WITHOUT_RETEST = "closed in ServiceNow without re-test"
RETEST_NOTE_PREFIX = "[iFabric re-test]"


def build_trace(steps: Iterable[dict], agent_zones: Optional[dict] = None) -> List[dict]:
    """A finding `trace` (<= 200 steps) from our records: dicts with at / actor / action and optional
    decision / ref / run_id / zone. A step whose actor has no known zone is `other` (our handoffs).
    The newest TRACE_MAX steps are kept, in time order; text is one line and bounded."""
    zones = agent_zones or {}
    out = []
    for step in steps or ():
        at, actor, action = step.get("at"), step.get("actor"), step.get("action")
        if not (at and actor and action):
            continue
        zone = step.get("zone") or zones.get(actor) or "other"
        out.append({"at": _clean(at, 40), "actor": _clean(actor, 100), "zone": zone if zone in ZONES else "other",
                    "action": _clean(action, 100), "decision": _clean(step.get("decision", ""), 100),
                    "ref": _clean(step.get("ref", ""), 200), "run_id": _clean(step.get("run_id", ""), 100)})
    out.sort(key=lambda s: s["at"])
    return out[-TRACE_MAX:]


def build_retest(assessment: dict, at: Optional[str] = None) -> Optional[dict]:
    """The `retest` block from a later assessment on the same control and scope type; None unless it is
    the assessment's own SATISFIED-or-other verdict mapped onto the finding verdict (NOT_ASSESSED: None)."""
    verdict = _cverdicts.finding_verdict(assessment["requirement_verdict"])
    if verdict is None:
        return None
    ref = assessment.get("assessment_id") or assessment.get("id") or assessment["scope_id"]
    return {"assessment": _clean("assessment:%s" % ref, 200), "verdict": verdict,
            "threshold_version": _clean(assessment["threshold_version"], 100), "at": at or _clocks.now_utc()}


def closes(finding: dict, retest: Optional[dict]) -> bool:
    """Only a SATISFIED re-test on the finding's own threshold version closes it (R-J-24)."""
    return bool(retest) and retest.get("verdict") == _cverdicts.SATISFIED \
        and retest.get("threshold_version") == finding.get("threshold_version")


def retest_note(finding: dict, retest: dict) -> str:
    """The work note linking an incident to its re-test; one line, templated, never model text."""
    return _clean("%s finding %s: re-test %s is %s on %s (%s)" % (
        RETEST_NOTE_PREFIX, finding.get("id") or "%s/%s" % (finding.get("control_ref"), finding.get("scope_id")),
        retest["assessment"], retest["verdict"], retest["threshold_version"], retest.get("at", "")), 500)


def closed_without_retest(export_doc: dict, retest: Optional[dict], finding: dict,
                          closed_states: Iterable[str] = ("6", "7", "Resolved", "Closed")) -> Optional[dict]:
    """A gap entry when an exported incident is closed in ServiceNow with no linked passing re-test; the
    finding stays open in the pack. `closed_states` are ServiceNow's own labels (display or value)."""
    incident = export_doc.get("incident") or {}
    state = incident.get("state")
    state = state.get("display_value") or state.get("value") if isinstance(state, dict) else state
    if str(state) not in tuple(closed_states) or closes(finding, retest):
        return None
    return {"gap": CLOSED_WITHOUT_RETEST, "finding_id": export_doc.get("finding_id"),
            "incident": incident.get("number"), "servicenow_state": str(state), "finding_status": "open"}

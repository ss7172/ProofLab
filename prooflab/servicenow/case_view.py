"""One JSON object per finding for the GUI: the ServiceNow half of the evidence chain.

  finding (from the AWS-side evaluator) -> delivery (our log) -> incident (ServiceNow)
  -> owner response -> Assurance Agent analysis -> AICT trace link
plus five computed assurance sections (assurance_checks.py): movement, decision_trace,
evidence, policy_alignment, outcome_validation.

Safe to poll: it only reads ServiceNow and the delivery log, never writes either,
and reports ServiceNow outages as data instead of raising.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional, Tuple, Union

from prooflab.servicenow.analysis import facts_match, latest_agent_analysis, trusted_digests
from prooflab.servicenow.assurance_checks import (classify_evidence, decision_trace, movement, outcome_validation,
                                                  policy_alignment)
from prooflab.servicenow.client import ServiceNowClient, ServiceNowError
from prooflab.servicenow.delivery_log import DeliveryLog, utc_now_iso
from prooflab.servicenow.finding import Finding
from prooflab.servicenow.notifier import (DEFAULT_AGENT_USER, DEFAULT_INTEGRATION_USER,
                                          check_response)

CASE_SCHEMA = "ifabric.servicenow.case/v1"
DELIVERY_STATES = ("DELIVERED", "FAILED", "UNVERIFIED", "OUTCOME_UNKNOWN", "DRY_RUN")
DISPLAY_FIELDS = ("number", "short_description", "state", "assigned_to", "urgency",
                  "sys_updated_on", "sys_updated_by", "work_notes")
_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]")


class _ReadOnlyLog:
    """Lets check_response classify for display without adding evidence-log entries."""

    def __init__(self, log: DeliveryLog) -> None:
        self._log = log

    def append(self, finding_id: str, state: str, **details) -> dict:
        return {"finding_id": finding_id, "state": state, **details}

    def history(self, finding_id: str) -> list:
        return self._log.history(finding_id)


def _finding_dict(finding: Finding) -> dict:
    return {"control_ref": finding.control_ref, "control_id": finding.control_id,
            "threshold_version": finding.threshold_version, "scope_kind": finding.scope_kind,
            "scope_id": finding.scope_id, "verdict": finding.verdict, "summary": finding.summary,
            "detected_at": finding.detected_at, "evidence": list(finding.evidence),
            "kind": finding.kind}


def delivery_state(log: DeliveryLog, finding_id: str) -> str:
    return _delivery(log, finding_id)["state"]


def _delivery(log: DeliveryLog, finding_id: str) -> dict:
    for entry in reversed(log.history(finding_id)):
        if entry.get("state") in DELIVERY_STATES:
            return {"state": entry["state"], "at": entry.get("ts"), "number": entry.get("number")}
    return {"state": "NOT_SENT", "at": None, "number": None}


def _agent_run(log: DeliveryLog, finding_id: str) -> dict:
    """The assurance agent's last run as recorded in the delivery log (WRITTEN, REFUSED, ...)."""
    for entry in reversed(log.history(finding_id)):
        state = entry.get("state", "")
        if state.startswith("ANALYSIS_"):
            return {"state": state[len("ANALYSIS_"):], "at": entry.get("ts"), "reason": entry.get("reason"),
                    "backend": entry.get("backend"), "model_alias": entry.get("model_alias"),
                    "action_ids": entry.get("action_ids") or [], "evidence": entry.get("evidence")}
    return {"state": "NOT_RUN"}


def _response(outcome, log: DeliveryLog, finding_id: str, cutoff: str) -> dict:
    """A logged RESPONDED is sticky: itil sees only the last updater, so a later write by
    the agent or the integration user must not turn a recorded reply back into silence."""
    if outcome.state != "RESPONDED":
        for entry in reversed(log.history(finding_id)):
            if entry.get("state") == "RESPONDED":
                return {"state": "RESPONDED", "actor": entry.get("actor"), "at": entry.get("at"),
                        "cutoff": cutoff, "source": "delivery_log"}
    return {"state": outcome.state, "actor": outcome.actor, "at": outcome.at, "cutoff": cutoff,
            "source": "live"}


def display_text(value) -> Optional[str]:
    """Display values may arrive as {"display_value", "link"} objects; the GUI wants text."""
    if isinstance(value, dict):
        return value.get("display_value")
    return value


def owner_response(finding: Finding, client: ServiceNowClient, log: DeliveryLog, owner_user: str,
                   cutoff: str, integration_user: str = DEFAULT_INTEGRATION_USER,
                   agent_user: str = DEFAULT_AGENT_USER, now: Optional[str] = None) -> dict:
    """The owner's response as the GUI and the assurance agent both see it (never writes the log)."""
    outcome = check_response(finding, client, _ReadOnlyLog(log), owner_user=owner_user,
                             cutoff=cutoff, integration_user=integration_user, now=now,
                             agent_user=agent_user)
    return _response(outcome, log, finding.finding_id, cutoff)


def _incident_part(client: ServiceNowClient, sys_id: str, display: dict) -> dict:
    url = f"{client.base_url}/incident.do?sys_id={sys_id}"
    text = {key: display_text(display.get(key)) for key in DISPLAY_FIELDS}
    return {"status": "ok", "sys_id": sys_id, "url": url, "number": text["number"],
            "short_description": text["short_description"], "state": text["state"],
            "owner": text["assigned_to"], "urgency": text["urgency"],
            "updated_at": text["sys_updated_on"], "updated_by": text["sys_updated_by"]}


def case_view(finding: Finding, client: ServiceNowClient, log: DeliveryLog, owner_user: str,
              cutoff: str, integration_user: str = DEFAULT_INTEGRATION_USER,
              agent_user: str = DEFAULT_AGENT_USER, aict_url: Optional[str] = None,
              now: Optional[str] = None) -> dict:
    fid = finding.finding_id
    case = {"schema": CASE_SCHEMA, "generated_at": now or utc_now_iso(), "finding_id": fid,
            "finding": _finding_dict(finding), "delivery": _delivery(log, fid),
            "agent_run": _agent_run(log, fid), "links": {"incident": None, "aict": aict_url}}
    case["response"] = owner_response(finding, client, log, owner_user, cutoff,
                                      integration_user, agent_user, now)
    try:
        rows = client.find_incidents(fid, integration_user)
        if not rows:
            case = {**case, "servicenow": {"status": "no_incident"},
                    "agent_analysis": {"status": "not_applicable"}}
            return _with_sections(case, finding, log, owner_user)
        display = client.get_incident_display(rows[0]["sys_id"], DISPLAY_FIELDS)
    except ServiceNowError as err:
        case = {**case, "servicenow": {"status": "unreachable", "error": str(err)},
                "agent_analysis": {"status": "unknown"}}
        return _with_sections(case, finding, log, owner_user)
    incident = _incident_part(client, rows[0]["sys_id"], display)
    analysis = latest_agent_analysis(display_text(display.get("work_notes")), fid,
                                     trusted_digests(log.history(fid)))
    agent_analysis = ({**analysis.to_dict(), "facts_match": facts_match(analysis.fields, finding)}
                      if analysis else {"status": "pending"})
    case = {**case, "servicenow": incident, "links": {"incident": incident["url"], "aict": aict_url},
            "agent_analysis": agent_analysis}
    return _with_sections(case, finding, log, owner_user)


def record_ref(path: Path, log: DeliveryLog) -> str:
    """Store run-record paths relative to the delivery log, so any reader of the log finds them."""
    try:
        return os.path.relpath(Path(path).resolve(), log.path.resolve().parent)
    except ValueError:  # different drive on Windows
        return str(Path(path).resolve())


def _run_record(log: DeliveryLog, agent_run: dict) -> Optional[dict]:
    ref = agent_run.get("evidence")
    if not ref:
        return None
    path = Path(ref) if Path(ref).is_absolute() else log.path.resolve().parent / ref
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _with_sections(case: dict, finding: Finding, log: DeliveryLog, owner_user: str) -> dict:
    record = _run_record(log, case["agent_run"])
    analysis = case["agent_analysis"]
    return {**case,
            "movement": movement(finding),
            "decision_trace": decision_trace(finding, log.history(finding.finding_id), record),
            "evidence": classify_evidence(finding, analysis.get("fields")),
            "policy_alignment": policy_alignment(finding, delivery_state=case["delivery"]["state"],
                                                 response_state=case["response"]["state"],
                                                 incident_state=(case["servicenow"].get("state") or ""),
                                                 owner_user=owner_user),
            "outcome_validation": outcome_validation(finding, case["agent_run"], analysis, record)}


def write_case_snapshot(case: dict, out_dir: Union[str, Path]) -> Tuple[Path, str]:
    """Save the case as an evidence file; returns (path, sha256 of the bytes written)."""
    data = json.dumps(case, indent=2, sort_keys=True).encode("utf-8")
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{_UNSAFE_FILENAME.sub('_', case['finding_id'])}.json"
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()

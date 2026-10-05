"""Human loop: tell the named owner about a finding, then observe their response.

notify()
  INTENT -> existing own incident? -> DELIVERED (reused)
         -> SENT -> readback -> DELIVERED | FAILED(readback_mismatch) | UNVERIFIED(readback_failed)
  no clean answer to the create (timeout, 5xx, garbled body) -> OUTCOME_UNKNOWN, then
  reconciled by correlation id -> DELIVERED(reconciled) -- never re-sent blindly.
check_response()
  RESPONDED (owner only) | AWAITING_RESPONSE | NO_RESPONSE_OBSERVED (after cutoff)
  | RESPONSE_UNKNOWN (history unreadable) | NOT_DELIVERED

Every step is appended to the DeliveryLog, and every path ends in a terminal
state. Only incidents created by our integration user are ever considered, so
other teams' records on the shared instance are never read as ours.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from prooflab.servicenow.client import ServiceNowClient, ServiceNowError, check_query_value
from prooflab.servicenow.delivery_log import DeliveryLog, utc_now_iso
from prooflab.servicenow.finding import Finding, build_incident_payload

DEFAULT_TEAM_TAG = "[iFabric]"
DEFAULT_INTEGRATION_USER = "ifabric.integration"


@dataclass(frozen=True)
class DeliveryResult:
    finding_id: str
    state: str
    number: Optional[str] = None
    sys_id: Optional[str] = None
    reused: bool = False
    reason: Optional[str] = None


@dataclass(frozen=True)
class ResponseOutcome:
    finding_id: str
    state: str
    number: Optional[str] = None
    actor: Optional[str] = None
    at: Optional[str] = None


def _ref_value(field) -> str:
    """Reference fields come back as a sys_id string or {"value": sys_id, "link": ...}."""
    if isinstance(field, dict):
        return str(field.get("value", ""))
    return str(field or "")


def _parse_utc(value: str) -> datetime:
    """Accepts YYYY-MM-DDTHH:MM:SS[Z|+00:00]; raises ValueError otherwise."""
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _own_incident(finding: Finding, client: ServiceNowClient, log: DeliveryLog,
                  integration_user: str) -> Optional[dict]:
    rows = client.find_incidents(finding.finding_id, integration_user)
    if len(rows) > 1:
        log.append(finding.finding_id, "DUPLICATE_CORRELATION",
                   sys_ids=[row["sys_id"] for row in rows], used=rows[0]["sys_id"])
    return rows[0] if rows else None


def _confirm(finding: Finding, client: ServiceNowClient, log: DeliveryLog, sys_id: str,
             assignee_sys_id: str, reused: bool, reconciled: bool = False) -> DeliveryResult:
    """Only a readback with the right correlation (and, when fresh, the right assignee) counts."""
    fid = finding.finding_id
    try:
        incident = client.get_incident(sys_id)
    except ServiceNowError as err:
        log.append(fid, "UNVERIFIED", sys_id=sys_id, reason="readback_failed", detail=str(err))
        return DeliveryResult(fid, "UNVERIFIED", sys_id=sys_id, reused=reused, reason="readback_failed")
    current_assignee = _ref_value(incident.get("assigned_to"))
    # A reused incident may have been reassigned by the owner since; that is not a delivery failure.
    assignee_ok = reused or current_assignee == assignee_sys_id
    if incident.get("correlation_id") != fid or not assignee_ok:
        log.append(fid, "FAILED", reason="readback_mismatch", sys_id=sys_id,
                   number=incident.get("number"), assigned_to=current_assignee)
        return DeliveryResult(fid, "FAILED", incident.get("number"), sys_id, reused, "readback_mismatch")
    log.append(fid, "DELIVERED", sys_id=sys_id, number=incident.get("number"),
               assigned_to=current_assignee, intended_assignee=assignee_sys_id,
               reused=reused, reconciled=reconciled)
    return DeliveryResult(fid, "DELIVERED", incident.get("number"), sys_id, reused)


def _reconcile(finding: Finding, client: ServiceNowClient, log: DeliveryLog,
               integration_user: str, assignee_sys_id: str) -> DeliveryResult:
    fid = finding.finding_id
    try:
        found = _own_incident(finding, client, log, integration_user)
    except ServiceNowError as err:
        log.append(fid, "OUTCOME_UNKNOWN", reason="reconcile_failed", detail=str(err))
        return DeliveryResult(fid, "OUTCOME_UNKNOWN", reason="reconcile_failed")
    if found:
        return _confirm(finding, client, log, found["sys_id"], assignee_sys_id,
                        reused=True, reconciled=True)
    log.append(fid, "OUTCOME_UNKNOWN", reason="no_record_found_yet")
    return DeliveryResult(fid, "OUTCOME_UNKNOWN", reason="no_record_found_yet")


def notify(finding: Finding, client: ServiceNowClient, log: DeliveryLog, owner_user: str,
           integration_user: str = DEFAULT_INTEGRATION_USER, team_tag: str = DEFAULT_TEAM_TAG,
           dry_run: bool = False) -> DeliveryResult:
    fid = check_query_value(finding.finding_id)  # bad ids fail before anything is logged
    try:
        assignee = client.find_user_sys_id(owner_user)
    except ServiceNowError as err:
        log.append(fid, "FAILED", reason="owner_lookup", status=err.status, detail=str(err))
        return DeliveryResult(fid, "FAILED", reason="owner_lookup")

    try:
        caller = client.find_user_sys_id(integration_user)
    except ServiceNowError:
        caller = None  # optional: incident still valid, only the form's Caller stays empty
    payload = build_incident_payload(finding, assignee, team_tag, caller_sys_id=caller)
    log.append(fid, "INTENT", owner=owner_user, caller=caller, control=finding.control_ref,
               scope=f"{finding.scope_kind}:{finding.scope_id}", verdict=finding.verdict)
    try:
        existing = _own_incident(finding, client, log, integration_user)
    except ServiceNowError as err:
        log.append(fid, "FAILED", reason="lookup_failed", status=err.status, detail=str(err))
        return DeliveryResult(fid, "FAILED", reason="lookup_failed")
    if existing:
        return _confirm(finding, client, log, existing["sys_id"], assignee, reused=True)
    if dry_run:
        log.append(fid, "DRY_RUN", payload=payload)
        return DeliveryResult(fid, "DRY_RUN")

    try:
        created = client.create_incident(payload)
    except ServiceNowError as err:
        if not err.outcome_unknown:
            log.append(fid, "FAILED", reason="create_rejected", status=err.status, detail=str(err))
            return DeliveryResult(fid, "FAILED", reason="create_rejected")
        log.append(fid, "OUTCOME_UNKNOWN", status=err.status, detail=str(err))
        return _reconcile(finding, client, log, integration_user, assignee)
    log.append(fid, "SENT", sys_id=created.get("sys_id"), number=created.get("number"))
    return _confirm(finding, client, log, created["sys_id"], assignee, reused=False)


def export_incident(finding: Finding, client: ServiceNowClient, integration_user: str,
                    out_dir: Union[str, Path]) -> Path:
    """Write the incident as ServiceNow stores it, plus its notes, as an evidence file."""
    rows = client.find_incidents(finding.finding_id, integration_user)
    if not rows:
        raise LookupError(f"no incident created by {integration_user} for {finding.finding_id}")
    incident = client.get_incident(rows[0]["sys_id"])
    try:
        journal, journal_error = client.list_work_notes(incident["sys_id"]), None
    except ServiceNowError as err:  # e.g. itil user may not read sys_journal_field via the API
        journal, journal_error = None, str(err)
    try:
        notes_text = client.get_incident_notes_text(incident["sys_id"])
        notes_display = {"work_notes": notes_text.get("work_notes", ""),
                         "comments": notes_text.get("comments", "")}
    except ServiceNowError as err:
        notes_display = {"error": str(err)}
    record = {
        "finding_id": finding.finding_id,
        "exported_at": utc_now_iso(),
        "source": f"{client.base_url}/api/now/table/incident/{incident['sys_id']}",
        "incident": incident,
        "journal": journal,
        "journal_error": journal_error,
        "notes_display": notes_display,
    }
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{incident.get('number') or incident['sys_id']}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _actions(client: ServiceNowClient, incident: dict, owner_user: str,
             integration_user: str) -> Tuple[List[Tuple[str, str]], Set[str], bool]:
    """Owner actions as (at, basis); other human/system actors; whether history was readable."""
    owner_actions: List[Tuple[str, str]] = []
    others: Set[str] = set()
    ignored = {"", None, integration_user}
    readable = True
    try:
        for note in client.list_work_notes(incident["sys_id"]):
            author, at = note.get("sys_created_by"), note.get("sys_created_on")
            if author == owner_user and at:
                owner_actions.append((at, "work_note"))
            elif author not in ignored:
                others.add(author)
    except ServiceNowError:
        readable = False
    updated_by, updated_on = incident.get("sys_updated_by"), incident.get("sys_updated_on")
    if updated_by == owner_user and updated_on:
        owner_actions.append((updated_on, "last_update"))
    elif updated_by not in ignored:
        others.add(updated_by)
    return owner_actions, others, readable


def check_response(finding: Finding, client: ServiceNowClient, log: DeliveryLog, owner_user: str,
                   cutoff: str, integration_user: str = DEFAULT_INTEGRATION_USER,
                   now: Optional[str] = None) -> ResponseOutcome:
    """Classify the owner's reaction; silence only counts once the cutoff has passed."""
    fid = finding.finding_id
    now = now or utc_now_iso()
    cutoff_at, now_at = _parse_utc(cutoff), _parse_utc(now)  # bad input fails before any call
    try:
        incident = _own_incident(finding, client, log, integration_user)
    except ServiceNowError as err:
        log.append(fid, "RESPONSE_UNKNOWN", reason="lookup_failed", detail=str(err), checked_at=now)
        return ResponseOutcome(fid, "RESPONSE_UNKNOWN")
    if not incident:
        log.append(fid, "NOT_DELIVERED", checked_at=now)
        return ResponseOutcome(fid, "NOT_DELIVERED")

    number = incident.get("number")
    owner_actions, others, readable = _actions(client, incident, owner_user, integration_user)
    context = {"number": number, "checked_at": now, "non_owner_actors": sorted(others)}
    if owner_actions:
        at, basis = min(owner_actions)
        log.append(fid, "RESPONDED", actor=owner_user, at=at, at_basis=basis, **context)
        return ResponseOutcome(fid, "RESPONDED", number, owner_user, at)
    if not readable:
        log.append(fid, "RESPONSE_UNKNOWN", reason="journal_unreadable", **context)
        return ResponseOutcome(fid, "RESPONSE_UNKNOWN", number)
    if now_at >= cutoff_at:
        log.append(fid, "NO_RESPONSE_OBSERVED", cutoff=cutoff, **context)
        return ResponseOutcome(fid, "NO_RESPONSE_OBSERVED", number)
    log.append(fid, "AWAITING_RESPONSE", cutoff=cutoff, **context)
    return ResponseOutcome(fid, "AWAITING_RESPONSE", number)

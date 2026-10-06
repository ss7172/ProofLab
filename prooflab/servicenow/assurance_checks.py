"""Deterministic assurance checks behind the Assurance Agent's analysis.

Five sections, all computed by our code (never by the model), each check pass / fail / unknown:
  movement            the agents' path across zones and gateways (from Finding.trace)
  policy_alignment    the finding against the frozen register and our human-loop policy
  outcome_validation  whether the Assurance Agent's own output can be trusted
  decision_trace      every decision in time order: gateway, control, ServiceNow, owner, agent
  classify_evidence   the finding's evidence refs, by kind, and which ones the agent used
"Unknown" means the data was not provided; it is never shown as a pass.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from prooflab.servicenow.finding import Finding
from prooflab.servicenow.finding_context import format_number

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
CLOSED_STATES = frozenset({"resolved", "closed", "canceled", "cancelled"})
_COMPARE = {"<=": lambda m, l: m <= l, "<": lambda m, l: m < l, ">=": lambda m, l: m >= l,
            ">": lambda m, l: m > l, "==": lambda m, l: m == l}
_SERVICENOW_STATES = ("INTENT", "SENT", "DELIVERED", "FAILED", "UNVERIFIED", "OUTCOME_UNKNOWN", "DRY_RUN",
                      "DUPLICATE_CORRELATION")
_OWNER_STATES = ("RESPONDED", "NO_RESPONSE_OBSERVED", "RESPONSE_UNKNOWN", "NOT_DELIVERED")


def _check(check_id: str, label: str, status: str, detail: str) -> Dict[str, str]:
    return {"id": check_id, "label": label, "status": status, "detail": detail}


def _iso_ok(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- movement
def _route_check(steps) -> Dict[str, str]:
    label = "No direct network → customer hop (every return passes a gateway)"
    if not steps:
        return _check("M1", label, UNKNOWN, "no trace provided")
    for prev, nxt in zip(steps, steps[1:]):
        if prev.zone == "network" and nxt.zone == "customer":
            return _check("M1", label, FAIL, f"{prev.actor} ({prev.at}) → {nxt.actor} ({nxt.at}) skipped the gateways")
    return _check("M1", label, PASS, "every network → customer movement crossed a gateway")


def _run_id_check(finding: Finding, steps) -> Dict[str, str]:
    label = "Every step belongs to this run"
    if not steps or all(not s.run_id for s in steps):
        return _check("M2", label, UNKNOWN, "steps carry no run id")
    if finding.scope_kind != "run":
        return _check("M2", label, UNKNOWN, f"{finding.scope_kind} scope: run ids not compared")
    foreign = [s for s in steps if s.run_id != finding.scope_id]
    if foreign:
        return _check("M2", label, FAIL, f"{len(foreign)} step(s) without run {finding.scope_id}")
    return _check("M2", label, PASS, f"all {len(steps)} steps carry run {finding.scope_id}")


def movement(finding: Finding) -> dict:
    steps = sorted(finding.trace, key=lambda s: s.at)
    path = [s.actor for i, s in enumerate(steps) if i == 0 or s.actor != steps[i - 1].actor]
    agents: List[str] = []
    for s in steps:
        if s.zone != "gateway" and s.actor not in agents:
            agents.append(s.actor)
    timestamps = [_iso_ok(s.at) for s in steps]
    time_check = (_check("M3", "Every step has a valid UTC timestamp", UNKNOWN, "no trace provided") if not steps
                  else _check("M3", "Every step has a valid UTC timestamp", PASS if all(timestamps) else FAIL,
                              f"{sum(timestamps)}/{len(steps)} valid"))
    return {"steps": [s.__dict__.copy() for s in steps], "path": path, "agents": agents,
            "zones": [s.zone for i, s in enumerate(steps) if i == 0 or s.zone != steps[i - 1].zone],
            "gateway_crossings": sum(1 for s in steps if s.zone == "gateway"),
            "checks": [_route_check(steps), _run_id_check(finding, steps), time_check]}


# ---------------------------------------------------------------- policy alignment
def _measurement_check(finding: Finding) -> Dict[str, str]:
    label = "Verdict follows from measured value vs limit"
    m, lim = finding.measured, finding.limit
    if not (m and lim):
        return _check("P1", label, UNKNOWN, "measured value or limit not provided")
    if m.unit != lim.unit:
        return _check("P1", label, UNKNOWN, f"units differ ({m.unit} vs {lim.unit})")
    within = _COMPARE[lim.operator](m.value, lim.value)
    text = f"{format_number(m.value)} {m.unit} vs limit {lim.operator} {format_number(lim.value)} → {'within' if within else 'outside'}"
    if finding.verdict == "BREACHED":
        return _check("P1", label, PASS if not within else FAIL, text)
    if finding.verdict == "SATISFIED":
        return _check("P1", label, PASS if within else FAIL, text)
    return _check("P1", label, UNKNOWN, f"{finding.verdict} is not decided by the measurement; {text}")


def _register_checks(finding: Finding, owner_user: str) -> List[Dict[str, str]]:
    reg = finding.register
    if reg is None:
        return [_check("P2", "Threshold version dated before the test", UNKNOWN, "register reference not provided"),
                _check("P3", "Named owner matches the register", UNKNOWN, "register reference not provided")]
    dated = reg.version_date[:10] <= finding.detected_at[:10]
    return [_check("P2", "Threshold version dated before the test", PASS if dated else FAIL,
                   f"{finding.threshold_version} dated {reg.version_date}; detected {finding.detected_at}"),
            _check("P3", "Named owner matches the register", PASS if reg.owner.lower() == owner_user.lower() else FAIL,
                   f"register owner {reg.owner}; incident owner {owner_user}")]


def _closed_check(finding: Finding, state: str) -> Dict[str, str]:
    """A closed incident passes only with a linked SATISFIED re-test at the same threshold version."""
    label, retest = "Not closed without a linked passing re-test", finding.retest
    if retest is None:
        return _check("P6", label, FAIL, f"incident is {state} with no linked passing re-test")
    if retest.verdict == "SATISFIED" and retest.threshold_version == finding.threshold_version:
        return _check("P6", label, PASS, f"incident {state}; closed by re-test {retest.assessment} "
                                         f"(SATISFIED, same version {retest.threshold_version})")
    return _check("P6", label, FAIL, f"incident is {state}; re-test {retest.assessment} does not count "
                                     f"({retest.verdict}, version {retest.threshold_version})")


def _loop_checks(finding: Finding, delivery_state: str, response_state: str,
                 incident_state: str) -> List[Dict[str, str]]:
    delivered = {"DELIVERED": PASS, "FAILED": FAIL, "NOT_SENT": FAIL, "DRY_RUN": FAIL}.get(delivery_state, UNKNOWN)
    responded = {"RESPONDED": PASS, "NO_RESPONSE_OBSERVED": PASS, "NOT_DELIVERED": FAIL}.get(response_state, UNKNOWN)
    response_detail = "pending until the cutoff" if response_state == "AWAITING_RESPONSE" else response_state
    state = (incident_state or "").strip()
    if not state:
        closure = _check("P6", "Not closed without a linked passing re-test", UNKNOWN, "incident state unknown")
    elif state.lower() in CLOSED_STATES and finding.verdict != "SATISFIED":
        closure = _closed_check(finding, state)
    else:
        closure = _check("P6", "Not closed without a linked passing re-test", PASS,
                         f"incident {state}; closes only after a linked passing re-test")
    return [_check("P4", "Named owner was notified (incident read back)", delivered, delivery_state or "unknown"),
            _check("P5", "Owner response or silence recorded", responded, response_detail or "unknown"),
            closure]


def policy_alignment(finding: Finding, *, delivery_state: str, response_state: str, incident_state: str,
                     owner_user: str) -> dict:
    route = _route_check(sorted(finding.trace, key=lambda s: s.at))
    checks = [_measurement_check(finding), *_register_checks(finding, owner_user),
              *_loop_checks(finding, delivery_state, response_state, incident_state),
              _check("P7", "Evidence records attached", PASS if finding.evidence else FAIL,
                     f"{len(finding.evidence)} reference(s)"),
              {**route, "id": "P8"}]
    return {"passed": sum(c["status"] == PASS for c in checks), "total": len(checks), "checks": checks}


# ---------------------------------------------------------------- outcome validation
def _refs(fields: Dict[str, str]) -> List[str]:
    return [r.strip() for r in (fields.get("Evidence refs") or "").split(";") if r.strip() and r.strip() != "none"]


def outcome_validation(finding: Finding, agent_run: dict, analysis: dict, run_record: Optional[dict]) -> dict:
    run_state = (agent_run or {}).get("state", "NOT_RUN")
    run_reason = (agent_run or {}).get("reason")
    present = (analysis or {}).get("status") == "present"
    flag = lambda value: PASS if value is True else FAIL if value is False else UNKNOWN  # noqa: E731
    used = _refs((analysis or {}).get("fields") or {})
    attempts = (run_record or {}).get("attempts") or []
    backend = (run_record or {}).get("backend") or ""
    governed = backend.startswith(("modaas-agw:", "agentcore:")) and any(a.get("action_id") for a in attempts)
    checks = [
        _check("V1", "Assurance Agent run completed", {"WRITTEN": PASS, "SKIPPED": PASS, "REFUSED": FAIL,
                                                       "BLOCKED": FAIL, "FAILED": FAIL}.get(run_state, UNKNOWN),
               f"{run_state}: {run_reason}" if run_reason else run_state),
        _check("V2", "Note is the agent's own (digest in the run log)",
               flag(analysis.get("verified")) if present else UNKNOWN, "trust anchor: delivery log"),
        _check("V3", "Facts in the note match the finding", flag(analysis.get("facts_match")) if present else UNKNOWN,
               "control, version, scope, verdict, next step"),
        _check("V4", "Evidence refs cited by the agent exist in the finding",
               (PASS if all(r in finding.evidence for r in used) else FAIL) if present else UNKNOWN,
               f"{len(used)} cited"),
        _check("V5", "Model reasoning not stored", UNKNOWN if not run_record else
               FAIL if any({"text", "reasoning", "content"} & set(a) for a in attempts) else PASS,
               "only SHA-256 of raw responses are kept"),
        _check("V6", "Governed Nemotron call with provenance", UNKNOWN if not run_record else
               PASS if governed else FAIL, backend or "no run record"),
    ]
    statuses = [c["status"] for c in checks]
    status = "failed" if FAIL in statuses else "validated" if all(s == PASS for s in statuses) else "pending"
    return {"status": status, "checks": checks}


# ---------------------------------------------------------------- decision trace and evidence
def _history_event(entry: dict) -> Optional[dict]:
    state = entry.get("state", "")
    if state in _SERVICENOW_STATES:
        return {"at": entry.get("ts"), "source": "servicenow", "actor": "ifabric.integration", "decision": state,
                "detail": entry.get("reason") or "", "ref": entry.get("number") or ""}
    if state in _OWNER_STATES:
        return {"at": entry.get("ts"), "source": "owner", "actor": entry.get("actor") or "owner", "decision": state,
                "detail": f"at {entry.get('at')}" if entry.get("at") else "", "ref": entry.get("number") or ""}
    if state.startswith("ANALYSIS_"):
        return {"at": entry.get("ts"), "source": "assurance_agent", "actor": entry.get("backend") or "assurance agent",
                "decision": state[len("ANALYSIS_"):], "detail": entry.get("reason") or "",
                "ref": ", ".join(a for a in entry.get("action_ids") or [] if a)}
    return None


def _owner_once(events: List[dict]) -> List[dict]:
    """Re-checking the same reply logs it again; the trace shows each reply once."""
    seen, kept = set(), []
    for event in events:
        if event["source"] == "owner":
            key = (event["decision"], event["actor"], event["detail"])
            if key in seen:
                continue
            seen.add(key)
        kept.append(event)
    return kept


def decision_trace(finding: Finding, history: Iterable[dict], run_record: Optional[dict]) -> List[dict]:
    # (phase, event): within the same second, events keep the pipeline order
    # agents -> control -> ServiceNow -> owner -> agent attempts -> agent outcome.
    phased = [(0, {"at": s.at, "source": "gateway" if s.zone == "gateway" else "agent", "actor": s.actor,
                   "decision": s.decision or s.action, "detail": f"{s.action} ({s.zone})", "ref": s.ref})
              for s in finding.trace]
    measured = (f"measured {format_number(finding.measured.value)} {finding.measured.unit}"
                if finding.measured else finding.summary)
    phased.append((1, {"at": finding.detected_at, "source": "control", "actor": f"{finding.control_ref} evaluator",
                       "decision": finding.verdict, "detail": measured,
                       "ref": f"{finding.control_id} v={finding.threshold_version}"}))
    history_phase = {"servicenow": 2, "owner": 3, "assurance_agent": 5}
    phased += [(history_phase[e["source"]], e) for e in (_history_event(h) for h in history) if e]
    for attempt in (run_record or {}).get("attempts") or []:
        problems = attempt.get("problems") or []
        phased.append((4, {"at": run_record.get("started_at") or "", "source": "assurance_agent",
                           "actor": run_record.get("backend") or "assurance agent",
                           "decision": f"attempt {attempt.get('attempt')}: "
                                       f"{'refused' if problems or attempt.get('error') else 'checks passed'}",
                           "detail": "; ".join(problems)[:240] or attempt.get("error")
                           or "facts echoed; refs within finding",
                           "ref": attempt.get("action_id") or ""}))
    ordered = sorted(phased, key=lambda pe: (pe[1]["at"] or "~", pe[0]))  # undated events last, never first
    return _owner_once([event for _, event in ordered])


def classify_evidence(finding: Finding, fields: Optional[Dict[str, str]]) -> List[dict]:
    used = set(_refs(fields or {}))
    return [{"ref": ref, "kind": ref.split(":", 1)[0].lower() if ":" in ref else "record",
             "used_by_agent": ref in used} for ref in finding.evidence]


def summary_lines(moved: dict, policy: dict, validation_notes: List[str]) -> Dict[str, str]:
    """Compact computed lines for the ServiceNow note (the full detail is in the case JSON)."""
    if moved["steps"]:
        agents = moved["agents"]
        path = " → ".join(agents[:8]) + (" → …" if len(agents) > 8 else "")
        route = next(c for c in moved["checks"] if c["id"] == "M1")
        path += f" ({len(agents)} agents, {moved['gateway_crossings']} gateway crossings)"
        path += "; ROUTE RULE BROKEN" if route["status"] == FAIL else ""
    else:
        path = "not provided by the evaluator"
    fails = [c["id"] for c in policy["checks"] if c["status"] == FAIL]
    unknown = [c["id"] for c in policy["checks"] if c["status"] == UNKNOWN]
    alignment = f"{policy['passed']}/{policy['total']} pass"
    alignment += f"; fail: {', '.join(fails)}" if fails else ""
    alignment += f"; unknown: {', '.join(unknown)}" if unknown else ""
    return {"Agent path": path, "Policy alignment": alignment,
            "Validation": "; ".join(validation_notes) or "not run"}

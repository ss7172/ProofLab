"""risk.py: the live risk view (ARCH 3.9). A RISK STATE, never a control verdict. Pure, stateless, stdlib, Python 3.9.

    risk_view(risk, assessments, findings, approvals, as_of) -> RiskState (a JSON-safe dict)
    risk_views(risks, assessments, findings, approvals, as_of) -> [RiskState] in risk_id order

States (prooflab.contract.verdicts.RISK_STATES): WITHIN_APPETITE (no open linked finding), EXPOSED (an open linked
finding: residual = inherent; `accepted_until` when an unexpired acceptance is on record), UNTESTED (no assessment
of a mitigating control as of the time). Everything is recomputed from the inputs as of `as_of`; nothing is stored.

Closure rule (ARCH 3.9 loop): a finding closes only by a LATER SATISFIED assessment (not after as_of) of the same
control and scope kind. An acceptance (approval kind risk-acceptance, a named approver, a finding id, a risk id and
a future expiry) changes how the risk is shown, never the finding and never the state.
"""
from __future__ import annotations

from prooflab.contract import clocks as _clocks
from prooflab.contract import verdicts as _v

NAME = "prooflab.evaluators.risk"
ACCEPTANCE_KIND = "risk-acceptance"
OPEN_FINDING_VERDICTS = (_v.BREACHED, _v.INDETERMINATE, _v.ESCALATED)
WITHIN_APPETITE, EXPOSED, UNTESTED = _v.RISK_STATES


def _g(o, k, d=None):
    if isinstance(o, dict):
        return o.get(k, d)
    return getattr(o, k, d)


def _t(value):
    try:
        return _clocks.parse_utc(value)
    except (ValueError, TypeError):
        return None


def _csv(text):
    return [p.strip() for p in str(text or "").split(",") if p.strip()]


def _a_time(a):
    return _t(_g(a, "as_of"))


def _f_time(f):
    return _t(_g(f, "detected_at")) or _t(_g(f, "as_of"))


def _f_id(f):
    return _g(f, "finding_id") or ""


def _closing(finding, controls_assessments, at):
    """The earliest SATISFIED assessment after the finding, not after `at`, same control and scope kind; or None."""
    ft = _f_time(finding)
    best = None
    for a in controls_assessments:
        if _g(a, "control_ref") != _g(finding, "control_ref") or _g(a, "scope_kind") != _g(finding, "scope_kind"):
            continue
        if _g(a, "requirement_verdict") != _v.SATISFIED:
            continue
        t = _a_time(a)
        if t is None or t > at or (ft is not None and t <= ft):
            continue
        key = (t, _g(a, "assessment_id") or "")
        if best is None or key < best[0]:
            best = (key, a)
    return best[1] if best else None


def _acceptance(risk_id, finding, approvals, at):
    """The unexpired acceptance for this finding on this risk with the latest expiry, or None."""
    best = None
    for ap in approvals or ():
        if _g(ap, "kind") != ACCEPTANCE_KIND and _g(ap, "approval_kind") != ACCEPTANCE_KIND:
            continue
        if _g(ap, "risk_id") != risk_id or _g(ap, "finding_id") != _f_id(finding):
            continue
        if not str(_g(ap, "approver") or "").strip():
            continue
        exp, given = _t(_g(ap, "expiry")), _t(_g(ap, "approved_at") or _g(ap, "as_of"))
        if exp is None or exp <= at or (given is not None and given > at):
            continue
        if best is None or exp > best[0]:
            best = (exp, ap)
    return best[1] if best else None


def risk_view(risk, assessments, findings, approvals, as_of):
    """The state of one risk as of `as_of` (a UTC string). `risk` is one entry of the parsed risks.yaml."""
    at = _t(as_of)
    if at is None:
        raise ValueError("as_of must be a UTC timestamp: %r" % (as_of,))
    rid = _g(risk, "risk_id")
    controls = _csv(_g(risk, "controls"))
    mine = [a for a in (assessments or ()) if _g(a, "control_ref") in controls
            and _a_time(a) is not None and _a_time(a) <= at]
    tested = [a for a in mine if _g(a, "requirement_verdict") != _v.NOT_ASSESSED]
    linked, open_rows, closed_rows = [], [], []
    for f in sorted(findings or (), key=lambda x: (_f_id(x), str(_g(x, "detected_at")))):
        if _g(f, "control_ref") not in controls or _g(f, "verdict") not in OPEN_FINDING_VERDICTS:
            continue
        ft = _f_time(f)
        if ft is None or ft > at:
            continue
        linked.append(f)
        closer = _closing(f, mine, at)
        row = {"finding_id": _f_id(f), "control_ref": _g(f, "control_ref"), "verdict": _g(f, "verdict"),
               "detected_at": _g(f, "detected_at")}
        if closer is not None:
            closed_rows.append(dict(row, state="closed", retest_assessment_id=_g(closer, "assessment_id"),
                                    retest_as_of=_g(closer, "as_of")))
            continue
        acc = _acceptance(rid, f, approvals, at)
        row["state"] = "open"
        if acc is not None:
            row["accepted_until"] = _g(acc, "expiry")
            row["accepted_by"] = _g(acc, "approver")
        open_rows.append(row)
    if open_rows:
        state = EXPOSED
    elif tested:
        state = WITHIN_APPETITE
    else:
        state = UNTESTED
    accepted = sorted(r["accepted_until"] for r in open_rows if r.get("accepted_until"))
    all_accepted = bool(open_rows) and len(accepted) == len(open_rows)
    residual = _g(risk, "inherent_rating") if state == EXPOSED else _g(risk, "residual_rating")
    return {
        "risk_id": rid, "state": state, "as_of": as_of, "statement": _g(risk, "statement"),
        "owner": _g(risk, "owner_name") or _g(risk, "owner"), "controls": controls,
        "inherent_rating": _g(risk, "inherent_rating"), "appetite_rating": _g(risk, "appetite_rating"),
        "residual_rating_shown": residual, "residual_rating_target": _g(risk, "residual_rating"),
        "status_at_freeze": _g(risk, "status"),
        "open_findings": open_rows, "closed_findings": closed_rows,
        "accepted_until": accepted[0] if all_accepted else None,
        "assessments_considered": len(tested),
        "reason": _reason(state, open_rows, tested),
    }


def _reason(state, open_rows, tested):
    if state == EXPOSED:
        return "%d open linked finding(s): residual = inherent" % len(open_rows)
    if state == WITHIN_APPETITE:
        return "no open linked finding; %d assessment(s) of a mitigating control" % len(tested)
    return "no assessment of a mitigating control as of the time"


def risk_views(risks, assessments, findings, approvals, as_of):
    return [risk_view(r, assessments, findings, approvals, as_of)
            for r in sorted(risks or (), key=lambda x: str(_g(x, "risk_id")))]

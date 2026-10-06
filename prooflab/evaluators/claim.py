"""claim.py: the claim rollup (C-FM-01) and the helpers the control testers share (ARCH 3.4, 1.2, 4.3).

Pure and stateless: no I/O, no clock, no module state; `as_of` is always passed in. Stdlib, Python 3.9.

  rollup(assessments_by_control, complete_by_control) -> ClaimLine
      "partial coverage" unless all three claim controls (C16, C7, C9) are complete AND SATISFIED. INV and the
      others carry in_claim false and never count (a missing INV never turns the line into partial coverage).
  make_assessment(...)   builds the contract's Assessment (+ the Finding dict, ARCH 4.3 mapping)
  parse_limits(text)     "k=v;k=v" -> {k: v} for a register entry's observation_limit string
  pct_over(part, whole, pct)      exact: part/whole*100 > pct (Fractions, no floats)
  window_scope(...)      the shared window rule (E-06, A1) used by c16, c7 and c9 assess_window
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction

from prooflab.contract import clocks as _clocks
from prooflab.contract import finding as _finding
from prooflab.contract import transports as _tr
from prooflab.contract import verdicts as _v

CLAIM_CONTROLS = ("C16", "C7", "C9")
CLAIM_ID = "C-FM-01"
WINDOW_PROVENANCE = ("LIVE_SUBJECT", "FAULT_INJECTION", "AUTHORIZED_TEST")
DESIGN = ("DESIGNED", "NOT_DESIGNED")
OPERATION = ("OPERATED", "DEGRADED", "NOT_PRESENT")
SUFFICIENCY = ("COMPLETE", "PARTIAL", "MISSING")


@dataclass(frozen=True)
class ClaimLine:
    claim_id: str
    state: str                # "claim satisfied" | "partial coverage"
    complete_and_satisfied: int
    of: int
    per_control: tuple        # ((ref, verdict, complete, counted), ...) in CLAIM_CONTROLS order
    line: str


def verdict_of(x):
    """A verdict string from an Assessment, a dict or a plain string."""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get("requirement_verdict") or x.get("verdict")
    return getattr(x, "requirement_verdict", None)


def rollup(assessments_by_control, complete_by_control, claim_id=CLAIM_ID):
    rows = []
    for ref in CLAIM_CONTROLS:
        a = assessments_by_control.get(ref)
        v = verdict_of(a) if a is not None else None
        v = v if v in _v.ASSESSMENT_VERDICTS else "NOT_ASSESSED"
        complete = bool(complete_by_control.get(ref, False))
        rows.append((ref, v, complete, complete and v == "SATISFIED"))
    n = sum(1 for r in rows if r[3])
    total = len(CLAIM_CONTROLS)
    state = "claim satisfied" if n == total else "partial coverage"
    detail = ", ".join("%s %s%s" % (r[0], r[1], "" if r[2] else " (incomplete)") for r in rows)
    line = "%s: %s (%d of %d controls complete and satisfied; %s)" % (claim_id, state, n, total, detail)
    return ClaimLine(claim_id, state, n, total, tuple(rows), line)


def parse_limits(text):
    """'a=1;b=2.5' -> {'a': '1', 'b': '2.5'} (values stay strings; callers convert). Bad parts are skipped."""
    out = {}
    for part in (text or "").replace(",", ";").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k.strip():
                out[k.strip()] = v.strip()
    return out


def frac(x):
    """Exact Fraction from an int, float or numeric string; None if not a number."""
    try:
        if isinstance(x, bool) or x is None:
            return None
        return Fraction(str(x).strip())
    except (ValueError, ZeroDivisionError):
        return None


def pct_over(part, whole, pct):
    """True iff part/whole*100 > pct. whole must be > 0 (callers handle the empty denominator)."""
    return Fraction(part) * 100 > Fraction(pct) * Fraction(whole)


def pct_under(part, whole, pct):
    """True iff part/whole*100 < pct."""
    return Fraction(part) * 100 < Fraction(pct) * Fraction(whole)


def deficiency_of(design, operation):
    d = design != "DESIGNED"
    o = operation != "OPERATED"
    return "both" if d and o else "design" if d else "operation" if o else "none"


def make_assessment(control_ref, control_id, threshold_version, threshold_sha256, register_version,
                    scope_kind, scope_id, scope_start, scope_end, verdict, design, operation, sufficiency,
                    measured, exceptions, denominators, completeness, formula, evidence_refs, gaps,
                    evaluator_name, evaluator_sha256, as_of, snapshot_id="", revision=1, summary=None):
    """The contract Assessment (transports.Assessment) with its Finding dict (None for NOT_ASSESSED)."""
    deficiency = deficiency_of(design, operation)
    aid = _tr.assessment_id(control_ref, threshold_version, scope_kind, scope_id, revision)
    base = dict(
        assessment_id=aid, control_ref=control_ref, control_id=control_id, threshold_version=threshold_version,
        threshold_sha256=threshold_sha256, register_version=register_version, scope_kind=scope_kind,
        scope_id=scope_id, scope_start=scope_start or "", scope_end=scope_end or "", requirement_verdict=verdict,
        design=design, operation=operation, deficiency=deficiency, evidence_sufficiency=sufficiency,
        measured=measured, exceptions=list(exceptions), denominators=denominators, completeness=completeness,
        formula=formula, evidence_refs=list(evidence_refs), gaps=list(gaps), evaluator_name=evaluator_name,
        evaluator_sha256=evaluator_sha256 or "", as_of=as_of, snapshot_id=snapshot_id)
    finding = None
    if verdict in _v.ASSESSMENT_VERDICTS and _v.finding_verdict(verdict) is not None and _clocks.is_utc(as_of):
        text = "deficiency: %s; %s %s %s: %s" % (
            deficiency, control_ref, scope_kind, scope_id, summary or ("; ".join(gaps) or verdict))
        try:
            finding = _finding.finding_from_assessment(base, text, as_of, evidence=list(evidence_refs))
        except ValueError:
            finding = None
    return _tr.Assessment(finding=finding, **base)


def as_dict(assessment):
    return asdict(assessment)


def window_scope(t1, t2, run_assessments, pins_by_version, condition=None):
    """The shared window rule (E-06, A1). Returns (counted, listed) where
    counted = [(assessment, tolerance)] and listed = [{run, reason}].

    In scope: the run's first span in [t1, t2) with provenance LIVE_SUBJECT / FAULT_INJECTION / AUTHORIZED_TEST,
    tested under its own bound version (assessment.threshold_version). A run whose version has no pins entry
    is listed, not counted; other provenance is 'not assessed by provenance'; a --condition filter lists the
    excluded runs. Reads `measured['first_span_at']`, `['provenance']`, `['condition']` of each run assessment.
    Tolerance = pins_by_version[version]['exception_tolerance'] (an integer count; missing -> not counted)."""
    counted, listed = [], []
    for a in sorted(run_assessments, key=lambda x: x.assessment_id):
        m = a.measured or {}
        rid = a.scope_id
        first = m.get("first_span_at") or a.scope_start
        prov = m.get("provenance")
        if prov not in WINDOW_PROVENANCE:
            listed.append({"run": rid, "reason": "not assessed by provenance (%s)" % prov})
            continue
        try:
            inside = _clocks.parse_utc(t1) <= _clocks.parse_utc(first) < _clocks.parse_utc(t2)
        except (ValueError, TypeError):
            listed.append({"run": rid, "reason": "no usable first-span time"})
            continue
        if not inside:
            listed.append({"run": rid, "reason": "outside the window"})
            continue
        if condition is not None and m.get("condition") != condition:
            listed.append({"run": rid, "reason": "excluded by the condition filter (%s)" % m.get("condition")})
            continue
        pin = (pins_by_version or {}).get(a.threshold_version)
        tol = frac((pin or {}).get("exception_tolerance"))
        if pin is None or tol is None:
            listed.append({"run": rid, "reason": "no entry for %s in the bound version" % a.threshold_version})
            continue
        if a.requirement_verdict == "NOT_ASSESSED":
            listed.append({"run": rid, "reason": "run NOT_ASSESSED"})
            continue
        counted.append((a, tol))
    return counted, listed


def window_verdict(counted):
    """BREACHED if, for any version, its breached runs exceed that version's tolerance; else INDETERMINATE if
    any counted run is INDETERMINATE; else SATISFIED; nothing counted: NOT_ASSESSED."""
    if not counted:
        return "NOT_ASSESSED", {}
    by_version = {}
    for a, tol in counted:
        by_version.setdefault(a.threshold_version, [tol, 0, 0])
        if a.requirement_verdict == "BREACHED":
            by_version[a.threshold_version][1] += 1
        if a.requirement_verdict == "INDETERMINATE":
            by_version[a.threshold_version][2] += 1
    summary = dict((k, {"tolerance": str(v[0]), "breached_runs": v[1], "indeterminate_runs": v[2]})
                   for k, v in sorted(by_version.items()))
    if any(v[1] > v[0] for v in by_version.values()):
        return "BREACHED", summary
    if any(v[2] for v in by_version.values()):
        return "INDETERMINATE", summary
    return "SATISFIED", summary

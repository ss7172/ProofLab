import copy
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from prooflab.contract import verdicts as V  # noqa: E402
from prooflab.evaluators import risk as R  # noqa: E402
from prooflab.registry import parse  # noqa: E402

RISKS = parse.entries_by_id(parse.parse_file(os.path.join(ROOT, "register", "risks.yaml"), "risks"))


def A(control, verdict, at, scope="run", aid=None):
    return {"assessment_id": aid or "%s-%s-%s" % (control, verdict, at), "control_ref": control, "scope_kind": scope,
            "requirement_verdict": verdict, "as_of": at}


def F(control, verdict, at, scope="run", fid=None):
    return {"finding_id": fid or "f-%s-%s" % (control, at), "control_ref": control, "scope_kind": scope,
            "verdict": verdict, "detected_at": at}


T0, T1, T2, T3 = "2026-10-06T04:00:00Z", "2026-10-06T05:00:00Z", "2026-10-06T06:00:00Z", "2026-10-06T07:00:00Z"
NOW = "2026-10-06T08:00:00Z"


def test_register_parses_and_every_risk_has_a_state():
    out = R.risk_views(list(RISKS.values()), [], [], [], NOW)
    assert len(out) == len(RISKS) and all(o["state"] == R.UNTESTED for o in out)
    assert all(o["state"] in V.RISK_STATES for o in out)


def test_untested_then_within_appetite():
    assert R.risk_view(RISKS["R-C16"], [], [], [], NOW)["state"] == "UNTESTED"
    s = R.risk_view(RISKS["R-C16"], [A("C16", V.SATISFIED, T1)], [], [], NOW)
    assert s["state"] == "WITHIN_APPETITE" and s["residual_rating_shown"] == RISKS["R-C16"]["residual_rating"]


def test_not_assessed_does_not_test():
    assert R.risk_view(RISKS["R-C16"], [A("C16", V.NOT_ASSESSED, T1)], [], [], NOW)["state"] == "UNTESTED"


def test_open_finding_exposes_with_inherent():
    s = R.risk_view(RISKS["R-C16"], [A("C16", V.BREACHED, T1)], [F("C16", V.BREACHED, T1)], [], NOW)
    assert s["state"] == "EXPOSED" and s["residual_rating_shown"] == RISKS["R-C16"]["inherent_rating"]
    assert len(s["open_findings"]) == 1


def test_retest_closes_same_control_and_scope_kind_only():
    base = [A("C16", V.BREACHED, T1)]
    fs = [F("C16", V.BREACHED, T1)]
    closed = R.risk_view(RISKS["R-C16"], base + [A("C16", V.SATISFIED, T2)], fs, [], NOW)
    assert closed["state"] == "WITHIN_APPETITE" and closed["closed_findings"][0]["retest_as_of"] == T2
    other_scope = R.risk_view(RISKS["R-C16"], base + [A("C16", V.SATISFIED, T2, scope="window")], fs, [], NOW)
    assert other_scope["state"] == "EXPOSED"
    other_ctl = R.risk_view(RISKS["R-C16"], base + [A("C7", V.SATISFIED, T2)], fs, [], NOW)
    assert other_ctl["state"] == "EXPOSED"
    earlier = R.risk_view(RISKS["R-C16"], [A("C16", V.SATISFIED, T0)] + base, fs, [], NOW)
    assert earlier["state"] == "EXPOSED"


def test_as_of_time_travel():
    assess = [A("C16", V.BREACHED, T1), A("C16", V.SATISFIED, T3)]
    fs = [F("C16", V.BREACHED, T1)]
    assert R.risk_view(RISKS["R-C16"], assess, fs, [], T0)["state"] == "UNTESTED"
    assert R.risk_view(RISKS["R-C16"], assess, fs, [], T2)["state"] == "EXPOSED"
    assert R.risk_view(RISKS["R-C16"], assess, fs, [], NOW)["state"] == "WITHIN_APPETITE"


def test_satisfied_finding_is_not_open():
    s = R.risk_view(RISKS["R-C16"], [A("C16", V.SATISFIED, T1)], [F("C16", V.SATISFIED, T1)], [], NOW)
    assert s["state"] == "WITHIN_APPETITE"


def test_unlinked_control_finding_ignored():
    s = R.risk_view(RISKS["R-C16"], [A("C16", V.SATISFIED, T1)], [F("C7", V.BREACHED, T1)], [], NOW)
    assert s["state"] == "WITHIN_APPETITE"


def acc(**kw):
    d = {"kind": "risk-acceptance", "risk_id": "R-C16", "finding_id": "f-C16-" + T1, "approver": "A Name",
         "expiry": T3, "approved_at": T2}
    d.update(kw)
    return d


def test_acceptance_shown_never_closes_and_expires():
    a, f = [A("C16", V.BREACHED, T1)], [F("C16", V.BREACHED, T1)]
    s = R.risk_view(RISKS["R-C16"], a, f, [acc()], "2026-10-06T06:30:00Z")
    assert s["state"] == "EXPOSED" and s["accepted_until"] == T3 and s["open_findings"][0]["state"] == "open"
    after = R.risk_view(RISKS["R-C16"], a, f, [acc()], NOW)
    assert after["state"] == "EXPOSED" and after["accepted_until"] is None


def test_invalid_acceptances_ignored():
    a, f = [A("C16", V.BREACHED, T1)], [F("C16", V.BREACHED, T1)]
    at = "2026-10-06T06:30:00Z"
    for bad in (acc(approver=""), acc(risk_id="R-C7"), acc(finding_id="other"), acc(expiry="soon"),
                acc(kind="approval"), acc(approved_at=T3)):
        assert R.risk_view(RISKS["R-C16"], a, f, [bad], at)["accepted_until"] is None


def test_never_a_control_verdict():
    s = R.risk_view(RISKS["R-C16"], [A("C16", V.BREACHED, T1)], [F("C16", V.BREACHED, T1)], [], NOW)
    assert s["state"] not in V.ASSESSMENT_VERDICTS and "verdict" not in s


def test_stateless_inputs_unmutated_order_independent_json_safe():
    assess = [A("C16", V.BREACHED, T1), A("C16", V.SATISFIED, T2), A("C7", V.BREACHED, T1)]
    fs = [F("C16", V.BREACHED, T1), F("C7", V.BREACHED, T1)]
    snap = copy.deepcopy((assess, fs))
    want = json.dumps(R.risk_views(list(RISKS.values()), assess, fs, [], NOW), sort_keys=True)
    for _ in range(5):
        a2, f2, r2 = list(assess), list(fs), list(RISKS.values())
        random.shuffle(a2), random.shuffle(f2), random.shuffle(r2)
        assert json.dumps(R.risk_views(r2, a2, f2, [], NOW), sort_keys=True) == want
    assert (assess, fs) == snap


def test_bad_as_of_raises():
    import pytest
    with pytest.raises(ValueError):
        R.risk_view(RISKS["R-C16"], [], [], [], "yesterday")


def test_module_has_no_clock_or_io():
    src = open(R.__file__.replace(".pyc", ".py")).read()
    for banned in ("time.time", "datetime.now", "utcnow", "open(", "os.environ"):
        assert banned not in src

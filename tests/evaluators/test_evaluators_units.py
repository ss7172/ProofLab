import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conftest  # noqa: E402,F401  (sets up sibling paths)

from prooflab.contract import verdicts as V  # noqa: E402
from prooflab.evaluators import approval, c16, c16_core, c7, c9, claim  # noqa: E402

AS_OF = "2026-10-06T06:00:00.000Z"


def _pin(mode="enforce"):
    return c16_core.PinnedC16.from_dict(
        {"schema": "ifabric.pin/1", "register": {"version": "v1", "sha256": "a" * 64},
         "c16": {"control_id": "ACN-COST-001", "threshold_version": "C16-v1", "tiers": ["high", "standard"],
                 "default_tier": "standard", "caps": {"high": 20000, "standard": 40000}, "safety_ceiling": 300000,
                 "modes": ["enforce", "observe"], "mode": mode,
                 "bound": {"inline_bound_margin_pct": 10, "inline_bound_fallback_tokens": 8000, "max_tokens": 800}}}, "f" * 64)


# --- approval ---------------------------------------------------------------------------------------------
RUNNING = {"ifabric-it": {"image_digest": "sha256:aa", "model": "super-120b", "generation": 3, "approved_generation": 3},
           "ifabric-net": {"image_digest": "sha256:bb", "model": "super-120b", "generation": 1, "approved_generation": 1}}
APPROVED = {"ifabric-it": {"sha256:aa|super-120b"}, "ifabric-net": {("sha256:bb", "super-120b")}}


def test_approval_all_approved_proceeds():
    ds = approval.check_versions(RUNNING, APPROVED, "block-assessed", True)
    assert [d.verdict for d in ds] == ["ALLOW", "ALLOW"]
    assert [d.action for d in ds] == ["proceed", "proceed"]
    assert all(d.control_ref == "APPROVAL" and d.mode == "block-assessed" and d.limit_applied == "approved-versions" for d in ds)


def test_approval_paused_assessed_declines():
    r = copy.deepcopy(RUNNING)
    r["ifabric-net"]["paused"] = True
    ds = approval.check_versions(r, APPROVED, "block-assessed", True)
    assert [(d.verdict, d.action) for d in ds] == [("ALLOW", "proceed"), ("DENY", "decline-start")]
    assert "paused" in ds[1].reason


def test_approval_stale_generation_denies():
    r = copy.deepcopy(RUNNING)
    r["ifabric-it"]["generation"] = 4
    ds = approval.check_versions(r, APPROVED, "block-assessed", True)
    assert ds[0].verdict == "DENY" and ds[0].action == "decline-start" and "stale approval" in ds[0].reason


def test_approval_unapproved_digest_denies_but_not_assessed_proceeds():
    r = copy.deepcopy(RUNNING)
    r["ifabric-it"]["image_digest"] = "sha256:zz"
    ds = approval.check_versions(r, APPROVED, "block-assessed", False)
    assert ds[0].verdict == "DENY" and ds[0].action == "proceed"


def test_approval_record_only_never_declines():
    r = copy.deepcopy(RUNNING)
    r["ifabric-it"]["paused"] = True
    ds = approval.check_versions(r, APPROVED, "record-only", True)
    assert ds[0].verdict == "DENY" and ds[0].action == "proceed" and ds[0].mode == "record-only"


def test_approval_no_approved_set_and_bad_policy_fail_closed():
    ds = approval.check_versions(RUNNING, {}, "nonsense", True)
    assert all(d.verdict == "DENY" and d.action == "decline-start" for d in ds)


def test_approval_sorted_and_meta_stamped():
    ds = approval.check_versions(dict(reversed(list(RUNNING.items()))), APPROVED, "record-only", True,
                                 meta={"threshold_version": "APPROVAL-v1", "register_version": "v1"})
    assert [d.reason.split(":")[0] for d in ds] == ["ifabric-it", "ifabric-net"]
    assert ds[0].threshold_version == "APPROVAL-v1"


# --- claim ------------------------------------------------------------------------------------------------
def test_claim_partial_unless_three_of_three():
    allc = {"C16": "SATISFIED", "C7": "SATISFIED", "C9": "SATISFIED"}
    full = claim.rollup(allc, {"C16": True, "C7": True, "C9": True})
    assert full.state == "claim satisfied" and full.complete_and_satisfied == 3
    part = claim.rollup(allc, {"C16": True, "C7": True, "C9": False})
    assert part.state == "partial coverage" and "C9 SATISFIED (incomplete)" in part.line
    breached = claim.rollup(dict(allc, C7="BREACHED"), {"C16": True, "C7": True, "C9": True})
    assert breached.state == "partial coverage" and breached.complete_and_satisfied == 2
    assert claim.rollup({}, {}).complete_and_satisfied == 0


def test_claim_ignores_inv():
    r = claim.rollup({"C16": "SATISFIED", "C7": "SATISFIED", "C9": "SATISFIED", "INV": "BREACHED"},
                     {"C16": True, "C7": True, "C9": True, "INV": False})
    assert r.state == "claim satisfied"


def test_verdict_map_consistent_for_every_assessment_verdict():
    for v in V.ASSESSMENT_VERDICTS:
        assert V.exit_code(v) == V.VERDICT_MAP[v][5]


# --- c16 pieces -------------------------------------------------------------------------------------------
def test_tier_rule_parse_and_derive():
    p = _pin()
    rule = "impact=high&data=pii->high;impact=high->standard;*->standard"
    assert c16.derive_tier({"impact": "high", "data": "pii"}, rule, p) == ("high", "tier_rule")
    assert c16.derive_tier({"impact": "high"}, rule, p)[0] == "standard"
    assert c16.derive_tier({}, "", p) == ("standard", "pin-default")


def test_unknown_tier_uses_strictest_cap():
    a = c16.assess_run("r", [{"action_id": "a", "listener": "llm", "tokens_in": 25000, "tokens_out": 1,
                              "http_status": 200}], {"tier_rule": {"rules": [], "default": "weird"}}, [], _pin(),
                       {}, AS_OF)
    assert a.measured["tier"] == "high" and a.requirement_verdict == "BREACHED"
    assert any(e["kind"] == "unknown-tier" for e in a.exceptions)


def test_comparison_uses_core_compare(monkeypatch):
    seen = []
    real = c16.compare
    monkeypatch.setattr(c16, "compare", lambda t, l: (seen.append((t, l)), real(t, l))[1])
    c16.assess_run("r", [{"action_id": "a", "listener": "llm", "tokens_in": 1, "tokens_out": 1, "http_status": 200}],
                   {}, [], _pin(), {}, AS_OF)
    assert seen == [(2, 40000)]


def _run_assessment(rid, verdict, first, prov="LIVE_SUBJECT", version="C16-v1", cond="none"):
    return claim.make_assessment(
        "C16", "ACN-COST-001", version, "s" * 64, "v1", "run", rid, first, first, verdict, "DESIGNED", "OPERATED",
        "COMPLETE", {"first_span_at": first, "provenance": prov, "condition": cond, "overshoot": 5}, [], {}, {}, "f",
        [], [], "t", "", AS_OF)


def test_c16_window_rule():
    runs = [_run_assessment("r1", "SATISFIED", "2026-10-06T05:10:00.000Z"),
            _run_assessment("r2", "BREACHED", "2026-10-06T05:20:00.000Z"),
            _run_assessment("r3", "BREACHED", "2026-10-06T05:30:00.000Z", prov="PILOT"),
            _run_assessment("r4", "SATISFIED", "2026-10-06T09:00:00.000Z"),
            _run_assessment("r5", "SATISFIED", "2026-10-06T05:40:00.000Z", version="C16-v9")]
    pins = {"C16-v1": {"exception_tolerance": 0}}
    w = c16.assess_window("2026-10-06T05:00:00.000Z", "2026-10-06T06:00:00.000Z", runs, pins, AS_OF)
    assert w.requirement_verdict == "BREACHED"
    reasons = dict((x["run"], x["reason"]) for x in w.completeness["listed_not_counted"])
    assert set(reasons) == {"r3", "r4", "r5"} and "provenance" in reasons["r3"]
    tolerant = c16.assess_window("2026-10-06T05:00:00.000Z", "2026-10-06T06:00:00.000Z", runs,
                                 {"C16-v1": {"exception_tolerance": 1}}, AS_OF)
    assert tolerant.requirement_verdict == "SATISFIED"
    empty = c16.assess_window("2026-10-07T05:00:00.000Z", "2026-10-07T06:00:00.000Z", runs, pins, AS_OF)
    assert empty.requirement_verdict == "NOT_ASSESSED"
    only_cond = c16.assess_window("2026-10-06T05:00:00.000Z", "2026-10-06T06:00:00.000Z", runs, pins, AS_OF, condition="x")
    assert only_cond.requirement_verdict == "NOT_ASSESSED"


def test_c7_window_pooled():
    def a(rid, verdict, cov, exp, hit, gaps, vio):
        return claim.make_assessment("C7", "AIA-LOG-001", "C7-v1", "s", "v1", "run", rid, "2026-10-06T05:10:00.000Z", "",
                                     verdict, "DESIGNED", "OPERATED", "COMPLETE",
                                     {"first_span_at": "2026-10-06T05:10:00.000Z", "provenance": "LIVE_SUBJECT",
                                      "coverage": cov, "violating_gaps": vio}, [],
                                     {"expected": exp, "observed_and_expected": hit, "gaps_measured": gaps}, {}, "f", [], [],
                                     "t", "", AS_OF)
    w = c7.assess_window("2026-10-06T05:00:00.000Z", "2026-10-06T06:00:00.000Z",
                         [a("r1", "SATISFIED", "5/5", 5, 5, 4, 0), a("r2", "BREACHED", "4/5", 5, 4, 3, 1)],
                         {"C7-v1": {"exception_tolerance": 0}}, AS_OF)
    assert w.requirement_verdict == "BREACHED"
    assert w.measured["pooled_coverage"] == "9/10" and w.measured["pooled_violating_gaps"] == "1/7"


def test_c9_hourly_rollup_and_no_traffic_hour():
    pin = {"baseline_value_rt": 100, "max_relative_change_pct": 10, "violating_windows_max_pct": 0}
    pins = {"C9-v1.1": pin}
    hw = lambda h, lat, exp=1, dp=1: {"hour": h, "runtime": "rt", "threshold_version": "C9-v1.1", "latency_max": lat,
                                      "errors": 0, "invocations_expected": exp, "datapoints": dp}
    t1, t2 = "2026-10-06T04:00:00.000Z", "2026-10-06T08:00:00.000Z"
    ok = c9.assess_window(t1, t2, [], [hw("2026-10-06T04:00:00.000Z", 100), hw("2026-10-06T05:00:00.000Z", None, exp=0, dp=0)], pins, AS_OF)
    assert ok.requirement_verdict == "SATISFIED" and ok.gaps == []
    idle = c9.assess_window(t1, t2, [], [hw("2026-10-06T05:00:00.000Z", None, exp=0, dp=0)], pins, AS_OF)
    assert idle.requirement_verdict == "NOT_ASSESSED"
    bad = c9.assess_window(t1, t2, [], [hw("2026-10-06T04:00:00.000Z", 100), hw("2026-10-06T06:00:00.000Z", 150)], pins, AS_OF)
    assert bad.requirement_verdict == "BREACHED" and bad.measured["violating_hours"] == 1
    gap = c9.assess_window(t1, t2, [], [hw("2026-10-06T04:00:00.000Z", None, dp=0)], pins, AS_OF)
    assert gap.requirement_verdict == "INDETERMINATE" and gap.gaps
    outside = c9.assess_window(t1, t2, [], [hw("2026-10-06T09:00:00.000Z", 999)], pins, AS_OF)
    assert outside.requirement_verdict == "NOT_ASSESSED"


def test_assessment_id_and_threshold_stamps():
    a = c16.assess_run("r", [{"action_id": "a", "listener": "llm", "tokens_in": 1, "tokens_out": 1, "http_status": 200}],
                       {}, [], _pin(), {}, AS_OF, evaluator_sha256="9" * 64)
    assert a.assessment_id == "C16:C16-v1:run:r:r1"
    assert (a.threshold_version, a.register_version, a.threshold_sha256) == ("C16-v1", "v1", "a" * 64)
    assert a.evaluator_sha256 == "9" * 64 and a.evaluator_name == "prooflab.evaluators.c16"

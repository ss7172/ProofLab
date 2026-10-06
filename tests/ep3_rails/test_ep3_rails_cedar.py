"""PR-31: which layer refuses in ADV-R-01 (DG-1 rails vs the DG-4 Cedar forbid), declared and proven offline.

Leg 1 (network agent, undeclared customer_lookup): our rails refuse in enforce (X-02 BLOCK).
Leg 2 (customer agent, declared customer_lookup, site SITE-ADV-*): our rails ALLOW and leave the argument unchanged,
so the platform PDP (policies/cedar/customer-records.forbid-site-adv.cedar) is the layer that refuses.
Python 3.9, stdlib only.
"""
import os
import re

from adapters.runtime import rails as R

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOOKUP = "customer-records___customer_lookup"


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _cedar_forbid_prefix():
    text = _read("policies", "cedar", "customer-records.forbid-site-adv.cedar")
    (pat,) = re.findall(r'context\.arguments\.site like "([^"]+)"', text)
    assert pat.endswith("*") and "*" not in pat[:-1]
    return pat[:-1]


def test_leg2_rails_leave_the_cedar_forbidden_site_alone_in_enforce():
    prefix = _cedar_forbid_prefix()   # "SITE-ADV-"
    for site in (prefix + "99", prefix + "00", prefix + "12"):
        r = R.Rails("ifabric-customer", mode="enforce")
        args = {"site": site}
        refusal, out = r.before_tool(LOOKUP, args)
        assert refusal is None and out == {"site": site}          # not blocked, not rewritten
        assert [d for d in r.records if d["verdict"] in ("BLOCK", "MODIFY")] == []
        assert r.counts["X-02"]["ALLOW"] == 1 and r.counts["X-03"]["ALLOW"] == 1


def test_leg2_the_api_surface_agrees():
    o = R.check_tool_call(LOOKUP, {"site": "SITE-ADV-99"}, policy="ifabric-customer")
    assert o["verdict"] == "ALLOW" and o["output"] == {"site": "SITE-ADV-99"}


def test_x03_still_rewrites_element_ids_but_never_into_a_pass_of_the_rule():
    # X-03 only rewrites element ids (never a SITE-* value), so it cannot launder a forbidden value away.
    r = R.Rails("ifabric-customer", mode="enforce")
    _, out = r.before_tool(LOOKUP, {"site": "ENB-ADV-99"})
    assert out == {"site": "SITE-ADV-99"}   # an element id of the test site still reaches the PDP as the test site


def test_leg1_our_rails_refuse_the_undeclared_tool_in_enforce():
    r = R.Rails("ifabric-network", mode="enforce")
    refusal, _ = r.before_tool(LOOKUP, {"site": "SITE-ADV-99"})
    assert refusal and refusal.startswith("denied by rail X-02")
    (d,) = [x for x in r.records if x["rail.id"] == "X-02"]
    assert d["verdict"] == "BLOCK" and d["inline.action"] == "block" and d["outcome.real"] == "CANCELLED_RAIL"


def test_case_file_declares_the_refusing_layer_per_leg():
    t = _read("evidence", "adversarial", "cases", "ADV-R-01.md")
    assert re.search(r"Pre-registered:\*\* 2026-10-06", t)
    assert "## Which layer is expected to refuse" in t
    rows = [ln for ln in t.splitlines() if ln.startswith("| 1 |") or ln.startswith("| 2 |")]
    assert len(rows) == 2
    assert "ifabric-network" in rows[0] and "**Our rails**" in rows[0]
    assert "ifabric-customer" in rows[1] and "SITE-ADV-99" in rows[1] and "**The platform PDP (Cedar)**" in rows[1]
    assert "`enforce`" in t and "do NOT pre-empt" in t
    for needle in ("HELD", "DETECTED-ONLY", "BROKE", "Observed", "case-sensitive"):
        assert needle in t
    assert "ADV-R-01" in _read("evidence", "adversarial", "README.md")

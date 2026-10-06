"""S-G2: the golden-set false-positive gate (guardrails/PLAN.md §2). Must pass before the agent build.

Gate: every rail over every fixture gives 0 BLOCK and 0 FLAG, except the expected T-02 FLAGs (no evidence)
and X-03 MODIFYs (element -> site). Other MODIFYs allowed: X-01 (tools withheld) and I-02 pii.name
(structured customers[].name -> "Customer <id>", DG-2). The report prints counts per rail.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _railpath  # noqa: F401,E402
from adapters.runtime import rails as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = json.load(open(os.path.join(HERE, "fixtures", "golden.json")))
WIRE7 = ["customer-records___customer_lookup", "runbook-lookup___lookup", "network-twin___predict_rsrp",
         "cr-author___scaffold_cr", "cr-author___patch_cr", "cluster-status___list_resources",
         "evidence-lookup___get_evidence"]
ASSETS = os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-assets")
CONFLICTING = os.path.join(os.path.dirname(os.path.dirname(HERE)), "register", "conditions", "conflicting-context.txt")


def run_golden():
    counts = {}
    for p in GOLDEN["payloads"]:
        r = R.Rails(p["agent"], mode="enforce")
        r.ingress(p["payload"])
        r.tools(WIRE7)
        yield p["scenario"], r
    for c in GOLDEN["tool_calls"]:
        r = R.Rails(c["agent"], mode="enforce")
        cancel, _ = r.before_tool(c["tool"], c["args"])
        assert cancel is None
        r.after_tool(c["tool"], c["result"])
        yield c["scenario"], r


def report():
    tot = {}
    bad = []
    for scen, r in run_golden():
        for rail, c in r.counts.items():
            t = tot.setdefault(rail, {"ALLOW": 0, "BLOCK": 0, "MODIFY": 0, "FLAG": 0})
            for k, v in c.items():
                t[k] += v
        for d in r.records:
            v, rail = d["verdict"], d["rail.id"]
            ok = (v == "FLAG" and rail == "T-02") or (v == "MODIFY" and (rail in ("X-01", "X-03") or
                  (rail == "I-02" and set(d["rail.matches"]) == {"pii.name"})))
            if not ok:
                bad.append((scen, rail, v, d["rail.matches"]))
    return tot, bad


def test_golden_gate_zero_unexpected():
    tot, bad = report()
    for rail in sorted(tot):
        print("S-G2", rail, tot[rail])
    assert bad == [], bad
    assert sum(c["BLOCK"] for c in tot.values()) == 0
    assert tot["T-02"]["FLAG"] > 0 and tot["X-03"]["MODIFY"] > 0   # the expected ones do occur
    assert set(r for r, c in tot.items() if c["FLAG"]) == {"T-02"}


def test_golden_scrub_has_no_hits_on_clean_data():
    # O-04 over every fixture string (payloads after the structured name mask, and tool results): 0 masks
    for p in GOLDEN["payloads"]:
        n = {}
        R._walk(p["payload"], lambda s: R.scrub(s, True, n))
        assert n == {}, (p["scenario"], n)
    for c in GOLDEN["tool_calls"]:
        n = {}
        R.scrub(c["result"], True, n)
        assert n == {}, (c["scenario"], c["args"], n)


def test_golden_o03_grounded_ids_from_evidence():
    # S1-like: an auto-resolve citing its delivered evidence and ids seen in input/evidence stays ALLOW
    p = GOLDEN["payloads"][2]
    r = R.Rails("ifabric-network")
    r.ingress(p["payload"])
    _, a = r.before_tool("network-twin___predict_rsrp", {"site": "DU-DEN-12-A"})
    res = [c for c in GOLDEN["tool_calls"] if c["tool"] == "network-twin___predict_rsrp" and c["args"] == a][0]
    r.after_tool(res["tool"], res["result"])
    j = r.ground({"disposition": "auto-resolve", "deciding_evidence": ["E1"],
                  "reason": "Packet loss on DU-DEN-12-A at SITE-DEN-12", "reversible_step": "switch to protection path"})
    assert j["disposition"] == "auto-resolve"
    assert r.counts["O-03"] == {"ALLOW": 1, "BLOCK": 0, "MODIFY": 0, "FLAG": 0}


def test_conflicting_context_text_if_frozen():
    if not os.path.exists(CONFLICTING):
        print("SKIP: register/conditions/conflicting-context.txt not frozen yet")
        return
    text = open(CONFLICTING).read()
    assert R.scan(text) == {}


def test_design_probe_1_6_phone_patterns():
    # Design §1.6: a naive phone pattern hits 8 times (all ISO dates); the strict NANP pattern hits 0.
    data = os.path.join(ASSETS, "data")
    if not os.path.isdir(data):
        print("SKIP: workshop-assets/data not present")
        return
    naive = re.compile(r"\+?\d[\d\s().-]{7,}\d")
    blob = "".join(open(os.path.join(data, f)).read() for f in sorted(os.listdir(data)) if f.endswith(".json"))
    assert len(naive.findall(blob)) == 8
    assert R.PII["pii.phone"].findall(blob) == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)

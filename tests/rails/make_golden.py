"""Regenerate tests/rails/fixtures/golden.json (S-G2) from the workshop assets. Offline, stdlib.

DERIVED fixtures: the S1-S3 payloads are built exactly as run-reference.sh builds them, plus the
ifabric.run/1 envelope our orchestrator adds; tool outputs come from the packaged Lambda handlers run
locally with DATA_DIR=<workshop-assets>/data. No token or credential is involved.
Usage: python tests/rails/make_golden.py [<workshop-assets dir>]
"""
import importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-assets")
DATA = os.path.join(ASSETS, "data")
os.environ["DATA_DIR"] = DATA


def handler(name):
    spec = importlib.util.spec_from_file_location("h_" + name.replace("-", "_"), os.path.join(ASSETS, "lambda", name, "handler.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.handler


def payloads(scen, cid, n):
    sy = scen["symptoms"]
    cons = sy.get("constraints", [])
    env = {"envelope": "ifabric.run/1", "run_id": cid, "tier": "standard", "tally_tokens": 0, "tally_calls": 0,
           "register_version": "v1", "provenance": "LIVE_SUBJECT", "condition": "none"}
    cx = {"correlation_id": cid, "context": {
        "customers": [{"id": c.split()[0], "name": " ".join(c.split()[1:])} for c in sy.get("affected_customers", [])],
        "symptoms": sy, "operational_constraints": cons}}
    it = {"correlation_id": cid, "context": {
        "incident": {"id": "INC-" + cid[-4:], "severity": "P2", "summary": scen["title"], "alarms": sy.get("alarms", [])},
        "symptoms": sy, "operational_constraints": cons}}
    nw = {"correlation_id": cid, "context": {
        "element": sy.get("element"), "telemetry": {"packet_loss_pct": sy.get("packet_loss_pct"),
                                                     "latency_ms_p95": sy.get("latency_ms_p95")},
        "alarms": sy.get("alarms", []), "operational_constraints": cons}}
    out = []
    for i, (agent, p) in enumerate((("ifabric-customer", cx), ("ifabric-it", it), ("ifabric-network", nw))):
        p = dict(p, ifabric=dict(env, handoff_id="%s:h%d" % (cid, i), to=agent))
        out.append({"scenario": scen["id"], "agent": agent, "payload": p})
    return out


def main():
    inv = json.load(open(os.path.join(DATA, "network-inventory.json")))
    cust, rb, twin = handler("customer-records"), handler("runbook-lookup"), handler("network-twin")
    pays, calls = [], []
    for n, scen in enumerate(inv["fault_scenarios"]):
        cid = "ifabric-run-1791270000-%06x" % (0xa1b2c0 + n)
        pays += payloads(scen, cid, n)
        sy = scen["symptoms"]
        elems = [e.strip() for e in (sy.get("element") or "").split(",") if e.strip()]
        sites = sorted({"SITE-%s-%s" % tuple(e.split("-")[1:3]) for e in elems})
        for site in sites + elems:   # raw element ids too: the model may pass one before X-03 normalises it
            calls.append({"scenario": scen["id"], "agent": "ifabric-customer", "tool": "customer-records___customer_lookup",
                          "args": {"site": site}, "result": json.dumps(cust({"site": site}))})
            calls.append({"scenario": scen["id"], "agent": "ifabric-network", "tool": "network-twin___predict_rsrp",
                          "args": {"site": site}, "result": json.dumps(twin({"site": site}))})
        queries = sites + elems + [scen["id"], scen["title"]] + [a.split()[0] for a in sy.get("alarms", [])]
        for q in queries:
            for cat in ("all", "incidents", "network"):
                calls.append({"scenario": scen["id"], "agent": "ifabric-it", "tool": "runbook-lookup___lookup",
                              "args": {"query": q, "category": cat}, "result": json.dumps(rb({"query": q, "category": cat}, None))})
    doc = {"_synthetic": True,
           "_derived_from": "workshop-assets/reference-impl/run-reference.sh payload builder + workshop-assets/lambda/{customer-records,runbook-lookup,network-twin}/handler.py over workshop-assets/data (2026-10-06); the ifabric envelope ids are synthetic",
           "payloads": pays, "tool_calls": calls}
    with open(os.path.join(HERE, "fixtures", "golden.json"), "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write("\n")
    print(len(pays), "payloads,", len(calls), "tool calls")


if __name__ == "__main__":
    main()

import json, sys, collections
d = json.load(sys.stdin)
ev = d.get("events", [])
pr = collections.Counter(); dec = collections.Counter(); cid_kinds = collections.Counter(); n = 0
first = last = None
for e in ev:
    n += 1
    ts = e.get("timestamp"); first = ts if first is None or ts < first else first; last = ts if last is None or ts > last else last
    try: m = json.loads(e["message"])
    except Exception: continue
    flat = {}
    def walk(x, p=""):
        if isinstance(x, dict):
            for k, v in x.items(): walk(v, p + "." + k if p else k)
        else: flat[p] = x
    walk(m)
    for k, v in flat.items():
        if k.endswith("modaas.evidence.principal") or k.endswith("evidence.principal"): pr[str(v)] += 1
        if k.endswith("modaas.evidence.decision"): dec[str(v)] += 1
        if k.endswith("modaas.evidence.correlation_id"):
            s = str(v); cid_kinds["cid-shaped" if ("-" in s and not all(c in "0123456789abcdef" for c in s)) else "hex/other"] += 1
import datetime
f = lambda t: datetime.datetime.utcfromtimestamp(t/1000).strftime("%Y-%m-%dT%H:%MZ") if t else None
print("events", n, "from", f(first), "to", f(last))
print("principals", dict(pr)); print("decisions", dict(dec)); print("correlation_id kinds", dict(cid_kinds))

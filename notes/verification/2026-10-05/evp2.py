import json, sys, collections, datetime
d = json.load(sys.stdin)
rows = collections.Counter(); ex = {}
for e in d.get("events", []):
    try: m = json.loads(e["message"])
    except Exception: continue
    flat = {}
    def walk(x, p=""):
        if isinstance(x, dict):
            for k, v in x.items(): walk(v, p + "." + k if p else k)
        else: flat[p] = x
    walk(m)
    g = lambda suf: next((str(v) for k, v in flat.items() if k.endswith(suf)), "")
    key = (g("modaas.evidence.decision"), g("modaas.evidence.principal"), g("modaas.evidence.reason")[:60], g("modaas.evidence.policy_id")[:40], g("modaas.evidence.phase"))
    if key[0] == "DENY" or key[1] != 'ServiceIdentity::"bootstrap-key"':
        rows[key] += 1
        ex.setdefault(key, datetime.datetime.utcfromtimestamp(e["timestamp"]/1000).strftime("%m-%dT%H:%MZ"))
for k, c in rows.most_common(): print(c, k, "first", ex[k])

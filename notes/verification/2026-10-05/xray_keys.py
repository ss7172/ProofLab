import json, sys, collections
d = json.load(sys.stdin)
keys_with = collections.Counter(); keys_without = collections.Counter(); n_with = n_without = 0
tok_sum = collections.Counter(); http_status = collections.Counter()
def flat(x, prefix=""):
    out = {}
    if isinstance(x, dict):
        for k, v in x.items():
            out.update(flat(v, (prefix + "." + k) if prefix else k))
    else:
        out[prefix] = x
    return out
for t in d.get("Traces", []):
    for s in t["Segments"]:
        doc = json.loads(s["Document"])
        stack = [doc]
        while stack:
            x = stack.pop()
            stack.extend(x.get("subsegments", []) or [])
            if x.get("name") != "modaas-agw": continue
            f = {}
            for sect in ("annotations", "metadata"):
                f.update(flat(x.get(sect) or {}))
            ks = set(k.split(".", 1)[-1] if k.startswith("default.") else k for k in f)
            has = any(k.endswith("modaas.run_id") for k in f)
            if has: n_with += 1; keys_with.update(ks)
            else: n_without += 1; keys_without.update(ks)
            st = (x.get("http") or {}).get("response", {}).get("status")
            http_status[(has, st)] += 1
            for k, v in f.items():
                if k.endswith("gen_ai.usage.input_tokens") or k.endswith("gen_ai.usage.output_tokens"):
                    try: tok_sum[k.split(".")[-1]] += int(v)
                    except Exception: pass
print("agw segments with run_id:", n_with, "without:", n_without)
print("keys on WITH (top):", sorted(k for k, c in keys_with.items())[:60])
print("keys on WITHOUT (top):", sorted(k for k, c in keys_without.items())[:40])
print("token sums on agw segments:", dict(tok_sum))
print("(has_run_id, http status) counts:", dict(http_status))

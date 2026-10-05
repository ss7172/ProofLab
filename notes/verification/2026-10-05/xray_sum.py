import json, sys, collections
def flat(x, prefix=""):
    out = {}
    if isinstance(x, dict):
        for k, v in x.items():
            out.update(flat(v, (prefix + "." + k) if prefix else k))
    else:
        out[prefix] = x
    return out
d = json.load(sys.stdin)
for t in d.get("Traces", []):
    runs = collections.Counter(); acts = 0; tin = tout = 0; agw = 0; models = collections.Counter()
    for s in t["Segments"]:
        stack = [json.loads(s["Document"])]
        while stack:
            x = stack.pop(); stack.extend(x.get("subsegments", []) or [])
            if x.get("name") != "modaas-agw": continue
            agw += 1
            f = {}
            for sect in ("annotations", "metadata"): f.update(flat(x.get(sect) or {}, sect))
            for k, v in f.items():
                if k.endswith("modaas.run_id"): runs[str(v)] += 1
                elif k.endswith("modaas.action_id"): acts += 1
                elif k.endswith("gen_ai.usage.input_tokens"): tin += int(v)
                elif k.endswith("gen_ai.usage.output_tokens"): tout += int(v)
                elif k.endswith("gen_ai.request.model"): models[str(v)] += 1
    print(t["Id"], "agw", agw, "run_ids", dict(runs), "action_ids", acts, "tokens", tin, "+", tout, "=", tin + tout, "models", dict(models))
print("unprocessed:", d.get("UnprocessedTraceIds"))

import json, sys, collections
d = json.load(sys.stdin)
for t in d.get("Traces", []):
    segs = t.get("Segments", [])
    names = collections.Counter()
    run_ids = collections.Counter(); act = 0; agw_spans = 0; agw_with_act = 0
    def walk(doc, in_agw):
        global act, agw_spans, agw_with_act
        nm = doc.get("name", "")
        is_agw = in_agw or nm == "modaas-agw"
        found_act = False
        for sect in ("annotations", "metadata"):
            blob = doc.get(sect) or {}
            stack = [blob]
            while stack:
                x = stack.pop()
                if isinstance(x, dict):
                    for k, v in x.items():
                        if k in ("modaas.run_id", "modaas_run_id"): run_ids[str(v)] += 1
                        if k in ("modaas.action_id", "modaas_action_id"): found_act = True
                        stack.append(v)
                elif isinstance(x, list):
                    stack.extend(x)
        return nm, is_agw, found_act
    for s in segs:
        doc = json.loads(s["Document"])
        todo = [(doc, False)]
        while todo:
            dd, parent_agw = todo.pop()
            nm, is_agw, fa = walk(dd, parent_agw)
            names[nm] += 1
            if dd.get("name") == "modaas-agw" or (parent_agw and not dd.get("subsegments") is None):
                pass
            if nm == "modaas-agw" or parent_agw:
                agw_spans += 1; agw_with_act += 1 if fa else 0
            for sub in dd.get("subsegments", []) or []:
                todo.append((sub, nm == "modaas-agw" or parent_agw))
    print("trace", t.get("Id"), "segments", len(segs), "top names", dict(names.most_common(6)))
    print("  modaas-agw spans", agw_spans, "with action_id", agw_with_act)
    print("  run_id values", dict(run_ids.most_common(5)))

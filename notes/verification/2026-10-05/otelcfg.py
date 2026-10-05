import json, sys, re
d = json.load(sys.stdin)
for k, v in d.get("data", {}).items():
    print("KEY:", k, "len", len(v))
    # print only service/pipelines, exporters (names + log group/stream), processors names
    try:
        import yaml  # may not exist
        cfg = yaml.safe_load(v)
    except Exception:
        cfg = None
    if cfg is None:
        # crude: print lines mentioning pipelines/exporters/log_group/receivers/processors
        for line in v.splitlines():
            if re.search(r'(pipelines|exporters|receivers|processors|log_group|log_stream|awsxray|awscloudwatch|debug|logs/|traces|metrics|filter|attributes|transform|delete|key:|action:|pattern|sampl)', line, re.I):
                if re.search(r'(token|secret|password|authorization)', line, re.I):
                    print("   <line with credential-like word suppressed>")
                else:
                    print("  ", line)

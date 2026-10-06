# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# VERBATIM copy of the no-PyYAML fallback branch of the workshop kit's starter/evaluate.py
# `_load_register` (PR-01 kit-parity oracle). test_registry_parse.py checks this copy against the kit's
# own file whenever the kit is present on the machine.


def kit_fallback_load_register(text):
    controls, cur = {}, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("- control_id:"):
            if cur:
                controls[str(cur["control_id"])] = cur
            cur = {"control_id": line.split(":", 1)[1].strip().strip('"\'')}
        elif cur is not None and ":" in line:
            k, v = line.strip().split(":", 1)
            v = v.strip().strip('"\'')
            cur[k] = v
    if cur:
        controls[str(cur["control_id"])] = cur
    return controls

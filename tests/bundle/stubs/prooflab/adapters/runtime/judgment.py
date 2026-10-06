"""STUB prooflab.adapters.runtime.judgment (tests/bundle/stubs): last JSON line, else escalate."""
import json


def decide(inv, text, spec, ask):
    if text is None:
        return {"disposition": "escalate", "reason": "no-answer"}
    for line in reversed(text.strip().splitlines()):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("disposition"):
            return obj
    return {"disposition": "escalate", "reason": "invalid-structured-output"}

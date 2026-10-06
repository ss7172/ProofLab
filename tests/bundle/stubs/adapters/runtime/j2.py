"""STUB adapters.runtime.j2 (tests/bundle/stubs): PR-07's names; the last JSON line, else escalate."""
import json


class Judgment(object):
    def __init__(self, disposition, reason="", deciding_evidence=None, reversible_step="", precedence_rule=""):
        self.disposition, self.reason, self.reversible_step = disposition, reason, reversible_step
        self.deciding_evidence, self.precedence_rule = list(deciding_evidence or []), precedence_rule

    def to_record_fields(self):
        return {"disposition": self.disposition, "deciding_evidence": self.deciding_evidence,
                "reversible_step": self.reversible_step, "precedence_rule": self.precedence_rule,
                "reason": self.reason}


def halted_judgment():
    return Judgment("escalate", "c16-budget-halt", precedence_rule="c16-budget-halt")


def judge(answer, ask_again, constraints=None, tool_evidence=None, evidence_needed=None):
    for line in reversed((answer or "").strip().splitlines()):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if isinstance(o, dict) and o.get("disposition"):
            return Judgment(o["disposition"], o.get("reason", ""), o.get("deciding_evidence"),
                            o.get("reversible_step", ""))
    return Judgment("escalate", "invalid-structured-output", precedence_rule="invalid-structured-output")

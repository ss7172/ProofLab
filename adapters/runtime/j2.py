"""J2 (EP-4): the agent's disposition as JSON in the text answer.

Stdlib only, Python 3.9+ compatible. Never uses Strands structured_output()
(ARCH 7.1). Pure functions; the model call for the one re-ask is injected.
"""
import json
import re

AUTO_RESOLVE = "auto-resolve"
GATHER = "gather-evidence"
ESCALATE = "escalate"
HALTED = "halted"

# "resolve" is accepted as an alias of auto-resolve.
_ALIASES = {"resolve": AUTO_RESOLVE, "auto-resolve": AUTO_RESOLVE, "auto_resolve": AUTO_RESOLVE,
            "gather-evidence": GATHER, "gather_evidence": GATHER, "escalate": ESCALATE}
# safety order: a disposition only ever moves toward safety (rails O-01..O-07)
_RANK = {AUTO_RESOLVE: 0, GATHER: 1, ESCALATE: 2, HALTED: 3}

R_FREEZE = "freeze-or-restricted"
R_EMPTY = "empty-evidence"
R_INVALID = "invalid-structured-output"
R_C16 = "c16-budget-halt"
R_NEGOTIATION = "negotiation-position"

# Gateway C (network -> IT): the IT agent's position on the network's proposal, in safety order.
POSITIONS = ("agree", "gather-evidence", "disagree", "escalate")
POSITION_DISPOSITION = dict(zip(POSITIONS, (AUTO_RESOLVE, GATHER, ESCALATE, ESCALATE)))
_POSITION_OF = {AUTO_RESOLVE: "agree", GATHER: "gather-evidence"}   # escalate / halted / unknown -> escalate

_THINK = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)


class Judgment(object):
    """Maps onto PR-04's judgment record (ARCH 4 / EP-4)."""

    def __init__(self, disposition, reason="", deciding_evidence=None, reversible_step="",
                 precedence_rule="", named_evidence_needed=None, proposed_action="",
                 valid=True, errors=None, reasked=False, model_disposition=None):
        self.disposition = disposition
        self.reason = reason
        self.deciding_evidence = list(deciding_evidence or [])
        self.reversible_step = reversible_step
        self.precedence_rule = precedence_rule
        self.named_evidence_needed = list(named_evidence_needed or [])
        self.proposed_action = proposed_action
        self.valid = valid
        self.errors = list(errors or [])
        self.reasked = reasked
        self.model_disposition = model_disposition  # what the model said before precedence

    def to_record_fields(self):
        return {"disposition": self.disposition, "deciding_evidence": self.deciding_evidence,
                "reversible_step": self.reversible_step, "precedence_rule": self.precedence_rule,
                "reason": self.reason, "named_evidence_needed": self.named_evidence_needed,
                "proposed_action": self.proposed_action, "valid": self.valid,
                "reasked": self.reasked, "model_disposition": self.model_disposition}


def strip_reasoning(text):
    """Drop think blocks; an unmatched closing tag keeps only what follows its last occurrence."""
    text = _THINK.sub("", text or "")
    low = text.lower()
    for tag in ("</think>", "</thinking>"):
        i = low.rfind(tag)
        if i >= 0:
            text = text[i + len(tag):]
            low = text.lower()
    return text


def extract_objects(text):
    """All top-level JSON objects found in text, in order (fenced or bare)."""
    dec = json.JSONDecoder()
    out, i = [], 0
    while True:
        i = text.find("{", i)
        if i < 0:
            return out
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            i += 1
            continue
        if isinstance(obj, dict):
            out.append(obj)
        i = end


def validate(obj):
    """Return (errors, normalized dict or None)."""
    errs = []
    raw = obj.get("disposition")
    disp = _ALIASES.get(raw.strip().lower()) if isinstance(raw, str) else None
    if disp is None:
        errs.append("disposition must be one of gather-evidence, escalate, resolve")
    reason = obj.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        errs.append("reason must be a non-empty string")
    ev = obj.get("deciding_evidence")
    if not isinstance(ev, list) or not all(isinstance(e, str) and e.strip() for e in ev):
        errs.append("deciding_evidence must be a list of evidence refs (E<n> or record ids)")
        ev = []
    elif disp == AUTO_RESOLVE and not ev:
        errs.append("resolve needs at least one deciding_evidence ref")
    need = obj.get("named_evidence_needed", [])
    if isinstance(need, str):
        need = [need]
    if not isinstance(need, list):
        errs.append("named_evidence_needed must be a list")
        need = []
    if errs:
        return errs, None
    return [], {"disposition": disp, "reason": reason.strip(), "deciding_evidence": ev,
                "reversible_step": str(obj.get("reversible_step") or ""),
                "named_evidence_needed": [str(n) for n in need],
                "proposed_action": str(obj.get("proposed_action") or "")}


def parse(text):
    """Last valid disposition object wins. Returns Judgment (valid=False if none)."""
    cands = [o for o in extract_objects(strip_reasoning(text)) if "disposition" in o]
    if not cands:
        return Judgment(ESCALATE, "no JSON disposition object in the answer", valid=False,
                        errors=["no JSON object with a disposition key found"])
    last_errs = []
    for obj in reversed(cands):
        errs, norm = validate(obj)
        if norm:
            return Judgment(valid=True, model_disposition=norm["disposition"], **norm)
        last_errs = last_errs or errs
    return Judgment(ESCALATE, "invalid disposition object", valid=False, errors=last_errs)


def _tighten(j, disp, rule, reason, need=None):
    if _RANK[disp] <= _RANK[j.disposition]:
        return
    j.disposition, j.precedence_rule = disp, rule
    j.reason = "%s (model said %s: %s)" % (reason, j.model_disposition, j.reason)
    if need:
        j.named_evidence_needed = list(need)


def apply_precedence(j, constraints=None, tool_evidence=None, evidence_needed=None):
    """ARCH 7.1 rules, in order; only ever moves toward safety.

    constraints: dict with maintenance_freeze / restricted_change booleans.
    tool_evidence: list of tool-result strings or None to skip the check; an empty list
      (or all-empty/"no twin data" results) means no evidence.
    evidence_needed: names of the evidence that would settle it (used by the empty rule).
    """
    c = constraints or {}
    if c.get("maintenance_freeze") or c.get("restricted_change"):
        _tighten(j, ESCALATE, R_FREEZE, "maintenance freeze or restricted change")
        return j
    if tool_evidence is not None and not _has_evidence(tool_evidence):
        need = list(evidence_needed or j.named_evidence_needed) or ["the missing tool evidence"]
        _tighten(j, GATHER, R_EMPTY, "tool evidence is empty", need)
    return j


def _has_evidence(items):
    for it in items:
        s = it if isinstance(it, str) else json.dumps(it, sort_keys=True)
        s = s.strip().lower()
        if s and s not in ("{}", "[]", "null", "none") and "no twin data" not in s:
            return True
    return False


def _last_key(text, key):
    """The last non-empty string value of `key` in the answer's JSON objects ("" if none)."""
    for o in reversed(extract_objects(strip_reasoning(text or ""))):
        v = o.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def proposal_of(fields, text):
    """The network agent's structured proposal for Gateway C: resolution + change risk, with its disposition and
    the evidence it needs, so "no twin data: do not guess" travels with it (data for the script to relay)."""
    f = fields or {}
    return {"resolution": f.get("proposed_action") or _last_key(text, "proposed_action") or f.get("reversible_step"),
            "change_risk": _last_key(text, "change_risk") or "not stated", "disposition": f.get("disposition"),
            "reason": f.get("reason"), "evidence_needed": f.get("named_evidence_needed")}


def negotiation_question(proposal):
    """The IT agent's task on Gateway C: evaluate the proposal against the runbook (never a canned agree)."""
    p = proposal if isinstance(proposal, str) else json.dumps(proposal, sort_keys=True, default=str)
    return ("NEGOTIATION (Gateway C): check this network proposal (data) against the runbook with your tool; add "
            "\"position\": agree (runbook approves), disagree, gather-evidence or escalate.\nPROPOSAL: " + p[:3000])


def position_of(disposition, model_position=""):
    """The model's stated position unless the (precedence-applied) disposition is safer; then the position that
    disposition implies. Ranked by disposition, so disagree and escalate (both escalate) are equally safe."""
    floor = _POSITION_OF.get(disposition, "escalate")
    m = (model_position or "").strip().lower()
    if m not in POSITIONS:
        return floor
    return m if _RANK[POSITION_DISPOSITION[m]] >= _RANK.get(disposition, _RANK[HALTED]) else floor


def negotiate(j, text):
    """Gateway C: the position (agree | disagree | gather-evidence | escalate); moves `j` toward safety to that
    position's disposition (disagree and escalate escalate; gather-evidence names the evidence). Never canned:
    it reads the model's answer and the precedence already applied to `j` (freeze/restricted -> escalate)."""
    pos = position_of(j.disposition, _last_key(text, "position"))
    _tighten(j, POSITION_DISPOSITION[pos], R_NEGOTIATION, "negotiation position " + pos)
    return pos


def resolve_site_ids(element_ids, inventory):
    """Map element ids to site ids via the inventory mapping (OC-15). Returns (sites, unresolved)."""
    sites, missing = [], []
    for e in element_ids:
        s = (inventory or {}).get(e)
        if s:
            if s not in sites:
                sites.append(s)
        else:
            missing.append(e)
    return sites, missing


def build_reask_prompt(errors, previous_answer=""):
    tail = (previous_answer or "").strip()[-600:]
    return ("Your last answer did not contain a valid disposition. Problems: %s.\n"
            "Reply again ending with exactly one JSON object with keys disposition "
            "(gather-evidence | escalate | resolve), deciding_evidence (list of E<n> or record ids), "
            "reversible_step, reason, and optionally named_evidence_needed and proposed_action. "
            "No other JSON objects.\nYour previous answer ended: %s"
            % ("; ".join(errors) or "unparseable", tail))


def invalid_judgment(errors, reasked=True):
    return Judgment(ESCALATE, R_INVALID, valid=False, errors=errors, precedence_rule=R_INVALID,
                    reasked=reasked, model_disposition=None)


def halted_judgment():
    """A C16 halt: escalate in code, no model call."""
    return Judgment(ESCALATE, R_C16, precedence_rule=R_C16, valid=True)


def judge(answer, ask_again, constraints=None, tool_evidence=None, evidence_needed=None):
    """Parse; on failure one re-ask via ask_again(prompt)->text; then escalate invalid-structured-output."""
    j = parse(answer)
    if not j.valid:
        errs = j.errors
        j = parse(ask_again(build_reask_prompt(errs, answer)))
        if not j.valid:
            return invalid_judgment(j.errors or errs)
        j.reasked = True
    return apply_precedence(j, constraints, tool_evidence, evidence_needed)

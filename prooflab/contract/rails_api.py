"""The rails API (guardrails AGENT-GUARDRAILS §5-§6; PLAN B-G1/B-G2). Signatures + shapes only. Stdlib, 3.9.

PR-05 implements these in `adapters/runtime/rails.py` (pure, stdlib, vendored into each agent bundle);
PR-03's per-event dispatcher calls them (rails -> C16 -> emit, fixed code order) and PR-04 emits the
records. Nothing here decides anything; the helpers only convert a RailDecision into the one record.

    check_input(text, envelope, policy)                 -> RailOutcome   # EP-14: I-01..I-04 (entrypoint)
    check_tools(tool_names, policy)                     -> RailOutcome   # X-01 at load_tools() (discovery)
    check_tool_call(tool_name, args, policy, state)     -> RailOutcome   # EP-3 before: X-05, X-02, X-03, X-04
    check_tool_result(tool_name, text, policy, state)   -> RailOutcome   # EP-3 after: T-01..T-06
    check_output(text, policy, state)                   -> RailOutcome   # EP-4: O-01..O-07
    decisions(outcome)                                  -> list          # the RailDecision dicts, in order
    policy_sha256(policy)                               -> str           # RT-01/RT-04: sha256 of the table

RailOutcome (dict):
    {"verdict": worst of the decisions (BLOCK > MODIFY > FLAG > ALLOW),
     "output":  the (possibly modified) subject to pass on, or None when blocked,
     "decisions": [RailDecision, ...]}
RailDecision (dict):
    {"rail_id": "X-02", "rail_version": "1", "stage": RAIL_STAGES, "hook": RAIL_HOOKS,
     "mechanism": "code", "verdict": "ALLOW|BLOCK|MODIFY|FLAG",
     "matches": {"<rule id>": <count>},              # rule ids and counts, never text
     "subject": "tool_use:<id>" | "input" | "output" | ...,
     "subject_sha256_in": "<64 hex>", "subject_sha256_out": "<64 hex>" | None,
     "reason": "<rule ids that fired, with counts>", "threshold_value": "<rule parameter or its digest>"}

Records (DG-3 compact default): every non-ALLOW decision -> one full `rail_decision` record
(`rail_record`); ALLOWs ride on the host EP's record as `rails.allow` + `rails.policy_sha256`
(`attach_compact_allows`); the invocation's lifecycle record carries `rails.counts` (`count_into`).
"""
from __future__ import annotations

from prooflab.contract import record as _rec
from prooflab.contract import verdicts as _v

SEVERITY = {"ALLOW": 0, "FLAG": 1, "MODIFY": 2, "BLOCK": 3}
RAIL_EP_KIND = "sidecar / SDK: interceptor in the process"
RAIL_DECISION_KEYS = ("rail_id", "rail_version", "stage", "hook", "mechanism", "verdict", "matches", "subject",
                      "subject_sha256_in", "subject_sha256_out", "reason", "threshold_value")


def worst(verdicts) -> str:
    """The combined verdict of several rail verdicts (ALLOW when empty)."""
    out = "ALLOW"
    for v in verdicts:
        if v not in SEVERITY:
            raise ValueError("not a rail verdict: %r" % (v,))
        if SEVERITY[v] > SEVERITY[out]:
            out = v
    return out


def validate_rail_decision(d) -> list:
    if not isinstance(d, dict):
        return ["rail decision must be an object"]
    errors = ["%s: missing" % k for k in ("rail_id", "rail_version", "stage", "hook", "verdict") if not d.get(k)]
    if d.get("verdict") not in _v.RAIL_VERDICTS:
        errors.append("verdict: not a rail verdict")
    if d.get("stage") not in _rec.RAIL_STAGES:
        errors.append("stage: not in %s" % list(_rec.RAIL_STAGES))
    if d.get("hook") not in _rec.RAIL_HOOKS:
        errors.append("hook: not in %s" % list(_rec.RAIL_HOOKS))
    matches = d.get("matches") or {}
    if not isinstance(matches, dict) or not all(isinstance(n, int) for n in matches.values()):
        errors.append("matches: {rule id: count}")
    return errors


def rail_record(decision: dict, ctx: dict) -> dict:
    """A full `rail_decision` record from one RailDecision and the invocation context.

    ctx keys (dotted record fields): run.id, handoff.id, actor.id, actor.version, ep.id, inline.mode,
    rail.policy_sha256, emitted.at, emitted.clock, emitter, provenance, record_id, plus any optional
    record fields (trace.id, seq.in_stream, call.id, tool.*). Unset table-A fields become null with a reason.
    """
    mode = ctx.get("inline.mode", "enforce")
    fields = dict(ctx)
    fields.update({
        "detail": "%s %s: %s" % (decision["rail_id"], decision["verdict"], decision.get("reason") or ""),
        "control.ref": "RAIL",
        "control.id": "RAIL-" + decision["rail_id"],
        "threshold.version": "%s@%s" % (decision["rail_id"], decision["rail_version"]),
        "threshold.sha256": ctx.get("rail.policy_sha256"),
        "threshold.value": decision.get("threshold_value"),
        "verdict": decision["verdict"],
        "reason": decision.get("reason"),
        "inline.mode": mode,
        "inline.action": _v.rail_action(decision["verdict"], mode),
        "rail.id": decision["rail_id"],
        "rail.version": str(decision["rail_version"]),
        "rail.stage": decision["stage"],
        "rail.hook": decision["hook"],
        "rail.mechanism": decision.get("mechanism", "code"),
        "rail.subject": decision.get("subject"),
        "rail.subject_sha256_in": decision.get("subject_sha256_in"),
        "rail.subject_sha256_out": decision.get("subject_sha256_out"),
        "rail.matches": decision.get("matches") or {},
        "ep.kind": RAIL_EP_KIND,
        "ep.transport": "emit",
        "authorship": "TESTIMONY",
    })
    for key in ("rail.subject_sha256_out", "rail.subject"):
        if fields.get(key) is None:
            fields.pop(key)
    reasons = dict(fields.pop("null_reasons", None) or {})
    reasons.setdefault("register.version", "not a register control: rail")
    return _rec.new_record("rail_decision", null_reason="not applicable: rail decision",
                           null_reasons=reasons, **fields)


def attach_compact_allows(host: dict, decisions, policy_sha256: str) -> dict:
    """Copy of a host EP record with the ALLOW decisions as `rails.allow` tags (DG-3 compact)."""
    out = dict(host)
    tags = [_rec.rail_tag(d["rail_id"], d["rail_version"]) for d in decisions if d["verdict"] == "ALLOW"]
    out["rails.allow"] = list(out.get("rails.allow") or []) + tags
    out["rails.policy_sha256"] = policy_sha256
    return out


def count_into(counts: dict, decisions) -> dict:
    """Add decisions into a `rails.counts` map {rail: {ALLOW, BLOCK, MODIFY, FLAG}} (returns a new map)."""
    out = dict((k, dict(v)) for k, v in (counts or {}).items())
    for d in decisions:
        row = out.setdefault(d["rail_id"], dict((v, 0) for v in _v.RAIL_VERDICTS))
        row[d["verdict"]] = row.get(d["verdict"], 0) + 1
    return out

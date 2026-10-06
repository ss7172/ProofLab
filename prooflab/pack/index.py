"""Pack-index builder (G-07, T5.3): the console's table of contents, `ifabric.pack-index/v1`. Stdlib, 3.9.

ONE-WAY: this module and `projector.py` read the pack's source tree and WRITE the console projection. Nothing in
prooflab/ reads the projection back (the console's server reads it, never our code). Every value is derived from
the source tree or marked as not supplied; nothing is invented. No threshold literals live here.

`build_index(ctx)` takes plain dicts (see `projector.load_context`) and returns the pack-index dict.
`ENFORCEMENT_POINTS` is our EP-0..EP-16 (ARCHITECTURE section 3.6) with the schema's six `kind` values; `status` is
computed from the evidence by `enforcement_points(ep_seen)`, never fixed here (EP-13 is the one fixed ALERT_ONLY).
"""
from __future__ import annotations

import hashlib
import json
import os
import re

CONTROL_NAMES = {
    "C16": ("ACN-COST-001", "Per-run token spend cap", "in-transaction"),
    "C7": ("AIA-LOG-001", "Automatic event recording", "event-driven"),
    "C9": ("AIA-ARC-006", "Drift and performance", "continuous"),
    "ESC": ("AGENT-ESCALATION", "Agent escalation", "event-driven"),
}
CONTROL_ORDER = ("C16", "C7", "C9", "ESC")
NOT_SUPPLIED = "(not supplied in the pack's source tree)"
ZERO_SHA = "0" * 64

# id, name, kind (schema enum), kind_detail, transport, can_refuse, controls, observed_only
# observed_only: a platform or human EP we do not build; its status is EVIDENCED at best, never BUILT.
ENFORCEMENT_POINTS = (
    ("EP-0", "Pre-run version gate (preflight)", "sdk-interceptor", "script preflight", "evaluate", True, ["APPROVAL"], False),
    ("EP-1", "Model call inside our agent runtime", "sdk-interceptor", "model-call adapter", "evaluate", True, ["C16"], False),
    ("EP-2", "Managed gateway log, after the run", "model-gateway", "spend and actions adapter over aws/spans", "pull", False, ["C16", "C7"], True),
    ("EP-3", "Tool call inside our agent runtime", "sdk-interceptor", "tool-call adapter", "emit", False, ["C7"], False),
    ("EP-4", "Agent judgment (disposition)", "sdk-interceptor", "judgment adapter", "emit", False, ["C7", "ESC"], False),
    ("EP-5", "Sub-agent handoff (orchestrating script)", "sub-agent-handoff", "orchestrator handoff records", "emit", False, ["C7"], False),
    ("EP-6", "Gateway authorization (modaas-authz, PDP/Cedar)", "tool-call", "platform Cedar policy", "pull", True, [], True),
    ("EP-7", "Guardrails and the real outcome of each call", "model-gateway", "Bedrock guardrail, observed", "pull", True, [], True),
    ("EP-8", "Kill switch (pause)", "kill-switch", "route withdrawal, observed", "out-of-band", True, [], True),
    ("EP-9", "Rate ceilings", "model-gateway", "platform ceilings, observed", "pull", True, [], True),
    ("EP-10", "Admission (CEL + VAP) and asset approvals", "human-approval-queue", "admission and approval annotations", "pull", True, ["APPROVAL"], True),
    ("EP-11", "AgentCore runtime invocation and its metrics", "sdk-interceptor", "AgentCore invoke records", "pull", False, ["C9"], True),
    ("EP-12", "AgentCore gateway and Lambda tools", "tool-call", "AWS_IAM tools, code sha read", "pull", True, [], True),
    ("EP-13", "Human approval queue (ServiceNow)", "human-approval-queue", "ServiceNow incident, owner reply", "callback", False, ["C16", "C7", "C9", "ESC"], True),
    ("EP-14", "Agent ingress rails", "sdk-interceptor", "entrypoint rails", "emit", True, [], False),
    ("EP-15", "Runtime egress audit", "sdk-interceptor", "audit hook, observe", "emit", False, [], False),
    ("EP-16", "The cockpit ask API (side door)", "model-gateway", "observed side door, no control of ours", "pull", False, [], True),
)

REF_RE = re.compile(r"^[a-z][a-z0-9-]*:\S.*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def enforcement_points(ep_seen):
    """Our EP-0..EP-16 with an honest status. `ep_seen` = {ep id: [evidence refs]} counted from the stored records.

    BUILT only where records of that EP exist; EP-13 is ALERT_ONLY by design (a notification, never a refusal) once
    records exist; an EP we only observe is EVIDENCED when records exist; otherwise NOT_RUN (we built or observe it,
    but the pack holds no record of it running). Nothing is BUILT on the strength of a plan.
    """
    out = []
    for ep_id, name, kind, detail, transport, can_refuse, controls, observed in ENFORCEMENT_POINTS:
        refs = list(ep_seen.get(ep_id) or [])[:5]
        seen = bool(ep_seen.get(ep_id))
        if not seen:
            status, note = "NOT_RUN", "no record of this enforcement point in the pack"
        elif ep_id == "EP-13":
            status, note = "ALERT_ONLY", "records a notification and the owner's reply; it refuses nothing"
        elif observed:
            status, note = "EVIDENCED", "observed from the platform's own records; not ours to change"
        else:
            status, note = "BUILT", "records of this enforcement point are in the pack"
        out.append({"id": ep_id, "name": name, "kind": kind, "kind_detail": detail, "transport": transport,
                    "can_refuse": can_refuse, "status": status, "controls": list(controls),
                    "evidence_refs": refs, "note": note})
    return out


def good_refs(values, limit=None):
    out = []
    for v in values or []:
        if isinstance(v, str) and REF_RE.match(v):
            out.append(v)
        elif isinstance(v, str) and v:
            out.append("record:" + v.replace("\n", " "))
    return out[:limit] if limit else out


def person(name=None, ident=None, role=None):
    p = {"name": name or ident or "UNASSIGNED", "id": ident or name or "UNASSIGNED"}
    if role:
        p["role"] = role
    return p


def _overall(verdicts):
    vs = [v for v in verdicts if v]
    if not vs:
        return "NOT_ASSESSED"
    if "BREACHED" in vs:
        return "BREACHED"
    if all(v == "SATISFIED" for v in vs):
        return "SATISFIED"
    if "INDETERMINATE" in vs:
        return "INDETERMINATE"
    return "NOT_ASSESSED" if all(v == "NOT_ASSESSED" for v in vs) else "INDETERMINATE"


def claim_verdict(overalls):
    vs = [v for v in overalls if v]
    if "BREACHED" in vs:
        return "NOT_SATISFIED"
    if vs and all(v == "SATISFIED" for v in vs):
        return "SATISFIED"
    return "NOT_ESTABLISHED"


def build_controls(ctx):
    """claim.controls[]: the verdict per control from the projected assessments; completeness a-g from what the pack holds."""
    by_ctl = {}
    for a in ctx["assessments"]:
        by_ctl.setdefault(a["control_ref"], []).append(a)
    named = ctx.get("named_runs") or {}
    out = []
    for ref in CONTROL_ORDER:
        rows = by_ctl.get(ref) or []
        reg_ref = ref in (ctx.get("register_controls") or {})
        if not rows and not reg_ref:
            continue
        cid, name, mode = CONTROL_NAMES[ref]
        verdicts = [a["verdict"] for a in rows]
        entry = {"ref": ref, "id": cid, "name": name, "mode": mode, "verdict_overall": _overall(verdicts)}
        passed = next((a for a in rows if a["verdict"] == "SATISFIED"), None)
        breached = next((a for a in rows if a["verdict"] == "BREACHED"), None)
        for key, a in (("pass", passed), ("breach", breached)):
            if a:
                m = a.get("measured") or {}
                entry[key] = {"run": a["scope"].get("alias") or a["scope"]["id"], "verdict": a["verdict"],
                              "measured": "%s %s" % (m.get("value"), m.get("unit")),
                              "answer_ref": "assessment:" + a["assessment_id"]}
        findings = [f for f in ctx.get("findings") or [] if f["control_ref"] == ref]
        entry["completeness"] = {
            "a_register": reg_ref,
            "b_bound_records": ctx["record_counts"].get(ref, 0) > 0,
            "c_evaluator": bool(rows),
            "d_named_runs": any(e.get("control") == ref for e in named.get("entries") or []),
            "e_owner_alerted": any(f.get("incident") for f in findings),
            "f_query_under_2min": False,   # never measured by this projector: stays false until a timed query is recorded
            "g_gaps_recorded": any(a.get("gaps") for a in rows) or bool(ctx.get("gaps")),
        }
        entry["findings_open"] = sum(1 for f in findings if (f.get("closure") or {}).get("state") != "CLOSED_BY_RETEST")
        entry["built_properly"] = all(v for k, v in entry["completeness"].items() if k != "f_query_under_2min")
        entry["actually_worked"] = None if not rows else entry["verdict_overall"] == "SATISFIED"
        out.append(entry)
    return out


def build_register(ctx):
    reg = ctx.get("register") or {}
    top = reg.get("top") or {}
    approval = ctx.get("approval") or {"status": "MISSING"}
    owner = person(top.get("owner_name"), top.get("owner") or top.get("register_owner"), "control owner")
    controls = []
    for ref in CONTROL_ORDER:
        e = (ctx.get("register_controls") or {}).get(ref)
        if e:
            controls.append(register_control(ref, e, owner))
    first = ctx.get("first_assessed_run_at")
    return {
        "version": top.get("version") or top.get("register_version") or "UNKNOWN",
        "sha256": reg.get("sha256") or ZERO_SHA,
        "frozen_at": top.get("frozen_at") or ctx["as_of"],
        "owner": owner,
        "builder": person(top.get("builder"), top.get("builder"), "builder"),
        "assurance": person(top.get("assurance"), top.get("assurance"), "assurance"),
        "approval": approval,
        "first_assessed_run_at": first,
        "exploratory_runs": ctx.get("exploratory_runs", 0),
        "versions": ctx.get("register_versions") or [],
        "controls": controls,
    }


def _num(text):
    try:
        return float(text) if "." in str(text) else int(str(text))
    except (TypeError, ValueError):
        return None


def limit_of(entry, key, default_unit):
    v = _num(entry.get(key))
    if v is None:
        return None
    op = entry.get("limit_direction") if key == "observation_limit" else None
    return {"value": v, "operator": op if op in ("<", "<=", ">", ">=", "==") else "<=",
            "unit": entry.get("metric_unit") or default_unit}


def register_control(ref, e, owner):
    cid, name, mode = CONTROL_NAMES[ref]
    ns = NOT_SUPPLIED
    out = {
        "ref": ref, "id": cid, "name": e.get("name") or name,
        "mode": e.get("mode") if e.get("mode") in ("static", "scheduled", "event-driven", "in-transaction", "continuous") else mode,
        "version": e.get("threshold_version") or "UNKNOWN",
        "version_date": e.get("version_date") or "1970-01-01",
        "owner": person(e.get("owner_name"), e.get("owner"), "control owner") if e.get("owner") else owner,
        "metric": e.get("metric") or ns,
        "observation_limit": limit_of(e, "observation_limit", "unit") or {"value": 0, "operator": "<=", "unit": "unknown"},
        "exception_tolerance": limit_of(dict(e, limit_direction="<=", metric_unit=e.get("exception_unit") or "exceptions"),
                                        "exception_tolerance", "exceptions") or {"value": 0, "operator": "<=", "unit": "exceptions"},
        "measurement_basis": e.get("measurement_basis") or ns,
        "enforcement_point": e.get("enforcement_point") or ns,
        "justification": {"why_this_metric": e.get("why_metric") or ns, "why_this_value": e.get("why_value") or ns,
                          "how_measured": e.get("measured_on") or ns, "when_it_stops_holding": e.get("stops_holding_when") or ns},
        "governance": {"objective": e.get("objective") or ns, "risk": e.get("risk") or ns,
                       "control_test": e.get("test_procedure") or ns, "evidence": e.get("evidence_artefacts") or ns},
    }
    if e.get("applicability") or e.get("applies_to"):
        out["applicability"] = e.get("applicability") or e.get("applies_to")
    return out


def build_index(ctx):
    """ctx keys: as_of, generated_at, pack{title,team,event_window,...}, assessments (projected), findings, cases, runs,
    named_runs, gaps, levels, environments, artefacts, integrity, record_counts, ep_seen, register..., provenance."""
    controls = build_controls(ctx)
    summary_bits = ["%s %s" % (c["ref"], c["verdict_overall"]) for c in controls]
    claim = ctx.get("claim") or {}
    return {
        "schema": "ifabric.pack-index/v1",
        "generated_at": ctx["generated_at"],
        "provenance": ctx.get("provenance", "ASSESSED"),
        "pack": ctx["pack"],
        "claim": {"id": claim.get("id") or "UNSET", "text": claim.get("text") or NOT_SUPPLIED,
                  "verdict": claim_verdict([c["verdict_overall"] for c in controls]),
                  "summary": claim.get("summary") or ("; ".join(summary_bits) or "no assessments in the pack"),
                  "controls": controls},
        "register": build_register(ctx),
        "artefacts": ctx.get("artefacts") or [],
        "named_runs": ctx.get("named_runs") or {"written_at": ctx["as_of"], "entries": []},
        "runs": ctx.get("runs") or [],
        "assessments": [{"assessment_id": a["assessment_id"], "control_ref": a["control_ref"], "verdict": a["verdict"],
                         "scope": a["scope"], "path": a["_path"]} for a in ctx["assessments"]],
        "cases": ctx.get("cases") or [],
        "findings": ctx.get("findings") or [],
        "answers": ctx.get("answers") or [],
        "auditor": ctx.get("auditor") or [],
        "adversarial": ctx.get("adversarial") or [],
        "gaps": ctx.get("gaps") or [],
        "levels": ctx.get("levels") or [
            {"level": l, "status": "NOT_SHOWN", "items": []} for l in ("L1_FOUNDATION", "L2_OBSERVABILITY", "L3_EXTENDED_CHAIN")],
        "environments": ctx.get("environments") or [],
        "enforcement_points": enforcement_points(ctx.get("ep_seen") or {}),
        "integrity": ctx["integrity"],
    }


def dumps(doc):
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_index(out_dir, doc):
    path = os.path.join(out_dir, "pack-index.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dumps(doc))
    return path

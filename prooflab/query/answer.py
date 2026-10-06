"""The answer composer (ARCH 3.7, T5.2). Stdlib only, Python 3.9. Offline: reads an unzipped Evidence Pack.

ask(pack, text) -> {"ok", "kind", "doc", "exit", "parse"}:
    kind "answer"   doc = an `ifabric.answer/v1` document (one control test over a run or a window)
    kind "auditor"  doc = an `ifabric.auditor/v1` document (the six questions)
    kind "gap"      doc = {"kind": "gap", ...}: the pack cannot answer; says what is missing, never guesses
    kind "trail" | "told" | "unparsed"
Every verdict comes from the stored assessment (engine.control_run / control_window); this module only shapes it.
answer_id = sha256 of the canonical JSON without answer_id, answered_at, elapsed_ms and source.mode (Arth's
generate_examples.answer_id_of), so the same question over the same pack gives the same id.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
import time

from prooflab.contract import verdicts as V
from prooflab.query import engine as E
from prooflab.query import grammar as G

CONTROL_IDS = {"C16": "ACN-COST-001", "C7": "AIA-LOG-001", "C9": "AIA-ARC-006"}      # Arth's schema enum
CONTROL_NAMES = {"C16": "Per-run token spend cap", "C7": "Event recording coverage", "C9": "Drift against a frozen baseline"}
CONTROL_MODES = {"C16": "in-transaction", "C7": "event-driven", "C9": "scheduled"}
_UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$")
RECORD_LIMIT = 40
_ROLE = {"assessment": "measurement", "decision": "decision", "platform_decision": "decision",
         "action": "operation", "handoff": "operation"}


# ---------------------------------------------------------------- small helpers
def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def answer_id_of(answer):
    """Byte-for-byte Arth's generate_examples.answer_id_of."""
    stable = dict((k, v) for k, v in answer.items() if k not in ("answer_id", "answered_at", "elapsed_ms"))
    stable["source"] = dict((k, v) for k, v in answer["source"].items() if k != "mode")
    return sha(json.dumps(stable, sort_keys=True, ensure_ascii=False))


def now_utc():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_or(text, default=None):
    text = str(text or "")
    return text if _UTC_RE.match(text) else default


def _num(x):
    v = E._num(x)
    return v


def _gap_doc(parse, message, **extra):
    doc = {"kind": "gap", "verdict": V.NOT_ASSESSED, "message": message, "query": parse.get("text"),
           "normalized": parse.get("normalized"), "gaps": [message]}
    doc.update(extra)
    return doc


def manifest_state(pack):
    """(sha256 of MANIFEST.json, status VERIFIED|MODIFIED|UNVERIFIED, {path: ok}) from the pack's own manifest."""
    path = pack.p("MANIFEST.json")
    try:
        raw = open(path, "rb").read()
        doc = json.loads(raw.decode("utf-8"))
    except (IOError, OSError, ValueError):
        return "0" * 64, "UNVERIFIED", {}
    files = doc.get("files") if isinstance(doc, dict) else None
    if not isinstance(files, list) or not files:
        return hashlib.sha256(raw).hexdigest(), "UNVERIFIED", {}
    ok, status = {}, "VERIFIED"
    for e in files:
        rel, want = (e or {}).get("path"), (e or {}).get("sha256")
        try:
            have = hashlib.sha256(open(pack.p(rel), "rb").read()).hexdigest()
        except (IOError, OSError, TypeError):
            have = None
        ok[rel] = have == want
        if have != want:
            status = "MODIFIED"
    return hashlib.sha256(raw).hexdigest(), status, ok


def _source(pack, records):
    msha, status, ok = manifest_state(pack)
    return ({"mode": "PACK", "pack_root": "evidence/", "manifest_sha256": msha, "manifest_status": status,
             "records_scanned": records}, ok)


def _provenance(raw, run_start, t1):
    if raw == "SYNTHETIC":
        return "SYNTHETIC"
    if raw == "WIRING_TEST":
        return "WIRING_TEST"
    if raw in E.WINDOW_PROVENANCE:
        a, b = E._utc_key(run_start), E._utc_key(t1)
        return "EXPLORATORY" if (a and b and a < b) else "ASSESSED"
    return "EXPLORATORY"


def _person(name):
    n = name or E.UNKNOWN
    return {"name": n, "id": n, "role": "control owner (register)"}


def _limit(value, operator, unit, label=None):
    out = {"value": value, "operator": operator, "unit": unit}
    if label:
        out["label"] = label
    return out


def _rule(pack, control, a, gaps):
    """The `rule` block from the register entry bound to the assessment; None when the pack has no such entry."""
    rname, entry = pack.control_entry(control, a["threshold_version"], a["register_version"])
    if entry is None:
        return None, None
    reg = pack.registers[rname]
    top = reg["doc"]["top"]
    t1_file, t1 = pack.t1_for(a["threshold_version"], control)
    vdate = str(entry.get("version_date") or top.get("version_date") or "")
    frozen = _utc_or(t1) or _utc_or(vdate)
    if frozen is None:
        return None, None
    lim, op = _num(a["limit"]), "<="
    if lim is None:
        lim = _num(entry.get("observation_limit"))
    extra = {}
    if lim is None and control == "C9":
        # C9's numbers in one string (`max_relative_change_pct=..;violating_windows_max_pct=..;errors_max=..`, the form
        # prooflab.evaluators.c9 reads): the judged limit is the relative change against the frozen baseline, inclusive
        from prooflab.evaluators import claim as _claim
        parts = _claim.parse_limits(entry.get("observation_limit"))
        lim, op = _num(parts.get("max_relative_change_pct")), "<="
        extra = dict((k, _num(v)) for k, v in parts.items() if k != "max_relative_change_pct" and _num(v) is not None)
    if lim is None and control == "C7":
        # C7's numbers live in one string (`coverage_min_pct=..;gap_max_ms=..;violating_gap_share_max_pct=..`, the form
        # prooflab.evaluators.c7.limits_of reads): coverage is the judged floor, so the operator is >=
        from prooflab.evaluators import claim as _claim
        parts = _claim.parse_limits(entry.get("observation_limit"))
        lim, op = _num(parts.get("coverage_min_pct")), ">="
        extra = dict((k, _num(v)) for k, v in parts.items() if k != "coverage_min_pct" and _num(v) is not None)
    if lim is None:
        return None, None
    tol = _num(entry.get("exception_tolerance"))
    if tol is None:
        gaps.append({"id": "G-TOL", "text": "exception_tolerance missing or not numeric in the register; shown as 0 allowed", "affects": "rule.exception_tolerance"})
        tol = 0
    unit = (a.get("measured") or {}).get("unit") or (("% relative change vs baseline") if control == "C9" else E.UNKNOWN)
    approval = top.get("approval")
    approval = ({"status": "APPROVED", "ref": approval} if isinstance(approval, str) and re.match(r"^[a-z][a-z0-9-]*:\S", approval)
                else {"status": "MISSING"})
    if approval["status"] == "MISSING":
        # the T2 files: register/approval*/ (Finding + canonical note), the delivery log, the ServiceNow export
        from prooflab.pack import history as _h
        t2 = _h.approvals(pack.root).get(str(rname))
        if t2:
            approval = dict((k, t2[k]) for k in ("status", "ref", "at", "approver") if t2.get(k))
            if approval["status"] != "APPROVED":
                gaps.append({"id": "G-APPR", "text": "register %s approval is %s: %s" % (rname, t2["status"], t2.get("note") or ""),
                             "affects": "rule.approval"})
    if approval["status"] == "MISSING":
        gaps.append({"id": "G-APPR", "text": "no register approval record in the pack (register/ carries none)", "affects": "rule.approval"})
    first_run = E._utc_key(a.get("scope_start"))
    before = bool(t1 and first_run and E._utc_key(frozen) and E._utc_key(frozen) <= first_run)
    owner = entry.get("owner") or top.get("register_owner")
    rule = {"register_version": str(rname), "threshold_version": a["threshold_version"],
            "version_date": vdate[:10] if re.match(r"^\d{4}-\d\d-\d\d", vdate) else "1970-01-01",
            "frozen_at": frozen, "owner": _person(owner), "approval": approval, "date_before_scope": before,
            "statement": entry.get("metric") or entry.get("name") or E.UNKNOWN,
            "observation_limit": _limit(lim, op, unit),
            "exception_tolerance": _limit(tol, "<=", "breached runs"),
            "measurement_basis": entry.get("measurement_basis") or E.UNKNOWN,
            "source_ref": "register:register/versions/%s.yaml#%s" % (rname, control),
            "register_sha256": _file_sha(pack.p("register", "versions", "%s.yaml" % rname))}
    if extra:
        rule["other_limits"] = extra      # e.g. C7 gap_max_ms, violating_gap_share_max_pct (judged by the evaluator)
    return rule, entry


def _file_sha(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except (IOError, OSError):
        return "0" * 64


def _approved_before(rule, run_start):
    """True only when the owner's approval time is recorded and at or before the run start (never on a dated register alone)."""
    at, start = E._utc_key((rule.get("approval") or {}).get("at")), E._utc_key(run_start)
    return bool(at and start and at <= start)


def _dated_before(at, start):
    """True / False when both UTC times are recorded, None when either is missing."""
    a, b = E._utc_key(at), E._utc_key(start)
    return None if not (a and b) else a <= b


def _cmp(at, start):
    b = _dated_before(at, start)
    return "before" if b else "after" if b is False else "not proven before"


def _with_dates(pack, control, rule):
    """The rule plus WHICH register frozen_at belongs to: frozen_at is the S3 (T1) date of the FIRST register that carried
    the threshold version (t1_register); register_t1 is the S3 (T1) date of the register named in register_version.
    Read from the T1 heads; nothing is rewritten."""
    try:
        first, _t = pack.t1_for(rule.get("threshold_version"), control)
        head = (pack.registers.get(rule.get("register_version")) or {}).get("head") or {}
    except Exception:
        return rule
    own = head.get("LastModified") or head.get("last_modified") or head.get("t1")
    own = E._utc_key(own) and own or (re.sub(r"\+00:00$", "Z", own) if isinstance(own, str) else None)
    return dict(rule, t1_register=first or rule.get("register_version"), register_t1=_utc_or(own))


def _authority_text(rule, run_start, label="run start"):
    """Who authorised the rule and WHEN, stated exactly: the S3 (T1) date of the register that FIRST carried the threshold
    version, the S3 date of the register named (when different), and the ServiceNow approval time, each vs the scope start."""
    ap = rule.get("approval") or {}
    who = "register owner: %s" % ((rule.get("owner") or {}).get("id") or (rule.get("owner") or {}).get("name") or E.UNKNOWN)
    first = rule.get("t1_register") or rule.get("register_version")
    t1 = "threshold version %s first dated by S3 (T1) %s in register %s, %s the %s %s" % (
        rule.get("threshold_version") or "not recorded", rule.get("frozen_at"), first, _cmp(rule.get("frozen_at"), run_start),
        label, run_start or "not recorded")
    if rule.get("register_version") and rule.get("register_version") != first:
        t1 += "; register %s (the rule shown) dated by S3 (T1) %s, %s the %s" % (
            rule["register_version"], rule.get("register_t1") or "not recorded", _cmp(rule.get("register_t1"), run_start), label)
    if rule.get("bound_by"):
        who += "; threshold version bound by %s" % rule["bound_by"]
    if ap.get("status") == "APPROVED" and ap.get("at"):
        noun = "run" if label == "run start" else label
        when = ("approved before the %s" % noun if _approved_before(rule, run_start)
                else "approved after the %s; dated before the %s by S3" % (noun, noun)
                if _dated_before(rule.get("frozen_at"), run_start) else "approved after the %s" % noun)
        appr = "ServiceNow approval note %s on %s, responded from account %s (%s)" % (ap["at"], str(ap.get("ref") or "").replace("servicenow:", ""),
                                                             (ap.get("approver") or {}).get("id") or "not recorded", when)
    else:
        appr = "approval %s" % (ap.get("status") or "MISSING")
    return "%s; %s; %s" % (who, t1, appr)


def _first_carrier_approval(pack, control, threshold_version):
    """(register, approval) of the FIRST register that carried this threshold version (the approval that bound it), from
    the T2 files; (None, None) when the pack has none. A later register re-carrying the same version does not re-date it."""
    try:
        from prooflab.pack import history as _h
        appr = _h.approvals(pack.root) or {}
        names = sorted(pack.registers, key=lambda n: pack._reg_date(n))
    except Exception:
        return None, None
    for name in names:
        if any(e.get("control_ref") == control and e.get("threshold_version") == threshold_version
               for e in pack.registers[name]["doc"]["entries"]):
            a = appr.get(str(name))
            return (str(name), dict((k, a[k]) for k in ("status", "ref", "at", "approver") if a.get(k))) if a else (str(name), None)
    return None, None


def _bound_rule(pack, control, rule, run_start):
    """The rule as the approval that FIRST bound its threshold version sees it (C7-v1/C9-v1 carried by v1, approved before
    the run, are re-carried unchanged by v1.1); the rule itself when no earlier approval applies."""
    name, ap = _first_carrier_approval(pack, control, rule.get("threshold_version"))
    if not name or not ap or name == rule.get("register_version") or ap.get("status") != "APPROVED":
        return rule
    if not _approved_before(dict(rule, approval=ap), run_start):
        return rule
    return dict(rule, approval=ap, register_version=name, bound_by="register %s (first carried %s)" % (name, rule.get("threshold_version")))


def _tick_text(ok, manifest_status, a, rc, rule, corr=None, run_start=None, label="run start"):
    """V is lit only when the owner's approval is recorded at or before the scope start AND the threshold version was
    dated by S3 before it; an approval after the scope start is stated, never vouched."""
    ap = rule.get("approval") or {}
    first = rule.get("t1_register") or rule.get("register_version")
    dated = "threshold version %s dated by S3 %s (register %s)" % (rule.get("threshold_version") or "not recorded", rule.get("frozen_at"), first)
    if ap.get("status") != "APPROVED":
        v = "not vouched: no owner approval recorded (%s)" % (ap.get("status") or "MISSING")
    elif run_start is None:
        v = "not vouched: the %s is not recorded, so the approval cannot be placed before it" % label
    elif not _dated_before(rule.get("frozen_at"), run_start):
        v = "not vouched: %s, not proven before the %s %s" % (dated, label, run_start)
    elif not _approved_before(rule, run_start):
        v = ("not vouched: %s, before the %s, but the owner's approval (%s) is after the %s %s"
             % (dated, label, ap.get("at") or "time not recorded", label, run_start))
    else:
        v = "vouched: owner approval %s, before the %s %s; %s" % (ap.get("at"), label, run_start, dated)
    return {"R": ("recomputed by the evaluator: %s" % rc) if rc else "not recomputed (no evaluator entry point)",
            "A": "agreed to MANIFEST.json (%s)" % manifest_status,
            "T": ("corroboration report: %d mismatches" % len(corr.get("mismatches", []))) if isinstance(corr, dict)
                 else "not traced: no corroboration report for this scope in the pack",
            "V": v}


_NONE = re.compile(r"\bNone\b")


def _clean(text):
    """A Python None leaking from a recorded detail string ('position=None', 'received None') reads 'not recorded'.
    The record itself is never changed; only the displayed summary."""
    return _NONE.sub("not recorded", str(text))


def _record_rows(recs, ok, manifest_status, rc_matches):
    rows = []
    in_manifest = ok.get("store/records.jsonl")
    for r in recs[:RECORD_LIMIT]:
        mf = "OK" if in_manifest else ("CHANGED" if in_manifest is False else "MISSING")
        ticks = (["A"] if in_manifest else []) + (["R"] if (r.get("record_kind") == "assessment" and rc_matches) else [])
        rows.append({"ref": "record:%s" % r.get("record_id"), "role": _ROLE.get(r.get("record_kind"), "context"),
                     "surface": str(r.get("emitter") or r.get("record_kind") or ""), "manifest": mf, "tickmarks": ticks,
                     "summary": _clean(r.get("detail") or r.get("record_kind") or ""),
                     "source": "recorded (detail of record:%s)" % r.get("record_id") if r.get("detail") else "recorded (record_kind)"})
    return rows


def _human_loops(recs):
    out = []
    notes = [r for r in recs if r.get("record_kind") == "notification"]
    for f in [r for r in recs if r.get("record_kind") == "finding"]:
        out.append({"finding_id": str(f.get("record_id")), "incident": f.get("incident") or None,
                    "delivery": {"state": "DELIVERED" if notes else "NOT_RECORDED", "at": notes[0].get("ts") if notes and _utc_or(notes[0].get("ts")) else None},
                    "response": {"state": "UNKNOWN", "actor": None, "at": None},
                    "assurance_agent": {"state": "UNKNOWN", "at": None},
                    "closure": {"state": "OPEN"}})
    return out


_BRACKET = re.compile(r"\b(committed|reserved|bound)=(\d+(?:\.\d+)?)")


def _c9_largest(measured):
    """((largest |change_pct|, runtime), n windows) from a stored C9 assessment's measured.windows; (None, 0) when none."""
    wins = [w for w in ((measured or {}).get("windows") or []) if isinstance(w, dict) and _num(w.get("change_pct")) is not None]
    if not wins:
        return None, 0
    top = max(wins, key=lambda w: abs(_num(w["change_pct"])))
    return (round(abs(_num(top["change_pct"])), 4), top.get("runtime")), len(wins)


def _decision_numbers(r):
    """committed / reserved / bound from the decision's own detail bracket (recorded: detail), limit from inline.limit_value,
    and the projected total = committed + reserved + bound (the decision's measured.value is this projection, not spend)."""
    out = {}
    for k, v in _BRACKET.findall(str(r.get("detail") or "")):
        out[k] = _num(v)
    lim = _num(r.get("inline.limit_value"))
    if lim is None:
        lim = _num(r.get("threshold.value"))
    if lim is not None:
        out["limit"] = lim
    if all(out.get(k) is not None for k in ("committed", "bound")):
        out["projected"] = out["committed"] + (out.get("reserved") or 0) + out["bound"]
    if out:
        out["source"] = "recorded (detail bracket, inline.limit_value) on record:%s" % r.get("record_id")
    return out


def _enforcement(control, recs, a):
    # only decisions OF THIS control: a C7 answer never lists C16 inline decisions (PR-40c defect 5)
    dec = [r for r in recs if r.get("record_kind") == "decision" and r.get("inline.mode") and r.get("control.ref") == control]
    modes = set(r["inline.mode"] for r in dec)
    mode = "INLINE_ENFORCE" if "enforce" in modes else "INLINE_OBSERVE" if "observe" in modes else "POST_RUN"
    items = []
    for r in dec:
        d = r.get("verdict")
        if d in V.DECISION_VERDICTS and _utc_or(r.get("ts")):
            item = {"call_id": str(r.get("record_id")), "decision": d, "at": r["ts"], "reason": str(r.get("detail") or "")}
            item.update(_decision_numbers(r))
            items.append(item)
    return {"mode": mode, "tester": {"name": a.get("evaluator_name") or "prooflab.evaluators.%s" % control.lower(),
                                     "version": a.get("threshold_version") or E.UNKNOWN},
            "inline_decisions": items}


def _aict(pack):
    return {"status": "UNKNOWN", "monitor": "UNKNOWN"}


def _txt(text, refs=None, flag=None, source=None):
    d = {"text": text}
    if source:
        d["source"] = source
    if refs:
        d["refs"] = refs
    if flag:
        d["flag"] = flag
    return d


def _inventory_versions(pack):
    """{component_id: (inventory name, approved_version)} from the frozen inventory in the pack (empty when none)."""
    try:
        name, inv = E._inventory(pack)
    except Exception:       # an unreadable inventory is a gap, never a crash
        return {}
    out = {}
    for c in (inv or {}).get("components") or (inv or {}).get("entries") or []:
        if isinstance(c, dict) and c.get("component_id"):
            out[c["component_id"]] = (name, c.get("approved_version"))
    return out


def stored_findings(pack, cid):
    """The staged findings/*.json for one run, joined to the ServiceNow delivery log in the pack (incident + state)."""
    import glob as _glob
    deliv = {}
    try:
        with open(pack.p("servicenow", "delivery-log.jsonl"), "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (IOError, OSError):
        lines = []
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("finding_id"):
            cur = deliv.setdefault(d["finding_id"], {})
            if d.get("number"):
                cur["incident"] = d["number"]
            if d.get("state"):
                cur["state"] = d["state"]
                cur["at"] = d.get("ts")
            if d.get("owner"):
                cur["owner"] = d["owner"]
    out = []
    for path in sorted(_glob.glob(pack.p("findings", "*.json"))):
        f = E.read_json(path)
        if not isinstance(f, dict) or f.get("scope_id") != cid:
            continue
        fid = "ifabric:%s:%s:%s:%s:finding" % (f.get("control_ref"), f.get("threshold_version"), f.get("scope_kind") or "run", cid)
        out.append(dict(f, finding_id=fid, path="findings/" + os.path.basename(path), delivery=deliv.get(fid) or {}))
    return out


def _audit_question(control, a, rule, ctx):
    recs, cid = ctx["recs"], ctx["cid"]
    actors = E._actors(recs)
    stopped = any(r.get("verdict") == "DENY" for r in recs
                  if r.get("record_kind") in ("decision", "platform_decision") and r.get("control.ref") in (None, control))
    told = [r for r in recs if r.get("record_kind") in ("finding", "notification")]
    staged = [f for f in ctx.get("findings") or [] if f.get("control_ref") == control]
    rid = lambda rows: ["record:%s" % r["record_id"] for r in rows[:3] if r.get("record_id")]
    inv = ctx.get("inventory") or {}

    def _agent(x):
        ver = x["version"]
        if not ver and x["actor"] in inv and inv[x["actor"]][1]:
            ver = "%s (inventory %s)" % (inv[x["actor"]][1], inv[x["actor"]][0])
        return "%s on runtime %s, version %s (principal %s)" % (
            x["actor"] or E.UNKNOWN, x["runtime"] or "not recorded", ver or "not recorded",
            x["principal"] or "not recorded in the records")
    agents = "; ".join(_agent(x) for x in actors)
    vr = ctx.get("vrule") or rule
    meas = a.get("measured") or {}
    mval = ctx["mval"] if "mval" in ctx else meas.get("value")
    munit = (ctx.get("munit") if "mval" in ctx else meas.get("unit")) or ""
    mshow = "not recorded" if mval is None else (round(mval, 4) if isinstance(mval, float) else mval)
    lbl = "run start" if ctx["scope_kind"] == "run" else "scope start"
    return {
        "what_was_done": _txt("%s over %s %s: %d records, measured %s %s." % (
            control, ctx["scope_kind"], ctx["scope_label"], len(recs), mshow, munit),
            rid(recs), source="%s; record count from store/records.jsonl" % (ctx.get("msource") or "recorded (measured.value of the stored assessment)")),
        "by_which_agent": _txt(agents or "not recorded (gap: no actor records for this scope)", rid([r for r in recs if r.get("actor.id")]),
                               None if agents else "GAP",
                               source="recorded (actor.id); version joined-from: register inventory (actor.version not recorded)"),
        "where": _txt("by the evaluator named in the assessment; EPs seen: %s" % (", ".join(sorted(set(str(r["ep.id"]) for r in recs if r.get("ep.id")))) or "none recorded"),
                      rid([r for r in recs if r.get("ep.id")]), source="recorded (ep.id)"),
        "when": _txt("%s .. %s (UTC)" % ("not recorded" if not ctx["start"] else ctx["start"], "not recorded" if not ctx["end"] else ctx["end"]),
                     source="recorded (ts of the scope's records)"),
        "under_whose_authority": _txt(_authority_text(vr, ctx["start"], lbl),
                                      [rule["source_ref"]] + ([vr["approval"]["ref"]] if vr["approval"].get("ref") else []),
                                      "OK" if (vr["approval"]["status"] == "APPROVED" and _approved_before(vr, ctx["start"])) else "FLAG",
                                      source="joined-from: register/versions + register/t1 (witnessed-by:S3) + register/approval* (witnessed-by:ServiceNow)"),
        "rule_checked": _txt("%s %s: %s" % (control, rule["threshold_version"], rule["statement"]), [rule["source_ref"]],
                             source="joined-from: register/versions/%s.yaml" % rule["register_version"]),
        "limit_in_force": _txt("%s %s %s per run, version %s, frozen %s (%s the scope)" % (
            rule["observation_limit"]["operator"], rule["observation_limit"]["value"], rule["observation_limit"]["unit"], rule["threshold_version"], rule["frozen_at"],
            "before" if rule["date_before_scope"] else "NOT proven before"), [rule["source_ref"]],
            "OK" if rule["date_before_scope"] else "FLAG", source="joined-from: register/versions + register/t1 (witnessed-by:S3)"),
        "decision": {"text": "control test %s (%s)%s" % (a["verdict"], V.display(a["verdict"]), "; a call was DENIED inline" if stopped else ""),
                     "refs": ["assessment:%s" % a["assessment_id"]] if a.get("assessment_id") else [],
                     # the outcome follows THIS control's assessment: a stop, else a breach escalated to a human, else allowed
                     "source": "recorded (verdict of the stored assessment; DENY decisions recorded by the EP-1 adapter)",
                     "outcome": "STOPPED" if stopped else "ESCALATED" if (a["verdict"] == V.BREACHED and (told or staged)) else "ALLOWED"},
        "who_was_told": _txt("; ".join(["%s %s" % (r["record_kind"], r.get("verdict")) for r in told] + [
            "finding %s %s -> %s %s%s" % (f.get("control_ref"), f.get("verdict"), (f["delivery"].get("incident") or "no incident recorded"),
                                         f["delivery"].get("state") or "not delivered", (" to " + f["delivery"]["owner"]) if f["delivery"].get("owner") else "")
            for f in staged]) or "no finding or notification record for this scope (none needed when the control held)",
                             rid(told) + ["finding:%s" % f["path"] for f in staged][:3],
                             None if (told or staged) else ("GAP" if a.get("verdict") == V.BREACHED else None),
                             source="recorded (finding/notification records); joined-from: servicenow/delivery-log.jsonl"),
        "unchanged_since": _txt("MANIFEST.json status %s" % ctx["manifest_status"], ["manifest:MANIFEST.json"] if ctx["manifest_status"] != "UNVERIFIED" else None,
                                "OK" if ctx["manifest_status"] == "VERIFIED" else "FLAG", source="joined-from: MANIFEST.json"),
    }


# ---------------------------------------------------------------- answer/v1: one run
def compose_run(pack, parse, ans=None, started=None, now=None):
    """The answer document for `controltest N --run RUN`, or a gap doc when the pack cannot supply every required field."""
    control, cid = parse["control"], parse["run"]
    ans = ans or E.control_run(pack, control, cid)
    if ans.get("kind") != "control-run" or "assessment" not in ans:
        return _gap_doc(parse, ans.get("message") or "no assessment", verdict=ans.get("verdict", V.NOT_ASSESSED),
                        control=control, run=cid, assessment_gaps=ans.get("gaps", []))
    a = ans["assessment"]
    gaps = [{"id": "G-%d" % (i + 1), "text": str(g)} for i, g in enumerate(ans["gaps"])]
    rule, entry = _rule(pack, control, a, gaps)
    if rule is None:
        return _gap_doc(parse, "the pack has no register entry (limit, version date) bound to %s %s: the rule cannot be shown" % (
            control, a["threshold_version"]), verdict=ans["verdict"], control=control, run=cid, assessment_gaps=ans["gaps"])
    recs = [r for r in pack.by_cid.get(cid, []) if r.get("record_kind") != "assessment"]
    src, ok = _source(pack, len(pack.records))
    ms = ans["measured"] or {}
    mval = _num(ms.get("value"))
    msource = "recorded (measured.value of the stored assessment)"
    if mval is None and control == "C9":
        # C9 stores one change_pct per runtime window: the judged figure is the largest |change_pct| (never 'unknown' next to a verdict)
        top, n = _c9_largest(a.get("measured"))
        if top is not None:
            mval = top[0]
            ms = dict(ms, unit="%% relative change vs baseline (largest |change_pct|, runtime %s)" % top[1])
            msource = "recorded (measured.windows[].change_pct of the stored assessment; largest of %d)" % n
    lim = _num(ans["limit"])
    op = "<="
    if lim is None:
        lim, op = rule["observation_limit"]["value"], rule["observation_limit"]["operator"]
    within = None if (mval is None or lim is None) else (mval >= lim if op == ">=" else mval <= lim)
    exc = a["exceptions"] or []
    verdict = ans["verdict"]
    reason = "measured %s vs limit %s %s %s%s" % (E.UNKNOWN if mval is None else (round(mval, 2) if isinstance(mval, float) else mval),
                                                 op, E.UNKNOWN if lim is None else lim, ms.get("unit") or "",
                                                 ("; over by %s" % ans["overshoot"]) if ans.get("overshoot") and ans["overshoot"] > 0 else "")
    den = a["denominators"] or {}
    comp = a["completeness"] or {}
    exp = _num(comp.get("expected"))
    cap_n = _num(comp.get("captured"))
    population = {"expected": {"count": int(exp) if exp is not None else 0, "source": "assessment completeness.expected" if exp is not None else "unknown (gap)"},
                  "observed": int(cap_n) if cap_n is not None else 0, "matched": int(cap_n) if cap_n is not None else 0,
                  "missing": (len(comp["missing"]) if isinstance(comp.get("missing"), (list, tuple)) else int(_num(comp.get("missing")) or 0))}
    if isinstance(comp.get("missing"), (list, tuple)) and comp["missing"]:
        population["missing_events"] = [str(k) for k in comp["missing"]]       # C7: which expected events were not captured
    if exp is None:
        gaps.append({"id": "G-POP", "text": "the assessment carries no completeness counts: the population is unknown, zeros shown", "affects": "population"})
    rc = ans.get("recompute") or ""
    rc_match = rc.startswith("matches")
    vrule = _with_dates(pack, control, _bound_rule(pack, control, rule, ans.get("run_start")))
    tick = _tick_text(ok, src["manifest_status"], a, rc, vrule, E.read_json(pack.p("derived", "corroboration", cid + ".json")),
                      run_start=ans.get("run_start"))
    ctx = {"recs": recs, "cid": cid, "scope_kind": "run", "scope_label": parse.get("alias") or cid, "start": ans.get("run_start"),
           "end": E.run_end(pack, cid), "manifest_status": src["manifest_status"], "findings": stored_findings(pack, cid),
           "inventory": _inventory_versions(pack), "vrule": vrule, "mval": mval, "munit": ms.get("unit") or "", "msource": msource}
    scope = {"kind": "run", "id": parse.get("alias") or cid, "cid": cid}
    if parse.get("alias"):
        scope["alias"] = parse["alias"]
    for k, v in (("start", ans.get("run_start")), ("end", ctx["end"])):
        if _utc_or(v):
            scope[k] = v
    doc = {
        "schema": "ifabric.answer/v1", "answer_id": "0" * 64,
        "query": {"text": parse["text"], "normalized": parse["normalized"], "control_ref": control, "scope": scope,
                  "grammar_version": G.GRAMMAR_VERSION},
        "answered_at": now or now_utc(), "elapsed_ms": 0, "source": src,
        "provenance": _provenance(ans["provenance"], ans.get("run_start"), (ans.get("t1") if _utc_or(ans.get("t1")) else rule["frozen_at"])),
        "control": {"ref": control, "id": CONTROL_IDS[control], "name": (entry or {}).get("name") or CONTROL_NAMES[control],
                    "mode": CONTROL_MODES[control]},
        "rule": rule, "scope": scope, "population": population,
        "measurement": {"value": mval, "unit": ms.get("unit") or E.UNKNOWN, "source": msource,
                        "formula": str(a.get("formula") or rule["measurement_basis"])},
        "comparison": {"limit": lim, "operator": op, "delta": (mval - lim) if (mval is not None and lim is not None) else None,
                       "within_limit": within, "exceptions_count": len(exc), "exceptions_allowed": rule["exception_tolerance"]["value"],
                       "exceptions_unit": rule["exception_tolerance"]["unit"]},
        "exceptions": [x if isinstance(x, dict) else {"note": str(x)} for x in exc],
        "verdict": {"value": verdict, "label": V.display(verdict), "reason": reason,
                    "evidence_sufficiency": a.get("evidence_sufficiency") if a.get("evidence_sufficiency") in ("COMPLETE", "PARTIAL", "UNKNOWN") else "UNKNOWN"},
        "enforcement": _enforcement(control, recs, a),
        "audit_question": _audit_question(control, a, rule, ctx),
        "human_loops": _human_loops(recs), "aict": _aict(pack),
        "records": _record_rows(recs + ([{"record_id": a["record_id"], "record_kind": "assessment", "detail": "stored assessment"}] if a.get("record_id") else []),
                                ok, src["manifest_status"], rc_match),
        "gaps": gaps, "tickmarks": tick,
    }
    if len(recs) > RECORD_LIMIT:
        doc["gaps"].append({"id": "G-REC", "text": "%d records for this run; the first %d are listed" % (len(recs), RECORD_LIMIT)})
    if rc.startswith(("MISMATCH", "FAILED")):
        doc["gaps"].append({"id": "G-RC", "text": "recompute: %s" % rc, "affects": "verdict"})
    doc["answer_id"] = answer_id_of(doc)
    return doc


# ---------------------------------------------------------------- answer/v1: one window
def compose_window(pack, parse, ans=None, now=None):
    control = parse["control"]
    win = "%s..%s" % (parse["t1"], parse["t2"])
    ans = ans or E.control_window(pack, control, win)
    if ans.get("kind") != "control-window" or not ans["counted"]:
        return _gap_doc(parse, (ans.get("message") or "; ".join(ans.get("gaps", [])) or "no run in scope"),
                        verdict=ans.get("verdict", V.NOT_ASSESSED), control=control, window=[parse["t1"], parse["t2"]],
                        listed=ans.get("listed", []), assessment_gaps=ans.get("gaps", []))
    counted = ans["counted"]
    first = counted[0]
    gaps = [{"id": "G-%d" % (i + 1), "text": str(g)} for i, g in enumerate(ans["gaps"])]
    rule, entry = _rule(pack, control, first, gaps)
    if rule is None:
        return _gap_doc(parse, "the pack has no register entry bound to %s %s: the rule cannot be shown" % (control, first["threshold_version"]),
                        verdict=ans["verdict"], control=control, window=[parse["t1"], parse["t2"]], assessment_gaps=ans["gaps"])
    src, ok = _source(pack, len(pack.records))
    breached = [a for a in counted if a["verdict"] == V.BREACHED]
    pv = ans["per_version"]
    allowed = rule["exception_tolerance"]["value"]
    if len(pv) > 1:
        gaps.append({"id": "G-VER", "text": "the window spans %d register versions (%s); the rule shown is the first" % (
            len(pv), ", ".join(p["threshold_version"] for p in pv)), "affects": "rule"})
    for r in ans["listed"]:
        gaps.append({"id": "G-L%d" % (len(gaps) + 1), "text": "listed, not counted: %s (%s)" % (r["scope"], r["reason"]), "affects": "population"})
    scope = {"kind": "interval", "id": win, "start": parse["t1"], "end": parse["t2"]}
    series = []
    for a in counted:
        m = a.get("measured") or {}
        sval = _num(m.get("value"))
        if sval is None and control == "C9":
            top, _n = _c9_largest(m)
            sval = top[0] if top else None
        series.append({"id": str(a["scope_id"]), "value": sval, "limit": _num(a["limit"]),
                       "violates": a["verdict"] == V.BREACHED if a["verdict"] in (V.BREACHED, V.SATISFIED) else None,
                       "status": "VIOLATES" if a["verdict"] == V.BREACHED else "OK" if a["verdict"] == V.SATISFIED else "UNKNOWN",
                       "ref": "assessment:%s" % a["assessment_id"] if a.get("assessment_id") else "run:%s" % a["scope_id"]})
    vrule = _with_dates(pack, control, _bound_rule(pack, control, rule, parse["t1"]))
    top_s = max([x for x in series if x["value"] is not None], key=lambda x: abs(x["value"]), default=None)
    ctx = {"recs": [], "cid": win, "scope_kind": "window", "scope_label": win, "start": parse["t1"], "end": parse["t2"],
           "manifest_status": src["manifest_status"], "vrule": vrule, "mval": len(breached),
           "munit": "breached runs of %d counted%s" % (len(counted), ("; largest per-run value %s (run %s)" % (top_s["value"], top_s["id"])) if top_s else ""),
           "msource": "recorded (verdict and measured value of each counted run's stored assessment)"}
    verdict = ans["verdict"]
    reason = "%d of %d counted runs breached; tolerance %s per register version" % (len(breached), len(counted), E.UNKNOWN if allowed is None else allowed)
    recs = []
    for a in counted:
        recs += [r for r in pack.by_cid.get(a["scope_id"], []) if r.get("record_kind") == "finding"]
    doc = {
        "schema": "ifabric.answer/v1", "answer_id": "0" * 64,
        "query": {"text": parse["text"], "normalized": parse["normalized"], "control_ref": control, "scope": scope,
                  "grammar_version": G.GRAMMAR_VERSION},
        "answered_at": now or now_utc(), "elapsed_ms": 0, "source": src,
        "provenance": _provenance(E.run_provenance(pack, first["scope_id"]) if first["scope_kind"] == "run" else E.WINDOW_PROVENANCE[0],
                                  first.get("scope_start"), rule["frozen_at"]),
        "control": {"ref": control, "id": CONTROL_IDS[control], "name": (entry or {}).get("name") or CONTROL_NAMES[control],
                    "mode": CONTROL_MODES[control]},
        "rule": rule, "scope": scope,
        "population": {"expected": {"count": len(counted) + len(ans["listed"]), "source": "assessments and run index inside the window (E-06)"},
                       "observed": len(counted) + len(ans["listed"]), "matched": len(counted), "missing": 0, "unmatched": len(ans["listed"])},
        "measurement": {"value": len(breached), "unit": "breached runs",
                        "formula": "count of counted runs whose stored verdict is BREACHED (window rule E-06)", "series": series},
        "comparison": {"limit": allowed, "operator": "<=", "delta": len(breached) - allowed,
                       "within_limit": len(breached) <= allowed, "exceptions_count": len(breached), "exceptions_allowed": allowed,
                       "exceptions_unit": "breached runs"},
        "exceptions": [{"id": str(a["scope_id"]), "ref": "run:%s" % a["scope_id"], "value": _num((a.get("measured") or {}).get("value")),
                        "why": "stored verdict %s" % a["verdict"]} for a in breached],
        "verdict": {"value": verdict, "label": V.display(verdict), "reason": reason,
                    "evidence_sufficiency": "PARTIAL" if ans["listed"] or ans["gaps"] else "COMPLETE"},
        "enforcement": {"mode": "POST_RUN", "tester": {"name": "prooflab.query.engine.control_window", "version": G.GRAMMAR_VERSION}},
        "audit_question": _audit_question(control, first, rule, ctx),
        "human_loops": _human_loops(recs), "aict": _aict(pack),
        "records": [{"ref": "assessment:%s" % a["assessment_id"], "role": "measurement", "manifest": "OK" if ok.get("store/records.jsonl") else "MISSING",
                     "tickmarks": []} for a in counted[:RECORD_LIMIT] if a.get("assessment_id")],
        "gaps": gaps,
        "tickmarks": _tick_text(ok, src["manifest_status"], first, "", vrule, run_start=parse["t1"], label="scope start"),
    }
    doc["answer_id"] = answer_id_of(doc)
    return doc


# ---------------------------------------------------------------- auditor/v1
_QMAP = (("who", ("WHO acted", "WHO owns it")), ("what", ("WHAT it touched",)), ("authorized", ("AUTHORIZED",)),
         ("approved", ("APPROVED",)), ("integrity", ("INTEGRITY",)), ("reconstruct", ("RECONSTRUCT",)))


_QSOURCE = {"WHO acted": "recorded (actor.id); version joined-from: register inventory",
            "WHO owns it": "joined-from: register inventory + register owner; recorded (control.owner)",
            "WHAT it touched": "recorded (model.id, tool.name)",
            "AUTHORIZED": "recorded (platform_decision records)",
            "APPROVED": "joined-from: register/approval* (witnessed-by:ServiceNow); recorded (detail of ep0.declared_treatment)",
            "INTEGRITY": "joined-from: MANIFEST.json, derived/corroboration/",
            "RECONSTRUCT": "recorded (ts, record_kind, ep.id, record_id)"}


def compose_auditor(pack, parse, now=None, only=None):
    inc = E.incident(pack, parse.get("incident") or parse.get("run"))
    if inc["kind"] == "error" or inc.get("out_of_scope") or not inc.get("questions"):
        return _gap_doc(parse, inc.get("message") or inc.get("out_of_scope") or "no questions for this scope", verdict=V.NOT_ASSESSED)
    start, end = _utc_or(inc["start"]), _utc_or(inc["end"] or inc["start"])
    if not start or not end:
        return _gap_doc(parse, "run %s has no recorded start and end time in the pack" % inc["run"], verdict=V.NOT_ASSESSED)
    byq = dict((q["q"], q) for q in inc["questions"])
    questions = {}
    for key, names in _QMAP:
        parts = [byq[n] for n in names if n in byq]
        facts, refs, gaps = [], [], []
        for q in parts:
            for line in q["lines"]:
                facts.append({"label": q["q"], "value": _clean(line), "refs": ["record:%s" % r for r in q["records"][:3]], "flag": "OK",
                              "source": "not-recorded" if q.get("gap") else _QSOURCE.get(q["q"], "recorded")})
            refs += ["record:%s" % r for r in q["records"]]
            if q.get("gap"):
                gaps.append(q["gap"])
        has = any(not q.get("gap") for q in parts)
        status = "GAP" if not has else ("PARTIAL" if gaps else "ANSWERED")
        questions[key] = {"status": status, "answer": "; ".join(f["value"] for f in facts[:2]) or "unknown (gap)",
                          "facts": facts, "refs": sorted(set(refs)), "gaps": gaps}
        if parts:
            questions[key]["facts"].append({"label": "stated limit", "value": " / ".join(q["limit"] for q in parts)})
    prov = _provenance(inc["provenance"], inc["start"], inc["start"])
    doc = {"schema": "ifabric.auditor/v1", "auditor_id": "auditor:%s" % inc["run"], "title": "six questions for %s" % inc["run"],
           "scope": {"kind": "run", "id": inc["run"], "cid": inc["run"]}, "window": {"start": start, "end": end},
           "generated_at": now or now_utc(), "provenance": prov, "questions": questions}
    if parse.get("incident") and parse["incident"] != inc["run"]:
        doc["scope"]["incident"] = parse["incident"]
    return doc


# ---------------------------------------------------------------- the entry point
def ask(pack, text, now=None):
    """Parse the question and compose the answer; never raises on a bad question."""
    t0 = time.time()
    parse = G.parse(text, pack)
    if not parse["ok"]:
        return {"ok": False, "kind": "unparsed", "doc": {"kind": "unparsed", "message": parse["error"], "examples": parse["examples"],
                                                         "candidates": parse["candidates"]}, "exit": 2, "parse": parse}
    kind = parse["kind"]
    if kind == "controltest-run":
        doc = compose_run(pack, parse, now=now)
    elif kind == "controltest-window":
        doc = compose_window(pack, parse, now=now)
    elif kind in ("auditor", "who"):
        doc = compose_auditor(pack, parse, now=now)
        if kind == "who" and doc.get("schema") == "ifabric.auditor/v1":
            doc = dict(doc, focus="who")
    elif kind == "trail":
        inc = E.incident(pack, parse["run"])
        doc = {"kind": "trail", "run": parse["run"], "verdict": inc.get("verdict", V.NOT_ASSESSED), "incident": inc,
               "message": inc.get("message")}
    else:       # told
        cid = parse["run"]
        if not E.run_known(pack, cid):
            doc = _gap_doc(parse, "unknown run %s: not in this pack" % cid)
        else:
            recs = [r for r in pack.by_cid.get(cid, []) if r.get("record_kind") != "assessment"]
            doc = {"kind": "told", "run": cid, "verdict": "RECORDED", "rows": E._human_loop(pack, cid, recs)}
    out_kind = ("answer" if doc.get("schema") == "ifabric.answer/v1" else "auditor" if doc.get("schema") == "ifabric.auditor/v1"
                else doc.get("kind", "gap"))
    if doc.get("schema") == "ifabric.answer/v1":
        doc["elapsed_ms"] = int((time.time() - t0) * 1000)
        code = V.exit_code(doc["verdict"]["value"])
    elif out_kind == "gap":
        code = 2
    else:
        code = E.exit_for(doc) if out_kind == "trail" else 0
    return {"ok": out_kind != "gap", "kind": out_kind, "doc": doc, "exit": code, "parse": parse}


def verb_main(argv):
    """`prooflab query ask|controltest|auditor|trail ...` (the CLI verbs; the query CLI dispatches here)."""
    from prooflab.query import render_text as R
    args = list(argv)
    pack_dir, as_json, rest = ".", False, []
    i = 0
    while i < len(args):
        if args[i] == "--pack" and i + 1 < len(args):
            pack_dir = args[i + 1]
            i += 2
            continue
        if args[i] == "--json":
            as_json = True
        else:
            rest.append(args[i])
        i += 1
    if not rest:
        print("usage: query ask \"<question>\" | controltest <N> --run RUN | auditor <INC|RUN> | trail <RUN>", file=sys.stderr)
        return 2
    verb = rest[0].lower()
    text = rest[1] if verb == "ask" and len(rest) == 2 else " ".join(rest[1:] if verb == "ask" else rest)
    res = ask(E.Pack(pack_dir), text)
    if as_json:
        print(json.dumps(res["doc"], indent=1, sort_keys=True, default=str))
    else:
        print("\n".join(R.render(res)))
    return res["exit"]

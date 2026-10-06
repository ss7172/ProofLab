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
    proof = E.date_proof(pack, a["threshold_version"], control, a.get("scope_start"))
    before = proof["state"] == "PROVEN_BEFORE"      # the boolean of schema v1, kept: True only when PROVEN
    if proof["state"] == "NOT_PROVEN":
        gaps.append({"id": "G-T1", "text": "rule date NOT PROVEN against the scope: %s; the register's own frozen_at %s is "
                     "a claim, not a proof" % (proof["reason"], _utc_or(vdate) or E.UNKNOWN), "affects": "rule.date_proof"})
    elif proof["state"] == "PROVEN_AFTER":
        gaps.append({"id": "G-T1", "text": "rule DATED AFTER the test: %s" % proof["reason"], "affects": "rule.date_proof"})
    date_proof = {"state": proof["state"], "t1_at": proof["t1_at"], "version_id": proof["version_id"], "key": proof["key"],
                  "register_file": proof["register_file"], "checksum_verified": proof["checksum_verified"],
                  "register_frozen_at": _utc_or(vdate), "reason": proof["reason"]}
    owner = entry.get("owner") or top.get("register_owner")
    rule = {"register_version": str(rname), "threshold_version": a["threshold_version"],
            "version_date": vdate[:10] if re.match(r"^\d{4}-\d\d-\d\d", vdate) else "1970-01-01",
            "frozen_at": frozen, "owner": _person(owner), "approval": approval, "date_before_scope": before,
            "date_proof": date_proof,
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


def _tick_text(ok, manifest_status, a, rc, rule, corr=None):
    return {"R": ("recomputed by the evaluator: %s" % rc) if rc else "not recomputed (no evaluator entry point)",
            "A": "agreed to MANIFEST.json (%s)" % manifest_status,
            "T": ("corroboration report: %d mismatches" % len(corr.get("mismatches", []))) if isinstance(corr, dict)
                 else "not traced: no corroboration report for this scope in the pack",
            "V": _vouch_text(rule)}


def date_words(rule):
    """(words, flag) for the rule's date proof; 'DATED AFTER' only when a T1 proof in the pack shows it (PROVEN_AFTER)."""
    dp = rule.get("date_proof") or {}
    state = dp.get("state") or ("PROVEN_BEFORE" if rule.get("date_before_scope") else "NOT_PROVEN")
    if state == "PROVEN_BEFORE":
        return ("dated before the scope (S3 T1 %s%s)" % (dp.get("t1_at") or rule.get("frozen_at"),
                                                          (", version " + dp["version_id"]) if dp.get("version_id") else ""), "OK")
    if state == "PROVEN_AFTER":
        return ("RULE DATED AFTER TEST (S3 T1 %s is later than the scope start)" % dp.get("t1_at"), "FLAG")
    return ("date proof not in this pack (register says frozen %s, unproven)" % (dp.get("register_frozen_at") or rule.get("frozen_at")),
            "GAP")


def _vouch_text(rule):
    words, _ = date_words(rule)
    approved = rule["approval"]["status"] == "APPROVED"
    if approved and rule["date_before_scope"]:
        return "vouched: owner approval, register %s" % words
    return "not vouched: %s; register %s" % ("owner approval on record" if approved else "no owner approval record in the pack", words)


def _record_rows(recs, ok, manifest_status, rc_matches):
    rows = []
    in_manifest = ok.get("store/records.jsonl")
    for r in recs[:RECORD_LIMIT]:
        mf = "OK" if in_manifest else ("CHANGED" if in_manifest is False else "MISSING")
        ticks = (["A"] if in_manifest else []) + (["R"] if (r.get("record_kind") == "assessment" and rc_matches) else [])
        rows.append({"ref": "record:%s" % r.get("record_id"), "role": _ROLE.get(r.get("record_kind"), "context"),
                     "surface": str(r.get("emitter") or r.get("record_kind") or ""), "manifest": mf, "tickmarks": ticks,
                     "summary": str(r.get("detail") or r.get("record_kind") or "")})
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


def _enforcement(control, recs, a):
    # only decisions OF THIS control: a C7 answer never lists C16 inline decisions (PR-40c defect 5)
    dec = [r for r in recs if r.get("record_kind") == "decision" and r.get("inline.mode") and r.get("control.ref") == control]
    modes = set(r["inline.mode"] for r in dec)
    mode = "INLINE_ENFORCE" if "enforce" in modes else "INLINE_OBSERVE" if "observe" in modes else "POST_RUN"
    items = []
    for r in dec:
        d = r.get("verdict")
        if d in V.DECISION_VERDICTS and _utc_or(r.get("ts")):
            items.append({"call_id": str(r.get("record_id")), "decision": d, "at": r["ts"],
                          "reason": str(r.get("detail") or "")})
    return {"mode": mode, "tester": {"name": a.get("evaluator_name") or "prooflab.evaluators.%s" % control.lower(),
                                     "version": a.get("threshold_version") or E.UNKNOWN},
            "inline_decisions": items}


def _aict(pack):
    return {"status": "UNKNOWN", "monitor": "UNKNOWN"}


def _txt(text, refs=None, flag=None):
    d = {"text": text}
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
                  if r.get("record_kind") in ("decision", "platform_decision") and r.get("control.ref") == control
                  and str(r.get("inline.mode") or "enforce") == "enforce" and str(r.get("ep.id") or "") != "EP-2")
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
    meas = a.get("measured") or {}
    return {
        "what_was_done": _txt("%s over %s %s: %d records, measured %s %s." % (
            control, ctx["scope_kind"], ctx["scope_label"], len(recs), E.UNKNOWN if meas.get("value") is None else meas["value"], meas.get("unit") or ""),
            rid(recs)),
        "by_which_agent": _txt(agents or "unknown (gap: no actor records for this scope)", rid([r for r in recs if r.get("actor.id")]),
                               None if agents else "GAP"),
        "where": _txt("by the evaluator named in the assessment; EPs seen: %s" % (", ".join(sorted(set(str(r["ep.id"]) for r in recs if r.get("ep.id")))) or "none recorded"),
                      rid([r for r in recs if r.get("ep.id")])),
        "when": _txt("%s .. %s (UTC)" % (E.UNKNOWN if not ctx["start"] else ctx["start"], E.UNKNOWN if not ctx["end"] else ctx["end"])),
        "under_whose_authority": _txt("register owner %s; approval %s" % (rule["owner"]["name"], rule["approval"]["status"]),
                                      [rule["source_ref"]], "OK" if rule["approval"]["status"] == "APPROVED" else "FLAG"),
        "rule_checked": _txt("%s %s: %s" % (control, rule["threshold_version"], rule["statement"]), [rule["source_ref"]]),
        "limit_in_force": _txt("%s %s %s per run, version %s, %s" % (
            rule["observation_limit"]["operator"], rule["observation_limit"]["value"], rule["observation_limit"]["unit"], rule["threshold_version"],
            date_words(rule)[0]), [rule["source_ref"]], date_words(rule)[1]),
        "decision": {"text": "control test %s (%s)%s" % (a["verdict"], V.display(a["verdict"]), "; a call was DENIED inline" if stopped else ""),
                     "refs": ["assessment:%s" % a["assessment_id"]] if a.get("assessment_id") else [],
                     # the outcome follows THIS control's assessment: a stop, else a breach escalated to a human, else allowed
                     "outcome": "STOPPED" if stopped else "ESCALATED" if (a["verdict"] == V.BREACHED and (told or staged)) else "ALLOWED"},
        "who_was_told": _txt("; ".join(["%s %s" % (r["record_kind"], r.get("verdict")) for r in told] + [
            "finding %s %s -> %s %s%s" % (f.get("control_ref"), f.get("verdict"), (f["delivery"].get("incident") or "no incident recorded"),
                                         f["delivery"].get("state") or "not delivered", (" to " + f["delivery"]["owner"]) if f["delivery"].get("owner") else "")
            for f in staged]) or "no finding or notification record for this scope (none needed when the control held)",
                             rid(told) + ["finding:%s" % f["path"] for f in staged][:3],
                             None if (told or staged) else ("GAP" if a.get("verdict") == V.BREACHED else None)),
        "unchanged_since": _txt("MANIFEST.json status %s" % ctx["manifest_status"], ["manifest:MANIFEST.json"] if ctx["manifest_status"] != "UNVERIFIED" else None,
                                "OK" if ctx["manifest_status"] == "VERIFIED" else "FLAG"),
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
    tick = _tick_text(ok, src["manifest_status"], a, rc, rule, E.read_json(pack.p("derived", "corroboration", cid + ".json")))
    ctx = {"recs": recs, "cid": cid, "scope_kind": "run", "scope_label": parse.get("alias") or cid, "start": ans.get("run_start"),
           "end": E.run_end(pack, cid), "manifest_status": src["manifest_status"], "findings": stored_findings(pack, cid),
           "inventory": _inventory_versions(pack)}
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
        "measurement": {"value": mval, "unit": ms.get("unit") or E.UNKNOWN,
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
        series.append({"id": str(a["scope_id"]), "value": _num(m.get("value")), "limit": _num(a["limit"]),
                       "violates": a["verdict"] == V.BREACHED if a["verdict"] in (V.BREACHED, V.SATISFIED) else None,
                       "status": "VIOLATES" if a["verdict"] == V.BREACHED else "OK" if a["verdict"] == V.SATISFIED else "UNKNOWN",
                       "ref": "assessment:%s" % a["assessment_id"] if a.get("assessment_id") else "run:%s" % a["scope_id"]})
    ctx = {"recs": [], "cid": win, "scope_kind": "window", "scope_label": win, "start": parse["t1"], "end": parse["t2"],
           "manifest_status": src["manifest_status"]}
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
        "tickmarks": _tick_text(ok, src["manifest_status"], first, "", rule),
    }
    doc["answer_id"] = answer_id_of(doc)
    return doc


# ---------------------------------------------------------------- auditor/v1
_QMAP = (("who", ("WHO acted", "WHO owns it")), ("what", ("WHAT it touched",)), ("authorized", ("AUTHORIZED",)),
         ("approved", ("APPROVED",)), ("integrity", ("INTEGRITY",)), ("reconstruct", ("RECONSTRUCT",)))


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
                facts.append({"label": q["q"], "value": line, "refs": ["record:%s" % r for r in q["records"][:3]], "flag": "OK"})
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

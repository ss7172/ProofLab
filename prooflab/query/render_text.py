"""One screen of text for an answer document (the CLI's view of `ifabric.answer/v1`, `ifabric.auditor/v1`, gaps).
Stdlib only, Python 3.9. No verdict logic: it prints what the document says."""
from __future__ import annotations

import json

from prooflab.contract import verdicts as V


def _flag(f):
    return {"OK": "[ok]", "FLAG": "[flag]", "GAP": "[gap]"}.get(f, "")


def _ref_line(refs):
    return ("  refs: " + ", ".join(refs[:4]) + (" (+%d more)" % (len(refs) - 4) if len(refs) > 4 else "")) if refs else ""


def render_answer(d):
    r, v, c, m = d["rule"], d["verdict"], d["comparison"], d["measurement"]
    lines = [
        "ANSWER %s" % d["answer_id"][:16],
        "Q: %s   [%s]" % (d["query"]["text"], d["query"]["normalized"]),
        "CONTROL %s (%s) %s  scope %s %s  provenance %s" % (d["control"]["ref"], d["control"]["id"], d["control"]["name"],
                                                         d["scope"]["kind"], d["scope"]["id"], d["provenance"]),
        "rule: %s v%s dated %s, frozen %s (%s), owner %s, approval %s" % (
            r["register_version"], r["threshold_version"], r["version_date"], r["frozen_at"],
            "before the scope" if r["date_before_scope"] else "NOT proven before the scope", r["owner"]["name"], r["approval"]["status"]),
        "limit: %s %s %s; tolerance %s %s" % (r["observation_limit"]["operator"], r["observation_limit"]["value"],
                                              r["observation_limit"]["unit"], r["exception_tolerance"]["value"], r["exception_tolerance"]["unit"]),
        "population: expected %s, observed %s, matched %s, missing %s" % (
            d["population"]["expected"]["count"], d["population"]["observed"], d["population"]["matched"], d["population"]["missing"]),
        "measured: %s %s  vs limit %s  delta %s  within limit %s" % (m["value"], m["unit"], c["limit"], c.get("delta"), c["within_limit"]),
        "exceptions: %d (allowed %s)" % (c["exceptions_count"], c["exceptions_allowed"]),
        "VERDICT: %s (%s)  %s  evidence %s" % (v["value"], v["label"], v["reason"], v["evidence_sufficiency"]),
        "enforcement: %s by %s %s" % (d["enforcement"]["mode"], d["enforcement"]["tester"]["name"], d["enforcement"]["tester"]["version"]),
    ]
    for key, q in d["audit_question"].items():
        lines.append("  %-20s %s %s" % (key, q["text"], _flag(q.get("flag"))))
    for h in d["human_loops"]:
        lines.append("human loop: %s delivery %s, response %s, closure %s" % (
            h["finding_id"], h["delivery"]["state"], h["response"]["state"], h["closure"]["state"]))
    lines.append("AICT: %s, monitor %s" % (d["aict"]["status"], d["aict"].get("monitor", "UNKNOWN")))
    lines.append("records: %d listed; manifest %s (%s)" % (len(d["records"]), d["source"]["manifest_status"], d["source"]["manifest_sha256"][:12]))
    lines.append("tickmarks: " + " | ".join("%s %s" % (k, d["tickmarks"][k]) for k in ("R", "A", "T", "V")))
    lines += ["gap %s: %s" % (g["id"], g["text"]) for g in d["gaps"]]
    return lines


def render_auditor(d):
    lines = ["AUDITOR %s  %s .. %s  provenance %s" % (d["auditor_id"], d["window"]["start"], d["window"]["end"], d["provenance"])]
    keys = ("who",) if d.get("focus") == "who" else ("who", "what", "authorized", "approved", "integrity", "reconstruct")
    for i, k in enumerate(("who", "what", "authorized", "approved", "integrity", "reconstruct"), 1):
        if k not in keys:
            continue
        q = d["questions"][k]
        lines.append("%d. %s  [%s]" % (i, k.upper(), q["status"]))
        lines += ["   - %s: %s" % (f["label"], f["value"]) for f in q["facts"]]
        if q["gaps"]:
            lines += ["   gap: %s" % g for g in q["gaps"]]
        if _ref_line(q["refs"]):
            lines.append("  " + _ref_line(q["refs"]))
    return lines


def render(res):
    d, kind = res["doc"], res["kind"]
    if kind == "answer":
        return render_answer(d)
    if kind == "auditor":
        return render_auditor(d)
    if kind == "unparsed":
        lines = [d["message"]]
        if d.get("candidates"):
            lines += ["candidates:"] + ["  " + c for c in d["candidates"]]
        lines += ["examples:"] + ["  " + e for e in d["examples"]]
        return lines
    if kind == "trail":
        inc = d["incident"]
        if inc.get("kind") == "error":
            return [inc["message"]]
        recon = [q for q in inc.get("questions", []) if q["q"] == "RECONSTRUCT"]
        return ["TRAIL %s  %s .. %s  provenance %s" % (d["run"], inc["start"], inc["end"], inc["provenance"])] + (
            ["  " + x for x in recon[0]["lines"]] if recon else [inc.get("out_of_scope") or "no trail in the pack"])
    if kind == "told":
        return ["WHO WAS TOLD for %s" % d["run"]] + (["  %s %s [%s] %s" % (h["kind"], h["verdict"], h["record_id"], h.get("detail") or "")
                                                     for h in d["rows"]] or ["  no finding or notification record for this run (gap)"])
    lines = ["%s: %s" % (V.display(d.get("verdict", V.NOT_ASSESSED)), d.get("message"))]
    lines += ["gap: %s" % g for g in d.get("assessment_gaps", [])]
    lines += ["listed, not counted: %s (%s)" % (x["scope"], x["reason"]) for x in d.get("listed", [])]
    return lines


def render_json(res):
    return json.dumps(res["doc"], indent=1, sort_keys=True, default=str)

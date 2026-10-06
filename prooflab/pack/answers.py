"""Compose the console's stored answers from a staged pack, with the same engine the CLI uses (prooflab.query.answer.ask).

The console only locates stored answer documents; it composes none (no verdict logic in the console). `pack build` runs
this on the staged tree so a judge who unzips the pack finds answers/<key>.json and the pack-index answers[] entries.

  compose(root) -> (entries, skipped)   per-run answers for C16 and C7, then one window answer per control over window.json
  compose_auditor(root) -> (entries, skipped)  auditor/<cid>.json (the six questions) for every assessed run   writes <root>/answers/<C>_run_<id>.json for every run-scoped assessment
                                         whose answer composes (kind 'answer'); a question that yields a gap document
                                         is listed in `skipped` with its message, never written as an answer.
Stdlib, Python 3.9. Idempotent for a given tree except the answered_at/elapsed_ms stamps.
"""
import glob
import json
import os
import re

CONTROLS = ("C16", "C7")


def _num(ref):
    return ref[1:]


def compose(root):
    from prooflab.query import engine as E, answer as A
    entries, skipped = [], []
    if not os.path.isdir(os.path.join(root, "assessments")):
        return entries, skipped
    pack = E.Pack(root)
    seen = set()
    for ctl in CONTROLS:
        for path in sorted(glob.glob(os.path.join(root, "assessments", ctl, "*.json"))):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (IOError, OSError, ValueError):
                continue
            a = E.normalize_assessment(doc)
            if a["scope_kind"] != "run" or (ctl, a["scope_id"]) in seen:
                continue
            seen.add((ctl, a["scope_id"]))
            q = "control %s for run %s" % (_num(ctl), a["scope_id"])
            res = A.ask(pack, q)
            if res["kind"] != "answer":
                skipped.append({"query": q, "reason": res["doc"].get("message")})
                continue
            d = res["doc"]
            sc = d.get("scope") or {}
            key = "%s|%s|%s" % (ctl, sc.get("kind", "run"), sc.get("alias") or sc.get("id"))
            fname = re.sub(r"[^A-Za-z0-9_.-]", "_", key) + ".json"
            os.makedirs(os.path.join(root, "answers"), exist_ok=True)
            with open(os.path.join(root, "answers", fname), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(d, fh, indent=1, sort_keys=True, ensure_ascii=False)
                fh.write("\n")
            entries.append({"key": key, "control_ref": ctl, "scope": sc.get("alias") or sc.get("id"),
                            "verdict": d["verdict"]["value"], "answer_id": d["answer_id"]})
    _windows(root, pack, entries, skipped)
    return entries, skipped


def _write_doc(root, sub, fname, doc):
    os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, sub, fname), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def _windows(root, pack, entries, skipped):
    """One window answer per control over the declared window (window.json), from the same ask() as the CLI."""
    from prooflab.query import answer as A
    try:
        with open(os.path.join(root, "window.json"), "r", encoding="utf-8") as fh:
            w = json.load(fh)
    except (IOError, OSError, ValueError):
        return
    w = w.get("event_window") if isinstance(w.get("event_window"), dict) else w
    if not (w.get("start") and w.get("end")):
        return
    for ctl in CONTROLS:
        if not glob.glob(os.path.join(root, "assessments", ctl, "*.json")):
            continue
        q = "control %s between %s and %s" % (_num(ctl), w["start"], w["end"])
        res = A.ask(pack, q)
        if res["kind"] != "answer":
            skipped.append({"query": q, "reason": res["doc"].get("message")})
            continue
        d = res["doc"]
        sc = d.get("scope") or {}
        key = "%s|%s|%s" % (ctl, sc.get("kind", "interval"), sc.get("id"))
        _write_doc(root, "answers", re.sub(r"[^A-Za-z0-9_.-]", "_", key) + ".json", d)
        entries.append({"key": key, "control_ref": ctl, "scope": sc.get("id"), "verdict": d["verdict"]["value"],
                        "answer_id": d["answer_id"]})


def compose_auditor(root):
    """auditor/<cid>.json (the six questions, the same engine as `query --incident`) for every assessed run.

    Returns (entries for pack-index auditor[], skipped)."""
    from prooflab.query import engine as E, answer as A
    entries, skipped, cids = [], [], []
    for path in sorted(glob.glob(os.path.join(root, "assessments", "*", "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                a = E.normalize_assessment(json.load(fh))
        except (IOError, OSError, ValueError):
            continue
        if a["scope_kind"] == "run" and a["scope_id"] not in cids:
            cids.append(a["scope_id"])
    if not cids:
        return entries, skipped
    pack = E.Pack(root)
    for cid in cids:
        res = A.ask(pack, "auditor %s" % cid)
        if res["kind"] != "auditor":
            skipped.append({"query": "auditor %s" % cid, "reason": res["doc"].get("message")})
            continue
        d = res["doc"]
        fname = re.sub(r"[^A-Za-z0-9_.-]", "_", cid) + ".json"
        _write_doc(root, "auditor", fname, d)
        statuses = dict((k, q.get("status")) for k, q in (d.get("questions") or {}).items())
        entries.append({"id": cid, "title": d.get("title"), "path": "auditor/" + fname, "auditor_id": d.get("auditor_id"),
                        "questions": statuses})
    return entries, skipped

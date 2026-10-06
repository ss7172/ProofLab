"""Compose the console's stored answers from a staged pack, with the same engine the CLI uses (prooflab.query.answer.ask).

The console only locates stored answer documents; it composes none (no verdict logic in the console). `pack build` runs
this on the staged tree so a judge who unzips the pack finds answers/<key>.json and the pack-index answers[] entries.

  compose(root) -> (entries, skipped)   writes <root>/answers/<C>_run_<id>.json for every run-scoped assessment
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
    return entries, skipped

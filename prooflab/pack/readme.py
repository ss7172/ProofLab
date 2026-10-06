"""Fill the pack README's `<...>` placeholders from the STAGED pack (pack build, after the console projection).

  fill(root) -> {"filled": [...], "not_available": [...], "absent_files": [...]}

Every value comes from a file in the pack (window.json, the frozen register, pack-index.json, servicenow/, the
auditor views, pack-root.json when present); a placeholder the pack cannot fill becomes an explicit
"not yet available in this pack" text, never a guess. Files the README names that the pack does not hold are marked
"(not in this pack)". The reader's own command arguments (<CID>, <T1>, <T2>, <CID-or-time>) stay. The template note
is removed once nothing is left unfilled. Stdlib, Python 3.9.
"""
import datetime
import glob
import json
import os
import re

KEEP = ("<CID>", "<T1>", "<T2>", "<CID-or-time>", "<port>")
NA = "not yet available in this pack"
PH_RE = re.compile(r"`?<([A-Za-z_.][^<>`]{1,600}?)>`?", re.S)
FILE_RE = re.compile(r"`([a-z0-9][a-z0-9-]*(?:\.md|\.json|\.jsonl|/))`")
_NOTE_RE = re.compile(r"^> \*\*Template\.\*\*.*?Delete this note when filled\.\n\n?", re.S | re.M)


def _json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (IOError, OSError, ValueError):
        return None


def _register(root):
    """(top, {control_ref: entry}) of the newest frozen register in the pack (register/versions/v*.yaml)."""
    try:
        from prooflab.registry import parse as P
    except Exception:
        return {}, {}
    paths = [p for p in glob.glob(os.path.join(root, "register", "versions", "*.yaml"))
             if not os.path.basename(p).startswith("inv-") and ".risks." not in os.path.basename(p)]
    paths += [os.path.join(root, "register", "register.yaml")]
    best = None
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as fh:
                doc = P.parse_register(fh.read())
        except (IOError, OSError, ValueError):
            continue
        key = str(doc["top"].get("version_date") or "")
        if best is None or key > best[0]:
            best = (key, doc)
    if not best:
        return {}, {}
    doc = best[1]
    return doc["top"], dict((e.get("control_ref"), e) for e in doc.get("entries") or [] if e.get("control_ref"))


def _delivery(root):
    rows = []
    try:
        with open(os.path.join(root, "servicenow", "delivery-log.jsonl"), "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except (IOError, OSError):
        pass
    return rows


def values(root):
    """{placeholder text (without <>): value} computed from the staged pack."""
    v = {}
    w = _json(os.path.join(root, "window.json")) or {}
    w = w.get("event_window") if isinstance(w.get("event_window"), dict) else w
    if w.get("start") and w.get("end"):
        v["WINDOW_START"], v["WINDOW_END"] = w["start"], w["end"]
    top, ctl = _register(root)
    ret = str(top.get("retention") or "")
    m = re.search(r"kept for (.+?) from", ret, re.I)
    if ret:
        v["RETENTION_RULE"] = m.group(1) if m else ret
    v["YYYY-MM-DD"] = datetime.datetime.utcnow().strftime("%Y-%m-%d") + " (the pack build date; section 7 holds the upload time)"
    if top.get("owner") or top.get("owner_name"):
        v["owner name and contact"] = ("%s, %s" % (top.get("owner_name") or "", top.get("owner") or "")).strip(", ")
    if top.get("builder"):
        v["builder"] = str(top["builder"])
    root_doc = _json(os.path.join(root, "pack-root.json")) or {}
    if root_doc.get("incident") or root_doc.get("number"):
        v["INCnnnnnnn"] = str(root_doc.get("incident") or root_doc.get("number"))
    if root_doc.get("journal_time") or root_doc.get("note_journal_time"):
        v["NOTE_JOURNAL_TIME_UTC"] = str(root_doc.get("journal_time") or root_doc.get("note_journal_time"))
    if root_doc.get("label"):
        v["submit-1 / submit-2 / final"] = str(root_doc["label"])
    c7 = ctl.get("C7") or {}
    if c7:
        v["expected-event source, reconciliation and gap rule, from the register"] = (
            "expected events: %s. Rule: %s. Limits (register %s, %s): %s." % (
                c7.get("measurement_basis") or NA, c7.get("calculation") or NA, top.get("version") or "?",
                c7.get("threshold_version") or "?", c7.get("observation_limit") or NA))
    c9 = ctl.get("C9") or {}
    if c9:
        assessed9 = bool(glob.glob(os.path.join(root, "assessments", "C9", "*.json")))
        v["baseline, closed UTC windows, relative change, crossings; a missing window is a monitoring gap"] = (
            "%s; limit: %s. %s" % (c9.get("measurement_basis") or NA, c9.get("observation_limit") or NA,
                                   "Assessments are in assessments/C9/." if assessed9 else
                                   "C9 is not assessed in this pack (no assessments/C9/): a stated gap."))
    idx = _json(os.path.join(root, "pack-index.json")) or {}
    per = []
    for ref in ("C16", "C7", "C9"):
        n = len(glob.glob(os.path.join(root, "assessments", ref, "*.json")))
        vs = [a.get("verdict") for a in idx.get("answers") or [] if a.get("control_ref") == ref and "|run|" in str(a.get("key"))]
        tally = ", ".join("%d %s" % (vs.count(x), x) for x in sorted(set(vs)))
        per.append("%s %s" % (ref, ("assessed over %d run(s)%s" % (n, (" (" + tally + ")") if tally else "")) if n else "not assessed yet"))
    v["per control: assessed / not assessed yet"] = "; ".join(per)
    aud = idx.get("auditor") or []
    if aud:
        qs = {}
        for a in aud:
            for k, st in (a.get("questions") or {}).items():
                qs.setdefault(k, set()).add(st)
        v["per question: FULL / PARTIAL, and what arrives later"] = "; ".join(
            "%s %s" % (k.upper(), "FULL" if s == {"ANSWERED"} else "PARTIAL (%s)" % ", ".join(sorted(s))) for k, s in sorted(qs.items())) + \
            " (over %d stored auditor view(s) in auditor/)" % len(aud)
    deliv = _delivery(root)
    incs = sorted(set(d.get("number") for d in deliv if d.get("number")))
    if deliv:
        states = sorted(set(d.get("state") for d in deliv if d.get("state")))
        v["Filled from servicenow/ at submit."] = ("From servicenow/delivery-log.jsonl: %d finding(s) delivered as incident(s) %s; "
                                                   "states recorded: %s." % (len(set(d.get("finding_id") for d in deliv if d.get("finding_id"))),
                                                                              ", ".join(incs) or "none", ", ".join(states)))
    answers = idx.get("answers") or []
    runs_c = sorted(set(a.get("control_ref") for a in answers if "|run|" in str(a.get("key"))))
    win_c = sorted(set(a.get("control_ref") for a in answers if "|interval|" in str(a.get("key"))))
    v["CONSOLE_STORED"] = ("%d stored answers (per run: %s; over the declared window: %s) and %d six-questions view(s)" % (
        len(answers), ", ".join(runs_c) or "none", ", ".join(win_c) or "none", len(aud)))
    return v


def fill(root):
    path = os.path.join(root, "README.md")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except (IOError, OSError):
        return {"filled": [], "not_available": [], "absent_files": []}
    vals = values(root)
    filled, missing = [], []

    def sub(m):
        whole, key = m.group(0), m.group(1)
        if "<%s>" % key in KEEP:
            return whole
        code = whole.startswith("`") and whole.endswith("`")
        if key == "update before each submit":
            return "*update before submission*"
        if key in vals:
            filled.append(key)
            val = vals[key]
            return "`%s`" % val if code and len(val) < 60 and "\n" not in val else val
        missing.append(key.split(";")[0].split("\n")[0][:60])
        return "*(%s: %s)*" % (NA, re.sub(r"\s+", " ", key)[:160])
    text = _NOTE_RE.sub("", text)        # the template note goes: every placeholder below is filled or stated unavailable
    if not os.path.isdir(os.path.join(root, "adversarial")):
        # the default honest-failure paragraph describes adversarial results; without adversarial/ it would claim them
        text = re.sub(r"(## 6\. The honest failure\n\n)(.*?)(\n## 7\.)", lambda m: m.group(1) + (
            "No adversarial results are in this pack (`adversarial/` is absent), so none is claimed here. The failures "
            "this pack does show are the runs whose stored verdict is BREACHED (`assessments/`, `findings/`) and the "
            "open items in `gap-list.md`. If a result in this pack differs from this paragraph, the pack wins.\n") + m.group(3),
            text, flags=re.S)
    text = PH_RE.sub(sub, text)

    absent = []

    def mark(m):
        name = m.group(1)
        if os.path.exists(os.path.join(root, name.rstrip("/"))):
            return m.group(0)
        absent.append(name)
        return m.group(0) + " (not in this pack)"
    text = FILE_RE.sub(mark, text)
    lines = []
    for line in text.split("\n"):       # the layout block: a line naming an absent top-level file says so
        mm = re.match(r"^([a-z0-9][a-z0-9-]*(?:\.md|\.json|\.jsonl|/))\s{2,}", line)
        if mm and not os.path.exists(os.path.join(root, mm.group(1).rstrip("/"))) and "(not in this pack)" not in line:
            line += "   (not in this pack)"
            absent.append(mm.group(1))
        lines.append(line)
    text = "\n".join(lines)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return {"filled": filled, "not_available": missing, "absent_files": sorted(set(absent))}

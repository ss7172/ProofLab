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

from prooflab.contract import verdicts as _V  # the one verdict vocabulary

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
    """(top, {control_ref: entry}) of the CURRENT register: the head of the frozen chain (prooflab.pack.history),
    else register/register.yaml."""
    try:
        from prooflab.pack import history as _h
        hist = _h.register_history(root)
        doc = hist["docs"].get(hist["head"]) if hist["head"] else None
        if doc is None:
            from prooflab.registry import parse as P
            with open(os.path.join(root, "register", "register.yaml"), "r", encoding="utf-8") as fh:
                doc = P.parse_register(fh.read())
    except Exception:
        return {}, {}
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


def _root_incident(root):
    """The incident the MANIFEST root note goes on (runbook 13e: register/approval/t2-sys-id.txt), by its number."""
    try:
        with open(os.path.join(root, "register", "approval", "t2-sys-id.txt"), "r", encoding="utf-8") as fh:
            sys_id = fh.read().strip()
    except (IOError, OSError):
        sys_id = None
    from prooflab.pack import history as _h
    if sys_id:
        for r in _h._delivery_rows(root):
            if r.get("sys_id") == sys_id and r.get("number"):
                return r["number"]
    return None


def values(root, label=None):
    """{placeholder text (without <>): value} computed from the staged pack."""
    v = {}
    idx = _json(os.path.join(root, "pack-index.json")) or {}
    w = _json(os.path.join(root, "window.json")) or {}
    w = w.get("event_window") if isinstance(w.get("event_window"), dict) else w
    from prooflab.pack import history as _h
    nmd_win = _h.named_runs_md(root)["window"]
    if w.get("start") and w.get("end"):
        v["WINDOW_START"], v["WINDOW_END"] = w["start"], w["end"]
    elif nmd_win:      # the window named-runs.md declares; pack-index pack.event_window carries the same one
        v["WINDOW_START"], v["WINDOW_END"] = nmd_win["start"], nmd_win["end"]
    else:      # no declared window file: the first and last named (assessed) run, said so
        named = [r for r in idx.get("runs") or [] if r.get("provenance") == "ASSESSED" and r.get("started_at")]
        if named:
            v["WINDOW_START"] = "%s (the first named run's start; no window.json in this pack)" % min(r["started_at"] for r in named)
            v["WINDOW_END"] = "%s (the last named run's end)" % max(r.get("ended_at") or r["started_at"] for r in named)
    top, ctl = _register(root)
    ret = str(top.get("retention") or "")
    m = re.search(r"kept for (.+?) from", ret, re.I)
    if ret:
        v["RETENTION_RULE"] = m.group(1) if m else ret
    v["YYYY-MM-DD"] = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    if top.get("owner") or top.get("owner_name"):
        v["owner name and contact"] = ("%s, %s" % (top.get("owner_name") or "", top.get("owner") or "")).strip(", ")
    if top.get("builder"):
        v["builder"] = str(top["builder"])
    root_doc = _json(os.path.join(root, "pack-root.json")) or {}
    if root_doc.get("incident") or root_doc.get("number"):
        v["INCnnnnnnn"] = str(root_doc.get("incident") or root_doc.get("number"))
    else:
        inc = _root_incident(root)
        if inc:
            v["INCnnnnnnn"] = inc
    if root_doc.get("journal_time") or root_doc.get("note_journal_time"):
        v["NOTE_JOURNAL_TIME_UTC"] = str(root_doc.get("journal_time") or root_doc.get("note_journal_time"))
    v["C16_CORE_SHA"] = c16_core_sha(root)
    if label or root_doc.get("label"):
        v["submit-1 / submit-2 / final"] = str(label or root_doc["label"])
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
    per, assessed = [], []
    for ref in ("C16", "C7", "C9"):
        n = len(glob.glob(os.path.join(root, "assessments", ref, "*.json")))
        vs = [a.get("verdict") for a in idx.get("answers") or [] if a.get("control_ref") == ref and "|run|" in str(a.get("key"))]
        tally = ", ".join("%d %s" % (vs.count(x), x) for x in sorted(set(vs)))
        nw = n - len(vs)  # files that are not per-run answers: hourly windows
        per.append("%s %s" % (ref, ("assessed over %d run(s)%s%s" % (len(vs), (" (" + tally + ")") if tally else "",
                                     ("; plus %d hourly window(s)" % nw) if nw > 0 else "")) if n else "not assessed yet"))
        if n:
            assessed.append(ref)
    v["per control: assessed / not assessed yet"] = "; ".join(per)
    missing = [r for r in ("C16", "C7", "C9") if r not in assessed]
    judged = any(str(g.get("id")) in ("1", "B1", "gap-1") and str(g.get("status") or "").upper() in ("CLOSED", "DONE")
                 for g in idx.get("gaps") or [])
    v["FULL / PARTIAL"] = ("FULL: C16, C7 and C9 are each assessed in this pack (assessments/)" if not missing else
                           "PARTIAL: not assessed in this pack: %s" % ", ".join(missing)) + (
        "; the judgment records' deciding evidence is in store/ (gap 1 closed in gap-list.md)" if judged else
        "; gap 1 in gap-list.md states what is still open for the judgment pillar")
    aud = idx.get("auditor") or []
    if aud:
        qs = {}
        for a in aud:
            full = _auditor_full(root, a)
            for k, st in (a.get("questions") or {}).items():
                qs.setdefault(k, []).append(st == "ANSWERED" and full.get(k, True))
        v["per question: FULL / PARTIAL, and what arrives later"] = "; ".join(
            "%s %s" % (k.upper(), "FULL" if all(s) else "PARTIAL (%d/%d views answered without a gap)" % (sum(s), len(s)))
            for k, s in sorted(qs.items())) + " (over %d stored auditor view(s) in auditor/)" % len(aud)
    deliv = _h._delivery_rows(root)
    cutoffs = sorted(set(d.get("cutoff") for d in deliv if isinstance(d.get("cutoff"), str) and d.get("cutoff")))
    if cutoffs:
        v["CUTOFF_UTC"] = "%s (the latest cutoff in the delivery logs)" % cutoffs[-1]
    incs = sorted(set(d.get("number") for d in deliv if d.get("number")))
    if deliv:
        states = sorted(set(d.get("state") for d in deliv if d.get("state")))
        appr = _h.approvals(root)
        a_txt = "; ".join("register %s approval %s%s" % (ver, a["status"], (" on %s" % a["incident"]) if a.get("incident") else "")
                          for ver, a in sorted(appr.items()))
        v["Filled from servicenow/ at submit."] = servicenow_text(root, idx, appr, deliv, states)
    answers = idx.get("answers") or []
    runs_c = sorted(set(a.get("control_ref") for a in answers if "|run|" in str(a.get("key"))))
    win_c = sorted(set(a.get("control_ref") for a in answers if "|interval|" in str(a.get("key"))))
    v["CONSOLE_STORED"] = ("%d stored answers (per run: %s; over the declared window: %s) and %d six-questions view(s)" % (
        len(answers), ", ".join(runs_c) or "none", ", ".join(win_c) or "none", len(aud)))
    return v


_GAP_RE = re.compile(r"\bgap\b|\bmissing\b|\bunknown\b", re.I)


def _auditor_full(root, a):
    """{question: True when the stored auditor view's answer states no gap}; the grade the README gives a question
    is FULL only when every view answers it without a gap, missing or unknown part."""
    out = {}
    ref = str(a.get("path") or a.get("ref") or "")
    doc = None
    for cand in (ref, os.path.join("auditor", "%s.json" % (a.get("cid") or a.get("scope_id") or ""))):
        if cand and os.path.isfile(os.path.join(root, cand)):
            doc = _json(os.path.join(root, cand))
            break
    for k, q in ((doc or {}).get("questions") or {}).items():
        if isinstance(q, dict):
            out[k] = not _GAP_RE.search(str(q.get("answer") or ""))
    return out


def _hm(ts):
    m = re.search(r"T(\d\d:\d\d:\d\d)", str(ts or ""))
    return (m.group(1) + "Z") if m else "?"


def _short_note(note):
    """The reason a NOT COUNTED attempt is not counted, as named-runs.md words it (INFRA-FAILED, halted ...)."""
    n = str(note or "")
    for key in ("INFRA-FAILED", "INFRA FAILED"):
        if key in n.upper():
            return "INFRA-FAILED"
    m = re.search(r"(halted by [^(.;,|]*)", n, re.I)
    return m.group(1).strip().replace("HALTED", "halted") if m else ""


def servicenow_text(root, idx, appr, deliv, states):
    """README section 8: each register approval with its incident and time stated against the named runs (an
    approval after a run is said to be after it), then the control findings delivered, apart from approval requests."""
    runs = sorted((r.get("started_at"), r.get("cid")) for r in idx.get("runs") or []
                  if r.get("provenance") == "ASSESSED" and r.get("started_at"))
    nmd = {}
    nc = {}
    try:
        from prooflab.pack import history as _h
        for r in _h.named_runs_md(root)["rows"]:
            m = re.match(r"(N\d+[a-z]?)\b", r.get("note") or "") or re.search(r"\blabel (N\d+[a-z]?)\b", r.get("note") or "")
            if m and r.get("cid"):
                nmd.setdefault(r["cid"], m.group(1))
            if r.get("not_counted") and r.get("cid") and r.get("start"):
                nc.setdefault(r["cid"], r)
    except Exception:
        pass
    for r in idx.get("runs") or []:
        if "NOT COUNTED" in str(r.get("provenance") or "").upper() and r.get("cid") and r.get("started_at"):
            nc.setdefault(r["cid"], {"cid": r["cid"], "start": r["started_at"], "note": r.get("reason") or r.get("note") or ""})
    counted = set(c for _, c in runs)
    nc = dict((c, r) for c, r in nc.items() if c not in counted)
    reg_hist = {}
    try:
        reg_hist = dict((x.get("version"), x) for x in (idx.get("register") or {}).get("versions") or [])
    except Exception:
        pass
    parts = []
    for ver, a in sorted(appr.items()):
        at = a.get("at")
        txt = "register %s approval %s on %s at %s" % (ver, a.get("status"), a.get("incident") or "?", _hm(at))
        rv = reg_hist.get(ver) or {}
        if rv.get("frozen_at"):
            txt += " (frozen %s)" % _hm(rv["frozen_at"])
        if at and runs:
            before = [nmd.get(c) or c for s, c in runs if s < at]
            nc_before = sorted((r["start"], c, r) for c, r in nc.items() if str(r.get("start")) < at
                               and (not r.get("register") or str(r.get("register")) == str(ver)))
            if not before:
                txt += ", before every counted named run" if nc_before else ", before every named run"
            else:
                txt += ", AFTER named run(s) %s, which ran under it frozen but not yet approved" % ", ".join(before)
            if nc_before:
                txt += "; AFTER the NOT COUNTED attempt(s) %s, which ran under it frozen but not yet approved" % ", ".join(
                    "%s (%s%s%s)" % (c, (nmd[c] + ", ") if nmd.get(c) else "", _hm(st),
                                     (", " + _short_note(r.get("note"))) if _short_note(r.get("note")) else "")
                    for st, c, r in nc_before)
        resp = a.get("responded") or {}
        if resp.get("at") and resp.get("at") != at:
            txt += "; the incident was last updated %s (a later note on it, not the approval of record)" % _hm(resp["at"])
        parts.append(txt)
    reqs = set(str(a.get("finding_id")) for a in appr.values() if a.get("finding_id"))
    ctl = []
    for f in idx.get("findings") or []:
        if f.get("verdict") == _V.BREACHED and f.get("incident"):
            cl = f.get("closure") or {}
            ctl.append("%s on %s %s%s" % (f["incident"], f.get("control_ref"), nmd.get(f.get("scope_id")) or f.get("scope_id"),
                                          (", finding closed by re-test %s at %s (the incident stays open for the owner)" % (
                                              nmd.get(cl.get("retest_cid")) or cl.get("retest_cid"), _hm(cl.get("at"))))
                                          if cl.get("state") == "CLOSED_BY_RETEST" else ""))
    req_inc = sorted(set(a.get("incident") for a in appr.values() if a.get("incident")))
    return ("Register approvals (register/approval*/, servicenow/export/): %s. Control findings delivered as incidents "
            "(servicenow/delivery-log.jsonl): %d, %s. Register-approval requests (not findings): %s. Delivery states "
            "recorded: %s." % ("; ".join(parts) or "none", len(ctl), "; ".join(ctl) or "none",
                               ", ".join(req_inc) or "none", ", ".join(states)))


def c16_core_sha(root):
    """The sha256 of prooflab.evaluators.c16_core recorded at EP-1 and at EP-2 in the staged records."""
    seen = {}
    for base in ("store", "records"):
        for dp, _, fns in os.walk(os.path.join(root, base)):
            for fn in fns:
                if not (fn.endswith(".jsonl") or fn.endswith(".json")):
                    continue
                try:
                    with open(os.path.join(dp, fn), "r", encoding="utf-8") as fh:
                        for line in fh:
                            if "c16_core" not in line:
                                continue
                            try:
                                r = json.loads(line)
                            except ValueError:
                                continue
                            if isinstance(r, dict) and r.get("evaluator.name") == "prooflab.evaluators.c16_core" and r.get("evaluator.sha256"):
                                seen.setdefault(str(r.get("ep.id")), set()).add(r["evaluator.sha256"])
                except (IOError, OSError):
                    continue
    if not seen:
        return "The C16 core's sha256 is not recorded in this pack's records (a stated gap)."
    eps = ", ".join("%s: `%s`" % (ep, "`, `".join(sorted(s))) for ep, s in sorted(seen.items()))
    same = len(set().union(*seen.values())) == 1 and {"EP-1", "EP-2"} <= set(seen)
    return ("The C16 core's sha256 as recorded in the records (evaluator.sha256): %s; %s. The adapter-diff PR sha "
            "and its diff --stat are not in this pack." % (eps, "the same hash at EP-1 and EP-2" if same else
                                                           "NOT one hash at both points (see the records)"))


def _has_observed_adversarial(root):
    """True only when adversarial/ holds an observed result (log.jsonl with a row): pre-registered cases alone claim nothing."""
    try:
        with open(os.path.join(root, "adversarial", "log.jsonl"), "r", encoding="utf-8") as fh:
            return any(line.strip() for line in fh)
    except (IOError, OSError):
        return False


def _has_breach(root):
    for p in glob.glob(os.path.join(root, "assessments", "*", "*.json")):
        d = _json(p) or {}
        if (d.get("requirement_verdict") or d.get("verdict")) == _V.BREACHED:
            return True
    return False


def fill(root, label=None):
    path = os.path.join(root, "README.md")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except (IOError, OSError):
        return {"filled": [], "not_available": [], "absent_files": []}
    vals = values(root, label=label)
    filled, missing = [], []

    def sub(m):
        whole, key = m.group(0), m.group(1)
        if "<%s>" % key in KEEP:
            return whole
        code = whole.startswith("`") and whole.endswith("`")
        if key == "update before each submit":
            return "*update before submission*"
        if key not in vals and key.split(";")[0].strip() in vals:     # `<FULL / PARTIAL; if J2 ...>`: matched on the prefix
            key = key.split(";")[0].strip()
        if key in vals:
            filled.append(key)
            val = vals[key]
            return "`%s`" % val if code and len(val) < 60 and "\n" not in val else val
        missing.append(key.split(";")[0].split("\n")[0][:60])
        return "*(%s: %s)*" % (NA, re.sub(r"\s+", " ", key)[:160])
    text = _NOTE_RE.sub("", text)        # the template note goes: every placeholder below is filled or stated unavailable
    if not _has_observed_adversarial(root):
        # the default honest-failure paragraph describes adversarial results; with no observed result it would claim them
        text = re.sub(r"(## 6\. The honest failure\n\n)(.*?)(\n## 7\.)", lambda m: m.group(1) + (
            "No observed adversarial result is in this pack (`adversarial/` holds at most the pre-registered cases, with no "
            "log of runs), so none is claimed here. The failures "
            "this pack does show are the runs whose stored verdict is BREACHED (`assessments/`, `findings/`) and the "
            "open items in `gap-list.md`. If a result in this pack differs from this paragraph, the pack wins.\n") + m.group(3),
            text, flags=re.S)
    text = PH_RE.sub(sub, text)

    absent = []

    breach = _has_breach(root)

    def why_absent(name):
        if name == "pack-root.json":
            return "uploaded after the pack as a sidecar; not in this pack by design"
        if name == "findings/" and not breach:
            return "none in this pack: no assessment is BREACHED, so there is no finding"
        return "not in this pack"

    def mark(m):
        name = m.group(1)
        if os.path.exists(os.path.join(root, name.rstrip("/"))):
            return m.group(0)
        why = why_absent(name)
        if why == "not in this pack":
            absent.append(name)
        return m.group(0) + " (%s)" % why
    text = FILE_RE.sub(mark, text)
    lines = []
    for line in text.split("\n"):       # the layout block: a line naming an absent top-level file says so
        mm = re.match(r"^([a-z0-9][a-z0-9-]*(?:\.md|\.json|\.jsonl|/))\s{2,}", line)
        if mm and not os.path.exists(os.path.join(root, mm.group(1).rstrip("/"))) and "(not in this pack" not in line \
                and "by design)" not in line and "no finding)" not in line:
            line += "   (%s)" % why_absent(mm.group(1))
            if why_absent(mm.group(1)) == "not in this pack":
                absent.append(mm.group(1))
        lines.append(line)
    text = "\n".join(lines)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return {"filled": filled, "not_available": missing, "absent_files": sorted(set(absent))}

"""Readers over a pack source tree for what the pack must show WHOLE: the register history (the frozen chain),
the register approvals (T2: approval Finding + delivery log + ServiceNow export), and every run in the window.

  register_history(src) -> {"head": name|None, "versions": [row...], "docs": {name: parsed doc}}
  approvals(src)        -> {register version: approval dict (schema: status APPROVED|PENDING|MISSING, ref, ...)}
  run_catalogue(src, run_ids, window=None, store_records=None) -> [run row...]

Order is never a text sort: versions are ordered by the `supersedes` chain and `frozen_at` (v1.1 sorts before v1
as text). Every value comes from a file in the tree; nothing is invented. Read-only; stdlib; Python 3.9.
"""
from __future__ import annotations

import datetime
import glob
import hashlib
import json
import os
import re

UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$")
_SN_TS = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)$")
_NOTE_HDR = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) - (.+?) \((Work notes|Additional comments)\)$", re.M)


def _read_bytes(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except (IOError, OSError):
        return None


def _read_json(path):
    data = _read_bytes(path)
    if data is None:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _read_jsonl(path):
    rows = []
    for line in (_read_bytes(path) or b"").decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def utc(v):
    """A UTC Z string, or None. Accepts `YYYY-MM-DD HH:MM:SS` (ServiceNow API times are UTC) and `+00:00`."""
    if not isinstance(v, str):
        return None
    v = v.strip()
    if UTC_RE.match(v):
        return v
    m = _SN_TS.match(v)
    if m:
        return "%sT%sZ" % (m.group(1), m.group(2))
    if v.endswith("+00:00") and UTC_RE.match(v[:-6] + "Z"):
        return v[:-6] + "Z"
    return None


def _parse_register(text):
    from prooflab.registry import parse as P
    return P.parse_register(text)


# ------------------------------------------------------------------ T1 date proofs
def t1_heads(src):
    """{file basename: {"key", "version_id", "last_modified", "path"}} from the T1 records the tree holds:
    register/t1/*.json and t1/*.json (lists of {file, key, head_object}) and register[/versions]/<v>.head.json."""
    out = {}
    paths = sorted(glob.glob(os.path.join(src, "register", "t1", "*.json")) + glob.glob(os.path.join(src, "t1", "*.json")))
    for p in paths:
        doc = _read_json(p)
        for row in doc if isinstance(doc, list) else []:
            if not isinstance(row, dict) or not row.get("file"):
                continue
            head = row.get("head_object") if isinstance(row.get("head_object"), dict) else {}
            put = row.get("put_object") if isinstance(row.get("put_object"), dict) else {}
            out[os.path.basename(row["file"])] = {
                "key": row.get("key"), "version_id": head.get("VersionId") or put.get("VersionId"),
                "last_modified": utc(head.get("LastModified")), "path": os.path.relpath(p, src)}
    for p in sorted(glob.glob(os.path.join(src, "register", "*.head.json"))
                    + glob.glob(os.path.join(src, "register", "versions", "*.head.json"))):
        doc = _read_json(p) or {}
        name = os.path.basename(p)[:-len(".head.json")] + ".yaml"
        if name not in out and isinstance(doc, dict):
            out[name] = {"key": doc.get("Key") or doc.get("key"), "version_id": doc.get("VersionId") or doc.get("version_id"),
                         "last_modified": utc(doc.get("LastModified") or doc.get("last_modified") or doc.get("t1")),
                         "path": os.path.relpath(p, src)}
    return out


def _post_hoc(src, version):
    doc = _read_json(os.path.join(src, "register", "experiments", "rules-%s.json" % version))
    ph = doc.get("post_hoc") if isinstance(doc, dict) else None
    if not isinstance(ph, dict) or not ph.get("declared"):
        return None
    bits = ["DECLARED POST-HOC change"]
    if ph.get("control"):
        bits.append("control %s" % ph["control"])
    if ph.get("rule_replaced") and ph.get("rule_new"):
        bits.append("rule %s replaced by %s" % (ph["rule_replaced"], ph["rule_new"]))
    if ph.get("decided_by"):
        bits.append("decided by %s%s" % (ph["decided_by"], (" at about " + ph["decided_at_utc_approx"]) if ph.get("decided_at_utc_approx") else ""))
    text = "; ".join(bits) + "."
    for k in ("why", "evidence_after_the_fact", "scope", "frozen_v1_stays_on_record"):
        if ph.get(k):
            text += " %s: %s." % (k.replace("_", " "), str(ph[k]).rstrip("."))
    return text


# ------------------------------------------------------------------ the register chain
def register_history(src):
    vdir = os.path.join(src, "register", "versions")
    docs, rows = {}, {}
    heads = t1_heads(src)
    for path in sorted(glob.glob(os.path.join(vdir, "*.yaml"))):
        base = os.path.basename(path)
        if base.endswith(".risks.yaml") or base.startswith("inv-"):
            continue
        data = _read_bytes(path)
        try:
            doc = _parse_register(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, AttributeError):
            continue
        top = doc.get("top") or {}
        name = str(top.get("version") or base[:-5])
        docs[name] = dict(doc, path=os.path.relpath(path, src), sha256=hashlib.sha256(data).hexdigest())
        sup = str(top.get("supersedes") or "").strip()
        row = {"version": name, "path": os.path.relpath(path, src), "sha256": docs[name]["sha256"],
               "status": top.get("status") or "UNKNOWN",
               "frozen_at": utc(top.get("frozen_at")) or utc(top.get("version_date")),
               "version_date": top.get("version_date"),
               "supersedes": sup if sup and sup.lower() != "none" else None}
        risks = os.path.join(vdir, base[:-5] + ".risks.yaml")
        if os.path.isfile(risks):
            row["risks_sha256"] = hashlib.sha256(_read_bytes(risks) or b"").hexdigest()
        t1 = heads.get(base)
        if t1:
            row["t1"] = {k: v for k, v in t1.items() if v}
        ph = _post_hoc(src, name)
        if ph:
            row["post_hoc"] = ph
        rows[name] = row
    succ = {}
    for name, row in rows.items():
        if row["supersedes"]:
            succ.setdefault(row["supersedes"], []).append(name)
    for name, row in rows.items():
        row["superseded_by"] = sorted(succ.get(name) or []) or None

    def depth(name, seen=()):
        sup = rows[name]["supersedes"]
        return 0 if (not sup or sup not in rows or sup in seen) else 1 + depth(sup, seen + (name,))

    tips = [n for n in rows if not succ.get(n)]
    head = None
    if tips:
        head = max(tips, key=lambda n: (rows[n]["status"] == "FROZEN", rows[n]["frozen_at"] or "", depth(n), n))
    chain = []
    cur = head
    while cur in rows and cur not in chain:
        chain.append(cur)
        cur = rows[cur]["supersedes"]
    chain.reverse()
    rest = sorted((n for n in rows if n not in chain), key=lambda n: (rows[n]["frozen_at"] or "", depth(n), n))
    order = rest + chain        # history oldest first; the head is last
    out = []
    for n in order:
        r = rows[n]
        r["current"] = n == head
        r["in_chain"] = n in chain
        out.append(r)
    out.sort(key=lambda r: (r["frozen_at"] or "", r["in_chain"], depth(r["version"]), r["version"]))
    if head and out and out[-1]["version"] != head:     # the head is always shown last (newest)
        out = [r for r in out if r["version"] != head] + [rows[head]]
    return {"head": head, "versions": out, "docs": docs}


def entry_for(history, control_ref, threshold_version=None, register_version=None, register_sha256=None):
    """(version name, entry) for an assessment: the version it names (cross-checked by sha256), else the newest version
    carrying that threshold_version, else (None, None). Never the head by default when the versions differ."""
    docs, order = history["docs"], [r["version"] for r in history["versions"]][::-1]
    cands = []
    if register_version in docs:
        cands.append(register_version)
    if register_sha256:
        cands += [n for n in order if docs[n]["sha256"] == register_sha256 and n not in cands]
    cands += [n for n in order if n not in cands]
    for name in cands:
        for e in docs[name].get("entries") or []:
            if e.get("control_ref") == control_ref and threshold_version in (None, e.get("threshold_version")):
                return name, e
    return None, None


# ------------------------------------------------------------------ approvals (T2)
def _delivery_rows(src):
    seen, rows = set(), []
    paths = sorted(glob.glob(os.path.join(src, "register", "approval*", "delivery-log.jsonl")))
    paths += [os.path.join(src, "servicenow", "delivery-log.jsonl"), os.path.join(src, "servicenow", "approval-delivery-log.jsonl")]
    for p in paths:
        for r in _read_jsonl(p):
            k = json.dumps(r, sort_keys=True)
            if k not in seen:
                seen.add(k)
                rows.append(r)
    return rows


def _exports(src):
    out = {}
    for p in sorted(glob.glob(os.path.join(src, "servicenow", "export", "*.json")) + glob.glob(os.path.join(src, "servicenow", "cases", "*.json"))):
        d = _read_json(p)
        if not isinstance(d, dict):
            continue
        inc = d.get("incident") if isinstance(d.get("incident"), dict) else {}
        num = inc.get("number") or (d.get("incident") if isinstance(d.get("incident"), str) else None) or d.get("number")
        if num and num not in out:
            out[num] = {"path": os.path.relpath(p, src), "doc": d, "incident": inc}
    return out


def _notes(exp):
    """[(utc time or None, author, text)] from an export's work notes and comments. The display times are in the
    instance's zone: converted to UTC with the offset of the integration's own creation note (its opened_at)."""
    d, inc = exp["doc"], exp["incident"]
    nd = d.get("notes_display") if isinstance(d.get("notes_display"), dict) else {}
    blob = "\n".join(str(nd.get(k) or "") for k in ("work_notes", "comments"))
    parts = _NOTE_HDR.split(blob)
    notes = []
    for i in range(1, len(parts) - 3, 4):
        notes.append((parts[i], parts[i + 1], parts[i + 3].strip()))
    offset = None
    opened = utc(inc.get("opened_at") or inc.get("sys_created_on"))
    if opened and notes:
        oldest = sorted(notes, key=lambda n: n[0])[0]
        try:
            a = datetime.datetime.strptime(opened, "%Y-%m-%dT%H:%M:%SZ")
            b = datetime.datetime.strptime(oldest[0], "%Y-%m-%d %H:%M:%S")
            secs = (a - b).total_seconds()
            if abs(secs) <= 14 * 3600 and abs(secs) % 900 < 5:
                offset = datetime.timedelta(seconds=round(secs / 900) * 900)
        except ValueError:
            offset = None
    out = []
    for t, who, text in notes:
        when = None
        if offset is not None:
            when = (datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S") + offset).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append((when, who, text))
    return out


def _version_of_finding(doc, dirname):
    v = doc.get("threshold_version")
    if not v and str(doc.get("scope_id") or "").startswith("register-"):
        v = doc["scope_id"][len("register-"):]
    return v or (dirname.split("approval-", 1)[1] if "approval-" in dirname else None)


def approvals(src):
    """{register version: approval} from register/approval*/ (Finding + canonical note), the delivery logs and the
    ServiceNow exports. APPROVED: the owner's APPROVED note for this version on its own incident, or the humanloop
    check says RESPONDED on it. PENDING: requested, no owner approval on its own incident yet (a same-text note
    elsewhere is named in `note`, not counted). Versions with no approval request are not in the dict (MISSING)."""
    rows = _delivery_rows(src)
    exports = _exports(src)
    out = {}
    for fpath in sorted(glob.glob(os.path.join(src, "register", "approval*", "approval-finding.json"))):
        dname = os.path.basename(os.path.dirname(fpath))
        doc = _read_json(fpath) or {}
        version = _version_of_finding(doc, dname)
        if not version:
            continue
        fid = "ifabric:%s:%s:%s:%s:approval" % (doc.get("control_ref") or "REG", version, doc.get("scope_kind") or "escalation",
                                                 doc.get("scope_id") or "register-%s" % version)
        canon = (_read_bytes(os.path.join(os.path.dirname(fpath), "approved-note-canonical.txt")) or b"").decode("utf-8", "replace").strip()
        mine = [r for r in rows if r.get("finding_id") == fid]
        number = next((r.get("number") for r in reversed(mine) if r.get("number")), None)
        delivered = next((r for r in mine if r.get("state") == "DELIVERED"), None)
        sent = next((r for r in mine if r.get("state") == "SENT"), None)
        checks = [r for r in mine if r.get("state") in ("RESPONDED", "AWAITING_RESPONSE", "SILENT", "NO_RESPONSE", "CLOSED")]
        last = checks[-1] if checks else None
        responded = next((r for r in checks if r.get("state") == "RESPONDED"), None)
        a = {"status": "PENDING", "finding_id": fid, "finding_path": os.path.relpath(fpath, src)}
        if number:
            a["incident"] = number
            a["ref"] = "servicenow:%s" % number
        req = utc((delivered or sent or {}).get("ts")) or utc(doc.get("detected_at"))
        if req:
            a["requested_at"] = req
        a["delivery_state"] = (last or delivered or sent or (mine[-1] if mine else {})).get("state") or ("NOT_SENT" if not mine else "UNKNOWN")
        own_note = other_note = None
        if canon:
            for num, exp in sorted(exports.items()):
                for when, who, text in _notes(exp):
                    if text.startswith(canon):
                        if num == number and own_note is None:
                            own_note = (num, when, who, exp["path"])
                        elif num != number and other_note is None:
                            other_note = (num, when, who, exp["path"])
        bits = []
        if own_note:
            a["status"] = "APPROVED"
            a["at"] = own_note[1] or utc((responded or {}).get("at"))
            a["approver"] = {"name": own_note[2], "id": (responded or {}).get("actor") or own_note[2], "role": "owner"}
            a["export_path"] = own_note[3]
            bits.append("the owner's note \"%s\" is on %s (export %s)" % (canon, number, own_note[3]))
        elif responded:
            a["status"] = "APPROVED"
            a["at"] = utc(responded.get("at")) or utc(responded.get("ts"))
            a["approver"] = {"name": responded.get("actor") or "owner", "id": responded.get("actor") or "owner", "role": "owner"}
            bits.append("humanloop check: RESPONDED by %s on %s (no export in the pack shows the note text)" % (
                responded.get("actor") or "the owner", number))
        if responded:
            a["responded"] = {"state": "RESPONDED", "actor": responded.get("actor"), "at": utc(responded.get("at")),
                              "at_basis": responded.get("at_basis"), "checked_at": responded.get("checked_at")}
            if a["status"] == "APPROVED" and responded.get("at_basis") == "last_update" and own_note and own_note[1] \
                    and utc(responded.get("at")) and utc(responded.get("at")) != own_note[1]:
                bits.append("the check's RESPONDED time %s is the incident's last update, not this note (%s)" % (
                    utc(responded.get("at")), own_note[1]))
        if a["status"] != "APPROVED":
            bits.append("%s is %s%s" % (number or "the approval incident", a["delivery_state"],
                                        (" (last check %s)" % last.get("checked_at")) if last and last.get("checked_at") else ""))
            if other_note:
                bits.append("a note with the same APPROVED text for %s by %s is on %s at %s (%s), not on this version's own "
                            "incident; it is not counted here" % (version, other_note[2], other_note[0], other_note[1] or "unknown time", other_note[3]))
        a["note"] = "; ".join(bits)
        out[version] = a
    return out


# ------------------------------------------------------------------ every run
PROV_BY_LABEL = {"LIVE_SUBJECT": "ASSESSED", "WIRING_TEST": "WIRING_TEST"}


def run_catalogue(src, run_ids, window=None, store_records=None):
    """Every run the tree knows: named runs (run-ids.txt, ASSESSED), pilots (register/experiments/experiments.jsonl,
    failed and halted ones included with their failure class), and every other run in derived/run-catalogue.jsonl
    (warm-ups and undeclared runs: EXPLORATORY). A run whose records are partly or not at all in the store is still
    listed, with `records_in_store` saying so. Sorted by start time."""
    store_records = store_records or []
    by = {}

    def row(cid):
        return by.setdefault(cid, {"cid": cid, "alias": cid, "provenance": "EXPLORATORY", "sources": []})

    counts = {}
    for r in store_records:
        cid = r.get("run.id") or r.get("correlation_id")
        if cid:
            c = counts.setdefault(cid, {"n": 0, "first": None, "last": None})
            c["n"] += 1
            ts = r.get("ts") if isinstance(r.get("ts"), str) and UTC_RE.match(r.get("ts")) else None
            if ts:
                c["first"] = min(c["first"] or ts, ts)
                c["last"] = max(c["last"] or ts, ts)
    for cid, alias in (run_ids or {}).items():
        x = row(cid)
        x.update(alias=alias, provenance="ASSESSED", purpose="named run (run-ids.txt)")
        x["sources"].append("run-ids.txt")
    for e in _read_jsonl(os.path.join(src, "register", "experiments", "experiments.jsonl")):
        cid = e.get("run_id")
        if not cid:
            continue
        x = row(cid)
        x["sources"].append("register/experiments/experiments.jsonl")
        if cid not in (run_ids or {}):
            x["provenance"] = "EXPLORATORY"
            x["alias"] = ("pilot-%s-%s" % (e.get("pilot"), cid.rsplit("-", 1)[-1])) if e.get("pilot") else cid
        state = "FAILED" if e.get("failed") else "HALTED" if e.get("halted") else "FINISHED"
        fc = e.get("failure_class") or (("halted: " + str(e.get("halt_reason") or "no halt_reason recorded")[:90]) if e.get("halted") else
                                        ("failed (no failure_class recorded): " + str(e.get("failure") or "")[:90]) if e.get("failed") else None)
        x.update(pilot=e.get("pilot"), scenario=e.get("scenario"), mode=e.get("mode"), state=state,
                 derivation_eligible=bool(e.get("derivation_eligible")), register=e.get("register"),
                 measure_file=e.get("measure_file"))
        if fc:
            x["failure_class"] = fc
        x["purpose"] = "pilot %s (%s, %s%s%s)" % (e.get("pilot") or "?", e.get("provenance") or "PILOT", state,
                                                 (": " + fc) if fc else "", "; baseline-eligible" if e.get("derivation_eligible") else "")
        t = e.get("time_utc") if isinstance(e.get("time_utc"), list) else []
        if len(t) == 2 and utc(t[0]) and utc(t[1]):
            x["started_at"], x["ended_at"] = utc(t[0]), utc(t[1])
        tok = (e.get("measured") or {}).get("c16_tokens")
        if isinstance(tok, int):
            x["tokens"] = tok
    for c in _read_jsonl(os.path.join(src, "derived", "run-catalogue.jsonl")):
        cid = c.get("run_id")
        if not cid:
            continue
        x = row(cid)
        x["sources"].append("derived/run-catalogue.jsonl")
        if x["provenance"] != "ASSESSED":
            x["provenance"] = PROV_BY_LABEL.get(c.get("label"), "EXPLORATORY")
        x["label"] = c.get("label")
        if not x.get("purpose"):
            x["purpose"] = "%s (%s)" % ("warm-up / exploratory run" if c.get("label") != "WIRING_TEST" else "wiring test",
                                        c.get("label") or "unlabelled")
        if utc(c.get("first_seen")) and not x.get("started_at"):
            x["started_at"] = utc(c.get("first_seen"))
        if utc(c.get("last_seen")) and not x.get("ended_at"):
            x["ended_at"] = utc(c.get("last_seen"))
        if "tokens" not in x and isinstance(c.get("tokens_in"), int):
            x["tokens"] = int(c.get("tokens_in") or 0) + int(c.get("tokens_out") or 0)
    w = window or {}
    w = w.get("event_window") if isinstance(w.get("event_window"), dict) else w
    ws, we = utc(w.get("start")), utc(w.get("end"))
    out = []
    for cid, x in by.items():
        c = counts.get(cid)
        x["records_in_store"] = c["n"] if c else 0
        if c and not x.get("started_at"):
            x["started_at"], x["ended_at"] = c["first"], c["last"]
        if not c:
            x["store_note"] = "no records of this run in store/ (listed from %s)" % ", ".join(sorted(set(x["sources"])))
        x["sources"] = sorted(set(x["sources"]))
        if ws and we and x.get("started_at"):
            x["in_window"] = ws <= x["started_at"] <= we
        for k in [k for k, v in x.items() if v is None]:
            del x[k]
        out.append(x)
    out.sort(key=lambda r: (r.get("started_at") or "9999", r["cid"]))
    return out


# ------------------------------------------------------------------ named-runs.md (the declared roles and window)
_NR_WIN = re.compile(r"Declared event window \(UTC\):\s*`(\d{4}-\d\d-\d\dT[0-9:.]+Z)`\s*to\s*`(\d{4}-\d\d-\d\dT[0-9:.]+Z)`")
_NR_CID = re.compile(r"`(ifabric-run-\d+-[0-9a-f]+)`")


def named_runs_md(root):
    """{"window": {"start", "end"} or None, "rows": [{control, role, attempt, cid, start, end, note, not_counted}]}
    parsed from the staged named-runs.md (the team's declared roles); empty when the pack has none."""
    try:
        with open(os.path.join(root, "named-runs.md"), "r", encoding="utf-8") as fh:
            text = fh.read()
    except (IOError, OSError):
        return {"window": None, "rows": []}
    m = _NR_WIN.search(text)
    win = {"start": m.group(1), "end": m.group(2)} if m else None
    day = win["start"][:10] if win else None
    rows = []
    for line in text.split("\n"):
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 12 or cells[0] == "control":
            continue
        cm = _NR_CID.search(cells[3])
        note = cells[11]

        def t(s):
            mm = re.match(r"(\d\d:\d\d:\d\d(?:\.\d+)?Z)", s or "")
            return "%sT%s" % (day, mm.group(1)) if (mm and day) else None
        rows.append({"control": cells[0], "role": cells[1].upper(), "attempt": cells[2], "cid": cm.group(1) if cm else None,
                     "start": t(cells[4]), "end": t(cells[5]), "note": note,
                     "not_counted": "NOT COUNTED" in note.upper()})
    return {"window": win, "rows": rows}

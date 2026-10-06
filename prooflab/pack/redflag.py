"""Red-flag lint over a STAGED Evidence Pack, read exactly as the console serves it (PR-49). Stdlib, Python 3.9.

    python3 -m prooflab pack lint <staged pack dir>        (or: python3 -m prooflab.pack.redflag <dir>)

Exit 0 = clean, 2 = red flags (one line per finding: rule id | file | offending text | fix hint), 1 = not a pack.
It never writes. It reads pack-index.json, answers/, auditor/, assessments/, register/, run-ids.txt,
derived/run-catalogue.jsonl, README.md, MANIFEST.json and the evidence data dirs; never the shipped prooflab/
or tools/ source (the console's own source carries the very words it hunts for).

Rules (each one is something a judge could read as disqualifying, or a false statement about us):
  R1  the rule is said to be dated after / not proven before the test (date_before_scope false, 'RULE DATED
      AFTER TEST', 'NOT proven before', PROVEN_AFTER, NOT_PROVEN). Always fails; R1-TRUE when the register's
      <v>.head.json is in the pack AND its LastModified is later than the run's scope start (a real finding).
  R2  'approval MISSING' / approval.status MISSING, per version (a register.versions[N] entry's own version).
      Fails, and the hint says whether that version's approval evidence (register/approval*, servicenow/) is in the
      pack (then the text is false) or omitted; a non-FROZEN pilot register with no evidence is honestly MISSING.
  R3  NOT_ASSESSED / INDETERMINATE shown for a run+control that has assessments/<C>/<cid>.json with a verdict.
  R4  the register shown is not the head of the frozen chain (by supersedes / frozen_at, never by name sort);
      a .sha256 sidecar that does not match its yaml. The whole chain ships under register/versions/ (main's layout).
  R5  run catalogue honesty over pack-index runs[] (every run, with provenance) and derived/run-catalogue.jsonl:
      every CID in run-ids.txt once and ASSESSED / LIVE_SUBJECT; no EXPLORATORY / PILOT run named or judged;
      every other run carries a declared role; infra-failed runs say why.
  R6  numbers: each answer's measured value / limit / verdict equals the stored assessment's; the run catalogue's
      token figure does not contradict the C16 verdict.
  R7  README: no <UPPER_SNAKE> placeholders outside backticks; every file it names exists in the pack.
  R8  contradictions: SATISFIED next to exceptions over tolerance, a halted run, a DEGRADED
      operation, 'over cap' / negative-headroom wording; one finding id with two different summaries.
  R9  secret-shaped strings or unredacted token-shaped values in the evidence data.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

from prooflab.contract.verdicts import BREACHED, INDETERMINATE, NOT_ASSESSED, SATISFIED

EXIT_CLEAN, EXIT_NOT_PACK, EXIT_FLAGS = 0, 1, 2
UNDECIDED = (NOT_ASSESSED, INDETERMINATE, "")
NOT_MET = (BREACHED, "NOT_" + SATISFIED)
NAMED_OK = ("LIVE_SUBJECT",)
# data the console serves; never the shipped source tree
TEXT_FILES = ("pack-index.json", "README.md")
TEXT_DIRS = ("answers", "auditor", "assessments", "projected-assessments")
DATA_DIRS = ("answers", "auditor", "assessments", "projected-assessments", "records", "store", "raw", "derived",
             "kit-crosscheck", "register", "servicenow")
SKIP_DIRS = ("prooflab", "tools", "__pycache__")


class Finding(object):
    __slots__ = ("rule", "file", "text", "hint")

    def __init__(self, rule, file, text, hint):
        self.rule, self.file, self.text, self.hint = rule, file, _clip(text), hint

    def line(self):
        return "%s | %s | %s | %s" % (self.rule, self.file, self.text, self.hint)

    def __repr__(self):
        return "Finding(%s)" % self.line()


def _clip(s, n=160):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 3] + "..."


# ---------------------------------------------------------------- loading
class Pack(object):
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.pidx = self.json("pack-index.json") or {}
        self.answers = self._dir_json("answers")
        self.auditor = self._dir_json("auditor")
        self.assessments = self._dir_json("assessments")
        self.run_ids = self._run_ids()
        self.catalogue = self._jsonl("derived/run-catalogue.jsonl")

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    def rel(self, path):
        return os.path.relpath(path, self.root)

    def exists(self, rel):
        return os.path.exists(self.p(*rel.split("/")))

    def json(self, rel):
        try:
            with open(self.p(*rel.split("/")), "rb") as fh:
                return json.loads(fh.read().decode("utf-8"))
        except (IOError, OSError, ValueError):
            return None

    def text(self, rel):
        try:
            with open(self.p(*rel.split("/")), "rb") as fh:
                return fh.read().decode("utf-8", "replace")
        except (IOError, OSError):
            return None

    def _dir_json(self, d):
        out = {}
        for path in sorted(glob.glob(self.p(d, "**", "*.json"), recursive=True)):
            doc = self.json(self.rel(path))
            if doc is not None:
                out[self.rel(path)] = doc
        return out

    def _jsonl(self, rel):
        rows = []
        for line in (self.text(rel) or "").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    rows.append({"_unparsed": line})
        return rows

    def _run_ids(self):
        txt = self.text("run-ids.txt") or ""
        return [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith("#")]

    def scope_start(self, cid=None):
        """Earliest known scope start for a run (or for any named run when cid is None)."""
        starts = []
        for a in self.assessments.values():
            if isinstance(a, dict) and (cid is None or a.get("scope_id") == cid) and a.get("scope_kind") == "run":
                starts.append(str(a.get("scope_start") or ""))
        for r in self.pidx.get("runs") or []:
            if isinstance(r, dict) and (cid is None or r.get("cid") == cid):
                starts.append(str(r.get("started_at") or ""))
        starts = [s for s in starts if s]
        return min(starts, key=_tkey) if starts else None


def _tkey(ts):
    """Comparable key for an ISO-8601 UTC time with or without fractional seconds."""
    m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?", str(ts or ""))
    if not m:
        return ""
    return m.group(1) + "." + (m.group(2) or "").ljust(6, "0")[:6]


def _http_date_key(s):
    """S3 head-object LastModified: ISO-8601, or an RFC 1123 date (Tue, 06 Oct 2026 13:36:44 GMT)."""
    if _tkey(s):
        return _tkey(s)
    import email.utils
    try:
        d = email.utils.parsedate_to_datetime(str(s))
        return d.strftime("%Y-%m-%dT%H:%M:%S") + ".000000"
    except (TypeError, ValueError, IndexError):
        return ""


# ---------------------------------------------------------------- register
_TOP = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*"?(.*?)"?\s*$')


def _register_top(text):
    top = {}
    for line in text.splitlines():
        if line.startswith("controls:") or line.startswith("- ") or line.startswith("  "):
            if line.startswith("controls:"):
                break
            continue
        m = _TOP.match(line)
        if m:
            top[m.group(1)] = m.group(2)
    return top


def registers(pack):
    """{version: {path, top}} over register/versions and register/superseded (not risks, inventories, pins)."""
    out = {}
    for d in ("versions", "superseded"):
        for path in sorted(glob.glob(pack.p("register", d, "*.yaml"))):
            base = os.path.basename(path)[:-5]
            if base.endswith(".risks") or base.startswith("inv-"):
                continue
            top = _register_top(pack.text(pack.rel(path)) or "")
            out[top.get("version") or top.get("register_version") or base] = {"path": pack.rel(path), "top": top}
    return out


def head_json(pack, version):
    for rel in ("register/versions/%s.head.json", "register/superseded/%s.head.json", "register/%s.head.json"):
        doc = pack.json(rel % version)
        if isinstance(doc, dict):
            return rel % version, doc
    return None, None


def approval_evidence(pack, version=None):
    """Paths in the pack that carry an approval Finding / its delivery / a ServiceNow export of it, for version.

    Approval-specific only: a file named approval* under register/ or servicenow/, or a servicenow/ JSON whose
    control_ref is REG (the T2 approval Finding's shape). A C16 breach finding is NOT approval evidence."""
    hits = []
    cands = glob.glob(pack.p("register", "**", "*approval*"), recursive=True)
    cands += glob.glob(pack.p("servicenow", "**", "*"), recursive=True)
    vpat = re.compile(r"(?<![A-Za-z0-9.-])%s(?![0-9.])" % re.escape(version)) if version else None
    for path in sorted(set(cands)):
        if not os.path.isfile(path):
            continue
        rel = pack.rel(path)
        body = pack.text(rel) or ""
        named = "approval" in os.path.basename(rel).lower()
        reg = bool(re.search(r'"control_ref"\s*:\s*"REG"', body))
        if not (named or reg):
            continue
        if vpat and not (vpat.search(body) or vpat.search(os.path.basename(rel))):
            continue
        hits.append(rel)
    return hits


# ---------------------------------------------------------------- text walking
def _strings(obj, path=""):
    """(json path, value) for every string / bool leaf."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            for item in _strings(v, "%s.%s" % (path, k) if path else str(k)):
                yield item
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for item in _strings(v, "%s[%d]" % (path, i)):
                yield item
    elif isinstance(obj, (str, bool)) or obj is None:
        yield path, obj


def _served_docs(pack):
    """(rel file, parsed json or None, raw text) for the files the console serves as text."""
    for rel in TEXT_FILES:
        raw = pack.text(rel)
        if raw is not None:
            yield rel, (pack.pidx if rel == "pack-index.json" else None), raw
    for d in TEXT_DIRS:
        for path in sorted(glob.glob(pack.p(d, "**", "*.json"), recursive=True)):
            rel = pack.rel(path)
            raw = pack.text(rel)
            yield rel, pack.json(rel), raw


# ---------------------------------------------------------------- R1
R1_TEXT = re.compile(r"DATED AFTER|PROVEN_AFTER|NOT_PROVEN|NOT proven before", re.I)


def r1(pack):
    out = []
    regs = registers(pack)
    for rel, doc, raw in _served_docs(pack):
        hits = []
        if isinstance(doc, dict):
            for jp, v in _strings(doc):
                if jp.endswith("date_before_scope") and v is False:
                    hits.append((jp, "date_before_scope: false", _hit_version(pack, doc, jp)))
                elif isinstance(v, str) and R1_TEXT.search(v):
                    hits.append((jp, v, _hit_version(pack, doc, jp)))
        elif raw:
            for line in raw.splitlines():
                if R1_TEXT.search(line):
                    hits.append(("", line, None))
        seen = set()
        for jp, text, version in hits:
            key = (version, R1_TEXT.search(text).group(0).upper() if R1_TEXT.search(text) else text)
            if key in seen:
                continue
            seen.add(key)
            cid = (doc or {}).get("scope", {}).get("cid") if isinstance(doc, dict) and isinstance(
                doc.get("scope"), dict) else None
            out.append(_r1_one(pack, regs, rel, jp, text, version, cid))
    return out


def _version_of(doc, jp):
    rule = doc.get("rule") if isinstance(doc, dict) else None
    if isinstance(rule, dict) and rule.get("register_version"):
        return str(rule["register_version"])
    reg = doc.get("register") if isinstance(doc, dict) else None
    if isinstance(reg, dict) and reg.get("version"):
        return str(reg["version"])
    return None


def _r1_one(pack, regs, rel, jp, text, version, cid):
    start = pack.scope_start(cid)
    version = version or (pack.pidx.get("register") or {}).get("version")
    hpath, head = head_json(pack, version) if version else (None, None)
    frozen = ((regs.get(version) or {}).get("top") or {}).get("frozen_at") if version else None
    where = "%s%s" % (rel, (" @" + jp) if jp else "")
    if head:
        lm = head.get("LastModified") or head.get("last_modified") or head.get("t1")
        if start and _http_date_key(lm) and _http_date_key(lm) > _tkey(start):
            return Finding("R1-TRUE", where, text, "TRUE: %s LastModified %s is after the scope start %s; a human "
                           "must decide (re-run under a rule frozen before it, or declare it)" % (hpath, lm, start))
        return Finding("R1", where, text, "FALSE: %s LastModified %s is not after the scope start %s; the "
                       "answers were built without the proof file, rebuild them" % (hpath, lm, start))
    return Finding("R1", where, text, "UNPROVEN, not dated after: register %s frozen_at %s, scope start %s, but "
                   "register/versions/%s.head.json (S3 head-object of the frozen copy) is not in the pack; add it "
                   "and rebuild" % (version, frozen, start, version))


# ---------------------------------------------------------------- R2
R2_TEXT = re.compile(r"approval\s+MISSING", re.I)


JP_PART = re.compile(r"[^.\[\]]+|\[\d+\]")


def _jp_get(doc, parts):
    """The value at json path parts like ['register', 'versions', '[2]'] (None when absent)."""
    cur = doc
    for part in parts:
        if part.startswith("["):
            i = int(part[1:-1])
            cur = cur[i] if isinstance(cur, list) and i < len(cur) else None
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def _hit_version(pack, doc, jp):
    """The register version a hit is about: the nearest enclosing object's own `version` (a register.versions[N]
    entry), else the doc's rule.register_version / register.version, else the pack-index head."""
    parts = JP_PART.findall(jp or "")
    for n in range(len(parts) - 1, 0, -1):
        node = _jp_get(doc, parts[:n])
        if isinstance(node, dict) and node.get("version") and ("register" in parts[:n] or "versions" in parts[:n]):
            return str(node["version"])
    return _version_of(doc, jp) or (pack.pidx.get("register") or {}).get("version")


def r2(pack):
    out, regs = [], registers(pack)
    for rel, doc, raw in _served_docs(pack):
        hits = []
        if isinstance(doc, dict):
            for jp, v in _strings(doc):
                if jp.endswith("approval.status") and v == "MISSING":
                    hits.append((jp, "approval.status MISSING", _hit_version(pack, doc, jp)))
                elif isinstance(v, str) and R2_TEXT.search(v):
                    hits.append((jp, v, _hit_version(pack, doc, jp)))
        elif raw:
            hits += [("", l, (pack.pidx.get("register") or {}).get("version"))
                     for l in raw.splitlines() if R2_TEXT.search(l)]
        by_version = {}
        for jp, text, version in hits:
            by_version.setdefault(version, []).append((jp, text))
        for version, vhits in sorted(by_version.items(), key=lambda kv: str(kv[0])):
            jp, text = vhits[0]
            ev = approval_evidence(pack, version)
            status = ((regs.get(version) or {}).get("top") or {}).get("status") or ""
            if not ev and status and status != "FROZEN":
                continue  # an EXPLORATORY / pilot register that was never sent for approval: MISSING is the truth
            where = "%s%s" % (rel, (" @" + jp) if jp else "")
            more = (" (+%d more for %s in this file)" % (len(vhits) - 1, version)) if len(vhits) > 1 else ""
            if ev:
                out.append(Finding("R2", where, text + more, "FALSE: approval evidence for %s is in the pack (%s); "
                                   "rebuild the answers so they read it" % (version, ", ".join(ev[:3]))))
            else:
                out.append(Finding("R2", where, text + more, "approval evidence for %s is omitted from the pack: "
                                   "copy register/approval-finding.json + its delivery / ServiceNow export into the "
                                   "pack and rebuild, or confirm with the owner that it truly does not exist" % version))
    return out


# ---------------------------------------------------------------- R3
def _assessed(pack):
    """{(control, cid): (verdict, rel)} for run-scoped assessments with a definite verdict."""
    out = {}
    for rel, a in pack.assessments.items():
        if not isinstance(a, dict) or a.get("scope_kind") != "run":
            continue
        v = str(a.get("requirement_verdict") or (a.get("finding") or {}).get("verdict") or "")
        if v and v not in UNDECIDED:
            out[(str(a.get("control_ref")), str(a.get("scope_id")))] = (v, rel)
    return out


def r3(pack):
    out, done = [], _assessed(pack)
    for rel, ans in pack.answers.items():
        key = (str((ans.get("control") or {}).get("ref")), str((ans.get("scope") or {}).get("cid")))
        v = str((ans.get("verdict") or {}).get("value") or "")
        if key in done and v in UNDECIDED:
            out.append(Finding("R3", rel, "verdict %s" % (v or "empty"), "%s says %s: rebuild the answer from it"
                               % (done[key][1], done[key][0])))
    for i, row in enumerate(pack.pidx.get("answers") or []):
        key = (str(row.get("control_ref")), str(row.get("scope")))
        if key in done and str(row.get("verdict") or "") in UNDECIDED:
            out.append(Finding("R3", "pack-index.json @answers[%d]" % i, "%s %s" % (key, row.get("verdict")),
                               "%s says %s" % (done[key][1], done[key][0])))
    for i, run in enumerate(pack.pidx.get("runs") or []):
        cid, verdicts = run.get("cid"), run.get("verdicts") or {}
        for (c, rid), (v, arel) in sorted(done.items()):
            if rid == cid and str(verdicts.get(c, "")) in UNDECIDED:
                out.append(Finding("R3", "pack-index.json @runs[%d].verdicts" % i, "%s for %s: %s" % (
                    c, cid, verdicts.get(c, "absent")), "%s says %s: show it" % (arel, v)))
    claim = pack.pidx.get("claim") or {}
    for i, c in enumerate(claim.get("controls") or []):
        if str(c.get("verdict_overall") or "") not in UNDECIDED:
            continue
        hits = [(rid, v, arel) for (cr, rid), (v, arel) in done.items() if cr == c.get("ref") and rid in pack.run_ids]
        if hits:
            rid, v, arel = sorted(hits)[0]
            out.append(Finding("R3", "pack-index.json @claim.controls[%d]" % i, "%s %s" % (
                c.get("ref"), c.get("verdict_overall")), "%s (named run %s) says %s: the claim must carry it"
                % (arel, rid, v)))
    return out


# ---------------------------------------------------------------- R4
def r4(pack):
    out, regs = [], registers(pack)
    if not regs:
        return out
    superseded = set(r["top"].get("supersedes") for r in regs.values() if r["top"].get("supersedes"))
    heads = [v for v in regs if v not in superseded]
    if len(heads) != 1:
        out.append(Finding("R4", "register/", "chain heads: %s" % (", ".join(sorted(heads)) or "none"),
                           "the frozen chain must have exactly one head (fix supersedes)"))
        heads = sorted(heads, key=lambda v: _tkey(regs[v]["top"].get("frozen_at")))[-1:]
    head = heads[0] if heads else None
    # The whole chain (pilot registers included) ships under register/versions/: history.register_history,
    # engine.date_proof and build._missing_t1 read only there, so neither the layout nor a non-FROZEN pilot status
    # is a red flag. Only the head shown and the sidecars are checked.
    for v, r in regs.items():
        side = pack.text(r["path"][:-5] + ".sha256")
        if side is not None:
            import hashlib
            got = hashlib.sha256(open(pack.p(*r["path"].split("/")), "rb").read()).hexdigest()
            want = (side.split() or [""])[0]
            if want != got:
                out.append(Finding("R4", r["path"][:-5] + ".sha256", want, "sidecar does not match the yaml (%s)" % got))
    shown = (pack.pidx.get("register") or {}).get("version")
    if head and shown and shown != head:
        out.append(Finding("R4", "pack-index.json @register.version", shown, "head of the frozen chain is %s" % head))
    for rel, ans in pack.answers.items():
        rv = (ans.get("rule") or {}).get("register_version")
        if head and rv and rv != head:
            out.append(Finding("R4", rel, "rule.register_version %s" % rv, "head of the frozen chain is %s; rebuild "
                               "or state why this run was judged under an older version" % head))
    return out


# ---------------------------------------------------------------- R5
NAMED_PROV = ("ASSESSED", "LIVE_SUBJECT")          # pack-index runs[].provenance of a named run (PR-47)
NOT_NAMED = ("EXPLORATORY", "PILOT", "BASELINE")    # honest catalogue entries, never a named run
UNDECLARED = ("", "OURS-ROLE-UNDECLARED", "unlabelled (gap)")


def _declared(lab):
    return str(lab or "") not in UNDECLARED


def r5(pack):
    """Run catalogue honesty. pack-index runs[] lists EVERY run (pilots and warm-ups included), each with its
    provenance (PR-47); derived/run-catalogue.jsonl lists the runs the stitcher saw. A run is NAMED when it is in
    named_runs.entries or in runs[] with provenance ASSESSED / LIVE_SUBJECT; an EXPLORATORY / PILOT entry is an
    honest catalogue line, not a red flag."""
    out = []
    rows, idx = {}, {}
    for row in pack.catalogue:
        rows.setdefault(row.get("run_id"), []).append(row)
    for i, r in enumerate(pack.pidx.get("runs") or []):
        if isinstance(r, dict):
            idx.setdefault(r.get("cid"), []).append((i, r))

    def labels(cid):
        """Every label the pack gives this run: the index's provenance and label, the catalogue's label."""
        labs = []
        for _, r in idx.get(cid) or []:
            labs += [str(r.get("provenance") or ""), str(r.get("label") or "")]
        labs += [str(row.get("label") or "") for row in rows.get(cid) or []]
        return [l for l in labs if l]

    def is_named_label(cid):
        labs = labels(cid)
        return bool(labs) and any(l in NAMED_OK + NAMED_PROV for l in labs) and not any(l in NOT_NAMED for l in labs)

    # 1. every CID in run-ids.txt: listed exactly once per source, and labelled as a named run everywhere
    if len(set(pack.run_ids)) != len(pack.run_ids):
        out.append(Finding("R5", "run-ids.txt", "duplicate CID", "list each named run once"))
    for cid in pack.run_ids:
        n_idx, n_cat = len(idx.get(cid) or []), len(rows.get(cid) or [])
        if n_idx + n_cat == 0:
            out.append(Finding("R5", "pack-index.json @runs", "%s not catalogued" % cid,
                               "every CID in run-ids.txt appears in the run catalogue (pack-index runs[])"))
        for src, n in (("pack-index.json @runs", n_idx), ("derived/run-catalogue.jsonl", n_cat)):
            if n > 1:
                out.append(Finding("R5", src, "%s appears %d times" % (cid, n), "list each run exactly once"))
        if n_idx + n_cat and not is_named_label(cid):
            out.append(Finding("R5", "pack-index.json @runs", "%s labelled %s" % (cid, "/".join(labels(cid)) or
                                                                                   "nothing"),
                               "a named run (run-ids.txt) must be ASSESSED / LIVE_SUBJECT, never a warm-up or pilot"))
    # 2. every other run carries a declared role somewhere in the pack, and is not shown as assessed
    for cid in sorted(set(rows) | set(idx), key=str):
        if cid in pack.run_ids:
            continue
        if not any(_declared(l) for l in labels(cid)):
            out.append(Finding("R5", "derived/run-catalogue.jsonl", "%s labelled %s" % (cid, "/".join(labels(cid)) or "nothing"),
                               "declare its role (PILOT / BASELINE / warm-up EXPLORATORY / infra-failed) in the "
                               "provenance, or drop its records from the pack"))
        elif "ASSESSED" in labels(cid) and not any(l in NOT_NAMED for l in labels(cid)):
            out.append(Finding("R5", "pack-index.json @runs", "%s labelled %s but not in run-ids.txt" % (
                cid, "/".join(labels(cid))), "label it EXPLORATORY / PILOT, or name it in run-ids.txt"))
        if any(row.get("assessed") for row in rows.get(cid) or []):
            out.append(Finding("R5", "derived/run-catalogue.jsonl", "%s assessed but not in run-ids.txt" % cid,
                               "only named runs are assessed"))
        for i, r in idx.get(cid) or []:
            if r.get("verdicts"):
                out.append(Finding("R5", "pack-index.json @runs[%d].verdicts" % i, "%s %s" % (cid, r["verdicts"]),
                                   "a run outside run-ids.txt is not judged: drop its verdicts"))
    # 3. infra-failed attempts are labelled as such
    for cid, entries in sorted(idx.items(), key=lambda kv: str(kv[0])):
        for i, r in entries:
            if str(r.get("state") or "").upper() == "FAILED" and not (
                    r.get("failure_class") or "FAIL" in str(r.get("purpose") or "").upper()):
                out.append(Finding("R5", "pack-index.json @runs[%d]" % i, "%s state FAILED" % cid,
                                   "say why it failed (failure_class) so it is not read as a subject failure"))
    # 4. named_runs.entries: every scope is a named run
    for i, e in enumerate((pack.pidx.get("named_runs") or {}).get("entries") or []):
        cid = (e.get("scope") or {}).get("cid")
        if cid and cid not in pack.run_ids:
            out.append(Finding("R5", "pack-index.json @named_runs.entries[%d]" % i, "%s (%s)" % (
                cid, "/".join(labels(cid)) or "not catalogued"),
                "a named run must be in run-ids.txt; no warm-up or pilot"))
    return out


# ---------------------------------------------------------------- R6
def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _measured_of(a):
    m = a.get("measured") or {}
    c = str(a.get("control_ref"))
    if c == "C16":
        return _num(m.get("total_tokens")), _num(m.get("cap"))
    if c == "C7":
        return _num(m.get("coverage_pct")), None
    if c == "C9":
        return _num(m.get("violating")), None
    return None, None


def r6(pack):
    out = []
    by_id = {}
    for rel, a in pack.assessments.items():
        if isinstance(a, dict):
            by_id[(str(a.get("control_ref")), str(a.get("scope_kind")), str(a.get("scope_id")))] = (rel, a)
    for rel, ans in pack.answers.items():
        c = str((ans.get("control") or {}).get("ref"))
        sc = ans.get("scope") or {}
        hit = by_id.get((c, str(sc.get("kind")), str(sc.get("id") or sc.get("cid"))))
        if not hit:
            continue
        arel, a = hit
        av = str((ans.get("verdict") or {}).get("value") or "")
        if av and av != str(a.get("requirement_verdict") or ""):
            out.append(Finding("R6", rel, "verdict %s" % av, "%s says %s" % (arel, a.get("requirement_verdict"))))
        meas, cap = _measured_of(a)
        got = _num((ans.get("measurement") or {}).get("value"))
        if meas is not None and c in ("C16", "C7") and got != meas:
            out.append(Finding("R6", rel, "measurement.value %s" % got, "%s measured %s" % (arel, meas)))
        lim = _num((ans.get("comparison") or {}).get("limit"))
        if cap is not None and lim != cap:
            out.append(Finding("R6", rel, "comparison.limit %s" % lim, "%s cap %s" % (arel, cap)))
        if c == "C16" and av == SATISFIED:
            lim = lim if lim is not None else cap
            for row in pack.catalogue:
                if row.get("run_id") == sc.get("cid"):
                    tot = (_num(row.get("tokens_in")) or 0) + (_num(row.get("tokens_out")) or 0)
                    if lim is not None and tot > lim:
                        out.append(Finding("R6", "derived/run-catalogue.jsonl", "%s tokens_in+out %d > cap %d"
                                           % (sc.get("cid"), tot, lim),
                                           "contradicts C16 SATISFIED at %s tokens in %s: state the basis of each "
                                           "figure in the pack, or align them" % (got, rel)))
    return out


# ---------------------------------------------------------------- R7
PLACEHOLDER = re.compile(r"<[A-Z][A-Z0-9_]*>")
PATHLIKE = re.compile(r"^[A-Za-z0-9_.\-/]+\.(md|json|jsonl|txt|py|png|yaml|sha256|zip)$|^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-/]*$")
README_SIDECARS = ("pack-root.json",)  # uploaded AFTER the pack, never inside it
PLATFORM_NAMES = ("aws/", "/aws/")      # CloudWatch log group names, not pack paths
NOT_IN_PACK = re.compile(r"^\s*\((not|none) in (this|the) pack\b", re.I)


def r7(pack):
    out = []
    txt = pack.text("README.md")
    if txt is None:
        return [Finding("R7", "README.md", "missing", "the pack must carry its README")]
    for n, line in enumerate(txt.splitlines(), 1):
        bare = re.sub(r"`[^`]*`", "", line)
        for m in PLACEHOLDER.finditer(bare):
            out.append(Finding("R7", "README.md:%d" % n, m.group(0), "fill the template placeholder"))
        for m in re.finditer(r"`([^`]+)`", line):
            name = m.group(1).strip()
            if " " in name or "<" in name or "__pycache__" in name or name in README_SIDECARS:
                continue
            if name.startswith(PLATFORM_NAMES) or NOT_IN_PACK.match(line[m.end():]):
                continue  # a platform log group, or the README itself says the file is not shipped
            if PATHLIKE.match(name) and not pack.exists(name.rstrip("/")):
                out.append(Finding("R7", "README.md:%d" % n, name, "the README names a file the pack does not "
                                   "contain: add it or fix the README"))
    return out


# ---------------------------------------------------------------- R8
def r8(pack):
    out = []
    # Stored integrity fields (pack-index.integrity, answers' source.manifest_status, the auditor's integrity line)
    # are stale BY CONSTRUCTION: they are written before MANIFEST.json, which lists them, and the console stamps
    # integrity at serve time (console/server.py). So they are not linted here.
    for rel, ans in pack.answers.items():
        verdict = str((ans.get("verdict") or {}).get("value") or "")
        comp = ans.get("comparison") or {}
        n, allowed = _num(comp.get("exceptions_count")), _num(comp.get("exceptions_allowed"))
        if verdict == SATISFIED and n is not None and allowed is not None and n > allowed:
            out.append(Finding("R8", rel + " @comparison", "SATISFIED with exceptions_count %d > exceptions_allowed "
                               "%s" % (n, comp.get("exceptions_allowed")), "the answer must explain or count the "
                               "exception (%s) next to the verdict" % ", ".join(
                                   str(e.get("kind")) for e in ans.get("exceptions") or [])))
        if comp.get("within_limit") is True and verdict in NOT_MET or (
                comp.get("within_limit") is False and verdict == SATISFIED):
            out.append(Finding("R8", rel + " @comparison.within_limit", "%s with within_limit %s" % (
                verdict, comp.get("within_limit")), "verdict and comparison disagree"))
        dec = (ans.get("audit_question") or {}).get("decision") or {}
        if verdict == SATISFIED and str(dec.get("outcome")) in ("STOPPED", "DENIED", "BLOCKED"):
            out.append(Finding("R8", rel + " @audit_question.decision", "outcome %s / %s" % (
                dec.get("outcome"), dec.get("text")), "a halted run shown as SATISFIED: say what was halted and "
                "why the requirement still held"))
        for jp, v in _strings(ans):
            if not isinstance(v, str):
                continue
            if verdict == SATISFIED and re.search(r"\bover (the )?cap\b|\bexceed(s|ed)? (the )?(cap|limit)\b|"
                                                    r"headroom -\d", v, re.I):
                out.append(Finding("R8", "%s @%s" % (rel, jp), v, "over-cap wording next to SATISFIED"))
            if verdict in NOT_MET and re.search(r"\bunder (the )?cap\b|within (the )?limit",
                                                                       v, re.I):
                out.append(Finding("R8", "%s @%s" % (rel, jp), v, "under-cap wording next to %s" % verdict))
    for rel, a in pack.assessments.items():
        if not isinstance(a, dict):
            continue
        v = str(a.get("requirement_verdict") or "")
        summ = str((a.get("finding") or {}).get("summary") or "")
        if v == SATISFIED and (str(a.get("operation")) == "DEGRADED" or str(a.get("deficiency")) not in (
                "none", "None", "")):
            out.append(Finding("R8", rel, "SATISFIED with operation %s, deficiency %s (%s)" % (
                a.get("operation"), a.get("deficiency"), (a.get("measured") or {}).get("operation_note") or ""),
                "the shown verdict must carry the operating deficiency (e.g. spans after a halt), not hide it"))
        if v == SATISFIED and re.search(r"headroom -\d", summ):
            out.append(Finding("R8", rel + " @finding.summary", summ, "'headroom -N' reads as over cap; say 'under "
                               "cap by N' as pack-index does"))
    summaries = {}
    for rel, a in pack.assessments.items():
        f = (a or {}).get("finding") if isinstance(a, dict) else None
        if isinstance(f, dict) and f.get("summary"):
            summaries.setdefault((str(a.get("control_ref")), str(a.get("scope_id"))), set()).add(
                re.sub(r"\s+", " ", f["summary"]))
    for i, f in enumerate(pack.pidx.get("findings") or []):
        key = (str(f.get("control_ref")), str(f.get("scope_id")))
        if key in summaries and f.get("summary") and re.sub(r"\s+", " ", f["summary"]) not in summaries[key]:
            out.append(Finding("R8", "pack-index.json @findings[%d].summary" % i, f["summary"],
                               "the stored assessment says: %s" % sorted(summaries[key])[0]))
    return out


# ---------------------------------------------------------------- R9
def _patterns():
    # assembled from parts so this file never carries a secret-shaped literal
    aws = "(?:" + "AK" + "IA|" + "AS" + "IA)" + "[A-Z0-9]{16}"
    pem = "-----BEGIN [A-Z ]*" + "PRIV" + "ATE KEY-----"
    gh = "gh" + "p_[A-Za-z0-9]{20,}|" + "github" + "_pat_"
    oa = "s" + "k-[A-Za-z0-9]{20,}"
    sl = "xo" + "x[bap]-[A-Za-z0-9-]{10,}"
    br = "Bea" + "rer [A-Za-z0-9._~+/=-]{20,}"
    tq = "t" + "kn=[A-Za-z0-9]"
    sa = "aws_" + "secret_access_key|aws_" + "session_token"
    return re.compile("|".join((aws, pem, gh, oa, sl, br, tq, sa)))


TOKEN_KEY = re.compile(r"(^|[._-])(token|secret|password|api[_-]?key|authorization|write[_-]?token)$", re.I)
REDACTED = re.compile(r"^(\*+|REDACTED.*|<redacted>|\[redacted\]|sha256:[0-9a-f]+|)$", re.I)


def r9(pack):
    out, pat = [], _patterns()
    for d in DATA_DIRS + ("",):
        base = pack.p(d) if d else pack.root
        if not os.path.isdir(base):
            continue
        paths = (glob.glob(os.path.join(base, "**", "*"), recursive=True) if d else
                 [os.path.join(base, f) for f in os.listdir(base)])
        for path in sorted(paths):
            rel = pack.rel(path)
            if not os.path.isfile(path) or rel.split(os.sep)[0] in SKIP_DIRS or path.endswith((".png", ".zip")):
                continue
            raw = pack.text(rel) or ""
            m = pat.search(raw)
            if m:
                out.append(Finding("R9", rel, m.group(0)[:6] + "...(redacted)", "secret-shaped string: remove it, "
                                   "re-run the redaction, rebuild the manifest"))
                continue
            if rel.endswith((".json", ".jsonl")):
                for doc in _json_docs(raw):
                    for jp, v in _strings(doc):
                        leaf = jp.rsplit(".", 1)[-1]
                        if isinstance(v, str) and TOKEN_KEY.search(leaf) and len(v) >= 16 and " " not in v \
                                and not REDACTED.match(v):
                            out.append(Finding("R9", "%s @%s" % (rel, jp), v[:4] + "...(redacted)",
                                               "token-shaped value not redacted"))
                            break
    return out


def _json_docs(raw):
    try:
        yield json.loads(raw)
        return
    except ValueError:
        pass
    for line in raw.splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            continue


# ---------------------------------------------------------------- driver
RULES = (r1, r2, r3, r4, r5, r6, r7, r8, r9)


def lint(pack_dir):
    pack = Pack(pack_dir)
    out = []
    for rule in RULES:
        out.extend(rule(pack))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["lint"]:
        argv = argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.split("\n\n")[1] + "\n\nexit 0 clean, 2 red flags, 1 not a pack")
        return 0 if argv else EXIT_NOT_PACK
    root = argv[0]
    if not os.path.isfile(os.path.join(root, "pack-index.json")):
        print("pack lint: %s has no pack-index.json (not a staged pack)" % root, file=sys.stderr)
        return EXIT_NOT_PACK
    found = lint(root)
    for f in found:
        print(f.line())
    print("pack lint: %d red flag(s) in %s" % (len(found), root), file=sys.stderr)
    return EXIT_FLAGS if found else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())

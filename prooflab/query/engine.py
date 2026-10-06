"""The query engine (ARCH 3.7, T5.1). Stdlib only, Python 3.9. Offline: reads an unzipped Evidence Pack.

Pack layout read (ARCH 9.1, all optional; a missing piece becomes a printed gap, never a crash):
  store/records.jsonl          flat dotted-key records (prooflab.contract.record), one JSON object per line
  derived/run-index.jsonl      one row per run: cid | run_id, provenance, phase, condition, first_span, last_span
  derived/run-catalogue.jsonl  one row per run any source saw: cid | run_id, label, source, assessed
  assessments/<C>/*.json       Assessment as a dict (the contract dataclass names) or one flat assessment record
  register/versions/*.yaml (+ <v>.head.json T1 proof), register/versions/*.risks.yaml, register/versions/inv-*.yaml (or register/inventory/*.yaml)
  MANIFEST.json, derived/corroboration/<cid>.json

Verdict semantics live here (the window rule, E-06) and in prooflab.evaluators; nothing in console code.
A stored assessment is the answer; if an evaluator exposes `recompute_from_pack(pack, control, cid)` (optional
entry point, discovered by name) its result is compared and any mismatch is shown as a flagged difference.
"""
from __future__ import annotations

import glob
import importlib
import json
import os
import re

from prooflab.contract import verdicts as V
from prooflab.registry import parse as P

CONTROLS = ("C16", "C7", "C9")
WINDOW_PROVENANCE = ("LIVE_SUBJECT", "FAULT_INJECTION", "AUTHORIZED_TEST")   # ARCH 3.4 window rule
OUT_OF_SCOPE_LABELS = ("reference", "other", "cockpit", "my-agent", "unattributed")
UNKNOWN = "unknown"


# ---------------------------------------------------------------- small helpers
def norm_control(text):
    t = str(text).strip().upper()
    if t.startswith("C"):
        t = t[1:]
    return "C" + t if t.isdigit() else str(text).strip().upper()


def read_jsonl(path):
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except (IOError, OSError):
        pass
    return rows


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError):
        return None


def _cid(row):
    for key in ("cid", "run_id", "run.id", "correlation_id"):
        if row.get(key):
            return str(row[key])
    return None


def t1_text(head):
    """The T1 instant of a head-object proof as a ...Z string (S3 prints `+00:00`), else None."""
    if not isinstance(head, dict):
        return None
    t = head.get("LastModified") or head.get("last_modified") or head.get("t1")
    if not isinstance(t, str):
        return None
    t = t.strip()
    return t[:-6] + "Z" if t.endswith("+00:00") else t


DATE_PROOF_STATES = ("PROVEN_BEFORE", "PROVEN_AFTER", "NOT_PROVEN")


def _sha_matches(claimed, digest):
    """True/False when the proof carries a SHA-256 (hex, or S3's base64 of the digest), None when it carries none."""
    import base64
    if not isinstance(claimed, str) or not claimed.strip():
        return None
    c = claimed.strip()
    if re.match(r"^[0-9a-fA-F]{64}$", c):
        return c.lower() == digest.hex()
    try:
        return base64.b64decode(c, validate=True) == digest
    except (ValueError, TypeError):
        return False


def date_proof(pack, threshold_version, control, scope_start):
    """The tri-state date proof for a rule against a scope start (ARCH 3.3, G5):
    PROVEN_BEFORE  the pack holds the S3 head-object proof (T1) of the first register file carrying the threshold
                   version, its SHA-256 matches that file, and T1 <= the scope start;
    PROVEN_AFTER   the same proof, but T1 is LATER than the scope start (only this state may read "dated after");
    NOT_PROVEN     no proof in the pack, a proof whose SHA-256 does not match the file, or no scope start to compare."""
    import hashlib
    first, head = pack.t1_head(threshold_version, control)
    out = {"state": "NOT_PROVEN", "register_file": first, "t1_at": None, "version_id": None, "key": None,
           "checksum_verified": None, "scope_start": scope_start if _utc_key(scope_start) else None, "reason": ""}
    if not first:
        out["reason"] = "no register version in the pack carries %s" % threshold_version
        return out
    t1 = t1_text(head)
    if not head or not _utc_key(t1):
        out["reason"] = ("date proof not in this pack: no S3 head-object (T1) for register/versions/%s.yaml "
                         "(register/versions/%s.head.json)" % (first, first))
        return out
    out.update(t1_at=t1, version_id=head.get("VersionId"), key=head.get("Key"))
    try:
        digest = hashlib.sha256(open(pack.p("register", "versions", first + ".yaml"), "rb").read()).digest()
        out["checksum_verified"] = _sha_matches(head.get("ChecksumSHA256"), digest)
    except (IOError, OSError):
        out["checksum_verified"] = False
    if out["checksum_verified"] is False:
        out["reason"] = ("the T1 proof's SHA-256 does not match register/versions/%s.yaml in this pack: "
                         "it proves another file" % first)
        return out
    start = _utc_key(scope_start)
    if not start:
        out["reason"] = "no recorded scope start to compare T1 %s against" % t1
        return out
    if _utc_key(t1) <= start:
        out.update(state="PROVEN_BEFORE", reason="S3 T1 %s <= scope start %s" % (t1, scope_start))
    else:
        out.update(state="PROVEN_AFTER", reason="S3 T1 %s is LATER than scope start %s" % (t1, scope_start))
    return out


def _utc_key(text):
    """A sortable key for a UTC string (ms/no-ms alike), or None."""
    if not isinstance(text, str):
        return None
    m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z$", text)
    if not m:
        return None
    return m.group(1) + ((m.group(2) or ".")[:4].ljust(4, "0"))


def _num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _ids(records, limit=8):
    out = [r.get("record_id") for r in records if r.get("record_id")]
    shown = out[:limit]
    return shown, max(0, len(out) - len(shown))


# ---------------------------------------------------------------- the pack
class Pack(object):
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.records = read_jsonl(self.p("store", "records.jsonl"))
        self.run_index = read_jsonl(self.p("derived", "run-index.jsonl"))
        self.catalogue = read_jsonl(self.p("derived", "run-catalogue.jsonl"))
        self.by_cid = {}
        for r in self.records:
            c = _cid(r)
            if c:
                self.by_cid.setdefault(c, []).append(r)
        for rows in self.by_cid.values():
            rows.sort(key=lambda r: (_utc_key(r.get("ts")) or "", str(r.get("record_id"))))
        self.index_by_cid = dict((_cid(r), r) for r in self.run_index if _cid(r))
        self.catalogue_by_cid = dict((_cid(r), r) for r in self.catalogue if _cid(r))
        self.assessments = self._load_assessments()
        self.registers = self._load_registers()
        self.window = read_json(self.p("window.json"))

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    # -- assessments
    def _load_assessments(self):
        found = []
        for r in self.records:
            if r.get("record_kind") == "assessment":
                found.append(normalize_assessment(r))
        for path in sorted(glob.glob(self.p("assessments", "*", "*.json"))):
            doc = read_json(path)
            if isinstance(doc, dict):
                a = normalize_assessment(doc)
                a["_file"] = os.path.relpath(path, self.root)
                found.append(a)
        latest = {}
        for a in found:           # corrections replace, they don't add: keep the highest rN per scope
            key = (a["control_ref"], a["threshold_version"], a["scope_kind"], a["scope_id"])
            old = latest.get(key)
            if old is None or (a["rev"], a["as_of"] or "") >= (old["rev"], old["as_of"] or ""):
                latest[key] = a
        return sorted(latest.values(), key=lambda a: (a["control_ref"], a["scope_start"] or "", a["scope_id"]))

    def assessments_for(self, control, scope_kinds=None, scope_id=None):
        out = []
        for a in self.assessments:
            if a["control_ref"] != control:
                continue
            if scope_kinds and a["scope_kind"] not in scope_kinds:
                continue
            if scope_id is not None and a["scope_id"] != scope_id:
                continue
            out.append(a)
        return out

    # -- register
    def _load_registers(self):
        regs = {}
        for path in sorted(glob.glob(self.p("register", "versions", "*.yaml"))):
            name = os.path.basename(path)[:-5]
            if name.endswith(".risks"):
                continue
            try:
                doc = P.parse_register(open(path, "rb").read().decode("utf-8"))
            except (ValueError, IOError, OSError):
                continue
            head = read_json(self.p("register", name + ".head.json")) or read_json(
                self.p("register", "versions", name + ".head.json"))
            regs[name] = {"doc": doc, "head": head}
        if regs and any(r["head"] is None for r in regs.values()):
            # T1 records kept as lists of {file, key, head_object} (register/t1/*.json, t1/*.json)
            from prooflab.pack import history as _h
            heads = _h.t1_heads(self.root)
            for name, r in regs.items():
                h = heads.get(name + ".yaml")
                if r["head"] is None and h and h.get("last_modified"):
                    r["head"] = {"LastModified": h["last_modified"], "VersionId": h.get("version_id"), "Key": h.get("key")}
        return regs

    def control_entry(self, control, threshold_version=None, register_version=None):
        """(register name, entry dict) bound to an assessment, else (None, None)."""
        names = []
        if register_version in self.registers:
            names.append(register_version)
        names += [n for n in sorted(self.registers) if n not in names]
        for name in names:
            for e in self.registers[name]["doc"]["entries"]:
                if e.get("control_ref") == control and (threshold_version in (None, e.get("threshold_version"))):
                    return name, e
        return None, None

    def t1_for(self, threshold_version, control):
        """T1 proof of the FIRST register file that carried this threshold_version (ARCH 3.3)."""
        first = None
        for name in sorted(self.registers, key=lambda n: self._reg_date(n)):
            for e in self.registers[name]["doc"]["entries"]:
                if e.get("control_ref") == control and e.get("threshold_version") == threshold_version:
                    first = name
                    break
            if first:
                break
        if not first:
            return None, None
        return first, t1_text(self.registers[first]["head"])

    def t1_head(self, threshold_version, control):
        """(first register file carrying this threshold_version, its head-object dict or None)."""
        first, _ = self.t1_for(threshold_version, control)
        return first, (self.registers[first]["head"] if first else None)

    def _reg_date(self, name):
        top = self.registers[name]["doc"]["top"]
        return _utc_key(top.get("version_date")) or name

    def list_file(self, pattern):
        return sorted(glob.glob(self.p(*pattern)))


def _native_measured(m):
    """Map an evaluator's own measured keys onto value/unit/limit (the renderer's vocabulary); never invents a number.
    C16: total_tokens vs cap. C7: coverage_pct (share of the expected events observed). Existing value/unit/limit win."""
    if not isinstance(m, dict) or m.get("value") is not None:
        return m
    m = dict(m)
    if m.get("total_tokens") is not None:
        m["value"], m["unit"] = m["total_tokens"], m.get("unit") or "tokens"
        if m.get("limit") is None and m.get("cap") is not None:
            m["limit"] = m["cap"]
    elif m.get("coverage_pct") is not None:
        m["value"], m["unit"] = m["coverage_pct"], m.get("unit") or "% of expected events observed"
    return m


def normalize_assessment(doc):
    """Accept the contract dataclass dict or a flat `assessment` record; return one flat shape."""
    g = lambda *keys: next((doc[k] for k in keys if k in doc and doc[k] is not None), None)
    aid = g("assessment_id", "assessment.id", "record_id") or ""
    parts = str(aid).split(":", 3)
    ref = g("control_ref", "control.ref") or (parts[0] if len(parts) > 1 else None) or "?"
    tv = g("threshold_version", "threshold.version") or (parts[1] if len(parts) > 3 else None) or UNKNOWN
    kind = g("scope_kind", "assessment.scope_kind") or (parts[2] if len(parts) > 3 else None) or "run"
    scope = g("scope_id", "assessment.scope_id")
    rev = 1
    if len(parts) > 3:
        scope = scope or parts[3].rsplit(":r", 1)[0]
        m = re.search(r":r(\d+)$", parts[3])
        rev = int(m.group(1)) if m else 1
    scope = scope or g("run.id", "correlation_id") or UNKNOWN
    verdict = g("requirement_verdict", "assessment.requirement_verdict", "verdict")
    measured = doc.get("measured")
    if not isinstance(measured, dict):
        measured = {"value": g("measured.value"), "unit": g("measured.unit"), "source": g("measured.source")}
    measured = _native_measured(measured)
    limit = g("limit", "threshold.value")
    if limit is None and isinstance(measured, dict):
        limit = measured.get("limit")
    x = {}
    for k, v in doc.items():
        if k.startswith("assessment."):
            x[k[len("assessment."):]] = v
    def pick(name, default=None):
        val = doc.get(name, x.get(name))
        return default if val is None else val
    return {
        "assessment_id": aid, "rev": rev, "control_ref": norm_control(ref), "control_id": g("control_id", "control.id"),
        "threshold_version": tv, "register_version": g("register_version", "register.version"),
        "scope_kind": kind, "scope_id": scope,
        "scope_start": pick("scope_start", g("emitted.at", "ts")) if kind != "run" else pick("scope_start"),
        "scope_end": pick("scope_end"), "verdict": verdict or "NOT_ASSESSED",
        "design": pick("design"), "operation": pick("operation"), "deficiency": pick("deficiency"),
        "evidence_sufficiency": pick("evidence_sufficiency"), "measured": measured, "limit": limit,
        "exceptions": pick("exceptions", []), "denominators": pick("denominators", {}),
        "completeness": pick("completeness", {}), "gaps": pick("gaps", []), "evidence_refs": pick("evidence_refs", []),
        "as_of": g("as_of", "emitted.at", "ts"), "record_id": g("record_id"), "detail": g("detail"),
        "evaluator_name": g("evaluator_name", "evaluator.name"), "formula": pick("formula"),
    }


# ---------------------------------------------------------------- run facts
def run_known(pack, cid):
    return bool(cid in pack.by_cid or cid in pack.index_by_cid or cid in pack.catalogue_by_cid
                or any(a["scope_id"] == cid for a in pack.assessments))


def run_provenance(pack, cid):
    row = pack.index_by_cid.get(cid) or {}
    if row.get("provenance"):
        return row["provenance"]
    for r in pack.by_cid.get(cid, []):
        if r.get("record_kind") != "assessment" and r.get("provenance"):
            return r["provenance"]
    return UNKNOWN


def run_start(pack, cid, assessment=None):
    row = pack.index_by_cid.get(cid) or {}
    for key in ("first_span", "start", "first_seen", "t_start"):
        if row.get(key):
            return row[key]
    if assessment and assessment.get("scope_start"):
        return assessment["scope_start"]
    recs = [r for r in pack.by_cid.get(cid, []) if r.get("record_kind") != "assessment"]
    return recs[0].get("ts") if recs else None


def run_end(pack, cid):
    row = pack.index_by_cid.get(cid) or {}
    for key in ("last_span", "end", "last_seen", "t_end"):
        if row.get(key):
            return row[key]
    recs = [r for r in pack.by_cid.get(cid, []) if r.get("record_kind") != "assessment"]
    return recs[-1].get("ts") if recs else None


def _first(recs, field):
    for r in recs:
        if r.get(field) not in (None, ""):
            return r[field]
    return None


# ---------------------------------------------------------------- control test: per run
def recompute(pack, control, cid):
    """Optional evaluator recompute; None when the evaluator does not expose the pack entry point."""
    try:
        mod = importlib.import_module("prooflab.evaluators.%s" % control.lower())
    except ImportError:
        return None
    fn = getattr(mod, "recompute_from_pack", None)
    if fn is None:
        return None
    try:
        out = fn(pack, control, cid)
    except Exception as exc:     # a failing recompute is shown, never hidden
        return {"error": "%s: %s" % (type(exc).__name__, exc)}
    return out


def control_run(pack, control, cid, recompute_fn=None):
    """Answer dict for `query --control <C> --run <cid>`; answer['verdict'] drives the exit code."""
    control = norm_control(control)
    if control not in CONTROLS:
        return {"kind": "error", "verdict": "NOT_ASSESSED", "message": "unsupported control %r (C16, C7, C9)" % control}
    if not run_known(pack, cid):
        return {"kind": "error", "verdict": "NOT_ASSESSED", "message": "unknown run %s: not in this pack" % cid}
    recs = [r for r in pack.by_cid.get(cid, []) if r.get("record_kind") != "assessment"]
    found = pack.assessments_for(control, ("run",), cid)
    out = {"kind": "control-run", "control": control, "run": cid, "provenance": run_provenance(pack, cid),
           "gaps": []}
    if not found:
        out.update(verdict="NOT_ASSESSED", message="not assessed: no %s assessment for this run in the pack" % control)
        out["gaps"].append("no %s assessment for %s" % (control, cid))
        out["records"] = _ids(recs)
        return out
    a = sorted(found, key=lambda x: x["threshold_version"])[-1]
    rname, entry = pack.control_entry(control, a["threshold_version"], a["register_version"])
    entry = entry or {}
    t1_file, t1 = pack.t1_for(a["threshold_version"], control)
    out.update(verdict=a["verdict"], assessment=a, register_file=rname, rule_metric=entry.get("metric"),
               rule_basis=entry.get("measurement_basis"), control_version=a["threshold_version"],
               control_date=entry.get("version_date"), t1=t1, t1_file=t1_file,
               owner=entry.get("owner") or _first(recs, "control.owner"),
               run_start=run_start(pack, cid, a))
    if rname is None:
        out["gaps"].append("register version for %s not in the pack" % a["threshold_version"])
    out["date_proof"] = date_proof(pack, a["threshold_version"], control, out["run_start"])
    if t1 is None:
        out["gaps"].append("T1 date proof for %s missing (register/<v>.head.json)" % a["threshold_version"])
    elif out["date_proof"]["checksum_verified"] is False:
        out["gaps"].append("T1 date proof for %s does not match the register file: %s"
                           % (a["threshold_version"], out["date_proof"]["reason"]))
    out["gaps"] += [str(g) for g in (a["gaps"] or [])]
    t1_key, start_key = _utc_key(t1), _utc_key(out["run_start"])
    if t1_key and start_key and t1_key > start_key:      # G5 date check: the register must predate the run (ARCH 3.3)
        out["stored_verdict"] = out["verdict"]
        out["verdict"] = V.INDETERMINATE
        out["gaps"].append("date check failed: T1 proof %s is later than the run start %s; the stored verdict %s "
                           "is not a clean answer" % (t1, out["run_start"], a["verdict"]))
    ms = a["measured"] or {}
    mv, lv = _num(ms.get("value")), _num(a["limit"])
    out["measured"], out["limit"] = ms, a["limit"]
    out["overshoot"] = (mv - lv) if (mv is not None and lv is not None) else None
    if out["limit"] is None and entry.get("observation_limit") is not None:
        lv2 = _num(entry["observation_limit"])
        if lv2 is None and control == "C7":    # C7's numbers in one string (prooflab.evaluators.c7.limits_of reads it)
            from prooflab.evaluators import claim as _claim
            parts = _claim.parse_limits(entry["observation_limit"])
            if parts.get("coverage_min_pct") is not None:
                out["limit"] = ">= %s %% coverage (%s)" % (parts["coverage_min_pct"], ", ".join(
                    "%s %s" % (k, v) for k, v in sorted(parts.items()) if k != "coverage_min_pct"))
        elif lv2 is not None:
            out["limit"] = lv2
        if out["limit"] is not None:
            out["limit_source"] = "register/versions/%s.yaml %s observation_limit" % (rname, control)
    out["records"] = _ids(recs + [{"record_id": x} for x in [a["record_id"]] if x])
    out["actors"] = _actors(recs)
    try:
        inv_name, inv = _inventory(pack)
    except Exception:       # an unreadable inventory is a gap, never a crash
        inv_name, inv = None, None
    comps = dict((c.get("component_id"), c.get("approved_version")) for c in ((inv or {}).get("entries") or (inv or {}).get("components") or [])
                 if isinstance(c, dict))
    for x in out["actors"]:
        if not x.get("version") and comps.get(x.get("actor")):
            x["version"] = "%s (inventory %s)" % (comps[x["actor"]], inv_name)
    out["eps"] = _eps(recs)
    out["human_loop"] = _human_loop(pack, cid, recs)
    fn = recompute_fn or recompute
    rc = fn(pack, control, cid)
    if rc is None:
        out["recompute"] = "not available: no evaluator entry point in this pack; stored assessment shown"
    elif isinstance(rc, dict) and rc.get("error"):
        out["recompute"] = "FAILED: %s" % rc["error"]
    else:
        rv = rc.get("verdict") if isinstance(rc, dict) else getattr(rc, "requirement_verdict", None)
        out["recompute"] = ("matches stored verdict" if rv == a["verdict"]
                            else "MISMATCH: recomputed %s, stored %s (flagged difference)" % (rv, a["verdict"]))
    return out


def _actors(recs):
    seen, out = set(), []
    for r in recs:
        row = tuple(r.get(k) for k in ("actor.id", "actor.runtime_id", "actor.version", "principal.platform", "on_behalf_of"))
        if any(row) and row not in seen:
            seen.add(row)
            out.append(dict(zip(("actor", "runtime", "version", "principal", "on_behalf_of"), row)))
    return out


def _eps(recs):
    out = []
    for r in recs:
        if r.get("ep.id") or r.get("record_kind") in ("decision", "platform_decision"):
            out.append({"ep": r.get("ep.id"), "kind": r.get("record_kind"), "verdict": r.get("verdict"),
                        "action": r.get("inline.action"), "mode": r.get("inline.mode"),
                        "responsible": r.get("ep.responsible"), "record_id": r.get("record_id")})
    return out


def _human_loop(pack, cid, recs):
    hl = [r for r in recs if r.get("record_kind") in ("finding", "notification")]
    return [{"kind": r["record_kind"], "verdict": r.get("verdict"), "detail": r.get("detail"),
             "record_id": r.get("record_id")} for r in hl]


# ---------------------------------------------------------------- control test: per window
def parse_window(text):
    if ".." not in str(text):
        return None
    t1, t2 = str(text).split("..", 1)
    return (t1, t2) if _utc_key(t1) and _utc_key(t2) and _utc_key(t1) < _utc_key(t2) else None


def tolerance(entry, counted):
    """(allowed breached-run count, note). exception_tolerance: a count, or a percentage of counted runs."""
    raw = (entry or {}).get("exception_tolerance")
    if raw is None:
        return None, "exception_tolerance missing in the register"
    text = str(raw).strip()
    n = _num(text.rstrip("%").strip())
    if n is None:
        return None, "exception_tolerance %r not numeric" % text
    return (n * counted / 100.0 if text.endswith("%") else n), None


def control_window(pack, control, window):
    control = norm_control(control)
    if control not in CONTROLS:
        return {"kind": "error", "verdict": "NOT_ASSESSED", "message": "unsupported control %r (C16, C7, C9)" % control}
    bounds = parse_window(window)
    if not bounds:
        return {"kind": "error", "verdict": "NOT_ASSESSED", "message": "--window needs <T1>..<T2> in full UTC (…Z), T1 < T2"}
    lo, hi = _utc_key(bounds[0]), _utc_key(bounds[1])
    kinds = ("run", "window", "hour") if control == "C9" else ("run",)     # C9's hourly roll-up: scope_kind window
    counted, listed, gaps = [], [], []
    seen_runs = set()
    for a in pack.assessments_for(control, kinds):
        start = _utc_key(a["scope_start"] or run_start(pack, a["scope_id"], a))
        if start is None or not (lo <= start < hi):
            continue
        prov = run_provenance(pack, a["scope_id"]) if a["scope_kind"] == "run" else None
        seen_runs.add(a["scope_id"])
        if prov is not None and prov not in WINDOW_PROVENANCE:
            listed.append({"scope": a["scope_id"], "reason": "not assessed by provenance (%s)" % prov})
        elif a["verdict"] == "NOT_ASSESSED":
            listed.append({"scope": a["scope_id"], "reason": "assessment is NOT_ASSESSED"})
        else:
            counted.append(a)
    for row in pack.run_index:   # in-window runs of an in-scope provenance with no assessment: listed, not counted
        cid = _cid(row)
        st = _utc_key(run_start(pack, cid))
        if cid and cid not in seen_runs and st and lo <= st < hi:
            prov = run_provenance(pack, cid)
            listed.append({"scope": cid, "reason": ("no %s assessment for this run (version has no entry, or not assessed)" % control)
                           if prov in WINDOW_PROVENANCE else "not assessed by provenance (%s)" % prov})
    by_version = {}
    for a in counted:
        by_version.setdefault(a["threshold_version"], []).append(a)
    per_version, breached_over, indeterminate = [], False, False
    for tv in sorted(by_version):
        runs = by_version[tv]
        _, entry = pack.control_entry(control, tv, runs[0]["register_version"])
        n_b = len([a for a in runs if a["verdict"] == "BREACHED"])
        tol, note = tolerance(entry, len(runs))
        if n_b and tol is None:
            indeterminate = True
            gaps.append("%s: %s" % (tv, note))
        elif tol is not None and n_b > tol:
            breached_over = True
        per_version.append({"threshold_version": tv, "counted": len(runs), "breached": n_b,
                            "tolerance": (entry or {}).get("exception_tolerance"), "tolerance_note": note})
    if any(a["verdict"] == "INDETERMINATE" for a in counted):
        indeterminate = True
    verdict = ("NOT_ASSESSED" if not counted else "BREACHED" if breached_over
               else "INDETERMINATE" if indeterminate else "SATISFIED")
    if verdict == "NOT_ASSESSED":
        gaps.append("no run in scope: empty denominator, not 100%")
    return {"kind": "control-window", "control": control, "window": [bounds[0], bounds[1]], "verdict": verdict,
            "counted": counted, "listed": listed, "per_version": per_version, "gaps": gaps,
            "window_rule": "E-06 (query engine; ARCH 3.4)"}


# ---------------------------------------------------------------- incident: the six questions
def resolve_incident(pack, ident):
    """(cid, note) for a CID or a UTC time; (None, reason) when nothing matches."""
    if run_known(pack, ident):
        return ident, None
    key = _utc_key(ident)
    if not key:
        return None, "unknown incident %r: not a run id in this pack and not a UTC time" % ident
    spans = []
    for cid in set(list(pack.index_by_cid) + list(pack.by_cid)):
        st, en = _utc_key(run_start(pack, cid)), _utc_key(run_end(pack, cid))
        if st:
            spans.append((st, en or st, cid))
    inside = sorted([s for s in spans if s[0] <= key <= s[1]])
    if inside:
        return inside[0][2], "time %s falls inside this run" % ident
    before = sorted([s for s in spans if s[0] <= key])
    if before:
        return before[-1][2], "no run spans %s; nearest earlier run shown" % ident
    return None, "no run at or before %s in this pack" % ident


def _inventory(pack):
    # `registry inventory` freezes to register/versions/inv-N.yaml; register/inventory/*.yaml is the older layout
    paths = pack.list_file(("register", "inventory", "*.yaml")) + sorted(
        pack.list_file(("register", "versions", "inv-*.yaml")),
        key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", os.path.basename(p))])
    for path in reversed(paths):
        try:
            return os.path.basename(path)[:-5], P.parse_inventory(open(path, "rb").read().decode("utf-8"))
        except (ValueError, IOError, OSError):
            continue
    return None, None


def _q(name, lines, recs, limit, gap=None):
    shown, more = _ids(recs)
    return {"q": name, "lines": lines or [("%s (gap: %s)" % (UNKNOWN, gap or "no evidence in the pack"))],
            "records": shown, "more": more, "limit": limit, "gap": gap if not lines else None}


def incident(pack, ident):
    cid, note = resolve_incident(pack, ident)
    if cid is None:
        return {"kind": "error", "verdict": "NOT_ASSESSED", "message": note}
    recs = [r for r in pack.by_cid.get(cid, []) if r.get("record_kind") != "assessment"]
    cat = pack.catalogue_by_cid.get(cid) or {}
    label = cat.get("label") or cat.get("source")
    ours = cid.startswith("ifabric-") or str(label or "").lower().startswith("ours")
    prov = run_provenance(pack, cid)
    out = {"kind": "incident", "verdict": "RECORDED", "run": cid, "note": note, "label": run_label(pack, cid, label, prov) or UNKNOWN,
           "provenance": prov, "start": run_start(pack, cid), "end": run_end(pack, cid)}
    if not ours:
        inv_name, _ = _inventory(pack)
        out["out_of_scope"] = ("out of scope (scope_rule, inventory version %s); seen: %d records, label %s"
                               % (inv_name or UNKNOWN, len(recs), label or UNKNOWN))
        out["questions"] = []
        return out
    inv_name, inv = _inventory(pack)
    comp = dict((e.get("component_id"), e) for e in (inv or {"entries": []})["entries"])
    actors = _actors(recs)
    who = ["actor %s on %s v%s, principal %s, on behalf of %s" % tuple(x or UNKNOWN for x in (
        a["actor"], a["runtime"], a["version"], a["principal"], a["on_behalf_of"])) for a in actors]
    owns = sorted(set("%s owned by %s" % (a["actor"], (comp.get(a["actor"]) or {}).get("owner") or UNKNOWN)
                      for a in actors if a["actor"]))
    for ctl in sorted(set(r.get("control.ref") for r in recs if r.get("control.owner"))):
        owns.append("control %s owner %s" % (ctl, _first([r for r in recs if r.get("control.ref") == ctl], "control.owner")))
    what = sorted(set(["model %s" % r["model.id"] for r in recs if r.get("model.id")]
                      + ["tool %s%s" % (r["tool.name"], "" if r.get("tool.declared") in (None, True) else " (undeclared)")
                         for r in recs if r.get("tool.name")]))
    authz = ["%s %s %s -> real outcome %s" % (r.get("ep.id"), r.get("record_kind"), r.get("verdict"), r.get("outcome.real") or UNKNOWN)
             for r in recs if r.get("record_kind") == "platform_decision"]
    appr = ["%s %s %s" % (r.get("ep.id"), r.get("record_kind"), r.get("verdict"))
            for r in recs if r.get("record_kind") == "approval" or r.get("ep.id") in ("EP-0", "EP-10")]
    manifest = os.path.exists(pack.p("MANIFEST.json"))
    corr = read_json(pack.p("derived", "corroboration", cid + ".json"))
    integ = ["MANIFEST.json %s" % ("present" if manifest else "not yet written when this view was built (it is written last at pack build; verify: python3 tools/manifest.py verify .)"),
             ("corroboration report: %s mismatches" % len(corr.get("mismatches", []))) if isinstance(corr, dict)
             else "no corroboration report for this run (gap)"]
    timeline = ["%s %s %s %s" % (r.get("ts"), r.get("record_kind"), r.get("ep.id") or "-", r.get("record_id")) for r in recs]
    cap = 12
    if len(timeline) > cap:
        timeline = timeline[:cap] + ["... %d more in store/records.jsonl" % (len(timeline) - cap)]
    pick = lambda pred: [r for r in recs if pred(r)]
    out["questions"] = [
        _q("WHO acted", who, pick(lambda r: r.get("actor.id")), "One shared platform principal (gap 2); an AWS record names a role, not a person"),
        _q("WHO owns it", owns, pick(lambda r: r.get("control.owner") or r.get("component.owner")),
           "Platform components' owners are our declaration (inventory %s)" % (inv_name or UNKNOWN)),
        _q("WHAT it touched", what, pick(lambda r: r.get("model.id") or r.get("tool.name")),
           "Undeclared tools are allowed unless a Cedar rule forbids them (gap 3)"),
        _q("AUTHORIZED", authz, pick(lambda r: r.get("record_kind") == "platform_decision"),
           "The platform records blocks and pauses as ALLOW (gap 4)", None if authz else "no platform_decision records"),
        _q("APPROVED", appr, pick(lambda r: r.get("record_kind") == "approval" or r.get("ep.id") in ("EP-0", "EP-10")),
           "Approvals are self-asserted (gap 5)", None if appr else "no approval or EP-0 records"),
        _q("INTEGRITY", integ, [], "Corroboration, not proof (gap 6)"),
        _q("RECONSTRUCT", timeline, recs, "Refusals carry no run id (gap 7): joined by trace id", None if recs else "no records"),
    ]
    return out


# ---------------------------------------------------------------- listings
def declared_fault_kinds(pack):
    """The fault kinds the frozen pins declare (c7.declared_faults, `<kind>:<agent>:<event>:<n>`): ARCH 5.5."""
    kinds = []
    for path in pack.list_file(("register", "pins", "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (IOError, OSError, ValueError):
            continue
        for f in ((doc.get("c7") or {}).get("declared_faults") or []) if isinstance(doc, dict) else []:
            k = str(f).split(":", 1)[0]
            if k and k not in kinds:
                kinds.append(k)
    return kinds


def run_label(pack, cid, label, provenance):
    """ONE label per run for the CLI and the console. A run whose records carry FAULT_INJECTION is a LIVE_SUBJECT with a
    DECLARED fault (ARCH 5.5), never 'role undeclared': the label names the declared fault kind."""
    if provenance == "FAULT_INJECTION" and str(label or "") in ("", "OURS-ROLE-UNDECLARED", "unlabelled (gap)"):
        kinds = declared_fault_kinds(pack)
        # a suppressed record shows up as a missing C7 event; an injected tool output removes none: narrow to the kind the run shows
        try:
            missing = any(x.get("kind") == "missing-event" for a in pack.assessments_for("C7", ("run",))
                          if a.get("scope_id") == cid for x in (a.get("exceptions") or []))
        except Exception:
            missing = False
        if missing and "suppress-record" in kinds:
            kinds = ["suppress-record"]
        return "declared fault: " + (", ".join(kinds) if kinds else "kind not recorded (no pin declares one)")
    return label


def runs_list(pack):
    """Catalogue rows (honestly labelled); falls back to the run index, then to CIDs seen in the store."""
    rows, src = [], None
    if pack.catalogue:
        src, base = "derived/run-catalogue.jsonl", pack.catalogue
    elif pack.run_index:
        src, base = "derived/run-index.jsonl (no run catalogue in this pack)", pack.run_index
    else:
        src, base = "store/records.jsonl only (no run index or catalogue in this pack)", [{"cid": c} for c in sorted(pack.by_cid)]
    for r in base:
        cid = _cid(r)
        idx = pack.index_by_cid.get(cid) or {}
        prov = r.get("provenance") or idx.get("provenance") or run_provenance(pack, cid)
        rows.append({"cid": cid, "label": run_label(pack, cid, r.get("label") or r.get("source") or "unlabelled (gap)", prov),
                     "provenance": prov,
                     "phase": r.get("phase") or idx.get("phase") or UNKNOWN,
                     "condition": r.get("condition") or idx.get("condition") or r.get("run.condition"),
                     "version": r.get("register_version") or idx.get("register_version"),
                     "assessed": r.get("assessed"),
                     "start": run_start(pack, cid)})
    rows.sort(key=lambda r: (_utc_key(r["start"]) or "", r["cid"]))
    return {"kind": "runs", "verdict": "RECORDED", "source": src, "rows": rows, "window": pack.window}


def risk_list(pack, risk_id=None):
    out = []
    for path in pack.list_file(("register", "versions", "*.risks.yaml")):
        try:
            doc = P.parse_risks(open(path, "rb").read().decode("utf-8"))
        except (ValueError, IOError, OSError):
            continue
        for e in doc["entries"]:
            if risk_id in (None, "", e.get("risk_id")):
                linked = [a for a in pack.assessments if a["control_ref"] and e.get("risk_id") and
                          (pack.control_entry(a["control_ref"], a["threshold_version"])[1] or {}).get("risk_ref") == e["risk_id"]]
                out.append(dict(e, file=os.path.basename(path), linked=sorted(set((a["control_ref"], a["scope_id"], a["verdict"]) for a in linked))))
    return {"kind": "risk", "verdict": "RECORDED" if out else "NOT_ASSESSED", "rows": out,
            "message": None if out else "no risk %s in this pack (register/versions/*.risks.yaml)" % (risk_id or "")}


def inventory_list(pack):
    name, doc = _inventory(pack)
    if not doc:
        return {"kind": "inventory", "verdict": "NOT_ASSESSED", "rows": [], "message": "no inventory in this pack (register/versions/inv-*.yaml)"}
    return {"kind": "inventory", "verdict": "RECORDED", "version": name, "top": doc["top"], "rows": doc["entries"]}


def claim_line(pack):
    rows, counts = [], 0
    for c in CONTROLS:
        found = pack.assessments_for(c, ("run",))
        worst = None
        for a in found:
            worst = a["verdict"] if worst is None or ["SATISFIED", "INDETERMINATE", "NOT_ASSESSED", "BREACHED"].index(a["verdict"]) > \
                ["SATISFIED", "INDETERMINATE", "NOT_ASSESSED", "BREACHED"].index(worst) else worst
        rows.append({"control": c, "runs": len(found), "worst": worst or "NOT_ASSESSED"})
        counts += 1 if any(a["verdict"] != "NOT_ASSESSED" for a in found) else 0   # a NOT_ASSESSED file is not coverage
    top = (pack.registers[sorted(pack.registers)[-1]]["doc"]["top"] if pack.registers else {})
    return {"kind": "claim", "verdict": "RECORDED", "claim_id": top.get("claim_id") or "C-FM-01", "rows": rows,
            "coverage": "full coverage: %d of %d controls assessed" % (counts, len(CONTROLS)) if counts == len(CONTROLS)
            else "partial coverage: %d of %d controls assessed" % (counts, len(CONTROLS))}


def exit_for(answer):
    v = answer.get("verdict")
    if answer.get("kind") == "error":
        return 2
    if v in V.ASSESSMENT_VERDICTS:
        return V.exit_code(v)
    return 0

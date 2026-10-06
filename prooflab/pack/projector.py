"""The one-way pack projector (G-07, T5.3): our pack's source tree -> the Evidence Console's contract files. Stdlib, 3.9.

  python3 -m prooflab.pack.projector --src <pack source tree> --out <projection dir> [--as-of <UTC>]

READS  <src>/store/records.jsonl, <src>/assessments/*/*.json, <src>/run-ids.txt, <src>/window.json,
       <src>/derived/run-catalogue.jsonl, <src>/register/versions/*.yaml (+ <name>.head.json), <src>/MANIFEST.json,
       <src>/servicenow/cases/*.json, <src>/claim.json (optional: id, text, summary)
WRITES <out>/pack-index.json, records/<run>/<evidence id>.json, assessments/<control>/<id>.json   (the first slice)
       and a report (returned; written to <out>/projection-report.json) listing what was NOT projected and why.
ONE WAY: `out` must not be (or contain) `src`; nothing in prooflab/ reads the projection back; a projected file is
never an input to a verdict. Mapping tables: architecture/work/12-handoff3-reconciliation.md section 5.4 (G-07).

Not in this slice (P1; see the PR's open issues): runs/<cid>/run.json, auditor/, gaps/, adversarial/, levels, answers
(G-08). INV, APPROVAL and PLATFORM records are not projected as records or findings (they show as EP rows).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

from prooflab.pack import index as _index
from prooflab.contract import verdicts as _V  # the one verdict vocabulary (ARCH §4.3)

PROJ_SCHEMA_RECORD = "ifabric.evidence/v1"
PROJ_SCHEMA_ASSESSMENT = "ifabric.assessment/v1"
PROJECTED_CONTROLS = ("C16", "C7", "C9", "ESC")
NOT_PROJECTED_CONTROLS = ("INV", "APPROVAL", "PLATFORM")
KIND_MAP = {"model": "model-call", "tool": "tool-call", "handoff": "event", "lifecycle": "event", "judgment": "event",
            "notification": "event", "metric": "window", "decision": "decision", "approval": "approval"}
PROV_BY_VALUE = {"LIVE_SUBJECT": "ASSESSED", "EXPLORATORY": "EXPLORATORY", "PILOT": "EXPLORATORY",
                 "BASELINE": "EXPLORATORY", "AUTHORIZED_TEST": "EXPLORATORY", "FAULT_INJECTION": "EXPLORATORY",
                 "REPLAY": "EXPLORATORY", "COUNTERFACTUAL_EXPORT": "EXPLORATORY", "UNATTRIBUTED": "EXPLORATORY",
                 "WIRING_TEST": "WIRING_TEST"}
CLOCK_MAP = {"agent-runtime": "agent", "script-host": "orchestrator", "evaluator-host": "orchestrator",
             "gateway": "gateway", "pdp": "pdp", "authz": "pdp", "audit-store": "ledger",
             "cloudwatch-ingest": "cloudwatch", "aws-cloudtrail": "cloudwatch", "servicenow": "servicenow",
             "s3": "capture"}
SURFACE_BY_REF = (("gateway:", "gateway-stdout"), ("ledger:", "ledger"), ("span", "spans"), ("cloudwatch:", "spans"),
                  ("xray:", "xray"), ("pdp:", "pdp"), ("aict", "aict-invocations"), ("servicenow:", "servicenow"),
                  ("cr:", "cr-status"), ("register:", "register"), ("expected:", "expected"), ("raw:", "adapter"))
CONTROL_LIBRARY = {"C16": "ACN-COST-001", "C7": "AIA-LOG-001", "C9": "AIA-ARC-006", "ESC": "AGENT-ESCALATION"}
ASSESSMENT_VERDICTS = _V.ASSESSMENT_VERDICTS
SCOPE_KINDS = ("run", "window", "interval", "incident", "escalation")
UTC_RE = _index.UTC_RE


# ------------------------------------------------------------------ reading (source tree only)
def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (IOError, OSError, ValueError):
        return None


def _read_jsonl(path):
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(row, dict):
                        rows.append(row)
    except (IOError, OSError):
        pass
    return rows


def _read_bytes(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except (IOError, OSError):
        return None


def safe(text):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(text))


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def parse_run_ids(text):
    """run-ids.txt -> {cid: alias}. One line per run: `<cid>`, or `<alias> <cid>` / `<alias>=<cid>` (either order)."""
    out = {}
    for line in (text or "").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        toks = [t for t in re.split(r"[\s=,]+", line) if t]
        cid = next((t for t in toks if t.startswith(("ifabric-", "fault-"))), toks[-1])
        alias = next((t for t in toks if t != cid), cid)
        out[cid] = alias
    return out


def _utc(v):
    return v if isinstance(v, str) and UTC_RE.match(v) else None


# ------------------------------------------------------------------ mapping tables
def provenance_of(rec_provenance, run_id, assessed):
    """Membership first (run-ids.txt), whatever the record says; then by value. SYNTHETIC -> None (never in the pack)."""
    if run_id in assessed:
        return "ASSESSED"
    if rec_provenance == "SYNTHETIC":
        return None
    return PROV_BY_VALUE.get(rec_provenance, "EXPLORATORY")


def record_kind_of(rec):
    k = rec.get("record_kind")
    if k == "action":
        return "tool-call" if (rec.get("tool.name") or rec.get("tool.args_sha256")) and not rec.get("model.id") else "model-call"
    return KIND_MAP.get(k)


def infer_control(rec, kind):
    """Which control a record is evidence for when it names none: model calls -> C16, handoffs and judgments -> C7,
    metrics -> C9, EP-1 decisions -> C16. Anything else (EP-0 and approvals, platform records) is not bound."""
    if kind == "model-call":
        return "C16"
    if kind == "decision":
        return "C16" if rec.get("ep.id") == "EP-1" else None
    if kind == "event":
        return None if rec.get("record_kind") == "notification" else "C7"
    if kind == "tool-call":
        return "C7"
    if kind == "window":
        return "C9"
    return None


def decision_of(rec):
    """Inline decision -> ALLOW | ALERT | DENY | None (DENY under observe is an ALERT)."""
    verdict = rec.get("verdict")
    if rec.get("record_kind") not in ("decision", "platform_decision") and not rec.get("inline.mode"):
        return None
    if verdict == "DENY" or rec.get("inline.action") in ("halt", "decline-start"):
        return "ALERT" if rec.get("inline.mode") in ("observe", "record-only") else "DENY"
    if verdict == "ALLOW" or rec.get("inline.action") == "proceed":
        return "ALLOW"
    return None


def _surface(refs, rec):
    for ref in refs:
        for prefix, surface in SURFACE_BY_REF:
            if ref.startswith(prefix):
                return surface
    return "orchestrator" if str(rec.get("emitter") or "").startswith(("prooflab", "orchestr")) else "adapter"


def disposition_of(rec):
    """J2 judgment fields -> the schema's names; the budget halt escalation -> halted-by-budget."""
    out = {}
    if rec.get("reason") == "c16-budget-halt":
        out["disposition"] = "halted-by-budget"
    if rec.get("deciding_evidence"):
        out["cited_evidence"] = rec["deciding_evidence"]
    if rec.get("reversible_step"):
        out["reversible_action"] = rec["reversible_step"]
    if rec.get("reason"):
        out["rationale"] = str(rec["reason"])[:400]
    return out


# ------------------------------------------------------------------ context loading
def _flat_parse(text):
    """Fallback for the flat register subset (top-level `key: value`, then `controls:` and `- control_id:` entries)
    when prooflab.registry.parse is not importable. Values stay strings; it never raises."""
    top, entries, cur, in_list = {}, [], None, False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        body = line.strip()
        if not line[:1].isspace() and body.rstrip(":") == "controls" and body.endswith(":"):
            in_list = True
            continue
        if body.startswith("- "):
            if cur is not None:
                entries.append(cur)
            cur = {}
            body = body[2:]
        if ":" not in body:
            continue
        k, v = body.split(":", 1)
        v = v.strip()
        if " #" in v:
            v = v.split(" #", 1)[0].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        (cur if (in_list and cur is not None) else top)[k.strip()] = v
    if cur is not None:
        entries.append(cur)
    return {"top": top, "entries": entries}


def load_register_ctx(src):
    """(register ctx, controls-by-ref, versions) from register/versions/*.yaml. Uses prooflab.registry.parse when it
    is importable (PR-01), else the flat fallback above; the sha256 is over the file bytes either way."""
    try:
        from prooflab.registry import parse as _parse
        parse = _parse.parse_register
    except ImportError:
        parse = None
    best = None
    for path in sorted(glob.glob(os.path.join(src, "register", "versions", "*.yaml"))):
        data = _read_bytes(path)
        if data is None or os.path.basename(path).endswith(".risks.yaml"):
            continue
        try:
            text = data.decode("utf-8")
            doc = parse(text) if parse else _flat_parse(text)
        except (ValueError, UnicodeDecodeError):
            continue
        best = (path, data, doc)   # the last (highest-named) file is the current one
    if not best:
        return None, {}, []
    path, data, doc = best
    controls = {}
    for e in doc["entries"]:
        ref = e.get("control_ref")
        if ref in CONTROL_LIBRARY:
            controls[ref] = e
    ctx = {"top": doc["top"], "sha256": hashlib.sha256(data).hexdigest(), "path": os.path.relpath(path, src),
           "entries": doc["entries"]}
    return ctx, controls, [{"version": doc["top"].get("version"), "path": os.path.relpath(path, src)}]


def load_context(src, as_of=None):
    records = _read_jsonl(os.path.join(src, "store", "records.jsonl"))
    run_ids = parse_run_ids((_read_bytes(os.path.join(src, "run-ids.txt")) or b"").decode("utf-8", "replace"))
    assessments = [r for r in records if r.get("record_kind") == "assessment"]
    for path in sorted(glob.glob(os.path.join(src, "assessments", "*", "*.json"))):
        doc = _read_json(path)
        if isinstance(doc, dict):
            assessments.append(doc)
    catalogue = _read_jsonl(os.path.join(src, "derived", "run-catalogue.jsonl"))
    reg, reg_controls, reg_versions = load_register_ctx(src)
    return {"src": src, "records": [r for r in records if r.get("record_kind") != "assessment"],
            "assessments_in": assessments, "run_ids": run_ids, "catalogue": catalogue,
            "window": _read_json(os.path.join(src, "window.json")) or {}, "register": reg,
            "register_controls": reg_controls, "register_versions": reg_versions,
            "claim": _read_json(os.path.join(src, "claim.json")) or {}, "as_of": as_of}


# ------------------------------------------------------------------ assessments
def _flat(doc):
    """A contract Assessment dict, or a flat `assessment.*` record -> one flat dict."""
    x = dict(doc)
    for k, v in doc.items():
        if k.startswith("assessment."):
            x.setdefault(k[len("assessment."):], v)
    return x


def _limit(entry, key, unit):
    return _index.limit_of(dict(entry, metric_unit=entry.get("metric_unit") or unit) if key == "observation_limit"
                           else dict(entry, limit_direction="<=", metric_unit=entry.get("exception_unit") or unit), key, unit)


def project_assessment(doc, cx, report):
    a = _flat(doc)
    aid = a.get("assessment_id")
    ref = a.get("control_ref") or a.get("control.ref")
    if ref in NOT_PROJECTED_CONTROLS or ref not in PROJECTED_CONTROLS:
        report["skipped_assessments"].append({"id": aid, "why": "control %s is not projected" % ref})
        return None
    kind = a.get("scope_kind")
    if kind not in SCOPE_KINDS:
        report["skipped_assessments"].append({"id": aid, "why": "scope kind %r is not in the schema" % kind})
        return None
    tv = a.get("threshold_version")
    entry = (cx["register_controls"] or {}).get(ref) or {}
    if entry.get("threshold_version") not in (None, tv):
        entry = next((e for e in (cx["register"] or {}).get("entries", []) if e.get("control_ref") == ref
                      and e.get("threshold_version") == tv), {})
    m = a.get("measured") if isinstance(a.get("measured"), dict) else {}
    unit = m.get("unit") or entry.get("metric_unit") or "unit"
    obs = _limit(entry, "observation_limit", unit)
    if obs is None and isinstance(m.get("limit"), (int, float)):
        obs = {"value": m["limit"], "operator": "<=", "unit": unit}
    exc = _limit(entry, "exception_tolerance", "exceptions") if entry else None
    if obs is None or exc is None:
        report["skipped_assessments"].append({"id": aid, "why": "no register limits for %s %s (cannot state the threshold honestly)" % (ref, tv)})
        return None
    reg_sha = a.get("threshold_sha256") if _index.SHA_RE.match(str(a.get("threshold_sha256") or "")) else (cx["register"] or {}).get("sha256")
    if not reg_sha:
        report["skipped_assessments"].append({"id": aid, "why": "no register sha256"})
        return None
    scope_id = a.get("scope_id") or a.get("run.id")
    scope = {"kind": kind, "id": str(scope_id)}
    if kind == "run":
        scope["cid"] = str(scope_id)
        alias = cx["run_ids"].get(scope_id)
        if alias:
            scope["alias"] = alias
    for k_out, k_in in (("start", "scope_start"), ("end", "scope_end")):
        if _utc(a.get(k_in)):
            scope[k_out] = a[k_in]
    if kind == "run":
        prov = provenance_of(cx["run_prov"].get(scope_id), scope_id, cx["run_ids"]) or "EXPLORATORY"
    else:
        prov = "ASSESSED" if any(rid in cx["run_ids"] for rid in (a.get("evidence_refs") or [])) or cx["run_ids"] else "EXPLORATORY"
    den = a.get("denominators") if isinstance(a.get("denominators"), dict) else {}
    exp = den.get("expected")
    if isinstance(exp, dict):
        expected = {"count": int(exp.get("count") or 0), "source": str(exp.get("source") or "assessment denominators")}
    else:
        expected = {"count": int(exp) if isinstance(exp, (int, float)) else 0,
                    "source": "assessment denominators" if isinstance(exp, (int, float)) else "not supplied"}
    population = {"expected": expected}
    for k in ("observed", "matched", "missing"):
        population[k] = int(den.get(k) or 0)
    measured = {"value": m.get("value") if isinstance(m.get("value"), (int, float)) and not isinstance(m.get("value"), bool) else None,
                "unit": unit}
    for k, t in (("breakdown", dict), ("series", list), ("by_actor", list)):
        if isinstance(m.get(k), t):
            measured[k] = m[k]
    verdict = a.get("requirement_verdict") or a.get("verdict")
    verdict = verdict if verdict in ASSESSMENT_VERDICTS else _V.NOT_ASSESSED
    gaps = []
    for i, g in enumerate(a.get("gaps") or []):
        gaps.append(g if isinstance(g, dict) and "id" in g and "text" in g else {"id": "g%d" % (i + 1), "text": str(g)})
    out = {
        "schema": PROJ_SCHEMA_ASSESSMENT, "assessment_id": aid, "revision": int(a.get("revision") or _rev(aid)),
        "control_ref": ref, "control_id": CONTROL_LIBRARY[ref], "threshold_version": tv,
        "register_version": a.get("register_version") or (cx["register"] or {}).get("top", {}).get("version") or "UNKNOWN",
        "threshold": {"observation_limit": obs, "exception_tolerance": exc,
                      "source_ref": "register:%s" % ((cx["register"] or {}).get("path") or tv), "register_sha256": reg_sha},
        "owner": _index.person(entry.get("owner_name"), entry.get("owner")),
        "scope": scope, "provenance": prov, "population": population, "measured": measured, "verdict": verdict,
        "formula": str(a.get("formula") or "not supplied"),
        "evaluator": {"name": str(a.get("evaluator_name") or "unknown"),
                      "version": (str(a.get("evaluator_sha256") or "")[:12] or "unversioned"), "kind": "control-test"},
        "evaluated_at": a.get("as_of") if _utc(a.get("as_of")) else (cx["as_of"] or ""),
        "evidence_refs": _index.good_refs(a.get("evidence_refs")),
        "exceptions": [e for e in (a.get("exceptions") or []) if isinstance(e, dict) and "id" in e and "why" in e],
        "gaps": gaps,
    }
    fnd = a.get("finding")
    if isinstance(fnd, dict) and all(k in fnd for k in ("control_ref", "control_id", "threshold_version", "scope_kind",
                                                       "scope_id", "verdict", "summary", "detected_at")):
        out["finding"] = fnd
    elif "finding" in a:
        out["finding"] = None
    return out


def _rev(aid):
    m = re.search(r":r(\d+)$", str(aid or ""))
    return int(m.group(1)) if m else 1


def latest_revisions(assessments):
    """Corrections replace, they don't add: keep the highest revision per (control, version, scope kind, scope id)."""
    best = {}
    for d in assessments:
        a = _flat(d)
        key = (a.get("control_ref"), a.get("threshold_version"), a.get("scope_kind"), a.get("scope_id"))
        old = best.get(key)
        if old is None or _rev(a.get("assessment_id")) >= _rev(_flat(old).get("assessment_id")):
            best[key] = d
    return [best[k] for k in sorted(best, key=lambda k: tuple(str(x) for x in k))]


# ------------------------------------------------------------------ records
class RawLines(object):
    """The exact captured lines a record's raw_ref can point at, so the console resolves it and the browser can
    recompute its sha256: store/records.jsonl by record_id, raw/**/*.jsonl lines by gateway action id."""

    def __init__(self, src):
        self.src = src
        self.store = {}
        for n, text in enumerate(self._lines(os.path.join(src, "store", "records.jsonl")), 1):
            try:
                rid = json.loads(text).get("record_id")
            except (ValueError, AttributeError):
                continue
            if rid and rid not in self.store:
                self.store[rid] = (n, text)
        self.files = {}

    @staticmethod
    def _lines(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read().split("\n")
        except (IOError, OSError):
            return []

    def file_lines(self, rel):
        if rel not in self.files:
            full = os.path.normpath(os.path.join(self.src, rel))
            ok = rel.startswith("raw/") and full.startswith(os.path.join(self.src, "raw") + os.sep)
            self.files[rel] = self._lines(full) if ok else []
        return self.files[rel]

    def find(self, rel, needle):
        for n, text in enumerate(self.file_lines(rel), 1):
            if text and (needle is None or ('"%s"' % needle) in text or ('\\"%s\\"' % needle) in text):
                return n, text
        return None

    def span(self, act, cid=None):
        pats = (["raw/aws-spans/%s/spans.jsonl" % cid] if cid else []) + sorted(
            os.path.relpath(p, self.src) for p in glob.glob(os.path.join(self.src, "raw", "aws-spans", "*", "*.jsonl")))
        for rel in pats:
            hit = self.find(rel, act)
            if hit:
                return rel, hit[0], hit[1]
        return None


def resolve_raw(refs, r, rec_id, lines):
    """(raw_ref, line text or None): the first ref the console can serve, pointing at one exact captured line."""
    cid = r.get("run.id") or r.get("correlation_id")
    for ref in refs:
        if ref.startswith("gateway-span:"):
            hit = lines.span(ref.split(":", 1)[1], cid)
            if hit:
                return "raw:%s#L%d" % (hit[0], hit[1]), hit[2]
        elif ref.startswith("raw:"):
            rel, _, ln = ref[4:].partition("#L")
            if ln.isdigit():
                got = lines.file_lines(rel)
                if 0 < int(ln) <= len(got) and got[int(ln) - 1]:
                    return ref, got[int(ln) - 1]
            else:
                hit = lines.find(rel, r.get("call.id")) or lines.find(rel, None)
                if hit:
                    return "raw:%s#L%d" % (rel, hit[0]), hit[1]
    if rec_id in lines.store:
        return "record:%s" % rec_id, lines.store[rec_id][1]
    return (refs[0] if refs else "record:%s" % rec_id), None


def project_records(cx, projected_assessments, report, lines=None):
    """Yield (relative path, evidence record). C16: cumulative run tokens after each call (MC-33)."""
    by_run = {}
    for a in projected_assessments:
        by_run.setdefault((a["scope"].get("cid") or a["scope"]["id"]), {})[a["control_ref"]] = a
    cum = {}
    ordered = sorted(cx["records"], key=lambda r: (str(r.get("ts") or ""), str(r.get("record_id") or "")))
    out = []
    for r in ordered:
        rid = r.get("run.id") or r.get("correlation_id")
        rec_id = r.get("record_id")
        kind = record_kind_of(r)
        if kind is None:
            report["skipped_records"]["unmapped record_kind %s" % r.get("record_kind")] = report["skipped_records"].get("unmapped record_kind %s" % r.get("record_kind"), 0) + 1
            continue
        ref = r.get("control.ref")
        if ref in NOT_PROJECTED_CONTROLS:
            _bump(report, "control %s is not projected as records" % ref)
            continue
        controls = by_run.get(rid) or {}
        if ref not in PROJECTED_CONTROLS:
            ref = infer_control(r, kind)
            if ref is None:
                _bump(report, "no control to bind a %s record to (ep.id %s)" % (kind, r.get("ep.id")))
                continue
        a = controls.get(ref)
        reg = (cx["register_controls"] or {}).get(ref)
        if a is None and reg is None:
            _bump(report, "no %s assessment for run %s and no register entry for %s" % (ref, rid, ref))
            continue
        prov = provenance_of(r.get("provenance"), rid, cx["run_ids"])
        if prov is None:
            _bump(report, "SYNTHETIC never enters the pack")
            continue
        tokens = (r.get("tokens.in") or 0) + (r.get("tokens.out") or 0)
        measured_call = None
        if ref == "C16" and kind == "model-call":
            cum[rid] = cum.get(rid, 0) + tokens
            value, measured_call, unit = cum[rid], tokens, "tokens"
        else:
            mv = r.get("measured.value")
            value = mv if isinstance(mv, (int, float)) and not isinstance(mv, bool) else None
            unit = r.get("measured.unit") or "none"
        limit = ((a or {}).get("threshold") or {}).get("observation_limit") or (_limit(reg, "observation_limit", unit) if reg else None) or {}
        tver = (a or {}).get("threshold_version") or (reg or {}).get("threshold_version") or r.get("threshold.version") or "unbound"
        refs = _index.good_refs(r.get("source.refs"))
        at = r.get("emitted.at") or r.get("observed.at") or r.get("ts")
        if not _utc(at):
            _bump(report, "no UTC timestamp")
            continue
        clock = CLOCK_MAP.get(r.get("emitted.clock") or r.get("observed.clock"), "capture")
        raw_ref, line = resolve_raw(refs, r, rec_id, lines) if lines is not None else ((refs[0] if refs else "record:%s" % rec_id), None)
        if line is not None:       # the sha256 of the exact line the raw_ref resolves to: the browser recomputes it
            sha = hashlib.sha256(line.encode("utf-8")).hexdigest()
        else:
            sha = r.get("source.sha256") if _index.SHA_RE.match(str(r.get("source.sha256") or "")) else hashlib.sha256(canon(r).encode("utf-8")).hexdigest()
        alias = cx["run_ids"].get(rid)
        doc = {
            "schema": PROJ_SCHEMA_RECORD, "evidence_id": "ev:%s:%s:%s:%s" % (ref, tver, alias or rid, rec_id),
            "provenance": prov, "record_kind": kind, "run.id": alias or rid, "call.id": r.get("call.id"),
            "control.id": CONTROL_LIBRARY[ref], "control.ref": ref,
            "threshold.version": tver,
            "threshold.value": limit.get("value") if limit.get("value") is not None else "n/a",
            "measured.value": value, "measured.unit": unit,
            "verdict": _V.NOT_ASSESSED,   # a record is not a verdict; the control test's verdict lives in the assessment
            "decision": decision_of(r), "actor.id": r.get("actor.id") or "unknown",
            "emitted.at": at, "emitted.by": str(r.get("emitter") or "unknown"),
            "scope": {"kind": "run", "id": alias or rid, "cid": rid},
            "joins": {"cid": rid, "trace_id": r.get("trace.id"), "action_id": r.get("call.id"), "span_id": r.get("span.id"),
                      "finding_id": r.get("finding.id")},
            "facts": {"our_record_kind": r.get("record_kind"), "our_verdict": r.get("verdict"),
                      "our_provenance": r.get("provenance"), "record_id": rec_id},
            "source": {"surface": _surface(refs, r), "raw_ref": raw_ref, "sha256": sha, "captured_at": at, "clock": clock},
            "seal": "out-of-scope",
        }
        if measured_call is not None:
            doc["measured.call"] = measured_call
        doc["facts"].update(disposition_of(r))
        if r.get("hop.via") or r.get("record_kind") == "handoff":
            doc["facts"]["hop.via"] = "orchestrator-handoff"
        if len(refs) > 1:
            doc["source"]["corroborated_by"] = refs[1:]
        out.append(("records/%s/%s.json" % (safe(rid), safe(doc["evidence_id"])), doc, r))
    return out


def _bump(report, why):
    report["skipped_records"][why] = report["skipped_records"].get(why, 0) + 1


# ------------------------------------------------------------------ the projection
def project(src, out, as_of=None, generated_at=None, answers=None, assessments_dir="assessments", auditor=None):
    src, out = os.path.abspath(src), os.path.abspath(out)
    if out == src or out.startswith(src + os.sep) or src.startswith(out + os.sep):
        raise ValueError("projection is one-way: --out must be a directory apart from --src (and not contain it)")
    cx = load_context(src, as_of)
    ts = [str(r.get("ts")) for r in cx["records"] if _utc(r.get("ts"))]
    cx["as_of"] = as_of or (max(ts) if ts else "1970-01-01T00:00:00Z")
    cx["run_prov"] = {}
    for r in cx["records"]:
        rid = r.get("run.id") or r.get("correlation_id")
        if rid and r.get("provenance") and rid not in cx["run_prov"]:
            cx["run_prov"][rid] = r["provenance"]
    for row in cx["catalogue"]:
        if row.get("run_id") and row.get("label"):
            cx["run_prov"].setdefault(row["run_id"], row["label"])
    report = {"skipped_assessments": [], "skipped_records": {}, "written": {"records": 0, "assessments": 0}}

    docs = []
    for d in latest_revisions(cx["assessments_in"]):
        p = project_assessment(d, cx, report)
        if p:
            docs.append(p)
    files = []
    for p in docs:
        rel = "%s/%s/%s.json" % (assessments_dir, p["control_ref"], safe(p["assessment_id"]))
        files.append((rel, p))
    proj_records = project_records(cx, docs, report, RawLines(src))
    ep_seen, counts = {}, {}
    for rel, doc, src_rec in proj_records:
        files.append((rel, doc))
        counts[doc["control.ref"]] = counts.get(doc["control.ref"], 0) + 1
    for r in cx["records"]:
        ep = r.get("ep.id")
        if ep:
            ep_seen.setdefault(ep, []).append("record:%s" % r.get("record_id"))
    report["written"] = {"records": len(proj_records), "assessments": len(docs)}

    window = cx["window"]
    ew = window.get("event_window") if isinstance(window.get("event_window"), dict) else window
    first = min(ts) if ts else cx["as_of"]
    pack = {"title": cx["claim"].get("title") or "iFabric ProofLab Evidence Pack", "team": cx["claim"].get("team") or "iFabric",
            "event_window": {"start": ew.get("start") if _utc(ew.get("start")) else first,
                             "end": ew.get("end") if _utc(ew.get("end")) else cx["as_of"]},
            "as_of": cx["as_of"]}
    manifest = _read_bytes(os.path.join(src, "MANIFEST.json"))
    mj = None
    if manifest:
        try:
            mj = json.loads(manifest.decode("utf-8"))
        except ValueError:
            mj = None
    nfiles = len(mj.get("files")) if isinstance(mj, dict) and isinstance(mj.get("files"), (list, dict)) else 0
    integrity = {"manifest_sha256": hashlib.sha256(manifest).hexdigest() if manifest else _index.ZERO_SHA,
                 "files": nfiles, "status": "UNVERIFIED"}   # the projector never verifies; manifest.py verify does
    cases = []
    for path in sorted(glob.glob(os.path.join(src, "servicenow", "cases", "*.json"))):
        c = _read_json(path) or {}
        data = _read_bytes(path)
        if c.get("finding_id") and c.get("incident") and data is not None:
            cases.append({"finding_id": c["finding_id"], "incident": str(c["incident"]),
                          "path": os.path.relpath(path, src), "sha256": hashlib.sha256(data).hexdigest()})
    findings = []
    for p in docs:
        f = p.get("finding")
        if f:
            findings.append({"finding_id": "ifabric:%s:%s:%s:%s:finding" % (p["control_ref"], p["threshold_version"],
                                                                         p["scope"]["kind"], p["scope"]["id"]),
                             "control_ref": p["control_ref"], "scope_id": p["scope"]["id"], "verdict": f["verdict"],
                             "kind": f.get("kind") or "finding", "summary": f["summary"]})
    runs = []
    for cid, alias in sorted(cx["run_ids"].items(), key=lambda kv: kv[1]):
        rr = [r for r in cx["records"] if (r.get("run.id") or r.get("correlation_id")) == cid and _utc(r.get("ts"))]
        row = {"alias": alias, "cid": cid, "provenance": "ASSESSED"}
        if rr:
            row["started_at"], row["ended_at"] = min(r["ts"] for r in rr), max(r["ts"] for r in rr)
        row["verdicts"] = dict((p["control_ref"], p["verdict"]) for p in docs if p["scope"].get("cid") == cid)
        runs.append(row)
    named = {"written_at": cx["as_of"], "entries": [
        {"control": p["control_ref"], "expected": "BREACH" if p["verdict"] == _V.BREACHED else "PASS",
         "scope": p["scope"], "observed": p["verdict"], "answer_ref": "assessment:%s" % p["assessment_id"]}
        for p in docs if p["scope"].get("cid") in cx["run_ids"]]}
    artefacts = []
    for i, (name, path) in enumerate((("Threshold document", cx["register"] and cx["register"]["path"] or "register/register.yaml"),
                                      ("Gap list", "gap-list.md"), ("Run ids", "run-ids.txt"), ("Manifest", "MANIFEST.json"))):
        data = _read_bytes(os.path.join(src, path))
        artefacts.append({"id": i + 1, "name": name, "path": path, "present": data is not None,
                          "sha256": hashlib.sha256(data).hexdigest() if data is not None else None})
    ictx = {"as_of": cx["as_of"], "generated_at": generated_at or cx["as_of"], "pack": pack, "claim": cx["claim"],
            "assessments": [dict(p, _path="%s/%s/%s.json" % (assessments_dir, p["control_ref"], safe(p["assessment_id"]))) for p in docs],
            "findings": findings, "cases": cases, "runs": runs, "named_runs": named, "artefacts": artefacts,
            "integrity": integrity, "record_counts": counts, "ep_seen": ep_seen, "register": cx["register"],
            "register_controls": cx["register_controls"], "register_versions": cx["register_versions"],
            "approval": cx["claim"].get("approval") or None,
            "first_assessed_run_at": min((r["started_at"] for r in runs if r.get("started_at")), default=None),
            "exploratory_runs": len(set(r.get("run.id") for r in cx["records"] if r.get("run.id") and r.get("run.id") not in cx["run_ids"]
                                       and provenance_of(r.get("provenance"), r.get("run.id"), cx["run_ids"]) == "EXPLORATORY")),
            "gaps": _gaps(src), "answers": list(answers or []), "auditor": list(auditor or [])}
    index_doc = _index.build_index(ictx)
    os.makedirs(out, exist_ok=True)
    for rel, doc in files:
        _write(os.path.join(out, rel), doc)
    _write(os.path.join(out, "pack-index.json"), index_doc)
    _write(os.path.join(out, "projection-report.json"), report)
    return {"index": index_doc, "report": report, "files": [rel for rel, _ in files] + ["pack-index.json"]}


def _gaps(src):
    """pack-index gaps[] parsed from the staged gap-list.md (empty when the pack has none)."""
    from prooflab.pack import gaps as _g
    data = _read_bytes(os.path.join(src, "gap-list.md"))
    return _g.parse(data.decode("utf-8", "replace")) if data else []


def _write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_index.dumps(doc))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="prooflab.pack.projector", description="One-way pack projection for the console.")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--answers", default=None, help="JSON list of pack-index answers[] entries (from pack build)")
    ap.add_argument("--assessments-dir", default="assessments", help="where projected assessments go (default assessments)")
    ap.add_argument("--auditor", default=None, help="JSON list of pack-index auditor[] entries (from pack build)")
    args = ap.parse_args(argv)
    answers = auditor = None
    if args.answers:
        with open(args.answers, "r", encoding="utf-8") as fh:
            answers = json.load(fh)
    if args.auditor:
        with open(args.auditor, "r", encoding="utf-8") as fh:
            auditor = json.load(fh)
    try:
        res = project(args.src, args.out, args.as_of, answers=answers, assessments_dir=args.assessments_dir, auditor=auditor)
    except ValueError as exc:
        sys.stderr.write("projector: %s\n" % exc)
        return 2
    sys.stdout.write("projected %d records, %d assessments -> %s\n" % (
        res["report"]["written"]["records"], res["report"]["written"]["assessments"], args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

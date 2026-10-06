"""`prooflab humanloop findings --kind escalation` (N6, M2): the ESC finding producer. Stdlib, Python 3.9.

Reads one snapshot's ledger rows (raw/ledger/*.jsonl) and, for each run that has escalation records (control ESC,
verdict ESCALATED, phase ifabric.escalation), builds ONE Finding (Arth's `finding_from_dict` contract): control_ref
ESC, control_id AGENT-ESCALATION, scope_kind escalation, scope_id = the CID, verdict ESCALATED, kind escalation.
The named constraint is the records' `judgment.precedence_rule`; the evidence is the record chain (ESC records first,
then the same run's judgment records), at most 8 refs. The summary is templated: never agent or model text.
Only runs on the assessed provenance (the id family `ifabric-run-`) are produced unless --all-families is given
(ARCH 3.8: PILOT and BASELINE runs are filtered out to bound the volume).
"""
from __future__ import annotations

import glob
import json
import os

from prooflab.adapters import human_loop as hl
from prooflab.contract import finding as _cfinding
from prooflab.contract import clocks as _clocks

CONTROL_REF, CONTROL_ID = "ESC", "AGENT-ESCALATION"
ESC_VERDICT, ESC_PHASE = "ESCALATED", "ifabric.escalation"
SCOPE_KIND, KIND = "escalation", "escalation"
ASSESSED_PREFIX = "ifabric-run-"
NO_RULE = "no precedence rule fired"


def _cid(row):
    return row.get("run.id") or row.get("correlation_id") or ""


def is_escalation(row):
    return (row.get("control.ref") == CONTROL_REF and row.get("verdict") == ESC_VERDICT
            and row.get("phase") == ESC_PHASE)


def _ref(row):
    rid = row.get("record_id") or row.get("seq")
    return "ledger:record_id=%s" % rid if rid is not None else None


def ledger_rows(snapshot):
    rows = []
    for path in sorted(glob.glob(os.path.join(snapshot, "raw", "ledger", "*.jsonl"))):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except ValueError:
                    continue
                if isinstance(doc, dict):
                    rows.append(doc)
    return rows


def build_from_rows(rows, threshold_version, version_date, owner, cid=None, all_families=False, detected_at=None):
    """[(cid, finding dict)] one per run with at least one escalation record, sorted by CID."""
    by_run = {}
    for row in rows:
        run = _cid(row)
        if run and (cid is None or run == cid):
            by_run.setdefault(run, []).append(row)
    out = []
    for run in sorted(by_run):
        recs = by_run[run]
        esc = [r for r in recs if is_escalation(r)]
        if not esc or (not all_families and not run.startswith(ASSESSED_PREFIX) and cid != run):
            continue
        rules = []
        for r in esc:
            rule = r.get("judgment.precedence_rule")
            if rule and rule != NO_RULE and rule not in rules:
                rules.append(str(rule))
        constraint = ", ".join(rules) if rules else NO_RULE
        judgments = [r for r in recs if r.get("record_kind") == "judgment" and not is_escalation(r)]
        refs = []
        for r in esc + judgments:
            ref = _ref(r)
            if ref and ref not in refs:
                refs.append(ref)
        summary = "agent escalated %s: %d escalation record%s, named constraint: %s" % (
            run, len(esc), "" if len(esc) == 1 else "s", constraint)
        out.append((run, _cfinding.make_finding(
            CONTROL_REF, CONTROL_ID, threshold_version, SCOPE_KIND, run, ESC_VERDICT, hl._clean(summary, hl.SUMMARY_MAX),
            detected_at or _clocks.now_utc(), evidence=hl._evidence(refs), kind=KIND,
            register={"version_date": hl._clean(version_date, 40), "owner": hl._clean(owner, 100)})))
    return out


def build_all(snapshot, register_path, out_dir, owner, force=False, cid=None, all_families=False,
              detected_at=None, threshold_version=None):
    from prooflab.registry import parse as P
    with open(register_path, "rb") as fh:
        doc = P.parse_register(fh.read().decode("utf-8"))
    top = doc.get("top") or {}
    version = threshold_version or top.get("version") or top.get("register_version")
    if not version:
        raise ValueError("%s states no register version (pass --threshold-version)" % register_path)
    built = build_from_rows(ledger_rows(snapshot), version, top.get("version_date") or "unknown", owner, cid=cid,
                            all_families=all_families, detected_at=detected_at)
    made = []
    for run, finding in built:
        target = os.path.join(out_dir, "%s-%s.json" % (CONTROL_REF, run.replace(":", "_")))
        if os.path.exists(target) and not force:
            made.append((target, "kept"))
            continue
        os.makedirs(out_dir, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(finding, indent=1, sort_keys=True))
        made.append((target, "written"))
    return made

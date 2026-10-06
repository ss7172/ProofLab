"""`prooflab humanloop findings` (D4): Finding files from the BREACHED assessments of a snapshot. Stdlib, Python 3.9.

    prooflab humanloop findings --snapshot DIR [--register FILE] [--out DIR] [--verdict BREACHED ...] [--force]
    prooflab humanloop findings --kind escalation --snapshot DIR [--register FILE] [--out DIR] [--cid CID]
                                [--all-families] [--threshold-version V] [--force]

For each assessments/<C>/<cid>.json whose requirement_verdict is one of --verdict (default: breached), the register
entry bound to the assessment (control_ref + threshold_version) supplies the version_date and the limit
(`human_loop.build_finding`); the owner is SNOW_OWNER_USER (never a default). Files go to <out> (default
<snapshot>/findings/<C>-<cid>.json); an existing file is kept unless --force, so the finding id stays stable.
--kind escalation (N6) builds one ESC finding per run from the run's escalation records (humanloop/escalation.py).
Exit: 0 ok, 2 bad input or configuration.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from prooflab.adapters import human_loop as hl
from prooflab.contract import verdicts as V
from prooflab.humanloop import config as cfg
from prooflab.registry import parse as P


def _num(text):
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return None


def limit_of(entry, assessment):
    """{"value", "operator", "unit"} from the register entry (a numeric observation_limit, else the tier cap the
    evaluator applied), or None when the entry states no numeric limit."""
    unit = (entry.get("metric_unit") or "").strip()
    value = _num(entry.get("observation_limit"))
    if value is None and entry.get("control_ref") == "C16":
        value = _num((assessment.get("measured") or {}).get("cap")) or _num(entry.get("cap_tier_default"))
    if value is None or not unit or " " in unit:
        return None
    return {"value": value, "operator": "<=", "unit": unit}


def build_all(snapshot, register_path, out_dir, owner, force=False, verdicts=(V.BREACHED,), detected_at=None):
    with open(register_path, "rb") as fh:
        doc = P.parse_register(fh.read().decode("utf-8"))
    made = []
    for path in sorted(glob.glob(os.path.join(snapshot, "assessments", "*", "*.json"))):
        with open(path, "r", encoding="utf-8") as fh:
            a = json.load(fh)
        if a.get("requirement_verdict") not in verdicts or a.get("scope_kind") != "run":
            continue
        entry = next((e for e in doc["entries"] if e.get("control_ref") == a.get("control_ref")
                      and e.get("threshold_version") == a.get("threshold_version")), None)
        if entry is None:
            raise ValueError("%s: no register entry for %s %s in %s" % (
                os.path.relpath(path, snapshot), a.get("control_ref"), a.get("threshold_version"), register_path))
        cid = a["scope_id"]
        finding = hl.build_finding(a, cid, owner, entry["version_date"], limit=limit_of(entry, a),
                                   detected_at=detected_at)
        if finding is None:
            continue
        target = os.path.join(out_dir, "%s-%s.json" % (a["control_ref"], cid.replace(":", "_")))
        if os.path.exists(target) and not force:
            made.append((target, "kept"))
            continue
        os.makedirs(out_dir, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(finding, indent=1, sort_keys=True))
        made.append((target, "written"))
    return made


def main(argv=None, env=None):
    ap = argparse.ArgumentParser(prog="prooflab humanloop findings")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--register", help="frozen register file (default: newest register/versions/v*.yaml)")
    ap.add_argument("--out", help="default: <snapshot>/findings")
    ap.add_argument("--verdict", action="append", help="verdict to build a finding for (default: breached)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--kind", choices=("breach", "escalation"), default="breach",
                    help="breach: BREACHED assessments (default); escalation: ESC findings from the ledger records")
    ap.add_argument("--cid", help="--kind escalation: only this run")
    ap.add_argument("--all-families", action="store_true",
                    help="--kind escalation: also non-assessed CID families (default: ifabric-run- only)")
    ap.add_argument("--threshold-version", help="--kind escalation: override the register's version")
    args = ap.parse_args(argv)
    try:
        from prooflab.query import assess_snapshot as S
        owner = cfg.owner_from_env(env)
        reg = S.find_register(args.snapshot, args.register)
        out_dir = args.out or os.path.join(args.snapshot, "findings")
        if args.kind == "escalation":
            from prooflab.humanloop import escalation
            made = escalation.build_all(args.snapshot, reg, out_dir, owner, force=args.force, cid=args.cid,
                                        all_families=args.all_families, threshold_version=args.threshold_version)
        else:
            made = build_all(args.snapshot, reg, out_dir, owner, force=args.force,
                             verdicts=tuple(args.verdict or (V.BREACHED,)))
    except (ValueError, OSError, KeyError) as exc:     # ConfigError and AssessError are ValueErrors
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps([{"file": p, "action": a} for p, a in made], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

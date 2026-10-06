"""`run-ids.txt` check (ARCH §5.4 rule 8, §5.5; I-13, B14). Stdlib, Python 3.9.

One CID per line, as the kit's submit.sh expects. Pilot and baseline run ids never appear in it. Refused:
a line with more than one CID, a duplicate, a malformed id, and any id the experiments log marks PILOT or BASELINE
(or any id given with --exclude).
"""
from __future__ import annotations

import argparse
import json
import sys

from prooflab.contract import ids as _ids

EXCLUDED_PROVENANCE = ("PILOT", "BASELINE")


def excluded_ids(experiments_path: str) -> set:
    out = set()
    with open(experiments_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                if rec.get("provenance") in EXCLUDED_PROVENANCE and rec.get("run_id"):
                    out.add(rec["run_id"])
    return out


def check_run_ids(text: str, excluded=()) -> list:
    """Errors for the text of a run-ids.txt (empty list = OK)."""
    errors, seen, excluded = [], set(), set(excluded)
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if len(line.split()) > 1 or "," in line or ";" in line:
            errors.append("line %d: more than one CID on a line" % n)
            continue
        if not _ids.is_ours(line):
            errors.append("line %d: %r is not an ifabric run id (reference fault- runs are never assessed)" % (n, line))
        if line in excluded:
            errors.append("line %d: %s is a pilot or baseline run and never belongs in run-ids.txt" % (n, line))
        if line in seen:
            errors.append("line %d: duplicate id %s" % (n, line))
        seen.add(line)
    if not seen and not errors:
        errors.append("run-ids.txt names no run")
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab register run-ids")
    ap.add_argument("--run-ids", default="run-ids.txt")
    ap.add_argument("--experiments", default="register/experiments/experiments.jsonl")
    ap.add_argument("--exclude", action="append", default=[], help="an extra id that must not appear")
    ns = ap.parse_args(argv)
    try:
        ex = excluded_ids(ns.experiments) | set(ns.exclude)
        with open(ns.run_ids, encoding="utf-8") as fh:
            errors = check_run_ids(fh.read(), ex)
    except (OSError, ValueError) as exc:
        print("run-ids check failed: %s" % exc, file=sys.stderr)
        return 2
    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

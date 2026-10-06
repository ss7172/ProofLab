"""`python3 -m prooflab recheck CASE.json...`: the rechecker's command-line shell (PR-25). Stdlib, Python 3.9.

The I/O half of the independent rechecker: reads the named case files (the shared fixture schema: evaluator, pin, inputs,
expect) and prints each recheck verdict against the case's expected requirement verdict. The arithmetic stays in
prooflab.recheck.rechecker (pure; no I/O).
"""
import argparse
import json
import sys

from prooflab.recheck.rechecker import recheck_case


def main(argv=None):
    """`python3 -m prooflab recheck CASE.json...`: run fixture-schema cases (evaluator, pin, inputs, expect)
    through the rechecker and compare with each case's expected requirement verdict. Exit 0 all agree, 1 a
    disagreement, 2 usage or an unreadable case. Reads only the files named; no I/O beyond them."""
    p = argparse.ArgumentParser(prog="prooflab recheck",
                                description="Independent recheck (ARCH section 5) of control-test cases.")
    p.add_argument("cases", nargs="+", help="case JSON files in the shared fixture schema")
    p.add_argument("--json", action="store_true", help="one JSON line per case")
    try:
        args = p.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 2
    worst = 0
    for path in args.cases:
        try:
            with open(path) as f:
                case = json.load(f)
            got = recheck_case(case)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print("%s: cannot recheck (%s: %s)" % (path, type(exc).__name__, exc), file=sys.stderr)
            worst = max(worst, 2)
            continue
        want = (case.get("expect") or {}).get("requirement_verdict")
        agree = want is None or got["verdict"] == want
        worst = max(worst, 0 if agree else 1)
        if args.json:
            print(json.dumps({"case": case.get("name", path), "verdict": got["verdict"], "expected": want,
                              "agree": agree}, sort_keys=True))
        else:
            print("%-5s %s: %s%s" % ("OK" if agree else "DIFF", case.get("name", path), got["verdict"],
                                     "" if want is None else " (expected %s)" % want))
    return worst

"""`python3 -m prooflab query ...` (ARCH 3.7). main(argv) -> exit code. Stdlib only, Python 3.9.

    query --control C16|C7|C9 --run <CID>
    query --control C16|C7|C9 --window <T1>..<T2>
    query --control C16 --run <CID> --window <T1>..<T2>   the run's verdict + the evidence slice inside the window
    query --incident <CID or UTC time>      the six auditor questions
    query --runs | --risk [ID] | --inventory | --claim
    common: --pack <dir> (default: current directory), --json
    assess [--control C ...] [--run CID] [--out DIR]   (assess_main) every control x run of the pack
    assess --snapshot DIR [--register F] [--limit C7:k=v]   evaluate a refreshed snapshot, write assessments/
Exit codes (prooflab.contract.verdicts.exit_code): 0 SATISFIED, 1 BREACHED, 2 INDETERMINATE / NOT_ASSESSED /
unknown run / unsupported control / usage. Listings and incident answers exit 0.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from prooflab.contract import verdicts as V
from prooflab.query import engine as E


def _verdict_words(v):
    if v not in V.ASSESSMENT_VERDICTS:
        return str(v)
    kit = V.kit_label(v)
    return "%s (%s; kit: %s; brief: %s)" % (v, V.display(v), kit or "n/a", V.brief_label(v))


def _fmt_ids(pair):
    shown, more = pair
    return ", ".join(shown) + (" (+%d more)" % more if more else "") if shown else "none (gap)"


def render_control_run(a):
    if a["kind"] == "error" or "assessment" not in a:
        lines = ["%s: %s" % (a.get("control", "-"), a.get("message") or a["verdict"])]
        if a.get("records"):
            lines.append("records seen for the run: %s" % _fmt_ids(a["records"]))
        lines.append("verdict: %s" % _verdict_words(a["verdict"]))
        lines += ["gap: %s" % g for g in a.get("gaps", [])]
        return lines
    s = a["assessment"]
    ms = a["measured"] or {}
    unit = ms.get("unit") or ""
    def v(x):
        return UNKNOWN_(x)
    lines = [
        "CONTROL %s  RUN %s  (provenance %s)" % (a["control"], a["run"], a["provenance"]),
        "rule: %s%s" % (v(a["rule_metric"]), (" | basis: %s" % a["rule_basis"]) if a.get("rule_basis") else ""),
        "control version: %s (register file %s); version date %s; T1 proof %s (first file %s)" % (
            a["control_version"], v(a["register_file"]), v(a["control_date"]), v(a["t1"]), v(a["t1_file"])),
        "date of the run (T1 basis): %s" % v(a["run_start"]),
        "owner: %s" % v(a["owner"]),
        "population: %s" % (json.dumps(s["denominators"], sort_keys=True) if s["denominators"] else "unknown (gap)"),
        "measured: %s %s  vs limit: %s  (source %s)%s" % (
            v(ms.get("value")), unit, v(a["limit"]), v(a.get("limit_source") or ms.get("source")),
            ("  overshoot %s" % a["overshoot"]) if a.get("overshoot") is not None else ""),
        "exceptions: %s" % (json.dumps(s["exceptions"], sort_keys=True) if s["exceptions"] else "none recorded"),
        "completeness: %s" % (json.dumps(s["completeness"], sort_keys=True) if s["completeness"] else "unknown (gap)"),
        "design / operation / deficiency: %s / %s / %s" % (v(s["design"]), v(s["operation"]), v(s["deficiency"])),
        "VERDICT: %s" % _verdict_words(a["verdict"]),
        "gaps: %s" % ("; ".join(a["gaps"]) if a["gaps"] else "none"),
        "records: %s" % _fmt_ids(a["records"]),
        "who acted: %s" % ("; ".join("%s on runtime %s, version %s, principal %s, on behalf of %s" % tuple(v(x[k]) for k in (
            "actor", "runtime", "version", "principal", "on_behalf_of")) for x in a["actors"]) or "unknown (gap)"),
    ]
    for e in a["eps"][:12]:
        lines.append("  decision at %s: %s %s action %s mode %s responsible %s [%s]" % (
            v(e["ep"]), e["kind"], v(e["verdict"]), v(e["action"]), v(e["mode"]), v(e["responsible"]), e["record_id"]))
    lines.append("human loop: %s" % ("; ".join("%s %s [%s]" % (h["kind"], h["verdict"], h["record_id"]) for h in a["human_loop"])
                                   or "no finding or notification record for this run (gap)"))
    lines.append("recompute: %s" % a["recompute"])
    return lines


def UNKNOWN_(x):
    return "unknown" if x in (None, "") else str(x)


def render_window(a):
    if a["kind"] == "error":
        return [a["message"], "verdict: %s" % _verdict_words(a["verdict"])]
    lines = ["CONTROL %s  WINDOW %s .. %s  (rule: %s)" % (a["control"], a["window"][0], a["window"][1], a["window_rule"])]
    for r in a["counted"]:
        ms = r["measured"] or {}
        lines.append("  counted %-8s %-40s %-14s measured %s vs limit %s [%s]" % (
            r["scope_kind"], r["scope_id"], r["verdict"], UNKNOWN_(ms.get("value")), UNKNOWN_(r["limit"]), r["threshold_version"]))
    for r in a["listed"]:
        lines.append("  listed, not counted: %s (%s)" % (r["scope"], r["reason"]))
    for p in a["per_version"]:
        lines.append("  version %s: %d counted, %d breached, exception_tolerance %s%s" % (
            p["threshold_version"], p["counted"], p["breached"], UNKNOWN_(p["tolerance"]),
            (" (%s)" % p["tolerance_note"]) if p["tolerance_note"] else ""))
    lines.append("WINDOW VERDICT: %s" % _verdict_words(a["verdict"]))
    lines += ["gap: %s" % g for g in a["gaps"]]
    return lines


def render_incident(a):
    if a["kind"] == "error":
        return [a["message"], "verdict: %s" % _verdict_words(a["verdict"])]
    lines = ["INCIDENT %s  label %s  provenance %s  %s .. %s" % (a["run"], a["label"], a["provenance"],
                                                                   UNKNOWN_(a["start"]), UNKNOWN_(a["end"]))]
    if a.get("note"):
        lines.append("note: %s" % a["note"])
    if a.get("out_of_scope"):
        lines.append(a["out_of_scope"])
        return lines
    for i, q in enumerate(a["questions"], 1):
        lines.append("%d. %s" % (i, q["q"]))
        lines += ["   - %s" % x for x in q["lines"]]
        lines.append("   records: %s" % _fmt_ids((q["records"], q["more"])))
        lines.append("   stated limit: %s" % q["limit"])
    return lines


def render_runs(a):
    lines = ["RUN CATALOGUE (%s)" % a["source"]]
    if a.get("window"):
        lines.append("declared window: %s" % json.dumps(a["window"], sort_keys=True))
    for r in a["rows"]:
        lines.append("  %-44s %-22s %-18s phase %-8s cond %-10s v %-8s start %s" % (
            r["cid"], r["label"], r["provenance"], r["phase"], UNKNOWN_(r["condition"]), UNKNOWN_(r["version"]), UNKNOWN_(r["start"])))
    lines.append("%d runs" % len(a["rows"]))
    return lines


def render_simple(a):
    if a["kind"] == "risk":
        lines = [a["message"]] if a.get("message") else []
        for r in a["rows"]:
            lines.append("  ".join("%s=%s" % (k, r[k]) for k in sorted(r) if k != "linked"))
            lines.append("    linked assessments: %s" % (", ".join("%s %s %s" % x for x in r["linked"]) or "none"))
        return lines
    if a["kind"] == "inventory":
        lines = [a["message"]] if a.get("message") else ["inventory %s: %s" % (a["version"], json.dumps(a["top"], sort_keys=True))]
        lines += ["  ".join("%s=%s" % (k, r[k]) for k in sorted(r)) for r in a["rows"]]
        return lines
    lines = ["CLAIM %s: %s" % (a["claim_id"], a["coverage"])]
    lines += ["  %s: %d run assessments, worst verdict %s" % (r["control"], r["runs"], r["worst"]) for r in a["rows"]]
    return lines


def _run_window(pack, args, G, RW):
    """--run with --window: T1/T2 resolved exactly as the grammar does (HH:MMZ inside the pack's event window)."""
    if ".." not in args.window:
        return {"kind": "error", "verdict": "NOT_ASSESSED", "message": "--window needs <T1>..<T2>"}
    t1, t2, err = G.resolve_times(pack, *args.window.split("..", 1))
    if err:
        return {"kind": "error", "verdict": "NOT_ASSESSED", "message": err}
    cid, cands = G.resolve_run(pack, args.run)
    if cid is None and cands:
        return {"kind": "error", "verdict": "NOT_ASSESSED", "message": "ambiguous run %r: %s" % (args.run, ", ".join(cands))}
    return RW.compose(pack, args.control, cid or args.run, t1, t2)


def _render_run_window(a):
    from prooflab.query import run_window as RW
    return RW.render(a)


RENDER = {"control-run": render_control_run, "control-run-window": _render_run_window, "control-window": render_window, "incident": render_incident,
          "runs": render_runs, "risk": render_simple, "inventory": render_simple, "claim": render_simple}


def _jsonable(x):
    if isinstance(x, dict):
        return dict((k, _jsonable(v)) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


def build_parser():
    p = argparse.ArgumentParser(prog="prooflab query", description="Ask the Evidence Pack a control question.")
    p.add_argument("--pack", default=".", help="the unzipped evidence/ directory (default: current directory)")
    p.add_argument("--control", help="C16 | C7 | C9")
    p.add_argument("--run", help="run id (CID)")
    p.add_argument("--window", help="<T1>..<T2>, full UTC timestamps")
    p.add_argument("--incident", help="a run id or a UTC time")
    p.add_argument("--runs", action="store_true", help="the run catalogue")
    p.add_argument("--risk", nargs="?", const="", metavar="ID", help="list risks (one if an id is given)")
    p.add_argument("--inventory", action="store_true")
    p.add_argument("--claim", action="store_true")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    from prooflab.query import grammar as G
    if argv and argv[0].lower() in G.VERBS:       # PR-15b: ask "<question>" | controltest | auditor | trail
        from prooflab.query import answer as A
        return A.verb_main(argv)
    p = build_parser()
    try:
        args = p.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 2
    pack = E.Pack(args.pack)
    if args.control:
        if args.run and not args.window:
            ans = E.control_run(pack, args.control, args.run)
        elif args.window and not args.run:
            ans = E.control_window(pack, args.control, args.window)
        elif args.run and args.window:          # PR-53: run + window = the run's verdict + the evidence slice
            from prooflab.query import run_window as RW
            ans = _run_window(pack, args, G, RW)
        else:
            print("usage: --control <C> needs --run <CID>, --window <T1>..<T2>, or both", file=sys.stderr)
            return 2
    elif args.incident:
        ans = E.incident(pack, args.incident)
    elif args.runs:
        ans = E.runs_list(pack)
    elif args.risk is not None:
        ans = E.risk_list(pack, args.risk or None)
    elif args.inventory:
        ans = E.inventory_list(pack)
    elif args.claim:
        ans = E.claim_line(pack)
    else:
        p.print_usage(sys.stderr)
        return 2
    if args.json:
        print(json.dumps(_jsonable(ans), indent=1, sort_keys=True, default=str))
    else:
        print("\n".join(RENDER.get(ans["kind"], lambda a: [a.get("message", "")])(ans)))
    return E.exit_for(ans)


def _assess_snapshot(args):
    from prooflab.query import assess_snapshot as S
    try:
        res = S.assess_snapshot(args.snapshot, register=args.register, controls=[E.norm_control(c) for c in (
            args.control or E.CONTROLS)], runs=args.run, default_mode=args.mode, overrides=args.limit,
            expect_ep1=args.expect_ep1_decisions)
    except (S.AssessError, ValueError) as exc:
        print("prooflab assess --snapshot: %s" % exc, file=sys.stderr)
        return 2
    for control, cid, verdict, _path in res["written"]:
        if args.json:
            print(json.dumps({"control": control, "run": cid, "verdict": verdict}, sort_keys=True))
        else:
            print("%-4s %s %s" % (control, cid, verdict))
    for control, cid, why in res["skipped"]:
        print("skipped %s %s: %s" % (control, cid, why), file=sys.stderr)
    if not res["written"]:
        print("prooflab assess --snapshot: nothing assessed (no assessed ifabric- run in the catalogue; "
              "pass --run <CID>)", file=sys.stderr)
        return V.exit_code(V.NOT_ASSESSED)
    return S.worst_exit(res["written"])


def assess_main(argv=None):
    """`python3 -m prooflab assess`: the control test for every control x run in the pack (or the ones named).

    Each answer is control_run's: the stored assessment plus the evaluator's recompute where it exposes
    `recompute_from_pack`, a mismatch flagged. With --out each answer is written to <out>/<control>/<cid>.json
    (never into the pack's assessments/, which holds Assessment documents only). Exit: the worst verdict's code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(prog="prooflab assess", description="Run the control tests over the pack's runs.")
    p.add_argument("--pack", default=".", help="the unzipped evidence/ directory (default: current directory)")
    p.add_argument("--control", action="append", help="C16 | C7 | C9 (repeatable; default: all)")
    p.add_argument("--run", action="append", help="run id (CID) (repeatable; default: every run in the pack)")
    p.add_argument("--out", help="write each answer as JSON under this directory")
    p.add_argument("--json", action="store_true", help="one JSON line per answer")
    p.add_argument("--snapshot", help="D1: assess a refreshed snapshot: run the evaluators over its store/ and "
                   "derived/ and write <snapshot>/assessments/<C>/<cid>.json")
    p.add_argument("--register", help="--snapshot: the frozen register file (default: newest register/versions/v*.yaml)")
    p.add_argument("--mode", default="observe", help="--snapshot: C16 pin mode when a run has no EP-1 decision")
    p.add_argument("--limit", action="append", default=[], metavar="C7:key=value",
                   help="--snapshot: a limit the register text does not carry yet (repeatable)")
    p.add_argument("--expect-ep1-decisions", action="store_true",
                   help="--snapshot: C7 also expects one EP-1 decision per model call")
    try:
        args = p.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 2
    if args.snapshot:
        return _assess_snapshot(args)
    pack = E.Pack(args.pack)
    controls = [E.norm_control(c) for c in (args.control or E.CONTROLS)]
    cids = args.run or [r["cid"] for r in E.runs_list(pack)["rows"] if r.get("cid")]
    if not cids:
        print("prooflab assess: no runs in this pack (%s): nothing assessed" % pack.root, file=sys.stderr)
        return V.exit_code(V.NOT_ASSESSED)
    worst = 0
    for control in controls:
        for cid in cids:
            ans = E.control_run(pack, control, cid)
            code = E.exit_for(ans)
            worst = code if code == 1 or (worst != 1 and code > worst) else worst   # a breach outranks a gap
            if args.out:
                d = os.path.join(args.out, control)
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, "%s.json" % cid), "w") as f:
                    json.dump(_jsonable(ans), f, indent=1, sort_keys=True, default=str)
            if args.json:
                print(json.dumps({"control": control, "run": cid, "verdict": ans.get("verdict"),
                                  "recompute": ans.get("recompute")}, sort_keys=True))
            else:
                print("%-4s %s %s%s" % (control, cid, ans.get("verdict"),
                                        "  [%s]" % ans["recompute"] if ans.get("recompute") else ""))
    return worst


if __name__ == "__main__":
    sys.exit(main())

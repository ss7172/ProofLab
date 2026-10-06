"""The run catalogue (ARCH §3.7 `query --runs`; plan T4.5): ONE row per run any source saw, honestly labelled. Stdlib, 3.9.

`build(sightings, run_ids, provenance=None, window=None, records=())` -> rows, sorted by (first_seen, run_id).
A sighting is {run_id, source, ts, tokens_in, tokens_out}. Sources: gateway (spans), aws-invocation, ledger, store.
Labels (never empty): LIVE_SUBJECT / PILOT / BASELINE (declared in `provenance`, our `ifabric-run-` ids), then by id:
  test, adv, assure, unenveloped, EXPLORATORY (`fault-`, the reference trio), my-agent, hackathon-helper,
  UNATTRIBUTED (`unattributed:<runtime>:<eventTime>`), OTHER-PARTY (anything else); `ifabric-run-` with no declared
  role is "OURS-ROLE-UNDECLARED". `assessed` is true ONLY for a CID listed in run-ids.txt.
`unresolved:<trace>` ids are link-gaps, not runs: they are not catalogued.
Tokens are the gateway's figure of record, summed over its llm lines; None when no gateway llm line saw the run.
CLI: `python3 -m prooflab.stitch.catalogue --derived <dir> [--assessed-only]` lists derived/run-catalogue.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from prooflab.contract import ids as _ids

ROLE_LABELS = ("LIVE_SUBJECT", "PILOT", "BASELINE")
UNDECLARED = "OURS-ROLE-UNDECLARED"


def label_for(run_id: str, provenance=None) -> str:
    declared = (provenance or {}).get(run_id)
    if declared in ROLE_LABELS and run_id.startswith("ifabric-run-"):
        return declared
    if run_id.startswith("ifabric-run-"):
        return UNDECLARED
    for prefix, label in (("ifabric-test-", "test"), ("ifabric-adv-", "adv"), ("ifabric-assure-", "assure"),
                          ("ifabric-unenveloped-", "unenveloped"), ("fault-", "EXPLORATORY"),
                          ("my-agent-", "my-agent"), ("hackathon-helper-", "hackathon-helper"),
                          ("unattributed:", "UNATTRIBUTED")):
        if run_id.startswith(prefix):
            return label
    return "OTHER-PARTY"


def read_run_ids(text: str) -> set:
    return set(l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#"))


def build(sightings, run_ids, provenance=None, window=None, records=()) -> list:
    run_ids = set(run_ids or ())
    rows = {}
    for s in sightings:
        rid = s.get("run_id")
        if not rid or rid.startswith("unresolved:"):
            continue
        ts = s.get("ts")
        if window and ts and not (window[0] <= ts <= window[1]):
            continue
        row = rows.setdefault(rid, {"run_id": rid, "first_seen": ts, "last_seen": ts, "sources": {},
                                    "tokens_in": None, "tokens_out": None, "record_ids": []})
        if ts:
            row["first_seen"] = min(x for x in (row["first_seen"], ts) if x)
            row["last_seen"] = max(x for x in (row["last_seen"], ts) if x)
        row["sources"][s["source"]] = row["sources"].get(s["source"], 0) + 1
        if s["source"] == "gateway" and s.get("tokens_in") is not None and s.get("tokens_out") is not None:
            row["tokens_in"] = (row["tokens_in"] or 0) + s["tokens_in"]
            row["tokens_out"] = (row["tokens_out"] or 0) + s["tokens_out"]
    for rec in records:
        rid = rec.get("run.id") or rec.get("correlation_id")
        if rid in rows and rec.get("record_id"):
            rows[rid]["record_ids"].append(rec["record_id"])
    out = []
    for rid, row in rows.items():
        row["label"] = label_for(rid, provenance)
        row["assessed"] = rid in run_ids
        row["family"] = _family(rid)
        row["record_ids"] = sorted(set(row["record_ids"]))
        out.append(row)
    out.sort(key=lambda r: (r["first_seen"] or "", r["run_id"]))
    return out


def _family(rid: str) -> str:
    for fam in _ids.CID_FAMILIES:
        if rid.startswith(fam + "-"):
            return fam
    for fam in ("fault", "unattributed"):
        if rid.startswith(fam + ("-" if fam == "fault" else ":")):
            return fam
    return "other"


def dumps_rows(rows) -> str:
    return "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows)


def format_table(rows) -> str:
    head = "%-46s %-22s %-8s %-9s %s" % ("RUN", "LABEL", "ASSESSED", "TOKENS", "SOURCES")
    lines = [head]
    for r in rows:
        tok = "-" if r["tokens_in"] is None else str(r["tokens_in"] + r["tokens_out"])
        lines.append("%-46s %-22s %-8s %-9s %s" % (r["run_id"], r["label"], "yes" if r["assessed"] else "no", tok,
                                                  ",".join("%s:%d" % kv for kv in sorted(r["sources"].items()))))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab query --runs", description="list the run catalogue")
    ap.add_argument("--derived", required=True, help="the snapshot's derived/ directory")
    ap.add_argument("--assessed-only", action="store_true")
    args = ap.parse_args(argv)
    path = os.path.join(args.derived, "run-catalogue.jsonl")
    if not os.path.exists(path):
        sys.stderr.write("no run-catalogue.jsonl in %s (run `prooflab refresh` first)\n" % args.derived)
        return 1
    with open(path, "r", encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    if args.assessed_only:
        rows = [r for r in rows if r["assessed"]]
    sys.stdout.write(format_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The run catalogue (ARCH §3.7 `query --runs`; plan T4.5): ONE row per run any source saw, honestly labelled. Stdlib, 3.9.

`build(sightings, run_ids, provenance=None, window=None, records=())` -> rows, sorted by (first_seen, run_id).
A sighting is {run_id, source, ts, tokens_in, tokens_out}. Sources: gateway (spans), aws-invocation, ledger, store.
Labels (never empty): the role declared in `provenance` for our `ifabric-run-` ids (LIVE_SUBJECT / PILOT / BASELINE /
  EXPLORATORY for a warm-up, ...), then by id:
  test, adv, assure, unenveloped, EXPLORATORY (`fault-`, the reference trio), my-agent, hackathon-helper,
  UNATTRIBUTED (`unattributed:<runtime>:<eventTime>`), OTHER-PARTY (anything else); `ifabric-run-` with no declared
  role is "OURS-ROLE-UNDECLARED". `assessed` is true ONLY for a CID listed in run-ids.txt.
`unresolved:<trace>` ids are link-gaps, not runs: they are not catalogued.
Tokens are the gateway's figure of record, summed over its llm lines ONCE per action id (several captures of one
run overlap; the latest wins); None when no gateway llm line saw the run. Every CID in `provenance` and in the store
gets a row, even with no sighting in the window.
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
    if isinstance(declared, str) and declared.strip() and run_id.startswith("ifabric-run-"):
        return declared.strip()           # any declared role (LIVE_SUBJECT, PILOT, BASELINE, EXPLORATORY, ...)
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


def _gateway_dedup(sightings):
    """Gateway sightings that carry an action id are kept once per (run, action id); the LAST one wins, so a later
    capture (sightings arrive oldest capture first) replaces an earlier one. Others pass through unchanged."""
    last = {}
    for i, s in enumerate(sightings):
        if s.get("source") == "gateway" and s.get("action_id"):
            last[(s.get("run_id"), s["action_id"])] = i
    return [s for i, s in enumerate(sightings)
            if not (s.get("source") == "gateway" and s.get("action_id"))
            or last[(s.get("run_id"), s["action_id"])] == i]


def _new_row(rid, ts):
    return {"run_id": rid, "first_seen": ts, "last_seen": ts, "sources": {}, "tokens_in": None, "tokens_out": None,
            "record_ids": []}


def _seen(row, ts):
    if ts:
        row["first_seen"] = min(x for x in (row["first_seen"], ts) if x)
        row["last_seen"] = max(x for x in (row["last_seen"], ts) if x)


def build(sightings, run_ids, provenance=None, window=None, records=()) -> list:
    """Rows for every run a source saw in the window, plus every CID declared in `provenance` and every CID the
    store holds (a declared or stored run is never dropped by the window). Gateway tokens are summed once per
    action id (latest capture wins): the same figure C16 measures."""
    run_ids = set(run_ids or ())
    rows = {}
    for s in _gateway_dedup(sightings):
        rid = s.get("run_id")
        if not rid or rid.startswith("unresolved:"):
            continue
        ts = s.get("ts")
        if window and ts and not (window[0] <= ts <= window[1]):
            continue
        row = rows.setdefault(rid, _new_row(rid, ts))
        _seen(row, ts)
        row["sources"][s["source"]] = row["sources"].get(s["source"], 0) + 1
        if s["source"] == "gateway" and s.get("tokens_in") is not None and s.get("tokens_out") is not None:
            row["tokens_in"] = (row["tokens_in"] or 0) + s["tokens_in"]
            row["tokens_out"] = (row["tokens_out"] or 0) + s["tokens_out"]
    for rec in records:
        rid = rec.get("run.id") or rec.get("correlation_id")
        if not rid or rid.startswith("unresolved:"):
            continue
        if rid not in rows:
            rows[rid] = _new_row(rid, rec.get("ts"))
            rows[rid]["sources"]["store"] = 0
        if "store" in rows[rid]["sources"]:
            rows[rid]["sources"]["store"] += 1
            _seen(rows[rid], rec.get("ts"))
        if rec.get("record_id"):
            rows[rid]["record_ids"].append(rec["record_id"])
    for rid in sorted((provenance or {})):
        if rid and not rid.startswith("unresolved:") and rid not in rows:
            rows[rid] = _new_row(rid, None)
            rows[rid]["sources"]["provenance"] = 1
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

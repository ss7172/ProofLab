#!/usr/bin/env python3
"""Grade one of our runs with the KIT's own grader (score-run.py), unmodified (OC-6). Stdlib, Python 3.9.

    python3 tools/kit_grade.py --cid <CID> --scenario S1 --records chain.jsonl     # offline: a saved per-CID read
    python3 tools/kit_grade.py --cid <CID> --scenario S1 --url <audit-store base>  # GET /records?cid= (open read)

Why a wrapper, and what it does NOT change:
  * score-run.py's timeline parser only knows phases matching [A-Z-]+, so our dotted phases (handoff.sent,
    ifabric.judgment) cannot go through the timeline view: we feed it a JSON array built from /records?cid=
    (JSONL), which its own parse() accepts.
  * with a file argument score-run.py reads /tmp/network-inventory.json; we use stdin instead, in a temp cwd
    holding a copy of the kit's network-inventory.json (its documented fallback).
  * records are ordered by their own timestamp (`ts`, then `emitted.at`), store order breaking ties: the store's
    append order is not emission order (our emit client drains critical kinds first) and the kit's
    "intent before invocation" check is a list-index comparison.
Nothing is added to or removed from the records; the grader's verdict is its own.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

ASSETS = os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-assets")
KIT_SCORE = os.environ.get("KIT_SCORE_RUN") or os.path.join(ASSETS, "reference-impl", "score-run.py")
KIT_INVENTORY = os.environ.get("KIT_INVENTORY") or os.path.join(ASSETS, "data", "network-inventory.json")
CHECK = re.compile(r"^\s+(PASS|FAIL)\s+(.+?)\s{2,}(.*)$")


def read_records(text):
    """JSONL (the store's per-CID read) or a JSON array / {"records": [...]}."""
    text = (text or "").strip()
    if text.startswith("["):
        return json.loads(text)
    if text.startswith("{") and "\n" not in text:
        doc = json.loads(text)
        return doc.get("records", [doc]) if isinstance(doc, dict) else doc
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def fetch(base_url, cid, timeout=10.0):
    url = base_url.rstrip("/") + "/records?" + urllib.parse.urlencode({"cid": cid})
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return read_records(resp.read().decode("utf-8"))


def kit_order(records, cid=None):
    recs = [r for r in records if cid is None or r.get("correlation_id") == cid]
    return [r for _, r in sorted(enumerate(recs), key=lambda p: (str(p[1].get("ts") or p[1].get("emitted.at") or ""),
                                                                 p[0]))]


def scenario_id(short, inventory=KIT_INVENTORY):
    """Our S1/S2/S3 -> the kit's scenario id (S1-fronthaul-degradation, ...); a full id passes through."""
    with open(inventory, encoding="utf-8") as fh:
        ids = [s["id"] for s in json.load(fh)["fault_scenarios"]]
    if short in ids:
        return short
    hits = [i for i in ids if i.startswith(short + "-")]
    return hits[0] if len(hits) == 1 else short


def grade(records, cid, scenario, score=KIT_SCORE, inventory=KIT_INVENTORY, python=None):
    """Run the kit's score-run.py on our records. -> {rc, result, checks: {name: (ok, note)}, output}."""
    scenario = scenario_id(scenario, inventory)
    work = tempfile.mkdtemp(prefix="kit-grade-")
    try:
        shutil.copy(inventory, os.path.join(work, "network-inventory.json"))
        body = json.dumps(kit_order(records, cid), sort_keys=True)
        proc = subprocess.run([python or sys.executable, score, cid, scenario], input=body, cwd=work,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    checks, result = {}, None
    for line in proc.stdout.splitlines():
        m = CHECK.match(line)
        if m:
            checks[m.group(2).strip()] = (m.group(1) == "PASS", m.group(3).strip())
        elif line.startswith("RESULT:"):
            result = line[len("RESULT:"):].strip()
    return {"rc": proc.returncode, "result": result, "checks": checks, "output": proc.stdout + proc.stderr}


def main(argv=None):
    p = argparse.ArgumentParser(description="grade a run with the kit's score-run.py")
    p.add_argument("--cid", required=True)
    p.add_argument("--scenario", required=True)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--records", help="the per-CID JSONL (or JSON array); - for stdin")
    src.add_argument("--url", help="audit-store base URL: GET /records?cid=")
    p.add_argument("--score-run", default=KIT_SCORE)
    p.add_argument("--inventory", default=KIT_INVENTORY)
    a = p.parse_args(argv)
    if a.url:
        recs = fetch(a.url, a.cid)
    else:
        recs = read_records(sys.stdin.read() if a.records == "-" else open(a.records, encoding="utf-8").read())
    out = grade(recs, a.cid, a.scenario, a.score_run, a.inventory)
    sys.stdout.write(out["output"])
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())

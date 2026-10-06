"""`prooflab refresh`: build one snapshot's derived files from its raw captures (ARCH §3.5 "The export"). Stdlib, 3.9.

Snapshot directory layout (the collectors, PR-12, write raw/; this module reads it and writes the rest):
  raw/gateway/*.log          gateway pod logs, byte-exact          raw/spans/*.jsonl        span exports (flat JSON)
  raw/aws-invocations/*.jsonl  InvokeAgentRuntime records          raw/ledger/*.jsonl       ledger rows (verbatim)
  -> store/records.jsonl            the store's records, verbatim: ledger rows + normalized, deduped, sorted
  -> derived/observations.jsonl     the normalized records (pure function of raw/)
  -> derived/run-index.jsonl, derived/unjoined.jsonl, derived/run-catalogue.jsonl, derived/rejects.jsonl
  -> SNAPSHOT.json                  as-of + sha256 of every file above (deterministic given --as-of)
Optional live steps (between runs only; the token is read from the environment variable NAMED by --token-env, never
from argv): --pull-ledger fetches each of our CIDs per-CID into raw/ledger/; --ingest appends the normalized records
to the ledger (or --fallback-store FILE). Run it twice on the same raw/ and `derived/` is byte-identical.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

from prooflab.contract import ids as _ids
from prooflab.contract import record as _rec
from prooflab.stitch import catalogue as _catalogue
from prooflab.stitch import corroboration as _corroboration
from prooflab.stitch import kit_crosscheck as _kit
from prooflab.stitch import stitcher as _stitcher
from prooflab.store import ingest as _ingest
from prooflab.store import observations as _obs
from prooflab.store.ledger_client import LedgerClient, LedgerError


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _dumps(rows):
    return "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def _files(root, sub, pattern):
    return sorted(glob.glob(os.path.join(root, "raw", sub, pattern)))


def our_scope(run_id) -> bool:
    return bool(run_id) and (_ids.is_ours(run_id) or run_id.startswith(("unresolved:", "unattributed:")))


def _safe(cid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", cid)


def normalize_all(root, provenance=None) -> dict:
    records, sightings, rejects, background = [], [], [], 0
    jobs = [("gateway", "*.log", _obs.normalize_gateway_text), ("spans", "*.jsonl", _obs.normalize_gateway_text),
            ("aws-invocations", "*.jsonl", _obs.normalize_invocation_text)]
    work = [(sub, path, fn, False) for sub, pattern, fn in jobs for path in _files(root, sub, pattern)]
    # D3: the aws/spans collector's capture, raw/aws-spans/<cid>/spans.jsonl (Logs Insights @timestamp/@message rows)
    work += [("aws-spans", path, _obs.normalize_gateway_text, True)
             for path in sorted(glob.glob(os.path.join(root, "raw", "aws-spans", "*", "spans.jsonl*"))
                                ) if not path.endswith(".capture.json")]
    for sub, path, fn, insights in work:
        ref = os.path.relpath(path, root).replace(os.sep, "/") if sub == "aws-spans" else \
            "raw/%s/%s" % (sub, os.path.basename(path))
        out = fn(_read(path), ref, provenance, insights=True) if insights else fn(_read(path), ref, provenance)
        records += out["records"]
        sightings += out["sightings"]
        rejects += out["rejects"]
        background += out["background"]
    return {"records": _obs.sort_records(_dedup(records)), "sightings": sightings, "rejects": rejects,
            "background": background}


def _dedup(records):
    seen, out = set(), []
    for r in records:
        key = _ingest.record_key(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def read_ledger_rows(root) -> list:
    rows = []
    for path in _files(root, "ledger", "*.jsonl"):
        for line in _read(path).splitlines():
            if line.strip():
                try:
                    doc = json.loads(line)
                except ValueError:
                    continue
                if isinstance(doc, dict):
                    rows.append(doc)
    return rows


def pull_ledger(client, cids, root) -> list:
    """Per-CID GET of each CID into raw/ledger/<cid>.jsonl, verbatim. Returns the CIDs written."""
    done = []
    for cid in sorted(set(cids)):
        rows = client.get_by_cid(cid)
        _write(os.path.join(root, "raw", "ledger", _safe(cid) + ".jsonl"),
               "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows))
        done.append(cid)
    return done


def _ledger_sightings(rows):
    out = []
    for r in rows:
        cid = r.get("run.id") or r.get("correlation_id")
        if cid:
            out.append({"run_id": cid, "source": "ledger", "ts": r.get("ts"), "tokens_in": None, "tokens_out": None})
    return out


def _read_raw(root):
    def read(rel):
        path = os.path.join(root, rel)
        return _read(path) if os.path.isfile(path) else None
    return read


def _write_corroboration(root, store_rows, stitched, join_tolerance_s) -> list:
    """derived/corroboration/<CID>.json (ARCH 3.6 / 9.2): where the independent sources agree and where they do not."""
    reports = _corroboration.corroborate(store_rows, stitched, join_tolerance_s, read_raw=_read_raw(root))
    return [os.path.relpath(p, root).replace(os.sep, "/") for p in _corroboration.write(root, reports)]


def _write_kit_logs(root, store_rows) -> list:
    """D10: kit-crosscheck/<CID>/gateway-log.json, built from the gateway records of that CID (ARCH 9.1)."""
    cids = sorted(set(r.get("run.id") or r.get("correlation_id") or "" for r in store_rows
                      if _kit.is_model_call_span(r)))
    names = []
    for cid in cids:
        if not _ids.is_ours(cid):
            continue
        log = _kit.build_gateway_log(store_rows, cid)
        if log["records"]:
            names.append(os.path.relpath(_kit.write(root, cid, log), root).replace(os.sep, "/"))
    return names


def refresh(root, as_of=None, run_ids=(), provenance=None, window=None, join_tolerance_s=None,
            client=None, pull=False, do_ingest=False, fallback_store=None) -> dict:
    summary = {"pulled": [], "ingest": None}
    if pull:
        if client is None:
            raise LedgerError("--pull-ledger needs a ledger client")
        first = normalize_all(root, provenance)
        cids = set(s["run_id"] for s in first["sightings"] if _ids.is_ours(s["run_id"]))
        cids |= set(r.get("correlation_id") for r in read_ledger_rows(root) if _ids.is_ours(r.get("correlation_id") or ""))
        summary["pulled"] = pull_ledger(client, cids, root)
    norm = normalize_all(root, provenance)
    if do_ingest:
        store = _ingest.FileStore(fallback_store) if fallback_store else (
            _ingest.LedgerStore(client) if client is not None else None)
        if store is None:
            raise LedgerError("--ingest needs a ledger client or --fallback-store")
        summary["ingest"] = _ingest.ingest(norm["records"], store, scope=our_scope)
    ledger_rows = read_ledger_rows(root)
    store_rows = _dedup(ledger_rows + norm["records"])
    store_rows.sort(key=lambda r: (r.get("ts") or "", _ingest.record_key(r)))
    out = _stitcher.stitch(store_rows, join_tolerance_s=join_tolerance_s)
    sightings = norm["sightings"] + _ledger_sightings(ledger_rows)
    cat = _catalogue.build(sightings, run_ids, provenance=provenance, window=window, records=store_rows)
    _write(os.path.join(root, "store", "records.jsonl"), _dumps(store_rows))
    _write(os.path.join(root, "derived", "observations.jsonl"), _dumps(norm["records"]))
    _write(os.path.join(root, "derived", "run-index.jsonl"), _stitcher.dumps_rows(out["run_index"]))
    _write(os.path.join(root, "derived", "unjoined.jsonl"), _stitcher.dumps_rows(out["unjoined"]))
    _write(os.path.join(root, "derived", "run-catalogue.jsonl"), _catalogue.dumps_rows(cat))
    _write(os.path.join(root, "derived", "rejects.jsonl"), _dumps(sorted(norm["rejects"], key=lambda r: r["ref"])))
    names = ["store/records.jsonl", "derived/observations.jsonl", "derived/run-index.jsonl",
             "derived/unjoined.jsonl", "derived/run-catalogue.jsonl", "derived/rejects.jsonl"]
    names += _write_corroboration(root, store_rows, out, join_tolerance_s)
    names += _write_kit_logs(root, store_rows)
    manifest = {"as_of": as_of, "schema": _rec.SCHEMA_ID, "background_lines": norm["background"],
                "files": dict((n, _sha(os.path.join(root, n))) for n in names)}
    _write(os.path.join(root, "SNAPSHOT.json"), json.dumps(manifest, sort_keys=True, indent=1) + "\n")
    summary.update({"records": len(store_rows), "runs": len(cat), "unjoined": len(out["unjoined"]),
                    "rejects": len(norm["rejects"])})
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prooflab refresh", description="rebuild one snapshot's derived files")
    ap.add_argument("--snapshot", required=True, help="snapshot directory (raw/ inside it)")
    ap.add_argument("--as-of", default=None, help="UTC time recorded in SNAPSHOT.json")
    ap.add_argument("--run-ids", default=None, help="run-ids.txt (only these CIDs are marked assessed)")
    ap.add_argument("--provenance", default=None, help="JSON {cid: LIVE_SUBJECT|PILOT|BASELINE|...}")
    ap.add_argument("--window", nargs=2, metavar=("START", "END"), default=None)
    ap.add_argument("--join-tolerance-s", type=float, default=None, help="the register's join_tolerance_s")
    ap.add_argument("--ledger-url", default=None, help="ledger base URL (e.g. the kubectl proxy service path)")
    ap.add_argument("--token-env", default=None, help="NAME of the env var holding the ledger token")
    ap.add_argument("--pull-ledger", action="store_true", help="GET each of our CIDs per CID (between runs)")
    ap.add_argument("--ingest", action="store_true", help="append normalized records to the store (between runs)")
    ap.add_argument("--fallback-store", default=None, help="ifabric-store/records.jsonl (D16 fallback)")
    args = ap.parse_args(argv)
    client = None
    if args.ledger_url:
        if not args.token_env:
            sys.stderr.write("--ledger-url needs --token-env NAME\n")
            return 2
        try:
            client = LedgerClient.from_env(args.ledger_url, args.token_env)
        except LedgerError as exc:
            sys.stderr.write("%s\n" % exc)
            return 2
    run_ids = _catalogue.read_run_ids(_read(args.run_ids)) if args.run_ids else set()
    provenance = json.loads(_read(args.provenance)) if args.provenance else None
    try:
        res = refresh(args.snapshot, as_of=args.as_of, run_ids=run_ids, provenance=provenance,
                      window=tuple(args.window) if args.window else None, join_tolerance_s=args.join_tolerance_s,
                      client=client, pull=args.pull_ledger, do_ingest=args.ingest, fallback_store=args.fallback_store)
    except LedgerError as exc:
        sys.stderr.write("refresh failed: %s\n" % exc)
        return 1
    sys.stdout.write(json.dumps(res, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

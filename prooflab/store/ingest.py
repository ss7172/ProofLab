"""The ingest rule (ARCH §3.5): append between runs, per CID, skip what the store already holds. Stdlib, 3.9.

There is NO update and NO delete path here (a correction is a new record with `supersedes`). Two stores share one
tiny interface (`known_ids(cid)`, `append(record)`):
  * LedgerStore(client)  the platform ledger, via LedgerClient (default, D16 (a))
  * FileStore(path)      the fallback `ifabric-store/records.jsonl` (open for append, flushed and fsync'd per write)
Only records that validate against `ifabric.evidence/1` are ingested; the rest are returned as rejects.
Reference-shaped ledger rows (no `record_id`, no ifabric fields, e.g. the `ifabric-test-ledger-smoke-*` probe) are
never ingested by us and never crash anything: `record_key` gives them a content key so a verbatim copy dedups.
"""
from __future__ import annotations

import json
import os

from prooflab.contract import record as _rec

MAX_CONSECUTIVE_FAILURES = 3


def record_key(rec: dict) -> str:
    """The dedup key: `record_id` when present, else a content key (verbatim ledger rows lack one)."""
    rid = rec.get("record_id")
    if isinstance(rid, str) and rid:
        return rid
    import hashlib
    return "ledger:" + hashlib.sha256(_rec.canonical_json(rec).encode("utf-8")).hexdigest()


def run_key(rec: dict):
    return rec.get("run.id") or rec.get("correlation_id")


def is_ifabric_record(rec) -> bool:
    return isinstance(rec, dict) and rec.get("schema") == _rec.SCHEMA_ID


class LedgerStore:
    def __init__(self, client):
        self._client = client

    def known_ids(self, cid: str) -> set:
        return set(record_key(r) for r in self._client.get_by_cid(cid))

    def append(self, rec: dict) -> None:
        self._client.post(rec)


class FileStore:
    """`ifabric-store/records.jsonl`: append + fsync, nothing else."""

    def __init__(self, path: str):
        self.path = path

    def rows(self) -> list:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
        return out

    def known_ids(self, cid: str) -> set:
        return set(record_key(r) for r in self.rows() if run_key(r) == cid)

    def append(self, rec: dict) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(_rec.canonical_json(rec) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def ingest(records, store, scope=None) -> dict:
    """Append `records` to `store`, grouped per CID, skipping record ids the store already holds.

    `scope(run_id) -> bool` limits what is written (default: everything valid). Returns
    {appended, skipped, rejected: [{record_id, errors}], failed: [record_id], out_of_scope}. Run it between runs.
    """
    by_cid = {}
    summary = {"appended": 0, "skipped": 0, "rejected": [], "failed": [], "out_of_scope": 0}
    for rec in records:
        errs = _rec.validate_record(rec) if is_ifabric_record(rec) else ["not an ifabric.evidence/1 record"]
        if errs:
            summary["rejected"].append({"record_id": (rec or {}).get("record_id") if isinstance(rec, dict) else None,
                                        "errors": errs[:3]})
            continue
        cid = run_key(rec)
        if scope is not None and not scope(cid):
            summary["out_of_scope"] += 1
            continue
        by_cid.setdefault(cid, []).append(rec)
    consecutive = 0
    for cid in sorted(by_cid):
        try:
            known = store.known_ids(cid)
        except Exception as exc:  # noqa: BLE001 - a store read failure must not lose the run
            summary["failed"].extend(r["record_id"] for r in by_cid[cid])
            consecutive += 1
            summary.setdefault("errors", []).append("%s: %s" % (cid, type(exc).__name__))
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                break
            continue
        for rec in by_cid[cid]:
            key = record_key(rec)
            if key in known:
                summary["skipped"] += 1
                continue
            try:
                store.append(rec)
            except Exception as exc:  # noqa: BLE001
                summary["failed"].append(rec["record_id"])
                summary.setdefault("errors", []).append("%s: %s" % (cid, type(exc).__name__))
                consecutive += 1
                if consecutive >= MAX_CONSECUTIVE_FAILURES:
                    return summary
                continue
            consecutive = 0
            known.add(key)
            summary["appended"] += 1
    return summary


def copy_ledger_into_file_store(client, file_store: FileStore, cids) -> dict:
    """Fallback only: copy the ledger's rows for each CID verbatim into the laptop store, skipping known ones.
    Reference-shaped rows are copied as they are (they are the platform's, not ours to validate)."""
    out = {"appended": 0, "skipped": 0}
    for cid in sorted(set(cids)):
        known = file_store.known_ids(cid)
        for row in client.get_by_cid(cid):
            if record_key(row) in known:
                out["skipped"] += 1
                continue
            file_store.append(row)
            known.add(record_key(row))
            out["appended"] += 1
    return out


def merge_replay(root, records, replaced_runs, is_replay):
    """Put post-run replay records (EP-2) into <root>/store/records.jsonl: this replay's records replace any earlier
    replay records of the same runs (`is_replay(rec)` names them), the store is re-sorted (ts, key) and the
    store's sha256 in SNAPSHOT.json is updated. Returns the number of records written."""
    import hashlib
    import json
    import os
    path = os.path.join(root, "store", "records.jsonl")
    rows = []
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    replaced = set(replaced_runs)
    keep = [r for r in rows if not (is_replay(r) and (r.get("run.id") or r.get("correlation_id")) in replaced)]
    seen, out = set(), []
    for r in keep + list(records):
        k = record_key(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    out.sort(key=lambda r: (r.get("ts") or "", record_key(r)))
    text = "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in out)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    manifest = os.path.join(root, "SNAPSHOT.json")
    if os.path.isfile(manifest):
        with open(manifest, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if isinstance(doc.get("files"), dict) and "store/records.jsonl" in doc["files"]:
            doc["files"]["store/records.jsonl"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            with open(manifest, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(doc, sort_keys=True, indent=1) + "\n")
    return len(records)

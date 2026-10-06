#!/usr/bin/env python3
"""Stage the S3 T1 date proofs of the frozen registers into the pack source (PR-48). Stdlib only, Python 3.9.

The ops lane saves each write-once upload of a register version as a list of
{file, key, local_sha256_hex, local_sha256_b64, put_object{...}, head_object{VersionId, LastModified, ETag,
ChecksumSHA256, ...}} entries in t1*.json files. The query engine reads the T1 proof of register version <v> from
register/versions/<v>.head.json. This tool converts one into the other:

  python3 tools/stage_t1.py --from <ops-lane dir or t1*.json> [--from ...] --to <src>/register/versions [--dry-run]

For every <v>.yaml under --to it picks the entries whose Key is exactly ifabric/register/<v>.yaml, checks that the
SHA-256 of the local <v>.yaml equals the proof's (local_sha256_hex and head_object.ChecksumSHA256, which is the
base64 of the digest), and writes <v>.head.json with VersionId, LastModified (UTC, ...Z), ETag, ChecksumSHA256, Key.
Nothing is written when any check fails (exit 2). Reads only from --from; writes only under --to.
"""
from __future__ import annotations

import argparse
import base64
import glob
import hashlib
import json
import os
import sys

KEY_PREFIX = "ifabric/register/"


def _utc(text):
    t = str(text or "").strip()
    if t.endswith("+00:00"):
        t = t[:-6] + "Z"
    return t


def t1_files(sources):
    out = []
    for s in sources:
        if os.path.isfile(s):
            out.append(s)
        elif os.path.isdir(s):
            out += sorted(glob.glob(os.path.join(s, "**", "t1*.json"), recursive=True))
        else:
            raise ValueError("--from %s: no such file or directory" % s)
    return sorted(set(os.path.abspath(p) for p in out))


def load_entries(paths):
    entries = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
        for e in (doc if isinstance(doc, list) else [doc]):
            if isinstance(e, dict) and isinstance(e.get("head_object"), dict):
                entries.append(dict(e, _source=os.path.basename(p)))
    return entries


def plan(entries, to_dir):
    """-> (writes {name: head dict}, errors [str], notes [str])."""
    writes, errors, notes = {}, [], []
    names = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(to_dir, "*.yaml"))
                   if not p.endswith(".risks.yaml"))
    for name in names:
        key = KEY_PREFIX + name + ".yaml"
        mine = [e for e in entries if e.get("key") == key or e["head_object"].get("Key") == key]
        if not mine:
            notes.append("%s.yaml: no T1 entry with Key %s in the sources (not staged)" % (name, key))
            continue
        with open(os.path.join(to_dir, name + ".yaml"), "rb") as f:
            digest = hashlib.sha256(f.read()).digest()
        hexd, b64d = digest.hex(), base64.b64encode(digest).decode("ascii")
        ok = []
        for e in mine:
            h = e["head_object"]
            bad = []
            if e.get("local_sha256_hex") and e["local_sha256_hex"].lower() != hexd:
                bad.append("local_sha256_hex %s" % e["local_sha256_hex"][:12])
            if h.get("ChecksumSHA256") != b64d:
                bad.append("head_object.ChecksumSHA256 %s" % h.get("ChecksumSHA256"))
            if not h.get("VersionId") or not h.get("LastModified"):
                bad.append("no VersionId/LastModified")
            if bad:
                errors.append("%s.yaml (sha256 %s, base64 %s) does not match the T1 proof in %s: %s"
                              % (name, hexd[:12], b64d, e["_source"], "; ".join(bad)))
            else:
                ok.append(e)
        if ok:
            e = sorted(ok, key=lambda x: _utc(x["head_object"]["LastModified"]))[0]     # the first write is T1
            h = e["head_object"]
            writes[name] = {"VersionId": h["VersionId"], "LastModified": _utc(h["LastModified"]), "ETag": h.get("ETag"),
                            "ChecksumSHA256": h["ChecksumSHA256"], "Key": key, "StagedFrom": e["_source"]}
    return writes, errors, notes


def main(argv=None):
    p = argparse.ArgumentParser(prog="stage_t1.py", description=__doc__.split("\n\n")[0])
    p.add_argument("--from", dest="sources", action="append", required=True,
                   help="an ops-lane dir (searched for t1*.json) or a t1*.json file; repeatable")
    p.add_argument("--to", required=True, help="<src>/register/versions holding the frozen <v>.yaml files")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    if not os.path.isdir(a.to):
        print("stage_t1: --to %s is not a directory" % a.to, file=sys.stderr)
        return 2
    try:
        files = t1_files(a.sources)
        entries = load_entries(files)
    except (ValueError, IOError, OSError) as exc:
        print("stage_t1: %s" % exc, file=sys.stderr)
        return 2
    writes, errors, notes = plan(entries, a.to)
    for n in notes:
        print("note: " + n, file=sys.stderr)
    if errors:
        for e in errors:
            print("REFUSED: " + e, file=sys.stderr)
        print("stage_t1: nothing written (%d checksum mismatch(es))" % len(errors), file=sys.stderr)
        return 2
    if not writes:
        print("stage_t1: no register version under %s has a T1 proof in %d file(s)" % (a.to, len(files)), file=sys.stderr)
        return 2
    for name in sorted(writes):          # refuse a conflicting proof before writing anything
        dst = os.path.join(a.to, name + ".head.json")
        old = None
        if os.path.isfile(dst):
            try:
                with open(dst, encoding="utf-8") as f:
                    old = json.load(f)
            except ValueError:
                old = None
        if isinstance(old, dict) and (old.get("VersionId"), _utc(old.get("LastModified"))) != (
                writes[name]["VersionId"], writes[name]["LastModified"]):
            print("REFUSED: %s exists with another proof (VersionId %s); remove it first" % (dst, old.get("VersionId")),
                  file=sys.stderr)
            return 2
    for name in sorted(writes):
        print("%s %s.head.json: VersionId %s LastModified %s (from %s)" % (
            "would write" if a.dry_run else "wrote", name, writes[name]["VersionId"], writes[name]["LastModified"],
            writes[name]["StagedFrom"]))
        if not a.dry_run:
            with open(os.path.join(a.to, name + ".head.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps(writes[name], indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

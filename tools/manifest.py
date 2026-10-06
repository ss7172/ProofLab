#!/usr/bin/env python3
"""MANIFEST.json for the Evidence Pack: SHA-256 and size of every file, plus a verify mode.

  python3 manifest.py build  <evidence_dir>   # writes <evidence_dir>/MANIFEST.json
  python3 manifest.py verify <evidence_dir>   # exit 0 = unchanged; 1 = changed/missing/unlisted files

Lets a stranger check that the pack was not changed after hand-in. It is a checksum
list, not a signature or hash chain (those are out of scope for the hackathon).
Standard library only; Python 3.9+.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Union

MANIFEST_NAME = "MANIFEST.json"
SCHEMA = "ifabric.evidence-manifest/v1"
_CHUNK = 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _files(root: Path) -> List[Path]:
    return sorted((p for p in root.rglob("*") if p.is_file() and not p.is_symlink()
                   and p.relative_to(root).as_posix() != MANIFEST_NAME),
                  key=lambda p: p.relative_to(root).as_posix())


def _entries(root: Path) -> List[dict]:
    return [{"path": p.relative_to(root).as_posix(), "sha256": _sha256(p), "bytes": p.stat().st_size}
            for p in _files(root)]


def build_manifest(root: Union[str, Path]) -> dict:
    root = Path(root)
    manifest = {"schema": SCHEMA,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "algorithm": "sha256", "files": _entries(root)}
    (root / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_manifest(root: Union[str, Path]) -> Dict[str, List[str]]:
    root = Path(root)
    listed = {e["path"]: e["sha256"] for e in json.loads((root / MANIFEST_NAME).read_text())["files"]}
    present = {e["path"]: e["sha256"] for e in _entries(root)}
    return {"changed": sorted(p for p in listed if p in present and present[p] != listed[p]),
            "missing": sorted(p for p in listed if p not in present),
            "unlisted": sorted(p for p in present if p not in listed)}


def main(argv: List[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("build", "verify"):
        print("usage: manifest.py build|verify <evidence_dir>", file=sys.stderr)
        return 2
    command, root = argv
    if command == "build":
        manifest = build_manifest(root)
        print(f"OK: {len(manifest['files'])} files listed in {Path(root) / MANIFEST_NAME}")
        return 0
    result = verify_manifest(root)
    problems = [f"{kind}: {path}" for kind, paths in result.items() for path in paths]
    print("\n".join(problems) if problems else "OK: every file matches MANIFEST.json")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

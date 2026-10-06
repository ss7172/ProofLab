"""MANIFEST.json: SHA-256 of every evidence file, and a verify mode a judge can run."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from manifest import MANIFEST_NAME, build_manifest, verify_manifest

TOOL = Path(__file__).resolve().parents[1] / "manifest.py"


@pytest.fixture()
def pack(tmp_path: Path) -> Path:
    (tmp_path / "raw" / "gateway").mkdir(parents=True)
    (tmp_path / "raw" / "gateway" / "calls.jsonl").write_text('{"run":"FM-B"}\n')
    (tmp_path / "gap-list.md").write_text("# gaps\n")
    return tmp_path


def test_build_lists_every_file_with_sha256_and_size(pack):
    manifest = build_manifest(pack)
    paths = [entry["path"] for entry in manifest["files"]]
    assert paths == ["gap-list.md", "raw/gateway/calls.jsonl"]          # sorted, posix, relative
    entry = manifest["files"][1]
    assert len(entry["sha256"]) == 64 and entry["bytes"] == len('{"run":"FM-B"}\n')
    assert json.loads((pack / MANIFEST_NAME).read_text())["files"] == manifest["files"]


def test_manifest_never_lists_itself(pack):
    build_manifest(pack)
    build_manifest(pack)
    assert MANIFEST_NAME not in [e["path"] for e in json.loads((pack / MANIFEST_NAME).read_text())["files"]]


def test_verify_passes_on_an_untouched_pack(pack):
    build_manifest(pack)
    assert verify_manifest(pack) == {"changed": [], "missing": [], "unlisted": []}


def test_verify_reports_changed_missing_and_unlisted_files(pack):
    build_manifest(pack)
    (pack / "gap-list.md").write_text("# gaps (edited)\n")
    (pack / "raw" / "gateway" / "calls.jsonl").unlink()
    (pack / "late-addition.txt").write_text("x")
    assert verify_manifest(pack) == {"changed": ["gap-list.md"], "missing": ["raw/gateway/calls.jsonl"],
                                     "unlisted": ["late-addition.txt"]}


def test_cli_exit_codes(pack):
    assert subprocess.run([sys.executable, str(TOOL), "build", str(pack)]).returncode == 0
    assert subprocess.run([sys.executable, str(TOOL), "verify", str(pack)]).returncode == 0
    (pack / "gap-list.md").write_text("tampered")
    result = subprocess.run([sys.executable, str(TOOL), "verify", str(pack)], capture_output=True, text=True)
    assert result.returncode == 1 and "changed: gap-list.md" in result.stdout

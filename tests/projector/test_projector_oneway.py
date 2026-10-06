"""One-way: the projector never writes into its source and nothing in prooflab/ reads the projection back."""
import os
import re

import pytest

import _pack_fixture as fx
from prooflab.pack import projector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_out_must_be_apart_from_src(tmp_path):
    src = fx.build(str(tmp_path / "src"))
    for bad in (src, os.path.join(src, "console"), str(tmp_path)):
        with pytest.raises(ValueError):
            projector.project(src, bad)


def test_source_tree_is_untouched(tmp_path):
    src = fx.build(str(tmp_path / "src"))
    def snap():
        return dict((os.path.join(d, f), os.path.getmtime(os.path.join(d, f))) for d, _, fs in os.walk(src) for f in fs)
    before = snap()
    projector.project(src, str(tmp_path / "out"), as_of="2026-10-06T09:00:00Z")
    assert snap() == before


def test_grep_nothing_reads_the_projection_back():
    """No prooflab/ module imports the projector or index (except the pack package itself), and none opens the
    projection's files (pack-index.json, records/, projection-report.json) as input."""
    offenders = []
    for d, _, files in os.walk(os.path.join(ROOT, "prooflab")):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(d, f)
            rel = os.path.relpath(path, ROOT)
            if rel in (os.path.join("prooflab", "pack", "projector.py"), os.path.join("prooflab", "pack", "index.py")):
                continue
            text = open(path, encoding="utf-8", errors="replace").read()
            if re.search(r"pack\s+import\s+(projector|index)|pack\.(projector|index)\b|import\s+(projector|index)\b", text):
                offenders.append((rel, "imports the projector"))
    assert offenders == [], offenders


def test_projector_never_reads_its_own_output():
    text = open(os.path.join(ROOT, "prooflab", "pack", "projector.py"), encoding="utf-8").read()
    reads = re.findall(r"_read_(?:json|jsonl|bytes)\(([^)]*)\)", text)
    assert reads and not any("out" in re.findall(r"\b\w+\b", r) for r in reads), reads
    assert "pack-index.json" not in " ".join(reads)


def test_no_threshold_literals_in_the_modules():
    for name in ("projector.py", "index.py"):
        text = open(os.path.join(ROOT, "prooflab", "pack", name), encoding="utf-8").read()
        assert not re.search(r"\b(60000|300000|25000|50000|10000)\b", text)

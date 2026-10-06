"""Every projected file validates against Arth's contracts.schema.json with 0 errors (stdlib validator on 3.9)."""
import glob
import json
import os

import pytest

import _pack_fixture as fx
import _projector_schema as sch
from prooflab.pack import projector

DEFS = {"assessments": "assessment", "records": "evidenceRecord"}


@pytest.fixture()
def proj(tmp_path):
    src = fx.build(str(tmp_path / "src"))
    out = str(tmp_path / "out")
    res = projector.project(src, out, as_of="2026-10-06T09:00:00Z")
    return src, out, res


def _files(out, top):
    return sorted(glob.glob(os.path.join(out, top, "**", "*.json"), recursive=True))


def test_every_projected_file_validates_zero_errors(proj):
    src, out, res = proj
    schema = sch.load_schema()
    checked = 0
    for top, name in DEFS.items():
        files = _files(out, top)
        assert files, "no %s projected" % top
        for path in files:
            errs = sch.validate_def(json.load(open(path)), name, schema)
            assert errs == [], (path, errs[:5])
            checked += 1
    idx = json.load(open(os.path.join(out, "pack-index.json")))
    assert sch.validate_def(idx, "packIndex", schema) == []
    assert checked >= 8


def test_validator_catches_a_real_error(proj):
    _, out, _ = proj
    idx = json.load(open(os.path.join(out, "pack-index.json")))
    del idx["integrity"]
    idx["claim"]["verdict"] = "MAYBE"
    errs = sch.validate_def(idx, "packIndex")
    assert any("integrity" in e for e in errs) and any("MAYBE" in e for e in errs)


def test_arth_examples_validate_with_our_validator():
    """Anchors the mini validator: Arth's own examples must pass it (they pass jsonschema)."""
    ex = os.path.join(sch.repo_root(), "handoffs", "ifabric-handoff-3", "evidence-console-plan", "examples")
    pairs = (("pack-index.json", "packIndex"), ("evidence-record.C16.FM-B.c-0015.json", "evidenceRecord"),
             ("assessment.C16.run.FM-B.r1.json", "assessment") if os.path.exists(os.path.join(ex, "assessment.C16.run.FM-B.r1.json")) else None)
    for pair in pairs:
        if pair and os.path.exists(os.path.join(ex, pair[0])):
            assert sch.validate_def(json.load(open(os.path.join(ex, pair[0]))), pair[1]) == [], pair

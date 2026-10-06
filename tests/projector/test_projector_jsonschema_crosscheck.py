"""Cross-check: the same projected files pass the real `jsonschema` package (Draft 2020-12) on the pinned 3.12 stack.
Skipped when that interpreter is absent (the stdlib validator in _projector_schema is the primary check on 3.9)."""
import json
import os
import subprocess

import pytest

import _pack_fixture as fx
from prooflab.pack import projector

PY312 = os.path.expanduser("~/firstmate-homes/TrustworthyAI/workshop-local/.venv-strands312/bin/python")
SCRIPT = r'''
import glob, json, sys
from jsonschema import Draft202012Validator
schema = json.load(open(sys.argv[1])); out = sys.argv[2]; n = 0
def check(doc, name):
    global n
    errs = list(Draft202012Validator({"$ref": "#/$defs/" + name, "$defs": schema["$defs"]}).iter_errors(doc)); n += 1
    assert not errs, (name, [e.message for e in errs][:3])
for top, name in (("records", "evidenceRecord"), ("assessments", "assessment")):
    for p in glob.glob(out + "/" + top + "/**/*.json", recursive=True):
        check(json.load(open(p)), name)
check(json.load(open(out + "/pack-index.json")), "packIndex")
print(n)
'''


@pytest.mark.skipif(not os.path.exists(PY312), reason="3.12 stack not present")
def test_jsonschema_package_agrees(tmp_path):
    src = fx.build(str(tmp_path / "src"))
    out = str(tmp_path / "out")
    projector.project(src, out, as_of="2026-10-06T09:00:00Z")
    schema = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "handoffs", "ifabric-handoff-3", "evidence-console-plan", "schemas", "contracts.schema.json")
    r = subprocess.run([PY312, "-c", SCRIPT, schema, out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
    assert int(r.stdout.strip()) >= 8

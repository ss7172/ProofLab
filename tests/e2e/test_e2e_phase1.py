"""PR-27: the offline Phase-1 rehearsal under pytest. One subprocess run of tools/rehearse_phase1.sh (the
/usr/bin/python3 the judge uses); every row must be PASS or XFAIL (an XFAIL names a defect in merged code)."""
import json
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "tools", "rehearse_phase1.sh")


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("rehearsal") / "rows.json")
    p = subprocess.run(["bash", SCRIPT, "--json", out], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=600)
    with open(out) as fh:
        doc = json.load(fh)
    return p.returncode, p.stdout.decode("utf-8", "replace"), doc


def test_no_step_fails(result):
    rc, text, doc = result
    fails = [r for r in doc["rows"] if r["status"] == "FAIL"]
    assert rc == 0 and not fails, text


def test_every_stage_ran(result):
    _, text, doc = result
    assert not [r for r in doc["rows"] if r["status"] == "SKIP"], text
    assert len(doc["rows"]) >= 50


def test_xfails_name_a_known_defect(result):
    _, _, doc = result
    for r in doc["rows"]:
        if r["status"] == "XFAIL":
            did = r["note"].split("]", 1)[0].lstrip("[")
            assert did in doc["defects"], r


def test_query_answers_from_the_fresh_unzip(result):
    _, _, doc = result
    rows = dict((r["step"], r["status"]) for r in doc["rows"])
    for step in ("query C16 run N2 (BREACHED) from the fresh unzip", "query C7 run N4 (BREACHED) from the fresh unzip",
                 "planted tokens in the 3 ARCH 9.3 paths: 0 hits in the pack", "tools/manifest.py verify",
                 "manifest verify on the fresh unzip"):
        assert rows.get(step) == "PASS", step

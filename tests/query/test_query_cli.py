import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
import contextlib

import pytest

import prooflab
import prooflab.contract
from prooflab.contract import verdicts as V
from prooflab.query import cli, engine

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures", "pack")
CID1 = "ifabric-run-1791260000-ab12cd"     # C16 BREACHED
CID2 = "ifabric-run-1791261000-cd34ef"     # C16 SATISFIED
CID3 = "ifabric-adv-1791262000-ee55aa"
REF = "customer-1791250000-0a0a0a"
ROOT = os.path.dirname(os.path.dirname(HERE))
WIN = "2026-10-06T05:00:00Z..2026-10-06T09:00:00Z"


def _zip_unzip(tmp_path):
    z = str(tmp_path / "evidence.zip")
    with zipfile.ZipFile(z, "w") as zf:
        for base, _, files in os.walk(FIX):
            for f in files:
                full = os.path.join(base, f)
                zf.write(full, os.path.join("evidence", os.path.relpath(full, FIX)))
    out = tmp_path / "unzipped"
    with zipfile.ZipFile(z) as zf:
        zf.extractall(str(out))
    return str(out / "evidence")


@pytest.fixture()
def pack_dir(tmp_path):
    return _zip_unzip(tmp_path)


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(argv)
    return code, buf.getvalue()


def test_control_run_breached_prints_every_field(pack_dir):
    code, out = run(["--pack", pack_dir, "--control", "C16", "--run", CID1])
    assert code == V.exit_code("BREACHED") == 1
    for needle in ("rule:", "control version: C16-v1", "T1 proof 2026-10-06T03:55:00Z", "owner: Sree", "population:",
                   "measured: 121500", "vs limit: 50000", "overshoot 71500", "exceptions:", "VERDICT: BREACHED (NOT SATISFIED; kit: BREACH",
                   "gaps:", "records:", "who acted:", "decision at EP-1", "human loop: finding ESCALATED", "recompute:"):
        assert needle in out, needle


def test_control_run_satisfied_exit_zero(pack_dir):
    code, out = run(["--pack", pack_dir, "--control", "c16", "--run", CID2])
    assert code == 0 and "VERDICT: SATISFIED (SATISFIED; kit: PASS" in out


def test_unknown_run_unsupported_control_and_not_assessed_exit_2(pack_dir):
    assert run(["--pack", pack_dir, "--control", "C16", "--run", "nope-1"])[0] == 2
    assert run(["--pack", pack_dir, "--control", "C99", "--run", CID1])[0] == 2
    code, out = run(["--pack", pack_dir, "--control", "C16", "--run", CID3])   # known run, no assessment
    assert code == 2 and "not assessed" in out and V.exit_code("NOT_ASSESSED") == 2
    assert run(["--pack", pack_dir, "--control", "C16"])[0] == 2


def test_exit_code_comes_from_contract(pack_dir, monkeypatch):
    monkeypatch.setattr(V, "exit_code", lambda v: 7)
    assert run(["--pack", pack_dir, "--control", "C16", "--run", CID2])[0] == 7


def test_window_c7_c16_c9(pack_dir):
    code, out = run(["--pack", pack_dir, "--control", "C7", "--window", WIN])
    assert code == 1 and "WINDOW VERDICT: BREACHED" in out and "2 counted" in out
    code, out = run(["--pack", pack_dir, "--control", "C16", "--window", WIN])
    assert code == 1 and "1 breached" in out and "listed, not counted: %s" % CID3 in out and "by provenance (BASELINE)" in out
    code, out = run(["--pack", pack_dir, "--control", "C9", "--window", WIN])
    assert code == 0 and "hour" in out and "WINDOW VERDICT: SATISFIED" in out


def test_window_rules_empty_missing_tolerance_and_bounds(pack_dir):
    code, out = run(["--pack", pack_dir, "--control", "C7", "--window", "2026-10-07T00:00:00Z..2026-10-07T01:00:00Z"])
    assert code == 2 and "NOT_ASSESSED" in out and "empty denominator" in out
    assert run(["--pack", pack_dir, "--control", "C7", "--window", "garbage"])[0] == 2
    # a register without exception_tolerance and a breach in the window: INDETERMINATE, never a silent pass
    p = os.path.join(pack_dir, "register", "versions", "v1.yaml")
    text = open(p).read().replace("    exception_tolerance: 0\n", "")
    open(p, "w").write(text)
    code, out = run(["--pack", pack_dir, "--control", "C7", "--window", WIN])
    assert code == 2 and "exception_tolerance missing" in out


def test_incident_six_questions_and_out_of_scope(pack_dir):
    code, out = run(["--pack", pack_dir, "--incident", CID1])
    assert code == 0
    for q in ("WHO acted", "WHO owns it", "WHAT it touched", "AUTHORIZED", "APPROVED", "INTEGRITY", "RECONSTRUCT"):
        assert q in out
    assert "stated limit:" in out and "owned by Sree" in out
    code, out = run(["--pack", pack_dir, "--incident", "2026-10-06T06:31:00Z"])   # a time inside CID2
    assert code == 0 and CID2 in out
    code, out = run(["--pack", pack_dir, "--incident", REF])
    assert code == 0 and "out of scope (scope_rule, inventory version inv-1)" in out
    assert run(["--pack", pack_dir, "--incident", "no-such-run"])[0] == 2


def test_runs_catalogue_is_labelled(pack_dir):
    code, out = run(["--pack", pack_dir, "--runs"])
    assert code == 0 and "4 runs" in out and "reference trio" in out and "ours: ifabric trio" in out and "unlabelled" not in out
    os.remove(os.path.join(pack_dir, "derived", "run-catalogue.jsonl"))
    code, out = run(["--pack", pack_dir, "--runs"])
    assert code == 0 and "no run catalogue in this pack" in out


def test_risk_inventory_claim_listings(pack_dir):
    code, out = run(["--pack", pack_dir, "--risk"])
    assert code == 0 and "R-C16" in out and "C16 %s BREACHED" % CID1 in out
    assert run(["--pack", pack_dir, "--risk", "R-none"])[0] == 2
    code, out = run(["--pack", pack_dir, "--inventory"])
    assert code == 0 and "ifabric-customer" in out and "nemotron-synthetic" in out
    code, out = run(["--pack", pack_dir, "--claim"])
    assert code == 0 and "C-FM-01" in out and "full coverage: 3 of 3" in out


def test_json_output_and_empty_pack(pack_dir, tmp_path):
    code, out = run(["--pack", pack_dir, "--control", "C16", "--run", CID1, "--json"])
    assert code == 1 and json.loads(out)["verdict"] == "BREACHED"
    empty = str(tmp_path / "empty")
    os.makedirs(empty)
    assert run(["--pack", empty, "--control", "C16", "--run", CID1])[0] == 2
    assert run(["--pack", empty, "--runs"])[0] == 0


def test_recompute_mismatch_is_flagged(pack_dir, monkeypatch):
    pack = engine.Pack(pack_dir)
    ans = engine.control_run(pack, "C16", CID1, recompute_fn=lambda p, c, cid: {"verdict": "SATISFIED"})
    assert "MISMATCH" in ans["recompute"] and ans["verdict"] == "BREACHED"
    ans = engine.control_run(pack, "C16", CID1, recompute_fn=lambda p, c, cid: {"verdict": "BREACHED"})
    assert ans["recompute"] == "matches stored verdict"


def test_latest_revision_replaces(pack_dir):
    d = os.path.join(pack_dir, "assessments", "C16")
    a = json.load(open(os.path.join(d, os.listdir(d)[0])))
    a["assessment_id"] = a["assessment_id"].replace(":r1", ":r2")
    a["requirement_verdict"] = "BREACHED"
    a["measured"]["value"] = 99999
    json.dump(a, open(os.path.join(d, "r2.json"), "w"))
    code, out = run(["--pack", pack_dir, "--control", "C16", "--run", CID2])
    assert code == 1 and "99999" in out


def test_fresh_unzip_runs_as_module_on_py39_in_under_5s(tmp_path):
    """The DONE check: cd <unzipped>/evidence && python3 -m prooflab query --control C16 --run <CID>."""
    ev = _zip_unzip(tmp_path)
    contract_root = os.path.dirname(os.path.dirname(prooflab.contract.__file__))   # the dir holding contract/
    tool = os.path.join(ev, "prooflab")
    os.makedirs(tool)
    for name in ("__init__.py", "__main__.py", "cli.py"):
        shutil.copy(os.path.join(contract_root, name), tool)
    for sub in ("contract", "registry"):
        shutil.copytree(os.path.join(contract_root, sub), os.path.join(tool, sub), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(ROOT, "prooflab", "query"), os.path.join(tool, "query"), ignore=shutil.ignore_patterns("__pycache__"))
    env = dict((k, v) for k, v in os.environ.items() if k != "PYTHONPATH")
    started = time.time()
    proc = subprocess.run([sys.executable, "-m", "prooflab", "query", "--control", "C16", "--run", CID1],
                          cwd=ev, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    elapsed = time.time() - started
    assert proc.returncode == 1, proc.stderr
    assert "VERDICT: BREACHED" in proc.stdout and elapsed < 5
    for argv in (["--runs"], ["--incident", CID2], ["--control", "C7", "--window", WIN]):
        p2 = subprocess.run([sys.executable, "-m", "prooflab", "query"] + argv, cwd=ev, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        assert p2.returncode in (0, 1), p2.stderr


def test_no_verdict_literals_outside_query_and_evaluators():
    """All verdict semantics live in prooflab/query and prooflab/evaluators (contract and Arth's code excluded)."""
    pat = re.compile(r"""["'](SATISFIED|BREACHED|INDETERMINATE)["']""")
    skip = {"contract", "evaluators", "query", "servicenow", "tests", "__pycache__"}
    bad = []
    for base, dirs, files in os.walk(os.path.join(ROOT, "prooflab")):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith(".py") and pat.search(open(os.path.join(base, f)).read()):
                bad.append(os.path.join(base, f))
    assert bad == []


def test_no_threshold_literals_and_no_network_in_query_code():
    src = ""
    for f in ("engine.py", "cli.py"):
        src += open(os.path.join(ROOT, "prooflab", "query", f)).read()
    assert not re.search(r"\b(socket|urllib|subprocess|requests|http\.client|boto3)\b", src)
    assert not re.search(r"(cap|limit|threshold)\w*\s*[=<>]=?\s*\d{3,}", src)

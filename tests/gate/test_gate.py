"""tools/gate.sh: every check passes on a clean temp tree and fails on a planted violation (T0.4)."""
import base64
import gzip
import hashlib
import os
import subprocess
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[2] / "tools" / "gate.sh"
CORE_TEXT = "def decide_inline(q, pin):\n    return 'proceed'\n"
CORE_SHA = hashlib.sha256(CORE_TEXT.encode()).hexdigest()


def write(root, rel, text):
    p = Path(str(root)) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def run_gate(root, *extra):
    env = dict(os.environ)
    proc = subprocess.run(["bash", str(GATE), "--no-scan", "--no-tests", "--root", str(root)] + list(extra),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=env)
    return proc.returncode, proc.stdout


def bundle_text(sha, pad=0):
    return 'C16_CORE_SHA256 = "%s"\nx = "%s"\n' % (sha, "".join(chr(97 + (i * 7919) % 26) for i in range(pad)))


@pytest.fixture()
def clean(tmp_path):
    write(tmp_path, "prooflab/evaluators/c16_core.py", CORE_TEXT)
    write(tmp_path, "prooflab/evaluators/c16.py", "def assess(register):\n    return register['limit']\n")
    write(tmp_path, "adapters/runtime/model_call.py", "from prooflab.evaluators.c16_core import evaluate\n")
    write(tmp_path, "agents/ifabric-it/ifabric-it.py", bundle_text(CORE_SHA))
    write(tmp_path, "prooflab/console/server.py", "PORT = 8080\n")
    return tmp_path


def test_clean_tree_all_green_scan_skipped_exit_3(clean):
    rc, out = run_gate(clean)
    assert "FAIL" not in out, out
    assert "SCAN SKIPPED" in out
    assert rc == 3


def test_empty_tree_is_na_not_failure(tmp_path):
    rc, out = run_gate(tmp_path)
    assert "FAIL" not in out and rc == 3, out


@pytest.mark.parametrize("line", [
    "TOKEN_CAP = 25000\n",
    "limit: int = 50000\n",
    "self.max_threshold = 0.5\n",
])
@pytest.mark.parametrize("where", ["prooflab/evaluators/c7.py", "adapters/x.py", "agents/ifabric-it/helper.py"])
def test_threshold_literal_fails(clean, where, line):
    write(clean, where, line)
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  no threshold literal" in out, out


def test_threshold_from_register_and_comparison_pass(clean):
    write(clean, "adapters/ok.py", "cap = register['cap']\nif used == 5:\n    pass\nretries = 3\n")
    rc, out = run_gate(clean)
    assert "FAIL" not in out, out


def test_evaluate_import_elsewhere_fails(clean):
    write(clean, "adapters/runtime/tool_call.py", "from prooflab.evaluators.c16_core import decide_inline, evaluate\n")
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  evaluate imported only" in out, out


def test_evaluate_plain_import_elsewhere_fails(clean):
    write(clean, "prooflab/adapters/other.py", "import evaluate\n")
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  evaluate imported only" in out, out


def test_embedded_sha_mismatch_fails(clean):
    write(clean, "agents/ifabric-it/ifabric-it.py", bundle_text("0" * 64))
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  embedded c16 core sha256" in out, out


def test_embedded_sha_missing_marker_fails(clean):
    write(clean, "agents/ifabric-it/ifabric-it.py", "M = {'prooflab.evaluators.c16_core': 'abc'}\n")
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  embedded c16 core sha256" in out, out


def test_bundle_over_24000_fails(clean):
    import random
    rnd = random.Random(1)
    noise = "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(40000))
    write(clean, "agents/ifabric-it/ifabric-it.py", bundle_text(CORE_SHA) + 'y = "%s"\n' % noise)
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  every agents/ifabric-*/ bundle" in out, out
    assert "FAIL  embedded" not in out


def test_bundle_size_boundary_passes(clean):
    text = bundle_text(CORE_SHA)
    assert len(base64.b64encode(gzip.compress(text.encode(), 9, mtime=0))) <= 24000
    rc, out = run_gate(clean)
    assert "FAIL" not in out, out


def test_file_named_agent_py_fails(clean):
    write(clean, "agents/ifabric-it/agent.py", "x = 1\n")
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  no file named agent.py" in out, out


def test_approve_true_fails(clean):
    needle = "approve" + "=True"
    write(clean, "tools/make_agents.py", "spec = dict(%s)\n" % needle)
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  no approve" in out, out


def test_console_secret_fails_per_pattern(clean):
    patterns = [
        "AK" + "IA" + "A" * 16,
        "aws_secret" + "_access_key",
        "tk" + "n=" + "abc",
        "-----BEGIN " + "RSA PRIV" + "ATE KEY-----",
        "gh" + "p_" + "a" * 24,
        "Bea" + "rer " + "a" * 24,
    ]
    for pat in patterns:
        write(clean, "prooflab/console/static/app.js", "var x = '%s';\n" % pat)
        rc, out = run_gate(clean)
        assert rc == 1 and "FAIL  console AT-06" in out, (pat[:6], out)
    (clean / "prooflab/console/static/app.js").unlink()
    rc, out = run_gate(clean)
    assert "FAIL" not in out, out


def test_secret_in_console_does_not_leak_into_output(clean):
    write(clean, "prooflab/console/a.js", "x='%s'\n" % ("AK" + "IA" + "B" * 16))
    rc, out = run_gate(clean)
    assert "B" * 16 not in out


def test_scan_missing_script_fails(clean, monkeypatch):
    monkeypatch.setenv("SCAN_SCRIPT", str(clean / "nope.sh"))
    proc = subprocess.run(["bash", str(GATE), "--no-tests", "--root", str(clean)], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    assert proc.returncode == 1 and "secret scan script missing" in proc.stdout


def test_scan_must_print_result_clean(clean, monkeypatch):
    fake = clean / "scan_ok.sh"
    fake.write_text("#!/bin/bash\necho 'RESULT: clean'\n")
    monkeypatch.setenv("SCAN_SCRIPT", str(fake))
    proc = subprocess.run(["bash", str(GATE), "--no-tests", "--root", str(clean)], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    assert proc.returncode == 0 and "GATE: green" in proc.stdout, proc.stdout
    fake.write_text("#!/bin/bash\necho 'RESULT: NOT CLEAN'\n")
    proc = subprocess.run(["bash", str(GATE), "--no-tests", "--root", str(clean)], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    assert proc.returncode == 1


def test_failure_beats_scan_skipped(clean):
    write(clean, "agents/ifabric-it/agent.py", "")
    rc, _ = run_gate(clean)
    assert rc == 1


# ---- two-stage layout (D-B), assurance exemption, buildspec size -------------------------------------------
def noise_text(n=40000):
    import random
    rnd = random.Random(2)
    return 'y = "%s"\n' % "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(n))


@pytest.fixture()
def two_stage(clean):
    (clean / "agents/ifabric-it/ifabric-it.py").unlink()
    write(clean, "agents/ifabric-base/ifabric-base.py", bundle_text(CORE_SHA))
    write(clean, "agents/ifabric-it/ifabric-it.py", "from prooflab.evaluators.c16_core import decide_inline\n")
    write(clean, "agents/ifabric-assurance/ifabric-assurance.py", "print('assurance, no core')\n")
    return clean


def test_two_stage_clean_passes_with_na_for_role_bundles(two_stage):
    rc, out = run_gate(two_stage)
    assert "FAIL" not in out and rc == 3, out
    assert "SHA OK agents/ifabric-base/ifabric-base.py" in out
    assert "SHA NA agents/ifabric-it/ifabric-it.py" in out
    assert "SHA NA agents/ifabric-assurance/ifabric-assurance.py" in out


def test_base_without_core_fails(two_stage):
    write(two_stage, "agents/ifabric-base/ifabric-base.py", "print('loader only')\n")
    rc, out = run_gate(two_stage)
    assert rc == 1 and "FAIL  embedded c16 core sha256" in out and "SHA FAIL agents/ifabric-base" in out, out


def test_base_wrong_sha_fails(two_stage):
    write(two_stage, "agents/ifabric-base/ifabric-base.py", bundle_text("1" * 64))
    rc, out = run_gate(two_stage)
    assert rc == 1 and "SHA FAIL agents/ifabric-base" in out, out


def test_role_bundle_embedding_core_needs_matching_marker(two_stage):
    write(two_stage, "agents/ifabric-it/ifabric-it.py", bundle_text("2" * 64))
    rc, out = run_gate(two_stage)
    assert rc == 1 and "SHA FAIL agents/ifabric-it" in out, out
    write(two_stage, "agents/ifabric-it/ifabric-it.py", bundle_text(CORE_SHA))
    rc, out = run_gate(two_stage)
    assert "FAIL" not in out and "SHA OK agents/ifabric-it" in out, out


def test_assurance_exempt_from_sha_but_not_from_size(two_stage):
    write(two_stage, "agents/ifabric-assurance/ifabric-assurance.py", noise_text())
    rc, out = run_gate(two_stage)
    assert rc == 1 and "FAIL  every agents/ifabric-*/ bundle" in out, out
    assert "FAIL  embedded" not in out and "SIZE FAIL agents/ifabric-assurance" in out, out


def test_size_reported_per_file(two_stage):
    rc, out = run_gate(two_stage)
    for f in ("ifabric-base/ifabric-base.py", "ifabric-it/ifabric-it.py", "ifabric-assurance/ifabric-assurance.py"):
        assert "SIZE OK agents/" + f in out, out


def test_role_bundle_over_size_fails_even_without_core(two_stage):
    write(two_stage, "agents/ifabric-it/ifabric-it.py", noise_text())
    rc, out = run_gate(two_stage)
    assert rc == 1 and "SIZE FAIL agents/ifabric-it" in out, out


@pytest.mark.parametrize("where", ["tools/base-buildspec.yml", "agents/ifabric-it/buildspec.yml",
                                   "agents/ifabric-base/buildspec-base.yml"])
def test_buildspec_over_limit_fails(clean, where):
    write(clean, where, "x: " + "a" * 25600 + "\n")
    rc, out = run_gate(clean)
    assert rc == 1 and "FAIL  every buildspec <= 25600" in out and "SPEC FAIL " + where in out, out


def test_buildspec_at_limit_passes(clean):
    write(clean, "tools/it-buildspec.yml", "a" * 25600)
    rc, out = run_gate(clean)
    assert "FAIL" not in out and "PASS  every buildspec" in out, out
    write(clean, "tools/it-buildspec.yml", "a" * 25601)
    rc, out = run_gate(clean)
    assert rc == 1


def test_no_buildspec_is_na(clean):
    rc, out = run_gate(clean)
    assert "N/A   buildspec" in out and "FAIL" not in out

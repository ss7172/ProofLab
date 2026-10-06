"""PR-43: gate checks that keep Arth's code byte-identical and the whole tree integrated (each fails on a planted violation)."""
import os
import subprocess
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[2] / "tools" / "gate.sh"
INTEG = Path(__file__).resolve().parents[2] / "tools" / "integration_check.sh"
H = "handoffs/ifabric-handoff-3"
NEMO = "class AnalyzerError(Exception):\n    pass\n"
FILES = {  # repo path -> (handoff path, text)
    "prooflab/servicenow/a.py": (H + "/code/prooflab/servicenow/a.py", "A = 1\n"),
    "prooflab/servicenow/nemotron.py": (H + "/code/prooflab/servicenow/nemotron.py", NEMO),
    "prooflab/tests/test_a.py": (H + "/code/prooflab/tests/test_a.py", "def test_a():\n    assert True\n"),
    "prooflab/console/panel_vendor/ifabric-case-panel.js": (H + "/code/prooflab/servicenow/panel/ifabric-case-panel.js", "js\n"),
    "prooflab/console/panel_vendor/ifabric-case-panel.css": (H + "/code/prooflab/servicenow/panel/ifabric-case-panel.css", "css\n"),
    "prooflab/servicenow/panel/ifabric-case-panel.js": (H + "/code/prooflab/servicenow/panel/ifabric-case-panel.js", "js\n"),
    "prooflab/servicenow/panel/ifabric-case-panel.css": (H + "/code/prooflab/servicenow/panel/ifabric-case-panel.css", "css\n"),
    "tools/manifest.py": (H + "/deliverables/evidence-pack/tools/manifest.py", "M = 1\n"),
}


def write(root, rel, text):
    p = Path(str(root)) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def gate(root, *extra, **env):
    e = dict(os.environ, **env)
    p = subprocess.run(["bash", str(GATE), "--no-scan", "--root", str(root)] + list(extra), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True, env=e)
    return p.returncode, p.stdout


@pytest.fixture()
def tree(tmp_path):
    for rel, (href, text) in FILES.items():
        write(tmp_path, rel, text)
        write(tmp_path, href, text)
    write(tmp_path, "agents/ifabric-assurance/ifabric-assurance.py", "_SOURCES = {'prooflab.servicenow.nemotron': %r}\n" % NEMO)
    return tmp_path


def identity(root):
    return gate(root, "--no-tests", "--no-integration")


def test_identical_tree_passes(tree):
    rc, out = identity(tree)
    assert "FAIL" not in out and "PASS  Arth byte-identity" in out and "ARTH OK embedded nemotron.py" in out, out
    assert rc == 3


def test_tree_without_handoffs_is_na(tmp_path):
    rc, out = identity(tmp_path)
    assert "FAIL" not in out and "ARTH NA all" in out, out


@pytest.mark.parametrize("mutate", [
    lambda t: write(t, "prooflab/servicenow/a.py", "A = 2\n"),                      # servicenow edited
    lambda t: write(t, "prooflab/servicenow/extra.py", "X = 1\n"),                  # servicenow file added
    lambda t: os.remove(str(t / "prooflab/servicenow/a.py")),                       # servicenow file removed
    lambda t: write(t, "prooflab/tests/test_no_threshold_literals.py", "x = 1\n"),  # foreign file in Arth's tests
    lambda t: write(t, "prooflab/tests/test_a.py", "def test_a():\n    pass\n"),    # Arth test edited
    lambda t: write(t, "prooflab/console/panel_vendor/ifabric-case-panel.js", "js2\n"),
    lambda t: write(t, "prooflab/console/panel_vendor/ifabric-case-panel.css", "css2\n"),
    lambda t: write(t, "agents/ifabric-assurance/ifabric-assurance.py", "_SOURCES = {'prooflab.servicenow.nemotron': 'x'}\n"),
    lambda t: write(t, "tools/manifest.py", "M = 2\n"),
])
def test_planted_difference_fails(tree, mutate):
    mutate(tree)
    rc, out = identity(tree)
    assert rc == 1 and "FAIL  Arth byte-identity" in out, out


def test_pycache_is_ignored(tree):
    write(tree, "prooflab/tests/__pycache__/x.cpython-39.pyc", "junk")
    rc, out = identity(tree)
    assert "FAIL" not in out, out


def test_arth_suite_exact_count(tree):
    rc, out = gate(tree, "--no-integration", ARTH_PASS_COUNT="1")
    assert "PASS  Arth suite" in out and "FAIL" not in out, out
    rc, out = gate(tree, "--no-integration", ARTH_PASS_COUNT="152")
    assert rc == 1 and "FAIL  Arth suite" in out, out


def test_arth_suite_failure_fails(tree):
    write(tree, "prooflab/tests/test_a.py", "def test_a():\n    assert False\n")
    write(tree, H + "/code/prooflab/tests/test_a.py", "def test_a():\n    assert False\n")
    rc, out = gate(tree, "--no-integration", ARTH_PASS_COUNT="1")
    assert rc == 1 and "FAIL  Arth suite" in out, out


# ---- integration stage -------------------------------------------------------------------------------------------

def stub(root, name, body):
    p = write(root, name, body)
    return str(p)


@pytest.fixture()
def prod(tmp_path):
    write(tmp_path, "tests/e2e/rehearse.py", "print('TOTAL: 68 PASS, 0 FAIL, 0 XFAIL, 0 SKIP')\n")
    return tmp_path


def integ(root, dry):
    e = dict(os.environ, REHEARSE_PY="/usr/bin/python3", DRYRUN_SH=dry)
    p = subprocess.run(["bash", str(INTEG), "--root", str(root)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, env=e)
    return p.returncode, p.stdout


def test_integration_green(prod, tmp_path):
    dry = stub(tmp_path, "d/dry.sh", "echo 'TOTAL: 64 PASS, 0 FAIL, 10 other'\n")
    rc, out = integ(prod, dry)
    assert rc == 0 and "FAIL" not in out, out


def test_integration_na_when_dryrun_absent(prod):
    rc, out = integ(prod, "/nonexistent/dryrun.sh")
    assert rc == 0 and "N/A   integration: ops-lane runbook dryrun.sh" in out, out


def test_integration_rehearse_fail_fails(prod, tmp_path):
    write(prod, "tests/e2e/rehearse.py", "print('TOTAL: 67 PASS, 1 FAIL, 0 XFAIL, 0 SKIP')\n")
    rc, out = integ(prod, "/nonexistent")
    assert rc == 1 and "FAIL  integration: tests/e2e/rehearse.py" in out, out


def test_integration_rehearse_without_total_fails(prod):
    write(prod, "tests/e2e/rehearse.py", "print('crashed')\n")
    rc, out = integ(prod, "/nonexistent")
    assert rc == 1 and "FAIL  integration: tests/e2e/rehearse.py" in out, out


def test_integration_dryrun_fail_fails(prod, tmp_path):
    dry = stub(tmp_path, "d/dry.sh", "echo 'TOTAL: 60 PASS, 4 FAIL, 10 other'\n")
    rc, out = integ(prod, dry)
    assert rc == 1 and "FAIL  integration: ops-lane runbook dryrun.sh" in out, out


def test_integration_dryrun_nonzero_exit_fails(prod, tmp_path):
    dry = stub(tmp_path, "d/dry.sh", "echo 'TOTAL: 64 PASS, 0 FAIL, 10 other'\nexit 1\n")
    rc, out = integ(prod, dry)
    assert rc == 1, out


def test_gate_runs_integration_when_forced_and_fails_on_it(prod):
    write(prod, "tests/e2e/rehearse.py", "print('TOTAL: 1 PASS, 1 FAIL')\n")
    rc, out = gate(prod, "--no-tests", "--integration", DRYRUN_SH="/nonexistent")
    assert rc == 1 and "FAIL  integration stage" in out, out


def test_gate_skips_integration_with_no_tests_by_default(prod):
    write(prod, "tests/e2e/rehearse.py", "print('TOTAL: 1 PASS, 1 FAIL')\n")
    rc, out = gate(prod, "--no-tests")
    assert "integration stage" not in out.replace("SKIP  integration stage", "") and rc == 3, out

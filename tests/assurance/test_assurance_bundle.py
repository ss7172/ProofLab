"""G-01: the generated one-file handler: size gate, Arth's nemotron.py byte-identical, nothing else of his, the name."""
import ast
import base64
import gzip
import os
import re
import subprocess
import sys

from assurance_support import ARTH_NEMOTRON, BUNDLE, ROOT

BUNDLER = os.path.join(ROOT, "tools", "bundle_assurance.py")


def _sources():
    tree = ast.parse(open(BUNDLE, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "_SOURCES":
            return ast.literal_eval(node.value)
    raise AssertionError("no _SOURCES literal in the bundle")


def test_bundler_rebuild_matches_the_committed_file_and_is_under_the_gate(tmp_path):
    out = tmp_path / "ifabric-assurance.py"
    proc = subprocess.run([sys.executable, BUNDLER, "--out", str(out)], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    assert proc.returncode == 0, proc.stderr
    assert out.read_bytes() == open(BUNDLE, "rb").read()  # deterministic; the committed file is current
    check = subprocess.run([sys.executable, BUNDLER, "--check"], stdout=subprocess.PIPE, universal_newlines=True)
    assert check.returncode == 0 and '"up to date"' in check.stdout


def test_gzip_base64_size_is_within_the_ci_gate():
    data = open(BUNDLE, "rb").read()
    size = len(base64.b64encode(gzip.compress(data, 9, mtime=0)))
    assert size <= 24000, size


def test_arths_nemotron_is_embedded_byte_identical():
    sources = _sources()
    master = open(ARTH_NEMOTRON, "rb").read()
    assert sources["prooflab.servicenow.nemotron"].encode("utf-8") == master
    synced = os.path.join(ROOT, "prooflab", "servicenow", "nemotron.py")
    if os.path.exists(synced):  # after PR-00: the repo copy is the same bytes too
        assert open(synced, "rb").read() == master


def test_nothing_else_of_arths_is_embedded():
    sources = _sources()
    assert sorted(sources) == ["prooflab", "prooflab.servicenow", "prooflab.servicenow.nemotron"]
    assert sources["prooflab"] == "" and sources["prooflab.servicenow"] == ""


def test_the_shim_follows_the_loader_verbatim():
    shim = open(os.path.join(ROOT, "agents", "ifabric-assurance", "assurance_shim.py"), encoding="utf-8").read()
    assert open(BUNDLE, encoding="utf-8").read().endswith(shim)


def test_no_forbidden_file_name_and_the_bundler_refuses_one(tmp_path):
    forbidden = "agent" + ".py"
    hits = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ROOT, "agents")) for f in fs if f == forbidden]
    assert hits == []
    proc = subprocess.run([sys.executable, BUNDLER, "--out", str(tmp_path / forbidden)], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    assert proc.returncode == 2 and not (tmp_path / forbidden).exists()


def test_no_threshold_literal_in_the_shim():  # the gate's own pattern (tools/gate.sh, PR-00)
    pat = re.compile(r"(cap|limit|threshold|ceiling)[a-z0-9_]*\s*(:[^=#]*)?=\s*-?[0-9]", re.I)
    shim = open(os.path.join(ROOT, "agents", "ifabric-assurance", "assurance_shim.py"), encoding="utf-8").read()
    assert [l for l in shim.splitlines() if pat.search(l) and not re.search(r"[=!<>]=\s*-?[0-9]", l)] == []

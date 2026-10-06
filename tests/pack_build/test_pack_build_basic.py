"""PR-21 tests. Manifest tool: tools/manifest.py in the repo, else PR-00's worktree
(PROOFLAB_MANIFEST_PY). Run: PYTHONPATH=<PR-01 wt>:<this wt> $PY39 -m pytest -q -p no:cacheprovider tests/pack_build
"""
import filecmp
import json
import os
import subprocess
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
_PR00 = "/Users/satyabratsrikumar/firstmate-homes/TrustworthyAI/wt/PR-00-setup/tools/manifest.py"
MANIFEST = os.environ.get("PROOFLAB_MANIFEST_PY") or (
    os.path.join(REPO, "tools", "manifest.py") if os.path.isfile(os.path.join(REPO, "tools", "manifest.py")) else _PR00)
if not os.path.isfile(MANIFEST):
    pytest.skip("tools/manifest.py not available", allow_module_level=True)
os.environ["PROOFLAB_MANIFEST_PY"] = MANIFEST
sys.path.insert(0, REPO)
from prooflab.pack import build  # noqa: E402

# Fake values assembled at runtime (never literal secrets).
TOK = "synthetic-" + "ledger" + "-token-0123456789abcdef"
KEY = "synthetic-" + "gateway" + "-value-fedcba98765"
WRAPPER = os.path.join(REPO, "tools", "submit_wrapper.sh")


def _w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


@pytest.fixture
def inputs(tmp_path):
    src, wd, tool = tmp_path / "src", tmp_path / "wd", tmp_path / "toolsrc"
    with open(os.path.join(HERE, "fixtures", "records.derived.jsonl")) as f:
        _w(str(src / "store" / "records.jsonl"), f.read())
    _w(str(src / "raw" / "aws-spans" / "a.json"), '{"synthetic": true}\n')
    _w(str(src / "derived" / "observations.jsonl"), "{}\n")
    _w(str(src / "assessments" / "C16" / "x.json"), "{}\n")
    cr = {"items": [{"metadata": {"annotations": {
              "kubectl.kubernetes.io/last-applied-configuration": json.dumps({"t": TOK}),
              "kopf.zalando.org/last-handled-configuration": json.dumps({"t": TOK})}},
          "spec": {"awsAgentCore": {"environmentVariables": {"AUDIT_WRITE_TOKEN": TOK}}}}]}
    _w(str(src / "raw" / "cr-status" / "cr.json"), json.dumps(cr))
    _w(str(src / "register" / "versions" / "v1.yaml"), "controls: []\n")
    _w(str(wd / "register.yaml"), "controls: []\n")
    _w(str(wd / "gap-list.md"), "# gaps\n")
    _w(str(wd / "run-ids.txt"), "cid-1\ncid-2\n")
    _w(str(tool / "__init__.py"), "")
    return src, wd, tool, tmp_path


def _build(inputs, out, env_vals=None):
    src, wd, tool, _ = inputs
    if env_vals:
        os.environ["PROOFLAB_SCAN_VALUES"] = "\n".join(env_vals)
    else:
        os.environ.pop("PROOFLAB_SCAN_VALUES", None)
    try:
        return build.main(["build", "--out", str(out), "--src", str(src), "--workdir", str(wd),
                           "--tool-src", str(tool)])
    finally:
        os.environ.pop("PROOFLAB_SCAN_VALUES", None)


def _verify(d):
    return subprocess.run([sys.executable, MANIFEST, "verify", str(d)], capture_output=True, text=True)


def test_build_stages_layout_and_verifies(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out, [TOK, KEY]) == 0
    for rel in ("store/records.jsonl", "raw", "derived", "assessments", "register", "run-ids.txt",
                "gap-list.md", "README.md", "prooflab/__init__.py", "MANIFEST.json"):
        assert (out / rel).exists(), rel
    assert _verify(out).returncode == 0


def test_three_cr_paths_zero_hits(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out, [TOK]) == 0
    assert build.scan_tree(str(out), [TOK]) == []
    assert TOK.encode() not in (out / "raw" / "cr-status" / "cr.json").read_bytes()


def test_workdir_copies_match_cmp(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    wd = inputs[1]
    assert filecmp.cmp(str(wd / "gap-list.md"), str(out / "gap-list.md"), shallow=False)
    assert filecmp.cmp(str(wd / "run-ids.txt"), str(out / "run-ids.txt"), shallow=False)
    assert filecmp.cmp(str(wd / "register.yaml"), str(out / "register" / "versions" / "v1.yaml"), shallow=False)


def test_dirty_scan_blocks_manifest(inputs):
    src = inputs[0]
    _w(str(src / "derived" / "leak.txt"), "oops " + KEY + "\n")
    out = inputs[3] / "pack"
    assert _build(inputs, out, [KEY]) == 1
    assert not (out / "MANIFEST.json").exists()


def test_tampered_byte_fails_verify(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    p = out / "run-ids.txt"
    p.write_bytes(p.read_bytes().replace(b"cid-1", b"cid-9"))
    assert _verify(out).returncode == 1  # ADV-R-03


def _stub(tmp_path):
    bindir = tmp_path / "bin"
    _w(str(bindir / "submit.sh"), "#!/bin/sh\necho SUBMITTED \"$@\"\n")
    os.chmod(str(bindir / "submit.sh"), 0o755)
    return bindir


def _run_wrapper(args, tmp_path, vals=""):
    env = dict(os.environ, PATH=str(_stub(tmp_path)) + os.pathsep + os.environ["PATH"],
               PROOFLAB_PYTHON=sys.executable, PROOFLAB_REPO=REPO, PROOFLAB_MANIFEST_PY=MANIFEST,
               PROOFLAB_SCAN_VALUES=vals)
    return subprocess.run(["bash", WRAPPER] + args, capture_output=True, text=True, env=env)


def test_wrapper_dry_run_clean_then_dirty(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    r = _run_wrapper(["--dry-run", "--evidence", str(out), "team-x"], inputs[3], KEY)
    assert r.returncode == 0 and "DRY-RUN" in r.stdout and "submit.sh team-x" in r.stdout
    (out / "derived" / "late.txt").write_text(KEY)  # planted after build: dirty and unlisted
    r = _run_wrapper(["--dry-run", "--evidence", str(out), "team-x"], inputs[3], KEY)
    assert r.returncode != 0 and "REFUSED" in r.stderr and "SUBMITTED" not in r.stdout
    assert KEY not in r.stdout + r.stderr


def test_wrapper_refuses_tampered_pack(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    (out / "run-ids.txt").write_text("changed\n")
    r = _run_wrapper(["--dry-run", "--evidence", str(out), "t"], inputs[3])
    assert r.returncode != 0 and "manifest verify failed" in r.stderr


def test_readback(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    z = inputs[3] / "sub.zip"
    with zipfile.ZipFile(str(z), "w") as zf:
        for d, _, names in os.walk(str(out)):
            for n in names:
                p = os.path.join(d, n)
                zf.write(p, os.path.join("evidence", os.path.relpath(p, str(out))))
        zf.writestr("MANIFEST.txt", "platform list\n")
    r = _run_wrapper(["--readback", str(z)], inputs[3], KEY)
    assert r.returncode == 0 and "READBACK OK" in r.stdout
    with zipfile.ZipFile(str(z), "a") as zf:
        zf.writestr("register.yaml", "leak " + KEY + "\n")  # outside the evidence tree, still scanned
    r = _run_wrapper(["--readback", str(z)], inputs[3], KEY)
    assert r.returncode != 0 and "REFUSED" in r.stderr


def test_no_threshold_or_secret_literals():
    src = open(os.path.join(REPO, "prooflab", "pack", "build.py")).read()
    assert "AKIA" not in src and "BEGIN " + "PRIVATE" not in src

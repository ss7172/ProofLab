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


# Fake pre-push scan: reports a hit when any file under the dir contains the marker in FAKE_SCAN_NEEDLE.
FAKE_SCAN = """#!/usr/bin/env bash
d="$1"
if [ -n "${FAKE_SCAN_NEEDLE:-}" ] && grep -rIlF -- "$FAKE_SCAN_NEEDLE" "$d" >/dev/null 2>&1; then
  echo "   X: 1 file(s)"; echo "RESULT: NOT CLEAN"; exit 1
fi
echo "$d" >> "${FAKE_SCAN_LOG:-/dev/null}"
echo "RESULT: clean"; exit 0
"""


def _run_wrapper(args, tmp_path, needle="", extra_env=None):
    scan = tmp_path / "fake-scan.sh"
    _w(str(scan), FAKE_SCAN)
    env = dict(os.environ, PATH=str(_stub(tmp_path)) + os.pathsep + os.environ["PATH"],
               PROOFLAB_PYTHON=sys.executable, PROOFLAB_REPO=REPO, PROOFLAB_MANIFEST_PY=MANIFEST,
               PROOFLAB_PREPUSH_SCAN=str(scan), FAKE_SCAN_NEEDLE=needle,
               FAKE_SCAN_LOG=str(tmp_path / "scanlog.txt"))
    env.update(extra_env or {})
    return subprocess.run(["bash", WRAPPER] + args, capture_output=True, text=True, env=env)


def test_wrapper_dry_run_clean_then_dirty(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    r = _run_wrapper(["--dry-run", "--evidence", str(out), "team-x"], inputs[3], KEY)
    assert r.returncode == 0 and "DRY-RUN" in r.stdout and "submit.sh team-x" in r.stdout
    (out / "derived" / "late.txt").write_text(KEY)  # planted after build
    r = _run_wrapper(["--dry-run", "--evidence", str(out), "team-x"], inputs[3], KEY)
    assert r.returncode != 0 and "REFUSED" in r.stderr and "SUBMITTED" not in r.stdout
    assert KEY not in r.stdout + r.stderr


def test_wrapper_refuses_tampered_pack(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    (out / "run-ids.txt").write_text("changed\n")
    r = _run_wrapper(["--dry-run", "--evidence", str(out), "t"], inputs[3], KEY)
    assert r.returncode != 0 and "manifest verify failed" in r.stderr


def test_wrapper_needs_no_injected_values_and_scans_dir_workdir_zip(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    z = inputs[3] / "pre.zip"
    _zip(out, z)
    env = dict(os.environ)
    env.pop("PROOFLAB_SCAN_VALUES", None)
    r = _run_wrapper(["--dry-run", "--evidence", str(out), "--workdir", str(inputs[1]), "--zip", str(z)],
                     inputs[3])
    assert r.returncode == 0 and "DRY-RUN" in r.stdout, r.stderr
    log = (inputs[3] / "scanlog.txt").read_text().split()
    assert str(out) in log and str(inputs[1]) in log and len(log) == 3   # evidence, workdir, unzipped copy
    # a dirty value inside the zip (the scan can't read zips: the unzipped copy is scanned)
    with zipfile.ZipFile(str(z), "a") as zf:
        zf.writestr("leak.txt", "leak " + KEY + "\n")
    r = _run_wrapper(["--dry-run", "--evidence", str(out), "--zip", str(z)], inputs[3], KEY)
    assert r.returncode != 0 and "scan not clean" in r.stderr


def test_wrapper_refuses_scan_not_clean_without_result_line(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    scan = inputs[3] / "noresult.sh"
    _w(str(scan), "#!/bin/sh\necho hello\nexit 0\n")
    r = _run_wrapper(["--dry-run", "--evidence", str(out)], inputs[3], extra_env={"PROOFLAB_PREPUSH_SCAN": str(scan)})
    assert r.returncode != 0 and "scan not clean" in r.stderr


def test_wrapper_team_default_and_key_layout(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    r = _run_wrapper(["--dry-run", "--evidence", str(out)], inputs[3])
    assert "submit.sh ifabric" in r.stdout
    assert build.TEAM_NAME == "ifabric" and build.KEY_PREFIX == "submissions/ifabric/"
    src = open(WRAPPER).read()
    assert 'TEAM_DEFAULT="ifabric"' in src and "submissions/%s/" in src


def _zip(out, z):
    with zipfile.ZipFile(str(z), "w") as zf:
        for d, _, names in os.walk(str(out)):
            for n in names:
                p = os.path.join(d, n)
                zf.write(p, os.path.join("evidence", os.path.relpath(p, str(out))))
        zf.writestr("MANIFEST.txt", "platform list\n")


AWS_SHIM = r"""#!/bin/sh
# fake aws: logs argv; head-object returns the VersionId and ETag from files; get-object copies SRC to the outfile
echo "$@" >> "$AWS_LOG"
case "$*" in
  *--version-id*) echo "AccessDenied: s3:GetObjectVersion" >&2; exit 255 ;;
  *head-object*) n=$(cat "$AWS_DIR/n" 2>/dev/null || echo 0); echo $((n+1)) > "$AWS_DIR/n"
     if [ -f "$AWS_DIR/change_after" ] && [ "$n" -ge 1 ]; then printf 'v2\t"etag1"\n'; else printf 'v1\t"etag1"\n'; fi ;;
  *get-object*) case "$*" in *--if-match\ etag1*) ;; *) echo "no if-match" >&2; exit 255 ;; esac
     for last; do :; done; cp "$AWS_DIR/remote.zip" "$last"; echo '{}' ;;
  *) exit 1 ;;
esac
"""


def _aws(tmp_path, remote_zip):
    d = tmp_path / "awsdir"
    d.mkdir(exist_ok=True)
    (d / "remote.zip").write_bytes(open(str(remote_zip), "rb").read())
    _w(str(tmp_path / "bin" / "aws"), AWS_SHIM)
    os.chmod(str(tmp_path / "bin" / "aws"), 0o755)
    return {"AWS_DIR": str(d), "AWS_LOG": str(tmp_path / "aws.log")}


def test_readback(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    z = inputs[3] / "sub.zip"
    _zip(out, z)
    r = _run_wrapper(["--readback", str(z)], inputs[3], KEY)
    assert r.returncode == 0 and "READBACK OK" in r.stdout
    with zipfile.ZipFile(str(z), "a") as zf:
        zf.writestr("register.yaml", "leak " + KEY + "\n")  # outside the evidence tree, still scanned
    r = _run_wrapper(["--readback", str(z)], inputs[3], KEY)
    assert r.returncode != 0 and "REFUSED" in r.stderr


def test_readback_s3_if_match_bracketed_by_head_object(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    z = inputs[3] / "sub.zip"
    _zip(out, z)
    env = _aws(inputs[3], z)
    r = _run_wrapper(["--readback", str(z), "--bucket", "bkt"], inputs[3], extra_env=env)
    assert r.returncode == 0 and "READBACK OK" in r.stdout, r.stderr
    calls = [l.split() for l in open(env["AWS_LOG"]).read().splitlines()]
    verbs = [c[1] for c in calls]
    assert verbs == ["head-object", "get-object", "head-object"]
    assert "--if-match" in calls[1] and "etag1" in calls[1]
    assert "--version-id" not in " ".join(sum(calls, []))
    assert "submissions/ifabric/sub.zip" in calls[0]          # default key from the team constant


def test_readback_refuses_changed_version_or_bad_sha(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    z = inputs[3] / "sub.zip"
    _zip(out, z)
    env = _aws(inputs[3], z)
    open(os.path.join(env["AWS_DIR"], "change_after"), "w").close()
    r = _run_wrapper(["--readback", str(z), "--bucket", "bkt"], inputs[3], extra_env=env)
    assert r.returncode != 0 and "changed during the download" in r.stderr
    os.remove(os.path.join(env["AWS_DIR"], "change_after"))
    open(os.path.join(env["AWS_DIR"], "n"), "w").write("0")
    with zipfile.ZipFile(env["AWS_DIR"] + "/remote.zip", "a") as zf:    # remote differs from the local zip
        zf.writestr("extra.txt", "x")
    r = _run_wrapper(["--readback", str(z), "--bucket", "bkt"], inputs[3], extra_env=env)
    assert r.returncode != 0 and "sha256 differs" in r.stderr


def test_no_threshold_or_secret_literals():
    src = open(os.path.join(REPO, "prooflab", "pack", "build.py")).read()
    assert "AK" + "IA" not in src and "BEGIN " + "PRIV" not in src


def test_build_reports_scan_skipped_without_values(inputs, capsys):
    assert _build(inputs, inputs[3] / "pack") == 0
    assert "scan skipped: no values" in capsys.readouterr().out


def test_jsonl_token_paths_redacted(inputs):
    src = inputs[0]
    line = {"metadata": {"annotations": {"kubectl.kubernetes.io/last-applied-configuration": TOK}}}
    _w(str(src / "raw" / "cr.jsonl"), json.dumps(line) + "\n" + json.dumps(line) + "\n")
    out = inputs[3] / "pack"
    assert _build(inputs, out, [TOK]) == 0
    assert TOK.encode() not in (out / "raw" / "cr.jsonl").read_bytes()


def test_unparseable_cr_status_file_fails_build(inputs):
    src = inputs[0]
    _w(str(src / "raw" / "cr-status" / "bad.yaml"), "x: kubectl.kubernetes.io/last-applied-configuration\n")
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 1
    assert not (out / "MANIFEST.json").exists()
    _w(str(src / "raw" / "cr-status" / "bad.yaml"), "ok: 1\n")
    _w(str(src / "raw" / "cr-status" / "broken.json"), "{not json")
    assert _build(inputs, inputs[3] / "pack2") == 1


# ---- PR-34 ----
def _build_args(inputs, out, *extra, drop_versions=False, register=None):
    src, wd, tool, _ = inputs
    if drop_versions:
        import shutil
        shutil.rmtree(str(src / "register" / "versions"))
    if register is not None:
        _w(str(wd / "register.yaml"), register)
    os.environ.pop("PROOFLAB_SCAN_VALUES", None)
    return build.main(["build", "--out", str(out), "--src", str(src), "--workdir", str(wd),
                       "--tool-src", str(tool)] + list(extra))


def test_pack_ships_manifest_tool_and_lists_it(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    assert (out / "tools" / "manifest.py").is_file()
    listed = [e["path"] for e in json.load(open(str(out / "MANIFEST.json")))["files"]]
    assert "tools/manifest.py" in listed
    # the README's own commands work inside the pack
    r = subprocess.run([sys.executable, "tools/manifest.py", "verify", "."], cwd=str(out),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    out2 = inputs[3] / "pack-real-tool"      # with the real prooflab/ the pack verifies itself
    assert build.main(["build", "--out", str(out2), "--src", str(inputs[0]), "--workdir", str(inputs[1])]) == 0
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.'); "
                        "from prooflab.pack import build; sys.exit(build.main(['verify', '.']))"],
                       cwd=str(out2), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_unfrozen_register_refused_with_and_without_versions_folder(inputs, capsys):
    # (a) versions/ staged but different register.yaml: refuse, exit 2, nothing built
    out = inputs[3] / "p1"
    assert _build_args(inputs, out, register="controls: [x]\n") == 2
    assert not (out / "MANIFEST.json").exists()
    assert "refusing to present it as frozen" in capsys.readouterr().err
    # (b) no versions/ folder at all: refuse (was: silently copied as versions/register.yaml)
    out = inputs[3] / "p2"
    assert _build_args(inputs, out, drop_versions=True) == 2
    assert not (out / "register").exists()


def test_allow_draft_register_stages_draft_with_note(inputs):
    out = inputs[3] / "p3"
    assert _build_args(inputs, out, "--allow-draft-register", drop_versions=True) == 0
    assert (out / "register" / "draft" / "register.yaml").is_file()
    assert (out / "register" / "versions" / "NO-VERSION-FROZEN.md").is_file()
    assert not [n for n in os.listdir(str(out / "register" / "versions")) if n.endswith(".yaml")]
    out = inputs[3] / "p4"          # versions/ present but not matching: still draft, with the note
    assert _build_args(inputs, out, "--allow-draft-register", register="controls: [y]\n") == 0
    assert (out / "register" / "draft" / "register.yaml").read_text() == "controls: [y]\n"
    assert (out / "register" / "versions" / "NO-VERSION-FROZEN.md").is_file()


def test_submit1_path_src_v1_frozen_no_draft(inputs):
    out = inputs[3] / "p5"
    assert _build_args(inputs, out) == 0           # register.yaml == --src register/versions/v1.yaml
    assert (out / "register" / "versions" / "v1.yaml").is_file()
    assert not (out / "register" / "draft").exists()
    assert not (out / "register" / "versions" / "NO-VERSION-FROZEN.md").exists()


def test_pack_verify_ignores_pycache_but_manifest_tool_does_not(inputs):
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    _w(str(out / "prooflab" / "__pycache__" / "x.cpython-39.pyc"), "b")
    assert build.main(["verify", str(out)]) == 0
    assert _verify(out).returncode == 1            # tools/manifest.py (Arth's copy) stays untouched
    _w(str(out / "prooflab" / "other.py"), "x")    # a real unlisted file still fails
    assert build.main(["verify", str(out)]) == 1


def test_builder_never_copies_pycache(inputs):
    tool = inputs[2]
    _w(str(tool / "__pycache__" / "a.pyc"), "b")
    out = inputs[3] / "pack"
    assert _build(inputs, out) == 0
    assert not (out / "prooflab" / "__pycache__").exists()


def test_readme_template_has_bytecode_guidance_and_manifest_tool_identical():
    t = open(os.path.join(REPO, "evidence-templates", "README.md")).read()
    assert "PYTHONDONTWRITEBYTECODE=1" in t
    arth = os.path.join(REPO, "handoffs", "ifabric-handoff-3", "deliverables", "evidence-pack", "tools", "manifest.py")
    if os.path.isfile(arth):
        assert filecmp.cmp(arth, os.path.join(REPO, "tools", "manifest.py"), shallow=False)

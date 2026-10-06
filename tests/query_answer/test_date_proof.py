"""PR-48: the rule's date proof has three states; only a T1 proof later than the scope may read 'DATED AFTER'.

N1 under register v1.1 showed 'RULE DATED AFTER TEST' because the pack lacked register/versions/v1.1.head.json.
"""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

from prooflab.pack import build
from prooflab.query import answer as A
from prooflab.query import engine as E
from prooflab.query import render_text as R

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(ROOT, "tests", "query", "fixtures", "pack")
CID2 = "ifabric-run-1791261000-cd34ef"     # C16 SATISFIED, scope start 2026-10-06T06:30:00.000Z
NOW = "2026-10-06T09:00:00Z"
STAGE = os.path.join(ROOT, "tools", "stage_t1.py")


def _b64(path):
    return base64.b64encode(hashlib.sha256(open(path, "rb").read()).digest()).decode("ascii")


@pytest.fixture()
def pack_dir(tmp_path):
    dst = str(tmp_path / "pack")
    shutil.copytree(FIX, dst)
    os.remove(os.path.join(dst, "register", "v1.head.json"))      # each test states its own proof
    return dst


def _head(pack_dir, last_modified, checksum=None):
    v = os.path.join(pack_dir, "register", "versions", "v1.yaml")
    with open(os.path.join(pack_dir, "register", "versions", "v1.head.json"), "w") as f:
        json.dump({"VersionId": "JysDSBX6TiasKYLiBaLvuIDK1rNwb5_Q", "LastModified": last_modified, "ETag": "\"e\"",
                   "ChecksumSHA256": checksum or _b64(v), "Key": "ifabric/register/v1.yaml"}, f)


def _answer(pack_dir):
    d = A.ask(E.Pack(pack_dir), "Show me control 16 for run %s" % CID2, now=NOW)["doc"]
    return d, "\n".join(R.render_answer(d))


def test_proven_before_n1_shape(pack_dir):
    _head(pack_dir, "2026-10-06T05:38:05+00:00")             # S3 prints +00:00; read as ...Z
    d, text = _answer(pack_dir)
    dp = d["rule"]["date_proof"]
    assert dp["state"] == "PROVEN_BEFORE" and d["rule"]["date_before_scope"] is True
    assert dp["t1_at"] == "2026-10-06T05:38:05Z" and dp["version_id"] == "JysDSBX6TiasKYLiBaLvuIDK1rNwb5_Q"
    assert dp["key"] == "ifabric/register/v1.yaml" and dp["checksum_verified"] is True
    assert "dated before the scope (S3 T1 2026-10-06T05:38:05Z" in text
    assert d["audit_question"]["limit_in_force"]["flag"] == "OK"
    assert "AFTER" not in text and not [g for g in d["gaps"] if g["id"] == "G-T1"]


def test_proven_after(pack_dir):
    _head(pack_dir, "2026-10-06T07:00:00Z")
    d, text = _answer(pack_dir)
    assert d["rule"]["date_proof"]["state"] == "PROVEN_AFTER" and d["rule"]["date_before_scope"] is False
    assert "RULE DATED AFTER TEST" in text
    assert d["audit_question"]["limit_in_force"]["flag"] == "FLAG"


def test_no_head_json_is_not_proven_never_after(pack_dir):
    d, text = _answer(pack_dir)
    dp = d["rule"]["date_proof"]
    assert dp["state"] == "NOT_PROVEN" and d["rule"]["date_before_scope"] is False
    assert dp["register_frozen_at"] == "2026-10-06T03:52:10Z"
    assert "date proof not in this pack" in text and "unproven" in text
    assert "AFTER" not in text and "NOT proven before" not in text
    assert d["audit_question"]["limit_in_force"]["flag"] == "GAP"
    assert any(g["id"] == "G-T1" for g in d["gaps"])


def test_checksum_mismatch_is_not_proven(pack_dir):
    _head(pack_dir, "2026-10-06T05:38:05Z", checksum=base64.b64encode(b"\0" * 32).decode())
    d, text = _answer(pack_dir)
    assert d["rule"]["date_proof"]["state"] == "NOT_PROVEN" and d["rule"]["date_proof"]["checksum_verified"] is False
    assert "AFTER" not in text


# ---------------------------------------------------------------- tools/stage_t1.py
def _ops_lane(tmp_path, reg_bytes, tamper=False):
    ops, to = tmp_path / "ops" / "b4b" / "t1", tmp_path / "src" / "register" / "versions"
    ops.mkdir(parents=True)
    to.mkdir(parents=True)
    (to / "v1.1.yaml").write_bytes(reg_bytes)
    (to / "v1.1.risks.yaml").write_bytes(b"risks: []\n")
    good = hashlib.sha256(reg_bytes).digest()
    d = good if not tamper else hashlib.sha256(b"other").digest()

    def entry(key, digest, vid, lm):
        b = base64.b64encode(digest).decode()
        return {"file": key.rsplit("/", 1)[1], "key": key, "local_sha256_hex": digest.hex(), "local_sha256_b64": b,
                "head_object": {"VersionId": vid, "LastModified": lm, "ETag": "\"x\"", "ChecksumSHA256": b}}
    (ops / "t1-v1.1.json").write_text(json.dumps([
        entry("ifabric/register/v1.1.yaml", d, "JysDSBX6TiasKYLiBaLvuIDK1rNwb5_Q", "2026-10-06T13:38:05+00:00"),
        entry("ifabric/register/v1.1.risks.yaml", hashlib.sha256(b"risks: []\n").digest(), "risks-vid", "2026-10-06T13:38:12+00:00"),
        entry("ifabric/register/experiments/rules-v1.1.json", hashlib.sha256(b"r").digest(), "rules-vid", "2026-10-06T13:38:17+00:00"),
    ]))
    return tmp_path / "ops", to


def _stage(*args):
    return subprocess.run([sys.executable, STAGE] + [str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def test_stage_t1_picks_the_register_key(tmp_path):
    ops, to = _ops_lane(tmp_path, b"version: v1.1\n")
    r = _stage("--from", ops, "--to", to)
    assert r.returncode == 0, r.stderr
    h = json.loads((to / "v1.1.head.json").read_text())
    assert h["Key"] == "ifabric/register/v1.1.yaml" and h["VersionId"] == "JysDSBX6TiasKYLiBaLvuIDK1rNwb5_Q"
    assert h["LastModified"] == "2026-10-06T13:38:05Z"
    assert set(h) >= {"VersionId", "LastModified", "ETag", "ChecksumSHA256", "Key"}
    assert not (to / "v1.1.risks.head.json").exists()


def test_stage_t1_refuses_a_sha_mismatch(tmp_path):
    ops, to = _ops_lane(tmp_path, b"version: v1.1\n", tamper=True)
    r = _stage("--from", ops, "--to", to)
    assert r.returncode == 2 and "REFUSED" in r.stderr
    assert not (to / "v1.1.head.json").exists()


# ---------------------------------------------------------------- pack build
def _src(tmp_path, head):
    src, tool = tmp_path / "src", tmp_path / "tool"
    (src / "register" / "versions").mkdir(parents=True)
    (src / "register" / "versions" / "v1.yaml").write_text("controls: []\n")
    (src / "register" / "versions" / "v1.risks.yaml").write_text("risks: []\n")
    (src / "register" / "versions" / "inv-1.yaml").write_text("components: []\n")
    if head:
        (src / "register" / "versions" / "v1.head.json").write_text('{"VersionId": "x", "LastModified": "2026-10-06T00:00:00Z"}\n')
    tool.mkdir()
    (tool / "__init__.py").write_text("")
    return src, tool


def test_pack_build_refuses_a_version_without_t1(tmp_path, capsys):
    src, tool = _src(tmp_path, head=False)
    assert build._missing_t1(str(src)) == ["v1"]
    rc = build.main(["build", "--out", str(tmp_path / "out"), "--src", str(src), "--tool-src", str(tool)])
    assert rc == 2 and "stage_t1.py" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_pack_build_allow_missing_t1(tmp_path, capsys):
    src, tool = _src(tmp_path, head=False)
    rc = build.main(["build", "--out", str(tmp_path / "out"), "--src", str(src), "--tool-src", str(tool), "--allow-missing-t1"])
    assert rc == 0 and "NOT_PROVEN" in capsys.readouterr().out


def test_pack_build_with_t1(tmp_path):
    src, tool = _src(tmp_path, head=True)
    assert build._missing_t1(str(src)) == []

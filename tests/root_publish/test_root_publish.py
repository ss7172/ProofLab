"""PR-32: root published (unsigned). Offline: the fake ServiceNow only."""
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
from prooflab.pack import root_publish as rp  # noqa: E402
from prooflab.servicenow.client import ServiceNowClient  # noqa: E402
from prooflab.tests import fake_servicenow as fk  # noqa: E402

VID = "3sL4kqtJlcpXroDTDmJ-rmSpXd3dIbrHY"


@pytest.fixture
def snow():
    fake = fk.FakeServiceNow().start()
    sys_id = fake._create({"short_description": "pack root"})["sys_id"]
    client = ServiceNowClient(fake.base_url, fk.CLIENT_ID, fk.CLIENT_SECRET)
    yield fake, client, sys_id
    fake.stop()


@pytest.fixture
def pack(tmp_path):
    d = tmp_path / "pack"
    d.mkdir()
    (d / "a.txt").write_text("a")
    (d / "MANIFEST.json").write_text('{"files": []}\n')
    z = tmp_path / "pack.zip"
    with zipfile.ZipFile(str(z), "w") as zf:
        zf.write(str(d / "MANIFEST.json"), "MANIFEST.json")
        zf.write(str(d / "a.txt"), "a.txt")
    return d, z


def _sha(path):
    return hashlib.sha256(open(str(path), "rb").read()).hexdigest()


def test_hash_equals_recomputation(pack):
    d, z = pack
    assert rp.manifest_sha256(str(d)) == _sha(d / "MANIFEST.json")
    assert rp.manifest_sha256(str(z)) == _sha(d / "MANIFEST.json")
    out = io.StringIO()
    assert rp.main(["--recompute", str(d)], out=out) == 0
    assert out.getvalue().strip() == _sha(d / "MANIFEST.json")


def test_note_has_no_url_bucket_account_and_passes_secret_check(pack):
    d, z = pack
    text = rp.build_note("submit-1", rp.manifest_sha256(str(d)), _sha(z), VID)
    assert "://" not in text and "s3:" not in text and "amazonaws" not in text
    assert not rp._TWELVE_DIGITS.search(rp._HEX64.sub("", text))
    assert not rp.secret_shaped(text)
    assert text.splitlines()[0] == "pack root: submit-1"
    assert rp.HONEST_LINE in text and _sha(z) in text and VID in text


def test_a_hash_with_a_twelve_digit_run_is_accepted():
    h = "123456789012" + "a" * 52
    assert "123456789012" in rp.build_note("final", h, None, VID)


@pytest.mark.parametrize("bad", ["https://example.org/x", "bucket.s3.amazonaws.com", "arn:aws:s3:::b",
                                 "123456789012", "has space", "s3://b/k"])
def test_planted_url_or_account_in_version_id_refused(bad):
    with pytest.raises(rp.RefusedNote):
        rp.build_note("final", "a" * 64, None, bad)


def test_bad_label_and_secret_shaped_refused():
    with pytest.raises(rp.RefusedNote):
        rp.build_note("submit-3", "a" * 64, None, VID)
    with pytest.raises(rp.RefusedNote):
        rp.build_note("final", "a" * 64, None, "AK" + "IA" + "ABCDEFGHIJKLMNOP")


def test_one_patch_with_only_work_notes_and_sidecar(snow, pack, tmp_path):
    fake, client, sys_id = snow
    d, z = pack
    calls = []
    orig = client._api

    def spy(method, path, params=None, body=None):
        calls.append((method, body))
        return orig(method, path, params, body)
    client._api = spy
    side = tmp_path / "evidence" / "pack-root.json"
    code, rec = rp.publish("submit-2", str(d), VID, sys_id, client, zip_path=str(z), sidecar=str(side))
    assert code == 0 and fake.patch_count == 1
    patches = [c for c in calls if c[0] == "PATCH"]
    assert len(patches) == 1 and list(patches[0][1]) == ["work_notes"]
    data = json.load(open(str(side)))
    for k in ("label", "manifest_sha256", "zip_sha256", "s3_version_id", "servicenow_incident_number",
              "note_journal_time", "note_text_sha256"):
        assert data[k], k
    assert data["manifest_sha256"] == _sha(d / "MANIFEST.json") and data["zip_sha256"] == _sha(z)
    assert data["servicenow_incident_number"].startswith("INC")


def test_sidecar_not_in_manifest_and_refused_inside_pack(snow, pack):
    fake, client, sys_id = snow
    d, z = pack
    with pytest.raises(rp.RefusedNote):
        rp.publish("final", str(d), VID, sys_id, client, sidecar=str(d / "pack-root.json"))
    assert fake.patch_count == 0
    assert "pack-root.json" not in (d / "MANIFEST.json").read_text()


def test_readback_picks_the_right_entry(snow, pack, tmp_path):
    fake, client, sys_id = snow
    d, _ = pack
    fake.add_journal_entry(sys_id, "someone", "unrelated note", "2026-10-05 08:00:00")
    text = rp.build_note("final", rp.manifest_sha256(str(d)), None, VID)
    fake.add_journal_entry(sys_id, "someone", "x" + text, "2026-10-05 09:00:00")  # look-alike, not equal
    code, rec = rp.publish("final", str(d), VID, sys_id, client, sidecar=str(tmp_path / "e" / "pack-root.json"))
    assert code == 0
    assert rec["note_journal_time"] == "2026-10-05 11:01:00"  # the fake's first PATCH note, not the look-alike


def test_journal_acl_falls_back_to_display_notes(snow, pack, tmp_path):
    fake, client, sys_id = snow
    d, _ = pack
    fake.journal_forbidden = True
    code, rec = rp.publish("final", str(d), VID, sys_id, client, sidecar=str(tmp_path / "pack-root.json"))
    assert code == 0 and rec["note_journal_time"] == "2026-10-05 11:01:00"


def test_readback_missing_is_reported(snow, pack, tmp_path):
    fake, client, sys_id = snow
    d, _ = pack
    fake.mangle_notes = True  # the instance shows something other than what we wrote
    fake.journal_forbidden = True
    code, rec = rp.publish("final", str(d), VID, sys_id, client, sidecar=str(tmp_path / "pack-root.json"))
    assert code == 1 and rec["note_journal_time"] is None and rec["readback"] != "matched"


def test_dry_run_posts_nothing(snow, pack):
    fake, client, sys_id = snow
    d, _ = pack
    out = io.StringIO()
    assert rp.main(["--label", "final", "--pack-dir", str(d), "--s3-version-id", VID, "--dry-run"],
                   client=client, out=out) == 0
    assert fake.patch_count == 0 and "root published (unsigned)" in out.getvalue()


def test_wrapper_prints_command_and_posts_nothing(pack, tmp_path):
    d, z = pack
    fake = tmp_path / "fake-scan.sh"     # never run the real pre-push scan from a test (it loads live secrets)
    fake.write_text("#!/bin/sh\necho 'RESULT: clean'\n")
    env = dict(os.environ, PROOFLAB_PREPUSH_SCAN=str(fake), PROOFLAB_PYTHON=sys.executable)
    subprocess.check_call([sys.executable, os.path.join(REPO, "tools", "manifest.py"), "build", str(d)],
                          stdout=subprocess.DEVNULL)
    z2 = tmp_path / "p2.zip"
    with zipfile.ZipFile(str(z2), "w") as zf:
        for f in os.listdir(str(d)):
            zf.write(str(d / f), f)
    r = subprocess.run(["bash", os.path.join(REPO, "tools", "submit_wrapper.sh"), "--readback", str(z2),
                        "--print-root-cmd", "final"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    assert r.returncode == 0, r.stderr
    assert "READBACK OK" in r.stdout and "pack root --label final --zip " + str(z2) in r.stdout

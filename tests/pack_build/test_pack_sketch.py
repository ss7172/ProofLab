"""D2: the checked-in sketch.png is staged; a missing one fails the build loudly. D7: findings/ is staged."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prooflab.pack import build  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_checked_in_sketch_is_a_png():
    with open(os.path.join(REPO, "evidence-templates", "sketch.png"), "rb") as fh:
        assert fh.read(8) == b"\x89PNG\r\n\x1a\n"


def test_findings_in_pack_top():
    assert "findings" in build.PACK_TOP


def test_missing_sketch_fails_loudly(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "_repo_root", lambda: str(tmp_path))
    rc = build.main(["build", "--out", str(tmp_path / "out"), "--tool-src", str(tmp_path)])
    assert rc == 2

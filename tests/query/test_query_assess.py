"""`python3 -m prooflab assess` (PR-25): cli.assess_main over the query fixture pack."""
import contextlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_query_cli import CID1, CID2, pack_dir  # noqa: E402,F401  (the fixture pack)

from prooflab.query import cli  # noqa: E402


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.assess_main(argv)
    return code, buf.getvalue()


def test_assess_every_run_breach_outranks_and_writes_answers(pack_dir, tmp_path):
    out = str(tmp_path / "answers")
    code, text = _run(["--pack", pack_dir, "--control", "C16", "--out", out])
    assert code == 1                                   # CID1 is a C16 breach
    assert "C16  %s BREACHED" % CID1 in text and "C16  %s SATISFIED" % CID2 in text
    with open(os.path.join(out, "C16", CID1 + ".json")) as f:
        assert json.load(f)["verdict"] == "BREACHED"


def test_assess_one_satisfied_run_json(pack_dir):
    code, text = _run(["--pack", pack_dir, "--control", "C16", "--run", CID2, "--json"])
    assert code == 0 and json.loads(text.splitlines()[0])["verdict"] == "SATISFIED"


def test_assess_empty_pack_is_not_assessed(tmp_path):
    assert _run(["--pack", str(tmp_path)])[0] == 2
    assert _run(["--help"])[0] == 0

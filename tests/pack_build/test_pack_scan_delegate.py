"""M10: `pack scan` delegates to the pre-push scan script when no values are injected; the injected-values path stays."""
import os
import stat
import subprocess
import sys

import pytest

from prooflab import cli
from prooflab.pack import build

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NEEDLE = "needle-" + "q7" * 5          # a synthetic marker for the stub, not a credential


def _stub(path, body):
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


CLEAN = 'echo "$1" >> "${STUB_LOG:-/dev/null}"\necho "RESULT: clean"\nexit 0\n'
DIRTY = 'echo "   X: 1 file(s)"\necho "RESULT: NOT CLEAN"\nexit 1\n'


@pytest.fixture()
def pack(tmp_path):
    d = tmp_path / "pack"
    d.mkdir()
    (d / "a.txt").write_text("nothing here\n")
    return d


@pytest.fixture(autouse=True)
def _no_real_scan(monkeypatch, tmp_path):
    monkeypatch.delenv("PROOFLAB_SCAN_VALUES", raising=False)
    monkeypatch.delenv("PROOFLAB_ALLOW_EMPTY_SCAN", raising=False)
    monkeypatch.setenv("PROOFLAB_PREPUSH_SCAN", str(tmp_path / "missing.sh"))     # never the real script from a test


def test_no_values_delegates_to_the_script_and_needs_result_clean(pack, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROOFLAB_PREPUSH_SCAN", _stub(tmp_path / "ok.sh", CLEAN))
    monkeypatch.setenv("STUB_LOG", str(tmp_path / "log.txt"))
    assert build.main(["scan", str(pack)]) == 0
    assert "RESULT: clean" in capsys.readouterr().out
    assert (tmp_path / "log.txt").read_text().split() == [str(pack)]


def test_dirty_script_blocks(pack, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROOFLAB_PREPUSH_SCAN", _stub(tmp_path / "dirty.sh", DIRTY))
    assert build.main(["scan", str(pack)]) == 1
    err = capsys.readouterr().err
    assert "REFUSED" in err and "NOT CLEAN" in err


def test_exit_zero_without_the_result_line_is_not_clean(pack, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROOFLAB_PREPUSH_SCAN", _stub(tmp_path / "quiet.sh", "echo hello\nexit 0\n"))
    assert build.main(["scan", str(pack)]) == 1


def test_missing_script_refuses(pack, capsys):
    assert build.main(["scan", str(pack)]) == 1
    assert "scan script not found" in capsys.readouterr().err


def test_injected_values_path_keeps_working_and_never_calls_the_script(pack, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PROOFLAB_PREPUSH_SCAN", _stub(tmp_path / "ok.sh", CLEAN))
    monkeypatch.setenv("STUB_LOG", str(tmp_path / "log.txt"))
    monkeypatch.setenv("PROOFLAB_SCAN_VALUES", NEEDLE)
    assert build.main(["scan", str(pack)]) == 0
    assert "0 hit(s)" in capsys.readouterr().out and not (tmp_path / "log.txt").exists()
    (pack / "b.txt").write_text("leak " + NEEDLE + "\n")
    assert build.main(["scan", str(pack)]) == 1
    assert NEEDLE not in capsys.readouterr().err


def test_allow_empty_scan_still_skips(pack, capsys):
    assert build.main(["scan", "--allow-empty-scan", str(pack)]) == 0
    assert "skipped: no values" in capsys.readouterr().out


def test_through_the_dispatcher_in_a_subprocess(pack, tmp_path):
    stub = _stub(tmp_path / "ok.sh", CLEAN)
    env = dict((k, v) for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG"))
    env.update(PROOFLAB_PREPUSH_SCAN=stub, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "prooflab", "pack", "scan", str(pack)], cwd=ROOT, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert p.returncode == 0 and "RESULT: clean" in p.stdout


def test_pack_help_quirks(capsys, tmp_path):
    assert build.main(["verify", "--help"]) == 0
    out = capsys.readouterr()
    assert "usage: pack verify" in out.out and "cannot verify" not in out.err
    assert build.main(["index", "--help"]) == 0
    assert "usage: pack index" in capsys.readouterr().out
    assert build.main(["--help"]) == 0
    assert "pack index" in capsys.readouterr().out
    assert build.main(["scan", "--help"]) == 0
    assert "PROOFLAB_PREPUSH_SCAN" in capsys.readouterr().out


def test_index_refuses_a_sealed_pack(tmp_path, capsys):
    (tmp_path / "MANIFEST.json").write_text("{}")
    assert build.main(["index", str(tmp_path)]) == 2
    assert "sealed" in capsys.readouterr().err


def test_humanloop_and_collect_help_through_the_dispatcher(capsys):
    for verb, words in (("humanloop", ("findings", "retest")), ("collect", ("--cid", "--surfaces", "--runtimes"))):
        with pytest.raises(SystemExit) as stop:
            cli.main([verb, "--help"])
        assert stop.value.code == 0
        text = capsys.readouterr().out
        assert all(w in text for w in words), (verb, text)

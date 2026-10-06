"""M1: `humanloop retest` closes a finding only by a passing re-test, writes the link note once, records the closure."""
import json

import pytest

from prooflab.adapters import human_loop as hl
from prooflab.humanloop import retest, runner
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.tests.fake_servicenow import FakeServiceNow

from hl_support import LIMIT, assessment, env_for, make_client, write_json

CID = "ifabric-run-1791177843-a1b2c3"
RETEST_CID = "ifabric-run-1791178843-d4e5f6"


@pytest.fixture()
def fake():
    srv = FakeServiceNow().start()
    yield srv
    srv.stop()


def _finding():
    return hl.build_finding(assessment(scope_id=CID), CID, "owner@example.com", "2026-10-06T05:15:00.000Z",
                            limit=LIMIT, detected_at="2026-10-06T06:00:00.000Z")


def _setup(fake, tmp_path):
    """A delivered finding: file, log, incident."""
    log = tmp_path / "log.jsonl"
    fpath = write_json(tmp_path / ("C16-%s.json" % CID), _finding())
    assert runner.main(["notify", "--finding", fpath], env=env_for(log), client_factory=lambda: make_client(fake)) == 0
    return str(log), fpath


def _retest_assessment(tmp_path, **over):
    over.setdefault("scope_id", RETEST_CID)
    over.setdefault("requirement_verdict", "SATISFIED")
    return write_json(tmp_path / "retest-assessment.json", assessment(**over))


def _run(fake, log, argv):
    return runner.main(["retest"] + argv, env=env_for(log), client_factory=lambda: make_client(fake))


def test_satisfied_retest_links_note_logs_and_records_closure(fake, tmp_path, capsys):
    log, fpath = _setup(fake, tmp_path)
    capsys.readouterr()
    a = _retest_assessment(tmp_path)
    out = tmp_path / "closures"
    assert _run(fake, log, ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", a, "--out", str(out)]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["action"] == "linked" and row["closed"] is True
    notes = [j["value"] for j in fake.journal if j["value"].startswith(hl.RETEST_NOTE_PREFIX)]
    assert len(notes) == 1 and "SATISFIED" in notes[0] and "R-synthetic-v1" in notes[0]
    fid = finding_from_dict(_finding()).finding_id
    entries = [e for e in DeliveryLog(log).history(fid) if e["state"] == "RETEST_LINKED"]
    assert len(entries) == 1 and entries[0]["retest_cid"] == RETEST_CID and entries[0]["sys_id"]
    closure = json.loads(next(out.glob("*-closure.json")).read_text())
    assert closure["closed_by"] == "retest" and closure["retest_cid"] == RETEST_CID and closure["finding_id"] == fid
    assert closure["retest"]["verdict"] == "SATISFIED"


def test_repeat_writes_no_second_note(fake, tmp_path, capsys):
    log, fpath = _setup(fake, tmp_path)
    a = _retest_assessment(tmp_path)
    argv = ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", a, "--out", str(tmp_path / "c")]
    assert _run(fake, log, argv) == 0
    patches = fake.patch_count
    capsys.readouterr()
    assert _run(fake, log, argv) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "already-linked"
    assert fake.patch_count == patches


@pytest.mark.parametrize("over,why", [
    ({"requirement_verdict": "BREACHED"}, "not SATISFIED"),
    ({"requirement_verdict": "INDETERMINATE"}, "not SATISFIED"),
    ({"threshold_version": "R-synthetic-v2"}, "register version"),
    ({"control_ref": "C7"}, "control"),
    ({"scope_kind": "window"}, "scope kind"),
    ({"scope_id": "ifabric-run-1791179999-ffffff"}, "not --retest-run"),
])
def test_refused_writes_nothing(fake, tmp_path, capsys, over, why):
    log, fpath = _setup(fake, tmp_path)
    patches = fake.patch_count
    a = _retest_assessment(tmp_path, **over)
    assert _run(fake, log, ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", a,
                            "--out", str(tmp_path / "c")]) == 2
    assert why in capsys.readouterr().err
    fid = finding_from_dict(_finding()).finding_id
    assert not [e for e in DeliveryLog(log).history(fid) if e["state"] == "RETEST_LINKED"]
    assert fake.patch_count == patches and not (tmp_path / "c").exists()


def test_the_finding_own_run_is_no_retest(fake, tmp_path, capsys):
    log, fpath = _setup(fake, tmp_path)
    a = _retest_assessment(tmp_path, scope_id=CID)
    assert _run(fake, log, ["--finding", fpath, "--retest-run", CID, "--assessment", a]) == 2
    assert "must differ" in capsys.readouterr().err


def test_lookup_by_id_and_assessment_from_snapshot(fake, tmp_path):
    log, fpath = _setup(fake, tmp_path)
    snap = tmp_path / "snap"
    (snap / "findings").mkdir(parents=True)
    (snap / "findings" / "x.json").write_text(json.dumps(_finding()))
    (snap / "assessments" / "C16").mkdir(parents=True)
    (snap / "assessments" / "C16" / ("%s.json" % RETEST_CID)).write_text(
        json.dumps(assessment(scope_id=RETEST_CID, requirement_verdict="SATISFIED")))
    fid = finding_from_dict(_finding()).finding_id
    assert _run(fake, log, ["--finding", fid, "--retest-run", RETEST_CID, "--snapshot", str(snap)]) == 0
    assert (snap / "closures" / "x-closure.json").exists()


def test_undelivered_finding_is_refused(fake, tmp_path, capsys):
    log = str(tmp_path / "empty.jsonl")
    fpath = write_json(tmp_path / "f.json", _finding())
    a = _retest_assessment(tmp_path)
    assert _run(fake, log, ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", a]) == 2
    assert "no delivered incident" in capsys.readouterr().err


def test_dry_run_refused_on_the_production_log_and_writes_nothing_under_wiring_tests(fake, tmp_path, capsys):
    log, fpath = _setup(fake, tmp_path)
    a = _retest_assessment(tmp_path)
    assert _run(fake, log, ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", a, "--dry-run"]) == 2
    assert "guard (a)" in capsys.readouterr().err
    wlog = tmp_path / "wiring-tests" / "log.jsonl"
    patches = fake.patch_count
    env = env_for(wlog)
    assert runner.main(["retest", "--finding", fpath, "--retest-run", RETEST_CID, "--assessment", a, "--dry-run"],
                       env=env, client_factory=lambda: make_client(fake)) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "dry-run"
    assert fake.patch_count == patches and not wlog.exists()

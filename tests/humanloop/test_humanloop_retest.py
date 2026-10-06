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
    over.setdefault("as_of", "2026-10-06T07:30:00.000Z")     # after the finding's detected_at (06:00)
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
        json.dumps(assessment(scope_id=RETEST_CID, requirement_verdict="SATISFIED", as_of="2026-10-06T07:30:00.000Z")))
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


def test_export_with_closures_has_no_closed_without_retest_gap(fake, tmp_path, capsys):
    log, fpath = _setup(fake, tmp_path)
    a = _retest_assessment(tmp_path)
    cdir = tmp_path / "closures"
    assert _run(fake, log, ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", a, "--out", str(cdir)]) == 0
    sys_id = next(iter(fake.incidents))
    fake.human_update(sys_id, "owner@example.com", "2026-10-06 07:00:00", state="7")      # the owner closes it
    capsys.readouterr()
    base = ["export", "--finding", fpath, "--out", str(tmp_path / "exp")]
    assert runner.main(base, env=env_for(log), client_factory=lambda: make_client(fake)) == 0
    assert json.loads(capsys.readouterr().out)["gaps"]
    assert runner.main(base + ["--closures", str(cdir)], env=env_for(log), client_factory=lambda: make_client(fake)) == 0
    assert json.loads(capsys.readouterr().out)["gaps"] == []


def _nothing_written(fake, log, patches, tmp_path):
    fid = finding_from_dict(_finding()).finding_id
    assert not [e for e in DeliveryLog(log).history(fid) if e["state"] == "RETEST_LINKED"]
    assert fake.patch_count == patches and not (tmp_path / "c").exists()


def test_an_earlier_run_is_no_retest(fake, tmp_path, capsys):
    log, fpath = _setup(fake, tmp_path)
    patches = fake.patch_count
    earlier = "ifabric-run-1791170000-000000"
    a = _retest_assessment(tmp_path, scope_id=earlier, as_of="2026-10-06T05:00:00.000Z")
    assert _run(fake, log, ["--finding", fpath, "--retest-run", earlier, "--assessment", a, "--out", str(tmp_path / "c")]) == 2
    assert "must be later" in capsys.readouterr().err
    _nothing_written(fake, log, patches, tmp_path)


def test_no_ordering_evidence_is_refused(fake, tmp_path, capsys):
    log, fpath = _setup(fake, tmp_path)
    patches = fake.patch_count
    a = _retest_assessment(tmp_path, as_of=None)
    assert _run(fake, log, ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", a, "--out", str(tmp_path / "c")]) == 2
    assert "cannot establish" in capsys.readouterr().err
    _nothing_written(fake, log, patches, tmp_path)


def test_scope_times_in_the_snapshot_decide_order(fake, tmp_path, capsys):
    log, fpath = _setup(fake, tmp_path)
    snap = tmp_path / "snap"
    (snap / "assessments" / "C16").mkdir(parents=True)
    (snap / "assessments" / "C16" / ("%s.json" % CID)).write_text(json.dumps(
        assessment(scope_id=CID, scope_start="2026-10-06T05:00:00Z", scope_end="2026-10-06T05:10:00Z")))
    patches = fake.patch_count
    early = _retest_assessment(tmp_path, scope_start="2026-10-06T05:10:00Z")      # not strictly after; as_of alone would pass
    assert _run(fake, log, ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", early, "--snapshot", str(snap),
                            "--out", str(tmp_path / "c")]) == 2
    _nothing_written(fake, log, patches, tmp_path)
    ok = _retest_assessment(tmp_path, scope_start="2026-10-06T05:20:00Z", as_of="2026-10-06T05:30:00.000Z")
    assert _run(fake, log, ["--finding", fpath, "--retest-run", RETEST_CID, "--assessment", ok, "--snapshot", str(snap),
                            "--out", str(tmp_path / "c")]) == 0


def test_window_scope_needs_a_different_later_window(fake, tmp_path, capsys):
    wid = "window-2026-10-06T05"
    f = hl.build_finding(assessment(scope_kind="window", scope_id=wid), CID, "owner@example.com",
                         "2026-10-06T05:15:00.000Z", limit=LIMIT, detected_at="2026-10-06T06:00:00.000Z")
    log = tmp_path / "log.jsonl"
    fpath = write_json(tmp_path / "W.json", f)
    assert runner.main(["notify", "--finding", fpath], env=env_for(log), client_factory=lambda: make_client(fake)) == 0
    patches = fake.patch_count
    for over in ({"scope_id": wid}, {"scope_id": "window-2026-10-06T04", "as_of": "2026-10-06T05:00:00.000Z"}):
        a = _retest_assessment(tmp_path, scope_kind="window", **over)
        assert _run(fake, str(log), ["--finding", fpath, "--retest-run", over["scope_id"], "--assessment", a,
                                     "--out", str(tmp_path / "c")]) == 2
    assert fake.patch_count == patches and not (tmp_path / "c").exists()
    a = _retest_assessment(tmp_path, scope_kind="window", scope_id="window-2026-10-06T07")
    assert _run(fake, str(log), ["--finding", fpath, "--retest-run", "window-2026-10-06T07", "--assessment", a,
                                 "--out", str(tmp_path / "c")]) == 0

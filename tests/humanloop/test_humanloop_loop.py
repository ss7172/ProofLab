"""PR-20b: analysis between runs, the check loop, snapshots, export, the mirror, trace + retest."""
import json

import pytest

from prooflab.adapters import human_loop as hl
from prooflab.contract import record as rec
from prooflab.humanloop import analysis, check_loop, mirror, runner, snapshots
from prooflab.humanloop import config as cfg
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.servicenow.notifier import notify
from prooflab.servicenow.nemotron import AnalyzerError
from prooflab.tests.fake_servicenow import INTEGRATION_USER, OWNER_USER, FakeServiceNow

from hl_support import LIMIT, assessment, env_for, fixture, make_client, write_json

CID = "ifabric-test-1791177843-a1b2c3"
CUTOFF = "2026-10-06T12:00:00Z"


@pytest.fixture()
def fake():
    srv = FakeServiceNow().start()
    yield srv
    srv.stop()


def the_finding():
    return hl.build_finding(assessment(), CID, OWNER_USER, "2026-10-06T05:15:00.000Z", limit=LIMIT,
                            detected_at="2026-10-06T06:00:00.000Z")


def delivered(fake, tmp_path):
    data = the_finding()
    config = cfg.HumanLoopConfig.from_env(env_for(tmp_path / "log.jsonl"))
    log = DeliveryLog(config.delivery_log)
    res = notify(finding_from_dict(data), make_client(fake), log, owner_user=OWNER_USER,
                 integration_user=INTEGRATION_USER)
    return data, config, log, res.sys_id


class Boom:
    backend, model_alias = "x", "y"

    def analyze(self, messages):
        raise RuntimeError("model text must never reach the log: SECRET-MODEL-TEXT")


def test_analysis_deferred_while_a_run_is_active_and_never_for_approval(fake, tmp_path):
    data, config, log, _ = delivered(fake, tmp_path)
    rows = analysis.analyze_between_runs([data], make_client(fake), config, Boom(), lambda: True, str(tmp_path))
    assert rows[0]["action"] == "deferred"
    approval = fixture("approval-finding.json")
    rows = analysis.analyze_between_runs([approval], make_client(fake), config, Boom(), lambda: False, str(tmp_path))
    assert rows[0]["action"] == "skipped" and "approval" in rows[0]["reason"]


def test_analysis_exception_becomes_our_failure_entry_without_model_text(fake, tmp_path):
    data, config, log, _ = delivered(fake, tmp_path)
    rows = analysis.analyze_between_runs([data], make_client(fake), config, Boom(), lambda: False, str(tmp_path))
    assert rows[0]["action"] in ("failed", "analysed")
    text = open(config.delivery_log, encoding="utf-8").read()
    assert "SECRET-MODEL-TEXT" not in text


def test_analysis_skips_undelivered_and_wiring_test_logs(fake, tmp_path):
    data = the_finding()
    config = cfg.HumanLoopConfig.from_env(env_for(tmp_path / "log.jsonl"))
    rows = analysis.analyze_between_runs([data], make_client(fake), config, Boom(), lambda: False, str(tmp_path))
    assert rows[0]["reason"] == "not delivered"
    wcfg = cfg.HumanLoopConfig.from_env(env_for(tmp_path / "wiring-tests" / "log.jsonl"))
    rows = analysis.analyze_between_runs([data], make_client(fake), wcfg, Boom(), lambda: False, str(tmp_path))
    assert rows[0]["reason"] == "wiring-test log"


def test_check_loop_stops_at_responded_and_final_check_records_silence(fake, tmp_path):
    data, config, log, sys_id = delivered(fake, tmp_path)
    clock = iter(["2026-10-06T11:00:00Z", "2026-10-06T11:30:00Z", "2026-10-06T12:00:01Z", "2026-10-06T12:00:01Z"])
    sleeps = []
    passes = check_loop.run_loop([data], make_client(fake), config, CUTOFF, interval_s=3600,
                                 sleep=sleeps.append, clock=lambda: next(clock))
    assert sleeps and max(sleeps) == check_loop.MAX_INTERVAL_S      # interval capped
    assert passes[-1][0]["state"] == "NO_RESPONSE_OBSERVED"          # silence recorded after the cutoff
    # a response stops the loop
    data2, config2, log2, sys2 = delivered(fake, tmp_path / "second")
    fake.add_journal_entry(sys2, OWNER_USER, "Acknowledged", "2026-10-06 11:00:00")
    passes = check_loop.run_loop([data2], make_client(fake), config2, CUTOFF, sleep=lambda s: None,
                                 clock=lambda: "2026-10-06T11:05:00Z")
    assert passes[0][0]["state"] == "RESPONDED" and len(passes) == 2 and passes[1][0]["action"] == "stopped"


def test_snapshot_cadence_and_case_written(fake, tmp_path):
    data, config, log, _ = delivered(fake, tmp_path)
    rows = snapshots.snapshot_cases([data], make_client(fake), config, CUTOFF, str(tmp_path / "cases"))
    assert rows[0]["sha256"] and rows[0]["servicenow"] != "unreachable"
    assert 30 <= snapshots.PENDING_CADENCE_S <= 60 and 300 <= snapshots.SETTLED_CADENCE_S <= 600
    t0 = "2026-10-06T10:00:00Z"
    assert snapshots.due(None, t0, True)
    assert not snapshots.due(t0, "2026-10-06T10:00:20Z", True)
    assert snapshots.due(t0, "2026-10-06T10:01:00Z", True)
    assert not snapshots.due(t0, "2026-10-06T10:02:00Z", False)
    assert snapshots.due(t0, t0, False, sealed=True) and not snapshots.due(t0, t0, False, sealed=True, sealed_done=True)


def test_export_records_closed_without_retest_gap(fake, tmp_path):
    data, config, log, sys_id = delivered(fake, tmp_path)
    out = snapshots.export_all([data], make_client(fake), config, str(tmp_path / "inc"))
    assert len(out["exports"]) == 1 and out["gaps"] == []
    fake.human_update(sys_id, OWNER_USER, "2026-10-06 11:30:00", state="7")
    out = snapshots.export_all([data], make_client(fake), config, str(tmp_path / "inc"))
    assert out["gaps"][0]["gap"] == hl.CLOSED_WITHOUT_RETEST and out["gaps"][0]["finding_status"] == "open"
    good = hl.build_retest(assessment(requirement_verdict="SATISFIED"), at="2026-10-06T11:40:00Z")
    out = snapshots.export_all([data], make_client(fake), config, str(tmp_path / "inc"),
                               retests={finding_from_dict(data).finding_id: good})
    assert out["gaps"] == []


def test_trace_and_retest_helpers():
    steps = [{"at": "2026-10-06T06:00:%02dZ" % (i % 60), "actor": "agent-%d" % (i % 2), "action": "handoff"}
             for i in range(250)] + [{"at": "", "actor": "x", "action": "y"}]
    trace = hl.build_trace(steps, {"agent-0": "customer"})
    assert len(trace) == hl.TRACE_MAX and {s["zone"] for s in trace} <= {"customer", "other"}
    assert [s["at"] for s in trace] == sorted(s["at"] for s in trace)
    data = the_finding()
    data["trace"] = trace
    finding_from_dict(data)         # Arth's validator accepts the trace
    retest = hl.build_retest(assessment(requirement_verdict="SATISFIED"), at="2026-10-06T11:40:00Z")
    data["retest"] = retest
    finding_from_dict(data)
    assert hl.closes(data, retest) and "\n" not in hl.retest_note(data, retest)
    assert not hl.closes(data, dict(retest, threshold_version="other"))


def test_mirror_transitions_dedupe_and_validate(tmp_path):
    fid = "ifabric:C16:v1:run:%s:finding" % CID
    lines = [json.dumps(e, sort_keys=True) for e in (
        {"ts": "2026-10-06T06:00:00Z", "finding_id": fid, "state": "DELIVERED", "number": "INC1"},
        {"ts": "2026-10-06T06:01:00Z", "finding_id": fid, "state": "AWAITING_RESPONSE"},
        {"ts": "2026-10-06T06:02:00Z", "finding_id": fid, "state": "AWAITING_RESPONSE"},
        {"ts": "2026-10-06T06:03:00Z", "finding_id": fid, "state": "RESPONDED", "at": "2026-10-06T06:02:30Z",
         "actor": OWNER_USER},
        {"ts": "2026-10-06T06:04:00Z", "finding_id": fid, "state": "ANALYSIS_WRITTEN", "note_digest": "ab"},
    )]
    lines.insert(2, "{torn")
    records = mirror.mirror_lines(lines)
    assert [r["reason"] for r in records] == ["DELIVERED", "AWAITING_RESPONSE", "RESPONDED", "ANALYSIS_WRITTEN"]
    for r in records:
        assert rec.validate_record(r) == [], rec.validate_record(r)
        assert r["run.id"] == CID and r["record_kind"] == "notification"
    assert records[2]["observed.clock"] == "servicenow" and records[0]["observed.clock"] == "script-host"
    assert mirror.mirror_lines(lines, {r["record_id"] for r in records}) == []     # a re-mirror deduplicates


def test_mirror_analysis_line_carries_call_id_and_digest():
    fid = "F-1"
    line = json.dumps({"ts": "2026-10-06T06:04:00Z", "finding_id": fid, "state": "ANALYSIS_WRITTEN",
                       "note_digest": "ab", "action_ids": ["act-1", "act-2"]})
    [r] = mirror.mirror_lines([line])
    assert r["call.id"] == "act-1,act-2"
    assert '"note_digest": "ab"' in r["detail"]
    assert rec.validate_record(r) == []
    [r1] = mirror.mirror_lines([line.replace('["act-1", "act-2"]', '["act-1"]')])
    assert r1["call.id"] == "act-1"


def test_runner_mirror_and_check_verbs(fake, tmp_path, capsys):
    data, config, log, sys_id = delivered(fake, tmp_path)
    path = write_json(tmp_path / "f.json", data)
    env = env_for(tmp_path / "log.jsonl")
    out = tmp_path / "records.jsonl"
    assert runner.main(["mirror", "--out", str(out)], env=env) == 0
    first = out.read_text()
    assert runner.main(["mirror", "--out", str(out)], env=env) == 0
    assert out.read_text() == first and len(first.splitlines()) >= 1     # a re-mirror adds nothing
    capsys.readouterr()
    assert runner.main(["check", "--finding", path, "--cutoff", CUTOFF, "--once"], env=env,
                       client_factory=lambda: make_client(fake)) == 0
    assert json.loads(capsys.readouterr().out)[0]["action"] == "checked"
    assert runner.main(["export", "--finding", path, "--out", str(tmp_path / "inc")], env=env,
                       client_factory=lambda: make_client(fake)) == 0

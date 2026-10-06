"""G-05: the runner (humanloop/runner.py) against Arth's fake ServiceNow."""
import json

import pytest

from prooflab.humanloop import config as cfg
from prooflab.humanloop import runner
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.adapters import human_loop as hl
from prooflab.tests.fake_servicenow import FakeServiceNow

from hl_support import LIMIT, assessment, env_for, fixture, make_client, write_json

CID = "ifabric-test-1791177843-a1b2c3"


@pytest.fixture()
def fake():
    srv = FakeServiceNow().start()
    yield srv
    srv.stop()


def finding(**over):
    return hl.build_finding(assessment(**over), CID, "owner@example.com", "2026-10-06T05:15:00.000Z", limit=LIMIT,
                            detected_at="2026-10-06T06:00:00.000Z")


def run(fake, tmp_path, files, env, extra=()):
    argv = ["notify"] + [a for f in files for a in ("--finding", f)] + list(extra)
    return runner.main(argv, env=env, client_factory=lambda: make_client(fake))


def test_breached_notified_satisfied_not_and_rerun_is_zero_new(fake, tmp_path, capsys):
    log = tmp_path / "log.jsonl"
    breached = write_json(tmp_path / "b.json", finding())
    satisfied = write_json(tmp_path / "s.json", finding(requirement_verdict="SATISFIED"))
    assert run(fake, tmp_path, [breached, satisfied], env_for(log)) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["action"] for r in rows] == ["notified", "skipped"]
    assert rows[0]["state"] == "DELIVERED" and fake.post_count == 1
    # re-run: 0 new
    assert run(fake, tmp_path, [breached, satisfied], env_for(log)) == 0
    rows = json.loads(capsys.readouterr().out)
    assert all(r["action"] == "skipped" for r in rows) and fake.post_count == 1


def test_selftest_runs_before_any_log_write_and_blocks_on_failure(fake, tmp_path, capsys):
    log = tmp_path / "log.jsonl"
    order = []
    client = make_client(fake)
    real_find = client.find_incidents

    def spy(cid, user):
        order.append(("find", cid, DeliveryLog(log).path.exists()))
        return real_find(cid, user)

    client.find_incidents = spy
    path = write_json(tmp_path / "b.json", finding())
    assert runner.main(["notify", "--finding", path], env=env_for(log), client_factory=lambda: client) == 0
    assert order[0][1] == runner.SELFTEST_QUERY and order[0][2] is False   # selftest first, log not yet written
    assert fake.post_count == 1
    # a failing selftest stops the batch: nothing is sent or logged
    bad = make_client(fake)
    bad._client_secret = "wrong"
    log2 = tmp_path / "log2.jsonl"
    code = runner.main(["notify", "--finding", path], env=env_for(log2), client_factory=lambda: bad)
    assert code == 1 and not log2.exists() and fake.post_count == 1


def test_monitoring_gap_is_notified(fake, tmp_path, capsys):
    gap = write_json(tmp_path / "g.json", finding(requirement_verdict="INDETERMINATE"))
    assert run(fake, tmp_path, [gap], env_for(tmp_path / "log.jsonl")) == 0
    assert json.loads(capsys.readouterr().out)[0]["state"] == "DELIVERED"


def test_approval_finding_has_its_own_log(fake, tmp_path, capsys):
    main_log = tmp_path / "log.jsonl"
    appr_log = tmp_path / "evidence" / "register" / "approval" / "delivery-log.jsonl"
    approval = write_json(tmp_path / "a.json", hl.build_approval_finding(fixture("approval-finding.json")))
    assert run(fake, tmp_path, [approval], env_for(main_log, appr_log)) == 0
    fid = finding_from_dict(fixture("approval-finding.json")).finding_id
    assert [e["state"] for e in DeliveryLog(appr_log).history(fid)][-1] == "DELIVERED"
    assert not main_log.exists()
    capsys.readouterr()
    # without its log configured the approval is refused, not written to the main log
    assert run(fake, tmp_path, [approval], env_for(tmp_path / "other.jsonl")) == 2
    assert not (tmp_path / "other.jsonl").exists()


def test_every_generated_file_passes_finding_from_dict(tmp_path):
    for over in ({}, {"requirement_verdict": "SATISFIED"}, {"requirement_verdict": "INDETERMINATE"}):
        finding_from_dict(finding(**over))


def test_config_requires_absolute_log_and_explicit_owner(fake, tmp_path, capsys):
    path = write_json(tmp_path / "b.json", finding())
    assert run(fake, tmp_path, [path], {"SNOW_OWNER_USER": "o", "PROOFLAB_DELIVERY_LOG": "rel/log.jsonl"}) == 2
    assert run(fake, tmp_path, [path], {"PROOFLAB_DELIVERY_LOG": str(tmp_path / "l")}) == 2
    assert fake.post_count == 0
    with pytest.raises(cfg.ConfigError):
        cfg.HumanLoopConfig.from_env({"SNOW_OWNER_USER": "o", "PROOFLAB_DELIVERY_LOG": str(tmp_path / "l"),
                                      "PROOFLAB_APPROVAL_DELIVERY_LOG": str(tmp_path / "l")})

"""Bugs (a) and (b): reproduced on Arth's fakes (the prototype work/13-prototypes/repro_bugs.py), then guarded."""
import json

import pytest

from prooflab.adapters import human_loop as hl
from prooflab.humanloop import runner
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import finding_from_dict
from prooflab.servicenow.notifier import check_response, notify
from prooflab.tests.fake_servicenow import INTEGRATION_USER, OWNER_USER, FakeServiceNow

from hl_support import LIMIT, assessment, env_for, make_client, write_json

CID = "ifabric-test-1791177843-a1b2c3"
CUTOFF, NOW = "2026-10-06T12:00:00Z", "2026-10-06T13:00:00Z"


@pytest.fixture()
def fake():
    srv = FakeServiceNow().start()
    yield srv
    srv.stop()


def the_finding():
    return finding_from_dict(hl.build_finding(assessment(), CID, OWNER_USER, "v", limit=LIMIT,
                                              detected_at="2026-10-06T06:00:00.000Z"))


def test_bug_a_reproduced_upstream_dry_run_on_existing_incident_logs_delivered(fake, tmp_path):
    client, log, f = make_client(fake), DeliveryLog(tmp_path / "wiring-tests" / "log.jsonl"), the_finding()
    notify(f, client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER)
    posts = fake.post_count
    dry = notify(f, client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER, dry_run=True)
    states = [e["state"] for e in log.history(f.finding_id)]
    assert dry.state == "DELIVERED" and dry.reused and "DRY_RUN" not in states   # the bug: not a DRY_RUN
    assert fake.post_count == posts                                              # but nothing is written


def test_bug_a_guard_refuses_dry_run_on_a_production_log(fake, tmp_path, capsys):
    prod = tmp_path / "evidence" / "servicenow" / "delivery-log.jsonl"
    path = write_json(tmp_path / "b.json", hl.build_finding(assessment(), CID, OWNER_USER, "v", limit=LIMIT))
    code = runner.main(["notify", "--finding", path, "--dry-run"], env=env_for(prod),
                       client_factory=lambda: make_client(fake))
    assert code == 2 and not prod.exists() and fake.post_count == 0
    assert "guard (a)" in capsys.readouterr().err


def test_bug_a_guard_allows_dry_run_under_wiring_tests_and_never_posts(fake, tmp_path, capsys):
    log = tmp_path / "wiring-tests" / "delivery-log.jsonl"
    path = write_json(tmp_path / "b.json", hl.build_finding(assessment(), CID, OWNER_USER, "v", limit=LIMIT))
    code = runner.main(["notify", "--finding", path, "--dry-run"], env=env_for(log),
                       client_factory=lambda: make_client(fake))
    assert code == 0 and fake.post_count == 0
    assert json.loads(capsys.readouterr().out)[0]["state"] == "DRY_RUN"


def test_bug_a_guard_covers_the_approval_log_too(fake, tmp_path):
    from hl_support import fixture
    appr = write_json(tmp_path / "a.json", hl.build_approval_finding(fixture("approval-finding.json")))
    wiring = tmp_path / "wiring-tests" / "log.jsonl"
    prod_appr = tmp_path / "evidence" / "register" / "approval" / "delivery-log.jsonl"
    code = runner.main(["notify", "--finding", appr, "--dry-run"], env=env_for(wiring, prod_appr),
                       client_factory=lambda: make_client(fake))
    assert code == 2 and not prod_appr.exists()


def test_bug_b_reproduced_upstream_zero_row_journal_gives_false_silence(fake, tmp_path):
    client, log, f = make_client(fake), DeliveryLog(tmp_path / "log.jsonl"), the_finding()
    sys_id = notify(f, client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER).sys_id
    fake.add_journal_entry(sys_id, OWNER_USER, "Acknowledged", "2026-10-06 11:00:00")
    fake.human_update(sys_id, "other.admin", "2026-10-06 11:30:00")      # a later non-owner update
    fake.journal.clear()                                                 # live ACL: 200 with 0 rows
    out = check_response(f, client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER,
                         cutoff=CUTOFF, now=NOW)
    assert out.state == "NO_RESPONSE_OBSERVED"                           # the upstream bug, reproduced


def test_bug_b_guard_sticky_responded_survives_later_states(fake, tmp_path):
    client, log, f = make_client(fake), DeliveryLog(tmp_path / "log.jsonl"), the_finding()
    sys_id = notify(f, client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER).sys_id
    fake.add_journal_entry(sys_id, OWNER_USER, "Acknowledged", "2026-10-06 11:00:00")
    first = check_response(f, client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER,
                           cutoff=CUTOFF, now="2026-10-06T11:05:00Z")
    assert first.state == "RESPONDED"
    fake.human_update(sys_id, "other.admin", "2026-10-06 11:30:00")
    fake.journal.clear()
    late = check_response(f, client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER,
                          cutoff=CUTOFF, now=NOW)
    entries = log.history(f.finding_id)
    assert entries[-1]["state"] == late.state != "RESPONDED"             # latest-wins would say silence
    sticky = hl.sticky_response(entries)
    assert sticky is not None and sticky["state"] == "RESPONDED" and sticky["actor"] == OWNER_USER


def test_sticky_response_none_without_a_reply():
    assert hl.sticky_response([{"state": "DELIVERED"}, {"state": "NO_RESPONSE_OBSERVED"}]) is None

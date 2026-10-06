"""G-22: the live shapes Arth's fakes model differently (work/13 T2, R6, R7), against his UNCHANGED code."""
import pytest

from assurance_support import ELB_URL
from prooflab.servicenow.case_view import case_view
from prooflab.servicenow.client import ServiceNowClient
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.finding import Finding
from prooflab.servicenow.nemotron import AnalyzerError, GatewayAnalyzer
from prooflab.servicenow.notifier import check_response, notify
from prooflab.tests.fake_gateway import API_KEY, FakeGateway, completion
from prooflab.tests.fake_servicenow import CLIENT_ID, CLIENT_SECRET, INTEGRATION_USER, OWNER_USER, FakeServiceNow

CUTOFF = "2026-10-05T12:00:00Z"
ALIAS = "nemotron-super-120b"


def _breach():  # synthetic finding (work/13 repro shape)
    return Finding(control_ref="C16", control_id="ACN-COST-001", threshold_version="G-FM-v1",
                   scope_kind="run", scope_id="FM-B", verdict="BREACHED",
                   summary="synthetic: 10,800 tokens over the cap", detected_at="2026-10-05T10:00:00Z",
                   evidence=("gateway:action-123",))


@pytest.fixture()
def sn():
    fake = FakeServiceNow().start()
    yield fake
    fake.stop()


@pytest.fixture()
def gw():
    fake = FakeGateway().start()
    yield fake
    fake.stop()


def test_unchanged_gateway_analyzer_refuses_the_injected_plain_http_url():
    with pytest.raises(ValueError):
        GatewayAnalyzer(ELB_URL, ALIAS)
    with pytest.raises(ValueError):
        GatewayAnalyzer(ELB_URL[:-3], ALIAS)
    assert GatewayAnalyzer("http://127.0.0.1:8081", ALIAS).base_url == "http://127.0.0.1:8081"  # loopback (G-15)


def test_guardrail_200_with_content_filter_is_blocked(gw):
    gw.replies.append(completion("Input blocked by policy.", finish_reason="content_filter", action_id="act-g-200"))
    with pytest.raises(AnalyzerError) as err:
        GatewayAnalyzer(gw.base_url, ALIAS, API_KEY).analyze([{"role": "user", "content": "x"}])
    assert err.value.kind == "blocked" and err.value.action_id == "act-g-200"


def test_an_unstripped_v1_suffix_misses_the_endpoint(gw):
    gw.replies.append(completion("never reached"))
    with pytest.raises(AnalyzerError) as err:  # /v1/v1/chat/completions: the fake answers 503
        GatewayAnalyzer(gw.base_url + "/v1", ALIAS, API_KEY).analyze([{"role": "user", "content": "x"}])
    assert err.value.kind == "unavailable"


def test_journal_200_with_0_rows_hides_the_owner_reply_bug_b(sn, tmp_path):
    """Live: the itil ACL makes sys_journal_field answer 200 with 0 rows (the fake answers 403). With a later
    non-owner update, Arth's unchanged check_response then reports NO_RESPONSE_OBSERVED although the owner
    replied: bug (b). PR-20a's guards (<= 60 s check, sticky RESPONDED, nobody else updates) carry it."""
    client = ServiceNowClient(base_url=sn.base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    log = DeliveryLog(tmp_path / "log-b.jsonl")
    sys_id = notify(_breach(), client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER).sys_id
    sn.append_work_note(sys_id, "Owner Person", OWNER_USER, "Acknowledged, investigating")
    sn.append_work_note(sys_id, "Other Admin", "other.admin", "triage: assignment group set")
    sn.journal.clear()  # the live shape: 200, 0 rows, no error
    out = check_response(_breach(), client, log, owner_user=OWNER_USER, integration_user=INTEGRATION_USER,
                         cutoff=CUTOFF, now="2026-10-05T13:00:00Z")
    assert out.state == "NO_RESPONSE_OBSERVED"
    assert "Acknowledged, investigating" in sn.incidents[sys_id]["work_notes"]
    case = case_view(_breach(), client, log, owner_user=OWNER_USER, cutoff=CUTOFF,
                     integration_user=INTEGRATION_USER, now="2026-10-05T13:00:00Z")
    assert case["response"]["state"] == "NO_RESPONSE_OBSERVED"
    sn.journal_forbidden = True  # the fakes' 403 model gives a different, honest answer
    out403 = check_response(_breach(), client, DeliveryLog(tmp_path / "log-c.jsonl"), owner_user=OWNER_USER,
                            integration_user=INTEGRATION_USER, cutoff=CUTOFF, now="2026-10-05T13:00:00Z")
    assert out403.state == "RESPONSE_UNKNOWN"

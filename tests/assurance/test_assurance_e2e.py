"""G-01 + G-03 + G-22 end to end: Arth's run_assurance_agent -> CallableAnalyzer -> our invoke helper (stubbed
aws CLI) -> the GENERATED bundle running as a local runtime -> Arth's fake gateway reached over plain HTTP through
a host name his URL check refuses, with the injected /v1 suffix. Arth's fakes, 127.0.0.1 only."""
import json

import pytest

from assurance_support import ARN, FakeAwsCli, Runtime
from prooflab.humanloop.invoke import assurance_analyzer
from prooflab.servicenow.assurance_agent import run_assurance_agent
from prooflab.servicenow.case_view import case_view
from prooflab.servicenow.client import ServiceNowClient
from prooflab.servicenow.delivery_log import DeliveryLog
from prooflab.servicenow.nemotron import GatewayAnalyzer
from prooflab.servicenow.notifier import notify
from prooflab.tests.fake_gateway import API_KEY, FakeGateway, completion
from prooflab.tests.fake_servicenow import CLIENT_ID, CLIENT_SECRET, INTEGRATION_USER, OWNER_USER, FakeServiceNow
from prooflab.tests.test_servicenow_assurance_agent import ALIAS, finding, note

CUTOFF = "2026-10-05T12:00:00Z"


@pytest.fixture()
def world(tmp_path):
    sn, gw = FakeServiceNow().start(), FakeGateway().start()
    port = gw.base_url.rsplit(":", 1)[1]
    url = "http://127.1:%s/v1" % port  # plain HTTP, a host Arth's check refuses, the injected /v1 suffix
    with pytest.raises(ValueError):
        GatewayAnalyzer(url, ALIAS)
    try:
        with Runtime(OPENAI_BASE_URL=url, OPENAI_API_KEY=API_KEY, MODEL_ALIAS=ALIAS) as rt:
            cli = FakeAwsCli(runtime=rt)
            client = ServiceNowClient(base_url=sn.base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
            log = DeliveryLog(tmp_path / "delivery-log.jsonl")
            analyzer = assurance_analyzer(arn=ARN, runner=cli, tmpdir=str(tmp_path / "io"))
            (tmp_path / "io").mkdir()
            yield {"sn": sn, "gw": gw, "rt": rt, "cli": cli, "client": client, "log": log,
                   "analyzer": analyzer, "tmp": tmp_path}
    finally:
        sn.stop()
        gw.stop()


def _run(w, **kw):
    return run_assurance_agent(finding(), w["client"], w["log"], w["analyzer"], owner_user=OWNER_USER,
                               integration_user=INTEGRATION_USER, out_dir=w["tmp"] / "agent", **kw)


def test_written_end_to_end_with_v1_to_v6(world):
    w = world
    assert notify(finding(), w["client"], w["log"], owner_user=OWNER_USER,
                  integration_user=INTEGRATION_USER).state == "DELIVERED"
    w["gw"].replies.append(completion("<think>private chain of thought</think>\n" + note(), action_id="act-ac-1"))
    out = _run(w)
    assert out.state == "WRITTEN", out.reason
    req = w["gw"].requests[0]
    assert req["model"] == ALIAS and req["max_tokens"] == 900
    assert w["gw"].auth_headers[0] == "Bearer " + API_KEY  # the path was /v1/chat/completions (else the fake 503s)
    rec = json.loads(out.evidence_path.read_text())
    assert rec["backend"] == "agentcore:ifabric_assurance_agent"
    assert rec["attempts"][0]["action_id"] == "act-ac-1" and rec["attempts"][0]["think_stripped"] is True
    case = case_view(finding(), w["client"], w["log"], owner_user=OWNER_USER, cutoff=CUTOFF,
                     integration_user=INTEGRATION_USER)
    checks = {c["id"]: c["status"] for c in case["outcome_validation"]["checks"]}
    assert [k for k in ("V1", "V2", "V3", "V4", "V5", "V6") if checks.get(k) != "pass"] == [], checks
    assert case["outcome_validation"]["status"] == "validated"
    cid = w["cli"].calls[0]["payload"]["cid"]
    assert cid.startswith("ifabric-assure-")
    assert list((w["tmp"] / "io").iterdir()) == []


def test_platform_guardrail_200_content_filter_is_blocked_with_the_action_id(world):
    w = world
    notify(finding(), w["client"], w["log"], owner_user=OWNER_USER, integration_user=INTEGRATION_USER)
    w["gw"].replies.append(completion("Input blocked by policy.", finish_reason="content_filter",
                                      action_id="act-blk-200"))
    out = _run(w)
    assert out.state == "BLOCKED"
    last = [e for e in w["log"].history(finding().finding_id) if e["state"].startswith("ANALYSIS_")][-1]
    assert last["state"] == "ANALYSIS_BLOCKED" and last["action_ids"] == ["act-blk-200"]
    assert len(w["cli"].calls) == 1  # blocked: no second invocation


def test_the_runtime_witness_lines_carry_ids_never_text(world):
    w = world
    notify(finding(), w["client"], w["log"], owner_user=OWNER_USER, integration_user=INTEGRATION_USER)
    text = note()
    w["gw"].replies.append(completion(text, action_id="act-w-1"))
    assert _run(w).state == "WRITTEN"
    w["rt"].__exit__(None, None, None)
    lines = w["rt"].witness_lines()
    assert lines and lines[-1]["action_id"] == "act-w-1" and lines[-1]["outcome"] == "ok"
    assert lines[-1]["usage"]["total_tokens"] == 1110 and lines[-1]["finish_reason"] == "stop"
    assert lines[-1]["cid"] == w["cli"].calls[0]["payload"]["cid"]
    assert text.splitlines()[0] not in w["rt"].stdout
